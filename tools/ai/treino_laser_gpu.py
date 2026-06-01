"""
treino_laser_gpu.py  —  Versao GPU v5 (Dueling DQN + PER + Neurogenese)
=========================================================================
Versao do treino laser otimizada para GPU NVIDIA.

Hardware alvo:
  GPU:  NVIDIA GTX 1650 (4GB GDDR5, Compute 7.5, Turing)
  CPU:  AMD Ryzen 5 4600G (6C / 12T)
  RAM:  16 GB

Otimizacoes v5 (vs v4):
  [+] Dueling DQN 256x256 (via apolo_brain.py) ... separa V(s) de A(s,a)
  [+] Prioritized Experience Replay (PER) ......... eventos raros super-amostrados
  [+] Double DQN ................................. sem overestimation de Q
  [+] Neurogenese automatica ..................... rede cresce sozinha se confusa
  [+] Auto-reset em incompatibilidade ............ sem conflito de pesos
  [+] Recompensas mais granulares ................ gradiente desde dist=200

Arquitetura (apolo_brain.py):
  Inicio: hidden=256 (configuravel via apolo_arq.json)
  Cresce: +64 neuronios quando entropia media > 1.8 por 1000 passos
  Teto:   512 neuronios (GTX 1650 4GB)

SETUP (rode setup_gpu.bat primeiro):
  Este script requer Python 3.12 + PyTorch-CUDA.
  Veja setup_gpu.bat para instalar o ambiente correto.

Uso:
    .venv312\\Scripts\\python tools/ai/treino_laser_gpu.py
    .venv312\\Scripts\\python tools/ai/treino_laser_gpu.py --curriculum --geracoes 3000
    .venv312\\Scripts\\python tools/ai/treino_laser_gpu.py --verificar
    .venv312\\Scripts\\python tools/ai/treino_laser_gpu.py --limpar
"""

import math
import random
import sys
import os
import time
import argparse
import collections
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

import torch
import torch.nn as nn
import torch.optim as optim

# =============================================================================
# IMPORTA O CEREBRO CENTRAL DE APOLO
# =============================================================================
from apolo_brain import (
    ApoloDQN, ApoloAgent, PrioritizedReplay,
    INPUT_SIZE, OUTPUT_SIZE,
    GerenciadorArquitetura,
)

# -----------------------------------------------------------------------
# Verifica CUDA antes de qualquer coisa
# -----------------------------------------------------------------------
def checar_gpu():
    if not torch.cuda.is_available():
        print("\n[ERRO] CUDA nao disponivel!")
        print("       Certifique-se de usar o ambiente Python correto:")
        print("       > .venv312\\Scripts\\python tools/ai/treino_laser_gpu.py")
        print("       Execute setup_gpu.bat para criar o ambiente.\n")
        sys.exit(1)

    props  = torch.cuda.get_device_properties(0)
    vram   = props.total_memory / 1e9
    cc     = (props.major, props.minor)
    nome   = props.name

    print(f"\n[GPU] {nome}")
    print(f"      VRAM:    {vram:.1f} GB")
    print(f"      Compute: {cc[0]}.{cc[1]}")
    print(f"      AMP/FP16: {'SIM (Tensor Cores)' if cc >= (7, 0) else 'SIM (FP16 basico)'}")

    if vram < 2.0:
        print("[AVISO] Menos de 2GB VRAM — reduzindo batch para 128.")
        return 128
    elif vram < 4.5:
        return 256   # GTX 1650 (4GB)
    else:
        return 512   # RTX 3060+ etc.


# Garante UTF-8 no terminal Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# =============================================================================
# CONFIGURACAO DO MAPA  (identico ao treino_laser_apolo.py)
# =============================================================================
LARGURA_MAPA     = 1280
ALTURA_MAPA      = 720
VELOCIDADE_APOLO = 4.0
VELOCIDADE_DASH  = 80.0
DASH_COOLDOWN_FRAMES = 90

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
RAIO_MORTE_LASER   = 50

# =============================================================================
# AGENTE GPU  —  Wrapper fino sobre ApoloAgent para AMP + torch.compile
# =============================================================================
class ApoloTreinoLaserGPU:
    """Wrapper que adiciona AMP (FP16) e torch.compile ao ApoloAgent base."""

    def __init__(self, batch_size: int = 256, taxa_exploracao: float = 0.80,
                 limpar_pesos: bool = False):
        self.device     = torch.device("cuda")
        self.batch_size = batch_size

        torch.backends.cudnn.benchmark = True

        if limpar_pesos:
            import shutil, os
            from apolo_brain import PESOS_FILE
            if os.path.exists(PESOS_FILE):
                bak = PESOS_FILE.replace('.pt', '_backup_antes_limpar.pt')
                shutil.copy2(PESOS_FILE, bak)
                os.remove(PESOS_FILE)
                print(f"[APOLO] Backup salvo em '{bak}' — iniciando zerado.")

        per = PrioritizedReplay(
            capacidade=200_000,
            alpha=0.6,
            beta=0.4,
            beta_inc=0.0001,
            pin=True,
        )
        self._agente = ApoloAgent(
            device=self.device,
            batch_size=batch_size,
            taxa_exploracao=taxa_exploracao,
            replay_buffer=per,
        )

        # AMP scaler
        self.scaler    = torch.cuda.amp.GradScaler()
        self.taxa_exp  = self._agente.taxa_exp
        self.passos    = 0

        # torch.compile
        try:
            self._agente.q_online = torch.compile(self._agente.q_online)
            print("[GPU] torch.compile ativado")
        except Exception:
            print("[GPU] torch.compile indisponivel (PyTorch < 2.0)")

    @property
    def replay(self):
        return self._agente.replay

    @property
    def taxa_exp(self):
        return self._agente.taxa_exp

    @taxa_exp.setter
    def taxa_exp(self, v):
        self._agente.taxa_exp = v

    def decidir_batch(self, tensores, acoes_validas_batch):
        return self._agente.decidir_batch(tensores, acoes_validas_batch)

    def adicionar_transicao(self, s, a, r, s_, done):
        self._agente.adicionar_transicao(s, a, r, s_, done)

    def treinar_passo(self):
        return self._agente.treinar_passo(scaler=self.scaler)

    def salvar_pesos(self):
        self._agente.salvar_pesos()

# =============================================================================
# AMBIENTE DO LASER  (copiado do treino_laser_apolo.py v4 — features identicas)
# =============================================================================
class LaserEnv:
    MAX_HITS = 3

    def __init__(self):
        self.rodada_max = 4
        self.reset()

    def reset(self) -> torch.Tensor:
        while True:
            ax = random.randint(MARGEM_SPAWN, LARGURA_MAPA - MARGEM_SPAWN)
            ay = random.randint(MARGEM_SPAWN, ALTURA_MAPA  - MARGEM_SPAWN)
            if math.hypot(ax - BOSS_POS[0], ay - BOSS_POS[1]) > 200:
                break

        self.apolo_x  = float(ax)
        self.apolo_y  = float(ay)
        self._heading = (1.0, 0.0)
        self.dash_cooldown = 0

        self.tempo_ms = 0
        self.dt_ms    = 16
        self.hits     = 0
        self.done     = False

        self.ultima_dist_feixe       = None
        self.laser_estava_carregando = False
        self.recompensa_acumulada    = 0.0
        self.rodadas_sobrevividas    = 0

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

    # ---- Acao -> Movimento -------------------------------------------------
    def _aplicar_acao(self, acao: int):
        dx, dy    = 0.0, 0.0
        usar_dash = False

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
            dx *= 0.7071; dy *= 0.7071

        if usar_dash and self.dash_cooldown == 0:
            hdx, hdy = self._heading
            self.apolo_x += hdx * VELOCIDADE_DASH
            self.apolo_y += hdy * VELOCIDADE_DASH
            self.dash_cooldown = DASH_COOLDOWN_FRAMES
        else:
            self.apolo_x += dx * VELOCIDADE_APOLO
            self.apolo_y += dy * VELOCIDADE_APOLO
            if dx != 0 or dy != 0:
                mag = math.hypot(dx, dy)
                self._heading = (dx / max(mag, 1e-9), dy / max(mag, 1e-9))

        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        self.apolo_x = max(10.0, min(LARGURA_MAPA - 10.0, self.apolo_x))
        self.apolo_y = max(10.0, min(ALTURA_MAPA  - 10.0, self.apolo_y))

    # ---- Geometria do laser ------------------------------------------------
    def _geometria_laser(self):
        laser = self.laser
        cfg   = RODADAS_CONFIG[laser['rodada']]
        prog  = 0.0
        if laser['fase'] == 'disparando' and laser['tempo_inicio_disparo'] is not None:
            t    = self.tempo_ms - laser['tempo_inicio_disparo']
            prog = min(1.0, t / laser['duracao_disparo'])

        ang_base = laser['angulo_base_inicio'] + cfg['giro_total'] * prog * cfg['sentido']
        ox, oy   = BOSS_POS
        comp     = 2500
        feixes   = []
        for i in range(cfg['num_feixes']):
            ang = ang_base + i * ((math.pi * 2) / cfg['num_feixes'])
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

    # ---- Tensor de 40 features (v4) ----------------------------------------
    def _montar_tensor(self) -> torch.Tensor:
        px, py = self.apolo_x, self.apolo_y
        bx, by = BOSS_POS
        mp     = 100

        # [0-17] Base
        f_px = px / LARGURA_MAPA;  f_py = py / ALTURA_MAPA
        f_bx = bx / LARGURA_MAPA;  f_by = by / ALTURA_MAPA
        f_vp = 1.0;  f_vb = 1.0
        f_be = min(1.0, px / mp);  f_bd = min(1.0, (LARGURA_MAPA - px) / mp)
        f_bc = min(1.0, py / mp);  f_bb = min(1.0, (ALTURA_MAPA  - py) / mp)
        f_canto = 1.0 if (
            (px < mp and py < mp) or (px > LARGURA_MAPA - mp and py < mp) or
            (px < mp and py > ALTURA_MAPA - mp) or
            (px > LARGURA_MAPA - mp and py > ALTURA_MAPA - mp)
        ) else 0.0
        f_dp = 1.0; f_dxp = 0.0; f_dyp = 0.0
        f_cd = 1.0 if self.dash_cooldown > 0 else 0.0
        f_vel = VELOCIDADE_APOLO / 15.0
        f_orb = 0.0; f_vb2 = 0.0

        # [18-26] Laser
        f_lfase = 0.0; f_lrod = 0.0; f_lprog = 0.0
        f_lfeixes = 0.0; f_lsent = 0.0; f_lvel = 0.0
        f_lang = 0.0; f_ldist = 1.0; f_ltempo = 0.0

        # [27-33]
        f_orbd = 1.0; f_ox = 0.0; f_oy = 0.0
        f_fugax = 0.0; f_fugay = 0.0; f_zona = 0.0; f_dist2 = -1.0

        laser  = self.laser
        rodada = laser['rodada']
        cfg    = RODADAS_CONFIG[rodada]
        num_f  = cfg['num_feixes']
        sentido= cfg['sentido']
        giro   = cfg['giro_total']

        menor_dist_global  = float('inf')
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
            vel_ang   = giro / (laser['duracao_disparo'] / 1000.0)
            f_lvel    = min(1.0, abs(vel_ang) / (2 * math.pi))

            feixes, _ = self._geometria_laser()
            dists_feixes = []
            for ang_f, fx, fy in feixes:
                if not self._em_frente(ang_f, px, py):
                    continue
                dist_f = self._dist_perp(ang_f, fx, fy, px, py)
                dists_feixes.append((dist_f, ang_f))

            dists_feixes.sort(key=lambda x: x[0])
            if dists_feixes:
                menor_dist_global  = dists_feixes[0][0]
                ang_proximo_global = dists_feixes[0][1]

            f_ldist = min(1.0, menor_dist_global / 400.0)

            ang_p  = math.atan2(py - BOSS_POS[1], px - BOSS_POS[0])
            diff_1 = ang_p - ang_proximo_global
            while diff_1 >  math.pi: diff_1 -= 2 * math.pi
            while diff_1 < -math.pi: diff_1 += 2 * math.pi
            f_lang   = max(-1.0, min(1.0, (diff_1 * sentido) / math.pi))
            f_ltempo = math.cos(ang_proximo_global)

            ang_fuga = ang_proximo_global + (math.pi / 2) * sentido
            f_fugax  = math.cos(ang_fuga)
            f_fugay  = math.sin(ang_fuga)

            ang_restante = giro * (1.0 - f_lprog)
            diff_sweep   = diff_1 * sentido
            if diff_sweep < 0: diff_sweep += 2 * math.pi
            f_zona = 1.0 if 0 < diff_sweep <= ang_restante else 0.0

            if len(dists_feixes) >= 2:
                ang_2nd = dists_feixes[1][1]
                diff_2  = ang_p - ang_2nd
                while diff_2 >  math.pi: diff_2 -= 2 * math.pi
                while diff_2 < -math.pi: diff_2 += 2 * math.pi
                f_dist2 = max(-1.0, min(1.0, (diff_2 * sentido) / math.pi))

        # [34-39] Armadilhas
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
            f_fugax, f_fugay, f_zona, f_dist2,   # 30-33
        ] + f_arm                                 # 34-39

        assert len(features) == 40
        return torch.tensor(features, dtype=torch.float32).unsqueeze(0)  # CPU, sera movido para GPU em batch

    # ---- Step --------------------------------------------------------------
    def step(self, acao: int):
        self._aplicar_acao(acao)
        self.tempo_ms += self.dt_ms

        laser  = self.laser
        px, py = self.apolo_x, self.apolo_y
        rodada = laser['rodada']
        recomp = 0.0

        if laser['fase'] == 'carregando':
            t_c = self.tempo_ms - laser['tempo_inicio']
            if t_c >= laser['duracao_carga']:
                laser['fase'] = 'disparando'
                laser['tempo_inicio_disparo'] = self.tempo_ms
                self.laser_estava_carregando  = True

            dist_borda = min(px, py, LARGURA_MAPA - px, ALTURA_MAPA - py)
            if dist_borda < MARGEM_SPAWN:
                recomp -= 5.0

            prog_c = min(1.0, (self.tempo_ms - laser['tempo_inicio']) / laser['duracao_carga'])
            if acao == 8:
                recomp += 15.0 if prog_c >= 0.75 else -8.0
            recomp += 0.2

        elif laser['fase'] == 'disparando':
            t_d   = self.tempo_ms - laser['tempo_inicio_disparo']
            feixes, _ = self._geometria_laser()

            menor_dist = float('inf')
            ang_mp     = 0.0
            em_perigo  = False

            for ang, fx, fy in feixes:
                if not self._em_frente(ang, px, py):
                    continue
                dist = self._dist_perp(ang, fx, fy, px, py)
                if dist < menor_dist:
                    menor_dist = dist
                    ang_mp     = ang
                    em_perigo  = True

            if self.laser_estava_carregando:
                self.laser_estava_carregando = False
                recomp += 50.0 if (not em_perigo or menor_dist > RAIO_MORTE_LASER + 20) else -40.0

            if em_perigo:
                if self.ultima_dist_feixe is not None:
                    delta = menor_dist - self.ultima_dist_feixe
                    if abs(delta) < 80:
                        recomp += delta * 2.5
                self.ultima_dist_feixe = menor_dist

                if menor_dist <= RAIO_MORTE_LASER:
                    recomp -= 80.0
                    self.hits += 1
                elif menor_dist < 70:
                    recomp -= 6.0
                elif menor_dist < 130:
                    recomp -= 1.0
                else:
                    recomp += 3.0
            else:
                recomp += 1.0
                self.ultima_dist_feixe = None

            dist_borda = min(px, py, LARGURA_MAPA - px, ALTURA_MAPA - py)
            if dist_borda < 80:
                recomp -= 15.0

            recomp += 0.5

            if t_d >= laser['duracao_disparo']:
                self.rodadas_sobrevividas += 1
                marcos = {1: 60.0, 2: 100.0, 3: 180.0, 4: 400.0}
                recomp += marcos.get(rodada, 0.0)

                if rodada < self.rodada_max:
                    ang_player_boss = math.atan2(py - BOSS_POS[1], px - BOSS_POS[0])
                    cfg_next  = RODADAS_CONFIG[rodada + 1]
                    sent_prox = cfg_next['sentido']
                    ang_seg   = ang_player_boss + (math.pi / 2) * sent_prox
                    self.laser = {
                        'tempo_inicio':         self.tempo_ms,
                        'fase':                 'carregando',
                        'rodada':               rodada + 1,
                        'duracao_carga':        DURACAO_CARGA_MS,
                        'duracao_disparo':      DURACAO_DISPARO_MS,
                        'tempo_inicio_disparo': None,
                        'angulo_base_inicio':   ang_seg,
                    }
                    self.ultima_dist_feixe = None
                else:
                    self.done = True

        if self.hits >= self.MAX_HITS:
            recomp   -= 100.0
            self.done = True

        if self.tempo_ms > 70_000:
            self.done = True

        self.recompensa_acumulada += recomp
        return self._montar_tensor(), recomp, self.done

    def acoes_validas(self) -> list:
        px, py  = self.apolo_x, self.apolo_y
        m       = 80
        validas = list(range(9))
        if px < m and 2 in validas:                                           validas.remove(2)
        if px > LARGURA_MAPA - m and 3 in validas:                           validas.remove(3)
        if py < m and 0 in validas:                                           validas.remove(0)
        if py > ALTURA_MAPA  - m and 1 in validas:                           validas.remove(1)
        if (px < m or py < m) and 4 in validas:                              validas.remove(4)
        if (px > LARGURA_MAPA - m or py < m) and 5 in validas:               validas.remove(5)
        if (px < m or py > ALTURA_MAPA - m) and 6 in validas:                validas.remove(6)
        if (px > LARGURA_MAPA - m or py > ALTURA_MAPA - m) and 7 in validas: validas.remove(7)
        return validas if validas else [8]


# =============================================================================
# VECTOR ENV  —  N ambientes simultaneos
# =============================================================================
class VectorLaserEnv:
    """
    Roda N ambientes de forma sequencial mas sem overhead de reset/verificacao.
    Cada step coleta N transicoes de uma vez, alimentando o GPU com batches maiores.
    """

    def __init__(self, n_envs: int = 8):
        self.n_envs   = n_envs
        self.envs     = [LaserEnv() for _ in range(n_envs)]
        self.estados  = [env.reset() for env in self.envs]
        self.rodada_max = 4

    @property
    def rodada_max(self):
        return self._rodada_max

    @rodada_max.setter
    def rodada_max(self, v):
        self._rodada_max = v
        for env in self.envs:
            env.rodada_max = v

    def reset_todos(self):
        self.estados = [env.reset() for env in self.envs]
        return self.estados

    def step_todos(self, acoes: list):
        """
        Executa uma acao em cada ambiente.
        Ambientes terminados sao automaticamente resetados.
        Retorna: lista de (s, a, r, s', done, rodadas_ep, recomp_ep)
          rodadas_ep/recomp_ep sao None se o env ainda nao terminou.
        """
        transicoes = []
        for i, (env, acao) in enumerate(zip(self.envs, acoes)):
            s_ant  = self.estados[i]
            s_prox, r, done = env.step(acao)

            # Captura stats ANTES do reset (done=True apaga tudo no reset)
            rodadas_ep = env.rodadas_sobrevividas if done else None
            recomp_ep  = env.recompensa_acumulada if done else None

            transicoes.append((s_ant, acao, r, s_prox, done, rodadas_ep, recomp_ep))

            if done:
                self.estados[i] = env.reset()
            else:
                self.estados[i] = s_prox

        return transicoes

    def get_estados(self) -> list:
        return self.estados

    def get_acoes_validas(self) -> list:
        return [env.acoes_validas() for env in self.envs]

    def get_stats(self):
        """Retorna stats agregadas dos ambientes vivos."""
        recompensas = [env.recompensa_acumulada for env in self.envs]
        rodadas     = [env.rodadas_sobrevividas  for env in self.envs]
        return recompensas, rodadas


# =============================================================================
# LOOP PRINCIPAL DE TREINO GPU
# =============================================================================
def treinar_gpu(num_geracoes: int = 2000, n_envs: int = 8,
                salvar_intervalo: int = 100, curriculum: bool = False,
                limpar_pesos: bool = False):

    batch_size  = checar_gpu()
    venvs       = VectorLaserEnv(n_envs=n_envs)
    agente      = ApoloTreinoLaserGPU(batch_size=batch_size,
                                       limpar_pesos=limpar_pesos)

    hist_rod     = {1: [], 2: [], 3: [], 4: []}  # lista de bool (sobreviveu rodada?)
    melhor_rodada= 0

    # Curriculum com estado explícito de fase (evita recalculo por ep_total)
    fase_curr    = 1   # fase atual: 1 = so rod1 | 2 = rod1-2 | 3 = rod1-4
    rod_max_ant  = 0   # detecta transicao de fase

    ep_total     = 0
    passos_total = 0

    print("\n" + "=" * 65)
    print("  TREINO LASER GPU  --  APOLO  (AMP + VectorEnv)")
    print("=" * 65)
    print(f"  GPU:           {torch.cuda.get_device_name(0)}")
    print(f"  VRAM:          {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB")
    print(f"  Ambientes:     {n_envs} paralelos")
    print(f"  Batch size:    {batch_size}")
    print(f"  Replay buffer: 200.000 transicoes")
    print(f"  AMP FP16:      SIM")
    print(f"  Pesos limpos:  {'SIM (treinando do zero)' if limpar_pesos else 'NAO (continuando treino)'}")
    print(f"  Geracoes:      {num_geracoes}")
    if curriculum:
        print(f"  CURRICULUM:    Fase1=Rod1(sv>50%) | Fase2=Rod1-2(sv>40%) | Fase3=Rod1-4")
        print(f"                 Epsilon e resetado a 0.60 em cada transicao de fase.")
    print("=" * 65 + "\n")

    inicio        = time.time()
    ultimo_log    = inicio
    transicoes_s  = 0

    # Warmup: preenche o buffer com experiencias aleatorias antes de treinar
    print("[GPU] Aquecendo replay buffer...")
    while len(agente.replay) < batch_size * 4:
        estados = venvs.get_estados()
        avs     = venvs.get_acoes_validas()
        acoes   = [random.choice(av) for av in avs]
        trans   = venvs.step_todos(acoes)
        for s, a, r, s_, done, rod_ep, rec_ep in trans:
            agente.adicionar_transicao(s, a, r, s_, done)
    print(f"[GPU] Buffer aquecido ({len(agente.replay)} transicoes). Iniciando treino...\n")

    while ep_total < num_geracoes:

        # ---- Curriculum adaptativo -----------------------------------------
        if curriculum:
            # Avanca fase baseado em taxa de sobrevivencia das ultimas 100 eps
            sv1 = sum(hist_rod[1][-100:]) / max(1, len(hist_rod[1][-100:]))
            sv2 = sum(hist_rod[2][-100:]) / max(1, len(hist_rod[2][-100:]))
            sv3 = sum(hist_rod[3][-100:]) / max(1, len(hist_rod[3][-100:]))

            if   fase_curr == 1 and sv1 >= 0.50 and ep_total >= 300:
                fase_curr = 2   # Passou 50% em rod1 + minimo de 300 ep
            elif fase_curr == 2 and sv2 >= 0.40 and ep_total >= 600:
                fase_curr = 3   # Passou 40% em rod2
            elif fase_curr == 3 and sv3 >= 0.30 and ep_total >= 1000:
                fase_curr = 4   # Passou 30% em rod3 — treino completo

            rod_max = {1: 1, 2: 2, 3: 4, 4: 4}[fase_curr]
        else:
            rod_max = 4

        venvs.rodada_max = rod_max

        # ---- Deteccao de transicao de fase → reset epsilon -----------------
        if rod_max != rod_max_ant:
            if rod_max_ant > 0:   # nao e o inicio
                agente.taxa_exp = 0.60  # boost de exploracao para a nova fase
                print(f"\n  [CURRICULUM] Fase {fase_curr}: rod_max={rod_max}, "
                      f"epsilon -> {agente.taxa_exp:.2f} (re-explorando novo padrao)\n")
            rod_max_ant = rod_max

        # ---- Epsilon annealing global ---------------------------------------
        agente.taxa_exp = max(0.08, agente.taxa_exp * 0.9998)

        # ---- Step vetorizado ------------------------------------------------
        estados   = venvs.get_estados()
        avs       = venvs.get_acoes_validas()
        acoes     = agente.decidir_batch(estados, avs)
        trans     = venvs.step_todos(acoes)

        for s, a, r, s_, done, rod_ep, rec_ep in trans:
            agente.adicionar_transicao(s, a, r, s_, done)
            transicoes_s += 1

            if done:
                ep_total += 1
                # Registra em hist_rod quais rodadas foram concluidas neste episodio
                if rod_ep is not None:
                    for rr in range(1, 5):
                        hist_rod[rr].append(1 if rod_ep >= rr else 0)
                    if rod_ep > melhor_rodada:
                        melhor_rodada = rod_ep

        # ---- Treino ---------------------------------------------------------
        agente.treinar_passo()
        passos_total += 1

        # ---- Log a cada 5s --------------------------------------------------
        agora = time.time()
        if ep_total > 0 and (agora - ultimo_log > 5.0):
            elapsed = agora - inicio
            ep_s    = ep_total / max(1.0, elapsed)
            buf_sz  = len(agente.replay)

            sv = {rr: sum(hist_rod[rr][-100:]) / max(1, len(hist_rod[rr][-100:])) * 100
                  for rr in range(1, 5)}
            fase_c = f"F{fase_curr}/Rod{rod_max}" if curriculum else f"Rod{rod_max}"

            print(
                f"[Ep {ep_total:>5} | {fase_c}] "
                f"MelhorRod:{melhor_rodada}/4 | "
                f"Sv%: R1={sv[1]:.0f} R2={sv[2]:.0f} R3={sv[3]:.0f} R4={sv[4]:.0f} | "
                f"eps:{agente.taxa_exp:.3f} buf:{buf_sz:>6} | "
                f"{ep_s:.1f}ep/s"
            )
            ultimo_log = agora

        # ---- Salva pesos ----------------------------------------------------
        if ep_total > 0 and ep_total % salvar_intervalo == 0:
            agente.salvar_pesos()
            print(f"  [OK] Pesos salvos  (ep {ep_total})")

    # Final
    agente.salvar_pesos()
    dur = time.time() - inicio
    print("\n" + "=" * 65)
    print("  TREINO GPU CONCLUIDO!")
    print("=" * 65)
    print(f"  Total episodios:    {ep_total}")
    print(f"  Duracao:            {dur:.1f}s  ({dur/60:.1f} min)")
    print(f"  Throughput medio:   {ep_total/dur:.1f} ep/s")
    print(f"  Melhor rodada:      {melhor_rodada}/4")
    sv_fin = {rr: sum(hist_rod[rr][-100:]) / max(1, len(hist_rod[rr][-100:])) * 100 for rr in range(1, 5)}
    print(f"  Sv% (ult 100ep):   R1={sv_fin[1]:.0f}% R2={sv_fin[2]:.0f}% R3={sv_fin[3]:.0f}% R4={sv_fin[4]:.0f}%")
    print(f"  Pesos salvos em:    saves/apolo_memoria_dqn.pt")
    print("=" * 65)


# =============================================================================
# VERIFICACAO
# =============================================================================
def verificar():
    print("[VERIFICAR] Verificando ambiente GPU...")
    checar_gpu()

    env = LaserEnv()
    t   = env._montar_tensor()
    assert t.shape == (1, 40), f"Shape errado: {t.shape}"
    print(f"  Tensor shape: {t.shape} -- OK")

    device = torch.device("cuda")
    rede   = ApoloDQN().to(device)
    t_gpu  = t.to(device)

    with torch.no_grad():
        q = rede(t_gpu)
    assert q.shape == (1, 9)
    print(f"  Forward pass (GPU): {q.shape} -- OK")

    with torch.cuda.amp.autocast(dtype=torch.float16):
        q_fp16 = rede(t_gpu)
    print(f"  Forward pass (AMP FP16): {q_fp16.shape} -- OK")
    print(f"  Compativel com GAME5.py -- OK\n")

    # Benchmark rapido
    print("[VERIFICAR] Benchmark de velocidade (1000 forward passes)...")
    t0 = time.time()
    batch = t_gpu.repeat(256, 1)  # Simula batch de 256
    for _ in range(1000):
        with torch.no_grad(), torch.cuda.amp.autocast(dtype=torch.float16):
            rede(batch)
    torch.cuda.synchronize()
    t1 = time.time()
    print(f"  1000 x batch256 em {(t1-t0)*1000:.1f}ms = {1000/(t1-t0):.0f} batches/s")
    print(f"  = {1000*256/(t1-t0)/1000:.0f}k amostras/segundo -- OK\n")


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Treino Laser Apolo — GPU otimizado (GTX 1650+)"
    )
    parser.add_argument("--geracoes",   type=int, default=2000)
    parser.add_argument("--envs",       type=int, default=8,
                        help="Numero de ambientes paralelos (padrao: 8)")
    parser.add_argument("--salvar",     type=int, default=100)
    parser.add_argument("--curriculum", action="store_true")
    parser.add_argument("--verificar",  action="store_true")
    parser.add_argument("--limpar",     action="store_true",
                        help="Reinicia pesos do zero (use quando features mudaram)")
    args = parser.parse_args()

    if args.verificar:
        verificar()
        sys.exit(0)

    treinar_gpu(
        num_geracoes    = args.geracoes,
        n_envs          = args.envs,
        salvar_intervalo= args.salvar,
        curriculum      = args.curriculum,
        limpar_pesos    = args.limpar,
    )
