import pygame
import Variaveis


def _texto_contornado(superficie, texto, fonte, cor, pos, contorno=(0, 0, 0)):
    x, y = pos
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        superficie.blit(fonte.render(texto, True, contorno), (x + dx, y + dy))
    superficie.blit(fonte.render(texto, True, cor), (x, y))


def registrar_dano_boss(efeitos_texto, dano, x, y, tempo_atual, cor=(255, 230, 120), critico=False):
    if efeitos_texto is None or dano is None:
        return
    valor = max(1, int(dano))
    Variaveis.registrar_efeito_texto(
        efeitos_texto,
        f"-{valor}",
        int(x),
        int(y),
        int(tempo_atual),
        (255, 248, 120) if critico else cor,
        chave=("boss-dano", int(x) // 12, int(y) // 12, valor),
    )


def desenhar_barra_vida_boss(
    tela,
    vida_atual,
    vida_maxima,
    nome,
    fase,
    cor_barra=(220, 70, 90),
    cor_fundo=(28, 12, 18),
):
    vida_maxima = max(1, float(vida_maxima or 1))
    vida_atual = max(0.0, min(float(vida_atual or 0), vida_maxima))
    pct = vida_atual / vida_maxima

    largura_tela = tela.get_width()
    largura = min(560, max(360, largura_tela - 420))
    altura = 48
    x = (largura_tela - largura) // 2
    y = 18

    painel = pygame.Surface((largura, altura), pygame.SRCALPHA)
    pygame.draw.rect(painel, (6, 6, 10, 190), (0, 0, largura, altura), border_radius=7)
    pygame.draw.rect(painel, (255, 255, 255, 38), (0, 0, largura, altura), 1, border_radius=7)

    fonte_nome = pygame.font.Font(None, 22)
    fonte_num = pygame.font.Font(None, 19)
    titulo = f"FASE {fase} - {nome}"
    vida_txt = f"{int(vida_atual):,} / {int(vida_maxima):,}".replace(",", ".")
    pct_txt = f"{int(pct * 100)}%"

    _texto_contornado(painel, titulo, fonte_nome, (255, 236, 194), (12, 6))
    vida_render = fonte_num.render(vida_txt, True, (245, 245, 250))
    _texto_contornado(painel, vida_txt, fonte_num, (245, 245, 250), (largura - vida_render.get_width() - 12, 8))

    barra_x = 12
    barra_y = 29
    barra_w = largura - 76
    barra_h = 11
    pygame.draw.rect(painel, cor_fundo, (barra_x, barra_y, barra_w, barra_h), border_radius=5)
    preenchido = int(barra_w * pct)
    if preenchido > 0:
        pygame.draw.rect(painel, cor_barra, (barra_x, barra_y, preenchido, barra_h), border_radius=5)
        brilho = (min(255, cor_barra[0] + 40), min(255, cor_barra[1] + 40), min(255, cor_barra[2] + 40))
        pygame.draw.rect(painel, brilho, (barra_x, barra_y, preenchido, 3), border_radius=3)
    pygame.draw.rect(painel, (255, 255, 255, 70), (barra_x, barra_y, barra_w, barra_h), 1, border_radius=5)

    pct_render = fonte_num.render(pct_txt, True, (255, 230, 170))
    _texto_contornado(painel, pct_txt, fonte_num, (255, 230, 170), (largura - pct_render.get_width() - 12, 27))

    tela.blit(painel, (x, y))
