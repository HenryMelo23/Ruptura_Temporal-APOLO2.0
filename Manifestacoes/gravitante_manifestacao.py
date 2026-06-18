# -*- coding: utf-8 -*-
import math
import random

import pygame

import condutora_manifestacao


COR_GRAVITANTE = (118, 190, 255)
COR_GRAVITANTE_CLARA = (218, 245, 255)
COR_GRAVITANTE_NUCLEO = (88, 82, 210)
COR_GRAVITANTE_ESCURA = (18, 24, 74)

GRAVITANTE_DANO_REFERENCIA_INICIAL = 35.0
ORBE_DANO_IMPACTO_MULT = 0.30
ORBE_VELOCIDADE_MULT = 0.94
ORBE_DURACAO_MS = 3400
ORBE_TICK_MS = 680
ORBE_TICK_MULT = 0.14
ORBE_EXPLOSAO_MULT = 0.90
ORBE_RAIO_EXPLOSAO = 96
ORBE_RAIO_MIGRACAO = 160
ORBE_DANO_INICIAL_MULT = 0.55
ORBE_DANO_ESCALA_CARTA_MULT = 1.10
ORBE_MIGRACAO_DANO_MULT = 0.62
ORBE_MIGRACOES_MAX = 2
COLAPSO_DURACAO_MS = 2600
COLAPSO_PREPARO_MS = 1450
COLAPSO_ORBES = 3
COLAPSO_DANO_MULT = 0.85

_EXPLOSOES = []


def ativa(manifestacao):
    return str(manifestacao or "").strip().lower() == "gravitante"


def dano_orbe_escalavel(dano_base, bonus=1.0):
    dano_base = max(1.0, float(dano_base))
    dano_inicial = min(dano_base, GRAVITANTE_DANO_REFERENCIA_INICIAL)
    dano_build = max(0.0, dano_base - GRAVITANTE_DANO_REFERENCIA_INICIAL)
    dano = (
        dano_inicial * ORBE_DANO_INICIAL_MULT
        + dano_build * ORBE_DANO_ESCALA_CARTA_MULT
    )
    return max(1.0, dano * float(bonus))


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


def _texto(efeitos_texto, texto, rect, tempo_atual, cor=COR_GRAVITANTE_CLARA):
    if efeitos_texto is None or rect is None:
        return
    efeitos_texto.append({
        "texto": texto,
        "x": rect.centerx,
        "y": rect.top - 24,
        "tempo_inicio": int(tempo_atual),
        "cor": cor,
    })


def _rect(alvo):
    return alvo.get("rect") if isinstance(alvo, dict) else None


def _distancia_rect(a, b):
    ra = _rect(a)
    rb = _rect(b)
    if ra is None or rb is None:
        return 999999.0
    return math.hypot(ra.centerx - rb.centerx, ra.centery - rb.centery)


def criar_auto_attack(manifestacao, vfx, centro_x, centro_y, largura, altura, angulo, velocidade, tempo_atual, impulsiva=False):
    if not ativa(manifestacao):
        return condutora_manifestacao.criar_auto_attack(
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

    largura = max(10, int(largura * 0.72))
    altura = max(10, int(altura * 0.72))
    disparo = vfx.criar_disparo(
        centro_x,
        centro_y,
        largura,
        altura,
        angulo,
        velocidade * ORBE_VELOCIDADE_MULT,
        tempo_atual,
        impulsiva,
    )
    disparo["tipo_manifestacao"] = "gravitante_orbe"
    disparo["dano_mult_manifestacao"] = ORBE_DANO_IMPACTO_MULT
    disparo["raio_vfx"] = max(5, min(11, int(min(largura, altura) * 0.55)))
    disparo["pulso_gravitante"] = random.random() * math.tau
    return disparo


def multiplicador_dano_disparo(disparo):
    if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "gravitante_orbe":
        return float(disparo.get("dano_mult_manifestacao", ORBE_DANO_IMPACTO_MULT))
    return 1.0


def _novo_orbe(tempo_atual, dano_base, origem=None, bonus=1.0):
    seed = random.randint(1000, 999999) + int(tempo_atual)
    return {
        "criada_ms": int(tempo_atual),
        "fim_ms": int(tempo_atual) + ORBE_DURACAO_MS,
        "ultimo_tick_ms": int(tempo_atual),
        "dano_base": dano_orbe_escalavel(dano_base, bonus),
        "angulo": random.random() * math.tau,
        "vel": random.choice((-1.0, 1.0)) * random.uniform(0.0045, 0.0072),
        "raio": random.uniform(18.0, 30.0),
        "seed": seed,
        "origem": origem,
        "pulso_ms": int(tempo_atual),
        "migracoes": 0,
    }


def ancorar_orbe(alvo, disparo, tempo_atual, dano_base=10.0, efeitos_texto=None, bonus=1.0, inimigos=None):
    if not isinstance(alvo, dict):
        return None
    rect = alvo.get("rect")
    morreu_antes_da_orbita = alvo.get("vida", 1) <= 0
    orbes = alvo.setdefault("orbes_gravitantes", [])
    orbes.append(_novo_orbe(tempo_atual, dano_base, id(disparo), bonus))
    if len(orbes) > 5:
        del orbes[:-5]
    _texto(efeitos_texto, "orbita", rect, tempo_atual)
    orbe = orbes[-1]
    if morreu_antes_da_orbita and inimigos is not None:
        migrar_orbes_do_morto(alvo, inimigos, tempo_atual)
    return orbe


def _alvo_migracao(inimigos, morto, limite=ORBE_RAIO_MIGRACAO):
    candidatos = [
        alvo for alvo in inimigos or []
        if isinstance(alvo, dict) and alvo is not morto and alvo.get("vida", 1) > 0 and alvo.get("rect") is not None
    ]
    if not candidatos:
        return None
    candidatos.sort(key=lambda alvo: _distancia_rect(morto, alvo))
    if _distancia_rect(morto, candidatos[0]) <= limite:
        return candidatos[0]
    return None


def migrar_orbes_do_morto(morto, inimigos, tempo_atual):
    if not isinstance(morto, dict):
        return
    orbes = morto.pop("orbes_gravitantes", [])
    if not orbes:
        return
    alvo = _alvo_migracao(inimigos, morto)
    if alvo is None:
        rect = morto.get("rect")
        if rect is not None:
            _EXPLOSOES.append({"x": rect.centerx, "y": rect.centery, "inicio_ms": int(tempo_atual), "forte": False})
        return
    destino = alvo.setdefault("orbes_gravitantes", [])
    for orbe in orbes:
        migracoes = int(orbe.get("migracoes", 0))
        if migracoes >= ORBE_MIGRACOES_MAX:
            continue
        orbe["migracoes"] = migracoes + 1
        orbe["dano_base"] = max(1.0, float(orbe.get("dano_base", 1.0)) * ORBE_MIGRACAO_DANO_MULT)
        orbe["pulso_ms"] = int(tempo_atual)
        destino.append(orbe)


def _explodir_no_alvo(alvo, orbe, inimigos, tempo_atual, efeitos_texto=None):
    rect = alvo.get("rect") if isinstance(alvo, dict) else None
    if rect is None:
        return []
    mortos = []
    dano_base = float(orbe.get("dano_base", 10.0)) * ORBE_EXPLOSAO_MULT
    _EXPLOSOES.append({"x": rect.centerx, "y": rect.centery, "inicio_ms": int(tempo_atual), "forte": True})
    _texto(efeitos_texto, "COLAPSO", rect, tempo_atual, COR_GRAVITANTE_CLARA)
    for outro in inimigos or []:
        outro_rect = outro.get("rect") if isinstance(outro, dict) else None
        if outro_rect is None or outro.get("vida", 1) <= 0:
            continue
        dist = math.hypot(outro_rect.centerx - rect.centerx, outro_rect.centery - rect.centery)
        if dist > ORBE_RAIO_EXPLOSAO:
            continue
        queda = max(0.34, 1.0 - dist / max(1.0, ORBE_RAIO_EXPLOSAO * 1.28))
        dano = max(1.0, dano_base * queda)
        outro["vida"] -= dano
        _texto(efeitos_texto, f"-{int(dano)}", outro_rect, tempo_atual, COR_GRAVITANTE)
        if outro.get("vida", 1) <= 0 and outro not in mortos:
            mortos.append(outro)
    return mortos


def atualizar_orbes(inimigos, tempo_atual, dano_base, efeitos_texto=None):
    mortos = []
    migracoes = []
    for alvo in list(inimigos or []):
        if not isinstance(alvo, dict):
            continue
        orbes = alvo.get("orbes_gravitantes")
        rect = alvo.get("rect")
        if not orbes or rect is None:
            continue
        if alvo.get("vida", 1) <= 0:
            migracoes.append(alvo)
            continue

        vivos = []
        for orbe in list(orbes):
            if int(tempo_atual) >= int(orbe.get("fim_ms", 0)):
                for morto in _explodir_no_alvo(alvo, orbe, inimigos, tempo_atual, efeitos_texto):
                    if morto not in mortos:
                        mortos.append(morto)
                continue
            if int(tempo_atual) - int(orbe.get("ultimo_tick_ms", 0)) >= ORBE_TICK_MS:
                orbe["ultimo_tick_ms"] = int(tempo_atual)
                dano = max(1.0, float(orbe.get("dano_base", dano_base)) * ORBE_TICK_MULT)
                alvo["vida"] -= dano
                _texto(efeitos_texto, f"-{int(dano)}", rect, tempo_atual, COR_GRAVITANTE)
                if alvo.get("vida", 1) <= 0:
                    if alvo not in mortos:
                        mortos.append(alvo)
                    vivos.append(orbe)
                    break
            vivos.append(orbe)
        if vivos:
            alvo["orbes_gravitantes"] = vivos
        else:
            alvo.pop("orbes_gravitantes", None)

    for morto in mortos + migracoes:
        migrar_orbes_do_morto(morto, inimigos, tempo_atual)
    return mortos


def criar_colapso_orbital(x, y, tempo_atual, dano_base, largura_mapa=None, altura_mapa=None):
    rect = pygame.Rect(int(x - 52), int(y - 52), 104, 104)
    return {
        "tipo_manifestacao": "colapso_orbital",
        "rect": rect,
        "x": float(x),
        "y": float(y),
        "tempo_inicio": int(tempo_atual),
        "disparar_ms": int(tempo_atual) + COLAPSO_PREPARO_MS,
        "fim_ms": int(tempo_atual) + COLAPSO_DURACAO_MS,
        "dano_base": max(1.0, float(dano_base)),
        "orbes": [
            {"angulo": i * math.tau / COLAPSO_ORBES, "seed": random.randint(1000, 999999), "disparado": False}
            for i in range(COLAPSO_ORBES)
        ],
        "largura_mapa": largura_mapa,
        "altura_mapa": altura_mapa,
    }


def processar_colapso_orbital(colapso, inimigos, tela, tempo_atual, config_graficos=None, efeitos_texto=None):
    desenhar_colapso_orbital(tela, colapso, tempo_atual, config_graficos)
    if int(tempo_atual) < int(colapso.get("disparar_ms", 0)):
        return True, []

    mortos = []
    usados = set()
    for orbe in colapso.get("orbes", []):
        if orbe.get("disparado"):
            continue
        candidatos = [
            alvo for alvo in inimigos or []
            if isinstance(alvo, dict) and alvo.get("vida", 1) > 0 and alvo.get("rect") is not None and id(alvo) not in usados
        ]
        if not candidatos:
            continue
        candidatos.sort(key=lambda alvo: math.hypot(alvo["rect"].centerx - colapso["x"], alvo["rect"].centery - colapso["y"]))
        alvo = candidatos[0]
        usados.add(id(alvo))
        ancorar_orbe(
            alvo,
            {"tipo_manifestacao": "colapso_orbital", "seed": orbe.get("seed")},
            tempo_atual,
            colapso.get("dano_base", 10.0),
            efeitos_texto,
            COLAPSO_DANO_MULT,
            inimigos,
        )
        orbe["disparado"] = True
        rect = alvo.get("rect")
        if rect is not None:
            _EXPLOSOES.append({"x": rect.centerx, "y": rect.centery, "inicio_ms": int(tempo_atual), "forte": False})

    manter = int(tempo_atual) < int(colapso.get("fim_ms", 0)) and not all(o.get("disparado") for o in colapso.get("orbes", []))
    return manter, mortos


def desenhar_orbes(tela, inimigos, tempo_atual, config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        _EXPLOSOES.clear()
        return
    for alvo in inimigos or []:
        if not isinstance(alvo, dict):
            continue
        rect = alvo.get("rect")
        orbes = alvo.get("orbes_gravitantes")
        if rect is None or not orbes:
            continue
        for idx, orbe in enumerate(orbes):
            orbe["angulo"] = float(orbe.get("angulo", 0.0)) + float(orbe.get("vel", 0.005)) * 16.67
            raio = float(orbe.get("raio", 24.0)) + math.sin(tempo_atual * 0.006 + idx) * 3.0
            px = rect.centerx + math.cos(orbe["angulo"]) * raio
            py = rect.centery + math.sin(orbe["angulo"]) * raio * 0.72
            _desenhar_orbe(tela, px, py, 6 if perfil == "baixo" else 8, perfil, tempo_atual, orbe.get("seed", idx))
            if perfil in ("alto", "medio"):
                pygame.draw.arc(
                    tela,
                    COR_GRAVITANTE_ESCURA,
                    rect.inflate(int(raio * 2.0), int(raio * 1.3)),
                    orbe["angulo"] - 1.1,
                    orbe["angulo"] + 1.1,
                    1,
                )
    _desenhar_explosoes(tela, tempo_atual, perfil)


def desenhar_colapso_orbital(tela, colapso, tempo_atual, config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        return
    idade = int(tempo_atual) - int(colapso.get("tempo_inicio", tempo_atual))
    progresso = max(0.0, min(1.0, idade / float(max(1, COLAPSO_PREPARO_MS))))
    cx = float(colapso.get("x", colapso["rect"].centerx))
    cy = float(colapso.get("y", colapso["rect"].centery))
    raio = 46 + math.sin(tempo_atual * 0.008) * 5
    pygame.draw.circle(tela, COR_GRAVITANTE_ESCURA, (int(cx), int(cy)), int(raio + 8), 2)
    pygame.draw.circle(tela, COR_GRAVITANTE, (int(cx), int(cy)), int(raio), 1)
    for idx, orbe in enumerate(colapso.get("orbes", [])):
        if orbe.get("disparado"):
            continue
        ang = float(orbe.get("angulo", 0.0)) + tempo_atual * (0.004 + progresso * 0.004)
        px = cx + math.cos(ang) * raio
        py = cy + math.sin(ang) * raio
        _desenhar_orbe(tela, px, py, 7 if perfil == "baixo" else 10, perfil, tempo_atual, orbe.get("seed", idx))


def desenhar_orbe_disparo(tela, disparo, tempo_atual, offset=(0, 0), config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        return
    ox, oy = offset
    cx = disparo["rect"].centerx + ox
    cy = disparo["rect"].centery + oy
    trail = disparo.get("trail", [])
    rastro = 8 if perfil == "alto" else 5 if perfil == "medio" else 3
    for idx, (tx, ty) in enumerate(reversed(trail[-rastro:])):
        fade = 1.0 - idx / max(1, rastro)
        pygame.draw.circle(tela, COR_GRAVITANTE_ESCURA, (int(tx + ox), int(ty + oy)), max(2, int(8 * fade)), 1)
        if perfil != "baixo":
            pygame.draw.circle(tela, COR_GRAVITANTE, (int(tx + ox), int(ty + oy)), max(1, int(3 * fade)))
    _desenhar_orbe(tela, cx, cy, int(disparo.get("raio_vfx", 8)), perfil, tempo_atual, disparo.get("seed_vfx", 0))


def _desenhar_orbe(tela, x, y, raio, perfil, tempo_atual, seed=0):
    cx, cy = int(x), int(y)
    if perfil != "baixo":
        pygame.draw.circle(tela, COR_GRAVITANTE_ESCURA, (cx, cy), raio + 8)
        pygame.draw.circle(tela, COR_GRAVITANTE, (cx, cy), raio + 4, 2)
    pygame.draw.circle(tela, COR_GRAVITANTE_NUCLEO, (cx, cy), raio + 2)
    pygame.draw.circle(tela, COR_GRAVITANTE_CLARA, (cx - max(1, raio // 3), cy - max(1, raio // 3)), max(2, raio // 2))
    if perfil == "alto":
        rng = random.Random(int(seed) + int(tempo_atual // 75))
        for i in range(4):
            ang = tempo_atual * 0.012 + i * math.tau / 4 + rng.uniform(-0.2, 0.2)
            p1 = (cx + int(math.cos(ang) * (raio + 4)), cy + int(math.sin(ang) * (raio + 4)))
            p2 = (cx + int(math.cos(ang + 0.55) * (raio + 12)), cy + int(math.sin(ang + 0.55) * (raio + 12)))
            pygame.draw.line(tela, COR_GRAVITANTE_CLARA, p1, p2, 1)


def _desenhar_explosoes(tela, tempo_atual, perfil):
    vivos = []
    for exp in _EXPLOSOES:
        idade = int(tempo_atual) - int(exp.get("inicio_ms", tempo_atual))
        dur = 520 if exp.get("forte") else 320
        if idade >= dur:
            continue
        t = max(0.0, min(1.0, idade / float(dur)))
        raio = int((18 + (95 if exp.get("forte") else 48) * t) * (1.0 if perfil == "alto" else 0.72 if perfil == "medio" else 0.48))
        alpha = int(210 * (1.0 - t))
        surf = pygame.Surface((raio * 2 + 10, raio * 2 + 10), pygame.SRCALPHA)
        c = raio + 5
        pygame.draw.circle(surf, (*COR_GRAVITANTE, max(18, alpha // 3)), (c, c), raio, 2)
        pygame.draw.circle(surf, (*COR_GRAVITANTE_CLARA, max(24, alpha)), (c, c), max(4, int(raio * 0.24)), 1)
        tela.blit(surf, (int(exp.get("x", 0)) - c, int(exp.get("y", 0)) - c))
        vivos.append(exp)
    _EXPLOSOES[:] = vivos
