
import Caminhos
import pygame
import sys
import random
import math
import subprocess
import json
import os
from qa_logger import instalar_captura_global, instalar_filtro_prints, registrar_erro
from Tela_Cartas import tela_de_pausa
from Variaveis import *
from habilidades_personagem import processar_habilidade_onda, atualizar_e_desenhar_correntes
import Variaveis
from utils import *
from ui_helpers import (
    desenhar_hud_fase,
    obter_pos_mouse_jogo,
    tela_transicao_dimensional,
    desenhar_efeitos_vanguarda,
    desenhar_efeito_racional_dilatacao,
    fator_movimento_racional,
    fator_mundo_racional,
    intervalo_disparo_racional,
)
from audio_manager import carregar_config_audio, aplicar_volume_som
from Tela_Upgrade_Aureas import tela_upgrade_aureas

instalar_captura_global()
instalar_filtro_prints()

dt = 1.0

# Forward declarations (atribuídos no loop principal)
botao_mouse = (False, False, False)
sprite_moeda = None
escudo_devota_ativo = True
duracao_incendio_vanguarda = 5000
intervalo_escudo = 30000
racional_dilatacao_fim = 0
gerar_fragmentos_morte = None
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

Boss_andando=False
texto_dano = None
tempo_texto_dano = 0

estalos = aplicar_volume_som(pygame.mixer.Sound("Sounds/Estalo.mp3"), config_audio)

som_ataque_boss = aplicar_volume_som(pygame.mixer.Sound("Sounds/Hit_Boss1.mp3"), config_audio)

Hit_inimigo3 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Inimigo3_hit.mp3"), config_audio)

Disparo_Geo = aplicar_volume_som(pygame.mixer.Sound("Sounds/Disparo_Geo.wav"), config_audio)

Musica_tema_Boss3 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase3_Boss.mp3"), config_audio)  

Musica_tema_fases = pygame.mixer.Sound("Sounds/Fase_boas.mp3")
Musica_tema_fases.set_volume(0.07)  

Som_tema_fases = pygame.mixer.Sound("Sounds/Esgoto.mp3")
Som_tema_fases.set_volume(0.10)  

Som_portal = pygame.mixer.Sound("Sounds/Portal.mp3")
Som_portal.set_volume(0.06)  

Boss_Queijo= pygame.mixer.Sound("Sounds/Queijo.mp3")
Boss_Queijo.set_volume(0.11)  

Boss3_andando= pygame.mixer.Sound("Sounds/Boss3_andando.mp3")
Boss3_andando.set_volume(0.7)  

Frascos= pygame.mixer.Sound("Sounds/Frasco.mp3")
Frascos.set_volume(0.02)  

toque=0

musica_boss3= 1



# Defina os limites da área onde o queijo pode aparecer (exemplo)
area_x_min = 10
area_x_max = 800
area_y_min = 10
area_y_max = 800
# Carregue e exiba a sprite de queijo no meio da tela
sprite_queijo = pygame.image.load('Sprites/queijo.png')
largura_queijo, altura_queijo = sprite_queijo.get_size()

queijo_spawn=False
vida_queijo = 25
tempo_ultimo_grupo_disparo_boss3 = 0
tempo_espera_grupo_disparo_boss3 = 5000  # Tempo de espera entre cada grupo de disparo (em milissegundos)

# Defina as dimensões da hitbox do queijo (largura e altura)
largura_hitbox_queijo = largura_queijo + 50  # Adicione 20 pixels à largura
altura_hitbox_queijo = altura_queijo + 50  # Adicione 20 pixels à altura
pos_x_chefe3 = largura_tela /1.3  # Posição inicial do boss na tela (à direita)
pos_y_chefe3 = altura_tela / 3   # Centralizado verticalmente
chefe_largura3,chefe_altura3= largura_tela * 0.2, altura_tela * 0.3
disparos_boss3=[]
tempo_espera_ataque_boss3=5000
carregar_atributos_na_fase=True
tempo_boss_entrada_fim = 0


# Carregar os frames do boss
boss_frame1 = pygame.image.load("Sprites/Boss3_1.png")
boss_frame1 = pygame.transform.scale(boss_frame1, (largura_tela * 0.2, altura_tela * 0.3))

boss_frame2 = pygame.image.load("Sprites/Boss3_2.png")
boss_frame2 = pygame.transform.scale(boss_frame2, (largura_tela * 0.2, altura_tela * 0.3))

# Carregar os frames do boss
boss_frame_andando1 = pygame.image.load("Sprites/Bossandando3_1.png")
boss_frame_andando1 = pygame.transform.scale(boss_frame_andando1, (largura_tela * 0.2, altura_tela * 0.3))

boss_frame_andando2 = pygame.image.load("Sprites/Bossandando3_2.png")
boss_frame_andando2 = pygame.transform.scale(boss_frame_andando2, (largura_tela * 0.2, altura_tela * 0.3))
boss_frame_andando = boss_frame_andando1  # Inicialize com o primeiro frame

boss_frame_peca1 = pygame.image.load("Sprites/peça.png")
boss_frame_peca1 = pygame.transform.scale(boss_frame_peca1, (64, 64))
boss_frame_peca2 = pygame.image.load("Sprites/peça.png")
boss_frame_peca2 = pygame.transform.scale(boss_frame_peca2, (64, 64))
boss_frame_peca = boss_frame_peca1  # Inicialize com o primeiro frame


boss_frame_atual = boss_frame1  # Inicialize com o primeiro frame
tempo_ultimo_frame_boss = pygame.time.get_ticks()  # Inicialize o tempo do último frame do boss

# Configurações da tela
 
tela = pygame.Surface((largura_mapa, altura_mapa))
pygame.display.set_caption("Renderizando Mapa com Personagem")

# Variáveis para a barra de magia
pontuacao_inimigos=0
maxima_pontuacao_magia = 750
piscar_magia = False

# Variáveis para controlar a imobilização da personagem
personagem_doente = False
tempo_ultimo_atingido = pygame.time.get_ticks()
tempo_doente = 800  # Tempo em milissegundos de imobilização após ser atingido

spawn_inimigo=True



intervalo_disparo_inimigo = 1500  # Intervalo de 2 segundos entre os disparos dos inimigos 
tempo_ultimo_disparo_inimigo = pygame.time.get_ticks()  # Adicione esta variável global para controlar o tempo do último disparo de cada inimigo





#INIMIGOS
nivel_ameaca = inimigos_eliminados // 10
tempo_ultimo_inimigo_apos_morte = pygame.time.get_ticks()
# Adicione esta variável global para controlar o tempo do último disparo de cada inimigo
tempo_ultimo_disparo_inimigo = pygame.time.get_ticks()
cronometro_pausado = False
retomar_cronometro()

# Carregar a imagem do mapa
mapa = pygame.image.load(mapa_path3).convert()
mapa = pygame.transform.scale(mapa, (largura_tela, altura_tela))


disparos_inimigos = []


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
frames_inimigo = frames_inimigo_esquerda3 + frames_inimigo_direita3


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
        "Chance_Sorte": Chance_Sorte,
        "cartas_compradas": cartas_compradas,
    }

    with open('saves/atributos.json', 'w') as file:
        json.dump(atributos, file)

def carregar_atributos():
    global velocidade_personagem, intervalo_disparo, dano_person_hit, chance_critico, roubo_de_vida, quantidade_roubo_vida,vida_maxima,vida_maxima_petro,vida,xp_petro,Petro_active,trembo,dano_petro,Resistencia,Resistencia_petro,dano_inimigo_longe,dano_inimigo_perto,direcao_atual,Poison_Active,Ultimo_Estalo,Executa_inimigo,Valor_Bonus,Mercenaria_Active,tempo_cooldown_dash,vida_petro,petro_evolucao,Dano_Veneno_Acumulado, Tempo_cura,porcentagem_cura, moedas_totais, Chance_Sorte, cartas_compradas
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
        Chance_Sorte = atributos.get("Chance_Sorte", 0.01)
        if "cartas_compradas" in atributos:
            cartas_compradas.update(atributos["cartas_compradas"])


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
    global pos_x_personagem, pos_y_personagem, direcao_atual, ultima_tecla_movimento, dano_person_hit
    global movimento_pressionado, cooldown_dash, distancia_dash, tempo_ultimo_dash, teleporte_duration
    global personagem_doente, tempo_ultimo_atingido, angulo_inclinacao_personagem
    global vida_inimigo_maxima, Resistencia_petro, dano_inimigo_perto, vida_maxima_petro, dano_petro, dano_inimigo_longe
    global inimigos_eliminados, pontuacao, pontuacao_exib, eliminacoes_consecutivas, bonus_pontuacao, Boss_vivo3
    global vida_boss3, vida_maxima_boss3, vida_boss4, vida_maxima_boss4, Valor_Bonus
    global racional_dilatacao_fim

    direcao_atual = 'stop'  # Por padrão, definimos a direção como 'stop'
    dx, dy = 0, 0
    velocidade_movimento = velocidade_personagem * fator_movimento_racional(aurea, racional_dilatacao_fim)

    # ---- TECLADO ----
    if Variaveis.verificar_input("Mover para direita"): dx, ultima_tecla_movimento = 1, 'right'
    elif Variaveis.verificar_input("Mover para esquerda"): dx, ultima_tecla_movimento = -1, 'left'
    
    if Variaveis.verificar_input("Mover para cima"): dy, ultima_tecla_movimento = -1, 'up'
    elif Variaveis.verificar_input("Mover para baixo"): dy, ultima_tecla_movimento = 1, 'down'

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

    # INVERTER CONTROLES SE ESTIVER DOENTE
    if personagem_doente:
        dx = -dx
        dy = -dy
        # inverte também a direção base do sprite
        if ultima_tecla_movimento == 'right': ultima_tecla_movimento = 'left'
        elif ultima_tecla_movimento == 'left': ultima_tecla_movimento = 'right'
        elif ultima_tecla_movimento == 'up': ultima_tecla_movimento = 'down'
        elif ultima_tecla_movimento == 'down': ultima_tecla_movimento = 'up'

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
                                         pos_x_personagem + dx * velocidade_movimento * fator_normalizacao * dt))
            pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                         pos_y_personagem + dy * velocidade_movimento * fator_normalizacao * dt))
        else:
            angulo_inclinacao_personagem = 0
            pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                         pos_x_personagem + dx * velocidade_movimento * dt))
            pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                         pos_y_personagem + dy * velocidade_movimento * dt))
        
        pos_x_personagem, pos_y_personagem = Variaveis.resolver_colisao_player_com_inimigos(
            pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, inimigos_comum
        )
        pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem))
        pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem))
    else:
        angulo_inclinacao_personagem = 0
        if botao_mouse[0]:
            direcao_atual = 'disp'
        else:
            direcao_atual = 'stop'

    # ---- DASH/TELEPORTE ----
    executar_teleporte_mouse_flag = False
    if Variaveis.obter_modo_teleporte() == "mouse":
        dash_teclado = False
        dash_joystick = False
        Variaveis.atualizar_estado_teleporte()
        if Variaveis.executar_teleporte_pendente and not cooldown_dash:
            executar_teleporte_mouse_flag = True
            Variaveis.executar_teleporte_pendente = False
    else:
        dash_teclado = Variaveis.verificar_input("Teleporte")
        dash_joystick = joystick and joystick.get_button(4) if joystick else False

    if (dash_teclado or dash_joystick or executar_teleporte_mouse_flag) and cooldown_dash == False:
        Som_portal.play()

        if executar_teleporte_mouse_flag:
            px_c = pos_x_personagem + largura_personagem // 2
            py_c = pos_y_personagem + altura_personagem // 2
            dest_x, dest_y = Variaveis.calcular_destino_teleporte(px_c, py_c, distancia_dash)
            dest_px = max(0, min(largura_mapa - largura_personagem, dest_x - largura_personagem // 2))
            dest_py = max(0, min(altura_mapa - altura_personagem, dest_y - altura_personagem // 2))
            
            animar_teleporte_plasma(tela, mapa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, teleporte_duration // 2, ultima_tecla_movimento, distancia_dash, largura_mapa, altura_mapa, dest_x=dest_px, dest_y=dest_py)
            tela.blit(mapa, (pos_x_personagem, pos_y_personagem), pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem))
            pos_x_personagem, pos_y_personagem = dest_px, dest_py
        else:
            animar_teleporte_plasma(tela, mapa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, teleporte_duration // 2, ultima_tecla_movimento, distancia_dash, largura_mapa, altura_mapa)
            tela.blit(mapa, (pos_x_personagem, pos_y_personagem), pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem))
            if ultima_tecla_movimento == 'up': pos_y_personagem = max(0, pos_y_personagem - distancia_dash)
            elif ultima_tecla_movimento == 'down': pos_y_personagem = min(altura_mapa - altura_personagem, pos_y_personagem + distancia_dash)
            elif ultima_tecla_movimento == 'left': pos_x_personagem = max(0, pos_x_personagem - distancia_dash)
            elif ultima_tecla_movimento == 'right': pos_x_personagem = min(largura_mapa - largura_personagem, pos_x_personagem + distancia_dash)

        cooldown_dash = True
        tempo_ultimo_dash = pygame.time.get_ticks()
        if aurea == "Racional":
            racional_dilatacao_fim = tempo_ultimo_dash + 3000

        # Onda de choque no destino do teletransporte
        cx_t = pos_x_personagem + largura_personagem // 2
        cy_t = pos_y_personagem + altura_personagem // 2
        raio_choque = 120
        dano_choque = dano_person_hit * 0.3

        ondas_choque.append({
            "cx": cx_t,
            "cy": cy_t,
            "raio_atual": 10.0,
            "raio_max": raio_choque,
            "velocidade": 8.0,
            "cor": (0, 191, 255)
        })

        # Dano nos inimigos comuns próximos
        inimigos_atingidos = []
        for inimigo in inimigos_comum:
            dist = math.hypot(inimigo["rect"].centerx - cx_t, inimigo["rect"].centery - cy_t)
            if dist <= raio_choque:
                inimigos_atingidos.append(inimigo)

        for inimigo in inimigos_atingidos:
            inimigo["vida"] -= dano_choque
            efeitos_texto.append({
                "texto": f"-{int(dano_choque)}",
                "x": inimigo["rect"].x,
                "y": inimigo["rect"].y - 20,
                "tempo_inicio": pygame.time.get_ticks(),
                "cor": (0, 191, 255)
            })
            if inimigo["vida"] <= 0:
                posicao_inimigo = inimigo["rect"].center
                soltar_moeda(posicao_inimigo)
                Variaveis.tentar_soltar_carta(posicao_inimigo, tempo_atual, Chance_Sorte, inimigos_eliminados)
                gerar_fragmentos_morte(inimigo, 3)
                if inimigo in inimigos_comum:
                    inimigos_comum.remove(inimigo)
                
                # Escalonamento de elite (Fase 3)
                mult = 1.0 + (nivel_ameaca * 0.15)
                vida_inimigo_maxima += 0.8 * mult
                Resistencia_petro += 0.02 * mult
                dano_inimigo_perto += 0.08 * mult
                dano_person_hit += 0.12 * mult
                vida_maxima_petro += 1.2 * mult
                dano_petro += 0.01 * mult
                dano_inimigo_longe += 0.025 * mult

                inimigos_eliminados += 1
                ganho = int(150 * (1 + math.log10(inimigos_eliminados + 1)))
                pontuacao += ganho

                if Mercenaria_Active:
                    eliminacoes_consecutivas += 1
                    pontuacao_exib += ganho + bonus_pontuacao
                    if eliminacoes_consecutivas % 5 == 0:
                        bonus_pontuacao = min(800, bonus_pontuacao + Valor_Bonus)
                else:
                    pontuacao_exib += ganho

                if not Boss_vivo3:
                    incremento_v = 20 * mult
                    vida_boss3 += incremento_v
                    vida_maxima_boss3 = vida_boss3
                    vida_boss4 += incremento_v * 1.5
                    vida_maxima_boss4 = vida_boss4

        # Dano ao Boss 3
        if Boss_vivo3:
            bx = pos_x_chefe3 + chefe_largura // 2
            by = pos_y_chefe3 + chefe_altura // 2
            dist_boss = math.hypot(bx - cx_t, by - cy_t)
            if dist_boss <= raio_choque:
                vida_boss3 -= dano_choque
                efeitos_texto.append({
                    "texto": f"-{int(dano_choque)}",
                    "x": pos_x_chefe3 + chefe_largura // 2,
                    "y": pos_y_chefe3 - 20,
                    "tempo_inicio": pygame.time.get_ticks(),
                    "cor": (0, 191, 255)
                })

    # Atualizar o cooldown do dash
    if cooldown_dash and pygame.time.get_ticks() - tempo_ultimo_dash > tempo_cooldown_dash:
        cooldown_dash = False

    return direcao_atual



# Antes do loop principal, crie uma lista para armazenar os inimigos
inimigos_comum = []

tempo_ultima_criacao_gelo = pygame.time.get_ticks()



def criar_disparo_inimigo(pos_inimigo, pos_personagem):
    dx = pos_personagem[0] - pos_inimigo[0]
    dy = pos_personagem[1] - pos_inimigo[1]
    dist = max(1, math.sqrt(dx ** 2 + dy ** 2))

    
    velocidade_disparo_inimigo = 1.6  
    direcao_disparo_inimigo = (dx / dist * velocidade_disparo_inimigo, dy / dist * velocidade_disparo_inimigo)

    return {"rect": pygame.Rect(pos_inimigo[0], pos_inimigo[1], largura_disparo, altura_disparo), "velocidade": direcao_disparo_inimigo}


def criar_inimigo(x, y):
    image = frames_inimigo_esquerda3[0]
    return {"rect": pygame.Rect(x, y, largura_inimigo3, altura_inimigo3), "image": image, "vida": vida_inimigo_maxima, "vida_maxima": vida_inimigo_maxima}

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


tempo_parado_person = pygame.time.get_ticks() 
tempo_ultimo_disparo = pygame.time.get_ticks()

tempo_ultimo_escudo = pygame.time.get_ticks()
Som_tema_fases.play(loops=-1)
movimento_pressionado = False
fonte = None
running = True
tempo_atual = 0
upgrades = {}
x = 0
y = 0

def executar_jogo(game_manager=None):
    global dt
    global Boss_vivo3, gerar_fragmentos_morte, Chance_Sorte, Dano_Veneno_Acumulado, Executa_inimigo, Mercenaria_Active, Musica_tema_Boss3, Musica_tema_fases, Petro_active, Poison_Active, Resistencia, Resistencia_petro, Tempo_cura, Ultimo_Estalo, Valor_Bonus, altura_disparo, bonus_pontuacao, boss_envenenado, boss_frame_andando, boss_frame_atual, boss_frame_peca, carregar_atributos_na_fase, cartas_compradas, chance_critico, dano_inimigo_longe, dano_inimigo_perto, dano_person_hit, dano_petro, dano_por_tick_veneno_boss, disparos, disparos_boss3, disparos_inimigos, dispositivo_ativo, efeitos_texto, eliminacoes_consecutivas, eliminacoes_consecutivas_impulsiva, escudo_devota_ativo, fonte, frame_atual, impulsiva_ativa, imune_tempo_restante, inimigos_atingidos_por_onda, inimigos_eliminados, inimigos_em_chamas, intervalo_disparo, largura_disparo, max_inimigos2, moedas_coletadas, moedas_soltadas, moedas_totais, movimento_pressionado, musica_boss3, nivel_ameaca, ondas, personagem_doente, petro_evolucao, piscando_vida, pontuacao, pontuacao_exib, pontuacao_magia, porcentagem_cura, pos_x_chefe3, pos_x_personagem, pos_x_petro, pos_y_chefe3, pos_y_personagem, pos_y_petro, quantidade_roubo_vida, queijo_geracao, queijo_spawn, r_press, rect_boss, roubo_de_vida, running, spawn_inimigo, sprite_moeda, teleportado, tempo_anterior_petro, tempo_atual, tempo_boss_entrada_fim, tempo_cooldown_dash, tempo_inicio_buff_impulsiva, tempo_inicio_veneno_boss, tempo_passado, tempo_texto_dano, tempo_ultima_atualizacao_direcao, tempo_ultima_regeneracao, tempo_ultimo_atingido, tempo_ultimo_disparo_inimigo, tempo_ultimo_frame_boss, tempo_ultimo_grupo_disparo_boss3, tempo_ultimo_hit_inimigo, tempo_ultimo_inimigo, tempo_ultimo_uso_habilidade, texto_dano, tipo_buff_impulsiva, toque, trembo, ultima_direcao_animacao, ultimo_tick_veneno_boss, upgrades, velocidade_personagem, vida, vida_boss3, vida_boss4, vida_inimigo_maxima, vida_maxima, vida_maxima_boss3, vida_maxima_boss4, vida_maxima_petro, vida_petro, vida_queijo, x, xp_petro, y, duracao_incendio_vanguarda, intervalo_escudo, comando_direção_petro
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
        global tela
        tela = configurar_tela(largura_mapa, altura_mapa)

        # Pre-carregar frames de disparo
        frames_disparo_normal_base = [
            pygame.image.load("Sprites/Fogo1.png").convert_alpha(),
            pygame.image.load("Sprites/Fogo2.png").convert_alpha()
        ]
        frames_disparo_impulso_base = [
            pygame.image.load("Sprites/Fogo_impulso1.png").convert_alpha(),
            pygame.image.load("Sprites/Fogo_impulso2.png").convert_alpha()
        ]
        
        Musica_tema_fases.play(loops=-1)
        upgrades = carregar_upgrade_aureas("saves/aureas_upgrade.json")
        ondas_choque = []

        # Configurar e escalar as passivas das áureas
        nivel_devota = upgrades.get("Devota", 0)
        nivel_vanguarda = upgrades.get("Vanguarda", 0)
        nivel_impulsiva = upgrades.get("Impulsiva", 0)

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
        fragmentos_morte = []

        def gerar_fragmentos_morte(inimigo, fase):
            if not (config_graficos.get("particulas_ativas", True) and config_graficos.get("efeitos_visuais", True)):
                return
            rect_inimigo = inimigo["rect"]
            gerar_particulas_pontos(rect_inimigo)
            for _ in range(random.randint(15, 25)):
                px = random.uniform(rect_inimigo.left, rect_inimigo.right)
                py = random.uniform(rect_inimigo.top, rect_inimigo.bottom)
                vx = random.uniform(-3, 3)
                vy = random.uniform(-4, 1)
                
                if fase == 1:
                    r = random.randint(120, 200)
                    g = random.randint(30, 80)
                    b = random.randint(200, 255)
                    color = (r, g, b)
                elif fase == 2:
                    r = random.randint(0, 50)
                    g = random.randint(130, 220)
                    b = random.randint(220, 255)
                    color = (r, g, b)
                elif fase == 3:
                    r = random.randint(220, 255)
                    g = random.randint(180, 225)
                    b = random.randint(0, 50)
                    color = (r, g, b)
                elif fase == 4:
                    if random.random() < 0.5:
                        r = random.randint(120, 180)
                        g = random.randint(30, 70)
                        b = random.randint(180, 240)
                    else:
                        r = random.randint(210, 255)
                        g = random.randint(170, 210)
                        b = random.randint(0, 40)
                    color = (r, g, b)
                else:
                    color = (255, 255, 255)
                    
                size = random.uniform(3, 8)
                shape_type = random.choice(["triangulo", "losango", "quadrado"])
                if shape_type == "triangulo":
                    vertices = [
                        (0, -size),
                        (-size * 0.8, size * 0.6),
                        (size * 0.8, size * 0.6)
                    ]
                elif shape_type == "losango":
                    vertices = [
                        (0, -size),
                        (size * 0.6, 0),
                        (0, size),
                        (-size * 0.6, 0)
                    ]
                else:
                    vertices = [
                        (-size * 0.5, -size * 0.5),
                        (size * 0.5, -size * 0.5),
                        (size * 0.5, size * 0.5),
                        (-size * 0.5, size * 0.5)
                    ]
                    
                fragmentos_morte.append({
                    "x": px,
                    "y": py,
                    "vx": vx,
                    "vy": vy,
                    "color": color,
                    "vertices": vertices,
                    "rot": random.uniform(0, 360),
                    "vrot": random.uniform(-10, 10),
                    "life": random.randint(30, 50)
                })

        def gerar_explosao_branca(cx, cy):
            if not (config_graficos.get("particulas_ativas", True) and config_graficos.get("efeitos_visuais", True)):
                return
            for _ in range(random.randint(40, 60)):
                px = cx + random.uniform(-10, 10)
                py = cy + random.uniform(-10, 10)
                angulo = random.uniform(0, 2 * math.pi)
                velocidade = random.uniform(4, 12)
                vx = math.cos(angulo) * velocidade
                vy = math.sin(angulo) * velocidade
                
                choice = random.random()
                if choice < 0.8:
                    color = (255, 255, 255)
                elif choice < 0.9:
                    color = (240, 240, 255)
                else:
                    color = (255, 255, 200)
                    
                size = random.uniform(3, 8)
                shape_type = random.choice(["triangulo", "losango", "quadrado"])
                if shape_type == "triangulo":
                    vertices = [
                        (0, -size),
                        (-size * 0.8, size * 0.6),
                        (size * 0.8, size * 0.6)
                    ]
                elif shape_type == "losango":
                    vertices = [
                        (0, -size),
                        (size * 0.6, 0),
                        (0, size),
                        (-size * 0.6, 0)
                    ]
                else:
                    vertices = [
                        (-size * 0.5, -size * 0.5),
                        (size * 0.5, -size * 0.5),
                        (size * 0.5, size * 0.5),
                        (-size * 0.5, size * 0.5)
                    ]
                    
                fragmentos_morte.append({
                    "x": px,
                    "y": py,
                    "vx": vx,
                    "vy": vy,
                    "color": color,
                    "vertices": vertices,
                    "rot": random.uniform(0, 360),
                    "vrot": random.uniform(-12, 12),
                    "life": random.randint(30, 50)
                })

        def gerar_fragmentos_trembo(x, y, w, h):
            if not (config_graficos.get("particulas_ativas", True) and config_graficos.get("efeitos_visuais", True)):
                return
            for _ in range(random.randint(30, 45)):
                px = random.uniform(x, x + w)
                py = random.uniform(y, y + h)
                vx = random.uniform(-6, 6)
                vy = random.uniform(-6, 6)
                
                choice = random.random()
                if choice < 0.4:
                    color = (0, random.randint(180, 255), 255)  # Ciano / Sky Blue
                elif choice < 0.7:
                    color = (255, 255, 255)  # Branco
                else:
                    color = (random.randint(160, 220), 50, 255)  # Roxo / Violeta
                    
                size = random.uniform(4, 9)
                shape_type = random.choice(["triangulo", "losango", "quadrado"])
                if shape_type == "triangulo":
                    vertices = [
                        (0, -size),
                        (-size * 0.8, size * 0.6),
                        (size * 0.8, size * 0.6)
                    ]
                elif shape_type == "losango":
                    vertices = [
                        (0, -size),
                        (size * 0.6, 0),
                        (0, size),
                        (-size * 0.6, 0)
                    ]
                else:
                    vertices = [
                        (-size * 0.5, -size * 0.5),
                        (size * 0.5, -size * 0.5),
                        (size * 0.5, size * 0.5),
                        (-size * 0.5, size * 0.5)
                    ]
                    
                fragmentos_morte.append({
                    "x": px,
                    "y": py,
                    "vx": vx,
                    "vy": vy - 2.0,
                    "color": color,
                    "vertices": vertices,
                    "rot": random.uniform(0, 360),
                    "vrot": random.uniform(-15, 15),
                    "life": random.randint(40, 65)
                })

        def atualizar_e_desenhar_fragmentos(tela):
            if not (config_graficos.get("particulas_ativas", True) and config_graficos.get("efeitos_visuais", True)):
                fragmentos_morte.clear()
                return
            novos_frag = []
            for f in fragmentos_morte:
                f["x"] += f["vx"]
                f["y"] += f["vy"]
                f["vy"] += 0.15
                f["vx"] *= 0.98
                f["rot"] += f["vrot"]
                f["life"] -= 1
                
                if f["life"] <= 0:
                    continue
                    
                rad = math.radians(f["rot"])
                cos_r = math.cos(rad)
                sin_r = math.sin(rad)
                
                rotated_vertices = []
                for vx, vy in f["vertices"]:
                    rx = f["x"] + (vx * cos_r - vy * sin_r)
                    ry = f["y"] + (vx * sin_r + vy * cos_r)
                    rotated_vertices.append((rx, ry))
                    
                pygame.draw.polygon(tela, f["color"], rotated_vertices)
                novos_frag.append(f)
            fragmentos_morte[:] = novos_frag

        particulas_pontos = []

        def gerar_particulas_pontos(rect_inimigo):
            if not (config_graficos.get("particulas_ativas", True) and config_graficos.get("efeitos_visuais", True)):
                return
            qualidade = config_graficos.get("qualidade_grafica", "alta")
            quantidade = random.randint(5, 8) if qualidade == "alta" else random.randint(2, 3)
            
            for _ in range(quantidade):
                px = random.uniform(rect_inimigo.left, rect_inimigo.right)
                py = random.uniform(rect_inimigo.top, rect_inimigo.bottom)
                vx = random.uniform(-4, 4)
                vy = random.uniform(-4, 4)
                
                particulas_pontos.append({
                    "x": px,
                    "y": py,
                    "vx": vx,
                    "vy": vy,
                    "timer": random.randint(10, 20),
                    "history": [],
                    "speed": random.uniform(0.1, 0.3)
                })

        def atualizar_e_desenhar_particulas_pontos(tela):
            if not (config_graficos.get("particulas_ativas", True) and config_graficos.get("efeitos_visuais", True)):
                particulas_pontos.clear()
                return
            
            qualidade = config_graficos.get("qualidade_grafica", "alta")
            px_centro = pos_x_personagem + largura_personagem // 2
            py_centro = pos_y_personagem + altura_personagem // 2
            
            novas_particulas = []
            for p in particulas_pontos:
                if qualidade == "alta":
                    p["history"].append((p["x"], p["y"]))
                    if len(p["history"]) > 4:
                        p["history"].pop(0)
                
                if p["timer"] > 0:
                    p["x"] += p["vx"]
                    p["y"] += p["vy"]
                    p["vx"] *= 0.92
                    p["vy"] *= 0.92
                    p["timer"] -= 1
                else:
                    dx = px_centro - p["x"]
                    dy = py_centro - p["y"]
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist < 15:
                        continue
                    
                    dx /= dist
                    dy /= dist
                    
                    p["vx"] += dx * p["speed"]
                    p["vy"] += dy * p["speed"]
                    max_speed = 12.0
                    speed = math.sqrt(p["vx"]**2 + p["vy"]**2)
                    if speed > max_speed:
                        p["vx"] = (p["vx"] / speed) * max_speed
                        p["vy"] = (p["vy"] / speed) * max_speed
                        
                    p["x"] += p["vx"]
                    p["y"] += p["vy"]
                    p["speed"] += 0.05
                    
                if qualidade == "alta":
                    for idx, (hx, hy) in enumerate(p["history"]):
                        alpha_factor = (idx + 1) / len(p["history"])
                        r = int(0 * alpha_factor)
                        g = int(191 * alpha_factor)
                        b = int(255 * alpha_factor)
                        size = max(1, int(3 * alpha_factor))
                        pygame.draw.circle(tela, (r, g, b), (int(hx), int(hy)), size)
                
                # Desenhar partícula principal (azul brilhante)
                pygame.draw.circle(tela, (135, 206, 250), (int(p["x"]), int(p["y"])), 3)
                novas_particulas.append(p)
                
            particulas_pontos[:] = novas_particulas

        ###################################################################################################PRINCIPAL#################################################################################################################
        #LOOP PRINCIPAL
        jogo_pausado = False
        running = True
        while running:
            tempo_atual = pygame.time.get_ticks()

            # Registrar snapshot para o sistema de rewind
            if vida > 0:
                snapshot_attrs = {
                    "velocidade_personagem": velocidade_personagem,
                    "intervalo_disparo": intervalo_disparo,
                    "dano_person_hit": dano_person_hit,
                    "chance_critico": chance_critico,
                    "roubo_de_vida": roubo_de_vida,
                    "quantidade_roubo_vida": quantidade_roubo_vida,
                    "vida_petro": vida_petro,
                    "vida_maxima_personagem": vida_maxima,
                    "vida_maxima_petro": vida_maxima_petro,
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
                    "moedas_totais": moedas_totais,
                    "Chance_Sorte": Chance_Sorte,
                    "cartas_compradas": cartas_compradas,
                }
                snapshot_data = {
                    "atributos": snapshot_attrs,
                    "pos_x": pos_x_personagem,
                    "pos_y": pos_y_personagem,
                    "vida_boss": vida_chefe if 'vida_chefe' in locals() or 'vida_chefe' in globals() else (
                                 vida_boss if 'vida_boss' in locals() or 'vida_boss' in globals() else (
                                 vida_boss2 if 'vida_boss2' in locals() or 'vida_boss2' in globals() else (
                                 vida_boss3 if 'vida_boss3' in locals() or 'vida_boss3' in globals() else (
                                 vida_boss4 if 'vida_boss4' in locals() or 'vida_boss4' in globals() else None))))
                }
                Variaveis.registrar_snapshot(snapshot_data, tempo_atual)

            if carregar_atributos_na_fase:
                try:
                    carregar_atributos()
                    if Variaveis.snapshot_para_carregar is not None:
                        snap = Variaveis.snapshot_para_carregar
                        pos_x_personagem = snap.get("pos_x", pos_x_personagem)
                        pos_y_personagem = snap.get("pos_y", pos_y_personagem)
                        vida = snap.get("vida_fracao", 0.20) * vida_maxima
                        pontuacao = 0
                        pontuacao_exib = 0
                        if "vida_boss" in snap and snap["vida_boss"] is not None:
                            if 'vida_chefe' in locals() or 'vida_chefe' in globals():
                                vida_chefe = snap["vida_boss"]
                            elif 'vida_boss' in locals() or 'vida_boss' in globals():
                                vida_boss = snap["vida_boss"]
                            elif 'vida_boss2' in locals() or 'vida_boss2' in globals():
                                vida_boss2 = snap["vida_boss"]
                            elif 'vida_boss3' in locals() or 'vida_boss3' in globals():
                                vida_boss3 = snap["vida_boss"]
                            elif 'vida_boss4' in locals() or 'vida_boss4' in globals():
                                vida_boss4 = snap["vida_boss"]
                        Variaveis.snapshot_para_carregar = None
                except Exception as e:
                    registrar_erro("Fase 3: erro ao carregar atributos; usando padrao", e)
                carregar_atributos_na_fase=False

            if impulsiva_ativa:
                frames_disparo = [pygame.transform.scale(frame, (largura_disparo, altura_disparo)) for frame in frames_disparo_impulso_base]
            else:
                frames_disparo = [pygame.transform.scale(frame, (largura_disparo, altura_disparo)) for frame in frames_disparo_normal_base]


            if impulsiva_ativa and tempo_atual - tempo_inicio_buff_impulsiva > 15000:
                impulsiva_ativa = False
                tipo_buff_impulsiva = None
            elif impulsiva_ativa:
                if tempo_atual - tempo_texto_dano > 2000:
                    tempo_texto_dano = tempo_atual
                    if tipo_buff_impulsiva == "dano":
                        multiplicador_dano = 1.3 + (0.05 * nivel_impulsiva)
                    elif tipo_buff_impulsiva == "velocidade":
                        multiplicador_velocidade = 1.2 + (0.05 * nivel_impulsiva)


            pos_mouse = obter_pos_mouse_jogo()
            botao_mouse = pygame.mouse.get_pressed()
            mouse_x = max(0, min(pos_mouse[0], largura_mapa - cursor_tamanho[0]))
            mouse_y = max(0, min(pos_mouse[1], altura_mapa - cursor_tamanho[1]))
            for event in pygame.event.get():
                Variaveis.atualizar_estado_mouse(event)
                Variaveis.processar_eventos_teleporte(event, cooldown_dash)
                if event.type == pygame.QUIT:
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.SAIR)
                        raise CleanExit()
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
                elif botao_mouse[0] and tempo_atual - tempo_ultimo_disparo >= intervalo_disparo_racional(intervalo_disparo, aurea, racional_dilatacao_fim, tempo_atual):  # Botão esquerdo do mouse
                    pos_mouse = obter_pos_mouse_jogo()
                    px_centro = pos_x_personagem + largura_personagem // 2
                    py_centro = pos_y_personagem + altura_personagem // 2
                    angulo = calcular_angulo_disparo((px_centro, py_centro), pos_mouse)

                    # Crie o disparo com direção baseada no ângulo
                    novo_disparo = {
                        "rect": pygame.Rect(px_centro - largura_disparo // 2, py_centro - altura_disparo // 2, largura_disparo, altura_disparo),
                        "angulo": angulo
                    }
                    disparos.append(novo_disparo)
                    tempo_ultimo_disparo = tempo_atual  # Atualizar o tempo do último disparo
                elif Variaveis.verificar_evento_input(event, "Habilidade Onda") and tempo_atual - tempo_ultimo_uso_habilidade >= cooldown_habilidade:
                    pos_mouse = obter_pos_mouse_jogo()
                    px_centro = pos_x_personagem + largura_personagem // 2
                    py_centro = pos_y_personagem + altura_personagem // 2
                    angulo = calcular_angulo_disparo((px_centro, py_centro), pos_mouse)

                    # Criar uma onda cinética com as novas propriedades
                    nova_onda = {
                        "rect": pygame.Rect(px_centro - largura_onda // 2, py_centro - altura_onda // 2, largura_onda, altura_onda),
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
                
                try:
                    salvar_atributos()
                except Exception as e:
                    registrar_erro("Fase 3: erro ao salvar atributos para pausa", e)
                from Tela_Pause import exibir_tela_pause
                ret_pause = exibir_tela_pause(tela, cartas_compradas, joy)
                if isinstance(ret_pause, dict):
                    tela = ret_pause.get("tela", tela)
                    nova_config_graficos = ret_pause.get("config_graficos")
                    if isinstance(nova_config_graficos, dict):
                        config_graficos.clear()
                        config_graficos.update(nova_config_graficos)
                    ret_pause = ret_pause.get("acao", "continuar")
                if ret_pause == "sair":
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.MENU_PRINCIPAL)
                        raise CleanExit()
                    else:
                        running = False
                        break
                
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

            # --- PARTÍCULAS DE VENENO PINGANDO ---
            Variaveis.atualizar_e_desenhar_particulas_veneno(tela, inimigos_comum, config_graficos)

            for inimigo in inimigos_comum:

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
                        pos_texto = (inimigo["rect"].x + largura_inimigo3 // 2 - texto_dano.get_width() // 2,  inimigo["rect"].y - 20)

                        # Rastreie o tempo de exibição do texto
                        tempo_texto_dano = pygame.time.get_ticks()
                        inimigo["vida"] -= dano
                        disparos.remove(disparo)  # Remover o disparo após colisão

                        if Poison_Active:
                            aplicar_veneno(inimigo, tempo_atual, cartas_compradas.get("Poison", 0))


                        if quantidade_roubo_vida > 0:
                            vida += (vida_maxima-vida)*quantidade_roubo_vida
                        if Ultimo_Estalo and inimigo["vida"] <= Executa_inimigo * inimigo["vida_maxima"]:
                            if inimigo in inimigos_comum:
                                gerar_fragmentos_morte(inimigo, 3)
                                inimigos_comum.remove(inimigo)
                            posicao_inimigo = inimigo["rect"].center
                            soltar_moeda(posicao_inimigo)
                            Variaveis.tentar_soltar_carta(posicao_inimigo, tempo_atual, Chance_Sorte, inimigos_eliminados)
                            inimigos_eliminados += 1

                            # Multiplicador de Execução Superior (20%)
                            mult_ex = 1.0 + (nivel_ameaca * 0.20)

                            vida_inimigo_maxima += 1.0 * mult_ex
                            Resistencia_petro += 0.03 * mult_ex
                            dano_inimigo_perto += 0.1 * mult_ex
                            dano_person_hit += 0.18 * mult_ex
                            vida_maxima_petro += 1.5 * mult_ex
                            dano_petro += 0.015 * mult_ex
                            dano_inimigo_longe += 0.03 * mult_ex

                            ganho = int(180 * (1 + math.log10(inimigos_eliminados + 1)))
                            pontuacao += ganho

                            if Mercenaria_Active:
                                eliminacoes_consecutivas += 1
                                # Bônus mercenário fixo para evitar inflação infinita
                                pontuacao_exib += ganho + bonus_pontuacao
                                if eliminacoes_consecutivas % 5 == 0:
                                    bonus_pontuacao = min(500, bonus_pontuacao + Valor_Bonus) 
                            else:
                                pontuacao_exib += ganho


                            if not Boss_vivo3:
                                vida_boss3 += 25 + nivel_ameaca * 10
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += 30 + nivel_ameaca * 12
                                vida_maxima_boss4 = vida_boss4

                        elif inimigo["vida"] <= 0:
                            posicao_inimigo = inimigo["rect"].center
                            soltar_moeda(posicao_inimigo)
                            Variaveis.tentar_soltar_carta(posicao_inimigo, tempo_atual, Chance_Sorte, inimigos_eliminados)
                            gerar_fragmentos_morte(inimigo, 3)
                            inimigos_comum.remove(inimigo)
                            inimigos_eliminados += 1

                            # --- ESCALONAMENTO DE ELITE (FASE 3 - 20 MINUTOS) ---
                            # O multiplicador base da Fase 3 é mais alto (0.15)
                            mult = 1.0 + (nivel_ameaca * 0.15)

                            vida_inimigo_maxima += 0.8 * mult
                            Resistencia_petro += 0.02 * mult
                            dano_inimigo_perto += 0.08 * mult
                            dano_person_hit += 0.12 * mult
                            vida_maxima_petro += 1.2 * mult
                            dano_petro += 0.01 * mult
                            dano_inimigo_longe += 0.025 * mult

                            # Pontuação Logarítmica ajustada para a economia de 50 cartas
                            ganho = int(150 * (1 + math.log10(inimigos_eliminados + 1)))
                            pontuacao += ganho

                            if Mercenaria_Active:
                                eliminacoes_consecutivas += 1
                                pontuacao_exib += ganho + bonus_pontuacao
                                if eliminacoes_consecutivas % 5 == 0:
                                    bonus_pontuacao = min(800, bonus_pontuacao + Valor_Bonus)
                            else:
                                pontuacao_exib += ganho

                            # Gestão de Bosses (Fase 3 e 4)
                            if not Boss_vivo3:
                                incremento_v = 20 * mult
                                vida_boss3 += incremento_v
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += incremento_v * 1.5
                                vida_maxima_boss4 = vida_boss4

                            break
                if "veneno" in inimigo:
                    # Verifique se é hora de aplicar dano
                    if tempo_atual - inimigo["veneno"]["ultimo_tick"] >= INTERVALO_TICK_VENENO:
                        inimigo["vida"] -= inimigo["veneno"]["dano_por_tick"]
                        inimigo["veneno"]["ultimo_tick"] = tempo_atual  # Atualiza o tempo do último tick
                        inimigo["veneno"]["tempo_texto_dano"] = tempo_atual  # Atualiza o tempo de exibição do texto

                    # Exibe o texto apenas por 1.5 segundos após o dano
                    if tempo_atual - inimigo["veneno"]["tempo_texto_dano"] <= 1500:
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

            # Adicionar um novo disparo quando a tecla de espaço é pressionada


            tempo_passado += relogio.get_rawtime()
            relogio.tick()

             # Adicionar inimigos a cada 10 segundos
            tempo_atual = pygame.time.get_ticks()
            if tempo_atual - tempo_ultimo_inimigo >= 1000 and len(inimigos_comum) < max_inimigos2 :
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

                    mensagem_buff = "+ Buff: Dano ↑" if tipo_buff_impulsiva == "dano" else "+ Buff: Velocidade ↑"
                    efeitos_texto.append({
                        "texto": mensagem_buff,
                        "x": pos_x_personagem,
                        "y": pos_y_personagem - 20,
                        "tempo_inicio": pygame.time.get_ticks(),
                        "cor": (255, 100, 100) if tipo_buff_impulsiva == "dano" else (100, 100, 255)
                    })



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
            if not personagem_doente:
                frame_para_desenhar = frames_animacao[direcao_atual][frame_atual % len(frames_animacao[direcao_atual])]
                if angulo_inclinacao_personagem != 0:
                    # Rotaciona o frame pelo centro para manter o eixo
                    frame_rotacionado = pygame.transform.rotate(frame_para_desenhar, angulo_inclinacao_personagem)
                    novo_rect = frame_rotacionado.get_rect(center=(pos_x_personagem + largura_personagem//2, pos_y_personagem + altura_personagem//2))
                    tela.blit(frame_rotacionado, novo_rect.topleft)
                else:
                    tela.blit(frame_para_desenhar, (pos_x_personagem, pos_y_personagem))
            else:
                tela.blit(imagem_personagem_doente, (pos_x_personagem, pos_y_personagem))

            # Desenhar zona de teleporte (se estiver mirando no modo mouse)
            Variaveis.desenhar_zona_teleporte(tela, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, distancia_dash)
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
            if trembo and tempo_atual - tempo_ultima_regeneracao >= Tempo_cura and vida < vida_maxima:
                cura_trembo = vida_maxima * porcentagem_cura
                vida = min(vida_maxima, vida + cura_trembo)
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
                        pos_x_petro += 1.5 * direcao_petro[0] * dt
                        pos_y_petro += 1.5 * direcao_petro[1] * dt

                    # Calcula a distância entre "Petro" e o inimigo mais próximo
                    distancia_petro_inimigo = math.sqrt((pos_x_petro - pos_x_inimigo_mais_proximo) ** 2 + (pos_y_petro - pos_y_inimigo_mais_proximo) ** 2)

                    # Verifica se "Petro" está próximo o suficiente para aplicar dano
                    if distancia_petro_inimigo <= 50:
                        tempo_atual_petro = pygame.time.get_ticks()
                        if tempo_atual_petro - tempo_anterior_petro >= intervalo_dano_petro:
                            # Resistência mitigando o impacto
                            dano_real = max(0, dano_inimigo_perto - Resistencia_petro)
                            vida_petro -= int(dano_real)

                            # Ataque Simbiótico: 1% do poder total do jogador + bônus da Petro
                            inimigo_mais_proximo["vida"] -= int(dano_person_hit * 0.01) + dano_petro
                            tempo_anterior_petro = tempo_atual_petro

                            if inimigo_mais_proximo["vida"] <= 0:
                                # Evolução por abate direto da Petro (Balanceado para 20 min)
                                vida_inimigo_maxima += 0.7
                                Resistencia_petro += 0.04 # Crescimento de armadura robusto
                                vida_maxima_petro += 1.5
                                dano_person_hit += 0.1
                                dano_petro += 0.012
                                dano_inimigo_longe += 0.02
                                inimigos_eliminados += 1

                                pontos_p = int(120 * (1 + math.log10(inimigos_eliminados + 1)))
                                pontuacao += pontos_p
                                pontuacao_exib += pontos_p

                                if inimigo_mais_proximo in inimigos_comum:
                                    gerar_fragmentos_morte(inimigo_mais_proximo, 3)
                                    Variaveis.tentar_soltar_carta(inimigo_mais_proximo["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                                    inimigos_comum.remove(inimigo_mais_proximo)

                                if not Boss_vivo3:
                                    # O dano do Boss 4 escala discretamente aqui para o desafio final
                                    mult_ex = 1.0 + (nivel_ameaca * 0.20)
                                    vida_boss4 += 5 * mult

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



                if Boss_vivo3:
                    # Define a direção de Petro em relação ao boss
                    dx = pos_x_chefe3 - pos_x_petro
                    dy = pos_y_chefe3 - pos_y_petro

                    # Normaliza a direção para manter a mesma velocidade em todas as direções
                    magnitude = math.sqrt(dx ** 2 + dy ** 2)
                    if magnitude != 0:
                        direcao_x = dx / magnitude
                        direcao_y = dy / magnitude
                    else:
                        direcao_x = 0
                        direcao_y = 0

                    # Move Petro na direção do boss
                    pos_x_petro += 1 * direcao_x * dt
                    pos_y_petro += 1 * direcao_y * dt

                    # Verifica se Petro está próximo o suficiente para aplicar dano ao boss
                    distancia_petro_boss = math.sqrt((pos_x_petro - pos_x_chefe3) ** 2 + (pos_y_petro - pos_y_chefe3) ** 2)
                    if distancia_petro_boss <= 50:
                        # Verifica se passou tempo suficiente desde o último dano
                        tempo_atual_petro = pygame.time.get_ticks()
                        if tempo_atual_petro - tempo_anterior_petro >= intervalo_dano_petro:
                            # Aplica dano ao "boss"
                            vida_petro -= int(dano_inimigo_perto)
                            vida_petro += int(vida_maxima_petro - vida_petro) * quantidade_roubo_vida
                            vida_boss3-= int(dano_person_hit*0.25)+300
                            # Aqui você pode adicionar outras ações relacionadas ao dano ao "boss"
                            tempo_anterior_petro = tempo_atual_petro


                if comando_direção_petro:
                    direcao_atual_petro="left_petro"
                    comando_direção_petro=False


                desenhar_barra_de_vida_petro(tela, vida_petro, pos_x_petro, pos_y_petro - 20,vida_maxima_petro)  
                tela.blit(petro_nivel[direcao_atual_petro][frame_atual % len(petro_nivel[direcao_atual_petro])], (pos_x_petro, pos_y_petro)) 





            # Desenhar os disparos normais
            novos_disparos = []
            novos_disparos = []
            # Desenhar os disparos normais
            novos_disparos = []
            for disparo in disparos:
                if "pos_x" not in disparo:
                    disparo["pos_x"] = float(disparo["rect"].x)
                if "pos_y" not in disparo:
                    disparo["pos_y"] = float(disparo["rect"].y)
                disparo["pos_x"] += velocidade_disparo * math.cos(disparo["angulo"]) * dt
                disparo["pos_y"] += velocidade_disparo * math.sin(disparo["angulo"]) * dt
                disparo["rect"].x = int(disparo["pos_x"])
                disparo["rect"].y = int(disparo["pos_y"])

                # Verificar se o disparo está dentro do mapa
                if 0 <= disparo["rect"].x < largura_mapa and 0 <= disparo["rect"].y < altura_mapa:
                    novos_disparos.append(disparo)

            disparos = novos_disparos

            # Renderizar os disparos
            for disparo in disparos:
                tela.blit(frames_disparo[frame_atual_disparo], disparo["rect"].topleft)



            boss_info = {
                "vivo": Boss_vivo3,
                "rect": pygame.Rect(pos_x_chefe3, pos_y_chefe3, chefe_largura3, chefe_altura3) if Boss_vivo3 else None,
                "atingido_por_onda": globals().get("boss_atingido_por_onda", {}).get("boss", 0),
                "hit_flag": False
            }
            inimigos_mortos_neste_frame = processar_habilidade_onda(
                ondas, correntes_eletricas, inimigos_comum, boss_info, tela, dt, tempo_atual, largura_mapa, altura_mapa, velocidade_onda
            )
            if boss_info.get("hit_flag"):
                vida_boss3 -= dano_person_hit * 3
                if "boss_atingido_por_onda" not in globals():
                    globals()["boss_atingido_por_onda"] = {}
                globals()["boss_atingido_por_onda"]["boss"] = boss_info["atingido_por_onda"]
                
                if vida_boss3 <= 0:
                    rect_boss = pygame.Rect(pos_x_chefe3, pos_y_chefe3, 64, 64)
                    rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                    if tempo_atual - tempo_ultimo_frame_boss >= 300:
                        if boss_frame_peca == boss_frame_peca1:
                            boss_frame_peca = boss_frame_peca2
                        else:
                            boss_frame_peca = boss_frame_peca1
                        tempo_ultimo_frame_boss = tempo_atual
                        tela.blit(boss_frame_peca, (pos_x_chefe3, pos_y_chefe3))

                    if rect_boss.colliderect(rect_personagem):
                        if toque == 0:
                            salvar_atributos()
                            Musica_tema_Boss3.stop()
                            pausar_cronometro()
                            tela_transicao_dimensional(tela, 4)
                            if game_manager:
                                from game_manager import EstadoJogo
                                game_manager.mudar_estado(EstadoJogo.JOGO_FASE_4)
                                raise CleanExit()
                            else:
                                import GAME4
                                GAME4.executar_jogo()
                                raise CleanExit()
                            toque += 1

            # Atualizar e desenhar correntes elétricas
            inimigos_mortos_correntes = atualizar_e_desenhar_correntes(tela, correntes_eletricas, inimigos_comum, tempo_atual, dano_person_hit)
            
            inimigos_mortos = inimigos_mortos_neste_frame + inimigos_mortos_correntes
            for morto in inimigos_mortos:
                if morto in inimigos_comum:
                    gerar_fragmentos_morte(morto, 3)
                    Variaveis.tentar_soltar_carta(morto["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                    inimigos_comum.remove(morto)
                    nivel_ameaca = min(inimigos_eliminados // 10, 100)
                    vida_inimigo_maxima += 1.5 + nivel_ameaca * 1.2
                    Resistencia_petro += 0.4 + nivel_ameaca * 0.3
                    dano_inimigo_perto += 0.25 + nivel_ameaca * 0.15
                    dano_person_hit += 3 + nivel_ameaca * 1.2
                    vida_maxima_petro += 10 + nivel_ameaca * 5
                    dano_petro += 0.02 + nivel_ameaca * 0.01
                    dano_inimigo_longe += 2 + nivel_ameaca * 0.8
                    
                    inimigos_eliminados += 1
                    
                    ganho = int(75 + math.log2(inimigos_eliminados + 1) * 5)
                    pontuacao += ganho
                    pontuacao_exib += ganho
                    
                    if not Boss_vivo3:
                        vida_boss3 += 25 + nivel_ameaca * 10
                        vida_maxima_boss3 = vida_boss3
                        vida_boss4 += 30 + nivel_ameaca * 12
                        vida_maxima_boss4 = vida_boss4
            # loop principal, onde o inimigo é desenhado:
            for inimigo in inimigos_comum:
                dx = pos_x_personagem - inimigo["rect"].x
                dy = pos_y_personagem - inimigo["rect"].y
                dist = max(40, abs(dx) + abs(dy))
                
                if "pos_x" not in inimigo:
                    inimigo["pos_x"] = float(inimigo["rect"].x)
                if "pos_y" not in inimigo:
                    inimigo["pos_y"] = float(inimigo["rect"].y)
                    
                fator_tempo_mundo = fator_mundo_racional(aurea, racional_dilatacao_fim, tempo_atual)
                inimigo["pos_x"] += (dx / dist) * 1.70 * fator_tempo_mundo
                inimigo["pos_y"] += (dy / dist) * 1.50 * fator_tempo_mundo
                inimigo["rect"].x = int(inimigo["pos_x"])
                inimigo["rect"].y = int(inimigo["pos_y"])

            # Resolve colisões e separações entre inimigos e jogador
            pos_x_personagem, pos_y_personagem = Variaveis.resolver_colisao_player_com_inimigos(
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, inimigos_comum
            )
            pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem))
            pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem))
            Variaveis.resolver_colisoes_e_separacao(inimigos_comum, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)

            for inimigo in inimigos_comum:
                dx = pos_x_personagem - inimigo["rect"].x
                dy = pos_y_personagem - inimigo["rect"].y

                # Atualize os frames do inimigo com base na direção
                if dx > 0:  # Mova para a direita
                    inimigo["image"] = frames_inimigo_direita3[frame_atual % len(frames_inimigo_direita3)]
                else:  # Mova para a esquerda
                    inimigo["image"] = frames_inimigo_esquerda3[frame_atual % len(frames_inimigo_esquerda3)]

                # Desenhar sombra do inimigo
                desenhar_sombra(tela, inimigo["rect"].x, inimigo["rect"].y, largura_inimigo3, altura_inimigo3)
                tela.blit(inimigo["image"], inimigo["rect"])
                desenhar_barra_de_vida(tela, inimigo["rect"].x, inimigo["rect"].y - 10, largura_inimigo3, 5, inimigo["vida"], inimigo["vida_maxima"], inimigo.get("eletrocutado", False), Executa_inimigo if Ultimo_Estalo else None)

                tempo_atual = pygame.time.get_ticks()
                if tempo_atual - tempo_ultimo_disparo_inimigo >= intervalo_disparo_inimigo and random.random() <= 0.01:  #frequencia do disparo do sinimigos
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
                    Dano_pos_resistencia_person = int(((vida_maxima * 0.25)+dano_inimigo_perto) - Resistencia)
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


            # Verifica colisão entre disparos dos inimigos e personagem
            novos_disparos_inimigos = []
            for disparo_inimigo in disparos_inimigos:
                pos_x_disparo_inimigo, pos_y_disparo_inimigo = disparo_inimigo["rect"].x, disparo_inimigo["rect"].y
                tela.blit(frames_disparo3[frame_atual_disparo], (pos_x_disparo_inimigo, pos_y_disparo_inimigo))

                # Atualize a posição do disparo do inimigo
                disparo_inimigo["rect"].x += disparo_inimigo["velocidade"][0]
                disparo_inimigo["rect"].y += disparo_inimigo["velocidade"][1]



                if (
                    pos_x_personagem < pos_x_disparo_inimigo < pos_x_personagem + largura_personagem and
                    pos_y_personagem < pos_y_disparo_inimigo < pos_y_personagem + altura_personagem
                ):
                    # O disparo do inimigo atingiu o personagem

                    if not personagem_doente:
                        Dano_pos_resistencia_person_longe=int((vida_maxima*0.35+dano_inimigo_longe)-Resistencia)
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
                        # esta parte para iniciar o piscar da barra de vida
                        tempo_ultimo_atingido = pygame.time.get_ticks()


                        personagem_doente = True  # O personagem está imóvel após ser atingido
                        disparos_inimigos.remove(disparo_inimigo)
                    continue
                    # Lógica para controle da imobilização
                tempo_atual = pygame.time.get_ticks()
                if personagem_doente and tempo_atual - tempo_ultimo_atingido >= tempo_doente:
                    personagem_doente = False  # A personagem volta a poder se mexer

                # Adicione o disparo à lista se não atingir o final do mapa
                if (
                    0 <= pos_x_disparo_inimigo < largura_mapa and
                    0 <= pos_y_disparo_inimigo < altura_mapa
                ):
                    novos_disparos_inimigos.append(disparo_inimigo)

            # Atualiza a lista de disparos dos inimigos
            disparos_inimigos = novos_disparos_inimigos



            if vida <= 0:
                if trembo:
                    # Capturar posições antigas antes do teleporte
                    old_cx = pos_x_personagem + largura_personagem // 2
                    old_cy = pos_y_personagem + altura_personagem // 2
                    
                    if 'trembo_pos_x_atual' in locals() or 'trembo_pos_x_atual' in globals():
                         trembo_x = trembo_pos_x_atual
                         trembo_y = trembo_pos_y_atual
                    else:
                         trembo_x = pos_x_personagem
                         trembo_y = pos_y_personagem
                    
                    # Gerar animações de explosão branca e fragmentação do Trembo
                    gerar_explosao_branca(old_cx, old_cy)
                    gerar_fragmentos_trembo(trembo_x, trembo_y, largura_trembo, altura_trembo)
                    
                    # Ondas de choque da explosão branca
                    ondas_choque.append({
                        "cx": old_cx,
                        "cy": old_cy,
                        "raio_atual": 10.0,
                        "raio_max": 200.0,
                        "velocidade": 12.0,
                        "cor": (255, 255, 255)
                    })
                    ondas_choque.append({
                        "cx": old_cx,
                        "cy": old_cy,
                        "raio_atual": 20.0,
                        "raio_max": 150.0,
                        "velocidade": 8.0,
                        "cor": (240, 240, 250)
                    })
                    
                    # Tocar som de teleporte
                    Som_portal.play()
                    
                    # Executar a segunda chance e teleporte
                    vida = vida_maxima  # Recupera a vida total
                    trembo = False  # Consome o "trembo"
                    imune_tempo_restante = 10000
                    teleportado = True  # Ativa o teleporte aleatório
                    porcentagem_cura = max(0.02, porcentagem_cura * 0.5)
                    Tempo_cura = min(2500, int(Tempo_cura * 1.5))
                    pos_x_personagem, pos_y_personagem = gerar_posicao_aleatoria(largura_mapa, altura_mapa, largura_personagem, altura_personagem)
                else:
                    from utils import executar_animacao_morte_personagem
                    frame_para_desenhar_morte = frames_animacao[direcao_atual][frame_atual % len(frames_animacao[direcao_atual])]
                    executar_animacao_morte_personagem(
                        tela=tela,
                        pos_x_personagem=pos_x_personagem,
                        pos_y_personagem=pos_y_personagem,
                        largura_personagem=largura_personagem,
                        altura_personagem=altura_personagem,
                        frame_para_desenhar=frame_para_desenhar_morte,
                        angulo_inclinacao_personagem=angulo_inclinacao_personagem,
                        desenhar_hud_callback=lambda s: desenhar_hud_fase(
                        s, 0, vida_maxima, pontuacao_exib, custo_carta_atual,
                        pontuacao_magia, cooldowns, dispositivo_ativo,
                        eliminacoes_consecutivas, bonus_pontuacao, aurea,
                        escudo_devota_ativo, pos_x_personagem, pos_y_personagem,
                        largura_personagem, altura_personagem
                    ),
                        exibir_cronometro_callback=lambda s: exibir_cronometro(s),
                        cursor_imagem=cursor_imagem,
                        mouse_pos=(mouse_x, mouse_y),
                        config_graficos=config_graficos,
                        som_morte=locals().get('Dano_person', globals().get('Dano_person', None))
                    )

                    Musica_tema_fases.stop()
                    Som_tema_fases.stop()
                    if moedas_totais > 0:
                        moedas_totais = tela_upgrade_aureas(tela, fonte, moedas_totais)
                    pygame.event.clear()

                    limpar_salvamento()
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.GAME_OVER)
                        raise CleanExit()
                    else:
                        pygame.quit()
                        subprocess.run([sys.executable, "Game_Over.py"])
                        sys.exit()

            # Adicione esta verificação para controlar o piscar da barra de vida
            if piscando_vida:
                if False: # Desativado para o HUD widescreen
                    if tempo_atual % 500 < 250:  # Altere o valor 500 e 250 conforme necessário
                        # Desenha a barra de vida piscando em vermelho
                        pygame.draw.rect(tela, (255, 0, 0), (posicao_barra_vida[0], posicao_barra_vida[1], largura_barra_vida, altura_barra_vida))
                    else:
                        # Desenha a barra de vida normalmente
                        pygame.draw.rect(tela, verde, (posicao_barra_vida[0], posicao_barra_vida[1], (vida / vida_maxima) * largura_barra_vida, altura_barra_vida))

                # verificação para parar o piscar depois de um tempo
                if tempo_atual - tempo_ultimo_hit_inimigo >= intervalo_hit_inimigo:
                    piscando_vida = False

            tempo_atual = pygame.time.get_ticks()
            if Ultimo_Estalo and vida_boss3 <= Executa_inimigo * vida_maxima_boss3:
                Boss_vivo3=False
            elif vida_boss3 <=0:
                Boss_vivo3=False


            if Boss_vivo3:

                if (keys[pygame.K_r]) or r_press:
                    if not r_press:
                        tempo_boss_entrada_fim = tempo_atual + 2500
                    r_press=True
                    Musica_tema_fases.stop()
                    max_inimigos2=9
                    if musica_boss3 == 1:
                        # Defina o volume da música (opcional)
                        Musica_tema_Boss3.play(loops=-1)
                        musica_boss3+=1

                    spawn_inimigo=False
                    personagem_doente = False

                    pygame.draw.rect(tela, vermelho, (pos_x_barra_boss3, pos_y_barra_boss3, largura_barra_boss3, altura_barra_boss3))
                    pygame.draw.rect(tela, (224,190,1), (pos_x_barra_boss3, pos_y_barra_boss3, largura_barra_boss3, (vida_boss3 /  vida_maxima_boss3) * altura_barra_boss3))
                    pygame.draw.rect(tela, (255, 255, 255), (pos_x_barra_boss3, pos_y_barra_boss3, largura_barra_boss3, altura_barra_boss3), 2)
                    if not Boss_andando:

                        # Verificar se é hora de alternar os frames do boss
                        tempo_atual = pygame.time.get_ticks()
                        if tempo_atual - tempo_ultimo_frame_boss >= 500:
                            if boss_frame_atual == boss_frame1:
                                boss_frame_atual = boss_frame2
                            else:
                                boss_frame_atual = boss_frame1
                            tempo_ultimo_frame_boss = tempo_atual
                        tela.blit(boss_frame_atual, (pos_x_chefe3, pos_y_chefe3))




                    for disparo in disparos:
                        pos_x_disparo=disparo["rect"].x 
                        pos_y_disparo=disparo["rect"].y 
                        rect_disparo = pygame.Rect(pos_x_disparo, pos_y_disparo, largura_disparo, altura_disparo)
                        rect_boss = pygame.Rect(pos_x_chefe3, pos_y_chefe3, chefe_largura3, chefe_altura3)

                        if rect_disparo.colliderect(rect_boss):
                            if vida_boss3 > 0:  # Verifica se o chefe está vivo antes de aplicar dano
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
                                global duracao_veneno_boss
                                dano_por_tick_veneno_boss = vida_maxima_boss3 * Dano_Veneno_Acumulado
                                duracao_veneno_boss = 8000 + cartas_compradas.get("Poison", 0) * 100
                                tempo_inicio_veneno_boss = pygame.time.get_ticks()
                                ultimo_tick_veneno_boss = pygame.time.get_ticks()

                            # Renderizar texto do dano
                            texto_dano = fonte_dano.render("-" + str(int(dano)), True, cor)
                            pos_texto = (pos_x_chefe3 + chefe_largura3 // 2 - texto_dano.get_width() // 2, pos_y_chefe3 - 20)
                            tempo_texto_dano = pygame.time.get_ticks()
                            vida_boss3 -= dano
                            disparos.remove(disparo)

                            # Roubo de vida
                            if quantidade_roubo_vida > 0:
                                vida += (vida_maxima - vida) * quantidade_roubo_vida

                    # Aplicar dano de veneno no Boss se ele estiver envenenado
                    if boss_envenenado:
                        tempo_atual = pygame.time.get_ticks()

                        # Aplicar dano a cada 500 ms
                        if tempo_atual - ultimo_tick_veneno_boss >= INTERVALO_TICK_VENENO:
                            vida_boss3 -= dano_por_tick_veneno_boss
                            ultimo_tick_veneno_boss = tempo_atual

                        # Exibir texto do dano de veneno (1.5 segundos)
                        if tempo_atual - ultimo_tick_veneno_boss <= 1500:
                            dano_veneno_texto = "-" + str(int(dano_por_tick_veneno_boss))
                            texto_dano_veneno = fonte_veneno.render(dano_veneno_texto, True, (0, 255, 0))
                            texto_dano_veneno_borda = fonte_veneno.render(dano_veneno_texto, True, (0, 0, 0))
                            pos_texto = (pos_x_chefe3 + chefe_largura3 // 2 - texto_dano_veneno.get_width() // 2, pos_y_chefe3 - 30)
                            tela.blit(texto_dano_veneno_borda, (pos_texto[0] - 1, pos_texto[1]))
                            tela.blit(texto_dano_veneno_borda, (pos_texto[0] + 1, pos_texto[1]))
                            tela.blit(texto_dano_veneno_borda, (pos_texto[0], pos_texto[1] - 1))
                            tela.blit(texto_dano_veneno_borda, (pos_texto[0], pos_texto[1] + 1))
                            tela.blit(texto_dano_veneno, pos_texto)

                        # Desativar o veneno após o tempo de duração
                        if tempo_atual - tempo_inicio_veneno_boss >= duracao_veneno_boss:
                            boss_envenenado = False









                    tempo_atual = pygame.time.get_ticks()
                    if tempo_atual - tempo_ultimo_grupo_disparo_boss3 >= tempo_espera_grupo_disparo_boss3 and not queijo_spawn:  # Verifique se passou 1 segundo
                        # Reinicie o contador de disparos
                        contador_disparos_boss3 = 0
                        disparos_boss3.clear()  # Limpe a lista de disparos anteriores

                    # Gere um grupo de 4 disparos
                        for _ in range(4):
                            # Gere uma posição aleatória no canto direito da tela
                            pos_y_disparo_boss3 = random.randint(0, altura_tela - altura_disparo)
                            pos_x_disparo_boss3 = largura_tela  # Inicie o disparo no canto direito da tela
                            disparos_boss3.append((pos_x_disparo_boss3, pos_y_disparo_boss3, 'left'))  # 'left' indica que o disparo vai para a esquerda

                        # Atualize o tempo do último grupo de disparos do boss
                        tempo_ultimo_grupo_disparo_boss3 = tempo_atual  # Atualize o tempo do último grupo de disparos do boss

                    # Atualize a posição dos disparos do boss3 antes de desenhá-los
                    novos_disparos_boss3 = []
                    for disparo in disparos_boss3:
                        pos_x_disparo, pos_y_disparo, direcao_disparo = disparo

                        # Atualize a posição do disparo
                        if direcao_disparo == 'right':
                            pos_x_disparo += 3
                        elif direcao_disparo == 'left':
                            pos_x_disparo -= 3

                        # Adicione o disparo à lista se não atingir o final do mapa
                        if 0 <= pos_x_disparo < largura_mapa:
                            novos_disparos_boss3.append((pos_x_disparo, pos_y_disparo, direcao_disparo))

                        # Limpe a lista de disparos anteriores e atualize para os novos disparos
                    disparos_boss3 = novos_disparos_boss3

                    # Desenhe os disparos atualizados na tela
                    for disparo in disparos_boss3:
                        pos_x_disparo, pos_y_disparo, _ = disparo
                        tela.blit(sprite_disparo_boss3, (pos_x_disparo, pos_y_disparo))


                    for disparo in disparos_boss3:
                        pos_x_disparo, pos_y_disparo, _ = disparo
                        rect_disparo_boss = pygame.Rect(pos_x_disparo, pos_y_disparo, largura_disparo, altura_disparo)
                        rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)

                        if rect_disparo_boss.colliderect(rect_personagem):
                            Frascos.play()
                            vida -= int(vida_maxima*0.25)+450
                            disparos_boss3.remove(disparo)  # Remova o disparo após colisão


            #PRIMEIRA GERAÇÂO QUEIJO MESTRE
                if vida_boss3 <= 0.9 * vida_maxima_boss3 and queijo_geracao==1:
                    if  not queijo_spawn:

                        pos_x_queijo = random.randint(area_x_min, area_x_max)
                        pos_y_queijo = random.randint(area_y_min, area_y_max)

                    queijo_spawn = True
                    tela.blit(sprite_queijo, (pos_x_queijo, pos_y_queijo))


                    if queijo_spawn:
                        # Calcule o vetor de direção do chefe para o queijo
                        vetor_direcao = (pos_x_queijo - pos_x_chefe3, pos_y_queijo - pos_y_chefe3)
                        # Normalize o vetor de direção para manter uma velocidade constante
                        comprimento_vetor = max(1, math.sqrt(vetor_direcao[0] ** 2 + vetor_direcao[1] ** 2))
                        vetor_direcao_normalizado = (vetor_direcao[0] / comprimento_vetor, vetor_direcao[1] / comprimento_vetor)
                        # Defina a velocidade do chefe
                        velocidade_chefe = 0.8 * dt
                        #   Atualize a posição do chefe em direção ao queijo
                        pos_x_chefe3 += vetor_direcao_normalizado[0] * velocidade_chefe
                        pos_y_chefe3 += vetor_direcao_normalizado[1] * velocidade_chefe
                        # Verifique se o boss chegou ao queijo
                        distancia_para_queijo = math.sqrt((pos_x_queijo - pos_x_chefe3) ** 2 + (pos_y_queijo - pos_y_chefe3) ** 2)
                        # Alternar entre os frames da animação de locomoção do inimigo
                        tempo_atual = pygame.time.get_ticks()
                        if tempo_atual - tempo_ultimo_frame_boss >= 300:

                            if boss_frame_andando == boss_frame_andando1:
                                boss_frame_andando= boss_frame_andando2
                            else:
                                boss_frame_andando = boss_frame_andando1
                            tempo_ultimo_frame_boss = tempo_atual
                        tela.blit(boss_frame_andando, (pos_x_chefe3, pos_y_chefe3))

                        # Defina uma distância de tolerância para considerar que o chefe alcançou o queijo
                        distancia_tolerancia = 10
                        if distancia_para_queijo < distancia_tolerancia:
                            # O chefe chegou ao queijo, volte para a posição inicial
                            pos_x_chefe3 = largura_tela / 1.3
                            pos_y_chefe3 = altura_tela / 3
                            vida_boss3 += int(vida_maxima_boss3-vida_boss3)*0.3
                            if vida_boss3 > vida_maxima_boss3:
                                vida_maxima_boss3=vida_boss3
                            # Resetar a variável que indica se o queijo está presente
                            queijo_spawn = False

                        for disparo in disparos:
                            # Verifique a colisão entre o disparo e o queijo
                            rect_disparo = pygame.Rect(pos_x_disparo, pos_y_disparo, largura_disparo, altura_disparo)
                            rect_queijo_hitbox = pygame.Rect(pos_x_queijo - 10, pos_y_queijo - 10, largura_hitbox_queijo, altura_hitbox_queijo)
                            if rect_disparo.colliderect(rect_queijo_hitbox):
                                # Reduza a vida do queijo com base no dano do disparo
                                vida_queijo -= 5
                                # Remova o disparo
                                disparos.remove(disparo)
                                # Verifique se a vida do queijo chegou a zero
                                if vida_queijo <= 5:
                                    queijo_geracao+=1
                                    queijo_spawn=False
                                    pos_x_chefe3 = largura_tela / 1.3
                                    pos_y_chefe3 = altura_tela / 3
                                    vida_queijo=50

            #SEGUNDA GERAÇÂO QUEIJO MESTRE
                if vida_boss3 <= 0.6 * vida_maxima_boss3 and queijo_geracao==2:
                    if not queijo_spawn:

                        pos_x_queijo = random.randint(area_x_min, area_x_max)
                        pos_y_queijo = random.randint(area_y_min, area_y_max)
                    queijo_spawn = True
                    tela.blit(sprite_queijo, (pos_x_queijo, pos_y_queijo))


                    if queijo_spawn:
                        # Calcule o vetor de direção do chefe para o queijo
                        vetor_direcao = (pos_x_queijo - pos_x_chefe3, pos_y_queijo - pos_y_chefe3)
                        # Normalize o vetor de direção para manter uma velocidade constante
                        comprimento_vetor = max(1, math.sqrt(vetor_direcao[0] ** 2 + vetor_direcao[1] ** 2))
                        vetor_direcao_normalizado = (vetor_direcao[0] / comprimento_vetor, vetor_direcao[1] / comprimento_vetor)
                        # Defina a velocidade do chefe
                        velocidade_chefe = 1 * dt
                        #   Atualize a posição do chefe em direção ao queijo
                        pos_x_chefe3 += vetor_direcao_normalizado[0] * velocidade_chefe
                        pos_y_chefe3 += vetor_direcao_normalizado[1] * velocidade_chefe
                        # Verifique se o boss chegou ao queijo
                        distancia_para_queijo = math.sqrt((pos_x_queijo - pos_x_chefe3) ** 2 + (pos_y_queijo - pos_y_chefe3) ** 2)
                        # Alternar entre os frames da animação de locomoção do inimigo
                        tempo_atual = pygame.time.get_ticks()
                        if tempo_atual - tempo_ultimo_frame_boss >= 300:

                            if boss_frame_andando == boss_frame_andando1:
                                boss_frame_andando= boss_frame_andando2
                            else:
                                boss_frame_andando = boss_frame_andando1
                            tempo_ultimo_frame_boss = tempo_atual
                        tela.blit(boss_frame_andando, (pos_x_chefe3, pos_y_chefe3))

                        # Defina uma distância de tolerância para considerar que o chefe alcançou o queijo
                        distancia_tolerancia = 10
                        if distancia_para_queijo < distancia_tolerancia:
                            # O chefe chegou ao queijo, volte para a posição inicial
                            pos_x_chefe3 = largura_tela / 1.3
                            pos_y_chefe3 = altura_tela / 3
                            vida_boss3 += int(vida_maxima_boss3-vida_boss3)*0.5
                            if vida_boss3 > vida_maxima_boss3:
                                vida_maxima_boss3=vida_boss3
                            # Resetar a variável que indica se o queijo está presente
                            queijo_spawn = False

                        for disparo in disparos:
                            # Verifique a colisão entre o disparo e o queijo
                            rect_disparo = pygame.Rect(pos_x_disparo, pos_y_disparo, largura_disparo, altura_disparo)
                            rect_queijo_hitbox = pygame.Rect(pos_x_queijo - 10, pos_y_queijo - 10, largura_hitbox_queijo, altura_hitbox_queijo)
                            if rect_disparo.colliderect(rect_queijo_hitbox):
                                # Reduza a vida do queijo com base no dano do disparo
                                vida_queijo -= 5
                                # Remova o disparo
                                disparos.remove(disparo)
                                # Verifique se a vida do queijo chegou a zero
                                if vida_queijo <= 5:
                                    queijo_geracao+=1
                                    queijo_spawn=False
                                    pos_x_chefe3 = largura_tela / 1.3
                                    pos_y_chefe3 = altura_tela / 3
                                    vida_queijo=40

            #Terceira GERAÇÂO QUEIJO MESTRE
                if vida_boss3 <= 0.4 * vida_maxima_boss3 and queijo_geracao==3:
                    if not queijo_spawn:

                        pos_x_queijo = random.randint(area_x_min, area_x_max)
                        pos_y_queijo = random.randint(area_y_min, area_y_max)
                    queijo_spawn = True
                    tela.blit(sprite_queijo, (pos_x_queijo, pos_y_queijo))


                    if queijo_spawn:
                        # Calcule o vetor de direção do chefe para o queijo
                        vetor_direcao = (pos_x_queijo - pos_x_chefe3, pos_y_queijo - pos_y_chefe3)
                        # Normalize o vetor de direção para manter uma velocidade constante
                        comprimento_vetor = max(1, math.sqrt(vetor_direcao[0] ** 2 + vetor_direcao[1] ** 2))
                        vetor_direcao_normalizado = (vetor_direcao[0] / comprimento_vetor, vetor_direcao[1] / comprimento_vetor)
                        # Defina a velocidade do chefe
                        velocidade_chefe = 1.02 * dt
                        #   Atualize a posição do chefe em direção ao queijo
                        pos_x_chefe3 += vetor_direcao_normalizado[0] * velocidade_chefe
                        pos_y_chefe3 += vetor_direcao_normalizado[1] * velocidade_chefe
                        # Verifique se o boss chegou ao queijo
                        distancia_para_queijo = math.sqrt((pos_x_queijo - pos_x_chefe3) ** 2 + (pos_y_queijo - pos_y_chefe3) ** 2)
                        # Alternar entre os frames da animação de locomoção do inimigo
                        tempo_atual = pygame.time.get_ticks()
                        if tempo_atual - tempo_ultimo_frame_boss >= 300:

                            if boss_frame_andando == boss_frame_andando1:
                                boss_frame_andando= boss_frame_andando2
                            else:
                                boss_frame_andando = boss_frame_andando1
                            tempo_ultimo_frame_boss = tempo_atual
                        tela.blit(boss_frame_andando, (pos_x_chefe3, pos_y_chefe3))

                        # Defina uma distância de tolerância para considerar que o chefe alcançou o queijo
                        distancia_tolerancia = 10
                        if distancia_para_queijo < distancia_tolerancia:
                            # O chefe chegou ao queijo, volte para a posição inicial
                            pos_x_chefe3 = largura_tela / 1.3
                            pos_y_chefe3 = altura_tela / 3
                            vida_boss3 += int(vida_maxima_boss3-vida_boss3)*0.6
                            if vida_boss3 > vida_maxima_boss3:
                                vida_maxima_boss3=vida_boss3
                            # Resetar a variável que indica se o queijo está presente
                            queijo_spawn = False

                        for disparo in disparos:
                            # Verifique a colisão entre o disparo e o queijo
                            rect_disparo = pygame.Rect(pos_x_disparo, pos_y_disparo, largura_disparo, altura_disparo)
                            rect_queijo_hitbox = pygame.Rect(pos_x_queijo - 10, pos_y_queijo - 10, largura_hitbox_queijo, altura_hitbox_queijo)
                            if rect_disparo.colliderect(rect_queijo_hitbox):
                                # Reduza a vida do queijo com base no dano do disparo
                                vida_queijo -= 5
                                # Remova o disparo
                                disparos.remove(disparo)
                                # Verifique se a vida do queijo chegou a zero
                                if vida_queijo <= 5:
                                    queijo_geracao+=1
                                    queijo_spawn=False
                                    pos_x_chefe3 = largura_tela / 1.3
                                    pos_y_chefe3 = altura_tela / 3
                                    vida_queijo=40
            #Quarta GERAÇÂO QUEIJO MESTRE
                if vida_boss3 <= 0.4 * vida_maxima_boss3 and queijo_geracao==3:
                    if not queijo_spawn:

                        pos_x_queijo = random.randint(area_x_min, area_x_max)
                        pos_y_queijo = random.randint(area_y_min, area_y_max)
                    queijo_spawn = True
                    tela.blit(sprite_queijo, (pos_x_queijo, pos_y_queijo))


                    if queijo_spawn:
                        # Calcule o vetor de direção do chefe para o queijo
                        vetor_direcao = (pos_x_queijo - pos_x_chefe3, pos_y_queijo - pos_y_chefe3)
                        # Normalize o vetor de direção para manter uma velocidade constante
                        comprimento_vetor = max(1, math.sqrt(vetor_direcao[0] ** 2 + vetor_direcao[1] ** 2))
                        vetor_direcao_normalizado = (vetor_direcao[0] / comprimento_vetor, vetor_direcao[1] / comprimento_vetor)
                        # Defina a velocidade do chefe
                        velocidade_chefe = 1.03 * dt
                        #   Atualize a posição do chefe em direção ao queijo
                        pos_x_chefe3 += vetor_direcao_normalizado[0] * velocidade_chefe
                        pos_y_chefe3 += vetor_direcao_normalizado[1] * velocidade_chefe
                        # Verifique se o boss chegou ao queijo
                        distancia_para_queijo = math.sqrt((pos_x_queijo - pos_x_chefe3) ** 2 + (pos_y_queijo - pos_y_chefe3) ** 2)
                        # Alternar entre os frames da animação de locomoção do inimigo
                        tempo_atual = pygame.time.get_ticks()
                        if tempo_atual - tempo_ultimo_frame_boss >= 300:

                            if boss_frame_andando == boss_frame_andando1:
                                boss_frame_andando= boss_frame_andando2
                            else:
                                boss_frame_andando = boss_frame_andando1
                            tempo_ultimo_frame_boss = tempo_atual
                        tela.blit(boss_frame_andando, (pos_x_chefe3, pos_y_chefe3))

                        # Defina uma distância de tolerância para considerar que o chefe alcançou o queijo
                        distancia_tolerancia = 10
                        if distancia_para_queijo < distancia_tolerancia:
                            # O chefe chegou ao queijo, volte para a posição inicial
                            pos_x_chefe3 = largura_tela / 1.3
                            pos_y_chefe3 = altura_tela / 3
                            vida_boss3 += int(vida_maxima_boss3-vida_boss3)*0.7
                            if vida_boss3 > vida_maxima_boss3:
                                vida_maxima_boss3=vida_boss3
                            # Resetar a variável que indica se o queijo está presente
                            queijo_spawn = False

                        for disparo in disparos:
                            # Verifique a colisão entre o disparo e o queijo
                            rect_disparo = pygame.Rect(pos_x_disparo, pos_y_disparo, largura_disparo, altura_disparo)
                            rect_queijo_hitbox = pygame.Rect(pos_x_queijo - 10, pos_y_queijo - 10, largura_hitbox_queijo, altura_hitbox_queijo)
                            if rect_disparo.colliderect(rect_queijo_hitbox):
                                # Reduza a vida do queijo com base no dano do disparo
                                vida_queijo -= 5
                                # Remova o disparo
                                disparos.remove(disparo)
                                # Verifique se a vida do queijo chegou a zero
                                if vida_queijo <= 5:
                                    queijo_geracao+=1
                                    queijo_spawn=False
                                    pos_x_chefe3 = largura_tela / 1.3
                                    pos_y_chefe3 = altura_tela / 3
                                    vida_queijo=40
            #Quinta GERAÇÂO QUEIJO MESTRE
                if vida_boss3 <= 0.4 * vida_maxima_boss3 and queijo_geracao==3:
                    if not queijo_spawn:

                        pos_x_queijo = random.randint(area_x_min, area_x_max)
                        pos_y_queijo = random.randint(area_y_min, area_y_max)
                    queijo_spawn = True
                    tela.blit(sprite_queijo, (pos_x_queijo, pos_y_queijo))


                    if queijo_spawn:
                        # Calcule o vetor de direção do chefe para o queijo
                        vetor_direcao = (pos_x_queijo - pos_x_chefe3, pos_y_queijo - pos_y_chefe3)
                        # Normalize o vetor de direção para manter uma velocidade constante
                        comprimento_vetor = max(1, math.sqrt(vetor_direcao[0] ** 2 + vetor_direcao[1] ** 2))
                        vetor_direcao_normalizado = (vetor_direcao[0] / comprimento_vetor, vetor_direcao[1] / comprimento_vetor)
                        # Defina a velocidade do chefe
                        velocidade_chefe = 1.1 * dt
                        #   Atualize a posição do chefe em direção ao queijo
                        pos_x_chefe3 += vetor_direcao_normalizado[0] * velocidade_chefe
                        pos_y_chefe3 += vetor_direcao_normalizado[1] * velocidade_chefe
                        # Verifique se o boss chegou ao queijo
                        distancia_para_queijo = math.sqrt((pos_x_queijo - pos_x_chefe3) ** 2 + (pos_y_queijo - pos_y_chefe3) ** 2)
                        # Alternar entre os frames da animação de locomoção do inimigo
                        tempo_atual = pygame.time.get_ticks()
                        if tempo_atual - tempo_ultimo_frame_boss >= 300:

                            if boss_frame_andando == boss_frame_andando1:
                                boss_frame_andando= boss_frame_andando2
                            else:
                                boss_frame_andando = boss_frame_andando1
                            tempo_ultimo_frame_boss = tempo_atual
                        tela.blit(boss_frame_andando, (pos_x_chefe3, pos_y_chefe3))

                        # Defina uma distância de tolerância para considerar que o chefe alcançou o queijo
                        distancia_tolerancia = 10
                        if distancia_para_queijo < distancia_tolerancia:
                            # O chefe chegou ao queijo, volte para a posição inicial
                            pos_x_chefe3 = largura_tela / 1.3
                            pos_y_chefe3 = altura_tela / 3
                            vida_boss3 += int(vida_maxima_boss3-vida_boss3)*1
                            if vida_boss3 > vida_maxima_boss3:
                                vida_maxima_boss3=vida_boss3
                            # Resetar a variável que indica se o queijo está presente
                            queijo_spawn = False

                        for disparo in disparos:
                            # Verifique a colisão entre o disparo e o queijo
                            rect_disparo = pygame.Rect(pos_x_disparo, pos_y_disparo, largura_disparo, altura_disparo)
                            rect_queijo_hitbox = pygame.Rect(pos_x_queijo - 10, pos_y_queijo - 10, largura_hitbox_queijo, altura_hitbox_queijo)
                            if rect_disparo.colliderect(rect_queijo_hitbox):
                                # Reduza a vida do queijo com base no dano do disparo
                                vida_queijo -= 10
                                # Remova o disparo
                                disparos.remove(disparo)
                                # Verifique se a vida do queijo chegou a zero
                                if vida_queijo <= 5:
                                    queijo_geracao+=1
                                    queijo_spawn=False
                                    pos_x_chefe3 = largura_tela / 1.3
                                    pos_y_chefe3 = altura_tela / 3
                                    vida_queijo=30



            if not Boss_vivo3:

                    rect_boss = pygame.Rect(pos_x_chefe3, pos_y_chefe3, 64, 64)
                    rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                    if tempo_atual - tempo_ultimo_frame_boss >= 300:
                        if boss_frame_peca == boss_frame_peca1:
                            boss_frame_peca= boss_frame_peca2
                        else:
                            boss_frame_peca = boss_frame_peca1
                        tempo_ultimo_frame_boss = tempo_atual
                        tela.blit(boss_frame_peca, (pos_x_chefe3, pos_y_chefe3))

                    if rect_boss.colliderect(rect_personagem):
                        if toque == 0:
                            salvar_atributos()
                            Musica_tema_Boss3.stop()
                            pausar_cronometro()
                            tela_transicao_dimensional(tela, 4)
                            if game_manager:
                                from game_manager import EstadoJogo
                                game_manager.mudar_estado(EstadoJogo.JOGO_FASE_4)
                                raise CleanExit()
                            else:
                                import GAME4
                                GAME4.executar_jogo()
                                raise CleanExit()
                            toque+=1

            total_cartas_compradas = sum(cartas_compradas.values())
            custo_carta_atual = custo_base_carta + (total_cartas_compradas * custo_por_carta)
            # Verifica se a pontuação atingiu o custo e se o jogador pressionou o botão da loja
            if Variaveis.obter_modo_cartas() != "drops" and (pontuacao_exib >= custo_carta_atual) and (Variaveis.verificar_input("Comprar na loja") or (joystick and joystick.get_button(3))):
                # Calcula quantas cartas o jogador pode comprar com o custo progressivo
                max_cartas = 0
                total_custo = 0
                temp_cartas_compradas = total_cartas_compradas
                while True:
                    proximo_custo = custo_base_carta + (temp_cartas_compradas * custo_por_carta)
                    if total_custo + proximo_custo <= pontuacao_exib:
                        total_custo += proximo_custo
                        temp_cartas_compradas += 1
                        max_cartas += 1
                    else:
                        break

                if max_cartas > 0:
                    pontuacao_exib -= total_custo
                    pontuacao_magia -= total_custo

                    ret = tela_de_pausa(velocidade_personagem, intervalo_disparo,vida,largura_disparo, altura_disparo,trembo,dano_person_hit,chance_critico,roubo_de_vida,
                                        quantidade_roubo_vida,tempo_cooldown_dash,vida_maxima,Petro_active,Resistencia,vida_petro,vida_maxima_petro,dano_petro,xp_petro,petro_evolucao,Resistencia_petro,
                                        Chance_Sorte,Poison_Active,Dano_Veneno_Acumulado,Executa_inimigo,Ultimo_Estalo,mostrar_info,Mercenaria_Active,Valor_Bonus,dispositivo_ativo,Tempo_cura,porcentagem_cura,cartas_compradas,pontuacao_exib, max_cartas_compraveis=max_cartas, inimigos_eliminados=inimigos_eliminados)
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







            cooldowns = {
                "disparo": max(0.0, (intervalo_disparo_racional(intervalo_disparo, aurea, racional_dilatacao_fim, tempo_atual) - (tempo_atual - tempo_ultimo_disparo)) / 1000.0),
                "teleporte": max(0.0, (tempo_cooldown_dash - (pygame.time.get_ticks() - tempo_ultimo_dash)) / 1000.0),
                "onda": max(0.0, (cooldown_habilidade - (tempo_atual - tempo_ultimo_uso_habilidade)) / 1000.0),
                "loja": 1 if pontuacao_exib >= custo_carta_atual else 0, 
            }

            if False: # Desativado pois o HUD agora é widescreen desenhado nas bordas
                posicao_barra_vida = (80, altura_mapa - (altura_mapa - 34))
                fonte = pygame.font.Font(None, int(altura_barra_vida*1))
                fonte_vida = pygame.font.Font(None, int(altura_barra_vida*0.9))
                texto_vida = fonte_vida.render(f'{int(vida)}/{int(vida_maxima)}', True, (255, 255, 255))

                if Variaveis.obter_modo_cartas() != "drops":
                    texto_pontuacao = fonte.render(f'{pontuacao_exib}/{custo_carta_atual}', True, (250, 255,255))
                    texto_pontuacao_borda = fonte.render(f'{pontuacao_exib}/{custo_carta_atual}', True, (0, 0, 0))
                    tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 - 1, altura_mapa*0.118 - 1))
                    tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 + 1, altura_mapa*0.118 - 1))
                    tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 - 1, altura_mapa*0.118 + 1))
                    tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 + 1, altura_mapa*0.118 + 1))
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

                if not area_icones.colliderect(
                (pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                ):
                    # Desenhar habilidades na tela
                    desenhar_habilidades(tela, cooldowns,dispositivo_ativo)
                if Mercenaria_Active:
                    fonte_combo = pygame.font.Font(None, 36)  # Tamanho maior para o combo
                    fonte_bonus = pygame.font.Font(None, 28)  # Tamanho menor para o bônus

                    # Texto do combo
                    texto_combo = f"Mercenaria: {eliminacoes_consecutivas} abates"
                    posicao_combo = (largura_mapa - 330, 50)
                    desenhar_texto_com_contorno(tela, texto_combo, fonte_combo, (255, 220, 80), (0, 0, 0), posicao_combo)

                    # Texto do bônus
                    faltam_bonus = 5 - (eliminacoes_consecutivas % 5)
                    texto_bonus = f"Bonus: +{bonus_pontuacao} | prox +{Valor_Bonus} em {faltam_bonus}"
                    posicao_bonus = (largura_mapa - 330, 90)
                    desenhar_texto_com_contorno(tela, texto_bonus, fonte_bonus, (255, 245, 190), (0, 0, 0), posicao_bonus)

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
            desenhar_efeitos_vanguarda(
                tela,
                pos_x_personagem,
                pos_y_personagem,
                largura_personagem,
                altura_personagem,
                inimigos_comum,
                inimigos_em_chamas,
                duracao_incendio_vanguarda,
                aurea,
                config_graficos,
            )
            desenhar_efeito_racional_dilatacao(
                tela,
                pos_x_personagem,
                pos_y_personagem,
                largura_personagem,
                altura_personagem,
                racional_dilatacao_fim,
                aurea,
                config_graficos,
            )
            atualizar_e_desenhar_fragmentos(tela)
            atualizar_e_desenhar_particulas_pontos(tela)

            # Atualizar e desenhar ondas de choque do teleporte
            ondas_ativas = []
            for oc in ondas_choque:
                oc["raio_atual"] += oc["velocidade"]
                if oc["raio_atual"] <= oc["raio_max"]:
                    ondas_ativas.append(oc)
                    # Desenhar círculo em expansão com transparência
                    diametro = int(oc["raio_atual"] * 2)
                    surf = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
                    
                    progresso = oc["raio_atual"] / oc["raio_max"]
                    alpha = int(180 * (1.0 - progresso))
                    
                    cor = oc["cor"]
                    r, g, b = cor
                    # Círculo externo
                    pygame.draw.circle(surf, (r, g, b, alpha), (int(oc["raio_atual"]), int(oc["raio_atual"])), int(oc["raio_atual"]), width=max(1, int(4 * (1.0 - progresso))))
                    # Brilho interno sutil
                    pygame.draw.circle(surf, (r, g, b, alpha // 2), (int(oc["raio_atual"]), int(oc["raio_atual"])), int(oc["raio_atual"]))
                    
                    tela.blit(surf, (oc["cx"] - int(oc["raio_atual"]), oc["cy"] - int(oc["raio_atual"])))
            ondas_choque = ondas_ativas
            for moeda in moedas_soltadas:
                tela.blit(moeda["image"], moeda["rect"])

            # --- SISTEMA DE CARTAS DROP ---
            if Variaveis.obter_modo_cartas() == "drops":
                Variaveis.atualizar_e_desenhar_cartas_no_chao(tela, tempo_atual)
                stats_jogador = {
                    "velocidade_personagem": velocidade_personagem, "intervalo_disparo": intervalo_disparo,
                    "vida": vida, "vida_maxima": vida_maxima, "dano_person_hit": dano_person_hit,
                    "chance_critico": chance_critico, "roubo_de_vida": roubo_de_vida,
                    "quantidade_roubo_vida": quantidade_roubo_vida, "tempo_cooldown_dash": tempo_cooldown_dash,
                    "Petro_active": Petro_active, "Resistencia": Resistencia,
                    "vida_petro": vida_petro, "vida_maxima_petro": vida_maxima_petro,
                    "dano_petro": dano_petro, "xp_petro": xp_petro, "petro_evolucao": petro_evolucao,
                    "Resistencia_petro": Resistencia_petro, "Chance_Sorte": Chance_Sorte,
                    "Poison_Active": Poison_Active, "Dano_Veneno_Acumulado": Dano_Veneno_Acumulado,
                    "Executa_inimigo": Executa_inimigo, "Ultimo_Estalo": Ultimo_Estalo,
                    "Mercenaria_Active": Mercenaria_Active, "Valor_Bonus": Valor_Bonus,
                    "Tempo_cura": Tempo_cura, "porcentagem_cura": porcentagem_cura,
                    "trembo": trembo, "cartas_compradas": cartas_compradas,
                    "inimigos_eliminados": inimigos_eliminados
                }
                coletadas = Variaveis.coletar_cartas_no_chao(personagem_rect, stats_jogador, efeitos_texto)
                if coletadas:
                    velocidade_personagem = stats_jogador["velocidade_personagem"]
                    intervalo_disparo = stats_jogador["intervalo_disparo"]
                    vida = stats_jogador["vida"]; vida_maxima = stats_jogador["vida_maxima"]
                    dano_person_hit = stats_jogador["dano_person_hit"]
                    chance_critico = stats_jogador["chance_critico"]
                    roubo_de_vida = stats_jogador["roubo_de_vida"]
                    quantidade_roubo_vida = stats_jogador["quantidade_roubo_vida"]
                    tempo_cooldown_dash = stats_jogador["tempo_cooldown_dash"]
                    Petro_active = stats_jogador["Petro_active"]; Resistencia = stats_jogador["Resistencia"]
                    vida_petro = stats_jogador["vida_petro"]; vida_maxima_petro = stats_jogador["vida_maxima_petro"]
                    dano_petro = stats_jogador["dano_petro"]; xp_petro = stats_jogador["xp_petro"]
                    petro_evolucao = stats_jogador["petro_evolucao"]; Resistencia_petro = stats_jogador["Resistencia_petro"]
                    Chance_Sorte = stats_jogador["Chance_Sorte"]; Poison_Active = stats_jogador["Poison_Active"]
                    Dano_Veneno_Acumulado = stats_jogador["Dano_Veneno_Acumulado"]
                    Executa_inimigo = stats_jogador["Executa_inimigo"]; Ultimo_Estalo = stats_jogador["Ultimo_Estalo"]
                    Mercenaria_Active = stats_jogador["Mercenaria_Active"]; Valor_Bonus = stats_jogador["Valor_Bonus"]
                    Tempo_cura = stats_jogador["Tempo_cura"]; porcentagem_cura = stats_jogador["porcentagem_cura"]
                    trembo = stats_jogador["trembo"]; cartas_compradas = stats_jogador["cartas_compradas"]


            desenhar_hud_fase(
                tela, vida, vida_maxima, pontuacao_exib, custo_carta_atual,
                pontuacao_magia, cooldowns, dispositivo_ativo,
                eliminacoes_consecutivas, bonus_pontuacao, aurea,
                escudo_devota_ativo, pos_x_personagem, pos_y_personagem,
                largura_personagem, altura_personagem
            )

            tela.blit(cursor_imagem, (mouse_x, mouse_y))    

            exibir_cronometro(tela)

            pygame.display.flip()
            dt_ms = FPS.tick(config_graficos.get("fps_limite", 60))  # Limita a taxa de quadros conforme configuração
            dt = max(0.05, min(3.0, dt_ms / 16.666667))
            Variaveis.dt = dt


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
