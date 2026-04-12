import re

with open('GAME5.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. REMOVER O BLOCO INTEIRO DE BORDAS TÓXICAS DO LOOP DE DISPAROS
# Ele começava num comentário e terminava no reset de bordas.
regex_remover_bordas = r'                # --- RENDERIZAÇÃO E FÍSICA DAS BORDAS VENENOSAS \(RASTRO\) ---.*?tempo_acumulado_bordas = 0'
text = re.sub(regex_remover_bordas, '', text, flags=re.DOTALL)


# 2. CRIAR O MOTOR GLOBAL DA PRAGA DE RATOS (A SER INJETADO FORA DO LOOP)
motor_ratos = """    # --- MOTOR DE PRAGA DE RATOS (DIMENSÃO 9) ---
    if estado_atual_ia.get('dimensao_ativa') == "rastro":
        ratos = estado_atual_ia.get('ratos_ativos', [])
        novos_ratos = []
        for rato in ratos:
            vivo = True
            # Steering Boids (Cercamento Implacável)
            dx = pos_x_personagem + largura_personagem//2 - rato['x']
            dy = pos_y_personagem + altura_personagem//2 - rato['y']
            dist = math.hypot(dx, dy)
            if dist > 0:
                rato['x'] += (dx/dist) * 6.0
                rato['y'] += (dy/dist) * 6.0
            
            # Colisão com o Jogador (Lifesteal)
            if dist < 30 and vivo:
                vivo = False
                vida -= 5.0
                vida_boss5 = min(vida_boss_maxima, vida_boss5 + 20)
                estado_atual_ia['ratos_adicionais'] = estado_atual_ia.get('ratos_adicionais', 0) + 1
                
                memoria_umbra.treinar(5.0)  # Recompensa alta pra Umbra
                apolo.aplicar_recompensa_direta(-5.0)  # Punição pro Apolo
                
                efeitos_texto.append({"texto": "+20 LIFESTEAL UMBRA", "x": pos_x_umbra, "y": pos_y_umbra - 30, "tempo_inicio": agora, "cor": (50, 255, 50)})
                efeitos_texto.append({"texto": "+1 RATO PERMANENTE", "x": pos_x_umbra, "y": pos_y_umbra - 50, "tempo_inicio": agora, "cor": (150, 0, 150)})
            
            # Bloqueio Ativo (Escudo de Carne / Destruição de Ratos)
            for tiro in list(disparos): # Itera uma cópia de disparos globais
                dist_tiro = math.hypot(tiro['rect'].centerx - rato['x'], tiro['rect'].centery - rato['y'])
                if dist_tiro < 25 and vivo:
                    vivo = False
                    if tiro in disparos:
                        disparos.remove(tiro)
                    efeitos_texto.append({"texto": "SPLAT!", "x": rato['x'], "y": rato['y'], "tempo_inicio": agora, "cor": (100, 0, 100)})
                    apolo.aplicar_recompensa_direta(0.5) # Micro recompensa pro player acertar rato
                    break
            
            if vivo:
                novos_ratos.append(rato)
                # Arte Procedural Boids/Rato (Borda de caos púrpura)
                pygame.draw.circle(tela, (20, 10, 30), (int(rato['x']), int(rato['y'])), 12)
                pygame.draw.circle(tela, (130, 20, 150), (int(rato['x']), int(rato['y'])), 8)
                pygame.draw.circle(tela, (50, 255, 50), (int(rato['x']+random.randint(-2,2)), int(rato['y']+random.randint(-2,2))), 3)
                
        estado_atual_ia['ratos_ativos'] = novos_ratos

    novos_disparos = []
"""

# Injetar o motor ratos logo antes do loop "novos_disparos = []"
text = text.replace("    novos_disparos = []", motor_ratos)

with open('GAME5.py', 'w', encoding='utf-8') as f:
    f.write(text)
