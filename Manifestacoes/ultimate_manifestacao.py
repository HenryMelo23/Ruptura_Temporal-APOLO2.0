# -*- coding: utf-8 -*-
import math
import random

import pygame

try:
    from dados_manifestacoes import MANIFESTACOES_DADOS
except Exception:
    MANIFESTACOES_DADOS = {}


ULTIMATE_COOLDOWN_MS = 75000
TESLA_DURACAO_MS = 4000
LACERANTE_DURACAO_MS = 10000
PRISMATICA_DURACAO_MS = 3000
RETORNANTE_DURACAO_MS = 4000
PARASITICA_DURACAO_MS = 4000
CONDUTORA_DURACAO_MS = 4000
GRAVITANTE_DURACAO_MS = 4000
ANCORADA_DURACAO_MS = 4000

DURACOES_MS = {
    "eletrica": TESLA_DURACAO_MS,
    "lacerante": LACERANTE_DURACAO_MS,
    "prismatica": PRISMATICA_DURACAO_MS,
    "retornante": RETORNANTE_DURACAO_MS,
    "parasitica": PARASITICA_DURACAO_MS,
    "condutora": CONDUTORA_DURACAO_MS,
    "gravitante": GRAVITANTE_DURACAO_MS,
    "ancorada": ANCORADA_DURACAO_MS,
}

TICKS_MS = {
    "eletrica": 360,
    "lacerante": 155,
    "prismatica": 120,
    "retornante": 420,
    "parasitica": 520,
    "condutora": 420,
    "gravitante": 360,
    "ancorada": 460,
}

NOMES_ULTIMATE = {
    "eletrica": "Anel de Tesla",
    "lacerante": "Carnificina Temporal",
    "prismatica": "Supernova Prismatica",
    "retornante": "Paradoxo Recorrente",
    "parasitica": "Epidemia Voraz",
    "condutora": "Circuito Absoluto",
    "gravitante": "Colapso Orbital",
    "ancorada": "Marco Zero",
}

_ultimo_uso_ms = pygame.time.get_ticks() - ULTIMATE_COOLDOWN_MS
_FONT_CACHE = {}
_lacerante_execucao_fim_ms = 0


def _manifestacao(chave):
    chave = str(chave or "eletrica").strip().lower()
    return chave if chave in NOMES_ULTIMATE else "eletrica"


def nome_ultimate(manifestacao):
    return NOMES_ULTIMATE.get(_manifestacao(manifestacao), NOMES_ULTIMATE["eletrica"])


def cooldown_ms(_manifestacao_ativa=None):
    return ULTIMATE_COOLDOWN_MS


def resetar_cooldown(tempo_atual=None, pronta=False):
    global _ultimo_uso_ms
    agora = pygame.time.get_ticks() if tempo_atual is None else int(tempo_atual)
    _ultimo_uso_ms = agora - ULTIMATE_COOLDOWN_MS if pronta else agora


def registrar_uso(tempo_atual):
    global _ultimo_uso_ms
    _ultimo_uso_ms = int(tempo_atual)


def restante_ms(tempo_atual):
    return max(0, ULTIMATE_COOLDOWN_MS - (int(tempo_atual) - int(_ultimo_uso_ms)))


def disponivel(tempo_atual):
    return restante_ms(tempo_atual) <= 0


def acionamento_por_evento(event, joystick=None):
    if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
        return True
    return bool(event.type == pygame.JOYBUTTONDOWN and getattr(event, "button", None) == 3)


def jogador_bloqueado(tempo_atual):
    return int(tempo_atual) < int(_lacerante_execucao_fim_ms)


def jogador_oculto(tempo_atual):
    return jogador_bloqueado(tempo_atual)


def _fonte(tamanho):
    tamanho = int(tamanho)
    fonte = _FONT_CACHE.get(tamanho)
    if fonte is None:
        fonte = pygame.font.Font(None, tamanho)
        _FONT_CACHE[tamanho] = fonte
    return fonte


def _cores(manifestacao):
    dados = MANIFESTACOES_DADOS.get(_manifestacao(manifestacao), {})
    return (
        tuple(dados.get("cor", (0, 225, 255))),
        tuple(dados.get("cor_secundaria", (160, 90, 255))),
    )


def _clamp(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def _dist(a, b):
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _dist_linha(px, py, ax, ay, bx, by):
    dx = bx - ax
    dy = by - ay
    denom = dx * dx + dy * dy
    if denom <= 0.001:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    lx = ax + dx * t
    ly = ay + dy * t
    return math.hypot(px - lx, py - ly)


def _alvos_vivos(inimigos):
    return [
        alvo for alvo in list(inimigos or [])
        if isinstance(alvo, dict) and alvo.get("rect") is not None and float(alvo.get("vida", 1)) > 0
    ]


def _id_alvo(alvo):
    if isinstance(alvo, dict):
        return alvo.get("ultimate_id", id(alvo))
    return id(alvo)


def _dano_com_janela(onda, alvo, canal, tempo_atual, dano, intervalo_ms, stun_ms=0):
    if not isinstance(alvo, dict) or float(alvo.get("vida", 1)) <= 0:
        return False
    atingidos = onda.setdefault("atingidos", {})
    por_alvo = atingidos.setdefault(_id_alvo(alvo), {})
    if int(tempo_atual) - int(por_alvo.get(canal, -999999)) < int(intervalo_ms):
        return False
    por_alvo[canal] = int(tempo_atual)
    alvo["vida"] = float(alvo.get("vida", 1)) - max(1.0, float(dano))
    if stun_ms:
        alvo["stun_fim"] = max(int(alvo.get("stun_fim", 0)), int(tempo_atual) + int(stun_ms))
    return float(alvo.get("vida", 1)) <= 0


def _boss_ativo(boss_info):
    return bool(boss_info and boss_info.get("vivo") and boss_info.get("rect"))


def _aplicar_boss(onda, boss_info, tempo_atual, dano, intervalo_ms=500):
    if not _boss_ativo(boss_info):
        return False
    if int(tempo_atual) - int(onda.get("ultimo_boss_ms", -999999)) < int(intervalo_ms):
        return False
    onda["ultimo_boss_ms"] = int(tempo_atual)
    boss_info["atingido_por_onda"] = int(tempo_atual)
    boss_info["hit_flag"] = True
    boss_info["dano_manifestacao"] = max(1.0, float(dano))
    return True


def _ponto_seguro(x, y, largura_mapa, altura_mapa, margem=72):
    return (
        _clamp(float(x), margem, max(margem, float(largura_mapa) - margem)),
        _clamp(float(y), margem, max(margem, float(altura_mapa) - margem)),
    )


def _draw_raio(tela, p1, p2, cor, cor2, largura=2, jitter=10):
    x1, y1 = p1
    x2, y2 = p2
    pontos = [(int(x1), int(y1))]
    for i in range(1, 6):
        t = i / 6.0
        pontos.append((
            int(x1 + (x2 - x1) * t + random.randint(-jitter, jitter)),
            int(y1 + (y2 - y1) * t + random.randint(-jitter, jitter)),
        ))
    pontos.append((int(x2), int(y2)))
    pygame.draw.lines(tela, cor2, False, pontos, max(1, largura + 2))
    pygame.draw.lines(tela, (245, 255, 255), False, pontos, max(1, largura // 2))
    pygame.draw.lines(tela, cor, False, pontos, max(1, largura))


def _criar_particulas(chave, cx, cy, cor, cor2):
    total = 70 if chave in ("eletrica", "prismatica", "gravitante") else 48
    particulas = []
    for i in range(total):
        particulas.append({
            "ang": random.random() * math.tau,
            "dist": random.uniform(18, 185),
            "speed": random.uniform(0.7, 3.4),
            "tam": random.randint(1, 3),
            "fase": random.random() * math.tau,
            "cor": cor if i % 2 else cor2,
        })
    return particulas


def criar_ultimate(manifestacao, centro_x, centro_y, cursor, tempo_atual, dano_base, largura_mapa, altura_mapa, intervalo_disparo_ref=None):
    global _lacerante_execucao_fim_ms
    chave = _manifestacao(manifestacao)
    cor, cor2 = _cores(chave)
    alvo = cursor or (centro_x, centro_y)
    duracao = DURACOES_MS.get(chave, 4000)
    origem_x, origem_y = (alvo if chave == "lacerante" else (centro_x, centro_y))
    if chave == "lacerante":
        _lacerante_execucao_fim_ms = int(tempo_atual) + duracao
    onda = {
        "tipo_manifestacao": "ultimate_manifestacao",
        "manifestacao": chave,
        "nome": nome_ultimate(chave),
        "cx": float(origem_x),
        "cy": float(origem_y),
        "cursor": (float(alvo[0]), float(alvo[1])),
        "inicio_ms": int(tempo_atual),
        "fim_ms": int(tempo_atual) + duracao,
        "ultimo_tick_ms": int(tempo_atual) - 999999,
        "tick_ms": TICKS_MS.get(chave, 420),
        "dano_base": max(1.0, float(dano_base)),
        "intervalo_disparo_ref": float(intervalo_disparo_ref) if intervalo_disparo_ref is not None else 650.0,
        "largura_mapa": int(largura_mapa),
        "altura_mapa": int(altura_mapa),
        "cor": cor,
        "cor2": cor2,
        "atingidos": {},
        "ultimo_boss_ms": -999999,
        "particulas": _criar_particulas(chave, origem_x, origem_y, cor, cor2),
        "seed": random.randint(1000, 999999),
    }
    onda["estado"] = _criar_estado(chave, origem_x, origem_y, alvo, tempo_atual, largura_mapa, altura_mapa)
    return onda


def _criar_estado(chave, cx, cy, cursor, tempo_atual, largura_mapa, altura_mapa):
    estado = {"criado_ms": int(tempo_atual), "finalizado": False}
    if chave == "eletrica":
        estado.update({"raio": 150.0, "pulso_ms": int(tempo_atual), "correntes": []})
    elif chave == "lacerante":
        estado.update({
            "cortes_total": 10,
            "cortes_feitos": 0,
            "cortes": [],
            "proximo_corte_ms": int(tempo_atual),
            "escurecer": False,
        })
    elif chave == "prismatica":
        estado.update({"proximo_feixe_ms": int(tempo_atual), "feixes": [], "contador": 0})
    elif chave == "retornante":
        estado.update({"pulsos_marcados": False, "pulsos_ids": [], "final_forcado": False, "rastros": []})
    elif chave == "parasitica":
        estado.update({"preparada": False, "proximo_espalhar_ms": int(tempo_atual), "explodiu_final": False})
    elif chave == "condutora":
        estado.update({"porta": random.choice(("OR", "AND", "XOR", "NAND", "NOR")), "links": [], "sobrecarga": 0, "detonou": False})
    elif chave == "gravitante":
        gx, gy = _ponto_seguro(cursor[0], cursor[1], largura_mapa, altura_mapa)
        estado.update({"x": gx, "y": gy, "puxados": set(), "orbes": set(), "colapsou": False})
    elif chave == "ancorada":
        estado.update({"x": float(cx), "y": float(cy), "carga_ms": 0, "ultimo_player_ms": int(tempo_atual), "ultimo_pulso_ms": int(tempo_atual), "onda_final": False})
    return estado


def _tick_pronto(onda, tempo_atual):
    if int(tempo_atual) - int(onda.get("ultimo_tick_ms", 0)) < int(onda.get("tick_ms", 420)):
        return False
    onda["ultimo_tick_ms"] = int(tempo_atual)
    return True


def processar_ultimate(onda, inimigos, boss_info, tela, tempo_atual, config_graficos=None, disparos=None, player_center=None):
    chave = _manifestacao(onda.get("manifestacao"))
    inicio = int(onda.get("inicio_ms", tempo_atual))
    fim = int(onda.get("fim_ms", tempo_atual))
    duracao = max(1, fim - inicio)
    progresso = _clamp((int(tempo_atual) - inicio) / float(duracao), 0.0, 1.0)
    player_center = player_center or (onda.get("cx", 0), onda.get("cy", 0))

    if chave == "eletrica":
        onda["cx"], onda["cy"] = float(player_center[0]), float(player_center[1])

    _desenhar_base(onda, tela, tempo_atual, progresso, config_graficos)
    mortos = []
    if chave == "eletrica":
        mortos = _tick_eletrica(onda, inimigos, boss_info, tela, tempo_atual, progresso, player_center)
    elif chave == "lacerante":
        mortos = _tick_lacerante(onda, inimigos, boss_info, tela, tempo_atual, progresso)
    elif chave == "prismatica":
        mortos = _tick_prismatica(onda, inimigos, boss_info, tela, tempo_atual, progresso)
    elif chave == "retornante":
        mortos = _tick_retornante(onda, inimigos, boss_info, tela, tempo_atual, progresso, disparos or [], player_center)
    elif chave == "parasitica":
        mortos = _tick_parasitica(onda, inimigos, boss_info, tela, tempo_atual, progresso)
    elif chave == "condutora":
        mortos = _tick_condutora(onda, inimigos, boss_info, tela, tempo_atual, progresso)
    elif chave == "gravitante":
        mortos = _tick_gravitante(onda, inimigos, boss_info, tela, tempo_atual, progresso, disparos or [])
    elif chave == "ancorada":
        mortos = _tick_ancorada(onda, inimigos, boss_info, tela, tempo_atual, progresso, player_center)

    return int(tempo_atual) < fim, [alvo for alvo in mortos if isinstance(alvo, dict)]


def _desenhar_base(onda, tela, tempo_atual, progresso, config_graficos):
    cfg = config_graficos if isinstance(config_graficos, dict) else {}
    if cfg and not cfg.get("efeitos_visuais", True):
        return
    particulas_ativas = cfg.get("particulas_ativas", True)
    qualidade = str(cfg.get("qualidade_grafica", "alta")).lower()
    cx, cy = int(onda.get("cx", 0)), int(onda.get("cy", 0))
    cor, cor2 = onda["cor"], onda["cor2"]
    raio = int(80 + 210 * (0.35 + 0.30 * math.sin(progresso * math.pi)))
    surf = pygame.Surface((raio * 2 + 12, raio * 2 + 12), pygame.SRCALPHA)
    centro = raio + 6
    pygame.draw.circle(surf, (*cor, 36), (centro, centro), raio, 2)
    pygame.draw.circle(surf, (*cor2, 22), (centro, centro), int(raio * 0.62), 1)
    tela.blit(surf, (cx - raio - 6, cy - raio - 6), special_flags=pygame.BLEND_RGBA_ADD)
    if not particulas_ativas or qualidade == "desativado":
        return
    passo = 1 if qualidade == "alta" else 3
    for p in onda.get("particulas", [])[::passo]:
        ang = p["ang"] + progresso * p["speed"] * 2.0
        dist = p["dist"] * (1.0 + 0.16 * math.sin(tempo_atual * 0.006 + p["fase"]))
        if onda.get("manifestacao") == "gravitante":
            dist *= max(0.35, 1.0 - progresso * 0.55)
        px = cx + math.cos(ang) * dist
        py = cy + math.sin(ang) * dist
        pygame.draw.circle(tela, p["cor"], (int(px), int(py)), p["tam"])


def _tick_eletrica(onda, inimigos, boss_info, tela, tempo_atual, progresso, player_center):
    cx, cy = player_center
    estado = onda["estado"]
    raio = float(estado.get("raio", 150.0)) + math.sin(tempo_atual * 0.012) * 18.0
    mortos = []
    pontos = []
    giro = tempo_atual * 0.006
    for i in range(18):
        ang = giro + i * math.tau / 18
        pontos.append((int(cx + math.cos(ang) * raio), int(cy + math.sin(ang) * raio)))
    if len(pontos) > 2:
        pygame.draw.lines(tela, onda["cor2"], True, pontos, 7)
        pygame.draw.lines(tela, (235, 255, 255), True, pontos, 2)
        pygame.draw.lines(tela, onda["cor"], True, pontos, 4)
    for i in range(0, len(pontos), 3):
        p1 = pontos[i]
        p2 = pontos[(i + 1) % len(pontos)]
        _draw_raio(tela, p1, p2, onda["cor"], onda["cor2"], 1, 6)

    tick_ok = _tick_pronto(onda, tempo_atual)
    tocando = []
    for alvo in _alvos_vivos(inimigos):
        dist = _dist((cx, cy), alvo["rect"].center)
        if abs(dist - raio) <= 42 or dist <= raio * 0.48:
            tocando.append(alvo)
            _draw_raio(tela, (cx, cy), alvo["rect"].center, onda["cor"], onda["cor2"], 2, 8)
            if tick_ok and _dano_com_janela(onda, alvo, "tesla", tempo_atual, onda["dano_base"] * 1.45, 330, 260):
                mortos.append(alvo)
    if tick_ok and tocando:
        for origem in random.sample(tocando, min(3, len(tocando))):
            candidatos = [a for a in _alvos_vivos(inimigos) if a is not origem and _dist(origem["rect"].center, a["rect"].center) <= 210]
            if candidatos:
                alvo = min(candidatos, key=lambda a: _dist(origem["rect"].center, a["rect"].center))
                _draw_raio(tela, origem["rect"].center, alvo["rect"].center, onda["cor"], onda["cor2"], 2, 9)
                if _dano_com_janela(onda, alvo, "tesla_salto", tempo_atual, onda["dano_base"] * 0.72, 520, 140):
                    mortos.append(alvo)
    if _boss_ativo(boss_info) and abs(_dist((cx, cy), boss_info["rect"].center) - raio) <= 70:
        _aplicar_boss(onda, boss_info, tempo_atual, onda["dano_base"] * 0.72, 520)
    return mortos


def _tick_lacerante(onda, inimigos, boss_info, tela, tempo_atual, progresso):
    estado = onda["estado"]
    mortos = []
    cx, cy = onda["cx"], onda["cy"]
    raio_aura = 92 + int(22 * math.sin(tempo_atual * 0.010) ** 2)
    pygame.draw.circle(tela, (95, 0, 18), (int(cx), int(cy)), raio_aura, 2)
    pygame.draw.circle(tela, (255, 42, 62), (int(cx), int(cy)), max(28, raio_aura // 2), 1)

    cadencia_bonus = _clamp((1000.0 / max(120.0, float(onda.get("intervalo_disparo_ref", 650.0)))) - 1.0, 0.0, 0.8)
    intervalo_corte = max(115, int(230 - cadencia_bonus * 75))
    limite_cortes_por_frame = 3
    cortes_gerados_frame = 0
    while int(tempo_atual) >= int(estado.get("proximo_corte_ms", tempo_atual)) and cortes_gerados_frame < limite_cortes_por_frame:
        idx = int(estado.get("cortes_feitos", 0))
        ang = onda["seed"] * 0.001 + idx * 2.399 + random.uniform(-0.28, 0.28)
        comp = random.uniform(250, 370)
        meio = random.uniform(-55, 55)
        ax = cx + math.cos(ang + math.pi / 2) * meio - math.cos(ang) * comp * 0.45
        ay = cy + math.sin(ang + math.pi / 2) * meio - math.sin(ang) * comp * 0.45
        bx = cx + math.cos(ang + math.pi / 2) * meio + math.cos(ang) * comp * 0.55
        by = cy + math.sin(ang + math.pi / 2) * meio + math.sin(ang) * comp * 0.55
        estado.setdefault("cortes", []).append({"linha": (ax, ay, bx, by), "ms": int(tempo_atual), "idx": idx})
        estado["cortes_feitos"] = idx + 1
        estado["proximo_corte_ms"] = int(estado.get("proximo_corte_ms", tempo_atual)) + intervalo_corte
        cortes_gerados_frame += 1

        for alvo in _alvos_vivos(inimigos):
            if _dist_linha(alvo["rect"].centerx, alvo["rect"].centery, ax, ay, bx, by) <= 54:
                lacerado = _alvo_lacerado(alvo)
                pct = 0.10 if lacerado else 0.06
                dano = max(1.0, float(alvo.get("vida_maxima", alvo.get("vida", 1))) * pct)
                if _dano_com_janela(onda, alvo, "lacerante_cortes", tempo_atual, dano, 240, 110):
                    mortos.append(alvo)
        if _boss_ativo(boss_info) and boss_info["rect"].clipline((ax, ay), (bx, by)):
            mult_boss = 1.80 if estado.get("boss_lacerado") else 1.20
            _aplicar_boss(onda, boss_info, tempo_atual, onda["dano_base"] * mult_boss, 130)

    sobreviventes = []
    for corte in estado.get("cortes", []):
        idade = int(tempo_atual) - int(corte["ms"])
        if idade > 360:
            continue
        fade = max(0.0, 1.0 - idade / 360.0)
        ax, ay, bx, by = corte["linha"]
        largura = max(1, int(10 * fade))
        pygame.draw.line(tela, (95, 0, 18), (int(ax), int(ay)), (int(bx), int(by)), largura + 5)
        pygame.draw.line(tela, (255, 42, 62), (int(ax), int(ay)), (int(bx), int(by)), largura)
        pygame.draw.line(tela, (255, 230, 220), (int(ax), int(ay)), (int(bx), int(by)), max(1, largura // 3))
        sobreviventes.append(corte)
    estado["cortes"] = sobreviventes
    return mortos


def _alvo_lacerado(alvo):
    lac = alvo.get("laceracao_temporal") or {}
    return bool(int(lac.get("stacks", 0)) > 0 or alvo.get("aberto_lacerante") or alvo.get("lacerado"))


def _calcular_segmentos_ricochete(cx, cy, ang, largura, altura, ricochetes=2, passo=520):
    segmentos = []
    x, y = float(cx), float(cy)
    vx, vy = math.cos(ang), math.sin(ang)
    restante = float(passo)
    for _ in range(ricochetes + 1):
        tx = float("inf") if abs(vx) < 0.001 else ((largura - x) / vx if vx > 0 else -x / vx)
        ty = float("inf") if abs(vy) < 0.001 else ((altura - y) / vy if vy > 0 else -y / vy)
        t = max(1.0, min(restante, tx, ty))
        nx, ny = x + vx * t, y + vy * t
        segmentos.append((x, y, nx, ny))
        restante -= t
        if restante <= 0:
            break
        if tx <= ty:
            vx *= -1
        else:
            vy *= -1
        x, y = _clamp(nx, 0, largura), _clamp(ny, 0, altura)
        restante = float(passo)
    return segmentos


def _tick_prismatica(onda, inimigos, boss_info, tela, tempo_atual, progresso):
    estado = onda["estado"]
    mortos = []
    cx, cy = onda["cx"], onda["cy"]
    cores = ((80, 235, 255), (255, 115, 185), (175, 95, 255), (255, 230, 130))
    if int(tempo_atual) >= int(estado.get("proximo_feixe_ms", 0)):
        estado["proximo_feixe_ms"] = int(tempo_atual) + 120
        base = tempo_atual * 0.002 + estado.get("contador", 0) * 0.19
        for i in range(10):
            ang = base + i * math.tau / 10
            estado.setdefault("feixes", []).append({
                "id": estado.get("contador", 0) * 100 + i,
                "ms": int(tempo_atual),
                "cor": cores[i % len(cores)],
                "segmentos": _calcular_segmentos_ricochete(cx, cy, ang, onda["largura_mapa"], onda["altura_mapa"], 2, 460),
            })
        estado["contador"] = int(estado.get("contador", 0)) + 1

    vivos = []
    for feixe in estado.get("feixes", []):
        idade = int(tempo_atual) - int(feixe["ms"])
        if idade > 280:
            continue
        alpha = max(55, int(230 * (1.0 - idade / 280.0)))
        for ax, ay, bx, by in feixe["segmentos"]:
            pygame.draw.line(tela, feixe["cor"], (int(ax), int(ay)), (int(bx), int(by)), 4)
            pygame.draw.line(tela, (255, 255, 255), (int(ax), int(ay)), (int(bx), int(by)), 1)
            if random.random() < 0.18:
                px = ax + (bx - ax) * random.random()
                py = ay + (by - ay) * random.random()
                pygame.draw.polygon(tela, (*feixe["cor"], alpha), [(int(px), int(py - 5)), (int(px + 5), int(py + 4)), (int(px - 5), int(py + 4))])
        vivos.append(feixe)
    estado["feixes"] = vivos

    for feixe in vivos:
        for alvo in _alvos_vivos(inimigos):
            if any(_dist_linha(alvo["rect"].centerx, alvo["rect"].centery, *seg) <= 20 for seg in feixe["segmentos"]):
                if _dano_com_janela(onda, alvo, f"prisma_{feixe['id']}", tempo_atual, onda["dano_base"] * 0.54, 1, 0):
                    mortos.append(alvo)
        if _boss_ativo(boss_info) and any(boss_info["rect"].clipline((seg[0], seg[1]), (seg[2], seg[3])) for seg in feixe["segmentos"]):
            _aplicar_boss(onda, boss_info, tempo_atual, onda["dano_base"] * 0.30, 190)
    return mortos


def _tick_retornante(onda, inimigos, boss_info, tela, tempo_atual, progresso, disparos, player_center):
    estado = onda["estado"]
    mortos = []
    pulsos = [
        d for d in list(disparos or [])
        if isinstance(d, dict) and d.get("tipo_manifestacao") == "retornante_pulso" and not d.get("expirado")
    ]
    if not estado.get("pulsos_marcados"):
        estado["pulsos_marcados"] = True
        for pulso in pulsos:
            pulso["retornante_paradoxo_ate"] = int(onda.get("fim_ms", tempo_atual))
            pulso["retornante_paradoxo_ciclos"] = 0
            pulso["retornante_marca_ms"] = int(tempo_atual)
            estado.setdefault("pulsos_ids", []).append(id(pulso))
        if not pulsos:
            for i in range(5):
                ang = i * math.tau / 5 + random.uniform(-0.20, 0.20)
                px = player_center[0] + math.cos(ang) * 260
                py = player_center[1] + math.sin(ang) * 210
                estado.setdefault("rastros", []).append({"ponto": (px, py), "fase": random.random(), "ultimo": -999999})

    for pulso in pulsos:
        p = pulso["rect"].center
        pygame.draw.line(tela, onda["cor2"], (int(player_center[0]), int(player_center[1])), p, 2)
        pygame.draw.circle(tela, onda["cor"], p, 18 + int(7 * math.sin(tempo_atual * 0.015)), 2)
        if _tick_pronto(onda, tempo_atual):
            ciclo = min(2, int(pulso.get("retornante_paradoxo_ciclos", 0)))
            mult = (1.0, 0.8, 0.65)[ciclo]
            for alvo in _alvos_vivos(inimigos):
                if _dist_linha(alvo["rect"].centerx, alvo["rect"].centery, player_center[0], player_center[1], p[0], p[1]) <= 34:
                    if _dano_com_janela(onda, alvo, f"paradoxo_{id(pulso)}", tempo_atual, onda["dano_base"] * 1.25 * mult, 410, 0):
                        mortos.append(alvo)
            if _boss_ativo(boss_info) and boss_info["rect"].clipline(player_center, p):
                _aplicar_boss(onda, boss_info, tempo_atual, onda["dano_base"] * 0.55 * mult, 520)

    for rastro in estado.get("rastros", []):
        px, py = rastro["ponto"]
        trem = math.sin(tempo_atual * 0.010 + rastro["fase"] * 7) * 12
        pygame.draw.line(tela, onda["cor2"], (int(player_center[0]), int(player_center[1])), (int(px), int(py + trem)), 3)

    if progresso >= 0.88 and not estado.get("final_forcado"):
        estado["final_forcado"] = True
        for pulso in pulsos:
            pulso["retornante_fase"] = "volta"
            pulso["retornante_forcado"] = True
            pulso["retornante_paradoxo_final"] = True
            pulso["memoria_retorno_bonus"] = max(float(pulso.get("memoria_retorno_bonus", 1.0)), 1.35)
            pulso["retornante_marca_ms"] = int(tempo_atual)
    return mortos


def _tick_parasitica(onda, inimigos, boss_info, tela, tempo_atual, progresso):
    estado = onda["estado"]
    mortos = []
    try:
        import parasitica_manifestacao
    except Exception:
        parasitica_manifestacao = None

    alvos = _alvos_vivos(inimigos)
    if not estado.get("preparada"):
        estado["preparada"] = True
        infectados = [a for a in alvos if a.get("semente_parasitica")]
        if not infectados:
            infectados = sorted(alvos, key=lambda a: _dist((onda["cx"], onda["cy"]), a["rect"].center))[:5]
        for alvo in infectados:
            if parasitica_manifestacao:
                semente = parasitica_manifestacao.implantar_semente(alvo, tempo_atual, onda["dano_base"])
                if semente:
                    semente["valor"] = max(float(semente.get("valor", 0)), getattr(parasitica_manifestacao, "SEMENTE_MADURA", 165.0))
                    semente["madura"] = True
            else:
                alvo["semente_parasitica"] = {"valor": 165.0, "madura": True, "dano_base": onda["dano_base"]}

    for alvo in alvos:
        if alvo.get("semente_parasitica") and alvo.get("rect"):
            rect = alvo["rect"]
            pygame.draw.circle(tela, (30, 95, 55), rect.center, max(rect.width, rect.height), 2)
            for i in range(5):
                ang = tempo_atual * 0.003 + i * math.tau / 5
                pygame.draw.line(tela, onda["cor2"], rect.center, (int(rect.centerx + math.cos(ang) * 28), int(rect.centery + math.sin(ang) * 28)), 2)

    if int(tempo_atual) >= int(estado.get("proximo_espalhar_ms", 0)):
        estado["proximo_espalhar_ms"] = int(tempo_atual) + 520
        infectados = [a for a in alvos if a.get("semente_parasitica")]
        for origem in infectados[:8]:
            candidatos = [a for a in alvos if a is not origem and not a.get("semente_parasitica") and _dist(origem["rect"].center, a["rect"].center) <= 260]
            if candidatos:
                alvo = min(candidatos, key=lambda a: _dist(origem["rect"].center, a["rect"].center))
                _draw_raio(tela, origem["rect"].center, alvo["rect"].center, onda["cor"], onda["cor2"], 2, 5)
                if parasitica_manifestacao:
                    parasitica_manifestacao.implantar_semente(alvo, tempo_atual, onda["dano_base"] * 0.55)
                else:
                    alvo["semente_parasitica"] = {"valor": 42.0, "madura": False, "dano_base": onda["dano_base"] * 0.55}
            if _dano_com_janela(onda, origem, "parasita_pulso", tempo_atual, onda["dano_base"] * 0.45, 500, 0):
                mortos.append(origem)
        if _boss_ativo(boss_info) and any(_dist(boss_info["rect"].center, a["rect"].center) <= 210 for a in infectados if a.get("rect")):
            _aplicar_boss(onda, boss_info, tempo_atual, onda["dano_base"] * 0.55, 650)

    if progresso >= 0.92 and not estado.get("explodiu_final"):
        estado["explodiu_final"] = True
        if parasitica_manifestacao:
            novos, _total = parasitica_manifestacao.eclodir_todas(alvos, tempo_atual)
            mortos.extend(novos)
        else:
            for alvo in alvos:
                if alvo.pop("semente_parasitica", None):
                    alvo["vida"] = float(alvo.get("vida", 1)) - onda["dano_base"] * 3.0
                    if alvo["vida"] <= 0:
                        mortos.append(alvo)
        if _boss_ativo(boss_info):
            _aplicar_boss(onda, boss_info, tempo_atual, onda["dano_base"] * 1.25, 450)
    return mortos


def _porta_logica(porta, a, b):
    a = 1 if a else 0
    b = 1 if b else 0
    porta = str(porta or "OR").upper()
    if porta == "AND":
        return 1 if a and b else 0
    if porta == "XOR":
        return 1 if a != b else 0
    if porta == "NAND":
        return 0 if a and b else 1
    if porta == "NOR":
        return 0 if a or b else 1
    return 1 if a or b else 0


def _tick_condutora(onda, inimigos, boss_info, tela, tempo_atual, progresso):
    estado = onda["estado"]
    porta = estado.get("porta", "OR")
    mortos = []
    alvos = sorted(_alvos_vivos(inimigos), key=lambda a: _dist((onda["cx"], onda["cy"]), a["rect"].center))[:14]
    nos = []
    for alvo in alvos:
        if "condutora_bit_ultimate" not in alvo:
            alvo["condutora_bit_ultimate"] = random.randint(0, 1)
        bit = int(alvo.get("condutora_bit_ultimate", 0))
        nos.append({"tipo": "inimigo", "obj": alvo, "ponto": alvo["rect"].center, "bit": bit})
        texto = _fonte(22).render(str(bit), True, (255, 245, 120) if bit else onda["cor2"])
        tela.blit(texto, (alvo["rect"].centerx - 5, alvo["rect"].top - 24))
    if _boss_ativo(boss_info):
        nos.append({"tipo": "boss", "obj": boss_info, "ponto": boss_info["rect"].center, "bit": 1})

    links = []
    for i, no in enumerate(nos):
        for outro in sorted((n for j, n in enumerate(nos) if j != i), key=lambda n: _dist(no["ponto"], n["ponto"]))[:1]:
            par = tuple(sorted((id(no["obj"]), id(outro["obj"]))))
            if any(l["par"] == par for l in links):
                continue
            ok = _porta_logica(porta, no["bit"], outro["bit"]) == 1
            links.append({"a": no, "b": outro, "ok": ok, "par": par})
    estado["links"] = links

    placa = _fonte(28).render(f"{porta} FIXO", True, (255, 240, 120))
    tela.blit(placa, (int(onda["cx"] - placa.get_width() / 2), int(onda["cy"] - 90)))
    for link in links:
        p1, p2 = link["a"]["ponto"], link["b"]["ponto"]
        if link["ok"]:
            _draw_raio(tela, p1, p2, onda["cor"], onda["cor2"], 3, 7)
        else:
            pygame.draw.line(tela, (72, 68, 92), p1, p2, 1)

    if _tick_pronto(onda, tempo_atual):
        for link in links:
            mult = 1.45 if link["ok"] else 0.30
            if link["ok"]:
                estado["sobrecarga"] = int(estado.get("sobrecarga", 0)) + 1
            else:
                estado["sobrecarga"] = max(0, int(estado.get("sobrecarga", 0)) - 1)
            for no in (link["a"], link["b"]):
                if no["tipo"] == "inimigo" and _dano_com_janela(onda, no["obj"], f"cond_{link['par']}", tempo_atual, onda["dano_base"] * mult, 380, 280 if link["ok"] else 0):
                    mortos.append(no["obj"])
            if _boss_ativo(boss_info) and (link["a"]["tipo"] == "boss" or link["b"]["tipo"] == "boss"):
                _aplicar_boss(onda, boss_info, tempo_atual, onda["dano_base"] * (0.82 if link["ok"] else 0.18), 620)

    if progresso >= 0.88 and not estado.get("detonou"):
        estado["detonou"] = True
        carga = max(1, int(estado.get("sobrecarga", 0)))
        for link in links:
            if not link["ok"]:
                continue
            pygame.draw.line(tela, (255, 255, 255), link["a"]["ponto"], link["b"]["ponto"], 8)
            for no in (link["a"], link["b"]):
                if no["tipo"] == "inimigo" and _dano_com_janela(onda, no["obj"], f"cond_final_{link['par']}", tempo_atual, onda["dano_base"] * (1.8 + carga * 0.20), 1, 420):
                    mortos.append(no["obj"])
        if _boss_ativo(boss_info) and any(l["ok"] and (l["a"]["tipo"] == "boss" or l["b"]["tipo"] == "boss") for l in links):
            _aplicar_boss(onda, boss_info, tempo_atual, onda["dano_base"] * (1.0 + carga * 0.08), 450)
    return mortos


def _tick_gravitante(onda, inimigos, boss_info, tela, tempo_atual, progresso, disparos):
    estado = onda["estado"]
    mortos = []
    cx, cy = estado["x"], estado["y"]
    raio = 330 * (1.0 - progresso * 0.22)
    pygame.draw.circle(tela, (10, 4, 24), (int(cx), int(cy)), int(42 + 38 * progresso))
    for i in range(9):
        r = int(62 + i * 31 - progresso * 34)
        if r > 14:
            pygame.draw.circle(tela, onda["cor2"], (int(cx), int(cy)), r, 1)
    pygame.draw.circle(tela, onda["cor"], (int(cx), int(cy)), int(raio), 2)

    for disparo in list(disparos or []):
        if not isinstance(disparo, dict) or "gravitante" not in str(disparo.get("tipo_manifestacao", "")):
            continue
        rect = disparo.get("rect")
        if rect is None:
            continue
        if _dist(rect.center, (cx, cy)) <= raio + 120:
            estado.setdefault("orbes", set()).add(id(disparo))
            dx, dy = cx - rect.centerx, cy - rect.centery
            dist = max(1.0, math.hypot(dx, dy))
            rect.x += int(dx / dist * 11 - dy / dist * 7)
            rect.y += int(dy / dist * 11 + dx / dist * 7)
            disparo["pos_x"], disparo["pos_y"] = float(rect.x), float(rect.y)
            pygame.draw.circle(tela, onda["cor2"], rect.center, 13, 1)

    for alvo in _alvos_vivos(inimigos):
        rect = alvo["rect"]
        dist = max(1.0, _dist(rect.center, (cx, cy)))
        if dist <= raio:
            estado.setdefault("puxados", set()).add(id(alvo))
            dx, dy = cx - rect.centerx, cy - rect.centery
            nx, ny = dx / dist, dy / dist
            tx, ty = -ny, nx
            forca = 0.11 + progresso * 0.06
            rect.x += int(dx * forca + tx * 7)
            rect.y += int(dy * forca + ty * 7)
            alvo["pos_x"], alvo["pos_y"] = float(rect.x), float(rect.y)
            alvo["stun_fim"] = max(int(alvo.get("stun_fim", 0)), int(tempo_atual) + 90)

    if _tick_pronto(onda, tempo_atual):
        colapso = progresso >= 0.86
        bonus = 1.0 + min(1.2, (len(estado.get("puxados", set())) + len(estado.get("orbes", set()))) * 0.06)
        for alvo in _alvos_vivos(inimigos):
            dist = _dist(alvo["rect"].center, (cx, cy))
            if dist <= raio + (92 if colapso else 0):
                mult = (0.88 if not colapso else 3.1) * bonus * max(0.35, 1.0 - dist / max(1.0, raio + 92))
                if _dano_com_janela(onda, alvo, "gravidade", tempo_atual, onda["dano_base"] * mult, 330, 170 if colapso else 80):
                    mortos.append(alvo)
        if _boss_ativo(boss_info) and _dist(boss_info["rect"].center, (cx, cy)) <= raio + 100:
            _aplicar_boss(onda, boss_info, tempo_atual, onda["dano_base"] * (0.50 if not colapso else 1.25) * bonus, 620)
    return mortos


def _tick_ancorada(onda, inimigos, boss_info, tela, tempo_atual, progresso, player_center):
    estado = onda["estado"]
    mortos = []
    cx, cy = estado["x"], estado["y"]
    raio = 220
    dentro = _dist(player_center, (cx, cy)) <= raio
    ultimo = int(estado.get("ultimo_player_ms", tempo_atual))
    estado["ultimo_player_ms"] = int(tempo_atual)
    if dentro:
        estado["carga_ms"] = min(ANCORADA_DURACAO_MS, int(estado.get("carga_ms", 0)) + max(0, int(tempo_atual) - ultimo))
    carga = _clamp(float(estado.get("carga_ms", 0)) / ANCORADA_DURACAO_MS, 0.0, 1.0)

    pygame.draw.circle(tela, (*onda["cor2"],), (int(cx), int(cy)), raio, 2)
    pygame.draw.circle(tela, onda["cor"], (int(cx), int(cy)), int(54 + 42 * carga), 3)
    for i in range(12):
        ang = onda["seed"] * 0.001 + i * math.tau / 12 + tempo_atual * 0.002
        px = cx + math.cos(ang) * raio
        py = cy + math.sin(ang) * raio
        pygame.draw.line(tela, onda["cor2"], (int(cx), int(cy)), (int(px), int(py)), 1)
    if dentro:
        pygame.draw.circle(tela, (255, 245, 185), (int(player_center[0]), int(player_center[1])), 32, 2)

    if int(tempo_atual) - int(estado.get("ultimo_pulso_ms", 0)) >= 620:
        estado["ultimo_pulso_ms"] = int(tempo_atual)
        for alvo in _alvos_vivos(inimigos):
            dist = _dist(alvo["rect"].center, (cx, cy))
            if dist <= raio:
                dx = alvo["rect"].centerx - cx
                dy = alvo["rect"].centery - cy
                comp = max(1.0, math.hypot(dx, dy))
                alvo["rect"].x += int(dx / comp * (5 + carga * 7))
                alvo["rect"].y += int(dy / comp * (5 + carga * 7))
                alvo["pos_x"], alvo["pos_y"] = float(alvo["rect"].x), float(alvo["rect"].y)
                if _dano_com_janela(onda, alvo, "marco_pulso", tempo_atual, onda["dano_base"] * (0.40 + carga * 0.55), 580, 120):
                    mortos.append(alvo)
        if _boss_ativo(boss_info) and _dist(boss_info["rect"].center, (cx, cy)) <= raio:
            _aplicar_boss(onda, boss_info, tempo_atual, onda["dano_base"] * (0.24 + carga * 0.32), 700)

    if progresso >= 0.90 and not estado.get("onda_final"):
        estado["onda_final"] = True
        pygame.draw.circle(tela, (255, 255, 255), (int(cx), int(cy)), int(raio * 1.2), 8)
        for alvo in _alvos_vivos(inimigos):
            if _dist(alvo["rect"].center, (cx, cy)) <= raio * 1.22:
                if _dano_com_janela(onda, alvo, "marco_final", tempo_atual, onda["dano_base"] * (1.8 + carga * 4.2), 1, 260):
                    mortos.append(alvo)
        if _boss_ativo(boss_info) and _dist(boss_info["rect"].center, (cx, cy)) <= raio * 1.25:
            _aplicar_boss(onda, boss_info, tempo_atual, onda["dano_base"] * (0.75 + carga * 1.4), 450)
    return mortos
