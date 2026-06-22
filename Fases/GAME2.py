
import Caminhos
import pygame
import sys
import os
import random
import math
from Tela_Cartas import tela_de_pausa as tela_de_pausa_single
from Tela_Cartas_Coop import tela_de_pausa as tela_de_pausa_coop
import subprocess
import sys
import json
import lacerante_manifestacao
import prismatica_manifestacao
import retornante_manifestacao
import parasitica_manifestacao
import condutora_manifestacao
import gravitante_manifestacao
import ancorada_manifestacao
import boss_manifestacao_effects
import teleporte_manifestacao
from estado_jogador_fases import carregar_estado_jogador, salvar_estado_jogador
from dados_manifestacoes import registrar_conclusao_fase
from qa_logger import instalar_captura_global, instalar_filtro_prints, registrar_erro
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
    ganho_passiva_racional,
    intervalo_disparo_racional,
    personagem_racional_imovel,
    RACIONAL_PASSIVA_INTERVALO_MS,
    tentar_ativar_dilatacao_racional,
    absorver_hit_devota,
    consumir_cura_absorcao_devota,
    criar_estado_devota,
    fator_dano_devota,
    fator_velocidade_devota,
    restaurar_escudo_devota,
)
from post_boss_pressure import criar_estado_pressao_pos_boss, calcular_pressao_spawn_pos_boss
from player_projectile import PlayerProjectileVFX, estourar_disparo_eletrico
from onda_recoil import criar_estado_coice_onda, aplicar_coice_onda, atualizar_coice_onda
from audio_manager import carregar_config_audio, aplicar_volume_som
from Tela_Upgrade_Aureas import tela_upgrade_aureas
from boss_ui import desenhar_barra_vida_boss, registrar_dano_boss
import insana_aurea
import voraz_aurea
import aureas_avancadas
import multiplayer_coop

instalar_captura_global()
instalar_filtro_prints()


def tela_de_pausa(*args, **kwargs):
    if multiplayer_coop.modo_multiplayer():
        return tela_de_pausa_coop(*args, **kwargs)
    return tela_de_pausa_single(*args, **kwargs)

dt = 1.0

# Forward declarations (atribuídos no loop principal)
botao_mouse = (False, False, False)
sprite_moeda = None
joystick = None
gerar_fragmentos_morte = None
aurea = None
escudo_devota_ativo = True
duracao_incendio_vanguarda = 5000
intervalo_escudo = 30000
racional_dilatacao_fim = 0
racional_dilatacao_proximo_uso = 0
estado_devota = criar_estado_devota(False)
pressao_pos_boss_spawn = criar_estado_pressao_pos_boss()

def fator_dano_aureas(agora_ms=None):
    agora_ms = pygame.time.get_ticks() if agora_ms is None else agora_ms
    import condutora_manifestacao
    return fator_dano_devota(aurea, estado_devota, agora_ms) * condutora_manifestacao.obter_multiplicador_dano_and(agora_ms)

def absorver_dano_devota_atual():
    global vida, escudo_devota_ativo, tempo_ultimo_escudo
    agora_ms = pygame.time.get_ticks()
    import condutora_manifestacao
    if condutora_manifestacao.tentar_absorver_dano_nand(agora_ms):
        efeitos_texto.append({"texto": "BLOQUEIO LÓGICO", "x": pos_x_personagem - 28, "y": pos_y_personagem - 28, "tempo_inicio": agora_ms, "cor": (104, 255, 214)})
        return True
    absorvido, escudo_devota_ativo, escudo_quebrou = absorver_hit_devota(aurea, escudo_devota_ativo, estado_devota, agora_ms)
    if not absorvido:
        return False
    vida, cura_devota = consumir_cura_absorcao_devota(aurea, estado_devota, vida, vida_maxima)
    if cura_devota > 0:
        efeitos_texto.append({"texto": f"+{cura_devota} FE", "x": pos_x_personagem + 8, "y": pos_y_personagem - 48, "tempo_inicio": agora_ms, "cor": (255, 225, 90)})
    if escudo_quebrou:
        tempo_ultimo_escudo = agora_ms
        efeitos_texto.append({"texto": "FE ARDENTE: +DANO", "x": pos_x_personagem - 28, "y": pos_y_personagem - 28, "tempo_inicio": agora_ms, "cor": (80, 180, 255)})
    else:
        efeitos_texto.append({"texto": f"ESCUDO DEVOTA {estado_devota.get('cargas', 0)}/3", "x": pos_x_personagem - 28, "y": pos_y_personagem - 28, "tempo_inicio": agora_ms, "cor": (255, 210, 80)})
    return True

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
velocidade_disparo_inimigo = 3  

estalos = aplicar_volume_som(pygame.mixer.Sound("Sounds/Estalo.mp3"), config_audio)

som_ataque_boss = aplicar_volume_som(pygame.mixer.Sound("Sounds/Hit_Boss1.mp3"), config_audio)

Hit_inimigo2 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Inimigo1_hit.wav"), config_audio)

Disparo_Geo = aplicar_volume_som(pygame.mixer.Sound("Sounds/Disparo_Geo.wav"), config_audio)  
Musica_tema_Boss2 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase2_Boss.mp3"), config_audio, canal="musica", volume_maximo=0.05)
Musica_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase_boas.mp3"), config_audio, canal="musica", volume_maximo=0.06)
Som_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Neve.wav"), config_audio, canal="musica", volume_maximo=0.07)
Som_portal = aplicar_volume_som(pygame.mixer.Sound("Sounds/Portal.mp3"), config_audio, canal="efeitos", volume_maximo=0.06)  
musica_boss2=1

tela = pygame.Surface((largura_mapa, altura_mapa))
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

def criar_variante_imagem(image, color):
    tinted = image.copy()
    tint_surf = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
    tint_surf.fill(color + (255,))
    tinted.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return tinted

frames_atirador_esquerda = [criar_variante_imagem(img, (180, 220, 255)) for img in frames_inimigo_esquerda2]
frames_atirador_direita = [criar_variante_imagem(img, (180, 220, 255)) for img in frames_inimigo_direita2]

frames_kamikaze_esquerda = [criar_variante_imagem(img, (255, 120, 120)) for img in frames_inimigo_esquerda2]
frames_kamikaze_direita = [criar_variante_imagem(img, (255, 120, 120)) for img in frames_inimigo_direita2]

vida_inimigo_maxima = multiplayer_coop.aplicar_multiplicador_vida_inimigo(vida_inimigo_comum_inicial(30))
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
    salvar_estado_jogador(globals())
    return
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
        "largura_disparo": largura_disparo,
        "altura_disparo": altura_disparo,
    }

    with open('saves/atributos.json', 'w') as file:
        json.dump(atributos, file)

def carregar_atributos():
    carregar_estado_jogador(globals())
    globals()["cartas_compradas"] = normalizar_cartas_compradas(globals()["cartas_compradas"])
    return
    global velocidade_personagem, intervalo_disparo, dano_person_hit, chance_critico, roubo_de_vida, quantidade_roubo_vida,vida_maxima,vida_maxima_petro,vida,xp_petro,Petro_active,trembo,dano_petro,Resistencia,Resistencia_petro,dano_inimigo_longe,dano_inimigo_perto,direcao_atual,Poison_Active,Ultimo_Estalo,Executa_inimigo,Valor_Bonus,Mercenaria_Active,tempo_cooldown_dash,vida_petro,petro_evolucao,Dano_Veneno_Acumulado, Tempo_cura,porcentagem_cura, moedas_totais, Chance_Sorte, cartas_compradas, largura_disparo, altura_disparo
    if not os.path.exists('saves/atributos.json'):
        cartas_compradas = normalizar_cartas_compradas(cartas_compradas)
        return
    with open('saves/atributos.json', 'r') as file:
        atributos = json.load(file)
        if not isinstance(atributos, dict):
            atributos = {}
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
            "moedas_totais": moedas_totais,
            **atributos,
        }
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
        Chance_Sorte = atributos.get("Chance_Sorte", 0.0)
        largura_disparo = atributos.get("largura_disparo", largura_disparo)
        altura_disparo = atributos.get("altura_disparo", altura_disparo)
        if "cartas_compradas" in atributos:
            cartas_compradas.update(atributos["cartas_compradas"])
        cartas_compradas = normalizar_cartas_compradas(cartas_compradas)



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
    global personagem_imovel, tempo_ultimo_atingido
    global angulo_inclinacao_personagem
    global vida_inimigo_maxima, Resistencia_petro, dano_inimigo_perto, vida_maxima_petro, dano_petro, dano_boss2, dano_inimigo_longe
    global inimigos_eliminados, pontuacao, pontuacao_exib, eliminacoes_consecutivas, bonus_pontuacao, vida_boss2, Valor_Bonus
    global jogador_desacelerado, blizzard_ativo
    global racional_dilatacao_fim, racional_dilatacao_proximo_uso

    # Se o personagem estiver imóvel, não atualize a posição
    if personagem_imovel:
        return
    direcao_atual = 'stop'  # Por padrão, definimos a direção como 'stop'
    dx, dy = 0, 0

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

    if dx != 0 or dy != 0:
        movimento_pressionado = True
        direcao_atual = ultima_tecla_movimento
        
        # Calculate active movement speed considering slows
        vel_atual = velocidade_personagem * fator_velocidade_devota(aurea, estado_devota, pygame.time.get_ticks())
        if jogador_desacelerado:
            vel_atual *= 0.65
        if blizzard_ativo:
            vel_atual *= 0.75
        vel_atual *= fator_movimento_racional(aurea, racional_dilatacao_fim)
        vel_atual *= condutora_manifestacao.fator_ruido_logico(manifestacao_ativa, pygame.time.get_ticks())
        vel_atual *= condutora_manifestacao.obter_fator_velocidade_xor(pygame.time.get_ticks())
        vel_atual *= aureas_avancadas.fator_velocidade_jogador(globals().get("estado_aureas_avancadas"), aurea, pygame.time.get_ticks())

        # Normalização de movimento diagonal
        if dx != 0 and dy != 0:
            inclinacao = angulo_diagonal_personagem
            
            if dy < 0:
                angulo_inclinacao_personagem = -inclinacao if dx > 0 else inclinacao
            else:
                angulo_inclinacao_personagem = inclinacao if dx > 0 else -inclinacao
                
            fator_normalizacao = 0.7071
            pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                         pos_x_personagem + dx * vel_atual * fator_normalizacao * dt))
            pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                         pos_y_personagem + dy * vel_atual * fator_normalizacao * dt))
        else:
            angulo_inclinacao_personagem = 0
            pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                         pos_x_personagem + dx * vel_atual * dt))
            pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                         pos_y_personagem + dy * vel_atual * dt))
        
        pos_x_personagem, pos_y_personagem = Variaveis.resolver_colisao_player_com_inimigos(
            pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, inimigos_comum
        )
        pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem))
        pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem))
    else:
        angulo_inclinacao_personagem = 0
        if disparo_preparando:
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

    teleporte_pressionado = bool(dash_teclado or dash_joystick or executar_teleporte_mouse_flag)
    estado_retorno = teleporte_manifestacao.atualizar_estado_retorno(
        manifestacao_ativa, tempo_atual, teleporte_pressionado
    )
    if estado_retorno == "expirado" and not cooldown_dash:
        cooldown_dash = True
        tempo_ultimo_dash = tempo_atual
    retorno_disponivel = teleporte_manifestacao.retorno_disponivel(
        manifestacao_ativa, tempo_atual, teleporte_pressionado
    )
    if (dash_teclado or dash_joystick or executar_teleporte_mouse_flag) and (cooldown_dash == False or retorno_disponivel):
        Som_portal.play()
        origem_teleporte = (pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2)
        player_pos_origem_teleporte = (pos_x_personagem, pos_y_personagem)
        retorno_teleporte = teleporte_manifestacao.consumir_retorno_manifestacao_retornante(
            manifestacao_ativa, tempo_atual, largura_mapa, altura_mapa, largura_personagem, altura_personagem
        ) if retorno_disponivel else None

        if retorno_teleporte is not None:
            dest_px, dest_py = retorno_teleporte
            animar_teleporte_plasma(tela, mapa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, teleporte_duration // 2, ultima_tecla_movimento, distancia_dash, largura_mapa, altura_mapa, dest_x=dest_px, dest_y=dest_py)
            tela.blit(mapa, (pos_x_personagem, pos_y_personagem), pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem))
            pos_x_personagem, pos_y_personagem = dest_px, dest_py
        elif executar_teleporte_mouse_flag:
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

        tempo_teleporte_agora = pygame.time.get_ticks()
        novo_fim_racional, racional_dilatacao_proximo_uso = tentar_ativar_dilatacao_racional(
            aurea,
            tempo_teleporte_agora,
            racional_dilatacao_proximo_uso,
        )
        if novo_fim_racional is not None:
            racional_dilatacao_fim = novo_fim_racional
        destino_teleporte = (pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2)
        efeito_teleporte = teleporte_manifestacao.aplicar_efeito_teleporte_manifestacao(
            manifestacao_ativa,
            origem_teleporte,
            destino_teleporte,
            inimigos_comum,
            None,
            dano_person_hit * fator_dano_aureas(tempo_atual),
            efeitos_texto,
            tempo_atual,
            largura_mapa,
            altura_mapa,
            ondas,
            retorno_teleporte is not None,
            player_pos_origem_teleporte,
        )
        if condutora_manifestacao.ativa(manifestacao_ativa):
            condutora_manifestacao.registrar_teleporte_condutor(tempo_teleporte_agora)
        primeiro_salto_retornante = (
            str(manifestacao_ativa or "").strip().lower() == "retornante"
            and retorno_teleporte is None
            and teleporte_manifestacao.teleporte_retornante_ativo(manifestacao_ativa)
        )
        if primeiro_salto_retornante:
            cooldown_dash = False
            tempo_ultimo_dash = tempo_teleporte_agora - int(tempo_cooldown_dash)
        else:
            cooldown_dash = True
            tempo_ultimo_dash = tempo_teleporte_agora + int(efeito_teleporte.get("cooldown_extra_ms", 0))

        # Onda de choque no destino do teletransporte
        cx_t = pos_x_personagem + largura_personagem // 2
        cy_t = pos_y_personagem + altura_personagem // 2
        raio_choque = 120
        dano_choque = dano_person_hit * fator_dano_aureas(tempo_atual) * 0.3

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
                gerar_fragmentos_morte(inimigo, 2)
                if inimigo in inimigos_comum:
                    if inimigo.get("tipo", "comum") == "kamikaze":
                        trigger_kamikaze_explosion(inimigo)
                    inimigos_comum.remove(inimigo)
                
                # Escalonamento recalibrado
                mult = 1.0 + (nivel_ameaca * 0.12)
                vida_inimigo_maxima += ganho_vida_inimigo_comum(0.6 * mult)
                Resistencia_petro += 0.01 * mult
                dano_inimigo_perto += 0.06 * mult
                dano_person_hit += 0.1 * mult
                vida_maxima_petro += 0.8 * mult
                dano_petro += 0.008 * mult
                dano_boss2 += 0.02 * mult
                dano_inimigo_longe += 0.015 * mult

                inimigos_eliminados += 1
                ganho = int(130 * (1 + math.log10(inimigos_eliminados + 1)))
                pontuacao += ganho

                if Mercenaria_Active:
                    eliminacoes_consecutivas += 1
                    pontuacao_exib += ganho + bonus_pontuacao
                    if eliminacoes_consecutivas % 5 == 0:
                        bonus_pontuacao = min(500, bonus_pontuacao + Valor_Bonus)
                else:
                    pontuacao_exib += ganho

        # Dano ao Boss 2
        if r_press and not boss_entrada_ativa and boss_vivo2:
            bx = pos_x_chefe2 + chefe_largura2 // 2
            by = pos_y_chefe2 + chefe_altura2 // 2
            dist_boss = math.hypot(bx - cx_t, by - cy_t)
            if dist_boss <= raio_choque:
                vida_boss2 -= dano_boss_mitigado(dano_choque, 2, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                efeitos_texto.append({
                    "texto": f"-{int(dano_choque)}",
                    "x": pos_x_chefe2 + chefe_largura2 // 2,
                    "y": pos_y_chefe2 - 20,
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
intervalo_criacao_gelo = 2000  # 10 segundos

# State variables for new Phase 2 features
jogador_desacelerado = False
blizzard_ativo = False
zonas_lentidao = []
rastros_neve = []
ice_blocks_particles = []
velocidade_disparo_inimigo = 3.0 # Fallback global value
tempo_ultimo_blizzard = 0
tempo_inicio_blizzard = 0
intervalo_blizzard = 40000
duracao_blizzard = 10000
tempo_inicio_aviso_vertical = 0
tempo_inicio_aviso_horizontal = 0
duracao_aviso = 1000
ataque_vertical_aviso = False
ataque_horizontal_aviso = False
boss_entrada_ativa = False
boss_entrada_tempo_inicio = 0
tempo_boss_entrada_fim = 0
boss_impacto_feito = False
screen_shake = 0
ice_shards = []
ataque_avalanche_aviso = False
ataque_avalanche_ativo = False
tempo_inicio_aviso_avalanche = 0
avalanche_posicoes = []
avalanche_projeteis = []
tempo_inicio_ataque = 0
boss_sopro_aviso = False
boss_sopro_ativo = False
tempo_inicio_sopro = 0
sopro_dir = (0, 0)
sopro_particulas = []
tempo_ultimo_sopro_disparo = 0
boss_escudo_ativo = False
tempo_inicio_escudo = 0
escudo_cristais_angulo = 0.0
tempo_ultimo_disparo_escudo = 0
avalanche_particulas_vento = []
ondas_nevasca = []
ondas_nevasca_preparadas = []


def criar_disparo_inimigo(pos_inimigo, pos_personagem, is_elite=False, tipo="comum"):
    dx = pos_personagem[0] - pos_inimigo[0]
    dy = pos_personagem[1] - pos_inimigo[1]
    dist = max(1, math.sqrt(dx ** 2 + dy ** 2))
    
    vel = velocidade_disparo_inimigo
    w = largura_disparo * 0.5
    h = altura_disparo * 0.5

    if tipo == "atirador":
        # Snowball is larger, but slower
        vel = velocidade_disparo_inimigo * 0.8
        w = largura_disparo * 1.2
        h = altura_disparo * 1.2

    if is_elite:
        vel *= 1.3
        w = int(w * 1.4)
        h = int(h * 1.4)
    
    direcao_disparo_inimigo = (dx / dist * vel, dy / dist * vel)

    return {
        "rect": pygame.Rect(pos_inimigo[0], pos_inimigo[1], w, h),
        "velocidade": direcao_disparo_inimigo,
        "elite": is_elite,
        "tipo": tipo,
        "angulo_rotacao": 0.0,
        "ultimo_rastro": pygame.time.get_ticks()
    }


def criar_inimigo(x, y, is_elite=False, tipo=None):
    if tipo is None:
        r_type = random.random()
        if r_type <= 0.50:
            tipo = "comum"
        elif r_type <= 0.80:
            tipo = "atirador"
        else:
            tipo = "kamikaze"

    image = frames_inimigo[0]
    w = largura_inimigo
    h = altura_inimigo
    vida_max = vida_inimigo_maxima

    if tipo == "kamikaze":
        w = int(largura_inimigo * 0.9)
        h = int(altura_inimigo * 0.9)
        vida_max = int(vida_inimigo_maxima * 0.8)
    elif tipo == "atirador":
        w = int(largura_inimigo * 1.1)
        h = int(altura_inimigo * 1.1)
        vida_max = int(vida_inimigo_maxima * 1.2)

    if is_elite:
        w = int(w * 1.35)
        h = int(h * 1.35)
        vida_max = vida_max * 3.0

    return {
        "rect": pygame.Rect(x, y, w, h),
        "image": image,
        "vida": vida_max,
        "vida_maxima": vida_max,
        "elite": is_elite,
        "tipo": tipo,
        "pos_x": float(x),
        "pos_y": float(y)
    }

def trigger_kamikaze_explosion(inimigo):
    global vida, personagem_imovel, tempo_ultimo_atingido, escudo_devota_ativo, piscando_vida, tempo_ultimo_hit_inimigo, imune_tempo_restante
    cx, cy = inimigo["rect"].center

    # 1. Damage and freeze player if within radius of 120px
    px = pos_x_personagem + largura_personagem // 2
    py = pos_y_personagem + altura_personagem // 2
    dist_to_player = math.sqrt((px - cx)**2 + (py - cy)**2)
    if dist_to_player <= 120:
        dmg = int(vida_maxima * 0.15)
        dmg_taken = max(10, dmg - Resistencia)

        if imune_tempo_restante > 0:
            pass
        elif absorver_dano_devota_atual():
            pass
        else:
            vida -= dmg_taken
            piscando_vida = True
            tempo_ultimo_hit_inimigo = pygame.time.get_ticks()

        # Freeze player
        personagem_imovel = True
        tempo_ultimo_atingido = pygame.time.get_ticks()

        # Add visual floating text popup
        efeitos_texto.append({
            "texto": "CONGELADO!",
            "x": pos_x_personagem,
            "y": pos_y_personagem - 20,
            "tempo_inicio": pygame.time.get_ticks(),
            "cor": (0, 225, 255)
        })

    # 2. Spawn ice block particles (exploding into several small blocks of ice)
    for _ in range(random.randint(12, 18)):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.0, 5.0)
        ice_blocks_particles.append({
            "pos": [float(cx), float(cy)],
            "vel": [speed * math.cos(angle), speed * math.sin(angle)],
            "size": random.randint(6, 12),
            "life": 1.0,
            "decay": random.uniform(0.02, 0.04),
            "rot": random.uniform(0, 360),
            "rot_vel": random.uniform(-5, 5)
        })

def criar_inimigo_old(x, y, is_elite=False):
    image = frames_inimigo[0]
    w = largura_inimigo
    h = altura_inimigo
    vida_max = vida_inimigo_maxima
    if is_elite:
        w = int(largura_inimigo * 1.35)
        h = int(altura_inimigo * 1.35)
        vida_max = vida_inimigo_maxima * 3.0
    return {"rect": pygame.Rect(x, y, w, h), "image": image, "vida": vida_max, "vida_maxima": vida_max, "elite": is_elite}

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

def gerar_inimigo(limite_inimigos=None):
    global inimigos_comum, r_press
    if multiplayer_coop.eh_cliente():
        return
    if r_press and boss_vivo2:
        return

    limite_inimigos = max_inimigos2 if limite_inimigos is None else limite_inimigos
    if len(inimigos_comum) < limite_inimigos:
        is_elite = random.random() <= 0.20
        # Adicione uma chance de 40% de gerar o inimigo na borda esquerda
        if random.random() <= 0.4:
            novo_inimigo = criar_inimigo(0, random.randint(10, altura_mapa), is_elite)
        else:
            novo_inimigo = criar_inimigo(largura_mapa, random.randint(10, altura_mapa), is_elite)

        # Verifique se o novo inimigo está muito próximo de algum inimigo existente
        distancia_minima_alcancada = any(
            math.sqrt((novo_inimigo["rect"].x - inimigo["rect"].x) ** 2 + (novo_inimigo["rect"].y - inimigo["rect"].y) ** 2) < distancia_minima_inimigos
            for inimigo in inimigos_comum
        )

        
        while distancia_minima_alcancada:
            if random.random() <= 0.4:
                novo_inimigo = criar_inimigo(0, random.randint(10, altura_mapa), is_elite)
            else:
                novo_inimigo = criar_inimigo(largura_mapa, random.randint(10, altura_mapa), is_elite)
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


movimento_pressionado = False
dano = 0
fonte = None
running = True
tempo_atual = 0
disparo_preparando = False
disparo_frame_atual = 0
tempo_ultimo_frame_preparo_disparo = 0
angulo_disparo_preparado = 0.0
DISPARO_PREPARO_FRAME_MS = 85
upgrades = {}
x = 0
y = 0

def executar_jogo(game_manager=None):
    global dt
    global aurea
    global boss_vivo2
    global direcao_atual
    global disparo_preparando, disparo_frame_atual, tempo_ultimo_frame_preparo_disparo, angulo_disparo_preparado, DISPARO_PREPARO_FRAME_MS
    global joystick, inimigos_comum, ondas_choque, gerar_fragmentos_morte, Chance_Sorte, Dano_Veneno_Acumulado, Executa_inimigo, Mercenaria_Active, Musica_tema_Boss2, Musica_tema_fases, Petro_active, Poison_Active, Resistencia, Resistencia_petro, Som_tema_fases, Tempo_cura, Ultimo_Estalo, Valor_Bonus, altura_disparo, ataque_horizontal_ativo, ataque_vertical_ativo, bonus_pontuacao, boss_envenenado, carregar_atributos_na_fase, cartas_compradas, cartas_visiveis, chance_critico, cooldown_dash, dano, dano_boss2, dano_inimigo_longe, dano_inimigo_perto, dano_person_hit, dano_petro, dano_por_tick_veneno_boss, disparos, disparos_inimigos, dispositivo_ativo, efeitos_texto, eliminacoes_consecutivas, eliminacoes_consecutivas_impulsiva, escudo_devota_ativo, fonte, frame_atual, frame_atual_chefe, frame_atual_disparo, frame_porcentagem, impulsiva_ativa, imune_tempo_restante, inimigos_atingidos_por_onda, inimigos_eliminados, inimigos_em_chamas, intervalo_disparo, largura_disparo, max_inimigos2, moedas_coletadas, moedas_soltadas, moedas_totais, movimento_pressionado, musica_boss2, nivel_ameaca, ondas, personagem_imovel, petro_evolucao, piscando_vida, pontuacao, pontuacao_exib, pontuacao_magia, porcentagem_cura, pos_x_personagem, pos_x_petro, pos_y_personagem, pos_y_petro, posicao_ataque_horizontal, posicao_ataque_vertical, quantidade_roubo_vida, r_press, rect_boss, roubo_de_vida, running, sprite_moeda, teleportado, tempo_anterior_petro, tempo_atual, tempo_cooldown_dash, tempo_ultimo_dash, tempo_inicio_ataque_horizontal, tempo_inicio_buff_impulsiva, tempo_inicio_dano_horizontal, tempo_inicio_veneno_boss, tempo_passado, tempo_passado_animacao_chefe2, tempo_texto_dano, tempo_ultima_atualizacao_direcao, tempo_ultima_regeneracao, tempo_ultimo_atingido, tempo_ultimo_dano_horizontal, tempo_ultimo_dano_vertical, tempo_ultimo_disparo_inimigo, tempo_ultimo_hit_inimigo, tempo_ultimo_inimigo, tempo_ultimo_uso_habilidade, texto_dano, tipo_buff_impulsiva, toque, trembo, ultima_direcao_animacao, ultimo_tick_veneno_boss, upgrades, velocidade_ataque_horizontal, velocidade_ataque_vertical, velocidade_inimigo2, velocidade_personagem, vida, vida_boss, vida_boss2, vida_boss3, vida_boss4, vida_inimigo_maxima, vida_maxima, vida_maxima_boss2, vida_maxima_boss3, vida_maxima_boss4, vida_maxima_petro, vida_petro, x, xp_petro, y, duracao_incendio_vanguarda, intervalo_escudo, comando_direção_petro
    global jogador_desacelerado, blizzard_ativo, zonas_lentidao, velocidade_disparo_inimigo, ataque_vertical_aviso, ataque_horizontal_aviso, tempo_inicio_aviso_vertical, tempo_inicio_aviso_horizontal, vida_inimigo, tempo_ultimo_blizzard, tempo_inicio_blizzard, intervalo_blizzard, duracao_blizzard, duracao_aviso, boss_entrada_ativa, boss_entrada_tempo_inicio, tempo_boss_entrada_fim, boss_impacto_feito, screen_shake, ice_shards, ataque_avalanche_aviso, ataque_avalanche_ativo, tempo_inicio_aviso_avalanche, avalanche_posicoes, avalanche_projeteis, tempo_inicio_ataque, boss_sopro_aviso, boss_sopro_ativo, tempo_inicio_sopro, sopro_dir, sopro_particulas, tempo_ultimo_sopro_disparo, boss_escudo_ativo, tempo_inicio_escudo, escudo_cristais_angulo, tempo_ultimo_disparo_escudo, avalanche_particulas_vento, pos_x_chefe2, pos_y_chefe2, ondas_nevasca, ondas_nevasca_preparadas, rastros_neve, ice_blocks_particles
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
        manifestacao_ativa = Variaveis.obter_manifestacao_ativa()

        vfx_disparo_player = PlayerProjectileVFX()
        
        tempo_ultimo_escudo = pygame.time.get_ticks()
        tempo_parado_person = pygame.time.get_ticks()  
        tempo_ultimo_disparo = pygame.time.get_ticks()
        disparo_preparando = False
        disparo_frame_atual = 0
        tempo_ultimo_frame_preparo_disparo = 0
        angulo_disparo_preparado = 0.0
        DISPARO_PREPARO_FRAME_MS = 85
        coice_onda = criar_estado_coice_onda()
        boss_atingido_por_onda = pygame.time.get_ticks()
        Musica_tema_fases.play(loops=-1)
        Som_tema_fases.play(loops=-1)
        upgrades = carregar_upgrade_aureas("saves/aureas_upgrade.json")
        ondas_choque = []
        rastros_neve = []
        ice_blocks_particles = []

        # Configurar e escalar as passivas das áureas
        nivel_devota = upgrades.get("Devota", 0)
        nivel_vanguarda = upgrades.get("Vanguarda", 0)
        estado_insana = insana_aurea.criar_estado_insana(upgrades.get("Insana", 0), pygame.time.get_ticks())
        estado_voraz = voraz_aurea.criar_estado_voraz(upgrades.get("Voraz", 0), pygame.time.get_ticks())
        estado_aureas_avancadas = aureas_avancadas.criar_estado(upgrades, aurea, pygame.time.get_ticks())
        globals()["estado_aureas_avancadas"] = estado_aureas_avancadas

        if aurea == "Devota":
            escudo_devota_ativo = True
            intervalo_escudo = max(8000, 22000 - (nivel_devota * 2500))
            estado_devota.clear()
            estado_devota.update(criar_estado_devota(True, pygame.time.get_ticks()))
        else:
            escudo_devota_ativo = False
            estado_devota.clear()
            estado_devota.update(criar_estado_devota(False))

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
            voraz_aurea.criar_fragmento_abate(estado_voraz, aurea, inimigo["rect"].center, pygame.time.get_ticks(), 1)
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
        # Cache do joystick (evita re-init a cada frame)
        joystick_count = pygame.joystick.get_count()
        if joystick_count > 0:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
        else:
            joystick = None

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
                    "pontuacao_magia": pontuacao_magia,
                    "inimigos_eliminados": inimigos_eliminados,
                    "nivel_ameaca": nivel_ameaca,
                    "vida_inimigo_maxima": vida_inimigo_maxima,
                    "max_inimigos": max_inimigos2,
                    "tempo_cronometro": Variaveis.obter_tempo_decorrido(),
                    "inimigos_comum": Variaveis.serializar_inimigos_rewind(inimigos_comum),
                    "vida_boss": vida_boss2,
                    "r_press": bool(r_press)
                }
                Variaveis.registrar_snapshot(snapshot_data, tempo_atual)

            if carregar_atributos_na_fase:
                rewind_aplicado = False
                try:
                    carregar_atributos()
                    if Variaveis.snapshot_para_carregar is not None:
                        snap = Variaveis.snapshot_para_carregar
                        rewind_aplicado = True
                        pos_x_personagem = snap.get("pos_x", pos_x_personagem)
                        pos_y_personagem = snap.get("pos_y", pos_y_personagem)
                        vida = snap.get("vida_fracao", 0.20) * vida_maxima
                        pontuacao = 0
                        pontuacao_exib = 0
                        pontuacao_magia = snap.get("pontuacao_magia", pontuacao_magia)
                        inimigos_eliminados = snap.get("inimigos_eliminados", inimigos_eliminados)
                        nivel_ameaca = snap.get("nivel_ameaca", inimigos_eliminados // 10)
                        vida_inimigo_maxima = snap.get("vida_inimigo_maxima", vida_inimigo_maxima)
                        max_inimigos2 = snap.get("max_inimigos", max_inimigos2)
                        Variaveis.definir_tempo_cronometro(snap.get("tempo_cronometro", Variaveis.obter_tempo_decorrido()))
                        if "inimigos_comum" in snap:
                            inimigos_comum = Variaveis.restaurar_inimigos_rewind(snap.get("inimigos_comum"), frames_inimigo[0])
                        if snap.get("refragmentacao_rewind"):
                            imune_tempo_restante = max(imune_tempo_restante, 4000)
                            piscando_vida = False
                            Variaveis.aplicar_rewind_respawn_visual(pos_x_personagem, pos_y_personagem, direcao_atual, pygame.time.get_ticks())
                        if "vida_boss" in snap and snap["vida_boss"] is not None:
                            vida_boss2 = snap["vida_boss"]
                        if snap.get("r_press"):
                            r_press = True
                        Variaveis.snapshot_para_carregar = None
                except Exception as e:
                    registrar_erro("Fase 2: erro ao carregar atributos; usando padrao", e)
                carregar_atributos_na_fase=False
                
                # Dynamic enemy stat scaling based on loaded player stats
                if not rewind_aplicado:
                    vida_inimigo_maxima = multiplayer_coop.aplicar_multiplicador_vida_inimigo(vida_inimigo_comum_inicial(max(35, int(dano_person_hit * 2.5))))
                    vida_inimigo = vida_inimigo_maxima
                
                dano_inimigo_perto = max(dano_inimigo_perto, Resistencia + 15)
                dano_inimigo_longe = max(dano_inimigo_longe, Resistencia // 2 + 10)
                
                velocidade_inimigo2 = max(1.70, velocidade_personagem * 0.55)
                velocidade_disparo_inimigo = max(3.0, velocidade_personagem * 0.9)
                
                # Boss 2 scaling
                if not rewind_aplicado:
                    vida_boss2 = multiplayer_coop.aplicar_multiplicador_vida_boss(max(vida_inicial_boss(2, 8000), int(dano_person_hit * 120 * 1.75)))
                    vida_maxima_boss2 = vida_boss2

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


            pos_mouse = obter_pos_mouse_jogo()
            botao_mouse = pygame.mouse.get_pressed()
            mouse_x = max(0, min(pos_mouse[0], largura_mapa - cursor_tamanho[0]))
            mouse_y = max(0, min(pos_mouse[1], altura_mapa - cursor_tamanho[1]))
            pausa_por_fuga_mouse = Variaveis.deve_pausar_por_fuga_mouse(pos_mouse, largura_mapa, altura_mapa)
            fase_coop = multiplayer_coop.atualizar(2, pos_x_personagem, pos_y_personagem, direcao_atual, vida, vida_maxima, vida <= 0)
            if multiplayer_coop.aplicar_transicao_recebida(fase_coop, game_manager):
                raise CleanExit()
            mundo_coop = multiplayer_coop.sincronizar_mundo(
                2,
                inimigos_comum,
                criar_inimigo,
                boss={
                    "vida": vida_boss2,
                    "vida_maxima": vida_maxima_boss2,
                    "vivo": boss_vivo2,
                    "r_press": r_press,
                    "x": pos_x_chefe2,
                    "y": pos_y_chefe2,
                },
                economia={
                    "pontuacao": pontuacao,
                    "pontuacao_exib": pontuacao_exib,
                    "pontuacao_magia": pontuacao_magia,
                    "tempo_cronometro": Variaveis.obter_tempo_decorrido(),
                },
            )
            if mundo_coop:
                boss_coop = mundo_coop.get("boss", {})
                economia_coop = mundo_coop.get("economia", {})
                vida_boss2 = boss_coop.get("vida", vida_boss2)
                vida_maxima_boss2 = boss_coop.get("vida_maxima", vida_maxima_boss2)
                boss_vivo2 = bool(boss_coop.get("vivo", boss_vivo2))
                r_press_anterior = r_press
                r_press = bool(boss_coop.get("r_press", r_press))
                if r_press and not r_press_anterior:
                    boss_entrada_ativa = True
                    boss_entrada_tempo_inicio = pygame.time.get_ticks()
                    tempo_boss_entrada_fim = boss_entrada_tempo_inicio + 2500
                    boss_impacto_feito = False
                    ice_shards = []
                    ondas_nevasca = []
                    ondas_nevasca_preparadas = []
                pos_x_chefe2 = boss_coop.get("x", pos_x_chefe2)
                pos_y_chefe2 = boss_coop.get("y", pos_y_chefe2)
                pontuacao = economia_coop.get("pontuacao", pontuacao)
                pontuacao_exib = economia_coop.get("pontuacao_exib", pontuacao_exib)
                pontuacao_magia = economia_coop.get("pontuacao_magia", pontuacao_magia)
                if "tempo_cronometro" in economia_coop:
                    Variaveis.definir_tempo_cronometro(economia_coop.get("tempo_cronometro", Variaveis.obter_tempo_decorrido()))

            multiplayer_coop.processar_eventos_visuais(2, efeitos_texto, ondas_choque, gerar_particulas_pontos)
            for event in pygame.event.get():
                Variaveis.atualizar_estado_mouse(event)
                Variaveis.processar_eventos_teleporte(event, cooldown_dash)
                if Variaveis.evento_deve_pausar_por_fuga_mouse(event):
                    pausa_por_fuga_mouse = True
                    jogo_pausado = True
                if event.type == pygame.QUIT:
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.SAIR)
                        raise CleanExit()
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if multiplayer_coop.modo_multiplayer():
                        multiplayer_coop.solicitar_acao("pause", 2)
                    else:
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
                elif Variaveis.verificar_evento_input(event, "Habilidade Onda") and tempo_atual - tempo_ultimo_uso_habilidade >= cooldown_habilidade * voraz_aurea.bonus_cooldown(estado_voraz, aurea) * parasitica_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * lacerante_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * condutora_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa):
                    pos_mouse = obter_pos_mouse_jogo()
                    px_centro = pos_x_personagem + largura_personagem // 2
                    py_centro = pos_y_personagem + altura_personagem // 2
                    angulo = calcular_angulo_disparo((px_centro, py_centro), pos_mouse)

                    if ancorada_manifestacao.ativa(manifestacao_ativa):
                        ondas.append(ancorada_manifestacao.criar_dominio_fixo(
                            px_centro, py_centro, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual)
                        ))
                        cooldown_dash = True
                        tempo_ultimo_dash = max(tempo_ultimo_dash, tempo_atual)
                    elif gravitante_manifestacao.ativa(manifestacao_ativa):
                        ondas.append(gravitante_manifestacao.criar_colapso_orbital(
                            px_centro, py_centro, tempo_atual,
                            dano_person_hit * fator_dano_aureas(tempo_atual), largura_mapa, altura_mapa
                        ))
                    elif condutora_manifestacao.ativa(manifestacao_ativa):
                        jogador_rect_temp = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                        mortos_circuito, total_alvos, total_links = condutora_manifestacao.fechar_circuitos(
                            inimigos_comum, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto, jogador_rect_temp
                        )
                        ondas.append(condutora_manifestacao.criar_fechamento(px_centro, py_centro, tempo_atual, total_alvos, total_links))
                        for morto_circuito in mortos_circuito:
                            if morto_circuito in inimigos_comum:
                                gerar_fragmentos_morte(morto_circuito, 2)
                                Variaveis.tentar_soltar_carta(morto_circuito["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                                inimigos_comum.remove(morto_circuito)
                                inimigos_eliminados += 1
                    elif parasitica_manifestacao.ativa(manifestacao_ativa):
                        mortos_eclosao, total_eclosao = parasitica_manifestacao.eclodir_todas(inimigos_comum, tempo_atual, efeitos_texto)
                        ondas.append(parasitica_manifestacao.criar_eclosao(px_centro, py_centro, tempo_atual, total_eclosao))
                        for morto_eclosao in mortos_eclosao:
                            if morto_eclosao in inimigos_comum:
                                gerar_fragmentos_morte(morto_eclosao, 2)
                                Variaveis.tentar_soltar_carta(morto_eclosao["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                                inimigos_comum.remove(morto_eclosao)
                                inimigos_eliminados += 1
                    elif retornante_manifestacao.ativa(manifestacao_ativa):
                        total_chamado = retornante_manifestacao.chamado_reverso(disparos, tempo_atual)
                        ondas.append(retornante_manifestacao.criar_chamado(px_centro, py_centro, tempo_atual, total_chamado))
                    elif prismatica_manifestacao.ativa(manifestacao_ativa):
                        ondas.append(prismatica_manifestacao.criar_prisma(
                            pos_mouse[0], pos_mouse[1], tempo_atual,
                            dano_person_hit * fator_dano_aureas(tempo_atual), largura_mapa, altura_mapa
                        ))
                    elif lacerante_manifestacao.ativa(manifestacao_ativa):
                        ondas.append(lacerante_manifestacao.criar_fenda(px_centro, py_centro, angulo, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual)))
                    else:
                        # Criar uma onda cinética com as novas propriedades
                        nova_onda = {
                            "rect": pygame.Rect(px_centro - largura_onda // 2, py_centro - altura_onda // 2, largura_onda, altura_onda),
                            "angulo": angulo,
                            "tempo_inicio": pygame.time.get_ticks(),
                            "frame_atual": 0,
                            "frames": frames_onda_cinetica  # Certifique-se de ter os frames para animação da onda
                        }
                        ondas.append(nova_onda)
                        aplicar_coice_onda(coice_onda, angulo)
                    if condutora_manifestacao.ativa(manifestacao_ativa):
                        cooldown_base_condutora = cooldown_habilidade * voraz_aurea.bonus_cooldown(estado_voraz, aurea) * parasitica_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * lacerante_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * condutora_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa)
                        tempo_ultimo_uso_habilidade = condutora_manifestacao.ajustar_inicio_cooldown_registrador(tempo_atual, cooldown_base_condutora)
                    else:
                        tempo_ultimo_uso_habilidade = tempo_atual


            # Verificar eventos de teclado
            # --- Tela de pausa (ESC) ---
            if multiplayer_coop.acao_confirmada("pause", 2):
                jogo_pausado = True
                pausar_cronometro()
                pygame.event.set_grab(False)
                pygame.mouse.set_visible(True)
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
                    registrar_erro("Fase 2: erro ao salvar atributos para pausa", e)
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
                multiplayer_coop.aguardar_barreira("pause_saida", 2, tela, fonte, "Aguardando o outro jogador voltar do pause...")
                pygame.event.set_grab(True)
                pygame.mouse.set_visible(False)
                jogo_pausado = False
                continue

            if not pausa_por_fuga_mouse and botao_mouse[0] and not condutora_manifestacao.disparo_bloqueado_registrador(manifestacao_ativa, tempo_atual) and not disparo_preparando and tempo_atual - tempo_ultimo_disparo >= ancorada_manifestacao.intervalo_disparo_ancorado(intervalo_disparo_racional(intervalo_disparo, aurea, racional_dilatacao_fim, tempo_atual), manifestacao_ativa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, tempo_atual):
                pos_mouse = obter_pos_mouse_jogo()
                px_centro = pos_x_personagem + largura_personagem // 2
                py_centro = pos_y_personagem + altura_personagem // 2
                angulo_disparo_preparado = calcular_angulo_disparo((px_centro, py_centro), pos_mouse)
                disparo_preparando = True
                disparo_frame_atual = 0
                tempo_ultimo_frame_preparo_disparo = tempo_atual
                direcao_atual = 'disp'
                frame_atual = 0

            keys = pygame.key.get_pressed()

            # Verificar eventos de joystick de forma dinâmica e eficiente
            joystick_count = pygame.joystick.get_count()
            if joystick_count > 0:
                if joystick is None:
                    joystick = pygame.joystick.Joystick(0)
                    joystick.init()
            else:
                joystick = None

            # Chamar a função para atualizar a posição do personagem
            ultimo_x = pos_x_personagem
            ultimo_y = pos_y_personagem
            atualizar_posicao_personagem(keys,joystick)
            if condutora_manifestacao.disparo_bloqueado_registrador(manifestacao_ativa, tempo_atual):
                disparo_preparando = False

            if disparo_preparando:
                direcao_atual = 'disp'
                frame_atual = disparo_frame_atual
            pos_x_personagem, pos_y_personagem = atualizar_coice_onda(
                pos_x_personagem, pos_y_personagem,
                largura_personagem, altura_personagem,
                largura_mapa, altura_mapa,
                coice_onda,
                dt,
            )



            novos_inimigos = []
            novos_disparos = []
            inimig_atin=[]

            # --- PARTÍCULAS DE VENENO PINGANDO ---
            Variaveis.atualizar_e_desenhar_particulas_veneno(tela, inimigos_comum, config_graficos)
            for inimigo in inimigos_comum:
                inimigo_rect = inimigo["rect"]
                inimigo_image = inimigo["image"]

                inimigo_atingido = False

                for disparo in disparos:

                    if (
                        retornante_manifestacao.colisao_alvo(disparo, inimigo)
                        if disparo.get("tipo_manifestacao") == "retornante_pulso"
                        else verificar_colisao_disparo_inimigo(disparo, (inimigo["rect"].x, inimigo["rect"].y), largura_disparo, altura_disparo, inimigo["rect"].width, inimigo["rect"].height, inimigos_eliminados)
                    ):
                        if random.random() <= chance_critico:  # 10% de chance de dano crítico
                            dano = dano_person_hit * fator_dano_aureas(tempo_atual) * 3  # Valor do dano crítico é 3 vezes o dano normal
                            cor = (255, 255, 0)  # Amarelo (RGB)
                            fonte_dano=fonte_dano_critico
                        else:
                            dano = dano_person_hit * fator_dano_aureas(tempo_atual)
                            cor = (255, 0, 0)  # Vermelho (RGB)
                            fonte_dano=fonte_dano_normal
                        if Petro_active:    
                            if vida_petro > vida_maxima_petro :
                                vida_petro+= (vida_maxima_petro-vida_petro) *0.25
                        acerto_prismatico = prismatica_manifestacao.registrar_acerto(disparo, inimigo, tempo_atual)
                        if acerto_prismatico["critico"]:
                            dano *= prismatica_manifestacao.FEIXE_CRITICO_MULT
                            cor = (235, 255, 255)
                            fonte_dano = fonte_dano_critico
                        acerto_retornante = retornante_manifestacao.registrar_acerto(
                            disparo,
                            inimigo,
                            tempo_atual,
                            (pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2),
                        )
                        if acerto_retornante["critico"]:
                            dano *= retornante_manifestacao.PULSO_CRITICO_COSTAS_MULT
                            cor = (235, 225, 255)
                            fonte_dano = fonte_dano_critico
                        dano *= insana_aurea.dano_mult_disparo(disparo)
                        dano *= voraz_aurea.dano_mult_disparo(disparo)
                        dano *= lacerante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= prismatica_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= retornante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= parasitica_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= condutora_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= gravitante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= ancorada_manifestacao.multiplicador_dano_disparo(disparo)
                        dano = aureas_avancadas.aplicar_dano_inimigo(
                            estado_aureas_avancadas, aurea, inimigo, disparo, dano,
                            tempo_atual, efeitos_texto, inimigos_comum
                        )

                        # Renderize o texto do dano
                        texto_hit = "-" + str(int(dano))
                        pos_texto = (inimigo["rect"].x + inimigo["rect"].width // 2 - fonte_dano.size(texto_hit)[0] // 2, inimigo["rect"].y - 20)
                        Variaveis.registrar_efeito_texto(
                            efeitos_texto,
                            texto_hit,
                            pos_texto[0],
                            pos_texto[1],
                            tempo_atual,
                            cor,
                            chave=("disparo-inimigo", id(disparo), id(inimigo)),
                        )
                        # Rastreie o tempo de exibição do texto
                        tempo_texto_dano = pygame.time.get_ticks()
                        inimigo["vida"] -= dano
                        multiplayer_coop.enviar_dano_inimigo(inimigo, dano, origem="disparo")
                        if disparo.get("tipo_manifestacao") == "parasitica_semente":
                            parasitica_manifestacao.implantar_semente(
                                inimigo, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto
                            )
                        if disparo.get("tipo_manifestacao") == "condutora_fio":
                            condutora_manifestacao.registrar_acerto_logico(
                                inimigo, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto,
                                inimigos=inimigos_comum
                            )
                        if disparo.get("tipo_manifestacao") == "gravitante_orbe":
                            gravitante_manifestacao.ancorar_orbe(
                                inimigo, disparo, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto, inimigos=inimigos_comum
                            )
                        if disparo.get("tipo_manifestacao") == "lacerante_corte":
                            lacerante_manifestacao.aplicar_laceracao(inimigo, tempo_atual)
                        if not (acerto_prismatico["manter_disparo"] or acerto_retornante["manter_disparo"]):
                            estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)  # Remover o disparo após colisão

                        if Poison_Active:
                            aplicar_veneno(inimigo, tempo_atual, cartas_compradas.get("Poison", 0))


                        if quantidade_roubo_vida > 0:
                            vida += (vida_maxima-vida)*quantidade_roubo_vida
                        if Ultimo_Estalo and inimigo["vida"] <= Executa_inimigo * inimigo["vida_maxima"]:
                            insana_aurea.notificar_abate_insana(estado_insana, aurea, disparo)
                            bonus_aurea, reducao_habilidade = aureas_avancadas.aplicar_recompensa_abate(
                                estado_aureas_avancadas, aurea, inimigo, tempo_atual, efeitos_texto
                            )
                            pontuacao += bonus_aurea
                            pontuacao_exib += bonus_aurea
                            tempo_ultimo_uso_habilidade += reducao_habilidade
                            if inimigo in inimigos_comum:
                                gerar_fragmentos_morte(inimigo, 2)
                                if inimigo.get("elite", False):
                                    # Frost Nova!
                                    zonas_lentidao.append({
                                        "pos": inimigo["rect"].center,
                                        "raio": 95,
                                        "duracao": 5000,
                                        "tempo_inicio": pygame.time.get_ticks()
                                    })
                                if inimigo.get("tipo", "comum") == "kamikaze":
                                    trigger_kamikaze_explosion(inimigo)
                                inimigos_comum.remove(inimigo)
                            if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                largura_disparo += 0.095
                                altura_disparo += 0.095
                            posicao_inimigo = inimigo["rect"].center
                            soltar_moeda(posicao_inimigo)
                            Variaveis.tentar_soltar_carta(posicao_inimigo, tempo_atual, Chance_Sorte, inimigos_eliminados)
                            if inimigo.get("elite", False):
                                soltar_moeda(posicao_inimigo) # double coins!
                            inimigos_eliminados += 1
                            ganho_pontos = int(150 * (1 + math.log10(inimigos_eliminados + 1)))
                            # Execução oferece um prêmio de escala superior (15%)
                            mult_ex = 1.0 + (nivel_ameaca * 0.15)

                            vida_inimigo_maxima += ganho_vida_inimigo_comum(0.7 * mult_ex)
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
                                vida_boss2 += ganho_progressao_boss(20 * mult_ex)
                                vida_maxima_boss2 = vida_boss2
                                vida_boss3 += ganho_progressao_boss(25 * mult_ex)
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += ganho_progressao_boss(30 * mult_ex)
                                vida_maxima_boss4 = vida_boss4

                            if vida_petro < vida_maxima_petro:
                                vida_petro += (vida_maxima_petro - vida_petro) * 0.25

                        # Quando o inimigo morre normalmente
                        elif inimigo["vida"] <= 0:
                            insana_aurea.notificar_abate_insana(estado_insana, aurea, disparo)
                            bonus_aurea, reducao_habilidade = aureas_avancadas.aplicar_recompensa_abate(
                                estado_aureas_avancadas, aurea, inimigo, tempo_atual, efeitos_texto
                            )
                            pontuacao += bonus_aurea
                            pontuacao_exib += bonus_aurea
                            tempo_ultimo_uso_habilidade += reducao_habilidade
                            posicao_inimigo = inimigo["rect"].center
                            soltar_moeda(posicao_inimigo)
                            Variaveis.tentar_soltar_carta(posicao_inimigo, tempo_atual, Chance_Sorte, inimigos_eliminados)
                            if inimigo.get("elite", False):
                                soltar_moeda(posicao_inimigo) # double coins!
                                # Frost Nova!
                                zonas_lentidao.append({
                                    "pos": inimigo["rect"].center,
                                    "raio": 95,
                                    "duracao": 5000,
                                    "tempo_inicio": pygame.time.get_ticks()
                                })
                            gerar_fragmentos_morte(inimigo, 2)
                            if inimigo.get("tipo", "comum") == "kamikaze":
                                trigger_kamikaze_explosion(inimigo)
                            inimigos_comum.remove(inimigo)
                            if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                largura_disparo += 0.095
                                altura_disparo += 0.095
                            inimigos_eliminados += 1

                            # --- ESCALONAMENTO RECALIBRADO PARA 20 MINUTOS ---
                            mult = 1.0 + (nivel_ameaca * 0.12)

                            vida_inimigo_maxima += ganho_vida_inimigo_comum(0.6 * mult)
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
                                incremento_v = ganho_progressao_boss(15 * mult)
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

            tempo_passado += relogio.get_rawtime()
            relogio.tick()

             # Adicionar inimigos a cada 10 segundos
            tempo_atual = pygame.time.get_ticks()
            tempo_decorrido_run = Variaveis.obter_tempo_decorrido()
            limite_inimigos_run = max_inimigos2 + bonus_limite_inimigos_sem_boss(
                tempo_decorrido_run,
                r_press or boss_vivo2,
                inimigos_eliminados,
                modo_dificil=Variaveis.obter_modo_cartas() == "drops",
            )
            pressao_spawn = calcular_pressao_spawn_pos_boss(
                pressao_pos_boss_spawn,
                tempo_atual,
                r_press and not boss_vivo2,
                len(inimigos_comum),
                inimigos_eliminados,
                limite_inimigos_run,
            )
            if tempo_atual - tempo_ultimo_inimigo >= pressao_spawn["intervalo_ms"] and pressao_spawn["lote"] > 0 and (spawn_inimigo or not boss_vivo2):
                for _ in range(pressao_spawn["lote"]):
                    gerar_inimigo(pressao_spawn["limite"])
                tempo_ultimo_inimigo = tempo_atual  # Atualizar o tempo do último inimigo adicionado
            nivel_racional = upgrades.get("Racional", 0)    
            #LUGAR AONDE COLOCAMOS AS AUREAS
            if aurea == "Racional":
                if personagem_racional_imovel(pos_x_personagem, pos_y_personagem, ultimo_x, ultimo_y):
                    if tempo_atual - tempo_parado_person >= RACIONAL_PASSIVA_INTERVALO_MS:
                        ganho = ganho_passiva_racional(nivel_racional)
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
            chave_direcao_animacao = direcao_atual
            if direcao_atual == 'disp':
                chave_direcao_animacao = 'disp_left' if math.cos(angulo_disparo_preparado) < 0 else 'disp_right'
            if chave_direcao_animacao != ultima_direcao_animacao:
                frame_atual = 0
                tempo_passado = 0
                ultima_direcao_animacao = chave_direcao_animacao

            if direcao_atual == 'stop':
                if tempo_passado >= tempo_animacao_stop:
                    tempo_passado = 0
                    frame_atual = (frame_atual + 1) % len(frames_animacao[direcao_atual])
            if direcao_atual != 'stop':
                if tempo_passado >= tempo_animacao_no_stop:
                    tempo_passado = 0
                    frame_atual = (frame_atual + 1) % len(frames_animacao[direcao_atual])

            if disparo_preparando:
                direcao_atual = 'disp'
                if tempo_atual - tempo_ultimo_frame_preparo_disparo >= DISPARO_PREPARO_FRAME_MS:
                    tempo_ultimo_frame_preparo_disparo = tempo_atual
                    disparo_frame_atual += 1
                frame_atual = min(disparo_frame_atual, len(frames_animacao['disp']) - 1)

                if disparo_frame_atual >= len(frames_animacao['disp']):
                    px_centro = pos_x_personagem + largura_personagem // 2
                    py_centro = pos_y_personagem + altura_personagem // 2
                    largura_tiro, altura_tiro = voraz_aurea.dimensoes_disparo(estado_voraz, aurea, largura_disparo, altura_disparo)
                    disparo_novo = ancorada_manifestacao.criar_auto_attack(manifestacao_ativa, vfx_disparo_player,
                        px_centro, py_centro, largura_tiro, altura_tiro,
                        angulo_disparo_preparado, velocidade_disparo, tempo_atual, impulsiva_ativa
                    )
                    disparo_novo = aureas_avancadas.marcar_disparo(
                        estado_aureas_avancadas, aurea, disparo_novo, tempo_atual, efeitos_texto
                    )
                    disparos.append(voraz_aurea.marcar_disparo_voraz(estado_voraz, aurea, disparo_novo))
                    insana_aurea.registrar_tiro_insana(
                        estado_insana, aurea, tempo_atual,
                        pos_x_personagem, pos_y_personagem, px_centro, py_centro,
                        angulo_disparo_preparado, largura_tiro, altura_tiro, velocidade_disparo,
                        manifestacao_ativa
                    )
                    tempo_ultimo_disparo = tempo_atual
                    disparo_preparando = False
                    disparo_frame_atual = 0

            # Screen shake update
            if screen_shake > 0:
                screen_shake = max(0, screen_shake - 1)
                shake_x = random.randint(-screen_shake, screen_shake)
                shake_y = random.randint(-screen_shake, screen_shake)
            else:
                shake_x = 0
                shake_y = 0

            tela.fill((255, 255, 255))
            tela.blit(mapa, (shake_x, shake_y))

            # Update and Draw Ice Shards from Boss Entrance Impact
            novos_shards = []
            for shard in ice_shards:
                shard["x"] += shard["vx"] * dt
                shard["y"] += shard["vy"] * dt
                shard["vy"] += 0.25 * dt # gravity!
                shard["vida"] -= 6 * dt
                if shard["vida"] > 0:
                    novos_shards.append(shard)
                    # Draw a translucent ice polygon
                    rx = int(shard["x"]) + shake_x
                    ry = int(shard["y"]) + shake_y
                    sz = int(shard["size"])
                    # Create surface with transparency for color alpha
                    surf_shard = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
                    pygame.draw.polygon(surf_shard, (135, 206, 250, min(255, int(shard["vida"]))), [
                        (sz, 0),
                        (sz * 2, sz),
                        (sz, sz * 2),
                        (0, sz)
                    ])
                    tela.blit(surf_shard, (rx - sz, ry - sz))
            ice_shards = novos_shards

            # Update and Draw Frost Slow Zones
            tempo_atual = pygame.time.get_ticks()
            novas_zonas = []
            jogador_desacelerado = False # Reset every frame, we will check if player is in any active zone
            for zona in zonas_lentidao:
                if tempo_atual - zona["tempo_inicio"] < zona["duracao"]:
                    novas_zonas.append(zona)
                    
                    # Draw translucent ice patch on ground
                    surf_zona = pygame.Surface((zona["raio"] * 2, zona["raio"] * 2), pygame.SRCALPHA)
                    pygame.draw.circle(surf_zona, (0, 191, 255, 45), (zona["raio"], zona["raio"]), zona["raio"])
                    pygame.draw.circle(surf_zona, (173, 216, 230, 75), (zona["raio"], zona["raio"]), int(zona["raio"] * 0.7))
                    pygame.draw.circle(surf_zona, (240, 248, 255, 120), (zona["raio"], zona["raio"]), zona["raio"], 2)
                    
                    tela.blit(surf_zona, (zona["pos"][0] - zona["raio"] + shake_x, zona["pos"][1] - zona["raio"] + shake_y))
                    
                    # Check collision with player center
                    px = pos_x_personagem + largura_personagem // 2
                    py = pos_y_personagem + altura_personagem // 2
                    dist_to_player = math.sqrt((px - zona["pos"][0]) ** 2 + (py - zona["pos"][1]) ** 2)
                    if dist_to_player <= zona["raio"]:
                        jogador_desacelerado = True
            zonas_lentidao = novas_zonas

            # Update and Draw Snow Trails (rastros_neve)
            novos_rastros = []
            for rastro in rastros_neve:
                rastro["life"] -= rastro["decay"]
                if rastro["life"] > 0:
                    novos_rastros.append(rastro)
                    # Draw a fading soft white circle
                    alpha = int(140 * rastro["life"])
                    surf_rastro = pygame.Surface((rastro["raio"] * 2, rastro["raio"] * 2), pygame.SRCALPHA)
                    pygame.draw.circle(surf_rastro, (255, 255, 255, alpha), (rastro["raio"], rastro["raio"]), rastro["raio"])
                    # Draw a slightly blue/ice inner center
                    pygame.draw.circle(surf_rastro, (200, 230, 255, int(alpha * 0.5)), (rastro["raio"], rastro["raio"]), int(rastro["raio"] * 0.6))

                    tela.blit(surf_rastro, (rastro["pos"][0] - rastro["raio"] + shake_x, rastro["pos"][1] - rastro["raio"] + shake_y))

                    # Check collision with player
                    px = pos_x_personagem + largura_personagem // 2
                    py = pos_y_personagem + altura_personagem // 2
                    dist_to_player = math.sqrt((px - rastro["pos"][0]) ** 2 + (py - rastro["pos"][1]) ** 2)
                    if dist_to_player <= rastro["raio"]:
                        jogador_desacelerado = True
            rastros_neve = novos_rastros

            # Update and Draw Ice Block Particles (ice_blocks_particles)
            novas_particulas = []
            for p in ice_blocks_particles:
                p["life"] -= p["decay"]
                if p["life"] > 0:
                    novas_particulas.append(p)
                    # Update physics
                    p["pos"][0] += p["vel"][0]
                    p["pos"][1] += p["vel"][1]
                    p["vel"][0] *= 0.95 # friction
                    p["vel"][1] *= 0.95
                    p["rot"] += p["rot_vel"]

                    # Draw a rotated square/polygon for ice block
                    sz = p["size"]
                    alpha = int(255 * p["life"])
                    # Create a surface for the block
                    surf_p = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
                    # Draw ice block inside surface
                    color_ice = (200, 240, 255, alpha)
                    pygame.draw.rect(surf_p, color_ice, (sz // 2, sz // 2, sz, sz))
                    pygame.draw.rect(surf_p, (255, 255, 255, int(alpha * 0.8)), (sz // 2, sz // 2, sz, sz), 1)

                    # Rotate the surface
                    rot_p = pygame.transform.rotate(surf_p, p["rot"])
                    rot_rect = rot_p.get_rect(center=(p["pos"][0] + shake_x, p["pos"][1] + shake_y))
                    tela.blit(rot_p, rot_rect.topleft)
            ice_blocks_particles = novas_particulas


            # Desenha a personagem
            # Desenhar sombra do personagem
            desenhar_sombra(tela, pos_x_personagem + shake_x, pos_y_personagem + shake_y, largura_personagem, altura_personagem)
            if not personagem_imovel:
                frames_local = multiplayer_coop.frames_jogador_local(frames_animacao, frames_animacao2)
                if direcao_atual == 'disp' and lacerante_manifestacao.ativa(manifestacao_ativa):
                    estagio = lacerante_manifestacao.obter_proximo_estagio()
                    idx = estagio * 2 + (frame_atual % 2)
                    if idx < len(Variaveis.frames_lacerar):
                        frame_para_desenhar = Variaveis.frames_lacerar[idx]
                    else:
                        frame_para_desenhar = frames_local[direcao_atual][frame_atual % len(frames_local[direcao_atual])]
                else:
                    frame_para_desenhar = frames_local[direcao_atual][frame_atual % len(frames_local[direcao_atual])]
                if direcao_atual == 'disp' and math.cos(angulo_disparo_preparado) < 0:
                    frame_para_desenhar = pygame.transform.flip(frame_para_desenhar, True, False)
                if angulo_inclinacao_personagem != 0:
                    # Rotaciona o frame pelo centro para manter o eixo
                    frame_rotacionado = pygame.transform.rotate(frame_para_desenhar, angulo_inclinacao_personagem)
                    novo_rect = frame_rotacionado.get_rect(center=(pos_x_personagem + largura_personagem//2 + shake_x, pos_y_personagem + altura_personagem//2 + shake_y))
                    desenhar_personagem_com_dano(tela, frame_rotacionado, novo_rect.x, novo_rect.y, tempo_atual, tempo_ultimo_hit_inimigo)
                else:
                    w_f, h_f = frame_para_desenhar.get_size()
                    bx = pos_x_personagem + (largura_personagem - w_f) // 2 + shake_x
                    by = pos_y_personagem + (altura_personagem - h_f) + shake_y
                    desenhar_personagem_com_dano(tela, frame_para_desenhar, bx, by, tempo_atual, tempo_ultimo_hit_inimigo)
            else:
                desenhar_personagem_com_dano(tela, imagem_personagem_congelada, pos_x_personagem + shake_x, pos_y_personagem + shake_y, tempo_atual, tempo_ultimo_hit_inimigo)

            insana_aurea.desenhar_insana(
                tela, estado_insana, aurea, tempo_atual,
                pos_x_personagem + shake_x, pos_y_personagem + shake_y,
                largura_personagem, altura_personagem, config_graficos
            )
            aureas_avancadas.desenhar(
                tela, estado_aureas_avancadas, aurea, tempo_atual,
                pos_x_personagem + shake_x, pos_y_personagem + shake_y,
                largura_personagem, altura_personagem, inimigos_comum, config_graficos
            )
            multiplayer_coop.desenhar_jogador_remoto(tela, 2, frame_atual, frames_animacao, frames_animacao2)

            # Desenhar zona de teleporte (se estiver mirando no modo mouse)
            Variaveis.desenhar_zona_teleporte(tela, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, distancia_dash)

            personagem_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
            for moeda in moedas_soltadas[:]:
                if personagem_rect.colliderect(moeda["rect"]):
                    moedas_coletadas += 1
                    moedas_totais += 1   # 🪙 acumula no total salvo
                    moedas_soltadas.remove(moeda)
                    salvar_atributos()   # 💾 salva imediatamente


            efeitos_texto = Variaveis.atualizar_e_desenhar_efeitos_texto(tela, tempo_atual, efeitos_texto, config_graficos)

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
                            # Resistência mitigando o dano recebido
                            dano_real = max(0, dano_inimigo_perto - Resistencia_petro)
                            vida_petro -= int(dano_real)

                            # Dano da Petro escala com o poder do Personagem
                            inimigo_mais_proximo["vida"] -= int(dano_person_hit * 0.008) + dano_petro
                            tempo_anterior_petro = tempo_atual_petro

                            if inimigo_mais_proximo["vida"] <= 0:
                                # Incrementos controlados por abate direto da Petro
                                vida_inimigo_maxima += ganho_vida_inimigo_comum(0.6)
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
                                    gerar_fragmentos_morte(inimigo_mais_proximo, 2)
                                    Variaveis.tentar_soltar_carta(inimigo_mais_proximo["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                                    if inimigo_mais_proximo.get("tipo", "comum") == "kamikaze":
                                        trigger_kamikaze_explosion(inimigo_mais_proximo)
                                    inimigos_comum.remove(inimigo_mais_proximo)


                            if not boss_vivo2:
                                vida_boss2 += ganho_progressao_boss(20 * mult_ex)
                                vida_maxima_boss2 = vida_boss2
                                vida_boss3 += ganho_progressao_boss(25 * mult_ex)
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += ganho_progressao_boss(30 * mult_ex)
                                vida_maxima_boss4 = vida_boss4



                if vida_petro<=0:
                    Petro_active= False
                    vida_petro+= vida_maxima_petro
                    vida_maxima_petro= vida_petro                     


                if xp_petro == "nivel_1" or xp_petro in (0, 1):
                    petro_nivel=frames_animacao_Petro

                elif xp_petro == "nivel_2" or xp_petro == 2:
                    petro_nivel=frames_animacao_Petro2

                elif xp_petro == "nivel_3" or (isinstance(xp_petro, (int, float)) and xp_petro >= 3):
                    petro_nivel=frames_animacao_Petro3
                else:
                    petro_nivel=frames_animacao_Petro



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
                    pos_x_petro += 1 * direcao_x * dt
                    pos_y_petro += 1 * direcao_y * dt

                    # Verifica se Petro está próximo o suficiente para aplicar dano ao boss
                    distancia_petro_boss = math.sqrt((pos_x_petro - pos_x_chefe2) ** 2 + (pos_y_petro - pos_y_chefe2) ** 2)
                    if distancia_petro_boss <= 50:
                        # Verifica se passou tempo suficiente desde o último dano
                        tempo_atual_petro = pygame.time.get_ticks()
                        if tempo_atual_petro - tempo_anterior_petro >= intervalo_dano_petro:
                            # Aplica dano ao "boss"
                            vida_petro -= int(dano_inimigo_perto)
                            vida_petro += int(vida_maxima_petro - vida_petro) * quantidade_roubo_vida
                            vida_boss2-= dano_boss_mitigado(int(dano_person_hit*0.25)+300, 2, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                            # Aqui você pode adicionar outras ações relacionadas ao dano ao "boss"
                            tempo_anterior_petro = tempo_atual_petro


                if comando_direção_petro:
                    direcao_atual_petro="left_petro"
                    comando_direção_petro=False


                desenhar_barra_de_vida_petro(tela, vida_petro, pos_x_petro, pos_y_petro - 20,vida_maxima_petro) 
                tela.blit(petro_nivel[direcao_atual_petro][frame_atual % len(petro_nivel[direcao_atual_petro])], (pos_x_petro, pos_y_petro))            




            insana_aurea.atualizar_insana(estado_insana, aurea, tempo_atual, disparos, vfx_disparo_player)
            if insana_aurea.consumir_penalidade_dash_insana(estado_insana):
                cooldown_dash = True
                tempo_ultimo_dash = max(tempo_ultimo_dash, tempo_atual + insana_aurea.INSANA_DEBUFF_DASH_MS)

            boss_rect_voraz = pygame.Rect(pos_x_chefe2, pos_y_chefe2, chefe_largura2, chefe_altura2) if (boss_vivo2 and r_press and not boss_entrada_ativa) else None
            aureas_avancadas.atualizar(
                estado_aureas_avancadas, aurea, tempo_atual,
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem,
                inimigos_comum, efeitos_texto, boss_vivo2 and r_press and not boss_entrada_ativa
            )
            vida, _ = voraz_aurea.atualizar_voraz(
                estado_voraz, aurea, tempo_atual,
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem,
                boss_rect=boss_rect_voraz, vida=vida, vida_maxima=vida_maxima,
                efeitos_texto=efeitos_texto
            )
            vida, _ = voraz_aurea.aplicar_custo_fome(estado_voraz, aurea, tempo_atual, vida, vida_maxima)
            vida, _, mortos_voraz = voraz_aurea.aplicar_passiva_em_inimigos(
                estado_voraz, aurea, tempo_atual,
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem,
                inimigos_comum, efeitos_texto, dano_person_hit * fator_dano_aureas(tempo_atual),
                fator_tempo=dt, vida=vida, vida_maxima=vida_maxima
            )
            for morto_voraz in mortos_voraz:
                if morto_voraz in inimigos_comum:
                    gerar_fragmentos_morte(morto_voraz, 2)
                    Variaveis.tentar_soltar_carta(morto_voraz["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                    inimigos_comum.remove(morto_voraz)
                    inimigos_eliminados += 1
            if boss_rect_voraz is not None:
                vida_boss2, vida, _ = voraz_aurea.aplicar_mordida_boss(
                    estado_voraz, aurea, tempo_atual,
                    pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem,
                    boss_rect_voraz, vida_boss2, vida, vida_maxima, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto
                )

            # Desenhar os disparos normais
            novos_disparos = []
            for disparo in disparos:
                vfx_disparo_player.atualizar_disparo(disparo, velocidade_disparo, dt)
                centro_retorno_x = pos_x_personagem + largura_personagem // 2
                centro_retorno_y = pos_y_personagem + altura_personagem // 2

                # Verificar se o disparo está dentro do mapa
                if disparo.get("tipo_manifestacao") == "lacerante_corte":
                    if not disparo.get("expirado"):
                        novos_disparos.append(disparo)
                elif disparo.get("tipo_manifestacao") == "retornante_pulso":
                    if retornante_manifestacao.atualizar_disparo(disparo, centro_retorno_x, centro_retorno_y, dt, tempo_atual):
                        novos_disparos.append(disparo)
                elif disparo.get("tipo_manifestacao") == "prismatica_feixe":
                    if prismatica_manifestacao.atualizar_ricochete(disparo, largura_mapa, altura_mapa, tempo_atual):
                        novos_disparos.append(disparo)
                elif 0 <= disparo["rect"].x < largura_mapa and 0 <= disparo["rect"].y < altura_mapa:
                    novos_disparos.append(disparo)

            disparos = novos_disparos

            # Renderizar os disparos
            for disparo in disparos:
                vfx_disparo_player.desenhar_disparo(tela, disparo, tempo_atual, config_graficos, (shake_x, shake_y))
            vfx_disparo_player.atualizar_e_desenhar_particulas(tela, dt, config_graficos, (shake_x, shake_y))

            boss_info = {
                "vivo": boss_vivo2,
                "rect": pygame.Rect(pos_x_chefe2, pos_y_chefe2, chefe_largura2, chefe_altura2) if (boss_vivo2 and r_press and not boss_entrada_ativa) else None,
                "atingido_por_onda": boss_atingido_por_onda,
                "hit_flag": False
            }
            inimigos_mortos_neste_frame = processar_habilidade_onda(
                ondas, correntes_eletricas, inimigos_comum, boss_info, tela, dt, tempo_atual, largura_mapa, altura_mapa, velocidade_onda, disparos, config_graficos
            )
            if boss_info.get("hit_flag"):
                dano_onda = boss_info.get("dano_manifestacao", dano_person_hit * fator_dano_aureas(tempo_atual) * 2)
                if boss_escudo_ativo:
                    dano_onda = max(1, int(dano_onda * 0.1))
                dano_onda_real = dano_boss_mitigado(dano_onda, 2, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                vida_boss2 -= dano_onda_real
                registrar_dano_boss(efeitos_texto, dano_onda_real, pos_x_chefe2 + chefe_largura2 // 2, pos_y_chefe2 - 22, tempo_atual, (180, 255, 255))
                boss_atingido_por_onda = boss_info["atingido_por_onda"]
                if vida_boss2 <= 0:
                    frame_porcentagem = frames_chefe2_4
                    rect_boss = pygame.Rect(pos_x_chefe2, pos_y_chefe2, 64, 64)
                    rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                    ataque_vertical_ativo = False
                    ataque_horizontal_ativo = False
                    if rect_boss.colliderect(rect_personagem):
                        if toque == 0:
                            registrar_conclusao_fase(2)
                            salvar_atributos()
                            Musica_tema_Boss2.stop()
                            pausar_cronometro()
                            tela_transicao_dimensional(tela, 3)
                            multiplayer_coop.enviar_transicao_fase(3)
                            if game_manager:
                                from game_manager import EstadoJogo
                                game_manager.mudar_estado(EstadoJogo.JOGO_FASE_3)
                                raise CleanExit()
                            else:
                                import GAME3
                                GAME3.executar_jogo()
                                raise CleanExit()

            # Atualizar e desenhar correntes elétricas
            inimigos_mortos_correntes = atualizar_e_desenhar_correntes(tela, correntes_eletricas, inimigos_comum, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual))
            inimigos_mortos_laceracao = lacerante_manifestacao.atualizar_laceracoes(inimigos_comum, tempo_atual, efeitos_texto)
            jogador_rect_parasitica = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
            inimigos_mortos_parasitica = parasitica_manifestacao.atualizar_sementes(
                inimigos_comum, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto, jogador_rect_parasitica
            )
            parasitica_manifestacao.desenhar_sementes(tela, inimigos_comum, tempo_atual, config_graficos)
            inimigos_mortos_condutora = condutora_manifestacao.atualizar_circuitos(
                inimigos_comum, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto
            )
            condutora_manifestacao.desenhar_circuitos(tela, inimigos_comum, tempo_atual, config_graficos, manifestacao_ativa, jogador_rect_parasitica)
            inimigos_mortos_gravitante = gravitante_manifestacao.atualizar_orbes(
                inimigos_comum, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto
            )
            gravitante_manifestacao.desenhar_orbes(tela, inimigos_comum, tempo_atual, config_graficos)
            inimigos_mortos_ancorada = ancorada_manifestacao.atualizar_territorio(
                inimigos_comum, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), jogador_rect_parasitica, efeitos_texto
            )
            ancorada_manifestacao.aplicar_lentidao_projeteis(disparos_inimigos, tempo_atual)
            ancorada_manifestacao.desenhar_territorios(tela, tempo_atual, config_graficos, jogador_rect_parasitica)
            inimigos_mortos_teleporte = teleporte_manifestacao.atualizar_efeitos_teleporte_manifestacao(
                inimigos_comum, boss_info, disparos, tempo_atual,
                dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto, largura_mapa, altura_mapa,
                jogador_rect_parasitica
            )
            teleporte_manifestacao.desenhar_efeitos_teleporte_manifestacao(tela, tempo_atual, config_graficos)

            inimigos_mortos = inimigos_mortos_neste_frame + inimigos_mortos_correntes + inimigos_mortos_laceracao + inimigos_mortos_parasitica + inimigos_mortos_condutora + inimigos_mortos_gravitante + inimigos_mortos_ancorada + inimigos_mortos_teleporte
            for morto in inimigos_mortos:
                if morto in inimigos_comum:
                    posicao_inimigo = morto["rect"].center
                    soltar_moeda(posicao_inimigo)
                    Variaveis.tentar_soltar_carta(posicao_inimigo, tempo_atual, Chance_Sorte, inimigos_eliminados)
                    if morto.get("elite", False):
                        soltar_moeda(posicao_inimigo) # double coins!
                        # Frost Nova!
                        zonas_lentidao.append({
                            "pos": posicao_inimigo,
                            "raio": 95,
                            "duracao": 5000,
                            "tempo_inicio": pygame.time.get_ticks()
                        })
                    gerar_fragmentos_morte(morto, 2)
                    if morto.get("tipo", "comum") == "kamikaze":
                        trigger_kamikaze_explosion(morto)
                    inimigos_comum.remove(morto)
                    nivel_ameaca = min(inimigos_eliminados // 10, 100)
                    vida_inimigo_maxima += ganho_vida_inimigo_comum(1.2 + nivel_ameaca * 0.8)
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
                        vida_boss2 += ganho_progressao_boss(20 + nivel_ameaca * 8)
                        vida_maxima_boss2 = vida_boss2
                        vida_boss3 += ganho_progressao_boss(25 + nivel_ameaca * 10)
                        vida_maxima_boss3 = vida_boss3
                        vida_boss4 += ganho_progressao_boss(30 + nivel_ameaca * 12)
                        vida_maxima_boss4 = vida_boss4



            #MODIFICA O TEMPO QUE OS INIMIGOS DISPARAM REFERENTE O BOSS ESTÁ VIVO OU NÃO                
            if not boss_vivo2:
                intervalo_disparo_inimigo = 3500
            else:
                intervalo_disparo_inimigo = random.randint(1800, 4000) 
            kamikazes_explodidos = []
            for inimigo in inimigos_comum:
                if multiplayer_coop.eh_cliente():
                    continue
                dx = pos_x_personagem - inimigo["rect"].x
                dy = pos_y_personagem - inimigo["rect"].y
                dist = max(40, abs(dx) + abs(dy))
                
                if "pos_x" not in inimigo:
                    inimigo["pos_x"] = float(inimigo["rect"].x)
                if "pos_y" not in inimigo:
                    inimigo["pos_y"] = float(inimigo["rect"].y)

                # Check speed multiplier based on elite status or blizzard
                vel = velocidade_inimigo2
                if inimigo.get("elite", False):
                    vel = velocidade_inimigo2 * 0.90
                if blizzard_ativo:
                    vel *= 1.30 # enemies thrive in snowstorm!
                if inimigo.get("tipo", "comum") == "kamikaze":
                    vel *= 1.6
                vel *= fator_mundo_racional(aurea, racional_dilatacao_fim, tempo_atual)
                
                if r_press:
                    # Flee from player: move in the opposite direction
                    inimigo["pos_x"] -= (dx / dist) * vel * 2.5 * dt
                    inimigo["pos_y"] -= (dy / dist) * vel * 2.5 * dt
                else:
                    inimigo["pos_x"] += (dx / dist) * vel * dt
                    inimigo["pos_y"] += (dy / dist) * vel * dt
                inimigo["rect"].x = int(inimigo["pos_x"])
                inimigo["rect"].y = int(inimigo["pos_y"])

                # Check proximity for kamikaze explosion
                if inimigo.get("tipo", "comum") == "kamikaze" and not r_press:
                    dist_real = math.sqrt(dx**2 + dy**2)
                    if dist_real <= 55:
                        trigger_kamikaze_explosion(inimigo)
                        kamikazes_explodidos.append(inimigo)

            if kamikazes_explodidos:
                inimigos_comum = [im for im in inimigos_comum if im not in kamikazes_explodidos]

            # Resolve colisões e separações entre inimigos e jogador
            if not multiplayer_coop.eh_cliente():
                pos_x_personagem, pos_y_personagem = Variaveis.resolver_colisao_player_com_inimigos(
                    pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, inimigos_comum
                )
                pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem))
                pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem))
            if not multiplayer_coop.eh_cliente():
                Variaveis.resolver_colisoes_e_separacao(inimigos_comum, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)

            lacerante_manifestacao.atualizar_e_desenhar_sangue_lacerante(tela, inimigos_comum, config_graficos)

            for inimigo in inimigos_comum:
                dx = pos_x_personagem - inimigo["rect"].x
                dy = pos_y_personagem - inimigo["rect"].y

                tipo_enemy = inimigo.get("tipo", "comum")
                if dx > 0:  # Mova para a direita
                    if tipo_enemy == "atirador":
                        img_base = frames_atirador_direita[frame_atual % len(frames_atirador_direita)]
                    elif tipo_enemy == "kamikaze":
                        img_base = frames_kamikaze_direita[frame_atual % len(frames_kamikaze_direita)]
                    else:
                        img_base = frames_inimigo_direita2[frame_atual % len(frames_inimigo_direita2)]
                else:  # Mova para a esquerda
                    if tipo_enemy == "atirador":
                        img_base = frames_atirador_esquerda[frame_atual % len(frames_atirador_esquerda)]
                    elif tipo_enemy == "kamikaze":
                        img_base = frames_kamikaze_esquerda[frame_atual % len(frames_kamikaze_esquerda)]
                    else:
                        img_base = frames_inimigo_esquerda2[frame_atual % len(frames_inimigo_esquerda2)]

                # Scale the image if it's elite
                if inimigo.get("elite", False):
                    inimigo_image = pygame.transform.scale(img_base, (inimigo["rect"].width, inimigo["rect"].height))
                else:
                    inimigo_image = img_base
                inimigo["image"] = inimigo_image

                # Desenhar sombra do inimigo using its actual width and height
                desenhar_sombra(tela, inimigo["rect"].x + shake_x, inimigo["rect"].y + shake_y, inimigo["rect"].width, inimigo["rect"].height)
                
                # Draw Elite Aura
                if inimigo.get("elite", False):
                    glow_surf = pygame.Surface((inimigo["rect"].width + 16, inimigo["rect"].height + 16), pygame.SRCALPHA)
                    pygame.draw.ellipse(glow_surf, (0, 191, 255, 60), (0, 0, inimigo["rect"].width + 16, inimigo["rect"].height + 16))
                    tela.blit(glow_surf, (inimigo["rect"].x - 8 + shake_x, inimigo["rect"].y - 8 + shake_y))

                tela.blit(inimigo["image"], (inimigo["rect"].x + shake_x, inimigo["rect"].y + shake_y))
                desenhar_barra_de_vida(tela, inimigo["rect"].x + shake_x, inimigo["rect"].y - 10 + shake_y, inimigo["rect"].width, 5, inimigo["vida"], inimigo["vida_maxima"], inimigo.get("eletrocutado", False), Executa_inimigo if Ultimo_Estalo else None)

                tempo_atual = pygame.time.get_ticks()
                # If Blizzard is active, enemies spawn projectiles faster too!
                shoot_interval = intervalo_disparo_inimigo
                if inimigo.get("elite", False):
                    shoot_interval = int(intervalo_disparo_inimigo * 0.70)
                if blizzard_ativo:
                    shoot_interval = int(shoot_interval * 0.60)

                # Enemies do not fire if they are kamikazes
                if inimigo.get("tipo", "comum") != "kamikaze" and not r_press and tempo_atual - tempo_ultimo_disparo_inimigo >= shoot_interval and random.random() <= 0.25:  #frequencia do disparo do sinimigos
                    disparos_inimigos.append(criar_disparo_inimigo((inimigo["rect"].x, inimigo["rect"].y), (pos_x_personagem, pos_y_personagem), inimigo.get("elite", False), inimigo.get("tipo", "comum")))
                    tempo_ultimo_disparo_inimigo = tempo_atual  # Atualize o tempo do último disparo

            if r_press:
                # Remove enemies that run off-screen
                inimigos_comum[:] = [im for im in inimigos_comum if not (
                    im["pos_x"] < -100 or im["pos_x"] > largura_tela + 100 or
                    im["pos_y"] < -100 or im["pos_y"] > altura_tela + 100
                )]

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

                    if absorver_dano_devota_atual():
                        pass
                    elif imune_tempo_restante <= 0 and Dano_pos_resistencia_person > 0:
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
                restaurar_escudo_devota(estado_devota)
                tempo_ultimo_escudo = tempo_atual



            novos_disparos_inimigos = []
            for disparo_inimigo in disparos_inimigos:
                if "pos_x" not in disparo_inimigo:
                    disparo_inimigo["pos_x"] = float(disparo_inimigo["rect"].x)
                if "pos_y" not in disparo_inimigo:
                    disparo_inimigo["pos_y"] = float(disparo_inimigo["rect"].y)

                pos_x_disparo_inimigo, pos_y_disparo_inimigo = disparo_inimigo["rect"].x, disparo_inimigo["rect"].y
                if disparo_inimigo.get("frost_shard", False):
                    # Draw sharp ice shard rotated in its movement direction
                    vx, vy = disparo_inimigo["velocidade"]
                    angle = math.atan2(vy, vx)
                    px, py = pos_x_disparo_inimigo + shake_x, pos_y_disparo_inimigo + shake_y
                    pts = [
                        (px + 12 * math.cos(angle), py + 12 * math.sin(angle)),
                        (px + 6 * math.cos(angle + math.pi/2), py + 6 * math.sin(angle + math.pi/2)),
                        (px - 12 * math.cos(angle), py - 12 * math.sin(angle)),
                        (px + 6 * math.cos(angle - math.pi/2), py + 6 * math.sin(angle - math.pi/2))
                    ]
                    pygame.draw.polygon(tela, (0, 191, 255), pts)
                    pygame.draw.polygon(tela, (240, 248, 255), pts, 1)
                elif disparo_inimigo.get("tipo", "comum") == "atirador":
                    disparo_inimigo["angulo_rotacao"] = (disparo_inimigo.get("angulo_rotacao", 0.0) + 0.15) % (2 * math.pi)
                    cx = pos_x_disparo_inimigo + disparo_inimigo["rect"].width // 2 + shake_x
                    cy = pos_y_disparo_inimigo + disparo_inimigo["rect"].height // 2 + shake_y
                    raio = disparo_inimigo["rect"].width // 2
                    pygame.draw.circle(tela, (200, 235, 255), (cx, cy), raio + 2)
                    pygame.draw.circle(tela, (255, 255, 255), (cx, cy), raio)
                    ang = disparo_inimigo["angulo_rotacao"]
                    x1 = cx + (raio - 3) * math.cos(ang)
                    y1 = cy + (raio - 3) * math.sin(ang)
                    x2 = cx - (raio - 3) * math.cos(ang)
                    y2 = cy - (raio - 3) * math.sin(ang)
                    pygame.draw.line(tela, (180, 210, 230), (x1, y1), (x2, y2), 2)
                    x3 = cx + (raio - 3) * math.cos(ang + math.pi/2)
                    y3 = cy + (raio - 3) * math.sin(ang + math.pi/2)
                    x4 = cx - (raio - 3) * math.cos(ang + math.pi/2)
                    y4 = cy - (raio - 3) * math.sin(ang + math.pi/2)
                    pygame.draw.line(tela, (180, 210, 230), (x3, y3), (x4, y4), 2)
                    t_agora = pygame.time.get_ticks()
                    if t_agora - disparo_inimigo.get("ultimo_rastro", 0) >= 50:
                        disparo_inimigo["ultimo_rastro"] = t_agora
                        rastros_neve.append({
                            "pos": (pos_x_disparo_inimigo + disparo_inimigo["rect"].width // 2, pos_y_disparo_inimigo + disparo_inimigo["rect"].height // 2),
                            "raio": random.randint(14, 20),
                            "life": 1.0,
                            "decay": random.uniform(0.015, 0.03)
                        })
                elif disparo_inimigo.get("elite", False):
                    cx = pos_x_disparo_inimigo + disparo_inimigo["rect"].width // 2 + shake_x
                    cy = pos_y_disparo_inimigo + disparo_inimigo["rect"].height // 2 + shake_y
                    raio = max(5, int(disparo_inimigo["rect"].width * 0.48))
                    pygame.draw.circle(tela, (90, 190, 255), (cx, cy), raio + 4)
                    pygame.draw.circle(tela, (210, 245, 255), (cx - 2, cy - 2), max(2, raio // 2))
                    pygame.draw.circle(tela, (25, 105, 210), (cx, cy), raio + 5, 2)
                else:
                    cx = pos_x_disparo_inimigo + disparo_inimigo["rect"].width // 2 + shake_x
                    cy = pos_y_disparo_inimigo + disparo_inimigo["rect"].height // 2 + shake_y
                    raio = max(4, int(disparo_inimigo["rect"].width * 0.42))
                    pygame.draw.circle(tela, (120, 220, 255), (cx, cy), raio)
                    pygame.draw.circle(tela, (235, 255, 255), (cx - 1, cy - 1), max(2, raio // 2))

                # Atualize a posição do disparo do inimigo
                disparo_inimigo["pos_x"] += disparo_inimigo["velocidade"][0] * dt
                disparo_inimigo["pos_y"] += disparo_inimigo["velocidade"][1] * dt
                disparo_inimigo["rect"].x = int(disparo_inimigo["pos_x"])
                disparo_inimigo["rect"].y = int(disparo_inimigo["pos_y"])
                
                # Check collision with player
                colidiu = False
                if (
                    pos_x_personagem < pos_x_disparo_inimigo < pos_x_personagem + largura_personagem and
                    pos_y_personagem < pos_y_disparo_inimigo < pos_y_personagem + altura_personagem
                ):
                    # O disparo do inimigo atingiu o personagem
                    colidiu = True
                    if not personagem_imovel:
                        if disparo_inimigo.get("frost_shard", False):
                            Dano_pos_resistencia_person_longe = int((vida_maxima * 0.05 + 15) - Resistencia)
                        else:
                            dmg_base = dano_inimigo_longe
                            if disparo_inimigo.get("elite", False):
                                dmg_base = dano_inimigo_longe * 1.5
                            Dano_pos_resistencia_person_longe = int((vida_maxima * 0.25 + dmg_base) - Resistencia)
                        
                        if Dano_pos_resistencia_person_longe < 10:
                            Dano_pos_resistencia_person_longe = 10
                        if aurea == "Impulsiva":
                            eliminacoes_consecutivas_impulsiva = 0  # Perde streak se levar dano        
                        if absorver_dano_devota_atual():
                            pass
                        elif imune_tempo_restante <= 0:
                            vida -= Dano_pos_resistencia_person_longe
                            eliminacoes_consecutivas = 0
                            bonus_pontuacao = 0
                        tempo_ultimo_hit_inimigo = tempo_atual  # Atualize o tempo do último hit do inimigo
                        piscando_vida = True

                        tempo_ultimo_atingido = pygame.time.get_ticks()
                        personagem_imovel = True  # O personagem está imóvel após ser atingido

                # Lógica para controle da imobilização
                tempo_atual = pygame.time.get_ticks()
                if personagem_imovel and tempo_atual - tempo_ultimo_atingido >= tempo_imobilizacao:
                    personagem_imovel = False  # A personagem volta a poder se mexer

                if not colidiu and (
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
                    largura_disparo, altura_disparo = 40, 40
                    from utils import executar_animacao_morte_personagem
                    frames_local = multiplayer_coop.frames_jogador_local(frames_animacao, frames_animacao2)
                    frame_para_desenhar_morte = frames_local[direcao_atual][frame_atual % len(frames_local[direcao_atual])]
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
                        som_morte=locals().get('Dano_person', globals().get('Dano_person', None)),
                        mapa=mapa
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



            if piscando_vida:
                if False: # Desativado para o HUD widescreen
                    if tempo_atual % 500 < 250:  # Altere o valor 500 e 250 conforme necessário
                        # Desenha a barra de vida piscando em vermelho
                        pygame.draw.rect(tela, (255, 0, 0), (posicao_barra_vida[0], posicao_barra_vida[1], largura_barra_vida, altura_barra_vida))
                    else:
                        # Desenha a barra de vida normalmente
                        pygame.draw.rect(tela, verde, (posicao_barra_vida[0], posicao_barra_vida[1], (vida / vida_maxima) * largura_barra_vida, altura_barra_vida))


                if tempo_atual - tempo_ultimo_hit_inimigo >= intervalo_hit_inimigo:
                    piscando_vida = False

            tempo_atual = pygame.time.get_ticks()

            chamada_boss2_solicitada = keys[pygame.K_r]
            if multiplayer_coop.modo_multiplayer() and not r_press and chamada_boss2_solicitada:
                multiplayer_coop.solicitar_acao("boss2", 2)
            boss2_confirmado = multiplayer_coop.modo_multiplayer() and not r_press and multiplayer_coop.acao_confirmada(
                "boss2", 2, delay_ms=4000, assumir_sim_apos_ms=multiplayer_coop.COOP_SILENCIO_CONFIRMA_MS
            )
            if boss2_confirmado or (not multiplayer_coop.modo_multiplayer() and chamada_boss2_solicitada):
                if not r_press:
                    boss_entrada_ativa = True
                    boss_entrada_tempo_inicio = tempo_atual
                    tempo_boss_entrada_fim = tempo_atual + 2500
                    boss_impacto_feito = False
                    ice_shards = []
                    ondas_nevasca = []
                    ondas_nevasca_preparadas = []
                r_press = True

            if r_press:

                max_inimigos2=4
                intervalo_disparo_inimigo =3000
                velocidade_inimigo2=1.50
                if musica_boss2 == 1:
                    Musica_tema_Boss2.play(loops=-1)
                    musica_boss2+=1

            if r_press and boss_entrada_ativa:
                tempo_decorrido = tempo_atual - boss_entrada_tempo_inicio
                progress = min(1.0, tempo_decorrido / 2500)
                
                # Falling crystal stage
                if progress < 0.8:
                    # Draw falling ice block/crystal
                    cy = -300 + (pos_y_chefe2 + 300) * (progress / 0.8)
                    cx = pos_x_chefe2 + chefe_largura2 // 2
                    
                    crystal_surf = pygame.Surface((120, 200), pygame.SRCALPHA)
                    # Outer glow (cyan)
                    pygame.draw.polygon(crystal_surf, (0, 191, 255, 75), [(60, 0), (120, 50), (100, 150), (60, 200), (20, 150), (0, 50)])
                    # Inner core (light blue)
                    pygame.draw.polygon(crystal_surf, (173, 216, 230, 200), [(60, 10), (110, 55), (90, 145), (60, 190), (30, 145), (10, 55)])
                    # Highlights (ice white)
                    pygame.draw.polygon(crystal_surf, (240, 248, 255, 255), [(60, 20), (100, 60), (80, 140), (60, 180), (40, 140), (20, 60)], 2)
                    tela.blit(crystal_surf, (cx - 60 + shake_x, cy - 100 + shake_y))
                else:
                    # Impact stage!
                    if not boss_impacto_feito:
                        boss_impacto_feito = True
                        screen_shake = 18
                        # Spawn 35 ice shards blasting out!
                        for _ in range(35):
                            angle = random.uniform(0, 2 * math.pi)
                            speed = random.uniform(3, 10)
                            ice_shards.append({
                                "x": pos_x_chefe2 + chefe_largura2 // 2,
                                "y": pos_y_chefe2 + chefe_altura2 // 2,
                                "vx": speed * math.cos(angle),
                                "vy": speed * math.sin(angle) - random.uniform(2, 6), # upward blast bias
                                "size": random.randint(5, 12),
                                "vida": random.uniform(150, 255)
                            })
                    
                    # Draw expanding freezing shockwave rings!
                    cx = pos_x_chefe2 + chefe_largura2 // 2
                    cy = pos_y_chefe2 + chefe_altura2 // 2
                    for i in range(3):
                        wave_r = int(250 * ((tempo_decorrido % 500) / 500.0)) + i * 20
                        alpha = max(0, 255 - int(255 * ((tempo_decorrido % 500) / 500.0)))
                        surf_ring = pygame.Surface((wave_r * 2, wave_r * 2), pygame.SRCALPHA)
                        pygame.draw.circle(surf_ring, (173, 216, 230, alpha // 3), (wave_r, wave_r), wave_r, 4)
                        tela.blit(surf_ring, (cx - wave_r + shake_x, cy - wave_r + shake_y))

                # Banner announcing the boss entrance!
                if (tempo_atual // 150) % 2 == 0:
                    fonte_aviso = pygame.font.Font(None, 48)
                    txt_boss = fonte_aviso.render("A nevasca emite um grito", True, (0, 191, 255))
                    rect_boss_txt = txt_boss.get_rect(center=(largura_tela // 2, altura_tela // 2 - 100))
                    # Draw dark transparent banner background for high contrast/readability
                    bg_surf = pygame.Surface((rect_boss_txt.width + 40, rect_boss_txt.height + 20), pygame.SRCALPHA)
                    bg_surf.fill((0, 0, 0, 180))
                    tela.blit(bg_surf, (rect_boss_txt.x - 20, rect_boss_txt.y - 10))
                    tela.blit(txt_boss, rect_boss_txt)

                if tempo_decorrido >= 2500:
                    boss_entrada_ativa = False
                    # Start the boss attacks after entrance finishes
                    ataque_vertical_aviso = True
                    tempo_inicio_aviso_vertical = tempo_atual


            if r_press:
                # Lógica para animar o chefe
                tempo_passado_animacao_chefe2 += relogio.get_rawtime()
                if tempo_passado_animacao_chefe2 >= tempo_animacao_chefe2:
                    tempo_passado_animacao_chefe2 = 0
                    frame_atual_chefe = (frame_atual_chefe + 1) % 2

                if Ultimo_Estalo and vida_boss2 <= limiar_execucao_boss(Executa_inimigo) * vida_maxima_boss2:
                    vida_boss2=0

                if vida_boss2 <= 0:
                    frame_porcentagem=frames_chefe2_4
                    rect_boss = pygame.Rect(pos_x_chefe2, pos_y_chefe2, 64, 64)
                    rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                    ataque_vertical_ativo=False
                    ataque_horizontal_ativo=False



                    if rect_boss.colliderect(rect_personagem):
                        if toque == 0:
                            registrar_conclusao_fase(2)
                            salvar_atributos()
                            Musica_tema_Boss2.stop()
                            pausar_cronometro()
                            tela_transicao_dimensional(tela, 3)
                            multiplayer_coop.enviar_transicao_fase(3)
                            if game_manager:
                                from game_manager import EstadoJogo
                                game_manager.mudar_estado(EstadoJogo.JOGO_FASE_3)
                                raise CleanExit()
                            else:
                                import GAME3
                                GAME3.executar_jogo()
                                raise CleanExit()

                            toque+=1
                #  onde verifica a colisão dos disparos com o boss


                if boss_vivo2:


                    Musica_tema_fases.stop()
                    # Dentro do loop principal
                    if not boss_entrada_ativa:
                        desenhar_barra_vida_boss(tela, vida_boss2, vida_maxima_boss2, "SENTINELA GLACIAL", 2, (80, 220, 255))

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


                    if not boss_entrada_ativa:
                        # Draw freezing breath wind effect (particles and cone)
                        if boss_sopro_ativo:
                            cx = pos_x_chefe2 + chefe_largura2 // 2
                            cy = pos_y_chefe2 + chefe_altura2 // 2
                            px = pos_x_personagem + largura_personagem // 2
                            py = pos_y_personagem + altura_personagem // 2
                            dx = px - cx
                            dy = py - cy
                            dist = max(1.0, math.hypot(dx, dy))
                            udir = (dx / dist, dy / dist)
                            perp = (-udir[1], udir[0])
                            
                            # Draw wind particles
                            for _ in range(2):
                                sopro_particulas.append({
                                    "x": cx + udir[0] * 30 + random.uniform(-10, 10),
                                    "y": cy + udir[1] * 30 + random.uniform(-10, 10),
                                    "vx": udir[0] * random.uniform(6.0, 9.0) + random.uniform(-1.0, 1.0),
                                    "vy": udir[1] * random.uniform(6.0, 9.0) + random.uniform(-1.0, 1.0),
                                    "size": random.randint(10, 22),
                                    "alpha": random.randint(100, 200)
                                })
                                
                            alpha = int(40 + 20 * math.sin(pygame.time.get_ticks() * 0.02))
                            cone_len = min(dist, 400.0)
                            p1 = (cx + udir[0] * 30, cy + udir[1] * 30)
                            p2 = (cx + udir[0] * cone_len + perp[0] * 90, cy + udir[1] * cone_len + perp[1] * 90)
                            p3 = (cx + udir[0] * cone_len - perp[0] * 90, cy + udir[1] * cone_len - perp[1] * 90)
                            
                            surf_cone = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
                            pygame.draw.polygon(surf_cone, (173, 216, 230, alpha), [p1, p2, p3])
                            tela.blit(surf_cone, (0, 0))

                        # Shake boss during warning charge
                        bx_offset = random.randint(-4, 4) if boss_sopro_aviso else 0
                        by_offset = random.randint(-4, 4) if boss_sopro_aviso else 0
                        
                        tela.blit(frame_porcentagem[frame_atual_chefe], (pos_x_chefe2 + shake_x + bx_offset, pos_y_chefe2 + shake_y + by_offset))
                        
                        # Draw crystal shield around boss
                        if boss_escudo_ativo:
                            cx = pos_x_chefe2 + chefe_largura2 // 2
                            cy = pos_y_chefe2 + chefe_altura2 // 2
                            
                            # Draw overlapping translucent shields
                            for r_shield, opacity in [(70, 70), (80, 40)]:
                                shield_surf = pygame.Surface((r_shield * 2, r_shield * 2), pygame.SRCALPHA)
                                pygame.draw.circle(shield_surf, (173, 216, 230, opacity), (r_shield, r_shield), r_shield)
                                pygame.draw.circle(shield_surf, (240, 248, 255, opacity + 40), (r_shield, r_shield), r_shield, 3)
                                tela.blit(shield_surf, (cx - r_shield + shake_x, cy - r_shield + shake_y))
                            
                            # Draw orbiting crystals
                            raio_orbita = 85
                            for i in range(3):
                                angle = escudo_cristais_angulo + i * (2 * math.pi / 3)
                                ox = cx + raio_orbita * math.cos(angle)
                                oy = cy + raio_orbita * math.sin(angle)
                                
                                # Draw diamond shape
                                pygame.draw.polygon(tela, (0, 191, 255), [
                                    (ox + shake_x, oy - 14 + shake_y),
                                    (ox + 10 + shake_x, oy + shake_y),
                                    (ox + shake_x, oy + 14 + shake_y),
                                    (ox - 10 + shake_x, oy + shake_y)
                                ])
                                pygame.draw.polygon(tela, (240, 248, 255), [
                                    (ox + shake_x, oy - 9 + shake_y),
                                    (ox + 6 + shake_x, oy + shake_y),
                                    (ox + shake_x, oy + 9 + shake_y),
                                    (ox - 6 + shake_x, oy + shake_y)
                                ])
                    else:
                        # Draw crack marks on the floor during the latter part of entrance
                        tempo_decorrido = tempo_atual - boss_entrada_tempo_inicio
                        progress = min(1.0, tempo_decorrido / 2500)
                        if progress >= 0.8:
                            # Show boss fading in/shaking out of the shattered ice!
                            alpha = min(255, int(255 * ((progress - 0.8) / 0.2)))
                            temp_surf = frame_porcentagem[frame_atual_chefe].copy()
                            # Pygame surface transparency
                            temp_surf.set_alpha(alpha)
                            tela.blit(temp_surf, (pos_x_chefe2 + shake_x, pos_y_chefe2 + shake_y))



                    # Warning telegraph updates and drawing
                    if ataque_vertical_aviso:
                        if pygame.time.get_ticks() - tempo_inicio_aviso_vertical >= duracao_aviso:
                            ataque_vertical_aviso = False
                            ataque_vertical_ativo = True
                            ondas_nevasca = list(ondas_nevasca_preparadas)
                            ondas_nevasca_preparadas = []
                        else:
                            alpha = int(90 + 50 * math.sin(pygame.time.get_ticks() * 0.015))
                            surf_warn_lane = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
                            for wave in ondas_nevasca_preparadas:
                                if wave["direction"] in ["left", "right"]:
                                    x_pos = wave["x"] if wave["direction"] == "left" else 0
                                    pygame.draw.rect(surf_warn_lane, (0, 220, 255, alpha), (x_pos - 40, 0, 80, altura_tela))
                                    pygame.draw.rect(surf_warn_lane, (255, 255, 255, alpha + 30), (x_pos - 40, 0, 80, altura_tela), 2)
                                    for _ in range(2):
                                        rx = x_pos + random.uniform(-35, 35)
                                        ry = random.uniform(0, altura_tela)
                                        pygame.draw.circle(surf_warn_lane, (240, 248, 255, alpha + 60), (rx, ry), random.randint(2, 5))
                            tela.blit(surf_warn_lane, (0, 0))
                            
                            if (pygame.time.get_ticks() // 150) % 2 == 0:
                                warn_font = pygame.font.Font(None, 32)
                                warn_txt = warn_font.render("<- ALERTA: NEVASCA VERTICAL IMINENTE <-", True, (0, 220, 255))
                                shadow_txt = warn_font.render("<- ALERTA: NEVASCA VERTICAL IMINENTE <-", True, (0, 0, 0))
                                tela.blit(shadow_txt, (largura_tela - warn_txt.get_width() - 22, 22))
                                tela.blit(warn_txt, (largura_tela - warn_txt.get_width() - 20, 20))
                                
                    if ataque_horizontal_aviso:
                        if pygame.time.get_ticks() - tempo_inicio_aviso_horizontal >= duracao_aviso:
                            ataque_horizontal_aviso = False
                            ataque_horizontal_ativo = True
                            ondas_nevasca = list(ondas_nevasca_preparadas)
                            ondas_nevasca_preparadas = []
                        else:
                            alpha = int(90 + 50 * math.sin(pygame.time.get_ticks() * 0.015))
                            surf_warn_lane = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
                            for wave in ondas_nevasca_preparadas:
                                if wave["direction"] in ["down", "up"]:
                                    y_pos = wave["y"] if wave["direction"] == "down" else altura_tela
                                    pygame.draw.rect(surf_warn_lane, (0, 220, 255, alpha), (0, y_pos - 40, largura_tela, 80))
                                    pygame.draw.rect(surf_warn_lane, (255, 255, 255, alpha + 30), (0, y_pos - 40, largura_tela, 80), 2)
                                    for _ in range(2):
                                        rx = random.uniform(0, largura_tela)
                                        ry = y_pos + random.uniform(-35, 35)
                                        pygame.draw.circle(surf_warn_lane, (240, 248, 255, alpha + 60), (rx, ry), random.randint(2, 5))
                            tela.blit(surf_warn_lane, (0, 0))
                            
                            if (pygame.time.get_ticks() // 150) % 2 == 0:
                                warn_font = pygame.font.Font(None, 32)
                                warn_txt = warn_font.render("v ALERTA: NEVASCA HORIZONTAL IMINENTE v", True, (0, 220, 255))
                                shadow_txt = warn_font.render("v ALERTA: NEVASCA HORIZONTAL IMINENTE v", True, (0, 0, 0))
                                tela.blit(shadow_txt, (largura_tela // 2 - warn_txt.get_width() // 2 + 2, 22))
                                tela.blit(warn_txt, (largura_tela // 2 - warn_txt.get_width() // 2, 20))

                    if ataque_avalanche_aviso:
                        if pygame.time.get_ticks() - tempo_inicio_aviso_avalanche >= duracao_aviso:
                            ataque_avalanche_aviso = False
                            ataque_avalanche_ativo = True
                            avalanche_projeteis = []
                            for pos in avalanche_posicoes:
                                avalanche_projeteis.append({
                                    "tx": pos[0],
                                    "ty": pos[1],
                                    "x": pos[0],
                                    "y": -100.0,
                                    "vel": random.uniform(6.0, 9.0)
                                })
                        else:
                            # Draw blinking red warning circles on the ground
                            alpha = int(120 + 80 * math.sin(pygame.time.get_ticks() * 0.01))
                            for pos in avalanche_posicoes:
                                surf_circulo = pygame.Surface((100, 100), pygame.SRCALPHA)
                                pygame.draw.circle(surf_circulo, (255, 0, 0, alpha), (50, 50), 40, 3)
                                pygame.draw.circle(surf_circulo, (255, 0, 0, alpha // 4), (50, 50), 40)
                                tela.blit(surf_circulo, (pos[0] - 50 + shake_x, pos[1] - 50 + shake_y))
                                warn_font = pygame.font.Font(None, 24)
                                txt = warn_font.render("!", True, (255, 0, 0))
                                tela.blit(txt, (pos[0] - txt.get_width() // 2 + shake_x, pos[1] - 65 + shake_y))

                    # Freezing Breath Warning
                    if boss_sopro_aviso:
                        tempo_decorrido = pygame.time.get_ticks() - tempo_inicio_sopro
                        if tempo_decorrido >= duracao_aviso:
                            boss_sopro_aviso = False
                            boss_sopro_ativo = True
                            # Lock breath direction towards current player position
                            cx = pos_x_chefe2 + chefe_largura2 // 2
                            cy = pos_y_chefe2 + chefe_altura2 // 2
                            px = pos_x_personagem + largura_personagem // 2
                            py = pos_y_personagem + altura_personagem // 2
                            dx = px - cx
                            dy = py - cy
                            dist = max(1.0, math.hypot(dx, dy))
                            sopro_dir = (dx / dist, dy / dist)
                        else:
                            # Draw flashing warning cone guide
                            alpha = int(120 + 80 * math.sin(tempo_decorrido * 0.02))
                            cx = pos_x_chefe2 + chefe_largura2 // 2
                            cy = pos_y_chefe2 + chefe_altura2 // 2
                            px = pos_x_personagem + largura_personagem // 2
                            py = pos_y_personagem + altura_personagem // 2
                            dx = px - cx
                            dy = py - cy
                            dist = max(1.0, math.hypot(dx, dy))
                            udir = (dx / dist, dy / dist)
                            perp = (-udir[1], udir[0])
                            
                            # Warning cone geometry
                            cone_len = min(dist, 400.0)
                            p1 = (cx + udir[0] * 30, cy + udir[1] * 30)
                            p2 = (cx + udir[0] * cone_len + perp[0] * 90, cy + udir[1] * cone_len + perp[1] * 90)
                            p3 = (cx + udir[0] * cone_len - perp[0] * 90, cy + udir[1] * cone_len - perp[1] * 90)
                            
                            surf_warn = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
                            pygame.draw.polygon(surf_warn, (0, 191, 255, alpha // 3), [p1, p2, p3])
                            pygame.draw.polygon(surf_warn, (0, 191, 255, alpha), [p1, p2, p3], 2)
                            tela.blit(surf_warn, (0, 0))
                            
                            # Emit frosty charge sparks
                            if random.random() < 0.4:
                                bx = pos_x_chefe2 + chefe_largura2 // 2
                                by = pos_y_chefe2 + chefe_altura2 // 2
                                sopro_particulas.append({
                                    "x": bx + random.uniform(-25, 25),
                                    "y": by + random.uniform(-25, 25),
                                    "vx": random.uniform(-2, 2) - udir[0] * 2,
                                    "vy": random.uniform(-2, 2) - udir[1] * 2,
                                    "size": random.randint(3, 6),
                                    "vida": 200
                                })

                    # Update and draw active Blizzard Waves (horizontal & vertical)
                    if ataque_vertical_ativo or ataque_horizontal_ativo:
                        tempo_inicio_ataque = pygame.time.get_ticks()
                        tempo_inicio_ataque_horizontal = tempo_inicio_dano_horizontal = pygame.time.get_ticks()
                        
                        novas_ondas = []
                        for wave in ondas_nevasca:
                            # Update wave positions
                            wave["x"] += wave["vx"] * dt
                            wave["y"] += wave["vy"] * dt
                            
                            # Sinusoidal oscillation logic
                            if wave.get("type") == "sinusoidal":
                                wave["fase_seno"] += 0.08 * dt
                                displacement = math.sin(wave["fase_seno"]) * 4.5
                                if wave["direction"] in ["left", "right"]:
                                    wave["y"] += displacement
                                else:
                                    wave["x"] += displacement
                                    
                            # Direction-changing pivoting logic
                            if wave.get("type") == "pivoting" and not wave.get("pivoted"):
                                if wave["direction"] == "left" and wave["x"] <= wave["pivot_coord"]:
                                    wave["vx"], wave["vy"] = wave["pivot_new_vel"]
                                    wave["pivoted"] = True
                                    wave["direction"] = "down" if wave["pivot_new_vel"][1] > 0 else "up"
                                    screen_shake = 5
                                elif wave["direction"] == "down" and wave["y"] >= wave["pivot_coord"]:
                                    wave["vx"], wave["vy"] = wave["pivot_new_vel"]
                                    wave["pivoted"] = True
                                    wave["direction"] = "left" if wave["pivot_new_vel"][0] < 0 else "right"
                                    screen_shake = 5
                                    
                            # Render the blizzard wave
                            x_c = int(wave["x"])
                            y_c = int(wave["y"])
                            w_half = wave["largura"] // 2
                            
                            if wave["direction"] in ["left", "right", "left_pivot"]:
                                # Vertical wave drawing (moving horizontally)
                                surf_wave = pygame.Surface((wave["largura"], altura_tela), pygame.SRCALPHA)
                                for rx in range(wave["largura"]):
                                    dist_center = abs(rx - w_half)
                                    alpha_val = int(max(0, 110 - (dist_center * (110 / w_half))))
                                    pygame.draw.line(surf_wave, (173, 216, 230, alpha_val), (rx, 0), (rx, altura_tela))
                                pygame.draw.line(surf_wave, (255, 255, 255, 200), (w_half, 0), (w_half, altura_tela), 2)
                                tela.blit(surf_wave, (x_c - w_half, 0))
                                
                                # Frost streaks and snow wind lines
                                for _ in range(4):
                                    wy = random.randint(0, altura_tela)
                                    wlen = random.randint(20, 50)
                                    pygame.draw.line(tela, (255, 255, 255, 210), (x_c - wlen//2, wy), (x_c + wlen//2, wy + random.randint(-4, 4)), 2)
                            else:
                                # Horizontal wave drawing (moving vertically)
                                surf_wave = pygame.Surface((largura_tela, wave["largura"]), pygame.SRCALPHA)
                                for ry in range(wave["largura"]):
                                    dist_center = abs(ry - w_half)
                                    alpha_val = int(max(0, 110 - (dist_center * (110 / w_half))))
                                    pygame.draw.line(surf_wave, (173, 216, 230, alpha_val), (0, ry), (largura_tela, ry))
                                pygame.draw.line(surf_wave, (255, 255, 255, 200), (0, w_half), (largura_tela, w_half), 2)
                                tela.blit(surf_wave, (0, y_c - w_half))
                                
                                for _ in range(4):
                                    wx = random.randint(0, largura_tela)
                                    wlen = random.randint(20, 50)
                                    pygame.draw.line(tela, (255, 255, 255, 210), (wx, y_c - wlen//2), (wx + random.randint(-4, 4), y_c + wlen//2), 2)
                                    
                            # Check boundaries to keep on screen
                            on_screen = True
                            if wave["direction"] == "left" and wave["x"] < -100:
                                on_screen = False
                            elif wave["direction"] == "right" and wave["x"] > largura_tela + 100:
                                on_screen = False
                            elif wave["direction"] == "down" and wave["y"] > altura_tela + 100:
                                on_screen = False
                            elif wave["direction"] == "up" and wave["y"] < -100:
                                on_screen = False
                                
                            if on_screen:
                                novas_ondas.append(wave)
                                
                        ondas_nevasca = novas_ondas
                        if len(ondas_nevasca) == 0:
                            ataque_vertical_ativo = False
                            ataque_horizontal_ativo = False

                    if ataque_avalanche_ativo:
                        tempo_inicio_ataque = pygame.time.get_ticks()
                        
                        # Draw passing avalanche backdrop (dynamic wind snow circles)
                        if len(avalanche_particulas_vento) < 60:
                            avalanche_particulas_vento.append({
                                "x": random.uniform(-150, largura_tela - 100),
                                "y": random.uniform(-150, -50),
                                "vx": random.uniform(7.0, 11.0),
                                "vy": random.uniform(8.0, 13.0),
                                "size": random.randint(15, 30),
                                "alpha": random.randint(30, 80)
                            })
                        
                        novas_ventos = []
                        for p_vento in avalanche_particulas_vento:
                            p_vento["x"] += p_vento["vx"] * dt
                            p_vento["y"] += p_vento["vy"] * dt
                            if p_vento["x"] < largura_tela + 100 and p_vento["y"] < altura_tela + 100:
                                novas_ventos.append(p_vento)
                                surf_p = pygame.Surface((p_vento["size"] * 2, p_vento["size"] * 2), pygame.SRCALPHA)
                                pygame.draw.circle(surf_p, (240, 248, 255, p_vento["alpha"]), (p_vento["size"], p_vento["size"]), p_vento["size"])
                                tela.blit(surf_p, (p_vento["x"] - p_vento["size"], p_vento["y"] - p_vento["size"]))
                        avalanche_particulas_vento = novas_ventos
                        
                        novos_projeteis = []
                        for p in avalanche_projeteis:
                            p["y"] += p["vel"] * dt
                            if p["y"] < p["ty"]:
                                novos_projeteis.append(p)
                                # Draw glowing avalanche streak
                                px = int(p["x"]) + shake_x
                                py = int(p["y"]) + shake_y
                                pygame.draw.line(tela, (173, 216, 230), (px, py - 45), (px, py), 4)
                                pygame.draw.circle(tela, (255, 255, 255), (px, py), 7)
                                for j in range(3):
                                    pygame.draw.circle(tela, (240, 248, 255), (px, py - 15 - j * 10), 5 - j)
                            else:
                                # Explode!
                                screen_shake = 7
                                for _ in range(6):
                                    angle = random.uniform(0, 2 * math.pi)
                                    speed = random.uniform(2, 5)
                                    ice_shards.append({
                                        "x": p["tx"],
                                        "y": p["ty"],
                                        "vx": speed * math.cos(angle),
                                        "vy": speed * math.sin(angle) - 2.0,
                                        "size": random.randint(3, 7),
                                        "vida": random.uniform(100, 180)
                                    })
                                # Check collision with player
                                dist_to_player = math.hypot(pos_x_personagem + largura_personagem // 2 - p["tx"], pos_y_personagem + altura_personagem // 2 - p["ty"])
                                if dist_to_player <= 50:
                                    if absorver_dano_devota_atual():
                                        pass
                                    elif imune_tempo_restante <= 0 and pygame.time.get_ticks() - tempo_ultimo_atingido >= 1000:
                                        vida -= int(vida_maxima - vida) * 0.10 + 20 + dano_boss2
                                        tempo_ultimo_atingido = pygame.time.get_ticks()
                                        personagem_imovel = True
                                        piscando_vida = True
                                
                                # Leave a slow zone
                                zonas_lentidao.append({
                                    "pos": (p["tx"], p["ty"]),
                                    "raio": 60,
                                    "tempo_inicio": pygame.time.get_ticks(),
                                    "duracao": 4000
                                })
                        avalanche_projeteis = novos_projeteis
                        if len(avalanche_projeteis) == 0:
                            ataque_avalanche_ativo = False

                    # Active Freezing Breath loop
                    if boss_sopro_ativo:
                        tempo_inicio_ataque = pygame.time.get_ticks()
                        tempo_atual = pygame.time.get_ticks()
                        if tempo_atual - tempo_ultimo_sopro_disparo >= 100:
                            tempo_ultimo_sopro_disparo = tempo_atual
                            cx = pos_x_chefe2 + chefe_largura2 // 2
                            cy = pos_y_chefe2 + chefe_altura2 // 2
                            base_angle = math.atan2(sopro_dir[1], sopro_dir[0])
                            for offset_angle in [-0.25, 0.0, 0.25]:
                                angle = base_angle + offset_angle
                                vx = math.cos(angle) * 7.5
                                vy = math.sin(angle) * 7.5
                                disparos_inimigos.append({
                                    "rect": pygame.Rect(cx + sopro_dir[0] * 40 - 6, cy + sopro_dir[1] * 40 - 6, 12, 12),
                                    "velocidade": (vx, vy),
                                    "elite": False,
                                    "frost_shard": True
                                })
                        
                        if pygame.time.get_ticks() - tempo_inicio_sopro >= 3500:
                            boss_sopro_ativo = False

                    # Active Crystal Shield loop
                    if boss_escudo_ativo:
                        tempo_inicio_ataque = pygame.time.get_ticks()
                        escudo_cristais_angulo += 0.05 * dt
                        
                        tempo_atual = pygame.time.get_ticks()
                        if tempo_atual - tempo_ultimo_disparo_escudo >= 1000:
                            tempo_ultimo_disparo_escudo = tempo_atual
                            cx = pos_x_chefe2 + chefe_largura2 // 2
                            cy = pos_y_chefe2 + chefe_altura2 // 2
                            raio_orbita = 85
                            for i in range(3):
                                angle = escudo_cristais_angulo + i * (2 * math.pi / 3)
                                ox = cx + raio_orbita * math.cos(angle)
                                oy = cy + raio_orbita * math.sin(angle)
                                pdx = (pos_x_personagem + largura_personagem // 2) - ox
                                pdy = (pos_y_personagem + altura_personagem // 2) - oy
                                pdist = max(1.0, math.hypot(pdx, pdy))
                                disparos_inimigos.append({
                                    "rect": pygame.Rect(ox - 6, oy - 6, 12, 12),
                                    "velocidade": ((pdx / pdist) * 6.5, (pdy / pdist) * 6.5),
                                    "elite": False,
                                    "frost_shard": True
                                })
                        
                        if pygame.time.get_ticks() - tempo_inicio_escudo >= 4000:
                            boss_escudo_ativo = False

                    # Update and draw breath wind/frost particles
                    novas_particulas = []
                    for pt in sopro_particulas:
                        pt["x"] += pt["vx"] * dt
                        pt["y"] += pt["vy"] * dt
                        if "vida" in pt:
                            pt["vida"] -= 10
                            vida_val = pt["vida"]
                        else:
                            pt["alpha"] -= 8
                            vida_val = pt["alpha"]
                            
                        if vida_val > 0:
                            novas_particulas.append(pt)
                            alpha = max(0, min(255, vida_val))
                            p_surf = pygame.Surface((pt["size"]*2, pt["size"]*2), pygame.SRCALPHA)
                            pygame.draw.circle(p_surf, (173, 216, 230, alpha // 2), (pt["size"], pt["size"]), pt["size"])
                            pygame.draw.circle(p_surf, (240, 248, 255, alpha), (pt["size"], pt["size"]), pt["size"] // 2)
                            tela.blit(p_surf, (pt["x"] - pt["size"] + shake_x, pt["y"] - pt["size"] + shake_y))
                    sopro_particulas = novas_particulas

                    # Verifica o tempo decorrido desde o início do ataque
                    tempo_decorrido_ataque = pygame.time.get_ticks() - tempo_inicio_ataque
                    if tempo_decorrido_ataque >= tempo_espera_ataque:
                    # Verifica se nenhum dos ataques ou avisos está ativo
                        if (not ataque_horizontal_ativo and not ataque_vertical_ativo and not ataque_avalanche_ativo and 
                            not ataque_horizontal_aviso and not ataque_vertical_aviso and not ataque_avalanche_aviso and
                            not boss_sopro_aviso and not boss_sopro_ativo and not boss_escudo_ativo):
                            # Escolhe aleatoriamente entre as 5 habilidades com pesos iguais
                            rnd = random.random()
                            if rnd < 0.20:
                                # Ativa o aviso do ataque horizontal
                                ataque_horizontal_aviso = True
                                tempo_inicio_aviso_horizontal = pygame.time.get_ticks()
                                tempo_decorrido_horizontal = 0
                                pattern = random.choice([1, 2, 3, 4])
                                if pattern == 1:
                                    ondas_nevasca_preparadas = [
                                        {"x": 0, "y": -30, "vx": 0, "vy": 4.0, "largura": 70, "direction": "down", "type": "standard"},
                                        {"x": 0, "y": -280, "vx": 0, "vy": 4.0, "largura": 70, "direction": "down", "type": "standard"}
                                    ]
                                elif pattern == 2:
                                    ondas_nevasca_preparadas = [
                                        {"x": 0, "y": -30, "vx": 0, "vy": 4.2, "largura": 80, "direction": "down", "type": "pivoting", "pivoted": False, "pivot_coord": 300, "pivot_new_vel": (-5.0, 0)}
                                    ]
                                elif pattern == 3:
                                    ondas_nevasca_preparadas = [
                                        {"x": 0, "y": -30, "vx": 0, "vy": 3.6, "largura": 70, "direction": "down", "type": "standard"},
                                        {"x": largura_tela + 30, "y": 0, "vx": -3.6, "vy": 0, "largura": 70, "direction": "left", "type": "standard"}
                                    ]
                                else:
                                    ondas_nevasca_preparadas = [
                                        {"x": 0, "y": -30, "vx": 0, "vy": 4.2, "largura": 60, "direction": "down", "type": "standard"},
                                        {"x": 0, "y": -230, "vx": 0, "vy": 4.2, "largura": 60, "direction": "down", "type": "standard"},
                                        {"x": 0, "y": -430, "vx": 0, "vy": 4.2, "largura": 60, "direction": "down", "type": "standard"}
                                    ]
                            elif rnd < 0.40:
                                # Ativa o aviso do ataque vertical
                                ataque_vertical_aviso = True
                                tempo_inicio_aviso_vertical = pygame.time.get_ticks()
                                velocidade_inimigo2 += 0.010
                                tempo_decorrido_vertical = 0
                                pattern = random.choice([1, 2, 3, 4])
                                if pattern == 1:
                                    ondas_nevasca_preparadas = [
                                        {"x": largura_tela + 30, "y": 0, "vx": -4.2, "vy": 0, "largura": 70, "direction": "left", "type": "standard"},
                                        {"x": largura_tela + 310, "y": 0, "vx": -4.2, "vy": 0, "largura": 70, "direction": "left", "type": "standard"}
                                    ]
                                elif pattern == 2:
                                    ondas_nevasca_preparadas = [
                                        {"x": largura_tela + 30, "y": 0, "vx": -4.0, "vy": 0, "largura": 80, "direction": "left", "type": "sinusoidal", "fase_seno": 0.0}
                                    ]
                                elif pattern == 3:
                                    ondas_nevasca_preparadas = [
                                        {"x": largura_tela + 30, "y": 0, "vx": -4.5, "vy": 0, "largura": 80, "direction": "left", "type": "pivoting", "pivoted": False, "pivot_coord": 450, "pivot_new_vel": (0, 4.5)}
                                    ]
                                else:
                                    ondas_nevasca_preparadas = [
                                        {"x": largura_tela + 30, "y": 0, "vx": -4.5, "vy": 0, "largura": 60, "direction": "left", "type": "standard"},
                                        {"x": largura_tela + 250, "y": 0, "vx": -4.5, "vy": 0, "largura": 60, "direction": "left", "type": "standard"},
                                        {"x": largura_tela + 470, "y": 0, "vx": -4.5, "vy": 0, "largura": 60, "direction": "left", "type": "standard"}
                                    ]
                            elif rnd < 0.60:
                                # Ativa o aviso da avalanche
                                ataque_avalanche_aviso = True
                                tempo_inicio_aviso_avalanche = pygame.time.get_ticks()
                                avalanche_posicoes = []
                                px = pos_x_personagem + largura_personagem // 2
                                py = pos_y_personagem + altura_personagem // 2
                                avalanche_posicoes.append((px, py))
                                for _ in range(5):
                                    rx = random.randint(50, largura_tela - 50)
                                    ry = random.randint(50, altura_tela - 50)
                                    avalanche_posicoes.append((rx, ry))
                            elif rnd < 0.80:
                                # Ativa o aviso do sopro congelante
                                boss_sopro_aviso = True
                                tempo_inicio_sopro = pygame.time.get_ticks()
                                tempo_ultimo_sopro_disparo = 0
                                sopro_particulas = []
                            else:
                                # Ativa a barreira de cristais
                                boss_escudo_ativo = True
                                tempo_inicio_escudo = pygame.time.get_ticks()
                                tempo_ultimo_disparo_escudo = pygame.time.get_ticks()
                                escudo_cristais_angulo = 0.0

                    # Check player collision with active Blizzard Waves
                    if ataque_vertical_ativo or ataque_horizontal_ativo:
                        for wave in ondas_nevasca:
                            if wave["direction"] in ["left", "right"]:
                                w_half = wave["largura"] // 2
                                rect_wave = pygame.Rect(wave["x"] - w_half, 0, wave["largura"], altura_tela)
                            else:
                                w_half = wave["largura"] // 2
                                rect_wave = pygame.Rect(0, wave["y"] - w_half, largura_tela, wave["largura"])
                                
                            if rect_wave.colliderect(personagem_rect):
                                if absorver_dano_devota_atual():
                                    pass
                                elif imune_tempo_restante <= 0 and pygame.time.get_ticks() - tempo_ultimo_atingido >= 800:
                                    vida -= int(vida_maxima * 0.08) + 20 + dano_boss2
                                    tempo_ultimo_atingido = pygame.time.get_ticks()
                                    personagem_imovel = True
                                    piscando_vida = True

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

                    acertou_boss_disparo = (
                        lacerante_manifestacao.colisao_corte(disparo, rect_boss, tempo_atual)
                        if disparo.get("tipo_manifestacao") == "lacerante_corte"
                        else (
                            prismatica_manifestacao.colisao_feixe(disparo, rect_boss, tempo_atual)
                            if disparo.get("tipo_manifestacao") == "prismatica_feixe"
                            else (
                                retornante_manifestacao.colisao_alvo(disparo, {"rect": rect_boss, "retornante_id": "boss2"})
                                if disparo.get("tipo_manifestacao") == "retornante_pulso"
                                else rect_disparo.colliderect(rect_boss)
                            )
                        )
                    )
                    if r_press and not boss_entrada_ativa and acertou_boss_disparo:
                        acerto_prismatico = prismatica_manifestacao.registrar_acerto(
                            disparo, {"rect": rect_boss, "prismatica_id": "boss2"}, tempo_atual
                        )
                        acerto_retornante = retornante_manifestacao.registrar_acerto(
                            disparo,
                            {"rect": rect_boss, "retornante_id": "boss2"},
                            tempo_atual,
                            (pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2),
                        )
                        if vida_boss2 > 0:  # Verifica se o chefe está vivo antes de aplicar dano
                            if random.random() <= chance_critico:  # 10% de chance de dano crítico
                                dano = dano_person_hit * fator_dano_aureas(tempo_atual) * 3  # Valor do dano crítico é 3 vezes o dano normal
                                cor = (255, 255, 0)  # Amarelo (RGB)
                                fonte_dano = fonte_dano_critico
                            else:
                                dano = dano_person_hit * fator_dano_aureas(tempo_atual)
                                cor = (255, 0, 0)  # Vermelho (RGB)
                                fonte_dano = fonte_dano_normal
                            
                            if boss_escudo_ativo:
                                dano = max(1, int(dano * 0.1))

                        # Ativar veneno no Boss com 50% de chance, se ainda não estiver envenenado
                        if random.random() < 0.5 and not boss_envenenado and Poison_Active:
                            boss_envenenado = True
                            global duracao_veneno_boss
                            dano_por_tick_veneno_boss = vida_maxima_boss2 * Dano_Veneno_Acumulado
                            duracao_veneno_boss = 8000 + cartas_compradas.get("Poison", 0) * 100
                            tempo_inicio_veneno_boss = pygame.time.get_ticks()
                            ultimo_tick_veneno_boss = pygame.time.get_ticks()

                        if acerto_prismatico["critico"]:
                            dano *= prismatica_manifestacao.FEIXE_CRITICO_MULT
                            cor = (235, 255, 255)
                            fonte_dano = fonte_dano_critico
                        if acerto_retornante["critico"]:
                            dano *= retornante_manifestacao.PULSO_CRITICO_COSTAS_MULT
                            cor = (235, 225, 255)
                            fonte_dano = fonte_dano_critico
                        dano *= insana_aurea.dano_mult_disparo(disparo)
                        dano *= voraz_aurea.dano_mult_disparo(disparo)
                        dano *= lacerante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= prismatica_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= retornante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= parasitica_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= condutora_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= gravitante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= ancorada_manifestacao.multiplicador_dano_disparo(disparo)
                        dano *= lacerante_manifestacao.multiplicador_dano_boss(disparo)
                        dano = boss_manifestacao_effects.aplicar_efeito_boss(disparo, dano, tempo_atual, efeitos_texto, rect_boss, "boss2")

                        # Renderizar texto do dano
                        tempo_texto_dano = pygame.time.get_ticks()
                        dano = dano_boss_mitigado(dano, 2, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                        registrar_dano_boss(efeitos_texto, dano, pos_x_chefe2 + chefe_largura2 // 2, pos_y_chefe2 - 24, tempo_atual, cor)
                        vida_boss2 -= dano
                        if (vida_boss2 <= 0 or (Ultimo_Estalo and vida_boss2 <= limiar_execucao_boss(Executa_inimigo) * vida_maxima_boss2)):
                            if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                largura_disparo += 0.095
                                altura_disparo += 0.095
                        if not (acerto_prismatico["manter_disparo"] or acerto_retornante["manter_disparo"]):
                            estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)

                        # Roubo de vida
                        if quantidade_roubo_vida > 0:
                            vida += (vida_maxima - vida) * quantidade_roubo_vida

                # Aplicar dano de veneno no Boss se ele estiver envenenado
                if boss_envenenado:
                    tempo_atual = pygame.time.get_ticks()

                    # Aplicar dano a cada 500 ms
                    if tempo_atual - ultimo_tick_veneno_boss >= INTERVALO_TICK_VENENO:
                        vida_boss2 -= dano_boss_mitigado(dano_por_tick_veneno_boss, 2, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0), tipo_dano="veneno")
                        ultimo_tick_veneno_boss = tempo_atual

                    # Exibir texto do dano de veneno (1.5 segundos)
                    if tempo_atual - ultimo_tick_veneno_boss <= 1500:
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
            # Verifica se a pontuação atingiu o custo e se o jogador pressionou o botão da loja
            modo_loja_normal = Variaveis.obter_modo_cartas() != "drops"
            abrir_loja_manual = modo_loja_normal and (Variaveis.verificar_input("Comprar na loja") or (joystick and joystick.get_button(3)))
            if abrir_loja_manual and multiplayer_coop.modo_multiplayer():
                if pontuacao_exib >= custo_carta_atual:
                    multiplayer_coop.solicitar_acao("loja", 2)
                abrir_loja_manual = False
            if multiplayer_coop.acao_confirmada("loja", 2):
                abrir_loja_manual = True
            if abrir_loja_manual:
                Variaveis.cancelar_aviso_loja_forcada()
            if modo_loja_normal:
                Variaveis.tentar_ativar_larapio_normal(pontuacao_exib, custo_carta_atual, tempo_atual, efeitos_texto)
            if (pontuacao_exib >= custo_carta_atual) and abrir_loja_manual:
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





            pontuacao_exib, pontuacao_magia = Variaveis.atualizar_e_desenhar_larapios_pontos(
                tela, tempo_atual, pos_x_personagem, pos_y_personagem,
                largura_personagem, altura_personagem,
                pontuacao_exib, pontuacao_magia, custo_carta_atual, efeitos_texto
            )

            cooldowns = {
                "disparo": max(0.0, (intervalo_disparo_racional(intervalo_disparo, aurea, racional_dilatacao_fim, tempo_atual) - (tempo_atual - tempo_ultimo_disparo)) / 1000.0),
                "teleporte": max(0.0, (tempo_cooldown_dash - (pygame.time.get_ticks() - tempo_ultimo_dash)) / 1000.0),
                "onda": max(0.0, (cooldown_habilidade * voraz_aurea.bonus_cooldown(estado_voraz, aurea) * parasitica_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * lacerante_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * condutora_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) - (tempo_atual - tempo_ultimo_uso_habilidade)) / 1000.0),
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

                if deve_desenhar_habilidades(
                    (pos_x_personagem, pos_y_personagem), (largura_personagem, altura_personagem)
                ):
                    # Desenhar habilidades na tela
                    desenhar_habilidades(tela, cooldowns, dispositivo_ativo, (pos_x_personagem, pos_y_personagem))
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
                movimento_pressionado,
                ultima_tecla_movimento,
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
                Variaveis.tentar_ativar_larapio_hard(pontuacao_exib, custo_carta_atual, tempo_atual, efeitos_texto)
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


            # Blizzard Event System: Update & Draw Overlay and effects
            tempo_atual = pygame.time.get_ticks()
            if not blizzard_ativo:
                if tempo_atual - tempo_ultimo_blizzard >= intervalo_blizzard:
                    blizzard_ativo = True
                    tempo_inicio_blizzard = tempo_atual
            else:
                if tempo_atual - tempo_inicio_blizzard >= duracao_blizzard:
                    blizzard_ativo = False
                    tempo_ultimo_blizzard = tempo_atual

            # Draw Blizzard Overlay and Effects
            if blizzard_ativo:
                # 1. Fog/Snow overlay
                blizzard_surf = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
                blizzard_surf.fill((240, 248, 255, 60)) # AliceBlue with alpha 60
                
                # Draw wind particles (fast horizontal white lines)
                for _ in range(7):
                    wx = random.randint(0, largura_tela)
                    wy = random.randint(0, altura_tela)
                    wlen = random.randint(60, 160)
                    pygame.draw.line(blizzard_surf, (255, 255, 255, 170), (wx, wy), (wx + wlen, wy - random.randint(2, 5)), 2)
                tela.blit(blizzard_surf, (0, 0))
                
                # 2. Text Announcement (warning)
                if (tempo_atual // 250) % 2 == 0:
                    fonte_blizzard = pygame.font.Font(None, 40)
                    txt_warn = fonte_blizzard.render("TEMPESTADE DE NEVE (LENTIDÃO)!", True, (0, 220, 255))
                    rect_warn = txt_warn.get_rect(center=(largura_tela // 2, 70))
                    # Draw a dark background shadow for readability
                    shadow_surf = pygame.Surface((rect_warn.width + 20, rect_warn.height + 10), pygame.SRCALPHA)
                    shadow_surf.fill((0, 0, 0, 160))
                    tela.blit(shadow_surf, (rect_warn.x - 10, rect_warn.y - 5))
                    tela.blit(txt_warn, rect_warn)

            Variaveis.desenhar_refragmentacao_rewind(tela, tempo_atual)
            Variaveis.desenhar_overlay_vida_critica(tela, vida, vida_maxima, tempo_atual)

            desenhar_hud_fase(
                tela, vida, vida_maxima, pontuacao_exib, custo_carta_atual,
                pontuacao_magia, cooldowns, dispositivo_ativo,
                eliminacoes_consecutivas, bonus_pontuacao, aurea,
                escudo_devota_ativo, pos_x_personagem, pos_y_personagem,
                largura_personagem, altura_personagem
            )
            voraz_aurea.desenhar_voraz(tela, estado_voraz, aurea, tempo_atual, largura_tela, config_graficos, player_pos=(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem))

            Variaveis.aplicar_tremor_dano_tela(tela, tempo_atual, tempo_ultimo_hit_inimigo, piscando_vida)

            tela.blit(cursor_imagem, (mouse_x, mouse_y))

            exibir_cronometro(tela)

            multiplayer_coop.desenhar_status_acao(tela, fonte, "loja", 2)
            multiplayer_coop.desenhar_status_acao(tela, fonte, "pause", 2)
            multiplayer_coop.desenhar_status_acao(
                tela,
                fonte,
                "boss2",
                2,
                delay_ms=4000,
                assumir_sim_apos_ms=multiplayer_coop.COOP_SILENCIO_CONFIRMA_MS,
            )
            multiplayer_coop.desenhar_diagnostico(tela, fonte)
            pygame.display.flip()
            dt_ms = FPS.tick(config_graficos.get("fps_limite", 60))  # Limita a taxa de quadros conforme configuração
            dt = max(0.05, min(3.0, dt_ms / 16.666667))
            dt *= condutora_manifestacao.fator_tempo_registrador(manifestacao_ativa, tempo_atual)
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
