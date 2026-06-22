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
MEMORIA_INSTAVEL_DURACAO_MS = 4000
MEMORIA_INSTAVEL_DANO_MULT = 0.32
MEMORIA_INSTAVEL_INTERVALO_ALVO_MS = 400
MEMORIA_INSTAVEL_INTERVALO_GLOBAL_MS = 90
MEMORIA_INSTAVEL_ESCALA = 0.80
MEMORIA_INSTAVEL_RAIO_BUSCA = 520
MEMORIA_RETORNO_BONUS_MEDIO = 1.15
MEMORIA_RETORNO_BONUS_ALTO = 1.25

_MEMORIA_PENDENTE = False


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
    global _MEMORIA_PENDENTE
    if not ativa(manifestacao):
        _MEMORIA_PENDENTE = False
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
    disparo = {
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
    if _MEMORIA_PENDENTE:
        _MEMORIA_PENDENTE = False
        _tornar_instavel(disparo, tempo_atual)
    return disparo


def _redimensionar_pulso(disparo, escala):
    rect = disparo["rect"]
    base_largura = int(disparo.setdefault("retornante_largura_original", rect.width))
    base_altura = int(disparo.setdefault("retornante_altura_original", rect.height))
    centro = rect.center
    rect.size = (max(8, int(base_largura * escala)), max(8, int(base_altura * escala)))
    rect.center = centro
    disparo["pos_x"] = float(rect.x)
    disparo["pos_y"] = float(rect.y)
    disparo["raio_vfx"] = max(4, min(15, rect.width // 2))


def _tornar_instavel(disparo, tempo_atual):
    if disparo.get("expirado") or disparo.get("retornante_fase") == "instavel":
        return False
    disparo["retornante_fase"] = "instavel"
    disparo["memoria_instavel_inicio_ms"] = int(tempo_atual)
    disparo["memoria_instavel_fim_ms"] = int(tempo_atual) + MEMORIA_INSTAVEL_DURACAO_MS
    disparo["memoria_instavel_impactos"] = 0
    disparo["memoria_instavel_hits_ms"] = {}
    disparo["memoria_instavel_ultimo_hit_ms"] = -999999
    disparo["memoria_instavel_ultimo_alvo"] = None
    disparo["memoria_instavel_buscar_alvo"] = False
    disparo["retornante_forcado"] = False
    disparo["retornante_marca_ms"] = int(tempo_atual)
    _redimensionar_pulso(disparo, MEMORIA_INSTAVEL_ESCALA)
    return True


def ativar_memoria_instavel(disparos, tempo_atual, cursor=None):
    """Instabiliza um unico pulso ou reserva o efeito para o proximo disparo."""
    global _MEMORIA_PENDENTE
    candidatos = [
        d for d in list(disparos or [])
        if isinstance(d, dict)
        and d.get("tipo_manifestacao") == "retornante_pulso"
        and not d.get("expirado")
        and d.get("retornante_fase") != "instavel"
    ]
    if not candidatos:
        _MEMORIA_PENDENTE = True
        return {"ativado": False, "reservado": True, "centro": cursor}

    if cursor is not None:
        mx, my = cursor
        escolhido = min(candidatos, key=lambda d: (d["rect"].centerx - mx) ** 2 + (d["rect"].centery - my) ** 2)
    else:
        escolhido = min(candidatos, key=lambda d: int(d.get("nascimento_ms", tempo_atual)))
    _MEMORIA_PENDENTE = False
    _tornar_instavel(escolhido, tempo_atual)
    return {"ativado": True, "reservado": False, "centro": escolhido["rect"].center}


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


def chamado_reverso(disparos, tempo_atual, cursor=None):
    """Compatibilidade: o antigo chamado agora ativa uma Memoria Instavel."""
    resultado = ativar_memoria_instavel(disparos, tempo_atual, cursor)
    return 1 if resultado["ativado"] else 0


def criar_chamado(x, y, tempo_atual, total=0):
    rect = pygame.Rect(int(x - 42), int(y - 42), 84, 84)
    return {
        "tipo_manifestacao": "memoria_instavel_ativacao",
        "rect": rect,
        "tempo_inicio": int(tempo_atual),
        "fim_ms": int(tempo_atual) + CHAMADO_DURACAO_MS,
        "total": int(total),
        "reservado": int(total) <= 0,
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
    reservado = bool(chamado.get("reservado"))
    cor = COR_RETORNO if reservado else COR_RETORNO_FORCADO
    pygame.draw.circle(surf, (*cor, max(20, alpha // 3)), (centro, centro), raio, 2)
    pygame.draw.circle(surf, (*COR_RETORNO_CLARA, max(20, alpha)), (centro, centro), max(6, int(raio * 0.35)), 1)
    pontas = 4 if perfil == "baixo" else 7
    giro = tempo_atual * (0.008 if reservado else -0.014)
    for indice in range(pontas):
        angulo = giro + math.tau * indice / pontas
        interno = raio * 0.42
        externo = raio * (0.78 + 0.12 * math.sin(giro * 2 + indice))
        pygame.draw.line(
            surf, (*cor, max(18, alpha // 2)),
            (int(centro + math.cos(angulo) * interno), int(centro + math.sin(angulo) * interno)),
            (int(centro + math.cos(angulo + 0.24) * externo), int(centro + math.sin(angulo + 0.24) * externo)),
            1,
        )
    tela.blit(surf, (chamado["rect"].centerx - centro, chamado["rect"].centery - centro))


def _finalizar_instabilidade(disparo, tempo_atual):
    impactos = int(disparo.get("memoria_instavel_impactos", 0))
    bonus = MEMORIA_RETORNO_BONUS_ALTO if impactos >= 6 else (MEMORIA_RETORNO_BONUS_MEDIO if impactos >= 3 else 1.0)
    disparo["retornante_fase"] = "volta"
    disparo["memoria_retorno_bonus"] = bonus
    disparo["memoria_retorno_impactos"] = impactos
    disparo["retornante_marca_ms"] = int(tempo_atual)
    _redimensionar_pulso(disparo, 1.22 if impactos >= 6 else 1.0)


def _direcionar_ricochete(disparo, alvos):
    rect = disparo["rect"]
    ultimo = disparo.get("memoria_instavel_ultimo_alvo")
    candidatos = []
    for alvo in list(alvos or []):
        alvo_rect = _rect_alvo(alvo)
        if alvo_rect is None or (isinstance(alvo, dict) and (alvo.get("invisivel") or alvo.get("vida", 1) <= 0)):
            continue
        if _id_alvo(alvo) == ultimo:
            continue
        distancia = math.hypot(alvo_rect.centerx - rect.centerx, alvo_rect.centery - rect.centery)
        if distancia <= MEMORIA_INSTAVEL_RAIO_BUSCA:
            candidatos.append((distancia, alvo_rect))
    if candidatos:
        _, alvo_rect = min(candidatos, key=lambda item: item[0])
        disparo["angulo"] = math.atan2(alvo_rect.centery - rect.centery, alvo_rect.centerx - rect.centerx)
    else:
        # Sem outro corpo valido, rebate para longe e deixa os limites da arena
        # manterem o pulso vivo ate surgir uma nova oportunidade.
        disparo["angulo"] = float(disparo.get("angulo", 0.0)) + math.pi + 0.19
    disparo["memoria_instavel_buscar_alvo"] = False


def atualizar_disparo(disparo, player_x, player_y, dt, tempo_atual, alvos=None, largura_mapa=None, altura_mapa=None):
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "retornante_pulso":
        return not disparo.get("expirado")

    rect = disparo["rect"]
    velocidade_base = float(disparo.get("velocidade_retornante", disparo.get("velocidade_base_vfx", 10.0)))
    passo = max(0.0, float(dt))

    fase = _fase(disparo)
    if fase == "instavel":
        if int(tempo_atual) >= int(disparo.get("memoria_instavel_fim_ms", tempo_atual)):
            _finalizar_instabilidade(disparo, tempo_atual)
            fase = "volta"
        else:
            if disparo.get("memoria_instavel_buscar_alvo"):
                _direcionar_ricochete(disparo, alvos)
            angulo = float(disparo.get("angulo", 0.0))
            vx = math.cos(angulo) * velocidade_base
            vy = math.sin(angulo) * velocidade_base
            proximo_x = float(disparo.get("pos_x", rect.x)) + vx * passo
            proximo_y = float(disparo.get("pos_y", rect.y)) + vy * passo
            bateu = False
            if largura_mapa is not None:
                limite_x = max(0.0, float(largura_mapa - rect.width))
                if proximo_x <= 0.0 or proximo_x >= limite_x:
                    vx = -vx
                    proximo_x = max(0.0, min(limite_x, proximo_x))
                    bateu = True
            if altura_mapa is not None:
                limite_y = max(0.0, float(altura_mapa - rect.height))
                if proximo_y <= 0.0 or proximo_y >= limite_y:
                    vy = -vy
                    proximo_y = max(0.0, min(limite_y, proximo_y))
                    bateu = True
            if bateu:
                disparo["angulo"] = math.atan2(vy, vx)
                disparo["memoria_instavel_ultimo_alvo"] = None
                disparo["memoria_instavel_buscar_alvo"] = True
            disparo["vx"], disparo["vy"] = vx, vy
            disparo["pos_x"], disparo["pos_y"] = proximo_x, proximo_y
            rect.x, rect.y = int(proximo_x), int(proximo_y)

            trail = disparo.setdefault("trail", [])
            trail.append(rect.center)
            if len(trail) > 16:
                del trail[:-16]
            return True

    if fase == "ida":
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
    if _fase(disparo) == "instavel":
        agora = pygame.time.get_ticks()
        hits = disparo.setdefault("memoria_instavel_hits_ms", {})
        if agora - int(hits.get(alvo_id, -999999)) < MEMORIA_INSTAVEL_INTERVALO_ALVO_MS:
            return False
        if agora - int(disparo.get("memoria_instavel_ultimo_hit_ms", -999999)) < MEMORIA_INSTAVEL_INTERVALO_GLOBAL_MS:
            return False
        return disparo["rect"].colliderect(rect_alvo)
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
    if _fase(disparo) == "instavel":
        agora = pygame.time.get_ticks()
        hits = disparo.setdefault("memoria_instavel_hits_ms", {})
        if agora - int(hits.get(alvo_id, -999999)) < MEMORIA_INSTAVEL_INTERVALO_ALVO_MS:
            return False
        if agora - int(disparo.get("memoria_instavel_ultimo_hit_ms", -999999)) < MEMORIA_INSTAVEL_INTERVALO_GLOBAL_MS:
            return False
        return disparo["rect"].colliderect(rect_alvo)
    lista = disparo.setdefault("retornante_hits_volta" if _fase(disparo) == "volta" else "retornante_hits_ida", [])
    if alvo_id in lista:
        return False
    return disparo["rect"].colliderect(rect_alvo)


def registrar_acerto(disparo, alvo, tempo_atual, player_center=None):
    resultado = {"critico": False, "manter_disparo": False, "volta": False}
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "retornante_pulso":
        return resultado

    fase = _fase(disparo)
    alvo_id = _id_alvo(alvo)
    if fase == "instavel":
        hits = disparo.setdefault("memoria_instavel_hits_ms", {})
        hits[alvo_id] = int(tempo_atual)
        disparo["memoria_instavel_ultimo_hit_ms"] = int(tempo_atual)
        disparo["memoria_instavel_ultimo_alvo"] = alvo_id
        disparo["memoria_instavel_impactos"] = int(disparo.get("memoria_instavel_impactos", 0)) + 1
        disparo["memoria_instavel_buscar_alvo"] = True
        resultado["manter_disparo"] = True
        return resultado

    lista = disparo.setdefault("retornante_hits_volta" if fase == "volta" else "retornante_hits_ida", [])
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
    fase = _fase(disparo)
    if fase == "instavel":
        return MEMORIA_INSTAVEL_DANO_MULT
    mult = PULSO_DANO_VOLTA_MULT if fase == "volta" else PULSO_DANO_IDA_MULT
    if fase == "volta":
        mult *= float(disparo.get("memoria_retorno_bonus", 1.0))
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
    fase = _fase(disparo)
    voltando = fase == "volta"
    instavel = fase == "instavel"
    cor_base = (255, 70, 205) if instavel else (COR_RETORNO_FORCADO if (disparo.get("retornante_forcado") or disparo.get("memoria_retorno_bonus", 1.0) > 1.0) and voltando else COR_RETORNO)
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
    if instavel:
        restante = max(0, int(disparo.get("memoria_instavel_fim_ms", tempo_atual)) - int(tempo_atual))
        pulso = 0.5 + 0.5 * math.sin(tempo_atual * 0.045)
        giro = tempo_atual * 0.018 + disparo.get("seed_vfx", 0) * 0.001
        pontas = 5 if perfil == "baixo" else (7 if perfil == "medio" else 10)
        for indice in range(pontas):
            angulo_fragmento = giro + math.tau * indice / pontas
            distancia = raio + 7 + (indice % 3) * 3 + pulso * 4
            px = cx + math.cos(angulo_fragmento) * distancia
            py = cy + math.sin(angulo_fragmento) * distancia
            tangente = angulo_fragmento + math.pi / 2
            pygame.draw.line(
                tela,
                (100, 235, 255) if indice % 2 else COR_RETORNO_FORCADO,
                (int(px - math.cos(tangente) * 3), int(py - math.sin(tangente) * 3)),
                (int(px + math.cos(tangente) * 5), int(py + math.sin(tangente) * 5)),
                2 if perfil == "alto" else 1,
            )
        proporcao = restante / float(MEMORIA_INSTAVEL_DURACAO_MS)
        pygame.draw.arc(
            tela, COR_RETORNO_CLARA,
            pygame.Rect(int(cx - raio - 10), int(cy - raio - 10), (raio + 10) * 2, (raio + 10) * 2),
            -math.pi / 2, -math.pi / 2 + math.tau * proporcao, 2,
        )
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
