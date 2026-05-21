import pygame
import json
import subprocess
import sys
import math

python = sys.executable

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

def tela_de_controles(tela, config_teclas, largura_tela, altura_tela):
    pygame.mouse.set_visible(True)
    
    padrao_config_teclas = {
        "Mover para cima": pygame.K_w,
        "Mover para baixo": pygame.K_s,
        "Mover para esquerda": pygame.K_a,
        "Mover para direita": pygame.K_d,
        "Teleporte": pygame.K_LSHIFT,
        "Comprar na loja": pygame.K_e,
    }

    for chave, valor in padrao_config_teclas.items():
        if chave not in config_teclas:
            config_teclas[chave] = valor

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
    except:
        fonte_titulo = pygame.font.Font(None, 52)
        fonte_fallback_titulo = pygame.font.Font(None, 52)
        fonte = pygame.font.Font(None, 28)
        fonte_valores = pygame.font.Font(None, 24)
        fonte_hint = pygame.font.Font(None, 18)

    COR_BG         = (10, 8, 20)
    COR_PAINEL     = (20, 16, 40, 200)
    COR_BORDA      = (90, 40, 180)
    COR_NORMAL     = (200, 190, 220)
    COR_SELECIONADO = (255, 210, 60)
    COR_AGUARDANDO = (100, 220, 100)
    COR_ERRO       = (255, 80, 80)
    COR_TITULO     = (180, 100, 255)
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

    CARD_W = int(largura_tela * 0.55)
    CARD_H = int(altura_tela * 0.72)
    CARD_X = (largura_tela - CARD_W) // 2
    CARD_Y = int(altura_tela * 0.15)
    LINHA_H = 54

    rodando = True
    while rodando:
        dt = relogio.tick(60)
        animacao += dt * 0.001

        if fundo:
            tela.blit(fundo, (0, 0))
        else:
            tela.fill(COR_BG)

        # Gradiente sutil de fundo
        grad = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        for y in range(0, altura_tela, 4):
            alpha = int(30 + 20 * math.sin(y * 0.01 + animacao))
            pygame.draw.line(grad, (60, 20, 100, alpha), (0, y), (largura_tela, y))
        tela.blit(grad, (0, 0))

        # Painel central
        painel = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
        painel.fill((15, 10, 30, 190))
        borda_surface = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
        pygame.draw.rect(borda_surface, (*COR_BORDA, 180), (0, 0, CARD_W, CARD_H), 2, border_radius=14)
        tela.blit(painel, (CARD_X, CARD_Y))
        tela.blit(borda_surface, (CARD_X, CARD_Y))

        # Título
        titulo = render_glitch_text_with_fallback("CONTROLES", fonte_titulo, fonte_fallback_titulo, COR_TITULO)
        tela.blit(titulo, (largura_tela // 2 - titulo.get_width() // 2, CARD_Y - 55))

        # Lista de teclas
        for i, funcao in enumerate(funcoes):
            y_item = CARD_Y + 30 + i * LINHA_H
            is_sel = (i == indice_selecionado)

            # Highlight do item selecionado
            if is_sel:
                hl = pygame.Surface((CARD_W - 20, LINHA_H - 8), pygame.SRCALPHA)
                pulso = int(30 + 20 * abs(math.sin(animacao * 3)))
                hl.fill((90, 40, 180, pulso + 40))
                pygame.draw.rect(hl, (*COR_BORDA, 120), (0, 0, CARD_W - 20, LINHA_H - 8), 1, border_radius=8)
                tela.blit(hl, (CARD_X + 10, y_item - 4))

            cor = COR_SELECIONADO if is_sel else COR_NORMAL
            if is_sel and redefinindo_tecla:
                cor = COR_AGUARDANDO

            # Nome da ação
            txt_funcao = fonte.render(funcao, True, cor)
            tela.blit(txt_funcao, (CARD_X + 24, y_item))

            # Tecla atribuída
            nome_tecla   = pygame.key.name(config_teclas[funcao]).upper()
            if is_sel and redefinindo_tecla:
                nome_tecla = "▶ _ ◀" if mostrar_piscar else "▶   ◀"

            txt_tecla = fonte_valores.render(f"[ {nome_tecla} ]", True, cor)
            tela.blit(txt_tecla, (CARD_X + CARD_W - txt_tecla.get_width() - 24, y_item))

            # Separador sutil
            if i < len(funcoes) - 1:
                pygame.draw.line(tela, (60, 40, 90), (CARD_X + 18, y_item + LINHA_H - 6), (CARD_X + CARD_W - 18, y_item + LINHA_H - 6), 1)

        # Mensagem de feedback
        agora_msg = pygame.time.get_ticks()
        if mensagem and agora_msg - timer_mensagem < 2500:
            alpha_msg = max(0, 255 - int((agora_msg - timer_mensagem) / 2500 * 255))
            surf_msg = fonte_hint.render(mensagem, True, cor_mensagem)
            surf_msg.set_alpha(alpha_msg)
            tela.blit(surf_msg, (largura_tela // 2 - surf_msg.get_width() // 2, CARD_Y + CARD_H + 14))
        elif agora_msg - timer_mensagem >= 2500:
            mensagem = ""

        # Rodapé de ajuda
        hints = [
            ("W / S", "Navegar"),
            ("ESPAÇO", "Redefinir tecla"),
            ("ESC", "Voltar"),
        ]
        rodape_y = altura_tela - 40
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

        # Events
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
                        mensagem = f"'{pygame.key.name(nova_tecla).upper()}' já está em uso!"
                        cor_mensagem = COR_ERRO
                        timer_mensagem = pygame.time.get_ticks()
                    else:
                        config_teclas[funcao_atual] = nova_tecla
                        redefinindo_tecla = False
                        salvar_config_teclas(config_teclas)
                        mensagem = f"'{funcao_atual}' → [ {pygame.key.name(nova_tecla).upper()} ]  ✔"
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
                for i in range(len(funcoes)):
                    y_item = CARD_Y + 30 + i * LINHA_H
                    rect_item = pygame.Rect(CARD_X + 10, y_item - 4, CARD_W - 20, LINHA_H - 8)
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
    with open("saves/config_teclas.json", "w") as arquivo:
        json.dump(config_teclas, arquivo)

def carregar_config_teclas():
    try:
        with open("saves/config_teclas.json", "r") as arquivo:
            return json.load(arquivo)
    except FileNotFoundError:
        return {
            "Mover para cima": pygame.K_w,
            "Mover para baixo": pygame.K_s,
            "Mover para esquerda": pygame.K_a,
            "Mover para direita": pygame.K_d,
            "Teleporte": pygame.K_LSHIFT,
            "Comprar na loja": pygame.K_e,
        }

if __name__ == "__main__":
    config_teclas = carregar_config_teclas()
    largura_tela, altura_tela = 800, 600
    pygame.init()
    tela = pygame.display.set_mode((largura_tela, altura_tela))
    tela_de_controles(tela, config_teclas, largura_tela, altura_tela)
