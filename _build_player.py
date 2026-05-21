"""
Script dinâmico e robusto para gerar GAME5_PLAYER.py a partir de GAME5.py
Remove toda a lógica do Apolo AI e do Flask, adaptando o jogo para controle manual do jogador.
"""

import sys
import os

def build_player():
    if not os.path.exists("GAME5.py"):
        print("Erro: GAME5.py não encontrado no diretório atual.")
        sys.exit(1)

    with open("GAME5.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    def find_line(search_str, start_idx=0):
        for idx in range(start_idx, len(lines)):
            if search_str in lines[idx]:
                return idx
        return -1

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

    # Localizar índices dinâmicos
    if_main_idx = find_line('if __name__ == "__main__":')
    if if_main_idx == -1:
        print("Erro: Bloco main não encontrado em GAME5.py")
        sys.exit(1)

    setup_start = find_line("CACHE GLOBAL DE PERFORMANCE", if_main_idx)
    setup_end = find_line("app = Flask(__name__)", setup_start)

    if setup_start == -1 or setup_end == -1:
        print("Erro: Setup global ou Flask não encontrados em GAME5.py")
        sys.exit(1)

    # ============================================================
    # PARTE 2: Cache global e setup (do CACHE GLOBAL até antes do Flask)
    # ============================================================
    for i in range(setup_start - 1, setup_end):
        output.append(lines[i])

    # ============================================================
    # PARTE 3: Separador de dados_ia (copia a declaração de dados_ia_umbra)
    # ============================================================
    dados_ia_idx = find_line('dados_ia_umbra = {"estado": "Aguardando..."', setup_end)
    if dados_ia_idx != -1:
        output.append(lines[dados_ia_idx])
        output.append("\n")

    # ============================================================
    # PARTE 4: Funções Auxiliares 1 (gerar_posicao_aleatoria até antes de atualizar_posicao_personagem)
    # ============================================================
    helper1_start = find_line("def gerar_posicao_aleatoria", setup_end)
    helper1_end = find_line("def atualizar_posicao_personagem", helper1_start)

    if helper1_start == -1 or helper1_end == -1:
        print("Erro: Funções auxiliares 1 não encontradas em GAME5.py")
        sys.exit(1)

    for i in range(helper1_start, helper1_end):
        line = lines[i]
        # Remove referências de apolo
        if "'apolo' in globals()" in line and 'encerrar' in line:
            continue
        if 'apolo.encerrar' in line:
            continue
        output.append(line)

    # ============================================================
    # PARTE 5: atualizar_posicao_personagem REESCRITA (manual player)
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
    #####################################################################
"""
    output.append(new_movement)

    # ============================================================
    # PARTE 6: Funções Auxiliares 2 (criar_disparo até antes de AgenteApolo)
    # ============================================================
    helper2_start = find_line("def criar_disparo", helper1_end)
    helper2_end = find_line("class AgenteApolo", helper2_start)

    if helper2_start == -1 or helper2_end == -1:
        print("Erro: Funções auxiliares 2 não encontradas em GAME5.py")
        sys.exit(1)

    for i in range(helper2_start, helper2_end):
        line = lines[i]
        # Remove referências de apolo
        if "'apolo' in globals()" in line and 'encerrar' in line:
            continue
        if 'apolo.encerrar' in line:
            continue
        output.append(line)

    # ============================================================
    # PARTE 7: Pula AgenteApolo e escreve o novo quit handler
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
    # PARTE 8: Sistema de Cartas (do Núcleo de Aprendizado de Cartas até antes do Loop Principal)
    # ============================================================
    cards_start = find_line("cartas_compradas_apolo_global = []", helper2_end)
    # Procuramos o início real do bloco de comentários ou imports do núcleo de cartas
    nucleus_idx = find_line("NÚCLEO DE APRENDIZADO DE CARTAS", helper2_end)
    if nucleus_idx != -1 and nucleus_idx < cards_start:
        cards_start_real = find_line("import collections", nucleus_idx)
        if cards_start_real == -1 or cards_start_real > cards_start:
            cards_start_real = cards_start
    else:
        cards_start_real = cards_start

    main_loop_start = find_line("running = True", cards_start)

    if cards_start == -1 or main_loop_start == -1:
        print("Erro: Bloco de cartas ou início do loop não encontrados em GAME5.py")
        sys.exit(1)

    for i in range(cards_start_real, main_loop_start):
        output.append(lines[i])

    # ============================================================
    # PARTE 9: LOOP PRINCIPAL (copia com filtros cirúrgicos de IA)
    # ============================================================

    def is_apolo_line(s):
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
        return s.count('(') - s.count(')')

    i = main_loop_start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # --- REMOÇÕES CIRÚRGICAS ---
        
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

        # 2. Remove bloco "if 'apolo' in globals()..." (IMPORTANTE: deve vir antes de is_apolo_line!)
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
        
        # 3. Remove keys[pygame.K_t] Apolo teleporte trigger (IMPORTANTE: deve vir antes de is_apolo_line!)
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

        # 4. Remove blocos compostos (if/elif/for/while) que referenciam o apolo por completo (IMPORTANTE: evita blocos filhos órfãos!)
        if ('if ' in stripped or 'elif ' in stripped or 'for ' in stripped or 'while ' in stripped) and is_apolo_line(stripped):
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

        # 5. Remove registrar_batalha(...) calls (multi-line) e substitui por 'pass' para evitar erro de indentação
        if 'registrar_batalha(' in stripped:
            paren_depth = count_parens(line)
            indent_str = line[:len(line) - len(line.lstrip())]
            output.append(indent_str + 'pass\n')
            i += 1
            while i < len(lines) and paren_depth > 0:
                paren_depth += count_parens(lines[i])
                i += 1
            continue
        
        # 6. Remove recompensar_cartas() calls
        if 'recompensar_cartas(' in stripped:
            indent_str = line[:len(line) - len(line.lstrip())]
            output.append(indent_str + 'pass\n')
            i += 1
            continue
        
        # 7. Remove linhas com referencia a apolo (incluindo multi-line) e coloca 'pass'
        if is_apolo_line(stripped):
            paren_depth = count_parens(line)
            indent_str = line[:len(line) - len(line.lstrip())]
            output.append(indent_str + 'pass\n')
            i += 1
            while i < len(lines) and paren_depth > 0:
                paren_depth += count_parens(lines[i])
                i += 1
            continue
        
        # 8. Remove "A tecla V foi removida" comment
        if "A tecla V foi removida" in stripped:
            i += 1
            continue
        
        # 9. Remove Apolo train comment lines
        if stripped.startswith('# Apolo aprende') or stripped.startswith('# Punição para Apolo'):
            i += 1
            continue
        
        # 10. Remove erros_player_contagem increment (Apolo punishment)
        if 'erros_player_contagem' in stripped and '+=' in stripped:
            i += 1
            continue
        
        # --- SUBSTITUIÇÕES ---
        
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
        
        output.append(line)
        i += 1

    # Escreve o arquivo final
    with open("GAME5_PLAYER.py", "w", encoding="utf-8") as f:
        f.writelines(output)

    print(f"GAME5_PLAYER.py gerado com sucesso! ({len(output)} blocos)")

if __name__ == "__main__":
    build_player()
