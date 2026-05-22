import pygame
import sys
import math
import os

# Atributos e descrições para todas as cartas
atributos_todas_cartas = {
    "Speed Boost": {
        "Nick": "Vento Celeste",
        "descricao": "Aumente sua velocidade em +10%. Corra como o vento e fuja de qualquer situação perigosa.",
        "imagem_path": "Sprites/Deck/Speed_boost1.png"
    },
    "Porção": {
        "Nick": "Elixir Vital",
        "descricao": "Recupere 25% da sua vida máxima e ganhe mais vida máxima permanentemente.",
        "imagem_path": "Sprites/Deck/carta_por1.png"
    },
    "Disparo crescente": {
        "Nick": "Impacto Escalante",
        "descricao": "Ganhe +27 de dano e deixe os inimigos temendo seus tiros poderosos.",
        "imagem_path": "Sprites/Deck/carta_odio1.png"
    },
    "Tempestade": {
        "Nick": "Tempestade Crescente",
        "descricao": "Aumente sua chance crítica em 2% e triplique o dano causado. Transforme cada acerto em uma tempestade!",
        "imagem_path": "Sprites/Deck/Carta_tempestade_crescente1.png"
    },
    "Cura": {
        "Nick": "Mordida Sombria",
        "descricao": "Restaure 3% da sua vida a cada hit e 4% a cada ativação. Recupere sua saúde enquanto luta!",
        "imagem_path": "Sprites/Deck/Carta_roubo_vida1.png"
    },
    "Trembo": {
        "Nick": "Reversão Temporal",
        "descricao": "Quando a morte se aproxima, o tempo volta. Recupere toda a sua saúde e reapareça em outro local!",
        "imagem_path": "Sprites/Deck/carta_trem1.png"
    },
    "Speed Atack": {
        "Nick": "Fluidez Letal",
        "descricao": "Aumente a velocidade de ataque em 5%, tornando seus tiros rápidos e letais.",
        "imagem_path": "Sprites/Deck/carta_onda.png"
    },
    "Teleporte": {
        "Nick": "Salto Espacial",
        "descricao": "Reduza o cooldown do teleporte em 3%, permitindo que você se mova rapidamente entre os campos de batalha.",
        "imagem_path": "Sprites/Deck/carta_teleporte1.png"
    },
    "Petro": {
        "Nick": "Sentinela Leal",
        "descricao": "Desencadeie o poder de um pequeno guardião. Alimente-o para ver seu poder crescer e proteger você!",
        "imagem_path": "Sprites/Deck/carta_petro1.png"
    },
    "Defesa": {
        "Nick": "Escudo Fásico",
        "descricao": "Aumente sua resistência em +5 e mitigue os danos dos inimigos.",
        "imagem_path": "Sprites/Deck/carta_defesa1.png"
    },
    "Sorte": {
        "Nick": "Anomalia Favorável",
        "descricao": "Aumente suas chances de obter cartas raras com 2% de sorte adicional.",
        "imagem_path": "Sprites/Deck/carta_sorte1.png"
    },
    "Poison": {
        "Nick": "Toxina Temporal",
        "descricao": "Infunde seus ataques com veneno, causando dano contínuo ao longo do tempo aos inimigos atingidos.",
        "imagem_path": "Sprites/Deck/carta_poison1.png"
    },
    "Coletora": {
        "Nick": "Foice do Tempo",
        "descricao": "Coleta a energia vital de inimigos enfraquecidos, executando-os instantaneamente quando sua vida está baixa.",
        "imagem_path": "Sprites/Deck/carta_estalo1.png"
    }
}

class ParticulaPause:
    def __init__(self, largura_tela, altura_tela):
        # Fallback determinístico para evitar math.random
        import random
        self.x = random.uniform(0, largura_tela)
        self.y = altura_tela + 20
        self.vel_y = - (1.0 + random.uniform(0, 1) * 2.0)
        self.tamanho = int(2 + random.uniform(0, 1) * 4)
        self.cor = (0, 255, 200) if random.random() > 0.5 else (180, 0, 255)
        self.oscilacao = random.uniform(0, 10)
        self.frequencia = 0.02 + random.uniform(0, 1) * 0.05

    def atualizar(self, altura_tela):
        import random
        self.y += self.vel_y
        self.oscilacao += self.frequencia
        self.x += math.sin(self.oscilacao) * 0.5
        if self.y < -20:
            self.y = altura_tela + 20
            self.x = random.uniform(0, 1200)

    def desenhar(self, tela):
        pygame.draw.circle(tela, self.cor, (int(self.x), int(self.y)), self.tamanho)

def carregar_fontes():
    fontes = {}
    caminho_glitch = 'Texto/Doctor Glitch.otf'
    caminho_hearts = 'Texto/rainyhearts.ttf'

    # Carrega fontes com fallback
    if os.path.exists(caminho_glitch):
        fontes["titulo"] = lambda s: pygame.font.Font(caminho_glitch, s)
    else:
        fontes["titulo"] = lambda s: pygame.font.Font(None, s)

    if os.path.exists(caminho_hearts):
        fontes["texto"] = lambda s: pygame.font.Font(caminho_hearts, s)
    else:
        fontes["texto"] = lambda s: pygame.font.Font(None, s)
        
    return fontes

def wrap_text(texto, fonte, largura_maxima):
    palavras = texto.split()
    linhas = []
    linha_atual = ""
    for palavra in palavras:
        test_line = (linha_atual + " " + palavra).strip()
        if fonte.size(test_line)[0] <= largura_maxima:
            linha_atual = test_line
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra
    if linha_atual:
        linhas.append(linha_atual)
    return linhas

def exibir_tela_pause(tela, cartas_compradas, joystick=None):
    pygame.init()
    clock = pygame.time.Clock()
    largura_tela, altura_tela = tela.get_size()

    # Prepara lista de cartas adquiridas
    cartas_adquiridas = []
    for nome, qtd in cartas_compradas.items():
        if qtd > 0:
            dados = atributos_todas_cartas.get(nome, {
                "Nick": nome,
                "descricao": "Carta de upgrade temporal adquirida nesta jornada.",
                "imagem_path": None
            })
            
            # Carrega e escala imagem da carta
            img = None
            if dados["imagem_path"] and os.path.exists(dados["imagem_path"]):
                try:
                    img = pygame.image.load(dados["imagem_path"]).convert_alpha()
                except:
                    pass
            
            # Se falhar no carregamento, gera um placeholder estilizado
            if img is None:
                img = pygame.Surface((150, 200), pygame.SRCALPHA)
                img.fill((40, 40, 50))
                pygame.draw.rect(img, (0, 255, 200), (0, 0, 150, 200), 4)
                # Renderiza letra inicial no centro
                f_temp = pygame.font.Font(None, 80)
                letra = f_temp.render(nome[0], True, (0, 255, 200))
                img.blit(letra, (75 - letra.get_width()//2, 100 - letra.get_height()//2))

            cartas_adquiridas.append({
                "nome": nome,
                "Nick": dados["Nick"],
                "descricao": dados["descricao"],
                "imagem": img,
                "quantidade": qtd
            })

    # Fontes
    fontes = carregar_fontes()
    fonte_titulo_large = fontes["titulo"](64)
    fonte_titulo_sub = fontes["texto"](28)
    fonte_card_name = fontes["titulo"](32)
    fonte_card_nick = fontes["texto"](26)
    fonte_desc = fontes["texto"](20)
    fonte_footer = fontes["texto"](22)

    # Partículas no background
    particulas = [ParticulaPause(largura_tela, altura_tela) for _ in range(30)]

    # Controle de navegação
    selecionado_idx = 0
    current_offset = 0.0
    
    # Parâmetros de layout das cartas
    base_largura = 150
    base_altura = 200
    spacing = 220
    
    # Joystick cooldown
    last_joystick_move = pygame.time.get_ticks()
    cooldown_joy = 200

    jogo_pausado = True
    while jogo_pausado:
        agora = pygame.time.get_ticks()
        
        # --- Eventos ---
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    jogo_pausado = False
                    
                elif len(cartas_adquiridas) > 0:
                    if evento.key in [pygame.K_d, pygame.K_RIGHT]:
                        selecionado_idx = (selecionado_idx + 1) % len(cartas_adquiridas)
                    elif evento.key in [pygame.K_a, pygame.K_LEFT]:
                        selecionado_idx = (selecionado_idx - 1) % len(cartas_adquiridas)

            elif evento.type == pygame.JOYBUTTONDOWN:
                # Botão B (geralmente index 1) ou Start (index 7) para despausar
                if evento.button in [1, 7]:
                    jogo_pausado = False

        # --- Eixos Joystick ---
        if joystick and len(cartas_adquiridas) > 0:
            if agora - last_joystick_move > cooldown_joy:
                eixo_x = joystick.get_axis(0)
                if eixo_x > 0.5:
                    selecionado_idx = (selecionado_idx + 1) % len(cartas_adquiridas)
                    last_joystick_move = agora
                elif eixo_x < -0.5:
                    selecionado_idx = (selecionado_idx - 1) % len(cartas_adquiridas)
                    last_joystick_move = agora

        # --- LERP de suavização da transição do carousel ---
        current_offset += (selecionado_idx - current_offset) * 0.15

        # --- Renderização ---
        # Darkening glass background
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((10, 10, 18, 225))
        tela.blit(overlay, (0, 0))

        # Desenha partículas
        for p in particulas:
            p.atualizar(altura_tela)
            p.desenhar(tela)

        # Desenha efeito de vortex ou grelha cibernética abstrata no centro
        cy = altura_tela // 2.5
        pulsar = (math.sin(agora * 0.004) + 1) / 2
        
        # Título do Jogo / Menu
        txt_pausa = fonte_titulo_large.render("RUPTURA TEMPORAL", True, (255, 255, 255))
        txt_sub = fonte_titulo_sub.render("FLUXO TEMPORAL SUSPENSO - ARQUIVO DE ANOMALIAS", True, (0, 255, 200))
        
        tela.blit(txt_pausa, (largura_tela // 2 - txt_pausa.get_width() // 2, 40))
        tela.blit(txt_sub, (largura_tela // 2 - txt_sub.get_width() // 2, 100))

        if len(cartas_adquiridas) == 0:
            # Estado vazio
            txt_vazio = fonte_card_name.render("NENHUMA ANOMALIA ADQUIRIDA AINDA", True, (200, 200, 200))
            txt_vazio_desc = fonte_desc.render("Derrote inimigos e colete moedas para alterar sua linha temporal.", True, (150, 150, 150))
            
            # Painel Central de aviso
            painel_w = 600
            painel_h = 160
            px = largura_tela // 2 - painel_w // 2
            py = altura_tela // 2 - painel_h // 2
            
            pygame.draw.rect(tela, (15, 15, 25, 200), (px, py, painel_w, painel_h), border_radius=12)
            pygame.draw.rect(tela, (0, 255, 200, 100), (px, py, painel_w, painel_h), 2, border_radius=12)
            
            tela.blit(txt_vazio, (largura_tela // 2 - txt_vazio.get_width() // 2, py + 40))
            tela.blit(txt_vazio_desc, (largura_tela // 2 - txt_vazio_desc.get_width() // 2, py + 90))
        else:
            # Renderiza Carousel de cartas
            cx_tela = largura_tela // 2
            
            # Desenha primeiro as cartas inativas para garantir ordenamento (z-index)
            # Ordenamos por distância do índice selecionado para que o selecionado fique no topo
            cartas_ordenadas = []
            for idx, c in enumerate(cartas_adquiridas):
                dist = abs(idx - current_offset)
                cartas_ordenadas.append((dist, idx, c))
            cartas_ordenadas.sort(key=lambda x: x[0], reverse=True)

            for dist, idx, c in cartas_ordenadas:
                # Posição x baseada no lerped offset
                rel_idx = idx - current_offset
                card_cx = cx_tela + rel_idx * spacing
                card_cy = cy
                
                # Fatores dinâmicos de escala e transparência baseados na distância ao centro
                scale_factor = max(0.65, 1.25 - dist * 0.45)
                opacity = max(40, int(255 - dist * 160))
                
                w = int(base_largura * scale_factor)
                h = int(base_altura * scale_factor)
                
                # Redimensiona imagem da carta
                scaled_img = pygame.transform.scale(c["imagem"], (w, h))
                
                # Desenha sombra/glow atrás do ativo
                if idx == selecionado_idx:
                    # Neon cyan/purple glow pulsante
                    glow_size = int(12 + pulsar * 8)
                    glow_surf = pygame.Surface((w + glow_size * 2, h + glow_size * 2), pygame.SRCALPHA)
                    glow_cor = (0, 255, 200, int(80 + pulsar * 80))
                    pygame.draw.rect(glow_surf, glow_cor, (0, 0, w + glow_size * 2, h + glow_size * 2), border_radius=18)
                    tela.blit(glow_surf, (card_cx - w//2 - glow_size, card_cy - h//2 - glow_size))
                
                # Ajusta opacidade criando uma surface intermediária
                temp_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                temp_surf.blit(scaled_img, (0, 0))
                temp_surf.set_alpha(opacity)
                
                tela.blit(temp_surf, (card_cx - w//2, card_cy - h//2))
                
                # Se for a carta ativa, desenha o indicador de quantidade no próprio card
                qtd_txt = fonte_card_name.render(f"x{c['quantidade']}", True, (0, 255, 200) if idx == selecionado_idx else (255, 255, 255))
                qtd_surf = pygame.Surface((qtd_txt.get_width() + 16, qtd_txt.get_height() + 8), pygame.SRCALPHA)
                pygame.draw.rect(qtd_surf, (10, 10, 20, 220), (0, 0, qtd_surf.get_width(), qtd_surf.get_height()), border_radius=6)
                pygame.draw.rect(qtd_surf, (0, 255, 200) if idx == selecionado_idx else (100, 100, 100), (0, 0, qtd_surf.get_width(), qtd_surf.get_height()), 2, border_radius=6)
                qtd_surf.blit(qtd_txt, (8, 4))
                
                # Blit quantidade no canto superior direito do card
                tela.blit(qtd_surf, (card_cx + w//2 - qtd_surf.get_width()//2, card_cy - h//2 - qtd_surf.get_height()//2))

            # --- Painel de Informações da Carta Ativa ---
            c_ativa = cartas_adquiridas[selecionado_idx]
            
            panel_w = 700
            panel_h = 160
            panel_x = largura_tela // 2 - panel_w // 2
            panel_y = altura_tela - 240
            
            # Painel com efeito vidro escuro
            pygame.draw.rect(tela, (15, 15, 22, 220), (panel_x, panel_y, panel_w, panel_h), border_radius=16)
            pygame.draw.rect(tela, (0, 255, 200, 180), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=16)
            
            # Informações detalhadas
            txt_nome = fonte_card_name.render(c_ativa["nome"].upper(), True, (255, 255, 255))
            txt_nick = fonte_card_nick.render(f"\"{c_ativa['Nick']}\"", True, (200, 200, 100))
            txt_qtd = fonte_card_nick.render(f"Quantidade: {c_ativa['quantidade']}", True, (0, 255, 200))
            
            tela.blit(txt_nome, (panel_x + 30, panel_y + 20))
            tela.blit(txt_nick, (panel_x + 30 + txt_nome.get_width() + 15, panel_y + 26))
            tela.blit(txt_qtd, (panel_x + panel_w - txt_qtd.get_width() - 30, panel_y + 20))
            
            # Linha divisória neon
            pygame.draw.line(tela, (0, 255, 200, 80), (panel_x + 30, panel_y + 60), (panel_x + panel_w - 30, panel_y + 60), 2)
            
            # Descrição com auto-wrap
            linhas_desc = wrap_text(c_ativa["descricao"], fonte_desc, panel_w - 60)
            for l_idx, linha in enumerate(linhas_desc):
                desc_render = fonte_desc.render(linha, True, (200, 200, 200))
                tela.blit(desc_render, (panel_x + 30, panel_y + 75 + l_idx * 22))

        # --- Instruções de rodapé ---
        txt_footer = fonte_footer.render("[A / D] ou [Setas] para Navegar | [ESC] ou [Start] para Retornar", True, (150, 150, 150))
        tela.blit(txt_footer, (largura_tela // 2 - txt_footer.get_width() // 2, altura_tela - 50))

        pygame.display.flip()
        clock.tick(60)
        
    return False
