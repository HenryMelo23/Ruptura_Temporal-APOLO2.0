import sys

with open('GAME5.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith('        def encontrar_alvo_seguro_grid(self, px, py, projeteis, ratos, boss_hitbox, laser):'):
        start_idx = i
    if start_idx != -1 and line.startswith('            return melhor_alvo'):
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    new_func = """        def encontrar_alvo_seguro_grid(self, px, py, projeteis, ratos, boss_hitbox, laser):
            import math
            import numpy as np
            tamanho_celula = 80
            cols = largura_mapa // tamanho_celula
            rows = altura_mapa // tamanho_celula
            
            col_atual = int(px / tamanho_celula)
            row_atual = int(py / tamanho_celula)
            
            c_min, c_max = max(0, col_atual - 3), min(cols, col_atual + 4)
            r_min, r_max = max(0, row_atual - 3), min(rows, row_atual + 4)
            
            if c_max <= c_min or r_max <= r_min:
                return (px, py)
                
            C, R = np.meshgrid(np.arange(c_min, c_max), np.arange(r_min, r_max))
            CX = C * tamanho_celula + tamanho_celula // 2
            CY = R * tamanho_celula + tamanho_celula // 2
            SCORE = np.zeros_like(CX, dtype=np.float32)
            
            # 1. Projéteis
            if projeteis:
                px_arr = np.array([p['rect'].centerx if 'rect' in p else p.get('x', px) for p in projeteis])
                py_arr = np.array([p['rect'].centery if 'rect' in p else p.get('y', py) for p in projeteis])
                dx = CX[..., np.newaxis] - px_arr
                dy = CY[..., np.newaxis] - py_arr
                dist_proj = np.min(np.hypot(dx, dy), axis=-1)
                mask = dist_proj < 120
                SCORE[mask] -= (120 - dist_proj[mask]) * 5.0

            # 2. Ratos
            if ratos:
                rx_arr = np.array([r.pos_x for r in ratos])
                ry_arr = np.array([r.pos_y for r in ratos])
                dx = CX[..., np.newaxis] - rx_arr
                dy = CY[..., np.newaxis] - ry_arr
                dist_rato = np.min(np.hypot(dx, dy), axis=-1)
                mask = dist_rato < 150
                SCORE[mask] -= (150 - dist_rato[mask]) * 3.0

            # 3. Kiting Umbra e LoS
            origem_laser = (boss_hitbox.centerx, boss_hitbox.centery) if boss_hitbox else (largura_mapa//2, altura_mapa//2)
            dist_boss = np.hypot(CX - origem_laser[0], CY - origem_laser[1])
            SCORE[dist_boss < 200] -= (200 - dist_boss[dist_boss < 200]) * 2.0
            SCORE[dist_boss > 600] -= (dist_boss[dist_boss > 600] - 600) * 0.5
            
            ang_umbra_apolo = math.atan2(py - origem_laser[1], px - origem_laser[0])
            ang_umbra_celula = np.arctan2(CY - origem_laser[1], CX - origem_laser[0])
            diff_ang = np.abs(ang_umbra_apolo - ang_umbra_celula)
            diff_ang[diff_ang > math.pi] = 2 * math.pi - diff_ang[diff_ang > math.pi]
            mask_ang = diff_ang < 0.35
            SCORE[mask_ang] -= (0.35 - diff_ang[mask_ang]) * 500.0

            # 4. Laser Rotativo
            laser_disparando = laser and laser.get('fase') == 'disparando'
            if laser_disparando:
                import pygame
                agora = pygame.time.get_ticks()
                t_disp = agora - laser.get('tempo_inicio_disparo', agora)
                duracao_disp = laser.get('duracao_disparo', 4000)
                progresso = min(1.0, t_disp / duracao_disp)
                prog_futuro = min(1.0, (t_disp + 400.0) / duracao_disp)
                rodada = laser.get('rodada', 1)
                num_feixes, sentido, giro_total = 1, 1, math.pi * 2
                if rodada == 2: num_feixes, sentido = 2, -1
                elif rodada == 3: num_feixes, giro_total = 4, math.pi * 0.8
                elif rodada == 4: num_feixes, sentido, giro_total = 6, -1, math.pi * 0.8
                
                angulo_base = laser.get('angulo_base_inicio', 0.0) + giro_total * progresso * sentido
                ang_base_futuro = laser.get('angulo_base_inicio', 0.0) + giro_total * prog_futuro * sentido
                
                menor_dist_laser = np.full_like(CX, np.inf)
                em_frente = np.zeros_like(CX, dtype=bool)
                
                for i in range(num_feixes):
                    ang_atual = angulo_base + i * ((math.pi * 2) / num_feixes)
                    ang_futuro = ang_base_futuro + i * ((math.pi * 2) / num_feixes)
                    
                    for ang_teste in [ang_atual, ang_futuro]:
                        cos_ang = math.cos(ang_teste)
                        sin_ang = math.sin(ang_teste)
                        fim_x = origem_laser[0] + cos_ang * 2500
                        fim_y = origem_laser[1] + sin_ang * 2500
                        
                        num_val = np.abs((fim_y - origem_laser[1])*CX - (fim_x - origem_laser[0])*CY + fim_x*origem_laser[1] - fim_y*origem_laser[0])
                        den = math.hypot(fim_y - origem_laser[1], fim_x - origem_laser[0])
                        dist_l = num_val / den if den > 0 else 9999
                        dot = (CX - origem_laser[0]) * cos_ang + (CY - origem_laser[1]) * sin_ang
                        
                        mask_frente = dot > 0
                        em_frente |= mask_frente
                        menor_dist_laser = np.where(mask_frente & (dist_l < menor_dist_laser), dist_l, menor_dist_laser)
                        
                    ang_ponto = np.arctan2(CY - origem_laser[1], CX - origem_laser[0])
                    diff_pt = np.arctan2(np.sin(ang_ponto - ang_atual), np.cos(ang_ponto - ang_atual))
                    diff_ft = np.arctan2(np.sin(ang_futuro - ang_atual), np.cos(ang_futuro - ang_atual))
                    mask_sweep = (diff_pt * diff_ft > 0) & (np.abs(diff_pt) <= np.abs(diff_ft))
                    
                    menor_dist_laser[mask_sweep] = 0.0
                    em_frente |= mask_sweep
                    
                mask_laser = em_frente & (menor_dist_laser < 180)
                mask_fatal = mask_laser & (menor_dist_laser < 50)
                mask_dano = mask_laser & ~mask_fatal
                SCORE[mask_fatal] -= np.inf
                SCORE[mask_dano] -= (180 - menor_dist_laser[mask_dano]) * 15.0

            # 5. Distância Apolo e Bordas
            dist_apolo = np.hypot(CX - px, CY - py)
            SCORE -= dist_apolo * 0.2
            mask_borda = (CX < 100) | (CX > largura_mapa - 100) | (CY < 100) | (CY > altura_mapa - 100)
            SCORE[mask_borda] -= 50.0
            
            idx = np.argmax(SCORE)
            return (int(CX.flat[idx]), int(CY.flat[idx]))\n"""
    
    out = lines[:start_idx] + [new_func] + lines[end_idx+1:]
    with open('GAME5.py', 'w', encoding='utf-8') as f:
        f.writelines(out)
    print("Substituição concluída!")
else:
    print("Falha ao encontrar blocos.")
