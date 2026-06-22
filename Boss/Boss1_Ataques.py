import pygame
import math
import random


def _alpha(valor):
    return max(0, min(255, int(valor)))


def _particulas_com_glow(tela, particulas, raio_base=2):
    """Renderiza particulas em halo, cor e nucleo luminoso."""
    if not particulas:
        return
    overlay = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    for p in particulas:
        x, y = int(p.get("x", 0)), int(p.get("y", 0))
        cor = tuple(p.get("cor", (255, 255, 255)))[:3]
        a = _alpha(p.get("alpha", 255))
        raio = max(1, int(p.get("raio", raio_base)))
        pygame.draw.circle(overlay, (*cor, a // 5), (x, y), raio * 4)
        pygame.draw.circle(overlay, (*cor, a // 2), (x, y), raio * 2)
        pygame.draw.circle(overlay, (245, 255, 255, a), (x, y), raio)
    tela.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


def _anel_segmentado(surface, centro, raio, cor, alpha, rotacao=0.0, segmentos=12, largura=2, ocupacao=0.62):
    if raio <= 1:
        return
    rect = pygame.Rect(int(centro[0] - raio), int(centro[1] - raio), int(raio * 2), int(raio * 2))
    passo = math.tau / max(1, segmentos)
    for i in range(segmentos):
        inicio = rotacao + i * passo
        pygame.draw.arc(surface, (*cor[:3], _alpha(alpha)), rect, inicio, inicio + passo * ocupacao, largura)


def _circulo_glow(surface, centro, raio, cor, alpha=180, largura=0, camadas=4):
    raio = max(1, int(raio))
    for i in range(camadas, 0, -1):
        extra = i * 4
        a = _alpha(alpha / (i * 2.2))
        pygame.draw.circle(surface, (*cor[:3], a), centro, raio + extra, max(1, largura + i) if largura else 0)
    pygame.draw.circle(surface, (*cor[:3], _alpha(alpha)), centro, raio, largura)


def _raio_organico(surface, inicio, fim, cor, alpha, largura=2, fase=0.0, passos=9):
    dx, dy = fim[0] - inicio[0], fim[1] - inicio[1]
    dist = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / dist, dx / dist
    pontos = []
    for i in range(passos + 1):
        t = i / passos
        ondula = math.sin(t * math.pi * 5 + fase) * (5.0 + math.sin(t * math.pi) * 6.0)
        pontos.append((int(inicio[0] + dx * t + nx * ondula), int(inicio[1] + dy * t + ny * ondula)))
    pygame.draw.lines(surface, (*cor[:3], _alpha(alpha // 4)), False, pontos, largura + 5)
    pygame.draw.lines(surface, (*cor[:3], _alpha(alpha)), False, pontos, largura)


def _seta_fluxo(surface, pos, angulo, tamanho, cor, alpha):
    ux, uy = math.cos(angulo), math.sin(angulo)
    nx, ny = -uy, ux
    ponta = (pos[0] + ux * tamanho, pos[1] + uy * tamanho)
    cauda = (pos[0] - ux * tamanho * 0.6, pos[1] - uy * tamanho * 0.6)
    esq = (pos[0] + nx * tamanho * 0.45, pos[1] + ny * tamanho * 0.45)
    dire = (pos[0] - nx * tamanho * 0.45, pos[1] - ny * tamanho * 0.45)
    pygame.draw.polygon(surface, (*cor[:3], _alpha(alpha)), [ponta, esq, cauda, dire])


def _desenhar_bolha_premium(atk, tela, agora):
    _particulas_com_glow(tela, atk.particulas, 2)
    x = int(atk.target_pos[0] + atk.shake_offset[0])
    y = int(atk.target_pos[1] + atk.shake_offset[1])
    r = max(4, int(atk.raio_atual))
    t = agora * 0.001
    ov = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    pulso = (math.sin(t * 7.0) + 1.0) * 0.5

    if atk.estado == "telegraph":
        _circulo_glow(ov, (x, y), r, (70, 245, 255), 75 + pulso * 55, 0, 5)
        pygame.draw.circle(ov, (34, 6, 70, 115), (x, y), max(2, r - 4))
        pygame.draw.circle(ov, (105, 35, 190, 62), (x, y), max(2, int(r * 0.68)))
        _anel_segmentado(ov, (x, y), r + 12, (80, 255, 230), 220, t * 1.8, 14, 2)
        _anel_segmentado(ov, (x, y), max(8, r - 8), (255, 65, 190), 180, -t * 2.5, 9, 2, 0.42)
        for i in range(8):
            ang = t * 1.4 + i * math.tau / 8
            p1 = (x + math.cos(ang) * (r + 3), y + math.sin(ang) * (r + 3))
            p2 = (x + math.cos(ang + 0.18) * max(4, r * 0.35), y + math.sin(ang + 0.18) * max(4, r * 0.35))
            pygame.draw.line(ov, (135, 255, 240, 115), p1, p2, 1)
        _circulo_glow(ov, (x, y), int(5 + pulso * 4), (255, 245, 255), 245, 0, 3)
        _raio_organico(ov, (int(atk.boss_pos[0]), int(atk.boss_pos[1])), (x, y), (150, 70, 255), 135, 1, t * 5)
    elif atk.estado == "impacto":
        flash = 0.65 + 0.35 * math.sin(t * 55.0) ** 2
        _circulo_glow(ov, (x, y), r, (255, 20, 120), 195 * flash, 0, 6)
        pygame.draw.circle(ov, (75, 0, 125, 190), (x, y), r)
        _anel_segmentado(ov, (x, y), r, (255, 255, 255), 250, -t * 7, 18, 4, 0.52)
        _anel_segmentado(ov, (x, y), int(r * 0.62), (40, 255, 235), 225, t * 9, 11, 3, 0.35)
        for i in range(18):
            ang = i * math.tau / 18 + t * 0.4
            ini = (x + math.cos(ang) * r * 0.35, y + math.sin(ang) * r * 0.35)
            fim = (x + math.cos(ang) * r * 1.18, y + math.sin(ang) * r * 1.18)
            pygame.draw.line(ov, (255, 80 + i * 5 % 150, 225, 165), ini, fim, 2 if i % 3 == 0 else 1)
        _circulo_glow(ov, (x, y), max(5, int(r * 0.18)), (255, 255, 255), 255, 0, 5)
    elif atk.estado == "finalizacao":
        progresso = max(0.0, min(1.0, (atk.tempo_decorrido - atk.duracao * 0.9) / (atk.duracao * 0.1)))
        rf = int(atk.max_raio + progresso * 150)
        a = 255 * (1.0 - progresso)
        _circulo_glow(ov, (x, y), rf, (160, 55, 255), a, 3, 4)
        _anel_segmentado(ov, (x, y), int(rf * 0.78), (0, 245, 255), a * 0.7, t * 3, 16, 2)
    tela.blit(ov, (0, 0))


def _desenhar_diluvio_premium(atk, tela, agora):
    _particulas_com_glow(tela, atk.particulas, 1)
    t = agora * 0.001
    ov = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    for indice, g in enumerate(atk.gotas):
        st = g["estado_gota"]
        if st in ("aguardando", "terminado"):
            continue
        x, y = int(g["target_pos"][0]), int(g["target_pos"][1])
        r = max(2, int(g["raio_sombra"]))
        fase = t * 3.0 + indice * 0.73
        if st in ("no_ar", "caindo", "impacto"):
            urgente = st == "caindo"
            cor = (255, 55, 130) if urgente else (45, 210, 255)
            _circulo_glow(ov, (x, y), r, cor, 185 if urgente else 105, 0, 3)
            pygame.draw.ellipse(ov, (8, 18, 55, 155), (x - r, y - max(3, r // 2), r * 2, max(6, r)))
            _anel_segmentado(ov, (x, y), r + 9, cor, 235, fase, 10, 2, 0.46)
            for j in range(4):
                ang = fase + j * math.pi / 2
                _seta_fluxo(ov, (x + math.cos(ang) * (r + 20), y + math.sin(ang) * (r + 20)), ang + math.pi, 7, cor, 210)
            if st == "no_ar":
                restante = max(0.0, 1.0 - (agora - g["tempo_gota"]) / 2200.0)
                largura = int(10 + restante * 18)
                beam = pygame.Rect(x - largura // 2, 0, largura, max(1, y))
                pygame.draw.rect(ov, (30, 170, 255, 20), beam)
                pygame.draw.line(ov, (180, 250, 255, 100), (x, 0), (x, y), 2)
                _anel_segmentado(ov, (x, y), r + int(restante * 58), (255, 75, 150), 230, -fase * 1.7, 12, 2)
        if st == "caindo":
            gy = int(g["y_gota"])
            for largura, alpha in ((18, 28), (10, 65), (4, 180)):
                pygame.draw.line(ov, (30, 210, 255, alpha), (x, gy - 90), (x, gy + 4), largura)
            pygame.draw.polygon(ov, (45, 175, 255, 245), [(x, gy - 25), (x - 11, gy + 2), (x, gy + 11), (x + 11, gy + 2)])
            _circulo_glow(ov, (x, gy + 1), 7, (235, 255, 255), 255, 0, 3)
        elif st == "subindo":
            gy = int(g["y_gota"])
            _raio_organico(ov, (int(atk.boss_pos[0]), int(atk.boss_pos[1])), (int(atk.boss_pos[0]), gy), (20, 190, 255), 145, 2, fase)
        elif st == "poca":
            restante = max(0.0, 1.0 - (agora - g["tempo_poca_inicio"]) / max(1, g["duracao_poca"]))
            rr = max(2, r)
            pygame.draw.ellipse(ov, (30, 20, 100, int(125 * restante)), (x - rr, y - rr // 2, rr * 2, rr))
            for j in range(3):
                wobble = math.sin(fase * (1.0 + j * 0.12)) * 3
                rect = pygame.Rect(x - rr + j * 5, y - rr // 2 + j * 3, max(4, rr * 2 - j * 10), max(3, rr - j * 6))
                pygame.draw.ellipse(ov, (30 + j * 35, 170 + j * 20, 255, int((150 - j * 28) * restante)), rect, 2)
                pygame.draw.arc(ov, (220, 255, 255, int(190 * restante)), rect.move(int(wobble), 0), 3.4, 5.8, 2)
    tela.blit(ov, (0, 0))


def _segmentos_fora_zona(atk):
    if atk.direcao in ("esquerda", "direita"):
        return [(0, atk.safe_pos), (atk.safe_pos + atk.safe_span, atk.altura_mapa)]
    return [(0, atk.safe_pos), (atk.safe_pos + atk.safe_span, atk.largura_mapa)]


def _desenhar_mare_premium(atk, tela, agora):
    _particulas_com_glow(tela, atk.particulas, 2)
    t = agora * 0.001
    ov = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    horizontal = atk.direcao in ("esquerda", "direita")
    sinal = 1 if atk.direcao in ("esquerda", "cima") else -1
    angulo_fluxo = 0 if atk.direcao == "esquerda" else math.pi if atk.direcao == "direita" else math.pi / 2 if atk.direcao == "cima" else -math.pi / 2

    if atk.estado == "telegraph":
        progresso = max(0.0, min(1.0, atk.tempo_decorrido / atk.aviso_duracao))
        faixa = int(28 + progresso * 44)
        if horizontal:
            x = 0 if atk.direcao == "esquerda" else atk.largura_mapa - faixa
            pygame.draw.rect(ov, (20, 120, 210, 45 + int(progresso * 55)), (x, 0, faixa, atk.altura_mapa))
            safe = pygame.Rect(max(0, x - 8), atk.safe_pos, faixa + 16, atk.safe_span)
        else:
            y = 0 if atk.direcao == "cima" else atk.altura_mapa - faixa
            pygame.draw.rect(ov, (20, 120, 210, 45 + int(progresso * 55)), (0, y, atk.largura_mapa, faixa))
            safe = pygame.Rect(atk.safe_pos, max(0, y - 8), atk.safe_span, faixa + 16)
        pygame.draw.rect(ov, (20, 255, 205, 42), safe)
        pygame.draw.rect(ov, (150, 255, 230, 235), safe, 3)
        # Flechas sucessivas fazem a direcao e o ritmo da mare serem lidos de relance.
        limite = atk.altura_mapa if horizontal else atk.largura_mapa
        for pos in range(42, limite, 72):
            if atk.safe_pos <= pos <= atk.safe_pos + atk.safe_span:
                continue
            px = faixa * 0.5 if atk.direcao == "esquerda" else atk.largura_mapa - faixa * 0.5 if atk.direcao == "direita" else pos
            py = pos if horizontal else faixa * 0.5 if atk.direcao == "cima" else atk.altura_mapa - faixa * 0.5
            _seta_fluxo(ov, (px, py), angulo_fluxo, 11 + progresso * 5, (120, 235, 255), 100 + progresso * 140)
    elif atk.estado == "impacto":
        frente = float(atk.pos_travel)
        esp = atk.espessura_onda
        for inicio, fim in _segmentos_fora_zona(atk):
            if fim <= inicio:
                continue
            # Corpo profundo com faixas de corrente, em vez de um bloco azul plano.
            if horizontal:
                pygame.draw.rect(ov, (5, 55, 125, 145), (frente - esp / 2, inicio, esp, fim - inicio))
            else:
                pygame.draw.rect(ov, (5, 55, 125, 145), (inicio, frente - esp / 2, fim - inicio, esp))
            for camada in range(5):
                desloc = (camada - 2) * 11
                pontos = []
                for q in range(int(inicio), int(fim) + 1, 10):
                    ond = math.sin(q * 0.055 + t * (7 + camada)) * (7 + camada * 1.5)
                    if horizontal:
                        pontos.append((int(frente + sinal * (esp * 0.42 + desloc + ond)), q))
                    else:
                        pontos.append((q, int(frente + sinal * (esp * 0.42 + desloc + ond))))
                if len(pontos) > 1:
                    cor = (205, 255, 255, 230 - camada * 28) if camada < 2 else (20, 185, 255, 145)
                    pygame.draw.lines(ov, cor, False, pontos, 4 if camada == 0 else 2)
            for q in range(int(inicio) + 18, int(fim), 46):
                px, py = (frente + sinal * esp * 0.45, q) if horizontal else (q, frente + sinal * esp * 0.45)
                _circulo_glow(ov, (int(px), int(py)), 3 + int((q // 46) % 3), (220, 255, 255), 190, 0, 2)
        # Portao seguro recebe moldura viva para nunca se perder no espetaculo.
        if horizontal:
            safe = pygame.Rect(int(frente - esp * 0.58), atk.safe_pos, int(esp * 1.16), atk.safe_span)
        else:
            safe = pygame.Rect(atk.safe_pos, int(frente - esp * 0.58), atk.safe_span, int(esp * 1.16))
        pygame.draw.rect(ov, (30, 255, 205, 75), safe)
        pygame.draw.rect(ov, (175, 255, 235, 230), safe, 3)
    tela.blit(ov, (0, 0))


def _desenhar_areia_premium(atk, tela, agora):
    t = agora * 0.001
    ov = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    for idx, rdm in enumerate(atk.redemoinhos):
        x, y = int(rdm["center"][0]), int(rdm["center"][1])
        fase = t * 2.8 + idx * 1.7
        if atk.estado == "telegraph":
            progresso = max(0.0, min(1.0, atk.tempo_decorrido / 1200.0))
            _circulo_glow(ov, (x, y), atk.raio, (255, 164, 35), 80 + progresso * 70, 2, 4)
            _anel_segmentado(ov, (x, y), atk.raio, (255, 205, 90), 220, fase, 18, 3, 0.38)
            _anel_segmentado(ov, (x, y), max(8, int(atk.raio * (1.0 - progresso))), (255, 255, 230), 245, -fase * 2, 12, 2)
            for j in range(10):
                ang = fase + j * math.tau / 10
                _seta_fluxo(ov, (x + math.cos(ang) * atk.raio * 0.72, y + math.sin(ang) * atk.raio * 0.72), ang + math.pi * 0.72, 8, (255, 188, 70), 170)
        else:
            pygame.draw.circle(ov, (20, 10, 2, 190), (x, y), atk.raio)
            # Bracos espirais com cores e espessuras diferentes criam profundidade.
            for braco in range(7):
                pontos = []
                for passo in range(34):
                    frac = passo / 33.0
                    rr = atk.raio * (1.0 - frac * 0.88)
                    ang = fase + braco * math.tau / 7 + frac * math.tau * 1.65
                    pontos.append((int(x + math.cos(ang) * rr), int(y + math.sin(ang) * rr * 0.72)))
                pygame.draw.lines(ov, (120, 55, 12, 85), False, pontos, 9)
                pygame.draw.lines(ov, (245, 178, 65, 185), False, pontos, 3)
                pygame.draw.lines(ov, (255, 236, 160, 150), False, pontos, 1)
            _circulo_glow(ov, (x, y), 24, (255, 75, 10), 220, 0, 5)
            pygame.draw.circle(ov, (2, 1, 4, 250), (x, y), 17)
            _anel_segmentado(ov, (x, y), atk.raio - 5, (255, 190, 80), 150, -fase * 0.7, 24, 2, 0.28)
            for p in atk.particulas:
                px = int(x + math.cos(p["ang"] + rdm["angulo_rotacao"]) * p["r"])
                py = int(y + math.sin(p["ang"] + rdm["angulo_rotacao"]) * p["r"] * 0.72)
                _circulo_glow(ov, (px, py), 1, (255, 220, 145), 155, 0, 2)
    tela.blit(ov, (0, 0))


def _garra_poligono(centro, lado, abertura, escala=1.0):
    x, y = centro
    s = lado
    d = abertura
    return [
        (x + s * d, y - 48 * escala),
        (x + s * (d + 34 * escala), y - 31 * escala),
        (x + s * (d + 50 * escala), y - 4 * escala),
        (x + s * (d + 25 * escala), y + 2 * escala),
        (x + s * (d + 43 * escala), y + 35 * escala),
        (x + s * d, y + 49 * escala),
        (x + s * max(3, d - 14 * escala), y + 13 * escala),
        (x + s * max(2, d - 8 * escala), y - 14 * escala),
    ]


def _desenhar_pinca_premium(atk, tela, agora):
    _particulas_com_glow(tela, atk.particulas, 2)
    t = agora * 0.001
    x, y = int(atk.target_pos[0]), int(atk.target_pos[1])
    d = max(0.0, atk.clamp_dist)
    ov = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    pulso = (math.sin(t * 10.0) + 1.0) * 0.5
    cor = (255, 255, 255) if atk.estado == "impacto" else (190, 45, 255)
    _circulo_glow(ov, (x, y), max(8, int(d)), (70, 255, 235), 75 + pulso * 65, 2, 3)
    _anel_segmentado(ov, (x, y), max(22, int(d + 17)), (255, 65, 200), 220, t * 3.2, 8, 3, 0.34)
    pygame.draw.line(ov, (255, 80, 210, 105), (x - 62, y), (x + 62, y), 1)
    pygame.draw.line(ov, (70, 255, 235, 105), (x, y - 62), (x, y + 62), 1)
    for lado in (-1, 1):
        pontos = _garra_poligono((x, y), lado, d, 1.0)
        pygame.draw.polygon(ov, (*cor, 55), pontos)
        pygame.draw.lines(ov, (*cor, 245), True, pontos, 4 if atk.estado == "impacto" else 3)
        brilho = [(int(px - lado * 3), int(py)) for px, py in pontos[:5]]
        pygame.draw.lines(ov, (255, 185, 255, 170), False, brilho, 1)
        origem = (int(atk.boss_pos[0]), int(atk.boss_pos[1]))
        destino = (int(x + lado * (d + 38)), y)
        _raio_organico(ov, origem, destino, (170, 35, 255), 115, 1, t * 8 + lado)
    if atk.estado == "impacto":
        _circulo_glow(ov, (x, y), 13, (255, 255, 255), 255, 0, 5)
        for i in range(12):
            ang = i * math.tau / 12 + t
            pygame.draw.line(ov, (255, 55, 195, 190), (x, y), (x + math.cos(ang) * 70, y + math.sin(ang) * 70), 2)
    tela.blit(ov, (0, 0))


def _desenhar_investida_premium(atk, tela, agora):
    _particulas_com_glow(tela, atk.particulas, 2)
    t = agora * 0.001
    bx, by = float(atk.boss_pos[0]), float(atk.boss_pos[1])
    tx, ty = float(atk.target_pos[0]), float(atk.target_pos[1])
    ov = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    if atk.estado == "telegraph":
        dx, dy = tx - bx, ty - by
        dist = max(1.0, math.hypot(dx, dy))
        nx, ny = -dy / dist, dx / dist
        progresso = max(0.0, min(1.0, atk.tempo_decorrido / 2000.0))
        largura = 18 + progresso * 24
        corredor = [(bx + nx * largura, by + ny * largura), (tx + nx * largura, ty + ny * largura), (tx - nx * largura, ty - ny * largura), (bx - nx * largura, by - ny * largura)]
        pygame.draw.polygon(ov, (255, 30, 80, 28 + int(progresso * 32)), corredor)
        pygame.draw.lines(ov, (255, 70, 110, 130), False, corredor[:2], 2)
        pygame.draw.line(ov, (255, 45, 90, 65), (bx, by), (tx, ty), 12)
        pygame.draw.line(ov, (255, 90, 140, 150), (bx, by), (tx, ty), 4)
        pygame.draw.line(ov, (255, 255, 255, 235), (bx, by), (tx, ty), 1)
        for i in range(1, 8):
            frac = (i / 8.0 + t * 0.75) % 1.0
            px, py = bx + dx * frac, by + dy * frac
            _seta_fluxo(ov, (px, py), math.atan2(dy, dx), 8 + progresso * 4, (255, 120, 165), 180)
        raio = int(28 + (1.0 - progresso) * 42)
        _anel_segmentado(ov, (int(tx), int(ty)), raio, (255, 40, 100), 245, -t * 5, 12, 3, 0.42)
        _anel_segmentado(ov, (int(tx), int(ty)), max(10, raio - 13), (255, 255, 255), 190, t * 7, 8, 2)
    elif atk.estado == "impacto":
        ang = math.atan2(atk.charge_dir[1], atk.charge_dir[0])
        # Casulos atrasados sugerem velocidade sem duplicar o sprite do chefe.
        for i in range(1, 6):
            dist = i * 23
            px = int(bx - atk.charge_dir[0] * dist)
            py = int(by - atk.charge_dir[1] * dist)
            rr = max(5, 23 - i * 3)
            _circulo_glow(ov, (px, py), rr, (40, 180, 255), 115 - i * 14, 2, 3)
        for i in range(-4, 5):
            lateral = i * 13
            px = bx - atk.charge_dir[0] * 74 + math.cos(ang + math.pi / 2) * lateral
            py = by - atk.charge_dir[1] * 74 + math.sin(ang + math.pi / 2) * lateral
            fim = (px - atk.charge_dir[0] * (65 + abs(i) * 7), py - atk.charge_dir[1] * (65 + abs(i) * 7))
            pygame.draw.line(ov, (100, 225, 255, 120), (px, py), fim, 2 if i % 2 == 0 else 1)
        _circulo_glow(ov, (int(bx), int(by)), 30, (255, 90, 170), 165, 3, 4)
    tela.blit(ov, (0, 0))


def _desenhar_ataque_premium(atk, tela):
    agora = pygame.time.get_ticks()
    nome = atk.__class__.__name__
    if nome == "BolhaPressaoTemporal":
        _desenhar_bolha_premium(atk, tela, agora)
    elif nome == "DiluvioSuspenso":
        _desenhar_diluvio_premium(atk, tela, agora)
    elif nome == "MareFraturada":
        _desenhar_mare_premium(atk, tela, agora)
    elif nome == "AreiaViva":
        _desenhar_areia_premium(atk, tela, agora)
    elif nome == "PincaRuptura":
        _desenhar_pinca_premium(atk, tela, agora)
    elif nome == "InvestidaTemporal":
        _desenhar_investida_premium(atk, tela, agora)
    else:
        atk.draw(tela)


def desenhar_onda_transicao_premium(tela, wave, tempo_atual):
    """Onda de mudanca de estagio com fissuras, profundidade e saida legivel."""
    x, y = int(wave["x"]), int(wave["y"])
    raio = max(1, int(wave["raio"]))
    largura = max(2, int(wave["largura_linha"]))
    t = tempo_atual * 0.001
    ov = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    rect = pygame.Rect(x - raio, y - raio, raio * 2, raio * 2)
    completa = wave.get("tipo") == "completa"

    if completa:
        _circulo_glow(ov, (x, y), raio, (155, 35, 255), 175, largura + 2, 4)
        pygame.draw.circle(ov, (20, 245, 255, 235), (x, y), raio, max(2, largura // 3))
        _anel_segmentado(ov, (x, y), raio + largura + 5, (255, 90, 220), 180, t * 2.6, 28, 2, 0.34)
    else:
        centro_gap = float(wave["angulo_abertura_centro"])
        tamanho_gap = float(wave["tamanho_abertura"])
        inicio = centro_gap + tamanho_gap / 2
        fim = centro_gap - tamanho_gap / 2 + math.tau
        for extra, cor, alpha, lw in (
            (8, (145, 25, 255), 65, largura + 10),
            (3, (210, 45, 255), 165, largura + 4),
            (0, (30, 245, 255), 235, max(2, largura // 3)),
        ):
            rr = raio + extra
            pygame.draw.arc(ov, (*cor, alpha), (x - rr, y - rr, rr * 2, rr * 2), inicio, fim, lw)

        # As duas mandibulas de luz enquadram a abertura segura.
        for borda, sentido in ((centro_gap - tamanho_gap / 2, 1), (centro_gap + tamanho_gap / 2, -1)):
            p1 = (x + math.cos(borda) * (raio - 18), y + math.sin(borda) * (raio - 18))
            p2 = (x + math.cos(borda) * (raio + 25), y + math.sin(borda) * (raio + 25))
            pygame.draw.line(ov, (180, 255, 235, 235), p1, p2, 4)
            _seta_fluxo(ov, p2, centro_gap + math.pi * sentido * 0.08, 10, (90, 255, 215), 220)

    # Fragmentos viajam na crista e eliminam a sensacao de circulo geometrico cru.
    for i in range(24):
        ang = i * math.tau / 24 + t * (0.55 if i % 2 else -0.35)
        if not completa:
            delta = (ang - float(wave["angulo_abertura_centro"]) + math.pi) % math.tau - math.pi
            if abs(delta) < float(wave["tamanho_abertura"]) / 2:
                continue
        rr = raio + math.sin(t * 6 + i) * 5
        px, py = x + math.cos(ang) * rr, y + math.sin(ang) * rr
        tang = ang + math.pi / 2
        pontos = [
            (px + math.cos(tang) * 7, py + math.sin(tang) * 7),
            (px + math.cos(ang) * 4, py + math.sin(ang) * 4),
            (px - math.cos(tang) * 7, py - math.sin(tang) * 7),
            (px - math.cos(ang) * 3, py - math.sin(ang) * 3),
        ]
        pygame.draw.polygon(ov, (195, 105, 255, 145), pontos)
        pygame.draw.line(ov, (210, 255, 255, 205), pontos[0], pontos[2], 1)
    tela.blit(ov, (0, 0))

class AtaqueBoss1:
    """
    Classe base para todos os ataques do Boss 1.
    Garante uma interface unificada com telegraph, impacto, finalização e controle de dano único.
    """
    def __init__(self, nome, duracao, boss_pos, jogador_pos, largura_mapa, altura_mapa):
        self.nome = nome
        self.estado = "telegraph"  # telegraph, impacto, finalizacao, terminado
        self.tempo_inicio = pygame.time.get_ticks()
        self.duracao = duracao
        self.danificou = False
        self.boss_pos = list(boss_pos)
        self.jogador_pos = list(jogador_pos)
        self.alvo_fixo = None
        self.largura_mapa = largura_mapa
        self.altura_mapa = altura_mapa
        self.particulas = []
        self.tempo_decorrido = 0

    def update(self, dt, pos_jogador, boss_pos, tempo_atual):
        self.tempo_decorrido = tempo_atual - self.tempo_inicio
        if self.tempo_decorrido >= self.duracao:
            self.estado = "terminado"
        self.boss_pos = list(boss_pos)

    def draw(self, tela):
        pass

    def verificar_colisao(self, pos_jogador, largura_j, altura_j, vida, vida_maxima, escudo_ativo, dano_adicional):
        return pos_jogador[0], pos_jogador[1], vida, escudo_ativo


# --- 1. BOLHA DE PRESSÃO TEMPORAL ---
class BolhaPressaoTemporal(AtaqueBoss1):
    def __init__(self, boss_pos, jogador_pos, largura_mapa, altura_mapa):
        super().__init__("Bolha de Pressao Temporal", 3200, boss_pos, jogador_pos, largura_mapa, altura_mapa)
        self.target_pos = list(jogador_pos)  # Posição onde a bolha vai explodir
        self.max_raio = 90
        self.raio_atual = 10
        self.shake_offset = [0, 0]

    def update(self, dt, pos_jogador, boss_pos, tempo_atual):
        super().update(dt, pos_jogador, boss_pos, tempo_atual)
        if self.estado == "terminado":
            return
        
        progresso = self.tempo_decorrido / self.duracao

        # Estágios da Bolha
        if progresso < 0.25:
            # Estágio 1: núcleo pequeno (Telegraph)
            self.estado = "telegraph"
            self.raio_atual = 15 + math.sin(tempo_atual * 0.02) * 3
            # Gerar partículas sugadas para o centro
            if random.random() < 0.3:
                ang = random.uniform(0, math.pi * 2)
                dist = random.uniform(50, 120)
                self.particulas.append({
                    "x": self.target_pos[0] + math.cos(ang) * dist,
                    "y": self.target_pos[1] + math.sin(ang) * dist,
                    "vx": -math.cos(ang) * 3.0,
                    "vy": -math.sin(ang) * 3.0,
                    "alpha": 255,
                    "cor": (0, 255, 204)
                })
        elif progresso < 0.50:
            # Estágio 2: bolha maior translúcida
            self.raio_atual = 50 + math.sin(tempo_atual * 0.01) * 5
            if random.random() < 0.5:
                ang = random.uniform(0, math.pi * 2)
                dist = random.uniform(60, 150)
                self.particulas.append({
                    "x": self.target_pos[0] + math.cos(ang) * dist,
                    "y": self.target_pos[1] + math.sin(ang) * dist,
                    "vx": -math.cos(ang) * 4.0,
                    "vy": -math.sin(ang) * 4.0,
                    "alpha": 255,
                    "cor": (140, 100, 255)
                })
        elif progresso < 0.75:
            # Estágio 3: bolha tremendo e pulsando
            self.raio_atual = 65 + math.sin(tempo_atual * 0.05) * 8
            self.shake_offset = [random.randint(-4, 4), random.randint(-4, 4)]
            if random.random() < 0.7:
                ang = random.uniform(0, math.pi * 2)
                dist = random.uniform(40, 100)
                self.particulas.append({
                    "x": self.target_pos[0] + math.cos(ang) * dist,
                    "y": self.target_pos[1] + math.sin(ang) * dist,
                    "vx": -math.cos(ang) * 5.0,
                    "vy": -math.sin(ang) * 5.0,
                    "alpha": 255,
                    "cor": (255, 0, 128)
                })
        elif progresso < 0.90:
            # Estágio 4: impacto (Explosão em anel)
            self.estado = "impacto"
            self.shake_offset = [0, 0]
            self.raio_atual += (self.max_raio - self.raio_atual) * 0.15
            # Gerar faíscas da explosão
            for _ in range(3):
                ang = random.uniform(0, math.pi * 2)
                spd = random.uniform(3, 8)
                self.particulas.append({
                    "x": self.target_pos[0],
                    "y": self.target_pos[1],
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "alpha": 255,
                    "cor": random.choice([(255, 0, 100), (180, 50, 255), (0, 255, 230)])
                })
        else:
            # Finalização (Anel se dissipa)
            self.estado = "finalizacao"
            self.raio_atual += 10
            
        # Atualizar partículas internas
        for p in self.particulas[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["alpha"] -= 8
            if p["alpha"] <= 0:
                self.particulas.remove(p)

    def draw(self, tela):
        # Desenhar partículas
        for p in self.particulas:
            surf_p = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(surf_p, p["cor"] + (p["alpha"],), (3, 3), 3)
            tela.blit(surf_p, (int(p["x"] - 3), int(p["y"] - 3)))

        x_c = int(self.target_pos[0] + self.shake_offset[0])
        y_c = int(self.target_pos[1] + self.shake_offset[1])
        r = int(self.raio_atual)

        if self.estado == "telegraph":
            # Círculo translúcido com borda neon
            surf = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
            pygame.draw.circle(surf, (0, 255, 204, 30), (r + 5, r + 5), r)
            pygame.draw.circle(surf, (0, 255, 204, 180), (r + 5, r + 5), r, 2)
            tela.blit(surf, (x_c - r - 5, y_c - r - 5))
            
            # Linha de mira sutil ligando o Boss ao centro da bolha
            pygame.draw.line(tela, (0, 255, 204, 80), (int(self.boss_pos[0]), int(self.boss_pos[1])), (x_c, y_c), 1)

        elif self.estado == "impacto":
            # Bolha piscando roxo/vermelho com anel de impacto brilhante
            cor = (255, 30, 100) if (pygame.time.get_ticks() // 50) % 2 == 0 else (160, 0, 255)
            surf = pygame.Surface((r * 2 + 20, r * 2 + 20), pygame.SRCALPHA)
            pygame.draw.circle(surf, cor + (90,), (r + 10, r + 10), r)
            pygame.draw.circle(surf, (255, 255, 255, 220), (r + 10, r + 10), r, 3)
            tela.blit(surf, (x_c - r - 10, y_c - r - 10))

        elif self.estado == "finalizacao":
            # Anel se expandindo e esmaecendo
            r_fade = int(self.max_raio + (self.tempo_decorrido - self.duracao * 0.9) * 0.8)
            alpha = max(0, int(255 * (1.0 - (self.tempo_decorrido / self.duracao))))
            if r_fade > 0 and alpha > 0:
                surf = pygame.Surface((r_fade * 2 + 10, r_fade * 2 + 10), pygame.SRCALPHA)
                pygame.draw.circle(surf, (140, 50, 255, alpha), (r_fade + 5, r_fade + 5), r_fade, 3)
                tela.blit(surf, (x_c - r_fade - 5, y_c - r_fade - 5))

    def verificar_colisao(self, pos_jogador, largura_j, altura_j, vida, vida_maxima, escudo_ativo, dano_adicional):
        if self.estado == "impacto" and not self.danificou:
            player_rect = pygame.Rect(pos_jogador[0], pos_jogador[1], largura_j, altura_j)
            # Aproximação circular para colisão da bolha
            bubble_center = self.target_pos
            px = max(player_rect.left, min(bubble_center[0], player_rect.right))
            py = max(player_rect.top, min(bubble_center[1], player_rect.bottom))
            dist = math.sqrt((px - bubble_center[0])**2 + (py - bubble_center[1])**2)
            
            if dist <= self.raio_atual:
                self.danificou = True
                if escudo_ativo:
                    return pos_jogador[0], pos_jogador[1], vida, False  # Consome escudo
                else:
                    dano = (vida_maxima * 0.15) + dano_adicional
                    return pos_jogador[0], pos_jogador[1], max(0.0, vida - dano), escudo_ativo
                    
        return pos_jogador[0], pos_jogador[1], vida, escudo_ativo


# --- 2. DILÚVIO SUSPENSO ---
class DiluvioSuspenso(AtaqueBoss1):
    def __init__(self, boss_pos, jogador_pos, largura_mapa, altura_mapa, num_gotas=10):
        super().__init__("Diluvio Suspenso", 6500, boss_pos, jogador_pos, largura_mapa, altura_mapa)
        self.gotas = []
        self.notificacoes = []
        # Spawn gotas
        for i in range(num_gotas):
            self.gotas.append({
                "target_pos": list(jogador_pos),
                "y_gota": -100.0,  # Começa no topo/céu
                "estado_gota": "aguardando",  # aguardando, subindo, no_ar, caindo, impacto, poca, terminado
                "tempo_gota": pygame.time.get_ticks() + i * 300, # Atraso procedural
                "raio_sombra": 0.0,
                "duracao_poca": 3500,
                "tempo_poca_inicio": 0,
                "dano_poca_cooldown": 0,
                "danificou": False
            })

    def update(self, dt, pos_jogador, boss_pos, tempo_atual):
        super().update(dt, pos_jogador, boss_pos, tempo_atual)
        if self.estado == "terminado":
            return

        pos_alvo = self.alvo_fixo or pos_jogador
        todos_terminados = True
        
        for g in self.gotas:
            st = g["estado_gota"]
            if st != "terminado":
                todos_terminados = False

            if st == "aguardando" and tempo_atual >= g["tempo_gota"]:
                g["estado_gota"] = "subindo"
                g["tempo_gota"] = tempo_atual
                g["y_gota"] = boss_pos[1]
                g["target_pos"] = list(pos_alvo) # Trava a mira na posicao atual do alvo.
                # Criar partículas saindo do boss para cima
                for _ in range(5):
                    self.particulas.append({
                        "x": boss_pos[0],
                        "y": boss_pos[1],
                        "vx": random.uniform(-1.5, 1.5),
                        "vy": random.uniform(-10.0, -6.0),
                        "alpha": 255,
                        "cor": (0, 180, 255)
                    })

            elif st == "subindo":
                # Gota subindo rápido
                g["y_gota"] -= 16.0 * dt
                # Criar rastro azul
                if random.random() < 0.4:
                    self.particulas.append({
                        "x": boss_pos[0] + random.uniform(-5, 5),
                        "y": g["y_gota"],
                        "vx": random.uniform(-0.5, 0.5),
                        "vy": random.uniform(1, 3),
                        "alpha": 200,
                        "cor": (0, 200, 255)
                    })
                if g["y_gota"] < -150:
                    g["estado_gota"] = "no_ar"
                    g["tempo_gota"] = tempo_atual

            elif st == "no_ar":
                # Sombra no chão cresce e escurece (dura 2.2 segundos)
                decorrido_no_ar = tempo_atual - g["tempo_gota"]
                g["raio_sombra"] = min(35.0, (decorrido_no_ar / 2200.0) * 35.0)
                if decorrido_no_ar >= 2200:
                    g["estado_gota"] = "caindo"
                    g["tempo_gota"] = tempo_atual
                    g["y_gota"] = -150.0

            elif st == "caindo":
                # Gota caindo verticalmente super rápido
                g["y_gota"] += 28.0 * dt
                if g["y_gota"] >= g["target_pos"][1]:
                    g["estado_gota"] = "impacto"
                    g["tempo_gota"] = tempo_atual

            elif st == "impacto":
                # Respingo e aplicação de dano
                g["estado_gota"] = "poca"
                g["tempo_poca_inicio"] = tempo_atual
                # Gerar respingos (partículas de água)
                for _ in range(12):
                    ang = random.uniform(0, math.pi * 2)
                    spd = random.uniform(2.0, 5.0)
                    self.particulas.append({
                        "x": g["target_pos"][0],
                        "y": g["target_pos"][1],
                        "vx": math.cos(ang) * spd,
                        "vy": math.sin(ang) * spd - 2, # Voa um pouco para cima
                        "alpha": 255,
                        "cor": (0, 150, 255)
                    })

            elif st == "poca":
                # Poça encolhe no final
                decorrido_poca = tempo_atual - g["tempo_poca_inicio"]
                if decorrido_poca >= g["duracao_poca"]:
                    g["estado_gota"] = "terminado"
                elif decorrido_poca >= g["duracao_poca"] - 500:
                    # Encolhendo
                    restante = g["duracao_poca"] - decorrido_poca
                    g["raio_sombra"] = 35.0 * (restante / 500.0)

        if todos_terminados:
            self.estado = "terminado"

        # Atualizar partículas
        for p in self.particulas[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["alpha"] -= 6
            if p["alpha"] <= 0:
                self.particulas.remove(p)

    def draw(self, tela):
        # Partículas
        for p in self.particulas:
            surf_p = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(surf_p, p["cor"] + (p["alpha"],), (2, 2), 2)
            tela.blit(surf_p, (int(p["x"] - 2), int(p["y"] - 2)))

        tempo_atual = pygame.time.get_ticks()

        for g in self.gotas:
            tx, ty = int(g["target_pos"][0]), int(g["target_pos"][1])
            st = g["estado_gota"]

            # 1. Desenhar a Sombra / Poça / Telegraph no chão
            if st in ["no_ar", "caindo", "impacto"]:
                r = int(g["raio_sombra"])
                if r > 0:
                    # Pulsar a sombra se estiver quase caindo
                    alpha = 150
                    if st == "caindo":
                        alpha = 210 if (tempo_atual // 40) % 2 == 0 else 120
                    surf_s = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
                    pygame.draw.circle(surf_s, (0, 100, 200, alpha), (r + 5, r + 5), r)
                    pygame.draw.circle(surf_s, (0, 200, 255, alpha), (r + 5, r + 5), r, 2)
                    tela.blit(surf_s, (tx - r - 5, ty - r - 5))

                if st == "no_ar":
                    decorrido_no_ar = tempo_atual - g["tempo_gota"]
                    restante = 2200 - decorrido_no_ar
                    
                    # Coluna de luz vertical indicando a queda iminente (Telegraph aéreo)
                    surf_beam = pygame.Surface((12, ty), pygame.SRCALPHA)
                    pygame.draw.rect(surf_beam, (0, 180, 255, 20), (0, 0, 12, ty))
                    pygame.draw.rect(surf_beam, (0, 230, 255, 45), (4, 0, 4, ty))
                    tela.blit(surf_beam, (tx - 6, 0))

                    # Retículo/Anel que encolhe em direção ao alvo
                    r_shrink = r + int(max(0.0, (restante / 2200.0) * 55.0))
                    pygame.draw.circle(tela, (255, 50, 50, 160), (tx, ty), r_shrink, 2)

                    # Sinal de alerta (!) flutuando acima do alvo
                    pulse = 1.0 + 0.12 * math.sin(tempo_atual * 0.015)
                    pt1 = (tx, int(ty - 45 * pulse))
                    pt2 = (int(tx - 12 * pulse), int(ty - 20 * pulse))
                    pt3 = (int(tx + 12 * pulse), int(ty - 20 * pulse))
                    pygame.draw.polygon(tela, (255, 50, 50), [pt1, pt2, pt3])
                    pygame.draw.polygon(tela, (255, 255, 255), [pt1, pt2, pt3], 1)
                    # Exclamação no triângulo
                    pygame.draw.line(tela, (255, 255, 255), (tx, int(ty - 38 * pulse)), (tx, int(ty - 28 * pulse)), 2)
                    pygame.draw.circle(tela, (255, 255, 255), (tx, int(ty - 24 * pulse)), 2)

            elif st == "poca":
                # Desenhar a poça temporal azul/roxa translúcida
                r = int(g["raio_sombra"])
                if r > 0:
                    surf_p = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
                    # Poça ondulante
                    ondulacao = math.sin(tempo_atual * 0.005 + tx) * 2.0
                    pygame.draw.circle(surf_p, (80, 50, 230, 90), (r + 5, r + 5), int(r + ondulacao))
                    pygame.draw.circle(surf_p, (0, 150, 255, 140), (r + 5, r + 5), int(r + ondulacao), 2)
                    tela.blit(surf_p, (tx - r - 5, ty - r - 5))

                    # Bolhas corrosivas que sobem da poça
                    if random.random() < 0.08:
                        self.particulas.append({
                            "x": tx + random.uniform(-r, r),
                            "y": ty + random.uniform(-r * 0.3, r * 0.3),
                            "vx": random.uniform(-0.1, 0.1),
                            "vy": random.uniform(-0.6, -0.2),
                            "alpha": 180,
                            "cor": (0, 180, 255)
                        })

            # 2. Desenhar a Gota Física no ar
            if st == "subindo":
                # Desenha linha de subida do boss
                pygame.draw.line(tela, (0, 180, 255, 150), (int(self.boss_pos[0]), int(g["y_gota"] + 20)), (int(self.boss_pos[0]), int(g["y_gota"])), 2)
            elif st == "caindo":
                # Gota caindo com forma realista de gota d'água (Glow + teardrop shape)
                yg = int(g["y_gota"])
                # Linha de rastro/velocidade
                pygame.draw.line(tela, (0, 200, 255, 80), (tx, yg - 40), (tx, yg), 2)
                # Corpo da gota
                pygame.draw.circle(tela, (255, 255, 255), (tx, yg), 8)
                pygame.draw.polygon(tela, (0, 180, 255), [(tx - 8, yg), (tx, yg - 18), (tx + 8, yg)])
                # Núcleo brilhante
                pygame.draw.circle(tela, (255, 255, 255), (tx, yg - 2), 3)

        # 3. Desenhar notificações de dano / efeitos flutuantes personalizados
        fonte_notif = pygame.font.Font(None, 24)
        novas_notif = []
        for n in self.notificacoes:
            decorrido = tempo_atual - n["tempo_inicio"]
            if decorrido < n["duracao"]:
                y_offset = (decorrido / n["duracao"]) * 35.0
                alpha = int(255 * (1.0 - (decorrido / n["duracao"])))
                
                text_surf = fonte_notif.render(n["texto"], True, n["cor"])
                surf_temp = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
                surf_temp.fill((255, 255, 255, alpha))
                surf_temp.blit(text_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                
                tela.blit(surf_temp, (int(n["x"] - text_surf.get_width() // 2), int(n["y"] - y_offset)))
                novas_notif.append(n)
        self.notificacoes = novas_notif

    def verificar_colisao(self, pos_jogador, largura_j, altura_j, vida, vida_maxima, escudo_ativo, dano_adicional):
        tempo_atual = pygame.time.get_ticks()
        player_rect = pygame.Rect(pos_jogador[0], pos_jogador[1], largura_j, altura_j)
        slow_multiplier = 1.0

        for g in self.gotas:
            tx, ty = g["target_pos"][0], g["target_pos"][1]
            st = g["estado_gota"]

            if st == "impacto" and not g["danificou"]:
                # Colisão direta no impacto
                px = max(player_rect.left, min(tx, player_rect.right))
                py = max(player_rect.top, min(ty, player_rect.bottom))
                dist = math.sqrt((px - tx)**2 + (py - ty)**2)
                if dist <= 35:
                    g["danificou"] = True
                    if escudo_ativo:
                        escudo_ativo = False
                        self.notificacoes.append({
                            "texto": "ESCUDO BLOQUEOU GOTA!",
                            "x": pos_jogador[0] + largura_j // 2,
                            "y": pos_jogador[1] - 30,
                            "cor": (0, 255, 200),
                            "tempo_inicio": tempo_atual,
                            "duracao": 1200
                        })
                    else:
                        dano = (vida_maxima * 0.10 + dano_adicional)
                        vida = max(0.0, vida - dano)
                        self.notificacoes.append({
                            "texto": f"-{int(dano)} (IMPACTO GOTA!)",
                            "x": pos_jogador[0] + largura_j // 2,
                            "y": pos_jogador[1] - 30,
                            "cor": (255, 50, 50),
                            "tempo_inicio": tempo_atual,
                            "duracao": 1500
                        })

            elif st == "poca":
                # Lentidão e dano leve na poça
                px = max(player_rect.left, min(tx, player_rect.right))
                py = max(player_rect.top, min(ty, player_rect.bottom))
                dist = math.sqrt((px - tx)**2 + (py - ty)**2)
                if dist <= 35:
                    # Aplica lentidão (50% de velocidade)
                    slow_multiplier = 0.5
                    # Dano contínuo na poça (a cada 300ms)
                    if tempo_atual >= g["dano_poca_cooldown"]:
                        g["dano_poca_cooldown"] = tempo_atual + 300
                        if not escudo_ativo:
                            dano_p = (vida_maxima * 0.01 + dano_adicional * 0.1)
                            vida = max(0.0, vida - dano_p)
                            self.notificacoes.append({
                                "texto": "Poça Ácida!",
                                "x": pos_jogador[0] + largura_j // 2,
                                "y": pos_jogador[1] - 10,
                                "cor": (0, 150, 255),
                                "tempo_inicio": tempo_atual,
                                "duracao": 600
                            })

        # Modifica temporariamente a velocidade se necessário (retornado ao GAME.py)
        return pos_jogador[0], pos_jogador[1], vida, escudo_ativo, slow_multiplier


# --- 3. MARÉ FRATURADA ---
class MareFraturada(AtaqueBoss1):
    def __init__(self, boss_pos, jogador_pos, largura_mapa, altura_mapa):
        super().__init__("Mare Fraturada", 3600, boss_pos, jogador_pos, largura_mapa, altura_mapa)
        # Escolher a borda da qual a onda nascerá
        self.direcao = random.choice(["esquerda", "direita", "cima", "baixo"])
        self.aviso_duracao = 1500
        self.espessura_onda = 90
        
        # Posição da onda ao longo do eixo de viagem
        self.pos_travel = 0.0
        
        # Espaço seguro (Safe zone)
        if self.direcao in ["cima", "baixo"]:
            self.safe_span = 170
            self.safe_pos = random.randint(100, largura_mapa - 100 - self.safe_span)
        else:
            self.safe_span = 170
            self.safe_pos = random.randint(100, altura_mapa - 100 - self.safe_span)

    def update(self, dt, pos_jogador, boss_pos, tempo_atual):
        super().update(dt, pos_jogador, boss_pos, tempo_atual)
        if self.estado == "terminado":
            return

        if self.tempo_decorrido < self.aviso_duracao:
            self.estado = "telegraph"
        else:
            self.estado = "impacto"
            # Mover a onda
            progresso_viagem = (self.tempo_decorrido - self.aviso_duracao) / (self.duracao - self.aviso_duracao)
            
            if self.direcao == "esquerda":
                self.pos_travel = progresso_viagem * (self.largura_mapa + self.espessura_onda)
            elif self.direcao == "direita":
                self.pos_travel = self.largura_mapa - progresso_viagem * (self.largura_mapa + self.espessura_onda)
            elif self.direcao == "cima":
                self.pos_travel = progresso_viagem * (self.altura_mapa + self.espessura_onda)
            elif self.direcao == "baixo":
                self.pos_travel = self.altura_mapa - progresso_viagem * (self.altura_mapa + self.espessura_onda)

            # Criar espuma / partículas na frente da onda
            if random.random() < 0.6:
                for _ in range(3):
                    px, py = 0, 0
                    if self.direcao == "esquerda":
                        px = self.pos_travel
                        py = random.uniform(0, self.altura_mapa)
                    elif self.direcao == "direita":
                        px = self.pos_travel
                        py = random.uniform(0, self.altura_mapa)
                    elif self.direcao == "cima":
                        px = random.uniform(0, self.largura_mapa)
                        py = self.pos_travel
                    elif self.direcao == "baixo":
                        px = random.uniform(0, self.largura_mapa)
                        py = self.pos_travel

                    # Não gera na safe zone
                    if self.direcao in ["esquerda", "direita"]:
                        if self.safe_pos <= py <= self.safe_pos + self.safe_span:
                            continue
                    else:
                        if self.safe_pos <= px <= self.safe_pos + self.safe_span:
                            continue

                    self.particulas.append({
                        "x": px,
                        "y": py,
                        "vx": random.uniform(-1, 1),
                        "vy": random.uniform(-1, 1),
                        "alpha": 200,
                        "cor": random.choice([(0, 180, 255), (200, 220, 255), (0, 240, 200)])
                    })

        # Atualizar partículas
        for p in self.particulas[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["alpha"] -= 10
            if p["alpha"] <= 0:
                self.particulas.remove(p)

    def draw(self, tela):
        # Partículas de espuma
        for p in self.particulas:
            surf_p = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(surf_p, p["cor"] + (p["alpha"],), (3, 3), 3)
            tela.blit(surf_p, (int(p["x"] - 3), int(p["y"] - 3)))

        tempo_atual = pygame.time.get_ticks()

        # 1. Desenhar Telegraph (Aviso piscando)
        if self.estado == "telegraph":
            alpha = 140 if (tempo_atual // 80) % 2 == 0 else 60
            surf_w = pygame.Surface((self.largura_mapa, self.altura_mapa), pygame.SRCALPHA)
            
            cor_telegraph = (255, 120, 0, alpha)
            
            if self.direcao == "esquerda":
                # Desenha aviso na esquerda
                pygame.draw.rect(surf_w, cor_telegraph, (0, 0, 50, self.altura_mapa))
                # Desenhar guias da safe zone
                pygame.draw.line(surf_w, (0, 255, 200, 200), (0, self.safe_pos), (80, self.safe_pos), 3)
                pygame.draw.line(surf_w, (0, 255, 200, 200), (0, self.safe_pos + self.safe_span), (80, self.safe_pos + self.safe_span), 3)
            elif self.direcao == "direita":
                pygame.draw.rect(surf_w, cor_telegraph, (self.largura_mapa - 50, 0, 50, self.altura_mapa))
                pygame.draw.line(surf_w, (0, 255, 200, 200), (self.largura_mapa - 80, self.safe_pos), (self.largura_mapa, self.safe_pos), 3)
                pygame.draw.line(surf_w, (0, 255, 200, 200), (self.largura_mapa - 80, self.safe_pos + self.safe_span), (self.largura_mapa, self.safe_pos + self.safe_span), 3)
            elif self.direcao == "cima":
                pygame.draw.rect(surf_w, cor_telegraph, (0, 0, self.largura_mapa, 50))
                pygame.draw.line(surf_w, (0, 255, 200, 200), (self.safe_pos, 0), (self.safe_pos, 80), 3)
                pygame.draw.line(surf_w, (0, 255, 200, 200), (self.safe_pos + self.safe_span, 0), (self.safe_pos + self.safe_span, 80), 3)
            elif self.direcao == "baixo":
                pygame.draw.rect(surf_w, cor_telegraph, (0, self.altura_mapa - 50, self.largura_mapa, 50))
                pygame.draw.line(surf_w, (0, 255, 200, 200), (self.safe_pos, self.altura_mapa - 80), (self.safe_pos, self.altura_mapa), 3)
                pygame.draw.line(surf_w, (0, 255, 200, 200), (self.safe_pos + self.safe_span, self.altura_mapa - 80), (self.safe_pos + self.safe_span, self.altura_mapa), 3)
            
            tela.blit(surf_w, (0, 0))

        # 2. Desenhar a onda (Duas partes separadas pela Safe Zone)
        elif self.estado == "impacto":
            surf_wave = pygame.Surface((self.largura_mapa, self.altura_mapa), pygame.SRCALPHA)
            cor_onda = (0, 160, 255, 110)
            cor_crista = (0, 240, 255, 200)

            pt = self.pos_travel
            esp = self.espessura_onda

            if self.direcao in ["esquerda", "direita"]:
                # Desenhar dois blocos: topo -> safe_pos, e safe_pos+safe_span -> final
                r1 = pygame.Rect(pt - esp//2, 0, esp, self.safe_pos)
                r2 = pygame.Rect(pt - esp//2, self.safe_pos + self.safe_span, esp, self.altura_mapa - (self.safe_pos + self.safe_span))
                
                pygame.draw.rect(surf_wave, cor_onda, r1)
                pygame.draw.rect(surf_wave, cor_onda, r2)
                
                # Cristas da onda
                pygame.draw.rect(surf_wave, cor_crista, (pt + (esp//2 if self.direcao=="esquerda" else -esp//2) - 3, 0, 6, self.safe_pos))
                pygame.draw.rect(surf_wave, cor_crista, (pt + (esp//2 if self.direcao=="esquerda" else -esp//2) - 3, self.safe_pos + self.safe_span, 6, self.altura_mapa - (self.safe_pos + self.safe_span)))
            else:
                # Desenhar dois blocos: esquerda -> safe_pos, e safe_pos+safe_span -> final
                r1 = pygame.Rect(0, pt - esp//2, self.safe_pos, esp)
                r2 = pygame.Rect(self.safe_pos + self.safe_span, pt - esp//2, self.largura_mapa - (self.safe_pos + self.safe_span), esp)
                
                pygame.draw.rect(surf_wave, cor_onda, r1)
                pygame.draw.rect(surf_wave, cor_onda, r2)
                
                # Cristas da onda
                pygame.draw.rect(surf_wave, cor_crista, (0, pt + (esp//2 if self.direcao=="cima" else -esp//2) - 3, self.safe_pos, 6))
                pygame.draw.rect(surf_wave, cor_crista, (self.safe_pos + self.safe_span, pt + (esp//2 if self.direcao=="cima" else -esp//2) - 3, self.largura_mapa - (self.safe_pos + self.safe_span), 6))

            tela.blit(surf_wave, (0, 0))

    def verificar_colisao(self, pos_jogador, largura_j, altura_j, vida, vida_maxima, escudo_ativo, dano_adicional):
        if self.estado != "impacto" or self.danificou:
            return pos_jogador[0], pos_jogador[1], vida, escudo_ativo

        player_rect = pygame.Rect(pos_jogador[0], pos_jogador[1], largura_j, altura_j)
        pt = self.pos_travel
        esp = self.espessura_onda

        atingiu = False
        push_x, push_y = 0.0, 0.0

        if self.direcao in ["esquerda", "direita"]:
            # Verifica se o jogador está na faixa X da onda
            if pt - esp//2 <= player_rect.centerx <= pt + esp//2:
                # Verifica se NÃO está na safe zone
                if not (self.safe_pos <= player_rect.centery <= self.safe_pos + self.safe_span):
                    atingiu = True
                    push_x = 350.0 if self.direcao == "esquerda" else -350.0
        else:
            # Verifica se o jogador está na faixa Y da onda
            if pt - esp//2 <= player_rect.centery <= pt + esp//2:
                # Verifica se NÃO está na safe zone
                if not (self.safe_pos <= player_rect.centerx <= self.safe_pos + self.safe_span):
                    atingiu = True
                    push_y = 350.0 if self.direcao == "cima" else -350.0

        if atingiu:
            self.danificou = True
            # Aplicar empurrão (knockback) à posição do jogador
            new_x = max(0, min(self.largura_mapa - largura_j, pos_jogador[0] + push_x * 0.016))
            new_y = max(0, min(self.altura_mapa - altura_j, pos_jogador[1] + push_y * 0.016))
            
            if escudo_ativo:
                return new_x, new_y, vida, False
            else:
                dano = (vida_maxima * 0.12) + dano_adicional
                return new_x, new_y, max(0.0, vida - dano), escudo_ativo

        return pos_jogador[0], pos_jogador[1], vida, escudo_ativo


# --- 4. AREIA VIVA ---
class AreiaViva(AtaqueBoss1):
    def __init__(self, boss_pos, jogador_pos, largura_mapa, altura_mapa, num_redemoinhos=3):
        super().__init__("Areia Viva", 5000, boss_pos, jogador_pos, largura_mapa, altura_mapa)
        self.redemoinhos = []
        self.raio = 120
        # Criar redemoinhos em posições dispersas perto do jogador
        for _ in range(num_redemoinhos):
            ang = random.uniform(0, math.pi * 2)
            dist = random.uniform(50, 220)
            rx = max(self.raio, min(largura_mapa - self.raio, jogador_pos[0] + math.cos(ang) * dist))
            ry = max(self.raio, min(altura_mapa - self.raio, jogador_pos[1] + math.sin(ang) * dist))
            self.redemoinhos.append({
                "center": [rx, ry],
                "dano_cooldown": 0,
                "angulo_rotacao": 0.0
            })
            
        # Partículas da areia
        for _ in range(60):
            r = random.uniform(10, self.raio)
            ang = random.uniform(0, math.pi*2)
            self.particulas.append({
                "r": r,
                "ang": ang,
                "speed": random.uniform(0.04, 0.08)
            })

    def update(self, dt, pos_jogador, boss_pos, tempo_atual):
        super().update(dt, pos_jogador, boss_pos, tempo_atual)
        if self.estado == "terminado":
            return

        if self.tempo_decorrido < 1200:
            self.estado = "telegraph"
        else:
            self.estado = "impacto"
        
        # Atualizar rotação interna
        for rdm in self.redemoinhos:
            rdm["angulo_rotacao"] += 0.05 * dt

        # Espiralizar partículas de areia para dentro
        for p in self.particulas:
            p["ang"] += p["speed"] * dt
            p["r"] -= 0.4 * dt
            if p["r"] < 5:
                p["r"] = random.uniform(60, self.raio)
                p["ang"] = random.uniform(0, math.pi * 2)

    def draw(self, tela):
        tempo_atual = pygame.time.get_ticks()
        
        for rdm in self.redemoinhos:
            cx, cy = int(rdm["center"][0]), int(rdm["center"][1])
            
            if self.estado == "telegraph":
                # Desenhar um anel de aviso pulsante cor de areia/laranja
                progresso = self.tempo_decorrido / 1200.0
                alpha = int(80 + math.sin(tempo_atual * 0.015) * 40)
                
                surf_aviso = pygame.Surface((self.raio * 2, self.raio * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf_aviso, (230, 150, 20, alpha), (self.raio, self.raio), self.raio, 3)
                pygame.draw.circle(surf_aviso, (230, 180, 50, alpha // 2), (self.raio, self.raio), self.raio)
                
                # Anel que contrai indicando a ativação
                raio_contraido = int(self.raio * (1.0 - progresso))
                if raio_contraido > 0:
                    pygame.draw.circle(surf_aviso, (255, 255, 255, 200), (self.raio, self.raio), raio_contraido, 2)
                
                tela.blit(surf_aviso, (cx - self.raio, cy - self.raio))
            else:
                # Centro escuro
                surf_c = pygame.Surface((self.raio * 2, self.raio * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf_c, (12, 10, 8, 140), (self.raio, self.raio), self.raio)
                pygame.draw.circle(surf_c, (230, 180, 80, 50), (self.raio, self.raio), self.raio, 4)
                pygame.draw.circle(surf_c, (240, 190, 90, 80), (self.raio, self.raio), self.raio - 20, 2)
                
                # Centro crítico
                pygame.draw.circle(surf_c, (10, 5, 0, 220), (self.raio, self.raio), 25)
                pygame.draw.circle(surf_c, (255, 100, 0, 180), (self.raio, self.raio), 25, 2)
                
                tela.blit(surf_c, (cx - self.raio, cy - self.raio))

                # Desenhar partículas girando em espiral ao redor desse redemoinho
                for p in self.particulas:
                    px = cx + math.cos(p["ang"] + rdm["angulo_rotacao"]) * p["r"]
                    py = cy + math.sin(p["ang"] + rdm["angulo_rotacao"]) * p["r"]
                    
                    # Densidade alfa baseada na proximidade ao centro
                    alpha = int(255 * (p["r"] / self.raio))
                    surf_p = pygame.Surface((4, 4), pygame.SRCALPHA)
                    pygame.draw.circle(surf_p, (230, 190, 110, alpha), (2, 2), 2)
                    tela.blit(surf_p, (int(px - 2), int(py - 2)))

    def verificar_colisao(self, pos_jogador, largura_j, altura_j, vida, vida_maxima, escudo_ativo, dano_adicional):
        if self.estado == "telegraph":
            return pos_jogador[0], pos_jogador[1], vida, escudo_ativo, 1.0
            
        tempo_atual = pygame.time.get_ticks()
        player_rect = pygame.Rect(pos_jogador[0], pos_jogador[1], largura_j, altura_j)
        px_c, py_c = player_rect.centerx, player_rect.centery
        
        slow_multiplier = 1.0
        final_x, final_y = pos_jogador[0], pos_jogador[1]

        for rdm in self.redemoinhos:
            rx, ry = rdm["center"][0], rdm["center"][1]
            dist = math.sqrt((px_c - rx)**2 + (py_c - ry)**2)

            if dist <= self.raio:
                # 1. Puxar o jogador lentamente para o centro
                vec_x = rx - px_c
                vec_y = ry - py_c
                if dist > 0:
                    vec_x /= dist
                    vec_y /= dist
                
                # Força de puxar (escalando: quanto mais perto do centro, mais forte)
                pull_force = 1.6 + (1.0 - (dist / self.raio)) * 2.5
                final_x += vec_x * pull_force
                final_y += vec_y * pull_force
                
                # 2. Aplicar lentidão
                slow_multiplier = min(slow_multiplier, 0.45)

                # 3. Dano contínuo se estiver muito perto do centro (dist <= 30)
                if dist <= 30 and tempo_atual >= rdm["dano_cooldown"]:
                    rdm["dano_cooldown"] = tempo_atual + 200
                    if not escudo_ativo:
                        dano = (vida_maxima * 0.02) + dano_adicional * 0.1
                        vida = max(0.0, vida - dano)

        return final_x, final_y, vida, escudo_ativo, slow_multiplier


# --- 5. PINÇA DE RUPTURA ---
class PincaRuptura(AtaqueBoss1):
    def __init__(self, boss_pos, jogador_pos, largura_mapa, altura_mapa):
        super().__init__("Pinca de Ruptura", 1800, boss_pos, jogador_pos, largura_mapa, altura_mapa)
        self.target_pos = list(jogador_pos)  # Posição focada do jogador
        self.clamp_dist = 90.0  # Distância inicial das pinças

    def update(self, dt, pos_jogador, boss_pos, tempo_atual):
        super().update(dt, pos_jogador, boss_pos, tempo_atual)
        if self.estado == "terminado":
            return

        prog = self.tempo_decorrido / self.duracao
        if prog < 0.65:
            # Telegraph: Pinças se posicionam ao redor e retícula foca
            self.estado = "telegraph"
            self.clamp_dist = 90.0 - prog * 20.0
        elif prog < 0.82:
            # Impacto: Pinças fecham abruptamente
            self.estado = "impacto"
            prog_impacto = (prog - 0.65) / 0.17
            self.clamp_dist = 70.0 - prog_impacto * 70.0
            if self.clamp_dist < 0:
                self.clamp_dist = 0
            
            # Centelhas e partículas de impacto roxas
            if random.random() < 0.8:
                for _ in range(5):
                    ang = random.uniform(0, math.pi*2)
                    spd = random.uniform(4, 9)
                    self.particulas.append({
                        "x": self.target_pos[0],
                        "y": self.target_pos[1],
                        "vx": math.cos(ang) * spd,
                        "vy": math.sin(ang) * spd,
                        "alpha": 255,
                        "cor": (180, 0, 255)
                    })
        else:
            # Finalização
            self.estado = "finalizacao"
            
        # Atualizar partículas
        for p in self.particulas[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["alpha"] -= 12
            if p["alpha"] <= 0:
                self.particulas.remove(p)

    def draw(self, tela):
        # Partículas
        for p in self.particulas:
            surf_p = pygame.Surface((5, 5), pygame.SRCALPHA)
            pygame.draw.circle(surf_p, p["cor"] + (p["alpha"],), (2, 2), 2)
            tela.blit(surf_p, (int(p["x"] - 2), int(p["y"] - 2)))

        tx, ty = int(self.target_pos[0]), int(self.target_pos[1])

        if self.estado == "telegraph":
            # Desenhar retícula (cruz) translúcida roxa no chão
            pygame.draw.line(tela, (180, 0, 255, 120), (tx - 40, ty), (tx + 40, ty), 2)
            pygame.draw.line(tela, (180, 0, 255, 120), (tx, ty - 40), (tx, ty + 40), 2)
            pygame.draw.circle(tela, (0, 255, 230, 80), (tx, ty), int(self.clamp_dist), 1)

            # Arcos laterais
            cd = int(self.clamp_dist)
            # Arco Esquerdo
            surf_l = pygame.Surface((60, 120), pygame.SRCALPHA)
            pygame.draw.arc(surf_l, (180, 0, 255, 200), (0, 0, 100, 120), math.pi/2, 3*math.pi/2, 4)
            tela.blit(surf_l, (tx - cd - 50, ty - 60))
            
            # Arco Direito
            surf_r = pygame.Surface((60, 120), pygame.SRCALPHA)
            pygame.draw.arc(surf_r, (180, 0, 255, 200), (-40, 0, 100, 120), -math.pi/2, math.pi/2, 4)
            tela.blit(surf_r, (tx + cd - 10, ty - 60))

        elif self.estado == "impacto":
            # Esmagamento visível roxo neon/branco
            cd = int(self.clamp_dist)
            pygame.draw.circle(tela, (255, 255, 255, 240), (tx, ty), max(5, cd), 3)
            
            # Arcos se fechando no centro
            surf_l = pygame.Surface((60, 120), pygame.SRCALPHA)
            pygame.draw.arc(surf_l, (255, 255, 255, 240), (0, 0, 100, 120), math.pi/2, 3*math.pi/2, 6)
            tela.blit(surf_l, (tx - cd - 50, ty - 60))
            
            surf_r = pygame.Surface((60, 120), pygame.SRCALPHA)
            pygame.draw.arc(surf_r, (255, 255, 255, 240), (-40, 0, 100, 120), -math.pi/2, math.pi/2, 6)
            tela.blit(surf_r, (tx + cd - 10, ty - 60))

    def verificar_colisao(self, pos_jogador, largura_j, altura_j, vida, vida_maxima, escudo_ativo, dano_adicional):
        if self.estado == "impacto" and not self.danificou:
            player_rect = pygame.Rect(pos_jogador[0], pos_jogador[1], largura_j, altura_j)
            tx, ty = self.target_pos[0], self.target_pos[1]
            
            px = max(player_rect.left, min(tx, player_rect.right))
            py = max(player_rect.top, min(ty, player_rect.bottom))
            dist = math.sqrt((px - tx)**2 + (py - ty)**2)
            
            if dist <= 55:
                self.danificou = True
                if escudo_ativo:
                    return pos_jogador[0], pos_jogador[1], vida, False
                else:
                    dano = (vida_maxima * 0.18) + dano_adicional
                    # Atordoa/empurra ligeiramente (retorna deslocamento pequeno)
                    return pos_jogador[0], pos_jogador[1], max(0.0, vida - dano), escudo_ativo

        return pos_jogador[0], pos_jogador[1], vida, escudo_ativo


# --- 6. INVESTIDA TEMPORAL ---
class InvestidaTemporal(AtaqueBoss1):
    def __init__(self, boss_pos, jogador_pos, largura_mapa, altura_mapa):
        # 2000ms telegraphing + 1500ms charge = 3500ms total
        super().__init__("Investida Temporal", 3500, boss_pos, jogador_pos, largura_mapa, altura_mapa)
        self.target_locked = False
        self.target_pos = list(jogador_pos)
        self.charge_dir = [0.0, 0.0]
        self.boss_move = True # Indica que move o boss
        self.velocidade_investida = 8.0 # Velocidade moderada
        self.hit_player = False

    def update(self, dt, pos_jogador, boss_pos, tempo_atual):
        self.tempo_decorrido = tempo_atual - self.tempo_inicio
        if self.tempo_decorrido >= self.duracao:
            self.estado = "terminado"
            return
        pos_alvo = self.alvo_fixo or pos_jogador
        
        if self.tempo_decorrido < 2000:
            # Fase 1: MIRA
            self.estado = "telegraph"
            self.target_pos = list(pos_alvo)
            self.boss_pos = list(boss_pos)
        else:
            # Fase 2: CORRIDA
            self.estado = "impacto"
            if not self.target_locked:
                self.target_locked = True
                # Travar a direção da investida a partir do centro do boss (boss_pos) até o jogador
                dx = self.target_pos[0] - boss_pos[0]
                dy = self.target_pos[1] - boss_pos[1]
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > 0:
                    self.charge_dir = [dx / dist, dy / dist]
                else:
                    self.charge_dir = [0.0, 0.0]
            
            # Atualiza self.boss_pos (que representa o centro do boss para colisão/desenho)
            self.boss_pos[0] += self.charge_dir[0] * self.velocidade_investida * dt
            self.boss_pos[1] += self.charge_dir[1] * self.velocidade_investida * dt

        # Atualizar partículas
        for p in self.particulas[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["alpha"] -= 8
            if p["alpha"] <= 0:
                self.particulas.remove(p)

    def update_boss_pos(self, dt, pos_chefe, boss_w, boss_h, largura_mapa, altura_mapa):
        if self.estado == "impacto" and self.charge_dir:
            # Move o boss (top-left) no mapa
            pos_chefe[0] += self.charge_dir[0] * self.velocidade_investida * dt
            pos_chefe[1] += self.charge_dir[1] * self.velocidade_investida * dt
            pos_chefe[0] = max(0, min(largura_mapa - boss_w, pos_chefe[0]))
            pos_chefe[1] = max(0, min(altura_mapa - boss_h, pos_chefe[1]))
        return pos_chefe

    def draw(self, tela):
        # Partículas
        for p in self.particulas:
            surf_p = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(surf_p, p["cor"] + (p["alpha"],), (3, 3), 3)
            tela.blit(surf_p, (int(p["x"] - 3), int(p["y"] - 3)))

        tempo_atual = pygame.time.get_ticks()
        bc = self.boss_pos

        if self.estado == "telegraph":
            # Linha de mira laser vermelha piscando
            alpha = int(120 + 80 * math.sin(tempo_atual * 0.02))
            
            # Desenha linha laser e brilho
            pygame.draw.line(tela, (255, 50, 50, alpha // 2), bc, self.target_pos, 4)
            pygame.draw.line(tela, (255, 255, 255, alpha), bc, self.target_pos, 1)
            
            pygame.draw.circle(tela, (255, 0, 0, alpha // 2), (int(self.target_pos[0]), int(self.target_pos[1])), 15, 2)
            pygame.draw.circle(tela, (255, 0, 0, alpha // 3), (int(self.target_pos[0]), int(self.target_pos[1])), 5)

        elif self.estado == "impacto":
            # Partículas de poeira e vento atrás do boss
            if random.random() < 0.4:
                opp_x = -self.charge_dir[0]
                opp_y = -self.charge_dir[1]
                self.particulas.append({
                    "x": bc[0] + random.uniform(-20, 20),
                    "y": bc[1] + random.uniform(-20, 20),
                    "vx": opp_x * random.uniform(2, 5) + random.uniform(-1, 1),
                    "vy": opp_y * random.uniform(2, 5) + random.uniform(-1, 1),
                    "alpha": 180,
                    "cor": random.choice([(240, 220, 180), (200, 200, 200), (0, 191, 255)])
                })

    def verificar_colisao(self, pos_jogador, largura_j, altura_j, vida, vida_maxima, escudo_ativo, dano_adicional):
        if self.estado == "impacto" and not self.hit_player:
            player_rect = pygame.Rect(pos_jogador[0], pos_jogador[1], largura_j, altura_j)
            p_center = player_rect.center
            # Colisão circular
            dist = math.hypot(p_center[0] - self.boss_pos[0], p_center[1] - self.boss_pos[1])
            if dist <= 90:
                self.hit_player = True
                if escudo_ativo:
                    return pos_jogador[0], pos_jogador[1], vida, False, 1.0, 0, 0.0, 0.0
                else:
                    dano = (vida_maxima * 0.20) + dano_adicional
                    # Knockback de 35.0 pixels na direção da investida
                    kb_x = self.charge_dir[0] * 35.0
                    kb_y = self.charge_dir[1] * 35.0
                    return pos_jogador[0], pos_jogador[1], max(0.0, vida - dano), escudo_ativo, 1.0, 1500, kb_x, kb_y
        
        return pos_jogador[0], pos_jogador[1], vida, escudo_ativo, 1.0, 0, 0.0, 0.0


# --- GERENCIADOR DE ATAQUES ---
class GerenciadorAtaquesBoss1:
    def __init__(self):
        self.ataques_ativos = []
        self.tempo_ultimo_ataque = pygame.time.get_ticks()
        self.cooldown_base = 3800  # Intervalo padrão entre os ataques

    def _fixar_alvo(self, ataque, alvo):
        ataque.alvo_fixo = list(alvo)
        return ataque

    def _alvos_validos(self, pos_jogador, alvos_jogadores=None):
        alvos = []
        for alvo in alvos_jogadores or []:
            if alvo is None:
                continue
            try:
                alvos.append((float(alvo[0]), float(alvo[1])))
            except Exception:
                continue
        if not alvos:
            alvos.append((float(pos_jogador[0]), float(pos_jogador[1])))
        return alvos[:2]

    def _adicionar_diluvio_por_alvo(self, pos_chefe, alvos, largura_mapa, altura_mapa, num_gotas):
        gotas_por_alvo = max(4, int(num_gotas / max(1, len(alvos))))
        for alvo in alvos:
            self.ataques_ativos.append(self._fixar_alvo(
                DiluvioSuspenso(pos_chefe, alvo, largura_mapa, altura_mapa, num_gotas=gotas_por_alvo),
                alvo,
            ))

    def escolher_e_lancar_ataque(self, pos_chefe, pos_jogador, vida_boss, vida_maxima_boss, largura_mapa, altura_mapa, tempo_atual, alvos_jogadores=None):
        # Determinar a porcentagem de vida
        porcentagem_vida = vida_boss / vida_maxima_boss if vida_maxima_boss > 0 else 0.0
        alvos = self._alvos_validos(pos_jogador, alvos_jogadores)
        alvo_principal = random.choice(alvos)
        
        # Escolher a pool de ataques disponíveis baseado no estágio da luta
        if porcentagem_vida > 0.70:
            pool = ["bolha", "diluvio_simples", "investida"]
        elif porcentagem_vida > 0.35:
            pool = ["bolha", "diluvio", "mare", "areia", "investida"]
        else:
            pool = ["bolha_combo", "mare_combo", "pinca_gotas", "investida_combo"]

        escolha = random.choice(pool)
        
        # Instanciar e lançar ataques
        if escolha == "bolha":
            for alvo in alvos:
                self.ataques_ativos.append(BolhaPressaoTemporal(pos_chefe, alvo, largura_mapa, altura_mapa))
        elif escolha == "diluvio_simples":
            self._adicionar_diluvio_por_alvo(pos_chefe, alvos, largura_mapa, altura_mapa, num_gotas=6)
        elif escolha == "diluvio":
            self._adicionar_diluvio_por_alvo(pos_chefe, alvos, largura_mapa, altura_mapa, num_gotas=8)
        elif escolha == "mare":
            self.ataques_ativos.append(MareFraturada(pos_chefe, alvo_principal, largura_mapa, altura_mapa))
        elif escolha == "areia":
            self.ataques_ativos.append(AreiaViva(pos_chefe, alvo_principal, largura_mapa, altura_mapa, num_redemoinhos=3))
        elif escolha == "investida":
            self.ataques_ativos.append(self._fixar_alvo(InvestidaTemporal(pos_chefe, alvo_principal, largura_mapa, altura_mapa), alvo_principal))
        
        # Combinações do Estágio Crítico (vida < 35%)
        elif escolha == "bolha_combo":
            for alvo in alvos:
                self.ataques_ativos.append(BolhaPressaoTemporal(pos_chefe, alvo, largura_mapa, altura_mapa))
            self.ataques_ativos.append(AreiaViva(pos_chefe, alvo_principal, largura_mapa, altura_mapa, num_redemoinhos=2))
        elif escolha == "mare_combo":
            self.ataques_ativos.append(MareFraturada(pos_chefe, alvo_principal, largura_mapa, altura_mapa))
            self.ataques_ativos.append(AreiaViva(pos_chefe, alvo_principal, largura_mapa, altura_mapa, num_redemoinhos=3))
        elif escolha == "pinca_gotas":
            for alvo in alvos:
                self.ataques_ativos.append(PincaRuptura(pos_chefe, alvo, largura_mapa, altura_mapa))
            self._adicionar_diluvio_por_alvo(pos_chefe, alvos, largura_mapa, altura_mapa, num_gotas=6)
        elif escolha == "investida_combo":
            self.ataques_ativos.append(self._fixar_alvo(InvestidaTemporal(pos_chefe, alvo_principal, largura_mapa, altura_mapa), alvo_principal))
            self._adicionar_diluvio_por_alvo(pos_chefe, alvos, largura_mapa, altura_mapa, num_gotas=10)

        self.tempo_ultimo_ataque = tempo_atual

    def boss_movendo_por_ataque(self):
        for atk in self.ataques_ativos:
            if getattr(atk, "boss_move", False):
                return True
        return False

    def update(self, dt, pos_jogador, largura_j, altura_j, vida, vida_maxima, escudo_ativo, dano_adicional,
               pos_chefe, pos_chefe_larg, pos_chefe_alt, vida_boss, vida_maxima_boss, largura_mapa, altura_mapa, tempo_atual, alvos_jogadores=None):
        
        # 1. Verificar se precisa e pode lançar um novo ataque
        if vida_boss > 0:
            porcentagem_vida = vida_boss / vida_maxima_boss if vida_maxima_boss > 0 else 1.0
            cooldown_atual = self.cooldown_base
            if porcentagem_vida <= 0.35:
                cooldown_atual = 2500
            elif porcentagem_vida <= 0.70:
                cooldown_atual = 3200
                
            if len(self.ataques_ativos) == 0 and (tempo_atual - self.tempo_ultimo_ataque >= cooldown_atual):
                centro_chefe = (pos_chefe[0] + pos_chefe_larg // 2, pos_chefe[1] + pos_chefe_alt // 2)
                centro_jogador = (pos_jogador[0] + largura_j // 2, pos_jogador[1] + altura_j // 2)
                self.escolher_e_lancar_ataque(centro_chefe, centro_jogador, vida_boss, vida_maxima_boss, largura_mapa, altura_mapa, tempo_atual, alvos_jogadores)

        # 2. Atualizar todos os ataques ativos e resolver colisões
        fator_slow_geral = 1.0
        stun_req_geral = 0
        kb_x_geral = 0.0
        kb_y_geral = 0.0
        
        for atk in self.ataques_ativos[:]:
            # Se for um ataque que move o chefe, deixa ele atualizar a posição do chefe
            if hasattr(atk, "update_boss_pos"):
                pos_chefe = atk.update_boss_pos(dt, pos_chefe, pos_chefe_larg, pos_chefe_alt, largura_mapa, altura_mapa)

            # Centro do chefe
            centro_chefe = (pos_chefe[0] + pos_chefe_larg // 2, pos_chefe[1] + pos_chefe_alt // 2)
            atk.update(dt, pos_jogador, centro_chefe, tempo_atual)
            
            # Verificar colisão/dano
            res_colisao = atk.verificar_colisao(pos_jogador, largura_j, altura_j, vida, vida_maxima, escudo_ativo, dano_adicional)
            
            if isinstance(atk, InvestidaTemporal):
                # InvestidaTemporal retorna (pos_x, pos_y, vida, escudo, slow, stun, kb_x, kb_y)
                pos_jogador = [res_colisao[0], res_colisao[1]]
                vida = res_colisao[2]
                escudo_ativo = res_colisao[3]
                fator_slow_geral = min(fator_slow_geral, res_colisao[4])
                stun_req = res_colisao[5]
                kb_x_atk = res_colisao[6]
                kb_y_atk = res_colisao[7]
                
                stun_req_geral = max(stun_req_geral, stun_req)
                if kb_x_atk != 0.0 or kb_y_atk != 0.0:
                    kb_x_geral = kb_x_atk
                    kb_y_geral = kb_y_atk
            elif isinstance(atk, (DiluvioSuspenso, AreiaViva)):
                pos_jogador = [res_colisao[0], res_colisao[1]]
                vida = res_colisao[2]
                escudo_ativo = res_colisao[3]
                fator_slow_geral = min(fator_slow_geral, res_colisao[4])
            else:
                pos_jogador = [res_colisao[0], res_colisao[1]]
                vida = res_colisao[2]
                escudo_ativo = res_colisao[3]

            if atk.estado == "terminado":
                self.ataques_ativos.remove(atk)

        return pos_jogador[0], pos_jogador[1], vida, escudo_ativo, fator_slow_geral, [pos_chefe[0], pos_chefe[1]], stun_req_geral, kb_x_geral, kb_y_geral

    def draw(self, tela):
        for atk in self.ataques_ativos:
            _desenhar_ataque_premium(atk, tela)


# Instância global para facilitar integração no loop de GAME.py
gerenciador_ataques_boss1 = GerenciadorAtaquesBoss1()
