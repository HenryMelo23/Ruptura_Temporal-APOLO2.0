import math
import random

import pygame


AUREAS_AVANCADAS = {"Nula", "Abissal", "Profetica", "Sanguinaria"}

NULA_CARGA_MAX = 100.0
NULA_OCIOSO_MS = 2300
NULA_CARGA_OCIOSA_POR_S = 9.5
NULA_CARGA_ABATE_LIMPO = 18.0
NULA_DURACAO_MS = 4200

ABISSAL_PROFUNDIDADE_MAX = 100.0
ABISSAL_MAREA_MS_BASE = 5200
ABISSAL_MAREA_MS_POR_NIVEL = 550

PROFETICA_INTERVALO_BASE_MS = 11000
PROFETICA_DURACAO_MS = 6400
PROFETICA_RECOMPENSA_BASE = 35

SANGUINARIA_HITS_FERIDA = 3
SANGUINARIA_JANELA_HIT_MS = 4300
SANGUINARIA_FERIDA_MS = 7800
SANGUINARIA_EXPLOSAO_BASE = 4

_FONTES_HUD = {}


def _normalizar(aurea):
    return str(aurea or "").strip().lower()


def _nivel(upgrades, nome):
    try:
        return max(0, min(5, int((upgrades or {}).get(nome, 0))))
    except Exception:
        return 0


def _rect(alvo):
    if isinstance(alvo, dict):
        rect = alvo.get("rect")
        if isinstance(rect, pygame.Rect):
            return rect
    return None


def _vida_pct(alvo):
    if not isinstance(alvo, dict):
        return 1.0
    vida_max = max(1.0, float(alvo.get("vida_maxima", alvo.get("vida", 1)) or 1))
    return max(0.0, min(1.0, float(alvo.get("vida", vida_max)) / vida_max))


def _efeito(efeitos_texto, texto, x, y, tempo_atual, cor):
    if efeitos_texto is None:
        return
    efeitos_texto.append({
        "texto": texto,
        "x": float(x),
        "y": float(y),
        "tempo_inicio": int(tempo_atual),
        "cor": cor,
    })


def _fonte_hud(tamanho):
    tamanho = int(tamanho)
    if tamanho not in _FONTES_HUD:
        try:
            _FONTES_HUD[tamanho] = pygame.font.Font("Texto/rainyhearts.ttf", tamanho)
        except Exception:
            _FONTES_HUD[tamanho] = pygame.font.Font(None, tamanho)
    return _FONTES_HUD[tamanho]


def _texto_hud(surf, texto, pos, cor, tamanho=17, centro=False):
    imagem = _fonte_hud(tamanho).render(str(texto), True, cor)
    rect = imagem.get_rect()
    if centro:
        rect.center = (int(pos[0]), int(pos[1]))
    else:
        rect.topleft = (int(pos[0]), int(pos[1]))
    surf.blit(imagem, rect)


def _painel_aurea(tamanho, cor, alpha=205):
    surf = pygame.Surface(tamanho, pygame.SRCALPHA)
    rect = surf.get_rect()
    pygame.draw.rect(surf, (5, 6, 14, alpha), rect, border_radius=10)
    pygame.draw.rect(surf, (*cor, 88), rect.inflate(-2, -2), 1, border_radius=9)
    pygame.draw.line(surf, (255, 255, 255, 26), (14, 7), (rect.width - 14, 7), 1)
    return surf


def _hud_nula(estado, tempo_atual):
    nula = estado["nula"]
    pct = max(0.0, min(1.0, float(nula.get("carga", 0.0)) / NULA_CARGA_MAX))
    armada = bool(nula.get("armada")) or pct >= 1.0
    cor = (190, 240, 255)
    surf = _painel_aurea((202, 44), cor, alpha=178)
    pulso = (math.sin(tempo_atual * 0.012) + 1.0) * 0.5

    # O nucleo vazio contrai conforme a carga cresce: a barra e uma fissura,
    # nao um retangulo preenchido.
    centro = (24, 22)
    pygame.draw.circle(surf, (2, 8, 14, 235), centro, 14)
    pygame.draw.circle(surf, (*cor, int(95 + pulso * 80)), centro, int(12 + pulso * 2), 2)
    pygame.draw.circle(surf, (245, 254, 255, 230), centro, int(2 + pct * 5))
    for i in range(6):
        ang = tempo_atual * 0.003 + i * math.tau / 6
        r1 = 8 + pct * 5
        r2 = 14 + pulso * 3
        pygame.draw.line(
            surf, (*cor, 125),
            (centro[0] + math.cos(ang) * r1, centro[1] + math.sin(ang) * r1),
            (centro[0] + math.cos(ang + 0.22) * r2, centro[1] + math.sin(ang + 0.22) * r2), 1,
        )

    inicio_x = 48
    segmentos = 9
    ativos = int(round(pct * segmentos))
    for i in range(segmentos):
        x = inicio_x + i * 15
        tremor = int(math.sin(tempo_atual * 0.009 + i * 1.7) * (2 if i >= ativos else 1))
        pontos = [(x, 25 + tremor), (x + 5, 20 - tremor), (x + 10, 25 + tremor), (x + 6, 31 - tremor)]
        if i < ativos:
            cor_segmento = (220, 250, 255, 225)
            pygame.draw.polygon(surf, cor_segmento, pontos)
            pygame.draw.circle(surf, (255, 255, 255, 120), (x + 5, 25), 2)
        else:
            pygame.draw.polygon(surf, (75, 105, 120, 72), pontos, 1)

    _texto_hud(surf, "NULO PRONTO" if armada else "VAZIO", (48, 4), cor, 13)
    _texto_hud(surf, "PRONTO" if armada else f"{int(pct * 100)}%", (181, 36), (235, 250, 255), 12, centro=True)
    return surf


def _hud_abissal(estado, tempo_atual):
    ab = estado["abissal"]
    ativo = tempo_atual < int(ab.get("marea_fim_ms", 0))
    pct = max(0.0, min(1.0, float(ab.get("profundidade", 0.0)) / ABISSAL_PROFUNDIDADE_MAX))
    visual_pct = 1.0 if ativo else pct
    cor = (105, 92, 230)
    surf = _painel_aurea((202, 44), cor, alpha=184)
    pulso = (math.sin(tempo_atual * 0.009) + 1.0) * 0.5

    # Medidor vertical: quanto mais fundo, mais camadas ficam submersas.
    cx, cy = 24, 22
    for camada in range(3):
        raio = 15 - camada * 4
        pygame.draw.circle(surf, (55, 42, 145, 80 + camada * 18), (cx, cy), raio, 2)
    pygame.draw.circle(surf, (2, 1, 14, 245), (cx, cy), int(5 + visual_pct * 5))
    pygame.draw.circle(surf, (145, 125, 255, int(110 + pulso * 90)), (cx, cy), int(2 + pulso * 2))

    inicio_x = 48
    colunas = 11
    for i in range(colunas):
        onda = math.sin(tempo_atual * (0.014 if ativo else 0.006) + i * 0.72)
        altura = int(4 + visual_pct * 13 + onda * (3 if ativo else 1))
        topo = 32 - altura
        cor_coluna = (75 + int(visual_pct * 30), 62 + int(visual_pct * 40), 185 + int(visual_pct * 55), 220)
        pygame.draw.rect(surf, cor_coluna, (inicio_x + i * 13, topo, 7, altura), border_radius=3)
        pygame.draw.circle(surf, (155, 145, 255, 100), (inicio_x + i * 13 + 3, topo), 3)

    if ativo:
        restante = max(0, int(ab.get("marea_fim_ms", 0)) - int(tempo_atual))
        titulo = "MARE NEGRA"
        estado_txt = f"{restante / 1000.0:.1f}s"
    else:
        titulo = "PROFUNDIDADE"
        estado_txt = f"{int(pct * 100)}%"
    _texto_hud(surf, titulo, (48, 4), (170, 160, 255) if ativo else (130, 120, 245), 13)
    _texto_hud(surf, estado_txt, (181, 36), (225, 220, 255), 12, centro=True)
    return surf


def _hud_profetica(estado, tempo_atual):
    prof = estado["profetica"]
    nivel = int(estado["niveis"].get("Profetica", 0))
    marcado = bool(prof.get("alvo_id")) and tempo_atual <= int(prof.get("fim_ms", 0))
    quebrado = tempo_atual < int(prof.get("destino_quebrado_fim_ms", 0))
    intervalo = max(6200, PROFETICA_INTERVALO_BASE_MS - nivel * 850)
    if marcado:
        restante = max(0, int(prof.get("fim_ms", 0)) - int(tempo_atual))
        pct = max(0.0, min(1.0, restante / float(PROFETICA_DURACAO_MS)))
    else:
        restante = max(0, int(prof.get("proximo_pressagio_ms", 0)) - int(tempo_atual))
        pct = max(0.0, min(1.0, 1.0 - restante / float(intervalo)))

    cor = (255, 225, 100)
    surf = _painel_aurea((216, 46), cor, alpha=182)
    pulso = (math.sin(tempo_atual * 0.013) + 1.0) * 0.5
    cx, cy = 25, 23
    olho = pygame.Rect(cx - 17, cy - 8, 34, 16)
    pygame.draw.ellipse(surf, (64, 45, 12, 220), olho)
    pygame.draw.ellipse(surf, (*cor, 235), olho, 2)
    pygame.draw.circle(surf, (255, 252, 210, 245), (cx, cy), int(3 + pct * 3))
    pygame.draw.circle(surf, (180, 95, 20, 255), (cx, cy), int(1 + pulso * 2))
    for i in range(5):
        ang = -math.pi * 0.82 + i * math.pi * 0.41
        pygame.draw.line(
            surf, (255, 240, 150, 150),
            (cx + math.cos(ang) * 19, cy + math.sin(ang) * 12),
            (cx + math.cos(ang) * (23 + pulso * 2), cy + math.sin(ang) * (15 + pulso * 2)), 1,
        )

    # A progressao e uma constelacao: cada estrela acende um passo do destino.
    inicio_x = 51
    estrelas = 7
    acesas = int(round(pct * estrelas))
    pontos = []
    for i in range(estrelas):
        x = inicio_x + i * 22
        y = 28 + int(math.sin(i * 1.45) * 5)
        pontos.append((x, y))
    for i in range(len(pontos) - 1):
        pygame.draw.line(surf, (125, 98, 35, 115), pontos[i], pontos[i + 1], 1)
    for i, (x, y) in enumerate(pontos):
        raio = 3 + (1 if i < acesas and math.sin(tempo_atual * 0.016 + i) > 0 else 0)
        if i < acesas:
            pygame.draw.line(surf, (255, 240, 145, 205), (x - raio - 2, y), (x + raio + 2, y), 1)
            pygame.draw.line(surf, (255, 240, 145, 205), (x, y - raio - 2), (x, y + raio + 2), 1)
            pygame.draw.circle(surf, (255, 250, 205, 245), (x, y), raio)
        else:
            pygame.draw.circle(surf, (105, 82, 35, 125), (x, y), 3, 1)

    if quebrado:
        titulo = "DESTINO QUEBRADO"
    elif marcado:
        titulo = f"PRESSAGIO: {str(prof.get('tipo') or '').upper()}"
    else:
        titulo = "ORACULO OBSERVA"
    _texto_hud(surf, titulo, (51, 4), (195, 135, 255) if quebrado else cor, 13)
    _texto_hud(surf, f"ECO {int(prof.get('sequencia', 0))}", (190, 38), (255, 245, 190), 12, centro=True)
    return surf


def _desenhar_hud_aurea(tela, estado, nome, tempo_atual):
    try:
        from ui_helpers import palco_ativo, registrar_widget_aurea
        usando_palco = palco_ativo()
    except Exception:
        usando_palco = False

    if nome not in {"nula", "abissal", "profetica"}:
        if usando_palco:
            registrar_widget_aurea(None)
        return
    if nome == "nula":
        widget = _hud_nula(estado, tempo_atual)
    elif nome == "abissal":
        widget = _hud_abissal(estado, tempo_atual)
    else:
        widget = _hud_profetica(estado, tempo_atual)
    if usando_palco and registrar_widget_aurea(widget):
        return
    # Fallback para superficies isoladas usadas em previews e telas antigas.
    x = max(8, min(270, tela.get_width() - widget.get_width() - 110))
    tela.blit(widget, (x, 10))


def criar_estado(upgrades=None, aurea=None, agora_ms=0):
    agora = int(agora_ms or 0)
    return {
        "niveis": {
            "Nula": _nivel(upgrades, "Nula"),
            "Abissal": _nivel(upgrades, "Abissal"),
            "Profetica": _nivel(upgrades, "Profetica"),
            "Sanguinaria": _nivel(upgrades, "Sanguinaria"),
        },
        "ultimo_ataque_ms": agora,
        "nula": {
            "carga": 0.0,
            "armada": False,
            "ultimo_update_ms": agora,
        },
        "abissal": {
            "profundidade": 0.0,
            "marea_fim_ms": 0,
            "ultimo_update_ms": agora,
        },
        "profetica": {
            "proximo_pressagio_ms": agora + max(5500, PROFETICA_INTERVALO_BASE_MS - _nivel(upgrades, "Profetica") * 800),
            "alvo_id": None,
            "tipo": None,
            "fim_ms": 0,
            "sequencia": 0,
            "destino_quebrado_fim_ms": 0,
        },
        "sanguinaria": {
            "hits": {},
            "sede": 0.0,
            "ultimo_hit_ferida_ms": agora,
            "feridas_combate": 0,
            "explosao_pronta": False,
            "vulneravel_fim_ms": 0,
        },
    }


def marcar_disparo(estado, aurea, disparo, tempo_atual, efeitos_texto=None):
    if not estado or not isinstance(disparo, dict):
        return disparo
    estado["ultimo_ataque_ms"] = int(tempo_atual)
    nome = _normalizar(aurea)
    if nome == "nula":
        nula = estado["nula"]
        if nula.get("armada") or nula.get("carga", 0.0) >= NULA_CARGA_MAX:
            disparo["nula_nulificacao"] = True
            nula["armada"] = False
            nula["carga"] = 0.0
            _efeito(efeitos_texto, "NULIFICACAO", disparo["rect"].x, disparo["rect"].y - 20, tempo_atual, (190, 240, 255))
    return disparo


def fator_velocidade_jogador(estado, aurea, agora_ms=None):
    if not estado:
        return 1.0
    nome = _normalizar(aurea)
    agora = pygame.time.get_ticks() if agora_ms is None else int(agora_ms)
    if nome == "abissal":
        prof = max(0.0, min(ABISSAL_PROFUNDIDADE_MAX, estado["abissal"].get("profundidade", 0.0)))
        peso = 1.0 - min(0.16, prof / ABISSAL_PROFUNDIDADE_MAX * 0.16)
        if agora < estado["abissal"].get("marea_fim_ms", 0):
            peso -= 0.04
        return max(0.78, peso)
    if nome == "sanguinaria" and agora < estado["sanguinaria"].get("vulneravel_fim_ms", 0):
        return 0.95
    return 1.0


def cooldown_teleporte(estado, aurea, base_ms, agora_ms=None):
    if not estado:
        return int(base_ms)
    nome = _normalizar(aurea)
    agora = pygame.time.get_ticks() if agora_ms is None else int(agora_ms)
    if nome == "nula" and estado["nula"].get("carga", 0.0) > 0:
        return int(base_ms * 1.04)
    if nome == "abissal":
        prof = max(0.0, min(ABISSAL_PROFUNDIDADE_MAX, estado["abissal"].get("profundidade", 0.0)))
        mult = 1.0 + prof / ABISSAL_PROFUNDIDADE_MAX * 0.10
        if agora < estado["abissal"].get("marea_fim_ms", 0):
            mult += 0.08
        return int(base_ms * mult)
    if nome == "profetica" and agora < estado["profetica"].get("destino_quebrado_fim_ms", 0):
        return int(base_ms * 1.12)
    return int(base_ms)


def aplicar_dano_inimigo(estado, aurea, inimigo, disparo, dano, tempo_atual, efeitos_texto=None, inimigos=None):
    if not estado or not isinstance(inimigo, dict):
        return dano
    nome = _normalizar(aurea)
    rect = _rect(inimigo)
    x = rect.centerx if rect else 0
    y = rect.y if rect else 0

    if nome == "nula" and isinstance(disparo, dict) and disparo.get("nula_nulificacao"):
        nivel = estado["niveis"].get("Nula", 0)
        inimigo["nula_nulificado_ate"] = int(tempo_atual) + NULA_DURACAO_MS + nivel * 350
        inimigo["nula_resistencia_mult"] = max(0.55, 0.82 - nivel * 0.045)
        if _vida_pct(inimigo) >= 0.55:
            dano *= 1.18 + nivel * 0.035
        _efeito(efeitos_texto, "NULO", x, y - 18, tempo_atual, (170, 230, 255))

    if nome == "abissal":
        nivel = estado["niveis"].get("Abissal", 0)
        ab = estado["abissal"]
        if int(tempo_atual) < ab.get("marea_fim_ms", 0):
            if _vida_pct(inimigo) <= 0.28 + nivel * 0.015:
                dano *= 1.22 + nivel * 0.04
                inimigo["abissal_marcado_ate"] = int(tempo_atual) + 2600
            else:
                dano *= 1.06 + nivel * 0.015
        elif _vida_pct(inimigo) <= 0.18:
            dano *= 1.04 + nivel * 0.01

    if nome == "profetica":
        prof = estado["profetica"]
        if prof.get("alvo_id") == id(inimigo) and int(tempo_atual) <= prof.get("fim_ms", 0):
            tipo = prof.get("tipo")
            if tipo in ("atacar", "avancar", "morrer"):
                dano *= 1.22 + estado["niveis"].get("Profetica", 0) * 0.04
                prof["sequencia"] = int(prof.get("sequencia", 0)) + 1
                _efeito(efeitos_texto, "PRESSAGIO CUMPRIDO", x, y - 22, tempo_atual, (255, 235, 120))
                prof["alvo_id"] = None

    if nome == "sanguinaria":
        nivel = estado["niveis"].get("Sanguinaria", 0)
        sang = estado["sanguinaria"]
        alvo_id = id(inimigo)
        hits = sang.setdefault("hits", {})
        dados = hits.setdefault(alvo_id, {"contagem": 0, "ultimo_ms": 0})
        if int(tempo_atual) - int(dados.get("ultimo_ms", 0)) > SANGUINARIA_JANELA_HIT_MS:
            dados["contagem"] = 0
        dados["contagem"] = int(dados.get("contagem", 0)) + 1
        dados["ultimo_ms"] = int(tempo_atual)

        ferida_ativa = int(tempo_atual) < int(inimigo.get("sanguinaria_ferida_ate", 0))
        if not ferida_ativa and dados["contagem"] >= max(2, SANGUINARIA_HITS_FERIDA - (1 if nivel >= 5 else 0)):
            inimigo["sanguinaria_ferida_ate"] = int(tempo_atual) + SANGUINARIA_FERIDA_MS + nivel * 450
            sang["feridas_combate"] = int(sang.get("feridas_combate", 0)) + 1
            sang["sede"] = min(100.0, float(sang.get("sede", 0.0)) + 12.0 + nivel * 2.0)
            ferida_ativa = True
            _efeito(efeitos_texto, "FERIDA ABERTA", x, y - 20, tempo_atual, (255, 55, 70))

        if ferida_ativa:
            sede = min(1.0, float(sang.get("sede", 0.0)) / 100.0)
            dano *= 1.12 + nivel * 0.035 + sede * 0.14
            sang["ultimo_hit_ferida_ms"] = int(tempo_atual)
            if sang.get("explosao_pronta"):
                dano *= 1.35
                sang["explosao_pronta"] = False
                sang["feridas_combate"] = 0
                _efeito(efeitos_texto, "CARNIFICINA", x, y - 32, tempo_atual, (255, 25, 45))
                if inimigos:
                    for outro in inimigos:
                        if outro is inimigo or not isinstance(outro, dict):
                            continue
                        r2 = _rect(outro)
                        if r2 and rect and math.hypot(r2.centerx - rect.centerx, r2.centery - rect.centery) <= 96:
                            outro["vida"] = float(outro.get("vida", 0)) - dano * 0.22

        limite = max(2, SANGUINARIA_EXPLOSAO_BASE - (1 if nivel >= 5 else 0))
        if int(sang.get("feridas_combate", 0)) >= limite:
            sang["explosao_pronta"] = True

    return dano


def notificar_abate(estado, aurea, inimigo, tempo_atual, efeitos_texto=None):
    if not estado:
        return {"pontuacao_bonus": 0, "reduzir_cooldown_habilidade_ms": 0}
    nome = _normalizar(aurea)
    rect = _rect(inimigo)
    x = rect.centerx if rect else 0
    y = rect.y if rect else 0
    retorno = {"pontuacao_bonus": 0, "reduzir_cooldown_habilidade_ms": 0}

    if nome == "nula":
        nula = estado["nula"]
        nula["carga"] = min(NULA_CARGA_MAX, float(nula.get("carga", 0.0)) + NULA_CARGA_ABATE_LIMPO)
        if nula["carga"] >= NULA_CARGA_MAX:
            nula["armada"] = True
            _efeito(efeitos_texto, "VAZIO PRONTO", x, y - 24, tempo_atual, (190, 245, 255))

    if nome == "profetica":
        prof = estado["profetica"]
        if prof.get("alvo_id") == id(inimigo):
            bonus = PROFETICA_RECOMPENSA_BASE + estado["niveis"].get("Profetica", 0) * 15 + int(prof.get("sequencia", 0)) * 10
            retorno["pontuacao_bonus"] = bonus
            prof["sequencia"] = int(prof.get("sequencia", 0)) + 1
            prof["alvo_id"] = None
            _efeito(efeitos_texto, f"+{bonus} PRESSAGIO", x, y - 28, tempo_atual, (255, 235, 120))

    if nome == "sanguinaria":
        sang = estado["sanguinaria"]
        if int(tempo_atual) < int(inimigo.get("sanguinaria_ferida_ate", 0)):
            sang["sede"] = min(100.0, float(sang.get("sede", 0.0)) + 10.0)
            retorno["reduzir_cooldown_habilidade_ms"] = 180 + estado["niveis"].get("Sanguinaria", 0) * 30

    return retorno


def aplicar_recompensa_abate(estado, aurea, inimigo, tempo_atual, efeitos_texto=None):
    evento = notificar_abate(estado, aurea, inimigo, tempo_atual, efeitos_texto)
    return (
        int(evento.get("pontuacao_bonus", 0)),
        int(evento.get("reduzir_cooldown_habilidade_ms", 0)),
    )


def atualizar(estado, aurea, tempo_atual, pos_x, pos_y, largura, altura, inimigos=None, efeitos_texto=None, boss_vivo=False):
    if not estado:
        return
    nome = _normalizar(aurea)
    tempo_atual = int(tempo_atual)
    inimigos = inimigos or []

    if nome == "nula":
        nula = estado["nula"]
        ultimo = int(nula.get("ultimo_update_ms", tempo_atual))
        nula["ultimo_update_ms"] = tempo_atual
        sem_atacar = tempo_atual - int(estado.get("ultimo_ataque_ms", tempo_atual))
        if sem_atacar >= NULA_OCIOSO_MS:
            dt_s = max(0.0, min(0.12, (tempo_atual - ultimo) / 1000.0))
            nula["carga"] = min(NULA_CARGA_MAX, float(nula.get("carga", 0.0)) + NULA_CARGA_OCIOSA_POR_S * dt_s)
            if nula["carga"] >= NULA_CARGA_MAX:
                nula["armada"] = True

    if nome == "abissal":
        nivel = estado["niveis"].get("Abissal", 0)
        ab = estado["abissal"]
        ultimo = int(ab.get("ultimo_update_ms", tempo_atual))
        ab["ultimo_update_ms"] = tempo_atual
        dt_s = max(0.0, min(0.12, (tempo_atual - ultimo) / 1000.0))
        centro = (pos_x + largura / 2, pos_y + altura / 2)
        perto = 0
        for inimigo in inimigos:
            r = _rect(inimigo)
            if r and math.hypot(r.centerx - centro[0], r.centery - centro[1]) <= 190:
                perto += 1
                if tempo_atual < ab.get("marea_fim_ms", 0):
                    puxao = 0.55 + nivel * 0.04
                    dx = centro[0] - r.centerx
                    dy = centro[1] - r.centery
                    dist = max(1.0, math.hypot(dx, dy))
                    r.x += int(dx / dist * puxao)
                    r.y += int(dy / dist * puxao)
                    if _vida_pct(inimigo) <= 0.20 + nivel * 0.015:
                        inimigo["vida"] = float(inimigo.get("vida", 0)) - max(1.0, float(inimigo.get("vida_maxima", 20)) * (0.010 + nivel * 0.0015))

        ganho = (len(inimigos) * 0.20 + perto * 0.52 + (0.42 if boss_vivo else 0.0)) * dt_s * (1.0 + nivel * 0.08)
        if tempo_atual >= ab.get("marea_fim_ms", 0):
            ab["profundidade"] = min(ABISSAL_PROFUNDIDADE_MAX, float(ab.get("profundidade", 0.0)) + ganho)
            if ab["profundidade"] >= ABISSAL_PROFUNDIDADE_MAX:
                ab["profundidade"] = 0.0
                ab["marea_fim_ms"] = tempo_atual + ABISSAL_MAREA_MS_BASE + nivel * ABISSAL_MAREA_MS_POR_NIVEL
                _efeito(efeitos_texto, "MARE NEGRA", pos_x, pos_y - 30, tempo_atual, (80, 80, 180))

    if nome == "profetica":
        prof = estado["profetica"]
        if prof.get("alvo_id") and tempo_atual > prof.get("fim_ms", 0):
            prof["alvo_id"] = None
            prof["tipo"] = None
            prof["sequencia"] = 0
            prof["destino_quebrado_fim_ms"] = tempo_atual + 3500
            _efeito(efeitos_texto, "DESTINO QUEBRADO", pos_x, pos_y - 24, tempo_atual, (180, 120, 255))
        if not prof.get("alvo_id") and tempo_atual >= prof.get("proximo_pressagio_ms", 0) and inimigos:
            candidatos = [i for i in inimigos if isinstance(i, dict) and _rect(i) and float(i.get("vida", 1)) > 0]
            if candidatos:
                alvo = random.choice(candidatos)
                tipo = random.choice(("atacar", "avancar", "morrer"))
                alvo["profetica_pressagio"] = tipo
                alvo["profetica_fim_ms"] = tempo_atual + PROFETICA_DURACAO_MS
                prof["alvo_id"] = id(alvo)
                prof["tipo"] = tipo
                prof["fim_ms"] = tempo_atual + PROFETICA_DURACAO_MS
                intervalo = max(6200, PROFETICA_INTERVALO_BASE_MS - estado["niveis"].get("Profetica", 0) * 850)
                prof["proximo_pressagio_ms"] = tempo_atual + intervalo

    if nome == "sanguinaria":
        sang = estado["sanguinaria"]
        if tempo_atual - int(sang.get("ultimo_hit_ferida_ms", tempo_atual)) > 8500:
            sang["sede"] = max(0.0, float(sang.get("sede", 0.0)) - 0.18)
            if float(sang.get("sede", 0.0)) <= 0.0 and int(sang.get("feridas_combate", 0)) > 0:
                sang["feridas_combate"] = 0
                sang["explosao_pronta"] = False
                sang["vulneravel_fim_ms"] = tempo_atual + 2600


def desenhar(tela, estado, aurea, tempo_atual, pos_x, pos_y, largura, altura, inimigos=None, config_graficos=None):
    if not estado or tela is None:
        return
    nome = _normalizar(aurea)
    if config_graficos is not None and not config_graficos.get("interface", True):
        return
    if config_graficos is not None and not config_graficos.get("efeitos_visuais", True):
        _desenhar_hud_aurea(tela, estado, nome, tempo_atual)
        return
    inimigos = inimigos or []

    if nome == "nula":
        carga = float(estado["nula"].get("carga", 0.0))
        if carga > 0:
            pct = max(0.0, min(1.0, carga / NULA_CARGA_MAX))
            raio = int(24 + pct * 34 + math.sin(tempo_atual * 0.012) * 3)
            cor = (170, 235, 255, int(45 + pct * 75))
            surf = pygame.Surface((raio * 2 + 4, raio * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, cor, (raio + 2, raio + 2), raio, 2)
            for i in range(10):
                ang = tempo_atual * 0.003 + i * (math.tau / 10.0)
                r1 = raio * (0.30 + pct * 0.22)
                r2 = raio * (0.82 + 0.08 * math.sin(tempo_atual * 0.006 + i))
                p1 = (raio + 2 + math.cos(ang) * r1, raio + 2 + math.sin(ang) * r1)
                p2 = (raio + 2 + math.cos(ang + 0.35) * r2, raio + 2 + math.sin(ang + 0.35) * r2)
                pygame.draw.line(surf, (190, 245, 255, int(24 + pct * 55)), p1, p2, 1)
            pygame.draw.circle(surf, (10, 25, 35, int(28 + pct * 55)), (raio + 2, raio + 2), max(7, int(raio * 0.32)))
            tela.blit(surf, (pos_x + largura // 2 - raio - 2, pos_y + altura // 2 - raio - 2), special_flags=pygame.BLEND_RGBA_ADD)

    if nome == "abissal":
        ab = estado["abissal"]
        ativo = tempo_atual < ab.get("marea_fim_ms", 0)
        pct = 1.0 if ativo else max(0.0, min(1.0, float(ab.get("profundidade", 0.0)) / ABISSAL_PROFUNDIDADE_MAX))
        if pct > 0.05:
            raio = int(42 + pct * 78)
            surf = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
            alpha = 92 if ativo else int(28 + pct * 48)
            for camada in range(4):
                r_camada = max(8, raio - camada * max(8, raio // 6))
                pygame.draw.circle(surf, (35, 25, 105, max(16, alpha - camada * 14)), (raio + 4, raio + 4), r_camada, 2)
            for i in range(14):
                ang = -tempo_atual * 0.004 + i * (math.tau / 14.0)
                r1 = raio * 0.18
                r2 = raio * (0.72 + 0.14 * math.sin(tempo_atual * 0.005 + i))
                pygame.draw.line(
                    surf,
                    (95, 80, 220, max(18, alpha // 2)),
                    (raio + 4 + math.cos(ang) * r1, raio + 4 + math.sin(ang) * r1),
                    (raio + 4 + math.cos(ang + 0.55) * r2, raio + 4 + math.sin(ang + 0.55) * r2),
                    2 if ativo else 1,
                )
            pygame.draw.circle(surf, (4, 0, 18, max(24, alpha // 2)), (raio + 4, raio + 4), max(8, raio // 3), 0)
            tela.blit(surf, (pos_x + largura // 2 - raio - 4, pos_y + altura // 2 - raio - 4), special_flags=pygame.BLEND_RGBA_ADD)

    for inimigo in inimigos:
        r = _rect(inimigo)
        if not r:
            continue
        if nome == "profetica" and inimigo.get("profetica_fim_ms", 0) > tempo_atual:
            simbolo = {"atacar": "!", "avancar": ">", "morrer": "X"}.get(inimigo.get("profetica_pressagio"), "?")
            try:
                fonte = pygame.font.Font("Texto/rainyhearts.ttf", 28)
            except Exception:
                fonte = pygame.font.Font(None, 30)
            pulso = (math.sin(tempo_atual * 0.010) + 1.0) * 0.5
            raio = int(max(r.width, r.height) * (0.72 + pulso * 0.12))
            surf = pygame.Surface((raio * 2 + 36, raio * 2 + 58), pygame.SRCALPHA)
            cx = surf.get_width() // 2
            cy = raio + 22
            pygame.draw.circle(surf, (255, 220, 90, 68), (cx, cy), raio + 10, 2)
            pygame.draw.circle(surf, (255, 245, 165, 128), (cx, cy), raio, 2)
            for i in range(12):
                ang = tempo_atual * 0.005 + i * (math.tau / 12.0)
                p1 = (cx + math.cos(ang) * (raio * 0.55), cy + math.sin(ang) * (raio * 0.55))
                p2 = (cx + math.cos(ang + 0.22) * (raio + 8), cy + math.sin(ang + 0.22) * (raio + 8))
                pygame.draw.line(surf, (255, 232, 90, 72), p1, p2, 1)
            pygame.draw.line(surf, (255, 245, 170, 120), (cx, 0), (cx, cy - raio), 2)
            pygame.draw.line(surf, (255, 210, 70, 84), (cx - 10, 5), (cx + 10, 5), 2)
            tela.blit(surf, (r.centerx - cx, r.centery - cy), special_flags=pygame.BLEND_RGBA_ADD)
            txt = fonte.render(simbolo, True, (255, 250, 180))
            tela.blit(txt, (r.centerx - txt.get_width() // 2, r.y - 26))
        if nome == "sanguinaria" and inimigo.get("sanguinaria_ferida_ate", 0) > tempo_atual:
            pulso = (math.sin(tempo_atual * 0.014) + 1.0) * 0.5
            aura = pygame.Surface((r.width + 34, r.height + 34), pygame.SRCALPHA)
            pygame.draw.ellipse(aura, (255, 25, 55, int(60 + pulso * 50)), aura.get_rect(), 3)
            pygame.draw.ellipse(aura, (100, 0, 22, int(34 + pulso * 32)), aura.get_rect().inflate(-12, -12), 2)
            tela.blit(aura, (r.x - 17, r.y - 17), special_flags=pygame.BLEND_RGBA_ADD)
            pygame.draw.line(tela, (255, 35, 55), (r.left - 4, r.top - 3), (r.right + 4, r.top - 3), 3)
            if random.random() < 0.25:
                pygame.draw.circle(tela, (220, 0, 40), (random.randint(r.left, r.right), random.randint(r.top, r.bottom)), random.randint(2, 4))
        if nome == "nula" and inimigo.get("nula_nulificado_ate", 0) > tempo_atual:
            inflado = r.inflate(14, 14)
            pygame.draw.rect(tela, (170, 235, 255), inflado, 2)
            for i in range(6):
                off = int(math.sin(tempo_atual * 0.015 + i) * 5)
                pygame.draw.line(tela, (120, 230, 255), (inflado.left + i * inflado.w // 6, inflado.top + off), (inflado.left + i * inflado.w // 6 + 10, inflado.bottom - off), 1)
        if nome == "abissal" and inimigo.get("abissal_marcado_ate", 0) > tempo_atual:
            raio = max(10, int(max(r.width, r.height) * 0.62))
            pygame.draw.circle(tela, (80, 80, 190), r.center, raio, 2)
            pygame.draw.circle(tela, (18, 8, 40), r.center, max(5, raio // 2), 1)

    _desenhar_hud_aurea(tela, estado, nome, tempo_atual)
