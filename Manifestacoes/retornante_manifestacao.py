# -*- coding: utf-8 -*-
import math
import random

import pygame

import prismatica_manifestacao


COR_RETORNO = (145, 95, 255)
COR_RETORNO_CLARA = (235, 225, 255)
COR_RETORNO_FORCADO = (255, 95, 175)

PULSO_DANO_IDA_MULT = 0.44
PULSO_DANO_VOLTA_MULT = 1.58
PULSO_RETORNO_FORCADO_MULT = 1.28
PULSO_CRITICO_COSTAS_MULT = 1.85
PULSO_ALCANCE = 360
PULSO_VELOCIDADE_IDA_MULT = 0.94
PULSO_VELOCIDADE_VOLTA_MULT = 1.18
CHAMADO_DURACAO_MS = 360
MARCA_RETORNANTE_MS = 780


def _perfil_efeito(config_graficos=None):
    cfg = config_graficos or {}
    if cfg and not cfg.get("efeitos_visuais", True):
        return "desativado"
    perfil = str(cfg.get("efeitos_manifestacoes", "")).lower()
    if perfil in ("alto", "medio", "baixo", "desativado"):
        return perfil
    if cfg and not cfg.get("particulas_ativas", True):
        return "baixo"
    nivel = str(cfg.get("nivel_detalhes", cfg.get("qualidade_grafica", "alto"))).lower()
    if nivel in ("baixo", "baixa"):
        return "baixo"
    if nivel in ("medio", "media"):
        return "medio"
    return "alto"


def ativa(manifestacao):
    return str(manifestacao or "").strip().lower() == "retornante"


def _normalizar(vx, vy):
    comp = math.hypot(vx, vy)
    if comp <= 0.001:
        return 1.0, 0.0
    return vx / comp, vy / comp


def _id_alvo(alvo):
    if isinstance(alvo, dict):
        return alvo.get("retornante_id", id(alvo))
    if hasattr(alvo, "left"):
        return (int(alvo.left), int(alvo.top), int(alvo.width), int(alvo.height))
    return id(alvo)


def _rect_alvo(alvo):
    if isinstance(alvo, dict):
        return alvo.get("rect")
    return alvo


def _fase(disparo):
    return str(disparo.get("retornante_fase", "ida"))


def criar_auto_attack(manifestacao, vfx, centro_x, centro_y, largura, altura, angulo, velocidade, tempo_atual, impulsiva=False):
    if not ativa(manifestacao):
        return prismatica_manifestacao.criar_auto_attack(
            manifestacao,
            vfx,
            centro_x,
            centro_y,
            largura,
            altura,
            angulo,
            velocidade,
            tempo_atual,
            impulsiva,
        )

    largura = max(12, int(largura * 0.86))
    altura = max(12, int(altura * 0.86))
    rect = pygame.Rect(int(centro_x - largura // 2), int(centro_y - altura // 2), largura, altura)
    angulo = float(angulo)
    velocidade = float(velocidade)
    return {
        "tipo_manifestacao": "retornante_pulso",
        "rect": rect,
        "angulo": angulo,
        "pos_x": float(rect.x),
        "pos_y": float(rect.y),
        "origem_x": float(centro_x),
        "origem_y": float(centro_y),
        "vx": math.cos(angulo) * velocidade * PULSO_VELOCIDADE_IDA_MULT,
        "vy": math.sin(angulo) * velocidade * PULSO_VELOCIDADE_IDA_MULT,
        "velocidade_retornante": velocidade,
        "velocidade_base_vfx": velocidade,
        "raio_vfx": max(5, min(12, largura // 2)),
        "nascimento_ms": int(tempo_atual),
        "seed_vfx": random.randint(1000, 999999) + int(tempo_atual),
        "impulsiva_vfx": bool(impulsiva),
        "trail": [],
        "retornante_fase": "ida",
        "retornante_hits_ida": [],
        "retornante_hits_volta": [],
        "retornante_forcado": False,
        "retornante_chamado_ms": 0,
        "distancia_ida": 0.0,
        "alcance_retornante": PULSO_ALCANCE,
    }


def forcar_retorno(disparo, tempo_atual):
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "retornante_pulso":
        return False
    if disparo.get("expirado"):
        return False
    disparo["retornante_fase"] = "volta"
    disparo["retornante_forcado"] = True
    disparo["retornante_chamado_ms"] = int(tempo_atual)
    disparo["retornante_marca_ms"] = int(tempo_atual)
    return True


def chamado_reverso(disparos, tempo_atual):
    total = 0
    for disparo in list(disparos or []):
        if forcar_retorno(disparo, tempo_atual):
            total += 1
    return total


def criar_chamado(x, y, tempo_atual, total=0):
    rect = pygame.Rect(int(x - 42), int(y - 42), 84, 84)
    return {
        "tipo_manifestacao": "chamado_reverso",
        "rect": rect,
        "tempo_inicio": int(tempo_atual),
        "fim_ms": int(tempo_atual) + CHAMADO_DURACAO_MS,
        "total": int(total),
    }


def desenhar_chamado(tela, chamado, tempo_atual, config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        return
    inicio = int(chamado.get("tempo_inicio", tempo_atual))
    progresso = max(0.0, min(1.0, (int(tempo_atual) - inicio) / float(CHAMADO_DURACAO_MS)))
    alpha = int(180 * (1.0 - progresso))
    raio = int(18 + 72 * progresso)
    if perfil == "baixo":
        alpha = int(alpha * 0.55)
        raio = int(14 + 44 * progresso)
    elif perfil == "medio":
        alpha = int(alpha * 0.78)
        raio = int(16 + 58 * progresso)
    surf = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
    centro = raio + 4
    pygame.draw.circle(surf, (*COR_RETORNO_FORCADO, max(20, alpha // 3)), (centro, centro), raio, 2)
    pygame.draw.circle(surf, (*COR_RETORNO_CLARA, max(20, alpha)), (centro, centro), max(6, int(raio * 0.35)), 1)
    tela.blit(surf, (chamado["rect"].centerx - centro, chamado["rect"].centery - centro))


def atualizar_disparo(disparo, player_x, player_y, dt, tempo_atual):
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "retornante_pulso":
        return not disparo.get("expirado")

    rect = disparo["rect"]
    velocidade_base = float(disparo.get("velocidade_retornante", disparo.get("velocidade_base_vfx", 10.0)))
    passo = max(0.0, float(dt))

    if _fase(disparo) == "ida":
        vx = math.cos(float(disparo.get("angulo", 0.0))) * velocidade_base * PULSO_VELOCIDADE_IDA_MULT
        vy = math.sin(float(disparo.get("angulo", 0.0))) * velocidade_base * PULSO_VELOCIDADE_IDA_MULT
        disparo["distancia_ida"] = float(disparo.get("distancia_ida", 0.0)) + math.hypot(vx * passo, vy * passo)
        if disparo["distancia_ida"] >= float(disparo.get("alcance_retornante", PULSO_ALCANCE)):
            disparo["retornante_fase"] = "volta"
    else:
        cx, cy = rect.center
        dx, dy = float(player_x) - cx, float(player_y) - cy
        dist_player = math.hypot(dx, dy)
        if dist_player <= max(20, rect.width + 8):
            disparo["expirado"] = True
            return False
        nx, ny = _normalizar(dx, dy)
        vx = nx * velocidade_base * PULSO_VELOCIDADE_VOLTA_MULT
        vy = ny * velocidade_base * PULSO_VELOCIDADE_VOLTA_MULT
        disparo["angulo"] = math.atan2(vy, vx)

    disparo["vx"] = vx
    disparo["vy"] = vy
    disparo["velocidade_base_vfx"] = math.hypot(vx, vy)
    disparo["pos_x"] = float(disparo.get("pos_x", rect.x)) + vx * passo
    disparo["pos_y"] = float(disparo.get("pos_y", rect.y)) + vy * passo
    rect.x = int(disparo["pos_x"])
    rect.y = int(disparo["pos_y"])

    trail = disparo.setdefault("trail", [])
    trail.append(rect.center)
    if len(trail) > 12:
        del trail[:-12]
    return True


def colisao_pulso(disparo, rect_alvo):
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "retornante_pulso":
        return False
    if disparo.get("expirado"):
        return False
    alvo_id = _id_alvo(rect_alvo)
    lista = disparo.setdefault("retornante_hits_volta" if _fase(disparo) == "volta" else "retornante_hits_ida", [])
    if alvo_id in lista:
        return False
    return disparo["rect"].colliderect(rect_alvo)


def colisao_alvo(disparo, alvo):
    rect_alvo = _rect_alvo(alvo)
    if rect_alvo is None:
        return False
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "retornante_pulso":
        return False
    if disparo.get("expirado"):
        return False
    alvo_id = _id_alvo(alvo)
    lista = disparo.setdefault("retornante_hits_volta" if _fase(disparo) == "volta" else "retornante_hits_ida", [])
    if alvo_id in lista:
        return False
    return disparo["rect"].colliderect(rect_alvo)


def registrar_acerto(disparo, alvo, tempo_atual, player_center=None):
    resultado = {"critico": False, "manter_disparo": False, "volta": False}
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "retornante_pulso":
        return resultado

    fase = _fase(disparo)
    lista = disparo.setdefault("retornante_hits_volta" if fase == "volta" else "retornante_hits_ida", [])
    alvo_id = _id_alvo(alvo)
    if alvo_id not in lista:
        lista.append(alvo_id)
    rect_alvo = _rect_alvo(alvo)
    if rect_alvo is not None:
        rect_id = _id_alvo(rect_alvo)
        if rect_id not in lista:
            lista.append(rect_id)

    resultado["manter_disparo"] = True
    resultado["volta"] = fase == "volta"
    if fase == "volta" and isinstance(alvo, dict):
        alvo["retornante_bonus_ate"] = max(int(alvo.get("retornante_bonus_ate", 0)), int(tempo_atual) + 900)
        if "stun_fim" in alvo:
            alvo["stun_fim"] = max(int(alvo.get("stun_fim", 0)), int(tempo_atual) + 220)

    if fase == "volta" and rect_alvo is not None and player_center is not None:
        px, py = player_center
        proj_dist = math.hypot(disparo["rect"].centerx - px, disparo["rect"].centery - py)
        alvo_dist = math.hypot(rect_alvo.centerx - px, rect_alvo.centery - py)
        vx1, vy1 = _normalizar(px - disparo["rect"].centerx, py - disparo["rect"].centery)
        vx2, vy2 = _normalizar(px - rect_alvo.centerx, py - rect_alvo.centery)
        resultado["critico"] = proj_dist > alvo_dist + rect_alvo.width * 0.35 and (vx1 * vx2 + vy1 * vy2) > 0.82
    return resultado


def multiplicador_dano_disparo(disparo):
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "retornante_pulso":
        return 1.0
    mult = PULSO_DANO_VOLTA_MULT if _fase(disparo) == "volta" else PULSO_DANO_IDA_MULT
    if disparo.get("retornante_forcado") and _fase(disparo) == "volta":
        mult *= PULSO_RETORNO_FORCADO_MULT
    return mult


def desenhar_pulso(tela, disparo, tempo_atual, offset=(0, 0), config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        return
    ox, oy = offset
    cx = disparo["rect"].centerx + ox
    cy = disparo["rect"].centery + oy
    voltando = _fase(disparo) == "volta"
    cor_base = COR_RETORNO_FORCADO if disparo.get("retornante_forcado") and voltando else COR_RETORNO
    cor_core = COR_RETORNO_CLARA if voltando else (205, 195, 255)

    trail = disparo.get("trail", [])
    rastro = 8 if perfil == "alto" else (5 if perfil == "medio" else 3)
    for idx, (tx, ty) in enumerate(reversed(trail[-rastro:])):
        fade = 1.0 - idx / max(1, rastro)
        raio = max(2, int(disparo.get("raio_vfx", 8) * (0.35 + 0.45 * fade)))
        pygame.draw.circle(tela, (*cor_base[:3],), (int(tx + ox), int(ty + oy)), raio, 1)

    raio = int(disparo.get("raio_vfx", 8))
    pygame.draw.circle(tela, (55, 35, 105), (int(cx), int(cy)), raio + 5)
    pygame.draw.circle(tela, cor_base, (int(cx), int(cy)), raio + (3 if voltando else 1), 2)
    pygame.draw.circle(tela, cor_core, (int(cx), int(cy)), max(3, raio // 2))
    marca_ms = int(disparo.get("retornante_marca_ms", 0))
    if marca_ms and tempo_atual - marca_ms < MARCA_RETORNANTE_MS:
        t = max(0.0, min(1.0, (tempo_atual - marca_ms) / float(MARCA_RETORNANTE_MS)))
        alpha = int(230 * (1.0 - t))
        giro = tempo_atual * 0.01 + disparo.get("seed_vfx", 0) * 0.001
        marca_raio = raio + 12 + int(8 * math.sin(tempo_atual * 0.02))
        pontas = 6 if perfil == "alto" else (4 if perfil == "medio" else 3)
        for i in range(pontas):
            a = giro + math.tau * i / pontas
            px = cx + math.cos(a) * marca_raio
            py = cy + math.sin(a) * marca_raio
            qx = cx + math.cos(a + 0.36) * (marca_raio + 7)
            qy = cy + math.sin(a + 0.36) * (marca_raio + 7)
            pygame.draw.line(tela, COR_RETORNO_FORCADO, (int(px), int(py)), (int(qx), int(qy)), 2 if perfil != "baixo" else 1)
        pygame.draw.circle(tela, COR_RETORNO_FORCADO, (int(cx), int(cy)), marca_raio, 1)
    if voltando:
        ang = float(disparo.get("angulo", 0.0))
        dx, dy = math.cos(ang), math.sin(ang)
        pygame.draw.line(
            tela,
            cor_core,
            (int(cx - dx * 24), int(cy - dy * 24)),
            (int(cx + dx * 12), int(cy + dy * 12)),
            2,
        )
