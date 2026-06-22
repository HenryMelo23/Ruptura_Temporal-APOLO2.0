# -*- coding: utf-8 -*-
import math
import random

import pygame

import lacerante_manifestacao


COR_PRISMA = (70, 245, 255)
COR_PRISMA_QUENTE = (255, 115, 185)
COR_PRISMA_CLARA = (235, 255, 255)
COR_PRISMA_DOURADA = (255, 225, 115)
COR_PRISMA_VIOLETA = (175, 95, 255)
CORES_ESPECTRO = (
    (80, 235, 255),
    (255, 225, 115),
    (255, 115, 185),
    (175, 95, 255),
    (140, 255, 180),
)

FEIXE_DANO_MULT = 0.72
FEIXE_RICOCHETE_MULT = 1.22
FEIXE_CRITICO_MULT = 2.15
FEIXE_VELOCIDADE_MULT = 1.34
FEIXE_RICOCHETES = 1
PRISMA_DURACAO_MS = 6200
PRISMA_TAMANHO = 50
PRISMA_DANO_TOQUE_MULT = 0.75
PRISMA_ABERTURA_RAD = 0.26


def ativa(manifestacao):
    return str(manifestacao or "").strip().lower() == "prismatica"


def _normalizar_angulo(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


def _id_alvo(alvo):
    if isinstance(alvo, dict):
        return alvo.get("prismatica_id", id(alvo))
    if hasattr(alvo, "left"):
        return (int(alvo.left), int(alvo.top), int(alvo.width), int(alvo.height))
    return id(alvo)


def _rect_alvo(alvo):
    if isinstance(alvo, dict):
        return alvo.get("rect")
    return alvo


def _criar_feixe(centro_x, centro_y, largura, altura, angulo, velocidade, tempo_atual, impulsiva=False, fragmento=False):
    largura = max(6, int(largura))
    altura = max(4, int(altura))
    rect = pygame.Rect(int(centro_x - largura // 2), int(centro_y - altura // 2), largura, altura)
    velocidade = float(velocidade) * (0.92 if fragmento else FEIXE_VELOCIDADE_MULT)
    angulo = float(angulo)
    return {
        "tipo_manifestacao": "prismatica_feixe",
        "rect": rect,
        "angulo": angulo,
        "pos_x": float(rect.x),
        "pos_y": float(rect.y),
        "vx": math.cos(angulo) * velocidade,
        "vy": math.sin(angulo) * velocidade,
        "velocidade_prismatica": velocidade,
        "velocidade_base_vfx": velocidade,
        "raio_vfx": max(3, min(8, largura // 2)),
        "nascimento_ms": int(tempo_atual),
        "seed_vfx": random.randint(1000, 999999) + int(tempo_atual),
        "impulsiva_vfx": bool(impulsiva),
        "trail": [],
        "dano_mult_manifestacao": FEIXE_DANO_MULT * (0.56 if fragmento else 1.0),
        "ricochetes_restantes": FEIXE_RICOCHETES,
        "prismatica_ricocheteou": False,
        "prismatica_alvos": [],
        "prismatica_ignorar_alvos": {},
        "prismatica_fragmento": bool(fragmento),
        "prismatica_refracoes": 0,
    }


def criar_auto_attack(manifestacao, vfx, centro_x, centro_y, largura, altura, angulo, velocidade, tempo_atual, impulsiva=False):
    if not ativa(manifestacao):
        return lacerante_manifestacao.criar_auto_attack(
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

    largura_feixe = max(7, int(largura * 0.58))
    altura_feixe = max(5, int(altura * 0.42))
    return _criar_feixe(
        centro_x,
        centro_y,
        largura_feixe,
        altura_feixe,
        angulo,
        velocidade,
        tempo_atual,
        impulsiva,
        False,
    )


def multiplicador_dano_disparo(disparo):
    if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "prismatica_feixe":
        return float(disparo.get("dano_mult_manifestacao", FEIXE_DANO_MULT))
    return 1.0


def _marcar_ricochete(disparo, tempo_atual):
    disparo["ricochetes_restantes"] = max(0, int(disparo.get("ricochetes_restantes", 0)) - 1)
    disparo["prismatica_ricocheteou"] = True
    disparo["ultimo_ricochete_ms"] = int(tempo_atual)
    disparo["dano_mult_manifestacao"] = float(disparo.get("dano_mult_manifestacao", FEIXE_DANO_MULT)) * FEIXE_RICOCHETE_MULT


def atualizar_ricochete(disparo, largura_mapa, altura_mapa, tempo_atual):
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "prismatica_feixe":
        return not disparo.get("expirado")

    rect = disparo["rect"]
    bateu_x = rect.left < 0 or rect.right > largura_mapa
    bateu_y = rect.top < 0 or rect.bottom > altura_mapa
    if not bateu_x and not bateu_y:
        return True

    if int(disparo.get("ricochetes_restantes", 0)) <= 0:
        disparo["expirado"] = True
        return False

    angulo = float(disparo.get("angulo", 0.0))
    if bateu_x:
        angulo = math.pi - angulo
        rect.x = max(0, min(largura_mapa - rect.width, rect.x))
    if bateu_y:
        angulo = -angulo
        rect.y = max(0, min(altura_mapa - rect.height, rect.y))

    disparo["angulo"] = _normalizar_angulo(angulo)
    disparo["pos_x"] = float(rect.x)
    disparo["pos_y"] = float(rect.y)
    _marcar_ricochete(disparo, tempo_atual)
    return True


def ignorar_colisao(disparo, alvo, tempo_atual):
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "prismatica_feixe":
        return False
    ate = disparo.get("prismatica_ignorar_alvos", {}).get(_id_alvo(alvo), 0)
    return int(tempo_atual) < int(ate)


def colisao_feixe(disparo, rect_alvo, tempo_atual):
    if ignorar_colisao(disparo, rect_alvo, tempo_atual):
        return False
    return disparo["rect"].colliderect(rect_alvo)


def registrar_acerto(disparo, alvo, tempo_atual):
    resultado = {"critico": False, "manter_disparo": False}
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "prismatica_feixe":
        return resultado

    alvo_id = _id_alvo(alvo)
    alvos = disparo.setdefault("prismatica_alvos", [])
    ja_acertou = alvo_id in alvos
    resultado["critico"] = bool(ja_acertou and disparo.get("prismatica_ricocheteou"))
    if not ja_acertou:
        alvos.append(alvo_id)

    if int(disparo.get("ricochetes_restantes", 0)) <= 0:
        return resultado

    rect_alvo = _rect_alvo(alvo)
    if rect_alvo is None:
        return resultado

    vx = math.cos(float(disparo.get("angulo", 0.0)))
    vy = math.sin(float(disparo.get("angulo", 0.0)))
    nx = disparo["rect"].centerx - rect_alvo.centerx
    ny = disparo["rect"].centery - rect_alvo.centery
    comprimento = math.hypot(nx, ny)
    if comprimento <= 0.001:
        nx, ny = -vx, -vy
    else:
        nx, ny = nx / comprimento, ny / comprimento
    dot = vx * nx + vy * ny
    novo_vx = vx - 2.0 * dot * nx
    novo_vy = vy - 2.0 * dot * ny
    if math.hypot(novo_vx, novo_vy) <= 0.001:
        novo_vx, novo_vy = -vx, -vy

    disparo["angulo"] = _normalizar_angulo(math.atan2(novo_vy, novo_vx))
    ignorar = disparo.setdefault("prismatica_ignorar_alvos", {})
    ignorar[alvo_id] = int(tempo_atual) + 180
    if rect_alvo is not None:
        ignorar[_id_alvo(rect_alvo)] = int(tempo_atual) + 180
    _marcar_ricochete(disparo, tempo_atual)
    resultado["manter_disparo"] = True
    return resultado


def criar_prisma(x, y, tempo_atual, dano_base, largura_mapa=None, altura_mapa=None):
    metade = PRISMA_TAMANHO // 2
    if largura_mapa is not None:
        x = max(metade, min(int(largura_mapa) - metade, x))
    if altura_mapa is not None:
        y = max(metade, min(int(altura_mapa) - metade, y))
    rect = pygame.Rect(int(x - metade), int(y - metade), PRISMA_TAMANHO, PRISMA_TAMANHO)
    return {
        "tipo_manifestacao": "prisma_refracao",
        "rect": rect,
        "pos_x": float(rect.x),
        "pos_y": float(rect.y),
        "tempo_inicio": int(tempo_atual),
        "fim_ms": int(tempo_atual) + PRISMA_DURACAO_MS,
        "dano_toque": max(1.0, float(dano_base) * PRISMA_DANO_TOQUE_MULT),
        "disparos_divididos": [],
        "seed_vfx": random.randint(1000, 999999) + int(tempo_atual),
    }


def _desenhar_losango(tela, rect, cor, largura=1):
    pontos = [
        (rect.centerx, rect.top),
        (rect.right, rect.centery),
        (rect.centerx, rect.bottom),
        (rect.left, rect.centery),
    ]
    pygame.draw.polygon(tela, cor, pontos, largura)


def desenhar_prisma(tela, prisma, tempo_atual):
    rect = prisma["rect"]
    idade = max(0, int(tempo_atual) - int(prisma.get("tempo_inicio", tempo_atual)))
    pulso = 0.5 + 0.5 * math.sin(idade * 0.007)
    grande = bool(prisma.get("grande_prisma_teleporte"))
    margem = 58 if grande else 42
    surf = pygame.Surface((rect.width + margem * 2, rect.height + margem * 2), pygame.SRCALPHA)
    local = pygame.Rect(margem, margem, rect.width, rect.height)
    centro = local.center
    alpha = int((100 if grande else 84) + 62 * pulso)

    for i, cor in enumerate(CORES_ESPECTRO):
        ang = idade * 0.0024 + i * math.tau / len(CORES_ESPECTRO)
        raio = rect.width * (0.62 + 0.08 * math.sin(idade * 0.004 + i))
        p1 = (int(centro[0] + math.cos(ang) * raio), int(centro[1] + math.sin(ang) * raio))
        p2 = (int(centro[0] - math.cos(ang) * raio * 1.55), int(centro[1] - math.sin(ang) * raio * 1.55))
        pygame.draw.line(surf, (*cor, 42 if grande else 30), p1, p2, 2 if grande else 1)

    _desenhar_losango(surf, local.inflate(34 if grande else 24, 34 if grande else 24), (*COR_PRISMA, 34), 0)
    _desenhar_losango(surf, local.inflate(20 if grande else 12, 20 if grande else 12), (*COR_PRISMA_QUENTE, alpha), 2)
    _desenhar_losango(surf, local.inflate(8 if grande else 0, 8 if grande else 0), (*COR_PRISMA_DOURADA, int(alpha * 0.58)), 1)
    _desenhar_losango(surf, local, (*COR_PRISMA_CLARA, 230), 2)
    pygame.draw.line(surf, (*COR_PRISMA, 170), local.midleft, local.midright, 1)
    pygame.draw.line(surf, (*COR_PRISMA_QUENTE, 160), local.midtop, local.midbottom, 1)
    pygame.draw.line(surf, (*COR_PRISMA_VIOLETA, 145), local.topleft, local.bottomright, 1)
    pygame.draw.line(surf, (*COR_PRISMA_DOURADA, 135), local.topright, local.bottomleft, 1)

    for i in range(3 if grande else 2):
        raio = int(local.w * (0.85 + i * 0.28 + pulso * 0.08))
        pygame.draw.circle(surf, (*CORES_ESPECTRO[i], 26), centro, raio, 1)

    tela.blit(surf, (rect.x - margem, rect.y - margem), special_flags=pygame.BLEND_RGBA_ADD)


def desenhar_feixe(tela, disparo, tempo_atual, offset=(0, 0)):
    ox, oy = offset
    cx = disparo["rect"].centerx + ox
    cy = disparo["rect"].centery + oy
    angulo = float(disparo.get("angulo", 0.0))
    dx = math.cos(angulo)
    dy = math.sin(angulo)
    comprimento = 34 if disparo.get("prismatica_fragmento") else 48
    ponta = (int(cx + dx * comprimento * 0.45), int(cy + dy * comprimento * 0.45))
    cauda = (int(cx - dx * comprimento), int(cy - dy * comprimento))

    trail = disparo.get("trail", [])
    for idx, ponto in enumerate(reversed(trail[-5:])):
        fade = 1.0 - idx / 5.0
        px, py = ponto
        cor = CORES_ESPECTRO[idx % len(CORES_ESPECTRO)]
        pygame.draw.circle(tela, (*cor, 180), (int(px + ox), int(py + oy)), max(1, int(4 * fade)))

    largura = 2 if disparo.get("prismatica_fragmento") else 3
    lado = (-dy, dx)
    # Antes cada feixe alocava uma superficie alpha do tamanho da tela.
    # Esta superficie local preserva o efeito sem o custo por projetil.
    margem = 18
    origem_x = min(cauda[0], ponta[0]) - margem
    origem_y = min(cauda[1], ponta[1]) - margem
    largura_surf = max(1, abs(ponta[0] - cauda[0]) + margem * 2)
    altura_surf = max(1, abs(ponta[1] - cauda[1]) + margem * 2)
    surf = pygame.Surface((largura_surf, altura_surf), pygame.SRCALPHA)

    def local(ponto):
        return int(ponto[0] - origem_x), int(ponto[1] - origem_y)

    for desloc, cor, alpha in (
        (-5, COR_PRISMA_QUENTE, 80),
        (5, COR_PRISMA_DOURADA, 78),
        (-9, COR_PRISMA_VIOLETA, 44),
        (9, (120, 255, 180), 42),
    ):
        pygame.draw.line(
            surf,
            (*cor, alpha),
            local((cauda[0] + lado[0] * desloc, cauda[1] + lado[1] * desloc)),
            local((ponta[0] + lado[0] * desloc * 0.25, ponta[1] + lado[1] * desloc * 0.25)),
            1,
        )
    pygame.draw.line(surf, (35, 110, 180, 135), local(cauda), local(ponta), largura + 6)
    pygame.draw.line(surf, (*COR_PRISMA, 230), local(cauda), local(ponta), largura + 1)
    pygame.draw.line(surf, (*COR_PRISMA_CLARA, 255), local((cx - dx * 10, cy - dy * 10)), local(ponta), 1)
    tela.blit(surf, (origem_x, origem_y), special_flags=pygame.BLEND_RGBA_ADD)
    if disparo.get("prismatica_ricocheteou"):
        pygame.draw.line(
            tela,
            COR_PRISMA_QUENTE,
            (int(cx - lado[0] * 7), int(cy - lado[1] * 7)),
            (int(cx + lado[0] * 7), int(cy + lado[1] * 7)),
            1,
        )


def _dividir_disparo(prisma, disparo, disparos, tempo_atual):
    chave = id(disparo)
    if chave in prisma.setdefault("disparos_divididos", []):
        return
    prisma["disparos_divididos"].append(chave)
    if disparo.get("tipo_manifestacao") == "lacerante_corte":
        return
    refracoes = int(disparo.get("prismatica_refracoes", 0))
    pode_refratar_fragmento = bool(prisma.get("grande_prisma_teleporte")) and refracoes < 2
    if disparo.get("prismatica_fragmento") and not pode_refratar_fragmento:
        return

    centro_x, centro_y = disparo["rect"].center
    largura = max(5, int(disparo["rect"].width * 0.62))
    altura = max(4, int(disparo["rect"].height * 0.62))
    velocidade = float(disparo.get("velocidade_prismatica", disparo.get("velocidade_base_vfx", 14.0)))
    base = float(disparo.get("angulo", 0.0))
    abertura = PRISMA_ABERTURA_RAD * (0.72 if pode_refratar_fragmento else 1.0)
    novos = [
        _criar_feixe(centro_x, centro_y, largura, altura, base - abertura, velocidade, tempo_atual, False, True),
        _criar_feixe(centro_x, centro_y, largura, altura, base, velocidade, tempo_atual, False, True),
        _criar_feixe(centro_x, centro_y, largura, altura, base + abertura, velocidade, tempo_atual, False, True),
    ]
    for novo in novos:
        novo["prismatica_refracoes"] = refracoes + 1
        if pode_refratar_fragmento:
            novo["dano_mult_manifestacao"] = float(novo.get("dano_mult_manifestacao", FEIXE_DANO_MULT)) * 0.72
        for chave in ("eco_insana", "insana_vfx", "dano_mult", "voraz_aurea", "voraz_dano_mult"):
            if chave in disparo:
                novo[chave] = disparo[chave]
    if disparo in disparos:
        disparos.remove(disparo)
    disparos.extend(novos)


def processar_prisma(prisma, disparos, inimigos_comum, boss_info, tela, tempo_atual):
    desenhar_prisma(tela, prisma, tempo_atual)
    if int(tempo_atual) >= int(prisma.get("fim_ms", 0)):
        return False, []

    for disparo in list(disparos or []):
        if isinstance(disparo, dict) and disparo.get("rect") and disparo["rect"].colliderect(prisma["rect"]):
            _dividir_disparo(prisma, disparo, disparos, tempo_atual)

    mortos = []
    for inimigo in list(inimigos_comum or []):
        rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
        if rect is not None and prisma["rect"].colliderect(rect):
            inimigo["vida"] -= float(prisma.get("dano_toque", 1.0))
            if inimigo.get("vida", 1) <= 0:
                mortos.append(inimigo)
            return False, mortos

    if boss_info and boss_info.get("vivo") and boss_info.get("rect") and prisma["rect"].colliderect(boss_info["rect"]):
        if int(tempo_atual) - int(boss_info.get("atingido_por_onda", 0)) >= 500:
            boss_info["atingido_por_onda"] = int(tempo_atual)
            boss_info["hit_flag"] = True
            boss_info["dano_manifestacao"] = float(prisma.get("dano_toque", 1.0))
        return False, mortos

    return True, mortos
