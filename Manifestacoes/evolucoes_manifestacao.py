# -*- coding: utf-8 -*-
"""Fragmento da Ruptura e evolucoes de combate das Manifestacoes.

O estado deste modulo e exclusivo da partida. Nada e gravado no save: a escolha
e uma mutacao temporaria da Manifestacao equipada naquela jornada.
"""
import copy
import math
import random

import pygame

from dados_manifestacoes import MANIFESTACOES_DADOS
import ui_helpers
from deslocamento_inimigo import agendar_deslocamento, amostrar_trajetoria, progresso_deslocamento


MECANICAS = (
    ("eco", "A cada quarto ataque, dois ecos menores nascem em angulos opostos."),
    ("perfuracao", "O disparo atravessa o primeiro alvo e continua sua trajetoria."),
    ("caca", "Os disparos corrigem suavemente a rota em direcao ao inimigo mais proximo."),
    ("elo", "O impacto conecta ate dois inimigos proximos e reduz o movimento deles."),
    ("pulso", "Cada terceiro impacto abre um pulso que repele a horda ao redor do alvo."),
    ("vortice", "Cada quarto impacto contrai o espaco e puxa inimigos proximos para o centro."),
    ("selo", "Tres impactos no mesmo inimigo o aprisionam brevemente numa ruptura."),
    ("campo", "Usar a habilidade deixa um campo temporal que desacelera inimigos."),
    ("passo", "O Teleporte rompe origem e destino, afastando inimigos dos dois pontos."),
)


NOMES = {
    "eletrica": (
        "Sobrecarga Bifurcada", "Raio Transpassante", "Caça-Tempestade",
        "Rede Voltaica", "Trovão de Impacto", "Ímã de Tormenta",
        "Gaiola de Tesla", "Olho do Temporal", "Passo Fulminante",
    ),
    "lacerante": (
        "Cortes Gêmeos", "Fio Sem Fim", "Lâmina Perseguidora",
        "Sutura Cruel", "Ferida Repulsiva", "Carniceiro do Vazio",
        "Cicatriz Imóvel", "Matadouro Suspenso", "Passo Escarlate",
    ),
    "prismatica": (
        "Espectro Fraturado", "Luz Intangível", "Refração Caçadora",
        "Malha Cromática", "Explosão de Espectro", "Lente Gravitacional",
        "Cela de Luz", "Câmara Prismática", "Passo Arco-Íris",
    ),
    "retornante": (
        "Eco de Duas Voltas", "Travessia Reversa", "Rota Inevitável",
        "Laço de Retorno", "Recuo do Passado", "Chamado ao Centro",
        "Instante Repetido", "Horizonte Reverso", "Passo Recorrente",
    ),
    "parasitica": (
        "Ninhada Gêmea", "Esporo Penetrante", "Fome Guiada",
        "Micélio Compartilhado", "Eclosão Defensiva", "Raiz Faminta",
        "Casulo Temporal", "Jardim de Ruína", "Passo Infeccioso",
    ),
    "condutora": (
        "Entrada Duplicada", "Bit Perfurante", "Roteamento Autônomo",
        "Barramento Vivo", "Porta de Repulsão", "Nó de Convergência",
        "Loop Travado", "Clock Suspenso", "Salto de Circuito",
    ),
    "gravitante": (
        "Órbita Binária", "Massa Fantasma", "Queda Guiada",
        "Constelação Cativa", "Onda de Expulsão", "Poço Faminto",
        "Horizonte de Eventos", "Campo de Maré", "Passo Singular",
    ),
    "ancorada": (
        "Estacas Gêmeas", "Fundação Profunda", "Prego Buscador",
        "Território Conectado", "Bastião Repulsor", "Solo Voraz",
        "Prisão de Fundação", "Domínio Persistente", "Passo Demarcador",
    ),
}


VERBOS = {
    "eletrica": ("descargas", "eletricidade"),
    "lacerante": ("cortes", "a ferida espacial"),
    "prismatica": ("feixes", "a luz refratada"),
    "retornante": ("pulsos", "o fluxo reverso"),
    "parasitica": ("sementes", "a infestacao"),
    "condutora": ("bits", "o circuito"),
    "gravitante": ("orbes", "a gravidade"),
    "ancorada": ("ancoras", "o territorio"),
}


# Mesmo quando duas evolucoes usam uma primitiva interna parecida (por exemplo,
# criar outro projetil), gatilho, quantidade, geometria e controle pertencem a
# identidade da Manifestacao. Nenhum perfil mecanico abaixo e repetido.
PERFIS_MANIFESTACAO = {
    "eletrica": {"eco": (4, 2, 0.22), "perfuracao": 1, "caca": 0.055, "elo": (2, 1400), "pulso": (3, 230, 130), "vortice": (4, 280, 145), "selo": (3, 900), "campo": (2300, 185), "passo": (190, 115)},
    "lacerante": {"eco": (3, 1, 1.57), "perfuracao": 2, "cicatriz": (3, 1050), "elo": (1, 1850), "pulso": (3, 185, 165), "vortice": (5, 245, 175), "selo": (2, 720), "campo": (1750, 225), "passo": (150, 155)},
    "prismatica": {"eco": (5, 3, 0.34), "perfuracao": 3, "caca": 0.032, "elo": (3, 900), "pulso": (4, 265, 105), "vortice": (6, 310, 120), "selo": (4, 1150), "campo": (2800, 155), "passo": (230, 82)},
    "retornante": {"eco": (3, 1, 0.0), "perfuracao": 4, "caca": 0.024, "elo": (1, 2100), "pulso": (5, 210, 185), "vortice": (3, 325, 105), "selo": (2, 1050), "campo": (1900, 245), "passo": (260, 74)},
    "parasitica": {"eco": (5, 2, 0.12), "perfuracao": 5, "caca": 0.042, "elo": (3, 1750), "pulso": (4, 195, 145), "vortice": (3, 275, 190), "selo": (4, 1450), "campo": (3200, 205), "passo": (175, 128)},
    "condutora": {"eco": (2, 1, 0.18), "perfuracao": 6, "caca": 0.068, "elo": (4, 1050), "pulso": (6, 290, 120), "vortice": (5, 350, 92), "selo": (2, 620), "campo": (1600, 265), "passo": (215, 102)},
    "gravitante": {"eco": (6, 3, 0.08), "perfuracao": 7, "caca": 0.018, "elo": (2, 2400), "pulso": (5, 320, 92), "vortice": (2, 365, 205), "selo": (5, 1550), "campo": (3600, 235), "passo": (285, 68)},
    "ancorada": {"eco": (4, 1, 0.0), "perfuracao": 8, "caca": 0.012, "elo": (3, 2600), "pulso": (7, 350, 78), "vortice": (6, 390, 85), "selo": (3, 1850), "campo": (4200, 285), "passo": (145, 188)},
}


TEXTOS_EXCLUSIVOS = {
    "eletrica": (
        "A quarta descarga se bifurca em dois arcos laterais que procuram abrir a horda.",
        "A carga ioniza o primeiro corpo e atravessa para descarregar no que estiver atras dele.",
        "A eletricidade curva o voo continuamente para perseguir o condutor mais proximo.",
        "O impacto fecha uma rede voltaica em dois vizinhos e reduz o movimento do circuito.",
        "O terceiro impacto descarrega um trovao que expulsa tudo ao redor do alvo.",
        "A quarta descarga inverte a polaridade e atrai inimigos para o ponto atingido.",
        "Tres cargas no mesmo corpo fecham uma gaiola eletrica e o imobilizam.",
        "A Onda deixa uma tempestade ionizada que desacelera quem atravessa sua borda.",
        "Origem e destino do Teleporte explodem em aneis eletricos de repulsao.",
    ),
    "lacerante": (
        "O terceiro ataque abre um corte perpendicular, formando uma cruz de laminas no espaco.",
        "Os dois primeiros cortes atravessam mais corpos antes de a fenda se fechar.",
        "O terceiro corte permanece como uma cicatriz por um instante e pode atingir quem a cruza.",
        "Acertar um lacerado costura sua ferida ao inimigo mais proximo e prolonga o sangramento.",
        "Quando a sequencia abre uma ferida, o sangue temporal repele os inimigos ao redor.",
        "Feridas abertas contraem o espaco e arrastam a horda para a linha do proximo corte.",
        "Dois impactos gravam uma cicatriz que prende brevemente o alvo no lugar.",
        "A Fenda Carnivora deixa um matadouro suspenso que retarda quem entrar na linha.",
        "O Teleporte rasga origem e destino com um golpe curto e agressivo de afastamento.",
    ),
    "prismatica": (
        "O quinto feixe se abre em tres cores, cada uma partindo num angulo diferente.",
        "A luz atravessa tres alvos sem perder sua geometria de ricochete.",
        "A refracao corrige o feixe devagar, preservando o desafio de calcular o angulo.",
        "Tres inimigos formam uma malha cromatica que desacelera apenas dentro do triangulo.",
        "O quarto impacto rompe o espectro numa onda larga de repulsao suave.",
        "Seis impactos formam uma lente que converge inimigos para o foco de luz.",
        "Quatro exposicoes fecham uma cela luminosa de duracao prolongada.",
        "O Prisma cria uma camara estreita e duradoura onde o tempo da horda refrata.",
        "O Teleporte abre dois flashes amplos que reposicionam inimigos sem violencia bruta.",
    ),
    "retornante": (
        "A cada terceiro pulso, uma memoria repete sozinha o caminho de volta.",
        "A ida atravessa quatro alvos adicionais; a volta ainda reconhece cada corpo cortado.",
        "Somente durante a ida o pulso ajusta levemente a rota antes de escolher seu retorno.",
        "O primeiro alvo cria um laco longo que segura um segundo inimigo na rota de volta.",
        "O quinto impacto devolve o espaco com forca e arremessa a horda para longe.",
        "O terceiro retorno chama inimigos de uma area enorme para cruzarem o caminho do pulso.",
        "Dois encontros com o mesmo alvo repetem aquele instante e o congelam.",
        "Cada ricochete da Memoria Instavel deixa um eco temporal que atrasa perseguidores.",
        "Os dois pontos do Teleporte criam recuos extensos, preparando corredores para o retorno.",
    ),
    "parasitica": (
        "A quinta semente libera dois esporos laterais que procuram novos hospedeiros.",
        "O esporo perfura cinco corpos, plantando uma infestacao progressivamente mais espalhada.",
        "A semente viva fareja o hospedeiro mais proximo e corrige sua trajetoria com paciencia.",
        "O micelio conecta tres infectados e torna pesado o movimento de toda a colonia.",
        "A quarta eclosao parcial repele predadores para proteger o hospedeiro central.",
        "A terceira infeccao cria uma raiz faminta que puxa a colonia para a mesma colheita.",
        "Quatro implantes fecham um casulo demorado ao redor do alvo.",
        "Eclosao cultiva um jardim amplo e persistente que amadurece a horda lentamente.",
        "O Teleporte espalha a infestacao num anel curto que empurra novos hospedeiros.",
    ),
    "condutora": (
        "A cada segunda entrada, um bit duplicado nasce em diagonal para buscar outro circuito.",
        "O pulso atravessa seis entradas e preserva o sinal para avaliar o proximo bit.",
        "O roteamento autonomo faz o fio virar rapidamente para a entrada logica mais proxima.",
        "Quatro alvos compartilham um barramento; o movimento de todos desacelera enquanto conectados.",
        "A sexta operacao envia uma porta de repulsao pelo circuito inteiro.",
        "Cinco resultados comprimem as entradas num unico no de convergencia amplo.",
        "Duas leituras repetidas travam o alvo num loop curto e imediato.",
        "Fechamento cria um clock enorme, breve e lento ao redor do registrador.",
        "Cada ponta do Teleporte executa um pulso logico de alcance medio.",
    ),
    "gravitante": (
        "O sexto disparo cria tres massas menores em formacao orbital fechada.",
        "A massa atravessa sete corpos antes de escolher em qual gravidade ficara presa.",
        "A queda guiada faz o orbe corrigir a rota quase imperceptivelmente antes da captura.",
        "Dois hospedeiros viram uma constelacao cativa e movem-se pesadamente por mais tempo.",
        "O quinto impacto libera uma mare enorme que afasta sem quebrar as orbitas existentes.",
        "O segundo impacto abre um poco violento e puxa uma area inteira para o hospedeiro.",
        "Cinco passagens formam um horizonte de eventos longo ao redor do alvo.",
        "Colapso deixa o maior campo temporal, mantendo a mare gravitacional ativa.",
        "O Teleporte produz aneis vastos e suaves, como ondas numa superficie pesada.",
    ),
    "ancorada": (
        "A quarta estaca finca uma ancora gemea exatamente sobre a mesma trajetoria.",
        "A fundacao atravessa oito inimigos antes de se fixar no territorio escolhido.",
        "O prego corrige a rota apenas o suficiente para nao abandonar o dominio proximo.",
        "Tres alvos passam a compartilhar um territorio conectado de lentidao muito longa.",
        "A setima colisao ergue um bastiao largo que empurra invasores para fora.",
        "Seis impactos fazem o solo contrair lentamente uma area extensa para dentro do dominio.",
        "Tres marcas constroem a prisao mais longa entre todas as Manifestacoes.",
        "Dominio Fixo permanece por mais tempo e cobre o maior territorio de controle.",
        "O Teleporte demarca uma fronteira curta, mas expulsa invasores com grande forca.",
    ),
}


def _montar_catalogo():
    catalogo = {}
    for chave, nomes in NOMES.items():
        substantivo, identidade = VERBOS[chave]
        entradas = []
        for indice, ((mecanica, texto), nome) in enumerate(zip(MECANICAS, nomes)):
            familia = "cicatriz" if chave == "lacerante" and mecanica == "caca" else mecanica
            descricao = TEXTOS_EXCLUSIVOS[chave][indice]
            entradas.append({
                "id": f"{chave}_{indice + 1}",
                "nome": nome,
                "descricao": descricao,
                "mecanica": f"{chave}_{familia}",
                "familia": familia,
                "perfil": PERFIS_MANIFESTACAO[chave].get(familia),
                "indice": indice,
                "identidade": identidade,
            })
        catalogo[chave] = tuple(entradas)
    return catalogo


CATALOGO = _montar_catalogo()


def criar_estado(manifestacao):
    chave = str(manifestacao or "eletrica").strip().lower()
    if chave not in CATALOGO:
        chave = "eletrica"
    return {
        "manifestacao": chave,
        "evolucao": None,
        "contador_disparos": 0,
        "contador_impactos": 0,
        "campos": [],
        "pulsos": [],
    }


def evolucao_ativa(estado):
    if not estado or not estado.get("evolucao"):
        return None
    for item in CATALOGO.get(estado.get("manifestacao"), ()):
        if item["id"] == estado["evolucao"]:
            return item
    return None


def sortear_opcoes(manifestacao, quantidade=3):
    chave = str(manifestacao or "eletrica").strip().lower()
    return random.sample(list(CATALOGO.get(chave, CATALOGO["eletrica"])), k=min(quantidade, 9))


def criar_fragmento(x, y, agora_ms):
    return {"x": float(x), "y": float(y), "inicio": int(agora_ms), "seed": random.randint(1, 999999)}


def fragmento_colidiu(fragmento, jogador_rect):
    return math.hypot(jogador_rect.centerx - fragmento["x"], jogador_rect.centery - fragmento["y"]) <= 48


def repelir_inimigos(inimigos, centro, raio=310, forca=175):
    cx, cy = centro
    afetados = 0
    for inimigo in inimigos:
        rect = inimigo.get("rect")
        if not rect:
            continue
        dx, dy = rect.centerx - cx, rect.centery - cy
        distancia = math.hypot(dx, dy)
        if distancia <= 0 or distancia > raio:
            continue
        impulso = forca * (1.0 - distancia / raio) + 34
        nx, ny = dx / distancia, dy / distancia
        destino_x = rect.x + nx * impulso
        destino_y = rect.y + ny * impulso
        if agendar_deslocamento(inimigo, destino_x, destino_y, curvatura=0.20):
            afetados += 1
    return afetados


def desenhar_fragmento(tela, fragmento, agora_ms):
    x, y = int(fragmento["x"]), int(fragmento["y"])
    fase = (agora_ms - fragmento["inicio"]) * 0.008
    pulso = 1.0 + math.sin(fase) * 0.16
    brilho = pygame.Surface((150, 150), pygame.SRCALPHA)
    centro = (75, 75)
    for raio, alpha in ((58, 18), (43, 30), (29, 55)):
        pygame.draw.circle(brilho, (155, 60, 255, alpha), centro, int(raio * pulso))
    angulo = fase * 0.35
    pontos = []
    for i, raio in enumerate((25, 12, 25, 12, 25, 12)):
        a = angulo + i * math.pi / 3
        pontos.append((75 + math.cos(a) * raio * pulso, 75 + math.sin(a) * raio * pulso))
    pygame.draw.polygon(brilho, (205, 115, 255, 235), pontos)
    pygame.draw.polygon(brilho, (235, 225, 255, 255), pontos, 2)
    pygame.draw.circle(brilho, (85, 10, 135, 255), centro, 8)
    pygame.draw.circle(brilho, (255, 255, 255, 245), centro, 3)
    tela.blit(brilho, (x - 75, y - 75))


def _ajustar_pontos_corte(disparo, delta_angulo, escala=1.0):
    pontos = disparo.get("pontos_corte")
    if not pontos:
        return
    px, py = pontos[0]
    c, s = math.cos(delta_angulo), math.sin(delta_angulo)
    novos = []
    for x, y in pontos:
        dx, dy = (x - px) * escala, (y - py) * escala
        novos.append((px + dx * c - dy * s, py + dx * s + dy * c))
    disparo["pontos_corte"] = novos
    disparo["inicio"], disparo["fim"] = novos[0], novos[-1]
    margem = float(disparo.get("largura_corte", 18.0))
    min_x, max_x = min(p[0] for p in novos), max(p[0] for p in novos)
    min_y, max_y = min(p[1] for p in novos), max(p[1] for p in novos)
    disparo["rect"] = pygame.Rect(
        int(min_x - margem), int(min_y - margem),
        max(2, int(max_x - min_x + margem * 2)),
        max(2, int(max_y - min_y + margem * 2)),
    )


def _copiar_disparo(disparo, desvio, escala=0.72):
    novo = copy.deepcopy(disparo)
    novo["angulo"] = float(disparo.get("angulo", 0.0)) + desvio
    novo["vx"] = math.cos(novo["angulo"]) * float(disparo.get("velocidade_base_vfx", 10.0))
    novo["vy"] = math.sin(novo["angulo"]) * float(disparo.get("velocidade_base_vfx", 10.0))
    if novo.get("tipo_manifestacao") == "lacerante_corte":
        _ajustar_pontos_corte(novo, desvio, escala)
    rect = novo["rect"]
    centro = rect.center
    if novo.get("tipo_manifestacao") != "lacerante_corte":
        rect.size = (max(8, int(rect.width * escala)), max(8, int(rect.height * escala)))
        rect.center = centro
    novo["pos_x"], novo["pos_y"] = float(rect.x), float(rect.y)
    novo["evolucao_eco"] = True
    novo["seed_vfx"] = random.randint(1, 9999999)
    novo["trail"] = []
    return novo


def aplicar_ao_disparo(disparo, estado):
    item = evolucao_ativa(estado)
    if not item:
        return [disparo]
    disparo["evolucao_manifestacao"] = item["id"]
    mecanica = item.get("familia", item["mecanica"])
    perfil = item.get("perfil")
    if mecanica == "perfuracao":
        disparo["evolucao_perfuracoes"] = int(perfil or 1)
    elif mecanica == "caca":
        disparo["evolucao_caca"] = True
        disparo["evolucao_caca_curva"] = float(perfil or 0.055)
    elif mecanica == "cicatriz":
        a_cada, duracao = perfil or (3, 1050)
        if (estado["contador_disparos"] + 1) % int(a_cada) == 0:
            disparo["duracao_ms"] = max(int(disparo.get("duracao_ms", 0)), int(duracao))
            disparo["evolucao_cicatriz"] = True
            disparo["multi_hit"] = True
    estado["contador_disparos"] += 1
    if mecanica == "eco":
        a_cada, quantidade, abertura = perfil or (4, 2, 0.22)
        if estado["contador_disparos"] % int(a_cada) == 0:
            if int(quantidade) == 1:
                return [disparo, _copiar_disparo(disparo, float(abertura))]
            desvios = [
                (indice - (int(quantidade) - 1) / 2.0) * float(abertura)
                for indice in range(int(quantidade))
            ]
            return [disparo] + [_copiar_disparo(disparo, desvio) for desvio in desvios]
    return [disparo]


def atualizar_disparo(disparo, inimigos):
    if not disparo.get("evolucao_caca") or not inimigos:
        return
    alvos = [i for i in inimigos if i.get("rect") and not i.get("invisivel", False)]
    if not alvos:
        return
    cx, cy = disparo["rect"].center
    alvo = min(alvos, key=lambda i: (i["rect"].centerx - cx) ** 2 + (i["rect"].centery - cy) ** 2)
    desejado = math.atan2(alvo["rect"].centery - cy, alvo["rect"].centerx - cx)
    atual = float(disparo.get("angulo", desejado))
    delta = (desejado - atual + math.pi) % (2 * math.pi) - math.pi
    curva = float(disparo.get("evolucao_caca_curva", 0.055))
    ajuste = max(-curva, min(curva, delta))
    disparo["angulo"] = atual + ajuste
    if disparo.get("tipo_manifestacao") == "lacerante_corte":
        _ajustar_pontos_corte(disparo, ajuste)


def _mover_grupo(inimigos, centro, raio, forca, puxar=False):
    cx, cy = centro
    for outro in inimigos:
        rect = outro.get("rect")
        if not rect:
            continue
        dx, dy = rect.centerx - cx, rect.centery - cy
        d = math.hypot(dx, dy)
        if d <= 1 or d > raio:
            continue
        sinal = -1 if puxar else 1
        deslocamento = forca * (1 - d / raio)
        destino_x = rect.x + sinal * dx / d * deslocamento
        destino_y = rect.y + sinal * dy / d * deslocamento
        agendar_deslocamento(outro, destino_x, destino_y, curvatura=0.14 if puxar else 0.20)


def ao_acertar(disparo, alvo, inimigos, estado, agora_ms):
    item = evolucao_ativa(estado)
    if not item or disparo.get("evolucao_manifestacao") != item["id"]:
        return False
    mecanica = item.get("familia", item["mecanica"])
    perfil = item.get("perfil")
    estado["contador_impactos"] += 1
    centro = alvo["rect"].center
    if item["id"] == "retornante_8" and disparo.get("retornante_fase") == "instavel":
        estado["campos"].append({
            "centro": centro,
            "inicio": agora_ms,
            "fim": agora_ms + 950,
            "raio": 92,
        })
    if mecanica == "elo":
        quantidade_alvos, duracao_lento = perfil or (2, 1400)
        proximos = sorted(
            (i for i in inimigos if i is not alvo and i.get("rect")),
            key=lambda i: (i["rect"].centerx - centro[0]) ** 2 + (i["rect"].centery - centro[1]) ** 2,
        )[:int(quantidade_alvos)]
        for outro in proximos:
            outro["ruptura_lento_fim"] = agora_ms + int(duracao_lento)
        estado["pulsos"].append({"tipo": "elo", "centro": centro, "alvos": [i["rect"].center for i in proximos], "inicio": agora_ms})
    elif mecanica == "pulso" and estado["contador_impactos"] % int((perfil or (3, 230, 130))[0]) == 0:
        _, raio, forca = perfil or (3, 230, 130)
        _mover_grupo(inimigos, centro, raio, forca, False)
        estado["pulsos"].append({"tipo": "pulso", "centro": centro, "inicio": agora_ms})
    elif mecanica == "vortice" and estado["contador_impactos"] % int((perfil or (4, 280, 145))[0]) == 0:
        _, raio, forca = perfil or (4, 280, 145)
        _mover_grupo(inimigos, centro, raio, forca, True)
        estado["pulsos"].append({"tipo": "vortice", "centro": centro, "inicio": agora_ms})
    elif mecanica == "selo":
        limite_selo, duracao_raiz = perfil or (3, 900)
        chave = "ruptura_selo_" + item["id"]
        alvo[chave] = int(alvo.get(chave, 0)) + 1
        if alvo[chave] >= int(limite_selo):
            alvo[chave] = 0
            alvo["ruptura_raiz_fim"] = agora_ms + int(duracao_raiz)
            estado["pulsos"].append({"tipo": "selo", "centro": centro, "inicio": agora_ms})
    if mecanica == "perfuracao" and disparo.get("evolucao_perfuracoes", 0) > 0:
        disparo["evolucao_perfuracoes"] -= 1
        return True
    if mecanica == "cicatriz" and disparo.get("evolucao_cicatriz"):
        return True
    return False


def ao_usar_habilidade(estado, centro, agora_ms):
    item = evolucao_ativa(estado)
    if item and item.get("familia", item["mecanica"]) == "campo" and item["id"] != "retornante_8":
        duracao, raio = item.get("perfil") or (2300, 185)
        estado["campos"].append({"centro": tuple(centro), "inicio": agora_ms, "fim": agora_ms + int(duracao), "raio": int(raio)})


def ao_teleportar(estado, origem, destino, inimigos, agora_ms):
    item = evolucao_ativa(estado)
    if not item or item.get("familia", item["mecanica"]) != "passo":
        return
    raio, forca = item.get("perfil") or (190, 115)
    for centro in (origem, destino):
        _mover_grupo(inimigos, centro, raio, forca, False)
        estado["pulsos"].append({"tipo": "passo", "centro": centro, "inicio": agora_ms})


def atualizar_e_desenhar(tela, estado, inimigos, agora_ms):
    cor = tuple(MANIFESTACOES_DADOS.get(estado.get("manifestacao"), {}).get("cor", (175, 80, 255)))
    trilhas = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    tem_trilha = False
    for inimigo in inimigos:
        deslocamento = inimigo.get("ruptura_deslocamento") if isinstance(inimigo, dict) else None
        rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
        if not deslocamento or rect is None:
            continue
        tem_trilha = True
        pontos = [
            (int(x + rect.width / 2), int(y + rect.height / 2))
            for x, y in amostrar_trajetoria(deslocamento)
        ]
        if len(pontos) > 1:
            for indice in range(0, len(pontos) - 1, 2):
                pygame.draw.line(trilhas, (*cor, 120), pontos[indice], pontos[indice + 1], 2)
        destino = (int(deslocamento["destino_x"] + rect.width / 2), int(deslocamento["destino_y"] + rect.height / 2))
        progresso = progresso_deslocamento(deslocamento, agora_ms)
        raio_destino = int(10 + 12 * progresso)
        pygame.draw.circle(trilhas, (*cor, 205), destino, raio_destino, 2)
        pygame.draw.circle(trilhas, (235, 235, 255, 190), rect.center, max(5, int(13 * (1.0 - progresso))), 1)
    if tem_trilha:
        tela.blit(trilhas, (0, 0))
    for campo in list(estado["campos"]):
        if agora_ms >= campo["fim"]:
            estado["campos"].remove(campo)
            continue
        cx, cy = campo["centro"]
        for inimigo in inimigos:
            rect = inimigo.get("rect")
            if rect and math.hypot(rect.centerx - cx, rect.centery - cy) <= campo["raio"]:
                inimigo["ruptura_lento_fim"] = agora_ms + 120
        surf = pygame.Surface((campo["raio"] * 2 + 8, campo["raio"] * 2 + 8), pygame.SRCALPHA)
        alpha = int(55 * min(1.0, (campo["fim"] - agora_ms) / 450.0))
        pygame.draw.circle(surf, (*cor, alpha), (campo["raio"] + 4, campo["raio"] + 4), campo["raio"], 3)
        tela.blit(surf, (cx - campo["raio"] - 4, cy - campo["raio"] - 4))
    for pulso in list(estado["pulsos"]):
        idade = agora_ms - pulso["inicio"]
        if idade > 520:
            estado["pulsos"].remove(pulso)
            continue
        progresso = idade / 520.0
        cx, cy = pulso["centro"]
        raio = int(18 + 145 * progresso)
        pygame.draw.circle(tela, cor, (int(cx), int(cy)), raio, max(1, int(4 * (1 - progresso))))
        if pulso["tipo"] == "elo":
            for fim in pulso.get("alvos", []):
                pygame.draw.line(tela, cor, (int(cx), int(cy)), fim, 2)


def fator_movimento_inimigo(inimigo, agora_ms):
    if agora_ms < int(inimigo.get("ruptura_raiz_fim", 0)):
        return 0.0
    if agora_ms < int(inimigo.get("ruptura_lento_fim", 0)):
        return 0.55
    return 1.0


def _desenhar_glifo(surf, centro, indice, cor, selecionado):
    cx, cy = centro
    raio = 25 if selecionado else 21
    pygame.draw.circle(surf, (*cor, 45), centro, raio + 10)
    pygame.draw.circle(surf, cor, centro, raio, 2)
    pontas = 3 + indice % 5
    pontos = []
    for i in range(pontas * 2):
        r = raio if i % 2 == 0 else raio * 0.38
        a = -math.pi / 2 + i * math.pi / pontas + indice * 0.19
        pontos.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    pygame.draw.lines(surf, cor, True, pontos, 2)
    pygame.draw.circle(surf, (245, 245, 255), centro, 4)


def _texto_wrap(surf, texto, fonte, cor, rect, linhas_max=5):
    palavras = texto.split()
    linhas, atual = [], ""
    for palavra in palavras:
        teste = (atual + " " + palavra).strip()
        if fonte.size(teste)[0] <= rect.width:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    for i, linha in enumerate(linhas[:linhas_max]):
        img = fonte.render(linha, True, cor)
        surf.blit(img, (rect.x, rect.y + i * (fonte.get_height() + 3)))


def _tracar_fratura(surf, rng, origem, angulo, comprimento, cor, ramificar=True):
    """Desenha uma rachadura irregular com halo e pequenas bifurcacoes."""
    pontos = [(float(origem[0]), float(origem[1]))]
    x, y = pontos[0]
    passos = max(4, int(comprimento / 34))
    passo = comprimento / passos
    direcao = angulo
    for indice in range(passos):
        direcao += rng.uniform(-0.18, 0.18)
        x += math.cos(direcao) * passo * rng.uniform(0.82, 1.18)
        y += math.sin(direcao) * passo * rng.uniform(0.82, 1.18)
        pontos.append((x, y))
        if ramificar and indice > 1 and rng.random() < 0.22:
            lado = rng.choice((-1, 1))
            tamanho_ramo = rng.uniform(24, 72)
            fim_ramo = (
                x + math.cos(direcao + lado * rng.uniform(0.55, 1.0)) * tamanho_ramo,
                y + math.sin(direcao + lado * rng.uniform(0.55, 1.0)) * tamanho_ramo,
            )
            pygame.draw.line(surf, (*cor, 22), (int(x), int(y)), fim_ramo, 4)
            pygame.draw.line(surf, (*cor, 105), (int(x), int(y)), fim_ramo, 1)
    pontos_int = [(int(px), int(py)) for px, py in pontos]
    pygame.draw.lines(surf, (*cor, 20), False, pontos_int, 7)
    pygame.draw.lines(surf, (*cor, 72), False, pontos_int, 3)
    pygame.draw.lines(surf, (*cor, 175), False, pontos_int, 1)


def _criar_textura_fragmentada(largura, altura, cor, cor2, seed):
    """Cria vidro rompido procedural: placas, veios e estilhacos soltos."""
    rng = random.Random(seed)
    textura = pygame.Surface((largura, altura), pygame.SRCALPHA)
    foco = (largura * 0.5, altura * 0.42)

    # Placas radiais irregulares. Cada anel se desencontra do anterior para
    # evitar a aparencia de uma teia geometrica perfeita.
    setores = 22
    angulos = [
        -math.pi / 2 + i * math.tau / setores + rng.uniform(-0.055, 0.055)
        for i in range(setores + 1)
    ]
    aneis = (54, 125, 225, 355, math.hypot(largura, altura) * 0.72)
    anteriores = [foco for _ in range(setores + 1)]
    for indice_anel, raio in enumerate(aneis):
        atuais = []
        for indice, angulo in enumerate(angulos):
            variacao = rng.uniform(0.84, 1.16)
            atuais.append((
                foco[0] + math.cos(angulo) * raio * variacao,
                foco[1] + math.sin(angulo) * raio * variacao,
            ))
        for setor in range(setores):
            poligono = [anteriores[setor], anteriores[setor + 1], atuais[setor + 1], atuais[setor]]
            alpha = rng.randint(7, 18) + (5 if (setor + indice_anel) % 4 == 0 else 0)
            tonalidade = cor if (setor + indice_anel) % 3 else cor2
            pygame.draw.polygon(textura, (*tonalidade, alpha), poligono)
            pygame.draw.lines(textura, (*cor, rng.randint(30, 66)), False, poligono[1:], 1)
        anteriores = atuais

    # Veios principais partindo do epicentro e fraturas secundarias nas bordas.
    for indice in range(18):
        angulo = indice * math.tau / 18 + rng.uniform(-0.13, 0.13)
        _tracar_fratura(
            textura, rng, foco, angulo,
            math.hypot(largura, altura) * rng.uniform(0.46, 0.70),
            cor if indice % 3 else cor2,
        )
    focos_secundarios = (
        (largura * 0.08, altura * 0.18),
        (largura * 0.92, altura * 0.23),
        (largura * 0.14, altura * 0.83),
        (largura * 0.88, altura * 0.80),
    )
    for fx, fy in focos_secundarios:
        for _ in range(4):
            angulo_centro = math.atan2(foco[1] - fy, foco[0] - fx)
            _tracar_fratura(
                textura, rng, (fx, fy), angulo_centro + rng.uniform(-1.05, 1.05),
                rng.uniform(100, 245), cor2, ramificar=False,
            )

    # Estilhacos destacados nas margens, com tamanhos e rotacoes diferentes.
    for _ in range(74):
        borda_horizontal = rng.random() < 0.58
        if borda_horizontal:
            cx = rng.uniform(0, largura)
            cy = rng.choice((rng.uniform(-10, altura * 0.16), rng.uniform(altura * 0.84, altura + 10)))
        else:
            cx = rng.choice((rng.uniform(-10, largura * 0.13), rng.uniform(largura * 0.87, largura + 10)))
            cy = rng.uniform(0, altura)
        tamanho = rng.uniform(9, 38)
        rotacao = rng.uniform(0, math.tau)
        pontas = 3 if rng.random() < 0.72 else 4
        pontos = []
        for indice in range(pontas):
            angulo = rotacao + indice * math.tau / pontas + rng.uniform(-0.25, 0.25)
            raio = tamanho * rng.uniform(0.45, 1.0)
            pontos.append((cx + math.cos(angulo) * raio, cy + math.sin(angulo) * raio))
        cor_estilhaco = cor2 if rng.random() < 0.32 else cor
        pygame.draw.polygon(textura, (*cor_estilhaco, rng.randint(9, 28)), pontos)
        pygame.draw.polygon(textura, (*cor_estilhaco, rng.randint(48, 108)), pontos, 1)
        if rng.random() < 0.25:
            pygame.draw.line(textura, (*cor_estilhaco, 85), pontos[0], pontos[2], 1)
    textura.set_alpha(168)
    return textura


def abrir_menu(tela, manifestacao, estado, relogio=None):
    opcoes = sortear_opcoes(manifestacao)
    selecionado = 0
    clock = relogio or pygame.time.Clock()
    fundo = tela.copy()
    largura, altura = tela.get_size()
    dados = MANIFESTACOES_DADOS.get(estado["manifestacao"], {})
    cor = tuple(dados.get("cor", (175, 80, 255)))
    cor2 = tuple(dados.get("cor_secundaria", (80, 220, 255)))
    fonte_titulo = pygame.font.Font("Texto/rainyhearts.ttf", max(30, int(altura * 0.047)))
    fonte_nome = pygame.font.Font("Texto/rainyhearts.ttf", max(22, int(altura * 0.030)))
    fonte_desc = pygame.font.Font("Texto/rainyhearts.ttf", max(16, int(altura * 0.021)))
    fonte_rodape = pygame.font.Font("Texto/rainyhearts.ttf", max(15, int(altura * 0.019)))
    card_w = min(330, int(largura * 0.27))
    card_h = min(410, int(altura * 0.53))
    gap = max(18, int(largura * 0.025))
    total_w = card_w * 3 + gap * 2
    inicio_x = (largura - total_w) // 2
    card_y = int(altura * 0.29)
    cards = [
        pygame.Rect(inicio_x + i * (card_w + gap), card_y, card_w, card_h)
        for i in range(3)
    ]
    textura_fragmentada = _criar_textura_fragmentada(
        largura, altura, cor, cor2,
        seed=sum(ord(letra) for letra in estado["manifestacao"]) * 7919,
    )
    cursor_visivel_anterior = pygame.mouse.get_visible()
    pygame.mouse.set_visible(False)
    while True:
        agora = pygame.time.get_ticks()
        mouse = ui_helpers.obter_pos_mouse_superficie(tela)
        confirmar = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                pygame.mouse.set_visible(cursor_visivel_anterior)
                return None
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    selecionado = (selecionado - 1) % 3
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    selecionado = (selecionado + 1) % 3
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    confirmar = True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos_evento = ui_helpers.converter_pos_mouse_jogo(event.pos)
                for indice_card, rect_card in enumerate(cards):
                    if rect_card.collidepoint(pos_evento):
                        selecionado = indice_card
                        confirmar = True
                        break
            if event.type == pygame.JOYHATMOTION:
                if event.value[0]:
                    selecionado = (selecionado + event.value[0]) % 3
            if event.type == pygame.JOYBUTTONDOWN and event.button in (0, 7):
                confirmar = True

        tela.blit(fundo, (0, 0))
        véu = pygame.Surface((largura, altura), pygame.SRCALPHA)
        véu.fill((4, 1, 13, 224))
        tela.blit(véu, (0, 0))
        tela.blit(textura_fragmentada, (0, 0))
        centro = (largura // 2, int(altura * 0.145))
        pulso = 1 + math.sin(agora * 0.005) * 0.10
        aura_cabecalho = pygame.Surface((largura, altura), pygame.SRCALPHA)
        for r, a in ((74, 18), (52, 32), (31, 62)):
            pygame.draw.circle(aura_cabecalho, (*cor, a), centro, int(r * pulso))
        for i in range(12):
            a = i * math.tau / 12 + agora * 0.00018
            r1, r2 = 22, 48 + (i % 3) * 7
            pygame.draw.line(aura_cabecalho, (*cor2, 155), (centro[0] + math.cos(a) * r1, centro[1] + math.sin(a) * r1), (centro[0] + math.cos(a) * r2, centro[1] + math.sin(a) * r2), 1)
        tela.blit(aura_cabecalho, (0, 0))
        titulo = fonte_titulo.render("FRAGMENTO DA RUPTURA", True, (245, 238, 255))
        tela.blit(titulo, titulo.get_rect(center=(centro[0], int(altura * 0.052))))
        subtitulo = fonte_desc.render(dados.get("nome", "Manifestacao").upper() + " RESPONDE", True, cor)
        tela.blit(subtitulo, subtitulo.get_rect(center=(centro[0], int(altura * 0.245))))

        for i, opcao in enumerate(opcoes):
            rect = cards[i]
            if rect.collidepoint(mouse):
                selecionado = i
            ativo = i == selecionado
            painel = pygame.Surface(rect.size, pygame.SRCALPHA)
            painel.fill((18, 10, 34, 245) if ativo else (10, 7, 22, 225))
            pygame.draw.rect(painel, cor if ativo else (86, 69, 112), painel.get_rect(), 3 if ativo else 1, border_radius=14)
            if ativo:
                pygame.draw.rect(painel, (*cor, 35), (7, 7, card_w - 14, card_h - 14), border_radius=10)
            _desenhar_glifo(painel, (card_w // 2, 70), opcao["indice"], cor2 if ativo else cor, ativo)
            numero = fonte_rodape.render(f"ECO 0{i + 1}", True, cor2 if ativo else (130, 120, 150))
            painel.blit(numero, numero.get_rect(center=(card_w // 2, 118)))
            _texto_wrap(painel, opcao["nome"].upper(), fonte_nome, (250, 246, 255), pygame.Rect(25, 145, card_w - 50, 72), 2)
            pygame.draw.line(painel, (*cor, 150), (25, 222), (card_w - 25, 222), 1)
            _texto_wrap(painel, opcao["descricao"], fonte_desc, (198, 190, 215), pygame.Rect(25, 244, card_w - 50, 120), 5)
            tela.blit(painel, rect)
        rodape = fonte_rodape.render("A/D OU SETAS PARA ESCOLHER   •   ENTER / A PARA FUNDIR", True, (165, 153, 185))
        tela.blit(rodape, rodape.get_rect(center=(largura // 2, int(altura * 0.91))))
        ui_helpers.desenhar_cursor_personalizado(tela, mouse)
        pygame.display.flip()
        if confirmar:
            estado["evolucao"] = opcoes[selecionado]["id"]
            pygame.mouse.set_visible(cursor_visivel_anterior)
            return opcoes[selecionado]
        clock.tick(60)
