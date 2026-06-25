
import Caminhos
import pygame
import subprocess
import sys
import random
import math
import time
import os
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
import evolucoes_manifestacao
import ultimate_manifestacao
from estado_jogador_fases import carregar_estado_jogador, salvar_estado_jogador
from dados_manifestacoes import registrar_conclusao_fase
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
from Boss1_Ataques import gerenciador_ataques_boss1, desenhar_onda_transicao_premium
from boss_ui import desenhar_barra_vida_boss, registrar_dano_boss
import insana_aurea
import voraz_aurea
import aureas_avancadas
import multiplayer_coop
from balanceamento import limitar_dano_larapio

instalar_captura_global()
instalar_filtro_prints()


def tela_de_pausa(*args, **kwargs):
    if multiplayer_coop.modo_multiplayer():
        return tela_de_pausa_coop(*args, **kwargs)
    return tela_de_pausa_single(*args, **kwargs)

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
moedas_arremessadas = []

# Constantes do Larapio
TIPO_LARAPIO = 6
LARAPIO_SPAWN_APOS_SEG = 120
LARAPIO_CHANCE_MIN = 1.0
LARAPIO_MULT_REFERENCIA_PONTOS = 3.0
LARAPIO_TEMPO_COBICA_MAX_MS = 9000
LARAPIO_CHANCE_MAX = 1.0
LARAPIO_ALCANCE_ATAQUE = 65
LARAPIO_TEMPO_PREPARO_ATAQUE = 1000
LARAPIO_TEMPO_FUGA = 6500
LARAPIO_INTERVALO_ANIMACAO_FUGA = 80
LARAPIO_INTERVALO_ANIMACAO = 120
LARAPIO_COOLDOWN_SPAWN_MS = 120000
LARAPIO_FATOR_RIQUEZA_MAX = 2.5
LARAPIO_ARREMESSO_MIN_MS = 6500
LARAPIO_ARREMESSO_MAX_MS = 8000
custo_carta_atual = 100

# Forward declarations (atribuídos no loop principal)
botao_mouse = (False, False, False)
sprite_moeda = None
joystick = None
aurea = None
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

Musica_tema_Boss1 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase1_Boss.mp3"), config_audio, canal="musica")

Musica_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase_boas.mp3"), config_audio, canal="musica")

Som_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Praia.wav"), config_audio, canal="musica")

Som_portal = aplicar_volume_som(pygame.mixer.Sound("Sounds/Portal.mp3"), config_audio)

Dano_person = aplicar_volume_som(pygame.mixer.Sound("Sounds/hit_person.mp3"), config_audio)

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
    (11, "Colete recursos para fortalecer sua linha temporal"),
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
        velocidade_personagem = atributos.get("velocidade_personagem", velocidade_personagem)
        intervalo_disparo = atributos.get("intervalo_disparo", intervalo_disparo)
        dano_person_hit = atributos.get("dano_person_hit", dano_person_hit)
        chance_critico = atributos.get("chance_critico", chance_critico)
        roubo_de_vida = atributos.get("roubo_de_vida", roubo_de_vida)
        quantidade_roubo_vida = atributos.get("quantidade_roubo_vida", quantidade_roubo_vida)
        vida_petro = atributos.get("vida_petro", vida_petro)
        vida_maxima = atributos.get("vida_maxima_personagem", vida_maxima)
        vida_maxima_petro = atributos.get("vida_maxima_petro", vida_maxima_petro)
        vida = atributos.get("vida_atual_personagem", vida)
        xp_petro = atributos.get("nivel_Petro", xp_petro)
        Petro_active = atributos.get("existencia_petro", Petro_active)
        trembo = atributos.get("existencia_trembo", trembo)
        dano_petro = atributos.get("dano_petro", dano_petro)
        Resistencia = atributos.get("resistencia_personagem", Resistencia)
        Resistencia_petro = atributos.get("resistencia_petro", Resistencia_petro)
        dano_inimigo_longe = atributos.get("dano_inimigo_longe", dano_inimigo_longe)
        dano_inimigo_perto = atributos.get("dano_inimigo_perto", dano_inimigo_perto)
        Poison_Active = atributos.get("Poison_Active", Poison_Active)
        Ultimo_Estalo = atributos.get("Ultimo_Estalo", Ultimo_Estalo)
        Executa_inimigo = atributos.get("Executa_inimigo", Executa_inimigo)
        Mercenaria_Active = atributos.get("Mercenaria_Active", Mercenaria_Active)
        Valor_Bonus = atributos.get("Valor_Bonus", Valor_Bonus)
        tempo_cooldown_dash = atributos.get("tempo_cooldown_dash", tempo_cooldown_dash)
        petro_evolucao = atributos.get("petro_evolucao", petro_evolucao)
        Dano_Veneno_Acumulado = atributos.get("Dano_Veneno_Acumulado", Dano_Veneno_Acumulado)
        Tempo_cura = atributos.get("Tempo_cura", Tempo_cura)
        porcentagem_cura = atributos.get("porcentagem_cura", porcentagem_cura)
        moedas_totais = atributos.get("moedas_totais", moedas_totais)
        Chance_Sorte = atributos.get("Chance_Sorte", 0.0)
        largura_disparo = atributos.get("largura_disparo", largura_disparo)
        altura_disparo = atributos.get("altura_disparo", altura_disparo)
        if "cartas_compradas" in atributos:
            cartas_compradas.update(atributos["cartas_compradas"])
        cartas_compradas = normalizar_cartas_compradas(cartas_compradas)

        
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
    global moedas_arremessadas
    global aurea
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
        manifestacao_ativa = obter_manifestacao_ativa()
        estado_evolucao_manifestacao = evolucoes_manifestacao.criar_estado(manifestacao_ativa)

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

        # A fase offline precisa trocar imediatamente o frame que veio do menu.
        # DOUBLEBUF/vsync pode prender o primeiro flip em algumas maquinas Windows.
        tela = configurar_tela(largura_mapa, altura_mapa)
        pygame.display.set_caption("Renderizando Mapa com Personagem")
        tela.fill((10, 5, 20))
        try:
            fonte_loading = pygame.font.Font(None, 34)
            texto_loading = fonte_loading.render("Carregando fase...", True, (0, 255, 204))
            tela.blit(
                texto_loading,
                (
                    largura_mapa // 2 - texto_loading.get_width() // 2,
                    altura_mapa // 2 - texto_loading.get_height() // 2,
                ),
            )
        except Exception:
            pass
        pygame.display.flip()
        pygame.event.pump()

        pontuacao_inimigos=0
        maxima_pontuacao_magia = 750
        piscar_magia = False





        #INIMIGOS

        tempo_ultimo_inimigo_apos_morte = pygame.time.get_ticks()
        # Carregar a imagem do mapa
        mapa = pygame.image.load(mapa_path1).convert()
        mapa = pygame.transform.scale(mapa, (largura_mapa, altura_mapa))

        vfx_disparo_player = PlayerProjectileVFX()

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
        disparo_preparando = False
        disparo_frame_atual = 0
        tempo_ultimo_frame_preparo_disparo = 0
        angulo_disparo_preparado = 0.0
        DISPARO_PREPARO_FRAME_MS = 85
        coice_onda = criar_estado_coice_onda()
        
        # VARIÁVEIS PARA VARIANTES DE INIMIGOS (AREIA CÓSMICA)
        TESTAR_VARIANTES_RAPIDO = False
        ANOMALIA_ESPREITADOR_TEMPO = 15 if TESTAR_VARIANTES_RAPIDO else ANOMALIA_ESPREITADOR_SEG
        ANOMALIA_PROJETADOR_TEMPO = 30 if TESTAR_VARIANTES_RAPIDO else ANOMALIA_PROJETADOR_SEG
        ANOMALIA_CRISTALIZADOR_TEMPO = 45 if TESTAR_VARIANTES_RAPIDO else ANOMALIA_CRISTALIZADOR_SEG
        ANOMALIA_AGLOMERADOR_TEMPO = 60 if TESTAR_VARIANTES_RAPIDO else ANOMALIA_AGLOMERADOR_SEG
        ANOMALIA_CURATER_TEMPO = 75 if TESTAR_VARIANTES_RAPIDO else ANOMALIA_CURATER_SEG
        FUSAO_AGLOMERACAO_MS = 120000
        FUSAO_AGLOMERACAO_RAIO = 90
        FUSAO_AGLOMERACAO_MINIMO = 3
        disparos_inimigos = []
        tempo_ultimo_cheque_fusao = 0
        TIPO_CURATER = "curater"
        TIPO_LARAPIO = "larapio"
        CURATER_CHANCE_SPAWN_LOCAL = CURATER_CHANCE_SPAWN
        CURATER_INTERVALO_CURA = 2000
        CURATER_PERCENTUAL_VIDA_PERDIDA = CURATER_CURA_PERCENTUAL_VIDA_PERDIDA
        CURATER_MAX_ALVOS_CURA = 4
        CURATER_MAX_ATIVOS = 2
        CURATER_COOLDOWN_CHANCE_SPAWN_MS = 10000
        pulsos_cura_curater = []
        orientacao_base_sprite_inimigo = {
            1: "left",
            2: "left",
            3: "right",
            4: "left",
            5: "right",
            TIPO_CURATER: "left",
            TIPO_LARAPIO: "right",
            "larapio": "right",
        }

        def direcao_horizontal_inimigo(inimigo):
            if inimigo.get("parado", False):
                dx = (pos_x_personagem + largura_personagem / 2) - inimigo["rect"].centerx
                if abs(dx) > 1:
                    return "right" if dx > 0 else "left"
            return inimigo.get("direcao_horizontal", "left")

        def orientar_sprite_inimigo(sprite, inimigo):
            tipo = inimigo.get("tipo", 1)
            orientacao_base = orientacao_base_sprite_inimigo.get(tipo, "left")
            direcao_alvo = direcao_horizontal_inimigo(inimigo)
            if direcao_alvo != orientacao_base:
                cache = getattr(orientar_sprite_inimigo, "_cache", None)
                if cache is None:
                    cache = {}
                    orientar_sprite_inimigo._cache = cache
                chave = id(sprite)
                sprite_flipado = cache.get(chave)
                if sprite_flipado is None:
                    if len(cache) > 128:
                        cache.clear()
                    sprite_flipado = pygame.transform.flip(sprite, True, False)
                    cache[chave] = sprite_flipado
                return sprite_flipado
            return sprite

        def perfil_espreitador():
            tempo_decorrido = Variaveis.obter_tempo_decorrido()
            janela_escalada = max(1, (12 * 60) - ANOMALIA_ESPREITADOR_TEMPO)
            progresso = max(0.0, min(1.0, (tempo_decorrido - ANOMALIA_ESPREITADOR_TEMPO) / janela_escalada))
            return {
                "base": 0.82 + progresso * 0.28,
                "furtivo": 0.62 + progresso * 0.16,
                "sprint": 1.24 + progresso * 0.46,
                "duracao_ms": int(850 + progresso * 450),
                "cooldown_ms": int(9200 - progresso * 2600),
            }

        def dano_inimigo_inicio_ajustado(dano_base):
            if dano_base <= 0:
                return 0
            mult = multiplicador_dano_inimigo_por_tempo(Variaveis.obter_tempo_decorrido())
            return max(1, int(dano_base * mult))
        
        # Announcement Banner variables
        aviso_evento_texto = ""
        aviso_evento_cor = (0, 255, 255)
        aviso_evento_inicio = 0
        alerta_t1_mostrado = False
        alerta_t2_mostrado = False
        alerta_t3_mostrado = False
        alerta_t4_mostrado = False
        alerta_t5_mostrado = False
        
        # Helper functions
        def obter_mitigacao_dano(inimigo):
            if inimigo.get("tipo", 1) == TIPO_LARAPIO:
                return max(0.75, 1.0 - bonus_larapio(inimigo)["resistencia"])
            if inimigo.get("tipo", 1) == 4: # Cristalizador doesn't shield itself
                return 1.0
            if inimigo.get("tipo", 1) == TIPO_CURATER:
                return CURATER_MITIGACAO_DANO
            for c in inimigos_comum:
                if c.get("tipo", 1) == 4 and c != inimigo:
                    dist = math.hypot(inimigo["rect"].centerx - c["rect"].centerx, inimigo["rect"].centery - c["rect"].centery)
                    if dist <= 120:
                        return 0.5 # 50% damage reduction
            return 1.0

        def atualizar_curater(inimigo, agora_ms):
            ultimo_tick = inimigo.get("ultimo_tick_cura_curater")
            if ultimo_tick is not None and agora_ms - ultimo_tick < CURATER_INTERVALO_CURA:
                return
            inimigo["ultimo_tick_cura_curater"] = agora_ms
            candidatos = []
            for alvo in inimigos_comum:
                if alvo is inimigo or alvo.get("tipo", 1) == TIPO_CURATER or alvo.get("vida", 0) <= 0:
                    continue
                vida_maxima_alvo = alvo.get("vida_maxima", 0)
                if vida_maxima_alvo <= 0 or alvo.get("vida", 0) >= vida_maxima_alvo:
                    continue
                candidatos.append((alvo.get("vida", 0) / max(1, vida_maxima_alvo), alvo))

            alvos_curados = 0
            for _, alvo in sorted(candidatos, key=lambda item: item[0])[:CURATER_MAX_ALVOS_CURA]:
                vida_maxima_alvo = alvo.get("vida_maxima", 0)
                vida_perdida = vida_maxima_alvo - alvo["vida"]
                cura = vida_perdida * CURATER_PERCENTUAL_VIDA_PERDIDA
                if cura <= 0:
                    continue
                alvo["vida"] = min(vida_maxima_alvo, alvo["vida"] + cura)
                alvos_curados += 1

                if cura >= 1 or agora_ms - alvo.get("ultimo_texto_cura_recebida", 0) >= 1500:
                    alvo["ultimo_texto_cura_recebida"] = agora_ms
                    efeitos_texto.append({
                        "texto": f"+{max(1, int(cura))}",
                        "x": alvo["rect"].x,
                        "y": alvo["rect"].y - 32,
                        "tempo_inicio": agora_ms,
                        "cor": (98, 255, 120)
                    })
                pulsos_cura_curater.append({
                    "origem": inimigo["rect"].center,
                    "alvo": alvo["rect"].center,
                    "inicio": agora_ms,
                })

            if alvos_curados > 0 and agora_ms - inimigo.get("ultimo_texto_cura", 0) >= 900:
                inimigo["ultimo_texto_cura"] = agora_ms
                efeitos_texto.append({
                    "texto": "CURA!",
                    "x": inimigo["rect"].x,
                    "y": inimigo["rect"].y - 44,
                    "tempo_inicio": agora_ms,
                    "cor": (120, 255, 120)
                })

        def desenhar_plantinhas_curater(tela, inimigo, desenhar_x, desenhar_y, l_vis, a_vis):
            agora_ms = pygame.time.get_ticks()
            base_y = desenhar_y + a_vis - 8
            centro_x = desenhar_x + l_vis // 2
            for i in range(7):
                fase = agora_ms * 0.002 + i * 0.9
                px = centro_x + int(math.cos(i * 1.7) * (l_vis * 0.42)) + int(math.sin(fase) * 2)
                py = base_y + int(math.sin(i * 1.3) * 8)
                caule_h = 8 + (i % 3) * 3
                pygame.draw.line(tela, (45, 150, 58), (px, py), (px, py - caule_h), 2)
                pygame.draw.ellipse(tela, (72, 214, 92), (px - 5, py - caule_h - 3, 7, 5))
                pygame.draw.ellipse(tela, (104, 245, 132), (px, py - caule_h - 2, 7, 5))
            pulso = int(18 + 5 * math.sin(agora_ms * 0.004))
            pygame.draw.circle(tela, (70, 230, 105), inimigo["rect"].center, pulso, 1)
            
        def registrar_hit_larapio(inimigo):
            inimigo["ultimo_tempo_atingido"] = pygame.time.get_ticks()
            portal_charge = inimigo.get("portal_charge", 0.0)
            inimigo["portal_charge"] = max(0.0, portal_charge - 0.5)

        def processar_morte_inimigo(inimigo):
            global vida, tempo_ultimo_spawn_larapio
            posicao_inimigo = inimigo["rect"].center
            soltar_moeda(posicao_inimigo)
            if inimigo.get("eco_vinculado"):
                ecos_rompidos_condutor.append({"x": posicao_inimigo[0], "y": posicao_inimigo[1], "inicio": tempo_atual})
                efeitos_texto.append({
                    "texto": "VINCULO ROMPIDO",
                    "x": posicao_inimigo[0] - 48,
                    "y": posicao_inimigo[1] - 44,
                    "tempo_inicio": tempo_atual,
                    "cor": (150, 220, 255),
                })
            if inimigo.get("tipo") == TIPO_LARAPIO:
                tempo_ultimo_spawn_larapio = pygame.time.get_ticks()
                pontos_devolvidos = soltar_pontos_larapio(posicao_inimigo, inimigo.get("dinheiro_roubado", 0))
                pontos_devolvidos += soltar_pontos_larapio(posicao_inimigo, int(custo_carta_atual * 2.0), multiplicador=1.0)
                if inimigo.get("possui_chave_loja"):
                    Variaveis.soltar_chave_do_larapio(posicao_inimigo, tempo_atual)
                if pontos_devolvidos > 0:
                    efeitos_texto.append({
                        "texto": f"{pontos_devolvidos} PONTOS RECUPERAVEIS",
                        "x": posicao_inimigo[0] - 54,
                        "y": posicao_inimigo[1] - 52,
                        "tempo_inicio": tempo_atual,
                        "cor": (255, 230, 90),
                    })
                
                if Variaveis.obter_modo_cartas() == "drops":
                    cartas_roubadas = inimigo.get("cartas_roubadas_larapio", [])
                    if cartas_roubadas:
                        n = len(cartas_roubadas)
                        if n % 2 == 1:
                            qtd_devolver = (n + 1) // 2
                        else:
                            qtd_devolver = n // 2
                        
                        cartas_devolvidas = random.sample(cartas_roubadas, qtd_devolver)
                        for c_nome in cartas_devolvidas:
                            offset_x = random.randint(-30, 30)
                            offset_y = random.randint(-30, 30)
                            pos_drop = (posicao_inimigo[0] + offset_x, posicao_inimigo[1] + offset_y)
                            Variaveis.soltar_carta_especifica(c_nome, pos_drop, tempo_atual)
                            
                        efeitos_texto.append({
                            "texto": f"RECUPEROU {qtd_devolver}/{n} CARTAS!",
                            "x": posicao_inimigo[0] - 50,
                            "y": posicao_inimigo[1] - 40,
                            "tempo_inicio": tempo_atual,
                            "cor": (0, 255, 100),
                        })
            Variaveis.tentar_soltar_carta(posicao_inimigo, tempo_atual, Chance_Sorte, inimigos_eliminados)
            gerar_fragmentos_morte(inimigo, 1)

            if inimigo.get("tipo", 1) == TIPO_CURATER:
                vida_perdida = max(0, vida_maxima - vida)
                cura = int(vida_perdida * CURATER_CURA_ABATE_VIDA_PERDIDA)
                if cura > 0:
                    vida = min(vida_maxima, vida + cura)
                    efeitos_texto.append({
                        "texto": f"CURATER +{cura}",
                        "x": posicao_inimigo[0] - 22,
                        "y": posicao_inimigo[1] - 42,
                        "tempo_inicio": tempo_atual,
                        "cor": (130, 255, 145)
                    })
                    pulsos_cura_curater.append({
                        "origem": posicao_inimigo,
                        "alvo": (int(pos_x_personagem + largura_personagem // 2), int(pos_y_personagem + altura_personagem // 2)),
                        "inicio": tempo_atual,
                    })
            
            # Se for Aglomerador (tipo 2), explode em 2 mini-inimigos
            if inimigo.get("tipo", 1) == 2:
                for _ in range(2):
                    offset_x = random.randint(-20, 20)
                    offset_y = random.randint(-20, 20)
                    mini = criar_inimigo(inimigo["rect"].x + offset_x, inimigo["rect"].y + offset_y, tipo=1)
                    mini["vida"] = int(vida_inimigo_maxima * 0.3)
                    mini["vida_maxima"] = int(vida_inimigo_maxima * 0.3)
                    mini["velocidade"] = Velocidade_Inimigos_1 * 0.9
                    inimigos_comum.append(mini)
                    
        def atualizar_espreitador(inimigo):
            dx = pos_x_personagem - inimigo["rect"].x
            dy = pos_y_personagem - inimigo["rect"].y
            dist = math.hypot(dx, dy)
            
            # Stealth Alpha Oscillation
            inimigo["alpha_oscilation"] = inimigo.get("alpha_oscilation", 120.0) + inimigo.get("alpha_dir", 1) * 6
            if inimigo["alpha_oscilation"] >= 180:
                inimigo["alpha_oscilation"] = 180
                inimigo["alpha_dir"] = -1
            elif inimigo["alpha_oscilation"] <= 40:
                inimigo["alpha_oscilation"] = 40
                inimigo["alpha_dir"] = 1
                
            perfil = perfil_espreitador()
            if dist > 300:
                inimigo["invisivel"] = True
                inimigo["velocidade"] = Velocidade_Inimigos_1 * perfil["furtivo"]
            else:
                inimigo["invisivel"] = False
                # Sprint burst trigger
                tempo_sprint = pygame.time.get_ticks()
                if not inimigo.get("sprint_ativo", False) and tempo_sprint - inimigo.get("sprint_timer", 0) > perfil["cooldown_ms"]:
                    inimigo["sprint_ativo"] = True
                    inimigo["sprint_timer"] = tempo_sprint
                    
                if inimigo.get("sprint_ativo", False):
                    if pygame.time.get_ticks() - inimigo["sprint_timer"] < perfil["duracao_ms"]:
                        inimigo["velocidade"] = Velocidade_Inimigos_1 * perfil["sprint"]
                        inimigo["alpha_oscilation"] = 255 # Visible
                    else:
                        inimigo["sprint_ativo"] = False
                        inimigo["sprint_timer"] = pygame.time.get_ticks() # Cooldown start
                        inimigo["velocidade"] = Velocidade_Inimigos_1 * perfil["base"]
                else:
                    inimigo["velocidade"] = Velocidade_Inimigos_1 * perfil["base"]
                        
        def atualizar_projetador(inimigo):
            # Projetador não age enquanto estiver stunado
            if pygame.time.get_ticks() < inimigo.get("stun_fim", 0):
                inimigo["parado"] = True
                return
            dx = pos_x_personagem - inimigo["rect"].centerx
            dy = pos_y_personagem - inimigo["rect"].centery
            dist = math.hypot(dx, dy)
            
            if dist <= 280:
                inimigo["parado"] = True
                if tempo_atual - inimigo.get("ultimo_disparo", 0) > 2500:
                    inimigo["ultimo_disparo"] = tempo_atual
                    angulo = math.atan2(dy, dx)
                    disparos_inimigos.append({
                        "rect": pygame.Rect(inimigo["rect"].centerx, inimigo["rect"].centery, 12, 12),
                        "vx": math.cos(angulo) * 3.5,
                        "vy": math.sin(angulo) * 3.5,
                    })
            else:
                inimigo["parado"] = False
        # Atualizar a última direção da personagem
        ultima_tecla_movimento = None
        movimento_pressionado = False
        #as seguintes variáveis para controle do tempo de hit do inimigo
        tempo_ultimo_hit_inimigo = pygame.time.get_ticks()

        piscando_vida = False
        vida_inimigo_maxima = multiplayer_coop.aplicar_multiplicador_vida_inimigo(vida_inimigo_comum_inicial(30))
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
            global racional_dilatacao_fim, racional_dilatacao_proximo_uso
            nonlocal vida_inimigo_maxima, fator_lentidao_boss

            tempo_atual = pygame.time.get_ticks()
            if ultimate_manifestacao.jogador_bloqueado(tempo_atual):
                movimento_pressionado = False
                direcao_atual = 'stop'
                return 'stop'
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
            velocidade_movimento = (
                velocidade_personagem
                * fator_movimento_racional(aurea, racional_dilatacao_fim, tempo_atual)
                * fator_velocidade_devota(aurea, estado_devota, tempo_atual)
                * aureas_avancadas.fator_velocidade_jogador(estado_aureas_avancadas, aurea, tempo_atual)
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
                                                 pos_x_personagem + dx * (velocidade_movimento * fator_lentidao_boss) * fator_normalizacao * dt))
                    pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                                 pos_y_personagem + dy * (velocidade_movimento * fator_lentidao_boss) * fator_normalizacao * dt))
                else:
                    angulo_inclinacao_personagem = 0
                    pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                                 pos_x_personagem + dx * (velocidade_movimento * fator_lentidao_boss) * dt))
                    pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                                 pos_y_personagem + dy * (velocidade_movimento * fator_lentidao_boss) * dt))
                
                if not multiplayer_coop.eh_cliente():
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
                alvo_teleporte_info = {
                    "vivo": bool(miniboss_condutor) or (boss_vivo1 and not boss_morte_processada),
                    "rect": (
                        miniboss_condutor["rect"] if miniboss_condutor
                        else (pygame.Rect(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura) if boss_vivo1 and not boss_morte_processada else None)
                    ),
                    "hit_flag": False,
                    "alvo": "arauto" if miniboss_condutor else "boss",
                }
                efeito_teleporte = teleporte_manifestacao.aplicar_efeito_teleporte_manifestacao(
                    manifestacao_ativa,
                    origem_teleporte,
                    destino_teleporte,
                    inimigos_comum,
                    alvo_teleporte_info,
                    dano_person_hit * fator_dano_aureas(tempo_atual),
                    efeitos_texto,
                    tempo_atual,
                    largura_mapa,
                    altura_mapa,
                    ondas,
                    retorno_teleporte is not None,
                    player_pos_origem_teleporte,
                )
                if alvo_teleporte_info.get("hit_flag"):
                    dano_teleporte_alvo = alvo_teleporte_info.get("dano_manifestacao", dano_person_hit * 0.10)
                    if alvo_teleporte_info.get("alvo") == "arauto" and miniboss_condutor:
                        aplicar_dano_ao_condutor(dano_teleporte_alvo, (205, 155, 255))
                    elif boss_vivo1 and not boss_morte_processada:
                        vida_boss -= dano_boss_mitigado(
                            dano_teleporte_alvo, 1, inimigos_eliminados, tempo_atual,
                            cartas_compradas.get("Coletora", 0)
                        )
                evolucoes_manifestacao.ao_teleportar(
                    estado_evolucao_manifestacao, origem_teleporte, destino_teleporte,
                    inimigos_comum, tempo_teleporte_agora
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
                    mitigacao = obter_mitigacao_dano(inimigo)
                    dano_final = dano_choque * mitigacao
                    inimigo["vida"] -= dano_final
                    if inimigo.get("tipo") == TIPO_LARAPIO:
                        registrar_hit_larapio(inimigo)
                    cor_txt = (0, 191, 255) if mitigacao == 1.0 else (0, 255, 255)
                    efeitos_texto.append({
                        "texto": f"-{int(dano_final)}",
                        "x": inimigo["rect"].x,
                        "y": inimigo["rect"].y - 20,
                        "tempo_inicio": pygame.time.get_ticks(),
                        "cor": cor_txt
                    })
                    if inimigo["vida"] <= 0:
                        processar_morte_inimigo(inimigo)
                        if inimigo in inimigos_comum:
                            inimigos_comum.remove(inimigo)
                        
                        # Escalonamento por nível de ameaça
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
                                vida_boss += ganho_progressao_boss(15 + nivel_ameaca * 10)
                                vida_maxima_boss1 = vida_boss
                                vida_boss2 += ganho_progressao_boss(20 + nivel_ameaca * 12)
                                vida_maxima_boss2 = vida_boss2
                                vida_boss3 += ganho_progressao_boss(25 + nivel_ameaca * 15)
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += ganho_progressao_boss(30 + nivel_ameaca * 18)
                                vida_maxima_boss4 = vida_boss4

                # Dano ao Boss (só se vivo e morte não processada)
                if boss_vivo1 and not boss_morte_processada:
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
            frames_tipo = frames_inimigo_especies.get(tipo, frames_inimigo)
            image = frames_tipo[0]
            
            # Base stats
            hp = vida_inimigo_maxima
            vel = Velocidade_Inimigos_1
            l_inimigo = largura_inimigo
            a_inimigo = altura_inimigo
            
            if tipo == 2:  # Aglomerador
                hp = vida_inimigo_maxima * 3.2
                vel = Velocidade_Inimigos_1 * 1.35
                l_inimigo = int(largura_inimigo * 1.6)
                a_inimigo = int(altura_inimigo * 1.6)
            elif tipo == 3:  # Espreitador
                hp = vida_inimigo_maxima * 0.9
                vel = Velocidade_Inimigos_1 * perfil_espreitador()["base"]
            elif tipo == 4:  # Cristalizador
                hp = vida_inimigo_maxima * 2.0
                vel = Velocidade_Inimigos_1 * 0.5
            elif tipo == 5:  # Projetador
                hp = vida_inimigo_maxima * 1.2
                vel = Velocidade_Inimigos_1 * 0.8
            elif tipo == TIPO_CURATER:
                hp = vida_inimigo_maxima * CURATER_MULTIPLICADOR_VIDA
                vel = Velocidade_Inimigos_1 * 0.45
            elif tipo == TIPO_LARAPIO:
                image = frames_larapio[0]
                tempo_decorrido = time.time() - tempo_inicial
                escala_dificuldade = 1.0 + (tempo_decorrido * 0.005) + (inimigos_eliminados * 0.002)
                hp = vida_inimigo_maxima * 2.2 * escala_dificuldade
                vel = Velocidade_Inimigos_1 * 1.25
                l_inimigo = frames_larapio[0].get_width()
                a_inimigo = frames_larapio[0].get_height()
                
            # Ajustar a hitbox para ser menor que a imagem original
            largura_hitbox = int(l_inimigo * 0.8)  # Reduz a largura da hitbox
            altura_hitbox = int(a_inimigo * 0.5)    # Reduz a altura da hitbox
            offset_x = (l_inimigo - largura_hitbox) // 2  # Centraliza a hitbox horizontalmente
            offset_y = (a_inimigo - altura_hitbox) // 2    # Centraliza a hitbox verticalmente

            rect = pygame.Rect(x + offset_x, y + offset_y, largura_hitbox, altura_hitbox)

            enemy_dict = {
                "rect": rect,
                "image": image,
                "tipo": tipo,
                "vida": hp,
                "vida_maxima": hp,
                "velocidade": vel,
                "largura_visual": l_inimigo,
                "altura_visual": a_inimigo,
                "offset_x": offset_x,
                "offset_y": offset_y,
            }
            
            # Custom fields
            if tipo == 3: # Espreitador
                enemy_dict["invisivel"] = False
                enemy_dict["sprint_timer"] = pygame.time.get_ticks()
                enemy_dict["sprint_ativo"] = False
                enemy_dict["alpha_oscilation"] = 120.0
                enemy_dict["alpha_dir"] = 1
            elif tipo == 5: # Projetador
                enemy_dict["ultimo_disparo"] = 0
                enemy_dict["parado"] = False
            elif tipo == TIPO_CURATER:
                enemy_dict["ultimo_tick_cura_curater"] = -CURATER_INTERVALO_CURA
                enemy_dict["parado"] = True
            elif tipo == TIPO_LARAPIO:
                agora_larapio = pygame.time.get_ticks()
                enemy_dict.update({
                    "estado": "cacando",
                    "dinheiro_roubado": 0,
                    "poder_saque": 0,
                    "ultimo_roubo": 0,
                    "inicio_fuga": 0,
                    "tempo_fuga": LARAPIO_TEMPO_FUGA,
                    "ultimo_ataque": 0,
                    "cooldown_ataque": 2600,
                    "pausa_arremesso_stun_ms": None,
                    "inicio_preparo_ataque": 0,
                    "frame_atual": 0,
                    "ultimo_frame": agora_larapio,
                    "direcao_x": 1,
                    "vel_x": 0.0,
                    "vel_y": 0.0,
                    "agressivo": False,
                    "roubos_realizados": 0,
                    "cobica_spawn": 0.0,
                    "parado": False,
                    "cartas_roubadas_larapio": [],
                })
                
            return enemy_dict
        def desenhar_sombra(tela, x, y, largura, altura, offset_y=5):
            """Desenha uma sombra elíptica embaixo de um ser com três níveis de qualidade"""
            modo_sombra = config_graficos.get("sombras_ativas", "dinamicas")
            Variaveis.desenhar_sombra_cacheada(tela, x, y, largura, altura, modo_sombra, offset_y)
            return

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


        tempo_ultima_chance_curater_spawn = -CURATER_COOLDOWN_CHANCE_SPAWN_MS

        def gerar_inimigo(limite_inimigos=None):
            nonlocal tempo_ultima_chance_curater_spawn
            global inimigos_comum
            if multiplayer_coop.eh_cliente():
                return

            limite_inimigos = max_inimigos if limite_inimigos is None else limite_inimigos
            if len(inimigos_comum) < limite_inimigos:
                # Determina o tipo com base no tempo decorrido
                tempo_decorrido = Variaveis.obter_tempo_decorrido()
                tipo_escolhido = 1
                if tempo_decorrido >= ANOMALIA_CURATER_TEMPO:
                    curaters_ativos = sum(1 for ini in inimigos_comum if ini.get("tipo", 1) == TIPO_CURATER)
                    agora_spawn = pygame.time.get_ticks()
                    pode_testar_curater = (
                        curaters_ativos < CURATER_MAX_ATIVOS
                        and agora_spawn - tempo_ultima_chance_curater_spawn >= CURATER_COOLDOWN_CHANCE_SPAWN_MS
                    )
                    if pode_testar_curater:
                        tempo_ultima_chance_curater_spawn = agora_spawn
                        choices = [TIPO_CURATER, 1, 3, 5, 4]
                        weights = [CURATER_CHANCE_SPAWN_LOCAL, 0.45, 0.16, 0.14, 0.10]
                    else:
                        choices = [1, 3, 5, 4]
                        weights = [0.58, 0.18, 0.15, 0.09]
                    tipo_escolhido = random.choices(choices, weights=weights)[0]
                elif tempo_decorrido >= ANOMALIA_CRISTALIZADOR_TEMPO:
                    choices = [1, 3, 5, 4]
                    weights = [0.58, 0.18, 0.15, 0.09]
                    tipo_escolhido = random.choices(choices, weights=weights)[0]
                elif tempo_decorrido >= ANOMALIA_PROJETADOR_TEMPO:
                    choices = [1, 3, 5]
                    weights = [0.66, 0.20, 0.14]
                    tipo_escolhido = random.choices(choices, weights=weights)[0]
                elif tempo_decorrido >= ANOMALIA_ESPREITADOR_TEMPO:
                    choices = [1, 3]
                    weights = [0.76, 0.24]
                    tipo_escolhido = random.choices(choices, weights=weights)[0]
                    
                # Regra: Limite de 1 Cristalizador por vez
                if tipo_escolhido == 4:
                    if any(ini.get("tipo", 1) == 4 for ini in inimigos_comum):
                        tipo_escolhido = 1

                if tipo_escolhido == TIPO_CURATER:
                    if sum(1 for ini in inimigos_comum if ini.get("tipo", 1) == TIPO_CURATER) >= CURATER_MAX_ATIVOS:
                        tipo_escolhido = 1

                if tipo_escolhido == TIPO_CURATER:
                    margem = 28
                    cantos = [
                        (margem, margem),
                        (int(largura_mapa) - int(largura_inimigo) - margem, margem),
                        (margem, int(altura_mapa) - int(altura_inimigo) - margem),
                        (int(largura_mapa) - int(largura_inimigo) - margem, int(altura_mapa) - int(altura_inimigo) - margem),
                    ]
                    sx, sy = random.choice(cantos)
                    sx += random.randint(-12, 36)
                    sy += random.randint(-12, 36)
                    novo_inimigo = criar_inimigo(max(0, min(int(largura_mapa) - int(largura_inimigo), sx)), max(0, min(int(altura_mapa) - int(altura_inimigo), sy)), tipo=tipo_escolhido)
                else:
                    borda = random.choice(['esquerda', 'direita', 'superior', 'inferior'])
                    if borda == 'esquerda':
                        novo_inimigo = criar_inimigo(0, random.randint(0, int(altura_mapa) - int(altura_inimigo)), tipo=tipo_escolhido)
                    elif borda == 'direita':
                        novo_inimigo = criar_inimigo(int(largura_mapa) - int(largura_inimigo), random.randint(0, int(altura_mapa) - int(altura_inimigo)), tipo=tipo_escolhido)
                    elif borda == 'superior':
                        novo_inimigo = criar_inimigo(random.randint(0, int(largura_mapa) - int(largura_inimigo)), 0, tipo=tipo_escolhido)
                    elif borda == 'inferior':
                        novo_inimigo = criar_inimigo(random.randint(0, int(largura_mapa) - int(largura_inimigo)), int(altura_mapa) - int(altura_inimigo), tipo=tipo_escolhido)

                # Verifica se o novo inimigo está muito próximo de algum inimigo existente
                distancia_minima_alcancada = any(
                    math.sqrt((novo_inimigo["rect"].x - inimigo["rect"].x) ** 2 + (novo_inimigo["rect"].y - inimigo["rect"].y) ** 2) < distancia_minima_inimigos
                    for inimigo in inimigos_comum
                )

                # Ajusta a posição do novo inimigo se estiver muito próximo
                tentativas_spawn = 0
                while distancia_minima_alcancada and tentativas_spawn < 12:
                    tentativas_spawn += 1
                    if tipo_escolhido == TIPO_CURATER:
                        margem = 28
                        cantos = [
                            (margem, margem),
                            (int(largura_mapa) - int(largura_inimigo) - margem, margem),
                            (margem, int(altura_mapa) - int(altura_inimigo) - margem),
                            (int(largura_mapa) - int(largura_inimigo) - margem, int(altura_mapa) - int(altura_inimigo) - margem),
                        ]
                        sx, sy = random.choice(cantos)
                        sx += random.randint(-12, 36)
                        sy += random.randint(-12, 36)
                        novo_inimigo = criar_inimigo(max(0, min(int(largura_mapa) - int(largura_inimigo), sx)), max(0, min(int(altura_mapa) - int(altura_inimigo), sy)), tipo=tipo_escolhido)
                    else:
                        borda = random.choice(['esquerda', 'direita', 'superior', 'inferior'])
                        if borda == 'esquerda':
                            novo_inimigo = criar_inimigo(0, random.randint(0, int(altura_mapa) - int(altura_inimigo)), tipo=tipo_escolhido)
                        elif borda == 'direita':
                            novo_inimigo = criar_inimigo(int(largura_mapa) - int(largura_inimigo), random.randint(0, int(altura_mapa) - int(altura_inimigo)), tipo=tipo_escolhido)
                        elif borda == 'superior':
                            novo_inimigo = criar_inimigo(random.randint(0, int(largura_mapa) - int(largura_inimigo)), 0, tipo=tipo_escolhido)
                        elif borda == 'inferior':
                            novo_inimigo = criar_inimigo(random.randint(0, int(largura_mapa) - int(largura_inimigo)), int(altura_mapa) - int(altura_inimigo), tipo=tipo_escolhido)

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
        tempo_inicio_cobica_larapio = 0
        chance_atual_larapio = 0.0
        tempo_ultimo_spawn_larapio = pygame.time.get_ticks() if (Variaveis.obter_modo_cartas() == "drops") else 0
        alerta_larapio_mostrado = False
        miniboss_condutor = None
        miniboss_condutor_spawnado = False
        fragmentos_ruptura = []
        ecos_rompidos_condutor = []
        raios_olhar_condutor = []

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

        def soltar_pontos_larapio(posicao, quantidade_roubada, multiplicador=1.25):
            pontos_devolvidos = int(quantidade_roubada * multiplicador)
            if quantidade_roubada > 0:
                pontos_devolvidos = max(1, pontos_devolvidos)
            if pontos_devolvidos <= 0:
                return 0

            tamanho_moeda = (32, 32)
            sprite_redimensionada = pygame.transform.scale(sprite_moeda, tamanho_moeda)
            quantidade_pickups = min(12, max(1, int(math.ceil(pontos_devolvidos / 75))))
            valor_base = pontos_devolvidos // quantidade_pickups
            resto = pontos_devolvidos % quantidade_pickups
            for i in range(quantidade_pickups):
                valor_pickup = valor_base + (1 if i < resto else 0)
                offset_x = random.randint(-42, 42)
                offset_y = random.randint(-36, 36)
                rect = sprite_redimensionada.get_rect(center=(posicao[0] + offset_x, posicao[1] + offset_y))
                rect.x = max(0, min(int(largura_mapa) - rect.width, rect.x))
                rect.y = max(0, min(int(altura_mapa) - rect.height, rect.y))
                moedas_soltadas.append({
                    "rect": rect,
                    "image": sprite_redimensionada,
                    "valor": valor_pickup,
                    "tipo": "pontos_larapio",
                })
            return pontos_devolvidos

        def gerar_brilhos_roubo_larapio(origem, destino):
            if not (config_graficos.get("particulas_ativas", True) and config_graficos.get("efeitos_visuais", True)):
                return
            ox, oy = origem
            dx = destino[0] - ox
            dy = destino[1] - oy
            dist = max(1.0, math.hypot(dx, dy))
            for _ in range(random.randint(3, 5)):
                size = random.uniform(3, 5)
                fragmentos_morte.append({
                    "x": ox + random.uniform(-10, 10),
                    "y": oy + random.uniform(-8, 8),
                    "vx": (dx / dist) * random.uniform(3.5, 5.5) + random.uniform(-1.0, 1.0),
                    "vy": (dy / dist) * random.uniform(3.5, 5.5) + random.uniform(-1.0, 1.0),
                    "color": random.choice([(255, 218, 82), (255, 191, 36), (255, 245, 160)]),
                    "vertices": [(-size, 0), (0, -size), (size, 0), (0, size)],
                    "rot": random.uniform(0, 360),
                    "vrot": random.uniform(-16, 16),
                    "life": random.randint(18, 28),
                })

        def calcular_cobica_larapio(tempo_decorrido_run):
            nonlocal tempo_inicio_cobica_larapio, chance_atual_larapio
            tempo_atual_local = pygame.time.get_ticks()
            if tempo_decorrido_run < LARAPIO_SPAWN_APOS_SEG:
                tempo_inicio_cobica_larapio = 0
                chance_atual_larapio = 0.0
                return 0, chance_atual_larapio, 0.0

            limiar_pontos = float(custo_carta_atual) * 3.0
            if pontuacao_exib >= limiar_pontos:
                chance_atual_larapio = 0.70
            else:
                chance_atual_larapio = 0.70 * (pontuacao_exib / max(1.0, limiar_pontos))
                
            cobica = min(1.0, pontuacao_exib / max(1.0, limiar_pontos))

            pontos_minimos_cobica = max(50.0, float(custo_carta_atual) * 0.50)
            segurando_pontos = pontuacao_exib >= pontos_minimos_cobica

            if segurando_pontos:
                if tempo_inicio_cobica_larapio <= 0:
                    tempo_inicio_cobica_larapio = tempo_atual_local
                tempo_segurando = tempo_atual_local - tempo_inicio_cobica_larapio
            else:
                tempo_inicio_cobica_larapio = 0
                tempo_segurando = 0

            return tempo_segurando, chance_atual_larapio, cobica

        def bonus_larapio(inimigo):
            poder_saque = inimigo.get("dinheiro_roubado", 0)
            cobica_spawn = inimigo.get("cobica_spawn", 0.0)
            pontos_referencia = max(150.0, float(custo_carta_atual) * LARAPIO_MULT_REFERENCIA_PONTOS)
            cobica_atual = min(1.0, max(0.0, pontuacao_exib / pontos_referencia))
            tempo_fuga = 0
            if inimigo.get("estado") == "fugindo":
                tempo_fuga = max(0, tempo_atual - inimigo.get("inicio_fuga", tempo_atual))
            bonus_sedento = min(0.45, (cobica_spawn * 0.18) + (cobica_atual * 0.20) + (tempo_fuga / 7000.0) * 0.07)
            return {
                "velocidade": min(0.65, poder_saque * 0.01 + bonus_sedento),
                "dano": min(0.40, poder_saque * 0.012),
                "resistencia": min(0.25, poder_saque * 0.008),
            }

        def mover_larapio(inimigo, dir_x, dir_y, velocidade):
            dist = math.hypot(dir_x, dir_y)
            if dist <= 0:
                inimigo["vel_x"] = 0.0
                inimigo["vel_y"] = 0.0
                return
            dir_x /= dist
            dir_y /= dist
            if abs(dir_x) > 0.05:
                inimigo["direcao_horizontal"] = "right" if dir_x > 0 else "left"
            fator_tempo_larapio = fator_mundo_racional(aurea, racional_dilatacao_fim, tempo_atual)
            passo_x = dir_x * velocidade * dt * fator_tempo_larapio
            passo_y = dir_y * velocidade * dt * fator_tempo_larapio
            inimigo["pos_x"] = float(inimigo.get("pos_x", inimigo["rect"].x)) + passo_x
            inimigo["pos_y"] = float(inimigo.get("pos_y", inimigo["rect"].y)) + passo_y
            max_x = max(0, int(largura_mapa) - inimigo["rect"].width)
            max_y = max(0, int(altura_mapa) - inimigo["rect"].height)
            inimigo["pos_x"] = max(0.0, min(float(max_x), inimigo["pos_x"]))
            inimigo["pos_y"] = max(0.0, min(float(max_y), inimigo["pos_y"]))
            inimigo["rect"].x = int(inimigo["pos_x"])
            inimigo["rect"].y = int(inimigo["pos_y"])
            inimigo["vel_x"] = passo_x
            inimigo["vel_y"] = passo_y
            if abs(passo_x) > 0.01:
                inimigo["direcao_x"] = 1 if passo_x >= 0 else -1

        def direcao_fuga_larapio(inimigo, jogador_cx, jogador_cy, velocidade):
            atual_x = float(inimigo.get("pos_x", inimigo["rect"].x))
            atual_y = float(inimigo.get("pos_y", inimigo["rect"].y))
            inimigo_cx = atual_x + inimigo["rect"].width / 2
            inimigo_cy = atual_y + inimigo["rect"].height / 2
            dx_player = inimigo_cx - jogador_cx
            dy_player = inimigo_cy - jogador_cy
            dist_player = max(1.0, math.hypot(dx_player, dy_player))
            
            tempo_atual = pygame.time.get_ticks()
            max_x = max(0.0, float(largura_mapa - inimigo["rect"].width))
            max_y = max(0.0, float(altura_mapa - inimigo["rect"].height))
            
            # Detecção de encurralamento em canto/parede
            dist_borda = min(atual_x, max_x - atual_x, atual_y, max_y - atual_y)
            if dist_player < 160.0 and dist_borda < 80.0 and tempo_atual - inimigo.get("ultimo_escape_fantasma", 0) >= 4000:
                inimigo["tempo_fuga_fantasma"] = tempo_atual + 1200
                inimigo["ultimo_escape_fantasma"] = tempo_atual
                efeitos_texto.append({
                    "texto": "DESVIO!",
                    "x": inimigo_cx,
                    "y": inimigo_cy - 28,
                    "tempo_inicio": tempo_atual,
                    "cor": (0, 225, 255),
                })
            
            # Escape fantasma: Corre em linha reta para o centro do mapa
            if tempo_atual < inimigo.get("tempo_fuga_fantasma", 0):
                centro_x = largura_mapa / 2
                centro_y = altura_mapa / 2
                dx_c = centro_x - inimigo_cx
                dy_c = centro_y - inimigo_cy
                dist_c = max(1.0, math.hypot(dx_c, dy_c))
                return (dx_c / dist_c, dy_c / dist_c)

            # Lógica de quinas: se estiver em um canto, escolhe a quina adjacente mais distante do jogador e corre para lá
            is_near_left = atual_x < 70.0
            is_near_right = atual_x > max_x - 70.0
            is_near_top = atual_y < 70.0
            is_near_bottom = atual_y > max_y - 70.0
            
            is_in_corner = (is_near_left or is_near_right) and (is_near_top or is_near_bottom)
            
            if is_in_corner:
                if "target_quina" in inimigo:
                    tx, ty = inimigo["target_quina"]
                    dist_to_target = math.hypot(tx - atual_x, ty - atual_y)
                    if dist_to_target < 60.0:
                        inimigo.pop("target_quina", None)
                
                if "target_quina" not in inimigo:
                    c_top_left = (15.0, 15.0)
                    c_top_right = (max_x - 15.0, 15.0)
                    c_bottom_left = (15.0, max_y - 15.0)
                    c_bottom_right = (max_x - 15.0, max_y - 15.0)
                    
                    vizinhos = []
                    if is_near_left and is_near_top:
                        vizinhos = [c_top_right, c_bottom_left]
                    elif is_near_right and is_near_top:
                        vizinhos = [c_top_left, c_bottom_right]
                    elif is_near_left and is_near_bottom:
                        vizinhos = [c_top_left, c_bottom_right]
                    elif is_near_right and is_near_bottom:
                        vizinhos = [c_top_right, c_bottom_left]
                    
                    if vizinhos:
                        d1 = math.hypot(vizinhos[0][0] - jogador_cx, vizinhos[0][1] - jogador_cy)
                        d2 = math.hypot(vizinhos[1][0] - jogador_cx, vizinhos[1][1] - jogador_cy)
                        inimigo["target_quina"] = vizinhos[0] if d1 >= d2 else vizinhos[1]
            else:
                inimigo.pop("target_quina", None)
                
            if "target_quina" in inimigo:
                tx, ty = inimigo["target_quina"]
                dx_t = tx - atual_x
                dy_t = ty - atual_y
                dist_t = max(1.0, math.hypot(dx_t, dy_t))
                return (dx_t / dist_t, dy_t / dist_t)

            base_ang = math.atan2(dy_player, dx_player)
            fator_tempo_larapio = fator_mundo_racional(aurea, racional_dilatacao_fim, tempo_atual)
            passo_previsto = max(24.0, velocidade * dt * fator_tempo_larapio * 10.0)
            centro_mapa_x = largura_mapa / 2
            centro_mapa_y = altura_mapa / 2
            margem_segura = 150.0
            melhor_score = -float("inf")
            melhor_dir = (dx_player / dist_player, dy_player / dist_player)

            for offset in (0, -0.35, 0.35, -0.7, 0.7, -1.05, 1.05, math.pi):
                ang = base_ang + offset
                dir_x = math.cos(ang)
                dir_y = math.sin(ang)
                
                # Deslizar ao longo das paredes se estiver muito perto delas (Wall-sliding)
                if atual_x <= 15.0 and dir_x < 0:
                    dir_x = 0.0
                    dir_y = 1.0 if dy_player >= 0 else -1.0
                elif atual_x >= max_x - 15.0 and dir_x > 0:
                    dir_x = 0.0
                    dir_y = 1.0 if dy_player >= 0 else -1.0
                    
                if atual_y <= 15.0 and dir_y < 0:
                    dir_y = 0.0
                    dir_x = 1.0 if dx_player >= 0 else -1.0
                elif atual_y >= max_y - 15.0 and dir_y > 0:
                    dir_y = 0.0
                    dir_x = 1.0 if dx_player >= 0 else -1.0
                
                # Normaliza vetor deslizado
                h = math.hypot(dir_x, dir_y)
                if h > 0:
                    dir_x /= h
                    dir_y /= h
                
                prev_x = atual_x + dir_x * passo_previsto
                prev_y = atual_y + dir_y * passo_previsto
                fora_x = max(0.0, -prev_x) + max(0.0, prev_x - max_x)
                fora_y = max(0.0, -prev_y) + max(0.0, prev_y - max_y)
                prev_x_clamp = max(0.0, min(max_x, prev_x))
                prev_y_clamp = max(0.0, min(max_y, prev_y))
                prev_cx = prev_x_clamp + inimigo["rect"].width / 2
                prev_cy = prev_y_clamp + inimigo["rect"].height / 2
                dist_nova = math.hypot(prev_cx - jogador_cx, prev_cy - jogador_cy)
                dist_borda = min(prev_x_clamp, max_x - prev_x_clamp, prev_y_clamp, max_y - prev_y_clamp)
                borda_bonus = min(dist_borda, margem_segura) * 1.8
                centro_bonus = 0.0
                if dist_borda < margem_segura:
                    centro_dx = centro_mapa_x - inimigo_cx
                    centro_dy = centro_mapa_y - inimigo_cy
                    centro_dist = max(1.0, math.hypot(centro_dx, centro_dy))
                    centro_bonus = ((dir_x * centro_dx + dir_y * centro_dy) / centro_dist) * (margem_segura - dist_borda) * 2.2
                score = dist_nova * 2.6 + borda_bonus + centro_bonus - (fora_x + fora_y) * 12.0
                if score > melhor_score:
                    melhor_score = score
                    melhor_dir = (dir_x, dir_y)

            return melhor_dir

        def executar_ataque_larapio(inimigo):
            nonlocal tempo_ultimo_hit_inimigo, piscando_vida
            global vida, pontuacao, pontuacao_exib, pontuacao_magia, imune_tempo_restante, tempo_stun_jogador_fim
            global eliminacoes_consecutivas, eliminacoes_consecutivas_impulsiva, bonus_pontuacao
            tempo_atual = pygame.time.get_ticks()

            centro_larapio = inimigo["rect"].center
            centro_jogador = (pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2)
            distancia = math.hypot(centro_jogador[0] - centro_larapio[0], centro_jogador[1] - centro_larapio[1])
            inimigo["ultimo_ataque"] = tempo_atual
            if distancia > LARAPIO_ALCANCE_ATAQUE + 60 or imune_tempo_restante > 0:
                inimigo["estado"] = "cacando"
                return

            if absorver_dano_devota_atual():
                inimigo["estado"] = "cacando"
                return

            # Sem saque, o Larapio apenas importuna: investida curta, dano
            # controlado e chance de atordoar. Ele nao remove mais pontos aqui.
            dano_incomodo = limitar_dano_larapio(
                dano_inimigo_inicio_ajustado(max(1, int(vida_maxima * 0.06) + int(dano_inimigo_perto * 0.35))),
                vida, vida_maxima,
            )
            vida -= dano_incomodo
            imune_tempo_restante = max(imune_tempo_restante, 500)
            tempo_ultimo_hit_inimigo = tempo_atual
            piscando_vida = True
            if random.random() < 0.45:
                tempo_stun_jogador_fim = max(tempo_stun_jogador_fim, tempo_atual + 2000)
                texto_incomodo = f"INVESTIDA! -{dano_incomodo} | STUN"
            else:
                texto_incomodo = f"INVESTIDA! -{dano_incomodo}"
            efeitos_texto.append({
                "texto": texto_incomodo,
                "x": pos_x_personagem - 18,
                "y": pos_y_personagem - 34,
                "tempo_inicio": tempo_atual,
                "cor": (255, 105, 70),
            })
            inimigo["ultimo_ataque"] = tempo_atual
            inimigo["estado"] = "fugindo"
            inimigo["inicio_fuga"] = tempo_atual



        def atualizar_larapio(inimigo):
            nonlocal tempo_ultimo_spawn_larapio
            tempo_atual = pygame.time.get_ticks()
            if tempo_atual < inimigo.get("stun_fim", 0):
                return

            modo_dificil = (Variaveis.obter_modo_cartas() == "drops")
            Variaveis.larapio_tentar_roubar_chave(inimigo, tempo_atual)

            # Lógica do Portal de Fuga
            coletou = (
                inimigo.get("dinheiro_roubado", 0) > 0
                or len(inimigo.setdefault("cartas_roubadas_larapio", [])) > 0
                or inimigo.get("possui_chave_loja", False)
            )
            menos_70_vida = (inimigo["vida"] < inimigo["vida_maxima"] * 0.7)
            
            if coletou and menos_70_vida:
                if tempo_atual - inimigo.setdefault("ultimo_tempo_atingido", 0) >= 4000:
                    if inimigo.setdefault("ultimo_tick_portal", 0) == 0:
                        inimigo["ultimo_tick_portal"] = tempo_atual
                    tempo_diff = tempo_atual - inimigo["ultimo_tick_portal"]
                    if tempo_diff >= 1000:
                        ticks = tempo_diff // 1000
                        inimigo["portal_charge"] = min(100.0, inimigo.get("portal_charge", 0.0) + ticks * 1.0)
                        inimigo["ultimo_tick_portal"] = tempo_atual - (tempo_diff % 1000)
                else:
                    inimigo["ultimo_tick_portal"] = tempo_atual
            else:
                inimigo["portal_charge"] = 0.0
                inimigo["ultimo_tick_portal"] = 0

            if inimigo.get("portal_charge", 0.0) >= 100.0:
                efeitos_texto.append({
                    "texto": "LARAPIO FUGIU!",
                    "x": inimigo["rect"].centerx - 40,
                    "y": inimigo["rect"].centery - 40,
                    "tempo_inicio": tempo_atual,
                    "cor": (200, 100, 255),
                })
                tempo_ultimo_spawn_larapio = tempo_atual
                gerar_fragmentos_morte(inimigo, 1)
                if inimigo in inimigos_comum:
                    inimigos_comum.remove(inimigo)
                return

            # Efeito de moedas/pedaços de cartas caindo no chão
            if modo_dificil:
                possui_cartas_bolsa = len(inimigo.setdefault("cartas_roubadas_larapio", [])) > 0
                if possui_cartas_bolsa:
                    if config_graficos.get("efeitos_visuais", True) and config_graficos.get("particulas_ativas", True):
                        qualidade = config_graficos.get("qualidade_grafica", "alta")
                        if qualidade != "baixa":
                            intervalo_fragmento = 120 if qualidade == "alta" else 280
                            if tempo_atual - inimigo.get("ultimo_drop_moeda_ms", 0) >= intervalo_fragmento:
                                inimigo["ultimo_drop_moeda_ms"] = tempo_atual
                                gerar_pedaco_carta(inimigo["rect"].centerx, inimigo["rect"].centery, inimigo["rect"].bottom)
            else:
                if inimigo.get("roubou_pontos", False):
                    if config_graficos.get("efeitos_visuais", True) and config_graficos.get("particulas_ativas", True):
                        qualidade = config_graficos.get("qualidade_grafica", "alta")
                        if qualidade != "baixa":
                            intervalo_moeda = 100 if qualidade == "alta" else 250
                            if tempo_atual - inimigo.get("ultimo_drop_moeda_ms", 0) >= intervalo_moeda:
                                inimigo["ultimo_drop_moeda_ms"] = tempo_atual
                                gerar_moeda_larapio(inimigo["rect"].centerx, inimigo["rect"].centery, inimigo["rect"].bottom)

            if "pos_x" not in inimigo:
                inimigo["pos_x"] = float(inimigo["rect"].x)
            if "pos_y" not in inimigo:
                inimigo["pos_y"] = float(inimigo["rect"].y)

            # Lógica de arremesso de moedas atordoadoras / pedras
            if "proximo_tempo_moeda_arremessar" not in inimigo:
                inimigo["proximo_tempo_moeda_arremessar"] = tempo_atual + random.randint(
                    LARAPIO_ARREMESSO_MIN_MS,
                    LARAPIO_ARREMESSO_MAX_MS,
                )

            possui_cartas_bolsa = len(inimigo.setdefault("cartas_roubadas_larapio", [])) > 0
            pode_arremessar = False
            if modo_dificil:
                # No difícil ele taca pedras enquanto foge se tiver cartas na bolsa
                estado_atual = inimigo.get("estado", "fugindo")
                if estado_atual == "fugindo" and possui_cartas_bolsa:
                    pode_arremessar = True
            else:
                estado_atual = inimigo.get("estado", "cacando")
                if estado_atual in ("cacando", "fugindo") and not inimigo.get("possui_chave_loja"):
                    pode_arremessar = True

            jogador_stunado = tempo_atual < tempo_stun_jogador_fim
            if jogador_stunado:
                if inimigo.get("pausa_arremesso_stun_ms") is None:
                    inimigo["pausa_arremesso_stun_ms"] = tempo_atual
            else:
                pausa_inicio = inimigo.get("pausa_arremesso_stun_ms")
                if pausa_inicio is not None:
                    inimigo["proximo_tempo_moeda_arremessar"] += max(0, tempo_atual - pausa_inicio)
                    inimigo["pausa_arremesso_stun_ms"] = None

            if pode_arremessar and not jogador_stunado and tempo_atual >= inimigo["proximo_tempo_moeda_arremessar"]:
                inimigo["proximo_tempo_moeda_arremessar"] = tempo_atual + random.randint(
                    LARAPIO_ARREMESSO_MIN_MS,
                    LARAPIO_ARREMESSO_MAX_MS,
                )
                cx = pos_x_personagem + largura_personagem // 2
                cy = pos_y_personagem + altura_personagem // 2
                if math.hypot(cx - inimigo["rect"].centerx, cy - inimigo["rect"].centery) <= 500:
                    gerar_moeda_arremessada(inimigo)

            if movendo and inimigo.get("player_move_start_time") is None:
                inimigo["player_move_start_time"] = tempo_atual

            bonus = bonus_larapio(inimigo)
            velocidade_atual = inimigo.get("velocidade", Velocidade_Inimigos_1) * (1 + bonus["velocidade"])
            
            has_stolen = (
                inimigo.get("dinheiro_roubado", 0) > 0
                or len(inimigo.get("cartas_roubadas_larapio", [])) > 0
                or inimigo.get("roubou_pontos", False)
                or inimigo.get("possui_chave_loja", False)
            )
            
            if not has_stolen:
                if inimigo.get("player_move_start_time") is None:
                    velocidade_atual *= 0.3
                else:
                    tempo_desde_movimento = tempo_atual - inimigo["player_move_start_time"]
                    if tempo_desde_movimento < 4000:
                        velocidade_atual *= 0.4

            # Entre 4 e 8 segundos depois do drop, a chave vira a prioridade
            # absoluta do Larapio. Ele precisa alcanca-la fisicamente: nada de
            # coleta a distancia ou teleporte escondido.
            if not inimigo.get("possui_chave_loja"):
                chave_alvo = Variaveis.obter_chave_roubavel_larapio(inimigo["rect"].center, tempo_atual)
                if chave_alvo is not None:
                    inimigo["estado"] = "cacando_chave"
                    dx_chave = chave_alvo["rect"].centerx - inimigo["rect"].centerx
                    dy_chave = chave_alvo["rect"].centery - inimigo["rect"].centery
                    mover_larapio(inimigo, dx_chave, dy_chave, velocidade_atual * 2.2)
                    Variaveis.larapio_tentar_roubar_chave(inimigo, tempo_atual)
                    if tempo_atual - inimigo.get("ultimo_frame", 0) >= LARAPIO_INTERVALO_ANIMACAO:
                        inimigo["frame_atual"] = (inimigo.get("frame_atual", 0) + 1) % len(frames_larapio)
                        inimigo["ultimo_frame"] = tempo_atual
                    return
                if inimigo.get("estado") == "cacando_chave":
                    inimigo["estado"] = "cacando"

            # ----------------------------------------------------
            # COMPORTAMENTO MODO DIFÍCIL (DROPS DE CARTAS)
            # ----------------------------------------------------
            if modo_dificil:
                # Procurar cartas no chão qualificadas (> 2 segundos no mapa)
                cartas_elegiveis = []
                for c in Variaveis.cartas_no_chao:
                    # Verifica se a carta não está associada ao larapio_hard antigo e se passou 2s
                    if not c.get("larapio") and (tempo_atual - c.get("tempo_criado", 0) >= 2000):
                        cartas_elegiveis.append(c)

                if cartas_elegiveis:
                    # Encontrar a carta mais próxima
                    inimigo_pos = inimigo["rect"].center
                    carta_alvo = min(cartas_elegiveis, key=lambda c: math.hypot(c["rect"].centerx - inimigo_pos[0], c["rect"].centery - inimigo_pos[1]))
                    inimigo["estado"] = "cacando_carta"

                    # Mover em disparada
                    velocidade_disparada = velocidade_atual * 2.2
                    dx_c = carta_alvo["rect"].centerx - inimigo_pos[0]
                    dy_c = carta_alvo["rect"].centery - inimigo_pos[1]
                    dist_c = math.hypot(dx_c, dy_c)

                    if dist_c <= 20:
                        # Coleta a carta!
                        nome_carta = carta_alvo["nome"]
                        inimigo["cartas_roubadas_larapio"].append(nome_carta)
                        
                        # Remove a carta do chão
                        if carta_alvo in Variaveis.cartas_no_chao:
                            Variaveis.cartas_no_chao.remove(carta_alvo)

                        efeitos_texto.append({
                            "texto": f"+1 CARTA ({nome_carta})",
                            "x": inimigo["rect"].centerx,
                            "y": inimigo["rect"].centery - 30,
                            "tempo_inicio": tempo_atual,
                            "cor": (255, 80, 45),
                        })
                        # Entra em estado de fuga
                        inimigo["estado"] = "fugindo"
                        inimigo["inicio_fuga"] = tempo_atual
                    else:
                        mover_larapio(inimigo, dx_c, dy_c, velocidade_disparada)
                else:
                    # Sem cartas qualificadas: corre aleatoriamente/fuga do player
                    inimigo["estado"] = "fugindo"
                    cx = pos_x_personagem + largura_personagem // 2
                    cy = pos_y_personagem + altura_personagem // 2
                    # Fuga em velocidade normal
                    velocidade_fuga = velocidade_atual
                    fugir_x, fugir_y = direcao_fuga_larapio(inimigo, cx, cy, velocidade_fuga)
                    mover_larapio(inimigo, fugir_x, fugir_y, velocidade_fuga)

            # ----------------------------------------------------
            # COMPORTAMENTO MODO NORMAL (ROUBO DE PONTOS)
            # ----------------------------------------------------
            else:
                if inimigo.get("ir_direto_roubar", False) and tempo_atual >= inimigo.get("speed_boost_tempo", 0):
                    inimigo["ir_direto_roubar"] = False

                estado = inimigo.get("estado", "cacando")
                cx = pos_x_personagem + largura_personagem // 2
                cy = pos_y_personagem + altura_personagem // 2
                dx = cx - inimigo["rect"].centerx
                dy = cy - inimigo["rect"].centery
                distancia = math.hypot(dx, dy)

                if tempo_atual < inimigo.get("speed_boost_tempo", 0):
                    velocidade_atual *= 1.75

                if estado == "cacando":
                    if distancia <= LARAPIO_ALCANCE_ATAQUE:
                        if inimigo.get("ir_direto_roubar", False):
                            executar_ataque_larapio(inimigo)
                            return
                        elif tempo_atual - inimigo.get("ultimo_ataque", 0) >= inimigo.get("cooldown_ataque", 1200):
                            inimigo["estado"] = "preparando_ataque"
                            inimigo["inicio_preparo_ataque"] = tempo_atual
                            inimigo["vel_x"] = 0.0
                            inimigo["vel_y"] = 0.0
                        else:
                            lateral_x = -dy * 0.25
                            lateral_y = dx * 0.25
                            mover_larapio(inimigo, dx + lateral_x, dy + lateral_y, velocidade_atual)
                    else:
                        lateral_x = -dy * 0.25
                        lateral_y = dx * 0.25
                        if inimigo.get("ir_direto_roubar", False):
                            mover_larapio(inimigo, dx, dy, velocidade_atual)
                        else:
                            mover_larapio(inimigo, dx + lateral_x, dy + lateral_y, velocidade_atual)
                elif estado == "preparando_ataque":
                    mover_larapio(inimigo, dx, dy, velocidade_atual * 0.45)
                    if tempo_atual - inimigo.get("inicio_preparo_ataque", tempo_atual) >= LARAPIO_TEMPO_PREPARO_ATAQUE:
                        executar_ataque_larapio(inimigo)
                elif estado == "fugindo":
                    if tempo_atual - inimigo.get("inicio_fuga", tempo_atual) >= 14000:
                        inimigo["estado"] = "cacando"
                        inimigo.pop("target_quina", None)
                        return
                    velocidade_fuga = inimigo.get("velocidade", Velocidade_Inimigos_1) * (1.55 + bonus["velocidade"])
                    if tempo_atual < inimigo.get("tempo_fuga_fantasma", 0):
                        velocidade_fuga *= 1.85
                    fugir_x, fugir_y = direcao_fuga_larapio(inimigo, cx, cy, velocidade_fuga)
                    mover_larapio(inimigo, fugir_x, fugir_y, velocidade_fuga)

            intervalo_animacao = LARAPIO_INTERVALO_ANIMACAO_FUGA if inimigo.get("estado") == "fugindo" else LARAPIO_INTERVALO_ANIMACAO
            if tempo_atual - inimigo.get("ultimo_frame", 0) >= intervalo_animacao:
                inimigo["frame_atual"] = (inimigo.get("frame_atual", 0) + 1) % len(frames_larapio)
                inimigo["ultimo_frame"] = tempo_atual

        def tentar_spawn_larapio(tempo_decorrido_run, limite_inimigos_run):
            nonlocal tempo_ultimo_spawn_larapio, alerta_larapio_mostrado
            if tempo_decorrido_run < LARAPIO_SPAWN_APOS_SEG:
                return
            
            modo_dificil = (Variaveis.obter_modo_cartas() == "drops")
            cooldown_larapio = 300000 if modo_dificil else LARAPIO_COOLDOWN_SPAWN_MS
            if tempo_atual - tempo_ultimo_spawn_larapio < cooldown_larapio:
                return
            if mostrar_tutorial or r_press or boss_vivo1 or boss_morte_processada:
                return
            if any(ini.get("tipo") == TIPO_LARAPIO for ini in inimigos_comum):
                return

            if modo_dificil:
                cobica = 1.0
                chance_spawn = 1.0
                pct_roubo = 0.25
            else:
                tempo_segurando, chance_spawn, cobica = calcular_cobica_larapio(tempo_decorrido_run)
                limiar_pontos = float(custo_carta_atual) * 3.0
                if pontuacao_exib >= limiar_pontos:
                    fator_riqueza = pontuacao_exib / max(1.0, limiar_pontos)
                    pct_roubo = min(0.50, 0.15 + 0.10 * (fator_riqueza - 1.0))
                else:
                    pct_roubo = 0.15

            # Reseta o timer para a próxima tentativa de spawn
            tempo_ultimo_spawn_larapio = tempo_atual

            # Verifica a chance de spawn no modo normal
            if not modo_dificil:
                chance_spawn = 1.0

            print(f"==================================================")
            print(f"[TESTE DEBUG] LARAPIO FOI CHAMADO E GERADO NA TELA Aos {tempo_decorrido_run} Segundos!")
            if not modo_dificil:
                print(f"  - Pontuacao Exibida: {pontuacao_exib} | Custo Carta: {custo_carta_atual}")
                print(f"  - Cobica Calculada: {cobica:.2f} | Chance de Spawn: {chance_spawn * 100:.1f}%")
                print(f"  - Porcentagem de Roubo Projetada: {pct_roubo * 100:.1f}%")
            print(f"==================================================")

            borda = random.choice(["esquerda", "direita", "superior", "inferior"])
            if borda == "esquerda":
                novo = criar_inimigo(0, random.randint(0, int(altura_mapa) - int(altura_inimigo)), tipo=TIPO_LARAPIO)
            elif borda == "direita":
                novo = criar_inimigo(int(largura_mapa) - int(largura_inimigo), random.randint(0, int(altura_mapa) - int(altura_inimigo)), tipo=TIPO_LARAPIO)
            elif borda == "superior":
                novo = criar_inimigo(random.randint(0, int(largura_mapa) - int(largura_inimigo)), 0, tipo=TIPO_LARAPIO)
            else:
                novo = criar_inimigo(random.randint(0, int(largura_mapa) - int(largura_inimigo)), int(altura_mapa) - int(altura_inimigo), tipo=TIPO_LARAPIO)
            novo["cobica_spawn"] = cobica
            novo["chance_spawn"] = chance_spawn
            novo["tempo_segurando_pontos"] = 0
            inimigos_comum.append(novo)
            efeitos_texto.append({
                "texto": "LARAPIO!",
                "x": novo["rect"].x,
                "y": novo["rect"].y - 36,
                "tempo_inicio": tempo_atual,
                "cor": (255, 218, 70),
            })
            if not alerta_larapio_mostrado:
                alerta_larapio_mostrado = True


        def distancia_ponto_segmento(px, py, ax, ay, bx, by):
            abx = bx - ax
            aby = by - ay
            ab_len2 = abx * abx + aby * aby
            if ab_len2 <= 0:
                return math.hypot(px - ax, py - ay)
            t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / ab_len2))
            proj_x = ax + abx * t
            proj_y = ay + aby * t
            return math.hypot(px - proj_x, py - proj_y)

        def contar_ecos_vivos_condutor():
            return sum(1 for inimigo in inimigos_comum if inimigo.get("eco_vinculado") and inimigo.get("vida", 0) > 0)

        def limpar_ecos_condutor(remover_restantes=False):
            for inimigo in list(inimigos_comum):
                if inimigo.get("eco_vinculado"):
                    inimigo.pop("eco_vinculado", None)
                    inimigo.pop("condutor_boost_fim", None)
                    if "velocidade_base_condutor" in inimigo:
                        inimigo["velocidade"] = inimigo.pop("velocidade_base_condutor")
                    if remover_restantes and inimigo in inimigos_comum:
                        gerar_fragmentos_morte(inimigo, 1)
                        inimigos_comum.remove(inimigo)

        def posicao_segura_condutor():
            px = pos_x_personagem + largura_personagem // 2
            py = pos_y_personagem + altura_personagem // 2
            margem = 120
            melhor = (largura_mapa // 2, altura_mapa // 2)
            melhor_dist = -1
            candidatos = [
                (margem, margem),
                (largura_mapa - margem, margem),
                (margem, altura_mapa - margem),
                (largura_mapa - margem, altura_mapa - margem),
                (largura_mapa // 2, margem),
                (largura_mapa // 2, altura_mapa - margem),
            ]
            for cx_c, cy_c in candidatos:
                dist = math.hypot(cx_c - px, cy_c - py)
                if dist > melhor_dist:
                    melhor_dist = dist
                    melhor = (cx_c, cy_c)
            return melhor

        def criar_condutor_de_ecos():
            nonlocal miniboss_condutor, miniboss_condutor_spawnado
            cx, cy = posicao_segura_condutor()
            rect = frames_condutor[0].get_rect(center=(int(cx), int(cy)))
            vida_base = max(900, int(dano_person_hit * 65 + vida_inimigo_maxima * 5.5))
            volume_musica_condutor = Musica_tema_fases.get_volume()
            volume_ambiente_condutor = Som_tema_fases.get_volume()
            Musica_tema_fases.set_volume(max(0.04, volume_musica_condutor * 0.45))
            Som_tema_fases.set_volume(max(0.04, volume_ambiente_condutor * 0.55))
            miniboss_condutor = {
                "ativo": True,
                "is_boss": True,
                "eh_miniboss": True,
                "rect": rect,
                "pos_x": float(rect.x),
                "pos_y": float(rect.y),
                "vida": vida_base,
                "vida_maxima": vida_base,
                "entrada_inicio": tempo_atual,
                "entrada_fim": tempo_atual + MINIBOSS_CONDUTOR_ENTRADA_MS,
                "ultimo_disparo": tempo_atual,
                "proximo_olhar": tempo_atual + 4200,
                "olhar_inicio": 0,
                "olhar_alvo": None,
                "olhar_travou": False,
                "fase2_anunciada": False,
                "frame_atual": 0,
                "ultimo_frame": tempo_atual,
                "direcao_x": 1,
                "sentido_orbita": random.choice((-1, 1)),
                "volume_musica": volume_musica_condutor,
                "volume_ambiente": volume_ambiente_condutor,
                "volume_restaurado": False,
            }
            miniboss_condutor_spawnado = True
            efeitos_texto.append({
                "texto": "ARAUTO: CONDUTOR DE ECOS",
                "x": largura_mapa // 2 - 210,
                "y": int(altura_mapa * 0.18),
                "tempo_inicio": tempo_atual,
                "cor": (180, 225, 255),
            })
            ondas_choque.append({
                "cx": rect.centerx,
                "cy": rect.centery,
                "raio_atual": 10.0,
                "raio_max": 430.0,
                "velocidade": 10.0,
                "cor": (120, 80, 255),
            })
            vincular_ecos_condutor(MINIBOSS_CONDUTOR_ECOS_INICIAIS)

        def vincular_ecos_condutor(quantidade):
            if not miniboss_condutor:
                return

            # A ruptura limpa a arena: o confronto sempre começa com os ecos do Arauto.
            for inimigo in list(inimigos_comum):
                if inimigo.get("tipo") == TIPO_LARAPIO and (
                    inimigo.get("dinheiro_roubado", 0) > 0 or inimigo.get("cartas_roubadas_larapio")
                ):
                    processar_morte_inimigo(inimigo)
                else:
                    gerar_fragmentos_morte(inimigo, 1)
                inimigos_comum.remove(inimigo)

            candidatos = []
            for indice in range(quantidade):
                ang = (math.tau / max(1, quantidade)) * indice + random.uniform(-0.25, 0.25)
                raio = 175
                sx = int(min(max(0, miniboss_condutor["rect"].centerx + math.cos(ang) * raio), largura_mapa - largura_inimigo))
                sy = int(min(max(0, miniboss_condutor["rect"].centery + math.sin(ang) * raio), altura_mapa - altura_inimigo))
                tipo_eco = random.choice([1, 2, 3, 4, 5])
                inimigo = criar_inimigo(sx, sy, tipo=tipo_eco)
                inimigo["eco_vinculado"] = True
                inimigo["eco_vinculado_inicio"] = tempo_atual
                inimigo["vida_maxima"] = max(inimigo.get("vida_maxima", vida_inimigo_maxima), vida_inimigo_maxima * 1.25)
                inimigo["vida"] = inimigo["vida_maxima"]
                inimigos_comum.append(inimigo)
                candidatos.append(inimigo)
                efeitos_texto.append({
                    "texto": "ECO VINCULADO",
                    "x": inimigo["rect"].x,
                    "y": inimigo["rect"].y - 30,
                    "tempo_inicio": tempo_atual,
                    "cor": (160, 210, 255),
                })

        def tentar_spawn_condutor(tempo_decorrido_run):
            if miniboss_condutor_spawnado or mostrar_tutorial or r_press or boss_vivo1 or boss_morte_processada:
                return
            if tempo_decorrido_run < MINIBOSS_CONDUTOR_TEMPO_SEG:
                return
            criar_condutor_de_ecos()

        def posicao_olho_condutor():
            rect = miniboss_condutor["rect"]
            proporcao_x = 0.68 if miniboss_condutor.get("direcao_x", 1) >= 0 else 0.32
            return (int(rect.x + rect.width * proporcao_x), int(rect.y + rect.height * 0.45))

        def disparar_condutor():
            cx = pos_x_personagem + largura_personagem // 2
            cy = pos_y_personagem + altura_personagem // 2
            olho_x, olho_y = posicao_olho_condutor()
            dx = cx - olho_x
            dy = cy - olho_y
            dist = max(1.0, math.hypot(dx, dy))
            vel = 4.6
            disparos_inimigos.append({
                "rect": pygame.Rect(olho_x - 8, olho_y - 8, 17, 17),
                "vx": (dx / dist) * vel,
                "vy": (dy / dist) * vel,
                "dano": int((vida_maxima * 0.052) + dano_inimigo_longe),
                "cor": (160, 105, 255),
                "origem": "arauto",
            })

        def mover_condutor(fase2):
            rect = miniboss_condutor["rect"]
            px = pos_x_personagem + largura_personagem / 2
            py = pos_y_personagem + altura_personagem / 2
            cx, cy = rect.center
            dx, dy = px - cx, py - cy
            distancia = max(1.0, math.hypot(dx, dy))
            nx, ny = dx / distancia, dy / distancia
            sentido = miniboss_condutor.get("sentido_orbita", 1)

            radial = 0.0
            if distancia < MINIBOSS_CONDUTOR_DISTANCIA_MIN:
                radial = -0.85
            elif distancia > MINIBOSS_CONDUTOR_DISTANCIA_MAX:
                radial = 0.65
            tangente_x, tangente_y = -ny * sentido, nx * sentido
            dir_x = tangente_x + nx * radial
            dir_y = tangente_y + ny * radial
            norma = max(1.0, math.hypot(dir_x, dir_y))
            velocidade = MINIBOSS_CONDUTOR_VELOCIDADE * (1.25 if fase2 else 1.0)
            velocidade *= fator_mundo_racional(aurea, racional_dilatacao_fim, tempo_atual)
            passo_x = (dir_x / norma) * velocidade * dt
            passo_y = (dir_y / norma) * velocidade * dt

            margem = 18
            novo_x = max(margem, min(largura_mapa - rect.width - margem, rect.x + passo_x))
            novo_y = max(margem, min(altura_mapa - rect.height - margem, rect.y + passo_y))
            if abs(novo_x - rect.x) < 0.05 and abs(passo_x) > 0.2:
                miniboss_condutor["sentido_orbita"] = -sentido
            miniboss_condutor["pos_x"] = float(novo_x)
            miniboss_condutor["pos_y"] = float(novo_y)
            rect.x = int(novo_x)
            rect.y = int(novo_y)
            if abs(passo_x) > 0.05:
                miniboss_condutor["direcao_x"] = 1 if passo_x > 0 else -1

        def iniciar_olhar_condutor():
            miniboss_condutor["olhar_inicio"] = tempo_atual
            miniboss_condutor["olhar_alvo"] = (
                pos_x_personagem + largura_personagem // 2,
                pos_y_personagem + altura_personagem // 2,
            )
            miniboss_condutor["olhar_travou"] = False
            efeitos_texto.append({
                "texto": "OLHAR DA RUPTURA — USE UM ECO COMO COBERTURA!",
                "x": largura_mapa // 2 - 250,
                "y": int(altura_mapa * 0.16),
                "tempo_inicio": tempo_atual,
                "cor": (235, 150, 255),
            })

        def resolver_olhar_condutor(fase2):
            nonlocal tempo_ultimo_hit_inimigo, piscando_vida
            global vida, imune_tempo_restante
            origem = posicao_olho_condutor()
            alvo = miniboss_condutor.get("olhar_alvo") or origem
            dx, dy = alvo[0] - origem[0], alvo[1] - origem[1]
            distancia = max(1.0, math.hypot(dx, dy))
            alcance = math.hypot(largura_mapa, altura_mapa) * 1.25
            fim = (origem[0] + dx / distancia * alcance, origem[1] + dy / distancia * alcance)

            bloqueadores = []
            for inimigo in inimigos_comum:
                if inimigo.get("eco_vinculado") and inimigo["rect"].clipline(origem, fim):
                    eco_dx = inimigo["rect"].centerx - origem[0]
                    eco_dy = inimigo["rect"].centery - origem[1]
                    projecao_eco = eco_dx * (dx / distancia) + eco_dy * (dy / distancia)
                    if 0 < projecao_eco <= distancia:
                        bloqueadores.append((projecao_eco, inimigo))

            bloqueado = False
            if bloqueadores:
                _, eco = min(bloqueadores, key=lambda item: item[0])
                bloqueado = True
                fim = eco["rect"].center
                efeitos_texto.append({
                    "texto": "ECO SACRIFICADO — OLHAR BLOQUEADO!",
                    "x": eco["rect"].x - 70,
                    "y": eco["rect"].y - 42,
                    "tempo_inicio": tempo_atual,
                    "cor": (150, 235, 255),
                })
                processar_morte_inimigo(eco)
                if eco in inimigos_comum:
                    inimigos_comum.remove(eco)
            else:
                jogador_cx = pos_x_personagem + largura_personagem // 2
                jogador_cy = pos_y_personagem + altura_personagem // 2
                acertou = distancia_ponto_segmento(jogador_cx, jogador_cy, origem[0], origem[1], fim[0], fim[1]) <= 42
                if acertou and imune_tempo_restante <= 0 and not absorver_dano_devota_atual():
                    percentual = 0.18 if fase2 else 0.14
                    dano = max(1, int(vida_maxima * percentual + dano_inimigo_longe * 0.35 - Resistencia))
                    vida = max(0, vida - dano)
                    imune_tempo_restante = 700
                    tempo_ultimo_hit_inimigo = tempo_atual
                    piscando_vida = True
                    Dano_person.play()
                    efeitos_texto.append({
                        "texto": f"OLHAR DA RUPTURA -{dano}",
                        "x": pos_x_personagem - 30,
                        "y": pos_y_personagem - 38,
                        "tempo_inicio": tempo_atual,
                        "cor": (255, 80, 190),
                    })

            raios_olhar_condutor.append({
                "inicio": tempo_atual,
                "origem": origem,
                "fim": fim,
                "bloqueado": bloqueado,
            })

        def finalizar_condutor():
            nonlocal miniboss_condutor
            if not miniboss_condutor:
                return
            cx, cy = miniboss_condutor["rect"].center
            if not miniboss_condutor.get("volume_restaurado", False):
                Musica_tema_fases.set_volume(miniboss_condutor.get("volume_musica", Musica_tema_fases.get_volume()))
                Som_tema_fases.set_volume(miniboss_condutor.get("volume_ambiente", Som_tema_fases.get_volume()))
            limpar_ecos_condutor(remover_restantes=True)
            gerar_explosao_branca(cx, cy)
            ondas_choque.append({
                "cx": cx,
                "cy": cy,
                "raio_atual": 20.0,
                "raio_max": 520.0,
                "velocidade": 14.0,
                "cor": (165, 90, 255),
            })
            efeitos_texto.append({
                "texto": "ARAUTO: CONDUTOR DE ECOS DESFEITO",
                "x": cx - 130,
                "y": cy - 70,
                "tempo_inicio": tempo_atual,
                "cor": (190, 235, 255),
            })
            fragmentos_ruptura.append(evolucoes_manifestacao.criar_fragmento(cx, cy, tempo_atual))
            efeitos_texto.append({
                "texto": "UM FRAGMENTO DA RUPTURA PERMANECE...",
                "x": cx - 150,
                "y": cy + 54,
                "tempo_inicio": tempo_atual,
                "cor": (220, 150, 255),
            })
            miniboss_condutor = None

        def aplicar_dano_ao_condutor(dano_bruto, cor_dano):
            if not miniboss_condutor:
                return
            vivos = contar_ecos_vivos_condutor()
            reducao = min(0.80, vivos * MINIBOSS_CONDUTOR_REDUCAO_POR_ECO)
            dano_final = max(1, dano_bruto * (1.0 - reducao))
            miniboss_condutor["vida"] -= dano_final
            if reducao > 0:
                cor_dano = (90, 220, 255)
            Variaveis.registrar_efeito_texto(
                efeitos_texto,
                "-" + str(int(dano_final)),
                miniboss_condutor["rect"].centerx - 18,
                miniboss_condutor["rect"].y - 24,
                tempo_atual,
                cor_dano,
                chave=("disparo-condutor", int(tempo_atual // 80)),
            )
            if miniboss_condutor["vida"] <= 0:
                finalizar_condutor()

        def atualizar_condutor():
            if not miniboss_condutor or not miniboss_condutor.get("ativo"):
                return
            rect = miniboss_condutor["rect"]
            if tempo_atual - miniboss_condutor.get("ultimo_frame", 0) >= 180:
                miniboss_condutor["frame_atual"] = (miniboss_condutor.get("frame_atual", 0) + 1) % len(frames_condutor)
                miniboss_condutor["ultimo_frame"] = tempo_atual
            if tempo_atual < miniboss_condutor["entrada_fim"]:
                return
            if not miniboss_condutor.get("volume_restaurado", False):
                Musica_tema_fases.set_volume(miniboss_condutor.get("volume_musica", Musica_tema_fases.get_volume()))
                Som_tema_fases.set_volume(miniboss_condutor.get("volume_ambiente", Som_tema_fases.get_volume()))
                miniboss_condutor["volume_restaurado"] = True

            fase2 = miniboss_condutor["vida"] <= miniboss_condutor["vida_maxima"] * 0.5
            if fase2 and not miniboss_condutor.get("fase2_anunciada"):
                miniboss_condutor["fase2_anunciada"] = True
                miniboss_condutor["sentido_orbita"] *= -1
                miniboss_condutor["proximo_olhar"] = min(miniboss_condutor.get("proximo_olhar", tempo_atual + 1500), tempo_atual + 1500)
                efeitos_texto.append({
                    "texto": "O OLHO DA RUPTURA DESPERTOU!",
                    "x": largura_mapa // 2 - 180,
                    "y": int(altura_mapa * 0.20),
                    "tempo_inicio": tempo_atual,
                    "cor": (255, 85, 210),
                })
                ondas_choque.append({
                    "cx": rect.centerx,
                    "cy": rect.centery,
                    "raio_atual": 18.0,
                    "raio_max": 360.0,
                    "velocidade": 12.0,
                    "cor": (220, 70, 255),
                })
            inicio_olhar = miniboss_condutor.get("olhar_inicio", 0)
            if not inicio_olhar:
                mover_condutor(fase2)
            if inicio_olhar:
                carga = 1050 if fase2 else MINIBOSS_CONDUTOR_OLHAR_CARGA_MS
                idade = tempo_atual - inicio_olhar
                if idade < carga * 0.58:
                    miniboss_condutor["olhar_alvo"] = (
                        pos_x_personagem + largura_personagem // 2,
                        pos_y_personagem + altura_personagem // 2,
                    )
                elif not miniboss_condutor.get("olhar_travou"):
                    miniboss_condutor["olhar_travou"] = True
                    efeitos_texto.append({
                        "texto": "ALVO TRAVADO!",
                        "x": pos_x_personagem - 28,
                        "y": pos_y_personagem - 46,
                        "tempo_inicio": tempo_atual,
                        "cor": (255, 100, 210),
                    })
                if idade >= carga:
                    resolver_olhar_condutor(fase2)
                    miniboss_condutor["olhar_inicio"] = 0
                    miniboss_condutor["olhar_alvo"] = None
                    cooldown_olhar = 6200 if fase2 else MINIBOSS_CONDUTOR_OLHAR_COOLDOWN
                    miniboss_condutor["proximo_olhar"] = tempo_atual + cooldown_olhar
            elif tempo_atual >= miniboss_condutor.get("proximo_olhar", tempo_atual + 1):
                iniciar_olhar_condutor()

            intervalo_disparo_arauto = 1750 if fase2 else MINIBOSS_CONDUTOR_DISPARO_COOLDOWN
            if not miniboss_condutor.get("olhar_inicio") and tempo_atual - miniboss_condutor["ultimo_disparo"] >= intervalo_disparo_arauto:
                miniboss_condutor["ultimo_disparo"] = tempo_atual
                disparar_condutor()

        def desenhar_condutor(tela):
            if not miniboss_condutor:
                return
            rect = miniboss_condutor["rect"]
            vivos = contar_ecos_vivos_condutor()
            for inimigo in inimigos_comum:
                if inimigo.get("eco_vinculado"):
                    pygame.draw.line(tela, (115, 205, 255), rect.center, inimigo["rect"].center, 1)
                    pygame.draw.circle(tela, (145, 95, 255), inimigo["rect"].center, 18, 2)
                    pygame.draw.circle(tela, (160, 230, 255), (inimigo["rect"].centerx, inimigo["rect"].bottom), 12, 2)
            frame = frames_condutor[miniboss_condutor.get("frame_atual", 0) % len(frames_condutor)]
            if miniboss_condutor.get("direcao_x", 1) < 0:
                frame = pygame.transform.flip(frame, True, False)
            desenhar_sombra(tela, rect.x, rect.y, rect.width, rect.height)
            aura_raio = int(rect.width * 0.70 + 8 * math.sin(tempo_atual * 0.006))
            pygame.draw.circle(tela, (110, 70, 220), rect.center, aura_raio, 2)
            pygame.draw.circle(tela, (90, 210, 255), rect.center, max(18, aura_raio - 24), 1)

            alvo_olhar = miniboss_condutor.get("olhar_alvo")
            if miniboss_condutor.get("olhar_inicio") and alvo_olhar:
                travou = miniboss_condutor.get("olhar_travou", False)
                pulso = 5 + int(abs(math.sin(tempo_atual * 0.018)) * 4)
                cor_mira = (255, 70, 200) if travou else (185, 120, 255)
                origem_olhar = posicao_olho_condutor()
                pygame.draw.line(tela, cor_mira, origem_olhar, alvo_olhar, pulso)
                pygame.draw.circle(tela, cor_mira, (int(alvo_olhar[0]), int(alvo_olhar[1])), 24, 2)
                pygame.draw.circle(tela, (255, 225, 255), (int(alvo_olhar[0]), int(alvo_olhar[1])), 7, 1)
            tela.blit(frame, rect)
            reducao = vivos * MINIBOSS_CONDUTOR_REDUCAO_POR_ECO
            barra_w = min(430, int(largura_mapa * 0.42))
            barra_x = int((largura_mapa - barra_w) / 2)
            barra_y = 54
            painel_barra = pygame.Surface((barra_w + 24, 58), pygame.SRCALPHA)
            pygame.draw.rect(painel_barra, (10, 5, 24, 210), painel_barra.get_rect(), border_radius=9)
            pygame.draw.rect(painel_barra, (155, 80, 235, 180), painel_barra.get_rect(), 1, border_radius=9)
            tela.blit(painel_barra, (barra_x - 12, barra_y - 28))
            fonte_nome = pygame.font.Font(None, 23)
            fase_texto = "FASE II" if miniboss_condutor["vida"] <= miniboss_condutor["vida_maxima"] * 0.5 else "FASE I"
            titulo = fonte_nome.render(f"ARAUTO — CONDUTOR DE ECOS  |  {fase_texto}", True, (235, 220, 255))
            tela.blit(titulo, titulo.get_rect(center=(largura_mapa // 2, barra_y - 13)))
            desenhar_barra_de_vida(tela, barra_x, barra_y, barra_w, 13, miniboss_condutor["vida"], miniboss_condutor["vida_maxima"], False, None)
            fonte_eco = pygame.font.Font(None, 20)
            texto_eco = fonte_eco.render(f"ECOS: {vivos}/2  |  PROTECAO: {int(reducao * 100)}%", True, (150, 225, 255))
            tela.blit(texto_eco, texto_eco.get_rect(center=(largura_mapa // 2, barra_y + 26)))

        def atualizar_e_desenhar_vfx_condutor(tela):
            for rompido in list(ecos_rompidos_condutor):
                idade = tempo_atual - rompido["inicio"]
                if idade > 480:
                    ecos_rompidos_condutor.remove(rompido)
                    continue
                raio = int(8 + idade * 0.16)
                pygame.draw.circle(tela, (170, 230, 255), (rompido["x"], rompido["y"]), raio, 2)
                pygame.draw.circle(tela, (180, 90, 255), (rompido["x"], rompido["y"]), max(4, raio - 8), 1)

            for raio_olhar in list(raios_olhar_condutor):
                idade = tempo_atual - raio_olhar["inicio"]
                if idade > 360:
                    raios_olhar_condutor.remove(raio_olhar)
                    continue
                progresso = idade / 360.0
                alpha = max(40, int(255 * (1.0 - progresso)))
                largura_raio = max(3, int(24 * (1.0 - progresso)))
                cor = (120, 225, 255, alpha) if raio_olhar.get("bloqueado") else (255, 65, 205, alpha)
                camada = pygame.Surface((largura_mapa, altura_mapa), pygame.SRCALPHA)
                pygame.draw.line(camada, cor, raio_olhar["origem"], raio_olhar["fim"], largura_raio)
                pygame.draw.line(camada, (255, 245, 255, alpha), raio_olhar["origem"], raio_olhar["fim"], max(1, largura_raio // 4))
                tela.blit(camada, (0, 0))



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

        pedacos_cartas = []

        def gerar_pedaco_carta(px, py, bottom_y):
            vx = random.uniform(-1.5, 1.5)
            vy = random.uniform(-4.0, -2.0)
            cor = random.choice([
                (147, 112, 219),  # Purple
                (30, 144, 255),   # Blue
                (0, 255, 230),    # Cyan
                (50, 205, 50),    # Lime Green
                (255, 215, 0)     # Gold
            ])
            pedacos_cartas.append({
                "x": float(px),
                "y": float(py),
                "vx": vx,
                "vy": vy,
                "ground_y": float(bottom_y),
                "bounces": 0,
                "inicio_ms": pygame.time.get_ticks(),
                "rotacao": random.uniform(0, 360),
                "vel_rotacao": random.uniform(-6, 6),
                "w": random.randint(7, 10),
                "h": random.randint(10, 14),
                "cor": cor
            })

        def atualizar_e_desenhar_pedacos_cartas(tela):
            if not (config_graficos.get("particulas_ativas", True) and config_graficos.get("efeitos_visuais", True)):
                pedacos_cartas.clear()
                return

            tempo_atual = pygame.time.get_ticks()
            novas_pedacos = []
            
            for m in pedacos_cartas:
                idade = tempo_atual - m["inicio_ms"]
                if idade >= 2000:
                    continue  # desaparece em 2s
                
                # Física de gravidade e quique no chão
                if m["y"] < m["ground_y"] or m["vy"] < 0:
                    m["x"] += m["vx"]
                    m["y"] += m["vy"]
                    m["vy"] += 0.22  # gravidade
                    m["rotacao"] += m["vel_rotacao"]
                else:
                    if m["bounces"] < 2:
                        m["vy"] = -m["vy"] * 0.4
                        m["vx"] *= 0.6
                        m["bounces"] += 1
                        m["y"] = m["ground_y"] - 1
                    else:
                        m["vy"] = 0
                        m["vx"] = 0
                
                # Fade out nos últimos 500ms
                if idade > 1500:
                    alpha = int(255 * (1.0 - (idade - 1500) / 500.0))
                else:
                    alpha = 255
                
                # Desenhar pedaço de carta
                w, h = m["w"], m["h"]
                surf = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
                cor_val = m["cor"] + (alpha,)
                pygame.draw.rect(surf, cor_val, (2, 2, w, h))
                pygame.draw.rect(surf, (255, 255, 255, alpha), (2, 2, w, h), 1)
                
                rot_surf = pygame.transform.rotate(surf, m["rotacao"])
                rot_rect = rot_surf.get_rect(center=(int(m["x"]), int(m["y"])))
                tela.blit(rot_surf, rot_rect.topleft)
                novas_pedacos.append(m)
                
            pedacos_cartas[:] = novas_pedacos

        moedas_larapio = []

        def gerar_moeda_larapio(px, py, bottom_y):
            vx = random.uniform(-1.2, 1.2)
            vy = random.uniform(-3.5, -1.5)
            moedas_larapio.append({
                "x": float(px),
                "y": float(py),
                "vx": vx,
                "vy": vy,
                "ground_y": float(bottom_y),
                "bounces": 0,
                "inicio_ms": pygame.time.get_ticks(),
                "rotacao": random.uniform(0, 360),
                "vel_rotacao": random.uniform(-5, 5),
                "tamanho": random.randint(3, 5),
                "cor": random.choice([
                    (255, 223, 0),   # Golden
                    (212, 175, 55),  # Metallic Gold
                    (255, 215, 0)    # Bright Yellow Gold
                ])
            })

        def atualizar_e_desenhar_moedas_larapio(tela):
            if not (config_graficos.get("particulas_ativas", True) and config_graficos.get("efeitos_visuais", True)):
                moedas_larapio.clear()
                return

            tempo_atual = pygame.time.get_ticks()
            novas_moedas = []
            
            for m in moedas_larapio:
                idade = tempo_atual - m["inicio_ms"]
                if idade >= 2000:
                    continue  # desaparece em 2s
                
                # Física de gravidade e quique no chão
                if m["y"] < m["ground_y"] or m["vy"] < 0:
                    m["x"] += m["vx"]
                    m["y"] += m["vy"]
                    m["vy"] += 0.22  # gravidade
                    m["rotacao"] += m["vel_rotacao"]
                else:
                    if m["bounces"] < 2:
                        m["vy"] = -m["vy"] * 0.4  # quica com menos energia
                        m["vx"] *= 0.6
                        m["bounces"] += 1
                        m["y"] = m["ground_y"] - 1
                    else:
                        m["vy"] = 0
                        m["vx"] = 0
                
                # Fade out nos últimos 500ms
                if idade > 1500:
                    alpha = int(255 * (1.0 - (idade - 1500) / 500.0))
                else:
                    alpha = 255
                
                # Desenhar moeda
                r = m["tamanho"]
                surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                
                cor_interna = m["cor"] + (alpha,)
                cor_borda = (180, 130, 20, alpha)
                
                pygame.draw.circle(surf, cor_interna, (r + 1, r + 1), r)
                pygame.draw.circle(surf, cor_borda, (r + 1, r + 1), r, 1)
                
                tela.blit(surf, (int(m["x"] - r - 1), int(m["y"] - r - 1)))
                novas_moedas.append(m)
                
            moedas_larapio[:] = novas_moedas

        moedas_arremessadas = []

        def gerar_moeda_arremessada(inimigo):
            global pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, dt
            cx = pos_x_personagem + largura_personagem // 2
            cy = pos_y_personagem + altura_personagem // 2
            lx = inimigo["rect"].centerx
            ly = inimigo["rect"].centery
            dx = cx - lx
            dy = cy - ly
            dist = math.hypot(dx, dy)
            if dist <= 0:
                return
            
            speed = 8.5
            vx = (dx / dist) * speed
            vy = (dy / dist) * speed
            
            is_pedra = True

            moedas_arremessadas.append({
                "x": float(lx),
                "y": float(ly),
                "vx": vx,
                "vy": vy,
                "rect": pygame.Rect(lx - 6, ly - 6, 12, 12),
                "rotacao": random.uniform(0, 360),
                "vel_rotacao": random.uniform(8, 16),
                "larapio_id": id(inimigo),
                "is_pedra": is_pedra,
                "apenas_stun": True,
            })

        def atualizar_e_desenhar_moedas_arremessadas(tela):
            global tempo_stun_jogador_fim, vida, tempo_ultimo_hit_inimigo, piscando_vida, dt
            global pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem
            global moedas_arremessadas
            global velocidade_personagem, intervalo_disparo, dano_person_hit, chance_critico, roubo_de_vida, quantidade_roubo_vida, tempo_cooldown_dash, Petro_active, Resistencia, vida_petro, vida_maxima_petro, dano_petro, xp_petro, petro_evolucao, Resistencia_petro, Chance_Sorte, Poison_Active, Dano_Veneno_Acumulado, Executa_inimigo, Ultimo_Estalo, Mercenaria_Active, Valor_Bonus, Tempo_cura, porcentagem_cura, trembo, cartas_compradas, vida_maxima

            tempo_atual = pygame.time.get_ticks()
            novas_arremessadas = []
            
            player_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
            
            for m in moedas_arremessadas:
                m["x"] += m["vx"] * dt
                m["y"] += m["vy"] * dt
                m["rect"].center = (int(m["x"]), int(m["y"]))
                
                # Colisão com o jogador
                if m["rect"].colliderect(player_rect):
                    # Pedra: controle forte, mas sem roubo automatico de carta.
                    tempo_stun_jogador_fim = tempo_atual + 2000
                    
                    if m.get("is_pedra") and not m.get("apenas_stun"):
                        # Roubar carta do deck do jogador
                        cartas_possuidas = [nome for nome, qtd in cartas_compradas.items() if qtd > 0]
                        if cartas_possuidas:
                            carta_sorteada = random.choice(cartas_possuidas)
                            cartas_compradas[carta_sorteada] -= 1
                            
                            # Encontra o inimigo correspondente para colocar na bolsa dele
                            for ini in inimigos_comum:
                                if ini.get("tipo") == TIPO_LARAPIO and id(ini) == m.get("larapio_id"):
                                    ini.setdefault("cartas_roubadas_larapio", []).append(carta_sorteada)
                                    # Força o Larápio a fugir
                                    ini["estado"] = "fugindo"
                                    ini["inicio_fuga"] = tempo_atual
                                    break
                            
                            # Recalcular atributos
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
                                "trembo": trembo, "cartas_compradas": cartas_compradas
                            }
                            Variaveis.recalcular_atributos_por_cartas(stats_jogador)
                            
                            # Re-aplicar variáveis locais
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
                            
                            salvar_atributos()
                            
                            efeitos_texto.append({
                                "texto": f"CARTA ROUBADA: {carta_sorteada}",
                                "x": pos_x_personagem - 20,
                                "y": pos_y_personagem - 30,
                                "tempo_inicio": tempo_atual,
                                "cor": (255, 70, 70),
                            })
                        else:
                            efeitos_texto.append({
                                "texto": "SEM CARTAS PARA ROUBAR!",
                                "x": pos_x_personagem - 20,
                                "y": pos_y_personagem - 30,
                                "tempo_inicio": tempo_atual,
                                "cor": (200, 200, 200),
                            })
                    else:
                        # Avisa o Larápio para ir correndo roubar (modo normal)
                        for ini in inimigos_comum:
                            if ini.get("tipo") == TIPO_LARAPIO and id(ini) == m.get("larapio_id"):
                                ini["estado"] = "cacando"
                                ini["speed_boost_tempo"] = tempo_atual + 3000
                                ini["ir_direto_roubar"] = True
                            
                    efeitos_texto.append({
                        "texto": "ATURDIDO! (2s)",
                        "x": pos_x_personagem,
                        "y": pos_y_personagem - 24,
                        "tempo_inicio": tempo_atual,
                        "cor": (255, 60, 60),
                    })
                    continue  # destrói o arremessável
                
                # Limite do mapa
                if m["x"] < 0 or m["x"] > largura_mapa or m["y"] < 0 or m["y"] > altura_mapa:
                    continue
                
                m["rotacao"] += m["vel_rotacao"]
                r = 6
                surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                
                if m.get("is_pedra"):
                    # Pedra cinza irregular
                    pygame.draw.circle(surf, (120, 120, 120), (r + 1, r + 1), r)
                    pygame.draw.circle(surf, (70, 70, 70), (r + 1, r + 1), r, 1)
                    pygame.draw.line(surf, (90, 90, 90), (r - 2, r + 1), (r + 3, r - 1), 1)
                else:
                    # Moeda de ouro
                    pygame.draw.circle(surf, (255, 215, 0), (r + 1, r + 1), r)
                    pygame.draw.circle(surf, (180, 130, 20), (r + 1, r + 1), r, 1)
                    
                    rad = math.radians(m["rotacao"])
                    bx = r + 1 + math.cos(rad) * (r - 1)
                    by = r + 1 + math.sin(rad) * (r - 1)
                    pygame.draw.line(surf, (255, 255, 255), (r + 1, r + 1), (bx, by), 2)
                
                tela.blit(surf, (int(m["x"] - r - 1), int(m["y"] - r - 1)))
                novas_arremessadas.append(m)
            moedas_arremessadas = novas_arremessadas
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
        custo_carta_atual = custo_base_carta + (sum(cartas_compradas.values()) * custo_por_carta)
        while running:
            tempo_atual = pygame.time.get_ticks()

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
                    "pontuacao_magia": pontuacao_magia,
                    "inimigos_eliminados": inimigos_eliminados,
                    "vida_inimigo_maxima": vida_inimigo_maxima,
                    "tempo_cronometro": Variaveis.obter_tempo_decorrido(),
                    "inimigos_comum": Variaveis.serializar_inimigos_rewind(inimigos_comum),
                    "vida_boss": vida_chefe if 'vida_chefe' in locals() or 'vida_chefe' in globals() else (vida_boss if 'vida_boss' in locals() or 'vida_boss' in globals() else None),
                    "r_press": bool(r_press)
                }
                Variaveis.registrar_snapshot(snapshot_data, tempo_atual)

            if carregar_atributos_na_fase:
                try:
                    if not Variaveis.ignorar_atributos_transicao:
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
                        Variaveis.definir_tempo_cronometro(snap.get("tempo_cronometro", Variaveis.obter_tempo_decorrido()))
                        if "inimigos_comum" in snap:
                            inimigos_comum = Variaveis.restaurar_inimigos_rewind(snap.get("inimigos_comum"), frames_inimigo[0])
                        if snap.get("refragmentacao_rewind"):
                            imune_tempo_restante = max(imune_tempo_restante, 4000)
                            piscando_vida = False
                            Variaveis.aplicar_rewind_respawn_visual(pos_x_personagem, pos_y_personagem, direcao_atual, pygame.time.get_ticks())
                        if "vida_boss" in snap and snap["vida_boss"] is not None:
                            if 'vida_chefe' in locals() or 'vida_chefe' in globals():
                                vida_chefe = snap["vida_boss"]
                            elif 'vida_boss' in locals() or 'vida_boss' in globals():
                                vida_boss = snap["vida_boss"]
                        if snap.get("r_press"):
                            r_press = True
                        Variaveis.snapshot_para_carregar = None
                    Variaveis.ignorar_atributos_transicao = False
                except Exception as e:
                    registrar_erro("Fase 1: erro ao carregar atributos; usando padrao", e)
                    Variaveis.ignorar_atributos_transicao = False
                carregar_atributos_na_fase = False
            fator_lentidao_boss = 1.0
            if tempo_atual < tempo_slow_onda_fim:
                fator_lentidao_boss = min(fator_lentidao_boss, 0.4)
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
            fase_coop = multiplayer_coop.atualizar(1, pos_x_personagem, pos_y_personagem, direcao_atual, vida, vida_maxima, vida <= 0)
            if multiplayer_coop.aplicar_transicao_recebida(fase_coop, game_manager):
                raise CleanExit()
            mundo_coop = multiplayer_coop.sincronizar_mundo(
                1,
                inimigos_comum,
                criar_inimigo,
                boss={
                    "vida": vida_boss,
                    "vida_maxima": vida_maxima_boss1,
                    "vivo": boss_vivo1,
                    "r_press": r_press,
                    "x": pos_x_chefe,
                    "y": pos_y_chefe,
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
                vida_boss = boss_coop.get("vida", vida_boss)
                vida_maxima_boss1 = boss_coop.get("vida_maxima", vida_maxima_boss1)
                boss_vivo1 = bool(boss_coop.get("vivo", boss_vivo1))
                r_press = bool(boss_coop.get("r_press", r_press))
                pos_x_chefe = boss_coop.get("x", pos_x_chefe)
                pos_y_chefe = boss_coop.get("y", pos_y_chefe)
                pontuacao = economia_coop.get("pontuacao", pontuacao)
                pontuacao_exib = economia_coop.get("pontuacao_exib", pontuacao_exib)
                pontuacao_magia = economia_coop.get("pontuacao_magia", pontuacao_magia)
                if "tempo_cronometro" in economia_coop:
                    Variaveis.definir_tempo_cronometro(economia_coop.get("tempo_cronometro", Variaveis.obter_tempo_decorrido()))
            multiplayer_coop.processar_eventos_visuais(1, efeitos_texto, ondas_choque, gerar_particulas_pontos)
            for event in pygame.event.get():
                Variaveis.atualizar_estado_mouse(event)
                Variaveis.processar_eventos_teleporte(event, cooldown_dash)
                if event.type == pygame.QUIT:
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.SAIR)
                        raise CleanExit()
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                    if event.key == pygame.K_ESCAPE:
                        if multiplayer_coop.modo_multiplayer():
                            multiplayer_coop.solicitar_acao("pause", 1)
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
                    elif event.key == pygame.K_p and Caminhos.modo_desenvolvedor_ativo():
                        if multiplayer_coop.modo_multiplayer():
                            aviso_teste = "ARAUTO INDISPONIVEL NO MULTIPLAYER"
                            cor_teste = (255, 120, 90)
                        elif miniboss_condutor:
                            aviso_teste = "ARAUTO JA ESTA NA ARENA"
                            cor_teste = (160, 220, 255)
                        elif miniboss_condutor_spawnado:
                            aviso_teste = "ARAUTO JA FOI ENFRENTADO NESTA FASE"
                            cor_teste = (180, 180, 195)
                        elif r_press or boss_vivo1:
                            aviso_teste = "FINALIZE O CHEFE ANTES DE CHAMAR O ARAUTO"
                            cor_teste = (255, 170, 80)
                        else:
                            criar_condutor_de_ecos()
                            aviso_teste = "TESTE DEV: ARAUTO INVOCADO"
                            cor_teste = (170, 225, 255)
                            print("[TESTE DEV / P] ARAUTO: CONDUTOR DE ECOS INVOCADO")

                        efeitos_texto.append({
                            "texto": aviso_teste,
                            "x": largura_mapa // 2 - 190,
                            "y": int(altura_mapa * 0.24),
                            "tempo_inicio": pygame.time.get_ticks(),
                            "cor": cor_teste,
                        })
                elif botao_mouse[0] and not condutora_manifestacao.disparo_bloqueado_registrador(manifestacao_ativa, tempo_atual) and not disparo_preparando and tempo_atual - tempo_ultimo_disparo >= ancorada_manifestacao.intervalo_disparo_ancorado(intervalo_disparo_racional(intervalo_disparo, aurea, racional_dilatacao_fim, tempo_atual), manifestacao_ativa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, tempo_atual) and tempo_atual >= tempo_stun_jogador_fim:  # Botão esquerdo do mouse
                    pos_mouse = obter_pos_mouse_jogo()
                    px_centro = pos_x_personagem + largura_personagem // 2
                    py_centro = pos_y_personagem + altura_personagem // 2
                    angulo_disparo_preparado = calcular_angulo_disparo((px_centro, py_centro), pos_mouse)
                    disparo_preparando = True
                    disparo_frame_atual = 0
                    tempo_ultimo_frame_preparo_disparo = tempo_atual
                    direcao_atual = 'disp'
                    frame_atual = 0
                elif ultimate_manifestacao.acionamento_por_evento(event, joystick) and ultimate_manifestacao.disponivel(tempo_atual) and tempo_atual >= tempo_stun_jogador_fim:
                    pos_mouse = obter_pos_mouse_jogo()
                    px_centro = pos_x_personagem + largura_personagem // 2
                    py_centro = pos_y_personagem + altura_personagem // 2
                    ondas.append(ultimate_manifestacao.criar_ultimate(
                        manifestacao_ativa, px_centro, py_centro, pos_mouse, tempo_atual,
                        dano_person_hit * fator_dano_aureas(tempo_atual), largura_mapa, altura_mapa, intervalo_disparo
                    ))
                    ultimate_manifestacao.registrar_uso(tempo_atual)
                    efeitos_texto.append({
                        "texto": ultimate_manifestacao.nome_ultimate(manifestacao_ativa).upper(),
                        "x": px_centro - 80,
                        "y": py_centro - 72,
                        "tempo_inicio": tempo_atual,
                        "cor": (255, 240, 120),
                    })
                elif Variaveis.verificar_evento_input(event, "Habilidade Onda") and tempo_atual - tempo_ultimo_uso_habilidade >= cooldown_habilidade * voraz_aurea.bonus_cooldown(estado_voraz, aurea) * parasitica_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * lacerante_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * condutora_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) and tempo_atual >= tempo_stun_jogador_fim:
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
                        alvos_circuito = inimigos_comum + ([miniboss_condutor] if miniboss_condutor else [])
                        vida_arauto_antes = miniboss_condutor["vida"] if miniboss_condutor else None
                        mortos_circuito, total_alvos, total_links = condutora_manifestacao.fechar_circuitos(
                            alvos_circuito, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto, jogador_rect_temp
                        )
                        if miniboss_condutor and vida_arauto_antes is not None:
                            dano_circuito_arauto = max(0.0, vida_arauto_antes - miniboss_condutor["vida"])
                            miniboss_condutor["vida"] = vida_arauto_antes
                            mortos_circuito = [m for m in mortos_circuito if m is not miniboss_condutor]
                            if dano_circuito_arauto > 0:
                                aplicar_dano_ao_condutor(dano_circuito_arauto, (255, 220, 90))
                        ondas.append(condutora_manifestacao.criar_fechamento(px_centro, py_centro, tempo_atual, total_alvos, total_links))
                        for morto_circuito in mortos_circuito:
                            if morto_circuito in inimigos_comum:
                                processar_morte_inimigo(morto_circuito)
                                inimigos_comum.remove(morto_circuito)
                                inimigos_eliminados += 1
                    elif parasitica_manifestacao.ativa(manifestacao_ativa):
                        alvos_eclosao = inimigos_comum + ([miniboss_condutor] if miniboss_condutor else [])
                        vida_arauto_antes = miniboss_condutor["vida"] if miniboss_condutor else None
                        mortos_eclosao, total_eclosao = parasitica_manifestacao.eclodir_todas(alvos_eclosao, tempo_atual, efeitos_texto)
                        if miniboss_condutor and vida_arauto_antes is not None:
                            dano_eclosao_arauto = max(0.0, vida_arauto_antes - miniboss_condutor["vida"])
                            miniboss_condutor["vida"] = vida_arauto_antes
                            mortos_eclosao = [m for m in mortos_eclosao if m is not miniboss_condutor]
                            if dano_eclosao_arauto > 0:
                                aplicar_dano_ao_condutor(dano_eclosao_arauto, (125, 255, 145))
                        ondas.append(parasitica_manifestacao.criar_eclosao(px_centro, py_centro, tempo_atual, total_eclosao))
                        for morto_eclosao in mortos_eclosao:
                            if morto_eclosao in inimigos_comum:
                                processar_morte_inimigo(morto_eclosao)
                                inimigos_comum.remove(morto_eclosao)
                                inimigos_eliminados += 1
                    elif retornante_manifestacao.ativa(manifestacao_ativa):
                        resultado_memoria = retornante_manifestacao.ativar_memoria_instavel(disparos, tempo_atual, pos_mouse)
                        memoria_x, memoria_y = resultado_memoria.get("centro") or (px_centro, py_centro)
                        ondas.append(retornante_manifestacao.criar_chamado(memoria_x, memoria_y, tempo_atual, int(resultado_memoria["ativado"])))
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
                    evolucoes_manifestacao.ao_usar_habilidade(
                        estado_evolucao_manifestacao, (px_centro, py_centro), tempo_atual
                    )

            # Verificar eventos de teclado
            # --- Tela de pausa (ESC) ---
            if multiplayer_coop.acao_confirmada("pause", 1):
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
                    registrar_erro("Fase 1: erro ao salvar atributos para pausa", e)
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
                multiplayer_coop.aguardar_barreira("pause_saida", 1, tela, fonte, "Aguardando o outro jogador voltar do pause...")
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

            tempo_passado += relogio.get_rawtime()
            relogio.tick()

             # Adicionar inimigos a cada 10 segundos
            tempo_atual = pygame.time.get_ticks()
            if mostrar_tutorial:
                pass  # Nenhum inimigo comum durante o tutorial
            else:
                tempo_decorrido_run = Variaveis.obter_tempo_decorrido()
                if not multiplayer_coop.modo_multiplayer():
                    tentar_spawn_condutor(tempo_decorrido_run)
                limite_inimigos_run = max_inimigos + bonus_limite_inimigos_sem_boss(
                    tempo_decorrido_run,
                    r_press or boss_vivo1,
                    inimigos_eliminados,
                    modo_dificil=Variaveis.obter_modo_cartas() == "drops",
                )
                pressao_spawn = calcular_pressao_spawn_pos_boss(
                    pressao_pos_boss_spawn,
                    tempo_atual,
                    r_press and not boss_vivo1,
                    len(inimigos_comum),
                    inimigos_eliminados,
                    limite_inimigos_run,
                )
                condutor_ativo = bool(miniboss_condutor)
                if tempo_atual - tempo_ultimo_inimigo >= pressao_spawn["intervalo_ms"] and pressao_spawn["lote"] > 0 and not boss_vivo1 and not condutor_ativo:
                    for _ in range(pressao_spawn["lote"]):
                        gerar_inimigo(pressao_spawn["limite"])
                    tempo_ultimo_inimigo = tempo_atual  # Atualizar o tempo do último inimigo adicionado
                # O Larapio atual roda fora de inimigos_comum em Variaveis.
                # Mantemos o spawner antigo desligado para nao quebrar o limite de inimigos.
                if not condutor_ativo:
                    tentar_spawn_larapio(tempo_decorrido_run, limite_inimigos_run)
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
                    Disparo_Geo.play()
                    largura_tiro, altura_tiro = voraz_aurea.dimensoes_disparo(estado_voraz, aurea, largura_disparo, altura_disparo)
                    disparo_novo = ancorada_manifestacao.criar_auto_attack(manifestacao_ativa, vfx_disparo_player,
                        px_centro, py_centro, largura_tiro, altura_tiro,
                        angulo_disparo_preparado, velocidade_disparo, tempo_atual, impulsiva_ativa
                    )
                    disparo_novo = aureas_avancadas.marcar_disparo(
                        estado_aureas_avancadas, aurea, disparo_novo, tempo_atual, efeitos_texto
                    )
                    disparo_novo = voraz_aurea.marcar_disparo_voraz(estado_voraz, aurea, disparo_novo)
                    disparos.extend(evolucoes_manifestacao.aplicar_ao_disparo(
                        disparo_novo, estado_evolucao_manifestacao
                    ))
                    insana_aurea.registrar_tiro_insana(
                        estado_insana, aurea, tempo_atual,
                        pos_x_personagem, pos_y_personagem, px_centro, py_centro,
                        angulo_disparo_preparado, largura_tiro, altura_tiro, velocidade_disparo,
                        manifestacao_ativa
                    )
                    tempo_ultimo_disparo = tempo_atual
                    disparo_preparando = False
                    disparo_frame_atual = 0


            shake_x, shake_y = 0, 0
            tela.fill((255, 255, 255))
            tela.blit(mapa, (0, 0))




            insana_aurea.atualizar_insana(estado_insana, aurea, tempo_atual, disparos, vfx_disparo_player)
            if insana_aurea.consumir_penalidade_dash_insana(estado_insana):
                cooldown_dash = True
                tempo_ultimo_dash = max(tempo_ultimo_dash, tempo_atual + insana_aurea.INSANA_DEBUFF_DASH_MS)

            boss_rect_voraz = pygame.Rect(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura) if (boss_vivo1 and not boss_morte_processada) else None
            aureas_avancadas.atualizar(
                estado_aureas_avancadas, aurea, tempo_atual,
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem,
                inimigos_comum, efeitos_texto, boss_vivo1 and not boss_morte_processada
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
                    processar_morte_inimigo(morto_voraz)
                    inimigos_comum.remove(morto_voraz)
                    inimigos_eliminados += 1
            if boss_rect_voraz is not None:
                vida_boss, vida, _ = voraz_aurea.aplicar_mordida_boss(
                    estado_voraz, aurea, tempo_atual,
                    pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem,
                    boss_rect_voraz, vida_boss, vida, vida_maxima, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto
                )

            # Desenhar os disparos normais
            novos_disparos = []
            for disparo in disparos:
                evolucoes_manifestacao.atualizar_disparo(disparo, inimigos_comum)
                vfx_disparo_player.atualizar_disparo(disparo, velocidade_disparo, dt)
                centro_retorno_x = pos_x_personagem + largura_personagem // 2
                centro_retorno_y = pos_y_personagem + altura_personagem // 2

                # Verificar se o disparo está dentro do mapa
                if disparo.get("tipo_manifestacao") == "lacerante_corte":
                    if not disparo.get("expirado"):
                        novos_disparos.append(disparo)
                elif disparo.get("tipo_manifestacao") == "retornante_pulso":
                    if retornante_manifestacao.atualizar_disparo(disparo, centro_retorno_x, centro_retorno_y, dt, tempo_atual, inimigos_comum, largura_mapa, altura_mapa):
                        novos_disparos.append(disparo)
                elif disparo.get("tipo_manifestacao") == "prismatica_feixe":
                    if prismatica_manifestacao.atualizar_ricochete(disparo, largura_mapa, altura_mapa, tempo_atual):
                        novos_disparos.append(disparo)
                elif 0 <= disparo["rect"].x < largura_mapa and 0 <= disparo["rect"].y < altura_mapa:
                    novos_disparos.append(disparo)

            disparos = novos_disparos

            # Renderizar os disparos
            vfx_disparo_player.preparar_frame(len(disparos), config_graficos)
            for disparo in disparos:
                vfx_disparo_player.desenhar_disparo(tela, disparo, tempo_atual, config_graficos)
            vfx_disparo_player.atualizar_e_desenhar_particulas(tela, dt, config_graficos)



            alvo_principal_eh_boss = boss_vivo1 and not boss_morte_processada
            alvo_principal_eh_arauto = bool(miniboss_condutor) and not alvo_principal_eh_boss
            boss_info = {
                "vivo": alvo_principal_eh_boss or alvo_principal_eh_arauto,
                "rect": (
                    pygame.Rect(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura)
                    if alvo_principal_eh_boss
                    else (miniboss_condutor["rect"] if alvo_principal_eh_arauto else None)
                ),
                "alvo": "arauto" if alvo_principal_eh_arauto else "boss",
                "atingido_por_onda": boss_atingido_por_onda,
                "hit_flag": False
            }
            alvos_onda = (
                inimigos_comum + [miniboss_condutor]
                if alvo_principal_eh_arauto and gravitante_manifestacao.ativa(manifestacao_ativa)
                else inimigos_comum
            )
            vida_arauto_antes_onda = miniboss_condutor["vida"] if alvo_principal_eh_arauto else None
            inimigos_mortos_neste_frame = processar_habilidade_onda(
                ondas, correntes_eletricas, alvos_onda, boss_info, tela, dt, tempo_atual, largura_mapa, altura_mapa, velocidade_onda, disparos, config_graficos,
                player_center=(pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2)
            )
            if miniboss_condutor and vida_arauto_antes_onda is not None:
                dano_direto_onda_arauto = max(0.0, vida_arauto_antes_onda - miniboss_condutor["vida"])
                miniboss_condutor["vida"] = vida_arauto_antes_onda
                inimigos_mortos_neste_frame = [m for m in inimigos_mortos_neste_frame if m is not miniboss_condutor]
                if dano_direto_onda_arauto > 0:
                    aplicar_dano_ao_condutor(dano_direto_onda_arauto, (155, 215, 255))
            if boss_info.get("hit_flag") and alvo_principal_eh_arauto:
                dano_onda = boss_info.get("dano_manifestacao", dano_person_hit * fator_dano_aureas(tempo_atual) * 5.8)
                aplicar_dano_ao_condutor(dano_onda, (180, 255, 255))
                boss_info["hit_flag"] = False
            elif boss_info.get("hit_flag") and not boss_morte_processada:
                dano_onda = boss_info.get("dano_manifestacao", dano_person_hit * fator_dano_aureas(tempo_atual) * 5.8)
                dano_onda_real = dano_boss_mitigado(dano_onda, 1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                vida_boss -= dano_onda_real
                registrar_dano_boss(efeitos_texto, dano_onda_real, pos_x_chefe + chefe_largura // 2, pos_y_chefe - 22, tempo_atual, (180, 255, 255))
                boss_atingido_por_onda = boss_info["atingido_por_onda"]
                boss_info["hit_flag"] = False

            # Atualizar e desenhar correntes elétricas
            inimigos_mortos_correntes = atualizar_e_desenhar_correntes(tela, correntes_eletricas, inimigos_comum, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), config_graficos)
            alvos_passivas = inimigos_comum + ([miniboss_condutor] if miniboss_condutor else [])
            vida_arauto_antes_passivas = miniboss_condutor["vida"] if miniboss_condutor else None
            inimigos_mortos_laceracao = lacerante_manifestacao.atualizar_laceracoes(alvos_passivas, tempo_atual, efeitos_texto)
            jogador_rect_parasitica = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
            inimigos_mortos_parasitica = parasitica_manifestacao.atualizar_sementes(
                alvos_passivas, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto, jogador_rect_parasitica
            )
            parasitica_manifestacao.desenhar_sementes(tela, alvos_passivas, tempo_atual, config_graficos)
            inimigos_mortos_condutora = condutora_manifestacao.atualizar_circuitos(
                alvos_passivas, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto
            )
            condutora_manifestacao.desenhar_circuitos(tela, alvos_passivas, tempo_atual, config_graficos, manifestacao_ativa, jogador_rect_parasitica)
            inimigos_mortos_gravitante = gravitante_manifestacao.atualizar_orbes(
                alvos_passivas, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto
            )
            gravitante_manifestacao.desenhar_orbes(tela, alvos_passivas, tempo_atual, config_graficos)
            inimigos_mortos_ancorada = ancorada_manifestacao.atualizar_territorio(
                alvos_passivas, tempo_atual, dano_person_hit * fator_dano_aureas(tempo_atual), jogador_rect_parasitica, efeitos_texto
            )
            ancorada_manifestacao.aplicar_lentidao_projeteis(disparos_inimigos, tempo_atual)
            ancorada_manifestacao.desenhar_territorios(tela, tempo_atual, config_graficos, jogador_rect_parasitica)
            inimigos_mortos_teleporte = teleporte_manifestacao.atualizar_efeitos_teleporte_manifestacao(
                inimigos_comum, boss_info, disparos, tempo_atual,
                dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto, largura_mapa, altura_mapa,
                jogador_rect_parasitica
            )
            if boss_info.get("hit_flag") and boss_info.get("alvo") == "arauto" and miniboss_condutor:
                aplicar_dano_ao_condutor(
                    boss_info.get("dano_manifestacao", dano_person_hit * 0.10),
                    (205, 155, 255),
                )
                boss_info["hit_flag"] = False
            elif boss_info.get("hit_flag") and boss_info.get("alvo") == "boss" and not boss_morte_processada:
                dano_teleporte_tardio = dano_boss_mitigado(
                    boss_info.get("dano_manifestacao", dano_person_hit * 0.10),
                    1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0),
                )
                vida_boss -= dano_teleporte_tardio
                boss_info["hit_flag"] = False
            teleporte_manifestacao.desenhar_efeitos_teleporte_manifestacao(tela, tempo_atual, config_graficos)
            
            inimigos_mortos = inimigos_mortos_neste_frame + inimigos_mortos_correntes + inimigos_mortos_laceracao + inimigos_mortos_parasitica + inimigos_mortos_condutora + inimigos_mortos_gravitante + inimigos_mortos_ancorada + inimigos_mortos_teleporte
            for morto in inimigos_mortos:
                if morto in inimigos_comum:
                    processar_morte_inimigo(morto)
                    inimigos_comum.remove(morto)
                    inimigos_eliminados += 1
                    
                    # --- ESCALONAMENTO POR NIVEL DE AMEAÇA ---
                    mult = 1.0 + (nivel_ameaca * 0.1)
                    vida_inimigo_maxima += ganho_vida_inimigo_comum(0.5 * mult)
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
                        vida_boss += ganho_progressao_boss(12 * mult)
                        vida_maxima_boss1 = vida_boss
                        vida_boss2 += ganho_progressao_boss(15 * mult)
                        vida_maxima_boss2 = vida_boss2
                        vida_boss3 += ganho_progressao_boss(18 * mult)
                        vida_maxima_boss3 = vida_boss3
                        vida_boss4 += ganho_progressao_boss(22 * mult)
                        vida_maxima_boss4 = vida_boss4

            tempo_atual = pygame.time.get_ticks()
            if movendo and not multiplayer_coop.eh_cliente():
                if tempo_atual - tempo_anterior >= tempo_movimento:
                    # Atualize o tempo anterior para o tempo atual
                    tempo_anterior = tempo_atual
                    movendo = False
                    tempo_movimento = random.randint(3000, 7000)
                # Atualizar movimento dos inimigos com previsão
                tempo_previsao = 5  # Tempo em quadros para prever o movimento

                pos_x_personagem, pos_y_personagem = atualizar_movimento_inimigos(
                    inimigos_comum, pos_x_personagem, pos_y_personagem, ultima_tecla_movimento, velocidade_personagem, tempo_previsao, movendo, largura_personagem, altura_personagem, fator_mundo_racional(aurea, racional_dilatacao_fim, tempo_atual)
                )
                pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem))
                pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem))
            elif not multiplayer_coop.eh_cliente():
                if tempo_atual - tempo_anterior >= tempo_parado:
                    # Atualize o tempo anterior para o tempo atual
                    tempo_anterior = tempo_atual
                    movendo = True
                    tempo_parado = random.randint(10, 3000)

            # --- ATUALIZAR COMPORTAMENTOS DAS VARIANTES ---
            if not multiplayer_coop.eh_cliente():
                for inimigo in inimigos_comum[:]:
                    if (
                        inimigo.get("ruptura_deslocamento")
                        or tempo_atual < int(inimigo.get("ruptura_raiz_fim", 0))
                    ):
                        continue
                    tipo = inimigo.get("tipo", 1)
                    if tipo == 3: # Espreitador
                        atualizar_espreitador(inimigo)
                    elif tipo == 5: # Projetador
                        atualizar_projetador(inimigo)
                    elif tipo == TIPO_CURATER:
                        atualizar_curater(inimigo, tempo_atual)
                    elif tipo == TIPO_LARAPIO:
                        atualizar_larapio(inimigo)
                atualizar_condutor()
                    
            # --- CHEQUE DE FUSÃO DO AGLOMERADOR (A cada 1 segundo) ---
            tempo_decorrido = Variaveis.obter_tempo_decorrido()
            if tempo_atual - tempo_ultimo_cheque_fusao >= 1000 and not r_press and not miniboss_condutor and not multiplayer_coop.eh_cliente():
                delta_fusao = tempo_atual - tempo_ultimo_cheque_fusao if tempo_ultimo_cheque_fusao else 1000
                tempo_ultimo_cheque_fusao = tempo_atual
                standard_enemies = [ini for ini in inimigos_comum if ini.get("tipo", 1) == 1]
                clusters = []
                usados = set()
                em_cluster = set()
                
                for i, e1 in enumerate(standard_enemies):
                    if id(e1) in usados:
                        continue
                    cluster = [e1]
                    for j, e2 in enumerate(standard_enemies):
                        if i != j and id(e2) not in usados:
                            dist = math.hypot(e1["rect"].centerx - e2["rect"].centerx, e1["rect"].centery - e2["rect"].centery)
                            if dist <= FUSAO_AGLOMERACAO_RAIO:
                                cluster.append(e2)
                    if len(cluster) >= FUSAO_AGLOMERACAO_MINIMO:
                        clusters.append(cluster)
                        for c_e in cluster:
                            usados.add(id(c_e))
                            em_cluster.add(id(c_e))

                for inimigo in standard_enemies:
                    if id(inimigo) in em_cluster:
                        inimigo["tempo_aglomerado_ms"] = inimigo.get("tempo_aglomerado_ms", 0) + delta_fusao
                    else:
                        inimigo["tempo_aglomerado_ms"] = 0
                            
                for cluster in clusters:
                    if min(e.get("tempo_aglomerado_ms", 0) for e in cluster) < FUSAO_AGLOMERACAO_MS:
                        continue
                    cx = sum(e["rect"].centerx for e in cluster) // len(cluster)
                    cy = sum(e["rect"].centery for e in cluster) // len(cluster)
                    aglomerador = criar_inimigo(cx - largura_inimigo // 2, cy - altura_inimigo // 2, tipo=2)
                    vida_fundida = sum(e.get("vida_maxima", vida_inimigo_maxima) for e in cluster) * 0.9
                    aglomerador["vida_maxima"] = max(aglomerador["vida_maxima"], vida_fundida)
                    aglomerador["vida"] = aglomerador["vida_maxima"]
                    aglomerador["velocidade"] = max(
                        aglomerador["velocidade"],
                        Velocidade_Inimigos_1 * (1.35 + max(0, len(cluster) - FUSAO_AGLOMERACAO_MINIMO) * 0.15),
                    )
                    for c_e in cluster:
                        if c_e in inimigos_comum:
                            inimigos_comum.remove(c_e)
                    efeitos_texto.append({
                        "texto": "FUSAO FORCADA!",
                        "x": cx,
                        "y": cy - 40,
                        "tempo_inicio": tempo_atual,
                        "cor": (255, 200, 0)
                    })
                    inimigos_comum.append(aglomerador)
                    
            # --- CONTROLE DOS AVISOS DOS EVENTOS ---
            if not mostrar_tutorial and not r_press:
                if tempo_decorrido >= ANOMALIA_CURATER_TEMPO and not alerta_t5_mostrado:
                    alerta_t5_mostrado = True
                    aviso_evento_texto = "ANOMALIA DE CURA DETECTADA: CURATER!"
                    aviso_evento_cor = (120, 255, 140)
                    aviso_evento_inicio = tempo_atual
                elif tempo_decorrido >= ANOMALIA_AGLOMERADOR_TEMPO and not alerta_t4_mostrado:
                    alerta_t4_mostrado = True
                    aviso_evento_texto = "ANOMALIA DE FUSAO: AGLOMERADORES!"
                    aviso_evento_cor = (255, 210, 80)
                    aviso_evento_inicio = tempo_atual
                elif tempo_decorrido >= ANOMALIA_CRISTALIZADOR_TEMPO and not alerta_t3_mostrado:
                    alerta_t3_mostrado = True
                    aviso_evento_texto = "ANOMALIA DETECTADA: INIMIGOS CRISTALIZADOS!"
                    aviso_evento_cor = (255, 0, 128)
                    aviso_evento_inicio = tempo_atual
                elif tempo_decorrido >= ANOMALIA_PROJETADOR_TEMPO and not alerta_t2_mostrado:
                    alerta_t2_mostrado = True
                    aviso_evento_texto = "ANOMALIA DETECTADA: PROJETADORES!"
                    aviso_evento_cor = (255, 0, 128)
                    aviso_evento_inicio = tempo_atual
                elif tempo_decorrido >= ANOMALIA_ESPREITADOR_TEMPO and not alerta_t1_mostrado:
                    alerta_t1_mostrado = True
                    aviso_evento_texto = "ALERTA: A AREIA COSMICA SE ADAPTOU!"
                    aviso_evento_cor = (0, 255, 255)
                    aviso_evento_inicio = tempo_atual

            # --- ATUALIZAR E DESENHAR DISPAROS INIMIGOS (PROJETADORES) ---
            for disp in list(disparos_inimigos):
                disp["rect"].x += int(disp["vx"])
                disp["rect"].y += int(disp["vy"])
                
                # Desenhar projétil de areia: gray/dark particle swirl
                cor_proj = disp.get("cor", (140, 140, 150))
                pygame.draw.circle(tela, cor_proj, disp["rect"].center, 6)
                pygame.draw.circle(tela, (80, 80, 120), disp["rect"].center, 3)
                
                # Limpar projéteis fora do mapa
                if (disp["rect"].x < 0 or disp["rect"].x > largura_mapa or 
                    disp["rect"].y < 0 or disp["rect"].y > altura_mapa):
                    if disp in disparos_inimigos:
                        disparos_inimigos.remove(disp)
                    continue
                    
                # Colisão com o jogador
                player_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem * 0.5, altura_personagem * 0.8)
                if disp["rect"].colliderect(player_rect):
                    if imune_tempo_restante <= 0:
                        dano_base_proj = disp.get("dano", int((vida_maxima * 0.05) + dano_inimigo_longe))
                        Dano_pos_resistencia_person = int(dano_base_proj - Resistencia)
                        Dano_pos_resistencia_person = dano_inimigo_inicio_ajustado(Dano_pos_resistencia_person)
                        if Dano_pos_resistencia_person > 0:
                            vida -= Dano_pos_resistencia_person
                            tempo_ultimo_hit_inimigo = tempo_atual
                            imune_tempo_restante = 500
                            try:
                                pass
                            except:
                                pass
                    if disp in disparos_inimigos:
                        disparos_inimigos.remove(disp)

            for pulso in list(pulsos_cura_curater):
                idade = tempo_atual - pulso["inicio"]
                if idade > 520:
                    pulsos_cura_curater.remove(pulso)
                    continue
                progresso = idade / 520.0
                cor_raio = (92, 255, 135)
                pygame.draw.line(tela, cor_raio, pulso["origem"], pulso["alvo"], max(1, int(4 - progresso * 3)))
                ax, ay = pulso["alvo"]
                raio = int(8 + progresso * 18)
                pygame.draw.circle(tela, (160, 255, 176), (ax, ay), raio, 2)

            lacerante_manifestacao.atualizar_e_desenhar_sangue_lacerante(tela, inimigos_comum, config_graficos)
            evolucoes_manifestacao.atualizar_e_desenhar(
                tela, estado_evolucao_manifestacao, inimigos_comum, tempo_atual
            )
            if miniboss_condutor and vida_arauto_antes_passivas is not None:
                dano_passivas_arauto = max(0.0, vida_arauto_antes_passivas - miniboss_condutor["vida"])
                miniboss_condutor["vida"] = vida_arauto_antes_passivas
                listas_mortos_passivas = (
                    inimigos_mortos_laceracao, inimigos_mortos_parasitica,
                    inimigos_mortos_condutora, inimigos_mortos_gravitante,
                    inimigos_mortos_ancorada, inimigos_mortos_teleporte,
                )
                for lista_mortos in listas_mortos_passivas:
                    if miniboss_condutor in lista_mortos:
                        lista_mortos.remove(miniboss_condutor)
                if dano_passivas_arauto > 0:
                    aplicar_dano_ao_condutor(dano_passivas_arauto, (210, 150, 255))
            jogador_fragmento_rect = pygame.Rect(
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem
            )
            for fragmento in list(fragmentos_ruptura):
                evolucoes_manifestacao.desenhar_fragmento(tela, fragmento, tempo_atual)
                if evolucoes_manifestacao.fragmento_colidiu(fragmento, jogador_fragmento_rect):
                    fragmentos_ruptura.remove(fragmento)
                    pausar_cronometro()
                    pygame.event.clear()
                    escolha = evolucoes_manifestacao.abrir_menu(
                        tela, manifestacao_ativa, estado_evolucao_manifestacao, relogio
                    )
                    retomar_cronometro()
                    pygame.event.clear()
                    # O impulso comeca somente depois que o menu fecha; assim a
                    # trajetoria nao acontece escondida atras da tela de escolha.
                    afetados = evolucoes_manifestacao.repelir_inimigos(
                        inimigos_comum, (fragmento["x"], fragmento["y"])
                    )
                    ondas_choque.append({
                        "cx": fragmento["x"], "cy": fragmento["y"],
                        "raio_atual": 16.0, "raio_max": 360.0,
                        "velocidade": 18.0, "cor": (195, 105, 255),
                    })
                    if escolha:
                        efeitos_texto.append({
                            "texto": escolha["nome"].upper(),
                            "x": pos_x_personagem - 20,
                            "y": pos_y_personagem - 54,
                            "tempo_inicio": pygame.time.get_ticks(),
                            "cor": (225, 175, 255),
                        })
                    if afetados:
                        efeitos_texto.append({
                            "texto": f"RUPTURA REPELIU {afetados}",
                            "x": pos_x_personagem - 30,
                            "y": pos_y_personagem - 30,
                            "tempo_inicio": pygame.time.get_ticks(),
                            "cor": (185, 225, 255),
                        })
            atualizar_e_desenhar_vfx_condutor(tela)
            desenhar_condutor(tela)

            # Desenhe os inimigos na tela
            for inimigo in inimigos_comum:
                tipo = inimigo.get("tipo", 1)
                l_vis = inimigo.get("largura_visual", largura_inimigo)
                a_vis = inimigo.get("altura_visual", altura_inimigo)
                off_x = inimigo.get("offset_x", (largura_inimigo - int(largura_inimigo * 0.8)) // 2)
                off_y = inimigo.get("offset_y", (altura_inimigo - int(altura_inimigo * 0.5)) // 2)
                
                desenhar_x = inimigo["rect"].x - off_x
                desenhar_y = inimigo["rect"].y - off_y
                
                frames_tipo = frames_inimigo_especies.get(tipo, frames_inimigo)
                f_idx = inimigo.get("frame_atual", frame_atual)
                current_frame = frames_tipo[f_idx % len(frames_tipo)]
                if l_vis != largura_inimigo or a_vis != altura_inimigo:
                    img_render = pygame.transform.scale(current_frame, (l_vis, a_vis))
                else:
                    img_render = current_frame
                img_render = orientar_sprite_inimigo(img_render, inimigo)
                
                # Efeito Stealth do Espreitador
                alpha = 255
                if tipo == 3: # Espreitador
                    alpha = int(inimigo.get("alpha_oscilation", 255))
                    alpha_surf = pygame.Surface(img_render.get_size(), pygame.SRCALPHA)
                    alpha_surf.blit(img_render, (0, 0))
                    alpha_surf.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
                    img_render = alpha_surf

                
                pulo_y = 0
                if tipo == TIPO_LARAPIO or tipo == "larapio":
                    has_stolen = (
                        inimigo.get("dinheiro_roubado", 0) > 0
                        or len(inimigo.get("cartas_roubadas_larapio", [])) > 0
                        or inimigo.get("roubou_pontos", False)
                        or inimigo.get("possui_chave_loja", False)
                    )
                    if has_stolen:
                        pulo_y = int(abs(math.sin(pygame.time.get_ticks() * 0.012)) * 18)
                        desenhar_y -= pulo_y

                desenhar_sombra(tela, desenhar_x, desenhar_y + pulo_y, l_vis, a_vis)
                if tipo == TIPO_LARAPIO or tipo == "larapio":
                    portal_charge = inimigo.get("portal_charge", 0.0)
                    if portal_charge > 0.0:
                        max_largura_portal = int(l_vis * 1.35)
                        max_altura_portal = int(a_vis * 0.45)
                        largura_portal = int((portal_charge / 100.0) * max_largura_portal)
                        altura_portal = int((portal_charge / 100.0) * max_altura_portal)
                        if largura_portal > 4 and altura_portal > 2:
                            centro_x = desenhar_x + l_vis // 2
                            centro_y = desenhar_y + pulo_y + a_vis - 2
                            portal_surf = pygame.Surface((largura_portal, altura_portal), pygame.SRCALPHA)
                            pygame.draw.ellipse(portal_surf, (148, 0, 211, 200), (0, 0, largura_portal, altura_portal))
                            pygame.draw.ellipse(portal_surf, (224, 130, 255, 240), (2, 1, max(1, largura_portal - 4), max(1, altura_portal - 2)))
                            random.seed(inimigo["rect"].x + int(portal_charge))
                            for _ in range(5):
                                p_ang = random.uniform(0, 2 * math.pi)
                                rx = int(largura_portal / 2 + math.cos(p_ang) * (largura_portal / 2 - 2))
                                ry = int(altura_portal / 2 + math.sin(p_ang) * (altura_portal / 2 - 1))
                                pygame.draw.circle(portal_surf, (0, 0, 0, 230), (rx, ry), random.randint(1, 3))
                            tela.blit(portal_surf, (centro_x - largura_portal // 2, centro_y - altura_portal // 2))

                if tipo == TIPO_CURATER and inimigo.get("parado", False):
                    desenhar_plantinhas_curater(tela, inimigo, desenhar_x, desenhar_y, l_vis, a_vis)
                tela.blit(img_render, (desenhar_x, desenhar_y))
                
                # Efeitos visuais por tipo
                if tipo == 2: # Aglomerador particles
                    tempo_part = pygame.time.get_ticks()
                    for p_i in range(8):
                        ang_p = (tempo_part * 0.005 + p_i * (math.pi / 4))
                        rx = desenhar_x + l_vis // 2 + int(math.cos(ang_p) * (l_vis // 1.6))
                        ry = desenhar_y + a_vis // 2 + int(math.sin(ang_p) * (a_vis // 2.5))
                        pygame.draw.circle(tela, (120, 120, 130), (rx, ry), random.randint(2, 4))
                elif tipo == 4: # Cristalizador shield
                    tempo_hex = pygame.time.get_ticks()
                    pulsar_hex = int(10 * math.sin(tempo_hex * 0.004))
                    cx, cy = inimigo["rect"].centerx, inimigo["rect"].centery
                    pts_hex = []
                    for h_i in range(6):
                        ang_h = h_i * (math.pi / 3) + tempo_hex * 0.0005
                        h_rad = int(35 + pulsar_hex)
                        pts_hex.append((cx + int(math.cos(ang_h) * h_rad), cy + int(math.sin(ang_h) * h_rad)))
                    pygame.draw.polygon(tela, (0, 191, 255), pts_hex, width=2)
                elif tipo == 5: # Projetador focus marker
                    tempo_proj = pygame.time.get_ticks()
                    cx, cy = inimigo["rect"].centerx, inimigo["rect"].centery
                    pulso_proj = int(3 * math.sin(tempo_proj * 0.009))
                    raio_proj = 24 + pulso_proj
                    pygame.draw.circle(tela, (255, 196, 70), (cx, cy), raio_proj, 2)
                    pygame.draw.circle(tela, (110, 72, 38), (cx, cy), max(7, raio_proj - 12), 1)
                    for m_i in range(4):
                        ang_m = tempo_proj * 0.003 + m_i * (math.pi / 2)
                        x1 = cx + int(math.cos(ang_m) * (raio_proj + 3))
                        y1 = cy + int(math.sin(ang_m) * (raio_proj + 3))
                        x2 = cx + int(math.cos(ang_m) * (raio_proj + 12))
                        y2 = cy + int(math.sin(ang_m) * (raio_proj + 12))
                        pygame.draw.line(tela, (255, 230, 128), (x1, y1), (x2, y2), 2)
                    pygame.draw.circle(tela, (255, 245, 170), (cx, cy - 12), 4, 0)
                desenhar_barra_de_vida(tela, desenhar_x, desenhar_y - 10, l_vis, 5, inimigo["vida"], inimigo["vida_maxima"], inimigo.get("eletrocutado", False), Executa_inimigo if Ultimo_Estalo else None)

            personagem_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem*0.5, altura_personagem*0.8)
            inimigos_rects = [inimigo["rect"] for inimigo in inimigos_comum if not inimigo.get("invisivel", False) and inimigo.get("tipo") != TIPO_LARAPIO]


            if imune_tempo_restante > 0:
                imune_tempo_restante -= relogio.get_time()  
            else:
                imune_tempo_restante = 0 


            if verificar_colisao_personagem_inimigo(personagem_rect, inimigos_rects) and imune_tempo_restante <= 0:

                if tempo_atual - tempo_ultimo_hit_inimigo >= intervalo_hit_inimigo:
                    Dano_pos_resistencia_person = int(((vida_maxima * 0.06)+dano_inimigo_perto) - Resistencia)
                    Dano_pos_resistencia_person = dano_inimigo_inicio_ajustado(Dano_pos_resistencia_person)
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
                    Dano_person.play()
                    piscando_vida = True

            if aurea == "Devota" and not escudo_devota_ativo and tempo_atual - tempo_ultimo_escudo >= intervalo_escudo:
                escudo_devota_ativo = True
                restaurar_escudo_devota(estado_devota)
                tempo_ultimo_escudo = tempo_atual
                # adicionar um efeito visual de "escudo ativado"



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
                    mostrar_tutorial=False
                    try:
                        with open("saves/tutorial_config.json", "w") as f:
                            json.dump({"mostrar_tutorial": False}, f)
                    except:
                        pass
                    pausar_cronometro()
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
                            "dano": int(vida_maxima * 0.08),
                            "atingiu_player": False
                        }
                        boss_transicao_ondas.append(nova_onda)
                else:
                    escudo_devota_pre_boss = escudo_devota_ativo
                    vida_pre_boss_devota = vida
                    alvos_boss1 = [(pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2)]
                    rect_jogador_remoto = multiplayer_coop.jogador_remoto_rect(1, largura_personagem, altura_personagem)
                    if rect_jogador_remoto is not None:
                        alvos_boss1.append(rect_jogador_remoto.center)
                    pos_x_personagem, pos_y_personagem, vida, escudo_devota_ativo, slow_f, pos_chefe_nova, stun_req, kb_x_boss, kb_y_boss = gerenciador_ataques_boss1.update(
                        dt, [pos_x_personagem, pos_y_personagem], largura_personagem, altura_personagem,
                        vida, vida_maxima, escudo_devota_ativo, Dano_Boss_Habilit,
                        [pos_x_chefe, pos_y_chefe], chefe_largura, chefe_altura, vida_boss, vida_maxima_boss1,
                        largura_mapa, altura_mapa, tempo_atual, alvos_jogadores=alvos_boss1
                    )
                    if aurea == "Devota" and escudo_devota_pre_boss and not escudo_devota_ativo and vida == vida_pre_boss_devota:
                        escudo_devota_ativo = True
                        absorver_dano_devota_atual()
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
                    
                    desenhar_onda_transicao_premium(tela, wave, tempo_atual)
                    
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
                            if absorver_dano_devota_atual():
                                pass
                            elif imune_tempo_restante <= 0 and Resistencia < dano_onda:
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
            if not ultimate_manifestacao.jogador_oculto(tempo_atual):
                # Desenhar sombra do personagem
                desenhar_sombra(tela, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)

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

            insana_aurea.desenhar_insana(
                tela, estado_insana, aurea, tempo_atual,
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, config_graficos
            )
            aureas_avancadas.desenhar(
                tela, estado_aureas_avancadas, aurea, tempo_atual,
                pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem,
                inimigos_comum, config_graficos
            )
            multiplayer_coop.desenhar_jogador_remoto(tela, 1, frame_atual, frames_animacao, frames_animacao2)

            # Desenhar zona de teleporte (se estiver mirando no modo mouse)
            Variaveis.desenhar_zona_teleporte(tela, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, distancia_dash)

            for moeda in moedas_soltadas[:]:
                if personagem_rect.colliderect(moeda["rect"]):
                    valor_moeda = int(moeda.get("valor", 1))
                    if moeda.get("tipo") == "pontos_larapio":
                        pontuacao += valor_moeda
                        pontuacao_exib += valor_moeda
                        pontuacao_magia = min(maxima_pontuacao_magia, pontuacao_magia + valor_moeda)
                        efeitos_texto.append({
                            "texto": f"+{valor_moeda} PONTOS",
                            "x": moeda["rect"].x,
                            "y": moeda["rect"].y - 18,
                            "tempo_inicio": tempo_atual,
                            "cor": (255, 230, 90),
                        })
                    else:
                        moedas_coletadas += valor_moeda
                        moedas_totais += valor_moeda   # 🪙 acumula no total salvo
                        salvar_atributos()   # 💾 salva imediatamente
                    moedas_soltadas.remove(moeda)

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
                            if inimigo_mais_proximo.get("tipo") == TIPO_LARAPIO:
                                registrar_hit_larapio(inimigo_mais_proximo)
                            tempo_anterior_petro = tempo_atual_petro

                            if inimigo_mais_proximo["vida"] <= 0:
                                # Evolução harmônica por abate da Petro
                                vida_inimigo_maxima += ganho_vida_inimigo_comum(0.5)
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
                                    processar_morte_inimigo(inimigo_mais_proximo)
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


                if xp_petro == "nivel_1" or xp_petro in (0, 1):
                    petro_nivel=frames_animacao_Petro

                elif xp_petro == "nivel_2" or xp_petro == 2:
                    petro_nivel=frames_animacao_Petro2

                elif xp_petro == "nivel_3" or (isinstance(xp_petro, (int, float)) and xp_petro >= 3):
                    petro_nivel=frames_animacao_Petro3
                else:
                    petro_nivel=frames_animacao_Petro



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
                            vida_boss-= dano_boss_mitigado(int(dano_person_hit*0.15)+15, 1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
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
            chamada_boss1_solicitada = pontuacao >= 3000500 or keys[pygame.K_r]
            if multiplayer_coop.modo_multiplayer() and not r_press and chamada_boss1_solicitada:
                multiplayer_coop.solicitar_acao("boss1", 1)
            if multiplayer_coop.modo_multiplayer() and not r_press and multiplayer_coop.acao_confirmada(
                "boss1", 1, delay_ms=4000, assumir_sim_apos_ms=multiplayer_coop.COOP_SILENCIO_CONFIRMA_MS
            ):
                r_press = True
            elif not multiplayer_coop.modo_multiplayer() and chamada_boss1_solicitada:
                r_press = True

            if r_press:
                # Verificar se é hora de realizar um ataque do boss
                Musica_tema_fases.stop()
                tempo_atual = pygame.time.get_ticks()


                if musica_boss1 == 1:
                    boss_vivo1=True
                    vida_boss = multiplayer_coop.aplicar_multiplicador_vida_boss(vida_boss)
                    vida_maxima_boss1 = multiplayer_coop.aplicar_multiplicador_vida_boss(vida_maxima_boss1)
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
                if (vida_boss <= 0 or (Ultimo_Estalo and vida_boss <= limiar_execucao_boss(Executa_inimigo) * vida_maxima_boss1)) and not boss_morte_processada:
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
                            registrar_conclusao_fase(1)
                            salvar_atributos()
                            pausar_cronometro()
                            tela_transicao_dimensional(tela, 2)
                            multiplayer_coop.enviar_transicao_fase(2)
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
                    desenhar_barra_vida_boss(
                        tela,
                        vida_boss,
                        vida_maxima_boss1,
                        "CARANGUEJO COSMICO",
                        1,
                        (143, 33, 252),
                        pos_boss=(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura)
                    )




                # Disparos contra o boss (só se não morreu)
                if not boss_morte_processada:
                    for disparo in disparos[:]:
                        pos_x_disparo=disparo["rect"].x 
                        pos_y_disparo=disparo["rect"].y 
                        rect_disparo = pygame.Rect(pos_x_disparo, pos_y_disparo, largura_disparo, altura_disparo)
                        rect_boss = pygame.Rect(pos_x_chefe, pos_y_chefe, chefe_largura, chefe_altura)

                        acertou_boss_disparo = (
                            lacerante_manifestacao.colisao_corte(disparo, rect_boss, tempo_atual)
                            if disparo.get("tipo_manifestacao") == "lacerante_corte"
                            else (
                                prismatica_manifestacao.colisao_feixe(disparo, rect_boss, tempo_atual)
                                if disparo.get("tipo_manifestacao") == "prismatica_feixe"
                                else (
                                    retornante_manifestacao.colisao_alvo(disparo, {"rect": rect_boss, "retornante_id": "boss1"})
                                    if disparo.get("tipo_manifestacao") == "retornante_pulso"
                                    else rect_disparo.colliderect(rect_boss)
                                )
                            )
                        )

                        if acertou_boss_disparo:
                            acerto_prismatico = prismatica_manifestacao.registrar_acerto(
                                disparo, {"rect": rect_boss, "prismatica_id": "boss1"}, tempo_atual
                            )
                            acerto_retornante = retornante_manifestacao.registrar_acerto(
                                disparo,
                                {"rect": rect_boss, "retornante_id": "boss1"},
                                tempo_atual,
                                (pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2),
                            )
                            if vida_boss > 0:  # Verifica se o chefe está vivo antes de aplicar dano
                                if random.random() <= chance_critico:  # 10% de chance de dano crítico
                                    dano = dano_person_hit * fator_dano_aureas(tempo_atual) * 3  # Valor do dano crítico é 3 vezes o dano normal
                                    cor = (255, 255, 0)  # Amarelo (RGB)
                                    fonte_dano = fonte_dano_critico
                                else:
                                    dano = dano_person_hit * fator_dano_aureas(tempo_atual)
                                    cor = (255, 0, 0)  # Vermelho (RGB)
                                    fonte_dano = fonte_dano_normal

                            # Ativar veneno no Boss com 50% de chance, se ainda não estiver envenenado
                            if not boss_envenenado and Poison_Active:
                                boss_envenenado = True
                                global duracao_veneno_boss
                                dano_por_tick_veneno_boss = vida_maxima_boss1 * Dano_Veneno_Acumulado
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
                            dano = boss_manifestacao_effects.aplicar_efeito_boss(disparo, dano, tempo_atual, efeitos_texto, rect_boss, "boss1")

                            # Renderizar texto do dano
                            tempo_texto_dano = pygame.time.get_ticks()
                            dano = dano_boss_mitigado(dano, 1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                            registrar_dano_boss(efeitos_texto, dano, pos_x_chefe + chefe_largura // 2, pos_y_chefe - 24, tempo_atual, cor)
                            vida_boss -= dano
                            if (vida_boss <= 0 or (Ultimo_Estalo and vida_boss <= limiar_execucao_boss(Executa_inimigo) * vida_maxima_boss1)) and not boss_morte_processada:
                                if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                    largura_disparo += 0.095
                                    altura_disparo += 0.095
                            if not (acerto_prismatico["manter_disparo"] or acerto_retornante["manter_disparo"]):
                                estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)

                            # Roubo de vida
                            if quantidade_roubo_vida > 0:
                                vida += (vida_maxima - vida) * quantidade_roubo_vida

                # Aplicar dano de veneno no Boss se ele estiver envenenado (só se não morreu)
                if boss_envenenado and not boss_morte_processada:
                    tempo_atual = pygame.time.get_ticks()

                    # Aplicar dano a cada 500 ms
                    if tempo_atual - ultimo_tick_veneno_boss >= INTERVALO_TICK_VENENO:
                        vida_boss -= dano_boss_mitigado(dano_por_tick_veneno_boss, 1, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0), tipo_dano="veneno")
                        ultimo_tick_veneno_boss = tempo_atual

                    # Exibir texto do dano de veneno (1.5 segundos)
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

                    # Desativar o veneno após o tempo de duração
                    if tempo_atual - tempo_inicio_veneno_boss >= duracao_veneno_boss:
                        boss_envenenado = False
                # Colisão e renderização do boss (só se vivo e morte não processada)
                if boss_vivo1 and not boss_morte_processada:
                    rect_boss = pygame.Rect(pos_x_chefe, pos_y_chefe, 200, 100)

                    rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)

                    if rect_boss.colliderect(rect_personagem) and tempo_atual >= tempo_boss_entrada_fim:
                        # Verifique se tempo suficiente passou desde o último ataque
                        tempo_atual = pygame.time.get_ticks()
                        if tempo_atual - tempo_ultimo_ataque >= 2500:
                            dano_boss_total=int((vida_maxima*0.10)+150+dano_boss)
                            if absorver_dano_devota_atual():
                                pass
                            elif imune_tempo_restante <= 0 and Resistencia < dano_boss_total:
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

            # --- PARTÍCULAS DE VENENO PINGANDO ---
            Variaveis.atualizar_e_desenhar_particulas_veneno(tela, inimigos_comum, config_graficos)
            if miniboss_condutor:
                for disparo in disparos[:]:
                    if not miniboss_condutor:
                        break
                    colisao_condutor = (
                        lacerante_manifestacao.colisao_corte(disparo, miniboss_condutor["rect"], tempo_atual)
                        if disparo.get("tipo_manifestacao") == "lacerante_corte"
                        else (
                            prismatica_manifestacao.colisao_feixe(disparo, miniboss_condutor["rect"], tempo_atual)
                            if disparo.get("tipo_manifestacao") == "prismatica_feixe"
                            else (
                                retornante_manifestacao.colisao_alvo(disparo, miniboss_condutor)
                                if disparo.get("tipo_manifestacao") == "retornante_pulso"
                                else disparo["rect"].colliderect(miniboss_condutor["rect"])
                            )
                        )
                    )
                    if colisao_condutor:
                        acerto_prismatico_condutor = prismatica_manifestacao.registrar_acerto(
                            disparo, miniboss_condutor, tempo_atual
                        )
                        acerto_retornante_condutor = retornante_manifestacao.registrar_acerto(
                            disparo, miniboss_condutor, tempo_atual,
                            (pos_x_personagem + largura_personagem // 2, pos_y_personagem + altura_personagem // 2),
                        )
                        if random.random() <= chance_critico:
                            dano_condutor = dano_person_hit * fator_dano_aureas(tempo_atual) * 3
                            cor_condutor = (255, 255, 0)
                        else:
                            dano_condutor = dano_person_hit * fator_dano_aureas(tempo_atual)
                            cor_condutor = (255, 80, 120)
                        dano_condutor *= insana_aurea.dano_mult_disparo(disparo)
                        dano_condutor *= voraz_aurea.dano_mult_disparo(disparo)
                        dano_condutor *= lacerante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_condutor *= prismatica_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_condutor *= retornante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_condutor *= parasitica_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_condutor *= condutora_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_condutor *= gravitante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_condutor *= ancorada_manifestacao.multiplicador_dano_disparo(disparo)
                        aplicar_dano_ao_condutor(dano_condutor, cor_condutor)
                        if miniboss_condutor and disparo.get("tipo_manifestacao") == "lacerante_corte":
                            lacerante_manifestacao.aplicar_laceracao(miniboss_condutor, tempo_atual)
                        if miniboss_condutor and disparo.get("tipo_manifestacao") == "parasitica_semente":
                            parasitica_manifestacao.implantar_semente(
                                miniboss_condutor, tempo_atual,
                                dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto
                            )
                        if miniboss_condutor and disparo.get("tipo_manifestacao") == "condutora_fio":
                            condutora_manifestacao.registrar_acerto_logico(
                                miniboss_condutor, tempo_atual,
                                dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto,
                                inimigos=inimigos_comum + [miniboss_condutor]
                            )
                        if miniboss_condutor and disparo.get("tipo_manifestacao") == "gravitante_orbe":
                            gravitante_manifestacao.ancorar_orbe(
                                miniboss_condutor, disparo, tempo_atual,
                                dano_person_hit * fator_dano_aureas(tempo_atual), efeitos_texto,
                                inimigos=inimigos_comum + [miniboss_condutor]
                            )
                        manter_disparo_condutor = (
                            acerto_prismatico_condutor.get("manter_disparo", False)
                            or acerto_retornante_condutor.get("manter_disparo", False)
                        )
                        if disparo in disparos and not manter_disparo_condutor:
                            estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)
            grade_disparos_colisao = Variaveis.construir_grade_disparos(disparos) if len(disparos) >= 12 else None
            for inimigo in inimigos_comum:
                inimigo_rect = inimigo["rect"]
                inimigo_image = inimigo["image"]

                inimigo_atingido = False

                disparos_candidatos = Variaveis.consultar_disparos_proximos(grade_disparos_colisao, inimigo_rect) or disparos[:]
                for disparo in disparos_candidatos:
                    if disparo.get("_removido_colisao"):
                        continue
                    if inimigo.get("invisivel", False):
                        continue

                    if (
                        retornante_manifestacao.colisao_alvo(disparo, inimigo)
                        if disparo.get("tipo_manifestacao") == "retornante_pulso"
                        else (
                            lacerante_manifestacao.colisao_corte(disparo, inimigo["rect"], tempo_atual)
                            if disparo.get("tipo_manifestacao") == "lacerante_corte"
                            else disparo["rect"].colliderect(inimigo["rect"])
                            if inimigo.get("tipo") == TIPO_LARAPIO
                            else verificar_colisao_disparo_inimigo(disparo, (inimigo["rect"].x, inimigo["rect"].y), largura_disparo, altura_disparo, largura_inimigo, altura_inimigo, inimigos_eliminados)
                        )
                    ):

                        if random.random() <= chance_critico:  # chance de dano crítico
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
                        
                        mitigacao = obter_mitigacao_dano(inimigo)
                        dano_final = dano * mitigacao
                        dano_final *= insana_aurea.dano_mult_disparo(disparo)
                        dano_final *= voraz_aurea.dano_mult_disparo(disparo)
                        dano_final *= lacerante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_final *= prismatica_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_final *= retornante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_final *= parasitica_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_final *= condutora_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_final *= gravitante_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_final *= ancorada_manifestacao.multiplicador_dano_disparo(disparo)
                        dano_final = aureas_avancadas.aplicar_dano_inimigo(
                            estado_aureas_avancadas, aurea, inimigo, disparo, dano_final,
                            tempo_atual, efeitos_texto, inimigos_comum
                        )
                        if mitigacao < 1.0:
                            cor = (0, 255, 255) # Cyan indicating shielded damage
                            
                        texto_hit = "-" + str(int(dano_final))
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
                        inimigo["vida"] -= dano_final
                        manter_evolucao = evolucoes_manifestacao.ao_acertar(
                            disparo, inimigo, inimigos_comum,
                            estado_evolucao_manifestacao, tempo_atual
                        )
                        multiplayer_coop.enviar_dano_inimigo(inimigo, dano_final, origem="disparo")
                        if inimigo.get("tipo") == TIPO_LARAPIO:
                            registrar_hit_larapio(inimigo)
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
                        if not (acerto_prismatico["manter_disparo"] or acerto_retornante["manter_disparo"] or manter_evolucao):
                            estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)  # Remover o disparo após colisão
                        # Adicionar uma chance de 50% de aumentar a vida em 20 pontos

                        if quantidade_roubo_vida > 0:
                            vida += (vida_maxima-vida)*quantidade_roubo_vida

                        if Poison_Active:
                            aplicar_veneno(inimigo, tempo_atual, cartas_compradas.get("Poison", 0))

                            # Dentro do loop principal, fora do loop de verificação de disparo


                        if Ultimo_Estalo and inimigo["vida"] <= Executa_inimigo * inimigo["vida_maxima"]:
                            insana_aurea.notificar_abate_insana(estado_insana, aurea, disparo)
                            bonus_aurea, reducao_habilidade = aureas_avancadas.aplicar_recompensa_abate(
                                estado_aureas_avancadas, aurea, inimigo, tempo_atual, efeitos_texto
                            )
                            pontuacao += bonus_aurea
                            pontuacao_exib += bonus_aurea
                            tempo_ultimo_uso_habilidade += reducao_habilidade
                            estalos.play()
                            processar_morte_inimigo(inimigo)
                            if inimigo in inimigos_comum:
                                inimigos_comum.remove(inimigo)
                            if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                largura_disparo += 0.095
                                altura_disparo += 0.095

                            inimigos_eliminados += 1
                            mult_exec = 1.0 + (nivel_ameaca * 0.12) # Execução dá 12% a mais de escala

                            vida_inimigo_maxima += ganho_vida_inimigo_comum(0.6 * mult_exec)
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
                                vida_boss += ganho_progressao_boss(15 * mult_exec)
                                vida_maxima_boss1 = vida_boss
                                vida_boss2 += ganho_progressao_boss(20 * mult_exec)
                                vida_maxima_boss2 = vida_boss2
                                vida_boss3 += ganho_progressao_boss(25 * mult_exec)
                                vida_maxima_boss3 = vida_boss3
                                vida_boss4 += ganho_progressao_boss(30 * mult_exec)
                                vida_maxima_boss4 = vida_boss4

                        elif inimigo["vida"] <= 0:
                            insana_aurea.notificar_abate_insana(estado_insana, aurea, disparo)
                            bonus_aurea, reducao_habilidade = aureas_avancadas.aplicar_recompensa_abate(
                                estado_aureas_avancadas, aurea, inimigo, tempo_atual, efeitos_texto
                            )
                            pontuacao += bonus_aurea
                            pontuacao_exib += bonus_aurea
                            tempo_ultimo_uso_habilidade += reducao_habilidade
                            processar_morte_inimigo(inimigo)
                            if inimigo in inimigos_comum:
                                inimigos_comum.remove(inimigo)
                            if isinstance(disparo, dict) and disparo.get("tipo_manifestacao") == "lacerante_corte" and disparo.get("estagio_corte") == 2:
                                largura_disparo += 0.095
                                altura_disparo += 0.095

                            # Crescimento proporcional por nível de ameaça
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
                                    vida_boss += ganho_progressao_boss(15 + nivel_ameaca * 10)
                                    vida_maxima_boss1 = vida_boss
                                    vida_boss2 += ganho_progressao_boss(20 + nivel_ameaca * 12)
                                    vida_maxima_boss2 = vida_boss2
                                    vida_boss3 += ganho_progressao_boss(25 + nivel_ameaca * 15)
                                    vida_maxima_boss3 = vida_boss3
                                    vida_boss4 += ganho_progressao_boss(30 + nivel_ameaca * 18)
                                    vida_maxima_boss4 = vida_boss4




                            break  # Sai do loop interno para evitar problemas ao modificar a lista enquanto iteramos sobre ela

                if "veneno" in inimigo:
                    # Verifique se é hora de aplicar dano
                    if tempo_atual - inimigo["veneno"]["ultimo_tick"] >= INTERVALO_TICK_VENENO:
                        inimigo["vida"] -= inimigo["veneno"]["dano_por_tick"]
                        if inimigo.get("tipo") == TIPO_LARAPIO:
                            registrar_hit_larapio(inimigo)
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





            total_cartas_compradas = sum(cartas_compradas.values())
            custo_carta_atual = custo_base_carta + (total_cartas_compradas * custo_por_carta)
            # A chave coletada é o novo gatilho da loja: sem botão, sem chamado manual.
            modo_loja_normal = Variaveis.obter_modo_cartas() != "drops"
            abrir_loja_manual = modo_loja_normal and Variaveis.tem_chave_loja() and pontuacao_exib >= custo_carta_atual
            if abrir_loja_manual:
                Variaveis.cancelar_aviso_loja_forcada()
                Variaveis.consumir_chave_loja()
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


            pontuacao_exib, pontuacao_magia = Variaveis.atualizar_e_desenhar_larapios_pontos(
                tela, tempo_atual, pos_x_personagem, pos_y_personagem,
                largura_personagem, altura_personagem,
                pontuacao_exib, pontuacao_magia, custo_carta_atual, efeitos_texto
            )

            cooldowns = {
                "disparo": max(0.0, (intervalo_disparo_racional(intervalo_disparo, aurea, racional_dilatacao_fim, tempo_atual) - (tempo_atual - tempo_ultimo_disparo)) / 1000.0),
                "teleporte": max(0.0, (tempo_cooldown_dash - (pygame.time.get_ticks() - tempo_ultimo_dash)) / 1000.0),
                "onda": max(0.0, (cooldown_habilidade * voraz_aurea.bonus_cooldown(estado_voraz, aurea) * parasitica_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * lacerante_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) * condutora_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) - (tempo_atual - tempo_ultimo_uso_habilidade)) / 1000.0),
                "ultimate": ultimate_manifestacao.restante_ms(tempo_atual) / 1000.0,
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

                if deve_desenhar_habilidades(
                    (pos_x_personagem, pos_y_personagem), (largura_personagem, altura_personagem)
                ):
                    # Desenhar habilidades na tela
                    desenhar_habilidades(tela, cooldowns, dispositivo_ativo, (pos_x_personagem, pos_y_personagem))
                if Mercenaria_Active:
                    fonte_combo = Variaveis._hud_font(None, 36)  # Tamanho maior para o combo
                    fonte_bonus = Variaveis._hud_font(None, 28)  # Tamanho menor para o bônus

                    # Texto do combo
                    texto_combo = f"Mercenaria: {eliminacoes_consecutivas} abates"
                    posicao_combo = (largura_mapa - 330, 50)
                    desenhar_texto_com_contorno(tela, texto_combo, fonte_combo, (255, 220, 80), (0, 0, 0), posicao_combo)

                    # Texto do bônus
                    faltam_bonus = 5 - (eliminacoes_consecutivas % 5)
                    texto_bonus = f"Bonus: +{bonus_pontuacao} | prox +{Valor_Bonus} em {faltam_bonus}"
                    posicao_bonus = (largura_mapa - 330, 90)
                    desenhar_texto_com_contorno(tela, texto_bonus, fonte_bonus, (255, 245, 190), (0, 0, 0), posicao_bonus)

            texto_dano = None
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
                fonte_tut = Variaveis._hud_font(None, 48)

                # Carregar teclas dinâmicas e modo de teleporte
                tecla_cima = Variaveis.formatar_nome_tecla(Variaveis.config_teclas.get("Mover para cima", pygame.K_w))
                tecla_baixo = Variaveis.formatar_nome_tecla(Variaveis.config_teclas.get("Mover para baixo", pygame.K_s))
                tecla_esquerda = Variaveis.formatar_nome_tecla(Variaveis.config_teclas.get("Mover para esquerda", pygame.K_a))
                tecla_direita = Variaveis.formatar_nome_tecla(Variaveis.config_teclas.get("Mover para direita", pygame.K_d))
                tecla_teleporte = Variaveis.formatar_nome_tecla(Variaveis.config_teclas.get("Teleporte", pygame.K_LSHIFT))
                tecla_loja = "AUTO"
                modo_teleporte = Variaveis.obter_modo_teleporte()
                modo_sem_loja = Variaveis.obter_modo_cartas() == "drops"

                # Definir dimensões do painel de informações com base na fase do tutorial para enquadrar perfeitamente
                w, h = 600, 160  # padrão
                if tutorial_fase == 1:
                    w, h = 580, 150
                elif tutorial_fase == 2:
                    w, h = 720, 185
                elif tutorial_fase == 3:
                    w, h = (720, 125) if modo_teleporte == "mouse" else (680, 115)
                elif tutorial_fase == 4:
                    w, h = 720, 190
                elif tutorial_fase == 5:
                    w, h = 720, 160

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
                    tr = Variaveis._hud_texto(fonte_tut, txt, (255, 255, 255))
                    tb = Variaveis._hud_texto(fonte_tut, txt, (0, 0, 0))
                    xm = cx - tr.get_width() // 2
                    tela.blit(tb, (xm - 1, y_pos))
                    tela.blit(tb, (xm + 1, y_pos))
                    tela.blit(tb, (xm, y_pos - 1))
                    tela.blit(tb, (xm, y_pos + 1))
                    tela.blit(tr, (xm, y_pos))

                # ====== FASE 1: WASD ======
                if tutorial_fase == 1:
                    _draw_msg(f"Use {tecla_cima}, {tecla_esquerda}, {tecla_baixo} e {tecla_direita} para se mover", y_msg)

                    # Teclas WASD flutuantes
                    esp = 5
                    tecla_y = y_msg + 50
                    
                    ft_k = Variaveis._hud_font(None, 24)
                    # Renderizar as teclas dinâmicas para calcular suas larguras corretas
                    txt_c = Variaveis._hud_texto(ft_k, tecla_cima, (255, 255, 255))
                    txt_e = Variaveis._hud_texto(ft_k, tecla_esquerda, (255, 255, 255))
                    txt_b = Variaveis._hud_texto(ft_k, tecla_baixo, (255, 255, 255))
                    txt_d = Variaveis._hud_texto(ft_k, tecla_direita, (255, 255, 255))
                    
                    # Altura padrão 32
                    tam = 32
                    w_c = max(32, txt_c.get_width() + 10)
                    w_e = max(32, txt_e.get_width() + 10)
                    w_b = max(32, txt_b.get_width() + 10)
                    w_d = max(32, txt_d.get_width() + 10)

                    # Posicionamento centralizado relativo
                    # Cima (W) centrado no topo
                    cx_c = cx
                    cy_c = tecla_y
                    
                    # Baixo (S) centrado no meio
                    cx_b = cx
                    cy_b = tecla_y + tam + esp
                    
                    # Esquerda (A) à esquerda do Baixo
                    cx_e = cx - w_b // 2 - esp - w_e // 2
                    cy_e = tecla_y + tam + esp
                    
                    # Direita (D) à direita do Baixo
                    cx_d = cx + w_b // 2 + esp + w_d // 2
                    cy_d = tecla_y + tam + esp
                    
                    posicoes = [
                        (tecla_cima, cx_c - w_c // 2, cy_c, w_c, tutorial_wasd['w'], txt_c),
                        (tecla_esquerda, cx_e - w_e // 2, cy_e, w_e, tutorial_wasd['a'], txt_e),
                        (tecla_baixo, cx_b - w_b // 2, cy_b, w_b, tutorial_wasd['s'], txt_b),
                        (tecla_direita, cx_d - w_d // 2, cy_d, w_d, tutorial_wasd['d'], txt_d),
                    ]
                    
                    pulso = abs(pygame.time.get_ticks() % 1200 - 600) / 600.0
                    for letra, kx, ky, kw, ok, render_txt in posicoes:
                        if ok:
                            cor_bg = (20, 120, 200, 220)
                            cor_bd = (53, 200, 252)
                        else:
                            alpha = int(100 + 60 * pulso)
                            cor_bg = (20, 30, 50, alpha)
                            cor_bd = (int(53 + 80 * pulso), int(100 + 60 * pulso), 200)
                        ks = pygame.Surface((kw, tam), pygame.SRCALPHA)
                        ks.fill(cor_bg)
                        tela.blit(ks, (kx, ky))
                        pygame.draw.rect(tela, cor_bd, (kx, ky, kw, tam), 2)
                        tela.blit(render_txt, (kx + kw // 2 - render_txt.get_width() // 2, ky + tam // 2 - render_txt.get_height() // 2))

                # ====== FASE 2: SHIFT / Teleporte ======
                elif tutorial_fase == 2:
                    if modo_teleporte == "mouse":
                        _draw_msg(f"Segure {tecla_teleporte} para mirar com o mouse!", y_msg)
                    else:
                        _draw_msg(f"Aperte {tecla_teleporte} para teleportar!", y_msg)
                        
                    fonte_sub = Variaveis._hud_font(None, 32)
                    # Subtexto 1 com contraste (Sky Blue)
                    if modo_teleporte == "mouse":
                        t1 = "Solte a tecla para se teleportar na posicao do cursor"
                    else:
                        t1 = "O teleporte vai na direcao da ultima tecla apertada"
                        
                    sub1_b = Variaveis._hud_texto(fonte_sub, t1, (0, 0, 0))
                    sub1 = Variaveis._hud_texto(fonte_sub, t1, (170, 240, 255))
                    tela.blit(sub1_b, (cx - sub1.get_width() // 2 + 1, y_msg + 46))
                    tela.blit(sub1, (cx - sub1.get_width() // 2, y_msg + 45))
                    
                    # Subtexto 2 com contraste (Sky Blue)
                    if modo_teleporte == "mouse":
                        t2 = f"Mire e solte para se mover! ({tutorial_dash_count}/3)"
                    else:
                        t2 = f"Use para se reposicionar! ({tutorial_dash_count}/3)"
                        
                    sub2_b = Variaveis._hud_texto(fonte_sub, t2, (0, 0, 0))
                    sub2 = Variaveis._hud_texto(fonte_sub, t2, (170, 240, 255))
                    tela.blit(sub2_b, (cx - sub2.get_width() // 2 + 1, y_msg + 76))
                    tela.blit(sub2, (cx - sub2.get_width() // 2, y_msg + 75))

                    # Desenhar tecla de Teleporte pulsando
                    pulso = abs(pygame.time.get_ticks() % 1200 - 600) / 600.0
                    ft_s = Variaveis._hud_font(None, 24)
                    st = Variaveis._hud_texto(ft_s, tecla_teleporte, (255, 255, 255))
                    
                    shift_w = max(80, st.get_width() + 20)
                    shift_h = 32
                    sx = cx - shift_w // 2
                    sy = y_msg + 110
                    alpha = int(100 + 60 * pulso)
                    ss = pygame.Surface((shift_w, shift_h), pygame.SRCALPHA)
                    ss.fill((20, 30, 50, alpha))
                    tela.blit(ss, (sx, sy))
                    cor_bd = (int(53 + 80 * pulso), int(100 + 60 * pulso), 200)
                    pygame.draw.rect(tela, cor_bd, (sx, sy, shift_w, shift_h), 2)
                    tela.blit(st, (sx + shift_w // 2 - st.get_width() // 2, sy + shift_h // 2 - st.get_height() // 2))

                # ====== FASE 3: Parede Roxa ======
                elif tutorial_fase == 3:
                    if modo_teleporte == "mouse":
                        _draw_msg("Atravesse a barreira usando o mouse!", y_msg)
                        t_sub = f"Segure {tecla_teleporte}, aponte do outro lado da barreira e solte"
                    else:
                        _draw_msg("Atravesse a barreira usando o teleporte!", y_msg)
                        t_sub = "Você não pode passar andando, apenas teleportando"
                        
                    fonte_sub = Variaveis._hud_font(None, 32)
                    sub_b = Variaveis._hud_texto(fonte_sub, t_sub, (0, 0, 0))
                    sub = Variaveis._hud_texto(fonte_sub, t_sub, (170, 240, 255))
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
                    ft_lmb = Variaveis._hud_font(None, 20)
                    lmb_txt = Variaveis._hud_texto(ft_lmb, "LMB", (255, 255, 255))
                    tela.blit(lmb_txt, (mx_icon + mouse_icon_w // 2 - lmb_txt.get_width() // 2, my_icon + mouse_icon_h + 5))

                    # Desenhar e gerenciar o inimigo do tutorial
                    if tutorial_inimigo_ativo and tutorial_inimigo is not None:
                        # Desenhar sombra e sprite do inimigo
                        tutorial_inimigo["image"] = frames_inimigo[frame_atual % len(frames_inimigo)]
                        desenhar_sombra(tela, tutorial_inimigo["rect"].x, tutorial_inimigo["rect"].y, largura_inimigo, altura_inimigo)
                        tela.blit(tutorial_inimigo["image"], tutorial_inimigo["rect"])
                        desenhar_barra_de_vida(tela, tutorial_inimigo["rect"].x, tutorial_inimigo["rect"].y - 10, largura_inimigo, 5, tutorial_inimigo["vida"], tutorial_inimigo["vida_maxima"], tutorial_inimigo.get("eletrocutado", False), Executa_inimigo if Ultimo_Estalo else None)

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
                            acertou_tut_disparo = (
                                lacerante_manifestacao.colisao_corte(disparo, tutorial_inimigo["rect"], tempo_atual)
                                if disparo.get("tipo_manifestacao") == "lacerante_corte"
                                else disparo["rect"].colliderect(tutorial_inimigo["rect"])
                            )
                            if acertou_tut_disparo:
                                dano_tut = dano_person_hit * lacerante_manifestacao.multiplicador_dano_disparo(disparo)
                                tutorial_inimigo["vida"] -= dano_tut
                                if disparo in disparos:
                                    estourar_disparo_eletrico(disparos, disparo, vfx_disparo_player, config_graficos)
                                Hit_inimigo1.play()

                                if tutorial_inimigo["vida"] <= 0:
                                    gerar_fragmentos_morte(tutorial_inimigo, 1)
                                    tutorial_inimigo_ativo = False
                                    tutorial_inimigo = None
                                    if modo_sem_loja:
                                        tutorial_fase = 7
                                        mostrar_tutorial = False
                                        try:
                                            with open("saves/tutorial_config.json", "w") as f:
                                                json.dump({"mostrar_tutorial": False}, f)
                                        except:
                                            pass
                                    else:
                                        tutorial_fase = 5
                                    tempo_fase_completa = time.time()
                                    break

                # ====== FASE 5: Ensinar a loja por chave ======
                elif tutorial_fase == 5:
                    if modo_sem_loja:
                        tutorial_fase = 7
                        mostrar_tutorial = False
                        try:
                            with open("saves/tutorial_config.json", "w") as f:
                                json.dump({"mostrar_tutorial": False}, f)
                        except:
                            pass
                        continue
                    # Garantir que o jogador tenha pontos suficientes para comprar
                    total_cartas_temp = sum(cartas_compradas.values())
                    custo_temp = custo_base_carta + (total_cartas_temp * custo_por_carta)
                    if pontuacao_exib < custo_temp:
                        pontuacao_exib = custo_temp
                        pontuacao = pontuacao_exib
                    if not Variaveis.tem_chave_loja():
                        Variaveis.adicionar_chave_loja()

                    _draw_msg("A chave da loja abre a compra automaticamente!", y_msg)
                    fonte_sub = Variaveis._hud_font(None, 32)
                    t_sub = "Colete uma chave e tenha pontos para escolher uma carta"
                    sub_b = Variaveis._hud_texto(fonte_sub, t_sub, (0, 0, 0))
                    sub = Variaveis._hud_texto(fonte_sub, t_sub, (170, 240, 255))
                    tela.blit(sub_b, (cx - sub.get_width() // 2 + 1, y_msg + 46))
                    tela.blit(sub, (cx - sub.get_width() // 2, y_msg + 45))

                    # Desenhar indicador de abertura automatica da loja
                    pulso = abs(pygame.time.get_ticks() % 1200 - 600) / 600.0
                    ft_q = Variaveis._hud_font(None, 28)
                    qt = Variaveis._hud_texto(ft_q, tecla_loja, (255, 255, 255))
                    
                    q_w = max(40, qt.get_width() + 15)
                    q_h = 40
                    qx = cx - q_w // 2
                    qy = y_msg + 80
                    alpha_q = int(100 + 60 * pulso)
                    qs = pygame.Surface((q_w, q_h), pygame.SRCALPHA)
                    qs.fill((20, 30, 50, alpha_q))
                    tela.blit(qs, (qx, qy))
                    cor_bd_q = (int(53 + 80 * pulso), int(100 + 60 * pulso), 200)
                    pygame.draw.rect(tela, cor_bd_q, (qx, qy, q_w, q_h), 2)
                    tela.blit(qt, (qx + q_w // 2 - qt.get_width() // 2, qy + q_h // 2 - qt.get_height() // 2))

                    # Quando o jogador comprar (apertou_q fica True), o tutorial acaba
                    if apertou_q:
                        tutorial_fase = 7
                        mostrar_tutorial = False
                        try:
                            with open("saves/tutorial_config.json", "w") as f:
                                json.dump({"mostrar_tutorial": False}, f)
                        except:
                            pass
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
                            if inimigo.get("tipo") == TIPO_LARAPIO:
                                registrar_hit_larapio(inimigo)

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
            atualizar_e_desenhar_moedas_larapio(tela)
            atualizar_e_desenhar_pedacos_cartas(tela)
            atualizar_e_desenhar_moedas_arremessadas(tela)

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

            # --- SISTEMA DE CARTAS DROP ---
            vida = Variaveis.aplicar_regen_passivo_base(vida, vida_maxima, tempo_atual, "fase1")
            Variaveis.atualizar_e_coletar_chaves_loja(tela, tempo_atual, personagem_rect, efeitos_texto)
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



            # A cada 13 minutos de jogo, lembra que R chama o boss imediatamente.
            tempo_jogo_segundos = int(Variaveis.obter_tempo_decorrido())
            aviso_boss_periodo = tempo_jogo_segundos // (13 * 60)
            if not mostrar_tutorial and not r_press and aviso_boss_periodo > 0:
                if alerta_boss_mostrado_para != aviso_boss_periodo:
                    alerta_boss_ativo = True
                    tempo_inicio_alerta_boss = pygame.time.get_ticks()
                    alerta_boss_mostrado_para = aviso_boss_periodo

            if alerta_boss_ativo:
                if pygame.time.get_ticks() - tempo_inicio_alerta_boss >= 4000:
                    alerta_boss_ativo = False
                else:
                    # Painel de notificacao com efeito de vidro
                    w_n, h_n = 820, 120
                    cx_n = largura_mapa // 2
                    cy_n = altura_mapa // 2
                    card_n = pygame.Surface((w_n, h_n), pygame.SRCALPHA)
                    pygame.draw.rect(card_n, (20, 10, 12, 235), (0, 0, w_n, h_n), border_radius=12)
                    pygame.draw.rect(card_n, (255, 60, 60), (0, 0, w_n, h_n), width=2, border_radius=12)
                    tela.blit(card_n, (cx_n - w_n // 2, cy_n - h_n // 2))
                    
                    font_n = Variaveis._hud_font(None, 32)
                    msg_line1 = Variaveis._hud_texto(font_n, "R CHAMA O BOSS IMEDIATAMENTE.", (255, 230, 230))
                    msg_line2 = Variaveis._hud_texto(font_n, "Se voce ainda esta fraco, NAO aperte R: farme cartas primeiro.", (255, 100, 100))
                    msg_line3 = Variaveis._hud_texto(font_n, "Quando estiver forte, aperte R para iniciar a luta.", (190, 255, 210))
                    
                    tela.blit(msg_line1, (cx_n - msg_line1.get_width() // 2, cy_n - 42))
                    tela.blit(msg_line2, (cx_n - msg_line2.get_width() // 2, cy_n - 8))
                    tela.blit(msg_line3, (cx_n - msg_line3.get_width() // 2, cy_n + 26))

            # --- DESENHAR BANNER DE EVENTO (VARIANTES) ---
            if aviso_evento_texto and not r_press and tempo_atual - aviso_evento_inicio <= 4000:
                # Semi-transparent background stripe
                banner_surf = pygame.Surface((largura_tela, 60), pygame.SRCALPHA)
                banner_surf.fill((15, 10, 20, 200))
                tela.blit(banner_surf, (0, altura_tela // 3))
                
                # Glowing borders
                pygame.draw.line(tela, aviso_evento_cor, (0, altura_tela // 3), (largura_tela, altura_tela // 3), 2)
                pygame.draw.line(tela, aviso_evento_cor, (0, altura_tela // 3 + 60), (largura_tela, altura_tela // 3 + 60), 2)
                
                # Render text
                fonte_banner = Variaveis._hud_font(None, 40)
                txt_b = Variaveis._hud_texto(fonte_banner, aviso_evento_texto, (0, 0, 0))
                txt_rend = Variaveis._hud_texto(fonte_banner, aviso_evento_texto, aviso_evento_cor)
                
                cx_b = largura_tela // 2
                cy_b = altura_tela // 3 + 30
                # Contorno para contraste
                tela.blit(txt_b, (cx_b - txt_rend.get_width() // 2 + 1, cy_b - txt_rend.get_height() // 2 + 1))
                tela.blit(txt_rend, (cx_b - txt_rend.get_width() // 2, cy_b - txt_rend.get_height() // 2))

            Variaveis.desenhar_refragmentacao_rewind(tela, tempo_atual)
            Variaveis.desenhar_overlay_vida_critica(tela, vida, vida_maxima, tempo_atual)

            desenhar_hud_fase(
                tela, vida, vida_maxima, pontuacao_exib, custo_carta_atual,
                pontuacao_magia, cooldowns, dispositivo_ativo,
                eliminacoes_consecutivas, bonus_pontuacao, aurea,
                escudo_devota_ativo, pos_x_personagem, pos_y_personagem,
                largura_personagem, altura_personagem,
                fps_atual=FPS.get_fps()
            )
            voraz_aurea.desenhar_voraz(tela, estado_voraz, aurea, tempo_atual, largura_tela, config_graficos, player_pos=(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem))

            Variaveis.aplicar_tremor_dano_tela(tela, tempo_atual, tempo_ultimo_hit_inimigo, piscando_vida)

            tela.blit(cursor_imagem, (mouse_x, mouse_y))

            # Aplica tremor de tela se necessário
            if shake_x != 0 or shake_y != 0:
                shake_temp = tela.copy()
                tela.fill((10, 5, 20))  # Cor cósmica escura de fundo
                tela.blit(shake_temp, (shake_x, shake_y))

            exibir_cronometro(tela)

            multiplayer_coop.desenhar_status_acao(tela, fonte, "loja", 1)
            multiplayer_coop.desenhar_status_acao(tela, fonte, "pause", 1)
            multiplayer_coop.desenhar_status_acao(
                tela,
                fonte,
                "boss1",
                1,
                delay_ms=4000,
                assumir_sim_apos_ms=multiplayer_coop.COOP_SILENCIO_CONFIRMA_MS,
            )
            multiplayer_coop.desenhar_diagnostico(tela, fonte)
            pygame.display.flip()
            dt_ms = FPS.tick(Variaveis.obter_limite_fps(config_graficos))  # Limita a taxa de quadros conforme configuração
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
