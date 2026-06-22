import pygame
import subprocess
import sys
import random
import math
import time
import os
import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
for _folder in ("Fases", "Manifestacoes", "Aureas", "Rede", "Boss", "Menus", "Engine"):
    _path = str(_PROJECT_ROOT / _folder)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from Tela_Cartas import tela_de_pausa
from Variaveis import *
import Variaveis
from utils import *
from ui_helpers import (
    desenhar_hud_fase,
    obter_pos_mouse_jogo,
    desenhar_efeitos_vanguarda,
    desenhar_efeito_racional_dilatacao,
    fator_movimento_racional,
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
    restaurar_escudo_devota,
)
from onda_recoil import criar_estado_coice_onda, aplicar_coice_onda, atualizar_coice_onda
import habilidade_boss_player as hb
import collections
from audio_manager import carregar_config_audio, aplicar_volume_som
from sistema_ratos_umbra import GerenciadorRatos
from vfx_engine_apolo import ApoloVFXManager
from player_projectile import PlayerProjectileVFX, estourar_disparo_eletrico
from habilidades_personagem import desenhar_onda, criar_particulas_explosao_onda as criar_particulas_explosao
from qa_logger import instalar_captura_global, instalar_filtro_prints
escudo_devota_ativo = True
duracao_incendio_vanguarda = 5000
intervalo_escudo = 30000
dt = 1.0
instalar_captura_global()
instalar_filtro_prints()
_VORTICE_SURF_CACHE = {}
_fonte_bonus_cached = None
_fonte_combo_cached = None
apolo = None
aurea = "Racional"
manifestacao_ativa = None
bonus_cura_sifon = 0.5
cartas_compradas_apolo_global = []
gerenciador_ratos = None
hitbox_boss5 = None
joystick = None
modo_ia_treino = True
movimento_pressionado = False
multiplicador_dano_umbra = 1.0
reducao_cooldown_umbra = 1.0
resistencia_umbra = 0.0
tempo_ultimo_disparo = 0
tempo_boss_entrada_fim = 0
running = True
tempo_atual = 0
ultima_tecla_movimento = None
teleporte_sprites = []
teleporte_index = 0
teleporte_timer = 0
racional_dilatacao_fim = 0
racional_dilatacao_proximo_uso = 0
estado_impulsiva = criar_estado_impulsiva()
estado_devota = criar_estado_devota(False)
vanguarda_fogo_fim = 0
inimigos_em_chamas = {}
tempo_ultimo_escudo = pygame.time.get_ticks()
def alvos_vanguarda_fase5():
    alvos = []
    if gerenciador_ratos is not None:
        for rato in getattr(gerenciador_ratos, "ratos", []):
            alvos.append({"rect": rato.rect, "_vanguarda_id": id(rato)})
    return alvos
def reiniciar_estados_aureas_fase(aurea_atual):
    global estado_impulsiva, estado_devota, vanguarda_fogo_fim, inimigos_em_chamas
    estado_impulsiva = criar_estado_impulsiva()
    estado_devota = criar_estado_devota(aurea_atual == "Devota", pygame.time.get_ticks())
    vanguarda_fogo_fim = 0
    inimigos_em_chamas = {}
def fator_dano_aureas(agora_ms=None):
    agora_ms = pygame.time.get_ticks() if agora_ms is None else agora_ms
    return (
        fator_dano_impulsiva(aurea, estado_impulsiva)
        * fator_dano_devota(aurea, estado_devota, agora_ms)
    )
def incendiar_vanguarda_proximos(agora_ms):
    if aurea != "Vanguarda":
        return
    centro_x = pos_x_personagem + largura_personagem // 2
    centro_y = pos_y_personagem + altura_personagem // 2
    alcance = max(76, int(max(largura_personagem, altura_personagem) * 1.45))
    for alvo in alvos_vanguarda_fase5():
        rect = alvo["rect"]
        dist = math.hypot(rect.centerx - centro_x, rect.centery - centro_y)
        if dist <= alcance + max(rect.width, rect.height) * 0.4:
            inimigos_em_chamas[alvo["_vanguarda_id"]] = agora_ms
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
    absorvido, escudo_devota_ativo, escudo_quebrou = absorver_hit_devota(aurea, escudo_devota_ativo, estado_devota, agora_ms)
    if absorvido:
        if escudo_quebrou:
            tempo_ultimo_escudo = agora_ms
            efeitos_texto.append({
                "texto": "ESCUDO ROMPIDO: +DANO / -VELOCIDADE",
                "x": pos_x_personagem - 40,
                "y": pos_y_personagem - 28,
                "tempo_inicio": agora_ms,
                "cor": (80, 180, 255),
            })
        return 0
    nivel_queda = quebrar_frenesi_impulsiva(aurea, estado_impulsiva)
    if nivel_queda:
        impulsiva_ativa = False
        tipo_buff_impulsiva = None
        eliminacoes_consecutivas_impulsiva = 0
        efeitos_texto.append({
            "texto": f"PANICO N{nivel_queda}",
            "x": pos_x_personagem,
            "y": pos_y_personagem - 34,
            "tempo_inicio": agora_ms,
            "cor": (255, 70, 70),
        })
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


def executar_jogo(game_manager=None):
    global dt
    global carregar_atributos_na_fase, Chance_Sorte, Dano_Veneno_Acumulado, Executa_inimigo, Mercenaria_Active, Petro_active, Poison_Active, Resistencia, Resistencia_petro, Tempo_cura, Ultimo_Estalo, Valor_Bonus, _VORTICE_SURF_CACHE, _fonte_bonus_cached, _fonte_combo_cached, altura_boss, altura_disparo, altura_personagem, angulo_inclinacao_personagem, apolo, aurea, bonus_cura_sifon, bonus_pontuacao, boss_envenenado, boss_final_ativo, cartas_compradas_apolo_global, chance_critico, cooldown_dash, dano_inimigo_longe, dano_inimigo_perto, dano_person_hit, dano_petro, dano_por_tick_veneno_boss, direcao_atual, direcao_boss, disparos, distancia_dash, duracao_frame_onda, efeitos_texto, eliminacoes_consecutivas, eliminacoes_consecutivas_impulsiva, em_transicao_mapa, erros_player_contagem, escudo_devota_ativo, esferas_energia_umbra, espacamento, estado_atual_ia, frame_boss, gerenciador_ratos, hitbox_boss5, impulsiva_ativa, imune_tempo_restante, inicio_transicao_mapa, inimigos_eliminados, intervalo_disparo, largura_boss, largura_disparo, largura_personagem, linha, mapa_antigo, mapa_novo, modo_ia_treino, moedas_coletadas, moedas_soltadas, moedas_totais, movimento_pressionado, multiplicador_chamas, multiplicador_dano_umbra, ondas, particulas_fogo_player, petro_evolucao, piscando_vida, player_em_chamas, pontuacao, pontuacao_exib, porcentagem_cura, pos_x_personagem, pos_x_petro, pos_x_umbra, pos_y_personagem, pos_y_petro, pos_y_umbra, projeteis_boss, quantidade_roubo_vida, racional_dilatacao_fim, racional_dilatacao_proximo_uso, reducao_cooldown_umbra, relogio, resistencia_umbra, roubo_de_vida, running, surf, teleporte_duration, teleporte_index, teleporte_timer, tempo_atual, tempo_boss_entrada_fim, tempo_cooldown_dash, tempo_fim_chamas, tempo_inicial, tempo_inicio_buff_impulsiva, tempo_inicio_veneno_boss, tempo_passado_boss, tempo_ultima_esfera_umbra, tempo_ultima_regeneracao, tempo_ultimo_dash, tempo_ultimo_disparo, tempo_ultimo_hit_inimigo, tempo_ultimo_uso_habilidade, tipo_buff_impulsiva, trauma_umbra_acumulado, trembo, ultima_direcao_animacao, ultima_tecla_movimento, ultimo_tick_chamas, ultimo_tick_veneno_boss, velocidade_disparo, velocidade_personagem, vida, vida_boss, vida_maxima, vida_maxima_petro, vida_maxima_umbra, vida_petro, vida_umbra, xp_petro, duracao_incendio_vanguarda, intervalo_escudo, estado_impulsiva, estado_devota, vanguarda_fogo_fim, inimigos_em_chamas, tempo_ultimo_escudo
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

        import multiprocessing as mp
        mp.freeze_support()
        pygame.init()
        memoria_umbra = hb.MemoriaEvolutivaUmbra()
        vfx_apolo = ApoloVFXManager()
        vfx_disparo_player = PlayerProjectileVFX()

        # =============================================================================
        # CACHE GLOBAL DE PERFORMANCE — criados UMA vez, reutilizados a cada frame
        # =============================================================================
        # Fonte dos efeitos flutuantes: pygame.font.Font() e MUITO lenta para criar por frame
        _FONTE_EFEITO = pygame.font.Font(None, 28)

        # Cache de sombras SRCALPHA: Surface e cara de criar (aloca buffer RGBA do tamanho)
        # Indexado por (largura, altura, modo): reutiliza se tamanho nao mudou
        _SOMBRA_CACHE = {}

        # Superficies dos flocos e cristais da Prisao Criogenica (usadas em loop de 70 iter)
        _FLOCO_SURF = pygame.Surface((4, 4), pygame.SRCALPHA)
        pygame.draw.circle(_FLOCO_SURF, (200, 240, 255, 200), (2, 2), 2)
        _CRISTAL_SURF = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.polygon(_CRISTAL_SURF, (150, 220, 255, 220), [(3,0),(6,3),(3,6),(0,3)])

        # Cache da superficie do vortice da Prisao (recriada com quantizacao de 8px)
        _VORTICE_SURF_CACHE = {}   # {raio_quantizado: Surface}

        # Offsets pre-computados para contorno de texto (8 direcoes)
        _CONTORNO_OFFSETS = [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]

        # Pontos do circulo da magia pre-calculados (evita 360 trig functions/frame)
        _PONTOS_PREENCHIMENTO = []
        for i in range(361):
            rad = math.radians(i - 90)
            _x = centro_circulo[0] + raio_circulo * math.cos(rad)
            _y = centro_circulo[1] + raio_circulo * math.sin(rad)
            _PONTOS_PREENCHIMENTO.append((_x, _y))

        # Cache de textos estaticos da UI (vida, pontuacao)
        _CACHE_TEXTO_UI = {}
        def render_cached_text(texto, fonte, cor):
            key = (texto, cor)
            if key not in _CACHE_TEXTO_UI:
                if len(_CACHE_TEXTO_UI) > 200:
                    _CACHE_TEXTO_UI.clear()
                _CACHE_TEXTO_UI[key] = fonte.render(texto, True, cor)
            return _CACHE_TEXTO_UI[key]
        # =============================================================================


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

        estalos = aplicar_volume_som(pygame.mixer.Sound("Sounds/Estalo.mp3"), config_audio, canal="efeitos", volume_maximo=1.0)

        som_ataque_boss = aplicar_volume_som(pygame.mixer.Sound("Sounds/Hit_Boss1.mp3"), config_audio, canal="efeitos", volume_maximo=1.0)

        Disparo_Geo = aplicar_volume_som(pygame.mixer.Sound("Sounds/Disparo_Geo.wav"), config_audio, canal="efeitos", volume_maximo=1.0)

        Musica_tema_Boss1 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase1_Boss.mp3"), config_audio, canal="musica", volume_maximo=1.0)

        Musica_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase_boas.mp3"), config_audio, canal="musica", volume_maximo=1.0)

        Som_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Praia.wav"), config_audio, canal="musica", volume_maximo=1.0)

        Som_portal = aplicar_volume_som(pygame.mixer.Sound("Sounds/Portal.mp3"), config_audio, canal="efeitos", volume_maximo=1.0) 

        Dano_person = aplicar_volume_som(pygame.mixer.Sound("Sounds/hit_person.mp3"), config_audio, canal="efeitos", volume_maximo=0.1)  

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


        tempo_mostrando_mensagem = 0  
        imune_tempo_restante = 0  # Tempo restante de imunidade (em milissegundos)
        teleportado = False  # Controle de teleporte

        direcao_atual_petro="left_petro"
        carregar_atributos_na_fase=True
        nivel_ameaca = inimigos_eliminados // 10
        fonte_mensagem = pygame.font.Font(None, 48)  # Tamanho da fonte
        mensagens_exibidas = set()
        mensagem_ativa = None
        tempo_fim_mensagem = 0

        # Nossa ponte de dados (Dicionário simples, sem frescura)
        dados_ia_umbra = {"estado": "Aguardando...", "pesos": {}}

        def gerar_posicao_aleatoria(largura_mapa, altura_mapa, largura_personagem, altura_personagem):
            largura_mapa_int, altura_mapa_int, largura_personagem_int, altura_personagem_int=map(int,(largura_mapa, altura_mapa, largura_personagem, altura_personagem))
            x = random.randint(0, largura_mapa_int - largura_personagem_int)
            y = random.randint(0, altura_mapa_int - altura_personagem_int)
            return x, y


        def renderizar_portal_teleporte_umbra(tela, agora, cx, cy, cfg_graficos):
            cx, cy = int(cx), int(cy)
            qualidade = cfg_graficos.get("qualidade_grafica", "media")
            estatico = (qualidade == "desligado" or not cfg_graficos.get("particulas_ativas", True))

            if estatico:
                # Círculo Simples (Máximo Desempenho)
                pygame.draw.circle(tela, (0, 25, 40), (cx, cy), 60)
                pygame.draw.circle(tela, (0, 200, 200), (cx, cy), 60, 3)
                return

            # Efeitos Rotativos LÍQUIDOS (Médio / Alto)
            raio_base = 60 + math.sin(agora * 0.005) * 8

            # Camada de Fundo escura azulada/esverdeada
            pygame.draw.circle(tela, (0, 15, 30), (cx, cy), int(raio_base))

            # Anéis Vortex desenhados de forma procedural
            q_aneis = 4 if qualidade == "alta" else 2

            for i in range(q_aneis):
                offset_ang = agora * 0.003 * (i + 1)
                r = raio_base * (0.8 - i*0.15)

                for ang in range(0, 360, 30 if qualidade == "alta" else 60):
                    rad_inicio = math.radians(ang) + offset_ang
                    # Arcos mais alongados dão sensação fluida
                    rad_fim = math.radians(ang + 45) + offset_ang
                    px1 = cx + math.cos(rad_inicio) * r
                    py1 = cy + math.sin(rad_inicio) * r
                    px2 = cx + math.cos(rad_fim) * r * 0.95 # Puxando para o centro
                    py2 = cy + math.sin(rad_fim) * r * 0.95

                    # Subtil gradient entre verde neon e azul ciano
                    t_cor = (math.sin(agora * 0.002 + i) + 1) / 2
                    cor = (int(0 + t_cor * 50), int(255 - t_cor * 50), int(150 + t_cor * 105)) 

                    pygame.draw.line(tela, cor, (int(px1), int(py1)), (int(px2), int(py2)), 5 - i)

            # Partículas no Vortex (Alta Qualidade)
            if qualidade == "alta":
                for i in range(12):
                    seed = (agora // 15 + i * 40) 
                    ang = (seed * 0.15 + i * 0.5) % (math.pi * 2)
                    dist = 90 - (seed % 90)  # Sugado para o centro do vortex
                    if dist > 5:
                        px = cx + math.cos(ang) * dist
                        py = cy + math.sin(ang) * dist
                        tamanho = max(1, int(4 * (dist / 90)))
                        pygame.draw.circle(tela, (50, 255, 200), (int(px), int(py)), tamanho)

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
                if "cartas_compradas" in atributos:
                    cartas_compradas.update(atributos["cartas_compradas"])
                cartas_compradas = normalizar_cartas_compradas(cartas_compradas)


        try:
            with open("saves/aurea_selecionada.json", "r") as file:
                aurea = json.load(file).get("aurea", "Racional")
        except (OSError, json.JSONDecodeError, TypeError):
            aurea = "Racional"
        if aurea not in {"Racional", "Impulsiva", "Devota", "Vanguarda", "Insana", "Voraz", "Nula", "Abissal", "Profetica", "Sanguinaria"}:
            aurea = "Racional"
        manifestacao_ativa = Variaveis.obter_manifestacao_ativa()

        upgrade_aureas = carregar_upgrade_aureas("saves/aureas_upgrade.json")


        tempo_inicial = time.time() 

        tempo_anterior = pygame.time.get_ticks()
        tempo_movimento = random.randint(2000, 7000)
        tempo_parado = random.randint(500, 700) 
        movendo = True 
        boss_vivo1=False
        relogio = pygame.time.Clock()
        ultimo_tempo_reducao = time.time()
        largura_disparo, altura_disparo = 8, 8
        velocidade_disparo = 10
        disparos = []

        pygame.display.set_caption("Renderizando Mapa com Personagem")

        pontuacao_inimigos=0
        maxima_pontuacao_magia = 750
        piscar_magia = False





        #INIMIGOS
        # Carregar a imagem do mapa
        mapa_atual_path = mapa_path5
        mapa = pygame.image.load(mapa_atual_path).convert()
        mapa = pygame.transform.scale(mapa, (largura_mapa, altura_mapa))

        teleporte_sprites = [
            pygame.transform.scale(pygame.image.load("Sprites/icon_teleport.png").convert_alpha(), (80, 80)),
            pygame.transform.scale(pygame.image.load("Sprites/icon_teleport2.png").convert_alpha(), (80, 80))
        ]
        teleporte_index = 0
        teleporte_timer = 0

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


        def aplicar_shockwave_teleporte():
            global vida_umbra, vida, efeitos_texto
            global player_hemorragia_ativa, tempo_fim_hemorragia, penalidade_cura_percentual
            cx_t = pos_x_personagem + largura_personagem // 2
            cy_t = pos_y_personagem + altura_personagem // 2
            raio_choque = 120
            dano_choque = dano_person_hit * 0.3 * fator_dano_aureas()

            ondas_choque.append({
                "cx": cx_t,
                "cy": cy_t,
                "raio_atual": 10.0,
                "raio_max": raio_choque,
                "velocidade": 8.0,
                "cor": (148, 0, 211)
            })

            if 'luta_iniciada' in globals() and luta_iniciada and 'hitbox_boss5' in globals() and hitbox_boss5 is not None:
                bx = hitbox_boss5.centerx
                by = hitbox_boss5.centery
                dist_boss = math.hypot(bx - cx_t, by - cy_t)
                if dist_boss <= raio_choque:
                    dano_final = dano_choque
                    cor_feedback = (148, 0, 211)

                    if estado_atual_ia.get('parede_ativa'):
                        dano_final *= 0.75
                        cor_feedback = (0, 200, 255)

                    if 'resistencia_umbra' in globals() and resistencia_umbra > 0:
                        dano_final *= max(0.1, 1.0 - (resistencia_umbra / 100.0))

                    if estado_atual_ia.get('dimensao_ativa') == "atrito":
                        dano_final *= 0.3
                        if not estado_atual_ia.get('laser_ativo'):
                            estado_atual_ia['carga_atrito'] = estado_atual_ia.get('carga_atrito', 0) + 8
                            if estado_atual_ia['carga_atrito'] >= 100:
                                estado_atual_ia['laser_ativo'] = {
                                    'tempo_inicio':          pygame.time.get_ticks(),
                                    'fase':                  'carregando',
                                    'rodada':                1,
                                    'duracao_carga':         1500,
                                    'duracao_disparo':       4000,
                                    'angulo_base_inicio':    random.uniform(0, math.pi * 2)
                                }
                                estado_atual_ia['carga_atrito'] = 0

                    if vida_umbra > 0:
                        dano_final = dano_boss_mitigado(dano_final, 5, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                        vida_umbra -= dano_final
                        estado_atual_ia['dano_recente'] = estado_atual_ia.get('dano_recente', 0) + dano_final
                        vfx_apolo.criar_impacto_fragmentado(bx, by)

                        punicao = -4.0
                        memoria_umbra.treinar(punicao, prioridade=True)

                        if quantidade_roubo_vida > 0:
                            cura_base = (vida_maxima - vida) * quantidade_roubo_vida
                            if player_hemorragia_ativa and pygame.time.get_ticks() < tempo_fim_hemorragia:
                                cura_base *= (1.0 - penalidade_cura_percentual)
                            vida = min(vida_maxima, vida + cura_base)

                        efeitos_texto.append({
                            "texto": f"-{int(dano_final)}",
                            "x": bx,
                            "y": hitbox_boss5.top - 20,
                            "tempo_inicio": pygame.time.get_ticks(),
                            "cor": cor_feedback
                        })

        #####################################################################APOLO1######################################################################################################

        #####################################################################CONTROLE DO JOGADOR######################################################################################################
        def atualizar_posicao_personagem(keys, joystick):
            global pos_x_personagem, pos_y_personagem, direcao_atual, ultima_tecla_movimento
            global movimento_pressionado, cooldown_dash, distancia_dash, tempo_ultimo_dash, teleporte_duration
            global hitbox_boss5, estado_atual_ia

            dx, dy = 0, 0
            direcao_atual = 'stop'
        
            tempo_agora = pygame.time.get_ticks()
            tempo_fim_stun_ia = estado_atual_ia.get('fim_stun', 0) if 'estado_atual_ia' in globals() else 0
            atordoado = tempo_agora < tempo_fim_stun_ia

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
            
                # Normalização de movimento diagonal (com escala dt)
                if dx != 0 and dy != 0:
                    fator_normalizacao = 0.7071
                    pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                                 pos_x_personagem + dx * velocidade_personagem * fator_normalizacao * dt))
                    pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                                 pos_y_personagem + dy * velocidade_personagem * fator_normalizacao * dt))
                else:
                    pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                                 pos_x_personagem + dx * velocidade_personagem * dt))
                    pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                                 pos_y_personagem + dy * velocidade_personagem * dt))

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
                dash_teclado = keys[config_teclas["Teleporte"]]
                dash_joystick = joystick and joystick.get_button(4) if joystick else False
            
            if (dash_teclado or dash_joystick or executar_teleporte_mouse_flag) and cooldown_dash == False and atordoado == False:
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
                    # Animação de teletransporte (plasma procedural)
                    animar_teleporte_plasma(tela, mapa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, teleporte_duration // 2, ultima_tecla_movimento, distancia_dash, largura_mapa, altura_mapa)
                    tela.blit(mapa, (pos_x_personagem, pos_y_personagem), pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem))

                    if ultima_tecla_movimento == 'up': pos_y_personagem = max(0, pos_y_personagem - distancia_dash)
                    elif ultima_tecla_movimento == 'down': pos_y_personagem = min(altura_mapa - altura_personagem, pos_y_personagem + distancia_dash)
                    elif ultima_tecla_movimento == 'left': pos_x_personagem = max(0, pos_x_personagem - distancia_dash)
                    elif ultima_tecla_movimento == 'right': pos_x_personagem = min(largura_mapa - largura_personagem, pos_x_personagem + distancia_dash)
            
                cooldown_dash = True
                tempo_ultimo_dash = pygame.time.get_ticks()

            if cooldown_dash and pygame.time.get_ticks() - tempo_ultimo_dash > tempo_cooldown_dash:
                cooldown_dash = False

            return direcao_atual
        #####################################################################
        def criar_disparo():
                return {"rect": pygame.Rect(pos_x_personagem, pos_y_personagem, largura_disparo, altura_disparo),"direcao": ultima_tecla_movimento }



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


        def desenhar_sombra(tela, x, y, largura, altura, offset_y=5):
            """Desenha sombra eliptica com cache de Surface — sem alocar por frame."""
            modo_sombra = config_graficos.get("sombras_ativas", "dinamicas")

            if modo_sombra == "desativadas":
                return

            if modo_sombra == "simples":
                cache_key = (largura, altura, "simples")
                if cache_key not in _SOMBRA_CACHE:
                    surf = pygame.Surface((largura, altura // 3), pygame.SRCALPHA)
                    pygame.draw.ellipse(surf, (0, 0, 0, 80), (0, 0, largura, altura // 3))
                    _SOMBRA_CACHE[cache_key] = surf
                tela.blit(_SOMBRA_CACHE[cache_key], (x, y + altura - offset_y))

            elif modo_sombra == "dinamicas":
                cache_key = (largura, altura, "dinamicas")
                if cache_key not in _SOMBRA_CACHE:
                    sw, sh = int(largura * 1.2), int(altura // 2.5)
                    surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                    margem = int(largura * 0.15)
                    margem_i = int(largura * 0.25)
                    pygame.draw.ellipse(surf, (0, 0, 0, 40), (0, 0, sw, sh))
                    pygame.draw.ellipse(surf, (0, 0, 0, 70),
                                        (margem, margem // 2, int(largura * 0.9), int(altura // 3)))
                    pygame.draw.ellipse(surf, (0, 0, 0, 100),
                                        (margem_i, margem_i // 2, int(largura * 0.7), int(altura // 3.5)))
                    _SOMBRA_CACHE[cache_key] = surf
                surf = _SOMBRA_CACHE[cache_key]
                pos_x = x - int(largura * 0.1)
                pos_y = y + altura - offset_y - int(altura // 6)
                tela.blit(surf, (pos_x, pos_y))


        def soltar_moeda(posicao):
            chance = 0.05 # 5%
            if random.random() < chance:
                if not hasattr(soltar_moeda, '_sprite_cached'):
                    tamanho_moeda = (36, 36)
                    soltar_moeda._sprite_cached = pygame.transform.scale(sprite_moeda, tamanho_moeda)

                sprite_redimensionada = soltar_moeda._sprite_cached
                rect = sprite_redimensionada.get_rect(center=posicao)
                moedas_soltadas.append({
                    "rect": rect,
                    "image": sprite_redimensionada
                })





        # Variáveis Globais de Mutação da Umbra
        multiplicador_dano_umbra = 1.0
        reducao_cooldown_umbra = 1.0
        resistencia_umbra = 0.0
        bonus_cura_sifon = 0.5

        tempo_parado_person = pygame.time.get_ticks()  
        boss_atingido_por_onda = pygame.time.get_ticks()
        tempo_ultimo_disparo = pygame.time.get_ticks()
        disparo_preparando = False
        disparo_frame_atual = 0
        tempo_ultimo_frame_preparo_disparo = 0
        angulo_disparo_preparado = 0.0
        DISPARO_PREPARO_FRAME_MS = 85
        coice_onda = criar_estado_coice_onda()
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

        reiniciar_estados_aureas_fase(aurea)
        tempo_ultimo_escudo = pygame.time.get_ticks()

        FPS=pygame.time.Clock()
        pygame.mouse.set_visible(False)
        cursor_imagem = pygame.image.load("Sprites/Ponteiro.png").convert_alpha()  # Ajuste o caminho
        cursor_tamanho = cursor_imagem.get_size()

        sprite_moeda = pygame.image.load("Sprites/moeda.png").convert_alpha()
        moedas_soltadas = []

        modo_ia_treino = True





        import atexit, signal
        def _salvar_tudo_ao_sair():
            try:
                memoria_umbra.salvar()
            except Exception:
                pass
        atexit.register(_salvar_tudo_ao_sair)
        def _handler_ctrl_c(sig, frame):
            _salvar_tudo_ao_sair()
            sys.exit(0)
        signal.signal(signal.SIGINT, _handler_ctrl_c)

        cartas_compradas_apolo_global = []

        def carregar_memoria_cartas():
            arquivo = "saves/memoria_cartas_apolo.json"
            pesos_base = {
                "Speed Boost": {"N": 1, "W": 1}, "Porção": {"N": 1, "W": 1}, 
                "Disparo crescente": {"N": 1, "W": 1}, "Trembo": {"N": 1, "W": 1}, 
                "Tempestade": {"N": 1, "W": 1}, "Cura": {"N": 1, "W": 1}, 
                "Speed Atack": {"N": 1, "W": 1}, "Teleporte": {"N": 1, "W": 1}, 
                "Defesa": {"N": 1, "W": 1}
            }
            if os.path.exists(arquivo):
                try:
                    with open(arquivo, "r") as f:
                        pesos_salvos = json.load(f)
                        for k, v in pesos_salvos.items():
                            if isinstance(v, dict) and "N" in v and "W" in v:
                                pesos_base[k] = v
                            elif isinstance(v, float) or isinstance(v, int):
                                pesos_base[k] = {"N": max(1, int(v)), "W": max(0, int(v * 0.5))}
                except: pass
            return pesos_base

        def salvar_memoria_cartas(pesos):
            with open("saves/memoria_cartas_apolo.json", "w") as f:
                json.dump(pesos, f, indent=4)

        def recompensar_cartas(cartas_usadas, venceu):
            pesos = carregar_memoria_cartas()
            for carta in cartas_usadas:
                if carta in pesos:
                    pesos[carta]["N"] += 1
                    if venceu:
                        pesos[carta]["W"] += 1
            salvar_memoria_cartas(pesos)

        def inteligencia_escolha_cartas_apolo(qtd):
            import math
            pesos = carregar_memoria_cartas()
            escolhas = []
            opcoes = list(pesos.keys())

            total_jogadas = sum(v["N"] for v in pesos.values())
            if total_jogadas == 0: total_jogadas = 1
            C_exploration = math.sqrt(2)

            for _ in range(qtd):
                opcoes_validas = opcoes.copy()
                if escolhas.count("Trembo") >= 2 and "Trembo" in opcoes_validas: opcoes_validas.remove("Trembo")
                if escolhas.count("Cura") >= 10 and "Cura" in opcoes_validas: opcoes_validas.remove("Cura")
                if escolhas.count("Defesa") >= 10 and "Defesa" in opcoes_validas: opcoes_validas.remove("Defesa")
                if escolhas.count("Speed Boost") >= 8 and "Speed Boost" in opcoes_validas: opcoes_validas.remove("Speed Boost")
                if escolhas.count("Porção") >= 10 and "Porção" in opcoes_validas: opcoes_validas.remove("Porção")
                if escolhas.count("Tempestade") >= 12 and "Tempestade" in opcoes_validas: opcoes_validas.remove("Tempestade")
                if escolhas.count("Disparo crescente") >= 15 and "Disparo crescente" in opcoes_validas: opcoes_validas.remove("Disparo crescente")

                if not opcoes_validas:
                    break

                melhor_carta = None
                melhor_ucb = -float('inf')

                for op in opcoes_validas:
                    n_i = pesos[op]["N"]
                    w_i = pesos[op]["W"]
                    if n_i == 0:
                        ucb = float('inf')
                    else:
                        taxa_sucesso = w_i / n_i
                        exploracao = C_exploration * math.sqrt(math.log(total_jogadas) / n_i)
                        ucb = taxa_sucesso + exploracao

                    if ucb > melhor_ucb:
                        melhor_ucb = ucb
                        melhor_carta = op

                if melhor_carta:
                    escolhas.append(melhor_carta)

            return escolhas

        def injetar_build_endgame(qtd_cartas_jogador=30):
            global velocidade_personagem, intervalo_disparo, dano_person_hit, chance_critico
            global roubo_de_vida, quantidade_roubo_vida, vida_maxima, vida, trembo
            global tempo_cooldown_dash, Resistencia, Poison_Active, Dano_Veneno_Acumulado
            global Executa_inimigo, Ultimo_Estalo, Tempo_cura, porcentagem_cura
            global Petro_active, vida_petro, vida_maxima_petro, dano_petro, petro_evolucao
            global xp_petro, Resistencia_petro, Chance_Sorte, inimigos_eliminados

            global vida_maxima_umbra, vida_umbra
            global multiplicador_dano_umbra, reducao_cooldown_umbra, resistencia_umbra, bonus_cura_sifon
            global cartas_compradas_apolo_global, cartas_compradas

            inimigos_eliminados = 3000

            # --- PROGRESSÃO DO APOLO ---
            cartas_inteligentes = inteligencia_escolha_cartas_apolo(qtd_cartas_jogador)
            cartas_compradas_apolo_global = cartas_inteligentes

            # Reset and populate global cartas_compradas for the pause menu (ESC)
            for k in cartas_compradas:
                cartas_compradas[k] = 0
            for carta in cartas_inteligentes:
                if carta in cartas_compradas:
                    cartas_compradas[carta] += 1

            for carta in cartas_inteligentes:
                if carta == "Speed Boost":
                    velocidade_personagem += 0.09 + (inimigos_eliminados // 200) * 0.002
                    dano_person_hit += 10 + (inimigos_eliminados // 50) * 1.0
                elif carta == "Porção":
                    aumento_vida = 650 + (inimigos_eliminados // 50) * 8
                    vida_maxima += aumento_vida
                    vida += int(vida_maxima * 0.30)
                    vida_petro += int(vida_maxima_petro * 0.25)
                    if vida_petro > vida_maxima_petro: vida_maxima_petro = vida_petro
                elif carta == "Disparo crescente":
                    dano_person_hit = aplicar_incremento_carta_dano(dano_person_hit, inimigos_eliminados)
                elif carta == "Trembo":
                    trembo = True
                    Tempo_cura = max(500, int(Tempo_cura * 0.85)) # Em 10 cartas, o tick cai para próximo de 0.5s
                    porcentagem_cura += 0.005 + (inimigos_eliminados // 400) * 0.001 # Garante uma base inicial mais forte (0.5%)
                elif carta == "Tempestade":
                    dano_person_hit += 2.5 + (inimigos_eliminados // 100) * 1
                    chance_critico += 0.01 + (inimigos_eliminados // 300) * 0.002
                elif carta == "Cura":
                    roubo_de_vida += 0.25 + (inimigos_eliminados // 500) * 0.001
                    quantidade_roubo_vida += 0.30 + (inimigos_eliminados // 500) * 0.001
                elif carta == "Speed Atack":
                    intervalo_disparo = max(70, int(intervalo_disparo * 0.95))
                elif carta == "Teleporte":
                    reducao = 0.95 - min(0.15, (inimigos_eliminados // 1000) * 0.02)
                    tempo_cooldown_dash = max(0.4, tempo_cooldown_dash * reducao)

                elif carta == "Defesa":
                    Resistencia = min(60, Resistencia + 10 + (inimigos_eliminados // 200) * 0.25)


            # --- ESCALONAMENTO DINÂMICO DA UMBRA ---
            ataques_por_segundo = 1000 / max(50, intervalo_disparo)
            multiplicador_critico = 1 + (chance_critico * 2.0)
            dps_teorico_apolo = dano_person_hit * ataques_por_segundo * multiplicador_critico

            # Cap no dps para o boss não ficar imortal com muito dano
            dps_escalonamento = min(dps_teorico_apolo, 1200) 

            vida_maxima_umbra = int((20000 + (dps_escalonamento * 18) + (inimigos_eliminados * 20)) * 1.2)

            # --- O ESPELHO CORROMPIDO (CARTAS DA UMBRA) ---
            qtd_cartas_umbra = qtd_cartas_jogador // 3
            cartas_umbra = [
                "Essência Obscura", 
                "Projétil Devastador", 
                "Frenesi Temporal", 
                "Armadura de Matéria Escura", 
                "Sifão Aprimorado"
            ]

            registro_umbra = []
            for _ in range(qtd_cartas_umbra):
                carta_u = random.choice(cartas_umbra)
                registro_umbra.append(carta_u)
                if carta_u == "Essência Obscura":
                    vida_maxima_umbra = int(vida_maxima_umbra * 1.25) 
                elif carta_u == "Projétil Devastador":
                    multiplicador_dano_umbra += 0.05 + (inimigos_eliminados // 500) * 0.005
                elif carta_u == "Frenesi Temporal":
                    reducao_cooldown_umbra *= 0.92 
                elif carta_u == "Armadura de Matéria Escura":
                    resistencia_umbra += 2.5 
                elif carta_u == "Sifão Aprimorado":
                    bonus_cura_sifon += 0.05

            vida = vida_maxima
            vida_umbra = vida_maxima_umbra

        # Invoca a mutação absoluta
        injetar_build_endgame(qtd_cartas_jogador=80)
        ###################################################################################################################################################################################################
        # Geração de coordenadas estocásticas para o início do embate
        pos_x_personagem, pos_y_personagem = gerar_posicao_aleatoria(largura_mapa, altura_mapa, largura_personagem, altura_personagem)
        pos_x_petro= pos_x_personagem + largura_personagem + 4
        pos_y_petro = pos_y_personagem

        ###################################################################################################PRINCIPAL#################################################################################################################
        #LOOP PRINCIPAL

        # Inicializar gerenciador de ratos da Umbra
        gerenciador_ratos = GerenciadorRatos(largura_mapa, altura_mapa)

        # CACHE DE SPRITES DE DISPARO (Otimização Zero-Allocation)

        # Inicialização pré-loop (Zero-Allocation)
        tempo_ultimo_frame = pygame.time.get_ticks()
        _fonte_combo_cached = pygame.font.Font(None, 36)
        _fonte_bonus_cached = pygame.font.Font(None, 28)

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
            _autosave_treino_ias(tempo_atual)

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
                    "inimigos_eliminados": inimigos_eliminados,
                    "vida_umbra": vida_umbra,
                    "vida_maxima_umbra": vida_maxima_umbra,
                    "trauma_umbra_acumulado": trauma_umbra_acumulado,
                    "tempo_cronometro": Variaveis.obter_tempo_decorrido(),
                    "vida_boss": vida_umbra,
                    "boss_final_ativo": bool(boss_final_ativo)
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
                        inimigos_eliminados = snap.get("inimigos_eliminados", inimigos_eliminados)
                        vida_umbra = snap.get("vida_umbra", vida_umbra)
                        vida_maxima_umbra = snap.get("vida_maxima_umbra", vida_maxima_umbra)
                        trauma_umbra_acumulado = snap.get("trauma_umbra_acumulado", trauma_umbra_acumulado)
                        Variaveis.definir_tempo_cronometro(snap.get("tempo_cronometro", Variaveis.obter_tempo_decorrido()))
                        if snap.get("refragmentacao_rewind"):
                            imune_tempo_restante = max(imune_tempo_restante, 4000)
                            piscando_vida = False
                            Variaveis.aplicar_rewind_respawn_visual(pos_x_personagem, pos_y_personagem, direcao_atual, pygame.time.get_ticks())
                        if "vida_boss" in snap and snap["vida_boss"] is not None:
                            vida_umbra = snap["vida_boss"]
                        boss_final_ativo = snap.get("boss_final_ativo", boss_final_ativo)
                        Variaveis.snapshot_para_carregar = None
                except Exception as e:
                    registrar_erro("Fase 5: erro ao carregar atributos; usando padrao", e)
                carregar_atributos_na_fase = False
            agora = pygame.time.get_ticks()
            nivel_impulsiva = upgrades.get("Impulsiva", 0)
            eliminacoes_consecutivas_impulsiva, eventos_impulsiva = atualizar_ciclo_impulsiva(
                aurea,
                estado_impulsiva,
                eliminacoes_consecutivas_impulsiva,
                agora,
                nivel_impulsiva,
            )
            impulsiva_ativa = bool(estado_impulsiva.get("ativa"))
            tipo_buff_impulsiva = "frenesi" if impulsiva_ativa else None
            for evento_impulsiva in eventos_impulsiva:
                texto_evento = "FRENESI DISSIPADO" if evento_impulsiva["tipo"] == "fim" else f"FRENESI N{evento_impulsiva.get('nivel', 0)}"
                if evento_impulsiva["tipo"] == "ascendeu":
                    texto_evento = f"ASCENSAO N{evento_impulsiva['nivel']}"
                efeitos_texto.append({
                    "texto": texto_evento,
                    "x": pos_x_personagem,
                    "y": pos_y_personagem - 24,
                    "tempo_inicio": pygame.time.get_ticks(),
                    "cor": (255, 210, 70) if evento_impulsiva["tipo"] == "ascendeu" else (255, 100, 60),
                })

            # Seleção instantânea sem alocação
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
            pausa_por_fuga_mouse = False
            tempo_fim_stun = estado_atual_ia.get('fim_stun', 0) if 'estado_atual_ia' in globals() else 0

            for event in pygame.event.get():
                Variaveis.atualizar_estado_mouse(event)
                Variaveis.processar_eventos_teleporte(event, cooldown_dash)
                if False and Variaveis.evento_deve_pausar_por_fuga_mouse(event):
                    pausa_por_fuga_mouse = True
                if event.type == pygame.QUIT:
                    running = False
                    _salvar_tudo_ao_sair()
                    rodando = False
                    pygame.quit()
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.SAIR)
                        raise CleanExit()
                    sys.exit(0)
                elif False:
                    pos_mouse = obter_pos_mouse_jogo()
                    px_centro = pos_x_personagem + largura_personagem // 2
                    py_centro = pos_y_personagem + altura_personagem // 2
                    angulo_disparo_preparado = calcular_angulo_disparo((px_centro, py_centro), pos_mouse)
                    disparo_preparando = True
                    disparo_frame_atual = 0
                    tempo_ultimo_frame_preparo_disparo = tempo_atual
                    direcao_atual = 'disp'
                    frame_atual = 0
                elif not pausa_por_fuga_mouse and Variaveis.verificar_evento_input(event, "Habilidade Onda") and tempo_atual - tempo_ultimo_uso_habilidade >= cooldown_habilidade * lacerante_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) and tempo_atual >= tempo_fim_stun:
                    pos_mouse = obter_pos_mouse_jogo()
                    px_centro = pos_x_personagem + largura_personagem // 2
                    py_centro = pos_y_personagem + altura_personagem // 2
                    angulo = calcular_angulo_disparo((px_centro, py_centro), pos_mouse)
                    if lacerante_manifestacao.ativa(manifestacao_ativa):
                        ondas.append(lacerante_manifestacao.criar_fenda(px_centro, py_centro, angulo, tempo_atual, dano_person_hit))
                    else:
                        nova_onda = {
                            "rect": pygame.Rect(px_centro - largura_onda // 2, py_centro - altura_onda // 2, largura_onda, altura_onda),
                            "angulo": angulo,
                            "tempo_inicio": pygame.time.get_ticks(),
                            "frame_atual": 0,
                            "frames": frames_onda_cinetica
                        }
                        ondas.append(nova_onda)
                        aplicar_coice_onda(coice_onda, angulo)
                    tempo_ultimo_uso_habilidade = tempo_atual
                elif not pausa_por_fuga_mouse and Variaveis.verificar_evento_input(event, "Habilidade Onda") and tempo_atual >= tempo_fim_stun:
                    pos_mouse = obter_pos_mouse_jogo()
                    px_centro = pos_x_personagem + largura_personagem // 2
                    py_centro = pos_y_personagem + altura_personagem // 2
                    angulo = calcular_angulo_disparo((px_centro, py_centro), pos_mouse)
                    Variaveis.emitir_feedback_onda_cooldown(
                        ondas,
                        efeitos_texto,
                        pos_x_personagem,
                        pos_y_personagem,
                        largura_personagem,
                        altura_personagem,
                        angulo,
                        largura_onda,
                        altura_onda,
                        tempo_atual,
                    )

            if not pausa_por_fuga_mouse and botao_mouse[0] and not disparo_preparando and tempo_atual - tempo_ultimo_disparo >= intervalo_disparo_racional(intervalo_disparo, aurea, racional_dilatacao_fim, tempo_atual) and tempo_atual >= tempo_fim_stun:
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


            # Joystick já inicializado antes do loop (cache)

            # Chamar a função para atualizar a posição do personagem
            ultimo_x = pos_x_personagem
            ultimo_y = pos_y_personagem
            tempo_atual = pygame.time.get_ticks()
            delta_time_ms = tempo_atual - tempo_ultimo_frame
            tempo_ultimo_frame = tempo_atual
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



            tempo_passado += relogio.get_rawtime()
            relogio.tick()

             # Adicionar inimigos a cada 10 segundos
            tempo_atual = pygame.time.get_ticks()

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
                    Disparo_Geo.play()
                    disparos.append(lacerante_manifestacao.criar_auto_attack(manifestacao_ativa, vfx_disparo_player,
                        px_centro, py_centro, largura_disparo, altura_disparo,
                        angulo_disparo_preparado, velocidade_disparo, tempo_atual, impulsiva_ativa
                    ))
                    tempo_ultimo_disparo = tempo_atual
                    disparo_preparando = False
                    disparo_frame_atual = 0


            tela.fill((255, 255, 255))
            if em_transicao_mapa:
                # 1. Desenha o mapa novo ao fundo (ele é o que será revelado)
                tela.blit(mapa_novo, (0, 0))

                # 2. Criamos uma máscara de "furos" para este frame (Otimizado: Zero Allocation via cache)
                if not '_mascara_furos_cache' in locals():
                    _mascara_furos_cache = pygame.Surface((largura_mapa, altura_mapa), pygame.SRCALPHA)
                mascara_furos = _mascara_furos_cache
                mascara_furos.fill((0, 0, 0, 0))

                for p in particulas_pulso:
                    p['x'] += p['vx']
                    p['y'] += p['vy']
                    # Desenha furos na máscara (cor preta com alfa total para o SUB funcionar)
                    pygame.draw.circle(mascara_furos, (0, 0, 0, 255), (int(p['x']), int(p['y'])), int(p['tamanho']))

                    # Opcional: poeira visual brilhante nas bordas
                    pygame.draw.circle(tela, (200, 230, 255, 150), (int(p['x']), int(p['y'])), 2)

                # 3. Aplicamos os furos no mapa antigo (Erosão)
                # Importante: blitamos a máscara no mapa antigo usando subtração de alfa
                mapa_antigo.blit(mascara_furos, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

                # 4. Desenha o mapa antigo (agora com buracos) por cima do novo
                tela.blit(mapa_antigo, (0, 0))

                # 5. Finaliza quando o tempo passar ou partículas saírem da tela
                if pygame.time.get_ticks() - inicio_transicao_mapa > 3500: # 3.5 segundos de pura estética
                    mapa = mapa_novo
                    em_transicao_mapa = False
            else:
                # Desenho normal
                tela.blit(mapa, (0, 0))



            novas_ondas = []
            for onda in ondas:
                if onda.get("tipo_manifestacao") == "fenda_lacerante":
                    lacerante_manifestacao.desenhar_fenda(tela, onda, tempo_atual)
                    boss_info_fenda = {
                        "vivo": bool(luta_iniciada and vida_umbra > 0),
                        "rect": hitbox_boss5 if luta_iniciada else None,
                        "hit_flag": False,
                    }
                    lacerante_manifestacao.processar_fenda(onda, [], boss_info_fenda, tempo_atual)
                    if boss_info_fenda.get("hit_flag") and vida_umbra > 0:
                        dano_final = float(onda.get("dano", dano_person_hit * 4 * fator_dano_aureas()))
                        if estado_atual_ia.get("parede_ativa"):
                            dano_final *= 0.75
                        if "resistencia_umbra" in globals() and resistencia_umbra > 0:
                            dano_final *= max(0.1, 1.0 - (resistencia_umbra / 100.0))
                        if estado_atual_ia.get("dimensao_ativa") == "atrito":
                            dano_final *= 0.3
                            if not estado_atual_ia.get("laser_ativo"):
                                estado_atual_ia["carga_atrito"] = estado_atual_ia.get("carga_atrito", 0) + 12
                        dano_final = dano_boss_mitigado(dano_final, 5, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                        vida_umbra -= dano_final
                        estado_atual_ia["dano_recente"] = estado_atual_ia.get("dano_recente", 0) + dano_final
                        efeitos_texto.append({
                            "texto": f"-{int(dano_final)}",
                            "x": hitbox_boss5.centerx + random.randint(-20, 20),
                            "y": hitbox_boss5.top - 10,
                            "tempo_inicio": tempo_atual,
                            "cor": lacerante_manifestacao.COR_LACERANTE_CLARA,
                        })
                        criar_particulas_explosao(tela, hitbox_boss5.centerx, hitbox_boss5.centery)
                    if tempo_atual < int(onda.get("fim_ms", 0)):
                        novas_ondas.append(onda)
                    continue

                if "pos_x" not in onda:
                    onda["pos_x"] = float(onda["rect"].x)
                if "pos_y" not in onda:
                    onda["pos_y"] = float(onda["rect"].y)
                distancia_passo = velocidade_onda * dt
                if onda.get("falha_cooldown"):
                    distancia_restante = max(
                        0.0,
                        float(onda.get("distancia_maxima", 10.0)) - float(onda.get("distancia_percorrida", 0.0)),
                    )
                    distancia_passo = min(distancia_passo, distancia_restante)
                onda["pos_x"] += distancia_passo * math.cos(onda["angulo"])
                onda["pos_y"] += distancia_passo * math.sin(onda["angulo"])
                if onda.get("falha_cooldown"):
                    onda["distancia_percorrida"] = float(onda.get("distancia_percorrida", 0.0)) + abs(distancia_passo)
                onda["rect"].x = int(onda["pos_x"])
                onda["rect"].y = int(onda["pos_y"])

                # Renderizar a onda proceduralmente
                desenhar_onda(tela, onda)

                if onda.get("falha_cooldown"):
                    if onda["distancia_percorrida"] >= float(onda.get("distancia_maxima", 10.0)):
                        criar_particulas_explosao(tela, onda["rect"].centerx, onda["rect"].centery)
                    else:
                        novas_ondas.append(onda)
                    continue

                colidiu = False
                if luta_iniciada and onda["rect"].colliderect(hitbox_boss5):
                    # O dano final da onda no boss
                    dano_final = dano_person_hit * 4 * fator_dano_aureas()
                    
                    if estado_atual_ia.get("parede_ativa"):
                        dano_final *= 0.75
                    if "resistencia_umbra" in globals() and resistencia_umbra > 0:
                        dano_final *= max(0.1, 1.0 - (resistencia_umbra / 100.0))
                    if estado_atual_ia.get("dimensao_ativa") == "atrito":
                        dano_final *= 0.3
                        if not estado_atual_ia.get("laser_ativo"):
                            estado_atual_ia["carga_atrito"] = estado_atual_ia.get("carga_atrito", 0) + 12
                            if estado_atual_ia["carga_atrito"] >= 100:
                                estado_atual_ia["laser_ativo"] = {
                                    "tempo_inicio":          tempo_atual,
                                    "fase":                  "carregando",
                                    "rodada":                1,
                                    "duracao_carga":         1500,
                                    "duracao_disparo":       4000,
                                    "angulo_base_inicio":    random.uniform(0, math.pi * 2)
                                }
                                estado_atual_ia["carga_atrito"] = 0
                                
                    if vida_umbra > 0:
                        dano_final = dano_boss_mitigado(dano_final, 5, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                        vida_umbra -= dano_final
                        estado_atual_ia["dano_recente"] = estado_atual_ia.get("dano_recente", 0) + dano_final
                        
                        # VFX de Desfragmentação de Impacto
                        # Impacto visual (simplificado)
                        
                        punicao = -4.0
                        if tempo_atual - estado_atual_ia.get("chegada_teleporte", 0) < 1500:
                            punicao -= 10.0
                        memoria_umbra.treinar(punicao, prioridade=True)
                        
                        if quantidade_roubo_vida > 0:
                            cura_base = (vida_maxima - vida) * quantidade_roubo_vida
                            if player_hemorragia_ativa and tempo_atual < tempo_fim_hemorragia:
                                cura_base *= (1.0 - penalidade_cura_percentual)
                            vida = min(vida_maxima, vida + cura_base)
                            
                        if inicio_transicao_mapa == 0 or (tempo_atual - inicio_transicao_mapa) >= 8000:
                            trauma_umbra_acumulado += dano_final
                            
                    criar_particulas_explosao(tela, onda["rect"].centerx, onda["rect"].centery)
                    colidiu = True

                if not colidiu:
                    if 0 <= onda["rect"].x < largura_mapa and 0 <= onda["rect"].y < altura_mapa:
                        novas_ondas.append(onda)

            ondas = novas_ondas

            if imune_tempo_restante > 0:
                imune_tempo_restante -= relogio.get_time()  
            else:
                imune_tempo_restante = 0 




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
                        som_morte=locals().get('Dano_person', globals().get('Dano_person', None)),
                        mapa=mapa
                    )
                    pass
                    limpar_salvamento()
                    _salvar_tudo_ao_sair()
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.GAME_OVER, dados={'vitoria': False})
                        raise CleanExit()
                    else:
                        _salvar_tudo_ao_sair()
                        pygame.quit()
                        sys.exit(0)

            # Adicione esta verificação para controlar o piscar da barra de vida
            if piscando_vida:
                if False: # Desativado para o HUD widescreen
                    if tempo_atual % 500 < 250:  # Altere o valor 500 e 250 conforme necessário
                        # Desenha a barra de vida piscando em vermelho
                        pygame.draw.rect(tela, (255, 0, 0), (posicao_barra_vida[0], posicao_barra_vida[1], largura_barra_vida, altura_barra_vida))
                    else:
                        # Desenha a barra de vida normalmente
                        pygame.draw.rect(tela, verde, (posicao_barra_vida[0], posicao_barra_vida[1], (vida / vida_maxima) * largura_barra_vida, altura_barra_vida))



            if 'historico_player' not in locals():
                historico_player = []
            historico_player.append((pos_x_personagem, pos_y_personagem))
            if len(historico_player) > 60:
                historico_player.pop(0)

            if len(historico_player) >= 2:
                vetor_x = historico_player[-1][0] - historico_player[-2][0]
                vetor_y = historico_player[-1][1] - historico_player[-2][1]
                memoria_umbra.registrar_esquiva_player(vetor_x, vetor_y)
            personagem_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)


            ###############################################   DESENHA O BOSS NA TELA ################################
            if boss_final_ativo:

                agora = pygame.time.get_ticks()
                if vida_umbra <= 0:
                    pass
                    _salvar_tudo_ao_sair()
                    from build_runtime import fase_disponivel
                    if fase_disponivel(6):
                        salvar_atributos()
                        try:
                            Musica_tema_fases.stop()
                            Som_tema_fases.stop()
                        except:
                            pass
                        if game_manager:
                            from game_manager import EstadoJogo
                            game_manager.mudar_estado(EstadoJogo.JOGO_FASE_6)
                            raise CleanExit()
                        else:
                            import GAME6
                            GAME6.executar_jogo()
                            raise CleanExit()
                    limpar_salvamento()
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.GAME_OVER, dados={'vitoria': True, 'pontuacao': pontuacao})
                        raise CleanExit()
                    else:
                        _salvar_tudo_ao_sair()
                        pygame.quit()
                        sys.exit(0)
                if 'tempo_start_boss' not in estado_atual_ia:
                    estado_atual_ia['tempo_start_boss'] = agora
                    estado_atual_ia['ultimo_ataque'] = agora
                    estado_atual_ia['ultimo_teleporte'] = agora
                    estado_atual_ia['ultimo_sifao'] = agora
                    estado_atual_ia['passiva_chance'] = 0.30
                    estado_atual_ia['passiva_reducao'] = 1.0
                    estado_atual_ia['intervalo'] = 1900

                luta_iniciada = (agora - estado_atual_ia['tempo_start_boss']) >= 2000
                ataque_liberado = (agora - estado_atual_ia['tempo_start_boss']) >= 3000

                # ============================================================================
                # SISTEMA DE RATOS DA UMBRA (APENAS DIMENSÃO 9)
                # ============================================================================
                if luta_iniciada and mapa_atual_path == "Sprites/Fase9.png":
                    # Calcular centro do Apolo para os ratos perseguirem
                    apolo_centro_x = pos_x_personagem + largura_personagem // 2
                    apolo_centro_y = pos_y_personagem + altura_personagem // 2

                    # Spawnar ratos automaticamente quando cooldown passar
                    if gerenciador_ratos.pode_spawnar(agora):
                        qtd_spawnada = gerenciador_ratos.spawnar_ratos(agora)
                        if qtd_spawnada > 0:
                            # Feedback visual de spawn
                            efeitos_texto.append({
                                "texto": f"RATOS INVOCADOS! ({qtd_spawnada})",
                                "x": largura_mapa // 2 - 100,
                                "y": 50,
                                "tempo_inicio": agora,
                                "cor": (255, 100, 255)
                            })

                    # Atualizar posição de todos os ratos
                    gerenciador_ratos.atualizar(agora, apolo_centro_x, apolo_centro_y)

                    # Verificar colisões com o Apolo
                    personagem_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, 
                                                 largura_personagem, altura_personagem)

                    resultado_colisoes = gerenciador_ratos.verificar_colisoes(
                        personagem_rect, 
                        vida_umbra, 
                        vida_maxima_umbra
                    )

                    # Aplicar dano ao Apolo e cura à Umbra
                    if resultado_colisoes['hits'] > 0:
                        aplicar_hit_jogador(resultado_colisoes['dano_total'], respeitar_resistencia=False)
                        vida_umbra = resultado_colisoes['vida_umbra_nova']

                        # Feedback visual de hit
                        for i in range(resultado_colisoes['hits']):
                            efeitos_texto.append({
                                "texto": f"-{gerenciador_ratos.dano_rato} RATO!",
                                "x": pos_x_personagem + random.randint(-20, 20),
                                "y": pos_y_personagem - 40 - (i * 20),
                                "tempo_inicio": agora,
                                "cor": (255, 50, 50)
                            })

                        # Feedback de cura da Umbra
                        efeitos_texto.append({
                            "texto": f"+{resultado_colisoes['cura_umbra']} SIFÃO",
                            "x": pos_x_umbra + largura_boss // 2,
                            "y": pos_y_umbra - 30,
                            "tempo_inicio": agora,
                            "cor": (0, 255, 150)
                        })

                        # Recompensa negativa para Apolo (foi atingido)
                        pass

                        # Recompensa positiva para Umbra (acertou o alvo)
                        memoria_umbra.treinar(20.0 * resultado_colisoes['hits'], prioridade=True)
                elif mapa_atual_path != "Sprites/Fase9.png":
                    # Se não está na Dimensão 9, limpa todos os ratos
                    if len(gerenciador_ratos.ratos) > 0:
                        gerenciador_ratos.ratos.clear()

                # ============================================================================

                # Criamos o dicionário que o 'processar_ia_umbra' espera
                boss_pos_ia = {
                    'x': pos_x_umbra,
                    'y': pos_y_umbra,
                    'hitbox_centro': hitbox_boss5.center if hitbox_boss5 is not None else (pos_x_umbra + largura_boss // 2, pos_y_umbra + altura_boss // 2)
                }
                player_pos_data = (pos_x_personagem, pos_y_personagem)
                dados_p = {
                    'vida_atual': vida_umbra,
                    'vida_max': vida_maxima_umbra,
                    'erros': erros_player_contagem,
                    'mapa_atual': mapa_atual_path,
                    'p_roubo_chance': roubo_de_vida,
                    'p_roubo_qtd': quantidade_roubo_vida,
                    'p_trembo': trembo,
                    'p_intervalo_disparo': intervalo_disparo,
                }
                # No exato frame em que a luta começa, resetamos os timers para o 'agora' atual
                if luta_iniciada and not estado_atual_ia.get('timers_sincronizados'):
                    estado_atual_ia['ultimo_ataque'] = agora
                    estado_atual_ia['ultimo_teleporte'] = agora
                    estado_atual_ia['ultimo_sifao'] = agora
                    estado_atual_ia['timers_sincronizados'] = True # Trava para não resetar mais

                # A cada segundo de sobrevivência, a IA recebe um pequeno incentivo
                if luta_iniciada:
                    if agora - estado_atual_ia.get('ultimo_reforço_positivo', 0) >= 1000:
                        memoria_umbra.treinar(0.1)
                        estado_atual_ia['ultimo_reforço_positivo'] = agora

                    # --- 2. CHAMADA DO CÉREBRO (O GRAFO) ---
                    if ataque_liberado:
                        # 1. Processamento da IA 
                        estado_atual_ia = hb.processar_ia_umbra(
                            agora, boss_pos_ia, player_pos_data, 
                            historico_player, disparos, estado_atual_ia, dados_p, memoria_umbra
                        )

                        # 2. MAPEAMENTO DA REDE NEURAL COMPLETA PARA O DASHBOARD
                        id_estado = estado_atual_ia.get('estado_composto', 'estavel_longe_calmo_linear')

                        # Capturamos todos os estados conhecidos para desenhar o grafo global
                        # (Limitamos aos 5 estados mais recentes para não poluir o visual)
                        mapa_neural = {"DQN": "Ativo"}

                        # 3. TRANSMISSÃO PARA O DASHBOARD
                        dados_ia_umbra = {
                            "estado_atual": id_estado,
                            "rede_completa": { id_estado: estado_atual_ia.get('ultimos_pesos_calculados', {}) }, 
                            "decisao_ativa": estado_atual_ia.get('decisoes_ativas', ["---"]),
                            "bias_bayesiano": memoria_umbra.calcular_bias_bayesiano(),
                            "estatisticas": dados_p
                        }
                    # --- 3. HIERARQUIA DE MOVIMENTAÇÃO ---
                    if estado_atual_ia.get('parede_ativa'):
                        if agora - estado_atual_ia.get('ultimo_tick_cura', 0) >= 600:
                            # Balanceado: reduzido de 0.049 para 0.015
                            valor_cura = (vida_maxima_umbra-vida_umbra) * 0.015
                            memoria_umbra.treinar(1.5)
                            # A cura não pode ultrapassar o limite máximo
                            vida_umbra = min(vida_maxima_umbra, vida_umbra + valor_cura)

                            efeitos_texto.append({
                                "texto": f"+{int(valor_cura)}",
                                "x": hitbox_boss5.centerx + random.randint(-30, 30),
                                "y": hitbox_boss5.top - 30,
                                "tempo_inicio": agora,
                                "cor": (0, 255, 150) # Esmeralda Visionário
                            })
                            estado_atual_ia['ultimo_tick_cura'] = agora

                    # --- RENDERIZAÇÃO E FÍSICA DO VÓRTICE TEMPORAL (FASE 1) ---
                    vortice = estado_atual_ia.get('vortice_ativo')
                    if vortice:
                        tempo_vortice = agora - vortice['tempo_inicio']
                        if tempo_vortice < vortice['duracao']:
                            # Telegraph / Warning phase: primeiros 1500ms
                            if tempo_vortice < 1500:
                                # Aviso visual no chão (não aplica atração nem dano)
                                raio_aviso = 150
                                progresso = tempo_vortice / 1500.0
                                s_aviso = pygame.Surface((raio_aviso * 2, raio_aviso * 2), pygame.SRCALPHA)
                                alpha_aviso = int(50 + math.sin(agora * 0.01) * 30)
                                pygame.draw.circle(s_aviso, (138, 43, 226, alpha_aviso), (raio_aviso, raio_aviso), raio_aviso)
                                pygame.draw.circle(s_aviso, (255, 0, 128, 200), (raio_aviso, raio_aviso), raio_aviso, 3)
                                # Anel de contração
                                raio_contraido = int(raio_aviso * (1.0 - progresso))
                                if raio_contraido > 0:
                                    pygame.draw.circle(s_aviso, (255, 255, 255, 220), (raio_aviso, raio_aviso), raio_contraido, 2)
                                tela.blit(s_aviso, (vortice['x'] - raio_aviso, vortice['y'] - raio_aviso))
                            else:
                                # Lógica ativa de atração vetorial e punição física
                                dx_v = vortice['x'] - pos_x_personagem
                                dy_v = vortice['y'] - pos_y_personagem
                                dist_v = math.hypot(dx_v, dy_v)

                                if dist_v > 5:
                                    fator_succao = vortice['forca'] * (1 - min(1, dist_v / 900))
                                    pos_x_personagem += (dx_v / dist_v) * fator_succao
                                    pos_y_personagem += (dy_v / dist_v) * fator_succao

                                    # --- PUNIÇÃO APOLO: Sendo sugado para o centro ---
                                    if dist_v < 150 and agora % 200 < 30:
                                        pass

                                    # Trava de colisão com os limites do mapa
                                    pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem))
                                    pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem))

                                # Renderizacao animada da Singularidade — frames pre-escalados
                                if not hasattr(desenhar_sombra, '_frames_v_scaled') or \
                                        len(desenhar_sombra._frames_v_scaled) != len(frames_vortex):
                                    desenhar_sombra._frames_v_scaled = [
                                        pygame.transform.scale(f, (160, 160)) for f in frames_vortex
                                    ]
                                frame_v = desenhar_sombra._frames_v_scaled[(agora // 150) % len(frames_vortex)]
                                tela.blit(frame_v, (vortice['x'] - 80, vortice['y'] - 80))
                        else:
                            estado_atual_ia['vortice_ativo'] = None

                    # --- RENDERIZAÇÃO E FÍSICA DA PRISÃO CRIOGÊNICA (FASE 2) ---
                    prisao = estado_atual_ia.get('prisao_ativa')
                    if prisao:
                        tempo_prisao = agora - prisao['tempo_inicio']
                        if tempo_prisao < prisao['duracao']:
                            # Telegraph / Warning phase: primeiros 1500ms
                            if tempo_prisao < 1500:
                                # Aviso visual no chão (sem lentidão nem dano)
                                raio_aviso = 180
                                progresso = tempo_prisao / 1500.0
                                s_aviso = pygame.Surface((raio_aviso * 2, raio_aviso * 2), pygame.SRCALPHA)
                                alpha_aviso = int(60 + math.sin(agora * 0.015) * 40)
                                pygame.draw.circle(s_aviso, (0, 120, 255, alpha_aviso), (raio_aviso, raio_aviso), raio_aviso)
                                pygame.draw.circle(s_aviso, (0, 255, 255, 220), (raio_aviso, raio_aviso), raio_aviso, 3)
                                # Anel de contração
                                raio_contraido = int(raio_aviso * (1.0 - progresso))
                                if raio_contraido > 0:
                                    pygame.draw.circle(s_aviso, (255, 255, 255, 240), (raio_aviso, raio_aviso), raio_contraido, 2)
                                
                                # Flocos de neve flutuantes suaves na área de aviso
                                random.seed(prisao['tempo_inicio'])
                                for i in range(12):
                                    r_o = random.uniform(10, raio_aviso - 10)
                                    a_o = random.uniform(0, math.pi * 2)
                                    px_s = raio_aviso + r_o * math.cos(a_o)
                                    py_s = raio_aviso + r_o * math.sin(a_o)
                                    s_aviso.blit(_CRISTAL_SURF, (int(px_s) - 3, int(py_s) - 3))
                                random.seed()
                                
                                tela.blit(s_aviso, (prisao['x'] - raio_aviso, prisao['y'] - raio_aviso))
                                velocidade_personagem = velocidade_personagem_base
                            else:
                                # 1. Dinamica de Pulsacao e Crescimento da Zona
                                raio_hitbox_base = 45
                                aumento_pulso = int(abs(math.sin(agora * 0.001)) * 180)
                                raio_hitbox_atual = raio_hitbox_base + aumento_pulso

                                tamanho_vortice = (raio_hitbox_atual * 2) + 40
                                centro_v_x, centro_v_y = tamanho_vortice // 2, tamanho_vortice // 2

                                # Cache da Surface: quantiza raio a cada 8px para reutilizar surface
                                raio_q = (raio_hitbox_atual // 8) * 8
                                if raio_q not in _VORTICE_SURF_CACHE:
                                    _sv = pygame.Surface((tamanho_vortice, tamanho_vortice), pygame.SRCALPHA)
                                    _VORTICE_SURF_CACHE.clear()           # nao acumular dezenas de sizes
                                    _VORTICE_SURF_CACHE[raio_q] = _sv
                                superficie_vortice = _VORTICE_SURF_CACHE[raio_q]
                                superficie_vortice.fill((0, 0, 0, 0))    # limpa para redesenhar

                                # 2. Nucleo Energetico Pulsante
                                raio_nucleo = (raio_hitbox_atual * 0.6) + int(math.sin(agora * 0.008) * 8)
                                alfa_nucleo = 110 + int(math.sin(agora * 0.008) * 40)
                                cores_nucleo = [
                                    ((0, 80, 255, alfa_nucleo), raio_nucleo),
                                    ((0, 160, 255, alfa_nucleo + 20), raio_nucleo * 0.7),
                                    ((150, 240, 255, alfa_nucleo + 40), raio_nucleo * 0.3)
                                ]
                                for cor, raio in cores_nucleo:
                                    pygame.draw.circle(superficie_vortice, cor, (centro_v_x, centro_v_y), max(1, int(raio)))

                                # 3. Anel Externo Congelante — 20 segmentos (era 40, mesmo visual a 60fps)
                                num_segmentos = 20
                                angulo_base = agora * 0.002
                                step_ang = math.pi * 2 / num_segmentos
                                for i in range(num_segmentos):
                                    ang = angulo_base + i * step_ang
                                    r_ext = raio_hitbox_atual + random.uniform(-4, 4)
                                    px_s = centro_v_x + r_ext * math.cos(ang)
                                    py_s = centro_v_y + r_ext * math.sin(ang)
                                    pygame.draw.circle(superficie_vortice, (200, 250, 255, 180), (int(px_s), int(py_s)), 3)

                                # 4. Tempestade de Flocos e Cristais — 35 particulas (era 70)
                                random.seed(prisao['tempo_inicio'])
                                num_particulas = 35
                                velocidade_tempestade = -(agora * 0.005)
                                for i in range(num_particulas):
                                    raio_orbita = random.uniform(15, raio_hitbox_atual)
                                    angulo_offset = random.uniform(0, math.pi * 2)
                                    usa_floco = random.randint(0, 2) == 0   # 1/3 floco, 2/3 cristal
                                    ang_final = velocidade_tempestade + angulo_offset
                                    px_s = centro_v_x + raio_orbita * math.cos(ang_final)
                                    py_s = centro_v_y + raio_orbita * math.sin(ang_final)
                                    if usa_floco:
                                        superficie_vortice.blit(_FLOCO_SURF, (int(px_s) - 2, int(py_s) - 2))
                                    else:
                                        superficie_vortice.blit(_CRISTAL_SURF, (int(px_s) - 3, int(py_s) - 3))
                                random.seed()

                                # 5. Aplicacao Visceral no Ecra
                                tela.blit(superficie_vortice, (prisao['x'] - centro_v_x, prisao['y'] - centro_v_y))

                                # 6. Detecção de Punição Física (Hitbox Dinâmica)
                                dist_p = math.hypot(prisao['x'] - personagem_rect.centerx, prisao['y'] - personagem_rect.centery)
                                if dist_p < raio_hitbox_atual: 
                                    velocidade_personagem = 0.3 

                                    # --- PUNIÇÃO APOLO: Ficar preso no gelo (lentidão) ---
                                    if agora % 100 < 20: 
                                        pass

                                    if agora % 1000 < 50:
                                        efeitos_texto.append({
                                            "texto": "ZERO ABSOLUTO!",
                                            "x": pos_x_personagem,
                                            "y": pos_y_personagem - 30,
                                            "tempo_inicio": agora,
                                            "cor": (0, 255, 255)
                                        })
                                else:
                                    velocidade_personagem = velocidade_personagem_base
                        else:
                            estado_atual_ia['prisao_ativa'] = None
                            velocidade_personagem = velocidade_personagem_base
                    else:
                        velocidade_personagem = velocidade_personagem_base

                    if estado_atual_ia.get('fase_tele') == "projetil_viajando":
                        sinal = estado_atual_ia.get('proj_tele')
                        if sinal:
                            # A. Movimentação do Sinalizador
                            dx_sinal = sinal['velocidade'] * math.cos(sinal['angulo']) * dt
                            dy_sinal = sinal['velocidade'] * math.sin(sinal['angulo']) * dt
                            sinal['x'] += dx_sinal
                            sinal['y'] += dy_sinal
                            sinal['dist_percorrida'] += math.hypot(dx_sinal, dy_sinal)
                            memoria_umbra.treinar(0.5)

                            # B. Renderização da Orbe do Sinalizador (Verde/Azul)
                            cor_sinal = sinal.get('cor_sinal', (0, 255, 150))
                            pygame.draw.circle(tela, (100, 255, 200), (int(sinal['x']), int(sinal['y'])), 8)
                            pygame.draw.circle(tela, cor_sinal, (int(sinal['x']), int(sinal['y'])), 15, 2)

                            # C. O INÍCIO DA FENDA (Quando a orbe chega)
                            if sinal['dist_percorrida'] >= sinal['dist_total']:
                                estado_atual_ia['fase_tele'] = "portal_abrindo"
                                sinal['tempo_chegada'] = agora

                    elif estado_atual_ia.get('fase_tele') == "portal_abrindo":
                        sinal = estado_atual_ia.get('proj_tele')
                        if sinal:
                            tx, ty = sinal['target_pos'][0], sinal['target_pos'][1]
                            renderizar_portal_teleporte_umbra(tela, agora, tx, ty, config_graficos)

                            # Inteligência Analítica do Juke: Mapear se Apolo atirou no portal
                            tiros_no_portal_agora = 0
                            for d in disparos:
                                if math.hypot(d["rect"].centerx - tx, d["rect"].centery - ty) < 80:
                                    tiros_no_portal_agora += 1
                            sinal['engano_jogador'] = sinal.get('engano_jogador', 0) + tiros_no_portal_agora

                            # Detecção de Farsa Quebrada (Surra durante Falso Teleporte)
                            if sinal.get('tipo') == 'falso' and estado_atual_ia.get('dano_recente', 0) > 0:
                                sinal['tipo'] = 'real' # Aborta o blefe, entra em desespero e foge pelo portal!
                                memoria_umbra.treinar(-20.0) # Punição por falhar no blefe

                            if agora - sinal.get('tempo_chegada', agora) >= 450:
                                if sinal.get('tipo', 'real') == 'falso':
                                    # CONCLUSÃO DO JUKE!
                                    if sinal.get('engano_jogador', 0) > 0:
                                        memoria_umbra.treinar(15.0 * sinal['engano_jogador']) # Recompensa maciça por trollar
                                    estado_atual_ia['fase_tele'] = "espera"
                                    estado_atual_ia['proj_tele'] = None

                                else:
                                    # O SALTO REAL DEFINITIVO
                                    pos_x_umbra = tx
                                    pos_y_umbra = ty

                                    # Efeito visual de entrada ao chegar
                                    # Impacto visual (simplificado)
                                    Som_portal.play()

                                    estado_atual_ia['chegada_teleporte'] = agora # Timestamp de vulnerabilidade!
                                    estado_atual_ia['fase_tele'] = "espera"
                                    estado_atual_ia['proj_tele'] = None
                                    estado_atual_ia['dano_recente'] = 0 

                    else:
                        # SÓ SE MOVE NORMALMENTE SE NÃO ESTIVER TELEPORTANDO
                        nova_pos, estado_mental = hb.movimentacao_inteligente_umbra(
                            agora, 
                            (pos_x_umbra, pos_y_umbra),
                            player_pos_data, 
                            disparos, 
                            estado_atual_ia, 
                            dados_p,
                            memoria_umbra,
                            historico_player
                        )
                        pos_x_umbra, pos_y_umbra = nova_pos[0], nova_pos[1]
                        pos_x_umbra = max(espacamento, min(largura_mapa - largura_boss - espacamento, pos_x_umbra))
                        pos_y_umbra = max(espacamento, min(altura_mapa - altura_boss - espacamento, pos_y_umbra))

                    # --- 4. DINÂMICA VISUAL, ANIMAÇÃO E HITBOX ---
                    offset_y_boss = math.sin(agora * 0.005) * 7
                    direcao_boss = 'stop'

                    tempo_passado_boss += relogio.get_time()
                    if tempo_passado_boss >= tempo_animacao_stop:
                        tempo_passado_boss = 0
                        frame_boss = (frame_boss + 1) % len(frames_geo_umbra_paths[direcao_boss])

                    img_atual_boss = frames_geo_umbra_paths[direcao_boss][frame_boss]

                    # Inversão horizontal e ajuste de Hitbox
                    if pos_x_personagem < pos_x_umbra:
                        img_atual_boss = pygame.transform.flip(img_atual_boss, True, False)
                        hitbox_x = pos_x_umbra
                    else:
                        hitbox_x = pos_x_umbra + 30

                    hitbox_boss5 = pygame.Rect(hitbox_x, pos_y_umbra + offset_y_boss, largura_boss - 30, altura_boss)
                    # Desenhar sombra do boss
                    desenhar_sombra(tela, pos_x_umbra, pos_y_umbra + offset_y_boss, largura_boss, altura_boss, offset_y=10)
                    tela.blit(img_atual_boss, (pos_x_umbra, pos_y_umbra + offset_y_boss))

                    # Desenhar ratos (APÓS o boss, ANTES da barra de vida)
                    gerenciador_ratos.desenhar(tela, agora)

                    # --- 5. BARRA DE VIDA E PROJÉTEIS ---
                    largura_barra = largura_boss * 0.8
                    barra_x = pos_x_umbra + (largura_boss - largura_barra) // 2
                    barra_y = pos_y_umbra + offset_y_boss - 15
                    vida_percent = max(0, vida_umbra) / vida_maxima_umbra
                    projeteis_vivos = []

                    for p in estado_atual_ia.get('projeteis', []):
                        # Movimentação baseada no ângulo definido pela IA
                        if "pos_x" not in p:
                            p["pos_x"] = float(p["rect"].x)
                        if "pos_y" not in p:
                            p["pos_y"] = float(p["rect"].y)
                        p["pos_x"] += p["velocidade"] * math.cos(p["angulo"]) * dt
                        p["pos_y"] += p["velocidade"] * math.sin(p["angulo"]) * dt
                        p["rect"].x = int(p["pos_x"])
                        p["rect"].y = int(p["pos_y"])

                        # Verificação de fronteiras (Limites do Mapa)
                        if 0 < p["rect"].x < largura_mapa and 0 < p["rect"].y < altura_mapa:
                            projeteis_vivos.append(p)

                            # A renderização agora é processada pelo MOTOR DE VFX PROCEDURAL abaixo
                            pass 
                        else:
                            memoria_umbra.treinar(-0.5)
                            estado_atual_ia['passiva_chance'] = 0.30
                            estado_atual_ia['passiva_reducao'] = 1.0
                            estado_atual_ia['intervalo'] = 1900

                    estado_atual_ia['projeteis'] = projeteis_vivos

                    # --- 2. MOTOR DE VFX PROCEDURAL (PLASMA & PARTÍCULAS) ---
                    hb.renderizar_vfx_umbra(tela, agora, estado_atual_ia)

                    # --- 3. DETECÇÃO DE DANO NO JOGADOR ---
                    hitbox_player = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
                    for p in estado_atual_ia['projeteis'][:]:
                        if p["rect"].colliderect(hitbox_player):
                            # Aciona VFX de Desfragmentação Elite no Impacto
                            cor_frag = (138, 43, 226) if p.get('tipo') == 'furia' else (0, 191, 255)
                            hb.gerar_burst_desfragmentacao(p["rect"].centerx, p["rect"].centery, estado_atual_ia, cor_frag)

                            dano_bruto = (200 + (inimigos_eliminados *0.05)) * multiplicador_dano_umbra * 1.5
                            dano_recebido = int(dano_bruto - Resistencia)

                            if dano_recebido < 0: 
                                dano_recebido = 0

                            aplicar_hit_jogador(dano_recebido, respeitar_resistencia=False)

                            memoria_umbra.treinar(3.0, prioridade=True)

                            chance_atual = estado_atual_ia.get('passiva_chance', 0.50)
                            if random.random() <= chance_atual:
                                reducao_atual = estado_atual_ia.get('passiva_reducao', 1.0)
                                nova_reducao = max(0.2, reducao_atual - 0.35) 

                                estado_atual_ia['passiva_reducao'] = nova_reducao
                                estado_atual_ia['passiva_chance'] = min(1.0, chance_atual + 0.15)
                                estado_atual_ia['intervalo'] = int(1900 * nova_reducao)

                                efeitos_texto.append({
                                    "texto": "ACELERAÇÃO UMBRAL!",
                                    "x": pos_x_personagem,
                                    "y": pos_y_personagem - 50,
                                    "tempo_inicio": agora,
                                    "cor": (138, 43, 226)
                                })

                            if p in estado_atual_ia['projeteis']:
                                estado_atual_ia['projeteis'].remove(p)

                    miasma = estado_atual_ia.get('miasma_ativo')
                    if miasma:
                        tempo_miasma = agora - miasma['tempo_inicio']
                        if tempo_miasma < miasma['duracao']:

                            if agora % 1000 < 50: 
                                aplicar_hit_jogador(vida_maxima * 0.01, respeitar_resistencia=False, ativar_vanguarda=False)
                                # --- PUNIÇÃO APOLO: Dano por cegueira/miasma ---
                                pass

                            centro_ceg_x = pos_x_personagem + (largura_personagem // 2)
                            centro_ceg_y = pos_y_personagem + (altura_personagem // 2)

                            tela.blit(img_cegueira, (centro_ceg_x - (largura_mascara // 2), centro_ceg_y - (altura_mascara // 2)))
                        else:
                            estado_atual_ia['miasma_ativo'] = None

                    # --- RENDERIZAÇÃO E FÍSICA DA TEMPESTADE ELÉTRICA (FASE 4) ---
                    descarga = estado_atual_ia.get('descarga_eletrica')
                    if descarga:
                        tempo_decorrido = agora - descarga['tempo_inicio']
                        if tempo_decorrido < descarga['duracao']:
                            origem = (descarga['x'], descarga['y'])
                            raio_max = descarga['raio_maximo']
                            abertura = descarga['abertura']
                            angulo_base = descarga['angulo_base']

                            qtd_raios = 6 + int(math.sin(agora * 0.05) * 3)

                            for _ in range(qtd_raios):
                                ponto_atual = origem
                                angulo_raio = angulo_base + random.uniform(-abertura/2, abertura/2)
                                distancia = 0

                                while distancia < raio_max:
                                    passo = random.uniform(25, 60)
                                    distancia += passo
                                    var_ang = random.uniform(-0.5, 0.5)

                                    prox_x = ponto_atual[0] + math.cos(angulo_raio + var_ang) * passo
                                    prox_y = ponto_atual[1] + math.sin(angulo_raio + var_ang) * passo
                                    prox_ponto = (prox_x, prox_y)

                                    cor = random.choice([(255, 255, 0), (138, 43, 226), (255, 255, 255)])
                                    espessura = random.randint(2, 7)
                                    pygame.draw.line(tela, cor, ponto_atual, prox_ponto, espessura)

                                    if random.random() > 0.65:
                                        ram_ang = angulo_raio + random.choice([-0.8, 0.8])
                                        ram_x = prox_x + math.cos(ram_ang) * passo * 0.7
                                        ram_y = prox_y + math.sin(ram_ang) * passo * 0.7
                                        pygame.draw.line(tela, cor, prox_ponto, (ram_x, ram_y), max(1, espessura - 2))

                                    ponto_atual = prox_ponto

                            dist_player = math.hypot(personagem_rect.centerx - origem[0], personagem_rect.centery - origem[1])
                            ang_player = math.atan2(personagem_rect.centery - origem[1], personagem_rect.centerx - origem[0])

                            diff_ang = (ang_player - angulo_base + math.pi) % (2 * math.pi) - math.pi

                            if dist_player <= raio_max and abs(diff_ang) <= abertura / 2:
                                if agora % 100 < 40:
                                    aplicar_hit_jogador(descarga['dano_por_tick'], respeitar_resistencia=False)
                                    efeitos_texto.append({
                                        "texto": "SOBRECARGA!",
                                        "x": pos_x_personagem + random.randint(-20, 20),
                                        "y": pos_y_personagem - 30,
                                        "tempo_inicio": agora,
                                        "cor": (255, 255, 0)
                                    })
                                    memoria_umbra.treinar(2.0)

                                    # --- PUNIÇÃO APOLO: Choque e atordoamento ---
                                    pass

                                estado_atual_ia['fim_stun'] = agora + 600 
                        else:
                            estado_atual_ia['descarga_eletrica'] = None

                    if agora < estado_atual_ia.get('fim_stun', 0):
                        velocidade_personagem = 0
                        for _ in range(5):
                            fx = pos_x_personagem + random.randint(0, int(largura_personagem))
                            fy = pos_y_personagem + random.randint(0, int(altura_personagem))
                            pygame.draw.circle(tela, random.choice([(255, 255, 0), (138, 43, 226)]), (int(fx), int(fy)), random.randint(2, 6))
                    elif not estado_atual_ia.get('prisao_ativa'):
                        velocidade_personagem = velocidade_personagem_base

                    # --- RENDERIZAÇÃO E FÍSICA DO CAMINHO DE ESPINHOS (FASE 6) ---
                    caminho = estado_atual_ia.get('caminho_espinhos')
                    if caminho:
                        tempo_decorrido = agora - caminho['tempo_inicio']
                        raios = caminho.get('raios', [])
                        largura_maxima = caminho['largura_maxima']

                        if caminho['fase'] == 'crescimento':
                            progresso = min(1.0, tempo_decorrido / caminho['duracao_crescimento'])
                            comp_frac = progresso
                            largura_atual = 10
                            if tempo_decorrido >= caminho['duracao_crescimento']:
                                caminho['fase'] = 'expansao'
                                caminho['tempo_inicio_expansao'] = agora

                        elif caminho['fase'] == 'expansao':
                            tempo_exp = agora - caminho['tempo_inicio_expansao']
                            progresso_exp = min(1.0, tempo_exp / caminho['duracao_expansao'])
                            comp_frac = 1.0
                            largura_atual = 10 + (largura_maxima - 10) * progresso_exp
                            if tempo_exp >= caminho['duracao_expansao']:
                                estado_atual_ia['caminho_espinhos'] = None
                                caminho = None
                        else:
                            comp_frac = 1.0
                            largura_atual = 10

                        if caminho:
                            hitou = False
                            for raio in raios:
                                origem = raio['origem']
                                angulo = raio['angulo']
                                comp_atual = raio['comprimento'] * comp_frac
                                fim_x = origem[0] + math.cos(angulo) * comp_atual
                                fim_y = origem[1] + math.sin(angulo) * comp_atual

                                # Renderização do raio
                                num_seg = max(2, int(comp_atual / 15))
                                pontos1, pontos2 = [], []
                                for i in range(num_seg + 1):
                                    dist = min(i * 15, comp_atual)
                                    bx_r = origem[0] + math.cos(angulo) * dist
                                    by_r = origem[1] + math.sin(angulo) * dist
                                    perp_x = math.cos(angulo + math.pi/2)
                                    perp_y = math.sin(angulo + math.pi/2)
                                    w1 = math.sin(i * 0.5 + agora * 0.003) * (largura_atual * 0.35)
                                    w2 = math.cos(i * 0.7 - agora * 0.002) * (largura_atual * 0.35)
                                    pontos1.append((bx_r + perp_x * w1, by_r + perp_y * w1))
                                    pontos2.append((bx_r + perp_x * w2, by_r + perp_y * w2))

                                if len(pontos1) > 1:
                                    for i in range(1, len(pontos1)):
                                        esp = max(2, int((largura_atual * 0.15) * (1.0 - i / num_seg)))
                                        pygame.draw.line(tela, (10, 20, 10), (int(pontos1[i-1][0]+2), int(pontos1[i-1][1]+2)), (int(pontos1[i][0]+2), int(pontos1[i][1]+2)), esp)
                                        pygame.draw.line(tela, (20, 60, 20), (int(pontos1[i-1][0]), int(pontos1[i-1][1])), (int(pontos1[i][0]), int(pontos1[i][1])), esp)
                                        pygame.draw.line(tela, (34, 90, 34), (int(pontos2[i-1][0]), int(pontos2[i-1][1])), (int(pontos2[i][0]), int(pontos2[i][1])), max(1, esp-1))
                                        hash_v = (i * 37) % 100
                                        if hash_v < 35 and caminho['fase'] == 'expansao':
                                            dir_e = 1 if hash_v < 17 else -1
                                            ang_e = angulo + (math.pi/2.5 * dir_e)
                                            tam_e = 8 + largura_atual * 0.15
                                            px_e = pontos1[i][0] + math.cos(ang_e) * tam_e
                                            py_e = pontos1[i][1] + math.sin(ang_e) * tam_e
                                            b1x = pontos1[i][0] + math.cos(ang_e + 1.2) * esp
                                            b1y = pontos1[i][1] + math.sin(ang_e + 1.2) * esp
                                            b2x = pontos1[i][0] + math.cos(ang_e - 1.2) * esp
                                            b2y = pontos1[i][1] + math.sin(ang_e - 1.2) * esp
                                            pygame.draw.polygon(tela, (180, 200, 120), [(px_e, py_e), (b1x, b1y), (b2x, b2y)])

                                # Colisão vetorial (apenas na expansão)
                                if caminho['fase'] == 'expansao' and not hitou:
                                    cx_p = personagem_rect.centerx
                                    cy_p = personagem_rect.centery
                                    vl_x = fim_x - origem[0]
                                    vl_y = fim_y - origem[1]
                                    vp_x = cx_p - origem[0]
                                    vp_y = cy_p - origem[1]
                                    len_sq = vl_x**2 + vl_y**2
                                    param = (vp_x*vl_x + vp_y*vl_y) / len_sq if len_sq > 0 else -1
                                    if 0 <= param <= 1:
                                        prox_x = origem[0] + param * vl_x
                                        prox_y = origem[1] + param * vl_y
                                        dist_linha = math.hypot(cx_p - prox_x, cy_p - prox_y)
                                        if dist_linha <= largura_atual / 2:
                                            hitou = True

                            if hitou and agora - caminho.get('ultimo_espinho_hit', 0) > 1000:
                                caminho['ultimo_espinho_hit'] = agora
                                estado_atual_ia['fim_stun'] = agora + 4000  # STUN 4 SEGUNDOS
                                aplicar_hit_jogador(50, respeitar_resistencia=False)
                                pass
                                # Umbra ganha 2 disparos rápidos
                                estado_atual_ia['bonus_tiros'] = estado_atual_ia.get('bonus_tiros', 0) + 2
                                efeitos_texto.append({'texto': 'ESPINHO! ATORDOADO!', 'x': pos_x_personagem, 'y': pos_y_personagem - 40, 'tempo_inicio': agora, 'cor': (180, 200, 120)})
                                memoria_umbra.treinar(8.0)


                    # --- RENDERIZAÇÃO E FÍSICA DO LASER DE SOBRECARGA (FASE 7) ---
                    laser = estado_atual_ia.get('laser_ativo')
                    if laser:

                        pos_x_umbra = (largura_mapa // 2) - (largura_boss // 2)
                        pos_y_umbra = (altura_mapa // 2) - (altura_boss // 2)

                        tempo_laser = agora - laser['tempo_inicio']
                        origem_laser = (pos_x_umbra + largura_boss // 2, pos_y_umbra + altura_boss // 2)
                        rodada = laser['rodada']

                        if laser['fase'] == 'carregando':
                            # Esfera condensando energia térmica (Cresce mais rápido nas últimas rodadas)
                            progresso_carga = min(1.0, tempo_laser / laser['duracao_carga'])
                            raio_esfera = progresso_carga * (50 + (rodada * 10))
                            pulso = abs(math.sin(agora * 0.01)) * 10

                            pygame.draw.circle(tela, (150, 0, 0), origem_laser, int(raio_esfera + pulso), 2)
                            pygame.draw.circle(tela, (255, 30, 30), origem_laser, int(raio_esfera * 0.7))
                            pygame.draw.circle(tela, (255, 255, 255), origem_laser, int(raio_esfera * 0.3))

                            # Desenha linhas guias finas mostrando onde os raios vão nascer (aviso)
                            if progresso_carga > 0.5:
                                num_f_aviso = 1 if rodada == 1 else (2 if rodada == 2 else (4 if rodada == 3 else 6))
                                for i in range(num_f_aviso):
                                    ang_aviso = i * ((math.pi * 2) / num_f_aviso)
                                    f_av_x = origem_laser[0] + math.cos(ang_aviso) * 2500
                                    f_av_y = origem_laser[1] + math.sin(ang_aviso) * 2500
                                    pygame.draw.line(tela, (100, 0, 0), origem_laser, (f_av_x, f_av_y), 1)

                            if tempo_laser >= laser['duracao_carga']:
                                laser['fase'] = 'disparando'
                                laser['tempo_inicio_disparo'] = agora

                        elif laser['fase'] == 'disparando':
                            t_disp = agora - laser['tempo_inicio_disparo']
                            progresso = min(1.0, t_disp / laser['duracao_disparo'])

                            # ====================================================================
                            # CONFIGURADOR DE ESTÁGIOS DA MÁQUINA DE MORTE
                            # ====================================================================
                            if rodada == 1:
                                num_feixes = 1
                                sentido = 1
                                giro_total = math.pi * 1.0 # Reduzido pela metade (180º)
                                esp = [65, 35, 15, 6]
                                hitbox_r = 38
                            elif rodada == 2:
                                num_feixes = 2
                                sentido = -1
                                giro_total = math.pi * 1.0 # Reduzido pela metade (180º cada braço)
                                esp = [65, 35, 15, 6]
                                hitbox_r = 38
                            elif rodada == 3:
                                num_feixes = 4
                                sentido = 1
                                giro_total = math.pi * 0.4 # Reduzido pela metade (72º em 4s)
                                esp = [65, 35, 15, 6]
                                hitbox_r = 38
                            else: # Rodada 4
                                num_feixes = 6
                                sentido = -1
                                giro_total = math.pi * 0.4 # Reduzido pela metade (72º em 4s)
                                esp = [30, 16, 6, 2]       # Feixes super finos
                                hitbox_r = 16

                            angulo_base = giro_total * progresso * sentido
                            tomou_dano_neste_frame = False

                            for i in range(num_feixes):
                                # Defasagem espalha os feixes uniformemente em 360º
                                angulo_atual = angulo_base + i * ((math.pi * 2) / num_feixes)

                                comp_laser = 2500 
                                fim_x = origem_laser[0] + math.cos(angulo_atual) * comp_laser
                                fim_y = origem_laser[1] + math.sin(angulo_atual) * comp_laser

                                tremor = math.sin(agora * 0.05) * 6 if rodada < 4 else math.sin(agora * 0.08) * 3

                                # Camadas do Plasma
                                pygame.draw.line(tela, (120, 0, 0), origem_laser, (fim_x, fim_y), int(esp[0] + tremor))
                                pygame.draw.line(tela, (220, 10, 10), origem_laser, (fim_x, fim_y), int(esp[1] + tremor))
                                pygame.draw.line(tela, (255, 120, 0), origem_laser, (fim_x, fim_y), int(esp[2] + tremor/2))
                                pygame.draw.line(tela, (255, 255, 255), origem_laser, (fim_x, fim_y), esp[3])

                                # Faiscas — 3/1 (era 6/2): indistinguivel a 60fps
                                qtd_particulas = 3 if rodada < 4 else 1
                                perp_ang = angulo_atual + math.pi / 2
                                cos_a, sin_a = math.cos(angulo_atual), math.sin(angulo_atual)
                                cos_p, sin_p = math.cos(perp_ang), math.sin(perp_ang)
                                for _ in range(qtd_particulas):
                                    dist_faisca = random.uniform(50, 1200)
                                    desvio = random.uniform(-esp[0] / 2, esp[0] / 2)
                                    f_x = origem_laser[0] + cos_a * dist_faisca + cos_p * desvio
                                    f_y = origem_laser[1] + sin_a * dist_faisca + sin_p * desvio
                                    tamanho_faisca = random.randint(2, 5) if rodada < 4 else 2
                                    cor_faisca = random.choice([(255, 50, 50), (255, 150, 0), (255, 255, 255)])
                                    pygame.draw.circle(tela, cor_faisca, (int(f_x), int(f_y)), tamanho_faisca)


                                # Matemática de Colisão
                                px_c, py_c = personagem_rect.center

                                numerador = abs((fim_y - origem_laser[1])*px_c - (fim_x - origem_laser[0])*py_c + fim_x*origem_laser[1] - fim_y*origem_laser[0])
                                denominador = math.hypot(fim_y - origem_laser[1], fim_x - origem_laser[0])
                                dist_linha = numerador / denominador if denominador > 0 else 9999

                                dot_product = (px_c - origem_laser[0]) * math.cos(angulo_atual) + (py_c - origem_laser[1]) * math.sin(angulo_atual)

                                if dist_linha <= hitbox_r and dot_product > 0:
                                    tomou_dano_neste_frame = True

                            if tomou_dano_neste_frame:
                                if agora - estado_atual_ia.get('ultimo_dano_laser', 0) > 100: 
                                    aplicar_hit_jogador(int(vida_maxima * 0.10), respeitar_resistencia=False)

                                    # --- PUNIÇÃO APOLO: Ser atingido pelo laser principal ---
                                    pass

                                    # --- MEMÓRIA ESPACIAL: Registra zona como perigosa no SafeZone Grid ---
                                    col_laser_hit = int(pos_x_personagem / max(1, largura_mapa / 8))
                                    row_laser_hit = int(pos_y_personagem / max(1, altura_mapa / 6))
                                    key_laser_hit = (col_laser_hit, row_laser_hit)
                                    pass
                                    pass

                                    # Matemática de Combustão Progressiva
                                    if player_em_chamas and agora < tempo_fim_chamas:
                                        multiplicador_chamas += 1
                                    else:
                                        multiplicador_chamas = 1

                                    player_em_chamas = True
                                    tempo_fim_chamas = agora + 4000

                                    efeitos_texto.append({
                                        "texto": f"INCINERADO! (x{multiplicador_chamas})",
                                        "x": pos_x_personagem + random.randint(-20, 20),
                                        "y": pos_y_personagem - 50,
                                        "tempo_inicio": agora,
                                        "cor": (255, 80, 0)
                                    })
                                    memoria_umbra.treinar(3.0) 
                                    estado_atual_ia['ultimo_dano_laser'] = agora



                            if t_disp >= laser['duracao_disparo']:
                                if laser['rodada'] < 4:
                                    laser['rodada'] += 1
                                    laser['fase'] = 'carregando'
                                    laser['tempo_inicio'] = agora
                                else:
                                    estado_atual_ia['laser_ativo'] = None
                                    estado_atual_ia['ultimo_laser'] = agora
                    if player_em_chamas:
                        if agora > tempo_fim_chamas:
                            player_em_chamas = False
                            multiplicador_chamas = 0
                        else:
                            # Aplica 2% da vida ATUAL por tick de 1 segundo, multiplicado pelas cargas
                            if agora - ultimo_tick_chamas >= 1000:
                                dano_chamas = vida * (0.02 * multiplicador_chamas)
                                aplicar_hit_jogador(dano_chamas, respeitar_resistencia=False, ativar_vanguarda=False)
                                ultimo_tick_chamas = agora

                                efeitos_texto.append({
                                    "texto": f"-{int(dano_chamas)}",
                                    "x": pos_x_personagem + random.randint(-15, 15),
                                    "y": pos_y_personagem - 30,
                                    "tempo_inicio": agora,
                                    "cor": (255, 100, 0)
                                })

                            # Gerador de Brasas (Caindo e esfriando)
                            if random.random() < 0.4:
                                particulas_fogo_player.append({
                                    "tipo": "brasa",
                                    "x": pos_x_personagem + random.randint(0, int(largura_personagem)),
                                    "y": pos_y_personagem + random.randint(0, int(altura_personagem)),
                                    "vx": random.uniform(-1, 1),
                                    "vy": random.uniform(1, 3.5), 
                                    "vida": 255,
                                    "tamanho": random.randint(3, 6)
                                })
                            # Gerador de Fumaça (Subindo e expandindo)
                            if random.random() < 0.3:
                                particulas_fogo_player.append({
                                    "tipo": "fumaca",
                                    "x": pos_x_personagem + random.randint(0, int(largura_personagem)),
                                    "y": pos_y_personagem - 10,
                                    "vx": random.uniform(-0.8, 0.8),
                                    "vy": random.uniform(-2.5, -1), 
                                    "vida": 255,
                                    "tamanho": random.randint(5, 12)
                                })

                    # Renderizador Físico das Partículas
                    nova_lista_fogo = []
                    for p in particulas_fogo_player:
                        if p["tipo"] == "brasa":
                            p["x"] += p["vx"]
                            p["y"] += p["vy"]
                            p["vida"] -= 8
                            p["tamanho"] = max(0.1, p["tamanho"] - 0.15)

                            if p["vida"] > 0 and p["tamanho"] > 0.1:
                                # Transição térmica: Laranja incandescente -> Cinza frio (chão)
                                cor_brasa = (255, int(p["vida"]), 0) if p["vida"] > 100 else (100, 100, 100)
                                pygame.draw.circle(tela, cor_brasa, (int(p["x"]), int(p["y"])), int(p["tamanho"]))
                                nova_lista_fogo.append(p)

                        elif p["tipo"] == "fumaca":
                            p["x"] += p["vx"]
                            p["y"] += p["vy"]
                            p["vida"] -= 6
                            p["tamanho"] += 0.25

                            if p["vida"] > 0:
                                cinza = int(p["vida"] * 0.4)
                                pygame.draw.circle(tela, (cinza, cinza, cinza), (int(p["x"]), int(p["y"])), int(p["tamanho"]))
                                nova_lista_fogo.append(p)
                    particulas_fogo_player = nova_lista_fogo




                    # Renderização Final da Barra de Vida da Boss
                    mostrar_vida_boss = True
                    if estado_atual_ia.get('miasma_ativo'):
                        if agora % 3000 < 2000:
                            mostrar_vida_boss = False

                    if mostrar_vida_boss:
                        pygame.draw.rect(tela, (40, 40, 40), (barra_x, barra_y, largura_barra, 7))
                        pygame.draw.rect(tela, (138, 43, 226), (barra_x, barra_y, largura_barra * vida_percent, 7))
                        pygame.draw.rect(tela, (0, 255, 0), (barra_x, barra_y, largura_barra, 7), 1)
                    # --- MOTOR DE COLAPSO DIMENSIONAL CÍCLICO ---
                    dimensao_atual = estado_atual_ia.get('dimensao_ativa')
                    if dimensao_atual:
                        tempo_na_dimensao = agora - estado_atual_ia['tempo_inicio_dimensao']

                        # Só transiciona se nenhuma habilidade dimensional estiver ativa
                        habilidade_ativa = False
                        chaves_limpas = ['vortice_ativo', 'prisao_ativa', 'caminho_espinhos', 'laser_ativo', 'descarga_eletrica', 'miasma_ativo']
                        for k in chaves_limpas:
                            if estado_atual_ia.get(k) is not None:
                                habilidade_ativa = True
                                break
                        if not habilidade_ativa:
                            ratos = estado_atual_ia.get('praga_ratos')
                            if ratos is not None:
                                dur = ratos.get('duracao', 9000)
                                if agora - ratos.get('tempo_inicio', 0) < dur:
                                    habilidade_ativa = True

                        if tempo_na_dimensao > estado_atual_ia['duracao_dimensao'] and not em_transicao_mapa and not habilidade_ativa:
                            estado_atual_ia['dimensao_ativa'] = None
                            estado_atual_ia['ultimo_transmutar'] = agora

                            mapa_antigo = mapa.copy().convert_alpha() 
                            mapa_atual_path = mapa_path5 
                            dados_p['mapa_atual'] = mapa_atual_path

                            mapa_novo = pygame.transform.scale(pygame.image.load(mapa_atual_path).convert(), (largura_mapa, altura_mapa))

                            particulas_pulso = []
                            for i in range(120): 
                                ang = random.uniform(0, math.pi * 2)
                                vel = random.uniform(15, 30) 
                                particulas_pulso.append({
                                    'x': pos_x_umbra + (largura_boss // 2),
                                    'y': pos_y_umbra + (altura_boss // 2),
                                    'vx': math.cos(ang) * vel,
                                    'vy': math.sin(ang) * vel,
                                    'tamanho': random.randint(20, 40) 
                                })

                            em_transicao_mapa = True
                            inicio_transicao_mapa = agora
                    if agora - tempo_ultima_esfera_umbra >= 30000:
                        esferas_energia_umbra.append({
                            "x": random.randint(100, largura_mapa - 100),
                            "y": random.randint(100, altura_mapa - 100),
                            "tempo_criacao": agora
                        })
                        tempo_ultima_esfera_umbra = agora

                    for esfera in esferas_energia_umbra[:]:
                        # Tempo de vida da esfera: 15 segundos
                        tempo_vida_esfera = agora - esfera["tempo_criacao"]
                        if tempo_vida_esfera >= 15000:
                            esferas_energia_umbra.remove(esfera)
                            continue

                        # Animação de pulso mais elaborada
                        pulso = math.sin(agora * 0.005) * 5
                        raio_esfera = 15 + pulso

                        # Animação de rotação de partículas ao redor
                        angulo_rotacao = (agora * 0.003) % (2 * math.pi)
                        for i in range(4):
                            ang = angulo_rotacao + (i * math.pi / 2)
                            px_particula = esfera["x"] + math.cos(ang) * (raio_esfera + 12)
                            py_particula = esfera["y"] + math.sin(ang) * (raio_esfera + 12)
                            pygame.draw.circle(tela, (100, 255, 180), (int(px_particula), int(py_particula)), 3)

                        # Efeito de fade out nos últimos 3 segundos
                        alpha_fade = 255
                        if tempo_vida_esfera >= 12000:
                            alpha_fade = int(255 * (1.0 - (tempo_vida_esfera - 12000) / 3000))

                        # Desenho da esfera com múltiplas camadas
                        pygame.draw.circle(tela, (0, 255, 150), (int(esfera["x"]), int(esfera["y"])), int(raio_esfera + 8), 2)
                        pygame.draw.circle(tela, (50, 255, 200), (int(esfera["x"]), int(esfera["y"])), int(raio_esfera))
                        pygame.draw.circle(tela, (255, 255, 255), (int(esfera["x"]), int(esfera["y"])), int(raio_esfera * 0.4))

                        # Indicador visual de tempo restante (anel externo que diminui)
                        tempo_restante_percentual = 1.0 - (tempo_vida_esfera / 15000)
                        if tempo_restante_percentual < 0.3:
                            # Piscar quando está acabando
                            if (agora // 200) % 2 == 0:
                                pygame.draw.circle(tela, (255, 100, 100), (int(esfera["x"]), int(esfera["y"])), int(raio_esfera + 12), 3)

                        cx_p = pos_x_personagem + largura_personagem // 2
                        cy_p = pos_y_personagem + altura_personagem // 2
                        distancia_coleta = math.hypot(cx_p - esfera["x"], cy_p - esfera["y"])

                        if distancia_coleta <= 45:
                            vida_perdida = vida_maxima - vida
                            cura_aplicada = int(vida_perdida * 0.50)
                            vida_antes = vida
                            vida += cura_aplicada

                            # Recompensa para Apolo MÁXIMA para ele viciar em coletar as orbes!
                            percentual_vida_antes = vida_antes / vida_maxima
                            if percentual_vida_antes < 0.3:  # Menos de 30% de vida
                                recompensa_coleta = 500.0  # RECOMPENSA COLOSSAL QUANDO ESTIVER MORRENDO
                                pass
                                efeitos_texto.append({"texto": "+500 DOPAMINA REWARD!", "x": pos_x_personagem, "y": pos_y_personagem - 50, "tempo_inicio": agora, "cor": (255, 215, 0)})
                            elif percentual_vida_antes < 0.6:  # Menos de 60% de vida
                                recompensa_coleta = 300.0  # RECOMPENSA MASSIVA
                                pass
                                efeitos_texto.append({"texto": "+300 DOPAMINA REWARD!", "x": pos_x_personagem, "y": pos_y_personagem - 50, "tempo_inicio": agora, "cor": (255, 215, 0)})
                            else:
                                recompensa_coleta = 150.0  # RECOMPENSA ENORME MESMO COM VIDA CHEIA
                                pass
                                efeitos_texto.append({"texto": "+150 DOPAMINA REWARD!", "x": pos_x_personagem, "y": pos_y_personagem - 50, "tempo_inicio": agora, "cor": (255, 215, 0)})

                            efeitos_texto.append({
                                "texto": f"+{cura_aplicada} RESTAURAÇÃO!",
                                "x": pos_x_personagem,
                                "y": pos_y_personagem - 30,
                                "tempo_inicio": agora,
                                "cor": (0, 255, 150)
                            })

                            pass
                            esferas_energia_umbra.remove(esfera)
                else:
                    img_atual_boss = frames_geo_umbra_paths[direcao_boss][frame_boss]
                    offset_y_boss = math.sin(agora * 0.005) * 7
                    img_atual_boss = pygame.transform.flip(img_atual_boss, True, False)
                    # Desenhar sombra do boss
                    desenhar_sombra(tela, pos_x_umbra, pos_y_umbra + offset_y_boss, largura_boss, altura_boss, offset_y=10)
                    tela.blit(img_atual_boss, (pos_x_umbra, pos_y_umbra + offset_y_boss))

            ###############################################   DESENHA O PERSONAGEM NA TELA ################################
            # Desenhar sombra do personagem
            desenhar_sombra(tela, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)

            if direcao_atual == 'disp' and lacerante_manifestacao.ativa(manifestacao_ativa):
                estagio = lacerante_manifestacao.obter_proximo_estagio()
                idx = estagio * 2 + (frame_atual % 2)
                if idx < len(Variaveis.frames_lacerar):
                    frame_para_desenhar = Variaveis.frames_lacerar[idx]
                else:
                    frame_para_desenhar = frames_animacao[direcao_atual][frame_atual % len(frames_animacao[direcao_atual])]
            else:
                frame_para_desenhar = frames_animacao[direcao_atual][frame_atual % len(frames_animacao[direcao_atual])]
            if direcao_atual == 'disp' and math.cos(angulo_disparo_preparado) < 0:
                frame_para_desenhar = pygame.transform.flip(frame_para_desenhar, True, False)
            desenhar_personagem_estado = desenhar_personagem_miasma if estado_atual_ia.get('miasma_ativo') else desenhar_personagem_com_dano
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

            # Desenhar zona de teleporte (se estiver mirando no modo mouse)
            Variaveis.desenhar_zona_teleporte(tela, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, distancia_dash)
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
            if aurea == "Vanguarda" and tempo_atual < vanguarda_fogo_fim:
                incendiar_vanguarda_proximos(tempo_atual)
            desenhar_efeitos_vanguarda(
                tela,
                pos_x_personagem,
                pos_y_personagem,
                largura_personagem,
                altura_personagem,
                alvos_vanguarda_fase5(),
                inimigos_em_chamas,
                duracao_incendio_vanguarda,
                aurea,
                config_graficos,
                vanguarda_fogo_fim,
            )

            # Se a IA ainda não foi processada neste frame, garantimos que o estado exista
            if 'estado_atual_ia' not in locals() and 'estado_atual_ia' not in globals():
                estado_atual_ia = {'parede_ativa': False}

            # --- MOTOR DE PRAGA DE RATOS (DIMENSÃO 9) ---
            if estado_atual_ia.get('dimensao_ativa') == "rastro":
                ratos = estado_atual_ia.get('ratos_ativos', [])
                novos_ratos = []
                if ratos:  # early-exit se lista vazia
                    # Pre-computa rect do personagem para colisao eficiente
                    rect_player_rats = pygame.Rect(
                        pos_x_personagem, pos_y_personagem,
                        largura_personagem, altura_personagem
                    ).inflate(60, 60)  # zona de colisao de 30px ao redor
                    pcx = pos_x_personagem + largura_personagem // 2
                    pcy = pos_y_personagem + altura_personagem // 2

                    for rato in ratos:
                        vivo = True
                        # Steering Boids (Cercamento Implacavel)
                        dx = pcx - rato['x']
                        dy = pcy - rato['y']
                        dist = math.hypot(dx, dy)
                        if dist > 0:
                            rato['x'] += (dx / dist) * 6.0
                            rato['y'] += (dy / dist) * 6.0

                        # Colisao com o Jogador — Rect.collidepoint e O(1)
                        if vivo and rect_player_rats.collidepoint(rato['x'], rato['y']):
                            if dist < 30:
                                vivo = False
                                aplicar_hit_jogador(5.0, respeitar_resistencia=False)
                                vida_boss5 = min( vida_boss5 + 20)
                                estado_atual_ia['ratos_adicionais'] = estado_atual_ia.get('ratos_adicionais', 0) + 1
                                memoria_umbra.treinar(5.0)
                                pass
                                efeitos_texto.append({"texto": "+20 LIFESTEAL / +1 RATO", "x": pos_x_umbra,
                                                      "y": pos_y_umbra - 30, "tempo_inicio": agora, "cor": (50, 255, 50)})

                        # Bloqueio Ativo (Escudo de Carne / Destruicao de Ratos)
                        if vivo:
                            rato_rect = pygame.Rect(int(rato['x']) - 25, int(rato['y']) - 25, 50, 50)
                            for tiro in list(disparos):
                                if rato_rect.colliderect(tiro['rect']):
                                    vivo = False
                                    if tiro in disparos:
                                        disparos.remove(tiro)
                                    efeitos_texto.append({"texto": "SPLAT!", "x": rato['x'], "y": rato['y'],
                                                          "tempo_inicio": agora, "cor": (100, 0, 100)})
                                    pass
                                    break

                        if vivo:
                            novos_ratos.append(rato)
                            # Arte Procedural Boids/Rato
                            pygame.draw.circle(tela, (20, 10, 30), (int(rato['x']), int(rato['y'])), 12)
                            pygame.draw.circle(tela, (130, 20, 150), (int(rato['x']), int(rato['y'])), 8)
                            pygame.draw.circle(tela, (50, 255, 50),
                                               (int(rato['x']) + random.randint(-2, 2),
                                                int(rato['y']) + random.randint(-2, 2)), 3)

                estado_atual_ia['ratos_ativos'] = novos_ratos


            novos_disparos = []


            for disparo in disparos:
                # 1. Movimentação do Projétil do Jogador
                vfx_disparo_player.atualizar_disparo(disparo, velocidade_disparo, dt)

                atingiu_boss = False
                interceptado = False
                if luta_iniciada:
                    acertou_boss_disparo = (
                        lacerante_manifestacao.colisao_corte(disparo, hitbox_boss5, tempo_atual)
                        if disparo.get("tipo_manifestacao") == "lacerante_corte"
                        else disparo["rect"].colliderect(hitbox_boss5)
                    )
                    if acertou_boss_disparo:

                        if random.random() <= chance_critico:
                            dano_final = dano_person_hit * 2 * fator_dano_aureas()
                            punicao = -4.0  # Dano crítico pune o dobro
                            cor_feedback = (255, 255, 0) # Amarelo Crítico
                        else:
                            dano_final = dano_person_hit * fator_dano_aureas()
                            cor_feedback = (255, 255, 255) # Branco Normal

                        dano_final *= lacerante_manifestacao.multiplicador_dano_disparo(disparo)

                        # Se o escudo (parede_ativa) estiver ligado, reduzimos o dano em 25%
                        if estado_atual_ia.get('parede_ativa'):
                            dano_final *= 0.75
                            cor_feedback = (0, 200, 255) # Azul de Escudo

                        # Aplicação da Resistência Passiva da Umbra
                        if 'resistencia_umbra' in globals() and resistencia_umbra > 0:
                            dano_final *= max(0.1, 1.0 - (resistencia_umbra / 100.0))

                        # O Escudo de Atrito (Reduz dano em 70% e carrega a fúria)
                        if estado_atual_ia.get('dimensao_ativa') == "atrito":
                            dano_final *= 0.3
                            if not estado_atual_ia.get('laser_ativo'):
                                estado_atual_ia['carga_atrito'] = estado_atual_ia.get('carga_atrito', 0) + 8

                                if estado_atual_ia['carga_atrito'] >= 100:
                                    estado_atual_ia['laser_ativo'] = {
                                        'tempo_inicio':          agora,
                                        'fase':                  'carregando',
                                        'rodada':                1,
                                        'duracao_carga':         1500,
                                        'duracao_disparo':       4000,
                                        'angulo_base_inicio':    random.uniform(0, math.pi * 2)  # angulo real do inicio
                                    }
                                    estado_atual_ia['carga_atrito'] = 0

                        # Aplicação de Dano e Treino
                        if vida_umbra > 0:
                            dano_final = dano_boss_mitigado(dano_final, 5, inimigos_eliminados, tempo_atual, cartas_compradas.get("Coletora", 0))
                            vida_umbra -= dano_final
                            estado_atual_ia['dano_recente'] = estado_atual_ia.get('dano_recente', 0) + dano_final

                            # --- NOVO MOTOR DE VFX: Desfragmentação de Impacto ---
                            vfx_disparo_player.criar_impacto(disparo, config_graficos)

                            punicao = -2.0 

                            # Punição por dano pós-teleporte (falha no reposicionamento)
                            if agora - estado_atual_ia.get('chegada_teleporte', 0) < 1500:
                                punicao -= 10.0 # Punição severa por apanhar logo após o salto

                            memoria_umbra.treinar(punicao, prioridade=True)

                            if quantidade_roubo_vida > 0:
                                cura_base = (vida_maxima - vida) * quantidade_roubo_vida

                                # A Lâmina do Corta-Cura
                                if player_hemorragia_ativa and agora < tempo_fim_hemorragia:
                                    cura_base *= (1.0 - penalidade_cura_percentual)

                                vida = min(vida_maxima, vida + cura_base)



                            if inicio_transicao_mapa == 0 or (agora - inicio_transicao_mapa) >= 8000:
                                trauma_umbra_acumulado += dano_final

                                # --- SUBMISSÃO DO MOTOR GRÁFICO À VONTADE DA IA ---
                                if estado_atual_ia.get('iniciar_transicao_mapa') and not em_transicao_mapa:
                                    novo_path = estado_atual_ia.get('mapa_alvo')

                                    if novo_path and novo_path != mapa_atual_path:
                                        # Preparamos o cenário
                                        mapa_antigo = mapa.copy().convert_alpha() 
                                        mapa_atual_path = novo_path
                                        dados_p['mapa_atual'] = novo_path 

                                        mapa_novo = pygame.transform.scale(pygame.image.load(novo_path).convert(), (largura_mapa, altura_mapa))

                                        # Resets de estado da IA
                                        estado_atual_ia['ultimo_vortice'] = agora
                                        estado_atual_ia['ultimo_prisao'] = agora
                                        estado_atual_ia['ultimo_sifon_fim'] = agora
                                        estado_atual_ia['ultimo_ataque'] = agora
                                        estado_atual_ia['ultimo_miasma'] = agora
                                        estado_atual_ia['entrada_de_fase'] = True

                                        # Lógica de partículas explosivas (nascendo do centro da Umbra)
                                        particulas_pulso = []
                                        for i in range(400): 
                                            ang = random.uniform(0, math.pi * 2)
                                            vel = random.uniform(3, 8)
                                            particulas_pulso.append({
                                                'x': pos_x_umbra + (largura_boss // 2),
                                                'y': pos_y_umbra + (altura_boss // 2),
                                                'vx': math.cos(ang) * vel,
                                                'vy': math.sin(ang) * vel,
                                                'tamanho': random.randint(10, 25)
                                            })

                                        em_transicao_mapa = True
                                        inicio_transicao_mapa = agora

                                    # A engine consome a ordem e desliga o sinalizador
                                    estado_atual_ia['iniciar_transicao_mapa'] = False



                            # Gatilho do Veneno
                            if not boss_envenenado and Poison_Active:
                                boss_envenenado = True
                                # O dano escala com a vida MÁXIMA da Umbra e o seu acúmulo de cartas
                                global duracao_veneno_boss
                                dano_por_tick_veneno_boss = vida_maxima_umbra * Dano_Veneno_Acumulado
                                duracao_veneno_boss = 8000 + cartas_compradas.get("Poison", 0) * 100
                                tempo_inicio_veneno_boss = agora
                                ultimo_tick_veneno_boss = agora
                            # --- CORROSÃO: DANO CONTÍNUO DE VENENO ---
                            if boss_envenenado:
                                # Aplica o tick de dano a cada 500 milissegundos
                                if agora - ultimo_tick_veneno_boss >= INTERVALO_TICK_VENENO:
                                    vida_umbra -= dano_boss_mitigado(dano_por_tick_veneno_boss, 5, inimigos_eliminados, agora, cartas_compradas.get("Coletora", 0), tipo_dano="veneno")
                                    ultimo_tick_veneno_boss = agora

                                    # Feedback Visual (Verde Tóxico integrado ao sistema de partículas)
                                    efeitos_texto.append({
                                        "texto": f"-{int(dano_por_tick_veneno_boss)}",
                                        "x": hitbox_boss5.centerx + random.randint(-30, 30),
                                        "y": hitbox_boss5.top - random.randint(10, 30),
                                        "tempo_inicio": agora,
                                        "cor": (50, 255, 50) # Verde vibrante
                                    })

                                    # Punição sensorial na rede neural: A Umbra odeia o dano contínuo
                                    memoria_umbra.treinar(-0.8)

                                # Verifica se o efeito do veneno passou
                                if agora - tempo_inicio_veneno_boss >= duracao_veneno_boss:
                                    boss_envenenado = False
                            # Feedback Visual e Limpeza
                            efeitos_texto.append({
                                "texto": f"-{int(dano_final)}",
                                "x": hitbox_boss5.centerx + random.randint(-20, 20),
                                "y": hitbox_boss5.top - 10,
                                "tempo_inicio": agora,
                                "cor": cor_feedback
                            })
                            atingiu_boss = True
                            pass
                            estado_atual_ia['tomou_tiro_no_dash'] = True


                # 5. Manutenção de Projéteis no Mapa
                dentro_mapa = (
                    (disparo.get("tipo_manifestacao") == "lacerante_corte" and not disparo.get("expirado"))
                    or (0 <= disparo["rect"].x < largura_mapa and 0 <= disparo["rect"].y < altura_mapa)
                )
                if dentro_mapa and not atingiu_boss and not interceptado:
                    novos_disparos.append(disparo)
                elif not atingiu_boss and not interceptado:
                    # Punição por tiro perdido na borda (Ensina ele a poupar munição e atirar só com mira certa)
                    pass

            disparos = novos_disparos

            # --- PROCESSAMENTO DE PROJÉTEIS DA BOSS 5 ---
            rect_personagem = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
            novos_projeteis_boss = []

            # DISPAROS BÔNUS DA UMBRA (concedidos por espinhos)
            bonus = estado_atual_ia.get('bonus_tiros', 0)
            if bonus > 0 and luta_iniciada:
                centro_bx = pos_x_umbra + largura_boss // 2
                centro_by = pos_y_umbra + altura_boss // 2
                centro_px = pos_x_personagem + largura_personagem // 2
                centro_py = pos_y_personagem + altura_personagem // 2
                ang_bonus = math.atan2(centro_py - centro_by, centro_px - centro_bx)
                for spread in [-0.15, 0, 0.15]:
                    estado_atual_ia['projeteis'].append({
                        "rect": pygame.Rect(centro_bx - 6, centro_by - 6, 12, 12),
                        "angulo": ang_bonus + spread,
                        "velocidade": 11,
                        "tipo": "bonus"
                    })
                estado_atual_ia['bonus_tiros'] = bonus - 1

            # Renderizar os disparos (NOVO MOTOR PROCEDURAL)
            for disparo in disparos:
                vfx_disparo_player.desenhar_disparo(tela, disparo, agora, config_graficos)
            vfx_disparo_player.atualizar_e_desenhar_particulas(tela, dt, config_graficos)

            # Atualizar e Desenhar Partículas de Desfragmentação (Globais)
            pass  # VFX update (simplificado)

            for moeda in moedas_soltadas[:]:
                if personagem_rect.colliderect(moeda["rect"]):
                    moedas_coletadas += 1
                    moedas_totais += 1   # acumula no total salvo
                    moedas_soltadas.remove(moeda)
                    salvar_atributos()   #salva imediatamente

            Variaveis.atualizar_e_desenhar_feedback_cooldown(tela, tempo_atual, efeitos_texto)
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
                diferenca_altura =  altura_personagem - 115
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

                # Mantendo a interceptação do Corta-Cura (Fase 6)
                if player_hemorragia_ativa and tempo_atual < tempo_fim_hemorragia:
                    cura_trembo *= (1.0 - penalidade_cura_percentual)

                vida = min(vida_maxima, vida + cura_trembo)
                tempo_ultima_regeneracao = tempo_atual
            # --- OTIMIZACAO UI ---
            total_cartas_compradas = sum(cartas_compradas.values())
            custo_carta_atual = custo_base_carta + (total_cartas_compradas * custo_por_carta)
            cooldowns = {
                "disparo": max(0.0, (intervalo_disparo_racional(intervalo_disparo, aurea, racional_dilatacao_fim, tempo_atual) - (tempo_atual - tempo_ultimo_disparo)) / 1000.0),
                "teleporte": max(0.0, (cooldown_teleporte_vanguarda(tempo_cooldown_dash, aurea, alvos_vanguarda_fase5(), inimigos_em_chamas, duracao_incendio_vanguarda, tempo_atual) - (pygame.time.get_ticks() - tempo_ultimo_dash)) / 1000.0),
                "onda": max(0.0, (cooldown_habilidade * lacerante_manifestacao.multiplicador_cooldown_habilidade(manifestacao_ativa) - (tempo_atual - tempo_ultimo_uso_habilidade)) / 1000.0),
                "loja": 1 if pontuacao_exib >= custo_carta_atual else 0,
            }

            if False: # Desativado pois o HUD agora é widescreen desenhado nas bordas
                posicao_barra_vida = (80, altura_mapa - (altura_mapa - 34))

                # Lazy init das fontes da UI (evita pygame.font.Font() por frame)
                if not hasattr(render_cached_text, '_fonte_ui'):
                    render_cached_text._fonte_ui = pygame.font.Font(None, int(altura_barra_vida*1))
                    render_cached_text._fonte_vida = pygame.font.Font(None, int(altura_barra_vida*0.9))
                fonte = render_cached_text._fonte_ui
                fonte_vida = render_cached_text._fonte_vida

                # Usa cache para render de textos, cortando alocacoes por frame
                texto_vida_str = f'{int(vida)}/{int(vida_maxima)}'
                texto_vida = render_cached_text(texto_vida_str, fonte_vida, (255, 255, 255))
                texto_vida_borda = render_cached_text(texto_vida_str, fonte_vida, (0, 0, 0))

                texto_pontuacao_str = f'{pontuacao_exib}/{custo_carta_atual}'
                texto_pontuacao = render_cached_text(texto_pontuacao_str, fonte, (255, 255, 255))
                texto_pontuacao_borda = render_cached_text(texto_pontuacao_str, fonte, (0, 0, 0))

                # Desenha o texto da borda da pontuacao deslocado (4x blits, 0x renders novos)
                tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 - 1, altura_mapa*0.118 - 1))
                tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 + 1, altura_mapa*0.118 - 1))
                tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 - 1, altura_mapa*0.118 + 1))
                tela.blit(texto_pontuacao_borda, (largura_mapa*0.075 + 1, altura_mapa*0.118 + 1))

                # Desenha o texto da pontuação por cima da borda
                tela.blit(texto_pontuacao, (largura_mapa*0.075, altura_mapa*0.118))

                # Preenchendo a parte do círculo (Usa array pre-calculado, elimina 360 sines/cosines/frame)
                angulo_preenchimento = (pontuacao_magia / 735) * 360
                idx_preenchimento = int(angulo_preenchimento)
                if idx_preenchimento > 0:
                    idx_preenchimento = min(idx_preenchimento, 360)
                    pontos_ui = _PONTOS_PREENCHIMENTO[:idx_preenchimento + 1]
                    pygame.draw.polygon(tela, (53, 239, 252), [centro_circulo] + pontos_ui)

                tela.blit(imagem_relogio, posicao_imagem_relogio)

                porcentagem_vida_personagem = (vida / vida_maxima) * 100
                if aurea == "Devota" and escudo_devota_ativo:
                    cor_barra = (0, 150, 255)  # Azul para indicar o escudo ativo
                else:
                    cor_barra = calcular_cor_barra_de_vida(porcentagem_vida_personagem)

                pygame.draw.rect(tela, cor_barra, (posicao_barra_vida[0], posicao_barra_vida[1], (vida / vida_maxima) * largura_barra_vida, altura_barra_vida))
                pygame.draw.rect(tela, (0, 0, 0), (posicao_barra_vida[0], posicao_barra_vida[1], largura_barra_vida, altura_barra_vida), 2)

                # Desenha o texto da borda da vida
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
                if eliminacoes_consecutivas > 0:
                    fonte_combo = _fonte_combo_cached
                    fonte_bonus = _fonte_bonus_cached

                    # Texto do combo
                    texto_combo = f"Combo: {eliminacoes_consecutivas}"
                    posicao_combo = (largura_mapa - 170, 50)  
                    desenhar_texto_com_contorno(tela, texto_combo, fonte_combo, (255, 255, 255), (0, 0, 0), posicao_combo)

                    # Texto do bônus
                    texto_bonus = f"Bônus: +{bonus_pontuacao}"
                    posicao_bonus = (largura_mapa - 200, 90)  
                    desenhar_texto_com_contorno(tela, texto_bonus, fonte_bonus, (255, 255, 255), (0, 0, 0), posicao_bonus)

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

            Variaveis.desenhar_refragmentacao_rewind(tela, tempo_atual)
            Variaveis.desenhar_overlay_vida_critica(tela, vida, vida_maxima, tempo_atual)

            desenhar_hud_fase(
                tela, vida, vida_maxima, pontuacao_exib, custo_carta_atual,
                pontuacao_magia, cooldowns, dispositivo_ativo,
                eliminacoes_consecutivas, bonus_pontuacao, aurea,
                escudo_devota_ativo, pos_x_personagem, pos_y_personagem,
                largura_personagem, altura_personagem
            )

            Variaveis.aplicar_tremor_dano_tela(tela, tempo_atual, tempo_ultimo_hit_inimigo, piscando_vida)

            tela.blit(cursor_imagem, (mouse_x, mouse_y))

            exibir_cronometro(tela)

            pygame.display.flip()
            # 144 FPS: A IA já roda em processo separado (multiprocessing), não precisa de tick alto.
            # O tick(900) anterior fazia TODO o código Python rodar 900x/s, causando 80%+ CPU.
            dt_ms = FPS.tick(config_graficos.get("fps_limite", 60))
            dt = max(0.05, min(3.0, dt_ms / 16.666667))
            Variaveis.dt = dt


        # Encerrar o Pygame
        _salvar_tudo_ao_sair()
        pygame.quit()
        sys.exit(0)
    except CleanExit:
        return
    finally:
        try:
            _salvar_tudo_ao_sair()
        except Exception:
            pass
        _sys.exit = _orig_sys_exit
        _os._exit = _orig_os_exit
        if _orig_builtins_exit:
            _builtins.exit = _orig_builtins_exit


if __name__ == '__main__':
    executar_jogo()
