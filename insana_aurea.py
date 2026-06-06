import math
import random

import pygame


INSANA_ECOS_BASE = 4
INSANA_ECOS_MAX = 5
INSANA_DELAY_MS = 1000
INSANA_COOLDOWN_BASE_MS = 20000
INSANA_COOLDOWN_MIN_MS = 15000
INSANA_DEBUFF_DASH_MS = 2000
INSANA_DANO_ECO_BASE = 0.45
INSANA_DANO_ECO_POR_NIVEL = 0.03
INSANA_SPRITES_ECO = ("Sprites/Geo_ECO1.png", "Sprites/Geo_ECO2.png")

_SPRITES_ECO_CACHE = {}


def _eh_insana(aurea):
    return str(aurea).strip().lower() == "insana"


def criar_estado_insana(nivel=0, agora_ms=0):
    nivel = max(0, int(nivel or 0))
    cooldown = max(INSANA_COOLDOWN_MIN_MS, INSANA_COOLDOWN_BASE_MS - nivel * 1000)
    return {
        "nivel": nivel,
        "ativa": False,
        "ecos_restantes": 0,
        "ecos_proxima_ativacao": INSANA_ECOS_BASE,
        "ecos": [],
        "cooldown_ms": cooldown,
        "proximo_uso_ms": int(agora_ms or 0),
        "debuff_fim_ms": 0,
        "penalidade_dash_pendente": False,
        "ativacao_id": 0,
    }


def dano_mult_disparo(disparo):
    if not isinstance(disparo, dict):
        return 1.0
    return float(disparo.get("dano_mult", 1.0))


def notificar_abate_insana(estado, aurea, disparo):
    if not _eh_insana(aurea) or not estado or not isinstance(disparo, dict):
        return
    if disparo.get("eco_insana"):
        estado["ecos_proxima_ativacao"] = min(
            INSANA_ECOS_MAX,
            max(INSANA_ECOS_BASE, int(estado.get("ecos_proxima_ativacao", INSANA_ECOS_BASE))) + 1,
        )


def registrar_tiro_insana(
    estado,
    aurea,
    tempo_atual,
    x_player,
    y_player,
    centro_x,
    centro_y,
    angulo,
    largura_disparo,
    altura_disparo,
    velocidade_disparo,
):
    if not _eh_insana(aurea) or not estado:
        return

    if not estado.get("ativa"):
        if tempo_atual < estado.get("proximo_uso_ms", 0):
            return
        estado["ativa"] = True
        estado["ecos_restantes"] = max(INSANA_ECOS_BASE, min(INSANA_ECOS_MAX, int(estado.get("ecos_proxima_ativacao", INSANA_ECOS_BASE))))
        estado["ecos_proxima_ativacao"] = INSANA_ECOS_BASE
        estado["ativacao_id"] = int(estado.get("ativacao_id", 0)) + 1

    if estado.get("ecos_restantes", 0) <= 0:
        return

    indice = estado["ecos_restantes"]
    estado["ecos_restantes"] -= 1
    angulo = float(angulo)
    estado.setdefault("ecos", []).append({
        "x": float(x_player),
        "y": float(y_player),
        "centro_x": float(centro_x),
        "centro_y": float(centro_y),
        "angulo": angulo,
        "largura_disparo": int(largura_disparo),
        "altura_disparo": int(altura_disparo),
        "velocidade_disparo": float(velocidade_disparo),
        "criado_ms": int(tempo_atual),
        "disparar_ms": int(tempo_atual + INSANA_DELAY_MS),
        "disparou_ms": 0,
        "sprite_idx": 0,
        "fase_pulso": indice,
        "virado_esquerda": math.cos(angulo) < 0,
        "ativacao_id": estado.get("ativacao_id", 0),
    })


def atualizar_insana(estado, aurea, tempo_atual, disparos, vfx_disparo_player):
    if not _eh_insana(aurea) or not estado:
        return

    ecos_vivos = []
    for eco in estado.get("ecos", []):
        if not eco.get("disparou_ms") and tempo_atual >= eco.get("disparar_ms", 0):
            disparo = vfx_disparo_player.criar_disparo(
                eco["centro_x"],
                eco["centro_y"],
                eco["largura_disparo"],
                eco["altura_disparo"],
                eco["angulo"],
                eco["velocidade_disparo"] * 0.92,
                tempo_atual,
                False,
            )
            nivel = int(estado.get("nivel", 0))
            disparo["eco_insana"] = True
            disparo["insana_vfx"] = True
            disparo["dano_mult"] = min(0.62, INSANA_DANO_ECO_BASE + nivel * INSANA_DANO_ECO_POR_NIVEL)
            disparos.append(disparo)
            eco["disparou_ms"] = tempo_atual

        if not eco.get("disparou_ms") or tempo_atual - eco["disparou_ms"] < 520:
            ecos_vivos.append(eco)

    estado["ecos"] = ecos_vivos

    if estado.get("ativa") and estado.get("ecos_restantes", 0) <= 0:
        todos_dispararam = all(eco.get("disparou_ms") for eco in estado.get("ecos", []))
        if todos_dispararam:
            estado["ativa"] = False
            estado["proximo_uso_ms"] = tempo_atual + int(estado.get("cooldown_ms", INSANA_COOLDOWN_BASE_MS))
            estado["debuff_fim_ms"] = tempo_atual + INSANA_DEBUFF_DASH_MS
            estado["penalidade_dash_pendente"] = True


def consumir_penalidade_dash_insana(estado):
    if not estado or not estado.get("penalidade_dash_pendente"):
        return False
    estado["penalidade_dash_pendente"] = False
    return True


def _carregar_sprites_eco(largura, altura):
    chave = (int(largura), int(altura))
    if chave in _SPRITES_ECO_CACHE:
        return _SPRITES_ECO_CACHE[chave]

    sprites = []
    for caminho in INSANA_SPRITES_ECO:
        try:
            img = pygame.image.load(caminho).convert_alpha()
            img = pygame.transform.smoothscale(img, chave)
        except Exception:
            img = pygame.Surface(chave, pygame.SRCALPHA)
            pygame.draw.ellipse(img, (150, 55, 220, 95), img.get_rect())
            pygame.draw.circle(img, (80, 255, 140, 150), (chave[0] // 2, chave[1] // 2), max(6, min(chave) // 4), 2)
        sprites.append(img)

    _SPRITES_ECO_CACHE[chave] = sprites
    return sprites


def _indice_sprite_eco(eco, tempo_atual, total_sprites):
    if total_sprites <= 1:
        return 0
    if eco.get("disparou_ms"):
        return total_sprites - 1

    criado_ms = int(eco.get("criado_ms", tempo_atual))
    disparar_ms = int(eco.get("disparar_ms", criado_ms + INSANA_DELAY_MS))
    duracao_preparo = max(1, disparar_ms - criado_ms)
    idade = max(0, min(duracao_preparo - 1, tempo_atual - criado_ms))
    return min(total_sprites - 1, int(idade * total_sprites / duracao_preparo))


def obter_alvo_eco_mais_proximo(estado, origem_x, origem_y, largura_player, altura_player):
    if not estado:
        return None

    ecos = estado.get("ecos") or []
    if not ecos:
        return None

    melhor_eco = None
    melhor_dist = None
    for eco in ecos:
        eco_cx = float(eco.get("x", 0.0)) + largura_player / 2
        eco_cy = float(eco.get("y", 0.0)) + altura_player / 2
        dist = (eco_cx - origem_x) ** 2 + (eco_cy - origem_y) ** 2
        if melhor_dist is None or dist < melhor_dist:
            melhor_dist = dist
            melhor_eco = eco

    if melhor_eco is None:
        return None
    return float(melhor_eco.get("x", 0.0)), float(melhor_eco.get("y", 0.0))


def obter_retangulo_alvo_inimigo(estado, origem_x, origem_y, pos_x_player, pos_y_player, largura_player, altura_player):
    alvo_eco = obter_alvo_eco_mais_proximo(estado, origem_x, origem_y, largura_player, altura_player)
    if alvo_eco is None:
        return (pos_x_player, pos_y_player, largura_player, altura_player)
    return (alvo_eco[0], alvo_eco[1], largura_player, altura_player)


def desenhar_insana(tela, estado, aurea, tempo_atual, x_player, y_player, largura_player, altura_player, config_graficos=None):
    if not _eh_insana(aurea) or not estado:
        return
    if config_graficos is not None and not config_graficos.get("efeitos_visuais", True):
        return

    ativo = estado.get("ativa")
    debuff = tempo_atual < estado.get("debuff_fim_ms", 0)
    pronto = tempo_atual >= estado.get("proximo_uso_ms", 0)
    if ativo or debuff or pronto:
        pulso = (math.sin(tempo_atual * 0.010) + 1.0) * 0.5
        margem = int(16 + pulso * 10)
        surf = pygame.Surface((int(largura_player + margem * 2), int(altura_player + margem * 2)), pygame.SRCALPHA)
        cor = (165, 60, 255, 95 if ativo else (60 if pronto else 42))
        pygame.draw.ellipse(surf, cor, surf.get_rect(), 3)
        pygame.draw.ellipse(surf, (80, 255, 140, 42), surf.get_rect().inflate(-12, -12), 2)
        tela.blit(surf, (x_player - margem, y_player - margem), special_flags=pygame.BLEND_RGBA_ADD)

    sprites = _carregar_sprites_eco(largura_player, altura_player)
    for eco in estado.get("ecos", []):
        idade = tempo_atual - eco.get("criado_ms", tempo_atual)
        alpha = 118
        if eco.get("disparou_ms"):
            alpha = max(0, int(118 * (1.0 - (tempo_atual - eco["disparou_ms"]) / 520.0)))
        else:
            alpha = int(92 + 55 * ((math.sin(tempo_atual * 0.024 + eco.get("fase_pulso", 0)) + 1.0) * 0.5))

        sprite = sprites[_indice_sprite_eco(eco, tempo_atual, len(sprites))].copy()
        if eco.get("virado_esquerda", math.cos(float(eco.get("angulo", 0.0))) < 0):
            sprite = pygame.transform.flip(sprite, True, False)
        sprite.set_alpha(alpha)
        jitter_x = int(math.sin(tempo_atual * 0.030 + eco["x"]) * 2)
        jitter_y = int(math.cos(tempo_atual * 0.025 + eco["y"]) * 2)
        x = int(eco["x"] + jitter_x)
        y = int(eco["y"] + jitter_y)

        raio = max(16, int(min(largura_player, altura_player) * 0.38))
        ring = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        pygame.draw.circle(ring, (165, 60, 255, min(135, alpha)), (raio, raio), raio, 2)
        pygame.draw.circle(ring, (80, 255, 140, min(80, alpha)), (raio, raio), max(4, raio // 2), 1)
        tela.blit(ring, (x + largura_player // 2 - raio, y + altura_player // 2 - raio), special_flags=pygame.BLEND_RGBA_ADD)
        tela.blit(sprite, (x, y))


def texto_status_insana(estado, tempo_atual):
    if not estado:
        return ""
    if estado.get("ativa"):
        return f"ECOS {estado.get('ecos_restantes', 0)}"
    restante = max(0, int((estado.get("proximo_uso_ms", 0) - tempo_atual) / 1000))
    if restante <= 0:
        return "INSANA PRONTA"
    return f"INSANA {restante}s"
