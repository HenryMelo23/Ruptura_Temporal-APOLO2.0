import re

### 1. HABILIDADE BOSS
with open('habilidade_boss.py', 'r', encoding='utf-8') as f:
    hb = f.read()

# Trocar strings base
hb = hb.replace('BORDAS_TOXICAS', 'PRAGA_RATOS')

new_node = """def node_praga_ratos(agora, estado_ia):
    if agora - estado_ia.get('ultimo_praga', 0) >= 3000:
        estado_ia['ultimo_praga'] = agora
        if 'ratos_ativos' not in estado_ia:
            estado_ia['ratos_ativos'] = []
        if 'ratos_adicionais' not in estado_ia:
            estado_ia['ratos_adicionais'] = 0
            
        base_ratos = 4 + estado_ia['ratos_adicionais']
        cantos = [(150, 150), (1150, 150), (150, 600), (1150, 600)]
        for i in range(base_ratos):
            canto = cantos[i % 4]
            estado_ia['ratos_ativos'].append({
                'x': canto[0] + random.randint(-20, 20),
                'y': canto[1] + random.randint(-20, 20),
                'vx': 0.0,
                'vy': 0.0
            })
"""
hb = re.sub(r'def node_bordas_toxicas\(agora, estado_ia\):.*?(?=\n\n(?:def|#))', new_node, hb, flags=re.DOTALL)
hb = hb.replace('node_bordas_toxicas(agora, estado_ia)', 'node_praga_ratos(agora, estado_ia)')

with open('habilidade_boss.py', 'w', encoding='utf-8') as f:
    f.write(hb)

### 2. TREINO ACELERADO (Simulador Físico Ratos)
with open('treino_acelerado_v3_percepcao_expandida.py', 'r', encoding='utf-8') as f:
    ta = f.read()

ta = ta.replace('BORDAS_TOXICAS', 'PRAGA_RATOS')
ta = ta.replace('bordas_ativas', 'praga_ratos') # Keys do sensor de tensor

# Injetar estado de ratos_ativos no reset
ta_reset_inject = """            'velocidade_apolo_atual': velocidade_apolo_atual,
            'ratos_ativos': [],
            'ratos_adicionais': 0,
            'ultimo_praga': 0,"""
ta = ta.replace("            'velocidade_apolo_atual': velocidade_apolo_atual,\n            'estava_nas_bordas'", ta_reset_inject + "\n            'estava_nas_bordas'")

# Delete the exact old DANO DA BORDA logic and insert RATS.
new_rats_sim = """        # ===== ENXAME DE RATOS =====
        for rato in list(estado['ratos_ativos']):
            dx = estado['pos_apolo'][0] - rato['x']
            dy = estado['pos_apolo'][1] - rato['y']
            dist = math.hypot(dx, dy)
            if dist > 0:
                rato['x'] += (dx/dist) * 6.0
                rato['y'] += (dy/dist) * 6.0
            
            # Colisão com o Player
            if dist < 25 and not invulneravel:
                estado['vida_apolo'] -= 8
                estado['vida_umbra'] = min(estado['vida_max_umbra'], estado['vida_umbra'] + 20)
                estado['ratos_adicionais'] += 1
                self.umbra.treinar(5.0, prioridade=True)
                self.apolo.aplicar_recompensa_direta(-5.0)
                estado['ratos_ativos'].remove(rato)"""
ta = re.sub(r'        # ===== DANO DE BORDAS TÓXICAS =====.*?estado\[\'estava_nas_bordas\'\] = False', new_rats_sim, ta, flags=re.DOTALL)

with open('treino_acelerado_v3_percepcao_expandida.py', 'w', encoding='utf-8') as f:
    f.write(ta)
