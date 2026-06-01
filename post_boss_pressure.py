# -*- coding: utf-8 -*-
import math


def criar_estado_pressao_pos_boss():
    return {
        "ativo": False,
        "inicio_ms": 0,
        "kills_inicio": 0,
    }


def calcular_pressao_spawn_pos_boss(
    estado,
    agora_ms,
    boss_finalizado,
    inimigos_vivos,
    inimigos_eliminados,
    limite_base,
    intervalo_base_ms=1000,
    limite_extra=28,
):
    if not boss_finalizado:
        estado["ativo"] = False
        return {
            "ativo": False,
            "limite": limite_base,
            "intervalo_ms": intervalo_base_ms,
            "lote": 1 if inimigos_vivos < limite_base else 0,
        }

    if not estado["ativo"]:
        estado["ativo"] = True
        estado["inicio_ms"] = agora_ms
        estado["kills_inicio"] = inimigos_eliminados

    segundos = max(0.0, (agora_ms - estado["inicio_ms"]) / 1000.0)
    kills_pos_boss = max(0, inimigos_eliminados - estado["kills_inicio"])

    pressao_tempo = 1.095 ** min(70.0, segundos / 2.5)
    pressao_kills = 1.045 ** min(120, kills_pos_boss)
    pressao = min(7.5, pressao_tempo * pressao_kills)

    limite_seguro = max(limite_base, limite_base + limite_extra)
    limite = min(limite_seguro, max(limite_base, int(math.ceil(limite_base * pressao))))
    intervalo_ms = max(180, int(intervalo_base_ms / max(1.0, pressao * 0.85)))
    lote = max(1, min(5, int(1 + pressao // 1.7)))

    if inimigos_vivos >= limite:
        lote = 0
    else:
        lote = min(lote, limite - inimigos_vivos)

    return {
        "ativo": True,
        "limite": limite,
        "intervalo_ms": intervalo_ms,
        "lote": lote,
    }
