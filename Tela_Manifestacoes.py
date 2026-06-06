# -*- coding: utf-8 -*-
import math
import random
import os
import re

import pygame

import ui_helpers
from dados_manifestacoes import obter_manifestacoes, obter_manifestacao_ativa, salvar_manifestacao_ativa
from sons_procedurais import tocar_hover, tocar_selecionar


_ICONE_CACHE = {}


def _fonte(caminho, tamanho, fallback=None):
    try:
        return pygame.font.Font(caminho, tamanho)
    except Exception:
        return fallback or pygame.font.Font(None, tamanho)


def _linhas_wrap(texto, fonte, largura_max):
    palavras = str(texto).split(" ")
    linhas = []
    atual = []
    for palavra in palavras:
        teste = " ".join(atual + [palavra])
        if fonte.size(teste)[0] <= largura_max:
            atual.append(palavra)
            continue
        if atual:
            linhas.append(" ".join(atual))
        atual = [palavra]
    if atual:
        linhas.append(" ".join(atual))
    return linhas


def _desenhar_texto_wrap(superficie, texto, rect, fonte, cor, gap=2):
    y = rect.y
    for linha in _linhas_wrap(texto, fonte, rect.w):
        if y + fonte.get_linesize() > rect.bottom:
            break
        render = fonte.render(linha, True, cor)
        superficie.blit(render, (rect.x, y))
        y += fonte.get_linesize() + gap
    return y


def _carregar_icone_manifestacao(caminho, tamanho):
    chave = (caminho, tamanho)
    if chave in _ICONE_CACHE:
        return _ICONE_CACHE[chave]
    try:
        imagem = pygame.image.load(caminho).convert_alpha()
        largura, altura = imagem.get_size()
        escala = min(tamanho / max(1, largura), tamanho / max(1, altura))
        novo_tamanho = (max(1, int(largura * escala)), max(1, int(altura * escala)))
        imagem = pygame.transform.smoothscale(imagem, novo_tamanho)
    except Exception:
        imagem = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
        pygame.draw.circle(imagem, (0, 225, 255), (tamanho // 2, tamanho // 2), tamanho // 2 - 4, 2)
    _ICONE_CACHE[chave] = imagem
    return imagem


def _desenhar_fundo(tela, agora, particulas):
    largura, altura = tela.get_size()
    tela.fill((5, 7, 15))

    for y in range(0, altura, 46):
        alpha = 15 + int(8 * math.sin(agora * 0.0014 + y * 0.03))
        pygame.draw.line(tela, (0, 150, 190), (0, y), (largura, y), 1)
        if alpha > 0:
            pygame.draw.line(tela, (10, 30, 48), (0, y + 1), (largura, y + 1), 1)

    for x in range(0, largura, 64):
        pygame.draw.line(tela, (7, 24, 42), (x, 0), (x, altura), 1)

    cx, cy = largura // 2, altura // 2
    for raio, alpha in ((360, 16), (250, 22), (120, 28)):
        surf = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (0, 220, 255, alpha), (raio, raio), raio, 2)
        tela.blit(surf, (cx - raio, cy - raio))

    for p in particulas:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["fase"] += 0.025
        if p["x"] < -20 or p["x"] > largura + 20 or p["y"] < -20 or p["y"] > altura + 20:
            p["x"] = random.uniform(0, largura)
            p["y"] = altura + random.uniform(0, 60)
        alpha = max(20, min(150, int(p["alpha"] + math.sin(p["fase"]) * 40)))
        pygame.draw.circle(tela, (0, 230, 255), (int(p["x"]), int(p["y"])), p["r"])
        if alpha > 90:
            pygame.draw.line(tela, (110, 245, 255), (int(p["x"]), int(p["y"])), (int(p["x"] - p["vx"] * 12), int(p["y"] - p["vy"] * 12)), 1)


def _desenhar_icone(tela, rect, dados, selecionado, desbloqueada, agora, entrada):
    centro = rect.center
    cor = dados["cor"] if desbloqueada else (80, 90, 105)
    cor2 = dados["cor_secundaria"] if desbloqueada else (50, 55, 70)
    pulso = 1.0 + (0.08 * math.sin(agora * 0.008) if selecionado else 0.0)
    raio = int((rect.w // 2 - 8) * pulso * entrada)

    if selecionado:
        for r, alpha in ((raio + 22, 35), (raio + 10, 60)):
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*cor[:3], alpha), (r, r), r, 2)
            tela.blit(surf, (centro[0] - r, centro[1] - r))

    pygame.draw.circle(tela, (10, 14, 24), centro, max(8, raio))
    pygame.draw.circle(tela, cor, centro, max(8, raio), 2 if selecionado else 1)
    pygame.draw.circle(tela, cor2, centro, max(4, raio // 2), 1)

    if desbloqueada:
        mao_y = centro[1] + 13
        pygame.draw.line(tela, (220, 255, 255), (centro[0] - 20, mao_y), (centro[0] - 5, centro[1] + 3), 3)
        pygame.draw.line(tela, (220, 255, 255), (centro[0] + 20, mao_y), (centro[0] + 5, centro[1] + 3), 3)
        for dx in (-12, 0, 12):
            y = centro[1] - 6 + int(math.sin(agora * 0.009 + dx) * 5)
            pygame.draw.circle(tela, cor, (centro[0] + dx, y), 3)
        pygame.draw.line(tela, cor, (centro[0] - 10, centro[1]), (centro[0] + 14, centro[1] - 10), 2)
        pygame.draw.line(tela, cor, (centro[0] + 14, centro[1] - 10), (centro[0] + 2, centro[1] + 3), 2)
        pygame.draw.line(tela, cor, (centro[0] + 2, centro[1] + 3), (centro[0] + 20, centro[1] + 5), 2)
    else:
        corpo = pygame.Rect(0, 0, 34, 42)
        corpo.center = centro
        pygame.draw.ellipse(tela, (35, 38, 50), corpo)
        cadeado = pygame.Rect(0, 0, 24, 19)
        cadeado.center = (centro[0], centro[1] + 4)
        pygame.draw.rect(tela, (95, 100, 115), cadeado, border_radius=4)
        pygame.draw.arc(tela, (95, 100, 115), (centro[0] - 9, centro[1] - 16, 18, 20), math.pi, math.tau, 3)

    if selecionado and desbloqueada:
        for i in range(9):
            ang = agora * 0.004 + i * math.tau / 9
            px = centro[0] + math.cos(ang) * (raio + 15)
            py = centro[1] + math.sin(ang) * (raio + 15)
            pygame.draw.circle(tela, cor, (int(px), int(py)), 2)


def _desenhar_slot_matriz(tela, rect, dados, selecionado, desbloqueada, agora, entrada, fontes):
    cor = dados["cor"] if desbloqueada else (92, 102, 122)
    pulso = 1.0 + (0.045 * math.sin(agora * 0.008) if selecionado else 0.0)
    slot = rect.copy()
    if selecionado:
        slot.inflate_ip(int(rect.w * (pulso - 1.0)), int(rect.h * (pulso - 1.0)))

    surf = pygame.Surface((slot.w, slot.h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (8, 11, 22, int(210 * entrada)), (0, 0, slot.w, slot.h), border_radius=8)
    pygame.draw.rect(surf, (*cor[:3], 245 if selecionado else 95), (0, 0, slot.w, slot.h), 2 if selecionado else 1, border_radius=8)
    pygame.draw.rect(surf, (255, 255, 255, 22 if selecionado else 10), (7, 7, slot.w - 14, slot.h - 14), 1, border_radius=6)

    if selecionado:
        for i in range(8):
            ang = agora * 0.006 + i * math.tau / 8
            px = slot.w // 2 + math.cos(ang) * (slot.w * 0.43)
            py = slot.h // 2 + math.sin(ang) * (slot.h * 0.43)
            pygame.draw.circle(surf, (*cor[:3], 180), (int(px), int(py)), 2)

    if desbloqueada:
        icone = _carregar_icone_manifestacao(dados.get("icone", ""), int(min(slot.w, slot.h) * 0.66))
        surf.blit(icone, icone.get_rect(center=(slot.w // 2, slot.h // 2 - 8)))
        nome = fontes["pequena"].render(dados["nome"], True, (220, 250, 255))
        surf.blit(nome, nome.get_rect(center=(slot.w // 2, slot.h - 20)))
    else:
        texto = fontes["titulo_slot"].render("?", True, (155, 165, 185))
        surf.blit(texto, texto.get_rect(center=(slot.w // 2, slot.h // 2 - 4)))
        futuro = fontes["pequena"].render("Futura", True, (115, 125, 145))
        surf.blit(futuro, futuro.get_rect(center=(slot.w // 2, slot.h - 20)))

    tela.blit(surf, slot.topleft)


def _desenhar_painel(tela, rect, dados, desbloqueada, fontes, fade):
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    surf.fill((8, 10, 20, int(220 * fade)))
    pygame.draw.rect(surf, (0, 210, 255, int(90 * fade)), (0, 0, rect.w, rect.h), 1, border_radius=8)
    pygame.draw.rect(surf, (120, 80, 255, int(35 * fade)), (7, 7, rect.w - 14, rect.h - 14), 1, border_radius=6)

    x = 24
    y = 20
    titulo = dados["nome"] if desbloqueada else "Manifestação não estabilizada"
    cor_titulo = (230, 255, 255) if desbloqueada else (155, 160, 175)
    surf.blit(fontes["nome"].render(titulo, True, cor_titulo), (x, y))
    y += 46

    if not desbloqueada:
        _desenhar_texto_wrap(
            surf,
            "Eco ainda não dominado. A Ruptura emite resposta, mas Geovana ainda não estabilizou essa forma de combate.",
            pygame.Rect(x, y, rect.w - 48, rect.h - y - 24),
            fontes["texto"],
            (170, 180, 195),
        )
        tela.blit(surf, rect.topleft)
        return

    descricao = dados.get("frase") or dados.get("descricao_curta")
    if descricao:
        y = _desenhar_texto_wrap(surf, descricao, pygame.Rect(x, y, rect.w - 48, 58), fontes["texto"], (170, 205, 215), 1)
        y += 10

    itens = [
        ("Função", dados["funcao"]),
        ("Disparo", dados["disparo"]),
        ("Habilidade", dados["habilidade"] + ": " + dados["descricao_habilidade"]),
        ("Traço", dados["traco"]),
        ("Risco", dados["risco"]),
    ]

    for rotulo, texto in itens:
        if y > rect.h - 55:
            break
        surf.blit(fontes["rotulo"].render(rotulo.upper(), True, dados["cor"]), (x, y))
        y += 22
        y = _desenhar_texto_wrap(surf, texto, pygame.Rect(x, y, rect.w - 48, rect.h - y - 12), fontes["texto"], (210, 225, 236), 1)
        y += 10

    tela.blit(surf, rect.topleft)


def _desenhar_preview_em_preparo(tela, rect, fontes, dados):
    cor = dados.get("cor", (120, 130, 150))
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (7, 9, 18, 225), (0, 0, rect.w, rect.h), border_radius=8)
    pygame.draw.rect(surf, (*cor[:3], 100), (0, 0, rect.w, rect.h), 1, border_radius=8)
    surf.blit(fontes["rotulo"].render("PREVIEW", True, cor), (20, 16))
    texto = fontes["titulo_slot"].render("?", True, (175, 180, 195))
    surf.blit(texto, texto.get_rect(center=(rect.w // 2, rect.h // 2 - 4)))
    aviso = fontes["texto"].render("Preview em preparo", True, (145, 150, 165))
    surf.blit(aviso, aviso.get_rect(center=(rect.w // 2, rect.h - 34)))
    tela.blit(surf, rect.topleft)


def _desenhar_preview_eletrico(tela, rect, agora, fontes, frames_video=None):
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (7, 9, 18, 225), (0, 0, rect.w, rect.h), border_radius=8)
    pygame.draw.rect(surf, (0, 210, 255, 95), (0, 0, rect.w, rect.h), 1, border_radius=8)

    surf.blit(fontes["rotulo"].render("PREVIEW", True, (0, 225, 255)), (20, 16))

    if frames_video and len(frames_video) > 0:
        # Tenta desenhar o frame do vídeo preservando o aspect ratio
        fps = 15  # frames por segundo padrão
        intervalo = 1000 // fps
        frame_atual = (agora // intervalo) % len(frames_video)
        img_original = frames_video[frame_atual]

        max_w = rect.w - 40
        max_h = rect.h - 62
        
        w_orig, h_orig = img_original.get_size()
        escala = min(max_w / w_orig, max_h / h_orig)
        novo_w = int(w_orig * escala)
        novo_h = int(h_orig * escala)
        
        # Centraliza o vídeo na área disponível
        x_dest = 20 + (max_w - novo_w) // 2
        y_dest = 42 + (max_h - novo_h) // 2

        try:
            img_redimensionada = pygame.transform.smoothscale(img_original, (novo_w, novo_h))
            
            # Fundo preto atrás do frame do vídeo
            pygame.draw.rect(surf, (0, 0, 0), (x_dest, y_dest, novo_w, novo_h))
            surf.blit(img_redimensionada, (x_dest, y_dest))
            
            # Desenha uma borda neon sutil ao redor do frame
            pygame.draw.rect(surf, (0, 210, 255, 120), (x_dest - 1, y_dest - 1, novo_w + 2, novo_h + 2), 1)
        except Exception:
            surf.blit(img_original, (20, 42))
    else:
        # Fallback para a animação procedural antiga caso não haja vídeo
        fase = (agora % 5200) / 5200.0
        base_x = 86
        base_y = rect.h // 2 + 16
        recuo = 0
        if fase > 0.67:
            recuo = int(math.sin(min(1.0, (fase - 0.67) / 0.12) * math.pi) * 14)

        mao_esq = (base_x - recuo, base_y - 16)
        mao_dir = (base_x - recuo, base_y + 16)
        pygame.draw.circle(surf, (185, 240, 255), mao_esq, 7)
        pygame.draw.circle(surf, (185, 240, 255), mao_dir, 7)
        pygame.draw.line(surf, (80, 170, 210), (base_x - 30 - recuo, base_y), mao_esq, 3)
        pygame.draw.line(surf, (80, 170, 210), (base_x - 30 - recuo, base_y), mao_dir, 3)

        alvos = [(rect.w - 95, base_y), (rect.w - 58, base_y - 42), (rect.w - 42, base_y + 44)]
        for alvo in alvos:
            pygame.draw.circle(surf, (32, 38, 52), alvo, 15)
            pygame.draw.circle(surf, (100, 110, 135), alvo, 15, 1)

        if fase < 0.34:
            carga = fase / 0.34
            r = int(8 + carga * 18 + math.sin(agora * 0.03) * 2)
            pygame.draw.circle(surf, (0, 230, 255), (base_x + 12, base_y), max(2, r), 2)
            pygame.draw.circle(surf, (220, 255, 255), (base_x + 12, base_y), max(2, r // 3))
        elif fase < 0.62:
            t = (fase - 0.34) / 0.28
            x = int(base_x + 20 + (alvos[0][0] - base_x - 20) * t)
            y = base_y
            for i in range(7):
                tx = x - i * 18
                alpha = max(30, 190 - i * 25)
                pygame.draw.circle(surf, (0, 215, 255, alpha), (tx, y), max(2, 7 - i))
            pygame.draw.circle(surf, (220, 255, 255), (x, y), 8)
        elif fase < 0.75:
            for i in range(16):
                ang = i * math.tau / 16 + agora * 0.01
                px = alvos[0][0] + math.cos(ang) * (8 + i % 5)
                py = alvos[0][1] + math.sin(ang) * (8 + i % 5)
                pygame.draw.line(surf, (0, 230, 255), alvos[0], (int(px), int(py)), 1)
        else:
            t = (fase - 0.75) / 0.25
            raio = int(24 + t * 80)
            pygame.draw.circle(surf, (120, 80, 255), (base_x + 14, base_y), raio, 2)
            for a, b in ((alvos[0], alvos[1]), (alvos[0], alvos[2])):
                pontos = []
                for i in range(7):
                    k = i / 6.0
                    px = a[0] + (b[0] - a[0]) * k + math.sin(agora * 0.018 + i) * 8
                    py = a[1] + (b[1] - a[1]) * k + math.cos(agora * 0.015 + i) * 6
                    pontos.append((int(px), int(py)))
                pygame.draw.lines(surf, (0, 230, 255), False, pontos, 2)

    tela.blit(surf, rect.topleft)


def _desenhar_preview_bloqueado(tela, rect, fontes):
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (7, 9, 18, 225), (0, 0, rect.w, rect.h), border_radius=8)
    pygame.draw.rect(surf, (95, 100, 120, 80), (0, 0, rect.w, rect.h), 1, border_radius=8)
    surf.blit(fontes["rotulo"].render("PREVIEW", True, (120, 130, 150)), (20, 16))
    texto = fontes["texto"].render("Eco sem leitura estável.", True, (145, 150, 165))
    surf.blit(texto, texto.get_rect(center=(rect.w // 2, rect.h // 2)))
    for x in range(40, rect.w - 40, 34):
        pygame.draw.circle(surf, (45, 50, 64), (x, rect.h // 2 + int(math.sin(x) * 8)), 3)
    tela.blit(surf, rect.topleft)


def tela_manifestacoes(tela, fonte_base):
    pygame.mouse.set_visible(False)
    largura, altura = tela.get_size()
    clock = pygame.time.Clock()
    manifestacoes = obter_manifestacoes()
    manifestacao_salva = obter_manifestacao_ativa()
    selecionado = 0
    for i, (chave, _) in enumerate(manifestacoes):
        if chave == manifestacao_salva:
            selecionado = i
            break
    entrada_inicio = pygame.time.get_ticks()
    troca_inicio = entrada_inicio
    modo_interacao = "teclado"
    analogo_movido = False

    # Carrega os frames do preview de vídeo para as manifestações dominadas
    frames_previews = {}
    for chave, dados in manifestacoes:
        if dados.get("desbloqueada", False):
            pasta_video = os.path.join("Video", f"preview_{chave}")
            if os.path.isdir(pasta_video):
                try:
                    arquivos = [f for f in os.listdir(pasta_video) if f.lower().endswith(('.png', '.webp', '.jpg', '.jpeg'))]
                    def obter_numero(nome):
                        numeros = re.findall(r'\d+', nome)
                        return int(numeros[0]) if numeros else 0
                    arquivos.sort(key=obter_numero)
                    
                    frames = []
                    for arq in arquivos:
                        caminho_completo = os.path.join(pasta_video, arq)
                        img = pygame.image.load(caminho_completo).convert_alpha()
                        frames.append(img)
                    if frames:
                        frames_previews[chave] = frames
                except Exception as e:
                    from qa_logger import registrar_erro
                    registrar_erro(f"Erro ao carregar frames do preview de {chave}", e)

    fontes = {
        "titulo": _fonte("Texto/World.otf", 46, fonte_base),
        "subtitulo": _fonte("Texto/rainyhearts.ttf", 22, fonte_base),
        "nome": _fonte("Texto/rainyhearts.ttf", 34, fonte_base),
        "rotulo": _fonte("Texto/rainyhearts.ttf", 18, fonte_base),
        "texto": _fonte("Texto/rainyhearts.ttf", 17, fonte_base),
        "botao": _fonte("Texto/rainyhearts.ttf", 24, fonte_base),
        "pequena": _fonte("Texto/rainyhearts.ttf", 15, fonte_base),
        "titulo_slot": _fonte("Texto/World.otf", 56, fonte_base),
    }

    particulas = [
        {
            "x": random.uniform(0, largura),
            "y": random.uniform(0, altura),
            "vx": random.uniform(-0.15, 0.15),
            "vy": random.uniform(-0.75, -0.18),
            "r": random.randint(1, 3),
            "alpha": random.randint(40, 120),
            "fase": random.uniform(0, math.tau),
        }
        for _ in range(80)
    ]

    def mover(delta):
        nonlocal selecionado, troca_inicio
        selecionado = (selecionado + delta) % len(manifestacoes)
        troca_inicio = pygame.time.get_ticks()
        tocar_hover()

    def confirmar():
        chave, dados = manifestacoes[selecionado]
        if not dados.get("desbloqueada", False):
            tocar_hover()
            return None
        tocar_selecionar()
        salvar_manifestacao_ativa(chave)
        return "confirmar"

    while True:
        agora = pygame.time.get_ticks()
        entrada = min(1.0, (agora - entrada_inicio) / 850.0)
        fade_painel = min(1.0, (agora - troca_inicio) / 230.0)
        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        clicado = False

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if evento.type == pygame.MOUSEMOTION and evento.rel != (0, 0):
                modo_interacao = "mouse"
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                modo_interacao = "mouse"
                clicado = True
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    return "voltar"
                if evento.key in (pygame.K_RIGHT, pygame.K_d):
                    mover(1)
                elif evento.key in (pygame.K_LEFT, pygame.K_a):
                    mover(-1)
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    resultado = confirmar()
                    if resultado:
                        return resultado
            elif evento.type == pygame.JOYAXISMOTION:
                modo_interacao = "teclado"
                if evento.axis == 0:
                    if evento.value > 0.55 and not analogo_movido:
                        mover(1)
                        analogo_movido = True
                    elif evento.value < -0.55 and not analogo_movido:
                        mover(-1)
                        analogo_movido = True
                    elif abs(evento.value) < 0.25:
                        analogo_movido = False
            elif evento.type == pygame.JOYHATMOTION:
                dx, _ = evento.value
                if dx > 0:
                    mover(1)
                elif dx < 0:
                    mover(-1)
            elif evento.type == pygame.JOYBUTTONDOWN:
                if evento.button == 0:
                    resultado = confirmar()
                    if resultado:
                        return resultado
                elif evento.button == 1:
                    tocar_selecionar()
                    return "voltar"

        _desenhar_fundo(tela, agora, particulas)

        titulo = fontes["titulo"].render("MANIFESTAÇÕES", True, (225, 255, 255))
        sombra = fontes["titulo"].render("MANIFESTAÇÕES", True, (0, 90, 125))
        tela.blit(sombra, titulo.get_rect(center=(largura // 2 + 3, 72 + 3)))
        tela.blit(titulo, titulo.get_rect(center=(largura // 2, 72)))
        subtitulo = fontes["subtitulo"].render("Formas que a Ruptura assume através de Geovana.", True, (145, 235, 255))
        tela.blit(subtitulo, subtitulo.get_rect(center=(largura // 2, 118)))

        painel_rect = pygame.Rect(largura - 438, 160, 392, 430)
        preview_rect = pygame.Rect(48, altura - 244, min(560, largura - 520), 190)
        grade_rect = pygame.Rect(52, 175, max(420, largura - 560), max(300, altura - 470))

        titulo_grade = fontes["rotulo"].render("MATRIZ DE MANIFESTAÇÕES", True, (0, 225, 255))
        tela.blit(titulo_grade, (grade_rect.x + 4, grade_rect.y - 30))
        colunas = 3
        slot_w = min(150, max(112, (grade_rect.w - 56) // colunas))
        slot_h = 118
        gap_x = 28
        gap_y = 24
        matriz_w = colunas * slot_w + (colunas - 1) * gap_x
        inicio_x = grade_rect.x + max(0, (grade_rect.w - matriz_w) // 2)
        inicio_y = grade_rect.y + 12
        icone_rects = []
        for i, (chave, dados) in enumerate(manifestacoes):
            atraso = i * 0.14
            entrada_icone = min(1.0, max(0.0, (entrada - atraso) / 0.42))
            coluna = i % colunas
            linha = i // colunas
            rect = pygame.Rect(
                inicio_x + coluna * (slot_w + gap_x),
                inicio_y + linha * (slot_h + gap_y),
                slot_w,
                slot_h,
            )
            icone_rects.append(rect)
            if entrada_icone <= 0:
                continue
            _desenhar_slot_matriz(tela, rect, dados, i == selecionado, dados.get("desbloqueada", False), agora, entrada_icone, fontes)

        if clicado:
            for i, rect in enumerate(icone_rects):
                if rect.collidepoint(mx, my):
                    if i != selecionado:
                        selecionado = i
                        troca_inicio = pygame.time.get_ticks()
                        tocar_hover()
                        chave, dados = manifestacoes[selecionado]
                        if dados.get("desbloqueada", False):
                            salvar_manifestacao_ativa(chave)
                    else:
                        resultado = confirmar()
                        if resultado:
                            return resultado

        chave_sel, dados_sel = manifestacoes[selecionado]
        desbloqueada = dados_sel.get("desbloqueada", False)
        _desenhar_painel(tela, painel_rect, dados_sel, desbloqueada, fontes, fade_painel)
        if chave_sel == "eletrica":
            _desenhar_preview_eletrico(tela, preview_rect, agora - troca_inicio, fontes, frames_previews.get(chave_sel))
        elif desbloqueada and frames_previews.get(chave_sel):
            _desenhar_preview_eletrico(tela, preview_rect, agora - troca_inicio, fontes, frames_previews.get(chave_sel))
        elif desbloqueada:
            _desenhar_preview_em_preparo(tela, preview_rect, fontes, dados_sel)
        else:
            _desenhar_preview_bloqueado(tela, preview_rect, fontes)

        botao_rect = pygame.Rect(painel_rect.centerx - 92, painel_rect.bottom + 22, 184, 46)
        btn_cor = dados_sel["cor"] if desbloqueada else (80, 85, 95)
        pygame.draw.rect(tela, (8, 12, 22), botao_rect, border_radius=8)
        pygame.draw.rect(tela, btn_cor, botao_rect, 2, border_radius=8)
        texto_btn = "Manifestar" if desbloqueada else "Bloqueada"
        txt_btn = fontes["botao"].render(texto_btn, True, (230, 255, 255) if desbloqueada else (145, 150, 160))
        tela.blit(txt_btn, txt_btn.get_rect(center=botao_rect.center))
        if clicado and botao_rect.collidepoint(mx, my):
            resultado = confirmar()
            if resultado:
                return resultado

        voltar_rect = pygame.Rect(40, 34, 118, 36)
        pygame.draw.rect(tela, (10, 12, 22, 180), voltar_rect, border_radius=7)
        pygame.draw.rect(tela, (0, 210, 255), voltar_rect, 1, border_radius=7)
        txt_voltar = fontes["pequena"].render("ESC Voltar", True, (180, 225, 235))
        tela.blit(txt_voltar, txt_voltar.get_rect(center=voltar_rect.center))
        if clicado and voltar_rect.collidepoint(mx, my):
            tocar_selecionar()
            return "voltar"

        rodape = "A/D ou setas navegam  |  ENTER manifesta  |  Mouse seleciona"
        if modo_interacao == "mouse":
            rodape = "Clique no ícone para selecionar, clique em Manifestar para confirmar"
        txt_rodape = fontes["pequena"].render(rodape, True, (115, 165, 185))
        tela.blit(txt_rodape, txt_rodape.get_rect(center=(largura // 2, altura - 22)))

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)
