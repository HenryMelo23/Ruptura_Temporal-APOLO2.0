# -*- coding: utf-8 -*-
"""Trajetoria compartilhada para empurroes e puxoes de inimigos."""
import math

import pygame


PAUSA_CHEGADA_MS = 800


def _bezier(estado, t):
    t = max(0.0, min(1.0, float(t)))
    inv = 1.0 - t
    x = inv * inv * estado["origem_x"] + 2 * inv * t * estado["controle_x"] + t * t * estado["destino_x"]
    y = inv * inv * estado["origem_y"] + 2 * inv * t * estado["controle_y"] + t * t * estado["destino_y"]
    return x, y


def agendar_deslocamento(inimigo, destino_x, destino_y, agora_ms=None, duracao_ms=None, pausa_ms=PAUSA_CHEGADA_MS, curvatura=0.16):
    rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
    if rect is None:
        return False
    agora_ms = pygame.time.get_ticks() if agora_ms is None else int(agora_ms)
    origem_x, origem_y = float(rect.x), float(rect.y)
    destino_x, destino_y = float(destino_x), float(destino_y)
    palco = pygame.display.get_surface()
    if palco is not None:
        largura, altura = palco.get_size()
        destino_x = max(0.0, min(float(largura - rect.width), destino_x))
        destino_y = max(0.0, min(float(altura - rect.height), destino_y))
    distancia = math.hypot(destino_x - origem_x, destino_y - origem_y)
    if distancia < 1.0:
        return False
    duracao_ms = int(duracao_ms or max(240, min(520, 210 + distancia * 1.35)))
    dx, dy = destino_x - origem_x, destino_y - origem_y
    nx, ny = -dy / distancia, dx / distancia
    lado = -1.0 if id(inimigo) % 2 else 1.0
    arco = min(54.0, distancia * abs(float(curvatura))) * lado
    estado = {
        "origem_x": origem_x,
        "origem_y": origem_y,
        "controle_x": (origem_x + destino_x) * 0.5 + nx * arco,
        "controle_y": (origem_y + destino_y) * 0.5 + ny * arco,
        "destino_x": destino_x,
        "destino_y": destino_y,
        "inicio_ms": agora_ms,
        "fim_ms": agora_ms + duracao_ms,
        "duracao_ms": duracao_ms,
        "pausa_ms": int(pausa_ms),
        "fase": "trajetoria",
    }
    inimigo["ruptura_deslocamento"] = estado
    inimigo["pos_x"], inimigo["pos_y"] = origem_x, origem_y
    return True


def atualizar_deslocamento(inimigo, agora_ms=None):
    estado = inimigo.get("ruptura_deslocamento") if isinstance(inimigo, dict) else None
    if not estado:
        return False
    rect = inimigo.get("rect")
    if rect is None:
        inimigo.pop("ruptura_deslocamento", None)
        return False
    agora_ms = pygame.time.get_ticks() if agora_ms is None else int(agora_ms)
    if estado.get("fase") == "pausa":
        rect.x, rect.y = int(estado["destino_x"]), int(estado["destino_y"])
        inimigo["pos_x"], inimigo["pos_y"] = float(rect.x), float(rect.y)
        if agora_ms >= int(estado.get("pausa_fim_ms", agora_ms)):
            inimigo.pop("ruptura_deslocamento", None)
            return False
        return True

    duracao = max(1, int(estado.get("duracao_ms", 1)))
    linear = max(0.0, min(1.0, (agora_ms - int(estado["inicio_ms"])) / float(duracao)))
    suave = linear * linear * (3.0 - 2.0 * linear)
    x, y = _bezier(estado, suave)
    rect.x, rect.y = int(x), int(y)
    inimigo["pos_x"], inimigo["pos_y"] = float(x), float(y)
    if linear >= 1.0:
        estado["fase"] = "pausa"
        estado["chegada_ms"] = agora_ms
        estado["pausa_fim_ms"] = agora_ms + int(estado.get("pausa_ms", PAUSA_CHEGADA_MS))
        inimigo["ruptura_raiz_fim"] = max(int(inimigo.get("ruptura_raiz_fim", 0)), estado["pausa_fim_ms"])
    return True


def amostrar_trajetoria(estado, quantidade=18):
    if not estado:
        return []
    return [_bezier(estado, i / float(max(1, quantidade - 1))) for i in range(quantidade)]


def progresso_deslocamento(estado, agora_ms=None):
    if not estado:
        return 0.0
    if estado.get("fase") == "pausa":
        return 1.0
    agora_ms = pygame.time.get_ticks() if agora_ms is None else int(agora_ms)
    return max(0.0, min(1.0, (agora_ms - int(estado.get("inicio_ms", agora_ms))) / float(max(1, int(estado.get("duracao_ms", 1))))))
