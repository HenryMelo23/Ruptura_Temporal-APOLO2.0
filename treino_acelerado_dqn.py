"""
TREINO ACELERADO DQN - RUPTURA TEMPORAL (Headless Engine)

Motor de simulacao matematica pura para convergencia rapida das redes
neurais de Apolo (jogador) e Umbra (boss), sem janela ou renderizacao.

Pilares:
  1. Headless Absoluto   - SDL_VIDEODRIVER=dummy
  2. Simulacao por Rects - Hitbox pura, sem sprites
  3. DQN Assíncrono      - ReplayBuffer + Target Networks
  4. Rewards Fieis       - Exatamente os definidos no GAME5.py
  5. Metricas / Logs     - Checkpoints a cada 50 episodios
"""

# =============================================================================
# PILAR 1 - HEADLESS ABSOLUTO (deve vir ANTES de qualquer import do pygame)
# =============================================================================
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

# =============================================================================
# IMPORTS GERAIS
# =============================================================================
import pygame
import math
import random
import time
import collections
from typing import List, Dict, Optional, Tuple, Deque

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

# =============================================================================
# INICIALIZACAO MINIMA DO PYGAME (sem display, sem som)
# =============================================================================
pygame.init()
pygame.display.set_mode((1, 1), flags=pygame.NOFRAME)   # Surface dummy

# =============================================================================
# HIPERPARAMETROS E CONSTANTES DO TREINO
# =============================================================================

# --- Dimensoes do Mapa (espelha Variaveis.py) ---
LARGURA_MAPA   = int(1360 * 0.8)   # 1088 px
ALTURA_MAPA    = int(768  * 1)     # 768  px
ESPACAMENTO    = 100

# --- Tamanhos dos personagens ---
LARGURA_PERSON = int(LARGURA_MAPA * 0.05)
ALTURA_PERSON  = int(ALTURA_MAPA  * 0.08)
LARGURA_BOSS   = int(LARGURA_PERSON * 1.2)
ALTURA_BOSS    = int(ALTURA_PERSON  * 1.2)

# --- Atributos base do Apolo ---
VIDA_MAXIMA_APOLO  = 1000
VELOCIDADE_APOLO   = 3.5
DISTANCIA_DASH     = 300
COOLDOWN_DASH_MS   = 2800
INTERVALO_DISPARO  = 400            # ms
DANO_TIRO_APOLO    = 120
DANO_BOSS_HIT      = 90             # Dano do projétil da Umbra

# --- Atributos base da Umbra ---
VIDA_MAXIMA_UMBRA  = 45_000
VELOCIDADE_UMBRA   = 3.0
VELOCIDADE_PROJ    = 11             # px/frame

# --- Esferas de cura ---
CURA_ESFERA        = 80
INTERVALO_ESFERA   = 8_000          # ms

# --- DQN ---
BATCH_SIZE         = 64
BUFFER_SIZE        = 50_000
LR_APOLO           = 3e-4
LR_UMBRA           = 3e-4
GAMMA              = 0.97
TARGET_UPDATE_FREQ = 200            # frames entre updates do target
TREINO_FREQ        = 4              # treina a cada N frames

# --- Epsilon-Greedy ---
EPSILON_INICIO     = 1.0
EPSILON_FIM        = 0.05
EPSILON_DECAIMENTO = 0.9985

# --- Loop de Treino ---
MAX_EPISODIOS      = 100_000
MAX_FRAMES_EP      = 4_000
LOG_INTERVALO      = 100
SAVE_INTERVALO     = 50

# --- Arquivos de persistencia ---
ARQUIVO_APOLO = "apolo_memoria_dqn.pt"
ARQUIVO_UMBRA = "memoria_umbra_dqn.pt"

# --- Device ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[DISPOSITIVO] Usando: {DEVICE}")


# =============================================================================
# PILAR 3 - REDES NEURAIS
# =============================================================================
# Arquitetura IDENTICA ao GAME5.py / habilidade_boss.py para compatibilidade:
#   Apolo: Linear(41,128)->LeakyReLU->Linear(128,64)->LeakyReLU->Linear(64,5)
#   Umbra: Linear(18,128)->LeakyReLU->Linear(128,64)->LeakyReLU->Linear(64,22)

class DQNNet(nn.Module):
    def __init__(self, input_size: int, output_size: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.LeakyReLU(),
            nn.Linear(128, 64),
            nn.LeakyReLU(),
            nn.Linear(64, output_size)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# =============================================================================
# PILAR 3 - REPLAY BUFFER
# =============================================================================

class ReplayBuffer:
    """Buffer de experiencias (s, a, r, s', done) com amostragem uniforme."""

    def __init__(self, capacidade: int):
        self.buffer: Deque = collections.deque(maxlen=capacidade)

    def adicionar(self, s, a: int, r: float, s_next, done: bool):
        self.buffer.append((s, a, r, s_next, done))

    def amostrar(self, batch_size: int):
        amostras = random.sample(self.buffer, batch_size)
        estados, acoes, recompensas, proximos, dones = zip(*amostras)
        return (
            torch.cat(estados,  dim=0),
            torch.tensor(acoes,       dtype=torch.long,    device=DEVICE),
            torch.tensor(recompensas, dtype=torch.float32, device=DEVICE),
            torch.cat(proximos, dim=0),
            torch.tensor(dones,       dtype=torch.float32, device=DEVICE),
        )

    def __len__(self) -> int:
        return len(self.buffer)


# =============================================================================
# PILAR 2 - OBJETOS EM CENA (representacao matematica pura)
# =============================================================================

class Projetil:
    """Projetil de qualquer origem — calculo vetorial sem sprites."""

    def __init__(self, x: float, y: float, angulo: float, vel: float,
                 dano: int, dono: str = "umbra"):
        self.rect  = pygame.Rect(int(x), int(y), 12, 12)
        self.fx    = float(x)
        self.fy    = float(y)
        self.vx    = math.cos(angulo) * vel
        self.vy    = math.sin(angulo) * vel
        self.dano  = dano
        self.dono  = dono   # "apolo" | "umbra"
        self.ativo = True

    def atualizar(self) -> bool:
        """Move o projetil. Desativa se sair do mapa."""
        self.fx += self.vx
        self.fy += self.vy
        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)
        if (self.fx < -50 or self.fx > LARGURA_MAPA + 50 or
                self.fy < -50 or self.fy > ALTURA_MAPA  + 50):
            self.ativo = False
        return self.ativo


class EsferaEnergia:
    """Esfera de cura deixada pela Umbra."""

    def __init__(self, x: float, y: float, cura: int = CURA_ESFERA):
        self.rect  = pygame.Rect(int(x - 12), int(y - 12), 24, 24)
        self.cura  = cura
        self.ativo = True


# =============================================================================
# PILAR 2 - ESTADO DA UMBRA (armadilhas)
# =============================================================================

def _criar_estado_ia() -> Dict:
    """Dicionario de estado da IA da Umbra — espelha Variaveis.py."""
    return {
        'ultimo_ataque'        : 0,
        'intervalo'            : 1200,
        'projeteis'            : [],
        'fase_tele'            : "espera",
        'proj_tele'            : None,
        'dano_recente'         : 0,
        'ultimo_teleporte'     : 0,
        'parede_ativa'         : False,
        'ultimo_parede'        : 0,
        'ultimo_tick_cura'     : 0,
        'vel_x'                : 0,
        'vel_y'                : 0,
        'alvo_ia'              : (LARGURA_MAPA // 2, ALTURA_MAPA // 2),
        'ultimo_vortice'       : 0,
        'ultimo_prisao'        : 0,
        'ultimo_miasma'        : 0,
        'ultimo_descarga'      : 0,
        'ultimo_espinhos'      : 0,
        'ultimo_laser'         : 0,
        'ultimo_bordas'        : 0,
        'vortice_ativo'        : None,
        'prisao_ativa'         : None,
        'caminho_espinhos'     : None,
        'laser_ativo'          : None,
        'descarga_eletrica'    : None,
        'bordas_ativas'        : None,
        'miasma_ativo'         : None,
        'mapa_atual'           : "Sprites/Fase5-1.png",
        'decisoes_ativas'      : [],
        'centro_mapa'          : (LARGURA_MAPA // 2, ALTURA_MAPA // 2),
        'espinho_padrao_ultimo': 'B',
        'f_fuga_x'             : 0,
        'f_fuga_y'             : 0,
    }


# =============================================================================
# PILAR 2 - PERSONAGEM APOLO
# =============================================================================

class ApoloSim:
    """Representacao matematica do Apolo para o ambiente headless."""

    def __init__(self):
        self.reset()

    def reset(self, x: Optional[float] = None, y: Optional[float] = None):
        self.fx = float(x if x is not None
                        else random.randint(ESPACAMENTO,
                                            LARGURA_MAPA - LARGURA_PERSON - ESPACAMENTO))
        self.fy = float(y if y is not None
                        else random.randint(ESPACAMENTO,
                                            ALTURA_MAPA  - ALTURA_PERSON  - ESPACAMENTO))
        self.rect           = pygame.Rect(int(self.fx), int(self.fy), LARGURA_PERSON, ALTURA_PERSON)
        self.vida           = float(VIDA_MAXIMA_APOLO)
        self.cooldown_dash  = False
        self.tempo_dash     = 0
        self.tempo_disparo  = 0
        self.ultima_direcao = 'right'

    def mover(self, acao: int, agora: int) -> Tuple[float, float]:
        """
        Acoes: 0=Cima, 1=Baixo, 2=Esquerda, 3=Direita, 4=Dash
        Retorna (dx, dy) efetivo apos clamp.
        """
        dx, dy = 0.0, 0.0
        if   acao == 0: dy = -1.0; self.ultima_direcao = 'up'
        elif acao == 1: dy =  1.0; self.ultima_direcao = 'down'
        elif acao == 2: dx = -1.0; self.ultima_direcao = 'left'
        elif acao == 3: dx =  1.0; self.ultima_direcao = 'right'
        elif acao == 4 and not self.cooldown_dash:
            mult = DISTANCIA_DASH / max(VELOCIDADE_APOLO, 1e-6)
            if   self.ultima_direcao == 'up':    dy = -mult
            elif self.ultima_direcao == 'down':   dy =  mult
            elif self.ultima_direcao == 'left':   dx = -mult
            elif self.ultima_direcao == 'right':  dx =  mult
            self.cooldown_dash = True
            self.tempo_dash    = agora

        self.fx = max(0.0, min(float(LARGURA_MAPA - LARGURA_PERSON), self.fx + dx * VELOCIDADE_APOLO))
        self.fy = max(0.0, min(float(ALTURA_MAPA  - ALTURA_PERSON),  self.fy + dy * VELOCIDADE_APOLO))
        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)

        if self.cooldown_dash and (agora - self.tempo_dash) >= COOLDOWN_DASH_MS:
            self.cooldown_dash = False

        return dx * VELOCIDADE_APOLO, dy * VELOCIDADE_APOLO

    def disparar(self, alvo_x: float, alvo_y: float, agora: int) -> Optional[Projetil]:
        if (agora - self.tempo_disparo) < INTERVALO_DISPARO:
            return None
        cx = self.fx + LARGURA_PERSON / 2
        cy = self.fy + ALTURA_PERSON  / 2
        ang = math.atan2(alvo_y - cy, alvo_x - cx)
        self.tempo_disparo = agora
        return Projetil(cx, cy, ang, VELOCIDADE_APOLO * 2.8, DANO_TIRO_APOLO, dono="apolo")

    def em_canto(self, m: int = 100) -> bool:
        nas_x = (self.fx < m or self.fx > LARGURA_MAPA - LARGURA_PERSON - m)
        nas_y = (self.fy < m or self.fy > ALTURA_MAPA  - ALTURA_PERSON  - m)
        return nas_x and nas_y

    def nas_bordas(self, m: int = 100) -> bool:
        return (self.fx < m or self.fy < m or
                self.fx > LARGURA_MAPA - LARGURA_PERSON - m or
                self.fy > ALTURA_MAPA  - ALTURA_PERSON  - m)


# =============================================================================
# PILAR 2 - BOSS UMBRA
# =============================================================================

class UmbraSim:
    """Representacao matematica da Umbra para o ambiente headless."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.fx   = float(LARGURA_MAPA // 2 - LARGURA_BOSS // 2)
        self.fy   = float(ALTURA_MAPA  // 2 - ALTURA_BOSS  // 2)
        self.rect = pygame.Rect(int(self.fx), int(self.fy), LARGURA_BOSS, ALTURA_BOSS)
        self.vida = float(VIDA_MAXIMA_UMBRA)
        self.vel_x = 0.0
        self.vel_y = 0.0

    def mover_para(self, alvo_x: float, alvo_y: float):
        """Movimento suavizado em direcao ao alvo, igual ao GAME5."""
        VEL_MAX   = VELOCIDADE_UMBRA
        AGILIDADE = 0.25
        dx_a = alvo_x - self.fx
        dy_a = alvo_y - self.fy
        mag  = math.hypot(dx_a, dy_a)
        if mag > 0:
            vx_d = (dx_a / mag) * VEL_MAX
            vy_d = (dy_a / mag) * VEL_MAX
        else:
            vx_d = vy_d = 0.0
        self.vel_x += (vx_d - self.vel_x) * AGILIDADE
        self.vel_y += (vy_d - self.vel_y) * AGILIDADE
        self.fx = max(float(ESPACAMENTO),
                      min(float(LARGURA_MAPA - LARGURA_BOSS - ESPACAMENTO), self.fx + self.vel_x))
        self.fy = max(float(ESPACAMENTO),
                      min(float(ALTURA_MAPA  - ALTURA_BOSS  - ESPACAMENTO), self.fy + self.vel_y))
        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)

    def teleportar(self, ax: float, ay: float):
        """Teleporte instantaneo (simplificado para treino)."""
        self.fx = max(float(ESPACAMENTO), min(float(LARGURA_MAPA - LARGURA_BOSS - ESPACAMENTO), ax))
        self.fy = max(float(ESPACAMENTO), min(float(ALTURA_MAPA  - ALTURA_BOSS  - ESPACAMENTO), ay))
        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)


# =============================================================================
# PILAR 3 - AGENTE APOLO (DQN + ReplayBuffer)
# =============================================================================
#
# Estado Apolo: 41 features (identico ao obter_estado_expandido do GAME5.py)
#  0- 5: px, py, bx, by, vida_a, vida_b
#  6-10: d_esq, d_dir, d_cima, d_baixo, em_canto
# 11-15: dist_perigo, dpx, dpy, cd_tele, vel_p
# 16-17: qtd_esferas, vel_boss
# 18-26: laser (9 campos - zerados no headless)
# 27-29: dist_orbe, orbe_dx, orbe_dy
# 30-33: qtd_ratos, dist_rato, rato_dx, rato_dy (zerados no headless)
# 34-40: 7 flags de armadilhas

APOLO_INPUT_SIZE  = 41
APOLO_OUTPUT_SIZE = 5   # 0=cima, 1=baixo, 2=esq, 3=dir, 4=dash


class AgenteApolo:
    """Agente DQN completo para o Apolo com ReplayBuffer e target network."""

    ACOES = ['CIMA', 'BAIXO', 'ESQUERDA', 'DIREITA', 'DASH']

    def __init__(self, epsilon: float = EPSILON_INICIO):
        self.epsilon    = epsilon
        self.q_net      = DQNNet(APOLO_INPUT_SIZE, APOLO_OUTPUT_SIZE).to(DEVICE)
        self.target_net = DQNNet(APOLO_INPUT_SIZE, APOLO_OUTPUT_SIZE).to(DEVICE)
        self.target_net.load_state_dict(self.q_net.state_dict())
        self.target_net.eval()
        self.optimizer  = optim.Adam(self.q_net.parameters(), lr=LR_APOLO)
        self.buffer     = ReplayBuffer(BUFFER_SIZE)
        self.loss_acum  = 0.0
        self.loss_count = 0
        self._carregar()

    def _carregar(self):
        if os.path.exists(ARQUIVO_APOLO):
            try:
                self.q_net.load_state_dict(
                    torch.load(ARQUIVO_APOLO, map_location=DEVICE, weights_only=True))
                self.target_net.load_state_dict(self.q_net.state_dict())
                print(f"  [Apolo] Pesos carregados de '{ARQUIVO_APOLO}'")
            except Exception as e:
                print(f"  [Apolo] Aviso ao carregar pesos: {e}")

    def salvar(self):
        torch.save(self.q_net.state_dict(), ARQUIVO_APOLO)

    def atualizar_target(self):
        self.target_net.load_state_dict(self.q_net.state_dict())

    def obter_estado(self, apolo: ApoloSim, umbra: UmbraSim,
                     projeteis: List[Projetil],
                     esferas: List[EsferaEnergia],
                     estado_ia: Dict) -> torch.Tensor:
        """
        Vetor de 41 features identico ao obter_estado_expandido() do GAME5.py.
        Campos de laser e ratos sao zerados (nao existem no headless).
        """
        px = apolo.fx + LARGURA_PERSON / 2
        py = apolo.fy + ALTURA_PERSON  / 2
        bx = umbra.fx + LARGURA_BOSS   / 2
        by = umbra.fy + ALTURA_BOSS    / 2

        # 0-5: posicoes e vidas
        f_px = px / LARGURA_MAPA
        f_py = py / ALTURA_MAPA
        f_bx = bx / LARGURA_MAPA
        f_by = by / ALTURA_MAPA
        f_va = apolo.vida / VIDA_MAXIMA_APOLO
        f_vb = umbra.vida / VIDA_MAXIMA_UMBRA

        # 6-10: bordas
        M = 100.0
        f_de  = min(1.0, apolo.fx / M)
        f_dd  = min(1.0, (LARGURA_MAPA - apolo.fx) / M)
        f_dc  = min(1.0, apolo.fy / M)
        f_db  = min(1.0, (ALTURA_MAPA  - apolo.fy) / M)
        f_can = 1.0 if apolo.em_canto() else 0.0

        # 11-14: projetil mais proximo
        dist_p, dpx_f, dpy_f = 1.0, 0.0, 0.0
        proximos = []
        for p in projeteis:
            if p.dono == "umbra" and p.ativo:
                d = math.hypot(p.rect.centerx - px, p.rect.centery - py)
                if d < 250:
                    proximos.append((p.rect.centerx, p.rect.centery, d))
        if proximos:
            ex, ey, dp = min(proximos, key=lambda v: v[2])
            dist_p  = dp / 250.0
            dpx_f   = (ex - px) / max(1.0, dp)
            dpy_f   = (ey - py) / max(1.0, dp)

        # 15: cooldown dash
        f_cd = 1.0 if apolo.cooldown_dash else 0.0

        # 16: vel apolo (simplificado)
        f_vp = 0.5

        # 17: qtd esferas
        f_qe = min(1.0, len(esferas) / 10.0)

        # 18: vel boss
        f_vb_vel = min(1.0, math.hypot(umbra.vel_x, umbra.vel_y) / (VELOCIDADE_UMBRA + 1e-6))

        # 19-27: laser (9 campos zerados - sem laser no headless)
        f_las = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0]  # dist=1 e tempo=1 = seguro

        # 28-30: orbe mais proxima
        f_do, f_odx, f_ody = 1.0, 0.0, 0.0
        if esferas:
            e_best = min(esferas, key=lambda e: math.hypot(e.rect.centerx - px, e.rect.centery - py))
            de = math.hypot(e_best.rect.centerx - px, e_best.rect.centery - py)
            f_do = min(1.0, de / 800.0)
            if de > 0:
                f_odx = (e_best.rect.centerx - px) / de
                f_ody = (e_best.rect.centery - py) / de

        # 31-34: ratos (zerados no headless)
        f_rat = [0.0, 1.0, 0.0, 0.0]

        # 35-41: armadilhas (7 flags)
        chaves_arm = ['vortice_ativo', 'prisao_ativa', 'caminho_espinhos',
                      'laser_ativo', 'descarga_eletrica', 'bordas_ativas', 'miasma_ativo']
        f_arm = [1.0 if estado_ia.get(k) else 0.0 for k in chaves_arm]

        features = [
            f_px, f_py, f_bx, f_by, f_va, f_vb,           # 0-5
            f_de, f_dd, f_dc, f_db, f_can,                 # 6-10
            dist_p, dpx_f, dpy_f, f_cd, f_vp,             # 11-15
            f_qe, f_vb_vel,                                # 16-17
        ] + f_las + [                                       # 18-26
            f_do, f_odx, f_ody,                            # 27-29
        ] + f_rat + f_arm                                   # 30-33, 34-40

        assert len(features) == 41, f"Estado Apolo invalido: {len(features)} features"
        return torch.tensor(features, dtype=torch.float32, device=DEVICE).unsqueeze(0)

    def decidir(self, estado: torch.Tensor, acoes_validas: List[int]) -> int:
        if random.random() < self.epsilon:
            return random.choice(acoes_validas)
        with torch.no_grad():
            self.q_net.eval()
            q_vals = self.q_net(estado)[0].clone()
            for i in range(APOLO_OUTPUT_SIZE):
                if i not in acoes_validas:
                    q_vals[i] = -1e9
        return int(q_vals.argmax().item())

    def armazenar(self, s, a: int, r: float, s_next, done: bool):
        self.buffer.adicionar(s, a, r, s_next, done)

    def treinar(self) -> float:
        if len(self.buffer) < BATCH_SIZE:
            return 0.0
        s, a, r, s_next, done = self.buffer.amostrar(BATCH_SIZE)
        self.q_net.train()
        q_atual = self.q_net(s).gather(1, a.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            q_prox = self.target_net(s_next).max(1)[0]
            q_alvo = r + GAMMA * q_prox * (1.0 - done)
        loss = F.smooth_l1_loss(q_atual, q_alvo)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_net.parameters(), max_norm=10.0)
        self.optimizer.step()
        lv = loss.item()
        self.loss_acum  += lv
        self.loss_count += 1
        return lv

    def loss_media(self) -> float:
        if self.loss_count == 0:
            return 0.0
        v = self.loss_acum / self.loss_count
        self.loss_acum  = 0.0
        self.loss_count = 0
        return v


# =============================================================================
# PILAR 3 - AGENTE UMBRA (DQN + ReplayBuffer)
# =============================================================================
#
# Estado Umbra: 18 features (identico ao discretizar_estado do habilidade_boss.py)
#  0: vida_perc        1: dist_p/2000     2: sob_fogo bool
#  3: vx_p             4: vy_p            5: dx              6: dy
#  7: fogo_flag        8-14: 7 flags armadilhas
#  15: map_val         16: bias_x         17: bias_y
#
# Acoes: 22 (identico ao acoes_base de MemoriaEvolutivaUmbra)

UMBRA_INPUT_SIZE = 18
UMBRA_ACOES = [
    "FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR", "ATAQUE", "SIFON", "TELEPORTE",
    "TRANSMUTAR_VORTICE", "TRANSMUTAR_GRAVIDADE", "TRANSMUTAR_NECROSE",
    "TRANSMUTAR_RESSONANCIA", "TRANSMUTAR_HEMORRAGIA", "TRANSMUTAR_ATRITO",
    "TRANSMUTAR_RASTRO", "VORTICE", "PRISAO", "MIASMA", "DESCARGA_ELETRICA",
    "PRAGA_RATOS", "LASER_SOBRECARGA", "CAMINHO_ESPINHOS", "NENHUMA"
]
UMBRA_OUTPUT_SIZE = len(UMBRA_ACOES)   # 22


class AgenteUmbra:
    """Agente DQN para a Umbra, identico ao MemoriaEvolutivaUmbra do GAME5."""

    def __init__(self, epsilon: float = EPSILON_INICIO):
        self.epsilon    = epsilon
        self.acoes      = UMBRA_ACOES
        self.q_net      = DQNNet(UMBRA_INPUT_SIZE, UMBRA_OUTPUT_SIZE).to(DEVICE)
        self.target_net = DQNNet(UMBRA_INPUT_SIZE, UMBRA_OUTPUT_SIZE).to(DEVICE)
        self.target_net.load_state_dict(self.q_net.state_dict())
        self.target_net.eval()
        self.optimizer  = optim.Adam(self.q_net.parameters(), lr=LR_UMBRA)
        self.buffer     = ReplayBuffer(BUFFER_SIZE)
        self.loss_acum  = 0.0
        self.loss_count = 0
        # Bayesian bias do Apolo
        self.tendencias: Dict[str, float] = {
            "TOTAL": 0.0, "ESQUERDA": 0.0, "DIREITA": 0.0, "CIMA": 0.0, "BAIXO": 0.0
        }
        # Cooldowns de habilidades (ms)
        self.cd: Dict[str, int] = {
            "ataque": 0, "teleporte": 0, "vortice": 0,
            "prisao": 0, "miasma": 0,   "descarga": 0, "espinhos": 0,
        }
        self._carregar()

    def _carregar(self):
        if os.path.exists(ARQUIVO_UMBRA):
            try:
                self.q_net.load_state_dict(
                    torch.load(ARQUIVO_UMBRA, map_location=DEVICE, weights_only=True))
                self.target_net.load_state_dict(self.q_net.state_dict())
                print(f"  [Umbra] Pesos carregados de '{ARQUIVO_UMBRA}'")
            except Exception as e:
                print(f"  [Umbra] Aviso ao carregar pesos: {e}")

    def salvar(self):
        torch.save(self.q_net.state_dict(), ARQUIVO_UMBRA)

    def atualizar_target(self):
        self.target_net.load_state_dict(self.q_net.state_dict())

    def registrar_movimento_apolo(self, vx: float, vy: float):
        """Atualiza contagens Bayesianas (espelha habilidade_boss.py)."""
        if abs(vx) > 0.5 or abs(vy) > 0.5:
            if vx > 1:    self.tendencias["DIREITA"]  += 1
            elif vx < -1: self.tendencias["ESQUERDA"] += 1
            if vy > 1:    self.tendencias["BAIXO"]    += 1
            elif vy < -1: self.tendencias["CIMA"]     += 1
            self.tendencias["TOTAL"] += 1

    def calcular_bias_bayesiano(self) -> Tuple[float, float]:
        total = max(1.0, self.tendencias["TOTAL"])
        bx = (self.tendencias["DIREITA"]  - self.tendencias["ESQUERDA"]) / total
        by = (self.tendencias["BAIXO"]    - self.tendencias["CIMA"])     / total
        return bx, by

    def obter_estado(self, umbra: UmbraSim, apolo: ApoloSim,
                     projeteis: List[Projetil],
                     estado_ia: Dict,
                     hist_apolo: List[Tuple[float, float]]) -> torch.Tensor:
        """
        Vetor de 18 features identico ao discretizar_estado() de habilidade_boss.py.
        """
        bx = umbra.fx + LARGURA_BOSS   / 2
        by = umbra.fy + ALTURA_BOSS    / 2
        px = apolo.fx + LARGURA_PERSON / 2
        py = apolo.fy + ALTURA_PERSON  / 2

        vida_perc  = umbra.vida / VIDA_MAXIMA_UMBRA
        dist_p     = math.hypot(bx - px, by - py)
        n_tiros    = float(sum(1 for p in projeteis if p.dono == "apolo" and p.ativo))

        # Velocidade do Apolo (ultimos 3 frames do historico)
        vx_p, vy_p = 0.0, 0.0
        if hist_apolo and len(hist_apolo) >= 3:
            p1, p3 = hist_apolo[-3], hist_apolo[-1]
            vx_p = (p3[0] - p1[0]) / 30.0
            vy_p = (p3[1] - p1[1]) / 30.0
        vx_p = max(-1.0, min(1.0, vx_p))
        vy_p = max(-1.0, min(1.0, vy_p))

        # Vetor normalizado boss -> player
        dx = (bx - px) / 1000.0
        dy = (by - py) / 1000.0

        # Armadilhas (7 flags)
        chaves = ['vortice_ativo', 'prisao_ativa', 'caminho_espinhos',
                  'laser_ativo', 'descarga_eletrica', 'bordas_ativas', 'miasma_ativo']
        f_arm = [1.0 if estado_ia.get(k) else 0.0 for k in chaves]

        # map_val (fase base = 0.5)
        map_val = 0.5

        # Bias bayesiano
        bx_b, by_b = self.calcular_bias_bayesiano()

        features = [
            vida_perc,                      # 0
            dist_p / 2000.0,                # 1
            min(1.0, n_tiros / 5.0),        # 2  sob_fogo normalizado
            vx_p, vy_p,                     # 3-4
            dx, dy,                         # 5-6
            1.0 if n_tiros > 0 else 0.0,   # 7  fogo bool
        ] + f_arm + [                       # 8-14
            map_val,                        # 15
            bx_b, by_b,                     # 16-17
        ]

        assert len(features) == 18, f"Estado Umbra invalido: {len(features)} features"
        return torch.tensor(features, dtype=torch.float32, device=DEVICE).unsqueeze(0)

    def decidir(self, estado: torch.Tensor, acoes_disp: List[str]) -> str:
        # Filtra acoes que existem no espaco de saida
        validas = [a for a in acoes_disp if a in self.acoes]
        if not validas:
            return "NENHUMA"
        if random.random() < self.epsilon:
            return random.choice(validas)
        indices = [self.acoes.index(a) for a in validas]
        with torch.no_grad():
            self.q_net.eval()
            q_vals = self.q_net(estado)[0]
            best_i = max(indices, key=lambda i: q_vals[i].item())
        return self.acoes[best_i]

    def armazenar(self, s, a_str: str, r: float, s_next, done: bool):
        a_idx = self.acoes.index(a_str) if a_str in self.acoes else 0
        self.buffer.adicionar(s, a_idx, r, s_next, done)

    def treinar(self) -> float:
        if len(self.buffer) < BATCH_SIZE:
            return 0.0
        s, a, r, s_next, done = self.buffer.amostrar(BATCH_SIZE)
        self.q_net.train()
        q_atual = self.q_net(s).gather(1, a.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            q_prox = self.target_net(s_next).max(1)[0]
            q_alvo = r + GAMMA * q_prox * (1.0 - done)
        loss = F.smooth_l1_loss(q_atual, q_alvo)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_net.parameters(), max_norm=10.0)
        self.optimizer.step()
        lv = loss.item()
        self.loss_acum  += lv
        self.loss_count += 1
        return lv

    def loss_media(self) -> float:
        if self.loss_count == 0:
            return 0.0
        v = self.loss_acum / self.loss_count
        self.loss_acum  = 0.0
        self.loss_count = 0
        return v

    def acoes_disponiveis(self, agora: int) -> List[str]:
        """Filtra acoes pelos cooldowns (espelha processar_ia_umbra)."""
        disp = ["ATAQUE"]
        if agora - self.cd.get("teleporte", 0) >= 10_000: disp.append("TELEPORTE")
        if agora - self.cd.get("vortice",   0) >= 12_000: disp.append("VORTICE")
        if agora - self.cd.get("prisao",    0) >=  9_000: disp.append("PRISAO")
        if agora - self.cd.get("miasma",    0) >= 10_000: disp.append("MIASMA")
        if agora - self.cd.get("descarga",  0) >= 11_000: disp.append("DESCARGA_ELETRICA")
        if agora - self.cd.get("espinhos",  0) >=  8_000: disp.append("CAMINHO_ESPINHOS")
        disp.append("NENHUMA")
        return [a for a in disp if a in self.acoes]


# =============================================================================
# PILAR 4 - SISTEMA DE RECOMPENSAS (fiel ao GAME5.py)
# =============================================================================

def calcular_reward_apolo(apolo: ApoloSim, umbra: UmbraSim,
                           projeteis: List[Projetil],
                           esferas: List[EsferaEnergia],
                           estado_ia: Dict,
                           vida_ant: float, vida_boss_ant: float,
                           coletou: bool, venceu: bool, morreu: bool) -> float:
    """Recompensas do Apolo — espelha pensar() do AgenteApolo no GAME5.py."""
    px = apolo.fx + LARGURA_PERSON / 2
    py = apolo.fy + ALTURA_PERSON  / 2
    r  = 0.3   # Sobrevivencia base por frame

    if venceu: return r + 500.0
    if morreu: return r - 500.0

    # Delta de vida
    da = apolo.vida - vida_ant
    db = umbra.vida - vida_boss_ant
    if da < 0: r -= 50.0
    if db < 0: r += 30.0
    if coletou: r += 100.0

    # Bordas e cantos
    MC, MP = 50, 100
    de = apolo.fx;                  dd = LARGURA_MAPA - apolo.fx
    dc = apolo.fy;                  db2 = ALTURA_MAPA  - apolo.fy
    if de < MC or dd < MC or dc < MC or db2 < MC: r -= 25.0
    elif de < MP or dd < MP or dc < MP or db2 < MP: r -= 8.0
    if apolo.em_canto(MP): r -= 40.0

    # Centro e distancia ao boss
    cx = LARGURA_MAPA / 2;  cy = ALTURA_MAPA / 2
    if math.hypot(px - cx, py - cy) < min(LARGURA_MAPA, ALTURA_MAPA) * 0.30: r += 3.0
    bx = umbra.fx + LARGURA_BOSS / 2;  by = umbra.fy + ALTURA_BOSS / 2
    db3 = math.hypot(bx - px, by - py)
    if 300 < db3 < 600: r += 1.0
    elif db3 < 200:     r -= 3.0

    # Busca esferas quando com pouca vida
    perc = apolo.vida / VIDA_MAXIMA_APOLO
    if esferas and perc < 0.5:
        eb = min(esferas, key=lambda e: math.hypot(e.rect.centerx - px, e.rect.centery - py))
        de2 = math.hypot(eb.rect.centerx - px, eb.rect.centery - py)
        if perc < 0.3:
            if de2 < 200: r += 15.0
            elif de2 < 400: r += 8.0
        else:
            if de2 < 200: r += 8.0
            elif de2 < 400: r += 4.0

    # Projeteis proximos
    for p in projeteis:
        if p.dono == "umbra" and p.ativo:
            if math.hypot(p.rect.centerx - px, p.rect.centery - py) < 80:
                r -= 20.0
                break

    # Vortice
    if estado_ia.get("vortice_ativo"):
        v = estado_ia["vortice_ativo"]
        dv = math.hypot(v['x'] - px, v['y'] - py)
        if dv < 150:   r -= 30.0
        elif dv < 300: r -= 10.0

    return float(r)


def calcular_reward_umbra(acertou: bool, acao: str,
                           venceu: bool, perdeu: bool) -> float:
    """Recompensas da Umbra — espelha treinar() de MemoriaEvolutivaUmbra."""
    r = 0.1
    if venceu: return r + 500.0
    if perdeu: return r - 500.0
    if acertou: r += 50.0
    if acao not in ("ATAQUE", "NENHUMA"): r -= 2.0   # custo energetico de habilidade
    return float(r)


# =============================================================================
# PILAR 2 - LOGICA DE HABILIDADES DA UMBRA (sem renderizacao)
# =============================================================================

def executar_acao_umbra(agora: int, acao: str,
                         umbra: UmbraSim, apolo: ApoloSim,
                         estado_ia: Dict, agente: AgenteUmbra,
                         projeteis: List[Projetil],
                         hist_apolo: List[Tuple[float, float]]) -> None:
    """Executa logica de combate da Umbra em calculo puro, sem renderizacao."""
    bx = umbra.fx + LARGURA_BOSS   / 2
    by = umbra.fy + ALTURA_BOSS    / 2
    px = apolo.fx + LARGURA_PERSON / 2
    py = apolo.fy + ALTURA_PERSON  / 2

    if acao == "ATAQUE":
        if agora - agente.cd["ataque"] >= estado_ia.get("intervalo", 1200):
            dist = math.hypot(px - bx, py - by)
            t_voo = dist / max(VELOCIDADE_PROJ, 1e-6)
            # Lead preditivo (espelha node_ataque_direcionado)
            vax, vay = 0.0, 0.0
            if len(hist_apolo) >= 2:
                vax = px - (hist_apolo[-2][0] + LARGURA_PERSON / 2)
                vay = py - (hist_apolo[-2][1] + ALTURA_PERSON  / 2)
            fator = max(0.55, 1.0 - dist / 1800.0)
            ax = max(50.0, min(LARGURA_MAPA - 50.0, px + vax * t_voo * fator))
            ay = max(50.0, min(ALTURA_MAPA  - 50.0, py + vay * t_voo * fator))
            ang = math.atan2(ay - by, ax - bx)
            projeteis.append(Projetil(bx, by, ang, float(VELOCIDADE_PROJ), DANO_BOSS_HIT, dono="umbra"))
            agente.cd["ataque"] = agora

    elif acao == "TELEPORTE":
        ang_p  = math.atan2(py - by, px - bx)
        ang_fl = ang_p + random.choice([math.pi / 2, -math.pi / 2])
        ax = px + math.cos(ang_fl) * 450
        ay = py + math.sin(ang_fl) * 450
        umbra.teleportar(ax, ay)
        agente.cd["teleporte"] = agora

    elif acao == "VORTICE":
        estado_ia['vortice_ativo'] = {
            'x': LARGURA_MAPA / 2, 'y': ALTURA_MAPA / 2,
            'tempo_inicio': agora, 'duracao': 8000, 'forca': 2.8
        }
        agente.cd["vortice"] = agora

    elif acao == "PRISAO":
        if len(hist_apolo) >= 5:
            vax = px - (hist_apolo[-5][0] + LARGURA_PERSON / 2)
            vay = py - (hist_apolo[-5][1] + ALTURA_PERSON  / 2)
            ax = max(80.0, min(LARGURA_MAPA - 80.0, px + vax * 6))
            ay = max(80.0, min(ALTURA_MAPA  - 80.0, py + vay * 6))
        else:
            ax, ay = px, py
        estado_ia['prisao_ativa'] = {
            'rect': pygame.Rect(int(ax - 60), int(ay - 60), 120, 120),
            'tempo_inicio': agora, 'duracao': 3500, 'x': ax, 'y': ay
        }
        agente.cd["prisao"] = agora

    elif acao == "MIASMA":
        estado_ia['miasma_ativo'] = {'tempo_inicio': agora, 'duracao': 4500}
        agente.cd["miasma"] = agora

    elif acao == "DESCARGA_ELETRICA":
        ang_d = math.atan2(py - by, px - bx)
        estado_ia['descarga_eletrica'] = {
            'x': bx, 'y': by, 'angulo_base': ang_d,
            'raio_maximo': 380.0, 'abertura': 0.9,
            'duracao': 1800, 'tempo_inicio': agora, 'dano_por_tick': 12
        }
        agente.cd["descarga"] = agora

    elif acao == "CAMINHO_ESPINHOS":
        pad = estado_ia.get('espinho_padrao_ultimo', 'B')
        prox = 'A' if pad == 'B' else 'B'
        estado_ia['espinho_padrao_ultimo'] = prox
        raios = (
            [{'angulo': a, 'comprimento': 1200}
             for a in [math.pi*0.25, math.pi*0.75, math.pi*1.25, math.pi*1.75]]
            if prox == 'A'
            else [{'y_linha': int(ALTURA_MAPA * f)} for f in [0.25, 0.50, 0.75]]
        )
        estado_ia['caminho_espinhos'] = {
            'padrao': prox, 'raios': raios, 'largura_maxima': 90,
            'tempo_inicio': agora, 'fase': 'crescimento',
            'duracao_crescimento': 1800, 'duracao_expansao': 1600,
            'ultimo_espinho_hit': 0
        }
        agente.cd["espinhos"] = agora
    # NENHUMA, FUGIR, INTERCEPTAR, etc. nao tem efeito direto - sao acoes de movimento


# =============================================================================
# PILAR 2 - FISICA: COLISOES E ARMADILHAS
# =============================================================================

def atualizar_armadilhas(agora: int, estado_ia: Dict, apolo: ApoloSim) -> float:
    """Processa efeitos de armadilhas e retorna dano total ao Apolo."""
    px = apolo.fx + LARGURA_PERSON / 2
    py = apolo.fy + ALTURA_PERSON  / 2
    dano = 0.0

    # Vortice: puxao continuo
    if estado_ia.get('vortice_ativo'):
        v = estado_ia['vortice_ativo']
        if agora - v['tempo_inicio'] > v['duracao']:
            estado_ia['vortice_ativo'] = None
        else:
            dx = v['x'] - px;  dy = v['y'] - py
            d  = math.hypot(dx, dy)
            if d < 350 and d > 0:
                apolo.fx += (dx / d) * v['forca']
                apolo.fy += (dy / d) * v['forca']
                apolo.fx = max(0.0, min(float(LARGURA_MAPA - LARGURA_PERSON), apolo.fx))
                apolo.fy = max(0.0, min(float(ALTURA_MAPA  - ALTURA_PERSON),  apolo.fy))
                apolo.rect.x = int(apolo.fx)
                apolo.rect.y = int(apolo.fy)

    # Prisao
    if estado_ia.get('prisao_ativa'):
        p = estado_ia['prisao_ativa']
        if agora - p['tempo_inicio'] > p['duracao']:
            estado_ia['prisao_ativa'] = None
        elif p['rect'].colliderect(apolo.rect):
            dano += 8 * 0.016

    # Miasma
    if estado_ia.get('miasma_ativo'):
        m = estado_ia['miasma_ativo']
        if agora - m['tempo_inicio'] > m['duracao']:
            estado_ia['miasma_ativo'] = None
        else:
            dano += 5 * 0.016

    # Descarga eletrica
    if estado_ia.get('descarga_eletrica'):
        dc = estado_ia['descarga_eletrica']
        if agora - dc['tempo_inicio'] > dc['duracao']:
            estado_ia['descarga_eletrica'] = None
        else:
            dy2 = py - dc['y'];  dx2 = px - dc['x']
            d   = math.hypot(dx2, dy2)
            if d < dc['raio_maximo']:
                ang  = math.atan2(dy2, dx2)
                diff = abs(ang - dc['angulo_base']) % (2 * math.pi)
                if diff > math.pi: diff = 2 * math.pi - diff
                if diff < dc['abertura'] / 2:
                    dano += dc['dano_por_tick'] * 0.016

    # Caminho de espinhos
    if estado_ia.get('caminho_espinhos'):
        ce      = estado_ia['caminho_espinhos']
        elapsed = agora - ce['tempo_inicio']
        if elapsed > ce['duracao_crescimento'] + ce['duracao_expansao']:
            estado_ia['caminho_espinhos'] = None
        elif ce['padrao'] == 'A':
            cx2 = LARGURA_MAPA / 2;  cy2 = ALTURA_MAPA / 2
            for raio in ce.get('raios', []):
                ang = raio.get('angulo', 0)
                for t in range(0, int(raio.get('comprimento', 1200)), 30):
                    rx = cx2 + math.cos(ang) * t
                    ry = cy2 + math.sin(ang) * t
                    if math.hypot(rx - px, ry - py) < 45:
                        dano += 20.0
                        break

    return dano


def processar_colisoes(projeteis: List[Projetil],
                        apolo: ApoloSim,
                        umbra: UmbraSim) -> Dict:
    """Detecta colisoes e aplica dano; retorna flags de acerto."""
    acertou_a = False
    acertou_u = False
    vivos: List[Projetil] = []
    for p in projeteis:
        if not p.ativo:
            continue
        p.atualizar()
        if not p.ativo:
            continue
        if p.dono == "umbra" and p.rect.colliderect(apolo.rect):
            apolo.vida -= float(p.dano)
            acertou_a   = True
            p.ativo     = False
        elif p.dono == "apolo" and p.rect.colliderect(umbra.rect):
            umbra.vida -= float(p.dano)
            acertou_u   = True
            p.ativo     = False
        if p.ativo:
            vivos.append(p)
    projeteis.clear()
    projeteis.extend(vivos)
    return {"acertou_apolo": acertou_a, "acertou_umbra": acertou_u}


def processar_esferas(esferas: List[EsferaEnergia], apolo: ApoloSim) -> bool:
    """Detecta coleta de esferas."""
    coletou = False
    vivas: List[EsferaEnergia] = []
    for e in esferas:
        if e.ativo and e.rect.colliderect(apolo.rect):
            apolo.vida = min(float(VIDA_MAXIMA_APOLO), apolo.vida + e.cura)
            coletou    = True
            e.ativo    = False
        elif e.ativo:
            vivas.append(e)
    esferas.clear()
    esferas.extend(vivas)
    return coletou


# =============================================================================
# MOVIMENTO DA UMBRA (vetorial, sem render)
# =============================================================================

def calcular_alvo_umbra(apolo: ApoloSim, umbra: UmbraSim, estrategia: str) -> Tuple[float, float]:
    bx = umbra.fx + LARGURA_BOSS   / 2;  by = umbra.fy + ALTURA_BOSS   / 2
    px = apolo.fx + LARGURA_PERSON / 2;  py = apolo.fy + ALTURA_PERSON / 2
    if estrategia == "FUGIR":
        ang = math.atan2(by - py, bx - px)
        ax  = bx + math.cos(ang) * 600;  ay = by + math.sin(ang) * 600
    elif estrategia == "INTERCEPTAR":
        ax = px + (px - bx) * 0.3;  ay = py + (py - by) * 0.3
    elif estrategia == "ORBITAR":
        ang = math.atan2(by - py, bx - px) + 0.7
        ax  = px + math.cos(ang) * 450;  ay = py + math.sin(ang) * 450
    else:   # CERCAR
        ang = math.atan2(by - py, bx - px)
        ax  = px + math.cos(ang) * 300;  ay = py + math.sin(ang) * 300
    ax = max(float(ESPACAMENTO), min(float(LARGURA_MAPA - LARGURA_BOSS - ESPACAMENTO), ax))
    ay = max(float(ESPACAMENTO), min(float(ALTURA_MAPA  - ALTURA_BOSS  - ESPACAMENTO), ay))
    return ax, ay


# =============================================================================
# PILAR 5 - EPISODIO COMPLETO
# =============================================================================

def rodar_episodio(agente_a: AgenteApolo, agente_u: AgenteUmbra,
                    frame_global: int) -> Tuple[str, float, float, float, float]:
    """
    Roda um episodio completo de treino.
    Retorna: (vencedor, reward_apolo, reward_umbra, frames, duracao_s)
    """
    t0 = time.perf_counter()

    apolo      = ApoloSim()
    umbra      = UmbraSim()
    estado_ia  = _criar_estado_ia()
    projeteis  : List[Projetil]           = []
    esferas    : List[EsferaEnergia]      = []
    hist_apolo : List[Tuple[float, float]] = []

    agora          = 0
    dt             = 16              # ~60fps
    vida_a_ant     = apolo.vida
    vida_u_ant     = umbra.vida
    r_apolo_total  = 0.0
    r_umbra_total  = 0.0
    vencedor       = "TIMEOUT"
    ultima_esfera  = 0
    estrategias    = ["FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR"]
    estrategia     = random.choice(estrategias)

    for frame in range(MAX_FRAMES_EP):
        agora += dt
        frames = frame + 1

        # ── Historico do Apolo ──────────────────────────────────────────────
        hist_apolo.append((apolo.fx, apolo.fy))
        if len(hist_apolo) > 60:
            hist_apolo.pop(0)

        # Registrar movimento do Apolo na memoria bayesiana da Umbra
        if len(hist_apolo) >= 2:
            dvx = hist_apolo[-1][0] - hist_apolo[-2][0]
            dvy = hist_apolo[-1][1] - hist_apolo[-2][1]
            agente_u.registrar_movimento_apolo(dvx, dvy)

        # ── APOLO: observar -> decidir -> agir ──────────────────────────────
        s_a = agente_a.obter_estado(apolo, umbra, projeteis, esferas, estado_ia)

        # Filtra acoes que nao saem do mapa
        MARG = 80
        ac_v = list(range(APOLO_OUTPUT_SIZE))
        if apolo.fy < MARG and 0 in ac_v:            ac_v.remove(0)
        if apolo.fy > ALTURA_MAPA  - MARG and 1 in ac_v: ac_v.remove(1)
        if apolo.fx < MARG and 2 in ac_v:            ac_v.remove(2)
        if apolo.fx > LARGURA_MAPA - MARG and 3 in ac_v: ac_v.remove(3)
        if not ac_v: ac_v = [4]

        acao_a = agente_a.decidir(s_a, ac_v)
        apolo.mover(acao_a, agora)

        # Disparo automatico em direcao a Umbra
        proj = apolo.disparar(
            umbra.fx + LARGURA_BOSS / 2,
            umbra.fy + ALTURA_BOSS  / 2,
            agora
        )
        if proj:
            projeteis.append(proj)

        # ── UMBRA: observar -> decidir -> agir ─────────────────────────────
        s_u = agente_u.obter_estado(umbra, apolo, projeteis, estado_ia, hist_apolo)
        acao_u = agente_u.decidir(s_u, agente_u.acoes_disponiveis(agora))
        executar_acao_umbra(agora, acao_u, umbra, apolo, estado_ia,
                             agente_u, projeteis, hist_apolo)

        # Movimento da Umbra
        if frame % 60 == 0:
            estrategia = random.choice(estrategias)
        alvo = calcular_alvo_umbra(apolo, umbra, estrategia)
        umbra.mover_para(alvo[0], alvo[1])

        # ── Fisica ─────────────────────────────────────────────────────────
        res = processar_colisoes(projeteis, apolo, umbra)
        coletou = processar_esferas(esferas, apolo)
        dano_arm = atualizar_armadilhas(agora, estado_ia, apolo)
        if dano_arm > 0:
            apolo.vida -= dano_arm

        # Esfera gerada pela Umbra periodicamente
        if agora - ultima_esfera >= INTERVALO_ESFERA:
            ex = umbra.fx + LARGURA_BOSS / 2 + random.uniform(-200, 200)
            ey = umbra.fy + ALTURA_BOSS  / 2 + random.uniform(-200, 200)
            ex = max(50.0, min(LARGURA_MAPA - 50.0, ex))
            ey = max(50.0, min(ALTURA_MAPA  - 50.0, ey))
            esferas.append(EsferaEnergia(ex, ey))
            ultima_esfera = agora

        # ── Condicao de fim ─────────────────────────────────────────────────
        morreu_a = apolo.vida <= 0
        morreu_u = umbra.vida <= 0

        # ── Recompensas ─────────────────────────────────────────────────────
        r_a = calcular_reward_apolo(
            apolo, umbra, projeteis, esferas, estado_ia,
            vida_a_ant, vida_u_ant, coletou,
            venceu=morreu_u, morreu=morreu_a
        )
        r_u = calcular_reward_umbra(
            acertou=res["acertou_apolo"],
            acao=acao_u,
            venceu=morreu_a,
            perdeu=morreu_u
        )

        # ── Proximo estado ──────────────────────────────────────────────────
        s_a_next = agente_a.obter_estado(apolo, umbra, projeteis, esferas, estado_ia)
        s_u_next = agente_u.obter_estado(umbra, apolo, projeteis, estado_ia, hist_apolo)

        done = morreu_a or morreu_u

        # ── Armazenar experiencias ─────────────────────────────────────────
        agente_a.armazenar(s_a, acao_a, r_a, s_a_next, done)
        agente_u.armazenar(s_u, acao_u, r_u, s_u_next, done)

        r_apolo_total += r_a
        r_umbra_total += r_u

        # ── Treino (a cada TREINO_FREQ frames) ─────────────────────────────
        if frame % TREINO_FREQ == 0:
            agente_a.treinar()
            agente_u.treinar()

        # ── Atualiza Target Networks ────────────────────────────────────────
        fg = frame_global + frame
        if fg % TARGET_UPDATE_FREQ == 0:
            agente_a.atualizar_target()
            agente_u.atualizar_target()

        vida_a_ant = apolo.vida
        vida_u_ant = umbra.vida

        # ── Fim do episodio ─────────────────────────────────────────────────
        if morreu_a:
            vencedor = "Umbra"; break
        if morreu_u:
            vencedor = "Apolo"; break

    return vencedor, r_apolo_total, r_umbra_total, float(frames), time.perf_counter() - t0


# =============================================================================
# PILAR 5 - LOOP DE TREINO PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("  TREINO ACELERADO DQN - RUPTURA TEMPORAL")
    print(f"  Episodios: {MAX_EPISODIOS:,}  |  Max frames/ep: {MAX_FRAMES_EP:,}")
    print(f"  Batch: {BATCH_SIZE}  |  Buffer: {BUFFER_SIZE:,}  |  gamma: {GAMMA}")
    print(f"  Epsilon: {EPSILON_INICIO:.2f} -> {EPSILON_FIM:.2f}  |  Decaimento: {EPSILON_DECAIMENTO}")
    print(f"  Apolo: {APOLO_INPUT_SIZE} inputs, {APOLO_OUTPUT_SIZE} outputs")
    print(f"  Umbra: {UMBRA_INPUT_SIZE} inputs, {UMBRA_OUTPUT_SIZE} outputs")
    print("=" * 70)

    eps_a = EPSILON_INICIO
    eps_u = EPSILON_INICIO

    agente_a = AgenteApolo(epsilon=eps_a)
    agente_u = AgenteUmbra(epsilon=eps_u)

    vit_a = 0;  vit_u = 0;  frame_global = 0
    rew_a_hist : Deque[float] = collections.deque(maxlen=LOG_INTERVALO)
    rew_u_hist : Deque[float] = collections.deque(maxlen=LOG_INTERVALO)
    win_hist   : Deque[int]   = collections.deque(maxlen=LOG_INTERVALO)
    fps_hist   : Deque[float] = collections.deque(maxlen=LOG_INTERVALO)
    t_ini = time.time()

    for ep in range(1, MAX_EPISODIOS + 1):
        agente_a.epsilon = eps_a
        agente_u.epsilon = eps_u

        venc, ra, ru, frames, dur = rodar_episodio(agente_a, agente_u, frame_global)
        frame_global += int(frames)

        if   venc == "Apolo": vit_a += 1; win_hist.append(1)
        elif venc == "Umbra": vit_u += 1; win_hist.append(0)
        else:                             win_hist.append(0)

        rew_a_hist.append(ra);  rew_u_hist.append(ru)
        fps_hist.append(frames / max(dur, 1e-9))

        # Decay do epsilon
        eps_a = max(EPSILON_FIM, eps_a * EPSILON_DECAIMENTO)
        eps_u = max(EPSILON_FIM, eps_u * EPSILON_DECAIMENTO)

        # Checkpoint
        if ep % SAVE_INTERVALO == 0:
            agente_a.salvar()
            agente_u.salvar()

        # Log
        if ep % LOG_INTERVALO == 0:
            wr  = sum(win_hist) / max(1, len(win_hist)) * 100.0
            ra_m = sum(rew_a_hist) / max(1, len(rew_a_hist))
            ru_m = sum(rew_u_hist) / max(1, len(rew_u_hist))
            la_m = agente_a.loss_media()
            lu_m = agente_u.loss_media()
            fps_m = sum(fps_hist) / max(1, len(fps_hist))
            buf_a = len(agente_a.buffer) / BUFFER_SIZE * 100
            buf_u = len(agente_u.buffer) / BUFFER_SIZE * 100
            elapsed = (time.time() - t_ini) / 60.0

            print(
                f"Ep {ep:>7,} "
                f"| Win Apolo: {wr:5.1f}% "
                f"| eA: {eps_a:.3f} eU: {eps_u:.3f} "
                f"| LossA: {la_m:.4f} LossU: {lu_m:.4f} "
                f"| rA: {ra_m:+.1f} rU: {ru_m:+.1f} "
                f"| FPS: {fps_m:,.0f} "
                f"| Buf: {buf_a:.0f}%/{buf_u:.0f}% "
                f"| {elapsed:.1f}min"
            )

    # Salvamento final
    agente_a.salvar()
    agente_u.salvar()
    total_vit = vit_a + vit_u
    total_min = (time.time() - t_ini) / 60.0
    print("\n" + "=" * 70)
    print("  TREINO CONCLUIDO!")
    print(f"  Tempo total    : {total_min:.1f} min")
    print(f"  Vitorias Apolo : {vit_a:,} ({vit_a / max(1, total_vit) * 100:.1f}%)")
    print(f"  Vitorias Umbra : {vit_u:,} ({vit_u / max(1, total_vit) * 100:.1f}%)")
    print(f"  Pesos salvos   : '{ARQUIVO_APOLO}' e '{ARQUIVO_UMBRA}'")
    print("=" * 70)


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    main()
