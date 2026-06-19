# -*- coding: utf-8 -*-
import json
import os

import Caminhos  # Instala o redirecionamento do Cofre Dimensional para saves/*.json.


MANIFESTACAO_PADRAO = "eletrica"
CAMINHO_MANIFESTACAO_SELECIONADA = "saves/manifestacao_selecionada.json"
CAMINHO_PROGRESSO_MANIFESTACOES = "saves/manifestacoes_progresso.json"

MANIFESTACOES_JOGAVEIS = {
    "eletrica",
    "lacerante",
    "prismatica",
    "retornante",
    "parasitica",
    "condutora",
    "gravitante",
    "ancorada",
}

MISSOES_DESBLOQUEIO = {
    "eletrica": {
        "id": "eletrica_inicial",
        "fase": 0,
        "texto": "Disponivel desde o inicio.",
    },
    "lacerante": {
        "id": "fase1_fragmento_boss",
        "fase": 1,
        "texto": "Fase 1: derrote o Caranguejo do Nulo e colete o Fragmento Temporal.",
    },
    "prismatica": {
        "id": "fase2_fragmento_boss",
        "fase": 2,
        "texto": "Fase 2: estabilize a vitoria contra o chefe e atravesse para a proxima dimensao.",
    },
    "retornante": {
        "id": "fase3_fragmento_boss",
        "fase": 3,
        "texto": "Fase 3: vença o Pai-Rato e atravesse a fenda dimensional.",
    },
    "parasitica": {
        "id": "fase4_fragmento_boss",
        "fase": 4,
        "texto": "Fase 4: conclua a dimensao nevada e alcance a quinta fase.",
    },
    "condutora": {
        "id": "fase5_vitoria_umbra",
        "fase": 5,
        "texto": "Fase 5: vença Umbra ou atravesse a transicao para a fase 6.",
    },
    "gravitante": {
        "id": "fase6_vitoria_espinhos",
        "fase": 6,
        "texto": "Fase 6: conclua a arena de sarcas e energia gravitacional.",
    },
    "ancorada": {
        "id": "fase6_ciclo_concluido",
        "fase": 6,
        "texto": "Fase 6: estabilize o ciclo final da arena e firme uma ancora dimensional.",
    },
}

MISSOES_POR_FASE = {}
for _chave, _missao in MISSOES_DESBLOQUEIO.items():
    MISSOES_POR_FASE.setdefault(int(_missao.get("fase", 0)), []).append(_chave)


def _progresso_padrao():
    return {"missoes_concluidas": ["eletrica_inicial"], "desbloqueadas": ["eletrica"]}


def carregar_progresso_manifestacoes():
    progresso = _progresso_padrao()
    try:
        with open(CAMINHO_PROGRESSO_MANIFESTACOES, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if isinstance(dados, dict):
            missoes = dados.get("missoes_concluidas", [])
            desbloqueadas = dados.get("desbloqueadas", [])
            if isinstance(missoes, list):
                progresso["missoes_concluidas"] = sorted(set(str(m) for m in missoes) | {"eletrica_inicial"})
            if isinstance(desbloqueadas, list):
                progresso["desbloqueadas"] = sorted((set(str(m) for m in desbloqueadas) & MANIFESTACOES_JOGAVEIS) | {"eletrica"})
    except Exception:
        pass
    return progresso


def salvar_progresso_manifestacoes(progresso):
    progresso = progresso if isinstance(progresso, dict) else _progresso_padrao()
    progresso["missoes_concluidas"] = sorted(set(progresso.get("missoes_concluidas", [])) | {"eletrica_inicial"})
    progresso["desbloqueadas"] = sorted((set(progresso.get("desbloqueadas", [])) & MANIFESTACOES_JOGAVEIS) | {"eletrica"})
    os.makedirs("saves", exist_ok=True)
    with open(CAMINHO_PROGRESSO_MANIFESTACOES, "w", encoding="utf-8") as arquivo:
        json.dump(progresso, arquivo, ensure_ascii=False, indent=4)
    return progresso


def registrar_conclusao_fase(fase, detalhes=None):
    try:
        fase = int(fase)
    except Exception:
        return []
    progresso = carregar_progresso_manifestacoes()
    novas = []
    for chave in MISSOES_POR_FASE.get(fase, []):
        missao = MISSOES_DESBLOQUEIO.get(chave, {})
        missao_id = missao.get("id")
        if missao_id and missao_id not in progresso["missoes_concluidas"]:
            progresso["missoes_concluidas"].append(missao_id)
        if chave not in progresso["desbloqueadas"]:
            progresso["desbloqueadas"].append(chave)
            novas.append(chave)
    salvar_progresso_manifestacoes(progresso)
    return novas


def manifestacao_desbloqueada(chave, progresso=None, considerar_dev=True):
    if chave == MANIFESTACAO_PADRAO:
        return True
    if chave not in MANIFESTACOES_JOGAVEIS:
        return False
    if considerar_dev and Caminhos.modo_desenvolvedor_ativo():
        return True
    progresso = progresso or carregar_progresso_manifestacoes()
    return chave in set(progresso.get("desbloqueadas", []))


def missao_manifestacao(chave):
    return MISSOES_DESBLOQUEIO.get(chave, {"texto": "Eco ainda nao estabilizado."}).get("texto", "Eco ainda nao estabilizado.")


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
        "desbloqueada": False,
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
        "desbloqueada": False,
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
        "desbloqueada": False,
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
        "desbloqueada": False,
        "ativa": True,
        "cor": (105, 255, 130),
        "cor_secundaria": (215, 255, 95),
    },
    "condutora": {
        "nome": "Manifestacao Condutora",
        "icone": "Sprites/manifestacao_condutora.png",
        "estado": "encontrado",
        "funcao": "Tecnica logica: transforma inimigos em bits, conecta duas entradas e recompensa portas que resultam em 1.",
        "descricao_curta": (
            "Geovana passa a conduzir a Ruptura como um circuito vivo. Cada inimigo carrega 0 ou 1; "
            "o jogador escolhe dois alvos e resolve a porta logica atual."
        ),
        "disparo": (
            "Pulso Logico: o primeiro acerto marca Entrada A por poucos segundos. O segundo acerto em outro inimigo "
            "vira Entrada B, avalia OR, XOR, AND, NAND ou NOR e cria uma linha condutora."
        ),
        "habilidade": "Fechamento de Circuito",
        "descricao_habilidade": (
            "Detona os links logicos corretos ativos. Resultado 1 causa dano amplificado e deixa o link pronto; "
            "resultado 0 causa dano fraco e aplica Ruido Logico, uma lentidao curta em Geovana."
        ),
        "traco": "Ideal para ler o campo, escolher pares de bits e guardar links corretos para uma descarga em cadeia.",
        "risco": "Ruim contra alvo unico; exige leitura rapida dos bits e punira erros com lentidao leve, nao com stun.",
        "frase": "Geovana nao persegue um inimigo. Ela transforma a horda em entradas de um circuito logico.",
        "desbloqueada": False,
        "ativa": True,
        "cor": (255, 210, 80),
        "cor_secundaria": (80, 235, 255),
    },
    "gravitante": {
        "nome": "Manifestacao Gravitante",
        "icone": "Sprites/manifestacao_gravitante.png",
        "estado": "encontrado",
        "funcao": "Pressao automatica moderada no inicio: orbes orbitam alvos, causam ticks e escalam com build.",
        "descricao_curta": (
            "Geovana prende energia instavel ao corpo do inimigo. O disparo nao controla a gravidade: "
            "ele fica orbitando o alvo como materia presa em queda."
        ),
        "disparo": (
            "Orbe Gravitante: ao acertar o primeiro inimigo, fica girando em volta dele por alguns "
            "segundos, causa pequenos ticks e explode. Se o hospedeiro morrer antes, tenta migrar "
            "para outro alvo proximo."
        ),
        "habilidade": "Colapso Orbital",
        "descricao_habilidade": (
            "Cria tres orbes ao redor de Geovana. Apos breve preparo, eles disparam automaticamente "
            "contra inimigos proximos e iniciam orbitas de dano retardado."
        ),
        "traco": "Boa quando a tela esta caotica, oferecendo protecao temporaria e dano automatico retardado.",
        "risco": "Menos explosiva no inicio; depende de tempo de orbita, cartas de dano e alvos bem escolhidos.",
        "frase": "Geovana nao puxa o mundo. Ela prende a Ruptura ao corpo do inimigo ate tudo colapsar.",
        "desbloqueada": False,
        "ativa": True,
        "cor": (118, 190, 255),
        "cor_secundaria": (218, 245, 255),
    },
    "ancorada": {
        "nome": "Manifestacao Ancorada",
        "icone": "Sprites/manifestacao_ancorada.png",
        "estado": "encontrado",
        "funcao": "Controle de territorio proprio: escolhe um lugar, fixa ancoras e luta melhor ali.",
        "descricao_curta": (
            "Geovana prende pequenas ancoras de Ruptura no chao. A energia nao protege por escudo: "
            "ela recompensa permanecer perto do territorio escolhido."
        ),
        "disparo": (
            "Ancora de Ruptura: cada ataque planta uma ancora energetica no chao. "
            "Enquanto Geovana estiver perto de ancoras, seus disparos ficam mais fortes, "
            "a cadencia aumenta e inimigos que cruzam a area sofrem dano leve."
        ),
        "habilidade": "Dominio Fixo",
        "descricao_habilidade": (
            "Cria um circulo de dominio ao redor de Geovana por alguns segundos. Dentro dele, "
            "ataques sao fortalecidos, projeteis inimigos ficam mais lentos e inimigos recebem marca."
        ),
        "traco": "Ideal para escolher um territorio e defender aquele ponto em vez de fugir sem parar.",
        "risco": "Ruim contra chefes que forcam movimento, areas de dano e lutas em que ficar parado e perigoso.",
        "frase": "Geovana finca a Ruptura no chao e decide: daqui eu nao cedo.",
        "desbloqueada": False,
        "ativa": True,
        "cor": (75, 225, 255),
        "cor_secundaria": (255, 205, 80),
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


MANIFESTACOES_DADOS["lacerante"].update({
    "funcao": "Agressiva de medio alcance, feita para cortar hordas alinhadas, punir elites moveis e aplicar Laceracao.",
    "disparo": (
        "Corte de Ruptura: lamina curta, alcance menor e dano moderado no inicio. Atravessa inimigos em linha, "
        "aplica Laceracao e escala bem quando a build investe em dano. Com 3 acumulos, o alvo fica Aberto "
        "e sofre mais com movimento e ataques."
    ),
    "descricao_habilidade": (
        "Fenda Carnivora abre um rasgo a frente de Geovana. Apos breve aviso, a fissura explode em cortes, "
        "causa dano em linha, tem recarga mais longa e consome Laceracao dos alvos para dano extra. O teleporte lacerante tambem rasga "
        "o caminho percorrido, aplicando Laceracao em inimigos tocados pela fenda."
    ),
    "teleporte": (
        "Shift abre um rasgo lacerante entre origem e destino. Inimigos tocados pelo caminho recebem dano menor, "
        "ganham Laceracao e deixam a rota visualmente conectada ao estilo dos cortes da manifestacao."
    ),
    "traco": (
        "Lacerados sofrem dano extra ao se mover ou atacar. Sinergias fortes: Profetica para alinhar fendas, "
        "Insana para puxar alvos pelo rasgo e Voraz para aproveitar inimigos feridos."
    ),
    "risco": "Menor alcance, exige posicionamento e perde valor quando o jogador nao alinha os cortes ou enfrenta boss muito parado.",
})

MANIFESTACOES_DADOS["prismatica"].update({
    "funcao": "Tecnica de precisao que recompensa angulo, preparo, ricochete e geometria de luz.",
    "disparo": (
        "Feixe Prismatico: tiro fino, veloz e de dano base menor. Ricocheteia uma vez em parede ou inimigo marcado; "
        "apos ricochetear ganha dano. Se o feixe voltar ao mesmo alvo depois do ricochete, causa critico prismatico."
    ),
    "descricao_habilidade": (
        "Prisma de Refracao cria um prisma no cursor por alguns segundos. Disparos que atravessam o prisma se dividem "
        "em 3 feixes menores. O teleporte prismatico cria um prisma maior na saida do shift; esse prisma amplifica "
        "fragmentos ja refratados uma vez, permitindo combo de habilidade 2 com teleporte. Inimigos que tocam o prisma "
        "recebem dano leve e quebram a estrutura."
    ),
    "teleporte": (
        "Shift projeta luz da origem ate a saida e materializa um prisma maior no destino, nao no ponto de partida. "
        "Esse prisma aceita fragmentos do Prisma de Refracao e cria a segunda divisao controlada do combo."
    ),
    "traco": (
        "Excelente contra chefes previsiveis, paredes uteis e jogadores que calculam angulos. Brilha quando o jogador "
        "posiciona prisma, atravessa feixes e usa o shift como segunda lente."
    ),
    "risco": "Dano direto menor; depende de mira, posicionamento, arena com angulos bons e preparo do campo.",
})

MANIFESTACOES_DADOS["condutora"].update({
    "funcao": "Tecnica logica: conecte dois inimigos. Se a porta atual resultar em 1, o circuito fica amplificado.",
    "disparo": (
        "Pulso Logico: cada inimigo mostra 0 ou 1 enquanto a Condutora esta ativa. O primeiro acerto marca Entrada A; "
        "o segundo acerto em outro inimigo marca Entrada B, avalia a porta atual e consome a fila de portas. "
        "OR aceita qualquer 1; XOR pede bits diferentes; AND pede 1 e 1; NAND falha apenas em 1 e 1; NOR pede 0 e 0."
    ),
    "descricao_habilidade": (
        "Fechamento de Circuito detona apenas os links logicos corretos, aqueles com resultado 1. Um link causa dano bom; "
        "varios links criam descarga em cadeia mais forte. Se nao houver link correto, a habilidade apenas mostra falha fraca."
    ),
    "teleporte": (
        "Salto em Circuito: Shift cria uma linha de condutividade entre origem e destino. Inimigos tocados por essa linha "
        "podem ser conduzidos, e se Geovana cruzar a linha eles sofrem CURTO: stun de 3s e dano equivalente a 50% do auto attack. "
        "Esse teleporte nao consome portas logicas e nao aplica Ruido Logico."
    ),
    "traco": (
        "A estrategia ideal e ler os bits, escolher o par certo para a porta atual, manter links corretos por alguns segundos "
        "e fechar tudo no momento em que a horda estiver alinhada."
    ),
    "risco": "Resultado 0 ainda causa dano, mas aplica Ruido Logico: velocidade reduzida por pouco tempo. A pressao vem da leitura, nao de punicao pesada.",
})


ORDEM_MANIFESTACOES = [
    "eletrica",
    "lacerante",
    "prismatica",
    "retornante",
    "parasitica",
    "condutora",
    "gravitante",
    "ancorada",
    "eco_grav",
]


def obter_manifestacoes():
    progresso = carregar_progresso_manifestacoes()
    manifestacoes = []
    for chave in ORDEM_MANIFESTACOES:
        dados = dict(MANIFESTACOES_DADOS[chave])
        desbloqueada = manifestacao_desbloqueada(chave, progresso)
        dados["desbloqueada"] = desbloqueada
        dados["ativa"] = desbloqueada
        dados["missao_desbloqueio"] = missao_manifestacao(chave)
        manifestacoes.append((chave, dados))
    return manifestacoes


def salvar_manifestacao_ativa(chave):
    if chave not in MANIFESTACOES_DADOS or not manifestacao_desbloqueada(chave):
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
    if not manifestacao_desbloqueada(chave):
        chave = MANIFESTACAO_PADRAO
    return chave


def obter_dados_manifestacao_ativa():
    chave = obter_manifestacao_ativa()
    dados = dict(MANIFESTACOES_DADOS[chave])
    dados["desbloqueada"] = manifestacao_desbloqueada(chave)
    dados["missao_desbloqueio"] = missao_manifestacao(chave)
    return chave, dados
