
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
from audio_manager import carregar_config_audio, aplicar_volume_musica, aplicar_volume_som
from utils import configurar_tela, tocar_trailer_se_necessario, redimensionar_cover, carregar_upgrade_aureas
from sons_procedurais import tocar_hover, tocar_selecionar


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

def mostrar_erro_lan(tela, font_titulo, font_desc):
    largura, altura = tela.get_size()
    duracao = 3000
    inicio = pygame.time.get_ticks()
    
    while pygame.time.get_ticks() - inicio < duracao:
        tela.fill((15, 12, 20))
        
        # Grade cibernética sutil
        for gx in range(40, largura, 80):
            for gy in range(40, altura, 80):
                pygame.draw.circle(tela, (255, 80, 80, 12), (gx, gy), 1)
                
        # Mensagem de erro centralizada
        txt_err = font_titulo.render("SEM CONEXAO ENCONTRADA", True, (255, 80, 80))
        txt_desc = font_desc.render("Nao foi possivel encontrar nenhuma partida LAN ativa na rede local.", True, (200, 200, 200))
        txt_desc2 = font_desc.render("Certifique-se de que o host iniciou a partida e tente novamente.", True, (140, 140, 150))
        
        tela.blit(txt_err, (largura // 2 - txt_err.get_width() // 2, altura // 2 - 50))
        tela.blit(txt_desc, (largura // 2 - txt_desc.get_width() // 2, altura // 2 + 10))
        tela.blit(txt_desc2, (largura // 2 - txt_desc2.get_width() // 2, altura // 2 + 40))
        
        pygame.display.flip()
        pygame.time.Clock().tick(60)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
                return # Pula o aviso com qualquer entrada

def tela_escolha_modo():
    import socket, pyperclip, random
    from rede import descobrir_host_udp
    pygame.init()
    largura, altura = largura_tela, altura_tela
    tela = pygame.display.get_surface() or pygame.display.set_mode((largura, altura))
    pygame.display.set_caption("Escolher Modo de Jogo")
    
    # Carregar fontes com fallback seguro
    try:
        font_titulo = pygame.font.Font("Texto/Top_Menu.otf", 44)
    except:
        font_titulo = pygame.font.Font(None, 44)
        
    try:
        font_card_title = pygame.font.Font("Texto/World.otf", 26)
    except:
        font_card_title = pygame.font.Font(None, 26)
        
    try:
        font_card_desc = pygame.font.Font("Texto/rainyhearts.ttf", 20)
    except:
        font_card_desc = pygame.font.Font(None, 20)
        
    try:
        font_btn = pygame.font.Font("Texto/World.otf", 24)
    except:
        font_btn = pygame.font.Font(None, 24)
        
    clock = pygame.time.Clock()
    
    # Fase: "principal" (Solo ou Coop) ou "coop_sub" (Criar ou Entrar)
    fase_tela = "principal"
    selecionado_principal = 0  # 0: Jogar Solo, 1: Cooperativo
    selecionado_sub = 0        # 0: Criar, 1: Entrar, 2: Voltar
    
    # Partículas sutis ao fundo
    particulas = []
    for _ in range(25):
        particulas.append({
            "x": random.uniform(0, largura),
            "y": random.uniform(0, altura),
            "vy": random.uniform(-0.6, -0.2),
            "alpha": random.randint(30, 95),
            "size": random.uniform(1.2, 2.5)
        })
        
    btn_back_rect = pygame.Rect(40, 40, 120, 36)
    
    while True:
        agora = pygame.time.get_ticks()
        
        # Desenhar Fundo Escuro Sci-Fi
        tela.fill((10, 8, 16))
        
        # Desenhar Grade Tecnológica de Pontos
        for gx in range(40, largura, 80):
            for gy in range(40, altura, 80):
                pygame.draw.circle(tela, (0, 255, 204, 10), (gx, gy), 1)
                
        # Atualizar e Desenhar Partículas
        for p in particulas:
            p["y"] += p["vy"]
            if p["y"] < 0:
                p["y"] = altura
                p["x"] = random.uniform(0, largura)
                
            p_surf = pygame.Surface((int(p["size"]*2), int(p["size"]*2)), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (0, 255, 204, p["alpha"]), (int(p["size"]), int(p["size"])), int(p["size"]))
            tela.blit(p_surf, (int(p["x"]), int(p["y"])))
            
        # Título
        txt_titulo = font_titulo.render("MODO DE JOGO", True, (255, 255, 255))
        tela.blit(txt_titulo, (largura // 2 - txt_titulo.get_width() // 2, 70))
        
        mx, my = pygame.mouse.get_pos()
        clicado = False
        
        # Botão Voltar no Canto Superior Esquerdo
        is_hover_back = btn_back_rect.collidepoint(mx, my)
        color_back = (180, 100, 255) if is_hover_back else (100, 100, 110)
        bg_back = (25, 20, 38, 200) if is_hover_back else (12, 10, 18, 120)
        
        surf_back = pygame.Surface((120, 36), pygame.SRCALPHA)
        pygame.draw.rect(surf_back, bg_back, (0, 0, 120, 36), border_radius=8)
        pygame.draw.rect(surf_back, color_back, (0, 0, 120, 36), width=1, border_radius=8)
        
        txt_back = font_card_desc.render("< VOLTAR", True, color_back)
        surf_back.blit(txt_back, (60 - txt_back.get_width() // 2, 18 - txt_back.get_height() // 2))
        tela.blit(surf_back, (40, 40))
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return None, None
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    clicado = True
                    if btn_back_rect.collidepoint(evento.pos):
                        tocar_selecionar()
                        if fase_tela == "coop_sub":
                            fase_tela = "principal"
                            selecionado_sub = 0
                        else:
                            return None, None
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    if fase_tela == "coop_sub":
                        fase_tela = "principal"
                        selecionado_sub = 0
                    else:
                        return None, None
                elif evento.key in [pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w]:
                    tocar_hover()
                    if fase_tela == "principal":
                        selecionado_principal = (selecionado_principal - 1) % 2
                    elif fase_tela == "coop_sub":
                        selecionado_sub = (selecionado_sub - 1) % 3
                elif evento.key in [pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s]:
                    tocar_hover()
                    if fase_tela == "principal":
                        selecionado_principal = (selecionado_principal + 1) % 2
                    elif fase_tela == "coop_sub":
                        selecionado_sub = (selecionado_sub + 1) % 3
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    if fase_tela == "principal":
                        if selecionado_principal == 0:
                            return "offline", None
                        else:
                            fase_tela = "coop_sub"
                            selecionado_sub = 0
                    elif fase_tela == "coop_sub":
                        if selecionado_sub == 0:
                            return "host", None
                        elif selecionado_sub == 1:
                            ip_encontrado = descobrir_host_udp(timeout=4)
                            if ip_encontrado:
                                return "join", ip_encontrado
                            else:
                                mostrar_erro_lan(tela, font_card_title, font_card_desc)
                        elif selecionado_sub == 2:
                            fase_tela = "principal"
                            selecionado_sub = 0
            
            # Suporte a Controle / Gamepad
            elif evento.type == pygame.JOYBUTTONDOWN and controle is not None:
                if evento.button == 0:  # Botão A
                    tocar_selecionar()
                    if fase_tela == "principal":
                        if selecionado_principal == 0:
                            return "offline", None
                        else:
                            fase_tela = "coop_sub"
                            selecionado_sub = 0
                    elif fase_tela == "coop_sub":
                        if selecionado_sub == 0:
                            return "host", None
                        elif selecionado_sub == 1:
                            ip_encontrado = descobrir_host_udp(timeout=4)
                            if ip_encontrado:
                                return "join", ip_encontrado
                            else:
                                mostrar_erro_lan(tela, font_card_title, font_card_desc)
                        elif selecionado_sub == 2:
                            fase_tela = "principal"
                            selecionado_sub = 0
                elif evento.button == 1:  # Botão B
                    tocar_selecionar()
                    if fase_tela == "coop_sub":
                        fase_tela = "principal"
                        selecionado_sub = 0
                    else:
                        return None, None
                            
        # Renderizar Fase Principal: Cards lado a lado
        if fase_tela == "principal":
            card_y = altura // 2 - 90
            card_w = 265
            card_h = 245
            
            # --- CARD ESQUERDO: JOGAR SOLO ---
            card_l_x = largura // 2 - 295
            rect_solo = pygame.Rect(card_l_x, card_y, card_w, card_h)
            is_hover_solo = rect_solo.collidepoint(mx, my)
            if is_hover_solo:
                if selecionado_principal != 0:
                    selecionado_principal = 0
                    tocar_hover()
                if clicado:
                    tocar_selecionar()
                    return "offline", None
                    
            is_sel_solo = (selecionado_principal == 0)
            bg_color_solo = (20, 16, 32, 205) if is_sel_solo else (12, 10, 18, 140)
            border_color_solo = (0, 255, 204) if is_sel_solo else (70, 70, 85)
            border_w_solo = 2 if is_sel_solo else 1
            
            solo_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(solo_surf, bg_color_solo, (0, 0, card_w, card_h), border_radius=12)
            pygame.draw.rect(solo_surf, border_color_solo, (0, 0, card_w, card_h), width=border_w_solo, border_radius=12)
            
            if is_sel_solo:
                # Efeito glow interno ciano
                pygame.draw.rect(solo_surf, (0, 255, 204, 25), (5, 5, card_w - 10, card_h - 10), border_radius=8)
                
            tela.blit(solo_surf, (card_l_x, card_y))
            
            title_solo = font_card_title.render("JOGAR SOLO", True, (255, 255, 255) if is_sel_solo else (170, 170, 180))
            tela.blit(title_solo, (card_l_x + card_w // 2 - title_solo.get_width() // 2, card_y + 35))
            
            lines_solo = [
                "Jogue no modo offline.",
                "Enfronte desafios e",
                "domine o espaco-tempo",
                "em uma jornada solitaria."
            ]
            for li, l_txt in enumerate(lines_solo):
                txt_line = font_card_desc.render(l_txt, True, (215, 220, 230) if is_sel_solo else (130, 130, 140))
                tela.blit(txt_line, (card_l_x + card_w // 2 - txt_line.get_width() // 2, card_y + 95 + li * 24))
                
            # --- CARD DIREITO: COOPERATIVO ---
            card_r_x = largura // 2 + 30
            rect_coop = pygame.Rect(card_r_x, card_y, card_w, card_h)
            is_hover_coop = rect_coop.collidepoint(mx, my)
            if is_hover_coop:
                if selecionado_principal != 1:
                    selecionado_principal = 1
                    tocar_hover()
                if clicado:
                    tocar_selecionar()
                    fase_tela = "coop_sub"
                    selecionado_sub = 0
                    
            is_sel_coop = (selecionado_principal == 1)
            bg_color_coop = (24, 16, 36, 205) if is_sel_coop else (12, 10, 18, 140)
            border_color_coop = (180, 100, 255) if is_sel_coop else (70, 70, 85)
            border_w_coop = 2 if is_sel_coop else 1
            
            coop_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(coop_surf, bg_color_coop, (0, 0, card_w, card_h), border_radius=12)
            pygame.draw.rect(coop_surf, border_color_coop, (0, 0, card_w, card_h), width=border_w_coop, border_radius=12)
            
            if is_sel_coop:
                # Efeito glow interno roxo
                pygame.draw.rect(coop_surf, (180, 100, 255, 25), (5, 5, card_w - 10, card_h - 10), border_radius=8)
                
            tela.blit(coop_surf, (card_r_x, card_y))
            
            title_coop = font_card_title.render("MULTIPLAYER", True, (255, 255, 255) if is_sel_coop else (170, 170, 180))
            tela.blit(title_coop, (card_r_x + card_w // 2 - title_coop.get_width() // 2, card_y + 35))
            
            lines_coop = [
                "Jogue em Rede Local (LAN).",
                "Conecte-se com outro",
                "jogador para explorar",
                "a fenda cooperativamente."
            ]
            for li, l_txt in enumerate(lines_coop):
                txt_line = font_card_desc.render(l_txt, True, (215, 220, 230) if is_sel_coop else (130, 130, 140))
                tela.blit(txt_line, (card_r_x + card_w // 2 - txt_line.get_width() // 2, card_y + 95 + li * 24))
                
        # Renderizar Subfase: Opções Multiplayer LAN
        elif fase_tela == "coop_sub":
            sub_y = altura // 2 - 50
            btn_w = 340
            btn_h = 52
            
            opcoes_sub = [
                ("Criar Sala (Host)", "host"),
                ("Entrar em Sala (Join)", "join"),
                ("Voltar", "voltar")
            ]
            
            txt_subtitle = font_card_desc.render("CONEXÃO DE MULTIJOGADOR EM REDE LOCAL", True, (180, 100, 255))
            tela.blit(txt_subtitle, (largura // 2 - txt_subtitle.get_width() // 2, 125))
            
            for idx, (label, mode) in enumerate(opcoes_sub):
                btn_x = largura // 2 - btn_w // 2
                item_y = sub_y + idx * 70
                rect_btn = pygame.Rect(btn_x, item_y, btn_w, btn_h)
                
                is_hover = rect_btn.collidepoint(mx, my)
                if is_hover:
                    if selecionado_sub != idx:
                        selecionado_sub = idx
                        tocar_hover()
                    if clicado:
                        tocar_selecionar()
                        if mode == "host":
                            return "host", None
                        elif mode == "join":
                            ip_encontrado = descobrir_host_udp(timeout=4)
                            if ip_encontrado:
                                return "join", ip_encontrado
                            else:
                                mostrar_erro_lan(tela, font_card_title, font_card_desc)
                        elif mode == "voltar":
                            fase_tela = "principal"
                            selecionado_sub = 0
                            
                is_sel = (selecionado_sub == idx)
                bg_color = (25, 20, 42, 210) if is_sel else (12, 10, 18, 140)
                border_color = (180, 100, 255) if is_sel else (65, 55, 80)
                border_w = 2 if is_sel else 1
                
                btn_surf = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
                pygame.draw.rect(btn_surf, bg_color, (0, 0, btn_w, btn_h), border_radius=8)
                pygame.draw.rect(btn_surf, border_color, (0, 0, btn_w, btn_h), width=border_w, border_radius=8)
                tela.blit(btn_surf, (btn_x, item_y))
                
                txt_lbl = font_btn.render(label, True, (255, 255, 255) if is_sel else (175, 175, 185))
                tela.blit(txt_lbl, (btn_x + btn_w // 2 - txt_lbl.get_width() // 2, item_y + btn_h // 2 - txt_lbl.get_height() // 2))
                
        pygame.display.flip()
        clock.tick(60)



def tela_selecao_aurea(tela, fonte):
    # Carregar som do tick
    try:
        som_tick = aplicar_volume_som(pygame.mixer.Sound("Sounds/Estalo.mp3"))
    except Exception:
        som_tick = None

    aureas = [
        {
            "nome": "Racional",
            "imagem": "Sprites/aurea_cientista.png",
            "ativa": True,
            "cor_tema": (0, 191, 255),       # Azul Elétrico / Ciano
            "bg_tema": (8, 20, 42),          # Fundo Deep Blue
            "categoria": "ANÁLISE E PRECISÃO TEMPORAL",
            "efeito": "Aumenta drasticamente a probabilidade de acerto crítico e melhora a cadência de disparos.",
            "atributos": [
                "• Chance de Crítico: +15%",
                "• Cadência de Tiro: +10% de velocidade de ataque",
                "• Ideal para jogabilidade focada em DPS e precisão."
            ],
            "lore": "A mente fria calcula trajetórias e enxerga padrões em meio ao caos da ruptura temporal."
        },
        {
            "nome": "Impulsiva",
            "imagem": "Sprites/aurea_impulsiva.png",
            "ativa": True,
            "cor_tema": (255, 99, 71),       # Vermelho Coral / Laranja
            "bg_tema": (42, 14, 8),          # Fundo Deep Red/Orange
            "categoria": "COMBATE VELOZ E AGRESSIVO",
            "efeito": "Concede bônus de dano ou velocidade de movimento temporário após realizar eliminações rápidas.",
            "atributos": [
                "• Buff após Eliminação: +30% de Dano ou +20% de Velocidade",
                "• Duração do Buff: 3s (+0.5s por Nível)",
                "• Ideal para jogadores dinâmicos que gostam de velocidade."
            ],
            "lore": "Ação imediata. O instinto puro reage antes que o próprio tempo possa processar."
        },
        {
            "nome": "Devota",
            "imagem": "Sprites/aurea_devota.png",
            "ativa": True,
            "cor_tema": (255, 215, 0),       # Dourado Divino
            "bg_tema": (36, 30, 8),          # Fundo Deep Gold
            "categoria": "SOBREVIVÊNCIA E PROTEÇÃO SAGRADA",
            "efeito": "Manifesta um escudo sagrado automático que absorve completamente um golpe sofrido.",
            "atributos": [
                "• Escudo Protetor: Absorve 1 hit fatal ou dano",
                "• Cooldown do Escudo: 30s (-3s por Nível, mínimo 10s)",
                "• Excelente para garantir segurança contra ataques inesperados."
            ],
            "lore": "A fé inabalável manifesta-se como uma barreira divina que desafia a própria causalidade."
        },
        {
            "nome": "Vanguarda",
            "imagem": "Sprites/aurea_vanguarda.png",
            "ativa": True,
            "cor_tema": (230, 0, 120),       # Magenta / Carmesim
            "bg_tema": (36, 8, 28),          # Fundo Deep Purple/Magenta
            "categoria": "DANO EM ÁREA E INCÊNDIO CONTÍNUO",
            "efeito": "Deixa um rastro de chamas purificadoras por onde passa, causando dano aos inimigos.",
            "atributos": [
                "• Duração do Rastro de Fogo: 5s (+1s por Nível)",
                "• Dano de Incêndio: Causa dano contínuo a inimigos que tocarem o rastro",
                "• Ideal para controle de hordas e movimentação tática."
            ],
            "lore": "Liderando o avanço, o pioneiro incendeia o solo para que nada o siga no fluxo temporal."
        },
        {
            "nome": "Aleatória",
            "imagem": "Sprites/aurea_misteriosa.png",
            "ativa": True,
            "cor_tema": (0, 255, 180),       # Verde Esmeralda / Neon
            "bg_tema": (8, 32, 24),          # Fundo Deep Green
            "categoria": "SURPRESA E DESTINO INCERTO",
            "efeito": "Escolhe uma das quatro áureas ativas aleatoriamente ao iniciar a jornada.",
            "atributos": [
                "• Racional, Impulsiva, Devota ou Vanguarda",
                "• Uma nova estratégia a cada tentativa.",
                "• Destinado aos jogadores que buscam adaptação constante."
            ],
            "lore": "O destino é incerto, e o tempo se desdobra em infinitas possibilidades."
        }
    ]

    upgrades = carregar_upgrade_aureas("saves/aureas_upgrade.json")

    selecionado = 0
    clock = pygame.time.Clock()
    largura, altura = tela.get_size()

    # Fontes específicas
    import random
    caminho_fonte_aureas = "Texto/rainyhearts.ttf"
    fonte_nome = pygame.font.Font(caminho_fonte_aureas, 36)
    fonte_desc = pygame.font.Font(caminho_fonte_aureas, 22)
    fonte_status = pygame.font.Font(caminho_fonte_aureas, 14)
    fonte_instrucao = pygame.font.Font(caminho_fonte_aureas, 20)
    fonte_categoria = pygame.font.Font(caminho_fonte_aureas, 18)

    # Variáveis de animação (Interpolação LERP)
    cor_fundo_atual = list(aureas[selecionado]["bg_tema"])
    
    # Propriedades dos cards
    card_x = [largura // 2 for _ in aureas]
    card_scale = [0.85 for _ in aureas]
    card_y_offset = [20 for _ in aureas]
    card_alpha = [100 for _ in aureas]

    # Carregar imagens das áureas antecipadamente
    imagens_aureas = []
    for item in aureas:
        try:
            img = pygame.image.load(item["imagem"]).convert_alpha()
        except:
            img = pygame.Surface((180, 240))
            img.fill((30, 30, 30))
            pygame.draw.line(img, (100, 100, 100), (0, 0), (180, 240), 2)
            pygame.draw.line(img, (100, 100, 100), (180, 0), (0, 240), 2)
        imagens_aureas.append(img)

    # Sistema de Partículas Celestiais
    particulas = []
    for _ in range(50):
        particulas.append({
            "x": random.randint(0, largura),
            "y": random.randint(0, altura),
            "vel_y": random.uniform(-1.2, -0.4),
            "tamanho": random.uniform(2.0, 5.0),
            "alpha": random.randint(50, 200),
            "breathe_speed": random.uniform(0.02, 0.05),
            "breathe_dir": 1
        })

    # Controle de repetição do analógico
    analogo_movido = False
    btn_back_rect = pygame.Rect(40, 40, 120, 36)
    
    while True:
        agora = pygame.time.get_ticks()
        mx, my = pygame.mouse.get_pos()
        clicado = False
        
        # 1. Processamento de Eventos
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    clicado = True
                    if btn_back_rect.collidepoint(evento.pos):
                        tocar_selecionar()
                        return "voltar"
            elif evento.type == pygame.KEYDOWN:
                anterior = selecionado
                if evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    return "voltar"
                elif evento.key in [pygame.K_RIGHT, pygame.K_d]:
                    selecionado = (selecionado + 1) % len(aureas)
                    while not aureas[selecionado]["ativa"]:
                        selecionado = (selecionado + 1) % len(aureas)
                elif evento.key in [pygame.K_LEFT, pygame.K_a]:
                    selecionado = (selecionado - 1) % len(aureas)
                    while not aureas[selecionado]["ativa"]:
                        selecionado = (selecionado - 1) % len(aureas)
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    if aureas[selecionado]["ativa"]:
                        tocar_selecionar()
                        nome_aurea = aureas[selecionado]["nome"]
                        if nome_aurea == "Aleatória":
                            nome_aurea = random.choice(["Racional", "Impulsiva", "Devota", "Vanguarda"])
                        
                        # Salva a escolha
                        os.makedirs("saves", exist_ok=True)
                        with open("saves/aurea_selecionada.json", "w") as file:
                            json.dump({"aurea": nome_aurea}, file)
                        return "confirmar"
                
                if selecionado != anterior:
                    tocar_hover()
            
            # Suporte a Controle / Gamepad
            elif evento.type == pygame.JOYAXISMOTION and controle is not None:
                if evento.axis == 0:  # Analógico Horizontal
                    anterior = selecionado
                    if evento.value > 0.5 and not analogo_movido:
                        selecionado = (selecionado + 1) % len(aureas)
                        while not aureas[selecionado]["ativa"]:
                            selecionado = (selecionado + 1) % len(aureas)
                        analogo_movido = True
                        tocar_hover()
                    elif evento.value < -0.5 and not analogo_movido:
                        selecionado = (selecionado - 1) % len(aureas)
                        while not aureas[selecionado]["ativa"]:
                            selecionado = (selecionado - 1) % len(aureas)
                        analogo_movido = True
                        tocar_hover()
                    elif abs(evento.value) < 0.3:
                        analogo_movido = False
            
            elif evento.type == pygame.JOYHATMOTION and controle is not None:
                anterior = selecionado
                # D-Pad
                dx, dy = evento.value
                if dx > 0:
                    selecionado = (selecionado + 1) % len(aureas)
                    while not aureas[selecionado]["ativa"]:
                        selecionado = (selecionado + 1) % len(aureas)
                    tocar_hover()
                elif dx < 0:
                    selecionado = (selecionado - 1) % len(aureas)
                    while not aureas[selecionado]["ativa"]:
                        selecionado = (selecionado - 1) % len(aureas)
                    tocar_hover()
            
            elif evento.type == pygame.JOYBUTTONDOWN and controle is not None:
                if evento.button == 0:  # Botão A do controle para confirmar
                    if aureas[selecionado]["ativa"]:
                        tocar_selecionar()
                        nome_aurea = aureas[selecionado]["nome"]
                        if nome_aurea == "Aleatória":
                            nome_aurea = random.choice(["Racional", "Impulsiva", "Devota", "Vanguarda"])
                        os.makedirs("saves", exist_ok=True)
                        with open("saves/aurea_selecionada.json", "w") as file:
                            json.dump({"aurea": nome_aurea}, file)
                        return "confirmar"
                elif evento.button == 1:  # Botão B do controle para voltar
                    tocar_selecionar()
                    return "voltar"

        # 2. Interpolação de Fundo
        bg_alvo = aureas[selecionado]["bg_tema"]
        for c in range(3):
            cor_fundo_atual[c] += (bg_alvo[c] - cor_fundo_atual[c]) * 0.08
        tela.fill((int(cor_fundo_atual[0]), int(cor_fundo_atual[1]), int(cor_fundo_atual[2])))

        # 3. Desenhar Partículas Dinâmicas
        cor_accent = aureas[selecionado]["cor_tema"]
        for p in particulas:
            # Move para cima
            p["y"] += p["vel_y"]
            if p["y"] < -10:
                p["y"] = altura + 10
                p["x"] = random.randint(0, largura)
            
            # Animação de brilho respiratório
            p["alpha"] += p["breathe_dir"] * p["breathe_speed"] * 50
            if p["alpha"] >= 255:
                p["alpha"] = 255
                p["breathe_dir"] = -1
            elif p["alpha"] <= 40:
                p["alpha"] = 40
                p["breathe_dir"] = 1
            
            # Desenha com mistura aditiva / alfa
            cor_part = cor_accent + (int(p["alpha"]),)
            surf_p = pygame.Surface((int(p["tamanho"]*2), int(p["tamanho"]*2)), pygame.SRCALPHA)
            pygame.draw.circle(surf_p, cor_part, (int(p["tamanho"]), int(p["tamanho"])), int(p["tamanho"]))
            tela.blit(surf_p, (int(p["x"] - p["tamanho"]), int(p["y"] - p["tamanho"])))

        # 4. Renderizar Título Geral (Sem acento para evitar falhas com a fonte Doctor Glitch)
        render_titulo = render_glitch_text_with_fallback("ESCOLHA DE AUREA", fonte_titulo, fonte_letra1, (255, 255, 255))
        tela.blit(render_titulo, (largura // 2 - render_titulo.get_width() // 2, altura // 14))

        # 5. Cálculo das Posições e Escalas dos Cards (Animação Fluida)
        largura_quadro = 160
        altura_quadro = 220
        espacamento_cards = 180

        for i, aurea in enumerate(aureas):
            # Define alvos
            dist = i - selecionado
            target_x = largura // 2 + dist * espacamento_cards
            
            if i == selecionado:
                target_scale = 1.15
                target_y_offset = -20
                target_alpha = 255
            else:
                target_scale = 0.85
                target_y_offset = 15
                target_alpha = 100
            
            # Interpolação suave
            card_x[i] += (target_x - card_x[i]) * 0.1
            card_scale[i] += (target_scale - card_scale[i]) * 0.1
            card_y_offset[i] += (target_y_offset - card_y_offset[i]) * 0.1
            card_alpha[i] += (target_alpha - card_alpha[i]) * 0.1

        # 6. Renderizar Cards
        for i, aurea in enumerate(aureas):
            curr_scale = card_scale[i]
            w_scaled = int(largura_quadro * curr_scale)
            h_scaled = int(altura_quadro * curr_scale)
            x_pos = int(card_x[i] - w_scaled // 2)
            y_pos = int(altura // 3.3 + card_y_offset[i])

            # Superfície temporária para o card com canal alpha
            surf_card = pygame.Surface((w_scaled, h_scaled), pygame.SRCALPHA)
            
            # Fundo glassmorphic do card
            alpha_fundo = int(50 + (card_alpha[i] / 255.0) * 110)
            pygame.draw.rect(surf_card, (20, 20, 25, alpha_fundo), (0, 0, w_scaled, h_scaled), border_radius=12)

            # Imagem da Áurea
            img_scaled = pygame.transform.scale(imagens_aureas[i], (w_scaled - 12, h_scaled - 12))
            
            # Aplicar transparência à imagem da Áurea
            surf_img_alpha = pygame.Surface(img_scaled.get_size(), pygame.SRCALPHA)
            surf_img_alpha.blit(img_scaled, (0, 0))
            # Aplica canal alpha geral da imagem
            surf_img_alpha.fill((255, 255, 255, int(card_alpha[i])), special_flags=pygame.BLEND_RGBA_MULT)
            surf_card.blit(surf_img_alpha, (6, 6))

            # Desenhar Borda do Card
            cor_borda = aurea["cor_tema"] + (int(card_alpha[i]),)
            largura_linha = 3 if i == selecionado else 1
            pygame.draw.rect(surf_card, cor_borda, (0, 0, w_scaled, h_scaled), width=largura_linha, border_radius=12)

            # Efeito Glow Concêntrico se estiver selecionado
            if i == selecionado:
                for g in range(1, 5):
                    glow_alpha = int((1.0 - g/5.0) * 80)
                    glow_color = aurea["cor_tema"] + (glow_alpha,)
                    glow_surf = pygame.Surface((w_scaled + g*4, h_scaled + g*4), pygame.SRCALPHA)
                    pygame.draw.rect(glow_surf, glow_color, (0, 0, w_scaled + g*4, h_scaled + g*4), width=1, border_radius=12 + g)
                    tela.blit(glow_surf, (x_pos - g*2, y_pos - g*2))

            # Blitar card final na tela
            tela.blit(surf_card, (x_pos, y_pos))

            # Badge do Nível (se aplicável)
            nome_aurea = aurea["nome"]
            if nome_aurea != "?" and nome_aurea != "Aleatória" and aurea["ativa"]:
                nivel = upgrades.get(nome_aurea, 0)
                if nivel > 0:
                    badge_texto = f"Nv. {nivel}"
                    render_badge = fonte_status.render(badge_texto, True, (255, 255, 255))
                    
                    largura_badge = render_badge.get_width() + 16
                    altura_badge = 20
                    surf_badge = pygame.Surface((largura_badge, altura_badge), pygame.SRCALPHA)
                    
                    pygame.draw.rect(surf_badge, (20, 20, 20, 230), (0, 0, largura_badge, altura_badge), border_radius=4)
                    pygame.draw.rect(surf_badge, aurea["cor_tema"], (0, 0, largura_badge, altura_badge), width=1, border_radius=4)
                    surf_badge.blit(render_badge, (8, (altura_badge - render_badge.get_height()) // 2))
                    
                    # Desenhar no canto superior direito do card
                    tela.blit(surf_badge, (x_pos + w_scaled - largura_badge - 6, y_pos - 8))

        # 7. Renderizar Painel Descritivo Glassmorphic (Apenas para a selecionada)
        aurea_sel = aureas[selecionado]
        
        largura_painel = largura - 160
        altura_painel = 180
        x_painel = 80
        y_painel = altura - altura_painel - 70

        surf_painel = pygame.Surface((largura_painel, altura_painel), pygame.SRCALPHA)
        # Fundo do painel
        pygame.draw.rect(surf_painel, (10, 10, 15, 210), (0, 0, largura_painel, altura_painel), border_radius=16)
        # Borda brilhante combinando com o tema da áurea
        cor_borda_p = aurea_sel["cor_tema"] + (180,)
        pygame.draw.rect(surf_painel, cor_borda_p, (0, 0, largura_painel, altura_painel), width=2, border_radius=16)

        # Desenhar Conteúdo do Painel
        # Título da Áurea
        nome_display = aurea_sel["nome"].upper()
        if nome_display not in ["?", "ALEATÓRIA"] and upgrades.get(aurea_sel["nome"], 0) > 0:
            nome_display += f" (NÍVEL {upgrades[aurea_sel['nome']]})"
        
        render_nome = fonte_nome.render(nome_display, True, aurea_sel["cor_tema"])
        surf_painel.blit(render_nome, (24, 16))

        # Subtítulo / Categoria
        render_cat = fonte_categoria.render(aurea_sel["categoria"], True, (150, 150, 150))
        surf_painel.blit(render_cat, (26, 48))

        # Linha Divisória Vertical
        x_divisor = largura_painel // 2
        pygame.draw.line(surf_painel, (50, 50, 60, 150), (x_divisor, 16), (x_divisor, altura_painel - 16), 1)

        # Descrição principal com auto-quebra de linha dinâmica (máx largura_limite)
        palavras = aurea_sel["efeito"].split(' ')
        linhas_desc = []
        linha_atual = []
        largura_limite = x_divisor - 48
        for palavra in palavras:
            test_linha = ' '.join(linha_atual + [palavra])
            if fonte_desc.size(test_linha)[0] <= largura_limite:
                linha_atual.append(palavra)
            else:
                linhas_desc.append(' '.join(linha_atual))
                linha_atual = [palavra]
        if linha_atual:
            linhas_desc.append(' '.join(linha_atual))

        y_desc = 76
        for linha in linhas_desc:
            render_linha = fonte_desc.render(linha, True, (230, 230, 230))
            surf_painel.blit(render_linha, (24, y_desc))
            y_desc += 22

        # Atributos (Lado Direito)
        y_attr = 20
        for attr in aurea_sel["atributos"]:
            render_attr = fonte_status.render(attr, True, (190, 190, 200))
            surf_painel.blit(render_attr, (x_divisor + 24, y_attr))
            y_attr += 24

        # Lore/Flavor text (Dinamicamente abaixo das linhas da descrição)
        render_lore = fonte_status.render(f'"{aurea_sel["lore"]}"', True, (120, 120, 130))
        y_lore = max(124, y_desc + 10)
        surf_painel.blit(render_lore, (24, y_lore))

        # Renderiza o painel final na tela
        tela.blit(surf_painel, (x_painel, y_painel))

        # 8. Barra de instrução no rodapé
        texto_instr = "A / D ou SETAS: Navegar | ESPAÇO/ENTER: Selecionar | ESC: Voltar"
        render_instr_text = fonte_instrucao.render(texto_instr, True, (0, 255, 230))
        largura_instr = render_instr_text.get_width() + 40
        altura_instr = 32
        
        surf_instr = pygame.Surface((largura_instr, altura_instr), pygame.SRCALPHA)
        pygame.draw.rect(surf_instr, (10, 10, 15, 200), (0, 0, largura_instr, altura_instr), border_radius=6)
        pygame.draw.rect(surf_instr, (0, 240, 255, 80), (0, 0, largura_instr, altura_instr), width=1, border_radius=6)
        surf_instr.blit(render_instr_text, (20, (altura_instr - render_instr_text.get_height()) // 2))
        
        tela.blit(surf_instr, (largura // 2 - largura_instr // 2, altura - 42))

        # 9. Botão Voltar no Canto Superior Esquerdo (Desenhado dinamicamente com a cor do tema da Áurea)
        is_hover_back = btn_back_rect.collidepoint(mx, my)
        color_back = cor_accent if is_hover_back else (140, 140, 150)
        bg_back = (int(cor_accent[0]*0.15), int(cor_accent[1]*0.15), int(cor_accent[2]*0.15), 200) if is_hover_back else (15, 15, 20, 120)
        
        surf_back = pygame.Surface((120, 36), pygame.SRCALPHA)
        pygame.draw.rect(surf_back, bg_back, (0, 0, 120, 36), border_radius=8)
        pygame.draw.rect(surf_back, color_back, (0, 0, 120, 36), width=1, border_radius=8)
        
        txt_back = fonte_desc.render("< VOLTAR", True, color_back)
        surf_back.blit(txt_back, (60 - txt_back.get_width() // 2, 18 - txt_back.get_height() // 2))
        tela.blit(surf_back, (btn_back_rect.x, btn_back_rect.y))

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
                        tocar_hover()
                    elif event.key == pygame.K_s and agora - ultima_mudanca_de_opcao >= DELAY_ENTRE_OPCOES:
                        indice_selecionado = (indice_selecionado + 1) % len(opcoes)
                        ultima_mudanca_de_opcao = agora
                        tocar_hover()
                    elif event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                        opcao_confirmada = indice_selecionado
                        tempo_confirmacao = agora
                        tocar_selecionar()
                        
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
                        tocar_selecionar()
                        
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
                                tocar_hover()
                            elif event.value < -0.5:
                                indice_selecionado = (indice_selecionado - 1) % len(opcoes)
                                analogo_movido = True
                                tocar_hover()
                    elif event.axis == 1 and abs(event.value) < 0.5:
                        analogo_movido = False
                        
                elif event.type == pygame.JOYBUTTONDOWN and controle is not None:
                    if event.button == 0:  # Botão A
                        opcao_confirmada = indice_selecionado
                        tempo_confirmacao = agora
                        tocar_selecionar()
                        
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
        

        
        # Renderização do título
        texto_titulo = fonte_titulo.render(titulo_jogo, True, cor_letra)
        retangulo_titulo = texto_titulo.get_rect(center=posicao_titulo)
        

        
        # Sombra e Contorno do Título (AAA volumetric effect)
        texto_titulo_sombra = fonte_titulo.render(titulo_jogo, True, (15, 5, 25))
        tela.blit(texto_titulo_sombra, (retangulo_titulo.left + 4, retangulo_titulo.top + 4))
        
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            texto_titulo_contorno = fonte_titulo.render(titulo_jogo, True, contorno_rosa)
            tela.blit(texto_titulo_contorno, (retangulo_titulo.left + dx, retangulo_titulo.top + dy))
            
        tela.blit(texto_titulo, retangulo_titulo)

        
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
                if not os.path.exists("saves/nome_jogador.json"):
                    try:
                        os.makedirs("saves", exist_ok=True)
                        with open("saves/nome_jogador.json", "w") as f:
                            json.dump({"nome": "Apolo"}, f)
                    except:
                        pass
                if not os.path.exists("saves/tutorial_config.json"):
                    mostrar_tutorial = tela_decisao_tutorial(tela, fonte)
                    with open("saves/tutorial_config.json", "w") as f:
                        json.dump({"mostrar_tutorial": mostrar_tutorial}, f)
                else:
                    with open("saves/tutorial_config.json", "r") as f:
                        mostrar_tutorial = json.load(f)["mostrar_tutorial"]

                estado_jornada = "aurea"
                retornar_ao_menu = False
                modo, ip = None, None
                
                while True:
                    if estado_jornada == "aurea":
                        res_aurea = tela_selecao_aurea(tela, fonte)
                        if res_aurea == "voltar":
                            retornar_ao_menu = True
                            break
                        else:
                            estado_jornada = "modo"
                    elif estado_jornada == "modo":
                        modo, ip = tela_escolha_modo()
                        if modo is None:
                            estado_jornada = "aurea"
                        else:
                            break
                
                if retornar_ao_menu:
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
                indice_config = 0
                
                opcao_conf_confirmada = None
                tempo_conf_confirmacao = 0
                particulas_conf_eclosao = []
                
                config_rodando = True
                while config_rodando:
                    agora_conf = pygame.time.get_ticks()
                    
                    try:
                        with open("saves/tutorial_config.json", "r") as f:
                            mostrar_tut = json.load(f).get("mostrar_tutorial", True)
                    except:
                        mostrar_tut = True
                    
                    status_tut = "ATIVADO" if mostrar_tut else "DESATIVADO"
                    opcoes_config = ["Controles", "Gráficos", "Áudio", f"Tutorial: {status_tut}", "Voltar"]
                    
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
                        elif escolha_config == 3:  # Tutorial: Alternar status
                            mostrar_tut = not mostrar_tut
                            with open("saves/tutorial_config.json", "w") as f:
                                json.dump({"mostrar_tutorial": mostrar_tut}, f)
                        elif escolha_config == 4:  # Voltar
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
