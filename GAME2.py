
import pygame
import sys
import os
import random
import math
from Tela_Cartas import tela_de_pausa
import subprocess
import sys
import json
from Variaveis import *
from utils import *
from audio_manager import carregar_config_audio, aplicar_volume_som

# Forward declarations (atribuídos no loop principal)
botao_mouse = (False, False, False)
sprite_moeda = None
escudo_devota_ativo = True
duracao_incendio_vanguarda = 5000
intervalo_escudo = 30000

# Inicializar o Pygame
pygame.init()

# Carregar configurações gráficas
try:
    with open("saves/config_graficos.json", "r") as f:
        config_graficos = json.load(f)
except:
    config_graficos = {
        "sombras_ativas": "dinamicas",
        "qualidade_grafica": "alta",
        "particulas_ativas": True,
        "particulas_ativas": True,
        "efeitos_visuais": True,
        "fps_limite": 60
    }

# Carregar configurações de áudio
config_audio = carregar_config_audio()

# Variáveis para rastrear o texto de dano
texto_dano = None
tempo_texto_dano = 0

velocidade_inimigo2=1.70
velocidade_disparo_inimigo = 5  

estalos = aplicar_volume_som(pygame.mixer.Sound("Sounds/Estalo.mp3"), config_audio)

som_ataque_boss = aplicar_volume_som(pygame.mixer.Sound("Sounds/Hit_Boss1.mp3"), config_audio)

Hit_inimigo2 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Inimigo1_hit.wav"), config_audio)

Disparo_Geo = aplicar_volume_som(pygame.mixer.Sound("Sounds/Disparo_Geo.wav"), config_audio)  
Musica_tema_Boss2 = pygame.mixer.Sound("Sounds/Fase2_Boss.mp3")
Musica_tema_Boss2.set_volume(0.05)  
Musica_tema_fases = pygame.mixer.Sound("Sounds/Fase_boas.mp3")
Musica_tema_fases.set_volume(0.06)  
Som_tema_fases = pygame.mixer.Sound("Sounds/Neve.wav")
Som_tema_fases.set_volume(0.07)  
Som_portal = pygame.mixer.Sound("Sounds/Portal.mp3")
Som_portal.set_volume(0.06)  
musica_boss2=1

tela = pygame.display.set_mode((largura_tela, altura_tela))
pygame.display.set_caption("Renderizando Mapa com Personagem")

# Variáveis para a barra de magia
pontuacao_inimigos=0
maxima_pontuacao_magia = 750
piscar_magia = False


# Variáveis para controlar a imobilização da personagem
personagem_imovel = False
tempo_ultimo_atingido = pygame.time.get_ticks()
tempo_imobilizacao = 1000  # Tempo em milissegundos de imobilização após ser atingido

spawn_inimigo=True
dano_boss2=100
toque=0

tempo_ultimo_disparo_inimigo = pygame.time.get_ticks()  
cronometro_pausado = False
retomar_cronometro()

#INIMIGOS
nivel_ameaca = inimigos_eliminados // 10
tempo_ultimo_inimigo_apos_morte = pygame.time.get_ticks()
tempo_ultimo_disparo_inimigo = pygame.time.get_ticks()
# Carregar a imagem do mapa
mapa = pygame.image.load(mapa_path2).convert()
mapa = pygame.transform.scale(mapa, (largura_tela, altura_tela))


disparos_inimigos = []

comando_direção_petro=True

# Configurações do loop principal
relogio = pygame.time.Clock()
tempo_passado = 0
frame_atual = 0
frame_atual_disparo = 0

# Atualizar a última direção da personagem
ultima_tecla_movimento = None
movimento_pressionado = False

#as seguintes variáveis para controle do tempo de hit do inimigo
tempo_ultimo_hit_inimigo = pygame.time.get_ticks()


# esta variável global para controlar o piscar da barra de vida
piscando_vida = False

# Adicione esses frames aos frames_inimigo existentes
frames_inimigo = frames_inimigo_esquerda2 + frames_inimigo_direita2

vida_inimigo_maxima=30
vida_inimigo= vida_inimigo_maxima

carregar_atributos_na_fase=True
imune_tempo_restante = 0  # Tempo restante de imunidade (em milissegundos)
teleportado = False  # Controle de teleporte

def gerar_posicao_aleatoria(largura_mapa, altura_mapa, largura_personagem, altura_personagem):
    largura_mapa_int, altura_mapa_int, largura_personagem_int, altura_personagem_int=map(int,(largura_mapa, altura_mapa, largura_personagem, altura_personagem))
    x = random.randint(0, largura_mapa_int - largura_personagem_int)
    y = random.randint(0, altura_mapa_int - altura_personagem_int)
    return x, y
def limpar_salvamento():
    if os.path.exists('saves/atributos.json'):
        os.remove('saves/atributos.json')

def salvar_atributos():
    atributos = {
        "velocidade_personagem": velocidade_personagem,
        "intervalo_disparo": intervalo_disparo,
        "dano_person_hit": dano_person_hit,
        "chance_critico": chance_critico,
        "roubo_de_vida": roubo_de_vida,
        "quantidade_roubo_vida": quantidade_roubo_vida,
        "vida_petro": vida_petro,
        "vida_maxima_personagem": vida_maxima,
        "vida_maxima_petro": vida_maxima_petro,
        "vida_atual_personagem": vida,
        "nivel_Petro": xp_petro,
        "existencia_petro": Petro_active,
        "existencia_trembo": trembo,
        "dano_petro": dano_petro,
        "resistencia_personagem": Resistencia,
        "resistencia_petro": Resistencia_petro,
        "dano_inimigo_longe": dano_inimigo_longe,
        "dano_inimigo_perto": dano_inimigo_perto,
        "Poison_Active": Poison_Active,
        "Ultimo_Estalo": Ultimo_Estalo,
        "Executa_inimigo": Executa_inimigo,
        "Mercenaria_Active": Mercenaria_Active,
        "Valor_Bonus": Valor_Bonus,
        "tempo_cooldown_dash": tempo_cooldown_dash,
        "petro_evolucao": petro_evolucao,
        "Dano_Veneno_Acumulado": Dano_Veneno_Acumulado,
        "Tempo_cura": Tempo_cura,
        "porcentagem_cura": porcentagem_cura,
        # 🪙 novo campo
        "moedas_totais": moedas_totais,
    }

    with open('saves/atributos.json', 'w') as file:
        json.dump(atributos, file)

def carregar_atributos():
    global velocidade_personagem, intervalo_disparo, dano_person_hit, chance_critico, roubo_de_vida, quantidade_roubo_vida,vida_maxima,vida_maxima_petro,vida,xp_petro,Petro_active,trembo,dano_petro,Resistencia,Resistencia_petro,dano_inimigo_longe,dano_inimigo_perto,direcao_atual,Poison_Active,Ultimo_Estalo,Executa_inimigo,Valor_Bonus,Mercenaria_Active,tempo_cooldown_dash,vida_petro,petro_evolucao,Dano_Veneno_Acumulado, Tempo_cura,porcentagem_cura, moedas_totais
    with open('saves/atributos.json', 'r') as file:
        atributos = json.load(file)
        velocidade_personagem = atributos["velocidade_personagem"]
        intervalo_disparo = atributos["intervalo_disparo"]
        dano_person_hit = atributos["dano_person_hit"]
        chance_critico = atributos["chance_critico"]
        roubo_de_vida = atributos["roubo_de_vida"]
        quantidade_roubo_vida = atributos["quantidade_roubo_vida"]
        vida_petro= atributos["vida_petro"]
        vida_maxima=atributos["vida_maxima_personagem"]
        vida_maxima_petro=atributos["vida_maxima_petro"]
        vida=atributos["vida_atual_personagem"]
        xp_petro=atributos["nivel_Petro"]
        Petro_active=atributos["existencia_petro"]
        trembo=atributos["existencia_trembo"]
        dano_petro=atributos["dano_petro"]
        Resistencia=atributos["resistencia_personagem"]
        Resistencia_petro=atributos["resistencia_petro"]
        dano_inimigo_longe=atributos["dano_inimigo_longe"]
        dano_inimigo_perto=atributos["dano_inimigo_perto"]
        Poison_Active=atributos["Poison_Active"]
        Ultimo_Estalo=atributos["Ultimo_Estalo"]
        Executa_inimigo=atributos["Executa_inimigo"]
        Mercenaria_Active=atributos["Mercenaria_Active"]
        Valor_Bonus=atributos["Valor_Bonus"]
        tempo_cooldown_dash=atributos["tempo_cooldown_dash"]
        petro_evolucao= atributos["petro_evolucao"]
        Dano_Veneno_Acumulado= atributos["Dano_Veneno_Acumulado"]
        Tempo_cura= atributos["Tempo_cura"]
        porcentagem_cura= atributos["porcentagem_cura"]
        moedas_totais = atributos["moedas_totais"]



with open("saves/aurea_selecionada.json", "r") as file:
    aurea = json.load(file)["aurea"]




    
def determinar_frames_petro(posicao_petro, posicao_inimigo):
    if posicao_petro[0] < posicao_inimigo[0]:  # Petro está à esquerda do inimigo
        return 'right_petro'
    elif posicao_petro[0] > posicao_inimigo[0]:  # Petro está à direita do inimigo
        return 'left_petro'
    elif posicao_petro[1] < posicao_inimigo[1]:  # Petro está acima do inimigo
        return 'down_petro'
    elif posicao_petro[1] > posicao_inimigo[1]:  # Petro está abaixo do inimigo
        return 'up_petro'
    else:
        return 'stop_petro'  # Petro está na mesma posição do inimigo   


def atualizar_posicao_personagem(keys, joystick):
    global pos_x_personagem, pos_y_personagem, direcao_atual, ultima_tecla_movimento
    global movimento_pressionado, cooldown_dash, distancia_dash, tempo_ultimo_dash, teleporte_duration
    global personagem_imovel, tempo_ultimo_atingido
    global angulo_inclinacao_personagem

    # Se o personagem estiver imóvel, não atualize a posição
    if personagem_imovel:
        return
    direcao_atual = 'stop'  # Por padrão, definimos a direção como 'stop'
    dx, dy = 0, 0

    # ---- TECLADO ----
    if keys[config_teclas["Mover para direita"]]: dx, ultima_tecla_movimento = 1, 'right'
    elif keys[config_teclas["Mover para esquerda"]]: dx, ultima_tecla_movimento = -1, 'left'
    
    if keys[config_teclas["Mover para cima"]]: dy, ultima_tecla_movimento = -1, 'up'
    elif keys[config_teclas["Mover para baixo"]]: dy, ultima_tecla_movimento = 1, 'down'

    # ---- JOYSTICK ----
    if joystick:
        eixo_x = joystick.get_axis(0)
        eixo_y = joystick.get_axis(1)
        if abs(eixo_x) > 0.3:
            dx = 1 if eixo_x > 0 else -1
            ultima_tecla_movimento = 'right' if eixo_x > 0 else 'left'
        if abs(eixo_y) > 0.3:
            dy = 1 if eixo_y > 0 else -1
            ultima_tecla_movimento = 'down' if eixo_y > 0 else 'up'

    if dx != 0 or dy != 0:
        movimento_pressionado = True
        direcao_atual = ultima_tecla_movimento
        
        # Normalização de movimento diagonal
        if dx != 0 and dy != 0:
            inclinacao = angulo_diagonal_personagem
            
            if dy < 0:
                angulo_inclinacao_personagem = -inclinacao if dx > 0 else inclinacao
            else:
                angulo_inclinacao_personagem = inclinacao if dx > 0 else -inclinacao
                
            fator_normalizacao = 0.7071
            pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                         pos_x_personagem + dx * velocidade_personagem * fator_normalizacao))
            pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                         pos_y_personagem + dy * velocidade_personagem * fator_normalizacao))
        else:
            angulo_inclinacao_personagem = 0
            pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                         pos_x_personagem + dx * velocidade_personagem))
            pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                         pos_y_personagem + dy * velocidade_personagem))
    else:
        angulo_inclinacao_personagem = 0
        if botao_mouse[0]:
            direcao_atual = 'disp'
        else:
            direcao_atual = 'stop'

    # ---- DASH/TELEPORTE ----
    dash_teclado = keys[config_teclas["Teleporte"]]
    dash_joystick = joystick and joystick.get_button(4) if joystick else False

    if (dash_teclado or dash_joystick) and cooldown_dash == False:
        Som_portal.play()

        # Animação de teletransporte (plasma procedural)
        animar_teleporte_plasma(tela, mapa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, teleporte_duration // 2, ultima_tecla_movimento, distancia_dash, largura_mapa, altura_mapa)
        tela.blit(mapa, (pos_x_personagem, pos_y_personagem), pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem))

        if ultima_tecla_movimento == 'up': pos_y_personagem = max(0, pos_y_personagem - distancia_dash)
        elif ultima_tecla_movimento == 'down': pos_y_personagem = min(altura_mapa - altura_personagem, pos_y_personagem + distancia_dash)
        elif ultima_tecla_movimento == 'left': pos_x_personagem = max(0, pos_x_personagem - distancia_dash)
        elif ultima_tecla_movimento == 'right': pos_x_personagem = min(largura_mapa - largura_personagem, pos_x_personagem + distancia_dash)

        cooldown_dash = True
        tempo_ultimo_dash = pygame.time.get_ticks()

    # Atualizar o cooldown do dash
    if cooldown_dash and pygame.time.get_ticks() - tempo_ultimo_dash > tempo_cooldown_dash:
        cooldown_dash = False

    return direcao_atual


# Antes do loop principal, crie uma lista para armazenar os inimigos
inimigos_comum = []

tempo_ultima_criacao_gelo = pygame.time.get_ticks()
intervalo_criacao_gelo = 2000  # 10 segundos


def criar_disparo_inimigo(pos_inimigo, pos_personagem):
    dx = pos_personagem[0] - pos_inimigo[0]
    dy = pos_personagem[1] - pos_inimigo[1]
    dist = max(1, math.sqrt(dx ** 2 + dy ** 2))
    
    direcao_disparo_inimigo = (dx / dist * velocidade_disparo_inimigo, dy / dist * velocidade_disparo_inimigo)

    return {"rect": pygame.Rect(pos_inimigo[0], pos_inimigo[1], largura_disparo*0.5,altura_disparo*0.5), "velocidade": direcao_disparo_inimigo}


def criar_inimigo(x, y):
    image = frames_inimigo[0]
    return {"rect": pygame.Rect(x, y, largura_inimigo, altura_inimigo), "image": image, "vida": vida_inimigo_maxima, "vida_maxima": vida_inimigo_maxima}

def desenhar_sombra(tela, x, y, largura, altura, offset_y=5):
    """Desenha uma sombra elíptica embaixo de um ser com três níveis de qualidade"""
    modo_sombra = config_graficos.get("sombras_ativas", "dinamicas")
    
    if modo_sombra == "desativadas":
        return
    
    if modo_sombra == "simples":
        # Sombra simples - elipse básica
        sombra_surface = pygame.Surface((largura, altura // 3), pygame.SRCALPHA)
        cor_sombra = (0, 0, 0, 80)
        pygame.draw.ellipse(sombra_surface, cor_sombra, (0, 0, largura, altura // 3))
        tela.blit(sombra_surface, (x, y + altura - offset_y))
    
    elif modo_sombra == "dinamicas":
        # Sombra dinâmica - múltiplas camadas com gradiente
        sombra_surface = pygame.Surface((int(largura * 1.2), int(altura // 2.5)), pygame.SRCALPHA)
        
        # Camada externa (mais suave e transparente)
        cor_externa = (0, 0, 0, 40)
        pygame.draw.ellipse(sombra_surface, cor_externa, 
                          (0, 0, int(largura * 1.2), int(altura // 2.5)))
        
        # Camada intermediária
        cor_media = (0, 0, 0, 70)
        margem = int(largura * 0.15)
        pygame.draw.ellipse(sombra_surface, cor_media, 
                          (margem, margem // 2, int(largura * 0.9), int(altura // 3)))
        
        # Camada interna (mais escura e definida)
        cor_interna = (0, 0, 0, 100)
        margem_interna = int(largura * 0.25)
        pygame.draw.ellipse(sombra_surface, cor_interna, 
                          (margem_interna, margem_interna // 2, int(largura * 0.7), int(altura // 3.5)))
        
        # Posicionar a sombra centralizada
        pos_x = x - int(largura * 0.1)
        pos_y = y + altura - 15 - int(altura // 6)
        tela.blit(sombra_surface, (pos_x, pos_y))

def gerar_inimigo():
    global inimigos_comum

    if len(inimigos_comum) < max_inimigos2:
        # Adicione uma chance de 40% de gerar o inimigo na borda esquerda
        if random.random() <= 0.4:
            novo_inimigo = criar_inimigo(0, random.randint(10, altura_mapa))
        else:
            novo_inimigo = criar_inimigo(largura_mapa, random.randint(10, altura_mapa))

        # Verifique se o novo inimigo está muito próximo de algum inimigo existente
        distancia_minima_alcancada = any(
            math.sqrt((novo_inimigo["rect"].x - inimigo["rect"].x) ** 2 + (novo_inimigo["rect"].y - inimigo["rect"].y) ** 2) < distancia_minima_inimigos
            for inimigo in inimigos_comum
        )

        
        while distancia_minima_alcancada:
            if random.random() <= 0.4:
                novo_inimigo = criar_inimigo(0, random.randint(10, altura_mapa))
            else:
                novo_inimigo = criar_inimigo(largura_mapa, random.randint(10, altura_mapa))
            distancia_minima_alcancada = any(
                math.sqrt((novo_inimigo["rect"].x - inimigo["rect"].x) ** 2 + (novo_inimigo["rect"].y - inimigo["rect"].y) ** 2) < distancia_minima_inimigos
                for inimigo in inimigos_comum
            )

        inimigos_comum.append(novo_inimigo)
        
def calcular_direcao_para_inimigo(personagem, inimigos):
    # Inicialize a distância mínima como infinito e o inimigo mais próximo como None
    distancia_minima = float('inf')
    inimigo_mais_proximo = None

    # Calcule a distância para cada inimigo e encontre o inimigo mais próximo
    for inimigo in inimigos:
        distancia = math.sqrt((inimigo["rect"].x - personagem["rect"].x) ** 2 + (inimigo["rect"].y - personagem["rect"].y) ** 2)
        if distancia < distancia_minima:
            distancia_minima = distancia
            inimigo_mais_proximo = inimigo

    # Se encontrou um inimigo próximo, calcule a direção para ele
    if inimigo_mais_proximo:
        dx = inimigo_mais_proximo["rect"].x - personagem["rect"].x
        dy = inimigo_mais_proximo["rect"].y - personagem["rect"].y
        direcao_x = 1 if dx > 0 else -1
        direcao_y = 1 if dy > 0 else -1
        return (direcao_x, direcao_y)
    else:
        return (0, 0)  # Se não houver inimigos, retorne a direção neutra

# Configurações para controlar a criação de inimigos
dobro_pontuacao = 15  # Quantidade de pontos necessários para dobrar a pontuação e adicionar mais inimigos
pontuacao_dobro = dobro_pontuacao  # Inicializa a pontuação necessária para dobrar a pontuação



# Variável para armazenar o tempo do último inimigo adicionado
tempo_ultimo_inimigo = pygame.time.get_ticks()
quantidade_inimigos = 1

# Função para verificar a colisão entre o personagem e os projéteis inimigos
def verificar_colisao_personagem(projeteis):
    global pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem

    for proj in projeteis:
        pos_x_proj, pos_y_proj = proj["rect"].x, proj["rect"].y

        if (
            pos_x_personagem < pos_x_proj < pos_x_personagem + largura_personagem and
            pos_y_personagem < pos_y_proj < pos_y_personagem + altura_personagem
        ):
            return True  # Colisão detectada

    return False  # Sem colisão

def verificar_colisao_personagem_inimigo(personagem_rect, inimigos_rects):
    tempo_atual = pygame.time.get_ticks()
    for inimigo_rect in inimigos_rects:
        if personagem_rect.colliderect(inimigo_rect):
            return True  # Colisão detectada

    return False  # Sem colisão

def soltar_moeda(posicao):
    chance = 0.05  # 5%
    if random.random() < chance:
        tamanho_moeda = (36, 36)  # Novo tamanho desejado
        sprite_redimensionada = pygame.transform.scale(sprite_moeda, tamanho_moeda)
        rect = sprite_redimensionada.get_rect(center=posicao)
        moedas_soltadas.append({
            "rect": rect,
            "image": sprite_redimensionada
        })

def tela_upgrade_aureas(tela, fonte, moedas_disponiveis):
    if not os.path.exists("saves/aureas_upgrade.json"):
        dados_iniciais = {
            "Racional": 0,
            "Impulsiva": 0,
            "Devota": 0,
            "Vanguarda": 0
        }
        with open("saves/aureas_upgrade.json", "w") as f:
            json.dump(dados_iniciais, f, indent=4)
    
    with open("saves/aureas_upgrade.json", "r") as f:
        upgrades = json.load(f)
    aureas = [
        {"nome": "Racional", "imagem": "Sprites/aurea_cientista.png", "ativa": True},
        {"nome": "Impulsiva", "imagem": "Sprites/aurea_impulsiva.png", "ativa": True},
        {"nome": "Devota", "imagem": "Sprites/aurea_devota.png", "ativa": True},
        {"nome": "Vanguarda", "imagem": "Sprites/aurea_vanguarda.png", "ativa": True},
        {"nome": "?", "imagem": "Sprites/aurea_misteriosa.png", "ativa": False}
    ]
    for nome in ["Racional", "Impulsiva", "Devota", "Vanguarda"]:
        if nome not in upgrades:
            upgrades[nome] = 0

    upgrades = carregar_upgrade_aureas("saves/aureas_upgrade.json")

    selecionado = 0
    clock = pygame.time.Clock()
    largura, altura = tela.get_size()

    largura_quadro = 120
    altura_quadro = 140
    espacamento = 50
    colunas = 3

    while True:
        tela.fill((15, 15, 15))

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_RIGHT, pygame.K_d]:
                    selecionado = (selecionado + 1) % len(aureas)
                    while not aureas[selecionado]["ativa"]:
                        selecionado = (selecionado + 1) % len(aureas)
                elif evento.key in [pygame.K_LEFT, pygame.K_a]:
                    selecionado = (selecionado - 1) % len(aureas)
                    while not aureas[selecionado]["ativa"]:
                        selecionado = (selecionado - 1) % len(aureas)
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    nome = aureas[selecionado]["nome"]
                    if aureas[selecionado]["ativa"] and nome != "?":
                        if moedas_disponiveis > 0:
                            upgrades[nome] += 1
                            moedas_disponiveis -= 1
                            salvar_upgrade_aureas("saves/aureas_upgrade.json", upgrades)

                elif evento.key == pygame.K_ESCAPE:
                    return

        for i, aurea in enumerate(aureas):
            linha = i // colunas
            coluna = i % colunas

            x = largura // 2 - ((colunas * largura_quadro + (colunas - 1) * espacamento) // 2) + coluna * (largura_quadro + espacamento)
            y = altura // 4 + linha * (altura_quadro + 30)

            cor_borda = (255, 255, 255) if i == selecionado else (80, 80, 80)
            pygame.draw.rect(tela, cor_borda, (x, y, largura_quadro, altura_quadro), 3)

            # Texto com nome
            cor_texto = cor_borda
            nome_display = aurea["nome"]
            if nome_display != "?" and upgrades.get(nome_display, 0) > 0:
                nome_display += f" (Nv. {upgrades[nome_display]})"

            texto = fonte.render(nome_display, True, cor_texto)
            tela.blit(texto, (x + largura_quadro // 2 - texto.get_width() // 2, y - 25))

            

            # Texto com nível
            if aurea["ativa"] and aurea["nome"] != "?":
                nivel = upgrades.get(aurea["nome"], 0)
                texto_nivel = fonte.render(f"Nível {nivel}", True, (200, 200, 100))
                tela.blit(texto_nivel, (x + largura_quadro // 2 - texto_nivel.get_width() // 2, y + altura_quadro + 5))

            # Imagem
            try:
                imagem = pygame.image.load(aurea["imagem"]).convert_alpha()
                imagem = pygame.transform.scale(imagem, (largura_quadro, altura_quadro))
                tela.blit(imagem, (x, y))
            except:
                pass

        # Mostrar moedas
        texto_moedas = fonte.render(f"Moedas: {moedas_disponiveis}", True, (255, 255, 100))
        tela.blit(texto_moedas, (50, 40))

        instrucoes = fonte.render("← → para navegar | ENTER para melhorar | ESC para sair", True, (150, 150, 150))
        tela.blit(instrucoes, (largura // 2 - instrucoes.get_width() // 2, altura - 60))

        pygame.display.flip()
        clock.tick(60)


movimento_pressionado = False
dano = 0
fonte = None
running = True
tempo_atual = 0
upgrades = {}
x = 0
y = 0

def executar_jogo(game_manager=None):
    global Chance_Sorte, Dano_Veneno_Acumulado, Executa_inimigo, Mercenaria_Active, Musica_tema_Boss2, Musica_tema_fases, Petro_active, Poison_Active, Resistencia, Resistencia_petro, Som_tema_fases, Tempo_cura, Ultimo_Estalo, Valor_Bonus, altura_disparo, ataque_horizontal_ativo, ataque_vertical_ativo, bonus_pontuacao, boss_envenenado, carregar_atributos_na_fase, cartas_compradas, cartas_visiveis, chance_critico, dano, dano_boss2, dano_inimigo_longe, dano_inimigo_perto, dano_person_hit, dano_petro, dano_por_tick_veneno_boss, disparos, disparos_inimigos, dispositivo_ativo, efeitos_texto, eliminacoes_consecutivas, eliminacoes_consecutivas_impulsiva, escudo_devota_ativo, fonte, frame_atual, frame_atual_chefe, frame_atual_disparo, frame_porcentagem, impulsiva_ativa, imune_tempo_restante, inimigos_atingidos_por_onda, inimigos_eliminados, inimigos_em_chamas, intervalo_disparo, largura_disparo, max_inimigos2, moedas_coletadas, moedas_soltadas, moedas_totais, movimento_pressionado, musica_boss2, nivel_ameaca, ondas, personagem_imovel, petro_evolucao, piscando_vida, pontuacao, pontuacao_exib, pontuacao_magia, porcentagem_cura, pos_x_personagem, pos_x_petro, pos_y_personagem, pos_y_petro, posicao_ataque_horizontal, posicao_ataque_vertical, quantidade_roubo_vida, r_press, rect_boss, roubo_de_vida, running, teleportado, tempo_anterior_petro, tempo_atual, tempo_cooldown_dash, tempo_inicio_ataque_horizontal, tempo_inicio_buff_impulsiva, tempo_inicio_dano_horizontal, tempo_inicio_veneno_boss, tempo_passado, tempo_passado_animacao_chefe2, tempo_texto_dano, tempo_ultima_atualizacao_direcao, tempo_ultima_regeneracao, tempo_ultimo_atingido, tempo_ultimo_dano_horizontal, tempo_ultimo_dano_vertical, tempo_ultimo_disparo_inimigo, tempo_ultimo_hit_inimigo, tempo_ultimo_uso_habilidade, texto_dano, tipo_buff_impulsiva, toque, trembo, ultima_direcao_animacao, ultimo_tick_veneno_boss, upgrades, velocidade_ataque_horizontal, velocidade_ataque_vertical, velocidade_inimigo2, velocidade_personagem, vida, vida_boss, vida_boss2, vida_boss3, vida_boss4, vida_inimigo_maxima, vida_maxima, vida_maxima_boss2, vida_maxima_boss3, vida_maxima_boss4, vida_maxima_petro, vida_petro, x, xp_petro, y, duracao_incendio_vanguarda, intervalo_escudo, comando_direção_petro
    class CleanExit(BaseException):
        pass
    import sys as _sys
    import os as _os
    import builtins as _builtins
    def local_exit(*args, **kwargs):
        if game_manager:
            raise CleanExit()
        else:
            _orig_sys_exit(*args, **kwargs)
    def local_os_exit(*args, **kwargs):
        if game_manager:
            raise CleanExit()
        else:
            _orig_os_exit(*args, **kwargs)
    _orig_sys_exit = _sys.exit
    _orig_os_exit = _os._exit
    _orig_builtins_exit = getattr(_builtins, 'exit', None)
    _sys.exit = local_exit
    _os._exit = local_os_exit
    if _orig_builtins_exit:
        _builtins.exit = local_exit
    try:
        tempo_ultimo_escudo = pygame.time.get_ticks()
        tempo_parado_person = pygame.time.get_ticks()  
        tempo_ultimo_disparo = pygame.time.get_ticks()
        boss_atingido_por_onda = pygame.time.get_ticks()
        Musica_tema_fases.play(loops=-1)
        Som_tema_fases.play(loops=-1)
        upgrades = carregar_upgrade_aureas("saves/aureas_upgrade.json")

        # Configurar e escalar as passivas das áureas
        nivel_devota = upgrades.get("Devota", 0)
        nivel_vanguarda = upgrades.get("Vanguarda", 0)

        if aurea == "Devota":
            escudo_devota_ativo = True
            intervalo_escudo = max(10000, 30000 - (nivel_devota * 3000))
        else:
            escudo_devota_ativo = False

        if aurea == "Vanguarda":
            duracao_incendio_vanguarda = 5000 + (nivel_vanguarda * 1000)


        pygame.mouse.set_visible(False)
        FPS=pygame.time.Clock()
        cursor_imagem = pygame.image.load("Sprites/Ponteiro.png").convert_alpha()  # Ajuste o caminho
        cursor_tamanho = cursor_imagem.get_size()

        sprite_moeda = pygame.image.load("Sprites/moeda.png").convert_alpha()
        moedas_soltadas = []

        ###################################################################################################PRINCIPAL#################################################################################################################
        #LOOP PRINCIPAL
        jogo_pausado = False
        running = True
        while running:
            tempo_atual = pygame.time.get_ticks()
            if carregar_atributos_na_fase:
                carregar_atributos()
                carregar_atributos_na_fase=False

            if impulsiva_ativa:
                disparo_paths = ["Sprites/Fogo_impulso1.png", "Sprites/Fogo_impulso2.png"]
            else:
                disparo_paths = ["Sprites/Fogo1.png", "Sprites/Fogo2.png"]
            frames_disparo = [pygame.image.load(path) for path in disparo_paths]
            frames_disparo = [pygame.transform.scale(frame, (largura_disparo, altura_disparo)) for frame in frames_disparo]


            nivel_impulsiva = upgrades.get("Impulsiva", 0)
            if impulsiva_ativa:
                duracao_buff = 3000 + nivel_impulsiva * 500  # 3s base + 0.5s por nível
                if pygame.time.get_ticks() - tempo_inicio_buff_impulsiva >= duracao_buff:
                    impulsiva_ativa = False
                    tipo_buff_impulsiva = None
                else:
                    if tipo_buff_impulsiva == "dano":
                        multiplicador_dano = 1.3 + (0.05 * nivel_impulsiva)
                    elif tipo_buff_impulsiva == "velocidade":
                        multiplicador_velocidade = 1.2 + (0.05 * nivel_impulsiva)
                mensagem = "+ Buff: Dano ↑" if tipo_buff_impulsiva == "dano" else "+ Buff: Velocidade ↑"

                efeitos_texto.append({
                    "texto": mensagem,
                    "x": pos_x_personagem,
                    "y": pos_y_personagem - 20,
                    "tempo_inicio": pygame.time.get_ticks(),
                    "cor": (255, 100, 100) if tipo_buff_impulsiva == "dano" else (100, 100, 255)
                })


            pos_mouse = pygame.mouse.get_pos()
            botao_mouse = pygame.mouse.get_pressed()
            mouse_x = max(0, min(pos_mouse[0], largura_mapa - cursor_tamanho[0]))
            mouse_y = max(0, min(pos_mouse[1], altura_mapa - cursor_tamanho[1]))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    # Alternar pausa
                    jogo_pausado = not jogo_pausado
                    if jogo_pausado:
                        pausar_cronometro()
                        pygame.event.set_grab(False)  # Liberar mouse
                        pygame.mouse.set_visible(True)  # Mostrar cursor do sistema
                    else:
                        retomar_cronometro()
                        pygame.event.set_grab(True)  # Travar mouse de novo
                        pygame.mouse.set_visible(False)  # Esconder cursor do sistema
                elif botao_mouse[0] and tempo_atual - tempo_ultimo_disparo >= intervalo_disparo:  # Botão esquerdo do mouse
                    pos_mouse = pygame.mouse.get_pos()
                    angulo = calcular_angulo_disparo((pos_x_personagem, pos_y_personagem), pos_mouse)

                    # Crie o disparo com direção baseada no ângulo
                    novo_disparo = {
                        "rect": pygame.Rect(pos_x_personagem, pos_y_personagem, largura_disparo, altura_disparo),
                        "angulo": angulo
                    }
                    disparos.append(novo_disparo)
                    tempo_ultimo_disparo = tempo_atual  # Atualizar o tempo do último disparo
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and tempo_atual - tempo_ultimo_uso_habilidade >= cooldown_habilidade:  # Botão direito do mouse
                    pos_mouse = pygame.mouse.get_pos()
                    angulo = calcular_angulo_disparo((pos_x_personagem, pos_y_personagem), pos_mouse)

                    # Criar uma onda cinética com as novas propriedades
                    nova_onda = {
                        "rect": pygame.Rect(pos_x_personagem, pos_y_personagem, largura_onda, altura_onda),
                        "angulo": angulo,
                        "tempo_inicio": pygame.time.get_ticks(),
                        "frame_atual": 0,
                        "frames": frames_onda_cinetica  # Certifique-se de ter os frames para animação da onda
                    }
                    ondas.append(nova_onda)
                    tempo_ultimo_uso_habilidade = tempo_atual


            # Verificar eventos de teclado
            # --- Tela de pausa (ESC) ---
            if jogo_pausado:
                pausar_cronometro()
                pygame.event.set_grab(False)
                pygame.mouse.set_visible(True)
                
                joystick_count = pygame.joystick.get_count()
                joy = pygame.joystick.Joystick(0) if joystick_count > 0 else None
                if joy:
                    joy.init()
                
                from Tela_Pause import exibir_tela_pause
                exibir_tela_pause(tela, cartas_compradas, joy)
                
                retomar_cronometro()
                pygame.event.set_grab(True)
                pygame.mouse.set_visible(False)
                jogo_pausado = False
                continue

            keys = pygame.key.get_pressed()

            # Verificar eventos de joystick
            joystick_count = pygame.joystick.get_count()
            if joystick_count > 0:
                joystick = pygame.joystick.Joystick(0)
                joystick.init()
            else:
                joystick = None

            # Chamar a função para atualizar a posição do personagem
            ultimo_x = pos_x_personagem
            ultimo_y = pos_y_personagem
            atualizar_posicao_personagem(keys,joystick)



            novos_inimigos = []
            novos_disparos = []
            inimig_atin=[]

            for inimigo in inimigos_comum:
                inimigo_rect = inimigo["rect"]
                inimigo_image = inimigo["image"]

                inimigo_atingido = False

                for disparo in disparos:

                    if verificar_colisao_disparo_inimigo(disparo, (inimigo["rect"].x, inimigo["rect"].y), largura_disparo, altura_disparo, largura_inimigo, altura_inimigo, inimigos_eliminados):
                        if random.random() <= chance_critico:  # 10% de chance de dano crítico
                            dano = dano_person_hit * 3  # Valor do dano crítico é 3 vezes o dano normal
                            cor = (255, 255, 0)  # Amarelo (RGB)
                            fonte_dano=fonte_dano_critico
                        else:
                            dano = dano_person_hit
                            cor = (255, 0, 0)  # Vermelho (RGB)
                            fonte_dano=fonte_dano_normal
                        if Petro_active:    
                            if vida_petro > vida_maxima_petro :
                                vida_petro+= (vida_maxima_petro-vida_petro) *0.25
                        # Renderize o texto do dano
                        texto_dano = fonte_dano.render("-" + str(int(dano)), True, cor)

                        # Desenhe o texto na tela perto do chefe
                        pos_texto = (inimigo["rect"].x + largura_inimigo // 2 - texto_dano.get_width() // 2,  inimigo["rect"].y - 20)

                        # Rastreie o tempo de exibição do texto
                        tempo_texto_dano = pygame.time.get_ticks()
                        inimigo["vida"] -= dano
                        disparos.remove(disparo)  # Remover o disparo após colisão

                        if Poison_Active:
                            inimigo["veneno"] = {
                                "dano_por_tick": inimigo["vida_maxima"] * Dano_Veneno_Acumulado,  # 0.5% da vida máxima
                                "tempo_inicio": pygame.time.get_ticks(),
                                "duracao": 4000,  # 4 segundos
                                "ultimo_tick": pygame.time.get_ticks(),  # Tempo do último tick
                                "posicao_texto": (inimigo["rect"].x, inimigo["rect"].y - 20),  # Posição inicial do texto
                                "tempo_texto_dano": pygame.time.get_ticks()  # Tempo de exibição do texto
                                }


                        if random.random() < roubo_de_vida:
                            vida += (vida_maxima-vida)*quantidade_roubo_vida
                        if Ultimo_Estalo and inimigo["vida"] <= Executa_inimigo * inimigo["vida_maxima"]:
                            if inimigo in inimigos_comum: inimigos_comum.remove(inimigo)
                            posicao_inimigo = inimigo["rect"].center
                            soltar_moeda(posicao_inimigo)
                            inimigos_eliminados += 1
                            ganho_pontos = int(150 * (1 + math.log10(inimigos_eliminados + 1)))
                            # Execução oferece um prêmio de escala superior (15%)
                            mult_ex = 1.0 + (nivel_ameaca * 0.15)

                            vida_inimigo_maxima += 0.7 * mult_ex
                            Resistencia_petro += 0.015 * mult_ex
                            dano_inimigo_perto += 0.07 * mult_ex
                            dano_person_hit += 0.15 * mult_ex
                            vida_maxima_petro += 1.0 * mult_ex
                            dano_petro += 0.01 * mult_ex
                            dano_boss2 += 0.03 * mult_ex
                            dano_inimigo_longe += 0.02 * mult_ex

                            ganho = int(160 * (1 + math.log10(inimigos_eliminados + 1)))
                            pontuacao += ganho

                            eliminacoes_consecutivas_impulsiva += 1

                            if Mercenaria_Active:
                                eliminacoes_consecutivas += 1
                                # Bônus mercenário fixo para evitar inflação infinita
                                pontuacao_exib += ganho_pontos + bonus_pontuacao
                                if eliminacoes_consecutivas % 5 == 0:
                                    bonus_pontuacao = min(500, bonus_pontuacao + Valor_Bonus) 
                            else:
                                pontuacao_exib += ganho_pontos

                            if not boss_vivo2:
                                vida_boss2 += 20 * mult_ex
                                vida_maxima_boss2 = vida_boss2
                                vida_boss3 += 25 * mult_ex
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += 30 * mult_ex
                                vida_maxima_boss4 = vida_boss4

                            if vida_petro < vida_maxima_petro:
                                vida_petro += (vida_maxima_petro - vida_petro) * 0.25

                        # Quando o inimigo morre normalmente
                        elif inimigo["vida"] <= 0:
                            posicao_inimigo = inimigo["rect"].center
                            soltar_moeda(posicao_inimigo)
                            inimigos_comum.remove(inimigo)
                            inimigos_eliminados += 1

                            # --- ESCALONAMENTO RECALIBRADO PARA 20 MINUTOS ---
                            mult = 1.0 + (nivel_ameaca * 0.12)

                            vida_inimigo_maxima += 0.6 * mult
                            Resistencia_petro += 0.01 * mult
                            dano_inimigo_perto += 0.06 * mult
                            dano_person_hit += 0.1 * mult # Crescimento firme para sustentar 50 cartas
                            vida_maxima_petro += 0.8 * mult
                            dano_petro += 0.008 * mult
                            dano_boss2 += 0.02 * mult
                            dano_inimigo_longe += 0.015 * mult

                            # Pontuação Logarítmica para estabilizar a economia de cartas
                            ganho = int(130 * (1 + math.log10(inimigos_eliminados + 1)))
                            pontuacao += ganho

                            if Mercenaria_Active:
                                eliminacoes_consecutivas += 1
                                pontuacao_exib += ganho + bonus_pontuacao
                                if eliminacoes_consecutivas % 5 == 0:
                                    bonus_pontuacao = min(600, bonus_pontuacao + Valor_Bonus)
                            else:
                                pontuacao_exib += ganho

                            # Foco nos Bosses da Fase 2 em diante
                            if not boss_vivo2:
                                incremento_v = 15 * mult
                                vida_boss2 += incremento_v
                                vida_maxima_boss2 = vida_boss2
                                vida_boss3 += incremento_v * 1.3
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += incremento_v * 1.6
                                vida_maxima_boss4 = vida_boss4

                            # Cura Inteligente da Petro
                            if vida_petro < vida_maxima_petro:
                                vida_petro = min(vida_maxima_petro, vida_petro + (vida_maxima_petro - vida_petro) * 0.20)

                            break  # importante para não iterar sobre lista modificada

                if "veneno" in inimigo:
                        # Verifique se é hora de aplicar dano
                        if tempo_atual - inimigo["veneno"]["ultimo_tick"] >= 500:
                            inimigo["vida"] -= inimigo["veneno"]["dano_por_tick"]
                            inimigo["veneno"]["ultimo_tick"] = tempo_atual  # Atualiza o tempo do último tick
                            inimigo["veneno"]["tempo_texto_dano"] = tempo_atual  # Atualiza o tempo de exibição do texto

                        # Exibe o texto apenas por 1.5 segundos após o dano
                        if tempo_atual - inimigo["veneno"]["tempo_texto_dano"] <= 250:
                            dano_veneno_texto = "-" + str(int(inimigo["veneno"]["dano_por_tick"]))

                            # Renderize o texto do dano com borda preta
                            texto_dano_veneno = fonte_veneno.render(dano_veneno_texto, True, (0, 255, 0))
                            texto_dano_veneno_borda = fonte_veneno.render(dano_veneno_texto, True, (0, 0, 0))

                            # Posicione o texto
                            pos_texto = (inimigo["rect"].x + largura_inimigo // 2 - texto_dano_veneno.get_width() // 2,
                                    inimigo["rect"].y - 30)

                            # Exibe o texto com borda preta e o texto em verde
                            tela.blit(texto_dano_veneno_borda, (pos_texto[0] - 1, pos_texto[1]))
                            tela.blit(texto_dano_veneno_borda, (pos_texto[0] + 1, pos_texto[1]))
                            tela.blit(texto_dano_veneno_borda, (pos_texto[0], pos_texto[1] - 1))
                            tela.blit(texto_dano_veneno_borda, (pos_texto[0], pos_texto[1] + 1))
                            tela.blit(texto_dano_veneno, pos_texto)  # Texto principal em verde

                        # Verifica se o efeito de veneno expirou
                        if tempo_atual - inimigo["veneno"]["tempo_inicio"] >= inimigo["veneno"]["duracao"]:
                            del inimigo["veneno"]  # Remove o efeito de veneno ao expirar        

                if inimigo_atingido:
                    break  # Sair do loop externo se um inimigo foi atingido



                if pontuacao_exib > pontuacao_magia:
                    pontuacao_magia = min(pontuacao_exib, maxima_pontuacao_magia)   

            def criar_disparo():
                return {"rect": pygame.Rect(pos_x_personagem, pos_y_personagem, largura_disparo, altura_disparo),"direcao": ultima_tecla_movimento }

            tempo_passado += relogio.get_rawtime()
            relogio.tick()

             # Adicionar inimigos a cada 10 segundos
            tempo_atual = pygame.time.get_ticks()
            if tempo_atual - tempo_ultimo_inimigo >= 1000 and len(inimigos_comum) < max_inimigos2 and spawn_inimigo:
                gerar_inimigo()
                tempo_ultimo_inimigo = tempo_atual  # Atualizar o tempo do último inimigo adicionado
            nivel_racional = upgrades.get("Racional", 0)    
            #LUGAR AONDE COLOCAMOS AS AUREAS
            if aurea == "Racional":
                if pos_x_personagem == ultimo_x and pos_y_personagem == ultimo_y:
                    if tempo_atual - tempo_parado_person >= 5000:
                        ganho = 3 + nivel_racional  # ganho aumenta com o nível
                        pontuacao += ganho
                        pontuacao_exib += ganho
                        tempo_parado_person = tempo_atual

                        # Determina posição flutuante aleatória à direita ou esquerda do personagem
                        lado = random.choice(["esquerda", "direita"])
                        if lado == "esquerda":
                            x = pos_x_personagem - 20
                        else:
                            x = pos_x_personagem + largura_personagem + 5

                        y = pos_y_personagem - 10  # ligeiramente acima

                        # Adiciona efeito à lista
                        efeitos_texto.append({
                            "texto": "+3",
                            "x": x,
                            "y": y,
                            "tempo_inicio": tempo_atual,
                            "cor": (50, 255, 50)  # verde
                        })
            if aurea == "Impulsiva":

                if eliminacoes_consecutivas_impulsiva >= 5 and not impulsiva_ativa:
                    impulsiva_ativa = True
                    tipo_buff_impulsiva = random.choice(["dano", "velocidade"])
                    tempo_inicio_buff_impulsiva = pygame.time.get_ticks()
                    eliminacoes_consecutivas_impulsiva = 0  # Zera para forçar novo ciclo



            # Reinicia a animação quando troca de direção para não pular frames
            if direcao_atual != ultima_direcao_animacao:
                frame_atual = 0
                tempo_passado = 0
                ultima_direcao_animacao = direcao_atual

            if direcao_atual == 'stop':
                if tempo_passado >= tempo_animacao_stop:
                    tempo_passado = 0
                    frame_atual = (frame_atual + 1) % len(frames_animacao[direcao_atual])
            if direcao_atual != 'stop':
                if tempo_passado >= tempo_animacao_no_stop:
                    tempo_passado = 0
                    frame_atual = (frame_atual + 1) % len(frames_animacao[direcao_atual])

            tela.fill((255, 255, 255))
            tela.blit(mapa, (0, 0))


            # Desenha a personagem
            # Desenhar sombra do personagem
            desenhar_sombra(tela, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
            if not personagem_imovel:
                frame_para_desenhar = frames_animacao[direcao_atual][frame_atual % len(frames_animacao[direcao_atual])]
                if angulo_inclinacao_personagem != 0:
                    # Rotaciona o frame pelo centro para manter o eixo
                    frame_rotacionado = pygame.transform.rotate(frame_para_desenhar, angulo_inclinacao_personagem)
                    novo_rect = frame_rotacionado.get_rect(center=(pos_x_personagem + largura_personagem//2, pos_y_personagem + altura_personagem//2))
                    tela.blit(frame_rotacionado, novo_rect.topleft)
                else:
                    tela.blit(frame_para_desenhar, (pos_x_personagem, pos_y_personagem))
            else:
                tela.blit(imagem_personagem_congelada, (pos_x_personagem, pos_y_personagem))

            for moeda in moedas_soltadas[:]:
                if personagem_rect.colliderect(moeda["rect"]):
                    moedas_coletadas += 1
                    moedas_totais += 1   # 🪙 acumula no total salvo
                    moedas_soltadas.remove(moeda)
                    salvar_atributos()   # 💾 salva imediatamente


            nova_lista = []
            for efeito in efeitos_texto:
                tempo_passado_efeito = tempo_atual - efeito["tempo_inicio"]
                if tempo_passado_efeito <= 800:  # mostra por 2 segundos
                    if config_graficos.get("efeitos_visuais", True):
                        fonte_efeito = pygame.font.Font(None, 28)
                        x = efeito["x"]
                        y = efeito["y"] - (tempo_passado_efeito // 25)
                        texto_principal = fonte_efeito.render(efeito["texto"], True, efeito["cor"])

                        # Contorno preto em 8 direções
                        for dx in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                if dx != 0 or dy != 0:
                                    contorno = fonte_efeito.render(efeito["texto"], True, (0, 0, 0))
                                    tela.blit(contorno, (x + dx, y + dy))

                        # Texto principal
                        tela.blit(texto_principal, (x, y))
                    nova_lista.append(efeito)
            efeitos_texto = nova_lista

            if trembo:
                # --- SISTEMA DINÂMICO DE POSICIONAMENTO DO TREMBO ---
                if 'trembo_lado' not in locals() and 'trembo_lado' not in globals():
                    trembo_lado = 'direita'
                    trembo_pos_x_atual = float(pos_x_personagem + largura_personagem + 4)
                    trembo_pos_y_atual = float(pos_y_personagem)
                    trembo_transicao = False
                TREMBO_VEL_CORRIDA = 4.0
                margem_borda = int(largura_trembo) + 10
                lado_ideal = trembo_lado
                if pos_x_personagem + largura_personagem + largura_trembo + 8 > largura_mapa - margem_borda:
                    lado_ideal = 'esquerda'
                elif pos_x_personagem - largura_trembo - 8 < margem_borda:
                    lado_ideal = 'direita'
                if lado_ideal != trembo_lado:
                    trembo_lado = lado_ideal
                    trembo_transicao = True
                if trembo_lado == 'direita':
                    alvo_x_trembo = pos_x_personagem + largura_personagem + 4
                else:
                    alvo_x_trembo = pos_x_personagem - largura_trembo - 4
                diferenca_altura =   altura_personagem - 115
                alvo_y_trembo = pos_y_personagem - diferenca_altura
                diff_x = alvo_x_trembo - trembo_pos_x_atual
                diff_y = alvo_y_trembo - trembo_pos_y_atual
                dist_total = max(1.0, (diff_x**2 + diff_y**2) ** 0.5)
                if dist_total > 2:
                    vel = min(TREMBO_VEL_CORRIDA, dist_total)
                    trembo_pos_x_atual += (diff_x / dist_total) * vel
                    trembo_pos_y_atual += (diff_y / dist_total) * vel
                    trembo_transicao = True
                else:
                    trembo_pos_x_atual = alvo_x_trembo
                    trembo_pos_y_atual = alvo_y_trembo
                    trembo_transicao = False
                pos_x_segundo_personagem = int(trembo_pos_x_atual)
                pos_y_segundo_personagem = int(trembo_pos_y_atual)
                pos_x_segundo_personagem = max(0, min(largura_mapa - int(largura_trembo), pos_x_segundo_personagem))
                pos_y_segundo_personagem = max(0, min(altura_mapa - int(altura_trembo), pos_y_segundo_personagem))
                if trembo_transicao and dist_total > 3:
                    if abs(diff_x) > abs(diff_y):
                        direcao_trembo = 'right' if diff_x > 0 else 'left'
                    else:
                        direcao_trembo = 'down' if diff_y > 0 else 'up'
                else:
                    direcao_trembo = direcao_atual
                desenhar_sombra(tela, pos_x_segundo_personagem, pos_y_segundo_personagem, int(largura_trembo), int(altura_trembo), offset_y=2)
                tela.blit(frames_animacao_trembo[direcao_trembo][frame_atual % len(frames_animacao_trembo[direcao_trembo])], (pos_x_segundo_personagem, pos_y_segundo_personagem))
            if trembo and tempo_atual- tempo_ultima_regeneracao >= Tempo_cura and vida < vida_maxima :
                if vida_maxima < vida:
                    vida=vida_maxima
                vida+= (vida_maxima*porcentagem_cura)
                tempo_ultima_regeneracao = tempo_atual



            if Petro_active:
                # Calcula a direção para o inimigo mais próximo

                direcao_petro = calcular_direcao_para_inimigo({"rect": pygame.Rect(pos_x_petro, pos_y_petro, largura_personagem, altura_personagem)}, inimigos_comum)


                # Se houver inimigos, atualize a posição de "Petro"
                if inimigos_comum:
                    # Calcula as coordenadas do inimigo mais próximo
                    inimigo_mais_proximo = min(inimigos_comum, key=lambda inimigo: math.sqrt((inimigo["rect"].x - pos_x_petro) ** 2 + (inimigo["rect"].y - pos_y_petro) ** 2))
                    pos_x_inimigo_mais_proximo = inimigo_mais_proximo["rect"].x
                    pos_y_inimigo_mais_proximo = inimigo_mais_proximo["rect"].y

                    posicao_petro = (pos_x_petro, pos_y_petro)
                    posicao_inimigo = (pos_x_inimigo_mais_proximo, pos_y_inimigo_mais_proximo)
                    tempo_atual = pygame.time.get_ticks()
                    if tempo_atual - tempo_ultima_atualizacao_direcao >= 1000:  # 1000 milissegundos = 1 segundo
                        # Atualiza a direção de Petro
                        direcao_atual_petro = determinar_frames_petro(posicao_petro, posicao_inimigo)
                        # Atualiza o tempo da última atualização da direção
                        tempo_ultima_atualizacao_direcao = tempo_atual


                    # Se "Petro" ainda não está na posição do inimigo, mova-o na direção calculada
                    if pos_x_petro != pos_x_inimigo_mais_proximo or pos_y_petro != pos_y_inimigo_mais_proximo:
                        pos_x_petro += 1.5 * direcao_petro[0]
                        pos_y_petro += 1.5 * direcao_petro[1]

                    # Calcula a distância entre "Petro" e o inimigo mais próximo
                    distancia_petro_inimigo = math.sqrt((pos_x_petro - pos_x_inimigo_mais_proximo) ** 2 + (pos_y_petro - pos_y_inimigo_mais_proximo) ** 2)

                    # Verifica se "Petro" está próximo o suficiente para aplicar dano
                    if distancia_petro_inimigo <= 50:
                        tempo_atual_petro = pygame.time.get_ticks()
                        if tempo_atual_petro - tempo_anterior_petro >= intervalo_dano_petro:
                            # Resistência mitigando o dano recebido
                            dano_real = max(0, dano_inimigo_perto - Resistencia_petro)
                            vida_petro -= int(dano_real)

                            # Dano da Petro escala com o poder do Personagem
                            inimigo_mais_proximo["vida"] -= int(dano_person_hit * 0.008) + dano_petro
                            tempo_anterior_petro = tempo_atual_petro

                            if inimigo_mais_proximo["vida"] <= 0:
                                # Incrementos controlados por abate direto da Petro
                                vida_inimigo_maxima += 0.6
                                Resistencia_petro += 0.02
                                vida_maxima_petro += 1.2
                                dano_person_hit += 0.08
                                dano_petro += 0.01
                                dano_boss2 += 0.05
                                inimigos_eliminados += 1

                                pontos_p = int(110 * (1 + math.log10(inimigos_eliminados + 1)))
                                pontuacao += pontos_p
                                pontuacao_exib += pontos_p

                                if inimigo_mais_proximo in inimigos_comum:
                                    inimigos_comum.remove(inimigo_mais_proximo)


                            if not boss_vivo2:
                                vida_boss2 += 20 * mult_ex
                                vida_maxima_boss2 = vida_boss2
                                vida_boss3 += 25 * mult_ex
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += 30 * mult_ex
                                vida_maxima_boss4 = vida_boss4



                if vida_petro<=0:
                    Petro_active= False
                    vida_petro+= vida_maxima_petro
                    vida_maxima_petro= vida_petro                     


                if xp_petro == "nivel_1":
                    petro_nivel=frames_animacao_Petro

                elif xp_petro == "nivel_2":
                    petro_nivel=frames_animacao_Petro2

                elif xp_petro == "nivel_3":
                    petro_nivel=frames_animacao_Petro3              



                if boss_vivo2:
                    # Define a direção de Petro em relação ao boss
                    dx = pos_x_chefe2 - pos_x_petro
                    dy = pos_y_chefe2 - pos_y_petro

                    # Normaliza a direção para manter a mesma velocidade em todas as direções
                    magnitude = math.sqrt(dx ** 2 + dy ** 2)
                    if magnitude != 0:
                        direcao_x = dx / magnitude
                        direcao_y = dy / magnitude
                    else:
                        direcao_x = 0
                        direcao_y = 0

                    # Move Petro na direção do boss
                    pos_x_petro += 1 * direcao_x
                    pos_y_petro += 1 * direcao_y

                    # Verifica se Petro está próximo o suficiente para aplicar dano ao boss
                    distancia_petro_boss = math.sqrt((pos_x_petro - pos_x_chefe2) ** 2 + (pos_y_petro - pos_y_chefe2) ** 2)
                    if distancia_petro_boss <= 50:
                        # Verifica se passou tempo suficiente desde o último dano
                        tempo_atual_petro = pygame.time.get_ticks()
                        if tempo_atual_petro - tempo_anterior_petro >= intervalo_dano_petro:
                            # Aplica dano ao "boss"
                            vida_petro -= int(dano_inimigo_perto)
                            vida_petro+= int(vida_maxima_petro)*quantidade_roubo_vida
                            vida_boss2-= int(dano_person_hit*0.25)+300
                            # Aqui você pode adicionar outras ações relacionadas ao dano ao "boss"
                            tempo_anterior_petro = tempo_atual_petro


                if comando_direção_petro:
                    direcao_atual_petro="left_petro"
                    comando_direção_petro=False


                desenhar_barra_de_vida_petro(tela, vida_petro, pos_x_petro, pos_y_petro - 20,vida_maxima_petro) 
                tela.blit(petro_nivel[direcao_atual_petro][frame_atual % len(petro_nivel[direcao_atual_petro])], (pos_x_petro, pos_y_petro))            




            # Desenhar os disparos normais
            novos_disparos = []
            for disparo in disparos:
                disparo["rect"].x += velocidade_disparo * math.cos(disparo["angulo"])
                disparo["rect"].y += velocidade_disparo * math.sin(disparo["angulo"])

                # Verificar se o disparo está dentro do mapa
                if 0 <= disparo["rect"].x < largura_mapa and 0 <= disparo["rect"].y < altura_mapa:
                    novos_disparos.append(disparo)

            disparos = novos_disparos

            # Renderizar os disparos
            for disparo in disparos:
                tela.blit(frames_disparo[frame_atual_disparo], disparo["rect"].topleft)

            frame_atual_disparo = (frame_atual_disparo + 1) % len(frames_disparo)

            novas_ondas = []
            for onda in ondas:
                onda["rect"].x += velocidade_onda * math.cos(onda["angulo"])
                onda["rect"].y += velocidade_onda * math.sin(onda["angulo"])

                # Atualizar o frame atual da animação da onda
                tempo_decorrido_onda = pygame.time.get_ticks() - onda["tempo_inicio"]
                onda["frame_atual"] = (tempo_decorrido_onda // duracao_frame_onda) % len(onda["frames"])

                # Renderizar a onda
                tela.blit(onda["frames"][onda["frame_atual"]], onda["rect"])

                # Verificar se a onda ainda está dentro do mapa
                if (
                    0 <= onda["rect"].x < largura_mapa and
                    0 <= onda["rect"].y < altura_mapa
                ):
                    novas_ondas.append(onda)

            ondas = novas_ondas
            for onda in ondas:
                for inimigo in inimigos_comum:
                    inimigo_id = id(inimigo["rect"])  # Identificador único baseado no objeto
                    if onda["rect"].colliderect(inimigo["rect"]) and \
                    (inimigo_id not in inimigos_atingidos_por_onda or tempo_atual - inimigos_atingidos_por_onda[inimigo_id] >= 500):

                        # Aplica o dano
                        inimigo["vida"] -= dano_person_hit * 2
                        inimigos_atingidos_por_onda[inimigo_id] = tempo_atual  # Atualiza o tempo do último hit

                        if inimigo["vida"] <= 0:
                            inimigos_comum.remove(inimigo)

                            # Escalonamento baseado no progresso
                            nivel_ameaca = min(inimigos_eliminados // 10, 100)

                            vida_inimigo_maxima += 1.2 + nivel_ameaca * 0.8
                            Resistencia_petro += 0.02 + nivel_ameaca * 0.02
                            dano_inimigo_perto += 0.25 + nivel_ameaca * 0.15
                            dano_person_hit += 4 + nivel_ameaca * 1.5
                            vida_maxima_petro += 15 + nivel_ameaca * 8
                            dano_petro += 0.02 + nivel_ameaca * 0.01
                            dano_boss2 += 3 + nivel_ameaca * 1.2
                            dano_inimigo_longe += 1 + nivel_ameaca * 0.6

                            inimigos_eliminados += 1

                            ganho = int(75 + math.log2(inimigos_eliminados + 1) * 5)
                            pontuacao += ganho
                            pontuacao_exib += ganho

                            if not boss_vivo2:
                                vida_boss2 += 20 + nivel_ameaca * 8
                                vida_maxima_boss2 = vida_boss2
                                vida_boss3 += 25 + nivel_ameaca * 10
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += 30 + nivel_ameaca * 12
                                vida_maxima_boss4 = vida_boss4


                # Controle de dano para o boss
                if boss_vivo2 and onda["rect"].colliderect(pygame.Rect(pos_x_chefe2, pos_y_chefe2, chefe_largura2, chefe_altura2)):
                    boss_id = "boss"  # Identificador único para o boss no dicionário
                    tempo_atual = pygame.time.get_ticks()

                    if boss_id and tempo_atual - boss_atingido_por_onda >= 1500: 
                        vida_boss -= dano_person_hit *2 
                        boss_atingido_por_onda = tempo_atual  # Atualiza o tempo do último dano

                        # Verifica se o boss foi derrotado
                        if vida_boss2 <= 0:
                            frame_porcentagem=frames_chefe2_4
                            rect_boss = pygame.Rect(pos_x_chefe2, pos_y_chefe2, 64, 64)
                            rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                            ataque_vertical_ativo=False
                            ataque_horizontal_ativo=False



                            if rect_boss.colliderect(rect_personagem):
                                if toque == 0:
                                    salvar_atributos()
                                    Musica_tema_Boss2.stop()
                                    pausar_cronometro()
                                    if game_manager:
                                        from game_manager import EstadoJogo
                                        game_manager.mudar_estado(EstadoJogo.JOGO_FASE_3)
                                        raise CleanExit()
                                    else:
                                        import GAME3

                                    toque+=1

            #MODIFICA O TEMPO QUE OS INIMIGOS DISPARAM REFERENTE O BOSS ESTÁ VIVO OU NÃO                
            if not boss_vivo2:
                intervalo_disparo_inimigo = 3500
            else :
                intervalo_disparo_inimigo = random.randint(1800, 4000) 
            for inimigo in inimigos_comum:
                dx = pos_x_personagem - inimigo["rect"].x
                dy = pos_y_personagem - inimigo["rect"].y
                dist = max(40, abs(dx) + abs(dy))
                inimigo["rect"].x += (dx / dist) * velocidade_inimigo2
                inimigo["rect"].y += (dy / dist) * velocidade_inimigo2


                if dx > 0:  # Mova para a direita
                    inimigo["image"] = frames_inimigo_direita2[frame_atual % len(frames_inimigo_direita2)]
                else:  # Mova para a esquerda
                    inimigo["image"] = frames_inimigo_esquerda2[frame_atual % len(frames_inimigo_esquerda2)]

                # Desenhar sombra do inimigo
                desenhar_sombra(tela, inimigo["rect"].x, inimigo["rect"].y, largura_inimigo, altura_inimigo)
                tela.blit(inimigo["image"], inimigo["rect"])
                desenhar_barra_de_vida(tela, inimigo["rect"].x, inimigo["rect"].y - 10, largura_inimigo, 5, inimigo["vida"], inimigo["vida_maxima"])

                tempo_atual = pygame.time.get_ticks()
                if tempo_atual - tempo_ultimo_disparo_inimigo >= intervalo_disparo_inimigo and random.random() <= 0.25:  #frequencia do disparo do sinimigos
                    disparos_inimigos.append(criar_disparo_inimigo((inimigo["rect"].x, inimigo["rect"].y), (pos_x_personagem, pos_y_personagem)))
                    tempo_ultimo_disparo_inimigo = tempo_atual  # Atualize o tempo do último disparo


            personagem_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
            inimigos_rects = [inimigo["rect"] for inimigo in inimigos_comum]

            if imune_tempo_restante > 0:
                imune_tempo_restante -= relogio.get_time()  # Reduz o tempo de imunidade com base no tempo de quadro
            else:
                imune_tempo_restante = 0  # Redefine a imunidade


            if verificar_colisao_personagem_inimigo(personagem_rect, inimigos_rects) and imune_tempo_restante <= 0:

                if tempo_atual - tempo_ultimo_hit_inimigo >= intervalo_hit_inimigo:
                    Dano_pos_resistencia_person = int(((vida_maxima * 0.12) + dano_inimigo_perto) - Resistencia)
                    if aurea == "Vanguarda":
                        for inimigo in inimigos_comum:
                            if personagem_rect.colliderect(inimigo["rect"]):
                                id_inimigo = id(inimigo)
                                tempo_queimadura = pygame.time.get_ticks()
                                inimigos_em_chamas[id_inimigo] = tempo_queimadura

                    if escudo_devota_ativo:
                        escudo_devota_ativo= False
                        pass
                    elif Dano_pos_resistencia_person > 0:
                        vida -= Dano_pos_resistencia_person
                        if aurea == "Impulsiva":
                            eliminacoes_consecutivas_impulsiva = 0  # Perde streak se levar dano
                        eliminacoes_consecutivas = 0
                        bonus_pontuacao = 0
                    tempo_ultimo_hit_inimigo = tempo_atual

                    piscando_vida = True
            # Regenerar o escudo se estiver inativo e o tempo passou
            if aurea == "Devota" and not escudo_devota_ativo and tempo_atual - tempo_ultimo_escudo >= intervalo_escudo:
                escudo_devota_ativo = True
                tempo_ultimo_escudo = tempo_atual



            novos_disparos_inimigos = []
            for disparo_inimigo in disparos_inimigos:
                pos_x_disparo_inimigo, pos_y_disparo_inimigo = disparo_inimigo["rect"].x, disparo_inimigo["rect"].y
                tela.blit(frames_disparo[frame_atual_disparo], (pos_x_disparo_inimigo, pos_y_disparo_inimigo))

                # Atualize a posição do disparo do inimigo
                disparo_inimigo["rect"].x += disparo_inimigo["velocidade"][0]
                disparo_inimigo["rect"].y += disparo_inimigo["velocidade"][1]
                #pygame.draw.rect(tela, (0, 0, 0), disparo_inimigo["rect"], 2)
                if (
                    pos_x_personagem < pos_x_disparo_inimigo < pos_x_personagem + largura_personagem and
                    pos_y_personagem < pos_y_disparo_inimigo < pos_y_personagem + altura_personagem
                ):
                    # O disparo do inimigo atingiu o personagem
                    if not personagem_imovel:
                        Dano_pos_resistencia_person_longe=int((vida_maxima*0.25+dano_inimigo_longe)-Resistencia)
                        if aurea == "Impulsiva":
                            eliminacoes_consecutivas_impulsiva = 0  # Perde streak se levar dano        
                        if Dano_pos_resistencia_person_longe < 0:
                            pass
                        if escudo_devota_ativo:
                            escudo_devota_ativo= False
                            pass
                        else:  
                            vida -=Dano_pos_resistencia_person_longe
                            eliminacoes_consecutivas = 0
                            bonus_pontuacao = 0
                        tempo_ultimo_hit_inimigo = tempo_atual  # Atualize o tempo do último hit do inimigo
                        piscando_vida=True

                        tempo_ultimo_atingido = pygame.time.get_ticks()
                        personagem_imovel = True  # O personagem está imóvel após ser atingido
                        disparos_inimigos.remove(disparo_inimigo)
                    continue
                    # Lógica para controle da imobilização
                tempo_atual = pygame.time.get_ticks()
                if personagem_imovel and tempo_atual - tempo_ultimo_atingido >= tempo_imobilizacao:
                    personagem_imovel = False  # A personagem volta a poder se mexer

                if (
                    0 <= pos_x_disparo_inimigo < largura_mapa and
                    0 <= pos_y_disparo_inimigo < altura_mapa
                ):
                    novos_disparos_inimigos.append(disparo_inimigo)

            # Atualiza a lista de disparos dos inimigos
            disparos_inimigos = novos_disparos_inimigos



            if vida <= 0:
                if trembo:
                    vida = vida_maxima  # Recupera a vida total
                    trembo = False  # Consome o "trembo"
                    imune_tempo_restante = 10000
                    teleportado = True  # Ativa o teleporte aleatório
                    porcentagem_cura= 0.02
                    Tempo_cura=2500
                    pos_x_personagem, pos_y_personagem = gerar_posicao_aleatoria(largura_mapa, altura_mapa, largura_personagem, altura_personagem)
                else:

                    pygame.time.delay(2000)
                    Musica_tema_fases.stop()
                    Som_tema_fases.stop()
                    tela_upgrade_aureas(tela, fonte, moedas_totais)

                    limpar_salvamento()
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.GAME_OVER)
                        raise CleanExit()
                    else:
                        pygame.quit()
                        subprocess.run([python, "Game_Over.py"])
                        sys.exit()



            if piscando_vida:


                if tempo_atual % 500 < 250:  # Altere o valor 500 e 250 conforme necessário
                    # Desenha a barra de vida piscando em vermelho
                    pygame.draw.rect(tela, (255, 0, 0), (posicao_barra_vida[0], posicao_barra_vida[1], largura_barra_vida, altura_barra_vida))
                else:
                    # Desenha a barra de vida normalmente
                    pygame.draw.rect(tela, verde, (posicao_barra_vida[0], posicao_barra_vida[1], (vida / vida_maxima) * largura_barra_vida, altura_barra_vida))


                if tempo_atual - tempo_ultimo_hit_inimigo >= intervalo_hit_inimigo:
                    piscando_vida = False

            tempo_atual = pygame.time.get_ticks()

            if (keys[pygame.K_r]) or r_press:
                r_press=True

                max_inimigos2=4
                intervalo_disparo_inimigo =3000
                velocidade_inimigo2=1.50
                if musica_boss2 == 1:
                    # Defina o volume da música (opcional)
                    ataque_vertical_ativo = True
                    Musica_tema_Boss2.play(loops=-1)
                    musica_boss2+=1


                # Lógica para animar o chefe
                tempo_passado_animacao_chefe2 += relogio.get_rawtime()
                if tempo_passado_animacao_chefe2 >= tempo_animacao_chefe2:
                    tempo_passado_animacao_chefe2 = 0
                    frame_atual_chefe = (frame_atual_chefe + 1) % 2

                if Ultimo_Estalo and vida_boss2 <= Executa_inimigo * vida_maxima_boss2:
                    vida_boss2=0

                if vida_boss2 <= 0:
                    frame_porcentagem=frames_chefe2_4
                    rect_boss = pygame.Rect(pos_x_chefe2, pos_y_chefe2, 64, 64)
                    rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                    ataque_vertical_ativo=False
                    ataque_horizontal_ativo=False



                    if rect_boss.colliderect(rect_personagem):
                        if toque == 0:
                            salvar_atributos()
                            Musica_tema_Boss2.stop()
                            pausar_cronometro()
                            if game_manager:
                                from game_manager import EstadoJogo
                                game_manager.mudar_estado(EstadoJogo.JOGO_FASE_3)
                                raise CleanExit()
                            else:
                                import GAME3

                            toque+=1
                #  onde verifica a colisão dos disparos com o boss


                if boss_vivo2:


                    Musica_tema_fases.stop()
                    # Dentro do loop principal
                    pygame.draw.rect(tela, vermelho, (pos_x_barra_boss2, pos_y_barra_boss2, largura_barra_boss2, altura_barra_boss2))
                    pygame.draw.rect(tela, (143,255,255), (pos_x_barra_boss2, pos_y_barra_boss2, largura_barra_boss2, (vida_boss2 / vida_maxima_boss2) * altura_barra_boss2))
                    pygame.draw.rect(tela, (255, 255, 255), (pos_x_barra_boss2, pos_y_barra_boss2, largura_barra_boss2, altura_barra_boss2), 2)    



                    porcentagem_vida_boss = (vida_boss2 / vida_maxima_boss2) * 100

                    if porcentagem_vida_boss >=90 :
                        frame_porcentagem=frames_chefe2_1


                    elif porcentagem_vida_boss <= 60 and porcentagem_vida_boss >=40:
                        frame_porcentagem=frames_chefe2_2
                        velocidade_ataque_horizontal=1.8
                        velocidade_ataque_vertical=2.6

                    elif porcentagem_vida_boss <= 40 and porcentagem_vida_boss>=10 :
                        frame_porcentagem=frames_chefe2_3
                        velocidade_ataque_horizontal=2.2
                        velocidade_ataque_vertical=3


                    tela.blit(frame_porcentagem[frame_atual_chefe], (pos_x_chefe2, pos_y_chefe2))



                    #  desenha o ataque vertical se estiver ativo
                    if ataque_vertical_ativo:
                        tempo_inicio_ataque = pygame.time.get_ticks()
                        for y in range(posicao_ataque_vertical[1], altura_tela, linha.get_height()):
                            tela.blit(linha, (posicao_ataque_vertical[0], y))
                        # Move o ataque vertical para a esquerda
                        posicao_ataque_vertical = (posicao_ataque_vertical[0] - velocidade_ataque_vertical, posicao_ataque_vertical[1])

                    # Verifica se atingiu a ponta esquerda da tela
                        if posicao_ataque_vertical[0] <= 0:
                            ataque_vertical_ativo = False


                    if ataque_horizontal_ativo:
                        tempo_inicio_ataque_horizontal = pygame.time.get_ticks()
                        for x in range(posicao_ataque_horizontal[0], largura_tela, linha.get_width()):
                            tela.blit(linha, (x, posicao_ataque_horizontal[1]))
                        # Move o ataque horizontal para baixo
                        posicao_ataque_horizontal = (posicao_ataque_horizontal[0], posicao_ataque_horizontal[1] + velocidade_ataque_horizontal)

                        # Verifica se atingiu a parte inferior da tela
                        if posicao_ataque_horizontal[1] >= altura_tela:
                            ataque_horizontal_ativo = False


                    # Verifica o tempo decorrido desde o início do ataque

                    tempo_decorrido_ataque = pygame.time.get_ticks() - tempo_inicio_ataque
                    if tempo_decorrido_ataque >= tempo_espera_ataque:
                    # Verifica se nenhum dos ataques está ativo
                        if not ataque_horizontal_ativo and not ataque_vertical_ativo:
                            # Escolhe aleatoriamente entre ataque horizontal e vertical
                            if random.random() < 0.7:
                            # Ativa o ataque horizontal
                                ataque_horizontal_ativo = True
                                posicao_ataque_horizontal = (0, 0)  # Reinicia na parte superior da tela
                                tempo_decorrido_horizontal = 0
                            else:
                                # Ativa o ataque vertical
                                ataque_vertical_ativo = True
                                velocidade_inimigo2+=0.010
                                posicao_ataque_vertical = (largura_mapa // 0.8, 0)  # Reinicia na ponta superior da tela
                                tempo_decorrido_vertical = 0



                    if ataque_vertical_ativo:
                        tempo_inicio_dano= pygame.time.get_ticks()
                        rect_ataque_vertical = pygame.Rect(posicao_ataque_vertical[0], posicao_ataque_vertical[1], largura_ataque_vertical, altura_tela)
                        # Verifica colisão do ataque vertical com o personagem
                        if rect_ataque_vertical.colliderect(personagem_rect):
                            # O ataque vertical atingiu o jogador
                            if escudo_devota_ativo:
                                escudo_devota_ativo= False
                                pass
                            elif pygame.time.get_ticks() - tempo_ultimo_dano_vertical >= tempo_cooldown_dano_vertical:
                                vida -= int(vida_maxima-vida)*0.15+30+dano_boss2  # Causa dano ao personagem
                                tempo_ultimo_atingido = pygame.time.get_ticks()
                                personagem_imovel = True  # O personagem fica imóvel após ser atingido
                                tempo_ultimo_dano_vertical = pygame.time.get_ticks()  # Atualiza o tempo do último dano


                    if ataque_horizontal_ativo:
                        tempo_inicio_dano_horizontal = pygame.time.get_ticks()
                        rect_ataque_horizontal = pygame.Rect(posicao_ataque_horizontal[0], posicao_ataque_horizontal[1], largura_tela, altura_ataque_horizontal)
                        # Verifica colisão do ataque horizontal com o personagem
                        if rect_ataque_horizontal.colliderect(personagem_rect):
                            if escudo_devota_ativo:
                                escudo_devota_ativo= False
                                pass
                            elif pygame.time.get_ticks() - tempo_ultimo_dano_horizontal >= tempo_cooldown_dano_horizontal:
                                vida -= int(vida_maxima)*0.05+30+dano_boss2  # Causa dano ao personagem
                                tempo_ultimo_atingido = pygame.time.get_ticks()
                                personagem_imovel = True  # O personagem fica imóvel após ser atingido
                                tempo_ultimo_dano_horizontal = pygame.time.get_ticks()  # Atualiza o tempo do último dano

                    tempo_decorrido_horizontal = pygame.time.get_ticks() - tempo_inicio_dano_horizontal
                    if tempo_atual - tempo_ultimo_atingido >= 3000:
                        pass




                    tempo_atual = pygame.time.get_ticks()
                    if personagem_imovel and tempo_atual - tempo_ultimo_atingido >= tempo_imobilizacao:
                        personagem_imovel = False  # A personagem volta a poder se mexer



                for disparo in disparos:
                    pos_x_disparo=disparo["rect"].x 
                    pos_y_disparo=disparo["rect"].y 
                    rect_disparo = pygame.Rect(pos_x_disparo, pos_y_disparo, largura_disparo, altura_disparo)
                    rect_boss = pygame.Rect(pos_x_chefe2, pos_y_chefe2, chefe_largura2, chefe_altura2)

                    if rect_disparo.colliderect(rect_boss):
                        if vida_boss2 > 0:  # Verifica se o chefe está vivo antes de aplicar dano
                            if random.random() <= chance_critico:  # 10% de chance de dano crítico
                                dano = dano_person_hit * 3  # Valor do dano crítico é 3 vezes o dano normal
                                cor = (255, 255, 0)  # Amarelo (RGB)
                                fonte_dano = fonte_dano_critico
                            else:
                                dano = dano_person_hit
                                cor = (255, 0, 0)  # Vermelho (RGB)
                                fonte_dano = fonte_dano_normal

                        # Ativar veneno no Boss com 50% de chance, se ainda não estiver envenenado
                        if random.random() < 0.5 and not boss_envenenado and Poison_Active:
                            boss_envenenado = True
                            dano_por_tick_veneno_boss = vida_boss2 * (Dano_Veneno_Acumulado*0.01) # Exemplo: 0.5% da vida máxima
                            tempo_inicio_veneno_boss = pygame.time.get_ticks()
                            ultimo_tick_veneno_boss = pygame.time.get_ticks()

                        # Renderizar texto do dano
                        texto_dano = fonte_dano.render("-" + str(int(dano)), True, cor)
                        pos_texto = (pos_x_chefe2 + chefe_largura2 // 2 - texto_dano.get_width() // 2, pos_y_chefe2 - 20)
                        tempo_texto_dano = pygame.time.get_ticks()
                        vida_boss2 -= dano
                        disparos.remove(disparo)

                        # Roubo de vida
                        if random.random() < roubo_de_vida:
                            vida += (vida_maxima - vida) * quantidade_roubo_vida

                # Aplicar dano de veneno no Boss se ele estiver envenenado
                if boss_envenenado:
                    tempo_atual = pygame.time.get_ticks()

                    # Aplicar dano a cada 500 ms
                    if tempo_atual - ultimo_tick_veneno_boss >= 500:
                        vida_boss2 -= dano_por_tick_veneno_boss
                        ultimo_tick_veneno_boss = tempo_atual

                    # Exibir texto do dano de veneno (1.5 segundos)
                    if tempo_atual - ultimo_tick_veneno_boss <= 250:
                        dano_veneno_texto = "-" + str(int(dano_por_tick_veneno_boss))
                        texto_dano_veneno = fonte_veneno.render(dano_veneno_texto, True, (0, 255, 0))
                        texto_dano_veneno_borda = fonte_veneno.render(dano_veneno_texto, True, (0, 0, 0))
                        pos_texto = (pos_x_chefe2 + chefe_largura2 // 2 - texto_dano_veneno.get_width() // 2, pos_y_chefe2 - 30)
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0] - 1, pos_texto[1]))
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0] + 1, pos_texto[1]))
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0], pos_texto[1] - 1))
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0], pos_texto[1] + 1))
                        tela.blit(texto_dano_veneno, pos_texto)

                    # Desativar o veneno após o tempo de duração
                    if tempo_atual - tempo_inicio_veneno_boss >= duracao_veneno_boss:
                        boss_envenenado = False






            total_cartas_compradas = sum(cartas_compradas.values())
            custo_carta_atual = custo_base_carta + (total_cartas_compradas * custo_por_carta)
            # Verifica se a pontuação atingiu 1500 e se o jogador pressionou 'Q'
            if pontuacao_exib >= custo_carta_atual and keys[config_teclas["Comprar na loja"]] or (joystick and joystick.get_button(3)):
                pontuacao_exib -= custo_carta_atual
                pontuacao_magia -= custo_carta_atual


                ret = tela_de_pausa(velocidade_personagem, intervalo_disparo,vida,largura_disparo, altura_disparo,trembo,dano_person_hit,chance_critico,roubo_de_vida,
                                    quantidade_roubo_vida,tempo_cooldown_dash,vida_maxima,Petro_active,Resistencia,vida_petro,vida_maxima_petro,dano_petro,xp_petro,petro_evolucao,Resistencia_petro,
                                    Chance_Sorte,Poison_Active,Dano_Veneno_Acumulado,Executa_inimigo,Ultimo_Estalo,mostrar_info,Mercenaria_Active,Valor_Bonus,dispositivo_ativo,Tempo_cura,porcentagem_cura,cartas_compradas,pontuacao_exib)
                velocidade_personagem = ret[0]
                intervalo_disparo = ret[1]
                vida = ret[2]
                largura_disparo =ret[3]
                altura_disparo =ret[4]
                trembo= ret[5]
                dano_person_hit= ret[6]
                chance_critico= ret[7]
                roubo_de_vida= ret[8]
                quantidade_roubo_vida= ret[9]
                tempo_cooldown_dash= ret[10]
                vida_maxima= ret[11]
                Petro_active= ret[12]
                Resistencia=  ret[13]
                vida_petro= ret[14]
                vida_maxima_petro= ret[15]
                dano_petro= ret[16]
                xp_petro= ret[17]
                petro_evolucao= ret[18]
                Resistencia_petro= ret[19]
                Chance_Sorte= ret[20]
                Poison_Active= ret[21]
                Dano_Veneno_Acumulado= ret[22]
                Executa_inimigo= ret[23]
                Ultimo_Estalo= ret[24]
                Mercenaria_Active= ret[25]
                Valor_Bonus= ret[26]
                dispositivo_ativo=ret[27]
                Tempo_cura=ret[28]
                porcentagem_cura=ret[29]
                cartas_compradas= ret[30]
                pontuacao_exib= ret[31]





            posicao_barra_vida = (80, altura_mapa - (altura_mapa - 34))
            fonte = pygame.font.Font(None, int(altura_barra_vida*1))
            texto_pontuacao = fonte.render(f'{pontuacao_exib}/{custo_carta_atual}', True, (250, 255,255))
            fonte_vida = pygame.font.Font(None, int(altura_barra_vida*0.9))
            texto_vida = fonte_vida.render(f'{int(vida)}/{int(vida_maxima)}', True, (255, 255, 255))

            # Renderiza o texto de pontuação com uma borda
            texto_pontuacao_borda = fonte.render(f'{pontuacao_exib}/{custo_carta_atual}', True, (0, 0, 0))  # Cor preta para a borda
            # Desenha o texto da borda um pouco deslocado para criar o efeito de contorno
            tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 - 1, altura_mapa*0.118 - 1))
            tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 + 1, altura_mapa*0.118 - 1))
            tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 - 1, altura_mapa*0.118 + 1))
            tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 + 1, altura_mapa*0.118 + 1))

            # Desenha o texto da pontuação por cima da borda
            tela.blit(texto_pontuacao, (largura_mapa*0.075, altura_mapa*0.118))





            # Calculando o ângulo do preenchimento em graus
            angulo_preenchimento = (pontuacao_magia / 735) * 360  # ângulo em graus
            # Preenchendo a parte do círculo
            if angulo_preenchimento > 0:
                pontos = []
                for i in range(int(angulo_preenchimento) + 1):
                    radianos = math.radians(i - 90) 
                    x = centro_circulo[0] + raio_circulo * math.cos(radianos)
                    y = centro_circulo[1] + raio_circulo * math.sin(radianos)
                    pontos.append((x, y))
                pygame.draw.polygon(tela, (53, 239, 252), [centro_circulo] + pontos) 

            tela.blit(imagem_relogio, posicao_imagem_relogio)




            porcentagem_vida_personagem = (vida / vida_maxima) * 100
            if aurea == "Devota" and escudo_devota_ativo:
                cor_barra = (0, 150, 255)  # Azul para indicar o escudo ativo
            else:
                cor_barra = calcular_cor_barra_de_vida(porcentagem_vida_personagem)
            pygame.draw.rect(tela, cor_barra, (posicao_barra_vida[0], posicao_barra_vida[1], (vida / vida_maxima) * largura_barra_vida, altura_barra_vida))
            pygame.draw.rect(tela, (0, 0, 0), (posicao_barra_vida[0], posicao_barra_vida[1], largura_barra_vida, altura_barra_vida), 2)


            # Renderiza o texto de vida com uma borda
            texto_vida_borda = fonte_vida.render(f'{int(vida)}/{int(vida_maxima)}', True, (0, 0, 0))  # Cor preta para a borda
            # Desenha o texto da borda um pouco deslocado para criar o efeito de contorno
            tela.blit(texto_vida_borda, (posicao_barra_vida[0]*2 - 1, posicao_barra_vida[1] + 5 - 1))
            tela.blit(texto_vida_borda, (posicao_barra_vida[0]*2 + 1, posicao_barra_vida[1] + 5 - 1))
            tela.blit(texto_vida_borda, (posicao_barra_vida[0]*2 - 1, posicao_barra_vida[1] + 5 + 1))
            tela.blit(texto_vida_borda, (posicao_barra_vida[0]*2 + 1, posicao_barra_vida[1] + 5 + 1))

            # Desenha o texto da vida por cima da borda
            tela.blit(texto_vida, (posicao_barra_vida[0]*2, posicao_barra_vida[1] + 5))
            tela.blit(imagem_vida, posicao_vida)

            if area_cartas.collidepoint(pos_x_personagem, pos_y_personagem):  
                cartas_visiveis = False  # Se o personagem está na área, esconda as cartas
            else:
                cartas_visiveis = True  # Se o personagem não está na área, mostre as cartas
            # Remova o texto após 2 segundos
            if texto_dano is not None and pygame.time.get_ticks() - tempo_texto_dano >= 250:
                texto_dano = None
            cooldowns = {
                "disparo": max(0, tempo_atual - tempo_ultimo_disparo >= intervalo_disparo),
                "teleporte": max(0, pygame.time.get_ticks() - tempo_ultimo_dash > tempo_cooldown_dash),
                "onda": max(0, tempo_atual - tempo_ultimo_uso_habilidade >= cooldown_habilidade),
                "loja": 1 if pontuacao_exib >= custo_carta_atual else 0,  
            }
            if not area_icones.colliderect(
            (pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
            ):
                # Desenhar habilidades na tela
                desenhar_habilidades(tela, cooldowns,dispositivo_ativo)
            if eliminacoes_consecutivas > 0:
                fonte_combo = pygame.font.Font(None, 36)  # Tamanho maior para o combo
                fonte_bonus = pygame.font.Font(None, 28)  # Tamanho menor para o bônus

                # Texto do combo
                texto_combo = f"Combo: {eliminacoes_consecutivas}"
                posicao_combo = (largura_mapa - 200, 50)  
                desenhar_texto_com_contorno(tela, texto_combo, fonte_combo, (255, 255, 255), (0, 0, 0), posicao_combo)

                # Texto do bônus
                texto_bonus = f"Bônus: +{bonus_pontuacao}"
                posicao_bonus = (largura_mapa - 200, 90) 
                desenhar_texto_com_contorno(tela, texto_bonus, fonte_bonus, (255, 255, 255), (0, 0, 0), posicao_bonus)

            # Desenhe o texto na tela
            if texto_dano is not None:
                tela.blit(texto_dano, pos_texto)
            for inimigo in inimigos_comum:
                i_id = id(inimigo)
                if i_id in inimigos_em_chamas:
                    if tempo_atual - inimigos_em_chamas[i_id] <= duracao_incendio_vanguarda:
                        if tempo_atual - inimigo.get("ultimo_tick_queimando", 0) >= 1000:
                            inimigo["ultimo_tick_queimando"] = tempo_atual

                            # Escalonamento: base 1% a 3% da vida máxima, mais 0.2% base e 0.5% max por nível do upgrade
                            nivel_vanguarda = upgrades.get("Vanguarda", 0)
                            limite_max = 0.03 + (nivel_vanguarda * 0.005)
                            proporcao_base = 0.01 + (nivel_vanguarda * 0.002)
                            proporcao = min(limite_max, proporcao_base + (eliminacoes_consecutivas * 0.0005))
                            dano_fogo = int(inimigo.get("vida_maxima", 100) * proporcao)

                            inimigo["vida"] -= dano_fogo

                            efeitos_texto.append({
                                "texto": f"-{dano_fogo}",
                                "x": inimigo["rect"].x,
                                "y": inimigo["rect"].y - 20,
                                "tempo_inicio": tempo_atual,
                                "cor": (255, 60, 0)
                            })

                            if inimigo["vida"] <= 0:
                                inimigos_em_chamas.pop(i_id, None)
                    else:
                        inimigos_em_chamas.pop(i_id, None)
            for moeda in moedas_soltadas:
                tela.blit(moeda["image"], moeda["rect"])


            tela.blit(cursor_imagem, (mouse_x, mouse_y))
            exibir_cronometro(tela)
            pygame.display.flip()
            FPS.tick(config_graficos.get("fps_limite", 60))  # Limita a taxa de quadros conforme configuração


        # Encerrar o Pygame
        pygame.quit()
        sys.exit()
    except CleanExit:
        return
    finally:
        _sys.exit = _orig_sys_exit
        _os._exit = _orig_os_exit
        if _orig_builtins_exit:
            _builtins.exit = _orig_builtins_exit


if __name__ == '__main__':
    executar_jogo()
