# -*- coding: utf-8 -*-
import math
import random

import pygame


COR_LACERANTE = (255, 42, 112)
COR_LACERANTE_CLARA = (255, 205, 105)
COR_LACERANTE_ESCURA = (145, 0, 42)
COR_SANGUE = (180, 10, 10)

CORTE_ALCANCE = 120
CORTE_LARGURA = 42
CORTE_DURACAO_MS = 240
CORTE_DANO_MULT = 1.30
CORTE_DANO_AREA_MULT = 0.58
CORTE_DANO_FINAL_MULT = 1.60
LACERACAO_MAX_STACKS = 3
LACERACAO_DURACAO_MS = 6500

FENDA_ALCANCE = 250
FENDA_LARGURA = 76
FENDA_AVISO_MS = 520
FENDA_DURACAO_EXPLOSAO_MS = 260
FENDA_DANO_INICIAL_MULT = 2.10
FENDA_DANO_ESCALA_CARTA_MULT = 3.25
FENDA_DANO_LACERADO_MULT = 1.35
LACERANTE_DANO_REFERENCIA_INICIAL = 35.0
LACERANTE_COOLDOWN_HABILIDADE_MULT = 1.55

_sequencia_corte_auto_attack = 0


def obter_proximo_estagio():
    global _sequencia_corte_auto_attack
    return _sequencia_corte_auto_attack


def ativa(manifestacao):
    return str(manifestacao or "").strip().lower() == "lacerante"


def multiplicador_cooldown_habilidade(manifestacao):
    return LACERANTE_COOLDOWN_HABILIDADE_MULT if ativa(manifestacao) else 1.0


def dano_fenda_escalavel(dano_base):
    dano_base = max(1.0, float(dano_base))
    dano_inicial = min(dano_base, LACERANTE_DANO_REFERENCIA_INICIAL)
    dano_build = max(0.0, dano_base - LACERANTE_DANO_REFERENCIA_INICIAL)
    return max(
        1.0,
        dano_inicial * FENDA_DANO_INICIAL_MULT
        + dano_build * FENDA_DANO_ESCALA_CARTA_MULT,
    )


def _ponto_na_linha(origem_x, origem_y, angulo, distancia):
    return (
        float(origem_x) + math.cos(angulo) * distancia,
        float(origem_y) + math.sin(angulo) * distancia,
    )


def _vetores(angulo):
    frente = (math.cos(angulo), math.sin(angulo))
    normal = (-math.sin(angulo), math.cos(angulo))
    return frente, normal


def _ponto_orientado(origem_x, origem_y, frente, normal, avanco, lateral):
    return (
        float(origem_x) + frente[0] * avanco + normal[0] * lateral,
        float(origem_y) + frente[1] * avanco + normal[1] * lateral,
    )


def _bounds_pontos(pontos, largura):
    margem = largura * 0.5 + 18
    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    left = int(min(xs) - margem)
    top = int(min(ys) - margem)
    return pygame.Rect(left, top, int(max(xs) - min(xs) + margem * 2), int(max(ys) - min(ys) + margem * 2))


def _bounds_segmento(x1, y1, x2, y2, largura):
    margem = largura * 0.5 + 8
    left = int(min(x1, x2) - margem)
    top = int(min(y1, y2) - margem)
    return pygame.Rect(left, top, int(abs(x2 - x1) + margem * 2), int(abs(y2 - y1) + margem * 2))


def _rect_intersecta_segmento(rect, x1, y1, x2, y2, largura):
    dx = x2 - x1
    dy = y2 - y1
    comprimento2 = dx * dx + dy * dy
    if comprimento2 <= 0.0001:
        return False

    pontos = [
        rect.center,
        rect.topleft,
        rect.topright,
        rect.bottomleft,
        rect.bottomright,
        (rect.centerx, rect.top),
        (rect.centerx, rect.bottom),
        (rect.left, rect.centery),
        (rect.right, rect.centery),
    ]
    limite = largura * 0.5
    for px, py in pontos:
        t = ((px - x1) * dx + (py - y1) * dy) / comprimento2
        if 0.0 <= t <= 1.0:
            proj_x = x1 + dx * t
            proj_y = y1 + dy * t
            if math.hypot(px - proj_x, py - proj_y) <= limite:
                return True
    return False


def _rect_intersecta_polilinha(rect, pontos, largura):
    if not pontos or len(pontos) < 2:
        return False
    for i in range(len(pontos) - 1):
        x1, y1 = pontos[i]
        x2, y2 = pontos[i + 1]
        if _rect_intersecta_segmento(rect, x1, y1, x2, y2, largura):
            return True
    return False


def _proximo_estagio_corte():
    global _sequencia_corte_auto_attack
    estagio = _sequencia_corte_auto_attack
    _sequencia_corte_auto_attack = (_sequencia_corte_auto_attack + 1) % 3
    return estagio


def _multiplicador_estagio_corte(estagio):
    if estagio in (0, 1):
        return CORTE_DANO_AREA_MULT
    return CORTE_DANO_FINAL_MULT


def _criar_pontos_corte(centro_x, centro_y, angulo, estagio=0, escala=1.0):
    frente, normal = _vetores(angulo)
    pontos = []
    total = 11 if estagio in (0, 1) else 9
    for i in range(total):
        t = i / float(total - 1)
        avanco = (18 + CORTE_ALCANCE * t) * escala
        if estagio == 2:
            lateral = math.sin(t * math.pi * 2.0) * 3.0 * escala
        else:
            lateral = (-24 + 48 * t - math.sin(t * math.pi) * 10) * escala
            if estagio == 1:
                lateral *= -1
        pontos.append(_ponto_orientado(centro_x, centro_y, frente, normal, avanco, lateral))
    return pontos


def _curva_fenda(x1, y1, x2, y2, largura, semente, amplitude=18):
    rng = random.Random(int(semente))
    dx = x2 - x1
    dy = y2 - y1
    comprimento = max(1.0, math.hypot(dx, dy))
    nx = -dy / comprimento
    ny = dx / comprimento
    pontos = []
    for i in range(15):
        t = i / 14.0
        ruido = math.sin(t * math.pi * 3.0) * amplitude + rng.uniform(-largura * 0.12, largura * 0.12)
        if i in (0, 14):
            ruido *= 0.25
        pontos.append((x1 + dx * t + nx * ruido, y1 + dy * t + ny * ruido))
    return pontos


def colisao_corte(disparo, rect_inimigo, tempo_atual=None):
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "lacerante_corte":
        return False

    tempo_atual = pygame.time.get_ticks() if tempo_atual is None else int(tempo_atual)
    if tempo_atual - int(disparo.get("nascimento_ms", tempo_atual)) > int(disparo.get("duracao_ms", CORTE_DURACAO_MS)):
        disparo["expirado"] = True
        return False

    pontos = disparo.get("pontos_corte")
    largura = float(disparo.get("largura_corte", CORTE_LARGURA))
    if pontos:
        acertou = _rect_intersecta_polilinha(rect_inimigo, pontos, largura)
    else:
        x1, y1 = disparo.get("inicio", disparo["rect"].center)
        x2, y2 = disparo.get("fim", disparo["rect"].center)
        acertou = _rect_intersecta_segmento(rect_inimigo, x1, y1, x2, y2, largura)
    if not acertou:
        return False

    chave = (int(rect_inimigo.left), int(rect_inimigo.top), int(rect_inimigo.width), int(rect_inimigo.height))
    atingidos = disparo.setdefault("atingidos", [])
    if not disparo.get("multi_hit") and atingidos:
        return False
    if not disparo.get("multi_hit"):
        hit_frame = disparo.setdefault("hit_frame_ms", tempo_atual)
        if tempo_atual != hit_frame:
            return False
    if chave in atingidos:
        return False
    atingidos.append(chave)
    return True


def criar_auto_attack(manifestacao, vfx, centro_x, centro_y, largura, altura, angulo, velocidade, tempo_atual, impulsiva=False):
    if not ativa(manifestacao):
        return vfx.criar_disparo(centro_x, centro_y, largura, altura, angulo, velocidade, tempo_atual, impulsiva)

    estagio_corte = _proximo_estagio_corte()
    base_size = 8.0 if largura < 15.0 else 40.0
    escala = largura / base_size
    pontos = _criar_pontos_corte(centro_x, centro_y, angulo, estagio_corte, escala)
    inicio = pontos[0]
    fim = pontos[-1]
    largura_corte = CORTE_LARGURA * escala
    rect = _bounds_pontos(pontos, largura_corte)
    return {
        "tipo_manifestacao": "lacerante_corte",
        "rect": rect,
        "angulo": float(angulo),
        "inicio": inicio,
        "fim": fim,
        "pontos_corte": pontos,
        "estagio_corte": estagio_corte,
        "nascimento_ms": int(tempo_atual),
        "duracao_ms": CORTE_DURACAO_MS,
        "largura_corte": largura_corte,
        "dano_mult_manifestacao": _multiplicador_estagio_corte(estagio_corte),
        "multi_hit": estagio_corte in (0, 1),
        "atingidos": [],
        "impulsiva_vfx": bool(impulsiva),
    }


def multiplicador_dano_disparo(disparo):
    if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte":
        return float(disparo.get("dano_mult_manifestacao", CORTE_DANO_MULT))
    return 1.0


def multiplicador_dano_boss(disparo):
    if not isinstance(disparo, dict) or disparo.get("tipo_manifestacao") != "lacerante_corte":
        return 1.0
    estagio = int(disparo.get("estagio_corte", 0) or 0)
    return 1.28 if estagio in (0, 1) else 1.55


def aplicar_laceracao(inimigo, tempo_atual):
    if not isinstance(inimigo, dict):
        return 0
    estado = inimigo.setdefault("laceracao_temporal", {"stacks": 0, "aberto": False, "ultimo_tick_movimento": 0})
    stacks = min(LACERACAO_MAX_STACKS, int(estado.get("stacks", 0)) + 1)
    estado["stacks"] = stacks
    estado["expira_ms"] = int(tempo_atual) + LACERACAO_DURACAO_MS
    estado["aberto"] = stacks >= LACERACAO_MAX_STACKS
    estado["ultimo_tick_movimento"] = min(int(estado.get("ultimo_tick_movimento", 0)), int(tempo_atual))
    rect = inimigo.get("rect")
    if rect is not None and "ultima_pos" not in estado:
        estado["ultima_pos"] = (int(rect.centerx), int(rect.centery))
    return stacks


def dano_extra_movimento(inimigo, tempo_atual):
    estado = inimigo.get("laceracao_temporal") if isinstance(inimigo, dict) else None
    if not estado:
        return 0
    if tempo_atual > int(estado.get("expira_ms", 0)):
        inimigo.pop("laceracao_temporal", None)
        return 0

    stacks = max(1, min(LACERACAO_MAX_STACKS, int(estado.get("stacks", 1))))
    eh_miniboss = bool(inimigo.get("eh_miniboss", False))
    intervalo_tick = (900 if estado.get("aberto") else 1050) if eh_miniboss else (650 if estado.get("aberto") else 780)
    if tempo_atual - int(estado.get("ultimo_tick_movimento", 0)) < intervalo_tick:
        return 0

    rect = inimigo.get("rect")
    if rect is None:
        return 0
    pos = (int(rect.centerx), int(rect.centery))
    anterior = estado.get("ultima_pos")
    estado["ultima_pos"] = pos
    if anterior is None:
        return 0
    if math.hypot(pos[0] - anterior[0], pos[1] - anterior[1]) < 2:
        return 0

    estado["ultimo_tick_movimento"] = int(tempo_atual)
    vida_base = inimigo.get("vida_maxima", inimigo.get("vida", 50))
    percentual = 0.006 * stacks
    if estado.get("aberto"):
        percentual = 0.025
    if eh_miniboss:
        percentual = 0.006 if estado.get("aberto") else 0.0015 * stacks
    dano = max(1, int(vida_base * percentual))
    inimigo["vida"] -= dano
    return dano


def atualizar_laceracoes(inimigos, tempo_atual, efeitos_texto=None):
    mortos = []
    for inimigo in list(inimigos or []):
        dano = dano_extra_movimento(inimigo, tempo_atual)
        if dano and efeitos_texto is not None and inimigo.get("rect"):
            stacks = int((inimigo.get("laceracao_temporal") or {}).get("stacks", 1))
            efeitos_texto.append({
                "texto": f"-{int(dano)}",
                "x": inimigo["rect"].centerx,
                "y": inimigo["rect"].top - 18,
                "tempo_inicio": tempo_atual,
                "cor": COR_SANGUE,
            })
        if inimigo.get("vida", 1) <= 0:
            mortos.append(inimigo)
    return mortos


def criar_fenda(origem_x, origem_y, angulo, tempo_atual, dano_base):
    inicio = _ponto_na_linha(origem_x, origem_y, angulo, 26)
    fim = _ponto_na_linha(origem_x, origem_y, angulo, FENDA_ALCANCE)
    pontos = _curva_fenda(inicio[0], inicio[1], fim[0], fim[1], FENDA_LARGURA, tempo_atual, 14)
    return {
        "tipo_manifestacao": "fenda_lacerante",
        "rect": _bounds_pontos(pontos, FENDA_LARGURA),
        "angulo": float(angulo),
        "inicio": inicio,
        "fim": fim,
        "pontos_fenda": pontos,
        "tempo_inicio": int(tempo_atual),
        "explodir_ms": int(tempo_atual) + FENDA_AVISO_MS,
        "fim_ms": int(tempo_atual) + FENDA_AVISO_MS + FENDA_DURACAO_EXPLOSAO_MS,
        "dano": dano_fenda_escalavel(dano_base),
        "largura_fenda": FENDA_LARGURA,
        "aplicou": False,
    }


def _desenhar_linha_lacerante(tela, x1, y1, x2, y2, largura, alpha, explodindo=False):
    surf = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    cor = (*COR_LACERANTE, max(0, min(255, int(alpha))))
    cor_clara = (*COR_LACERANTE_CLARA, max(0, min(255, int(alpha * 0.9))))
    pygame.draw.line(surf, (*COR_LACERANTE_ESCURA, max(0, min(210, int(alpha * 0.55)))), (int(x1), int(y1)), (int(x2), int(y2)), max(2, int(largura)))
    pygame.draw.line(surf, cor, (int(x1), int(y1)), (int(x2), int(y2)), max(2, int(largura * (0.32 if explodindo else 0.18))))
    pygame.draw.line(surf, cor_clara, (int(x1), int(y1)), (int(x2), int(y2)), 2)
    tela.blit(surf, (0, 0))


def _pontos_int(pontos):
    return [(int(x), int(y)) for x, y in pontos]


def _ponto_em_curva(pontos, t):
    if not pontos:
        return (0.0, 0.0)
    if len(pontos) == 1:
        return pontos[0]
    t = max(0.0, min(1.0, t))
    pos = t * (len(pontos) - 1)
    idx = min(len(pontos) - 2, int(pos))
    frac = pos - idx
    x1, y1 = pontos[idx]
    x2, y2 = pontos[idx + 1]
    return (x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac)


def _clamp(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def _normalizar(vx, vy):
    comprimento = math.hypot(vx, vy)
    if comprimento <= 0.0001:
        return (1.0, 0.0)
    return (vx / comprimento, vy / comprimento)


def _normais_curva(pontos):
    normais = []
    total = len(pontos)
    for i, (x, y) in enumerate(pontos):
        if i == 0:
            dx = pontos[1][0] - x
            dy = pontos[1][1] - y
        elif i == total - 1:
            dx = x - pontos[i - 1][0]
            dy = y - pontos[i - 1][1]
        else:
            dx = pontos[i + 1][0] - pontos[i - 1][0]
            dy = pontos[i + 1][1] - pontos[i - 1][1]
        tx, ty = _normalizar(dx, dy)
        normais.append((-ty, tx))
    return normais


def _perfil_largura_rasgo(t, abertura=1.0):
    ventre = math.sin(math.pi * _clamp(t, 0.0, 1.0))
    corpo = 0.16 + 0.84 * (max(0.0, ventre) ** 0.52)
    ponta_inicio = _clamp(t * 7.5, 0.08, 1.0)
    ponta_fim = _clamp((1.0 - t) * 10.5, 0.035, 1.0)
    return corpo * ponta_inicio * ponta_fim * _clamp(abertura, 0.05, 1.4)


def _contorno_rasgo(pontos, largura, abertura, semente, escala=1.0):
    if not pontos or len(pontos) < 2:
        return [], [], []
    rng = random.Random(int(semente) + int(escala * 1009))
    normais = _normais_curva(pontos)
    esquerda = []
    direita = []
    total = len(pontos) - 1
    for i, (x, y) in enumerate(pontos):
        t = i / float(total)
        nx, ny = normais[i]
        perfil = _perfil_largura_rasgo(t, abertura)
        serrilha = math.sin((t * 37.0) + rng.random() * 1.8) * largura * 0.025
        metade = max(1.2, largura * 0.5 * perfil * escala)
        jitter_esq = serrilha + rng.uniform(-largura * 0.08, largura * 0.08) * perfil
        jitter_dir = -serrilha + rng.uniform(-largura * 0.08, largura * 0.08) * perfil
        esquerda.append((int(x + nx * (metade + jitter_esq)), int(y + ny * (metade + jitter_esq))))
        direita.append((int(x - nx * (metade + jitter_dir)), int(y - ny * (metade + jitter_dir))))
    return esquerda, direita, esquerda + list(reversed(direita))


def _desenhar_glow_rasgo(surf, pontos_i, largura_base, alpha):
    for escala, fator_alpha in ((1.65, 0.12), (1.22, 0.18), (0.86, 0.24)):
        pygame.draw.lines(
            surf,
            (*COR_LACERANTE, max(0, min(145, int(alpha * fator_alpha)))),
            False,
            pontos_i,
            max(3, int(largura_base * escala)),
        )


def _desenhar_bordas_rasgadas(surf, esquerda, direita, largura_base, alpha):
    if len(esquerda) < 2 or len(direita) < 2:
        return
    sombra = (*COR_LACERANTE_ESCURA, max(0, min(225, int(alpha * 0.72))))
    rubro = (*COR_LACERANTE, max(0, min(245, int(alpha * 0.86))))
    luz = (*COR_LACERANTE_CLARA, max(0, min(255, int(alpha * 0.78))))
    pygame.draw.lines(surf, sombra, False, esquerda, max(2, int(largura_base * 0.13)))
    pygame.draw.lines(surf, sombra, False, direita, max(2, int(largura_base * 0.13)))
    pygame.draw.lines(surf, rubro, False, esquerda, max(1, int(largura_base * 0.07)))
    pygame.draw.lines(surf, rubro, False, direita, max(1, int(largura_base * 0.07)))
    pygame.draw.lines(surf, luz, False, esquerda[1:-1] or esquerda, 1)
    pygame.draw.lines(surf, luz, False, direita[1:-1] or direita, 1)


def _desenhar_particulas_borda(surf, pontos, largura_base, alpha, progresso, semente, quantidade):
    rng = random.Random(int(semente) + 6503 + int(progresso * 90))
    normais = _normais_curva(pontos)
    total = len(pontos) - 1
    fade = _clamp(1.0 - progresso * 0.72, 0.0, 1.0)
    for _ in range(quantidade):
        t = rng.random()
        idx = min(total, max(0, int(t * total)))
        px, py = _ponto_em_curva(pontos, t)
        nx, ny = normais[idx]
        lado = -1 if rng.random() < 0.5 else 1
        perfil = _perfil_largura_rasgo(t, 1.0)
        distancia_borda = largura_base * 0.5 * perfil + rng.uniform(0, largura_base * 0.22)
        px += nx * lado * distancia_borda + rng.uniform(-2.8, 2.8)
        py += ny * lado * distancia_borda + rng.uniform(-2.8, 2.8)
        tamanho = rng.choice((1, 1, 1, 2, 2, 3))
        cor = rng.choice((COR_LACERANTE_CLARA, COR_LACERANTE, COR_LACERANTE_ESCURA))
        a = int(alpha * rng.uniform(0.18, 0.62) * fade)
        if a <= 0:
            continue
        if rng.random() < 0.5:
            pygame.draw.circle(surf, (*cor, a), (int(px), int(py)), tamanho)
        else:
            tx = px + nx * lado * rng.uniform(3, 11)
            ty = py + ny * lado * rng.uniform(3, 11)
            pygame.draw.line(surf, (*cor, a), (int(px), int(py)), (int(tx), int(ty)), 1)


def _desenhar_curva_lacerante(tela, pontos, largura, alpha, progresso, semente, explodindo=True):
    if not pontos or len(pontos) < 2 or alpha <= 0:
        return

    surf = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    rng = random.Random(int(semente) + 4049)
    fade = _clamp(1.0 - progresso, 0.0, 1.0)
    largura_base = max(3, int(largura))
    pontos_i = _pontos_int(pontos)

    abertura = _clamp(0.32 + progresso * 1.65, 0.16, 1.0) if not explodindo else _clamp(0.78 + fade * 0.28, 0.32, 1.1)
    esquerda_sombra, direita_sombra, poligono_sombra = _contorno_rasgo(pontos, largura_base, abertura, semente, 1.28)
    esquerda, direita, poligono = _contorno_rasgo(pontos, largura_base, abertura, semente, 1.0)
    esquerda_miolo, direita_miolo, poligono_miolo = _contorno_rasgo(pontos, largura_base, abertura * 0.78, semente + 37, 0.72)

    _desenhar_glow_rasgo(surf, pontos_i, largura_base, alpha)
    if len(poligono_sombra) >= 3:
        pygame.draw.polygon(surf, (18, 0, 10, max(0, min(185, int(alpha * 0.36)))), poligono_sombra)
    if len(poligono) >= 3:
        pygame.draw.polygon(surf, (*COR_LACERANTE_ESCURA, max(0, min(225, int(alpha * 0.54)))), poligono)
    if len(poligono_miolo) >= 3:
        pygame.draw.polygon(surf, (8, 0, 12, max(0, min(245, int(alpha * (0.78 if explodindo else 0.52))))), poligono_miolo)

    pygame.draw.lines(
        surf,
        (0, 0, 0, max(0, min(210, int(alpha * 0.38)))),
        False,
        pontos_i,
        max(2, int(largura_base * (0.22 if explodindo else 0.12))),
    )
    _desenhar_bordas_rasgadas(surf, esquerda_sombra, direita_sombra, largura_base, alpha * 0.78)
    _desenhar_bordas_rasgadas(surf, esquerda, direita, largura_base, alpha)

    frente, normal = _vetores(math.atan2(pontos[-1][1] - pontos[0][1], pontos[-1][0] - pontos[0][0]))
    for trilha in range(2):
        desloc = (-10 + trilha * 20) * (0.45 + 0.45 * fade)
        trilha_pontos = []
        for x, y in pontos:
            jitter = rng.uniform(-4, 4)
            trilha_pontos.append((int(x + normal[0] * (desloc + jitter)), int(y + normal[1] * (desloc + jitter))))
        pygame.draw.lines(
            surf,
            (*COR_LACERANTE_CLARA, max(0, min(145, int(alpha * (0.22 - trilha * 0.04))))),
            False,
            trilha_pontos,
            1,
        )

    ponta = pontos[-1]
    cauda_ponta = _ponto_em_curva(pontos, 0.84)
    ponta_extra = (ponta[0] + frente[0] * largura_base * 0.24, ponta[1] + frente[1] * largura_base * 0.24)
    pygame.draw.line(
        surf,
        (*COR_LACERANTE_CLARA, max(0, min(255, int(alpha * 0.82)))),
        (int(cauda_ponta[0]), int(cauda_ponta[1])),
        (int(ponta_extra[0]), int(ponta_extra[1])),
        max(1, int(largura_base * 0.035)),
    )
    pygame.draw.circle(
        surf,
        (*COR_LACERANTE_CLARA, max(0, min(210, int(alpha * 0.58)))),
        (int(ponta_extra[0]), int(ponta_extra[1])),
        max(1, int(largura_base * 0.035)),
    )

    _desenhar_particulas_borda(
        surf,
        pontos,
        largura_base,
        alpha,
        progresso,
        semente,
        46 if explodindo else 22,
    )

    if explodindo:
        for _ in range(16):
            k = rng.random()
            px, py = _ponto_em_curva(pontos, k)
            espalhar = rng.uniform(-largura_base * 0.38, largura_base * 0.38) * fade
            px += normal[0] * espalhar + rng.uniform(-5, 5)
            py += normal[1] * espalhar + rng.uniform(-5, 5)
            comp = rng.uniform(8, 28) * (0.6 + fade * 0.55)
            cauda_x = px - frente[0] * comp + normal[0] * rng.uniform(-4, 4)
            cauda_y = py - frente[1] * comp + normal[1] * rng.uniform(-4, 4)
            cor = COR_LACERANTE_CLARA if rng.random() < 0.42 else COR_LACERANTE
            pygame.draw.line(
                surf,
                (*cor, max(0, min(220, int(alpha * rng.uniform(0.18, 0.54))))),
                (int(cauda_x), int(cauda_y)),
                (int(px), int(py)),
                rng.choice((1, 1, 2)),
            )

    tela.blit(surf, (0, 0))


def desenhar_corte(tela, disparo, tempo_atual):
    idade = max(0, int(tempo_atual) - int(disparo.get("nascimento_ms", tempo_atual)))
    duracao = max(1, int(disparo.get("duracao_ms", CORTE_DURACAO_MS)))
    t = min(1.0, idade / duracao)
    aparicao = min(1.0, idade / max(1, duracao * 0.18))
    alpha = int(255 * (1.0 - t * 0.68) * aparicao)
    if disparo.get("estagio_corte") == 2:
        alpha = min(255, int(alpha * 1.16))
    pontos = disparo.get("pontos_corte")
    largura = float(disparo.get("largura_corte", CORTE_LARGURA)) * (0.72 + 0.38 * (1.0 - t))
    if pontos:
        _desenhar_curva_lacerante(tela, pontos, largura, alpha, t, disparo.get("nascimento_ms", 0), True)
    else:
        x1, y1 = disparo.get("inicio", disparo["rect"].center)
        x2, y2 = disparo.get("fim", disparo["rect"].center)
        _desenhar_linha_lacerante(tela, x1, y1, x2, y2, largura, alpha, True)


def desenhar_fenda(tela, fenda, tempo_atual):
    x1, y1 = fenda["inicio"]
    x2, y2 = fenda["fim"]
    pontos = fenda.get("pontos_fenda")
    if not pontos:
        pontos = _curva_fenda(x1, y1, x2, y2, fenda.get("largura_fenda", FENDA_LARGURA), fenda.get("tempo_inicio", 0), 14)
        fenda["pontos_fenda"] = pontos
    if tempo_atual < fenda["explodir_ms"]:
        falta = max(0, fenda["explodir_ms"] - tempo_atual)
        pulso = 0.55 + 0.45 * math.sin(tempo_atual * 0.035)
        abertura = 1.0 - falta / max(1, FENDA_AVISO_MS)
        _desenhar_curva_lacerante(tela, pontos, 10 + pulso * 9 + abertura * 12, 80 + pulso * 80, abertura * 0.45, fenda.get("tempo_inicio", 0), False)
        return
    progresso = min(1.0, (tempo_atual - fenda["explodir_ms"]) / max(1, FENDA_DURACAO_EXPLOSAO_MS))
    _desenhar_curva_lacerante(
        tela,
        pontos,
        fenda.get("largura_fenda", FENDA_LARGURA) * (1.0 - progresso * 0.25),
        245 * (1.0 - progresso * 0.55),
        progresso,
        fenda.get("tempo_inicio", 0) + 991,
        True,
    )
    rng = random.Random(int(fenda["tempo_inicio"]) + int(tempo_atual // 45))
    for _ in range(12):
        k = rng.random()
        px, py = _ponto_em_curva(pontos, k)
        pygame.draw.line(tela, COR_LACERANTE_CLARA, (int(px - 10), int(py - 4)), (int(px + 10), int(py + 4)), 1)


def processar_fenda(fenda, inimigos, boss_info, tempo_atual):
    mortos = []
    if fenda.get("aplicou") or tempo_atual < int(fenda.get("explodir_ms", 0)):
        return mortos
    fenda["aplicou"] = True
    x1, y1 = fenda["inicio"]
    x2, y2 = fenda["fim"]
    largura = float(fenda.get("largura_fenda", FENDA_LARGURA))
    pontos_fenda = fenda.get("pontos_fenda")
    dano_base = float(fenda.get("dano", 1.0))

    for inimigo in list(inimigos or []):
        rect = inimigo.get("rect")
        if rect is None:
            continue
        if pontos_fenda:
            acertou = _rect_intersecta_polilinha(rect, pontos_fenda, largura)
        else:
            acertou = _rect_intersecta_segmento(rect, x1, y1, x2, y2, largura)
        if not acertou:
            continue
        estado = inimigo.get("laceracao_temporal") or {}
        stacks = int(estado.get("stacks", 0))
        mult = FENDA_DANO_LACERADO_MULT if stacks > 0 else 1.0
        inimigo["vida"] -= dano_base * mult
        if stacks > 0:
            inimigo.pop("laceracao_temporal", None)
        if inimigo.get("vida", 1) <= 0:
            mortos.append(inimigo)

    if boss_info and boss_info.get("vivo") and boss_info.get("rect"):
        if pontos_fenda:
            acertou_boss = _rect_intersecta_polilinha(boss_info["rect"], pontos_fenda, largura)
        else:
            acertou_boss = _rect_intersecta_segmento(boss_info["rect"], x1, y1, x2, y2, largura)
        if acertou_boss:
            boss_info["hit_flag"] = True
            boss_info["dano_manifestacao"] = dano_base
            boss_info["atingido_por_onda"] = tempo_atual
    return mortos


particulas_sangue = []
rastros_sangue = []


def _limitar_lista(lista, maximo):
    if len(lista) > maximo:
        del lista[:len(lista) - maximo]


def _origem_sangue_chao(inimigo, pos_anterior=None):
    rect = inimigo.get("rect")
    if rect is None:
        return (0.0, 0.0)
    x = float(rect.centerx)
    y = float(rect.bottom) + max(1.0, rect.height * 0.03)
    if pos_anterior:
        dx = x - float(pos_anterior[0])
        dy = y - float(pos_anterior[1])
        dist = math.hypot(dx, dy)
        if dist > 0.001:
            x -= (dx / dist) * min(10.0, rect.width * 0.22)
            y -= (dy / dist) * min(6.0, rect.height * 0.12)
    return (x, y)


def _criar_goticulas_chao(x, y, quantidade, raio_base):
    gotas = []
    for _ in range(quantidade):
        ang = random.random() * math.tau
        dist = random.uniform(raio_base * 0.45, raio_base * 2.4)
        gotas.append({
            "dx": math.cos(ang) * dist,
            "dy": math.sin(ang) * dist * random.uniform(0.38, 0.82),
            "raio": random.uniform(1.0, max(1.4, raio_base * 0.22)),
            "alpha": random.uniform(0.28, 0.78),
            "cor": random.choice([(95, 0, 0), (125, 4, 6), (165, 8, 10), (58, 0, 0)]),
        })
    return gotas


def _adicionar_poca_sangue(x, y, tempo_atual, opcao_sangue, intensidade=1.0, angulo=0.0):
    duracao = random.randint(6200, 9200) if opcao_sangue == "alto" else random.randint(2600, 3600)
    tamanho = random.uniform(7.0, 13.0) * intensidade if opcao_sangue == "alto" else random.uniform(3.0, 5.5)
    rastros_sangue.append({
        "x": x,
        "y": y,
        "tempo_criacao": tempo_atual,
        "duracao": duracao,
        "tamanho_max": tamanho,
        "rx": tamanho * random.uniform(1.45, 2.55) if opcao_sangue == "alto" else tamanho,
        "ry": tamanho * random.uniform(0.42, 0.82) if opcao_sangue == "alto" else tamanho,
        "angulo": math.degrees(angulo) + random.uniform(-18, 18),
        "cor": random.choice([
            (95, 2, 4),
            (125, 3, 6),
            (150, 8, 9),
            (70, 0, 2),
        ]),
        "gotas": _criar_goticulas_chao(x, y, random.randint(4, 10), tamanho) if opcao_sangue == "alto" else [],
    })


def _desenhar_poca_liquida(surf, r, alpha, progresso):
    rx = max(2, int(r.get("rx", r["tamanho_max"])))
    ry = max(2, int(r.get("ry", r["tamanho_max"] * 0.55)))
    margem = max(4, int(max(rx, ry) * 0.45))
    local = pygame.Surface((rx * 2 + margem * 2, ry * 2 + margem * 2), pygame.SRCALPHA)
    cx = local.get_width() // 2
    cy = local.get_height() // 2
    crescimento = 0.72 + 0.34 * min(1.0, progresso * 2.2)
    rect_sombra = pygame.Rect(0, 0, int(rx * 2.4 * crescimento), int(ry * 2.15 * crescimento))
    rect_sombra.center = (cx + 1, cy + 2)
    rect_base = pygame.Rect(0, 0, int(rx * 2.0 * crescimento), int(ry * 1.7 * crescimento))
    rect_base.center = (cx, cy)
    rect_miolo = pygame.Rect(0, 0, int(rx * 1.35 * crescimento), int(ry * 1.0 * crescimento))
    rect_miolo.center = (cx - int(rx * 0.08), cy)
    rect_brilho = pygame.Rect(0, 0, max(2, int(rx * 0.42 * crescimento)), max(2, int(ry * 0.22 * crescimento)))
    rect_brilho.center = (cx - int(rx * 0.28), cy - int(ry * 0.28))

    pygame.draw.ellipse(local, (24, 0, 0, int(alpha * 0.42)), rect_sombra)
    pygame.draw.ellipse(local, (*r["cor"], int(alpha * 0.86)), rect_base)
    pygame.draw.ellipse(local, (45, 0, 0, int(alpha * 0.70)), rect_miolo)
    pygame.draw.ellipse(local, (205, 22, 28, int(alpha * 0.22)), rect_brilho)

    for gota in r.get("gotas", []):
        gx = cx + int(gota["dx"] * crescimento)
        gy = cy + int(gota["dy"] * crescimento)
        ga = int(alpha * gota.get("alpha", 0.5))
        pygame.draw.circle(local, (*gota["cor"], ga), (gx, gy), max(1, int(gota["raio"] * crescimento)))

    rot = pygame.transform.rotate(local, r.get("angulo", 0.0))
    surf.blit(rot, rot.get_rect(center=(int(r["x"]), int(r["y"]))).topleft)


def _recortar_sangue_sobre_inimigos(surf, inimigos_comum):
    for inimigo in list(inimigos_comum or []):
        rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
        if rect is None:
            continue
        area = rect.inflate(8, 10)
        area.y -= 5
        surf.fill((0, 0, 0, 0), area, special_flags=pygame.BLEND_RGBA_MULT)


def atualizar_e_desenhar_sangue_lacerante(tela, inimigos_comum, config_graficos=None):
    global particulas_sangue, rastros_sangue

    opcao_sangue = "alto"
    if config_graficos is not None:
        opcao_sangue = config_graficos.get("sangue_lacerante", "alto")
    else:
        try:
            import json
            with open("saves/config_graficos.json", "r") as f:
                cfg = json.load(f)
                opcao_sangue = cfg.get("sangue_lacerante", "alto")
        except:
            pass

    if opcao_sangue == "desativado":
        particulas_sangue.clear()
        rastros_sangue.clear()
        return

    tempo_atual = pygame.time.get_ticks()

    # 1. Spawn particles and trails from active enemies
    for inimigo in list(inimigos_comum or []):
        if not inimigo.get("rect"):
            continue

        lacerado = False
        estado = inimigo.get("laceracao_temporal")
        if estado:
            if tempo_atual <= estado.get("expira_ms", 0):
                lacerado = True

        if lacerado:
            max_particulas = 520 if opcao_sangue == "alto" else 130
            max_rastros = 780 if opcao_sangue == "alto" else 240
            rect = inimigo["rect"]
            pos_antiga = inimigo.get("lacerante_pos_anterior")
            chao_x, chao_y = _origem_sangue_chao(inimigo, pos_antiga)
            spawn_chance = 0.78 if opcao_sangue == "alto" else 0.22

            if random.random() < spawn_chance and len(particulas_sangue) < max_particulas:
                px = chao_x + random.uniform(-rect.width * 0.28, rect.width * 0.28)
                py = chao_y + random.uniform(-1.5, 4.5)
                vx = random.uniform(-0.75, 0.75)
                vy = random.uniform(-0.35, 0.45) if opcao_sangue == "alto" else random.uniform(-0.55, 0.25)
                tamanho = random.uniform(1.6, 3.8) if opcao_sangue == "alto" else random.uniform(1.1, 2.4)
                vida = random.randint(42, 72) if opcao_sangue == "alto" else random.randint(22, 36)
                cor = random.choice([
                    (180, 10, 10),
                    (130, 0, 0),
                    (210, 20, 20),
                    (80, 0, 0),
                ])
                particulas_sangue.append({
                    "x": px,
                    "y": py,
                    "vx": vx,
                    "vy": vy,
                    "tamanho": tamanho,
                    "vida_max": vida,
                    "vida": vida,
                    "cor": cor
                })

            pos_atual = (chao_x, chao_y)
            pos_antiga = inimigo.setdefault("lacerante_pos_anterior", pos_atual)
            dx = pos_atual[0] - pos_antiga[0]
            dy = pos_atual[1] - pos_antiga[1]
            dist = math.hypot(dx, dy)

            if dist > 0.5:
                num_steps = max(1, int(dist / (3.4 if opcao_sangue == "alto" else 10.0)))
                num_steps = min(16 if opcao_sangue == "alto" else 6, num_steps)
                angulo_mov = math.atan2(dy, dx) if dist > 0.001 else 0.0

                for step in range(num_steps):
                    t = step / float(num_steps)
                    tx = pos_antiga[0] + dx * t + random.uniform(-4.5, 4.5)
                    ty = pos_antiga[1] + dy * t + random.uniform(-2.5, 4.5)
                    intensidade = 0.75 + min(1.4, dist / 22.0)
                    _adicionar_poca_sangue(tx, ty, tempo_atual, opcao_sangue, intensidade, angulo_mov)

                    if opcao_sangue == "alto" and random.random() < 0.55:
                        for _ in range(random.randint(1, 3)):
                            gx = tx + random.uniform(-16, 16)
                            gy = ty + random.uniform(-8, 10)
                            _adicionar_poca_sangue(gx, gy, tempo_atual, opcao_sangue, random.uniform(0.28, 0.55), random.random() * math.tau)

                _limitar_lista(rastros_sangue, max_rastros)

            inimigo["lacerante_pos_anterior"] = pos_atual
        else:
            # If not lacerated anymore, clean pos tracker
            inimigo.pop("lacerante_pos_anterior", None)

    # 2. Update and draw trails
    novos_rastros = []
    surf = None
    
    # Pre-check if we need a Surface
    if rastros_sangue or particulas_sangue:
        surf = pygame.Surface(tela.get_size(), pygame.SRCALPHA)

    for r in rastros_sangue:
        idade = tempo_atual - r["tempo_criacao"]
        if idade >= r["duracao"]:
            continue
        novos_rastros.append(r)
        
        progresso = idade / float(r["duracao"])
        permanencia = 1.0 - (progresso ** (1.9 if opcao_sangue == "alto" else 1.2))
        alpha = int((215 if opcao_sangue == "alto" else 170) * max(0.0, permanencia))
        tamanho = r["tamanho_max"] * (0.82 + 0.34 * min(1.0, progresso * 2.0))

        if surf is not None:
            if opcao_sangue == "alto":
                _desenhar_poca_liquida(surf, r, alpha, progresso)
            else:
                pygame.draw.circle(surf, (*r["cor"], alpha), (int(r["x"]), int(r["y"])), int(tamanho))
                if tamanho > 4:
                    pygame.draw.circle(surf, (50, 0, 0, int(alpha * 0.6)), (int(r["x"] + 1), int(r["y"] + 1)), int(tamanho * 0.55))
                
    rastros_sangue = novos_rastros

    # 3. Update and draw droplets
    novas_particulas = []
    for p in particulas_sangue:
        p["vida"] -= 1
        if p["vida"] <= 0:
            continue
            
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.08 if opcao_sangue == "alto" else 0.14
        p["vx"] *= 0.93 if opcao_sangue == "alto" else 0.96
        
        novas_particulas.append(p)
        
        progresso_vida = p["vida"] / float(p["vida_max"])
        alpha = int(255 * progresso_vida)
        tamanho = max(1.0, p["tamanho"] * (0.5 + 0.5 * progresso_vida))
        
        if surf is not None:
            pygame.draw.circle(surf, (*p["cor"], alpha), (int(p["x"]), int(p["y"])), int(tamanho))

            if opcao_sangue == "alto" and p["vida"] < p["vida_max"] - 2:
                prev_x = p["x"] - p["vx"] * 1.5
                prev_y = p["y"] - p["vy"] * 1.5
                pygame.draw.line(surf, (*p["cor"], int(alpha * 0.4)), (int(prev_x), int(prev_y)), (int(p["x"]), int(p["y"])), max(1, int(tamanho - 1)))

    particulas_sangue = novas_particulas

    # 4. Blit to screen
    if surf is not None:
        _recortar_sangue_sobre_inimigos(surf, inimigos_comum)
        tela.blit(surf, (0, 0))
