import Caminhos
import pygame
import math
import random
import json
import lacerante_manifestacao
import prismatica_manifestacao
import retornante_manifestacao
import parasitica_manifestacao
import condutora_manifestacao

def calcular_corrente_eletrica_grafo(origem_inimigo, inimigos_comum):
    """
    Realiza uma Busca em Largura (BFS) para criar a árvore de choque.
    Retorna os vizinhos afetados e os links com seus respectivos 'níveis' (depth),
    permitindo que o raio pule progressivamente.
    """
    visited = {id(origem_inimigo): origem_inimigo}
    queue = [(origem_inimigo, 0)]  # (inimigo, profundidade)
    links_com_profundidade = []
    
    while queue:
        atual, profundidade = queue.pop(0)
        ax = atual["rect"].centerx
        ay = atual["rect"].centery
        
        for outro in inimigos_comum:
            outro_id = id(outro)
            if outro_id not in visited:
                dist = math.sqrt((outro["rect"].centerx - ax)**2 + (outro["rect"].centery - ay)**2)
                if dist <= 250:  # Raio de espalhamento
                    visited[outro_id] = outro
                    # Salva (origem, destino, profundidade)
                    links_com_profundidade.append((atual, outro, profundidade + 1))
                    queue.append((outro, profundidade + 1))
                    
    return list(visited.values()), links_com_profundidade

def criar_particulas_explosao_onda(tela, cx, cy):
    particulas_ativas = True
    qualidade = "alta"
    try:
        with open("saves/config_graficos.json", "r") as f:
            cfg = json.load(f)
            particulas_ativas = cfg.get("particulas_ativas", True)
            qualidade = cfg.get("qualidade_grafica", "alta")
    except:
        pass
        
    if not particulas_ativas or qualidade == "desativado":
        return
        
    num_particles = 15 if qualidade == "alta" else (8 if qualidade == "media" else 4)
    for _ in range(num_particles):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3.0, 7.0)
        r = random.randint(5, 20)
        ex = cx + int(r * math.cos(angle))
        ey = cy + int(r * math.sin(angle))
        color = random.choice([(0, 255, 255), (138, 43, 226), (255, 255, 255)])
        pygame.draw.line(tela, color, (cx, cy), (ex, ey), random.randint(1, 2))

def draw_electric_arc(tela, p1, p2, qualidade="alta"):
    if qualidade == "desativado":
        pygame.draw.line(tela, (138, 43, 226), p1, p2, 2)
        return
        
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx*dx + dy*dy)
    if dist < 5:
        return
        
    if qualidade == "alta":
        divisions = 6
        jitter_range = 12
    elif qualidade == "media":
        divisions = 4
        jitter_range = 8
    else: 
        divisions = 3
        jitter_range = 4
        
    points = [p1]
    nx = -dy / dist
    ny = dx / dist
    for i in range(1, divisions):
        t = i / divisions
        bx = x1 + dx * t
        by = y1 + dy * t
        jitter = random.uniform(-jitter_range, jitter_range)
        px = bx + nx * jitter
        py = by + ny * jitter
        points.append((int(px), int(py)))
    points.append(p2)
    
    if qualidade in ("alta", "media"):
        pygame.draw.lines(tela, (138, 43, 226), False, points, 3)
        pygame.draw.lines(tela, (0, 255, 255), False, points, 1)
    else:
        pygame.draw.lines(tela, (138, 43, 226), False, points, 2)

def desenhar_onda(tela, onda):
    particulas_ativas = True
    qualidade = "alta"
    try:
        with open("saves/config_graficos.json", "r") as f:
            cfg = json.load(f)
            particulas_ativas = cfg.get("particulas_ativas", True)
            qualidade = cfg.get("qualidade_grafica", "alta")
    except:
        pass

    if "particulas" not in onda:
        onda["particulas"] = []
    
    cx = onda["rect"].centerx
    cy = onda["rect"].centery
    rw = onda["rect"].width // 2
    
    # Glow da onda
    radius_glow = int(rw * 2.5)
    glow_surf = pygame.Surface((radius_glow * 2, radius_glow * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (138, 43, 226, 12), (radius_glow, radius_glow), radius_glow)
    pygame.draw.circle(glow_surf, (0, 191, 255, 25), (radius_glow, radius_glow), int(radius_glow * 0.7))
    pygame.draw.circle(glow_surf, (0, 255, 255, 45), (radius_glow, radius_glow), int(radius_glow * 0.45))
    tela.blit(glow_surf, (cx - radius_glow, cy - radius_glow))
    
    max_particles = 25 if qualidade == "alta" else (12 if qualidade == "media" else 6)
    spawn_chance = 0.8 if qualidade == "alta" else (0.5 if qualidade == "media" else 0.3)
    if not particulas_ativas:
        max_particles = 0; spawn_chance = 0.0
        onda["particulas"] = []
        
    if len(onda["particulas"]) < max_particles and random.random() < spawn_chance:
        for _ in range(random.randint(1, 2 if qualidade != "alta" else 3)):
            p_angle = random.uniform(0, 2 * math.pi)
            p_speed = random.uniform(2.0, 5.0)
            p_life = random.randint(10, 20)
            p_color = random.choice([(0, 255, 255), (147, 112, 219), (186, 85, 211), (0, 191, 255)])
            onda["particulas"].append({"rx": 0.0, "ry": 0.0, "vx": p_speed * math.cos(p_angle), "vy": p_speed * math.sin(p_angle), "life": p_life, "color": p_color})
            
    novas_particulas = []
    for p in onda["particulas"]:
        p["rx"] += p["vx"]
        p["ry"] += p["vy"]
        p["life"] -= 1
        if p["life"] > 0:
            novas_particulas.append(p)
            px = int(cx + p["rx"])
            py = int(cy + p["ry"])
            if 0 <= px < tela.get_width() and 0 <= py < tela.get_height():
                pygame.draw.circle(tela, p["color"], (px, py), random.randint(1, 3))
    onda["particulas"] = novas_particulas
    
    r_core = int(rw * 0.6)
    pygame.draw.circle(tela, (0, 90, 255), (cx, cy), r_core)
    pygame.draw.circle(tela, (0, 191, 255), (cx, cy), int(r_core * 0.75))
    pygame.draw.circle(tela, (220, 255, 255), (cx, cy), int(r_core * 0.4))
    
    ticks = pygame.time.get_ticks()
    num_arcs = 1 if qualidade == "baixa" else (2 if qualidade == "media" else 3)
    for a in range(num_arcs):
        base_r = int(r_core * 0.9) + a * 3
        angle_start = (ticks * 0.005 + a * (2 * math.pi / num_arcs)) % (2 * math.pi)
        points = []
        num_segments = 5
        arc_length = math.pi / 2
        for s in range(num_segments + 1):
            curr_angle = angle_start + (s / num_segments) * arc_length
            r_jitter = base_r + random.randint(-4, 4)
            px = cx + int(r_jitter * math.cos(curr_angle))
            py = cy + int(r_jitter * math.sin(curr_angle))
            points.append((px, py))
        if len(points) > 1:
            pygame.draw.lines(tela, (138, 43, 226), False, points, 2)

def aplicar_efeito_visual_choque(tela, inimigo):
    """
    Desenha um efeito de eletrocução sobre a hitbox do inimigo.
    Isso torna visível que ele está tomando choque.
    """
    inimigo["eletrocutado"] = True

def atualizar_e_desenhar_correntes(tela, correntes_eletricas, inimigos_comum, tempo_atual, dano_jogador=10.0):
    for inimigo in inimigos_comum:
        if isinstance(inimigo, dict):
            inimigo["eletrocutado"] = False

    particulas_ativas = True
    qualidade = "alta"
    try:
        with open("saves/config_graficos.json", "r") as f:
            cfg = json.load(f)
            particulas_ativas = cfg.get("particulas_ativas", True)
            qualidade = cfg.get("qualidade_grafica", "alta")
    except:
        pass

    novas_correntes = []
    inimigos_mortos = []
    
    for c in correntes_eletricas:
        c["inimigos"] = [inimigo for inimigo in c["inimigos"] if inimigo in inimigos_comum]
        
        if len(c["inimigos"]) == 0 or (tempo_atual - c["tempo_inicio"] >= c["duracao"]):
            continue
            
        novas_correntes.append(c)
        
        # O tempo de progressão da onda. Cada nível demora X milissegundos para ser alcançado.
        tempo_passado = tempo_atual - c["tempo_inicio"]
        delay_por_nivel = 150 # milissegundos por profundidade
        nivel_atual_atingido = tempo_passado // delay_por_nivel

        # Aplicar Dano aos inimigos que já foram alcançados pela corrente
        if tempo_atual - c.get("tempo_ultimo_dano", 0) >= c["intervalo_dano"]:
            c["tempo_ultimo_dano"] = tempo_atual
            for inimigo in c["inimigos"]:
                # Verifica qual o 'nível' do inimigo na corrente para ver se ele já tomou o choque
                nivel_inimigo = c["profundidades"].get(id(inimigo), 0)
                if nivel_inimigo <= nivel_atual_atingido:
                    # Aplica stun de 0.5s ao inimigo atingido pela corrente (não bosses)
                    if not inimigo.get("is_boss", False):
                        inimigo["stun_fim"] = max(inimigo.get("stun_fim", 0), tempo_atual + 500)
                    total_inimigos = len(c["inimigos"])
                    if total_inimigos < 1:
                        total_inimigos = 1
                    # Formula: 10% da vida maxima + 30% do dano do jogador, distribuído pelo total de inimigos na corrente
                    dano_base = (inimigo.get("vida_maxima", 100) * 0.10) + (dano_jogador * 0.30)
                    dano_tick = max(1.0, dano_base / total_inimigos)
                    inimigo["vida"] -= dano_tick
                    if inimigo["vida"] <= 0 and inimigo not in inimigos_mortos:
                        inimigos_mortos.append(inimigo)

        # Desenhar links e aplicar efeitos visuais de choque
        active_links = []
        # links é uma lista de (ent_a, ent_b, profundidade_b)
        for ent_a, ent_b, prof_b in c.get("links", []):
            a_ok = (ent_a in inimigos_comum) or (isinstance(ent_a, dict) and ent_a.get("is_boss", False))
            b_ok = (ent_b in inimigos_comum) or (isinstance(ent_b, dict) and ent_b.get("is_boss", False))
            if a_ok and b_ok:
                active_links.append((ent_a, ent_b, prof_b))
                # Só desenha o arco e o choque se o tempo de progressão já alcançou a profundidade_b
                if prof_b <= nivel_atual_atingido:
                    draw_electric_arc(tela, ent_a["rect"].center, ent_b["rect"].center, qualidade)
                
        c["links"] = active_links
        
        # Aplicar choque no inimigo caso a propagação o tenha alcançado
        for inimigo in c["inimigos"]:
            nivel_inimigo = c["profundidades"].get(id(inimigo), 0)
            if nivel_inimigo <= nivel_atual_atingido:
                aplicar_efeito_visual_choque(tela, inimigo)

                if particulas_ativas and qualidade != "desativado":
                    cx = inimigo["rect"].centerx
                    cy = inimigo["rect"].centery
                    max_sparks = 3 if qualidade == "alta" else (1 if qualidade == "media" else 0)
                    for _ in range(random.randint(0, max_sparks)):
                        sp_x = cx + random.randint(-15, 15)
                        sp_y = cy + random.randint(-15, 15)
                        color = random.choice([(186, 85, 211), (0, 255, 255), (147, 112, 219)])
                        pygame.draw.circle(tela, color, (sp_x, sp_y), random.randint(1, 2))
                    
    # Retorna o array in-place no objeto global ou lista se for retornado para fora
    correntes_eletricas[:] = novas_correntes
    return inimigos_mortos

def processar_habilidade_onda(ondas, correntes_eletricas, inimigos_comum, boss_info, tela, dt, tempo_atual, largura_mapa, altura_mapa, velocidade_onda, disparos=None, config_graficos=None):
    """
    Processa movimento e colisão da onda, e inicializa as correntes elétricas.
    `boss_info` é um dict com: {"vivo": bool, "rect": pygame.Rect, "atingido_por_onda": int} e atualizará o int de hit
    """
    novas_ondas = []
    inimigos_mortos_neste_frame = []
    
    for onda in ondas:
        if onda.get("tipo_manifestacao") == "chamado_reverso":
            retornante_manifestacao.desenhar_chamado(tela, onda, tempo_atual, config_graficos)
            if tempo_atual < int(onda.get("fim_ms", 0)):
                novas_ondas.append(onda)
            continue
        if onda.get("tipo_manifestacao") == "eclosao_parasitica":
            parasitica_manifestacao.desenhar_eclosao(tela, onda, tempo_atual, config_graficos)
            if tempo_atual < int(onda.get("fim_ms", 0)):
                novas_ondas.append(onda)
            continue
        if onda.get("tipo_manifestacao") == "fechamento_condutor":
            condutora_manifestacao.desenhar_fechamento(tela, onda, tempo_atual, config_graficos)
            if tempo_atual < int(onda.get("fim_ms", 0)):
                novas_ondas.append(onda)
            continue

        if onda.get("tipo_manifestacao") == "prisma_refracao":
            manter, mortos_prisma = prismatica_manifestacao.processar_prisma(
                onda, disparos or [], inimigos_comum, boss_info, tela, tempo_atual
            )
            inimigos_mortos_neste_frame.extend(mortos_prisma)
            if manter:
                novas_ondas.append(onda)
            continue

        if onda.get("tipo_manifestacao") == "fenda_lacerante":
            lacerante_manifestacao.desenhar_fenda(tela, onda, tempo_atual)
            inimigos_mortos_neste_frame.extend(
                lacerante_manifestacao.processar_fenda(onda, inimigos_comum, boss_info, tempo_atual)
            )
            if tempo_atual < int(onda.get("fim_ms", 0)):
                novas_ondas.append(onda)
            continue

        if "pos_x" not in onda:
            onda["pos_x"] = float(onda["rect"].x)
        if "pos_y" not in onda:
            onda["pos_y"] = float(onda["rect"].y)
            
        distancia_passo = velocidade_onda * dt
        if onda.get("falha_cooldown"):
            distancia_restante = max(
                0.0,
                float(onda.get("distancia_maxima", 10.0)) - float(onda.get("distancia_percorrida", 0.0)),
            )
            distancia_passo = min(distancia_passo, distancia_restante)

        onda["pos_x"] += distancia_passo * math.cos(onda["angulo"])
        onda["pos_y"] += distancia_passo * math.sin(onda["angulo"])
        if onda.get("falha_cooldown"):
            onda["distancia_percorrida"] = float(onda.get("distancia_percorrida", 0.0)) + abs(distancia_passo)
        onda["rect"].x = int(onda["pos_x"])
        onda["rect"].y = int(onda["pos_y"])
        
        desenhar_onda(tela, onda)
        onda_consumida = False
        if onda.get("falha_cooldown"):
            if onda["distancia_percorrida"] >= float(onda.get("distancia_maxima", 10.0)):
                criar_particulas_explosao_onda(tela, onda["rect"].centerx, onda["rect"].centery)
            else:
                novas_ondas.append(onda)
            continue
        
        # Colisão com o Boss
        if boss_info and boss_info.get("vivo") and boss_info["rect"] and onda["rect"].colliderect(boss_info["rect"]):
            if tempo_atual - boss_info.get("atingido_por_onda", 0) >= 500:
                boss_info["atingido_por_onda"] = tempo_atual
                boss_info["hit_flag"] = True # Indica pra subtrair vida fora daqui
                criar_particulas_explosao_onda(tela, onda["rect"].centerx, onda["rect"].centery)
                onda_consumida = True
                
                # Boss gera arco elétrico pros inimigos ao redor
                # Simulamos o boss como se fosse um dicionário compatível com a BFS de inimigo
                mock_boss = {"rect": boss_info["rect"], "is_boss": True}
                vizinhos, links_com_profundidade = calcular_corrente_eletrica_grafo(mock_boss, inimigos_comum)
                
                # Salva o level (profundidade) em que cada inimigo foi atingido
                profundidades = {id(mock_boss): 0}
                for u, v, d in links_com_profundidade:
                    profundidades[id(v)] = d

                correntes_eletricas.append({
                    "inimigos": vizinhos,
                    "links": links_com_profundidade,
                    "profundidades": profundidades,
                    "tempo_inicio": tempo_atual,
                    "duracao": 5000,
                    "intervalo_dano": 1000,
                    "tempo_ultimo_dano": tempo_atual
                })

        # Colisão com inimigos comuns
        if not onda_consumida:
            for inimigo in inimigos_comum:
                if onda["rect"].colliderect(inimigo["rect"]):
                    onda_consumida = True
                    criar_particulas_explosao_onda(tela, onda["rect"].centerx, onda["rect"].centery)
                    
                    vizinhos, links_com_profundidade = calcular_corrente_eletrica_grafo(inimigo, inimigos_comum)
                    profundidades = {id(inimigo): 0}
                    for u, v, d in links_com_profundidade:
                        profundidades[id(v)] = d

                    # Aplica stun de 0.5s a todos os inimigos atingidos (não bosses)
                    for viz in vizinhos:
                        if not viz.get("is_boss", False):
                            viz["stun_fim"] = tempo_atual + 500

                    correntes_eletricas.append({
                        "inimigos": vizinhos,
                        "links": links_com_profundidade,
                        "profundidades": profundidades,
                        "tempo_inicio": tempo_atual,
                        "duracao": 5000,
                        "intervalo_dano": 1000,
                        "tempo_ultimo_dano": tempo_atual
                    })
                    break # Só bate em um inimigo primário por onda e se espalha

        # Remove ondas que saíram do mapa ou colidiram
        if not onda_consumida and 0 <= onda["rect"].x < largura_mapa and 0 <= onda["rect"].y < altura_mapa:
            novas_ondas.append(onda)

    ondas[:] = novas_ondas
    return inimigos_mortos_neste_frame

