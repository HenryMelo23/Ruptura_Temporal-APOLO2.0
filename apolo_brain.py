"""
apolo_brain.py  —  Nucleo de Inteligencia de Apolo v2.0
=========================================================
Modulo CENTRAL e UNICO de IA do Apolo.
Importado por GAME5.py e treino_laser_gpu.py.

NEUROGENESE ATIVA:
  Apolo monitora sua propria confusao (entropia dos Q-values).
  Quando confuso por muito tempo, CRIA novos neuronios automaticamente.
  Se a arquitetura mudar, faz backup e reinicia pesos sem conflito.

  Arquitetura salva em: apolo_arq.json
  Pesos salvos em:      apolo_memoria_dqn.pt
"""

import math, random, collections, os, json, shutil
import torch
import torch.nn as nn
from qa_logger import registrar_erro

# =============================================================================
# CONSTANTES CANONICAS
# =============================================================================
INPUT_SIZE  = 42
OUTPUT_SIZE = 9
ARQ_FILE    = "saves/apolo_arq.json"   # Metadata da arquitetura atual
PESOS_FILE  = "saves/apolo_memoria_dqn.pt"

# Limites de crescimento (GTX 1650: 4GB VRAM — 512 eh o teto seguro)
HIDDEN_MIN  = 128
HIDDEN_MAX  = 512
HIDDEN_STEP = 64   # Cresce 64 neuronios por vez

# Neurogenese: se entropia media > ENTROPIA_LIMIAR por JANELA_ENTROPIA passos -> cresce
ENTROPIA_LIMIAR  = 0.9   # Entropia maxima em 3 acoes = ln(3) ~ 1.09
JANELA_ENTROPIA  = 1000  # Avalia a cada 1000 passos


# =============================================================================
# GERENCIADOR DE ARQUITETURA  (unica fonte de verdade)
# =============================================================================
class GerenciadorArquitetura:
    """
    Le e escreve a configuracao da rede em apolo_arq.json.
    Detecta incompatibilidade ao carregar pesos e dispara reset automatico.
    """

    @staticmethod
    def _padrao():
        return {"hidden": 256, "version": 1}

    @staticmethod
    def carregar() -> dict:
        if os.path.exists(ARQ_FILE):
            try:
                with open(ARQ_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return GerenciadorArquitetura._padrao()

    @staticmethod
    def salvar(cfg: dict):
        with open(ARQ_FILE, "w") as f:
            json.dump(cfg, f, indent=2)

    @staticmethod
    def crescer(cfg: dict) -> dict:
        """Aumenta hidden em HIDDEN_STEP, respeitando o teto."""
        novo = min(cfg["hidden"] + HIDDEN_STEP, HIDDEN_MAX)
        if novo == cfg["hidden"]:
            return cfg  # Ja no teto
        novo_cfg = {"hidden": novo, "version": cfg.get("version", 1) + 1}
        GerenciadorArquitetura.salvar(novo_cfg)
        # Limpa pesos antigos (incompativeis)
        if os.path.exists(PESOS_FILE):
            bak = PESOS_FILE.replace(".pt", f"_bak_v{cfg.get('version',1)}.pt")
            shutil.copy2(PESOS_FILE, bak)
            os.remove(PESOS_FILE)
        return novo_cfg


# =============================================================================
# NEURONIO DE SOBREVIVENCIA  (SurvivalGate)  —  peso fixo, nao-treinavel
# =============================================================================
# Indices das features usadas pelo SurvivalGate
_IDX_VIDA_P    = 4    # vida_apolo normalizada (0-1)
_IDX_DIST_ORB  = 27   # dist_orbe_proxima  (1.0 = longe / nao existe)
_IDX_DIR_ORB_X = 28   # dir_orbe_x (-1 a 1)
_IDX_DIR_ORB_Y = 29   # dir_orbe_y (-1 a 1)

# Indices das features usadas pelo DodgeGate
_IDX_DIST_PROJ  = 11  # distancia ao projetil mais proximo (0=tocando, 1=longe)
_IDX_PROJ_VEL_X = 12  # direcao de DESLOCAMENTO do projetil — x (normalizado)
_IDX_PROJ_VEL_Y = 13  # direcao de DESLOCAMENTO do projetil — y (normalizado)
_IDX_PROJ_APPR  = 17  # 1.0 se projetil se aproxima de Apolo, 0.0 caso contrario
_IDX_DASH_CD    = 14  # 1.0 se dash esta em cooldown

# Indices das features usadas pelo LaserGate
_IDX_LASER_FASE       = 18  # 0=inativo, 0.5=carregando, 1.0=disparando
_IDX_LASER_PROGRESSO  = 20  # progresso da fase atual (0-1)
_IDX_LASER_SENTIDO    = 22  # -1=anti-horario, 0=parado, 1=horario
_IDX_LASER_ANG_PROX   = 24  # signed approach: positivo = feixe vindo pra mim
_IDX_LASER_DIST_FEIXE = 25  # distancia perpendicular ao feixe (0=tocando, 1=longe)
_IDX_LASER_FUGA_X     = 30  # componente X do vetor de fuga perpendicular ao laser
_IDX_LASER_FUGA_Y     = 31  # componente Y do vetor de fuga perpendicular ao laser
_IDX_LASER_SWEEP      = 32  # 1.0 se o player ainda sera varrido nesta rodada

class DodgeGate(nn.Module):
    """
    Neuronio de evasao de projeteis com PESO FIXO — nao-treinavel.

    Quando um projetil se aproxima de Apolo, aplica bias massivo
    nas acoes PERPENDICULARES a trajetoria do projetil (direcoes seguras)
    e no DASH (se disponivel).

    Features usadas (devem ter mesmo significado em GAME5 e treino):
      [11] dist_proj    — distancia ao projetil mais proximo (0=perto, 1=longe)
      [12] proj_vel_x   — direcao de deslocamento do projetil (x, normalizado)
      [13] proj_vel_y   — direcao de deslocamento do projetil (y, normalizado)
      [17] proj_appr    — 1.0 se projetil se aproxima, 0.0 caso contrario
      [14] dash_cd      — 1.0 se dash em cooldown (nao usar dash nesse caso)

    Logica:
      perp_A = (-vel_y,  vel_x)  — perpendicular esquerda ao vetor de voo
      perp_B = ( vel_y, -vel_x)  — perpendicular direita ao vetor de voo
      bias[acao] = max(dot(acao_dir, perp_A), dot(acao_dir, perp_B))
      Q_final = Q + urgencia * bias * PESO_MAXIMO

    PESO = 150.0 (menor que SurvivalGate=200, sobrevivencia e mais urgente).
    """

    DIST_LIMIAR  = 0.50   # Ativa quando dist < 50% de 250px (= 125px)
    PESO_MAXIMO  = 150.0

    # Direcoes unitarias das 9 acoes (0=cima 1=baixo 2=esq 3=dir 4-7=diagonais 8=dash)
    # Diagonal normalizado por 1/sqrt(2) = 0.7071
    _K = 0.7071
    _ADX = torch.tensor([ 0.,  0., -1.,  1., -_K,  _K, -_K,  _K, 0.])
    _ADY = torch.tensor([-1.,  1.,  0.,  0., -_K, -_K,  _K,  _K, 0.])

    def forward(self, q: torch.Tensor, estado: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            dist  = estado[:, _IDX_DIST_PROJ]   # (batch,) 0=perto 1=longe
            vx    = estado[:, _IDX_PROJ_VEL_X]  # (batch,) direcao do projetil
            vy    = estado[:, _IDX_PROJ_VEL_Y]
            appr  = estado[:, _IDX_PROJ_APPR]   # (batch,) esta vindo?
            dc    = estado[:, _IDX_DASH_CD]      # (batch,) dash em cooldown?

            # Urgencia: 0 quando longe, 1 quando muito perto
            urgencia = torch.clamp(
                (self.DIST_LIMIAR - dist) / self.DIST_LIMIAR,
                min=0.0, max=1.0
            ) * appr  # so ativa se projetil esta se aproximando

            # Perpendiculares ao vetor de voo do projetil
            # perp_A = (-vy, vx),  perp_B = (vy, -vx)
            # Para cada acao i: align = max(dot(acao, perpA), dot(acao, perpB))
            # acao_dir . perp_A = adx*(-vy) + ady*(vx)  →  -adx*vy + ady*vx
            # acao_dir . perp_B = adx*(vy)  + ady*(-vx) →   adx*vy - ady*vx

            adx = self._ADX.to(q.device)  # (9,)
            ady = self._ADY.to(q.device)  # (9,)

            # (batch,1) broadcast com (9,)
            dot_A = (-adx.unsqueeze(0)) * vy.unsqueeze(1) + ady.unsqueeze(0) * vx.unsqueeze(1)
            dot_B =   adx.unsqueeze(0)  * vy.unsqueeze(1) - ady.unsqueeze(0) * vx.unsqueeze(1)

            bias = torch.max(dot_A, dot_B)            # (batch, 9) — positivo = acao segura
            bias = torch.clamp(bias, min=0.0)          # ignora direcoes perigosas

            # Dash: bias proporcional a urgencia, mas desativado se em cooldown
            dash_bias = urgencia * (1.0 - dc) * 0.8   # (batch,)
            bias[:, 8] = dash_bias

            sinal = urgencia.unsqueeze(1) * bias * self.PESO_MAXIMO

        return q + sinal


class LaserGate(nn.Module):
    """
    Neuronio de evasao do laser rotativo — PESO FIXO, nao-treinavel.

    Quando o feixe do laser esta se aproximando de Apolo e a distancia
    perpendicular e critica, aplica bias MASSIVO nas acoes perpendiculares
    ao laser (direcoes de fuga geometricamente corretas) e no DASH.

    Features usadas (indices fixos — nao alteram INPUT_SIZE=40):
      [18] laser_fase        — 0=inativo, 0.5=carregando, 1.0=disparando
      [24] laser_ang_proximo — signed approach: positivo = feixe vindo pra mim
      [25] laser_dist_feixe  — distancia perpendicular (0=tocando, 1=longe)
      [30] fuga_x            — componente X da direcao de fuga perpendicular
      [31] fuga_y            — componente Y da direcao de fuga perpendicular
      [32] in_sweep_zone     — 1.0 se ainda sera varrido pelo laser
      [14] dash_cd           — 1.0 se dash esta em cooldown

    Logica:
      urgencia = clamp((DIST_LIMIAR - dist_feixe) / DIST_LIMIAR, 0, 1)
               x laser_fase (so ativa quando disparando)
               x in_sweep_zone (so ativa se sera varrido)
      bias[acao] = dot(direcao_acao, (fuga_x, fuga_y)) — acoes que fogem do laser
      Q_final = Q + urgencia x bias x PESO_MAXIMO

    PESO = 250.0 (maior que DodgeGate=150: laser e instantaneo e letal).
    """

    DIST_LIMIAR  = 0.38   # Ativa quando dist < 38% (= ~152px de 400px)
    PESO_MAXIMO  = 250.0

    # Direcoes unitarias das 9 acoes (igual DodgeGate)
    _K = 0.7071
    _ADX = torch.tensor([ 0.,  0., -1.,  1., -_K,  _K, -_K,  _K, 0.])
    _ADY = torch.tensor([-1.,  1.,  0.,  0., -_K, -_K,  _K,  _K, 0.])

    def forward(self, q: torch.Tensor, estado: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            laser_fase   = estado[:, _IDX_LASER_FASE]       # (batch,) 0/0.5/1.0
            ang_appr     = estado[:, _IDX_LASER_ANG_PROX]   # (batch,) signed: pos=feixe chegando
            dist_feixe   = estado[:, _IDX_LASER_DIST_FEIXE] # (batch,) 0=perto 1=longe
            fuga_x       = estado[:, _IDX_LASER_FUGA_X]     # (batch,)
            fuga_y       = estado[:, _IDX_LASER_FUGA_Y]     # (batch,)
            sweep        = estado[:, _IDX_LASER_SWEEP]      # (batch,) 1.0=sera varrido
            dc           = estado[:, _IDX_DASH_CD]          # (batch,) dash em cooldown?

            # Urgencia: maxima quando laser disparando + feixe perto + sera varrido
            urgencia_dist = torch.clamp(
                (self.DIST_LIMIAR - dist_feixe) / self.DIST_LIMIAR,
                min=0.0, max=1.0
            )
            # Feixe chegando: signed approach positivo significa que o feixe vai me atingir
            feixe_chegando = torch.clamp(ang_appr, min=0.0, max=1.0)
            # Ativa apenas quando laser realmente disparando (fase >= 0.9 = 1.0)
            laser_on = (laser_fase >= 0.9).float()
            urgencia = urgencia_dist * feixe_chegando * sweep * laser_on

            # Calcula bias por acao: dot(direcao_acao, vetor_fuga)
            # Acoes que se movem na direcao de fuga recebem bias alto
            adx = self._ADX.to(q.device)  # (9,)
            ady = self._ADY.to(q.device)  # (9,)

            # dot[batch, i] = adx[i]*fuga_x[batch] + ady[i]*fuga_y[batch]
            dot = adx.unsqueeze(0) * fuga_x.unsqueeze(1) + ady.unsqueeze(0) * fuga_y.unsqueeze(1)
            bias = torch.clamp(dot, min=0.0)  # ignora direcoes que vao PARA o laser

            # Dash: bias alto quando urgente e disponivel (fuga instantanea)
            dash_bias = urgencia * (1.0 - dc) * 0.9   # (batch,)
            bias[:, 8] = dash_bias

            sinal = urgencia.unsqueeze(1) * bias * self.PESO_MAXIMO

        return q + sinal


class SurvivalGate(nn.Module):
    """
    Neuronio de sobrevivencia com PESO MAXIMO FIXO — nao-treinavel.

    APOLO PRIORIZA VIDA A TODO CUSTO.
    Quando vida de Apolo cai abaixo de 95%, este gate aplica um bias
    MASSIVO nos Q-values em direcao a orbe de vida mais proxima.
    Nenhum padrao aprendido pela rede pode superar esse sinal.

    Logica:
      urgencia_vida  = max(0, LIMIAR_VIDA - feat_vida) / LIMIAR_VIDA
                       → 0.0 quando vida >= 95%
                       → 1.0 quando vida = 0% (situacao critica)

      oportunidade   = 1 + bonus quando orbe esta perto E vida baixa
                       → Apolo aprende que orbe ao alcance = agir AGORA

      bias[acao]     = funcao da direcao (feat_dir_orb_x, feat_dir_orb_y)
                       → maior para acoes que apontam para a orbe
                       → inclui dash quando orbe esta distante OU urgencia maxima

      Q_final = Q_dqn + urgencia * oportunidade * bias * PESO_MAXIMO

    PESO_MAXIMO = 300.0 garante que nenhum Q-value aprendido supere o gate.
    O gate eh INVISIVEL para o otimizador — nenhum gradiente passa por ele.
    Ignora completamente a Umbra: a vida e a unica prioridade.
    """

    LIMIAR_VIDA   = 0.95   # Ativa abaixo de 95% da vida (proativo!)
    PESO_MAXIMO   = 300.0  # Domina qualquer Q-value aprendido
    DIST_DASH     = 0.30   # Orbe considerada 'distante' (acima dessa dist normalizada)
    DIST_OPORTUN  = 0.25   # Dist maxima para bonus de oportunidade (orbe ao alcance!)

    def forward(self, q: torch.Tensor, estado: torch.Tensor) -> torch.Tensor:
        """
        q:      (batch, 9) — Q-values do Dueling DQN
        estado: (batch, 40) — tensor de features do estado
        Retorna Q modificado com o sinal de sobrevivencia.
        """
        with torch.no_grad():
            vida   = estado[:, _IDX_VIDA_P]     # (batch,)
            d_orb  = estado[:, _IDX_DIST_ORB]   # (batch,) — 1.0 = longe/inexistente
            ox     = estado[:, _IDX_DIR_ORB_X]  # (batch,)
            oy     = estado[:, _IDX_DIR_ORB_Y]  # (batch,)

            # Urgencia principal: rampa de 0 (vida ok) ate 1 (vida critica)
            urgencia_vida = torch.clamp(
                (self.LIMIAR_VIDA - vida) / self.LIMIAR_VIDA,
                min=0.0, max=1.0
            )  # (batch,)

            # Bonus de oportunidade: orbe perto + vida baixa = AGIR AGORA!
            # Amplifica o sinal quando a orbe esta ao alcance (dist < DIST_OPORTUN)
            # Ensina: esta perto, vai buscar, nao perca a chance!
            orbe_perto = torch.clamp(
                (self.DIST_OPORTUN - d_orb) / self.DIST_OPORTUN,
                min=0.0, max=1.0
            )  # (batch,) — 1.0 quando orbe tocando, 0 quando longe
            bonus_oportunidade = 1.0 + orbe_perto * urgencia_vida * 0.5  # max 1.5x

            urgencia = urgencia_vida * bonus_oportunidade  # urgencia composta

            # Mascara: orbe existe quando dist < 0.99
            # (dist=1.0 significa nenhuma orbe no campo)
            orbe_existe = (d_orb < 0.99).float()  # (batch,)

            # Bias por acao baseado na direcao da orbe
            #   0=cima  1=baixo  2=esq  3=dir
            #   4=cima-esq  5=cima-dir  6=baixo-esq  7=baixo-dir
            #   8=dash
            b0 = torch.relu(-oy)                            # cima
            b1 = torch.relu( oy)                            # baixo
            b2 = torch.relu(-ox)                            # esquerda
            b3 = torch.relu( ox)                            # direita
            b4 = torch.relu(-ox) * torch.relu(-oy)          # cima-esq
            b5 = torch.relu( ox) * torch.relu(-oy)          # cima-dir
            b6 = torch.relu(-ox) * torch.relu( oy)          # baixo-esq
            b7 = torch.relu( ox) * torch.relu( oy)          # baixo-dir
            # Dash: ativa quando orbe distante OU urgencia critica (< 30% vida)
            urgencia_critica = torch.clamp(
                (0.30 - vida) / 0.30, min=0.0, max=1.0
            )  # (batch,) — 1.0 apenas com vida < 30%
            b8 = torch.relu(d_orb - self.DIST_DASH) * urgencia_vida + urgencia_critica * 0.8

            bias = torch.stack(
                [b0, b1, b2, b3, b4, b5, b6, b7, b8], dim=1
            )  # (batch, 9)

            # Sinal final: urgencia_composta * direcao * peso_maximo * so_se_orbe_existe
            sinal = (
                urgencia.unsqueeze(1)      # (batch, 1)
                * bias                     # (batch, 9)
                * self.PESO_MAXIMO
                * orbe_existe.unsqueeze(1) # (batch, 1)
            )

        return q + sinal   # gradiente nao flui pelo sinal (torch.no_grad acima)


# =============================================================================
# REDE NEURAL  —  Dueling DQN com tamanho dinamico
# =============================================================================
class ApoloDQN(nn.Module):
    """
    Dueling DQN com hidden_dim configuravel + SurvivalGate.

    Fluxo:
      Input[40] -> FC[H] + LN + LReLU -> FC[H] + LN + LReLU
        -> Value[H//2 -> 1]  +  Advantage[H//2 -> 9]
        -> Q = V + (A - mean(A))
        -> Q_final = Q + SurvivalGate(Q, estado)  ← peso fixo, nao-treinavel

    SurvivalGate:
      Quando vida < 80% E existe orbe de vida:
        Aplica bias massivo (200.0) em direcao a orbe.
        Nenhum gradiente aprendido supera esse sinal.

    hidden_dim aumenta automaticamente via Neurogenese.
    """

    def __init__(self, hidden_dim: int = 256,
                 input_size: int = INPUT_SIZE,
                 output_size: int = OUTPUT_SIZE):
        super().__init__()
        self.hidden_dim = hidden_dim
        h2 = max(64, hidden_dim // 2)

        self.shared = nn.Sequential(
            nn.Linear(input_size, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.01),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.01),
        )
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_dim, h2),
            nn.LeakyReLU(0.01),
            nn.Linear(h2, 1),
        )
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_dim, h2),
            nn.LeakyReLU(0.01),
            nn.Linear(h2, output_size),
        )

        # Neuronio de sobrevivencia — nao-treinavel, peso maximo fixo
        self.survival_gate = SurvivalGate()

        # Neuronio de evasao de projeteis — nao-treinavel, peso fixo
        self.dodge_gate = DodgeGate()

        # Neuronio de evasao do laser rotativo — nao-treinavel, peso 250
        self.laser_gate = LaserGate()

        self._init_kaiming()

    def _init_kaiming(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='leaky_relu')
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        s   = self.shared(x)
        val = self.value_stream(s)
        adv = self.advantage_stream(s)
        q   = val + (adv - adv.mean(dim=1, keepdim=True))

        # Neuronio de sobrevivencia: vida < 80% → vai para a orbe
        q = self.survival_gate(q, x)

        # Neuronio de evasao: projetil se aproximando → move perpendicular
        q = self.dodge_gate(q, x)

        # Neuronio de evasao do laser: feixe perto → foge perpendicular
        # Peso 250 > DodgeGate 150: laser e fatal e instantaneo
        q = self.laser_gate(q, x)

        return q


# =============================================================================
# REPLAY BUFFERS
# =============================================================================
class PrioritizedReplay:
    """PER: amostragem proporcional ao TD-error."""

    def __init__(self, capacidade=200_000, alpha=0.6, beta=0.4,
                 beta_inc=0.0001, pin=True):
        self.capacidade = capacidade
        self.alpha      = alpha
        self.beta       = beta
        self.beta_inc   = beta_inc
        self.pin        = pin and torch.cuda.is_available()
        self.buffer     = []
        self.prios      = []
        self.pos        = 0
        self.max_prio   = 1.0

    def adicionar(self, s, a, r, s_, done):
        item = (s.cpu().detach(), int(a), float(r), s_.cpu().detach(), float(done))
        if len(self.buffer) < self.capacidade:
            self.buffer.append(item)
            self.prios.append(self.max_prio)
        else:
            self.buffer[self.pos] = item
            self.prios[self.pos]  = self.max_prio
        self.pos = (self.pos + 1) % self.capacidade

    def amostrar(self, batch_size, device):
        n     = len(self.buffer)
        p     = torch.tensor(self.prios[:n], dtype=torch.float32)
        probs = (p ** self.alpha)
        probs = probs / probs.sum()

        idx   = torch.multinomial(probs, batch_size, replacement=False).tolist()
        self.beta = min(1.0, self.beta + self.beta_inc)
        pesos = (n * probs[idx]) ** (-self.beta)
        pesos = pesos / pesos.max()

        s, a, r, s_, d = zip(*[self.buffer[i] for i in idx])
        st  = torch.cat(list(s))
        st_ = torch.cat(list(s_))
        if self.pin:
            st  = st.pin_memory()
            st_ = st_.pin_memory()
        return (
            st.to(device, non_blocking=True),
            torch.tensor(a, dtype=torch.long,    device=device),
            torch.tensor(r, dtype=torch.float32, device=device),
            st_.to(device, non_blocking=True),
            torch.tensor(d, dtype=torch.float32, device=device),
            idx,
            pesos.to(device),
        )

    def atualizar_prioridades(self, indices, td_errors):
        for i, e in zip(indices, td_errors):
            p = (abs(float(e)) + 1e-6) ** self.alpha
            self.prios[i] = p
            if p > self.max_prio:
                self.max_prio = p

    def __len__(self):
        return len(self.buffer)


class MiniReplayBuffer:
    """Buffer simples para uso online no GAME5 (sem overhead de PER)."""

    def __init__(self, capacidade=10_000):
        self.buffer = collections.deque(maxlen=capacidade)

    def adicionar(self, s, a, r, s_, done):
        self.buffer.append((s.cpu().detach(), int(a), float(r),
                            s_.cpu().detach(), float(done)))

    def amostrar(self, batch_size, device):
        am = random.sample(self.buffer, min(batch_size, len(self.buffer)))
        s, a, r, s_, d = zip(*am)
        return (
            torch.cat(list(s)).to(device),
            torch.tensor(a, dtype=torch.long,    device=device),
            torch.tensor(r, dtype=torch.float32, device=device),
            torch.cat(list(s_)).to(device),
            torch.tensor(d, dtype=torch.float32, device=device),
        )

    def __len__(self):
        return len(self.buffer)


# =============================================================================
# AGENTE APOLO  —  Double DQN + Neurogenese
# =============================================================================
class ApoloAgent:
    """
    Agente completo com:
      - Double DQN + target network
      - Neurogenese: cresce automaticamente quando confuso
      - Auto-reset de pesos ao detectar incompatibilidade de arquitetura
    """

    GAMMA        = 0.97
    LR           = 2e-4
    TARGET_UPDATE = 200

    def __init__(self, device=None, batch_size=64,
                 taxa_exploracao=0.50, replay_buffer=None):
        self.device     = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.batch_size = batch_size

        # Carrega (ou cria) configuracao da arquitetura
        self.arq_cfg = GerenciadorArquitetura.carregar()

        self.q_online = ApoloDQN(self.arq_cfg["hidden"]).to(self.device)
        self.q_target = ApoloDQN(self.arq_cfg["hidden"]).to(self.device)
        self.q_target.eval()

        self.optimizer = torch.optim.Adam(self.q_online.parameters(), lr=self.LR)
        self.criterion = nn.SmoothL1Loss(reduction='none')

        self.replay   = replay_buffer or MiniReplayBuffer()
        self.taxa_exp = taxa_exploracao
        self.passos   = 0

        # Neurogenese: acumulador de entropia
        self._entropia_acum  = 0.0
        self._entropia_count = 0

        self._carregar_pesos()
        self._sincronizar_target()

    # ---- Persistencia ------------------------------------------------------
    def _carregar_pesos(self):
        if not os.path.exists(PESOS_FILE):
            return
        try:
            state = torch.load(PESOS_FILE, map_location=self.device, weights_only=True)
            self.q_online.load_state_dict(state)
        except Exception as e:
            # Arquitetura incompativel -> backup + reset automatico
            registrar_erro("APOLO: pesos incompativeis; fazendo backup e reiniciando pesos", e)
            bak = PESOS_FILE.replace(".pt", "_bak_incompat.pt")
            shutil.copy2(PESOS_FILE, bak)
            os.remove(PESOS_FILE)

    def _sincronizar_target(self):
        self.q_target.load_state_dict(self.q_online.state_dict())

    def salvar_pesos(self):
        torch.save(self.q_online.state_dict(), PESOS_FILE)
        GerenciadorArquitetura.salvar(self.arq_cfg)

    # ---- Neurogenese -------------------------------------------------------
    def _avaliar_neurogenese(self, q_vals: torch.Tensor):
        """
        Calcula a entropia dos Q-values (confusao do agente).
        Alta entropia = agente nao tem preferencia clara = confuso.
        Se confuso por JANELA_ENTROPIA passos, cresce a rede.
        """
        with torch.no_grad():
            probs    = torch.softmax(q_vals.float(), dim=-1)
            log_p    = torch.log(probs + 1e-8)
            entropia = -(probs * log_p).sum(dim=-1).mean().item()

        self._entropia_acum  += entropia
        self._entropia_count += 1

        if self._entropia_count >= JANELA_ENTROPIA:
            media = self._entropia_acum / self._entropia_count
            self._entropia_acum  = 0.0
            self._entropia_count = 0

            if media > ENTROPIA_LIMIAR and self.arq_cfg["hidden"] < HIDDEN_MAX:
                # Dispara neurogenese!
                self.arq_cfg = GerenciadorArquitetura.crescer(self.arq_cfg)
                # Reconstroi redes com nova arquitetura
                self.q_online = ApoloDQN(self.arq_cfg["hidden"]).to(self.device)
                self.q_target = ApoloDQN(self.arq_cfg["hidden"]).to(self.device)
                self.q_target.eval()
                self.optimizer = torch.optim.Adam(
                    self.q_online.parameters(), lr=self.LR)
                self._sincronizar_target()
                # Reseta exploracao para redescobrir o ambiente com mais neuronios
                self.taxa_exp = max(self.taxa_exp, 0.40)
                return True  # Cresceu
        return False

    # ---- Inferencia --------------------------------------------------------
    @torch.no_grad()
    def decidir(self, estado: torch.Tensor, acoes_validas: list) -> int:
        if random.random() < self.taxa_exp:
            return random.choice(acoes_validas)
        self.q_online.eval()
        q = self.q_online(estado.to(self.device))[0]
        self._avaliar_neurogenese(q.unsqueeze(0))
        for i in range(OUTPUT_SIZE):
            if i not in acoes_validas:
                q[i] = -1e9
        return int(q.argmax().item())

    @torch.no_grad()
    def decidir_batch(self, tensores: list, acoes_validas_batch: list) -> list:
        stacked = torch.cat(tensores, dim=0).to(self.device)
        self.q_online.eval()
        q_vals = self.q_online(stacked)
        self._avaliar_neurogenese(q_vals)

        acoes = []
        for i, validas in enumerate(acoes_validas_batch):
            if random.random() < self.taxa_exp:
                acoes.append(random.choice(validas))
            else:
                q = q_vals[i].clone()
                for j in range(OUTPUT_SIZE):
                    if j not in validas:
                        q[j] = -1e9
                acoes.append(int(q.argmax().item()))
        return acoes

    # ---- Treinamento -------------------------------------------------------
    def adicionar_transicao(self, s, a, r, s_, done):
        self.replay.adicionar(s, a, r, s_, done)

    def treinar_passo(self, scaler=None) -> float:
        if len(self.replay) < self.batch_size:
            return 0.0

        use_per = isinstance(self.replay, PrioritizedReplay)

        if use_per:
            s, a, r, s_, done, idx, pesos = self.replay.amostrar(
                self.batch_size, self.device)
        else:
            s, a, r, s_, done = self.replay.amostrar(self.batch_size, self.device)
            pesos = torch.ones(len(r), device=self.device)
            idx   = None

        self.q_online.train()

        # Double DQN target
        with torch.no_grad():
            acoes_next = self.q_online(s_).argmax(dim=1, keepdim=True)
            q_next     = self.q_target(s_).gather(1, acoes_next).squeeze(1)
            target     = r + self.GAMMA * q_next * (1.0 - done)

        def _loss():
            q_pred    = self.q_online(s).gather(1, a.unsqueeze(1)).squeeze(1)
            loss_elem = self.criterion(q_pred, target)
            return loss_elem, (loss_elem * pesos).mean()

        if scaler is not None:
            with torch.cuda.amp.autocast(dtype=torch.float16):
                le, lw = _loss()
            self.optimizer.zero_grad()
            scaler.scale(lw).backward()
            scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.q_online.parameters(), 10.0)
            scaler.step(self.optimizer)
            scaler.update()
        else:
            le, lw = _loss()
            self.optimizer.zero_grad()
            lw.backward()
            torch.nn.utils.clip_grad_norm_(self.q_online.parameters(), 10.0)
            self.optimizer.step()

        if use_per and idx is not None:
            self.replay.atualizar_prioridades(idx, le.detach().cpu().tolist())

        self.passos += 1
        if self.passos % self.TARGET_UPDATE == 0:
            self._sincronizar_target()

        return float(lw.item())


# =============================================================================
# VERIFICACAO
# =============================================================================
def verificar_compatibilidade():
    cfg    = GerenciadorArquitetura.carregar()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rede   = ApoloDQN(cfg["hidden"]).to(device)

    # Testa SurvivalGate: simula Apolo com vida critica (50%) e orbe a direita
    t = torch.zeros(1, INPUT_SIZE, device=device)
    t[0, _IDX_VIDA_P]    = 0.50   # 50% vida  (< 80% → gate ativa)
    t[0, _IDX_DIST_ORB]  = 0.40   # orbe a 40% da distancia maxima
    t[0, _IDX_DIR_ORB_X] = 0.85   # orbe fortemente a direita
    t[0, _IDX_DIR_ORB_Y] = 0.20   # levemente abaixo

    with torch.no_grad():
        q = rede(t)

    acao_escolhida = int(q.argmax(dim=1).item())
    nomes_acoes = ['cima','baixo','esq','dir','cima-esq','cima-dir','baixo-esq','baixo-dir','dash']
    n = sum(p.numel() for p in rede.parameters())

    gate_ok = acao_escolhida in [3, 5, 7]  # dir, cima-dir, baixo-dir

    # Teste 2: vida critica (20%) + orbe PERTO (bonus de oportunidade ativo)
    t2 = torch.zeros(1, INPUT_SIZE, device=device)
    t2[0, _IDX_VIDA_P]    = 0.20   # 20% vida — critico
    t2[0, _IDX_DIST_ORB]  = 0.15   # orbe BEM perto (bonus oportunidade ativo!)
    t2[0, _IDX_DIR_ORB_X] = 0.70
    t2[0, _IDX_DIR_ORB_Y] = 0.70
    with torch.no_grad():
        q2 = rede(t2)
    acao2 = int(q2.argmax(dim=1).item())
    gate_ok2 = acao2 in [3, 5, 7]
    return {
        "hidden": cfg["hidden"],
        "params": n,
        "device": str(device),
        "shape_in": tuple(t.shape),
        "shape_out": tuple(q.shape),
        "gate_ok": gate_ok,
        "gate_ok2": gate_ok2,
    }

# =============================================================================
# WORKER ASSÍNCRONO PARA GAME5
# =============================================================================
def motor_cognitivo_worker(fila_in, fila_out, evento_salvar):
    """
    Processo em background para inferência e treinamento contínuo de Apolo.
    Isola o PyTorch do loop de renderização do Pygame.
    """
    import os
    # Suprime logs de inicialização do PyTorch
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    import queue
    import torch
    from qa_logger import instalar_captura_global, instalar_filtro_prints, registrar_erro

    instalar_captura_global()
    instalar_filtro_prints()

    # Garante que o worker use apenas 1 thread de CPU para evitar throttling
    torch.set_num_threads(1)

    device = torch.device("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
    agente = ApoloAgent(device=device, batch_size=64, taxa_exploracao=0.50)
    
    while True:
        try:
            # Se o evento de salvamento foi acionado, salva os pesos
            if evento_salvar.is_set():
                agente.salvar_pesos()
                evento_salvar.clear()

            try:
                # Timeout curto para não travar o evento de salvar
                comando, payload = fila_in.get(timeout=0.016)
                
                if comando == "INFERIR":
                    estado_tensor, acoes_validas = payload
                    # Assegura que o tensor está no formato correto (batch_size=1)
                    if estado_tensor.dim() == 1:
                        estado_tensor = estado_tensor.unsqueeze(0)
                    
                    acao = agente.decidir(estado_tensor, acoes_validas)
                    
                    # Evita encher a fila se o consumidor (GAME5) estiver atrasado
                    while not fila_out.empty():
                        try: fila_out.get_nowait()
                        except: pass
                        
                    fila_out.put(acao)

                elif comando == "TREINAR":
                    s, a, r, s_, d = payload
                    
                    # Ajuste de shape se necessário
                    if s.dim() == 1: s = s.unsqueeze(0)
                    if s_.dim() == 1: s_ = s_.unsqueeze(0)
                    
                    agente.adicionar_transicao(s, a, r, s_, d)
                    
                    # Treina 1 passo a cada adição (se houver batch suficiente)
                    agente.treinar_passo()

            except queue.Empty:
                pass

        except KeyboardInterrupt:
            break
        except Exception as e:
            registrar_erro("Motor cognitivo: erro no worker", e)

if __name__ == "__main__":
    verificar_compatibilidade()
