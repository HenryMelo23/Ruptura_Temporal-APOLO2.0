import math
import random

import pygame


VORAZ_FOME_BASE = 100.0
VORAZ_FOME_ESCALA = 54.0
VORAZ_FOME_ESCALA_QUADRATICA = 9.0
VORAZ_FRAGMENTO_VALOR = 28.0
VORAZ_FRAGMENTO_DURACAO_MS = 6800
VORAZ_FRAGMENTO_COLETA_RAIO = 68
VORAZ_DECAIMENTO_BASE_POR_S = 5.4
VORAZ_DECAIMENTO_ESCALA_POR_S = 1.65
VORAZ_DECAIMENTO_ALTA_FOME_MULT = 4.2
VORAZ_SEM_COLETA_DANO_MS = 30000
VORAZ_DANO_FOME_MS = 1500
VORAZ_SPAWN_BOSS_MS = 7000
VORAZ_MORDIDA_COOLDOWN_MS = 850
VORAZ_MORDIDA_INTENSIDADE_MIN = 0.18
VORAZ_MORDIDA_COLETA_RECENTE_MS = 16000
VORAZ_POEIRA_CURA_VIDA_PERDIDA = 0.05
VORAZ_MORDIDA_DANO_BASE_MULT = 1.50
VORAZ_MORDIDA_DANO_FOME_MULT = 0.75
VORAZ_MORDIDA_DANO_CICLO_MULT = 0.14
VORAZ_MORDIDA_BOSS_BASE_MULT = 1.70
VORAZ_MORDIDA_BOSS_FOME_MULT = 0.95
VORAZ_MORDIDA_BOSS_VIDA_MAX_MULT = 0.003
VORAZ_POEIRAS_POR_ABATE = 9


def _eh_voraz(aurea):
    return str(aurea).strip().lower() == "voraz"


def criar_estado_voraz(nivel=0, agora_ms=0):
    agora = int(agora_ms or 0)
    return {
        "nivel": max(0, int(nivel or 0)),
        "fome": 0.0,
        "ciclos": 0,
        "fragmentos": [],
        "poeiras": [],
        "mordidas": [],
        "ultimo_update_ms": agora,
        "ultima_coleta_ms": agora,
        "ultimo_dano_fome_ms": agora,
        "ultimo_spawn_boss_ms": agora,
    }


def fome_maxima(estado):
    ciclos = max(0, int(estado.get("ciclos", 0))) if estado else 0
    return VORAZ_FOME_BASE + ciclos * VORAZ_FOME_ESCALA + (ciclos * ciclos) * VORAZ_FOME_ESCALA_QUADRATICA


def _intensidade(estado):
    if not estado:
        return 0.0
    maximo = max(1.0, fome_maxima(estado))
    base = max(0.0, min(1.0, float(estado.get("fome", 0.0)) / maximo))
    ciclos = max(0, int(estado.get("ciclos", 0)))
    return min(1.85, base + ciclos * 0.12)


def _mordida_ativa(estado, tempo_atual):
    if not estado:
        return False
    if _intensidade(estado) >= VORAZ_MORDIDA_INTENSIDADE_MIN:
        return True
    if float(estado.get("fome", 0.0)) <= 0 and int(estado.get("ciclos", 0)) <= 0:
        return False
    return int(tempo_atual) - int(estado.get("ultima_coleta_ms", tempo_atual)) <= VORAZ_MORDIDA_COLETA_RECENTE_MS


def bonus_cooldown(estado, aurea):
    if not _eh_voraz(aurea):
        return 1.0
    nivel = int(estado.get("nivel", 0)) if estado else 0
    return max(0.74, 1.0 - _intensidade(estado) * (0.10 + nivel * 0.008))


def dimensoes_disparo(estado, aurea, largura, altura):
    if not _eh_voraz(aurea):
        return largura, altura
    escala = 1.0 + _intensidade(estado) * 0.28
    return max(1, int(largura * escala)), max(1, int(altura * escala))


def marcar_disparo_voraz(estado, aurea, disparo):
    if not _eh_voraz(aurea) or not isinstance(disparo, dict):
        return disparo
    nivel = int(estado.get("nivel", 0)) if estado else 0
    disparo["voraz_aurea"] = True
    disparo["voraz_dano_mult"] = 1.0 + _intensidade(estado) * (0.18 + nivel * 0.012)
    return disparo


def dano_mult_disparo(disparo):
    if not isinstance(disparo, dict):
        return 1.0
    return float(disparo.get("voraz_dano_mult", 1.0))


def _valor_fome_coletavel(estado, valor_base):
    ciclos = max(0, int(estado.get("ciclos", 0))) if estado else 0
    return max(10.0, float(valor_base) * (0.94 ** ciclos))


def _criar_poeira_abate(estado, x, y, tempo_atual):
    poeiras = estado.setdefault("poeiras", [])
    for _ in range(VORAZ_POEIRAS_POR_ABATE):
        ang = random.uniform(0, math.tau)
        vel = random.uniform(0.45, 1.8)
        poeiras.append({
            "x": float(x) + random.uniform(-8, 8),
            "y": float(y) + random.uniform(-8, 8),
            "vx": math.cos(ang) * vel,
            "vy": math.sin(ang) * vel - random.uniform(0.35, 1.15),
            "criado_ms": int(tempo_atual),
            "expira_ms": int(tempo_atual) + random.randint(560, 980),
            "fase": random.uniform(0, math.tau),
            "raio": random.uniform(1.6, 4.4),
        })


def criar_fragmento_abate(estado, aurea, posicao, tempo_atual, quantidade=1):
    if not _eh_voraz(aurea) or not estado:
        return
    x, y = posicao
    fragmentos = estado.setdefault("fragmentos", [])
    _criar_poeira_abate(estado, x, y, tempo_atual)
    for _ in range(max(1, int(quantidade))):
        ang = random.uniform(0, math.tau)
        dist = random.uniform(8, 30)
        fragmentos.append({
            "x": float(x) + math.cos(ang) * dist,
            "y": float(y) + math.sin(ang) * dist,
            "criado_ms": int(tempo_atual),
            "expira_ms": int(tempo_atual + VORAZ_FRAGMENTO_DURACAO_MS),
            "fase": random.uniform(0, math.tau),
            "valor": VORAZ_FRAGMENTO_VALOR,
            "nascendo_ms": int(tempo_atual),
        })


def _criar_fragmento_boss(estado, boss_rect, tempo_atual):
    if not boss_rect:
        return
    margem = 90
    x = random.uniform(boss_rect.left - margem, boss_rect.right + margem)
    y = random.uniform(boss_rect.top - margem, boss_rect.bottom + margem)
    criar_fragmento_abate(estado, "Voraz", (x, y), tempo_atual, 1)


def _coletar_fragmento(estado, frag, tempo_atual, vida=None, vida_maxima=None, efeitos_texto=None):
    estado["fome"] = float(estado.get("fome", 0.0)) + _valor_fome_coletavel(estado, frag.get("valor", VORAZ_FRAGMENTO_VALOR))
    estado["ultima_coleta_ms"] = int(tempo_atual)
    estado["ultimo_dano_fome_ms"] = int(tempo_atual)

    while estado["fome"] >= fome_maxima(estado):
        estado["fome"] -= fome_maxima(estado)
        estado["ciclos"] = int(estado.get("ciclos", 0)) + 1

    cura = 0
    if vida is not None and vida_maxima is not None:
        vida, cura = _curar_vida_perdida(vida, vida_maxima, VORAZ_POEIRA_CURA_VIDA_PERDIDA)
        _registrar_cura_voraz(efeitos_texto, frag.get("x", 0), frag.get("y", 0) - 18, cura)
    return vida, cura


def _adicionar_fome_mordida(estado, tempo_atual):
    fome_ganha = _valor_fome_coletavel(estado, VORAZ_FRAGMENTO_VALOR * 0.48)
    estado["fome"] = float(estado.get("fome", 0.0)) + fome_ganha
    estado["ultima_coleta_ms"] = int(tempo_atual)
    estado["ultimo_dano_fome_ms"] = int(tempo_atual)

    while estado["fome"] >= fome_maxima(estado):
        estado["fome"] -= fome_maxima(estado)
        estado["ciclos"] = int(estado.get("ciclos", 0)) + 1


def _multiplicador_dano_mordida(estado, intensidade, boss=False):
    nivel = int(estado.get("nivel", 0)) if estado else 0
    ciclos = max(0, int(estado.get("ciclos", 0))) if estado else 0
    if boss:
        base = VORAZ_MORDIDA_BOSS_BASE_MULT
        escala_fome = VORAZ_MORDIDA_BOSS_FOME_MULT
    else:
        base = VORAZ_MORDIDA_DANO_BASE_MULT
        escala_fome = VORAZ_MORDIDA_DANO_FOME_MULT
    return base + intensidade * escala_fome + ciclos * VORAZ_MORDIDA_DANO_CICLO_MULT + nivel * 0.035


def atualizar_voraz(
    estado, aurea, tempo_atual, pos_x, pos_y, largura, altura,
    boss_rect=None, vida=None, vida_maxima=None, efeitos_texto=None
):
    if not _eh_voraz(aurea) or not estado:
        return vida, False

    tempo_atual = int(tempo_atual)
    ultimo_update = int(estado.get("ultimo_update_ms", tempo_atual))
    dt_s = max(0.0, min(0.08, (tempo_atual - ultimo_update) / 1000.0))
    estado["ultimo_update_ms"] = tempo_atual

    ciclos = int(estado.get("ciclos", 0))
    maximo_atual = max(1.0, fome_maxima(estado))
    pct_fome = max(0.0, min(1.0, float(estado.get("fome", 0.0)) / maximo_atual))
    pressao_alta = pct_fome * pct_fome * VORAZ_DECAIMENTO_ALTA_FOME_MULT
    decaimento = (
        VORAZ_DECAIMENTO_BASE_POR_S
        + ciclos * VORAZ_DECAIMENTO_ESCALA_POR_S
        + pressao_alta
    ) * dt_s
    
    nova_fome = float(estado.get("fome", 0.0)) - decaimento
    while nova_fome < 0.0 and ciclos > 0:
        ciclos -= 1
        estado["ciclos"] = ciclos
        nova_fome += fome_maxima(estado)
        
    if nova_fome < 0.0:
        nova_fome = 0.0
    estado["fome"] = nova_fome

    if boss_rect and tempo_atual - int(estado.get("ultimo_spawn_boss_ms", 0)) >= VORAZ_SPAWN_BOSS_MS:
        estado["ultimo_spawn_boss_ms"] = tempo_atual
        _criar_fragmento_boss(estado, boss_rect, tempo_atual)

    centro_x = pos_x + largura / 2
    centro_y = pos_y + altura / 2
    vivos = []
    curou = False
    for frag in estado.get("fragmentos", []):
        if tempo_atual >= frag.get("expira_ms", 0):
            continue
        oscilacao = math.sin(tempo_atual * 0.006 + frag.get("fase", 0.0)) * 3
        dx = (frag["x"] - centro_x)
        dy = (frag["y"] + oscilacao - centro_y)
        if math.hypot(dx, dy) <= VORAZ_FRAGMENTO_COLETA_RAIO:
            vida, cura = _coletar_fragmento(estado, frag, tempo_atual, vida, vida_maxima, efeitos_texto)
            curou = curou or cura > 0
            continue
        vivos.append(frag)
    estado["fragmentos"] = vivos
    return vida, curou


def aplicar_custo_fome(estado, aurea, tempo_atual, vida, vida_maxima):
    if not _eh_voraz(aurea) or not estado:
        return vida, False
    sem_coleta_ms = int(tempo_atual) - int(estado.get("ultima_coleta_ms", tempo_atual))
    if sem_coleta_ms < VORAZ_SEM_COLETA_DANO_MS:
        return vida, False
    if int(tempo_atual) - int(estado.get("ultimo_dano_fome_ms", 0)) < VORAZ_DANO_FOME_MS:
        return vida, False

    estado["ultimo_dano_fome_ms"] = int(tempo_atual)
    dano = max(1, int(max(1, vida_maxima) * 0.01))
    return max(1, vida - dano), True


def _curar_vida_perdida(vida, vida_maxima, percentual):
    vida_maxima = max(1, vida_maxima)
    vida = max(0, vida)
    cura = int((vida_maxima - vida) * percentual)
    if cura <= 0:
        return vida, 0
    return min(vida_maxima, vida + cura), cura


def _registrar_cura_voraz(efeitos_texto, x, y, cura):
    if efeitos_texto is None or cura <= 0:
        return
    efeitos_texto.append({
        "texto": f"+{int(cura)}",
        "x": int(x),
        "y": int(y),
        "tempo_inicio": pygame.time.get_ticks(),
        "cor": (255, 176, 72),
    })


def aplicar_passiva_em_inimigos(
    estado, aurea, tempo_atual, pos_x, pos_y, largura, altura,
    inimigos, efeitos_texto, dano_base, fator_tempo=1.0, vida=None, vida_maxima=None
):
    if not _eh_voraz(aurea) or not estado or not inimigos:
        return vida, False, []

    if not _mordida_ativa(estado, tempo_atual):
        return vida, False, []
    intensidade = max(VORAZ_MORDIDA_INTENSIDADE_MIN, _intensidade(estado))

    centro_x = pos_x + largura / 2
    centro_y = pos_y + altura / 2
    raio_puxao = 155 + intensidade * 65
    rect_player = pygame.Rect(pos_x, pos_y, largura, altura).inflate(
        -int(largura * 0.25),
        -int(altura * 0.18),
    )
    curou = False
    mortos = []

    for inimigo in list(inimigos):
        rect = inimigo.get("rect")
        if not rect:
            continue

        dx = centro_x - rect.centerx
        dy = centro_y - rect.centery
        dist = max(1.0, math.hypot(dx, dy))
        if dist <= raio_puxao:
            if "pos_x" not in inimigo:
                inimigo["pos_x"] = float(rect.x)
            if "pos_y" not in inimigo:
                inimigo["pos_y"] = float(rect.y)
            forca = (0.10 + intensidade * 0.10) * float(fator_tempo or 1.0)
            inimigo["pos_x"] += (dx / dist) * forca
            inimigo["pos_y"] += (dy / dist) * forca
            rect.x = int(inimigo["pos_x"])
            rect.y = int(inimigo["pos_y"])

        if rect.colliderect(rect_player):
            ultimo = int(inimigo.get("voraz_ultima_mordida_ms", 0))
            if int(tempo_atual) - ultimo >= VORAZ_MORDIDA_COOLDOWN_MS:
                inimigo["voraz_ultima_mordida_ms"] = int(tempo_atual)
                dano = max(1, int(dano_base * _multiplicador_dano_mordida(estado, intensidade)))
                vida_anterior = inimigo.get("vida", 1)
                inimigo["vida"] = vida_anterior - dano
                eliminou = vida_anterior > 0 and inimigo["vida"] <= 0
                estado.setdefault("mordidas", []).append({
                    "x": rect.centerx,
                    "y": rect.top + rect.height * 0.35,
                    "inicio_ms": int(tempo_atual),
                    "dano": dano,
                })
                _adicionar_fome_mordida(estado, tempo_atual)
                if vida is not None and vida_maxima is not None:
                    percentual_cura = 0.35 if eliminou else 0.25
                    vida, cura = _curar_vida_perdida(vida, vida_maxima, percentual_cura)
                    if cura:
                        curou = True
                        _registrar_cura_voraz(efeitos_texto, rect.centerx, rect.top - 28, cura)
                if efeitos_texto is not None:
                    efeitos_texto.append({
                        "texto": "MORDIDA",
                        "x": rect.centerx,
                        "y": rect.top - 8,
                        "tempo_inicio": int(tempo_atual),
                        "cor": (255, 128, 32),
                    })
                if eliminou:
                    mortos.append(inimigo)

    return vida, curou, mortos


def aplicar_mordida_boss(
    estado, aurea, tempo_atual, pos_x, pos_y, largura, altura,
    boss_rect, vida_boss, vida, vida_maxima, dano_base, efeitos_texto=None
):
    if not _eh_voraz(aurea) or not estado or not boss_rect or vida_boss <= 0:
        return vida_boss, vida, False

    if not _mordida_ativa(estado, tempo_atual):
        return vida_boss, vida, False
    intensidade = max(VORAZ_MORDIDA_INTENSIDADE_MIN, _intensidade(estado))

    rect_player = pygame.Rect(pos_x, pos_y, largura, altura).inflate(
        -int(largura * 0.25),
        -int(altura * 0.18),
    )
    if not boss_rect.colliderect(rect_player):
        return vida_boss, vida, False

    ultimo = int(estado.get("ultima_mordida_boss_ms", 0))
    if int(tempo_atual) - ultimo < VORAZ_MORDIDA_COOLDOWN_MS:
        return vida_boss, vida, False

    estado["ultima_mordida_boss_ms"] = int(tempo_atual)
    dano_por_base = dano_base * _multiplicador_dano_mordida(estado, intensidade, boss=True)
    dano_por_vida = vida_boss * VORAZ_MORDIDA_BOSS_VIDA_MAX_MULT * (1.0 + intensidade * 0.55)
    dano = max(1, int(max(dano_por_base, dano_por_vida)))
    vida_boss = max(0, vida_boss - dano)
    vida, cura = _curar_vida_perdida(vida, vida_maxima, 0.60)
    x = boss_rect.centerx
    y = boss_rect.top + boss_rect.height * 0.35
    estado.setdefault("mordidas", []).append({
        "x": x,
        "y": y,
        "inicio_ms": int(tempo_atual),
        "dano": dano,
    })
    _adicionar_fome_mordida(estado, tempo_atual)
    if efeitos_texto is not None:
        efeitos_texto.append({
            "texto": "MORDIDA",
            "x": x,
            "y": boss_rect.top - 8,
            "tempo_inicio": int(tempo_atual),
            "cor": (255, 128, 32),
        })
        efeitos_texto.append({
            "texto": f"-{int(dano)}",
            "x": x + 18,
            "y": boss_rect.top - 30,
            "tempo_inicio": int(tempo_atual),
            "cor": (255, 204, 96),
        })
        _registrar_cura_voraz(efeitos_texto, x, boss_rect.top - 28, cura)
    return vida_boss, vida, cura > 0


def desenhar_voraz(tela, estado, aurea, tempo_atual, largura_tela=None, config_graficos=None):
    if not _eh_voraz(aurea) or not estado:
        return
    largura_tela = largura_tela or tela.get_width()

    efeitos = True
    if config_graficos is not None:
        efeitos = config_graficos.get("efeitos_visuais", True)

    if efeitos:
        poeiras_vivas = []
        for poeira in estado.get("poeiras", []):
            inicio = int(poeira.get("criado_ms", tempo_atual))
            fim = int(poeira.get("expira_ms", inicio + 1))
            if tempo_atual >= fim:
                continue
            idade = max(0, tempo_atual - inicio)
            duracao = max(1, fim - inicio)
            p = idade / duracao
            poeira["x"] += float(poeira.get("vx", 0.0))
            poeira["y"] += float(poeira.get("vy", 0.0))
            poeira["vy"] = float(poeira.get("vy", 0.0)) + 0.045
            alpha = int(210 * (1.0 - p))
            raio = max(1, int(float(poeira.get("raio", 2.0)) * (1.0 - p * 0.45)))
            x = int(poeira["x"] + math.sin(tempo_atual * 0.012 + poeira.get("fase", 0.0)) * 2)
            y = int(poeira["y"])
            brilho = pygame.Surface((34, 34), pygame.SRCALPHA)
            pygame.draw.circle(brilho, (255, 78, 18, int(alpha * 0.18)), (17, 17), raio + 9)
            pygame.draw.circle(brilho, (255, 138, 32, alpha), (17, 17), raio + 2)
            pygame.draw.circle(brilho, (255, 224, 120, min(220, alpha + 25)), (17, 17), max(1, raio // 2))
            tela.blit(brilho, (x - 17, y - 17), special_flags=pygame.BLEND_RGBA_ADD)
            poeiras_vivas.append(poeira)
        estado["poeiras"] = poeiras_vivas

        vivos = []
        for frag in estado.get("fragmentos", []):
            restante = max(0.0, min(1.0, (frag.get("expira_ms", tempo_atual) - tempo_atual) / VORAZ_FRAGMENTO_DURACAO_MS))
            if restante <= 0:
                continue
            pulso = (math.sin(tempo_atual * 0.010 + frag.get("fase", 0.0)) + 1.0) * 0.5
            nascimento = max(0, tempo_atual - int(frag.get("nascendo_ms", tempo_atual)))
            pop = max(0.0, 1.0 - nascimento / 420.0)
            x = int(frag["x"] + math.sin(tempo_atual * 0.004 + frag.get("fase", 0.0)) * 4)
            y = int(frag["y"] - (1.0 - restante) * 18 + pulso * 4)
            alpha = int(70 + 155 * restante)
            raio = int(4 + pulso * 4 + pop * 5)
            brilho = pygame.Surface((42, 42), pygame.SRCALPHA)
            pygame.draw.circle(brilho, (255, 82, 18, int(alpha * 0.24)), (21, 21), 19)
            pygame.draw.circle(brilho, (255, 138, 34, int(alpha * 0.65)), (21, 21), max(6, raio + 5), 1)
            pygame.draw.circle(brilho, (255, 190, 72, alpha), (21, 21), raio)
            pygame.draw.circle(brilho, (255, 238, 150, min(255, alpha + 35)), (21, 21), max(2, raio // 2))
            for i in range(3):
                ang = frag.get("fase", 0.0) + tempo_atual * 0.006 + i * math.tau / 3
                px = 21 + math.cos(ang) * (raio + 7)
                py = 21 + math.sin(ang) * (raio + 7)
                pygame.draw.circle(brilho, (255, 104, 20, int(alpha * 0.6)), (int(px), int(py)), 2)
            tela.blit(brilho, (x - 21, y - 21), special_flags=pygame.BLEND_RGBA_ADD)
            vivos.append(frag)
        estado["fragmentos"] = vivos

        mordidas_vivas = []
        for mordida in estado.get("mordidas", []):
            idade = tempo_atual - mordida.get("inicio_ms", tempo_atual)
            if idade >= 360:
                continue
            p = idade / 360.0
            abertura = math.sin(p * math.pi)
            alpha = int(220 * (1.0 - p))
            x = int(mordida["x"])
            y = int(mordida["y"])
            mandibula = pygame.Surface((58, 46), pygame.SRCALPHA)
            cor = (255, 118, 26, alpha)
            pygame.draw.arc(mandibula, cor, (8, 2 + int(8 * abertura), 42, 24), math.pi * 1.05, math.pi * 1.95, 3)
            pygame.draw.arc(mandibula, cor, (8, 18 - int(8 * abertura), 42, 24), math.pi * 0.05, math.pi * 0.95, 3)
            for i in range(4):
                tx = 14 + i * 8
                pygame.draw.line(mandibula, (255, 225, 160, alpha), (tx, 15), (tx + 3, 23), 1)
                pygame.draw.line(mandibula, (255, 225, 160, alpha), (tx, 31), (tx + 3, 23), 1)
            tela.blit(mandibula, (x - 29, y - 23), special_flags=pygame.BLEND_RGBA_ADD)
            mordidas_vivas.append(mordida)
        estado["mordidas"] = mordidas_vivas

    barra_w = 200
    barra_h = 14
    x = int((largura_tela - barra_w) / 2)
    y = 18
    maximo = max(1.0, fome_maxima(estado))
    pct = max(0.0, min(1.0, float(estado.get("fome", 0.0)) / maximo))
    ciclos = int(estado.get("ciclos", 0))
    pulso = (math.sin(tempo_atual * 0.008) + 1.0) * 0.5

    painel = pygame.Surface((barra_w + 10, 38), pygame.SRCALPHA)
    pygame.draw.rect(painel, (18, 8, 6, 150), (0, 0, barra_w + 10, 38), border_radius=5)
    pygame.draw.rect(painel, (105, 42, 18, 210), (5, 18, barra_w, barra_h), 1, border_radius=4)
    preenchido = int(barra_w * pct)
    if preenchido > 0:
        cor = (255, int(118 + pulso * 52), 28, 230)
        pygame.draw.rect(painel, cor, (5, 18, preenchido, barra_h), border_radius=4)
        pygame.draw.rect(painel, (255, 214, 92, 90), (5, 18, preenchido, max(2, barra_h // 3)), border_radius=4)
    fonte = pygame.font.Font(None, 18)
    texto = fonte.render(f"FOME X{ciclos}", True, (255, 212, 130))
    painel.blit(texto, (5, 3))
    tela.blit(painel, (x - 5, y))
