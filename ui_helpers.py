# -*- coding: utf-8 -*-
import pygame
import os
import math
import random

_font_cache = {}
_stage = {
    "active": False,
    "display": None,
    "game_surface": None,
    "game_size": (0, 0),
    "dst_rect": pygame.Rect(0, 0, 0, 0),
    "hud": None,
    "orig_flip": None,
}

def get_cached_font(caminho, tamanho):
    key = (caminho, tamanho)
    if key not in _font_cache:
        if caminho and os.path.exists(caminho):
            _font_cache[key] = pygame.font.Font(caminho, tamanho)
        else:
            _font_cache[key] = pygame.font.Font(None, tamanho)
    return _font_cache[key]

def palco_ativo():
    return bool(_stage["active"])

def obter_superficie_palco():
    return _stage["game_surface"] if _stage["active"] else pygame.display.get_surface()

def obter_pos_mouse_jogo():
    mx, my = pygame.mouse.get_pos()
    if not _stage["active"]:
        return mx, my
    rect = _stage["dst_rect"]
    if rect.width <= 0 or rect.height <= 0:
        return mx, my
    game_w, game_h = _stage["game_size"]
    gx = (mx - rect.x) * game_w / rect.width
    gy = (my - rect.y) * game_h / rect.height
    return int(max(0, min(game_w - 1, gx))), int(max(0, min(game_h - 1, gy)))

def ativar_palco_fullscreen(largura_jogo, altura_jogo):
    if _stage["orig_flip"] is None:
        _stage["orig_flip"] = pygame.display.flip

    display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    screen_w, screen_h = display.get_size()
    escala = min(screen_w / largura_jogo, screen_h / altura_jogo)
    dst_w = max(1, int(largura_jogo * escala))
    dst_h = max(1, int(altura_jogo * escala))
    dst_rect = pygame.Rect((screen_w - dst_w) // 2, (screen_h - dst_h) // 2, dst_w, dst_h)

    _stage.update({
        "active": True,
        "display": display,
        "game_surface": pygame.Surface((largura_jogo, altura_jogo)).convert(),
        "game_size": (largura_jogo, altura_jogo),
        "dst_rect": dst_rect,
        "hud": None,
    })
    pygame.display.flip = _flip_palco
    return _stage["game_surface"]

def desativar_palco():
    if _stage["orig_flip"] is not None:
        pygame.display.flip = _stage["orig_flip"]
    _stage.update({
        "active": False,
        "display": None,
        "game_surface": None,
        "game_size": (0, 0),
        "dst_rect": pygame.Rect(0, 0, 0, 0),
        "hud": None,
    })

def _texto_contorno(surface, fonte, texto, cor, pos):
    sombra = fonte.render(str(texto), True, (0, 0, 0))
    base = fonte.render(str(texto), True, cor)
    x, y = pos
    surface.blit(sombra, (x - 1, y))
    surface.blit(sombra, (x + 1, y))
    surface.blit(sombra, (x, y - 1))
    surface.blit(sombra, (x, y + 1))
    surface.blit(base, (x, y))

def _desenhar_moldura(surface, rect, lado):
    if rect.width <= 0 or rect.height <= 0:
        return
    painel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    painel.fill((8, 7, 16, 255))
    tempo = pygame.time.get_ticks() * 0.001
    for y in range(-40, rect.height + 40, 40):
        yy = int((y + tempo * 18) % (rect.height + 40) - 20)
        pygame.draw.line(painel, (0, 180, 200, 22), (0, yy), (rect.width, yy), 1)
    for x in range(0, rect.width, 40):
        pygame.draw.line(painel, (0, 180, 200, 15), (x, 0), (x, rect.height), 1)
    borda_x = rect.width - 4 if lado == "esquerda" else 0
    pygame.draw.line(painel, (0, 255, 220), (borda_x, 0), (borda_x, rect.height), 4)
    pygame.draw.line(painel, (255, 255, 255, 30), (borda_x + (1 if lado == "direita" else -1), 0), (borda_x + (1 if lado == "direita" else -1), rect.height), 1)
    surface.blit(painel, rect.topleft)

def _desenhar_barra_sidebar(surface, x, y, w, h, atual, maximo, cor):
    maximo = max(1.0, float(maximo))
    pct = max(0.0, min(1.0, float(atual) / maximo))
    pygame.draw.rect(surface, (24, 20, 32), (x, y, w, h), border_radius=4)
    if pct > 0:
        pygame.draw.rect(surface, cor, (x, y, max(3, int(w * pct)), h), border_radius=4)
    pygame.draw.rect(surface, (0, 255, 204), (x, y, w, h), 1, border_radius=4)

def _desenhar_hud_molduras(display):
    import Variaveis
    hud = _stage["hud"]
    if not hud:
        return
    rect = _stage["dst_rect"]
    screen_w, screen_h = display.get_size()
    left = pygame.Rect(0, 0, rect.x, screen_h)
    right = pygame.Rect(rect.right, 0, screen_w - rect.right, screen_h)
    _desenhar_moldura(display, left, "esquerda")
    _desenhar_moldura(display, right, "direita")

    font_titulo = get_cached_font(None, 24)
    font_valor = get_cached_font(None, 22)
    font_peq = get_cached_font(None, 16)

    if left.width >= 120:
        pad = 18
        w = left.width - pad * 2
        _texto_contorno(display, font_peq, "VIDA", (0, 255, 204), (pad, 36))
        _texto_contorno(display, font_valor, f"{int(max(0, hud['vida']))}/{int(max(1, hud['vida_maxima']))}", (255, 255, 255), (pad, 60))
        cor_vida = (0, 150, 255) if hud["aurea"] == "Devota" and hud["escudo_devota_ativo"] else Variaveis.calcular_cor_barra_de_vida((max(0, hud["vida"]) / max(1, hud["vida_maxima"])) * 100)
        _desenhar_barra_sidebar(display, pad, 92, w, 16, hud["vida"], hud["vida_maxima"], cor_vida)

        _texto_contorno(display, font_peq, "GEO", (0, 255, 204), (pad, 145))
        cx, cy, raio = left.centerx, 210, min(44, max(24, left.width // 5))
        pygame.draw.circle(display, (24, 20, 32), (cx, cy), raio)
        pygame.draw.circle(display, (0, 255, 204), (cx, cy), raio, 2)
        magia_pct = max(0.0, min(1.0, float(hud["pontuacao_magia"]) / 750.0))
        if magia_pct > 0:
            pygame.draw.arc(display, (53, 239, 252), pygame.Rect(cx - raio, cy - raio, raio * 2, raio * 2), -math.pi / 2, -math.pi / 2 + magia_pct * math.tau, 5)
        if hasattr(Variaveis, "imagem_relogio"):
            relogio = pygame.transform.smoothscale(Variaveis.imagem_relogio, (raio, raio))
            display.blit(relogio, (cx - raio // 2, cy - raio // 2))

        if hud["aurea"]:
            _texto_contorno(display, font_peq, f"AURA: {str(hud['aurea']).upper()}", (255, 220, 90), (pad, 285))

        _texto_contorno(display, font_peq, "TEMPO", (0, 255, 204), (pad, 335))
        try:
            tempo_txt = Variaveis.atualizar_cronometro()
        except Exception:
            tempo_txt = "00:00"
        _texto_contorno(display, font_valor, tempo_txt, (255, 255, 255), (pad, 360))

    if right.width >= 120:
        pad = 18
        x0 = right.x + pad
        w = right.width - pad * 2
        modo_drops = False
        try:
            modo_drops = Variaveis.obter_modo_cartas() == "drops"
        except Exception:
            pass
        _texto_contorno(display, font_peq, "FRAGMENTOS" if modo_drops else "PONTOS", (255, 220, 90), (x0, 36))
        valor_pts = f"{int(hud['pontuacao_exib'])}" if modo_drops else f"{int(hud['pontuacao_exib'])}/{int(max(1, hud['custo_carta_atual']))}"
        _texto_contorno(display, font_valor, valor_pts, (255, 255, 255), (x0, 60))
        if not modo_drops:
            _desenhar_barra_sidebar(display, x0, 92, w, 16, hud["pontuacao_exib"], max(1, hud["custo_carta_atual"]), (255, 210, 0))

        _texto_contorno(display, font_peq, "HABILIDADES", (0, 255, 204), (x0, 145))
        if hud["dispositivo_ativo"] == "teclado":
            teclas = [
                ("DISPARO", "LMB", Variaveis.icone_disparo_pronto, Variaveis.icone_disparo_recarga, hud["cooldowns"].get("disparo", 0.0)),
                ("TELEPORTE", Variaveis.formatar_nome_tecla(Variaveis.config_teclas.get("Teleporte", pygame.K_LSHIFT)), Variaveis.icone_teleporte_pronto, Variaveis.icone_teleporte_recarga, hud["cooldowns"].get("teleporte", 0.0)),
                ("ONDA", Variaveis.formatar_nome_tecla(Variaveis.config_teclas.get("Habilidade Onda", "MOUSE_3")), Variaveis.icone_onda_pronto, Variaveis.icone_onda_recarga, hud["cooldowns"].get("onda", 0.0)),
            ]
        else:
            teclas = [
                ("DISPARO", "A", Variaveis.icone_disparo_pronto, Variaveis.icone_disparo_recarga, hud["cooldowns"].get("disparo", 0.0)),
                ("TELEPORTE", "X", Variaveis.icone_teleporte_pronto, Variaveis.icone_teleporte_recarga, hud["cooldowns"].get("teleporte", 0.0)),
                ("ONDA", "B", Variaveis.icone_onda_pronto, Variaveis.icone_onda_recarga, hud["cooldowns"].get("onda", 0.0)),
            ]
        if not modo_drops:
            teclas.append(("LOJA", "Y" if hud["dispositivo_ativo"] != "teclado" else Variaveis.formatar_nome_tecla(Variaveis.config_teclas.get("Comprar na loja", pygame.K_e)), Variaveis.icone_loja, Variaveis.icone_loja_pronto, hud["cooldowns"].get("loja", 0.0)))

        y = 178
        icon_size = 42 if right.width < 190 else 50
        for nome, tecla, pronto, recarga, cd in teclas:
            if nome == "LOJA":
                icone = recarga if cd > 0 else pronto
            else:
                icone = recarga if cd > 0.0 else pronto
            img = pygame.transform.smoothscale(icone, (icon_size, icon_size))
            display.blit(img, (x0, y))
            if nome != "LOJA" and cd > 0.0:
                overlay = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                display.blit(overlay, (x0, y))
                _texto_contorno(display, font_peq, f"{cd:.1f}s", (0, 255, 240), (x0 + icon_size + 8, y + 25))
            _texto_contorno(display, font_peq, f"[{tecla}]", (0, 255, 204), (x0 + icon_size + 8, y + 4))
            _texto_contorno(display, font_peq, nome, (255, 255, 255), (x0 + icon_size + 8, y + 21))
            y += icon_size + 18

        if hud["eliminacoes_consecutivas"] > 0:
            _texto_contorno(display, font_titulo, f"COMBO: {hud['eliminacoes_consecutivas']}", (255, 255, 255), (x0, min(screen_h - 95, y + 18)))
            _texto_contorno(display, font_peq, f"Bônus: +{hud['bonus_pontuacao']}", (255, 255, 255), (x0, min(screen_h - 58, y + 50)))

def _flip_palco():
    if not _stage["active"]:
        return _stage["orig_flip"]()
    display = _stage["display"]
    display.fill((0, 0, 0))
    _desenhar_moldura(display, pygame.Rect(0, 0, _stage["dst_rect"].x, display.get_height()), "esquerda")
    _desenhar_moldura(display, pygame.Rect(_stage["dst_rect"].right, 0, display.get_width() - _stage["dst_rect"].right, display.get_height()), "direita")
    scaled = pygame.transform.smoothscale(_stage["game_surface"], _stage["dst_rect"].size)
    display.blit(scaled, _stage["dst_rect"].topleft)
    _desenhar_hud_molduras(display)
    return _stage["orig_flip"]()

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


def desenhar_hud_fase(
    tela,
    vida,
    vida_maxima,
    pontuacao_exib,
    custo_carta_atual,
    pontuacao_magia,
    cooldowns,
    dispositivo_ativo,
    eliminacoes_consecutivas=0,
    bonus_pontuacao=0,
    aurea=None,
    escudo_devota_ativo=False,
    pos_x_personagem=None,
    pos_y_personagem=None,
    largura_personagem=None,
    altura_personagem=None,
):
    import Variaveis

    if palco_ativo():
        _stage["hud"] = {
            "vida": vida,
            "vida_maxima": vida_maxima,
            "pontuacao_exib": pontuacao_exib,
            "custo_carta_atual": custo_carta_atual,
            "pontuacao_magia": pontuacao_magia,
            "cooldowns": cooldowns,
            "dispositivo_ativo": dispositivo_ativo,
            "eliminacoes_consecutivas": eliminacoes_consecutivas,
            "bonus_pontuacao": bonus_pontuacao,
            "aurea": aurea,
            "escudo_devota_ativo": escudo_devota_ativo,
        }
        return

    posicao_barra_vida = (80, Variaveis.altura_mapa - (Variaveis.altura_mapa - 34))
    fonte = get_cached_font(None, int(Variaveis.altura_barra_vida * 1))
    fonte_vida = get_cached_font(None, int(Variaveis.altura_barra_vida * 0.9))

    if Variaveis.obter_modo_cartas() != "drops":
        texto_pontuacao = fonte.render(f'{pontuacao_exib}/{custo_carta_atual}', True, (250, 255,255))
        texto_pontuacao_borda = fonte.render(f'{pontuacao_exib}/{custo_carta_atual}', True, (0, 0, 0))

        tela.blit(texto_pontuacao_borda, (Variaveis.largura_mapa*0.075 - 1, Variaveis.altura_mapa*0.118 - 1))
        tela.blit(texto_pontuacao_borda, (Variaveis.largura_mapa*0.075 + 1, Variaveis.altura_mapa*0.118 - 1))
        tela.blit(texto_pontuacao_borda, (Variaveis.largura_mapa*0.075 - 1, Variaveis.altura_mapa*0.118 + 1))
        tela.blit(texto_pontuacao_borda, (Variaveis.largura_mapa*0.075 + 1, Variaveis.altura_mapa*0.118 + 1))
        tela.blit(texto_pontuacao, (Variaveis.largura_mapa*0.075, Variaveis.altura_mapa*0.118))

    angulo_preenchimento = (pontuacao_magia / 735) * 360
    if angulo_preenchimento > 0:
        pontos = []
        for i in range(int(angulo_preenchimento) + 1):
            radianos = math.radians(i - 90)
            x = Variaveis.centro_circulo[0] + Variaveis.raio_circulo * math.cos(radianos)
            y = Variaveis.centro_circulo[1] + Variaveis.raio_circulo * math.sin(radianos)
            pontos.append((x, y))
        pygame.draw.polygon(tela, (53, 239, 252), [Variaveis.centro_circulo] + pontos)

    tela.blit(Variaveis.imagem_relogio, Variaveis.posicao_imagem_relogio)

    vida_segura = max(0, vida)
    vida_maxima_segura = max(1, vida_maxima)
    porcentagem_vida_personagem = (vida_segura / vida_maxima_segura) * 100
    if aurea == "Devota" and escudo_devota_ativo:
        cor_barra = (0, 150, 255)
    else:
        cor_barra = Variaveis.calcular_cor_barra_de_vida(porcentagem_vida_personagem)

    pygame.draw.rect(
        tela,
        cor_barra,
        (
            posicao_barra_vida[0],
            posicao_barra_vida[1],
            (vida_segura / vida_maxima_segura) * Variaveis.largura_barra_vida,
            Variaveis.altura_barra_vida,
        )
    )
    pygame.draw.rect(
        tela,
        (0, 0, 0),
        (posicao_barra_vida[0], posicao_barra_vida[1], Variaveis.largura_barra_vida, Variaveis.altura_barra_vida),
        2
    )

    texto_vida = fonte_vida.render(f'{int(vida_segura)}/{int(vida_maxima_segura)}', True, (255, 255, 255))
    texto_vida_borda = fonte_vida.render(f'{int(vida_segura)}/{int(vida_maxima_segura)}', True, (0, 0, 0))

    tela.blit(texto_vida_borda, (posicao_barra_vida[0]*2 - 1, posicao_barra_vida[1] + 5 - 1))
    tela.blit(texto_vida_borda, (posicao_barra_vida[0]*2 + 1, posicao_barra_vida[1] + 5 - 1))
    tela.blit(texto_vida_borda, (posicao_barra_vida[0]*2 - 1, posicao_barra_vida[1] + 5 + 1))
    tela.blit(texto_vida_borda, (posicao_barra_vida[0]*2 + 1, posicao_barra_vida[1] + 5 + 1))
    tela.blit(texto_vida, (posicao_barra_vida[0]*2, posicao_barra_vida[1] + 5))

    tela.blit(Variaveis.imagem_vida, Variaveis.posicao_vida)

    deve_desenhar_icones = True
    if None not in (pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem):
        deve_desenhar_icones = not Variaveis.area_icones.colliderect(
            (pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
        )

    if deve_desenhar_icones:
        Variaveis.desenhar_habilidades(tela, cooldowns, dispositivo_ativo)

    if eliminacoes_consecutivas > 0:
        fonte_combo = get_cached_font(None, 36)
        fonte_bonus = get_cached_font(None, 28)
        texto_combo = f"Combo: {eliminacoes_consecutivas}"
        posicao_combo = (Variaveis.largura_mapa - 170, 50)
        Variaveis.desenhar_texto_com_contorno(tela, texto_combo, fonte_combo, (255, 255, 255), (0, 0, 0), posicao_combo)

        texto_bonus = f"Bônus: +{bonus_pontuacao}"
        posicao_bonus = (Variaveis.largura_mapa - 200, 90)
        Variaveis.desenhar_texto_com_contorno(tela, texto_bonus, fonte_bonus, (255, 255, 255), (0, 0, 0), posicao_bonus)


def desenhar_hud_widescreen(tela_real, vida, vida_maxima, pontuacao_exib, custo_carta_atual, pontuacao_magia, cooldowns, dispositivo_ativo, eliminacoes_consecutivas, bonus_pontuacao, aurea, escudo_devota_ativo, fase_nome, cronometro_str):
    import Variaveis
    import pygame
    import os
    import math
    import random
    
    # 1. Carregar recursos / fontes
    fonte_caminho_titulo = "Texto/Doctor Glitch.otf" if os.path.exists("Texto/Doctor Glitch.otf") else "Texto/Broken.otf"
    fonte_caminho_texto = "Texto/rainyhearts.ttf" if os.path.exists("Texto/rainyhearts.ttf") else "Texto/World.otf"
    
    # Usar get_cached_font para desempenho
    font_titulo = get_cached_font(fonte_caminho_titulo, 24)
    font_subtitulo = get_cached_font(fonte_caminho_texto, 20)
    font_valores = get_cached_font(fonte_caminho_texto, 24)
    font_combo = get_cached_font(fonte_caminho_titulo, 36)
    font_combo_sub = get_cached_font(fonte_caminho_texto, 18)
    
    # 2. Desenhar fundo nos painéis laterais
    w_painel = Variaveis.x_offset
    h_painel = Variaveis.altura_tela
    
    # Painel Esquerdo
    surf_esq = pygame.Surface((w_painel, h_painel), pygame.SRCALPHA)
    surf_esq.fill((10, 8, 20, 255))
    
    # Linhas de grade futuristas (efeito de background premium)
    for y in range(0, h_painel, 40):
        pygame.draw.line(surf_esq, (0, 180, 200, 15), (0, y), (w_painel, y), 1)
    for x in range(0, w_painel, 40):
        pygame.draw.line(surf_esq, (0, 180, 200, 15), (x, 0), (x, h_painel), 1)
        
    # Painel Direito
    surf_dir = pygame.Surface((w_painel, h_painel), pygame.SRCALPHA)
    surf_dir.fill((10, 8, 20, 255))
    
    # Linhas de grade no painel direito
    for y in range(0, h_painel, 40):
        pygame.draw.line(surf_dir, (0, 180, 200, 15), (0, y), (w_painel, y), 1)
    for x in range(0, w_painel, 40):
        pygame.draw.line(surf_dir, (0, 180, 200, 15), (x, 0), (x, h_painel), 1)
        
    # 3. Desenhar bordas limitadoras (moldura)
    # Linhas neon ciano verticais separando a jogabilidade
    pygame.draw.line(surf_esq, (0, 255, 230), (w_painel - 4, 0), (w_painel - 4, h_painel), 4)
    pygame.draw.line(surf_dir, (0, 255, 230), (0, 0), (0, h_painel), 4)
    
    # 4. Painel Esquerdo: Conteúdo
    # Título do Jogo
    texto_titulo = font_titulo.render("RUPTURA TEMPORAL", True, (0, 255, 204))
    surf_esq.blit(texto_titulo, (20, 30))
    
    # Fase Atual
    texto_fase = font_subtitulo.render(fase_nome.upper(), True, (150, 150, 150))
    surf_esq.blit(texto_fase, (20, 65))
    
    # Vida do Jogador (High tech health bar)
    txt_vida_label = font_subtitulo.render("NÚCLEO VITAL", True, (255, 255, 255))
    surf_esq.blit(txt_vida_label, (20, 120))
    
    # Barra de vida
    largura_barra = w_painel - 40
    altura_barra = 24
    pygame.draw.rect(surf_esq, (30, 20, 35), (20, 145, largura_barra, altura_barra), border_radius=5)
    
    # Preenchimento proporcional
    vida_porc = max(0.0, min(1.0, vida / vida_maxima))
    if vida_porc > 0:
        cor_vida = (0, 255, 128) if vida_porc > 0.4 else (255, 50, 50)
        # Se estiver sob efeito de escudo devota, cor muda pra ciano
        if aurea == "Devota" and escudo_devota_ativo:
            cor_vida = (0, 240, 255)
        pygame.draw.rect(surf_esq, cor_vida, (20, 145, int(largura_barra * vida_porc), altura_barra), border_radius=5)
        # Detalhe de brilho
        pygame.draw.rect(surf_esq, (255, 255, 255, 80), (20, 145, int(largura_barra * vida_porc), 6), border_radius=2)
        
    # Borda externa da barra de vida
    pygame.draw.rect(surf_esq, (0, 255, 204, 150), (20, 145, largura_barra, altura_barra), width=2, border_radius=5)
    
    # Texto de vida numérico centralizado
    txt_vida_num = font_valores.render(f"{int(vida)} / {int(vida_maxima)} HP", True, (255, 255, 255))
    tx_life = 20 + (largura_barra - txt_vida_num.get_width()) // 2
    ty_life = 145 + (altura_barra - txt_vida_num.get_height()) // 2
    surf_esq.blit(txt_vida_num, (tx_life, ty_life))
    
    # Se tiver escudo devota ativo, desenha indicador textual
    if aurea == "Devota" and escudo_devota_ativo:
        txt_escudo = font_subtitulo.render("[ESCUDO ATIVO]", True, (0, 240, 255))
        surf_esq.blit(txt_escudo, (20, 175))
        
    # Núcleo de Magia / Rewind (Relógio no Painel Esquerdo)
    txt_magia_label = font_subtitulo.render("GEO-RECONSTRUÇÃO", True, (255, 255, 255))
    surf_esq.blit(txt_magia_label, (20, 220))
    
    # Desenhar círculo de magia
    cx_magia = 20 + largura_barra // 2
    cy_magia = 340
    raio_magia = 50
    # Círculo de fundo
    pygame.draw.circle(surf_esq, (25, 25, 35), (cx_magia, cy_magia), raio_magia)
    pygame.draw.circle(surf_esq, (0, 255, 204, 50), (cx_magia, cy_magia), raio_magia, width=3)
    
    # Preenchimento de arco
    magia_porc = max(0.0, min(1.0, pontuacao_magia / 750.0))
    if magia_porc > 0:
        cor_magia = (0, 255, 240) if magia_porc >= 1.0 else (0, 150, 200)
        rect_arco = pygame.Rect(cx_magia - raio_magia, cy_magia - raio_magia, raio_magia*2, raio_magia*2)
        angulo_fim = magia_porc * 2 * math.pi
        for r in range(raio_magia - 8, raio_magia):
            rect_temp = pygame.Rect(cx_magia - r, cy_magia - r, r*2, r*2)
            pygame.draw.arc(surf_esq, cor_magia, rect_temp, -math.pi/2, angulo_fim - math.pi/2, width=2)
            
    # Relógio Icon no centro
    if hasattr(Variaveis, 'imagem_relogio'):
        img_rel = pygame.transform.scale(Variaveis.imagem_relogio, (50, 50))
        surf_esq.blit(img_rel, (cx_magia - 25, cy_magia - 25))
        
    # Texto de cronômetro abaixo do círculo
    txt_crono_label = font_subtitulo.render("TEMPO DE INSTABILIDADE", True, (150, 150, 150))
    surf_esq.blit(txt_crono_label, (20, 430))
    
    txt_crono = font_valores.render(cronometro_str, True, (255, 255, 255))
    surf_esq.blit(txt_crono, (20, 455))
    
    # Aurea atual ativa
    txt_aurea_label = font_subtitulo.render("AURA SELECIONADA", True, (150, 150, 150))
    surf_esq.blit(txt_aurea_label, (20, 510))
    txt_aurea_nome = font_valores.render(str(aurea).upper() if aurea else "NENHUMA", True, (255, 215, 0) if aurea else (200, 200, 200))
    surf_esq.blit(txt_aurea_nome, (20, 535))
    
    # 5. Painel Direito: Conteúdo
    # Título do Painel Direito
    texto_status = font_titulo.render("GEO-METRIA", True, (0, 255, 204))
    surf_dir.blit(texto_status, (20, 30))
    
    # Fragmentos/Moedas Coletados
    txt_score_label = font_subtitulo.render("ENERGIA COLETADA", True, (255, 255, 255))
    surf_dir.blit(txt_score_label, (20, 120))
    
    # Barra de custo de compra da carta
    pygame.draw.rect(surf_dir, (30, 20, 35), (20, 145, largura_barra, altura_barra), border_radius=5)
    custo = max(1, custo_carta_atual)
    score_porc = max(0.0, min(1.0, pontuacao_exib / custo))
    if score_porc > 0:
        cor_score = (255, 200, 0) if score_porc < 1.0 else (0, 255, 128)
        pygame.draw.rect(surf_dir, cor_score, (20, 145, int(largura_barra * score_porc), altura_barra), border_radius=5)
        pygame.draw.rect(surf_dir, (255, 255, 255, 80), (20, 145, int(largura_barra * score_porc), 6), border_radius=2)
        
    pygame.draw.rect(surf_dir, (0, 255, 204, 150), (20, 145, largura_barra, altura_barra), width=2, border_radius=5)
    
    # Valor numérico da pontuação
    txt_score_num = font_valores.render(f"{int(pontuacao_exib)} / {int(custo)}", True, (255, 255, 255))
    tx_score = 20 + (largura_barra - txt_score_num.get_width()) // 2
    ty_score = 145 + (altura_barra - txt_score_num.get_height()) // 2
    surf_dir.blit(txt_score_num, (tx_score, ty_score))
    
    # Alerta de compra na Loja de Cartas
    if score_porc >= 1.0:
        pygame.draw.rect(surf_dir, (0, 80, 50, 180), (20, 175, largura_barra, 30), border_radius=5)
        pygame.draw.rect(surf_dir, (0, 255, 128), (20, 175, largura_barra, 30), width=1, border_radius=5)
        txt_alerta = font_subtitulo.render("COMPRA DISPONÍVEL [E] / [Y]", True, (0, 255, 128))
        surf_dir.blit(txt_alerta, (20 + (largura_barra - txt_alerta.get_width()) // 2, 181))
        
    # Habilidades do Jogador
    txt_habs_label = font_subtitulo.render("DISPOSITIVOS ATIVOS", True, (255, 255, 255))
    surf_dir.blit(txt_habs_label, (20, 230))
    
    if dispositivo_ativo == "teclado":
        tecla_disparo = "LMB"
        tecla_teleporte = Variaveis.formatar_nome_tecla(Variaveis.config_teclas.get("Teleporte", pygame.K_LSHIFT))
        tecla_onda = Variaveis.formatar_nome_tecla(Variaveis.config_teclas.get("Habilidade Onda", "MOUSE_3"))
    else:
        tecla_disparo = "A"
        tecla_teleporte = "X"
        tecla_onda = "B"
        
    habilidades_lista = [
        ("Disparo", tecla_disparo, Variaveis.icone_disparo_pronto, Variaveis.icone_disparo_recarga, cooldowns.get('disparo', 0.0)),
        ("Teleporte", tecla_teleporte, Variaveis.icone_teleporte_pronto, Variaveis.icone_teleporte_recarga, cooldowns.get('teleporte', 0.0)),
        ("Onda de Choque", tecla_onda, Variaveis.icone_onda_pronto, Variaveis.icone_onda_recarga, cooldowns.get('onda', 0.0))
    ]
    
    y_hab = 260
    for nome, tecla, icone_pronto, icone_recarga, cd in habilidades_lista:
        pygame.draw.rect(surf_dir, (20, 20, 30, 200), (20, y_hab, largura_barra, 64), border_radius=8)
        pygame.draw.rect(surf_dir, (0, 255, 204, 45), (20, y_hab, largura_barra, 64), width=1, border_radius=8)
        
        icone = icone_recarga if cd > 0.0 else icone_pronto
        img_hab = pygame.transform.scale(icone, (48, 48))
        surf_dir.blit(img_hab, (28, y_hab + 8))
        
        if cd > 0.0:
            overlay_cd = pygame.Surface((48, 48), pygame.SRCALPHA)
            pygame.draw.rect(overlay_cd, (0, 0, 0, 160), (0, 0, 48, 48), border_radius=8)
            surf_dir.blit(overlay_cd, (28, y_hab + 8))
            txt_cd = font_valores.render(f"{cd:.1f}s", True, (0, 255, 240))
            surf_dir.blit(txt_cd, (88, y_hab + 34))
            
        txt_tecla = font_subtitulo.render(f"[{tecla}]", True, (0, 255, 204))
        surf_dir.blit(txt_tecla, (88, y_hab + 10))
        
        txt_hab_nome = font_subtitulo.render(nome, True, (255, 255, 255) if cd == 0.0 else (150, 150, 150))
        surf_dir.blit(txt_hab_nome, (150, y_hab + 10))
        
        y_hab += 75
        
    # Combo Counter
    if eliminacoes_consecutivas > 0:
        cor_combo = (0, 255, 240) if eliminacoes_consecutivas < 10 else (255, 0, 128)
        shake_x = random.randint(-2, 2) if eliminacoes_consecutivas >= 10 else 0
        shake_y = random.randint(-2, 2) if eliminacoes_consecutivas >= 10 else 0
        
        txt_combo = font_combo.render(f"COMBO X{eliminacoes_consecutivas}", True, cor_combo)
        surf_dir.blit(txt_combo, (20 + shake_x, 500 + shake_y))
        
        txt_bonus = font_combo_sub.render(f"BÔNUS: +{bonus_pontuacao} PTS", True, (255, 255, 255))
        surf_dir.blit(txt_bonus, (20, 545))
        
    # 6. Desenhar painéis em tela_real
    tela_real.blit(surf_esq, (0, 0))
    tela_real.blit(surf_dir, (Variaveis.x_offset + Variaveis.largura_mapa, 0))
