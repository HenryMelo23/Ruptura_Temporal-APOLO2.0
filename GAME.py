
import pygame
import subprocess
import sys
import random
import math
import time
import os
import json
from Tela_Cartas import tela_de_pausa
from Variaveis import *
from habilidades_personagem import processar_habilidade_onda, atualizar_e_desenhar_correntes
import Variaveis
from utils import *
from audio_manager import carregar_config_audio, aplicar_volume_som
from Tela_Upgrade_Aureas import tela_upgrade_aureas
from Boss1_Ataques import gerenciador_ataques_boss1
def desenhar_onda_arco(tela, x, y, raio, angulo_centro, tamanho_abertura, cor, largura):
    ang_inicio = angulo_centro + tamanho_abertura / 2
    ang_fim = angulo_centro + 2 * math.pi - tamanho_abertura / 2
    passos = 60
    pontos = []
    for i in range(passos + 1):
        ang = ang_inicio + (ang_fim - ang_inicio) * (i / passos)
        px = x + math.cos(ang) * raio
        py = y + math.sin(ang) * raio
        pontos.append((px, py))
    if len(pontos) > 1:
        pygame.draw.lines(tela, cor, False, pontos, largura)

boss_estagio_60_ativado = False
boss_estagio_40_ativado = False
tempo_boss_estagio_ataque_fim = 0
boss_transicao_ondas = []
ondas_lancadas_transicao = 0
ultima_onda_tipo = ""
tempo_slow_onda_fim = 0
dt = 1.0

# Forward declarations (atribuídos no loop principal)
botao_mouse = (False, False, False)
sprite_moeda = None
joystick = None
escudo_devota_ativo = True
duracao_incendio_vanguarda = 5000
intervalo_escudo = 30000
boss_morte_processada = False
grupo_fragmentos = None
tempo_stun_jogador_fim = 0
knockback_x = 0.0
knockback_y = 0.0
tempo_boss_entrada_fim = 0
boss_empurrou_jogador = False

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
        "efeitos_visuais": True,
        "fps_limite": 60
    }

# Carregar configurações de áudio
config_audio = carregar_config_audio()

dano_inimigo=80
estalos = aplicar_volume_som(pygame.mixer.Sound("Sounds/Estalo.mp3"), config_audio)

som_ataque_boss = aplicar_volume_som(pygame.mixer.Sound("Sounds/Hit_Boss1.mp3"), config_audio)

Hit_inimigo1 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Inimigo1_hit.wav"), config_audio)

Disparo_Geo = aplicar_volume_som(pygame.mixer.Sound("Sounds/Disparo_Geo.wav"), config_audio)

Musica_tema_Boss1 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase1_Boss.mp3"), config_audio)

Musica_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase_boas.mp3"), config_audio)

Som_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Praia.wav"), config_audio) 

Som_portal = pygame.mixer.Sound("Sounds/Portal.mp3")
Som_portal.set_volume(0.06) 

Dano_person = pygame.mixer.Sound("Sounds/hit_person.mp3")
Dano_person.set_volume(0.1)  

toque=0
comando_direção_petro=True
musica_boss1= 1
tempo_ultimo_ataque = 0 
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
    (3, "Clique no botão esquerdo do mouse para atacar"),
    (7, "Use SHIFT para dar dash"),
    (11, "Aperte Q para abrir a loja"),
    (15, "Junte pontos e melhore o personagem"),
    (19, "Você está sozinho. Mas está preparado."),
    
]

# --- Tutorial Interativo (Fases) ---
# Fase 1: WASD  |  Fase 2: SHIFT x3  |  Fase 3: Parede roxa  |  Fase 4: Mensagens finais
tutorial_fase = 1
tutorial_inimigo_ativo = False  # inimigo do tutorial (fase 4)
tutorial_inimigo = None  # dicionário do inimigo do tutorial
tutorial_wasd = {'w': False, 'a': False, 's': False, 'd': False}
tutorial_dash_count = 0
tutorial_parede_ativa = False
tutorial_parede_rect = None  # definido ao entrar na fase 3
tutorial_lado_inicial = None  # lado do jogador quando a parede aparece
tempo_fase_completa = 0  # marca o instante da última transição



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

        
movimento_pressionado = False
atributos = {}
dano = 0
f = None
fonte = None
lado = None
running = True
tempo_atual = 0
texto = None
ultima_tecla_movimento = None
teleporte_sprites = []
teleporte_index = 0
teleporte_timer = 0
x = 0
y = 0

class FragmentoTemporal(pygame.sprite.Sprite):
    """Fragmento temporal coletável que aparece após a morte do boss.
    Renderizado proceduralmente com pygame.draw — sem dependência de imagem externa."""

    def __init__(self, posicao):
        super().__init__()
        self.posicao_base = pygame.math.Vector2(posicao)
        # Hitbox menor que o visual para coleta precisa
        self.rect = pygame.Rect(0, 0, 32, 32)
        self.rect.center = posicao

        self.w, self.h = 128, 128
        self.image = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.angle_ring = 0.0
        self.time = 0
        self.particulas = []
        self.coletado = False  # Flag para impedir coleta dupla

    def update(self, *args, **kwargs):
        if self.coletado:
            return

        self.time += 1
        self.angle_ring += 0.05

        # Movimento flutuante vertical usando seno
        floating_offset = math.sin(self.time * 0.07) * 8
        self.rect.centery = int(self.posicao_base.y + floating_offset)

        # Limpar imagem
        self.image.fill((0, 0, 0, 0))

        cx, cy = self.w // 2, self.h // 2

        # === GLOW EXTERNO PULSANTE ===
        glow_pulse = 1.0 + 0.20 * math.sin(self.time * 0.1)
        for r in range(48, 5, -4):
            glow_radius = int(r * glow_pulse)
            alpha = int(40 * (1.0 - r / 48.0))
            pygame.draw.circle(self.image, (0, 191, 255, alpha), (cx, cy), glow_radius)
            if r > 30:
                pygame.draw.circle(self.image, (128, 0, 200, alpha // 2), (cx, cy), glow_radius + 6)

        # === SOMBRA SUAVE ABAIXO ===
        sombra_w = int(44 - floating_offset * 0.5)
        sombra_h = int(12 - floating_offset * 0.15)
        if sombra_w > 0 and sombra_h > 0:
            sombra_rect = pygame.Rect(cx - sombra_w // 2, self.h - 16, sombra_w, sombra_h)
            pygame.draw.ellipse(self.image, (0, 0, 0, 55), sombra_rect)

        # === ANEL TEMPORAL GIRANDO ===
        anel_w = int(55 + 12 * math.sin(self.time * 0.05))
        anel_h = 18
        num_pontos = 20
        for i in range(num_pontos):
            ang = self.angle_ring + (i * (2 * math.pi / num_pontos))
            px = cx + int(anel_w * math.cos(ang))
            py = cy + int(anel_h * math.sin(ang))
            depth = math.sin(ang)
            size = max(1, int(2.5 + depth * 1.5))
            alpha = max(0, min(255, int(180 + depth * 75)))
            p_color = (0, 220, 255, alpha) if i % 2 == 0 else (180, 50, 255, alpha)
            pygame.draw.circle(self.image, p_color, (px, py), size)

        # === PARTÍCULAS ORBITANDO ===
        if len(self.particulas) < 18 and random.random() < 0.35:
            self.particulas.append({
                "radius": random.uniform(22, 55),
                "angle": random.uniform(0, 2 * math.pi),
                "speed": random.uniform(0.02, 0.07),
                "size": random.uniform(1.5, 3.5),
                "color": random.choice([
                    (0, 191, 255), (100, 200, 255), (143, 33, 252),
                    (200, 100, 255), (255, 255, 255)
                ]),
                "life": random.randint(35, 70),
                "max_life": 70
            })

        particulas_vivas = []
        for p in self.particulas:
            p["angle"] += p["speed"]
            p["radius"] -= 0.18
            p["life"] -= 1
            if p["life"] > 0 and p["radius"] >= 5:
                alpha = max(0, min(255, int((p["life"] / p["max_life"]) * 220)))
                px = cx + int(p["radius"] * math.cos(p["angle"]))
                py = cy + int(p["radius"] * math.sin(p["angle"]))
                cor = p["color"]
                pygame.draw.circle(self.image, (cor[0], cor[1], cor[2], alpha), (px, py), int(p["size"]))
                particulas_vivas.append(p)
        self.particulas = particulas_vivas

        # === LOSANGO CENTRAL (CRISTAL) ===
        cristal_w = 22
        cristal_h = 38
        pontos_losango = [
            (cx, cy - cristal_h // 2),       # Topo
            (cx + cristal_w // 2, cy),        # Direita
            (cx, cy + cristal_h // 2),        # Base
            (cx - cristal_w // 2, cy)         # Esquerda
        ]

        # Corpo escuro do cristal
        pygame.draw.polygon(self.image, (10, 25, 55, 240), pontos_losango)

        # Face direita iluminada com brilho pulsante
        brilho_face = int(120 + 60 * math.sin(self.time * 0.12))
        face_direita = [
            (cx, cy - cristal_h // 2),
            (cx + cristal_w // 2, cy),
            (cx, cy + cristal_h // 2)
        ]
        pygame.draw.polygon(self.image, (0, brilho_face, 220, 150), face_direita)

        # Borda ciano brilhante
        pygame.draw.polygon(self.image, (0, 255, 255, 220), pontos_losango, width=2)

        # Linha vertical central (rachadura de energia)
        pygame.draw.line(self.image, (255, 255, 255, 200),
                         (cx, cy - cristal_h // 2 + 4),
                         (cx, cy + cristal_h // 2 - 4), 1)
        # Linha horizontal central (rachadura de energia) — FIX: adicionadas tuplas corretas
        pygame.draw.line(self.image, (255, 255, 255, 200),
                         (cx - cristal_w // 2 + 3, cy),
                         (cx + cristal_w // 2 - 3, cy), 1)
        # Linha diagonal (energia roxa)
        pygame.draw.line(self.image, (180, 100, 255, 240),
                         (cx - 4, cy - 6),
                         (cx + 4, cy + 6), 1)
        # Linha diagonal cruzada
        pygame.draw.line(self.image, (100, 180, 255, 200),
                         (cx + 3, cy - 5),
                         (cx - 3, cy + 5), 1)

        # === BRILHO SHIMMER NO TOPO DO CRISTAL ===
        shimmer_alpha = max(0, min(255, int(80 + 120 * math.sin(self.time * 0.15))))
        shimmer_y = cy - cristal_h // 2 + 6
        pygame.draw.line(self.image, (255, 255, 255, shimmer_alpha),
                         (cx - 3, shimmer_y), (cx + 3, shimmer_y + 2), 2)

    def draw(self, surface):
        """Desenha o fragmento na superfície do jogo."""
        if self.coletado:
            return
        rect_desenho = self.image.get_rect(center=self.rect.center)
        surface.blit(self.image, rect_desenho.topleft)


def executar_jogo(game_manager=None):
    global dt
    global tempo_boss_entrada_fim
    global tempo_stun_jogador_fim, knockback_x, knockback_y, boss_empurrou_jogador
    global boss_estagio_60_ativado, boss_estagio_40_ativado, tempo_boss_estagio_ataque_fim
    global boss_transicao_ondas, ondas_lancadas_transicao, ultima_onda_tipo, tempo_slow_onda_fim
    global joystick, ondas_choque, carregar_atributos_na_fase, Chance_Sorte, Dano_Boss_Habilit, Dano_Veneno_Acumulado, Executa_inimigo, Mercenaria_Active, Musica_tema_Boss1, Musica_tema_fases, Petro_active, Poison_Active, Resistencia, Resistencia_petro, Som_tema_fases, Tempo_cura, Ultimo_Estalo, Valor_Bonus, Velocidade_Inimigos_1, altura_disparo, altura_personagem, angulo_inclinacao_personagem, apertou_q, atributos, bonus_pontuacao, boss_envenenado, cartas_compradas, chance_critico, cooldown_dash, dano, dano_boss, dano_inimigo_longe, dano_inimigo_perto, dano_person_hit, dano_petro, dano_por_tick_veneno_boss, direcao_atual, direcao_atual_petro, disparos, dispositivo_ativo, distancia_dash, efeitos_texto, eliminacoes_consecutivas, eliminacoes_consecutivas_impulsiva, em_ataque_especial, escudo_devota_ativo, espacamento, f, fonte, frame_atual_chefe, frame_porcentagem, hitboxes, impulsiva_ativa, imune_tempo_restante, inimigos_atingidos_por_onda, inimigos_comum, inimigos_eliminados, inimigos_em_chamas, intervalo_disparo, jogador_posicoes, lado, largura_disparo, largura_personagem, linha, mensagem, mensagem_ativa, mensagem_mostrada, mensagens_exibidas, moedas_coletadas, moedas_soltadas, moedas_totais, musica_boss1, ondas, petro_evolucao, pontuacao, pontuacao_exib, pontuacao_magia, porcentagem_cura, pos_x_chefe, pos_x_personagem, pos_x_petro, pos_y_chefe, pos_y_personagem, pos_y_petro, quantidade_roubo_vida, r_press, rect_boss, relogio, roubo_de_vida, running, sprite_moeda, teleportado, teleporte_duration, teleporte_index, teleporte_timer, tempo_anterior_petro, tempo_ataque_especial, tempo_atual, tempo_cooldown_dash, tempo_fase_completa, tempo_fim_mensagem, tempo_inicial, tempo_inicio_buff_impulsiva, tempo_inicio_veneno_boss, tempo_mostrando_mensagem, tempo_passado_animacao_chefe, tempo_texto_dano, tempo_ultima_atualizacao_direcao, tempo_ultima_mudanca_direcao_boss, tempo_ultima_regeneracao, tempo_ultimo_ataque, tempo_ultimo_dano_ataque, tempo_ultimo_dash, tempo_ultimo_uso_habilidade, texto, texto_dano, tipo_buff_impulsiva, toque, trembo, tutorial_dash_count, tutorial_fase, tutorial_lado_inicial, tutorial_parede_ativa, tutorial_parede_rect, tutorial_wasd, ultima_direcao_animacao, ultima_direcao_boss, ultima_tecla_movimento, ultimo_tick_veneno_boss, velocidade_disparo, velocidade_personagem, vida, vida_boss, vida_boss2, vida_boss3, vida_boss4, vida_maxima, vida_maxima_boss1, vida_maxima_boss2, vida_maxima_boss3, vida_maxima_boss4, vida_maxima_petro, vida_petro, x, xp_petro, tutorial_inimigo_ativo, tutorial_inimigo, y, duracao_incendio_vanguarda, intervalo_escudo, comando_direção_petro
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
        with open("saves/aurea_selecionada.json", "r") as file:
            aurea = json.load(file)["aurea"]

        with open("saves/tutorial_config.json", "r") as f:
            mostrar_tutorial = json.load(f).get("mostrar_tutorial", True)

        upgrade_aureas = carregar_upgrade_aureas("saves/aureas_upgrade.json")


        tempo_inicial = time.time() 

        tempo_anterior = pygame.time.get_ticks()
        tempo_movimento = random.randint(2000, 7000)
        tempo_parado = random.randint(500, 700) 
        movendo = True 
        boss_vivo1=False
        relogio = pygame.time.Clock()
        ultimo_tempo_reducao = time.time()
        fator_lentidao_boss = 1.0
        alerta_boss_ativo = False
        tempo_inicio_alerta_boss = 0
        alerta_boss_mostrado_para = 0
        largura_disparo, altura_disparo = 40, 40
        velocidade_disparo = 10
        disparos = []
        ondas_choque = []

        tela = pygame.display.set_mode((largura_mapa, altura_mapa))
        pygame.display.set_caption("Renderizando Mapa com Personagem")

        pontuacao_inimigos=0
        maxima_pontuacao_magia = 750
        piscar_magia = False





        #INIMIGOS

        tempo_ultimo_inimigo_apos_morte = pygame.time.get_ticks()
        # Carregar a imagem do mapa
        mapa = pygame.image.load(mapa_path1).convert()
        mapa = pygame.transform.scale(mapa, (largura_mapa, altura_mapa))

        teleporte_sprites = [
            pygame.transform.scale(pygame.image.load("Sprites/icon_teleport.png").convert_alpha(), (80, 80)),
            pygame.transform.scale(pygame.image.load("Sprites/icon_teleport2.png").convert_alpha(), (80, 80))
        ]
        teleporte_index = 0
        teleporte_timer = 0
        # Carregar as sequências de imagens do personagem

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

        piscando_vida = False
        vida_inimigo_maxima=30
        vida_inimigo= vida_inimigo_maxima





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
            global tutorial_wasd, tutorial_fase, tutorial_dash_count, tempo_fase_completa, tutorial_parede_ativa, tutorial_parede_rect, tutorial_lado_inicial
            global angulo_inclinacao_personagem
            global Resistencia_petro, dano_inimigo_perto, vida_maxima_petro, dano_petro, dano_inimigo_longe
            global dano_boss, Dano_Boss_Habilit, Velocidade_Inimigos_1, inimigos_eliminados, pontuacao
            global eliminacoes_consecutivas_impulsiva, eliminacoes_consecutivas, pontuacao_exib, bonus_pontuacao, vida_boss
            global vida_maxima_boss1, vida_boss2, vida_maxima_boss2, vida_boss3, vida_maxima_boss3, vida_boss4, vida_maxima_boss4
            global tempo_stun_jogador_fim, knockback_x, knockback_y
            nonlocal vida_inimigo_maxima, fator_lentidao_boss

            tempo_atual = pygame.time.get_ticks()
            if tempo_atual < tempo_stun_jogador_fim:
                # Jogador atordoado (stun) - não aceita comandos, mas sofre knockback
                if knockback_x != 0 or knockback_y != 0:
                    pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem + knockback_x * dt))
                    pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem + knockback_y * dt))
                    knockback_x *= 0.85
                    knockback_y *= 0.85
                    if abs(knockback_x) < 0.5: knockback_x = 0
                    if abs(knockback_y) < 0.5: knockback_y = 0
                direcao_atual = 'stop'
                return 'stop'

            # Aplica knockback mesmo sem estar atordoado
            if knockback_x != 0 or knockback_y != 0:
                pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem + knockback_x * dt))
                pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem + knockback_y * dt))
                knockback_x *= 0.85
                knockback_y *= 0.85
                if abs(knockback_x) < 0.5: knockback_x = 0
                if abs(knockback_y) < 0.5: knockback_y = 0

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
                # Rastrear WASD para o tutorial interativo
                if mostrar_tutorial and tutorial_fase == 1:
                    if ultima_tecla_movimento == 'right': tutorial_wasd['d'] = True
                    elif ultima_tecla_movimento == 'left': tutorial_wasd['a'] = True
                    elif ultima_tecla_movimento == 'up': tutorial_wasd['w'] = True
                    elif ultima_tecla_movimento == 'down': tutorial_wasd['s'] = True
                    if all(tutorial_wasd.values()):
                        tutorial_fase = 2
                        tempo_fase_completa = time.time()

                # Normalização de movimento diagonal
                if dx != 0 and dy != 0:
                    inclinacao = angulo_diagonal_personagem

                    if dy < 0:
                        angulo_inclinacao_personagem = -inclinacao if dx > 0 else inclinacao
                    else:
                        angulo_inclinacao_personagem = inclinacao if dx > 0 else -inclinacao

                    fator_normalizacao = 0.7071
                    pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                                 pos_x_personagem + dx * (velocidade_personagem * fator_lentidao_boss) * fator_normalizacao * dt))
                    pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                                 pos_y_personagem + dy * (velocidade_personagem * fator_lentidao_boss) * fator_normalizacao * dt))
                else:
                    angulo_inclinacao_personagem = 0
                    pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                                 pos_x_personagem + dx * (velocidade_personagem * fator_lentidao_boss) * dt))
                    pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                                 pos_y_personagem + dy * (velocidade_personagem * fator_lentidao_boss) * dt))
            else:
                angulo_inclinacao_personagem = 0
                if botao_mouse[0]:
                    direcao_atual = 'disp'
                else:
                    direcao_atual = 'stop'

            # Colisão com a parede roxa do tutorial (bloqueia andar, teleporte passa)
            if tutorial_parede_ativa and tutorial_parede_rect:
                personagem_rect_check = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                if personagem_rect_check.colliderect(tutorial_parede_rect):
                    # Como a parede é totalmente vertical de ponta a ponta do mapa, a colisão é apenas horizontal.
                    # Determina o lado baseado na posição do personagem em relação ao centro da parede para empurrar.
                    if (pos_x_personagem + largura_personagem / 2) < tutorial_parede_rect.centerx:
                        pos_x_personagem = tutorial_parede_rect.left - largura_personagem
                    else:
                        pos_x_personagem = tutorial_parede_rect.right

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
                        gerar_fragmentos_morte(inimigo, 1)
                        if inimigo in inimigos_comum:
                            inimigos_comum.remove(inimigo)
                        
                        # Escalonamento por nível de ameaça
                        vida_inimigo_maxima += 1.2 + nivel_ameaca * 0.8
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
                        ganho = int(75 + math.log2(inimigos_eliminados + 1) * 4)
                        pontuacao += ganho
                        eliminacoes_consecutivas_impulsiva += 1

                        if Mercenaria_Active:
                            eliminacoes_consecutivas += 1
                            pontuacao_exib += ganho + bonus_pontuacao
                            if eliminacoes_consecutivas % 5 == 0:
                                bonus_pontuacao = min(500, bonus_pontuacao + Valor_Bonus)
                        else:
                            pontuacao_exib += ganho

                        if not boss_vivo1:
                            if vida_boss > 0:
                                vida_boss += 15 + nivel_ameaca * 10
                                vida_maxima_boss1 = vida_boss
                                vida_boss2 += 20 + nivel_ameaca * 12
                                vida_maxima_boss2 = vida_boss2
                                vida_boss3 += 25 + nivel_ameaca * 15
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += 30 + nivel_ameaca * 18
                                vida_maxima_boss4 = vida_boss4

                # Dano ao Boss (só se vivo e morte não processada)
                if boss_vivo1 and not boss_morte_processada:
                    bx = pos_x_chefe + chefe_largura // 2
                    by = pos_y_chefe + chefe_altura // 2
                    dist_boss = math.hypot(bx - cx_t, by - cy_t)
                    if dist_boss <= raio_choque:
                        vida_boss -= dano_choque
                        efeitos_texto.append({
                            "texto": f"-{int(dano_choque)}",
                            "x": pos_x_chefe + chefe_largura // 2,
                            "y": pos_y_chefe - 20,
                            "tempo_inicio": pygame.time.get_ticks(),
                            "cor": (0, 191, 255)
                        })

                # Contar dashes para o tutorial
                if mostrar_tutorial and tutorial_fase == 2:
                    tutorial_dash_count += 1
                    if tutorial_dash_count >= 3:
                        tutorial_fase = 3
                        tutorial_parede_ativa = True
                        # Parede roxa vertical no centro do mapa de ponta a ponta
                        parede_w = 20
                        parede_h = altura_mapa
                        tutorial_parede_rect = pygame.Rect(
                            largura_mapa // 2 - parede_w // 2,
                            0,
                            parede_w, parede_h
                        )
                        tempo_fase_completa = time.time()

            if cooldown_dash and pygame.time.get_ticks() - tempo_ultimo_dash > tempo_cooldown_dash:
                cooldown_dash = False

            return direcao_atual

        inimigos_comum = []



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

            if len(inimigos_comum) < max_inimigos:
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
            chance = 0.05 # 5%
            if random.random() < chance:
                tamanho_moeda = (36, 36)  # Novo tamanho desejado
                sprite_redimensionada = pygame.transform.scale(sprite_moeda, tamanho_moeda)
                rect = sprite_redimensionada.get_rect(center=posicao)
                moedas_soltadas.append({
                    "rect": rect,
                    "image": sprite_redimensionada
                })






        tempo_parado_person = pygame.time.get_ticks()  
        boss_atingido_por_onda = pygame.time.get_ticks()
        tempo_ultimo_disparo = pygame.time.get_ticks()
        tempo_ultimo_escudo = pygame.time.get_ticks()

        Som_tema_fases.play(loops=-1)
        Musica_tema_fases.play(loops=-1)

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

        FPS=pygame.time.Clock()
        pygame.mouse.set_visible(False)
        cursor_imagem = pygame.image.load("Sprites/Ponteiro.png").convert_alpha()  # Ajuste o caminho
        cursor_tamanho = cursor_imagem.get_size()
        pygame.event.set_grab(True)  # Travar mouse dentro da janela
        jogo_pausado = False

        sprite_moeda = pygame.image.load("Sprites/moeda.png").convert_alpha()
        moedas_soltadas = []
        fragmentos_morte = []
        global boss_morte_processada, grupo_fragmentos
        boss_morte_processada = False
        grupo_fragmentos = pygame.sprite.Group()

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
            if carregar_atributos_na_fase:
                try:
                    carregar_atributos()
                except Exception as e:
                    print(f"Aviso: Nao foi possivel carregar atributos ({e}). Usando padrao.")
                carregar_atributos_na_fase = False
            fator_lentidao_boss = 1.0
            if tempo_atual < tempo_slow_onda_fim:
                fator_lentidao_boss = min(fator_lentidao_boss, 0.4)
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


            pos_mouse = pygame.mouse.get_pos()
            botao_mouse = pygame.mouse.get_pressed()
            mouse_x = max(0, min(pos_mouse[0], largura_mapa - cursor_tamanho[0]))
            mouse_y = max(0, min(pos_mouse[1], altura_mapa - cursor_tamanho[1]))
            for event in pygame.event.get():
                Variaveis.atualizar_estado_mouse(event)
                Variaveis.processar_eventos_teleporte(event, cooldown_dash)
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
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
                    elif mostrar_tutorial and tutorial_fase == 6:
                        if event.key in [pygame.K_RETURN, pygame.K_SPACE, pygame.K_r]:
                            if event.key == pygame.K_r:
                                r_press = True
                            tutorial_fase = 7
                            mostrar_tutorial = False
                            try:
                                with open("saves/tutorial_config.json", "w") as f:
                                    json.dump({"mostrar_tutorial": False}, f)
                            except:
                                pass
                elif botao_mouse[0] and tempo_atual - tempo_ultimo_disparo >= intervalo_disparo and tempo_atual >= tempo_stun_jogador_fim:  # Botão esquerdo do mouse
                    pos_mouse = pygame.mouse.get_pos()
                    px_centro = pos_x_personagem + largura_personagem // 2
                    py_centro = pos_y_personagem + altura_personagem // 2
                    angulo = calcular_angulo_disparo((px_centro, py_centro), pos_mouse)
                    Disparo_Geo.play()
                    # Crie o disparo com direção baseada no ângulo
                    novo_disparo = {
                        "rect": pygame.Rect(px_centro - largura_disparo // 2, py_centro - altura_disparo // 2, largura_disparo, altura_disparo),
                        "angulo": angulo
                    }
                    disparos.append(novo_disparo)
                    tempo_ultimo_disparo = tempo_atual  # Atualizar o tempo do último disparo
                elif Variaveis.verificar_evento_input(event, "Habilidade Onda") and tempo_atual - tempo_ultimo_uso_habilidade >= cooldown_habilidade and tempo_atual >= tempo_stun_jogador_fim:
                    pos_mouse = pygame.mouse.get_pos()
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
                
                from Tela_Pause import exibir_tela_pause
                ret_pause = exibir_tela_pause(tela, cartas_compradas, joy)
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


            novos_inimigos = []
            novos_disparos = []
            inimig_atin=[]

            tempo_passado += relogio.get_rawtime()
            relogio.tick()

             # Adicionar inimigos a cada 10 segundos
            tempo_atual = pygame.time.get_ticks()
            if mostrar_tutorial:
                pass  # Nenhum inimigo comum durante o tutorial
            else:
                if tempo_atual - tempo_ultimo_inimigo >= 1000 and len(inimigos_comum) < max_inimigos and not boss_vivo1:
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
                            "texto": f"+{ganho}",
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


            shake_x, shake_y = 0, 0
            tela.fill((255, 255, 255))
            tela.blit(mapa, (0, 0))




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
                "vivo": boss_vivo1 and not boss_morte_processada,
                "rect": pygame.Rect(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura) if (boss_vivo1 and not boss_morte_processada) else None,
                "atingido_por_onda": boss_atingido_por_onda,
                "hit_flag": False
            }
            inimigos_mortos_neste_frame = processar_habilidade_onda(
                ondas, correntes_eletricas, inimigos_comum, boss_info, tela, dt, tempo_atual, largura_mapa, altura_mapa, velocidade_onda
            )
            if boss_info.get("hit_flag") and not boss_morte_processada:
                vida_boss -= dano_person_hit * 5
                boss_atingido_por_onda = boss_info["atingido_por_onda"]

            # Atualizar e desenhar correntes elétricas
            inimigos_mortos_correntes = atualizar_e_desenhar_correntes(tela, correntes_eletricas, inimigos_comum, tempo_atual, dano_person_hit)
            
            inimigos_mortos = inimigos_mortos_neste_frame + inimigos_mortos_correntes
            for morto in inimigos_mortos:
                if morto in inimigos_comum:
                    gerar_fragmentos_morte(morto, 1)
                    inimigos_comum.remove(morto)
                    inimigos_eliminados += 1
                    
                    # --- ESCALONAMENTO POR NIVEL DE AMEAÇA ---
                    mult = 1.0 + (nivel_ameaca * 0.1)
                    vida_inimigo_maxima += 0.5 * mult
                    Resistencia_petro += 0.05 * mult
                    dano_inimigo_perto += 0.04 * mult
                    dano_person_hit += 0.03 * mult
                    vida_maxima_petro += 0.2 * mult
                    dano_petro += 0.005 * mult
                    dano_inimigo_longe += 0.01 * mult
                    dano_boss += 0.01 * mult
                    Dano_Boss_Habilit += 0.02 * mult
                    Velocidade_Inimigos_1 = min(4.8, Velocidade_Inimigos_1 + 0.0001)

                    # --- ECONOMIA DE PONTOS PARA AS 50 CARTAS ---
                    ganho = int(120 * (1 + math.log10(inimigos_eliminados + 1)))
                    pontuacao += ganho
                    pontuacao_exib += ganho
                    
                    if vida_petro < (vida_maxima_petro * 0.6):
                        vida_petro = min(vida_maxima_petro, vida_petro + (vida_maxima_petro * 0.2))
                        
                    if not boss_vivo1:
                        vida_boss += 12 * mult
                        vida_maxima_boss1 = vida_boss
                        vida_boss2 += 15 * mult
                        vida_maxima_boss2 = vida_boss2
                        vida_boss3 += 18 * mult
                        vida_maxima_boss3 = vida_boss3
                        vida_boss4 += 22 * mult
                        vida_maxima_boss4 = vida_boss4

            tempo_atual = pygame.time.get_ticks()
            if movendo:
                if tempo_atual - tempo_anterior >= tempo_movimento:
                    # Atualize o tempo anterior para o tempo atual
                    tempo_anterior = tempo_atual
                    movendo = False
                    tempo_movimento = random.randint(3000, 7000)
                # Atualizar movimento dos inimigos com previsão
                tempo_previsao = 5  # Tempo em quadros para prever o movimento

                atualizar_movimento_inimigos(
                inimigos_comum, pos_x_personagem, pos_y_personagem, ultima_tecla_movimento, velocidade_personagem, tempo_previsao, movendo
                )
            else:
                if tempo_atual - tempo_anterior >= tempo_parado:
                    # Atualize o tempo anterior para o tempo atual
                    tempo_anterior = tempo_atual
                    movendo = True
                    tempo_parado = random.randint(10, 3000)





            # Desenhe os inimigos na tela
            for inimigo in inimigos_comum:
                inimigo["image"] = frames_inimigo[frame_atual % len(frames_inimigo)]

                # Desenhar sombra do inimigo
                desenhar_sombra(tela, inimigo["rect"].x, inimigo["rect"].y, largura_inimigo, altura_inimigo)
                tela.blit(inimigo["image"], inimigo["rect"])
                desenhar_barra_de_vida(tela, inimigo["rect"].x, inimigo["rect"].y - 10, largura_inimigo, 5, inimigo["vida"], inimigo["vida_maxima"], inimigo.get("eletrocutado", False))

            personagem_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem*0.5, altura_personagem*0.8)
            inimigos_rects = [inimigo["rect"] for inimigo in inimigos_comum]


            if imune_tempo_restante > 0:
                imune_tempo_restante -= relogio.get_time()  
            else:
                imune_tempo_restante = 0 


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
                    mostrar_tutorial=False
                    try:
                        with open("saves/tutorial_config.json", "w") as f:
                            json.dump({"mostrar_tutorial": False}, f)
                    except:
                        pass
                    pausar_cronometro()
                    pygame.time.delay(2000)
                    Musica_tema_fases.stop()
                    Som_tema_fases.stop()
                    moedas_totais = tela_upgrade_aureas(tela, fonte, moedas_totais)


                    limpar_salvamento()
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.GAME_OVER)
                        raise CleanExit()
                    else:
                        pygame.quit()
                        subprocess.run([python, "Game_Over.py"])
                        sys.exit()

            # Adicione esta verificação para controlar o piscar da barra de vida
            if piscando_vida:
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

            if boss_vivo1 and not boss_morte_processada:
                if tempo_atual < tempo_boss_entrada_fim:
                    progresso = (tempo_atual - (tempo_boss_entrada_fim - 2500)) / 2500.0
                    target_y_chefe = altura_mapa // 2 - chefe_altura // 2
                    pos_x_chefe = largura_mapa // 2 - chefe_largura // 2
                    if progresso < 0.8:
                        pos_y_chefe = -chefe_altura - 200 + (target_y_chefe + chefe_altura + 200) * (progresso / 0.8)
                    else:
                        pos_y_chefe = target_y_chefe
                        # Tremor de tela do impacto
                        boss_impacto_shake = 1.0 - (progresso - 0.8) / 0.2
                        shake_intensity = int(15 * boss_impacto_shake)
                        shake_x = random.randint(-shake_intensity, shake_intensity) if shake_intensity > 0 else 0
                        shake_y = random.randint(-shake_intensity, shake_intensity) if shake_intensity > 0 else 0
                        
                        # Empurra o jogador radialmente se ele estiver embaixo do boss usando knockback suave
                        if not boss_empurrou_jogador:
                            boss_empurrou_jogador = True
                            dx = (pos_x_personagem + largura_personagem // 2) - (largura_mapa // 2)
                            dy = (pos_y_personagem + altura_personagem // 2) - (altura_mapa // 2)
                            dist = math.sqrt(dx ** 2 + dy ** 2)
                            if dist < 350:
                                if dist == 0:
                                    dx = 1
                                    dist = 1.0
                                kb_magnitude = max(15.0, 60.0 * (1.0 - dist / 350.0))
                                knockback_x = (dx / dist) * kb_magnitude
                                knockback_y = (dy / dist) * kb_magnitude
                elif tempo_atual < tempo_boss_estagio_ataque_fim:
                    pos_x_chefe = largura_mapa // 2 - chefe_largura // 2
                    pos_y_chefe = altura_mapa // 2 - chefe_altura // 2
                    
                    tempo_decorrido = 6000 - (tempo_boss_estagio_ataque_fim - tempo_atual)
                    if tempo_decorrido < 4800:
                        ciclo = tempo_decorrido % 1200
                        offset_y = -abs(math.sin(math.pi * ciclo / 1200) * 120)
                    else:
                        offset_y = 0

                    # Spawn de ondas no final de cada pulo (ao bater no chão)
                    onda_alvo = int(tempo_decorrido // 1200)
                    if onda_alvo > ondas_lancadas_transicao and onda_alvo <= 4:
                        ondas_lancadas_transicao = onda_alvo
                        if ultima_onda_tipo == "completa":
                            tipo_onda = "incompleta"
                        else:
                            tipo_onda = "incompleta" if random.random() > 0.4 else "completa"
                        ultima_onda_tipo = tipo_onda
                        nova_onda = {
                            "x": pos_x_chefe + chefe_largura // 2,
                            "y": pos_y_chefe + chefe_altura // 2,
                            "raio": 0.0,
                            "largura_linha": 12,
                            "tipo": tipo_onda,
                            "angulo_abertura_centro": random.uniform(0, 2 * math.pi),
                            "tamanho_abertura": random.uniform(math.pi / 4, math.pi / 2), # 45 a 90 graus
                            "velocidade": 350.0,
                            "dano": int(vida_maxima * 0.04),
                            "atingiu_player": False
                        }
                        boss_transicao_ondas.append(nova_onda)
                else:
                    pos_x_personagem, pos_y_personagem, vida, escudo_devota_ativo, slow_f, pos_chefe_nova, stun_req, kb_x_boss, kb_y_boss = gerenciador_ataques_boss1.update(
                        dt, [pos_x_personagem, pos_y_personagem], largura_personagem, altura_personagem,
                        vida, vida_maxima, escudo_devota_ativo, Dano_Boss_Habilit,
                        [pos_x_chefe, pos_y_chefe], chefe_largura, chefe_altura, vida_boss, vida_maxima_boss1,
                        largura_mapa, altura_mapa, tempo_atual
                    )
                    pos_x_chefe, pos_y_chefe = pos_chefe_nova
                    fator_lentidao_boss = min(fator_lentidao_boss, slow_f)
                    if stun_req > 0:
                        tempo_stun_jogador_fim = tempo_atual + stun_req
                        knockback_x = kb_x_boss
                        knockback_y = kb_y_boss
                        Dano_person.play()
                        piscando_vida = True
                        tempo_ultimo_hit_inimigo = tempo_atual
                
                gerenciador_ataques_boss1.draw(tela)

                # Atualizar e desenhar ondas de transição
                novas_ondas_transicao = []
                for wave in boss_transicao_ondas:
                    wave["raio"] += wave["velocidade"] * (dt_ms / 1000.0)
                    
                    cor_borda = (150, 0, 255)
                    cor_centro = (0, 255, 255)
                    if wave["tipo"] == "completa":
                        pygame.draw.circle(tela, cor_borda, (int(wave["x"]), int(wave["y"])), int(wave["raio"]), wave["largura_linha"] + 4)
                        pygame.draw.circle(tela, cor_centro, (int(wave["x"]), int(wave["y"])), int(wave["raio"]), wave["largura_linha"] - 4)
                    else:
                        desenhar_onda_arco(tela, wave["x"], wave["y"], wave["raio"], wave["angulo_abertura_centro"], wave["tamanho_abertura"], cor_borda, wave["largura_linha"] + 4)
                        desenhar_onda_arco(tela, wave["x"], wave["y"], wave["raio"], wave["angulo_abertura_centro"], wave["tamanho_abertura"], cor_centro, wave["largura_linha"] - 4)
                    
                    # Colisão
                    dist = math.sqrt((pos_x_personagem + largura_personagem // 2 - wave["x"]) ** 2 + (pos_y_personagem + altura_personagem // 2 - wave["y"]) ** 2)
                    if abs(dist - wave["raio"]) <= wave["largura_linha"] / 2 + max(largura_personagem, altura_personagem) / 2:
                        safe = False
                        if wave["tipo"] == "incompleta":
                            player_ang = math.atan2(pos_y_personagem + altura_personagem // 2 - wave["y"], pos_x_personagem + largura_personagem // 2 - wave["x"])
                            player_ang = player_ang % (2 * math.pi)
                            ang_inicio = (wave["angulo_abertura_centro"] - wave["tamanho_abertura"] / 2) % (2 * math.pi)
                            ang_fim = (wave["angulo_abertura_centro"] + wave["tamanho_abertura"] / 2) % (2 * math.pi)
                            
                            if ang_inicio < ang_fim:
                                if ang_inicio <= player_ang <= ang_fim:
                                    safe = True
                            else:
                                if player_ang >= ang_inicio or player_ang <= ang_fim:
                                    safe = True
                        
                        if not safe and not wave["atingiu_player"]:
                            wave["atingiu_player"] = True
                            dano_onda = wave["dano"]
                            if escudo_devota_ativo:
                                escudo_devota_ativo = False
                            elif Resistencia < dano_onda:
                                vida -= int(dano_onda - Resistencia)
                            
                            # Aplica 60% de slow por 2 segundos
                            tempo_slow_onda_fim = tempo_atual + 2000
                            
                            shake_x = random.randint(-12, 12)
                            shake_y = random.randint(-12, 12)
                            Dano_person.play()
                            piscando_vida = True
                            tempo_ultimo_hit_inimigo = tempo_atual

                    if wave["raio"] < 1200:
                        novas_ondas_transicao.append(wave)
                boss_transicao_ondas = novas_ondas_transicao


            ###############################################   DESENHA O PERSONAGEM NA TELA ################################
            # Desenhar sombra do personagem
            desenhar_sombra(tela, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)

            frame_para_desenhar = frames_animacao[direcao_atual][frame_atual % len(frames_animacao[direcao_atual])]
            if angulo_inclinacao_personagem != 0:
                # Rotaciona o frame pelo centro para manter o eixo
                frame_rotacionado = pygame.transform.rotate(frame_para_desenhar, angulo_inclinacao_personagem)
                novo_rect = frame_rotacionado.get_rect(center=(pos_x_personagem + largura_personagem//2, pos_y_personagem + altura_personagem//2))
                tela.blit(frame_rotacionado, novo_rect.topleft)
            else:
                tela.blit(frame_para_desenhar, (pos_x_personagem, pos_y_personagem))

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
                        pos_x_petro += 1 * direcao_petro[0] * dt
                        pos_y_petro += 1 * direcao_petro[1] * dt


                    # Calcula a distância entre "Petro" e o inimigo mais próximo
                    distancia_petro_inimigo = math.sqrt((pos_x_petro - pos_x_inimigo_mais_proximo) ** 2 + (pos_y_petro - pos_y_inimigo_mais_proximo) ** 2)

                    # Verifica se "Petro" está próximo o suficiente para aplicar dano
                    if distancia_petro_inimigo <= 50:
                        # Verifica se passou tempo suficiente desde o último dano
                        tempo_atual_petro = pygame.time.get_ticks()
                        if tempo_atual_petro - tempo_anterior_petro >= intervalo_dano_petro:
                            # Cálculo de Defesa: Petro absorve dano através de sua resistência
                            dano_real_em_petro = max(0, dano_inimigo - Resistencia_petro)
                            vida_petro -= int(dano_real_em_petro)

                            # Dano da Petro: 0.5% do dano total do jogador + bônus fixo da Petro
                            inimigo_mais_proximo["vida"] -= int(dano_person_hit * 0.005) + dano_petro
                            tempo_anterior_petro = tempo_atual_petro

                            if inimigo_mais_proximo["vida"] <= 0:
                                # Evolução harmônica por abate da Petro
                                vida_inimigo_maxima += 0.5
                                Resistencia_petro += 0.08
                                vida_maxima_petro += 0.25
                                dano_person_hit += 0.05
                                dano_petro += 0.008
                                inimigos_eliminados += 1

                                # Pontuação otimizada
                                pontos_petro = int(100 * (1 + math.log10(inimigos_eliminados + 1)))
                                pontuacao += pontos_petro
                                pontuacao_exib += pontos_petro

                                if inimigo_mais_proximo in inimigos_comum:
                                    gerar_fragmentos_morte(inimigo_mais_proximo, 1)
                                    inimigos_comum.remove(inimigo_mais_proximo)

                            if not boss_vivo1:
                                if vida_boss>0:
                                    vida_boss+=55
                                    vida_maxima_boss1= vida_boss
                                    vida_boss2+=66
                                    vida_maxima_boss2= vida_boss2
                                    vida_boss3+=72
                                    vida_maxima_boss3= vida_boss3   
                                    vida_boss4+=82
                                    vida_maxima_boss4= vida_boss4

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



                if boss_vivo1 and not boss_morte_processada:
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
                    pos_x_petro += 1 * direcao_x * dt
                    pos_y_petro += 1 * direcao_y * dt

                    # Verifica se Petro está próximo o suficiente para aplicar dano ao boss
                    distancia_petro_boss = math.sqrt((pos_x_petro - pos_x_chefe) ** 2 + (pos_y_petro - pos_y_chefe) ** 2)
                    if distancia_petro_boss <= 50:
                        # Verifica se passou tempo suficiente desde o último dano
                        tempo_atual_petro = pygame.time.get_ticks()
                        if tempo_atual_petro - tempo_anterior_petro >= intervalo_dano_petro:
                            # Aplica dano ao "boss"
                            vida_petro -= int(dano_boss)
                            vida_petro+= int(vida_maxima_petro-vida_petro)*quantidade_roubo_vida
                            vida_boss-= int(dano_person_hit*0.15)+15
                            # Aqui você pode adicionar outras ações relacionadas ao dano ao "boss"
                            tempo_anterior_petro = tempo_atual_petro

                if comando_direção_petro:
                    direcao_atual_petro="left_petro"
                    comando_direção_petro=False

                desenhar_barra_de_vida_petro(tela, vida_petro, pos_x_petro, pos_y_petro - 20,vida_maxima_petro)
                # Desenhar sombra do Petro
                desenhar_sombra(tela, pos_x_petro, pos_y_petro, largura_personagem, altura_personagem)
                tela.blit(petro_nivel[direcao_atual_petro][frame_atual % len(petro_nivel[direcao_atual_petro])], (pos_x_petro, pos_y_petro))


        #AQUI GERAMOS O BOSS:
            if pontuacao >= 3000500 or (keys[pygame.K_r]) or r_press:
                r_press=True
                # Verificar se é hora de realizar um ataque do boss
                Musica_tema_fases.stop()
                tempo_atual = pygame.time.get_ticks()


                if musica_boss1 == 1:
                    boss_vivo1=True
                    # Defina o volume da música (opcional)
                    Musica_tema_Boss1.play(loops=-1)
                    musica_boss1+=1
                    tempo_boss_entrada_fim = tempo_atual + 2500
                    tempo_stun_jogador_fim = tempo_boss_entrada_fim
                    boss_empurrou_jogador = False
                    pos_x_chefe = largura_mapa // 2 - chefe_largura // 2
                    pos_y_chefe = -chefe_altura - 200  # Começa no céu
                # Lógica para animar o chefe
                tempo_passado_animacao_chefe += relogio.get_rawtime()
                if tempo_passado_animacao_chefe >= tempo_animacao_chefe:
                    tempo_passado_animacao_chefe = 0
                    frame_atual_chefe = (frame_atual_chefe + 1) % 2

                # Mude a direção do boss a cada 3 segundos
                tempo_atual = pygame.time.get_ticks()
                intervalo_mudanca_direcao_boss = random.randint(1000, 3000) # Tempo em milissegundos para mudar de direção do boss
                if tempo_atual - tempo_ultima_mudanca_direcao_boss >= intervalo_mudanca_direcao_boss:

                    direcoes_possiveis = ['up', 'down', 'left', 'right']
                    if ultima_direcao_boss in direcoes_possiveis:
                        direcoes_possiveis.remove(ultima_direcao_boss)  # Remova a direção anterior
                    ultima_direcao_boss = random.choice(direcoes_possiveis)
                    tempo_ultima_mudanca_direcao_boss = tempo_atual  # Atualize o tempo da última mudança de direção

                if boss_vivo1:
                    inimigos_comum = []  # Limpe a lista de inimigos comuns
                    # Movimentação do boss

                    if tempo_atual < tempo_boss_entrada_fim or tempo_atual < tempo_boss_estagio_ataque_fim:
                        pass
                    elif gerenciador_ataques_boss1.boss_movendo_por_ataque():
                        pass
                    else:
                        # Carapaça quebrando e boss mais raivoso/leve -> mais rápido
                        velocidade_chefe_calculada = Velocidade_boss * (1.0 + (1.0 - (vida_boss / max(1.0, vida_maxima_boss1))) * 1.5)
                        if ultima_direcao_boss == 'up':
                            pos_y_chefe = max(0, pos_y_chefe - velocidade_chefe_calculada * dt)  # Garanta que o boss não ultrapasse o topo
                        elif ultima_direcao_boss == 'down':
                            pos_y_chefe = min(altura_mapa - chefe_altura, pos_y_chefe + velocidade_chefe_calculada * dt)  # Garanta que o boss não ultrapasse a base
                        elif ultima_direcao_boss == 'left':
                            pos_x_chefe = max(0, pos_x_chefe - velocidade_chefe_calculada * dt)  # Garanta que o boss não ultrapasse a borda esquerda
                        elif ultima_direcao_boss == 'right':
                            pos_x_chefe = min(largura_mapa - chefe_largura, pos_x_chefe + velocidade_chefe_calculada * dt)  # Garanta que o boss não ultrapasse a borda direita

                    # Verifica se o boss chegou à borda da tela (apenas se não estiver movendo por ataque)
                    if not gerenciador_ataques_boss1.boss_movendo_por_ataque() and (pos_x_chefe <= 0 or pos_x_chefe >= largura_mapa - chefe_largura or pos_y_chefe <= 0 or pos_y_chefe >= altura_mapa - chefe_altura):
                        # Se sim, mude para a direção oposta (você pode definir as direções conforme necessário)
                        if ultima_direcao_boss == 'up':
                            ultima_direcao_boss = 'down'
                        elif ultima_direcao_boss == 'down':
                            ultima_direcao_boss = 'up'
                        elif ultima_direcao_boss == 'left':
                            ultima_direcao_boss = 'right'
                        elif ultima_direcao_boss == 'right':
                            ultima_direcao_boss = 'left'








                # === PROCESSAR MORTE DO BOSS (uma única vez) ===
                if (vida_boss <= 0 or (Ultimo_Estalo and vida_boss <= Executa_inimigo * vida_maxima_boss1)) and not boss_morte_processada:
                    # Guardar posição antes de desativar
                    posicao_morte_boss = (pos_x_chefe + chefe_largura // 2, pos_y_chefe + chefe_altura // 2)
                    boss_vivo1 = False
                    boss_morte_processada = True
                    boss_envenenado = False
                    em_ataque_especial = False
                    gerenciador_ataques_boss1.ataques_ativos.clear()
                    # Criar o FragmentoTemporal na posição do boss
                    fragmento = FragmentoTemporal(posicao_morte_boss)
                    grupo_fragmentos.add(fragmento)

                # === COLETA DO FRAGMENTO TEMPORAL ===
                if boss_morte_processada and len(grupo_fragmentos) > 0:
                    rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                    for frag in grupo_fragmentos:
                        if not frag.coletado and rect_personagem.colliderect(frag.rect):
                            frag.coletado = True
                            frag.kill()
                            Musica_tema_Boss1.stop()
                            salvar_atributos()
                            pausar_cronometro()
                            if game_manager:
                                from game_manager import EstadoJogo
                                game_manager.mudar_estado(EstadoJogo.JOGO_FASE_2)
                                raise CleanExit()
                            else:
                                import GAME2
                                GAME2.executar_jogo()
                                raise CleanExit()

                # Barra de vida do boss (só se vivo e morte não processada)
                if vida_boss > 0 and not boss_morte_processada:
                    pygame.draw.rect(tela, vermelho, (pos_x_barra_boss, pos_y_barra_boss, largura_barra_boss, altura_barra_boss))
                    pygame.draw.rect(tela, (143,33,252), (pos_x_barra_boss, pos_y_barra_boss, largura_barra_boss, (vida_boss / vida_maxima_boss1) * altura_barra_boss))
                    pygame.draw.rect(tela, (255, 255, 255), (pos_x_barra_boss, pos_y_barra_boss, largura_barra_boss, altura_barra_boss), 2)




                # Disparos contra o boss (só se não morreu)
                if not boss_morte_processada:
                    for disparo in disparos:
                        pos_x_disparo=disparo["rect"].x 
                        pos_y_disparo=disparo["rect"].y 
                        rect_disparo = pygame.Rect(pos_x_disparo, pos_y_disparo, largura_disparo, altura_disparo)
                        rect_boss = pygame.Rect(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura)

                        if rect_disparo.colliderect(rect_boss):
                            if vida_boss > 0:  # Verifica se o chefe está vivo antes de aplicar dano
                                if random.random() <= chance_critico:  # 10% de chance de dano crítico
                                    dano = dano_person_hit * 3  # Valor do dano crítico é 3 vezes o dano normal
                                    cor = (255, 255, 0)  # Amarelo (RGB)
                                    fonte_dano = fonte_dano_critico
                                else:
                                    dano = dano_person_hit
                                    cor = (255, 0, 0)  # Vermelho (RGB)
                                    fonte_dano = fonte_dano_normal

                            # Ativar veneno no Boss com 50% de chance, se ainda não estiver envenenado
                            if not boss_envenenado and Poison_Active:
                                boss_envenenado = True
                                dano_por_tick_veneno_boss = vida_boss * (Dano_Veneno_Acumulado / 100)
                                tempo_inicio_veneno_boss = pygame.time.get_ticks()
                                ultimo_tick_veneno_boss = pygame.time.get_ticks()

                            # Renderizar texto do dano
                            texto_dano = fonte_dano.render("-" + str(int(dano)), True, cor)
                            pos_texto = (pos_x_chefe + chefe_largura // 2 - texto_dano.get_width() // 2, pos_y_chefe - 20)
                            tempo_texto_dano = pygame.time.get_ticks()
                            vida_boss -= dano
                            disparos.remove(disparo)

                            # Roubo de vida
                            if random.random() < roubo_de_vida:
                                vida += (vida_maxima - vida) * quantidade_roubo_vida

                # Aplicar dano de veneno no Boss se ele estiver envenenado (só se não morreu)
                if boss_envenenado and not boss_morte_processada:
                    tempo_atual = pygame.time.get_ticks()

                    # Aplicar dano a cada 500 ms
                    if tempo_atual - ultimo_tick_veneno_boss >= 500:
                        vida_boss -= dano_por_tick_veneno_boss
                        ultimo_tick_veneno_boss = tempo_atual

                    # Exibir texto do dano de veneno (1.5 segundos)
                    if tempo_atual - ultimo_tick_veneno_boss <= 250:
                        dano_veneno_texto = "-" + str(int(dano_por_tick_veneno_boss))
                        texto_dano_veneno = fonte_veneno.render(dano_veneno_texto, True, (0, 255, 0))
                        texto_dano_veneno_borda = fonte_veneno.render(dano_veneno_texto, True, (0, 0, 0))
                        pos_texto = (pos_x_chefe + chefe_largura // 2 - texto_dano_veneno.get_width() // 2, pos_y_chefe - 30)
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0] - 1, pos_texto[1]))
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0] + 1, pos_texto[1]))
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0], pos_texto[1] - 1))
                        tela.blit(texto_dano_veneno_borda, (pos_texto[0], pos_texto[1] + 1))
                        tela.blit(texto_dano_veneno, pos_texto)

                    # Desativar o veneno após o tempo de duração
                    if tempo_atual - tempo_inicio_veneno_boss >= duracao_veneno_boss:
                        boss_envenenado = False
                # Colisão e renderização do boss (só se vivo e morte não processada)
                if boss_vivo1 and not boss_morte_processada:
                    rect_boss = pygame.Rect(pos_x_chefe, pos_y_chefe, 200, 100)

                    rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)

                    if rect_boss.colliderect(rect_personagem):
                        # Verifique se tempo suficiente passou desde o último ataque
                        tempo_atual = pygame.time.get_ticks()
                        if tempo_atual - tempo_ultimo_ataque >= 2500:
                            dano_boss_total=int((vida_maxima*0.10)+150+dano_boss)
                            if escudo_devota_ativo:
                                escudo_devota_ativo= False
                                pass
                            elif Resistencia < dano_boss_total:
                                vida -= int(dano_boss_total-Resistencia)
                            else:
                                pass
                            Dano_person.play()
                            piscando_vida = True
                            # Atualize o tempo do último ataque
                            tempo_ultimo_ataque = tempo_atual

                    porcentagem_vida_boss = (vida_boss / vida_maxima_boss1) * 100

                    # Gatilho de mudança de estágio/fase (menos de 60% e menos de 40%)
                    if porcentagem_vida_boss < 60 and not boss_estagio_60_ativado:
                        boss_estagio_60_ativado = True
                        tempo_boss_estagio_ataque_fim = tempo_atual + 6000
                        ondas_lancadas_transicao = 0
                        ultima_onda_tipo = ""
                        tempo_slow_onda_fim = 0
                        boss_transicao_ondas = []
                    elif porcentagem_vida_boss < 40 and not boss_estagio_40_ativado:
                        boss_estagio_40_ativado = True
                        tempo_boss_estagio_ataque_fim = tempo_atual + 6000
                        ondas_lancadas_transicao = 0
                        ultima_onda_tipo = ""
                        tempo_slow_onda_fim = 0
                        boss_transicao_ondas = []

                    if porcentagem_vida_boss >= 60:
                        frame_porcentagem = frames_chefe1_1
                    elif 40 <= porcentagem_vida_boss < 60:
                        frame_porcentagem = frames_chefe1_2
                    else:
                        frame_porcentagem = frames_chefe1_3
                        intervalo_mudanca_direcao_boss -= 500

                    # Efeitos visuais de entrada do boss (portal e sombra)
                    if tempo_atual < tempo_boss_entrada_fim:
                        progresso = (tempo_atual - (tempo_boss_entrada_fim - 2500)) / 2500.0
                        target_y = altura_mapa // 2 - chefe_altura // 2
                        
                        # Desenha portal cósmico no chão
                        portal_radius = int(chefe_largura * 0.7 * (1.0 + 0.1 * math.sin(tempo_atual * 0.01)))
                        portal_surf = pygame.Surface((portal_radius * 2, portal_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(portal_surf, (20, 0, 40, 120), (portal_radius, portal_radius), portal_radius)
                        pygame.draw.circle(portal_surf, (150, 0, 255, 180), (portal_radius, portal_radius), int(portal_radius * 0.8), 5)
                        pygame.draw.circle(portal_surf, (0, 200, 255, 220), (portal_radius, portal_radius), int(portal_radius * 0.5), 3)
                        # Linhas do portal girando
                        for angle_deg in range(0, 360, 45):
                            rad = math.radians(angle_deg + tempo_atual * 0.05)
                            sx = portal_radius + math.cos(rad) * portal_radius * 0.3
                            sy = portal_radius + math.sin(rad) * portal_radius * 0.3
                            ex = portal_radius + math.cos(rad) * portal_radius * 0.9
                            ey = portal_radius + math.sin(rad) * portal_radius * 0.9
                            pygame.draw.line(portal_surf, (255, 100, 255, 200), (sx, sy), (ex, ey), 4)
                        tela.blit(portal_surf, (largura_mapa // 2 - portal_radius, target_y + chefe_altura // 2 - portal_radius))
                        
                        # Desenha sombra do boss se caindo
                        if progresso < 0.8:
                            shadow_surf = pygame.Surface((int(chefe_largura), int(chefe_altura // 2)), pygame.SRCALPHA)
                            pygame.draw.ellipse(shadow_surf, (0, 0, 0, int(150 * (progresso / 0.8))), (0, 0, shadow_surf.get_width(), shadow_surf.get_height()))
                            tela.blit(shadow_surf, (largura_mapa // 2 - shadow_surf.get_width() // 2, target_y + chefe_altura // 2 - shadow_surf.get_height() // 2))
                    
                    # Desenhar sombra sob o boss pulando na transição
                    elif tempo_atual < tempo_boss_estagio_ataque_fim:
                        tempo_decorrido = 6000 - (tempo_boss_estagio_ataque_fim - tempo_atual)
                        if tempo_decorrido < 4800:
                            ciclo = tempo_decorrido % 1200
                            altura_pulo = abs(math.sin(math.pi * ciclo / 1200))
                            sombra_fator = 1.0 - (altura_pulo * 0.5)
                            shadow_w = int(chefe_largura * sombra_fator)
                            shadow_h = int((chefe_altura // 2) * sombra_fator)
                            shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
                            pygame.draw.ellipse(shadow_surf, (0, 0, 0, int(150 * sombra_fator)), (0, 0, shadow_w, shadow_h))
                            tela.blit(shadow_surf, (pos_x_chefe + chefe_largura // 2 - shadow_w // 2, pos_y_chefe + chefe_altura // 2 - shadow_h // 2))

                    # Determinar Y com offsets
                    desenho_y = pos_y_chefe
                    if tempo_atual < tempo_boss_estagio_ataque_fim and tempo_atual >= tempo_boss_entrada_fim:
                        tempo_decorrido = 6000 - (tempo_boss_estagio_ataque_fim - tempo_atual)
                        if tempo_decorrido < 4800:
                            ciclo = tempo_decorrido % 1200
                            desenho_y += -abs(math.sin(math.pi * ciclo / 1200) * 120)

                    # Renderizar sprite do boss SOMENTE se vivo
                    tela.blit(frame_porcentagem[frame_atual_chefe], (pos_x_chefe, desenho_y))

                    # Efeitos de entrada pós-impacto (ondas de choque e título)
                    if tempo_atual < tempo_boss_entrada_fim:
                        progresso = (tempo_atual - (tempo_boss_entrada_fim - 2500)) / 2500.0
                        target_y = altura_mapa // 2 - chefe_altura // 2
                        
                        if progresso >= 0.8:
                            fator_impacto = (progresso - 0.8) / 0.2
                            shock_r = int(chefe_largura * 0.6 + fator_impacto * 600)
                            pygame.draw.circle(tela, (255, 255, 255, int(255 * (1.0 - fator_impacto))), (int(largura_mapa // 2), int(target_y + chefe_altura // 2)), shock_r, 6)
                            pygame.draw.circle(tela, (0, 191, 255, int(180 * (1.0 - fator_impacto))), (int(largura_mapa // 2), int(target_y + chefe_altura // 2)), int(shock_r * 0.8), 4)
                        
                        # Nome do Boss em destaque
                        font_boss = pygame.font.Font(None, 64)
                        text_glow = font_boss.render("CARANGUEJO CÓSMICO GIGANTE", True, (150, 0, 255))
                        text_main = font_boss.render("CARANGUEJO CÓSMICO GIGANTE", True, (255, 255, 255))
                        tx = largura_tela // 2 - text_main.get_width() // 2
                        ty = altura_tela // 4
                        for ox, oy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
                            tela.blit(text_glow, (tx + ox, ty + oy))
                        tela.blit(text_main, (tx, ty))

            for inimigo in inimigos_comum:
                inimigo_rect = inimigo["rect"]
                inimigo_image = inimigo["image"]

                inimigo_atingido = False

                for disparo in disparos:

                    if verificar_colisao_disparo_inimigo(disparo, (inimigo["rect"].x, inimigo["rect"].y), largura_disparo, altura_disparo, largura_inimigo, altura_inimigo, inimigos_eliminados):

                        if random.random() <= chance_critico:  # chance de dano crítico
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
                        # Adicionar uma chance de 50% de aumentar a vida em 20 pontos

                        if random.random() < roubo_de_vida:
                            vida += (vida_maxima-vida)*quantidade_roubo_vida

                        if Poison_Active:
                            inimigo["veneno"] = {
                                "dano_por_tick": inimigo["vida_maxima"] * Dano_Veneno_Acumulado,  # 0.5% da vida máxima
                                "tempo_inicio": pygame.time.get_ticks(),
                                "duracao": 4000,  # 4 segundos
                                "ultimo_tick": pygame.time.get_ticks(),  # Tempo do último tick
                                "posicao_texto": (inimigo["rect"].x, inimigo["rect"].y - 20),  # Posição inicial do texto
                                "tempo_texto_dano": pygame.time.get_ticks()  # Tempo de exibição do texto
                                }

                            # Dentro do loop principal, fora do loop de verificação de disparo


                        if Ultimo_Estalo and inimigo["vida"] <= Executa_inimigo * inimigo["vida_maxima"]:
                            estalos.play()
                            posicao_inimigo = inimigo["rect"].center
                            soltar_moeda(posicao_inimigo)
                            if inimigo in inimigos_comum:
                                gerar_fragmentos_morte(inimigo, 1)
                                inimigos_comum.remove(inimigo)

                            inimigos_eliminados += 1
                            mult_exec = 1.0 + (nivel_ameaca * 0.12) # Execução dá 12% a mais de escala

                            vida_inimigo_maxima += 0.6 * mult_exec
                            Resistencia_petro += 0.07 * mult_exec
                            dano_inimigo_perto += 0.05 * mult_exec
                            vida_maxima_petro += 0.3 * mult_exec
                            dano_petro += 0.006 * mult_exec
                            dano_inimigo_longe += 0.015 * mult_exec
                            dano_boss += 0.015 * mult_exec
                            Dano_Boss_Habilit += 0.02 * mult_exec
                            Velocidade_Inimigos_1 = min(4.8, Velocidade_Inimigos_1 + 0.0001)

                            ganho_pontos = int(150 * (1 + math.log10(inimigos_eliminados + 1)))
                            pontuacao += ganho_pontos
                            eliminacoes_consecutivas_impulsiva += 1

                            if Mercenaria_Active:
                                eliminacoes_consecutivas += 1
                                # Bônus mercenário fixo para evitar inflação infinita
                                pontuacao_exib += ganho_pontos + bonus_pontuacao
                                if eliminacoes_consecutivas % 5 == 0:
                                    bonus_pontuacao = min(500, bonus_pontuacao + Valor_Bonus) 
                            else:
                                pontuacao_exib += ganho_pontos

                            if not boss_vivo1:
                                vida_boss += 15 * mult_exec
                                vida_maxima_boss1 = vida_boss
                                vida_boss2 += 20 * mult_exec
                                vida_maxima_boss2 = vida_boss2
                                vida_boss3 += 25 * mult_exec
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += 30 * mult_exec
                                vida_maxima_boss4 = vida_boss4

                        elif inimigo["vida"] <= 0:
                            posicao_inimigo = inimigo["rect"].center
                            soltar_moeda(posicao_inimigo)
                            gerar_fragmentos_morte(inimigo, 1)
                            inimigos_comum.remove(inimigo)

                            # Crescimento proporcional por nível de ameaça
                            vida_inimigo_maxima += 1.2 + nivel_ameaca * 0.8
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

                            # Pontuação com escala suave
                            ganho = int(75 + math.log2(inimigos_eliminados + 1) * 4)
                            pontuacao += ganho
                            eliminacoes_consecutivas_impulsiva += 1
                            if Mercenaria_Active:
                                eliminacoes_consecutivas += 1
                                pontuacao_exib += ganho + bonus_pontuacao
                                if eliminacoes_consecutivas % 5 == 0:
                                    bonus_pontuacao += Valor_Bonus
                            else:
                                pontuacao_exib += ganho

                            # Boss: aumento escalonado
                            if not boss_vivo1:
                                if vida_boss > 0:
                                    vida_boss += 15 + nivel_ameaca * 10
                                    vida_maxima_boss1 = vida_boss
                                    vida_boss2 += 20 + nivel_ameaca * 12
                                    vida_maxima_boss2 = vida_boss2
                                    vida_boss3 += 25 + nivel_ameaca * 15
                                    vida_maxima_boss3 = vida_boss3
                                    vida_boss4 += 30 + nivel_ameaca * 18
                                    vida_maxima_boss4 = vida_boss4




                            break  # Sai do loop interno para evitar problemas ao modificar a lista enquanto iteramos sobre ela

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





            total_cartas_compradas = sum(cartas_compradas.values())
            custo_carta_atual = custo_base_carta + (total_cartas_compradas * custo_por_carta)
            # Verifica se a pontuação atingiu o custo e se o jogador pressionou o botão da loja
            if (pontuacao_exib >= custo_carta_atual) and (Variaveis.verificar_input("Comprar na loja") or (joystick and joystick.get_button(3))):
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
                    apertou_q = True

                    pausar_cronometro()
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
                retomar_cronometro()


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
                # Verifica se o personagem está passando pelo centro da tela e se a mensagem ainda não foi mostrada
            if False:


                # Renderiza o texto
                texto_renderizado = fonte.render(mensagem, True, (0,0,0))
                # Obtém o retângulo do texto
                texto_rect = texto_renderizado.get_rect()
                # Define a posição do texto para que ele fique no centro da tela
                texto_rect.center = (centro_x_tela_pequena, centro_y_tela_pequena)

                # Calcula as dimensões do retângulo de fundo da mensagem
                largura_fundo = texto_rect.width + 20  # Adiciona um espaço de 10 pixels de cada lado
                altura_fundo = texto_rect.height + 20  # Adiciona um espaço de 10 pixels em cima e embaixo
                # Cria um retângulo branco para o fundo da mensagem
                fundo_rect = pygame.Rect((centro_x_tela_pequena - largura_fundo // 2, centro_y_tela_pequena - altura_fundo // 2), (largura_fundo, altura_fundo))
                # Desenha o retângulo branco na tela
                pygame.draw.rect(tela, (225, 255, 255), fundo_rect)
                # Desenha o texto na tela
                tela.blit(texto_renderizado, texto_rect) 

                # Incrementa o tempo que a mensagem está sendo mostrada
                tempo_mostrando_mensagem += 1

                # Se a mensagem estiver sendo mostrada por mais de 3 segundos
                if tempo_mostrando_mensagem > 420:  # 60 frames por segundo * 3 segundos = 180
                    mensagem_mostrada = False  # Define que a mensagem foi mostrada
                    tempo_mostrando_mensagem = 0  # Reinicia o contador de tempo

            # Remova o texto após 2 segundos
            if texto_dano is not None and pygame.time.get_ticks() - tempo_texto_dano >= 250:
                texto_dano = None

            cooldowns = {
                "disparo": max(0.0, (intervalo_disparo - (tempo_atual - tempo_ultimo_disparo)) / 1000.0),
                "teleporte": max(0.0, (tempo_cooldown_dash - (pygame.time.get_ticks() - tempo_ultimo_dash)) / 1000.0),
                "onda": max(0.0, (cooldown_habilidade - (tempo_atual - tempo_ultimo_uso_habilidade)) / 1000.0),
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
                posicao_combo = (largura_mapa - 170, 50)  
                desenhar_texto_com_contorno(tela, texto_combo, fonte_combo, (255, 255, 255), (0, 0, 0), posicao_combo)

                # Texto do bônus
                texto_bonus = f"Bônus: +{bonus_pontuacao}"
                posicao_bonus = (largura_mapa - 200, 90)  
                desenhar_texto_com_contorno(tela, texto_bonus, fonte_bonus, (255, 255, 255), (0, 0, 0), posicao_bonus)

            # Desenhe o texto na tela
            if texto_dano is not None:
                tela.blit(texto_dano, pos_texto)
            # Controle de exibição
            if mostrar_tutorial:
                # Desenhar a barreira roxa se estiver ativa, ANTES de desenhar o painel de glassmorphism e as legendas
                # Isso garante que a legenda e o painel fiquem por cima e não fiquem escondidos sob a barreira
                if tutorial_parede_ativa and tutorial_parede_rect:
                    pulso = abs(pygame.time.get_ticks() % 800 - 400) / 400.0
                    r_val = int(140 + 40 * pulso)
                    parede_surf = pygame.Surface((tutorial_parede_rect.width, tutorial_parede_rect.height), pygame.SRCALPHA)
                    parede_surf.fill((r_val, 40, 200, 180))
                    tela.blit(parede_surf, tutorial_parede_rect.topleft)
                    pygame.draw.rect(tela, (200, 80, 255), tutorial_parede_rect, 2)

                cx = largura_mapa // 2
                y_msg = int(altura_mapa * 0.15)
                fonte_tut = pygame.font.Font(None, 48)

                # Definir dimensões do painel de informações com base na fase do tutorial para enquadrar perfeitamente
                w, h = 600, 160  # padrão
                if tutorial_fase == 1:
                    w, h = 580, 150
                elif tutorial_fase == 2:
                    w, h = 720, 185
                elif tutorial_fase == 3:
                    w, h = 680, 115
                elif tutorial_fase == 4:
                    w, h = 720, 190
                elif tutorial_fase == 5:
                    w, h = 720, 160
                elif tutorial_fase == 6:
                    w, h = 720, 180

                # Painel com efeito de vidro (glassmorphism) e brilho neon nas bordas
                card_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                
                # Fundo escuro semi-transparente para dar alto contraste sobre o chão cinza/roxo/preto
                pygame.draw.rect(card_surf, (12, 10, 18, 220), (0, 0, w, h), border_radius=15)
                
                # Borda neon pulsante
                pulso_borda = abs(pygame.time.get_ticks() % 2000 - 1000) / 1000.0
                # Cor pulsante combinando violeta neon com ciano neural/plasma do jogo
                cor_borda = (
                    int(130 + 80 * pulso_borda),
                    int(30 + 150 * (1 - pulso_borda)),
                    255
                )
                pygame.draw.rect(card_surf, cor_borda, (0, 0, w, h), width=2, border_radius=15)
                
                # Blit do painel na tela
                tela.blit(card_surf, (cx - w // 2, y_msg - 20))

                # --- Função auxiliar para desenhar texto com contorno ---
                def _draw_msg(txt, y_pos):
                    tr = fonte_tut.render(txt, True, (255, 255, 255))
                    tb = fonte_tut.render(txt, True, (0, 0, 0))
                    xm = cx - tr.get_width() // 2
                    tela.blit(tb, (xm - 1, y_pos))
                    tela.blit(tb, (xm + 1, y_pos))
                    tela.blit(tb, (xm, y_pos - 1))
                    tela.blit(tb, (xm, y_pos + 1))
                    tela.blit(tr, (xm, y_pos))

                # ====== FASE 1: WASD ======
                if tutorial_fase == 1:
                    _draw_msg("Use W, A, S e D para se mover", y_msg)

                    # Teclas WASD flutuantes
                    tam = 32
                    esp = 5
                    tecla_y = y_msg + 50
                    posicoes = [
                        ('W', cx - tam // 2, tecla_y, tutorial_wasd['w']),
                        ('A', cx - tam - tam // 2 - esp, tecla_y + tam + esp, tutorial_wasd['a']),
                        ('S', cx - tam // 2, tecla_y + tam + esp, tutorial_wasd['s']),
                        ('D', cx + tam // 2 + esp, tecla_y + tam + esp, tutorial_wasd['d']),
                    ]
                    ft_k = pygame.font.Font(None, 24)
                    pulso = abs(pygame.time.get_ticks() % 1200 - 600) / 600.0
                    for letra, kx, ky, ok in posicoes:
                        if ok:
                            cor_bg = (20, 120, 200, 220)
                            cor_bd = (53, 200, 252)
                        else:
                            alpha = int(100 + 60 * pulso)
                            cor_bg = (20, 30, 50, alpha)
                            cor_bd = (int(53 + 80 * pulso), int(100 + 60 * pulso), 200)
                        ks = pygame.Surface((tam, tam), pygame.SRCALPHA)
                        ks.fill(cor_bg)
                        tela.blit(ks, (kx, ky))
                        pygame.draw.rect(tela, cor_bd, (kx, ky, tam, tam), 2)
                        txt = ft_k.render(letra, True, (255, 255, 255))
                        tela.blit(txt, (kx + tam // 2 - txt.get_width() // 2, ky + tam // 2 - txt.get_height() // 2))

                # ====== FASE 2: SHIFT / Teleporte ======
                elif tutorial_fase == 2:
                    _draw_msg("Aperte SHIFT para teleportar!", y_msg)
                    fonte_sub = pygame.font.Font(None, 32)
                    # Subtexto 1 com contraste (Sky Blue)
                    t1 = "O teleporte vai na direção da última tecla apertada"
                    sub1_b = fonte_sub.render(t1, True, (0, 0, 0))
                    sub1 = fonte_sub.render(t1, True, (170, 240, 255))
                    tela.blit(sub1_b, (cx - sub1.get_width() // 2 + 1, y_msg + 46))
                    tela.blit(sub1, (cx - sub1.get_width() // 2, y_msg + 45))
                    # Subtexto 2 com contraste (Sky Blue)
                    t2 = f"Use para se reposicionar! ({tutorial_dash_count}/3)"
                    sub2_b = fonte_sub.render(t2, True, (0, 0, 0))
                    sub2 = fonte_sub.render(t2, True, (170, 240, 255))
                    tela.blit(sub2_b, (cx - sub2.get_width() // 2 + 1, y_msg + 76))
                    tela.blit(sub2, (cx - sub2.get_width() // 2, y_msg + 75))

                    # Desenhar tecla SHIFT pulsando
                    pulso = abs(pygame.time.get_ticks() % 1200 - 600) / 600.0
                    shift_w, shift_h = 80, 32
                    sx = cx - shift_w // 2
                    sy = y_msg + 110
                    alpha = int(100 + 60 * pulso)
                    ss = pygame.Surface((shift_w, shift_h), pygame.SRCALPHA)
                    ss.fill((20, 30, 50, alpha))
                    tela.blit(ss, (sx, sy))
                    cor_bd = (int(53 + 80 * pulso), int(100 + 60 * pulso), 200)
                    pygame.draw.rect(tela, cor_bd, (sx, sy, shift_w, shift_h), 2)
                    ft_s = pygame.font.Font(None, 24)
                    st = ft_s.render("SHIFT", True, (255, 255, 255))
                    tela.blit(st, (sx + shift_w // 2 - st.get_width() // 2, sy + shift_h // 2 - st.get_height() // 2))

                # ====== FASE 3: Parede Roxa ======
                elif tutorial_fase == 3:
                    _draw_msg("Atravesse a barreira usando o teleporte!", y_msg)
                    fonte_sub = pygame.font.Font(None, 32)
                    t_sub = "Você não pode passar andando, apenas teleportando"
                    sub_b = fonte_sub.render(t_sub, True, (0, 0, 0))
                    sub = fonte_sub.render(t_sub, True, (170, 240, 255))
                    tela.blit(sub_b, (cx - sub.get_width() // 2 + 1, y_msg + 46))
                    tela.blit(sub, (cx - sub.get_width() // 2, y_msg + 45))

                    # Desenhar a parede roxa (movido para o topo do bloco mostrar_tutorial)
                    if tutorial_parede_ativa and tutorial_parede_rect:
                        # Verificar se o personagem cruzou pro outro lado
                        centro_parede_x = tutorial_parede_rect.centerx
                        personagem_rect_tut = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                        if not personagem_rect_tut.colliderect(tutorial_parede_rect):
                            lado_atual = 'direita' if pos_x_personagem > centro_parede_x else 'esquerda'
                            if tutorial_lado_inicial is None:
                                tutorial_lado_inicial = lado_atual
                            elif lado_atual != tutorial_lado_inicial:
                                tutorial_fase = 4
                                tutorial_parede_ativa = False
                                tempo_fase_completa = time.time()
                                # Criar inimigo do tutorial de tiro
                                tutorial_inimigo_ativo = True
                                # Posicionar o inimigo à frente do jogador
                                tut_inimigo_x = max(50, min(largura_mapa - largura_inimigo - 50, pos_x_personagem + 200))
                                tut_inimigo_y = max(50, min(altura_mapa - altura_inimigo - 50, pos_y_personagem))
                                tutorial_inimigo = criar_inimigo(int(tut_inimigo_x), int(tut_inimigo_y))
                                tutorial_inimigo["vida"] = dano_person_hit * 4  # precisa de 4 disparos
                                tutorial_inimigo["vida_maxima"] = dano_person_hit * 4

                # ====== FASE 4: Atirar no inimigo ======
                elif tutorial_fase == 4:
                    _draw_msg("Clique com o botão esquerdo do mouse para atirar!", y_msg)
                    fonte_sub = pygame.font.Font(None, 32)
                    t_sub = "Elimine o inimigo para continuar"
                    sub_b = fonte_sub.render(t_sub, True, (0, 0, 0))
                    sub = fonte_sub.render(t_sub, True, (170, 240, 255))
                    tela.blit(sub_b, (cx - sub.get_width() // 2 + 1, y_msg + 46))
                    tela.blit(sub, (cx - sub.get_width() // 2, y_msg + 45))

                    # Desenhar ícone do mouse pulsando
                    pulso = abs(pygame.time.get_ticks() % 1200 - 600) / 600.0
                    mouse_icon_w, mouse_icon_h = 40, 50
                    mx_icon = cx - mouse_icon_w // 2
                    my_icon = y_msg + 80
                    ms = pygame.Surface((mouse_icon_w, mouse_icon_h), pygame.SRCALPHA)
                    alpha_m = int(100 + 60 * pulso)
                    ms.fill((20, 30, 50, alpha_m))
                    tela.blit(ms, (mx_icon, my_icon))
                    cor_bd_m = (int(53 + 80 * pulso), int(100 + 60 * pulso), 200)
                    pygame.draw.rect(tela, cor_bd_m, (mx_icon, my_icon, mouse_icon_w, mouse_icon_h), 2)
                    # Linha divisória vertical no ícone do mouse
                    pygame.draw.line(tela, cor_bd_m, (mx_icon + mouse_icon_w // 2, my_icon), (mx_icon + mouse_icon_w // 2, my_icon + mouse_icon_h // 2), 2)
                    # Destacar lado esquerdo do mouse
                    left_highlight = pygame.Surface((mouse_icon_w // 2, mouse_icon_h // 2), pygame.SRCALPHA)
                    left_highlight.fill((53, 200, 252, int(80 + 80 * pulso)))
                    tela.blit(left_highlight, (mx_icon, my_icon))
                    ft_lmb = pygame.font.Font(None, 20)
                    lmb_txt = ft_lmb.render("LMB", True, (255, 255, 255))
                    tela.blit(lmb_txt, (mx_icon + mouse_icon_w // 2 - lmb_txt.get_width() // 2, my_icon + mouse_icon_h + 5))

                    # Desenhar e gerenciar o inimigo do tutorial
                    if tutorial_inimigo_ativo and tutorial_inimigo is not None:
                        # Desenhar sombra e sprite do inimigo
                        tutorial_inimigo["image"] = frames_inimigo[frame_atual % len(frames_inimigo)]
                        desenhar_sombra(tela, tutorial_inimigo["rect"].x, tutorial_inimigo["rect"].y, largura_inimigo, altura_inimigo)
                        tela.blit(tutorial_inimigo["image"], tutorial_inimigo["rect"])
                        desenhar_barra_de_vida(tela, tutorial_inimigo["rect"].x, tutorial_inimigo["rect"].y - 10, largura_inimigo, 5, tutorial_inimigo["vida"], tutorial_inimigo["vida_maxima"], tutorial_inimigo.get("eletrocutado", False))

                        # Seta indicadora pulsando apontando para o inimigo
                        seta_pulso = abs(pygame.time.get_ticks() % 1000 - 500) / 500.0
                        seta_y_offset = int(10 * seta_pulso)
                        seta_x = tutorial_inimigo["rect"].x + largura_inimigo // 2
                        seta_y = tutorial_inimigo["rect"].y - 30 - seta_y_offset
                        pygame.draw.polygon(tela, (255, 80, 80), [
                            (seta_x, seta_y + 15),
                            (seta_x - 8, seta_y),
                            (seta_x + 8, seta_y)
                        ])

                        # Verificar colisão dos disparos com o inimigo do tutorial
                        for disparo in disparos[:]:
                            if disparo["rect"].colliderect(tutorial_inimigo["rect"]):
                                tutorial_inimigo["vida"] -= dano_person_hit
                                if disparo in disparos:
                                    disparos.remove(disparo)
                                Hit_inimigo1.play()

                                if tutorial_inimigo["vida"] <= 0:
                                    gerar_fragmentos_morte(tutorial_inimigo, 1)
                                    tutorial_inimigo_ativo = False
                                    tutorial_inimigo = None
                                    tutorial_fase = 5
                                    tempo_fase_completa = time.time()
                                    break

                # ====== FASE 5: Ensinar a loja (Q) ======
                elif tutorial_fase == 5:
                    # Garantir que o jogador tenha pontos suficientes para comprar
                    total_cartas_temp = sum(cartas_compradas.values())
                    custo_temp = custo_base_carta + (total_cartas_temp * custo_por_carta)
                    if pontuacao_exib < custo_temp:
                        pontuacao_exib = custo_temp
                        pontuacao = pontuacao_exib

                    _draw_msg("Aperte Q para abrir a loja e comprar uma carta!", y_msg)
                    fonte_sub = pygame.font.Font(None, 32)
                    t_sub = "Use seus pontos para ficar mais forte"
                    sub_b = fonte_sub.render(t_sub, True, (0, 0, 0))
                    sub = fonte_sub.render(t_sub, True, (170, 240, 255))
                    tela.blit(sub_b, (cx - sub.get_width() // 2 + 1, y_msg + 46))
                    tela.blit(sub, (cx - sub.get_width() // 2, y_msg + 45))

                    # Desenhar tecla Q pulsando
                    pulso = abs(pygame.time.get_ticks() % 1200 - 600) / 600.0
                    q_w, q_h = 40, 40
                    qx = cx - q_w // 2
                    qy = y_msg + 80
                    alpha_q = int(100 + 60 * pulso)
                    qs = pygame.Surface((q_w, q_h), pygame.SRCALPHA)
                    qs.fill((20, 30, 50, alpha_q))
                    tela.blit(qs, (qx, qy))
                    cor_bd_q = (int(53 + 80 * pulso), int(100 + 60 * pulso), 200)
                    pygame.draw.rect(tela, cor_bd_q, (qx, qy, q_w, q_h), 2)
                    ft_q = pygame.font.Font(None, 28)
                    qt = ft_q.render("Q", True, (255, 255, 255))
                    tela.blit(qt, (qx + q_w // 2 - qt.get_width() // 2, qy + q_h // 2 - qt.get_height() // 2))

                    # Quando o jogador comprar (apertou_q fica True), o tutorial avança para o summon
                    if apertou_q:
                        tutorial_fase = 6
                elif tutorial_fase == 6:
                    _draw_msg("Aperte R para chamar o Boss quando achar pronto!", y_msg)
                    fonte_sub = pygame.font.Font(None, 28)
                    t1 = "Você pode chamar o Boss apertando R a qualquer momento."
                    sub1_b = fonte_sub.render(t1, True, (0, 0, 0))
                    sub1 = fonte_sub.render(t1, True, (170, 240, 255))
                    tela.blit(sub1_b, (cx - sub1.get_width() // 2 + 1, y_msg + 46))
                    tela.blit(sub1, (cx - sub1.get_width() // 2, y_msg + 45))

                    t2 = "Recomendamos ficar forte com upgrades antes de invocar."
                    sub2_b = fonte_sub.render(t2, True, (0, 0, 0))
                    sub2 = fonte_sub.render(t2, True, (170, 240, 255))
                    tela.blit(sub2_b, (cx - sub2.get_width() // 2 + 1, y_msg + 71))
                    tela.blit(sub2, (cx - sub2.get_width() // 2, y_msg + 70))

                    t3 = "Aperte ENTER/ESPAÇO para começar ou R para summonar agora."
                    sub3_b = fonte_sub.render(t3, True, (0, 0, 0))
                    sub3 = fonte_sub.render(t3, True, (170, 240, 255))
                    tela.blit(sub3_b, (cx - sub3.get_width() // 2 + 1, y_msg + 96))
                    tela.blit(sub3, (cx - sub3.get_width() // 2, y_msg + 95))

                    # Desenhar tecla R pulsando
                    pulso = abs(pygame.time.get_ticks() % 1200 - 600) / 600.0
                    r_w, r_h = 40, 40
                    rx = cx - r_w // 2
                    ry = y_msg + 120
                    alpha_r = int(100 + 60 * pulso)
                    rs = pygame.Surface((r_w, r_h), pygame.SRCALPHA)
                    rs.fill((20, 30, 50, alpha_r))
                    tela.blit(rs, (rx, ry))
                    cor_bd_r = (int(53 + 80 * pulso), int(100 + 60 * pulso), 200)
                    pygame.draw.rect(tela, cor_bd_r, (rx, ry, r_w, r_h), 2)
                    ft_r = pygame.font.Font(None, 28)
                    rt = ft_r.render("R", True, (255, 255, 255))
                    tela.blit(rt, (rx + r_w // 2 - rt.get_width() // 2, ry + r_h // 2 - rt.get_height() // 2))
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
            atualizar_e_desenhar_fragmentos(tela)
            atualizar_e_desenhar_particulas_pontos(tela)

            # Atualizar e desenhar FragmentoTemporal (coletável do boss)
            grupo_fragmentos.update()
            for frag in grupo_fragmentos:
                frag.draw(tela)

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



            # A cada 1300 inimigos eliminados, avisa por 3s que R chama o Boss
            if inimigos_eliminados > 0 and inimigos_eliminados % 1300 == 0:
                if alerta_boss_mostrado_para != inimigos_eliminados:
                    alerta_boss_ativo = True
                    tempo_inicio_alerta_boss = pygame.time.get_ticks()
                    alerta_boss_mostrado_para = inimigos_eliminados

            if alerta_boss_ativo:
                if pygame.time.get_ticks() - tempo_inicio_alerta_boss >= 3000:
                    alerta_boss_ativo = False
                else:
                    # Painel de notificação com efeito de vidro
                    w_n, h_n = 700, 100
                    cx_n = largura_mapa // 2
                    cy_n = altura_mapa // 2
                    card_n = pygame.Surface((w_n, h_n), pygame.SRCALPHA)
                    pygame.draw.rect(card_n, (20, 10, 12, 235), (0, 0, w_n, h_n), border_radius=12)
                    pygame.draw.rect(card_n, (255, 60, 60), (0, 0, w_n, h_n), width=2, border_radius=12)
                    tela.blit(card_n, (cx_n - w_n // 2, cy_n - h_n // 2))
                    
                    font_n = pygame.font.Font(None, 32)
                    msg_line1 = font_n.render("Aperte R para chamar o Boss quando achar pronto!", True, (255, 230, 230))
                    msg_line2 = font_n.render("Recomendável fazer isso quando estiver forte.", True, (255, 100, 100))
                    
                    tela.blit(msg_line1, (cx_n - msg_line1.get_width() // 2, cy_n - 30))
                    tela.blit(msg_line2, (cx_n - msg_line2.get_width() // 2, cy_n + 5))

            tela.blit(cursor_imagem, (mouse_x, mouse_y))
            exibir_cronometro(tela)

            # Aplica tremor de tela se necessário
            if shake_x != 0 or shake_y != 0:
                shake_temp = tela.copy()
                tela.fill((10, 5, 20))  # Cor cósmica escura de fundo
                tela.blit(shake_temp, (shake_x, shake_y))

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
