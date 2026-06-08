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
FIO_TICK_DANO_MULT = 0.07
FIO_TRAVESSIA_DANO_MULT = 0.14
FECHAMENTO_DURACAO_MS = 520
FECHAMENTO_ISOLADO_MULT = 0.42
FECHAMENTO_BASE_MULT = 0.72
FECHAMENTO_ALVO_MULT = 0.24
FECHAMENTO_LINK_MULT = 0.18

_FECHAMENTOS = []

PORTAS_LOGICAS = ("OR", "XOR", "AND", "NAND", "NOR")
ENTRADA_A_DURACAO_MS = 3000
LINK_CORRETO_DURACAO_MS = 4000
LINK_ERRO_DURACAO_MS = 850
LINK_LOGICO_TICK_MS = 900
LINK_LOGICO_TICK_MULT = 0.14
LINK_RESULTADO_1_MULT = 1.78
LINK_RESULTADO_0_MULT = 0.58
FECHAMENTO_LOGICO_BASE_MULT = 1.10
FECHAMENTO_LOGICO_BONUS_LINK = 0.24
FECHAMENTO_LOGICO_LIMITE_MULT = 2.25
RUIDO_LOGICO_DURACAO_MS = 1800
RUIDO_LOGICO_VELOCIDADE_MULT = 0.88
COR_LOGICO_0 = (75, 225, 255)
COR_LOGICO_1 = (255, 228, 100)
COR_LOGICO_ERRO = (210, 82, 255)
COR_LOGICO_OK = (104, 255, 214)

_ESTADO_LOGICO = {
    "porta_atual": None,
    "proxima_porta": None,
    "entrada_a": None,
    "entrada_a_ms": 0,
    "links": [],
    "ruido_fim_ms": 0,
    "ultimo_resultado": None,
    "ultimo_resultado_ms": 0,
    "ultimo_feedback": "",
    "mortos_pendentes": [],
}


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


def _sortear_porta(evitar=None):
    opcoes = [porta for porta in PORTAS_LOGICAS if porta != evitar]
    return random.choice(opcoes or list(PORTAS_LOGICAS))


def _estado_logico():
    if _ESTADO_LOGICO.get("porta_atual") not in PORTAS_LOGICAS:
        _ESTADO_LOGICO["porta_atual"] = _sortear_porta()
    if _ESTADO_LOGICO.get("proxima_porta") not in PORTAS_LOGICAS:
        _ESTADO_LOGICO["proxima_porta"] = _sortear_porta(_ESTADO_LOGICO.get("porta_atual"))
    return _ESTADO_LOGICO


def reiniciar_logica_condutora():
    _ESTADO_LOGICO.update({
        "porta_atual": _sortear_porta(),
        "proxima_porta": None,
        "entrada_a": None,
        "entrada_a_ms": 0,
        "links": [],
        "ruido_fim_ms": 0,
        "ultimo_resultado": None,
        "ultimo_resultado_ms": 0,
        "ultimo_feedback": "",
        "mortos_pendentes": [],
    })
    _ESTADO_LOGICO["proxima_porta"] = _sortear_porta(_ESTADO_LOGICO["porta_atual"])


def _consumir_porta():
    estado = _estado_logico()
    usada = estado["porta_atual"]
    estado["porta_atual"] = estado["proxima_porta"]
    estado["proxima_porta"] = _sortear_porta(estado["porta_atual"])
    return usada


def _avaliar_porta(porta, bit_a, bit_b):
    a = 1 if int(bit_a) else 0
    b = 1 if int(bit_b) else 0
    porta = str(porta or "").upper()
    if porta == "AND":
        return 1 if a and b else 0
    if porta == "OR":
        return 1 if a or b else 0
    if porta == "XOR":
        return 1 if a != b else 0
    if porta == "NAND":
        return 0 if a and b else 1
    if porta == "NOR":
        return 1 if not a and not b else 0
    return 0


def _alvo_vivo(alvo):
    return isinstance(alvo, dict) and alvo.get("vida", 1) > 0 and alvo.get("rect") is not None


def garantir_bit_logico(alvo, inimigos=None):
    if not isinstance(alvo, dict):
        return 0
    bit = alvo.get("bit_logico")
    if bit in (0, 1):
        return int(bit)

    zeros = 0
    uns = 0
    for inimigo in inimigos or []:
        valor = inimigo.get("bit_logico") if isinstance(inimigo, dict) else None
        if valor == 0:
            zeros += 1
        elif valor == 1:
            uns += 1

    if zeros < uns:
        bit = 0
    elif uns < zeros:
        bit = 1
    else:
        bit = random.choice((0, 1))
    alvo["bit_logico"] = int(bit)
    alvo.setdefault("bit_logico_nasc_ms", pygame.time.get_ticks())
    return int(bit)


def garantir_bits_logicos(inimigos):
    for alvo in inimigos or []:
        if _alvo_vivo(alvo):
            garantir_bit_logico(alvo, inimigos)


def _link_chave(a, b, porta, tempo_atual):
    return f"{_id_alvo(a)}:{_id_alvo(b)}:{porta}:{int(tempo_atual)}"


def _registrar_feedback(texto, resultado, tempo_atual):
    estado = _estado_logico()
    estado["ultimo_feedback"] = str(texto or "")
    estado["ultimo_resultado"] = int(resultado)
    estado["ultimo_resultado_ms"] = int(tempo_atual)


def _aplicar_dano_logico(alvo, dano, tempo_atual, efeitos_texto, cor):
    if not _alvo_vivo(alvo):
        return False
    dano = max(1.0, float(dano))
    alvo["vida"] -= dano
    alvo["condutora_bit_pulso_ms"] = int(tempo_atual)
    _texto(efeitos_texto, f"-{int(dano)}", alvo.get("rect"), tempo_atual, cor)
    return alvo.get("vida", 1) <= 0


def registrar_acerto_logico(alvo, tempo_atual, dano_base=10.0, efeitos_texto=None, inimigos=None):
    if not _alvo_vivo(alvo):
        return None

    estado = _estado_logico()
    agora = int(tempo_atual)
    bit = garantir_bit_logico(alvo, inimigos)
    entrada_a = estado.get("entrada_a")

    if entrada_a is not None:
        if not _alvo_vivo(entrada_a) or agora - int(estado.get("entrada_a_ms", 0)) > ENTRADA_A_DURACAO_MS:
            estado["entrada_a"] = None
            entrada_a = None

    if entrada_a is None:
        estado["entrada_a"] = alvo
        estado["entrada_a_ms"] = agora
        alvo["condutora_entrada"] = "A"
        alvo["condutora_entrada_ms"] = agora
        alvo["condutora_bit_pulso_ms"] = agora
        _texto(efeitos_texto, f"A={bit}", alvo.get("rect"), agora, COR_LOGICO_0 if bit == 0 else COR_LOGICO_1)
        return {"fase": "A", "bit": bit}

    if entrada_a is alvo or _id_alvo(entrada_a) == _id_alvo(alvo):
        estado["entrada_a_ms"] = agora
        alvo["condutora_entrada"] = "A"
        alvo["condutora_entrada_ms"] = agora
        alvo["condutora_bit_pulso_ms"] = agora
        _texto(efeitos_texto, "A renovada", alvo.get("rect"), agora, COR_CONDUTORA_FRIA)
        return {"fase": "A", "renovada": True, "bit": bit}

    bit_a = garantir_bit_logico(entrada_a, inimigos)
    bit_b = bit
    porta = _consumir_porta()
    resultado = _avaliar_porta(porta, bit_a, bit_b)
    cor = COR_LOGICO_OK if resultado else COR_LOGICO_ERRO
    mult = LINK_RESULTADO_1_MULT if resultado else LINK_RESULTADO_0_MULT
    dano = max(1.0, float(dano_base) * mult)

    mortos = []
    if _aplicar_dano_logico(entrada_a, dano, agora, efeitos_texto, cor):
        mortos.append(entrada_a)
    if _aplicar_dano_logico(alvo, dano, agora, efeitos_texto, cor):
        mortos.append(alvo)
    if mortos:
        pendentes = estado.setdefault("mortos_pendentes", [])
        for morto in mortos:
            if morto not in pendentes:
                pendentes.append(morto)

    if not resultado:
        estado["ruido_fim_ms"] = agora + RUIDO_LOGICO_DURACAO_MS
        _texto(efeitos_texto, "RUIDO LOGICO", alvo.get("rect"), agora, COR_LOGICO_ERRO)

    entrada_a["condutora_entrada"] = "A"
    alvo["condutora_entrada"] = "B"
    entrada_a["condutora_entrada_ms"] = agora
    alvo["condutora_entrada_ms"] = agora
    entrada_a["condutora_resultado_ms"] = agora
    alvo["condutora_resultado_ms"] = agora
    entrada_a["condutora_resultado"] = resultado
    alvo["condutora_resultado"] = resultado

    link = {
        "a": entrada_a,
        "b": alvo,
        "porta": porta,
        "bit_a": bit_a,
        "bit_b": bit_b,
        "resultado": int(resultado),
        "criada_ms": agora,
        "fim_ms": agora + (LINK_CORRETO_DURACAO_MS if resultado else LINK_ERRO_DURACAO_MS),
        "ultimo_tick_ms": agora,
        "dano_base": max(1.0, float(dano_base)),
        "chave": _link_chave(entrada_a, alvo, porta, agora),
    }
    estado.setdefault("links", []).append(link)
    estado["entrada_a"] = None
    estado["entrada_a_ms"] = 0
    _registrar_feedback(f"{porta} = {resultado}", resultado, agora)
    _texto(efeitos_texto, f"{porta}={resultado}", alvo.get("rect"), agora, cor)
    return {"fase": "B", "porta": porta, "resultado": resultado, "mortos": mortos}


def fator_ruido_logico(manifestacao, tempo_atual):
    if not ativa(manifestacao):
        return 1.0
    estado = _estado_logico()
    return RUIDO_LOGICO_VELOCIDADE_MULT if int(tempo_atual) < int(estado.get("ruido_fim_ms", 0)) else 1.0


def _links_logicos_vivos(inimigos, tempo_atual, apenas_corretos=False):
    estado = _estado_logico()
    vivos = []
    inimigos_ids = {id(alvo) for alvo in inimigos or [] if isinstance(alvo, dict)}
    for link in list(estado.get("links", [])):
        a = link.get("a")
        b = link.get("b")
        if int(tempo_atual) >= int(link.get("fim_ms", 0)):
            continue
        if not _alvo_vivo(a) or not _alvo_vivo(b):
            continue
        if inimigos_ids and (id(a) not in inimigos_ids or id(b) not in inimigos_ids):
            continue
        if apenas_corretos and int(link.get("resultado", 0)) != 1:
            continue
        vivos.append(link)
    estado["links"] = vivos
    return vivos


def atualizar_circuitos(inimigos, tempo_atual, dano_base, efeitos_texto=None):
    estado = _estado_logico()
    if estado.get("entrada_a") is not None:
        entrada = estado["entrada_a"]
        if not _alvo_vivo(entrada) or int(tempo_atual) - int(estado.get("entrada_a_ms", 0)) > ENTRADA_A_DURACAO_MS:
            if isinstance(entrada, dict):
                entrada.pop("condutora_entrada", None)
            estado["entrada_a"] = None
            estado["entrada_a_ms"] = 0

    pendentes = []
    inimigos_set = {id(alvo) for alvo in inimigos or [] if isinstance(alvo, dict)}
    for morto in estado.get("mortos_pendentes", []):
        if isinstance(morto, dict) and id(morto) in inimigos_set and morto.get("vida", 1) <= 0:
            pendentes.append(morto)
    estado["mortos_pendentes"] = []
    mortos = list(pendentes)
    for link in _links_logicos_vivos(inimigos, tempo_atual):
        if int(link.get("resultado", 0)) != 1:
            continue
        if int(tempo_atual) - int(link.get("ultimo_tick_ms", 0)) < LINK_LOGICO_TICK_MS:
            continue
        link["ultimo_tick_ms"] = int(tempo_atual)
        dano = float(link.get("dano_base", dano_base)) * LINK_LOGICO_TICK_MULT
        for alvo in (link.get("a"), link.get("b")):
            if _aplicar_dano_logico(alvo, dano, tempo_atual, efeitos_texto, COR_CONDUTORA_FRIA) and alvo not in mortos:
                mortos.append(alvo)
    return mortos


def fechar_circuitos(inimigos, tempo_atual, dano_base, efeitos_texto=None):
    links = _links_logicos_vivos(inimigos, tempo_atual, apenas_corretos=True)
    if not links:
        _registrar_feedback("Sem circuito correto", 0, tempo_atual)
        _FECHAMENTOS.append({
            "tempo_inicio": int(tempo_atual),
            "fim_ms": int(tempo_atual) + FECHAMENTO_DURACAO_MS,
            "pontos": [],
            "links": [],
            "forte": False,
            "total": 0,
        })
        return [], 0, 0

    dano_por_alvo = {}
    pontos = []
    linhas = []
    mult = min(FECHAMENTO_LOGICO_LIMITE_MULT, FECHAMENTO_LOGICO_BASE_MULT + (len(links) - 1) * FECHAMENTO_LOGICO_BONUS_LINK)
    for link in links:
        a = link.get("a")
        b = link.get("b")
        for alvo in (a, b):
            if not _alvo_vivo(alvo):
                continue
            chave_alvo = id(alvo)
            if chave_alvo not in dano_por_alvo:
                dano_por_alvo[chave_alvo] = {"alvo": alvo, "dano": 0.0}
            dano_por_alvo[chave_alvo]["dano"] += float(dano_base) * mult
            pontos.append(alvo["rect"].center)
        if _alvo_vivo(a) and _alvo_vivo(b):
            linhas.append((a["rect"].center, b["rect"].center))

    mortos = []
    for item in dano_por_alvo.values():
        alvo = item["alvo"]
        dano = item["dano"]
        if _aplicar_dano_logico(alvo, dano, tempo_atual, efeitos_texto, COR_CONDUTORA_CLARA) and alvo not in mortos:
            mortos.append(alvo)

    ids_consumidos = {link.get("chave") for link in links}
    estado = _estado_logico()
    estado["links"] = [link for link in estado.get("links", []) if link.get("chave") not in ids_consumidos]
    _registrar_feedback(f"{len(links)} circuito(s)", 1, tempo_atual)
    _FECHAMENTOS.append({
        "tempo_inicio": int(tempo_atual),
        "fim_ms": int(tempo_atual) + FECHAMENTO_DURACAO_MS,
        "pontos": pontos,
        "links": linhas,
        "forte": True,
        "total": len(dano_por_alvo),
    })
    return mortos, len(dano_por_alvo), len(links)


def _fonte(tamanho, negrito=False):
    try:
        return pygame.font.SysFont("consolas", tamanho, bold=negrito)
    except Exception:
        return pygame.font.Font(None, tamanho)


def _texto_contorno(tela, fonte, texto, pos, cor, contorno=(2, 8, 15)):
    x, y = int(pos[0]), int(pos[1])
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        tela.blit(fonte.render(texto, True, contorno), (x + ox, y + oy))
    tela.blit(fonte.render(texto, True, cor), (x, y))


def _desenhar_bit_logico(tela, alvo, tempo_atual, perfil):
    rect = alvo.get("rect")
    if rect is None:
        return
    bit = garantir_bit_logico(alvo)
    cor = COR_LOGICO_0 if bit == 0 else COR_LOGICO_1
    nasc = int(alvo.get("bit_logico_nasc_ms", tempo_atual))
    pulso_ms = int(alvo.get("condutora_bit_pulso_ms", 0))
    idade = max(0, int(tempo_atual) - nasc)
    pop = 1.0 + max(0.0, 1.0 - idade / 320.0) * 0.35
    pulso = max(0.0, 1.0 - max(0, int(tempo_atual) - pulso_ms) / 420.0)
    tam = int((15 + pulso * 4) * pop)
    cx = rect.centerx
    cy = rect.top - 12
    pontos = [(cx, cy - tam), (cx + tam, cy), (cx, cy + tam), (cx - tam, cy)]
    pygame.draw.polygon(tela, (4, 13, 24), pontos)
    pygame.draw.polygon(tela, cor, pontos, 2)
    if pulso > 0.0:
        pygame.draw.circle(tela, cor, (cx, cy), int(tam + 10 * pulso), 1)
    fonte = _fonte(18, True)
    texto = str(bit)
    surf = fonte.render(texto, True, cor)
    _texto_contorno(tela, fonte, texto, (cx - surf.get_width() // 2, cy - surf.get_height() // 2), cor)

    entrada = alvo.get("condutora_entrada")
    entrada_ms = int(alvo.get("condutora_entrada_ms", 0))
    if entrada and int(tempo_atual) - entrada_ms < ENTRADA_A_DURACAO_MS + 500:
        letra_cor = COR_CONDUTORA_FRIA if entrada == "A" else COR_CONDUTORA_CLARA
        _texto_contorno(tela, _fonte(14, True), str(entrada), (cx + tam + 3, cy - 9), letra_cor)

    if perfil == "alto" and entrada:
        raio = max(rect.width, rect.height) * 0.55
        for i in range(3):
            ang = tempo_atual * 0.01 + i * math.tau / 3
            px = rect.centerx + math.cos(ang) * raio
            py = rect.centery + math.sin(ang) * raio
            pygame.draw.circle(tela, COR_CONDUTORA_FRIA, (int(px), int(py)), 2)


def _desenhar_link_logico(tela, link, tempo_atual, perfil):
    a = link.get("a")
    b = link.get("b")
    if not _alvo_vivo(a) or not _alvo_vivo(b):
        return
    ra, rb = a["rect"], b["rect"]
    resultado = int(link.get("resultado", 0))
    idade = int(tempo_atual) - int(link.get("criada_ms", tempo_atual))
    vida = max(1, int(link.get("fim_ms", tempo_atual)) - int(link.get("criada_ms", tempo_atual)))
    t = max(0.0, min(1.0, idade / float(vida)))
    largura = 4 if perfil == "alto" else 3 if perfil == "medio" else 2
    if resultado:
        cor_base = COR_LOGICO_OK
        cor_pulso = COR_LOGICO_1
    else:
        cor_base = COR_LOGICO_ERRO
        cor_pulso = (145, 160, 185)

    pygame.draw.line(tela, (5, 13, 24), ra.center, rb.center, largura + 5)
    if resultado:
        pygame.draw.line(tela, cor_base, ra.center, rb.center, largura)
    else:
        segmentos = 7
        for i in range(segmentos):
            if (i + int(tempo_atual / 90)) % 3 == 0:
                continue
            p1 = i / segmentos
            p2 = (i + 0.72) / segmentos
            x1 = ra.centerx + (rb.centerx - ra.centerx) * p1
            y1 = ra.centery + (rb.centery - ra.centery) * p1
            x2 = ra.centerx + (rb.centerx - ra.centerx) * min(1.0, p2)
            y2 = ra.centery + (rb.centery - ra.centery) * min(1.0, p2)
            pygame.draw.line(tela, cor_base, (int(x1), int(y1)), (int(x2), int(y2)), largura)

    if perfil in ("alto", "medio"):
        qtd = 7 if perfil == "alto" else 4
        for i in range(qtd):
            phase = ((tempo_atual * 0.0022) + i / qtd) % 1.0
            sx = int(ra.centerx + (rb.centerx - ra.centerx) * phase)
            sy = int(ra.centery + (rb.centery - ra.centery) * phase)
            pygame.draw.circle(tela, cor_pulso, (sx, sy), 3 if resultado else 2)
            if perfil == "alto" and resultado:
                pygame.draw.circle(tela, COR_CONDUTORA_FRIA, (sx, sy), 6, 1)

    mid = ((ra.centerx + rb.centerx) // 2, (ra.centery + rb.centery) // 2)
    if idade < 900:
        fonte = _fonte(14, True)
        texto = f"{link.get('porta', '?')}={resultado}"
        surf = fonte.render(texto, True, cor_pulso)
        _texto_contorno(tela, fonte, texto, (mid[0] - surf.get_width() // 2, mid[1] - 18), cor_pulso)
    if resultado and perfil == "alto":
        raio = int(8 + 18 * (1.0 - t))
        pygame.draw.circle(tela, COR_CONDUTORA_CLARA, mid, max(4, raio), 1)


def _desenhar_hud_logico(tela, tempo_atual, perfil):
    estado = _estado_logico()
    w = tela.get_width()
    x = max(390, w - 332)
    y = 86
    largura = 292
    altura = 72
    surf = pygame.Surface((largura, altura), pygame.SRCALPHA)
    pygame.draw.rect(surf, (2, 8, 18, 176), (0, 0, largura, altura), border_radius=8)
    pygame.draw.rect(surf, (*COR_CONDUTORA_FRIA, 160), (0, 0, largura, altura), 1, border_radius=8)
    fonte_titulo = _fonte(12, True)
    fonte_porta = _fonte(24, True)
    fonte_peq = _fonte(13, False)
    surf.blit(fonte_titulo.render("CIRCUITO LOGICO", True, COR_CONDUTORA_FRIA), (12, 8))

    porta = str(estado.get("porta_atual") or "?")
    prox = str(estado.get("proxima_porta") or "?")
    pulso = 0.5 + 0.5 * math.sin(tempo_atual * 0.007)
    cor_atual = COR_CONDUTORA_CLARA if pulso > 0.55 else COR_LOGICO_OK
    pygame.draw.rect(surf, (8, 31, 44, 210), (12, 28, 92, 32), border_radius=6)
    pygame.draw.rect(surf, COR_CONDUTORA, (12, 28, 92, 32), 1, border_radius=6)
    surf.blit(fonte_porta.render(porta, True, cor_atual), (22, 29))
    surf.blit(fonte_porta.render(">", True, COR_CONDUTORA_FRIA), (118, 29))
    pygame.draw.rect(surf, (5, 18, 32, 190), (148, 32, 72, 26), border_radius=6)
    pygame.draw.rect(surf, (40, 126, 155), (148, 32, 72, 26), 1, border_radius=6)
    surf.blit(_fonte(18, True).render(prox, True, (138, 206, 224)), (157, 33))

    entrada = estado.get("entrada_a")
    if _alvo_vivo(entrada):
        bit = garantir_bit_logico(entrada)
        texto = f"A={bit}  aguardando B"
        surf.blit(fonte_peq.render(texto, True, COR_LOGICO_0 if bit == 0 else COR_LOGICO_1), (228, 16))
    elif estado.get("ultimo_feedback") and int(tempo_atual) - int(estado.get("ultimo_resultado_ms", 0)) < 1300:
        resultado = int(estado.get("ultimo_resultado", 0))
        cor = COR_LOGICO_OK if resultado else COR_LOGICO_ERRO
        surf.blit(fonte_peq.render(str(estado.get("ultimo_feedback")), True, cor), (228, 16))

    if int(tempo_atual) < int(estado.get("ruido_fim_ms", 0)):
        resto = max(0.0, (int(estado.get("ruido_fim_ms", 0)) - int(tempo_atual)) / RUIDO_LOGICO_DURACAO_MS)
        for i in range(8 if perfil == "alto" else 4):
            gx = random.randint(2, largura - 14)
            gy = random.randint(2, altura - 8)
            pygame.draw.rect(surf, (*COR_LOGICO_ERRO, int(90 * resto)), (gx, gy, random.randint(4, 12), 2))
        surf.blit(fonte_peq.render("RUIDO LOGICO", True, COR_LOGICO_ERRO), (228, 38))

    tela.blit(surf, (x, y))


def desenhar_circuitos(tela, inimigos, tempo_atual, config_graficos=None, manifestacao=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        _FECHAMENTOS.clear()
        return

    _desenhar_fechamentos_ativos(tela, tempo_atual, perfil)
    if manifestacao is not None and not ativa(manifestacao):
        return

    garantir_bits_logicos(inimigos)
    for link in _links_logicos_vivos(inimigos, tempo_atual):
        _desenhar_link_logico(tela, link, tempo_atual, perfil)

    entrada = _estado_logico().get("entrada_a")
    if _alvo_vivo(entrada):
        rect = entrada["rect"]
        idade = int(tempo_atual) - int(_ESTADO_LOGICO.get("entrada_a_ms", tempo_atual))
        restante = max(0.0, 1.0 - idade / float(ENTRADA_A_DURACAO_MS))
        raio = int(max(rect.width, rect.height) * (0.62 + 0.08 * math.sin(tempo_atual * 0.018)))
        cor = COR_CONDUTORA_FRIA if restante > 0.22 or int(tempo_atual / 120) % 2 == 0 else COR_LOGICO_ERRO
        pygame.draw.circle(tela, (4, 13, 24), rect.center, raio + 4, 2)
        pygame.draw.circle(tela, cor, rect.center, raio, 2)

    for alvo in inimigos or []:
        if _alvo_vivo(alvo):
            _desenhar_bit_logico(tela, alvo, tempo_atual, perfil)

    _desenhar_hud_logico(tela, tempo_atual, perfil)


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
