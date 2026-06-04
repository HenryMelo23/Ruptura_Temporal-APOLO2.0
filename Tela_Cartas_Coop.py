import pygame
import sys
import random
import math
import os
import ui_helpers
from Variaveis import *

def carregar_fonte(caminho, tamanho, fallback_name=None):
    try:
        if os.path.exists(caminho):
            return pygame.font.Font(caminho, tamanho)
    except:
        pass
    return pygame.font.Font(fallback_name, tamanho)

def obter_tela_loja():
    try:
        from ui_helpers import obter_superficie_palco
        tela_palco = obter_superficie_palco()
        if tela_palco is not None:
            return tela_palco
    except Exception:
        pass

    tela_atual = pygame.display.get_surface()
    if tela_atual is not None:
        return tela_atual
    return pygame.display.set_mode((largura_tela, altura_tela))

def tela_de_pausa(velocidade_personagem, intervalo_disparo, vida, largura_disparo, altura_disparo, trembo, dano_person_hit, chance_critico, roubo_de_vida, quantidade_roubo_vida,
                  tempo_cooldown_dash, vida_maxima, Petro_active, Resistencia, vida_petro, vida_maxima_petro, dano_petro, xp_petro, petro_evolucao, Resistencia_petro, Chance_Sorte, Poison_Active, Dano_Veneno_Acumulado, Executa_inimigo, Ultimo_Estalo, mostrar_info, Mercenaria_Active, Valor_Bonus, dispositivo_ativo, Tempo_cura,
                  porcentagem_cura, cartas_compradas, pontuacao_exib, max_cartas_compraveis=1, inimigos_eliminados=0):
    
    cartas_compradas.setdefault("Mercenaria", 0)

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
        
    tela = obter_tela_loja()
    largura_tela, altura_tela = tela.get_size()
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(False)
        
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
         "descricao": "Aumenta a velocidade de movimento de Apolo em +0.035 (escala +0.005 a cada 50 abates na partida)."},
        
        {"nome": "Porção", "Nick": "Elixir Vital", 
         "descricao": "Cura Apolo em 45% da vida maxima e Petro em 30% da vida maxima (escala com abates). Cura excedente aumenta permanentemente a vida maxima de ambos."},
        
        {"nome": "Disparo crescente", "Nick": "Impacto Escalante", 
         "descricao": "Aumenta o dano de ataque basico de Apolo em +13.5 (escala com +5 a cada 50 abates na partida)."},
        
        {"nome": "Tempestade", "Nick": "Tempestade Crescente", 
         "descricao": "Aumenta a chance critica de Apolo em +2% (escala +0.5% a cada 100 abates) e o dano basico em +5 (escala +2 a cada 100 abates)."},

        {"nome": "Cura", "Nick": "Mordida Sombria", 
         "descricao": "Ativa Roubo de Vida. Cada acerto de projetil cura +0.20% da vida perdida de Apolo (a porcentagem de roubo de vida escala em +0.05% a cada 80 abates)."},

        {"nome": "Trembo", "Nick": "Reversão Temporal", 
         "descricao": "Ao sofrer dano fatal, revive Apolo com vida cheia. Concede bonus de regeneracao passiva (-5% de intervalo, +0.1% de cura). Acumular 2 Trembos melhora a regeneracao (-25% intervalo, +0.5% cura). Ao reviver, consome o companheiro e retem 50% dos bonus de regeneracao."},

        {"nome": "Speed Atack", "Nick": "Fluidez Letal", 
         "descricao": "Aumenta a cadencia de disparo reduzindo o intervalo em -20ms (escala em -5ms a cada 100 abates). O intervalo minimo permitido e de 50ms."},
        
        {"nome": "Teleporte", "Nick": "Salto Espacial", 
         "descricao": "Reduz o tempo de recarga do Teleporte em 0.3% do valor atual (reducao extra de 0.05% a cada 50 abates). Recarga minima de 0.5s."},

        {"nome": "Petro", "Nick": "Sentinela Leal", 
         "descricao": "Invoca a sentinela Petro. Compras adicionais aumentam seu dano basico em +2 (escala com abates), curam Petro em 45% de sua vida e o evoluem em ate 3 niveis (ganhando bonus de vida max, resistencia e dano)."},

        {"nome": "Defesa", "Nick": "Escudo Fásico", 
         "descricao": "Aumenta a resistencia de Apolo em +3.5 (escala +0.5 a cada 50 abates). A reducao maxima de dano por resistencia e de 50."},

        {"nome": "Sorte", "Nick": "Anomalia Favorável", 
         "descricao": "Aumenta a Sorte de Apolo em +0.3%, elevando a probabilidade de encontrar cartas e drops de maior raridade."},
         
        {"nome": "Poison", "Nick": "Toxina Temporal", 
         "descricao": "Ataques aplicam veneno por 2 segundos. Cada acúmulo desta carta aumenta o dano do veneno por segundo em +0.5% da vida máxima do inimigo."},
         
        {"nome": "Coletora", "Nick": "Foice do Tempo", 
         "descricao": f"Executa inimigos comuns abaixo do limiar de vida (inicia em 5%, aumenta +0.5% por compra). Contra chefes, o limiar e reduzido a 20% do normal e limitado ao teto de 1.5%. Cada compra tambem aumenta a armadura do chefe em +0.4%."},

        {"nome": "Mercenaria", "Nick": "Contrato de Guerra",
         "descricao": f"Ativa combo de pontos. A cada 5 abates consecutivos na partida, concede um bonus adicional de +25 pontos na pontuacao."}
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
        pygame.image.load('Sprites/Deck/carta_estalo1.png'),
        pygame.image.load('Sprites/Deck/carta_mercenaria1.png')
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
        [pygame.image.load('Sprites/Deck/carta_estalo1.png'), pygame.image.load('Sprites/Deck/carta_estalo2.png')],
        [pygame.image.load('Sprites/Deck/carta_mercenaria1.png'), pygame.image.load('Sprites/Deck/carta_mercenaria2.png')]
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
        "Coletora":          {"cor_tema": (220, 20, 60),   "bg_tema": (36, 8, 16),   "categoria": "CEIFADOR E EXECUÇÃO",     "lore": "O ceifador nao espera por aqueles que ja estao a beira do abismo."},
        "Mercenaria":        {"cor_tema": (255, 180, 40),  "bg_tema": (34, 22, 8),   "categoria": "COMBO E PONTUAÇÃO",       "lore": "Toda queda vira contrato. Todo contrato bem cumprido paga mais caro."}
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
        rare_names = CARTAS_RARAS
        rares = [c for c in cartas if c["nome"] in rare_names]
        commons = [c for c in cartas if c["nome"] not in rare_names]
        
        selecionadas = []

        chance_efetiva = chance_carta_rara(Chance_Sorte, cartas_compradas)

        def pop_random(pool):
            if not pool:
                return None
            choice = random.choice(pool)
            pool.remove(choice)
            return choice

        def pop_rare():
            return pop_random(rares)

        def pop_common():
            return pop_random(commons)

        # Sem preferencia por historico: cada oferta faz uma rolagem de rara
        # e as comuns sao sorteadas da mesma urna, compradas ou nao.
        if random.random() < chance_efetiva:
            card = pop_rare()
            if card:
                selecionadas.append(card)

        while len(selecionadas) < qtd:
            card = pop_common()
            if not card:
                card = pop_rare()
            if not card:
                break
            selecionadas.append(card)

        random.shuffle(selecionadas)
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
    modo_interacao = "teclado" if dispositivo_ativo == "teclado" else "mouse"

    def obter_rect_carta(indice):
        curr_scale = card_scale[indice]
        w_scaled = int(largura_carta * curr_scale)
        h_scaled = int(altura_carta * curr_scale)
        x_pos = int(card_x[indice] - w_scaled // 2)
        y_pos = int(altura_tela // 2.5 + card_y_offset[indice] - h_scaled // 2)
        return pygame.Rect(x_pos, y_pos, w_scaled, h_scaled)

    def iniciar_animacao_compra(indice, agora_evento):
        nonlocal animando_compra, tempo_inicio_animacao, carta_animada
        nonlocal pos_inicial_animacao, escala_inicial_animacao, carta_selecionada_index
        if animando_compra or not (0 <= indice < len(cartas_selecionadas)):
            return
        carta_selecionada_index = indice
        animando_compra = True
        tempo_inicio_animacao = agora_evento
        carta_animada = cartas_selecionadas[carta_selecionada_index]
        rect_carta = obter_rect_carta(carta_selecionada_index)
        pos_inicial_animacao = rect_carta.center
        escala_inicial_animacao = card_scale[carta_selecionada_index]

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
            dano_person_hit += incremento_carta_dano(inimigos_eliminados)
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
            dano_person_hit += incremento_dano_carta_critico(inimigos_eliminados)
            chance_critico += incremento_chance_carta_critico(inimigos_eliminados)
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
            Chance_Sorte += incremento_sorte_carta()
            cartas_compradas["Sorte"] += 1
        elif nome == "Poison":
            Poison_Active = True
            Dano_Veneno_Acumulado += 0.005
            cartas_compradas["Poison"] += 1
        elif nome == "Coletora":
            Executa_inimigo += 0.005
            Ultimo_Estalo = True
            cartas_compradas["Coletora"] += 1
        elif nome == "Mercenaria":
            Mercenaria_Active = True
            Valor_Bonus += 25
            cartas_compradas["Mercenaria"] += 1

        compras_restantes -= 1
        if compras_restantes > 0:
            cartas_selecionadas = obter_cartas_disponiveis(cartas, cartas_compradas, 3)

    while compras_restantes > 0:
        agora = pygame.time.get_ticks()
        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        rects_cartas = [obter_rect_carta(i) for i in range(len(cartas_selecionadas))]
        btn_reroll_rect = pygame.Rect(largura_tela // 2 - 240, altura_tela - 76, 130, 30)
        btn_sair_rect = pygame.Rect(largura_tela // 2 + 110, altura_tela - 76, 130, 30)
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if animando_compra:
                continue

            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if evento.key == pygame.K_ESCAPE:
                    if som_tick:
                        som_tick.play()
                    compras_restantes = 0
                    break

                anterior = carta_selecionada_index
                if evento.key in [pygame.K_a, pygame.K_LEFT]:
                    carta_selecionada_index = (carta_selecionada_index - 1) % len(cartas_selecionadas)
                elif evento.key in [pygame.K_d, pygame.K_RIGHT]:
                    carta_selecionada_index = (carta_selecionada_index + 1) % len(cartas_selecionadas)
                elif evento.key in [pygame.K_SPACE, pygame.K_RETURN]:
                    if som_tick:
                        som_tick.play()
                    iniciar_animacao_compra(carta_selecionada_index, agora)
                    
                elif Rolagens_possiveis > Rolagens_Dadas and evento.key == pygame.K_q:
                    if som_tick:
                        som_tick.play()
                    Rolagens_Dadas += 1
                    cartas_selecionadas = obter_cartas_disponiveis(cartas, cartas_compradas, 3)
                    
                if carta_selecionada_index != anterior and som_tick:
                    som_tick.play()
                    
            elif evento.type == pygame.JOYAXISMOTION:
                modo_interacao = "teclado"
                if evento.axis == 0:
                    if agora - ultima_mudanca_de_carta >= DELAY_ENTRE_CARTAS:
                        anterior = carta_selecionada_index
                        if evento.value < -0.5:
                            carta_selecionada_index = (carta_selecionada_index - 1) % len(cartas_selecionadas)
                            ultima_mudanca_de_carta = agora
                        elif evento.value > 0.5:
                            carta_selecionada_index = (carta_selecionada_index + 1) % len(cartas_selecionadas)
                            ultima_mudanca_de_carta = agora
                        if carta_selecionada_index != anterior and som_tick:
                            som_tick.play()
                            
            elif evento.type == pygame.JOYBUTTONDOWN:
                modo_interacao = "teclado"
                if evento.button == 0:  # Xbox Button A
                    if som_tick:
                        som_tick.play()
                    iniciar_animacao_compra(carta_selecionada_index, agora)
                    
                elif Rolagens_possiveis > Rolagens_Dadas and evento.button == 3:  # Xbox Button Y (Reroll)
                    if som_tick:
                        som_tick.play()
                    Rolagens_Dadas += 1
                    cartas_selecionadas = obter_cartas_disponiveis(cartas, cartas_compradas, 3)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                modo_interacao = "mouse"
                pos_evento = ui_helpers.converter_pos_mouse_jogo(evento.pos)
                if btn_sair_rect.collidepoint(pos_evento):
                    if som_tick:
                        som_tick.play()
                    compras_restantes = 0
                    break
                if btn_reroll_rect.collidepoint(pos_evento) and Rolagens_possiveis > Rolagens_Dadas:
                    if som_tick:
                        som_tick.play()
                    Rolagens_Dadas += 1
                    cartas_selecionadas = obter_cartas_disponiveis(cartas, cartas_compradas, 3)
                    carta_selecionada_index = 0
                    break
                for i, rect_carta in enumerate(rects_cartas):
                    if rect_carta.collidepoint(pos_evento):
                        if som_tick:
                            som_tick.play()
                        if i == carta_selecionada_index:
                            iniciar_animacao_compra(i, agora)
                        elif i > carta_selecionada_index:
                            carta_selecionada_index = min(carta_selecionada_index + 1, len(cartas_selecionadas) - 1)
                        else:
                            carta_selecionada_index = max(carta_selecionada_index - 1, 0)
                        break

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
        texto_instr = "Clique nas laterais para navegar | Clique na carta central para comprar | A/D, Q e ESC funcionam"
        render_instr_text = fonte_instrucao.render(texto_instr, True, cor_accent)
        largura_instr = render_instr_text.get_width() + 40
        altura_instr = 30
        
        surf_instr = pygame.Surface((largura_instr, altura_instr), pygame.SRCALPHA)
        pygame.draw.rect(surf_instr, (12, 12, 18, 200), (0, 0, largura_instr, altura_instr), border_radius=6)
        pygame.draw.rect(surf_instr, cor_accent + (80,), (0, 0, largura_instr, altura_instr), width=1, border_radius=6)
        surf_instr.blit(render_instr_text, (20, (altura_instr - render_instr_text.get_height()) // 2))
        
        tela.blit(surf_instr, (largura_tela // 2 - largura_instr // 2, altura_tela - 40))

        for rect_btn, label, ativo in [
            (btn_reroll_rect, f"REROLL {Rolagens_possiveis - Rolagens_Dadas}", Rolagens_possiveis > Rolagens_Dadas),
            (btn_sair_rect, "SAIR", True),
        ]:
            hover = modo_interacao == "mouse" and rect_btn.collidepoint(mx, my) and ativo
            cor_base = (18, 18, 26) if ativo else (45, 45, 52)
            cor_borda = cor_accent if hover else (80, 80, 90)
            cor_texto = (255, 255, 255) if ativo else (120, 120, 130)
            pygame.draw.rect(tela, cor_base, rect_btn, border_radius=6)
            pygame.draw.rect(tela, cor_borda, rect_btn, width=2 if hover else 1, border_radius=6)
            texto_btn = fonte_instrucao.render(label, True, cor_texto)
            tela.blit(texto_btn, (
                rect_btn.centerx - texto_btn.get_width() // 2,
                rect_btn.centery - texto_btn.get_height() // 2
            ))

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)

    # === ANIMACAO DE SAIDA PRE-MUNDO (550ms) ===
    tempo_inicio_saida = pygame.time.get_ticks()
    duracao_saida = 550
    
    # Armazenar coordenadas iniciais para LERP / offsets
    y_painel_ini = altura_tela - 160 - 80
    hud_y_ini = 35
    instr_y_ini = altura_tela - 40
    
    # Som da transicao (raio / portal se fechando) se houver
    try:
        som_transicao = pygame.mixer.Sound("Sounds/Teleporte.mp3")
        som_transicao.set_volume(0.3)
        som_transicao.play()
    except:
        som_transicao = None

    while True:
        agora = pygame.time.get_ticks()
        decorrido = agora - tempo_inicio_saida
        if decorrido >= duracao_saida:
            break
            
        progresso = decorrido / duracao_saida
        
        # Manter janela responsiva
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # 1. Interpolação de Fundo para Preto
        bg_alvo = (0, 0, 0)
        for c in range(3):
            cor_fundo_atual[c] += (bg_alvo[c] - cor_fundo_atual[c]) * 0.15
        tela.fill((int(cor_fundo_atual[0]), int(cor_fundo_atual[1]), int(cor_fundo_atual[2])))
        
        # 2. Desenhar grid background com opacidade decrescente
        alpha_bg = max(0, int(75 * (1.0 - progresso)))
        if alpha_bg > 0:
            background.set_alpha(alpha_bg)
            tela.blit(background, (0, 0))
            
        # 3. Particulas em espiral (vortex) em direcao ao centro
        cor_accent = theme_sel["cor_tema"]
        cx, cy = largura_tela // 2, altura_tela // 2
        for p in particulas:
            # Calcular vetor para o centro
            dx = cx - p["x"]
            dy = cy - p["y"]
            dist = math.hypot(dx, dy)
            if dist > 5:
                # Atrair para o centro + espiral
                pull_speed = 3.5 + progresso * 8.0
                spiral_speed = 4.0 - progresso * 2.0
                p["x"] += (dx / dist) * pull_speed - (dy / dist) * spiral_speed
                p["y"] += (dy / dist) * pull_speed + (dx / dist) * spiral_speed
            else:
                # Regenera distante para continuar a ser sugado
                p["x"] = random.randint(0, largura_tela)
                p["y"] = random.randint(0, altura_tela)
            
            p["alpha"] = max(0, int(255 * (1.0 - progresso)))
            if p["alpha"] > 0:
                cor_part = cor_accent + (p["alpha"],)
                surf_p = pygame.Surface((int(p["tamanho"]*2), int(p["tamanho"]*2)), pygame.SRCALPHA)
                pygame.draw.circle(surf_p, cor_part, (int(p["tamanho"]), int(p["tamanho"])), int(p["tamanho"]))
                tela.blit(surf_p, (int(p["x"] - p["tamanho"]), int(p["y"] - p["tamanho"])))

        # 4. Renderizar Cards do Carrossel (sendo sugados e rotacionando)
        for i, carta in enumerate(cartas_selecionadas):
            # LERP para o centro da tela
            t_lerp = progresso ** 1.5
            x_centro_alvo = cx
            y_centro_alvo = cy
            
            # Posição original do card neste instante
            orig_x = card_x[i]
            orig_y = altura_tela // 2.5 + card_y_offset[i]
            
            curr_x = orig_x + (x_centro_alvo - orig_x) * t_lerp
            curr_y = orig_y + (y_centro_alvo - orig_y) * t_lerp
            
            # Escala e Alpha reduzem a zero
            curr_scale = card_scale[i] * (1.0 - progresso)
            curr_alpha = max(0, int(card_alpha[i] * (1.0 - progresso)))
            
            if curr_scale > 0.05 and curr_alpha > 0:
                w_scaled = int(largura_carta * curr_scale)
                h_scaled = int(altura_carta * curr_scale)
                
                # Criar superficie do card
                surf_card = pygame.Surface((w_scaled, h_scaled), pygame.SRCALPHA)
                
                # Fundo do card
                alpha_fundo = int((45 + (curr_alpha / 255.0) * 115) * (1.0 - progresso))
                pygame.draw.rect(surf_card, (20, 20, 25, alpha_fundo), (0, 0, w_scaled, h_scaled), border_radius=max(1, int(12 * curr_scale)))
                
                # Imagem da carta
                frame = carta["frames_animacao"][carta["frame_atual"]]
                img_scaled = pygame.transform.scale(frame, (max(1, w_scaled - 12), max(1, h_scaled - 12)))
                surf_img_alpha = pygame.Surface(img_scaled.get_size(), pygame.SRCALPHA)
                surf_img_alpha.blit(img_scaled, (0, 0))
                surf_img_alpha.fill((255, 255, 255, curr_alpha), special_flags=pygame.BLEND_RGBA_MULT)
                surf_card.blit(surf_img_alpha, (6, 6))
                
                # Borda
                card_theme = CARD_THEMES.get(carta["nome"], {"cor_tema": (0, 255, 200)})
                cor_borda = card_theme["cor_tema"] + (curr_alpha,)
                pygame.draw.rect(surf_card, cor_borda, (0, 0, w_scaled, h_scaled), width=1, border_radius=max(1, int(12 * curr_scale)))
                
                # Rotacionar a carta baseada no progresso para dar efeito de redemoinho
                angulo_rotacao = progresso * 540  # 1.5 voltas completas
                surf_rot = pygame.transform.rotate(surf_card, angulo_rotacao)
                
                tela.blit(surf_rot, (int(curr_x - surf_rot.get_width() // 2), int(curr_y - surf_rot.get_height() // 2)))

        # 5. Painel HUD (Top) - desliza para cima e some
        hud_alpha = max(0, int(210 * (1.0 - progresso)))
        if hud_alpha > 0:
            hud_y_curr = hud_y_ini - int(progresso * 150)
            surf_hud = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
            pygame.draw.rect(surf_hud, (12, 12, 18, hud_alpha), (0, 0, hud_w, hud_h), border_radius=12)
            pygame.draw.rect(surf_hud, cor_accent + (int(120 * (1.0 - progresso)),), (0, 0, hud_w, hud_h), width=1, border_radius=12)
            
            # Textos do HUD
            render_compras_s = fonte_glitch_pequena.render(text_compras, True, (255, 255, 255))
            render_rerolls_s = fonte_glitch_pequena.render(text_rerolls, True, cor_accent)
            
            # Aplicar alpha nos textos renderizados
            surf_compras_alpha = pygame.Surface(render_compras_s.get_size(), pygame.SRCALPHA)
            surf_compras_alpha.blit(render_compras_s, (0, 0))
            surf_compras_alpha.fill((255, 255, 255, hud_alpha), special_flags=pygame.BLEND_RGBA_MULT)
            
            surf_rerolls_alpha = pygame.Surface(render_rerolls_s.get_size(), pygame.SRCALPHA)
            surf_rerolls_alpha.blit(render_rerolls_s, (0, 0))
            surf_rerolls_alpha.fill((255, 255, 255, hud_alpha), special_flags=pygame.BLEND_RGBA_MULT)
            
            surf_hud.blit(surf_compras_alpha, (35, (hud_h - render_compras_s.get_height()) // 2))
            surf_hud.blit(surf_rerolls_alpha, (hud_w - render_rerolls_s.get_width() - 35, (hud_h - render_rerolls_s.get_height()) // 2))
            tela.blit(surf_hud, (hud_x, hud_y_curr))

        # 6. Painel Descritivo (Bottom) - desliza para baixo e some
        painel_alpha = max(0, int(220 * (1.0 - progresso)))
        if painel_alpha > 0:
            carta_sel = cartas_selecionadas[carta_selecionada_index]
            y_painel_curr = y_painel_ini + int(progresso * 200)
            
            surf_painel_s = pygame.Surface((largura_painel, altura_painel), pygame.SRCALPHA)
            pygame.draw.rect(surf_painel_s, (12, 12, 18, painel_alpha), (0, 0, largura_painel, altura_painel), border_radius=16)
            pygame.draw.rect(surf_painel_s, theme_sel["cor_tema"] + (int(180 * (1.0 - progresso)),), (0, 0, largura_painel, altura_painel), width=2, border_radius=16)
            
            # Renderizar textos com alpha correto
            # Nome
            render_nome = fonte_nome.render(carta_sel["nome"].upper(), True, theme_sel["cor_tema"])
            surf_nome_alpha = pygame.Surface(render_nome.get_size(), pygame.SRCALPHA)
            surf_nome_alpha.blit(render_nome, (0, 0))
            surf_nome_alpha.fill((255, 255, 255, painel_alpha), special_flags=pygame.BLEND_RGBA_MULT)
            surf_painel_s.blit(surf_nome_alpha, (24, 16))
            
            # Nickname
            render_nick = fonte_desc.render(f'"{carta_sel["Nick"].upper()}"', True, (255, 255, 255))
            surf_nick_alpha = pygame.Surface(render_nick.get_size(), pygame.SRCALPHA)
            surf_nick_alpha.blit(render_nick, (0, 0))
            surf_nick_alpha.fill((255, 255, 255, painel_alpha), special_flags=pygame.BLEND_RGBA_MULT)
            surf_painel_s.blit(surf_nick_alpha, (24 + render_nome.get_width() + 15, 22))
            
            # Category
            render_cat = fonte_status.render(theme_sel["categoria"], True, (150, 150, 150))
            surf_cat_alpha = pygame.Surface(render_cat.get_size(), pygame.SRCALPHA)
            surf_cat_alpha.blit(render_cat, (0, 0))
            surf_cat_alpha.fill((255, 255, 255, painel_alpha), special_flags=pygame.BLEND_RGBA_MULT)
            surf_painel_s.blit(surf_cat_alpha, (26, 48))
            
            # Divider
            pygame.draw.line(surf_painel_s, (50, 50, 60, int(120 * (1.0 - progresso))), (x_divisor, 16), (x_divisor, altura_painel - 16), 1)
            
            # Descricao
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
                surf_l_alpha = pygame.Surface(render_linha.get_size(), pygame.SRCALPHA)
                surf_l_alpha.blit(render_linha, (0, 0))
                surf_l_alpha.fill((255, 255, 255, painel_alpha), special_flags=pygame.BLEND_RGBA_MULT)
                surf_painel_s.blit(surf_l_alpha, (24, y_desc))
                y_desc += 22
                
            # Lore
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
                surf_l_alpha = pygame.Surface(render_linha.get_size(), pygame.SRCALPHA)
                surf_l_alpha.blit(render_linha, (0, 0))
                surf_l_alpha.fill((255, 255, 255, painel_alpha), special_flags=pygame.BLEND_RGBA_MULT)
                surf_painel_s.blit(surf_l_alpha, (x_divisor + 24, y_lore))
                y_lore += 20
                
            # Owned count
            qtd = cartas_compradas.get(carta_sel["nome"], 0)
            render_qtd = fonte_status.render(f"POSSUIDO NO DECK: {qtd}", True, theme_sel["cor_tema"])
            surf_q_alpha = pygame.Surface(render_qtd.get_size(), pygame.SRCALPHA)
            surf_q_alpha.blit(render_qtd, (0, 0))
            surf_q_alpha.fill((255, 255, 255, painel_alpha), special_flags=pygame.BLEND_RGBA_MULT)
            surf_painel_s.blit(surf_q_alpha, (x_divisor + 24, 16))
            
            tela.blit(surf_painel_s, (x_painel, y_painel_curr))

        # 7. Barra de Instrucao - some
        footer_alpha = max(0, int(200 * (1.0 - progresso)))
        if footer_alpha > 0:
            surf_instr_s = pygame.Surface((largura_instr, altura_instr), pygame.SRCALPHA)
            pygame.draw.rect(surf_instr_s, (12, 12, 18, footer_alpha), (0, 0, largura_instr, altura_instr), border_radius=6)
            pygame.draw.rect(surf_instr_s, cor_accent + (int(80 * (1.0 - progresso)),), (0, 0, largura_instr, altura_instr), width=1, border_radius=6)
            
            surf_instr_text_alpha = pygame.Surface(render_instr_text.get_size(), pygame.SRCALPHA)
            surf_instr_text_alpha.blit(render_instr_text, (0, 0))
            surf_instr_text_alpha.fill((255, 255, 255, footer_alpha), special_flags=pygame.BLEND_RGBA_MULT)
            surf_instr_s.blit(surf_instr_text_alpha, (20, (altura_instr - render_instr_text.get_height()) // 2))
            
            tela.blit(surf_instr_s, (largura_tela // 2 - largura_instr // 2, instr_y_ini + int(progresso * 100)))

        # 8. Efeito da Ruptura Temporal (Abertura de Fenda Cósmica e Flash)
        if progresso < 0.8:
            # Fenda se abrindo no centro
            fenda_prog = progresso / 0.8
            fenda_w = int(largura_tela * fenda_prog)
            fenda_h = int(6 * math.sin(agora * 0.05) + 8)
            
            # Glow da fenda
            glow_fenda = pygame.Surface((largura_tela, 60), pygame.SRCALPHA)
            for g in range(1, 10):
                g_alpha = int((1.0 - g/10.0) * 120 * fenda_prog)
                g_h = g * 6
                pygame.draw.rect(glow_fenda, (0, 220, 255, g_alpha), (largura_tela // 2 - fenda_w // 2, 30 - g_h // 2, fenda_w, g_h), border_radius=g)
            pygame.draw.rect(glow_fenda, (255, 255, 255, int(255 * fenda_prog)), (largura_tela // 2 - fenda_w // 2, 30 - fenda_h // 2, fenda_w, fenda_h), border_radius=3)
            tela.blit(glow_fenda, (0, cy - 30), special_flags=pygame.BLEND_RGBA_ADD)
        else:
            # Flash de expansão (0.8 a 1.0)
            flash_prog = (progresso - 0.8) / 0.2
            
            # Surface branca/azulada que cobre a tela inteira
            flash_surf = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
            
            # Interpolar cor do flash: branco brilhante no início, desvanecendo para preto no final
            flash_alpha = int(255 * math.sin(flash_prog * math.pi))
            
            flash_surf.fill((210, 245, 255, flash_alpha))
            tela.blit(flash_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        pygame.display.flip()
        clock.tick(60)

    # Restaurar opacidade normal do background para proximas chamadas da tela
    try:
        background.set_alpha(75)
    except:
        pass

    return [velocidade_personagem, intervalo_disparo, vida, largura_disparo, altura_disparo, trembo, dano_person_hit, chance_critico, roubo_de_vida,
            quantidade_roubo_vida, tempo_cooldown_dash, vida_maxima, Petro_active, Resistencia, vida_petro, vida_maxima_petro, dano_petro, xp_petro, petro_evolucao, Resistencia_petro,
            Chance_Sorte, Poison_Active, Dano_Veneno_Acumulado, Executa_inimigo, Ultimo_Estalo, Mercenaria_Active, Valor_Bonus, dispositivo_ativo, Tempo_cura, porcentagem_cura, cartas_compradas, pontuacao_exib]
