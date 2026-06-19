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


def _nome_curto_manifestacao(dados):
    nome = str(dados.get("nome", "Manifestacao"))
    for prefixo in ("Manifestação ", "Manifestacao "):
        if nome.startswith(prefixo):
            return nome[len(prefixo):]
    return nome


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
    tela.fill((4, 6, 13))

    for y in range(0, altura, 48):
        pygame.draw.line(tela, (8, 22, 35), (0, y), (largura, y), 1)

    for x in range(0, largura, 64):
        pygame.draw.line(tela, (7, 20, 33), (x, 0), (x, altura), 1)

    for i in range(-altura, largura, 160):
        pygame.draw.line(tela, (10, 28, 42), (i, altura), (i + altura, 0), 1)

    cx, cy = largura // 2, altura // 2
    for raio, alpha in ((420, 10), (285, 16), (132, 22)):
        surf = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (0, 160, 210, alpha), (raio, raio), raio, 1)
        tela.blit(surf, (cx - raio, cy - raio))

    for p in particulas:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["fase"] += 0.025
        if p["x"] < -20 or p["x"] > largura + 20 or p["y"] < -20 or p["y"] > altura + 20:
            p["x"] = random.uniform(0, largura)
            p["y"] = altura + random.uniform(0, 60)
        alpha = max(16, min(90, int(p["alpha"] + math.sin(p["fase"]) * 24)))
        pygame.draw.line(
            tela,
            (28, 86, 110),
            (int(p["x"]), int(p["y"])),
            (int(p["x"] - p["vx"] * 18), int(p["y"] - p["vy"] * 18)),
            1,
        )
        if alpha > 65:
            pygame.draw.circle(tela, (58, 128, 150), (int(p["x"]), int(p["y"])), p["r"])


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
        pygame.draw.line(tela, cor, (centro[0] - raio - 10, centro[1]), (centro[0] - raio - 2, centro[1]), 2)
        pygame.draw.line(tela, cor, (centro[0] + raio + 2, centro[1]), (centro[0] + raio + 10, centro[1]), 2)


def _desenhar_slot_matriz(tela, rect, dados, selecionado, desbloqueada, agora, entrada, fontes):
    cor = dados["cor"] if desbloqueada else (92, 102, 122)
    slot = rect.copy()
    slot.y += int((1.0 - entrada) * 18)

    surf = pygame.Surface((slot.w, slot.h), pygame.SRCALPHA)
    alpha_base = int(218 * entrada)
    pygame.draw.rect(surf, (7, 10, 18, alpha_base), (0, 0, slot.w, slot.h), border_radius=8)
    pygame.draw.rect(surf, (255, 255, 255, 16), (6, 6, slot.w - 12, slot.h - 12), 1, border_radius=6)
    pygame.draw.rect(surf, (*cor[:3], 230 if selecionado else 86), (0, 0, slot.w, slot.h), 2 if selecionado else 1, border_radius=8)

    if selecionado:
        brilho = pygame.Surface((slot.w, slot.h), pygame.SRCALPHA)
        pygame.draw.rect(brilho, (*cor[:3], 35), (0, 0, slot.w, slot.h), border_radius=8)
        surf.blit(brilho, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.rect(surf, (*cor[:3], 220), (0, 0, 5, slot.h), border_radius=4)
        canto = 17
        for x1, y1, sx, sy in ((7, 7, 1, 1), (slot.w - 8, 7, -1, 1), (7, slot.h - 8, 1, -1), (slot.w - 8, slot.h - 8, -1, -1)):
            pygame.draw.line(surf, (235, 255, 255, 170), (x1, y1), (x1 + sx * canto, y1), 1)
            pygame.draw.line(surf, (235, 255, 255, 170), (x1, y1), (x1, y1 + sy * canto), 1)

    pygame.draw.line(surf, (255, 255, 255, 18), (14, 34), (slot.w - 14, 34), 1)
    status = "ENCONTRADO" if desbloqueada else "BLOQUEADA"
    badge_w = max(68, fontes["pequena"].size(status)[0] + 16)
    badge = pygame.Rect(slot.w - badge_w - 10, 10, badge_w, 22)
    pygame.draw.rect(surf, (*cor[:3], 34 if desbloqueada else 22), badge, border_radius=4)
    pygame.draw.rect(surf, (*cor[:3], 140 if desbloqueada else 70), badge, 1, border_radius=4)
    txt_status = fontes["pequena"].render(status, True, (220, 245, 250) if desbloqueada else (130, 138, 152))
    surf.blit(txt_status, txt_status.get_rect(center=badge.center))

    if desbloqueada:
        icone = _carregar_icone_manifestacao(dados.get("icone", ""), int(min(slot.w, slot.h) * 0.52))
        placa = pygame.Rect(16, 40, slot.w - 32, slot.h - 72)
        pygame.draw.rect(surf, (0, 0, 0, 70), placa, border_radius=6)
        pygame.draw.rect(surf, (*cor[:3], 58), placa, 1, border_radius=6)
        surf.blit(icone, icone.get_rect(center=placa.center))
        nome_curto = _nome_curto_manifestacao(dados)
        fonte_nome = fontes["rotulo"] if fontes["rotulo"].size(nome_curto)[0] <= slot.w - 22 else fontes["pequena"]
        nome_sombra = fonte_nome.render(nome_curto, True, (0, 0, 0))
        nome = fonte_nome.render(nome_curto, True, (235, 255, 255))
        nome_rect = nome.get_rect(center=(slot.w // 2, slot.h - 17))
        surf.blit(nome_sombra, nome_rect.move(1, 1))
        surf.blit(nome, nome_rect)
    else:
        texto = fontes["titulo_slot"].render("?", True, (155, 165, 185))
        surf.blit(texto, texto.get_rect(center=(slot.w // 2, slot.h // 2 - 2)))
        futuro = fontes["pequena"].render("Futura", True, (115, 125, 145))
        surf.blit(futuro, futuro.get_rect(center=(slot.w // 2, slot.h - 17)))

    tela.blit(surf, slot.topleft)


def _desenhar_painel(tela, rect, dados, desbloqueada, fontes, fade, scroll_y=0):
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    cor = dados.get("cor", (120, 130, 150)) if desbloqueada else (95, 102, 118)
    surf.fill((7, 9, 18, int(228 * fade)))
    pygame.draw.rect(surf, (*cor[:3], int(120 * fade)), (0, 0, rect.w, rect.h), 1, border_radius=8)
    pygame.draw.rect(surf, (255, 255, 255, int(20 * fade)), (8, 8, rect.w - 16, rect.h - 16), 1, border_radius=6)
    pygame.draw.rect(surf, (*cor[:3], int(210 * fade)), (0, 0, 5, rect.h), border_radius=4)

    x = 24
    y = 20
    titulo = dados["nome"] if desbloqueada else "Manifestação não estabilizada"
    cor_titulo = (230, 255, 255) if desbloqueada else (155, 160, 175)
    surf.blit(fontes["nome"].render(titulo, True, cor_titulo), (x, y))
    y += 42
    pygame.draw.line(surf, (*cor[:3], 125), (x, y), (rect.w - 24, y), 1)
    y += 18

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
        caixa_desc = pygame.Rect(x, y, rect.w - 48, 74)
        pygame.draw.rect(surf, (255, 255, 255, 10), caixa_desc, border_radius=6)
        pygame.draw.rect(surf, (*cor[:3], 42), caixa_desc, 1, border_radius=6)
        _desenhar_texto_wrap(surf, descricao, pygame.Rect(x + 12, y + 10, rect.w - 72, 52), fontes["texto"], (178, 212, 220), 1)
        y = caixa_desc.bottom + 14

    itens = [
        ("Função", dados["funcao"]),
        ("Disparo", dados["disparo"]),
        ("Habilidade", dados["habilidade"] + ": " + dados["descricao_habilidade"]),
        ("Traço", dados["traco"]),
        ("Risco", dados["risco"]),
    ]

    for rotulo, texto in itens:
        if y > rect.h - 62:
            break
        pygame.draw.line(surf, (255, 255, 255, 24), (x, y), (rect.w - 24, y), 1)
        y += 9
        surf.blit(fontes["rotulo"].render(rotulo.upper(), True, cor), (x, y))
        y += 20
        y = _desenhar_texto_wrap(surf, texto, pygame.Rect(x, y, rect.w - 48, rect.h - y - 12), fontes["texto"], (210, 225, 236), 1)
        y += 12

    tela.blit(surf, rect.topleft)


def _desenhar_painel_rolavel(tela, rect, dados, desbloqueada, fontes, fade, scroll_y=0):
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    cor = dados.get("cor", (120, 130, 150)) if desbloqueada else (95, 102, 118)
    surf.fill((7, 9, 18, int(228 * fade)))
    pygame.draw.rect(surf, (*cor[:3], int(120 * fade)), (0, 0, rect.w, rect.h), 1, border_radius=8)
    pygame.draw.rect(surf, (255, 255, 255, int(20 * fade)), (8, 8, rect.w - 16, rect.h - 16), 1, border_radius=6)
    pygame.draw.rect(surf, (*cor[:3], int(210 * fade)), (0, 0, 5, rect.h), border_radius=4)

    x = 24
    y = 20
    titulo = dados["nome"] if desbloqueada else "Manifestacao nao estabilizada"
    cor_titulo = (230, 255, 255) if desbloqueada else (155, 160, 175)
    surf.blit(fontes["nome"].render(titulo, True, cor_titulo), (x, y))
    y += 42
    pygame.draw.line(surf, (*cor[:3], 125), (x, y), (rect.w - 24, y), 1)
    y += 18

    conteudo_top = y
    conteudo_visivel_h = rect.h - conteudo_top - 18
    conteudo = pygame.Surface((rect.w, 1400), pygame.SRCALPHA)
    cy = 0

    if not desbloqueada:
        _desenhar_texto_wrap(
            conteudo,
            dados.get("missao_desbloqueio") or "Eco ainda nao dominado. A Ruptura emite resposta, mas Geovana ainda nao estabilizou essa forma de combate.",
            pygame.Rect(x, cy, rect.w - 48, 220),
            fontes["texto"],
            (170, 180, 195),
        )
        surf.blit(conteudo, (0, conteudo_top), pygame.Rect(0, 0, rect.w, conteudo_visivel_h))
        tela.blit(surf, rect.topleft)
        return 0.0

    descricao = dados.get("frase") or dados.get("descricao_curta")
    if descricao:
        linhas_desc = _linhas_wrap(descricao, fontes["texto"], rect.w - 72)
        altura_desc = max(74, 22 + len(linhas_desc) * (fontes["texto"].get_linesize() + 1))
        caixa_desc = pygame.Rect(x, cy, rect.w - 48, altura_desc)
        pygame.draw.rect(conteudo, (255, 255, 255, 10), caixa_desc, border_radius=6)
        pygame.draw.rect(conteudo, (*cor[:3], 42), caixa_desc, 1, border_radius=6)
        _desenhar_texto_wrap(
            conteudo,
            descricao,
            pygame.Rect(x + 12, cy + 10, rect.w - 72, altura_desc - 16),
            fontes["texto"],
            (178, 212, 220),
            1,
        )
        cy = caixa_desc.bottom + 14

    itens = [
        ("Funcao", dados["funcao"]),
        ("Disparo", dados["disparo"]),
        ("Habilidade", dados["habilidade"] + ": " + dados["descricao_habilidade"]),
    ]
    if dados.get("teleporte"):
        itens.append(("Teleporte", dados["teleporte"]))
    itens.extend([
        ("Traco", dados["traco"]),
        ("Risco", dados["risco"]),
    ])

    for rotulo, texto in itens:
        pygame.draw.line(conteudo, (255, 255, 255, 24), (x, cy), (rect.w - 24, cy), 1)
        cy += 9
        conteudo.blit(fontes["rotulo"].render(rotulo.upper(), True, cor), (x, cy))
        cy += 20
        altura_texto = max(42, len(_linhas_wrap(texto, fontes["texto"], rect.w - 48)) * (fontes["texto"].get_linesize() + 1))
        cy = _desenhar_texto_wrap(
            conteudo,
            texto,
            pygame.Rect(x, cy, rect.w - 48, altura_texto),
            fontes["texto"],
            (210, 225, 236),
            1,
        )
        cy += 12

    max_scroll = max(0.0, float(cy - conteudo_visivel_h + 8))
    scroll_y = max(0.0, min(max_scroll, float(scroll_y)))
    surf.blit(conteudo, (0, conteudo_top), pygame.Rect(0, int(scroll_y), rect.w, conteudo_visivel_h))

    if max_scroll > 0:
        trilho = pygame.Rect(rect.w - 13, conteudo_top + 4, 4, conteudo_visivel_h - 8)
        pygame.draw.rect(surf, (0, 0, 0, 135), trilho, border_radius=3)
        thumb_h = max(28, int(trilho.h * conteudo_visivel_h / max(1, cy)))
        thumb_y = trilho.y + int((trilho.h - thumb_h) * (scroll_y / max_scroll))
        pygame.draw.rect(surf, (*cor[:3], 210), (trilho.x, thumb_y, trilho.w, thumb_h), border_radius=3)

    tela.blit(surf, rect.topleft)
    return max_scroll


def _desenhar_preview_em_preparo(tela, rect, fontes, dados):
    cor = dados.get("cor", (120, 130, 150))
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (7, 9, 18, 230), (0, 0, rect.w, rect.h), border_radius=8)
    pygame.draw.rect(surf, (*cor[:3], 115), (0, 0, rect.w, rect.h), 1, border_radius=8)
    pygame.draw.rect(surf, (255, 255, 255, 16), (8, 8, rect.w - 16, rect.h - 16), 1, border_radius=6)
    surf.blit(fontes["rotulo"].render("LEITURA TÁTICA", True, cor), (20, 16))

    centro = (rect.w // 2, rect.h // 2 + 4)
    trilho = pygame.Rect(48, centro[1] - 22, rect.w - 96, 44)
    pygame.draw.rect(surf, (0, 0, 0, 80), trilho, border_radius=6)
    pygame.draw.line(surf, (*cor[:3], 145), (trilho.left + 14, centro[1]), (trilho.right - 14, centro[1]), 2)
    for i in range(5):
        x = trilho.left + 26 + i * max(1, (trilho.w - 52) // 4)
        pygame.draw.circle(surf, (*cor[:3], 150), (x, centro[1]), 5)
        pygame.draw.circle(surf, (230, 245, 250, 210), (x, centro[1]), 2)

    icone = _carregar_icone_manifestacao(dados.get("icone", ""), 70)
    pygame.draw.circle(surf, (0, 0, 0, 120), centro, 45)
    pygame.draw.circle(surf, (*cor[:3], 150), centro, 45, 2)
    surf.blit(icone, icone.get_rect(center=centro))

    resumo = dados.get("funcao", "Forma em leitura.")
    linhas = _linhas_wrap(resumo, fontes["texto"], rect.w - 56)[:2]
    y = rect.h - 52
    for linha in linhas:
        txt = fontes["texto"].render(linha, True, (190, 212, 220))
        surf.blit(txt, txt.get_rect(center=(rect.w // 2, y)))
        y += fontes["texto"].get_linesize()
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
    manifestacoes = [
        (chave, dados)
        for chave, dados in obter_manifestacoes()
        if dados.get("desbloqueada", False) or dados.get("icone")
    ]
    manifestacao_salva = obter_manifestacao_ativa()
    selecionado = 0
    for i, (chave, _) in enumerate(manifestacoes):
        if chave == manifestacao_salva:
            selecionado = i
            break
    entrada_inicio = pygame.time.get_ticks()
    troca_inicio = entrada_inicio
    modo_interacao = "teclado"
    colunas = 3
    analogo_x_movido = False
    analogo_y_movido = False

    # Carrega os frames do preview de vídeo para as manifestações encontradas.
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
        for _ in range(36)
    ]

    painel_rect = pygame.Rect(largura - 438, 160, 392, 430)
    preview_rect = pygame.Rect(48, altura - 244, min(560, largura - 520), 190)
    grade_rect = pygame.Rect(52, 175, max(420, largura - 560), max(300, altura - 470))
    slot_w = min(150, max(112, (grade_rect.w - 56) // colunas))
    slot_h = 118
    gap_x = 28
    gap_y = 24
    folga_final_grade = 88
    margem_visivel_grade = 48
    matriz_w = colunas * slot_w + (colunas - 1) * gap_x
    inicio_x = grade_rect.x + max(0, (grade_rect.w - matriz_w) // 2)
    inicio_y = grade_rect.y + 12
    total_linhas = (len(manifestacoes) + colunas - 1) // colunas
    conteudo_h = total_linhas * slot_h + max(0, total_linhas - 1) * gap_y + folga_final_grade
    scroll_y = 0.0
    painel_scroll_y = 0.0
    painel_scroll_max = 0.0

    def max_scroll():
        return max(0.0, float(conteudo_h - grade_rect.h))

    def limitar_scroll(valor):
        return max(0.0, min(max_scroll(), float(valor)))

    def garantir_selecionado_visivel():
        nonlocal scroll_y
        linha = selecionado // colunas
        y_slot = linha * (slot_h + gap_y)
        margem = margem_visivel_grade
        if y_slot < scroll_y + margem:
            scroll_y = limitar_scroll(y_slot - margem)
        elif y_slot + slot_h > scroll_y + grade_rect.h - margem:
            scroll_y = limitar_scroll(y_slot + slot_h - grade_rect.h + margem)

    garantir_selecionado_visivel()

    def mover_para(novo_indice):
        nonlocal selecionado, troca_inicio, painel_scroll_y
        if not manifestacoes:
            return
        novo_indice = max(0, min(len(manifestacoes) - 1, int(novo_indice)))
        if novo_indice == selecionado:
            return
        selecionado = novo_indice
        garantir_selecionado_visivel()
        painel_scroll_y = 0.0
        troca_inicio = pygame.time.get_ticks()
        tocar_hover()

    def indice_na_grade(linha, coluna):
        total = len(manifestacoes)
        if total <= 0:
            return 0
        total_linhas = (total + colunas - 1) // colunas
        linha = max(0, min(total_linhas - 1, int(linha)))
        inicio = linha * colunas
        fim = min(inicio + colunas, total) - 1
        return max(inicio, min(fim, inicio + int(coluna)))

    def mover_linear(delta):
        if manifestacoes:
            mover_para((selecionado + delta) % len(manifestacoes))

    def mover_grade(delta_coluna=0, delta_linha=0):
        if not manifestacoes:
            return
        linha_atual = selecionado // colunas
        coluna_atual = selecionado % colunas
        total_linhas = (len(manifestacoes) + colunas - 1) // colunas
        nova_linha = linha_atual + int(delta_linha)
        if delta_linha and (nova_linha < 0 or nova_linha >= total_linhas):
            return
        if delta_linha:
            mover_para(indice_na_grade(nova_linha, coluna_atual))
            return
        nova_coluna = coluna_atual + int(delta_coluna)
        inicio_linha = linha_atual * colunas
        fim_linha = min(inicio_linha + colunas, len(manifestacoes))
        quantidade_linha = max(1, fim_linha - inicio_linha)
        if nova_coluna < 0 or nova_coluna >= quantidade_linha:
            return
        mover_para(indice_na_grade(linha_atual, nova_coluna))

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
            elif evento.type == pygame.MOUSEWHEEL:
                modo_interacao = "mouse"
                if grade_rect.collidepoint(mx, my):
                    scroll_y = limitar_scroll(scroll_y - evento.y * 46)
                elif painel_rect.collidepoint(mx, my):
                    painel_scroll_y = max(0.0, min(painel_scroll_max, painel_scroll_y - evento.y * 42))
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button in (4, 5):
                modo_interacao = "mouse"
                if grade_rect.collidepoint(mx, my):
                    direcao_scroll = -1 if evento.button == 4 else 1
                    scroll_y = limitar_scroll(scroll_y + direcao_scroll * 46)
                elif painel_rect.collidepoint(mx, my):
                    direcao_scroll = -1 if evento.button == 4 else 1
                    painel_scroll_y = max(0.0, min(painel_scroll_max, painel_scroll_y + direcao_scroll * 42))
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                modo_interacao = "mouse"
                clicado = True
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    return "voltar"
                if evento.key in (pygame.K_RIGHT, pygame.K_d):
                    mover_grade(delta_coluna=1)
                elif evento.key in (pygame.K_LEFT, pygame.K_a):
                    mover_grade(delta_coluna=-1)
                elif evento.key in (pygame.K_DOWN, pygame.K_s):
                    mover_grade(delta_linha=1)
                elif evento.key in (pygame.K_UP, pygame.K_w):
                    mover_grade(delta_linha=-1)
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    resultado = confirmar()
                    if resultado:
                        return resultado
            elif evento.type == pygame.JOYAXISMOTION:
                modo_interacao = "teclado"
                if evento.axis == 0:
                    if evento.value > 0.55 and not analogo_x_movido:
                        mover_grade(delta_coluna=1)
                        analogo_x_movido = True
                    elif evento.value < -0.55 and not analogo_x_movido:
                        mover_grade(delta_coluna=-1)
                        analogo_x_movido = True
                    elif abs(evento.value) < 0.25:
                        analogo_x_movido = False
                elif evento.axis == 1:
                    if evento.value > 0.55 and not analogo_y_movido:
                        mover_grade(delta_linha=1)
                        analogo_y_movido = True
                    elif evento.value < -0.55 and not analogo_y_movido:
                        mover_grade(delta_linha=-1)
                        analogo_y_movido = True
                    elif abs(evento.value) < 0.25:
                        analogo_y_movido = False
            elif evento.type == pygame.JOYHATMOTION:
                dx, dy = evento.value
                if dx > 0:
                    mover_grade(delta_coluna=1)
                elif dx < 0:
                    mover_grade(delta_coluna=-1)
                elif dy > 0:
                    mover_grade(delta_linha=-1)
                elif dy < 0:
                    mover_grade(delta_linha=1)
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

        titulo_grade = fontes["rotulo"].render("MATRIZ DE MANIFESTAÇÕES", True, (0, 225, 255))
        tela.blit(titulo_grade, (grade_rect.x + 4, grade_rect.y - 30))
        pygame.draw.rect(tela, (0, 0, 0, 42), grade_rect, border_radius=8)
        pygame.draw.rect(tela, (0, 225, 255, 42), grade_rect, 1, border_radius=8)
        icone_rects = []
        clip_anterior = tela.get_clip()
        tela.set_clip(grade_rect)
        for i, (chave, dados) in enumerate(manifestacoes):
            atraso = i * 0.14
            entrada_icone = min(1.0, max(0.0, (entrada - atraso) / 0.42))
            coluna = i % colunas
            linha = i // colunas
            rect = pygame.Rect(
                inicio_x + coluna * (slot_w + gap_x),
                inicio_y + linha * (slot_h + gap_y) - int(scroll_y),
                slot_w,
                slot_h,
            )
            icone_rects.append(rect)
            if entrada_icone <= 0:
                continue
            if rect.bottom < grade_rect.top or rect.top > grade_rect.bottom:
                continue
            _desenhar_slot_matriz(tela, rect, dados, i == selecionado, dados.get("desbloqueada", False), agora, entrada_icone, fontes)
        tela.set_clip(clip_anterior)

        if max_scroll() > 0:
            trilho = pygame.Rect(grade_rect.right - 8, grade_rect.y + 8, 4, grade_rect.h - 16)
            pygame.draw.rect(tela, (0, 0, 0, 120), trilho, border_radius=3)
            thumb_h = max(30, int(trilho.h * grade_rect.h / max(1, conteudo_h)))
            thumb_y = trilho.y + int((trilho.h - thumb_h) * (scroll_y / max_scroll()))
            pygame.draw.rect(tela, (0, 225, 255), (trilho.x, thumb_y, trilho.w, thumb_h), border_radius=3)

        if clicado:
            for i, rect in enumerate(icone_rects):
                if grade_rect.collidepoint(mx, my) and rect.collidepoint(mx, my):
                    if i != selecionado:
                        selecionado = i
                        painel_scroll_y = 0.0
                        garantir_selecionado_visivel()
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
        painel_scroll_max = _desenhar_painel_rolavel(tela, painel_rect, dados_sel, desbloqueada, fontes, fade_painel, painel_scroll_y)
        painel_scroll_y = max(0.0, min(painel_scroll_max, painel_scroll_y))
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

        rodape = "WASD ou setas navegam na matriz  |  ENTER manifesta  |  Mouse seleciona"
        if modo_interacao == "mouse":
            rodape = "Clique no ícone para selecionar, clique em Manifestar para confirmar"
        txt_rodape = fontes["pequena"].render(rodape, True, (115, 165, 185))
        tela.blit(txt_rodape, txt_rodape.get_rect(center=(largura // 2, altura - 22)))

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)


def _texto_detalhado_manifestacao(dados, desbloqueada):
    if not desbloqueada:
        return [
            ("ECO NAO ESTABILIZADO", "Geovana ainda nao estabilizou essa forma de combate."),
        ]
    itens = [
        ("ESTILO DE JOGO", "A manifestacao e sua arma e seu jeito de jogar. Ela muda o ataque basico, a habilidade e a forma como Geovana resolve a luta."),
        ("IDENTIDADE", dados.get("descricao_curta") or dados.get("frase") or ""),
        ("FUNCAO", dados.get("funcao", "")),
        ("DISPARO", dados.get("disparo", "")),
        ("HABILIDADE", f"{dados.get('habilidade', '')}: {dados.get('descricao_habilidade', '')}"),
    ]
    if dados.get("teleporte"):
        itens.append(("TELEPORTE", dados.get("teleporte", "")))
    itens.extend([
        ("FORTE EM", dados.get("traco", "")),
        ("CUIDADO", dados.get("risco", "")),
    ])
    return [(rotulo, texto) for rotulo, texto in itens if texto]


def _desenhar_botao_manifestacao(tela, rect, texto, fonte, cor, ativo=True, hover=False):
    bg = (8, 13, 24) if ativo else (18, 20, 28)
    borda = cor if ativo else (88, 94, 108)
    if hover and ativo:
        bg = tuple(min(255, int(c * 1.35 + 10)) for c in bg)
    pygame.draw.rect(tela, bg, rect, border_radius=8)
    pygame.draw.rect(tela, borda, rect, 2 if hover and ativo else 1, border_radius=8)
    txt = fonte.render(texto, True, (230, 255, 255) if ativo else (145, 150, 160))
    tela.blit(txt, txt.get_rect(center=rect.center))


def _desenhar_card_carrossel(tela, rect, dados, selecionado, desbloqueada, agora, fontes):
    cor = dados.get("cor", (0, 225, 255)) if desbloqueada else (90, 98, 114)
    cor2 = dados.get("cor_secundaria", cor) if desbloqueada else (50, 55, 70)
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    alpha = 235 if selecionado else 150
    pygame.draw.rect(surf, (4, 7, 16, alpha), (0, 0, rect.w, rect.h), border_radius=10)
    pygame.draw.rect(surf, (*cor[:3], 230 if selecionado else 90), (0, 0, rect.w, rect.h), 2 if selecionado else 1, border_radius=10)

    if selecionado and desbloqueada:
        pulso = 0.5 + 0.5 * math.sin(agora * 0.006)
        pygame.draw.rect(surf, (*cor[:3], int(28 + pulso * 28)), (8, 8, rect.w - 16, rect.h - 16), border_radius=8)
        pygame.draw.line(surf, (*cor2[:3], 150), (18, 18), (rect.w - 18, 18), 1)
        pygame.draw.line(surf, (*cor2[:3], 90), (18, rect.h - 18), (rect.w - 18, rect.h - 18), 1)

    status = "ENCONTRADA" if desbloqueada else "BLOQUEADA"
    badge = pygame.Rect(rect.w // 2 - 56, 16, 112, 24)
    pygame.draw.rect(surf, (*cor[:3], 34), badge, border_radius=5)
    pygame.draw.rect(surf, (*cor[:3], 128), badge, 1, border_radius=5)
    surf.blit(fontes["pequena"].render(status, True, (220, 245, 250) if desbloqueada else (130, 138, 152)), (badge.x + 10, badge.y + 4))

    icone_tam = 106 if selecionado else 88
    icone = _carregar_icone_manifestacao(dados.get("icone", ""), icone_tam)
    centro = (rect.w // 2, rect.h // 2 - 10)
    pygame.draw.circle(surf, (0, 0, 0, 120), centro, icone_tam // 2 + 14)
    pygame.draw.circle(surf, (*cor[:3], 170 if selecionado else 85), centro, icone_tam // 2 + 14, 2)
    if selecionado:
        for i in range(8):
            ang = agora * 0.003 + i * math.tau / 8
            p1 = (centro[0] + int(math.cos(ang) * (icone_tam // 2 + 22)), centro[1] + int(math.sin(ang) * (icone_tam // 2 + 22)))
            p2 = (centro[0] + int(math.cos(ang) * (icone_tam // 2 + 31)), centro[1] + int(math.sin(ang) * (icone_tam // 2 + 31)))
            pygame.draw.line(surf, (*cor2[:3], 110), p1, p2, 1)
    surf.blit(icone, icone.get_rect(center=centro))

    nome = _nome_curto_manifestacao(dados)
    fonte_nome = fontes["nome_card"] if fontes["nome_card"].size(nome)[0] <= rect.w - 26 else fontes["rotulo"]
    txt = fonte_nome.render(nome, True, (235, 255, 255) if desbloqueada else (150, 156, 170))
    surf.blit(txt, txt.get_rect(center=(rect.w // 2, rect.h - 32)))
    tela.blit(surf, rect.topleft)


def _desenhar_popup_descricao_manifestacao(tela, rect, dados, desbloqueada, fontes, agora, frames_previews, chave, scroll_y):
    cor = dados.get("cor", (0, 225, 255)) if desbloqueada else (92, 102, 122)
    overlay = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 178))
    tela.blit(overlay, (0, 0))

    pygame.draw.rect(tela, (5, 8, 17), rect, border_radius=10)
    pygame.draw.rect(tela, cor, rect, 2, border_radius=10)
    pygame.draw.rect(tela, (255, 255, 255, 20), rect.inflate(-14, -14), 1, border_radius=8)

    titulo = dados.get("nome", "Manifestacao") if desbloqueada else "Manifestacao nao estabilizada"
    tela.blit(fontes["nome"].render(titulo, True, (230, 255, 255)), (rect.x + 24, rect.y + 18))
    subt = fontes["pequena"].render("A manifestacao define sua arma, seu ritmo e seu estilo de jogo.", True, (155, 215, 225))
    tela.blit(subt, (rect.x + 26, rect.y + 58))

    preview_rect = pygame.Rect(rect.x + 24, rect.y + 92, rect.w // 2 - 42, rect.h - 122)
    texto_rect = pygame.Rect(rect.centerx + 18, rect.y + 94, rect.w // 2 - 48, rect.h - 126)
    if desbloqueada and (chave == "eletrica" or frames_previews.get(chave)):
        _desenhar_preview_eletrico(tela, preview_rect, agora, fontes, frames_previews.get(chave))
    elif desbloqueada:
        _desenhar_preview_em_preparo(tela, preview_rect, fontes, dados)
    else:
        _desenhar_preview_bloqueado(tela, preview_rect, fontes)

    conteudo = pygame.Surface((texto_rect.w, 1300), pygame.SRCALPHA)
    y = 0
    for rotulo, texto in _texto_detalhado_manifestacao(dados, desbloqueada):
        pygame.draw.line(conteudo, (255, 255, 255, 28), (0, y), (texto_rect.w - 8, y), 1)
        y += 10
        conteudo.blit(fontes["rotulo"].render(rotulo, True, cor), (0, y))
        y += fontes["rotulo"].get_linesize() + 2
        y = _desenhar_texto_wrap(conteudo, texto, pygame.Rect(0, y, texto_rect.w - 12, 220), fontes["texto"], (210, 225, 236), 1)
        y += 14

    max_scroll = max(0.0, float(y - texto_rect.h))
    scroll_y = max(0.0, min(max_scroll, float(scroll_y)))
    tela.set_clip(texto_rect)
    tela.blit(conteudo, texto_rect.topleft, pygame.Rect(0, int(scroll_y), texto_rect.w, texto_rect.h))
    tela.set_clip(None)
    if max_scroll > 0:
        trilho = pygame.Rect(texto_rect.right - 6, texto_rect.y, 4, texto_rect.h)
        pygame.draw.rect(tela, (0, 0, 0, 120), trilho, border_radius=3)
        thumb_h = max(28, int(trilho.h * texto_rect.h / max(1, y)))
        thumb_y = trilho.y + int((trilho.h - thumb_h) * (scroll_y / max_scroll))
        pygame.draw.rect(tela, cor, (trilho.x, thumb_y, trilho.w, thumb_h), border_radius=3)

    fechar_rect = pygame.Rect(rect.right - 112, rect.y + 18, 82, 32)
    _desenhar_botao_manifestacao(tela, fechar_rect, "Fechar", fontes["pequena"], cor, True, False)
    return max_scroll, fechar_rect


def tela_manifestacoes(tela, fonte_base):
    pygame.mouse.set_visible(False)
    largura, altura = tela.get_size()
    clock = pygame.time.Clock()
    manifestacoes = [
        (chave, dados)
        for chave, dados in obter_manifestacoes()
        if dados.get("desbloqueada", False) or dados.get("icone")
    ]
    manifestacao_salva = obter_manifestacao_ativa()
    selecionado = 0
    for i, (chave, _) in enumerate(manifestacoes):
        if chave == manifestacao_salva:
            selecionado = i
            break

    fontes = {
        "titulo": _fonte("Texto/World.otf", 46, fonte_base),
        "subtitulo": _fonte("Texto/rainyhearts.ttf", 22, fonte_base),
        "nome": _fonte("Texto/rainyhearts.ttf", 36, fonte_base),
        "nome_card": _fonte("Texto/rainyhearts.ttf", 26, fonte_base),
        "rotulo": _fonte("Texto/rainyhearts.ttf", 18, fonte_base),
        "texto": _fonte("Texto/rainyhearts.ttf", 17, fonte_base),
        "botao": _fonte("Texto/rainyhearts.ttf", 24, fonte_base),
        "pequena": _fonte("Texto/rainyhearts.ttf", 15, fonte_base),
    }

    frames_previews = {}
    for chave, dados in manifestacoes:
        if dados.get("desbloqueada", False):
            pasta_video = os.path.join("Video", f"preview_{chave}")
            if os.path.isdir(pasta_video):
                try:
                    arquivos = [f for f in os.listdir(pasta_video) if f.lower().endswith((".png", ".webp", ".jpg", ".jpeg"))]
                    arquivos.sort(key=lambda nome: int(re.findall(r"\d+", nome)[0]) if re.findall(r"\d+", nome) else 0)
                    frames = [pygame.image.load(os.path.join(pasta_video, arq)).convert_alpha() for arq in arquivos]
                    if frames:
                        frames_previews[chave] = frames
                except Exception as e:
                    from qa_logger import registrar_erro
                    registrar_erro(f"Erro ao carregar frames do preview de {chave}", e)

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
        for _ in range(36)
    ]

    modo_interacao = "teclado"
    entrada_inicio = pygame.time.get_ticks()
    troca_inicio = entrada_inicio
    popup_aberto = False
    popup_scroll = 0.0
    popup_scroll_max = 0.0
    analogico_movido = False
    card_x = [largura // 2 for _ in manifestacoes]
    card_scale = [0.84 for _ in manifestacoes]
    card_y_offset = [8.0 for _ in manifestacoes]

    def mover(delta):
        nonlocal selecionado, troca_inicio, popup_scroll
        if not manifestacoes:
            return
        selecionado = (selecionado + int(delta)) % len(manifestacoes)
        troca_inicio = pygame.time.get_ticks()
        popup_scroll = 0.0
        tocar_hover()

    def distancia_circular(indice, centro):
        total = max(1, len(manifestacoes))
        dist = int(indice) - int(centro)
        metade = total / 2.0
        if dist > metade:
            dist -= total
        elif dist < -metade:
            dist += total
        return dist

    def confirmar():
        chave, dados = manifestacoes[selecionado]
        if not dados.get("desbloqueada", False):
            tocar_hover()
            return None
        salvar_manifestacao_ativa(chave)
        tocar_selecionar()
        return "confirmar"

    while True:
        agora = pygame.time.get_ticks()
        entrada = min(1.0, (agora - entrada_inicio) / 650.0)
        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        clicado = False
        popup_fechar_rect = pygame.Rect(0, 0, 0, 0)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if evento.type == pygame.MOUSEMOTION and evento.rel != (0, 0):
                modo_interacao = "mouse"
            elif evento.type == pygame.MOUSEWHEEL:
                modo_interacao = "mouse"
                if popup_aberto:
                    popup_scroll = max(0.0, min(popup_scroll_max, popup_scroll - evento.y * 42))
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                modo_interacao = "mouse"
                clicado = True
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if popup_aberto:
                    if evento.key in (pygame.K_ESCAPE, pygame.K_i, pygame.K_TAB):
                        popup_aberto = False
                        tocar_hover()
                    elif evento.key in (pygame.K_DOWN, pygame.K_s):
                        popup_scroll = max(0.0, min(popup_scroll_max, popup_scroll + 46))
                    elif evento.key in (pygame.K_UP, pygame.K_w):
                        popup_scroll = max(0.0, min(popup_scroll_max, popup_scroll - 46))
                    continue
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
                elif evento.key in (pygame.K_i, pygame.K_TAB):
                    popup_aberto = True
                    popup_scroll = 0.0
                    tocar_hover()
            elif evento.type == pygame.JOYAXISMOTION:
                modo_interacao = "teclado"
                if evento.axis == 0:
                    if evento.value > 0.55 and not analogico_movido and not popup_aberto:
                        mover(1)
                        analogico_movido = True
                    elif evento.value < -0.55 and not analogico_movido and not popup_aberto:
                        mover(-1)
                        analogico_movido = True
                    elif abs(evento.value) < 0.25:
                        analogico_movido = False
            elif evento.type == pygame.JOYBUTTONDOWN:
                modo_interacao = "teclado"
                if popup_aberto:
                    popup_aberto = False
                    continue
                if evento.button == 0:
                    resultado = confirmar()
                    if resultado:
                        return resultado
                elif evento.button == 1:
                    tocar_selecionar()
                    return "voltar"
                elif evento.button in (2, 3):
                    popup_aberto = True
                    popup_scroll = 0.0

        chave_preview, dados_preview = manifestacoes[selecionado]
        cor_preview = dados_preview.get("cor", (0, 225, 255)) if dados_preview.get("desbloqueada", False) else (80, 100, 120)
        ui_helpers.desenhar_fundo_menu_ruptura(tela, agora, particulas, (5, 8, 17), cor_preview, 0.95)
        ui_helpers.desenhar_cabecalho_menu(
            tela,
            "MANIFESTACOES",
            "Sua manifestacao e sua arma: escolha o estilo de jogo de Geovana.",
            fontes["titulo"],
            fontes["subtitulo"],
            cor_preview,
            y=80,
        )

        centro_x = largura // 2
        centro_y = int(altura * 0.44)
        espacamento = 242
        base_card_w = 172
        base_card_h = 226
        for i, _item in enumerate(manifestacoes):
            dist_circular = distancia_circular(i, selecionado)
            target_x = centro_x + dist_circular * espacamento
            if i == selecionado:
                target_scale = 1.34
                target_y_offset = -10.0
            else:
                target_scale = 0.84
                target_y_offset = 8.0
            card_x[i] += (target_x - card_x[i]) * 0.12
            card_scale[i] += (target_scale - card_scale[i]) * 0.12
            card_y_offset[i] += (target_y_offset - card_y_offset[i]) * 0.12

        card_rects = []
        for i, (chave, dados) in enumerate(manifestacoes):
            x = card_x[i]
            dist = abs(x - centro_x)
            if dist > largura * 0.72:
                continue
            w = int(base_card_w * card_scale[i])
            h = int(base_card_h * card_scale[i])
            rect = pygame.Rect(int(x - w // 2), int(centro_y - h // 2 + card_y_offset[i]), w, h)
            card_rects.append((i, rect))
            _desenhar_card_carrossel(tela, rect, dados, i == selecionado, dados.get("desbloqueada", False), agora, fontes)

        if clicado and not popup_aberto:
            for i, rect in card_rects:
                if rect.collidepoint(mx, my):
                    if i == selecionado:
                        resultado = confirmar()
                        if resultado:
                            return resultado
                    else:
                        dist_click = distancia_circular(i, selecionado)
                        if dist_click > 0:
                            selecionado = (selecionado + 1) % len(manifestacoes)
                        elif dist_click < 0:
                            selecionado = (selecionado - 1) % len(manifestacoes)
                        troca_inicio = pygame.time.get_ticks()
                        popup_scroll = 0.0
                        tocar_hover()
                    break

        chave_sel, dados_sel = manifestacoes[selecionado]
        desbloqueada = dados_sel.get("desbloqueada", False)
        cor = dados_sel.get("cor", (0, 225, 255)) if desbloqueada else (90, 98, 114)
        resumo_rect = pygame.Rect(max(80, largura // 2 - 430), int(altura * 0.68), min(860, largura - 160), 86)
        pygame.draw.rect(tela, (5, 8, 17, 205), resumo_rect, border_radius=8)
        pygame.draw.rect(tela, cor, resumo_rect, 1, border_radius=8)
        frase = dados_sel.get("funcao") if desbloqueada else dados_sel.get("missao_desbloqueio", "Forma futura ainda nao estabilizada.")
        _desenhar_texto_wrap(tela, frase, pygame.Rect(resumo_rect.x + 22, resumo_rect.y + 16, resumo_rect.w - 44, 48), fontes["texto"], (205, 228, 238), 1)

        btn_w = 178
        manifestar_rect = pygame.Rect(largura // 2 - btn_w - 12, resumo_rect.bottom + 18, btn_w, 42)
        desc_rect = pygame.Rect(largura // 2 + 12, resumo_rect.bottom + 18, btn_w, 42)
        hover_manifestar = modo_interacao == "mouse" and manifestar_rect.collidepoint(mx, my)
        hover_desc = modo_interacao == "mouse" and desc_rect.collidepoint(mx, my)
        _desenhar_botao_manifestacao(tela, manifestar_rect, "Manifestar", fontes["botao"], cor, desbloqueada, hover_manifestar)
        _desenhar_botao_manifestacao(tela, desc_rect, "Descricao", fontes["botao"], cor, True, hover_desc)
        if clicado and not popup_aberto:
            if manifestar_rect.collidepoint(mx, my):
                resultado = confirmar()
                if resultado:
                    return resultado
            elif desc_rect.collidepoint(mx, my):
                popup_aberto = True
                popup_scroll = 0.0
                tocar_hover()

        voltar_rect = pygame.Rect(40, 34, 118, 36)
        ui_helpers.desenhar_botao_voltar_menu(tela, voltar_rect, fontes["pequena"], modo_interacao == "mouse" and voltar_rect.collidepoint(mx, my), cor, "ESC Voltar")
        if clicado and not popup_aberto and voltar_rect.collidepoint(mx, my):
            tocar_selecionar()
            return "voltar"

        if popup_aberto:
            popup_rect = pygame.Rect(max(42, largura // 2 - 480), max(70, altura // 2 - 285), min(960, largura - 84), min(570, altura - 116))
            popup_scroll_max, popup_fechar_rect = _desenhar_popup_descricao_manifestacao(
                tela, popup_rect, dados_sel, desbloqueada, fontes, agora - troca_inicio, frames_previews, chave_sel, popup_scroll
            )
            if clicado:
                if popup_fechar_rect.collidepoint(mx, my):
                    popup_aberto = False
                    tocar_hover()
                elif not popup_rect.collidepoint(mx, my):
                    popup_aberto = False
                    tocar_hover()

        rodape = "A/D ou setas navegam  |  ENTER manifesta  |  TAB abre descricao"
        if modo_interacao == "mouse":
            rodape = "Clique em uma manifestacao, Manifestar confirma, Descricao abre detalhes"
        ui_helpers.desenhar_rodape_menu(tela, rodape, fontes["pequena"], cor, altura - 22)

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)
