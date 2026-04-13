"""
================================================================================
  TREINO PARALELO GPU - RUPTURA TEMPORAL
  treino_paralelo_gpu_dqn.py
================================================================================

Arquitetura de 3 Camadas:
  [Camada 1 - CPU Workers]   N processos rodando simulacao headless em paralelo.
                              Cada worker coleta experiencias (s,a,r,s',done) e
                              as envia para a fila central via multiprocessing.Queue.

  [Camada 2 - Replay Buffer] Buffer circular global no processo principal (RAM).
                              Recebe experiencias de todos os workers de forma
                              assíncrona e alimenta o processo de treinamento.

  [Camada 3 - GPU Trainer]   Processo principal com redes neurais na VRAM da
                              GTX 1650. Faz loss.backward() e optimizer.step()
                              com batch_size grande (256/512). Periodicamente
                              transmite pesos atualizados para todos os workers.

Hardware Alvo:
  CPU: AMD Ryzen 5 4600G (6C/12T) ─ roda os workers de simulacao
  RAM: 16GB                        ─ hospeda o Replay Buffer global
  GPU: NVIDIA GTX 1650 (4GB VRAM) ─ computa gradientes e atualiza pesos

Fluxo de dados:
  Worker_0 ──┐
  Worker_1 ──┤──> [experience_queue] ──> [ReplayBuffer] ──> [Trainer GPU]
  ...        ──┤                                                    │
  Worker_N ──┘   <─────────── [weight_queue] ─────────────────────┘
================================================================================
"""

# ==============================================================================
# IMPORTS E CONFIGURACAO DE AMBIENTE HEADLESS
# IMPORTANTE: os.environ deve ser definido ANTES de qualquer import do pygame.
# Como este arquivo e importado tanto no processo principal quanto nos workers,
# essa configuracao e aplicada em todos os contextos automaticamente.
# ==============================================================================
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

# --- Imports padrao ---
import math
import random
import time
import collections
import signal
import sys
from typing import List, Dict, Optional, Tuple, Deque

# --- Multiprocessing ---
# Usamos 'spawn' explicitamente para garantir compatibilidade com CUDA.
# CUDA nao e compativel com o metodo 'fork' do Linux/Mac, e o metodo
# padrao do Windows ja e 'spawn'. Declaramos aqui para ser explicito.
import multiprocessing as mp
# torch.multiprocessing e um wrapper de mp que adiciona suporte a
# tensores em shared memory - usado para passar pesos entre processos.
import torch.multiprocessing as tmp_mp

# --- PyTorch ---
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

# --- Pygame (importado DEPOIS dos envs, sera inicializado em cada processo) ---
import pygame


# ==============================================================================
# SECAO 1: HIPERPARAMETROS GLOBAIS
# Todos os processos (principal e workers) importam estas constantes.
# ==============================================================================

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
INTERVALO_DISPARO  = 400
DANO_TIRO_APOLO    = 120
DANO_BOSS_HIT      = 90

# --- Atributos base da Umbra ---
VIDA_MAXIMA_UMBRA  = 45_000
VELOCIDADE_UMBRA   = 3.0
VELOCIDADE_PROJ    = 11

# --- Esferas de cura ---
CURA_ESFERA        = 80
INTERVALO_ESFERA   = 8_000

# --- DQN (GPU pode suportar batches muito maiores) ---
# GTX 1650 tem 4GB VRAM. Com MLP 128->64, o batch pode ser grande sem overflow.
BATCH_SIZE         = 512        # >> 64 do script original. Aproveita a GPU.
BUFFER_SIZE        = 200_000    # Buffer maior = diversidade de experiencias
LR_APOLO           = 3e-4
LR_UMBRA           = 3e-4
GAMMA              = 0.97
TARGET_UPDATE_FREQ = 500        # Steps globais entre updates do target network
WEIGHT_SYNC_FREQ   = 100        # Steps globais: com que frequencia enviar pesos aos workers

# --- Epsilon-Greedy ---
# O epsilon e gerenciado GLOBALMENTE pelo processo principal e
# transmitido para os workers junto com os pesos.
EPSILON_INICIO     = 1.0
EPSILON_FIM        = 0.05
EPSILON_DECAIMENTO = 0.9995     # Decay mais suave - mais episodios totais agora

# --- Multiprocessing ---
NUM_WORKERS           = 8       # 8 workers para o Ryzen 5 4600G (6C/12T)
                                 # Deixamos 2 threads para o processo principal + OS.
MAX_FRAMES_EP         = 4_000
MAX_EP_POR_WORKER     = 2_000_000  # Cada worker pode rodar muitos episodios
QUEUE_MAX_SIZE        = 2_000   # Tamanho maximo da fila de experiencias
                                 # (previne RAM overflow se GPU estiver lenta)
EXPERIENCIAS_POR_ENVIO = 128   # Worker agrupa N experiencias antes de enviar.
                                 # PILAR 2 (IPC Bottleneck Fix): valor maior reduz
                                 # drasticamente as chamadas put_nowait() por segundo,
                                 # removendo o gargalo de serializacao pickle com 8 workers
                                 # a >1000 FPS cada. 128 * 2 (apolo+umbra) * 8 workers =
                                 # ~2048 exp/envio no pior caso, mantendo a fila fluida.

# --- Loop de Treino ---
LOG_INTERVALO      = 500        # Steps globais entre logs no processo principal
SAVE_INTERVALO     = 2_000      # Steps globais entre salvamentos

# --- Arquivos de persistencia (mesmos do script original) ---
ARQUIVO_APOLO = "apolo_memoria_dqn.pt"
ARQUIVO_UMBRA = "memoria_umbra_dqn.pt"

# --- Network shapes (identico ao GAME5.py e treino_acelerado_dqn.py) ---
APOLO_INPUT_SIZE  = 41
APOLO_OUTPUT_SIZE = 5
UMBRA_INPUT_SIZE  = 18
UMBRA_OUTPUT_SIZE = 22

# Acoes da Umbra (para conversao str <-> int nos workers CPU-only)
UMBRA_ACOES = [
    "FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR", "ATAQUE", "SIFON", "TELEPORTE",
    "TRANSMUTAR_VORTICE", "TRANSMUTAR_GRAVIDADE", "TRANSMUTAR_NECROSE",
    "TRANSMUTAR_RESSONANCIA", "TRANSMUTAR_HEMORRAGIA", "TRANSMUTAR_ATRITO",
    "TRANSMUTAR_RASTRO", "VORTICE", "PRISAO", "MIASMA", "DESCARGA_ELETRICA",
    "PRAGA_RATOS", "LASER_SOBRECARGA", "CAMINHO_ESPINHOS", "NENHUMA"
]


# ==============================================================================
# SECAO 2: REDE NEURAL (identica ao GAME5.py para compatibilidade de pesos)
# Instanciada tanto na GPU (processo principal) quanto na CPU (workers).
# ==============================================================================

class DQNNet(nn.Module):
    """
    Rede Q simples MLP 128->64.
    ARQUITETURA IDENTICA ao GAME5.py para carregar pesos existentes.

    - Processo Principal: instancia na GPU para treinamento.
    - Workers: instancia na CPU para inferencia rapida (forward pass only).
    """
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


# ==============================================================================
# SECAO 3: REPLAY BUFFER GLOBAL (roda no processo principal, na RAM)
# Thread-safe nao e necessario pois o processo principal e single-threaded
# do lado do buffer - ele so e acessado no loop principal.
# ==============================================================================

class ReplayBuffer:
    """
    Buffer de experiencias (s, a, r, s', done).
    Roda exclusivamente no processo principal.
    Amostras sao enviadas para a GPU para treinamento.
    """
    def __init__(self, capacidade: int):
        self.buffer: Deque = collections.deque(maxlen=capacidade)

    def adicionar_lote(self, experiencias: list):
        """Adiciona um lote de experiencias de uma vez (vindo dos workers)."""
        for exp in experiencias:
            self.buffer.append(exp)

    def amostrar(self, batch_size: int, device: torch.device):
        """
        Amostra um batch e converte para tensors JA no device GPU.
        Esta e a operacao critica - minimizar conversoes CPU->GPU.
        """
        amostras = random.sample(self.buffer, batch_size)
        # Descompacta: cada elemento e (s_np, a, r, s_next_np, done)
        # s_np e s_next_np sao listas de floats (nao tensors) para minimizar
        # overhead de serializacao nas Queues entre processos.
        estados, acoes, recompensas, proximos, dones = zip(*amostras)

        # Conversao para tensors GPU de uma vez so (operacao batched eficiente)
        s_t     = torch.tensor(estados,      dtype=torch.float32, device=device)
        a_t     = torch.tensor(acoes,        dtype=torch.long,    device=device)
        r_t     = torch.tensor(recompensas,  dtype=torch.float32, device=device)
        sn_t    = torch.tensor(proximos,     dtype=torch.float32, device=device)
        done_t  = torch.tensor(dones,        dtype=torch.float32, device=device)
        return s_t, a_t, r_t, sn_t, done_t

    def __len__(self) -> int:
        return len(self.buffer)


# ==============================================================================
# SECAO 4: SIMULACAO HEADLESS - OBJETOS DO AMBIENTE
# Estas classes sao usadas APENAS nos workers (CPU).
# Sao identicas ao treino_acelerado_dqn.py.
# ==============================================================================

class Projetil:
    def __init__(self, x: float, y: float, angulo: float, vel: float,
                 dano: int, dono: str = "umbra"):
        self.rect  = pygame.Rect(int(x), int(y), 12, 12)
        self.fx    = float(x)
        self.fy    = float(y)
        self.vx    = math.cos(angulo) * vel
        self.vy    = math.sin(angulo) * vel
        self.dano  = dano
        self.dono  = dono
        self.ativo = True

    def atualizar(self) -> bool:
        self.fx += self.vx;  self.fy += self.vy
        self.rect.x = int(self.fx);  self.rect.y = int(self.fy)
        if (self.fx < -50 or self.fx > LARGURA_MAPA + 50 or
                self.fy < -50 or self.fy > ALTURA_MAPA  + 50):
            self.ativo = False
        return self.ativo


class EsferaEnergia:
    def __init__(self, x: float, y: float, cura: int = CURA_ESFERA):
        self.rect  = pygame.Rect(int(x - 12), int(y - 12), 24, 24)
        self.cura  = cura
        self.ativo = True


# ==============================================================================
# PILAR 1 - MECANICA DOS RATOS (Praga dos Ratos / Dimensao da Transmutacao)
# ==============================================================================

# Constantes da habilidade
COOLDOWN_RATOS_MS      = 15_000  # 15 segundos de cooldown
TEMPO_VIDA_RATO_MS     = 5_000   # 5 segundos ate explodirem
VELOCIDADE_RATO        = 4.5     # px/frame (mais rapido que Apolo)
DANO_RATO              = 80      # Dano ao acertar Apolo
CURA_UMBRA_POR_RATO    = int(VIDA_MAXIMA_UMBRA * 0.04)  # 4% da vida maxima
RATOS_BASE             = 4       # Quantidade base por cast
# Posicoes de spawn: um em cada canto
_CANTOS_SPAWN = [
    (ESPACAMENTO,                          ESPACAMENTO),
    (LARGURA_MAPA - LARGURA_PERSON - ESPACAMENTO, ESPACAMENTO),
    (ESPACAMENTO,                          ALTURA_MAPA - ALTURA_PERSON - ESPACAMENTO),
    (LARGURA_MAPA - LARGURA_PERSON - ESPACAMENTO, ALTURA_MAPA - ALTURA_PERSON - ESPACAMENTO),
]


class Rato:
    """
    Entidade de perseguicao com tempo de vida limitado.
    Sem sprites - representado por Rect puro.

    Ciclo de vida:
      spawn_ms -> perseguicao ininterrupta -> colisao (hit) OU expiracao (esquiva).
    """
    LARGURA = 28
    ALTURA  = 22

    def __init__(self, x: float, y: float, tempo_spawn_ms: int):
        self.fx          = float(x)
        self.fy          = float(y)
        self.rect        = pygame.Rect(int(x), int(y), self.LARGURA, self.ALTURA)
        self.tempo_spawn = tempo_spawn_ms
        self.ativo       = True

    def atualizar(self, apolo: 'ApoloSim', agora: int) -> bool:
        """
        Move o rato em direcao ao Apolo.
        Desativa se o tempo de vida expirou.
        Retorna True enquanto ativo.
        """
        if agora - self.tempo_spawn >= TEMPO_VIDA_RATO_MS:
            self.ativo = False
            return False

        # Perseguicao: calcula vetor normalizado ate o centro do Apolo
        alvo_x = apolo.fx + LARGURA_PERSON / 2
        alvo_y = apolo.fy + ALTURA_PERSON  / 2
        dx     = alvo_x - (self.fx + self.LARGURA / 2)
        dy     = alvo_y - (self.fy + self.ALTURA  / 2)
        dist   = math.hypot(dx, dy)
        if dist > 0:
            self.fx += (dx / dist) * VELOCIDADE_RATO
            self.fy += (dy / dist) * VELOCIDADE_RATO

        # Mantém dentro dos limites do mapa
        self.fx = max(0.0, min(float(LARGURA_MAPA - self.LARGURA), self.fx))
        self.fy = max(0.0, min(float(ALTURA_MAPA  - self.ALTURA),  self.fy))
        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)
        return True


def spawnar_ratos(agora: int, ratos_extras: int) -> List['Rato']:
    """
    Instancia a horda de ratos nos 4 cantos + extras (ratos que acertaram antes).
    ratos_extras: acumulador persistente de ratos adicionais por cast.
    Extra rats alem dos 4 base surgem em posicoes aleatorias nas bordas.
    """
    novos: List[Rato] = []
    # 4 ratos base - um em cada canto
    for (cx, cy) in _CANTOS_SPAWN:
        novos.append(Rato(cx, cy, agora))
    # Extras: surgem em bordas aleatorias
    for _ in range(ratos_extras):
        lado = random.randint(0, 3)
        if lado == 0:   ex, ey = random.uniform(0, LARGURA_MAPA), float(ESPACAMENTO)
        elif lado == 1: ex, ey = random.uniform(0, LARGURA_MAPA), float(ALTURA_MAPA - ESPACAMENTO)
        elif lado == 2: ex, ey = float(ESPACAMENTO),              random.uniform(0, ALTURA_MAPA)
        else:           ex, ey = float(LARGURA_MAPA - ESPACAMENTO), random.uniform(0, ALTURA_MAPA)
        novos.append(Rato(ex, ey, agora))
    return novos


def processar_ratos(agora: int,
                    ratos: List[Rato],
                    apolo: 'ApoloSim',
                    umbra: 'UmbraSim',
                    acumulador_ratos: List[int]) -> Dict:
    """
    Atualiza todos os ratos: move, detecta colisao e expiracao.

    Retorna:
      hits      : quantos ratos acertaram o Apolo neste frame
      expirados : quantos ratos explodiram sem acertar (Apolo esquivou)

    Efeitos colaterais:
      - Apolo recebe DANO_RATO por cada hit
      - Umbra regenera CURA_UMBRA_POR_RATO por cada hit
      - acumulador_ratos[0] += 1 por cada hit (buff permanente no episodio)
      - Ratos inativos sao removidos da lista in-place
    """
    hits      = 0
    expirados = 0
    vivos: List[Rato] = []

    for r in ratos:
        if not r.ativo:
            continue

        expirou_antes = (agora - r.tempo_spawn >= TEMPO_VIDA_RATO_MS)
        r.atualizar(apolo, agora)

        if r.rect.colliderect(apolo.rect):
            # Colisao: aplica dano e cura, incrementa acumulador
            apolo.vida -= float(DANO_RATO)
            umbra.vida  = min(float(VIDA_MAXIMA_UMBRA), umbra.vida + float(CURA_UMBRA_POR_RATO))
            acumulador_ratos[0] += 1   # Buff permanente
            r.ativo = False
            hits   += 1
        elif not r.ativo and not expirou_antes:
            # O rato ficou inativo durante atualizar() = expirou neste frame
            expirados += 1
        elif not r.ativo:
            expirados += 1
        else:
            vivos.append(r)

    ratos.clear()
    ratos.extend(vivos)
    return {'hits': hits, 'expirados': expirados}


class ApoloSim:
    def __init__(self):
        self.reset()

    def reset(self):
        self.fx = float(random.randint(ESPACAMENTO, LARGURA_MAPA - LARGURA_PERSON - ESPACAMENTO))
        self.fy = float(random.randint(ESPACAMENTO, ALTURA_MAPA  - ALTURA_PERSON  - ESPACAMENTO))
        self.rect           = pygame.Rect(int(self.fx), int(self.fy), LARGURA_PERSON, ALTURA_PERSON)
        self.vida           = float(VIDA_MAXIMA_APOLO)
        self.cooldown_dash  = False
        self.tempo_dash     = 0
        self.tempo_disparo  = 0
        self.ultima_direcao = 'right'

    def mover(self, acao: int, agora: int) -> Tuple[float, float]:
        dx, dy = 0.0, 0.0
        if   acao == 0: dy = -1.0; self.ultima_direcao = 'up'
        elif acao == 1: dy =  1.0; self.ultima_direcao = 'down'
        elif acao == 2: dx = -1.0; self.ultima_direcao = 'left'
        elif acao == 3: dx =  1.0; self.ultima_direcao = 'right'
        elif acao == 4 and not self.cooldown_dash:
            mult = DISTANCIA_DASH / max(VELOCIDADE_APOLO, 1e-6)
            if   self.ultima_direcao == 'up':    dy = -mult
            elif self.ultima_direcao == 'down':  dy =  mult
            elif self.ultima_direcao == 'left':  dx = -mult
            elif self.ultima_direcao == 'right': dx =  mult
            self.cooldown_dash = True
            self.tempo_dash    = agora
        self.fx = max(0.0, min(float(LARGURA_MAPA - LARGURA_PERSON), self.fx + dx * VELOCIDADE_APOLO))
        self.fy = max(0.0, min(float(ALTURA_MAPA  - ALTURA_PERSON),  self.fy + dy * VELOCIDADE_APOLO))
        self.rect.x = int(self.fx);  self.rect.y = int(self.fy)
        if self.cooldown_dash and (agora - self.tempo_dash) >= COOLDOWN_DASH_MS:
            self.cooldown_dash = False
        return dx * VELOCIDADE_APOLO, dy * VELOCIDADE_APOLO

    def disparar(self, alvo_x: float, alvo_y: float, agora: int) -> Optional[Projetil]:
        if (agora - self.tempo_disparo) < INTERVALO_DISPARO:
            return None
        cx = self.fx + LARGURA_PERSON / 2;  cy = self.fy + ALTURA_PERSON / 2
        ang = math.atan2(alvo_y - cy, alvo_x - cx)
        self.tempo_disparo = agora
        return Projetil(cx, cy, ang, VELOCIDADE_APOLO * 2.8, DANO_TIRO_APOLO, dono="apolo")

    def em_canto(self, m: int = 100) -> bool:
        nas_x = (self.fx < m or self.fx > LARGURA_MAPA - LARGURA_PERSON - m)
        nas_y = (self.fy < m or self.fy > ALTURA_MAPA  - ALTURA_PERSON  - m)
        return nas_x and nas_y


class UmbraSim:
    def __init__(self):
        self.reset()

    def reset(self):
        self.fx   = float(LARGURA_MAPA // 2 - LARGURA_BOSS // 2)
        self.fy   = float(ALTURA_MAPA  // 2 - ALTURA_BOSS  // 2)
        self.rect = pygame.Rect(int(self.fx), int(self.fy), LARGURA_BOSS, ALTURA_BOSS)
        self.vida  = float(VIDA_MAXIMA_UMBRA)
        self.vel_x = 0.0;  self.vel_y = 0.0

    def mover_para(self, alvo_x: float, alvo_y: float):
        VEL_MAX = VELOCIDADE_UMBRA;  AGILIDADE = 0.25
        dx_a = alvo_x - self.fx;  dy_a = alvo_y - self.fy
        mag  = math.hypot(dx_a, dy_a)
        vx_d = (dx_a / mag) * VEL_MAX if mag > 0 else 0.0
        vy_d = (dy_a / mag) * VEL_MAX if mag > 0 else 0.0
        self.vel_x += (vx_d - self.vel_x) * AGILIDADE
        self.vel_y += (vy_d - self.vel_y) * AGILIDADE
        self.fx = max(float(ESPACAMENTO), min(float(LARGURA_MAPA - LARGURA_BOSS - ESPACAMENTO), self.fx + self.vel_x))
        self.fy = max(float(ESPACAMENTO), min(float(ALTURA_MAPA  - ALTURA_BOSS  - ESPACAMENTO), self.fy + self.vel_y))
        self.rect.x = int(self.fx);  self.rect.y = int(self.fy)

    def teleportar(self, ax: float, ay: float):
        self.fx = max(float(ESPACAMENTO), min(float(LARGURA_MAPA - LARGURA_BOSS - ESPACAMENTO), ax))
        self.fy = max(float(ESPACAMENTO), min(float(ALTURA_MAPA  - ALTURA_BOSS  - ESPACAMENTO), ay))
        self.rect.x = int(self.fx);  self.rect.y = int(self.fy)


# ==============================================================================
# SECAO 5: LOGICA DE ESTADO (identica ao treino_acelerado_dqn.py)
# Estas funcoes rodam nos workers (CPU). Retornam listas de floats
# (NAO tensors) para que possam ser serializadas eficientemente pelas Queues.
# ==============================================================================

def _criar_estado_ia() -> Dict:
    return {
        'ultimo_ataque': 0, 'intervalo': 1200, 'projeteis': [],
        'fase_tele': "espera", 'proj_tele': None, 'dano_recente': 0,
        'ultimo_teleporte': 0, 'parede_ativa': False, 'ultimo_parede': 0,
        'ultimo_tick_cura': 0, 'vel_x': 0, 'vel_y': 0,
        'alvo_ia': (LARGURA_MAPA // 2, ALTURA_MAPA // 2),
        'ultimo_vortice': 0, 'ultimo_prisao': 0, 'ultimo_miasma': 0,
        'ultimo_descarga': 0, 'ultimo_espinhos': 0, 'ultimo_laser': 0,
        'ultimo_bordas': 0, 'vortice_ativo': None, 'prisao_ativa': None,
        'caminho_espinhos': None, 'laser_ativo': None, 'descarga_eletrica': None,
        'bordas_ativas': None, 'miasma_ativo': None,
        'mapa_atual': "Sprites/Fase5-1.png", 'decisoes_ativas': [],
        'centro_mapa': (LARGURA_MAPA // 2, ALTURA_MAPA // 2),
        'espinho_padrao_ultimo': 'B', 'f_fuga_x': 0, 'f_fuga_y': 0,
    }


def obter_estado_apolo_cpu(apolo: 'ApoloSim', umbra: 'UmbraSim',
                            projeteis: List[Projetil],
                            esferas: List[EsferaEnergia],
                            estado_ia: Dict,
                            ratos: Optional[List[Rato]] = None) -> List[float]:
    """
    Retorna uma LISTA DE FLOATS (nao tensor) com 41 features.
    Features 30-33 agora contem informacao REAL dos ratos (antes zeradas).

    Indices dos campos de ratos no vetor (posicoes 30-33):
      30: qtd_ratos  - quantidade normalizada de ratos ativos (0..1)
      31: dist_rato  - distancia ao rato mais proximo, normalizada (1.0 = longe/seguro)
      32: rato_dx    - componente x do vetor ao rato mais proximo
      33: rato_dy    - componente y do vetor ao rato mais proximo
    """
    px = apolo.fx + LARGURA_PERSON / 2;  py = apolo.fy + ALTURA_PERSON  / 2
    bx = umbra.fx + LARGURA_BOSS   / 2;  by = umbra.fy + ALTURA_BOSS    / 2

    f_px = px / LARGURA_MAPA;  f_py = py / ALTURA_MAPA
    f_bx = bx / LARGURA_MAPA;  f_by = by / ALTURA_MAPA
    f_va = apolo.vida / VIDA_MAXIMA_APOLO;  f_vb = umbra.vida / VIDA_MAXIMA_UMBRA

    M = 100.0
    f_de  = min(1.0, apolo.fx / M)
    f_dd  = min(1.0, (LARGURA_MAPA - apolo.fx) / M)
    f_dc  = min(1.0, apolo.fy / M)
    f_db  = min(1.0, (ALTURA_MAPA  - apolo.fy) / M)
    f_can = 1.0 if apolo.em_canto() else 0.0

    dist_p, dpx_f, dpy_f = 1.0, 0.0, 0.0
    proximos = []
    for p in projeteis:
        if p.dono == "umbra" and p.ativo:
            d = math.hypot(p.rect.centerx - px, p.rect.centery - py)
            if d < 250:
                proximos.append((p.rect.centerx, p.rect.centery, d))
    if proximos:
        ex, ey, dp = min(proximos, key=lambda v: v[2])
        dist_p = dp / 250.0
        dpx_f  = (ex - px) / max(1.0, dp)
        dpy_f  = (ey - py) / max(1.0, dp)

    f_cd  = 1.0 if apolo.cooldown_dash else 0.0
    f_vp  = 0.5
    f_qe  = min(1.0, len(esferas) / 10.0)
    f_vbv = min(1.0, math.hypot(umbra.vel_x, umbra.vel_y) / (VELOCIDADE_UMBRA + 1e-6))
    f_las = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0]

    f_do, f_odx, f_ody = 1.0, 0.0, 0.0
    if esferas:
        eb = min(esferas, key=lambda e: math.hypot(e.rect.centerx - px, e.rect.centery - py))
        de = math.hypot(eb.rect.centerx - px, eb.rect.centery - py)
        f_do = min(1.0, de / 800.0)
        if de > 0:
            f_odx = (eb.rect.centerx - px) / de
            f_ody = (eb.rect.centery - py) / de

    # --- Features dos ratos (PILAR 1: agora com dados reais) ---
    # Antes estavam zeradas; agora a rede "ve" os ratos de verdade.
    ratos_ativos = [r for r in (ratos or []) if r.ativo]
    f_qtd_ratos  = min(1.0, len(ratos_ativos) / 8.0)   # norm: ate 8 ratos
    f_dist_rato  = 1.0;  f_rdx = 0.0;  f_rdy = 0.0
    if ratos_ativos:
        # Rato mais proximo ao Apolo = ameaca imediata
        mais_prox = min(
            ratos_ativos,
            key=lambda r: math.hypot(r.rect.centerx - px, r.rect.centery - py)
        )
        dr = math.hypot(mais_prox.rect.centerx - px, mais_prox.rect.centery - py)
        f_dist_rato = min(1.0, dr / 600.0)   # norm: 600px = tela inteira
        if dr > 0:
            f_rdx = (mais_prox.rect.centerx - px) / dr
            f_rdy = (mais_prox.rect.centery - py) / dr
    f_rat = [f_qtd_ratos, f_dist_rato, f_rdx, f_rdy]

    chaves_arm = ['vortice_ativo', 'prisao_ativa', 'caminho_espinhos',
                  'laser_ativo', 'descarga_eletrica', 'bordas_ativas', 'miasma_ativo']
    f_arm = [1.0 if estado_ia.get(k) else 0.0 for k in chaves_arm]

    return (
        [f_px, f_py, f_bx, f_by, f_va, f_vb,
         f_de, f_dd, f_dc, f_db, f_can,
         dist_p, dpx_f, dpy_f, f_cd, f_vp,
         f_qe, f_vbv] + f_las + [f_do, f_odx, f_ody] + f_rat + f_arm
    )


def obter_estado_umbra_cpu(umbra: UmbraSim, apolo: ApoloSim,
                            projeteis: List[Projetil],
                            estado_ia: Dict,
                            hist_apolo: List[Tuple[float, float]],
                            tendencias: Dict[str, float]) -> List[float]:
    """Retorna lista de 18 floats (identico ao habilidade_boss.py)."""
    bx = umbra.fx + LARGURA_BOSS   / 2;  by = umbra.fy + ALTURA_BOSS    / 2
    px = apolo.fx + LARGURA_PERSON / 2;  py = apolo.fy + ALTURA_PERSON  / 2

    vida_perc = umbra.vida / VIDA_MAXIMA_UMBRA
    dist_p    = math.hypot(bx - px, by - py)
    n_tiros   = float(sum(1 for p in projeteis if p.dono == "apolo" and p.ativo))

    vx_p, vy_p = 0.0, 0.0
    if hist_apolo and len(hist_apolo) >= 3:
        p1, p3 = hist_apolo[-3], hist_apolo[-1]
        vx_p = max(-1.0, min(1.0, (p3[0] - p1[0]) / 30.0))
        vy_p = max(-1.0, min(1.0, (p3[1] - p1[1]) / 30.0))

    dx = (bx - px) / 1000.0;  dy = (by - py) / 1000.0

    chaves = ['vortice_ativo', 'prisao_ativa', 'caminho_espinhos',
              'laser_ativo', 'descarga_eletrica', 'bordas_ativas', 'miasma_ativo']
    f_arm = [1.0 if estado_ia.get(k) else 0.0 for k in chaves]

    total = max(1.0, tendencias["TOTAL"])
    bx_b  = (tendencias["DIREITA"]  - tendencias["ESQUERDA"]) / total
    by_b  = (tendencias["BAIXO"]    - tendencias["CIMA"])     / total

    return [
        vida_perc, dist_p / 2000.0, min(1.0, n_tiros / 5.0),
        vx_p, vy_p, dx, dy, 1.0 if n_tiros > 0 else 0.0,
    ] + f_arm + [0.5, bx_b, by_b]


# ==============================================================================
# SECAO 6: SISTEMAS DE FISICA E HABILIDADES (usados nos workers)
# ==============================================================================

def calcular_reward_apolo(apolo: 'ApoloSim', umbra: 'UmbraSim',
                           projeteis: List[Projetil],
                           esferas: List[EsferaEnergia],
                           estado_ia: Dict,
                           vida_ant: float, vida_boss_ant: float,
                           coletou: bool, venceu: bool, morreu: bool,
                           hits_ratos: int = 0,
                           expirados_ratos: int = 0) -> float:
    """
    Calcula a recompensa do Apolo.
    PILAR 1: Novos parametros hits_ratos e expirados_ratos adicionam
    incentivo de esquiva tatica contra a Praga dos Ratos.
    """
    px = apolo.fx + LARGURA_PERSON / 2;  py = apolo.fy + ALTURA_PERSON  / 2
    r  = 0.3
    if venceu: return r + 500.0
    if morreu: return r - 500.0
    if apolo.vida - vida_ant < 0:       r -= 50.0
    if umbra.vida - vida_boss_ant < 0:  r += 30.0
    if coletou:                         r += 100.0

    # --- Recompensas dos Ratos (PILAR 1) ---
    # Penalidade severa por tomar hit de rato
    if hits_ratos > 0:
        r -= 80.0 * hits_ratos   # -80 por cada rato que acertou
    # Bonus por fazer todos os ratos expirarem sem ser atingido
    # (recompensa a esquiva tatica durante os 5 segundos)
    if expirados_ratos > 0 and hits_ratos == 0:
        r += 25.0 * expirados_ratos   # +25 por cada rato que expirou sem acertar

    MC, MP = 50, 100
    de = apolo.fx;  dd = LARGURA_MAPA - apolo.fx
    dc = apolo.fy;  db = ALTURA_MAPA  - apolo.fy
    if de < MC or dd < MC or dc < MC or db < MC: r -= 25.0
    elif de < MP or dd < MP or dc < MP or db < MP: r -= 8.0
    if apolo.em_canto(MP): r -= 40.0

    cx = LARGURA_MAPA / 2;  cy = ALTURA_MAPA / 2
    if math.hypot(px - cx, py - cy) < min(LARGURA_MAPA, ALTURA_MAPA) * 0.30: r += 3.0
    bx = umbra.fx + LARGURA_BOSS / 2;  by = umbra.fy + ALTURA_BOSS / 2
    db3 = math.hypot(bx - px, by - py)
    if 300 < db3 < 600: r += 1.0
    elif db3 < 200:     r -= 3.0

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

    for p in projeteis:
        if p.dono == "umbra" and p.ativo:
            if math.hypot(p.rect.centerx - px, p.rect.centery - py) < 80:
                r -= 20.0; break

    if estado_ia.get("vortice_ativo"):
        v = estado_ia["vortice_ativo"]
        dv = math.hypot(v['x'] - px, v['y'] - py)
        if dv < 150: r -= 30.0
        elif dv < 300: r -= 10.0

    return float(r)


def calcular_reward_umbra(acertou: bool, acao: str,
                           venceu: bool, perdeu: bool,
                           hits_ratos: int = 0) -> float:
    """
    Calcula a recompensa da Umbra.
    PILAR 1: hits_ratos adiciona recompensa positiva por acerto de rato.
    """
    r = 0.1
    if venceu: return r + 500.0
    if perdeu: return r - 500.0
    if acertou: r += 50.0
    if acao not in ("ATAQUE", "NENHUMA"): r -= 2.0
    # Bonus por ratos que acertaram: recompensa o cast estrategico da habilidade
    if hits_ratos > 0:
        r += 60.0 * hits_ratos   # +60 por cada rato que acertou o Apolo
    return float(r)


def atualizar_armadilhas(agora: int, estado_ia: Dict, apolo: ApoloSim) -> float:
    px = apolo.fx + LARGURA_PERSON / 2;  py = apolo.fy + ALTURA_PERSON  / 2
    dano = 0.0

    if estado_ia.get('vortice_ativo'):
        v = estado_ia['vortice_ativo']
        if agora - v['tempo_inicio'] > v['duracao']:
            estado_ia['vortice_ativo'] = None
        else:
            dx = v['x'] - px;  dy = v['y'] - py;  d = math.hypot(dx, dy)
            if d < 350 and d > 0:
                apolo.fx += (dx / d) * v['forca'];  apolo.fy += (dy / d) * v['forca']
                apolo.fx = max(0.0, min(float(LARGURA_MAPA - LARGURA_PERSON), apolo.fx))
                apolo.fy = max(0.0, min(float(ALTURA_MAPA  - ALTURA_PERSON),  apolo.fy))
                apolo.rect.x = int(apolo.fx);  apolo.rect.y = int(apolo.fy)

    if estado_ia.get('prisao_ativa'):
        p = estado_ia['prisao_ativa']
        if agora - p['tempo_inicio'] > p['duracao']: estado_ia['prisao_ativa'] = None
        elif p['rect'].colliderect(apolo.rect): dano += 8 * 0.016

    if estado_ia.get('miasma_ativo'):
        m = estado_ia['miasma_ativo']
        if agora - m['tempo_inicio'] > m['duracao']: estado_ia['miasma_ativo'] = None
        else: dano += 5 * 0.016

    if estado_ia.get('descarga_eletrica'):
        dc = estado_ia['descarga_eletrica']
        if agora - dc['tempo_inicio'] > dc['duracao']: estado_ia['descarga_eletrica'] = None
        else:
            dy2 = py - dc['y'];  dx2 = px - dc['x'];  d = math.hypot(dx2, dy2)
            if d < dc['raio_maximo']:
                ang  = math.atan2(dy2, dx2)
                diff = abs(ang - dc['angulo_base']) % (2 * math.pi)
                if diff > math.pi: diff = 2 * math.pi - diff
                if diff < dc['abertura'] / 2: dano += dc['dano_por_tick'] * 0.016

    if estado_ia.get('caminho_espinhos'):
        ce = estado_ia['caminho_espinhos']
        elapsed = agora - ce['tempo_inicio']
        if elapsed > ce['duracao_crescimento'] + ce['duracao_expansao']:
            estado_ia['caminho_espinhos'] = None
        elif ce['padrao'] == 'A':
            cx2 = LARGURA_MAPA / 2;  cy2 = ALTURA_MAPA / 2
            for raio in ce.get('raios', []):
                ang = raio.get('angulo', 0)
                for t in range(0, int(raio.get('comprimento', 1200)), 30):
                    rx = cx2 + math.cos(ang) * t;  ry = cy2 + math.sin(ang) * t
                    if math.hypot(rx - px, ry - py) < 45: dano += 20.0; break

    return dano


def processar_colisoes(projeteis: List[Projetil],
                        apolo: ApoloSim, umbra: UmbraSim) -> Dict:
    acertou_a = False;  acertou_u = False;  vivos: List[Projetil] = []
    for p in projeteis:
        if not p.ativo: continue
        p.atualizar()
        if not p.ativo: continue
        if p.dono == "umbra" and p.rect.colliderect(apolo.rect):
            apolo.vida -= float(p.dano);  acertou_a = True;  p.ativo = False
        elif p.dono == "apolo" and p.rect.colliderect(umbra.rect):
            umbra.vida -= float(p.dano);  acertou_u = True;  p.ativo = False
        if p.ativo: vivos.append(p)
    projeteis.clear();  projeteis.extend(vivos)
    return {"acertou_apolo": acertou_a, "acertou_umbra": acertou_u}


def processar_esferas(esferas: List[EsferaEnergia], apolo: ApoloSim) -> bool:
    coletou = False;  vivas: List[EsferaEnergia] = []
    for e in esferas:
        if e.ativo and e.rect.colliderect(apolo.rect):
            apolo.vida = min(float(VIDA_MAXIMA_APOLO), apolo.vida + e.cura)
            coletou = True;  e.ativo = False
        elif e.ativo: vivas.append(e)
    esferas.clear();  esferas.extend(vivas)
    return coletou


def executar_acao_umbra(agora: int, acao: str,
                         umbra: UmbraSim, apolo: ApoloSim,
                         estado_ia: Dict, cd: Dict,
                         projeteis: List[Projetil],
                         hist_apolo: List[Tuple[float, float]]) -> None:
    bx = umbra.fx + LARGURA_BOSS   / 2;  by = umbra.fy + ALTURA_BOSS    / 2
    px = apolo.fx + LARGURA_PERSON / 2;  py = apolo.fy + ALTURA_PERSON  / 2

    if acao == "ATAQUE":
        if agora - cd.get("ataque", 0) >= estado_ia.get("intervalo", 1200):
            dist = math.hypot(px - bx, py - by)
            t_voo = dist / max(VELOCIDADE_PROJ, 1e-6)
            vax, vay = 0.0, 0.0
            if len(hist_apolo) >= 2:
                vax = px - (hist_apolo[-2][0] + LARGURA_PERSON / 2)
                vay = py - (hist_apolo[-2][1] + ALTURA_PERSON  / 2)
            fator = max(0.55, 1.0 - dist / 1800.0)
            ax = max(50.0, min(LARGURA_MAPA - 50.0, px + vax * t_voo * fator))
            ay = max(50.0, min(ALTURA_MAPA  - 50.0, py + vay * t_voo * fator))
            ang = math.atan2(ay - by, ax - bx)
            projeteis.append(Projetil(bx, by, ang, float(VELOCIDADE_PROJ), DANO_BOSS_HIT, "umbra"))
            cd["ataque"] = agora

    elif acao == "TELEPORTE":
        ang_p  = math.atan2(py - by, px - bx)
        ang_fl = ang_p + random.choice([math.pi / 2, -math.pi / 2])
        umbra.teleportar(px + math.cos(ang_fl) * 450, py + math.sin(ang_fl) * 450)
        cd["teleporte"] = agora

    elif acao == "VORTICE":
        estado_ia['vortice_ativo'] = {
            'x': LARGURA_MAPA / 2, 'y': ALTURA_MAPA / 2,
            'tempo_inicio': agora, 'duracao': 8000, 'forca': 2.8
        }
        cd["vortice"] = agora

    elif acao == "PRISAO":
        if len(hist_apolo) >= 5:
            vax = px - (hist_apolo[-5][0] + LARGURA_PERSON / 2)
            vay = py - (hist_apolo[-5][1] + ALTURA_PERSON  / 2)
            ax = max(80.0, min(LARGURA_MAPA-80.0, px + vax * 6))
            ay = max(80.0, min(ALTURA_MAPA -80.0, py + vay * 6))
        else:
            ax, ay = px, py
        estado_ia['prisao_ativa'] = {
            'rect': pygame.Rect(int(ax-60), int(ay-60), 120, 120),
            'tempo_inicio': agora, 'duracao': 3500, 'x': ax, 'y': ay
        }
        cd["prisao"] = agora

    elif acao == "MIASMA":
        estado_ia['miasma_ativo'] = {'tempo_inicio': agora, 'duracao': 4500}
        cd["miasma"] = agora

    elif acao == "DESCARGA_ELETRICA":
        ang_d = math.atan2(py - by, px - bx)
        estado_ia['descarga_eletrica'] = {
            'x': bx, 'y': by, 'angulo_base': ang_d, 'raio_maximo': 380.0,
            'abertura': 0.9, 'duracao': 1800, 'tempo_inicio': agora, 'dano_por_tick': 12
        }
        cd["descarga"] = agora

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
            'duracao_crescimento': 1800, 'duracao_expansao': 1600, 'ultimo_espinho_hit': 0
        }
        cd["espinhos"] = agora


def _acoes_umbra_disponiveis(agora: int, cd: Dict) -> List[str]:
    disp = ["ATAQUE"]
    if agora - cd.get("teleporte", 0) >= 10_000: disp.append("TELEPORTE")
    if agora - cd.get("vortice",   0) >= 12_000: disp.append("VORTICE")
    if agora - cd.get("prisao",    0) >=  9_000: disp.append("PRISAO")
    if agora - cd.get("miasma",    0) >= 10_000: disp.append("MIASMA")
    if agora - cd.get("descarga",  0) >= 11_000: disp.append("DESCARGA_ELETRICA")
    if agora - cd.get("espinhos",  0) >=  8_000: disp.append("CAMINHO_ESPINHOS")
    # PILAR 1: Praga dos Ratos disponivel apos 15 segundos
    if agora - cd.get("ratos",     0) >= COOLDOWN_RATOS_MS:  disp.append("PRAGA_RATOS")
    disp.append("NENHUMA")
    return [a for a in disp if a in UMBRA_ACOES]


def _calcular_alvo_umbra(apolo: ApoloSim, umbra: UmbraSim,
                          estrategia: str) -> Tuple[float, float]:
    bx = umbra.fx + LARGURA_BOSS   / 2;  by = umbra.fy + ALTURA_BOSS   / 2
    px = apolo.fx + LARGURA_PERSON / 2;  py = apolo.fy + ALTURA_PERSON / 2
    if estrategia == "FUGIR":
        ang = math.atan2(by - py, bx - px)
        ax = bx + math.cos(ang) * 600;  ay = by + math.sin(ang) * 600
    elif estrategia == "INTERCEPTAR":
        ax = px + (px - bx) * 0.3;  ay = py + (py - by) * 0.3
    elif estrategia == "ORBITAR":
        ang = math.atan2(by - py, bx - px) + 0.7
        ax = px + math.cos(ang) * 450;  ay = py + math.sin(ang) * 450
    else:
        ang = math.atan2(by - py, bx - px)
        ax = px + math.cos(ang) * 300;  ay = py + math.sin(ang) * 300
    ax = max(float(ESPACAMENTO), min(float(LARGURA_MAPA - LARGURA_BOSS - ESPACAMENTO), ax))
    ay = max(float(ESPACAMENTO), min(float(ALTURA_MAPA  - ALTURA_BOSS  - ESPACAMENTO), ay))
    return ax, ay


# ==============================================================================
# SECAO 7: POLITICA LOCAL DO WORKER (CPU-only, sem optimizer)
#
# Cada worker tem cópias locais das redes (Policy Nets) somente para
# inferencia (forward pass). Nao ha backward() aqui.
# Os pesos sao periodicamente substituidos pelos pesos globais GPU.
# ==============================================================================

class PoliticaLocalCPU:
    """
    Copia local da politica para inferencia nos workers.
    Roda 100% na CPU. Nao tem optimizer nem buffer proprio.
    So faz forward pass para decidir acoes.
    """
    def __init__(self, input_size: int, output_size: int, epsilon: float):
        self.net        = DQNNet(input_size, output_size)   # Sempre na CPU
        self.net.eval()                                      # Modo inferencia
        self.output_size = output_size
        self.epsilon     = epsilon

    def decidir(self, estado_lista: List[float],
                acoes_validas: Optional[List[int]] = None) -> int:
        """
        Inferencia greedy-epsilon usando estado como lista de floats.
        acoes_validas: lista de indices inteiros validos (None = todos).
        """
        if acoes_validas is None:
            acoes_validas = list(range(self.output_size))
        if not acoes_validas:
            return 0
        if random.random() < self.epsilon:
            return random.choice(acoes_validas)
        # Converte para tensor CPU para forward pass
        with torch.no_grad():
            x = torch.tensor(estado_lista, dtype=torch.float32).unsqueeze(0)
            q = self.net(x)[0]
            # Mascara acoes invalidas
            for i in range(self.output_size):
                if i not in acoes_validas:
                    q[i] = -1e9
        return int(q.argmax().item())

    def decidir_umbra(self, estado_lista: List[float],
                      acoes_disp: List[str]) -> str:
        """Variante para a Umbra que trabalha com strings de acoes."""
        validas = [a for a in acoes_disp if a in UMBRA_ACOES]
        if not validas:
            return "NENHUMA"
        if random.random() < self.epsilon:
            return random.choice(validas)
        indices = [UMBRA_ACOES.index(a) for a in validas]
        with torch.no_grad():
            x = torch.tensor(estado_lista, dtype=torch.float32).unsqueeze(0)
            q = self.net(x)[0]
            best_i = max(indices, key=lambda i: q[i].item())
        return UMBRA_ACOES[best_i]

    def sincronizar_pesos(self, state_dict_cpu: dict):
        """
        Recebe um state_dict (CPU) e substitui os pesos locais.
        Chamado quando o processo principal transmite pesos atualizados.
        """
        self.net.load_state_dict(state_dict_cpu)
        self.net.eval()


# ==============================================================================
# SECAO 8: FUNCAO DO WORKER (roda em processo separado)
#
# FLUXO DE CADA WORKER:
#   1. Recebe pesos iniciais via weight_queue
#   2. Roda episodio headless coletando (s_lista, a, r, s_next_lista, done)
#   3. Agrupa EXPERIENCIAS_POR_ENVIO experiencias em um lote
#   4. Envia lote para exp_queue (processo principal le e adiciona ao buffer)
#   5. Checa weight_queue por novos pesos (nao-bloqueante)
#   6. Repete ate receber sinal de parada (None na weight_queue inicial)
# ==============================================================================

def worker_fn(worker_id: int,
              exp_queue: mp.Queue,       # Worker -> Principal (experiencias)
              weight_queue: mp.Queue,    # Principal -> Worker (pesos + epsilon)
              stats_queue: mp.Queue,     # Worker -> Principal (metricas de ep)
              stop_event: mp.Event):     # Sinal de parada do processo principal
    """
    Funcao executada em cada processo worker.
    Roda simulacao headless e gera experiencias para o processo principal.

    Parametros:
      worker_id    : Identificador unico do worker (0..N-1)
      exp_queue    : Fila para enviar tuplas de experiencia ao buffer global
      weight_queue : Fila para receber pesos atualizados do processo principal
      stats_queue  : Fila para enviar estatisticas (vencedor, duração) ao log
      stop_event   : Event que sinaliza parada graceful de todos os workers
    """
    # ── Configuracao do processo ──────────────────────────────────────────────
    # Cada proceso inicializa seu proprio pygame headless
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    pygame.display.set_mode((1, 1), flags=pygame.NOFRAME)

    # Seed diferente por worker para diversificacao de exploração
    random.seed(worker_id * 1000 + int(time.time()) % 10000)

    # ── Politicas locais (CPU) ─────────────────────────────────────────────────
    pol_apolo = PoliticaLocalCPU(APOLO_INPUT_SIZE, APOLO_OUTPUT_SIZE, EPSILON_INICIO)
    pol_umbra = PoliticaLocalCPU(UMBRA_INPUT_SIZE, UMBRA_OUTPUT_SIZE, EPSILON_INICIO)
    epsilon   = EPSILON_INICIO

    # ── Cooldowns da Umbra (estado local do worker) ───────────────────────────
    cd_umbra = {
        "ataque": 0, "teleporte": 0, "vortice": 0,
        "prisao": 0, "miasma": 0,   "descarga": 0,
        "espinhos": 0, "ratos": 0,   # PILAR 1: cooldown da Praga dos Ratos
    }

    # ── Tendencias Bayesianas (estado local do worker) ────────────────────────
    tendencias = {"TOTAL": 0.0, "ESQUERDA": 0.0, "DIREITA": 0.0, "CIMA": 0.0, "BAIXO": 0.0}

    # Aguarda o primeiro lote de pesos do processo principal
    try:
        pesos_iniciais = weight_queue.get(timeout=30)
        if pesos_iniciais is None:
            return   # Sinal de parada imediata
        pol_apolo.sincronizar_pesos(pesos_iniciais['apolo'])
        pol_umbra.sincronizar_pesos(pesos_iniciais['umbra'])
        epsilon = pesos_iniciais.get('epsilon_apolo', EPSILON_INICIO)
        pol_apolo.epsilon = epsilon
        pol_umbra.epsilon = pesos_iniciais.get('epsilon_umbra', EPSILON_INICIO)
    except Exception:
        return

    # ── Buffer local temporario de experiencias ───────────────────────────────
    # Acumulamos experiencias localmente e enviamos em lotes para reduzir
    # o overhead de comunicacao IPC (cada put() tem custo de serializacao).
    lote_exp_apolo: List[Tuple] = []
    lote_exp_umbra: List[Tuple] = []

    estrategias = ["FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR"]

    # ── Loop principal do worker ──────────────────────────────────────────────
    while not stop_event.is_set():

        # ── Checa por novos pesos (nao-bloqueante) ──────────────────────────
        # Usamos get_nowait() para verificar sem bloquear o loop de simulacao.
        try:
            novos_pesos = weight_queue.get_nowait()
            if novos_pesos is None:
                break   # Sinal de parada
            pol_apolo.sincronizar_pesos(novos_pesos['apolo'])
            pol_umbra.sincronizar_pesos(novos_pesos['umbra'])
            pol_apolo.epsilon = novos_pesos.get('epsilon_apolo', pol_apolo.epsilon)
            pol_umbra.epsilon = novos_pesos.get('epsilon_umbra', pol_umbra.epsilon)
        except Exception:
            pass   # Normal - fila vazia

        # ── Episodio ─────────────────────────────────────────────────────────
        apolo      = ApoloSim()
        umbra      = UmbraSim()
        estado_ia  = _criar_estado_ia()
        projeteis  : List[Projetil]            = []
        esferas    : List[EsferaEnergia]       = []
        hist_apolo : List[Tuple[float, float]] = []
        # PILAR 1: estado dos ratos por episodio
        ratos            : List[Rato] = []    # Ratos ativos no mapa
        acumulador_ratos  = [0]               # [0] = mutavel para closures
                                              # Conta hits acumulados -> extras no proximo cast
                                              # RESETA a cada episodio (conforme especificado)

        agora        = 0;  dt = 16
        vida_a_ant   = apolo.vida;  vida_u_ant = umbra.vida
        ultima_esfera = 0
        vencedor     = "TIMEOUT"
        t_ep_ini     = time.perf_counter()
        estrategia   = random.choice(estrategias)

        for frame in range(MAX_FRAMES_EP):
            agora += dt

            # Historico do Apolo (para Umbra calcular velocidade)
            hist_apolo.append((apolo.fx, apolo.fy))
            if len(hist_apolo) > 60:
                hist_apolo.pop(0)

            # Registra tendencias Bayesianas
            if len(hist_apolo) >= 2:
                dvx = hist_apolo[-1][0] - hist_apolo[-2][0]
                dvy = hist_apolo[-1][1] - hist_apolo[-2][1]
                if abs(dvx) > 0.5 or abs(dvy) > 0.5:
                    if dvx > 1:    tendencias["DIREITA"]  += 1
                    elif dvx < -1: tendencias["ESQUERDA"] += 1
                    if dvy > 1:    tendencias["BAIXO"]    += 1
                    elif dvy < -1: tendencias["CIMA"]     += 1
                    tendencias["TOTAL"] += 1

            # ── Estado atual (listas de floats) ───────────────────────────
            s_a = obter_estado_apolo_cpu(apolo, umbra, projeteis, esferas,
                                          estado_ia, ratos)  # PILAR 1: passa ratos
            s_u = obter_estado_umbra_cpu(umbra, apolo, projeteis, estado_ia,
                                          hist_apolo, tendencias)

            # ── Apolo: decidir acao ───────────────────────────────────────
            MARG = 80
            ac_v = list(range(APOLO_OUTPUT_SIZE))
            if apolo.fy < MARG and 0 in ac_v:                    ac_v.remove(0)
            if apolo.fy > ALTURA_MAPA  - MARG and 1 in ac_v:    ac_v.remove(1)
            if apolo.fx < MARG and 2 in ac_v:                    ac_v.remove(2)
            if apolo.fx > LARGURA_MAPA - MARG and 3 in ac_v:    ac_v.remove(3)
            if not ac_v: ac_v = [4]

            acao_a = pol_apolo.decidir(s_a, ac_v)
            apolo.mover(acao_a, agora)
            proj = apolo.disparar(umbra.fx + LARGURA_BOSS/2,
                                   umbra.fy + ALTURA_BOSS/2, agora)
            if proj: projeteis.append(proj)

            # ── Umbra: decidir acao ───────────────────────────────────────
            acao_u_str = pol_umbra.decidir_umbra(s_u, _acoes_umbra_disponiveis(agora, cd_umbra))
            acao_u_idx = UMBRA_ACOES.index(acao_u_str) if acao_u_str in UMBRA_ACOES else 0

            # PILAR 1: Trata o cast de Praga dos Ratos separadamente
            if acao_u_str == "PRAGA_RATOS":
                # Spawn: 4 base + acumulador de hits anteriores
                novos = spawnar_ratos(agora, acumulador_ratos[0])
                ratos.extend(novos)
                cd_umbra["ratos"] = agora
                # Nao precisa chamar executar_acao_umbra para esta acao
            else:
                executar_acao_umbra(agora, acao_u_str, umbra, apolo,
                                     estado_ia, cd_umbra, projeteis, hist_apolo)

            # Movimento da Umbra
            if frame % 60 == 0:
                estrategia = random.choice(estrategias)
            alvo = _calcular_alvo_umbra(apolo, umbra, estrategia)
            umbra.mover_para(alvo[0], alvo[1])

            # ── Fisica ────────────────────────────────────────────────────
            res      = processar_colisoes(projeteis, apolo, umbra)
            coletou  = processar_esferas(esferas, apolo)
            dano_arm = atualizar_armadilhas(agora, estado_ia, apolo)
            if dano_arm > 0: apolo.vida -= dano_arm

            # PILAR 1: Processa ratos (movimento + colisao + expiracao)
            res_ratos = processar_ratos(agora, ratos, apolo, umbra, acumulador_ratos)

            if agora - ultima_esfera >= INTERVALO_ESFERA:
                ex = max(50.0, min(LARGURA_MAPA-50.0, umbra.fx + LARGURA_BOSS/2 + random.uniform(-200,200)))
                ey = max(50.0, min(ALTURA_MAPA -50.0, umbra.fy + ALTURA_BOSS /2 + random.uniform(-200,200)))
                esferas.append(EsferaEnergia(ex, ey))
                ultima_esfera = agora

            # ── Condicao de fim ───────────────────────────────────────────
            morreu_a = apolo.vida <= 0
            morreu_u = umbra.vida <= 0
            done     = morreu_a or morreu_u

            # ── Recompensas (PILAR 1: inclui hits e expiracoes dos ratos) ──
            r_a = calcular_reward_apolo(
                apolo, umbra, projeteis, esferas, estado_ia,
                vida_a_ant, vida_u_ant, coletou,
                venceu=morreu_u, morreu=morreu_a,
                hits_ratos=res_ratos['hits'],
                expirados_ratos=res_ratos['expirados']
            )
            r_u = calcular_reward_umbra(
                acertou=res["acertou_apolo"], acao=acao_u_str,
                venceu=morreu_a, perdeu=morreu_u,
                hits_ratos=res_ratos['hits']
            )

            # ── Proximo estado (PILAR 1: passa ratos para s_a_next) ────────
            s_a_next = obter_estado_apolo_cpu(apolo, umbra, projeteis, esferas,
                                               estado_ia, ratos)
            s_u_next = obter_estado_umbra_cpu(umbra, apolo, projeteis, estado_ia,
                                               hist_apolo, tendencias)

            # ── Acumula experiencias (como tuplas Python - serializaveis) ──
            lote_exp_apolo.append((s_a, acao_a,     r_a, s_a_next, float(done)))
            lote_exp_umbra.append((s_u, acao_u_idx, r_u, s_u_next, float(done)))

            # ── Envia lote quando atingir o tamanho configurado ───────────
            # Enviamos como (tipo, lista_de_experiencias) para o processo principal
            # diferenciar experiencias de Apolo e Umbra.
            if len(lote_exp_apolo) >= EXPERIENCIAS_POR_ENVIO:
                try:
                    # block=False: descarta se a fila estiver cheia
                    # (evita que worker trave se GPU estiver lenta)
                    exp_queue.put_nowait(('apolo', list(lote_exp_apolo)))
                    exp_queue.put_nowait(('umbra', list(lote_exp_umbra)))
                except Exception:
                    pass  # Fila cheia: descarta este lote para nao bloquear
                lote_exp_apolo.clear()
                lote_exp_umbra.clear()

            vida_a_ant = apolo.vida;  vida_u_ant = umbra.vida

            if morreu_a: vencedor = "Umbra"; break
            if morreu_u: vencedor = "Apolo"; break

        # ── Envia estatisticas do episodio ao processo principal ──────────
        dur = time.perf_counter() - t_ep_ini
        fps = (frame + 1) / max(dur, 1e-9)
        try:
            stats_queue.put_nowait({
                'worker_id': worker_id,
                'vencedor' : vencedor,
                'frames'   : frame + 1,
                'fps'      : fps,
            })
        except Exception:
            pass  # Stats nao sao criticos

    # Cleanup ao terminar
    pygame.quit()


# ==============================================================================
# SECAO 9: TREINADOR GPU (roda no processo principal)
#
# Gerencia:
#   - Redes neurais globais na GPU
#   - Replay Buffer global
#   - Loop de optimizer.step()
#   - Transmissao de pesos para workers
#   - Logs e checkpoints
# ==============================================================================

class TreinadorGPU:
    """
    Gerencia o treinamento das redes neurais na GPU.
    Hospeda as Policy Nets e as Target Nets.
    Le experiencias da exp_queue e treina em batches.
    """
    def __init__(self, device: torch.device):
        self.device = device

        # ── Redes Apolo (GPU) ──────────────────────────────────────────────
        self.q_apolo      = DQNNet(APOLO_INPUT_SIZE, APOLO_OUTPUT_SIZE).to(device)
        self.target_apolo = DQNNet(APOLO_INPUT_SIZE, APOLO_OUTPUT_SIZE).to(device)
        self.target_apolo.load_state_dict(self.q_apolo.state_dict())
        self.target_apolo.eval()
        self.opt_apolo    = optim.Adam(self.q_apolo.parameters(), lr=LR_APOLO)

        # ── Redes Umbra (GPU) ──────────────────────────────────────────────
        self.q_umbra      = DQNNet(UMBRA_INPUT_SIZE, UMBRA_OUTPUT_SIZE).to(device)
        self.target_umbra = DQNNet(UMBRA_INPUT_SIZE, UMBRA_OUTPUT_SIZE).to(device)
        self.target_umbra.load_state_dict(self.q_umbra.state_dict())
        self.target_umbra.eval()
        self.opt_umbra    = optim.Adam(self.q_umbra.parameters(), lr=LR_UMBRA)

        # ── Replay Buffers (RAM) ───────────────────────────────────────────
        self.buf_apolo = ReplayBuffer(BUFFER_SIZE)
        self.buf_umbra = ReplayBuffer(BUFFER_SIZE)

        # ── Contadores ────────────────────────────────────────────────────
        self.steps_apolo = 0
        self.steps_umbra = 0
        self.loss_a_acum = 0.0;  self.loss_a_cnt = 0
        self.loss_u_acum = 0.0;  self.loss_u_cnt = 0

        # ── Carrega pesos existentes ───────────────────────────────────────
        self._carregar()

    def _carregar(self):
        for nome, net, target in [
            (ARQUIVO_APOLO, self.q_apolo, self.target_apolo),
            (ARQUIVO_UMBRA, self.q_umbra, self.target_umbra),
        ]:
            if os.path.exists(nome):
                try:
                    net.load_state_dict(torch.load(nome, map_location=self.device,
                                                   weights_only=True))
                    target.load_state_dict(net.state_dict())
                    print(f"  [GPU] Pesos carregados: '{nome}'")
                except Exception as e:
                    print(f"  [GPU] Aviso ao carregar '{nome}': {e}")

    def salvar(self):
        torch.save(self.q_apolo.state_dict(), ARQUIVO_APOLO)
        torch.save(self.q_umbra.state_dict(), ARQUIVO_UMBRA)
        print(f"  [GPU] Checkpoint salvo. Steps: A={self.steps_apolo} U={self.steps_umbra}")

    def _treinar_rede(self, q_net: nn.Module, target: nn.Module,
                      optimizer: optim.Optimizer, buffer: ReplayBuffer,
                      output_size: int) -> float:
        """
        Um passo de gradiente DQN na GPU.
        Fluxo: sample -> GPU -> loss -> backward -> clip -> step
        """
        if len(buffer) < BATCH_SIZE:
            return 0.0

        # Amostra e converte diretamente para tensors GPU
        s, a, r, sn, done = buffer.amostrar(BATCH_SIZE, self.device)

        q_net.train()
        # Q-values para acoes tomadas
        q_atual = q_net(s).gather(1, a.unsqueeze(1)).squeeze(1)

        # Q-values alvo (target network - sem grad)
        with torch.no_grad():
            q_prox = target(sn).max(1)[0]
            q_alvo = r + GAMMA * q_prox * (1.0 - done)

        loss = F.smooth_l1_loss(q_atual, q_alvo)
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(q_net.parameters(), max_norm=10.0)
        optimizer.step()
        return loss.item()

    def processar_experiencias(self, exp_queue: mp.Queue):
        """
        Drena a fila de experiencias e adiciona ao buffer.
        Chamado continuamente no loop principal.
        Retorna quantas experiencias foram processadas nesta chamada.
        """
        count = 0
        # Drena ate 20 lotes por chamada para nao monopolizar o loop
        for _ in range(20):
            try:
                tipo, lote = exp_queue.get_nowait()
                if tipo == 'apolo':
                    self.buf_apolo.adicionar_lote(lote)
                elif tipo == 'umbra':
                    self.buf_umbra.adicionar_lote(lote)
                count += len(lote)
            except Exception:
                break
        return count

    def treinar_step(self) -> Tuple[float, float]:
        """
        Executa um passo de treinamento para cada rede.
        Atualiza target networks quando necessario.
        Retorna (loss_apolo, loss_umbra).
        """
        la = self._treinar_rede(self.q_apolo, self.target_apolo,
                                 self.opt_apolo,  self.buf_apolo, APOLO_OUTPUT_SIZE)
        lu = self._treinar_rede(self.q_umbra, self.target_umbra,
                                 self.opt_umbra,  self.buf_umbra, UMBRA_OUTPUT_SIZE)

        if la > 0:
            self.steps_apolo += 1
            self.loss_a_acum += la;  self.loss_a_cnt += 1
        if lu > 0:
            self.steps_umbra += 1
            self.loss_u_acum += lu;  self.loss_u_cnt += 1

        # Atualiza target networks
        steps = max(self.steps_apolo, self.steps_umbra)
        if steps > 0 and steps % TARGET_UPDATE_FREQ == 0:
            self.target_apolo.load_state_dict(self.q_apolo.state_dict())
            self.target_umbra.load_state_dict(self.q_umbra.state_dict())

        return la, lu

    def obter_pesos_cpu(self, eps_a: float, eps_u: float) -> dict:
        """
        Extrai pesos das redes GPU, move para CPU e empacota para envio.
        Esta operacao e relativamente barata para redes pequenas (128->64).
        """
        return {
            'apolo'        : {k: v.cpu() for k, v in self.q_apolo.state_dict().items()},
            'umbra'        : {k: v.cpu() for k, v in self.q_umbra.state_dict().items()},
            'epsilon_apolo': eps_a,
            'epsilon_umbra': eps_u,
        }

    def loss_media(self) -> Tuple[float, float]:
        la = self.loss_a_acum / max(1, self.loss_a_cnt)
        lu = self.loss_u_acum / max(1, self.loss_u_cnt)
        self.loss_a_acum = self.loss_u_acum = 0.0
        self.loss_a_cnt  = self.loss_u_cnt  = 0
        return la, lu


# ==============================================================================
# SECAO 10: PROCESSO PRINCIPAL (main)
# ==============================================================================

def main():
    # ── Verificacao de CUDA ────────────────────────────────────────────────────
    if not torch.cuda.is_available():
        print("[AVISO] CUDA nao encontrado. Usando CPU como fallback.")
        print("        Para GPU, instale: pip install torch --index-url https://download.pytorch.org/whl/cu121")
        device = torch.device("cpu")
    else:
        device = torch.device("cuda")
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb  = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"[GPU] Dispositivo: {gpu_name}  |  VRAM: {vram_gb:.1f} GB")

    print("=" * 72)
    print("  TREINO PARALELO GPU - RUPTURA TEMPORAL")
    print(f"  Workers CPU: {NUM_WORKERS}  |  Device: {device}")
    print(f"  Batch: {BATCH_SIZE}  |  Buffer: {BUFFER_SIZE:,}")
    print(f"  Epsilon: {EPSILON_INICIO:.2f} -> {EPSILON_FIM:.2f}  |  Decay: {EPSILON_DECAIMENTO}")
    print(f"  Apolo: {APOLO_INPUT_SIZE}in/{APOLO_OUTPUT_SIZE}out  |  Umbra: {UMBRA_INPUT_SIZE}in/{UMBRA_OUTPUT_SIZE}out")
    print("=" * 72)

    # Necessario para CUDA + multiprocessing no Windows e macOS
    # No Linux com 'fork' isso nao seria necessario, mas 'spawn' e mais seguro.
    mp.set_start_method('spawn', force=True)

    # ── Filas de comunicacao IPC ──────────────────────────────────────────────
    #
    # exp_queue   : Workers -> Principal
    #               Transporta tuplas (tipo, lote_de_experiencias)
    #               maxsize previne RAM overflow se GPU estiver lenta
    #
    # weight_queues: Principal -> Worker_i
    #               Uma fila POR worker (nao broadcast, mas envio direto)
    #               Transporta dicts com state_dicts + epsilon
    #
    # stats_queue : Workers -> Principal
    #               Transporta dicts com metricas de cada episodio
    #
    exp_queue    = mp.Queue(maxsize=QUEUE_MAX_SIZE)
    stats_queue  = mp.Queue(maxsize=10_000)
    stop_event   = mp.Event()

    # Uma weight_queue por worker (permite controle individual)
    weight_queues = [mp.Queue(maxsize=5) for _ in range(NUM_WORKERS)]

    # ── Inicia os workers ─────────────────────────────────────────────────────
    treinador    = TreinadorGPU(device)
    eps_a        = EPSILON_INICIO
    eps_u        = EPSILON_INICIO

    # ── PILAR 3: Epsilon por Worker (Diversidade de Exploracao) ───────────────
    #
    # Estrategia: distribuicao linear de epsilons iniciais por ID do worker.
    # Worker 0 (mais conservador):  epsilon = EPSILON_FIM         (quase greedy)
    # Worker 7 (mais exploratorio): epsilon = EPSILON_INICIO      (totalmente aleatorio)
    #
    # Isso garante que o Replay Buffer global receba uma MIX de:
    #   - Transicoes de alta qualidade (workers conservadores, epsilon baixo)
    #   - Transicoes de exploracao (workers exploratorios, epsilon alto)
    # resultado: buffer mais rico e diverso, melhor cobertura do espaco de estados.
    #
    # Formula: eps_worker_i = EPSILON_FIM + (wid / max(1, N-1)) * (EPSILON_INICIO - EPSILON_FIM)
    # Exemplo com 8 workers:
    #   W0: 0.05, W1: 0.19, W2: 0.33, W3: 0.48,
    #   W4: 0.62, W5: 0.76, W6: 0.91, W7: 1.00
    def epsilon_para_worker(wid: int, n_workers: int) -> float:
        if n_workers <= 1:
            return EPSILON_INICIO
        frac = wid / (n_workers - 1)   # 0.0 .. 1.0
        return round(EPSILON_FIM + frac * (EPSILON_INICIO - EPSILON_FIM), 4)

    print("  [MAIN] Epsilons por worker (PILAR 3 - Diversidade):")
    for wid in range(NUM_WORKERS):
        ew = epsilon_para_worker(wid, NUM_WORKERS)
        print(f"         Worker-{wid}: eps={ew:.2f}")

    workers = []
    for wid in range(NUM_WORKERS):
        # Epsilon individualizado para cada worker
        eps_w = epsilon_para_worker(wid, NUM_WORKERS)

        # Pre-popula a weight_queue com pesos + epsilon especifico do worker
        pesos_worker = treinador.obter_pesos_cpu(eps_w, eps_w)
        weight_queues[wid].put(pesos_worker)

        p = mp.Process(
            target=worker_fn,
            args=(wid, exp_queue, weight_queues[wid], stats_queue, stop_event),
            daemon=True,
            name=f"Worker-{wid}"
        )
        p.start()
        workers.append(p)
        print(f"  [MAIN] Worker-{wid} iniciado (PID {p.pid}, eps={eps_w:.2f})")

    print(f"\n  [MAIN] {NUM_WORKERS} workers ativos. Aguardando experiencias...\n")

    # ── Variaveis de controle do loop principal ───────────────────────────────
    steps_global     = 0
    eps_totais       = 0
    vitorias_apolo   = 0
    vitorias_umbra   = 0

    fps_total_acum   = 0.0
    fps_count        = 0
    t_inicio         = time.time()
    t_ultimo_log     = t_inicio
    t_ultimo_save    = t_inicio

    # Aguarda o buffer ter experiencias suficientes antes de comecar a treinar
    print("  [MAIN] Aquecendo buffer...")
    while len(treinador.buf_apolo) < BATCH_SIZE:
        treinador.processar_experiencias(exp_queue)
        time.sleep(0.05)
    print(f"  [MAIN] Buffer aquecido com {len(treinador.buf_apolo)} experiencias.")

    # ── Loop principal de treinamento ─────────────────────────────────────────
    try:
        while True:
            # 1. Drena experiencias vindas dos workers para os buffers
            treinador.processar_experiencias(exp_queue)

            # 2. Executa um passo de treinamento na GPU
            treinador.treinar_step()
            steps_global += 1

            # 3. Eta do epsilon (decaimento global)
            eps_a = max(EPSILON_FIM, eps_a * EPSILON_DECAIMENTO)
            eps_u = max(EPSILON_FIM, eps_u * EPSILON_DECAIMENTO)

            # 4. Sincroniza pesos com workers periodicamente
            #    PILAR 3: cada worker recebe seu proprio epsilon (nao global)
            if steps_global % WEIGHT_SYNC_FREQ == 0:
                for wid in range(NUM_WORKERS):
                    # Recalcula epsilon do worker: mantem a proporcao relativa
                    # mas com o piso global eps_a como referencia do worker mais
                    # greedy (wid=0). Assim todos decaem juntos mas mantem o spread.
                    eps_w = epsilon_para_worker(wid, NUM_WORKERS)
                    # Escala o epsilon do worker proporcionalmente ao epsilon global:
                    # Se eps_a global caiu para 0.3, worker-0 fica em ~0.05 (floor)
                    # e worker-7 fica em ~0.3 (igual ao global).
                    escala = eps_a / max(EPSILON_INICIO, 1e-6)
                    eps_w_atual = max(EPSILON_FIM, eps_w * escala + EPSILON_FIM * (1.0 - escala))
                    pesos_w = treinador.obter_pesos_cpu(eps_w_atual, eps_w_atual)
                    try:
                        try:
                            weight_queues[wid].get_nowait()   # Descarta pesos antigos
                        except Exception:
                            pass
                        weight_queues[wid].put_nowait(pesos_w)
                    except Exception:
                        pass

            # 5. Coleta estatisticas dos workers
            stats_recebidas = 0
            try:
                for _ in range(100):   # Processa ate 100 stats por ciclo
                    s = stats_queue.get_nowait()
                    eps_totais += 1
                    stats_recebidas += 1
                    if s['vencedor'] == 'Apolo': vitorias_apolo += 1
                    elif s['vencedor'] == 'Umbra': vitorias_umbra += 1
                    fps_total_acum += s['fps']
                    fps_count      += 1
            except Exception:
                pass

            # 6. Checkpoint
            if steps_global % SAVE_INTERVALO == 0:
                treinador.salvar()

            # 7. Log periodico
            if steps_global % LOG_INTERVALO == 0 and fps_count > 0:
                la_m, lu_m = treinador.loss_media()
                fps_media  = fps_total_acum / fps_count
                total_vit  = vitorias_apolo + vitorias_umbra
                wr_apolo   = vitorias_apolo / max(1, total_vit) * 100.0
                buf_a_pct  = len(treinador.buf_apolo) / BUFFER_SIZE * 100
                buf_u_pct  = len(treinador.buf_umbra) / BUFFER_SIZE * 100
                elapsed_m  = (time.time() - t_inicio) / 60.0

                print(
                    f"Step {steps_global:>8,} "
                    f"| Eps: {eps_totais:>7,} "
                    f"| WinA: {wr_apolo:5.1f}% "
                    f"| eA: {eps_a:.3f} eU: {eps_u:.3f} "
                    f"| LossA: {la_m:.4f} LossU: {lu_m:.4f} "
                    f"| FPS: {fps_media*NUM_WORKERS:,.0f} "
                    f"| Buf: {buf_a_pct:.0f}%/{buf_u_pct:.0f}% "
                    f"| {elapsed_m:.1f}min"
                )
                fps_total_acum = 0.0;  fps_count = 0

    except KeyboardInterrupt:
        print("\n[MAIN] Interrupcao recebida. Finalizando workers...")

    finally:
        # ── Shutdown gracioso ─────────────────────────────────────────────────
        stop_event.set()

        # Envia sinal None para desbloquear workers que estao esperando pesos
        for wid in range(NUM_WORKERS):
            try:
                weight_queues[wid].put_nowait(None)
            except Exception:
                pass

        # Aguarda todos os workers terminarem (timeout de 5s cada)
        for p in workers:
            p.join(timeout=5)
            if p.is_alive():
                p.terminate()

        # Salvamento final
        treinador.salvar()

        total_vit = vitorias_apolo + vitorias_umbra
        total_min = (time.time() - t_inicio) / 60.0
        print("\n" + "=" * 72)
        print("  TREINO PARALELO CONCLUIDO!")
        print(f"  Tempo total      : {total_min:.1f} min")
        print(f"  Steps GPU totais : {steps_global:,}")
        print(f"  Episodios totais : {eps_totais:,}")
        print(f"  Vitorias Apolo   : {vitorias_apolo:,} ({vitorias_apolo/max(1,total_vit)*100:.1f}%)")
        print(f"  Vitorias Umbra   : {vitorias_umbra:,}")
        print(f"  Pesos salvos     : '{ARQUIVO_APOLO}' e '{ARQUIVO_UMBRA}'")
        print("=" * 72)


# ==============================================================================
# ENTRY POINT
# Obrigatorio: `if __name__ == '__main__':` para multiprocessing.spawn no Windows.
# Sem isso, cada processo filho ao importar este modulo tentaria iniciar
# novos workers, causando fork-bomb.
# ==============================================================================
if __name__ == '__main__':
    main()
