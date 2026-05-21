"""
Script para gerar GAME5_PLAYER.py a partir de GAME5.py
Remove toda a logica do Apolo e implementa controle manual do jogador
"""

import re

with open("GAME5.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Indices 0-based
output = []

# ============================================================
# PARTE 1: IMPORTS (reescritos, sem flask/torch/vfx_engine_apolo)
# ============================================================
new_imports = """\
import pygame
import subprocess
import sys
import random
import math
import time
import os
import json
from Tela_Cartas import tela_de_pausa
from Variaveis import *
from utils import *
import habilidade_boss as hb
import collections
from audio_manager import carregar_config_audio, aplicar_volume_som
from sistema_ratos_umbra import GerenciadorRatos

if __name__ == "__main__":
    pygame.init()
    memoria_umbra = hb.MemoriaEvolutivaUmbra()
"""
output.append(new_imports)

# ============================================================
# PARTE 2: Cache global e setup (linhas 29-127 no original, indices 28-126)
# ============================================================
for i in range(28, 127):
    line = lines[i]
    output.append(line)

# ============================================================
# PARTE 3: dados_ia + separador (pula Flask 134-212)
# ============================================================
for i in range(127, 133):
    output.append(lines[i])

# De 213 ate 319 (funcoes auxiliares, antes de atualizar_posicao)
for i in range(212, 320):
    line = lines[i]
    # Remove apolo references no quit handler do tela_upgrade_aureas
    if "'apolo' in globals()" in line and 'encerrar' in line:
        continue
    if 'apolo.encerrar' in line:
        continue
    output.append(line)

# ============================================================
# PARTE 3b: atualizar_posicao_personagem REESCRITA (manual player)
# ============================================================
new_movement = """\

    #####################################################################CONTROLE DO JOGADOR######################################################################################################
    def atualizar_posicao_personagem(keys, joystick):
        global pos_x_personagem, pos_y_personagem, direcao_atual, ultima_tecla_movimento
        global movimento_pressionado, cooldown_dash, distancia_dash, tempo_ultimo_dash, teleporte_duration
        global hitbox_boss5, estado_atual_ia

        dx, dy = 0, 0
        direcao_atual = 'stop'
    
        tempo_agora = pygame.time.get_ticks()
        tempo_fim_stun_ia = estado_atual_ia.get('fim_stun', 0) if 'estado_atual_ia' in globals() else 0
        atordoado = tempo_agora < tempo_fim_stun_ia

        # ---- TECLADO ----
        if keys[config_teclas["Mover para direita"]]: dx, ultima_tecla_movimento = 1, 'right'
        elif keys[config_teclas["Mover para esquerda"]]: dx, ultima_tecla_movimento = -1, 'left'
        if keys[config_teclas["Mover para cima"]]: dy, ultima_tecla_movimento = -1, 'up'
        elif keys[config_teclas["Mover para baixo"]]: dy, ultima_tecla_movimento = 1, 'down'

        # ---- JOYSTICK ----
        if joystick:
            eixo_x = joystick.get_axis(0)
            eixo_y = joystick.get_axis(1)
            if abs(eixo_x) > 0.3:
                dx = 1 if eixo_x > 0 else -1
                ultima_tecla_movimento = 'right' if eixo_x > 0 else 'left'
            if abs(eixo_y) > 0.3:
                dy = 1 if eixo_y > 0 else -1
                ultima_tecla_movimento = 'down' if eixo_y > 0 else 'up'

        if dx != 0 or dy != 0:
            movimento_pressionado = True
            direcao_atual = ultima_tecla_movimento
        
            # Normalização de movimento diagonal
            if dx != 0 and dy != 0:
                fator_normalizacao = 0.7071
                pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                             pos_x_personagem + dx * velocidade_personagem * fator_normalizacao))
                pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                             pos_y_personagem + dy * velocidade_personagem * fator_normalizacao))
            else:
                pos_x_personagem = max(0, min(largura_mapa - largura_personagem, 
                                             pos_x_personagem + dx * velocidade_personagem))
                pos_y_personagem = max(0, min(altura_mapa - altura_personagem, 
                                             pos_y_personagem + dy * velocidade_personagem))

        # ---- DASH/TELEPORTE ----
        dash_teclado = keys[config_teclas["Teleporte"]]
        dash_joystick = joystick and joystick.get_button(4) if joystick else False
        
        if (dash_teclado or dash_joystick) and cooldown_dash == False and atordoado == False:
            Som_portal.play()
            
            # Animação de teletransporte (plasma procedural)
            animar_teleporte_plasma(tela, mapa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, teleporte_duration // 2, ultima_tecla_movimento, distancia_dash, largura_mapa, altura_mapa)
            tela.blit(mapa, (pos_x_personagem, pos_y_personagem), pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem))


            if ultima_tecla_movimento == 'up': pos_y_personagem = max(0, pos_y_personagem - distancia_dash)
            elif ultima_tecla_movimento == 'down': pos_y_personagem = min(altura_mapa - altura_personagem, pos_y_personagem + distancia_dash)
            elif ultima_tecla_movimento == 'left': pos_x_personagem = max(0, pos_x_personagem - distancia_dash)
            elif ultima_tecla_movimento == 'right': pos_x_personagem = min(largura_mapa - largura_personagem, pos_x_personagem + distancia_dash)
        
            cooldown_dash = True
            tempo_ultimo_dash = pygame.time.get_ticks()

        if cooldown_dash and pygame.time.get_ticks() - tempo_ultimo_dash > tempo_cooldown_dash:
            cooldown_dash = False

        return direcao_atual
    ##########################################################################################################################################################################
"""
output.append(new_movement)

# Resto das funcoes auxiliares apos atualizar_posicao (424-637)
for i in range(423, 637):
    line = lines[i]
    if "'apolo' in globals()" in line:
        continue
    if "apolo.encerrar" in line:
        continue
    output.append(line)

# ============================================================
# PARTE 4: PULA AgenteApolo inteiro (linhas 638-1941)
# ============================================================
new_atexit = """
    import atexit, signal
    def _salvar_tudo_ao_sair():
        try:
            memoria_umbra.salvar()
        except Exception:
            pass
    atexit.register(_salvar_tudo_ao_sair)
    def _handler_ctrl_c(sig, frame):
        _salvar_tudo_ao_sair()
        sys.exit(0)
    signal.signal(signal.SIGINT, _handler_ctrl_c)

"""
output.append(new_atexit)

# ============================================================
# PARTE 5: Sistema de cartas (linhas 1943-2133)
# ============================================================
for i in range(1942, 2133):
    output.append(lines[i])

# ============================================================
# PARTE 6: LOOP PRINCIPAL (linhas 2134-3928)
# ============================================================

def is_apolo_line(s):
    """Verifica se a linha contem referencia direta ao apolo"""
    apolo_patterns = [
        'apolo.salvar_memoria', 'apolo.encerrar', 'apolo.pensar',
        'apolo.aplicar_recompensa', 'apolo.receber_dano_punitivo',
        'apolo.bonus_dopamina', 'apolo._orbe_coletada',
        'apolo.ultimo_estado_tensor', 'apolo.fila_estados',
        'apolo.acao_anterior', 'apolo.frames_no_laser',
        'apolo.safe_zone_grid', "hasattr(apolo",
        "'apolo' in globals()",
    ]
    return any(p in s for p in apolo_patterns)

def count_parens(s):
    """Conta parenteses abertos minus fechados"""
    return s.count('(') - s.count(')')

i = 2133
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    
    # --- REMOCOES CIRURGICAS ---
    
    # 1. Remove bloco if modo_ia_treino: (tudo dentro)
    if 'if modo_ia_treino:' in line:
        indent = len(line) - len(line.lstrip())
        i += 1
        while i < len(lines):
            next_line = lines[i]
            if next_line.strip() == '':
                i += 1
                continue
            next_indent = len(next_line) - len(next_line.lstrip())
            if next_indent <= indent:
                break
            i += 1
        continue
    
    # 2. Remove registrar_batalha(...) calls (multi-line)
    if 'registrar_batalha(' in stripped:
        paren_depth = count_parens(line)
        i += 1
        while i < len(lines) and paren_depth > 0:
            paren_depth += count_parens(lines[i])
            i += 1
        continue
    
    # 3. Remove recompensar_cartas() calls
    if 'recompensar_cartas(' in stripped:
        i += 1
        continue
    
    # 4. Remove linhas com referencia a apolo (incluindo multi-line)
    if is_apolo_line(stripped):
        # Verifica se eh um bloco multi-line (parenteses abertos)
        paren_depth = count_parens(line)
        i += 1
        while i < len(lines) and paren_depth > 0:
            paren_depth += count_parens(lines[i])
            i += 1
        continue
    
    # 5. Remove bloco "if 'apolo' in globals()..."
    if "'apolo' in globals()" in stripped:
        indent = len(line) - len(line.lstrip())
        i += 1
        while i < len(lines):
            next_line = lines[i]
            if next_line.strip() == '':
                i += 1
                continue
            next_indent = len(next_line) - len(next_line.lstrip())
            if next_indent <= indent:
                break
            i += 1
        continue
    
    # 6. Remove keys[pygame.K_t] Apolo teleporte trigger
    if "keys[pygame.K_t]" in stripped and "fase_tele" in stripped:
        indent = len(line) - len(line.lstrip())
        i += 1
        while i < len(lines):
            next_line = lines[i]
            if next_line.strip() == '':
                break
            next_indent = len(next_line) - len(next_line.lstrip())
            if next_indent <= indent and next_line.strip():
                break
            i += 1
        continue
    
    # 7. Remove "A tecla V foi removida" comment
    if "A tecla V foi removida" in stripped:
        i += 1
        continue
    
    # 8. Remove Apolo train comment lines
    if stripped.startswith('# Apolo aprende') or stripped.startswith('# Punição para Apolo'):
        i += 1
        continue
    
    # 9. Remove erros_player_contagem increment (Apolo punishment)
    if 'erros_player_contagem' in stripped and '+=' in stripped:
        i += 1
        continue
    
    # --- SUBSTITUICOES ---
    
    # A. subprocess.Popen GAME5.py -> Game_Over.py
    if 'subprocess.Popen' in line and 'GAME5.py' in line:
        line = line.replace('GAME5.py', 'Game_Over.py')
    
    # B. os._exit(0) -> sys.exit(0) 
    if 'os._exit(0)' in stripped:
        line = line.replace('os._exit(0)', 'sys.exit(0)')
    
    # C. vfx_apolo references
    if 'vfx_apolo.' in line:
        indent_str = line[:len(line) - len(line.lstrip())]
        if 'renderizar_plasma_apolo' in line:
            output.append(indent_str + 'pygame.draw.circle(tela, (255, 120, 0), disparo["rect"].center, 8)\n')
            output.append(indent_str + 'pygame.draw.circle(tela, (255, 255, 100), disparo["rect"].center, 4)\n')
            i += 1
            continue
        elif 'criar_impacto_fragmentado' in line:
            output.append(indent_str + '# Impacto visual (simplificado)\n')
            i += 1
            continue
        elif 'atualizar_e_desenhar' in line:
            output.append(indent_str + 'pass  # VFX update (simplificado)\n')
            i += 1
            continue
        elif 'mascara_furos' in line:
            line = line.replace('vfx_apolo.mascara_furos', '_mascara_furos_cache')
            if "hasattr(vfx_apolo, 'mascara_furos')" in line:
                line = line.replace("hasattr(vfx_apolo, 'mascara_furos')", "'_mascara_furos_cache' in locals()")
    
    # D. Handle hasattr(vfx_apolo...) in conditions
    if "hasattr(vfx_apolo" in line:
        line = line.replace("hasattr(vfx_apolo, 'mascara_furos')", "'_mascara_furos_cache' in locals()")
        line = line.replace('vfx_apolo.mascara_furos', '_mascara_furos_cache')
    
    # E. Remove miasma personagem doente skin check that refs estado_atual_ia before definition
    # (keep it - it's fine, estado_atual_ia is defined earlier)
    
    output.append(line)
    i += 1

# Escreve o arquivo final
with open("GAME5_PLAYER.py", "w", encoding="utf-8") as f:
    f.writelines(output)

print(f"GAME5_PLAYER.py gerado com sucesso! ({len(output)} blocos)")
