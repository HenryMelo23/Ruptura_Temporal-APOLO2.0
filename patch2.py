import re

with open('treino_acelerado_v3_percepcao_expandida.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Substituir resetar_episodio
new_reset = """    def resetar_episodio(self):
        pos_apolo = [largura_mapa // 2, altura_mapa - 150]
        pos_umbra = [largura_mapa // 2, 150]
        
        vida_apolo = 1000.0
        vida_umbra = 1200.0
        vida_max_apolo = 1000.0
        vida_max_umbra = 1200.0
        
        projeteis_umbra = []
        historico_apolo = deque(maxlen=60)
        
        cd_ataque_umbra = 0
        cd_teleporte_apolo = 0
        cd_habilidade_especial = 0
        
        tempo_simulado = 0
        frames_sobrevividos = 0
        invulneravel_ate = 0
        velocidade_apolo_atual = 0
        
        return {
            'pos_apolo': pos_apolo,
            'pos_umbra': pos_umbra,
            'vida_apolo': vida_apolo,
            'vida_umbra': vida_umbra,
            'vida_max_apolo': vida_max_apolo,
            'vida_max_umbra': vida_max_umbra,
            'projeteis_umbra': projeteis_umbra,
            'historico_apolo': historico_apolo,
            'cd_ataque_umbra': cd_ataque_umbra,
            'cd_teleporte_apolo': cd_teleporte_apolo,
            'cd_habilidade_especial': cd_habilidade_especial,
            'tempo_simulado': tempo_simulado,
            'frames_sobrevividos': frames_sobrevividos,
            'invulneravel_ate': invulneravel_ate,
            'velocidade_apolo_atual': velocidade_apolo_atual,
            'estava_nas_bordas': False,
            'tempo_entrada_bordas': 0,
            'ultimo_tick_dano_bordas': 0,
            'laser_ativo': None
        }"""

code = re.sub(r'    def resetar_episodio\(self\):.*?        return \{.*?\n        \}', new_reset, code, flags=re.DOTALL)

# Substituir trecho de simular_frame da Umbra Habilidade (laser)
new_simular_frame_laser = """        elif acao_umbra == "HABILIDADE_ESPECIAL":
            estado['cd_habilidade_especial'] = 8000
            if not estado['laser_ativo']:
                estado['laser_ativo'] = {
                    'tempo_inicio': estado['tempo_simulado'],
                    'fase': 'carregando',
                    'rodada': 1,
                    'duracao_carga': 1500,
                    'duracao_disparo': 4000
                }
                
        # ===== ATUALIZAR LASER =====
        laser = estado['laser_ativo']
        if laser:
            tempo_laser = estado['tempo_simulado'] - laser['tempo_inicio']
            origem_laser = (estado['pos_umbra'][0] + largura_boss // 2, estado['pos_umbra'][1] + altura_boss // 2)
            
            if laser['fase'] == 'carregando':
                if tempo_laser >= laser['duracao_carga']:
                    laser['fase'] = 'disparando'
                    laser['tempo_inicio_disparo'] = estado['tempo_simulado']
            elif laser['fase'] == 'disparando':
                t_disp = estado['tempo_simulado'] - laser['tempo_inicio_disparo']
                progresso = min(1.0, t_disp / laser['duracao_disparo'])
                angulo_atual = laser.get('angulo_base', 0) + math.sin(progresso * math.pi * 4) * 0.5
                
                comp_laser = 2500
                fim_x = origem_laser[0] + math.cos(angulo_atual) * comp_laser
                fim_y = origem_laser[1] + math.sin(angulo_atual) * comp_laser
                
                # Hitbox Euclidiano do Laser
                px_c = estado['pos_apolo'][0] + largura_personagem // 2
                py_c = estado['pos_apolo'][1] + altura_personagem // 2
                
                numerador = abs((fim_y - origem_laser[1])*px_c - (fim_x - origem_laser[0])*py_c + fim_x*origem_laser[1] - fim_y*origem_laser[0])
                denominador = math.hypot(fim_y - origem_laser[1], fim_x - origem_laser[0])
                distancia = numerador / denominador if denominador != 0 else 999
                
                dot_product = (px_c - origem_laser[0]) * math.cos(angulo_atual) + (py_c - origem_laser[1]) * math.sin(angulo_atual)
                atingido = distancia < 25 and 0 < dot_product < comp_laser
                
                if atingido and estado['tempo_simulado'] - laser.get('ultimo_dano_laser', 0) > 100:
                    estado['vida_apolo'] -= 45
                    self.umbra.treinar(50.0, prioridade=True)
                    self.apolo.aplicar_recompensa_direta(-30.0)
                    laser['ultimo_dano_laser'] = estado['tempo_simulado']
                    
                if t_disp >= laser['duracao_disparo']:
                    estado['laser_ativo'] = None"""

code = code.replace("""        elif acao_umbra == "HABILIDADE_ESPECIAL":
            estado['cd_habilidade_especial'] = 8000""", new_simular_frame_laser)

# Substituir o Dano da Armadilha pelo Novo Dano da Borda Euclidiana
new_dano_bordas = """        # ===== DANO DE BORDAS TÓXICAS =====
        if armadilhas_ativas and not invulneravel:
            margem = 150
            nas_bordas = (estado['pos_apolo'][0] < margem or estado['pos_apolo'][0] > largura_mapa - margem - largura_personagem or
                          estado['pos_apolo'][1] < margem or estado['pos_apolo'][1] > altura_mapa - margem - altura_personagem)
            
            if nas_bordas:
                if not estado['estava_nas_bordas']:
                    estado['estava_nas_bordas'] = True
                    estado['tempo_entrada_bordas'] = estado['tempo_simulado']
                
                tempo_acumulado_bordas = estado['tempo_simulado'] - estado['tempo_entrada_bordas']
                if estado['tempo_simulado'] - estado['ultimo_tick_dano_bordas'] >= 800:
                    tempo_segundos = tempo_acumulado_bordas / 1000.0
                    dano_percentual = min(0.05, 0.005 + (tempo_segundos * 0.003))
                    dano_bordas = estado['vida_max_apolo'] * dano_percentual
                    estado['vida_apolo'] -= dano_bordas
                    estado['ultimo_tick_dano_bordas'] = estado['tempo_simulado']
                    
                    intensidade = min(1.0, tempo_segundos / 10.0)
                    self.umbra.treinar(2.0 + (intensidade * 3.0), prioridade=True)
                    punicao_apolo = -5.0 - (intensidade * 10.0)
                    self.apolo.aplicar_recompensa_direta(punicao_apolo)
            else:
                if estado['estava_nas_bordas']:
                    estado['estava_nas_bordas'] = False"""

code = code.replace("""        # ===== DANO DE ARMADILHA =====
        if armadilhas_ativas and not invulneravel:
            estado['vida_apolo'] -= 0.5""", new_dano_bordas)

# Check for fixed DT 16.6ms in simular_frame
code = code.replace("estado['tempo_simulado'] += 16", "estado['tempo_simulado'] += 16.666")
code = code.replace("estado['cd_ataque_umbra'] = max(0, estado['cd_ataque_umbra'] - 16)", "estado['cd_ataque_umbra'] = max(0, estado['cd_ataque_umbra'] - 16.666)")
code = code.replace("estado['cd_teleporte_apolo'] = max(0, estado['cd_teleporte_apolo'] - 16)", "estado['cd_teleporte_apolo'] = max(0, estado['cd_teleporte_apolo'] - 16.666)")
code = code.replace("estado['cd_habilidade_especial'] = max(0, estado['cd_habilidade_especial'] - 16)", "estado['cd_habilidade_especial'] = max(0, estado['cd_habilidade_especial'] - 16.666)")

with open('treino_acelerado_v3_percepcao_expandida.py', 'w', encoding='utf-8') as f:
    f.write(code)
