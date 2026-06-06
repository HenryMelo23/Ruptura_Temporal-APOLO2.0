# -*- coding: utf-8 -*-
import json
import os

import Caminhos  # Instala o redirecionamento do Cofre Dimensional para saves/*.json.


MANIFESTACAO_PADRAO = "eletrica"
CAMINHO_MANIFESTACAO_SELECIONADA = "saves/manifestacao_selecionada.json"


MANIFESTACOES_DADOS = {
    "eletrica": {
        "nome": "Manifestação Elétrica",
        "icone": "Sprites/manifestacao_eletrica.png",
        "estado": "dominada",
        "funcao": "Disparo padrão equilibrado.",
        "descricao_curta": (
            "A primeira forma que Geovana aprendeu a dar à Ruptura: energia "
            "elétrica instável disparada pelas mãos."
        ),
        "disparo": (
            "Projétil elétrico em linha reta, com preparo visual, rastro ciano "
            "e explosão de faíscas no impacto."
        ),
        "habilidade": "Onda Cinética",
        "descricao_habilidade": (
            "Libera uma onda de choque que empurra Geovana para trás, causa dano "
            "em área e espalha corrente elétrica entre inimigos próximos."
        ),
        "traco": "Confiável contra qualquer tipo de inimigo.",
        "risco": "Não possui especialização extrema.",
        "desbloqueada": True,
        "ativa": True,
        "cor": (0, 225, 255),
        "cor_secundaria": (128, 90, 255),
    },
    "lacerante": {
        "nome": "Manifestação Lacerante",
        "icone": "Sprites/manifestacao_lacerante.png",
        "estado": "dominada",
        "funcao": "Agressiva de médio alcance, feita para cortar hordas alinhadas e elites móveis.",
        "descricao_curta": (
            "Geovana não dispara energia. Ela rasga o espaço entre ela e o alvo "
            "com cortes temporais saindo das mãos."
        ),
        "disparo": (
            "Corte de Ruptura: lâmina curta, alcance menor, dano maior, atravessa "
            "inimigos em linha e aplica Laceração. Com 3 acúmulos, o inimigo fica Aberto."
        ),
        "habilidade": "Fenda Carnívora",
        "descricao_habilidade": (
            "Fissura vermelha em linha reta. Após breve aviso, explode em cortes; "
            "lacerados sofrem dano extra e perdem os acúmulos."
        ),
        "traco": (
            "Lacerados sofrem dano extra ao se mover ou atacar. Sinergias: Profética, Insana e Voraz."
        ),
        "risco": "Menor alcance, exige posicionamento e perde valor contra boss parado ou recuo constante.",
        "frase": "Geovana aprendeu que nem toda energia precisa viajar. Algumas apenas abrem caminho à força.",
        "desbloqueada": True,
        "ativa": True,
        "cor": (255, 54, 72),
        "cor_secundaria": (255, 150, 170),
    },
    "eco_grav": {
        "nome": "Eco não estabilizado",
        "estado": "bloqueada",
        "funcao": "Forma futura.",
        "descricao_curta": "Manifestação ainda sem contorno estável.",
        "disparo": "Sinal incompleto.",
        "habilidade": "Indefinida",
        "descricao_habilidade": "Eco ainda não dominado.",
        "traco": "Aguardando domínio.",
        "risco": "Instável demais para combate.",
        "desbloqueada": False,
        "ativa": False,
        "cor": (255, 120, 92),
        "cor_secundaria": (255, 200, 120),
    },
    "eco_vazio": {
        "nome": "Eco não estabilizado",
        "estado": "bloqueada",
        "funcao": "Forma futura.",
        "descricao_curta": "A Ruptura responde, mas a técnica ainda não obedece.",
        "disparo": "Sinal incompleto.",
        "habilidade": "Indefinida",
        "descricao_habilidade": "Eco ainda não dominado.",
        "traco": "Aguardando domínio.",
        "risco": "Instável demais para combate.",
        "desbloqueada": False,
        "ativa": False,
        "cor": (165, 110, 255),
        "cor_secundaria": (80, 220, 255),
    },
    "eco_quinto": {
        "nome": "Eco não estabilizado",
        "estado": "bloqueada",
        "funcao": "Forma futura.",
        "descricao_curta": "Um contorno distante de poder, ainda sem técnica.",
        "disparo": "Sinal incompleto.",
        "habilidade": "Indefinida",
        "descricao_habilidade": "Eco ainda não dominado.",
        "traco": "Aguardando domínio.",
        "risco": "Instável demais para combate.",
        "desbloqueada": False,
        "ativa": False,
        "cor": (115, 255, 180),
        "cor_secundaria": (90, 160, 255),
    },
    "eco_sexto": {
        "nome": "Eco não estabilizado",
        "estado": "bloqueada",
        "funcao": "Forma futura.",
        "descricao_curta": "Um espaço reservado para uma nova manifestação.",
        "disparo": "Sinal incompleto.",
        "habilidade": "Indefinida",
        "descricao_habilidade": "Eco ainda não dominado.",
        "traco": "Aguardando domínio.",
        "risco": "Instável demais para combate.",
        "desbloqueada": False,
        "ativa": False,
        "cor": (140, 150, 170),
        "cor_secundaria": (70, 80, 100),
    },
}


ORDEM_MANIFESTACOES = ["eletrica", "lacerante", "eco_grav", "eco_vazio", "eco_quinto"]


def obter_manifestacoes():
    return [(chave, MANIFESTACOES_DADOS[chave]) for chave in ORDEM_MANIFESTACOES]


def salvar_manifestacao_ativa(chave):
    if chave not in MANIFESTACOES_DADOS:
        chave = MANIFESTACAO_PADRAO

    os.makedirs("saves", exist_ok=True)
    with open(CAMINHO_MANIFESTACAO_SELECIONADA, "w", encoding="utf-8") as arquivo:
        json.dump({"manifestacao_ativa": chave}, arquivo, ensure_ascii=False, indent=4)
    return chave


def obter_manifestacao_ativa():
    try:
        with open(CAMINHO_MANIFESTACAO_SELECIONADA, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        chave = dados.get("manifestacao_ativa", MANIFESTACAO_PADRAO)
    except Exception:
        chave = MANIFESTACAO_PADRAO

    if chave not in MANIFESTACOES_DADOS:
        chave = MANIFESTACAO_PADRAO
    return chave


def obter_dados_manifestacao_ativa():
    chave = obter_manifestacao_ativa()
    return chave, MANIFESTACOES_DADOS[chave]
