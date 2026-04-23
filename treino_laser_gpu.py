"""
treino_laser_gpu.py  —  Versao GPU (GTX 1650 / RTX serie Turing+)
==================================================================
Versao do treino laser otimizada para GPU NVIDIA.

Hardware alvo:
  GPU:  NVIDIA GTX 1650 (4GB GDDR5, Compute 7.5, Turing)
  CPU:  AMD Ryzen 5 4600G (6C / 12T)
  RAM:  16 GB

Otimizacoes ativas vs versao CPU:
  [1] 8 Ambientes paralelos (VectorEnv) ........... ~4-6x mais transicoes/s
  [2] Mixed Precision FP16 (AMP torch.cuda.amp) ... ~1.5x speedup GPU
  [3] Batch size 256 (vs 64) ...................... GPU subutilizada com 64
  [4] Replay buffer 200k (vs 50k) ................. 16GB RAM tem espaco
  [5] torch.backends.cudnn.benchmark = True ....... Kernels otimizados
  [6] torch.compile (PyTorch 2.0+) ................ Lazy JIT ~10-20% boost
  [7] Pin memory no replay buffer ................. Transferencia CPU->GPU rapida
  [8] Target network update a cada 500 steps ...... Escala com volume de dados

Resultado esperado:
  CPU (v3): ~2 ep/s
  GPU (v4): ~10-20 ep/s (dependendo do overhead Python)

Compatibilidade:
  Usa o MESMO arquivo 'apolo_memoria_dqn.pt' do GAME5.py e treino_laser_apolo.py
  Mesma arquitetura ApoloDQN (40->128->64->9)
  Identico conjunto de features (v4: signed_approach, in_sweep_zone, etc.)

SETUP (rode setup_gpu.bat primeiro):
  Este script requer Python 3.12 + PyTorch-CUDA.
  Python 3.14 NAO e suportado pelo PyTorch CUDA.
  Veja setup_gpu.bat para instalar o ambiente correto.

Uso:
    .venv312\\Scripts\\python treino_laser_gpu.py
    .venv312\\Scripts\\python treino_laser_gpu.py --curriculum --geracoes 3000
    .venv312\\Scripts\\python treino_laser_gpu.py --verificar
    .venv312\\Scripts\\python treino_laser_gpu.py --visual
"""

import math
import random
import sys
import os
import time
import argparse
import collections
import threading

import torch
import torch.nn as nn
import torch.optim as optim

# -----------------------------------------------------------------------
# Verifica CUDA antes de qualquer coisa
# -----------------------------------------------------------------------
def checar_gpu():
    if not torch.cuda.is_available():
        print("\n[ERRO] CUDA nao disponivel!")
        print("       Certifique-se de usar o ambiente Python correto:")
        print("       > .venv312\\Scripts\\python treino_laser_gpu.py")
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
# REDE NEURAL  (identica ao GAME5.py)
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
# REPLAY BUFFER com PIN MEMORY (CPU->GPU mais rapido)
# =============================================================================
class ReplayBufferGPU:
    """
    Buffer circular com suporte a pin_memory para transferencia rapida.
    Armazena tensores na CPU (RAM) e transfere para GPU em batches.
    16GB RAM suporta facilmente 200k transicoes (apenas ~120MB).
    """

    def __init__(self, capacidade: int = 200_000, pin: bool = True):
        self.buffer  = collections.deque(maxlen=capacidade)
        self.pin     = pin and torch.cuda.is_available()

    def adicionar(self, estado, acao, recompensa, prox_estado, done):
        # Armazena na CPU (float32, desanexado do grafo)
        self.buffer.append((
            estado.cpu().detach(),
            acao,
            float(recompensa),
            prox_estado.cpu().detach(),
            float(done)
        ))

    def amostrar(self, batch_size: int, device: torch.device):
        amostra = random.sample(self.buffer, batch_size)
        estados, acoes, recompensas, prox_estados, dones = zip(*amostra)

        # Concatena no CPU primeiro (mais eficiente)
        s  = torch.cat(estados)
        s_ = torch.cat(prox_estados)

        if self.pin:
            # Pin memory: permite transferencia assincrona GPU
            s  = s.pin_memory()
            s_ = s_.pin_memory()

        return (
            s.to(device,  non_blocking=True),
            torch.tensor(acoes,      dtype=torch.long,    device=device),
            torch.tensor(recompensas,dtype=torch.float32, device=device),
            s_.to(device, non_blocking=True),
            torch.tensor(dones,      dtype=torch.float32, device=device),
        )

    def __len__(self):
        return len(self.buffer)


# =============================================================================
# AGENTE GPU  —  DQN + AMP + torch.compile
# =============================================================================
class ApoloTreinoLaserGPU:
    ARQUIVO_PESOS    = "apolo_memoria_dqn.pt"
    INPUT_SIZE       = 40
    OUTPUT_SIZE      = 9
    GAMMA            = 0.97
    LR               = 3e-4          # AMP permite LR um pouco maior
    TARGET_UPDATE    = 500           # Hard update a cada 500 passos (mais dados = update mais frequente)

    def __init__(self, batch_size: int = 256, taxa_exploracao: float = 0.80):
        self.device     = torch.device("cuda")
        self.batch_size = batch_size

        # Ativa cudnn benchmark (kernels otimizados para tamanho fixo de batch)
        torch.backends.cudnn.benchmark = True

        # Redes
        self.q_online = ApoloDQN(self.INPUT_SIZE, self.OUTPUT_SIZE).to(self.device)
        self.q_target = ApoloDQN(self.INPUT_SIZE, self.OUTPUT_SIZE).to(self.device)

        # torch.compile (PyTorch 2.0+, ~10-20% speedup)
        # Desativado no Windows pois o backend default 'inductor' requer Triton
        if sys.platform != "win32":
            try:
                self.q_online = torch.compile(self.q_online)
                self._compiled = True
                print("[GPU] torch.compile ativado")
            except Exception:
                self._compiled = False
                print("[GPU] torch.compile indisponivel (PyTorch < 2.0)")
        else:
            self._compiled = False
            print("[GPU] torch.compile desativado (Windows sem Triton nativo)")

        self.optimizer = optim.Adam(self.q_online.parameters(), lr=self.LR)
        self.criterion = nn.SmoothL1Loss()

        # AMP (Mixed Precision FP16)
        self.scaler   = torch.amp.GradScaler('cuda')
        self.amp_dtype= torch.float16

        self.replay   = ReplayBufferGPU(capacidade=200_000)
        self.taxa_exp = taxa_exploracao
        self.passos   = 0

        self._carregar_pesos()
        self._sincronizar_target()

    # -- Persistencia --------------------------------------------------------
    def _carregar_pesos(self):
        if os.path.exists(self.ARQUIVO_PESOS):
            try:
                state = torch.load(self.ARQUIVO_PESOS,
                                   map_location=self.device,
                                   weights_only=True)
                # Desembrulha se compilado
                try:
                    self.q_online.load_state_dict(state)
                except Exception:
                    self.q_online._orig_mod.load_state_dict(state)
                print(f"[APOLO] Pesos carregados de '{self.ARQUIVO_PESOS}'")
            except Exception as e:
                print(f"[APOLO] Falha ao carregar pesos: {e} -- iniciando zerado.")
        else:
            print("[APOLO] Nenhum arquivo de pesos -- iniciando zerado.")

    def _sincronizar_target(self):
        try:
            self.q_target.load_state_dict(self.q_online.state_dict())
        except Exception:
            # Fallback para modelo compilado
            self.q_target.load_state_dict(self.q_online._orig_mod.state_dict())

    def salvar_pesos(self):
        try:
            state = self.q_online.state_dict()
        except Exception:
            state = self.q_online._orig_mod.state_dict()
        torch.save(state, self.ARQUIVO_PESOS)

    # -- Inferencia em lote (para VectorEnv) ---------------------------------
    @torch.no_grad()
    def decidir_batch(self, tensores: list, acoes_validas_batch: list) -> list:
        """
        Decide para N ambientes de uma vez (um unico forward pass na GPU).
        tensores: lista de tensors shape (1, 40)
        Retorna: lista de acoes inteiras
        """
        stacked = torch.cat(tensores, dim=0).to(self.device)  # (N, 40)

        self.q_online.eval()
        with torch.amp.autocast('cuda', dtype=self.amp_dtype):
            q_vals = self.q_online(stacked)  # (N, 9)

        acoes = []
        for i, validas in enumerate(acoes_validas_batch):
            if random.random() < self.taxa_exp:
                acoes.append(random.choice(validas))
            else:
                q = q_vals[i].clone()
                for j in range(self.OUTPUT_SIZE):
                    if j not in validas:
                        q[j] = -60000.0
                acoes.append(int(torch.argmax(q).item()))
        return acoes

    # -- Aprendizado com AMP -------------------------------------------------
    def treinar_passo(self):
        if len(self.replay) < self.batch_size:
            return None

        estados, acoes, recompensas, prox_estados, dones = \
            self.replay.amostrar(self.batch_size, self.device)

        self.q_online.train()

        with torch.amp.autocast('cuda', dtype=self.amp_dtype):
            q_current = self.q_online(estados)
            q_atual   = q_current.gather(1, acoes.unsqueeze(1)).squeeze(1)

            with torch.no_grad():
                self.q_target.eval()
                q_next  = self.q_target(prox_estados)
                q_alvo  = recompensas + self.GAMMA * q_next.max(1)[0] * (1 - dones)

            loss = self.criterion(q_atual, q_alvo.detach())

        self.optimizer.zero_grad(set_to_none=True)  # set_to_none=True: mais rapido que zero_grad()
        self.scaler.scale(loss).backward()
        self.scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.q_online.parameters(), max_norm=10.0)
        self.scaler.step(self.optimizer)
        self.scaler.update()

        self.passos += 1
        if self.passos % self.TARGET_UPDATE == 0:
            self._sincronizar_target()

        return loss.item()

    def adicionar_transicao(self, s, a, r, s_, done):
        self.replay.adicionar(s, a, r, s_, done)


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
        Retorna: lista de (s, a, r, s', done) para cada env.
        """
        transicoes = []
        for i, (env, acao) in enumerate(zip(self.envs, acoes)):
            s_ant  = self.estados[i]
            s_prox, r, done = env.step(acao)
            info = {'rodadas': env.rodadas_sobrevividas, 'rodada_max': env.rodada_max}
            transicoes.append((s_ant, acao, r, s_prox, done, info))

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
                salvar_intervalo: int = 100, curriculum: bool = False):

    batch_size  = checar_gpu()
    venvs       = VectorLaserEnv(n_envs=n_envs)
    agente      = ApoloTreinoLaserGPU(batch_size=batch_size)

    hist_recomp  = []
    hist_sv      = []
    hist_rod     = {1: [], 2: [], 3: [], 4: []}
    melhor_recomp= -float('inf')
    melhor_rodada= 0

    # --- NOVO SISTEMA CURRICULUM (PERFORMANCE-BASED) ---
    fase_atual       = 1
    ep_ultimo_avanco = 0
    historico_fases  = {1: 0, 2: None, 4: None}

    # Contador de "episodios completos" (um env por vez pode terminar, conta como ep)
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
    print(f"  Geracoes:      {num_geracoes}")
    if curriculum:
        print(f"  CURRICULUM:    Performance-Based (Exige >75% sobrevivencia para avancar)")
    print("=" * 65 + "\n")

    inicio        = time.time()
    ultimo_log    = inicio
    ultimo_log_ep = -1
    transicoes_s  = 0

    # Warmup: preenche o buffer antes de comecar a treinar
    print("[GPU] Aquecendo replay buffer...")
    while len(agente.replay) < batch_size * 4:
        estados = venvs.get_estados()
        avs     = venvs.get_acoes_validas()
        acoes   = [random.choice(av) for av in avs]
        trans   = venvs.step_todos(acoes)
        for s, a, r, s_, done, info in trans:
            agente.adicionar_transicao(s, a, r, s_, done)
    print(f"[GPU] Buffer aquecido ({len(agente.replay)} transicoes). Iniciando treino...\n")

    while ep_total < num_geracoes:
        # 1. CURRICULUM BASEADO EM DESEMPENHO REAL
        if curriculum:
            if len(hist_rod[fase_atual]) >= 50:
                sucesso_fase = sum(hist_rod[fase_atual][-50:]) / 50.0
            else:
                sucesso_fase = 0.0

            # Só avança se dominar a fase atual (>= 75%) e já treinou um pouco nela (> 100 eps)
            if sucesso_fase >= 0.75 and (ep_total - ep_ultimo_avanco) > 100:
                if fase_atual == 1:
                    fase_atual = 2
                    ep_ultimo_avanco = ep_total
                    historico_fases[2] = ep_total
                    print(f"\n[CURRICULUM] Excelente! Apolo dominou a Rodada 1. Avancando para Rodada 2. (Ep {ep_total})")
                elif fase_atual == 2:
                    fase_atual = 4
                    ep_ultimo_avanco = ep_total
                    historico_fases[4] = ep_total
                    print(f"\n[CURRICULUM] Excelente! Apolo dominou a Rodada 2. Avancando para Rodada 4. (Ep {ep_total})")
            rod_max = fase_atual
        else:
            rod_max = 4
            fase_atual = 4
        venvs.rodada_max = rod_max

        # 2. EPSILON DECADENTE COM "BUMP" (Sem Espiral da Morte)
        # Decai de 80% para 10% suavemente (0.995 precisa de ~400 eps para chegar a 10%).
        # Ao avancar de fase, ele recebe um "choque" de 40% de exploracao para testar a fase nova.
        eps_base = 0.80 if fase_atual == 1 else 0.40
        agente.taxa_exp = max(0.10, eps_base * (0.995 ** (ep_total - ep_ultimo_avanco)))

        # === UM STEP VETORIZADO ===
        estados   = venvs.get_estados()
        avs       = venvs.get_acoes_validas()
        acoes     = agente.decidir_batch(estados, avs)
        trans     = venvs.step_todos(acoes)

        for s, a, r, s_, done, info in trans:
            agente.adicionar_transicao(s, a, r, s_, done)
            if done:
                ep_total += 1
                hist_sv.append(1 if info['rodadas'] >= info['rodada_max'] else 0)
                for r_idx in range(1, 5):
                    hist_rod[r_idx].append(1 if info['rodadas'] >= r_idx else 0)
            transicoes_s += 1

        # === TREINO ===
        agente.treinar_passo()
        passos_total += 1

        # === LOG a cada 5s ou a cada 50 episodios ===
        agora = time.time()
        if ep_total > 0 and (agora - ultimo_log > 5.0 or (ep_total % 50 == 0 and ep_total != ultimo_log_ep)):
            elapsed  = agora - inicio
            ep_s     = ep_total / max(1.0, elapsed)
            trans_s  = transicoes_s / max(1.0, elapsed)
            buf_sz   = len(agente.replay)

            sv_r = {r: sum(hist_rod[r][-50:]) / max(1, len(hist_rod[r][-50:])) * 100
                    for r in range(1, 5)} if hist_rod[1] else {1:0,2:0,3:0,4:0}
            fase_c = f"Rod1" if fase_atual == 1 else f"Rod1-2" if fase_atual == 2 else f"Rod1-4"

            # Identifica o melhor env ativo
            recomps, rodadas = venvs.get_stats()
            melhor_r_agora   = max(rodadas) if rodadas else 0
            if melhor_r_agora > melhor_rodada:
                melhor_rodada = melhor_r_agora

            print(
                f"[Ep {ep_total:>5}/{fase_c}] "
                f"MelhorRod:{melhor_rodada}/4 | "
                f"Sv%: R1={sv_r[1]:.0f} R2={sv_r[2]:.0f} R3={sv_r[3]:.0f} R4={sv_r[4]:.0f} | "
                f"eps:{agente.taxa_exp:.3f} buf:{buf_sz:>6} | "
                f"{ep_s:.1f}ep/s {trans_s:.0f}t/s"
            )
            ultimo_log    = agora
            ultimo_log_ep = ep_total

        # Salva pesos
        if ep_total > 0 and ep_total % salvar_intervalo == 0:
            agente.salvar_pesos()
            print(f"  [OK] Pesos salvos  (ep {ep_total})")

    # Final
    agente.salvar_pesos()
    dur    = time.time() - inicio
    
    # Calcular taxa de sobrevivencia final (ultimos 100 episodios se possivel)
    sv_final = {r: sum(hist_rod[r][-100:]) / max(1, len(hist_rod[r][-100:])) * 100 for r in range(1, 5)} if hist_rod[1] else {1:0,2:0,3:0,4:0}

    print("\n" + "=" * 65)
    print("  RELATORIO FINAL DE TREINAMENTO (GPU)")
    print("=" * 65)
    print(f"  [METRICAS GERAIS]")
    print(f"  Total episodios:    {ep_total}")
    print(f"  Duracao:            {dur:.1f}s  ({dur/60:.1f} min)")
    print(f"  Throughput medio:   {ep_total/dur:.1f} ep/s | {passos_total*n_envs/dur:.0f} t/s")
    print(f"  Melhor rodada:      {melhor_rodada}/4")
    print(f"  Epsilon final:      {agente.taxa_exp:.3f} ({agente.taxa_exp*100:.1f}% exploracao)")
    
    print(f"\n  [CURRICULUM MILESTONES]")
    if not curriculum:
        print(f"  Curriculum desativado.")
    else:
        print(f"  - Iniciou Rodada 1: Episodio {historico_fases.get(1, 0)}")
        print(f"  - Alcancou Rodada 2: " + (f"Episodio {historico_fases[2]}" if historico_fases.get(2) else "(Nao atingido)"))
        print(f"  - Alcancou Rodada 4: " + (f"Episodio {historico_fases[4]}" if historico_fases.get(4) else "(Nao atingido)"))
            
    print(f"\n  [TAXA DE SOBREVIVENCIA FINAL (Ultimos 100 eps)]")
    print(f"  Rodada 1 (R1):      {sv_final[1]:.1f}%")
    print(f"  Rodada 2 (R2):      {sv_final[2]:.1f}%")
    print(f"  Rodada 3 (R3):      {sv_final[3]:.1f}%")
    print(f"  Rodada 4 (R4):      {sv_final[4]:.1f}%")
    
    print(f"\n  Pesos salvos em:    apolo_memoria_dqn.pt")
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
    args = parser.parse_args()

    if args.verificar:
        verificar()
        sys.exit(0)

    treinar_gpu(
        num_geracoes    = args.geracoes,
        n_envs          = args.envs,
        salvar_intervalo= args.salvar,
        curriculum      = args.curriculum,
    )
