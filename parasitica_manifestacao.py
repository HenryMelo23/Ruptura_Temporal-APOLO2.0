# -*- coding: utf-8 -*-
import math
import random

import pygame

import retornante_manifestacao


COR_PARASITA = (105, 255, 130)
COR_PARASITA_ESCURA = (30, 95, 55)
COR_PARASITA_MADURA = (215, 255, 95)

SEMENTE_DANO_INICIAL_MULT = 0.38
SEMENTE_REFORCO_ACERTO = 20.0
SEMENTE_INICIAL = 24.0
SEMENTE_MADURA = 165.0
SEMENTE_RAIO_PROXIMIDADE = 135
SEMENTE_RAIO_EXPLOSAO = 118
SEMENTE_DANO_IMATURA_MULT = 0.72
SEMENTE_DANO_MADURA_MULT = 2.45
SEMENTE_ESPALHADA_VALOR = 42.0
SEMENTE_DURACAO_MS = 16000
SEMENTE_TICK_MS = 760
ECLOSAO_DURACAO_MS = 430
ECLOSAO_COOLDOWN_MULT = 1.85
PARTICULAS_PARASITICAS_MAX = 320

_PARTICULAS_PARASITICAS = []
_RUPTURAS_PARASITICAS = []


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


def _parametros_perfil(perfil):
    if perfil == "alto":
        return {"vinhas": 14, "esporos": 24, "aneis": 4, "largura": 2, "particulas": 260}
    if perfil == "medio":
        return {"vinhas": 8, "esporos": 11, "aneis": 2, "largura": 2, "particulas": 130}
    if perfil == "baixo":
        return {"vinhas": 4, "esporos": 3, "aneis": 1, "largura": 1, "particulas": 48}
    return {"vinhas": 0, "esporos": 0, "aneis": 0, "largura": 1, "particulas": 0}


def _limitar_particulas(maximo=PARTICULAS_PARASITICAS_MAX):
    excesso = len(_PARTICULAS_PARASITICAS) - int(maximo)
    if excesso > 0:
        del _PARTICULAS_PARASITICAS[:excesso]


def _spawn_explosao_parasitica(rect, tempo_atual, madura, valor=1.0):
    if rect is None:
        return
    intensidade = max(0.35, min(1.0, float(valor) / max(1.0, SEMENTE_MADURA)))
    quantidade = int((46 if madura else 20) * (0.65 + intensidade * 0.45))
    rng = random.Random(int(tempo_atual) + rect.centerx * 31 + rect.centery * 17 + (97 if madura else 11))
    origem_x = rect.centerx
    origem_y = rect.centery
    _RUPTURAS_PARASITICAS.append({
        "x": origem_x,
        "y": origem_y,
        "nasc_ms": int(tempo_atual),
        "vida_ms": 520 if madura else 340,
        "raio": max(rect.width, rect.height) * (1.55 if madura else 1.05),
        "madura": bool(madura),
        "fase": rng.uniform(0, math.tau),
        "espinhos": 18 if madura else 10,
    })
    for indice in range(max(8, quantidade)):
        tipo = rng.choices(("parasita", "gota", "casca"), weights=(6, 4, 3), k=1)[0]
        angulo = rng.uniform(-math.pi * 0.95, math.pi * 1.95)
        distancia_origem = rng.uniform(0, max(6, min(rect.width, rect.height) * 0.35))
        velocidade = rng.uniform(70, 230 if madura else 160)
        vx = math.cos(angulo) * velocidade * rng.uniform(0.55, 1.08)
        vy = math.sin(angulo) * velocidade * rng.uniform(0.45, 0.95) - rng.uniform(50, 170 if madura else 110)
        tamanho_base = rng.uniform(2.0, 5.8 if madura else 4.2)
        vida = rng.randint(900, 1850 if madura else 1350)
        _PARTICULAS_PARASITICAS.append({
            "tipo": tipo,
            "nasc_ms": int(tempo_atual),
            "vida_ms": vida,
            "x": origem_x + math.cos(angulo) * distancia_origem,
            "y": origem_y + math.sin(angulo) * distancia_origem,
            "vx": vx,
            "vy": vy,
            "grav": rng.uniform(360, 620),
            "solo_y": rect.bottom + rng.uniform(-3, max(8, rect.height * 0.32)),
            "tam": tamanho_base,
            "rot": rng.uniform(0, math.tau),
            "fase": rng.uniform(0, math.tau),
            "madura": bool(madura),
            "indice": indice,
            "cor": rng.choice((COR_PARASITA, COR_PARASITA_MADURA, (145, 245, 120), (70, 170, 85))),
        })
    _limitar_particulas()


def _desenhar_rupturas_parasiticas(tela, tempo_atual, perfil):
    if not _RUPTURAS_PARASITICAS:
        return
    escala = 1.0 if perfil == "alto" else 0.72 if perfil == "medio" else 0.48
    sobreviventes = []
    for ruptura in _RUPTURAS_PARASITICAS:
        idade = int(tempo_atual) - int(ruptura.get("nasc_ms", tempo_atual))
        vida = max(1, int(ruptura.get("vida_ms", 400)))
        if idade < 0:
            idade = 0
        if idade >= vida:
            continue
        t = idade / float(vida)
        alpha = int((230 if ruptura.get("madura") else 170) * (1.0 - t) ** 0.9)
        raio = int((10 + float(ruptura.get("raio", 40)) * (0.45 + t * 0.9)) * escala)
        tamanho = max(32, raio * 2 + 40)
        surf = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
        centro = tamanho // 2
        cor = COR_PARASITA_MADURA if ruptura.get("madura") else COR_PARASITA

        pygame.draw.circle(surf, (*COR_PARASITA_ESCURA, max(20, alpha // 2)), (centro, centro), max(5, raio), 3)
        pygame.draw.circle(surf, (*cor, max(25, alpha)), (centro, centro), max(4, int(raio * 0.42)), 2)
        if perfil in ("alto", "medio"):
            espinhos = int(ruptura.get("espinhos", 10) * (1.0 if perfil == "alto" else 0.65))
            for i in range(max(5, espinhos)):
                ang = float(ruptura.get("fase", 0.0)) + i * math.tau / max(1, espinhos) + t * 0.9
                interno = int(raio * (0.24 + 0.18 * math.sin(i + t * 7.0)))
                externo = int(raio * (0.92 + 0.28 * math.sin(i * 1.7 + t * 11.0)))
                p1 = (centro + int(math.cos(ang) * interno), centro + int(math.sin(ang) * interno))
                p2 = (centro + int(math.cos(ang) * externo), centro + int(math.sin(ang) * externo))
                pygame.draw.line(surf, (*COR_PARASITA_ESCURA, max(35, alpha)), p1, p2, 3 if perfil == "alto" else 2)
                pygame.draw.line(surf, (*cor, max(20, alpha - 45)), p1, p2, 1)
        if perfil == "alto":
            for i in range(8):
                ang = float(ruptura.get("fase", 0.0)) + i * math.tau / 8.0 - t * 1.2
                px = centro + int(math.cos(ang) * raio * 0.58)
                py = centro + int(math.sin(ang) * raio * 0.42)
                pygame.draw.circle(surf, (*COR_PARASITA_MADURA, max(25, alpha // 2)), (px, py), max(2, int(3 + 4 * (1.0 - t))))

        tela.blit(surf, (int(ruptura.get("x", 0)) - centro, int(ruptura.get("y", 0)) - centro))
        sobreviventes.append(ruptura)
    _RUPTURAS_PARASITICAS[:] = sobreviventes


def _desenhar_particula_parasitica(tela, p, x, y, alpha, escala, no_chao, perfil):
    tamanho = max(1, int(float(p.get("tam", 3.0)) * escala))
    raio = max(8, tamanho * 4 + 8)
    surf = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
    centro = raio
    cor = p.get("cor", COR_PARASITA)
    escura = COR_PARASITA_ESCURA
    tipo = p.get("tipo", "parasita")

    if no_chao:
        pygame.draw.ellipse(surf, (5, 18, 12, max(20, alpha // 4)), (centro - tamanho * 3, centro + tamanho, tamanho * 6, max(2, tamanho)))

    if tipo == "parasita":
        alongamento = max(3, int(tamanho * (2.3 if no_chao else 2.8)))
        oscilacao = math.sin(float(p.get("fase", 0.0)) + float(p.get("rot", 0.0))) * tamanho
        corpo = pygame.Rect(centro - alongamento // 2, centro - tamanho, alongamento, tamanho * 2)
        corpo.y += int(oscilacao * 0.25)
        pygame.draw.ellipse(surf, (*escura, alpha), corpo.inflate(3, 3))
        pygame.draw.ellipse(surf, (*cor, alpha), corpo)
        pygame.draw.circle(surf, (18, 45, 24, alpha), (corpo.right - max(1, tamanho // 2), corpo.centery), max(1, tamanho // 2))
        if perfil in ("alto", "medio"):
            for lado in (-1, 1):
                for passo in range(2):
                    px = corpo.centerx + lado * (passo + 1) * max(2, tamanho // 2)
                    py = corpo.centery + int(math.sin(float(p.get("fase", 0.0)) + passo) * tamanho)
                    pygame.draw.line(
                        surf,
                        (*COR_PARASITA_MADURA, max(45, alpha // 2)),
                        (px, py),
                        (px + lado * tamanho * 2, py + (passo * 2 - 1) * tamanho),
                        1,
                    )
    elif tipo == "casca":
        pontos = []
        for i in range(3):
            a = float(p.get("rot", 0.0)) + i * math.tau / 3.0
            pontos.append((centro + int(math.cos(a) * tamanho * 2.2), centro + int(math.sin(a) * tamanho * 1.5)))
        pygame.draw.polygon(surf, (*escura, alpha), pontos)
        pontos_menor = [((px + centro) // 2, (py + centro) // 2) for px, py in pontos]
        pygame.draw.polygon(surf, (*cor, max(50, alpha // 2)), pontos_menor)
    else:
        pygame.draw.circle(surf, (*escura, alpha), (centro, centro), tamanho + 2)
        pygame.draw.circle(surf, (*cor, alpha), (centro, centro), tamanho)
        pygame.draw.circle(surf, (*COR_PARASITA_MADURA, max(40, alpha // 2)), (centro - 1, centro - 1), max(1, tamanho // 2))

    tela.blit(surf, (int(x) - raio, int(y) - raio))


def _atualizar_e_desenhar_particulas_parasiticas(tela, tempo_atual, config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        _PARTICULAS_PARASITICAS.clear()
        _RUPTURAS_PARASITICAS.clear()
        return
    _desenhar_rupturas_parasiticas(tela, tempo_atual, perfil)
    if not _PARTICULAS_PARASITICAS:
        return
    params = _parametros_perfil(perfil)
    limite = params["particulas"]
    _limitar_particulas(limite)
    escala = 1.0 if perfil == "alto" else 0.82 if perfil == "medio" else 0.62
    sobreviventes = []
    for idx, p in enumerate(_PARTICULAS_PARASITICAS):
        if perfil == "baixo" and idx % 2:
            sobreviventes.append(p)
            continue
        idade = int(tempo_atual) - int(p.get("nasc_ms", tempo_atual))
        vida = max(1, int(p.get("vida_ms", 1000)))
        if idade < 0:
            idade = 0
        if idade >= vida:
            continue
        t = idade / 1000.0
        progresso = idade / float(vida)
        x = float(p.get("x", 0.0)) + float(p.get("vx", 0.0)) * t
        y = float(p.get("y", 0.0)) + float(p.get("vy", 0.0)) * t + 0.5 * float(p.get("grav", 450.0)) * t * t
        solo_y = float(p.get("solo_y", y))
        no_chao = y >= solo_y
        if no_chao:
            amortecimento = max(0.0, 1.0 - progresso)
            x += math.sin(t * 18.0 + float(p.get("fase", 0.0))) * 9.0 * amortecimento
            y = solo_y + math.sin(t * 13.0 + float(p.get("rot", 0.0))) * 2.2 * amortecimento
        else:
            x += math.sin(t * 11.0 + float(p.get("fase", 0.0))) * 3.5
        alpha = int((235 if p.get("madura") else 190) * (1.0 - progresso) ** 0.85)
        if alpha > 8:
            _desenhar_particula_parasitica(tela, p, x, y, alpha, escala, no_chao, perfil)
        sobreviventes.append(p)
    _PARTICULAS_PARASITICAS[:] = sobreviventes


def ativa(manifestacao):
    return str(manifestacao or "").strip().lower() == "parasitica"


def multiplicador_cooldown_habilidade(manifestacao):
    return ECLOSAO_COOLDOWN_MULT if ativa(manifestacao) else 1.0


def criar_auto_attack(manifestacao, vfx, centro_x, centro_y, largura, altura, angulo, velocidade, tempo_atual, impulsiva=False):
    if not ativa(manifestacao):
        return retornante_manifestacao.criar_auto_attack(
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

    largura = max(9, int(largura * 0.66))
    altura = max(9, int(altura * 0.66))
    disparo = vfx.criar_disparo(centro_x, centro_y, largura, altura, angulo, velocidade * 0.88, tempo_atual, impulsiva)
    disparo["tipo_manifestacao"] = "parasitica_semente"
    disparo["dano_mult_manifestacao"] = SEMENTE_DANO_INICIAL_MULT
    disparo["raio_vfx"] = max(4, min(9, int(min(largura, altura) * 0.5)))
    return disparo


def multiplicador_dano_disparo(disparo):
    if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "parasitica_semente":
        return float(disparo.get("dano_mult_manifestacao", SEMENTE_DANO_INICIAL_MULT))
    return 1.0


def _rect_de(alvo):
    if isinstance(alvo, dict):
        return alvo.get("rect")
    return alvo


def _id_alvo(alvo):
    if isinstance(alvo, dict):
        return alvo.get("parasitica_id", id(alvo))
    if hasattr(alvo, "left"):
        return (int(alvo.left), int(alvo.top), int(alvo.width), int(alvo.height))
    return id(alvo)


def _texto(efeitos_texto, texto, rect, tempo_atual, cor):
    if efeitos_texto is None or rect is None:
        return
    efeitos_texto.append({
        "texto": texto,
        "x": rect.centerx,
        "y": rect.top - 26,
        "tempo_inicio": int(tempo_atual),
        "cor": cor,
    })


def implantar_semente(alvo, tempo_atual, dano_base=10.0, efeitos_texto=None):
    if not isinstance(alvo, dict):
        return None
    rect = alvo.get("rect")
    semente = alvo.get("semente_parasitica")
    if not semente:
        semente = {
            "valor": SEMENTE_INICIAL,
            "criada_ms": int(tempo_atual),
            "ultimo_tick_ms": int(tempo_atual),
            "ultimo_ataque_ms": 0,
            "madura": False,
            "dano_base": max(1.0, float(dano_base)),
        }
        alvo["semente_parasitica"] = semente
        _texto(efeitos_texto, "semente", rect, tempo_atual, COR_PARASITA)
    else:
        semente["valor"] = min(SEMENTE_MADURA, float(semente.get("valor", 0.0)) + SEMENTE_REFORCO_ACERTO)
        semente["dano_base"] = max(float(semente.get("dano_base", 1.0)), float(dano_base))
        _texto(efeitos_texto, "+parasita", rect, tempo_atual, COR_PARASITA_MADURA)
    if float(semente.get("valor", 0.0)) >= SEMENTE_MADURA:
        semente["madura"] = True
    return semente


def _aplicar_semente_espalhada(alvo, tempo_atual, dano_base):
    if not isinstance(alvo, dict) or alvo.get("vida", 1) <= 0:
        return
    semente = alvo.get("semente_parasitica")
    if semente:
        semente["valor"] = min(SEMENTE_MADURA, float(semente.get("valor", 0.0)) + SEMENTE_ESPALHADA_VALOR * 0.65)
    else:
        alvo["semente_parasitica"] = {
            "valor": SEMENTE_ESPALHADA_VALOR,
            "criada_ms": int(tempo_atual),
            "ultimo_tick_ms": int(tempo_atual),
            "ultimo_ataque_ms": 0,
            "madura": False,
            "dano_base": max(1.0, float(dano_base) * 0.72),
        }


def explodir_semente(alvo, inimigos, tempo_atual, efeitos_texto=None, forcar=False):
    if not isinstance(alvo, dict):
        return []
    semente = alvo.pop("semente_parasitica", None)
    if not semente:
        return []
    rect = alvo.get("rect")
    madura = bool(semente.get("madura")) or float(semente.get("valor", 0.0)) >= SEMENTE_MADURA
    dano_base = float(semente.get("dano_base", 10.0))
    mult = SEMENTE_DANO_MADURA_MULT if madura else SEMENTE_DANO_IMATURA_MULT
    dano = max(1.0, dano_base * mult)
    mortos = []

    if rect is not None:
        _texto(efeitos_texto, "ECLOSE" if madura else "ruptura", rect, tempo_atual, COR_PARASITA_MADURA if madura else COR_PARASITA)
        _spawn_explosao_parasitica(rect, tempo_atual, madura, semente.get("valor", 0.0))

    for outro in list(inimigos or []):
        outro_rect = outro.get("rect") if isinstance(outro, dict) else None
        if outro_rect is None or rect is None:
            continue
        distancia = math.hypot(outro_rect.centerx - rect.centerx, outro_rect.centery - rect.centery)
        if distancia > SEMENTE_RAIO_EXPLOSAO:
            continue
        queda = max(0.38, 1.0 - distancia / max(1.0, SEMENTE_RAIO_EXPLOSAO * 1.35))
        dano_final = dano * queda
        outro["vida"] -= dano_final
        if outro is not alvo and madura:
            _aplicar_semente_espalhada(outro, tempo_atual, dano_base)
        if efeitos_texto is not None and outro_rect is not None:
            _texto(efeitos_texto, f"-{int(dano_final)}", outro_rect, tempo_atual, COR_PARASITA_MADURA if madura else COR_PARASITA)
        if outro.get("vida", 1) <= 0 and outro not in mortos:
            mortos.append(outro)
    return mortos


def eclodir_todas(inimigos, tempo_atual, efeitos_texto=None):
    mortos = []
    total = 0
    for alvo in list(inimigos or []):
        if isinstance(alvo, dict) and alvo.get("semente_parasitica"):
            total += 1
            for morto in explodir_semente(alvo, inimigos, tempo_atual, efeitos_texto, True):
                if morto not in mortos:
                    mortos.append(morto)
    return mortos, total


def criar_eclosao(x, y, tempo_atual, total=0):
    rect = pygame.Rect(int(x - 44), int(y - 44), 88, 88)
    return {
        "tipo_manifestacao": "eclosao_parasitica",
        "rect": rect,
        "tempo_inicio": int(tempo_atual),
        "fim_ms": int(tempo_atual) + ECLOSAO_DURACAO_MS,
        "total": int(total),
    }


def desenhar_eclosao(tela, eclosao, tempo_atual, config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        return
    inicio = int(eclosao.get("tempo_inicio", tempo_atual))
    t = max(0.0, min(1.0, (int(tempo_atual) - inicio) / float(ECLOSAO_DURACAO_MS)))
    raio = int(20 + 90 * t)
    alpha = int(170 * (1.0 - t))
    if perfil == "baixo":
        raio = int(16 + 48 * t)
        alpha = int(alpha * 0.55)
    elif perfil == "medio":
        raio = int(18 + 68 * t)
        alpha = int(alpha * 0.78)
    surf = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
    centro = raio + 4
    pygame.draw.circle(surf, (*COR_PARASITA, max(22, alpha // 3)), (centro, centro), raio, 2)
    pygame.draw.circle(surf, (*COR_PARASITA_MADURA, max(30, alpha)), (centro, centro), max(6, int(raio * 0.28)), 1)
    tela.blit(surf, (eclosao["rect"].centerx - centro, eclosao["rect"].centery - centro))


def atualizar_sementes(inimigos, tempo_atual, dano_base, efeitos_texto=None, jogador_rect=None):
    mortos = []
    for inimigo in list(inimigos or []):
        if not isinstance(inimigo, dict):
            continue
        semente = inimigo.get("semente_parasitica")
        rect = inimigo.get("rect")
        if not semente or rect is None:
            continue
        if int(tempo_atual) - int(semente.get("criada_ms", tempo_atual)) > SEMENTE_DURACAO_MS:
            for morto in explodir_semente(inimigo, inimigos, tempo_atual, efeitos_texto, True):
                if morto not in mortos:
                    mortos.append(morto)
            continue
        if int(tempo_atual) - int(semente.get("ultimo_tick_ms", 0)) < SEMENTE_TICK_MS:
            continue
        semente["ultimo_tick_ms"] = int(tempo_atual)
        crescimento = 0.0
        vizinhos = 0
        for outro in inimigos:
            if outro is inimigo or not isinstance(outro, dict) or not outro.get("rect"):
                continue
            dist = math.hypot(outro["rect"].centerx - rect.centerx, outro["rect"].centery - rect.centery)
            if dist <= SEMENTE_RAIO_PROXIMIDADE:
                vizinhos += 1
        if vizinhos:
            crescimento += min(23.0, 7.0 + vizinhos * 4.5)
        if jogador_rect is not None and rect.colliderect(jogador_rect.inflate(26, 26)):
            crescimento += 11.0
            semente["ultimo_ataque_ms"] = int(tempo_atual)
        if crescimento <= 0.0:
            continue
        semente["valor"] = min(SEMENTE_MADURA, float(semente.get("valor", 0.0)) + crescimento)
        semente["dano_base"] = max(float(semente.get("dano_base", 1.0)), float(dano_base))
        if float(semente.get("valor", 0.0)) >= SEMENTE_MADURA:
            semente["madura"] = True
            for morto in explodir_semente(inimigo, inimigos, tempo_atual, efeitos_texto):
                if morto not in mortos:
                    mortos.append(morto)
    return mortos


def desenhar_sementes(tela, inimigos, tempo_atual, config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        _PARTICULAS_PARASITICAS.clear()
        return
    params = _parametros_perfil(perfil)
    for inimigo in inimigos or []:
        if not isinstance(inimigo, dict):
            continue
        semente = inimigo.get("semente_parasitica")
        rect = inimigo.get("rect")
        if not semente or rect is None:
            continue
        valor = max(0.0, min(1.0, float(semente.get("valor", 0.0)) / SEMENTE_MADURA))
        cx, cy = rect.centerx, rect.top + max(8, int(rect.height * 0.18))
        cor = COR_PARASITA_MADURA if valor >= 1.0 else COR_PARASITA
        idade = max(0, int(tempo_atual) - int(semente.get("criada_ms", tempo_atual)))
        pulso = 0.5 + 0.5 * math.sin(tempo_atual * 0.008 + hash(_id_alvo(inimigo)) % 17)
        margem_x = int(5 + 18 * valor)
        margem_y = int(4 + 16 * valor)
        corpo = rect.inflate(margem_x * 2, margem_y * 2)

        aura = pygame.Surface((corpo.width + 28, corpo.height + 28), pygame.SRCALPHA)
        local = pygame.Rect(14, 14, corpo.width, corpo.height)
        alpha_base = int(36 + 78 * valor)
        for i in range(params["aneis"], 0, -1):
            inflar = int(i * (8 + valor * 8))
            pygame.draw.ellipse(aura, (*COR_PARASITA_ESCURA, max(10, alpha_base // (i + 1))), local.inflate(inflar, inflar), params["largura"])
            pygame.draw.ellipse(aura, (*cor, max(18, alpha_base - i * 18)), local.inflate(inflar // 2, inflar // 2), 1)

        vinhas = params["vinhas"]
        for i in range(vinhas):
            fase = tempo_atual * 0.004 + i * 0.83 + idade * 0.0006
            lado = i % 4
            t = (i + pulso) / max(1, vinhas)
            if lado == 0:
                x1 = local.left + int(local.width * t)
                y1 = local.top
                x2 = x1 + int(math.sin(fase) * (8 + 18 * valor))
                y2 = local.top + int(local.height * (0.25 + 0.55 * valor))
            elif lado == 1:
                x1 = local.right
                y1 = local.top + int(local.height * t)
                x2 = local.right - int(local.width * (0.22 + 0.5 * valor))
                y2 = y1 + int(math.cos(fase) * (7 + 15 * valor))
            elif lado == 2:
                x1 = local.left + int(local.width * (1.0 - t))
                y1 = local.bottom
                x2 = x1 + int(math.cos(fase) * (8 + 18 * valor))
                y2 = local.bottom - int(local.height * (0.25 + 0.55 * valor))
            else:
                x1 = local.left
                y1 = local.top + int(local.height * (1.0 - t))
                x2 = local.left + int(local.width * (0.22 + 0.5 * valor))
                y2 = y1 + int(math.sin(fase) * (7 + 15 * valor))
            meio = ((x1 + x2) // 2 + int(math.sin(fase * 1.7) * 9), (y1 + y2) // 2 + int(math.cos(fase * 1.3) * 9))
            pygame.draw.line(aura, (*COR_PARASITA_ESCURA, 160), (x1, y1), meio, params["largura"] + 1)
            pygame.draw.line(aura, (*cor, 210), meio, (x2, y2), params["largura"])

        if perfil == "alto":
            centro_local = local.center
            for i in range(7):
                fase = tempo_atual * 0.0055 + i * 1.14 + idade * 0.0004
                y = local.top + int(local.height * (0.14 + i * 0.12))
                aperto = int((5 + valor * 11) * math.sin(fase))
                x1 = local.left + int(local.width * 0.08) + aperto
                x2 = local.right - int(local.width * 0.08) - aperto
                meio = ((x1 + x2) // 2, y + int(math.cos(fase * 1.3) * (5 + valor * 7)))
                pygame.draw.line(aura, (*COR_PARASITA_ESCURA, 175), (x1, y), meio, 3)
                pygame.draw.line(aura, (*cor, 210), meio, (x2, y + int(math.sin(fase) * 4)), 2)
            rng_consumo = random.Random(int(semente.get("criada_ms", 0)) + hash(_id_alvo(inimigo)) % 10007)
            feridas = 5 + int(valor * 8)
            for i in range(feridas):
                px = local.left + rng_consumo.randint(max(1, local.width // 8), max(2, local.width - local.width // 8))
                py = local.top + rng_consumo.randint(max(1, local.height // 8), max(2, local.height - local.height // 10))
                brilho = 0.55 + 0.45 * math.sin(tempo_atual * 0.007 + i)
                raio = max(2, int((2 + valor * 5) * brilho))
                pygame.draw.circle(aura, (8, 20, 12, 165), (px, py), raio + 2)
                pygame.draw.circle(aura, (*COR_PARASITA_MADURA, int(85 + 100 * valor)), (px, py), max(1, raio), 1)
                pygame.draw.line(aura, (*COR_PARASITA_ESCURA, 150), (px, py), centro_local, 1)
            if valor > 0.62:
                bulbos = 4 + int(valor * 5)
                for i in range(bulbos):
                    ang = tempo_atual * 0.002 + i * math.tau / max(1, bulbos)
                    bx = local.centerx + int(math.cos(ang) * local.width * (0.42 + 0.08 * pulso))
                    by = local.centery + int(math.sin(ang * 1.21) * local.height * (0.42 + 0.06 * pulso))
                    raio_bulbo = int(3 + valor * 8 + pulso * 2)
                    pygame.draw.circle(aura, (*COR_PARASITA_ESCURA, 190), (bx, by), raio_bulbo + 2)
                    pygame.draw.circle(aura, (*COR_PARASITA_MADURA, 215), (bx, by), raio_bulbo)
                    pygame.draw.circle(aura, (240, 255, 180, 170), (bx - 1, by - 1), max(1, raio_bulbo // 3))

        rng = random.Random(int(semente.get("criada_ms", 0)) + int(tempo_atual // 180))
        for _ in range(params["esporos"]):
            ang = rng.uniform(0, math.tau)
            rx = local.centerx + math.cos(ang) * rng.uniform(local.width * 0.28, local.width * 0.62)
            ry = local.centery + math.sin(ang) * rng.uniform(local.height * 0.28, local.height * 0.62)
            tamanho = rng.choice([1, 1, 2, 2, 3 if perfil == "alto" else 2])
            pygame.draw.circle(aura, (*cor, rng.randint(90, 190)), (int(rx), int(ry)), tamanho)

        tela.blit(aura, (corpo.x - 14, corpo.y - 14))
        raio = max(4, int(5 + 8 * valor))
        pygame.draw.circle(tela, COR_PARASITA_ESCURA, (cx, cy), raio + 2)
        pygame.draw.circle(tela, cor, (cx, cy), raio, 1)
        pygame.draw.circle(tela, cor, (cx, cy), max(2, int(raio * valor)))
    _atualizar_e_desenhar_particulas_parasiticas(tela, tempo_atual, config_graficos)


def desenhar_semente_disparo(tela, disparo, tempo_atual, offset=(0, 0), config_graficos=None):
    if _perfil_efeito(config_graficos) == "desativado":
        return
    ox, oy = offset
    cx = disparo["rect"].centerx + ox
    cy = disparo["rect"].centery + oy
    raio = int(disparo.get("raio_vfx", 7))
    trail = disparo.get("trail", [])
    for idx, (tx, ty) in enumerate(reversed(trail[-6:])):
        fade = 1.0 - idx / 6.0
        pygame.draw.circle(tela, COR_PARASITA_ESCURA, (int(tx + ox), int(ty + oy)), max(1, int(raio * fade)), 1)
    pygame.draw.circle(tela, (25, 60, 35), (int(cx), int(cy)), raio + 4)
    pygame.draw.circle(tela, COR_PARASITA, (int(cx), int(cy)), raio + 1, 2)
    pygame.draw.circle(tela, COR_PARASITA_MADURA, (int(cx - 1), int(cy - 1)), max(2, raio // 2))
