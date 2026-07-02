"""
Treino headless da arena da Umbra.

Objetivo:
  - Rodar muitas geracoes sem renderizar GAME5.py.
  - Treinar ApoloAgent e MemoriaEvolutivaUmbra usando as decisoes reais da Umbra.
  - Salvar checkpoints separados e promover o melhor apenas com --promover-melhor.

Uso:
  python tools/ai/treino_game5_headless.py --geracoes 50 --passos 12000
  python tools/ai/treino_game5_headless.py --geracoes 300 --passos 18000 --promover-melhor
  python tools/ai/treino_game5_headless.py --promover-checkpoint saves/headless_umbra/melhor
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
for folder in ("Engine", "Boss", "Fases", "Manifestacoes", "Aureas", "Rede", "Menus"):
    p = str(PROJECT_ROOT / folder)
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(PROJECT_ROOT)

import pygame
import torch

from apolo_brain import ApoloAgent, INPUT_SIZE
from Boss import habilidade_boss as hb
from sistema_ratos_umbra import GerenciadorRatos


LARGURA = 1360
ALTURA = 768
APOLO_W = 48
APOLO_H = 64
UMBRA_W = 126
UMBRA_H = 126
DT_MS = 16

ACOES_APOLO = {
    0: (0, -1),
    1: (0, 1),
    2: (-1, 0),
    3: (1, 0),
    4: (-1, -1),
    5: (1, -1),
    6: (-1, 1),
    7: (1, 1),
    8: (0, 0),
}

MAPAS_TREINO = [
    "Sprites/Fase1.png",
    "Sprites/Fase2.png",
    "Sprites/Fase3.png",
    "Sprites/Fase4.png",
    "Sprites/Fase6.png",
    "Sprites/Fase7.png",
    "Sprites/Fase9.png",
]


@dataclass
class ResultadoGeracao:
    geracao: int
    score: float
    venceu_apolo: bool
    tempo_s: float
    vida_apolo: float
    vida_umbra: float
    dano_apolo: float
    dano_umbra: float
    hits_sofridos: int
    acoes_umbra: Dict[str, int]


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def dist_ponto_linha(px: float, py: float, ox: float, oy: float, ang: float) -> Tuple[float, float]:
    dx = math.cos(ang)
    dy = math.sin(ang)
    vx = px - ox
    vy = py - oy
    proj = vx * dx + vy * dy
    perp = abs(vx * dy - vy * dx)
    return perp, proj


class ArenaUmbraHeadless:
    def __init__(self, seed: int | None = None, passos_max: int = 18000, salvar_trace: bool = False):
        self.rng = random.Random(seed)
        self.passos_max = passos_max
        self.salvar_trace = salvar_trace
        self.apolo = ApoloAgent(batch_size=64, taxa_exploracao=0.55)
        self.umbra = hb.MemoriaEvolutivaUmbra()
        self.ratos = GerenciadorRatos(LARGURA, ALTURA)
        self.trace: List[dict] = []
        pygame.init()
        self.reset(0)

    def reset(self, geracao: int) -> torch.Tensor:
        self.geracao = geracao
        self.tempo = 0
        self.frame = 0
        self.vida_apolo_max = 1000.0
        self.vida_apolo = self.vida_apolo_max
        self.vida_umbra_max = 9000.0
        self.vida_umbra = self.vida_umbra_max
        self.apolo_x = float(self.rng.randint(120, LARGURA - 180))
        self.apolo_y = float(self.rng.randint(120, ALTURA - 180))
        self.umbra_x = float(LARGURA // 2 - UMBRA_W // 2)
        self.umbra_y = float(ALTURA // 2 - UMBRA_H // 2)
        self.vel_apolo = 5.0
        self.dash_cd = 0
        self.disparo_cd = 0
        self.player_stun_ate = 0
        self.player_em_chamas_ate = 0
        self.ultimo_tick_chamas = 0
        self.ultimo_tick_miasma = 0
        self.ultimo_tick_vortice = 0
        self.dano_apolo = 0.0
        self.dano_umbra = 0.0
        self.hits_sofridos = 0
        self.historico_player: List[Tuple[float, float]] = []
        self.acoes_umbra: Dict[str, int] = {}
        self.ratos.resetar_partida()
        self.estado_ia = {
            "ultimo_ataque": 0,
            "intervalo": 900,
            "projeteis": [],
            "confianca": 0.5,
            "lead": 0.8,
            "erros_d": 0,
            "fase_tele": "espera",
            "proj_tele": None,
            "dano_recente": 0,
            "ultimo_teleporte": 0,
            "parede_ativa": False,
            "ultimo_sifon_fim": 0,
            "tempo_inicio_fase": 0,
            "tempo_inicio_dimensao": 0,
            "ultimo_transmutar": 0,
            "centro_mapa": (LARGURA // 2, ALTURA // 2),
            "alvo_ia": (LARGURA // 2, ALTURA // 2),
            "vel_x": 0.0,
            "vel_y": 0.0,
        }
        self.mapa_atual = self.rng.choice(MAPAS_TREINO)
        self.estado_ia["dimensao_ativa"] = self._dimensao_por_mapa(self.mapa_atual)
        return self._estado_apolo()

    def _dimensao_por_mapa(self, mapa: str) -> str:
        return {
            "Sprites/Fase1.png": "vortice",
            "Sprites/Fase2.png": "gravidade",
            "Sprites/Fase3.png": "necrose",
            "Sprites/Fase4.png": "ressonancia",
            "Sprites/Fase6.png": "hemorragia",
            "Sprites/Fase7.png": "atrito",
            "Sprites/Fase9.png": "rastro",
        }.get(mapa, "vortice")

    def _apolo_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.apolo_x), int(self.apolo_y), APOLO_W, APOLO_H)

    def _umbra_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.umbra_x), int(self.umbra_y), UMBRA_W, UMBRA_H)

    def _estado_apolo(self) -> torch.Tensor:
        px = self.apolo_x + APOLO_W / 2
        py = self.apolo_y + APOLO_H / 2
        bx = self.umbra_x + UMBRA_W / 2
        by = self.umbra_y + UMBRA_H / 2

        feat_px = px / LARGURA
        feat_py = py / ALTURA
        feat_bx = bx / LARGURA
        feat_by = by / ALTURA
        feat_vida_p = self.vida_apolo / self.vida_apolo_max
        feat_vida_b = self.vida_umbra / self.vida_umbra_max

        margem = 100.0
        borda_e = clamp(px / margem, 0, 1)
        borda_d = clamp((LARGURA - px) / margem, 0, 1)
        borda_c = clamp(py / margem, 0, 1)
        borda_b = clamp((ALTURA - py) / margem, 0, 1)
        em_canto = float((borda_e < 0.35 or borda_d < 0.35) and (borda_c < 0.35 or borda_b < 0.35))

        dist_perigo = 1.0
        proj_vx = 0.0
        proj_vy = 0.0
        proj_appr = 0.0
        for p in self.estado_ia.get("projeteis", []):
            cx, cy = p["rect"].center
            d = math.hypot(cx - px, cy - py)
            if d < dist_perigo * 250.0:
                dist_perigo = clamp(d / 250.0, 0, 1)
                proj_vx = math.cos(p.get("angulo", 0))
                proj_vy = math.sin(p.get("angulo", 0))
                proj_appr = float(proj_vx * (px - cx) + proj_vy * (py - cy) > 0)

        dash_cd_feat = float(self.dash_cd > 0)
        vel_feat = clamp(self.vel_apolo / 15.0, 0, 1)
        esferas_qtd = 0.0

        laser_feat = self._features_laser(px, py, bx, by)

        armadilhas_keys = [
            "vortice_ativo", "prisao_ativa", "caminho_espinhos", "laser_ativo",
            "descarga_eletrica", "miasma_ativo", "praga_ratos", "parede_ativa",
        ]
        armadilhas = [1.0 if self.estado_ia.get(k) else 0.0 for k in armadilhas_keys]

        features = [
            feat_px, feat_py, feat_bx, feat_by, feat_vida_p, feat_vida_b,
            borda_e, borda_d, borda_c, borda_b, em_canto,
            dist_perigo, proj_vx, proj_vy, dash_cd_feat, vel_feat, esferas_qtd, proj_appr,
            laser_feat["fase"], laser_feat["rodada"], laser_feat["progresso"],
            laser_feat["num_feixes"], laser_feat["sentido"], laser_feat["vel_ang"],
            laser_feat["ang_prox"], laser_feat["dist_feixe"], laser_feat["tempo_ate"],
            1.0, 0.0, 0.0,
            laser_feat["fuga_x"], laser_feat["fuga_y"], laser_feat["sweep"], laser_feat["segundo"],
        ] + armadilhas

        while len(features) < INPUT_SIZE:
            features.append(0.0)
        return torch.tensor(features[:INPUT_SIZE], dtype=torch.float32).unsqueeze(0)

    def _features_laser(self, px: float, py: float, bx: float, by: float) -> Dict[str, float]:
        laser = self.estado_ia.get("laser_ativo")
        base = {
            "fase": 0.0, "rodada": 0.0, "progresso": 0.0, "num_feixes": 0.0,
            "sentido": 0.0, "vel_ang": 0.0, "ang_prox": 0.0, "dist_feixe": 1.0,
            "tempo_ate": 1.0, "fuga_x": 0.0, "fuga_y": 0.0, "sweep": 0.0, "segundo": -1.0,
        }
        if not laser:
            return base
        rodada = int(laser.get("rodada", 1))
        cfg = self._cfg_laser(rodada)
        if laser.get("fase") == "carregando":
            base["fase"] = 0.5
            base["progresso"] = clamp((self.tempo - laser.get("tempo_inicio", self.tempo)) / max(1, laser.get("duracao_carga", 1500)), 0, 1)
        else:
            base["fase"] = 1.0
            base["progresso"] = clamp((self.tempo - laser.get("tempo_inicio_disparo", self.tempo)) / max(1, laser.get("duracao_disparo", 4000)), 0, 1)
        base["rodada"] = rodada / 4.0
        base["num_feixes"] = cfg["num"] / 6.0
        base["sentido"] = cfg["sentido"]
        base["vel_ang"] = clamp(abs(cfg["giro"]) / max(1.0, laser.get("duracao_disparo", 4000) / 1000.0) / (2 * math.pi), 0, 1)
        if base["fase"] < 1.0:
            return base

        ang_base = cfg["giro"] * base["progresso"] * cfg["sentido"]
        ang_player = math.atan2(py - by, px - bx)
        distancias = []
        for i in range(cfg["num"]):
            ang = ang_base + i * (2 * math.pi / cfg["num"])
            d, proj = dist_ponto_linha(px, py, bx, by, ang)
            if proj > 0:
                distancias.append((d, ang))
        if not distancias:
            return base
        distancias.sort(key=lambda item: item[0])
        menor, ang_prox = distancias[0]
        diff = (ang_player - ang_prox + math.pi) % (2 * math.pi) - math.pi
        base["ang_prox"] = clamp((diff * cfg["sentido"]) / math.pi, -1, 1)
        base["dist_feixe"] = clamp(menor / 400.0, 0, 1)
        base["tempo_ate"] = math.cos(ang_prox)
        ang_fuga = ang_prox + (math.pi / 2) * cfg["sentido"]
        base["fuga_x"] = math.cos(ang_fuga)
        base["fuga_y"] = math.sin(ang_fuga)
        restante = cfg["giro"] * (1.0 - base["progresso"])
        diff_sweep = diff * cfg["sentido"]
        if diff_sweep < 0:
            diff_sweep += 2 * math.pi
        base["sweep"] = float(0 < diff_sweep <= restante)
        if len(distancias) > 1:
            diff2 = (ang_player - distancias[1][1] + math.pi) % (2 * math.pi) - math.pi
            base["segundo"] = clamp((diff2 * cfg["sentido"]) / math.pi, -1, 1)
        return base

    def _cfg_laser(self, rodada: int) -> Dict[str, float]:
        if rodada == 1:
            return {"num": 1, "sentido": 1, "giro": math.pi * 1.0, "hit": 38}
        if rodada == 2:
            return {"num": 2, "sentido": -1, "giro": math.pi * 1.0, "hit": 38}
        if rodada == 3:
            return {"num": 4, "sentido": 1, "giro": math.pi * 0.4, "hit": 38}
        return {"num": 6, "sentido": -1, "giro": math.pi * 0.4, "hit": 16}

    def _mover_apolo(self, acao: int) -> None:
        if self.tempo < self.player_stun_ate:
            return
        dx, dy = ACOES_APOLO.get(acao, (0, 0))
        mag = math.hypot(dx, dy)
        if mag > 0:
            dx /= mag
            dy /= mag
        velocidade = self.vel_apolo
        if acao == 8 and self.dash_cd <= 0:
            if len(self.historico_player) >= 2:
                hx = self.apolo_x - self.historico_player[-2][0]
                hy = self.apolo_y - self.historico_player[-2][1]
                hmag = math.hypot(hx, hy) or 1.0
                dx, dy = hx / hmag, hy / hmag
            else:
                dx, dy = 1.0, 0.0
            velocidade = 80.0
            self.dash_cd = 90
        self.apolo_x = clamp(self.apolo_x + dx * velocidade, 0, LARGURA - APOLO_W)
        self.apolo_y = clamp(self.apolo_y + dy * velocidade, 0, ALTURA - APOLO_H)

    def _processar_umbra(self) -> None:
        boss_pos_ia = {
            "x": self.umbra_x,
            "y": self.umbra_y,
            "hitbox_centro": self._umbra_rect().center,
        }
        config = {
            "vida_atual": self.vida_umbra,
            "vida_max": self.vida_umbra_max,
            "mapa_atual": self.mapa_atual,
            "largura_mapa": LARGURA,
            "altura_mapa": ALTURA,
        }
        self.estado_ia = hb.processar_ia_umbra(
            self.tempo,
            boss_pos_ia,
            (self.apolo_x, self.apolo_y),
            self.historico_player,
            [],
            self.estado_ia,
            config,
            self.umbra,
        )
        for acao in self.estado_ia.get("decisoes_ativas", []):
            self.acoes_umbra[acao] = self.acoes_umbra.get(acao, 0) + 1

        nova_pos, _ = hb.movimentacao_inteligente_umbra(
            self.tempo,
            (self.umbra_x, self.umbra_y),
            (self.apolo_x, self.apolo_y),
            [],
            self.estado_ia,
            config,
            self.umbra,
            self.historico_player,
        )
        self.umbra_x = clamp(float(nova_pos[0]), 0, LARGURA - UMBRA_W)
        self.umbra_y = clamp(float(nova_pos[1]), 0, ALTURA - UMBRA_H)

    def _atualizar_teleporte(self) -> None:
        fase = self.estado_ia.get("fase_tele")
        sinal = self.estado_ia.get("proj_tele")
        if not sinal or fase == "espera":
            return
        if fase == "projetil_viajando":
            sinal["dist_percorrida"] = sinal.get("dist_percorrida", 0) + sinal.get("velocidade", 8) * 6
            if sinal["dist_percorrida"] >= sinal.get("dist_total", 1):
                sinal["tempo_chegada"] = self.tempo
                self.estado_ia["fase_tele"] = "portal_abrindo"
        elif fase == "portal_abrindo" and self.tempo - sinal.get("tempo_chegada", self.tempo) >= 450:
            if sinal.get("tipo") != "falso":
                tx, ty = sinal.get("target_pos", (self.umbra_x, self.umbra_y))
                self.umbra_x = clamp(float(tx), 0, LARGURA - UMBRA_W)
                self.umbra_y = clamp(float(ty), 0, ALTURA - UMBRA_H)
            self.estado_ia["fase_tele"] = "espera"
            self.estado_ia["proj_tele"] = None

    def _dano_no_apolo(self, valor: float, motivo: str, recompensa_umbra: float = 2.0) -> float:
        if valor <= 0:
            return 0.0
        self.vida_apolo = max(0.0, self.vida_apolo - valor)
        self.dano_apolo += valor
        self.hits_sofridos += 1
        self.umbra.treinar(recompensa_umbra, prioridade=True)
        return -valor * 0.8

    def _dano_na_umbra(self, valor: float) -> float:
        if valor <= 0:
            return 0.0
        self.vida_umbra = max(0.0, self.vida_umbra - valor)
        self.dano_umbra += valor
        self.estado_ia["dano_recente"] = self.estado_ia.get("dano_recente", 0) + valor
        self.umbra.treinar(-valor / 180.0, prioridade=True)
        return valor * 0.9

    def _atualizar_projeteis_umbra(self) -> float:
        reward = 0.0
        vivos = []
        rect_apolo = self._apolo_rect()
        for p in self.estado_ia.get("projeteis", []):
            if "pos_x" not in p:
                p["pos_x"] = float(p["rect"].x)
                p["pos_y"] = float(p["rect"].y)
            p["pos_x"] += p.get("velocidade", 10) * math.cos(p.get("angulo", 0))
            p["pos_y"] += p.get("velocidade", 10) * math.sin(p.get("angulo", 0))
            p["rect"].x = int(p["pos_x"])
            p["rect"].y = int(p["pos_y"])
            if p["rect"].colliderect(rect_apolo):
                reward += self._dano_no_apolo(90.0, "projetil", 3.0)
                continue
            if -80 < p["rect"].x < LARGURA + 80 and -80 < p["rect"].y < ALTURA + 80:
                vivos.append(p)
        self.estado_ia["projeteis"] = vivos
        return reward

    def _atualizar_habilidades(self) -> float:
        reward = 0.0
        cx = self.apolo_x + APOLO_W / 2
        cy = self.apolo_y + APOLO_H / 2
        bx = self.umbra_x + UMBRA_W / 2
        by = self.umbra_y + UMBRA_H / 2

        if self.estado_ia.get("parede_ativa"):
            if self.tempo - self.estado_ia.get("ultimo_tick_cura", 0) >= 600:
                cura = (self.vida_umbra_max - self.vida_umbra) * 0.012
                self.vida_umbra = min(self.vida_umbra_max, self.vida_umbra + cura)
                self.estado_ia["ultimo_tick_cura"] = self.tempo
                self.umbra.treinar(1.0)

        vortice = self.estado_ia.get("vortice_ativo")
        if vortice:
            tempo_v = self.tempo - vortice.get("tempo_inicio", self.tempo)
            if tempo_v < vortice.get("duracao", 8000):
                if tempo_v > 1500:
                    dx = vortice["x"] - cx
                    dy = vortice["y"] - cy
                    d = math.hypot(dx, dy)
                    if d > 1:
                        forca = vortice.get("forca", 2.8) * (1 - min(1, d / 900))
                        self.apolo_x = clamp(self.apolo_x + dx / d * forca, 0, LARGURA - APOLO_W)
                        self.apolo_y = clamp(self.apolo_y + dy / d * forca, 0, ALTURA - APOLO_H)
                    if d < 135 and self.tempo - self.ultimo_tick_vortice >= 450:
                        reward += self._dano_no_apolo(35.0, "vortice", 1.5)
                        self.ultimo_tick_vortice = self.tempo
            else:
                self.estado_ia["vortice_ativo"] = None

        prisao = self.estado_ia.get("prisao_ativa")
        if prisao:
            if self.tempo - prisao.get("tempo_inicio", self.tempo) < prisao.get("duracao", 3500):
                if prisao.get("rect") and prisao["rect"].colliderect(self._apolo_rect()):
                    self.player_stun_ate = max(self.player_stun_ate, self.tempo + 240)
                    if self.tempo % 500 < DT_MS:
                        reward += self._dano_no_apolo(25.0, "prisao", 1.5)
            else:
                self.estado_ia["prisao_ativa"] = None

        miasma = self.estado_ia.get("miasma_ativo")
        if miasma:
            if self.tempo - miasma.get("tempo_inicio", self.tempo) < miasma.get("duracao", 4500):
                if self.tempo - self.ultimo_tick_miasma >= 1000:
                    reward += self._dano_no_apolo(self.vida_apolo_max * 0.01, "miasma", 1.0)
                    self.ultimo_tick_miasma = self.tempo
            else:
                self.estado_ia["miasma_ativo"] = None

        descarga = self.estado_ia.get("descarga_eletrica")
        if descarga:
            if self.tempo - descarga.get("tempo_inicio", self.tempo) < descarga.get("duracao", 1800):
                dx = cx - descarga["x"]
                dy = cy - descarga["y"]
                dist = math.hypot(dx, dy)
                ang = math.atan2(dy, dx)
                diff = (ang - descarga["angulo_base"] + math.pi) % (2 * math.pi) - math.pi
                if dist <= descarga.get("raio_maximo", 380) and abs(diff) <= descarga.get("abertura", 0.9) / 2:
                    reward += self._dano_no_apolo(descarga.get("dano_por_tick", 12), "descarga", 1.3)
                    self.player_stun_ate = max(self.player_stun_ate, self.tempo + 120)
            else:
                self.estado_ia["descarga_eletrica"] = None

        reward += self._atualizar_espinhos(cx, cy)
        reward += self._atualizar_laser(cx, cy, bx, by)
        reward += self._atualizar_ratos()
        return reward

    def _atualizar_espinhos(self, cx: float, cy: float) -> float:
        caminho = self.estado_ia.get("caminho_espinhos")
        if not caminho:
            return 0.0
        tempo_c = self.tempo - caminho.get("tempo_inicio", self.tempo)
        dur_cres = caminho.get("duracao_crescimento", 1400)
        dur_exp = caminho.get("duracao_expansao", 1600)
        if tempo_c > dur_cres + dur_exp:
            self.estado_ia["caminho_espinhos"] = None
            return 0.0
        if tempo_c < dur_cres:
            return 0.0
        largura = caminho.get("largura_maxima", 80) / 2
        for raio in caminho.get("raios", []):
            ox, oy = raio["origem"]
            ang = raio["angulo"]
            comprimento = raio["comprimento"]
            perp, proj = dist_ponto_linha(cx, cy, ox, oy, ang)
            if 0 <= proj <= comprimento and perp <= largura:
                if self.tempo - caminho.get("ultimo_espinho_hit", 0) > 1000:
                    caminho["ultimo_espinho_hit"] = self.tempo
                    self.player_stun_ate = max(self.player_stun_ate, self.tempo + 1200)
                    self.estado_ia["bonus_tiros"] = self.estado_ia.get("bonus_tiros", 0) + 2
                    return self._dano_no_apolo(50.0, "espinhos", 2.5)
        return 0.0

    def _atualizar_laser(self, cx: float, cy: float, bx: float, by: float) -> float:
        laser = self.estado_ia.get("laser_ativo")
        if not laser:
            return 0.0
        tempo_l = self.tempo - laser.get("tempo_inicio", self.tempo)
        if laser.get("fase") == "carregando":
            if tempo_l >= laser.get("duracao_carga", 1500):
                laser["fase"] = "disparando"
                laser["tempo_inicio_disparo"] = self.tempo
            return 0.0

        rodada = int(laser.get("rodada", 1))
        cfg = self._cfg_laser(rodada)
        t_disp = self.tempo - laser.get("tempo_inicio_disparo", self.tempo)
        progresso = clamp(t_disp / max(1, laser.get("duracao_disparo", 4000)), 0, 1)
        ang_base = cfg["giro"] * progresso * cfg["sentido"]
        tomou = False
        for i in range(cfg["num"]):
            ang = ang_base + i * (2 * math.pi / cfg["num"])
            perp, proj = dist_ponto_linha(cx, cy, bx, by, ang)
            if proj > 0 and perp <= cfg["hit"]:
                tomou = True
                break
        reward = 0.0
        if tomou and self.tempo - self.estado_ia.get("ultimo_dano_laser", 0) > 130:
            reward += self._dano_no_apolo(self.vida_apolo_max * 0.08, "laser", 3.0)
            self.estado_ia["ultimo_dano_laser"] = self.tempo
            self.player_em_chamas_ate = self.tempo + 4000

        if t_disp >= laser.get("duracao_disparo", 4000):
            if rodada < 4:
                laser["rodada"] = rodada + 1
                laser["fase"] = "carregando"
                laser["tempo_inicio"] = self.tempo
            else:
                self.estado_ia["laser_ativo"] = None
                self.estado_ia["ultimo_laser"] = self.tempo

        if self.tempo < self.player_em_chamas_ate and self.tempo - self.ultimo_tick_chamas >= 1000:
            reward += self._dano_no_apolo(max(8.0, self.vida_apolo * 0.015), "chamas", 1.0)
            self.ultimo_tick_chamas = self.tempo
        return reward

    def _atualizar_ratos(self) -> float:
        if self.estado_ia.get("praga_ratos") and self.ratos.pode_spawnar(self.tempo):
            self.ratos.spawnar_ratos(self.tempo)
        self.ratos.atualizar(self.tempo, int(self.apolo_x + APOLO_W / 2), int(self.apolo_y + APOLO_H / 2))
        resultado = self.ratos.verificar_colisoes(self._apolo_rect(), self.vida_umbra, self.vida_umbra_max)
        if resultado["hits"] <= 0:
            return 0.0
        self.vida_umbra = resultado["vida_umbra_nova"]
        return self._dano_no_apolo(resultado["dano_total"], "ratos", 2.0 * resultado["hits"])

    def _apolo_atira(self) -> float:
        if self.disparo_cd > 0:
            return 0.0
        self.disparo_cd = 15
        cx = self.apolo_x + APOLO_W / 2
        cy = self.apolo_y + APOLO_H / 2
        bx = self.umbra_x + UMBRA_W / 2
        by = self.umbra_y + UMBRA_H / 2
        dist = math.hypot(cx - bx, cy - by)
        chance = clamp(0.92 - dist / 1900.0, 0.18, 0.92)
        if self.tempo < self.player_stun_ate:
            chance *= 0.4
        if self.estado_ia.get("miasma_ativo"):
            chance *= 0.55
        if self.rng.random() <= chance:
            dano = 46.0 + max(0.0, 420.0 - dist) * 0.04
            return self._dano_na_umbra(dano)
        return -0.5

    def step(self, acao: int) -> Tuple[torch.Tensor, float, bool]:
        estado_antigo = self._estado_apolo()
        vida_a_antes = self.vida_apolo
        vida_u_antes = self.vida_umbra

        self._mover_apolo(acao)
        self.historico_player.append((self.apolo_x, self.apolo_y))
        if len(self.historico_player) > 80:
            self.historico_player.pop(0)

        if self.dash_cd > 0:
            self.dash_cd -= 1
        if self.disparo_cd > 0:
            self.disparo_cd -= 1

        if self.frame % 4 == 0:
            self._processar_umbra()
        self._atualizar_teleporte()

        reward = 0.15
        reward += self._apolo_atira()
        reward += self._atualizar_projeteis_umbra()
        reward += self._atualizar_habilidades()

        # Recompensa densa por manter distancia util.
        d = math.hypot((self.apolo_x + APOLO_W / 2) - (self.umbra_x + UMBRA_W / 2), (self.apolo_y + APOLO_H / 2) - (self.umbra_y + UMBRA_H / 2))
        reward += 0.35 if 240 <= d <= 560 else -0.12
        if self.vida_apolo < vida_a_antes:
            reward -= (vida_a_antes - self.vida_apolo) * 0.5
        if self.vida_umbra < vida_u_antes:
            reward += (vida_u_antes - self.vida_umbra) * 0.7

        self.frame += 1
        self.tempo += DT_MS
        done = self.vida_apolo <= 0 or self.vida_umbra <= 0 or self.frame >= self.passos_max
        if self.vida_umbra <= 0:
            reward += 5000.0
            self.umbra.treinar(-50.0, prioridade=True)
        elif self.vida_apolo <= 0:
            reward -= 3000.0
            self.umbra.treinar(50.0, prioridade=True)

        estado_novo = self._estado_apolo()
        self.apolo.adicionar_transicao(estado_antigo, acao, reward, estado_novo, done)
        self.apolo.treinar_passo()

        if self.salvar_trace and self.frame % 120 == 0:
            self.trace.append({
                "t": self.tempo,
                "apolo": [round(self.apolo_x, 1), round(self.apolo_y, 1), round(self.vida_apolo, 1)],
                "umbra": [round(self.umbra_x, 1), round(self.umbra_y, 1), round(self.vida_umbra, 1)],
                "mente": self.estado_ia.get("mente_umbra", {}),
            })

        return estado_novo, reward, done

    def rodar_geracao(self, geracao: int) -> ResultadoGeracao:
        estado = self.reset(geracao)
        total_reward = 0.0
        done = False
        while not done:
            acao = self.apolo.decidir(estado, list(ACOES_APOLO.keys()))
            estado, reward, done = self.step(acao)
            total_reward += reward

        tempo_s = self.tempo / 1000.0
        score = (
            total_reward
            + self.dano_umbra * 0.8
            - self.dano_apolo * 0.55
            + (2500.0 if self.vida_umbra <= 0 else 0.0)
            - (1500.0 if self.vida_apolo <= 0 else 0.0)
            + tempo_s * 8.0
        )
        return ResultadoGeracao(
            geracao=geracao,
            score=round(score, 3),
            venceu_apolo=self.vida_umbra <= 0,
            tempo_s=round(tempo_s, 2),
            vida_apolo=round(self.vida_apolo, 2),
            vida_umbra=round(self.vida_umbra, 2),
            dano_apolo=round(self.dano_apolo, 2),
            dano_umbra=round(self.dano_umbra, 2),
            hits_sofridos=self.hits_sofridos,
            acoes_umbra=dict(sorted(self.acoes_umbra.items())),
        )

    def salvar_checkpoint(self, pasta: Path, resultado: ResultadoGeracao) -> None:
        pasta.mkdir(parents=True, exist_ok=True)
        torch.save(self.apolo.q_online.state_dict(), pasta / "apolo_memoria_dqn.pt")
        torch.save(self.umbra.q_network.state_dict(), pasta / "memoria_umbra_dqn.pt")
        with open(pasta / "apolo_arq.json", "w", encoding="utf-8") as f:
            json.dump(self.apolo.arq_cfg, f, indent=2)
        with open(pasta / "resultado.json", "w", encoding="utf-8") as f:
            json.dump(asdict(resultado), f, indent=2, ensure_ascii=False)
        if self.trace:
            with open(pasta / "trace.json", "w", encoding="utf-8") as f:
                json.dump(self.trace[-500:], f, indent=2, ensure_ascii=False)


def promover_checkpoint(pasta: Path) -> None:
    destinos = {
        "apolo_memoria_dqn.pt": PROJECT_ROOT / "saves" / "apolo_memoria_dqn.pt",
        "memoria_umbra_dqn.pt": PROJECT_ROOT / "saves" / "memoria_umbra_dqn.pt",
        "apolo_arq.json": PROJECT_ROOT / "saves" / "apolo_arq.json",
    }
    backup_dir = PROJECT_ROOT / "saves" / "backup_headless_promocao"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for nome, destino in destinos.items():
        origem = pasta / nome
        if not origem.exists():
            continue
        if destino.exists():
            shutil.copy2(destino, backup_dir / f"{destino.stem}_{int(time.time())}{destino.suffix}")
        shutil.copy2(origem, destino)


def main() -> int:
    parser = argparse.ArgumentParser(description="Treino headless da luta GAME5/Umbra.")
    parser.add_argument("--geracoes", type=int, default=20)
    parser.add_argument("--passos", type=int, default=12000, help="Passos por geracao. 18000 ~= 4m48s simulados.")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--saida", default="saves/headless_umbra")
    parser.add_argument("--promover-melhor", action="store_true")
    parser.add_argument("--promover-checkpoint", default=None, help="Promove um checkpoint ja treinado e encerra.")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()

    saida = PROJECT_ROOT / args.saida
    saida.mkdir(parents=True, exist_ok=True)

    if args.promover_checkpoint:
        checkpoint = Path(args.promover_checkpoint)
        if not checkpoint.is_absolute():
            checkpoint = PROJECT_ROOT / checkpoint
        promover_checkpoint(checkpoint)
        print(f"[HEADLESS] Checkpoint promovido: {checkpoint}")
        return 0

    arena = ArenaUmbraHeadless(seed=args.seed, passos_max=args.passos, salvar_trace=args.trace)
    historico: List[dict] = []
    melhor: ResultadoGeracao | None = None
    melhor_dir = saida / "melhor"
    inicio = time.time()

    print("[HEADLESS] Treino GAME5/Umbra")
    print(f"  geracoes: {args.geracoes}")
    print(f"  passos:   {args.passos}")
    print(f"  device:   {arena.apolo.device}")
    print(f"  saida:    {saida}")

    for geracao in range(1, args.geracoes + 1):
        resultado = arena.rodar_geracao(geracao)
        historico.append(asdict(resultado))
        if melhor is None or resultado.score > melhor.score:
            melhor = resultado
            arena.salvar_checkpoint(melhor_dir, resultado)

        if geracao % 5 == 0 or geracao == 1 or geracao == args.geracoes:
            media = sum(h["score"] for h in historico[-10:]) / min(len(historico), 10)
            print(
                f"[{geracao:04d}/{args.geracoes}] "
                f"score={resultado.score:9.1f} media10={media:9.1f} "
                f"win={'S' if resultado.venceu_apolo else 'N'} "
                f"t={resultado.tempo_s:6.1f}s "
                f"hpA={resultado.vida_apolo:7.1f} hpU={resultado.vida_umbra:8.1f}"
            )

        if geracao % 25 == 0:
            arena.salvar_checkpoint(saida / f"geracao_{geracao:04d}", resultado)
            with open(saida / "historico.json", "w", encoding="utf-8") as f:
                json.dump(historico, f, indent=2, ensure_ascii=False)

    with open(saida / "historico.json", "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)

    if melhor:
        print("\n[MELHOR]")
        print(json.dumps(asdict(melhor), indent=2, ensure_ascii=False))
        if args.promover_melhor:
            promover_checkpoint(melhor_dir)
            print("[HEADLESS] Melhor checkpoint promovido para saves/*.pt")
        else:
            print("[HEADLESS] Melhor checkpoint salvo separado. Use --promover-melhor para aplicar no jogo.")

    dur = time.time() - inicio
    print(f"[HEADLESS] concluido em {dur:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
