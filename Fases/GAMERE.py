import Caminhos
import pygame
import subprocess
import sys
import random
import math
import time
import os
import sys
import json
import lacerante_manifestacao
import threading
import queue
from qa_logger import instalar_captura_global, instalar_filtro_prints, registrar_erro
from Tela_Cartas_Coop import tela_de_pausa
from rede import iniciar_host, conectar_ao_host,fila_envio,fila_recebimento,thread_envio,thread_recebimento, anunciar_host_udp, descobrir_host_udp
from Variaveis import *
import Variaveis
from utils import *
from habilidades_personagem import (
    processar_habilidade_onda,
    atualizar_e_desenhar_correntes,
    calcular_corrente_eletrica_grafo as calcular_corrente_eletrica,
    criar_particulas_explosao_onda as criar_particulas_explosao,
    desenhar_onda
)
from ui_helpers import desenhar_efeitos_vanguarda, desenhar_efeito_racional_dilatacao, fator_movimento_racional, intervalo_disparo_racional, tentar_ativar_dilatacao_racional
from post_boss_pressure import criar_estado_pressao_pos_boss, calcular_pressao_spawn_pos_boss
from player_projectile import PlayerProjectileVFX, estourar_disparo_eletrico
lock_inimigos = threading.Lock()
from Tela_Upgrade_Aureas import tela_upgrade_aureas
from audio_manager import carregar_config_audio, aplicar_volume_som
joystick = None

instalar_captura_global()
instalar_filtro_prints()

try:
    with open("saves/config_graficos.json", "r") as f:
        config_graficos = json.load(f)
except Exception:
    config_graficos = {
        "sombras_ativas": "dinamicas",
        "qualidade_grafica": "alta",
        "nivel_detalhes": "alto",
        "particulas_ativas": True,
        "efeitos_visuais": True,
        "fps_limite": 60,
        "tela_cheia": False,
    }

def checar_colisao_onda(onda, inimigos_comum):
    for inimigo in inimigos_comum:
        if onda["rect"].colliderect(inimigo["rect"]):
            vizinhos, links = calcular_corrente_eletrica(inimigo, inimigos_comum)
            return inimigo, vizinhos, links
    return None, [], []


# Forward declaration (atribuído no loop principal)
botao_mouse = (False, False, False)
escudo_devota_ativo = True
duracao_incendio_vanguarda = 5000
intervalo_escudo = 30000
racional_dilatacao_fim = 0
racional_dilatacao_proximo_uso = 0
pressao_pos_boss_spawn = criar_estado_pressao_pos_boss()

with open("saves/modo_jogo.json", "r") as f:
    dados = json.load(f)
modo = dados["modo"]
ip = dados["ip"]


if modo == "host":
    anunciar_host_udp()  # LAN broadcast
    conn = iniciar_host()

elif modo == "join":
    ip_detectado = ip or descobrir_host_udp()
    if ip_detectado:
        conn = conectar_ao_host(ip_detectado)
    else:
        pygame.quit()
        sys.exit()

# se não conectou, encerra

if conn is None:
    pygame.quit()
    sys.exit()

# inicia as threads de rede
threading.Thread(target=thread_envio, args=(conn,), daemon=True).start()
threading.Thread(target=thread_recebimento, args=(conn,), daemon=True).start()


pygame.init()

dano_inimigo=80
config_audio = carregar_config_audio()

estalos = aplicar_volume_som(pygame.mixer.Sound("Sounds/Estalo.mp3"), config_audio, canal="efeitos", volume_maximo=0.07)

som_ataque_boss = aplicar_volume_som(pygame.mixer.Sound("Sounds/Hit_Boss1.mp3"), config_audio, canal="efeitos", volume_maximo=0.04)

Hit_inimigo1 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Inimigo1_hit.wav"), config_audio, canal="efeitos", volume_maximo=0.04)

Disparo_Geo = aplicar_volume_som(pygame.mixer.Sound("Sounds/Disparo_Geo.wav"), config_audio, canal="efeitos", volume_maximo=0.04)

Musica_tema_Boss1 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase1_Boss.mp3"), config_audio, canal="musica", volume_maximo=0.06)

Musica_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase_boas.mp3"), config_audio, canal="musica", volume_maximo=0.06)

Som_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Praia.wav"), config_audio, canal="musica", volume_maximo=0.10)

Som_portal = aplicar_volume_som(pygame.mixer.Sound("Sounds/Portal.mp3"), config_audio, canal="efeitos", volume_maximo=0.06)

Dano_person = aplicar_volume_som(pygame.mixer.Sound("Sounds/hit_person.mp3"), config_audio, canal="efeitos", volume_maximo=0.1)  

toque=0
comando_direção_petro=True
musica_boss1= 1
tempo_ultimo_ataque = 0 
tempo_boss_entrada_fim = 0
apertou_q=False

# Variáveis para rastrear o texto de dano
texto_dano = None
tempo_texto_dano = 0
centro_x_tela_pequena = largura_mapa // 2
centro_y_tela_pequena = altura_mapa // 2

mensagem_mostrada = True  # Variável para controlar se a mensagem já foi mostrada ou não
tempo_mostrando_mensagem = 0  
mensagem = "Tecla R PARA CHAMAR O REI"
imune_tempo_restante = 0  # Tempo restante de imunidade (em milissegundos)
teleportado = False  # Controle de teleporte

direcao_atual_petro="left_petro"
carregar_atributos_na_fase=True
nivel_ameaca = inimigos_eliminados // 10
fonte_mensagem = pygame.font.Font(None, 48)  # Tamanho da fonte
mensagens_exibidas = set()
mensagem_ativa = None
tempo_fim_mensagem = 0

mensagens_iniciais = [
    (3, "Use W, A, S e D para se mover"),
    (7, "Clique no botão esquerdo do mouse para atacar"),
    (11, "Use SHIFT para dar dash"),
    (15, "Colete recursos para fortalecer sua linha temporal"),
    (19, "Junte pontos e melhore o personagem"),
    (23, "Você está sozinho. Mas está preparado."),
    
]

def thread_atualizar_inimigos():
    global inimigos_comum, alvo_x, alvo_y, direcao_alvo, velocidade_personagem
    global movendo, tempo_anterior, tempo_movimento, tempo_parado
    ultimo_tempo = time.time()
    while True:
        agora = time.time()
        dt = agora - ultimo_tempo
        ultimo_tempo = agora
        if inimigos_comum:
            with lock_inimigos:
                try:
                    if movendo:
                        if tempo_atual - tempo_anterior >= tempo_movimento:
                            tempo_anterior = tempo_atual
                            movendo = False
                            tempo_movimento = random.randint(3000, 7000)
                        tempo_previsao = 5
                        atualizar_movimento_inimigos(
                            inimigos_comum, alvo_x, alvo_y, direcao_alvo, velocidade_personagem, tempo_previsao
                        )
                    else:
                        if tempo_atual - tempo_anterior >= tempo_parado:
                            tempo_anterior = tempo_atual
                            movendo = True
                            tempo_parado = random.randint(10, 3000)
                except Exception as e:
                    registrar_erro("Coop: erro na thread de inimigos", e)
        time.sleep(0.01)

#Com o aumento de inimigos, o client apresentou lentidão já que com o aumento o envio de pacotes com a localização de inimigos aumenta e ficam pesados.
def thread_processar_pacotes():
    global inimigos_comum,frame_porcentagem
    global pos_x_player2, pos_y_player2, direcao_player2
    global jogador_remoto_morto, host_ativo, loja_aberta, esperando_client, boss_vivo1
    global quantidade_cartas, cor_ping, pontuacao_exib, convite_boss_aceitou, convite_boss_ativo, convite_boss_recebido, convite_boss_tempo, iniciar_boss, pos_x_chefe, pos_y_chefe
    while True:
        try:
            dados = fila_recebimento.get()
            if modo == "join" and "host_ready" in dados and dados["host_ready"]:
                esperando_client = False

            if modo == "host"  and "join_ready" in dados and dados["join_ready"]:
                esperando_host = False
            if "abrir_loja" in dados:
                if dados["abrir_loja"] and obter_modo_cartas() != "drops":
                    quantidade_cartas = dados.get("quantidade_cartas", 1)  # Define a quantidade de cartas disponíveis
                    loja_aberta = True  # Define que a loja deve ser aberta no cliente
            if "pong" in dados:
                ping_atual = pygame.time.get_ticks() - dados["pong"]
                # Define a cor conforme o ping
                if ping_atual < 80:
                    cor_ping = (0, 255, 0)
                elif ping_atual < 160:
                    cor_ping = (255, 255, 0)
                else:
                    cor_ping = (255, 0, 0)

            if "pontuacao_atual" in dados:
                pontuacao_exib = dados["pontuacao_atual"]
                
            
            # --- Host convidou o boss ---
            if "convite_boss" in dados and dados["convite_boss"]:
                convite_boss_ativo = True
                convite_boss_recebido = True
                convite_boss_tempo = pygame.time.get_ticks()

            # --- Host mandou iniciar o boss ---
            if "iniciar_boss" in dados and dados["iniciar_boss"]:
                iniciar_boss = True
                convite_boss_ativo = False
            if "boss" in dados:
                boss_data = dados["boss"]
                pos_x_chefe = boss_data["x"]
                pos_y_chefe = boss_data["y"]
                vida_boss = boss_data["vida"]
                vida_maxima_boss1 = boss_data["vida_max"]
                boss_vivo1 = True

                # Define a sprite conforme a fase
                porcentagem_vida_boss = (vida_boss / vida_maxima_boss1) * 100
                if porcentagem_vida_boss >= 90:
                    frame_porcentagem = frames_chefe1_1
                elif 60 <= porcentagem_vida_boss < 90:
                    frame_porcentagem = frames_chefe1_2
                elif 40 <= porcentagem_vida_boss < 60:
                    frame_porcentagem = frames_chefe1_3
                else:
                    frame_porcentagem = frames_chefe1_4
            if "boss_morto" in dados and dados["boss_morto"]:
                boss_vivo1 = False
            if "crescimento_local" in dados:
                aplicar_crescimento_personalizado()
            if "drop_moeda" in dados:
                posicao_inimigo = dados["drop_moeda"]
                soltar_moeda(posicao_inimigo)

            if "p1" in dados:
                pos_x_player2 = dados["p1"]["x"]
                pos_y_player2 = dados["p1"]["y"]
                direcao_player2 = dados["p1"].get("direcao", "down")
                host_ativo = True  # Se o host enviou dados, o host está ativo
                if "morto" in dados["p1"]:
                    jogador_remoto_morto = dados["p1"]["morto"]
            # --- Recebe e sincroniza inimigos ---
            if "inimigos" in dados:
                inimigos_recebidos = dados["inimigos"]

                with lock_inimigos:
                    # Ajusta o tamanho da lista conforme o host
                    if len(inimigos_comum) < len(inimigos_recebidos):
                        # adiciona os que faltam
                        for i in range(len(inimigos_comum), len(inimigos_recebidos)):
                            novo = criar_inimigo(
                                inimigos_recebidos[i]["x"],
                                inimigos_recebidos[i]["y"]
                            )
                            novo["vida"] = inimigos_recebidos[i]["vida"]
                            novo["vida_maxima"] = inimigos_recebidos[i]["vida_max"]
                            inimigos_comum.append(novo)

                    elif len(inimigos_comum) > len(inimigos_recebidos):
                        # remove os que sobraram
                        inimigos_comum = inimigos_comum[:len(inimigos_recebidos)]

                    # Atualiza todos os inimigos existentes
                    for i, info in enumerate(inimigos_recebidos):
                        inimigos_comum[i]["rect"].x = info["x"]
                        inimigos_comum[i]["rect"].y = info["y"]
                        inimigos_comum[i]["vida"] = info["vida"]
                        inimigos_comum[i]["vida_maxima"] = info["vida_max"]



        except queue.Empty:
            continue
        except Exception as e:
            registrar_erro("Coop: erro ao processar pacote", e)

if modo == "join":
    
    threading.Thread(target=thread_processar_pacotes, daemon=True).start()


movimento_pressionado = False
boss = None
dados = None
dano = 0
direcao_x = 0
direcao_y = 0
estado = None
fonte = None
mostrar_tutorial = True
running = True
sprite_moeda = None
tempo_atual = 0
upgrades = {}
inimigos_comum = []
alvo_x = 0
alvo_y = 0
direcao_alvo = (0, 0)
velocidade_personagem = 5
movendo = False
tempo_anterior = 0
tempo_movimento = 0
tempo_parado = 0
direcao_player2 = "down"
pos_x_player2 = 0
pos_y_player2 = 0
jogador_remoto_morto = False
host_ativo = False
loja_aberta = False
esperando_client = True
esperando_host = True
boss_vivo1 = False
quantidade_cartas = 1
cor_ping = (0, 255, 0)
pontuacao_exib = 0
convite_boss_aceitou = None
convite_boss_ativo = False
convite_boss_recebido = False
convite_boss_tempo = 0
iniciar_boss = False
pos_x_chefe = 0
pos_y_chefe = 0
vida_boss = 0
vida_maxima_boss1 = 1000
frame_porcentagem = None
frames_chefe1_1 = []
frames_chefe1_2 = []
frames_chefe1_3 = []
frames_chefe1_4 = []

#inicializa a Threading
if modo == "host" and not Safe :
    tempo_anterior = pygame.time.get_ticks()
    tempo_movimento = random.randint(2000, 7000)
    tempo_parado = random.randint(500, 700) 
    movendo = True 
    threading.Thread(target=thread_atualizar_inimigos, daemon=True).start()


def gerar_posicao_aleatoria(largura_mapa, altura_mapa, largura_personagem, altura_personagem):
    largura_mapa_int, altura_mapa_int, largura_personagem_int, altura_personagem_int=map(int,(largura_mapa, altura_mapa, largura_personagem, altura_personagem))
    x = random.randint(0, largura_mapa_int - largura_personagem_int)
    y = random.randint(0, altura_mapa_int - altura_personagem_int)
    return x, y
    
def solicitar_boss(tela, fila_envio, modo):
    global convite_boss_recebido, convite_boss_ativo, convite_boss_aceitou, convite_boss_tempo
    fonte = pygame.font.Font(None, 36)
    clock = pygame.time.Clock()

    # Se o jogador for host, ele inicia o convite com R
    if modo == "host":
        keys = pygame.key.get_pressed()
        if keys[pygame.K_r]:
            convite_boss_recebido = False
            convite_boss_ativo = True
            convite_boss_tempo = pygame.time.get_ticks()
            fila_envio.put({"convite_boss": True})
            

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if convite_boss_recebido and convite_boss_ativo:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_y:
                        fila_envio.put({"resposta_boss": True})
                        convite_boss_aceitou = True
                        convite_boss_ativo = False
                    elif event.key == pygame.K_n:
                        fila_envio.put({"resposta_boss": False})
                        convite_boss_aceitou = False
                        convite_boss_ativo = False

        tela.fill((0, 0, 0))

        # --- Exibir status ---
        tela_rect = tela.get_rect()
        if convite_boss_ativo and not convite_boss_recebido:
            texto = fonte.render("Convite enviado: aguardando resposta...", True, (255, 255, 0))
            tela.blit(texto, (tela_rect.width - texto.get_width() - 30, 30))

        elif convite_boss_recebido and convite_boss_ativo:
            restante = 5 - int((pygame.time.get_ticks() - convite_boss_tempo) / 1000)
            texto = fonte.render(f"Boss solicitado! Aceitar? (Y/N) {restante}s", True, (255, 255, 255))
            tela.blit(texto, (tela_rect.width - texto.get_width() - 30, 30))
            if restante <= 0:
                fila_envio.put({"resposta_boss": False})
                convite_boss_aceitou = False
                convite_boss_ativo = False

        elif convite_boss_aceitou is True:
            return True
        elif convite_boss_aceitou is False:
            return False

        pygame.display.flip()
        clock.tick(30)


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
        "vida_maxima_personagem":vida_maxima,
        "vida_maxima_petro":vida_maxima_petro,
        "vida_atual_personagem":vida,
        "nivel_Petro":xp_petro,
        "existencia_petro":Petro_active,
        "existencia_trembo":trembo,
        "dano_petro":dano_petro,
        "resistencia_personagem":Resistencia,
        "resistencia_petro":Resistencia_petro,
        "dano_inimigo_longe":dano_inimigo_longe,
        "dano_inimigo_perto":dano_inimigo_perto,
        "Poison_Active":Poison_Active,
        "Ultimo_Estalo":Ultimo_Estalo,
        "Executa_inimigo":Executa_inimigo,
        "Mercenaria_Active": Mercenaria_Active,
        "Valor_Bonus": Valor_Bonus,
        "tempo_cooldown_dash": tempo_cooldown_dash,
        "petro_evolucao":petro_evolucao,
        "Dano_Veneno_Acumulado":Dano_Veneno_Acumulado,
        "Tempo_cura":Tempo_cura,
        "porcentagem_cura":porcentagem_cura,
        "Chance_Sorte": Chance_Sorte,
        "cartas_compradas": cartas_compradas,
        "largura_disparo": largura_disparo,
        "altura_disparo": altura_disparo,
    }
    with open('saves/atributos.json', 'w') as file:
        json.dump(atributos, file)

def carregar_atributos():
    global velocidade_personagem, intervalo_disparo, dano_person_hit, chance_critico, roubo_de_vida, quantidade_roubo_vida,vida_maxima,vida_maxima_petro,vida,xp_petro,Petro_active,trembo,dano_petro,Resistencia,Resistencia_petro,dano_inimigo_longe,dano_inimigo_perto,direcao_atual,Poison_Active,Ultimo_Estalo,Executa_inimigo,Valor_Bonus,Mercenaria_Active,tempo_cooldown_dash,vida_petro,petro_evolucao,Dano_Veneno_Acumulado, Tempo_cura,porcentagem_cura, Chance_Sorte, cartas_compradas, largura_disparo, altura_disparo
    if not os.path.exists('saves/atributos.json'):
        cartas_compradas = normalizar_cartas_compradas(cartas_compradas)
        return
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
        Chance_Sorte = atributos.get("Chance_Sorte", 0.0)
        largura_disparo = atributos.get("largura_disparo", largura_disparo)
        altura_disparo = atributos.get("altura_disparo", altura_disparo)
        if "cartas_compradas" in atributos:
            cartas_compradas.update(atributos["cartas_compradas"])
        cartas_compradas = normalizar_cartas_compradas(cartas_compradas)
        
with open("saves/aurea_selecionada.json", "r") as file:
    aurea = json.load(file)["aurea"]
manifestacao_ativa = Variaveis.obter_manifestacao_ativa()

with open("saves/tutorial_config.json", "r") as f:
    mostrar_tutorial = json.load(f).get("mostrar_tutorial", True)

upgrade_aureas = carregar_upgrade_aureas("saves/aureas_upgrade.json")

        
tempo_inicial = time.time() 



boss_vivo1=False
relogio = pygame.time.Clock()
ultimo_tempo_reducao = time.time()
largura_disparo, altura_disparo = 8, 8
velocidade_disparo = 10
disparos = []

tela = pygame.Surface((largura_mapa, altura_mapa))
pygame.display.set_caption("Renderizando Mapa com Personagem")

pontuacao_inimigos=0
maxima_pontuacao_magia = 750
piscar_magia = False

tempo_ultimo_inimigo_apos_morte = pygame.time.get_ticks()
# Carregar a imagem do mapa
mapa = pygame.image.load(mapa_path1).convert()
mapa = pygame.transform.scale(mapa, (largura_mapa, altura_mapa))
# Carregar as sequências de imagens do personagem

# Configurações do loop principal
relogio = pygame.time.Clock()
tempo_passado = 0
frame_atual = 0
frame_atual_disparo = 0
# Atualizar a última direção da personagem
ultima_tecla_movimento = None
direcao_player2 = None
movimento_pressionado = False
#as seguintes variáveis para controle do tempo de hit do inimigo
tempo_ultimo_hit_inimigo = pygame.time.get_ticks()

piscando_vida = False
vida_inimigo_maxima = vida_inimigo_comum_inicial(30)
vida_inimigo= vida_inimigo_maxima


def tela_de_espera_host(tela, fila_envio, fila_recebimento):
    global esperando_host
    fonte = pygame.font.Font(None, 60)
    clock = pygame.time.Clock()
    esperando_host = True

    while esperando_host:
        tela.fill((15, 15, 15))
        texto = fonte.render("Aguardando o jogador entrar...", True, (255, 255, 255))
        sub = fonte.render("O jogo começará quando o cliente estiver pronto.", True, (180, 180, 180))
        tela.blit(texto, (tela.get_width()//2 - texto.get_width()//2, tela.get_height()//2 - 30))
        tela.blit(sub, (tela.get_width()//2 - sub.get_width()//2, tela.get_height()//2 + 20))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # host envia o próprio estado de pronto
        fila_envio.put({"host_ready": True})

        # verifica se recebeu o join_ready do cliente
        try:
            while not fila_recebimento.empty():
                dados = fila_recebimento.get_nowait()
                if "join_ready" in dados and dados["join_ready"]:
                    
                    esperando_host = False
        except:
            pass

        clock.tick(30)

def tela_de_espera_client(tela, fila_envio, fila_recebimento):
    global esperando_client
    fonte = pygame.font.Font(None, 60)
    clock = pygame.time.Clock()
    esperando_client = True

    # o cliente envia uma única vez que está pronto
    fila_envio.put({"join_ready": True})

    while esperando_client:
        tela.fill((15, 15, 15))
        texto = fonte.render("Esperando o host iniciar...", True, (255, 255, 255))
        sub = fonte.render("O jogo começará em breve.", True, (180, 180, 180))
        tela.blit(texto, (tela.get_width()//2 - texto.get_width()//2, tela.get_height()//2 - 30))
        tela.blit(sub, (tela.get_width()//2 - sub.get_width()//2, tela.get_height()//2 + 20))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # A thread processar_pacotes() vai alterar esperando_client = False
        clock.tick(30)




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
    global racional_dilatacao_fim, racional_dilatacao_proximo_uso

    direcao_atual = 'stop'  # Por padrão, definimos a direção como 'stop'

    velocidade_movimento = velocidade_personagem * fator_movimento_racional(aurea, racional_dilatacao_fim)
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
        dash_joystick = joystick and joystick.get_button(2) if joystick else False

    if (dash_teclado or dash_joystick or executar_teleporte_mouse_flag) and not cooldown_dash:
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

            if pygame.time.get_ticks() - tempo_ultimo_dash >= teleporte_duration // 2:
                tempo_ultimo_dash = pygame.time.get_ticks()

            if ultima_tecla_movimento == 'up':
                pos_y_personagem = max(0, pos_y_personagem - distancia_dash)
            elif ultima_tecla_movimento == 'down':
                pos_y_personagem = min(altura_mapa - altura_personagem, pos_y_personagem + distancia_dash)
            elif ultima_tecla_movimento == 'left':
                pos_x_personagem = max(0, pos_x_personagem - distancia_dash)
            elif ultima_tecla_movimento == 'right':
                pos_x_personagem = min(largura_mapa - largura_personagem, pos_x_personagem + distancia_dash)

        cooldown_dash = True
        tempo_ultimo_dash = pygame.time.get_ticks()
        novo_fim_racional, racional_dilatacao_proximo_uso = tentar_ativar_dilatacao_racional(
            aurea,
            tempo_ultimo_dash,
            racional_dilatacao_proximo_uso,
        )
        if novo_fim_racional is not None:
            racional_dilatacao_fim = novo_fim_racional
        aplicar_shockwave_teleporte()

    elif Variaveis.verificar_input("Mover para direita"):
        pos_x_personagem = min(largura_mapa - largura_personagem, pos_x_personagem + velocidade_movimento)
        direcao_atual = 'right'
        ultima_tecla_movimento = 'right'
        movimento_pressionado = True
    elif Variaveis.verificar_input("Mover para cima"):
        pos_y_personagem = max(0, pos_y_personagem - velocidade_movimento)
        direcao_atual = 'up'
        ultima_tecla_movimento = 'up'
        movimento_pressionado = True
    elif Variaveis.verificar_input("Mover para baixo"):
        pos_y_personagem = min(altura_mapa - altura_personagem, pos_y_personagem + velocidade_movimento)
        direcao_atual = 'down'
        ultima_tecla_movimento = 'down'
        movimento_pressionado = True
    elif Variaveis.verificar_input("Mover para esquerda"):
        pos_x_personagem = max(0, pos_x_personagem - velocidade_movimento)
        direcao_atual = 'left'
        ultima_tecla_movimento = 'left'
        movimento_pressionado = True

    elif botao_mouse[0]:
        
        direcao_atual = 'disp'


    else:
        direcao_atual = 'stop'

    # Atualização do cooldown do dash
    if cooldown_dash and pygame.time.get_ticks() - tempo_ultimo_dash > tempo_cooldown_dash:
        cooldown_dash = False
    

    # Verificar movimento do joystick
    if joystick:
        joystick_x = joystick.get_axis(0)  # Eixo horizontal
        joystick_y = joystick.get_axis(1)  # Eixo vertical

        # Calcular magnitude do analógico
        magnitude = math.sqrt(joystick_x**2 + joystick_y**2)
        if magnitude > 0.2:  # Deadzone para ignorar pequenos desvios
            # Calcular ângulo em graus
            angle = math.degrees(math.atan2(-joystick_y, joystick_x)) % 360

            # Determinar direção baseada no ângulo
            if 45 <= angle < 135:  # Cima
                pos_y_personagem = max(0, pos_y_personagem - velocidade_movimento)
                direcao_atual = 'up'
                ultima_tecla_movimento = 'up'
                movimento_pressionado = True
            elif 135 <= angle < 225:  # Esquerda
                pos_x_personagem = max(0, pos_x_personagem - velocidade_movimento)
                direcao_atual = 'left'
                ultima_tecla_movimento = 'left'
                movimento_pressionado = True
            elif 225 <= angle < 315:  # Baixo
                pos_y_personagem = min(altura_mapa - altura_personagem, pos_y_personagem + velocidade_movimento)
                direcao_atual = 'down'
                ultima_tecla_movimento = 'down'
                movimento_pressionado = True
            else:  # Direita
                pos_x_personagem = min(largura_mapa - largura_personagem, pos_x_personagem + velocidade_movimento)
                direcao_atual = 'right'
                ultima_tecla_movimento = 'right'
                movimento_pressionado = True

    # Verificar botões do joystick para teletransporte (Já tratado no bloco principal acima)
    pass

    # Atualizar o cooldown do dash
    if cooldown_dash and pygame.time.get_ticks() - tempo_ultimo_dash > tempo_cooldown_dash:
        cooldown_dash = False
    
    return direcao_atual





def criar_inimigo(x, y, tipo=1):
    if tipo == 1:
        image = frames_inimigo[0]
    # Ajustar a hitbox para ser menor que a imagem original
    largura_hitbox = int(largura_inimigo * 0.8)  # Reduz a largura da hitbox
    altura_hitbox = int(altura_inimigo * 0.5)    # Reduz a altura da hitbox
    offset_x = (largura_inimigo - largura_hitbox) // 2  # Centraliza a hitbox horizontalmente
    offset_y = (altura_inimigo - altura_hitbox) // 2    # Centraliza a hitbox verticalmente

    rect = pygame.Rect(x + offset_x, y + offset_y, largura_hitbox, altura_hitbox)
    
    return {"rect": rect, "image": image, "tipo": tipo, "vida": vida_inimigo_maxima, "vida_maxima": vida_inimigo_maxima}


def gerar_inimigo(limite_inimigos=None):
    global inimigos_comum
    
    limite_inimigos = max_inimigos if limite_inimigos is None else limite_inimigos
    if len(inimigos_comum) < limite_inimigos:
        # Escolhe aleatoriamente uma borda para gerar o inimigo
        
        borda = random.choice(['esquerda', 'direita', 'superior', 'inferior'])
        if borda == 'esquerda':
            novo_inimigo = criar_inimigo(0, random.randint(0, int(altura_mapa) - int(altura_inimigo)))
        elif borda == 'direita':
            novo_inimigo = criar_inimigo(int(largura_mapa) - int(largura_inimigo), random.randint(0, int(altura_mapa) - int(altura_inimigo)))
        elif borda == 'superior':
            novo_inimigo = criar_inimigo(random.randint(0, int(largura_mapa) - int(largura_inimigo)), 0)
        elif borda == 'inferior':
            novo_inimigo = criar_inimigo(random.randint(0, int(largura_mapa) - int(largura_inimigo)), int(altura_mapa) - int(altura_inimigo))

        # Verifica se o novo inimigo está muito próximo de algum inimigo existente
        distancia_minima_alcancada = any(
            math.sqrt((novo_inimigo["rect"].x - inimigo["rect"].x) ** 2 + (novo_inimigo["rect"].y - inimigo["rect"].y) ** 2) < distancia_minima_inimigos
            for inimigo in inimigos_comum
        )

        # Ajusta a posição do novo inimigo se estiver muito próximo
        while distancia_minima_alcancada:
            borda = random.choice(['esquerda', 'direita', 'superior', 'inferior'])
            if borda == 'esquerda':
                novo_inimigo = criar_inimigo(0, random.randint(0, int(altura_mapa) - int(altura_inimigo)))
            elif borda == 'direita':
                novo_inimigo = criar_inimigo(int(largura_mapa) - int(largura_inimigo), random.randint(0, int(altura_mapa) - int(altura_inimigo)))
            elif borda == 'superior':
                novo_inimigo = criar_inimigo(random.randint(0, int(largura_mapa) - int(largura_inimigo)), 0)
            elif borda == 'inferior':
                novo_inimigo = criar_inimigo(random.randint(0, int(largura_mapa) - int(largura_inimigo)), int(altura_mapa) - int(altura_inimigo))

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

# aplica os escalonamento do jogo ao eliminar os inimigos
def aplicar_crescimento_personalizado():
    global vida_inimigo_maxima, Resistencia_petro, dano_inimigo_perto, dano_person_hit
    global vida_maxima_petro, dano_petro, dano_inimigo_longe, dano_boss
    global Dano_Boss_Habilit, Velocidade_Inimigos_1, inimigos_eliminados
    global max_inimigos, tempo_revive

    # Crescimento dos atributos do inimigo
    vida_inimigo_maxima += ganho_vida_inimigo_comum(1.2 + nivel_ameaca * 0.8)
    Resistencia_petro += 0.2 + nivel_ameaca * 0.1
    dano_inimigo_perto += 0.2 + nivel_ameaca * 0.1
    dano_person_hit += 0.15 + nivel_ameaca * 0.05
    vida_maxima_petro += 0.5 + nivel_ameaca * 0.3
    dano_petro += 0.02 + nivel_ameaca * 0.01
    dano_inimigo_longe += 0.03 + nivel_ameaca * 0.02
    dano_boss += 0.04 + nivel_ameaca * 0.02
    Dano_Boss_Habilit += 0.05 + nivel_ameaca * 0.03
    Velocidade_Inimigos_1 += 0.0015 + nivel_ameaca * 0.0005
    inimigos_eliminados += 1

    # ---- Crescimento balanceado do número máximo de inimigos ----
    # A cada 30 eliminações aumenta o número de inimigos até o limite de 12
    if inimigos_eliminados % 30 == 0 and max_inimigos < 12:
        max_inimigos += 1

    # ---- Incrementa o tempo de reviver baseado em inimigos eliminados ----
    tempo_revive += inimigos_eliminados // 30  # A cada 30 inimigos mortos, aumenta 1 segundo no tempo de reviver


def aplicar_shockwave_teleporte():
    global inimigos_eliminados, pontuacao, eliminacoes_consecutivas_impulsiva, pontuacao_exib, vida_boss, vida_maxima_boss1, vida
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

    # Notificar o outro jogador (se em rede)
    try:
        fila_envio.put({
            "vfx_onda": {
                "cx": cx_t,
                "cy": cy_t,
                "raio_max": raio_choque,
                "cor": (0, 191, 255)
            }
        })
    except:
        pass

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
            try:
                fila_envio.put({"drop_moeda": posicao_inimigo})
            except:
                pass
            if inimigo in inimigos_comum:
                inimigos_comum.remove(inimigo)
            
            aplicar_crescimento_personalizado()

            ganho = int(75 + math.log2(inimigos_eliminados + 1) * 4)
            pontuacao += ganho
            eliminacoes_consecutivas_impulsiva += 1
            pontuacao_exib += ganho

            try:
                fila_envio.put({"pontuacao_atual": pontuacao_exib})
                fila_envio.put({"crescimento_local": True})
            except:
                pass

            if not boss_vivo1:
                if vida_boss > 0:
                    vida_boss += 15 + nivel_ameaca * 10
                    vida_maxima_boss1 = vida_boss

        if quantidade_roubo_vida > 0:
            vida += (vida_maxima - vida) * quantidade_roubo_vida

    # Dano ao Boss
    if boss_vivo1:
        bx = pos_x_chefe + chefe_largura // 2
        by = pos_y_chefe + chefe_altura // 2
        dist_boss = math.hypot(bx - cx_t, by - cy_t)
        if dist_boss <= raio_choque:
            vida_boss -= dano_boss_mitigado(dano_choque, 1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
            efeitos_texto.append({
                "texto": f"-{int(dano_choque)}",
                "x": pos_x_chefe + chefe_largura // 2,
                "y": pos_y_chefe - 20,
                "tempo_inicio": pygame.time.get_ticks(),
                "cor": (0, 191, 255)
            })


def criar_disparo():
        return {"rect": pygame.Rect(pos_x_personagem, pos_y_personagem, largura_disparo, altura_disparo),"direcao": ultima_tecla_movimento }

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
    chance = 0.05 # Chance da moeda dropar 10%
    if random.random() < chance:
        tamanho_moeda = (36, 36)  # Novo tamanho desejado
        sprite_redimensionada = pygame.transform.scale(sprite_moeda, tamanho_moeda)
        rect = sprite_redimensionada.get_rect(center=posicao)
        moedas_soltadas.append({
            "rect": rect,
            "image": sprite_redimensionada
        })
        





def executar_jogo(game_manager=None):
    global joystick, botao_mouse, ondas_choque, carregar_atributos_na_fase, Chance_Sorte, Dano_Veneno_Acumulado, Executa_inimigo, Mercenaria_Active, Musica_tema_Boss1, Musica_tema_fases, Petro_active, Poison_Active, Resistencia, Resistencia_petro, Safe, Som_tema_fases, Tempo_cura, Ultimo_Estalo, Valor_Bonus, altura_disparo, alvo_x, alvo_y, apertou_q, bonus_pontuacao, boss, boss_envenenado, boss_vivo1, cartas_compradas, chance_critico, cliente_ativo, conn, convite_boss_ativo, convite_boss_recebido, convite_boss_tempo, dados, dano, dano_inimigo_longe, dano_inimigo_perto, dano_person_hit, dano_petro, dano_por_tick_veneno_boss, direcao_alvo, direcao_atual, direcao_atual_p2, direcao_atual_petro, direcao_player2, direcao_x, direcao_y, disparos, dispositivo_ativo, efeitos_texto, eliminacoes_consecutivas, eliminacoes_consecutivas_impulsiva, em_ataque_especial, escudo_devota_ativo, estado, estado_jogo, fila_envio, fila_recebimento, fonte, fonte_mensagem, frame_atual, frame_atual_chefe, frame_porcentagem, hitboxes, impulsiva_ativa, imune_tempo_restante, iniciar_boss, inimigos_atingidos_por_onda, inimigos_comum, inimigos_eliminados, inimigos_em_chamas, intervalo_disparo, jogador_morto, jogador_posicoes, jogador_remoto_morto, largura_disparo, loja_aberta, mensagem, mensagem_ativa, mensagem_mostrada, mensagens_exibidas, moedas_coletadas, moedas_soltadas, mostrar_tutorial, movimento_pressionado, ondas, outro_jogador_morto, petro_evolucao, piscando_vida, pontuacao, pontuacao_exib, pontuacao_magia, porcentagem_cura, pos_x_chefe, pos_x_personagem, pos_x_petro, pos_x_player2, pos_y_chefe, pos_y_personagem, pos_y_petro, pos_y_player2, quantidade_roubo_vida, r_press, roubo_de_vida, running, sprite_moeda, tela, teleportado, tempo_anterior_petro, tempo_ataque_especial, tempo_boss_entrada_fim, tempo_atual, tempo_cooldown_dash, tempo_envio_ping, tempo_fim_mensagem, tempo_inicio_buff_impulsiva, tempo_inicio_veneno_boss, tempo_morte, tempo_mostrando_mensagem, tempo_passado, tempo_passado_animacao_chefe, tempo_texto_dano, tempo_ultima_atualizacao_direcao, tempo_ultima_mudanca_direcao_boss, tempo_ultima_regeneracao, tempo_ultima_troca_alvo, tempo_ultimo_ataque, tempo_ultimo_dano_ataque, tempo_ultimo_hit_inimigo, tempo_ultimo_inimigo, tempo_ultimo_uso_habilidade, tipo_buff_impulsiva, trembo, ultima_direcao_boss, ultima_vida_enviada, ultimo_tick_veneno_boss, upgrades, velocidade_personagem, vida, vida_boss, vida_inimigo_maxima, vida_maxima, vida_maxima_boss1, vida_maxima_petro, vida_petro, xp_petro, duracao_incendio_vanguarda, intervalo_escudo, comando_direção_petro
    global alvo_atual, vida_boss2, vida_boss3, vida_boss4
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
        tela = configurar_tela(largura_mapa, altura_mapa)
        manifestacao_ativa = obter_manifestacao_ativa()

        vfx_disparo_player = PlayerProjectileVFX()
        
        tempo_parado_person = pygame.time.get_ticks()  
        boss_atingido_por_onda = pygame.time.get_ticks()
        tempo_ultimo_disparo = pygame.time.get_ticks()
        tempo_ultimo_escudo = pygame.time.get_ticks()

        Som_tema_fases.play(loops=-1)
        Musica_tema_fases.play(loops=-1)

        upgrades = carregar_upgrade_aureas("saves/aureas_upgrade.json")
        ondas_choque = []
        fragmentos_morte = []

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

        FPS=pygame.time.Clock()
        pygame.mouse.set_visible(False)
        cursor_imagem = pygame.image.load("Sprites/Ponteiro.png").convert_alpha()  # Ajuste o caminho
        cursor_tamanho = cursor_imagem.get_size()

        sprite_moeda = pygame.image.load("Sprites/moeda.png").convert_alpha()
        moedas_soltadas = []

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

        if Variaveis.snapshot_para_carregar is None:
            try:
                from utils import animar_spawn_portal
                animar_spawn_portal(
                    tela, mapa, pos_x_personagem, pos_y_personagem,
                    largura_personagem, altura_personagem, 2000,
                    frames_animacao, direcao_atual, Som_portal
                )
            except Exception as e:
                registrar_erro("Erro ao executar animacao de spawn do portal", e)

        running = True
        custo_carta_atual = custo_base_carta + (sum(cartas_compradas.values()) * custo_por_carta)
        while running:
            tempo_atual = pygame.time.get_ticks()
            if modo == "host":
                pressao_spawn = calcular_pressao_spawn_pos_boss(
                    pressao_pos_boss_spawn,
                    tempo_atual,
                    r_press and not boss_vivo1,
                    len(inimigos_comum),
                    inimigos_eliminados,
                    max_inimigos,
                )
                if tempo_atual - tempo_ultimo_inimigo >= pressao_spawn["intervalo_ms"] and pressao_spawn["lote"] > 0 and not boss_vivo1:
                    with lock_inimigos:
                        for _ in range(pressao_spawn["lote"]):
                            gerar_inimigo(pressao_spawn["limite"])
                    tempo_ultimo_inimigo = tempo_atual

            # Registrar snapshot para o sistema de rewind
            if vida > 0 and Variaveis.deve_registrar_snapshot(tempo_atual):
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
                    registrar_erro("Coop: erro ao carregar atributos; usando padrao", e)
                carregar_atributos_na_fase = False

            # --- Tratamento de Eventos e Pumping ---
            for event in pygame.event.get():
                Variaveis.atualizar_estado_mouse(event)
                Variaveis.processar_eventos_teleporte(event, cooldown_dash)
                if event.type == pygame.QUIT:
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.SAIR)
                        raise CleanExit()
                    running = False

            keys = pygame.key.get_pressed()
            pos_mouse = pygame.mouse.get_pos()
            botao_mouse = pygame.mouse.get_pressed()
            mouse_x = max(0, min(pos_mouse[0], largura_mapa - cursor_tamanho[0]))
            mouse_y = max(0, min(pos_mouse[1], altura_mapa - cursor_tamanho[1]))

            # Verificar eventos de joystick de forma dinâmica e eficiente
            joystick_count = pygame.joystick.get_count()
            if joystick_count > 0:
                if joystick is None:
                    joystick = pygame.joystick.Joystick(0)
                    joystick.init()
            else:
                joystick = None

            # Atualizar a posição do personagem
            atualizar_posicao_personagem(keys, joystick)

            #################################### Conexão Host ou cliente
            if modo == "host" :
                # --- Atualiza e envia estado completo para o cliente ---
                estado = {
                    "p1": {
                        "x": pos_x_personagem,
                        "y": pos_y_personagem,
                        "direcao": direcao_atual,
                        "morto": jogador_morto
                    },
                    "inimigos": [
                        {
                            "x": inimigo["rect"].x,
                            "y": inimigo["rect"].y,
                            "vida": inimigo["vida"],
                            "vida_max": inimigo["vida_maxima"]
                        }
                        for inimigo in inimigos_comum
                    ]
                }
                fila_envio.put(estado)
                if boss_vivo1:
                    estado["boss"] = {
                        "x": pos_x_chefe,
                        "y": pos_y_chefe,
                        "vida": vida_boss,
                        "vida_max": vida_maxima_boss1
                    }
                while not fila_recebimento.empty():
                    dados = fila_recebimento.get()
                    if dados:
                        if "game_over" in dados and dados["game_over"]:
                            estado_jogo = "game_over"

                        if "ping" in dados:
                            try:
                                fila_envio.put({"pong": dados["ping"]})  # devolve o mesmo tempo
                            except:
                                pass
                        if "p2" in dados:  # Recebe dados do cliente (jogador 2)
                            pos_x_player2 = dados["p2"]["x"]
                            pos_y_player2 = dados["p2"]["y"]
                            direcao_player2 = dados["p2"].get("direcao", "down")
                            cliente_ativo = True  # O cliente está ativo
                            if "morto" in dados["p2"]:
                                jogador_remoto_morto = dados["p2"]["morto"]


                        # Cliente avisou que acertou um inimigo
                        if "hit" in dados:

                            idx = dados["hit"]
                            if 0 <= idx < len(inimigos_comum):
                                inimigo = inimigos_comum[idx]

                                # aplica o dano
                                inimigo["vida"] -= dano_person_hit

                                # verifica se morreu
                                if inimigo["vida"] <= 0:
                                    # Guarda posição antes de remover
                                    posicao_inimigo = inimigo["rect"].center
                                    inimigos_comum.pop(idx)
                                    ganho = int(75 + math.log2(inimigos_eliminados + 1) * 4)
                                    # soma pontos
                                    pontuacao_exib += ganho  # ou o valor real do inimigo
                                    # envia pontuação atualizada para o cliente

                                    fila_envio.put({"pontuacao_atual": pontuacao_exib})
                                    aplicar_crescimento_personalizado()
                                    fila_envio.put({"crescimento_local": True})

                                    # Host também avisa o client para soltar moeda no local certo
                                    try:
                                        fila_envio.put({"drop_moeda": posicao_inimigo})
                                    except:
                                        pass


                        # Cliente avisou que acertou com ataque especial
                        # HOST
                        if "hit_especial" in dados:
                            rect_onda = pygame.Rect(
                                dados["hit_especial"]["x"],
                                dados["hit_especial"]["y"],
                                dados["hit_especial"]["w"],
                                dados["hit_especial"]["h"]
                            )
                            for inimigo in inimigos_comum[:]:
                                if rect_onda.colliderect(inimigo["rect"]):
                                    inimigo["vida"] -= dano_person_hit * 2
                                    if inimigo["vida"] <= 0:
                                        inimigos_comum.remove(inimigo)
                                        fila_envio.put({"pontuacao_atual": pontuacao_exib})
                                        aplicar_crescimento_personalizado()
                                        fila_envio.put({"crescimento_local": True})

                         # --- Cliente sugeriu o boss ---
                        if "convite_boss" in dados and dados["convite_boss"]:
                            convite_boss_ativo = True
                            convite_boss_recebido = True
                            convite_boss_tempo = pygame.time.get_ticks()

                        # --- Cliente respondeu ---
                        if "resposta_boss" in dados:
                            if dados["resposta_boss"]:
                                iniciar_boss = True
                                fila_envio.put({"iniciar_boss": True})  # avisa cliente
                            else:
                                convite_boss_ativo = False

                        # --- Cliente recebeu confirmação de iniciar ---
                        if "iniciar_boss" in dados and dados["iniciar_boss"]:
                            iniciar_boss = True
                        # --- CLIENTE ACERTOU O BOSS (DANO NORMAL) ---
                        if "hit_boss" in dados:
                            if boss_vivo1 and vida_boss > 0:
                                dano = dano_person_hit
                                if random.random() <= chance_critico:
                                    dano *= 3
                                dano = dano_boss_mitigado(dano, 1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                                vida_boss -= dano
                                if vida_boss <= 0:
                                    boss_vivo1 = False
                                    fila_envio.put({"boss_morto": True})

                        # --- CLIENTE ACERTOU O BOSS (HIT ESPECIAL) ---
                        if "hit_boss_especial" in dados:
                            if boss_vivo1 and vida_boss > 0:
                                dano = dano_person_hit * 2
                                dano = dano_boss_mitigado(dano, 1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                                vida_boss -= dano
                                if vida_boss <= 0:
                                    boss_vivo1 = False
                                    fila_envio.put({"boss_morto": True})
                        if "vida_cliente" in dados:
                            vida_remota = dados["vida_cliente"]


                    # --- Host aperta R para sugerir o boss ---
                if not convite_boss_ativo and not r_press and pygame.key.get_pressed()[pygame.K_r]:
                    convite_boss_ativo = True
                    convite_boss_enviado = True
                    convite_boss_tempo = pygame.time.get_ticks()
                    fila_envio.put({"convite_boss": True})

                # --- Tempo limite do convite ---
                if convite_boss_ativo and pygame.time.get_ticks() - convite_boss_tempo > 5000:  
                    convite_boss_ativo = False
                    convite_boss_enviado = False
                    convite_boss_recebido = False
                outro_jogador_morto = jogador_remoto_morto  # cliente remoto




            if modo == "join":
                novas_ondas = []
                for onda in ondas:
                    if "pos_x" not in onda:
                        onda["pos_x"] = float(onda["rect"].x)
                    if "pos_y" not in onda:
                        onda["pos_y"] = float(onda["rect"].y)
                    onda["pos_x"] += velocidade_onda * math.cos(onda["angulo"]) * dt
                    onda["pos_y"] += velocidade_onda * math.sin(onda["angulo"]) * dt
                    onda["rect"].x = int(onda["pos_x"])
                    onda["rect"].y = int(onda["pos_y"])
                    
                    # Renderizar a onda proceduralmente
                    desenhar_onda(tela, onda)

                    colidiu = False
                    # detecta colisão, só avisa
                    for idx, inimigo in enumerate(inimigos_comum):
                        if onda["rect"].colliderect(inimigo["rect"]):
                            try: 
                                for o in ondas:
                                    fila_envio.put({
                                        "hit_especial": {
                                            "x": o["rect"].x,
                                            "y": o["rect"].y,
                                            "w": o["rect"].w,
                                            "h": o["rect"].h
                                        }
                                    })
                            except:
                                pass
                            
                            criar_particulas_explosao(tela, onda["rect"].centerx, onda["rect"].centery)
                            
                            # Triga corrente elétrica nos inimigos comuns próximos localmente para efeito visual (BFS 250px)
                            cx = onda["rect"].centerx
                            cy = onda["rect"].centery
                            closest_enemy = None
                            min_dist = 250.0
                            for outro in inimigos_comum:
                                dist = math.sqrt((outro["rect"].centerx - cx)**2 + (outro["rect"].centery - cy)**2)
                                if dist < min_dist:
                                    min_dist = dist
                                    closest_enemy = outro

                            if closest_enemy:
                                vizinhos, links = calcular_corrente_eletrica(closest_enemy, inimigos_comum)
                                profundidades = {id(closest_enemy): 0}
                                for u, v, d in links:
                                    profundidades[id(v)] = d
                                correntes_eletricas.append({
                                    "inimigos": vizinhos,
                                    "links": links,
                                    "profundidades": profundidades,
                                    "tempo_inicio": tempo_atual,
                                    "tempo_ultimo_dano": tempo_atual,
                                    "duracao": 5000,
                                    "intervalo_dano": 1000
                                })
                            colidiu = True
                            break

                    if not colidiu:
                        if 0 <= onda["rect"].x < largura_mapa and 0 <= onda["rect"].y < altura_mapa:
                            novas_ondas.append(onda)

                ondas = novas_ondas
                atualizar_e_desenhar_correntes(tela, correntes_eletricas, inimigos_comum, tempo_atual, dano_person_hit)

            if modo == "host" :
                novas_ondas = []
                for onda in ondas:
                    if "pos_x" not in onda:
                        onda["pos_x"] = float(onda["rect"].x)
                    if "pos_y" not in onda:
                        onda["pos_y"] = float(onda["rect"].y)
                    onda["pos_x"] += velocidade_onda * math.cos(onda["angulo"]) * dt
                    onda["pos_y"] += velocidade_onda * math.sin(onda["angulo"]) * dt
                    onda["rect"].x = int(onda["pos_x"])
                    onda["rect"].y = int(onda["pos_y"])

                    # Renderizar a onda proceduralmente
                    desenhar_onda(tela, onda)

                    colidiu = False

                    # A. Colisão com o Boss
                    if boss_vivo1 and onda["rect"].colliderect(pygame.Rect(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura)):
                        if tempo_atual - boss_atingido_por_onda >= 500:
                            vida_boss -= dano_boss_mitigado(dano_person_hit * 5, 1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                            boss_atingido_por_onda = tempo_atual
                            if vida_boss <= 0:
                                boss_vivo1 = False
                                fila_envio.put({"boss_morto": True})
                                vida_maxima_boss1 = 0
                        
                        criar_particulas_explosao(tela, onda["rect"].centerx, onda["rect"].centery)
                        
                        # Triga corrente elétrica nos inimigos comuns próximos do Boss (BFS 250px)
                        cx = onda["rect"].centerx
                        cy = onda["rect"].centery
                        boss_entity = {
                            "rect": pygame.Rect(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura),
                            "is_boss": True
                        }
                        closest_enemy = None
                        min_dist = 250.0
                        for outro in inimigos_comum:
                            dist = math.sqrt((outro["rect"].centerx - cx)**2 + (outro["rect"].centery - cy)**2)
                            if dist < min_dist:
                                min_dist = dist
                                closest_enemy = outro

                        if closest_enemy:
                            vizinhos, links = calcular_corrente_eletrica(closest_enemy, inimigos_comum)
                            adjusted_links = [(boss_entity, closest_enemy, 1)]
                            for u, v, d in links:
                                adjusted_links.append((u, v, d + 1))
                            profundidades = {id(boss_entity): 0, id(closest_enemy): 1}
                            for u, v, d in adjusted_links:
                                profundidades[id(v)] = d
                            correntes_eletricas.append({
                                "inimigos": vizinhos,
                                "links": adjusted_links,
                                "profundidades": profundidades,
                                "tempo_inicio": tempo_atual,
                                "tempo_ultimo_dano": tempo_atual,
                                "duracao": 5000,
                                "intervalo_dano": 1000
                            })
                        colidiu = True

                    # B. Colisão com inimigos comuns
                    if not colidiu:
                        inimigo_atingido, vizinhos, links = checar_colisao_onda(onda, inimigos_comum)
                        if inimigo_atingido:
                            inimigo_atingido["vida"] -= dano_person_hit * 2
                            
                            if vizinhos:
                                profundidades = {id(inimigo_atingido): 0}
                                for u, v, d in links:
                                    profundidades[id(v)] = d
                                correntes_eletricas.append({
                                    "inimigos": vizinhos,
                                    "links": links,
                                    "profundidades": profundidades,
                                    "tempo_inicio": tempo_atual,
                                    "tempo_ultimo_dano": tempo_atual,
                                    "duracao": 5000,
                                    "intervalo_dano": 1000
                                })
                                
                            criar_particulas_explosao(tela, onda["rect"].centerx, onda["rect"].centery)
                            
                            if inimigo_atingido["vida"] <= 0:
                                if inimigo_atingido in inimigos_comum:
                                    inimigos_comum.remove(inimigo_atingido)
                                
                                ganho = int(75 + math.log2(inimigos_eliminados + 1) * 4)
                                pontuacao += ganho
                                pontuacao_exib += ganho
                                aplicar_crescimento_personalizado()
                                fila_envio.put({"pontuacao_atual": pontuacao_exib})
                                fila_envio.put({"crescimento_local": True})

                                # Cura da Petro se estiver muito ferida
                                if vida_petro < (vida_maxima_petro * 0.6):
                                    vida_petro += (vida_maxima_petro * 0.4)
                                    if vida_petro > vida_maxima_petro:
                                        vida_petro = vida_maxima_petro

                                # Boss: progressão escalada
                                if not boss_vivo1:
                                    if vida_boss > 0:
                                        vida_boss += 15 + nivel_ameaca * 10
                                        vida_maxima_boss1 = vida_boss
                            colidiu = True

                    if not colidiu:
                         if 0 <= onda["rect"].x < largura_mapa and 0 <= onda["rect"].y < altura_mapa:
                             novas_ondas.append(onda)

                ondas = novas_ondas

                # Atualizar e desenhar correntes elétricas
                inimigos_mortos = atualizar_e_desenhar_correntes(tela, correntes_eletricas, inimigos_comum, tempo_atual, dano_person_hit)
                inimigos_mortos += lacerante_manifestacao.atualizar_laceracoes(inimigos_comum, tempo_atual, efeitos_texto)
                for morto in inimigos_mortos:
                    if morto in inimigos_comum:
                        inimigos_comum.remove(morto)
                        ganho = int(75 + math.log2(inimigos_eliminados + 1) * 4)
                        pontuacao += ganho
                        pontuacao_exib += ganho
                        aplicar_crescimento_personalizado()
                        fila_envio.put({"pontuacao_atual": pontuacao_exib})
                        fila_envio.put({"crescimento_local": True})

                        # Cura da Petro se estiver muito ferida
                        if vida_petro < (vida_maxima_petro * 0.6):
                            vida_petro += (vida_maxima_petro * 0.4)
                            if vida_petro > vida_maxima_petro:
                                vida_petro = vida_maxima_petro

                        # Boss: progressão escalada
                        if not boss_vivo1:
                            if vida_boss > 0:
                                vida_boss += 15 + nivel_ameaca * 10
                                vida_maxima_boss1 = vida_boss

                # Depois do cálculo, envia sincronização pro cliente
                try:
                    fila_envio.put({"inimigos": [{"x": i["x"], "y": i["y"], "vida": i["vida"], "vida_max": i["vida_maxima"]} for i in inimigos_comum],
                                    "pontuacao_atual": pontuacao_exib})

                except:
                    pass

            if modo == "host" :
                for inimigo in inimigos_comum:
                    # Se o alvo atual morreu, força troca imediata
                    if alvo_atual == "host" and jogador_morto and not jogador_remoto_morto:
                        alvo_atual = "cliente"
                        tempo_ultima_troca_alvo = tempo_atual

                    elif alvo_atual == "cliente" and jogador_remoto_morto and not jogador_morto:
                        alvo_atual = "host"
                        tempo_ultima_troca_alvo = tempo_atual

                    else:
                        # Avalia se está na hora de reconsiderar o alvo
                        if tempo_atual - tempo_ultima_troca_alvo >= intervalo_troca_alvo:

                            # Calcula distância até cada jogador
                            for inimigo in inimigos_comum:  # Aqui a variável inimigo está sendo iterada de uma lista de inimigos
                                dist_host = math.hypot(pos_x_personagem - inimigo["rect"].x, pos_y_personagem - inimigo["rect"].y)
                                dist_cliente = math.hypot(pos_x_player2 - inimigo["rect"].x, pos_y_player2 - inimigo["rect"].y)

                            # Atribui pontuação de prioridade para cada alvo
                            prioridade_host = 0
                            prioridade_cliente = 0

                            if not jogador_morto:
                                prioridade_host += max(0, 1000 - dist_host)
                            if not jogador_remoto_morto:
                                prioridade_cliente += max(0, 1000 - dist_cliente)

                            # Bônus por vulnerabilidade: quanto menor a vida, mais atraente
                            prioridade_host += max(0, (vida_maxima - vida) * 0.3)
                            prioridade_cliente += max(0, (vida_maxima - vida_remota) * 0.3)

                            # Chance aleatória leve para variação de comportamento
                            prioridade_host *= random.uniform(0.8, 1.2)
                            prioridade_cliente *= random.uniform(0.8, 1.2)

                            # Define novo alvo se diferença for significativa
                            if abs(prioridade_host - prioridade_cliente) > 150:
                                novo_alvo = "host" if prioridade_host > prioridade_cliente else "cliente"
                                if novo_alvo != alvo_atual:
                                    alvo_atual = novo_alvo
                                    tempo_ultima_troca_alvo = tempo_atual

                    # Define coordenadas do alvo com base na escolha
                    if alvo_atual == "host":
                        alvo_x, alvo_y = pos_x_personagem, pos_y_personagem
                        direcao_alvo = ultima_tecla_movimento
                    else:
                        alvo_x, alvo_y = pos_x_player2, pos_y_player2
                        direcao_alvo = direcao_player2





            lacerante_manifestacao.atualizar_e_desenhar_sangue_lacerante(tela, inimigos_comum, None)

            # Desenhe os inimigos na tela
            with lock_inimigos: # Evita ler enqaunto a threading escreve
                for inimigo in inimigos_comum:
                    inimigo["image"] = frames_inimigo[frame_atual % len(frames_inimigo)]

                    tela.blit(inimigo["image"], inimigo["rect"])
                    desenhar_barra_de_vida(tela, inimigo["rect"].x, inimigo["rect"].y - 10, largura_inimigo, 5, inimigo["vida"], inimigo["vida_maxima"], inimigo.get("eletrocutado", False), Executa_inimigo if Ultimo_Estalo else None)
            personagem_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem*0.5, altura_personagem*0.8)
            inimigos_rects = [inimigo["rect"] for inimigo in inimigos_comum]


            if imune_tempo_restante > 0:
                imune_tempo_restante -= relogio.get_time()  
            else:
                imune_tempo_restante = 0 

            if not jogador_morto and not Safe:  # Só pode tomar dano se estiver vivo 
                if verificar_colisao_personagem_inimigo(personagem_rect, inimigos_rects) and imune_tempo_restante <= 0:

                    if tempo_atual - tempo_ultimo_hit_inimigo >= intervalo_hit_inimigo:
                        Dano_pos_resistencia_person = int(((vida_maxima * 0.06)+dano_inimigo_perto) - Resistencia)
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
                        Dano_person.play()
                        piscando_vida = True

                if aurea == "Devota" and not escudo_devota_ativo and tempo_atual - tempo_ultimo_escudo >= intervalo_escudo:
                    escudo_devota_ativo = True
                    tempo_ultimo_escudo = tempo_atual
                    # adicionar um efeito visual de "escudo ativado"
            else:
                # Morto = não sofre dano
                pass


            # --- SISTEMA DE MORTE E REVIVAL ---

            # Jogador morre
            if vida <= 0 and not jogador_morto:
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
                    pos_x_personagem, pos_y_personagem = gerar_posicao_aleatoria(
                        largura_mapa, altura_mapa, largura_personagem, altura_personagem
                    )
                else:
                    largura_disparo, altura_disparo = 8, 8
                    # Marca jogador como morto (revival temporário)
                    jogador_morto = True
                    tempo_morte = pygame.time.get_ticks()
                    vida = 0
                    sprite_atual = sprite_morto

            # Se estiver morto, controla o revival
            if jogador_morto:
                tempo_passado_morte = pygame.time.get_ticks() - tempo_morte

                # Desenha sprite de caído
                tela.blit(sprite_morto, (pos_x_personagem, pos_y_personagem))


                # Calcula o tempo restante para reviver em segundos
                segundos_restantes = max(0, (tempo_revive - (tempo_passado_morte // 1000)))  # tempo_revive é em segundos
                texto_timer = fonte_mensagem.render(f"Revive em {segundos_restantes}s", True, (255, 80, 80))
                tela.blit(texto_timer, (pos_x_personagem - 20, pos_y_personagem - 40))

                # ⚙️ 1️⃣ Se o tempo de revival acabou e o outro jogador está morto → Game Over
                if jogador_morto:
                    # Calcula o tempo passado desde a morte do jogador
                    tempo_passado_morte = pygame.time.get_ticks() - tempo_morte

                    # Desenha a sprite do jogador morto
                    tela.blit(sprite_morto, (pos_x_personagem, pos_y_personagem))

                    # Calcula o tempo restante para reviver em segundos
                    segundos_restantes = max(0, (tempo_revive - (tempo_passado_morte // 1000)))  # tempo_revive é em segundos
                    texto_timer = fonte_mensagem.render(f"Revive em {segundos_restantes}s", True, (255, 80, 80))
                    tela.blit(texto_timer, (pos_x_personagem - 20, pos_y_personagem - 40))

                    # ⚙️ 1️⃣ Se o tempo de revival acabou e o outro jogador também está morto → Game Over
                    if modo == "join" and jogador_remoto_morto:
                        fila_envio.put({"game_over": True})
                        mostrar_tutorial = False
                        try:
                            with open("saves/tutorial_config.json", "w") as f:
                                json.dump({"mostrar_tutorial": False}, f)
                        except:
                            pass
                        Musica_tema_fases.stop()
                        Som_tema_fases.stop()
                        if moedas_coletadas > 0:
                            moedas_coletadas = tela_upgrade_aureas(tela, fonte, moedas_coletadas)
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

                    # ⚙️ 2️⃣ Se o tempo de revival acabou, mas o outro jogador está vivo → revive
                    elif tempo_passado_morte >= tempo_revive * 1000 and not jogador_remoto_morto:
                        vida = vida_maxima // 2  # O jogador revive com metade da vida máxima
                        jogador_morto = False  # O jogador revive
                        sprite_atual = frames_animacao["down"][0]  # Restaura o sprite original do jogador

                        # Enviar para o host que o jogador reviveu
                        if modo == "join":
                            fila_envio.put({"reviver": True})
                if modo == "host" :
                    if estado_jogo == "game_over" or not running:
                        mostrar_tutorial = False
                        try:
                            with open("saves/tutorial_config.json", "w") as f:
                                json.dump({"mostrar_tutorial": False}, f)
                        except:
                            pass
                        Musica_tema_fases.stop()
                        Som_tema_fases.stop()
                        if moedas_coletadas > 0:
                            moedas_coletadas = tela_upgrade_aureas(tela, fonte, moedas_coletadas)
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
                # No lado do host, quando o jogador renasce
                if modo == "host" :
                    if jogador_morto and tempo_passado_morte >= tempo_revive * 1000:
                        jogador_morto = False  # O jogador revive
                        # Definir a posição e outras variáveis, se necessário
                        pos_x_personagem = largura_mapa // 2
                        pos_y_personagem = altura_mapa // 2
                        vida = vida_maxima // 2  # O jogador renasce com metade da vida
                        sprite_atual = frames_animacao["down"][0]  # Restabelece o sprite



            # Adicione esta verificação para controlar o piscar da barra de vida
            if piscando_vida:
                if False: # Desativado para o HUD widescreen
                    if tempo_atual % 500 < 250:  # Altere o valor 500 e 250 conforme necessário
                        # Desenha a barra de vida piscando em vermelho
                        pygame.draw.rect(tela, (255, 0, 0), (posicao_barra_vida[0], posicao_barra_vida[1], largura_barra_vida, altura_barra_vida))
                    else:
                        # Desenha a barra de vida normalmente
                        pygame.draw.rect(tela, verde, (posicao_barra_vida[0], posicao_barra_vida[1], (vida / vida_maxima) * largura_barra_vida, altura_barra_vida))

                # Adicione esta verificação para parar o piscar depois de um tempo
                if tempo_atual - tempo_ultimo_hit_inimigo >= intervalo_hit_inimigo:
                    piscando_vida = False

            tempo_atual = pygame.time.get_ticks()

            if boss_vivo1:
                if not em_ataque_especial and pygame.time.get_ticks() - tempo_ultimo_ataque >= 5000:  # Intervalo entre ataques
                    # Inicia o ataque especial
                    em_ataque_especial = True
                    jogador_posicoes = []  # Reiniciar lista de posições
                    tempo_ataque_especial = pygame.time.get_ticks()

                if em_ataque_especial:
                    tempo_atual = pygame.time.get_ticks()
                    indice_imagem = (tempo_atual - tempo_ataque_especial) // intervalo_troca

                    # Atualizar a posição somente no início de cada intervalo, exceto no quinto frame
                    if len(jogador_posicoes) <= indice_imagem < len(imagens_ataque) - 2:
                        jogador_posicoes.append((pos_x_personagem, pos_y_personagem))

                    ataque_concluido = ataque_especial_boss(jogador_posicoes, imagens_ataque, tempo_ataque_especial, intervalo_troca, tela)
                    if ataque_concluido:
                        em_ataque_especial = False
                        tempo_ultimo_ataque = pygame.time.get_ticks()

            # Verificar colisões com as bolhas e aplicar dano no loop principal
            if em_ataque_especial:
                personagem_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                for i, posicao in enumerate(jogador_posicoes[-1:]):
                    if i < len(imagens_ataque):
                        bolha_rect = pygame.Rect(posicao[0], posicao[1], 100, 100)  # Ajuste o tamanho da bolha aqui
                        hitboxes[i] = bolha_rect
                        # Verificar colisão com o personagem
                        if len(jogador_posicoes) == indice_imagem  and personagem_rect.colliderect(bolha_rect):
                            if escudo_devota_ativo:
                                escudo_devota_ativo= False
                                pass
                            elif pygame.time.get_ticks() - tempo_ultimo_dano_ataque >= 5000:  # Dano a cada 4 segundos
                                vida -= (vida_maxima * 0.10) + Dano_Boss_Habilit
                                tempo_ultimo_dano_ataque= pygame.time.get_ticks()


            ###############################################
            #   DESENHA OS PERSONAGENS NA TELA
            ###############################################

            # HOST (jogador 1 local)
            if modo == "host" :
                # --- Desenha o próprio personagem ---
                if jogador_morto:
                    tela.blit(sprite_morto, (pos_x_personagem, pos_y_personagem))
                else:
                    desenhar_personagem_com_dano(tela, frames_animacao[direcao_atual][frame_atual % len(frames_animacao[direcao_atual])], pos_x_personagem, pos_y_personagem, tempo_atual, tempo_ultimo_hit_inimigo)

                # --- Desenha o segundo jogador (cliente) ---
                if cliente_ativo:
                    try:
                        if jogador_remoto_morto:
                            tela.blit(sprite_morto, (pos_x_player2, pos_y_player2))
                        else:
                            tela.blit(frames_animacao2[direcao_player2][frame_atual % len(frames_animacao2[direcao_player2])], (pos_x_player2, pos_y_player2))
                    except KeyError:
                        tela.blit(frames_animacao2["down"][frame_atual % len(frames_animacao2["down"])], (pos_x_player2, pos_y_player2))

            # JOIN (jogador 2 local)
            elif modo == "join":
                # --- Desenha o próprio personagem ---
                if jogador_morto:
                    tela.blit(sprite_morto, (pos_x_personagem, pos_y_personagem))
                else:
                    desenhar_personagem_com_dano(tela, frames_animacao2[direcao_atual_p2][frame_atual % len(frames_animacao2[direcao_atual_p2])], pos_x_personagem, pos_y_personagem, tempo_atual, tempo_ultimo_hit_inimigo)

                # --- Desenha o host (jogador 1 remoto) ---
                if host_ativo:
                    try:
                        if jogador_remoto_morto:
                            tela.blit(sprite_morto, (pos_x_player2, pos_y_player2))
                        else:
                            tela.blit(frames_animacao[direcao_player2][frame_atual % len(frames_animacao[direcao_player2])], (pos_x_player2, pos_y_player2))
                    except KeyError:
                        tela.blit(frames_animacao["down"][frame_atual % len(frames_animacao["down"])], (pos_x_player2, pos_y_player2))






            # Desenhar zona de teleporte (se estiver mirando no modo mouse)
            Variaveis.desenhar_zona_teleporte(tela, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, distancia_dash)

            for moeda in moedas_soltadas[:]:  # cópia da lista para evitar erro ao remover
                if personagem_rect.colliderect(moeda["rect"]):
                    moedas_coletadas+=1
                    moedas_soltadas.remove(moeda)

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
                diferenca_altura = altura_personagem - 115
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
                        pos_x_petro += 1 * direcao_petro[0]
                        pos_y_petro += 1 * direcao_petro[1]


                    # Calcula a distância entre "Petro" e o inimigo mais próximo
                    distancia_petro_inimigo = math.sqrt((pos_x_petro - pos_x_inimigo_mais_proximo) ** 2 + (pos_y_petro - pos_y_inimigo_mais_proximo) ** 2)

                    # Verifica se "Petro" está próximo o suficiente para aplicar dano
                    if distancia_petro_inimigo <= 50:
                        # Verifica se passou tempo suficiente desde o último dano
                        tempo_atual_petro = pygame.time.get_ticks()
                        if tempo_atual_petro - tempo_anterior_petro >= intervalo_dano_petro:
                            # Aplica dano ao inimigo mais próximo
                            Dano_pos_resistencia_petro=dano_inimigo-Resistencia_petro
                            if Dano_pos_resistencia_petro < 0:
                                pass

                            else:
                                vida_petro-=int(Dano_pos_resistencia_petro)#Dano em petro


                            inimigo_mais_proximo["vida"] -= int(dano_person_hit * 0.005)+ dano_petro
                            tempo_anterior_petro = tempo_atual_petro

                            # Verifica se o inimigo foi derrotado
                            if inimigo_mais_proximo["vida"] <= 0:
                                vida_inimigo_maxima += ganho_vida_inimigo_comum(23)
                                pontuacao += int(75 + inimigos_eliminados * 0.5)
                                pontuacao_exib += int(75 + inimigos_eliminados * 0.5)
                                Resistencia_petro+=24.5
                                vida_maxima_petro+=35
                                dano_person_hit+=8
                                inimigos_eliminados += 1
                                dano_petro+=0.035 
                                dano_inimigo_longe+=2
                                dano_inimigo_perto+=0.35
                                # Remove o inimigo da lista de inimigos comuns
                                inimigos_comum.remove(inimigo_mais_proximo) 

                            if not boss_vivo1:
                                if vida_boss>0:
                                    vida_boss+=55
                                    vida_maxima_boss1= vida_boss


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



                if boss_vivo1:
                    # Define a direção de Petro em relação ao boss
                    dx = pos_x_chefe - pos_x_petro
                    dy = pos_y_chefe - pos_y_petro

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
                    distancia_petro_boss = math.sqrt((pos_x_petro - pos_x_chefe) ** 2 + (pos_y_petro - pos_y_chefe) ** 2)
                    if distancia_petro_boss <= 50:
                        # Verifica se passou tempo suficiente desde o último dano
                        tempo_atual_petro = pygame.time.get_ticks()
                        if tempo_atual_petro - tempo_anterior_petro >= intervalo_dano_petro:
                            # Aplica dano ao "boss"
                            vida_petro -= int(dano_boss)
                            vida_petro+= int(vida_maxima_petro-vida_petro)*quantidade_roubo_vida
                            vida_boss-= dano_boss_mitigado(int(dano_person_hit*0.15)+15, 1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                            tempo_anterior_petro = tempo_atual_petro

                if comando_direção_petro:
                    direcao_atual_petro="left_petro"
                    comando_direção_petro=False

                desenhar_barra_de_vida_petro(tela, vida_petro, pos_x_petro, pos_y_petro - 20,vida_maxima_petro)  
                tela.blit(petro_nivel[direcao_atual_petro][frame_atual % len(petro_nivel[direcao_atual_petro])], (pos_x_petro, pos_y_petro))


            #AQUI GERAMOS O BOSS:
                # --- ATIVAÇÃO DO BOSS ---
            if iniciar_boss and not r_press:
                tempo_atual = pygame.time.get_ticks()
                tempo_boss_entrada_fim = tempo_atual + 2500
                r_press = True
                iniciar_boss = False
                boss_vivo1 = True
                Musica_tema_fases.stop()
                Musica_tema_Boss1.play(loops=-1)
                tempo_inicio_boss = pygame.time.get_ticks()
                tempo_ultima_mudanca_direcao_boss = tempo_inicio_boss
                vida_boss = vida_maxima_boss1
                boss_envenenado = False
                frame_atual_chefe = 0
                tempo_passado_animacao_chefe = 0

            # --- LÓGICA DO BOSS (somente host controla) ---
            if modo == "host"  and boss_vivo1:
                tempo_passado_animacao_chefe += relogio.get_rawtime()
                if tempo_passado_animacao_chefe >= tempo_animacao_chefe:
                    tempo_passado_animacao_chefe = 0
                    frame_atual_chefe = (frame_atual_chefe + 1) % 2

                # Mudar direção aleatoriamente
                tempo_atual = pygame.time.get_ticks()
                intervalo_mudanca_direcao_boss = random.randint(1000, 3000)
                if tempo_atual - tempo_ultima_mudanca_direcao_boss >= intervalo_mudanca_direcao_boss:
                    direcoes_possiveis = ['up', 'down', 'left', 'right']
                    direcoes_possiveis.remove(ultima_direcao_boss)
                    ultima_direcao_boss = random.choice(direcoes_possiveis)
                    tempo_ultima_mudanca_direcao_boss = tempo_atual

                # Movimento do boss
                inimigos_comum = []  # limpa inimigos comuns durante o boss
                if ultima_direcao_boss == 'up':
                    pos_y_chefe = max(0, pos_y_chefe - Velocidade_boss)
                elif ultima_direcao_boss == 'down':
                    pos_y_chefe = min(altura_mapa - chefe_altura, pos_y_chefe + Velocidade_boss)
                elif ultima_direcao_boss == 'left':
                    pos_x_chefe = max(0, pos_x_chefe - Velocidade_boss)
                elif ultima_direcao_boss == 'right':
                    pos_x_chefe = min(largura_mapa - chefe_largura, pos_x_chefe + Velocidade_boss)

                # Muda direção se tocar na borda
                if pos_x_chefe <= 0 or pos_x_chefe >= largura_mapa - chefe_largura or pos_y_chefe <= 0 or pos_y_chefe >= altura_mapa - chefe_altura:
                    if ultima_direcao_boss == 'up': ultima_direcao_boss = 'down'
                    elif ultima_direcao_boss == 'down': ultima_direcao_boss = 'up'
                    elif ultima_direcao_boss == 'left': ultima_direcao_boss = 'right'
                    elif ultima_direcao_boss == 'right': ultima_direcao_boss = 'left'

                # --- Colisão com disparos do jogador ---
                for disparo in disparos[:]:
                    rect_disparo = disparo["rect"]
                    rect_boss = pygame.Rect(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura)
                    acertou_boss_disparo = (
                        lacerante_manifestacao.colisao_corte(disparo, rect_boss, tempo_atual)
                        if disparo.get("tipo_manifestacao") == "lacerante_corte"
                        else rect_disparo.colliderect(rect_boss)
                    )
                    if acertou_boss_disparo:
                        if vida_boss > 0:
                            if random.random() <= chance_critico:
                                dano = dano_person_hit * 3
                                cor = (255, 255, 0)
                                fonte_dano = fonte_dano_critico
                            else:
                                dano = dano_person_hit
                                cor = (255, 0, 0)
                                fonte_dano = fonte_dano_normal

                        # Efeito de veneno
                        if not boss_envenenado and Poison_Active:
                            boss_envenenado = True
                            global duracao_veneno_boss
                            dano_por_tick_veneno_boss = vida_boss * Dano_Veneno_Acumulado
                            duracao_veneno_boss = 8000 + cartas_compradas.get("Poison", 0) * 100
                            tempo_inicio_veneno_boss = pygame.time.get_ticks()
                            ultimo_tick_veneno_boss = pygame.time.get_ticks()

                        dano *= lacerante_manifestacao.multiplicador_dano_disparo(disparo)

                        # Aplica dano e roubo de vida
                        dano = dano_boss_mitigado(dano, 1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                        texto_hit = "-" + str(int(dano))
                        pos_texto = (pos_x_chefe + chefe_largura // 2 - fonte_dano.size(texto_hit)[0] // 2, pos_y_chefe - 20)
                        Variaveis.registrar_efeito_texto(
                            efeitos_texto,
                            texto_hit,
                            pos_texto[0],
                            pos_texto[1],
                            tempo_atual,
                            cor,
                            chave=("boss-dano", "coop", int(tempo_atual) // 90, int(dano)),
                        )
                        vida_boss -= dano
                        if (vida_boss <= 0 or (Ultimo_Estalo and vida_boss <= limiar_execucao_boss(Executa_inimigo) * vida_maxima_boss1)):
                            if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                largura_disparo += 0.095
                                altura_disparo += 0.095
                        estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)
                        if quantidade_roubo_vida > 0:
                            vida += (vida_maxima - vida) * quantidade_roubo_vida

                # --- Colisão com jogador ---
                rect_boss = pygame.Rect(pos_x_chefe, pos_y_chefe, 200, 100)
                rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                if rect_boss.colliderect(rect_personagem) and tempo_atual >= tempo_boss_entrada_fim:
                    tempo_atual = pygame.time.get_ticks()
                    if tempo_atual - tempo_ultimo_ataque >= 2500:
                        dano_boss_total = int((vida_maxima * 0.10) + 150 + dano_boss)
                        if not escudo_devota_ativo:
                            vida -= max(0, dano_boss_total - Resistencia)
                        Dano_person.play()
                        piscando_vida = True
                        tempo_ultimo_ataque = tempo_atual

                # --- Atualiza frame de acordo com a vida ---
                porcentagem_vida_boss = (vida_boss / vida_maxima_boss1) * 100
                if porcentagem_vida_boss >= 90:
                    frame_porcentagem = frames_chefe1_1
                elif 60 <= porcentagem_vida_boss < 90:
                    frame_porcentagem = frames_chefe1_2
                elif 40 <= porcentagem_vida_boss < 60:
                    frame_porcentagem = frames_chefe1_3
                else:
                    frame_porcentagem = frames_chefe1_4

                # --- Aplicar dano de veneno no Boss se ele estiver envenenado ---
                if boss_envenenado:
                    tempo_atual = pygame.time.get_ticks()
                    if tempo_atual - ultimo_tick_veneno_boss >= INTERVALO_TICK_VENENO:
                        vida_boss -= dano_boss_mitigado(dano_por_tick_veneno_boss, 1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0), tipo_dano="veneno")
                        ultimo_tick_veneno_boss = tempo_atual
                    if tempo_atual - ultimo_tick_veneno_boss <= 1500:
                        dano_veneno_texto = "-" + str(int(dano_por_tick_veneno_boss))
                        texto_dano_veneno = fonte_veneno.render(dano_veneno_texto, True, (0, 255, 0))
                        texto_dano_veneno_borda = fonte_veneno.render(dano_veneno_texto, True, (0, 0, 0))
                        pos_texto = (pos_x_chefe + chefe_largura // 2 - texto_dano_veneno.get_width() // 2, pos_y_chefe - 30)
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0] - 1, pos_texto[1]))
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0] + 1, pos_texto[1]))
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0], pos_texto[1] - 1))
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0], pos_texto[1] + 1))
                        tela.blit(texto_dano_veneno, pos_texto)
                    if tempo_atual - tempo_inicio_veneno_boss >= duracao_veneno_boss:
                        boss_envenenado = False

                # --- Renderizar ---
                tela.blit(frame_porcentagem[frame_atual_chefe], (pos_x_chefe, pos_y_chefe))
                desenhar_barra_de_vida(tela, pos_x_chefe, pos_y_chefe - 20, chefe_largura, 10, vida_boss, vida_maxima_boss1)

                fila_envio.put({
                    "boss": {
                        "x": pos_x_chefe,
                        "y": pos_y_chefe,
                        "vida": vida_boss,
                        "vida_max": vida_maxima_boss1,
                        "fase": porcentagem_vida_boss  # ou use porcentagem_vida_boss
                    }
                })
            if modo == "join" and boss_vivo1:
                for idx, disparo in enumerate(disparos[:]):
                    rect_disparo = disparo["rect"]
                    rect_boss = pygame.Rect(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura)
                    # Se o disparo colidir com o boss
                    acertou_boss_disparo = (
                        lacerante_manifestacao.colisao_corte(disparo, rect_boss, tempo_atual)
                        if disparo.get("tipo_manifestacao") == "lacerante_corte"
                        else rect_disparo.colliderect(rect_boss)
                    )
                    if acertou_boss_disparo:
                        try:
                            fila_envio.put({"hit_boss": True})
                        except:
                            pass
                        estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)
            if modo == "join" and boss_vivo1:
                for idx, onda in enumerate(ondas[:]):
                    rect_onda = onda["rect"]
                    rect_boss = pygame.Rect(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura)

                    if rect_onda.colliderect(rect_boss):
                        try:
                            fila_envio.put({"hit_boss_especial": True})
                        except:
                            pass
                        ondas.remove(onda)
            # --- DESENHAR NO CLIENT ---
            if modo == "join" and boss_vivo1:
                tela.blit(frame_porcentagem[frame_atual_chefe], (pos_x_chefe, pos_y_chefe))
                desenhar_barra_de_vida(
                    tela,
                    pos_x_chefe,
                    pos_y_chefe - 20,
                    chefe_largura,
                    10,
                    vida_boss,
                    vida_maxima_boss1
                )

            if modo == "host" :
                for inimigo in inimigos_comum:
                    inimigo_rect = inimigo["rect"]
                    inimigo_image = inimigo["image"]

                    inimigo_atingido = False

                    for disparo in disparos:

                        if verificar_colisao_disparo_inimigo(
                            disparo,
                            (inimigo["rect"].x, inimigo["rect"].y),
                            largura_disparo,
                            altura_disparo,
                            largura_inimigo,
                            altura_inimigo,
                            inimigos_eliminados
                        ):
                            if random.random() <= chance_critico:  # chance de dano crítico
                                dano = dano_person_hit * 3  # Valor do dano crítico é 3 vezes o dano normal
                                cor = (255, 255, 0)  # Amarelo (RGB)
                                fonte_dano = fonte_dano_critico
                            else:
                                dano = dano_person_hit
                                cor = (255, 0, 0)  # Vermelho (RGB)
                                fonte_dano = fonte_dano_normal

                            if Petro_active:
                                if vida_petro < vida_maxima_petro:
                                    vida_petro += (vida_maxima_petro - vida_petro) * 0.25

                            dano *= lacerante_manifestacao.multiplicador_dano_disparo(disparo)

                            # Renderize o texto do dano
                            texto_hit = "-" + str(int(dano))
                            pos_texto = (
                                inimigo["rect"].x + largura_inimigo // 2 - fonte_dano.size(texto_hit)[0] // 2,
                                inimigo["rect"].y - 20
                            )
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
                            if disparo.get("tipo_manifestacao") == "lacerante_corte":
                                lacerante_manifestacao.aplicar_laceracao(inimigo, tempo_atual)
                            estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)  # Remover o disparo após colisão



                            if inimigo["vida"] <= 0:
                                posicao_inimigo = inimigo["rect"].center
                                soltar_moeda(posicao_inimigo)
                                # envia pro client desenhar a moeda também
                                try:
                                    fila_envio.put({"drop_moeda": posicao_inimigo})
                                except:
                                    pass
                                inimigos_comum.remove(inimigo)
                                if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                    largura_disparo += 0.095
                                    altura_disparo += 0.095

                                # Crescimento proporcional por nível de ameaça
                                aplicar_crescimento_personalizado()

                                ganho = int(75 + math.log2(inimigos_eliminados + 1) * 4)
                                pontuacao += ganho
                                eliminacoes_consecutivas_impulsiva += 1

                                pontuacao_exib += ganho
                                fila_envio.put({"pontuacao_atual": pontuacao_exib})
                                fila_envio.put({"crescimento_local": True})

                                # Boss: aumento escalonado
                                if not boss_vivo1:
                                    if vida_boss > 0:
                                        vida_boss += 15 + nivel_ameaca * 10
                                        vida_maxima_boss1 = vida_boss

                            if quantidade_roubo_vida > 0:
                                vida += (vida_maxima - vida) * quantidade_roubo_vida



                    if inimigo_atingido:
                        break  # Sair do loop externo se um inimigo foi atingido



                    if pontuacao_exib > pontuacao_magia:
                        pontuacao_magia = min(pontuacao_exib, maxima_pontuacao_magia)

            if modo == "join":
                for inimigo in inimigos_comum:
                    inimigo_rect = inimigo["rect"]
                    inimigo_image = inimigo["image"]

                    inimigo_atingido = False

                    for disparo in disparos:

                        if verificar_colisao_disparo_inimigo(
                            disparo,
                            (inimigo["rect"].x, inimigo["rect"].y),
                            largura_disparo,
                            altura_disparo,
                            largura_inimigo,
                            altura_inimigo,
                            inimigos_eliminados
                        ):
                            if random.random() <= chance_critico:  # chance de dano crítico
                                dano = dano_person_hit * 3  # Valor do dano crítico é 3 vezes o dano normal
                                cor = (255, 255, 0)  # Amarelo (RGB)
                                fonte_dano = fonte_dano_critico
                            else:
                                dano = dano_person_hit
                                cor = (255, 0, 0)  # Vermelho (RGB)
                                fonte_dano = fonte_dano_normal

                            if Petro_active:
                                if vida_petro < vida_maxima_petro:
                                    vida_petro += (vida_maxima_petro - vida_petro) * 0.25

                            # Renderize o texto do dano
                            texto_hit = "-" + str(int(dano))
                            pos_texto = (
                                inimigo["rect"].x + largura_inimigo // 2 - fonte_dano.size(texto_hit)[0] // 2,
                                inimigo["rect"].y - 20
                            )
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
                            estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)  # Remover o disparo após colisão
                            # Notifica o host se for client
                            if modo == "join":
                                try:
                                    idx = inimigos_comum.index(inimigo)
                                    fila_envio.put({"hit": idx})
                                except:
                                    pass




                            if quantidade_roubo_vida > 0:
                                vida += (vida_maxima - vida) * quantidade_roubo_vida



                    if inimigo_atingido:
                        break  # Sair do loop externo se um inimigo foi atingido



                    if pontuacao_exib > pontuacao_magia:
                        pontuacao_magia = min(pontuacao_exib, maxima_pontuacao_magia)





            total_cartas_compradas = sum(cartas_compradas.values())
            custo_carta_atual = custo_base_carta + (total_cartas_compradas * custo_por_carta)
            # Verifica se a pontuação atingiu 1500 e se o jogador pressionou 'Q'
            if modo == "host" :
                if obter_modo_cartas() != "drops" and (not jogador_remoto_morto) and (pontuacao_exib >= custo_carta_atual) and (keys[config_teclas["Comprar na loja"]] or (joystick and joystick.get_button(3))):
                    # Calcula quantas cartas o jogador pode comprar
                    max_cartas = pontuacao_exib // custo_carta_atual
                    if max_cartas <= 0:
                        continue  # segurança

                    # Debita tudo de uma vez
                    total_custo = custo_carta_atual * max_cartas
                    pontuacao_exib -= total_custo
                    pontuacao_magia -= total_custo
                    apertou_q = True

                    # Envia pro client abrir loja também
                    fila_envio.put({"abrir_loja": True, "quantidade_cartas": max_cartas})
                    Safe=True
                    ret = tela_de_pausa(velocidade_personagem, intervalo_disparo, vida, largura_disparo, altura_disparo,
                                        trembo, dano_person_hit, chance_critico, roubo_de_vida, quantidade_roubo_vida,
                                        tempo_cooldown_dash, vida_maxima, Petro_active, Resistencia, vida_petro,
                                        vida_maxima_petro, dano_petro, xp_petro, petro_evolucao, Resistencia_petro,
                                        Chance_Sorte, Poison_Active, Dano_Veneno_Acumulado, Executa_inimigo, Ultimo_Estalo,
                                        mostrar_info, Mercenaria_Active, Valor_Bonus, dispositivo_ativo, Tempo_cura,
                                        porcentagem_cura, cartas_compradas, pontuacao_exib,max_cartas_compraveis=max_cartas, inimigos_eliminados=inimigos_eliminados)
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

                    # após sair da loja, avisa o outro lado
                    fila_envio.put({"abrir_loja": False})
                    tela_de_espera_host(tela, fila_envio, fila_recebimento)
                    Safe=False






            cooldowns = {
                "disparo": max(0.0, (intervalo_disparo_racional(intervalo_disparo, aurea, racional_dilatacao_fim, tempo_atual) - (tempo_atual - tempo_ultimo_disparo)) / 1000.0),
                "teleporte": max(0.0, (tempo_cooldown_dash - (pygame.time.get_ticks() - tempo_ultimo_dash)) / 1000.0),
                "onda": max(0.0, (cooldown_habilidade * lacerante_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) - (tempo_atual - tempo_ultimo_uso_habilidade)) / 1000.0),
                "loja": 1 if pontuacao_exib >= custo_carta_atual else 0, 
            }

            if False: # Desativado pois o HUD agora é widescreen desenhado nas bordas
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

                if vida > vida_maxima:
                    vida_maxima=vida

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

            # Controle de exibição
            if mostrar_tutorial:
                tempo_decorrido = time.time() - tempo_inicial
                if 'mensagens_exibidas' not in globals():
                    mensagens_exibidas = set()
                    mensagem_ativa = None
                    tempo_fim_mensagem = 0

                # Ativando nova mensagem, se for o tempo certo
                for tempo_msg, texto_msg in mensagens_iniciais:
                    if int(tempo_decorrido) == tempo_msg and tempo_msg not in mensagens_exibidas:
                        mensagem_ativa = texto_msg
                        tempo_fim_mensagem = tempo_decorrido + 10  # visível por 10 segundos
                        mensagens_exibidas.add(tempo_msg)

                # Exibindo mensagem ativa com contorno
                if mensagem_ativa and tempo_decorrido < tempo_fim_mensagem:
                    fonte_mensagem = pygame.font.Font(None, 48)
                    texto = mensagem_ativa
                    texto_renderizado = fonte_mensagem.render(texto, True, (255, 255, 255))
                    texto_borda = fonte_mensagem.render(texto, True, (0, 0, 0))

                    x = largura_mapa // 2 - texto_renderizado.get_width() // 2
                    y = int(altura_mapa * 0.15)

                    tela.blit(texto_borda, (x - 1, y))
                    tela.blit(texto_borda, (x + 1, y))
                    tela.blit(texto_borda, (x, y - 1))
                    tela.blit(texto_borda, (x, y + 1))
                    tela.blit(texto_renderizado, (x, y))
                else:
                    mensagem_ativa = None
            tempo_atual = pygame.time.get_ticks()
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
            for moeda in moedas_soltadas:
                tela.blit(moeda["image"], moeda["rect"])
            # Exibir ping no canto superior direito
            if modo == "join":  # apenas o cliente precisa ver o ping
                fonte_ping = pygame.font.Font(None, 32)
                texto_ping = fonte_ping.render(f"Ping: {ping_atual} ms", True, cor_ping)
                tela.blit(texto_ping, (largura_mapa - texto_ping.get_width() - 20, 40))
            # --- Popup Boss ---
            if convite_boss_ativo:
                fonte_popup = pygame.font.Font(None, 32)
                rect_popup = pygame.Rect(tela.get_width() - 320, 20, 300, 60)
                pygame.draw.rect(tela, (30, 30, 30), rect_popup, border_radius=8)
                pygame.draw.rect(tela, (200, 200, 0), rect_popup, 2, border_radius=8)

                if convite_boss_enviado:
                    texto = fonte_popup.render("Convite enviado...", True, (255, 255, 0))
                elif convite_boss_recebido:
                    restante = 5 - (pygame.time.get_ticks() - convite_boss_tempo) // 1000
                    texto = fonte_popup.render("Aperte Y para aceitar o Boss", True, (255, 255, 255))
                else:
                    texto = fonte_popup.render("Esperando confirmação...", True, (255, 255, 255))

                tela.blit(texto, (rect_popup.x + 15, rect_popup.y + 20))




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

            # Atualizar e desenhar fragmentos de morte / Trembo
            atualizar_e_desenhar_fragmentos(tela)
            vfx_disparo_player.atualizar_e_desenhar_particulas(tela, 1.0, config_graficos)

            tela.blit(cursor_imagem, (mouse_x, mouse_y))

            exibir_cronometro(tela)

            pygame.display.flip()
            FPS.tick(100)  # Limita a 100 FPS


        # Encerrar o Pygame
        pygame.quit()
    except CleanExit:
        return
    finally:
        _sys.exit = _orig_sys_exit
        _os._exit = _orig_os_exit
        if _orig_builtins_exit:
            _builtins.exit = _orig_builtins_exit


if __name__ == '__main__':
    executar_jogo()
