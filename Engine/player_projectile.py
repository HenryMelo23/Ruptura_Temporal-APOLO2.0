import math
import random

import pygame


_ORB_CACHE = {}
_PARTICLE_CACHE = {}
_FONT_CACHE = {}
_TEXT_CACHE = {}


_CORES_MANIFESTACAO = {
    "eletrica": ((0, 225, 255), (190, 250, 255), (0, 82, 255)),
    "lacerante": ((255, 42, 76), (255, 210, 155), (70, 0, 20)),
    "prismatica": ((60, 230, 255), (255, 95, 205), (255, 225, 80)),
    "retornante": ((135, 95, 255), (225, 210, 255), (255, 70, 205)),
    "parasitica": ((95, 255, 85), (175, 70, 235), (45, 18, 38)),
    "condutora": ((50, 255, 210), (235, 255, 185), (20, 70, 130)),
    "gravitante": ((120, 70, 255), (235, 210, 255), (5, 4, 18)),
    "ancorada": ((255, 215, 95), (225, 245, 255), (38, 56, 96)),
}


def _tipo_visual(disparo):
    tipo = str((disparo or {}).get("tipo_manifestacao") or "")
    if tipo == "lacerante_corte":
        return "lacerante"
    if tipo == "prismatica_feixe":
        return "prismatica"
    if tipo == "retornante_pulso":
        return "retornante"
    if tipo == "parasitica_semente":
        return "parasitica"
    if tipo == "condutora_fio":
        return "condutora"
    if tipo == "gravitante_orbe":
        return "gravitante"
    if tipo == "ancorada_disparo":
        return "ancorada"
    return "eletrica"


def _cores_tipo(tipo):
    tipo = str(tipo or "eletrica")
    if tipo in _CORES_MANIFESTACAO:
        return _CORES_MANIFESTACAO[tipo]
    return _CORES_MANIFESTACAO.get(_tipo_visual({"tipo_manifestacao": tipo}), _CORES_MANIFESTACAO["eletrica"])


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
        return {"raios": 5, "rastro": 4, "impacto": 20, "limite": 150, "ramo": True}
    if perfil == "medio":
        return {"raios": 3, "rastro": 3, "impacto": 10, "limite": 85, "ramo": False}
    return {"raios": 1, "rastro": 1, "impacto": 4, "limite": 36, "ramo": False}


def _quantizar_alpha(alpha):
    return max(0, min(255, int(alpha) // 12 * 12))


def _fonte_cache(tamanho):
    tamanho = int(tamanho)
    fonte = _FONT_CACHE.get(tamanho)
    if fonte is None:
        fonte = pygame.font.Font(None, tamanho)
        _FONT_CACHE[tamanho] = fonte
    return fonte


def _texto_cache(texto, tamanho, cor):
    chave = (str(texto), int(tamanho), tuple(cor[:3]))
    surf = _TEXT_CACHE.get(chave)
    if surf is None:
        if len(_TEXT_CACHE) > 128:
            _TEXT_CACHE.clear()
        surf = _fonte_cache(tamanho).render(str(texto), True, cor)
        _TEXT_CACHE[chave] = surf
    return surf


def _surface_orbe(raio, perfil, impulsiva=False, insana=False):
    chave = (int(raio), perfil, bool(impulsiva), bool(insana))
    if chave in _ORB_CACHE:
        return _ORB_CACHE[chave]

    margem = 18 if perfil == "alto" else (13 if perfil == "medio" else 8)
    tamanho = (raio + margem) * 2
    surf = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
    centro = tamanho // 2

    if insana:
        cor_aura = (168, 55, 255)
        cor_core = (95, 255, 135)
        cor_profunda = (80, 20, 150)
    else:
        cor_aura = (0, 185, 255) if not impulsiva else (70, 120, 255)
        cor_core = (165, 235, 255) if not impulsiva else (210, 240, 255)
        cor_profunda = (0, 42, 190) if not impulsiva else (30, 20, 210)

    if perfil != "baixo":
        for i in range(4, 0, -1):
            r = raio + i * (3 if perfil == "alto" else 2)
            alpha = int(22 + i * 13)
            pygame.draw.circle(surf, (*cor_aura, alpha), (centro, centro), r)

    pygame.draw.circle(surf, (125, 36, 220, 230) if insana else (0, 92, 230, 230), (centro, centro), raio + 4)
    pygame.draw.circle(surf, (*cor_profunda, 220), (centro + 2, centro + 2), raio + 1)
    pygame.draw.circle(surf, (50, 230, 120, 245) if insana else (0, 170, 255, 245), (centro, centro), raio)
    pygame.draw.circle(surf, (*cor_core, 255), (centro - max(1, raio // 3), centro - max(1, raio // 3)), max(2, raio // 2))
    pygame.draw.circle(surf, (235, 255, 255, 235), (centro - max(2, raio // 4), centro - max(2, raio // 4)), max(1, raio // 4))

    if perfil != "baixo":
        pygame.draw.circle(surf, (120, 255, 160, 210) if insana else (80, 220, 255, 210), (centro, centro), raio + 3, 1)
        pygame.draw.circle(surf, (170, 55, 255, 180) if insana else (0, 70, 255, 180), (centro + 1, centro + 1), raio + 6, 1)

    _ORB_CACHE[chave] = surf
    return surf


def _surface_plasma_eletrico(raio, perfil):
    chave = ("plasma_eletrico", int(raio), perfil)
    if chave in _ORB_CACHE:
        return _ORB_CACHE[chave]

    margem = 10 if perfil == "alto" else 7 if perfil == "medio" else 5
    tamanho = (raio + margem) * 2
    surf = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
    centro = tamanho // 2

    # Halo menor e mais seco: evita a leitura de bolha/agua.
    if perfil != "baixo":
        for i, alpha in ((3, 18), (2, 34), (1, 55)):
            pygame.draw.circle(surf, (0, 80, 255, alpha), (centro, centro), raio + i * 3)
    pygame.draw.circle(surf, (4, 22, 95, 210), (centro, centro), raio + 3)
    pygame.draw.circle(surf, (0, 210, 255, 235), (centro, centro), raio + 1)
    pygame.draw.circle(surf, (230, 255, 255, 255), (centro - max(1, raio // 4), centro - max(1, raio // 4)), max(2, raio // 2))
    pygame.draw.circle(surf, (255, 255, 255, 245), (centro - max(1, raio // 5), centro - max(1, raio // 5)), max(1, raio // 4))
    pygame.draw.circle(surf, (20, 95, 255, 185), (centro + 1, centro + 1), raio + 4, 1)
    pygame.draw.circle(surf, (185, 255, 255, 230), (centro, centro), raio + 1, 1)

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
        self.impactos = []
        self._proximo_id = 1
        self._config_frame = None
        self._quantidade_frame = 0
        self._cores = [
            (0, 120, 255),
            (0, 185, 255),
            (45, 215, 255),
            (115, 190, 255),
            (190, 245, 255),
        ]

    def _limitar_buffers(self, perfil):
        limite = _parametros(perfil)["limite"]
        if len(self.particulas) > limite:
            self.particulas = self.particulas[-limite:]
        limite_impactos = 28 if perfil == "alto" else 16 if perfil == "medio" else 8
        if len(self.impactos) > limite_impactos:
            self.impactos = self.impactos[-limite_impactos:]

    def preparar_frame(self, quantidade_disparos, config_graficos=None):
        """Ajusta somente a densidade visual quando muitos projeteis coexistem."""
        self._quantidade_frame = max(0, int(quantidade_disparos))
        config = dict(config_graficos or {})
        perfil_original = _perfil_grafico(config)

        # Todos os disparos continuam visiveis. Apenas raios, rastros e
        # particulas decorativas usam um perfil mais leve sob carga elevada.
        if self._quantidade_frame >= 32:
            perfil_efetivo = "baixo"
        elif self._quantidade_frame >= 14 and perfil_original == "alto":
            perfil_efetivo = "medio"
        else:
            perfil_efetivo = perfil_original

        if perfil_efetivo == "medio":
            config["nivel_detalhes"] = "medio"
            config["qualidade_grafica"] = "media"
        elif perfil_efetivo == "baixo":
            config["nivel_detalhes"] = "baixo"
            config["qualidade_grafica"] = "baixa"
        self._config_frame = config

    def _config_efetiva(self, config_graficos):
        return self._config_frame if self._config_frame is not None else config_graficos

    def criar_disparo(self, centro_x, centro_y, largura, altura, angulo, velocidade, agora_ms, impulsiva=False):
        raio = max(3, min(18, int(min(largura, altura) * 0.34)))
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
        if disparo.get("tipo_manifestacao") == "lacerante_corte":
            if pygame.time.get_ticks() - int(disparo.get("nascimento_ms", 0)) > int(disparo.get("duracao_ms", 1)):
                disparo["expirado"] = True
                disparo["rect"].x = -999999
            return
        if disparo.get("tipo_manifestacao") == "retornante_pulso":
            return

        angulo = disparo.get("angulo", 0.0)
        velocidade_real = float(disparo.get("velocidade_prismatica", velocidade))
        vx = math.cos(angulo) * velocidade_real
        vy = math.sin(angulo) * velocidade_real
        disparo["vx"] = vx
        disparo["vy"] = vy
        disparo["velocidade_base_vfx"] = velocidade_real
        disparo["pos_x"] = float(disparo.get("pos_x", disparo["rect"].x)) + vx * dt
        disparo["pos_y"] = float(disparo.get("pos_y", disparo["rect"].y)) + vy * dt
        disparo["rect"].x = int(disparo["pos_x"])
        disparo["rect"].y = int(disparo["pos_y"])

        trail = disparo.setdefault("trail", [])
        trail.append((disparo["rect"].centerx, disparo["rect"].centery))
        if len(trail) > 8:
            del trail[:-8]

    def desenhar_disparo(self, tela, disparo, agora_ms, config_graficos=None, offset=(0, 0)):
        config_graficos = self._config_efetiva(config_graficos)
        if disparo.get("tipo_manifestacao") == "lacerante_corte":
            try:
                import lacerante_manifestacao
                disparo["_vfx_quantidade_frame"] = self._quantidade_frame
                lacerante_manifestacao.desenhar_corte(tela, disparo, agora_ms)
            except Exception:
                pass
            self._desenhar_reforco_manifestacao(tela, disparo, agora_ms, config_graficos, offset)
            return
        if disparo.get("tipo_manifestacao") == "prismatica_feixe":
            try:
                import prismatica_manifestacao
                prismatica_manifestacao.desenhar_feixe(tela, disparo, agora_ms, offset)
            except Exception:
                pass
            self._desenhar_reforco_manifestacao(tela, disparo, agora_ms, config_graficos, offset)
            return
        if disparo.get("tipo_manifestacao") == "retornante_pulso":
            try:
                import retornante_manifestacao
                retornante_manifestacao.desenhar_pulso(tela, disparo, agora_ms, offset, config_graficos)
            except Exception:
                pass
            self._desenhar_reforco_manifestacao(tela, disparo, agora_ms, config_graficos, offset)
            return
        if disparo.get("tipo_manifestacao") == "parasitica_semente":
            try:
                import parasitica_manifestacao
                parasitica_manifestacao.desenhar_semente_disparo(tela, disparo, agora_ms, offset, config_graficos)
            except Exception:
                pass
            self._desenhar_reforco_manifestacao(tela, disparo, agora_ms, config_graficos, offset)
            return
        if disparo.get("tipo_manifestacao") == "condutora_fio":
            try:
                import condutora_manifestacao
                condutora_manifestacao.desenhar_fio_disparo(tela, disparo, agora_ms, offset, config_graficos)
            except Exception:
                pass
            self._desenhar_reforco_manifestacao(tela, disparo, agora_ms, config_graficos, offset)
            return
        if disparo.get("tipo_manifestacao") == "gravitante_orbe":
            try:
                import gravitante_manifestacao
                gravitante_manifestacao.desenhar_orbe_disparo(tela, disparo, agora_ms, offset, config_graficos)
            except Exception:
                pass
            self._desenhar_reforco_manifestacao(tela, disparo, agora_ms, config_graficos, offset)
            return
        if disparo.get("tipo_manifestacao") == "ancorada_disparo":
            try:
                import ancorada_manifestacao
                ancorada_manifestacao.desenhar_disparo_ancorado(tela, disparo, agora_ms, offset, config_graficos)
            except Exception:
                pass
            self._desenhar_reforco_manifestacao(tela, disparo, agora_ms, config_graficos, offset)
            return

        perfil = _perfil_grafico(config_graficos)
        p = _parametros(perfil)
        tipo = _tipo_visual(disparo)
        cor_base, cor_clara, cor_escura = _cores_tipo(tipo)
        ox, oy = offset
        cx = disparo["rect"].centerx + ox
        cy = disparo["rect"].centery + oy
        raio = max(4, int(disparo.get("raio_vfx", 12) * 0.72))
        angulo = float(disparo.get("angulo", 0.0))
        dir_x = math.cos(angulo)
        dir_y = math.sin(angulo)
        tras_x = -dir_x
        tras_y = -dir_y
        lado_x = -dir_y
        lado_y = dir_x

        is_insana = disparo.get("insana_vfx", False)
        is_impulsiva = disparo.get("impulsiva_vfx", False)

        idade = max(0, agora_ms - int(disparo.get("nascimento_ms", agora_ms)))
        impulso = max(0.18, 1.0 - min(1.0, idade / 240.0))
        forca = min(1.0, abs(float(disparo.get("velocidade_base_vfx", 10.0))) / 18.0)
        recuo = (5.0 + 10.0 * forca) * (0.45 + impulso * 0.75)

        # -------------------------------------------------------------
        # V F X   2 . 0  :  Ribbon Trail com Wobble e Additive Blending
        # -------------------------------------------------------------
        trail = disparo.get("trail", [])
        carga_alta = self._quantidade_frame >= 20
        carga_extrema = self._quantidade_frame >= 32
        tamanho_rastro = 1 if carga_extrema else max(2, int(p["rastro"] * (1.35 if is_impulsiva else 0.82)))

        # Desenhamos do mais velho para o mais novo
        for idx, (tx, ty) in enumerate(reversed(trail[-tamanho_rastro:])):
            fade = 1.0 - idx / max(1, tamanho_rastro) # 1.0 = cabeca, 0.0 = cauda

            wobble_x, wobble_y = 0, 0
            if carga_alta:
                wobble_x, wobble_y = 0, 0
            elif is_insana:
                # Personalidade Insana: Rastro vibra loucamente fora do eixo
                vib = math.sin(agora_ms * 0.03 + idx * 0.8) * 8.0 * fade
                wobble_x = lado_x * vib
                wobble_y = lado_y * vib

            rr = max(1, int(raio * (0.18 + 0.34 * fade))) if not is_impulsiva else max(1, int(raio * (0.12 + 0.26 * fade)))
            alpha = int(130 * fade) if is_impulsiva else int(74 * fade)

            if is_insana:
                cor = (150 + int(105 * fade), 20, 255)
            elif is_impulsiva:
                cor = (20, 180 + int(75 * fade), 255)
            else:
                cor = (0, 150 + int(105 * fade), 255)

            if tipo == "eletrica":
                sx = int(tx + ox + wobble_x)
                sy = int(ty + oy + wobble_y)
                comprimento_faisca = max(4, int(9 * fade))
                pygame.draw.line(
                    tela,
                    (90, 220, 255) if idx % 2 else (230, 255, 255),
                    (int(sx + lado_x * 2), int(sy + lado_y * 2)),
                    (int(sx + tras_x * comprimento_faisca - lado_x * 2), int(sy + tras_y * comprimento_faisca - lado_y * 2)),
                    1,
                )
                if idx % 2 == 0:
                    pygame.draw.circle(tela, (0, 190, 255), (sx, sy), 1)
                continue
            surf = _surface_particula(rr, cor, alpha)
            # Additive Blending (Brilho Intenso)
            tela.blit(surf, (int(tx + ox + wobble_x - surf.get_width()//2), int(ty + oy + wobble_y - surf.get_height()//2)), special_flags=pygame.BLEND_RGB_ADD)

        # -------------------------------------------------------------
        # N Ú C L E O   P R I N C I P A L
        # -------------------------------------------------------------
        # Tremor na Insana
        if is_insana:
            cx += math.cos(agora_ms * 0.05) * 3
            cy += math.sin(agora_ms * 0.06) * 3

        surf_orbe = _surface_plasma_eletrico(raio, perfil) if not is_impulsiva and not is_insana else _surface_orbe(raio, perfil, is_impulsiva, is_insana)
        # Modo aditivo pro núcleo brilhar como plasma puro
        tela.blit(surf_orbe, (int(cx - surf_orbe.get_width() / 2), int(cy - surf_orbe.get_height() / 2)), special_flags=pygame.BLEND_RGB_ADD)

        # -------------------------------------------------------------
        # E L E T R I C I D A D E   &   D E T A L H E S
        # -------------------------------------------------------------
        if carga_extrema:
            self._desenhar_reforco_manifestacao(tela, disparo, agora_ms, config_graficos, offset)
            return

        rng = random.Random(int(disparo.get("seed_vfx", 0)) + int(agora_ms // (25 if is_insana else 42)))
        pulso = 1.0 + math.sin(agora_ms * 0.018 + disparo.get("seed_vfx", 0) * 0.01) * (0.3 if is_insana else 0.16)

        ponto = lambda p_c: (int(p_c[0]), int(p_c[1]))
        total_raios = max(1, int(p["raios"] * (1.35 if is_insana else 0.72)))
        if carga_alta:
            total_raios = min(total_raios, 2)
        for i in range(total_raios):
            base_ang = (math.tau * i / max(1, p["raios"])) + rng.uniform(-0.6, 0.6)
            # Se for impulsiva, jogar os raios majoritariamente para trás (aerodinâmica)
            if is_impulsiva:
                base_ang = angulo + math.pi + rng.uniform(-0.8, 0.8)

            sx = cx + math.cos(base_ang) * (raio * 0.45)
            sy = cy + math.sin(base_ang) * (raio * 0.45)
            comprimento = (raio + rng.uniform(4, 18 if is_insana else 10)) * pulso
            empurrao = recuo * rng.uniform(0.18, 0.65)
            lateral = rng.uniform(-5.5, 5.5) if is_insana else rng.uniform(-2.8, 2.8)

            ex = cx + math.cos(base_ang) * comprimento + tras_x * empurrao + lado_x * lateral
            ey = cy + math.sin(base_ang) * comprimento + tras_y * empurrao + lado_y * lateral
            meio = (
                (sx + ex) * 0.5 + lado_x * rng.uniform(-6, 6) + tras_x * rng.uniform(0, recuo * 0.4),
                (sy + ey) * 0.5 + lado_y * rng.uniform(-6, 6) + tras_y * rng.uniform(0, recuo * 0.4),
            )

            if is_insana:
                cor_raio = rng.choice([(180, 50, 255), (255, 80, 255), (100, 255, 150)])
                cor_ponta = (150, 255, 180)
            elif is_impulsiva:
                cor_raio = rng.choice([(50, 200, 255), (100, 255, 255)])
                cor_ponta = (200, 255, 255)
            else:
                cor_raio = rng.choice(self._cores)
                cor_ponta = (185, 245, 255)

            pygame.draw.line(tela, cor_raio, ponto((sx, sy)), ponto(meio), 2 if perfil == "alto" else 1)
            pygame.draw.line(tela, cor_ponta, ponto(meio), ponto((ex, ey)), 1)

            if (p["ramo"] or is_insana) and i % 2 == 0:
                bx = meio[0] + lado_x * rng.uniform(-12, 12) + tras_x * rng.uniform(2, 10)
                by = meio[1] + lado_y * rng.uniform(-12, 12) + tras_y * rng.uniform(2, 10)
                pygame.draw.line(tela, cor_raio, ponto(meio), ponto((bx, by)), 1)

        self._desenhar_reforco_manifestacao(tela, disparo, agora_ms, config_graficos, offset)

    def _desenhar_reforco_manifestacao(self, tela, disparo, agora_ms, config_graficos=None, offset=(0, 0)):
        perfil = _perfil_grafico(config_graficos)
        if self._quantidade_frame >= 20:
            return
        if perfil == "baixo" and self._quantidade_frame >= 8:
            return
        tipo = _tipo_visual(disparo)
        if tipo == "lacerante":
            return
        cor, clara, escura = _cores_tipo(tipo)
        ox, oy = offset
        cx = int(disparo["rect"].centerx + ox)
        cy = int(disparo["rect"].centery + oy)
        raio = max(3, int(disparo.get("raio_vfx", 8) * 0.58))
        angulo = float(disparo.get("angulo", 0.0))
        dx, dy = math.cos(angulo), math.sin(angulo)
        nx, ny = -dy, dx
        seed = int(disparo.get("seed_vfx", 0))
        pulso = 0.5 + 0.5 * math.sin(agora_ms * 0.018 + seed * 0.003)

        if tipo == "eletrica":
            rng = random.Random(seed + int(agora_ms // 38))
            externo = raio + 4 + int(2 * pulso)
            pygame.draw.circle(tela, clara, (cx, cy), max(2, raio // 2))
            pygame.draw.circle(tela, cor, (cx, cy), externo, 1)
            for _ in range(3 if perfil != "alto" else 5):
                a = rng.uniform(0, math.tau)
                b = a + rng.uniform(-0.9, 0.9)
                p1 = (int(cx + math.cos(a) * (raio + 2)), int(cy + math.sin(a) * (raio + 2)))
                p2 = (int(cx + math.cos(b) * (externo + rng.uniform(2, 7))), int(cy + math.sin(b) * (externo + rng.uniform(2, 7))))
                pygame.draw.line(tela, clara if rng.random() < 0.45 else cor, p1, p2, 1)
        elif tipo == "lacerante":
            comprimento = 18 + int(10 * pulso)
            p1 = (int(cx - dx * comprimento), int(cy - dy * comprimento))
            p2 = (int(cx + dx * comprimento), int(cy + dy * comprimento))
            pygame.draw.line(tela, escura, (int(p1[0] + nx * 4), int(p1[1] + ny * 4)), (int(p2[0] + nx * 4), int(p2[1] + ny * 4)), 2)
            pygame.draw.line(tela, cor, p1, p2, 2)
            pygame.draw.line(tela, clara, (int(cx - dx * 5), int(cy - dy * 5)), (int(cx + dx * 11), int(cy + dy * 11)), 1)
        elif tipo == "prismatica":
            pts = [
                (int(cx + dx * (raio + 14)), int(cy + dy * (raio + 14))),
                (int(cx - dx * 8 + nx * (raio + 3)), int(cy - dy * 8 + ny * (raio + 3))),
                (int(cx - dx * 14), int(cy - dy * 14)),
                (int(cx - dx * 8 - nx * (raio + 3)), int(cy - dy * 8 - ny * (raio + 3))),
            ]
            pygame.draw.polygon(tela, clara, pts, 1)
            if perfil == "alto":
                pygame.draw.line(tela, cor, pts[0], pts[2], 1)
                pygame.draw.line(tela, (255, 225, 80), pts[1], pts[3], 1)
        elif tipo == "retornante":
            giro = agora_ms * (0.011 if disparo.get("fase") != "volta" else 0.018) + seed * 0.001
            for k in range(2 if perfil != "baixo" else 1):
                r = raio + 4 + k * 4 + int(2 * pulso)
                rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
                pygame.draw.arc(tela, clara if k == 0 else cor, rect, giro + k, giro + k + math.pi * 1.35, 1)
            if str(disparo.get("fase", "")) == "volta":
                pygame.draw.line(tela, clara, (int(cx + dx * 8), int(cy + dy * 8)), (int(cx - dx * 18), int(cy - dy * 18)), 1)
        elif tipo == "parasitica":
            rng = random.Random(seed + int(agora_ms // 90))
            for k in range(5):
                a = k * math.tau / 5 + pulso * 0.8
                p1 = (int(cx + math.cos(a) * raio * 0.55), int(cy + math.sin(a) * raio * 0.55))
                p2 = (int(cx + math.cos(a) * (raio + rng.uniform(3, 9))), int(cy + math.sin(a) * (raio + rng.uniform(3, 9))))
                pygame.draw.line(tela, cor if k % 2 else clara, p1, p2, 1)
            pygame.draw.circle(tela, escura, (cx, cy), raio + 4, 1)
        elif tipo == "condutora":
            lado = raio + 5
            pts = [(cx, cy - lado), (cx + lado, cy), (cx, cy + lado), (cx - lado, cy)]
            pygame.draw.polygon(tela, cor, pts, 1)
            if perfil != "baixo":
                bit = "1" if (seed + int(agora_ms // 180)) % 2 else "0"
                try:
                    fonte = _fonte_cache(15)
                    tela.blit(fonte.render(bit, True, clara), (cx - 4, cy - 7))
                except Exception:
                    pass
        elif tipo == "gravitante":
            for k in range(2 if perfil != "baixo" else 1):
                a = agora_ms * 0.010 + seed * 0.001 + k * math.tau / 3
                px = cx + math.cos(a) * (raio + 5 + k * 2)
                py = cy + math.sin(a) * (raio + 5 + k * 2)
                pygame.draw.circle(tela, clara if k == 0 else cor, (int(px), int(py)), 2)
            pygame.draw.circle(tela, escura, (cx, cy), raio + 6, 1)
        elif tipo == "ancorada":
            lado = raio + 5
            pygame.draw.line(tela, clara, (cx - lado, cy), (cx + lado, cy), 2)
            pygame.draw.line(tela, clara, (cx, cy - lado), (cx, cy + lado), 2)
            pygame.draw.rect(tela, cor, pygame.Rect(cx - lado, cy - lado, lado * 2, lado * 2), 1)

    def criar_impacto(self, disparo, config_graficos=None, multiplicador=1.0):
        config_graficos = self._config_efetiva(config_graficos)
        if not (config_graficos or {}).get("particulas_ativas", True):
            return
        perfil = _perfil_grafico(config_graficos)
        p = _parametros(perfil)
        tipo = _tipo_visual(disparo)
        cor_base, cor_clara, cor_escura = _cores_tipo(tipo)
        cx, cy = disparo["rect"].center
        angulo = float(disparo.get("angulo", 0.0))
        dir_x = math.cos(angulo)
        dir_y = math.sin(angulo)
        count = max(8, int(p["impacto"] * 1.5 * multiplicador)) # Mais partículas
        rng = random.Random(int(disparo.get("seed_vfx", 0)) + pygame.time.get_ticks())
        count = max(6, int(p["impacto"] * multiplicador))
        if self._quantidade_frame >= 32:
            count = 1 if tipo == "eletrica" else 0
        elif self._quantidade_frame >= 20:
            count = max(1, count // 4)
        elif self._quantidade_frame >= 12:
            count = max(2, count // 2)

        if tipo == "eletrica":
            count = int(count * 0.82)
        elif tipo == "prismatica":
            count = int(count * 1.0)
        elif tipo in ("parasitica", "ancorada"):
            count = int(count * 0.72)

        is_insana = disparo.get("insana_vfx", False)
        is_impulsiva = disparo.get("impulsiva_vfx", False)

        duracao = {
            "eletrica": 360,
            "lacerante": 260,
            "prismatica": 330,
            "retornante": 390,
            "parasitica": 420,
            "condutora": 340,
            "gravitante": 460,
            "ancorada": 520,
        }.get(tipo, 340)
        if self._quantidade_frame < 42 or tipo == "eletrica":
            self.impactos.append({
                "tipo": tipo,
                "x": float(cx),
                "y": float(cy),
                "angulo": angulo,
                "inicio_ms": pygame.time.get_ticks(),
                "duracao_ms": duracao if self._quantidade_frame < 20 else max(160, int(duracao * 0.55)),
                "seed": int(disparo.get("seed_vfx", 0)) ^ rng.randint(1, 999999),
                "raio": max(6, int(disparo.get("raio_vfx", 8))),
                "retorno": tipo == "retornante" and str(disparo.get("fase", "")) == "volta",
            })

        novas = []
        for i in range(count):
            a = rng.uniform(0, math.tau)
            # Expansão mais violenta e direcional
            radial = rng.uniform(2.5, 12.0 if perfil == "alto" else 8.0)
            heranca = rng.uniform(0.5, 3.0) # Herda um pouco do movimento para frente
            vida = rng.randint(300, 800 if perfil == "alto" else 500)

            # Adicionar rotação às partículas para dar impressão de fragmentos poligonais voando
            vel_rot = rng.uniform(-15.0, 15.0)

            if is_insana:
                cor = rng.choice([(180, 50, 255), (100, 255, 150), (255, 100, 255)])
            elif is_impulsiva:
                cor = rng.choice([(50, 200, 255), (255, 255, 255), (0, 150, 255)])
            else:
                cor = rng.choice(self._cores)

            forma = "faisca"
            grav = rng.uniform(0.05, 0.15)
            if tipo == "eletrica":
                radial = rng.uniform(4.0, 11.0 if perfil == "alto" else 8.0)
                heranca = rng.uniform(0.0, 1.0)
                vida = rng.randint(150, 310 if perfil == "alto" else 240)
                cor = rng.choice([(0, 190, 255), (60, 230, 255), (210, 255, 255), (45, 105, 255)])
                forma = "raio"
                grav = 0.0
            elif tipo == "lacerante":
                a = angulo + rng.choice((-1, 1)) * math.pi / 2 + rng.uniform(-0.7, 0.7)
                radial = rng.uniform(3.0, 12.0)
                cor = rng.choice([cor_base, cor_clara, cor_escura, (130, 0, 18)])
                forma = "lasca"
                grav = 0.05
            elif tipo == "prismatica":
                cor = rng.choice([(60, 230, 255), (255, 90, 205), (255, 230, 80), (150, 100, 255)])
                forma = "triangulo"
                grav = 0.02
            elif tipo == "parasitica":
                radial = rng.uniform(0.8, 5.4)
                heranca = rng.uniform(0.0, 1.2)
                cor = rng.choice([cor_base, cor_clara, (105, 35, 130), (35, 95, 38)])
                forma = "esporo"
                grav = rng.uniform(0.02, 0.10)
            elif tipo == "condutora":
                a = round(a / (math.pi / 4)) * (math.pi / 4)
                cor = rng.choice([cor_base, cor_clara, (80, 170, 255)])
                forma = "bit"
                grav = 0.0
            elif tipo == "gravitante":
                radial = rng.uniform(1.2, 6.0)
                cor = rng.choice([cor_base, cor_clara, (55, 30, 120), cor_escura])
                forma = "orbital"
                grav = -0.015
            elif tipo == "ancorada":
                a = round(a / (math.pi / 2)) * (math.pi / 2) + rng.uniform(-0.14, 0.14)
                radial = rng.uniform(1.4, 6.2)
                cor = rng.choice([cor_base, cor_clara, (120, 145, 190)])
                forma = "runa"
                grav = 0.01
            elif tipo == "retornante":
                radial = rng.uniform(1.8, 7.5)
                cor = rng.choice([cor_base, cor_clara, (255, 75, 210)])
                forma = "eco"
                grav = 0.0

            novas.append({
                "x": cx + rng.uniform(-8, 8),
                "y": cy + rng.uniform(-8, 8),
                "vx": math.cos(a) * radial + dir_x * heranca,
                "vy": math.sin(a) * radial + dir_y * heranca,
                "vida": vida,
                "vida_max": vida,
                "tamanho": rng.uniform(0.8, 2.4 if tipo == "eletrica" else 4.2 if perfil == "alto" else 3.0),
                "cor": cor,
                "tipo": tipo,
                "forma": forma,
                "drag": rng.uniform(0.85, 0.94),
                "grav": grav,
                "rot": rng.uniform(0, 360),
                "vrot": vel_rot
            })

        self.particulas.extend(novas)
        self._limitar_buffers(perfil)

    def atualizar_e_desenhar_particulas(self, tela, dt, config_graficos=None, offset=(0, 0)):
        config_graficos = self._config_efetiva(config_graficos)
        if not (config_graficos or {}).get("particulas_ativas", True):
            self.particulas.clear()
            self.impactos.clear()
            return
        perfil = _perfil_grafico(config_graficos)
        limite = _parametros(perfil)["limite"]
        ox, oy = offset
        novas = []
        passo = max(0.25, min(3.0, float(dt)))
        desenhar_complexo = self._quantidade_frame < 20
        area_visivel = tela.get_rect().inflate(160, 160)
        for idx_part, part in enumerate(self.particulas[-limite:]):
            part["x"] += part["vx"] * passo
            part["y"] += part["vy"] * passo
            part["vx"] *= part["drag"]
            part["vy"] = part["vy"] * part["drag"] + part["grav"] * passo
            part["rot"] += part.get("vrot", 0) * passo
            part["vida"] -= 16.67 * passo
            if part["vida"] <= 0:
                continue

            fator = max(0.0, min(1.0, part["vida"] / max(1, part["vida_max"])))
            alpha = int(255 * fator)
            tamanho = max(0.5, part["tamanho"] * (0.3 + fator * 0.7))

            # Shards ou Additive Points dependendo do tamanho
            forma = part.get("forma", "faisca")
            px_abs = part["x"] + ox
            py_abs = part["y"] + oy
            if not area_visivel.collidepoint(int(px_abs), int(py_abs)):
                novas.append(part)
                continue

            if not desenhar_complexo and idx_part % 2:
                if tamanho >= 1.0:
                    pygame.draw.circle(tela, part["cor"], (int(px_abs), int(py_abs)), 1)
                novas.append(part)
                continue

            if forma == "bit" and tamanho >= 1.2:
                bit = "1" if int(part.get("rot", 0)) % 2 else "0"
                try:
                    tela.blit(_texto_cache(bit, 13, part["cor"]), (int(px_abs), int(py_abs)))
                except Exception:
                    pygame.draw.rect(tela, part["cor"], (int(px_abs), int(py_abs), 3, 3), 1)
            elif forma == "esporo":
                pygame.draw.circle(tela, part["cor"], (int(px_abs), int(py_abs)), max(1, int(tamanho)))
                pygame.draw.circle(tela, (35, 15, 35), (int(px_abs), int(py_abs)), max(1, int(tamanho + 2)), 1)
            elif forma == "runa":
                tam = max(2, int(tamanho * 1.8))
                pygame.draw.line(tela, part["cor"], (int(px_abs - tam), int(py_abs)), (int(px_abs + tam), int(py_abs)), 1)
                pygame.draw.line(tela, part["cor"], (int(px_abs), int(py_abs - tam)), (int(px_abs), int(py_abs + tam)), 1)
            elif forma == "orbital":
                tam = max(3, int(tamanho * 2.2))
                rect_orb = pygame.Rect(int(px_abs - tam), int(py_abs - tam), tam * 2, tam * 2)
                pygame.draw.arc(tela, part["cor"], rect_orb, part["rot"] * 0.04, part["rot"] * 0.04 + math.pi * 1.1, 1)
                pygame.draw.circle(tela, part["cor"], (int(px_abs), int(py_abs)), max(1, int(tamanho * 0.7)))
            elif forma == "eco":
                pygame.draw.circle(tela, part["cor"], (int(px_abs), int(py_abs)), max(2, int(tamanho * 2.2)), 1)
            elif forma == "lasca" and tamanho >= 1.3:
                rad = math.radians(part["rot"])
                ux, uy = math.cos(rad), math.sin(rad)
                vx, vy = -uy, ux
                p1 = (px_abs + ux * tamanho * 2.6, py_abs + uy * tamanho * 2.6)
                p2 = (px_abs - ux * tamanho * 1.2 + vx * tamanho * 0.7, py_abs - uy * tamanho * 1.2 + vy * tamanho * 0.7)
                p3 = (px_abs - ux * tamanho * 1.2 - vx * tamanho * 0.7, py_abs - uy * tamanho * 1.2 - vy * tamanho * 0.7)
                pygame.draw.polygon(tela, part["cor"], [p1, p2, p3])
            elif forma == "raio":
                rad = math.radians(part["rot"])
                ux, uy = math.cos(rad), math.sin(rad)
                tam = max(5, int(tamanho * 5.0))
                meio = (int(px_abs + ux * tam * 0.42 - uy * 3), int(py_abs + uy * tam * 0.42 + ux * 3))
                fim = (int(px_abs + ux * tam), int(py_abs + uy * tam))
                pygame.draw.line(tela, part["cor"], (int(px_abs), int(py_abs)), meio, 2 if alpha > 150 else 1)
                pygame.draw.line(tela, (230, 255, 255), meio, fim, 1)
            elif tamanho < 1.5:
                # Partícula pequena, apenas desenha o ponto aditivo
                surf = _surface_particula(tamanho, part["cor"], alpha)
                tela.blit(surf, (int(part["x"] + ox - surf.get_width()//2), int(part["y"] + oy - surf.get_height()//2)), special_flags=pygame.BLEND_RGB_ADD)
            else:
                # Shard maior: rotaciona vértices de um triângulo/polígono
                rad = math.radians(part["rot"])
                cos_r = math.cos(rad)
                sin_r = math.sin(rad)
                # Shard em formato triangular pontiagudo
                pts = [
                    (0, -tamanho * 1.5),
                    (-tamanho, tamanho),
                    (tamanho, tamanho)
                ]
                rotated = []
                for px, py in pts:
                    rx = part["x"] + ox + (px * cos_r - py * sin_r)
                    ry = part["y"] + oy + (px * sin_r + py * cos_r)
                    rotated.append((rx, ry))

                pygame.draw.polygon(tela, part["cor"], rotated)
                # Adiciona brilho aditivo ao redor do shard
                surf = _surface_particula(tamanho * 1.5, part["cor"], int(alpha * 0.5))
                tela.blit(surf, (int(part["x"] + ox - surf.get_width()//2), int(part["y"] + oy - surf.get_height()//2)), special_flags=pygame.BLEND_RGB_ADD)

            novas.append(part)
        self.particulas = novas
        self._desenhar_impactos_temporarios(tela, pygame.time.get_ticks(), perfil, offset)

    def _desenhar_impactos_temporarios(self, tela, agora_ms, perfil, offset=(0, 0)):
        ox, oy = offset
        vivos = []
        area_visivel = tela.get_rect().inflate(220, 220)
        for idx_impacto, impacto in enumerate(self.impactos):
            idade = int(agora_ms) - int(impacto.get("inicio_ms", agora_ms))
            dur = max(1, int(impacto.get("duracao_ms", 320)))
            if idade >= dur:
                continue
            vivos.append(impacto)
            if self._quantidade_frame >= 32 and idx_impacto % 2 and impacto.get("tipo") != "eletrica":
                continue
            t = max(0.0, min(1.0, idade / float(dur)))
            fade = 1.0 - t
            tipo = impacto.get("tipo", "eletrica")
            cor, clara, escura = _cores_tipo(tipo)
            cx = int(impacto.get("x", 0) + ox)
            cy = int(impacto.get("y", 0) + oy)
            if not area_visivel.collidepoint(cx, cy):
                continue
            raio_base = int(impacto.get("raio", 8))
            angulo = float(impacto.get("angulo", 0.0))
            seed = int(impacto.get("seed", 0))
            rng = random.Random(seed + int(t * 1000))
            alpha = int(230 * fade)

            if tipo == "eletrica":
                raio = int(raio_base * 0.65 + 28 * t)
                pygame.draw.circle(tela, (25, 90, 255), (cx, cy), max(5, raio), 2)
                pygame.draw.circle(tela, clara, (cx, cy), max(2, int(raio_base * 0.45)), 1)
                pygame.draw.circle(tela, (255, 255, 255), (cx, cy), max(1, int(raio_base * 0.18)))
                total = 5 if self._quantidade_frame >= 20 else (8 if perfil == "alto" else 5)
                for k in range(total):
                    a = k * math.tau / total + rng.uniform(-0.32, 0.32)
                    dobra = a + rng.uniform(-0.55, 0.55)
                    inicio = (int(cx + math.cos(a) * raio_base * 0.35), int(cy + math.sin(a) * raio_base * 0.35))
                    meio = (int(cx + math.cos(a) * (raio * 0.72)), int(cy + math.sin(a) * (raio * 0.72)))
                    fim = (int(cx + math.cos(dobra) * (raio + 16 * fade)), int(cy + math.sin(dobra) * (raio + 16 * fade)))
                    pygame.draw.line(tela, (235, 255, 255), inicio, meio, 2 if fade > 0.55 else 1)
                    pygame.draw.line(tela, cor, meio, fim, 1)
                    if perfil == "alto" and k % 2 == 0:
                        ramo = (int(meio[0] + math.cos(dobra + 0.9) * 9 * fade), int(meio[1] + math.sin(dobra + 0.9) * 9 * fade))
                        pygame.draw.line(tela, (90, 210, 255), meio, ramo, 1)
            elif tipo == "lacerante":
                dx, dy = math.cos(angulo), math.sin(angulo)
                nx, ny = -dy, dx
                abertura = 34 + 32 * t
                for sinal in (-1, 1):
                    p1 = (int(cx - dx * abertura + nx * sinal * 6), int(cy - dy * abertura + ny * sinal * 6))
                    p2 = (int(cx + dx * abertura - nx * sinal * 6), int(cy + dy * abertura - ny * sinal * 6))
                    pygame.draw.line(tela, escura, p1, p2, 5)
                    pygame.draw.line(tela, cor, p1, p2, 2)
                pygame.draw.line(tela, clara, (int(cx - nx * 24), int(cy - ny * 24)), (int(cx + nx * 24), int(cy + ny * 24)), 1)
            elif tipo == "prismatica":
                total = 8 if perfil == "alto" else 5
                for k in range(total):
                    a = k * math.tau / total + rng.uniform(-0.12, 0.12)
                    r = 12 + 54 * t + (k % 3) * 5
                    pts = [
                        (cx + math.cos(a) * r, cy + math.sin(a) * r),
                        (cx + math.cos(a + 0.20) * (r + 18 * fade), cy + math.sin(a + 0.20) * (r + 18 * fade)),
                        (cx + math.cos(a - 0.20) * (r + 10 * fade), cy + math.sin(a - 0.20) * (r + 10 * fade)),
                    ]
                    pygame.draw.polygon(tela, [cor, clara, (255, 225, 80), (255, 90, 205)][k % 4], pts, 1)
            elif tipo == "retornante":
                raio = int(raio_base + (48 if impacto.get("retorno") else 28) * t)
                rect = pygame.Rect(cx - raio, cy - raio, raio * 2, raio * 2)
                for k in range(3):
                    pygame.draw.arc(tela, clara if k == 0 else cor, rect.inflate(k * 12, k * 12), -t * math.tau - k, math.pi * 1.5 - t * math.tau, 2 if k == 0 else 1)
                if impacto.get("retorno"):
                    pygame.draw.circle(tela, (255, 75, 210), (cx, cy), max(2, int(raio * fade)), 1)
            elif tipo == "parasitica":
                raio = int(raio_base + 30 * t)
                pygame.draw.circle(tela, (35, 15, 35), (cx, cy), raio + 5, 1)
                for k in range(6):
                    a = k * math.tau / 6 + t * 1.4
                    pygame.draw.line(tela, cor if k % 2 else clara, (cx, cy), (int(cx + math.cos(a) * raio), int(cy + math.sin(a) * raio)), 1)
                pygame.draw.circle(tela, cor, (cx, cy), max(3, int(raio * 0.25)))
            elif tipo == "condutora":
                lado = int(18 + 34 * t)
                pygame.draw.rect(tela, cor, pygame.Rect(cx - lado, cy - lado, lado * 2, lado * 2), 1)
                pygame.draw.line(tela, clara, (cx - lado, cy), (cx + lado, cy), 1)
                pygame.draw.line(tela, clara, (cx, cy - lado), (cx, cy + lado), 1)
                try:
                    tela.blit(_texto_cache("01", 16, clara), (cx - 8, cy - 8))
                except Exception:
                    pass
            elif tipo == "gravitante":
                externo = int(54 * t + raio_base)
                interno = max(3, int(externo * fade * 0.45))
                pygame.draw.circle(tela, escura, (cx, cy), externo, 2)
                pygame.draw.circle(tela, cor, (cx, cy), max(4, externo // 2), 1)
                pygame.draw.circle(tela, clara, (cx, cy), interno, 1)
            elif tipo == "ancorada":
                raio = int(24 + 42 * t)
                pygame.draw.circle(tela, cor, (cx, cy), raio, 2)
                pygame.draw.rect(tela, clara, pygame.Rect(cx - raio, cy - raio, raio * 2, raio * 2), 1)
                for k in range(4):
                    a = math.pi / 4 + k * math.pi / 2
                    pygame.draw.line(tela, cor, (cx, cy), (int(cx + math.cos(a) * raio), int(cy + math.sin(a) * raio)), 1)
        self.impactos = vivos


def estourar_disparo_eletrico(disparos, disparo, vfx, config_graficos=None):
    if disparo not in disparos:
        return
    if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte":
        return
    if isinstance(disparo, dict):
        disparo["_removido_colisao"] = True
    if vfx is not None:
        vfx.criar_impacto(disparo, config_graficos)
    disparos.remove(disparo)
