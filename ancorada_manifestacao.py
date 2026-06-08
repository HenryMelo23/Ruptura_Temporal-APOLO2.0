# -*- coding: utf-8 -*-
import math
import random

import pygame

import gravitante_manifestacao


COR_ANCORADA = (75, 225, 255)
COR_ANCORADA_CLARA = (235, 255, 245)
COR_ANCORADA_DOURADA = (255, 205, 80)
COR_ANCORADA_ESCURA = (18, 42, 72)

ANCORA_DURACAO_MS = 7200
ANCORA_RAIO = 116
ANCORA_MAX = 3
ANCORA_PLANTAR_INTERVALO_MS = 1050
ANCORA_SUSTENTAR_MS = 900
ANCORA_DISSIPAR_MS = 950
ANCORA_TICK_MS = 650
ANCORA_DANO_TICK_MULT = 0.16
ANCORA_DANO_DISPARO_MULT = 1.22
ANCORA_INTERVALO_MULT = 0.82

DOMINIO_DURACAO_MS = 6400
DOMINIO_RAIO = 178
DOMINIO_SUSTENTAR_MS = 1150
DOMINIO_DISSIPAR_MS = 1350
DOMINIO_TICK_MS = 520
DOMINIO_DANO_TICK_MULT = 0.20
DOMINIO_DANO_DISPARO_MULT = 1.34
DOMINIO_INTERVALO_MULT = 0.76
DOMINIO_LENTIDAO_PROJETIL = 0.52

_ANCORAS = []
_DOMINIOS = []
_ULTIMA_ANCORA_PLANTADA_MS = -999999


def ativa(manifestacao):
    return str(manifestacao or "").strip().lower() == "ancorada"


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


def _texto(efeitos_texto, texto, rect, tempo_atual, cor=COR_ANCORADA_CLARA):
    if efeitos_texto is None or rect is None:
        return
    efeitos_texto.append({
        "texto": texto,
        "x": rect.centerx,
        "y": rect.top - 24,
        "tempo_inicio": int(tempo_atual),
        "cor": cor,
    })


def _limpar_expirados(tempo_atual):
    agora = int(tempo_atual)
    _ANCORAS[:] = [a for a in _ANCORAS if agora < int(a.get("fim_ms", 0))]
    _DOMINIOS[:] = [d for d in _DOMINIOS if agora < int(d.get("fim_ms", 0))]


def _distancia(px, py, x, y):
    return math.hypot(float(px) - float(x), float(py) - float(y))


def _centro_jogador(x, y, largura, altura):
    return float(x) + float(largura) * 0.5, float(y) + float(altura) * 0.5


def _zona_contem(zona, x, y, margem=0.0):
    return _distancia(x, y, zona["x"], zona["y"]) <= float(zona.get("raio", ANCORA_RAIO)) + float(margem)


def _zona_no_ponto(x, y):
    for dominio in _DOMINIOS:
        if _zona_contem(dominio, x, y):
            return dominio
    for ancora in _ANCORAS:
        if _zona_contem(ancora, x, y):
            return ancora
    return None


def _tipo_territorio(zona):
    if not zona:
        return None
    return "dominio" if zona.get("tipo_manifestacao") == "dominio_ancorado" else "ancora"


def jogador_em_territorio(x, y, largura, altura, tempo_atual):
    _limpar_expirados(tempo_atual)
    cx, cy = _centro_jogador(x, y, largura, altura)
    return _tipo_territorio(_zona_no_ponto(cx, cy))


def intervalo_disparo_ancorado(intervalo_base, manifestacao, x, y, largura, altura, tempo_atual):
    if not ativa(manifestacao):
        return intervalo_base
    territorio = jogador_em_territorio(x, y, largura, altura, tempo_atual)
    if territorio == "dominio":
        return max(45, float(intervalo_base) * DOMINIO_INTERVALO_MULT)
    if territorio == "ancora":
        return max(55, float(intervalo_base) * ANCORA_INTERVALO_MULT)
    return intervalo_base


def _sustentar_zona(zona, tempo_atual):
    if not zona:
        return
    agora = int(tempo_atual)
    zona["ultimo_disparo_ms"] = agora
    zona["dissipando"] = False
    extra = DOMINIO_DISSIPAR_MS if zona.get("tipo_manifestacao") == "dominio_ancorado" else ANCORA_DISSIPAR_MS
    zona["fim_ms"] = max(int(zona.get("fim_ms", agora)), agora + extra * 2)


def _plantar_ancora(x, y, tempo_atual, dano_base):
    global _ULTIMA_ANCORA_PLANTADA_MS
    _limpar_expirados(tempo_atual)
    agora = int(tempo_atual)
    for ancora in _ANCORAS:
        if _zona_contem(ancora, x, y, margem=24):
            _sustentar_zona(ancora, agora)
            return ancora
    if agora - _ULTIMA_ANCORA_PLANTADA_MS < ANCORA_PLANTAR_INTERVALO_MS:
        zona = _zona_no_ponto(x, y)
        _sustentar_zona(zona, agora)
        return zona
    _ULTIMA_ANCORA_PLANTADA_MS = agora
    _ANCORAS.append({
        "x": float(x),
        "y": float(y),
        "criada_ms": agora,
        "fim_ms": agora + ANCORA_DURACAO_MS,
        "ultimo_tick_ms": agora,
        "ultimo_disparo_ms": agora,
        "dissipando": False,
        "dano_base": max(1.0, float(dano_base or 1.0)),
        "raio": ANCORA_RAIO,
        "seed": random.randint(1000, 999999),
    })
    if len(_ANCORAS) > ANCORA_MAX:
        del _ANCORAS[:-ANCORA_MAX]
    return _ANCORAS[-1]


def criar_auto_attack(manifestacao, vfx, centro_x, centro_y, largura, altura, angulo, velocidade, tempo_atual, impulsiva=False, plantar_ancora=True):
    if not ativa(manifestacao):
        return gravitante_manifestacao.criar_auto_attack(
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

    zona = _zona_no_ponto(centro_x, centro_y)
    if plantar_ancora:
        if zona:
            _sustentar_zona(zona, tempo_atual)
        else:
            zona = _plantar_ancora(centro_x, centro_y, tempo_atual, max(1.0, largura + altura))
    territorio = _tipo_territorio(zona)
    disparo = vfx.criar_disparo(centro_x, centro_y, largura, altura, angulo, velocidade, tempo_atual, impulsiva)
    disparo["tipo_manifestacao"] = "ancorada_disparo"
    disparo["raio_vfx"] = max(5, min(12, int(min(largura, altura) * 0.55)))
    disparo["dano_mult_manifestacao"] = (
        DOMINIO_DANO_DISPARO_MULT if territorio == "dominio"
        else ANCORA_DANO_DISPARO_MULT if territorio == "ancora"
        else 0.92
    )
    disparo["ancorada_territorio"] = territorio or "fora"
    disparo["seed_ancorada"] = random.randint(1000, 999999)
    return disparo


def multiplicador_dano_disparo(disparo):
    if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "ancorada_disparo":
        return float(disparo.get("dano_mult_manifestacao", 1.0))
    return 1.0


def criar_dominio_fixo(x, y, tempo_atual, dano_base):
    dominio = {
        "tipo_manifestacao": "dominio_ancorado",
        "rect": pygame.Rect(int(x - DOMINIO_RAIO), int(y - DOMINIO_RAIO), DOMINIO_RAIO * 2, DOMINIO_RAIO * 2),
        "x": float(x),
        "y": float(y),
        "raio": DOMINIO_RAIO,
        "tempo_inicio": int(tempo_atual),
        "fim_ms": int(tempo_atual) + DOMINIO_DURACAO_MS,
        "ultimo_tick_ms": int(tempo_atual),
        "ultimo_disparo_ms": int(tempo_atual),
        "dissipando": False,
        "dano_base": max(1.0, float(dano_base)),
        "seed": random.randint(1000, 999999),
    }
    _DOMINIOS.append(dominio)
    if len(_DOMINIOS) > 2:
        del _DOMINIOS[:-2]
    return dict(dominio)


def processar_dominio_fixo(dominio, tempo_atual):
    return int(tempo_atual) < int(dominio.get("fim_ms", 0))


def _jogador_dentro_da_zona(zona, jogador_rect):
    if jogador_rect is None:
        return True
    try:
        cx, cy = jogador_rect.center
    except AttributeError:
        return True
    return _zona_contem(zona, cx, cy)


def _atualizar_dissipacao(jogador_rect, tempo_atual):
    agora = int(tempo_atual)
    for zona in list(_ANCORAS) + list(_DOMINIOS):
        dominio = zona.get("tipo_manifestacao") == "dominio_ancorado"
        janela = DOMINIO_SUSTENTAR_MS if dominio else ANCORA_SUSTENTAR_MS
        dissipar_ms = DOMINIO_DISSIPAR_MS if dominio else ANCORA_DISSIPAR_MS
        sem_disparo = agora - int(zona.get("ultimo_disparo_ms", zona.get("criada_ms", agora))) > janela
        fora = not _jogador_dentro_da_zona(zona, jogador_rect)
        if sem_disparo or fora:
            zona["dissipando"] = True
            zona["fim_ms"] = min(int(zona.get("fim_ms", agora)), agora + dissipar_ms)


def atualizar_territorio(inimigos, tempo_atual, dano_base, jogador_rect=None, efeitos_texto=None):
    _limpar_expirados(tempo_atual)
    _atualizar_dissipacao(jogador_rect, tempo_atual)
    mortos = []
    zonas = list(_ANCORAS) + list(_DOMINIOS)
    for zona in zonas:
        intervalo = DOMINIO_TICK_MS if zona.get("tipo_manifestacao") == "dominio_ancorado" else ANCORA_TICK_MS
        if int(tempo_atual) - int(zona.get("ultimo_tick_ms", 0)) < intervalo:
            continue
        zona["ultimo_tick_ms"] = int(tempo_atual)
        raio = float(zona.get("raio", ANCORA_RAIO))
        mult = DOMINIO_DANO_TICK_MULT if zona.get("tipo_manifestacao") == "dominio_ancorado" else ANCORA_DANO_TICK_MULT
        for inimigo in inimigos or []:
            if not isinstance(inimigo, dict) or inimigo.get("vida", 1) <= 0:
                continue
            rect = inimigo.get("rect")
            if rect is None:
                continue
            if _distancia(rect.centerx, rect.centery, zona["x"], zona["y"]) > raio + min(rect.width, rect.height) * 0.3:
                continue
            inimigo["marca_ancorada_fim_ms"] = int(tempo_atual) + 1800
            dano = max(1.0, float(zona.get("dano_base", dano_base)) * mult)
            inimigo["vida"] -= dano
            _texto(efeitos_texto, f"-{int(dano)}", rect, tempo_atual, COR_ANCORADA)
            if inimigo.get("vida", 1) <= 0 and inimigo not in mortos:
                mortos.append(inimigo)
    return mortos


def aplicar_lentidao_projeteis(projeteis, tempo_atual):
    _limpar_expirados(tempo_atual)
    if not _DOMINIOS:
        for projetil in projeteis or []:
            _restaurar_projetil(projetil)
        return
    for projetil in projeteis or []:
        rect = projetil.get("rect") if isinstance(projetil, dict) else None
        if rect is None:
            continue
        dentro = any(
            _distancia(rect.centerx, rect.centery, dominio["x"], dominio["y"]) <= float(dominio.get("raio", DOMINIO_RAIO))
            for dominio in _DOMINIOS
        )
        if dentro:
            _lentificar_projetil(projetil)
        else:
            _restaurar_projetil(projetil)


def _lentificar_projetil(projetil):
    if "velocidade" in projetil and isinstance(projetil["velocidade"], (tuple, list)):
        if "_velocidade_ancorada_original" not in projetil:
            projetil["_velocidade_ancorada_original"] = tuple(projetil["velocidade"])
        vx, vy = projetil["_velocidade_ancorada_original"]
        projetil["velocidade"] = (vx * DOMINIO_LENTIDAO_PROJETIL, vy * DOMINIO_LENTIDAO_PROJETIL)
    for chave in ("dx", "dy", "vx", "vy"):
        if chave in projetil and isinstance(projetil[chave], (int, float)):
            orig = f"_{chave}_ancorada_original"
            if orig not in projetil:
                projetil[orig] = projetil[chave]
            projetil[chave] = projetil[orig] * DOMINIO_LENTIDAO_PROJETIL


def _restaurar_projetil(projetil):
    if not isinstance(projetil, dict):
        return
    if "_velocidade_ancorada_original" in projetil:
        projetil["velocidade"] = projetil.pop("_velocidade_ancorada_original")
    for chave in ("dx", "dy", "vx", "vy"):
        orig = f"_{chave}_ancorada_original"
        if orig in projetil:
            projetil[chave] = projetil.pop(orig)


def desenhar_territorios(tela, tempo_atual, config_graficos=None, jogador_rect=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        return
    _limpar_expirados(tempo_atual)
    for ancora in _ANCORAS:
        _desenhar_zona(tela, ancora, tempo_atual, perfil, False, jogador_rect)
    for dominio in _DOMINIOS:
        _desenhar_zona(tela, dominio, tempo_atual, perfil, True, jogador_rect)


def desenhar_disparo_ancorado(tela, disparo, tempo_atual, offset=(0, 0), config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        return
    ox, oy = offset
    cx = disparo["rect"].centerx + ox
    cy = disparo["rect"].centery + oy
    trail = disparo.get("trail", [])
    rastro = 7 if perfil == "alto" else 5 if perfil == "medio" else 3
    for idx, (tx, ty) in enumerate(reversed(trail[-rastro:])):
        fade = 1.0 - idx / max(1, rastro)
        pygame.draw.circle(tela, COR_ANCORADA_ESCURA, (int(tx + ox), int(ty + oy)), max(2, int(8 * fade)), 1)
        pygame.draw.circle(tela, COR_ANCORADA, (int(tx + ox), int(ty + oy)), max(1, int(3 * fade)))
    raio = int(disparo.get("raio_vfx", 8))
    pygame.draw.circle(tela, COR_ANCORADA_ESCURA, (int(cx), int(cy)), raio + 7)
    pygame.draw.circle(tela, COR_ANCORADA, (int(cx), int(cy)), raio + 3, 2)
    pygame.draw.circle(tela, COR_ANCORADA_CLARA, (int(cx), int(cy)), max(2, raio // 2))
    if disparo.get("ancorada_territorio") in ("ancora", "dominio"):
        pygame.draw.line(tela, COR_ANCORADA_DOURADA, (int(cx - raio - 3), int(cy)), (int(cx + raio + 3), int(cy)), 1)
        pygame.draw.line(tela, COR_ANCORADA_DOURADA, (int(cx), int(cy - raio - 3)), (int(cx), int(cy + raio + 3)), 1)


def _forca_visual_zona(zona, tempo_atual, dominio):
    inicio = int(zona.get("tempo_inicio", zona.get("criada_ms", tempo_atual)))
    fim = int(zona.get("fim_ms", tempo_atual))
    restante = max(0.0, min(1.0, (fim - int(tempo_atual)) / max(1.0, fim - inicio)))
    entrada = max(0.15, min(1.0, (int(tempo_atual) - inicio) / 260.0))
    base = 0.46 if dominio else 0.34
    if zona.get("dissipando"):
        return max(0.0, min(base, restante * 0.75))
    return base * entrada


def _desenhar_zona(tela, zona, tempo_atual, perfil, dominio, jogador_rect=None):
    vida = _forca_visual_zona(zona, tempo_atual, dominio)
    if vida <= 0:
        return
    inicio = int(zona.get("tempo_inicio", zona.get("criada_ms", tempo_atual)))
    raio = int(zona.get("raio", DOMINIO_RAIO if dominio else ANCORA_RAIO))
    alpha = int((44 if dominio else 28) * vida)
    margem = 22 if perfil == "baixo" else 42 if perfil == "medio" else 66
    surf = pygame.Surface((raio * 2 + margem * 2, raio * 2 + margem * 2), pygame.SRCALPHA)
    c = raio + margem
    cor_base = COR_ANCORADA_DOURADA if dominio else COR_ANCORADA
    pulso = 0.5 + 0.5 * math.sin(tempo_atual * (0.005 if dominio else 0.007) + zona.get("seed", 0))
    pygame.draw.circle(surf, (*COR_ANCORADA_ESCURA, max(3, alpha // 2)), (c, c), raio, 1)
    pygame.draw.circle(surf, (*cor_base, max(6, alpha + int(8 * pulso))), (c, c), raio, 2)
    if perfil != "baixo":
        pygame.draw.circle(surf, (*cor_base, max(2, alpha // 3)), (c, c), max(18, int(raio * 0.72)), 1)
        pygame.draw.circle(surf, (*COR_ANCORADA_ESCURA, max(3, alpha // 2)), (c, c), max(8, int(raio * 0.18)))
    pontas = 12 if dominio and perfil == "alto" else 8 if perfil != "baixo" else 5
    giro = tempo_atual * (0.0025 if dominio else 0.004)
    for i in range(pontas):
        ang = giro + i * math.tau / pontas
        p1 = (c + int(math.cos(ang) * raio * 0.72), c + int(math.sin(ang) * raio * 0.72))
        p2 = (c + int(math.cos(ang) * raio), c + int(math.sin(ang) * raio))
        pygame.draw.line(surf, (*cor_base, max(10, alpha + 16)), p1, p2, 1)
    if perfil == "alto":
        for i in range(4):
            arco = pygame.Rect(c - raio - 12 + i * 6, c - raio - 12 + i * 6, (raio + 12 - i * 6) * 2, (raio + 12 - i * 6) * 2)
            ini = giro * (1.2 + i * 0.15) + i * 0.8
            pygame.draw.arc(surf, (*cor_base, max(8, alpha + 16 - i * 4)), arco, ini, ini + 0.95, 2)
    tela.blit(surf, (int(zona["x"]) - c, int(zona["y"]) - c))
    _desenhar_ancoras_orbitais(tela, zona, tempo_atual, perfil, dominio, jogador_rect, vida)


def _centro_orbita(zona, jogador_rect=None):
    if jogador_rect is not None:
        try:
            cx, cy = jogador_rect.center
            if _distancia(cx, cy, zona["x"], zona["y"]) <= float(zona.get("raio", ANCORA_RAIO)):
                return float(cx), float(cy), True
        except AttributeError:
            pass
    return float(zona["x"]), float(zona["y"]), False


def _desenhar_ancoras_orbitais(tela, zona, tempo_atual, perfil, dominio, jogador_rect, vida):
    mundo_cx, mundo_cy, orbitando_jogador = _centro_orbita(zona, jogador_rect)
    cor_base = COR_ANCORADA_DOURADA if dominio else COR_ANCORADA
    cor_luz = COR_ANCORADA_CLARA if dominio else (190, 255, 255)
    raio_orbita = 58 if dominio else 46
    if orbitando_jogador:
        raio_orbita = 50 if dominio else 40
    margem = int(raio_orbita + (78 if perfil == "alto" else 54 if perfil == "medio" else 36))
    layer = pygame.Surface((margem * 2, margem * 2), pygame.SRCALPHA)
    cx = cy = float(margem)
    velocidade = 0.0062 if dominio else 0.0078
    seed = int(zona.get("seed", 0))
    fase = tempo_atual * velocidade + (seed % 628) / 100.0
    pontos = []
    for i in range(4):
        ang = fase + i * math.tau / 4.0
        ax = cx + math.cos(ang) * raio_orbita
        ay = cy + math.sin(ang) * raio_orbita
        pontos.append((ax, ay, ang))

    if perfil != "baixo":
        _desenhar_vento_orbital(layer, cx, cy, raio_orbita, fase, cor_base, perfil, vida)
        _desenhar_particulas_orbitais(layer, zona, cx, cy, raio_orbita, fase, cor_base, perfil, dominio, vida)

    for i, (ax, ay, _) in enumerate(pontos):
        prox = pontos[(i + 1) % len(pontos)]
        _desenhar_corrente(layer, (ax, ay), (prox[0], prox[1]), cor_base, perfil, vida)
        _desenhar_corrente(layer, (cx, cy), (ax, ay), cor_base, perfil, vida, radial=True)

    if perfil == "alto":
        pygame.draw.circle(layer, COR_ANCORADA_ESCURA, (int(cx), int(cy)), int(raio_orbita * 0.58), 1)
        pygame.draw.circle(layer, cor_base, (int(cx), int(cy)), int(raio_orbita * 0.34), 1)
        for i in range(8):
            ang = -fase * 0.8 + i * math.tau / 8.0
            p1 = (int(cx + math.cos(ang) * raio_orbita * 0.28), int(cy + math.sin(ang) * raio_orbita * 0.28))
            p2 = (int(cx + math.cos(ang) * raio_orbita * 0.46), int(cy + math.sin(ang) * raio_orbita * 0.46))
            pygame.draw.line(layer, cor_luz, p1, p2, 1)

    for ax, ay, ang in pontos:
        _desenhar_glifo_ancora(layer, ax, ay, ang, cor_base, cor_luz, perfil, vida)
    opacidade = 96 if perfil == "alto" else 84 if perfil == "medio" else 68
    if zona.get("dissipando"):
        opacidade = int(opacidade * 0.62)
    layer.set_alpha(max(18, int(opacidade * max(0.15, min(1.0, vida)))))
    tela.blit(layer, (int(mundo_cx) - margem, int(mundo_cy) - margem))


def _desenhar_corrente(tela, p1, p2, cor_base, perfil, vida, radial=False):
    x1, y1 = p1
    x2, y2 = p2
    largura = 3 if perfil == "alto" and not radial else 2
    pygame.draw.line(tela, COR_ANCORADA_ESCURA, (int(x1), int(y1)), (int(x2), int(y2)), largura + 2)
    pygame.draw.line(tela, cor_base, (int(x1), int(y1)), (int(x2), int(y2)), largura)
    if perfil == "baixo":
        return
    dx = x2 - x1
    dy = y2 - y1
    dist = max(1.0, math.hypot(dx, dy))
    nx = -dy / dist
    ny = dx / dist
    links = 4 if radial else 5
    for i in range(1, links):
        t = i / float(links)
        lx = x1 + dx * t
        ly = y1 + dy * t
        tam = 3 if perfil == "medio" else 4
        pygame.draw.line(
            tela,
            COR_ANCORADA_CLARA if i % 2 else cor_base,
            (int(lx - nx * tam), int(ly - ny * tam)),
            (int(lx + nx * tam), int(ly + ny * tam)),
            1,
        )


def _desenhar_glifo_ancora(tela, ax, ay, ang, cor_base, cor_luz, perfil, vida):
    tamanho = 10 if perfil == "baixo" else 12 if perfil == "medio" else 15
    dx = math.cos(ang)
    dy = math.sin(ang)
    tx = -dy
    ty = dx
    ponta = (int(ax + dx * tamanho), int(ay + dy * tamanho))
    costas = (int(ax - dx * tamanho * 0.82), int(ay - dy * tamanho * 0.82))
    lado_a = (int(ax + tx * tamanho * 0.78), int(ay + ty * tamanho * 0.78))
    lado_b = (int(ax - tx * tamanho * 0.78), int(ay - ty * tamanho * 0.78))
    centro = (int(ax), int(ay))
    if perfil == "alto":
        pygame.draw.circle(tela, COR_ANCORADA_ESCURA, centro, tamanho + 9)
        pygame.draw.circle(tela, cor_base, centro, tamanho + 5, 1)
    pygame.draw.polygon(tela, COR_ANCORADA_ESCURA, [ponta, lado_a, costas, lado_b], 0)
    pygame.draw.polygon(tela, cor_base, [ponta, lado_a, costas, lado_b], 2)
    pygame.draw.line(tela, cor_luz, (int(ax - tx * tamanho * 0.5), int(ay - ty * tamanho * 0.5)), (int(ax + tx * tamanho * 0.5), int(ay + ty * tamanho * 0.5)), 2)
    pygame.draw.circle(tela, cor_luz, centro, max(2, tamanho // 4))
    if perfil != "baixo":
        gancho_a = (int(ax - dx * tamanho * 1.12 + tx * tamanho * 0.52), int(ay - dy * tamanho * 1.12 + ty * tamanho * 0.52))
        gancho_b = (int(ax - dx * tamanho * 1.12 - tx * tamanho * 0.52), int(ay - dy * tamanho * 1.12 - ty * tamanho * 0.52))
        pygame.draw.line(tela, cor_base, costas, gancho_a, 2)
        pygame.draw.line(tela, cor_base, costas, gancho_b, 2)


def _desenhar_vento_orbital(tela, cx, cy, raio, fase, cor_base, perfil, vida):
    quantidade = 3 if perfil == "medio" else 6
    for i in range(quantidade):
        r = raio + 10 + i * (5 if perfil == "medio" else 4)
        ret = pygame.Rect(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        ini = fase * (0.9 + i * 0.07) + i * 0.55
        cor = cor_base if i % 2 else COR_ANCORADA_CLARA
        pygame.draw.arc(tela, COR_ANCORADA_ESCURA, ret, ini, ini + 0.72, 2)
        pygame.draw.arc(tela, cor, ret, ini, ini + 0.5, 1)


def _desenhar_particulas_orbitais(tela, zona, cx, cy, raio, fase, cor_base, perfil, dominio, vida):
    quantidade = 10 if perfil == "medio" else 24
    rng = random.Random(int(zona.get("seed", 0)) + int(tempo_frame_particula(zona, fase)))
    for i in range(quantidade):
        ang = fase * (0.7 + (i % 5) * 0.03) + rng.random() * math.tau
        distancia = raio * (0.62 + rng.random() * (1.35 if dominio else 1.0))
        px = cx + math.cos(ang) * distancia
        py = cy + math.sin(ang) * distancia
        tamanho = 1 if rng.random() < 0.62 else 2
        cor = COR_ANCORADA_DOURADA if dominio and i % 3 == 0 else cor_base
        pygame.draw.circle(tela, cor, (int(px), int(py)), tamanho)
        if perfil == "alto" and rng.random() < 0.42:
            tx = -math.sin(ang) * (4 + rng.random() * 8)
            ty = math.cos(ang) * (4 + rng.random() * 8)
            pygame.draw.line(tela, COR_ANCORADA_CLARA, (int(px), int(py)), (int(px + tx), int(py + ty)), 1)


def tempo_frame_particula(zona, fase):
    return int(fase * 100.0) // 8 + int(zona.get("fim_ms", 0)) // 113
