
#Este projeto está licenciado sob a Creative Commons Attribution-NonCommercial-ShareAlike 4.0.
#Uso comercial é estritamente proibido. Modificações e redistribuições são permitidas sob as mesmas condições.



import pygame
import sys
import importlib
import os
import json
import uuid
import pyperclip
from Config_Teclas import tela_de_controles,carregar_config_teclas
from Variaveis import largura_tela, altura_tela, python
from rede import descobrir_host_udp, conectar_ao_host
from audio_manager import carregar_config_audio, aplicar_volume_musica
from utils import configurar_tela, tocar_trailer_se_necessario, redimensionar_cover


# --- Declaração de Variáveis Globais (Inicialização Adiada para Evitar Telas Pretas por Dupla Importação) ---
tela = None
fundo_menu1 = None
fundo_menu2 = None
fundo_menu3 = None
fundo_menu4 = None
fundo_menu5 = None
imagens_fundo = []

caminho_fonte_letras = "Texto/Broken.otf"
tamanho_fonte_letras = 20
caminho_fonte_letra1 = "Texto/World.otf"
caminho_fonte_titulo = "Texto/Top_Menu.otf"
tamanho_fonte_titulo = 72

cor_letra = (40, 10, 88)
branco = (255, 255, 255)
cor_fundo_botao = (255, 255, 255, 100)
contorno_rosa = (255, 105, 180)
Letras_Of = caminho_fonte_letras

fonte_titulo = None
fonte_coop = None
fonte_letras = None
fonte_letra1 = None
fonte = None
fonte_instrucao = None
fonte_config = None
fonte_opcao = None
fonte_fallback_titulo = None
fonte_fallback_config = None

titulo_jogo = "Ruptura Temporal (2.0)"
posicao_titulo = (largura_tela // 2, altura_tela // 8)
ajuste_vertical = int(altura_tela * 0.12)

opcoes = ["Iniciar Jornada", "Configuração", "Sair"]
indice_selecionado = 0
DELAY_ENTRE_OPCOES = 100
ultima_mudanca_de_opcao = 0

tempo_exibicao_fundo1 = 5000
tempo_troca_fundo = 150
indice_fundo = 0
exibindo_fundo1 = True
ultima_troca = 0
controle = None
analogo_movido = False

def render_glitch_text_with_fallback(texto, fonte_glitch, fonte_fallback, cor):
    """
    Rendeiriza texto caractere por caractere. Usa a fonte_fallback se o caractere for acentuado
    ou especial, pois a fonte Doctor Glitch/Top_Menu não possui suporte a estes glifos.
    """
    surfaces = []
    largura_total = 0
    altura_max = 0
    
    for char in texto:
        # Verifica se o caractere precisa de fallback (acentos latinos, Ç, etc.)
        ord_char = ord(char)
        if ord_char > 127 or char in "ÇçÃãÕõÉéÍíÓóÚúÂâÊêÔôÀà":
            char_surf = fonte_fallback.render(char, True, cor)
        else:
            char_surf = fonte_glitch.render(char, True, cor)
        surfaces.append(char_surf)
        largura_total += char_surf.get_width()
        altura_max = max(altura_max, char_surf.get_height())
        
    surf_final = pygame.Surface((largura_total, altura_max), pygame.SRCALPHA)
    x_offset = 0
    for char_surf in surfaces:
        y_offset = (altura_max - char_surf.get_height()) // 2
        surf_final.blit(char_surf, (x_offset, y_offset))
        x_offset += char_surf.get_width()
        
    return surf_final

def inicializar_menu():
    global tela, fundo_menu1, fundo_menu2, fundo_menu3, fundo_menu4, fundo_menu5, imagens_fundo
    global fonte_titulo, fonte_coop, fonte_letras, fonte_letra1, fonte, fonte_instrucao, fonte_config, fonte_opcao
    global fonte_fallback_titulo, fonte_fallback_config
    global ultima_troca, ultima_mudanca_de_opcao, controle
    
    if tela is not None:
        return
        
    pygame.init()
    pygame.mouse.set_visible(False)
    centro_tela = (largura_tela // 2, altura_tela // 2)
    pygame.mouse.set_pos(centro_tela)
    
    tela = configurar_tela(largura_tela, altura_tela)
    tocar_trailer_se_necessario(tela)
    pygame.display.set_caption("Menu do Jogo")
    
    fundo_menu1 = pygame.image.load("Sprites/Melhoria_1.png")
    fundo_menu2 = pygame.image.load("Sprites/Melhoria_2.png")
    fundo_menu3 = pygame.image.load("Sprites/Melhoria_3.png")
    fundo_menu4 = pygame.image.load("Sprites/Melhoria_4.png")
    fundo_menu5 = pygame.image.load("Sprites/Melhoria_5.png")
    
    fundo_menu1 = redimensionar_cover(fundo_menu1, largura_tela, altura_tela)
    fundo_menu2 = redimensionar_cover(fundo_menu2, largura_tela, altura_tela)
    fundo_menu3 = redimensionar_cover(fundo_menu3, largura_tela, altura_tela)
    fundo_menu4 = redimensionar_cover(fundo_menu4, largura_tela, altura_tela)
    fundo_menu5 = redimensionar_cover(fundo_menu5, largura_tela, altura_tela)
    
    imagens_fundo.extend([fundo_menu1, fundo_menu4, fundo_menu2, fundo_menu4, fundo_menu5, fundo_menu3, fundo_menu2, fundo_menu3,
                          fundo_menu4, fundo_menu5, fundo_menu3, fundo_menu2, fundo_menu5])
                          
    fonte_titulo = pygame.font.Font(caminho_fonte_titulo, tamanho_fonte_titulo)
    ajuste_tamanho_fonte = int(tamanho_fonte_titulo * 0.80)
    fonte_coop = pygame.font.Font(caminho_fonte_titulo, ajuste_tamanho_fonte)
    
    fonte_letras = pygame.font.Font(caminho_fonte_letras, tamanho_fonte_letras)
    fonte_letra1 = pygame.font.Font(caminho_fonte_letra1, tamanho_fonte_letras)
    fonte = fonte_letras
    fonte_instrucao = pygame.font.Font(caminho_fonte_letras, 18)
    fonte_config = pygame.font.Font(caminho_fonte_titulo, 48)
    fonte_opcao = pygame.font.Font(caminho_fonte_letra1, 32)
    fonte_fallback_titulo = pygame.font.Font(caminho_fonte_letra1, tamanho_fonte_titulo)
    fonte_fallback_config = pygame.font.Font(caminho_fonte_letra1, 48)
    
    ultima_troca = pygame.time.get_ticks()
    ultima_mudanca_de_opcao = pygame.time.get_ticks()
    
    pygame.mixer.init()
    pygame.mixer.music.load("Sounds/Menu.mp3")
    config_audio = carregar_config_audio()
    aplicar_volume_musica(config_audio)
    pygame.mixer.music.play(-1)
    
    pygame.joystick.init()
    if pygame.joystick.get_count() > 0:
        controle = pygame.joystick.Joystick(0)
        controle.init()
    else:
        controle = None



def tela_inserir_nome(tela):
    nome = ""
    clock = pygame.time.Clock()
    fonte_input = pygame.font.Font("Texto/World.otf", 48)
    fonte_instrucao = pygame.font.Font(caminho_fonte_letras, 18)
    
    while True:
        tela.fill((10, 10, 10))
        
        texto_titulo = fonte_titulo.render("IDENTIFIQUE-SE", True, (0, 255, 204))
        tela.blit(texto_titulo, (largura_tela // 2 - texto_titulo.get_width() // 2, altura_tela // 4))
        
        texto_nome = fonte_input.render(nome + "_", True, branco)
        tela.blit(texto_nome, (largura_tela // 2 - texto_nome.get_width() // 2, altura_tela // 2))
        
        instrucao = fonte_instrucao.render("Pressione ENTER para confirmar sua existencia", True, (150, 150, 150))
        tela.blit(instrucao, (largura_tela // 2 - instrucao.get_width() // 2, altura_tela - 80))
        
        pygame.display.flip()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_RETURN, pygame.K_KP_ENTER] and len(nome) > 0:
                    with open("saves/nome_jogador.json", "w") as f:
                        json.dump({"nome": nome}, f)
                    return
                elif evento.key == pygame.K_BACKSPACE:
                    nome = nome[:-1]
                else:
                    if len(nome) < 16 and evento.unicode.isprintable():
                        nome += evento.unicode
        clock.tick(60)

def tela_escolha_modo():
    import socket, pyperclip
    from rede import descobrir_host_udp
    pygame.init()
    largura, altura = largura_tela, altura_tela
    tela = pygame.display.get_surface() or pygame.display.set_mode((largura, altura))
    pygame.display.set_caption("Escolher Modo de Jogo")
    fonte = pygame.font.Font("Texto/World.otf", 36)
    clock = pygame.time.Clock()

    opcoes = ["Host Game", "Join Game", "Offline"]
    selecionado = 0
    
    while True:
        tela.fill((15, 15, 15))
        titulo = fonte.render("Selecione o modo de jogo", True, (255, 255, 255))
        tela.blit(titulo, (largura // 2 - titulo.get_width() // 2, altura // 6))

        for i, texto in enumerate(opcoes):
            cor = (255, 255, 255) if i == selecionado else (120, 120, 120)
            render = fonte.render(texto, True, cor)
            tela.blit(render, (largura // 2 - render.get_width() // 2, altura // 3 + i * 70))

        pygame.display.flip()
        clock.tick(60)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return None, None
            elif evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado = (selecionado - 1) % len(opcoes)
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado = (selecionado + 1) % len(opcoes)
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    escolha = opcoes[selecionado]
                    # -----------------------------
                    # MODO HOST
                    # -----------------------------
                    if escolha == "Host Game":
                        return "host", None

                    # -----------------------------
                    # MODO JOIN
                    # -----------------------------
                    elif escolha == "Join Game":
                        ip_encontrado = descobrir_host_udp(timeout=5)
                        if ip_encontrado:
                            return "join", ip_encontrado
                        else:
                            tela.fill((15, 15, 15))
                            msg = fonte.render("Nenhum host LAN encontrado.", True, (255, 80, 80))
                            tela.blit(msg, (largura // 2 - msg.get_width() // 2, altura // 2))
                            pygame.display.flip()
                            pygame.time.delay(3000)

                    # -----------------------------
                    # MODO OFFLINE
                    # -----------------------------
                    elif escolha == "Offline":
                        return "offline", None



def tela_selecao_aurea(tela, fonte):
    aureas = [
        {"nome": "Racional", "imagem": "Sprites/aurea_cientista.png", "ativa": True},
        {"nome": "Impulsiva", "imagem": "Sprites/aurea_impulsiva.png", "ativa": True},
        {"nome": "Devota", "imagem": "Sprites/aurea_devota.png", "ativa": True},
        {"nome": "Vanguarda", "imagem": "Sprites/aurea_vanguarda.png", "ativa": True},
        {"nome": "?", "imagem": "Sprites/aurea_misteriosa.png", "ativa": False}
    ]

    # 🔹 Carrega os níveis salvos (ou usa 0 se o arquivo não existir)
    try:
        with open("saves/aureas_upgrade.json", "r") as f:
            data = json.load(f)
            upgrades = data.get("upgrades", {})
    except:
        upgrades = {}

    selecionado = 0
    clock = pygame.time.Clock()
    largura, altura = tela.get_size()

    largura_quadro = 120
    altura_quadro = 140
    espacamento = 50
    colunas = 3
    # --- Adicionar mensagem de instrução no canto inferior direito ---
    fonte_instrucao = pygame.font.Font(caminho_fonte_letras, 18)  # Use o mesmo estilo de fonte
    texto_instrucao = "A para esquerda e D para direita, espaço ou enter para selecionar"
    render_instrucao = fonte_instrucao.render(texto_instrucao, True, (0, 0, 0))  # Texto preto
    while True:
        tela.fill((15, 15, 15))

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
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
                    if aureas[selecionado]["ativa"]:
                        with open("saves/aurea_selecionada.json", "w") as file:
                            json.dump({"aurea": aureas[selecionado]["nome"]}, file)
                        return

        for i, aurea in enumerate(aureas):
            linha = i // colunas
            coluna = i % colunas

            x = largura // 2 - ((colunas * largura_quadro + (colunas - 1) * espacamento) // 2) + coluna * (largura_quadro + espacamento)
            y = altura // 4 + linha * (altura_quadro + 30)

            cor_borda = (255, 255, 255) if i == selecionado else (80, 80, 80)
            pygame.draw.rect(tela, cor_borda, (x, y, largura_quadro, altura_quadro), 3)

            cor_texto = cor_borda

            # 🔹 Nome com nível, se aplicável
            nome = aurea["nome"]
            if nome != "?" and aurea["ativa"]:
                nivel = upgrades.get(nome, 0)
                nome_display = f"{nome} (Nv. {nivel})" if nivel > 0 else nome
            else:
                nome_display = nome

            texto = fonte.render(nome_display, True, cor_texto)
            tela.blit(texto, (x + largura_quadro // 2 - texto.get_width() // 2, y - 25))

            try:
                imagem = pygame.image.load(aurea["imagem"]).convert_alpha()
                imagem = pygame.transform.scale(imagem, (largura_quadro, altura_quadro))
                tela.blit(imagem, (x, y))
            except:
                pass
        # Cria contorno branco desenhando o texto levemente deslocado em várias direções
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            contorno = fonte_instrucao.render(texto_instrucao, True, (255, 255, 255))  # Contorno branco
            tela.blit(contorno, (largura - render_instrucao.get_width() - 20 + dx,
                                altura - render_instrucao.get_height() - 20 + dy))

        # Renderiza o texto principal (preto)
        tela.blit(render_instrucao, (largura - render_instrucao.get_width() - 20,
                                    altura - render_instrucao.get_height() - 20))        
        pygame.display.flip()
        clock.tick(60)

def tela_decisao_tutorial(tela, fonte):
    opcoes = ["Sim", "Não"]
    selecionado = 0
    clock = pygame.time.Clock()

    while True:
        tela.fill((10, 10, 10))
        texto_titulo = fonte.render("Deseja jogar o tutorial?", True, (255, 255, 255))
        tela.blit(texto_titulo, (largura_tela // 2 - texto_titulo.get_width() // 2, altura_tela // 4))

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_LEFT, pygame.K_a]:
                    selecionado = (selecionado - 1) % len(opcoes)
                elif evento.key in [pygame.K_RIGHT, pygame.K_d]:
                    selecionado = (selecionado + 1) % len(opcoes)
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    with open("saves/tutorial_config.json", "w") as file:
                        json.dump({"mostrar_tutorial": opcoes[selecionado] == "Sim"}, file)
                    return opcoes[selecionado] == "Sim"

        for i, texto in enumerate(opcoes):
            cor = (255, 255, 255) if i == selecionado else (120, 120, 120)
            render = fonte.render(texto, True, cor)
            tela.blit(render, (largura_tela // 2 - 100 + i * 150, altura_tela // 2))

def tela_configuracoes_graficas(tela, fonte):
    """Tela de configurações gráficas"""
    global ultima_troca, exibindo_fundo1, indice_fundo
    # Carregar configurações atuais
    try:
        with open("saves/config_graficos.json", "r") as f:
            config = json.load(f)
    except:
        config = {
            "sombras_ativas": "dinamicas",
            "qualidade_grafica": "alta",
            "particulas_ativas": True,
            "efeitos_visuais": True,
            "fps_limite": 60
        }
    # Garante que chaves novas existam em configs antigas
    config.setdefault("fps_limite", 60)
    config.setdefault("particulas_ativas", True)
    config.setdefault("efeitos_visuais", True)
    
    opcoes_config = [
        {"nome": "Sombras", "chave": "sombras_ativas", "valores": ["desativadas", "simples", "dinamicas"], "labels": ["Desativadas", "Simples", "Dinâmicas"]},
        {"nome": "Qualidade Gráfica", "chave": "qualidade_grafica", "valores": ["alta", "media", "baixa"], "labels": ["Alta", "Média", "Baixa"]},
        {"nome": "Partículas", "chave": "particulas_ativas", "valores": [True, False], "labels": ["Ativadas", "Desativadas"]},
        {"nome": "Efeitos Visuais", "chave": "efeitos_visuais", "valores": [True, False], "labels": ["Ativados", "Desativados"]},
        {"nome": "Limite de FPS", "chave": "fps_limite", "valores": [30, 60, 120, 0], "labels": ["30 FPS", "60 FPS", "120 FPS", "Ilimitado"]},
        {"nome": "Voltar", "chave": None, "valores": None, "labels": None}
    ]
    
    descricoes_valores = {
        "sombras_ativas": {
            "desativadas": "Desliga sombras. Melhora muito o desempenho em PCs fracos.",
            "simples": "Sombras básicas estáticas. Bom equilíbrio de performance.",
            "dinamicas": "Sombras realistas em tempo real. Exige mais da placa de vídeo."
        },
        "qualidade_grafica": {
            "alta": "Texturas e renderização máxima. Para placas de vídeo modernas.",
            "media": "Qualidade padrão equilibrada para a maioria dos computadores.",
            "baixa": "Reduz resolução de efeitos para rodar liso em qualquer máquina."
        },
        "particulas_ativas": {
            True: "Partículas visuais de explosões e faíscas ligadas.",
            False: "Remove partículas para maior clareza visual e desempenho."
        },
        "efeitos_visuais": {
            True: "Ativa brilhos, distorções de tempo e glows premium.",
            False: "Desativa pós-processamento pesado para evitar lentidão."
        },
        "fps_limite": {
            30: "Limita a 30 FPS. Reduz consumo de energia e aquecimento.",
            60: "Padrão recomendado para jogabilidade fluida e estável.",
            120: "Para monitores de alta taxa de atualização (120Hz ou mais).",
            0: "Ilimitado. Roda o mais rápido possível (uso máximo de hardware)."
        }
    }
    
    selecionado = 0
    clock = pygame.time.Clock()
    fonte_titulo_tela = pygame.font.Font(caminho_fonte_titulo, 48)
    fonte_opcao_tela = pygame.font.Font(caminho_fonte_letra1, 24)
    fonte_valor_tela = pygame.font.Font(caminho_fonte_letras, 20)
    
    while True:
        agora = pygame.time.get_ticks()
        
        # Atualiza e desenha o fundo dinâmico
        if exibindo_fundo1:
            tela.blit(fundo_menu1, (0, 0))
            if agora - ultima_troca > tempo_exibicao_fundo1:
                exibindo_fundo1 = False
                ultima_troca = agora
                indice_fundo = 0
        else:
            tela.blit(imagens_fundo[indice_fundo], (0, 0))
            if agora - ultima_troca > tempo_troca_fundo:
                indice_fundo = (indice_fundo + 1) % len(imagens_fundo)
                ultima_troca = agora
                
        # Camada preta semi-transparente para contraste
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        tela.blit(overlay, (0, 0))
        
        # Título resiliente com Ç, G, Á, etc.
        texto_titulo = render_glitch_text_with_fallback("CONFIGURAÇÕES GRÁFICAS", fonte_titulo_tela, fonte_fallback_config, (0, 255, 204))
        retangulo_titulo = texto_titulo.get_rect(center=(largura_tela // 2, altura_tela // 8))
        
        # Sombra
        texto_titulo_sombra = render_glitch_text_with_fallback("CONFIGURAÇÕES GRÁFICAS", fonte_titulo_tela, fonte_fallback_config, (15, 5, 25))
        tela.blit(texto_titulo_sombra, (retangulo_titulo.left + 4, retangulo_titulo.top + 4))
        
        # Contorno
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            texto_titulo_contorno = render_glitch_text_with_fallback("CONFIGURAÇÕES GRÁFICAS", fonte_titulo_tela, fonte_fallback_config, contorno_rosa)
            tela.blit(texto_titulo_contorno, (retangulo_titulo.left + dx, retangulo_titulo.top + dy))
            
        tela.blit(texto_titulo, retangulo_titulo)
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado = (selecionado - 1) % len(opcoes_config)
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado = (selecionado + 1) % len(opcoes_config)
                elif evento.key in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d]:
                    if opcoes_config[selecionado]["chave"]:
                        chave = opcoes_config[selecionado]["chave"]
                        valores = opcoes_config[selecionado]["valores"]
                        valor_atual = config[chave]
                        indice_atual = valores.index(valor_atual)
                        
                        if evento.key in [pygame.K_RIGHT, pygame.K_d]:
                            novo_indice = (indice_atual + 1) % len(valores)
                        else:
                            novo_indice = (indice_atual - 1) % len(valores)
                        
                        config[chave] = valores[novo_indice]
                        
                        # Salvar imediatamente
                        with open("saves/config_graficos.json", "w") as f:
                            json.dump(config, f, indent=4)
                
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    if opcoes_config[selecionado]["nome"] == "Voltar":
                        return
                elif evento.key == pygame.K_ESCAPE:
                    return
        
        # Desenhar opções
        y_inicial = altura_tela // 4 + 20
        espacamento = 55
        
        for i, opcao in enumerate(opcoes_config):
            y_pos = y_inicial + i * espacamento
            
            # Caixa glassy para a opção selecionada
            if i == selecionado:
                rect_bg = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 42)
                pygame.draw.rect(tela, (0, 180, 200, 65), rect_bg, border_radius=6)
                pygame.draw.rect(tela, (0, 255, 230), rect_bg, width=2, border_radius=6)
                cor_nome = (255, 255, 255)
            else:
                cor_nome = (120, 120, 120)
            
            # Nome da opção
            texto_nome = fonte_opcao_tela.render(opcao["nome"], True, cor_nome)
            tela.blit(texto_nome, (largura_tela // 4, y_pos))
            
            # Valor atual (se não for "Voltar")
            if opcao["chave"]:
                valor_atual = config[opcao["chave"]]
                indice_valor = opcao["valores"].index(valor_atual)
                label_valor = opcao["labels"][indice_valor]
                
                cor_valor = (0, 255, 204) if i == selecionado else (150, 150, 150)
                texto_valor = fonte_valor_tela.render(label_valor, True, cor_valor)
                tela.blit(texto_valor, (largura_tela // 2 + 50, y_pos + 4))
                
                # Setas de navegação se selecionado
                if i == selecionado:
                    seta_esq = fonte_valor_tela.render("<", True, (255, 255, 255))
                    seta_dir = fonte_valor_tela.render(">", True, (255, 255, 255))
                    tela.blit(seta_esq, (largura_tela // 2 + 20, y_pos + 4))
                    tela.blit(seta_dir, (largura_tela // 2 + 230, y_pos + 4))
        
        # Caixa de Descrição Dinâmica
        rect_desc = pygame.Rect(largura_tela // 2 - 360, 480, 720, 50)
        pygame.draw.rect(tela, (15, 10, 30, 200), rect_desc, border_radius=8)
        pygame.draw.rect(tela, (0, 255, 230, 80), rect_desc, width=1, border_radius=8)
        
        opt_sel = opcoes_config[selecionado]
        if opt_sel["chave"] is None:
            texto_desc_str = "Retornar ao menu de configurações anterior."
        else:
            val_sel = config[opt_sel["chave"]]
            texto_desc_str = descricoes_valores[opt_sel["chave"]][val_sel]
            
        surf_desc_texto = fonte_valor_tela.render(texto_desc_str, True, (200, 200, 220))
        rect_desc_texto = surf_desc_texto.get_rect(center=rect_desc.center)
        tela.blit(surf_desc_texto, rect_desc_texto)
        
        # Instruções no rodapé
        instrucoes = [
            "W/S: Navegar | A/D: Alterar valor",
            "ENTER/ESPAÇO: Confirmar | ESC: Voltar"
        ]
        
        y_instrucao = altura_tela - 55
        for instrucao in instrucoes:
            texto_inst = fonte_instrucao.render(instrucao, True, (150, 150, 150))
            tela.blit(texto_inst, (largura_tela // 2 - texto_inst.get_width() // 2, y_instrucao))
            y_instrucao += 20
        
        pygame.display.flip()
        clock.tick(60)


def tela_configuracoes_audio(tela, fonte):
    """Tela de configurações de áudio"""
    global ultima_troca, exibindo_fundo1, indice_fundo
    # Carregar configurações atuais
    try:
        with open("saves/config_audio.json", "r") as f:
            config = json.load(f)
    except:
        config = {
            "volume_musica": 0.5,
            "volume_efeitos": 0.5,
            "volume_master": 1.0
        }
    
    selecionado = 0
    clock = pygame.time.Clock()
    fonte_titulo_tela = pygame.font.Font(caminho_fonte_titulo, 48)
    fonte_opcao_tela = pygame.font.Font(caminho_fonte_letra1, 24)
    fonte_valor_tela = pygame.font.Font(caminho_fonte_letras, 20)
    
    opcoes = ["volume_master", "volume_musica", "volume_efeitos", "voltar"]
    labels = ["Volume Master", "Volume Música", "Volume Efeitos", "Voltar"]
    
    descricoes_audio = {
        "volume_master": "Volume geral. Ajusta a música e os efeitos sonoros proporcionalmente.",
        "volume_musica": "Trilha sonora. Ajusta o volume da música de fundo e ambiente.",
        "volume_efeitos": "Efeitos sonoros. Ajusta o volume de tiros, explosões e impactos.",
        "voltar": "Retornar ao menu de configurações anterior."
    }
    
    while True:
        agora = pygame.time.get_ticks()
        
        # Atualiza e desenha o fundo dinâmico
        if exibindo_fundo1:
            tela.blit(fundo_menu1, (0, 0))
            if agora - ultima_troca > tempo_exibicao_fundo1:
                exibindo_fundo1 = False
                ultima_troca = agora
                indice_fundo = 0
        else:
            tela.blit(imagens_fundo[indice_fundo], (0, 0))
            if agora - ultima_troca > tempo_troca_fundo:
                indice_fundo = (indice_fundo + 1) % len(imagens_fundo)
                ultima_troca = agora
                
        # Camada preta semi-transparente para contraste
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        tela.blit(overlay, (0, 0))
        
        # Título de configurações de áudio
        texto_titulo = render_glitch_text_with_fallback("CONFIGURAÇÕES DE ÁUDIO", fonte_titulo_tela, fonte_fallback_config, (0, 255, 204))
        retangulo_titulo = texto_titulo.get_rect(center=(largura_tela // 2, altura_tela // 8))
        
        # Sombra
        texto_titulo_sombra = render_glitch_text_with_fallback("CONFIGURAÇÕES DE ÁUDIO", fonte_titulo_tela, fonte_fallback_config, (15, 5, 25))
        tela.blit(texto_titulo_sombra, (retangulo_titulo.left + 4, retangulo_titulo.top + 4))
        
        # Contorno
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            texto_titulo_contorno = render_glitch_text_with_fallback("CONFIGURAÇÕES DE ÁUDIO", fonte_titulo_tela, fonte_fallback_config, contorno_rosa)
            tela.blit(texto_titulo_contorno, (retangulo_titulo.left + dx, retangulo_titulo.top + dy))
            
        tela.blit(texto_titulo, retangulo_titulo)
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado = (selecionado - 1) % len(opcoes)
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado = (selecionado + 1) % len(opcoes)
                elif evento.key in [pygame.K_LEFT, pygame.K_a]:
                    if opcoes[selecionado] != "voltar":
                        chave = opcoes[selecionado]
                        config[chave] = max(0.0, config[chave] - 0.1)
                        
                        # Salvar e aplicar
                        with open("saves/config_audio.json", "w") as f:
                            json.dump(config, f, indent=4)
                        aplicar_volumes_audio(config)
                
                elif evento.key in [pygame.K_RIGHT, pygame.K_d]:
                    if opcoes[selecionado] != "voltar":
                        chave = opcoes[selecionado]
                        config[chave] = min(1.0, config[chave] + 0.1)
                        
                        # Salvar e aplicar
                        with open("saves/config_audio.json", "w") as f:
                            json.dump(config, f, indent=4)
                        aplicar_volumes_audio(config)
                
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    if opcoes[selecionado] == "voltar":
                        return
                elif evento.key == pygame.K_ESCAPE:
                    return
        
        # Desenhar opções
        y_inicial = altura_tela // 4 + 40
        espacamento = 65
        
        for i, opcao in enumerate(opcoes):
            y_pos = y_inicial + i * espacamento
            
            # Caixa glassy para a opção selecionada
            if i == selecionado:
                rect_bg = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 48)
                pygame.draw.rect(tela, (0, 180, 200, 65), rect_bg, border_radius=6)
                pygame.draw.rect(tela, (0, 255, 230), rect_bg, width=2, border_radius=6)
                cor_nome = (255, 255, 255)
            else:
                cor_nome = (120, 120, 120)
            
            # Nome da opção
            texto_nome = fonte_opcao_tela.render(labels[i], True, cor_nome)
            tela.blit(texto_nome, (largura_tela // 4, y_pos))
            
            # Barra de volume (se não for "Voltar")
            if opcao != "voltar":
                valor = config[opcao]
                
                # Barra de fundo
                barra_x = largura_tela // 2 - 20
                barra_y = y_pos + 10
                barra_largura = 200
                barra_altura = 16
                
                pygame.draw.rect(tela, (50, 50, 50), (barra_x, barra_y, barra_largura, barra_altura), border_radius=4)
                
                # Barra de preenchimento
                cor_barra = (0, 255, 204) if i == selecionado else (100, 200, 180)
                largura_preenchimento = int(barra_largura * valor)
                pygame.draw.rect(tela, cor_barra, (barra_x, barra_y, largura_preenchimento, barra_altura), border_radius=4)
                
                # Borda
                pygame.draw.rect(tela, (255, 255, 255), (barra_x, barra_y, barra_largura, barra_altura), 1, border_radius=4)
                
                # Porcentagem
                porcentagem = int(valor * 100)
                texto_porcentagem = fonte_valor_tela.render(f"{porcentagem}%", True, cor_nome)
                tela.blit(texto_porcentagem, (barra_x + barra_largura + 15, y_pos + 5))
                
                # Setas de navegação se selecionado
                if i == selecionado:
                    seta_esq = fonte_valor_tela.render("<", True, (255, 255, 255))
                    seta_dir = fonte_valor_tela.render(">", True, (255, 255, 255))
                    tela.blit(seta_esq, (barra_x - 25, y_pos + 5))
                    tela.blit(seta_dir, (barra_x + barra_largura + 50, y_pos + 5))
        
        # Caixa de Descrição Dinâmica
        rect_desc = pygame.Rect(largura_tela // 2 - 360, 480, 720, 50)
        pygame.draw.rect(tela, (15, 10, 30, 200), rect_desc, border_radius=8)
        pygame.draw.rect(tela, (0, 255, 230, 80), rect_desc, width=1, border_radius=8)
        
        opt_sel = opcoes[selecionado]
        texto_desc_str = descricoes_audio[opt_sel]
            
        surf_desc_texto = fonte_valor_tela.render(texto_desc_str, True, (200, 200, 220))
        rect_desc_texto = surf_desc_texto.get_rect(center=rect_desc.center)
        tela.blit(surf_desc_texto, rect_desc_texto)
        
        # Instruções no rodapé
        instrucoes = [
            "W/S: Navegar | A/D: Ajustar volume",
            "ENTER/ESPAÇO: Confirmar | ESC: Voltar"
        ]
        
        y_instrucao = altura_tela - 55
        for instrucao in instrucoes:
            texto_inst = fonte_instrucao.render(instrucao, True, (150, 150, 150))
            tela.blit(texto_inst, (largura_tela // 2 - texto_inst.get_width() // 2, y_instrucao))
            y_instrucao += 20
        
        pygame.display.flip()
        clock.tick(60)


def aplicar_volumes_audio(config):
    """Aplica as configurações de volume a todos os sons e músicas"""
    volume_master = config.get("volume_master", 1.0)
    volume_musica = config.get("volume_musica", 0.5)
    
    # Aplicar volume da música
    pygame.mixer.music.set_volume(volume_musica * volume_master)
    
    # Salvar configuração
    with open("saves/config_audio.json", "w") as f:
        json.dump(config, f, indent=4)


def executar_menu_principal(game_manager=None):
    """
    Executa o menu principal do jogo
    
    Args:
        game_manager: Instância do GameManager para controlar transições de estado
        
    Returns:
        str: Próximo estado ('jogo', 'sair', etc.) ou None se usar game_manager
    """
    inicializar_menu()
    global indice_selecionado, ultima_mudanca_de_opcao, analogo_movido
    global indice_fundo, exibindo_fundo1, ultima_troca
    
    # Reinicia música se não estiver tocando
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.load("Sounds/Menu.mp3")
        config_audio = carregar_config_audio()
        aplicar_volume_musica(config_audio)
        pygame.mixer.music.play(-1)
    
    clock = pygame.time.Clock()
    rodando = True
    
    opcao_confirmada = None
    tempo_confirmacao = 0
    particulas_eclosao = []
    
    while rodando:
        agora = pygame.time.get_ticks()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if game_manager:
                    from game_manager import EstadoJogo
                    game_manager.mudar_estado(EstadoJogo.SAIR)
                    return
                else:
                    pygame.mixer.music.stop()
                    pygame.quit()
                    sys.exit()
                    
            if opcao_confirmada is None:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_w and agora - ultima_mudanca_de_opcao >= DELAY_ENTRE_OPCOES:
                        indice_selecionado = (indice_selecionado - 1) % len(opcoes)
                        ultima_mudanca_de_opcao = agora
                    elif event.key == pygame.K_s and agora - ultima_mudanca_de_opcao >= DELAY_ENTRE_OPCOES:
                        indice_selecionado = (indice_selecionado + 1) % len(opcoes)
                        ultima_mudanca_de_opcao = agora
                    elif event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                        opcao_confirmada = indice_selecionado
                        tempo_confirmacao = agora
                        
                        particulas_eclosao = []
                        x_centro = 60 + 320 // 2
                        y_centro = (altura_tela // 2 - 20 + opcao_confirmada * 70) + 50 // 2
                        import random
                        for _ in range(40):
                            particulas_eclosao.append({
                                'x': x_centro + random.uniform(-160, 160),
                                'y': y_centro + random.uniform(-25, 25),
                                'dx': random.uniform(-8, 8),
                                'dy': random.uniform(-8, 8),
                                'cor': random.choice([(0, 255, 230), (255, 0, 128), (255, 255, 255)]),
                                'raio': random.uniform(2, 6),
                                'vida': 1.0
                            })
                    elif event.key == pygame.K_ESCAPE:
                        opcao_confirmada = 2  # Sair
                        tempo_confirmacao = agora
                        
                        particulas_eclosao = []
                        x_centro = 60 + 320 // 2
                        y_centro = (altura_tela // 2 - 20 + opcao_confirmada * 70) + 50 // 2
                        import random
                        for _ in range(40):
                            particulas_eclosao.append({
                                'x': x_centro + random.uniform(-160, 160),
                                'y': y_centro + random.uniform(-25, 25),
                                'dx': random.uniform(-8, 8),
                                'dy': random.uniform(-8, 8),
                                'cor': random.choice([(0, 255, 230), (255, 0, 128), (255, 255, 255)]),
                                'raio': random.uniform(2, 6),
                                'vida': 1.0
                            })
                            
                elif event.type == pygame.JOYAXISMOTION and controle is not None:
                    if event.axis == 1 and abs(controle.get_axis(0)) < 0.2:
                        if not analogo_movido:
                            if event.value > 0.5:
                                indice_selecionado = (indice_selecionado + 1) % len(opcoes)
                                analogo_movido = True
                            elif event.value < -0.5:
                                indice_selecionado = (indice_selecionado - 1) % len(opcoes)
                                analogo_movido = True
                    elif event.axis == 1 and abs(event.value) < 0.5:
                        analogo_movido = False
                        
                elif event.type == pygame.JOYBUTTONDOWN and controle is not None:
                    if event.button == 0:  # Botão A
                        opcao_confirmada = indice_selecionado
                        tempo_confirmacao = agora
                        
                        particulas_eclosao = []
                        x_centro = 60 + 320 // 2
                        y_centro = (altura_tela // 2 - 20 + opcao_confirmada * 70) + 50 // 2
                        import random
                        for _ in range(40):
                            particulas_eclosao.append({
                                'x': x_centro + random.uniform(-160, 160),
                                'y': y_centro + random.uniform(-25, 25),
                                'dx': random.uniform(-8, 8),
                                'dy': random.uniform(-8, 8),
                                'cor': random.choice([(0, 255, 230), (255, 0, 128), (255, 255, 255)]),
                                'raio': random.uniform(2, 6),
                                'vida': 1.0
                            })

        # Lógica de troca de imagem de fundo
        agora = pygame.time.get_ticks()
        
        if exibindo_fundo1:
            tela.blit(fundo_menu1, (0, 0))
            if agora - ultima_troca > tempo_exibicao_fundo1:
                exibindo_fundo1 = False
                ultima_troca = agora
                indice_fundo = 0
        else:
            tela.blit(imagens_fundo[indice_fundo], (0, 0))
            if agora - ultima_troca > tempo_troca_fundo:
                indice_fundo += 1
                ultima_troca = agora
                
                if indice_fundo >= len(imagens_fundo):
                    exibindo_fundo1 = True
                    indice_fundo = 0

        # Renderizar opções do menu (AAA Premium Sci-Fi)
        for i, opcao in enumerate(opcoes):
            x_botao = 60
            y_botao = altura_tela // 2 - 20 + i * 70
            largura_b = 320
            altura_b = 50
            
            surf_botao = pygame.Surface((largura_b, altura_b), pygame.SRCALPHA)
            
            if opcao_confirmada == i:
                decorrido = agora - tempo_confirmacao
                progresso = min(1.0, max(0.0, decorrido / 200.0))
                fator_escala = 1.0 + progresso * 0.4
                nova_largura = int(largura_b * fator_escala)
                nova_altura = int(altura_b * fator_escala)
                
                surf_eclosao = pygame.Surface((nova_largura, nova_altura), pygame.SRCALPHA)
                alpha_borda = int((1.0 - progresso) * 255)
                pygame.draw.rect(surf_eclosao, (0, 255, 230, alpha_borda), (0, 0, nova_largura, nova_altura), width=3, border_radius=10)
                
                x_ecl = x_botao - (nova_largura - largura_b) // 2
                y_ecl = y_botao - (nova_altura - altura_b) // 2
                tela.blit(surf_eclosao, (x_ecl, y_ecl))
                
                # Botão principal brilha em branco
                pygame.draw.rect(surf_botao, (255, 255, 255, 200), (0, 0, largura_b, altura_b), border_radius=8)
                texto_surf = fonte_letra1.render(opcao, True, (0, 0, 0))
                ret_texto = texto_surf.get_rect(center=(largura_b // 2 + 10, altura_b // 2))
                surf_botao.blit(texto_surf, ret_texto)
                
            elif i == indice_selecionado:
                import random
                is_glitch_frame = random.random() < 0.15 and opcao_confirmada is None
                glitch_offset_x = random.randint(-3, 3) if is_glitch_frame else 0
                glitch_offset_y = random.randint(-1, 1) if is_glitch_frame else 0
                
                alpha_bg = random.randint(45, 95) if is_glitch_frame else 65
                pygame.draw.rect(surf_botao, (0, 180, 200, alpha_bg), (0, 0, largura_b, altura_b), border_radius=8)
                pygame.draw.rect(surf_botao, (0, 255, 230), (0, 0, largura_b, altura_b), width=2, border_radius=8)
                pygame.draw.rect(surf_botao, (0, 255, 230), (0, 0, 6, altura_b), border_radius=8)
                
                if is_glitch_frame:
                    texto_ciano = fonte_letra1.render(opcao, True, (0, 255, 255))
                    texto_rosa = fonte_letra1.render(opcao, True, (255, 0, 128))
                    
                    ret_ciano = texto_ciano.get_rect(center=(largura_b // 2 + 10 + glitch_offset_x, altura_b // 2 + glitch_offset_y))
                    ret_rosa = texto_rosa.get_rect(center=(largura_b // 2 + 10 - glitch_offset_x, altura_b // 2 - glitch_offset_y))
                    
                    surf_botao.blit(texto_ciano, ret_ciano)
                    surf_botao.blit(texto_rosa, ret_rosa)
                    
                    if random.random() < 0.5:
                        y_linha = random.randint(5, altura_b - 5)
                        pygame.draw.line(surf_botao, (255, 255, 255), (5, y_linha), (largura_b - 5, y_linha), 1)
                else:
                    texto_surf = fonte_letra1.render(opcao, True, (255, 255, 255))
                    ret_texto = texto_surf.get_rect(center=(largura_b // 2 + 10, altura_b // 2))
                    surf_botao.blit(texto_surf, ret_texto)
            else:
                pygame.draw.rect(surf_botao, (15, 15, 25, 160), (0, 0, largura_b, altura_b), border_radius=8)
                pygame.draw.rect(surf_botao, (100, 100, 150, 45), (0, 0, largura_b, altura_b), width=1, border_radius=8)
                
                texto_surf = fonte_letras.render(opcao, True, (200, 200, 220))
                ret_texto = texto_surf.get_rect(center=(largura_b // 2, altura_b // 2))
                surf_botao.blit(texto_surf, ret_texto)
                
            tela.blit(surf_botao, (x_botao, y_botao))
            
        # Texto de instrução
        texto_instrucao = "Use W ou S para alternar e Espaço ou Enter para selecionar"
        
        # COOP no canto
        texto_coop = "COOP"
        cor_texto_coop = (0, 255, 255)
        cor_borda_coop = (255, 255, 0)
        render_coop = fonte_coop.render(texto_coop, True, cor_texto_coop)
        render_coop_borda = fonte_coop.render(texto_coop, True, cor_borda_coop)
        
        # Renderização do título
        texto_titulo = fonte_titulo.render(titulo_jogo, True, cor_letra)
        retangulo_titulo = texto_titulo.get_rect(center=posicao_titulo)
        
        # Posicionamento inteligente do COOP à direita do título para nunca sobrepor
        posicao_coop = (retangulo_titulo.right + 15, retangulo_titulo.centery - render_coop.get_height() // 2 + 5)
        
        # Desenho da borda COOP
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            tela.blit(render_coop_borda, (posicao_coop[0] + dx, posicao_coop[1] + dy))
        
        # Sombra e Contorno do Título (AAA volumetric effect)
        texto_titulo_sombra = fonte_titulo.render(titulo_jogo, True, (15, 5, 25))
        tela.blit(texto_titulo_sombra, (retangulo_titulo.left + 4, retangulo_titulo.top + 4))
        
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            texto_titulo_contorno = fonte_titulo.render(titulo_jogo, True, contorno_rosa)
            tela.blit(texto_titulo_contorno, (retangulo_titulo.left + dx, retangulo_titulo.top + dy))
            
        tela.blit(texto_titulo, retangulo_titulo)
        tela.blit(render_coop, posicao_coop)
        
        # Barra glassy de instrução no rodapé
        render_instrucao_aaa = fonte_instrucao.render(texto_instrucao, True, (0, 255, 230))
        largura_instr = render_instrucao_aaa.get_width() + 40
        altura_instr = 40
        
        surf_instr = pygame.Surface((largura_instr, altura_instr), pygame.SRCALPHA)
        pygame.draw.rect(surf_instr, (10, 10, 15, 200), (0, 0, largura_instr, altura_instr), border_radius=8)
        pygame.draw.rect(surf_instr, (0, 240, 255, 80), (0, 0, largura_instr, altura_instr), width=1, border_radius=8)
        
        surf_instr.blit(render_instrucao_aaa, (20, (altura_instr - render_instrucao_aaa.get_height()) // 2))
        tela.blit(surf_instr, (largura_tela - largura_instr - 20, altura_tela - altura_instr - 20))
        
        # Desenhar e atualizar partículas de eclosão
        if particulas_eclosao:
            for part in particulas_eclosao[:]:
                part['x'] += part['dx']
                part['y'] += part['dy']
                part['dx'] *= 0.96
                part['dy'] *= 0.96
                part['vida'] -= 0.05
                if part['vida'] <= 0:
                    particulas_eclosao.remove(part)
                    continue
                
                raio_atual = int(part['raio'] * part['vida'])
                if raio_atual > 0:
                    alpha_part = max(0, min(255, int(part['vida'] * 255)))
                    cor_alpha = part['cor'] + (alpha_part,)
                    surf_part = pygame.Surface((raio_atual * 2, raio_atual * 2), pygame.SRCALPHA)
                    pygame.draw.circle(surf_part, cor_alpha, (raio_atual, raio_atual), raio_atual)
                    tela.blit(surf_part, (int(part['x'] - raio_atual), int(part['y'] - raio_atual)))

        pygame.display.flip()
        clock.tick(60)
        
        # Lógica de confirmação após 200ms de eclosão (Transições de Tela)
        if opcao_confirmada is not None and agora - tempo_confirmacao >= 200:
            escolha = opcao_confirmada
            opcao_confirmada = None
            particulas_eclosao = []
            
            if escolha == 0:  # Iniciar Jornada
                tela_inserir_nome(tela)
                if not os.path.exists("saves/tutorial_config.json"):
                    mostrar_tutorial = tela_decisao_tutorial(tela, fonte)
                    with open("saves/tutorial_config.json", "w") as f:
                        json.dump({"mostrar_tutorial": mostrar_tutorial}, f)
                else:
                    with open("saves/tutorial_config.json", "r") as f:
                        mostrar_tutorial = json.load(f)["mostrar_tutorial"]

                tela_selecao_aurea(tela, fonte)
                modo, ip = tela_escolha_modo()
                
                if modo is None:
                    continue

                pygame.mixer.music.stop()

                with open("saves/modo_jogo.json", "w") as f:
                    json.dump({"modo": modo, "ip": ip}, f)

                if game_manager:
                    from game_manager import EstadoJogo
                    game_manager.mudar_estado(
                        EstadoJogo.JOGO_PRINCIPAL,
                        dados={'modo_jogo': modo, 'ip': ip, 'fase': 1}
                    )
                    return
                else:
                    if modo == 'offline':
                        import GAME
                        GAME.main()
                    else:
                        import GAMERE
                        GAMERE.main()
                    return

            elif escolha == 1:  # Configuração
                opcoes_config = ["Controles", "Gráficos", "Áudio", "Voltar"]
                indice_config = 0
                
                opcao_conf_confirmada = None
                tempo_conf_confirmacao = 0
                particulas_conf_eclosao = []
                
                config_rodando = True
                while config_rodando:
                    agora_conf = pygame.time.get_ticks()
                    
                    # Atualiza e desenha o fundo dinâmico do menu
                    if exibindo_fundo1:
                        tela.blit(fundo_menu1, (0, 0))
                        if agora_conf - ultima_troca > tempo_exibicao_fundo1:
                            exibindo_fundo1 = False
                            ultima_troca = agora_conf
                            indice_fundo = 0
                    else:
                        tela.blit(imagens_fundo[indice_fundo], (0, 0))
                        if agora_conf - ultima_troca > tempo_troca_fundo:
                            indice_fundo = (indice_fundo + 1) % len(imagens_fundo)
                            ultima_troca = agora_conf
                            
                    # Camada preta semi-transparente (glassmorphism/dimming overlay) para contraste
                    overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 185))
                    tela.blit(overlay, (0, 0))
                    
                    # Renderização do título de configurações com volumetric neon contorno
                    texto_config = render_glitch_text_with_fallback("CONFIGURAÇÕES", fonte_config, fonte_fallback_config, (0, 255, 204))
                    retangulo_config = texto_config.get_rect(center=(largura_tela // 2, altura_tela // 6))
                    
                    # Sombra
                    texto_config_sombra = render_glitch_text_with_fallback("CONFIGURAÇÕES", fonte_config, fonte_fallback_config, (15, 5, 25))
                    tela.blit(texto_config_sombra, (retangulo_config.left + 4, retangulo_config.top + 4))
                    
                    # Contorno
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        texto_config_contorno = render_glitch_text_with_fallback("CONFIGURAÇÕES", fonte_config, fonte_fallback_config, contorno_rosa)
                        tela.blit(texto_config_contorno, (retangulo_config.left + dx, retangulo_config.top + dy))
                        
                    tela.blit(texto_config, retangulo_config)
                    
                    for event_config in pygame.event.get():
                        if event_config.type == pygame.QUIT:
                            if game_manager:
                                from game_manager import EstadoJogo
                                game_manager.mudar_estado(EstadoJogo.SAIR)
                                return
                            else:
                                pygame.quit()
                                sys.exit()
                                
                        if opcao_conf_confirmada is None:
                            if event_config.type == pygame.KEYDOWN:
                                if event_config.key in [pygame.K_w, pygame.K_UP]:
                                    indice_config = (indice_config - 1) % len(opcoes_config)
                                elif event_config.key in [pygame.K_s, pygame.K_DOWN]:
                                    indice_config = (indice_config + 1) % len(opcoes_config)
                                elif event_config.key in [pygame.K_SPACE, pygame.K_RETURN]:
                                    opcao_conf_confirmada = indice_config
                                    tempo_conf_confirmacao = agora_conf
                                    
                                    particulas_conf_eclosao = []
                                    x_centro = largura_tela // 2
                                    y_centro = (altura_tela // 3 + opcao_conf_confirmada * 80) + 50 // 2
                                    import random
                                    for _ in range(40):
                                        particulas_conf_eclosao.append({
                                            'x': x_centro + random.uniform(-160, 160),
                                            'y': y_centro + random.uniform(-25, 25),
                                            'dx': random.uniform(-8, 8),
                                            'dy': random.uniform(-8, 8),
                                            'cor': random.choice([(0, 255, 230), (255, 0, 128), (255, 255, 255)]),
                                            'raio': random.uniform(2, 6),
                                            'vida': 1.0
                                        })
                                elif event_config.key == pygame.K_ESCAPE:
                                    config_rodando = False
                                    break
                                    
                    if not config_rodando:
                        break
                    
                    # Desenhar botões premium glassy no submenu
                    for i, opcao in enumerate(opcoes_config):
                        x_botao = largura_tela // 2 - 160
                        y_botao = altura_tela // 3 + i * 80
                        largura_b = 320
                        altura_b = 50
                        
                        surf_botao = pygame.Surface((largura_b, altura_b), pygame.SRCALPHA)
                        
                        if opcao_conf_confirmada == i:
                            decorrido = agora_conf - tempo_conf_confirmacao
                            progresso = min(1.0, max(0.0, decorrido / 200.0))
                            fator_escala = 1.0 + progresso * 0.4
                            nova_largura = int(largura_b * fator_escala)
                            nova_altura = int(altura_b * fator_escala)
                            
                            surf_eclosao = pygame.Surface((nova_largura, nova_altura), pygame.SRCALPHA)
                            alpha_borda = int((1.0 - progresso) * 255)
                            pygame.draw.rect(surf_eclosao, (0, 255, 230, alpha_borda), (0, 0, nova_largura, nova_altura), width=3, border_radius=10)
                            
                            x_ecl = x_botao - (nova_largura - largura_b) // 2
                            y_ecl = y_botao - (nova_altura - altura_b) // 2
                            tela.blit(surf_eclosao, (x_ecl, y_ecl))
                            
                            # Botão brilha em branco
                            pygame.draw.rect(surf_botao, (255, 255, 255, 200), (0, 0, largura_b, altura_b), border_radius=8)
                            texto_surf = fonte_letra1.render(opcao, True, (0, 0, 0))
                            ret_texto = texto_surf.get_rect(center=(largura_b // 2, altura_b // 2))
                            surf_botao.blit(texto_surf, ret_texto)
                            
                        elif i == indice_config:
                            import random
                            is_glitch_frame = random.random() < 0.15 and opcao_conf_confirmada is None
                            glitch_offset_x = random.randint(-3, 3) if is_glitch_frame else 0
                            glitch_offset_y = random.randint(-1, 1) if is_glitch_frame else 0
                            
                            alpha_bg = random.randint(45, 95) if is_glitch_frame else 65
                            pygame.draw.rect(surf_botao, (0, 180, 200, alpha_bg), (0, 0, largura_b, altura_b), border_radius=8)
                            pygame.draw.rect(surf_botao, (0, 255, 230), (0, 0, largura_b, altura_b), width=2, border_radius=8)
                            pygame.draw.rect(surf_botao, (0, 255, 230), (0, 0, 6, altura_b), border_radius=8)
                            
                            if is_glitch_frame:
                                texto_ciano = fonte_letra1.render(opcao, True, (0, 255, 255))
                                texto_rosa = fonte_letra1.render(opcao, True, (255, 0, 128))
                                
                                ret_ciano = texto_ciano.get_rect(center=(largura_b // 2 + glitch_offset_x, altura_b // 2 + glitch_offset_y))
                                ret_rosa = texto_rosa.get_rect(center=(largura_b // 2 - glitch_offset_x, altura_b // 2 - glitch_offset_y))
                                
                                surf_botao.blit(texto_ciano, ret_ciano)
                                surf_botao.blit(texto_rosa, ret_rosa)
                                
                                if random.random() < 0.5:
                                    y_linha = random.randint(5, altura_b - 5)
                                    pygame.draw.line(surf_botao, (255, 255, 255), (5, y_linha), (largura_b - 5, y_linha), 1)
                            else:
                                texto_surf = fonte_letra1.render(opcao, True, (255, 255, 255))
                                ret_texto = texto_surf.get_rect(center=(largura_b // 2, altura_b // 2))
                                surf_botao.blit(texto_surf, ret_texto)
                                
                            # Setas indicadoras piscantes
                            seta_esq = fonte_letra1.render("<", True, (0, 255, 230))
                            seta_dir = fonte_letra1.render(">", True, (0, 255, 230))
                            tela.blit(seta_esq, (x_botao - 45, y_botao + (altura_b - seta_esq.get_height()) // 2))
                            tela.blit(seta_dir, (x_botao + largura_b + 20, y_botao + (altura_b - seta_dir.get_height()) // 2))
                        else:
                            pygame.draw.rect(surf_botao, (15, 15, 25, 160), (0, 0, largura_b, altura_b), border_radius=8)
                            pygame.draw.rect(surf_botao, (100, 100, 150, 45), (0, 0, largura_b, altura_b), width=1, border_radius=8)
                            
                            texto_surf = fonte_letras.render(opcao, True, (200, 200, 220))
                            ret_texto = texto_surf.get_rect(center=(largura_b // 2, altura_b // 2))
                            surf_botao.blit(texto_surf, ret_texto)
                            
                        tela.blit(surf_botao, (x_botao, y_botao))
                        
                    # Desenhar e atualizar partículas de eclosão do submenu de config
                    if particulas_conf_eclosao:
                        for part in particulas_conf_eclosao[:]:
                            part['x'] += part['dx']
                            part['y'] += part['dy']
                            part['dx'] *= 0.96
                            part['dy'] *= 0.96
                            part['vida'] -= 0.05
                            if part['vida'] <= 0:
                                particulas_conf_eclosao.remove(part)
                                continue
                            
                            raio_atual = int(part['raio'] * part['vida'])
                            if raio_atual > 0:
                                alpha_part = max(0, min(255, int(part['vida'] * 255)))
                                cor_alpha = part['cor'] + (alpha_part,)
                                surf_part = pygame.Surface((raio_atual * 2, raio_atual * 2), pygame.SRCALPHA)
                                pygame.draw.circle(surf_part, cor_alpha, (raio_atual, raio_atual), raio_atual)
                                tela.blit(surf_part, (int(part['x'] - raio_atual), int(part['y'] - raio_atual)))
                                
                    pygame.display.flip()
                    clock.tick(60)
                    
                    # Lógica de confirmação após 200ms de eclosão do submenu
                    if opcao_conf_confirmada is not None and agora_conf - tempo_conf_confirmacao >= 200:
                        escolha_config = opcao_conf_confirmada
                        opcao_conf_confirmada = None
                        particulas_conf_eclosao = []
                        
                        if escolha_config == 0:  # Controles
                            config_teclas = carregar_config_teclas()
                            tela_de_controles(tela, config_teclas, largura_tela, altura_tela)
                        elif escolha_config == 1:  # Gráficos
                            tela_configuracoes_graficas(tela, fonte)
                        elif escolha_config == 2:  # Áudio
                            tela_configuracoes_audio(tela, fonte)
                        elif escolha_config == 3:  # Voltar
                            config_rodando = False

            elif escolha == 2:  # Sair
                if game_manager:
                    from game_manager import EstadoJogo
                    game_manager.mudar_estado(EstadoJogo.SAIR)
                    return
                else:
                    pygame.mixer.music.stop()
                    pygame.quit()
                    sys.exit()


# Código principal - mantém compatibilidade com execução direta
if __name__ == "__main__":
    # Tenta usar o GameManager se disponível
    try:
        from game_manager import obter_game_manager, EstadoJogo
        manager = obter_game_manager()
        manager.executar()
    except ImportError:
        # Fallback: executa modo legado
        executar_menu_principal()
