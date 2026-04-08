#!/usr/bin/env python3
"""
TESTE VISUAL: Verificação dos designs dos projéteis
Mostra lado a lado os projéteis do Apolo e da Umbra
"""

import pygame
import math
import sys

# Importa os motores VFX
from vfx_engine_apolo import ApoloVFXManager
import habilidade_boss as hb

pygame.init()

# Configuração da tela
LARGURA, ALTURA = 800, 400
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Teste Visual - Projéteis Invertidos")

# Inicializa VFX
vfx_apolo = ApoloVFXManager()

# Estado simulado da Umbra
estado_ia_umbra = {
    'projeteis': [
        {
            'rect': pygame.Rect(600, 200, 12, 12),
            'angulo': 0,
            'velocidade': 0,
            'tipo': 'comum'
        }
    ],
    'vfx_particulas': []
}

# Relógio
clock = pygame.time.Clock()
fonte = pygame.font.Font(None, 24)
fonte_titulo = pygame.font.Font(None, 36)

# Loop principal
rodando = True
frame = 0

print("=" * 80)
print("TESTE VISUAL - DESIGNS DOS PROJÉTEIS")
print("=" * 80)
print("\nVisualizando:")
print("  ESQUERDA: Projétil do Apolo (Verde+Azul Yin-Yang)")
print("  DIREITA:  Projétil da Umbra (Azul Ciano Radiante)")
print("\nPressione ESC para sair")
print("=" * 80)

while rodando:
    agora = pygame.time.get_ticks()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            rodando = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                rodando = False
    
    # Limpa tela
    tela.fill((20, 20, 30))
    
    # Linha divisória
    pygame.draw.line(tela, (100, 100, 100), (LARGURA // 2, 0), (LARGURA // 2, ALTURA), 2)
    
    # Títulos
    titulo_apolo = fonte_titulo.render("APOLO", True, (0, 255, 150))
    titulo_umbra = fonte_titulo.render("UMBRA", True, (0, 210, 255))
    tela.blit(titulo_apolo, (150, 30))
    tela.blit(titulo_umbra, (550, 30))
    
    # Descrições
    desc_apolo_1 = fonte.render("Verde + Azul", True, (200, 200, 200))
    desc_apolo_2 = fonte.render("Yin-Yang", True, (200, 200, 200))
    desc_apolo_3 = fonte.render("2 arcos", True, (200, 200, 200))
    
    desc_umbra_1 = fonte.render("Azul Ciano", True, (200, 200, 200))
    desc_umbra_2 = fonte.render("Radiante", True, (200, 200, 200))
    desc_umbra_3 = fonte.render("3 camadas", True, (200, 200, 200))
    
    tela.blit(desc_apolo_1, (130, 320))
    tela.blit(desc_apolo_2, (140, 345))
    tela.blit(desc_apolo_3, (150, 370))
    
    tela.blit(desc_umbra_1, (530, 320))
    tela.blit(desc_umbra_2, (540, 345))
    tela.blit(desc_umbra_3, (535, 370))
    
    # Renderiza projétil do Apolo (esquerda)
    centro_apolo = (200, 200)
    vfx_apolo.renderizar_plasma_apolo(tela, centro_apolo, agora)
    
    # Renderiza projétil da Umbra (direita)
    hb.renderizar_vfx_umbra(tela, agora, estado_ia_umbra)
    
    # Adiciona algumas partículas de teste
    if frame % 30 == 0:
        # Partículas do Apolo
        vfx_apolo.criar_impacto_fragmentado(200, 200, (0, 255, 150))
        
        # Partículas da Umbra
        hb.gerar_burst_desfragmentacao(600, 200, estado_ia_umbra, (0, 210, 255))
    
    # Atualiza partículas
    vfx_apolo.atualizar_e_desenhar(tela, agora)
    
    # Info de frame
    info_frame = fonte.render(f"Frame: {frame}", True, (150, 150, 150))
    tela.blit(info_frame, (10, 10))
    
    pygame.display.flip()
    clock.tick(60)
    frame += 1

pygame.quit()

print("\n" + "=" * 80)
print("TESTE CONCLUÍDO")
print("=" * 80)
print("\nResultado esperado:")
print("  ✓ Apolo: Projétil verde+azul com efeito Yin-Yang")
print("  ✓ Umbra: Projétil azul ciano radiante com aura intensa")
print("  ✓ Sem erros de cor (ValueError)")
print("=" * 80)

sys.exit(0)
