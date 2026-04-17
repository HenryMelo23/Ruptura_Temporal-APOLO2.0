import pygame
import sys
import math
import random

pygame.init()

PRETO = (0, 0, 0)
VERDE_ESCURO = (0, 100, 0)
VERDE_CLARO = (50, 205, 50)
ROXO_ESCURO = (128, 0, 128)
ROXO_CLARO = (186, 85, 211)
ROSA = (255, 105, 180)

ENERGIA_NUCLEO = (255, 255, 0)
ENERGIA_COROA = (255, 140, 0)
RRASTRO_CINETICO = (0, 255, 255)

LARGURA_TELA = 1000
ALTURA_TELA = 600
TAMANHO_PIXEL = 6 

mec_predador = [
    [0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0],
    [0,0,0,1,2,2,2,2,2,2,1,0,0,0,0,0,0,0,0],
    [0,0,1,2,4,4,4,4,4,2,2,1,0,0,0,1,1,0,0],
    [0,1,2,4,5,5,5,5,4,4,2,1,1,1,1,6,1,0,0],
    [0,1,2,4,5,1,1,5,4,4,2,2,2,2,1,6,1,0,0],
    [1,2,4,4,5,1,6,5,4,4,4,4,4,2,1,6,1,0,0],
    [1,2,4,4,5,5,5,5,4,4,1,1,4,2,1,1,0,0,0],
    [1,2,4,4,4,4,4,4,4,1,6,6,1,4,2,1,0,0,0],
    [1,2,2,4,4,4,4,4,1,6,6,6,6,1,4,1,0,0,0],
    [0,1,2,2,2,2,2,1,6,6,1,1,6,6,1,0,0,0,0],
    [0,0,1,1,1,1,1,1,6,1,0,0,1,6,1,0,0,0,0],
    [0,0,0,0,0,1,2,2,1,0,0,0,0,1,1,0,0,0,0],
    [0,0,0,0,1,2,3,3,2,1,0,0,0,0,0,0,0,0,0],
    [0,0,0,1,2,3,4,4,3,2,1,0,0,0,0,0,0,0,0],
    [0,0,1,2,3,4,5,5,4,3,2,1,0,0,0,0,0,0,0],
    [0,1,2,3,4,5,5,5,5,4,3,2,1,0,0,0,0,0,0],
    [0,1,2,3,4,4,4,4,4,4,3,2,1,0,0,0,0,0,0],
    [0,1,2,2,3,3,3,3,3,3,2,2,1,0,0,0,0,0,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0],
    [0,0,1,4,4,1,0,0,1,4,4,1,0,0,0,0,0,0,0],
    [0,1,4,5,4,1,0,0,1,4,5,4,1,0,0,0,0,0,0],
    [1,4,5,5,1,0,0,0,0,1,5,5,4,1,0,0,0,0,0],
    [1,1,1,1,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0]
]

tela = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
pygame.display.set_caption("Ecossistema Artificial - Mec-Predador")
relogio = pygame.time.Clock()

def desenhar_planta(grid, offset_x, offset_y):
    for y, row in enumerate(grid):
        for x, pixel_type in enumerate(row):
            if pixel_type == 0: continue
            
            rect = pygame.Rect(int(offset_x) + x * TAMANHO_PIXEL, int(offset_y) + y * TAMANHO_PIXEL, TAMANHO_PIXEL, TAMANHO_PIXEL)
            
            if pixel_type == 1: pygame.draw.rect(tela, PRETO, rect)
            elif pixel_type == 2: pygame.draw.rect(tela, VERDE_ESCURO, rect)
            elif pixel_type == 3: pygame.draw.rect(tela, VERDE_CLARO, rect)
            elif pixel_type == 4: pygame.draw.rect(tela, ROXO_ESCURO, rect)
            elif pixel_type == 5: pygame.draw.rect(tela, ROXO_CLARO, rect)
            elif pixel_type == 6: pygame.draw.rect(tela, ROSA, rect)

class Particula:
    def __init__(self, x, y, dx, dy, cor, vida):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.cor = cor
        self.vida = vida
        self.vida_max = vida

    def atualizar(self):
        self.x += self.dx
        self.y += self.dy
        self.vida -= 1

    def desenhar(self, superficie):
        if self.vida > 0:
            escala = max(1, int(4 * (self.vida / self.vida_max)))
            pygame.draw.rect(superficie, self.cor, (int(self.x), int(self.y), escala, escala))

pos_base = pygame.Vector2(100, 250)
pos_atual_cabeca = pygame.Vector2(pos_base)
pos_alvo = pygame.Vector2(750, 250) 

estado_planta = "REPOUSANDO"
inicio_carga = 0
velocidade_dash = 25
sistema_particulas = []

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and estado_planta == "REPOUSANDO":
            estado_planta = "CARREGANDO"
            inicio_carga = pygame.time.get_ticks()

    tempo_atual = pygame.time.get_ticks()
    centro_planta_x = pos_atual_cabeca.x + (len(mec_predador[0]) * TAMANHO_PIXEL) / 2
    centro_planta_y = pos_atual_cabeca.y + (len(mec_predador) * TAMANHO_PIXEL) / 2

    if estado_planta == "CARREGANDO":
        tempo_passado = tempo_atual - inicio_carga
        
        for _ in range(8):
            angulo = random.uniform(0, math.pi * 2)
            distancia = random.uniform(40, 100)
            px = centro_planta_x + math.cos(angulo) * distancia
            py = centro_planta_y + math.sin(angulo) * distancia
            dx = (centro_planta_x - px) * 0.08
            dy = (centro_planta_y - py) * 0.08
            cor = random.choice([ENERGIA_NUCLEO, ENERGIA_COROA])
            sistema_particulas.append(Particula(px, py, dx, dy, cor, random.randint(20, 40)))

        if tempo_passado >= 2000:
            estado_planta = "ATACANDO"
            
    elif estado_planta == "ATACANDO":
        direcao = pos_alvo - pos_atual_cabeca
        dist = direcao.length()
        
        for _ in range(15):
            px = centro_planta_x + random.uniform(-30, 30)
            py = centro_planta_y + random.uniform(-30, 30)
            sistema_particulas.append(Particula(px, py, random.uniform(-5, -1), random.uniform(-2, 2), RRASTRO_CINETICO, random.randint(15, 30)))

        if dist > velocidade_dash:
            direcao.normalize_ip()
            pos_atual_cabeca += direcao * velocidade_dash
        else:
            pos_atual_cabeca = pygame.Vector2(pos_alvo)
            estado_planta = "RETORNANDO"

    elif estado_planta == "RETORNANDO":
        direcao = pos_base - pos_atual_cabeca
        dist = direcao.length()
        if dist > 8:
            direcao.normalize_ip()
            pos_atual_cabeca += direcao * 8
        else:
            pos_atual_cabeca = pygame.Vector2(pos_base)
            estado_planta = "REPOUSANDO"

    for p in sistema_particulas[:]:
        p.atualizar()
        if p.vida <= 0:
            sistema_particulas.remove(p)

    tela.fill((20, 20, 25))
    pygame.draw.circle(tela, (255, 50, 50), (int(pos_alvo.x + (len(mec_predador[0]) * TAMANHO_PIXEL) / 2), int(pos_alvo.y + (len(mec_predador) * TAMANHO_PIXEL) / 2)), 12)

    for p in sistema_particulas:
        p.desenhar(tela)

    desenhar_planta(mec_predador, pos_atual_cabeca.x, pos_atual_cabeca.y)

    fonte = pygame.font.SysFont("consolas", 20)
    tela.blit(fonte.render(f"ESTADO: {estado_planta}", True, (255, 255, 255)), (20, 20))
    tela.blit(fonte.render("ESPAÇO: Engajar Motor Cinético", True, (150, 150, 150)), (20, 50))

    pygame.display.flip()
    relogio.tick(100)