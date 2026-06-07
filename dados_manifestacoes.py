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
        "estado": "encontrado",
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
        "estado": "encontrado",
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
    "prismatica": {
        "nome": "Manifestação Prismática",
        "icone": "Sprites/manifestacao_prismatica.png",
        "estado": "encontrado",
        "funcao": "Técnica de precisão que recompensa ângulo, preparo e geometria.",
        "descricao_curta": (
            "Geovana aprende a fragmentar energia em feixes de luz instável. "
            "Cada disparo é menos bruto, mas muito mais inteligente no espaço."
        ),
        "disparo": (
            "Feixe Prismático: tiro fino, veloz e de dano base menor. Ricocheteia "
            "uma vez em parede ou inimigo marcado; após ricochetear ganha dano e, "
            "se voltar ao mesmo alvo, causa crítico prismático."
        ),
        "habilidade": "Prisma de Refração",
        "descricao_habilidade": (
            "Cria um pequeno prisma no cursor por alguns segundos. Disparos que "
            "atravessam o prisma se dividem em 3 feixes menores. Inimigos que "
            "tocam o prisma recebem dano leve e quebram a estrutura."
        ),
        "traco": "Excelente contra chefes previsíveis, paredes úteis e jogadores que calculam ângulos.",
        "risco": "Dano direto menor; depende de mira, posicionamento e preparação do campo.",
        "frase": "Geovana descobriu que a Ruptura também obedece à luz quando o ângulo está certo.",
        "desbloqueada": True,
        "ativa": True,
        "cor": (70, 245, 255),
        "cor_secundaria": (255, 115, 185),
    },
    "retornante": {
        "nome": "Manifestação Retornante",
        "icone": "Sprites/manifestacao_retornante.png",
        "estado": "encontrado",
        "funcao": "Técnica de retorno: o dano real acontece quando o disparo volta para Geovana.",
        "descricao_curta": (
            "Geovana aprende a lançar energia que não termina no impacto. "
            "O pulso atravessa o campo, reconhece a distância e retorna como uma lâmina puxada de volta."
        ),
        "disparo": (
            "Pulso Retornante: na ida causa dano baixo e atravessa inimigos. "
            "Na volta causa dano alto, aplica bônus de retorno e pode critar quando atravessa o alvo pelas costas."
        ),
        "habilidade": "Chamado Reverso",
        "descricao_habilidade": (
            "Marca todos os projéteis retornantes ativos e força o retorno imediato. "
            "Projéteis chamados voltam com dano aumentado."
        ),
        "traco": "Excelente para kiting e posicionamento: o jogador quer colocar inimigos entre Geovana e o pulso voltando.",
        "risco": "Se Geovana fica parada ou mal posicionada, metade do dano da manifestação se perde.",
        "frase": "Geovana não mira onde o inimigo está. Ela caminha para onde a volta vai cortar.",
        "desbloqueada": True,
        "ativa": True,
        "cor": (145, 95, 255),
        "cor_secundaria": (255, 95, 175),
    },
    "parasitica": {
        "nome": "Manifestação Parasítica",
        "icone": "Sprites/manifestacao_parasitica.png",
        "estado": "encontrado",
        "funcao": "Manifestação de preparação: planta energia em inimigos e colhe explosões no momento certo.",
        "descricao_curta": (
            "Geovana usa o corpo dos inimigos como catalisador, implantando sementes "
            "dimensionais que crescem com aproximação, agressão e novos acertos."
        ),
        "disparo": (
            "Semente Parasítica: causa pouco dano inicial e implanta uma semente. "
            "Acertar o mesmo alvo fortalece a infecção; inimigos agrupados ou atacando aceleram a maturação."
        ),
        "habilidade": "Eclosão",
        "descricao_habilidade": (
            "Força todas as sementes ativas a explodirem imediatamente. Sementes maduras "
            "causam dano alto em área e espalham novas sementes menores; imaturas causam dano baixo."
        ),
        "traco": "Ideal para infectar alvos certos, controlar hordas e esperar o melhor momento de colher.",
        "risco": "Dano imediato baixo; perde valor contra inimigos que morrem antes da semente crescer.",
        "frase": "Geovana não destrói o inimigo de fora. Ela deixa a Ruptura crescer por dentro.",
        "desbloqueada": True,
        "ativa": True,
        "cor": (105, 255, 130),
        "cor_secundaria": (215, 255, 95),
    },
    "condutora": {
        "nome": "Manifestacao Condutora",
        "icone": "Sprites/manifestacao_condutora.png",
        "estado": "encontrado",
        "funcao": "Tecnica de rede: marca inimigos, cria circuitos entre eles e recompensa preparo coletivo.",
        "descricao_curta": (
            "Geovana aprende a usar os inimigos como parte do circuito. A energia nao procura "
            "apenas um alvo: ela monta caminhos, fecha conexoes e transforma a horda em uma rede instavel."
        ),
        "disparo": (
            "Fio Condutor: disparo de dano baixo que aplica um fio no alvo atingido. "
            "Inimigos marcados proximos criam linhas de energia entre si; essas linhas dao ticks "
            "nos conectados e ferem quem atravessa o circuito."
        ),
        "habilidade": "Fechamento de Circuito",
        "descricao_habilidade": (
            "Fecha todos os fios ativos. Cada componente conectado explode; quanto mais inimigos "
            "e conexoes existirem na rede, maior o dano. Alvos isolados recebem dano fraco."
        ),
        "traco": "Ideal para preparar o campo, manter inimigos vivos por tempo suficiente e explodir a rede inteira no momento certo.",
        "risco": "Ruim contra alvo unico; exige construir o circuito antes de colher dano alto.",
        "frase": "Geovana nao persegue um inimigo. Ela ensina a horda inteira a conduzir a propria queda.",
        "desbloqueada": True,
        "ativa": True,
        "cor": (255, 210, 80),
        "cor_secundaria": (80, 235, 255),
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


ORDEM_MANIFESTACOES = ["eletrica", "lacerante", "prismatica", "retornante", "parasitica", "condutora", "eco_grav"]


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
