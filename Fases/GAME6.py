
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
from dados_manifestacoes import registrar_conclusao_fase
from build_runtime import fase_disponivel
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
    atualizar_ciclo_impulsiva,
    cooldown_teleporte_vanguarda,
    criar_estado_devota,
    criar_estado_impulsiva,
    fator_dano_devota,
    fator_dano_impulsiva,
    fator_velocidade_devota,
    fator_velocidade_impulsiva,
    quebrar_frenesi_impulsiva,
    consumir_multiplicador_panico_impulsiva,
    consumir_cura_absorcao_devota,
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
estado_impulsiva = criar_estado_impulsiva()
estado_devota = criar_estado_devota(False)
vanguarda_fogo_fim = 0
pressao_pos_boss_spawn = criar_estado_pressao_pos_boss()

def reiniciar_estados_aureas_fase(aurea_atual):
    global estado_impulsiva, estado_devota, vanguarda_fogo_fim
    estado_impulsiva = criar_estado_impulsiva()
    estado_devota = criar_estado_devota(aurea_atual == "Devota", pygame.time.get_ticks())
    vanguarda_fogo_fim = 0

def fator_dano_aureas(agora_ms=None):
    agora_ms = pygame.time.get_ticks() if agora_ms is None else agora_ms
    import condutora_manifestacao
    return (fator_dano_impulsiva(aurea, estado_impulsiva) *
            fator_dano_devota(aurea, estado_devota, agora_ms) *
            condutora_manifestacao.obter_multiplicador_dano_and(agora_ms))

def incendiar_vanguarda_proximos(agora_ms):
    if aurea != "Vanguarda":
        return
    centro_x = pos_x_personagem + largura_personagem // 2
    centro_y = pos_y_personagem + altura_personagem // 2
    alcance = max(76, int(max(largura_personagem, altura_personagem) * 1.45))
    for inimigo in inimigos_comum:
        rect = inimigo.get("rect")
        if rect is None or inimigo.get("invisivel", False):
            continue
        dist = math.hypot(rect.centerx - centro_x, rect.centery - centro_y)
        if dist <= alcance + max(rect.width, rect.height) * 0.4:
            inimigos_em_chamas[id(inimigo)] = agora_ms

def aplicar_hit_jogador(dano_bruto, respeitar_resistencia=True, ativar_vanguarda=True):
    global vida, escudo_devota_ativo, tempo_ultimo_escudo, vanguarda_fogo_fim, imune_tempo_restante
    global impulsiva_ativa, tipo_buff_impulsiva, eliminacoes_consecutivas_impulsiva
    global eliminacoes_consecutivas, bonus_pontuacao, tempo_ultimo_hit_inimigo, piscando_vida
    agora_ms = pygame.time.get_ticks()
    if imune_tempo_restante > 0:
        return 0
    if ativar_vanguarda and aurea == "Vanguarda":
        vanguarda_fogo_fim = max(vanguarda_fogo_fim, agora_ms + 5000)
        incendiar_vanguarda_proximos(agora_ms)
    import condutora_manifestacao
    if condutora_manifestacao.tentar_absorver_dano_nand(agora_ms):
        efeitos_texto.append({"texto": "BLOQUEIO LÓGICO", "x": pos_x_personagem - 28, "y": pos_y_personagem - 28, "tempo_inicio": agora_ms, "cor": (104, 255, 214)})
        return 0
    absorvido, escudo_devota_ativo, escudo_quebrou = absorver_hit_devota(aurea, escudo_devota_ativo, estado_devota, agora_ms)
    if absorvido:
        vida, cura_devota = consumir_cura_absorcao_devota(aurea, estado_devota, vida, vida_maxima)
        if cura_devota > 0:
            efeitos_texto.append({"texto": f"+{cura_devota} FE", "x": pos_x_personagem + 8, "y": pos_y_personagem - 48, "tempo_inicio": agora_ms, "cor": (255, 225, 90)})
        if escudo_quebrou:
            tempo_ultimo_escudo = agora_ms
            efeitos_texto.append({"texto": "FE ARDENTE: +DANO", "x": pos_x_personagem - 28, "y": pos_y_personagem - 28, "tempo_inicio": agora_ms, "cor": (80, 180, 255)})
        else:
            cargas = estado_devota.get("cargas", 0)
            efeitos_texto.append({"texto": f"ESCUDO DEVOTA {cargas}/3", "x": pos_x_personagem - 28, "y": pos_y_personagem - 28, "tempo_inicio": agora_ms, "cor": (255, 210, 80)})
        return 0
    nivel_queda = quebrar_frenesi_impulsiva(aurea, estado_impulsiva)
    if nivel_queda:
        impulsiva_ativa = False
        tipo_buff_impulsiva = None
        eliminacoes_consecutivas_impulsiva = 0
        efeitos_texto.append({"texto": f"PANICO N{nivel_queda}", "x": pos_x_personagem, "y": pos_y_personagem - 34, "tempo_inicio": agora_ms, "cor": (255, 70, 70)})
    dano_final = float(dano_bruto)
    if respeitar_resistencia:
        dano_final -= Resistencia
    dano_final = max(0.0, dano_final)
    mult_panico = consumir_multiplicador_panico_impulsiva(aurea, estado_impulsiva)
    if mult_panico > 1.0:
        dano_final *= mult_panico
    dano_final = int(dano_final)
    if dano_final > 0:
        vida -= dano_final
        eliminacoes_consecutivas = 0
        bonus_pontuacao = 0
        tempo_ultimo_hit_inimigo = agora_ms
        piscando_vida = True
    return dano_final

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

current_time_vortex = pygame.time.get_ticks()

# Variáveis para rastrear o texto de dano
texto_dano = None
tempo_texto_dano = 0

velocidade_inimigo2=1.70
velocidade_disparo_inimigo = 3  

estalos = aplicar_volume_som(pygame.mixer.Sound("Sounds/Estalo.mp3"), config_audio, canal="efeitos", volume_maximo=1.0)

Hit_inimigo2 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Inimigo1_hit.wav"), config_audio, canal="efeitos", volume_maximo=1.0)

Disparo_Geo = aplicar_volume_som(pygame.mixer.Sound("Sounds/Disparo_Geo.wav"), config_audio, canal="efeitos", volume_maximo=0.08)

Disparo_Inimig_Som = aplicar_volume_som(pygame.mixer.Sound("Sounds/frog.mp3"), config_audio, canal="efeitos", volume_maximo=0.8)

Musica_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase_boas.mp3"), config_audio, canal="musica", volume_maximo=0.06)

Som_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Neve.wav"), config_audio, canal="musica", volume_maximo=0.07)

Som_portal = aplicar_volume_som(pygame.mixer.Sound("Sounds/Portal.mp3"), config_audio, canal="efeitos", volume_maximo=0.06)



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
toque=0
intervalo_disparo_inimigo = 1500  
tempo_ultimo_disparo_inimigo = pygame.time.get_ticks()  # Adicione esta variável global para controlar o tempo do último disparo de cada inimigo


nivel_ameaca = inimigos_eliminados // 10
tempo_ultimo_inimigo_apos_morte = pygame.time.get_ticks()
# Adicione esta variável global para controlar o tempo do último disparo de cada inimigo
tempo_ultimo_disparo_inimigo = pygame.time.get_ticks()
cronometro_pausado = False
tempo_boss_entrada_fim = 0
retomar_cronometro()

# Carregar a imagem do mapa
mapa = pygame.image.load(mapa_path6).convert()
mapa = pygame.transform.scale(mapa, (largura_tela, altura_tela))
boss4_2_img = pygame.transform.scale(pygame.image.load("Sprites/Boss6.png").convert_alpha(), (chefe_largura4, chefe_altura4))
frames_chefe4_1 = [
    pygame.transform.scale(pygame.image.load("Sprites/Boss6.png").convert_alpha(), (chefe_largura4, chefe_altura4)),
    pygame.transform.scale(pygame.image.load("Sprites/Boss6.png").convert_alpha(), (chefe_largura4, chefe_altura4)),
]


disparos_inimigos = []
areas_sarcas = []
ferida_espinhosa_ate = 0
preso_em_sarcas_ate = 0
fator_sarcas_movimento = 1.0

# Configurações do loop principal
relogio = pygame.time.Clock()
tempo_passado = 0
frame_atual = 0
frame_atual_disparo = 0

# Atualizar a última direção da personagem
ultima_tecla_movimento = None
movimento_pressionado = False

# as seguintes variáveis para controle do tempo de hit do inimigo
tempo_ultimo_hit_inimigo = pygame.time.get_ticks()

# --- EFEITOS VFX DE INIMIGOS ---
enemy_particles = []

def spawn_enemy_particle(tipo, x, y, **kwargs):
    if not config_graficos.get("particulas_ativas", True):
        return
    
    agora = pygame.time.get_ticks()
    p = {
        "tipo": tipo,
        "x": float(x),
        "y": float(y),
        "inicio": agora,
        "vida": kwargs.get("vida", random.randint(600, 1000)),
        "cor": kwargs.get("cor", (116, 255, 130)),
        "tamanho": kwargs.get("tamanho", random.uniform(2, 5)),
        "vx": kwargs.get("vx", 0.0),
        "vy": kwargs.get("vy", 0.0),
    }
    
    if tipo == "spore":
        p["phase"] = random.uniform(0, math.tau)
        p["freq"] = random.uniform(0.005, 0.012)
        p["amp"] = random.uniform(3, 8)
        p["base_x"] = float(x)
    elif tipo == "dust":
        p["tamanho_max"] = kwargs.get("tamanho_max", random.uniform(10, 16))
    elif tipo == "spark":
        p["gravity"] = kwargs.get("gravity", 0.2)
    elif tipo == "shockwave":
        p["raio_max"] = kwargs.get("raio_max", 40)
        p["largura"] = kwargs.get("largura", 2)
    elif tipo == "afterimage":
        p["image"] = kwargs.get("image")
        p["rect"] = kwargs.get("rect")
        
    enemy_particles.append(p)

def atualizar_e_desenhar_vfx_inimigos(tela, tempo_atual):
    global enemy_particles
    novas = []
    
    dt_local = globals().get("dt", 1.0)
    
    for p in enemy_particles:
        tempo_decorrido = tempo_atual - p["inicio"]
        if tempo_decorrido >= p["vida"]:
            continue
            
        progresso = tempo_decorrido / p["vida"]
        alpha = int(255 * (1.0 - progresso))
        
        if p["tipo"] == "spore":
            p["vy"] += -0.015 * dt_local
            p["y"] += p["vy"] * dt_local
            p["base_x"] += p["vx"] * dt_local
            p["x"] = p["base_x"] + math.sin(tempo_atual * p["freq"] + p["phase"]) * p["amp"]
            
            tam = max(1, int(p["tamanho"] * (1.0 - progresso * 0.5)))
            surf = pygame.Surface((tam * 4, tam * 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p["cor"], alpha // 3), (tam * 2, tam * 2), tam * 2)
            pygame.draw.circle(surf, (255, 255, 255, alpha), (tam * 2, tam * 2), tam)
            tela.blit(surf, (int(p["x"] - tam * 2), int(p["y"] - tam * 2)))
            
        elif p["tipo"] == "dust":
            p["x"] += p["vx"] * dt_local
            p["y"] += p["vy"] * dt_local
            p["vx"] *= 0.95
            p["vy"] *= 0.95
            
            tam = int(p["tamanho"] + (p["tamanho_max"] - p["tamanho"]) * progresso)
            surf = pygame.Surface((tam * 2, tam * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p["cor"], alpha // 4), (tam, tam), tam)
            tela.blit(surf, (int(p["x"] - tam), int(p["y"] - tam)))
            
        elif p["tipo"] == "spark":
            p["vy"] += p["gravity"] * dt_local
            p["x"] += p["vx"] * dt_local
            p["y"] += p["vy"] * dt_local
            
            tam = max(1, int(p["tamanho"] * (1.0 - progresso)))
            pygame.draw.circle(tela, (*p["cor"], alpha), (int(p["x"]), int(p["y"])), tam)
            
        elif p["tipo"] == "shockwave":
            raio = int(p["tamanho"] + (p["raio_max"] - p["tamanho"]) * progresso)
            diametro = raio * 2
            surf = pygame.Surface((diametro + 4, diametro + 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p["cor"], alpha), (raio + 2, raio + 2), raio, max(1, int(p["largura"] * (1.0 - progresso))))
            tela.blit(surf, (int(p["x"] - raio - 2), int(p["y"] - raio - 2)))
            
        elif p["tipo"] == "afterimage":
            try:
                img_fade = p["image"].copy()
                img_fade.set_alpha(int(100 * (1.0 - progresso)))
                tela.blit(img_fade, p["rect"])
            except:
                pass
            
        novas.append(p)
        
    enemy_particles = novas
# esta variável global para controlar o piscar da barra de vida
piscando_vida = False

# Frames proprios da fase 6. As artes foram desenhadas olhando para a direita.
def carregar_frame_por_altura(path, altura_destino):
    imagem = pygame.image.load(path).convert_alpha()
    largura_original, altura_original = imagem.get_size()
    escala = altura_destino / max(1, altura_original)
    tamanho = (max(1, int(largura_original * escala)), max(1, int(altura_destino)))
    return pygame.transform.smoothscale(imagem, tamanho)


def espelhar_frames(frames):
    return [pygame.transform.flip(frame, True, False) for frame in frames]


def escalar_surface(surface, fator):
    largura, altura = surface.get_size()
    tamanho = (max(1, int(largura * fator)), max(1, int(altura * fator)))
    return pygame.transform.smoothscale(surface, tamanho)


altura_aguilhao = int(altura_inimigo * 1.28)
altura_aguilhao_bote = int(altura_aguilhao * 0.78)
altura_enredador = int(altura_inimigo * 1.68)
frames_aguilhao_direita = [
    carregar_frame_por_altura("Sprites/aguilhao1.png", altura_aguilhao),
    carregar_frame_por_altura("Sprites/aguilhao2.png", altura_aguilhao_bote),
]
frames_aguilhao_esquerda = espelhar_frames(frames_aguilhao_direita)
frames_enredador_direita = [
    carregar_frame_por_altura("Sprites/enredador1.png", altura_enredador),
    carregar_frame_por_altura("Sprites/enredador2.png", altura_enredador),
]
frames_enredador_esquerda = espelhar_frames(frames_enredador_direita)
frames_aguilhao = frames_aguilhao_direita
frames_enredador = frames_enredador_direita
frames_inimigo = frames_aguilhao_direita + frames_enredador_direita
frames_inimigo_esquerda4 = frames_aguilhao_esquerda
frames_inimigo_direita4 = frames_aguilhao_direita

vida_inimigo_maxima = multiplayer_coop.aplicar_multiplicador_vida_inimigo(vida_inimigo_comum_inicial(30))
vida_inimigo= vida_inimigo_maxima
vida_boss4 = multiplayer_coop.aplicar_multiplicador_vida_boss(vida_boss4)
vida_maxima_boss4 = vida_boss4
carregar_atributos_na_fase=True
comando_direção_petro=True
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
        "largura_disparo": largura_disparo,
        "altura_disparo": altura_disparo,
    }

    with open('saves/atributos.json', 'w') as file:
        json.dump(atributos, file)

def carregar_atributos():
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

def criar_zona_nula(x, y, tempo_criacao):
    zona_nula = {
        "x": x,
        "y": y,
        "nascimento": tempo_criacao  # Momento em que a zona nula foi criada
    }
    zonas_nulas.append(zona_nula)


def calcular_direcao_projeteis(projetil, pos_x_personagem, pos_y_personagem):
    # Calcular a diferença de posição entre o projétil e o personagem
    dx = pos_x_personagem - projetil["x"]
    dy = pos_y_personagem - projetil["y"]
    
    # Calcular a distância entre os dois pontos
    distancia = math.sqrt(dx**2 + dy**2)
    
    # Normalizar a direção
    if distancia != 0:
        dx /= distancia
        dy /= distancia
    
    # Definir a velocidade do projétil
    velocidade_projeteis = 1.50  
    
    # Atualizar a direção do projétil
    projetil["dx"] = dx * velocidade_projeteis
    projetil["dy"] = dy * velocidade_projeteis






    
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
    global personagem_imovel, tempo_ultimo_atingido, angulo_inclinacao_personagem
    global vida_inimigo_maxima, Resistencia_petro, dano_inimigo_perto, vida_maxima_petro, dano_petro, dano_inimigo_longe
    global inimigos_eliminados, pontuacao, pontuacao_exib, eliminacoes_consecutivas, bonus_pontuacao, boss_vivo4
    global vida_boss4, vida_maxima_boss4, Valor_Bonus
    global racional_dilatacao_fim, racional_dilatacao_proximo_uso

    # Se o personagem estiver imóvel, não atualize a posição
    if personagem_imovel:
        return

    direcao_atual = 'stop'
    dx, dy = 0, 0
    velocidade_movimento = (
        velocidade_personagem
        * fator_movimento_racional(aurea, racional_dilatacao_fim)
        * fator_velocidade_impulsiva(aurea, estado_impulsiva)
        * fator_velocidade_devota(aurea, estado_devota)
        * aureas_avancadas.fator_velocidade_jogador(globals().get("estado_aureas_avancadas"), aurea, tempo_atual)
        * condutora_manifestacao.fator_ruido_logico(manifestacao_ativa, tempo_atual)
        * condutora_manifestacao.obter_fator_velocidade_xor(tempo_atual)
        * globals().get("fator_sarcas_movimento", 1.0)
    )

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
                gerar_fragmentos_morte(inimigo, 4)
                if inimigo in inimigos_comum:
                    inimigos_comum.remove(inimigo)
                
                # Escalonamento supremo (Fase 4)
                mult = 1.0 + (nivel_ameaca * 0.20)
                vida_inimigo_maxima += ganho_vida_inimigo_comum(1.0 * mult)
                Resistencia_petro += 0.03 * mult
                dano_inimigo_perto += 0.12 * mult
                dano_person_hit += 0.15 * mult
                vida_maxima_petro += 1.5 * mult
                dano_petro += 0.015 * mult
                dano_inimigo_longe += 0.03 * mult

                inimigos_eliminados += 1
                ganho = int(200 * (1 + math.log10(inimigos_eliminados + 1)))
                pontuacao += ganho

                if Mercenaria_Active:
                    eliminacoes_consecutivas += 1
                    pontuacao_exib += ganho + bonus_pontuacao
                    if eliminacoes_consecutivas % 5 == 0:
                        bonus_pontuacao = min(1000, bonus_pontuacao + Valor_Bonus)
                else:
                    pontuacao_exib += ganho

                if not boss_vivo4:
                    vida_boss4 += ganho_progressao_boss(30 * mult)
                    vida_maxima_boss4 = vida_boss4

        # Dano ao Boss 4
        if boss_vivo4:
            bx = pos_x_boss4 + chefe_largura4 // 2
            by = pos_y_boss4 + chefe_altura4 // 2
            dist_boss = math.hypot(bx - cx_t, by - cy_t)
            if dist_boss <= raio_choque:
                vida_boss4 -= dano_boss_mitigado(dano_choque, 4, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                efeitos_texto.append({
                    "texto": f"-{int(dano_choque)}",
                    "x": pos_x_boss4 + chefe_largura4 // 2,
                    "y": pos_y_boss4 - 20,
                    "tempo_inicio": pygame.time.get_ticks(),
                    "cor": (0, 191, 255)
                })

    # Atualizar o cooldown do dash
    tempo_cooldown_dash_efetivo = cooldown_teleporte_vanguarda(tempo_cooldown_dash, aurea, inimigos_comum, inimigos_em_chamas, duracao_incendio_vanguarda, pygame.time.get_ticks())
    if cooldown_dash and pygame.time.get_ticks() - tempo_ultimo_dash > tempo_cooldown_dash_efetivo:
        cooldown_dash = False

    return direcao_atual


# Antes do loop principal, crie uma lista para armazenar os inimigos
inimigos_comum = []

tempo_ultima_criacao_gelo = pygame.time.get_ticks()
intervalo_criacao_gelo = 2000  # 10 segundos


def criar_disparo_inimigo(pos_inimigo, pos_personagem, tipo="semente"):
    Disparo_Inimig_Som.play()
    dx = pos_personagem[0] - pos_inimigo[0]
    dy = pos_personagem[1] - pos_inimigo[1]
    dist = max(1, math.sqrt(dx ** 2 + dy ** 2))

    
    
    direcao_disparo_inimigo = (dx / dist * velocidade_disparo_inimigo, dy / dist * velocidade_disparo_inimigo)

    return {
        "rect": pygame.Rect(pos_inimigo[0], pos_inimigo[1], largura_disparo, altura_disparo),
        "velocidade": direcao_disparo_inimigo,
        "tipo": tipo,
        "nascimento": pygame.time.get_ticks(),
    }


def criar_inimigo(x, y):
    tipo = "enredador" if random.random() < 0.32 else "aguilhao"
    if tipo == "enredador":
        vida_base = int(vida_inimigo_maxima * 1.35)
        image = frames_enredador_direita[0]
    else:
        vida_base = int(vida_inimigo_maxima * 0.9)
        image = frames_aguilhao_direita[0]
    agora = pygame.time.get_ticks()
    rect = image.get_rect(topleft=(x, y))
    return {
        "rect": rect,
        "image": image,
        "vida": vida_base,
        "vida_maxima": vida_base,
        "tipo": tipo,
        "pos_x": float(x),
        "pos_y": float(y),
        "direcao_sprite": "right",
        "pulso_offset": random.randint(0, 1500),
        "atacando_ate": 0,
        "enredador_estado_mov": "parado",
        "enredador_proxima_troca": agora + random.randint(15000, 17500),
        "proxima_investida": agora + random.randint(900, 1900),
        "investida_ate": 0,
        "proximo_disparo": agora + random.randint(1200, 2600),
        "spawn_progress": 0.0,
        "spawn_complete": False,
        "vida_anterior": vida_base,
        "ultimo_trail": 0,
        "hit_flash_timer": 0,
    }


def criar_area_sarcas(x, y, raio=74, duracao=5200, origem="enredador"):
    areas_sarcas.append({
        "x": int(x),
        "y": int(y),
        "raio": int(raio),
        "fim": pygame.time.get_ticks() + int(duracao),
        "ultimo_tick": 0,
        "origem": origem,
    })


def soltar_tufo_aguilhao(inimigo):
    if inimigo.get("tipo") == "aguilhao" and random.random() < 0.38:
        criar_area_sarcas(inimigo["rect"].centerx, inimigo["rect"].centery, raio=48, duracao=3600, origem="aguilhao")


def desenhar_area_sarcas(tela, area, tempo_atual):
    pulso = 0.55 + 0.45 * math.sin(tempo_atual * 0.012 + area["x"] * 0.01)
    raio = int(area["raio"] * (0.92 + pulso * 0.08))
    surf = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
    cor_base = (42, 165, 76, 78) if area.get("origem") == "enredador" else (34, 125, 58, 92)
    pygame.draw.circle(surf, cor_base, (raio + 4, raio + 4), raio)
    pygame.draw.circle(surf, (128, 245, 120, 120), (raio + 4, raio + 4), raio, 2)
    for i in range(8):
        ang = tempo_atual * 0.0015 + i * math.tau / 8
        x1 = raio + 4 + math.cos(ang) * raio * 0.2
        y1 = raio + 4 + math.sin(ang) * raio * 0.2
        x2 = raio + 4 + math.cos(ang) * raio * 0.92
        y2 = raio + 4 + math.sin(ang) * raio * 0.92
        pygame.draw.line(surf, (150, 255, 125, 130), (x1, y1), (x2, y2), 2)
    tela.blit(surf, (area["x"] - raio - 4, area["y"] - raio - 4))

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
    global inimigos_comum
    if multiplayer_coop.eh_cliente():
        return

    limite_inimigos = max_inimigos4 if limite_inimigos is None else limite_inimigos
    if len(inimigos_comum) < limite_inimigos:
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
    chance = 0.05 # 5%
    if random.random() < chance:
        tamanho_moeda = (36, 36)  # Novo tamanho desejado
        sprite_redimensionada = pygame.transform.scale(sprite_moeda, tamanho_moeda)
        rect = sprite_redimensionada.get_rect(center=posicao)
        moedas_soltadas.append({
            "rect": rect,
            "image": sprite_redimensionada
        })
        



tempo_ultimo_escudo = pygame.time.get_ticks()
tempo_parado_person = pygame.time.get_ticks() 
tempo_ultimo_disparo = pygame.time.get_ticks()
upgrades = carregar_upgrade_aureas("saves/aureas_upgrade.json")

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
x = 0
y = 0

def executar_jogo(game_manager=None):
    global dt
    global aurea
    global tempo_parado_person, tempo_ultimo_escudo
    global direcao_atual, tempo_ultimo_disparo
    global pos_x_boss4, pos_y_boss4
    global disparo_preparando, disparo_frame_atual, tempo_ultimo_frame_preparo_disparo, angulo_disparo_preparado, DISPARO_PREPARO_FRAME_MS
    global joystick, ondas_choque, gerar_fragmentos_morte, Chance_Sorte, Dano_Veneno_Acumulado, Executa_inimigo, Mercenaria_Active, Musica_tema_fases, Petro_active, Poison_Active, Resistencia, Resistencia_petro, Som_tema_fases, Tempo_cura, Ultimo_Estalo, Valor_Bonus, altura_disparo, bonus_pontuacao, boss_envenenado, boss_vivo4, carregar_atributos_na_fase, cartas_compradas, chance_critico, cooldown_dash, current_frame_disparo_boss, current_frame_index, dano, dano_inimigo_longe, dano_inimigo_perto, dano_person_hit, dano_petro, dano_por_tick_veneno_boss, disparos, disparos_inimigos, dispositivo_ativo, efeitos_texto, eliminacoes_consecutivas, eliminacoes_consecutivas_impulsiva, escudo_devota_ativo, estado_boss_atacando, fonte, frame_atual, impulsiva_ativa, imune_tempo_restante, indice_frame_vortex, inimigos_atingidos_por_onda, inimigos_comum, inimigos_eliminados, inimigos_em_chamas, intervalo_disparo, intervalo_disparo_inimigo, largura_disparo, last_frame_change, max_inimigos4, moedas_coletadas, moedas_soltadas, moedas_totais, movimento_pressionado, ondas, petro_evolucao, piscando_vida, pontuacao, pontuacao_exib, pontuacao_magia, porcentagem_cura, pos_x_personagem, pos_x_petro, pos_y_personagem, pos_y_petro, quantidade_roubo_vida, r_press, rect_boss, roubo_de_vida, running, sprite_moeda, teleportado, tempo_anterior_petro, tempo_ataque, tempo_atual, tempo_boss_entrada_fim, tempo_cooldown_dash, tempo_ultimo_dash, tempo_frame_disparo_boss, tempo_inicio_buff_impulsiva, tempo_inicio_veneno_boss, tempo_passado, tempo_texto_dano, tempo_ultima_atualizacao_direcao, tempo_ultima_regeneracao, tempo_ultimo_dano_vortex, tempo_ultimo_disparo_inimigo, tempo_ultimo_hit_inimigo, tempo_ultimo_inimigo, tempo_ultimo_uso_habilidade, texto_dano, tipo_buff_impulsiva, toque, trembo, ultima_direcao_animacao, ultimo_disparo, ultimo_tick_veneno_boss, velocidade_inimigo2, velocidade_personagem, vida, vida_boss4, vida_inimigo_maxima, vida_maxima, vida_maxima_boss4, vida_maxima_petro, vida_petro, vida_planeta, x, xp_petro, y, duracao_incendio_vanguarda, intervalo_escudo, comando_direção_petro
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
        tempo_ultimo_disparo = pygame.time.get_ticks()
        disparo_preparando = False
        disparo_frame_atual = 0
        tempo_ultimo_frame_preparo_disparo = 0
        angulo_disparo_preparado = 0.0
        DISPARO_PREPARO_FRAME_MS = 85
        coice_onda = criar_estado_coice_onda()
        
        Musica_tema_fases.play(loops=-1)
        Som_tema_fases.play(loops=-1)

        FPS=pygame.time.Clock()
        # Configurar e escalar as passivas das áureas
        upgrades = carregar_upgrade_aureas("saves/aureas_upgrade.json")
        ondas_choque = []
        nivel_devota = upgrades.get("Devota", 0)
        nivel_vanguarda = upgrades.get("Vanguarda", 0)
        estado_insana = insana_aurea.criar_estado_insana(upgrades.get("Insana", 0), pygame.time.get_ticks())
        estado_voraz = voraz_aurea.criar_estado_voraz(upgrades.get("Voraz", 0), pygame.time.get_ticks())
        estado_aureas_avancadas = aureas_avancadas.criar_estado(upgrades, aurea, pygame.time.get_ticks())
        globals()["estado_aureas_avancadas"] = estado_aureas_avancadas

        if aurea == "Devota":
            escudo_devota_ativo = True
            intervalo_escudo = max(8000, 22000 - (nivel_devota * 2500))
        else:
            escudo_devota_ativo = False

        if aurea == "Vanguarda":
            duracao_incendio_vanguarda = 5000 + (nivel_vanguarda * 1000)
        reiniciar_estados_aureas_fase(aurea)
        pygame.mouse.set_visible(False)
        cursor_imagem = pygame.image.load("Sprites/Ponteiro.png").convert_alpha()  # Ajuste o caminho
        cursor_tamanho = cursor_imagem.get_size()
        sprite_moeda = pygame.image.load("Sprites/moeda.png").convert_alpha()
        fragmentos_morte = []
        areas_sarcas[:] = []
        ferida_espinhosa_ate = 0
        preso_em_sarcas_ate = 0

        def gerar_fragmentos_morte(inimigo, fase):
            soltar_tufo_aguilhao(inimigo)
            voraz_aurea.criar_fragmento_abate(estado_voraz, aurea, inimigo["rect"].center, pygame.time.get_ticks(), 1)
            if not (config_graficos.get("particulas_ativas", True) and config_graficos.get("efeitos_visuais", True)):
                return
            
            rect_inimigo = inimigo["rect"]
            gerar_particulas_pontos(rect_inimigo)
            
            qualidade = config_graficos.get("qualidade_grafica", "alta")
            
            if qualidade == "alta":
                qtd_particulas = random.randint(35, 50)
                spawn_enemy_particle("shockwave", rect_inimigo.centerx, rect_inimigo.centery, tamanho=5, raio_max=60, cor=(127, 255, 0), vida=400, largura=3)
                for _ in range(random.randint(2, 4)):
                    smoke_x = rect_inimigo.centerx + random.uniform(-15, 15)
                    smoke_y = rect_inimigo.centery + random.uniform(-15, 15)
                    spawn_enemy_particle("dust", smoke_x, smoke_y, cor=(80, 110, 80), tamanho=6, tamanho_max=24, vx=random.uniform(-1, 1), vy=random.uniform(-1.5, 0.5), vida=random.randint(600, 1000))
            elif qualidade == "media":
                qtd_particulas = random.randint(20, 30)
                spawn_enemy_particle("dust", rect_inimigo.centerx, rect_inimigo.centery, cor=(80, 110, 80), tamanho=6, tamanho_max=16, vx=0, vy=-0.5, vida=600)
            else:
                qtd_particulas = random.randint(10, 18)
                
            for _ in range(qtd_particulas):
                px = random.uniform(rect_inimigo.left, rect_inimigo.right)
                py = random.uniform(rect_inimigo.top, rect_inimigo.bottom)
                vx = random.uniform(-4, 4)
                vy = random.uniform(-5, 2)
                
                if random.random() < 0.7:
                    color = random.choice([
                        (127, 255, 0),
                        (34, 139, 34),
                        (50, 205, 50),
                        (173, 255, 47),
                    ])
                else:
                    color = random.choice([
                        (218, 165, 32),
                        (139, 69, 19),
                        (107, 142, 35),
                    ])
                    
                size = random.uniform(3, 9)
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
                    "life": random.randint(30, 60)
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
                    "vrot": random.uniform(-10, 10),
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
                    color = (0, random.randint(180, 255), 255)
                elif choice < 0.7:
                    color = (255, 255, 255)
                else:
                    color = (random.randint(160, 220), 50, 255)
                    
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
                    "vida_inimigo_maxima": vida_inimigo_maxima,
                    "max_inimigos": max_inimigos4,
                    "tempo_cronometro": Variaveis.obter_tempo_decorrido(),
                    "inimigos_comum": Variaveis.serializar_inimigos_rewind(inimigos_comum),
                    "vida_boss": vida_boss4,
                    "r_press": bool(r_press)
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
                        pontuacao_magia = snap.get("pontuacao_magia", pontuacao_magia)
                        inimigos_eliminados = snap.get("inimigos_eliminados", inimigos_eliminados)
                        vida_inimigo_maxima = snap.get("vida_inimigo_maxima", vida_inimigo_maxima)
                        max_inimigos4 = snap.get("max_inimigos", max_inimigos4)
                        Variaveis.definir_tempo_cronometro(snap.get("tempo_cronometro", Variaveis.obter_tempo_decorrido()))
                        if "inimigos_comum" in snap:
                            inimigos_comum = Variaveis.restaurar_inimigos_rewind(snap.get("inimigos_comum"), frames_inimigo_esquerda4[0])
                        if snap.get("refragmentacao_rewind"):
                            imune_tempo_restante = max(imune_tempo_restante, 4000)
                            piscando_vida = False
                            Variaveis.aplicar_rewind_respawn_visual(pos_x_personagem, pos_y_personagem, direcao_atual, pygame.time.get_ticks())
                        if "vida_boss" in snap and snap["vida_boss"] is not None:
                            vida_boss4 = snap["vida_boss"]
                        if snap.get("r_press"):
                            r_press = True
                        Variaveis.snapshot_para_carregar = None
                except Exception as e:
                    registrar_erro("Fase 4: erro ao carregar atributos; usando padrao", e)
                Variaveis.limpar_cartas_no_chao()
                carregar_atributos_na_fase=False

            nivel_impulsiva = upgrades.get("Impulsiva", 0)
            eliminacoes_consecutivas_impulsiva, eventos_impulsiva = atualizar_ciclo_impulsiva(aurea, estado_impulsiva, eliminacoes_consecutivas_impulsiva, pygame.time.get_ticks(), nivel_impulsiva)
            impulsiva_ativa = bool(estado_impulsiva.get("ativa"))
            tipo_buff_impulsiva = "frenesi" if impulsiva_ativa else None
            for evento_impulsiva in eventos_impulsiva:
                texto_evento = "FRENESI DISSIPADO" if evento_impulsiva["tipo"] == "fim" else f"FRENESI N{evento_impulsiva.get('nivel', 0)}"
                if evento_impulsiva["tipo"] == "ascendeu":
                    texto_evento = f"ASCENSAO N{evento_impulsiva['nivel']}"
                efeitos_texto.append({"texto": texto_evento, "x": pos_x_personagem, "y": pos_y_personagem - 24, "tempo_inicio": pygame.time.get_ticks(), "cor": (255, 210, 70) if evento_impulsiva["tipo"] == "ascendeu" else (255, 100, 60)})

            nivel_impulsiva = upgrades.get("Impulsiva", 0)
            if False and impulsiva_ativa:
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
            fase_coop = multiplayer_coop.atualizar(4, pos_x_personagem, pos_y_personagem, direcao_atual, vida, vida_maxima, vida <= 0)
            if multiplayer_coop.aplicar_transicao_recebida(fase_coop, game_manager):
                raise CleanExit()
            mundo_coop = multiplayer_coop.sincronizar_mundo(
                4,
                inimigos_comum,
                criar_inimigo,
                boss={
                    "vida": vida_boss4,
                    "vida_maxima": vida_maxima_boss4,
                    "vivo": boss_vivo4,
                    "r_press": r_press,
                    "x": pos_x_boss4,
                    "y": pos_y_boss4,
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
                vida_boss4 = boss_coop.get("vida", vida_boss4)
                vida_maxima_boss4 = boss_coop.get("vida_maxima", vida_maxima_boss4)
                boss_vivo4 = bool(boss_coop.get("vivo", boss_vivo4))
                r_press_anterior = r_press
                r_press = bool(boss_coop.get("r_press", r_press))
                if r_press and not r_press_anterior:
                    tempo_boss_entrada_fim = pygame.time.get_ticks() + 2500
                pos_x_boss4 = boss_coop.get("x", pos_x_boss4)
                pos_y_boss4 = boss_coop.get("y", pos_y_boss4)
                pontuacao = economia_coop.get("pontuacao", pontuacao)
                pontuacao_exib = economia_coop.get("pontuacao_exib", pontuacao_exib)
                pontuacao_magia = economia_coop.get("pontuacao_magia", pontuacao_magia)
                if "tempo_cronometro" in economia_coop:
                    Variaveis.definir_tempo_cronometro(economia_coop.get("tempo_cronometro", Variaveis.obter_tempo_decorrido()))

            multiplayer_coop.processar_eventos_visuais(4, efeitos_texto, ondas_choque, gerar_particulas_pontos)
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
                        multiplayer_coop.solicitar_acao("pause", 4)
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
                                    gerar_fragmentos_morte(morto_circuito, 4)
                                    Variaveis.tentar_soltar_carta(morto_circuito["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                                    inimigos_comum.remove(morto_circuito)
                                    inimigos_eliminados += 1
                        elif parasitica_manifestacao.ativa(manifestacao_ativa):
                            mortos_eclosao, total_eclosao = parasitica_manifestacao.eclodir_todas(inimigos_comum, tempo_atual, efeitos_texto)
                            ondas.append(parasitica_manifestacao.criar_eclosao(px_centro, py_centro, tempo_atual, total_eclosao))
                            for morto_eclosao in mortos_eclosao:
                                if morto_eclosao in inimigos_comum:
                                    gerar_fragmentos_morte(morto_eclosao, 4)
                                    Variaveis.tentar_soltar_carta(morto_eclosao["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                                    inimigos_comum.remove(morto_eclosao)
                                    inimigos_eliminados += 1
                        elif retornante_manifestacao.ativa(manifestacao_ativa):
                            total_chamado = retornante_manifestacao.chamado_reverso(disparos, tempo_atual)
                            ondas.append(retornante_manifestacao.criar_chamado(px_centro, py_centro, tempo_atual, total_chamado))
                        elif prismatica_manifestacao.ativa(manifestacao_ativa):
                            ondas.append(prismatica_manifestacao.criar_prisma(
                                pos_mouse[0], pos_mouse[1], tempo_atual,
                                dano_person_hit, largura_mapa, altura_mapa
                            ))
                        elif lacerante_manifestacao.ativa(manifestacao_ativa):
                            ondas.append(lacerante_manifestacao.criar_fenda(px_centro, py_centro, angulo, tempo_atual, dano_person_hit))
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
            if multiplayer_coop.acao_confirmada("pause", 4):
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
                    registrar_erro("Fase 4: erro ao salvar atributos para pausa", e)
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
                multiplayer_coop.aguardar_barreira("pause_saida", 4, tela, fonte, "Aguardando o outro jogador voltar do pause...")
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
                        else verificar_colisao_disparo_inimigo(disparo, (inimigo["rect"].x, inimigo["rect"].y), largura_disparo, altura_disparo, largura_inimigo, altura_inimigo,inimigos_eliminados)
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
                        pos_texto = (inimigo["rect"].x + largura_inimigo // 2 - fonte_dano.size(texto_hit)[0] // 2, inimigo["rect"].y - 20)
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
                                gerar_fragmentos_morte(inimigo, 4)
                                inimigos_comum.remove(inimigo)
                            if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                largura_disparo += 0.095
                                altura_disparo += 0.095
                            posicao_inimigo = inimigo["rect"].center
                            soltar_moeda(posicao_inimigo)
                            Variaveis.tentar_soltar_carta(posicao_inimigo, tempo_atual, Chance_Sorte, inimigos_eliminados)
                            inimigos_eliminados += 1


                            # Multiplicador de Execução Máximo (25%)
                            mult_ex = 1.0 + (nivel_ameaca * 0.25)

                            vida_inimigo_maxima += ganho_vida_inimigo_comum(1.2 * mult_ex)
                            Resistencia_petro += 0.04 * mult_ex
                            dano_inimigo_perto += 0.15 * mult_ex
                            dano_person_hit += 0.2 * mult_ex
                            vida_maxima_petro += 2.0 * mult_ex
                            dano_petro += 0.02 * mult_ex
                            dano_inimigo_longe += 0.04 * mult_ex

                            ganho = int(250 * (1 + math.log10(inimigos_eliminados + 1)))
                            pontuacao += ganho

                            if not boss_vivo4:
                                vida_boss4 += ganho_progressao_boss(35 * mult_ex)
                                vida_maxima_boss4 = vida_boss4

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
                            gerar_fragmentos_morte(inimigo, 4)
                            inimigos_comum.remove(inimigo)
                            if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                largura_disparo += 0.095
                                altura_disparo += 0.095
                            inimigos_eliminados += 1


                            # --- ESCALONAMENTO SUPREMO (FASE 4) ---
                            mult = 1.0 + (nivel_ameaca * 0.20)

                            vida_inimigo_maxima += ganho_vida_inimigo_comum(1.0 * mult)
                            Resistencia_petro += 0.03 * mult
                            dano_inimigo_perto += 0.12 * mult
                            dano_person_hit += 0.15 * mult
                            vida_maxima_petro += 1.5 * mult
                            dano_petro += 0.015 * mult
                            dano_inimigo_longe += 0.03 * mult

                            # Pontuação otimizada para o "Rush" final
                            ganho = int(200 * (1 + math.log10(inimigos_eliminados + 1)))
                            pontuacao += ganho

                            if Mercenaria_Active:
                                eliminacoes_consecutivas += 1
                                pontuacao_exib += ganho + bonus_pontuacao
                                if eliminacoes_consecutivas % 5 == 0:
                                    bonus_pontuacao = min(1000, bonus_pontuacao + Valor_Bonus)
                            else:
                                pontuacao_exib += ganho

                            # Escalonamento exclusivo do Último Boss da rodada normal
                            if not boss_vivo4:
                                vida_boss4 += ganho_progressao_boss(30 * mult)
                                vida_maxima_boss4 = vida_boss4

                            break  # importante
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
            limite_inimigos_run = max_inimigos4 + bonus_limite_inimigos_sem_boss(
                tempo_decorrido_run,
                r_press or boss_vivo4,
                inimigos_eliminados,
                modo_dificil=Variaveis.obter_modo_cartas() == "drops",
            )
            pressao_spawn = calcular_pressao_spawn_pos_boss(
                pressao_pos_boss_spawn,
                tempo_atual,
                r_press and not boss_vivo4,
                len(inimigos_comum),
                inimigos_eliminados,
                limite_inimigos_run,
            )
            if tempo_atual - tempo_ultimo_inimigo >= pressao_spawn["intervalo_ms"] and pressao_spawn["lote"] > 0 and (spawn_inimigo or not boss_vivo4):
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

                if False and eliminacoes_consecutivas_impulsiva >= 5 and not impulsiva_ativa:
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

            tela.fill((255, 255, 255))
            tela.blit(mapa, (0, 0))


            # Desenha a personagem
            # Desenhar sombra do personagem
            desenhar_sombra(tela, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
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
                    novo_rect = frame_rotacionado.get_rect(center=(pos_x_personagem + largura_personagem//2, pos_y_personagem + altura_personagem//2))
                    desenhar_personagem_com_dano(tela, frame_rotacionado, novo_rect.x, novo_rect.y, tempo_atual, tempo_ultimo_hit_inimigo)
                else:
                    w_f, h_f = frame_para_desenhar.get_size()
                    bx = pos_x_personagem + (largura_personagem - w_f) // 2
                    by = pos_y_personagem + (altura_personagem - h_f)
                    desenhar_personagem_com_dano(tela, frame_para_desenhar, bx, by, tempo_atual, tempo_ultimo_hit_inimigo)
            else:
                desenhar_personagem_com_dano(tela, imagem_personagem_congelada, pos_x_personagem, pos_y_personagem, tempo_atual, tempo_ultimo_hit_inimigo)

            insana_aurea.desenhar_insana(
                tela, estado_insana, aurea, tempo_atual,
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, config_graficos
            )
            aureas_avancadas.desenhar(
                tela, estado_aureas_avancadas, aurea, tempo_atual,
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem,
                inimigos_comum, config_graficos
            )
            multiplayer_coop.desenhar_jogador_remoto(tela, 4, frame_atual, frames_animacao, frames_animacao2)

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
                if tempo_atual < ferida_espinhosa_ate:
                    cura_trembo *= 0.35
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

                            dano_real = max(0, dano_inimigo_perto - Resistencia_petro)
                            vida_petro -= int(dano_real)

                            # Petro causa 1.5% do dano total de Apolo
                            inimigo_mais_proximo["vida"] -= int(dano_person_hit * 0.015) + dano_petro
                            tempo_anterior_petro = tempo_atual_petro

                            if inimigo_mais_proximo["vida"] <= 0:

                                vida_inimigo_maxima += ganho_vida_inimigo_comum(0.8)
                                Resistencia_petro += 0.05  # Aumento robusto, mas não invulnerável
                                vida_maxima_petro += 1.8
                                dano_person_hit += 0.12
                                dano_petro += 0.015
                                dano_inimigo_longe += 0.03
                                inimigos_eliminados += 1

                                pontos_p = int(150 * (1 + math.log10(inimigos_eliminados + 1)))
                                pontuacao += pontos_p
                                pontuacao_exib += pontos_p

                                if inimigo_mais_proximo in inimigos_comum:
                                    gerar_fragmentos_morte(inimigo_mais_proximo, 4)
                                    inimigos_comum.remove(inimigo_mais_proximo)
                                    Variaveis.tentar_soltar_carta(inimigo_mais_proximo["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)


                                if not boss_vivo4:
                                    vida_boss4 += ganho_progressao_boss(8 * mult)
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



                if boss_vivo4:
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
                            vida_boss4-= dano_boss_mitigado(int(dano_person_hit*0.25)+300, 4, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
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

            boss_rect_voraz = pygame.Rect(pos_x_boss4, pos_y_boss4, chefe_largura4, chefe_altura4) if boss_vivo4 else None
            aureas_avancadas.atualizar(
                estado_aureas_avancadas, aurea, tempo_atual,
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem,
                inimigos_comum, efeitos_texto, boss_vivo4
            )
            dano_base_voraz = dano_person_hit * fator_dano_aureas(tempo_atual)
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
                inimigos_comum, efeitos_texto, dano_base_voraz,
                fator_tempo=dt, vida=vida, vida_maxima=vida_maxima
            )
            for morto_voraz in mortos_voraz:
                if morto_voraz in inimigos_comum:
                    gerar_fragmentos_morte(morto_voraz, 4)
                    Variaveis.tentar_soltar_carta(morto_voraz["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                    inimigos_comum.remove(morto_voraz)
                    inimigos_eliminados += 1
            if boss_rect_voraz is not None:
                vida_boss4, vida, _ = voraz_aurea.aplicar_mordida_boss(
                    estado_voraz, aurea, tempo_atual,
                    pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem,
                    boss_rect_voraz, vida_boss4, vida, vida_maxima, dano_base_voraz, efeitos_texto
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
                vfx_disparo_player.desenhar_disparo(tela, disparo, tempo_atual, config_graficos)
            vfx_disparo_player.atualizar_e_desenhar_particulas(tela, dt, config_graficos)

            boss_info = {
                "vivo": boss_vivo4,
                "rect": pygame.Rect(pos_x_boss4, pos_y_boss4, chefe_largura4, chefe_altura4) if boss_vivo4 else None,
                "atingido_por_onda": globals().get("boss_atingido_por_onda", {}).get("boss", 0),
                "hit_flag": False
            }
            inimigos_mortos_neste_frame = processar_habilidade_onda(
                ondas, correntes_eletricas, inimigos_comum, boss_info, tela, dt, tempo_atual, largura_mapa, altura_mapa, velocidade_onda, disparos, config_graficos
            )
            if boss_info.get("hit_flag"):
                dano_onda_boss = boss_info.get("dano_manifestacao", dano_person_hit * fator_dano_aureas(tempo_atual) * 3)
                dano_onda_real = dano_boss_mitigado(dano_onda_boss, 4, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                vida_boss4 -= dano_onda_real
                registrar_dano_boss(efeitos_texto, dano_onda_real, pos_x_boss4 + chefe_largura4 // 2, pos_y_boss4 - 22, tempo_atual, (180, 255, 255))
                if "boss_atingido_por_onda" not in globals():
                    globals()["boss_atingido_por_onda"] = {}
                globals()["boss_atingido_por_onda"]["boss"] = boss_info["atingido_por_onda"]
                
                if vida_boss4 <= 0:
                    boss_vivo4 = False
                    try:
                        Musica_tema_fases.stop()
                        Som_tema_fases.stop()
                    except:
                        pass
                    registrar_conclusao_fase(6)
                    limpar_salvamento()
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.GAME_OVER, dados={'vitoria': True, 'pontuacao': pontuacao})
                        raise CleanExit()
                    else:
                        pygame.quit()
                        sys.exit()

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
                    gerar_fragmentos_morte(morto, 4)
                    inimigos_comum.remove(morto)
                    Variaveis.tentar_soltar_carta(morto["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)

                    vida_inimigo_maxima += ganho_vida_inimigo_comum(23)
                    Resistencia_petro += 24.5
                    dano_inimigo_perto += 0.35
                    dano_person_hit += 8
                    vida_maxima_petro += 35
                    dano_petro += 0.005
                    dano_inimigo_longe += 2
                    inimigos_eliminados += 1

                    ganho = int(75 + inimigos_eliminados * 0.5)
                    pontuacao += ganho
                    pontuacao_exib += ganho

                    if not boss_vivo4:
                        vida_boss4 += ganho_progressao_boss(82)
                        vida_maxima_boss4 = vida_boss4

            areas_sarcas[:] = [area for area in areas_sarcas if tempo_atual < area["fim"]]
            globals()["fator_sarcas_movimento"] = 1.0
            centro_player_x = pos_x_personagem + largura_personagem // 2
            centro_player_y = pos_y_personagem + altura_personagem // 2
            em_sarcas = False
            for area in areas_sarcas:
                desenhar_area_sarcas(tela, area, tempo_atual)
                dist_area = math.hypot(centro_player_x - area["x"], centro_player_y - area["y"])
                if dist_area <= area["raio"]:
                    em_sarcas = True
                    if tempo_atual - area.get("ultimo_tick", 0) >= 850:
                        area["ultimo_tick"] = tempo_atual
                        dano_sarcas = max(1, int(vida_maxima * 0.025))
                        aplicar_hit_jogador(dano_sarcas, respeitar_resistencia=True, ativar_vanguarda=False)
                    if tempo_atual < ferida_espinhosa_ate:
                        preso_em_sarcas_ate = max(preso_em_sarcas_ate, tempo_atual + 420)
            if em_sarcas:
                globals()["fator_sarcas_movimento"] = 0.42 if tempo_atual >= preso_em_sarcas_ate else 0.12
                if tempo_atual < preso_em_sarcas_ate and tempo_atual % 500 < 35:
                    efeitos_texto.append({
                        "texto": "PRESO NAS SARCAS",
                        "x": pos_x_personagem - 18,
                        "y": pos_y_personagem - 36,
                        "tempo_inicio": tempo_atual,
                        "cor": (116, 255, 130)
                    })
            # loop principal, onde o inimigo é desenhado:
            for inimigo in inimigos_comum:
                if multiplayer_coop.eh_cliente():
                    continue
                
                # Se ainda está no processo de spawn, atualiza o progresso
                if not inimigo.get("spawn_complete", False):
                    inimigo["spawn_progress"] += 0.025 # Dura 40 frames (~0.6 segundos)
                    if inimigo["spawn_progress"] >= 1.0:
                        inimigo["spawn_progress"] = 1.0
                        inimigo["spawn_complete"] = True
                        
                        qualidade = config_graficos.get("qualidade_grafica", "alta")
                        if qualidade == "alta":
                            for _ in range(random.randint(6, 12)):
                                px = inimigo["rect"].centerx + random.uniform(-10, 10)
                                py = inimigo["rect"].bottom + random.uniform(-5, 5)
                                spawn_enemy_particle("dust", px, py, cor=(90, 120, 90), tamanho=4, tamanho_max=16, vx=random.uniform(-1, 1), vy=random.uniform(-0.8, -0.2), vida=random.randint(400, 800))
                    continue # Não move enquanto spawna

                centro_x_anterior = inimigo["rect"].centerx
                dx = pos_x_personagem - inimigo["rect"].centerx
                dy = pos_y_personagem - inimigo["rect"].centery
                dist = max(1.0, math.hypot(dx, dy))
                
                if "pos_x" not in inimigo:
                    inimigo["pos_x"] = float(inimigo["rect"].x)
                if "pos_y" not in inimigo:
                    inimigo["pos_y"] = float(inimigo["rect"].y)

                tipo_inimigo = inimigo.get("tipo", "aguilhao")
                em_area_sarcas = any(
                    math.hypot(inimigo["rect"].centerx - area["x"], inimigo["rect"].centery - area["y"]) <= area["raio"]
                    for area in areas_sarcas
                )
                vel_inimigo_frame = velocidade_inimigo2 * fator_mundo_racional(aurea, racional_dilatacao_fim, tempo_atual)
                if em_area_sarcas:
                    vel_inimigo_frame *= 1.18

                if tipo_inimigo == "enredador":
                    if tempo_atual >= inimigo.get("enredador_proxima_troca", 0):
                        if inimigo.get("enredador_estado_mov") == "movendo":
                            inimigo["enredador_estado_mov"] = "parado"
                            inimigo["enredador_proxima_troca"] = tempo_atual + random.randint(15000, 18000)
                        else:
                            inimigo["enredador_estado_mov"] = "movendo"
                            inimigo["enredador_proxima_troca"] = tempo_atual + 5000

                    if inimigo.get("enredador_estado_mov") == "movendo":
                        vel_inimigo_frame *= 0.055
                        if dist < 185:
                            inimigo["pos_x"] -= (dx / dist) * vel_inimigo_frame * 0.35
                            inimigo["pos_y"] -= (dy / dist) * vel_inimigo_frame * 0.35
                        elif dist > 310:
                            inimigo["pos_x"] += (dx / dist) * vel_inimigo_frame * 0.18
                            inimigo["pos_y"] += (dy / dist) * vel_inimigo_frame * 0.18
                else:
                    vel_inimigo_frame *= 1.35
                    if tempo_atual >= inimigo.get("proxima_investida", 0):
                        inimigo["investida_ate"] = tempo_atual + 260
                        inimigo["proxima_investida"] = tempo_atual + random.randint(1350, 2300)
                    if tempo_atual < inimigo.get("investida_ate", 0):
                        vel_inimigo_frame *= 2.65
                    inimigo["pos_x"] += (dx / dist) * vel_inimigo_frame
                    inimigo["pos_y"] += (dy / dist) * vel_inimigo_frame
                inimigo["rect"].x = int(inimigo["pos_x"])
                inimigo["rect"].y = int(inimigo["pos_y"])
                if inimigo["rect"].centerx < centro_x_anterior - 0.5:
                    inimigo["direcao_sprite"] = "left"
                elif inimigo["rect"].centerx > centro_x_anterior + 0.5:
                    inimigo["direcao_sprite"] = "right"

            # Resolve colisões e separações entre inimigos e jogador
            if not multiplayer_coop.eh_cliente():
                inimigos_ativos = [inimigo for inimigo in inimigos_comum if inimigo.get("spawn_complete", False)]
                pos_x_personagem, pos_y_personagem = Variaveis.resolver_colisao_player_com_inimigos(
                    pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, inimigos_ativos
                )
                pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem))
                pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem))
            if not multiplayer_coop.eh_cliente():
                inimigos_ativos = [inimigo for inimigo in inimigos_comum if inimigo.get("spawn_complete", False)]
                Variaveis.resolver_colisoes_e_separacao(inimigos_ativos, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)

            lacerante_manifestacao.atualizar_e_desenhar_sangue_lacerante(tela, inimigos_comum, config_graficos)

            for inimigo in inimigos_comum:
                dx = pos_x_personagem - inimigo["rect"].x
                dy = pos_y_personagem - inimigo["rect"].y

                # Atualize os frames do inimigo com base na direção
                direcao_sprite = inimigo.get("direcao_sprite", "right")
                if inimigo.get("tipo", "aguilhao") == "enredador":
                    frames_tipo = frames_enredador_esquerda if direcao_sprite == "left" else frames_enredador_direita
                    if tempo_atual < inimigo.get("atacando_ate", 0):
                        inimigo["image"] = frames_tipo[1]
                    else:
                        fase_pulso = (math.sin((tempo_atual + inimigo.get("pulso_offset", 0)) * math.tau / 1500.0) + 1.0) * 0.5
                        fator_pulso = 1.0 + (0.05 * fase_pulso)
                        inimigo["image"] = escalar_surface(frames_tipo[0], fator_pulso)
                else:
                    frames_tipo = frames_aguilhao_esquerda if direcao_sprite == "left" else frames_aguilhao_direita
                    frame_idx = 1 if tempo_atual < inimigo.get("investida_ate", 0) else frame_atual % len(frames_tipo)
                    inimigo["image"] = frames_tipo[frame_idx]
                centro_sprite = inimigo["rect"].center
                inimigo["rect"] = inimigo["image"].get_rect(center=centro_sprite)
                inimigo["pos_x"] = float(inimigo["rect"].x)
                inimigo["pos_y"] = float(inimigo["rect"].y)

                # Se ainda não terminou o spawn, desenha o portal e o inimigo crescendo
                if not inimigo.get("spawn_complete", False):
                    progress = inimigo.get("spawn_progress", 0.0)
                    portal_largura = int(inimigo["rect"].width * 1.3)
                    portal_altura = 12
                    portal_surf = pygame.Surface((portal_largura, portal_altura * 2), pygame.SRCALPHA)
                    cor_portal = (34, 180, 50, int(200 * progress))
                    pygame.draw.ellipse(portal_surf, cor_portal, (0, 0, portal_largura, portal_altura))
                    pygame.draw.ellipse(portal_surf, (120, 255, 100, int(255 * progress)), (0, 0, portal_largura, portal_altura), 2)
                    tela.blit(portal_surf, (inimigo["rect"].centerx - portal_largura // 2, inimigo["rect"].bottom - portal_altura))
                    
                    try:
                        sprite_temp = inimigo["image"].copy()
                        escala_w = max(1, int(inimigo["rect"].width * progress))
                        escala_h = max(1, int(inimigo["rect"].height * progress))
                        sprite_temp = pygame.transform.scale(sprite_temp, (escala_w, escala_h))
                        
                        temp_surf = pygame.Surface(sprite_temp.get_size(), pygame.SRCALPHA)
                        temp_surf.blit(sprite_temp, (0, 0))
                        temp_surf.fill((255, 255, 255, int(255 * progress)), special_flags=pygame.BLEND_RGBA_MULT)
                        
                        pos_draw = temp_surf.get_rect(midbottom=(inimigo["rect"].centerx, inimigo["rect"].bottom))
                        tela.blit(temp_surf, pos_draw)
                    except Exception:
                        pass
                    continue

                # Efeito de hit/flash e faíscas
                if "vida_anterior" not in inimigo:
                    inimigo["vida_anterior"] = inimigo["vida"]
                if inimigo["vida"] < inimigo["vida_anterior"]:
                    inimigo["hit_flash_timer"] = tempo_atual + 120
                    inimigo["vida_anterior"] = inimigo["vida"]
                    
                    qualidade = config_graficos.get("qualidade_grafica", "alta")
                    num_sparks = 8 if qualidade == "alta" else (4 if qualidade == "media" else 0)
                    for _ in range(num_sparks):
                        vx = random.uniform(-3, 3)
                        vy = random.uniform(-3, 3)
                        cor_spark = random.choice([(127, 255, 0), (255, 215, 0), (255, 255, 255)])
                        spawn_enemy_particle(
                            "spark",
                            inimigo["rect"].centerx,
                            inimigo["rect"].centery,
                            cor=cor_spark,
                            tamanho=random.randint(2, 4),
                            vx=vx,
                            vy=vy,
                            vida=random.randint(200, 450)
                        )
                elif inimigo["vida"] > inimigo["vida_anterior"]:
                    inimigo["vida_anterior"] = inimigo["vida"]

                # Trilha de esporos e afterimages
                qualidade = config_graficos.get("qualidade_grafica", "alta")
                esta_carregando = (inimigo.get("tipo") == "aguilhao" and tempo_atual < inimigo.get("investida_ate", 0))
                freq_trail = 80 if esta_carregando else 250
                if qualidade == "baixa":
                    freq_trail = 999999
                elif qualidade == "media":
                    freq_trail *= 1.5
                    
                if tempo_atual - inimigo.get("ultimo_trail", 0) > freq_trail:
                    inimigo["ultimo_trail"] = tempo_atual
                    cor_trail = (173, 255, 47) if inimigo.get("tipo") == "enredador" else (143, 188, 143)
                    tipo_part = "spore" if random.random() < 0.6 else "dust"
                    spawn_enemy_particle(
                        tipo_part, 
                        inimigo["rect"].centerx + random.uniform(-10, 10), 
                        inimigo["rect"].bottom - 5, 
                        cor=cor_trail, 
                        tamanho=random.randint(3, 6), 
                        vx=random.uniform(-0.5, 0.5), 
                        vy=random.uniform(-0.8, -0.2), 
                        vida=random.randint(600, 1200)
                    )
                    
                    if esta_carregando and qualidade == "alta":
                        spawn_enemy_particle(
                            "afterimage",
                            inimigo["rect"].x,
                            inimigo["rect"].y,
                            image=inimigo["image"],
                            vida=200
                        )

                # Tint para hit flash
                tint_surface = None
                if tempo_atual < inimigo.get("hit_flash_timer", 0):
                    try:
                        mask = pygame.mask.from_surface(inimigo["image"])
                        cor_flash = (255, 250, 240) if qualidade == "alta" else (255, 80, 80)
                        tint_surface = mask.to_surface(setcolor=cor_flash, unsetcolor=(0, 0, 0, 0))
                    except Exception:
                        tint_surface = None

                # Desenhar sombra do inimigo
                desenhar_sombra(tela, inimigo["rect"].x, inimigo["rect"].y, inimigo["rect"].width, inimigo["rect"].height)
                
                if tint_surface:
                    tela.blit(tint_surface, inimigo["rect"])
                else:
                    tela.blit(inimigo["image"], inimigo["rect"])
                    
                desenhar_barra_de_vida(tela, inimigo["rect"].x, inimigo["rect"].y - 10, inimigo["rect"].width, 5, inimigo["vida"], inimigo["vida_maxima"], inimigo.get("eletrocutado", False), Executa_inimigo if Ultimo_Estalo else None)

                tempo_atual = pygame.time.get_ticks()
                if inimigo.get("tipo", "aguilhao") == "enredador" and tempo_atual >= inimigo.get("proximo_disparo", 0):
                    inimigo["atacando_ate"] = tempo_atual + 360
                    disparos_inimigos.append(criar_disparo_inimigo((inimigo["rect"].x, inimigo["rect"].y), (pos_x_personagem, pos_y_personagem)))
                    inimigo["proximo_disparo"] = tempo_atual + random.randint(1850, 3400)


            personagem_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
            inimigos_rects = [inimigo["rect"] for inimigo in inimigos_comum]

            if imune_tempo_restante > 0:
                imune_tempo_restante -= relogio.get_time()  # Reduz o tempo de imunidade com base no tempo de quadro
            else:
                imune_tempo_restante = 0  # Redefine a imunidade


            if verificar_colisao_personagem_inimigo(personagem_rect, inimigos_rects) and imune_tempo_restante <= 0:

                if tempo_atual - tempo_ultimo_hit_inimigo >= intervalo_hit_inimigo:
                    aplicar_hit_jogador((vida_maxima * 0.25) + dano_inimigo_perto)
                    if any(personagem_rect.colliderect(inimigo["rect"]) and inimigo.get("tipo") == "aguilhao" for inimigo in inimigos_comum):
                        ferida_espinhosa_ate = tempo_atual + 5200
                        efeitos_texto.append({
                            "texto": "FERIDA ESPINHOSA",
                            "x": pos_x_personagem - 18,
                            "y": pos_y_personagem - 34,
                            "tempo_inicio": tempo_atual,
                            "cor": (128, 255, 110)
                        })
                    tempo_ultimo_hit_inimigo = tempo_atual

                    piscando_vida = True
            # Regenerar o escudo se estiver inativo e o tempo passou
            if aurea == "Devota" and not escudo_devota_ativo and tempo_atual - tempo_ultimo_escudo >= intervalo_escudo:
                escudo_devota_ativo = True
                restaurar_escudo_devota(estado_devota)
                tempo_ultimo_escudo = tempo_atual


            # Verifica colisão entre disparos dos inimigos e personagem
            novos_disparos_inimigos = []
            for disparo_inimigo in disparos_inimigos:
                pos_x_disparo_inimigo, pos_y_disparo_inimigo = disparo_inimigo["rect"].x, disparo_inimigo["rect"].y
                tela.blit(frames_disparo4[frame_atual_disparo], (pos_x_disparo_inimigo, pos_y_disparo_inimigo))

                # Atualize a posição do disparo do inimigo
                disparo_inimigo["rect"].x += disparo_inimigo["velocidade"][0]
                disparo_inimigo["rect"].y += disparo_inimigo["velocidade"][1]

                if disparo_inimigo.get("tipo") == "semente" and tempo_atual - disparo_inimigo.get("nascimento", tempo_atual) >= 1550:
                    criar_area_sarcas(disparo_inimigo["rect"].centerx, disparo_inimigo["rect"].centery, raio=78, duracao=5400, origem="enredador")
                    continue



                if (
                    pos_x_personagem < pos_x_disparo_inimigo < pos_x_personagem + largura_personagem and
                    pos_y_personagem < pos_y_disparo_inimigo < pos_y_personagem + altura_personagem
                ):
                    # O disparo do inimigo atingiu o personagem
                    if not personagem_imovel:
                        Dano_pos_resistencia_person_longe=int((vida_maxima*0.25+dano_inimigo_longe)-Resistencia)
                        if Dano_pos_resistencia_person_longe < 0:
                            pass
                        else:
                            aplicar_hit_jogador(Dano_pos_resistencia_person_longe, respeitar_resistencia=False)
                        tempo_ultimo_hit_inimigo = tempo_atual  # Atualize o tempo do último hit do inimigo
                        piscando_vida=True
                        ferida_espinhosa_ate = tempo_atual + 5200
                        criar_area_sarcas(pos_x_disparo_inimigo, pos_y_disparo_inimigo, raio=82, duracao=5600, origem="enredador")
                        disparos_inimigos.remove(disparo_inimigo)
                    continue
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
            current_time = pygame.time.get_ticks()

            chamada_boss4_solicitada = keys[pygame.K_r]
            if multiplayer_coop.modo_multiplayer() and not r_press and chamada_boss4_solicitada:
                multiplayer_coop.solicitar_acao("boss4", 4)
            boss4_confirmado = multiplayer_coop.modo_multiplayer() and not r_press and multiplayer_coop.acao_confirmada(
                "boss4", 4, delay_ms=4000, assumir_sim_apos_ms=multiplayer_coop.COOP_SILENCIO_CONFIRMA_MS
            )
            if boss4_confirmado or (not multiplayer_coop.modo_multiplayer() and chamada_boss4_solicitada):
                if not r_press:
                    tempo_boss_entrada_fim = tempo_atual + 2500
                r_press = True

            if r_press:

                max_inimigos4=0
                intervalo_disparo_inimigo =3000
                velocidade_inimigo2=1.50
                desenhar_barra_vida_boss(tela, vida_boss4, vida_maxima_boss4, "CORACAO DAS SARCAS", 6, (116, 255, 130))

                # Detecção de hit no Boss 4
                if 'boss_vida_anterior' not in locals() and 'boss_vida_anterior' not in globals():
                    global boss_vida_anterior, boss_hit_flash_timer
                    boss_vida_anterior = vida_boss4
                    boss_hit_flash_timer = 0

                if vida_boss4 < boss_vida_anterior:
                    boss_hit_flash_timer = current_time + 120
                    boss_vida_anterior = vida_boss4
                    qualidade = config_graficos.get("qualidade_grafica", "alta")
                    num_sparks = 16 if qualidade == "alta" else (8 if qualidade == "media" else 0)
                    for _ in range(num_sparks):
                        vx = random.uniform(-4, 4)
                        vy = random.uniform(-4, 4)
                        cor_spark = random.choice([(127, 255, 0), (255, 215, 0), (255, 255, 255)])
                        spawn_enemy_particle(
                            "spark",
                            boss_rect.centerx,
                            boss_rect.centery,
                            cor=cor_spark,
                            tamanho=random.randint(3, 5),
                            vx=vx,
                            vy=vy,
                            vida=random.randint(250, 500)
                        )
                elif vida_boss4 > boss_vida_anterior:
                    boss_vida_anterior = vida_boss4

                # Determinar imagem do boss
                if estado_boss_atacando:
                    boss_image_to_draw = boss4_2_img
                    if current_time - tempo_ataque >= 800:
                        estado_boss_atacando = False
                        last_frame_change = current_time
                else:
                    if current_time - last_frame_change >= frame_interval:
                        current_frame_index = (current_frame_index + 1) % len(frames_chefe4_1)
                        last_frame_change = current_time
                    boss_image_to_draw = frames_chefe4_1[current_frame_index]

                # Tint para hit flash
                tint_surface = None
                if current_time < boss_hit_flash_timer:
                    try:
                        mask = pygame.mask.from_surface(boss_image_to_draw)
                        qualidade = config_graficos.get("qualidade_grafica", "alta")
                        cor_flash = (255, 250, 240) if qualidade == "alta" else (255, 80, 80)
                        tint_surface = mask.to_surface(setcolor=cor_flash, unsetcolor=(0, 0, 0, 0))
                    except Exception:
                        tint_surface = None

                if tint_surface:
                    tela.blit(tint_surface, boss_rect)
                else:
                    tela.blit(boss_image_to_draw, boss_rect)

                    # Verificar se já passou o tempo de disparo
                    if current_time - ultimo_disparo >= intervalo_disparo_Boss_4:
                        # Mudar o estado para indicar que o Boss está atacando
                        estado_boss_atacando = True
                        tempo_ataque = current_time  # Registrar o tempo de início do ataque

                        # Definir a posição inicial do projétil (a partir do Boss)
                        projetil_x_inicial = boss_rect.centerx
                        projetil_y_inicial = boss_rect.centery

                        # Criar o projétil com direção inicial e tempo de vida de 2 segundos
                        projetil = {
                            "x": projetil_x_inicial,
                            "y": projetil_y_inicial,
                            "dx": 0,  # Direção x será atualizada continuamente
                            "dy": 0,  # Direção y será atualizada continuamente
                            "nascimento": current_time  # Momento em que o projétil foi criado
                        }

                        # Adicionar o projétil à lista de projéteis
                        projetil_lista.append(projetil)

                        # Atualizar o tempo do último disparo
                        ultimo_disparo = current_time

                if current_time - tempo_frame_disparo_boss >= intervalo_frame_disparo_boss:
                # Alternar entre os frames
                    current_frame_disparo_boss = (current_frame_disparo_boss + 1) % len(sprite_disparo_boss)
                    tempo_frame_disparo_boss = current_time

                # Atualizar e desenhar os projéteis
                for projetil in projetil_lista[:]:
                    # Recalcular a direção para seguir o personagem
                    calcular_direcao_projeteis(projetil, pos_x_personagem, pos_y_personagem)

                    # Atualizar a posição do projétil
                    projetil["x"] += projetil["dx"]
                    projetil["y"] += projetil["dy"]

                    # Verificar se o projétil já passou dos 7 segundos
                    if current_time - projetil["nascimento"] >= 7000:
                        criar_zona_nula(projetil["x"], projetil["y"], current_time)
                        projetil_lista.remove(projetil)
                    else:
                        # Verificar colisão com a hitbox do personagem
                        if (projetil["x"] >= pos_x_personagem and
                        projetil["x"] <= pos_x_personagem + largura_personagem and
                        projetil["y"] >= pos_y_personagem and
                        projetil["y"] <= pos_y_personagem + altura_personagem):

                            # Calcular o dano
                            Dano_pos_resistencia_person_longe = int((vida_maxima * 0.25 + dano_inimigo_longe) - Resistencia)
                            if escudo_devota_ativo:
                                aplicar_hit_jogador(int((10 * vida / 100) + max(0, Dano_pos_resistencia_person_longe)), respeitar_resistencia=False)
                                projetil_lista.remove(projetil)
                                continue
                            elif Dano_pos_resistencia_person_longe > 0:
                                aplicar_hit_jogador(int((10 * vida / 100) + Dano_pos_resistencia_person_longe), respeitar_resistencia=False)
                                projetil_lista.remove(projetil)
                                continue

                            # Remover o projétil da lista ao causar dano
                            projetil_lista.remove(projetil)
                        else:
                            # Desenhar o projétil na tela
                            tela.blit(sprite_disparo_boss[current_frame_disparo_boss], (projetil["x"], projetil["y"]))
                            
                            qualidade = config_graficos.get("qualidade_grafica", "alta")
                            if qualidade != "baixa":
                                spawn_enemy_particle(
                                    "dust",
                                    projetil["x"] + 10,
                                    projetil["y"] + 50,
                                    cor=(128, 0, 128),
                                    tamanho=random.randint(4, 7),
                                    vx=random.uniform(-0.5, 0.5),
                                    vy=random.uniform(-0.5, 0.5),
                                    vida=random.randint(400, 800)
                                )


                largura_hitbox_vortex = frames_vortex[indice_frame_vortex].get_width() * 0.5  # 50% da largura original
                altura_hitbox_vortex = frames_vortex[indice_frame_vortex].get_height() * 0.5  # 50% da altura original

                # Loop principal do jogo
                for zona_nula in zonas_nulas[:]:
                    current_time = pygame.time.get_ticks()  # Obtém o tempo atual

                    # Verificar se já passaram 4 segundos
                    if current_time - zona_nula["nascimento"] >= 4000:
                        zonas_nulas.remove(zona_nula)
                    else:
                        # Verificar se já é hora de trocar o frame da galáxia
                        if current_time - current_time_vortex >= intervalo_frame_vortex:
                            # Alternar o frame da galáxia
                            indice_frame_vortex = (indice_frame_vortex + 1) % len(frames_vortex)
                            ultimo_frame_vortex = current_time  # Atualizar o tempo da última troca

                    # Desenhar o frame atual da galáxia na posição da zona nula
                    tela.blit(frames_vortex[indice_frame_vortex], (zona_nula["x"], zona_nula["y"]))

                    # Cria um retângulo para a zona nula com a hitbox menor
                    x_hitbox = zona_nula["x"] + (frames_vortex[indice_frame_vortex].get_width() - largura_hitbox_vortex) / 2
                    y_hitbox = zona_nula["y"] + (frames_vortex[indice_frame_vortex].get_height() - altura_hitbox_vortex) / 2
                    rect_zona_nula = pygame.Rect(x_hitbox, y_hitbox, largura_hitbox_vortex, altura_hitbox_vortex)

                    # Criação do retângulo do jogador
                    jogador_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)

                    # Verifica se o jogador está na zona nula
                    if jogador_rect.colliderect(rect_zona_nula):
                        # O jogador está dentro da zona nula
                        dentro_da_zona_nula = True
                    else:
                         dentro_da_zona_nula = False

                    # Aplica dano ao jogador se ele estiver dentro da zona nula
                    if dentro_da_zona_nula:
                    # Aplica dano ao jogador a cada 5 milesgundos
                        if current_time - tempo_ultimo_dano_vortex > 500:
                            aplicar_hit_jogador(int((10 * vida_maxima) / 100), respeitar_resistencia=False)
                            tempo_ultimo_dano_vortex = current_time
                        elif False:
                            pass

                        # Limite de vida do jogador
                            if vida < 0:
                                vida = 0  # Evita que a vida fique negativa



                for projetil in projetil_lista[:]:
                    for disparo in disparos[:]:
                        # Posição do projétil do inimigo
                        pos_x_proj, pos_y_proj = projetil["x"], projetil["y"]
                        # Posição do disparo do personagem
                        pos_x_disparo = disparo["rect"].x
                        pos_y_disparo = disparo["rect"].y

                        # Verificar colisão (usando uma condição simples de proximidade)
                        if (pos_x_proj < pos_x_disparo + largura_disparo and
                        pos_x_proj + 20 > pos_x_disparo and
                        pos_y_proj < pos_y_disparo + altura_disparo and
                        pos_y_proj + 100 > pos_y_disparo):

                            vida_planeta-=50

                            if vida_planeta<= 0:
                            # Deletar o projétil do inimigo
                                projetil_lista.remove(projetil)
                                vida_planeta= 150
                        # Deletar o disparo do personagem
                            estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)
                            break  # Sair do loop após uma colisão  

                for disparo in disparos:
                    pos_x_disparo=disparo["rect"].x 
                    pos_y_disparo=disparo["rect"].y 
                    rect_disparo = pygame.Rect(pos_x_disparo, pos_y_disparo, largura_disparo, altura_disparo)
                    rect_boss = pygame.Rect(pos_x_boss4, pos_y_boss4, chefe_largura4, chefe_altura4)



                    acertou_boss_disparo = (
                        lacerante_manifestacao.colisao_corte(disparo, rect_boss, tempo_atual)
                        if disparo.get("tipo_manifestacao") == "lacerante_corte"
                        else (
                            prismatica_manifestacao.colisao_feixe(disparo, rect_boss, tempo_atual)
                            if disparo.get("tipo_manifestacao") == "prismatica_feixe"
                            else (
                                retornante_manifestacao.colisao_alvo(disparo, {"rect": rect_boss, "retornante_id": "boss4"})
                                if disparo.get("tipo_manifestacao") == "retornante_pulso"
                                else rect_disparo.colliderect(rect_boss)
                            )
                        )
                    )
                    if acertou_boss_disparo:
                        acerto_prismatico = prismatica_manifestacao.registrar_acerto(
                            disparo, {"rect": rect_boss, "prismatica_id": "boss4"}, tempo_atual
                        )
                        acerto_retornante = retornante_manifestacao.registrar_acerto(
                            disparo,
                            {"rect": rect_boss, "retornante_id": "boss4"},
                            tempo_atual,
                            (pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2),
                        )
                        if vida_boss4 > 0:  # Verifica se o chefe está vivo antes de aplicar dano
                            if random.random() <= chance_critico:  # 10% de chance de dano crítico
                                dano = dano_person_hit * fator_dano_aureas(tempo_atual) * 3  # Valor do dano crítico é 3 vezes o dano normal
                                cor = (255, 255, 0)  # Amarelo (RGB)
                                fonte_dano = fonte_dano_critico
                            else:
                                dano = dano_person_hit * fator_dano_aureas(tempo_atual)
                                cor = (255, 0, 0)  # Vermelho (RGB)
                                fonte_dano = fonte_dano_normal

                        # Ativar veneno no Boss com 50% de chance, se ainda não estiver envenenado
                        if random.random() < 0.5 and not boss_envenenado and Poison_Active:
                            boss_envenenado = True
                            global duracao_veneno_boss
                            dano_por_tick_veneno_boss = vida_maxima_boss4 * Dano_Veneno_Acumulado
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
                        dano = boss_manifestacao_effects.aplicar_efeito_boss(disparo, dano, tempo_atual, efeitos_texto, rect_boss, "boss4")

                        # Renderizar texto do dano
                        tempo_texto_dano = pygame.time.get_ticks()
                        dano = dano_boss_mitigado(dano, 4, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                        registrar_dano_boss(efeitos_texto, dano, pos_x_boss4 + chefe_largura4 // 2, pos_y_boss4 - 24, tempo_atual, cor)
                        vida_boss4 -= dano
                        if vida_boss4 <= 0:
                            boss_vivo4 = False
                            try:
                                Musica_tema_fases.stop()
                                Som_tema_fases.stop()
                            except:
                                pass
                            registrar_conclusao_fase(6)
                            limpar_salvamento()
                            if game_manager:
                                from game_manager import EstadoJogo
                                game_manager.mudar_estado(EstadoJogo.GAME_OVER, dados={'vitoria': True, 'pontuacao': pontuacao})
                                raise CleanExit()
                            else:
                                pygame.quit()
                                sys.exit()
                        if (vida_boss4 <= 0 or (Ultimo_Estalo and vida_boss4 <= limiar_execucao_boss(Executa_inimigo) * vida_maxima_boss4)):
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
                        vida_boss4 -= dano_boss_mitigado(dano_por_tick_veneno_boss, 4, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0), tipo_dano="veneno")
                        ultimo_tick_veneno_boss = tempo_atual

                    # Exibir texto do dano de veneno (1.5 segundos)
                    if tempo_atual - ultimo_tick_veneno_boss <= 1500:
                        dano_veneno_texto = "-" + str(int(dano_por_tick_veneno_boss))
                        texto_dano_veneno = fonte_veneno.render(dano_veneno_texto, True, (0, 255, 0))
                        texto_dano_veneno_borda = fonte_veneno.render(dano_veneno_texto, True, (0, 0, 0))
                        pos_texto = (pos_x_boss4 + chefe_largura4 // 2 - texto_dano_veneno.get_width() // 2, pos_y_boss4 - 30)
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
                    multiplayer_coop.solicitar_acao("loja", 4)
                abrir_loja_manual = False
            if multiplayer_coop.acao_confirmada("loja", 4):
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
                "teleporte": max(0.0, (cooldown_teleporte_vanguarda(tempo_cooldown_dash, aurea, inimigos_comum, inimigos_em_chamas, duracao_incendio_vanguarda, tempo_atual) - (pygame.time.get_ticks() - tempo_ultimo_dash)) / 1000.0),
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

                if hub_vertical_inferior_ativo((pos_x_personagem, pos_y_personagem)) or not area_icones.colliderect(
                (pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
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
                    posicao_combo_y = 90  # Just standard
                    desenhar_texto_com_contorno(tela, texto_bonus, fonte_bonus, (255, 245, 190), (0, 0, 0), (largura_mapa - 330, posicao_combo_y))
            if aurea == "Vanguarda" and tempo_atual < vanguarda_fogo_fim:
                incendiar_vanguarda_proximos(tempo_atual)
            for inimigo in inimigos_comum:
                i_id = id(inimigo)
                if i_id in inimigos_em_chamas:
                    tempo_inicio = inimigos_em_chamas[i_id]
                    if tempo_atual - tempo_inicio <= duracao_incendio_vanguarda:
                        if tempo_atual - inimigo.get("ultimo_tick_queimando", 0) >= 1000:
                            inimigo["ultimo_tick_queimando"] = tempo_atual
                            # Escalonamento: base 1% a 3% da vida do jogador/inimigo, mais 0.2% base e 0.5% max por nível do upgrade
                            nivel_vanguarda = upgrades.get("Vanguarda", 0)
                            limite_max = 0.03 + (nivel_vanguarda * 0.005)
                            proporcao_base = 0.01 + (nivel_vanguarda * 0.002)
                            proporcao = min(limite_max, proporcao_base + (eliminacoes_consecutivas * 0.0015))
                            dano_fogo = int(vida_maxima * proporcao)

                            inimigo["vida"] -= dano_fogo

                            efeitos_texto.append({
                                "texto": f"-{dano_fogo}",
                                "x": inimigo["rect"].x,
                                "y": inimigo["rect"].y - 20,
                                "tempo_inicio": tempo_atual,
                                "cor": (255, 120, 0)
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
                vanguarda_fogo_fim,
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
            atualizar_e_desenhar_vfx_inimigos(tela, tempo_atual)
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
                # Coleta de cartas no chão
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
                    vida = stats_jogador["vida"]
                    vida_maxima = stats_jogador["vida_maxima"]
                    dano_person_hit = stats_jogador["dano_person_hit"]
                    chance_critico = stats_jogador["chance_critico"]
                    roubo_de_vida = stats_jogador["roubo_de_vida"]
                    quantidade_roubo_vida = stats_jogador["quantidade_roubo_vida"]
                    tempo_cooldown_dash = stats_jogador["tempo_cooldown_dash"]
                    Petro_active = stats_jogador["Petro_active"]
                    Resistencia = stats_jogador["Resistencia"]
                    vida_petro = stats_jogador["vida_petro"]
                    vida_maxima_petro = stats_jogador["vida_maxima_petro"]
                    dano_petro = stats_jogador["dano_petro"]
                    xp_petro = stats_jogador["xp_petro"]
                    petro_evolucao = stats_jogador["petro_evolucao"]
                    Resistencia_petro = stats_jogador["Resistencia_petro"]
                    Chance_Sorte = stats_jogador["Chance_Sorte"]
                    Poison_Active = stats_jogador["Poison_Active"]
                    Dano_Veneno_Acumulado = stats_jogador["Dano_Veneno_Acumulado"]
                    Executa_inimigo = stats_jogador["Executa_inimigo"]
                    Ultimo_Estalo = stats_jogador["Ultimo_Estalo"]
                    Mercenaria_Active = stats_jogador["Mercenaria_Active"]
                    Valor_Bonus = stats_jogador["Valor_Bonus"]
                    Tempo_cura = stats_jogador["Tempo_cura"]
                    porcentagem_cura = stats_jogador["porcentagem_cura"]
                    trembo = stats_jogador["trembo"]
                    cartas_compradas = stats_jogador["cartas_compradas"]



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

            multiplayer_coop.desenhar_status_acao(tela, fonte, "loja", 4)
            multiplayer_coop.desenhar_status_acao(tela, fonte, "pause", 4)
            multiplayer_coop.desenhar_status_acao(
                tela,
                fonte,
                "boss4",
                4,
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
