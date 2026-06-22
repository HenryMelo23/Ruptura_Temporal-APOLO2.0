"""Valores centrais de balanceamento do jogo.

Edite este arquivo para ajustar probabilidades, raridade, armadura e vida sem
precisar procurar numeros soltos nas fases.
"""

CARTAS_RARAS = {"Trembo", "Petro", "Poison", "Coletora", "Mercenaria"}

CHANCE_RARA_BASE = 0.0
CHANCE_RARA_MAXIMA = 0.08
SORTE_BASE = 0.0
SORTE_INCREMENTO_CARTA = 0.0035
SORTE_PESO_RARIDADE = 0.45
SORTE_BONUS_RARIDADE_POR_CARTA = 0.0006

DROP_CARTA_BASE_INICIAL = 0.045
DROP_CARTA_BASE_MAXIMA = 0.40
DROP_CARTA_ESCALA_TEMPO_MS = 120 * 60 * 1000
DROP_CARTA_SORTE_FATOR = 0.25
DROP_CARTA_SORTE_TETO = 0.70
DROP_CARTA_CERTEIRO_BASE_MS = 45 * 1000
DROP_CARTA_CERTEIRO_MAX_MS = 3 * 60 * 1000
DROP_CARTA_ASSISTENCIA_INICIO_ABATES = 55
DROP_CARTA_ASSISTENCIA_INICIO_TEMPO_MS = 8 * 60 * 1000
DROP_CARTA_ASSISTENCIA_INICIO_BONUS = 0.060
DROP_CARTA_TETO_INICIO = 0.22

VIDA_INIMIGO_HARD_MULTIPLICADOR = 0.90
GANHO_VIDA_INIMIGO_HARD_MULTIPLICADOR = 0.84

BOSS_VIDA_MULTIPLICADOR = {
    1: 9.3,
    2: 11.2,
    3: 13.0,
    4: 14.8,
    5: 16.7,
}

BOSS_ARMADURA_BASE = {
    1: 0.50,
    2: 0.66,
    3: 0.69,
    4: 0.71,
    5: 0.74,
}

BOSS_ARMADURA_MAX = 0.88
BOSS_ARMADURA_POR_MINUTO = 0.0016
BOSS_ARMADURA_POR_ABATE = 0.00006
BOSS_ARMADURA_POR_COLETORA = 0.004
BOSS_ARMADURA_EXTRA_VENENO = 0.10
BOSS_EXECUCAO_MULTIPLICADOR = 0.20
BOSS_EXECUCAO_MAX = 0.015
BOSS_GANHO_PROGRESSAO_MULTIPLICADOR = 0.85

CURATER_CHANCE_SPAWN = 0.20
CURATER_CURA_PERCENTUAL_VIDA_PERDIDA = 0.20
CURATER_ORBE_CURA_VIDA_PERDIDA = 0.20
CURATER_ORBE_DURACAO_MS = 12000
CURATER_ORBE_RAIO_COLETA = 52
CURATER_MULTIPLICADOR_VIDA = 2.4
CURATER_MITIGACAO_DANO = 0.42
CURATER_CURA_ABATE_VIDA_PERDIDA = 0.50

DANO_INIMIGO_INICIO_MULTIPLICADOR = 0.55
DANO_INIMIGO_ALIVIO_ATE_SEG = 8 * 60
DANO_INIMIGO_NORMALIZA_ATE_SEG = 12 * 60

CARTA_DANO_PERCENTUAL = 0.18
CARTA_DANO_PERCENTUAL_ESCALA_MAX = 0.04
CARTA_DANO_PERCENTUAL_POR_250_ABATES = 0.002
CARTA_DANO_BASE = CARTA_DANO_PERCENTUAL
CARTA_DANO_POR_50_ABATES = 0
CARTA_DANO_ESCALA_TARDIA_INICIO = 0
CARTA_DANO_ESCALA_TARDIA_EXTRA = 0
CARTA_VELOCIDADE_BASE = 0.090
CARTA_VELOCIDADE_POR_50_ABATES = 0.0
CARTA_SPEED_ATTACK_BASE_MS = 46
CARTA_SPEED_ATTACK_POR_100_ABATES_MS = 0
CARTA_SPEED_ATTACK_INTERVALO_MIN_MS = 60
CARTA_CRITICO_DANO_BASE = 9
CARTA_CRITICO_DANO_POR_ESCALA = 0
CARTA_CRITICO_CHANCE_BASE = 0.027
CARTA_CRITICO_CHANCE_POR_ESCALA = 0.0
CARTA_TELEPORTE_REDUCAO_MS = 400
CARTA_TELEPORTE_INTERVALO_MIN_MS = 500

ANOMALIA_ESPREITADOR_SEG = 2 * 60
ANOMALIA_PROJETADOR_SEG = 5 * 60
ANOMALIA_CRISTALIZADOR_SEG = 7 * 60
ANOMALIA_AGLOMERADOR_SEG = 9 * 60
ANOMALIA_CURATER_SEG = 18 * 60

PONTOS_TEMPO_BONUS_POR_MINUTO = 0.09
PONTOS_TEMPO_MULTIPLICADOR_MAX = 3.50
PONTOS_MULTIPLICADOR_TIPO_INIMIGO = {
    2: 1.60,          # Aglomerador
    3: 1.25,          # Espreitador
    4: 1.45,          # Cristalizador
    5: 1.35,          # Projetador
    "curater": 1.80,
}

LIMITE_EXTRA_NORMAL_QUEBRA_SEG = 18 * 60
LIMITE_EXTRA_NORMAL_ABATES_POR_INIMIGO = 15
LIMITE_EXTRA_DIFICIL_QUEBRA_SEG = 6 * 60
LIMITE_EXTRA_DIFICIL_ABATES_POR_INIMIGO = 20
LIMITE_EXTRA_ABATES_MARCO_SEG = LIMITE_EXTRA_NORMAL_QUEBRA_SEG
LIMITE_EXTRA_QUEBRA_SEG = LIMITE_EXTRA_NORMAL_QUEBRA_SEG
LIMITE_EXTRA_ABATES_POR_INIMIGO = LIMITE_EXTRA_NORMAL_ABATES_POR_INIMIGO

LOJA_FORCADA_INTERVALO_SEG = 5 * 60
LOJA_FORCADA_AVISO_SEG = 15
LOJA_FORCADA_CARTAS_MINIMAS = 5


def _clamp(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def limitar_dano_larapio(dano_calculado, vida_atual, vida_maxima, teto_percentual=0.18):
    """Limita o golpe do ladrao e garante que ele nunca seja a fonte do abate."""
    dano = max(0, int(dano_calculado or 0))
    teto = max(1, int(max(1, vida_maxima) * teto_percentual))
    limite_nao_letal = max(0, int(vida_atual) - 1)
    return min(dano, teto, limite_nao_letal)


def bonus_sorte(chance_sorte):
    return max(0.0, float(chance_sorte or 0.0) - SORTE_BASE)


def chance_com_sorte(chance_base, chance_sorte, fator=0.35, teto=0.95):
    return _clamp(float(chance_base) + bonus_sorte(chance_sorte) * fator, 0.0, teto)


def chance_carta_rara(chance_sorte, cartas_compradas=None):
    cartas_compradas = cartas_compradas or {}
    sorte = float(chance_sorte or 0.0)
    if sorte <= 0.0:
        return 0.0
    qtd_sorte = int(cartas_compradas.get("Sorte", 0) or 0)
    chance = (
        CHANCE_RARA_BASE
        + bonus_sorte(sorte) * SORTE_PESO_RARIDADE
        + qtd_sorte * SORTE_BONUS_RARIDADE_POR_CARTA
    )
    if chance <= 0.0:
        return 0.0
    return _clamp(chance, 0.0, CHANCE_RARA_MAXIMA)


def multiplicador_dano_inimigo_por_tempo(tempo_decorrido_seg):
    tempo = max(0.0, float(tempo_decorrido_seg or 0.0))
    if tempo <= DANO_INIMIGO_ALIVIO_ATE_SEG:
        return DANO_INIMIGO_INICIO_MULTIPLICADOR
    janela = max(1.0, DANO_INIMIGO_NORMALIZA_ATE_SEG - DANO_INIMIGO_ALIVIO_ATE_SEG)
    progresso = _clamp((tempo - DANO_INIMIGO_ALIVIO_ATE_SEG) / janela, 0.0, 1.0)
    return DANO_INIMIGO_INICIO_MULTIPLICADOR + (1.0 - DANO_INIMIGO_INICIO_MULTIPLICADOR) * progresso


def chance_drop_carta_por_tempo(tempo_ms, chance_sorte, inimigos_eliminados=0):
    progresso = _clamp(float(tempo_ms or 0.0) / DROP_CARTA_ESCALA_TEMPO_MS, 0.0, 1.0)
    chance_base = DROP_CARTA_BASE_INICIAL + (DROP_CARTA_BASE_MAXIMA - DROP_CARTA_BASE_INICIAL) * progresso

    progresso_abates = _clamp(
        float(max(0, int(inimigos_eliminados or 0))) / DROP_CARTA_ASSISTENCIA_INICIO_ABATES,
        0.0,
        1.0,
    )
    progresso_tempo_inicio = _clamp(float(tempo_ms or 0.0) / DROP_CARTA_ASSISTENCIA_INICIO_TEMPO_MS, 0.0, 1.0)
    intensidade_inicio = 1.0 - max(progresso_abates, progresso_tempo_inicio)
    chance_base += DROP_CARTA_ASSISTENCIA_INICIO_BONUS * intensidade_inicio

    chance = chance_com_sorte(
        chance_base,
        chance_sorte,
        fator=DROP_CARTA_SORTE_FATOR,
        teto=DROP_CARTA_SORTE_TETO,
    )
    if intensidade_inicio > 0:
        teto_inicio = DROP_CARTA_TETO_INICIO + (DROP_CARTA_SORTE_TETO - DROP_CARTA_TETO_INICIO) * (1.0 - intensidade_inicio)
        chance = min(chance, teto_inicio)
    return chance


def intervalo_drop_certeiro_ms(chance_drop):
    progresso = _clamp(
        (float(chance_drop or 0.0) - DROP_CARTA_BASE_INICIAL)
        / (DROP_CARTA_SORTE_TETO - DROP_CARTA_BASE_INICIAL),
        0.0,
        1.0,
    )
    return int(
        DROP_CARTA_CERTEIRO_BASE_MS
        + (DROP_CARTA_CERTEIRO_MAX_MS - DROP_CARTA_CERTEIRO_BASE_MS) * progresso
    )


def incremento_sorte_carta():
    return SORTE_INCREMENTO_CARTA


def percentual_carta_dano(inimigos_eliminados=0):
    bonus_abates = (max(0, int(inimigos_eliminados or 0)) // 250) * CARTA_DANO_PERCENTUAL_POR_250_ABATES
    return CARTA_DANO_PERCENTUAL + min(CARTA_DANO_PERCENTUAL_ESCALA_MAX, bonus_abates)


def aplicar_incremento_carta_dano(dano_atual, inimigos_eliminados=0):
    try:
        dano_base = float(dano_atual)
    except (TypeError, ValueError):
        dano_base = 0.0
    return max(1.0, dano_base * (1.0 + percentual_carta_dano(inimigos_eliminados)))


def incremento_carta_dano(inimigos_eliminados=0):
    return percentual_carta_dano(inimigos_eliminados)


def incremento_carta_velocidade_movimento(inimigos_eliminados=0):
    return CARTA_VELOCIDADE_BASE


def reducao_intervalo_carta_speed_attack(inimigos_eliminados=0):
    return CARTA_SPEED_ATTACK_BASE_MS


def intervalo_minimo_speed_attack():
    return CARTA_SPEED_ATTACK_INTERVALO_MIN_MS


def incremento_dano_carta_critico(inimigos_eliminados=0):
    return CARTA_CRITICO_DANO_BASE


def incremento_chance_carta_critico(inimigos_eliminados=0):
    return CARTA_CRITICO_CHANCE_BASE


def reducao_cooldown_carta_teleporte(tempo_cooldown_dash):
    try:
        tempo_atual = float(tempo_cooldown_dash)
    except (TypeError, ValueError):
        tempo_atual = CARTA_TELEPORTE_INTERVALO_MIN_MS
    return max(CARTA_TELEPORTE_INTERVALO_MIN_MS, tempo_atual - CARTA_TELEPORTE_REDUCAO_MS)


def vida_inicial_boss(boss_id, vida_base):
    return int(float(vida_base) * BOSS_VIDA_MULTIPLICADOR.get(int(boss_id), 1.8))


def ganho_progressao_boss(valor):
    return float(valor) * BOSS_GANHO_PROGRESSAO_MULTIPLICADOR


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


def multiplicador_pontos_por_tempo(tempo_decorrido_seg):
    minutos = max(0.0, float(tempo_decorrido_seg or 0.0)) / 60.0
    multiplicador = 1.0 + minutos * PONTOS_TEMPO_BONUS_POR_MINUTO
    return _clamp(multiplicador, 1.0, PONTOS_TEMPO_MULTIPLICADOR_MAX)


def multiplicador_pontos_por_tipo_inimigo(tipo_inimigo):
    return max(1.0, float(PONTOS_MULTIPLICADOR_TIPO_INIMIGO.get(tipo_inimigo, 1.0)))


def pontos_inimigo_por_tempo(pontos_base, tempo_decorrido_seg, tipo_inimigo=1):
    pontos_base = max(0, int(pontos_base or 0))
    if pontos_base <= 0:
        return 0
    multiplicador = (
        multiplicador_pontos_por_tempo(tempo_decorrido_seg)
        * multiplicador_pontos_por_tipo_inimigo(tipo_inimigo)
    )
    return max(pontos_base, int(round(pontos_base * multiplicador)))


def bonus_limite_inimigos_sem_boss(
    tempo_decorrido_seg,
    boss_chamado,
    inimigos_eliminados=0,
    inimigos_eliminados_no_marco=None,
    modo_dificil=None,
):
    if modo_dificil is None:
        try:
            import Variaveis
            modo_dificil = Variaveis.obter_modo_cartas() == "drops"
        except Exception:
            modo_dificil = False

    inicio_seg = LIMITE_EXTRA_DIFICIL_QUEBRA_SEG if modo_dificil else LIMITE_EXTRA_NORMAL_QUEBRA_SEG
    abates_por_inimigo = (
        LIMITE_EXTRA_DIFICIL_ABATES_POR_INIMIGO
        if modo_dificil
        else LIMITE_EXTRA_NORMAL_ABATES_POR_INIMIGO
    )

    if boss_chamado or tempo_decorrido_seg < inicio_seg:
        return 0
    if inimigos_eliminados_no_marco is None:
        inimigos_eliminados_no_marco = 0
    abates_apos_marco = max(0, int(inimigos_eliminados or 0) - int(inimigos_eliminados_no_marco or 0))
    return abates_apos_marco // abates_por_inimigo


# Balanceamento da Manifestação Retornante
RETORNANTE_ATTACK_SPEED_MULTIPLIER = 1.45
