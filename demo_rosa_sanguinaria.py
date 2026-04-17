"""
DEMONSTRAÇÃO: Rosa Sanguinária
Jardim Mortal com Múltiplas Flores @ 100 FPS
"""

import pygame
import sys
from rosa_sanguinaria import RosaSanguinaria, Paleta, FPS_TARGET

def main():
    pygame.init()
    
    LARGURA = 1920
    ALTURA = 1080
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("ROSA SANGUINÁRIA: Jardim Mortal @ 100 FPS")
    
    clock = pygame.time.Clock()
    
    # Jardim de rosas em formação
    rosas = [
        RosaSanguinaria(300, 300),
        RosaSanguinaria(300, 540),
        RosaSanguinaria(300, 780),
        RosaSanguinaria(LARGURA - 300, 540),
    ]
    
    # Alvo móvel
    alvo_x = LARGURA // 2
    alvo_y = ALTURA // 2
    alvo_vx = 250
    alvo_vy = 180
    
    # Modo automático
    modo_auto = True
    tempo_proximo_ataque = [0.0, 1.0, 2.0, 3.0]
    
    # Estatísticas
    total_ataques = 0
    ataques_acertados = 0
    
    rodando = True
    while rodando:
        dt = clock.tick(FPS_TARGET) / 1000.0
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            
            if evento.type == pygame.MOUSEBUTTONDOWN:
                mx, my = evento.pos
                for rosa in rosas:
                    if rosa.iniciar_ataque(mx, my):
                        total_ataques += 1
            
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_SPACE:
                    modo_auto = not modo_auto
                
                if evento.key == pygame.K_a:
                    for rosa in rosas:
                        if rosa.iniciar_ataque(alvo_x, alvo_y):
                            total_ataques += 1
                
                if evento.key == pygame.K_r:
                    total_ataques = 0
                    ataques_acertados = 0
        
        # Atualiza alvo móvel
        alvo_x += alvo_vx * dt
        alvo_y += alvo_vy * dt
        
        if alvo_x < 150 or alvo_x > LARGURA - 150:
            alvo_vx *= -1
            alvo_vx += (alvo_vx > 0) * 20 - 10
        if alvo_y < 150 or alvo_y > ALTURA - 150:
            alvo_vy *= -1
            alvo_vy += (alvo_vy > 0) * 20 - 10
        
        # Modo automático
        if modo_auto:
            for i, rosa in enumerate(rosas):
                tempo_proximo_ataque[i] -= dt
                if tempo_proximo_ataque[i] <= 0:
                    if rosa.iniciar_ataque(alvo_x, alvo_y):
                        total_ataques += 1
                        tempo_proximo_ataque[i] = 5.0 + i * 0.5
        
        # Atualiza rosas
        for rosa in rosas:
            rosa.atualizar(dt)
            
            hitbox = rosa.obter_hitbox()
            if hitbox.collidepoint(int(alvo_x), int(alvo_y)):
                if rosa.estado.value == "ATACANDO":
                    ataques_acertados += 1
        
        # Renderização
        tela.fill(Paleta.VAZIO_ESPACIAL)
        
        # Grid decorativo
        for x in range(0, LARGURA, 100):
            pygame.draw.line(tela, (25, 25, 30), (x, 0), (x, ALTURA), 1)
        for y in range(0, ALTURA, 100):
            pygame.draw.line(tela, (25, 25, 30), (0, y), (LARGURA, y), 1)
        
        # Desenha alvo
        pygame.draw.circle(tela, (100, 255, 100), (int(alvo_x), int(alvo_y)), 18)
        pygame.draw.circle(tela, (150, 255, 150), (int(alvo_x), int(alvo_y)), 25, 2)
        pygame.draw.circle(tela, (50, 200, 50), (int(alvo_x), int(alvo_y)), 8)
        
        # Renderiza rosas
        for rosa in rosas:
            rosa.renderizar(tela)
        
        # HUD
        fonte_titulo = pygame.font.Font(None, 36)
        fonte_normal = pygame.font.Font(None, 28)
        fonte_pequena = pygame.font.Font(None, 22)
        
        # Título
        titulo = fonte_titulo.render("ROSA SANGUINÁRIA: JARDIM MORTAL", True, Paleta.ROSA_NEON)
        tela.blit(titulo, (10, 10))
        
        # FPS
        fps_texto = fonte_normal.render(f"FPS: {int(clock.get_fps())}", True, (0, 255, 0))
        tela.blit(fps_texto, (10, 50))
        
        # Modo
        cor_modo = (255, 200, 100) if modo_auto else (150, 150, 150)
        modo_texto = fonte_normal.render(f"Modo: {'AUTOMÁTICO' if modo_auto else 'MANUAL'}", True, cor_modo)
        tela.blit(modo_texto, (10, 80))
        
        # Estatísticas
        stats_y = 120
        
        # Conta total de pólen e explosões
        total_polen = sum(len(rosa.polens_explosivos) for rosa in rosas)
        total_explosoes = sum(len(rosa.explosoes) for rosa in rosas)
        
        stats = [
            f"Ataques Totais: {total_ataques}",
            f"Ataques Acertados: {ataques_acertados}",
            f"Taxa de Acerto: {(ataques_acertados/max(1, total_ataques)*100):.1f}%",
            f"Pólen Ativo: {total_polen}",
            f"Explosões Ativas: {total_explosoes}",
        ]
        for stat in stats:
            texto = fonte_normal.render(stat, True, (255, 150, 200))
            tela.blit(texto, (10, stats_y))
            stats_y += 30
        
        # Instruções
        instrucoes_y = ALTURA - 150
        instrucoes = [
            "CONTROLES:",
            "ESPAÇO: Alternar Auto/Manual",
            "A: Atacar Alvo Atual",
            "CLIQUE: Atacar Posição",
            "R: Reset Estatísticas",
        ]
        
        for i, texto in enumerate(instrucoes):
            cor = (255, 255, 255) if i == 0 else (200, 200, 200)
            linha = fonte_pequena.render(texto, True, cor)
            tela.blit(linha, (10, instrucoes_y + i * 25))
        
        # Status das rosas
        status_x = LARGURA - 450
        status_y = 10
        status_titulo = fonte_normal.render("STATUS DO JARDIM:", True, Paleta.ROSA_INTENSO)
        tela.blit(status_titulo, (status_x, status_y))
        
        for i, rosa in enumerate(rosas):
            status_y += 35
            cor_estado = {
                "REPOUSANDO": (150, 255, 150),
                "CARREGANDO": (255, 200, 100),
                "ATACANDO": (255, 80, 100),
                "RETORNANDO": (150, 200, 255),
            }.get(rosa.estado.value, (255, 255, 255))
            
            texto = fonte_pequena.render(
                f"Rosa {i+1}: {rosa.estado.value} | Rot: {int(rosa.angulo_rotacao_petalas)}°", 
                True, cor_estado
            )
            tela.blit(texto, (status_x, status_y))
        
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
