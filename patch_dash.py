import re

with open('habilidade_boss.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. DQN INITS (18 inputs, 30 outputs)
code = code.replace('self.input_size = 16', 'self.input_size = 18')
acoes_velhas = """        self.acoes_base = [
            "FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR", "ATAQUE", "SIFON", "TELEPORTE",
            "TRANSMUTAR_VORTICE", "TRANSMUTAR_GRAVIDADE", "TRANSMUTAR_NECROSE", 
            "TRANSMUTAR_RESSONANCIA", "TRANSMUTAR_HEMORRAGIA", "TRANSMUTAR_ATRITO", 
            "TRANSMUTAR_RASTRO", "VORTICE", "PRISAO", "MIASMA", "DESCARGA_ELETRICA", 
            "PRAGA_RATOS", "LASER_SOBRECARGA", "CAMINHO_ESPINHOS", "NENHUMA"
        ]"""
acoes_novas = """        self.acoes_base = [
            "FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR", "ATAQUE", "SIFON", "TELEPORTE",
            "TRANSMUTAR_VORTICE", "TRANSMUTAR_GRAVIDADE", "TRANSMUTAR_NECROSE", 
            "TRANSMUTAR_RESSONANCIA", "TRANSMUTAR_HEMORRAGIA", "TRANSMUTAR_ATRITO", 
            "TRANSMUTAR_RASTRO", "VORTICE", "PRISAO", "MIASMA", "DESCARGA_ELETRICA", 
            "PRAGA_RATOS", "LASER_SOBRECARGA", "CAMINHO_ESPINHOS", "NENHUMA",
            "DASH_C", "DASH_B", "DASH_E", "DASH_D", "DASH_CE", "DASH_CD", "DASH_BE", "DASH_BD"
        ]"""
code = code.replace(acoes_velhas, acoes_novas)

# 2. DISCRETIZAR ESTADO (Adicionar ameaca_x, ameaca_y)
# Replace function signature and body up to features array
sig_antigo = """    def discretizar_estado(self, vida_perc, dist_player, sob_fogo, historico_player, mapa_atual="Fase_Base", player_pos=None, boss_pos=None, armadilhas=None):"""
sig_novo = """    def discretizar_estado(self, vida_perc, dist_player, sob_fogo, historico_player, mapa_atual="Fase_Base", player_pos=None, boss_pos=None, armadilhas=None, ameaca_vec=(0.0, 0.0)):"""
code = code.replace(sig_antigo, sig_novo)

code = code.replace("features = [feat_vida, feat_dist, feat_fogo, feat_vx, feat_vy, dx, dy] + feat_armadilhas + [map_val]",
                    "features = [feat_vida, feat_dist, feat_fogo, feat_vx, feat_vy, dx, dy] + feat_armadilhas + [map_val, ameaca_vec[0], ameaca_vec[1]]")

# 3. REESCREVER MOVIMENTACAO_INTELIGENTE_UMBRA INTEIRO (Do def até return)
movimento_antigo = re.search(r'def movimentacao_inteligente_umbra.*?return \(nx, ny\), "GENERATIVE_MOVE"', code, re.DOTALL).group(0)

novo_movimento = """def movimentacao_inteligente_umbra(agora, boss_pos, player_pos, disparos, estado_mov, dados_player, memoria, historico_player):
    if estado_mov.get('parede_ativa'):
        estado_mov['vel_x'], estado_mov['vel_y'] = 0, 0
        return estado_mov.get('centro_mapa', (680, 384)), "SIFON_STASIS"
    if estado_mov.get('laser_ativo'):
        estado_mov['vel_x'], estado_mov['vel_y'] = 0, 0
        return (boss_pos[0], boss_pos[1]), "LASER_STASIS"

    import math, random
    bx, by = boss_pos[0], boss_pos[1]
    px, py = player_pos[0], player_pos[1]
    dist_p = math.hypot(bx - px, by - py)

    # O PROTOCOLO DE DASH: Se estiver em meio a um Dash, trava e impulsiona
    if agora - estado_mov.get('tempo_inicio_dash', 0) < 250:
        nx = max(50, min(1200, bx + estado_mov['dash_vx']))
        ny = max(50, min(700, by + estado_mov['dash_vy']))
        return (nx, ny), "DASHING"
    
    # Fim do Dash: Verifica se tomou dano durante. Se n tomou mas teve ameaca, +BUFF!
    if estado_mov.get('dash_ativo'):
        estado_mov['dash_ativo'] = False
        dano_sofrido = estado_mov.get('dano_recente', 0) > 0 # Precisa injetar dano_recente no GAME5!! 
        # GAME5 tem q atualizar isso quando a boss toma tiro.
        
        if not estado_mov.get('tomou_tiro_no_dash', False):
            if estado_mov.get('dash_ameaca', False):
                # RECOMPENSA! ESQUIVA PERFEITA
                estado_mov['acumulo_buff'] = min(5, estado_mov.get('acumulo_buff', 0) + 1)
                estado_mov['ultimo_buff_tempo'] = agora
                memoria.treinar(10.0, prioridade=True)
            else:
                memoria.treinar(-1.0) # dash a toa
        else:
            # ERRO FATAL: TOMOU TIRO
            estado_mov['acumulo_buff'] = 0
            memoria.treinar(-15.0, prioridade=True)
            
        estado_mov['tomou_tiro_no_dash'] = False

    # Processa Dreno do Buff
    buff_stacks = estado_mov.get('acumulo_buff', 0)
    if agora - estado_mov.get('ultimo_buff_tempo', 0) > 6000:
        buff_stacks = 0
        estado_mov['acumulo_buff'] = 0

    speed_mult = 1.0 + (buff_stacks * 0.2) # Multiplicador ate 2.0x
    VEL_MAX = 3.0 * speed_mult
    AGILIDADE = 0.3 * speed_mult
    RAIO_SEGURANCA = 340

    # PROTOCOLO DE VISÃO DE BALA
    tiro_ameaca = None
    ameaca_x, ameaca_y = 0.0, 0.0
    for d in disparos:
        dx_tiro = bx - d["rect"].centerx
        vx_tiro = math.cos(d["angulo"])
        if (dx_tiro > 0 and vx_tiro > 0) or (dx_tiro < 0 and vx_tiro < 0):
            dist_h = math.hypot(d["rect"].centerx - bx, d["rect"].centery - by)
            if dist_h < 400:
                tiro_ameaca = d
                ameaca_x = math.cos(d["angulo"])
                ameaca_y = math.sin(d["angulo"])
                break

    vida_perc = dados_player['vida_atual'] / dados_player['vida_max']
    sob_fogo = 1.0 if tiro_ameaca else 0.0
    estado_atual = memoria.discretizar_estado(vida_perc, dist_p, sob_fogo, historico_player, dados_player.get('mapa_atual', 'Fase_Base'), player_pos, boss_pos, estado_mov, ameaca_vec=(ameaca_x, ameaca_y))
    
    estrategias = ["FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR", 
                   "DASH_C", "DASH_B", "DASH_E", "DASH_D", "DASH_CE", "DASH_CD", "DASH_BE", "DASH_BD"]
    decisao = memoria.decidir(estado_atual, estrategias)

    # EXECUCAO DE DASH (Se decidido)
    if "DASH" in decisao and agora - estado_mov.get('ultimo_dash_cd', 0) > 1500:
        ang_dash = 0
        if decisao == "DASH_C": ang_dash = -math.pi/2
        elif decisao == "DASH_B": ang_dash = math.pi/2
        elif decisao == "DASH_E": ang_dash = math.pi
        elif decisao == "DASH_D": ang_dash = 0
        elif decisao == "DASH_CE": ang_dash = -math.pi * 0.75
        elif decisao == "DASH_CD": ang_dash = -math.pi * 0.25
        elif decisao == "DASH_BE": ang_dash = math.pi * 0.75
        elif decisao == "DASH_BD": ang_dash = math.pi * 0.25
        
        estado_mov['tempo_inicio_dash'] = agora
        estado_mov['ultimo_dash_cd'] = agora
        estado_mov['dash_vx'] = math.cos(ang_dash) * 18.0
        estado_mov['dash_vy'] = math.sin(ang_dash) * 18.0
        estado_mov['dash_ativo'] = True
        estado_mov['tomou_tiro_no_dash'] = False
        estado_mov['dash_ameaca'] = True if tiro_ameaca else False
        
        return (bx + estado_mov['dash_vx'], by + estado_mov['dash_vy']), "DASHING"

    # MOVIMENTO PADRAO (Se chegou aqui n deu dash)
    if decisao == "FUGIR":
        ang_fuga = math.atan2(by - py, bx - px)
        alvo_x, alvo_y = bx + math.cos(ang_fuga) * 600, by + math.sin(ang_fuga) * 600
    elif decisao == "INTERCEPTAR":
        alvo_x = px + (px - bx) * 0.3; alvo_y = py + (py - by) * 0.3
    elif decisao == "ORBITAR":
        ang = math.atan2(by - py, bx - px) + 0.7
        alvo_x, alvo_y = px + math.cos(ang) * 450, py + math.sin(ang) * 450
    else: 
        ang = math.atan2(by - py, bx - px)
        alvo_x, alvo_y = px + math.cos(ang) * 300, py + math.sin(ang) * 300

    estado_mov['alvo_ia'] = (max(100, min(1260, alvo_x)), max(100, min(660, alvo_y)))
    
    dx_a, dy_a = estado_mov['alvo_ia'][0] - bx, estado_mov['alvo_ia'][1] - by
    mag_a = math.hypot(dx_a, dy_a)
    vec_alvo_x = (dx_a / mag_a) if mag_a > 0 else 0
    vec_alvo_y = (dy_a / mag_a) if mag_a > 0 else 0

    rx, ry = bx - px, by - py
    dist_r = math.hypot(rx, ry)
    f_rep_x = f_rep_y = 0
    if dist_r < RAIO_SEGURANCA:
        f_rep_x, f_rep_y = (rx/dist_r) * 1.5, (ry/dist_r) * 1.5

    v_desejada_x = (vec_alvo_x + f_rep_x) * VEL_MAX
    v_desejada_y = (vec_alvo_y + f_rep_y) * VEL_MAX
    vx = estado_mov.get('vel_x', 0)
    vy = estado_mov.get('vel_y', 0)
    vx += (v_desejada_x - vx) * AGILIDADE
    vy += (v_desejada_y - vy) * AGILIDADE
    estado_mov['vel_x'], estado_mov['vel_y'] = vx, vy

    nx = max(50, min(1200, bx + vx)) 
    ny = max(50, min(700, by + vy))

    return (nx, ny), "GENERATIVE_MOVE"
"""
code = code.replace(movimento_antigo, novo_movimento)

with open('habilidade_boss.py', 'w', encoding='utf-8') as f:
    f.write(code)
