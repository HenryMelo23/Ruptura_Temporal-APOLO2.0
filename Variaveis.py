import pygame

import random

import sys

import time

import math

import os
import json

from Config_Teclas import  carregar_config_teclas

config_teclas = carregar_config_teclas()



pygame.init()

relogio = pygame.time.Clock()



# Inicializa display OCULTO para permitir .convert_alpha() nos sprites.

# Nenhuma janela aparece — o display real é criado depois em cada GAME file.

largura_tela, altura_tela = int(1360*0.8), int(768*1)

largura_mapa, altura_mapa = largura_tela, altura_tela

_display_init = pygame.display.set_mode((largura_mapa, altura_mapa), pygame.HIDDEN)



# Configurações do mapa

mapa_path1 = "Sprites/Fase1.png"

mapa_path2 = "Sprites/Fase2.png"

mapa_path3 = "Sprites/Fase3.png"

mapa_path4 = "Sprites/Fase4.png"

mapa_path5 = "Sprites/Fase5-1.png"

mapa_path6 = "Sprites/Fase6.png"

mapa_path7 = "Sprites/Fase7.png"

python = sys.executable

cooldown_ativo_img = pygame.transform.scale(pygame.image.load("Sprites/cooldown2.png").convert_alpha(), (50, 50))

cooldown_concluido_img = pygame.transform.scale(pygame.image.load("Sprites/cooldown.png").convert_alpha(), (50, 50))

r_press=False

dispositivo_ativo = "teclado"





# Variáveis de conexão (para medir ping) e qualquer outra variavel para rede

ultimo_ping = 0

ping_atual = 0

tempo_envio_ping = 0

cor_ping = (0, 255, 0)

loja_aberta = False

esperando_outro_host = False

esperando_outro_join = False

ja_enviado_sair_espera = False

host_ativo = False  # Variável para verificar se o host está ativo

cliente_ativo = False  # Variável para verificar se o cliente está ativo

jogador_morto = False

tempo_morte = 0

tempo_revive = 15  # 15 segundos

jogador_remoto_morto = False  # <-- adiciona isso antes do loop principal

outro_jogador_morto = False

alvo_atual = "host"  # inimigos começam perseguindo o host

intervalo_troca_alvo = 20000  # 20 segundos

tempo_ultima_troca_alvo= 0

pos_x_player2, pos_y_player2= 0 , 0

ultimo_envio_estado = time.time()

intervalo_envio = 0.05  # envia a cada 50 ms (20 vezes por segundo)

ultima_vida_enviada= 0

pronto_para_comecar= False

estado_jogo= "Rodando"

conn = None  # <- adiciona isso no topo, antes dos if

direcao_atual_p2= "Down"

convite_boss_ativo= False

iniciar_boss= False

Safe=False



########################################## VARIAVEIS MAPA

cont=2

centro_horizontal_tela = largura_mapa // 2

espacamento = 100

##########################################

########################################## BOSS 1

vida_boss = 5000

vida_maxima_boss1= vida_boss

chefe_largura, chefe_altura = largura_tela * 0.2, altura_tela * 0.2

pos_x_chefe, pos_y_chefe = largura_mapa // 2 - chefe_largura // 2, altura_mapa // 2 - chefe_altura // 2

tempo_animacao_chefe = 300  # Tempo em milissegundos entre cada quadro

tempo_passado_animacao_chefe = 0

frame_atual_chefe = 0

frames_chefe1_1 = [

    pygame.transform.scale(pygame.image.load("Sprites/Boss1.png").convert_alpha(), (chefe_largura, chefe_altura)),

    pygame.transform.scale(pygame.image.load("Sprites/Boss2.png").convert_alpha(), (chefe_largura, chefe_altura))

]

frames_chefe1_2 = [

    pygame.transform.scale(pygame.image.load("Sprites/Boss3.png").convert_alpha(), (chefe_largura, chefe_altura)),

    pygame.transform.scale(pygame.image.load("Sprites/Boss4.png").convert_alpha(), (chefe_largura, chefe_altura))

]

frames_chefe1_3 = [

    pygame.transform.scale(pygame.image.load("Sprites/Boss5.png").convert_alpha(), (chefe_largura, chefe_altura)),

    pygame.transform.scale(pygame.image.load("Sprites/Boss6.png").convert_alpha(), (chefe_largura, chefe_altura))

]

frames_chefe1_4 = [

    pygame.transform.scale(pygame.image.load("Sprites/peça.png").convert_alpha(), (32, 32)),

    pygame.transform.scale(pygame.image.load("Sprites/peça2.png").convert_alpha(), (32, 32))

]



tempo_ultima_mudanca_direcao_boss = pygame.time.get_ticks()

# Defina uma variável de estado para controlar o comportamento do chefe

comportamento_boss = "aleatorio"  # Comece com movimento aleatório

ultima_direcao_boss = 'aleatorio'

Velocidade_boss=2

ultima_direcao_boss = random.choice(['up', 'down', 'left', 'right'])  # Inicialize a direção do boss   

tempo_ultimo_dano_atingido = pygame.time.get_ticks()

intervalo_dano_atingido = 1500  # 2 segundos

largura_barra_boss = 20

altura_barra_boss = 200

pos_x_barra_boss = largura_mapa - 30

pos_y_barra_boss = altura_tela // 2 - altura_barra_boss // 2



tempo_ultimo_dano_ataque=0

em_ataque_especial = False

jogador_posicoes = []

imagens_ataque = [

    pygame.transform.scale(pygame.image.load("Sprites/Bolha1.png").convert_alpha(), (100, 180)),

    pygame.transform.scale(pygame.image.load("Sprites/Bolha2.png").convert_alpha(), (100, 180)),

    pygame.transform.scale(pygame.image.load("Sprites/Bolha3.png").convert_alpha(), (100, 180)),

    pygame.transform.scale(pygame.image.load("Sprites/Bolha4.png").convert_alpha(), (100, 180)),

    pygame.transform.scale(pygame.image.load("Sprites/Bolha5.png").convert_alpha(), (100, 180))

]

tempo_ataque_especial = 0

intervalo_troca = 850  # 2 segundos para trocar entre as imagens

hitboxes = {}

########################################## BOSS 2



chefe_largura2, chefe_altura2 = largura_tela * 0.2, altura_tela * 0.3

pos_x_chefe2, pos_y_chefe2 = largura_mapa // 1.1 - chefe_largura // 2, altura_mapa // 2 - chefe_altura // 1

tempo_animacao_chefe2 = 1000  # Tempo em milissegundos entre cada quadro

tempo_passado_animacao_chefe2 = 0

frame_atual_chefe = 0

frames_chefe2_1 = [

    pygame.transform.scale(pygame.image.load("Sprites/Boss2_1.png").convert_alpha(), (chefe_largura2, chefe_altura2)),

    pygame.transform.scale(pygame.image.load("Sprites/Boss2_2.png").convert_alpha(), (chefe_largura2, chefe_altura2))

]

frames_chefe2_2 = [

    pygame.transform.scale(pygame.image.load("Sprites/Boss2_1.png").convert_alpha(), (chefe_largura2, chefe_altura2)),

    pygame.transform.scale(pygame.image.load("Sprites/Boss2_2.png").convert_alpha(), (chefe_largura2, chefe_altura2))

]

frames_chefe2_3 = [

    pygame.transform.scale(pygame.image.load("Sprites/Boss2_1.png").convert_alpha(), (chefe_largura2, chefe_altura2)),

    pygame.transform.scale(pygame.image.load("Sprites/Boss2_2.png").convert_alpha(), (chefe_largura2, chefe_altura2))

]



frames_chefe2_4 = [

    pygame.transform.scale(pygame.image.load("Sprites/peça.png").convert_alpha(), (32, 32)),

    pygame.transform.scale(pygame.image.load("Sprites/peça2.png").convert_alpha(), (32, 32))

]

frame_porcentagem=frames_chefe2_1

boss_vivo2=True

vida_boss2 = 8000

vida_maxima_boss2= vida_boss2

largura_barra_boss2 = 20

altura_barra_boss2 = 200

pos_x_barra_boss2 = largura_mapa - 30

pos_y_barra_boss2 = altura_tela // 4 - altura_barra_boss // 1.3



########################################## BOSS 4

boss_vivo4=True

zonas_nulas = []

contador_colisoes = 0

vida_planeta=150

# Organizando os frames do Boss em uma lista

chefe_largura4, chefe_altura4 = largura_tela * 0.2, altura_tela * 0.3





# Posição do boss (canto direito, centro vertical

frames_chefe4_1 = [

    pygame.transform.scale(pygame.image.load("Sprites/Boss4_1.png").convert_alpha(), (chefe_largura4, chefe_altura4)), 

    pygame.transform.scale(pygame.image.load("Sprites/Boss4_3.png").convert_alpha(), (chefe_largura4, chefe_altura4))

]





frames_vortex = [

    pygame.image.load("Sprites/Vortex1_1.png").convert_alpha(),

    pygame.image.load("Sprites/Vortex1_2.png").convert_alpha()

]



sprite_disparo_boss = [

    pygame.transform.scale(pygame.image.load("Sprites/Planet1_1.png").convert_alpha(), (100, 100)),

    pygame.transform.scale(pygame.image.load("Sprites/Planet1_2.png").convert_alpha(), (100, 100))

]



# Índice do frame atual da galáxia

indice_frame_vortex = 0



# Tempo de troca de frame da galáxia

intervalo_frame_vortex = 500  # Troca a cada 500 ms





estado_boss_atacando = False

tempo_ataque = 0  

current_frame_index = 0



boss_rect = frames_chefe4_1[current_frame_index].get_rect()



boss_rect.center = (largura_tela - boss_rect.width // 2, altura_tela // 2)



pos_x_boss4 = largura_tela - chefe_largura4  # Alinha à direita

pos_y_boss4 = altura_tela // 3 # Centraliza no eixo Y



last_frame_change = pygame.time.get_ticks()

frame_interval = 1000 



rect_boss = pygame.Rect(pos_x_boss4, pos_y_boss4, chefe_largura4, chefe_altura4)

current_frame_disparo_boss = 0

tempo_frame_disparo_boss = 0  # Para controlar a troca de frames

intervalo_frame_disparo_boss = 200  # Intervalo em milissegundos



projetil_lista = []



ultimo_disparo = pygame.time.get_ticks()

intervalo_disparo_Boss_4 = 6000 





vida_boss4 = 10000

vida_maxima_boss4 = vida_boss4

largura_barra_boss4 = 20

altura_barra_boss4 = 200

pos_x_barra_boss4 = largura_mapa - 30

pos_y_barra_boss4 = altura_tela // 2 - altura_barra_boss4 // 2

def calcular_posicao_boss(boss_rect):

    # Posição central do Boss

    pos_x_boss = boss_rect.centerx

    pos_y_boss = boss_rect.centery

    return pos_x_boss, pos_y_boss



tempo_ultimo_dano_vortex = 0 





# Altura e quantidade de sprites

altura_sprite_disparo_boss2 = 10

quantidade_sprites_boss2 = 16

linha = pygame.image.load("Sprites/Onda_Boss2.png").convert_alpha()

ataque_vertical_ativo = False

posicao_ataque_vertical = (0, 0)

velocidade_ataque_vertical = 2  

tempo_espera_ataque = 3000  # Tempo em milissegundos (1 segundo)

tempo_cooldown_dano_vertical = 1000  # Tempo de cooldown em milissegundos

tempo_ultimo_dano_vertical = pygame.time.get_ticks()  # Inicializa o tempo do último dano

largura_ataque_vertical = 20 

altura_ataque_vertical = 100 



tempo_inicio_dano_horizontal= pygame.time.get_ticks()  # Inicializa o tempo do último dano



tempo_ultimo_dano_horizontal = pygame.time.get_ticks()  # Inicializa o tempo do último dano

ataque_horizontal_ativo = False

tempo_cooldown_dano_horizontal = 1000  # Tempo de cooldown em milissegundos

posicao_ataque_horizontal = (0, 0)

velocidade_ataque_horizontal = 1

tempo_inicio_ataque_horizontal = 0

altura_ataque_horizontal=20

# Inicialize as variáveis relacionadas ao tempo antes do loop principal do jogo

tempo_inicio_ataque_vertical = 0

tempo_inicio_ataque_horizontal = 0



############################################ Boss 3

vida_boss3 = 20000

vida_maxima_boss3=vida_boss3

largura_barra_boss3 = 20

altura_barra_boss3 = 200

pos_x_barra_boss3 = largura_mapa - 30

pos_y_barra_boss3 = altura_tela // 4 - altura_barra_boss // 1.3

Boss_vivo3= False







#########################################  Condicionais

# Variável para armazenar a pontuação

pontuacao = 0

pontuacao_exib=500

pontuacao_magia=0

vida_maxima = 450

vida = vida_maxima  # Valor inicial da vida

largura_barra_vida = int(largura_tela*0.17)

altura_barra_vida = 20

posicao_circulo = (20, altura_mapa * 0.09)  # mesma posição da barra de magia

raio_circulo = int(largura_mapa * 0.025)  # ajustando o tamanho do círculo

centro_circulo = (posicao_circulo[0] + raio_circulo, posicao_circulo[1] + raio_circulo)

imagem_relogio = pygame.image.load("Sprites/relogio.png").convert_alpha()

imagem_relogio = pygame.transform.scale(imagem_relogio, (raio_circulo * 2.6, raio_circulo * 2.6))  

posicao_imagem_relogio = (13, altura_mapa * 0.074) 

Executa_inimigo=0.05

Ultimo_Estalo=False

imagem_vida=pygame.image.load("Sprites/vida.png").convert_alpha()

imagem_vida = pygame.transform.scale(imagem_vida, (largura_tela* 0.25, altura_tela*0.20))

posicao_vida = (13, -40)  

Chance_Sorte=0.01

Poison_Active=False

boss_envenenado = False

dano_por_tick_veneno_boss = 0

tempo_inicio_veneno_boss = 0

ultimo_tick_veneno_boss = 0

duracao_veneno_boss = 4000 

fonte_hit= "Texto/breakaway.ttf"

#Fonte para tipos de dano

fonte_dano_normal = pygame.font.Font(fonte_hit, 26)

fonte_dano_critico = pygame.font.Font(fonte_hit, 43)

fonte_veneno = pygame.font.Font(fonte_hit, 16)

Dano_Veneno_Acumulado=0.05

moedas_soltadas = []  # cada moeda é um dicionário com 'rect' e 'imagem'

moedas_coletadas=0

#########################################  CORES_GERAIS



amarelo= (255, 255, 0)

vermelho=(255, 0, 0)

verde=(0, 255, 0)

azul = (0, 0, 255)



######################################### INIMIGOS_COMUNS

inimigos_comum = []

inimigos_eliminados = 0

intervalo_hit_inimigo = 700  

inimigos_atingidos_por_onda = {}

if largura_tela == 1366:

    vel_inimig= 1  

elif largura_tela == 1920:

    vel_inimig= 1

elif largura_tela <= 1360:

    vel_inimig= 1

Velocidade_Inimigos_1=1.8

max_inimigos=6

max_inimigos2=4

max_inimigos3=5

max_inimigos4=4

distancia_minima_inimigos = 50  # Ajuste conforme necessário

largura_inimigo, altura_inimigo = largura_tela*0.05, altura_tela*0.08

frames_inimigo = [pygame.transform.scale(pygame.image.load("Sprites/inimig1.png").convert_alpha(), (largura_inimigo, altura_inimigo)),

                 pygame.transform.scale(pygame.image.load("Sprites/inimig2.png").convert_alpha(), (largura_inimigo, altura_inimigo))]



frames_inimigo2=[pygame.transform.scale(pygame.image.load("Sprites/inimig3.png").convert_alpha(), (100, 100)),

                 pygame.transform.scale(pygame.image.load("Sprites/inimig4.png").convert_alpha(), (102, 102))]

frames_inimigo_esquerda2 = [pygame.transform.scale(pygame.image.load("Sprites/inimigo_direita2-1.png").convert_alpha(), (largura_inimigo, altura_inimigo)),

                           pygame.transform.scale(pygame.image.load("Sprites/inimigo_direita2-2.png").convert_alpha(), (largura_inimigo, altura_inimigo))]

frames_inimigo_direita2 = [pygame.transform.scale(pygame.image.load("Sprites/inimigo_esquerda2-1.png").convert_alpha(), (largura_inimigo, altura_inimigo)),

                          pygame.transform.scale(pygame.image.load("Sprites/inimigo_esquerda2-2.png").convert_alpha(), (largura_inimigo, altura_inimigo))]









######################################### PERSONAGEM

direcao_atual = 'stop'  # Direção inicial

largura_personagem, altura_personagem = 54, 80

# Defina diretamente a Largura e Altura (L, A) da imagem para cada direção.

# A caixa transparente ao redor continua sendo 54x80 para manter os pés da personagem sempre no chão.

dimensoes_direcao_personagem = {

    'stop': (54, 80),

    'up':   (51, 77),

    'down': (51, 77),

    'left': (52, 76),  # Ajuste exato em pixels

    'right': (52, 76), 

    'disp': (54, 80)

}

angulo_diagonal_personagem = 15 # Graus de inclinação ao andar na diagonal

angulo_inclinacao_personagem = 0  # Ângulo de rotação atual do frame (calculado em tempo real)

ultima_direcao_animacao = 'stop'  # Rastreador de direção anterior para resetar animação

pos_x_personagem, pos_y_personagem = 100, 100

Resistencia=35

xp_petro=1

dano_inimigo_perto=30

velocidade_personagem = 3

intervalo_disparo = 800

dano_person_hit=35

tipo_buff_impulsiva = None

tempo_inicio_buff_impulsiva = 0

tempo_buff_impulsiva = 5000  # 5 segundos



eliminacoes_consecutivas_impulsiva = 0  # Contador de inimigos eliminados

dano_person_hit_base = dano_person_hit

velocidade_personagem_base = velocidade_personagem



chance_critico=0.02

roubo_de_vida=0.0 # Chance de Roubo de Vida

quantidade_roubo_vida=0.0 # Porcentagem de vida Recuperada baseada na vida perdida 

queijo_geracao=1

dano_boss=90

Dano_Boss_Habilit= 100

dano_inimigo_longe=24

largura_onda, altura_onda = 90, 90

velocidade_onda = 12

tempo_ultimo_uso_habilidade = 0

cooldown_habilidade = 10000  # Cooldown de 3 segundos

ondas = []

correntes_eletricas = []

duracao_frame_onda = 100

eliminacoes_consecutivas = 0

bonus_pontuacao = 0

Mercenaria_Active = False

Valor_Bonus=25

Tempo_cura=2500

porcentagem_cura=0.005

tempo_ultima_regeneracao=0



inimigos_em_chamas = {}  # id(inimigo): tempo_inicio

duracao_incendio_vanguarda = 5000  # 5 segundos



########################################## BOSS 5 (GEO-UMBRA)

# --- MEMÓRIA PERSISTENTE DA GEO-UMBRA (REVISADA) ---

direcao_boss = 'stop'

estado_atual_ia = {

    'ultimo_ataque': 0, 

    'intervalo': 1000, 

    'projeteis': [], 

    'confianca': 0.5,

    'lead': 0.8, 

    'erros_d': 0, 

    'fase_tele': "espera", 

    'proj_tele': None,

    'dano_recente': 0, 

    'ultimo_teleporte': 0, 

    'furia_fase': "espera",

    'ultimo_furia': 0, 

    'angulo_furia': 0, 

    'centro_mapa': (largura_mapa // 2, altura_mapa // 2),

    'f_fuga_x': 0, 

    'f_fuga_y': 0, 

    'parede_ativa': False,

    'ultimo_parede': 0, 

    'ultimo_tick_cura': 0,

    'alvo_ia': (largura_mapa // 2, altura_mapa // 2), # Inicia olhando para o centro

    'ultimo_alvo_tempo': 0,

    'vel_x': 0,

    'vel_y': 0

}

mapas_disponiveis = [ mapa_path1, mapa_path2, mapa_path3, mapa_path4, mapa_path6, mapa_path7]

trauma_umbra_acumulado = 0

# Sistema de Hemorragia (Fase 6)

player_hemorragia_ativa = False

tempo_fim_hemorragia = 0

penalidade_cura_percentual = 0.0

player_em_chamas = False

tempo_fim_chamas = 0

multiplicador_chamas = 0

ultimo_tick_chamas = 0

particulas_fogo_player = []

esferas_energia_umbra = []

tempo_ultima_esfera_umbra = 0

# Criação de superfícies pré-renderizadas para performance (flocos de neve)

floco_superficie = pygame.Surface((4, 4), pygame.SRCALPHA)

pygame.draw.circle(floco_superficie, (255, 255, 255, 230), (2, 2), 2)



cristal_superficie = pygame.Surface((6, 6), pygame.SRCALPHA)

# Desenha um pequeno losango azulado para parecer gelo

pygame.draw.polygon(cristal_superficie, (100, 230, 255, 200), [(3, 0), (6, 3), (3, 6), (0, 3)])



largura_mascara = int(largura_mapa * 3)

altura_mascara = int(altura_mapa * 3)

centro_mascara = (largura_mascara // 2, altura_mascara // 2)

raio_visao = 110 



img_cegueira = pygame.Surface((largura_mascara, altura_mascara), pygame.SRCALPHA)

img_cegueira.fill((0, 0, 0, 245)) 



pygame.draw.circle(img_cegueira, (0, 0, 0, 0), centro_mascara, raio_visao)



for i in range(25):

    alfa_borda = int(245 * (i / 25))

    pygame.draw.circle(img_cegueira, (0, 0, 0, alfa_borda), centro_mascara, raio_visao + i, 2)



em_transicao_mapa = False

inicio_transicao_mapa = 0

duracao_transicao_mapa = 600

mapa_antigo = None

mapa_novo = None

blocos_transicao = []

tamanho_bloco_transicao = 40

estado_atual_ia['parede_ativa'] = False

estado_atual_ia['ultimo_sifon_fim'] = 0  # Crucial para o cooldown tático

historico_posicao_player = [] 

vida_base_umbra = 5800000

fator_escalonamento = (dano_person_hit *0.10) # proporção

vida_maxima_umbra = vida_base_umbra + (1 + fator_escalonamento)

vida_umbra = vida_maxima_umbra

projeteis_boss = []

tempo_ultimo_ataque_boss = 0

velocidade_tiro_boss = 7

projetil_teleporte = None

fase_teleporte = "espera" 

dano_recente_boss = 0

tempo_ultimo_reset_dano = 0

distancia_player_boss = 0

intervalo_boss = 4000              # Cooldown inicial (2 segundos)

tempo_ultimo_teleporte_boss = 0  # Marco zero do teleporte

# --- CÉREBRO ADAPTATIVO (Sincronizado) ---

erros_preditivos = 0

erros_diretos = 0

confianca_predicao = 0.6  # 60% de chance inicial de prever o futuro

ajuste_lead = 0.6         # Multiplicador de antecipação inicial

# Define o tamanho boss 5 (desvinculado do personagem)

largura_boss, altura_boss = 56 , 82

dimensoes_direcao_boss = {

    'stop': (largura_boss, altura_boss),

    'up': (largura_boss, altura_boss),

    'down': (largura_boss, altura_boss),

    'left': (largura_boss, altura_boss),

    'right': (largura_boss, altura_boss),

    'ataque': (largura_boss, altura_boss),

    'ataque2': (largura_boss, altura_boss),

    'ataque3': (largura_boss, altura_boss),

    'escudo': (int(largura_boss * 1.4), int(altura_boss * 1.4))

}

largura_escudo, altura_escudo = int(largura_boss * 1.4), int(altura_boss * 1.4)

ultimo_parede_tempo = pygame.time.get_ticks()

parede_ativa = False

parede_rect = None

raio_aura_protecao = 95

tempo_ultimo_parede_boss = 0 # Variável global que mantém a memória

# --- ESTADOS INICIAIS DO BOSS 5 ---

moedas_totais=0

direcao_boss = 'stop'

frame_boss = 0

tempo_passado_boss = 0

pos_x_umbra = (largura_mapa // 2) - (largura_boss // 2)

pos_y_umbra = (altura_mapa // 2) - (altura_boss // 2)

boss_final_ativo = True

tempo_ultimo_dano_boss = 0

fase_furia = "espera"

tempo_ultima_furia = pygame.time.get_ticks()

angulo_espiral = 0

forca_fuga_x, forca_fuga_y = 0, 0

erros_player_contagem = 0

estado_mov_umbra = {

    'alvo_x': pos_x_umbra,

    'alvo_y': pos_y_umbra,

    'ultimo_alvo_tempo': 0,

    'dano_recente': 0,

    'ultimo_desvio_boss': 0 # Novo controle de decisão

}

modo_atual = "GHOST"



frames_onda_cinetica = [

    pygame.image.load(f"Sprites/Pulso_{i}.png") for i in range(1, 3)

]

frames_onda_cinetica = [

    pygame.transform.scale(frame, (largura_onda, altura_onda)) for frame in frames_onda_cinetica

]



sprite_morto = pygame.image.load("Sprites/morto.png")

sprite_morto = pygame.transform.scale(sprite_morto, (largura_personagem, altura_personagem))



personagem_paths = {

    'up': ["Sprites/Geo1-up.png", "Sprites/Geo2-up.png"],

    'down': ["Sprites/Geo1-Down.png", "Sprites/Geo2-Down.png"],

    'left': ["Sprites/Geo1-Esq.png", "Sprites/Geo2-Esq.png", "Sprites/Geo3-Esq.png", "Sprites/Geo2-Esq.png"],

    'right': ["Sprites/Geo1-Dir.png", "Sprites/Geo2-Dir.png", "Sprites/Geo3-Dir.png", "Sprites/Geo2-Dir.png"],

    'stop': ["Sprites/Geo1.png", "Sprites/Geo2.png"],

    'disp' :["Sprites/Geo_Disp1.png", "Sprites/Geo_Disp2.png", "Sprites/Geo_Disp3.png"]

}



geo_umbra_paths = {

    'stop': ["Sprites/Geo-Umbra-V2-1.png", "Sprites/Geo-Umbra-V2-2.png"],

    'damage': ["Sprites/Geo-Umbra-V2-1-dano.png", "Sprites/Geo-Umbra-V2-2-dano.png"],

    'escudo': ["Sprites/Geo_Umbra_Escudo-1.png", "Sprites/Geo_Umbra_Escudo-2.png"]

}



personagem_paths2 = {

    'up': ["Sprites/Henry_Up0.png", "Sprites/Henry_Up1.png"],

    'down': ["Sprites/Henry_Dir0.png", "Sprites/Henry_Dir1.png"],

    'left': ["Sprites/Henry_Esq0.png", "Sprites/Henry_Esq1.png"],

    'right': ["Sprites/Henry_Dir0.png", "Sprites/Henry_Dir1.png"],

    'stop': ["Sprites/Henry_Stop0.png", "Sprites/Henry_Stop1.png"],

    'disp' :["Sprites/Henry_Stop0.png", "Sprites/Henry_Stop1.png"]

}



trembo_paths = {

    'up': ["Sprites/trembo_costa1.png", "Sprites/trembo_costa1.png"],

    'down': ["Sprites/trembo_frente1.png", "Sprites/trembo_frente2.png"],

    'left': ["Sprites/trembo_esquerda1.png", "Sprites/trembo_esquerda2.png"],

    'right': ["Sprites/trembo_direita1.png", "Sprites/trembo_direita2.png"],

    'stop': ["Sprites/trembo_stop1.png", "Sprites/trembo_stop2.png"],

    'shift':["Sprites/inimig1.png", "Sprites/Geo2.png"],

    'disp':["Sprites/trembo_stop1.png", "Sprites/trembo_stop2.png"]

}



Petro_paths = {

    'up_petro': ["Sprites/Petro_nivel1_up1.png", "Sprites/Petro_nivel1_up2.png"],

    'down_petro': ["Sprites/Petro_nivel1_esq1.png", "Sprites/Petro_nivel1_esq2.png"],

    'left_petro': ["Sprites/Petro_nivel1_esq1.png", "Sprites/Petro_nivel1_esq2.png"],

    'right_petro': ["Sprites/Petro_nivel1_dir1.png", "Sprites/Petro_nivel1_dir2.png"],

    'stop_petro': ["Sprites/Petro_nivel1_stop1.png", "Sprites/Petro_nivel1_stop2.png", "Sprites/Petro_nivel1_stop3.png"],

    

}



Petro_paths2 = {

    'up_petro': ["Sprites/Petro_nivel1_up1.png", "Sprites/Petro_nivel1_up2.png"],

    'down_petro': ["Sprites/Petro_nivel1_esq1.png", "Sprites/Petro_nivel1_esq2.png"],

    'left_petro': ["Sprites/Petro_nivel2_esq1.png", "Sprites/Petro_nivel2_esq2.png"],

    'right_petro': ["Sprites/Petro_nivel2_dir1.png", "Sprites/Petro_nivel2_dir2.png"],

    'stop_petro': ["Sprites/Petro_nivel1_stop1.png", "Sprites/Petro_nivel1_stop2.png", "Sprites/Petro_nivel1_stop3.png"],

    

}



Petro_paths3 = {

    'up_petro': ["Sprites/Petro_nivel1_up1.png", "Sprites/Petro_nivel1_up2.png"],

    'down_petro': ["Sprites/Petro_nivel1_esq1.png", "Sprites/Petro_nivel1_esq2.png"],

    'left_petro': ["Sprites/Petro_nivel3_esq1.png", "Sprites/Petro_nivel3_esq2.png"],

    'right_petro': ["Sprites/Petro_nivel3_dir1.png", "Sprites/Petro_nivel3_dir2.png"],

    'stop_petro': ["Sprites/Petro_nivel1_stop1.png", "Sprites/Petro_nivel1_stop2.png", "Sprites/Petro_nivel1_stop3.png"],

    

}





Petro_active=False



tempo_animacao_stop = 700

tempo_animacao_no_stop = 300   # Tempo em milissegundos entre cada quadro

cooldown_dash = False

tempo_ultimo_dash = 0

tempo_cooldown_dash = 2800  #  segundos de cooldown

distancia_dash = 300





# Animação de teletransporte (plasma procedural)

teleporte_duration = 500  # Duração da animação (em milissegundos)



# Configurações do disparo



largura_disparo, altura_disparo = 40, 40



velocidade_disparo = 10

disparos = []





###Configuração personagens secundarios



largura_trembo,altura_trembo= largura_tela*0.08, altura_tela*0.11





# Carregar as sequências de imagens do personagem



# Carregar as sequências de imagens do personagem

frames_animacao2 = {}

for direcao, paths in personagem_paths2.items():

    frames = []

    w_alvo, h_alvo = dimensoes_direcao_personagem.get(direcao, (largura_personagem, altura_personagem))

    for path in paths:

        img = pygame.image.load(path).convert_alpha()

        img_s = pygame.transform.scale(img, (w_alvo, h_alvo))

        

        # Cria uma superfície do tamanho "padrão" para manter o ancoramento no chão (sem dar pulinhos)

        surf = pygame.Surface((largura_personagem, altura_personagem), pygame.SRCALPHA)

        x_offset = (largura_personagem - w_alvo) // 2

        y_offset = altura_personagem - h_alvo

        surf.blit(img_s, (x_offset, y_offset))

        frames.append(surf.convert_alpha())

    frames_animacao2[direcao] = frames



frames_animacao = {}

for direcao, paths in personagem_paths.items():

    frames = []

    w_alvo, h_alvo = dimensoes_direcao_personagem.get(direcao, (largura_personagem, altura_personagem))

    for path in paths:

        img = pygame.image.load(path).convert_alpha()

        img_s = pygame.transform.scale(img, (w_alvo, h_alvo))

        

        # Cria uma superfície do tamanho "padrão" para manter o ancoramento no chão (sem dar pulinhos)

        surf = pygame.Surface((largura_personagem, altura_personagem), pygame.SRCALPHA)

        x_offset = (largura_personagem - w_alvo) // 2

        y_offset = altura_personagem - h_alvo

        surf.blit(img_s, (x_offset, y_offset))

        frames.append(surf.convert_alpha())

    frames_animacao[direcao] = frames



# Carregar e escalar seguindo o seu padrão

frames_geo_umbra_paths_bruto = {direcao: [pygame.image.load(path).convert_alpha() for path in paths] for direcao, paths in geo_umbra_paths.items()}



frames_geo_umbra_paths = {}

for direcao, frames in frames_geo_umbra_paths_bruto.items():

    novos_frames = []

    w_alvo, h_alvo = dimensoes_direcao_boss.get(direcao, (largura_boss, altura_boss))

    

    for frame in frames:

        # Escala a imagem original para o tamanho alvo definido no dicionário

        img_s = pygame.transform.scale(frame, (w_alvo, h_alvo))

        

        if w_alvo != largura_boss or h_alvo != altura_boss:

            # Direções com tamanho diferente (ex: escudo) usam caixa-container

            # para manter os pés ancorados na mesma posição

            caixa_w = max(largura_boss, w_alvo)

            caixa_h = max(altura_boss, h_alvo)

            surf = pygame.Surface((caixa_w, caixa_h), pygame.SRCALPHA)

            x_offset = (caixa_w - w_alvo) // 2

            y_offset = caixa_h - h_alvo

            surf.blit(img_s, (x_offset, y_offset))

            novos_frames.append(surf)

        else:

            # Tamanho padrão: usa a imagem escalada diretamente

            novos_frames.append(img_s.convert_alpha())

            

    frames_geo_umbra_paths[direcao] = novos_frames



###############################################



# Carregar as sequências de imagens do trembo

frames_animacao_trembo = {direcao: [pygame.image.load(path).convert_alpha() for path in paths] for direcao, paths in trembo_paths.items()}

frames_animacao_trembo = {direcao: [pygame.transform.scale(frame, (largura_trembo, altura_trembo)).convert_alpha() for frame in frames] for direcao, frames in frames_animacao_trembo.items()}



# Adicionar uma entrada para 'stop' no dicionário

frames_animacao_trembo['stop'] = [pygame.image.load(path).convert_alpha() for path in trembo_paths['stop']]

frames_animacao_trembo['stop'] = [pygame.transform.scale(frame, (largura_trembo, altura_trembo)).convert_alpha() for frame in frames_animacao_trembo['stop']]





###############################################



############################################### PETRO

Resistencia_petro=50

petro_evolucao=1

vida_maxima_petro = 620

dano_petro=8

recuperacao_petro=15

pos_x_petro= pos_x_personagem + largura_personagem + 4

pos_y_petro = pos_y_personagem

tempo_anterior_petro = pygame.time.get_ticks()

tempo_ultima_atualizacao_direcao = pygame.time.get_ticks()

intervalo_dano_petro = 1000  # Intervalo de 1 segundo

vida_petro=vida_maxima_petro

largura_Petro,altura_Petro= largura_tela*0.03, altura_tela*0.05



comando_direcao_petro=True





# Carregar as sequências de imagens do Petro

frames_animacao_Petro = {direcao: [pygame.image.load(path).convert_alpha() for path in paths] for direcao, paths in Petro_paths.items()}

frames_animacao_Petro = {direcao: [pygame.transform.scale(frame, (largura_Petro, altura_Petro)).convert_alpha() for frame in frames] for direcao, frames in frames_animacao_Petro.items()}



frames_animacao_Petro2 = {direcao: [pygame.image.load(path).convert_alpha() for path in paths] for direcao, paths in Petro_paths2.items()}

frames_animacao_Petro2 = {direcao: [pygame.transform.scale(frame, (largura_tela*0.06, altura_tela*0.08)).convert_alpha() for frame in frames] for direcao, frames in frames_animacao_Petro2.items()}



frames_animacao_Petro3 = {direcao: [pygame.image.load(path).convert_alpha() for path in paths] for direcao, paths in Petro_paths3.items()}

frames_animacao_Petro3 = {direcao: [pygame.transform.scale(frame, (largura_tela*0.1, altura_tela*0.12)).convert_alpha() for frame in frames] for direcao, frames in frames_animacao_Petro3.items()}



# Adicionar uma entrada para 'stop' no dicionário

frames_animacao_Petro['stop_petro'] = [pygame.image.load(path).convert_alpha() for path in Petro_paths['stop_petro']]

frames_animacao_Petro['stop_petro'] = [pygame.transform.scale(frame, (largura_Petro, altura_Petro)).convert_alpha() for frame in frames_animacao_Petro['stop_petro']]









###############################################







# Carregar as sequências de imagens do disparo





##FASE2

# Carregar a imagem da personagem quando está congelada

imagem_personagem_congelada = pygame.image.load("Sprites/congelada1.png")

imagem_personagem_congelada = pygame.transform.scale(imagem_personagem_congelada, (largura_personagem, altura_personagem))

cor_vida=verde







#######################################################FASE 3





# Carregar a imagem da sprite do disparo do boss

sprite_disparo_boss3 = pygame.image.load('Sprites/disparo_boss3.png').convert_alpha()  # Substitua 'sprite_disparo_boss.png' pelo caminho do seu arquivo de imagem

sprite_disparo_boss3 = pygame.transform.scale(sprite_disparo_boss3, (50, 50))  # Ajuste as dimensões conforme necessário









cegueira_1="Sprites/cego.png"

disparo_paths_inimigo3 = ["Sprites/Disp_inimigo3_1.png", "Sprites/Disp_inimigo3_2.png"]

frames_disparo3 = [pygame.image.load(path).convert_alpha() for path in disparo_paths_inimigo3]

frames_disparo3 = [pygame.transform.scale(frame, (largura_disparo, altura_disparo)) for frame in frames_disparo3]



largura_inimigo3, altura_inimigo3 = largura_tela*0.05, altura_tela*0.08

frames_inimigo_esquerda3 = [pygame.transform.scale(pygame.image.load("Sprites/inimigo_direita3-1.png").convert_alpha(), (largura_inimigo, altura_inimigo)),

                           pygame.transform.scale(pygame.image.load("Sprites/inimigo_direita3-2.png").convert_alpha(), (largura_inimigo, altura_inimigo))]

frames_inimigo_direita3 = [pygame.transform.scale(pygame.image.load("Sprites/inimigo_esquerda3-1.png").convert_alpha(), (largura_inimigo, altura_inimigo)),

                          pygame.transform.scale(pygame.image.load("Sprites/inimigo_esquerda3-2.png").convert_alpha(), (largura_inimigo, altura_inimigo))]

imagem_personagem_doente = pygame.image.load("Sprites/Doente.png").convert_alpha()

imagem_personagem_doente = pygame.transform.scale(imagem_personagem_doente, (largura_personagem, altura_personagem))





#FASE 4

disparo_paths_inimigo4 = ["Sprites/Magia_inimigo1.png", "Sprites/Magia_inimigo2.png"]

frames_disparo4 = [pygame.image.load(path).convert_alpha() for path in disparo_paths_inimigo4]

frames_disparo4 = [pygame.transform.scale(frame, (largura_disparo, altura_disparo)) for frame in frames_disparo4]



#FRAME DO INIMIGO NO GAME 4











frames_inimigo_esquerda4 = [pygame.transform.scale(pygame.image.load("Sprites/inimigo_direita4-1.png").convert_alpha(), (largura_inimigo, altura_inimigo)),

                           pygame.transform.scale(pygame.image.load("Sprites/inimigo_direita4-2.png").convert_alpha(), (largura_inimigo, altura_inimigo))]

frames_inimigo_direita4 = [pygame.transform.scale(pygame.image.load("Sprites/inimigo_esquerda4-1.png").convert_alpha(), (largura_inimigo, altura_inimigo)),

                          pygame.transform.scale(pygame.image.load("Sprites/inimigo_esquerda4-2.png").convert_alpha(), (largura_inimigo, altura_inimigo))]





##############################   SOBRE o DECK 3############################################################



custo_base_carta = 500

custo_por_carta = 150  # Aumenta 150 a cada compra

# Defina as variáveis de posição do quadrado e texto

posicao_info_x = 0  # Deslocamento horizontal

posicao_info_y = -220  # Deslocamento vertical (levanta o quadrado)

icone_w=pygame.transform.scale(pygame.image.load("Sprites/W.png"), (largura_inimigo, altura_inimigo))

icone_x=pygame.transform.scale(pygame.image.load("Sprites/X.png"), (largura_inimigo, altura_inimigo))

trembo=False

mostrar_info = False

# Dicionário para armazenar as cartas compradas e suas quantidades

cartas_compradas = {

    "Speed Boost": 0,

    "Porção": 0,

    "Disparo crescente": 0,

    "Tempestade": 0,

    "Cura": 0,

    "Trembo": 0,

    "Speed Atack": 0,

    "Teleporte": 0,

    "Petro": 0,

    "Defesa": 0,

    "Sorte": 0,

    "Poison":0,

    "Coletora":0,

}

cartas_imagens = {

    "Speed Boost": pygame.image.load('Sprites/Deck/Speed_boost1.png'),

    "Porção": pygame.image.load('Sprites/Deck/carta_por1.png'),

    "Disparo crescente": pygame.image.load('Sprites/Deck/carta_odio1.png'),

    "Tempestade": pygame.image.load('Sprites/Deck/Carta_tempestade_crescente1.png'),

    "Cura": pygame.image.load('Sprites/Deck/Carta_roubo_vida1.png'),

    "Trembo": pygame.image.load('Sprites/Deck/carta_trem1.png'),

    "Speed Atack": pygame.image.load('Sprites/Deck/carta_onda.png'),

    "Teleporte": pygame.image.load('Sprites/Deck/carta_teleporte1.png'),

    "Petro": pygame.image.load('Sprites/Deck/carta_petro1.png'),

    "Defesa": pygame.image.load('Sprites/Deck/carta_defesa1.png'),

    "Sorte": pygame.image.load('Sprites/Deck/carta_sorte1.png'),

    "Poison": pygame.image.load('Sprites/Deck/carta_poison1.png'),

    "Coletora": pygame.image.load('Sprites/Deck/carta_estalo1.png'),

}

cartas_disponiveis_nomes = [

    "Speed Boost", 

    "Porção",

    "Disparo crescente", 

    "Tempestade", 

    "Cura", 

    "Trembo",

    "Speed Atack", 

    "Teleporte", 

    "Petro", 

    "Defesa",

    "Sorte",

    "Poison",

    "Coletora",

]

area_cartas = pygame.Rect(largura_tela // 4 - (len(cartas_compradas) * 100) // 2, altura_tela - 150, len(cartas_compradas) * 100, 100)

cartas_visiveis = True

#########################################################     AUREA       ##################################################################



efeitos_texto = []

eliminacoes_consecutivas_passivo = 0

impulsiva_ativa = False

tempo_inicio_buff_impulsiva = 0

tipo_buff_impulsiva = None

tempo_buff_impulsiva = 5000  # em milissegundos

escudo_devota_ativo = True



intervalo_escudo = 30000  # 30 segundos









#########################################################     Cronometro       ##################################################################

tempo_acumulado = 0      

tempo_inicial = time.time()  

cronometro_pausado = False   



# Função para formatar o tempo

def formatar_tempo(tempo_total):

    horas = int(tempo_total // 3600)

    minutos = int((tempo_total % 3600) // 60)

    segundos = int(tempo_total % 60)

    if horas > 0:

        return f"{horas:02}:{minutos:02}:{segundos:02}"

    else:

        return f"{minutos:02}:{segundos:02}"



# Função para atualizar o cronômetro

def atualizar_cronometro():

    if not cronometro_pausado:

        tempo_decorrido = time.time() - tempo_inicial + tempo_acumulado

        return formatar_tempo(tempo_decorrido)

    else:

        return formatar_tempo(tempo_acumulado)



def obter_tempo_decorrido():

    if not cronometro_pausado:

        return time.time() - tempo_inicial + tempo_acumulado

    return tempo_acumulado



# Função para pausar o cronômetro

def pausar_cronometro():

    global cronometro_pausado, tempo_acumulado

    if not cronometro_pausado:

        cronometro_pausado = True

        tempo_acumulado += time.time() - tempo_inicial



# Função para retomar o cronômetro em um novo script ou fase

def retomar_cronometro():

    global cronometro_pausado, tempo_inicial

    if cronometro_pausado:

        cronometro_pausado = False

        tempo_inicial = time.time()



# Função para exibir o cronômetro na tela

def exibir_cronometro(tela):

    try:

        from ui_helpers import palco_ativo

        if palco_ativo():

            return

    except Exception:

        pass



    tempo_exibido = atualizar_cronometro()

    fonte = pygame.font.Font(None, 36)

    

    # Renderizar o texto do cronômetro com contorno preto para contraste

    texto_contorno = fonte.render(tempo_exibido, True, (0, 0, 0))  

    texto_cronometro = fonte.render(tempo_exibido, True, (255, 255, 255)) 

    

    # Coordenadas do canto superior direito com uma margem de 10 pixels

    pos_x = largura_mapa - 100

    pos_y = 10

    

    # Desenhar o contorno em posições levemente deslocadas ao redor do texto principal

    tela.blit(texto_contorno, (pos_x - 1, pos_y))     # Esquerda

    tela.blit(texto_contorno, (pos_x + 1, pos_y))     # Direita

    tela.blit(texto_contorno, (pos_x, pos_y - 1))     # Cima

    tela.blit(texto_contorno, (pos_x, pos_y + 1))     # Baixo

    

    # Desenhar o texto principal no centro

    tela.blit(texto_cronometro, (pos_x, pos_y))



def criar_onda(posicao,ultima_tecla_movimento):

    return {

        "rect": pygame.Rect(posicao[0], posicao[1], largura_onda, altura_onda),  # Define a hitbox

        "direcao": ultima_tecla_movimento,  # Direção do movimento

        "frame_atual": 0,  # Frame inicial da animação

        "tempo_inicio": pygame.time.get_ticks()  # Para controlar os frames e o tempo de vida

    }

def rotacionar_frames(frames, angulo):

    return [pygame.transform.rotate(frame, angulo) for frame in frames]



estado_mouse_botoes = {}



def atualizar_estado_mouse(evento):

    global estado_mouse_botoes

    if evento.type == pygame.MOUSEBUTTONDOWN:

        estado_mouse_botoes[evento.button] = True

    elif evento.type == pygame.MOUSEBUTTONUP:

        estado_mouse_botoes[evento.button] = False



def verificar_input(acao):

    if acao not in config_teclas:

        return False

    tecla = config_teclas[acao]

    if isinstance(tecla, str) and tecla.startswith("MOUSE_"):

        try:

            btn_idx = int(tecla.split("_")[1])

            if btn_idx in [1, 2, 3]:

                return pygame.mouse.get_pressed()[btn_idx - 1]

            return estado_mouse_botoes.get(btn_idx, False)

        except:

            return False

    else:

        try:

            return pygame.key.get_pressed()[tecla]

        except:

            return False



def verificar_evento_input(evento, acao):

    if acao not in config_teclas:

        return False

    tecla = config_teclas[acao]

    if isinstance(tecla, str) and tecla.startswith("MOUSE_"):

        try:

            btn_idx = int(tecla.split("_")[1])

            return evento.type == pygame.MOUSEBUTTONDOWN and evento.button == btn_idx

        except:

            return False

    else:

        return evento.type == pygame.KEYDOWN and evento.key == tecla



def formatar_nome_tecla(tecla):

    if isinstance(tecla, str) and tecla.startswith("MOUSE_"):

        try:

            btn_idx = int(tecla.split("_")[1])

            nomes_mouse = {

                1: "LMB",

                2: "MMB",

                3: "RMB",

                4: "M4",

                5: "M5"

            }

            return nomes_mouse.get(btn_idx, f"M{btn_idx}")

        except:

            return tecla

    elif isinstance(tecla, int):

        nome = pygame.key.name(tecla)

        traducoes = {

            "left shift": "LSHIFT",

            "right shift": "RSHIFT",

            "left ctrl": "LCTRL",

            "right ctrl": "RCTRL",

            "left alt": "LALT",

            "right alt": "RALT",

            "space": "ESPAÇO",

            "return": "ENTER",

            "escape": "ESC"

        }

        return traducoes.get(nome.lower(), nome.upper())

    return str(tecla)



def recarregar_teclas():

    global config_teclas

    config_teclas = carregar_config_teclas()


def _nivel_detalhes_visuais():
    try:
        with open("saves/config_graficos.json", "r") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    nivel = str(cfg.get("nivel_detalhes", cfg.get("qualidade_grafica", "alta"))).lower()
    if nivel in ("alto", "alta"):
        return "alto"
    if nivel in ("medio", "media", "médio", "média"):
        return "medio"
    return "baixo"


def _desenhar_luz_loja_disponivel(tela, rect):
    nivel = _nivel_detalhes_visuais()
    camadas = {"baixo": 1, "medio": 2, "alto": 4}.get(nivel, 2)
    tempo = pygame.time.get_ticks() * 0.004
    for i in range(camadas):
        margem = 8 + i * 7 + int(math.sin(tempo + i) * 2)
        alpha = max(35, 115 - i * 20)
        glow = pygame.Surface((rect.w + margem * 2, rect.h + margem * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 235, 145, alpha), glow.get_rect())
        tela.blit(glow, (rect.x - margem, rect.y - margem), special_flags=pygame.BLEND_RGBA_ADD)



def desenhar_habilidades(tela, cooldowns, dispositivo_ativo):

    if dispositivo_ativo == "teclado":

        tecla_disparo = "LMB"

        tecla_teleporte = formatar_nome_tecla(config_teclas.get("Teleporte", pygame.K_LSHIFT))

        tecla_onda = formatar_nome_tecla(config_teclas.get("Habilidade Onda", "MOUSE_3"))

        tecla_loja = formatar_nome_tecla(config_teclas.get("Comprar na loja", pygame.K_e))

    else:

        tecla_disparo = "A"

        tecla_teleporte = "X"

        tecla_onda = "B"

        tecla_loja = "Y"



    habilidades = [

        ("disparo", tecla_disparo, icone_disparo_pronto, icone_disparo_recarga, cooldowns.get('disparo', 0.0)),

        ("teleporte", tecla_teleporte, icone_teleporte_pronto, icone_teleporte_recarga, cooldowns.get('teleporte', 0.0)),

        ("onda", tecla_onda, icone_onda_pronto, icone_onda_recarga, cooldowns.get('onda', 0.0)),

        ("loja", tecla_loja, icone_loja, icone_loja_pronto, cooldowns.get('loja', 0.0)),

    ]

    if obter_modo_cartas() == "drops":

        habilidades = [h for h in habilidades if h[0] != "loja"]

    

    num_hab = len(habilidades)

    for i, (nome, tecla, icone_pronto, icone_recarga, cooldown) in enumerate(habilidades):

        x = centro_tela - ((num_hab - 1) / 2.0 - i) * espacamento

        y = altura_base

        

        # Escolher o ícone baseado no cooldown

        if nome == "loja":

            # Para a loja: 1 = pronto (ícone colorido), 0 = indisponível (ícone cinza)

            if cooldown > 0:

                icone = icone_recarga

            else:

                icone = icone_pronto

        else:

            # Para habilidades normais: cooldown > 0 segundos significa em recarga (ícone cinza)

            if cooldown > 0.0:

                icone = icone_recarga

            else:

                icone = icone_pronto

        

        # Desenhar o ícone

        tela.blit(icone, (x, y))

        

        # Desenhar o tempo de cooldown se for relevante (> 0.0s) e não for a loja

        if nome != "loja" and cooldown > 0.0:

            # Desenhar overlay translúcido para indicar recarga

            overlay = pygame.Surface(icone_tamanho, pygame.SRCALPHA)

            pygame.draw.rect(overlay, (0, 0, 0, 160), (0, 0, icone_tamanho[0], icone_tamanho[1]), border_radius=15)

            tela.blit(overlay, (x, y))



            # Desenhar texto com contorno e sombra de forma premium

            fonte_cd = pygame.font.Font("Fonts/Outfit-Bold.ttf" if os.path.exists("Fonts/Outfit-Bold.ttf") else None, 26)

            texto_cd = f"{cooldown:.1f}s"

            

            # Renderizar contorno/sombra primeiro

            texto_sombra = fonte_cd.render(texto_cd, True, (0, 0, 0))

            # Texto principal em ciano neon brilhante

            texto_surf = fonte_cd.render(texto_cd, True, (0, 255, 240))

            

            tx = x + (icone_tamanho[0] - texto_surf.get_width()) // 2

            ty = y + (icone_tamanho[1] - texto_surf.get_height()) // 2

            

            # Blitar sombra deslocada

            tela.blit(texto_sombra, (tx - 1, ty - 1))

            tela.blit(texto_sombra, (tx + 1, ty - 1))

            tela.blit(texto_sombra, (tx - 1, ty + 1))

            tela.blit(texto_sombra, (tx + 1, ty + 1))

            tela.blit(texto_sombra, (tx + 2, ty + 2))

            # Blitar texto principal

            tela.blit(texto_surf, (tx, ty))

        

        cor_texto = (255, 255, 255)  # Branco para o texto principal

        cor_contorno = (0, 0, 0)    # Preto para o contorno

        

        # Desenhar a tecla acima do ícone com contorno

        fonte = pygame.font.Font(None, 20)

        render_texto_com_contorno(fonte, tecla.upper(), cor_texto, cor_contorno, x + icone_tamanho[0] // 10, y - 10, tela)



def render_texto_com_contorno(fonte, texto, cor_texto, cor_contorno, x, y, tela, deslocamento=2): #texto da interface

    """Renderiza texto com contorno."""

    texto_render = fonte.render(texto, True, cor_contorno)

    

    # Desenhar o contorno ao redor

    for dx, dy in [(-deslocamento, 0), (deslocamento, 0), (0, -deslocamento), (0, deslocamento),

                   (-deslocamento, -deslocamento), (-deslocamento, deslocamento),

                   (deslocamento, -deslocamento), (deslocamento, deslocamento)]:

        tela.blit(texto_render, (x + dx, y + dy))

    

    # Desenhar o texto principal

    texto_principal = fonte.render(texto, True, cor_texto)

    tela.blit(texto_principal, (x, y))



def desenhar_texto_com_contorno(surface, texto, fonte, cor_texto, cor_contorno, posicao): #TEXTO DE PONTOAÇÂO

    # Renderizar o texto duas vezes, uma para o contorno e outra para o texto em si

    texto_surface = fonte.render(texto, True, (255,0,0))

    texto_contorno = fonte.render(texto, True, cor_contorno)

    

    # Desenhar o contorno

    x, y = posicao

    surface.blit(texto_contorno, (x - 1, y))  # Esquerda

    surface.blit(texto_contorno, (x + 1, y))  # Direita

    surface.blit(texto_contorno, (x, y - 1))  # Acima

    surface.blit(texto_contorno, (x, y + 1))  # Abaixo



    # Desenhar o texto

    surface.blit(texto_surface, posicao)



def calcular_posicao_prevista(pos_x, pos_y, direcao, velocidade, tempo_previsao):

    if direcao == 'up':

        pos_y -= velocidade * tempo_previsao * dt

    elif direcao == 'down':

        pos_y += velocidade * tempo_previsao * dt

    elif direcao == 'left':

        pos_x -= velocidade * tempo_previsao * dt

    elif direcao == 'right':

        pos_x += velocidade * tempo_previsao * dt

    return pos_x, pos_y



# ============ SISTEMA DE PARTÍCULAS DE VENENO PINGANDO ============

particulas_veneno = []



def atualizar_e_desenhar_particulas_veneno(tela, inimigos_comum, config_graficos=None):

    """

    Gera e renderiza partículas de veneno pingando dos inimigos envenenados.

    Gotículas verdes caem com gravidade, simulando veneno escorrendo.

    """

    global particulas_veneno



    if config_graficos is not None:

        if not (config_graficos.get("particulas_ativas", True) and config_graficos.get("efeitos_visuais", True)):

            particulas_veneno.clear()

            return



    qualidade = "alta"

    if config_graficos is not None:

        qualidade = config_graficos.get("qualidade_grafica", "alta")



    tempo_agora = pygame.time.get_ticks()



    # Spawnar novas partículas a partir de inimigos envenenados

    max_particulas = 120 if qualidade == "alta" else (60 if qualidade == "media" else 30)

    for inimigo in inimigos_comum:

        if "veneno" not in inimigo:

            continue

        # Verificar se o veneno ainda está ativo

        if tempo_agora - inimigo["veneno"]["tempo_inicio"] >= inimigo["veneno"]["duracao"]:

            continue



        # Limita a taxa de spawn por inimigo

        spawn_chance = 0.35 if qualidade == "alta" else (0.2 if qualidade == "media" else 0.1)

        if random.random() < spawn_chance and len(particulas_veneno) < max_particulas:

            rect = inimigo["rect"]

            # Gerar gota na parte inferior/lateral do inimigo

            px = random.uniform(rect.left + 2, rect.right - 2)

            py = random.uniform(rect.centery, rect.bottom)

            vx = random.uniform(-0.5, 0.5)

            vy = random.uniform(0.3, 1.5)  # Cai para baixo (gravidade)

            tamanho = random.uniform(1.5, 3.5)



            # Tons de verde tóxico variados

            cor = random.choice([

                (0, 200, 0),      # Verde escuro

                (50, 255, 50),    # Verde brilhante

                (80, 220, 30),    # Verde lima

                (30, 180, 60),    # Verde profundo

                (100, 255, 80),   # Verde claro

            ])



            particulas_veneno.append({

                "x": px,

                "y": py,

                "vx": vx,

                "vy": vy,

                "tamanho": tamanho,

                "cor": cor,

                "vida": random.randint(20, 40),

                "alpha": 255,

            })



    # Atualizar e desenhar

    novas = []

    for p in particulas_veneno:

        p["x"] += p["vx"]

        p["y"] += p["vy"]

        p["vy"] += 0.12  # Gravidade (pingando)

        p["vx"] *= 0.96  # Atrito horizontal

        p["vida"] -= 1

        p["alpha"] = max(0, int(255 * (p["vida"] / 40.0)))

        p["tamanho"] = max(0.5, p["tamanho"] - 0.03)



        if p["vida"] <= 0:

            continue



        novas.append(p)



        # Desenhar a gotícula

        ix = int(p["x"])

        iy = int(p["y"])

        sz = max(1, int(p["tamanho"]))



        # Gota principal

        cor_alpha = (*p["cor"], min(255, p["alpha"]))

        if qualidade == "alta":

            # Glow sutil

            glow_surf = pygame.Surface((sz * 4, sz * 4), pygame.SRCALPHA)

            pygame.draw.circle(glow_surf, (*p["cor"][:3], min(60, p["alpha"] // 3)), (sz * 2, sz * 2), sz * 2)

            tela.blit(glow_surf, (ix - sz * 2, iy - sz * 2))



        # Gota sólida (forma de lágrima simplificada)

        pygame.draw.circle(tela, p["cor"], (ix, iy), sz)

        if sz >= 2 and qualidade != "baixa":

            # Ponto de brilho

            pygame.draw.circle(tela, (200, 255, 200), (ix - 1, iy - 1), max(1, sz // 2))



    particulas_veneno[:] = novas



def atualizar_movimento_inimigos(inimigos, pos_x_p, pos_y_p, direcao_j, vel_p, tempo_p, movendo_agora, larg_p=60, alt_p=90, fator_tempo=1.0):

    for inimigo in inimigos:

        # Se o inimigo estiver stunado pela onda cinética, nao se move

        if pygame.time.get_ticks() < inimigo.get("stun_fim", 0):

            continue

        # Se o inimigo estiver parado (ex: Projetador atacando), nao se move

        if inimigo.get("parado", False):

            continue

            

        # Inicializa pos_x e pos_y se nao existirem (para sub-pixel precision)

        if "pos_x" not in inimigo:

            inimigo["pos_x"] = float(inimigo["rect"].x)

        if "pos_y" not in inimigo:

            inimigo["pos_y"] = float(inimigo["rect"].y)

        

        # Calculo da posicao prevista (Alvo)

        if movendo_agora:

            alvo_x, alvo_y = calcular_posicao_prevista(pos_x_p, pos_y_p, direcao_j, vel_p, tempo_p)

        else:

            alvo_x, alvo_y = pos_x_p, pos_y_p

        

        # Calculo vetorial usando a MEMORIA DECIMAL (pos_x/pos_y)

        dx = alvo_x - inimigo["pos_x"]

        dy = alvo_y - inimigo["pos_y"]

        distancia = math.sqrt(dx**2 + dy**2)


        if distancia > 0:

            # 1. Movimentacao suave com sub-pixel precision

            vel_atual = inimigo.get("velocidade", Velocidade_Inimigos_1)

            inimigo["pos_x"] += (dx / distancia) * vel_atual * dt * fator_tempo

            inimigo["pos_y"] += (dy / distancia) * vel_atual * dt * fator_tempo

            

            # 2. Sincronizacao obrigatoria com o RECT (Inteiro) para renderizacao

            inimigo["rect"].x = int(inimigo["pos_x"])

            inimigo["rect"].y = int(inimigo["pos_y"])


    # Resolve colisão do jogador com inimigos (jogador é empurrado de volta)

    pos_x_p, pos_y_p = resolver_colisao_player_com_inimigos(pos_x_p, pos_y_p, larg_p, alt_p, inimigos)

    # Resolve colisões e separação entre inimigos e jogador (inimigos são empurrados de volta)

    resolver_colisoes_e_separacao(inimigos, pos_x_p, pos_y_p, larg_p, alt_p)

    return pos_x_p, pos_y_p



def resolver_colisao_player_com_inimigos(pos_x_p, pos_y_p, larg_p, alt_p, inimigos):

    """

    Resolve a colisao do player com todos os inimigos, tratando os inimigos como estaticos.

    Retorna a nova posicao (pos_x_p, pos_y_p) do player.

    """

    if not inimigos:

        return pos_x_p, pos_y_p


    raio_p = ((larg_p + alt_p) / 4.0) * 0.85

    centro_p = [pos_x_p + larg_p / 2.0, pos_y_p + alt_p / 2.0]


    # 2 iteracoes para maior estabilidade contra multiplos inimigos

    for _ in range(2):

        for inimigo in inimigos:

            if inimigo.get("invisivel", False):

                continue

            pos_xi = inimigo.get("pos_x", float(inimigo["rect"].x))

            pos_yi = inimigo.get("pos_y", float(inimigo["rect"].y))

            wi = inimigo["rect"].width

            hi = inimigo["rect"].height

            raio_i = ((wi + hi) / 4.0) * 0.90

            centro_i = (pos_xi + wi / 2.0, pos_yi + hi / 2.0)


            dx = centro_p[0] - centro_i[0]

            dy = centro_p[1] - centro_i[1]

            dist = math.sqrt(dx**2 + dy**2)

            dist_minima = raio_p + raio_i


            if dist < dist_minima:

                if dist > 0:

                    overlap = dist_minima - dist

                    centro_p[0] += (dx / dist) * overlap

                    centro_p[1] += (dy / dist) * overlap

                else:

                    centro_p[1] -= dist_minima


    pos_x_p = centro_p[0] - larg_p / 2.0

    pos_y_p = centro_p[1] - alt_p / 2.0

    return pos_x_p, pos_y_p



def resolver_colisoes_e_separacao(inimigos, pos_x_p, pos_y_p, larg_p, alt_p):

    """

    Resolve a sobreposicao entre inimigos e empurra os inimigos para fora do player.

    O player age como um corpo imovel neste passo.

    """

    if not inimigos:

        return


    # Separacao/colisao entre inimigos (relaxamento de restricoes em 2 iteracoes)

    for _ in range(2):

        for i in range(len(inimigos)):

            inimigo_a = inimigos[i]

            if inimigo_a.get("invisivel", False):

                continue

                

            pos_xa = inimigo_a.get("pos_x", float(inimigo_a["rect"].x))

            pos_ya = inimigo_a.get("pos_y", float(inimigo_a["rect"].y))

            wa = inimigo_a["rect"].width

            ha = inimigo_a["rect"].height

            raio_a = ((wa + ha) / 4.0) * 0.90

            centro_a = (pos_xa + wa / 2.0, pos_ya + ha / 2.0)

            

            for j in range(i + 1, len(inimigos)):

                inimigo_b = inimigos[j]

                if inimigo_b.get("invisivel", False):

                    continue

                    

                pos_xb = inimigo_b.get("pos_x", float(inimigo_b["rect"].x))

                pos_yb = inimigo_b.get("pos_y", float(inimigo_b["rect"].y))

                wb = inimigo_b["rect"].width

                hb = inimigo_b["rect"].height

                raio_b = ((wb + hb) / 4.0) * 0.90

                centro_b = (pos_xb + wb / 2.0, pos_yb + hb / 2.0)

                

                dx = centro_a[0] - centro_b[0]

                dy = centro_a[1] - centro_b[1]

                dist = math.sqrt(dx**2 + dy**2)

                dist_minima = raio_a + raio_b

                

                if dist < dist_minima:

                    if dist > 0:

                        overlap = dist_minima - dist

                        push_x = (dx / dist) * overlap * 0.5

                        push_y = (dy / dist) * overlap * 0.5

                    else:

                        push_x = dist_minima * 0.5

                        push_y = 0.0

                        

                    pos_xa += push_x

                    pos_ya += push_y

                    pos_xb -= push_x

                    pos_yb -= push_y

                    

                    inimigo_a["pos_x"] = pos_xa

                    inimigo_a["pos_y"] = pos_ya

                    inimigo_a["rect"].x = int(pos_xa)

                    inimigo_a["rect"].y = int(pos_ya)

                    

                    inimigo_b["pos_x"] = pos_xb

                    inimigo_b["pos_y"] = pos_yb

                    inimigo_b["rect"].x = int(pos_xb)

                    inimigo_b["rect"].y = int(pos_yb)


        # Separacao entre inimigo e player (jogador e imovel/infinito massa)

        raio_p = ((larg_p + alt_p) / 4.0) * 0.85

        centro_p = (pos_x_p + larg_p / 2.0, pos_y_p + alt_p / 2.0)

        for inimigo in inimigos:

            if inimigo.get("invisivel", False):

                continue

            pos_xi = inimigo.get("pos_x", float(inimigo["rect"].x))

            pos_yi = inimigo.get("pos_y", float(inimigo["rect"].y))

            wi = inimigo["rect"].width

            hi = inimigo["rect"].height

            raio_i = ((wi + hi) / 4.0) * 0.90

            centro_i = (pos_xi + wi / 2.0, pos_yi + hi / 2.0)


            dx = centro_i[0] - centro_p[0]

            dy = centro_i[1] - centro_p[1]

            dist = math.sqrt(dx**2 + dy**2)

            dist_minima = raio_p + raio_i


            if dist < dist_minima:

                if dist > 0:

                    overlap = dist_minima - dist

                    pos_xi += (dx / dist) * overlap

                    pos_yi += (dy / dist) * overlap

                else:

                    pos_yi += dist_minima

                inimigo["pos_x"] = pos_xi

                inimigo["pos_y"] = pos_yi

                inimigo["rect"].x = int(pos_xi)

                inimigo["rect"].y = int(pos_yi)



def calcular_angulo_disparo(posicao_jogador, posicao_mouse):

    dx = posicao_mouse[0] - posicao_jogador[0]

    dy = posicao_mouse[1] - posicao_jogador[1]

    angulo = math.atan2(dy, dx)

    return angulo



def verificar_colisao_disparo_inimigo(disparo, pos_inimigo, largura_disparo, altura_disparo, largura_inimigo, altura_inimigo, inimigos_eliminados):

    rect_disparo = disparo["rect"]  # Use o rect do disparo diretamente

    rect_inimigo = pygame.Rect(pos_inimigo[0], pos_inimigo[1], largura_inimigo, altura_inimigo)

    return rect_disparo.colliderect(rect_inimigo)



# Função para ataque especial do Boss

def ataque_especial_boss(jogador_posicoes, imagens_ataque, tempo_inicial, intervalo_troca, tela):

    tempo_atual = pygame.time.get_ticks()

    indice_imagem = (tempo_atual - tempo_inicial) // intervalo_troca



    if indice_imagem < len(imagens_ataque):

        imagem_atual = imagens_ataque[indice_imagem]

        posicao_atual = jogador_posicoes[min(indice_imagem, len(jogador_posicoes) - 1)]

        tela.blit(imagem_atual, posicao_atual)

        return False  # O ataque ainda está em andamento

    return True  # O ataque terminou



#Função que escolhe as cores da barra de vida do personagem 

def calcular_cor_barra_de_vida(porcentagem_vida):

    if porcentagem_vida > 80:

        return (0, 255, 0)  # Verde

    elif porcentagem_vida > 55:

        return (173, 255, 47)  # Verde amarelado

    elif porcentagem_vida > 40:

        return (255, 165, 0)  # Laranja

    elif porcentagem_vida > 30:

        return (255, 69, 0)  # Laranja avermelhado

    else:

        return (255, 0, 0)  # Vermelho



def desenhar_barra_de_vida(surface, x, y, largura_total, altura, vida_atual, vida_maxima, eletrocutado=False, limiar_execucao=None):

    if vida_maxima <= 0:

        return

    if eletrocutado:

        x += random.randint(-2, 2)

        y += random.randint(-2, 2)

        altura = max(8, altura + 3)



    vida_atual = max(0, min(vida_atual, vida_maxima))

    porcentagem_vida = (vida_atual / vida_maxima) * 100

    cor_barra = calcular_cor_barra_de_vida(porcentagem_vida)

    largura_vida = int(largura_total * (vida_atual / vida_maxima))



    if eletrocutado:

        # Generate horizontal lightning bolt points

        p1 = (x, y)

        p2 = (x + largura_total * 0.4, y)

        p3 = (x + largura_total * 0.35, y + altura * 0.4)

        p4 = (x + largura_total * 0.75, y + altura * 0.2)

        p5 = (x + largura_total * 0.7, y + altura * 0.6)

        p6 = (x + largura_total, y + altura * 0.5)

        

        p7 = (x + largura_total * 0.65, y + altura)

        p8 = (x + largura_total * 0.7, y + altura * 0.7)

        p9 = (x + largura_total * 0.3, y + altura)

        p10 = (x + largura_total * 0.35, y + altura * 0.5)

        p11 = (x, y + altura)

        

        pts_bg = [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11]

        

        # Draw background

        pygame.draw.polygon(surface, (30, 30, 40), pts_bg)

        

        # Clip surface to health width to draw filled potion

        clip_rect = surface.get_clip()

        surface.set_clip(pygame.Rect(x - 2, y - 2, largura_vida + 4, altura + 4))

        pygame.draw.polygon(surface, cor_barra, pts_bg)

        surface.set_clip(clip_rect)

        

        # Electric border color alternating

        border_color = (0, 255, 255) if pygame.time.get_ticks() % 200 < 100 else (138, 43, 226)

        pygame.draw.polygon(surface, border_color, pts_bg, 1)

    else:

        borda = pygame.Rect(x, y, largura_total, altura)

        barra = pygame.Rect(x, y, largura_vida, altura)

        pygame.draw.rect(surface, (0, 0, 0), borda, 2)  # Borda preta

        pygame.draw.rect(surface, cor_barra, barra)  # Cor variável



#Função que desenha a barra de vida do Petro

    if limiar_execucao is not None:

        try:

            limiar = max(0.0, min(1.0, float(limiar_execucao)))

            x_limiar = int(x + largura_total * limiar)

            cor_limiar = (255, 235, 80) if pygame.time.get_ticks() % 300 < 150 else (255, 120, 40)

            pygame.draw.line(surface, cor_limiar, (x_limiar, y - 2), (x_limiar, y + altura + 2), 2)

        except (TypeError, ValueError):

            pass



def desenhar_barra_de_vida_petro(surface, vida_petro, pos_x, pos_y,vida_maxima_petro):

    # Calculando a largura da barra de vida

    largura_barra_petro = 30 

    altura_barra_petro = 10     

    

    # Calculando a porcentagem de vida restante

    porcentagem_vida_petro = vida_petro / vida_maxima_petro

    

    

    # Desenhando a parte preenchida da barra de vida (marrom)

    barra_preenchida = pygame.Rect(pos_x, pos_y, largura_barra_petro * porcentagem_vida_petro, altura_barra_petro)

    pygame.draw.rect(surface, (139, 69, 19), barra_preenchida)

    

    # Desenhando a borda da barra de vida (preta)

    pygame.draw.rect(surface, (0, 0, 0), (pos_x, pos_y, largura_barra_petro, altura_barra_petro), 2)    



def resource_path(relative_path):

    try:

        base_path = sys._MEIPASS

    except Exception:

        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)



###################################################  SONS UNIVERSAIS ################################################



####################################################  CONFIG     ######################################################

cor_contorno = (0, 0, 0)  # Preto para o contorno

config_teclas = carregar_config_teclas()

####################################################  Habilidades     ######################################################

icone_disparo_pronto = pygame.transform.scale(pygame.image.load("Sprites/icon_disp2.png"), (80, 80))

icone_teleporte_pronto = pygame.transform.scale( pygame.image.load("Sprites/icon_teleport2.png"), (80, 80))

icone_onda_pronto =  pygame.transform.scale(pygame.image.load("Sprites/icon_onda2.png"), (80, 80))

icone_loja =  pygame.transform.scale(pygame.image.load("Sprites/icon_loja.png"), (80, 80))

icone_abobora_pronto =  pygame.transform.scale(pygame.image.load("Sprites/icon_teste.png"), (80, 80))



# Ícones indisponíveis

icone_disparo_recarga = pygame.transform.scale(pygame.image.load("Sprites/icon_disp.png"), (80, 80))

icone_teleporte_recarga = pygame.transform.scale( pygame.image.load("Sprites/icon_teleport.png"), (80, 80))

icone_onda_recarga = pygame.transform.scale(pygame.image.load("Sprites/icon_onda.png"), (80, 80))

icone_loja_pronto = pygame.transform.scale(pygame.image.load("Sprites/icon_loja2.png"), (80, 80))

icone_abobora_recarga =  pygame.transform.scale(pygame.image.load("Sprites/icon_teste.png"), (80, 80))



# Redimensionar ícones (opcional)

icone_tamanho = (80, 80)

todos_icones = [

    icone_disparo_pronto, icone_teleporte_pronto, icone_onda_pronto, icone_loja, icone_abobora_pronto,

    icone_disparo_recarga, icone_teleporte_recarga, icone_onda_recarga, icone_abobora_recarga,

]

# Coordenadas dos ícones na parte inferior central

centro_tela = largura_mapa // 2.15

espacamento = 100  # Espaço entre os ícones

altura_base = altura_mapa - 100  # Margem inferior



posicoes_icones = [

    (centro_tela - 2 * espacamento, altura_base),

    (centro_tela - espacamento, altura_base),

    (centro_tela, altura_base),

    (centro_tela + espacamento, altura_base),

    (centro_tela + 2 * espacamento, altura_base),

]

area_icones = pygame.Rect(0, altura_tela - 100, largura_tela, 100)  # Exemplo: região inferior de 100px



# Delta time global factor (normalized to 60 FPS)

dt = 1.0



######################################### VARIÁVEIS COMPARTILHADAS ENTRE FASES

running = True

movimento_pressionado = False

tempo_atual = 0

teleportado = False

tempo_texto_dano = 0

fonte = None

Musica_tema_fases = None

imune_tempo_restante = 0

toque = 0

dano = 0

x = 0

y = 0

texto_dano = None

Som_tema_fases = None

vida_inimigo_maxima = 30

vida_inimigo = vida_inimigo_maxima

tempo_passado = 0

tempo_ultimo_hit_inimigo = 0

tempo_ultimo_inimigo = 0

tempo_ultimo_inimigo_apos_morte = 0

tempo_ultimo_atingido = 0

piscando_vida = False

frame_atual = 0

carregar_atributos_na_fase = True

upgrades = {}

disparos_inimigos = []

tempo_ultimo_disparo_inimigo = 0

spawn_inimigo = True

intervalo_disparo_inimigo = 1500

velocidade_disparo_inimigo = 3

velocidade_inimigo2 = 1.70

tempo_imobilizacao = 1000

personagem_imovel = False

tempo_parado_person = 0

tempo_ultimo_disparo = 0

tempo_ultimo_escudo = 0

sprite_moeda = None

ondas_choque = []



# Variables for Mouse Teleport Mode

teleport_pressionado = False

tempo_teleport_press = 0

mostrar_zona_teleporte = False

executar_teleporte_pendente = False



_cached_modo_teleporte = None



def obter_modo_teleporte(forcar_recarregar=False):

    global _cached_modo_teleporte

    if _cached_modo_teleporte is None or forcar_recarregar:

        try:

            import os

            import json

            if os.path.exists("saves/config_teleporte.json"):

                with open("saves/config_teleporte.json", "r") as f:

                    _cached_modo_teleporte = json.load(f).get("modo", "fixo")

            else:

                _cached_modo_teleporte = "fixo"

        except:

            _cached_modo_teleporte = "fixo"

    return _cached_modo_teleporte



def verificar_evento_release(evento, acao):

    if acao not in config_teclas:

        return False

    tecla = config_teclas[acao]

    if isinstance(tecla, str) and tecla.startswith("MOUSE_"):

        try:

            btn_idx = int(tecla.split("_")[1])

            return evento.type == pygame.MOUSEBUTTONUP and evento.button == btn_idx

        except:

            return False

    else:

        return evento.type == pygame.KEYUP and evento.key == tecla



def processar_eventos_teleporte(evento, cooldown_dash):

    global teleport_pressionado, tempo_teleport_press, mostrar_zona_teleporte, executar_teleporte_pendente

    

    if obter_modo_teleporte() != "mouse":

        return None

        

    if verificar_evento_input(evento, "Teleporte"):

        if not cooldown_dash:

            teleport_pressionado = True

            tempo_teleport_press = pygame.time.get_ticks()

            mostrar_zona_teleporte = False

            executar_teleporte_pendente = False

            

    elif verificar_evento_release(evento, "Teleporte"):

        if teleport_pressionado:

            teleport_pressionado = False

            mostrar_zona_teleporte = False

            executar_teleporte_pendente = True

            return "executar"

            

    return None



def atualizar_estado_teleporte():

    global teleport_pressionado, tempo_teleport_press, mostrar_zona_teleporte, executar_teleporte_pendente

    if obter_modo_teleporte() == "mouse" and teleport_pressionado:

        # Safety net: check if the key is still physically pressed

        if not verificar_input("Teleporte"):

            teleport_pressionado = False

            mostrar_zona_teleporte = False

            executar_teleporte_pendente = True

            return "executar"

        

        if pygame.time.get_ticks() - tempo_teleport_press > 150:

            mostrar_zona_teleporte = True

    return None



def calcular_destino_teleporte(px_centro, py_centro, max_dist):

    try:

        from ui_helpers import obter_pos_mouse_jogo

        mx, my = obter_pos_mouse_jogo()

    except Exception:

        mx, my = pygame.mouse.get_pos()

    dx = mx - px_centro

    dy = my - py_centro

    dist = math.sqrt(dx**2 + dy**2)

    

    if dist <= max_dist:

        return mx, my

    else:

        if dist == 0:

            return px_centro, py_centro

        ux = dx / dist

        uy = dy / dist

        return px_centro + ux * max_dist, py_centro + uy * max_dist



def desenhar_zona_teleporte(tela, player_x, player_y, player_w, player_h, max_dist):

    if not (obter_modo_teleporte() == "mouse" and mostrar_zona_teleporte):

        return

        

    px = player_x + player_w // 2

    py = player_y + player_h // 2

    

    dest_x, dest_y = calcular_destino_teleporte(px, py, max_dist)

    

    # Draw soft translucent circle with radius max_dist

    surface_circulo = pygame.Surface((max_dist * 2, max_dist * 2), pygame.SRCALPHA)

    pygame.draw.circle(surface_circulo, (0, 255, 230, 25), (max_dist, max_dist), max_dist)

    pygame.draw.circle(surface_circulo, (0, 255, 230, 120), (max_dist, max_dist), max_dist, 2)

    tela.blit(surface_circulo, (px - max_dist, py - max_dist))

    

    # Draw line from player center to destination

    pygame.draw.line(tela, (0, 255, 230, 180), (px, py), (dest_x, dest_y), 3)

    

    # Draw target crosshair at destination

    pygame.draw.circle(tela, (255, 255, 255, 220), (int(dest_x), int(dest_y)), 10, 2)

    pygame.draw.circle(tela, (0, 255, 230, 220), (int(dest_x), int(dest_y)), 4)





# Variables and functions for Random Card Drops Mode

cartas_no_chao = []



def obter_modo_cartas():

    try:

        import os

        import json

        if os.path.exists("saves/config_cartas.json"):

            with open("saves/config_cartas.json", "r") as f:

                return json.load(f).get("modo_cartas", "loja")

    except:

        pass

    return "loja"



def limpar_cartas_no_chao():

    global cartas_no_chao

    cartas_no_chao = []



def tentar_soltar_carta(posicao, tempo_atual, chance_sorte_jogador, inimigos_eliminados):

    if obter_modo_cartas() != "drops":

        return

        

    # Base chance starts at 0.5% (0.005) and scales slowly over time (10 min -> 5.0% base)

    chance_base = 0.005 + min(0.045, (tempo_atual / 600000.0) * 0.045)

    

    # First roll: base chance

    if random.random() < chance_base:

        # Second roll: "chance on top of another chance"

        # Scales with player luck (Chance_Sorte)

        chance_sorte_efetiva = 0.30 + chance_sorte_jogador

        if random.random() < chance_sorte_efetiva:

            rare_names = {"Trembo", "Petro", "Poison", "Coletora"}

            all_cards = list(cartas_imagens.keys())

            rares = [c for c in all_cards if c in rare_names]

            commons = [c for c in all_cards if c not in rare_names]

            

            # Roll for rarity (same chance calculation as shop)

            # If player has 15+ Sorte cards, min rare chance is 10%

            sorte_count = cartas_compradas.get("Sorte", 0)

            chance_raridade = max(chance_sorte_jogador, 0.10) if sorte_count >= 15 else chance_sorte_jogador

            

            if random.random() < chance_raridade and rares:

                nome_carta = random.choice(rares)

            else:

                nome_carta = random.choice(commons) if commons else random.choice(all_cards)

                

            img_original = cartas_imagens[nome_carta]

            img_pequena = pygame.transform.scale(img_original, (40, 60))

            rect = img_pequena.get_rect(center=posicao)

            

            cartas_no_chao.append({

                "nome": nome_carta,

                "rect": rect,

                "image": img_pequena,

                "tempo_desaparecer": tempo_atual + 4000  # disappears after 4 seconds

            })



def atualizar_e_desenhar_cartas_no_chao(tela, tempo_atual):

    global cartas_no_chao

    # Remove expired cards

    cartas_no_chao = [c for c in cartas_no_chao if tempo_atual < c["tempo_desaparecer"]]

    

    # Draw active cards

    for c in cartas_no_chao:

        progresso_tempo = (c["tempo_desaparecer"] - tempo_atual) / 4000.0

        pulso = int(math.sin(tempo_atual * 0.01) * 3 + 5)

        rect_glow = c["rect"].inflate(pulso, pulso)

        

        rare_names = {"Trembo", "Petro", "Poison", "Coletora"}

        cor_glow = (255, 215, 0) if c["nome"] in rare_names else (0, 255, 230)

        

        alpha = max(0, min(255, int(progresso_tempo * 255)))

        surf_glow = pygame.Surface((rect_glow.width, rect_glow.height), pygame.SRCALPHA)

        pygame.draw.rect(surf_glow, cor_glow + (int(alpha * 0.3),), (0, 0, rect_glow.width, rect_glow.height), border_radius=4)

        pygame.draw.rect(surf_glow, cor_glow + (alpha,), (0, 0, rect_glow.width, rect_glow.height), width=2, border_radius=4)

        

        tela.blit(surf_glow, rect_glow.topleft)

        tela.blit(c["image"], c["rect"].topleft)



def aplicar_carta_drop(nome, stats):

    """Aplica o efeito de uma carta dropada ao dict de stats do jogador.

    Recebe e retorna um dicionário com os mesmos campos usados em Tela_Cartas.aplicar_carta().

    """

    ie = stats.get("inimigos_eliminados", 0)

    

    if nome == "Speed Boost":

        stats["velocidade_personagem"] += 0.035 + (ie // 50) * 0.005

        stats["cartas_compradas"]["Speed Boost"] += 1

    elif nome == "Porção":

        stats["vida"] += int(stats["vida_maxima"] * 0.45 + (ie // 30) * 0.05)

        if stats["vida"] > stats["vida_maxima"]:

            stats["vida_maxima"] = stats["vida"]

        stats["vida_petro"] += int(stats["vida_maxima_petro"] * 0.30 + (ie // 40) * 0.03)

        if stats["vida_petro"] > stats["vida_maxima_petro"]:

            stats["vida_maxima_petro"] = stats["vida_petro"]

        stats["cartas_compradas"]["Porção"] += 1

    elif nome == "Disparo crescente":

        stats["dano_person_hit"] += 27 + (ie // 50) * 10

        stats["cartas_compradas"]["Disparo crescente"] += 1

    elif nome == "Trembo":

        stats["trembo"] = True

        stats["cartas_compradas"]["Trembo"] += 1

        if stats["cartas_compradas"]["Trembo"] >= 2:

            stats["Tempo_cura"] = max(500, int(stats["Tempo_cura"] * 0.75))

            stats["porcentagem_cura"] += 0.005 + (ie // 100) * 0.001

        else:

            stats["Tempo_cura"] -= stats["Tempo_cura"] * 0.05

            stats["porcentagem_cura"] += 0.001 + (ie // 100) * 0.0005

    elif nome == "Tempestade":

        stats["dano_person_hit"] += 10 + (ie // 50) * 4

        stats["chance_critico"] += 0.02 + (ie // 100) * 0.005

        stats["cartas_compradas"]["Tempestade"] += 1

    elif nome == "Cura":

        stats["roubo_de_vida"] = 1.0

        stats["quantidade_roubo_vida"] += 0.001 + (ie // 80) * 0.0003

        stats["cartas_compradas"]["Cura"] += 1

    elif nome == "Speed Atack":

        stats["intervalo_disparo"] -= 20 + (ie // 100) * 5

        if stats["intervalo_disparo"] < 50:

            stats["intervalo_disparo"] = 50

        stats["cartas_compradas"]["Speed Atack"] += 1

    elif nome == "Teleporte":

        stats["tempo_cooldown_dash"] -= stats["tempo_cooldown_dash"] * 0.003 + (ie // 50) * 0.0005

        if stats["tempo_cooldown_dash"] < 0.5:

            stats["tempo_cooldown_dash"] = 0.5

        stats["cartas_compradas"]["Teleporte"] += 1

    elif nome == "Petro":

        stats["Petro_active"] = True

        stats["dano_petro"] += 2 + (ie // 30) * 1

        pe = stats["petro_evolucao"]

        if 0 < pe <= 8:

            stats["xp_petro"] = "nivel_1"

            stats["petro_evolucao"] += 4

        elif 8 < pe <= 16:

            stats["xp_petro"] = "nivel_2"

            stats["vida_maxima_petro"] += 1000

            stats["petro_evolucao"] += 4

        elif pe > 16:

            stats["xp_petro"] = "nivel_3"

            stats["vida_maxima_petro"] += 2000

            stats["Resistencia_petro"] += 18

            stats["dano_petro"] += 250

        if stats["vida_petro"] < stats["vida_maxima_petro"]:

            stats["vida_petro"] += int(stats["vida_maxima_petro"] * 0.45)

        if stats["vida_petro"] > stats["vida_maxima_petro"]:

            stats["vida_maxima_petro"] = stats["vida_petro"]

        stats["cartas_compradas"]["Petro"] += 1

    elif nome == "Defesa":

        stats["Resistencia"] += 3.5 + (ie // 50) * 0.5

        if stats["Resistencia"] > 50:

            stats["Resistencia"] = 50

        stats["cartas_compradas"]["Defesa"] += 1

    elif nome == "Sorte":

        stats["Chance_Sorte"] += 0.006

        stats["cartas_compradas"]["Sorte"] += 1

    elif nome == "Poison":

        stats["Poison_Active"] = True

        stats["Dano_Veneno_Acumulado"] += 0.05

        stats["cartas_compradas"]["Poison"] += 1

    elif nome == "Coletora":

        stats["Executa_inimigo"] += 0.005

        stats["Ultimo_Estalo"] = True

        stats["cartas_compradas"]["Coletora"] += 1

    elif nome == "Mercenaria":

        stats["Mercenaria_Active"] = True

        stats["Valor_Bonus"] += 25

        stats["cartas_compradas"]["Coletora"] += 1

    

    return stats



def coletar_cartas_no_chao(personagem_rect, stats, efeitos_texto_lista):

    """Verifica colisão do personagem com cartas no chão, aplica efeitos e retorna lista de nomes coletados."""

    global cartas_no_chao

    coletadas = []

    novas_cartas = []

    tempo_agora = pygame.time.get_ticks()

    

    for carta in cartas_no_chao:

        if personagem_rect.colliderect(carta["rect"]):

            nome = carta["nome"]

            aplicar_carta_drop(nome, stats)

            coletadas.append(nome)

            

            # Adicionar efeito de texto flutuante

            efeitos_texto_lista.append({

                "texto": f"+{nome}",

                "x": carta["rect"].centerx,

                "y": carta["rect"].centery - 20,

                "cor": (255, 215, 0) if nome in {"Tempestade", "Trembo", "Petro", "Poison", "Coletora"} else (0, 255, 230),

                "tempo_inicio": tempo_agora

            })

        else:

            novas_cartas.append(carta)

    

    cartas_no_chao = novas_cartas

    return coletadas



# --- SISTEMA DE REWIND TEMPORAL ---

historico_rewind = []

snapshot_para_carregar = None

ultimo_registro_tempo = 0

tentativas_rewind = 0

MAX_TENTATIVAS_REWIND = 3



# Penalidades por tentativa: (fração de vida, modo de cartas)

# modo: "manter" = mantém cartas, "metade" = perde metade aleatoriamente, "nenhuma" = perde todas

_PENALIDADES_REWIND = [

    (0.20, "manter"),   # 1ª tentativa

    (0.10, "metade"),   # 2ª tentativa

    (0.05, "nenhuma"),  # 3ª tentativa

]



def pode_tentar_novamente():

    return tentativas_rewind < MAX_TENTATIVAS_REWIND and len(historico_rewind) > 0



def obter_penalidade_atual():

    """Retorna (fração_vida, modo_cartas) da PRÓXIMA tentativa."""

    idx = min(tentativas_rewind, MAX_TENTATIVAS_REWIND - 1)

    return _PENALIDADES_REWIND[idx]



def registrar_snapshot(dados, tempo_atual):

    global historico_rewind, ultimo_registro_tempo

    # Registrar no máximo a cada 1000ms (1 segundo)

    if tempo_atual - ultimo_registro_tempo >= 1000:

        ultimo_registro_tempo = tempo_atual

        historico_rewind.append(dados)

        # Manter os últimos 11 snapshots (10 segundos + margem)

        if len(historico_rewind) > 11:

            historico_rewind.pop(0)



def obter_snapshot_rewind():

    global historico_rewind

    if not historico_rewind:

        return None

    return historico_rewind[0]



def _aplicar_penalidade_cartas(atributos, modo):

    """Modifica cartas_compradas no dict de atributos conforme o modo de penalidade."""

    import random as _rnd

    cartas = atributos.get("cartas_compradas", {})

    if not cartas:

        return



    if modo == "metade":

        # Pegar todas as cartas que o jogador possui (count > 0)

        cartas_possuidas = [nome for nome, qtd in cartas.items() if qtd > 0]

        if cartas_possuidas:

            qtd_remover = max(1, len(cartas_possuidas) // 2)

            cartas_a_remover = _rnd.sample(cartas_possuidas, min(qtd_remover, len(cartas_possuidas)))

            for nome in cartas_a_remover:

                cartas[nome] = 0

    elif modo == "nenhuma":

        for nome in cartas:

            cartas[nome] = 0



    atributos["cartas_compradas"] = cartas



def preparar_rewind():

    global snapshot_para_carregar, tentativas_rewind

    if not pode_tentar_novamente():

        return False

    snapshot = obter_snapshot_rewind()

    if snapshot:

        vida_fracao, modo_cartas = obter_penalidade_atual()

        tentativas_rewind += 1



        snapshot_copia = {

            "atributos": snapshot.get("atributos", {}).copy(),

            "pos_x": snapshot.get("pos_x"),

            "pos_y": snapshot.get("pos_y"),

            "vida_boss": snapshot.get("vida_boss"),

            "vida_fracao": vida_fracao,

        }



        import json

        import os

        try:

            atributos = snapshot_copia["atributos"]

            # Sobrescrever vida para a fração correspondente à tentativa

            vida_max = atributos.get("vida_maxima_personagem", 100)

            atributos["vida_atual_personagem"] = vida_fracao * vida_max

            # Aplicar penalidade de cartas

            _aplicar_penalidade_cartas(atributos, modo_cartas)

            # Salvar de volta

            os.makedirs("saves", exist_ok=True)

            with open("saves/atributos.json", "w") as file:

                json.dump(atributos, file)

        except Exception as e:

            print("Erro ao preparar rewind:", e)



        snapshot_para_carregar = snapshot_copia

        return True

    return False



def limpar_historico_rewind():

    global historico_rewind, snapshot_para_carregar, ultimo_registro_tempo, tentativas_rewind

    historico_rewind = []

    snapshot_para_carregar = None

    ultimo_registro_tempo = 0

    tentativas_rewind = 0





def reset_game_session():

    """Reseta todo o estado global do jogo para iniciar uma partida 100% nova."""

    global tempo_acumulado, tempo_inicial, cronometro_pausado, r_press, iniciar_boss

    global jogador_morto, outro_jogador_morto, jogador_remoto_morto

    global vida, vida_maxima, pontuacao, pontuacao_exib, pontuacao_magia

    global inimigos_eliminados, moedas_coletadas, moedas_totais, moedas_soltadas

    global Chance_Sorte, Poison_Active, boss_envenenado, Dano_Veneno_Acumulado

    global Ultimo_Estalo, Executa_inimigo, Resistencia, xp_petro, dano_inimigo_perto

    global velocidade_personagem, intervalo_disparo, dano_person_hit, chance_critico

    global roubo_de_vida, quantidade_roubo_vida, Mercenaria_Active, Valor_Bonus

    global Tempo_cura, porcentagem_cura, tempo_ultima_regeneracao, cartas_compradas

    global trembo, Petro_active, vida_petro, vida_maxima_petro, dano_petro, Resistencia_petro, petro_evolucao

    global boss_vivo1, vida_boss, vida_maxima_boss1, boss_morte_processada

    global Boss_vivo3, vida_boss3, vida_maxima_boss3

    global player_hemorragia_ativa, tempo_fim_hemorragia, player_em_chamas, tempo_fim_chamas

    global esferas_energia_umbra, ondas, correntes_eletricas, eliminacoes_consecutivas, bonus_pontuacao

    global pos_x_personagem, pos_y_personagem, trauma_umbra_acumulado



    import time

    

    # Cronômetro e Fluxo

    tempo_acumulado = 0

    tempo_inicial = time.time()

    cronometro_pausado = False

    r_press = False

    iniciar_boss = False

    

    # Jogador Estado Básico

    vida_maxima = 450

    vida = 450

    pos_x_personagem = 100

    pos_y_personagem = 100

    jogador_morto = False

    outro_jogador_morto = False

    jogador_remoto_morto = False

    

    # Pontuação e Economia

    pontuacao = 0

    pontuacao_exib = 500

    pontuacao_magia = 0

    inimigos_eliminados = 0

    moedas_coletadas = 0

    moedas_totais = 0

    moedas_soltadas = []

    

    # Habilidades / Atributos Especiais

    Chance_Sorte = 0.01

    Poison_Active = False

    boss_envenenado = False

    Dano_Veneno_Acumulado = 0.05

    Ultimo_Estalo = False

    Executa_inimigo = 0.05

    Resistencia = 35

    xp_petro = 1

    dano_inimigo_perto = 30

    velocidade_personagem = 3

    intervalo_disparo = 800

    dano_person_hit = 35

    chance_critico = 0.02

    roubo_de_vida = 0.0

    quantidade_roubo_vida = 0.0

    Mercenaria_Active = False

    Valor_Bonus = 25

    Tempo_cura = 2500

    porcentagem_cura = 0.005

    tempo_ultima_regeneracao = 0

    trembo = False

    

    # Petro

    Petro_active = False

    vida_petro = 500

    vida_maxima_petro = 500

    dano_petro = 25

    Resistencia_petro = 20

    petro_evolucao = 1

    

    # Cartas

    cartas_compradas = {

        "Speed Boost": 0,

        "Porção": 0,

        "Disparo crescente": 0,

        "Tempestade": 0,

        "Cura": 0,

        "Trembo": 0,

        "Speed Atack": 0,

        "Teleporte": 0,

        "Petro": 0,

        "Defesa": 0,

        "Sorte": 0,

        "Poison": 0,

        "Coletora": 0,

    }

    

    # Bosses

    boss_vivo1 = False

    vida_boss = 5000

    vida_maxima_boss1 = 5000

    boss_morte_processada = False

    

    Boss_vivo3 = False

    vida_boss3 = 20000

    vida_maxima_boss3 = 20000

    

    # Efeitos / Projéteis

    player_hemorragia_ativa = False

    tempo_fim_hemorragia = 0

    player_em_chamas = False

    tempo_fim_chamas = 0

    esferas_energia_umbra = []

    ondas = []

    correntes_eletricas = []

    eliminacoes_consecutivas = 0

    bonus_pontuacao = 0

    trauma_umbra_acumulado = 0





def reset_phase_state():

    """Reseta estados de boss, inimigos e projéteis entre as fases, preservando upgrades e o timer."""

    global r_press, iniciar_boss, boss_vivo1, boss_morte_processada, Boss_vivo3, player_hemorragia_ativa, player_em_chamas

    global esferas_energia_umbra, ondas, correntes_eletricas, moedas_soltadas, pos_x_personagem, pos_y_personagem

    

    r_press = False

    iniciar_boss = False

    boss_vivo1 = False

    boss_morte_processada = False

    Boss_vivo3 = False

    player_hemorragia_ativa = False

    player_em_chamas = False

    esferas_energia_umbra = []

    ondas = []

    correntes_eletricas = []

    moedas_soltadas = []

    

    # Resetar posições do jogador para uma área padrão na nova fase

    pos_x_personagem = 100

    pos_y_personagem = 100





