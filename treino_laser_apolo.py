"""
treino_laser_apolo.py  v3 — Curriculum + 2nd Beam + Fair Transition
=====================================================================
Ambiente de treino headless isolado para APOLO aprender a desviar
do Laser de Sobrecarga da Umbra (Fase 7).

v3 - Correções para superar a Rodada 2+:
  - Transicao justa entre rodadas: beams iniciam 90 graus longe do player
  - Curriculum learning: --curriculum treina fases 1->2->4 progressivamente
  - Feature do 2o feixe mais proximo no tensor (posicao 33)
  - Log de sobrevivencia por rodada individual
  - Mantém toda a arquitetura DQN v2 (replay buffer, target net, Bellman)

Uso:
    python treino_laser_apolo.py                      # 500 ep, todas rodadas
    python treino_laser_apolo.py --curriculum          # 1500 ep com currículo
    python treino_laser_apolo.py --visual              # Com pygame
    python treino_laser_apolo.py --geracoes 2000
    python treino_laser_apolo.py --verificar
"""

import math
import random
import sys
import os
import time
import argparse
import collections

import torch
import torch.nn as nn
import torch.optim as optim

# Garante UTF-8 no terminal Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# =============================================================================
# CONFIGURACAO DO MAPA
# =============================================================================
LARGURA_MAPA     = 1280
ALTURA_MAPA      = 720
VELOCIDADE_APOLO = 4.0
VELOCIDADE_DASH  = 80.0        # pixels de impulso total por dash
DASH_COOLDOWN_FRAMES = 90      # ~1.5s a 60fps (igual ao jogo)

BOSS_POS      = (LARGURA_MAPA // 2, ALTURA_MAPA // 2)
MARGEM_SPAWN  = 120

RODADAS_CONFIG = {
    1: {"num_feixes": 1, "sentido":  1, "giro_total": math.pi * 2},
    2: {"num_feixes": 2, "sentido": -1, "giro_total": math.pi * 2},
    3: {"num_feixes": 4, "sentido":  1, "giro_total": math.pi * 0.8},
    4: {"num_feixes": 6, "sentido": -1, "giro_total": math.pi * 0.8},
}
DURACAO_CARGA_MS   = 1500
DURACAO_DISPARO_MS = 4000
RAIO_MORTE_LASER   = 50        # pixels — raio de hitbox do feixe

# =============================================================================
# REDE NEURAL — idêntica ao GAME5.py
# =============================================================================
class ApoloDQN(nn.Module):
    def __init__(self, input_size: int = 40, output_size: int = 9):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.LeakyReLU(),
            nn.Linear(128, 64),
            nn.LeakyReLU(),
            nn.Linear(64, output_size),
        )

    def forward(self, x):
        return self.net(x)


# =============================================================================
# REPLAY BUFFER
# =============================================================================
class ReplayBuffer:
    """Buffer circular de experiências (s, a, r, s', done)."""

    def __init__(self, capacidade: int = 50_000):
        self.buffer = collections.deque(maxlen=capacidade)

    def adicionar(self, estado, acao, recompensa, prox_estado, done):
        self.buffer.append((estado, acao, recompensa, prox_estado, done))

    def amostrar(self, batch_size: int):
        amostra = random.sample(self.buffer, batch_size)
        estados, acoes, recompensas, prox_estados, dones = zip(*amostra)
        return (
            torch.cat(estados),                                          # (B, 40)
            torch.tensor(acoes,      dtype=torch.long),                  # (B,)
            torch.tensor(recompensas,dtype=torch.float32),               # (B,)
            torch.cat(prox_estados),                                     # (B, 40)
            torch.tensor(dones,      dtype=torch.float32),               # (B,)
        )

    def __len__(self):
        return len(self.buffer)


# =============================================================================
# AGENTE APOLO — DQN com Replay Buffer e Target Network
# =============================================================================
class ApoloTreinoLaser:
    """
    DQN completo para o treino laser:
    - Rede principal (online)  para inferência e treinamento
    - Rede alvo   (target)    para calcular os alvos de Bellman
    - Replay Buffer             para quebrar correlação temporal
    """

    ARQUIVO_PESOS    = "apolo_memoria_dqn.pt"
    INPUT_SIZE       = 40
    OUTPUT_SIZE      = 9
    GAMMA            = 0.97     # fator de desconto (preza futuro próximo)
    BATCH_SIZE       = 64
    LR               = 5e-4
    TARGET_UPDATE_EP = 200      # atualiza target network a cada N passos globais

    def __init__(self, taxa_exploracao: float = 0.80):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # -- Redes --
        self.q_online = ApoloDQN(self.INPUT_SIZE, self.OUTPUT_SIZE).to(self.device)
        self.q_target = ApoloDQN(self.INPUT_SIZE, self.OUTPUT_SIZE).to(self.device)

        self.optimizer = optim.Adam(self.q_online.parameters(), lr=self.LR)
        self.criterion = nn.SmoothL1Loss()  # Huber Loss (mais estável que MSE)

        self.replay   = ReplayBuffer(capacidade=50_000)
        self.taxa_exp = taxa_exploracao
        self.passos   = 0         # contador global de steps

        self._carregar_pesos()
        self._sincronizar_target()  # Target começa igual à online

    # -- Persistência -------------------------------------------------------
    def _carregar_pesos(self):
        if os.path.exists(self.ARQUIVO_PESOS):
            try:
                self.q_online.load_state_dict(
                    torch.load(self.ARQUIVO_PESOS,
                               map_location=self.device,
                               weights_only=True)
                )
                print(f"[APOLO] Pesos carregados de '{self.ARQUIVO_PESOS}'")
            except Exception as e:
                print(f"[APOLO] Falha ao carregar pesos: {e} -- iniciando zerado.")
        else:
            print("[APOLO] Nenhum arquivo de pesos -- iniciando zerado.")

    def _sincronizar_target(self):
        """Copia pesos da rede online para a rede alvo (hard update)."""
        self.q_target.load_state_dict(self.q_online.state_dict())

    def salvar_pesos(self):
        torch.save(self.q_online.state_dict(), self.ARQUIVO_PESOS)

    # -- Inferência ----------------------------------------------------------
    def decidir(self, tensor: torch.Tensor, acoes_validas: list) -> int:
        if random.random() < self.taxa_exp:
            return random.choice(acoes_validas)

        with torch.no_grad():
            self.q_online.eval()
            q_vals = self.q_online(tensor.to(self.device))[0]
            q_masked = q_vals.clone()
            for i in range(self.OUTPUT_SIZE):
                if i not in acoes_validas:
                    q_masked[i] = -1e9
            return int(torch.argmax(q_masked).item())

    # -- Aprendizado ---------------------------------------------------------
    def registrar_e_treinar(self, s, a, r, s_prox, done):
        """
        Adiciona (s,a,r,s',done) ao replay buffer e,
        se o buffer tiver amostras suficientes, faz um passo de treino.
        """
        self.replay.adicionar(
            s.to("cpu"), a, r,
            s_prox.to("cpu"), float(done)
        )
        self.passos += 1

        # Começa a treinar só após acumular um batch completo
        if len(self.replay) < self.BATCH_SIZE:
            return

        estados, acoes, recompensas, prox_estados, dones = self.replay.amostrar(self.BATCH_SIZE)
        estados      = estados.to(self.device)
        acoes        = acoes.to(self.device)
        recompensas  = recompensas.to(self.device)
        prox_estados = prox_estados.to(self.device)
        dones        = dones.to(self.device)

        # Q-values da rede online para os estados atuais
        self.q_online.train()
        q_current = self.q_online(estados)
        # Extrai o Q-value da ação realmente tomada
        q_atual = q_current.gather(1, acoes.unsqueeze(1)).squeeze(1)

        # Alvo de Bellman com a rede target (sem gradiente)
        with torch.no_grad():
            self.q_target.eval()
            q_next       = self.q_target(prox_estados)
            max_q_next   = q_next.max(1)[0]
            q_alvo       = recompensas + self.GAMMA * max_q_next * (1 - dones)

        loss = self.criterion(q_atual, q_alvo)
        self.optimizer.zero_grad()
        loss.backward()
        # Gradient clipping (evita explosão de gradiente)
        torch.nn.utils.clip_grad_norm_(self.q_online.parameters(), max_norm=10.0)
        self.optimizer.step()

        # Hard update da target network a cada N passos
        if self.passos % self.TARGET_UPDATE_EP == 0:
            self._sincronizar_target()


# =============================================================================
# AMBIENTE DO LASER
# =============================================================================
class LaserEnv:
    """
    Simula apenas o Laser de Sobrecarga da Umbra (4 rodadas, 1->2->4->6 feixes).
    Boss parado no centro. Sem projéteis, ratos ou orbes.
    """

    MAX_HITS = 3  # hits antes de encerrar episódio

    def __init__(self):
        self.rodada_max = 4  # pode ser alterado pelo loop de treino (curriculum)
        self.reset()

    # -- Reset ---------------------------------------------------------------
    def reset(self) -> torch.Tensor:
        # Spawn aleatório longe das bordas e do boss
        while True:
            ax = random.randint(MARGEM_SPAWN, LARGURA_MAPA - MARGEM_SPAWN)
            ay = random.randint(MARGEM_SPAWN, ALTURA_MAPA  - MARGEM_SPAWN)
            if math.hypot(ax - BOSS_POS[0], ay - BOSS_POS[1]) > 200:
                break

        self.apolo_x = float(ax)
        self.apolo_y = float(ay)
        self._heading = (1.0, 0.0)

        # Dash com cooldown real
        self.dash_cooldown = 0

        self.tempo_ms = 0
        self.dt_ms    = 16

        self.hits     = 0
        self.done     = False

        self.ultima_dist_feixe      = None
        self.laser_estava_carregando= False

        self.recompensa_acumulada = 0.0
        self.rodadas_sobrevividas  = 0
        # rodada_max é preservado entre resets (curriculum o define externamente)

        self.laser = {
            'tempo_inicio':         0,
            'fase':                 'carregando',
            'rodada':               1,
            'duracao_carga':        DURACAO_CARGA_MS,
            'duracao_disparo':      DURACAO_DISPARO_MS,
            'tempo_inicio_disparo': None,
            'angulo_base_inicio':   random.uniform(0, math.pi * 2),
        }

        return self._montar_tensor()

    # -- Ação -> Movimento ---------------------------------------------------
    def _aplicar_acao(self, acao: int):
        dx, dy     = 0.0, 0.0
        usar_dash  = False

        if   acao == 0: dy = -1.0
        elif acao == 1: dy =  1.0
        elif acao == 2: dx = -1.0
        elif acao == 3: dx =  1.0
        elif acao == 4: dx, dy = -1.0, -1.0
        elif acao == 5: dx, dy =  1.0, -1.0
        elif acao == 6: dx, dy = -1.0,  1.0
        elif acao == 7: dx, dy =  1.0,  1.0
        elif acao == 8: usar_dash = True

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        if usar_dash and self.dash_cooldown == 0:
            hdx, hdy = self._heading
            self.apolo_x  += hdx * VELOCIDADE_DASH
            self.apolo_y  += hdy * VELOCIDADE_DASH
            self.dash_cooldown = DASH_COOLDOWN_FRAMES
        else:
            self.apolo_x += dx * VELOCIDADE_APOLO
            self.apolo_y += dy * VELOCIDADE_APOLO
            if dx != 0 or dy != 0:
                mag = math.hypot(dx, dy)
                self._heading = (dx / max(mag, 1e-9), dy / max(mag, 1e-9))

        # Regenera cooldown do dash
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        # Clamp
        self.apolo_x = max(10.0, min(LARGURA_MAPA - 10.0, self.apolo_x))
        self.apolo_y = max(10.0, min(ALTURA_MAPA  - 10.0, self.apolo_y))

    # -- Física do Laser -----------------------------------------------------
    def _geometria_laser(self):
        laser = self.laser
        cfg   = RODADAS_CONFIG[laser['rodada']]
        num_f = cfg['num_feixes']
        sent  = cfg['sentido']
        giro  = cfg['giro_total']

        prog = 0.0
        if laser['fase'] == 'disparando' and laser['tempo_inicio_disparo'] is not None:
            t    = self.tempo_ms - laser['tempo_inicio_disparo']
            prog = min(1.0, t / laser['duracao_disparo'])

        ang_base = laser['angulo_base_inicio'] + giro * prog * sent
        ox, oy   = BOSS_POS
        comp     = 2500
        feixes   = []
        for i in range(num_f):
            ang = ang_base + i * ((math.pi * 2) / num_f)
            feixes.append((ang,
                           ox + math.cos(ang) * comp,
                           oy + math.sin(ang) * comp))
        return feixes, prog

    def _dist_perp(self, ang, fx, fy, px, py):
        ox, oy = BOSS_POS
        num  = abs((fy - oy) * px - (fx - ox) * py + fx * oy - fy * ox)
        den  = math.hypot(fy - oy, fx - ox)
        return num / den if den > 0 else 9999.0

    def _em_frente(self, ang, px, py):
        ox, oy = BOSS_POS
        return ((px - ox) * math.cos(ang) + (py - oy) * math.sin(ang)) > 0

    # -- Tensor de 40 Features -----------------------------------------------
    def _montar_tensor(self) -> torch.Tensor:
        px, py = self.apolo_x, self.apolo_y
        bx, by = BOSS_POS

        # [0-3] Posicoes
        f_px = px / LARGURA_MAPA
        f_py = py / ALTURA_MAPA
        f_bx = bx / LARGURA_MAPA
        f_by = by / ALTURA_MAPA

        # [4-5] Vida (neutro)
        f_vp = 1.0
        f_vb = 1.0

        # [6-10] Bordas
        mp = 100
        f_be = min(1.0, px / mp)
        f_bd = min(1.0, (LARGURA_MAPA - px) / mp)
        f_bc = min(1.0, py / mp)
        f_bb = min(1.0, (ALTURA_MAPA - py) / mp)
        f_canto = 1.0 if (
            (px < mp and py < mp) or
            (px > LARGURA_MAPA - mp and py < mp) or
            (px < mp and py > ALTURA_MAPA - mp) or
            (px > LARGURA_MAPA - mp and py > ALTURA_MAPA - mp)
        ) else 0.0

        # [11-13] Projeteis (neutro)
        f_dp = 1.0; f_dxp = 0.0; f_dyp = 0.0

        # [14] Dash cooldown (0=disponivel, 1=em cooldown)
        f_cd   = 1.0 if self.dash_cooldown > 0 else 0.0

        # [15] Velocidade
        f_vel  = VELOCIDADE_APOLO / 15.0

        # [16] Orbes (neutro)
        f_orb  = 0.0

        # [17] Velocidade boss (neutro)
        f_vb2  = 0.0

        # [18-26] Features do Laser
        f_lfase   = 0.0; f_lrod  = 0.0; f_lprog = 0.0
        f_lfeixes = 0.0; f_lsent = 0.0; f_lvel  = 0.0
        f_lang    = 0.0; f_ldist = 1.0; f_ltempo = 0.0  # f_ltempo = cos(ang), 0 quando inativo

        # [30-33] Features geometricas do laser (identicas ao GAME5.py)
        f_fugax = 0.0; f_fugay = 0.0; f_zona  = 0.0
        f_dist2 = -1.0   # signed approach 2o feixe: -1 = seguro (sem 2o feixe)


        laser    = self.laser
        rodada   = laser['rodada']
        cfg      = RODADAS_CONFIG[rodada]
        num_f    = cfg['num_feixes']
        sentido  = cfg['sentido']
        giro     = cfg['giro_total']

        menor_dist_global = float('inf')
        ang_proximo_global = 0.0

        if laser['fase'] == 'carregando':
            f_lfase   = 0.5
            t_c       = self.tempo_ms - laser['tempo_inicio']
            f_lprog   = min(1.0, t_c / laser['duracao_carga'])
            f_lrod    = rodada / 4.0
            f_lfeixes = num_f / 6.0
            f_lsent   = float(sentido)

        elif laser['fase'] == 'disparando' and laser['tempo_inicio_disparo'] is not None:
            f_lfase   = 1.0
            t_d       = self.tempo_ms - laser['tempo_inicio_disparo']
            f_lprog   = min(1.0, t_d / laser['duracao_disparo'])
            f_lrod    = rodada / 4.0
            f_lfeixes = num_f / 6.0
            f_lsent   = float(sentido)

            vel_ang      = giro / (laser['duracao_disparo'] / 1000.0)
            f_lvel       = min(1.0, abs(vel_ang) / (2 * math.pi))

            # Escaneia todos os feixes e coleta (dist, ang) dos que estao na frente
            feixes, _    = self._geometria_laser()
            dists_feixes = []
            for ang_f, fx, fy in feixes:
                if not self._em_frente(ang_f, px, py):
                    continue
                dist_f = self._dist_perp(ang_f, fx, fy, px, py)
                dists_feixes.append((dist_f, ang_f))

            # Ordena por distancia: 1o e 2o feixes na frente
            dists_feixes.sort(key=lambda x: x[0])
            if dists_feixes:
                menor_dist_global  = dists_feixes[0][0]
                ang_proximo_global = dists_feixes[0][1]

            f_ldist = min(1.0, menor_dist_global / 400.0)

            # [24] Signed approach angle: + = feixe vindo em minha direcao, - = se afastando
            # Nao ambiguo (diferente do sin). Unico para qualquer angulo do espaco.
            ang_p   = math.atan2(py - BOSS_POS[1], px - BOSS_POS[0])
            diff_1  = ang_p - ang_proximo_global
            while diff_1 >  math.pi: diff_1 -= 2 * math.pi
            while diff_1 < -math.pi: diff_1 += 2 * math.pi
            f_lang  = max(-1.0, min(1.0, (diff_1 * sentido) / math.pi))  # [-1,1]

            # [26] cos do angulo do feixe mais proximo (par com sin implicito em fuga_x/y)
            f_ltempo = math.cos(ang_proximo_global)

            # [30-31] Vetor de fuga perpendicular ao feixe
            ang_fuga = ang_proximo_global + (math.pi / 2) * sentido
            f_fugax  = math.cos(ang_fuga)
            f_fugay  = math.sin(ang_fuga)

            # [32] in_sweep_zone: 1 se o laser AINDA VAI VARRER minha posicao angular
            # Critico para rodadas 3 e 4 (varredura parcial de 144 deg):
            # se estou fora da zona de varredura restante, posso relaxar
            ang_restante = giro * (1.0 - f_lprog)
            diff_sweep   = diff_1 * sentido
            if diff_sweep < 0: diff_sweep += 2 * math.pi
            f_zona = 1.0 if 0 < diff_sweep <= ang_restante else 0.0

            # [33] signed approach do 2o feixe (timing do 2o perigo)
            if len(dists_feixes) >= 2:
                ang_2nd = dists_feixes[1][1]
                diff_2  = ang_p - ang_2nd
                while diff_2 >  math.pi: diff_2 -= 2 * math.pi
                while diff_2 < -math.pi: diff_2 += 2 * math.pi
                f_dist2 = max(-1.0, min(1.0, (diff_2 * sentido) / math.pi))
            else:
                f_dist2 = -1.0  # sem 2o feixe = safe

        # [27-29] Orbes (neutro)
        f_orbd = 1.0; f_ox = 0.0; f_oy = 0.0

        # [34-39] Armadilhas (laser=1)
        f_arm = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0]

        features = [
            f_px, f_py, f_bx, f_by,             # 0-3
            f_vp, f_vb,                           # 4-5
            f_be, f_bd, f_bc, f_bb, f_canto,     # 6-10
            f_dp, f_dxp, f_dyp, f_cd, f_vel,     # 11-15
            f_orb, f_vb2,                         # 16-17
            f_lfase, f_lrod, f_lprog,             # 18-20
            f_lfeixes, f_lsent,                   # 21-22
            f_lvel, f_lang,                       # 23-24
            f_ldist, f_ltempo,                    # 25-26
            f_orbd, f_ox, f_oy,                  # 27-29
            f_fugax, f_fugay, f_zona, f_dist2,   # 30-33  <-- 2o feixe aqui!
        ] + f_arm                                 # 34-39

        assert len(features) == 40, f"Tensor com {len(features)} features (esperado 40)!"
        dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.tensor(features, dtype=torch.float32, device=dev).unsqueeze(0)

    # -- Step: avança 1 frame ------------------------------------------------
    def step(self, acao: int):
        self._aplicar_acao(acao)
        self.tempo_ms += self.dt_ms

        laser = self.laser
        px, py = self.apolo_x, self.apolo_y
        rodada = laser['rodada']
        recomp = 0.0

        if laser['fase'] == 'carregando':
            t_c = self.tempo_ms - laser['tempo_inicio']

            # Transita para disparando
            if t_c >= laser['duracao_carga']:
                laser['fase'] = 'disparando'
                laser['tempo_inicio_disparo'] = self.tempo_ms
                self.laser_estava_carregando  = True

            # Penalidade de borda durante carga
            if px < MARGEM_SPAWN or px > LARGURA_MAPA - MARGEM_SPAWN or \
               py < MARGEM_SPAWN or py > ALTURA_MAPA - MARGEM_SPAWN:
                recomp -= 5.0

            # Qualidade do dash durante carga
            prog_c = min(1.0, t_c / laser['duracao_carga'])
            if acao == 8:
                recomp += 15.0 if prog_c >= 0.75 else -8.0

            # Sobrevivência base durante carga
            recomp += 0.2

        elif laser['fase'] == 'disparando':
            t_d   = self.tempo_ms - laser['tempo_inicio_disparo']
            prog  = min(1.0, t_d / laser['duracao_disparo'])
            feixes, _ = self._geometria_laser()

            # Feixe mais próximo
            menor_dist   = float('inf')
            ang_mp       = 0.0
            em_perigo    = False

            for ang, fx, fy in feixes:
                if not self._em_frente(ang, px, py):
                    continue
                dist = self._dist_perp(ang, fx, fy, px, py)
                if dist < menor_dist:
                    menor_dist = dist
                    ang_mp     = ang
                    em_perigo  = True

            # Bônus de transição limpa (carga -> disparo fora do caminho)
            if self.laser_estava_carregando:
                self.laser_estava_carregando = False
                if not em_perigo or menor_dist > RAIO_MORTE_LASER + 20:
                    recomp += 50.0    # Saiu do caminho a tempo
                else:
                    recomp -= 40.0    # Ficou na linha de fogo

            # Dense reward: delta de distância (guia de migalhas)
            if em_perigo:
                if self.ultima_dist_feixe is not None:
                    delta = menor_dist - self.ultima_dist_feixe
                    if abs(delta) < 80:              # ignora teleports absurdos
                        recomp += delta * 2.5        # afastar +, aproximar -
                self.ultima_dist_feixe = menor_dist

                # Zonas de segurança
                if menor_dist <= RAIO_MORTE_LASER:
                    recomp -= 80.0               # HIT
                    self.hits += 1
                elif menor_dist < 70:
                    recomp -= 6.0                # Zona crítica
                elif menor_dist < 130:
                    recomp -= 1.0                # Zona de alerta
                else:
                    recomp += 3.0                # Zona segura
            else:
                # Fora de todos os feixes: recompensa de segurança
                recomp += 1.0
                self.ultima_dist_feixe = None

            # Penalidade de borda durante disparo
            dist_borda = min(px, py, LARGURA_MAPA - px, ALTURA_MAPA - py)
            if dist_borda < 80:
                recomp -= 15.0

            # Sobrevivência base
            recomp += 0.5

            # Fim de rodada
            if t_d >= laser['duracao_disparo']:
                self.rodadas_sobrevividas += 1
                marcos = {1: 60.0, 2: 100.0, 3: 180.0, 4: 400.0}
                recomp += marcos.get(rodada, 0.0)

                if rodada < self.rodada_max:
                    # TRANSICAO JUSTA: beams da prox. rodada iniciam 90° longe do player
                    # Evita que o agente morra instantaneamente na transição
                    ang_player_boss = math.atan2(
                        py - BOSS_POS[1], px - BOSS_POS[0]
                    )
                    cfg_next     = RODADAS_CONFIG[rodada + 1]
                    sent_prox    = cfg_next['sentido']
                    # Coloca o 1o feixe da próxima rodada perpendicular ao player
                    angulo_seguro = ang_player_boss + (math.pi / 2) * sent_prox
                    self.laser = {
                        'tempo_inicio':         self.tempo_ms,
                        'fase':                 'carregando',
                        'rodada':               rodada + 1,
                        'duracao_carga':        DURACAO_CARGA_MS,
                        'duracao_disparo':      DURACAO_DISPARO_MS,
                        'tempo_inicio_disparo': None,
                        'angulo_base_inicio':   angulo_seguro,
                    }
                    self.ultima_dist_feixe = None
                else:
                    self.done = True     # todas as 4 rodadas sobrevividas!

        # Termina por hits
        if self.hits >= self.MAX_HITS:
            recomp    -= 100.0
            self.done  = True

        # Timeout
        if self.tempo_ms > 70_000:
            self.done = True

        self.recompensa_acumulada += recomp
        return self._montar_tensor(), recomp, self.done

    # -- Ações válidas (mesma lógica do GAME5.py) ----------------------------
    def acoes_validas(self) -> list:
        px, py  = self.apolo_x, self.apolo_y
        m       = 80
        validas = list(range(9))

        if px < m and 2 in validas:                                        validas.remove(2)
        if px > LARGURA_MAPA - m and 3 in validas:                        validas.remove(3)
        if py < m and 0 in validas:                                        validas.remove(0)
        if py > ALTURA_MAPA - m  and 1 in validas:                        validas.remove(1)
        if (px < m or py < m) and 4 in validas:                           validas.remove(4)
        if (px > LARGURA_MAPA - m or py < m) and 5 in validas:            validas.remove(5)
        if (px < m or py > ALTURA_MAPA - m) and 6 in validas:             validas.remove(6)
        if (px > LARGURA_MAPA - m or py > ALTURA_MAPA - m) and 7 in validas: validas.remove(7)

        return validas if validas else [8]


# =============================================================================
# RENDERIZADOR VISUAL (--visual)
# =============================================================================
class RenderizadorLaser:
    ESCALA = 0.75

    def __init__(self):
        import pygame
        pygame.init()
        self.screen = pygame.display.set_mode((
            int(LARGURA_MAPA * self.ESCALA),
            int(ALTURA_MAPA  * self.ESCALA)
        ))
        pygame.display.set_caption("APOLO v2 - Treino Laser")
        self.fonte  = pygame.font.SysFont("consolas", 16)
        self.clock  = pygame.time.Clock()
        self.pygame = pygame

    def desenhar(self, env, agente, episodio, total, hist_sv, eps):
        pg = self.pygame
        s  = self.screen
        E  = self.ESCALA

        for ev in pg.event.get():
            if ev.type == pg.QUIT:
                pg.quit(); sys.exit()

        s.fill((5, 5, 20))
        ox = int(BOSS_POS[0] * E)
        oy = int(BOSS_POS[1] * E)

        # Laser
        if env.laser['fase'] in ('carregando', 'disparando'):
            feixes, _ = env._geometria_laser()
            laser     = env.laser

            if laser['fase'] == 'carregando':
                t_c  = env.tempo_ms - laser['tempo_inicio']
                prog = min(1.0, t_c / laser['duracao_carga'])
                for ang, fx, fy in feixes:
                    r = int(60 + 120 * prog)
                    pg.draw.line(s, (r, 0, 0), (ox, oy),
                                 (int(fx * E), int(fy * E)), 1)
                raio = int(12 + 8 * prog + 2 * math.sin(env.tempo_ms * 0.01))
                pg.draw.circle(s, (200, 0, 0), (ox, oy), raio, 2)
                pg.draw.circle(s, (255, 60, 60), (ox, oy), raio // 2)
            else:
                for ang, fx, fy in feixes:
                    pg.draw.line(s, (100, 0, 0), (ox, oy),
                                 (int(fx * E), int(fy * E)), 5)
                    pg.draw.line(s, (220, 20, 20), (ox, oy),
                                 (int(fx * E), int(fy * E)), 2)
                    pg.draw.line(s, (255, 150, 0), (ox, oy),
                                 (int(fx * E), int(fy * E)), 1)

        # Boss
        pg.draw.circle(s, (160, 0, 200), (ox, oy), 22)
        pg.draw.circle(s, (255, 80, 255), (ox, oy), 12)

        # Apolo
        ax    = int(env.apolo_x * E)
        ay    = int(env.apolo_y * E)
        cor_a = (0, 200, 255) if env.hits == 0 else \
                (255, 200, 0) if env.hits == 1 else (255, 80, 80)
        pg.draw.circle(s, cor_a, (ax, ay), 13)
        pg.draw.circle(s, (255, 255, 255), (ax, ay), 6)

        # HUD
        rodada = env.laser['rodada']
        fase   = env.laser['fase']
        taxa   = sum(hist_sv[-50:]) / max(1, len(hist_sv[-50:])) * 100

        hud = [
            f"Episodio:  {episodio} / {total}",
            f"Laser:     Rod {rodada}/4 | {fase}",
            f"Hits:      {env.hits}/{env.MAX_HITS}",
            f"Recomp:    {env.recompensa_acumulada:.1f}",
            f"Sobreviv.: {taxa:.1f}%  (ult. 50)",
            f"Epsilon:   {eps:.3f}",
            f"Buffer:    {len(agente.replay)} transicoes",
        ]
        for i, txt in enumerate(hud):
            surf = self.fonte.render(txt, True, (200, 225, 255))
            s.blit(surf, (8, 8 + i * 20))

        pg.display.flip()
        self.clock.tick(60)


# =============================================================================
# LOOP PRINCIPAL DE TREINO
# =============================================================================
def treinar(num_geracoes: int = 500, visual: bool = False,
            salvar_intervalo: int = 10, curriculum: bool = False):
    """
    curriculum=True: progressivamente desafia rodadas mais difíceis.
      ep 1 ~ 33%:    apenas Rodada 1 (1 feixe)  — aprende desvio básico
      ep 34% ~ 66%:  Rodadas 1-2 (1+2 feixes)   — aprende inversão de sentido
      ep 67% ~ 100%: Rodadas 1-4 (completo)      — desafio final
    """
    env          = LaserEnv()
    agente       = ApoloTreinoLaser()
    renderizador = RenderizadorLaser() if visual else None

    hist_recomp   = []
    hist_sv       = []    # 1 = sobreviveu 4 rodadas, 0 = nao
    hist_rod      = {1: [], 2: [], 3: [], 4: []}  # sv por rodada individual
    melhor_recomp = -float('inf')
    melhor_rodada = 0

    # Limites de currículo
    fase1_fim  = num_geracoes // 3
    fase2_fim  = (num_geracoes * 2) // 3

    print("\n" + "=" * 60)
    print("  TREINO LASER v3 -- APOLO  (Curriculum + 2nd Beam)")
    print("=" * 60)
    print(f"  Geracoes:      {num_geracoes}")
    print(f"  Visual:        {'SIM' if visual else 'NAO (headless)'}")
    print(f"  Dispositivo:   {agente.device}")
    print(f"  Replay buffer: 50.000 transicoes | batch = 64")
    print(f"  Epsilon:       0.80 -> 0.10 (decay 0.998/ep)")
    if curriculum:
        print(f"  CURRICULUM:    ep 1-{fase1_fim} Rod1 | ep {fase1_fim+1}-{fase2_fim} Rod1-2 | ep {fase2_fim+1}+ Rod1-4")
    print("=" * 60 + "\n")

    inicio = time.time()

    for ep in range(1, num_geracoes + 1):
        # -- Curriculum: define rodada máxima do episódio ----------------------
        if curriculum:
            if ep <= fase1_fim:
                env.rodada_max = 1    # só Rodada 1
            elif ep <= fase2_fim:
                env.rodada_max = 2    # Rodadas 1-2
            else:
                env.rodada_max = 4    # completo
        else:
            env.rodada_max = 4        # sempre completo

        s = env.reset()

        # Epsilon annealing lento (0.998 por ep, min 0.10)
        agente.taxa_exp = max(0.10, 0.80 * (0.998 ** ep))

        while not env.done:
            acoes = env.acoes_validas()
            acao  = agente.decidir(s, acoes)

            s_prox, r, done = env.step(acao)
            agente.registrar_e_treinar(s, acao, r, s_prox, done)

            s = s_prox

        # Registros
        hist_recomp.append(env.recompensa_acumulada)
        hist_sv.append(1 if env.rodadas_sobrevividas >= env.rodada_max else 0)

        # Rastreia sobrevivência por rodada individual
        for r_idx in range(1, 5):
            hist_rod[r_idx].append(1 if env.rodadas_sobrevividas >= r_idx else 0)

        if env.recompensa_acumulada > melhor_recomp:
            melhor_recomp = env.recompensa_acumulada
        if env.rodadas_sobrevividas > melhor_rodada:
            melhor_rodada = env.rodadas_sobrevividas

        # Log a cada 10 ep
        if ep % 10 == 0 or ep == 1:
            ult50    = hist_recomp[-50:]
            media    = sum(ult50) / len(ult50)
            taxa_sv  = sum(hist_sv[-50:]) / max(1, len(hist_sv[-50:])) * 100
            elapsed  = time.time() - inicio
            ep_s     = ep / max(1.0, elapsed)
            buf_sz   = len(agente.replay)

            # Sobrevivencia por rodada (ult. 50)
            sv_r = {r: sum(hist_rod[r][-50:]) / max(1, len(hist_rod[r][-50:])) * 100
                    for r in range(1, 5)}

            fase_curr = ("Rod1" if curriculum and ep <= fase1_fim else
                         "Rod1-2" if curriculum and ep <= fase2_fim else "Rod1-4")

            print(
                f"[Ep {ep:>5}/{fase_curr}] "
                f"Recomp:{env.recompensa_acumulada:>8.1f} | "
                f"Med:{media:>8.1f} | "
                f"Rod:{env.rodadas_sobrevividas}/4 | "
                f"Sv%: R1={sv_r[1]:.0f} R2={sv_r[2]:.0f} R3={sv_r[3]:.0f} R4={sv_r[4]:.0f} | "
                f"eps:{agente.taxa_exp:.3f} buf:{buf_sz:>5} {ep_s:.1f}ep/s"
            )

        # Salva pesos
        if ep % salvar_intervalo == 0:
            agente.salvar_pesos()
            print(f"  [OK] Pesos salvos  (ep {ep})")

        # Render
        if renderizador:
            renderizador.desenhar(env, agente, ep, num_geracoes,
                                  hist_sv, agente.taxa_exp)

    # Salvamento final
    agente.salvar_pesos()
    dur    = time.time() - inicio
    taxa_f = sum(hist_sv[-100:]) / max(1, len(hist_sv[-100:])) * 100
    sv_r_f = {r: sum(hist_rod[r][-100:]) / max(1, len(hist_rod[r][-100:])) * 100
              for r in range(1, 5)}

    print("\n" + "=" * 60)
    print("  TREINO CONCLUIDO!")
    print("=" * 60)
    print(f"  Total episodios:    {num_geracoes}")
    print(f"  Duracao:            {dur:.1f}s  ({dur/60:.1f} min)")
    print(f"  Melhor rodada:      {melhor_rodada}/4")
    print(f"  Melhor recompensa:  {melhor_recomp:.1f}")
    print(f"  Taxa sv completa:   {taxa_f:.1f}%  (ult. 100)")
    print(f"  Rod 1 sv:  {sv_r_f[1]:.1f}%  | Rod 2 sv: {sv_r_f[2]:.1f}%")
    print(f"  Rod 3 sv:  {sv_r_f[3]:.1f}%  | Rod 4 sv: {sv_r_f[4]:.1f}%")
    print(f"  Pesos salvos em:    apolo_memoria_dqn.pt")
    print("=" * 60)


# =============================================================================
# VERIFICACAO RAPIDA
# =============================================================================
def verificar_tensor():
    print("[VERIFICAR] Montando tensor de teste...")
    env = LaserEnv()
    t   = env._montar_tensor()
    assert t.shape == (1, 40), f"Shape errado: {t.shape}"
    print(f"  Shape: {t.shape} -- OK")

    print("[VERIFICAR] Carregando rede e testando forward pass...")
    agente = ApoloTreinoLaser(taxa_exploracao=0.0)
    with torch.no_grad():
        agente.q_online.eval()
        q = agente.q_online(t)
    assert q.shape == (1, 9)
    print(f"  Output: {q.shape} -- OK")
    print(f"  Q-values: {[round(v, 3) for v in q[0].tolist()]}")
    print("[VERIFICAR] Compativel com GAME5.py -- OK\n")


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Treino isolado Apolo x Laser (DQN v3 - Curriculum)"
    )
    parser.add_argument("--visual",     action="store_true",
                        help="Ativa renderizacao pygame")
    parser.add_argument("--geracoes",   type=int, default=500,
                        help="Numero de episodios (padrao: 500)")
    parser.add_argument("--salvar",     type=int, default=10,
                        help="Salva pesos a cada N episodios (padrao: 10)")
    parser.add_argument("--verificar",  action="store_true",
                        help="Verifica tensor/pesos e sai")
    parser.add_argument("--curriculum", action="store_true",
                        help="Treino progressivo: Rod1 -> Rod1-2 -> Rod1-4")
    args = parser.parse_args()

    if args.verificar:
        verificar_tensor()
        sys.exit(0)

    if args.visual:
        try:
            import pygame
        except ImportError:
            print("[ERRO] pygame nao instalado: pip install pygame")
            sys.exit(1)

    treinar(
        num_geracoes    = args.geracoes,
        visual          = args.visual,
        salvar_intervalo= args.salvar,
        curriculum      = args.curriculum,
    )
