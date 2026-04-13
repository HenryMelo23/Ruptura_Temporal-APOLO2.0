
import pygame
import subprocess
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

pygame.init()
memoria_umbra = hb.MemoriaEvolutivaUmbra()
vfx_apolo = ApoloVFXManager()

# Carregar configurações gráficas
try:
    with open("config_graficos.json", "r") as f:
        config_graficos = json.load(f)
except:
    config_graficos = {
        "sombras_ativas": "dinamicas",
        "qualidade_grafica": "alta",
        "particulas_ativas": True,
        "efeitos_visuais": True
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
    global tempo_entrada_bordas, tempo_acumulado_bordas, ultimo_tick_dano_bordas, estava_nas_bordas

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
        pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem + dx * velocidade_personagem))
        pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem + dy * velocidade_personagem))

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
        pos_y = y + altura - offset_y - int(altura // 6)
        tela.blit(sombra_surface, (pos_x, pos_y))


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
                exit()
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
bonus_cura_sifon = 1.0

# Rastreadores de tempo nas bordas tóxicas
tempo_entrada_bordas = 0
tempo_acumulado_bordas = 0
ultimo_tick_dano_bordas = 0
estava_nas_bordas = False

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

class ApoloDQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(ApoloDQN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.LeakyReLU(),
            nn.Linear(128, 64),
            nn.LeakyReLU(),
            nn.Linear(64, output_size)
        )
    def forward(self, x):
        return self.net(x)

class AgenteApolo:
    def __init__(self):
        self.direcao_x = 0
        self.direcao_y = 0
        self.usar_dash = False
        self.mouse_simulado = [False, False, False]
        self.alvo_x = 0
        self.alvo_y = 0
        
        # Sistema de persistência de ação para movimentos mais fluidos
        self.acao_atual = 0
        self.frames_acao_atual = 0
        self.frames_minimos_por_acao = 8  # Mantém ação por pelo menos 8 frames (~133ms a 60fps)
        self.ultima_decisao_frame = 0
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.input_size = 41  # 35 anteriores + 6 novas features de laser (fase, rodada, progresso, num_feixes, sentido, vel_angular, angulo, dist, tempo)
        self.output_size = 5
        
        self.q_network = ApoloDQN(self.input_size, self.output_size).to(self.device)
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()
        
        self.ultimo_estado_tensor = None
        self.acao_anterior = 0
        self.vida_jogador_anterior = 0
        self.vida_boss_anterior = 0
        self.arquivo_memoria = "apolo_memoria_dqn.pt"
        self.taxa_exploracao = 0.50
        self.frames_sobrevividos = 0
        self.carregar_memoria()
        self.atualizar_foco_progressivo()

    def carregar_memoria(self):
        import os
        if os.path.exists(self.arquivo_memoria):
            try:
                self.q_network.load_state_dict(torch.load(self.arquivo_memoria, map_location=self.device, weights_only=True))
            except: pass

    def salvar_memoria(self):
        torch.save(self.q_network.state_dict(), self.arquivo_memoria)

    def aplicar_recompensa_direta(self, recompensa_direta):
        if self.ultimo_estado_tensor is not None:
            self.q_network.train()
            q_values = self.q_network(self.ultimo_estado_tensor)
            q_val = q_values[0, self.acao_anterior]
            alvo = q_val.item() + 0.15 * recompensa_direta
            alvo_tensor = torch.tensor(alvo, dtype=torch.float32, device=self.device)
            loss = self.criterion(q_val, alvo_tensor)
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

    def atualizar_foco_progressivo(self):
        import os, json
        try:
            if os.path.exists("historico_batalhas.json"):
                with open("historico_batalhas.json", "r") as f:
                    geracoes = len(json.load(f))
                self.taxa_exploracao = max(0.01, 0.20 * (0.985 ** geracoes))
        except: pass

    def obter_estado_expandido(self, pos_p, boss_hitbox, projeteis_boss, cds, esferas_energia, vida_apolo, vida_boss, velocidade_apolo, estado_ia):
        import math
        px, py = pos_p
        bx, by = largura_mapa // 2, altura_mapa // 2
        if boss_hitbox:
            bx, by = boss_hitbox.centerx, boss_hitbox.centery
            
        feat_px = px / max(1, largura_mapa)
        feat_py = py / max(1, altura_mapa)
        feat_bx = bx / max(1, largura_mapa)
        feat_by = by / max(1, altura_mapa)
        
        feat_vida_p = vida_apolo / 1000.0
        feat_vida_b = vida_boss / 1200.0
        
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
        for proj in projeteis_boss:
            if 'rect' in proj:
                proj_x, proj_y = proj['rect'].centerx, proj['rect'].centery
            else:
                proj_x, proj_y = proj.get('x', px), proj.get('y', py)
            d = math.hypot(proj_x - px, proj_y - py)
            if d < 250:
                projeteis_proximos.append((proj_x, proj_y, d))
                
        if projeteis_proximos:
            proj_x, proj_y, d = min(projeteis_proximos, key=lambda p: p[2])
            dist_perigo = d / 250.0
            dx_perigo = (proj_x - px) / max(1.0, d)
            dy_perigo = (proj_y - py) / max(1.0, d)
            
        feat_cd_tele = 1.0 if cds.get('teleporte', False) else 0.0
        
        feat_armadilhas = [0.0] * 7
        if estado_ia:
            keys = ['vortice_ativo', 'prisao_ativa', 'caminho_espinhos', 'laser_ativo', 'descarga_eletrica', 'bordas_ativas', 'miasma_ativo']
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
        
        feat_vel_b = 0.0
        
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
                    
                    # Calcular posição dos feixes e encontrar o mais próximo
                    if boss_hitbox:
                        origem_laser = (boss_hitbox.centerx, boss_hitbox.centery)
                        angulo_base = giro_total * feat_laser_progresso * sentido
                        
                        menor_dist = float('inf')
                        angulo_feixe_proximo = 0
                        tempo_ate_atingir = float('inf')
                        
                        for i in range(num_feixes):
                            angulo_atual = angulo_base + i * ((math.pi * 2) / num_feixes)
                            
                            # Calcula ponto final do feixe
                            comp_laser = 2500
                            fim_x = origem_laser[0] + math.cos(angulo_atual) * comp_laser
                            fim_y = origem_laser[1] + math.sin(angulo_atual) * comp_laser
                            
                            # Distância perpendicular do player à linha do laser
                            numerador = abs((fim_y - origem_laser[1])*px - (fim_x - origem_laser[0])*py + 
                                          fim_x*origem_laser[1] - fim_y*origem_laser[0])
                            denominador = math.hypot(fim_y - origem_laser[1], fim_x - origem_laser[0])
                            dist_linha = numerador / denominador if denominador > 0 else 9999
                            
                            # Verifica se está na frente do laser
                            dot_product = (px - origem_laser[0]) * math.cos(angulo_atual) + \
                                        (py - origem_laser[1]) * math.sin(angulo_atual)
                            
                            if dot_product > 0 and dist_linha < menor_dist:
                                menor_dist = dist_linha
                                angulo_feixe_proximo = angulo_atual
                                
                                # Estima tempo até o feixe atingir a posição do player
                                # Calcula ângulo entre posição atual do feixe e posição do player
                                angulo_player = math.atan2(py - origem_laser[1], px - origem_laser[0])
                                diff_angulo = angulo_player - angulo_atual
                                
                                # Normaliza diferença de ângulo para -pi a pi
                                while diff_angulo > math.pi: diff_angulo -= 2 * math.pi
                                while diff_angulo < -math.pi: diff_angulo += 2 * math.pi
                                
                                # Se o laser está girando na direção do player
                                if (sentido > 0 and diff_angulo > 0) or (sentido < 0 and diff_angulo < 0):
                                    tempo_ate_atingir = abs(diff_angulo) / abs(velocidade_angular) if velocidade_angular != 0 else 0
                                else:
                                    # Laser está se afastando, tempo é grande
                                    tempo_ate_atingir = 999
                        
                        # Normaliza features
                        feat_laser_dist_feixe_proximo = min(1.0, menor_dist / 400.0)  # 400px = distância segura
                        feat_laser_angulo_mais_proximo = math.sin(angulo_feixe_proximo)  # -1 a 1
                        feat_laser_tempo_ate_atingir = min(1.0, tempo_ate_atingir / 3.0)  # Normaliza até 3 segundos
            
        features = [feat_px, feat_py, feat_bx, feat_by, feat_vida_p, feat_vida_b, 
                   feat_dist_borda_esquerda, feat_dist_borda_direita, feat_dist_borda_cima, feat_dist_borda_baixo, em_canto,
                   dist_perigo, dx_perigo, dy_perigo, feat_cd_tele, feat_vel_p, feat_esferas_qtd, feat_vel_b, 
                   feat_laser_fase, feat_laser_rodada, feat_laser_progresso, feat_laser_num_feixes,
                   feat_laser_sentido_rotacao, feat_laser_velocidade_angular, feat_laser_angulo_mais_proximo,
                   feat_laser_dist_feixe_proximo, feat_laser_tempo_ate_atingir,
                   feat_dist_orbe_proxima, feat_dir_orbe_x, feat_dir_orbe_y, 
                   feat_qtd_ratos, feat_dist_rato_proximo, feat_dir_rato_x, feat_dir_rato_y] + feat_armadilhas
        
        tensor = torch.tensor(features, dtype=torch.float32, device=self.device).unsqueeze(0)
        return tensor

    def pensar(self, pos_p, boss_hitbox, projeteis_boss, cds, vida_jogador, vida_boss, esferas_energia, velocidade_atual=5, estado_ia=None):
        import random
        agora = pygame.time.get_ticks()  # Necessário para cálculos de tempo do laser
        self.direcao_x = 0
        self.direcao_y = 0
        self.usar_dash = False
        self.mouse_simulado[0] = False
        self.frames_sobrevividos += 1

        if boss_hitbox:
            self.alvo_x, self.alvo_y = boss_hitbox.center
            if cds.get("disparo", False) == False: 
                self.mouse_simulado[0] = True

        # RECOMPENSA EXPANDIDA
        recompensa = 0.5  # Sobrevivência base
        delta_vida_apolo = 0
        delta_vida_boss = 0
        px, py = pos_p  # Define px e py no início para uso em todo o método
        
        if self.vida_jogador_anterior > 0:
            delta_vida_apolo = vida_jogador - self.vida_jogador_anterior
            delta_vida_boss = vida_boss - self.vida_boss_anterior

        if delta_vida_apolo < 0:
            recompensa -= 50
        if delta_vida_boss < 0:
            recompensa += 30
        if delta_vida_apolo > 0:
            recompensa += 100
        
        # SISTEMA INTELIGENTE DE RECOMPENSAS PARA O LASER
        if estado_ia:
            laser = estado_ia.get('laser_ativo')
            if laser:
                # Recompensas durante fase de carregamento (preparação)
                if laser.get('fase') == 'carregando':
                    tempo_laser = agora - laser['tempo_inicio']
                    progresso_carga = min(1.0, tempo_laser / laser['duracao_carga'])
                    
                    # Recompensa por se afastar do centro durante carregamento
                    if boss_hitbox:
                        dist_centro = math.hypot(boss_hitbox.centerx - px, boss_hitbox.centery - py)
                        if dist_centro > 400:  # Longe do epicentro
                            recompensa += 5
                        elif dist_centro < 200:  # Muito perto (perigoso)
                            recompensa -= 10
                    
                    # Alerta crescente conforme o laser está prestes a disparar
                    if progresso_carga > 0.8:  # 80% carregado
                        recompensa += 3  # Recompensa por estar preparado
                
                # Recompensas durante disparo (evasão ativa)
                elif laser.get('fase') == 'disparando':
                    # Calcula distância ao feixe mais próximo
                    if boss_hitbox:
                        origem_laser = (boss_hitbox.centerx, boss_hitbox.centery)
                        t_disp = agora - laser['tempo_inicio_disparo']
                        progresso = min(1.0, t_disp / laser['duracao_disparo'])
                        
                        # Configuração por rodada
                        rodada = laser.get('rodada', 1)
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
                        else:
                            num_feixes = 6
                            sentido = -1
                            giro_total = math.pi * 0.8
                        
                        angulo_base = giro_total * progresso * sentido
                        menor_dist = float('inf')
                        
                        for i in range(num_feixes):
                            angulo_atual = angulo_base + i * ((math.pi * 2) / num_feixes)
                            comp_laser = 2500
                            fim_x = origem_laser[0] + math.cos(angulo_atual) * comp_laser
                            fim_y = origem_laser[1] + math.sin(angulo_atual) * comp_laser
                            
                            numerador = abs((fim_y - origem_laser[1])*px - (fim_x - origem_laser[0])*py + 
                                          fim_x*origem_laser[1] - fim_y*origem_laser[0])
                            denominador = math.hypot(fim_y - origem_laser[1], fim_x - origem_laser[0])
                            dist_linha = numerador / denominador if denominador > 0 else 9999
                            
                            dot_product = (px - origem_laser[0]) * math.cos(angulo_atual) + \
                                        (py - origem_laser[1]) * math.sin(angulo_atual)
                            
                            if dot_product > 0:
                                menor_dist = min(menor_dist, dist_linha)
                        
                        # Sistema de recompensas baseado em distância do feixe
                        if menor_dist < 50:  # ZONA DE PERIGO EXTREMO
                            recompensa -= 30
                        elif menor_dist < 100:  # Zona de perigo
                            recompensa -= 15
                        elif menor_dist < 200:  # Zona de alerta
                            recompensa -= 5
                        elif 200 <= menor_dist < 350:  # Zona segura próxima
                            recompensa += 8
                        elif menor_dist >= 350:  # Zona muito segura
                            recompensa += 15
                        
                        # Recompensa EXTRA por sobreviver sem dano durante laser ativo
                        if delta_vida_apolo == 0:
                            recompensa += 25  # Grande recompensa por evasão perfeita
                        
                        # Penalidade SEVERA por ser atingido
                        if delta_vida_apolo < 0:
                            recompensa -= 200  # Penalidade massiva para aprender a evitar
        
        # SISTEMA DE CONSCIÊNCIA DE BORDAS (CRÍTICO)
        margem_perigo = 100
        margem_critica = 50
        
        # Penalidades progressivas por proximidade das bordas
        dist_esquerda = px
        dist_direita = largura_mapa - px
        dist_cima = py
        dist_baixo = altura_mapa - py
        
        # Zona crítica (muito perto da borda)
        if dist_esquerda < margem_critica or dist_direita < margem_critica or \
           dist_cima < margem_critica or dist_baixo < margem_critica:
            recompensa -= 25  # Penalidade SEVERA
        # Zona de perigo (perto da borda)
        elif dist_esquerda < margem_perigo or dist_direita < margem_perigo or \
             dist_cima < margem_perigo or dist_baixo < margem_perigo:
            recompensa -= 8  # Penalidade moderada
        
        # PENALIDADE EXTREMA POR ESTAR EM CANTOS (situação mais perigosa)
        em_canto_esq_cima = (dist_esquerda < margem_perigo and dist_cima < margem_perigo)
        em_canto_dir_cima = (dist_direita < margem_perigo and dist_cima < margem_perigo)
        em_canto_esq_baixo = (dist_esquerda < margem_perigo and dist_baixo < margem_perigo)
        em_canto_dir_baixo = (dist_direita < margem_perigo and dist_baixo < margem_perigo)
        
        if em_canto_esq_cima or em_canto_dir_cima or em_canto_esq_baixo or em_canto_dir_baixo:
            recompensa -= 40  # Penalidade EXTREMA por estar em canto
        
        # RECOMPENSA por ficar na zona segura (centro do mapa)
        centro_x = largura_mapa // 2
        centro_y = altura_mapa // 2
        dist_centro = math.hypot(px - centro_x, py - centro_y)
        raio_seguro = min(largura_mapa, altura_mapa) * 0.3  # 30% do mapa é zona segura
        
        if dist_centro < raio_seguro:
            recompensa += 3  # Recompensa por estar no centro
        
        # Recompensa por manter distância segura do boss
        if boss_hitbox:
            dist_boss = math.hypot(boss_hitbox.centerx - px, boss_hitbox.centery - py)
            if 300 < dist_boss < 600:
                recompensa += 1
            elif dist_boss < 200:
                recompensa -= 3
        
        # NOVO: Recompensa por buscar orbes quando está com pouca vida
        if esferas_energia and len(esferas_energia) > 0:
            percentual_vida_atual = vida_jogador / 1000.0  # Assumindo vida máxima ~1000
            
            # Calcula distância até orbe mais próxima
            orbe_mais_proxima = None
            dist_min_orbe = float('inf')
            for orbe in esferas_energia:
                ox, oy = orbe.get('x', px), orbe.get('y', py)
                dist = math.hypot(ox - px, oy - py)
                if dist < dist_min_orbe:
                    dist_min_orbe = dist
                    orbe_mais_proxima = orbe
            
            if orbe_mais_proxima and dist_min_orbe < 800:
                # Se está com pouca vida e se aproximando de orbe: grande recompensa
                if percentual_vida_atual < 0.3:  # Menos de 30% vida
                    if dist_min_orbe < 200:  # Muito perto da orbe
                        recompensa += 15
                    elif dist_min_orbe < 400:  # Aproximando-se
                        recompensa += 8
                elif percentual_vida_atual < 0.5:  # Menos de 50% vida
                    if dist_min_orbe < 200:
                        recompensa += 8
                    elif dist_min_orbe < 400:
                        recompensa += 4
                
                # Penaliza se está com pouca vida mas se afastando da orbe
                if percentual_vida_atual < 0.4:
                    # Verifica se está se afastando (comparando com frame anterior)
                    if hasattr(self, 'dist_orbe_anterior'):
                        if dist_min_orbe > self.dist_orbe_anterior + 20:  # Se afastou significativamente
                            recompensa -= 5
                    self.dist_orbe_anterior = dist_min_orbe
        
        # NOVO: Recompensa por evitar ratos (apenas na Dimensão 9)
        if 'gerenciador_ratos' in globals():
            ratos_ativos = gerenciador_ratos.ratos
            if len(ratos_ativos) > 0:
                # Calcula distância até o rato mais próximo
                dist_min_rato = float('inf')
                for rato in ratos_ativos:
                    dist = math.hypot(rato.pos_x - px, rato.pos_y - py)
                    if dist < dist_min_rato:
                        dist_min_rato = dist
                
                # Recompensa por manter distância segura dos ratos
                if dist_min_rato < 100:  # Muito perto (perigo!)
                    recompensa -= 8
                elif dist_min_rato < 200:  # Perto (alerta)
                    recompensa -= 3
                elif 200 <= dist_min_rato < 400:  # Distância segura
                    recompensa += 2
                
                # Recompensa extra por evitar múltiplos ratos
                if len(ratos_ativos) >= 10:  # Muitos ratos ativos
                    if dist_min_rato > 300:  # Mantendo distância boa
                        recompensa += 5

        self.vida_jogador_anterior = vida_jogador
        self.vida_boss_anterior = vida_boss

        # OBTER ESTADO EXPANDIDO
        estado_tensor = self.obter_estado_expandido(
            pos_p, boss_hitbox, projeteis_boss, cds, esferas_energia,
            vida_jogador, vida_boss, velocidade_atual, estado_ia
        )

        if self.ultimo_estado_tensor is not None:
            self.q_network.train()
            q_values = self.q_network(self.ultimo_estado_tensor)
            q_val = q_values[0, self.acao_anterior]
            alvo = q_val.item() + 0.15 * (recompensa - q_val.item())
            alvo_tensor = torch.tensor(alvo, dtype=torch.float32, device=self.device)
            loss = self.criterion(q_val, alvo_tensor)
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

        # FILTRAGEM DE AÇÕES INVÁLIDAS (previne sair do mapa)
        margem_bloqueio = 80  # Pixels de margem onde ações são bloqueadas
        acoes_validas = [0, 1, 2, 3, 4]  # Todas as ações inicialmente válidas
        
        # Remove ações que levam para fora do mapa
        if py < margem_bloqueio:  # Muito perto da borda superior
            if 0 in acoes_validas: acoes_validas.remove(0)  # Bloqueia movimento para cima
        if py > altura_mapa - margem_bloqueio:  # Muito perto da borda inferior
            if 1 in acoes_validas: acoes_validas.remove(1)  # Bloqueia movimento para baixo
        if px < margem_bloqueio:  # Muito perto da borda esquerda
            if 2 in acoes_validas: acoes_validas.remove(2)  # Bloqueia movimento para esquerda
        if px > largura_mapa - margem_bloqueio:  # Muito perto da borda direita
            if 3 in acoes_validas: acoes_validas.remove(3)  # Bloqueia movimento para direita
        
        # Garante que sempre há pelo menos uma ação válida (dash sempre disponível)
        if len(acoes_validas) == 0:
            acoes_validas = [4]  # Apenas dash disponível em situação extrema
        
        # SISTEMA DE PERSISTÊNCIA DE AÇÃO (movimentos mais fluidos)
        self.frames_acao_atual += 1
        
        # Condições para forçar nova decisão (situações de emergência)
        forcar_nova_decisao = False
        
        # Emergência 1: Laser ativo e muito próximo
        if estado_ia:
            laser = estado_ia.get('laser_ativo')
            if laser and laser.get('fase') == 'disparando':
                if boss_hitbox:
                    origem_laser = (boss_hitbox.centerx, boss_hitbox.centery)
                    t_disp = agora - laser['tempo_inicio_disparo']
                    progresso = min(1.0, t_disp / laser['duracao_disparo'])
                    rodada = laser.get('rodada', 1)
                    
                    # Calcula distância ao feixe mais próximo
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
                    else:
                        num_feixes = 6
                        sentido = -1
                        giro_total = math.pi * 0.8
                    
                    angulo_base = giro_total * progresso * sentido
                    menor_dist = float('inf')
                    
                    for i in range(num_feixes):
                        angulo_atual = angulo_base + i * ((math.pi * 2) / num_feixes)
                        comp_laser = 2500
                        fim_x = origem_laser[0] + math.cos(angulo_atual) * comp_laser
                        fim_y = origem_laser[1] + math.sin(angulo_atual) * comp_laser
                        
                        numerador = abs((fim_y - origem_laser[1])*px - (fim_x - origem_laser[0])*py + 
                                      fim_x*origem_laser[1] - fim_y*origem_laser[0])
                        denominador = math.hypot(fim_y - origem_laser[1], fim_x - origem_laser[0])
                        dist_linha = numerador / denominador if denominador > 0 else 9999
                        
                        dot_product = (px - origem_laser[0]) * math.cos(angulo_atual) + \
                                    (py - origem_laser[1]) * math.sin(angulo_atual)
                        
                        if dot_product > 0:
                            menor_dist = min(menor_dist, dist_linha)
                    
                    # Se laser muito próximo, força nova decisão
                    if menor_dist < 100:
                        forcar_nova_decisao = True
        
        # Emergência 2: Rato muito próximo
        if 'gerenciador_ratos' in globals():
            ratos_ativos = gerenciador_ratos.ratos
            if len(ratos_ativos) > 0:
                for rato in ratos_ativos:
                    dist = math.hypot(rato.pos_x - px, rato.pos_y - py)
                    if dist < 80:  # Rato muito perto
                        forcar_nova_decisao = True
                        break
        
        # Emergência 3: Projétil muito próximo
        for proj in projeteis_boss:
            if 'rect' in proj:
                proj_x, proj_y = proj['rect'].centerx, proj['rect'].centery
            else:
                proj_x, proj_y = proj.get('x', px), proj.get('y', py)
            d = math.hypot(proj_x - px, proj_y - py)
            if d < 80:  # Projétil muito perto
                forcar_nova_decisao = True
                break
        
        # Emergência 4: Vida crítica
        if vida_jogador < 200:  # Menos de 20% de vida
            forcar_nova_decisao = True
        
        # Decide se mantém ação atual ou escolhe nova
        if self.frames_acao_atual < self.frames_minimos_por_acao and not forcar_nova_decisao:
            # Mantém ação atual se ainda não passou o tempo mínimo
            acao = self.acao_atual
            
            # Verifica se a ação atual ainda é válida
            if acao not in acoes_validas:
                # Se não é mais válida, escolhe a mais próxima válida
                if len(acoes_validas) > 0:
                    acao = min(acoes_validas, key=lambda a: abs(a - acao))
                else:
                    acao = 4  # Dash como fallback
        else:
            # Tempo de escolher nova ação
            if random.random() < self.taxa_exploracao:
                acao = random.choice(acoes_validas)  # Explora apenas ações válidas
            else:
                with torch.no_grad():
                    self.q_network.eval()
                    q_vals = self.q_network(estado_tensor)[0]  # Remove dimensão batch
                    
                    # Mascara ações inválidas com valor muito negativo
                    q_vals_masked = q_vals.clone()
                    for i in range(5):
                        if i not in acoes_validas:
                            q_vals_masked[i] = -1e9  # Valor extremamente negativo
                    
                    acao = torch.argmax(q_vals_masked).item()
            
            # Reseta contador se mudou de ação
            if acao != self.acao_atual:
                self.frames_acao_atual = 0
                self.acao_atual = acao

        self.ultimo_estado_tensor = estado_tensor
        self.acao_anterior = acao

        if acao == 0: self.direcao_y = -1   
        elif acao == 1: self.direcao_y = 1  
        elif acao == 2: self.direcao_x = -1 
        elif acao == 3: self.direcao_x = 1  
        elif acao == 4: self.usar_dash = True

apolo = AgenteApolo()

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
        "Speed Boost": 10.0, "Porção": 10.0, "Disparo crescente": 10.0, "Trembo": 10.0, 
        "Tempestade": 10.0, "Cura": 10.0, "Speed Atack": 10.0, "Teleporte": 10.0, 
        "Petro": 10.0, "Defesa": 10.0, "Poison": 10.0
    }
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r") as f:
                pesos_salvos = json.load(f)
                for k, v in pesos_salvos.items():
                    pesos_base[k] = v
        except: pass
    return pesos_base

def salvar_memoria_cartas(pesos):
    with open("memoria_cartas_apolo.json", "w") as f:
        json.dump(pesos, f, indent=4)

def recompensar_cartas(cartas_usadas, venceu):
    pesos = carregar_memoria_cartas()
    for carta in cartas_usadas:
        if carta in pesos:
            if venceu:
                pesos[carta] += 1.5  # Reforço positivo agressivo
            else:
                pesos[carta] = max(2.0, pesos[carta] - 0.3) # Punição tática, garantindo um piso mínimo
    salvar_memoria_cartas(pesos)

def inteligencia_escolha_cartas_apolo(qtd):
    pesos = carregar_memoria_cartas()
    escolhas = []
    opcoes = list(pesos.keys())

    for _ in range(qtd):
        if escolhas.count("Petro") >= 5: pesos["Petro"] = 0
        if escolhas.count("Trembo") >= 1: pesos["Trembo"] = 0
        if escolhas.count("Cura") >= 10: pesos["Cura"] = 0
        if escolhas.count("Defesa") >= 10: pesos["Defesa"] = 0
        if escolhas.count("Speed Boost") >= 8: pesos["Speed Boost"] = 0
        if escolhas.count("Porção") >= 10: pesos["Porção"] = 0
        if escolhas.count("Tempestade") >= 12: pesos["Tempestade"] = 0
        if escolhas.count("Disparo crescente") >= 15: pesos["Disparo crescente"] = 0

        p_lista = [pesos[op] for op in opcoes]
        soma = sum(p_lista)
        if soma == 0:
            p_lista = [1.0 for _ in opcoes]

        escolhida = random.choices(opcoes, weights=p_lista, k=1)[0]
        escolhas.append(escolhida)

    contagem = collections.Counter(escolhas)
    print("\n" + "="*50)
    print(f"🧠 SELEÇÃO GENÉTICA DE APOLO ({qtd} Cartas)")
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
            velocidade_personagem += 0.05 + (inimigos_eliminados // 200) * 0.002
        elif carta == "Porção":
            aumento_vida = 650 + (inimigos_eliminados // 50) * 8
            vida_maxima += aumento_vida
            vida += int(vida_maxima * 0.30)
            vida_petro += int(vida_maxima_petro * 0.25)
            if vida_petro > vida_maxima_petro: vida_maxima_petro = vida_petro
        elif carta == "Disparo crescente":
            dano_person_hit += 25 + (inimigos_eliminados // 50) * 1.5
        elif carta == "Trembo":
            trembo = True
            Tempo_cura = max(500, int(Tempo_cura * 0.85)) # Em 10 cartas, o tick cai para próximo de 0.5s
            porcentagem_cura += 0.005 + (inimigos_eliminados // 400) * 0.001 # Garante uma base inicial mais forte (0.5%)
        elif carta == "Tempestade":
            dano_person_hit += 5 + (inimigos_eliminados // 100) * 1
            chance_critico += 0.01 + (inimigos_eliminados // 300) * 0.002
        elif carta == "Cura":
            roubo_de_vida += 0.10 + (inimigos_eliminados // 500) * 0.001
            quantidade_roubo_vida += 0.30 + (inimigos_eliminados // 500) * 0.001
        elif carta == "Speed Atack":
            intervalo_disparo = max(50, int(intervalo_disparo * 0.88))
        elif carta == "Teleporte":
            reducao = 0.95 - min(0.15, (inimigos_eliminados // 1000) * 0.02)
            tempo_cooldown_dash = max(0.4, tempo_cooldown_dash * reducao)
        elif carta == "Petro":
            Petro_active = True
            dano_petro += 8 + (inimigos_eliminados // 80) * 2
            if 0 < petro_evolucao <= 8:
                xp_petro = "nivel_1"
                petro_evolucao += 4
            elif 8 < petro_evolucao <= 16:
                xp_petro = "nivel_2"
                vida_maxima_petro += 600
                petro_evolucao += 4
            elif petro_evolucao > 16:
                xp_petro = "nivel_3"
                vida_maxima_petro += 1200
                Resistencia_petro += 12
                dano_petro += 150
            if vida_petro < vida_maxima_petro: vida_petro += int(vida_maxima_petro * 0.40)
            if vida_petro > vida_maxima_petro: vida_maxima_petro = vida_petro
        elif carta == "Defesa":
            Resistencia = min(60, Resistencia + 2 + (inimigos_eliminados // 200) * 0.25)
        

    # --- ESCALONAMENTO DINÂMICO DA UMBRA ---
    ataques_por_segundo = 1000 / max(50, intervalo_disparo)
    multiplicador_critico = 1 + (chance_critico * 2.0)
    dps_teorico_apolo = dano_person_hit * ataques_por_segundo * multiplicador_critico
    
    vida_maxima_umbra = int(25000 + (dps_teorico_apolo * 24) + (inimigos_eliminados * 25))

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

    print(f"\n[ 💀 UMBRA ] - {qtd_cartas_umbra} Cartas Sorteadas (Caos Puro)")
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

running = True
while running:
    agora = pygame.time.get_ticks()
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
        
        # 2. Criamos uma máscara de "furos" para este frame
        mascara_furos = pygame.Surface((largura_mapa, altura_mapa), pygame.SRCALPHA)
        
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
            
            # Apolo sofre o trauma absoluto do fracasso
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
            subprocess.Popen([sys.executable, "GAME5.py"])
            sys.exit()

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
            subprocess.Popen([sys.executable, "GAME5.py"])
            sys.exit()
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
                apolo.aplicar_recompensa_direta(-50.0 * resultado_colisoes['hits'])
                
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
                    # Reduzimos para 2% para permitir o counter-play tático
                    valor_cura = (vida_maxima_umbra-vida_umbra) * 0.01
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
                            apolo.aplicar_recompensa_direta(-2.0)
                                
                        # Trava de colisão com os limites do mapa
                        pos_x_personagem = max(0, min(largura_mapa - largura_personagem, pos_x_personagem))
                        pos_y_personagem = max(0, min(altura_mapa - altura_personagem, pos_y_personagem))
                    
                    # Renderização animada da Singularidade
                    frame_v = frames_vortex[(agora // 150) % len(frames_vortex)]
                    frame_v = pygame.transform.scale(frame_v, (160, 160))
                    tela.blit(frame_v, (vortice['x'] - 80, vortice['y'] - 80))
                else:
                    estado_atual_ia['vortice_ativo'] = None

            # --- RENDERIZAÇÃO E FÍSICA DA PRISÃO CRIOGÊNICA (FASE 2) ---
            prisao = estado_atual_ia.get('prisao_ativa')
            if prisao:
                tempo_prisao = agora - prisao['tempo_inicio']
                if tempo_prisao < prisao['duracao']:
                    
                    # 1. Dinâmica de Pulsação e Crescimento da Zona
                    raio_hitbox_base = 45
                    aumento_pulso = int(abs(math.sin(agora * 0.001)) * 180)
                    raio_hitbox_atual = raio_hitbox_base + aumento_pulso
                    
                    tamanho_vortice = (raio_hitbox_atual * 2) + 40 
                    superficie_vortice = pygame.Surface((tamanho_vortice, tamanho_vortice), pygame.SRCALPHA)
                    centro_v_x, centro_v_y = tamanho_vortice // 2, tamanho_vortice // 2
                    
                    # 2. Núcleo Energético Pulsante Expandido
                    raio_nucleo = (raio_hitbox_atual * 0.6) + int(math.sin(agora * 0.008) * 8)
                    alfa_nucleo = 110 + int(math.sin(agora * 0.008) * 40)
                    cores_nucleo = [
                        ((0, 80, 255, alfa_nucleo), raio_nucleo),      
                        ((0, 160, 255, alfa_nucleo + 20), raio_nucleo * 0.7), 
                        ((150, 240, 255, alfa_nucleo + 40), raio_nucleo * 0.3) 
                    ]
                    for cor, raio in cores_nucleo:
                        pygame.draw.circle(superficie_vortice, cor, (centro_v_x, centro_v_y), max(1, int(raio)))

                    # 3. Anel Externo Congelante (Acompanha o Pulso)
                    num_segmentos = 40
                    angulo_base = (agora * 0.002) 
                    for i in range(num_segmentos):
                        ang = angulo_base + (i * (math.pi * 2 / num_segmentos))
                        r_ext = raio_hitbox_atual + random.uniform(-4, 4) 
                        px = centro_v_x + r_ext * math.cos(ang)
                        py = centro_v_y + r_ext * math.sin(ang)
                        pygame.draw.circle(superficie_vortice, (200, 250, 255, 180), (int(px), int(py)), random.choice([2, 3, 4]))

                    # 4. Tempestade de Flocos e Cristais
                    random.seed(prisao['tempo_inicio']) 
                    num_particulas = 70
                    velocidade_tempestade = -(agora * 0.005) 
                    
                    for i in range(num_particulas):
                        raio_orbita = random.uniform(15, raio_hitbox_atual)
                        angulo_offset = random.uniform(0, math.pi * 2)
                        tipo = random.choice(['floco', 'cristal', 'cristal']) 
                        
                        ang_final = velocidade_tempestade + angulo_offset
                        px = centro_v_x + raio_orbita * math.cos(ang_final)
                        py = centro_v_y + raio_orbita * math.sin(ang_final)
                        
                        if tipo == 'floco':
                            superficie_vortice.blit(floco_superficie, (int(px)-2, int(py)-2))
                        else:
                            superficie_vortice.blit(cristal_superficie, (int(px)-3, int(py)-3))
                    
                    random.seed()

                    # 5. Aplicação Visceral no Ecrã
                    tela.blit(superficie_vortice, (prisao['x'] - centro_v_x, prisao['y'] - centro_v_y))

                    # 6. Detecção de Punição Física (Hitbox Dinâmica)
                    dist_p = math.hypot(prisao['x'] - personagem_rect.centerx, prisao['y'] - personagem_rect.centery)
                    if dist_p < raio_hitbox_atual: 
                        velocidade_personagem = 0.3 
                        
                        # --- PUNIÇÃO APOLO: Ficar preso no gelo (lentidão) ---
                        if agora % 100 < 20: 
                            apolo.aplicar_recompensa_direta(-2.0)
                        
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
                    # A. Movimentação do Sinalizador Azul
                    dx_sinal = sinal['velocidade'] * math.cos(sinal['angulo'])
                    dy_sinal = sinal['velocidade'] * math.sin(sinal['angulo'])
                    sinal['x'] += dx_sinal
                    sinal['y'] += dy_sinal
                    sinal['dist_percorrida'] += math.hypot(dx_sinal, dy_sinal)
                    memoria_umbra.treinar(0.5)

                    # B. Renderização do Sinalizador (Brilho Neon)
                    pygame.draw.circle(tela, (200, 230, 255), (int(sinal['x']), int(sinal['y'])), 8)
                    pygame.draw.circle(tela, (0, 150, 255), (int(sinal['x']), int(sinal['y'])), 15, 2)

                    # C. O SALTO REAL (Quando o projétil chega ao destino)
                    if sinal['dist_percorrida'] >= sinal['dist_total']:
                        pos_x_umbra = sinal['target_pos'][0]
                        pos_y_umbra = sinal['target_pos'][1]
                        
                        # Reset dos estados para permitir o próximo ciclo
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
                    
                    dano_bruto = (420 + (inimigos_eliminados * 0.10)) * multiplicador_dano_umbra
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
                        apolo.aplicar_recompensa_direta(-5.0)
                    
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
                            apolo.aplicar_recompensa_direta(-10.0)
                        
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
                        apolo.aplicar_recompensa_direta(-20.0)
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
                        
                        # Partículas (Faiscas limitadas para o estágio 4 não fritar o FPS)
                        qtd_particulas = 6 if rodada < 4 else 2
                        for _ in range(qtd_particulas):
                            dist_faisca = random.uniform(50, 1200)
                            desvio = random.uniform(-esp[0]/2, esp[0]/2)
                            f_x = origem_laser[0] + math.cos(angulo_atual) * dist_faisca + math.cos(angulo_atual+math.pi/2)*desvio
                            f_y = origem_laser[1] + math.sin(angulo_atual) * dist_faisca + math.sin(angulo_atual+math.pi/2)*desvio
                            tamanho_faisca = random.randint(2, 5) if rodada < 4 else random.randint(1, 3)
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
                            apolo.aplicar_recompensa_direta(-15.0)
                                
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
            for p in particulas_fogo_player[:]:
                if p["tipo"] == "brasa":
                    p["x"] += p["vx"]
                    p["y"] += p["vy"]
                    p["vida"] -= 8
                    p["tamanho"] = max(0.1, p["tamanho"] - 0.15)
                    
                    if p["vida"] <= 0 or p["tamanho"] <= 0.1:
                        particulas_fogo_player.remove(p)
                    else:
                        # Transição térmica: Laranja incandescente -> Cinza frio (chão)
                        cor_brasa = (255, int(p["vida"]), 0) if p["vida"] > 100 else (100, 100, 100)
                        pygame.draw.circle(tela, cor_brasa, (int(p["x"]), int(p["y"])), int(p["tamanho"]))
                
                elif p["tipo"] == "fumaca":
                    p["x"] += p["vx"]
                    p["y"] += p["vy"]
                    p["vida"] -= 6
                    p["tamanho"] += 0.25
                    
                    if p["vida"] <= 0:
                        particulas_fogo_player.remove(p)
                    else:
                        cinza = int(p["vida"] * 0.4)
                        pygame.draw.circle(tela, (cinza, cinza, cinza), (int(p["x"]), int(p["y"])), int(p["tamanho"]))

            


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
                esferas_energia_umbra.append({
                    "x": pos_x_umbra + largura_boss // 2,
                    "y": pos_y_umbra + altura_boss // 2,
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
                    
                    # Recompensa para Apolo se coletou com pouca vida
                    percentual_vida_antes = vida_antes / vida_maxima
                    if percentual_vida_antes < 0.3:  # Menos de 30% de vida
                        recompensa_coleta = 80.0  # Grande recompensa por decisão tática
                        apolo.aplicar_recompensa_direta(recompensa_coleta)
                    elif percentual_vida_antes < 0.5:  # Menos de 50% de vida
                        recompensa_coleta = 40.0  # Recompensa moderada
                        apolo.aplicar_recompensa_direta(recompensa_coleta)
                    else:
                        recompensa_coleta = 10.0  # Pequena recompensa
                        apolo.aplicar_recompensa_direta(recompensa_coleta)
                    
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
        tela.blit(frames_animacao[direcao_atual][frame_atual], (pos_x_personagem, pos_y_personagem))
    
    # Se a IA ainda não foi processada neste frame, garantimos que o estado exista
    if 'estado_atual_ia' not in locals() and 'estado_atual_ia' not in globals():
        estado_atual_ia = {'parede_ativa': False}

    # --- MOTOR DE PRAGA DE RATOS (DIMENSÃO 9) ---
    if estado_atual_ia.get('dimensao_ativa') == "rastro":
        ratos = estado_atual_ia.get('ratos_ativos', [])
        novos_ratos = []
        for rato in ratos:
            vivo = True
            # Steering Boids (Cercamento Implacável)
            dx = pos_x_personagem + largura_personagem//2 - rato['x']
            dy = pos_y_personagem + altura_personagem//2 - rato['y']
            dist = math.hypot(dx, dy)
            if dist > 0:
                rato['x'] += (dx/dist) * 6.0
                rato['y'] += (dy/dist) * 6.0
            
            # Colisão com o Jogador (Lifesteal)
            if dist < 30 and vivo:
                vivo = False
                vida -= 5.0
                vida_boss5 = min(vida_boss_maxima, vida_boss5 + 20)
                estado_atual_ia['ratos_adicionais'] = estado_atual_ia.get('ratos_adicionais', 0) + 1
                
                memoria_umbra.treinar(5.0)  # Recompensa alta pra Umbra
                apolo.aplicar_recompensa_direta(-5.0)  # Punição pro Apolo
                
                efeitos_texto.append({"texto": "+20 LIFESTEAL UMBRA", "x": pos_x_umbra, "y": pos_y_umbra - 30, "tempo_inicio": agora, "cor": (50, 255, 50)})
                efeitos_texto.append({"texto": "+1 RATO PERMANENTE", "x": pos_x_umbra, "y": pos_y_umbra - 50, "tempo_inicio": agora, "cor": (150, 0, 150)})
            
            # Bloqueio Ativo (Escudo de Carne / Destruição de Ratos)
            for tiro in list(disparos): # Itera uma cópia de disparos globais
                dist_tiro = math.hypot(tiro['rect'].centerx - rato['x'], tiro['rect'].centery - rato['y'])
                if dist_tiro < 25 and vivo:
                    vivo = False
                    if tiro in disparos:
                        disparos.remove(tiro)
                    efeitos_texto.append({"texto": "SPLAT!", "x": rato['x'], "y": rato['y'], "tempo_inicio": agora, "cor": (100, 0, 100)})
                    apolo.aplicar_recompensa_direta(0.5) # Micro recompensa pro player acertar rato
                    break
            
            if vivo:
                novos_ratos.append(rato)
                # Arte Procedural Boids/Rato (Borda de caos púrpura)
                pygame.draw.circle(tela, (20, 10, 30), (int(rato['x']), int(rato['y'])), 12)
                pygame.draw.circle(tela, (130, 20, 150), (int(rato['x']), int(rato['y'])), 8)
                pygame.draw.circle(tela, (50, 255, 50), (int(rato['x']+random.randint(-2,2)), int(rato['y']+random.randint(-2,2))), 3)
                
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

                # Aplicação de Dano e Treino
                if vida_umbra > 0:
                    vida_umbra -= dano_final
                    
                    # --- NOVO MOTOR DE VFX: Desfragmentação de Impacto ---
                    vfx_apolo.criar_impacto_fragmentado(disparo["rect"].centerx, disparo["rect"].centery)
                    
                    punicao = -2.0 
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


                # O Escudo de Atrito (Reduz dano em 70% e carrega a fúria)
                if estado_atual_ia.get('dimensao_ativa') == "atrito":
                    dano_final *= 0.3
                    estado_atual_ia['carga_atrito'] = estado_atual_ia.get('carga_atrito', 0) + 8
                    
                    if estado_atual_ia['carga_atrito'] >= 100 and not estado_atual_ia.get('laser_ativo'):
                        pos_x_umbra = (largura_mapa // 2) - (largura_boss // 2)
                        pos_y_umbra = (altura_mapa // 2) - (altura_boss // 2)
                        
                        estado_atual_ia['laser_ativo'] = {
                            'tempo_inicio': agora,
                            'fase': 'carregando',
                            'rodada': 1,              # Inicia na Rodada 1
                            'duracao_carga': 1500,    # 1.5s de carga entre cada estágio
                            'duracao_disparo': 4000   # 4s atirando por estágio
                        }
                        estado_atual_ia['carga_atrito'] = 0
                

        # 5. Manutenção de Projéteis no Mapa
        dentro_mapa = 0 <= disparo["rect"].x < largura_mapa and 0 <= disparo["rect"].y < altura_mapa
        if dentro_mapa and not atingiu_boss and not interceptado:
            novos_disparos.append(disparo)
        elif not atingiu_boss and not interceptado:
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

    nova_lista = []
    for efeito in efeitos_texto:
        tempo_passado = tempo_atual - efeito["tempo_inicio"]
        if tempo_passado <= 800:  # mostra por 2 segundos
            fonte_efeito = pygame.font.Font(None, 28)
            x = efeito["x"]
            y = efeito["y"] - (tempo_passado // 25)
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
        # Desenhar o segundo personagem ao lado do personagem original
        pos_x_segundo_personagem = pos_x_personagem + largura_personagem + 4
        pos_y_segundo_personagem = pos_y_personagem
        # Desenhar sombra do Trembo
        desenhar_sombra(tela, pos_x_segundo_personagem, pos_y_segundo_personagem, largura_personagem, altura_personagem)
        tela.blit(frames_animacao_trembo[direcao_atual][frame_atual], (pos_x_segundo_personagem, pos_y_segundo_personagem))
    if trembo and tempo_atual - tempo_ultima_regeneracao >= Tempo_cura and vida < vida_maxima:
        cura_trembo = vida_maxima * porcentagem_cura
        
        # Mantendo a interceptação do Corta-Cura (Fase 6)
        if player_hemorragia_ativa and tempo_atual < tempo_fim_hemorragia:
            cura_trembo *= (1.0 - penalidade_cura_percentual)
            
        vida = min(vida_maxima, vida + cura_trembo)
        tempo_ultima_regeneracao = tempo_atual
    

    total_cartas_compradas = sum(cartas_compradas.values())
    custo_carta_atual = custo_base_carta + (total_cartas_compradas * custo_por_carta)
    # Verifica se a pontuação atingiu 1500 e se o jogador pressionou 'Q'
   
        

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

    tela.blit(cursor_imagem, (mouse_x, mouse_y))
    exibir_cronometro(tela)
    pygame.display.flip()
    FPS.tick(100)  # Limita a 60 FPS


# Encerrar o Pygame
pygame.quit()
sys.exit()