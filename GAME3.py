
import Caminhos
import pygame
import sys
import random
import math
import subprocess
import json
import os
import lacerante_manifestacao
import prismatica_manifestacao
import retornante_manifestacao
import parasitica_manifestacao
import condutora_manifestacao
import gravitante_manifestacao
import ancorada_manifestacao
import teleporte_manifestacao
from qa_logger import instalar_captura_global, instalar_filtro_prints, registrar_erro
from Tela_Cartas import tela_de_pausa as tela_de_pausa_single
from Tela_Cartas_Coop import tela_de_pausa as tela_de_pausa_coop
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
aurea = None
escudo_devota_ativo = True
duracao_incendio_vanguarda = 5000
intervalo_escudo = 30000
racional_dilatacao_fim = 0
racional_dilatacao_proximo_uso = 0
estado_devota = criar_estado_devota(False)
pressao_pos_boss_spawn = criar_estado_pressao_pos_boss()
gerar_fragmentos_morte = None

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

Boss_andando=False
texto_dano = None
tempo_texto_dano = 0

estalos = aplicar_volume_som(pygame.mixer.Sound("Sounds/Estalo.mp3"), config_audio)

som_ataque_boss = aplicar_volume_som(pygame.mixer.Sound("Sounds/Hit_Boss1.mp3"), config_audio)

Hit_inimigo3 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Inimigo3_hit.mp3"), config_audio)

Disparo_Geo = aplicar_volume_som(pygame.mixer.Sound("Sounds/Disparo_Geo.wav"), config_audio)

Musica_tema_Boss3 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase3_Boss.mp3"), config_audio, canal="musica", volume_maximo=1.0)  
Musica_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase_boas.mp3"), config_audio, canal="musica", volume_maximo=0.07)
Som_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Esgoto.mp3"), config_audio, canal="musica", volume_maximo=0.10)
Som_portal = aplicar_volume_som(pygame.mixer.Sound("Sounds/Portal.mp3"), config_audio, canal="efeitos", volume_maximo=0.06)
Boss_Queijo = aplicar_volume_som(pygame.mixer.Sound("Sounds/Queijo.mp3"), config_audio, canal="efeitos", volume_maximo=0.11)
Boss3_andando = aplicar_volume_som(pygame.mixer.Sound("Sounds/Boss3_andando.mp3"), config_audio, canal="efeitos", volume_maximo=0.7)
Frascos = aplicar_volume_som(pygame.mixer.Sound("Sounds/Frasco.mp3"), config_audio, canal="efeitos", volume_maximo=0.02)  

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
fe_pai_rato = 50
fase_pai_rato = 1
queijos_sagrados = []
avisos_pai_rato = []
projeteis_veneno_pai_rato = []
pai_rato_eventos = set()
pai_rato_chuva_frascos = None
pai_rato_cauda = None
pai_rato_carga = None
pai_rato_consumindo = None
pai_rato_ritual = None
pai_rato_atordoado_ate = 0
tempo_ultimo_cuspida_pai_rato = 0
tempo_ultimo_cauda_pai_rato = 0
tempo_ultimo_carga_pai_rato = 0
tempo_ultimo_queijo_pai_rato = 0
tempo_ultimo_chuva_pai_rato = 0
pai_rato_fala_entrada_feita = False
tempo_proxima_fala_pai_rato = 0
ultima_fala_pai_rato = None
FALAS_PAI_RATO_ENTRADA = [
    "Quem ousa pisar no templo do Grande Queijo?",
    "Farejo carne viva... e desrespeito.",
    "Ajoelhe-se, pequena invasora.",
    "Voce veio roubar nossa reliquia? Entao morrera diante dela.",
    "O esgoto e nosso ceu. O queijo e nosso sol.",
    "Eu sou o Pai-Rato, boca da fome e cauda da verdade!",
    "Voce nao entende este lugar. Aqui, a podridao reza.",
    "Ha seculos esperamos por alguem tolo o bastante para entrar.",
    "Seu cheiro e limpo demais. Vamos corrigir isso.",
    "O fragmento escolheu nossa ninhada.",
    "O altar range. A fe desperta.",
    "Entre, crianca do mundo seco. Afogue-se na nossa graca.",
    "Nao toque na peca sagrada com essas maos impuras.",
    "O queijo viu sua chegada. O queijo exige seu fim.",
    "Ratos pequenos roem pao. Eu roo destinos.",
    "Voce acha que isso e um esgoto? Isto e uma catedral.",
    "Cada goteira canta meu nome.",
    "Cada osso sob seus pes pertenceu a um descrente.",
    "Seu tempo acabou no momento em que sentiu nosso cheiro.",
    "Venha, Geovana. O Pai-Rato estava esperando.",
    "O culto tem fome, e voce trouxe coragem demais.",
    "Sua luz nao entra aqui. Aqui embaixo, quem brilha e o mofo.",
    "O mundo de cima esqueceu de nos. O queijo, nao.",
    "A reliquia pulsa. Ela sabe que voce e ameaca.",
    "Ajoelhe-se ou seja mastigada.",
    "Voce chegou ao fim do tunel. E no fim, estou eu.",
    "Que seus ossos virem oferenda.",
    "Que sua pressa vire lodo.",
    "Que seu nome seja guinchado pelos meus filhos.",
    "Comecemos o rito.",
]
FALAS_PAI_RATO_ATAQUE = [
    "Beba do nosso miasma!",
    "Vidro, veneno e fe!",
    "Quebre-se!",
    "Respire fundo, invasora!",
    "O ar daqui tambem me obedece.",
    "O mofo conhece sua pele.",
    "Frascos consagrados, voem!",
    "Que a tosse vire oracao!",
    "Dance entre os cacos!",
    "O veneno e so uma bencao mal interpretada.",
    "Veja como o esgoto floresce!",
    "Cada gota carrega um sermao.",
    "Fuja, fuja... o cheiro alcanca.",
    "Eu batizei estes frascos com fome.",
    "O vidro canta antes de ferir.",
    "Voce corre bem para alguem que vai cair.",
    "Nao desvie da bencao!",
    "O lodo sobe para abraca-la.",
    "A fumaca sabe onde voce respira.",
    "Sua carne ainda e muito integra.",
    "Vamos torna-la mais... sagrada.",
    "O miasma e paciente.",
    "O veneno nao erra. Ele espera.",
    "Cacos para os pes. Fumaca para os pulmoes.",
    "Minhas garrafas carregam pequenos milagres.",
    "A podridao tambem tem pontaria.",
    "Sinta o gosto do altar!",
    "O esgoto cospe comigo!",
    "Mais perto, pequena herege.",
    "Que sua coragem escorra pelo ralo!",
]
FALAS_PAI_RATO_QUEIJO = [
    "Tragam-me o Queijo Sagrado!",
    "Minha fe precisa se alimentar!",
    "O altar provera!",
    "Ah... o aroma da salvacao.",
    "Ninguem impede o Pai-Rato de comungar.",
    "Meus dentes conhecem esse milagre.",
    "O queijo cura. O queijo lembra. O queijo reina.",
    "Protejam a oferenda!",
    "Nao toque no meu sacramento!",
    "A gordura dourada me chama!",
    "Filhos, defendam a dadiva!",
    "A fome e uma prece com dentes.",
    "Comerei, e renascerei mais imundo!",
    "O Grande Queijo ainda me ama!",
    "A reliquia exige que eu continue.",
    "So mais uma mordida... e sua morte volta a ser certa.",
    "Nao e comida. E comunhao.",
    "O cheiro... oh, o cheiro da eternidade!",
    "Meu corpo quebra, mas o queijo me remenda.",
    "Saiam do caminho! O milagre e meu!",
    "Voce nao entende o rito da mastigacao.",
    "Cada mordida e uma promessa.",
    "Cada farelo e uma vida roubada da morte.",
    "Abencoado seja o mofo que o cobre.",
    "Sagrado, fedido e perfeito.",
    "Eu ouco sua casca dourada chamando.",
    "O queijo me ve. O queijo me quer vivo.",
    "Rapido, meus filhos! A fome nao espera!",
    "Um rei nao morre de barriga vazia.",
    "Vou me curar com a graca fermentada!",
]
FALAS_PAI_RATO_QUEIJO_DESTRUIDO = [
    "Nao! Seu monstro sem fe!",
    "Voce profanou o sacramento!",
    "Esse queijo era mais puro que sua alma!",
    "Como ousa destruir minha bencao?",
    "Herege! Herege de superficie!",
    "Meus filhos... chorem pelo queijo caido!",
    "Voce nao venceu. Voce blasfemou.",
    "O cheiro dele ainda vive em mim...",
    "Eu vou roer seus dedos por isso!",
    "O altar viu o que voce fez.",
    "Nenhum perdao para quem destroi uma oferenda.",
    "Era sagrado! Sagrado!",
    "Voce partiu o coracao da ninhada.",
    "O Grande Queijo nao esquecera.",
    "Sua crueldade fede mais que o esgoto.",
    "Eu senti a fe rasgar!",
    "Voce matou um milagre indefeso.",
    "A gordura dourada... desperdicada...",
    "Nao, nao, nao! Ainda havia poder nele!",
    "Vou transformar sua vitoria em chorume!",
    "Que seus ossos nunca sequem!",
    "Voce interrompeu minha comunhao!",
    "Esse insulto sera pago em sangue.",
    "O rito falhou... mas minha fome nao.",
    "Voce acha que isso me enfraquece?",
    "Eu ainda tenho dentes!",
    "O altar exige vinganca!",
    "Meus guinchos vao perseguir seu sono.",
    "A fe nao morre. Ela morde.",
    "Voce destruiu o queijo... agora eu destruo voce.",
]
FALAS_PAI_RATO_FINAL = [
    "Minha fe... ainda... mastiga...",
    "Nao vou cair diante de uma filha da superficie!",
    "O queijo... me prometeu eternidade...",
    "Meus filhos, guinchem mais alto!",
    "O altar esta rachando... nao... nao!",
    "A reliquia nao pode escolher voce!",
    "Eu sou o Pai! Eu sou a fome!",
    "Mesmo quebrado, eu ainda mordo!",
    "Voce queimou minha fe, mas nao meus dentes!",
    "Nao recue agora. Venha terminar sua blasfemia.",
    "O esgoto inteiro vai lembrar do meu nome!",
    "Minha cauda ainda derruba templos!",
    "Eu vou te arrastar para baixo comigo!",
    "O mofo cobrira sua vitoria.",
    "Nao existe luz suficiente para purificar este lugar.",
    "O fragmento pulsa por mim... por mim!",
    "Eu ouvi o queijo sussurrar... ele mandou matar voce.",
    "Minha carne falha, mas minha fome e divina.",
    "Voce nao venceu o culto. So acordou sua ira.",
    "A catedral afunda, mas eu ainda sou seu rei!",
    "Nao olhe para mim com pena!",
    "Eu era eterno neste buraco!",
    "Meus ossos sao pilares!",
    "Minha baba e bencao!",
    "Meu sangue e lodo sagrado!",
    "Voce destruiu tudo que era dourado...",
    "Entao que reste apenas ferrugem!",
    "Geovana... devolva... a reliquia...",
    "Nao... toque... no fragmento...",
    "O Pai-Rato... nao morre... ele apodrece...",
]

# Defina as dimensões da hitbox do queijo (largura e altura)
largura_hitbox_queijo = largura_queijo + 50  # Adicione 20 pixels à largura
altura_hitbox_queijo = altura_queijo + 50  # Adicione 20 pixels à altura
pos_x_chefe3 = largura_tela /1.3  # Posição inicial do boss na tela (à direita)
pos_y_chefe3 = altura_tela / 3   # Centralizado verticalmente
chefe_largura3,chefe_altura3= largura_tela * 0.2, altura_tela * 0.3
disparos_boss3=[]
tempo_espera_ataque_boss3=5000
carregar_atributos_na_fase=True
comando_direção_petro=True
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


vida_inimigo_maxima = multiplayer_coop.aplicar_multiplicador_vida_inimigo(vida_inimigo_comum_inicial(30))
vida_inimigo= vida_inimigo_maxima
vida_boss3 = multiplayer_coop.aplicar_multiplicador_vida_boss(vida_boss3)
vida_maxima_boss3 = vida_boss3
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
    global personagem_doente, tempo_ultimo_atingido, angulo_inclinacao_personagem
    global vida_inimigo_maxima, Resistencia_petro, dano_inimigo_perto, vida_maxima_petro, dano_petro, dano_inimigo_longe
    global inimigos_eliminados, pontuacao, pontuacao_exib, eliminacoes_consecutivas, bonus_pontuacao, Boss_vivo3
    global vida_boss3, vida_maxima_boss3, vida_boss4, vida_maxima_boss4, Valor_Bonus
    global racional_dilatacao_fim, racional_dilatacao_proximo_uso

    direcao_atual = 'stop'  # Por padrão, definimos a direção como 'stop'
    dx, dy = 0, 0
    velocidade_movimento = (
        velocidade_personagem
        * fator_movimento_racional(aurea, racional_dilatacao_fim)
        * fator_velocidade_devota(aurea, estado_devota, tempo_atual)
        * condutora_manifestacao.fator_ruido_logico(manifestacao_ativa, tempo_atual)
        * condutora_manifestacao.obter_fator_velocidade_xor(tempo_atual)
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
                registrar_morte_toxica(inimigo)
                gerar_fragmentos_morte(inimigo, 3)
                if inimigo in inimigos_comum:
                    inimigos_comum.remove(inimigo)
                
                # Escalonamento de elite (Fase 3)
                mult = 1.0 + (nivel_ameaca * 0.15)
                vida_inimigo_maxima += ganho_vida_inimigo_comum(0.8 * mult)
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
                    incremento_v = ganho_progressao_boss(20 * mult)
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
                vida_boss3 -= dano_boss_mitigado(dano_choque, 3, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
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
rastros_toxicos = []
nuvens_miasma = []
areas_miasma = []
feedbacks_bloqueio = []

TIPO_INIMIGO_BASE = "base"
TIPO_INIMIGO_DEVOTO_FEBRIL = "devoto_febril"
TIPO_INIMIGO_INCENSARIO = "incensario"
TIPO_INIMIGO_GUARDIAO_SUCATA = "guardiao_sucata"
MAX_DEVOTOS_FEBRIS = 3
MAX_INCENSARIOS = 2
MAX_GUARDIOES_SUCATA = 2
DURACAO_RASTRO_TOXICO = 2500
DURACAO_NUVEM_MIASMA = 2000
DURACAO_AREA_MIASMA = 3200
INTERVALO_RASTRO_DEVOTO = 260
INTERVALO_DANO_TOXICO = 650
PREPARACAO_ATAQUE_INCENSARIO = 550
COOLDOWN_ATAQUE_INCENSARIO = 2600

tempo_ultima_criacao_gelo = pygame.time.get_ticks()



def criar_disparo_inimigo(pos_inimigo, pos_personagem):
    dx = pos_personagem[0] - pos_inimigo[0]
    dy = pos_personagem[1] - pos_inimigo[1]
    dist = max(1, math.sqrt(dx ** 2 + dy ** 2))

    
    velocidade_disparo_inimigo = 1.6  
    direcao_disparo_inimigo = (dx / dist * velocidade_disparo_inimigo, dy / dist * velocidade_disparo_inimigo)

    return {"rect": pygame.Rect(pos_inimigo[0], pos_inimigo[1], largura_disparo, altura_disparo), "velocidade": direcao_disparo_inimigo}


def aplicar_atributos_tipo(inimigo):
    tipo = inimigo.get("tipo", TIPO_INIMIGO_BASE)

    inimigo.setdefault("escala", 1.0)
    inimigo.setdefault("velocidade_x", 1.70)
    inimigo.setdefault("velocidade_y", 1.50)
    inimigo.setdefault("dano_multiplicador", 1.0)

    if tipo == TIPO_INIMIGO_DEVOTO_FEBRIL:
        inimigo["escala"] = 0.85
        inimigo["vida_maxima"] = max(1, vida_inimigo_maxima * 0.60)
        inimigo["vida"] = inimigo["vida_maxima"]
        inimigo["velocidade_x"] = 1.70 * 1.35
        inimigo["velocidade_y"] = 1.50 * 1.35
        inimigo["dano_multiplicador"] = 0.90
        inimigo["cor_efeito"] = (70, 255, 90)
        inimigo["ultimo_rastro_toxico"] = 0
        inimigo["posicoes_recentes"] = []

    elif tipo == TIPO_INIMIGO_INCENSARIO:
        inimigo["escala"] = 1.0
        inimigo["vida_maxima"] = max(1, vida_inimigo_maxima * 0.90)
        inimigo["vida"] = inimigo["vida_maxima"]
        inimigo["velocidade_x"] = 1.70 * 0.72
        inimigo["velocidade_y"] = 1.50 * 0.72
        inimigo["dano_multiplicador"] = 0.75
        inimigo["cor_efeito"] = (155, 80, 225)
        inimigo["estado"] = "movendo"
        inimigo["tempo_inicio_preparo"] = 0
        inimigo["tempo_ultimo_ataque"] = pygame.time.get_ticks() + random.randint(400, 1200)
        inimigo["cooldown_ataque"] = random.randint(2200, 3000)
        inimigo["alvo_miasma"] = None
        inimigo["direcao_lateral"] = random.choice([-1, 1])

    elif tipo == TIPO_INIMIGO_GUARDIAO_SUCATA:
        inimigo["escala"] = 1.35
        inimigo["vida_maxima"] = max(1, vida_inimigo_maxima * 2.75)
        inimigo["vida"] = inimigo["vida_maxima"]
        inimigo["velocidade_x"] = 1.70 * 0.52
        inimigo["velocidade_y"] = 1.50 * 0.52
        inimigo["dano_multiplicador"] = 1.35
        inimigo["cor_efeito"] = (145, 135, 120)
        inimigo["direcao_frente"] = 1
        inimigo["estado"] = "movendo"

    largura = max(1, int(largura_inimigo3 * inimigo["escala"]))
    altura = max(1, int(altura_inimigo3 * inimigo["escala"]))
    centro = inimigo["rect"].center
    inimigo["rect"].size = (largura, altura)
    inimigo["rect"].center = centro
    return inimigo


def criar_inimigo(x=0, y=0, tipo=TIPO_INIMIGO_BASE):
    image = frames_inimigo_esquerda3[0]
    inimigo = {
        "rect": pygame.Rect(x, y, largura_inimigo3, altura_inimigo3),
        "image": image,
        "vida": vida_inimigo_maxima,
        "vida_maxima": vida_inimigo_maxima,
        "tipo": tipo
    }
    return aplicar_atributos_tipo(inimigo)


def escolher_tipo_inimigo():
    devotos_ativos = sum(1 for inimigo in inimigos_comum if inimigo.get("tipo") == TIPO_INIMIGO_DEVOTO_FEBRIL)
    incensarios_ativos = sum(1 for inimigo in inimigos_comum if inimigo.get("tipo") == TIPO_INIMIGO_INCENSARIO)
    guardioes_ativos = sum(1 for inimigo in inimigos_comum if inimigo.get("tipo") == TIPO_INIMIGO_GUARDIAO_SUCATA)

    rolagem = random.random()
    if guardioes_ativos < MAX_GUARDIOES_SUCATA and rolagem <= 0.06:
        return TIPO_INIMIGO_GUARDIAO_SUCATA
    if incensarios_ativos < MAX_INCENSARIOS and rolagem <= 0.15:
        return TIPO_INIMIGO_INCENSARIO
    if devotos_ativos < MAX_DEVOTOS_FEBRIS and rolagem <= 0.33:
        return TIPO_INIMIGO_DEVOTO_FEBRIL
    return TIPO_INIMIGO_BASE


def criar_nuvem_miasma(x, y):
    nuvens_miasma.append({
        "x": x,
        "y": y,
        "raio": 52,
        "tempo_inicio": pygame.time.get_ticks(),
        "ultimo_tick_dano": 0,
        "particulas": [
            {
                "dx": random.uniform(-28, 28),
                "dy": random.uniform(-22, 22),
                "raio": random.randint(3, 7),
                "vel": random.uniform(0.2, 0.7)
            }
            for _ in range(14)
        ]
    })


def registrar_morte_toxica(inimigo):
    if inimigo.get("tipo") == TIPO_INIMIGO_DEVOTO_FEBRIL:
        criar_nuvem_miasma(inimigo["rect"].centerx, inimigo["rect"].centery)


def registrar_rastro_toxico(inimigo, tempo_atual):
    if inimigo.get("tipo") != TIPO_INIMIGO_DEVOTO_FEBRIL:
        return

    centro = inimigo["rect"].center
    inimigo.setdefault("posicoes_recentes", []).append(centro)
    if len(inimigo["posicoes_recentes"]) > 8:
        inimigo["posicoes_recentes"].pop(0)

    if tempo_atual - inimigo.get("ultimo_rastro_toxico", 0) < INTERVALO_RASTRO_DEVOTO:
        return

    px, py = inimigo["posicoes_recentes"][0] if inimigo["posicoes_recentes"] else centro
    rastros_toxicos.append({
        "x": px,
        "y": py,
        "raio": random.randint(18, 26),
        "tempo_inicio": tempo_atual,
        "duracao": DURACAO_RASTRO_TOXICO,
        "ultimo_tick_dano": 0
    })
    inimigo["ultimo_rastro_toxico"] = tempo_atual


def aplicar_dano_toxico_no_personagem(efeito, personagem_rect, tempo_atual, dano_base):
    global vida, piscando_vida, tempo_ultimo_hit_inimigo, imune_tempo_restante

    if tempo_atual - efeito.get("ultimo_tick_dano", 0) < INTERVALO_DANO_TOXICO:
        return
    if imune_tempo_restante > 0:
        return

    if math.hypot(personagem_rect.centerx - efeito["x"], personagem_rect.centery - efeito["y"]) <= efeito["raio"]:
        vida -= dano_base
        efeito["ultimo_tick_dano"] = tempo_atual
        tempo_ultimo_hit_inimigo = tempo_atual
        piscando_vida = True


def atualizar_rastros_toxicos(personagem_rect, tempo_atual):
    rastros_ativos = []
    dano_base = max(1, int(vida_maxima * 0.012))

    for rastro in rastros_toxicos:
        if tempo_atual - rastro["tempo_inicio"] <= rastro["duracao"]:
            aplicar_dano_toxico_no_personagem(rastro, personagem_rect, tempo_atual, dano_base)
            rastros_ativos.append(rastro)

    rastros_toxicos[:] = rastros_ativos


def desenhar_rastros_toxicos(tela, tempo_atual):
    for rastro in rastros_toxicos:
        progresso = (tempo_atual - rastro["tempo_inicio"]) / rastro["duracao"]
        alpha = max(0, int(105 * (1 - progresso)))
        diametro = rastro["raio"] * 2
        superficie = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
        pygame.draw.circle(superficie, (45, 220, 75, alpha), (rastro["raio"], rastro["raio"]), rastro["raio"])
        pygame.draw.circle(superficie, (140, 255, 120, alpha // 2), (rastro["raio"], rastro["raio"]), max(4, rastro["raio"] // 2))
        tela.blit(superficie, (rastro["x"] - rastro["raio"], rastro["y"] - rastro["raio"]))


def atualizar_nuvens_miasma(personagem_rect, tempo_atual):
    nuvens_ativas = []
    dano_base = max(1, int(vida_maxima * 0.018))

    for nuvem in nuvens_miasma:
        if tempo_atual - nuvem["tempo_inicio"] <= DURACAO_NUVEM_MIASMA:
            aplicar_dano_toxico_no_personagem(nuvem, personagem_rect, tempo_atual, dano_base)
            nuvens_ativas.append(nuvem)

    nuvens_miasma[:] = nuvens_ativas


def desenhar_nuvens_miasma(tela, tempo_atual):
    for nuvem in nuvens_miasma:
        progresso = (tempo_atual - nuvem["tempo_inicio"]) / DURACAO_NUVEM_MIASMA
        raio = int(nuvem["raio"] * (0.75 + progresso * 0.35))
        alpha = max(0, int(135 * (1 - progresso)))
        superficie = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        pygame.draw.circle(superficie, (38, 210, 78, alpha), (raio, raio), raio)
        pygame.draw.circle(superficie, (170, 255, 135, alpha // 2), (raio, raio), max(5, raio // 3))

        for particula in nuvem.get("particulas", []):
            px = int(raio + particula["dx"] * (1 + progresso * particula["vel"]))
            py = int(raio + particula["dy"] * (1 + progresso * particula["vel"]))
            pygame.draw.circle(superficie, (100, 255, 120, alpha), (px, py), particula["raio"])

        tela.blit(superficie, (nuvem["x"] - raio, nuvem["y"] - raio))


def criar_area_miasma(x, y, raio=64, duracao=DURACAO_AREA_MIASMA):
    areas_miasma.append({
        "x": max(0, min(largura_mapa, x)),
        "y": max(0, min(altura_mapa, y)),
        "raio": raio,
        "duracao": duracao,
        "tempo_inicio": pygame.time.get_ticks(),
        "ultimo_tick_dano": 0,
        "particulas": [
            {
                "dx": random.uniform(-raio * 0.55, raio * 0.55),
                "dy": random.uniform(-raio * 0.45, raio * 0.45),
                "raio": random.randint(3, 8),
                "fase": random.uniform(0, math.pi * 2)
            }
            for _ in range(18)
        ]
    })


def atualizar_areas_miasma(personagem_rect, tempo_atual):
    areas_ativas = []
    dano_base = max(1, int(vida_maxima * 0.015))

    for area in areas_miasma:
        if tempo_atual - area["tempo_inicio"] <= area["duracao"]:
            aplicar_dano_toxico_no_personagem(area, personagem_rect, tempo_atual, dano_base)
            areas_ativas.append(area)

    areas_miasma[:] = areas_ativas


def desenhar_areas_miasma(tela, tempo_atual):
    for area in areas_miasma:
        progresso = (tempo_atual - area["tempo_inicio"]) / area["duracao"]
        alpha = max(0, int(125 * (1 - progresso)))
        raio = area["raio"]
        superficie = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        pygame.draw.circle(superficie, (86, 42, 140, alpha), (raio, raio), raio)
        pygame.draw.circle(superficie, (58, 210, 94, alpha // 2), (raio, raio), max(6, int(raio * 0.68)))
        pygame.draw.circle(superficie, (178, 112, 235, max(0, alpha - 35)), (raio, raio), raio, 2)

        for particula in area.get("particulas", []):
            ondulacao = math.sin(tempo_atual * 0.004 + particula["fase"]) * 5
            px = int(raio + particula["dx"] + ondulacao)
            py = int(raio + particula["dy"] - progresso * 18)
            pygame.draw.circle(superficie, (150, 245, 125, alpha), (px, py), particula["raio"])

        tela.blit(superficie, (area["x"] - raio, area["y"] - raio))


def desenhar_feedback_bloqueio(x, y):
    feedbacks_bloqueio.append({
        "x": x,
        "y": y,
        "tempo_inicio": pygame.time.get_ticks(),
        "particulas": [
            {
                "dx": random.uniform(-22, 22),
                "dy": random.uniform(-18, 18),
                "raio": random.randint(2, 4)
            }
            for _ in range(8)
        ]
    })


def atualizar_e_desenhar_feedbacks_bloqueio(tela, tempo_atual):
    ativos = []

    for feedback in feedbacks_bloqueio:
        idade = tempo_atual - feedback["tempo_inicio"]
        if idade > 320:
            continue

        progresso = idade / 320
        alpha = max(0, int(220 * (1 - progresso)))
        for particula in feedback.get("particulas", []):
            px = int(feedback["x"] + particula["dx"] * progresso)
            py = int(feedback["y"] + particula["dy"] * progresso)
            pygame.draw.circle(tela, (230, 225, 180, alpha), (px, py), particula["raio"])
            pygame.draw.line(tela, (180, 180, 165, alpha), (feedback["x"], feedback["y"]), (px, py), 1)
        ativos.append(feedback)

    feedbacks_bloqueio[:] = ativos


def ataque_veio_pela_frente(inimigo, origem_ataque):
    frente_x = inimigo.get("direcao_frente", 1)
    vetor_ataque_x = origem_ataque[0] - inimigo["rect"].centerx
    vetor_ataque_y = origem_ataque[1] - inimigo["rect"].centery
    distancia = max(1.0, math.hypot(vetor_ataque_x, vetor_ataque_y))
    alinhamento_frontal = (vetor_ataque_x / distancia) * frente_x
    return alinhamento_frontal > 0.55


def calcular_dano_com_escudo(inimigo, dano, origem_ataque):
    if inimigo.get("tipo") != TIPO_INIMIGO_GUARDIAO_SUCATA:
        return dano, False, False

    frente_x = inimigo.get("direcao_frente", 1)
    vetor_ataque_x = origem_ataque[0] - inimigo["rect"].centerx
    vetor_ataque_y = origem_ataque[1] - inimigo["rect"].centery
    distancia = max(1.0, math.hypot(vetor_ataque_x, vetor_ataque_y))
    alinhamento = (vetor_ataque_x / distancia) * frente_x

    if alinhamento > 0.55:
        return dano * 0.25, True, False
    if alinhamento < -0.45:
        return dano * 1.12, False, True
    return dano, False, False


def atualizar_guardiao_sucata(inimigo, jogador, fator_tempo_mundo):
    jogador_x, jogador_y, jogador_largura, jogador_altura = jogador
    alvo_x = jogador_x + jogador_largura // 2
    alvo_y = jogador_y + jogador_altura // 2
    dx = alvo_x - inimigo["rect"].centerx
    dy = alvo_y - inimigo["rect"].centery
    distancia = max(1.0, math.hypot(dx, dy))

    inimigo["direcao_frente"] = 1 if dx >= 0 else -1
    inimigo["estado"] = "movendo"
    intensidade = 0.55 if distancia < 95 else 1.0
    inimigo["pos_x"] += (dx / distancia) * inimigo.get("velocidade_x", 0.88) * intensidade * fator_tempo_mundo
    inimigo["pos_y"] += (dy / distancia) * inimigo.get("velocidade_y", 0.78) * intensidade * fator_tempo_mundo
    inimigo["pos_x"] = max(0, min(largura_mapa - inimigo["rect"].width, inimigo["pos_x"]))
    inimigo["pos_y"] = max(0, min(altura_mapa - inimigo["rect"].height, inimigo["pos_y"]))
    inimigo["rect"].x = int(inimigo["pos_x"])
    inimigo["rect"].y = int(inimigo["pos_y"])


def atualizar_incensario(inimigo, jogador, tempo_atual, fator_tempo_mundo):
    jogador_x, jogador_y, jogador_largura, jogador_altura = jogador
    alvo_x = jogador_x + jogador_largura // 2
    alvo_y = jogador_y + jogador_altura // 2
    centro_x = inimigo["rect"].centerx
    centro_y = inimigo["rect"].centery
    dx = alvo_x - centro_x
    dy = alvo_y - centro_y
    distancia = max(1.0, math.hypot(dx, dy))

    if tempo_atual - inimigo.get("tempo_troca_lateral", 0) > 1400:
        inimigo["direcao_lateral"] = random.choice([-1, 1])
        inimigo["tempo_troca_lateral"] = tempo_atual

    estado = inimigo.get("estado", "movendo")
    if estado == "preparando_ataque":
        if tempo_atual - inimigo.get("tempo_inicio_preparo", 0) >= PREPARACAO_ATAQUE_INCENSARIO:
            alvo = inimigo.get("alvo_miasma")
            if alvo:
                criar_area_miasma(alvo[0], alvo[1], random.randint(58, 72), random.randint(2800, 3500))
            inimigo["estado"] = "atacando"
            inimigo["tempo_estado"] = tempo_atual
            inimigo["tempo_ultimo_ataque"] = tempo_atual
            inimigo["cooldown_ataque"] = random.randint(2200, 3000)
            inimigo["alvo_miasma"] = None
        elif distancia < 190:
            inimigo["pos_x"] -= (dx / distancia) * inimigo.get("velocidade_x", 1.20) * 0.75 * fator_tempo_mundo
            inimigo["pos_y"] -= (dy / distancia) * inimigo.get("velocidade_y", 1.05) * 0.75 * fator_tempo_mundo
        inimigo["pos_x"] = max(0, min(largura_mapa - inimigo["rect"].width, inimigo["pos_x"]))
        inimigo["pos_y"] = max(0, min(altura_mapa - inimigo["rect"].height, inimigo["pos_y"]))
        inimigo["rect"].x = int(inimigo["pos_x"])
        inimigo["rect"].y = int(inimigo["pos_y"])
        return

    if estado == "atacando":
        if tempo_atual - inimigo.get("tempo_estado", 0) > 180:
            inimigo["estado"] = "movendo"
        else:
            inimigo["rect"].x = int(inimigo["pos_x"])
            inimigo["rect"].y = int(inimigo["pos_y"])
            return

    pode_atacar = (
        tempo_atual - inimigo.get("tempo_ultimo_ataque", 0) >= inimigo.get("cooldown_ataque", COOLDOWN_ATAQUE_INCENSARIO)
        and distancia <= 560
    )
    if pode_atacar:
        inimigo["estado"] = "preparando_ataque"
        inimigo["tempo_inicio_preparo"] = tempo_atual
        inimigo["alvo_miasma"] = (max(25, min(largura_mapa - 25, alvo_x)), max(25, min(altura_mapa - 25, alvo_y)))
        inimigo["rect"].x = int(inimigo["pos_x"])
        inimigo["rect"].y = int(inimigo["pos_y"])
        return

    perto_demais = 220
    longe_demais = 430
    if distancia < perto_demais:
        inimigo["estado"] = "recuando"
        mov_x = -dx / distancia
        mov_y = -dy / distancia
        intensidade = 1.20
    elif distancia > longe_demais:
        inimigo["estado"] = "movendo"
        mov_x = dx / distancia
        mov_y = dy / distancia
        intensidade = 0.82
    else:
        inimigo["estado"] = "movendo"
        lateral = inimigo.get("direcao_lateral", 1)
        mov_x = (-dy / distancia) * lateral
        mov_y = (dx / distancia) * lateral
        intensidade = 0.42

    inimigo["pos_x"] += mov_x * inimigo.get("velocidade_x", 1.20) * intensidade * fator_tempo_mundo
    inimigo["pos_y"] += mov_y * inimigo.get("velocidade_y", 1.05) * intensidade * fator_tempo_mundo
    inimigo["pos_x"] = max(0, min(largura_mapa - inimigo["rect"].width, inimigo["pos_x"]))
    inimigo["pos_y"] = max(0, min(altura_mapa - inimigo["rect"].height, inimigo["pos_y"]))
    inimigo["rect"].x = int(inimigo["pos_x"])
    inimigo["rect"].y = int(inimigo["pos_y"])


def desenhar_efeitos_incensario(tela, inimigo, tempo_atual, pos_x, pos_y, largura, altura):
    preparando = inimigo.get("estado") == "preparando_ataque"
    pulso = (math.sin(tempo_atual * 0.012) + 1) / 2
    aura_alpha = int(50 + pulso * 35 + (55 if preparando else 0))
    aura_raio_extra = 14 + (10 if preparando else 0)
    aura = pygame.Surface((largura + aura_raio_extra * 2, altura + aura_raio_extra * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(aura, (110, 65, 180, aura_alpha), (0, 0, largura + aura_raio_extra * 2, altura + aura_raio_extra * 2))
    pygame.draw.ellipse(aura, (80, 220, 110, aura_alpha // 2), (8, 8, largura + aura_raio_extra * 2 - 16, altura + aura_raio_extra * 2 - 16))
    tela.blit(aura, (pos_x - aura_raio_extra, pos_y - aura_raio_extra))

    origem_fumaca_x = pos_x + largura // 2
    origem_fumaca_y = pos_y + max(6, altura // 4)
    quantidade = 7 if preparando else 4
    for i in range(quantidade):
        oscilacao = math.sin(tempo_atual * 0.005 + i) * 7
        px = int(origem_fumaca_x + oscilacao + random.randint(-2, 2))
        py = int(origem_fumaca_y - i * 5 - random.randint(0, 4))
        raio = random.randint(3, 7) + (2 if preparando else 0)
        cor = (145, 80, 210, 95) if i % 2 == 0 else (80, 230, 120, 85)
        pygame.draw.circle(tela, cor, (px, py), raio)

    alvo = inimigo.get("alvo_miasma")
    if preparando and alvo:
        progresso = min(1.0, (tempo_atual - inimigo.get("tempo_inicio_preparo", 0)) / PREPARACAO_ATAQUE_INCENSARIO)
        raio = int(38 + progresso * 28)
        aviso = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        pygame.draw.circle(aviso, (130, 55, 205, 75), (raio, raio), raio)
        pygame.draw.circle(aviso, (110, 255, 120, 120), (raio, raio), max(4, int(raio * progresso)), 3)
        pygame.draw.circle(aviso, (230, 205, 255, 170), (raio, raio), raio, 2)
        tela.blit(aviso, (alvo[0] - raio, alvo[1] - raio))


def desenhar_armadura_guardiao(tela, inimigo, pos_x, pos_y, largura, altura):
    aura = pygame.Surface((largura + 20, altura + 20), pygame.SRCALPHA)
    pygame.draw.ellipse(aura, (95, 85, 70, 58), (0, 0, largura + 20, altura + 20))
    tela.blit(aura, (pos_x - 10, pos_y - 10))

    peito = pygame.Rect(pos_x + int(largura * 0.28), pos_y + int(altura * 0.30), int(largura * 0.44), int(altura * 0.28))
    pygame.draw.rect(tela, (92, 92, 88), peito, border_radius=3)
    pygame.draw.rect(tela, (155, 150, 135), peito, 2, border_radius=3)
    pygame.draw.line(tela, (55, 55, 52), peito.midleft, peito.midright, 2)

    frente_x = inimigo.get("direcao_frente", 1)
    if frente_x >= 0:
        escudo = pygame.Rect(pos_x + int(largura * 0.58), pos_y + int(altura * 0.22), int(largura * 0.25), int(altura * 0.46))
    else:
        escudo = pygame.Rect(pos_x + int(largura * 0.17), pos_y + int(altura * 0.22), int(largura * 0.25), int(altura * 0.46))

    pygame.draw.rect(tela, (75, 78, 80), escudo, border_radius=5)
    pygame.draw.rect(tela, (178, 174, 155), escudo, 2, border_radius=5)
    pygame.draw.line(tela, (48, 50, 52), (escudo.centerx, escudo.top + 4), (escudo.centerx, escudo.bottom - 4), 2)

    for px, py in (
        (peito.left + 5, peito.top + 5),
        (peito.right - 5, peito.top + 5),
        (peito.left + 5, peito.bottom - 5),
        (peito.right - 5, peito.bottom - 5),
        (escudo.left + 5, escudo.top + 7),
        (escudo.right - 5, escudo.bottom - 7),
    ):
        pygame.draw.circle(tela, (205, 200, 178), (px, py), 2)

    cano_y = pos_y + int(altura * 0.68)
    pygame.draw.line(tela, (105, 105, 100), (pos_x + int(largura * 0.20), cano_y), (pos_x + int(largura * 0.80), cano_y + 4), 4)
    pygame.draw.line(tela, (55, 55, 52), (pos_x + int(largura * 0.20), cano_y), (pos_x + int(largura * 0.80), cano_y + 4), 1)


def desenhar_inimigo(tela, inimigo):
    escala = inimigo.get("escala", 1.0)
    largura = max(1, int(largura_inimigo3 * escala))
    altura = max(1, int(altura_inimigo3 * escala))
    pos_x = inimigo["rect"].x
    pos_y = inimigo["rect"].y

    if inimigo.get("tipo") == TIPO_INIMIGO_GUARDIAO_SUCATA:
        imagem = pygame.transform.smoothscale(inimigo["image"], (largura, altura))
        tint = pygame.Surface((largura, altura), pygame.SRCALPHA)
        tint.fill((55, 48, 38, 35))
        imagem = imagem.copy()
        imagem.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        tela.blit(imagem, (pos_x, pos_y))
        desenhar_armadura_guardiao(tela, inimigo, pos_x, pos_y, largura, altura)

    elif inimigo.get("tipo") == TIPO_INIMIGO_INCENSARIO:
        desenhar_efeitos_incensario(tela, inimigo, pygame.time.get_ticks(), pos_x, pos_y, largura, altura)
        imagem = pygame.transform.smoothscale(inimigo["image"], (largura, altura))
        tint = pygame.Surface((largura, altura), pygame.SRCALPHA)
        tint.fill((70, 35, 115, 55))
        imagem = imagem.copy()
        imagem.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        tela.blit(imagem, (pos_x, pos_y))

    elif inimigo.get("tipo") == TIPO_INIMIGO_DEVOTO_FEBRIL:
        tremor_x = random.randint(-2, 2)
        tremor_y = random.randint(-2, 2)
        pos_x += tremor_x
        pos_y += tremor_y

        aura = pygame.Surface((largura + 18, altura + 18), pygame.SRCALPHA)
        pygame.draw.ellipse(aura, (45, 230, 85, 70), (0, 0, largura + 18, altura + 18))
        pygame.draw.ellipse(aura, (145, 255, 130, 45), (5, 5, largura + 8, altura + 8))
        tela.blit(aura, (pos_x - 9, pos_y - 9))

        for _ in range(3):
            px = pos_x + random.randint(2, largura)
            py = pos_y + altura - random.randint(2, max(3, altura // 3))
            pygame.draw.circle(tela, (90, 255, 105), (px, py), random.randint(2, 4))

        imagem = pygame.transform.smoothscale(inimigo["image"], (largura, altura))
        tint = pygame.Surface((largura, altura), pygame.SRCALPHA)
        tint.fill((30, 150, 45, 70))
        imagem = imagem.copy()
        imagem.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        tela.blit(imagem, (pos_x, pos_y))
    else:
        tela.blit(inimigo["image"], inimigo["rect"])


def atualizar_fe_pai_rato(delta):
    global fe_pai_rato
    fe_pai_rato = max(0, min(100, fe_pai_rato + delta))


def sortear_fala_pai_rato(falas):
    global ultima_fala_pai_rato
    if not falas:
        return ""
    opcoes = [fala for fala in falas if fala != ultima_fala_pai_rato]
    fala = random.choice(opcoes or falas)
    ultima_fala_pai_rato = fala
    return fala


def registrar_fala_pai_rato(categoria, tempo_atual, forcar=False):
    global tempo_proxima_fala_pai_rato, pai_rato_fala_entrada_feita

    if categoria == "entrada":
        if pai_rato_fala_entrada_feita and not forcar:
            return
        falas = FALAS_PAI_RATO_ENTRADA
        cor = (255, 235, 150)
        pai_rato_fala_entrada_feita = True
    elif categoria == "queijo":
        falas = FALAS_PAI_RATO_QUEIJO
        cor = (255, 222, 80)
    elif categoria == "queijo_destruido":
        falas = FALAS_PAI_RATO_QUEIJO_DESTRUIDO
        cor = (255, 95, 95)
    elif categoria == "final":
        falas = FALAS_PAI_RATO_FINAL
        cor = (255, 70, 110)
    else:
        falas = FALAS_PAI_RATO_FINAL if fase_pai_rato >= 3 and random.random() < 0.65 else FALAS_PAI_RATO_ATAQUE
        cor = (210, 255, 170) if falas is FALAS_PAI_RATO_ATAQUE else (255, 70, 110)

    if not forcar and categoria not in ("entrada",) and tempo_atual < tempo_proxima_fala_pai_rato:
        return

    fala = sortear_fala_pai_rato(falas)
    if not fala:
        return

    fonte_temp = pygame.font.Font(None, 23)
    largura_max = min(520, largura_mapa - 80)
    palavras = fala.split()
    linhas = []
    linha_atual = ""
    for palavra in palavras:
        teste = palavra if not linha_atual else f"{linha_atual} {palavra}"
        if fonte_temp.size(teste)[0] <= largura_max:
            linha_atual = teste
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra
    if linha_atual:
        linhas.append(linha_atual)

    x_fala = int(max(20, min(largura_mapa - largura_max - 20, pos_x_chefe3 - 110)))
    y_fala = int(max(58, pos_y_chefe3 - 72))
    efeitos_texto.append({
        "texto": fala,
        "linhas": linhas,
        "x": x_fala,
        "y": y_fala,
        "tempo_inicio": tempo_atual,
        "cor": cor,
        "duracao": 2600 if categoria != "entrada" else 3200,
        "tamanho": 23,
        "fala_boss": True,
    })
    tempo_proxima_fala_pai_rato = tempo_atual + random.randint(8000, 12000)


def atualizar_fase_pai_rato(tempo_atual):
    global fase_pai_rato
    if vida_maxima_boss3 <= 0:
        return fase_pai_rato

    vida_pct = vida_boss3 / vida_maxima_boss3
    nova_fase = 1 if vida_pct > 0.70 else (2 if vida_pct > 0.35 else 3)
    if nova_fase != fase_pai_rato:
        fase_pai_rato = nova_fase
        nomes = {1: "PONTIFICE SERENO", 2: "FANATICO FERIDO", 3: "FE DESPEDACADA"}
        efeitos_texto.append({
            "texto": nomes.get(fase_pai_rato, "PAI-RATO"),
            "x": int(pos_x_chefe3),
            "y": int(pos_y_chefe3 - 34),
            "tempo_inicio": tempo_atual,
            "cor": (255, 220, 90) if fase_pai_rato < 3 else (255, 70, 95),
        })
    return fase_pai_rato


def escolher_padrao_frascos():
    margem = 45
    topo = margem
    meio = altura_mapa // 2 - altura_disparo // 2
    baixo = altura_mapa - altura_disparo - margem
    abertura = random.choice(["topo", "meio", "baixo", "diagonal_subindo", "diagonal_descendo"])
    ys = []

    if abertura == "topo":
        ys = [meio - 75, meio, meio + 75, baixo]
    elif abertura == "meio":
        ys = [topo, topo + 75, baixo - 75, baixo]
    elif abertura == "baixo":
        ys = [topo, topo + 80, meio - 40, meio + 40]
    elif abertura == "diagonal_subindo":
        ys = [baixo, meio + 45, meio - 45, topo]
    else:
        ys = [topo, meio - 45, meio + 45, baixo]

    return [max(0, min(altura_mapa - altura_disparo, int(y))) for y in ys], abertura


def desenhar_avisos_pai_rato(tela, tempo_atual):
    ativos = []
    for aviso in avisos_pai_rato:
        idade = tempo_atual - aviso["inicio"]
        duracao = aviso.get("duracao", 600)
        if idade > duracao:
            continue
        progresso = idade / max(1, duracao)
        alpha = int((1.0 - progresso) * 115 + 45)
        cor = aviso.get("cor", (255, 70, 90, alpha))
        if aviso["tipo"] == "frascos":
            for y_lane in aviso.get("ys", []):
                surf = pygame.Surface((largura_mapa, altura_disparo + 24), pygame.SRCALPHA)
                surf.fill((cor[0], cor[1], cor[2], min(120, alpha)))
                pygame.draw.line(surf, (255, 245, 210, min(210, alpha + 70)), (0, 12), (largura_mapa, 12), 2)
                tela.blit(surf, (0, y_lane - 12))
        elif aviso["tipo"] == "circulo":
            raio = int(aviso.get("raio", 80) * (0.85 + progresso * 0.25))
            surf = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (cor[0], cor[1], cor[2], min(130, alpha)), (raio, raio), raio, 3)
            pygame.draw.circle(surf, (80, 255, 120, min(80, alpha)), (raio, raio), max(4, int(raio * progresso)), 2)
            tela.blit(surf, (aviso["x"] - raio, aviso["y"] - raio))
        elif aviso["tipo"] == "linha":
            pygame.draw.line(tela, (cor[0], cor[1], cor[2], min(255, alpha + 60)), aviso["inicio_pos"], aviso["fim_pos"], aviso.get("largura", 6))
        ativos.append(aviso)
    avisos_pai_rato[:] = ativos


def disparar_chuva_frascos_padronizada(tempo_atual):
    global pai_rato_chuva_frascos, tempo_ultimo_chuva_pai_rato
    fase = atualizar_fase_pai_rato(tempo_atual)
    cooldown_base = {1: 4300, 2: 3600, 3: 3000}.get(fase, 4000)
    cooldown = max(2200, cooldown_base - int(fe_pai_rato * 9))
    if pai_rato_chuva_frascos or tempo_atual - tempo_ultimo_chuva_pai_rato < cooldown:
        return

    ys, padrao = escolher_padrao_frascos()
    pai_rato_chuva_frascos = {"inicio": tempo_atual, "ys": ys, "padrao": padrao, "executado": False}
    avisos_pai_rato.append({"tipo": "frascos", "inicio": tempo_atual, "duracao": 650, "ys": ys, "cor": (235, 65, 95)})
    tempo_ultimo_chuva_pai_rato = tempo_atual


def atualizar_chuva_frascos_pai_rato(tempo_atual):
    global pai_rato_chuva_frascos
    if not pai_rato_chuva_frascos:
        return
    if tempo_atual - pai_rato_chuva_frascos["inicio"] < 650:
        return

    if not pai_rato_chuva_frascos["executado"]:
        atraso = 0
        for y_lane in pai_rato_chuva_frascos["ys"]:
            disparos_boss3.append((largura_mapa + atraso, y_lane, "left"))
            atraso += 34
        pai_rato_chuva_frascos["executado"] = True
    pai_rato_chuva_frascos = None


def invocar_queijo_sagrado(x=None, y=None, tipo="verdadeiro", vida_base=None, duracao=12000, ritual=False, anunciar=True):
    vida_base = vida_base if vida_base is not None else 35 + int(fe_pai_rato * 0.25)
    if x is None:
        x = random.randint(area_x_min, area_x_max)
    if y is None:
        y = random.randint(area_y_min, area_y_max)
    queijo = {
        "x": int(max(20, min(largura_mapa - largura_queijo - 20, x))),
        "y": int(max(20, min(altura_mapa - altura_queijo - 20, y))),
        "vida": vida_base,
        "vida_maxima": vida_base,
        "tipo": tipo,
        "tempo_inicio": pygame.time.get_ticks(),
        "duracao": duracao,
        "consumo_inicio": None,
        "ritual": ritual,
        "destruido": False,
    }
    queijos_sagrados.append(queijo)
    if anunciar:
        registrar_fala_pai_rato("queijo", pygame.time.get_ticks(), True)
    return queijo


def invocar_auxiliares_pai_rato(quantidade):
    devotos_ativos = sum(1 for inimigo in inimigos_comum if inimigo.get("tipo") == TIPO_INIMIGO_DEVOTO_FEBRIL)
    limite = max(0, min(2, quantidade, MAX_DEVOTOS_FEBRIS - devotos_ativos))
    for _ in range(limite):
        sx = random.choice([0, largura_mapa - largura_inimigo3])
        sy = random.randint(80, max(90, altura_mapa - altura_inimigo3 - 80))
        tipo = TIPO_INIMIGO_DEVOTO_FEBRIL if devotos_ativos < MAX_DEVOTOS_FEBRIS else TIPO_INIMIGO_BASE
        inimigos_comum.append(criar_inimigo(sx, sy, tipo))


def desenhar_queijos_sagrados(tela, tempo_atual):
    for queijo in queijos_sagrados:
        idade = tempo_atual - queijo["tempo_inicio"]
        pulso = (math.sin(tempo_atual * 0.008 + queijo["x"]) + 1.0) * 0.5
        verdadeiro = queijo["tipo"] == "verdadeiro"
        alpha = int((105 if verdadeiro else 65) + pulso * (85 if verdadeiro else 45))
        cor = (255, 210, 60, alpha) if verdadeiro else (130, 255, 95, alpha)
        raio = int(34 + pulso * (9 if verdadeiro else 5))
        surf = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, cor, (raio, raio), raio)
        pygame.draw.circle(surf, (255, 255, 220, min(230, alpha + 40)), (raio, raio), raio, 2)
        if not verdadeiro:
            pygame.draw.line(surf, (80, 210, 110, 160), (raio - 12, raio + 13), (raio + 14, raio - 9), 2)
        tela.blit(surf, (queijo["x"] + largura_queijo // 2 - raio, queijo["y"] + altura_queijo // 2 - raio))
        tela.blit(sprite_queijo, (queijo["x"], queijo["y"]))

        largura_barra = max(24, largura_queijo)
        pygame.draw.rect(tela, (42, 18, 10), (queijo["x"], queijo["y"] - 8, largura_barra, 5))
        pygame.draw.rect(tela, (255, 220, 80) if verdadeiro else (80, 220, 110), (queijo["x"], queijo["y"] - 8, int(largura_barra * queijo["vida"] / max(1, queijo["vida_maxima"])), 5))
        if queijo.get("consumo_inicio"):
            consumo = min(1.0, (tempo_atual - queijo["consumo_inicio"]) / 1000)
            pygame.draw.circle(tela, (255, 245, 180), (queijo["x"] + largura_queijo // 2, queijo["y"] - 18), int(8 + consumo * 14), 2)
        elif idade > queijo["duracao"] - 2200:
            pygame.draw.circle(tela, (255, 70, 70), (queijo["x"] + largura_queijo // 2, queijo["y"] + altura_queijo // 2), 24, 2)


def atualizar_queijos_sagrados(tempo_atual):
    global vida_boss3, pos_x_chefe3, pos_y_chefe3, pai_rato_consumindo
    if not queijos_sagrados:
        pai_rato_consumindo = None
        return

    for disparo in disparos[:]:
        rect_disparo = disparo["rect"]
        for queijo in queijos_sagrados[:]:
            rect_queijo = pygame.Rect(queijo["x"] - 12, queijo["y"] - 12, largura_hitbox_queijo, altura_hitbox_queijo)
            if rect_disparo.colliderect(rect_queijo):
                queijo["vida"] -= max(5, int(dano_person_hit * 0.18))
                estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)
                if queijo["vida"] <= 0:
                    destruir_queijo_sagrado(queijo, tempo_atual)
                break

    verdadeiro = next((q for q in queijos_sagrados if q["tipo"] == "verdadeiro"), None)
    if verdadeiro and tempo_atual > pai_rato_atordoado_ate:
        dx = verdadeiro["x"] - pos_x_chefe3
        dy = verdadeiro["y"] - pos_y_chefe3
        dist = max(1.0, math.hypot(dx, dy))
        velocidade = (0.85 + fase_pai_rato * 0.18 + fe_pai_rato * 0.004) * dt
        pos_x_chefe3 += (dx / dist) * velocidade
        pos_y_chefe3 += (dy / dist) * velocidade
        if dist <= 36:
            verdadeiro["consumo_inicio"] = verdadeiro.get("consumo_inicio") or tempo_atual
            pai_rato_consumindo = verdadeiro
            if tempo_atual - verdadeiro["consumo_inicio"] >= random.randint(850, 1150):
                cura = int((vida_maxima_boss3 - vida_boss3) * (0.22 + fe_pai_rato * 0.0015))
                vida_boss3 = min(vida_maxima_boss3, vida_boss3 + max(1, cura))
                atualizar_fe_pai_rato(20)
                if verdadeiro in queijos_sagrados:
                    queijos_sagrados.remove(verdadeiro)
                pai_rato_consumindo = None
                pos_x_chefe3 = largura_tela / 1.3
                pos_y_chefe3 = altura_tela / 3

    for queijo in queijos_sagrados[:]:
        if tempo_atual - queijo["tempo_inicio"] > queijo["duracao"]:
            if queijo["tipo"] == "falso":
                criar_area_miasma(queijo["x"] + largura_queijo // 2, queijo["y"] + altura_queijo // 2, 78, 2600)
            queijos_sagrados.remove(queijo)


def destruir_queijo_sagrado(queijo, tempo_atual):
    global pai_rato_consumindo
    if queijo not in queijos_sagrados:
        return
    if queijo["tipo"] == "verdadeiro":
        atualizar_fe_pai_rato(-15)
    else:
        criar_area_miasma(queijo["x"] + largura_queijo // 2, queijo["y"] + altura_queijo // 2, 82, 3000)
    registrar_fala_pai_rato("queijo_destruido", tempo_atual, True)
    if pai_rato_ritual and pai_rato_ritual.get("ativo") and queijo.get("ritual"):
        pai_rato_ritual["destruidos"] += 1
    if pai_rato_consumindo is queijo:
        pai_rato_consumindo = None
    queijos_sagrados.remove(queijo)


def iniciar_ritual_ultimo_queijo(tempo_atual):
    global pai_rato_ritual
    pai_rato_ritual = {"ativo": True, "inicio": tempo_atual, "duracao": 8500, "destruidos": 0, "resolvido": False}
    posicoes = [
        (largura_mapa * 0.22, altura_mapa * 0.25),
        (largura_mapa * 0.50, altura_mapa * 0.70),
        (largura_mapa * 0.78, altura_mapa * 0.32),
    ]
    for indice, (px, py) in enumerate(posicoes):
        invocar_queijo_sagrado(px, py, "verdadeiro", 42 + int(fe_pai_rato * 0.2), 9000, True, indice == 0)
    efeitos_texto.append({"texto": "RITUAL DO ULTIMO QUEIJO", "x": int(pos_x_chefe3 - 60), "y": int(pos_y_chefe3 - 52), "tempo_inicio": tempo_atual, "cor": (255, 80, 120)})


def atualizar_ritual_ultimo_queijo(tempo_atual, tela):
    global pai_rato_ritual, vida_boss3, pai_rato_atordoado_ate
    if not pai_rato_ritual or not pai_rato_ritual.get("ativo"):
        return

    restantes = [q for q in queijos_sagrados if q.get("ritual")]
    sucesso = pai_rato_ritual.get("destruidos", 0) >= 2
    expirou = tempo_atual - pai_rato_ritual["inicio"] >= pai_rato_ritual["duracao"]
    if not sucesso and not expirou:
        faltam = max(0, 2 - pai_rato_ritual.get("destruidos", 0))
        texto = fonte.render(f"Destrua {faltam} queijo(s) sagrado(s)", True, (255, 230, 120))
        tela.blit(texto, (largura_mapa // 2 - texto.get_width() // 2, 96))
        return

    if sucesso:
        atualizar_fe_pai_rato(-30)
        pai_rato_atordoado_ate = tempo_atual + 3200
        efeitos_texto.append({"texto": "FE QUEBRADA! VULNERAVEL", "x": int(pos_x_chefe3 - 35), "y": int(pos_y_chefe3 - 46), "tempo_inicio": tempo_atual, "cor": (100, 255, 210)})
    else:
        atualizar_fe_pai_rato(25)
        cura = int((vida_maxima_boss3 - vida_boss3) * 0.32)
        vida_boss3 = min(vida_maxima_boss3, vida_boss3 + max(1, cura))
        criar_area_miasma(pos_x_chefe3 + chefe_largura3 // 2, pos_y_chefe3 + chefe_altura3 // 2, 150, 3200)
        efeitos_texto.append({"texto": "A FE DEVORA A FERIDA", "x": int(pos_x_chefe3 - 35), "y": int(pos_y_chefe3 - 46), "tempo_inicio": tempo_atual, "cor": (255, 90, 90)})
    for queijo in restantes:
        if queijo in queijos_sagrados:
            queijos_sagrados.remove(queijo)
    pai_rato_ritual["ativo"] = False


def ataque_cauda_pai_rato(tempo_atual, personagem_rect):
    global pai_rato_cauda, tempo_ultimo_cauda_pai_rato, vida, piscando_vida, tempo_ultimo_hit_inimigo, pos_x_personagem, pos_y_personagem
    centro = (int(pos_x_chefe3 + chefe_largura3 // 2), int(pos_y_chefe3 + chefe_altura3 // 2))
    dist = math.hypot(personagem_rect.centerx - centro[0], personagem_rect.centery - centro[1])
    if pai_rato_cauda is None and fase_pai_rato >= 2 and dist < 145 and tempo_atual - tempo_ultimo_cauda_pai_rato > 3200:
        pai_rato_cauda = {"inicio": tempo_atual, "centro": centro, "raio": 155, "acertou": False}
        avisos_pai_rato.append({"tipo": "circulo", "inicio": tempo_atual, "duracao": 520, "x": centro[0], "y": centro[1], "raio": 155, "cor": (255, 75, 70)})
        tempo_ultimo_cauda_pai_rato = tempo_atual
    if not pai_rato_cauda:
        return
    if tempo_atual - pai_rato_cauda["inicio"] >= 520:
        if not pai_rato_cauda["acertou"] and imune_tempo_restante <= 0 and dist < pai_rato_cauda["raio"]:
            vida -= max(10, int(vida_maxima * 0.12))
            tempo_ultimo_hit_inimigo = tempo_atual
            piscando_vida = True
            dx = personagem_rect.centerx - centro[0]
            dy = personagem_rect.centery - centro[1]
            d = max(1.0, math.hypot(dx, dy))
            pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem + int((dx / d) * 42)))
            pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem + int((dy / d) * 42)))
        pai_rato_cauda = None


def iniciar_carga_cega_pai_rato(tempo_atual):
    global pai_rato_carga, tempo_ultimo_carga_pai_rato
    if fase_pai_rato < 3 or pai_rato_carga or tempo_atual - tempo_ultimo_carga_pai_rato < max(4200, 6800 - (50 - fe_pai_rato) * 45):
        return
    origem = (pos_x_chefe3 + chefe_largura3 // 2, pos_y_chefe3 + chefe_altura3 // 2)
    alvo = (pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2)
    dx = alvo[0] - origem[0]
    dy = alvo[1] - origem[1]
    dist = max(1.0, math.hypot(dx, dy))
    direcao = (dx / dist, dy / dist)
    fim = (int(origem[0] + direcao[0] * 650), int(origem[1] + direcao[1] * 650))
    pai_rato_carga = {"estado": "aviso", "inicio": tempo_atual, "dir": direcao, "acertou": False}
    avisos_pai_rato.append({"tipo": "linha", "inicio": tempo_atual, "duracao": 700, "inicio_pos": origem, "fim_pos": fim, "largura": 8, "cor": (255, 45, 70)})
    tempo_ultimo_carga_pai_rato = tempo_atual


def atualizar_carga_cega_pai_rato(tempo_atual, personagem_rect):
    global pai_rato_carga, pos_x_chefe3, pos_y_chefe3, vida, piscando_vida, tempo_ultimo_hit_inimigo, pai_rato_atordoado_ate
    if not pai_rato_carga:
        return
    idade = tempo_atual - pai_rato_carga["inicio"]
    if pai_rato_carga["estado"] == "aviso":
        if idade >= 700:
            pai_rato_carga["estado"] = "carga"
            pai_rato_carga["inicio"] = tempo_atual
        return

    dx, dy = pai_rato_carga["dir"]
    vel = 8.5 * dt
    pos_x_chefe3 += dx * vel
    pos_y_chefe3 += dy * vel
    rect_boss_carga = pygame.Rect(pos_x_chefe3, pos_y_chefe3, chefe_largura3, chefe_altura3)
    if not pai_rato_carga["acertou"] and rect_boss_carga.colliderect(personagem_rect) and imune_tempo_restante <= 0:
        vida -= max(15, int(vida_maxima * 0.16))
        tempo_ultimo_hit_inimigo = tempo_atual
        piscando_vida = True
        pai_rato_carga["acertou"] = True
    bateu_parede = pos_x_chefe3 < 8 or pos_x_chefe3 > largura_mapa - chefe_largura3 - 8 or pos_y_chefe3 < 8 or pos_y_chefe3 > altura_mapa - chefe_altura3 - 8
    if bateu_parede or tempo_atual - pai_rato_carga["inicio"] > 850:
        pos_x_chefe3 = max(0, min(largura_mapa - chefe_largura3, pos_x_chefe3))
        pos_y_chefe3 = max(0, min(altura_mapa - chefe_altura3, pos_y_chefe3))
        if bateu_parede:
            pai_rato_atordoado_ate = tempo_atual + 1700
        pai_rato_carga = None


def atualizar_cuspida_veneno_pai_rato(tempo_atual, personagem_rect, tela):
    global tempo_ultimo_cuspida_pai_rato, vida, piscando_vida, tempo_ultimo_hit_inimigo, personagem_doente, tempo_ultimo_atingido
    cooldown = {1: 4200, 2: 3400, 3: 3000}.get(fase_pai_rato, 3800)
    if tempo_atual - tempo_ultimo_cuspida_pai_rato >= cooldown and not queijos_sagrados:
        alvo = (pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2)
        origem = (pos_x_chefe3 + chefe_largura3 * 0.35, pos_y_chefe3 + chefe_altura3 * 0.45)
        dx = alvo[0] - origem[0]
        dy = alvo[1] - origem[1]
        dist = max(1.0, math.hypot(dx, dy))
        projeteis_veneno_pai_rato.append({
            "x": origem[0],
            "y": origem[1],
            "vx": dx / dist * 5.2,
            "vy": dy / dist * 5.2,
            "inicio": tempo_atual,
        })
        avisos_pai_rato.append({"tipo": "linha", "inicio": tempo_atual, "duracao": 360, "inicio_pos": origem, "fim_pos": alvo, "largura": 4, "cor": (80, 245, 110)})
        tempo_ultimo_cuspida_pai_rato = tempo_atual

    vivos = []
    for proj in projeteis_veneno_pai_rato:
        proj["x"] += proj["vx"] * dt
        proj["y"] += proj["vy"] * dt
        pygame.draw.circle(tela, (90, 255, 95), (int(proj["x"]), int(proj["y"])), 8)
        pygame.draw.circle(tela, (140, 70, 210), (int(proj["x"]), int(proj["y"])), 12, 2)
        rect = pygame.Rect(proj["x"] - 8, proj["y"] - 8, 16, 16)
        if rect.colliderect(personagem_rect):
            if imune_tempo_restante <= 0:
                vida -= max(8, int(vida_maxima * 0.10))
                tempo_ultimo_hit_inimigo = tempo_atual
                piscando_vida = True
                personagem_doente = True
                tempo_ultimo_atingido = tempo_atual
            criar_area_miasma(proj["x"], proj["y"], 48, 1900)
            continue
        if 0 <= proj["x"] <= largura_mapa and 0 <= proj["y"] <= altura_mapa and tempo_atual - proj["inicio"] < 4200:
            vivos.append(proj)
    projeteis_veneno_pai_rato[:] = vivos


def controlar_invocacoes_queijo_pai_rato(tempo_atual):
    global tempo_ultimo_queijo_pai_rato
    if queijos_sagrados or (pai_rato_ritual and pai_rato_ritual.get("ativo")):
        return
    vida_pct = vida_boss3 / max(1, vida_maxima_boss3)
    if vida_pct <= 0.85 and "queijo_85" not in pai_rato_eventos:
        invocar_queijo_sagrado(tipo="verdadeiro", vida_base=26, duracao=11000)
        pai_rato_eventos.add("queijo_85")
        tempo_ultimo_queijo_pai_rato = tempo_atual
    elif vida_pct <= 0.60 and "queijo_60" not in pai_rato_eventos:
        invocar_queijo_sagrado(largura_mapa * 0.34, altura_mapa * 0.34, "verdadeiro", 38, 12000)
        invocar_queijo_sagrado(largura_mapa * 0.66, altura_mapa * 0.62, "falso", 30, 12000, False, False)
        invocar_auxiliares_pai_rato(2)
        pai_rato_eventos.add("queijo_60")
        tempo_ultimo_queijo_pai_rato = tempo_atual
    elif vida_pct <= 0.25 and "ritual_25" not in pai_rato_eventos:
        iniciar_ritual_ultimo_queijo(tempo_atual)
        pai_rato_eventos.add("ritual_25")
        tempo_ultimo_queijo_pai_rato = tempo_atual
    elif fase_pai_rato >= 2 and tempo_atual - tempo_ultimo_queijo_pai_rato > 12000:
        invocar_queijo_sagrado(tipo="verdadeiro", vida_base=34 + fase_pai_rato * 7, duracao=10500)
        if fase_pai_rato >= 2:
            invocar_auxiliares_pai_rato(1)
        tempo_ultimo_queijo_pai_rato = tempo_atual


def atualizar_pai_rato(tela, tempo_atual, personagem_rect):
    global queijo_spawn, queijo_geracao
    queijo_spawn = bool(queijos_sagrados)
    queijo_geracao = 99
    atualizar_fase_pai_rato(tempo_atual)
    registrar_fala_pai_rato("entrada", tempo_atual)
    registrar_fala_pai_rato("final" if fase_pai_rato >= 3 else "ataque", tempo_atual)
    controlar_invocacoes_queijo_pai_rato(tempo_atual)
    disparar_chuva_frascos_padronizada(tempo_atual)
    atualizar_chuva_frascos_pai_rato(tempo_atual)
    atualizar_cuspida_veneno_pai_rato(tempo_atual, personagem_rect, tela)
    ataque_cauda_pai_rato(tempo_atual, personagem_rect)
    iniciar_carga_cega_pai_rato(tempo_atual)
    atualizar_carga_cega_pai_rato(tempo_atual, personagem_rect)
    atualizar_queijos_sagrados(tempo_atual)
    atualizar_ritual_ultimo_queijo(tempo_atual, tela)
    desenhar_queijos_sagrados(tela, tempo_atual)
    desenhar_avisos_pai_rato(tela, tempo_atual)
    if tempo_atual < pai_rato_atordoado_ate:
        pygame.draw.circle(tela, (90, 255, 220), (int(pos_x_chefe3 + chefe_largura3 // 2), int(pos_y_chefe3 - 12)), 28, 3)


def resetar_estado_pai_rato(tempo_base=None):
    global fe_pai_rato, fase_pai_rato, queijos_sagrados, avisos_pai_rato, projeteis_veneno_pai_rato
    global pai_rato_eventos, pai_rato_chuva_frascos, pai_rato_cauda, pai_rato_carga, pai_rato_consumindo
    global pai_rato_ritual, pai_rato_atordoado_ate, tempo_ultimo_cuspida_pai_rato, tempo_ultimo_cauda_pai_rato
    global tempo_ultimo_carga_pai_rato, tempo_ultimo_queijo_pai_rato, tempo_ultimo_chuva_pai_rato
    global pai_rato_fala_entrada_feita, tempo_proxima_fala_pai_rato, ultima_fala_pai_rato

    tempo_base = pygame.time.get_ticks() if tempo_base is None else tempo_base
    fe_pai_rato = 50
    fase_pai_rato = 1
    queijos_sagrados = []
    avisos_pai_rato = []
    projeteis_veneno_pai_rato = []
    pai_rato_eventos = set()
    pai_rato_chuva_frascos = None
    pai_rato_cauda = None
    pai_rato_carga = None
    pai_rato_consumindo = None
    pai_rato_ritual = None
    pai_rato_atordoado_ate = 0
    tempo_ultimo_cuspida_pai_rato = tempo_base
    tempo_ultimo_cauda_pai_rato = tempo_base
    tempo_ultimo_carga_pai_rato = tempo_base
    tempo_ultimo_queijo_pai_rato = tempo_base
    tempo_ultimo_chuva_pai_rato = tempo_base
    pai_rato_fala_entrada_feita = False
    tempo_proxima_fala_pai_rato = tempo_base
    ultima_fala_pai_rato = None


def serializar_estado_pai_rato():
    return {
        "tempo_snapshot_ms": pygame.time.get_ticks(),
        "fe": fe_pai_rato,
        "fase": fase_pai_rato,
        "queijos": queijos_sagrados,
        "avisos": avisos_pai_rato,
        "projeteis_veneno": projeteis_veneno_pai_rato,
        "eventos": list(pai_rato_eventos),
        "chuva_frascos": pai_rato_chuva_frascos,
        "cauda": pai_rato_cauda,
        "carga": pai_rato_carga,
        "ritual": pai_rato_ritual,
        "atordoado_ate": pai_rato_atordoado_ate,
        "tempo_ultimo_cuspida": tempo_ultimo_cuspida_pai_rato,
        "tempo_ultimo_cauda": tempo_ultimo_cauda_pai_rato,
        "tempo_ultimo_carga": tempo_ultimo_carga_pai_rato,
        "tempo_ultimo_queijo": tempo_ultimo_queijo_pai_rato,
        "tempo_ultimo_chuva": tempo_ultimo_chuva_pai_rato,
        "fala_entrada_feita": pai_rato_fala_entrada_feita,
        "tempo_proxima_fala": tempo_proxima_fala_pai_rato,
        "ultima_fala": ultima_fala_pai_rato,
        "disparos_boss3": disparos_boss3,
    }


def restaurar_estado_pai_rato(estado):
    global fe_pai_rato, fase_pai_rato, queijos_sagrados, avisos_pai_rato, projeteis_veneno_pai_rato
    global pai_rato_eventos, pai_rato_chuva_frascos, pai_rato_cauda, pai_rato_carga, pai_rato_consumindo
    global pai_rato_ritual, pai_rato_atordoado_ate, tempo_ultimo_cuspida_pai_rato, tempo_ultimo_cauda_pai_rato
    global tempo_ultimo_carga_pai_rato, tempo_ultimo_queijo_pai_rato, tempo_ultimo_chuva_pai_rato, disparos_boss3
    global pai_rato_fala_entrada_feita, tempo_proxima_fala_pai_rato, ultima_fala_pai_rato

    if not estado:
        resetar_estado_pai_rato()
        return

    agora = pygame.time.get_ticks()
    delta = agora - estado.get("tempo_snapshot_ms", agora)

    def ajustar_valor_tempo(valor):
        return valor + delta if valor else valor

    def ajustar_tempos_item(item, campos):
        if isinstance(item, dict):
            for campo in campos:
                if item.get(campo):
                    item[campo] += delta

    fe_pai_rato = estado.get("fe", 50)
    fase_pai_rato = estado.get("fase", 1)
    queijos_sagrados = estado.get("queijos", [])
    avisos_pai_rato = estado.get("avisos", [])
    projeteis_veneno_pai_rato = estado.get("projeteis_veneno", [])
    pai_rato_eventos = set(estado.get("eventos", []))
    pai_rato_chuva_frascos = estado.get("chuva_frascos")
    pai_rato_cauda = estado.get("cauda")
    pai_rato_carga = estado.get("carga")
    pai_rato_consumindo = None
    pai_rato_ritual = estado.get("ritual")
    pai_rato_atordoado_ate = ajustar_valor_tempo(estado.get("atordoado_ate", 0))
    tempo_ultimo_cuspida_pai_rato = ajustar_valor_tempo(estado.get("tempo_ultimo_cuspida", 0))
    tempo_ultimo_cauda_pai_rato = ajustar_valor_tempo(estado.get("tempo_ultimo_cauda", 0))
    tempo_ultimo_carga_pai_rato = ajustar_valor_tempo(estado.get("tempo_ultimo_carga", 0))
    tempo_ultimo_queijo_pai_rato = ajustar_valor_tempo(estado.get("tempo_ultimo_queijo", 0))
    tempo_ultimo_chuva_pai_rato = ajustar_valor_tempo(estado.get("tempo_ultimo_chuva", 0))
    pai_rato_fala_entrada_feita = estado.get("fala_entrada_feita", False)
    tempo_proxima_fala_pai_rato = ajustar_valor_tempo(estado.get("tempo_proxima_fala", 0))
    ultima_fala_pai_rato = estado.get("ultima_fala")
    disparos_boss3 = estado.get("disparos_boss3", [])

    for queijo in queijos_sagrados:
        ajustar_tempos_item(queijo, ("tempo_inicio", "consumo_inicio"))
    for aviso in avisos_pai_rato:
        ajustar_tempos_item(aviso, ("inicio",))
    for proj in projeteis_veneno_pai_rato:
        ajustar_tempos_item(proj, ("inicio",))
    for item in (pai_rato_chuva_frascos, pai_rato_cauda, pai_rato_carga, pai_rato_ritual):
        ajustar_tempos_item(item, ("inicio",))

    if pai_rato_consumindo is None:
        pai_rato_consumindo = next((q for q in queijos_sagrados if q.get("consumo_inicio")), None)


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

    limite_inimigos = max_inimigos2 if limite_inimigos is None else limite_inimigos
    if len(inimigos_comum) < limite_inimigos:
        tipo_inimigo = escolher_tipo_inimigo()
        # Adicione uma chance de 40% de gerar o inimigo na borda esquerda
        if random.random() <= 0.4:
            novo_inimigo = criar_inimigo(0, random.randint(10, altura_mapa), tipo_inimigo)
        else:
            novo_inimigo = criar_inimigo(largura_mapa, random.randint(10, altura_mapa), tipo_inimigo)

        # Verifique se o novo inimigo está muito próximo de algum inimigo existente
        distancia_minima_alcancada = any(
            math.sqrt((novo_inimigo["rect"].x - inimigo["rect"].x) ** 2 + (novo_inimigo["rect"].y - inimigo["rect"].y) ** 2) < distancia_minima_inimigos
            for inimigo in inimigos_comum
        )

        
        while distancia_minima_alcancada:
            tipo_inimigo = escolher_tipo_inimigo()
            if random.random() <= 0.4:
                novo_inimigo = criar_inimigo(0, random.randint(10, altura_mapa), tipo_inimigo)
            else:
                novo_inimigo = criar_inimigo(largura_mapa, random.randint(10, altura_mapa), tipo_inimigo)
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
    global aurea
    global tempo_parado_person, tempo_ultimo_escudo
    global direcao_atual, tempo_ultimo_disparo
    global fe_pai_rato, fase_pai_rato, queijos_sagrados, avisos_pai_rato, projeteis_veneno_pai_rato
    global pai_rato_eventos, pai_rato_chuva_frascos, pai_rato_cauda, pai_rato_carga, pai_rato_consumindo
    global pai_rato_ritual, pai_rato_atordoado_ate, tempo_ultimo_cuspida_pai_rato, tempo_ultimo_cauda_pai_rato
    global tempo_ultimo_carga_pai_rato, tempo_ultimo_queijo_pai_rato, tempo_ultimo_chuva_pai_rato
    global Boss_vivo3, gerar_fragmentos_morte, Chance_Sorte, Dano_Veneno_Acumulado, Executa_inimigo, Mercenaria_Active, Musica_tema_Boss3, Musica_tema_fases, Petro_active, Poison_Active, Resistencia, Resistencia_petro, Tempo_cura, Ultimo_Estalo, Valor_Bonus, altura_disparo, bonus_pontuacao, boss_envenenado, boss_frame_andando, boss_frame_atual, boss_frame_peca, carregar_atributos_na_fase, cartas_compradas, chance_critico, cooldown_dash, dano_inimigo_longe, dano_inimigo_perto, dano_person_hit, dano_petro, dano_por_tick_veneno_boss, disparos, disparos_boss3, disparos_inimigos, dispositivo_ativo, efeitos_texto, eliminacoes_consecutivas, eliminacoes_consecutivas_impulsiva, escudo_devota_ativo, fonte, frame_atual, impulsiva_ativa, imune_tempo_restante, inimigos_atingidos_por_onda, inimigos_comum, inimigos_eliminados, inimigos_em_chamas, rastros_toxicos, nuvens_miasma, areas_miasma, intervalo_disparo, largura_disparo, max_inimigos2, moedas_coletadas, moedas_soltadas, moedas_totais, movimento_pressionado, musica_boss3, nivel_ameaca, ondas, personagem_doente, petro_evolucao, piscando_vida, pontuacao, pontuacao_exib, pontuacao_magia, porcentagem_cura, pos_x_chefe3, pos_x_personagem, pos_x_petro, pos_y_chefe3, pos_y_personagem, pos_y_petro, quantidade_roubo_vida, queijo_geracao, queijo_spawn, r_press, rect_boss, roubo_de_vida, running, spawn_inimigo, sprite_moeda, teleportado, tempo_anterior_petro, tempo_atual, tempo_boss_entrada_fim, tempo_cooldown_dash, tempo_ultimo_dash, tempo_inicio_buff_impulsiva, tempo_inicio_veneno_boss, tempo_passado, tempo_texto_dano, tempo_ultima_atualizacao_direcao, tempo_ultima_regeneracao, tempo_ultimo_atingido, tempo_ultimo_disparo_inimigo, tempo_ultimo_frame_boss, tempo_ultimo_grupo_disparo_boss3, tempo_ultimo_hit_inimigo, tempo_ultimo_inimigo, tempo_ultimo_uso_habilidade, texto_dano, tipo_buff_impulsiva, toque, trembo, ultima_direcao_animacao, ultimo_tick_veneno_boss, upgrades, velocidade_personagem, vida, vida_boss3, vida_boss4, vida_inimigo_maxima, vida_maxima, vida_maxima_boss3, vida_maxima_boss4, vida_maxima_petro, vida_petro, vida_queijo, x, xp_petro, y, duracao_incendio_vanguarda, intervalo_escudo, comando_direção_petro
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
        resetar_estado_pai_rato()

        vfx_disparo_player = PlayerProjectileVFX()
        tempo_ultimo_disparo = pygame.time.get_ticks()
        disparo_preparando = False
        disparo_frame_atual = 0
        tempo_ultimo_frame_preparo_disparo = 0
        angulo_disparo_preparado = 0.0
        DISPARO_PREPARO_FRAME_MS = 85
        coice_onda = criar_estado_coice_onda()
        
        Musica_tema_fases.play(loops=-1)
        upgrades = carregar_upgrade_aureas("saves/aureas_upgrade.json")
        ondas_choque = []

        # Configurar e escalar as passivas das áureas
        nivel_devota = upgrades.get("Devota", 0)
        nivel_vanguarda = upgrades.get("Vanguarda", 0)
        nivel_impulsiva = upgrades.get("Impulsiva", 0)
        estado_insana = insana_aurea.criar_estado_insana(upgrades.get("Insana", 0), pygame.time.get_ticks())
        estado_voraz = voraz_aurea.criar_estado_voraz(upgrades.get("Voraz", 0), pygame.time.get_ticks())

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
                    "pontuacao": pontuacao,
                    "pontuacao_exib": pontuacao_exib,
                    "pontuacao_magia": pontuacao_magia,
                    "inimigos_eliminados": inimigos_eliminados,
                    "nivel_ameaca": nivel_ameaca,
                    "vida_inimigo_maxima": vida_inimigo_maxima,
                    "max_inimigos": max_inimigos2,
                    "tempo_cronometro": Variaveis.obter_tempo_decorrido(),
                    "inimigos_comum": Variaveis.serializar_inimigos_rewind(inimigos_comum),
                    "rastros_toxicos": rastros_toxicos,
                    "nuvens_miasma": nuvens_miasma,
                    "areas_miasma": areas_miasma,
                    "vida_boss": vida_boss3,
                    "estado_pai_rato": serializar_estado_pai_rato(),
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
                        nivel_ameaca = snap.get("nivel_ameaca", inimigos_eliminados // 10)
                        vida_inimigo_maxima = snap.get("vida_inimigo_maxima", vida_inimigo_maxima)
                        max_inimigos2 = snap.get("max_inimigos", max_inimigos2)
                        Variaveis.definir_tempo_cronometro(snap.get("tempo_cronometro", Variaveis.obter_tempo_decorrido()))
                        if "inimigos_comum" in snap:
                            inimigos_comum = Variaveis.restaurar_inimigos_rewind(snap.get("inimigos_comum"), frames_inimigo_esquerda3[0])
                        rastros_toxicos = snap.get("rastros_toxicos", [])
                        nuvens_miasma = snap.get("nuvens_miasma", [])
                        areas_miasma = snap.get("areas_miasma", [])
                        restaurar_estado_pai_rato(snap.get("estado_pai_rato"))
                        if snap.get("refragmentacao_rewind"):
                            imune_tempo_restante = max(imune_tempo_restante, 4000)
                            piscando_vida = False
                            Variaveis.aplicar_rewind_respawn_visual(pos_x_personagem, pos_y_personagem, direcao_atual, pygame.time.get_ticks())
                        if "vida_boss" in snap and snap["vida_boss"] is not None:
                            vida_boss3 = snap["vida_boss"]
                        if snap.get("r_press"):
                            r_press = True
                        Variaveis.snapshot_para_carregar = None
                except Exception as e:
                    registrar_erro("Fase 3: erro ao carregar atributos; usando padrao", e)
                carregar_atributos_na_fase=False

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
            pausa_por_fuga_mouse = Variaveis.deve_pausar_por_fuga_mouse(pos_mouse, largura_mapa, altura_mapa)
            fase_coop = multiplayer_coop.atualizar(3, pos_x_personagem, pos_y_personagem, direcao_atual, vida, vida_maxima, vida <= 0)
            if multiplayer_coop.aplicar_transicao_recebida(fase_coop, game_manager):
                raise CleanExit()
            mundo_coop = multiplayer_coop.sincronizar_mundo(
                3,
                inimigos_comum,
                criar_inimigo,
                boss={
                    "vida": vida_boss3,
                    "vida_maxima": vida_maxima_boss3,
                    "vivo": Boss_vivo3,
                    "r_press": r_press,
                    "x": pos_x_chefe3,
                    "y": pos_y_chefe3,
                },
                economia={
                    "pontuacao": pontuacao,
                    "pontuacao_exib": pontuacao_exib,
                    "pontuacao_magia": pontuacao_magia,
                },
            )
            if mundo_coop:
                boss_coop = mundo_coop.get("boss", {})
                economia_coop = mundo_coop.get("economia", {})
                vida_boss3 = boss_coop.get("vida", vida_boss3)
                vida_maxima_boss3 = boss_coop.get("vida_maxima", vida_maxima_boss3)
                Boss_vivo3 = bool(boss_coop.get("vivo", Boss_vivo3))
                r_press_anterior = r_press
                r_press = bool(boss_coop.get("r_press", r_press))
                if r_press and not r_press_anterior:
                    tempo_boss_entrada_fim = pygame.time.get_ticks() + 2500
                pos_x_chefe3 = boss_coop.get("x", pos_x_chefe3)
                pos_y_chefe3 = boss_coop.get("y", pos_y_chefe3)
                pontuacao = economia_coop.get("pontuacao", pontuacao)
                pontuacao_exib = economia_coop.get("pontuacao_exib", pontuacao_exib)
                pontuacao_magia = economia_coop.get("pontuacao_magia", pontuacao_magia)
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
                        multiplayer_coop.solicitar_acao("pause", 3)
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
                elif Variaveis.verificar_evento_input(event, "Habilidade Onda") and tempo_atual - tempo_ultimo_uso_habilidade >= cooldown_habilidade * voraz_aurea.bonus_cooldown(estado_voraz, aurea) * parasitica_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * lacerante_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa):
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
                                gerar_fragmentos_morte(morto_circuito, 3)
                                Variaveis.tentar_soltar_carta(morto_circuito["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                                inimigos_comum.remove(morto_circuito)
                                inimigos_eliminados += 1
                    elif parasitica_manifestacao.ativa(manifestacao_ativa):
                        mortos_eclosao, total_eclosao = parasitica_manifestacao.eclodir_todas(inimigos_comum, tempo_atual, efeitos_texto)
                        ondas.append(parasitica_manifestacao.criar_eclosao(px_centro, py_centro, tempo_atual, total_eclosao))
                        for morto_eclosao in mortos_eclosao:
                            if morto_eclosao in inimigos_comum:
                                gerar_fragmentos_morte(morto_eclosao, 3)
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
                    tempo_ultimo_uso_habilidade = tempo_atual

            # Verificar eventos de teclado
            # --- Tela de pausa (ESC) ---
            if multiplayer_coop.acao_confirmada("pause", 3):
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
                multiplayer_coop.aguardar_barreira("pause_saida", 3, tela, fonte, "Aguardando o outro jogador voltar do pause...")
                pygame.event.set_grab(True)
                pygame.mouse.set_visible(False)
                jogo_pausado = False
                continue

            if not pausa_por_fuga_mouse and botao_mouse[0] and not disparo_preparando and tempo_atual - tempo_ultimo_disparo >= ancorada_manifestacao.intervalo_disparo_ancorado(intervalo_disparo_racional(intervalo_disparo, aurea, racional_dilatacao_fim, tempo_atual), manifestacao_ativa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, tempo_atual):
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
                        origem_ataque = disparo["rect"].center
                        dano, dano_bloqueado, dano_flanco = calcular_dano_com_escudo(inimigo, dano, origem_ataque)
                        if dano_bloqueado:
                            cor = (190, 190, 170)
                            fonte_dano = fonte_dano_normal
                            desenhar_feedback_bloqueio(inimigo["rect"].centerx, inimigo["rect"].centery)
                            efeitos_texto.append({
                                "texto": "BLOQ",
                                "x": inimigo["rect"].centerx,
                                "y": inimigo["rect"].y - 34,
                                "tempo_inicio": tempo_atual,
                                "cor": (210, 205, 170)
                            })
                        elif dano_flanco:
                            cor = (255, 185, 60)
                            fonte_dano = fonte_dano_critico
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
                        if Petro_active:
                            if vida_petro > vida_maxima_petro :
                                vida_petro+= (vida_maxima_petro-vida_petro) *0.25   
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
                            if inimigo in inimigos_comum:
                                registrar_morte_toxica(inimigo)
                                gerar_fragmentos_morte(inimigo, 3)
                                inimigos_comum.remove(inimigo)
                            if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                largura_disparo += 0.095
                                altura_disparo += 0.095
                            posicao_inimigo = inimigo["rect"].center
                            soltar_moeda(posicao_inimigo)
                            Variaveis.tentar_soltar_carta(posicao_inimigo, tempo_atual, Chance_Sorte, inimigos_eliminados)
                            inimigos_eliminados += 1

                            # Multiplicador de Execução Superior (20%)
                            mult_ex = 1.0 + (nivel_ameaca * 0.20)

                            vida_inimigo_maxima += ganho_vida_inimigo_comum(1.0 * mult_ex)
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
                                vida_boss3 += ganho_progressao_boss(25 + nivel_ameaca * 10)
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += ganho_progressao_boss(30 + nivel_ameaca * 12)
                                vida_maxima_boss4 = vida_boss4

                        elif inimigo["vida"] <= 0:
                            insana_aurea.notificar_abate_insana(estado_insana, aurea, disparo)
                            posicao_inimigo = inimigo["rect"].center
                            soltar_moeda(posicao_inimigo)
                            Variaveis.tentar_soltar_carta(posicao_inimigo, tempo_atual, Chance_Sorte, inimigos_eliminados)
                            registrar_morte_toxica(inimigo)
                            gerar_fragmentos_morte(inimigo, 3)
                            inimigos_comum.remove(inimigo)
                            if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                largura_disparo += 0.095
                                altura_disparo += 0.095
                            inimigos_eliminados += 1

                            # --- ESCALONAMENTO DE ELITE (FASE 3 - 20 MINUTOS) ---
                            # O multiplicador base da Fase 3 é mais alto (0.15)
                            mult = 1.0 + (nivel_ameaca * 0.15)

                            vida_inimigo_maxima += ganho_vida_inimigo_comum(0.8 * mult)
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
                                incremento_v = ganho_progressao_boss(20 * mult)
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
            tempo_decorrido_run = Variaveis.obter_tempo_decorrido()
            limite_inimigos_run = max_inimigos2 + bonus_limite_inimigos_sem_boss(
                tempo_decorrido_run,
                r_press or Boss_vivo3,
                inimigos_eliminados,
                modo_dificil=Variaveis.obter_modo_cartas() == "drops",
            )
            pressao_spawn = calcular_pressao_spawn_pos_boss(
                pressao_pos_boss_spawn,
                tempo_atual,
                r_press and not Boss_vivo3,
                len(inimigos_comum),
                inimigos_eliminados,
                limite_inimigos_run,
            )
            if tempo_atual - tempo_ultimo_inimigo >= pressao_spawn["intervalo_ms"] and pressao_spawn["lote"] > 0 and (spawn_inimigo or not Boss_vivo3):
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
                disparo_frame_atual = min(disparo_frame_atual, len(frames_animacao['disp']) - 1)
                frame_atual = disparo_frame_atual
                if disparo_frame_atual >= len(frames_animacao['disp']) - 1:
                    px_centro = pos_x_personagem + largura_personagem // 2
                    py_centro = pos_y_personagem + altura_personagem // 2
                    largura_tiro, altura_tiro = voraz_aurea.dimensoes_disparo(estado_voraz, aurea, largura_disparo, altura_disparo)
                    disparo_novo = ancorada_manifestacao.criar_auto_attack(manifestacao_ativa, vfx_disparo_player,
                        px_centro, py_centro, largura_tiro, altura_tiro,
                        angulo_disparo_preparado, velocidade_disparo, tempo_atual, impulsiva_ativa
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
            frames_local = multiplayer_coop.frames_jogador_local(frames_animacao, frames_animacao2)
            frame_para_desenhar = frames_local[direcao_atual][frame_atual % len(frames_local[direcao_atual])]
            if direcao_atual == 'disp' and math.cos(angulo_disparo_preparado) < 0:
                frame_para_desenhar = pygame.transform.flip(frame_para_desenhar, True, False)
            desenhar_personagem_estado = desenhar_personagem_miasma if personagem_doente else desenhar_personagem_com_dano
            if angulo_inclinacao_personagem != 0:
                # Rotaciona o frame pelo centro para manter o eixo
                frame_rotacionado = pygame.transform.rotate(frame_para_desenhar, angulo_inclinacao_personagem)
                novo_rect = frame_rotacionado.get_rect(center=(pos_x_personagem + largura_personagem//2, pos_y_personagem + altura_personagem//2))
                desenhar_personagem_estado(tela, frame_rotacionado, novo_rect.x, novo_rect.y, tempo_atual, tempo_ultimo_hit_inimigo)
            else:
                w_f, h_f = frame_para_desenhar.get_size()
                bx = pos_x_personagem + (largura_personagem - w_f) // 2
                by = pos_y_personagem + (altura_personagem - h_f)
                desenhar_personagem_estado(tela, frame_para_desenhar, bx, by, tempo_atual, tempo_ultimo_hit_inimigo)

            insana_aurea.desenhar_insana(
                tela, estado_insana, aurea, tempo_atual,
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, config_graficos
            )
            multiplayer_coop.desenhar_jogador_remoto(tela, 3, frame_atual, frames_animacao, frames_animacao2)

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
                            # Resistência mitigando o impacto
                            dano_real = max(0, dano_inimigo_perto - Resistencia_petro)
                            vida_petro -= int(dano_real)

                            # Ataque Simbiótico: 1% do poder total do jogador + bônus da Petro
                            inimigo_mais_proximo["vida"] -= int(dano_person_hit * 0.01) + dano_petro
                            tempo_anterior_petro = tempo_atual_petro

                            if inimigo_mais_proximo["vida"] <= 0:
                                # Evolução por abate direto da Petro (Balanceado para 20 min)
                                vida_inimigo_maxima += ganho_vida_inimigo_comum(0.7)
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
                                    registrar_morte_toxica(inimigo_mais_proximo)
                                    gerar_fragmentos_morte(inimigo_mais_proximo, 3)
                                    Variaveis.tentar_soltar_carta(inimigo_mais_proximo["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                                    inimigos_comum.remove(inimigo_mais_proximo)

                                if not Boss_vivo3:
                                    # O dano do Boss 4 escala discretamente aqui para o desafio final
                                    mult_ex = 1.0 + (nivel_ameaca * 0.20)
                                    vida_boss4 += ganho_progressao_boss(5 * mult_ex)

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
                            vida_boss3-= dano_boss_mitigado(int(dano_person_hit*0.25)+300, 3, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
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

            boss_rect_voraz = pygame.Rect(pos_x_chefe3, pos_y_chefe3, chefe_largura3, chefe_altura3) if Boss_vivo3 else None
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
                    gerar_fragmentos_morte(morto_voraz, 3)
                    Variaveis.tentar_soltar_carta(morto_voraz["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                    inimigos_comum.remove(morto_voraz)
                    inimigos_eliminados += 1
            if boss_rect_voraz is not None:
                vida_boss3, vida, _ = voraz_aurea.aplicar_mordida_boss(
                    estado_voraz, aurea, tempo_atual,
                    pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem,
                    boss_rect_voraz, vida_boss3, vida, vida_maxima, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto
                )

            # Desenhar os disparos normais
            novos_disparos = []
            novos_disparos = []
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
                "vivo": Boss_vivo3,
                "rect": pygame.Rect(pos_x_chefe3, pos_y_chefe3, chefe_largura3, chefe_altura3) if Boss_vivo3 else None,
                "atingido_por_onda": globals().get("boss_atingido_por_onda", {}).get("boss", 0),
                "hit_flag": False
            }
            inimigos_mortos_neste_frame = processar_habilidade_onda(
                ondas, correntes_eletricas, inimigos_comum, boss_info, tela, dt, tempo_atual, largura_mapa, altura_mapa, velocidade_onda, disparos, config_graficos
            )
            if boss_info.get("hit_flag"):
                dano_onda_boss = boss_info.get("dano_manifestacao", dano_person_hit * fator_dano_aureas(tempo_atual) * 3)
                dano_onda_real = dano_boss_mitigado(dano_onda_boss, 3, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                vida_boss3 -= dano_onda_real
                registrar_dano_boss(efeitos_texto, dano_onda_real, pos_x_chefe3 + chefe_largura3 // 2, pos_y_chefe3 - 22, tempo_atual, (180, 255, 255))
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
                            multiplayer_coop.enviar_transicao_fase(4)
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
                    registrar_morte_toxica(morto)
                    gerar_fragmentos_morte(morto, 3)
                    Variaveis.tentar_soltar_carta(morto["rect"].center, tempo_atual, Chance_Sorte, inimigos_eliminados)
                    inimigos_comum.remove(morto)
                    nivel_ameaca = min(inimigos_eliminados // 10, 100)
                    vida_inimigo_maxima += ganho_vida_inimigo_comum(1.5 + nivel_ameaca * 1.2)
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
                        vida_boss3 += ganho_progressao_boss(25 + nivel_ameaca * 10)
                        vida_maxima_boss3 = vida_boss3
                        vida_boss4 += ganho_progressao_boss(30 + nivel_ameaca * 12)
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
                if inimigo.get("tipo") == TIPO_INIMIGO_INCENSARIO:
                    atualizar_incensario(
                        inimigo,
                        (pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem),
                        tempo_atual,
                        fator_tempo_mundo,
                    )
                elif inimigo.get("tipo") == TIPO_INIMIGO_GUARDIAO_SUCATA:
                    atualizar_guardiao_sucata(
                        inimigo,
                        (pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem),
                        fator_tempo_mundo,
                    )
                else:
                    inimigo["pos_x"] += (dx / dist) * inimigo.get("velocidade_x", 1.70) * fator_tempo_mundo
                    inimigo["pos_y"] += (dy / dist) * inimigo.get("velocidade_y", 1.50) * fator_tempo_mundo
                    inimigo["rect"].x = int(inimigo["pos_x"])
                    inimigo["rect"].y = int(inimigo["pos_y"])
                    registrar_rastro_toxico(inimigo, tempo_atual)

            # Resolve colisões e separações entre inimigos e jogador
            pos_x_personagem, pos_y_personagem = Variaveis.resolver_colisao_player_com_inimigos(
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, inimigos_comum
            )
            pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem))
            pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem))
            Variaveis.resolver_colisoes_e_separacao(inimigos_comum, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)

            personagem_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
            atualizar_rastros_toxicos(personagem_rect, tempo_atual)
            atualizar_nuvens_miasma(personagem_rect, tempo_atual)
            atualizar_areas_miasma(personagem_rect, tempo_atual)
            desenhar_rastros_toxicos(tela, tempo_atual)
            desenhar_nuvens_miasma(tela, tempo_atual)
            desenhar_areas_miasma(tela, tempo_atual)
            atualizar_e_desenhar_feedbacks_bloqueio(tela, tempo_atual)

            lacerante_manifestacao.atualizar_e_desenhar_sangue_lacerante(tela, inimigos_comum, config_graficos)

            for inimigo in inimigos_comum:
                dx = pos_x_personagem - inimigo["rect"].x
                dy = pos_y_personagem - inimigo["rect"].y

                # Atualize os frames do inimigo com base na direção
                if dx > 0:  # Mova para a direita
                    inimigo["image"] = frames_inimigo_direita3[frame_atual % len(frames_inimigo_direita3)]
                else:  # Mova para a esquerda
                    inimigo["image"] = frames_inimigo_esquerda3[frame_atual % len(frames_inimigo_esquerda3)]

                # Desenhar sombra do inimigo
                largura_visual = max(1, int(largura_inimigo3 * inimigo.get("escala", 1.0)))
                altura_visual = max(1, int(altura_inimigo3 * inimigo.get("escala", 1.0)))
                desenhar_sombra(tela, inimigo["rect"].x, inimigo["rect"].y, largura_visual, altura_visual)
                desenhar_inimigo(tela, inimigo)
                desenhar_barra_de_vida(tela, inimigo["rect"].x, inimigo["rect"].y - 10, largura_visual, 5, inimigo["vida"], inimigo["vida_maxima"], inimigo.get("eletrocutado", False), Executa_inimigo if Ultimo_Estalo else None)

                tempo_atual = pygame.time.get_ticks()
                if inimigo.get("tipo") not in (TIPO_INIMIGO_INCENSARIO, TIPO_INIMIGO_GUARDIAO_SUCATA) and tempo_atual - tempo_ultimo_disparo_inimigo >= intervalo_disparo_inimigo and random.random() <= 0.01:  #frequencia do disparo do sinimigos
                    disparos_inimigos.append(criar_disparo_inimigo((inimigo["rect"].x, inimigo["rect"].y), (pos_x_personagem, pos_y_personagem)))
                    tempo_ultimo_disparo_inimigo = tempo_atual  # Atualize o tempo do último disparo

            inimigos_rects = [inimigo["rect"] for inimigo in inimigos_comum]

            if imune_tempo_restante > 0:
                imune_tempo_restante -= relogio.get_time()  # Reduz o tempo de imunidade com base no tempo de quadro
            else:
                imune_tempo_restante = 0  # Redefine a imunidade


            if verificar_colisao_personagem_inimigo(personagem_rect, inimigos_rects) and imune_tempo_restante <= 0:

                if tempo_atual - tempo_ultimo_hit_inimigo >= intervalo_hit_inimigo:
                    inimigos_em_contato = [inimigo for inimigo in inimigos_comum if personagem_rect.colliderect(inimigo["rect"])]
                    multiplicador_dano_contato = max((inimigo.get("dano_multiplicador", 1.0) for inimigo in inimigos_em_contato), default=1.0)
                    Dano_pos_resistencia_person = int((((vida_maxima * 0.25)+dano_inimigo_perto) - Resistencia) * multiplicador_dano_contato)
                    if aurea == "Vanguarda":
                        for inimigo in inimigos_comum:
                            if personagem_rect.colliderect(inimigo["rect"]):
                                id_inimigo = id(inimigo)
                                tempo_queimadura = pygame.time.get_ticks()
                                inimigos_em_chamas[id_inimigo] = tempo_queimadura

                    if absorver_dano_devota_atual():
                        pass
                    elif Dano_pos_resistencia_person > 0:
                        vida -= Dano_pos_resistencia_person
                        guardiao_em_contato = next((inimigo for inimigo in inimigos_em_contato if inimigo.get("tipo") == TIPO_INIMIGO_GUARDIAO_SUCATA), None)
                        if guardiao_em_contato:
                            empurrao_x = (pos_x_personagem + largura_personagem // 2) - guardiao_em_contato["rect"].centerx
                            empurrao_y = (pos_y_personagem + altura_personagem // 2) - guardiao_em_contato["rect"].centery
                            dist_empurrao = max(1.0, math.hypot(empurrao_x, empurrao_y))
                            pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem + int((empurrao_x / dist_empurrao) * 14)))
                            pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem + int((empurrao_y / dist_empurrao) * 14)))
                            personagem_rect.x = pos_x_personagem
                            personagem_rect.y = pos_y_personagem
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
                        if absorver_dano_devota_atual():
                            pass
                        elif imune_tempo_restante <= 0:

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
            if Ultimo_Estalo and vida_boss3 <= limiar_execucao_boss(Executa_inimigo) * vida_maxima_boss3:
                Boss_vivo3=False
            elif vida_boss3 <=0:
                Boss_vivo3=False


            if Boss_vivo3:

                chamada_boss3_solicitada = keys[pygame.K_r]
                if multiplayer_coop.modo_multiplayer() and not r_press and chamada_boss3_solicitada:
                    multiplayer_coop.solicitar_acao("boss3", 3)
                boss3_confirmado = multiplayer_coop.modo_multiplayer() and not r_press and multiplayer_coop.acao_confirmada(
                    "boss3", 3, delay_ms=4000, assumir_sim_apos_ms=multiplayer_coop.COOP_SILENCIO_CONFIRMA_MS
                )
                if boss3_confirmado or (not multiplayer_coop.modo_multiplayer() and chamada_boss3_solicitada):
                    if not r_press:
                        tempo_boss_entrada_fim = tempo_atual + 2500
                    r_press = True

                if r_press:
                    Musica_tema_fases.stop()
                    max_inimigos2=9
                    if musica_boss3 == 1:
                        # Defina o volume da música (opcional)
                        Musica_tema_Boss3.play(loops=-1)
                        musica_boss3+=1

                    spawn_inimigo=False
                    personagem_doente = False

                    desenhar_barra_vida_boss(tela, vida_boss3, vida_maxima_boss3, "PAI-RATO", 3, (224, 190, 1))
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

                        acertou_boss_disparo = (
                            lacerante_manifestacao.colisao_corte(disparo, rect_boss, tempo_atual)
                            if disparo.get("tipo_manifestacao") == "lacerante_corte"
                            else (
                                prismatica_manifestacao.colisao_feixe(disparo, rect_boss, tempo_atual)
                                if disparo.get("tipo_manifestacao") == "prismatica_feixe"
                                else (
                                    retornante_manifestacao.colisao_alvo(disparo, {"rect": rect_boss, "retornante_id": "boss3"})
                                    if disparo.get("tipo_manifestacao") == "retornante_pulso"
                                    else rect_disparo.colliderect(rect_boss)
                                )
                            )
                        )
                        if acertou_boss_disparo:
                            acerto_prismatico = prismatica_manifestacao.registrar_acerto(
                                disparo, {"rect": rect_boss, "prismatica_id": "boss3"}, tempo_atual
                            )
                            acerto_retornante = retornante_manifestacao.registrar_acerto(
                                disparo,
                                {"rect": rect_boss, "retornante_id": "boss3"},
                                tempo_atual,
                                (pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2),
                            )
                            if vida_boss3 > 0:  # Verifica se o chefe está vivo antes de aplicar dano
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
                                dano_por_tick_veneno_boss = vida_maxima_boss3 * Dano_Veneno_Acumulado
                                duracao_veneno_boss = 8000 + cartas_compradas.get("Poison", 0) * 100
                                tempo_inicio_veneno_boss = pygame.time.get_ticks()
                                ultimo_tick_veneno_boss = pygame.time.get_ticks()

                            if tempo_atual < pai_rato_atordoado_ate:
                                dano *= 1.35
                                cor = (100, 255, 210)

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

                            # Renderizar texto do dano
                            tempo_texto_dano = pygame.time.get_ticks()
                            dano = dano_boss_mitigado(dano, 3, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                            registrar_dano_boss(efeitos_texto, dano, pos_x_chefe3 + chefe_largura3 // 2, pos_y_chefe3 - 24, tempo_atual, cor)
                            vida_boss3 -= dano
                            if (vida_boss3 <= 0 or (Ultimo_Estalo and vida_boss3 <= limiar_execucao_boss(Executa_inimigo) * vida_maxima_boss3)):
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
                            vida_boss3 -= dano_boss_mitigado(dano_por_tick_veneno_boss, 3, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0), tipo_dano="veneno")
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
                    rect_personagem_boss = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                    atualizar_pai_rato(tela, tempo_atual, rect_personagem_boss)

                    if False and tempo_atual - tempo_ultimo_grupo_disparo_boss3 >= tempo_espera_grupo_disparo_boss3 and not queijo_spawn:  # Mantido desativado; o Pai-Rato agora usa padroes telegrafados.
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
                            if imune_tempo_restante <= 0:
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
                                estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)
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
                                estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)
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
                                estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)
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
                                estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)
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
                                estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)
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
                            multiplayer_coop.enviar_transicao_fase(4)
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
            modo_loja_normal = Variaveis.obter_modo_cartas() != "drops"
            abrir_loja_manual = modo_loja_normal and (Variaveis.verificar_input("Comprar na loja") or (joystick and joystick.get_button(3)))
            if abrir_loja_manual and multiplayer_coop.modo_multiplayer():
                if pontuacao_exib >= custo_carta_atual:
                    multiplayer_coop.solicitar_acao("loja", 3)
                abrir_loja_manual = False
            if multiplayer_coop.acao_confirmada("loja", 3):
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
                "onda": max(0.0, (cooldown_habilidade * voraz_aurea.bonus_cooldown(estado_voraz, aurea) * parasitica_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * lacerante_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) - (tempo_atual - tempo_ultimo_uso_habilidade)) / 1000.0),
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

            multiplayer_coop.desenhar_status_acao(tela, fonte, "loja", 3)
            multiplayer_coop.desenhar_status_acao(tela, fonte, "pause", 3)
            multiplayer_coop.desenhar_status_acao(
                tela,
                fonte,
                "boss3",
                3,
                delay_ms=4000,
                assumir_sim_apos_ms=multiplayer_coop.COOP_SILENCIO_CONFIRMA_MS,
            )
            multiplayer_coop.desenhar_diagnostico(tela, fonte)
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
