"""Contrato unico do estado persistente do jogador entre as fases."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, MutableMapping


CAMINHO_ESTADO_JOGADOR = Path("saves/atributos.json")
VERSAO_ESTADO_JOGADOR = 1

# chave no JSON -> nome usado pelos GAME*.py
CAMPOS_JOGADOR = {
    "velocidade_personagem": "velocidade_personagem",
    "intervalo_disparo": "intervalo_disparo",
    "dano_person_hit": "dano_person_hit",
    "chance_critico": "chance_critico",
    "roubo_de_vida": "roubo_de_vida",
    "quantidade_roubo_vida": "quantidade_roubo_vida",
    "vida_petro": "vida_petro",
    "vida_maxima_personagem": "vida_maxima",
    "vida_maxima_petro": "vida_maxima_petro",
    "vida_atual_personagem": "vida",
    "nivel_Petro": "xp_petro",
    "existencia_petro": "Petro_active",
    "existencia_trembo": "trembo",
    "dano_petro": "dano_petro",
    "resistencia_personagem": "Resistencia",
    "resistencia_petro": "Resistencia_petro",
    "dano_inimigo_longe": "dano_inimigo_longe",
    "dano_inimigo_perto": "dano_inimigo_perto",
    "Poison_Active": "Poison_Active",
    "Ultimo_Estalo": "Ultimo_Estalo",
    "Executa_inimigo": "Executa_inimigo",
    "Mercenaria_Active": "Mercenaria_Active",
    "Valor_Bonus": "Valor_Bonus",
    "tempo_cooldown_dash": "tempo_cooldown_dash",
    "petro_evolucao": "petro_evolucao",
    "Dano_Veneno_Acumulado": "Dano_Veneno_Acumulado",
    "Tempo_cura": "Tempo_cura",
    "porcentagem_cura": "porcentagem_cura",
    "moedas_totais": "moedas_totais",
    "Chance_Sorte": "Chance_Sorte",
    "cartas_compradas": "cartas_compradas",
    "largura_disparo": "largura_disparo",
    "altura_disparo": "altura_disparo",
}


def _estado_serializavel(estado: MutableMapping[str, Any]) -> dict[str, Any]:
    ausentes = [nome for nome in CAMPOS_JOGADOR.values() if nome not in estado]
    if ausentes:
        raise RuntimeError(
            "Estado do jogador incompleto antes da transicao: " + ", ".join(ausentes)
        )

    dados = {chave: estado[nome] for chave, nome in CAMPOS_JOGADOR.items()}
    dados["_versao_transicao"] = VERSAO_ESTADO_JOGADOR
    return dados


def salvar_estado_jogador(
    estado: MutableMapping[str, Any],
    caminho: os.PathLike[str] | str = CAMINHO_ESTADO_JOGADOR,
) -> None:
    """Salva de modo atomico para uma fase nunca ler um JSON pela metade."""
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(destino.suffix + ".tmp")
    dados = _estado_serializavel(estado)
    with temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False)
        arquivo.flush()
        os.fsync(arquivo.fileno())
    os.replace(temporario, destino)


def carregar_estado_jogador(
    estado: MutableMapping[str, Any],
    caminho: os.PathLike[str] | str = CAMINHO_ESTADO_JOGADOR,
) -> bool:
    """Aplica somente campos conhecidos; save ausente/corrompido mantem os padroes."""
    origem = Path(caminho)
    if not origem.exists():
        return False

    try:
        with origem.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False

    if not isinstance(dados, dict):
        return False

    for chave, nome in CAMPOS_JOGADOR.items():
        if chave in dados:
            estado[nome] = dados[chave]

    # Invariantes que impedem divisao por zero e dimensoes invalidas na nova fase.
    for nome in ("vida_maxima", "vida_maxima_petro", "intervalo_disparo", "largura_disparo", "altura_disparo"):
        valor = estado.get(nome)
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            estado[nome] = max(1, valor)

    vida_maxima = estado.get("vida_maxima")
    vida = estado.get("vida")
    if isinstance(vida_maxima, (int, float)) and isinstance(vida, (int, float)):
        estado["vida"] = min(max(0, vida), vida_maxima)
    return True

