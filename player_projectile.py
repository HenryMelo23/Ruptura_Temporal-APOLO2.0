import math
import random

import pygame


_ORB_CACHE = {}
_PARTICLE_CACHE = {}


def _perfil_grafico(config_graficos):
    cfg = config_graficos or {}
    if not cfg.get("efeitos_visuais", True):
        return "baixo"
    nivel = str(cfg.get("nivel_detalhes", "alto")).lower()
    qualidade = str(cfg.get("qualidade_grafica", "alta")).lower()
    if not cfg.get("particulas_ativas", True):
        return "baixo"
    if nivel in ("baixo", "baixa") or qualidade in ("baixa", "baixo"):
        return "baixo"
    if nivel in ("medio", "media") or qualidade in ("media", "medio"):
        return "medio"
    return "alto"


def _parametros(perfil):
    if perfil == "alto":
        return {"raios": 9, "rastro": 6, "impacto": 46, "limite": 360, "ramo": True}
    if perfil == "medio":
        return {"raios": 5, "rastro": 4, "impacto": 28, "limite": 220, "ramo": False}
    return {"raios": 2, "rastro": 2, "impacto": 12, "limite": 100, "ramo": False}


def _quantizar_alpha(alpha):
    return max(0, min(255, int(alpha) // 12 * 12))


def _surface_orbe(raio, perfil, impulsiva=False):
    chave = (int(raio), perfil, bool(impulsiva))
    if chave in _ORB_CACHE:
        return _ORB_CACHE[chave]

    margem = 18 if perfil == "alto" else (13 if perfil == "medio" else 8)
    tamanho = (raio + margem) * 2
    surf = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
    centro = tamanho // 2

    cor_aura = (0, 185, 255) if not impulsiva else (70, 120, 255)
    cor_core = (165, 235, 255) if not impulsiva else (210, 240, 255)
    cor_profunda = (0, 42, 190) if not impulsiva else (30, 20, 210)

    if perfil != "baixo":
        for i in range(4, 0, -1):
            r = raio + i * (3 if perfil == "alto" else 2)
            alpha = int(22 + i * 13)
            pygame.draw.circle(surf, (*cor_aura, alpha), (centro, centro), r)

    pygame.draw.circle(surf, (0, 92, 230, 230), (centro, centro), raio + 4)
    pygame.draw.circle(surf, (*cor_profunda, 220), (centro + 2, centro + 2), raio + 1)
    pygame.draw.circle(surf, (0, 170, 255, 245), (centro, centro), raio)
    pygame.draw.circle(surf, (*cor_core, 255), (centro - max(1, raio // 3), centro - max(1, raio // 3)), max(2, raio // 2))
    pygame.draw.circle(surf, (235, 255, 255, 235), (centro - max(2, raio // 4), centro - max(2, raio // 4)), max(1, raio // 4))

    if perfil != "baixo":
        pygame.draw.circle(surf, (80, 220, 255, 210), (centro, centro), raio + 3, 1)
        pygame.draw.circle(surf, (0, 70, 255, 180), (centro + 1, centro + 1), raio + 6, 1)

    _ORB_CACHE[chave] = surf
    return surf


def _surface_particula(tamanho, cor, alpha):
    alpha = _quantizar_alpha(alpha)
    chave = (int(tamanho), tuple(cor[:3]), alpha)
    if chave in _PARTICLE_CACHE:
        return _PARTICLE_CACHE[chave]
    raio = max(1, int(tamanho))
    surf = pygame.Surface((raio * 4, raio * 4), pygame.SRCALPHA)
    centro = raio * 2
    pygame.draw.circle(surf, (*cor[:3], max(18, alpha // 3)), (centro, centro), raio * 2)
    pygame.draw.circle(surf, (*cor[:3], alpha), (centro, centro), raio)
    _PARTICLE_CACHE[chave] = surf
    return surf


class PlayerProjectileVFX:
    def __init__(self):
        self.particulas = []
        self._proximo_id = 1
        self._cores = [
            (0, 120, 255),
            (0, 185, 255),
            (45, 215, 255),
            (115, 190, 255),
            (190, 245, 255),
        ]

    def criar_disparo(self, centro_x, centro_y, largura, altura, angulo, velocidade, agora_ms, impulsiva=False):
        raio = max(7, min(18, int(min(largura, altura) * 0.34)))
        rect = pygame.Rect(int(centro_x - largura // 2), int(centro_y - altura // 2), int(largura), int(altura))
        disparo = {
            "rect": rect,
            "angulo": float(angulo),
            "pos_x": float(rect.x),
            "pos_y": float(rect.y),
            "vx": math.cos(angulo) * float(velocidade),
            "vy": math.sin(angulo) * float(velocidade),
            "raio_vfx": raio,
            "nascimento_ms": int(agora_ms),
            "seed_vfx": self._proximo_id * 7919 + int(agora_ms),
            "impulsiva_vfx": bool(impulsiva),
            "trail": [],
            "velocidade_base_vfx": float(velocidade),
        }
        self._proximo_id += 1
        return disparo

    def atualizar_disparo(self, disparo, velocidade, dt):
        angulo = disparo.get("angulo", 0.0)
        vx = math.cos(angulo) * float(velocidade)
        vy = math.sin(angulo) * float(velocidade)
        disparo["vx"] = vx
        disparo["vy"] = vy
        disparo["velocidade_base_vfx"] = float(velocidade)
        disparo["pos_x"] = float(disparo.get("pos_x", disparo["rect"].x)) + vx * dt
        disparo["pos_y"] = float(disparo.get("pos_y", disparo["rect"].y)) + vy * dt
        disparo["rect"].x = int(disparo["pos_x"])
        disparo["rect"].y = int(disparo["pos_y"])

        trail = disparo.setdefault("trail", [])
        trail.append((disparo["rect"].centerx, disparo["rect"].centery))
        if len(trail) > 8:
            del trail[:-8]

    def desenhar_disparo(self, tela, disparo, agora_ms, config_graficos=None, offset=(0, 0)):
        perfil = _perfil_grafico(config_graficos)
        p = _parametros(perfil)
        ox, oy = offset
        cx = disparo["rect"].centerx + ox
        cy = disparo["rect"].centery + oy
        raio = int(disparo.get("raio_vfx", 12))
        angulo = float(disparo.get("angulo", 0.0))
        dir_x = math.cos(angulo)
        dir_y = math.sin(angulo)
        tras_x = -dir_x
        tras_y = -dir_y
        lado_x = -dir_y
        lado_y = dir_x

        idade = max(0, agora_ms - int(disparo.get("nascimento_ms", agora_ms)))
        impulso = max(0.18, 1.0 - min(1.0, idade / 240.0))
        forca = min(1.0, abs(float(disparo.get("velocidade_base_vfx", 10.0))) / 18.0)
        recuo = (5.0 + 10.0 * forca) * (0.45 + impulso * 0.75)

        trail = disparo.get("trail", [])
        for idx, (tx, ty) in enumerate(reversed(trail[-p["rastro"]:])):
            fade = 1.0 - idx / max(1, p["rastro"])
            rr = max(2, int(raio * (0.45 + 0.34 * fade)))
            alpha = int(95 * fade)
            cor = (0, 135 + int(90 * fade), 255)
            surf = _surface_particula(rr, cor, alpha)
            tela.blit(surf, (int(tx + ox - rr * 2), int(ty + oy - rr * 2)))

        surf_orbe = _surface_orbe(raio, perfil, disparo.get("impulsiva_vfx", False))
        tela.blit(surf_orbe, (int(cx - surf_orbe.get_width() / 2), int(cy - surf_orbe.get_height() / 2)))

        rng = random.Random(int(disparo.get("seed_vfx", 0)) + int(agora_ms // 42))
        pulso = 1.0 + math.sin(agora_ms * 0.018 + disparo.get("seed_vfx", 0) * 0.01) * 0.16
        ponto = lambda p: (int(p[0]), int(p[1]))
        for i in range(p["raios"]):
            base_ang = (math.tau * i / max(1, p["raios"])) + rng.uniform(-0.42, 0.42)
            sx = cx + math.cos(base_ang) * (raio * 0.65)
            sy = cy + math.sin(base_ang) * (raio * 0.65)
            comprimento = (raio + rng.uniform(5, 15)) * pulso
            empurrao = recuo * rng.uniform(0.35, 1.0)
            lateral = rng.uniform(-5.5, 5.5)
            ex = cx + math.cos(base_ang) * comprimento + tras_x * empurrao + lado_x * lateral
            ey = cy + math.sin(base_ang) * comprimento + tras_y * empurrao + lado_y * lateral
            meio = (
                (sx + ex) * 0.5 + lado_x * rng.uniform(-4, 4) + tras_x * rng.uniform(0, recuo * 0.35),
                (sy + ey) * 0.5 + lado_y * rng.uniform(-4, 4) + tras_y * rng.uniform(0, recuo * 0.35),
            )
            cor = rng.choice(self._cores)
            pygame.draw.line(tela, cor, ponto((sx, sy)), ponto(meio), 2 if perfil == "alto" and i % 3 == 0 else 1)
            pygame.draw.line(tela, (185, 245, 255), ponto(meio), ponto((ex, ey)), 1)
            if p["ramo"] and i % 3 == 0:
                bx = meio[0] + lado_x * rng.uniform(-9, 9) + tras_x * rng.uniform(2, 8)
                by = meio[1] + lado_y * rng.uniform(-9, 9) + tras_y * rng.uniform(2, 8)
                pygame.draw.line(tela, (80, 210, 255), ponto(meio), ponto((bx, by)), 1)

    def criar_impacto(self, disparo, config_graficos=None, multiplicador=1.0):
        if not (config_graficos or {}).get("particulas_ativas", True):
            return
        perfil = _perfil_grafico(config_graficos)
        p = _parametros(perfil)
        cx, cy = disparo["rect"].center
        angulo = float(disparo.get("angulo", 0.0))
        dir_x = math.cos(angulo)
        dir_y = math.sin(angulo)
        count = max(6, int(p["impacto"] * multiplicador))
        rng = random.Random(int(disparo.get("seed_vfx", 0)) + pygame.time.get_ticks())

        novas = []
        for i in range(count):
            a = rng.uniform(0, math.tau)
            radial = rng.uniform(1.6, 8.8 if perfil == "alto" else 6.0)
            heranca = rng.uniform(1.4, 4.8)
            vida = rng.randint(260, 620 if perfil == "alto" else 460)
            novas.append({
                "x": cx + rng.uniform(-5, 5),
                "y": cy + rng.uniform(-5, 5),
                "vx": math.cos(a) * radial + dir_x * heranca,
                "vy": math.sin(a) * radial + dir_y * heranca,
                "vida": vida,
                "vida_max": vida,
                "tamanho": rng.choice([1, 1, 2, 2, 3, 4 if perfil == "alto" else 3]),
                "cor": rng.choice(self._cores),
                "drag": rng.uniform(0.88, 0.95),
                "grav": rng.uniform(-0.012, 0.026),
            })

        self.particulas.extend(novas)
        limite = p["limite"]
        if len(self.particulas) > limite:
            self.particulas = self.particulas[-limite:]

    def atualizar_e_desenhar_particulas(self, tela, dt, config_graficos=None, offset=(0, 0)):
        if not (config_graficos or {}).get("particulas_ativas", True):
            self.particulas.clear()
            return
        perfil = _perfil_grafico(config_graficos)
        limite = _parametros(perfil)["limite"]
        ox, oy = offset
        novas = []
        passo = max(0.25, min(3.0, float(dt)))
        for part in self.particulas[-limite:]:
            part["x"] += part["vx"] * passo
            part["y"] += part["vy"] * passo
            part["vx"] *= part["drag"]
            part["vy"] = part["vy"] * part["drag"] + part["grav"] * passo
            part["vida"] -= 16.67 * passo
            if part["vida"] <= 0:
                continue
            fator = max(0.0, min(1.0, part["vida"] / max(1, part["vida_max"])))
            alpha = int(235 * fator)
            tamanho = max(1, int(part["tamanho"] * (0.8 + fator * 0.7)))
            surf = _surface_particula(tamanho, part["cor"], alpha)
            tela.blit(surf, (int(part["x"] + ox - tamanho * 2), int(part["y"] + oy - tamanho * 2)))
            novas.append(part)
        self.particulas = novas


def estourar_disparo_eletrico(disparos, disparo, vfx, config_graficos=None):
    if disparo not in disparos:
        return
    if vfx is not None:
        vfx.criar_impacto(disparo, config_graficos)
    disparos.remove(disparo)
