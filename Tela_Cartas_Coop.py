import pygame
import sys
import random
import math
import os
from Variaveis import *

def carregar_fonte(caminho, tamanho, fallback_name=None):
    try:
        if os.path.exists(caminho):
            return pygame.font.Font(caminho, tamanho)
    except:
        pass
    return pygame.font.Font(fallback_name, tamanho)

def tela_de_pausa(velocidade_personagem, intervalo_disparo, vida, largura_disparo, altura_disparo, trembo, dano_person_hit, chance_critico, roubo_de_vida, quantidade_roubo_vida,
                  tempo_cooldown_dash, vida_maxima, Petro_active, Resistencia, vida_petro, vida_maxima_petro, dano_petro, xp_petro, petro_evolucao, Resistencia_petro, Chance_Sorte, Poison_Active, Dano_Veneno_Acumulado, Executa_inimigo, Ultimo_Estalo, mostrar_info, Mercenaria_Active, Valor_Bonus, dispositivo_ativo, Tempo_cura,
                  porcentagem_cura, cartas_compradas, pontuacao_exib, max_cartas_compraveis=1, inimigos_eliminados=0):
    
    Rolagens_possiveis = 3
    Rolagens_Dadas = 0
    compras_restantes = max_cartas_compraveis
    DELAY_ENTRE_CARTAS = 220
    ultima_mudanca_de_carta = pygame.time.get_ticks()
    
    pygame.init()
    
    # Sound FX
    try:
        som_tick = pygame.mixer.Sound("Sounds/Estalo.mp3")
        som_tick.set_volume(0.4)
    except:
        som_tick = None
        
    tela = pygame.display.get_surface()
    if tela is None:
        tela = pygame.display.set_mode((largura_tela, altura_tela))
        
    pygame.display.set_caption('Ruptura Temporal - Cards Shop Coop')
    
    # Grid Background Texture
    try:
        background = pygame.image.load("Sprites/Cartas_back.png").convert()
        background = pygame.transform.scale(background, (largura_tela, altura_tela))
        background.set_alpha(75)
    except:
        background = pygame.Surface((largura_tela, altura_tela))
        background.fill((10, 10, 15))
        
    # Fonts
    caminho_fonte_aureas = "Texto/rainyhearts.ttf"
    caminho_fonte_titulo = "Texto/Doctor Glitch.otf"
    
    fonte_glitch = carregar_fonte(caminho_fonte_titulo, 34)
    fonte_glitch_pequena = carregar_fonte(caminho_fonte_titulo, 18)
    fonte_nome = carregar_fonte(caminho_fonte_aureas, 30)
    fonte_desc = carregar_fonte(caminho_fonte_aureas, 20)
    fonte_status = carregar_fonte(caminho_fonte_aureas, 18)
    fonte_instrucao = carregar_fonte(caminho_fonte_aureas, 18)
    
    atributos_cartas = [
        {"nome": "Speed Boost", "Nick": "Vento Celeste", 
         "descricao": "Aumente sua velocidade em +10%. Corra como o vento e fuja de qualquer situacao perigosa."},
        
        {"nome": "Porção", "Nick": "Elixir Vital", 
         "descricao": "Recupere 25% da sua vida maxima e ganhe mais vida maxima permanentemente. Excedente vira vida maxima."},
        
        {"nome": "Disparo crescente", "Nick": "Impacto Escalante", 
         "descricao": "Ganhe +27 de dano e deixe os inimigos temendo seus tiros poderosos."},
        
        {"nome": "Tempestade", "Nick": "Tempestade Crescente", 
         "descricao": "Aumente sua chance critica em 2% e triplique o dano causado. Transforme cada acerto em uma tempestade!"},

        {"nome": "Cura", "Nick": "Mordida Sombria", 
         "descricao": "Toda bala recupera +0.20% da vida perdida. Recupere sua saude proporcionalmente a cada acerto!"},

        {"nome": "Trembo", "Nick": "Reversão Temporal", 
         "descricao": "Quando a morte se aproxima, o tempo volta. Recupere toda a saude e reapareca. Acumular 2 buffa a regeneracao. Se consumida, a regen diminui so 50%."},

        {"nome": "Speed Atack", "Nick": "Fluidez Letal", 
         "descricao": "Aumente a velocidade de ataque em 5%, tornando seus tiros rapidos e letais."},
        
        {"nome": "Teleporte", "Nick": "Salto Espacial", 
         "descricao": "Reduza o cooldown do teleporte em 3%, permitindo que voce se mova rapidamente entre os campos de batalha."},

        {"nome": "Petro", "Nick": "Sentinela Leal", 
         "descricao": "Desencadeie o poder de um pequeno guardiao. Alimente-o para ver seu poder crescer e proteger voce!"},

        {"nome": "Defesa", "Nick": "Escudo Fásico", 
         "descricao": "Aumente sua resistencia em +5 e mitigue os danos dos inimigos. Uma defesa imbatível para cada desafio."},

        {"nome": "Sorte", "Nick": "Anomalia Favorável", 
         "descricao": "Aumente suas chances de obter cartas raras com 0.6% de sorte adicional. A sorte agora esta ao seu favor!"},
         
        {"nome": "Poison", "Nick": "Toxina Temporal", 
         "descricao": "Infunde seus ataques com veneno, causando dano continuo ao longo do tempo aos inimigos atingidos."},
         
        {"nome": "Coletora", "Nick": "Foice do Tempo", 
         "descricao": "Coleta a energia vital de inimigos enfraquecidos, executando-os instantaneamente quando sua vida esta baixa."}
    ]

    cartas_disponiveis = [
        pygame.image.load('Sprites/Deck/Speed_boost1.png'),
        pygame.image.load('Sprites/Deck/carta_por1.png'),
        pygame.image.load('Sprites/Deck/carta_odio1.png'),
        pygame.image.load('Sprites/Deck/Carta_tempestade_crescente1.png'),
        pygame.image.load('Sprites/Deck/Carta_roubo_vida1.png'),
        pygame.image.load('Sprites/Deck/carta_trem1.png'),
        pygame.image.load('Sprites/Deck/carta_onda.png'),
        pygame.image.load('Sprites/Deck/carta_teleporte1.png'),
        pygame.image.load('Sprites/Deck/carta_petro1.png'),
        pygame.image.load('Sprites/Deck/carta_defesa1.png'),
        pygame.image.load('Sprites/Deck/carta_sorte1.png'),
        pygame.image.load('Sprites/Deck/carta_poison1.png'),
        pygame.image.load('Sprites/Deck/carta_estalo1.png')
    ]

    frames_cartas = [
        [pygame.image.load('Sprites/Deck/Speed_boost1.png'), pygame.image.load('Sprites/Deck/Speed_boost2.png')],
        [pygame.image.load('Sprites/Deck/carta_por1.png'), pygame.image.load('Sprites/Deck/carta_por2.png')],
        [pygame.image.load('Sprites/Deck/carta_odio1.png'), pygame.image.load('Sprites/Deck/carta_odio2.png')],
        [pygame.image.load('Sprites/Deck/Carta_tempestade_crescente1.png'), pygame.image.load('Sprites/Deck/Carta_tempestade_crescente2.png')],
        [pygame.image.load('Sprites/Deck/Carta_roubo_vida1.png'), pygame.image.load('Sprites/Deck/Carta_roubo_vida2.png')],
        [pygame.image.load('Sprites/Deck/carta_trem1.png'), pygame.image.load('Sprites/Deck/carta_trem2.png')],
        [pygame.image.load('Sprites/Deck/carta_onda.png'), pygame.image.load('Sprites/Deck/carta_onda2.png')],
        [pygame.image.load('Sprites/Deck/carta_teleporte1.png'), pygame.image.load('Sprites/Deck/carta_teleporte2.png')],
        [pygame.image.load('Sprites/Deck/carta_petro1.png'), pygame.image.load('Sprites/Deck/carta_petro2.png')],
        [pygame.image.load('Sprites/Deck/carta_defesa1.png'), pygame.image.load('Sprites/Deck/carta_defesa2.png')],
        [pygame.image.load('Sprites/Deck/carta_sorte1.png'), pygame.image.load('Sprites/Deck/carta_sorte2.png')],
        [pygame.image.load('Sprites/Deck/carta_poison1.png'), pygame.image.load('Sprites/Deck/carta_poison2.png')],
        [pygame.image.load('Sprites/Deck/carta_estalo1.png'), pygame.image.load('Sprites/Deck/carta_estalo2.png')]
    ]

    CARD_THEMES = {
        "Speed Boost":       {"cor_tema": (0, 255, 200),   "bg_tema": (8, 24, 36),   "categoria": "MOBILIDADE TEMPORAL",     "lore": "O vento corre rapido, mas voce deve correr ainda mais rapido que o proprio tempo."},
        "Porção":            {"cor_tema": (255, 60, 100),  "bg_tema": (36, 8, 12),   "categoria": "SUPORTE E ELIXIR VITAL",  "lore": "Uma gota de pura energia vital extraida de linhas temporais estaveis."},
        "Disparo crescente": {"cor_tema": (255, 100, 0),   "bg_tema": (36, 16, 8),   "categoria": "POTÊNCIA DE COMBATE",     "lore": "Deixe cada projetil carregar o peso do colapso temporal."},
        "Tempestade":        {"cor_tema": (138, 43, 226),  "bg_tema": (20, 8, 36),   "categoria": "ANOMALIA CRÍTICA",        "lore": "O caos atmosferico canalizado em disparos de precisao quantica."},
        "Cura":              {"cor_tema": (50, 205, 50),   "bg_tema": (8, 36, 12),   "categoria": "REGENERAÇÃO E SUSTENTO",   "lore": "Drene a forca vital dos oponentes para restaurar sua integridade."},
        "Trembo":            {"cor_tema": (0, 191, 255),   "bg_tema": (8, 20, 36),   "categoria": "SOBREVIVÊNCIA CAUSAL",    "lore": "A morte e apenas um contratempo em um loop perfeitamente controlado."},
        "Speed Atack":       {"cor_tema": (255, 215, 0),   "bg_tema": (36, 30, 8),   "categoria": "FLUIDEZ DE DISPAROS",     "lore": "Acelere sua frequencia temporal ate seus tiros virarem um borrao continuo."},
        "Teleporte":         {"cor_tema": (255, 0, 255),   "bg_tema": (36, 8, 30),   "categoria": "MANIPULAÇÃO ESPACIAL",    "lore": "Dobre o espaco para estar exatamente onde o inimigo nao espera."},
        "Petro":             {"cor_tema": (0, 255, 255),   "bg_tema": (8, 32, 32),   "categoria": "CONSTRUCTO TEMPORAL",     "lore": "Um guardiao leal que se alimenta de energia e lealdade ancestral."},
        "Defesa":            {"cor_tema": (192, 192, 192), "bg_tema": (24, 24, 28),  "categoria": "RESISTÊNCIA FÁSICA",      "lore": "Aumente a densidade do seu campo de forca contra impactos nocivos."},
        "Sorte":             {"cor_tema": (255, 182, 193), "bg_tema": (32, 16, 24),  "categoria": "PROBABILIDADE FAVORÁVEL", "lore": "Altere as probabilidades de eventos quanticos a seu favor."},
        "Poison":            {"cor_tema": (173, 255, 47),  "bg_tema": (16, 32, 12),  "categoria": "TOXINA DE ALTA ESCALA",    "lore": "Uma toxina que envelhece aceleradamente as celulas de quem a toca."},
        "Coletora":          {"cor_tema": (220, 20, 60),   "bg_tema": (36, 8, 16),   "categoria": "CEIFADOR E EXECUÇÃO",     "lore": "O ceifador nao espera por aqueles que ja estao a beira do abismo."}
    }

    largura_carta = 150
    altura_carta = 200
    cartas_disponiveis = [pygame.transform.scale(carta, (largura_carta, altura_carta)) for carta in cartas_disponiveis]
    frames_cartas = [[pygame.transform.scale(frame, (largura_carta, altura_carta)) for frame in frames] for frames in frames_cartas]

    cartas = []
    for i, carta_img in enumerate(cartas_disponiveis):
        carta = {"imagem": carta_img, "frames_animacao": frames_cartas[i], "frame_atual": 0}
        carta.update(atributos_cartas[i])
        cartas.append(carta)

    def obter_cartas_disponiveis(cartas, cartas_compradas, qtd=3):
        rare_names = {"Trembo", "Petro", "Poison", "Coletora"}
        
        # pool preference for unbought cards
        pool_nao_compradas = [c for c in cartas if cartas_compradas.get(c["nome"], 0) == 0]
        pool_compradas = [c for c in cartas if cartas_compradas.get(c["nome"], 0) > 0]
        
        # Partition
        rares_pref = [c for c in pool_nao_compradas if c["nome"] in rare_names]
        commons_pref = [c for c in pool_nao_compradas if c["nome"] not in rare_names]
        
        rares_fallback = [c for c in pool_compradas if c["nome"] in rare_names]
        commons_fallback = [c for c in pool_compradas if c["nome"] not in rare_names]
        
        selecionadas = []
        
        # Apply 10% rare drop rate floor if player has 15 or more Sorte cards
        sorte_count = cartas_compradas.get("Sorte", 0)
        chance_efetiva = max(Chance_Sorte, 0.10) if sorte_count >= 15 else Chance_Sorte
        
        def pop_card(rares, commons):
            if not rares and not commons:
                return None
            if rares and (not commons or random.random() < chance_efetiva):
                choice = random.choice(rares)
                rares.remove(choice)
                return choice
            else:
                choice = random.choice(commons)
                commons.remove(choice)
                return choice
                
        for _ in range(qtd):
            card = pop_card(rares_pref, commons_pref)
            if card:
                selecionadas.append(card)
            else:
                card = pop_card(rares_fallback, commons_fallback)
                if card:
                    selecionadas.append(card)
                    
        return selecionadas

    cartas_selecionadas = obter_cartas_disponiveis(cartas, cartas_compradas, 3)
    carta_selecionada_index = 0
    
    # Particle System
    particulas = []
    for _ in range(40):
        particulas.append({
            "x": random.randint(0, largura_tela),
            "y": random.randint(0, altura_tela),
            "vel_y": random.uniform(-1.5, -0.4),
            "tamanho": random.uniform(2.0, 5.0),
            "alpha": random.randint(50, 200),
            "breathe_speed": random.uniform(0.02, 0.05),
            "breathe_dir": 1
        })

    # LERP Animation Variables
    initial_theme = CARD_THEMES.get(cartas_selecionadas[0]["nome"], {"bg_tema": (20, 20, 25)})
    cor_fundo_atual = list(initial_theme["bg_tema"])
    
    card_x = [largura_tela // 2 for _ in range(3)]
    card_scale = [0.85 for _ in range(3)]
    card_y_offset = [20 for _ in range(3)]
    card_alpha = [100 for _ in range(3)]

    contador_animacao = 0
    fps_animacao = 30
    clock = pygame.time.Clock()

    # Animation variables for the futuristic bracelet animation
    animando_compra = False
    tempo_inicio_animacao = 0
    carta_animada = None
    pos_inicial_animacao = (0, 0)
    escala_inicial_animacao = 1.0

    def aplicar_carta(carta_sel):
        nonlocal velocidade_personagem, intervalo_disparo, vida, dano_person_hit, chance_critico, roubo_de_vida, quantidade_roubo_vida
        nonlocal tempo_cooldown_dash, vida_maxima, Petro_active, Resistencia, vida_petro, vida_maxima_petro, dano_petro, xp_petro
        nonlocal petro_evolucao, Resistencia_petro, Chance_Sorte, Poison_Active, Dano_Veneno_Acumulado, Executa_inimigo, Ultimo_Estalo
        nonlocal Mercenaria_Active, Valor_Bonus, Tempo_cura, porcentagem_cura, compras_restantes, cartas_selecionadas, trembo
        
        nome = carta_sel["nome"]
        if nome == "Speed Boost":
            velocidade_personagem += 0.035 + (inimigos_eliminados // 50) * 0.005
            cartas_compradas["Speed Boost"] += 1
        elif nome == "Porção":
            vida += int(vida_maxima * 0.45 + (inimigos_eliminados // 30) * 0.05)
            if vida > vida_maxima:
                vida_maxima = vida
            vida_petro += int(vida_maxima_petro * 0.30 + (inimigos_eliminados // 40) * 0.03)
            if vida_petro > vida_maxima_petro:
                vida_maxima_petro = vida_petro
            cartas_compradas["Porção"] += 1
        elif nome == "Disparo crescente":
            dano_person_hit += 27 + (inimigos_eliminados // 50) * 10
            cartas_compradas["Disparo crescente"] += 1
        elif nome == "Trembo":
            trembo = True
            cartas_compradas["Trembo"] += 1
            if cartas_compradas["Trembo"] >= 2:
                Tempo_cura = max(500, int(Tempo_cura * 0.75))
                porcentagem_cura += 0.005 + (inimigos_eliminados // 100) * 0.001
            else:
                Tempo_cura -= Tempo_cura * 0.05
                porcentagem_cura += 0.001 + (inimigos_eliminados // 100) * 0.0005
        elif nome == "Tempestade":
            dano_person_hit += 10 + (inimigos_eliminados // 50) * 4
            chance_critico += 0.02 + (inimigos_eliminados // 100) * 0.005
            cartas_compradas["Tempestade"] += 1
        elif nome == "Cura":
            # Coop balance values
            roubo_de_vida = 1.0
            quantidade_roubo_vida += 0.002 + (inimigos_eliminados // 80) * 0.0005
            cartas_compradas["Cura"] += 1
        elif nome == "Speed Atack":
            intervalo_disparo -= 20 + (inimigos_eliminados // 100) * 5
            if intervalo_disparo < 50:
                intervalo_disparo = 50
            cartas_compradas["Speed Atack"] += 1
        elif nome == "Teleporte":
            tempo_cooldown_dash -= tempo_cooldown_dash * 0.003 + (inimigos_eliminados // 50) * 0.0005
            if tempo_cooldown_dash < 0.5:
                tempo_cooldown_dash = 0.5
            cartas_compradas["Teleporte"] += 1
        elif nome == "Petro":
            Petro_active = True
            dano_petro += 2 + (inimigos_eliminados // 30) * 1
            if 0 < petro_evolucao <= 8:
                xp_petro = "nivel_1"
                petro_evolucao += 4
            elif 8 < petro_evolucao <= 16:
                xp_petro = "nivel_2"
                vida_maxima_petro += 1000
                petro_evolucao += 4
            elif petro_evolucao > 16:
                xp_petro = "nivel_3"
                vida_maxima_petro += 2000
                Resistencia_petro += 18
                dano_petro += 250
            if vida_petro < vida_maxima_petro:
                vida_petro += int(vida_maxima_petro * 0.45)
            if vida_petro > vida_maxima_petro:
                vida_maxima_petro = vida_petro
            cartas_compradas["Petro"] += 1
        elif nome == "Defesa":
            Resistencia += 3.5 + (inimigos_eliminados // 50) * 0.5
            if Resistencia > 50:
                Resistencia = 50
            cartas_compradas["Defesa"] += 1
        elif nome == "Sorte":
            Chance_Sorte += 0.006
            cartas_compradas["Sorte"] += 1
        elif nome == "Poison":
            Poison_Active = True
            Dano_Veneno_Acumulado += 0.05
            cartas_compradas["Poison"] += 1
        elif nome == "Coletora":
            Executa_inimigo += 0.005
            Ultimo_Estalo = True
            cartas_compradas["Coletora"] += 1
        elif nome == "Mercenaria":
            Mercenaria_Active = True
            Valor_Bonus += 25
            cartas_compradas["Coletora"] += 1

        compras_restantes -= 1
        if compras_restantes > 0:
            cartas_selecionadas = obter_cartas_disponiveis(cartas, cartas_compradas, 3)

    while compras_restantes > 0:
        agora = pygame.time.get_ticks()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if animando_compra:
                continue

            elif evento.type == pygame.KEYDOWN:
                anterior = carta_selecionada_index
                if evento.key in [pygame.K_a, pygame.K_LEFT]:
                    carta_selecionada_index = (carta_selecionada_index - 1) % 3
                elif evento.key in [pygame.K_d, pygame.K_RIGHT]:
                    carta_selecionada_index = (carta_selecionada_index + 1) % 3
                elif evento.key in [pygame.K_SPACE, pygame.K_RETURN]:
                    if som_tick:
                        som_tick.play()
                    # Trigger bracelet animation
                    animando_compra = True
                    tempo_inicio_animacao = agora
                    carta_animada = cartas_selecionadas[carta_selecionada_index]
                    
                    curr_scale = card_scale[carta_selecionada_index]
                    w_scaled = int(largura_carta * curr_scale)
                    h_scaled = int(altura_carta * curr_scale)
                    x_pos = int(card_x[carta_selecionada_index] - w_scaled // 2)
                    y_pos = int(altura_tela // 2.5 + card_y_offset[carta_selecionada_index] - h_scaled // 2)
                    pos_inicial_animacao = (x_pos + w_scaled // 2, y_pos + h_scaled // 2)
                    escala_inicial_animacao = curr_scale
                    
                elif Rolagens_possiveis > Rolagens_Dadas and evento.key == pygame.K_q:
                    if som_tick:
                        som_tick.play()
                    Rolagens_Dadas += 1
                    cartas_selecionadas = obter_cartas_disponiveis(cartas, cartas_compradas, 3)
                    
                if carta_selecionada_index != anterior and som_tick:
                    som_tick.play()
                    
            elif evento.type == pygame.JOYAXISMOTION:
                if evento.axis == 0:
                    if agora - ultima_mudanca_de_carta >= DELAY_ENTRE_CARTAS:
                        anterior = carta_selecionada_index
                        if evento.value < -0.5:
                            carta_selecionada_index = (carta_selecionada_index - 1) % 3
                            ultima_mudanca_de_carta = agora
                        elif evento.value > 0.5:
                            carta_selecionada_index = (carta_selecionada_index + 1) % 3
                            ultima_mudanca_de_carta = agora
                        if carta_selecionada_index != anterior and som_tick:
                            som_tick.play()
                            
            elif evento.type == pygame.JOYBUTTONDOWN:
                if evento.button == 0:  # Xbox Button A
                    if som_tick:
                        som_tick.play()
                    # Trigger bracelet animation
                    animando_compra = True
                    tempo_inicio_animacao = agora
                    carta_animada = cartas_selecionadas[carta_selecionada_index]
                    
                    curr_scale = card_scale[carta_selecionada_index]
                    w_scaled = int(largura_carta * curr_scale)
                    h_scaled = int(altura_carta * curr_scale)
                    x_pos = int(card_x[carta_selecionada_index] - w_scaled // 2)
                    y_pos = int(altura_tela // 2.5 + card_y_offset[carta_selecionada_index] - h_scaled // 2)
                    pos_inicial_animacao = (x_pos + w_scaled // 2, y_pos + h_scaled // 2)
                    escala_inicial_animacao = curr_scale
                    
                elif Rolagens_possiveis > Rolagens_Dadas and evento.button == 3:  # Xbox Button Y (Reroll)
                    if som_tick:
                        som_tick.play()
                    Rolagens_Dadas += 1
                    cartas_selecionadas = obter_cartas_disponiveis(cartas, cartas_compradas, 3)

        # Update animation progress
        if animando_compra:
            decorrido = agora - tempo_inicio_animacao
            progress = min(1.0, decorrido / 300.0)
            
            # Target bracelet position is center of the screen
            target_pos = (largura_tela // 2, altura_tela // 2 - 50)
            
            current_x = pos_inicial_animacao[0] + (target_pos[0] - pos_inicial_animacao[0]) * progress
            current_y = pos_inicial_animacao[1] + (target_pos[1] - pos_inicial_animacao[1]) * progress
            current_scale = escala_inicial_animacao * (1.0 - progress)
            angulo = progress * 360 * 2
            
            if progress >= 1.0:
                animando_compra = False
                aplicar_carta(carta_animada)

        # 1. Background color interpolation
        sel_card_name = cartas_selecionadas[carta_selecionada_index]["nome"]
        theme_sel = CARD_THEMES.get(sel_card_name, {"cor_tema": (0, 255, 200), "bg_tema": (20, 20, 25), "categoria": "MELHORIA", "lore": ""})
        bg_alvo = theme_sel["bg_tema"]
        for c in range(3):
            cor_fundo_atual[c] += (bg_alvo[c] - cor_fundo_atual[c]) * 0.08
        tela.fill((int(cor_fundo_atual[0]), int(cor_fundo_atual[1]), int(cor_fundo_atual[2])))
        
        # 2. Draw Cartas_back grid texture with low opacity
        tela.blit(background, (0, 0))
        
        # 3. Dynamic Upward Particles
        cor_accent = theme_sel["cor_tema"]
        for p in particulas:
            p["y"] += p["vel_y"]
            if p["y"] < -10:
                p["y"] = altura_tela + 10
                p["x"] = random.randint(0, largura_tela)
                
            p["alpha"] += p["breathe_dir"] * p["breathe_speed"] * 50
            if p["alpha"] >= 255:
                p["alpha"] = 255
                p["breathe_dir"] = -1
            elif p["alpha"] <= 40:
                p["alpha"] = 40
                p["breathe_dir"] = 1
                
            cor_part = cor_accent + (int(p["alpha"]),)
            surf_p = pygame.Surface((int(p["tamanho"]*2), int(p["tamanho"]*2)), pygame.SRCALPHA)
            pygame.draw.circle(surf_p, cor_part, (int(p["tamanho"]), int(p["tamanho"])), int(p["tamanho"]))
            tela.blit(surf_p, (int(p["x"] - p["tamanho"]), int(p["y"] - p["tamanho"])))

        # 4. Status HUD Panel (Top)
        hud_w = 640
        hud_h = 55
        hud_x = (largura_tela - hud_w) // 2
        hud_y = 35
        
        pygame.draw.rect(tela, (12, 12, 18, 210), (hud_x, hud_y, hud_w, hud_h), border_radius=12)
        pygame.draw.rect(tela, cor_accent + (120,), (hud_x, hud_y, hud_w, hud_h), width=1, border_radius=12)
        
        text_compras = f"COMPRAS RESTANTES: {compras_restantes}"
        text_rerolls = f"REROLLS DISPONIVEIS: {Rolagens_possiveis - Rolagens_Dadas}"
        
        render_compras = fonte_glitch_pequena.render(text_compras, True, (255, 255, 255))
        render_rerolls = fonte_glitch_pequena.render(text_rerolls, True, cor_accent)
        
        tela.blit(render_compras, (hud_x + 35, hud_y + (hud_h - render_compras.get_height()) // 2))
        tela.blit(render_rerolls, (hud_x + hud_w - render_rerolls.get_width() - 35, hud_y + (hud_h - render_rerolls.get_height()) // 2))

        # 5. Card Carousel Position and Scale LERP
        for i in range(3):
            dist = i - carta_selecionada_index
            target_x = largura_tela // 2 + dist * (largura_carta + 110)
            
            if i == carta_selecionada_index:
                target_scale = 1.15
                target_y_offset = -25
                target_alpha = 255
            else:
                target_scale = 0.85
                target_y_offset = 15
                target_alpha = 100
                
            card_x[i] += (target_x - card_x[i]) * 0.12
            card_scale[i] += (target_scale - card_scale[i]) * 0.12
            card_y_offset[i] += (target_y_offset - card_y_offset[i]) * 0.12
            card_alpha[i] += (target_alpha - card_alpha[i]) * 0.12

        # 6. Render Card Carousel
        for i, carta in enumerate(cartas_selecionadas):
            if animando_compra and carta == carta_animada:
                continue

            curr_scale = card_scale[i]
            w_scaled = int(largura_carta * curr_scale)
            h_scaled = int(altura_carta * curr_scale)
            x_pos = int(card_x[i] - w_scaled // 2)
            y_pos = int(altura_tela // 2.5 + card_y_offset[i] - h_scaled // 2)
            
            # Temporary Surface with Alpha
            surf_card = pygame.Surface((w_scaled, h_scaled), pygame.SRCALPHA)
            
            # Glassmorphic Card Background
            alpha_fundo = int(45 + (card_alpha[i] / 255.0) * 115)
            pygame.draw.rect(surf_card, (20, 20, 25, alpha_fundo), (0, 0, w_scaled, h_scaled), border_radius=12)
            
            # Draw frame
            frame = carta["frames_animacao"][carta["frame_atual"]]
            img_scaled = pygame.transform.scale(frame, (w_scaled - 12, h_scaled - 12))
            
            surf_img_alpha = pygame.Surface(img_scaled.get_size(), pygame.SRCALPHA)
            surf_img_alpha.blit(img_scaled, (0, 0))
            surf_img_alpha.fill((255, 255, 255, int(card_alpha[i])), special_flags=pygame.BLEND_RGBA_MULT)
            surf_card.blit(surf_img_alpha, (6, 6))
            
            # Border
            card_theme = CARD_THEMES.get(carta["nome"], {"cor_tema": (0, 255, 200)})
            cor_borda = card_theme["cor_tema"] + (int(card_alpha[i]),)
            largura_linha = 3 if i == carta_selecionada_index else 1
            pygame.draw.rect(surf_card, cor_borda, (0, 0, w_scaled, h_scaled), width=largura_linha, border_radius=12)
            
            # Glow concentrico
            if i == carta_selecionada_index:
                pulsar = (math.sin(agora * 0.005) + 1) / 2
                for g in range(1, 5):
                    glow_alpha = int((1.0 - g/5.0) * (80 + pulsar * 40))
                    glow_color = card_theme["cor_tema"] + (glow_alpha,)
                    glow_surf = pygame.Surface((w_scaled + g*4, h_scaled + g*4), pygame.SRCALPHA)
                    pygame.draw.rect(glow_surf, glow_color, (0, 0, w_scaled + g*4, h_scaled + g*4), width=1, border_radius=12 + g)
                    tela.blit(glow_surf, (x_pos - g*2, y_pos - g*2))
                    
            tela.blit(surf_card, (x_pos, y_pos))
            
            # Draw Nick/Name text on the card surface
            # Scaled name font
            fonte_card_nick = carregar_fonte(caminho_fonte_aureas, int(15 * curr_scale))
            render_card_nick = fonte_card_nick.render(carta["Nick"], True, (0, 0, 0))
            # Outline/Shadow on card
            tela.blit(render_card_nick, (x_pos + w_scaled // 2 - render_card_nick.get_width() // 2, y_pos + h_scaled // 1.4))

        # Update card frame animation
        contador_animacao += 1
        if contador_animacao >= fps_animacao:
            contador_animacao = 0
            for c_sel in cartas_selecionadas:
                c_sel["frame_atual"] = (c_sel["frame_atual"] + 1) % 2

        # 7. Inventory Bar (Badges of purchased cards)
        adquiridas = [(n, q) for n, q in cartas_compradas.items() if q > 0]
        if len(adquiridas) > 0:
            badge_w = 40
            badge_h = 40
            spacing_badge = 10
            total_w = len(adquiridas) * badge_w + (len(adquiridas) - 1) * spacing_badge
            start_x = (largura_tela - total_w) // 2
            y_badge = 105
            
            pygame.draw.rect(tela, (10, 10, 15, 120), (start_x - 8, y_badge - 4, total_w + 16, badge_h + 8), border_radius=6)
            
            for idx, (nome, quantidade) in enumerate(adquiridas):
                bx = start_x + idx * (badge_w + spacing_badge)
                img_badge = pygame.transform.scale(cartas_imagens[nome], (badge_w, badge_h))
                tela.blit(img_badge, (bx, y_badge))
                
                # Small badge owned count overlay
                render_qtd = fonte_glitch_pequena.render(f"{quantidade}", True, (255, 255, 255))
                pygame.draw.rect(tela, (10, 10, 15, 200), (bx + badge_w - 14, y_badge + badge_h - 14, 14, 14), border_radius=3)
                tela.blit(render_qtd, (bx + badge_w - 11, y_badge + badge_h - 13))

        # 8. Descriptive Glassmorphic Panel (Bottom)
        carta_sel = cartas_selecionadas[carta_selecionada_index]
        largura_painel = largura_tela - 160
        altura_painel = 160
        x_painel = 80
        y_painel = altura_tela - altura_painel - 80
        
        surf_painel = pygame.Surface((largura_painel, altura_painel), pygame.SRCALPHA)
        # Background
        pygame.draw.rect(surf_painel, (12, 12, 18, 220), (0, 0, largura_painel, altura_painel), border_radius=16)
        # Shiny border
        cor_borda_p = theme_sel["cor_tema"] + (180,)
        pygame.draw.rect(surf_painel, cor_borda_p, (0, 0, largura_painel, altura_painel), width=2, border_radius=16)
        
        # Name
        render_nome = fonte_nome.render(carta_sel["nome"].upper(), True, theme_sel["cor_tema"])
        surf_painel.blit(render_nome, (24, 16))
        
        # Nickname
        render_nick = fonte_desc.render(f'"{carta_sel["Nick"].upper()}"', True, (255, 255, 255))
        surf_painel.blit(render_nick, (24 + render_nome.get_width() + 15, 22))
        
        # Category
        render_cat = fonte_status.render(theme_sel["categoria"], True, (150, 150, 150))
        surf_painel.blit(render_cat, (26, 48))
        
        # Vertical Divider
        x_divisor = largura_painel // 2 + 50
        pygame.draw.line(surf_painel, (50, 50, 60, 120), (x_divisor, 16), (x_divisor, altura_painel - 16), 1)
        
        # Description wrapping on left
        palabras = carta_sel["descricao"].split(' ')
        linhas_desc = []
        linha_atual = []
        largura_limite = x_divisor - 48
        for palavra in palabras:
            test_linha = ' '.join(linha_atual + [palavra])
            if fonte_desc.size(test_linha)[0] <= largura_limite:
                linha_atual.append(palavra)
            else:
                linhas_desc.append(' '.join(linha_atual))
                linha_atual = [palavra]
        if linha_atual:
            linhas_desc.append(' '.join(linha_atual))
            
        y_desc = 76
        for linha in linhas_desc:
            render_linha = fonte_desc.render(linha, True, (230, 230, 230))
            surf_painel.blit(render_linha, (24, y_desc))
            y_desc += 22
            
        # Lore/Quote on right
        lore_txt = theme_sel["lore"]
        palabras_lore = lore_txt.split(' ')
        linhas_lore = []
        linha_atual_lore = []
        largura_limite_lore = largura_painel - x_divisor - 48
        for palavra in palabras_lore:
            test_linha = ' '.join(linha_atual_lore + [palavra])
            if fonte_status.size(test_linha)[0] <= largura_limite_lore:
                linha_atual_lore.append(palavra)
            else:
                linhas_lore.append(' '.join(linha_atual_lore))
                linha_atual_lore = [palavra]
        if linha_atual_lore:
            linhas_lore.append(' '.join(linha_atual_lore))
            
        y_lore = 45
        for linha in linhas_lore:
            render_linha = fonte_status.render(linha, True, (130, 130, 140))
            surf_painel.blit(render_linha, (x_divisor + 24, y_lore))
            y_lore += 20
            
        # Current Count owned in panel
        qtd = cartas_compradas.get(carta_sel["nome"], 0)
        render_qtd = fonte_status.render(f"POSSUIDO NO DECK: {qtd}", True, theme_sel["cor_tema"])
        surf_painel.blit(render_qtd, (x_divisor + 24, 16))
        
        tela.blit(surf_painel, (x_painel, y_painel))

        # 9. Draw Bracelet and Flying Card if animating
        if animando_compra:
            color_hologram = theme_sel["cor_tema"]
            target_pos = (largura_tela // 2, altura_tela // 2 - 50)
            
            # Holographic bracelet circle
            bracelet_surf = pygame.Surface((200, 200), pygame.SRCALPHA)
            pygame.draw.circle(bracelet_surf, color_hologram + (int(60 * progress),), (100, 100), int(45 * progress))
            pygame.draw.circle(bracelet_surf, color_hologram + (int(120 * progress),), (100, 100), int(30 * progress), width=2)
            
            # Tech rings rotating
            angulo_ring = agora * 0.01
            for r in range(1, 4):
                radius = int(35 + r * 15)
                pygame.draw.circle(bracelet_surf, color_hologram + (int(80 * progress),), (100, 100), radius, width=1)
                
                # Tech ticks
                for angle_offset in range(0, 360, 45):
                    rad = math.radians(angle_offset + (angulo_ring * (1 if r % 2 == 0 else -1) * 50))
                    tx = int(100 + math.cos(rad) * radius)
                    ty = int(100 + math.sin(rad) * radius)
                    pygame.draw.circle(bracelet_surf, (255, 255, 255, int(180 * progress)), (tx, ty), 2)
                    
            tela.blit(bracelet_surf, (target_pos[0] - 100, target_pos[1] - 100))
            
            # Flying, rotating and scaling card
            w_anim = int(largura_carta * current_scale)
            h_anim = int(altura_carta * current_scale)
            if w_anim > 0 and h_anim > 0:
                frame_anim = carta_animada["frames_animacao"][carta_animada["frame_atual"]]
                img_anim = pygame.transform.scale(frame_anim, (w_anim, h_anim))
                rotated_img = pygame.transform.rotate(img_anim, angulo)
                
                surf_anim_alpha = pygame.Surface(rotated_img.get_size(), pygame.SRCALPHA)
                surf_anim_alpha.blit(rotated_img, (0, 0))
                surf_anim_alpha.fill((255, 255, 255, int(255 * (1.0 - progress))), special_flags=pygame.BLEND_RGBA_MULT)
                tela.blit(surf_anim_alpha, (int(current_x - surf_anim_alpha.get_width() // 2), int(current_y - surf_anim_alpha.get_height() // 2)))

        # 10. Instruction Footer Bar
        texto_instr = "A / D ou SETAS para navegar | ESPACO para selecionar | Q para Reroll"
        render_instr_text = fonte_instrucao.render(texto_instr, True, cor_accent)
        largura_instr = render_instr_text.get_width() + 40
        altura_instr = 30
        
        surf_instr = pygame.Surface((largura_instr, altura_instr), pygame.SRCALPHA)
        pygame.draw.rect(surf_instr, (12, 12, 18, 200), (0, 0, largura_instr, altura_instr), border_radius=6)
        pygame.draw.rect(surf_instr, cor_accent + (80,), (0, 0, largura_instr, altura_instr), width=1, border_radius=6)
        surf_instr.blit(render_instr_text, (20, (altura_instr - render_instr_text.get_height()) // 2))
        
        tela.blit(surf_instr, (largura_tela // 2 - largura_instr // 2, altura_tela - 40))

        pygame.display.flip()
        clock.tick(60)

    return [velocidade_personagem, intervalo_disparo, vida, largura_disparo, altura_disparo, trembo, dano_person_hit, chance_critico, roubo_de_vida,
            quantidade_roubo_vida, tempo_cooldown_dash, vida_maxima, Petro_active, Resistencia, vida_petro, vida_maxima_petro, dano_petro, xp_petro, petro_evolucao, Resistencia_petro,
            Chance_Sorte, Poison_Active, Dano_Veneno_Acumulado, Executa_inimigo, Ultimo_Estalo, Mercenaria_Active, Valor_Bonus, dispositivo_ativo, Tempo_cura, porcentagem_cura, cartas_compradas, pontuacao_exib]
