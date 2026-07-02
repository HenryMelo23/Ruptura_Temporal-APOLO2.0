import pygame
import math
import random

def atualizar_fisica_gosma(disparo, dt):
    """
    Atualiza a física do projétil de gosma, aplicando arrasto (drag) até a velocidade terminal.
    """
    vx, vy = disparo.get("velocidade", (0, 0))
    speed = math.hypot(vx, vy)
    
    vel_terminal = disparo.get("velocidade_terminal", 4.5)
    
    # Aplica arrasto (desaceleração) se estiver muito rápido
    if speed > vel_terminal:
        # Fator de arrasto (0.94 por frame, mas ajustado por dt se necessário)
        fator_arrasto = 0.94
        vx *= fator_arrasto
        vy *= fator_arrasto
    
    # Garante que o rect seja atualizado com as frações (usando pos_x, pos_y)
    if "pos_x" not in disparo:
        disparo["pos_x"] = float(disparo["rect"].x)
        disparo["pos_y"] = float(disparo["rect"].y)
        
    disparo["pos_x"] += vx
    disparo["pos_y"] += vy
    disparo["rect"].x = int(disparo["pos_x"])
    disparo["rect"].y = int(disparo["pos_y"])
    disparo["velocidade"] = (vx, vy)


def desenhar_gosma_procedural(tela, disparo, tempo_atual, config_graficos):
    """
    Renderiza um projétil gelatinoso com rastro e balanço (wiggle) baseados
    na física e velocidade atual, respeitando a configuração gráfica.
    """
    vx, vy = disparo.get("velocidade", (0, 0))
    speed = math.hypot(vx, vy)
    
    # Se estiver quase parado, assume ângulo do centro da tela só para não dar erro
    if speed < 0.1:
        angulo = 0
    else:
        angulo = math.atan2(vy, vx)
    
    centro_x = disparo["rect"].centerx
    centro_y = disparo["rect"].centery
    
    # Dimensões baseadas na velocidade
    raio_cabeca = 10
    raio_cauda = 4
    
    # A cauda estica mais quanto mais rápido está
    comprimento = raio_cabeca + (speed * 2.8)
    
    # Oscilação da cauda (wiggle)
    idade = tempo_atual - disparo.get("nascimento", tempo_atual)
    # Frequência e amplitude da oscilação do catarro
    oscilacao = math.sin(idade * 0.015) * (speed * 0.6 + 2)
    
    # Posição da cauda (para trás da direção do movimento, somando a oscilação perpendicular)
    perp_dir = angulo + math.pi/2
    cauda_x = centro_x - math.cos(angulo) * comprimento + math.cos(perp_dir) * oscilacao
    cauda_y = centro_y - math.sin(angulo) * comprimento + math.sin(perp_dir) * oscilacao
    
    # Pontos para desenhar o corpo que liga cabeça e cauda
    angulo_corpo = math.atan2(centro_y - cauda_y, centro_x - cauda_x)
    perp_cauda = angulo_corpo + math.pi/2
    
    p1 = (centro_x + math.cos(perp_dir) * raio_cabeca, centro_y + math.sin(perp_dir) * raio_cabeca)
    p2 = (centro_x - math.cos(perp_dir) * raio_cabeca, centro_y - math.sin(perp_dir) * raio_cabeca)
    p3 = (cauda_x - math.cos(perp_cauda) * raio_cauda, cauda_y - math.sin(perp_cauda) * raio_cauda)
    p4 = (cauda_x + math.cos(perp_cauda) * raio_cauda, cauda_y + math.sin(perp_cauda) * raio_cauda)
    
    # Paleta de cores da gosma (tons de verde melequento)
    cor_borda = (15, 80, 25)
    cor_miolo = (95, 210, 50)
    cor_brilho = (200, 255, 170)
    cor_miolo_escuro = (60, 160, 35)
    
    # ----- DESENHO DO CORPO (POLÍGONO) -----
    pygame.draw.polygon(tela, cor_borda, [p1, p2, p3, p4])
    
    # Shrink interior points for fill
    shrink = 2
    p1_i = (centro_x + math.cos(perp_dir) * (raio_cabeca - shrink), centro_y + math.sin(perp_dir) * (raio_cabeca - shrink))
    p2_i = (centro_x - math.cos(perp_dir) * (raio_cabeca - shrink), centro_y - math.sin(perp_dir) * (raio_cabeca - shrink))
    p3_i = (cauda_x - math.cos(perp_cauda) * max(1, raio_cauda - 1), cauda_y - math.sin(perp_cauda) * max(1, raio_cauda - 1))
    p4_i = (cauda_x + math.cos(perp_cauda) * max(1, raio_cauda - 1), cauda_y + math.sin(perp_cauda) * max(1, raio_cauda - 1))
    
    # Gradiente fake: parte de trás mais escura
    pygame.draw.polygon(tela, cor_miolo_escuro, [p1_i, p2_i, p3_i, p4_i])
    # Parte da frente mais clara
    pygame.draw.polygon(tela, cor_miolo, [p1_i, p2_i, p3, p4])
    
    # ----- DESENHO DA CABEÇA E CAUDA (CÍRCULOS) -----
    pygame.draw.circle(tela, cor_borda, (int(centro_x), int(centro_y)), raio_cabeca)
    pygame.draw.circle(tela, cor_miolo, (int(centro_x), int(centro_y)), raio_cabeca - shrink)
    
    pygame.draw.circle(tela, cor_borda, (int(cauda_x), int(cauda_y)), raio_cauda)
    pygame.draw.circle(tela, cor_miolo_escuro, (int(cauda_x), int(cauda_y)), max(1, raio_cauda - 1))
    
    qualidade = config_graficos.get("qualidade_grafica", "alta")
    
    # Brilho de umidade na cabeça (highlight)
    if qualidade != "baixa":
        hl_x = centro_x + math.cos(angulo - math.pi/4) * (raio_cabeca * 0.4)
        hl_y = centro_y + math.sin(angulo - math.pi/4) * (raio_cabeca * 0.4)
        pygame.draw.circle(tela, cor_brilho, (int(hl_x), int(hl_y)), int(raio_cabeca * 0.35))
        
        # Ponto extra de detalhe orgânico
        hl2_x = centro_x + math.cos(angulo + math.pi/1.5) * (raio_cabeca * 0.5)
        hl2_y = centro_y + math.sin(angulo + math.pi/1.5) * (raio_cabeca * 0.5)
        pygame.draw.circle(tela, cor_miolo_escuro, (int(hl2_x), int(hl2_y)), int(raio_cabeca * 0.25))

    # ----- SISTEMA DE PARTÍCULAS (PINGOS DE GOSMA) -----
    if qualidade != "baixa":
        if "particulas_gosma" not in disparo:
            disparo["particulas_gosma"] = []
            
        chance_emissao = 0.85 if qualidade == "alta" else 0.4
        
        # Só emite partículas se estiver se movendo rápido o suficiente
        if speed > 2.0 and random.random() < chance_emissao:
            # Emite do meio pro fim da cauda
            spawn_x = centro_x - math.cos(angulo) * (comprimento * random.uniform(0.3, 1.0))
            spawn_y = centro_y - math.sin(angulo) * (comprimento * random.uniform(0.3, 1.0))
            
            disparo["particulas_gosma"].append({
                "x": spawn_x,
                "y": spawn_y,
                "vx": vx * random.uniform(0.1, 0.4) + (random.random() - 0.5) * 2.0,
                "vy": vy * random.uniform(0.1, 0.4) + (random.random() - 0.5) * 2.0,
                "raio": random.uniform(1.5, 4.5),
                "vida": random.randint(250, 600),
                "nascimento": tempo_atual
            })
            
        # Atualiza e desenha partículas
        novas_parts = []
        for p in disparo["particulas_gosma"]:
            idade_p = tempo_atual - p["nascimento"]
            if idade_p < p["vida"]:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                # Desaceleração das partículas
                p["vx"] *= 0.95
                p["vy"] *= 0.95
                
                progresso = idade_p / p["vida"]
                raio_atual = max(0, p["raio"] * (1.0 - progresso))
                
                if raio_atual > 0.5:
                    if qualidade == "alta":
                        alpha = int(255 * (1.0 - progresso))
                        s = pygame.Surface((int(raio_atual*2 + 2), int(raio_atual*2 + 2)), pygame.SRCALPHA)
                        pygame.draw.circle(s, (cor_miolo[0], cor_miolo[1], cor_miolo[2], alpha), (int(raio_atual+1), int(raio_atual+1)), int(raio_atual))
                        tela.blit(s, (int(p["x"] - raio_atual - 1), int(p["y"] - raio_atual - 1)))
                    else:
                        pygame.draw.circle(tela, cor_miolo, (int(p["x"]), int(p["y"])), int(raio_atual))
                    novas_parts.append(p)
        disparo["particulas_gosma"] = novas_parts
