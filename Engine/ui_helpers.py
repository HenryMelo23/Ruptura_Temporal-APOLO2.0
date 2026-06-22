# -*- coding: utf-8 -*-
import pygame
import os
import math
import random
import json

_font_cache = {}
_cursor_personalizado = None
_vida_animacoes = {}
_stage = {
    "active": False,
    "display": None,
    "game_surface": None,
    "game_size": (0, 0),
    "dst_rect": pygame.Rect(0, 0, 0, 0),
    "hud": None,
    "hud_atualizado_ms": 0,
    "aura_widget": None,
    "aura_atualizado_ms": 0,
    "top_h": 0,
    "bottom_h": 0,
    "orig_flip": None,
    "frame_surface": None,
    "logical_dst_rect": None,
    "window_scale": 1.0,
}

_MIN_LARGURA_HUD_FULLSCREEN = 150
_ALTURA_HUD_SUPERIOR = 76
_ALTURA_HUD_INFERIOR = 92

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


def registrar_widget_aurea(widget):
    """Move o medidor da aura para a faixa externa no proximo flip."""
    if not _stage["active"]:
        return False
    _stage["aura_widget"] = widget.copy() if widget is not None else None
    _stage["aura_atualizado_ms"] = pygame.time.get_ticks()
    return True


def limpar_hud_palco():
    _stage["hud"] = None
    _stage["hud_atualizado_ms"] = 0
    _stage["aura_widget"] = None
    _stage["aura_atualizado_ms"] = 0

def obter_pos_mouse_jogo():
    return converter_pos_mouse_jogo(pygame.mouse.get_pos())

def converter_pos_mouse_jogo(pos):
    mx, my = pos
    if not _stage["active"]:
        return mx, my
    rect = _stage["dst_rect"]
    if rect.width <= 0 or rect.height <= 0:
        return mx, my
    game_w, game_h = _stage["game_size"]
    gx = (mx - rect.x) * game_w / rect.width
    gy = (my - rect.y) * game_h / rect.height
    return int(max(0, min(game_w - 1, gx))), int(max(0, min(game_h - 1, gy)))

def obter_pos_mouse_superficie(superficie=None):
    if _stage["active"] and (superficie is None or superficie == _stage["game_surface"]):
        return obter_pos_mouse_jogo()
    return pygame.mouse.get_pos()

def _carregar_cursor_personalizado():
    global _cursor_personalizado
    if _cursor_personalizado is not None:
        return _cursor_personalizado
    try:
        _cursor_personalizado = pygame.image.load("Sprites/Ponteiro.png").convert_alpha()
    except Exception:
        _cursor_personalizado = pygame.Surface((22, 28), pygame.SRCALPHA)
        pygame.draw.polygon(_cursor_personalizado, (255, 255, 255), [(0, 0), (0, 24), (8, 18), (13, 28), (18, 25), (13, 15), (22, 15)])
        pygame.draw.polygon(_cursor_personalizado, (0, 0, 0), [(0, 0), (0, 24), (8, 18), (13, 28), (18, 25), (13, 15), (22, 15)], 2)
    return _cursor_personalizado

def desenhar_cursor_personalizado(superficie, pos=None):
    if superficie is None:
        return
    cursor = _carregar_cursor_personalizado()
    x, y = pos if pos is not None else obter_pos_mouse_superficie(superficie)
    largura, altura = superficie.get_size()
    x = max(0, min(int(x), max(0, largura - cursor.get_width())))
    y = max(0, min(int(y), max(0, altura - cursor.get_height())))
    superficie.blit(cursor, (x, y))

def criar_particulas_menu(largura, altura, quantidade=44, cor=(0, 220, 255)):
    particulas = []
    for _ in range(int(quantidade)):
        particulas.append({
            "x": random.uniform(0, largura),
            "y": random.uniform(0, altura),
            "vx": random.uniform(-0.14, 0.14),
            "vy": random.uniform(-0.68, -0.18),
            "r": random.uniform(1.1, 3.0),
            "alpha": random.randint(34, 130),
            "fase": random.uniform(0, math.tau),
            "cor": cor,
        })
    return particulas

def desenhar_fundo_menu_ruptura(tela, agora_ms=None, particulas=None, cor_base=(5, 9, 18), cor_acento=(0, 220, 255), intensidade=1.0):
    largura, altura = tela.get_size()
    agora_ms = pygame.time.get_ticks() if agora_ms is None else agora_ms
    tempo = agora_ms * 0.001
    intensidade = max(0.35, min(1.25, float(intensidade)))
    base = tuple(max(0, min(255, int(c))) for c in cor_base[:3])
    acento = tuple(max(0, min(255, int(c))) for c in cor_acento[:3])

    for y in range(0, altura, 8):
        t = y / max(1, altura)
        cor = (
            int(base[0] * (0.72 + 0.22 * t)),
            int(base[1] * (0.74 + 0.24 * t)),
            int(base[2] * (0.86 + 0.34 * t)),
        )
        pygame.draw.rect(tela, cor, (0, y, largura, 8))

    grade = pygame.Surface((largura, altura), pygame.SRCALPHA)
    passo = 64
    for x in range(0, largura + passo, passo):
        alpha = int(18 * intensidade)
        pygame.draw.line(grade, (*acento, alpha), (x, 0), (x, altura), 1)
    for y in range(0, altura + passo, passo):
        alpha = int(16 * intensidade)
        pygame.draw.line(grade, (*acento, alpha), (0, y), (largura, y), 1)
    for i in range(-altura, largura, 160):
        pygame.draw.line(grade, (*acento, int(12 * intensidade)), (i, altura), (i + altura, 0), 1)

    tela.blit(grade, (0, 0))

    if particulas is None:
        return
    for p in particulas:
        p["y"] = float(p.get("y", 0)) + float(p.get("vy", p.get("vel_y", p.get("speed_y", -0.35))))
        p["x"] = float(p.get("x", 0)) + float(p.get("vx", 0.0)) + math.sin(tempo * 0.8 + float(p.get("fase", p.get("drift_phase", 0.0)))) * 0.08
        if p["y"] < -12:
            p["y"] = altura + 12
            p["x"] = random.uniform(0, largura)
        elif p["y"] > altura + 12:
            p["y"] = -12
            p["x"] = random.uniform(0, largura)
        if p["x"] < -12:
            p["x"] = largura + 12
        elif p["x"] > largura + 12:
            p["x"] = -12

        alpha = int(p.get("alpha", 90))
        if "breathe_dir" in p:
            p["alpha"] = max(32, min(180, alpha + float(p.get("breathe_dir", 1)) * float(p.get("breathe_speed", 0.03)) * 24))
            if p["alpha"] >= 180:
                p["breathe_dir"] = -1
            elif p["alpha"] <= 32:
                p["breathe_dir"] = 1
            alpha = int(p["alpha"])
        raio = max(1, int(p.get("r", p.get("tamanho", p.get("size", 2)))))
        cor_p = p.get("cor", acento)
        if len(cor_p) >= 3:
            cor_p = tuple(cor_p[:3])
        else:
            cor_p = acento
        pygame.draw.circle(tela, (*cor_p, max(18, min(180, alpha))), (int(p["x"]), int(p["y"])), raio)

def desenhar_cabecalho_menu(tela, titulo, subtitulo, fonte_titulo, fonte_subtitulo, cor_acento=(0, 220, 255), y=68):
    largura, _ = tela.get_size()
    cor_acento = tuple(cor_acento[:3])
    sombra = fonte_titulo.render(str(titulo), True, (0, 70, 95))
    texto = fonte_titulo.render(str(titulo), True, (245, 252, 255))
    tela.blit(sombra, sombra.get_rect(center=(largura // 2 + 3, y + 3)))
    tela.blit(texto, texto.get_rect(center=(largura // 2, y)))
    if subtitulo:
        sub = fonte_subtitulo.render(str(subtitulo), True, tuple(min(255, int(c * 0.55 + 120)) for c in cor_acento))
        tela.blit(sub, sub.get_rect(center=(largura // 2, y + 48)))
        pygame.draw.line(tela, (*cor_acento, 120), (largura // 2 - 180, y + 27), (largura // 2 + 180, y + 27), 1)

def desenhar_botao_voltar_menu(tela, rect, fonte, hover=False, cor_acento=(0, 220, 255), texto="ESC Voltar"):
    cor_acento = tuple(cor_acento[:3])
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bg_alpha = 218 if hover else 150
    pygame.draw.rect(surf, (5, 9, 18, bg_alpha), surf.get_rect(), border_radius=7)
    pygame.draw.rect(surf, (*cor_acento, 230 if hover else 120), surf.get_rect(), 1 if not hover else 2, border_radius=7)
    pygame.draw.line(surf, (*cor_acento, 72), (10, rect.h - 6), (rect.w - 10, rect.h - 6), 1)
    txt = fonte.render(str(texto), True, (235, 255, 255) if hover else (160, 190, 205))
    surf.blit(txt, txt.get_rect(center=(rect.w // 2, rect.h // 2)))
    tela.blit(surf, rect.topleft)

def desenhar_rodape_menu(tela, texto, fonte, cor_acento=(0, 220, 255), y=None):
    largura, altura = tela.get_size()
    y = altura - 28 if y is None else y
    txt = fonte.render(str(texto), True, (126, 172, 190))
    rect = txt.get_rect(center=(largura // 2, y))
    painel = pygame.Rect(rect.left - 20, rect.top - 7, rect.w + 40, rect.h + 14)
    surf = pygame.Surface((painel.w, painel.h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (5, 9, 18, 170), surf.get_rect(), border_radius=6)
    pygame.draw.rect(surf, (*tuple(cor_acento[:3]), 80), surf.get_rect(), 1, border_radius=6)
    tela.blit(surf, painel.topleft)
    tela.blit(txt, rect)

def ativar_palco_fullscreen(largura_jogo, altura_jogo):
    if _stage["orig_flip"] is None:
        _stage["orig_flip"] = pygame.display.flip

    display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    screen_w, screen_h = display.get_size()
    top_h = max(72, min(82, int(screen_h * 0.072)))
    bottom_h = max(80, min(98, int(screen_h * 0.088)))
    altura_disponivel = max(1, screen_h - top_h - bottom_h)
    escala = min(screen_w / largura_jogo, altura_disponivel / altura_jogo)

    if screen_w >= largura_jogo + (_MIN_LARGURA_HUD_FULLSCREEN * 2):
        largura_maxima_jogo = screen_w - (_MIN_LARGURA_HUD_FULLSCREEN * 2)
        escala = min(escala, largura_maxima_jogo / largura_jogo)

    dst_w = max(1, int(largura_jogo * escala))
    dst_h = max(1, int(altura_jogo * escala))
    dst_rect = pygame.Rect(
        (screen_w - dst_w) // 2,
        top_h + (altura_disponivel - dst_h) // 2,
        dst_w,
        dst_h,
    )

    _stage.update({
        "active": True,
        "display": display,
        "game_surface": pygame.Surface((largura_jogo, altura_jogo)).convert(),
        "game_size": (largura_jogo, altura_jogo),
        "dst_rect": dst_rect,
        "hud": None,
        "hud_atualizado_ms": 0,
        "aura_widget": None,
        "aura_atualizado_ms": 0,
        "top_h": dst_rect.top,
        "bottom_h": screen_h - dst_rect.bottom,
        "frame_surface": None,
        "logical_dst_rect": None,
        "window_scale": escala,
    })
    pygame.display.flip = _flip_palco
    return _stage["game_surface"]


def _obter_area_util_desktop():
    """Retorna a area disponivel sem a barra de tarefas, quando possivel."""
    tamanhos = pygame.display.get_desktop_sizes()
    largura, altura = tamanhos[0] if tamanhos else (1366, 768)

    if os.name == "nt":
        try:
            import ctypes

            class _RectTrabalho(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            rect = _RectTrabalho()
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                largura = max(1, rect.right - rect.left)
                altura = max(1, rect.bottom - rect.top)
        except Exception:
            pass

    return int(largura), int(altura)


def _calcular_layout_janela(largura_jogo, altura_jogo, area_util=None):
    """Escala uniformemente jogo e molduras para caber no monitor."""
    largura_jogo = int(largura_jogo)
    altura_jogo = int(altura_jogo)
    largura_logica = largura_jogo
    altura_logica = altura_jogo + _ALTURA_HUD_SUPERIOR + _ALTURA_HUD_INFERIOR
    area_w, area_h = area_util or _obter_area_util_desktop()

    # Reserva para bordas e barra de titulo da janela. Em telas grandes a
    # escala permanece 1:1; em telas menores todo o quadro encolhe junto.
    limite_w = max(1, area_w - 32)
    limite_h = max(1, area_h - 48)
    escala = min(1.0, limite_w / largura_logica, limite_h / altura_logica)

    display_w = max(1, int(round(largura_logica * escala)))
    display_h = max(1, int(round(altura_logica * escala)))
    top_h = max(1, int(round(_ALTURA_HUD_SUPERIOR * escala)))
    game_h = max(1, int(round(altura_jogo * escala)))
    # Absorve arredondamentos na faixa inferior sem alterar a proporcao do mapa.
    bottom_h = max(1, display_h - top_h - game_h)
    dst_rect = pygame.Rect(0, top_h, display_w, game_h)
    return (display_w, display_h), dst_rect, escala, bottom_h


def ativar_palco_janela(largura_jogo, altura_jogo):
    if _stage["orig_flip"] is None:
        _stage["orig_flip"] = pygame.display.flip

    largura_jogo = int(largura_jogo)
    altura_jogo = int(altura_jogo)
    tamanho_display, dst_rect, escala, bottom_h = _calcular_layout_janela(largura_jogo, altura_jogo)
    display = pygame.display.set_mode(tamanho_display)
    pygame.mouse.set_visible(False)
    frame_surface = pygame.Surface(
        (largura_jogo, altura_jogo + _ALTURA_HUD_SUPERIOR + _ALTURA_HUD_INFERIOR)
    ).convert()
    logical_dst_rect = pygame.Rect(0, _ALTURA_HUD_SUPERIOR, largura_jogo, altura_jogo)
    _stage.update({
        "active": True,
        "display": display,
        "game_surface": pygame.Surface((largura_jogo, altura_jogo)).convert(),
        "game_size": (largura_jogo, altura_jogo),
        "dst_rect": dst_rect,
        "hud": None,
        "hud_atualizado_ms": 0,
        "aura_widget": None,
        "aura_atualizado_ms": 0,
        "top_h": _ALTURA_HUD_SUPERIOR,
        "bottom_h": bottom_h,
        "frame_surface": frame_surface,
        "logical_dst_rect": logical_dst_rect,
        "window_scale": escala,
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
        "hud_atualizado_ms": 0,
        "aura_widget": None,
        "aura_atualizado_ms": 0,
        "top_h": 0,
        "bottom_h": 0,
        "frame_surface": None,
        "logical_dst_rect": None,
        "window_scale": 1.0,
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

def _desenhar_fundo_palco(surface):
    largura, altura = surface.get_size()
    surface.fill((8, 7, 16))
    tempo = pygame.time.get_ticks() * 0.001
    for y in range(-40, altura + 40, 40):
        yy = int((y + tempo * 18) % (altura + 40) - 20)
        pygame.draw.line(surface, (5, 34, 43), (0, yy), (largura, yy), 1)
    for x in range(0, largura, 40):
        pygame.draw.line(surface, (4, 27, 36), (x, 0), (x, altura), 1)

def _desenhar_barra_sidebar(surface, x, y, w, h, atual, maximo, cor):
    maximo = max(1.0, float(maximo))
    pct = max(0.0, min(1.0, float(atual) / maximo))
    pygame.draw.rect(surface, (24, 20, 32), (x, y, w, h), border_radius=4)
    if pct > 0:
        pygame.draw.rect(surface, cor, (x, y, max(3, int(w * pct)), h), border_radius=4)
    pygame.draw.rect(surface, (0, 255, 204), (x, y, w, h), 1, border_radius=4)

def _obter_nivel_detalhes(config_graficos=None):
    cfg = config_graficos or {}
    if not cfg:
        try:
            with open("saves/config_graficos.json", "r") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    nivel = str(cfg.get("nivel_detalhes", cfg.get("qualidade_grafica", "alta"))).lower()
    if nivel in ("alto", "alta"):
        return "alto"
    if nivel in ("medio", "media", "médio", "média"):
        return "medio"
    return "baixo"

def _carregar_config_graficos():
    try:
        with open("saves/config_graficos.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _atualizar_animacao_vida(chave, atual, maximo):
    agora = pygame.time.get_ticks()
    maximo = max(1.0, float(maximo))
    pct = max(0.0, min(1.0, float(atual) / maximo))
    estado = _vida_animacoes.setdefault(chave, {"pct": pct, "eventos": []})
    pct_anterior = estado.get("pct", pct)
    delta = pct - pct_anterior
    if abs(delta) > 0.002:
        estado["eventos"].append({
            "tipo": "cura" if delta > 0 else "dano",
            "inicio": min(pct_anterior, pct),
            "fim": max(pct_anterior, pct),
            "tempo": agora,
            "seed": random.random(),
        })
        estado["pct"] = pct
    estado["eventos"] = [ev for ev in estado["eventos"] if agora - ev["tempo"] < 760]
    return estado["eventos"]

def _desenhar_efeitos_barra_vida(surface, rect, atual, maximo, cor_base, chave="principal", config_graficos=None):
    nivel = _obter_nivel_detalhes(config_graficos)
    if nivel == "baixo":
        frag_qtd, cura_linhas = 5, 4
    elif nivel == "medio":
        frag_qtd, cura_linhas = 10, 7
    else:
        frag_qtd, cura_linhas = 18, 12

    eventos = _atualizar_animacao_vida(chave, atual, maximo)
    agora = pygame.time.get_ticks()
    for ev in eventos:
        t = (agora - ev["tempo"]) / 760.0
        if not 0 <= t <= 1:
            continue
        x0 = rect.x + int(rect.w * ev["inicio"])
        x1 = rect.x + int(rect.w * ev["fim"])
        largura = max(2, x1 - x0)
        if ev["tipo"] == "dano":
            rng = random.Random(int(ev["seed"] * 100000))
            alpha = max(0, int(210 * (1 - t)))
            for _ in range(frag_qtd):
                fw = max(2, int(largura / rng.randint(5, 11)))
                fh = rng.randint(3, max(4, rect.h))
                fx = x0 + rng.randint(0, max(1, largura))
                fy = rect.y + rng.randint(-2, max(1, rect.h - fh + 2))
                drift = int((rng.random() - 0.5) * 38 * t)
                queda = int((8 + rng.random() * 22) * t)
                cor = (255, rng.randint(60, 120), rng.randint(45, 85), alpha)
                frag = pygame.Surface((fw, fh), pygame.SRCALPHA)
                pygame.draw.rect(frag, cor, (0, 0, fw, fh), border_radius=2)
                surface.blit(frag, (fx + drift, fy + queda))
        else:
            alpha = max(0, int(190 * (1 - abs(t - 0.45))))
            brilho = pygame.Surface((largura, rect.h + 8), pygame.SRCALPHA)
            pygame.draw.rect(brilho, (*cor_base[:3], min(210, alpha)), (0, 4, int(largura * min(1, t * 1.6)), rect.h), border_radius=4)
            for i in range(cura_linhas):
                lx = int((i / max(1, cura_linhas - 1)) * largura)
                pygame.draw.line(brilho, (210, 255, 240, alpha), (lx, 0), (lx, rect.h + 8), 1)
            surface.blit(brilho, (x0, rect.y - 4))

def _desenhar_brilho_loja(surface, rect, config_graficos=None):
    nivel = _obter_nivel_detalhes(config_graficos)
    if nivel == "baixo":
        camadas = 1
    elif nivel == "medio":
        camadas = 2
    else:
        camadas = 4
    tempo = pygame.time.get_ticks() * 0.004
    for i in range(camadas):
        margem = 8 + i * 7 + int(math.sin(tempo + i) * 2)
        alpha = max(35, 105 - i * 18)
        glow = pygame.Surface((rect.w + margem * 2, rect.h + margem * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 230, 120, alpha), glow.get_rect())
        surface.blit(glow, (rect.x - margem, rect.y - margem), special_flags=pygame.BLEND_RGBA_ADD)

def _escudo_eletrico_ativo(aurea, escudo_ativo):
    if not escudo_ativo:
        return False
    return str(aurea).strip().lower() == "devota"

def _desenhar_escudo_eletrico_personagem(surface, x, y, w, h, config_graficos=None):
    if surface is None:
        return
    try:
        x, y, w, h = int(x), int(y), int(w), int(h)
    except (TypeError, ValueError):
        return
    if w <= 0 or h <= 0:
        return

    nivel = _obter_nivel_detalhes(config_graficos)
    if nivel == "baixo":
        raios, particulas = 2, 5
    elif nivel == "medio":
        raios, particulas = 4, 8
    else:
        raios, particulas = 6, 12

    tempo = pygame.time.get_ticks() / 1000.0
    margem = 16
    aura_w = w + margem * 2
    aura_h = h + margem * 2
    aura = pygame.Surface((aura_w, aura_h), pygame.SRCALPHA)
    corpo = pygame.Rect(margem + int(w * 0.18), margem + int(h * 0.08), max(6, int(w * 0.64)), max(10, int(h * 0.86)))

    for i in range(raios):
        lado = i % 4
        fase = (tempo * (1.35 + i * 0.07) + i * 0.173) % 1.0
        jitter = math.sin(tempo * 15.0 + i * 2.4) * 3.0
        if lado == 0:
            base_x = corpo.left + corpo.w * fase
            base_y = corpo.top + jitter
        elif lado == 1:
            base_x = corpo.right + jitter
            base_y = corpo.top + corpo.h * fase
        elif lado == 2:
            base_x = corpo.right - corpo.w * fase
            base_y = corpo.bottom + jitter
        else:
            base_x = corpo.left + jitter
            base_y = corpo.bottom - corpo.h * fase

        pontos = []
        segmentos = 3 if nivel == "baixo" else 4
        ang = tempo * 8.0 + i * 1.9
        for j in range(segmentos):
            px = base_x + math.cos(ang + j * 1.7) * (j * 4 + 2)
            py = base_y + math.sin(ang + j * 2.1) * (j * 4 + 2)
            px = max(corpo.left - 5, min(corpo.right + 5, px))
            py = max(corpo.top - 6, min(corpo.bottom + 6, py))
            pontos.append((int(px), int(py)))
        if len(pontos) >= 2:
            pygame.draw.lines(aura, (0, 92, 255, 120), False, pontos, 2)
            pygame.draw.lines(aura, (185, 255, 255, 210), False, pontos, 1)

    for i in range(particulas):
        fase = (tempo * (0.9 + (i % 4) * 0.12) + i * 0.091) % 1.0
        lado = (i * 3) % 4
        if lado == 0:
            px = corpo.left + corpo.w * fase
            py = corpo.top + math.sin(tempo * 9.0 + i) * 4
        elif lado == 1:
            px = corpo.right + math.sin(tempo * 8.0 + i) * 4
            py = corpo.top + corpo.h * fase
        elif lado == 2:
            px = corpo.right - corpo.w * fase
            py = corpo.bottom + math.sin(tempo * 7.0 + i) * 4
        else:
            px = corpo.left + math.sin(tempo * 8.5 + i) * 4
            py = corpo.bottom - corpo.h * fase
        alpha = int(70 + 95 * ((math.sin(tempo * 6.5 + i) + 1.0) * 0.5))
        pygame.draw.circle(aura, (135, 248, 255, alpha), (int(px), int(py)), 1 if nivel == "baixo" else 2)

    surface.blit(aura, (x - margem, y - margem), special_flags=pygame.BLEND_RGBA_ADD)

def desenhar_efeitos_vanguarda(
    surface,
    pos_x_personagem,
    pos_y_personagem,
    largura_personagem,
    altura_personagem,
    inimigos,
    inimigos_em_chamas,
    duracao_incendio_ms=5000,
    aurea=None,
    config_graficos=None,
    aura_fogo_fim_ms=0,
):
    if surface is None or str(aurea).strip().lower() != "vanguarda":
        return

    nivel = _obter_nivel_detalhes(config_graficos)
    if nivel == "baixo":
        max_labaredas, max_brasas, max_chamas = 6, 8, 4
    elif nivel == "medio":
        max_labaredas, max_brasas, max_chamas = 11, 14, 7
    else:
        max_labaredas, max_brasas, max_chamas = 17, 22, 10

    agora = pygame.time.get_ticks()
    try:
        px = int(pos_x_personagem)
        py = int(pos_y_personagem)
        pw = int(largura_personagem)
        ph = int(altura_personagem)
    except (TypeError, ValueError):
        return

    centro_x = px + pw // 2
    centro_y = py + ph // 2
    alcance = max(76, int(max(pw, ph) * 1.45))
    inimigos = inimigos or []
    inimigos_em_chamas = inimigos_em_chamas or {}
    inimigos_proximos = []
    ha_inimigo_queimando = False

    for inimigo in inimigos:
        rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
        if rect is None or inimigo.get("invisivel", False):
            continue
        chave_chamas = inimigo.get("_vanguarda_id", id(inimigo))
        inicio_chamas = inimigos_em_chamas.get(chave_chamas)
        if inicio_chamas is not None and agora - inicio_chamas <= duracao_incendio_ms:
            ha_inimigo_queimando = True
        dist = math.hypot(rect.centerx - centro_x, rect.centery - centro_y)
        if dist <= alcance + max(rect.width, rect.height) * 0.4:
            inimigos_proximos.append(inimigo)

    raio_fogo_ativo = agora < aura_fogo_fim_ms or ha_inimigo_queimando

    if raio_fogo_ativo:
        margem = alcance + 28
        zona = pygame.Surface((margem * 2, margem * 2), pygame.SRCALPHA)
        zc = margem
        tempo = agora / 1000.0
        pulso = (math.sin(tempo * 7.2) + 1.0) * 0.5

        for i in range(max_labaredas):
            ang = (i / max_labaredas) * math.tau + tempo * (0.45 + (i % 3) * 0.08)
            raio_a = alcance * (0.58 + 0.28 * math.sin(tempo * 3.0 + i))
            raio_b = alcance * (0.92 + 0.10 * pulso)
            base = (
                zc + math.cos(ang) * raio_a,
                zc + math.sin(ang) * raio_a * 0.68,
            )
            ponta = (
                zc + math.cos(ang + 0.12 * math.sin(tempo + i)) * raio_b,
                zc + math.sin(ang + 0.12 * math.cos(tempo + i)) * raio_b * 0.68,
            )
            lateral = 8 + 5 * math.sin(tempo * 5.0 + i)
            p1 = (int(base[0] + math.cos(ang + math.pi / 2) * lateral), int(base[1] + math.sin(ang + math.pi / 2) * lateral))
            p2 = (int(ponta[0]), int(ponta[1]))
            p3 = (int(base[0] + math.cos(ang - math.pi / 2) * lateral), int(base[1] + math.sin(ang - math.pi / 2) * lateral))
            alpha = int(28 + 58 * pulso)
            pygame.draw.polygon(zona, (255, 72, 10, alpha), [p1, p2, p3])
            pygame.draw.line(zona, (255, 205, 80, min(150, alpha + 38)), p1, p2, 1)

        for alvo in inimigos_proximos[: max(2, max_labaredas // 3)]:
            rect = alvo["rect"]
            ax = zc + (rect.centerx - centro_x)
            ay = zc + (rect.centery - centro_y)
            pygame.draw.line(zona, (255, 92, 18, 72), (zc, zc), (int(ax), int(ay)), 2)
            pygame.draw.line(zona, (255, 220, 100, 48), (zc, zc), (int(ax), int(ay)), 1)

        surface.blit(zona, (centro_x - zc, centro_y - zc), special_flags=pygame.BLEND_RGBA_ADD)

    for inimigo in inimigos:
        rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
        if rect is None:
            continue
        chave_chamas = inimigo.get("_vanguarda_id", id(inimigo))
        inicio = inimigos_em_chamas.get(chave_chamas)
        if inicio is None or agora - inicio > duracao_incendio_ms:
            continue

        restante = max(0.0, 1.0 - ((agora - inicio) / max(1, duracao_incendio_ms)))
        fogo = pygame.Surface((rect.width + 28, rect.height + 34), pygame.SRCALPHA)
        ox = 14
        oy = 18
        fogo.fill((255, 72, 0, int(18 + 22 * restante)), pygame.Rect(ox, oy, rect.width, rect.height), special_flags=pygame.BLEND_RGBA_ADD)

        seed = chave_chamas % 997
        for i in range(max_chamas):
            fase = (agora * 0.006 + seed * 0.01 + i * 0.37) % 1.0
            fx = ox + int(rect.width * ((i + fase) / max(1, max_chamas)))
            base_y = oy + rect.height - int(rect.height * 0.10)
            altura = int(rect.height * (0.34 + 0.22 * math.sin(agora * 0.011 + i + seed)))
            largura = max(3, int(rect.width * 0.10))
            pts = [
                (fx - largura, base_y),
                (fx + int(math.sin(agora * 0.013 + i) * 5), base_y - altura),
                (fx + largura, base_y),
            ]
            alpha = int((92 + 70 * math.sin(agora * 0.01 + i) ** 2) * restante)
            pygame.draw.polygon(fogo, (255, 58, 0, alpha), pts)
            pygame.draw.polygon(fogo, (255, 214, 92, min(220, alpha + 35)), [
                (pts[0][0] + 2, pts[0][1]),
                (pts[1][0], pts[1][1] + max(2, altura // 4)),
                (pts[2][0] - 2, pts[2][1]),
            ])

        for i in range(max_brasas):
            fase = (agora * (0.0018 + i * 0.00006) + seed * 0.003 + i * 0.19) % 1.0
            bx = ox + int(rect.width * ((i * 0.37 + fase) % 1.0))
            by = oy + rect.height - int((rect.height + 22) * fase)
            alpha = int((120 - 70 * fase) * restante)
            pygame.draw.circle(fogo, (255, 178, 40, alpha), (bx, by), 1 if nivel == "baixo" else 2)

        surface.blit(fogo, (rect.x - ox, rect.y - oy), special_flags=pygame.BLEND_RGBA_ADD)

def racional_dilatacao_ativa(aurea, fim_ms, agora_ms=None):
    if str(aurea).strip().lower() != "racional":
        return False
    agora_ms = pygame.time.get_ticks() if agora_ms is None else agora_ms
    return agora_ms < fim_ms

RACIONAL_DILATACAO_DURACAO_MS = 8000
RACIONAL_DILATACAO_COOLDOWN_MS = 30000
RACIONAL_REBOTE_DURACAO_MS = 3000
RACIONAL_REBOTE_FATOR_MUNDO = 1.18
RACIONAL_PASSIVA_INTERVALO_MS = 4500
RACIONAL_PASSIVA_BASE = 5
RACIONAL_PASSIVA_POR_NIVEL = 2
RACIONAL_PASSIVA_TOLERANCIA_PX = 1.25

def ganho_passiva_racional(nivel_upgrade=0):
    return RACIONAL_PASSIVA_BASE + max(0, int(nivel_upgrade or 0)) * RACIONAL_PASSIVA_POR_NIVEL

def personagem_racional_imovel(x, y, ultimo_x, ultimo_y, tolerancia_px=RACIONAL_PASSIVA_TOLERANCIA_PX):
    try:
        return math.hypot(float(x) - float(ultimo_x), float(y) - float(ultimo_y)) <= float(tolerancia_px)
    except (TypeError, ValueError):
        return x == ultimo_x and y == ultimo_y

def tentar_ativar_dilatacao_racional(aurea, agora_ms, proximo_uso_ms=0):
    if str(aurea).strip().lower() != "racional" or agora_ms < proximo_uso_ms:
        return None, proximo_uso_ms
    fim_ms = agora_ms + RACIONAL_DILATACAO_DURACAO_MS
    return fim_ms, fim_ms + RACIONAL_DILATACAO_COOLDOWN_MS

def racional_rebote_ativo(aurea, fim_ms, agora_ms=None):
    if str(aurea).strip().lower() != "racional" or fim_ms <= 0:
        return False
    agora_ms = pygame.time.get_ticks() if agora_ms is None else agora_ms
    return fim_ms <= agora_ms < fim_ms + RACIONAL_REBOTE_DURACAO_MS

def fator_movimento_racional(aurea, fim_ms, agora_ms=None):
    return 1.35 if racional_dilatacao_ativa(aurea, fim_ms, agora_ms) else 1.0

_manifestacao_ativa_cached = None
_manifestacao_cache_ultimo_tick = 0

def obter_manifestacao_cached():
    global _manifestacao_ativa_cached, _manifestacao_cache_ultimo_tick
    try:
        agora = pygame.time.get_ticks()
    except Exception:
        agora = 0
    if _manifestacao_ativa_cached is None or (agora - _manifestacao_cache_ultimo_tick > 1000):
        try:
            from dados_manifestacoes import obter_manifestacao_ativa
            _manifestacao_ativa_cached = obter_manifestacao_ativa()
        except Exception:
            _manifestacao_ativa_cached = "eletrica"
        _manifestacao_cache_ultimo_tick = agora
    return _manifestacao_ativa_cached

def intervalo_disparo_racional(intervalo_base, aurea, fim_ms, agora_ms=None):
    import condutora_manifestacao
    agora = agora_ms if agora_ms is not None else pygame.time.get_ticks()
    fator_xor = condutora_manifestacao.obter_fator_cadencia_xor(agora)
    if fator_xor > 1.0:
        intervalo_base = int(intervalo_base / fator_xor)

    if obter_manifestacao_cached() == "retornante":
        try:
            import balanceamento
            mult = getattr(balanceamento, "RETORNANTE_ATTACK_SPEED_MULTIPLIER", 1.45)
            intervalo_base = int(intervalo_base * mult)
        except Exception:
            intervalo_base = int(intervalo_base * 1.45)

    if not racional_dilatacao_ativa(aurea, fim_ms, agora_ms):
        return intervalo_base
    return max(50, int(intervalo_base * 0.72))

def fator_mundo_racional(aurea, fim_ms, agora_ms=None):
    if racional_dilatacao_ativa(aurea, fim_ms, agora_ms):
        return 0.42
    if racional_rebote_ativo(aurea, fim_ms, agora_ms):
        return RACIONAL_REBOTE_FATOR_MUNDO
    return 1.0

IMPULSIVA_ABATES_POR_CICLO = 5
IMPULSIVA_DURACAO_BASE_MS = 3000
IMPULSIVA_DURACAO_POR_UPGRADE_MS = 500
IMPULSIVA_DANO_BASE = 1.3
IMPULSIVA_VELOCIDADE_BASE = 1.2

def criar_estado_impulsiva():
    return {
        "ativa": False,
        "nivel": 0,
        "fim_ms": 0,
        "panico_nivel": 0,
    }

def _duracao_impulsiva_ms(nivel_upgrade=0):
    return IMPULSIVA_DURACAO_BASE_MS + int(max(0, nivel_upgrade) * IMPULSIVA_DURACAO_POR_UPGRADE_MS)

def atualizar_ciclo_impulsiva(aurea, estado, abates_ciclo, agora_ms, nivel_upgrade=0):
    eventos = []
    if str(aurea).strip().lower() != "impulsiva":
        estado.update({"ativa": False, "nivel": 0, "fim_ms": 0, "panico_nivel": 0})
        return 0, eventos

    if estado.get("ativa") and agora_ms >= estado.get("fim_ms", 0):
        estado.update({"ativa": False, "nivel": 0, "fim_ms": 0})
        abates_ciclo = 0
        eventos.append({"tipo": "fim"})

    duracao = _duracao_impulsiva_ms(nivel_upgrade)
    while abates_ciclo >= IMPULSIVA_ABATES_POR_CICLO:
        abates_ciclo -= IMPULSIVA_ABATES_POR_CICLO
        if not estado.get("ativa"):
            estado["ativa"] = True
            estado["nivel"] = max(1, int(estado.get("nivel", 0)))
            estado["fim_ms"] = agora_ms + duracao
            eventos.append({"tipo": "ativou", "nivel": estado["nivel"]})
            continue

        sobra = estado.get("fim_ms", 0) - agora_ms
        if sobra >= 1000:
            estado["nivel"] = int(estado.get("nivel", 0)) + 1
            eventos.append({"tipo": "ascendeu", "nivel": estado["nivel"]})
        else:
            eventos.append({"tipo": "renovou", "nivel": estado["nivel"]})
        estado["fim_ms"] = agora_ms + duracao

    return abates_ciclo, eventos

def fator_dano_impulsiva(aurea, estado):
    if str(aurea).strip().lower() != "impulsiva" or not estado.get("ativa"):
        return 1.0
    return IMPULSIVA_DANO_BASE * (1.0 + 0.15 * int(estado.get("nivel", 0)))

def fator_velocidade_impulsiva(aurea, estado):
    if str(aurea).strip().lower() != "impulsiva" or not estado.get("ativa"):
        return 1.0
    return IMPULSIVA_VELOCIDADE_BASE * (1.0 + 0.15 * int(estado.get("nivel", 0)))

def quebrar_frenesi_impulsiva(aurea, estado):
    if str(aurea).strip().lower() != "impulsiva" or not estado.get("ativa"):
        return 0
    nivel = max(1, int(estado.get("nivel", 0)))
    estado.update({"ativa": False, "nivel": 0, "fim_ms": 0, "panico_nivel": nivel})
    return nivel

def consumir_multiplicador_panico_impulsiva(aurea, estado):
    if str(aurea).strip().lower() != "impulsiva":
        return 1.0
    nivel = int(estado.get("panico_nivel", 0))
    if nivel <= 0:
        return 1.0
    estado["panico_nivel"] = 0
    return 2.0 + 0.5 * nivel

DEVOTA_CARGAS_ESCUDO = 3
DEVOTA_DURACAO_PULSO_MS = 3000
DEVOTA_DURACAO_ROMPIMENTO_MS = 4500
DEVOTA_CURA_VIDA_PERDIDA = 0.10
DEVOTA_DANO_PULSO = 1.25
DEVOTA_DANO_ROMPIMENTO = 1.65
DEVOTA_VELOCIDADE_ROMPIMENTO = 0.9

def criar_estado_devota(ativa=False, agora_ms=0):
    return {
        "cargas": DEVOTA_CARGAS_ESCUDO if ativa else 0,
        "debuff_velocidade_fim_ms": 0,
        "buff_dano_fim_ms": 0,
        "buff_dano_multiplicador": 1.0,
        "cura_absorcao_pronta": False,
    }

def restaurar_escudo_devota(estado):
    estado["cargas"] = DEVOTA_CARGAS_ESCUDO
    estado["cura_absorcao_pronta"] = False

def absorver_hit_devota(aurea, escudo_ativo, estado, agora_ms):
    if str(aurea).strip().lower() != "devota" or not escudo_ativo:
        return False, escudo_ativo, False
    estado["cargas"] = max(0, int(estado.get("cargas", DEVOTA_CARGAS_ESCUDO)) - 1)
    estado["cura_absorcao_pronta"] = True
    estado["buff_dano_fim_ms"] = max(
        int(estado.get("buff_dano_fim_ms", 0)),
        agora_ms + DEVOTA_DURACAO_PULSO_MS,
    )
    estado["buff_dano_multiplicador"] = max(
        float(estado.get("buff_dano_multiplicador", 1.0)),
        DEVOTA_DANO_PULSO,
    )
    quebrado = estado["cargas"] <= 0
    if quebrado:
        escudo_ativo = False
        estado["debuff_velocidade_fim_ms"] = agora_ms + DEVOTA_DURACAO_ROMPIMENTO_MS
        estado["buff_dano_fim_ms"] = agora_ms + DEVOTA_DURACAO_ROMPIMENTO_MS
        estado["buff_dano_multiplicador"] = DEVOTA_DANO_ROMPIMENTO
    return True, escudo_ativo, quebrado

def consumir_cura_absorcao_devota(aurea, estado, vida_atual, vida_maxima_atual):
    if str(aurea).strip().lower() != "devota" or not estado.get("cura_absorcao_pronta"):
        return vida_atual, 0
    estado["cura_absorcao_pronta"] = False
    vida_maxima_segura = max(1, int(vida_maxima_atual))
    vida_atual = int(vida_atual)
    vida_perdida = max(0, vida_maxima_segura - vida_atual)
    if vida_perdida <= 0:
        return vida_atual, 0
    cura = max(3, int(vida_perdida * DEVOTA_CURA_VIDA_PERDIDA))
    nova_vida = min(vida_maxima_segura, vida_atual + cura)
    return nova_vida, nova_vida - vida_atual

def fator_velocidade_devota(aurea, estado, agora_ms=None):
    agora_ms = pygame.time.get_ticks() if agora_ms is None else agora_ms
    if str(aurea).strip().lower() == "devota" and agora_ms < estado.get("debuff_velocidade_fim_ms", 0):
        return DEVOTA_VELOCIDADE_ROMPIMENTO
    return 1.0

def fator_dano_devota(aurea, estado, agora_ms=None):
    agora_ms = pygame.time.get_ticks() if agora_ms is None else agora_ms
    if str(aurea).strip().lower() == "devota" and agora_ms < estado.get("buff_dano_fim_ms", 0):
        return float(estado.get("buff_dano_multiplicador", DEVOTA_DANO_PULSO))
    estado["buff_dano_multiplicador"] = 1.0
    return 1.0

def contar_inimigos_em_chamas_ativos(inimigos, inimigos_em_chamas, duracao_incendio_ms, agora_ms=None):
    agora_ms = pygame.time.get_ticks() if agora_ms is None else agora_ms
    total = 0
    for inimigo in inimigos or []:
        chave_chamas = inimigo.get("_vanguarda_id", id(inimigo)) if isinstance(inimigo, dict) else id(inimigo)
        inicio = (inimigos_em_chamas or {}).get(chave_chamas)
        if inicio is not None and agora_ms - inicio <= duracao_incendio_ms:
            total += 1
    return total

def cooldown_teleporte_vanguarda(base_ms, aurea, inimigos, inimigos_em_chamas, duracao_incendio_ms, agora_ms=None):
    if str(aurea).strip().lower() != "vanguarda":
        return base_ms
    queimando = contar_inimigos_em_chamas_ativos(inimigos, inimigos_em_chamas, duracao_incendio_ms, agora_ms)
    return int(base_ms * (1.0 + 0.15 * queimando))

def desenhar_efeito_racional_dilatacao(
    surface,
    pos_x_personagem,
    pos_y_personagem,
    largura_personagem,
    altura_personagem,
    fim_ms,
    aurea=None,
    config_graficos=None,
    movendo=False,
    direcao_movimento=None,
):
    if surface is None or not racional_dilatacao_ativa(aurea, fim_ms):
        return
    cfg = config_graficos or {}
    if cfg and not (cfg.get("efeitos_visuais", True) and cfg.get("particulas_ativas", True)):
        return

    nivel = _obter_nivel_detalhes(config_graficos)
    if nivel == "baixo":
        raios_borda, rastros = 5, 4
    elif nivel == "medio":
        raios_borda, rastros = 9, 7
    else:
        raios_borda, rastros = 15, 11

    agora = pygame.time.get_ticks()
    restante = max(0.0, min(1.0, (fim_ms - agora) / float(RACIONAL_DILATACAO_DURACAO_MS)))
    tempo = agora / 1000.0
    largura, altura = surface.get_size()

    overlay = pygame.Surface((largura, altura), pygame.SRCALPHA)
    overlay.fill((0, 34, 82, int(8 + 12 * restante)))

    for i in range(raios_borda):
        lado = i % 4
        fase = (tempo * (0.42 + i * 0.017) + i * 0.137) % 1.0
        comprimento = 28 + int(42 * (0.5 + 0.5 * math.sin(tempo * 6.0 + i)))
        zigue = 5 + (i % 3) * 2
        pontos = []
        if lado == 0:
            x0, y0 = int(largura * fase), 0
            direcao = (0, 1)
        elif lado == 1:
            x0, y0 = largura - 1, int(altura * fase)
            direcao = (-1, 0)
        elif lado == 2:
            x0, y0 = int(largura * (1.0 - fase)), altura - 1
            direcao = (0, -1)
        else:
            x0, y0 = 0, int(altura * (1.0 - fase))
            direcao = (1, 0)
        for j in range(4):
            desloc = j * comprimento / 3
            ruido = math.sin(tempo * 14.0 + i * 2.7 + j) * zigue
            if direcao[0] == 0:
                px = x0 + ruido
                py = y0 + direcao[1] * desloc
            else:
                px = x0 + direcao[0] * desloc
                py = y0 + ruido
            pontos.append((int(max(0, min(largura - 1, px))), int(max(0, min(altura - 1, py)))))
        pygame.draw.lines(overlay, (0, 95, 255, int(95 * restante)), False, pontos, 2)
        pygame.draw.lines(overlay, (170, 245, 255, int(165 * restante)), False, pontos, 1)

    try:
        px = int(pos_x_personagem)
        py = int(pos_y_personagem)
        pw = int(largura_personagem)
        ph = int(altura_personagem)
    except (TypeError, ValueError):
        pw = ph = 0

    if pw > 0 and ph > 0:
        cx = px + pw // 2
        cy = py + ph // 2
        direcoes = {
            "up": (0, 1),
            "down": (0, -1),
            "left": (1, 0),
            "right": (-1, 0),
        }
        rastro_dx, rastro_dy = direcoes.get(str(direcao_movimento).lower(), (0, 0))
        if not movendo:
            rastro_dx = rastro_dy = 0

        for i in range(rastros):
            ang = tempo * (8.0 + i * 0.23) + i * math.tau / max(1, rastros)
            raio_x = max(18, int(pw * (0.45 + (i % 3) * 0.06)))
            raio_y = max(24, int(ph * (0.48 + (i % 2) * 0.08)))
            desloc_rastro = 20 + (i % 5) * 7 if movendo else 0
            x1 = cx + math.cos(ang) * raio_x + rastro_dx * desloc_rastro
            y1 = cy + math.sin(ang) * raio_y + rastro_dy * desloc_rastro
            x2 = x1 - math.cos(ang + 0.6) * (14 + i % 4 * 3) + rastro_dx * (10 + i % 3 * 5)
            y2 = y1 - math.sin(ang + 0.6) * (14 + i % 4 * 3) + rastro_dy * (10 + i % 3 * 5)
            alpha = int((100 + 70 * math.sin(tempo * 10.0 + i) ** 2) * restante)
            pygame.draw.line(overlay, (0, 130, 255, alpha), (int(x1), int(y1)), (int(x2), int(y2)), 2)
            pygame.draw.line(overlay, (190, 255, 255, min(220, alpha + 45)), (int(x1), int(y1)), (int((x1 + x2) / 2), int((y1 + y2) / 2)), 1)

        particulas_raio = rastros * (3 if movendo else 2)
        for i in range(particulas_raio):
            fase = (tempo * (2.8 + i * 0.13) + i * 0.37) % 1.0
            lado = -1 if i % 2 else 1
            base_ang = tempo * 9.0 + i * 1.81
            corpo_x = math.cos(base_ang) * pw * random.uniform(0.24, 0.56)
            corpo_y = math.sin(base_ang * 1.17) * ph * random.uniform(0.18, 0.43)
            distancia = (18 + fase * 34) * (1.4 if movendo else 0.82)
            fora_x = math.cos(base_ang + lado * 0.4) * distancia + rastro_dx * (18 + fase * 42)
            fora_y = math.sin(base_ang + lado * 0.4) * distancia + rastro_dy * (18 + fase * 42)
            inicio = (int(cx + corpo_x), int(cy + corpo_y))
            meio = (int(cx + corpo_x * 0.65 + fora_x * 0.55 + math.sin(base_ang * 2.0) * 7), int(cy + corpo_y * 0.65 + fora_y * 0.55 + math.cos(base_ang * 1.7) * 7))
            fim = (int(cx + fora_x), int(cy + fora_y))
            alpha = int((190 - fase * 105) * restante)
            largura_raio = 2 if i % 4 == 0 else 1
            pygame.draw.lines(overlay, (255, 246, 170, alpha), False, [inicio, meio, fim], largura_raio)
            pygame.draw.lines(overlay, (85, 210, 255, min(210, alpha + 35)), False, [inicio, meio], 1)
            if i % 3 == 0:
                pygame.draw.circle(overlay, (255, 255, 230, min(210, alpha + 25)), fim, 2 if movendo else 1)

    surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

def _desenhar_vida_ruptura(display, hud, top, config_graficos=None, x=10):
    import Variaveis

    agora = pygame.time.get_ticks()
    vida = max(0.0, float(hud.get("vida", 0)))
    vida_maxima = max(1.0, float(hud.get("vida_maxima", 1)))
    pct = max(0.0, min(1.0, vida / vida_maxima))
    cor = (0, 150, 255) if hud.get("aurea") == "Devota" and hud.get("escudo_devota_ativo") else Variaveis.calcular_cor_barra_de_vida(pct * 100)
    pulso = (math.sin(agora * (0.018 if pct <= 0.3 else 0.008)) + 1.0) * 0.5

    painel = pygame.Rect(int(x), max(4, (top.height - 62) // 2), 272, 62)
    camada = pygame.Surface(painel.size, pygame.SRCALPHA)
    pygame.draw.rect(camada, (4, 5, 13, 212), camada.get_rect(), border_radius=8)
    pygame.draw.rect(camada, (*cor, 92), camada.get_rect().inflate(-2, -2), 1, border_radius=7)

    # Nucleo vital rachado: desenhado em codigo, sem depender do antigo sprite HEALTH.
    cx, cy = 30, 30
    brilho = int(45 + pulso * (95 if pct <= 0.3 else 45))
    pygame.draw.circle(camada, (*cor, brilho), (cx, cy), int(21 + pulso * 2), 2)
    cor_coracao = (*cor, 235)
    coracao = [(cx, cy + 18), (cx - 18, cy - 2), (cx - 17, cy - 11), (cx - 9, cy - 16), (cx, cy - 8), (cx + 9, cy - 16), (cx + 17, cy - 11), (cx + 18, cy - 2)]
    pygame.draw.polygon(camada, cor_coracao, coracao)
    pygame.draw.lines(camada, (5, 6, 13, 245), False, [(cx + 2, cy - 9), (cx - 4, cy), (cx + 4, cy + 5), (cx - 2, cy + 17)], 3)
    pygame.draw.line(camada, (255, 255, 255, 105), (cx - 11, cy - 8), (cx - 4, cy - 4), 2)

    fonte_label = get_cached_font(None, 15)
    fonte_valor = get_cached_font(None, 17)
    _texto_contorno(camada, fonte_label, "NUCLEO VITAL", tuple(cor), (58, 5))

    barra = pygame.Rect(58, 25, 202, 17)
    pygame.draw.rect(camada, (18, 15, 29, 245), barra, border_radius=4)
    preenchido = max(0, int(barra.w * pct))
    if preenchido > 0:
        pontos = [(barra.x, barra.y), (barra.x + preenchido, barra.y)]
        ponta = min(7, preenchido)
        pontos += [(barra.x + preenchido - ponta, barra.bottom), (barra.x, barra.bottom)]
        pygame.draw.polygon(camada, (*cor, 245), pontos)
        pygame.draw.line(camada, (255, 255, 255, 105), (barra.x + 3, barra.y + 3), (barra.x + max(3, preenchido - 4), barra.y + 3), 1)
    pygame.draw.rect(camada, (*cor, 150), barra, 1, border_radius=4)

    # Fissuras fixas tornam a leitura segmentada sem parecer uma barra generica.
    for i in range(1, 8):
        fx = barra.x + int(barra.w * i / 8)
        desvio = -2 if i % 2 else 2
        pygame.draw.line(camada, (4, 5, 13, 150), (fx + desvio, barra.y + 2), (fx - desvio, barra.bottom - 2), 1)

    _desenhar_efeitos_barra_vida(camada, barra, vida, vida_maxima, cor, "vida_ruptura", config_graficos)
    _texto_contorno(camada, fonte_valor, f"{int(vida)}/{int(vida_maxima)}", (245, 250, 255), (58, 44))
    if pct <= 0.3 and pulso > 0.55:
        pygame.draw.rect(camada, (255, 40, 65, int(35 + pulso * 45)), camada.get_rect().inflate(-3, -3), 2, border_radius=7)
    display.blit(camada, painel.topleft)


def _desenhar_hud_molduras(display):
    import Variaveis
    hud = _stage["hud"]
    agora_hud = pygame.time.get_ticks()
    if not hud or agora_hud - int(_stage.get("hud_atualizado_ms", 0)) > 1500:
        return
    if agora_hud - int(_stage.get("aura_atualizado_ms", 0)) > 1500:
        _stage["aura_widget"] = None
    rect = _stage["dst_rect"]
    screen_w, screen_h = display.get_size()
    top = pygame.Rect(0, 0, screen_w, max(0, rect.top))
    bottom = pygame.Rect(0, rect.bottom, screen_w, max(0, screen_h - rect.bottom))
    left = pygame.Rect(0, 0, rect.x, screen_h)
    right = pygame.Rect(rect.right, 0, screen_w - rect.right, screen_h)
    _desenhar_moldura(display, left, "esquerda")
    _desenhar_moldura(display, right, "direita")

    # As faixas sao parte da janela, mas ficam fora das coordenadas do mapa.
    if top.height > 0:
        pygame.draw.line(display, (0, 255, 220), (0, top.bottom - 2), (screen_w, top.bottom - 2), 2)
        pygame.draw.line(display, (180, 245, 255), (0, top.bottom - 4), (screen_w, top.bottom - 4), 1)
    if bottom.height > 0:
        pygame.draw.line(display, (0, 255, 220), (0, bottom.top + 1), (screen_w, bottom.top + 1), 2)
        pygame.draw.line(display, (180, 245, 255), (0, bottom.top + 3), (screen_w, bottom.top + 3), 1)

    if top.height >= 50:
        font_label = get_cached_font(None, max(14, min(18, top.height // 4)))
        font_valor_topo = get_cached_font(None, max(18, min(24, top.height // 3)))
        largura_painel_vida = 272
        if left.width >= largura_painel_vida + 16:
            vida_x = left.x + (left.width - largura_painel_vida) // 2
        else:
            vida_x = 10
        _desenhar_vida_ruptura(display, hud, top, hud.get("config_graficos"), vida_x)

        # Pontos/moedas e progresso da proxima compra.
        pontos_x = max(rect.left + 24, vida_x + largura_painel_vida + 28)
        modo_drops = False
        try:
            modo_drops = Variaveis.obter_modo_cartas() == "drops"
        except Exception:
            pass
        rotulo_pontos = "MOEDAS" if modo_drops else "PONTOS"
        valor_pontos = f"{int(hud['pontuacao_exib'])}" if modo_drops else f"{int(hud['pontuacao_exib'])}/{int(max(1, hud['custo_carta_atual']))}"
        _texto_contorno(display, font_label, rotulo_pontos, (255, 220, 90), (pontos_x, 11))
        if not modo_drops:
            _desenhar_barra_sidebar(display, pontos_x, 32, 150, 14, hud["pontuacao_exib"], max(1, hud["custo_carta_atual"]), (255, 210, 0))
        _texto_contorno(display, font_valor_topo, valor_pontos, (255, 255, 255), (pontos_x, 50))

        # Medidor exclusivo da aura. Quando nao existe, mostra apenas seu nome.
        aura_widget = _stage.get("aura_widget")
        if aura_widget is not None:
            aura_centro = rect.centerx
            aura_x = max(pontos_x + 178, aura_centro - aura_widget.get_width() // 2)
            aura_x = min(aura_x, screen_w - aura_widget.get_width() - 120)
            aura_y = max(4, (top.height - aura_widget.get_height()) // 2)
            display.blit(aura_widget, (aura_x, aura_y))
        elif hud.get("aurea"):
            aura_nome = str(hud["aurea"]).upper()
            aura_label_img = font_label.render("AURA", True, (155, 145, 255))
            aura_nome_img = font_valor_topo.render(aura_nome, True, (255, 230, 125))
            aura_centro = rect.centerx
            _texto_contorno(display, font_label, "AURA", (155, 145, 255), (aura_centro - aura_label_img.get_width() // 2, 10))
            _texto_contorno(display, font_valor_topo, aura_nome, (255, 230, 125), (aura_centro - aura_nome_img.get_width() // 2, 31))

        # Cronometro isolado no canto superior direito.
        try:
            tempo_txt = Variaveis.atualizar_cronometro()
        except Exception:
            tempo_txt = "00:00"
        tempo_label_img = font_label.render("TEMPO", True, (0, 255, 204))
        tempo_img = font_valor_topo.render(tempo_txt, True, (255, 255, 255))
        tempo_centro = right.centerx if right.width >= 110 else screen_w - max(48, tempo_img.get_width() // 2 + 18)
        _texto_contorno(display, font_label, "TEMPO", (0, 255, 204), (tempo_centro - tempo_label_img.get_width() // 2, 10))
        _texto_contorno(display, font_valor_topo, tempo_txt, (255, 255, 255), (tempo_centro - tempo_img.get_width() // 2, 34))

    if bottom.height >= 64:
        Variaveis.desenhar_habilidades(
            display,
            hud["cooldowns"],
            hud["dispositivo_ativo"],
            area_externa=bottom,
        )

    # O HUD agora pertence exclusivamente as faixas horizontalmente. As
    # laterais do fullscreen sao apenas letterbox decorativo, sem duplicatas.
    return

    painel_min = min(left.width, right.width)
    fonte_ajustada = painel_min < 170
    font_titulo = get_cached_font(None, 22 if fonte_ajustada else 24)
    font_valor = get_cached_font(None, 20 if fonte_ajustada else 22)
    font_peq = get_cached_font(None, 14 if fonte_ajustada else 16)

    if left.width >= 120:
        pad = 14 if left.width < 170 else 18
        w = left.width - pad * 2
        _texto_contorno(display, font_peq, "VIDA", (0, 255, 204), (pad, 36))
        _texto_contorno(display, font_valor, f"{int(max(0, hud['vida']))}/{int(max(1, hud['vida_maxima']))}", (255, 255, 255), (pad, 60))
        cor_vida = (0, 150, 255) if hud["aurea"] == "Devota" and hud["escudo_devota_ativo"] else Variaveis.calcular_cor_barra_de_vida((max(0, hud["vida"]) / max(1, hud["vida_maxima"])) * 100)
        _desenhar_barra_sidebar(display, pad, 92, w, 16, hud["vida"], hud["vida_maxima"], cor_vida)
        _desenhar_efeitos_barra_vida(display, pygame.Rect(pad, 92, w, 16), hud["vida"], hud["vida_maxima"], cor_vida, "sidebar", hud.get("config_graficos"))

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
        pad = 14 if right.width < 170 else 18
        x0 = right.x + pad
        w = right.width - pad * 2
        modo_drops = False
        try:
            modo_drops = Variaveis.obter_modo_cartas() == "drops"
        except Exception:
            pass
        _texto_contorno(display, font_peq, "MOEDAS" if modo_drops else "PONTOS", (255, 220, 90), (x0, 36))
        valor_pts = f"{int(hud['pontuacao_exib'])}" if modo_drops else f"{int(hud['pontuacao_exib'])}/{int(max(1, hud['custo_carta_atual']))}"
        _texto_contorno(display, font_valor, valor_pts, (255, 255, 255), (x0, 60))
        if not modo_drops:
            _desenhar_barra_sidebar(display, x0, 92, w, 16, hud["pontuacao_exib"], max(1, hud["custo_carta_atual"]), (255, 210, 0))

        y = 135
        if hud["eliminacoes_consecutivas"] > 0:
            _texto_contorno(display, font_titulo, f"COMBO: {hud['eliminacoes_consecutivas']}", (255, 255, 255), (x0, min(screen_h - 95, y + 18)))
            _texto_contorno(display, font_peq, f"Bônus: +{hud['bonus_pontuacao']}", (255, 255, 255), (x0, min(screen_h - 58, y + 50)))

def _flip_palco():
    if not _stage["active"]:
        return _stage["orig_flip"]()
    display = _stage["display"]
    frame = _stage.get("frame_surface")
    logical_rect = _stage.get("logical_dst_rect")
    if frame is not None and logical_rect is not None:
        # No modo janela o quadro inteiro e composto na resolucao logica e so
        # depois reduzido. Isso impede que o Windows corte uma janela maior que
        # o monitor e preserva a proporcao de todos os elementos do menu/HUD.
        physical_rect = _stage["dst_rect"]
        _stage["dst_rect"] = logical_rect
        try:
            _desenhar_fundo_palco(frame)
            frame.blit(_stage["game_surface"], logical_rect.topleft)
            _desenhar_hud_molduras(frame)
        finally:
            _stage["dst_rect"] = physical_rect

        display.fill((0, 0, 0))
        if frame.get_size() == display.get_size():
            display.blit(frame, (0, 0))
        else:
            display.blit(pygame.transform.smoothscale(frame, display.get_size()), (0, 0))
        return _stage["orig_flip"]()

    _desenhar_fundo_palco(display)
    _desenhar_moldura(display, pygame.Rect(0, 0, _stage["dst_rect"].x, display.get_height()), "esquerda")
    _desenhar_moldura(display, pygame.Rect(_stage["dst_rect"].right, 0, display.get_width() - _stage["dst_rect"].right, display.get_height()), "direita")
    scaled = pygame.transform.smoothscale(_stage["game_surface"], _stage["dst_rect"].size)
    display.blit(scaled, _stage["dst_rect"].topleft)
    _desenhar_hud_molduras(display)
    return _stage["orig_flip"]()

def _misturar_cores(cor_a, cor_b, peso):
    peso = max(0.0, min(1.0, peso))
    return tuple(int(cor_a[i] + (cor_b[i] - cor_a[i]) * peso) for i in range(3))

def tela_transicao_dimensional(tela, fase_destino, duracao_ms=1900):
    if tela is None:
        return
    limpar_hud_palco()

    paletas = {
        1: ((145, 54, 255), (222, 122, 255), "FASE 1"),
        2: ((28, 146, 255), (64, 238, 255), "FASE 2"),
        3: ((255, 205, 35), (255, 245, 132), "FASE 3"),
        4: ((138, 56, 255), (255, 207, 69), "FASE 4"),
        5: ((38, 226, 124), (34, 169, 255), "FASE 5"),
    }
    cor_primaria, cor_secundaria, rotulo_fase = paletas.get(fase_destino, paletas[1])

    alvo = _stage["display"] if _stage["active"] and _stage["display"] else tela
    flip = _stage["orig_flip"] if _stage["active"] and _stage["orig_flip"] else pygame.display.flip
    largura, altura = alvo.get_size()
    centro_x, centro_y = largura // 2, altura // 2
    raio_maximo = int(math.hypot(largura, altura) * 0.58)
    fonte_titulo = get_cached_font(None, max(32, min(64, largura // 18)))
    fonte_fase = get_cached_font(None, max(28, min(50, largura // 24)))
    fonte_pequena = get_cached_font(None, max(18, min(28, largura // 45)))

    particulas = []
    for i in range(150):
        particulas.append({
            "angulo": random.uniform(0, math.tau),
            "raio": random.uniform(35, raio_maximo),
            "vel": random.uniform(1.8, 4.2),
            "tamanho": random.randint(1, 4),
            "fase": random.random(),
        })

    clock = pygame.time.Clock()
    inicio = pygame.time.get_ticks()
    while True:
        agora = pygame.time.get_ticks()
        progresso = (agora - inicio) / max(1, duracao_ms)
        if progresso >= 1.0:
            break

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit()

        alvo.fill((2, 2, 10))
        brilho = math.sin(progresso * math.pi)
        giro = progresso * math.tau * 2.8

        camada = pygame.Surface((largura, altura), pygame.SRCALPHA)
        for faixa in range(22):
            raio = int((faixa / 21) * raio_maximo)
            alpha = max(0, int((1.0 - faixa / 22) * 90 * brilho))
            cor = _misturar_cores(cor_primaria, cor_secundaria, (faixa % 5) / 4)
            rect = pygame.Rect(0, 0, raio * 2, int(raio * 1.15))
            rect.center = (centro_x, centro_y)
            inicio_arco = giro + faixa * 0.32
            fim_arco = inicio_arco + math.pi * 1.15
            pygame.draw.arc(camada, (*cor, alpha), rect, inicio_arco, fim_arco, max(2, faixa // 3))

        for particula in particulas:
            particula["raio"] -= particula["vel"] * (1.0 + progresso * 2.2)
            if particula["raio"] < 18:
                particula["raio"] = raio_maximo * random.uniform(0.72, 1.0)
                particula["angulo"] = random.uniform(0, math.tau)
            angulo = particula["angulo"] + giro + particula["raio"] * 0.006
            x = centro_x + math.cos(angulo) * particula["raio"]
            y = centro_y + math.sin(angulo) * particula["raio"] * 0.56
            peso = (math.sin(particula["fase"] * math.tau + progresso * math.tau * 3) + 1) / 2
            cor = _misturar_cores(cor_primaria, cor_secundaria, peso)
            alpha = int(80 + 150 * brilho)
            pygame.draw.circle(camada, (*cor, alpha), (int(x), int(y)), particula["tamanho"])

        raio_portal = int((90 + raio_maximo * 0.18 * brilho) * (0.85 + progresso * 0.35))
        for i in range(7):
            raio = raio_portal + i * 18
            cor = _misturar_cores(cor_primaria, cor_secundaria, i / 6)
            alpha = max(25, int((180 - i * 18) * brilho))
            pygame.draw.circle(camada, (*cor, alpha), (centro_x, centro_y), raio, max(3, 10 - i))

        nucleo = pygame.Surface((raio_portal * 2, raio_portal * 2), pygame.SRCALPHA)
        pygame.draw.circle(nucleo, (0, 0, 8, 235), (raio_portal, raio_portal), raio_portal)
        pygame.draw.circle(nucleo, (*cor_secundaria, int(90 * brilho)), (raio_portal, raio_portal), max(4, raio_portal // 3))
        alvo.blit(camada, (0, 0))
        alvo.blit(nucleo, (centro_x - raio_portal, centro_y - raio_portal))

        texto = "ATRAVESSANDO O VORTEX TEMPORAL"
        subtitulo = f"DESTINO: {rotulo_fase}"
        fase_alpha = int(150 + 105 * brilho)
        titulo_surface = fonte_titulo.render(texto, True, (245, 248, 255))
        destino_surface = fonte_fase.render(subtitulo, True, _misturar_cores(cor_primaria, cor_secundaria, 0.5))
        dica_surface = fonte_pequena.render("sincronizando dimensao", True, (180, 198, 220))
        alvo.blit(titulo_surface, (centro_x - titulo_surface.get_width() // 2, int(altura * 0.16)))
        destino_surface.set_alpha(fase_alpha)
        alvo.blit(destino_surface, (centro_x - destino_surface.get_width() // 2, int(altura * 0.16) + titulo_surface.get_height() + 12))
        dica_surface.set_alpha(int(110 + 100 * brilho))
        alvo.blit(dica_surface, (centro_x - dica_surface.get_width() // 2, int(altura * 0.80)))

        flash = pygame.Surface((largura, altura), pygame.SRCALPHA)
        if progresso > 0.78:
            alpha_flash = int(((progresso - 0.78) / 0.22) * 120)
            flash.fill((*_misturar_cores(cor_primaria, cor_secundaria, 0.5), alpha_flash))
            alvo.blit(flash, (0, 0))

        flip()
        clock.tick(60)

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
    
    txt_moedas = fonte.render(f"Moedas: {fragmentos}", True, (255, 255, 255))
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
    config_graficos_hud = _carregar_config_graficos()

    if (
        None not in (pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem)
        and _escudo_eletrico_ativo(aurea, escudo_devota_ativo)
    ):
        _desenhar_escudo_eletrico_personagem(
            tela,
            pos_x_personagem,
            pos_y_personagem,
            largura_personagem,
            altura_personagem,
            config_graficos_hud,
        )

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
            "config_graficos": config_graficos_hud,
        }
        _stage["hud_atualizado_ms"] = pygame.time.get_ticks()
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

    rect_barra_vida = pygame.Rect(
        posicao_barra_vida[0],
        posicao_barra_vida[1],
        Variaveis.largura_barra_vida,
        Variaveis.altura_barra_vida,
    )

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
    _desenhar_efeitos_barra_vida(tela, rect_barra_vida, vida_segura, vida_maxima_segura, cor_barra, "principal", config_graficos_hud)
    pygame.draw.rect(
        tela,
        (0, 0, 0),
        rect_barra_vida,
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
        deve_desenhar_icones = Variaveis.deve_desenhar_habilidades(
            (pos_x_personagem, pos_y_personagem),
            (largura_personagem, altura_personagem),
        )

    if deve_desenhar_icones:
        Variaveis.desenhar_habilidades(
            tela,
            cooldowns,
            dispositivo_ativo,
            (pos_x_personagem, pos_y_personagem) if pos_x_personagem is not None and pos_y_personagem is not None else None,
        )

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
    config_graficos_hud = _carregar_config_graficos()
    pygame.draw.rect(surf_esq, (30, 20, 35), (20, 145, largura_barra, altura_barra), border_radius=5)
    
    # Preenchimento proporcional
    vida_porc = max(0.0, min(1.0, vida / vida_maxima))
    cor_vida = (0, 255, 128) if vida_porc > 0.4 else (255, 50, 50)
    if aurea == "Devota" and escudo_devota_ativo:
        cor_vida = (0, 240, 255)
    if vida_porc > 0:
        pygame.draw.rect(surf_esq, cor_vida, (20, 145, int(largura_barra * vida_porc), altura_barra), border_radius=5)
        # Detalhe de brilho
        pygame.draw.rect(surf_esq, (255, 255, 255, 80), (20, 145, int(largura_barra * vida_porc), 6), border_radius=2)
    _desenhar_efeitos_barra_vida(surf_esq, pygame.Rect(20, 145, largura_barra, altura_barra), vida, vida_maxima, cor_vida, "widescreen", config_graficos_hud)
        
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
    
    # Moedas coletadas
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
