import Caminhos
import pygame
import sys
import random
import math
from Variaveis import largura_tela, altura_tela
from sons_procedurais import tocar_hover, tocar_selecionar, tocar_game_over, parar_tudo

# Inicializar Pygame
pygame.init()

def generate_crack_points(p1, p2, deviation):
    points = [p1]
    
    def subdivide(pa, pb, dev):
        if dev < 4:
            return
        mid_x = (pa[0] + pb[0]) / 2 + random.uniform(-dev, dev)
        mid_y = (pa[1] + pb[1]) / 2 + random.uniform(-dev, dev)
        mid = (mid_x, mid_y)
        subdivide(pa, mid, dev * 0.5)
        points.append(mid)
        subdivide(mid, pb, dev * 0.5)
        
    subdivide(p1, p2, deviation)
    points.append(p2)
    return points

def tratar_tentar_novamente(game_manager):
    import Variaveis
    if not Variaveis.pode_tentar_novamente():
        return False
    Variaveis.preparar_rewind()
    if game_manager:
        from game_manager import EstadoJogo
        fase_retorno = game_manager.dados_compartilhados.get('fase_antes_do_game_over', EstadoJogo.JOGO_FASE_1)
        game_manager.mudar_estado(fase_retorno)
        return True
    else:
        import json
        import sys
        try:
            with open("saves/modo_jogo.json", "r") as f:
                dados = json.load(f)
            modo = dados["modo"]
            ip = dados["ip"]
        except:
            modo = "offline"
            ip = None

        if modo in ["host", "join"]:
            from rede import iniciar_host, conectar_ao_host
            if modo == "host":
                conn = iniciar_host()
            else:
                conn = conectar_ao_host(ip)
            import GAMERE
            GAMERE.modo = modo
            if modo == "join":
                GAMERE.ip_host = ip
            GAMERE.conn = conn
        else:
            import GAME
            GAME.executar_jogo()
        return False

def _obter_mensagem_rewind():
    """Retorna linhas curtas de aviso conforme a tentativa atual."""
    import Variaveis
    t = Variaveis.tentativas_rewind
    if t >= Variaveis.MAX_TENTATIVAS_REWIND:
        return ["O tempo se recusa a ser manipulado novamente.", "Suas chances acabaram."]
    elif t == 0:
        return ["Regressao Temporal: 20% de Vida | Pontuacao zerada.", "O tempo cobra caro por segunda chances."]
    elif t == 1:
        return ["Regressao Temporal: 10% de Vida | Metade das cartas perdidas.", "A realidade esta rejeitando voce."]
    else:
        return ["ULTIMA CHANCE: 5% de Vida | Todas as cartas perdidas.", "Voce sera apenas um eco do que ja foi."]

def executar_game_over(game_manager=None):
    pygame.init()
    
    # Garantir que o mouse esteja visível e liberado
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(True)
    
    # Inicializa controle Xbox
    joystick = None
    if pygame.joystick.get_count() > 0:
        try:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
        except:
            pass

    # Parar áudio anterior e tocar o som procedimental de Game Over
    parar_tudo()
    tocar_game_over()

    # Configuração da janela
    window = pygame.display.get_surface() or pygame.display.set_mode((largura_tela, altura_tela))
    largura, altura = window.get_size()
    pygame.display.set_caption("Linha do Tempo Rompida")
    
    # Carregar fontes com fallbacks
    try:
        font_large = pygame.font.Font("Texto/Top_Menu.otf", 50)
    except:
        font_large = pygame.font.Font(None, 65)
        
    try:
        font_desc = pygame.font.Font("Texto/rainyhearts.ttf", 22)
    except:
        font_desc = pygame.font.Font(None, 24)
        
    try:
        font_btn = pygame.font.Font("Texto/World.otf", 24)
    except:
        font_btn = pygame.font.Font(None, 24)

    # Opções do menu
    buttons = ["Tentar Novamente", "Voltar para o Menu", "Sair"]
    selected_button = 0
    prev_hovered = -1

    # Delays e Tempos
    DELAY_ENTRE_BOTOES = 200
    ultima_mudanca_de_botao = pygame.time.get_ticks()
    clock = pygame.time.Clock()

    # Partículas de Estilhaço de Tempo
    shards = []
    for _ in range(40):
        shards.append({
            "x": random.uniform(0, largura),
            "y": random.uniform(0, altura),
            "vx": random.uniform(-0.8, 0.8),
            "vy": random.uniform(-1.2, -0.4),
            "angle": random.uniform(0, 360),
            "rot_speed": random.uniform(-2.0, 2.0),
            "size": random.uniform(3, 8),
            "color": random.choice([
                (0, 255, 204, random.randint(60, 180)),   # Ciano
                (180, 100, 255, random.randint(60, 180)), # Roxo
                (255, 50, 100, random.randint(60, 180))   # Vermelho
            ])
        })

    # Faíscas dinâmicas ao redor da seleção
    sparks = []

    # Configuração de fenda temporal
    p1 = (largura // 2 - 300, altura // 2 - 120)
    p2 = (largura // 2 + 300, altura // 2 + 120)
    crack_points = generate_crack_points(p1, p2, 60)
    ultimo_flicker_fenda = pygame.time.get_ticks()

    debuff_lines = _obter_mensagem_rewind()

    # Loop Principal da Tela
    running = True
    while running:
        agora = pygame.time.get_ticks()
        mx, my = pygame.mouse.get_pos()
        clicado = False

        # --- PROCESSAR EVENTOS ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if game_manager:
                    from game_manager import EstadoJogo
                    game_manager.mudar_estado(EstadoJogo.SAIR)
                running = False
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    clicado = True
                    
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_manager:
                        from game_manager import EstadoJogo
                        game_manager.mudar_estado(EstadoJogo.SAIR)
                    running = False
                    
                elif event.key in [pygame.K_w, pygame.K_UP]:
                    if agora - ultima_mudanca_de_botao >= DELAY_ENTRE_BOTOES:
                        selected_button = (selected_button - 1) % len(buttons)
                        ultima_mudanca_de_botao = agora
                        tocar_hover()
                        
                elif event.key in [pygame.K_s, pygame.K_DOWN]:
                    if agora - ultima_mudanca_de_botao >= DELAY_ENTRE_BOTOES:
                        selected_button = (selected_button + 1) % len(buttons)
                        ultima_mudanca_de_botao = agora
                        tocar_hover()
                        
                elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    escolha = buttons[selected_button]
                    
                    if escolha == "Sair":
                        if game_manager:
                            from game_manager import EstadoJogo
                            game_manager.mudar_estado(EstadoJogo.SAIR)
                        running = False
                        
                    elif escolha == "Voltar para o Menu":
                        if game_manager:
                            from game_manager import EstadoJogo
                            game_manager.mudar_estado(EstadoJogo.MENU_PRINCIPAL)
                            return
                        else:
                            import Ruptura_Temporal
                    elif escolha == "Tentar Novamente":
                        if tratar_tentar_novamente(game_manager):
                            return

        # Controle de Joystick Xbox
        if joystick and joystick.get_init():
            try:
                eixo_vertical = joystick.get_axis(1)
                if eixo_vertical < -0.5 and agora - ultima_mudanca_de_botao >= DELAY_ENTRE_BOTOES:
                    selected_button = (selected_button - 1) % len(buttons)
                    ultima_mudanca_de_botao = agora
                    tocar_hover()
                elif eixo_vertical > 0.5 and agora - ultima_mudanca_de_botao >= DELAY_ENTRE_BOTOES:
                    selected_button = (selected_button + 1) % len(buttons)
                    ultima_mudanca_de_botao = agora
                    tocar_hover()

                if joystick.get_button(0):  # Botão A
                    tocar_selecionar()
                    escolha = buttons[selected_button]
                    if escolha == "Sair":
                        if game_manager:
                            from game_manager import EstadoJogo
                            game_manager.mudar_estado(EstadoJogo.SAIR)
                        running = False
                    elif escolha == "Voltar para o Menu":
                        if game_manager:
                            from game_manager import EstadoJogo
                            game_manager.mudar_estado(EstadoJogo.MENU_PRINCIPAL)
                            return
                        else:
                            import Ruptura_Temporal
                    elif escolha == "Tentar Novamente":
                        if tratar_tentar_novamente(game_manager):
                            return
            except:
                pass

        # --- RENDERIZAR FUNDO E EFEITOS ---
        window.fill((10, 8, 14))

        # Grade Digital cibernética
        for gx in range(0, largura, 80):
            for gy in range(0, altura, 80):
                pygame.draw.circle(window, (255, 50, 80, 8), (gx, gy), 1)

        # Fenda temporal (flickering elétrico)
        if agora - ultimo_flicker_fenda > random.choice([80, 150, 300]):
            crack_points = generate_crack_points(p1, p2, random.uniform(30, 75))
            ultimo_flicker_fenda = agora

        # Desenhar fenda em camadas (Glow centralizado)
        try:
            glow_surf = pygame.Surface((largura, altura), pygame.SRCALPHA)
            pygame.draw.lines(glow_surf, (255, 50, 100, 30), False, crack_points, 8)
            pygame.draw.lines(glow_surf, (180, 100, 255, 60), False, crack_points, 4)
            pygame.draw.lines(glow_surf, (255, 255, 255, 200), False, crack_points, 2)
            window.blit(glow_surf, (0, 0))
        except:
            pass

        # Desenhar e Atualizar Partículas de Estilhaços
        for s in shards:
            s["x"] += s["vx"]
            s["y"] += s["vy"]
            s["angle"] += s["rot_speed"]
            
            # Resetar se sair da tela
            if s["y"] < -20 or s["x"] < -20 or s["x"] > largura + 20:
                s["x"] = random.uniform(0, largura)
                s["y"] = altura + 20
                
            # Desenhar estilhaço como triângulo giratório translúcido
            sz = s["size"]
            ang = math.radians(s["angle"])
            points = [
                (s["x"] + math.cos(ang) * sz, s["y"] + math.sin(ang) * sz),
                (s["x"] + math.cos(ang + 2.09) * sz, s["y"] + math.sin(ang + 2.09) * sz),
                (s["x"] + math.cos(ang + 4.18) * sz, s["y"] + math.sin(ang + 4.18) * sz)
            ]
            
            # Surface com canal alpha para os triângulos
            shard_surf = pygame.Surface((int(sz*3), int(sz*3)), pygame.SRCALPHA)
            rel_points = [(p[0] - s["x"] + sz*1.5, p[1] - s["y"] + sz*1.5) for p in points]
            pygame.draw.polygon(shard_surf, s["color"], rel_points)
            window.blit(shard_surf, (int(s["x"] - sz*1.5), int(s["y"] - sz*1.5)))

        # --- TEXTO DE GAME OVER (GLITCH ABERRAÇÃO CROMÁTICA) ---
        glitch_offset = random.randint(-4, 4) if random.random() < 0.15 else 1
        
        txt_cyan = font_large.render("FLUXO TEMPORAL ROMPIDO", True, (0, 255, 204))
        txt_magenta = font_large.render("FLUXO TEMPORAL ROMPIDO", True, (255, 0, 128))
        txt_white = font_large.render("FLUXO TEMPORAL ROMPIDO", True, (255, 255, 255))
        
        title_x = largura // 2 - txt_white.get_width() // 2
        title_y = altura // 5
        
        window.blit(txt_cyan, (title_x - glitch_offset, title_y))
        window.blit(txt_magenta, (title_x + glitch_offset, title_y))
        window.blit(txt_white, (title_x, title_y))

        # Legenda explicativa
        txt_sub = font_desc.render("A fenda colapsou o espaco-tempo. Sua jornada foi fragmentada.", True, (160, 160, 175))
        window.blit(txt_sub, (largura // 2 - txt_sub.get_width() // 2, title_y + 70))

        # Renderizar aviso pesado de rewind (atualiza dinamicamente)
        debuff_lines = _obter_mensagem_rewind()
        import Variaveis as _Var
        tentativas_esgotadas = _Var.tentativas_rewind >= _Var.MAX_TENTATIVAS_REWIND
        cor_aviso = (120, 60, 60) if tentativas_esgotadas else (255, 75, 75)
        y_aviso = title_y + 105
        for line in debuff_lines:
            txt_aviso = font_desc.render(line, True, cor_aviso)
            window.blit(txt_aviso, (largura // 2 - txt_aviso.get_width() // 2, y_aviso))
            y_aviso += 22

        # Indicador de tentativas restantes
        restantes = max(0, _Var.MAX_TENTATIVAS_REWIND - _Var.tentativas_rewind)
        txt_tentativas = font_desc.render(f"Regressoes restantes: {restantes}/{_Var.MAX_TENTATIVAS_REWIND}", True, (180, 180, 200) if restantes > 0 else (80, 40, 40))
        window.blit(txt_tentativas, (largura // 2 - txt_tentativas.get_width() // 2, y_aviso + 4))

        # --- BOTÕES / CARDS INTERATIVOS ---
        card_w = 330
        card_h = 55
        y_start = altura // 2 - 10
        
        for idx, text in enumerate(buttons):
            item_y = y_start + idx * 72
            rect_btn = pygame.Rect(largura // 2 - card_w // 2, item_y, card_w, card_h)
            
            # Hover check
            is_hover = rect_btn.collidepoint(mx, my)
            if is_hover:
                if selected_button != idx:
                    selected_button = idx
                    tocar_hover()
                if clicado:
                    tocar_selecionar()
                    if text == "Sair":
                        if game_manager:
                            from game_manager import EstadoJogo
                            game_manager.mudar_estado(EstadoJogo.SAIR)
                        running = False
                    elif text == "Voltar para o Menu":
                        if game_manager:
                            from game_manager import EstadoJogo
                            game_manager.mudar_estado(EstadoJogo.MENU_PRINCIPAL)
                            return
                        else:
                            import Ruptura_Temporal
                    elif text == "Tentar Novamente":
                        if tratar_tentar_novamente(game_manager):
                            return

            is_selected = (selected_button == idx)

            # Verificar se o botão "Tentar Novamente" está desabilitado
            btn_desabilitado = (text == "Tentar Novamente" and tentativas_esgotadas)
            
            # Cores dinâmicas de borda baseadas na opção
            if btn_desabilitado:
                border_color = (50, 40, 45)
                bg_color = (12, 10, 14, 100)
                border_width = 1
            elif is_selected:
                if text == "Tentar Novamente":
                    border_color = (0, 255, 204) # Ciano elétrico
                elif text == "Voltar para o Menu":
                    border_color = (180, 100, 255) # Roxo cósmico
                else:
                    border_color = (255, 80, 80) # Vermelho alerta
                bg_color = (30, 20, 35, 220)
                border_width = 2
            else:
                border_color = (75, 70, 85)
                bg_color = (15, 12, 18, 150)
                border_width = 1

            # Desenhar Card
            surf_card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(surf_card, bg_color, (0, 0, card_w, card_h), border_radius=10)
            pygame.draw.rect(surf_card, border_color, (0, 0, card_w, card_h), width=border_width, border_radius=10)
            
            # Glow suave no card selecionado (não para desabilitados)
            if is_selected and not btn_desabilitado:
                pulsar_glow = 20 + int(math.sin(agora * 0.015) * 15)
                pygame.draw.rect(surf_card, (border_color[0], border_color[1], border_color[2], pulsar_glow), (4, 4, card_w - 8, card_h - 8), border_radius=6)
            
            window.blit(surf_card, (rect_btn.x, rect_btn.y))

            # Desenhar texto do botão
            if btn_desabilitado:
                txt_color = (60, 50, 55)
            elif is_selected:
                txt_color = (255, 255, 255)
            else:
                txt_color = (140, 140, 150)
            rendered_text = font_btn.render(text, True, txt_color)
            window.blit(rendered_text, (rect_btn.centerx - rendered_text.get_width() // 2, rect_btn.centery - rendered_text.get_height() // 2))

            # Spawning sparks around selected card edges
            if is_selected and random.random() < 0.35:
                # Top, bottom, left or right edge
                edge = random.choice(["top", "bottom", "left", "right"])
                if edge == "top":
                    sx = random.uniform(rect_btn.left, rect_btn.right)
                    sy = rect_btn.top
                elif edge == "bottom":
                    sx = random.uniform(rect_btn.left, rect_btn.right)
                    sy = rect_btn.bottom
                elif edge == "left":
                    sx = rect_btn.left
                    sy = random.uniform(rect_btn.top, rect_btn.bottom)
                else:
                    sx = rect_btn.right
                    sy = random.uniform(rect_btn.top, rect_btn.bottom)
                
                sparks.append({
                    "x": sx,
                    "y": sy,
                    "vx": random.uniform(-1.0, 1.0),
                    "vy": random.uniform(-1.5, 0.5),
                    "life": 1.0,
                    "color": border_color
                })

        # Atualizar e Desenhar Faíscas
        for sp in sparks[:]:
            sp["x"] += sp["vx"]
            sp["y"] += sp["vy"]
            sp["life"] -= 0.04
            if sp["life"] <= 0:
                sparks.remove(sp)
                continue
            
            # Desenhar pequena faísca
            r = int(2.5 * sp["life"])
            if r > 0:
                spark_alpha = int(255 * sp["life"])
                c = sp["color"]
                spark_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(spark_surf, (c[0], c[1], c[2], spark_alpha), (r, r), r)
                window.blit(spark_surf, (int(sp["x"] - r), int(sp["y"] - r)))

        pygame.display.flip()
        clock.tick(60)

    # Ao fechar o loop, encerra de forma limpa
    if game_manager:
        # Se for controlado por game_manager, retorna controle a ele
        return
    else:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    executar_game_over()
