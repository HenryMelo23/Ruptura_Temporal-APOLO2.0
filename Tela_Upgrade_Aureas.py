# -*- coding: utf-8 -*-
import Caminhos
import pygame
import os
import sys
import math
import random
import json

from utils import carregar_upgrade_aureas, salvar_upgrade_aureas
from dados_aureas import AUREAS_DADOS
import ui_helpers

def tela_upgrade_aureas(tela, fonte, moedas_disponiveis):
    # Setup
    clock = pygame.time.Clock()
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(False)
    fontes = ui_helpers.carregar_fontes()
    
    fonte_titulo_large = ui_helpers.get_cached_font(fontes["titulo_path"], 56)
    fonte_titulo_sub = ui_helpers.get_cached_font(fontes["texto_path"], 28)
    fonte_card_name = ui_helpers.get_cached_font(fontes["texto_path"], 30)
    fonte_card_level = ui_helpers.get_cached_font(fontes["texto_path"], 24)
    fonte_panel_title = ui_helpers.get_cached_font(fontes["texto_path"], 36)
    fonte_panel_label = ui_helpers.get_cached_font(fontes["texto_path"], 26)
    fonte_panel_text = ui_helpers.get_cached_font(fontes["texto_path"], 22)
    fonte_panel_lore = ui_helpers.get_cached_font(fontes["texto_path"], 18)
    
    # Pre-carregar upgrades
    upgrades_caminho = "saves/aureas_upgrade.json"
    upgrades = carregar_upgrade_aureas(upgrades_caminho)
    
    # Pre-carregar imagens
    imagens_aurea = ui_helpers.carregar_imagens_aureas(AUREAS_DADOS, 120, 140)
        
    custos_niveis = {0: 1, 1: 2, 2: 4, 3: 6, 4: 10, 5: 9999}
    max_nivel = 5
    
    # Estado da tela
    selecionado = 0
    modo_interacao = "teclado"
    cor_fundo_atual = [15, 15, 20]
    
    # Partículas
    particulas_ambiente = []
    particulas_orbitais = []
    explosoes = []
    textos_flutuantes = []
    
    # Feedbacks de erro / sucesso
    shake_amount = 0
    custo_erro_timer = 0
    t_confirm_scale = 0.0
    
    # Tentar carregar som de confirmação
    som_confirm = None
    try:
        som_confirm = pygame.mixer.Sound("Sounds/Estalo.mp3")
        som_confirm.set_volume(0.3)
    except Exception:
        pass
        
    running_menu = True
    global_time = 0
    
    # Posições interpoladas para o carrossel
    x_offset_lerp = 0.0
    
    while running_menu:
        global_time += 1
        largura_tela, altura_tela = tela.get_size()
        
        # DEFINIÇÃO DE LAYOUT SEGURO (pygame.Rect)
        header_margin = 80
        header_rect = pygame.Rect(header_margin, 30, largura_tela - 2 * header_margin, 80)
        
        # Fragment Panel Rect
        moedas_painel_w = 260
        moedas_painel_h = 50
        moedas_painel_x = largura_tela - moedas_painel_w - header_margin
        moedas_painel_y = 35
        moedas_rect = pygame.Rect(moedas_painel_x, moedas_painel_y, moedas_painel_w, moedas_painel_h)
        
        # Limite máximo de largura do título para evitar invasão do painel de moedas
        max_titulo_w = moedas_painel_x - header_margin - 30
        
        # Carousel Rect
        carousel_rect = pygame.Rect(0, 120, largura_tela, 280)
        centro_x = largura_tela // 2
        centro_y = carousel_rect.centery
        
        # Bottom Info Panel Rect (Glassmorphic)
        panel_w = max(600, largura_tela - 160)
        panel_h = 300
        panel_x = (largura_tela - panel_w) // 2
        panel_y = altura_tela - panel_h - 25
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        
        # Colunas do painel inferior
        left_col_rect = pygame.Rect(panel_rect.left + 35, panel_rect.top + 20, panel_rect.width // 2 - 70, panel_rect.height - 40)
        right_col_rect = pygame.Rect(panel_rect.left + panel_rect.width // 2 + 35, panel_rect.top + 20, panel_rect.width // 2 - 70, panel_rect.height - 40)
        
        # Sub-rects da coluna esquerda para segurança absoluta de textos
        left_name_rect = pygame.Rect(left_col_rect.left, left_col_rect.top, left_col_rect.width, 38)
        left_cat_rect = pygame.Rect(left_col_rect.left, left_col_rect.top + 38, left_col_rect.width, 30)
        left_desc_rect = pygame.Rect(left_col_rect.left, left_col_rect.top + 78, left_col_rect.width, 135)
        left_lore_rect = pygame.Rect(left_col_rect.left, left_col_rect.top + 222, left_col_rect.width, left_col_rect.height - 222)
        
        # Sub-rects da coluna direita
        right_eff_lbl_rect = pygame.Rect(right_col_rect.left, right_col_rect.top, right_col_rect.width, 28)
        right_eff_val_rect = pygame.Rect(right_col_rect.left, right_col_rect.top + 30, right_col_rect.width, 58)
        right_next_lbl_rect = pygame.Rect(right_col_rect.left, right_col_rect.top + 94, right_col_rect.width, 28)
        right_next_val_rect = pygame.Rect(right_col_rect.left, right_col_rect.top + 124, right_col_rect.width, 58)
        right_progress_rect = pygame.Rect(right_col_rect.left, right_col_rect.top + 190, right_col_rect.width, 12)
        right_cost_rect = pygame.Rect(right_col_rect.left, right_col_rect.top + 212, right_col_rect.width, 32)
        right_action_rect = pygame.Rect(right_col_rect.left, right_col_rect.top + 252, right_col_rect.width, 34)
        
        # Rodapé
        footer_rect = pygame.Rect(0, altura_tela - 22, largura_tela, 20)
        btn_voltar_rect = pygame.Rect(header_margin, altura_tela - 62, 130, 34)
        btn_evoluir_rect = right_action_rect.inflate(18, 8)
        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)

        rects_aureas = []
        for idx_aura in range(len(AUREAS_DADOS)):
            x_target = centro_x + idx_aura * 280 - x_offset_lerp
            distance_from_center = abs(x_target - centro_x)
            max_visible_dist = largura_tela // 2
            if distance_from_center > max_visible_dist:
                continue
            card_scale_evt = 1.3 + t_confirm_scale if idx_aura == selecionado else 0.85
            w_card_evt = int(140 * card_scale_evt)
            h_card_evt = int(185 * card_scale_evt)
            x_pos_evt = int(x_target - w_card_evt // 2)
            y_pos_evt = int(centro_y - h_card_evt // 2)
            rects_aureas.append((idx_aura, pygame.Rect(x_pos_evt, y_pos_evt, w_card_evt, h_card_evt)))

        # 1. Tratar eventos
        trigger_upgrade = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if event.key == pygame.K_ESCAPE:
                    pygame.event.clear()
                    return moedas_disponiveis
                elif event.key in [pygame.K_LEFT, pygame.K_a]:
                    selecionado = (selecionado - 1) % len(AUREAS_DADOS)
                elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                    selecionado = (selecionado + 1) % len(AUREAS_DADOS)
                elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    trigger_upgrade = True
            elif event.type == pygame.JOYBUTTONDOWN:
                modo_interacao = "teclado"
                if event.button in [1, 6]:  # B (1) or Back/Select (6)
                    pygame.event.clear()
                    return moedas_disponiveis
                elif event.button == 0:  # A (0)
                    trigger_upgrade = True
            elif event.type == pygame.JOYHATMOTION:
                modo_interacao = "teclado"
                dx, dy = event.value
                if dx < -0.5:
                    selecionado = (selecionado - 1) % len(AUREAS_DADOS)
                elif dx > 0.5:
                    selecionado = (selecionado + 1) % len(AUREAS_DADOS)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                modo_interacao = "mouse"
                pos_evento = ui_helpers.converter_pos_mouse_jogo(event.pos)
                if btn_voltar_rect.collidepoint(pos_evento):
                    pygame.event.clear()
                    return moedas_disponiveis
                clicou_card = False
                for idx_aura, rect_aura in rects_aureas:
                    if rect_aura.collidepoint(pos_evento):
                        if idx_aura > selecionado:
                            selecionado = min(selecionado + 1, len(AUREAS_DADOS) - 1)
                        elif idx_aura < selecionado:
                            selecionado = max(selecionado - 1, 0)
                        clicou_card = True
                        break
                if not clicou_card and btn_evoluir_rect.collidepoint(pos_evento):
                    trigger_upgrade = True

        if trigger_upgrade:
            # Executar upgrade
            aura_atual = AUREAS_DADOS[selecionado]
            nivel_atual = upgrades.get(aura_atual["id"], 0)
            custo = custos_niveis.get(nivel_atual, 9999)

            if nivel_atual >= max_nivel:
                # Já está no máximo
                shake_amount = 6
                custo_erro_timer = 20
            elif moedas_disponiveis >= custo:
                # Sucesso
                moedas_disponiveis -= custo
                upgrades[aura_atual["id"]] += 1

                # Salvar
                salvar_upgrade_aureas(upgrades_caminho, upgrades)
                try:
                    if os.path.exists("saves/atributos.json"):
                        with open("saves/atributos.json", "r") as f:
                            atributos = json.load(f)
                    else:
                        atributos = {}
                    atributos["moedas_totais"] = moedas_disponiveis
                    with open("saves/atributos.json", "w") as f:
                        json.dump(atributos, f, indent=4)
                except Exception:
                    pass

                # Audio
                if som_confirm:
                    som_confirm.play()

                # Feedbacks visuais
                t_confirm_scale = 1.35
                shake_amount = 0
                # Criar explosão de partículas
                for _ in range(60):
                    explosoes.append(ui_helpers.Particle(centro_x, centro_y, aura_atual["cor"], style=aura_atual["estilo"]))
                # Adicionar texto flutuante
                textos_flutuantes.append(
                    ui_helpers.FloatingText(centro_x, centro_y - 120, "NIVEL EXPANDIDO", aura_atual["cor"], fonte_panel_title)
                )
            else:
                # Erro de moedas
                shake_amount = 10
                custo_erro_timer = 30
                # Adicionar texto flutuante de erro
                textos_flutuantes.append(
                    ui_helpers.FloatingText(centro_x, centro_y - 120, "MOEDAS INSUFICIENTES", (255, 80, 80), fonte_card_name)
                )
                        
        # 2. Atualizar estado / interpolações
        aura_atual = AUREAS_DADOS[selecionado]
        nivel_atual = upgrades.get(aura_atual["id"], 0)
        
        # Interpolação de cor de fundo
        cor_fundo_alvo = [int(c * 0.4) for c in aura_atual["cor"]]
        for idx_c in range(3):
            cor_fundo_atual[idx_c] += (cor_fundo_alvo[idx_c] - cor_fundo_atual[idx_c]) * 0.06
            
        # Decaimento do shake
        offset_shake_x = 0
        offset_shake_y = 0
        if shake_amount > 0:
            offset_shake_x = random.randint(-shake_amount, shake_amount)
            offset_shake_y = random.randint(-shake_amount, shake_amount)
            shake_amount -= 1
            
        if custo_erro_timer > 0:
            custo_erro_timer -= 1
            
        if t_confirm_scale > 0.0:
            t_confirm_scale += (0.0 - t_confirm_scale) * 0.1
            
        # Atualizar interpolação de navegação
        target_offset = selecionado * 280
        x_offset_lerp += (target_offset - x_offset_lerp) * 0.12
        
        # Atualizar partículas ambiente
        if len(particulas_ambiente) < 40:
            particulas_ambiente.append(
                ui_helpers.Particle(random.randint(0, largura_tela), random.randint(0, altura_tela), aura_atual["cor"], style=aura_atual["estilo"])
            )
        for p in particulas_ambiente[:]:
            p.update()
            if p.life <= 0:
                particulas_ambiente.remove(p)
                
        # Atualizar partículas orbitais
        if len(particulas_orbitais) < 25:
            particulas_orbitais.append(
                ui_helpers.OrbitalParticle(centro_x, centro_y, aura_atual["cor"], style=aura_atual["estilo"])
            )
        for po in particulas_orbitais[:]:
            po.update(centro_x, centro_y)
            if po.life <= 0:
                particulas_orbitais.remove(po)
                
        # Atualizar explosões de compra
        for exp in explosoes[:]:
            exp.update()
            if exp.life <= 0:
                explosoes.remove(exp)
                
        # Atualizar textos flutuantes
        for tf in textos_flutuantes[:]:
            tf.update()
            if tf.life <= 0:
                textos_flutuantes.remove(tf)
                
        # Apply Screen Shake to whole coordinate offsets
        panel_rect_shaken = panel_rect.move(offset_shake_x, offset_shake_y)
        left_name_rect_shaken = left_name_rect.move(offset_shake_x, offset_shake_y)
        left_cat_rect_shaken = left_cat_rect.move(offset_shake_x, offset_shake_y)
        left_desc_rect_shaken = left_desc_rect.move(offset_shake_x, offset_shake_y)
        left_lore_rect_shaken = left_lore_rect.move(offset_shake_x, offset_shake_y)
        
        right_eff_lbl_rect_shaken = right_eff_lbl_rect.move(offset_shake_x, offset_shake_y)
        right_eff_val_rect_shaken = right_eff_val_rect.move(offset_shake_x, offset_shake_y)
        right_next_lbl_rect_shaken = right_next_lbl_rect.move(offset_shake_x, offset_shake_y)
        right_next_val_rect_shaken = right_next_val_rect.move(offset_shake_x, offset_shake_y)
        right_progress_rect_shaken = right_progress_rect.move(offset_shake_x, offset_shake_y)
        right_cost_rect_shaken = right_cost_rect.move(offset_shake_x, offset_shake_y)
        right_action_rect_shaken = right_action_rect.move(offset_shake_x, offset_shake_y)

        # 3. Renderização da tela
        tela.fill((int(cor_fundo_atual[0]), int(cor_fundo_atual[1]), int(cor_fundo_atual[2])))
        
        # Desenhar partículas ambiente
        for p in particulas_ambiente:
            p.draw(tela)
            
        # Efeito de energia pulsando atrás da áurea central
        glow_pulse = 1.0 + 0.1 * math.sin(global_time * 0.08)
        glow_radius = int(140 * glow_pulse)
        for r_offset in [0, 15, 30]:
            glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            alpha_val = int(35 / (1 + r_offset * 0.04))
            pygame.draw.circle(glow_surf, (aura_atual["cor"][0], aura_atual["cor"][1], aura_atual["cor"][2], alpha_val), (glow_radius, glow_radius), glow_radius - r_offset)
            tela.blit(glow_surf, (centro_x - glow_radius, centro_y - glow_radius))
            
        # Desenhar partículas orbitais
        for po in particulas_orbitais:
            po.draw(tela)
            
        # Desenhar cards do carrossel
        for i, d in enumerate(AUREAS_DADOS):
            # Calcular x relativo
            x_target = centro_x + i * 280 - x_offset_lerp
            
            # Fade out cards that are too far left or right (so they don't look broken when cut off)
            distance_from_center = abs(x_target - centro_x)
            max_visible_dist = largura_tela // 2
            if distance_from_center > max_visible_dist:
                continue # Do not draw cards that are offscreen
            
            if i == selecionado:
                card_scale = 1.3 + t_confirm_scale
                card_alpha = 255
            else:
                card_scale = 0.85
                # Fade card based on distance from center to make edge cards look natural
                card_alpha = int(110 * (1.0 - (distance_from_center / max_visible_dist)))
                if card_alpha < 0:
                    card_alpha = 0
                
            w_card = int(140 * card_scale)
            h_card = int(185 * card_scale)
            x_pos = int(x_target - w_card // 2) + offset_shake_x
            y_pos = int(centro_y - h_card // 2) + offset_shake_y
            
            # Painel do card
            card_surf = pygame.Surface((w_card, h_card), pygame.SRCALPHA)
            card_surf.fill((10, 8, 20, max(0, card_alpha - 20)))
            
            # Bordas neon
            borda_cor = d["cor"]
            b_alpha = card_alpha
            if i == selecionado:
                pulse_border = int(150 + 80 * math.sin(global_time * 0.12))
                b_color_with_alpha = (borda_cor[0], borda_cor[1], borda_cor[2], pulse_border)
                pygame.draw.rect(card_surf, b_color_with_alpha, (0, 0, w_card, h_card), width=3, border_radius=10)
                # Outer glow
                for k in range(1, 4):
                    pygame.draw.rect(card_surf, (borda_cor[0], borda_cor[1], borda_cor[2], int(50 / k)), 
                                     (-k, -k, w_card + k*2, h_card + k*2), width=1, border_radius=10 + k)
            else:
                b_color_with_alpha = (borda_cor[0], borda_cor[1], borda_cor[2], b_alpha // 2)
                pygame.draw.rect(card_surf, b_color_with_alpha, (0, 0, w_card, h_card), width=2, border_radius=8)
                
            # Imagem do card
            img_scaled = pygame.transform.scale(imagens_aurea[d["id"]], (int(100 * card_scale), int(120 * card_scale)))
            if card_alpha < 255:
                img_scaled.set_alpha(card_alpha)
            card_surf.blit(img_scaled, (w_card // 2 - img_scaled.get_width() // 2, 10))
            
            # Nome da aura no card
            txt_c_nome = fonte_card_name.render(d["nome"], True, (255, 255, 255))
            txt_c_nome_scaled = pygame.transform.scale(txt_c_nome, (int(txt_c_nome.get_width() * (card_scale * 0.75)), int(txt_c_nome.get_height() * (card_scale * 0.75))))
            if card_alpha < 255:
                txt_c_nome_scaled.set_alpha(card_alpha)
            card_surf.blit(txt_c_nome_scaled, (w_card // 2 - txt_c_nome_scaled.get_width() // 2, h_card - 45))
            
            # Nível da aura no card
            nv_val = upgrades.get(d["id"], 0)
            if nv_val >= max_nivel:
                txt_c_nv = fonte_card_level.render("MAX", True, (255, 215, 0))
            else:
                txt_c_nv = fonte_card_level.render(f"NV. {nv_val}", True, (200, 200, 200))
            txt_c_nv_scaled = pygame.transform.scale(txt_c_nv, (int(txt_c_nv.get_width() * (card_scale * 0.75)), int(txt_c_nv.get_height() * (card_scale * 0.75))))
            if card_alpha < 255:
                txt_c_nv_scaled.set_alpha(card_alpha)
            card_surf.blit(txt_c_nv_scaled, (w_card // 2 - txt_c_nv_scaled.get_width() // 2, h_card - 22))
            
            # Blit final do card
            tela.blit(card_surf, (x_pos, y_pos))
            
        # Desenhar explosões de compra
        for exp in explosoes:
            exp.draw(tela)
            
        # Desenhar textos flutuantes
        for tf in textos_flutuantes:
            tf.draw(tela)
            
        # 4. Painel de Informações inferior (Glassmorphic)
        ui_helpers.desenhar_painel_glassmorphic(tela, panel_rect_shaken, aura_atual["cor"])
        
        # TEXTOS DO PAINEL (Lado Esquerdo: Identidade)
        # Nome e Nível
        txt_p_titulo = fonte_panel_title.render(f"{aura_atual['nome']} - Nivel {nivel_atual}", True, (255, 255, 255))
        tela.blit(txt_p_titulo, (left_name_rect_shaken.left, left_name_rect_shaken.top))
        
        # Categoria
        txt_p_cat = fonte_panel_label.render(aura_atual["categoria"], True, aura_atual["cor"])
        tela.blit(txt_p_cat, (left_cat_rect_shaken.left, left_cat_rect_shaken.top))
        
        # Descrição wrapped
        ui_helpers.desenhar_texto_wrap(tela, aura_atual["descricao"], left_desc_rect_shaken, fonte_panel_text, (200, 200, 210))
            
        # Lore
        ui_helpers.desenhar_texto_wrap(tela, aura_atual["lore"], left_lore_rect_shaken, fonte_panel_lore, (130, 130, 140))
            
        # TEXTOS DO PAINEL (Lado Direito: Evolução)
        # Benefício Atual
        txt_p_atual_lbl = fonte_panel_label.render("Efeito Atual:", True, (180, 180, 190))
        tela.blit(txt_p_atual_lbl, (right_eff_lbl_rect_shaken.left, right_eff_lbl_rect_shaken.top))
        
        ui_helpers.desenhar_texto_wrap(tela, aura_atual["beneficios"].get(nivel_atual, ""), right_eff_val_rect_shaken, fonte_panel_text, (255, 255, 255))
        
        # Benefício Próximo Nível
        txt_p_prox_lbl = fonte_panel_label.render("Proximo Nivel:", True, (180, 180, 190))
        tela.blit(txt_p_prox_lbl, (right_next_lbl_rect_shaken.left, right_next_lbl_rect_shaken.top))
        
        if nivel_atual >= max_nivel:
            txt_p_prox_eff = "Nivel Maximo Atingido"
            cor_prox_eff = (255, 215, 0)
        else:
            txt_p_prox_eff = aura_atual["beneficios"].get(nivel_atual + 1, "")
            cor_prox_eff = (200, 200, 200)
        ui_helpers.desenhar_texto_wrap(tela, txt_p_prox_eff, right_next_val_rect_shaken, fonte_panel_text, cor_prox_eff)
        
        # Barra de Progresso
        ui_helpers.desenhar_barra_progresso(tela, right_progress_rect_shaken, nivel_atual, max_nivel, aura_atual["cor"])
            
        # Custo / Compra
        if nivel_atual >= max_nivel:
            txt_custo_str = "ESTABILIZADA"
            cor_custo = (255, 215, 0)
        else:
            custo_val = custos_niveis.get(nivel_atual, 1)
            txt_custo_str = f"Custo: {custo_val} Moedas"
            if moedas_disponiveis >= custo_val:
                cor_custo = (0, 255, 204)
            else:
                cor_custo = (255, 80, 80)
                
        # Piscar vermelho no erro
        if custo_erro_timer > 0 and nivel_atual < max_nivel:
            cor_custo = (255, 0, 0)
            
        txt_custo = fonte_panel_label.render(txt_custo_str, True, cor_custo)
        tela.blit(txt_custo, (right_cost_rect_shaken.left, right_cost_rect_shaken.top))
        
        # Prompt de ação
        if nivel_atual >= max_nivel:
            prompt_str = "AUREA DOMINADA"
            cor_prompt = (255, 215, 0)
        else:
            prompt_str = "CLIQUE PARA EVOLUIR"
            cor_prompt = (255, 255, 255)

        hover_action = modo_interacao == "mouse" and right_action_rect_shaken.collidepoint(mx, my)
        rect_action_btn = right_action_rect_shaken.inflate(18, 8)
        pygame.draw.rect(tela, (18, 18, 26), rect_action_btn, border_radius=6)
        pygame.draw.rect(tela, aura_atual["cor"] if hover_action else (80, 80, 90), rect_action_btn, width=2 if hover_action else 1, border_radius=6)
        txt_prompt = fonte_panel_text.render(prompt_str, True, cor_prompt)
        tela.blit(txt_prompt, (
            rect_action_btn.centerx - txt_prompt.get_width() // 2,
            rect_action_btn.centery - txt_prompt.get_height() // 2
        ))

        # 5. Top Bar (Título e Moedas)
        titulo_rect = pygame.Rect(header_rect.left, header_rect.top, max_titulo_w, 40)
        ui_helpers.renderizar_titulo(tela, "NUCLEO DE EVOLUCAO TEMPORAL", max_titulo_w, titulo_rect, fontes["titulo_path"], 52, (255, 255, 255))

        t_sub = fonte_titulo_sub.render("Estabilize as moedas de energia para expandir sua linhagem temporal", True, (150, 150, 160))
        tela.blit(t_sub, (header_rect.left, header_rect.top + 45))

        # Moedas no topo direito
        ui_helpers.desenhar_painel_fragmentos(tela, moedas_rect, moedas_disponiveis, fonte_card_name, (0, 255, 204))
        
        hover_voltar = modo_interacao == "mouse" and btn_voltar_rect.collidepoint(mx, my)
        pygame.draw.rect(tela, (18, 18, 26), btn_voltar_rect, border_radius=6)
        pygame.draw.rect(tela, aura_atual["cor"] if hover_voltar else (80, 80, 90), btn_voltar_rect, width=2 if hover_voltar else 1, border_radius=6)
        txt_voltar = fonte_panel_lore.render("VOLTAR", True, (255, 255, 255))
        tela.blit(txt_voltar, (
            btn_voltar_rect.centerx - txt_voltar.get_width() // 2,
            btn_voltar_rect.centery - txt_voltar.get_height() // 2
        ))

        # Barra inferior de instrução
        txt_barra_inf = fonte_panel_lore.render("Clique nas laterais para navegar  |  Clique em Evoluir para comprar  |  A/D e ESC funcionam", True, (130, 130, 140))
        tela.blit(txt_barra_inf, (footer_rect.left + footer_rect.width // 2 - txt_barra_inf.get_width() // 2, footer_rect.top))
        
        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)
        
    return moedas_disponiveis
