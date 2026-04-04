
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

pygame.init()
memoria_umbra = hb.MemoriaEvolutivaUmbra()


estalos = pygame.mixer.Sound("Sounds/Estalo.mp3")
estalos.set_volume(0.07) 

som_ataque_boss = pygame.mixer.Sound("Sounds/Hit_Boss1.mp3")
som_ataque_boss.set_volume(0.04) 


Disparo_Geo = pygame.mixer.Sound("Sounds/Disparo_Geo.wav")
Disparo_Geo.set_volume(0.04) 

Musica_tema_Boss1 = pygame.mixer.Sound("Sounds/Fase1_Boss.mp3")
Musica_tema_Boss1.set_volume(0.00) 

Musica_tema_fases = pygame.mixer.Sound("Sounds/Fase_boas.mp3")
Musica_tema_fases.set_volume(0.00) 

Som_tema_fases = pygame.mixer.Sound("Sounds/Praia.wav")
Som_tema_fases.set_volume(0.00) 

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
        estado_ativo = memoria_umbra.ultimo_estado
        
        # Mergulha na Matriz-Q para extrair os pesos reais formados pela dor e recompensa
        pesos_reais = {}
        if estado_ativo and estado_ativo in memoria_umbra.q_table:
            pesos_reais = memoria_umbra.q_table[estado_ativo]
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

        apolo.pensar((pos_x_personagem, pos_y_personagem), hitbox_alvo, lista_tiros_umbra, cds_ia, vida, vida_boss_atual, lista_esferas)
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

class AgenteApolo:
    def __init__(self):
        self.direcao_x = 0
        self.direcao_y = 0
        self.usar_dash = False
        self.mouse_simulado = [False, False, False]
        self.alvo_x = 0
        self.alvo_y = 0
        self.q_table = {}
        self.estado_anterior = "vazio"
        self.acao_anterior = 0
        self.vida_jogador_anterior = 0
        self.vida_boss_anterior = 0
        self.arquivo_memoria = "apolo_memoria.json"
        self.taxa_exploracao = 0.20
        self.carregar_memoria()
        self.atualizar_foco_progressivo()

    def carregar_memoria(self):
        import os, json
        if os.path.exists(self.arquivo_memoria):
            try:
                with open(self.arquivo_memoria, "r") as f:
                    self.q_table = json.load(f)
            except: pass

    def salvar_memoria(self):
        import json
        with open(self.arquivo_memoria, "w") as f:
            json.dump(self.q_table, f)

    def atualizar_foco_progressivo(self):
        import os, json
        try:
            if os.path.exists("historico_batalhas.json"):
                with open("historico_batalhas.json", "r") as f:
                    geracoes = len(json.load(f))
                self.taxa_exploracao = max(0.01, 0.20 * (0.985 ** geracoes))
        except: pass

    def obter_estado(self, pos_p, boss_hitbox, projeteis_boss, cds, esferas_energia):
        quadrante_boss = "C"
        if boss_hitbox:
            dx = boss_hitbox.centerx - pos_p[0]
            dy = boss_hitbox.centery - pos_p[1]
            if abs(dx) > abs(dy):
                quadrante_boss = "L" if dx > 0 else "O"
            else:
                quadrante_boss = "S" if dy > 0 else "N"
        
        perigo_dir = "LIVRE"
        import math
        for p in projeteis_boss:
            if math.hypot(p["rect"].centerx - pos_p[0], p["rect"].centery - pos_p[1]) < 150:
                dx = p["rect"].centerx - pos_p[0]
                dy = p["rect"].centery - pos_p[1]
                if abs(dx) > abs(dy):
                    perigo_dir = "L" if dx > 0 else "O"
                else:
                    perigo_dir = "S" if dy > 0 else "N"
                break
                
        esfera_dir = "NENHUMA"
        if esferas_energia:
            esf = esferas_energia[0]
            dx_e = esf["x"] - pos_p[0]
            dy_e = esf["y"] - pos_p[1]
            if abs(dx_e) > abs(dy_e):
                esfera_dir = "L" if dx_e > 0 else "O"
            else:
                esfera_dir = "S" if dy_e > 0 else "N"
        
        return f"{quadrante_boss}_{perigo_dir}_{cds['teleporte']}_{esfera_dir}"

    def pensar(self, pos_p, boss_hitbox, projeteis_boss, cds, vida_jogador, vida_boss, esferas_energia):
        import random
        self.direcao_x = 0
        self.direcao_y = 0
        self.usar_dash = False
        self.mouse_simulado[0] = False

        if boss_hitbox:
            self.alvo_x, self.alvo_y = boss_hitbox.center
            if cds["disparo"] == False: 
                self.mouse_simulado[0] = True

        recompensa = 0
        if self.vida_jogador_anterior > 0:
            if vida_jogador < self.vida_jogador_anterior: 
                recompensa -= 50
            if vida_boss < self.vida_boss_anterior: 
                recompensa += 30
            if vida_jogador > self.vida_jogador_anterior:
                recompensa += 100 

        self.vida_jogador_anterior = vida_jogador
        self.vida_boss_anterior = vida_boss

        estado_atual = self.obter_estado(pos_p, boss_hitbox, projeteis_boss, cds, esferas_energia)

        if self.estado_anterior not in self.q_table: 
            self.q_table[self.estado_anterior] = [0.0] * 5
        if estado_atual not in self.q_table: 
            self.q_table[estado_atual] = [0.0] * 5

        q_antigo = self.q_table[self.estado_anterior][self.acao_anterior]
        max_q_novo = max(self.q_table[estado_atual])
        self.q_table[self.estado_anterior][self.acao_anterior] = q_antigo + 0.2 * (recompensa + 0.9 * max_q_novo - q_antigo)

        if random.random() < self.taxa_exploracao:
            acao = random.choice([0, 1, 2, 3, 4])
        else:
            acao = self.q_table[estado_atual].index(max(self.q_table[estado_atual]))

        self.estado_anterior = estado_atual
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
        "Petro": 10.0, "Defesa": 10.0, "Sorte": 10.0, "Poison": 10.0, "Coletora": 10.0, "Mercenaria": 10.0
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
            velocidade_personagem += 0.02 + (inimigos_eliminados // 200) * 0.002
        elif carta == "Porção":
            aumento_vida = 650 + (inimigos_eliminados // 50) * 8
            vida_maxima += aumento_vida
            vida += int(vida_maxima * 0.30)
            vida_petro += int(vida_maxima_petro * 0.25)
            if vida_petro > vida_maxima_petro: vida_maxima_petro = vida_petro
        elif carta == "Disparo crescente":
            dano_person_hit += 15 + (inimigos_eliminados // 50) * 1.5
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
        elif carta == "Sorte":
            Chance_Sorte += 0.01 + (inimigos_eliminados // 400) * 0.002
        elif carta == "Poison":
            Poison_Active = True
            Dano_Veneno_Acumulado += 0.05
        elif carta == "Coletora":
            Executa_inimigo += 0.005
            Ultimo_Estalo = True
        elif carta == "Mercenaria":
            Mercenaria_Active = True

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
injetar_build_endgame(qtd_cartas_jogador=60)
###################################################################################################################################################################################################
# Geração de coordenadas estocásticas para o início do embate
pos_x_personagem, pos_y_personagem = gerar_posicao_aleatoria(largura_mapa, altura_mapa, largura_personagem, altura_personagem)
pos_x_petro= pos_x_personagem + largura_personagem + 4
pos_y_petro = pos_y_personagem

###################################################################################################PRINCIPAL#################################################################################################################
#LOOP PRINCIPAL
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

        apolo.pensar((pos_x_personagem, pos_y_personagem), boss_ref, proj_ref, cds, vida, vida_boss_atual, esferas_energia_umbra)
        
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
            if apolo.estado_anterior in apolo.q_table:
                apolo.q_table[apolo.estado_anterior][apolo.acao_anterior] -= 500.0
            
         
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
            if apolo.estado_anterior in apolo.q_table:
                apolo.q_table[apolo.estado_anterior][apolo.acao_anterior] += 500.0 
            memoria_umbra.treinar(-500.0, prioridade=True)
            
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
        # Criamos o dicionário que o 'processar_ia_umbra' espera
        boss_pos_ia = {
            'x': pos_x_umbra,
            'y': pos_y_umbra,
            'hitbox_centro': hitbox_boss5.center if 'hitbox_boss5' in locals() else (pos_x_umbra, pos_y_umbra)
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
                estados_relevantes = list(memoria_umbra.q_table.keys())[:]
                mapa_neural = {est: memoria_umbra.q_table[est] for est in estados_relevantes if isinstance(memoria_umbra.q_table[est], dict)}

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
                            if apolo.estado_anterior in apolo.q_table:
                                apolo.q_table[apolo.estado_anterior][apolo.acao_anterior] -= 2.0
                                
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
                            if apolo.estado_anterior in apolo.q_table:
                                apolo.q_table[apolo.estado_anterior][apolo.acao_anterior] -= 2.0
                        
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
            tela.blit(img_atual_boss, (pos_x_umbra, pos_y_umbra + offset_y_boss))
           
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
                    
                    # --- 2. RENDERIZAÇÃO DOS PROJÉTEIS ---
                    if p.get("tipo") == "furia":
                        cor_tiro = (138, 43, 226) # Roxo Intenso
                        raio = 12
                    else:
                        cor_tiro = (255, 50, 50)  # Vermelho Alerta
                        raio = 6

                    pygame.draw.circle(tela, cor_tiro, p["rect"].center, raio)
                    pygame.draw.circle(tela, (255, 255, 255), p["rect"].center, raio // 2)
                else:
                    memoria_umbra.treinar(-0.5)
                    estado_atual_ia['passiva_chance'] = 0.30
                    estado_atual_ia['passiva_reducao'] = 1.0
                    estado_atual_ia['intervalo'] = 1900

            estado_atual_ia['projeteis'] = projeteis_vivos

            # --- 3. DETECÇÃO DE DANO NO JOGADOR ---
            hitbox_player = pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
            for p in estado_atual_ia['projeteis'][:]:
                if p["rect"].colliderect(hitbox_player):
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
                    
                    chance_atual = estado_atual_ia.get('passiva_chance', 0.30)
                    if random.random() <= chance_atual:
                        reducao_atual = estado_atual_ia.get('passiva_reducao', 1.0)
                        nova_reducao = max(0.2, reducao_atual - 0.15) 
                        
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
                        if apolo.estado_anterior in apolo.q_table:
                            apolo.q_table[apolo.estado_anterior][apolo.acao_anterior] -= 5.0
                    
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
                            if apolo.estado_anterior in apolo.q_table:
                                apolo.q_table[apolo.estado_anterior][apolo.acao_anterior] -= 10.0
                        
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
                origem = caminho['origem']
                angulo = caminho['angulo']
                comp_total = caminho['comprimento']
                
                # ==========================================================
                # GESTÃO DE ESTADO E FASES DA ARMADILHA
                # ==========================================================
                if caminho['fase'] == 'crescimento':
                    # Fase 1: O caule avança até o limite. Inofensivo e fino.
                    progresso = min(1.0, tempo_decorrido / caminho['duracao_crescimento'])
                    comp_atual = comp_total * progresso
                    largura_atual = 10 
                    
                    if tempo_decorrido >= caminho['duracao_crescimento']:
                        caminho['fase'] = 'expansao'
                        caminho['tempo_inicio_expansao'] = agora

                elif caminho['fase'] == 'expansao':
                    # Fase 2: O caule desabrocha para os lados. Altamente letal.
                    tempo_exp = agora - caminho['tempo_inicio_expansao']
                    progresso = min(1.0, tempo_exp / caminho['duracao_expansao'])
                    comp_atual = comp_total
                    largura_atual = 10 + (caminho['largura_maxima'] - 10) * progresso
                    
                    if tempo_exp >= caminho['duracao_expansao']:
                        estado_atual_ia['caminho_espinhos'] = None 

                elif caminho['fase'] == 'recolhimento':
                    # Fase 3: A armadilha fisgou o jogador. Animação de tortura.
                    comp_atual = comp_total
                    largura_atual = 15 # Contração visual imediata
                    
                    if 'alvo_puxao' in caminho:
                        alvo_px, alvo_py = caminho['alvo_puxao']
                        
                        # Interpolação Linear: aproxima a personagem do centro 15% a cada frame
                        pos_x_personagem += (alvo_px - pos_x_personagem) * 0.15
                        pos_y_personagem += (alvo_py - pos_y_personagem) * 0.15
                        
                        # Renderiza raízes dinâmicas amarrando a personagem
                        cx = int(pos_x_personagem + largura_personagem / 2)
                        cy = int(pos_y_personagem + altura_personagem / 2)
                        for j in range(4):
                            # Rotação em espiral convergente para o centro
                            ang_raiz = (agora * 0.02) + (j * math.pi / 2)
                            raio_raiz = max(0, 45 - (agora - caminho['tempo_inicio_recolhimento']) * 0.08)
                            
                            rx = cx + math.cos(ang_raiz) * raio_raiz
                            ry = cy + math.sin(ang_raiz) * raio_raiz
                            
                            # Desenha os tentáculos espessos e as farpas
                            pygame.draw.line(tela, (20, 60, 20), (cx, cy), (rx, ry), 5)
                            pygame.draw.circle(tela, (180, 200, 120), (int(rx), int(ry)), 3)
                    
                    if agora - caminho['tempo_inicio_recolhimento'] >= 600:
                        estado_atual_ia['caminho_espinhos'] = None

                # ==========================================================
                # RENDERIZAÇÃO BOTÂNICA PROCEDURAL E COLISÃO VETORIAL
                # ==========================================================
                if estado_atual_ia.get('caminho_espinhos'):
                    dx_comp = math.cos(angulo) * comp_atual
                    dy_comp = math.sin(angulo) * comp_atual
                    fim_x = origem[0] + dx_comp
                    fim_y = origem[1] + dy_comp
                    
                    cor_caule_principal = (20, 60, 20)      # Verde escuro e putrefato
                    cor_caule_secundario = (34, 90, 34)     # Verde mais vivo
                    cor_espinho = (180, 200, 120)           # Verde-claro/amarelado afiado
                    cor_flor = (220, 30, 30)                # Vermelho sangue (flores da coroa)
                    
                    pontos_caule_1 = []
                    pontos_caule_2 = []
                    
                    # Resolvemos a renderização a cada 15 pixels de distância ao longo da reta
                    num_segmentos = max(2, int(comp_atual / 15)) 
                    
                    for i in range(num_segmentos + 1):
                        dist = min(i * 15, comp_atual)
                        base_x = origem[0] + math.cos(angulo) * dist
                        base_y = origem[1] + math.sin(angulo) * dist
                        
                        # A oscilação faz os caules se contorcerem (Ondas Senoidais)
                        mod_fase = 0.1 if caminho['fase'] == 'recolhimento' else 1.0
                        wobble_1 = math.sin(i * 0.5 + (agora * 0.003)) * (largura_atual * 0.35) * mod_fase
                        wobble_2 = math.cos(i * 0.7 - (agora * 0.002)) * (largura_atual * 0.35) * mod_fase
                        
                        dx_perp = math.cos(angulo + math.pi/2)
                        dy_perp = math.sin(angulo + math.pi/2)
                        
                        pontos_caule_1.append((base_x + dx_perp * wobble_1, base_y + dy_perp * wobble_1))
                        pontos_caule_2.append((base_x + dx_perp * wobble_2, base_y + dy_perp * wobble_2))

                    # Renderiza caules, espinhos e flores procedurais
                    if len(pontos_caule_1) > 1:
                        for i in range(1, len(pontos_caule_1)):
                            p_ant1, p_atu1 = pontos_caule_1[i-1], pontos_caule_1[i]
                            p_ant2, p_atu2 = pontos_caule_2[i-1], pontos_caule_2[i]
                            
                            # Espessura afunila até a ponta do caminho
                            espessura = max(2, int((largura_atual * 0.15) * (1.0 - (i / num_segmentos))))
                            
                            # Sombras e Caules entrelaçados
                            pygame.draw.line(tela, (10, 20, 10), (p_ant1[0]+2, p_ant1[1]+2), (p_atu1[0]+2, p_atu1[1]+2), espessura)
                            pygame.draw.line(tela, cor_caule_principal, p_ant1, p_atu1, espessura)
                            pygame.draw.line(tela, cor_caule_secundario, p_ant2, p_atu2, max(1, espessura - 1))
                            
                            # Pseudo-aleatoriedade com Hash (Garante geometria fixa sem piscar)
                            hash_val = (i * 37) % 100 
                            
                            # Renderiza Espinhos Afiados
                            if hash_val < 35 and caminho['fase'] != 'recolhimento':
                                dir_espinho = 1 if hash_val < 17 else -1
                                ang_espinho = angulo + (math.pi/2.5 * dir_espinho) + math.sin(agora*0.005 + i)*0.3
                                tam_espinho = 8 + (largura_atual * 0.15)
                                
                                ponta_x = p_atu1[0] + math.cos(ang_espinho) * tam_espinho
                                ponta_y = p_atu1[1] + math.sin(ang_espinho) * tam_espinho
                                
                                base1_x = p_atu1[0] + math.cos(ang_espinho + 1.2) * espessura
                                base1_y = p_atu1[1] + math.sin(ang_espinho + 1.2) * espessura
                                base2_x = p_atu1[0] + math.cos(ang_espinho - 1.2) * espessura
                                base2_y = p_atu1[1] + math.sin(ang_espinho - 1.2) * espessura
                                
                                pygame.draw.polygon(tela, cor_espinho, [(ponta_x, ponta_y), (base1_x, base1_y), (base2_x, base2_y)])

                            # Renderiza flores desabrochando apenas na Expansão
                            if caminho['fase'] == 'expansao' and 40 <= hash_val < 55:
                                pulso_flor = abs(math.sin(agora * 0.003 + i)) * 3
                                pygame.draw.circle(tela, cor_flor, (int(p_atu2[0]), int(p_atu2[1])), int(2 + pulso_flor))
                                pygame.draw.circle(tela, (255, 200, 100), (int(p_atu2[0]), int(p_atu2[1])), 1) # Miolo amarelo
                    
                    # --------------------------------------------------------
                    # FÍSICA E COLISÃO (CUIDADO: ATIVA SOMENTE NA EXPANSÃO)
                    # --------------------------------------------------------
                    if caminho['fase'] == 'expansao':
                        px_centro = personagem_rect.centerx
                        py_centro = personagem_rect.centery
                        
                        vetor_linha_x = fim_x - origem[0]
                        vetor_linha_y = fim_y - origem[1]
                        vetor_ponto_x = px_centro - origem[0]
                        vetor_ponto_y = py_centro - origem[1]
                        
                        len_sq = vetor_linha_x**2 + vetor_linha_y**2
                        param = (vetor_ponto_x * vetor_linha_x + vetor_ponto_y * vetor_linha_y) / len_sq if len_sq > 0 else -1
                            
                        if param < 0:
                            ponto_prox_x, ponto_prox_y = origem[0], origem[1]
                        elif param > 1:
                            ponto_prox_x, ponto_prox_y = fim_x, fim_y
                        else:
                            ponto_prox_x = origem[0] + param * vetor_linha_x
                            ponto_prox_y = origem[1] + param * vetor_linha_y
                            
                        dist_ao_centro_linha = math.hypot(px_centro - ponto_prox_x, py_centro - ponto_prox_y)
                        
                        # O Puxão Magnético e o Castigo das Lâminas de Sangue
                        if dist_ao_centro_linha <= largura_atual / 2:
                            caminho['fase'] = 'recolhimento'
                            caminho['tempo_inicio_recolhimento'] = agora
                            
                            # 1. Trava o alvo geométrico para o puxão
                            caminho['alvo_puxao'] = (ponto_prox_x - (largura_personagem / 2), ponto_prox_y - (altura_personagem / 2))
                            
                            # 2. Paralisa a personagem cortando o input motor por 600ms
                            estado_atual_ia['fim_stun'] = agora + 600 
                            
                            # 3. Aplica o Sangramento e o Corta-Cura
                            vida -= 85
                            player_hemorragia_ativa = True
                            tempo_fim_hemorragia = agora + 6000 
                            penalidade_cura_percentual = 0.85 # Aniquila 85% de toda a cura
                            
                            # --- PUNIÇÃO APOLO: Punição máxima por cair na armadilha mortal ---
                            if apolo.estado_anterior in apolo.q_table:
                                apolo.q_table[apolo.estado_anterior][apolo.acao_anterior] -= 25.0
                            
                            efeitos_texto.append({
                                "texto": "SANGRAMENTO FATAL!",
                                "x": pos_x_personagem + random.randint(-20, 20),
                                "y": pos_y_personagem - 40,
                                "tempo_inicio": agora,
                                "cor": (255, 0, 0)
                            })

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
                            if apolo.estado_anterior in apolo.q_table:
                                apolo.q_table[apolo.estado_anterior][apolo.acao_anterior] -= 15.0
                                
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
                pulso = math.sin(agora * 0.005) * 5
                raio_esfera = 15 + pulso
                
                pygame.draw.circle(tela, (0, 255, 150), (int(esfera["x"]), int(esfera["y"])), int(raio_esfera + 8), 2)
                pygame.draw.circle(tela, (50, 255, 200), (int(esfera["x"]), int(esfera["y"])), int(raio_esfera))
                pygame.draw.circle(tela, (255, 255, 255), (int(esfera["x"]), int(esfera["y"])), int(raio_esfera * 0.4))
                
                cx_p = pos_x_personagem + largura_personagem // 2
                cy_p = pos_y_personagem + altura_personagem // 2
                distancia_coleta = math.hypot(cx_p - esfera["x"], cy_p - esfera["y"])
                
                if distancia_coleta <= 45:
                    vida_perdida = vida_maxima - vida
                    cura_aplicada = int(vida_perdida * 0.50)
                    vida += cura_aplicada
                    
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
            tela.blit(img_atual_boss, (pos_x_umbra, pos_y_umbra + offset_y_boss))
            
    ###############################################   DESENHA O PERSONAGEM NA TELA ################################
    if estado_atual_ia.get('miasma_ativo'):
        tela.blit(imagem_personagem_doente, (pos_x_personagem, pos_y_personagem))
    else:
        tela.blit(frames_animacao[direcao_atual][frame_atual], (pos_x_personagem, pos_y_personagem))
    
    # Se a IA ainda não foi processada neste frame, garantimos que o estado exista
    if 'estado_atual_ia' not in locals() and 'estado_atual_ia' not in globals():
        estado_atual_ia = {'parede_ativa': False}

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
                # Aplicação de Dano e Treino
                if vida_umbra > 0:
                    vida_umbra -= dano_final
                    
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

    # Renderizar os disparos
    for disparo in disparos:
        tela.blit(frames_disparo[frame_atual_disparo], disparo["rect"].topleft)

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