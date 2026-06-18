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
    if config_graficos is not None and not config_graficos.get("efeitos_visuais", True):
        return
    nome = _normalizar(aurea)
    inimigos = inimigos or []

    if nome == "nula":
        carga = float(estado["nula"].get("carga", 0.0))
        if carga > 0:
            pct = max(0.0, min(1.0, carga / NULA_CARGA_MAX))
            raio = int(24 + pct * 34 + math.sin(tempo_atual * 0.012) * 3)
            cor = (170, 235, 255, int(45 + pct * 75))
            surf = pygame.Surface((raio * 2 + 4, raio * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, cor, (raio + 2, raio + 2), raio, 2)
            tela.blit(surf, (pos_x + largura // 2 - raio - 2, pos_y + altura // 2 - raio - 2), special_flags=pygame.BLEND_RGBA_ADD)

    if nome == "abissal":
        ab = estado["abissal"]
        ativo = tempo_atual < ab.get("marea_fim_ms", 0)
        pct = 1.0 if ativo else max(0.0, min(1.0, float(ab.get("profundidade", 0.0)) / ABISSAL_PROFUNDIDADE_MAX))
        if pct > 0.05:
            raio = int(42 + pct * 78)
            surf = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
            alpha = 92 if ativo else int(28 + pct * 48)
            pygame.draw.circle(surf, (38, 32, 95, alpha), (raio + 4, raio + 4), raio, 3)
            pygame.draw.circle(surf, (4, 0, 18, max(15, alpha // 2)), (raio + 4, raio + 4), max(6, raio // 3), 2)
            tela.blit(surf, (pos_x + largura // 2 - raio - 4, pos_y + altura // 2 - raio - 4), special_flags=pygame.BLEND_RGBA_ADD)

    for inimigo in inimigos:
        r = _rect(inimigo)
        if not r:
            continue
        if nome == "profetica" and inimigo.get("profetica_fim_ms", 0) > tempo_atual:
            simbolo = {"atacar": "!", "avancar": ">", "morrer": "X"}.get(inimigo.get("profetica_pressagio"), "?")
            try:
                fonte = pygame.font.Font("Texto/rainyhearts.ttf", 22)
            except Exception:
                fonte = pygame.font.Font(None, 24)
            txt = fonte.render(simbolo, True, (255, 235, 110))
            tela.blit(txt, (r.centerx - txt.get_width() // 2, r.y - 26))
        if nome == "sanguinaria" and inimigo.get("sanguinaria_ferida_ate", 0) > tempo_atual:
            pygame.draw.line(tela, (255, 35, 55), (r.left, r.top - 3), (r.right, r.top - 3), 2)
            if random.random() < 0.25:
                pygame.draw.circle(tela, (170, 0, 30), (random.randint(r.left, r.right), random.randint(r.top, r.bottom)), 2)
        if nome == "nula" and inimigo.get("nula_nulificado_ate", 0) > tempo_atual:
            pygame.draw.rect(tela, (170, 235, 255), r.inflate(6, 6), 1)
        if nome == "abissal" and inimigo.get("abissal_marcado_ate", 0) > tempo_atual:
            pygame.draw.circle(tela, (80, 80, 190), r.center, max(8, r.width // 2), 1)
