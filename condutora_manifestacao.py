# -*- coding: utf-8 -*-
import math
import random

import pygame

import parasitica_manifestacao


COR_CONDUTORA = (255, 210, 80)
COR_CONDUTORA_CLARA = (255, 248, 180)
COR_CONDUTORA_FRIA = (80, 235, 255)
COR_CONDUTORA_ESCURA = (88, 54, 18)

FIO_DANO_MULT = 0.54
FIO_VELOCIDADE_MULT = 1.04
FIO_DURACAO_MS = 8200
FIO_RAIO_CONEXAO = 190
FIO_MAX_LINKS_POR_ALVO = 3
FIO_LARGURA_DANO = 18
FIO_TICK_MS = 720
FIO_TRAVESSIA_MS = 460
FIO_TICK_DANO_MULT = 0.18
FIO_TRAVESSIA_DANO_MULT = 0.34
FECHAMENTO_DURACAO_MS = 520
FECHAMENTO_ISOLADO_MULT = 0.42
FECHAMENTO_BASE_MULT = 0.72
FECHAMENTO_ALVO_MULT = 0.24
FECHAMENTO_LINK_MULT = 0.18

_FECHAMENTOS = []


def ativa(manifestacao):
    return str(manifestacao or "").strip().lower() == "condutora"


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


def _id_alvo(alvo):
    if isinstance(alvo, dict):
        return alvo.get("condutora_id", id(alvo))
    if hasattr(alvo, "left"):
        return (int(alvo.left), int(alvo.top), int(alvo.width), int(alvo.height))
    return id(alvo)


def _rect(alvo):
    return alvo.get("rect") if isinstance(alvo, dict) else alvo


def _distancia(a, b):
    ra, rb = _rect(a), _rect(b)
    if ra is None or rb is None:
        return 999999.0
    return math.hypot(ra.centerx - rb.centerx, ra.centery - rb.centery)


def _ponto_segmento_dist(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab2 = abx * abx + aby * aby
    if ab2 <= 0.001:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab2))
    cx = ax + abx * t
    cy = ay + aby * t
    return math.hypot(px - cx, py - cy)


def _texto(efeitos_texto, texto, rect, tempo_atual, cor):
    if efeitos_texto is None or rect is None:
        return
    efeitos_texto.append({
        "texto": texto,
        "x": rect.centerx,
        "y": rect.top - 24,
        "tempo_inicio": int(tempo_atual),
        "cor": cor,
    })


def criar_auto_attack(manifestacao, vfx, centro_x, centro_y, largura, altura, angulo, velocidade, tempo_atual, impulsiva=False):
    if not ativa(manifestacao):
        return parasitica_manifestacao.criar_auto_attack(
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

    largura = max(8, int(largura * 0.58))
    altura = max(8, int(altura * 0.58))
    velocidade = float(velocidade) * FIO_VELOCIDADE_MULT
    rect = pygame.Rect(int(centro_x - largura // 2), int(centro_y - altura // 2), largura, altura)
    return {
        "tipo_manifestacao": "condutora_fio",
        "rect": rect,
        "angulo": float(angulo),
        "pos_x": float(rect.x),
        "pos_y": float(rect.y),
        "vx": math.cos(angulo) * velocidade,
        "vy": math.sin(angulo) * velocidade,
        "velocidade_base_vfx": velocidade,
        "raio_vfx": max(4, min(9, largura // 2)),
        "nascimento_ms": int(tempo_atual),
        "seed_vfx": random.randint(1000, 999999) + int(tempo_atual),
        "impulsiva_vfx": bool(impulsiva),
        "trail": [],
        "dano_mult_manifestacao": FIO_DANO_MULT,
    }


def multiplicador_dano_disparo(disparo):
    if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "condutora_fio":
        return float(disparo.get("dano_mult_manifestacao", FIO_DANO_MULT))
    return 1.0


def marcar_alvo(alvo, tempo_atual, dano_base=10.0, efeitos_texto=None):
    if not isinstance(alvo, dict) or alvo.get("vida", 1) <= 0:
        return None
    rect = alvo.get("rect")
    fio = alvo.get("fio_condutor")
    if not fio:
        fio = {
            "criada_ms": int(tempo_atual),
            "ultimo_tick_ms": int(tempo_atual),
            "dano_base": max(1.0, float(dano_base)),
            "carga": 1,
            "pulso_ms": int(tempo_atual),
            "travessias": {},
        }
        alvo["fio_condutor"] = fio
        _texto(efeitos_texto, "fio", rect, tempo_atual, COR_CONDUTORA)
    else:
        fio["criada_ms"] = int(tempo_atual)
        fio["dano_base"] = max(float(fio.get("dano_base", 1.0)), float(dano_base))
        fio["carga"] = min(5, int(fio.get("carga", 1)) + 1)
        fio["pulso_ms"] = int(tempo_atual)
        _texto(efeitos_texto, "+carga", rect, tempo_atual, COR_CONDUTORA_CLARA)
    return fio


def _alvos_marcados(inimigos, tempo_atual):
    marcados = []
    for inimigo in list(inimigos or []):
        if not isinstance(inimigo, dict):
            continue
        fio = inimigo.get("fio_condutor")
        rect = inimigo.get("rect")
        if not fio or rect is None or inimigo.get("vida", 1) <= 0:
            continue
        if int(tempo_atual) - int(fio.get("criada_ms", tempo_atual)) > FIO_DURACAO_MS:
            inimigo.pop("fio_condutor", None)
            continue
        marcados.append(inimigo)
    return marcados


def _conexoes(marcados):
    candidatos = []
    for i, a in enumerate(marcados):
        for b in marcados[i + 1:]:
            dist = _distancia(a, b)
            if dist <= FIO_RAIO_CONEXAO:
                candidatos.append((dist, a, b))
    candidatos.sort(key=lambda item: item[0])
    links = []
    grau = {id(alvo): 0 for alvo in marcados}
    vistos = set()
    for dist, a, b in candidatos:
        chave = frozenset((id(a), id(b)))
        if chave in vistos:
            continue
        if grau.get(id(a), 0) >= FIO_MAX_LINKS_POR_ALVO or grau.get(id(b), 0) >= FIO_MAX_LINKS_POR_ALVO:
            continue
        vistos.add(chave)
        grau[id(a)] = grau.get(id(a), 0) + 1
        grau[id(b)] = grau.get(id(b), 0) + 1
        links.append((a, b, dist))
    return links


def atualizar_circuitos(inimigos, tempo_atual, dano_base, efeitos_texto=None):
    marcados = _alvos_marcados(inimigos, tempo_atual)
    links = _conexoes(marcados)
    if not marcados:
        return []

    mortos = []
    grau = {id(alvo): 0 for alvo in marcados}
    for a, b, _dist in links:
        grau[id(a)] += 1
        grau[id(b)] += 1

    for alvo in marcados:
        fio = alvo.get("fio_condutor", {})
        if grau.get(id(alvo), 0) <= 0:
            continue
        if int(tempo_atual) - int(fio.get("ultimo_tick_ms", 0)) < FIO_TICK_MS:
            continue
        fio["ultimo_tick_ms"] = int(tempo_atual)
        dano = max(1.0, float(fio.get("dano_base", dano_base)) * FIO_TICK_DANO_MULT * (1.0 + grau[id(alvo)] * 0.22))
        alvo["vida"] -= dano
        _texto(efeitos_texto, f"-{int(dano)}", alvo.get("rect"), tempo_atual, COR_CONDUTORA)
        if alvo.get("vida", 1) <= 0 and alvo not in mortos:
            mortos.append(alvo)

    marcados_ids = {id(alvo) for alvo in marcados}
    for a, b, _dist in links:
        ra, rb = a.get("rect"), b.get("rect")
        if ra is None or rb is None:
            continue
        ax, ay = ra.center
        bx, by = rb.center
        chave_link = tuple(sorted((_id_alvo(a), _id_alvo(b)), key=str))
        for alvo in inimigos or []:
            if not isinstance(alvo, dict) or id(alvo) in marcados_ids or alvo.get("vida", 1) <= 0:
                continue
            rect = alvo.get("rect")
            if rect is None:
                continue
            dist_linha = _ponto_segmento_dist(rect.centerx, rect.centery, ax, ay, bx, by)
            if dist_linha > FIO_LARGURA_DANO + min(rect.width, rect.height) * 0.25:
                continue
            travessias = alvo.setdefault("condutora_travessias", {})
            if int(tempo_atual) - int(travessias.get(chave_link, 0)) < FIO_TRAVESSIA_MS:
                continue
            travessias[chave_link] = int(tempo_atual)
            dano = max(1.0, float(dano_base) * FIO_TRAVESSIA_DANO_MULT)
            alvo["vida"] -= dano
            _texto(efeitos_texto, f"-{int(dano)}", rect, tempo_atual, COR_CONDUTORA_FRIA)
            if alvo.get("vida", 1) <= 0 and alvo not in mortos:
                mortos.append(alvo)

    return mortos


def _componentes(marcados, links):
    vizinhos = {id(alvo): [] for alvo in marcados}
    por_id = {id(alvo): alvo for alvo in marcados}
    link_lookup = {}
    for a, b, _dist in links:
        vizinhos[id(a)].append(id(b))
        vizinhos[id(b)].append(id(a))
        link_lookup[frozenset((id(a), id(b)))] = (a, b)

    componentes = []
    visitados = set()
    for alvo in marcados:
        raiz = id(alvo)
        if raiz in visitados:
            continue
        pilha = [raiz]
        visitados.add(raiz)
        ids = []
        while pilha:
            atual = pilha.pop()
            ids.append(atual)
            for viz in vizinhos.get(atual, []):
                if viz not in visitados:
                    visitados.add(viz)
                    pilha.append(viz)
        alvos = [por_id[i] for i in ids if i in por_id]
        comp_links = []
        ids_set = set(ids)
        for chave, link in link_lookup.items():
            if set(chave).issubset(ids_set):
                comp_links.append(link)
        componentes.append((alvos, comp_links))
    return componentes


def fechar_circuitos(inimigos, tempo_atual, dano_base, efeitos_texto=None):
    marcados = _alvos_marcados(inimigos, tempo_atual)
    links = _conexoes(marcados)
    componentes = _componentes(marcados, links)
    mortos = []
    total_links = len(links)
    total_alvos = len(marcados)

    for alvos, comp_links in componentes:
        qtd_alvos = len(alvos)
        qtd_links = len(comp_links)
        mult = FECHAMENTO_ISOLADO_MULT if qtd_alvos <= 1 else (
            FECHAMENTO_BASE_MULT + qtd_alvos * FECHAMENTO_ALVO_MULT + qtd_links * FECHAMENTO_LINK_MULT
        )
        dano = max(1.0, float(dano_base) * mult)
        pontos = []
        for alvo in alvos:
            rect = alvo.get("rect")
            if rect is not None:
                pontos.append(rect.center)
            alvo["vida"] -= dano
            alvo.pop("fio_condutor", None)
            _texto(efeitos_texto, f"-{int(dano)}", rect, tempo_atual, COR_CONDUTORA_CLARA if qtd_alvos > 1 else COR_CONDUTORA)
            if alvo.get("vida", 1) <= 0 and alvo not in mortos:
                mortos.append(alvo)
        _FECHAMENTOS.append({
            "tempo_inicio": int(tempo_atual),
            "fim_ms": int(tempo_atual) + FECHAMENTO_DURACAO_MS,
            "pontos": pontos,
            "links": [(a.get("rect").center, b.get("rect").center) for a, b in comp_links if a.get("rect") and b.get("rect")],
            "forte": qtd_alvos > 1,
            "total": qtd_alvos,
        })

    return mortos, total_alvos, total_links


def criar_fechamento(x, y, tempo_atual, total_alvos=0, total_links=0):
    rect = pygame.Rect(int(x - 46), int(y - 46), 92, 92)
    return {
        "tipo_manifestacao": "fechamento_condutor",
        "rect": rect,
        "tempo_inicio": int(tempo_atual),
        "fim_ms": int(tempo_atual) + FECHAMENTO_DURACAO_MS,
        "total_alvos": int(total_alvos),
        "total_links": int(total_links),
    }


def desenhar_fechamento(tela, fechamento, tempo_atual, config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        return
    inicio = int(fechamento.get("tempo_inicio", tempo_atual))
    t = max(0.0, min(1.0, (int(tempo_atual) - inicio) / float(FECHAMENTO_DURACAO_MS)))
    raio = int((24 + 100 * t) * (1.0 if perfil == "alto" else 0.74 if perfil == "medio" else 0.52))
    alpha = int(190 * (1.0 - t))
    surf = pygame.Surface((raio * 2 + 12, raio * 2 + 12), pygame.SRCALPHA)
    c = raio + 6
    pygame.draw.circle(surf, (*COR_CONDUTORA, max(24, alpha // 3)), (c, c), raio, 2)
    pygame.draw.circle(surf, (*COR_CONDUTORA_CLARA, max(24, alpha)), (c, c), max(5, int(raio * 0.24)), 1)
    pontas = 10 if perfil == "alto" else 6 if perfil == "medio" else 4
    for i in range(pontas):
        ang = tempo_atual * 0.012 + i * math.tau / pontas
        p1 = (c + int(math.cos(ang) * raio * 0.35), c + int(math.sin(ang) * raio * 0.35))
        p2 = (c + int(math.cos(ang) * raio), c + int(math.sin(ang) * raio))
        pygame.draw.line(surf, (*COR_CONDUTORA_FRIA, max(20, alpha - 30)), p1, p2, 1)
    tela.blit(surf, (fechamento["rect"].centerx - c, fechamento["rect"].centery - c))


def _desenhar_fechamentos_ativos(tela, tempo_atual, perfil):
    if not _FECHAMENTOS:
        return
    vivos = []
    for fechamento in _FECHAMENTOS:
        inicio = int(fechamento.get("tempo_inicio", tempo_atual))
        fim = int(fechamento.get("fim_ms", inicio))
        if int(tempo_atual) >= fim:
            continue
        t = max(0.0, min(1.0, (int(tempo_atual) - inicio) / float(max(1, fim - inicio))))
        alpha = int((225 if fechamento.get("forte") else 150) * (1.0 - t))
        largura = 4 if perfil == "alto" else 3 if perfil == "medio" else 2
        for p1, p2 in fechamento.get("links", []):
            pygame.draw.line(tela, COR_CONDUTORA_ESCURA, p1, p2, largura + 3)
            pygame.draw.line(tela, COR_CONDUTORA_CLARA, p1, p2, largura)
        for px, py in fechamento.get("pontos", []):
            r = int(8 + 26 * t)
            pygame.draw.circle(tela, COR_CONDUTORA_ESCURA, (int(px), int(py)), r + 3, 2)
            pygame.draw.circle(tela, COR_CONDUTORA_CLARA if alpha > 100 else COR_CONDUTORA, (int(px), int(py)), max(3, r // 2), 1)
        vivos.append(fechamento)
    _FECHAMENTOS[:] = vivos


def desenhar_circuitos(tela, inimigos, tempo_atual, config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        _FECHAMENTOS.clear()
        return
    _desenhar_fechamentos_ativos(tela, tempo_atual, perfil)
    marcados = _alvos_marcados(inimigos, tempo_atual)
    links = _conexoes(marcados)
    largura = 3 if perfil == "alto" else 2 if perfil == "medio" else 1

    for a, b, dist in links:
        ra, rb = a.get("rect"), b.get("rect")
        if ra is None or rb is None:
            continue
        pulso = 0.5 + 0.5 * math.sin(tempo_atual * 0.011 + dist * 0.04)
        cor = COR_CONDUTORA_CLARA if pulso > 0.72 else COR_CONDUTORA
        pygame.draw.line(tela, COR_CONDUTORA_ESCURA, ra.center, rb.center, largura + 3)
        pygame.draw.line(tela, cor, ra.center, rb.center, largura)
        if perfil in ("alto", "medio"):
            segmentos = 4 if perfil == "alto" else 2
            for i in range(1, segmentos + 1):
                t = (i + pulso) / (segmentos + 1)
                sx = int(ra.centerx + (rb.centerx - ra.centerx) * t)
                sy = int(ra.centery + (rb.centery - ra.centery) * t)
                pygame.draw.circle(tela, COR_CONDUTORA_FRIA, (sx, sy), 2 if perfil == "alto" else 1)

    for alvo in marcados:
        rect = alvo.get("rect")
        fio = alvo.get("fio_condutor", {})
        if rect is None:
            continue
        carga = int(fio.get("carga", 1))
        idade_pulso = int(tempo_atual) - int(fio.get("pulso_ms", 0))
        pulso = 0.5 + 0.5 * math.sin(tempo_atual * 0.014 + carga)
        raio = max(7, int(min(rect.width, rect.height) * (0.36 + 0.08 * min(4, carga)) + pulso * 4))
        pygame.draw.circle(tela, COR_CONDUTORA_ESCURA, rect.center, raio + 4, 2)
        pygame.draw.circle(tela, COR_CONDUTORA, rect.center, raio, 1)
        if idade_pulso < 520:
            t = max(0.0, min(1.0, idade_pulso / 520.0))
            pygame.draw.circle(tela, COR_CONDUTORA_CLARA, rect.center, int(raio + 18 * t), 1)
        if perfil == "alto":
            for i in range(5):
                ang = tempo_atual * 0.008 + i * math.tau / 5 + carga
                px = rect.centerx + math.cos(ang) * (raio + 5)
                py = rect.centery + math.sin(ang) * (raio + 5)
                qx = rect.centerx + math.cos(ang + 0.45) * (raio + 10)
                qy = rect.centery + math.sin(ang + 0.45) * (raio + 10)
                pygame.draw.line(tela, COR_CONDUTORA_FRIA, (int(px), int(py)), (int(qx), int(qy)), 1)


def desenhar_fio_disparo(tela, disparo, tempo_atual, offset=(0, 0), config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        return
    ox, oy = offset
    cx = disparo["rect"].centerx + ox
    cy = disparo["rect"].centery + oy
    raio = int(disparo.get("raio_vfx", 6))
    trail = disparo.get("trail", [])
    rastro = 8 if perfil == "alto" else 5 if perfil == "medio" else 3
    for idx, (tx, ty) in enumerate(reversed(trail[-rastro:])):
        fade = 1.0 - idx / max(1, rastro)
        pygame.draw.circle(tela, COR_CONDUTORA_ESCURA, (int(tx + ox), int(ty + oy)), max(1, int(raio * fade)), 1)
        if perfil != "baixo":
            pygame.draw.circle(tela, COR_CONDUTORA, (int(tx + ox), int(ty + oy)), max(1, int(raio * fade * 0.45)))
    pygame.draw.circle(tela, COR_CONDUTORA_ESCURA, (int(cx), int(cy)), raio + 5)
    pygame.draw.circle(tela, COR_CONDUTORA, (int(cx), int(cy)), raio + 2, 2)
    pygame.draw.circle(tela, COR_CONDUTORA_CLARA, (int(cx), int(cy)), max(2, raio // 2))
    if perfil == "alto":
        giro = tempo_atual * 0.018 + disparo.get("seed_vfx", 0) * 0.001
        for i in range(4):
            ang = giro + i * math.tau / 4
            p1 = (int(cx + math.cos(ang) * (raio + 7)), int(cy + math.sin(ang) * (raio + 7)))
            p2 = (int(cx + math.cos(ang + 0.55) * (raio + 13)), int(cy + math.sin(ang + 0.55) * (raio + 13)))
            pygame.draw.line(tela, COR_CONDUTORA_FRIA, p1, p2, 1)
