import pygame
import json
import sys
import math

def render_glitch_text_with_fallback(texto, fonte_glitch, fonte_fallback, cor):
    surfaces = []
    largura_total = 0
    altura_max = 0
    for char in texto:
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

def formatar_nome_tecla(tecla):
    if isinstance(tecla, str) and tecla.startswith("MOUSE_"):
        try:
            btn_idx = int(tecla.split("_")[1])
            nomes_mouse = {
                1: "LMB",
                2: "MMB",
                3: "RMB",
                4: "M4",
                5: "M5"
            }
            return nomes_mouse.get(btn_idx, f"M{btn_idx}")
        except:
            return tecla
    elif isinstance(tecla, int):
        nome = pygame.key.name(tecla)
        traducoes = {
            "left shift": "LSHIFT",
            "right shift": "RSHIFT",
            "left ctrl": "LCTRL",
            "right ctrl": "RCTRL",
            "left alt": "LALT",
            "right alt": "RALT",
            "space": "ESPACO",
            "return": "ENTER",
            "escape": "ESC"
        }
        return traducoes.get(nome.lower(), nome.upper())
    return str(tecla)

def tela_de_controles(tela, config_teclas, largura_tela, altura_tela, fundo_pausa=None):
    pygame.mouse.set_visible(True)
    
    padrao_config_teclas = {
        "Mover para cima": pygame.K_w,
        "Mover para baixo": pygame.K_s,
        "Mover para esquerda": pygame.K_a,
        "Mover para direita": pygame.K_d,
        "Teleporte": pygame.K_LSHIFT,
        "Comprar na loja": pygame.K_e,
        "Habilidade Onda": "MOUSE_3"
    }

    for chave, valor in padrao_config_teclas.items():
        if chave not in config_teclas:
            config_teclas[chave] = valor

    if fundo_pausa:
        fundo = fundo_pausa
    else:
        try:
            fundo = pygame.image.load("Sprites/botao_menu.png").convert()
            fundo = pygame.transform.scale(fundo, (largura_tela, altura_tela))
        except:
            fundo = None

    caminho_titulo = "Texto/Top_Menu.otf"
    caminho_letras = "Texto/Broken.otf"
    caminho_letra1 = "Texto/World.otf"

    try:
        fonte_titulo = pygame.font.Font(caminho_titulo, 52)
        fonte_fallback_titulo = pygame.font.Font(caminho_letra1, 52)
        fonte = pygame.font.Font(caminho_letras, 24)
        fonte_valores = pygame.font.Font(caminho_letra1, 22)
        fonte_hint = pygame.font.Font(caminho_letras, 16)
        fonte_header = pygame.font.Font(caminho_letras, 18)
    except:
        fonte_titulo = pygame.font.Font(None, 52)
        fonte_fallback_titulo = pygame.font.Font(None, 52)
        fonte = pygame.font.Font(None, 28)
        fonte_valores = pygame.font.Font(None, 24)
        fonte_hint = pygame.font.Font(None, 18)
        fonte_header = pygame.font.Font(None, 20)

    COR_BG         = (10, 8, 20)
    COR_BORDA      = (0, 255, 204)  # Cyan neon
    COR_BORDA_SEC  = (180, 100, 255) # Purple neon
    COR_NORMAL     = (180, 180, 200)
    COR_SELECIONADO = (0, 255, 230)
    COR_AGUARDANDO = (255, 235, 60) # Amarelo vibrante
    COR_ERRO       = (255, 80, 80)
    COR_TITULO     = (0, 255, 204)
    COR_HINT       = (140, 130, 160)

    funcoes = list(config_teclas.keys())
    indice_selecionado = 0
    redefinindo_tecla = False
    mensagem = ""
    cor_mensagem = COR_NORMAL
    timer_mensagem = 0

    relogio = pygame.time.Clock()
    tempo_piscar = 0
    mostrar_piscar = True
    animacao = 0.0

    CARD_W = int(largura_tela * 0.6)
    CARD_H = int(altura_tela * 0.76)
    CARD_X = (largura_tela - CARD_W) // 2
    CARD_Y = int(altura_tela * 0.14)
    LINHA_H = 48

    # Button coordinates
    btn_voltar_w = 200
    btn_voltar_h = 42
    btn_voltar_x = largura_tela // 2 - btn_voltar_w // 2
    btn_voltar_y = CARD_Y + CARD_H - btn_voltar_h - 20
    rect_voltar = pygame.Rect(btn_voltar_x, btn_voltar_y, btn_voltar_w, btn_voltar_h)

    rodando = True
    while rodando:
        dt = relogio.tick(60)
        animacao += dt * 0.001
        mx, my = pygame.mouse.get_pos()

        if fundo:
            tela.blit(fundo, (0, 0))
        else:
            tela.fill(COR_BG)

        # Black semi-transparent overlay for readability
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        tela.blit(overlay, (0, 0))

        # Dynamic digital scanlines / grid effect
        grad = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        for y in range(0, altura_tela, 6):
            alpha = int(25 + 15 * math.sin(y * 0.02 + animacao * 2))
            pygame.draw.line(grad, (0, 255, 230, alpha), (0, y), (largura_tela, y))
        tela.blit(grad, (0, 0))

        # Glowing Neon Border Panel
        painel = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
        painel.fill((10, 8, 20, 220)) # Glassmorphic dark base
        
        # Pulse borders
        pulse_alpha = int(120 + 50 * math.sin(animacao * 4))
        pygame.draw.rect(painel, (0, 255, 204, pulse_alpha), (0, 0, CARD_W, CARD_H), width=2, border_radius=12)
        
        # Inner thin shadow border
        pygame.draw.rect(painel, (180, 100, 255, 80), (1, 1, CARD_W - 2, CARD_H - 2), width=1, border_radius=12)
        
        tela.blit(painel, (CARD_X, CARD_Y))

        # Title
        titulo = render_glitch_text_with_fallback("CONFIGURACOES DE CONTROLES", fonte_titulo, fonte_fallback_titulo, COR_TITULO)
        ret_tit = titulo.get_rect(center=(largura_tela // 2, CARD_Y - 45))
        # Sombra
        titulo_sombra = render_glitch_text_with_fallback("CONFIGURACOES DE CONTROLES", fonte_titulo, fonte_fallback_titulo, (10, 5, 20))
        tela.blit(titulo_sombra, (ret_tit.x + 3, ret_tit.y + 3))
        tela.blit(titulo, ret_tit)

        # Headers
        txt_header_acao = fonte_header.render("ACAO", True, COR_BORDA_SEC)
        txt_header_atalho = fonte_header.render("ATALHO ATUAL", True, COR_BORDA_SEC)
        tela.blit(txt_header_acao, (CARD_X + 30, CARD_Y + 20))
        tela.blit(txt_header_atalho, (CARD_X + CARD_W - txt_header_atalho.get_width() - 30, CARD_Y + 20))

        # Divider under headers
        pygame.draw.line(tela, (0, 255, 204, 100), (CARD_X + 20, CARD_Y + 45), (CARD_X + CARD_W - 20, CARD_Y + 45), 2)

        # List of bindings
        start_y = CARD_Y + 60
        for i, funcao in enumerate(funcoes):
            y_item = start_y + i * LINHA_H
            is_sel = (i == indice_selecionado)

            # Row hover / selection effect
            if is_sel:
                rect_row = pygame.Rect(CARD_X + 12, y_item - 3, CARD_W - 24, LINHA_H - 6)
                row_surf = pygame.Surface((rect_row.width, rect_row.height), pygame.SRCALPHA)
                
                # Dynamic golden or cyan highlight
                hl_color = (0, 255, 230, 45) if not redefinindo_tecla else (255, 210, 60, 55)
                row_surf.fill(hl_color)
                
                # Accent corner tick lines or border
                pygame.draw.rect(row_surf, COR_SELECIONADO if not redefinindo_tecla else COR_AGUARDANDO, (0, 0, rect_row.width, rect_row.height), width=1, border_radius=6)
                tela.blit(row_surf, rect_row)

            # Colors based on state
            cor_label = COR_SELECIONADO if is_sel else COR_NORMAL
            if is_sel and redefinindo_tecla:
                cor_label = COR_AGUARDANDO

            # Action Label
            txt_funcao = fonte.render(funcao, True, cor_label)
            tela.blit(txt_funcao, (CARD_X + 30, y_item + 6))

            # Key Bind Label
            if is_sel and redefinindo_tecla:
                nome_tecla = "▶ AGUARDANDO... ◀" if mostrar_piscar else ""
            else:
                nome_tecla = formatar_nome_tecla(config_teclas[funcao])

            txt_tecla = fonte_valores.render(f"[ {nome_tecla} ]", True, cor_label)
            tela.blit(txt_tecla, (CARD_X + CARD_W - txt_tecla.get_width() - 30, y_item + 6))

            # Sutil row separator
            if i < len(funcoes) - 1:
                pygame.draw.line(tela, (60, 40, 90, 100), (CARD_X + 24, y_item + LINHA_H - 3), (CARD_X + CARD_W - 24, y_item + LINHA_H - 3), 1)

        # Redefinition helper hint inside card
        if redefinindo_tecla:
            hint_txt = "Pressione qualquer Tecla do teclado ou clique com qualquer Botao do Mouse..."
            hint_color = COR_AGUARDANDO
        else:
            hint_txt = "Clique em um item e aperte ESPACO para redefinir o atalho."
            hint_color = COR_HINT
            
        surf_hint = fonte_hint.render(hint_txt, True, hint_color)
        tela.blit(surf_hint, (largura_tela // 2 - surf_hint.get_width() // 2, btn_voltar_y - 28))

        # Back Button (VOLTAR) with hover
        is_hover_voltar = rect_voltar.collidepoint(mx, my)
        btn_bg_color = (0, 180, 200, 75) if is_hover_voltar else (15, 12, 35, 230)
        btn_border_color = COR_SELECIONADO if is_hover_voltar else COR_BORDA_SEC
        
        pygame.draw.rect(tela, btn_bg_color, rect_voltar, border_radius=6)
        pygame.draw.rect(tela, btn_border_color, rect_voltar, width=2, border_radius=6)
        
        txt_voltar = fonte_valores.render("VOLTAR", True, (255, 255, 255) if is_hover_voltar else COR_NORMAL)
        txt_voltar_rect = txt_voltar.get_rect(center=rect_voltar.center)
        tela.blit(txt_voltar, txt_voltar_rect)

        # Message Banner
        agora_msg = pygame.time.get_ticks()
        if mensagem and agora_msg - timer_mensagem < 2500:
            alpha_msg = max(0, 255 - int((agora_msg - timer_mensagem) / 2500 * 255))
            surf_msg = fonte_valores.render(mensagem, True, cor_mensagem)
            surf_msg.set_alpha(alpha_msg)
            
            # Draw a capsule backdrop for the message
            msg_rect = pygame.Rect(largura_tela // 2 - surf_msg.get_width() // 2 - 15, CARD_Y + CARD_H + 10, surf_msg.get_width() + 30, 36)
            pygame.draw.rect(tela, (15, 10, 25, alpha_msg // 2), msg_rect, border_radius=6)
            pygame.draw.rect(tela, cor_mensagem, msg_rect, width=1, border_radius=6)
            tela.blit(surf_msg, (largura_tela // 2 - surf_msg.get_width() // 2, CARD_Y + CARD_H + 16))
        elif agora_msg - timer_mensagem >= 2500:
            mensagem = ""

        # Hints Footer bar
        hints = [
            ("CLIQUE / ENTER", "Selecionar"),
            ("ESPAÇO", "Redefinir"),
            ("ESC / VOLTAR", "Confirmar e Sair"),
        ]
        rodape_y = altura_tela - 30
        total_w = sum(fonte_hint.size(f"{k}  {v}   ")[0] for k, v in hints)
        x_hint = (largura_tela - total_w) // 2
        for key_h, desc_h in hints:
            s_key = fonte_hint.render(key_h, True, COR_SELECIONADO)
            s_desc = fonte_hint.render(f"  {desc_h}   ", True, COR_HINT)
            tela.blit(s_key, (x_hint, rodape_y))
            x_hint += s_key.get_width()
            tela.blit(s_desc, (x_hint, rodape_y))
            x_hint += s_desc.get_width()

        pygame.display.flip()

        # Event processing
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.KEYDOWN:
                if redefinindo_tecla:
                    nova_tecla = evento.key
                    funcao_atual = funcoes[indice_selecionado]
                    if nova_tecla == pygame.K_ESCAPE:
                        redefinindo_tecla = False
                        mensagem = "Redefinição cancelada."
                        cor_mensagem = COR_HINT
                        timer_mensagem = pygame.time.get_ticks()
                    elif nova_tecla in config_teclas.values():
                        # Find conflict
                        acao_conflito = ""
                        for acao, val in config_teclas.items():
                            if val == nova_tecla:
                                acao_conflito = acao
                                break
                        mensagem = f"'{formatar_nome_tecla(nova_tecla)}' já está em uso em '{acao_conflito}'!"
                        cor_mensagem = COR_ERRO
                        timer_mensagem = pygame.time.get_ticks()
                    else:
                        config_teclas[funcao_atual] = nova_tecla
                        redefinindo_tecla = False
                        salvar_config_teclas(config_teclas)
                        try:
                            import Variaveis
                            Variaveis.recarregar_teclas()
                        except:
                            pass
                        mensagem = f"'{funcao_atual}' → [ {formatar_nome_tecla(nova_tecla)} ]  ✔"
                        cor_mensagem = COR_AGUARDANDO
                        timer_mensagem = pygame.time.get_ticks()
                else:
                    if evento.key in (pygame.K_w, pygame.K_UP):
                        indice_selecionado = (indice_selecionado - 1) % len(funcoes)
                    elif evento.key in (pygame.K_s, pygame.K_DOWN):
                        indice_selecionado = (indice_selecionado + 1) % len(funcoes)
                    elif evento.key == pygame.K_SPACE or evento.key == pygame.K_RETURN:
                        redefinindo_tecla = True
                    elif evento.key == pygame.K_ESCAPE:
                        rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                mx, my = evento.pos
                
                # Check Voltar click first
                if rect_voltar.collidepoint(mx, my):
                    if not redefinindo_tecla:
                        rodando = False
                        break
                        
                if redefinindo_tecla:
                    # Bind this mouse button!
                    nova_tecla = f"MOUSE_{evento.button}"
                    funcao_atual = funcoes[indice_selecionado]
                    
                    if nova_tecla in config_teclas.values():
                        # Find conflict
                        acao_conflito = ""
                        for acao, val in config_teclas.items():
                            if val == nova_tecla:
                                acao_conflito = acao
                                break
                        mensagem = f"'{formatar_nome_tecla(nova_tecla)}' já está em uso em '{acao_conflito}'!"
                        cor_mensagem = COR_ERRO
                        timer_mensagem = pygame.time.get_ticks()
                    else:
                        config_teclas[funcao_atual] = nova_tecla
                        redefinindo_tecla = False
                        salvar_config_teclas(config_teclas)
                        try:
                            import Variaveis
                            Variaveis.recarregar_teclas()
                        except:
                            pass
                        mensagem = f"'{funcao_atual}' → [ {formatar_nome_tecla(nova_tecla)} ]  ✔"
                        cor_mensagem = COR_AGUARDANDO
                        timer_mensagem = pygame.time.get_ticks()
                else:
                    # Select action or start redefinition
                    for i in range(len(funcoes)):
                        y_item = start_y + i * LINHA_H
                        rect_item = pygame.Rect(CARD_X + 12, y_item - 3, CARD_W - 24, LINHA_H - 6)
                        if rect_item.collidepoint(mx, my):
                            if i == indice_selecionado:
                                redefinindo_tecla = True
                            else:
                                indice_selecionado = i

        tempo_piscar += dt
        if tempo_piscar > 450:
            mostrar_piscar = not mostrar_piscar
            tempo_piscar = 0

def salvar_config_teclas(config_teclas):
    import os
    os.makedirs("saves", exist_ok=True)
    with open("saves/config_teclas.json", "w") as arquivo:
        json.dump(config_teclas, arquivo)

def carregar_config_teclas():
    default_keys = {
        "Mover para cima": pygame.K_w,
        "Mover para baixo": pygame.K_s,
        "Mover para esquerda": pygame.K_a,
        "Mover para direita": pygame.K_d,
        "Teleporte": pygame.K_LSHIFT,
        "Comprar na loja": pygame.K_e,
        "Habilidade Onda": "MOUSE_3"
    }
    try:
        with open("saves/config_teclas.json", "r") as arquivo:
            config = json.load(arquivo)
            for k, v in default_keys.items():
                if k not in config:
                    config[k] = v
            return config
    except FileNotFoundError:
        return default_keys

if __name__ == "__main__":
    config_teclas = carregar_config_teclas()
    largura_tela, altura_tela = 800, 600
    pygame.init()
    tela = pygame.display.set_mode((largura_tela, altura_tela))
    tela_de_controles(tela, config_teclas, largura_tela, altura_tela)
