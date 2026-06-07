import Caminhos
import pygame
import sys
import math
import os
import json
from sons_procedurais import tocar_hover, tocar_selecionar
import ui_helpers


def _obter_pos_mouse_pause():
    return ui_helpers.obter_pos_mouse_superficie()

# Atributos e descricoes para todas as cartas
atributos_todas_cartas = {
    "Speed Boost": {
        "Nick": "Vento Celeste",
        "descricao": "Aumente sua velocidade em +10%. Corra como o vento e fuja de qualquer situacao perigosa.",
        "imagem_path": "Sprites/Deck/Speed_boost1.png"
    },
    "Porção": {
        "Nick": "Elixir Vital",
        "descricao": "Recupere 25% da sua vida maxima e ganhe mais vida maxima permanentemente.",
        "imagem_path": "Sprites/Deck/carta_por1.png"
    },
    "Disparo crescente": {
        "Nick": "Impacto Escalante",
        "descricao": "Ganhe +27 de dano e deixe os inimigos temendo seus tiros poderosos.",
        "imagem_path": "Sprites/Deck/carta_odio1.png"
    },
    "Tempestade": {
        "Nick": "Tempestade Crescente",
        "descricao": "Aumente sua chance critica em 2% e triplique o dano causado. Transforme cada acerto em uma tempestade!",
        "imagem_path": "Sprites/Deck/Carta_tempestade_crescente1.png"
    },
    "Cura": {
        "Nick": "Mordida Sombria",
        "descricao": "Restaure 3% da sua vida a cada hit e 4% a cada ativacao. Recupere sua saude enquanto luta!",
        "imagem_path": "Sprites/Deck/Carta_roubo_vida1.png"
    },
    "Trembo": {
        "Nick": "Reversao Temporal",
        "descricao": "Quando a morte se aproxima, o tempo volta. Recupere toda a sua saude e reapareca em outro local!",
        "imagem_path": "Sprites/Deck/carta_trem1.png"
    },
    "Speed Atack": {
        "Nick": "Fluidez Letal",
        "descricao": "Aumente a velocidade de ataque em 5%, tornando seus tiros rapidos e letais.",
        "imagem_path": "Sprites/Deck/carta_onda.png"
    },
    "Teleporte": {
        "Nick": "Salto Espacial",
        "descricao": "Reduza o cooldown do teleporte em 3%, permitindo que voce se mova rapidamente entre os campos de batalha.",
        "imagem_path": "Sprites/Deck/carta_teleporte1.png"
    },
    "Petro": {
        "Nick": "Sentinela Leal",
        "descricao": "Desencadeie o poder de um pequeno guardiao. Alimente-o para ver seu poder crescer e proteger voce!",
        "imagem_path": "Sprites/Deck/carta_petro1.png"
    },
    "Defesa": {
        "Nick": "Escudo Fasico",
        "descricao": "Aumente sua resistencia em +5 e mitigue os danos dos inimigos.",
        "imagem_path": "Sprites/Deck/carta_defesa1.png"
    },
    "Sorte": {
        "Nick": "Anomalia Favoravel",
        "descricao": "Aumente suas chances de obter cartas raras com 0.6% de sorte adicional.",
        "imagem_path": "Sprites/Deck/carta_sorte1.png"
    },
    "Poison": {
        "Nick": "Toxina Temporal",
        "descricao": "Infunde seus ataques com veneno, causando dano continuo ao longo do tempo aos inimigos atingidos.",
        "imagem_path": "Sprites/Deck/carta_poison1.png"
    },
    "Coletora": {
        "Nick": "Foice do Tempo",
        "descricao": "Coleta a energia vital de inimigos enfraquecidos, executando-os instantaneamente quando sua vida esta baixa.",
        "imagem_path": "Sprites/Deck/carta_estalo1.png"
    },
    "Mercenaria": {
        "Nick": "Contrato de Guerra",
        "descricao": "Ativa a contagem de combo de pontos. Abates consecutivos aumentam o bonus de pontuacao.",
        "imagem_path": "Sprites/Deck/carta_mercenaria1.png"
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

def _snapshot_config(config):
    return json.dumps(config, sort_keys=True, ensure_ascii=False)

def _tem_alteracoes_pendentes(config, config_salva):
    return _snapshot_config(config) != _snapshot_config(config_salva)

def _desenhar_painel_legibilidade(tela, rect, alpha=224, borda_alpha=95):
    painel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(painel, (3, 6, 18, alpha), painel.get_rect(), border_radius=10)
    pygame.draw.rect(painel, (0, 255, 230, borda_alpha), painel.get_rect(), width=1, border_radius=10)
    brilho = pygame.Rect(4, 4, max(0, rect.width - 8), max(0, rect.height - 8))
    if brilho.width > 0 and brilho.height > 0:
        pygame.draw.rect(painel, (20, 90, 120, 45), brilho, width=1, border_radius=8)
    tela.blit(painel, rect.topleft)

def _retornar_pause(acao, tela=None):
    pygame.mouse.set_visible(False)
    if tela is not None:
        return {"acao": acao, "tela": tela}
    return acao

def _confirmar_saida_alteracoes_pause(tela, fontes):
    largura_tela, altura_tela = tela.get_size()
    fonte_titulo = fontes["titulo"](34)
    fonte_texto = fontes["texto"](24)
    opcoes = [("Salvar e sair", "salvar"), ("Sair sem salvar", "descartar"), ("Cancelar", "cancelar")]
    selecionado = 0
    clock = pygame.time.Clock()

    while True:
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        tela.blit(overlay, (0, 0))

        caixa = pygame.Rect(largura_tela // 2 - 320, altura_tela // 2 - 130, 640, 260)
        pygame.draw.rect(tela, (12, 10, 24), caixa, border_radius=10)
        pygame.draw.rect(tela, (0, 255, 204), caixa, 2, border_radius=10)

        titulo = fonte_titulo.render("ALTERACOES NAO SALVAS", True, (255, 230, 120))
        tela.blit(titulo, titulo.get_rect(center=(caixa.centerx, caixa.y + 48)))
        msg = fonte_texto.render("Salvar alteracoes antes de sair?", True, (220, 220, 230))
        tela.blit(msg, msg.get_rect(center=(caixa.centerx, caixa.y + 90)))

        mx, my = _obter_pos_mouse_pause()
        for i, (label, _) in enumerate(opcoes):
            rect = pygame.Rect(caixa.x + 95, caixa.y + 120 + i * 42, caixa.w - 190, 34)
            if rect.collidepoint(mx, my):
                selecionado = i
            pygame.draw.rect(tela, (0, 180, 200, 55) if i == selecionado else (20, 18, 32), rect, border_radius=6)
            pygame.draw.rect(tela, (0, 255, 204) if i == selecionado else (90, 100, 120), rect, 1, border_radius=6)
            txt = fonte_texto.render(label, True, (255, 255, 255) if i == selecionado else (180, 185, 200))
            tela.blit(txt, txt.get_rect(center=rect.center))

        pygame.display.flip()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado = (selecionado - 1) % len(opcoes)
                    tocar_hover()
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado = (selecionado + 1) % len(opcoes)
                    tocar_hover()
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    return opcoes[selecionado][1]
                elif evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    return "cancelar"
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                for i, (_, acao) in enumerate(opcoes):
                    rect = pygame.Rect(caixa.x + 95, caixa.y + 120 + i * 42, caixa.w - 190, 34)
                    if rect.collidepoint(mx, my):
                        tocar_selecionar()
                        return acao

        clock.tick(60)
def abrir_configuracoes_graficas(tela, fontes, fundo_pausa=None):
    try:
        with open("saves/config_graficos.json", "r") as f:
            config = json.load(f)
    except:
        config = {
            "sombras_ativas": "dinamicas",
            "qualidade_grafica": "alta",
            "nivel_detalhes": "alto",
            "particulas_ativas": True,
            "efeitos_visuais": True,
            "efeitos_manifestacoes": "alto",
            "fps_limite": 60,
            "tela_cheia": False
        }
    config.setdefault("fps_limite", 60)
    config.setdefault("nivel_detalhes", "alto")
    config.setdefault("particulas_ativas", True)
    config.setdefault("efeitos_visuais", True)
    config.setdefault("efeitos_manifestacoes", "alto")
    config.setdefault("tela_cheia", False)
    config.setdefault("sangue_lacerante", "alto")
    
    config_salva = json.loads(json.dumps(config))
    
    opcoes_config = [
        {"nome": "Sombras", "chave": "sombras_ativas", "valores": ["desativadas", "simples", "dinamicas"], "labels": ["Desativadas", "Simples", "Dinamicas"]},
        {"nome": "Qualidade Grafica", "chave": "qualidade_grafica", "valores": ["alta", "media", "baixa"], "labels": ["Alta", "Media", "Baixa"]},
        {"nome": "Detalhes dos Efeitos", "chave": "nivel_detalhes", "valores": ["alto", "medio", "baixo"], "labels": ["Alto", "Medio", "Baixo"]},
        {"nome": "Particulas", "chave": "particulas_ativas", "valores": [True, False], "labels": ["Ativadas", "Desativadas"]},
        {"nome": "Efeitos Visuais", "chave": "efeitos_visuais", "valores": [True, False], "labels": ["Ativados", "Desativados"]},
        {"nome": "Efeitos Manifestacoes", "chave": "efeitos_manifestacoes", "valores": ["alto", "medio", "baixo", "desativado"], "labels": ["Alto", "Medio", "Baixo", "Desativado"]},
        {"nome": "Limite de FPS", "chave": "fps_limite", "valores": [30, 60, 120, 0], "labels": ["30 FPS", "60 FPS", "120 FPS", "Ilimitado"]},
        {"nome": "Tela Cheia", "chave": "tela_cheia", "valores": [False, True], "labels": ["Janela", "Tela Cheia"]},
        {"nome": "Sangue Lacerante", "chave": "sangue_lacerante", "valores": ["alto", "reduzido", "desativado"], "labels": ["Completo", "Reduzido", "Desativado"]},
        {"nome": "Aplicar Alteracoes", "chave": "aplicar", "valores": None, "labels": None},
        {"nome": "Voltar", "chave": None, "valores": None, "labels": None}
    ]
    
    descricoes_valores = {
        "sombras_ativas": {
            "desativadas": "Desliga sombras. Melhora muito o desempenho em PCs fracos.",
            "simples": "Sombras basicas estaticas. Bom equilibrio de performance.",
            "dinamicas": "Sombras realistas em tempo real. Exige mais da placa de video."
        },
        "qualidade_grafica": {
            "alta": "Texturas e renderizacao maxima. Para placas de video modernas.",
            "media": "Qualidade padrao equilibrada para a maioria dos computadores.",
            "baixa": "Reduz resolucao de efeitos para rodar liso em qualquer maquina."
        },
        "nivel_detalhes": {
            "alto": "Mais fragmentos, brilho e solidificacao detalhada na HUD.",
            "medio": "Equilibrio entre efeitos visuais e desempenho.",
            "baixo": "Efeitos essenciais com menos particulas e brilho."
        },
        "particulas_ativas": {
            True: "Particulas visuais de explosoes e faiscas ligadas.",
            False: "Remove particulas para maior clareza visual e desempenho."
        },
        "efeitos_visuais": {
            True: "Ativa brilhos, distorcoes de tempo e glows premium.",
            False: "Desativa pos-processamento pesado para evitar lentidao."
        },
        "efeitos_manifestacoes": {
            "alto": "Mostra efeitos completos de manifestacoes, como marcas, vinhas e parasitas.",
            "medio": "Reduz quantidade de vinhas, marcas e particulas das manifestacoes.",
            "baixo": "Mantem leitura essencial com poucos efeitos ao redor de inimigos e projeteis.",
            "desativado": "Remove efeitos extras das manifestacoes sem desligar toda a interface."
        },
        "fps_limite": {
            30: "Limita a 30 FPS. Reduz consumo de energia e aquecimento.",
            60: "Padrao recomendado para jogabilidade fluida e estavel.",
            120: "Para monitores de alta taxa de atualizacao (120Hz ou mais).",
            0: "Ilimitado. Roda o mais rapido possivel (uso maximo de hardware)."
        },
        "tela_cheia": {
            False: "Modo Janela: Executa o jogo em uma janela redimensionavel.",
            True: "Modo Tela Cheia: Ocupa toda a tela do monitor para maior imersao."
        },
        "sangue_lacerante": {
            "alto": "Efeito de sangue completo na passiva Lacerante. Maxima fidelidade.",
            "reduzido": "Efeito de sangue simplificado para economizar desempenho.",
            "desativado": "Remove as gotas e o rastro de sangue da passiva Lacerante."
        }
    }
    
    largura_tela, altura_tela = tela.get_size()
    selecionado = 0
    modo_interacao = "teclado"
    clock = pygame.time.Clock()
    
    fonte_titulo_tela = fontes["titulo"](48)
    fonte_opcao_tela = fontes["texto"](26)
    fonte_valor_tela = fontes["texto"](22)
    fonte_instrucao = fontes["texto"](20)
    
    def aplicar_config():
        nonlocal config_salva, tela, fundo_pausa
        with open("saves/config_graficos.json", "w") as f:
            json.dump(config, f, indent=4)
        from utils import configurar_tela
        tela = configurar_tela(largura_tela, altura_tela)
        config_salva = json.loads(json.dumps(config))
        if fundo_pausa:
            fundo_pausa = pygame.transform.scale(fundo_pausa, (largura_tela, altura_tela))

    def tentar_sair():
        if not _tem_alteracoes_pendentes(config, config_salva):
            return True
        acao = _confirmar_saida_alteracoes_pause(tela, fontes)
        if acao == "salvar":
            aplicar_config()
            return True
        if acao == "descartar":
            return True
        return False
        
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
        _desenhar_painel_legibilidade(tela, ret_tit.inflate(70, 28), alpha=210, borda_alpha=85)
        tela.blit(texto_titulo, ret_tit)
        
        mx, my = _obter_pos_mouse_pause()
        clicado = False
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.MOUSEMOTION:
                if evento.rel != (0, 0):
                    modo_interacao = "mouse"
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    modo_interacao = "mouse"
                    clicado = True
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado = (selecionado - 1) % len(opcoes_config)
                    tocar_hover()
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado = (selecionado + 1) % len(opcoes_config)
                    tocar_hover()
                elif evento.key in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d]:
                    if opcoes_config[selecionado]["chave"] and opcoes_config[selecionado]["chave"] != "aplicar":
                        tocar_hover()
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
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    if opcoes_config[selecionado]["chave"] == "aplicar":
                        aplicar_config()
                    elif opcoes_config[selecionado]["nome"] == "Voltar" and tentar_sair():
                        rodando = False
                elif evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    if tentar_sair():
                        rodando = False
                        
        y_inicial = altura_tela // 4 + 10
        espacamento = 44
        desc_y = min(altura_tela - 145, y_inicial + len(opcoes_config) * espacamento + 12)
        lista_rect = pygame.Rect(
            largura_tela // 4 - 44,
            y_inicial - 24,
            largura_tela // 2 + 88,
            max(80, desc_y - (y_inicial - 24) - 14),
        )
        _desenhar_painel_legibilidade(tela, lista_rect, alpha=218, borda_alpha=70)
        
        # Mouse hover & click processing
        if modo_interacao == "mouse":
            for i, opcao in enumerate(opcoes_config):
                y_pos = y_inicial + i * espacamento
                rect_item = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 34)
                if rect_item.collidepoint(mx, my):
                    if selecionado != i:
                        selecionado = i
                        tocar_hover()
                    if clicado:
                        tocar_selecionar()
                        if opcao["nome"] == "Voltar" and tentar_sair():
                            rodando = False
                        elif opcao["chave"] == "aplicar":
                            aplicar_config()
                        elif opcao["chave"]:
                            chave = opcao["chave"]
                            valores = opcao["valores"]
                            valor_atual = config[chave]
                            try:
                                idx = (valores.index(valor_atual) + 1) % len(valores)
                            except:
                                idx = 0
                            config[chave] = valores[idx]
                            
        for i, opcao in enumerate(opcoes_config):
            y_pos = y_inicial + i * espacamento
            
            if i == selecionado:
                rect_bg = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 34)
                pygame.draw.rect(tela, (0, 180, 200, 65), rect_bg, border_radius=6)
                pygame.draw.rect(tela, (0, 255, 230), rect_bg, width=2, border_radius=6)
                cor_nome = (255, 255, 255)
            else:
                cor_nome = (195, 195, 205)
                
            texto_nome = fonte_opcao_tela.render(opcao["nome"], True, cor_nome)
            tela.blit(texto_nome, (largura_tela // 4, y_pos))
            
            if opcao["chave"] and opcao["chave"] != "aplicar":
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
                    
        rect_desc = pygame.Rect(largura_tela // 2 - 360, desc_y, 720, 58)
        _desenhar_painel_legibilidade(tela, rect_desc, alpha=238, borda_alpha=120)
        
        opt_sel = opcoes_config[selecionado]
        if opt_sel["chave"] is None:
            texto_desc_str = "Retornar ao menu de configuracoes anterior."
        elif opt_sel["chave"] == "aplicar":
            texto_desc_str = "Salvar e aplicar as alteracoes graficas agora."
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

    return {"tela": tela, "config_graficos": json.loads(json.dumps(config_salva))}


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
        
    config_salva = json.loads(json.dumps(config))
    
    largura_tela, altura_tela = tela.get_size()
    selecionado = 0
    modo_interacao = "teclado"
    clock = pygame.time.Clock()
    
    fonte_titulo_tela = fontes["titulo"](48)
    fonte_opcao_tela = fontes["texto"](26)
    fonte_valor_tela = fontes["texto"](22)
    fonte_instrucao = fontes["texto"](20)
    
    opcoes = ["volume_master", "volume_musica", "volume_efeitos", "aplicar", "voltar"]
    labels = ["Volume Master", "Volume Musica", "Volume Efeitos", "Aplicar Alteracoes", "Voltar"]
    
    descricoes_audio = {
        "volume_master": "Volume geral. Ajusta a musica e os efeitos sonoros proporcionalmente.",
        "volume_musica": "Trilha sonora. Ajusta o volume da musica de fundo e ambiente.",
        "volume_efeitos": "Efeitos sonoros. Ajusta o volume de tiros, explosoes e impactos.",
        "aplicar": "Salvar e aplicar as alteracoes de audio agora.",
        "voltar": "Retornar ao menu de configuracoes anterior."
    }
    
    def aplicar_config():
        nonlocal config_salva
        from audio_manager import salvar_config_audio, atualizar_sons_do_jogo
        salvar_config_audio(config)
        atualizar_sons_do_jogo(config)
        config_salva = json.loads(json.dumps(config))

    def tentar_sair():
        if not _tem_alteracoes_pendentes(config, config_salva):
            return True
        acao = _confirmar_saida_alteracoes_pause(tela, fontes)
        if acao == "salvar":
            aplicar_config()
            return True
        if acao == "descartar":
            # Restore music volume to saved config
            pygame.mixer.music.set_volume(config_salva["volume_musica"] * config_salva["volume_master"])
            return True
        return False
        
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
        _desenhar_painel_legibilidade(tela, ret_tit.inflate(70, 28), alpha=210, borda_alpha=85)
        tela.blit(texto_titulo, ret_tit)
        
        mx, my = _obter_pos_mouse_pause()
        clicado = False
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.MOUSEMOTION:
                if evento.rel != (0, 0):
                    modo_interacao = "mouse"
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    modo_interacao = "mouse"
                    clicado = True
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado = (selecionado - 1) % len(opcoes)
                    tocar_hover()
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado = (selecionado + 1) % len(opcoes)
                    tocar_hover()
                elif evento.key in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d]:
                    if opcoes[selecionado] not in ["voltar", "aplicar"]:
                        tocar_hover()
                        chave = opcoes[selecionado]
                        step = -0.1 if evento.key in [pygame.K_LEFT, pygame.K_a] else 0.1
                        config[chave] = max(0.0, min(1.0, config[chave] + step))
                        pygame.mixer.music.set_volume(config["volume_musica"] * config["volume_master"])
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    if opcoes[selecionado] == "aplicar":
                        aplicar_config()
                    elif opcoes[selecionado] == "voltar" and tentar_sair():
                        rodando = False
                elif evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    if tentar_sair():
                        rodando = False
                        
        y_inicial = altura_tela // 4 + 10
        espacamento = 50
        lista_rect = pygame.Rect(
            largura_tela // 4 - 44,
            y_inicial - 24,
            largura_tela // 2 + 88,
            (len(opcoes) - 1) * espacamento + 76,
        )
        _desenhar_painel_legibilidade(tela, lista_rect, alpha=218, borda_alpha=70)
        
        # Mouse hover & click processing
        if modo_interacao == "mouse":
            for i, opcao in enumerate(opcoes):
                y_pos = y_inicial + i * espacamento
                rect_item = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 44)
                if rect_item.collidepoint(mx, my):
                    if selecionado != i:
                        selecionado = i
                        tocar_hover()
                    if clicado:
                        if opcao == "voltar" and tentar_sair():
                            rodando = False
                        elif opcao == "aplicar":
                            tocar_selecionar()
                            aplicar_config()
                        elif opcao not in ["voltar", "aplicar"]:
                            barra_x = largura_tela // 2 - 20
                            barra_largura = 180
                            rel_x = mx - barra_x
                            if 0 <= rel_x <= barra_largura:
                                tocar_selecionar()
                                pct = rel_x / barra_largura
                                config[opcao] = round(pct, 1)
                                pygame.mixer.music.set_volume(config["volume_musica"] * config["volume_master"])
                                
        for i, opcao in enumerate(opcoes):
            y_pos = y_inicial + i * espacamento
            
            if i == selecionado:
                rect_bg = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 44)
                pygame.draw.rect(tela, (0, 180, 200, 65), rect_bg, border_radius=6)
                pygame.draw.rect(tela, (0, 255, 230), rect_bg, width=2, border_radius=6)
                cor_nome = (255, 255, 255)
            else:
                cor_nome = (195, 195, 205)
                
            texto_nome = fonte_opcao_tela.render(labels[i], True, cor_nome)
            tela.blit(texto_nome, (largura_tela // 4, y_pos))
            
            if opcao not in ["voltar", "aplicar"]:
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
                    
        rect_desc = pygame.Rect(largura_tela // 2 - 360, 485, 720, 58)
        _desenhar_painel_legibilidade(tela, rect_desc, alpha=238, borda_alpha=120)
        
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


def abrir_configuracoes_jogabilidade(tela, fontes, fundo_pausa=None):
    try:
        with open("saves/tutorial_config.json", "r") as f:
            mostrar_tut = json.load(f).get("mostrar_tutorial", True)
    except:
        mostrar_tut = True
        
    try:
        with open("saves/config_teleporte.json", "r") as f:
            modo_teleporte = json.load(f).get("modo", "fixo")
    except:
        modo_teleporte = "fixo"

    try:
        import Variaveis
        loja_forcada = Variaveis.loja_forcada_ativa(forcar_recarregar=True)
    except:
        loja_forcada = True

    config = {
        "mostrar_tutorial": mostrar_tut,
        "modo_teleporte": modo_teleporte,
        "loja_forcada": loja_forcada
    }
    
    config_salva = json.loads(json.dumps(config))
    
    opcoes_config = [
        {"nome": "Tutorial", "chave": "mostrar_tutorial", "valores": [True, False], "labels": ["Ativado", "Desativado"]},
        {"nome": "Modo de Teleporte", "chave": "modo_teleporte", "valores": ["fixo", "mouse"], "labels": ["Fixo", "Mouse Target"]},
        {"nome": "Loja Forcada", "chave": "loja_forcada", "valores": [True, False], "labels": ["Ativada", "Desativada"]},
        {"nome": "Aplicar Alteracoes", "chave": "aplicar", "valores": None, "labels": None},
        {"nome": "Voltar", "chave": None, "valores": None, "labels": None}
    ]
    
    descricoes_valores = {
        "mostrar_tutorial": {
            True: "Exibe baloes explicativos e dicas ao longo das fases para iniciantes.",
            False: "Desativa tutoriais de jogabilidade. Recomendado para jogadores experientes."
        },
        "modo_teleporte": {
            "fixo": "Modo Fixo: Teleporta na direcao do movimento. Rapido e instantaneo.",
            "mouse": "Modo Mouse: Segure a tecla para mirar na posicao do cursor e solte para teleportar."
        },
        "loja_forcada": {
            True: "A loja abre sozinha apos aviso quando voce acumula pontos para 5 cartas.",
            False: "A loja nunca abre sozinha; voce decide quando gastar seus pontos."
        }
    }
    
    largura_tela, altura_tela = tela.get_size()
    selecionado = 0
    modo_interacao = "teclado"
    clock = pygame.time.Clock()
    
    fonte_titulo_tela = fontes["titulo"](48)
    fonte_opcao_tela = fontes["texto"](26)
    fonte_valor_tela = fontes["texto"](22)
    fonte_instrucao = fontes["texto"](20)

    def aplicar_config():
        nonlocal config_salva
        with open("saves/tutorial_config.json", "w") as f:
            json.dump({"mostrar_tutorial": config["mostrar_tutorial"]}, f)
        with open("saves/config_teleporte.json", "w") as f:
            json.dump({"modo": config["modo_teleporte"]}, f)
        try:
            import Variaveis
            Variaveis.salvar_config_jogabilidade({"loja_forcada": config["loja_forcada"]})
            Variaveis.obter_modo_teleporte(forcar_recarregar=True)
        except:
            pass
        config_salva = json.loads(json.dumps(config))

    def tentar_sair():
        if not _tem_alteracoes_pendentes(config, config_salva):
            return True
        acao = _confirmar_saida_alteracoes_pause(tela, fontes)
        if acao == "salvar":
            aplicar_config()
            return True
        if acao == "descartar":
            return True
        return False
        
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
         
        texto_titulo = fonte_titulo_tela.render("CONFIGURACOES DE JOGABILIDADE", True, (0, 255, 204))
        ret_tit = texto_titulo.get_rect(center=(largura_tela // 2, altura_tela // 8))
        _desenhar_painel_legibilidade(tela, ret_tit.inflate(70, 28), alpha=210, borda_alpha=85)
        tela.blit(texto_titulo, ret_tit)
        
        mx, my = _obter_pos_mouse_pause()
        clicado = False
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.MOUSEMOTION:
                if evento.rel != (0, 0):
                    modo_interacao = "mouse"
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    modo_interacao = "mouse"
                    clicado = True
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado = (selecionado - 1) % len(opcoes_config)
                    tocar_hover()
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado = (selecionado + 1) % len(opcoes_config)
                    tocar_hover()
                elif evento.key in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d]:
                    opt = opcoes_config[selecionado]
                    if opt["chave"] and opt["chave"] != "aplicar":
                        tocar_hover()
                        chave = opt["chave"]
                        valores = opt["valores"]
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
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    opt = opcoes_config[selecionado]
                    if opt["nome"] == "Voltar" and tentar_sair():
                        rodando = False
                    elif opt["nome"] == "Aplicar Alteracoes":
                        aplicar_config()
                    elif opt["chave"] and opt["chave"] != "aplicar":
                        chave = opt["chave"]
                        valores = opt["valores"]
                        valor_atual = config[chave]
                        try:
                            idx = (valores.index(valor_atual) + 1) % len(valores)
                        except:
                            idx = 0
                        config[chave] = valores[idx]
                elif evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    if tentar_sair():
                        rodando = False
                        
        y_inicial = altura_tela // 4 + 20
        espacamento = 45
        desc_y = min(altura_tela - 145, y_inicial + len(opcoes_config) * espacamento + 12)
        lista_rect = pygame.Rect(
            largura_tela // 4 - 44,
            y_inicial - 24,
            largura_tela // 2 + 88,
            max(80, desc_y - (y_inicial - 24) - 14),
        )
        _desenhar_painel_legibilidade(tela, lista_rect, alpha=218, borda_alpha=70)
        
        # Mouse interaction check
        if modo_interacao == "mouse":
            for i, opcao in enumerate(opcoes_config):
                y_pos = y_inicial + i * espacamento
                rect_item = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 38)
                if rect_item.collidepoint(mx, my):
                    if selecionado != i:
                        selecionado = i
                        tocar_hover()
                    if clicado:
                        tocar_selecionar()
                        if opcao["nome"] == "Voltar" and tentar_sair():
                            rodando = False
                        elif opcao["nome"] == "Aplicar Alteracoes":
                            aplicar_config()
                        elif opcao["chave"] and opcao["chave"] != "aplicar":
                            chave = opcao["chave"]
                            valores = opcao["valores"]
                            valor_atual = config[chave]
                            try:
                                idx = (valores.index(valor_atual) + 1) % len(valores)
                            except:
                                idx = 0
                            config[chave] = valores[idx]
                            
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
            
            if opcao["chave"] and opcao["chave"] != "aplicar":
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
                    
        rect_desc = pygame.Rect(largura_tela // 2 - 360, desc_y, 720, 70)
        _desenhar_painel_legibilidade(tela, rect_desc, alpha=238, borda_alpha=120)
        
        opt_sel = opcoes_config[selecionado]
        aviso_str = ""
        if opt_sel["chave"] is None:
            texto_desc_str = "Retornar ao menu de configuracoes anterior."
        elif opt_sel["chave"] == "aplicar":
            texto_desc_str = "Salvar e aplicar as alteracoes de jogabilidade agora."
        else:
            val_sel = config[opt_sel["chave"]]
            texto_desc_str = descricoes_valores[opt_sel["chave"]].get(val_sel, "")
            if opt_sel["chave"] == "mostrar_tutorial":
                aviso_str = "AVISO: Esta alteracao so sera aplicada na proxima run/fase."
            else:
                aviso_str = "Aplicado imediatamente."
                
        surf_desc_texto = fonte_valor_tela.render(texto_desc_str, True, (200, 200, 220))
        rect_desc_texto = surf_desc_texto.get_rect(centerx=rect_desc.centerx, y=rect_desc.y + 12)
        tela.blit(surf_desc_texto, rect_desc_texto)
        
        if aviso_str:
            cor_aviso = (255, 100, 100) if "proxima run" in aviso_str else (0, 255, 150)
            aviso_render = fonte_valor_tela.render(aviso_str, True, cor_aviso)
            rect_aviso_texto = aviso_render.get_rect(centerx=rect_desc.centerx, y=rect_desc.y + 38)
            tela.blit(aviso_render, rect_aviso_texto)
            
        instrucao_txt = "W/S: Navegar | A/D: Alterar | ENTER/ESC: Voltar"
        texto_inst = fonte_instrucao.render(instrucao_txt, True, (150, 150, 150))
        tela.blit(texto_inst, (largura_tela // 2 - texto_inst.get_width() // 2, altura_tela - 50))
        
        pygame.display.flip()
        clock.tick(60)

    return {"tela": tela}


def abrir_analise_atributos(tela, fontes, fundo_pausa=None):
    """
    Exibe a tela de Analise de Atributos do jogador, mostrando
    dados estatisticos detalhados com legibilidade maxima (fundos escuros, sombras).
    """
    try:
        with open("saves/atributos.json", "r") as f:
            attrs = json.load(f)
    except:
        attrs = {}

    largura_tela, altura_tela = tela.get_size()
    clock = pygame.time.Clock()
    
    fonte_titulo_tela = fontes["titulo"](44)
    fonte_secao = fontes["titulo"](24)
    fonte_label = fontes["texto"](22)
    fonte_valor = fontes["texto"](22)
    fonte_instrucao = fontes["texto"](20)
    
    # Valores extraidos com fallbacks seguros
    vida_atual = attrs.get("vida_atual_personagem", 100)
    vida_max = attrs.get("vida_maxima_personagem", 100)
    dano_base = attrs.get("dano_person_hit", 1.0)
    vel_ataque_ms = attrs.get("intervalo_disparo", 300)
    chance_crit = attrs.get("chance_critico", 0.02)
    roubo_vida = attrs.get("roubo_de_vida", 0.0)
    sorte = attrs.get("Chance_Sorte", 0.01)
    resistencia = attrs.get("resistencia_personagem", 0)
    dash_cd = attrs.get("tempo_cooldown_dash", 3500)
    moedas = attrs.get("moedas_totais", 0)
    poison = attrs.get("Poison_Active", False)
    executa = attrs.get("Executa_inimigo", False)
    mercenaria = attrs.get("Mercenaria_Active", False)
    
    petro_ativo = attrs.get("existencia_petro", False)
    petro_nivel = attrs.get("nivel_Petro", 1)
    petro_dano = attrs.get("dano_petro", 10)
    petro_res = attrs.get("resistencia_petro", 0)
    
    # Organizacao das colunas
    col_ofensiva = [
        ("Dano do Disparo", f"{dano_base:.2f}"),
        ("Intervalo de Tiro", f"{vel_ataque_ms} ms"),
        ("Chance Critica", f"{chance_crit * 100:.2f}%"),
        ("Multiplicador Critico", "3.00x (300%)"),
        ("Roubo de Vida", f"{attrs.get('quantidade_roubo_vida', 0.0) * 100:.2f}% perd." if attrs.get('quantidade_roubo_vida', 0.0) > 0 else "Inativo"),
        ("Ataque Venenoso", "Ativo" if poison else "Inativo"),
        ("Foice do Tempo (Executar)", "Ativo" if executa else "Inativo")
    ]
    
    col_defensiva = [
        ("Vida do Jogador", f"{int(vida_atual)} / {int(vida_max)}"),
        ("Resistencia Corporal", f"+{resistencia}"),
        ("Tempo Recarga Dash", f"{dash_cd / 1000:.2f}s"),
        ("Sorte (Drop Raro)", f"{sorte * 100:.2f}%"),
        ("Ganho Mercenaria", "Ativo (+Bonus)" if mercenaria else "Inativo"),
        ("Tempo de Regeneracao", f"{attrs.get('Tempo_cura', 2500)/1000:.2f}s"),
        ("Taxa de Regeneracao", f"{attrs.get('porcentagem_cura', 0.02) * 100:.2f}%")
    ]
    
    col_petro = [
        ("Petro (Sentinela)", "Ativo" if petro_ativo else "Inativo"),
        ("Nivel de Petro", f"Niv. {petro_nivel}"),
        ("Dano Petro", f"{float(petro_dano):.2f}" if isinstance(petro_dano, (int, float)) else str(petro_dano)),
        ("Resistencia Petro", f"+{float(petro_res):.2f}" if isinstance(petro_res, (int, float)) else str(petro_res)),
        ("Moedas Acumuladas", f"{moedas} moedas")
    ]
    
    rodando = True
    while rodando:
        if fundo_pausa:
            tela.blit(fundo_pausa, (0, 0))
        else:
            tela.fill((10, 10, 20))
            
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((8, 5, 15, 235)) # Fundo escuro com opacidade alta para total legibilidade
        
        # Linhas ciberneticas sutis de fundo
        for y in range(0, altura_tela, 8):
            pygame.draw.line(overlay, (0, 255, 204, 8), (0, y), (largura_tela, y))
            
        tela.blit(overlay, (0, 0))
        
        # Titulo principal com sombra para alto contraste
        texto_titulo = fonte_titulo_tela.render("ANALISE DE ATRIBUTOS", True, (0, 255, 204))
        ret_tit = texto_titulo.get_rect(center=(largura_tela // 2, 60))
        titulo_sombra = fonte_titulo_tela.render("ANALISE DE ATRIBUTOS", True, (0, 0, 0))
        tela.blit(titulo_sombra, (ret_tit.x + 3, ret_tit.y + 3))
        tela.blit(texto_titulo, ret_tit)
        
        # Configuracao do Grid
        margem_x = (largura_tela - 1100) // 2
        col_w = 340
        col_h = 440
        col_y = 120
        
        mx, my = _obter_pos_mouse_pause()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE]:
                    rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                back_rect = pygame.Rect(largura_tela // 2 - 100, altura_tela - 75, 200, 40)
                if back_rect.collidepoint(mx, my):
                    rodando = False
                    
        # Pulsing and scanner math
        tempo = pygame.time.get_ticks()
        pulse = int(200 + 55 * math.sin(tempo * 0.005))
        scan_offset = (tempo // 6) % (col_h - 20)
        
        # 1. Coluna Ofensiva (Cian/Verde)
        x_of = margem_x
        panel_of = pygame.Rect(x_of, col_y, col_w, col_h)
        hover_of = panel_of.collidepoint(mx, my)
        bg_of = (25, 20, 50, 230) if hover_of else (15, 12, 30, 215)
        border_of = (0, pulse, int(pulse * 0.8)) if hover_of else (0, 255, 204, 120)
        border_w_of = 3 if hover_of else 2
        
        pygame.draw.rect(tela, bg_of, panel_of, border_radius=12)
        pygame.draw.rect(tela, border_of, panel_of, width=border_w_of, border_radius=12)
        
        if hover_of:
            scan_y = col_y + 10 + scan_offset
            pygame.draw.line(tela, (0, pulse, int(pulse * 0.8), 120), (x_of + 10, scan_y), (x_of + col_w - 10, scan_y), 2)
        
        txt_sec_of = fonte_secao.render("OFENSIVO", True, (0, 255, 204))
        tela.blit(fonte_secao.render("OFENSIVO", True, (0, 0, 0)), (x_of + 22, col_y + 22))
        tela.blit(txt_sec_of, (x_of + 20, col_y + 20))
        pygame.draw.line(tela, (0, 255, 204, 80), (x_of + 20, col_y + 55), (x_of + col_w - 20, col_y + 55), 1)
        
        item_y = col_y + 70
        for label, val in col_ofensiva:
            txt_lbl = fonte_label.render(label, True, (200, 200, 210))
            tela.blit(fonte_label.render(label, True, (0, 0, 0)), (x_of + 21, item_y + 1))
            tela.blit(txt_lbl, (x_of + 20, item_y))
            
            cor_val = (0, 255, 150) if val not in ["Inativo", "Desativado"] else (220, 100, 100)
            txt_v = fonte_valor.render(val, True, cor_val)
            tela.blit(fonte_valor.render(val, True, (0, 0, 0)), (x_of + col_w - 21 - txt_v.get_width(), item_y + 1))
            tela.blit(txt_v, (x_of + col_w - 20 - txt_v.get_width(), item_y))
            item_y += 45
            
        # 2. Coluna Defensiva (Roxo/Rosa)
        x_def = margem_x + col_w + 40
        panel_def = pygame.Rect(x_def, col_y, col_w, col_h)
        hover_def = panel_def.collidepoint(mx, my)
        bg_def = (35, 18, 50, 230) if hover_def else (15, 12, 30, 215)
        border_def = (pulse, int(pulse * 0.5), pulse) if hover_def else (180, 100, 255, 120)
        border_w_def = 3 if hover_def else 2
        
        pygame.draw.rect(tela, bg_def, panel_def, border_radius=12)
        pygame.draw.rect(tela, border_def, panel_def, width=border_w_def, border_radius=12)
        
        if hover_def:
            scan_y = col_y + 10 + scan_offset
            pygame.draw.line(tela, (pulse, 100, pulse, 120), (x_def + 10, scan_y), (x_def + col_w - 10, scan_y), 2)
        
        txt_sec_def = fonte_secao.render("SOBREVIVENCIA", True, (180, 100, 255))
        tela.blit(fonte_secao.render("SOBREVIVENCIA", True, (0, 0, 0)), (x_def + 22, col_y + 22))
        tela.blit(txt_sec_def, (x_def + 20, col_y + 20))
        pygame.draw.line(tela, (180, 100, 255, 80), (x_def + 20, col_y + 55), (x_def + col_w - 20, col_y + 55), 1)
        
        item_y = col_y + 70
        for label, val in col_defensiva:
            txt_lbl = fonte_label.render(label, True, (210, 200, 220))
            tela.blit(fonte_label.render(label, True, (0, 0, 0)), (x_def + 21, item_y + 1))
            tela.blit(txt_lbl, (x_def + 20, item_y))
            
            cor_val = (180, 120, 255)
            if "/" in val:
                cor_val = (255, 100, 100)
            elif "Ativo" in val:
                cor_val = (0, 255, 150)
            elif "Inativo" in val:
                cor_val = (220, 100, 100)
                
            txt_v = fonte_valor.render(val, True, cor_val)
            tela.blit(fonte_valor.render(val, True, (0, 0, 0)), (x_def + col_w - 21 - txt_v.get_width(), item_y + 1))
            tela.blit(txt_v, (x_def + col_w - 20 - txt_v.get_width(), item_y))
            item_y += 45
 
        # 3. Coluna Petro / Recursos (Laranja/Amarelo)
        x_pet = margem_x + (col_w + 40) * 2
        panel_pet = pygame.Rect(x_pet, col_y, col_w, col_h)
        hover_pet = panel_pet.collidepoint(mx, my)
        bg_pet = (38, 25, 18, 230) if hover_pet else (15, 12, 30, 215)
        border_pet = (pulse, int(pulse * 0.7), 0) if hover_pet else (255, 180, 0, 120)
        border_w_pet = 3 if hover_pet else 2
        
        pygame.draw.rect(tela, bg_pet, panel_pet, border_radius=12)
        pygame.draw.rect(tela, border_pet, panel_pet, width=border_w_pet, border_radius=12)
        
        if hover_pet:
            scan_y = col_y + 10 + scan_offset
            pygame.draw.line(tela, (pulse, 180, 0, 120), (x_pet + 10, scan_y), (x_pet + col_w - 10, scan_y), 2)
        
        txt_sec_pet = fonte_secao.render("COMPANHEIRO & RECURSOS", True, (255, 180, 0))
        tela.blit(fonte_secao.render("COMPANHEIRO & RECURSOS", True, (0, 0, 0)), (x_pet + 22, col_y + 22))
        tela.blit(txt_sec_pet, (x_pet + 20, col_y + 20))
        pygame.draw.line(tela, (255, 180, 0, 80), (x_pet + 20, col_y + 55), (x_pet + col_w - 20, col_y + 55), 1)
        
        item_y = col_y + 70
        for label, val in col_petro:
            txt_lbl = fonte_label.render(label, True, (220, 210, 190))
            tela.blit(fonte_label.render(label, True, (0, 0, 0)), (x_pet + 21, item_y + 1))
            tela.blit(txt_lbl, (x_pet + 20, item_y))
            
            cor_val = (255, 180, 0)
            if "Inativo" in val or "Nao" in val:
                cor_val = (160, 160, 160)
            elif "Ativo" in val:
                cor_val = (0, 255, 150)
                
            txt_v = fonte_valor.render(val, True, cor_val)
            tela.blit(fonte_valor.render(val, True, (0, 0, 0)), (x_pet + col_w - 21 - txt_v.get_width(), item_y + 1))
            tela.blit(txt_v, (x_pet + col_w - 20 - txt_v.get_width(), item_y))
            item_y += 45
            
        # Botao Voltar
        back_rect = pygame.Rect(largura_tela // 2 - 100, altura_tela - 75, 200, 40)
        is_hover_back = back_rect.collidepoint(mx, my)
        pygame.draw.rect(tela, (0, 180, 200, 75) if is_hover_back else (15, 12, 35, 230), back_rect, border_radius=6)
        pygame.draw.rect(tela, (0, 255, 230) if is_hover_back else (0, 255, 204), back_rect, width=2, border_radius=6)
        txt_back = fonte_instrucao.render("VOLTAR AO MENU", True, (255, 255, 255) if is_hover_back else (200, 200, 200))
        tela.blit(txt_back, (back_rect.centerx - txt_back.get_width()//2, back_rect.centery - txt_back.get_height()//2))
        
        pygame.display.flip()
        clock.tick(60)

def exibir_tela_pause(tela, cartas_compradas, joystick=None):
    pygame.init()
    clock = pygame.time.Clock()
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(True)
    largura_tela, altura_tela = tela.get_size()
    fontes = carregar_fontes()
    fundo_pausa = tela.copy()
    tela_atualizada = False
    config_graficos_atualizada = None

    def _aplicar_resultado_config(resultado):
        nonlocal tela, largura_tela, altura_tela, fundo_pausa, tela_atualizada, config_graficos_atualizada
        nova_tela = None
        if isinstance(resultado, dict):
            nova_tela = resultado.get("tela")
            if isinstance(resultado.get("config_graficos"), dict):
                config_graficos_atualizada = resultado["config_graficos"]
        elif isinstance(resultado, pygame.Surface):
            nova_tela = resultado
        if nova_tela is None:
            return
        tela = nova_tela
        largura_tela, altura_tela = tela.get_size()
        fundo_pausa = pygame.transform.scale(fundo_pausa, (largura_tela, altura_tela))
        tela_atualizada = True
        pygame.mouse.set_visible(True)

    def _finalizar_pause(acao):
        pygame.mouse.set_visible(False)
        if tela_atualizada or config_graficos_atualizada is not None:
            retorno = {"acao": acao}
            if tela_atualizada:
                retorno["tela"] = tela
            if config_graficos_atualizada is not None:
                retorno["config_graficos"] = config_graficos_atualizada
            return retorno
        return acao
    
    opcoes_pause = [
        "Continuar",
        "Analise de Atributos",
        "Ajustar Controles",
        "Ajustar Audio",
        "Ajustar Graficos",
        "Ajustar Jogabilidade",
        "Ver Anomalias",
        "Sair ao Menu"
    ]
    
    descricoes_pause = {
        "Continuar": "Retornar ao combate e retomar a jornada.",
        "Analise de Atributos": "Visualizar estatisticas detalhadas de combate e sobrevivencia.",
        "Ajustar Controles": "Configurar teclas do teclado e botoes do mouse.",
        "Ajustar Audio": "Ajustar volumes de musica, efeitos e som geral.",
        "Ajustar Graficos": "Modificar configuracoes de sombra, particulas e FPS.",
        "Ajustar Jogabilidade": "Configurar preferencias de tutorial e teleporte.",
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
                "nome": "Porcao" if nome == "Porção" else nome,
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
    CARD_H = 430
    CARD_X = 70
    CARD_Y = 160
    
    # Joystick movement delay
    last_joy_move = 0
    
    rodando = True
    while rodando:
        agora = pygame.time.get_ticks()
        pulsar = (math.sin(agora * 0.005) + 1) / 2
        mx, my = _obter_pos_mouse_pause()
        
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
                        return _finalizar_pause("continuar")
                    elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        tocar_selecionar()
                        opcao_sel = opcoes_pause[selecionado]
                        if opcao_sel == "Continuar":
                            return _finalizar_pause("continuar")
                        elif opcao_sel == "Analise de Atributos":
                            abrir_analise_atributos(tela, fontes, fundo_pausa=fundo_pausa)
                        elif opcao_sel == "Ajustar Controles":
                            from Config_Teclas import tela_de_controles, carregar_config_teclas
                            cfg = carregar_config_teclas()
                            tela_de_controles(tela, cfg, largura_tela, altura_tela, fundo_pausa=fundo_pausa)
                        elif opcao_sel == "Ajustar Audio":
                            _aplicar_resultado_config(abrir_configuracoes_audio(tela, fontes, fundo_pausa=fundo_pausa))
                        elif opcao_sel == "Ajustar Graficos":
                            _aplicar_resultado_config(abrir_configuracoes_graficas(tela, fontes, fundo_pausa=fundo_pausa))
                        elif opcao_sel == "Ajustar Jogabilidade":
                            _aplicar_resultado_config(abrir_configuracoes_jogabilidade(tela, fontes, fundo_pausa=fundo_pausa))
                        elif opcao_sel == "Ver Anomalias":
                            estado_pause = "anomalias"
                        elif opcao_sel == "Sair ao Menu":
                            return _finalizar_pause("sair")
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
                mx, my = ui_helpers.converter_pos_mouse_jogo(evento.pos)
                if estado_pause == "menu":
                    for i, opcao in enumerate(opcoes_pause):
                        y_pos = CARD_Y + 24 + i * 48
                        rect_opcao = pygame.Rect(CARD_X + 15, y_pos - 6, CARD_W - 30, 42)
                        if rect_opcao.collidepoint(mx, my):
                            if i == selecionado:
                                tocar_selecionar()
                                opcao_sel = opcoes_pause[selecionado]
                                if opcao_sel == "Continuar":
                                    return _finalizar_pause("continuar")
                                elif opcao_sel == "Analise de Atributos":
                                    abrir_analise_atributos(tela, fontes, fundo_pausa=fundo_pausa)
                                elif opcao_sel == "Ajustar Controles":
                                    from Config_Teclas import tela_de_controles, carregar_config_teclas
                                    cfg = carregar_config_teclas()
                                    tela_de_controles(tela, cfg, largura_tela, altura_tela, fundo_pausa=fundo_pausa)
                                elif opcao_sel == "Ajustar Audio":
                                    _aplicar_resultado_config(abrir_configuracoes_audio(tela, fontes, fundo_pausa=fundo_pausa))
                                elif opcao_sel == "Ajustar Graficos":
                                    _aplicar_resultado_config(abrir_configuracoes_graficas(tela, fontes, fundo_pausa=fundo_pausa))
                                elif opcao_sel == "Ajustar Jogabilidade":
                                    _aplicar_resultado_config(abrir_configuracoes_jogabilidade(tela, fontes, fundo_pausa=fundo_pausa))
                                elif opcao_sel == "Ver Anomalias":
                                    estado_pause = "anomalias"
                                elif opcao_sel == "Sair ao Menu":
                                    return _finalizar_pause("sair")
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
                            return _finalizar_pause("continuar")
                        elif opcao_sel == "Analise de Atributos":
                            abrir_analise_atributos(tela, fontes, fundo_pausa=fundo_pausa)
                        elif opcao_sel == "Ajustar Controles":
                            from Config_Teclas import tela_de_controles, carregar_config_teclas
                            cfg = carregar_config_teclas()
                            tela_de_controles(tela, cfg, largura_tela, altura_tela, fundo_pausa=fundo_pausa)
                        elif opcao_sel == "Ajustar Audio":
                            _aplicar_resultado_config(abrir_configuracoes_audio(tela, fontes, fundo_pausa=fundo_pausa))
                        elif opcao_sel == "Ajustar Graficos":
                            _aplicar_resultado_config(abrir_configuracoes_graficas(tela, fontes, fundo_pausa=fundo_pausa))
                        elif opcao_sel == "Ajustar Jogabilidade":
                            _aplicar_resultado_config(abrir_configuracoes_jogabilidade(tela, fontes, fundo_pausa=fundo_pausa))
                        elif opcao_sel == "Ver Anomalias":
                            estado_pause = "anomalias"
                        elif opcao_sel == "Sair ao Menu":
                            return _finalizar_pause("sair")
                    elif evento.button in [1, 7]: # B or Start
                        tocar_selecionar()
                        return _finalizar_pause("continuar")
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

    return _finalizar_pause("continuar")
