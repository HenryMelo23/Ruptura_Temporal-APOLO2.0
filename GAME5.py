import pygame
import sys
import random
import math
import time
import os
import sys
import json
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import webbrowser
from Tela_Cartas import tela_de_pausa
from Variaveis import *
from utils import *
import habilidade_boss as hb
import collections
from vfx_engine_apolo import ApoloVFXManager
from audio_manager import carregar_config_audio, aplicar_volume_som
from sistema_ratos_umbra import GerenciadorRatos

if __name__ == "__main__":
    import multiprocessing as mp
    mp.freeze_support()
    pygame.init()
    memoria_umbra = hb.MemoriaEvolutivaUmbra()
    vfx_apolo = ApoloVFXManager()

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

    app = Flask(__name__)
    CORS(app) # Permite que o navegador acesse os dados sem bloqueio de segurança

    @app.route('/dados')
    def exportar_telemetria():
        try:
            # Extrai o viés estatístico absoluto
            bias_x, bias_y = memoria_umbra.calcular_bias_bayesiano()
        
            # Resgata o estado exato que a IA está enxergando neste milissegundo
            estado_ativo = "DQN_TENSOR"
        
            # Mergulha na Matriz-Q para extrair os pesos reais formados pela dor e recompensa
            # Mergulha na Matriz-Q para extrair os pesos reais formados pela dor e recompensa
            pesos_reais = {}
            import torch
            if memoria_umbra.ultimo_estado_tensor is not None:
                with torch.no_grad():
                    memoria_umbra.q_network.eval()
                    q_vals = memoria_umbra.q_network(memoria_umbra.ultimo_estado_tensor)[0]
                    for i, acn in enumerate(memoria_umbra.acoes_base):
                        pesos_reais[acn] = round(float(q_vals[i]), 3)
            else:
                pesos_reais = estado_atual_ia.get('ultimos_pesos_calculados', {})

            payload = {
                "estado_atual": estado_ativo if estado_ativo else "CALCULANDO_VETORES",
                "decisao_ativa": estado_atual_ia.get('decisoes_ativas', []),
                "bias_bayesiano": [bias_x, bias_y],
                "rede_completa": {
                    estado_ativo: pesos_reais
                }
            }
            return jsonify(payload)
        except Exception as e:
            return jsonify({"erro": str(e)})
    def get_dados():
        return jsonify(dados_ia_umbra)

    def rodar_servidor_flask():
        # Roda o servidor na porta 5000 de forma silenciosa
        app.run(host='localhost', port=5000, debug=False, use_reloader=False)

    # Dispara o servidor em uma Thread comum
    threading.Thread(target=rodar_servidor_flask, daemon=True).start()

    def registrar_batalha(duracao_segundos, vencedor, hp_restante, exploracao, acertos, erros, habilidades_usadas):
        arquivo_historico = "historico_batalhas.json"
        historico = []
        if os.path.exists(arquivo_historico):
            try:
                with open(arquivo_historico, "r") as f:
                    historico = json.load(f)
            except:
                pass
            
        geracao = len(historico) + 1
    
        habilidade_favorita = "NENHUMA"
        if habilidades_usadas:
            habilidade_favorita = max(habilidades_usadas, key=habilidades_usadas.get)
        
        taxa_acerto = 0.0
        total_tiros = acertos + erros
        if total_tiros > 0:
            taxa_acerto = (acertos / total_tiros) * 100.0

        historico.append({
            "geracao": geracao,
            "duracao": duracao_segundos,
            "vencedor": vencedor,
            "hp_restante": hp_restante,
            "exploracao_umbra": exploracao,
            "habilidade_dominante": habilidade_favorita,
            "precisao_bayesiana": taxa_acerto
        })
    
        with open(arquivo_historico, "w") as f:
            json.dump(historico, f, indent=4)
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

        
    with open("aurea_selecionada.json", "r") as file:
        aurea = json.load(file)["aurea"]

    upgrade_aureas = carregar_upgrade_aureas("aureas_upgrade.json")

        
    tempo_inicial = time.time() 

    tempo_anterior = pygame.time.get_ticks()
    tempo_movimento = random.randint(2000, 7000)
    tempo_parado = random.randint(500, 700) 
    movendo = True 
    boss_vivo1=False
    relogio = pygame.time.Clock()
    ultimo_tempo_reducao = time.time()
    largura_disparo, altura_disparo = 40, 40
    velocidade_disparo = 10
    disparos = []

    tela = pygame.display.set_mode((largura_mapa, altura_mapa))
    pygame.display.set_caption("Renderizando Mapa com Personagem")

    pontuacao_inimigos=0
    maxima_pontuacao_magia = 750
    piscar_magia = False





    #INIMIGOS
    # Carregar a imagem do mapa
    mapa_atual_path = mapa_path5
    mapa = pygame.image.load(mapa_atual_path).convert()
    mapa = pygame.transform.scale(mapa, (largura_mapa, altura_mapa))

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


    #####################################################################APOLO1######################################################################################################
    def atualizar_posicao_personagem(keys, joystick):#APOLO
        global pos_x_personagem, pos_y_personagem, direcao_atual, ultima_tecla_movimento
        global movimento_pressionado, cooldown_dash, distancia_dash, tempo_ultimo_dash, teleporte_timer, teleporte_duration, teleporte_index
        global hitbox_boss5, estado_atual_ia, modo_ia_treino
        global tempo_ultimo_disparo, intervalo_disparo, disparos
        global vida, largura_disparo, altura_disparo

        dx, dy = 0, 0
        direcao_atual = 'stop'
    
        tempo_agora = pygame.time.get_ticks()
        tempo_fim_stun_ia = estado_atual_ia.get('fim_stun', 0) if 'estado_atual_ia' in globals() else 0
        atordoado = tempo_agora < tempo_fim_stun_ia

        if modo_ia_treino:
            lista_tiros_umbra = estado_atual_ia.get('projeteis', [])
            hitbox_alvo = hitbox_boss5 if 'hitbox_boss5' in globals() else None
        
            cds_ia = {
                "teleporte": cooldown_dash,
                "disparo": (tempo_agora - tempo_ultimo_disparo < intervalo_disparo)
            }
        
            vida_boss_atual = vida_umbra if 'vida_umbra' in globals() else 10000
        
            # Garante que a IA não colapse se a lista de esferas ainda não existir no escopo global
            lista_esferas = esferas_energia_umbra if 'esferas_energia_umbra' in globals() else []
        
            # Calcula velocidade atual do personagem
            velocidade_atual = math.hypot(dx, dy) * velocidade_personagem if (dx != 0 or dy != 0) else 0
        
            # Passa estado_atual_ia para o Apolo ter consciência das armadilhas
            estado_ia_ref = estado_atual_ia if 'estado_atual_ia' in globals() else None

            apolo.pensar((pos_x_personagem, pos_y_personagem), hitbox_alvo, lista_tiros_umbra, cds_ia, vida, vida_boss_atual, lista_esferas, velocidade_atual, estado_ia_ref)
            dx, dy = apolo.direcao_x, apolo.direcao_y
        
            if dx > 0: ultima_tecla_movimento = 'right'
            elif dx < 0: ultima_tecla_movimento = 'left'
            if dy > 0: ultima_tecla_movimento = 'down'
            elif dy < 0: ultima_tecla_movimento = 'up'

            if apolo.mouse_simulado[0] and tempo_agora >= tempo_fim_stun_ia:
                angulo = calcular_angulo_disparo((pos_x_personagem, pos_y_personagem), (apolo.alvo_x, apolo.alvo_y))
                Disparo_Geo.play()
                disparos.append({
                    "rect": pygame.Rect(pos_x_personagem, pos_y_personagem, largura_disparo, altura_disparo),
                    "angulo": angulo
                })
                tempo_ultimo_disparo = tempo_agora

        else:
            if keys[config_teclas["Mover para direita"]]: dx, ultima_tecla_movimento = 1, 'right'
            elif keys[config_teclas["Mover para esquerda"]]: dx, ultima_tecla_movimento = -1, 'left'
            if keys[config_teclas["Mover para cima"]]: dy, ultima_tecla_movimento = -1, 'up'
            elif keys[config_teclas["Mover para baixo"]]: dy, ultima_tecla_movimento = 1, 'down'

        if dx != 0 or dy != 0:
            movimento_pressionado = True
            direcao_atual = ultima_tecla_movimento
        
            # NORMALIZAÇÃO DE MOVIMENTO DIAGONAL E INCLINAÇÃO
            if dx != 0 and dy != 0:
                inclinacao = angulo_diagonal_personagem
                
                if dy < 0:
                    angulo_inclinacao_personagem = -inclinacao if dx > 0 else inclinacao
                else:
                    angulo_inclinacao_personagem = inclinacao if dx > 0 else -inclinacao
                    
                # Fator de normalização para diagonal: 1/sqrt(2) ≈ 0.7071
                fator_normalizacao = 0.7071
                pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                             pos_x_personagem + dx * velocidade_personagem * fator_normalizacao))
                pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                             pos_y_personagem + dy * velocidade_personagem * fator_normalizacao))
            else:
                angulo_inclinacao_personagem = 0
                # Movimento cardinal (apenas uma direção)
                pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                             pos_x_personagem + dx * velocidade_personagem))
                pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                             pos_y_personagem + dy * velocidade_personagem))
        else:
            angulo_inclinacao_personagem = 0

        ia_precisa_dash = modo_ia_treino and getattr(apolo, 'usar_dash', False)
    
        if (keys[config_teclas["Teleporte"]] or ia_precisa_dash) and cooldown_dash == False and atordoado == False:
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
                    if 'apolo' in globals() and hasattr(apolo, 'encerrar'):
                        apolo.encerrar()
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
                    elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        nome = aureas[selecionado]["nome"]
                        if aureas[selecionado]["ativa"] and nome != "?":
                            if moedas_disponiveis > 0:
                                upgrades[nome] += 1
                                moedas_disponiveis -= 1
                                salvar_upgrade_aureas("aureas_upgrade.json", upgrades)


                                # 🪙 salva o novo total no arquivo de atributos
                                with open("atributos.json", "r") as f:
                                    atributos = json.load(f)
                                atributos["moedas_totais"] = moedas_disponiveis
                                with open("atributos.json", "w") as f:
                                    json.dump(atributos, f)

                    elif evento.key == pygame.K_ESCAPE:
                        return

            for i, aurea in enumerate(aureas):
                linha = i // colunas
                coluna = i % colunas

                x = largura // 2 - ((colunas * largura_quadro + (colunas - 1) * espacamento) // 2) + coluna * (largura_quadro + espacamento)
                y = altura // 4 + linha * (altura_quadro + 30)

                cor_borda = (255, 255, 255) if i == selecionado else (80, 80, 80)
                pygame.draw.rect(tela, cor_borda, (x, y, largura_quadro, altura_quadro), 3)

                # Texto com nome
                cor_texto = cor_borda
                nome_display = aurea["nome"]
                if nome_display != "?" and upgrades.get(nome_display, 0) > 0:
                    nome_display += f" (Nv. {upgrades[nome_display]})"

                texto = fonte.render(nome_display, True, cor_texto)
                tela.blit(texto, (x + largura_quadro // 2 - texto.get_width() // 2, y - 25))

            

                # Texto com nível
                if aurea["ativa"] and aurea["nome"] != "?":
                    nivel = upgrades.get(aurea["nome"], 0)
                    texto_nivel = fonte.render(f"Nível {nivel}", True, (200, 200, 100))
                    tela.blit(texto_nivel, (x + largura_quadro // 2 - texto_nivel.get_width() // 2, y + altura_quadro + 5))

                # Imagem
                try:
                    imagem = pygame.image.load(aurea["imagem"]).convert_alpha()
                    imagem = pygame.transform.scale(imagem, (largura_quadro, altura_quadro))
                    tela.blit(imagem, (x, y))
                except:
                    pass

            # Mostrar moedas
            texto_moedas = fonte.render(f"Moedas: {moedas_disponiveis}", True, (255, 255, 100))
            tela.blit(texto_moedas, (50, 40))

            instrucoes = fonte.render("← → para navegar | ENTER para melhorar | ESC para sair", True, (150, 150, 150))
            tela.blit(instrucoes, (largura // 2 - instrucoes.get_width() // 2, altura - 60))

            pygame.display.flip()
            clock.tick(60)


    # Variáveis Globais de Mutação da Umbra
    multiplicador_dano_umbra = 1.0
    reducao_cooldown_umbra = 1.0
    resistencia_umbra = 0.0
    bonus_cura_sifon = 0.5

    tempo_parado_person = pygame.time.get_ticks()  
    boss_atingido_por_onda = pygame.time.get_ticks()
    tempo_ultimo_disparo = pygame.time.get_ticks()
    tempo_ultimo_escudo = pygame.time.get_ticks()

    Som_tema_fases.play(loops=-1)
    Musica_tema_fases.play(loops=-1)

    upgrades = carregar_upgrade_aureas("aureas_upgrade.json")

    FPS=pygame.time.Clock()
    pygame.mouse.set_visible(False)
    cursor_imagem = pygame.image.load("Sprites/Ponteiro.png").convert_alpha()  # Ajuste o caminho
    cursor_tamanho = cursor_imagem.get_size()

    sprite_moeda = pygame.image.load("Sprites/moeda.png").convert_alpha()
    moedas_soltadas = []

    modo_ia_treino = True

    #####################################################################APOLO1######################################################################################################

    import torch
    import torch.nn as nn
    import torch.optim as optim
    torch.set_num_threads(1) # OTIMIZAÇÃO: Impede PyTorch de sugar 100% da CPU em redes minúsculas

    # Importa arquitetura e buffer do modulo central (mesma rede do treino offline)
    from apolo_brain import (
        ApoloDQN, ApoloAgent, MiniReplayBuffer,
        INPUT_SIZE, OUTPUT_SIZE, GerenciadorArquitetura,
    )

    class AgenteApolo:
        """Wrapper de jogo sobre ApoloAgent (apolo_brain). Cuida de percepcao e recompensas online."""
        def __init__(self):
            self.direcao_x = 0
            self.direcao_y = 0
            self.usar_dash = False
            self.mouse_simulado = [False, False, False]
            self.alvo_x = 0
            self.alvo_y = 0

            # Action Repetition / frame skip adaptativo
            self.frames_pulo            = 6   # normal (laser inativo)
            self.frames_pulo_emergencia = 2   # emergencia (laser < 100px, projétil < 80px)
            self.frame_atual_skip       = 0
            self.frames_acao_atual      = 0   # contador legado (compatibilidade)
            self.acao_persistente       = 8
            self.foco_orbe              = None

            # Tracking de recompensas acumuladas entre skips
            self.bonus_dopamina       = 0.0
            self.ultimo_estado_tensor = None
            self.acao_anterior        = 0

            # Tracking de vida para reward shaping (delta de vida entre frames)
            self.vida_jogador_anterior = 0
            self.vida_boss_anterior    = 0

            # Memoria de posicoes para recompensa de evasao
            self.ultima_dist_perp_laser  = None
            self.laser_estava_carregando = False
            self.ultima_pos_umbra_conhecida = (1000, 500)
            self.ultima_vida_b_conhecida    = 1200
            self.frames_sobrevividos     = 0

            # =================================================================
            # MEMORIA DO LASER — estruturas de conhecimento da fase do laser
            # =================================================================
            # SafeZone Grid 8x6: rastreia quais regioes do mapa sao seguras
            # durante o laser. Chave: (col, row), Valor: [safe_count, hit_count]
            self.safe_zone_grid = {}

            # Historico de padroes de laser por rodada:
            # {rodada: {'angulo_inicio': float, 'sentido': int, 'vezes_visto': int}}
            # Apolo memoriza onde CADA rodada começa para antecipar a rotacao
            self.historico_laser_rodada = {}

            # Ultima rodada registrada (para detectar mudanca de rodada)
            self._ultima_rodada_laser = 0

            # Contador de frames consecutivos sobrevivendo ao laser disparando
            # (recompensa de sobrevivencia crescente)
            self.frames_no_laser = 0

            # Ultima posicao safe confirmada (usada como fallback de navegacao)
            self.ultima_pos_segura = None

            # Registro de seguranca do destino de dash (resultado da ultima verificacao)
            self._dash_destino_seguro = None
            self._dash_direcao_segura = None

            import multiprocessing as mp
            import torch
            from apolo_brain import motor_cognitivo_worker
            self.device = torch.device("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
            self.fila_estados = mp.Queue()
            self.fila_acoes = mp.Queue()
            self.evento_salvar = mp.Event()
            self.worker_process = mp.Process(
                target=motor_cognitivo_worker,
                args=(self.fila_estados, self.fila_acoes, self.evento_salvar),
                daemon=True
            )
            self.worker_process.start()
            self.esperando_acao = False
            self.taxa_exploracao = 0.50 # Fixo para telemetria externa

            self.atualizar_foco_progressivo()

        # Removido property pois a exploração agora é interna ao worker

        def carregar_memoria(self):
            """Alias legado — ApoloAgent ja carrega no __init__."""
            pass

        def salvar_memoria(self):
            import time, os
            target = "apolo_memoria_dqn.pt"
            mtime_antes = os.path.getmtime(target) if os.path.exists(target) else 0
            self.evento_salvar.set()
            t0 = time.time()
            while time.time() - t0 < 10.0:
                if os.path.exists(target) and os.path.getmtime(target) > mtime_antes:
                    print("[APOLO] Memoria salva com sucesso.")
                    return
                time.sleep(0.1)
            print("[APOLO] AVISO: Timeout ao salvar memoria — worker pode estar travado.")

        def encerrar(self):
            if hasattr(self, 'worker_process') and self.worker_process.is_alive():
                self.worker_process.terminate()
                self.worker_process.join(timeout=1.0)

        def aplicar_recompensa_direta(self, recompensa_direta):
            """Adiciona recompensa imediata ao pool de dopamina (processada no proximo skip)."""
            self.bonus_dopamina += recompensa_direta

        def _log_decisao(self, tipo, mensagem):
            import pygame
            agora = pygame.time.get_ticks()
            if not hasattr(self, '_ultimos_logs'):
                self._ultimos_logs = {}
            
            # Usa as primeiras 3 palavras da mensagem como chave para evitar spam
            # quando a IA alterna entre múltiplas mensagens no mesmo tipo
            palavras = mensagem.split()
            assinatura = " ".join(palavras[:3]) if len(palavras) >= 3 else mensagem
            chave = f"{tipo}_{assinatura}"
            
            ultimo_tempo = self._ultimos_logs.get(chave, 0)
            if agora - ultimo_tempo > 2000:
                print(f"[APOLO - {tipo}] {mensagem}")
                self._ultimos_logs[chave] = agora

        def receber_dano_punitivo(self, hits, multiplicador_base=50.0):
            import time
            agora = time.time()
            if agora - getattr(self, 'tempo_ultimo_dano', 0) < 2.0:
                self.combo_dano_sofrido = getattr(self, 'combo_dano_sofrido', 0) + hits
            else:
                self.combo_dano_sofrido = hits
            self.tempo_ultimo_dano = agora
            
            penalidade = (multiplicador_base * hits) * (1.5 ** (self.combo_dano_sofrido - 1))
            self.aplicar_recompensa_direta(-penalidade)

        def atualizar_foco_progressivo(self):
            import os, json
            try:
                if os.path.exists("historico_batalhas.json"):
                    with open("historico_batalhas.json", "r") as f:
                        geracoes = len(json.load(f))
                    # Decay mais lento: 0.992^n (vs 0.985 anterior)
                    self.taxa_exploracao = max(0.05, 0.40 * (0.992 ** geracoes))
            except:
                pass

        def verificar_seguranca_dash(self, px, py, laser, boss_hitbox, distancia_dash):
            """
            Analisa os 4 destinos possiveis do dash (cima/baixo/esq/dir) e retorna
            o mais seguro em relacao ao laser atual.

            Retorna: {'seguro': bool, 'direcao': str, 'melhor_dist': float}
            onde 'direcao' e a tecla de movimento ('up'/'down'/'left'/'right')
            e 'melhor_dist' e a distancia perpendicular do destino ao feixe mais proximo.
            """
            if not boss_hitbox or not laser or laser.get('fase') != 'disparando':
                return {'seguro': False, 'direcao': None, 'melhor_dist': 0}

            rodada = laser.get('rodada', 1)
            if rodada == 1:   num_feixes, sentido, giro_total = 1,  1, math.pi * 2
            elif rodada == 2: num_feixes, sentido, giro_total = 2, -1, math.pi * 2
            elif rodada == 3: num_feixes, sentido, giro_total = 4,  1, math.pi * 0.8
            else:             num_feixes, sentido, giro_total = 6, -1, math.pi * 0.8

            agora = pygame.time.get_ticks()
            t_disp = agora - laser.get('tempo_inicio_disparo', agora)
            duracao = laser.get('duracao_disparo', 4000)
            progresso = min(1.0, t_disp / duracao)
            angulo_base = laser.get('angulo_base_inicio', 0.0) + giro_total * progresso * sentido
            origem = (boss_hitbox.centerx, boss_hitbox.centery)

            # Estima posicao do feixe daqui a ~200ms (tempo de execucao do dash)
            progresso_futuro = min(1.0, (t_disp + 200) / duracao)
            angulo_futuro = laser.get('angulo_base_inicio', 0.0) + giro_total * progresso_futuro * sentido

            def dist_minima_ao_laser(dest_x, dest_y, ang_base_usado):
                """Distancia perpendicular minima de (dest_x, dest_y) a todos os feixes."""
                menor = float('inf')
                for i in range(num_feixes):
                    ang = ang_base_usado + i * ((math.pi * 2) / num_feixes)
                    fim_x = origem[0] + math.cos(ang) * 2500
                    fim_y = origem[1] + math.sin(ang) * 2500
                    num = abs((fim_y - origem[1]) * dest_x - (fim_x - origem[0]) * dest_y +
                              fim_x * origem[1] - fim_y * origem[0])
                    den = math.hypot(fim_y - origem[1], fim_x - origem[0])
                    dist = num / den if den > 0 else 9999
                    # Verifica se o destino esta NA FRENTE do feixe
                    dot = (dest_x - origem[0]) * math.cos(ang) + (dest_y - origem[1]) * math.sin(ang)
                    if dot > 0:
                        menor = min(menor, dist)
                return menor

            # Candidatos de dash: 4 direcoes cardinais
            candidatos = {
                'up':    (px, max(0, py - distancia_dash)),
                'down':  (px, min(altura_mapa - 1, py + distancia_dash)),
                'left':  (max(0, px - distancia_dash), py),
                'right': (min(largura_mapa - 1, px + distancia_dash), py),
            }

            melhor_dir = None
            melhor_dist = 0.0

            for direcao, (dest_x, dest_y) in candidatos.items():
                dist_no_futuro = dist_minima_ao_laser(dest_x, dest_y, angulo_futuro)

                # Consulta o historico do SafeZone Grid para este destino
                col = int(dest_x / max(1, largura_mapa / 8))
                row = int(dest_y / max(1, altura_mapa / 6))
                hist = self.safe_zone_grid.get((col, row), [0, 0])
                bonus_hist = 20.0 if hist[0] > hist[1] and hist[0] > 3 else 0.0
                penalidade_hist = -30.0 if hist[1] > hist[0] and hist[1] > 2 else 0.0

                score = dist_no_futuro + bonus_hist + penalidade_hist

                if score > melhor_dist:
                    melhor_dist = score
                    melhor_dir = direcao

            # Considera seguro se a melhor distancia ao feixe futuro for > 80px
            eh_seguro = (melhor_dist >= 80.0)
            return {'seguro': eh_seguro, 'direcao': melhor_dir, 'melhor_dist': melhor_dist}

        def encontrar_alvo_seguro_grid(self, px, py, projeteis, ratos, boss_hitbox, laser):
            import math
            import numpy as np
            tamanho_celula = 80
            cols = largura_mapa // tamanho_celula
            rows = altura_mapa // tamanho_celula
            
            col_atual = int(px / tamanho_celula)
            row_atual = int(py / tamanho_celula)
            
            c_min, c_max = max(0, col_atual - 3), min(cols, col_atual + 4)
            r_min, r_max = max(0, row_atual - 3), min(rows, row_atual + 4)
            
            if c_max <= c_min or r_max <= r_min:
                return (px, py)
                
            C, R = np.meshgrid(np.arange(c_min, c_max), np.arange(r_min, r_max))
            CX = C * tamanho_celula + tamanho_celula // 2
            CY = R * tamanho_celula + tamanho_celula // 2
            SCORE = np.zeros_like(CX, dtype=np.float32)
            
            # 1. Projéteis
            if projeteis:
                px_arr = np.array([p['rect'].centerx if 'rect' in p else p.get('x', px) for p in projeteis])
                py_arr = np.array([p['rect'].centery if 'rect' in p else p.get('y', py) for p in projeteis])
                dx = CX[..., np.newaxis] - px_arr
                dy = CY[..., np.newaxis] - py_arr
                dist_proj = np.min(np.hypot(dx, dy), axis=-1)
                mask = dist_proj < 120
                SCORE[mask] -= (120 - dist_proj[mask]) * 5.0

            # 2. Ratos
            if ratos:
                rx_arr = np.array([r.pos_x for r in ratos])
                ry_arr = np.array([r.pos_y for r in ratos])
                dx = CX[..., np.newaxis] - rx_arr
                dy = CY[..., np.newaxis] - ry_arr
                dist_rato = np.min(np.hypot(dx, dy), axis=-1)
                mask = dist_rato < 150
                SCORE[mask] -= (150 - dist_rato[mask]) * 3.0

            # 3. Kiting Umbra e LoS
            origem_laser = (boss_hitbox.centerx, boss_hitbox.centery) if boss_hitbox else (largura_mapa//2, altura_mapa//2)
            dist_boss = np.hypot(CX - origem_laser[0], CY - origem_laser[1])
            SCORE[dist_boss < 200] -= (200 - dist_boss[dist_boss < 200]) * 2.0
            SCORE[dist_boss > 600] -= (dist_boss[dist_boss > 600] - 600) * 0.5
            
            ang_umbra_apolo = math.atan2(py - origem_laser[1], px - origem_laser[0])
            ang_umbra_celula = np.arctan2(CY - origem_laser[1], CX - origem_laser[0])
            diff_ang = np.abs(ang_umbra_apolo - ang_umbra_celula)
            diff_ang[diff_ang > math.pi] = 2 * math.pi - diff_ang[diff_ang > math.pi]
            mask_ang = diff_ang < 0.35
            SCORE[mask_ang] -= (0.35 - diff_ang[mask_ang]) * 500.0

            # 4. Laser Rotativo
            laser_disparando = laser and laser.get('fase') == 'disparando'
            if laser_disparando:
                import pygame
                agora = pygame.time.get_ticks()
                t_disp = agora - laser.get('tempo_inicio_disparo', agora)
                duracao_disp = laser.get('duracao_disparo', 4000)
                progresso = min(1.0, t_disp / duracao_disp)
                prog_futuro = min(1.0, (t_disp + 400.0) / duracao_disp)
                rodada = laser.get('rodada', 1)
                num_feixes, sentido, giro_total = 1, 1, math.pi * 2
                if rodada == 2: num_feixes, sentido = 2, -1
                elif rodada == 3: num_feixes, giro_total = 4, math.pi * 0.8
                elif rodada == 4: num_feixes, sentido, giro_total = 6, -1, math.pi * 0.8
                
                angulo_base = laser.get('angulo_base_inicio', 0.0) + giro_total * progresso * sentido
                ang_base_futuro = laser.get('angulo_base_inicio', 0.0) + giro_total * prog_futuro * sentido
                
                menor_dist_laser = np.full_like(CX, np.inf)
                em_frente = np.zeros_like(CX, dtype=bool)
                
                for i in range(num_feixes):
                    ang_atual = angulo_base + i * ((math.pi * 2) / num_feixes)
                    ang_futuro = ang_base_futuro + i * ((math.pi * 2) / num_feixes)
                    
                    for ang_teste in [ang_atual, ang_futuro]:
                        cos_ang = math.cos(ang_teste)
                        sin_ang = math.sin(ang_teste)
                        fim_x = origem_laser[0] + cos_ang * 2500
                        fim_y = origem_laser[1] + sin_ang * 2500
                        
                        num_val = np.abs((fim_y - origem_laser[1])*CX - (fim_x - origem_laser[0])*CY + fim_x*origem_laser[1] - fim_y*origem_laser[0])
                        den = math.hypot(fim_y - origem_laser[1], fim_x - origem_laser[0])
                        dist_l = num_val / den if den > 0 else 9999
                        dot = (CX - origem_laser[0]) * cos_ang + (CY - origem_laser[1]) * sin_ang
                        
                        mask_frente = dot > 0
                        em_frente |= mask_frente
                        menor_dist_laser = np.where(mask_frente & (dist_l < menor_dist_laser), dist_l, menor_dist_laser)
                        
                    ang_ponto = np.arctan2(CY - origem_laser[1], CX - origem_laser[0])
                    diff_pt = np.arctan2(np.sin(ang_ponto - ang_atual), np.cos(ang_ponto - ang_atual))
                    diff_ft = np.arctan2(np.sin(ang_futuro - ang_atual), np.cos(ang_futuro - ang_atual))
                    mask_sweep = (diff_pt * diff_ft > 0) & (np.abs(diff_pt) <= np.abs(diff_ft))
                    
                    menor_dist_laser[mask_sweep] = 0.0
                    em_frente |= mask_sweep
                    
                mask_laser = em_frente & (menor_dist_laser < 180)
                mask_fatal = mask_laser & (menor_dist_laser < 50)
                mask_dano = mask_laser & ~mask_fatal
                SCORE[mask_fatal] -= np.inf
                SCORE[mask_dano] -= (180 - menor_dist_laser[mask_dano]) * 15.0

            # 5. Distância Apolo e Bordas
            dist_apolo = np.hypot(CX - px, CY - py)
            SCORE -= dist_apolo * 0.2
            mask_borda = (CX < 100) | (CX > largura_mapa - 100) | (CY < 100) | (CY > altura_mapa - 100)
            SCORE[mask_borda] -= 50.0
            
            idx = np.argmax(SCORE)
            return (int(CX.flat[idx]), int(CY.flat[idx]))


        def obter_estado_expandido(self, pos_p, boss_hitbox, projeteis_boss, cds, esferas_energia, vida_apolo, vida_boss, velocidade_apolo, estado_ia):
            import math
            import pygame
            agora = pygame.time.get_ticks()
            px, py = pos_p
        
            # Inteligência de Miasma: Apolo pode ficar "cego"
            visao_umbra = True
            if estado_ia and estado_ia.get('miasma_ativo'):
                if agora % 3000 < 2000:
                    visao_umbra = False
                
            bx, by = largura_mapa // 2, altura_mapa // 2
        
            if not visao_umbra and hasattr(self, 'ultima_pos_umbra_conhecida'):
                bx, by = self.ultima_pos_umbra_conhecida
                vida_b_calc = self.ultima_vida_b_conhecida
            else:
                if boss_hitbox:
                    bx, by = boss_hitbox.centerx, boss_hitbox.centery
                    self.ultima_pos_umbra_conhecida = (bx, by)
                    self.ultima_vida_b_conhecida = vida_boss
                vida_b_calc = vida_boss
            
            feat_px = px / max(1, largura_mapa)
            feat_py = py / max(1, altura_mapa)
            feat_bx = bx / max(1, largura_mapa)
            feat_by = by / max(1, altura_mapa)
        
            feat_vida_p = vida_apolo / 1000.0
            feat_vida_b = vida_b_calc / 1200.0
        
            # NOVO: Features de proximidade das bordas (CRÍTICO para evitar sair do mapa)
            margem_perigo = 100  # Pixels de margem considerados perigosos
        
            # Distância até cada borda (normalizado 0-1, onde 0 = na borda, 1 = longe)
            feat_dist_borda_esquerda = min(1.0, px / margem_perigo)
            feat_dist_borda_direita = min(1.0, (largura_mapa - px) / margem_perigo)
            feat_dist_borda_cima = min(1.0, py / margem_perigo)
            feat_dist_borda_baixo = min(1.0, (altura_mapa - py) / margem_perigo)
        
            # Detecta se está em canto (situação crítica)
            em_canto = 0.0
            if (px < margem_perigo and py < margem_perigo) or \
               (px > largura_mapa - margem_perigo and py < margem_perigo) or \
               (px < margem_perigo and py > altura_mapa - margem_perigo) or \
               (px > largura_mapa - margem_perigo and py > altura_mapa - margem_perigo):
                em_canto = 1.0
        
            dist_perigo = 1.0
            dx_perigo = 0.0
            dy_perigo = 0.0
            projeteis_proximos = []
            # Dados do projetil mais proximo (DodgeGate precisa da VELOCIDADE, nao apenas posicao)
            proj_vel_x    = 0.0   # direcao de DESLOCAMENTO do projetil — x
            proj_vel_y    = 0.0   # direcao de DESLOCAMENTO do projetil — y
            proj_approaching = 0.0  # 1.0 se projetil se aproxima de Apolo

            for proj in projeteis_boss:
                if 'rect' in proj:
                    proj_x, proj_y = proj['rect'].centerx, proj['rect'].centery
                else:
                    proj_x, proj_y = proj.get('x', px), proj.get('y', py)
                d = math.hypot(proj_x - px, proj_y - py)
                if d < 250:
                    projeteis_proximos.append((proj_x, proj_y, d, proj))

            if projeteis_proximos:
                proj_x, proj_y, d, proj_ref = min(projeteis_proximos, key=lambda p: p[2])
                dist_perigo = d / 250.0

                # Velocidade do projetil: usa angulo se disponivel, senao estima da posicao
                if 'angulo' in proj_ref:
                    ang = proj_ref['angulo']
                    proj_vel_x = math.cos(ang)
                    proj_vel_y = math.sin(ang)
                elif 'vel_x' in proj_ref and 'vel_y' in proj_ref:
                    speed = math.hypot(proj_ref['vel_x'], proj_ref['vel_y'])
                    if speed > 0:
                        proj_vel_x = proj_ref['vel_x'] / speed
                        proj_vel_y = proj_ref['vel_y'] / speed
                else:
                    # Fallback: estima que o projetil vem do boss em direcao a Apolo
                    bx2 = proj_x - (largura_mapa // 2)
                    by2 = proj_y - (altura_mapa // 2)
                    spd = math.hypot(bx2, by2)
                    if spd > 0:
                        proj_vel_x = bx2 / spd
                        proj_vel_y = by2 / spd

                # Verifica se o projetil esta se aproximando: dot(vel, apolo-proj) > 0
                apolo_menos_proj_x = px - proj_x
                apolo_menos_proj_y = py - proj_y
                dot_appr = proj_vel_x * apolo_menos_proj_x + proj_vel_y * apolo_menos_proj_y
                proj_approaching = 1.0 if dot_appr > 0 else 0.0

            # dx_perigo / dy_perigo agora sao as features de velocidade do projetil
            dx_perigo = proj_vel_x
            dy_perigo = proj_vel_y

            
            feat_cd_tele = 1.0 if cds.get('teleporte', False) else 0.0
        
            feat_armadilhas = [0.0] * 8
            if estado_ia:
                keys = ['vortice_ativo', 'prisao_ativa', 'caminho_espinhos', 'laser_ativo', 'descarga_eletrica', 'miasma_ativo', 'praga_ratos', 'parede_ativa']
                for i, k in enumerate(keys):
                    if estado_ia.get(k): feat_armadilhas[i] = 1.0
        
            feat_vel_p = min(1.0, velocidade_apolo / 15.0)
        
            # NOVO: Features expandidas para orbes de vida
            qtd_esferas = len(esferas_energia) if esferas_energia else 0
            feat_esferas_qtd = min(1.0, qtd_esferas / 10.0)
        
            # Distância até a orbe mais próxima
            feat_dist_orbe_proxima = 1.0  # 1.0 = muito longe ou não existe
            feat_dir_orbe_x = 0.0
            feat_dir_orbe_y = 0.0
        
            if esferas_energia and len(esferas_energia) > 0:
                orbes_com_distancia = []
                for orbe in esferas_energia:
                    ox, oy = orbe.get('x', px), orbe.get('y', py)
                    dist_orbe = math.hypot(ox - px, oy - py)
                    orbes_com_distancia.append((ox, oy, dist_orbe))
            
                if orbes_com_distancia:
                    ox_prox, oy_prox, dist_prox = min(orbes_com_distancia, key=lambda o: o[2])
                    feat_dist_orbe_proxima = min(1.0, dist_prox / 800.0)  # Normaliza até 800 pixels
                    if dist_prox > 0:
                        feat_dir_orbe_x = (ox_prox - px) / dist_prox  # Direção normalizada
                        feat_dir_orbe_y = (oy_prox - py) / dist_prox
        
            # NOVO: Features para ratos (ameaça adicional)
            feat_qtd_ratos = 0.0
            feat_dist_rato_proximo = 1.0  # 1.0 = muito longe ou não existe
            feat_dir_rato_x = 0.0
            feat_dir_rato_y = 0.0
        
            # Obtém lista de ratos do gerenciador global
            if 'gerenciador_ratos' in globals():
                ratos_ativos = gerenciador_ratos.ratos
                feat_qtd_ratos = min(1.0, len(ratos_ativos) / 20.0)  # Normaliza até 20 ratos
            
                if len(ratos_ativos) > 0:
                    ratos_com_distancia = []
                    for rato in ratos_ativos:
                        rx, ry = rato.pos_x, rato.pos_y
                        dist_rato = math.hypot(rx - px, ry - py)
                        ratos_com_distancia.append((rx, ry, dist_rato))
                
                    if ratos_com_distancia:
                        rx_prox, ry_prox, dist_prox = min(ratos_com_distancia, key=lambda r: r[2])
                        feat_dist_rato_proximo = min(1.0, dist_prox / 600.0)  # Normaliza até 600 pixels
                        if dist_prox > 0:
                            feat_dir_rato_x = (rx_prox - px) / dist_prox  # Direção do rato mais próximo
                            feat_dir_rato_y = (ry_prox - py) / dist_prox
        
            # [17] proj_approaching: 1.0 se projetil se aproxima de Apolo (DodgeGate)
            # (substitui feat_vel_b que era menos critico)
            feat_vel_b = proj_approaching

        
            # SISTEMA EXPANDIDO DE PERCEPÇÃO DO LASER (CRÍTICO para sobrevivência)
            feat_laser_fase = 0.0  # 0 = inativo, 0.5 = carregando, 1.0 = disparando
            feat_laser_rodada = 0.0  # Normalizado 0-1 (rodada/4)
            feat_laser_progresso = 0.0  # Progresso da fase atual (0-1)
            feat_laser_num_feixes = 0.0  # Normalizado 0-1 (num_feixes/6)
            feat_laser_sentido_rotacao = 0.0  # -1 = anti-horário, 0 = parado, 1 = horário
            feat_laser_velocidade_angular = 0.0  # Velocidade de rotação normalizada
            feat_laser_angulo_mais_proximo = 0.0  # Ângulo do feixe mais próximo (-1 a 1)
            feat_laser_dist_feixe_proximo = 1.0  # Distância ao feixe mais próximo (0-1)
            feat_laser_tempo_ate_atingir = 1.0  # Tempo estimado até feixe atingir posição (0-1)
        
            if estado_ia:
                vx_b = estado_ia.get('vel_x', 0)
                vy_b = estado_ia.get('vel_y', 0)
                feat_vel_b = min(1.0, math.hypot(vx_b, vy_b) / 5.0)
            
                laser = estado_ia.get('laser_ativo')
                if laser:
                    # Fase do laser
                    if laser.get('fase') == 'carregando':
                        feat_laser_fase = 0.5
                        tempo_laser = agora - laser['tempo_inicio']
                        feat_laser_progresso = min(1.0, tempo_laser / laser['duracao_carga'])
                    elif laser.get('fase') == 'disparando':
                        feat_laser_fase = 1.0
                        t_disp = agora - laser['tempo_inicio_disparo']
                        feat_laser_progresso = min(1.0, t_disp / laser['duracao_disparo'])
                
                    # Rodada atual (1-4)
                    rodada = laser.get('rodada', 1)
                    feat_laser_rodada = rodada / 4.0
                
                    # Configuração por rodada (mesma lógica do código original)
                    if rodada == 1:
                        num_feixes = 1
                        sentido = 1
                        giro_total = math.pi * 2
                    elif rodada == 2:
                        num_feixes = 2
                        sentido = -1
                        giro_total = math.pi * 2
                    elif rodada == 3:
                        num_feixes = 4
                        sentido = 1
                        giro_total = math.pi * 0.8
                    else:  # Rodada 4
                        num_feixes = 6
                        sentido = -1
                        giro_total = math.pi * 0.8
                
                    feat_laser_num_feixes = num_feixes / 6.0
                    feat_laser_sentido_rotacao = sentido  # -1 ou 1
                
                    # Velocidade angular (radianos por segundo, normalizado)
                    if laser.get('fase') == 'disparando':
                        duracao_disparo = laser.get('duracao_disparo', 4000)
                        velocidade_angular = giro_total / (duracao_disparo / 1000.0)  # rad/s
                        feat_laser_velocidade_angular = min(1.0, abs(velocidade_angular) / (2 * math.pi))

                        # Calcular posição dos feixes usando angulo_base_inicio real
                        if boss_hitbox:
                            origem_laser = (boss_hitbox.centerx, boss_hitbox.centery)
                            ang_base_real = laser.get('angulo_base_inicio', 0.0)
                            angulo_base   = ang_base_real + giro_total * feat_laser_progresso * sentido

                            menor_dist   = float('inf')
                            ang_proximo  = 0.0
                            ang_2nd      = 0.0
                            dist_2nd     = float('inf')
                            feixes_info  = []  # (dist, ang) de cada feixe na frente

                            for i in range(num_feixes):
                                angulo_atual = angulo_base + i * ((math.pi * 2) / num_feixes)

                                # Calcula ponto final do feixe
                                comp_laser = 2500
                                fim_x = origem_laser[0] + math.cos(angulo_atual) * comp_laser
                                fim_y = origem_laser[1] + math.sin(angulo_atual) * comp_laser

                                # Distancia perpendicular do player a linha do laser
                                numerador   = abs((fim_y - origem_laser[1])*px - (fim_x - origem_laser[0])*py +
                                                 fim_x*origem_laser[1] - fim_y*origem_laser[0])
                                denominador = math.hypot(fim_y - origem_laser[1], fim_x - origem_laser[0])
                                dist_linha  = numerador / denominador if denominador > 0 else 9999

                                # Verifica se esta na frente do laser
                                dot = (px - origem_laser[0]) * math.cos(angulo_atual) + \
                                      (py - origem_laser[1]) * math.sin(angulo_atual)
                                if dot > 0:
                                    feixes_info.append((dist_linha, angulo_atual))

                            # Ordena por distancia para achar 1o e 2o feixes
                            feixes_info.sort(key=lambda x: x[0])
                            if feixes_info:
                                menor_dist  = feixes_info[0][0]
                                ang_proximo = feixes_info[0][1]
                            if len(feixes_info) >= 2:
                                dist_2nd = feixes_info[1][0]
                                ang_2nd  = feixes_info[1][1]

                            # --- FEATURE [24]: signed approach angle (substituiu sin ambiguo) ---
                            # Positivo = feixe se aproximando de mim na direcao de rotacao
                            # Negativo = feixe se afastando / ja passou
                            ang_player = math.atan2(py - origem_laser[1], px - origem_laser[0])
                            diff1 = ang_player - ang_proximo
                            while diff1 >  math.pi: diff1 -= 2 * math.pi
                            while diff1 < -math.pi: diff1 += 2 * math.pi
                            signed_approach = max(-1.0, min(1.0, (diff1 * sentido) / math.pi))
                            feat_laser_angulo_mais_proximo = signed_approach

                            # --- FEATURE [26]: cos do angulo do feixe mais proximo ---
                            feat_laser_tempo_ate_atingir = math.cos(ang_proximo)

                            # Normaliza features de distancia
                            feat_laser_dist_feixe_proximo = min(1.0, menor_dist / 400.0)

                            # --- FEATURES GEOMETRICAS [30-33]: identicas ao treino ---
                            # [30] fuga_x: componente X do vetor perpendicular ao feixe (direcao de fuga)
                            ang_fuga = ang_proximo + (math.pi / 2) * sentido
                            feat_fuga_x = math.cos(ang_fuga)
                            feat_fuga_y = math.sin(ang_fuga)

                            # [32] in_sweep_zone: 1 se o player ainda sera varrido pelo laser nesta rodada
                            ang_restante = giro_total * (1.0 - feat_laser_progresso)
                            diff_sweep = diff1 * sentido  # quanto falta ate o feixe chegar ao player
                            if diff_sweep < 0: diff_sweep += 2 * math.pi
                            in_sweep_zone = 1.0 if 0 < diff_sweep <= ang_restante else 0.0

                            # [33] signed approach do 2o feixe mais proximo
                            if dist_2nd < float('inf'):
                                diff2 = ang_player - ang_2nd
                                while diff2 >  math.pi: diff2 -= 2 * math.pi
                                while diff2 < -math.pi: diff2 += 2 * math.pi
                                signed_2nd = max(-1.0, min(1.0, (diff2 * sentido) / math.pi))
                            else:
                                signed_2nd = -1.0  # sem 2o feixe = seguro
        
            # ==============================================================
            # FEATURES GEOMETRICAS DO LASER (ativas apenas quando disparando)
            # Posicoes 30-33 sao identicas entre treino e jogo
            # ==============================================================
            if estado_ia and estado_ia.get('laser_ativo') and \
               estado_ia['laser_ativo'].get('fase') == 'disparando' and boss_hitbox:
                # Variaveis ja calculadas no bloco acima
                pass  # feat_fuga_x, feat_fuga_y, in_sweep_zone, signed_2nd definidos acima
            else:
                feat_fuga_x    = 0.0
                feat_fuga_y    = 0.0
                in_sweep_zone  = 0.0
                signed_2nd     = -1.0  # seguro por padrao

            features = [feat_px, feat_py, feat_bx, feat_by, feat_vida_p, feat_vida_b,
                       feat_dist_borda_esquerda, feat_dist_borda_direita, feat_dist_borda_cima, feat_dist_borda_baixo, em_canto,
                       dist_perigo, dx_perigo, dy_perigo, feat_cd_tele, feat_vel_p, feat_esferas_qtd, feat_vel_b,
                       feat_laser_fase, feat_laser_rodada, feat_laser_progresso, feat_laser_num_feixes,
                       feat_laser_sentido_rotacao, feat_laser_velocidade_angular, feat_laser_angulo_mais_proximo,
                       feat_laser_dist_feixe_proximo, feat_laser_tempo_ate_atingir,
                       feat_dist_orbe_proxima, feat_dir_orbe_x, feat_dir_orbe_y,
                       feat_fuga_x, feat_fuga_y, in_sweep_zone, signed_2nd] + feat_armadilhas

            tensor = torch.tensor(features, dtype=torch.float32, device=self.device).unsqueeze(0)
            return tensor

        def pensar(self, pos_p, boss_hitbox, projeteis_boss, cds, vida_jogador, vida_boss, esferas_energia, velocidade_atual=5, estado_ia=None):
            import random
            import math  # Movido para o início para estar disponível em todo o método
            agora = pygame.time.get_ticks()  # Necessário para cálculos de tempo do laser
        
            self.direcao_x = 0
            self.direcao_y = 0
            self.usar_dash = False
            self.mouse_simulado[0] = False
            self.frames_sobrevividos += 1
        
            px, py = pos_p  # Define px e py no início para uso em todo o método
        
            # --- MIRA MATEMÁTICA PREDITIVA (Igual ao da Umbra) ---
            tx, ty = px, py
            vx, vy = 0.0, 0.0
            # Apolo usa a última memória para mirar no escuro, se aplicável
            if hasattr(self, 'ultima_pos_umbra_conhecida'):
                tx, ty = self.ultima_pos_umbra_conhecida
            elif boss_hitbox:
                tx, ty = boss_hitbox.centerx, boss_hitbox.centery
            
            if estado_ia:
                vx = estado_ia.get('vel_x', 0.0)
                vy = estado_ia.get('vel_y', 0.0)
            
            distancia = math.hypot(tx - px, ty - py)
            tempo_bala = max(1.0, distancia / 10.0) # Velocidade da bala de Apolo = 10
        
            self.alvo_x = tx + (vx * tempo_bala * 0.7) # Trava 70% na velocidade do alvo simulando predição
            self.alvo_y = ty + (vy * tempo_bala * 0.7)
        
            if cds.get("disparo", False) == False and boss_hitbox is not None: 
                self.mouse_simulado[0] = True

            # --- HIERARQUIA DE PRIORIDADE: VIDA VS RISCO (custo-beneficio) ---
            # A Umbra pode ser ignorada quando morrer de falta de HP e mais provavel
            # do que morrer pelo projetil. Apolo aprende que a orbe e SAGRADA.
            perigo_iminente = False
            raio_perigo = 80

            # --- RECOMPUTO LOCAL DAS VARIAVEIS DE PROJETIL (necessarias em pensar) ---
            # (obter_estado_expandido calcula as mesmas, mas sao locais daquele metodo)
            dist_perigo       = 1.0
            proj_vel_x        = 0.0
            proj_vel_y        = 0.0
            proj_approaching  = 0.0
            projeteis_proximos = []

            for _proj in projeteis_boss:
                _px_p = _proj['rect'].centerx if 'rect' in _proj else _proj.get('x', px)
                _py_p = _proj['rect'].centery if 'rect' in _proj else _proj.get('y', py)
                _d    = math.hypot(_px_p - px, _py_p - py)
                if _d < 250:
                    projeteis_proximos.append((_px_p, _py_p, _d, _proj))

            if projeteis_proximos:
                _pp_x, _pp_y, _pd, _pref = min(projeteis_proximos, key=lambda p: p[2])
                dist_perigo = _pd / 250.0
                if 'angulo' in _pref:
                    _ang = _pref['angulo']
                    proj_vel_x = math.cos(_ang)
                    proj_vel_y = math.sin(_ang)
                elif 'vel_x' in _pref and 'vel_y' in _pref:
                    _spd = math.hypot(_pref['vel_x'], _pref['vel_y'])
                    if _spd > 0:
                        proj_vel_x = _pref['vel_x'] / _spd
                        proj_vel_y = _pref['vel_y'] / _spd
                _dot = proj_vel_x * (px - _pp_x) + proj_vel_y * (py - _pp_y)
                proj_approaching = 1.0 if _dot > 0 else 0.0

            # 1. Mede o perigo real do projetil (urgencia de evasao)
            dist_proj_atual = float('inf')
            for proj in projeteis_boss:
                px_proj = proj['rect'].centerx if 'rect' in proj else proj.get('x', px)
                py_proj = proj['rect'].centery if 'rect' in proj else proj.get('y', py)
                d_proj  = math.hypot(px_proj - px, py_proj - py)
                if d_proj < dist_proj_atual:
                    dist_proj_atual = d_proj
                if d_proj < raio_perigo:
                    perigo_iminente = True
                    break

            if estado_ia and estado_ia.get('laser_ativo') and estado_ia['laser_ativo'].get('fase') == 'carregando':
                perigo_iminente = True

            # 2. Calcula custo de cada risco
            vida_frac_atual = vida_jogador / 1000.0
            # Custo de morrer sem HP: quadratico — escala rapido com pouca vida
            custo_morrer_sem_hp = ((max(0.0, 0.80 - vida_frac_atual) / 0.80) ** 2) * 3.5
            # Custo do projetil: maximo 2.0 quando tocando e vindo direto
            proj_appr_atual = proj_approaching if projeteis_proximos else 0.0
            custo_dano_proj  = (1.0 - min(1.0, dist_proj_atual / 250.0)) * proj_appr_atual * 2.0


            # 3. Se morrer sem HP for mais perigoso: IGNORAR a Umbra e buscar a orbe
            orbe_mais_urgente = (custo_morrer_sem_hp > custo_dano_proj)

            if perigo_iminente and not orbe_mais_urgente:
                self.foco_orbe = None  # Perigo real supera urgencia de HP — evadir!
            
            # 4. Gatilho de Assuncao de Controle: busca orbe se precisar E nao ha laser
            laser_ativo = estado_ia.get('laser_ativo') if estado_ia else None
            laser_disparando = laser_ativo and laser_ativo.get('fase') == 'disparando'
            # Com laser disparando, o DQN deve cuidar da evasao; busca orbe so se critico
            limiar_orbe = 600 if not laser_disparando else 300  # 60% normal, 30% com laser
            if vida_jogador < limiar_orbe and esferas_energia and (not perigo_iminente or orbe_mais_urgente):
                # Escolhe orbe que maximiza (urgencia / distancia): melhor custo-beneficio
                melhor_orbe = None
                melhor_score = -1.0
                for o in esferas_energia:
                    ox_o = o['rect'].centerx if 'rect' in o else o.get('x', px)
                    oy_o = o['rect'].centery if 'rect' in o else o.get('y', py)
                    d_o  = math.hypot(ox_o - px, oy_o - py) + 1.0
                    # Urgencia temporal: orbe mais nova tem mais tempo, prioriza a que esta sumindo
                    t_criacao = o.get('tempo_criacao', agora)
                    tempo_restante_ms = max(0, 15000 - (agora - t_criacao))
                    fator_urgencia_tempo = 1.0 + max(0.0, (5000 - tempo_restante_ms) / 5000) * 2.0  # ate 3x nos ultimos 5s
                    score = fator_urgencia_tempo / d_o  # prioriza orbe sumindo E perto
                    if score > melhor_score:
                        melhor_score = score
                        melhor_orbe  = (ox_o, oy_o)
                if melhor_orbe:
                    self.foco_orbe = melhor_orbe
                    self._log_decisao("COLETAR_ORBE", f"Decidiu coletar orbe em {melhor_orbe}. Motivo: Vida crítica ({vida_jogador} < {limiar_orbe}). Custo morte ({custo_morrer_sem_hp:.2f}) > Custo Projétil ({custo_dano_proj:.2f})")
            
            # 5. Definicao de Target e Execucao de Smooth Steering (Grid Mapping)
            target_x, target_y = px, py
            ratos_ativos = []
            if 'gerenciador_ratos' in globals():
                ratos_ativos = gerenciador_ratos.ratos
            
            # Prioridade Máxima: Orbe (se necessário)
            if self.foco_orbe and (not perigo_iminente or orbe_mais_urgente):
                target_x, target_y = self.foco_orbe
                if math.hypot(target_x - px, target_y - py) < 30:
                    self.foco_orbe = None # Coletou
            else:
                # Prioridade Normal: Escolhe o quadrado mais seguro do Grid
                target_x, target_y = self.encontrar_alvo_seguro_grid(px, py, projeteis_boss, ratos_ativos, boss_hitbox, laser_ativo)
            
            dist_target = math.hypot(target_x - px, target_y - py)
        
            # Se não for o laser dominando tudo (verificado logo abaixo), Apolo vai para o Target
            if dist_target > 15:
                # Alinhamento de eixos: se alinhado, não aperta botões desnecessários
                if target_x > px + 10: self.direcao_x = 1
                elif target_x < px - 10: self.direcao_x = -1
                else: self.direcao_x = 0
            
                if target_y > py + 10: self.direcao_y = 1
                elif target_y < py - 10: self.direcao_y = -1
                else: self.direcao_y = 0
                
                self._log_decisao("MOVIMENTO", f"Indo para {'Orbe' if self.foco_orbe else 'Alvo Seguro'} em {target_x:.0f},{target_y:.0f}. Distância: {dist_target:.0f}")
            else:
                bx = boss_hitbox.centerx if boss_hitbox else px
                by = boss_hitbox.centery if boss_hitbox else py
                ang_umbra = math.atan2(py - by, px - bx)
                ang_orbital = ang_umbra + 1.5708
                self.direcao_x = 1 if math.cos(ang_orbital) > 0 else -1
                self.direcao_y = 1 if math.sin(ang_orbital) > 0 else -1
                self._log_decisao("MOVIMENTO", "Orbitando próximo ao alvo (dist_target < 15)")
            
                # Evasão Dinâmica Ativa (Obstacle Avoidance)
                # Se o grid escolheu um caminho, mas algo se moveu para frente, desvia levemente
                for _px_p, _py_p, _d, _proj in projeteis_proximos:
                    if _d < 70:
                        # Se estou movendo só em X e tem bala, dou step em Y
                        if self.direcao_x != 0 and self.direcao_y == 0:
                            self.direcao_y = 1 if py < _py_p else -1
                        # Se estou movendo só em Y e tem bala, dou step em X
                        elif self.direcao_y != 0 and self.direcao_x == 0:
                            self.direcao_x = 1 if px < _px_p else -1

                # Dash Inteligente para o Target
                vida_critica = vida_jogador < 300
                if (dist_target > 150 or (self.foco_orbe and vida_critica)) and cds.get("dash", False) == False:
                    self.usar_dash = True
                    motivo_dash = "Distância alta ao alvo seguro" if dist_target > 150 else "Vida crítica buscando orbe"
                    self._log_decisao("TELEPORTE", f"Dash acionado. Motivo: {motivo_dash} (dist: {dist_target:.0f})")
                
                # Interrupção de Fluxo: Apolo ignora a tremedeira do DQN e usa Smooth Steering
                # (A não ser que o Laser Hardwired abaixo decida dominar por urgência extrema)
                return

            # =================================================================
            # HIERARQUIA DE PRIORIDADE — LASER DOMINA TODAS AS OUTRAS DECISOES
            # Executado ANTES do DQN para garantir evasao geometricamente correta
            # =================================================================
            laser_ativo_pensar = estado_ia.get('laser_ativo') if estado_ia else None
            laser_disparando_pensar = laser_ativo_pensar and laser_ativo_pensar.get('fase') == 'disparando'

            if laser_disparando_pensar and boss_hitbox:
                rodada_p = laser_ativo_pensar.get('rodada', 1)
                if rodada_p == 1:   num_f_p, sent_p, giro_p = 1,  1, math.pi * 2
                elif rodada_p == 2: num_f_p, sent_p, giro_p = 2, -1, math.pi * 2
                elif rodada_p == 3: num_f_p, sent_p, giro_p = 4,  1, math.pi * 0.8
                else:               num_f_p, sent_p, giro_p = 6, -1, math.pi * 0.8

                t_disp_p = agora - laser_ativo_pensar.get('tempo_inicio_disparo', agora)
                dur_p = laser_ativo_pensar.get('duracao_disparo', 4000)
                prog_p = min(1.0, t_disp_p / dur_p)
                ang_base_p = laser_ativo_pensar.get('angulo_base_inicio', 0.0) + giro_p * prog_p * sent_p
                orig_p = (boss_hitbox.centerx, boss_hitbox.centery)

                # Registra padrao deste laser na memoria episodica
                rodada_id = rodada_p
                if rodada_id != self._ultima_rodada_laser:
                    self._ultima_rodada_laser = rodada_id
                    info_rodada = self.historico_laser_rodada.get(rodada_id, {})
                    self.historico_laser_rodada[rodada_id] = {
                        'angulo_inicio': laser_ativo_pensar.get('angulo_base_inicio', 0.0),
                        'sentido': sent_p,
                        'vezes_visto': info_rodada.get('vezes_visto', 0) + 1
                    }

                # Calcula distancia perpendicular de Apolo ao feixe mais proximo
                menor_dist_p = float('inf')
                ang_feixe_mais_proximo = 0.0
                em_frente_p = False
                for i in range(num_f_p):
                    ang_p = ang_base_p + i * ((math.pi * 2) / num_f_p)
                    fim_xp = orig_p[0] + math.cos(ang_p) * 2500
                    fim_yp = orig_p[1] + math.sin(ang_p) * 2500
                    num_p = abs((fim_yp - orig_p[1]) * px - (fim_xp - orig_p[0]) * py +
                                 fim_xp * orig_p[1] - fim_yp * orig_p[0])
                    den_p = math.hypot(fim_yp - orig_p[1], fim_xp - orig_p[0])
                    dist_p = num_p / den_p if den_p > 0 else 9999
                    dot_p = (px - orig_p[0]) * math.cos(ang_p) + (py - orig_p[1]) * math.sin(ang_p)
                    if dot_p > 0:
                        em_frente_p = True
                        if dist_p < menor_dist_p:
                            menor_dist_p = dist_p
                            ang_feixe_mais_proximo = ang_p

                # Inicializa Histerese se não existir
                if not hasattr(self, 'histerese_frames_laser'):
                    self.histerese_frames_laser = 0
                    self.histerese_dir_x = 0
                    self.histerese_dir_y = 0

                # PRIORIDADE MAXIMA: feixe a menos de 180px e Apolo esta na frente
                if em_frente_p and menor_dist_p < 180:
                    self.frames_no_laser += 1

                    # (Ponto 6) Órbita Dinâmica Preditiva
                    dist_radial = math.hypot(px - orig_p[0], py - orig_p[1])
                    ang_apolo = math.atan2(py - orig_p[1], px - orig_p[0])
                    ang_tangente = ang_apolo + (math.pi / 2) * sent_p
                
                    raio_ancora = 350.0
                    erro_radial = raio_ancora - dist_radial
                
                    fuga_x_p = math.cos(ang_tangente) + math.cos(ang_apolo) * (erro_radial * 0.015)
                    fuga_y_p = math.sin(ang_tangente) + math.sin(ang_apolo) * (erro_radial * 0.015)
                
                    mag = math.hypot(fuga_x_p, fuga_y_p)
                    if mag > 0:
                        fuga_x_p /= mag
                        fuga_y_p /= mag

                    # Verifica se dash esta disponivel e leva a zona segura
                    if not cds.get('teleporte', False):
                        resultado_dash = self.verificar_seguranca_dash(
                            px, py, laser_ativo_pensar, boss_hitbox, distancia_dash
                        )
                        if resultado_dash['seguro'] and resultado_dash['direcao']:
                            # Dash para zona segura — DECISAO PERFEITA
                            dir_dash = resultado_dash['direcao']
                            if dir_dash == 'up': ultima_tecla_movimento = 'up'
                            elif dir_dash == 'down': ultima_tecla_movimento = 'down'
                            elif dir_dash == 'left': ultima_tecla_movimento = 'left'
                            elif dir_dash == 'right': ultima_tecla_movimento = 'right'
                            self.usar_dash = True
                            self._dash_destino_seguro = True
                            self._dash_direcao_segura = dir_dash
                            self._log_decisao("TELEPORTE", f"Dash acionado no Laser. Motivo: Fuga perfeita para zona segura na direção {dir_dash}. Menor dist feixe: {menor_dist_p:.2f}")
                        
                            # (Ponto 1) Behavior Cloning (Macro Comando 0: Safe/Flee)
                            estado_t = self.obter_estado_expandido(pos_p, boss_hitbox, projeteis_boss, cds, esferas_energia, vida_jogador, vida_boss, velocidade_atual, estado_ia)
                            if self.ultimo_estado_tensor is not None:
                                self.fila_estados.put(("TREINAR", (
                                    self.ultimo_estado_tensor, self.acao_anterior, self.bonus_dopamina, estado_t, False
                                )))
                            self.ultimo_estado_tensor = estado_t
                            self.acao_anterior = 0
                            self.bonus_dopamina = 0.0
                            return

                    # Atualiza ultima posicao segura confirmada (pre-perigo)
                    if menor_dist_p > 120:
                        self.ultima_pos_segura = (px, py)

                    # (Ponto 5) Histerese de Controle (Fim do Tremor)
                    # Ativa o override direcional agressivo se em extremo perigo (< 60) ou se a histerese estiver ativa
                    if menor_dist_p < 60 or self.histerese_frames_laser > 0:
                        if menor_dist_p < 60:
                            self.histerese_frames_laser = 15 # Trava a ação por 15 frames
                            self.histerese_dir_x = 1 if fuga_x_p > 0.15 else (-1 if fuga_x_p < -0.15 else 0)
                            self.histerese_dir_y = 1 if fuga_y_p > 0.15 else (-1 if fuga_y_p < -0.15 else 0)
                            self._log_decisao("MOVIMENTO", f"Histerese ativada! Extrema proximidade do laser ({menor_dist_p:.2f}px < 60px). Trava de direção: {self.histerese_dir_x}, {self.histerese_dir_y}")
                        else:
                            self.histerese_frames_laser -= 1
                        
                            # Se já está longe o suficiente e não tem mais perigo, cancela a histerese cedo
                            if menor_dist_p > 100:
                                self.histerese_frames_laser = 0
                            
                        self.direcao_x = self.histerese_dir_x
                        self.direcao_y = self.histerese_dir_y
                    
                        # Se ainda estiver rodando o override mecânico, clona o comportamento
                        if self.histerese_frames_laser > 0:
                            estado_t = self.obter_estado_expandido(pos_p, boss_hitbox, projeteis_boss, cds, esferas_energia, vida_jogador, vida_boss, velocidade_atual, estado_ia)
                            if self.ultimo_estado_tensor is not None:
                                self.fila_estados.put(("TREINAR", (
                                    self.ultimo_estado_tensor, self.acao_anterior, self.bonus_dopamina, estado_t, False
                                )))
                            self.ultimo_estado_tensor = estado_t
                            self.acao_anterior = 0 # Macro Comando: Fuga
                            self.bonus_dopamina = 0.0
                            return
                else:
                    # Laser ativo mas longe — contabiliza sobrevivencia e atualiza SafeZone
                    if not em_frente_p or menor_dist_p >= 180:
                        self.frames_no_laser += 1
                        # Posicao atual e segura — registra no grid
                        col_safe = int(px / max(1, largura_mapa / 8))
                        row_safe = int(py / max(1, altura_mapa / 6))
                        key_safe = (col_safe, row_safe)
                        if key_safe not in self.safe_zone_grid:
                            self.safe_zone_grid[key_safe] = [0, 0]
                        self.safe_zone_grid[key_safe][0] += 1
            # RECOMPENSA EXPANDIDA (Bellman Equation - Erradicação do Reward Hacking)
            # =================================================================
            recompensa = 0.5  # Sobrevivência base
            recompensa += getattr(self, 'bonus_dopamina', 0.0) # Adiciona bônus transitórios acumulados
            self.bonus_dopamina = 0.0 # Zera para não somar duplo no prox frame
        
            delta_vida_apolo = 0
            delta_vida_boss = 0
        
            if self.vida_jogador_anterior > 0:
                delta_vida_apolo = vida_jogador - self.vida_jogador_anterior
                delta_vida_boss = vida_boss - self.vida_boss_anterior

            if delta_vida_apolo < 0:
                agora_dano = pygame.time.get_ticks()
                if not hasattr(self, '_t_ultimo_dano'):
                    self._t_ultimo_dano = 0
                    self._mult_dano = 1.0
                if agora_dano - self._t_ultimo_dano < 2000:
                    self._mult_dano = min(10.0, self._mult_dano * 1.5)
                else:
                    self._mult_dano = 1.0
                self._t_ultimo_dano = agora_dano
                recompensa -= 150 * self._mult_dano
            if delta_vida_boss < 0:
                recompensa += 50 # Boss tomou dano
            qtd_atual = len(esferas_energia)
            qtd_ant = getattr(self, '_qtd_orbes_anterior', qtd_atual)
            
            # Flag explícita: setada APENAS pelo código de coleta real (game loop)
            orbe_coletada = getattr(self, '_orbe_coletada_neste_frame', False)
            self._orbe_coletada_neste_frame = False  # Reset para próximo frame
            
            if orbe_coletada:
                recompensa += 5000 # Coletou Orbe (Recompensa densa absoluta - VÍCIO)
                self._log_decisao("DOPAMINA", "DOPAMINA EXTREMA! Orbe coletada (+5000)")
            
            # Punição severa se orbe desaparecer enquanto precisava (sem coleta)
            if qtd_ant > qtd_atual and not orbe_coletada:
                recompensa -= 1000 # Orbe perdida (Crise de abstinência forte)
                self._log_decisao("DOPAMINA", "Crise de Abstinência! Orbe sumiu e não foi pega (-1000)")

            # Fissura contínua: induzir Apolo a pegar orbes o mais rápido possível
            if qtd_atual > 0:
                recompensa -= 2.0 # Cada frame que a orbe está viva e ele não pegou, sofre penalidade leve

            self._qtd_orbes_anterior = qtd_atual
            self.vida_jogador_anterior = vida_jogador
            self.vida_boss_anterior = vida_boss

            # OBTER ESTADO EXPANDIDO
            estado_tensor = self.obter_estado_expandido(
                pos_p, boss_hitbox, projeteis_boss, cds, esferas_energia,
                vida_jogador, vida_boss, velocidade_atual, estado_ia
            )

            if self.ultimo_estado_tensor is not None:
                self.bonus_dopamina += recompensa # Acumula recompensas

            # Macro Comandos Disponíveis: 0 (Safe/Flee), 1 (Orb), 2 (Attack/Kite)
            acoes_validas = [0, 1, 2]
        
            # SISTEMA DE PERSISTÊNCIA DE AÇÃO
            self.frames_acao_atual += 1
            forcar_nova_decisao = False
        
            if estado_ia and estado_ia.get('laser_ativo') and estado_ia['laser_ativo'].get('fase') == 'disparando':
                forcar_nova_decisao = True
            
            frames_pulo_atual = self.frames_pulo_emergencia if forcar_nova_decisao else self.frames_pulo
            self.frame_atual_skip += 1

            if self.frame_atual_skip >= frames_pulo_atual or forcar_nova_decisao:
                if self.ultimo_estado_tensor is not None:
                    recompensa_final = self.bonus_dopamina
                    self.bonus_dopamina = 0.0
                    self.fila_estados.put(("TREINAR", (
                        self.ultimo_estado_tensor,
                        self.acao_anterior,
                        recompensa_final,
                        estado_tensor,
                        False
                    )))

                if not self.esperando_acao:
                    self.fila_estados.put(("INFERIR", (estado_tensor, acoes_validas)))
                    self.esperando_acao = True
                    self.frame_atual_skip = 0
                    self.ultimo_estado_tensor = estado_tensor

            if not self.fila_acoes.empty():
                self.acao_persistente = self.fila_acoes.get()
                self.acao_anterior = self.acao_persistente
                self.esperando_acao = False

            acao = self.acao_persistente

            vmx, vmy = 0.0, 0.0
            
            # INDUÇÃO DO DQN: Apolo escolhe a ação 1 (Orbe) ou a regra de desespero entra como rodinhas de treino
            if esferas_energia:
                mo = min(esferas_energia, key=lambda o: math.hypot((o.get('rect', {}).centerx if 'rect' in o else o.get('x', px)) - px, (o.get('rect', {}).centery if 'rect' in o else o.get('y', py)) - py))
                ox = mo.get('rect', {}).centerx if 'rect' in mo else mo.get('x', px)
                oy = mo.get('rect', {}).centery if 'rect' in mo else mo.get('y', py)
                dist_orbe_atual = math.hypot(ox - px, oy - py)
                
                # Recompensa contínua de aproximação se a IA decidiu ir pra orbe (Shaping)
                if not hasattr(self, '_dist_orbe_anterior'): self._dist_orbe_anterior = dist_orbe_atual
                delta_dist = self._dist_orbe_anterior - dist_orbe_atual
                if acao == 1 and delta_dist > 0:
                    self.aplicar_recompensa_direta(delta_dist * 3.0) # Vício em chegar mais perto
                    
                self._dist_orbe_anterior = dist_orbe_atual
                
                # O movimento vai para a orbe se o DQN decidir (acao == 1) OU (temporário) se vida quase zerada
                quer_orbe = (acao == 1) or (vida_jogador < 200) 
                
                if quer_orbe:
                    dx, dy = ox - px, oy - py
                    mag = math.hypot(dx, dy)
                    if mag > 0: vmx, vmy = (dx / mag) * 3.0, (dy / mag) * 3.0
                    self._log_decisao("DQN_ACAO", f"Ação 1 (Orbe) ativa! Movendo para Orbe. Distância: {mag:.0f}")
                else:
                    ra = gerenciador_ratos.ratos if 'gerenciador_ratos' in globals() else []
                    tx, ty = self.encontrar_alvo_seguro_grid(px, py, projeteis_boss, ra, boss_hitbox, laser_ativo_pensar)
                    dx, dy = tx - px, ty - py
                    mag = math.hypot(dx, dy)
                    if mag > 0: vmx, vmy = dx / mag, dy / mag
            else:
                if hasattr(self, '_dist_orbe_anterior'):
                    del self._dist_orbe_anterior
                ra = gerenciador_ratos.ratos if 'gerenciador_ratos' in globals() else []
                tx, ty = self.encontrar_alvo_seguro_grid(px, py, projeteis_boss, ra, boss_hitbox, laser_ativo_pensar)
                dx, dy = tx - px, ty - py
                mag = math.hypot(dx, dy)
                if mag > 0: vmx, vmy = dx / mag, dy / mag
            vex, vey = 0.0, 0.0
            for p in projeteis_boss:
                pxp = p.get('rect', {}).centerx if 'rect' in p else p.get('x', px)
                pyp = p.get('rect', {}).centery if 'rect' in p else p.get('y', py)
                dp = math.hypot(pxp - px, pyp - py)
                if dp < 200:
                    ang = p.get('angulo', 0)
                    vpx, vpy = p.get('vel_x', math.cos(ang)*10), p.get('vel_y', math.sin(ang)*10)
                    spd = math.hypot(vpx, vpy)
                    if spd > 0:
                        nx, ny = vpx / spd, vpy / spd
                        if nx * (px - pxp) + ny * (py - pyp) > 0:
                            fc = max(1.0, dp / spd)
                            o1x, o1y = -ny, nx
                            o2x, o2y = ny, -nx
                            bx, by = (o1x, o1y) if (o1x*vmx + o1y*vmy) > (o2x*vmx + o2y*vmy) else (o2x, o2y)
                            pe = min(3.0, 15.0 / fc)
                            vex += bx * pe
                            vey += by * pe
            vrx, vry = 0.0, 0.0
            if boss_hitbox:
                bx, by = boss_hitbox.centerx, boss_hitbox.centery
                db = math.hypot(px - bx, py - by)
                if db < 350:
                    rm = max(1.0, db)
                    pr = (350.0 - db) / 100.0
                    vrx = ((px - bx) / rm) * pr
                    vry = ((py - by) / rm) * pr
            vfx = vmx + vex + vrx
            vfy = vmy + vey + vry
            self.direcao_x = 1 if vfx > 0.3 else (-1 if vfx < -0.3 else 0)
            self.direcao_y = 1 if vfy > 0.3 else (-1 if vfy < -0.3 else 0)
            if self.direcao_x == 0 and self.direcao_y == 0 and boss_hitbox:
                bx, by = boss_hitbox.centerx, boss_hitbox.centery
                ao = math.atan2(py - by, px - bx) + 1.5708
                self.direcao_x = 1 if math.cos(ao) > 0 else -1
                self.direcao_y = 1 if math.sin(ao) > 0 else -1
            mag_evasao = math.hypot(vex + vrx, vey + vry)
            dist_orbe = math.hypot(vmx, vmy) * 100.0 if vida_jogador < limiar_orbe and esferas_energia else 0.0
            self.usar_dash = (mag_evasao > 2.5 or dist_orbe > 200 or (boss_hitbox and math.hypot(px - boss_hitbox.centerx, py - boss_hitbox.centery) < 150)) and not cds.get("dash", False)
            if self.usar_dash:
                motivo = "Evasão alta" if mag_evasao > 2.5 else "Buscando orbe distante" if dist_orbe > 200 else "Boss muito perto"
                self._log_decisao("TELEPORTE", f"Dash acionado (fallback mecânico). Motivo: {motivo}")

    apolo = AgenteApolo()

    import atexit, signal
    def _salvar_tudo_ao_sair():
        try:
            apolo.salvar_memoria()
            memoria_umbra.salvar()
            if hasattr(apolo, 'encerrar'):
                apolo.encerrar()
        except Exception:
            pass
    atexit.register(_salvar_tudo_ao_sair)
    def _handler_ctrl_c(sig, frame):
        _salvar_tudo_ao_sair()
        import os
        os._exit(0)
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
                apolo.salvar_memoria()
                memoria_umbra.salvar() 
                rodando = False
                pygame.quit()
                if 'apolo' in globals() and hasattr(apolo, 'encerrar'):
                    apolo.encerrar()
                os._exit(0)
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
        if keys[pygame.K_t] and estado_atual_ia['fase_tele'] == "espera":
                # Resetamos o cooldown e simulamos dano crítico para forçar o Grafo
                estado_atual_ia['ultimo_teleporte'] = 0
                estado_atual_ia['dano_recente'] = 500
        # A tecla V foi removida para dar a Umbra a capacidade de chamar autonomamente


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

        if modo_ia_treino:
            cds = {
                "teleporte": cooldown_dash,
                "disparo": (agora - tempo_ultimo_disparo < intervalo_disparo)
            }
        
            boss_ref = hitbox_boss5 if 'hitbox_boss5' in locals() or 'hitbox_boss5' in globals() else None
            proj_ref = estado_atual_ia.get('projeteis', [])
            vida_boss_atual = vida_umbra if 'vida_umbra' in globals() else 10000
        
            # Calcula velocidade atual do personagem
            delta_x = pos_x_personagem - ultimo_x
            delta_y = pos_y_personagem - ultimo_y
            velocidade_atual = math.hypot(delta_x, delta_y)
        
            # Passa estado_atual_ia para o Apolo ter consciência das armadilhas
            estado_ia_ref = estado_atual_ia if 'estado_atual_ia' in globals() else None

            apolo.pensar((pos_x_personagem, pos_y_personagem), boss_ref, proj_ref, cds, vida, vida_boss_atual, esferas_energia_umbra, velocidade_atual, estado_ia_ref)
        
            pos_mouse = (apolo.alvo_x, apolo.alvo_y)
            botao_mouse = (apolo.mouse_simulado[0], False, False)
    
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
            if not hasattr(vfx_apolo, 'mascara_furos'):
                vfx_apolo.mascara_furos = pygame.Surface((largura_mapa, altura_mapa), pygame.SRCALPHA)
            mascara_furos = vfx_apolo.mascara_furos
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
                recompensar_cartas(cartas_compradas_apolo_global, venceu=False)
                agora_fim = pygame.time.get_ticks()
                tempo_inicio = estado_atual_ia.get('tempo_start_boss', agora_fim) if 'estado_atual_ia' in locals() else agora_fim
                duracao_combate = (agora_fim - tempo_inicio) / 1000.0
                registrar_batalha(
                    duracao_combate, 
                    "Umbra", 
                    vida_umbra, 
                    memoria_umbra.exploracao,
                    estado_atual_ia.get('acertos_umbra', 0),
                    estado_atual_ia.get('erros_umbra', 0),
                    estado_atual_ia.get('contagem_habilidades', {})
                )
            
                # Apolo aprende: esta decisao levou a morte (done=True, recompensa=-500)
                if apolo.ultimo_estado_tensor is not None:
                    apolo.fila_estados.put(("TREINAR", (
                        apolo.ultimo_estado_tensor,
                        apolo.acao_anterior,
                        -500.0,
                        apolo.ultimo_estado_tensor,  # estado terminal
                        True
                    )))
                apolo.aplicar_recompensa_direta(-500.0)
            
                # Reset do sistema de ratos
                gerenciador_ratos.resetar_partida()
         
                memoria_umbra.treinar(500.0, prioridade=True)
   
                mostrar_tutorial=False
                pygame.time.delay(2000)
                Musica_tema_fases.stop()
                Som_tema_fases.stop()
                memoria_umbra.salvar() 
                apolo.salvar_memoria() 
                rodando = False
                pygame.quit()
                limpar_salvamento()
                if 'apolo' in globals() and hasattr(apolo, 'encerrar'):
                    apolo.encerrar()
                os._exit(0)

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
                recompensar_cartas(cartas_compradas_apolo_global, venceu=True)
                duracao_combate = (agora - estado_atual_ia.get('tempo_start_boss', agora)) / 1000.0
                agora_fim = pygame.time.get_ticks()
                tempo_inicio = estado_atual_ia.get('tempo_start_boss', agora_fim) if 'estado_atual_ia' in locals() else agora_fim
                duracao_combate = (agora_fim - tempo_inicio) / 1000.0
                registrar_batalha(
                    duracao_combate, 
                    "Apolo", 
                    vida_umbra, 
                    memoria_umbra.exploracao,
                    estado_atual_ia.get('acertos_umbra', 0),
                    estado_atual_ia.get('erros_umbra', 0),
                    estado_atual_ia.get('contagem_habilidades', {})
                )
                apolo.aplicar_recompensa_direta(500.0) 
                memoria_umbra.treinar(-500.0, prioridade=True)
            
                # Reset do sistema de ratos
                gerenciador_ratos.resetar_partida()
            
                mostrar_tutorial = False
                pygame.time.delay(2000)
                Musica_tema_fases.stop()
                Som_tema_fases.stop()
                memoria_umbra.salvar() 
                apolo.salvar_memoria() 
                rodando = False
                pygame.quit()
                limpar_salvamento()
                
                if 'apolo' in globals() and hasattr(apolo, 'encerrar'):
                    apolo.encerrar()
                os._exit(0)
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
                    apolo.receber_dano_punitivo(resultado_colisoes['hits'], 50.0)
                
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
                        
                            # --- PUNIÇÃO APOLO: Sendo sugado para o centro ---
                            if dist_v < 150 and agora % 200 < 30:
                                apolo.receber_dano_punitivo(1, 2.0)
                                
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
                        
                            # --- PUNIÇÃO APOLO: Ficar preso no gelo (lentidão) ---
                            if agora % 100 < 20: 
                                apolo.receber_dano_punitivo(1, 2.0)
                        
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
                                vfx_apolo.criar_impacto_fragmentado(pos_x_umbra + largura_boss // 2, pos_y_umbra + altura_boss // 2)
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
                            # --- PUNIÇÃO APOLO: Dano por cegueira/miasma ---
                            apolo.receber_dano_punitivo(1, 5.0)
                    
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
                                apolo.receber_dano_punitivo(1, 10.0)
                        
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
                            apolo.receber_dano_punitivo(1, 20.0)
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
                                apolo.receber_dano_punitivo(1, 15.0)

                                # --- MEMÓRIA ESPACIAL: Registra zona como perigosa no SafeZone Grid ---
                                col_laser_hit = int(pos_x_personagem / max(1, largura_mapa / 8))
                                row_laser_hit = int(pos_y_personagem / max(1, altura_mapa / 6))
                                key_laser_hit = (col_laser_hit, row_laser_hit)
                                if key_laser_hit not in apolo.safe_zone_grid:
                                    apolo.safe_zone_grid[key_laser_hit] = [0, 0]
                                apolo.safe_zone_grid[key_laser_hit][1] += 3  # hit_count (peso maior por ser dano real)
                                apolo.frames_no_laser = 0  # Reseta sobrevivencia (levou dano)
                                
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
                            apolo.aplicar_recompensa_direta(recompensa_coleta)
                            efeitos_texto.append({"texto": "+500 DOPAMINA REWARD!", "x": pos_x_personagem, "y": pos_y_personagem - 50, "tempo_inicio": agora, "cor": (255, 215, 0)})
                        elif percentual_vida_antes < 0.6:  # Menos de 60% de vida
                            recompensa_coleta = 300.0  # RECOMPENSA MASSIVA
                            apolo.aplicar_recompensa_direta(recompensa_coleta)
                            efeitos_texto.append({"texto": "+300 DOPAMINA REWARD!", "x": pos_x_personagem, "y": pos_y_personagem - 50, "tempo_inicio": agora, "cor": (255, 215, 0)})
                        else:
                            recompensa_coleta = 150.0  # RECOMPENSA ENORME MESMO COM VIDA CHEIA
                            apolo.aplicar_recompensa_direta(recompensa_coleta)
                            efeitos_texto.append({"texto": "+150 DOPAMINA REWARD!", "x": pos_x_personagem, "y": pos_y_personagem - 50, "tempo_inicio": agora, "cor": (255, 215, 0)})
                    
                        efeitos_texto.append({
                            "texto": f"+{cura_aplicada} RESTAURAÇÃO!",
                            "x": pos_x_personagem,
                            "y": pos_y_personagem - 30,
                            "tempo_inicio": agora,
                            "cor": (0, 255, 150)
                        })
                    
                        apolo._orbe_coletada_neste_frame = True
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
                # Rotaciona o frame pelo centro para manter o eixo
                frame_rotacionado = pygame.transform.rotate(frame_para_desenhar, angulo_inclinacao_personagem)
                novo_rect = frame_rotacionado.get_rect(center=(pos_x_personagem + largura_personagem//2, pos_y_personagem + altura_personagem//2))
                tela.blit(frame_rotacionado, novo_rect.topleft)
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
                            apolo.receber_dano_punitivo(1, 5.0)
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
                                apolo.aplicar_recompensa_direta(0.5)
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
                        vfx_apolo.criar_impacto_fragmentado(disparo["rect"].centerx, disparo["rect"].centery)
                    
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
                        apolo.bonus_dopamina += 150.0  # Massiva recompensa por prever a movimentação de Umbra!
                        estado_atual_ia['tomou_tiro_no_dash'] = True


            # 5. Manutenção de Projéteis no Mapa
            dentro_mapa = 0 <= disparo["rect"].x < largura_mapa and 0 <= disparo["rect"].y < altura_mapa
            if dentro_mapa and not atingiu_boss and not interceptado:
                novos_disparos.append(disparo)
            elif not atingiu_boss and not interceptado:
                # Punição por tiro perdido na borda (Ensina ele a poupar munição e atirar só com mira certa)
                apolo.bonus_dopamina -= 20.0
                erros_player_contagem += 1 

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
            vfx_apolo.renderizar_plasma_apolo(tela, disparo["rect"].center, agora)

        # Atualizar e Desenhar Partículas de Desfragmentação (Globais)
        vfx_apolo.atualizar_e_desenhar(tela, agora)

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
    if 'apolo' in globals() and hasattr(apolo, 'encerrar'):
        apolo.encerrar()
    os._exit(0)