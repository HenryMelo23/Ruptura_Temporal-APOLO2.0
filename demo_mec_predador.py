"""
DEMONSTRAÇÃO: Mec-Predador Biomecânico
Simulação de Alto Desempenho @ 100 FPS
Integração com Sistema de Jogo Existente
"""

import pygame
import sys
from mec_predador import MecPredador, Paleta, FPS_TARGET

def main():
    pygame.init()
    
    # Configuração
    LARGURA = 1920
    ALTURA = 1080
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("MEC-PREDADOR: Terror Biomecânico @ 100 FPS")
    
    clock = pygame.time.Clock()
    
    # Instancia múltiplos predadores em formação
    predadores = [
        MecPredador(300, 300),
        MecPredador(300, 780),
        MecPredador(LARGURA - 400, ALTURA // 2),
    ]
    
    # Alvo móvel (simula jogador)
    alvo_x = LARGURA // 2
    alvo_y = ALTURA // 2
    alvo_vx = 250
    alvo_vy = 180
    
    # Modo automático
    modo_auto = True
    tempo_proximo_ataque = [0.0, 1.5, 3.0]  # Ataques escalonados
    
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
                # Clique: todos atacam o ponto
                mx, my = evento.pos
                for pred in predadores:
                    if pred.iniciar_ataque(mx, my):
                        total_ataques += 1
            
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_SPACE:
                    modo_auto = not modo_auto
                
                if evento.key == pygame.K_a:
                    # Ataque manual ao alvo
                    for pred in predadores:
                        if pred.iniciar_ataque(alvo_x, alvo_y):
                            total_ataques += 1
                
                if evento.key == pygame.K_r:
                    # Reset estatísticas
                    total_ataques = 0
                    ataques_acertados = 0
        
        # Atualiza alvo móvel (simula jogador)
        alvo_x += alvo_vx * dt
        alvo_y += alvo_vy * dt
        
        # Rebate nas bordas com variação de velocidade
        if alvo_x < 150 or alvo_x > LARGURA - 150:
            alvo_vx *= -1
            alvo_vx += (alvo_vx > 0) * 20 - 10  # Variação aleatória
        if alvo_y < 150 or alvo_y > ALTURA - 150:
            alvo_vy *= -1
            alvo_vy += (alvo_vy > 0) * 20 - 10
        
        # Modo automático: ataques coordenados
        if modo_auto:
            for i, pred in enumerate(predadores):
                tempo_proximo_ataque[i] -= dt
                if tempo_proximo_ataque[i] <= 0:
                    if pred.iniciar_ataque(alvo_x, alvo_y):
                        total_ataques += 1
                        tempo_proximo_ataque[i] = 5.0 + i * 0.5  # Escalonamento
        
        # Atualiza predadores
        for pred in predadores:
            pred.atualizar(dt)
            
            # Detecta colisão com alvo
            hitbox = pred.obter_hitbox()
            if hitbox.collidepoint(int(alvo_x), int(alvo_y)):
                if pred.estado.value == "ATACANDO":
                    ataques_acertados += 1
        
        # Renderização
        tela.fill(Paleta.VAZIO_ESPACIAL)
        
        # Grid de fundo (opcional)
        for x in range(0, LARGURA, 100):
            pygame.draw.line(tela, (30, 30, 35), (x, 0), (x, ALTURA), 1)
        for y in range(0, ALTURA, 100):
            pygame.draw.line(tela, (30, 30, 35), (0, y), (LARGURA, y), 1)
        
        # Desenha alvo (jogador simulado)
        pygame.draw.circle(tela, (255, 100, 100), (int(alvo_x), int(alvo_y)), 18)
        pygame.draw.circle(tela, (255, 200, 200), (int(alvo_x), int(alvo_y)), 25, 2)
        pygame.draw.circle(tela, (255, 50, 50), (int(alvo_x), int(alvo_y)), 8)
        
        # Renderiza predadores
        for pred in predadores:
            pred.renderizar(tela)
        
        # HUD Avançado
        fonte_titulo = pygame.font.Font(None, 36)
        fonte_normal = pygame.font.Font(None, 28)
        fonte_pequena = pygame.font.Font(None, 22)
        
        # Título
        titulo = fonte_titulo.render("MEC-PREDADOR COM ASAS: SIMULAÇÃO BIOMECÂNICA", True, Paleta.CIANO_VIBRANTE)
        tela.blit(titulo, (10, 10))
        
        # FPS
        fps_texto = fonte_normal.render(f"FPS: {int(clock.get_fps())}", True, (0, 255, 0))
        tela.blit(fps_texto, (10, 50))
        
        # Modo
        cor_modo = (255, 255, 0) if modo_auto else (150, 150, 150)
        modo_texto = fonte_normal.render(f"Modo: {'AUTOMÁTICO' if modo_auto else 'MANUAL'}", True, cor_modo)
        tela.blit(modo_texto, (10, 80))
        
        # Estatísticas
        stats_y = 120
        stats = [
            f"Ataques Totais: {total_ataques}",
            f"Ataques Acertados: {ataques_acertados}",
            f"Taxa de Acerto: {(ataques_acertados/max(1, total_ataques)*100):.1f}%",
        ]
        for stat in stats:
            texto = fonte_normal.render(stat, True, (200, 200, 255))
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
            cor = (255, 255, 255) if i == 0 else (180, 180, 180)
            linha = fonte_pequena.render(texto, True, cor)
            tela.blit(linha, (10, instrucoes_y + i * 25))
        
        # Status dos predadores (com ângulo)
        status_x = LARGURA - 400
        status_y = 10
        status_titulo = fonte_normal.render("STATUS PREDADORES:", True, Paleta.ROSA_NEON)
        tela.blit(status_titulo, (status_x, status_y))
        
        for i, pred in enumerate(predadores):
            status_y += 35
            cor_estado = {
                "REPOUSANDO": (100, 255, 100),
                "CARREGANDO": (255, 255, 0),
                "ATACANDO": (255, 100, 100),
                "RETORNANDO": (100, 200, 255),
            }.get(pred.estado.value, (255, 255, 255))
            
            texto = fonte_pequena.render(
                f"Predador {i+1}: {pred.estado.value} | Ângulo: {int(pred.angulo_rotacao)}°", 
                True, cor_estado
            )
            tela.blit(texto, (status_x, status_y))
        
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
