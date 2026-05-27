import pygame
import sys
import math
import os
import json
from sons_procedurais import tocar_hover, tocar_selecionar

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
        "descricao": "Aumente suas chances de obter cartas raras com 0.6% de sorte adicional.",
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

def abrir_configuracoes_graficas(tela, fontes, fundo_pausa=None):
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
    
    largura_tela, altura_tela = tela.get_size()
    selecionado = 0
    clock = pygame.time.Clock()
    
    fonte_titulo_tela = fontes["titulo"](48)
    fonte_opcao_tela = fontes["texto"](26)
    fonte_valor_tela = fontes["texto"](22)
    fonte_instrucao = fontes["texto"](20)
    
    rodando = True
    while rodando:
        if fundo_pausa:
            tela.blit(fundo_pausa, (0, 0))
        else:
            tela.fill((10, 10, 20))
            
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 220))
        
        # Cyber Grid lines drawn on overlay (with alpha)
        for y in range(0, altura_tela, 8):
            pygame.draw.line(overlay, (0, 255, 204, 10), (0, y), (largura_tela, y))
            
        tela.blit(overlay, (0, 0))
        
        texto_titulo = fonte_titulo_tela.render("CONFIGURACOES GRAFICAS", True, (0, 255, 204))
        ret_tit = texto_titulo.get_rect(center=(largura_tela // 2, altura_tela // 8))
        tela.blit(texto_titulo, ret_tit)
        
        mx, my = pygame.mouse.get_pos()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
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
                        try:
                            indice_atual = valores.index(valor_atual)
                        except ValueError:
                            indice_atual = 0
                        
                        if evento.key in [pygame.K_RIGHT, pygame.K_d]:
                            novo_indice = (indice_atual + 1) % len(valores)
                        else:
                            novo_indice = (indice_atual - 1) % len(valores)
                        
                        config[chave] = valores[novo_indice]
                        with open("saves/config_graficos.json", "w") as f:
                            json.dump(config, f, indent=4)
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    if opcoes_config[selecionado]["nome"] == "Voltar":
                        rodando = False
                elif evento.key == pygame.K_ESCAPE:
                    rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                # Voltar Click check
                y_inicial = altura_tela // 4 + 20
                espacamento = 50
                for i, opcao in enumerate(opcoes_config):
                    y_pos = y_inicial + i * espacamento
                    rect_item = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 38)
                    if rect_item.collidepoint(mx, my):
                        if i == selecionado:
                            if opcao["nome"] == "Voltar":
                                rodando = False
                            elif opcao["chave"]:
                                # Cycle to next value on direct click
                                chave = opcao["chave"]
                                valores = opcao["valores"]
                                valor_atual = config[chave]
                                try:
                                    idx = (valores.index(valor_atual) + 1) % len(valores)
                                except:
                                    idx = 0
                                config[chave] = valores[idx]
                                with open("saves/config_graficos.json", "w") as f:
                                    json.dump(config, f, indent=4)
                        else:
                            selecionado = i
                    
        y_inicial = altura_tela // 4 + 20
        espacamento = 50
        
        for i, opcao in enumerate(opcoes_config):
            y_pos = y_inicial + i * espacamento
            
            if i == selecionado:
                rect_bg = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 38)
                pygame.draw.rect(tela, (0, 180, 200, 65), rect_bg, border_radius=6)
                pygame.draw.rect(tela, (0, 255, 230), rect_bg, width=2, border_radius=6)
                cor_nome = (255, 255, 255)
            else:
                cor_nome = (195, 195, 205)
                
            texto_nome = fonte_opcao_tela.render(opcao["nome"], True, cor_nome)
            tela.blit(texto_nome, (largura_tela // 4, y_pos))
            
            if opcao["chave"]:
                valor_atual = config[opcao["chave"]]
                try:
                    indice_valor = opcao["valores"].index(valor_atual)
                except ValueError:
                    indice_valor = 0
                label_valor = opcao["labels"][indice_valor]
                
                cor_valor = (0, 255, 204) if i == selecionado else (210, 210, 220)
                texto_valor = fonte_valor_tela.render(label_valor, True, cor_valor)
                tela.blit(texto_valor, (largura_tela // 2 + 50, y_pos + 2))
                
                if i == selecionado:
                    seta_esq = fonte_valor_tela.render("<", True, (255, 255, 255))
                    seta_dir = fonte_valor_tela.render(">", True, (255, 255, 255))
                    tela.blit(seta_esq, (largura_tela // 2 + 25, y_pos + 2))
                    tela.blit(seta_dir, (largura_tela // 2 + 220, y_pos + 2))
                    
        rect_desc = pygame.Rect(largura_tela // 2 - 360, 480, 720, 50)
        pygame.draw.rect(tela, (15, 10, 30, 200), rect_desc, border_radius=8)
        pygame.draw.rect(tela, (0, 255, 230, 80), rect_desc, width=1, border_radius=8)
        
        opt_sel = opcoes_config[selecionado]
        if opt_sel["chave"] is None:
            texto_desc_str = "Retornar ao menu de configurações anterior."
        else:
            val_sel = config[opt_sel["chave"]]
            texto_desc_str = descricoes_valores[opt_sel["chave"]].get(val_sel, "")
            
        surf_desc_texto = fonte_valor_tela.render(texto_desc_str, True, (200, 200, 220))
        rect_desc_texto = surf_desc_texto.get_rect(center=rect_desc.center)
        tela.blit(surf_desc_texto, rect_desc_texto)
        
        instrucao_txt = "W/S: Navegar | A/D: Alterar | ENTER/ESC: Voltar"
        texto_inst = fonte_instrucao.render(instrucao_txt, True, (150, 150, 150))
        tela.blit(texto_inst, (largura_tela // 2 - texto_inst.get_width() // 2, altura_tela - 50))
        
        pygame.display.flip()
        clock.tick(60)

def abrir_configuracoes_audio(tela, fontes, fundo_pausa=None):
    try:
        with open("saves/config_audio.json", "r") as f:
            config = json.load(f)
    except:
        config = {
            "volume_musica": 0.5,
            "volume_efeitos": 0.5,
            "volume_master": 1.0
        }
        
    largura_tela, altura_tela = tela.get_size()
    selecionado = 0
    clock = pygame.time.Clock()
    
    fonte_titulo_tela = fontes["titulo"](48)
    fonte_opcao_tela = fontes["texto"](26)
    fonte_valor_tela = fontes["texto"](22)
    fonte_instrucao = fontes["texto"](20)
    
    opcoes = ["volume_master", "volume_musica", "volume_efeitos", "voltar"]
    labels = ["Volume Master", "Volume Música", "Volume Efeitos", "Voltar"]
    
    descricoes_audio = {
        "volume_master": "Volume geral. Ajusta a música e os efeitos sonoros proporcionalmente.",
        "volume_musica": "Trilha sonora. Ajusta o volume da música de fundo e ambiente.",
        "volume_efeitos": "Efeitos sonoros. Ajusta o volume de tiros, explosões e impactos.",
        "voltar": "Retornar ao menu de configurações anterior."
    }
    
    rodando = True
    while rodando:
        if fundo_pausa:
            tela.blit(fundo_pausa, (0, 0))
        else:
            tela.fill((10, 10, 20))
            
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 220))
        
        # Cyber Grid lines drawn on overlay (with alpha)
        for y in range(0, altura_tela, 8):
            pygame.draw.line(overlay, (0, 255, 204, 10), (0, y), (largura_tela, y))
            
        tela.blit(overlay, (0, 0))
        
        texto_titulo = fonte_titulo_tela.render("CONFIGURACOES DE AUDIO", True, (0, 255, 204))
        ret_tit = texto_titulo.get_rect(center=(largura_tela // 2, altura_tela // 8))
        tela.blit(texto_titulo, ret_tit)
        
        mx, my = pygame.mouse.get_pos()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado = (selecionado - 1) % len(opcoes)
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado = (selecionado + 1) % len(opcoes)
                elif evento.key in [pygame.K_LEFT, pygame.K_a]:
                    if opcoes[selecionado] != "voltar":
                        chave = opcoes[selecionado]
                        config[chave] = max(0.0, config[chave] - 0.1)
                        with open("saves/config_audio.json", "w") as f:
                            json.dump(config, f, indent=4)
                        pygame.mixer.music.set_volume(config["volume_musica"] * config["volume_master"])
                elif evento.key in [pygame.K_RIGHT, pygame.K_d]:
                    if opcoes[selecionado] != "voltar":
                        chave = opcoes[selecionado]
                        config[chave] = min(1.0, config[chave] + 0.1)
                        with open("saves/config_audio.json", "w") as f:
                            json.dump(config, f, indent=4)
                        pygame.mixer.music.set_volume(config["volume_musica"] * config["volume_master"])
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    if opcoes[selecionado] == "voltar":
                        rodando = False
                elif evento.key == pygame.K_ESCAPE:
                    rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                y_inicial = altura_tela // 4 + 40
                espacamento = 65
                for i, opcao in enumerate(opcoes):
                    y_pos = y_inicial + i * espacamento
                    rect_bg = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 48)
                    if rect_bg.collidepoint(mx, my):
                        if i == selecionado:
                            if opcao == "voltar":
                                rodando = False
                            else:
                                # Standard volume click adjustment based on mouse x position relative to bar
                                barra_x = largura_tela // 2 - 20
                                barra_largura = 180
                                rel_x = mx - barra_x
                                if 0 <= rel_x <= barra_largura:
                                    pct = rel_x / barra_largura
                                    config[opcao] = round(pct, 1)
                                    with open("saves/config_audio.json", "w") as f:
                                        json.dump(config, f, indent=4)
                                    pygame.mixer.music.set_volume(config["volume_musica"] * config["volume_master"])
                        else:
                            selecionado = i
                    
        y_inicial = altura_tela // 4 + 40
        espacamento = 65
        
        for i, opcao in enumerate(opcoes):
            y_pos = y_inicial + i * espacamento
            
            if i == selecionado:
                rect_bg = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 48)
                pygame.draw.rect(tela, (0, 180, 200, 65), rect_bg, border_radius=6)
                pygame.draw.rect(tela, (0, 255, 230), rect_bg, width=2, border_radius=6)
                cor_nome = (255, 255, 255)
            else:
                cor_nome = (195, 195, 205)
                
            texto_nome = fonte_opcao_tela.render(labels[i], True, cor_nome)
            tela.blit(texto_nome, (largura_tela // 4, y_pos))
            
            if opcao != "voltar":
                valor = config[opcao]
                barra_x = largura_tela // 2 - 20
                barra_y = y_pos + 10
                barra_largura = 180
                barra_altura = 14
                
                pygame.draw.rect(tela, (50, 50, 50), (barra_x, barra_y, barra_largura, barra_altura), border_radius=4)
                
                cor_barra = (0, 255, 204) if i == selecionado else (100, 200, 180)
                largura_preenchimento = int(barra_largura * valor)
                pygame.draw.rect(tela, cor_barra, (barra_x, barra_y, largura_preenchimento, barra_altura), border_radius=4)
                
                pygame.draw.rect(tela, (255, 255, 255), (barra_x, barra_y, barra_largura, barra_altura), 1, border_radius=4)
                
                porcentagem = int(valor * 100)
                texto_porcentagem = fonte_valor_tela.render(f"{porcentagem}%", True, cor_nome)
                tela.blit(texto_porcentagem, (barra_x + barra_largura + 15, y_pos + 5))
                
                if i == selecionado:
                    seta_esq = fonte_valor_tela.render("<", True, (255, 255, 255))
                    seta_dir = fonte_valor_tela.render(">", True, (255, 255, 255))
                    tela.blit(seta_esq, (barra_x - 20, y_pos + 5))
                    tela.blit(seta_dir, (barra_x + barra_largura + 45, y_pos + 5))
                    
        rect_desc = pygame.Rect(largura_tela // 2 - 360, 480, 720, 50)
        pygame.draw.rect(tela, (15, 10, 30, 200), rect_desc, border_radius=8)
        pygame.draw.rect(tela, (0, 255, 230, 80), rect_desc, width=1, border_radius=8)
        
        opt_sel = opcoes[selecionado]
        texto_desc_str = descricoes_audio[opt_sel]
        
        surf_desc_texto = fonte_valor_tela.render(texto_desc_str, True, (200, 200, 220))
        rect_desc_texto = surf_desc_texto.get_rect(center=rect_desc.center)
        tela.blit(surf_desc_texto, rect_desc_texto)
        
        instrucao_txt = "W/S: Navegar | A/D: Alterar | ENTER/ESC: Voltar"
        texto_inst = fonte_instrucao.render(instrucao_txt, True, (150, 150, 150))
        tela.blit(texto_inst, (largura_tela // 2 - texto_inst.get_width() // 2, altura_tela - 50))
        
        pygame.display.flip()
        clock.tick(60)

def exibir_tela_pause(tela, cartas_compradas, joystick=None):
    pygame.init()
    clock = pygame.time.Clock()
    largura_tela, altura_tela = tela.get_size()
    fontes = carregar_fontes()
    fundo_pausa = tela.copy()
    
    opcoes_pause = [
        "Continuar",
        "Ajustar Controles",
        "Ajustar Áudio",
        "Ajustar Gráficos",
        "Ver Anomalias",
        "Sair ao Menu"
    ]
    
    descricoes_pause = {
        "Continuar": "Retornar ao combate e retomar a jornada.",
        "Ajustar Controles": "Configurar teclas do teclado e botões do mouse.",
        "Ajustar Áudio": "Ajustar volumes de música, efeitos e som geral.",
        "Ajustar Gráficos": "Modificar configurações de sombra, partículas e FPS.",
        "Ver Anomalias": "Visualizar a lista de anomalias adquiridas nesta jornada.",
        "Sair ao Menu": "Encerrar a corrida atual e retornar ao menu principal."
    }
    
    selecionado = 0
    estado_pause = "menu"
    
    cartas_adquiridas = []
    for nome, qtd in cartas_compradas.items():
        if qtd > 0:
            dados = atributos_todas_cartas.get(nome, {
                "Nick": nome,
                "descricao": "Carta de upgrade temporal adquirida nesta jornada.",
                "imagem_path": None
            })
            
            img = None
            if dados["imagem_path"] and os.path.exists(dados["imagem_path"]):
                try:
                    img = pygame.image.load(dados["imagem_path"]).convert_alpha()
                except:
                    pass
            
            if img is None:
                img = pygame.Surface((150, 200), pygame.SRCALPHA)
                img.fill((40, 40, 50))
                pygame.draw.rect(img, (0, 255, 200), (0, 0, 150, 200), 4)
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

    selecionado_card_idx = 0
    current_offset = 0.0
    
    fonte_titulo_large = fontes["titulo"](60)
    fonte_opcao_tela = fontes["texto"](28)
    fonte_valor_tela = fontes["texto"](22)
    fonte_desc = fontes["texto"](20)
    
    CARD_W = 280
    CARD_H = 340
    CARD_X = 70
    CARD_Y = 180
    
    # Joystick movement delay
    last_joy_move = 0
    
    rodando = True
    while rodando:
        agora = pygame.time.get_ticks()
        pulsar = (math.sin(agora * 0.005) + 1) / 2
        mx, my = pygame.mouse.get_pos()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif evento.type == pygame.KEYDOWN:
                if estado_pause == "menu":
                    if evento.key in [pygame.K_w, pygame.K_UP]:
                        selecionado = (selecionado - 1) % len(opcoes_pause)
                        tocar_hover()
                    elif evento.key in [pygame.K_s, pygame.K_DOWN]:
                        selecionado = (selecionado + 1) % len(opcoes_pause)
                        tocar_hover()
                    elif evento.key == pygame.K_ESCAPE:
                        tocar_selecionar()
                        return "continuar"
                    elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        tocar_selecionar()
                        opcao_sel = opcoes_pause[selecionado]
                        if opcao_sel == "Continuar":
                            return "continuar"
                        elif opcao_sel == "Ajustar Controles":
                            from Config_Teclas import tela_de_controles, carregar_config_teclas
                            cfg = carregar_config_teclas()
                            tela_de_controles(tela, cfg, largura_tela, altura_tela, fundo_pausa=fundo_pausa)
                        elif opcao_sel == "Ajustar Áudio":
                            abrir_configuracoes_audio(tela, fontes, fundo_pausa=fundo_pausa)
                        elif opcao_sel == "Ajustar Gráficos":
                            abrir_configuracoes_graficas(tela, fontes, fundo_pausa=fundo_pausa)
                        elif opcao_sel == "Ver Anomalias":
                            estado_pause = "anomalias"
                        elif opcao_sel == "Sair ao Menu":
                            return "sair"
                else: # "anomalias"
                    if evento.key == pygame.K_ESCAPE:
                        tocar_selecionar()
                        estado_pause = "menu"
                    elif len(cartas_adquiridas) > 0:
                        if evento.key in [pygame.K_d, pygame.K_RIGHT]:
                            selecionado_card_idx = (selecionado_card_idx + 1) % len(cartas_adquiridas)
                            tocar_hover()
                        elif evento.key in [pygame.K_a, pygame.K_LEFT]:
                            selecionado_card_idx = (selecionado_card_idx - 1) % len(cartas_adquiridas)
                            tocar_hover()

            elif evento.type == pygame.MOUSEBUTTONDOWN:
                mx, my = evento.pos
                if estado_pause == "menu":
                    for i, opcao in enumerate(opcoes_pause):
                        y_pos = CARD_Y + 24 + i * 48
                        rect_opcao = pygame.Rect(CARD_X + 15, y_pos - 6, CARD_W - 30, 42)
                        if rect_opcao.collidepoint(mx, my):
                            if i == selecionado:
                                tocar_selecionar()
                                opcao_sel = opcoes_pause[selecionado]
                                if opcao_sel == "Continuar":
                                    return "continuar"
                                elif opcao_sel == "Ajustar Controles":
                                    from Config_Teclas import tela_de_controles, carregar_config_teclas
                                    cfg = carregar_config_teclas()
                                    tela_de_controles(tela, cfg, largura_tela, altura_tela, fundo_pausa=fundo_pausa)
                                elif opcao_sel == "Ajustar Áudio":
                                    abrir_configuracoes_audio(tela, fontes, fundo_pausa=fundo_pausa)
                                elif opcao_sel == "Ajustar Gráficos":
                                    abrir_configuracoes_graficas(tela, fontes, fundo_pausa=fundo_pausa)
                                elif opcao_sel == "Ver Anomalias":
                                    estado_pause = "anomalias"
                                elif opcao_sel == "Sair ao Menu":
                                    return "sair"
                            else:
                                selecionado = i
                                tocar_hover()
                else: # "anomalias"
                    # Back to Menu button check
                    back_rect = pygame.Rect(largura_tela // 2 - 100, altura_tela - 65, 200, 36)
                    if back_rect.collidepoint(mx, my):
                        tocar_selecionar()
                        estado_pause = "menu"
            
            elif evento.type == pygame.JOYBUTTONDOWN:
                if estado_pause == "menu":
                    if evento.button == 0: # A button
                        tocar_selecionar()
                        opcao_sel = opcoes_pause[selecionado]
                        if opcao_sel == "Continuar":
                            return "continuar"
                        elif opcao_sel == "Ajustar Controles":
                            from Config_Teclas import tela_de_controles, carregar_config_teclas
                            cfg = carregar_config_teclas()
                            tela_de_controles(tela, cfg, largura_tela, altura_tela, fundo_pausa=fundo_pausa)
                        elif opcao_sel == "Ajustar Áudio":
                            abrir_configuracoes_audio(tela, fontes, fundo_pausa=fundo_pausa)
                        elif opcao_sel == "Ajustar Gráficos":
                            abrir_configuracoes_graficas(tela, fontes, fundo_pausa=fundo_pausa)
                        elif opcao_sel == "Ver Anomalias":
                            estado_pause = "anomalias"
                        elif opcao_sel == "Sair ao Menu":
                            return "sair"
                    elif evento.button in [1, 7]: # B or Start
                        tocar_selecionar()
                        return "continuar"
                else: # "anomalias"
                    if evento.button in [1, 7]: # B or Start
                        tocar_selecionar()
                        estado_pause = "menu"
        


        # Joystick axes motion check (for D-Pad or Left Stick)
        if joystick and agora - last_joy_move > 180:
            hats = joystick.get_numhats()
            hat_moved = False
            if hats > 0:
                dx, dy = joystick.get_hat(0)
                if dy > 0.5:
                    if estado_pause == "menu":
                        selecionado = (selecionado - 1) % len(opcoes_pause)
                        tocar_hover()
                    last_joy_move = agora
                    hat_moved = True
                elif dy < -0.5:
                    if estado_pause == "menu":
                        selecionado = (selecionado + 1) % len(opcoes_pause)
                        tocar_hover()
                    last_joy_move = agora
                    hat_moved = True
                elif dx > 0.5:
                    if estado_pause == "anomalias" and len(cartas_adquiridas) > 0:
                        selecionado_card_idx = (selecionado_card_idx + 1) % len(cartas_adquiridas)
                        tocar_hover()
                    last_joy_move = agora
                    hat_moved = True
                elif dx < -0.5:
                    if estado_pause == "anomalias" and len(cartas_adquiridas) > 0:
                        selecionado_card_idx = (selecionado_card_idx - 1) % len(cartas_adquiridas)
                        tocar_hover()
                    last_joy_move = agora
                    hat_moved = True
                    
            if not hat_moved:
                eixo_y = joystick.get_axis(1)
                eixo_x = joystick.get_axis(0)
                if eixo_y < -0.5:
                    if estado_pause == "menu":
                        selecionado = (selecionado - 1) % len(opcoes_pause)
                        tocar_hover()
                    last_joy_move = agora
                elif eixo_y > 0.5:
                    if estado_pause == "menu":
                        selecionado = (selecionado + 1) % len(opcoes_pause)
                        tocar_hover()
                    last_joy_move = agora
                elif eixo_x > 0.5:
                    if estado_pause == "anomalias" and len(cartas_adquiridas) > 0:
                        selecionado_card_idx = (selecionado_card_idx + 1) % len(cartas_adquiridas)
                        tocar_hover()
                    last_joy_move = agora
                elif eixo_x < -0.5:
                    if estado_pause == "anomalias" and len(cartas_adquiridas) > 0:
                        selecionado_card_idx = (selecionado_card_idx - 1) % len(cartas_adquiridas)
                        tocar_hover()
                    last_joy_move = agora

        # Blit original gameplay background copy
        tela.blit(fundo_pausa, (0, 0))

        # Dark overlay
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((8, 5, 15, 200))
        
        # Cyber Grid lines drawn on overlay (with alpha)
        for y in range(0, altura_tela, 8):
            pygame.draw.line(overlay, (0, 255, 204, 10), (0, y), (largura_tela, y))
            
        tela.blit(overlay, (0, 0))

        txt_pausa = fonte_titulo_large.render("JOGO PAUSADO", True, (0, 255, 204))
        tela.blit(txt_pausa, (largura_tela // 2 - txt_pausa.get_width() // 2, 40))

        if estado_pause == "menu":
            menu_panel = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
            menu_panel.fill((15, 12, 30, 160))
            pygame.draw.rect(menu_panel, (0, 255, 204, 150), (0, 0, CARD_W, CARD_H), width=2, border_radius=12)
            tela.blit(menu_panel, (CARD_X, CARD_Y))
            
            for i, opcao in enumerate(opcoes_pause):
                y_pos = CARD_Y + 24 + i * 48
                is_sel = (i == selecionado)
                
                if is_sel:
                    sel_surf = pygame.Surface((CARD_W - 30, 40), pygame.SRCALPHA)
                    sel_surf.fill((0, 255, 204, 45))
                    pygame.draw.rect(sel_surf, (0, 255, 230), (0, 0, CARD_W - 30, 40), width=1, border_radius=6)
                    tela.blit(sel_surf, (CARD_X + 15, y_pos - 6))
                    
                cor_opcao = (255, 255, 255) if is_sel else (195, 195, 205)
                txt_op = fonte_opcao_tela.render(opcao, True, cor_opcao)
                tela.blit(txt_op, (CARD_X + 30, y_pos))
                
            desc_w = largura_tela - CARD_W - CARD_X - 140
            desc_h = CARD_H
            desc_x = CARD_X + CARD_W + 50
            desc_y = CARD_Y
            
            desc_panel = pygame.Surface((desc_w, desc_h), pygame.SRCALPHA)
            desc_panel.fill((10, 8, 20, 200))
            pygame.draw.rect(desc_panel, (180, 100, 255, 100), (0, 0, desc_w, desc_h), width=1, border_radius=12)
            tela.blit(desc_panel, (desc_x, desc_y))
            
            txt_detalhes_titulo = fontes["titulo"](32).render("DETALHES DA OPCAO", True, (180, 100, 255))
            tela.blit(txt_detalhes_titulo, (desc_x + 30, desc_y + 30))
            
            pygame.draw.line(tela, (180, 100, 255, 80), (desc_x + 30, desc_y + 65), (desc_x + desc_w - 30, desc_y + 65), 1)
            
            opcao_atual = opcoes_pause[selecionado]
            desc_str = descricoes_pause[opcao_atual]
            
            linhas_desc = wrap_text(desc_str, fontes["texto"](22), desc_w - 60)
            for l_idx, linha in enumerate(linhas_desc):
                desc_render = fontes["texto"](22).render(linha, True, (220, 220, 240))
                tela.blit(desc_render, (desc_x + 30, desc_y + 90 + l_idx * 26))

        else: # "anomalias"
            current_offset += (selecionado_card_idx - current_offset) * 0.15
            cy = altura_tela // 2.5
            
            if len(cartas_adquiridas) == 0:
                txt_vazio = fontes["titulo"](32).render("NENHUMA ANOMALIA ADQUIRIDA", True, (200, 200, 200))
                txt_vazio_desc = fonte_desc.render("Derrote inimigos e colete moedas para alterar sua linha temporal.", True, (150, 150, 150))
                painel_w = 600
                painel_h = 160
                px = largura_tela // 2 - painel_w // 2
                py = altura_tela // 2 - painel_h // 2
                
                pygame.draw.rect(tela, (15, 15, 25, 200), (px, py, painel_w, painel_h), border_radius=12)
                pygame.draw.rect(tela, (0, 255, 200, 100), (px, py, painel_w, painel_h), 2, border_radius=12)
                
                tela.blit(txt_vazio, (largura_tela // 2 - txt_vazio.get_width() // 2, py + 40))
                tela.blit(txt_vazio_desc, (largura_tela // 2 - txt_vazio_desc.get_width() // 2, py + 90))
            else:
                cx_tela = largura_tela // 2
                spacing = 220
                base_largura = 150
                base_altura = 200
                
                cartas_ordenadas = []
                for idx, c in enumerate(cartas_adquiridas):
                    dist = abs(idx - current_offset)
                    cartas_ordenadas.append((dist, idx, c))
                cartas_ordenadas.sort(key=lambda x: x[0], reverse=True)

                for dist, idx, c in cartas_ordenadas:
                    rel_idx = idx - current_offset
                    card_cx = cx_tela + rel_idx * spacing
                    card_cy = cy
                    
                    scale_factor = max(0.65, 1.25 - dist * 0.45)
                    opacity = max(40, int(255 - dist * 160))
                    w = int(base_largura * scale_factor)
                    h = int(base_altura * scale_factor)
                    
                    scaled_img = pygame.transform.scale(c["imagem"], (w, h))
                    
                    if idx == selecionado_card_idx:
                        glow_size = int(12 + pulsar * 8)
                        glow_surf = pygame.Surface((w + glow_size * 2, h + glow_size * 2), pygame.SRCALPHA)
                        glow_cor = (0, 255, 200, int(80 + pulsar * 80))
                        pygame.draw.rect(glow_surf, glow_cor, (0, 0, w + glow_size * 2, h + glow_size * 2), border_radius=18)
                        tela.blit(glow_surf, (card_cx - w//2 - glow_size, card_cy - h//2 - glow_size))
                    
                    temp_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                    temp_surf.blit(scaled_img, (0, 0))
                    temp_surf.set_alpha(opacity)
                    tela.blit(temp_surf, (card_cx - w//2, card_cy - h//2))
                    
                    qtd_txt = fontes["titulo"](32).render(f"x{c['quantidade']}", True, (0, 255, 200) if idx == selecionado_card_idx else (255, 255, 255))
                    qtd_surf = pygame.Surface((qtd_txt.get_width() + 16, qtd_txt.get_height() + 8), pygame.SRCALPHA)
                    pygame.draw.rect(qtd_surf, (10, 10, 20, 220), (0, 0, qtd_surf.get_width(), qtd_surf.get_height()), border_radius=6)
                    pygame.draw.rect(qtd_surf, (0, 255, 200) if idx == selecionado_card_idx else (100, 100, 100), (0, 0, qtd_surf.get_width(), qtd_surf.get_height()), 2, border_radius=6)
                    qtd_surf.blit(qtd_txt, (8, 4))
                    tela.blit(qtd_surf, (card_cx + w//2 - qtd_surf.get_width()//2, card_cy - h//2 - qtd_surf.get_height()//2))

                c_ativa = cartas_adquiridas[selecionado_card_idx]
                panel_w = 700
                panel_h = 160
                panel_x = largura_tela // 2 - panel_w // 2
                panel_y = altura_tela - 240
                
                pygame.draw.rect(tela, (15, 15, 22, 220), (panel_x, panel_y, panel_w, panel_h), border_radius=16)
                pygame.draw.rect(tela, (0, 255, 200, 180), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=16)
                
                txt_nome = fontes["titulo"](32).render(c_ativa["nome"].upper(), True, (255, 255, 255))
                txt_nick = fontes["texto"](26).render(f"\"{c_ativa['Nick']}\"", True, (200, 200, 100))
                txt_qtd = fontes["texto"](26).render(f"Quantidade: {c_ativa['quantidade']}", True, (0, 255, 200))
                
                tela.blit(txt_nome, (panel_x + 30, panel_y + 20))
                tela.blit(txt_nick, (panel_x + 30 + txt_nome.get_width() + 15, panel_y + 26))
                tela.blit(txt_qtd, (panel_x + panel_w - txt_qtd.get_width() - 30, panel_y + 20))
                
                pygame.draw.line(tela, (0, 255, 200, 80), (panel_x + 30, panel_y + 60), (panel_x + panel_w - 30, panel_y + 60), 2)
                
                linhas_desc = wrap_text(c_ativa["descricao"], fonte_desc, panel_w - 60)
                for l_idx, linha in enumerate(linhas_desc):
                    desc_render = fonte_desc.render(linha, True, (200, 200, 200))
                    tela.blit(desc_render, (panel_x + 30, panel_y + 75 + l_idx * 22))

            # Back button for carousel
            back_rect = pygame.Rect(largura_tela // 2 - 100, altura_tela - 65, 200, 36)
            is_hover_back = back_rect.collidepoint(mx, my)
            pygame.draw.rect(tela, (0, 180, 200, 75) if is_hover_back else (15, 12, 35, 230), back_rect, border_radius=6)
            pygame.draw.rect(tela, (0, 255, 230) if is_hover_back else (180, 100, 255), back_rect, width=1, border_radius=6)
            txt_back = fontes["texto"](22).render("VOLTAR AO MENU", True, (255, 255, 255) if is_hover_back else (200, 200, 200))
            tela.blit(txt_back, (back_rect.centerx - txt_back.get_width()//2, back_rect.centery - txt_back.get_height()//2))

        pygame.display.flip()
        clock.tick(60)

    return "continuar"
