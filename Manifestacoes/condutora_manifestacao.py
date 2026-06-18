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

PORTAS_LOGICAS = ("OR", "AND", "XOR", "NAND", "NOR")
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

LIMITE_ERROS_TROCAR_PORTA = 2
JANELA_LINK_CORRETO_MS = 2500
JANELA_TELEPORTE_CONDUTOR_MS = 2500
COOLDOWN_REGISTRADOR_INSTAVEL = 11000
COOLDOWN_FALHA_REGISTRADOR = 3500
REGISTRADOR_ROLETAGEM_MS = 3000
REGISTRADOR_QUEDA_MS = 520
REGISTRADOR_RETORNO_SLOW_MS = 2000
REGISTRADOR_SLOW_INICIAL = 0.35
DURACAO_BUFF_REGISTRADOR = 5500
DURACAO_BUFF_D = 6000
BONUS_DURACAO_D_COM_TELEPORTE = 0.25
DURACAO_BUFF_T = 5500
BONUS_T_COM_TELEPORTE = 0.20
DURACAO_BUFF_JK = 6000
BONUS_JK_TOGGLE = 0.25
DURACAO_SOBRECARGA_RS = 2500
PENALIDADE_COOLDOWN_RS = 1000
BUFF_Q_DANO_LOGICO = 0.20
BUFF_Q_CORRENTE_EXTRA = 1
BUFF_Q_CADENCIA = 0.10
BUFF_Q_LINHA_INIMIGOS = 0.20
BUFF_Q_REDUCAO_RUIDO = 0.30
BUFF_Q_ESCUDO_HITS = 1

BUFFS_LOGICOS = {
    "OR": {"duracao": 5000, "bonus_area_corrente": 0.35, "bonus_por_stack": 0.15},
    "AND": {"duracao": 5000, "bonus_dano": 0.25, "bonus_por_stack": 0.10},
    "XOR": {"duracao": 5000, "bonus_velocidade": 0.20, "bonus_cadencia": 0.20, "bonus_por_stack": 0.08},
    "NAND": {"duracao": 4500, "escudo_hits": 1, "reducao_dano": 1.0},
    "NOR": {"duracao": 4500, "lentidao_inimigos": 0.35, "raio_lentidao": 260}
}

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
    "buff_logico_ativo": None,
    "buff_logico_inicio": 0,
    "buff_logico_duracao": 0,
    "buff_logico_stacks": 0,
    "ultimo_compilado_sucesso": False,
    "contador_erros_porta_atual": 0,
    "ultimo_link_correto_ms": 0,
    "ultimo_link_correto_porta": None,
    "ultimo_teleporte_condutor_ms": 0,
    "registrador_tipo_atual": None,
    "registrador_repeticoes": 0,
    "registrador_estado_q": True,
    "registrador_buff_ativo": None,
    "registrador_buff_inicio": 0,
    "registrador_buff_duracao": 0,
    "registrador_ultimo_uso": 0,
    "registrador_stacks": 0,
    "registrador_porta_capturada": None,
    "registrador_feedback": "",
    "registrador_feedback_ms": 0,
    "registrador_cooldown_ms": COOLDOWN_REGISTRADOR_INSTAVEL,
    "registrador_sobrecarga_fim_ms": 0,
    "registrador_pulso": None,
    "registrador_animacao_ativa": False,
    "registrador_animacao_inicio_ms": 0,
    "registrador_animacao_fim_ms": 0,
    "registrador_combo": [],
    "registrador_tipo_pendente": None,
    "registrador_links_pendentes": [],
    "registrador_link_correto_pendente": False,
    "registrador_teleporte_pendente": False,
    "registrador_dano_pendente": 0.0,
    "registrador_disparo_bloqueado_ate": 0,
    "registrador_slow_fim_ms": 0,
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


def obter_raio_conexao_atual():
    global _ESTADO_LOGICO
    tempo_atual = pygame.time.get_ticks()
    multiplicador = 1.0
    if _ESTADO_LOGICO.get("buff_logico_ativo") == "OR" and tempo_atual - _ESTADO_LOGICO.get("buff_logico_inicio", 0) < _ESTADO_LOGICO.get("buff_logico_duracao", 0):
        stacks = _ESTADO_LOGICO.get("buff_logico_stacks", 1)
        multiplicador += 0.35 + (stacks - 1) * 0.15
    return FIO_RAIO_CONEXAO * multiplicador

def obter_largura_dano_atual():
    global _ESTADO_LOGICO
    tempo_atual = pygame.time.get_ticks()
    multiplicador = 1.0
    if _ESTADO_LOGICO.get("buff_logico_ativo") == "OR" and tempo_atual - _ESTADO_LOGICO.get("buff_logico_inicio", 0) < _ESTADO_LOGICO.get("buff_logico_duracao", 0):
        stacks = _ESTADO_LOGICO.get("buff_logico_stacks", 1)
        multiplicador += 0.35 + (stacks - 1) * 0.15
    return FIO_LARGURA_DANO * multiplicador

def _conexoes(marcados):
    candidatos = []
    for i, a in enumerate(marcados):
        for b in marcados[i + 1:]:
            dist = _distancia(a, b)
            if dist <= obter_raio_conexao_atual():
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
            if dist_linha > obter_largura_dano_atual() + min(rect.width, rect.height) * 0.25:
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
    if evitar in PORTAS_LOGICAS:
        idx = PORTAS_LOGICAS.index(evitar)
        return PORTAS_LOGICAS[(idx + 1) % len(PORTAS_LOGICAS)]
    return random.choice(PORTAS_LOGICAS)


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
        "contador_erros_porta_atual": 0,
        "ultimo_link_correto_ms": 0,
        "ultimo_link_correto_porta": None,
        "ultimo_teleporte_condutor_ms": 0,
        "registrador_tipo_atual": None,
        "registrador_repeticoes": 0,
        "registrador_estado_q": True,
        "registrador_buff_ativo": None,
        "registrador_buff_inicio": 0,
        "registrador_buff_duracao": 0,
        "registrador_ultimo_uso": 0,
        "registrador_stacks": 0,
        "registrador_porta_capturada": None,
        "registrador_feedback": "",
        "registrador_feedback_ms": 0,
        "registrador_cooldown_ms": COOLDOWN_REGISTRADOR_INSTAVEL,
        "registrador_sobrecarga_fim_ms": 0,
        "registrador_pulso": None,
        "registrador_animacao_ativa": False,
        "registrador_animacao_inicio_ms": 0,
        "registrador_animacao_fim_ms": 0,
        "registrador_combo": [],
        "registrador_tipo_pendente": None,
        "registrador_links_pendentes": [],
        "registrador_link_correto_pendente": False,
        "registrador_teleporte_pendente": False,
        "registrador_dano_pendente": 0.0,
        "registrador_disparo_bloqueado_ate": 0,
        "registrador_slow_fim_ms": 0,
    })
    _ESTADO_LOGICO["proxima_porta"] = _sortear_porta(_ESTADO_LOGICO["porta_atual"])


def _avancar_porta():
    estado = _estado_logico()
    usada = estado["porta_atual"]
    estado["porta_atual"] = estado["proxima_porta"]
    estado["proxima_porta"] = _sortear_porta(estado["porta_atual"])
    estado["contador_erros_porta_atual"] = 0
    return usada


def _porta_atual():
    estado = _estado_logico()
    return estado.get("porta_atual") or _sortear_porta(None)


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


def _registrar_erro_porta(tempo_atual, efeitos_texto, rect_feedback=None):
    estado = _estado_logico()
    erros = int(estado.get("contador_erros_porta_atual", 0)) + 1
    estado["contador_erros_porta_atual"] = erros
    if erros >= LIMITE_ERROS_TROCAR_PORTA:
        _avancar_porta()
        texto = "ERRO LOGICO 2/2 - PROXIMA PORTA"
    else:
        texto = f"ERRO LOGICO {erros}/{LIMITE_ERROS_TROCAR_PORTA}"
    _registrar_feedback(texto, 0, tempo_atual)
    _texto(efeitos_texto, texto, rect_feedback, tempo_atual, COR_LOGICO_ERRO)


def _registrar_acerto_porta(porta, tempo_atual):
    estado = _estado_logico()
    estado["contador_erros_porta_atual"] = 0
    estado["ultimo_link_correto_ms"] = int(tempo_atual)
    estado["ultimo_link_correto_porta"] = porta
    _avancar_porta()


def registrar_teleporte_condutor(tempo_atual):
    estado = _estado_logico()
    estado["ultimo_teleporte_condutor_ms"] = int(tempo_atual)


def teleporte_condutor_recente(tempo_atual):
    estado = _estado_logico()
    return int(tempo_atual) - int(estado.get("ultimo_teleporte_condutor_ms", 0)) <= JANELA_TELEPORTE_CONDUTOR_MS


def link_correto_recente(inimigos, tempo_atual):
    estado = _estado_logico()
    if _links_logicos_vivos(inimigos, tempo_atual, apenas_corretos=True):
        return True
    return int(tempo_atual) - int(estado.get("ultimo_link_correto_ms", 0)) <= JANELA_LINK_CORRETO_MS


def _escolher_flip_flop():
    estado = _estado_logico()
    anterior = estado.get("registrador_tipo_atual")
    repeticoes = int(estado.get("registrador_repeticoes", 0))
    opcoes = ["D", "T", "RS", "JK"]
    if anterior in opcoes and repeticoes >= 2:
        opcoes = [tipo for tipo in opcoes if tipo != anterior]
    escolhido = random.choice(opcoes)
    estado["registrador_repeticoes"] = repeticoes + 1 if escolhido == anterior else 1
    estado["registrador_tipo_atual"] = escolhido
    return escolhido


def _registrador_buff_ativo(tempo_atual):
    estado = _estado_logico()
    buff = estado.get("registrador_buff_ativo")
    if not buff:
        return None
    if int(tempo_atual) - int(estado.get("registrador_buff_inicio", 0)) >= int(estado.get("registrador_buff_duracao", 0)):
        estado["registrador_buff_ativo"] = None
        estado["registrador_stacks"] = 0
        return None
    return buff


def _aplicar_buff_registrador(nome, estado_q, duracao, tempo_atual, stacks=1, porta=None, feedback=None):
    estado = _estado_logico()
    estado["registrador_estado_q"] = bool(estado_q)
    estado["registrador_buff_ativo"] = nome
    estado["registrador_buff_inicio"] = int(tempo_atual)
    estado["registrador_buff_duracao"] = int(duracao)
    estado["registrador_stacks"] = max(1, int(stacks))
    if porta:
        estado["registrador_porta_capturada"] = porta
    estado["registrador_feedback"] = feedback or nome
    estado["registrador_feedback_ms"] = int(tempo_atual)


def _registrar_falha_registrador(texto, tempo_atual, efeitos_texto, jogador_rect):
    estado = _estado_logico()
    estado["registrador_feedback"] = texto
    estado["registrador_feedback_ms"] = int(tempo_atual)
    estado["registrador_cooldown_ms"] = COOLDOWN_FALHA_REGISTRADOR
    _registrar_feedback(texto, 0, tempo_atual)
    if jogador_rect is not None and efeitos_texto is not None:
        efeitos_texto.append({
            "texto": texto,
            "x": jogador_rect.centerx,
            "y": jogador_rect.top - 35,
            "tempo_inicio": int(tempo_atual),
            "cor": COR_LOGICO_ERRO,
        })


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
    porta = _porta_atual()
    resultado = _avaliar_porta(porta, bit_a, bit_b)
    cor = COR_LOGICO_OK if resultado else COR_LOGICO_ERRO
    mult = LINK_RESULTADO_1_MULT if resultado else LINK_RESULTADO_0_MULT
    mult *= obter_multiplicador_dano_logico(agora)
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
        _registrar_erro_porta(agora, efeitos_texto, alvo.get("rect"))
    else:
        _registrar_acerto_porta(porta, agora)

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
    if resultado:
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
    for morto in _atualizar_roleta_registrador(inimigos, tempo_atual, dano_base, efeitos_texto):
        if morto not in mortos:
            mortos.append(morto)
    for link in _links_logicos_vivos(inimigos, tempo_atual):
        if int(link.get("resultado", 0)) != 1:
            continue
        if int(tempo_atual) - int(link.get("ultimo_tick_ms", 0)) < LINK_LOGICO_TICK_MS:
            continue
        link["ultimo_tick_ms"] = int(tempo_atual)
        dano = float(link.get("dano_base", dano_base)) * LINK_LOGICO_TICK_MULT * obter_multiplicador_dano_logico(tempo_atual)
        for alvo in (link.get("a"), link.get("b")):
            if _aplicar_dano_logico(alvo, dano, tempo_atual, efeitos_texto, COR_CONDUTORA_FRIA) and alvo not in mortos:
                mortos.append(alvo)
        saltos_extra = bonus_corrente_registrador(tempo_atual)
        if saltos_extra > 0:
            conectados = [alvo for alvo in (link.get("a"), link.get("b")) if _alvo_vivo(alvo)]
            candidatos = []
            for inimigo in inimigos or []:
                if not _alvo_vivo(inimigo) or inimigo in conectados:
                    continue
                menor_dist = min((_distancia(inimigo, alvo) for alvo in conectados), default=999999.0)
                if menor_dist <= FIO_RAIO_CONEXAO:
                    candidatos.append((menor_dist, inimigo))
            candidatos.sort(key=lambda item: item[0])
            for _, alvo_extra in candidatos[:saltos_extra]:
                if _aplicar_dano_logico(alvo_extra, dano * 0.55, tempo_atual, efeitos_texto, COR_CONDUTORA) and alvo_extra not in mortos:
                    mortos.append(alvo_extra)
    return mortos


_som_ruido_logico = None

def _tocar_som_ruido():
    global _som_ruido_logico
    try:
        import sons_procedurais
        if _som_ruido_logico is None:
            _som_ruido_logico = sons_procedurais.gerar_som_beep(220, 110, 0.28, volume=0.75)
        if _som_ruido_logico:
            _som_ruido_logico.play()
    except Exception:
        try:
            # Fallback to play Estalo
            pygame.mixer.Sound("Sounds/Estalo.mp3").play()
        except Exception:
            pass

def obter_multiplicador_dano_and(tempo_atual):
    global _ESTADO_LOGICO
    mult = obter_multiplicador_dano_logico(tempo_atual)
    if _ESTADO_LOGICO.get("buff_logico_ativo") == "AND" and tempo_atual - _ESTADO_LOGICO.get("buff_logico_inicio", 0) < _ESTADO_LOGICO.get("buff_logico_duracao", 0):
        stacks = _ESTADO_LOGICO.get("buff_logico_stacks", 1)
        mult *= 1.0 + 0.25 + (stacks - 1) * 0.10
    return mult

def obter_fator_velocidade_xor(tempo_atual):
    global _ESTADO_LOGICO
    mult = 1.0
    if _ESTADO_LOGICO.get("buff_logico_ativo") == "XOR" and tempo_atual - _ESTADO_LOGICO.get("buff_logico_inicio", 0) < _ESTADO_LOGICO.get("buff_logico_duracao", 0):
        stacks = _ESTADO_LOGICO.get("buff_logico_stacks", 1)
        mult *= 1.0 + 0.20 + (stacks - 1) * 0.08
    if _registrador_buff_ativo(tempo_atual) in ("D_XOR",):
        mult *= 1.10
    return mult

def obter_fator_cadencia_xor(tempo_atual):
    global _ESTADO_LOGICO
    mult = 1.0
    if _ESTADO_LOGICO.get("buff_logico_ativo") == "XOR" and tempo_atual - _ESTADO_LOGICO.get("buff_logico_inicio", 0) < _ESTADO_LOGICO.get("buff_logico_duracao", 0):
        stacks = _ESTADO_LOGICO.get("buff_logico_stacks", 1)
        mult *= 1.0 + 0.20 + (stacks - 1) * 0.08
    buff = _registrador_buff_ativo(tempo_atual)
    if buff in ("Q", "JK_Q", "T_Q"):
        mult *= 1.0 + BUFF_Q_CADENCIA
    elif buff == "D_XOR":
        mult *= 1.15
    return mult

def tentar_absorver_dano_nand(tempo_atual):
    global _ESTADO_LOGICO
    if _registrador_buff_ativo(tempo_atual) in ("Q_DEF", "JK_Q_DEF", "T_Q_DEF", "RS_RESET", "D_NAND"):
        stacks = int(_ESTADO_LOGICO.get("registrador_stacks", 0))
        if stacks > 0:
            _ESTADO_LOGICO["registrador_stacks"] = stacks - 1
            if _ESTADO_LOGICO["registrador_stacks"] <= 0:
                _ESTADO_LOGICO["registrador_buff_ativo"] = None
            return True
    if _ESTADO_LOGICO.get("buff_logico_ativo") == "NAND" and tempo_atual - _ESTADO_LOGICO.get("buff_logico_inicio", 0) < _ESTADO_LOGICO.get("buff_logico_duracao", 0):
        stacks = _ESTADO_LOGICO.get("buff_logico_stacks", 1)
        if stacks > 0:
            _ESTADO_LOGICO["buff_logico_stacks"] = stacks - 1
            if _ESTADO_LOGICO["buff_logico_stacks"] == 0:
                _ESTADO_LOGICO["buff_logico_ativo"] = None
            return True
    return False

def obter_fator_lentidao_inimigo(inimigo, pos_jogador):
    global _ESTADO_LOGICO
    tempo_atual = pygame.time.get_ticks()
    fator = 1.0
    if _ESTADO_LOGICO.get("buff_logico_ativo") == "NOR" and tempo_atual - _ESTADO_LOGICO.get("buff_logico_inicio", 0) < _ESTADO_LOGICO.get("buff_logico_duracao", 0):
        rect = inimigo.get("rect")
        if rect:
            dist = math.hypot(rect.centerx - pos_jogador[0], rect.centery - pos_jogador[1])
            if dist <= BUFFS_LOGICOS["NOR"]["raio_lentidao"]:
                fator = min(fator, 1.0 - BUFFS_LOGICOS["NOR"]["lentidao_inimigos"])
    buff = _registrador_buff_ativo(tempo_atual)
    if buff in ("Q_DEF", "JK_Q_DEF", "T_Q_DEF", "RS_RESET", "D_NOR"):
        rect = inimigo.get("rect")
        if rect:
            dist = math.hypot(rect.centerx - pos_jogador[0], rect.centery - pos_jogador[1])
            if dist <= BUFFS_LOGICOS["NOR"]["raio_lentidao"]:
                fator = min(fator, 1.0 - BUFF_Q_LINHA_INIMIGOS)
    return fator

def obter_multiplicador_cooldown():
    global _ESTADO_LOGICO
    success = _ESTADO_LOGICO.get("ultimo_compilado_sucesso", False)
    return 0.90 if success else 0.30

def obter_multiplicador_dano_logico(tempo_atual):
    buff = _registrador_buff_ativo(tempo_atual)
    if buff in ("Q", "JK_Q", "T_Q", "RS_SET"):
        return 1.0 + BUFF_Q_DANO_LOGICO
    if buff == "D_AND":
        return 1.25
    return 1.0

def bonus_corrente_registrador(tempo_atual):
    buff = _registrador_buff_ativo(tempo_atual)
    if buff in ("Q", "JK_Q", "T_Q", "RS_SET", "D_OR"):
        return BUFF_Q_CORRENTE_EXTRA
    return 0

def fator_ruido_logico(manifestacao, tempo_atual):
    if not ativa(manifestacao):
        return 1.0
    estado = _estado_logico()
    if int(tempo_atual) >= int(estado.get("ruido_fim_ms", 0)):
        return 1.0
    fator = RUIDO_LOGICO_VELOCIDADE_MULT
    if _registrador_buff_ativo(tempo_atual) in ("Q_DEF", "JK_Q_DEF", "T_Q_DEF", "RS_RESET"):
        fator = 1.0 - ((1.0 - fator) * (1.0 - BUFF_Q_REDUCAO_RUIDO))
    return fator

def multiplicador_cooldown_habilidade(manifestacao):
    return 1.1 if ativa(manifestacao) else 1.0

def cooldown_registrador_atual():
    return int(_estado_logico().get("registrador_cooldown_ms", COOLDOWN_REGISTRADOR_INSTAVEL))

def ajustar_inicio_cooldown_registrador(tempo_atual, cooldown_base_ms):
    cooldown_base_ms = max(1, int(cooldown_base_ms or COOLDOWN_REGISTRADOR_INSTAVEL))
    cooldown_real = max(1, cooldown_registrador_atual())
    return int(tempo_atual) - max(0, cooldown_base_ms - cooldown_real)

def fechar_circuitos(inimigos, tempo_atual, dano_base, efeitos_texto=None, jogador_rect=None):
    global _ESTADO_LOGICO
    links = _links_logicos_vivos(inimigos, tempo_atual, apenas_corretos=True)
    if not links:
        _ESTADO_LOGICO["ultimo_compilado_sucesso"] = False
        _ESTADO_LOGICO["ruido_fim_ms"] = int(tempo_atual) + RUIDO_LOGICO_DURACAO_MS
        _registrar_feedback("Sem circuito correto", 0, tempo_atual)
        _tocar_som_ruido()
        if jogador_rect is not None and efeitos_texto is not None:
            efeitos_texto.append({
                "texto": "RUÍDO LÓGICO",
                "x": jogador_rect.centerx,
                "y": jogador_rect.top - 35,
                "tempo_inicio": int(tempo_atual),
                "cor": COR_LOGICO_ERRO
            })
        _FECHAMENTOS.append({
            "tempo_inicio": int(tempo_atual),
            "fim_ms": int(tempo_atual) + FECHAMENTO_DURACAO_MS,
            "pontos": [],
            "links": [],
            "forte": False,
            "total": 0,
        })
        return [], 0, 0

    _ESTADO_LOGICO["ultimo_compilado_sucesso"] = True
    contagem = {}
    for link in links:
        porta = link.get("porta")
        if porta:
            contagem[porta] = contagem.get(porta, 0) + 1

    prioridade = {"NOR": 5, "NAND": 4, "AND": 3, "XOR": 2, "OR": 1}
    def criterio(porta):
        return (contagem[porta], prioridade.get(porta, 0))

    chosen_gate = max(contagem.keys(), key=criterio)
    old_buff = _ESTADO_LOGICO.get("buff_logico_ativo")
    if old_buff == chosen_gate:
        stacks = min(3, _ESTADO_LOGICO.get("buff_logico_stacks", 1) + 1)
        _ESTADO_LOGICO["buff_logico_stacks"] = stacks
        _ESTADO_LOGICO["buff_logico_inicio"] = int(tempo_atual)
        _ESTADO_LOGICO["buff_logico_duracao"] = BUFFS_LOGICOS[chosen_gate]["duracao"]
        txt = f"{chosen_gate} STACK {stacks}"
    else:
        _ESTADO_LOGICO["buff_logico_ativo"] = chosen_gate
        _ESTADO_LOGICO["buff_logico_stacks"] = 1
        _ESTADO_LOGICO["buff_logico_inicio"] = int(tempo_atual)
        _ESTADO_LOGICO["buff_logico_duracao"] = BUFFS_LOGICOS[chosen_gate]["duracao"]
        txt = f"COMPILAÇÃO: {chosen_gate}"

    if jogador_rect is not None and efeitos_texto is not None:
        efeitos_texto.append({
            "texto": txt,
            "x": jogador_rect.centerx,
            "y": jogador_rect.top - 35,
            "tempo_inicio": int(tempo_atual),
            "cor": COR_LOGICO_OK
        })

    dano_por_alvo = {}
    pontos = []
    linhas = []
    mult = min(1.75, 1.0 + 0.12 * len(links))
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


def _resolver_registrador_instavel(
    inimigos,
    tempo_atual,
    dano_base,
    efeitos_texto=None,
    jogador_rect=None,
    teleporte_recente=None,
    tipo_forcado=None,
    links_preparados=None,
    link_correto_preparado=None,
):
    """Clock do Registrador Instavel da Condutora."""
    estado = _estado_logico()
    agora = int(tempo_atual)
    links = list(links_preparados) if links_preparados is not None else _links_logicos_vivos(inimigos, agora, apenas_corretos=True)
    link_correto = (
        bool(link_correto_preparado)
        if link_correto_preparado is not None
        else bool(links) or agora - int(estado.get("ultimo_link_correto_ms", 0)) <= JANELA_LINK_CORRETO_MS
    )
    teleporte_recente = teleporte_condutor_recente(agora) if teleporte_recente is None else bool(teleporte_recente)
    tipo = tipo_forcado or _escolher_flip_flop()
    estado["registrador_ultimo_uso"] = agora
    estado["registrador_cooldown_ms"] = COOLDOWN_REGISTRADOR_INSTAVEL
    estado["ultimo_compilado_sucesso"] = bool(link_correto or teleporte_recente)
    pontos = []
    linhas = []
    mortos = []
    for link in links:
        a = link.get("a")
        b = link.get("b")
        if _alvo_vivo(a):
            pontos.append(a["rect"].center)
        if _alvo_vivo(b):
            pontos.append(b["rect"].center)
        if _alvo_vivo(a) and _alvo_vivo(b):
            linhas.append((a["rect"].center, b["rect"].center))

    def feedback(texto, cor=COR_LOGICO_OK):
        estado["registrador_feedback"] = texto
        estado["registrador_feedback_ms"] = agora
        _registrar_feedback(texto, 1, agora)
        if jogador_rect is not None and efeitos_texto is not None:
            efeitos_texto.append({
                "texto": texto,
                "x": jogador_rect.centerx,
                "y": jogador_rect.top - 35,
                "tempo_inicio": agora,
                "cor": cor,
            })

    def aplicar_estado(nome, q, duracao, texto, stacks=1, porta=None, bonus=1.0):
        _aplicar_buff_registrador(nome, q, int(duracao * bonus), agora, stacks=stacks, porta=porta, feedback=texto)
        feedback(texto, COR_LOGICO_OK if q else COR_CONDUTORA_FRIA)

    if tipo == "D":
        porta = None
        if links:
            contagem = {}
            for link in links:
                porta_link = link.get("porta")
                if porta_link:
                    contagem[porta_link] = contagem.get(porta_link, 0) + 1
            if contagem:
                prioridade = {"NOR": 5, "NAND": 4, "AND": 3, "XOR": 2, "OR": 1}
                porta = max(contagem.keys(), key=lambda p: (contagem[p], prioridade.get(p, 0)))
        if porta is None:
            porta = estado.get("ultimo_link_correto_porta") if link_correto else estado.get("porta_atual")
        if porta not in BUFFS_LOGICOS:
            _registrar_falha_registrador("SEM SINAL LOGICO", agora, efeitos_texto, jogador_rect)
            _tocar_som_ruido()
            return [], 0, 0
        aplicar_estado(
            f"D_{porta}",
            porta not in ("NAND", "NOR"),
            DURACAO_BUFF_D,
            f"D CAPTUROU: {porta}",
            stacks=BUFF_Q_ESCUDO_HITS if porta == "NAND" else 1,
            porta=porta,
            bonus=1.0 + (BONUS_DURACAO_D_COM_TELEPORTE if teleporte_recente else 0.0),
        )
    elif tipo == "T":
        if not link_correto:
            _registrar_falha_registrador("T: SEM TOGGLE", agora, efeitos_texto, jogador_rect)
            return [], 0, 0
        novo_q = not bool(estado.get("registrador_estado_q", True))
        aplicar_estado(
            "T_Q" if novo_q else "T_Q_DEF",
            novo_q,
            DURACAO_BUFF_T,
            "T: TOGGLE -> Q" if novo_q else "T: TOGGLE -> Q'",
            stacks=1 if novo_q else BUFF_Q_ESCUDO_HITS,
            bonus=1.0 + (BONUS_T_COM_TELEPORTE if teleporte_recente else 0.0),
        )
    elif tipo == "RS":
        if link_correto and not teleporte_recente:
            aplicar_estado("RS_SET", True, DURACAO_BUFF_REGISTRADOR, "RS: SET")
        elif teleporte_recente and not link_correto:
            estado["ruido_fim_ms"] = 0
            aplicar_estado("RS_RESET", False, DURACAO_BUFF_REGISTRADOR, "RS: RESET", stacks=BUFF_Q_ESCUDO_HITS)
        elif link_correto and teleporte_recente:
            estado["registrador_cooldown_ms"] = COOLDOWN_REGISTRADOR_INSTAVEL + PENALIDADE_COOLDOWN_RS
            estado["registrador_sobrecarga_fim_ms"] = agora + DURACAO_SOBRECARGA_RS
            estado["ruido_fim_ms"] = agora + RUIDO_LOGICO_DURACAO_MS
            feedback("RS: SOBRECARGA", COR_LOGICO_ERRO)
            alvos = {}
            for link in links:
                for alvo in (link.get("a"), link.get("b")):
                    if _alvo_vivo(alvo):
                        alvos[id(alvo)] = alvo
            for alvo in alvos.values():
                if _aplicar_dano_logico(alvo, float(dano_base) * 0.65, agora, efeitos_texto, COR_LOGICO_ERRO) and alvo not in mortos:
                    mortos.append(alvo)
        else:
            _registrar_falha_registrador("SEM SINAL LOGICO", agora, efeitos_texto, jogador_rect)
            return [], 0, 0
    elif tipo == "JK":
        if link_correto and not teleporte_recente:
            aplicar_estado("JK_Q", True, DURACAO_BUFF_JK, "JK: SET")
        elif teleporte_recente and not link_correto:
            aplicar_estado("JK_Q_DEF", False, DURACAO_BUFF_JK, "JK: RESET", stacks=BUFF_Q_ESCUDO_HITS)
        elif link_correto and teleporte_recente:
            novo_q = not bool(estado.get("registrador_estado_q", True))
            aplicar_estado(
                "JK_Q" if novo_q else "JK_Q_DEF",
                novo_q,
                DURACAO_BUFF_JK,
                "JK: TOGGLE -> Q" if novo_q else "JK: TOGGLE -> Q'",
                stacks=1 if novo_q else BUFF_Q_ESCUDO_HITS,
                bonus=1.0 + BONUS_JK_TOGGLE,
            )
        else:
            _registrar_falha_registrador("SEM SINAL LOGICO", agora, efeitos_texto, jogador_rect)
            return [], 0, 0

    total_alvos = len(set(pontos))
    _FECHAMENTOS.append({
        "tempo_inicio": agora,
        "fim_ms": agora + FECHAMENTO_DURACAO_MS,
        "pontos": pontos,
        "links": linhas,
        "forte": bool(link_correto or teleporte_recente),
        "total": total_alvos,
    })
    return mortos, total_alvos, len(links)


def _combo_roleta_registrador(tipo):
    opcoes = ["D", "T", "RS", "JK"]
    return [random.choice(opcoes), tipo, random.choice(opcoes)]


def fechar_circuitos(inimigos, tempo_atual, dano_base, efeitos_texto=None, jogador_rect=None, teleporte_recente=None):
    """Inicia a roleta visual do Registrador; o efeito resolve apos 3s."""
    estado = _estado_logico()
    agora = int(tempo_atual)
    if estado.get("registrador_animacao_ativa"):
        return [], 0, 0

    links = _links_logicos_vivos(inimigos, agora, apenas_corretos=True)
    link_correto = bool(links) or agora - int(estado.get("ultimo_link_correto_ms", 0)) <= JANELA_LINK_CORRETO_MS
    teleporte_ok = teleporte_condutor_recente(agora) if teleporte_recente is None else bool(teleporte_recente)
    tipo = _escolher_flip_flop()
    combo = _combo_roleta_registrador(tipo)

    estado["registrador_animacao_ativa"] = True
    estado["registrador_animacao_inicio_ms"] = agora
    estado["registrador_animacao_fim_ms"] = agora + REGISTRADOR_ROLETAGEM_MS
    estado["registrador_combo"] = combo
    estado["registrador_tipo_pendente"] = tipo
    estado["registrador_links_pendentes"] = list(links)
    estado["registrador_link_correto_pendente"] = bool(link_correto)
    estado["registrador_teleporte_pendente"] = bool(teleporte_ok)
    estado["registrador_dano_pendente"] = float(dano_base)
    estado["registrador_cooldown_ms"] = COOLDOWN_REGISTRADOR_INSTAVEL
    estado["registrador_disparo_bloqueado_ate"] = agora + REGISTRADOR_ROLETAGEM_MS + REGISTRADOR_RETORNO_SLOW_MS
    estado["registrador_slow_fim_ms"] = agora + REGISTRADOR_ROLETAGEM_MS + REGISTRADOR_RETORNO_SLOW_MS
    estado["registrador_feedback"] = "REGISTRADOR GIRANDO"
    estado["registrador_feedback_ms"] = agora
    _registrar_feedback("REGISTRADOR: ???", 1, agora)
    if jogador_rect is not None and efeitos_texto is not None:
        efeitos_texto.append({
            "texto": "REGISTRADOR INSTAVEL",
            "x": jogador_rect.centerx,
            "y": jogador_rect.top - 35,
            "tempo_inicio": agora,
            "cor": COR_CONDUTORA_FRIA,
        })
    return [], 0, len(links)


def _atualizar_roleta_registrador(inimigos, tempo_atual, dano_base, efeitos_texto=None):
    estado = _estado_logico()
    if not estado.get("registrador_animacao_ativa"):
        return []
    agora = int(tempo_atual)
    if agora < int(estado.get("registrador_animacao_fim_ms", 0)):
        return []

    estado["registrador_animacao_ativa"] = False
    tipo = estado.get("registrador_tipo_pendente") or "D"
    links = list(estado.get("registrador_links_pendentes") or [])
    dano_resolucao = float(estado.get("registrador_dano_pendente") or dano_base)
    mortos, _total_alvos, _total_links = _resolver_registrador_instavel(
        inimigos,
        agora,
        dano_resolucao,
        efeitos_texto,
        None,
        teleporte_recente=bool(estado.get("registrador_teleporte_pendente", False)),
        tipo_forcado=tipo,
        links_preparados=links,
        link_correto_preparado=bool(estado.get("registrador_link_correto_pendente", False)),
    )
    estado["registrador_links_pendentes"] = []
    estado["registrador_tipo_pendente"] = None
    estado["registrador_feedback"] = f"REGISTRADOR: {tipo}"
    estado["registrador_feedback_ms"] = agora
    return mortos


def disparo_bloqueado_registrador(manifestacao, tempo_atual):
    if not ativa(manifestacao):
        return False
    estado = _estado_logico()
    return estado.get("registrador_animacao_ativa") or int(tempo_atual) < int(estado.get("registrador_disparo_bloqueado_ate", 0))


def fator_tempo_registrador(manifestacao, tempo_atual):
    if not ativa(manifestacao):
        return 1.0
    estado = _estado_logico()
    agora = int(tempo_atual)
    if estado.get("registrador_animacao_ativa"):
        return REGISTRADOR_SLOW_INICIAL
    slow_fim = int(estado.get("registrador_slow_fim_ms", 0))
    anim_fim = int(estado.get("registrador_animacao_fim_ms", 0))
    if agora < slow_fim and slow_fim > anim_fim:
        progresso = max(0.0, min(1.0, (agora - anim_fim) / float(slow_fim - anim_fim)))
        return REGISTRADOR_SLOW_INICIAL + (1.0 - REGISTRADOR_SLOW_INICIAL) * progresso
    return 1.0


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
    barra_vida_y = rect.top - 14
    cy = max(tam + 2, barra_vida_y - tam - 5)
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
    altura = 104
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
    erros = int(estado.get("contador_erros_porta_atual", 0))
    surf.blit(fonte_peq.render(f"erros {erros}/{LIMITE_ERROS_TROCAR_PORTA}", True, (170, 220, 230)), (12, 66))

    tipo = str(estado.get("registrador_tipo_atual") or "?")
    q_txt = "Q" if estado.get("registrador_estado_q", True) else "Q'"
    porta_cap = estado.get("registrador_porta_capturada") or "-"
    buff_reg = _registrador_buff_ativo(tempo_atual) or "-"
    surf.blit(fonte_peq.render(f"FF:{tipo}  Estado:{q_txt}  Porta:{porta_cap}", True, COR_CONDUTORA_CLARA), (112, 66))
    surf.blit(fonte_peq.render(f"Buff: {buff_reg}", True, COR_CONDUTORA_FRIA), (112, 84))

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

    if estado.get("registrador_feedback") and int(tempo_atual) - int(estado.get("registrador_feedback_ms", 0)) < 1500:
        surf.blit(fonte_peq.render(str(estado.get("registrador_feedback")), True, COR_LOGICO_OK), (12, 84))

    tela.blit(surf, (x, y))


def _desenhar_roleta_registrador(tela, tempo_atual, perfil):
    estado = _estado_logico()
    if not estado.get("registrador_animacao_ativa"):
        return
    inicio = int(estado.get("registrador_animacao_inicio_ms", tempo_atual))
    fim = int(estado.get("registrador_animacao_fim_ms", tempo_atual))
    agora = int(tempo_atual)
    duracao = max(1, fim - inicio)
    progresso = max(0.0, min(1.0, (agora - inicio) / float(duracao)))
    queda = max(0.0, min(1.0, (agora - inicio) / float(REGISTRADOR_QUEDA_MS)))
    queda = 1.0 - (1.0 - queda) ** 3
    largura_tela, altura_tela = tela.get_size()
    reel_w, reel_h = 112, 118
    gap = 18
    total_w = reel_w * 3 + gap * 2
    base_x = largura_tela // 2 - total_w // 2
    alvo_y = altura_tela // 2 - reel_h // 2 - 42
    y = int(-reel_h - 24 + (alvo_y + reel_h + 24) * queda)
    combo = estado.get("registrador_combo") or ["D", "T", "RS"]
    opcoes = ["D", "T", "RS", "JK"]
    fonte_titulo = _fonte(18, True)
    fonte_reel = _fonte(42, True)
    fonte_peq = _fonte(14, True)

    overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
    alpha = 72 if perfil == "baixo" else 104
    overlay.fill((0, 0, 0, alpha))
    tela.blit(overlay, (0, 0))

    titulo = fonte_titulo.render("REGISTRADOR INSTAVEL", True, COR_CONDUTORA_FRIA)
    tela.blit(titulo, (largura_tela // 2 - titulo.get_width() // 2, y - 42))

    for i in range(3):
        x = base_x + i * (reel_w + gap)
        rect = pygame.Rect(x, y, reel_w, reel_h)
        pygame.draw.rect(tela, (5, 12, 24), rect, border_radius=10)
        pygame.draw.rect(tela, COR_CONDUTORA_FRIA if i == 1 else COR_CONDUTORA, rect, 2, border_radius=10)
        pygame.draw.rect(tela, (255, 255, 255, 22), rect.inflate(-10, -10), 1, border_radius=7)
        if progresso < 0.92:
            idx = (agora // max(55, 120 - i * 18) + i * 2) % len(opcoes)
            texto = opcoes[idx]
            offset = int(math.sin(agora * 0.035 + i) * 10)
        else:
            texto = combo[i] if i < len(combo) else "?"
            offset = 0
        cor = COR_LOGICO_OK if i == 1 else COR_CONDUTORA_CLARA
        render = fonte_reel.render(texto, True, cor)
        tela.blit(render, render.get_rect(center=(rect.centerx, rect.centery + offset)))
        legenda = "ESCOLHA" if i == 1 else "SINAL"
        leg = fonte_peq.render(legenda, True, (150, 210, 225))
        tela.blit(leg, leg.get_rect(center=(rect.centerx, rect.bottom - 16)))

    barra = pygame.Rect(largura_tela // 2 - total_w // 2, y + reel_h + 24, total_w, 8)
    pygame.draw.rect(tela, (8, 24, 38), barra, border_radius=4)
    pygame.draw.rect(tela, COR_CONDUTORA_FRIA, (barra.x, barra.y, int(barra.w * progresso), barra.h), border_radius=4)


def desenhar_circuitos(tela, inimigos, tempo_atual, config_graficos=None, manifestacao=None, jogador_rect=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        _FECHAMENTOS.clear()
        return

    _desenhar_fechamentos_ativos(tela, tempo_atual, perfil)
    if manifestacao is not None and not ativa(manifestacao):
        return

    # Draw custom logic buffs visual effects
    if jogador_rect is not None:
        buff_ativo = _ESTADO_LOGICO.get("buff_logico_ativo")
        buff_inicio = _ESTADO_LOGICO.get("buff_logico_inicio", 0)
        buff_duracao = _ESTADO_LOGICO.get("buff_logico_duracao", 0)
        stacks = _ESTADO_LOGICO.get("buff_logico_stacks", 0)
        
        if buff_ativo and (tempo_atual - buff_inicio < buff_duracao):
            cx, cy = jogador_rect.center
            if buff_ativo == "OR":
                raio_max = max(jogador_rect.width, jogador_rect.height) * 1.2
                fase = (tempo_atual * 0.003) % 1.0
                raio = int(raio_max * fase)
                alpha = int(180 * (1.0 - fase))
                surf = pygame.Surface((raio * 2 + 4, raio * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*COR_CONDUTORA_FRIA, alpha), (raio + 2, raio + 2), raio, 2)
                tela.blit(surf, (cx - raio - 2, cy - raio - 2))
                
            elif buff_ativo == "AND":
                raio = max(jogador_rect.width, jogador_rect.height) * 0.5
                for i in range(4):
                    rng_spark = random.Random(int(tempo_atual) // 150 + i * 49)
                    offset_x = rng_spark.randint(-int(raio), int(raio))
                    offset_y = rng_spark.randint(-int(raio * 1.5), int(raio * 0.5))
                    pygame.draw.circle(tela, (255, 120, 100), (cx + offset_x, cy + offset_y), 2)
                    
            elif buff_ativo == "XOR":
                raio = max(jogador_rect.width, jogador_rect.height) * 0.6
                for i in range(3):
                    ang = tempo_atual * 0.009 + i * math.tau / 3
                    px = int(cx + math.cos(ang) * raio)
                    py = int(cy + math.sin(ang) * (raio * 0.8))
                    pygame.draw.circle(tela, (255, 228, 100), (cx + px - cx, cy + py - cy), 2)
                    
            elif buff_ativo == "NAND":
                raio = max(jogador_rect.width, jogador_rect.height) * 0.75
                pulso = 0.5 + 0.5 * math.sin(tempo_atual * 0.01)
                pygame.draw.circle(tela, (104, 255, 214), (cx, cy), int(raio + pulso * 4), 2)
                for i in range(stacks):
                    ang = tempo_atual * 0.005 + i * math.tau / 3
                    px = int(cx + math.cos(ang) * (raio + pulso * 4))
                    py = int(cy + math.sin(ang) * (raio + pulso * 4))
                    pygame.draw.circle(tela, (255, 255, 255), (px, py), 4)
                    pygame.draw.circle(tela, (104, 255, 214), (px, py), 6, 1)
                    
            elif buff_ativo == "NOR":
                raio = BUFFS_LOGICOS["NOR"]["raio_lentidao"]
                pulso = 0.5 + 0.5 * math.sin(tempo_atual * 0.007)
                alpha = int(25 + 15 * pulso)
                aura_surf = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
                pygame.draw.circle(aura_surf, (80, 160, 255, alpha), (raio, raio), raio)
                pygame.draw.circle(aura_surf, (80, 160, 255, alpha * 2), (raio, raio), raio, 2)
                tela.blit(aura_surf, (cx - raio, cy - raio))

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
    _desenhar_roleta_registrador(tela, tempo_atual, perfil)


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
