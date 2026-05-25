# -*- coding: utf-8 -*-
import pygame
import os
import math
import random

_font_cache = {}

def get_cached_font(caminho, tamanho):
    key = (caminho, tamanho)
    if key not in _font_cache:
        if caminho and os.path.exists(caminho):
            _font_cache[key] = pygame.font.Font(caminho, tamanho)
        else:
            _font_cache[key] = pygame.font.Font(None, tamanho)
    return _font_cache[key]

def carregar_fontes():
    fontes = {}
    caminho_glitch = 'Texto/Doctor Glitch.otf'
    caminho_hearts = 'Texto/rainyhearts.ttf'
    caminho_broken = 'Texto/Broken.otf'
    caminho_world = 'Texto/World.otf'

    # Carrega fontes com fallback
    if os.path.exists(caminho_glitch):
        fontes["titulo_path"] = caminho_glitch
    elif os.path.exists(caminho_broken):
        fontes["titulo_path"] = caminho_broken
    else:
        fontes["titulo_path"] = None

    if os.path.exists(caminho_hearts):
        fontes["texto_path"] = caminho_hearts
    elif os.path.exists(caminho_world):
        fontes["texto_path"] = caminho_world
    else:
        fontes["texto_path"] = None
        
    return fontes

def carregar_imagens_aureas(dados, card_width, card_height):
    imagens = {}
    for d in dados:
        try:
            img = pygame.image.load(d["imagem_path"]).convert_alpha()
        except Exception:
            # Fallback a solid color with outline
            img = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
            img.fill((d["cor"][0], d["cor"][1], d["cor"][2], 100))
            pygame.draw.rect(img, d["cor"], (0, 0, card_width, card_height), 4)
        imagens[d["id"]] = img
    return imagens

def desenhar_texto_wrap(tela, texto, rect, fonte, cor):
    palavras = texto.split(' ')
    linhas = []
    linha_atual = []
    
    for palavra in palavras:
        test_line = " ".join(linha_atual + [palavra])
        if fonte.size(test_line)[0] <= rect.width:
            linha_atual.append(palavra)
        else:
            linhas.append(" ".join(linha_atual))
            linha_atual = [palavra]
    if linha_atual:
        linhas.append(" ".join(linha_atual))
        
    y_offset = rect.top
    line_height = fonte.get_linesize()
    
    for i, linha in enumerate(linhas):
        if y_offset + line_height > rect.bottom:
            break
        
        # If this is the last line we can fit and there are more lines left, append '...'
        if y_offset + 2 * line_height > rect.bottom and i < len(linhas) - 1:
            line_with_dots = linha + "..."
            while line_with_dots and fonte.size(line_with_dots)[0] > rect.width:
                if len(linha) > 0:
                    linha = linha[:-1]
                    line_with_dots = linha + "..."
                else:
                    break
            linha = line_with_dots
            
        txt_surf = fonte.render(linha, True, cor)
        tela.blit(txt_surf, (rect.left, y_offset))
        y_offset += line_height

def renderizar_titulo(tela, texto, max_width, rect, fonte_caminho, tamanho_base, cor):
    tamanho_atual = tamanho_base
    fonte = get_cached_font(fonte_caminho, tamanho_atual)
    
    # Try scaling down until it fits
    while fonte.size(texto)[0] > max_width and tamanho_atual > 20:
        tamanho_atual -= 2
        fonte = get_cached_font(fonte_caminho, tamanho_atual)
        
    # If it still doesn't fit, use short title
    if fonte.size(texto)[0] > max_width:
        texto = "NUCLEO DE EVOLUCAO"
        tamanho_atual = tamanho_base
        fonte = get_cached_font(fonte_caminho, tamanho_atual)
        while fonte.size(texto)[0] > max_width and tamanho_atual > 16:
            tamanho_atual -= 2
            fonte = get_cached_font(fonte_caminho, tamanho_atual)
            
    txt_surf = fonte.render(texto, True, cor)
    tela.blit(txt_surf, (rect.left, rect.top))

def desenhar_painel_glassmorphic(tela, rect, cor_borda, alpha_fundo=215):
    # Fundo do painel
    panel_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    panel_surf.fill((8, 6, 16, alpha_fundo)) # glassmorphic escuro
    
    # Bordas brilhantes com a cor da aura selecionada
    pygame.draw.rect(panel_surf, (cor_borda[0], cor_borda[1], cor_borda[2], 120), (0, 0, rect.width, rect.height), width=2, border_radius=12)
    pygame.draw.rect(panel_surf, (255, 255, 255, 40), (1, 1, rect.width - 2, rect.height - 2), width=1, border_radius=12)
    
    # Divisória vertical no centro
    pygame.draw.line(panel_surf, (cor_borda[0], cor_borda[1], cor_borda[2], 60), (rect.width // 2, 20), (rect.width // 2, rect.height - 20), 1)
    
    tela.blit(panel_surf, (rect.left, rect.top))

def desenhar_barra_progresso(tela, rect, nivel, max_nivel, cor):
    pygame.draw.rect(tela, (30, 30, 40), (rect.left, rect.top, rect.width, rect.height), border_radius=4)
    p_progresso = nivel / max_nivel
    if p_progresso > 0:
        pygame.draw.rect(tela, cor, (rect.left, rect.top, int(rect.width * p_progresso), rect.height), border_radius=4)
        # Brilho
        pygame.draw.rect(tela, (255, 255, 255, 80), (rect.left, rect.top, int(rect.width * p_progresso), max(1, rect.height // 3)), border_radius=2)

def desenhar_painel_fragmentos(tela, rect, fragmentos, fonte, cor_tema):
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    panel.fill((10, 8, 20, 180))
    pygame.draw.rect(panel, (cor_tema[0], cor_tema[1], cor_tema[2], 100), (0, 0, rect.width, rect.height), width=1, border_radius=8)
    tela.blit(panel, (rect.left, rect.top))
    
    # Desenhar pequeno símbolo de fragmento (losango neon)
    pygame.draw.polygon(tela, cor_tema, [
        (rect.left + 25, rect.top + 15),
        (rect.left + 35, rect.top + 25),
        (rect.left + 25, rect.top + 35),
        (rect.left + 15, rect.top + 25)
    ])
    
    txt_moedas = fonte.render(f"Fragmentos: {fragmentos}", True, (255, 255, 255))
    tela.blit(txt_moedas, (rect.left + 48, rect.top + (rect.height - txt_moedas.get_height()) // 2))

class Particle:
    def __init__(self, x, y, color, style="normal"):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        if style == "impulsiva":
            self.vx = random.uniform(-4, 4)
            self.vy = random.uniform(-4, 4)
            self.life = random.randint(15, 35)
        elif style == "racional":
            # Direções mais retas e ortogonais
            angles = [0, 90, 180, 270]
            angle = math.radians(random.choice(angles) + random.uniform(-5, 5))
            speed = random.uniform(1.5, 3)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
            self.life = random.randint(20, 45)
        else:
            self.life = random.randint(25, 50)
            
        self.max_life = self.life
        self.color = list(color)
        self.size = random.uniform(2, 5)
        self.style = style

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.style == "vanguarda":
            self.vy -= 0.05  # sobe como brasa
            
    def draw(self, surface):
        alpha = int((self.life / self.max_life) * 255)
        p_color = (self.color[0], self.color[1], self.color[2], alpha)
        
        # Desenhar com transparência
        surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        if self.style == "racional":
            pygame.draw.rect(surf, p_color, (0, 0, self.size, self.size))
        else:
            pygame.draw.circle(surf, p_color, (int(self.size), int(self.size)), int(self.size))
        surface.blit(surf, (int(self.x - self.size), int(self.y - self.size)))

class OrbitalParticle:
    def __init__(self, cx, cy, color, style="normal"):
        self.cx = cx
        self.cy = cy
        self.radius = random.uniform(120, 220)
        self.angle = random.uniform(0, math.pi * 2)
        self.speed = random.uniform(0.01, 0.04)
        if style == "impulsiva":
            self.speed = random.uniform(0.03, 0.07)
        self.color = color
        self.life = random.randint(40, 80)
        self.max_life = self.life
        self.size = random.uniform(1.5, 3.5)
        self.style = style

    def update(self, cx, cy):
        self.cx = cx
        self.cy = cy
        self.angle += self.speed
        self.radius -= 0.8
        if self.radius < 20:
            self.radius = random.uniform(140, 220)
        self.life -= 1

    def draw(self, surface):
        alpha = int((self.life / self.max_life) * 200)
        p_color = (self.color[0], self.color[1], self.color[2], alpha)
        
        x = self.cx + self.radius * math.cos(self.angle)
        y = self.cy + self.radius * math.sin(self.angle)
        
        surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, p_color, (int(self.size), int(self.size)), int(self.size))
        surface.blit(surf, (int(x - self.size), int(y - self.size)))

class FloatingText:
    def __init__(self, x, y, text, color, font):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.font = font
        self.life = 60
        self.max_life = 60

    def update(self):
        self.y -= 1.2
        self.life -= 1

    def draw(self, surface):
        alpha = int((self.life / self.max_life) * 255)
        text_surf = self.font.render(self.text, True, self.color)
        
        alpha_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        alpha_surf.blit(text_surf, (0, 0))
        
        overlay = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 255 - alpha))
        alpha_surf.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        sombra = self.font.render(self.text, True, (0, 0, 0))
        sombra_surf = pygame.Surface(sombra.get_size(), pygame.SRCALPHA)
        sombra_surf.blit(sombra, (0, 0))
        sombra_surf.fill((0, 0, 0, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        
        surface.blit(sombra_surf, (self.x - sombra.get_width() // 2 + 1, self.y + 1))
        
        text_surf_with_alpha = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        text_surf_with_alpha.blit(text_surf, (0, 0))
        text_surf_with_alpha.fill((self.color[0], self.color[1], self.color[2], alpha), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(text_surf_with_alpha, (self.x - text_surf.get_width() // 2, self.y))
