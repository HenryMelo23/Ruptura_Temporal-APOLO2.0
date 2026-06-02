"""Valores centrais de balanceamento do jogo.

Edite este arquivo para ajustar probabilidades, raridade, armadura e vida sem
precisar procurar numeros soltos nas fases.
"""

CARTAS_RARAS = {"Trembo", "Petro", "Poison", "Coletora", "Mercenaria"}

CHANCE_RARA_BASE = 0.01
CHANCE_RARA_MAXIMA = 0.08
SORTE_BASE = 0.01
SORTE_INCREMENTO_CARTA = 0.003
SORTE_PESO_RARIDADE = 0.45
SORTE_BONUS_RARIDADE_POR_CARTA = 0.0006

DROP_CARTA_BASE_INICIAL = 0.02
DROP_CARTA_BASE_MAXIMA = 0.40
DROP_CARTA_ESCALA_TEMPO_MS = 120 * 60 * 1000
DROP_CARTA_SORTE_FATOR = 0.25
DROP_CARTA_SORTE_TETO = 0.70

VIDA_INIMIGO_HARD_MULTIPLICADOR = 0.90
GANHO_VIDA_INIMIGO_HARD_MULTIPLICADOR = 0.84

BOSS_VIDA_MULTIPLICADOR = {
    1: 10.0,
    2: 12.0,
    3: 14.0,
    4: 16.0,
    5: 18.0,
}

BOSS_ARMADURA_BASE = {
    1: 0.62,
    2: 0.66,
    3: 0.69,
    4: 0.71,
    5: 0.74,
}

BOSS_ARMADURA_MAX = 0.90
BOSS_ARMADURA_POR_MINUTO = 0.002
BOSS_ARMADURA_POR_ABATE = 0.00008
BOSS_ARMADURA_POR_COLETORA = 0.004
BOSS_ARMADURA_EXTRA_VENENO = 0.10
BOSS_EXECUCAO_MULTIPLICADOR = 0.20
BOSS_EXECUCAO_MAX = 0.015

CURATER_CHANCE_SPAWN = 0.15
CURATER_CURA_PERCENTUAL_VIDA_PERDIDA = 0.20
CURATER_MULTIPLICADOR_VIDA = 2.4
CURATER_MITIGACAO_DANO = 0.42

CARTA_DANO_MULTIPLICADOR = 0.50
CARTA_CRITICO_DANO_BASE = 5
CARTA_CRITICO_DANO_POR_ESCALA = 2
CARTA_CRITICO_CHANCE_BASE = 0.02
CARTA_CRITICO_CHANCE_POR_ESCALA = 0.005

ANOMALIA_ESPREITADOR_SEG = 5 * 60
ANOMALIA_PROJETADOR_SEG = 7 * 60
ANOMALIA_CRISTALIZADOR_SEG = 9 * 60
ANOMALIA_AGLOMERADOR_SEG = 11 * 60
ANOMALIA_CURATER_SEG = 13 * 60

LIMITE_EXTRA_SEM_BOSS_INICIO_SEG = 20 * 60
LIMITE_EXTRA_SEM_BOSS_INTERVALO_SEG = 5 * 60


def _clamp(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def bonus_sorte(chance_sorte):
    return max(0.0, float(chance_sorte or 0.0) - SORTE_BASE)


def chance_com_sorte(chance_base, chance_sorte, fator=0.35, teto=0.95):
    return _clamp(float(chance_base) + bonus_sorte(chance_sorte) * fator, 0.0, teto)


def chance_carta_rara(chance_sorte, cartas_compradas=None):
    cartas_compradas = cartas_compradas or {}
    qtd_sorte = int(cartas_compradas.get("Sorte", 0) or 0)
    chance = (
        CHANCE_RARA_BASE
        + bonus_sorte(chance_sorte) * SORTE_PESO_RARIDADE
        + qtd_sorte * SORTE_BONUS_RARIDADE_POR_CARTA
    )
    return _clamp(chance, CHANCE_RARA_BASE, CHANCE_RARA_MAXIMA)


def chance_drop_carta_por_tempo(tempo_ms, chance_sorte):
    progresso = _clamp(float(tempo_ms or 0.0) / DROP_CARTA_ESCALA_TEMPO_MS, 0.0, 1.0)
    chance_base = DROP_CARTA_BASE_INICIAL + (DROP_CARTA_BASE_MAXIMA - DROP_CARTA_BASE_INICIAL) * progresso
    return chance_com_sorte(
        chance_base,
        chance_sorte,
        fator=DROP_CARTA_SORTE_FATOR,
        teto=DROP_CARTA_SORTE_TETO,
    )


def incremento_sorte_carta():
    return SORTE_INCREMENTO_CARTA


def incremento_carta_dano(inimigos_eliminados=0):
    return (27 + (max(0, int(inimigos_eliminados or 0)) // 50) * 10) * CARTA_DANO_MULTIPLICADOR


def incremento_dano_carta_critico(inimigos_eliminados=0):
    return CARTA_CRITICO_DANO_BASE + (max(0, int(inimigos_eliminados or 0)) // 100) * CARTA_CRITICO_DANO_POR_ESCALA


def incremento_chance_carta_critico(inimigos_eliminados=0):
    return CARTA_CRITICO_CHANCE_BASE + (max(0, int(inimigos_eliminados or 0)) // 100) * CARTA_CRITICO_CHANCE_POR_ESCALA


def vida_inicial_boss(boss_id, vida_base):
    return int(float(vida_base) * BOSS_VIDA_MULTIPLICADOR.get(int(boss_id), 3.0))


def limiar_execucao_boss(executa_inimigo):
    return min(float(executa_inimigo) * BOSS_EXECUCAO_MULTIPLICADOR, BOSS_EXECUCAO_MAX)


def dano_boss_mitigado(
    dano,
    boss_id,
    inimigos_eliminados=0,
    tempo_ms=0,
    coletora_nivel=0,
    tipo_dano="normal",
):
    armadura = BOSS_ARMADURA_BASE.get(int(boss_id), 0.50)
    armadura += max(0, int(inimigos_eliminados or 0)) * BOSS_ARMADURA_POR_ABATE
    armadura += max(0.0, float(tempo_ms or 0.0)) / 60000.0 * BOSS_ARMADURA_POR_MINUTO
    armadura += max(0, int(coletora_nivel or 0)) * BOSS_ARMADURA_POR_COLETORA
    if tipo_dano == "veneno":
        armadura += BOSS_ARMADURA_EXTRA_VENENO
    armadura = _clamp(armadura, 0.0, BOSS_ARMADURA_MAX)
    return max(1, float(dano) * (1.0 - armadura))


def bonus_limite_inimigos_sem_boss(tempo_decorrido_seg, boss_chamado):
    if boss_chamado or tempo_decorrido_seg < LIMITE_EXTRA_SEM_BOSS_INICIO_SEG:
        return 0
    tempo_extra = tempo_decorrido_seg - LIMITE_EXTRA_SEM_BOSS_INICIO_SEG
    return 1 + int(tempo_extra // LIMITE_EXTRA_SEM_BOSS_INTERVALO_SEG)
