import pygame
import subprocess
import sys
import random
import math
import time
import os
import json
from Tela_Cartas import tela_de_pausa
from Loja_Endgame import tela_loja_endgame, aplicar_deck_endgame
from Variaveis import *
from utils import *
import habilidade_boss as hb
import collections
from audio_manager import carregar_config_audio, aplicar_volume_som
from sistema_ratos_umbra import GerenciadorRatos

if __name__ == "__main__":
    pygame.init()
    memoria_umbra = hb.MemoriaEvolutivaUmbra()

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
        with open("config_graficos.json", "r") as f:
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

    estalos = aplicar_volume_som(pygame.mixer.Sound("Sounds/Estalo.mp3"), config_audio)

    som_ataque_boss = aplicar_volume_som(pygame.mixer.Sound("Sounds/Hit_Boss1.mp3"), config_audio)

    Disparo_Geo = aplicar_volume_som(pygame.mixer.Sound("Sounds/Disparo_Geo.wav"), config_audio)

    Musica_tema_Boss1 = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase1_Boss.mp3"), config_audio)

    Musica_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Fase_boas.mp3"), config_audio)

    Som_tema_fases = aplicar_volume_som(pygame.mixer.Sound("Sounds/Praia.wav"), config_audio)

    Som_portal = aplicar_volume_som(pygame.mixer.Sound("Sounds/Portal.mp3"), config_audio) 

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

    #####################################################################APOLO1######################################################################################################

    ###########################################################################################################################################################################

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
        if os.path.exists('atributos.json'):
            os.remove('atributos.json')

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

        with open('atributos.json', 'w') as file:
            json.dump(atributos, file)

    def carregar_atributos():
        global velocidade_personagem, intervalo_disparo, dano_person_hit, chance_critico, roubo_de_vida, quantidade_roubo_vida,vida_maxima,vida_maxima_petro,vida,xp_petro,Petro_active,trembo,dano_petro,Resistencia,Resistencia_petro,dano_inimigo_longe,dano_inimigo_perto,direcao_atual,Poison_Active,Ultimo_Estalo,Executa_inimigo,Valor_Bonus,Mercenaria_Active,tempo_cooldown_dash,vida_petro,petro_evolucao,Dano_Veneno_Acumulado, Tempo_cura,porcentagem_cura, moedas_totais
        with open('atributos.json', 'r') as file:
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


    #####################################################################CONTROLE DO JOGADOR######################################################################################################
    def atualizar_posicao_personagem(keys, joystick):
        global pos_x_personagem, pos_y_personagem, direcao_atual, ultima_tecla_movimento
        global movimento_pressionado, cooldown_dash, distancia_dash, tempo_ultimo_dash, teleporte_timer, teleporte_duration, teleporte_index
        global hitbox_boss5, estado_atual_ia, angulo_inclinacao_personagem

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

        # ---- DASH/TELEPORTE ----
        dash_teclado = keys[config_teclas["Teleporte"]]
        dash_joystick = joystick and joystick.get_button(4) if joystick else False
        
        if (dash_teclado or dash_joystick) and cooldown_dash == False and atordoado == False:
            Som_portal.play()
            teleporte_timer += velocidade_personagem
            if teleporte_timer >= teleporte_duration:
                teleporte_index = (teleporte_index + 1) % len(teleporte_sprites)
                teleporte_timer = 0
            
            tela.blit(teleporte_sprites[teleporte_index], (pos_x_personagem, pos_y_personagem))

            if ultima_tecla_movimento == 'up': pos_y_personagem = max(0, pos_y_personagem - distancia_dash)
            elif ultima_tecla_movimento == 'down': pos_y_personagem = min(altura_mapa - altura_personagem, pos_y_personagem + distancia_dash)
            elif ultima_tecla_movimento == 'left': pos_x_personagem = max(0, pos_x_personagem - distancia_dash)
            elif ultima_tecla_movimento == 'right': pos_x_personagem = min(largura_mapa - largura_personagem, pos_x_personagem + distancia_dash)
        
            cooldown_dash = True
            tempo_ultimo_dash = pygame.time.get_ticks()

        if cooldown_dash and pygame.time.get_ticks() - tempo_ultimo_dash > tempo_cooldown_dash:
            cooldown_dash = False

        return direcao_atual
    ##########################################################################################################################################################################
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


    def tela_upgrade_aureas(tela, fonte, moedas_disponiveis):
        if not os.path.exists("aureas_upgrade.json"):
            dados_iniciais = {
                "Racional": 0,
                "Impulsiva": 0,
                "Devota": 0,
                "Vanguarda": 0
            }
            with open("aureas_upgrade.json", "w") as f:
                json.dump(dados_iniciais, f, indent=4)
    
        with open("aureas_upgrade.json", "r") as f:
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

        upgrades = carregar_upgrade_aureas("aureas_upgrade.json")

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
                    memoria_umbra.salvar() # Garante que a experiência seja gravada no JSON
                    rodando = False
                    pygame.quit()
                    os._exit(0)
                elif evento.type == pygame.KEYDOWN:
                    if evento.key in [pygame.K_RIGHT, pygame.K_d]:
                        selecionado = (selecionado + 1) % len(aureas)
                        while not aureas[selecionado]["ativa"]:
                            selecionado = (selecionado + 1) % len(aureas)
                    elif evento.key in [pygame.K_LEFT, pygame.K_a]:
                        selecionado = (selecionado - 1) % len(aureas)
                        while not aureas[selecionado]["ativa"]:
                            selecionado = (selecionado - 1) % len(aureas)

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

    # =====================================================================
    # NÚCLEO DE APRENDIZADO DE CARTAS (APOLO)
    # =====================================================================
    import collections
    import os
    import json
    import random

    cartas_compradas_apolo_global = []

    def carregar_memoria_cartas():
        arquivo = "memoria_cartas_apolo.json"
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
        with open("memoria_cartas_apolo.json", "w") as f:
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
            if escolhas.count("Trembo") >= 1 and "Trembo" in opcoes_validas: opcoes_validas.remove("Trembo")
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

        contagem = collections.Counter(escolhas)
        print("\n" + "="*50)
        print(f"SELECAO GENETICA DE APOLO UCB ({qtd} Cartas)")
        for carta, q in sorted(contagem.items(), key=lambda x: x[1], reverse=True): 
            print(f"[{q}x] {carta}")
        print("="*50)
    
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
        global cartas_compradas_apolo_global

        inimigos_eliminados = 3000

        multiplicador_dano_umbra = 1.0
        reducao_cooldown_umbra = 1.0
        resistencia_umbra = 0.0
        bonus_cura_sifon = 0.0

        # --- PROGRESSÃO DO APOLO ---
        cartas_inteligentes = inteligencia_escolha_cartas_apolo(qtd_cartas_jogador)
        cartas_compradas_apolo_global = cartas_inteligentes

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
                dano_person_hit += 10 + (inimigos_eliminados // 50) * 1.5
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
    
        vida_maxima_umbra = int(25000 + (dps_escalonamento * 24) + (inimigos_eliminados * 25))

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

        print(f"\n[ UMBRA ] - {qtd_cartas_umbra} Cartas Sorteadas (Caos Puro)")
        for carta_u, qtd in sorted(collections.Counter(registro_umbra).items(), key=lambda x: x[1], reverse=True):
            print(f" -> [{qtd}x] {carta_u}")
        print("="*50 + "\n")

    # =========================================================================
    # LOJA DE SELEÇÃO DE BUILD — O jogador monta sua build manualmente
    # =========================================================================
    deck_escolhido = tela_loja_endgame()
    cartas_compradas_apolo_global = deck_escolhido

    # Monta o dicionário de atributos mutáveis para passar à função
    _variaveis_build = {
        "velocidade_personagem":  velocidade_personagem,
        "intervalo_disparo":      intervalo_disparo,
        "dano_person_hit":        dano_person_hit,
        "chance_critico":         chance_critico,
        "roubo_de_vida":          roubo_de_vida,
        "quantidade_roubo_vida":  quantidade_roubo_vida,
        "vida_maxima":            vida_maxima,
        "vida":                   vida,
        "trembo":                 trembo,
        "Tempo_cura":             Tempo_cura,
        "porcentagem_cura":       porcentagem_cura,
        "Resistencia":            Resistencia,
        "tempo_cooldown_dash":    tempo_cooldown_dash,
        "vida_petro":             vida_petro,
        "vida_maxima_petro":      vida_maxima_petro,
        "vida_maxima_umbra":      vida_maxima_umbra,
        "vida_umbra":             vida_umbra,
        "multiplicador_dano_umbra": 1.0,
        "reducao_cooldown_umbra":   1.0,
        "resistencia_umbra":        0.0,
        "bonus_cura_sifon":         0.0,
    }

    _variaveis_build = aplicar_deck_endgame(deck_escolhido, _variaveis_build)

    # Reaplica os atributos de volta às variáveis globais
    velocidade_personagem  = _variaveis_build["velocidade_personagem"]
    intervalo_disparo      = _variaveis_build["intervalo_disparo"]
    dano_person_hit        = _variaveis_build["dano_person_hit"]
    chance_critico         = _variaveis_build["chance_critico"]
    roubo_de_vida          = _variaveis_build["roubo_de_vida"]
    quantidade_roubo_vida  = _variaveis_build["quantidade_roubo_vida"]
    vida_maxima            = _variaveis_build["vida_maxima"]
    vida                   = _variaveis_build["vida"]
    trembo                 = _variaveis_build["trembo"]
    Tempo_cura             = _variaveis_build["Tempo_cura"]
    porcentagem_cura       = _variaveis_build["porcentagem_cura"]
    Resistencia            = _variaveis_build["Resistencia"]
    tempo_cooldown_dash    = _variaveis_build["tempo_cooldown_dash"]
    vida_petro             = _variaveis_build["vida_petro"]
    vida_maxima_petro      = _variaveis_build["vida_maxima_petro"]
    vida_maxima_umbra      = _variaveis_build["vida_maxima_umbra"]
    vida_umbra             = _variaveis_build["vida_umbra"]
    multiplicador_dano_umbra  = _variaveis_build["multiplicador_dano_umbra"]
    reducao_cooldown_umbra    = _variaveis_build["reducao_cooldown_umbra"]
    resistencia_umbra         = _variaveis_build["resistencia_umbra"]
    bonus_cura_sifon          = _variaveis_build["bonus_cura_sifon"]
    ###################################################################################################################################################################################################
    # Geração de coordenadas estocásticas para o início do embate
    pos_x_personagem, pos_y_personagem = gerar_posicao_aleatoria(largura_mapa, altura_mapa, largura_personagem, altura_personagem)
    pos_x_petro= pos_x_personagem + largura_personagem + 4
    pos_y_petro = pos_y_personagem

    ###################################################################################################PRINCIPAL#################################################################################################################
    #LOOP PRINCIPAL

    # Inicializa a tela (Necessário para carregar sprites)
    tela = pygame.display.set_mode((largura_mapa, altura_mapa))
    # Inicializar gerenciador de ratos da Umbra
    gerenciador_ratos = GerenciadorRatos(largura_mapa, altura_mapa)

    # CACHE DE SPRITES DE DISPARO (Otimização Zero-Allocation)
    frames_disparo_normal = [pygame.transform.scale(pygame.image.load(p).convert_alpha(), (largura_disparo, altura_disparo)) for p in ["Sprites/Fogo1.png", "Sprites/Fogo2.png"]]
    frames_disparo_impulso = [pygame.transform.scale(pygame.image.load(p).convert_alpha(), (largura_disparo, altura_disparo)) for p in ["Sprites/Fogo_impulso1.png", "Sprites/Fogo_impulso2.png"]]

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

    try:
        with open("aureas_upgrade.json", "r") as f:
            upgrades = json.load(f)
    except FileNotFoundError:
        upgrades = {"Racional": 0, "Impulsiva": 0, "Devota": 0, "Vanguarda": 0}

    try:
        with open('aurea_selecionada.json', 'r') as file:
            aurea = json.load(file)["aurea"]
    except FileNotFoundError:
        aurea = "Nenhuma"

    # =========================================================================
    # VARIÁVEIS DE INICIALIZAÇÃO PRÉ-LOOP (espelhadas do GAME5.py)
    # =========================================================================
    cursor_tamanho = (32, 32)
    tempo_passado = 0
    tempo_parado_person = 0
    frame_atual = 0
    frame_atual_disparo = 0
    ultima_tecla_movimento = None
    movimento_pressionado = False
    tempo_ultimo_hit_inimigo = pygame.time.get_ticks()
    piscando_vida = False
    posicao_barra_vida = (80, altura_mapa - (altura_mapa - 34))
    multiplicador_dano = 1.0
    multiplicador_velocidade = 1.0
    rodando = True
    mostrar_tutorial = False
    mostrar_vida_boss = True
    luta_iniciada = False
    ataque_liberado = False
    particulas_pulso = []
    tempo_inicial = time.time()
    tempo_anterior = pygame.time.get_ticks()
    boss_vivo1 = False
    pontuacao_inimigos = 0
    maxima_pontuacao_magia = 750
    piscar_magia = False
    ultimo_tempo_reducao = time.time()
    tempo_ultimo_disparo = 0
    tempo_ultimo_escudo = pygame.time.get_ticks()
    boss_atingido_por_onda = pygame.time.get_ticks()
    cartas_compradas_apolo_global = []
    historico_player = []

    mapa_atual_path = mapa_path5
    mapa = pygame.image.load(mapa_atual_path).convert()
    mapa = pygame.transform.scale(mapa, (largura_mapa, altura_mapa))

    # Inicializar tempo_start_boss na estado_atual_ia
    if 'tempo_start_boss' not in estado_atual_ia:
        estado_atual_ia['tempo_start_boss'] = pygame.time.get_ticks()
        estado_atual_ia['ultimo_ataque'] = pygame.time.get_ticks()
        estado_atual_ia['ultimo_teleporte'] = pygame.time.get_ticks()
        estado_atual_ia['ultimo_sifao'] = pygame.time.get_ticks()
        estado_atual_ia['passiva_chance'] = 0.30
        estado_atual_ia['passiva_reducao'] = 1.0
        estado_atual_ia['intervalo'] = 1900

    # Cursor personalizado
    FPS = pygame.time.Clock()
    pygame.mouse.set_visible(False)
    cursor_imagem = pygame.image.load("Sprites/Ponteiro.png").convert_alpha()
    cursor_tamanho = cursor_imagem.get_size()

    # Sprite de moeda
    sprite_moeda = pygame.image.load("Sprites/moeda.png").convert_alpha()

    # Cartas / Loja
    total_cartas_compradas = sum(cartas_compradas.values())
    custo_carta_atual = custo_base_carta + (total_cartas_compradas * custo_por_carta)

    running = True
    while running:
        agora = pygame.time.get_ticks()
        
        # Seleção instantânea sem alocação
        frames_disparo = frames_disparo_impulso if impulsiva_ativa else frames_disparo_normal
    
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
        tempo_fim_stun = estado_atual_ia.get('fim_stun', 0) if 'estado_atual_ia' in globals() else 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                memoria_umbra.salvar() 
                rodando = False
                pygame.quit()
                sys.exit(0)
            elif botao_mouse[0] and tempo_atual - tempo_ultimo_disparo >= intervalo_disparo and tempo_atual >= tempo_fim_stun:
                pos_mouse = pygame.mouse.get_pos()
                angulo = calcular_angulo_disparo((pos_x_personagem, pos_y_personagem), pos_mouse)
                Disparo_Geo.play()
                novo_disparo = {
                    "rect": pygame.Rect(pos_x_personagem, pos_y_personagem, largura_disparo, altura_disparo),
                    "angulo": angulo
                }
                disparos.append(novo_disparo)
                tempo_ultimo_disparo = tempo_atual  
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and tempo_atual - tempo_ultimo_uso_habilidade >= cooldown_habilidade and tempo_atual >= tempo_fim_stun:  
                pos_mouse = pygame.mouse.get_pos()
                angulo = calcular_angulo_disparo((pos_x_personagem, pos_y_personagem), pos_mouse)
                nova_onda = {
                    "rect": pygame.Rect(pos_x_personagem, pos_y_personagem, largura_onda, altura_onda),
                    "angulo": angulo,
                    "tempo_inicio": pygame.time.get_ticks(),
                    "frame_atual": 0,
                    "frames": frames_onda_cinetica  
                }
                ondas.append(nova_onda)
                tempo_ultimo_uso_habilidade = tempo_atual
        
        # Verificar eventos de teclado
        keys = pygame.key.get_pressed()


        # Joystick já inicializado antes do loop (cache)

        # Chamar a função para atualizar a posição do personagem
        ultimo_x = pos_x_personagem
        ultimo_y = pos_y_personagem
        tempo_atual = pygame.time.get_ticks()
        delta_time_ms = tempo_atual - tempo_ultimo_frame
        tempo_ultimo_frame = tempo_atual
        atualizar_posicao_personagem(keys,joystick)
    


        tempo_passado += relogio.get_rawtime()
        relogio.tick()

         # Adicionar inimigos a cada 10 segundos
        tempo_atual = pygame.time.get_ticks()

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
    

        if imune_tempo_restante > 0:
            imune_tempo_restante -= relogio.get_time()  
        else:
            imune_tempo_restante = 0 

    
    
            
        if not escudo_devota_ativo and tempo_atual - tempo_ultimo_escudo >= intervalo_escudo:
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
                agora_fim = pygame.time.get_ticks()
                tempo_inicio = estado_atual_ia.get('tempo_start_boss', agora_fim) if 'estado_atual_ia' in locals() else agora_fim
                duracao_combate = (agora_fim - tempo_inicio) / 1000.0
            
            
                # Reset do sistema de ratos
                gerenciador_ratos.resetar_partida()
         
                memoria_umbra.treinar(500.0, prioridade=True)
   
                mostrar_tutorial=False
                pygame.time.delay(2000)
                Musica_tema_fases.stop()
                Som_tema_fases.stop()
                memoria_umbra.salvar() 
                rodando = False
                pygame.quit()
                limpar_salvamento()
                subprocess.Popen([sys.executable, "Game_Over.py"])
                sys.exit(0)

        # Adicione esta verificação para controlar o piscar da barra de vida
        if piscando_vida:
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
                duracao_combate = (agora - estado_atual_ia.get('tempo_start_boss', agora)) / 1000.0
                agora_fim = pygame.time.get_ticks()
                tempo_inicio = estado_atual_ia.get('tempo_start_boss', agora_fim) if 'estado_atual_ia' in locals() else agora_fim
                duracao_combate = (agora_fim - tempo_inicio) / 1000.0
                memoria_umbra.treinar(-500.0, prioridade=True)
            
                # Reset do sistema de ratos
                gerenciador_ratos.resetar_partida()
            
                mostrar_tutorial = False
                pygame.time.delay(2000)
                Musica_tema_fases.stop()
                Som_tema_fases.stop()
                memoria_umbra.salvar() 
                rodando = False
                pygame.quit()
                limpar_salvamento()
                subprocess.Popen([sys.executable, "Game_Over.py"])
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
                    vida -= resultado_colisoes['dano_total']
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
                'hitbox_centro': hitbox_boss5.center if 'hitbox_boss5' in locals() or 'hitbox_boss5' in globals() else (pos_x_umbra + largura_boss // 2, pos_y_umbra + altura_boss // 2)
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
                        # Buffado: Aumentado em 40% em relação ao 0.035 original
                        valor_cura = (vida_maxima_umbra-vida_umbra) * 0.049
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
                        # Cálculos de atração vetorial e punição física
                        dx_v = vortice['x'] - pos_x_personagem
                        dy_v = vortice['y'] - pos_y_personagem
                        dist_v = math.hypot(dx_v, dy_v)
                    
                        if dist_v > 5:
                            fator_succao = vortice['forca'] * (1 - min(1, dist_v / 900))
                            pos_x_personagem += (dx_v / dist_v) * fator_succao
                            pos_y_personagem += (dy_v / dist_v) * fator_succao
                        
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
                        dx_sinal = sinal['velocidade'] * math.cos(sinal['angulo'])
                        dy_sinal = sinal['velocidade'] * math.sin(sinal['angulo'])
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
                    p["rect"].x += p["velocidade"] * math.cos(p["angulo"])
                    p["rect"].y += p["velocidade"] * math.sin(p["angulo"])

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
                    
                        dano_bruto = (200 + (inimigos_eliminados *0.05)) * multiplicador_dano_umbra
                        dano_recebido = int(dano_bruto - Resistencia)
                    
                        if dano_recebido < 0: 
                            dano_recebido = 0
                        
                        if aurea == "Impulsiva": 
                            eliminacoes_consecutivas_impulsiva = 0 
                        
                        if escudo_devota_ativo:
                            escudo_devota_ativo = False
                        else:
                            vida -= dano_recebido
                            eliminacoes_consecutivas = 0
                            bonus_pontuacao = 0
                            piscando_vida = True
                    
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
                            vida -= vida_maxima*0.01
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
                                vida -= descarga['dano_por_tick']
                                efeitos_texto.append({
                                    "texto": "SOBRECARGA!",
                                    "x": pos_x_personagem + random.randint(-20, 20),
                                    "y": pos_y_personagem - 30,
                                    "tempo_inicio": agora,
                                    "cor": (255, 255, 0)
                                })
                                memoria_umbra.treinar(2.0)
                            
                                # --- PUNIÇÃO APOLO: Choque e atordoamento ---
                        
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
                            vida -= 50
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
                            giro_total = math.pi * 2 # 360º
                            esp = [65, 35, 15, 6]
                            hitbox_r = 38
                        elif rodada == 2:
                            num_feixes = 2
                            sentido = -1
                            giro_total = math.pi * 2 # 360º cada braço, girando ao contrário
                            esp = [65, 35, 15, 6]
                            hitbox_r = 38
                        elif rodada == 3:
                            num_feixes = 4
                            sentido = 1
                            giro_total = math.pi * 0.8 # Gira lento (144º em 4s), criando um labirinto
                            esp = [65, 35, 15, 6]
                            hitbox_r = 38
                        else: # Rodada 4
                            num_feixes = 6
                            sentido = -1
                            giro_total = math.pi * 0.8 # Gira lento ao contrário
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
                                vida -= vida_maxima * 0.10
                            
                                # --- PUNIÇÃO APOLO: Ser atingido pelo laser principal ---

                                # --- MEMÓRIA ESPACIAL: Registra zona como perigosa no SafeZone Grid ---
                                col_laser_hit = int(pos_x_personagem / max(1, largura_mapa / 8))
                                row_laser_hit = int(pos_y_personagem / max(1, altura_mapa / 6))
                                key_laser_hit = (col_laser_hit, row_laser_hit)
                                
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
                if player_em_chamas:
                    if agora > tempo_fim_chamas:
                        player_em_chamas = False
                        multiplicador_chamas = 0
                    else:
                        # Aplica 2% da vida ATUAL por tick de 1 segundo, multiplicado pelas cargas
                        if agora - ultimo_tick_chamas >= 1000:
                            dano_chamas = vida * (0.02 * multiplicador_chamas)
                            vida -= dano_chamas
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
                
                    if tempo_na_dimensao > estado_atual_ia['duracao_dimensao'] and not em_transicao_mapa:
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
                    import random
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
                            efeitos_texto.append({"texto": "+500 DOPAMINA REWARD!", "x": pos_x_personagem, "y": pos_y_personagem - 50, "tempo_inicio": agora, "cor": (255, 215, 0)})
                        elif percentual_vida_antes < 0.6:  # Menos de 60% de vida
                            recompensa_coleta = 300.0  # RECOMPENSA MASSIVA
                            efeitos_texto.append({"texto": "+300 DOPAMINA REWARD!", "x": pos_x_personagem, "y": pos_y_personagem - 50, "tempo_inicio": agora, "cor": (255, 215, 0)})
                        else:
                            recompensa_coleta = 150.0  # RECOMPENSA ENORME MESMO COM VIDA CHEIA
                            efeitos_texto.append({"texto": "+150 DOPAMINA REWARD!", "x": pos_x_personagem, "y": pos_y_personagem - 50, "tempo_inicio": agora, "cor": (255, 215, 0)})
                    
                        efeitos_texto.append({
                            "texto": f"+{cura_aplicada} RESTAURAÇÃO!",
                            "x": pos_x_personagem,
                            "y": pos_y_personagem - 30,
                            "tempo_inicio": agora,
                            "cor": (0, 255, 150)
                        })
                    
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
    
        if estado_atual_ia.get('miasma_ativo'):
            tela.blit(imagem_personagem_doente, (pos_x_personagem, pos_y_personagem))
        else:
            frame_para_desenhar = frames_animacao[direcao_atual][frame_atual % len(frames_animacao[direcao_atual])]
            
            if angulo_inclinacao_personagem != 0:
                frame_rotacionado = pygame.transform.rotate(frame_para_desenhar, angulo_inclinacao_personagem)
                # O rect do frame original é obtido para não alterar o centro visual ao rotacionar
                rect_original = frame_para_desenhar.get_rect(topleft=(pos_x_personagem, pos_y_personagem))
                rect_rotacionado = frame_rotacionado.get_rect(center=rect_original.center)
                tela.blit(frame_rotacionado, rect_rotacionado.topleft)
            else:
                tela.blit(frame_para_desenhar, (pos_x_personagem, pos_y_personagem))
    
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
                            vida -= 5.0
                            vida_boss5 = min( vida_boss5 + 20)
                            estado_atual_ia['ratos_adicionais'] = estado_atual_ia.get('ratos_adicionais', 0) + 1
                            memoria_umbra.treinar(5.0)
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
            disparo["rect"].x += velocidade_disparo * math.cos(disparo["angulo"])
            disparo["rect"].y += velocidade_disparo * math.sin(disparo["angulo"])
        
            atingiu_boss = False
            interceptado = False
            if luta_iniciada:
                if disparo["rect"].colliderect(hitbox_boss5):

                    if random.random() <= chance_critico:
                        dano_final = dano_person_hit * 2
                        punicao = -4.0  # Dano crítico pune o dobro
                        cor_feedback = (255, 255, 0) # Amarelo Crítico
                    else:
                        dano_final = dano_person_hit
                        cor_feedback = (255, 255, 255) # Branco Normal

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
                        estado_atual_ia['carga_atrito'] = estado_atual_ia.get('carga_atrito', 0) + 8
                    
                        if estado_atual_ia['carga_atrito'] >= 100 and not estado_atual_ia.get('laser_ativo'):
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
                        vida_umbra -= dano_final
                        estado_atual_ia['dano_recente'] = estado_atual_ia.get('dano_recente', 0) + dano_final
                    
                        # --- NOVO MOTOR DE VFX: Desfragmentação de Impacto ---
                        # Impacto visual (simplificado)
                    
                        punicao = -2.0 
                    
                        # Punição por dano pós-teleporte (falha no reposicionamento)
                        if agora - estado_atual_ia.get('chegada_teleporte', 0) < 1500:
                            punicao -= 10.0 # Punição severa por apanhar logo após o salto
                        
                        memoria_umbra.treinar(punicao, prioridade=True)
    
                        if random.random() < roubo_de_vida:
                            cura_base = quantidade_roubo_vida
                        
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
                            dano_por_tick_veneno_boss = vida_maxima_umbra * (Dano_Veneno_Acumulado / 100)
                            tempo_inicio_veneno_boss = agora
                            ultimo_tick_veneno_boss = agora
                        # --- CORROSÃO: DANO CONTÍNUO DE VENENO ---
                        if boss_envenenado:
                            # Aplica o tick de dano a cada 500 milissegundos
                            if agora - ultimo_tick_veneno_boss >= 500:
                                vida_umbra -= dano_por_tick_veneno_boss
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
                        estado_atual_ia['tomou_tiro_no_dash'] = True


            # 5. Manutenção de Projéteis no Mapa
            dentro_mapa = 0 <= disparo["rect"].x < largura_mapa and 0 <= disparo["rect"].y < altura_mapa
            if dentro_mapa and not atingiu_boss and not interceptado:
                novos_disparos.append(disparo)
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
            pygame.draw.circle(tela, (255, 120, 0), disparo["rect"].center, 8)
            pygame.draw.circle(tela, (255, 255, 100), disparo["rect"].center, 4)

        # Atualizar e Desenhar Partículas de Desfragmentação (Globais)
        pass  # VFX update (simplificado)

        for moeda in moedas_soltadas[:]:
            if personagem_rect.colliderect(moeda["rect"]):
                moedas_coletadas += 1
                moedas_totais += 1   # acumula no total salvo
                moedas_soltadas.remove(moeda)
                salvar_atributos()   #salva imediatamente

        # Cap: maximos 12 efeitos simultaneos para evitar acumulo em combate
        if len(efeitos_texto) > 12:
            efeitos_texto = efeitos_texto[-12:]

        nova_lista = []
        for efeito in efeitos_texto:
            tempo_passado_efeito = tempo_atual - efeito["tempo_inicio"]
            if tempo_passado_efeito <= 800:
                if config_graficos.get("efeitos_visuais", True):
                    x = efeito["x"]
                    y = efeito["y"] - (tempo_passado_efeito // 25)
                    # Render feito UMA vez com a fonte cacheada (era Font(None,28) a cada frame!)
                    texto_principal = render_cached_text(efeito["texto"], _FONTE_EFEITO, efeito["cor"])
                    # Contorno: 1 render + 8 blits (era 8 renders separados)
                    contorno = render_cached_text(efeito["texto"], _FONTE_EFEITO, (0, 0, 0))
                    for ox, oy in _CONTORNO_OFFSETS:
                        tela.blit(contorno, (x + ox, y + oy))
                    tela.blit(texto_principal, (x, y))
                nova_lista.append(efeito)
        efeitos_texto = nova_lista

        if trembo:
            # Desenhar o segundo personagem ao lado do personagem original
            pos_x_segundo_personagem = pos_x_personagem + largura_personagem + 4
            pos_y_segundo_personagem = pos_y_personagem
            # Desenhar sombra do Trembo
            desenhar_sombra(tela, pos_x_segundo_personagem, pos_y_segundo_personagem, largura_personagem, altura_personagem)
            tela.blit(frames_animacao_trembo[direcao_atual][frame_atual % len(frames_animacao_trembo[direcao_atual])], (pos_x_segundo_personagem, pos_y_segundo_personagem))
        if trembo and tempo_atual - tempo_ultima_regeneracao >= Tempo_cura and vida < vida_maxima:
            cura_trembo = vida_maxima * porcentagem_cura
        
            # Mantendo a interceptação do Corta-Cura (Fase 6)
            if player_hemorragia_ativa and tempo_atual < tempo_fim_hemorragia:
                cura_trembo *= (1.0 - penalidade_cura_percentual)
            
            vida = min(vida_maxima, vida + cura_trembo)
            tempo_ultima_regeneracao = tempo_atual
        # --- OTIMIZACAO UI ---
        posicao_barra_vida = (80, altura_mapa - (altura_mapa - 34))
        total_cartas_compradas = sum(cartas_compradas.values())
        custo_carta_atual = custo_base_carta + (total_cartas_compradas * custo_por_carta)
    
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

        tela.blit(cursor_imagem, (mouse_x, mouse_y))
        exibir_cronometro(tela)
        
        pygame.display.flip()
        # 144 FPS: A IA já roda em processo separado (multiprocessing), não precisa de tick alto.
        # O tick(900) anterior fazia TODO o código Python rodar 900x/s, causando 80%+ CPU.
        FPS.tick(config_graficos.get("fps_limite", 60))


    # Encerrar o Pygame
    pygame.quit()
    sys.exit(0)