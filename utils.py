import Caminhos
import json
import hashlib
import os
import pygame
import random
import math
from qa_logger import registrar_erro

def calcular_hash(dados: dict) -> str:
    dados_sem_hash = {k: v for k, v in dados.items() if k != "hash"}
    conteudo = json.dumps(dados_sem_hash, sort_keys=True).encode()
    return hashlib.sha256(conteudo).hexdigest()

def salvar_upgrade_aureas(caminho, upgrades):
    data = {
        "upgrades": upgrades
    }
    upgrades_str = json.dumps(upgrades, sort_keys=True)
    hash_obj = hashlib.sha256(upgrades_str.encode())
    data["assinatura"] = hash_obj.hexdigest()

    with open(caminho, "w") as f:
        json.dump(data, f)


def carregar_upgrade_aureas(caminho):
    nomes_validos = ["Racional", "Impulsiva", "Devota", "Vanguarda", "Insana", "Voraz"]
    try:
        if not os.path.exists(caminho):
            return {nome: 0 for nome in nomes_validos}

        with open(caminho, "r") as f:
            data = json.load(f)
            upgrades = data.get("upgrades", {})
            assinatura = data.get("assinatura", "")

            upgrades_str = json.dumps(upgrades, sort_keys=True)
            hash_valido = hashlib.sha256(upgrades_str.encode()).hexdigest()

            if hash_valido != assinatura:
                return {nome: 0 for nome in nomes_validos}

            # Preenche chaves ausentes
            for nome in nomes_validos:
                if nome not in upgrades:
                    upgrades[nome] = 0

            return upgrades
    except Exception as e:
        registrar_erro("Erro ao carregar upgrades de aureas", e)
        return {nome: 0 for nome in nomes_validos}


    return upgrades

def carregar_qualidade_grafica():
    try:
        with open("saves/config_graficos.json", "r") as f:
            cfg = json.load(f)
            return cfg.get("qualidade_grafica", "alta")
    except:
        return "alta"

def animar_teleporte_plasma(tela, mapa, pos_x, pos_y, largura, altura, duracao, direcao, distancia_dash, largura_mapa, altura_mapa, dest_x=None, dest_y=None):
    """
    Bloqueia o jogo pela duração para renderizar um efeito de plasma/eletricidade azul
    simulando a fragmentação do personagem ao teleportar.
    Inclui um efeito de materialização no destino final.
    """
    inicio = pygame.time.get_ticks()
    relogio = pygame.time.Clock()
    
    qualidade = carregar_qualidade_grafica()
    if qualidade == "desligado":
        return  # Pula o efeito visual se estiver desligado

    # Multiplicadores de partículas baseado na qualidade
    mult_raios = 1.0
    mult_particulas = 1.0
    if qualidade == "media":
        mult_raios = 0.5
        mult_particulas = 0.5
    elif qualidade == "baixa":
        mult_raios = 0.2
        mult_particulas = 0.2

    centro_x = pos_x + largura // 2
    centro_y = pos_y + altura // 2
    
    # Calcular destino
    if dest_x is None or dest_y is None:
        dest_x, dest_y = pos_x, pos_y
        if direcao == 'up':
            dest_y = max(0, pos_y - distancia_dash)
        elif direcao == 'down':
            dest_y = min(altura_mapa - altura, pos_y + distancia_dash)
        elif direcao == 'left':
            dest_x = max(0, pos_x - distancia_dash)
        elif direcao == 'right':
            dest_x = min(largura_mapa - largura, pos_x + distancia_dash)
        
    centro_dest_x = dest_x + largura // 2
    centro_dest_y = dest_y + altura // 2
    
    while pygame.time.get_ticks() - inicio < duracao:
        # Apaga na posição de partida
        tela.blit(mapa, (pos_x, pos_y), pygame.Rect(pos_x, pos_y, largura, altura))
        # Apaga na posição de destino também para desenhar materialização sem borrar o fundo
        tela.blit(mapa, (dest_x, dest_y), pygame.Rect(dest_x, dest_y, largura, altura))
        
        # Progresso da animação (0 a 1)
        tempo_decorrido = pygame.time.get_ticks() - inicio
        progresso = tempo_decorrido / duracao if duracao > 0 else 1
        
        # Limite do raio da eletricidade proporcional ao personagem
        raio_maximo = max(largura, altura) * 0.6
        
        # ================= EFEITO DE PARTIDA (Fragmentando para fora) =================
        num_raios_partida = int((10 + (1.0 - progresso) * 20) * mult_raios)
        
        for _ in range(num_raios_partida):
            x1, y1 = centro_x, centro_y
            angulo = random.uniform(0, math.pi * 2)
            distancia_max = raio_maximo * (0.4 + progresso * 1.5) # Expandir para fora
            
            x2 = x1 + math.cos(angulo) * random.uniform(distancia_max*0.3, distancia_max)
            y2 = y1 + math.sin(angulo) * random.uniform(distancia_max*0.3, distancia_max)
            
            pontos = [(x1, y1)]
            passos = random.randint(3, 5)
            for i in range(1, passos):
                fator = i / passos
                px = x1 + (x2 - x1) * fator + random.uniform(-4, 4)
                py = y1 + (y2 - y1) * fator + random.uniform(-4, 4)
                pontos.append((px, py))
            pontos.append((x2, y2))
            
            cor = random.choice([(0, 255, 255), (0, 150, 255), (200, 255, 255), (255, 255, 255)])
            espessura = random.randint(1, 2)
            if len(pontos) > 1:
                pygame.draw.lines(tela, cor, False, pontos, espessura)
                
            if random.random() < (0.8 * mult_particulas):
                raio_particula = random.randint(1, 3)
                pygame.draw.circle(tela, cor, (int(x2), int(y2)), raio_particula)

        # ================= EFEITO DE CHEGADA (Materializando para dentro) =================
        num_raios_chegada = int((10 + progresso * 20) * mult_raios)
        
        for _ in range(num_raios_chegada):
            angulo = random.uniform(0, math.pi * 2)
            distancia_max = raio_maximo * (1.5 - progresso * 1.2) # Encolhendo para o centro
            
            x1 = centro_dest_x + math.cos(angulo) * random.uniform(distancia_max*0.5, distancia_max)
            y1 = centro_dest_y + math.sin(angulo) * random.uniform(distancia_max*0.5, distancia_max)
            x2, y2 = centro_dest_x, centro_dest_y
            
            pontos = [(x1, y1)]
            passos = random.randint(3, 5)
            for i in range(1, passos):
                fator = i / passos
                px = x1 + (x2 - x1) * fator + random.uniform(-4, 4)
                py = y1 + (y2 - y1) * fator + random.uniform(-4, 4)
                pontos.append((px, py))
            pontos.append((x2, y2))
            
            cor = random.choice([(0, 255, 255), (0, 150, 255), (200, 255, 255), (255, 255, 255)])
            espessura = random.randint(1, 2)
            if len(pontos) > 1:
                pygame.draw.lines(tela, cor, False, pontos, espessura)
                
            if random.random() < (0.8 * mult_particulas):
                raio_particula = random.randint(1, 3)
                pygame.draw.circle(tela, cor, (int(x1), int(y1)), raio_particula)
                
        # Esfera de luz convergente no destino
        if progresso > 0.3 and qualidade != "baixa":
            raio_esfera = int(raio_maximo * progresso * 0.8)
            if raio_esfera > 0:
                s = pygame.Surface((raio_esfera*2, raio_esfera*2), pygame.SRCALPHA)
                alpha_esf = int(255 * progresso)
                pygame.draw.circle(s, (0, 255, 255, int(alpha_esf * 0.5)), (raio_esfera, raio_esfera), raio_esfera)
                pygame.draw.circle(s, (255, 255, 255, alpha_esf), (raio_esfera, raio_esfera), raio_esfera//2)
                tela.blit(s, (centro_dest_x - raio_esfera, centro_dest_y - raio_esfera))

        pygame.display.flip()
        relogio.tick(60)


def configurar_tela(largura, altura):
    """
    Inicializa a tela do Pygame.
    """
    import pygame
    import json
    import os
    from ui_helpers import ativar_palco_fullscreen, desativar_palco

    tela_cheia = False
    try:
        if os.path.exists("saves/config_graficos.json"):
            with open("saves/config_graficos.json", "r") as f:
                tela_cheia = bool(json.load(f).get("tela_cheia", False))
    except Exception:
        tela_cheia = False

    if tela_cheia:
        tela = ativar_palco_fullscreen(largura, altura)
        pygame.mouse.set_visible(False)
        return tela

    desativar_palco()
    tela = pygame.display.set_mode((largura, altura))
    pygame.mouse.set_visible(False)
    return tela


def tocar_trailer_se_necessario(tela):
    """
    Toca o trailer do jogo se ainda nao tiver sido assistido.
    Suporta pular segurando ESC ou ESPACO.
    """
    import os
    import json
    import pygame
    import sys
    
    def _salvar_trailer_assistido(motivo_indisponivel=None):
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            dados = {"trailer_assistido": True}
            if motivo_indisponivel:
                dados["trailer_indisponivel"] = motivo_indisponivel
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(dados, f)
            return True
        except Exception as e:
            registrar_erro("Trailer: erro ao salvar config", e)
            return False

    def _erro_vlc_esperado(erro):
        texto = str(erro).lower()
        termos = (
            "vlc",
            "libvlc",
            "could not find module",
            "no module named",
            "cannot find",
            "dll",
        )
        return any(termo in texto for termo in termos)

    # 1. Verifica se ja foi assistido
    config_path = "saves/trailer_config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("trailer_assistido", False):
                    return
        except Exception:
            pass

    video_path = os.path.join("Video", "trailer.mp4")
    if not os.path.exists(video_path):
        registrar_erro(f"Trailer: arquivo nao encontrado em {video_path}")
        return

    # 2. Carrega python-vlc
    try:
        import vlc
    except Exception as e:
        if not _erro_vlc_esperado(e):
            registrar_erro("Trailer: erro ao carregar python-vlc", e)
        _salvar_trailer_assistido("python-vlc indisponivel")
        return

    # 3. Executa a reproducao
    try:
        try:
            vlc_instance = vlc.Instance('--quiet')
        except Exception as e:
            if not _erro_vlc_esperado(e):
                registrar_erro("Trailer: erro ao iniciar VLC", e)
            _salvar_trailer_assistido("libvlc indisponivel")
            return

        player = vlc_instance.media_player_new()
        
        # Vincula a tela do Pygame
        win_id = pygame.display.get_wm_info()['window']
        if sys.platform.startswith("win"):
            player.set_hwnd(win_id)
        elif sys.platform.startswith("linux"):
            player.set_xwindow(win_id)
        elif sys.platform.startswith("darwin"):
            player.set_nsobject(win_id)
            
        media = vlc_instance.media_new(video_path)
        player.set_media(media)
        
        # Desativa input de mouse/teclado interno do VLC para nao roubar eventos do Pygame
        player.video_set_mouse_input(False)
        player.video_set_key_input(False)
        
        # Preenche a tela de preto antes de iniciar
        tela.fill((0, 0, 0))
        pygame.display.flip()
        
        player.play()
        
        
        # Pequeno delay para a SDL e o VLC estabelecerem o frame e comecar o buffer
        pygame.time.delay(500)
        
        clock = pygame.time.Clock()
        running = True
        tempo_inicio_segurar = None
        tempo_para_pular = 1200  # 1.2 segundos segurando para pular
        
        # Fonte para o prompt de pulo
        font = None
        fonte_path = "Texto/Broken.otf"
        if os.path.exists(fonte_path):
            try:
                font = pygame.font.Font(fonte_path, 12)
            except Exception:
                pass
        if font is None:
            try:
                font = pygame.font.SysFont("arial", 12)
            except Exception:
                pass
                
        exibir_prompt = False
        tempo_exibicao_limite = 0
        
        while running:
            agora = pygame.time.get_ticks()
            
            # Consome eventos para manter a janela responsiva
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    player.stop()
                    player.release()
                    pygame.quit()
                    sys.exit(0)
                    
            # Verifica inputs para pular
            keys = pygame.key.get_pressed()
            segurando_pulo = keys[pygame.K_ESCAPE] or keys[pygame.K_SPACE]
            
            if segurando_pulo:
                exibir_prompt = True
                tempo_exibicao_limite = agora + 3000  # Mantem exibido por 3 segundos
                
                if tempo_inicio_segurar is None:
                    tempo_inicio_segurar = agora
                else:
                    tempo_decorrido = agora - tempo_inicio_segurar
                    if tempo_decorrido >= tempo_para_pular:
                        running = False
            else:
                tempo_inicio_segurar = None
                
            # Verifica estado da reproducao
            state = player.get_state()
            if state in [vlc.State.Ended, vlc.State.Stopped, vlc.State.Error]:
                running = False
                
            # Desenha o prompt AAA se estiver ativo
            if exibir_prompt and agora < tempo_exibicao_limite:
                largura_tela, altura_tela = tela.get_size()
                largura_prompt, altura_prompt = 360, 68
                x = largura_tela - largura_prompt - 30
                y = altura_tela - altura_prompt - 30
                
                # Container Glassy semi-transparente
                overlay_surf = pygame.Surface((largura_prompt, altura_prompt), pygame.SRCALPHA)
                pygame.draw.rect(overlay_surf, (15, 15, 20, 210), (0, 0, largura_prompt, altura_prompt), border_radius=10)
                pygame.draw.rect(overlay_surf, (0, 240, 255), (0, 0, largura_prompt, altura_prompt), width=2, border_radius=10)
                
                # Texto explicativo
                if font:
                    texto_surf = font.render("SEGURE [ESPACO] OU [ESC] PARA PULAR", True, (255, 255, 255))
                    overlay_surf.blit(texto_surf, (20, 14))
                
                # Barra de carregamento
                pygame.draw.rect(overlay_surf, (45, 45, 50), (20, 42, largura_prompt - 40, 8), border_radius=4)
                
                if tempo_inicio_segurar is not None:
                    decorrido = min(tempo_para_pular, agora - tempo_inicio_segurar)
                    pct = decorrido / tempo_para_pular
                    largura_preenchida = int((largura_prompt - 40) * pct)
                    # Cor neon ciano com efeito de brilho
                    pygame.draw.rect(overlay_surf, (0, 255, 204), (20, 42, largura_preenchida, 8), border_radius=4)
                    
                # Blita na tela do jogo
                tela.blit(overlay_surf, (x, y))
                pygame.display.update((x, y, largura_prompt, altura_prompt))
                
            clock.tick(60)
            
        player.stop()
        player.release()
        
        # Limpa a tela apos terminar
        tela.fill((0, 0, 0))
        pygame.display.flip()
        
    except Exception as e:
        if not _erro_vlc_esperado(e):
            registrar_erro("Trailer: erro ao reproduzir", e)
        
    # Salva nas configuracoes para nao repetir
    _salvar_trailer_assistido()


def redimensionar_cover(imagem, largura_dest, altura_dest):
    """
    Redimensiona uma imagem mantendo o aspect ratio original (cover) e recorta o excesso centralizado.
    Garante que a imagem preencha toda a tela sem distorção.
    """
    import pygame
    largura_orig, altura_orig = imagem.get_size()
    proporcao_orig = largura_orig / altura_orig
    proporcao_dest = largura_dest / altura_dest
    
    if proporcao_orig > proporcao_dest:
        # A imagem original é mais larga: ajusta a altura e recorta as laterais
        nova_altura = altura_dest
        nova_largura = int(nova_altura * proporcao_orig)
    else:
        # A imagem original é mais alta: ajusta a largura e recorta o topo/base
        nova_largura = largura_dest
        nova_altura = int(nova_largura / proporcao_orig)
        
    imagem_redimensionada = pygame.transform.scale(imagem, (nova_largura, nova_altura))
    
    # Cria a superfície final e blita a imagem recortada centralizada
    superficie_final = pygame.Surface((largura_dest, altura_dest))
    x_offset = (nova_largura - largura_dest) // 2
    y_offset = (nova_altura - altura_dest) // 2
    superficie_final.blit(imagem_redimensionada, (0, 0), (x_offset, y_offset, largura_dest, altura_dest))
    return superficie_final


def executar_animacao_morte_personagem(
    tela,
    pos_x_personagem,
    pos_y_personagem,
    largura_personagem,
    altura_personagem,
    frame_para_desenhar,
    angulo_inclinacao_personagem,
    desenhar_hud_callback=None,
    exibir_cronometro_callback=None,
    cursor_imagem=None,
    mouse_pos=None,
    config_graficos=None,
    som_morte=None
):
    """
    Bloqueia o jogo na morte do jogador:
    1. Pausa o jogo por 500ms mostrando a cena estática (congelada).
    2. Divide a sprite atual do jogador em pedaços e executa uma animação de
       fragmentação que cai por gravidade e desaparece gradualmente por 1 segundo.
    """
    import pygame
    import random
    import math
    import sys

    # Toca som de morte se fornecido
    if som_morte:
        try:
            som_morte.play()
        except:
            pass

    # Captura a tela de fundo sem o player (como ela se encontra no momento da chamada)
    screen_bg = tela.copy()

    # Cria a tela congelada com o player estático desenhado
    screen_frozen = screen_bg.copy()
    if frame_para_desenhar:
        if angulo_inclinacao_personagem != 0:
            frame_rotacionado = pygame.transform.rotate(frame_para_desenhar, angulo_inclinacao_personagem)
            novo_rect = frame_rotacionado.get_rect(center=(pos_x_personagem + largura_personagem//2, pos_y_personagem + altura_personagem//2))
            screen_frozen.blit(frame_rotacionado, novo_rect.topleft)
        else:
            screen_frozen.blit(frame_para_desenhar, (pos_x_personagem, pos_y_personagem))

    # Desenha o HUD e cronômetro na tela congelada se os callbacks forem fornecidos
    if desenhar_hud_callback:
        try:
            desenhar_hud_callback(screen_frozen)
        except Exception as e:
            pass
    if exibir_cronometro_callback:
        try:
            exibir_cronometro_callback(screen_frozen)
        except Exception as e:
            pass
    if cursor_imagem and mouse_pos:
        screen_frozen.blit(cursor_imagem, mouse_pos)

    # --- FASE 1: CONGELAMENTO POR 500MS ---
    tempo_inicio_congelamento = pygame.time.get_ticks()
    clock = pygame.time.Clock()
    
    while pygame.time.get_ticks() - tempo_inicio_congelamento < 500:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
                
        tela.blit(screen_frozen, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    # --- FASE 2: ANIMAÇÃO DE FRAGMENTAÇÃO (1000MS) ---
    fragments = []
    if frame_para_desenhar:
        num_rows = 6
        num_cols = 6
        w, h = frame_para_desenhar.get_size()
        tile_w = w // num_cols
        tile_h = h // num_rows
        colorkey = frame_para_desenhar.get_colorkey()

        for r in range(num_rows):
            for c in range(num_cols):
                rect = pygame.Rect(c * tile_w, r * tile_h, tile_w, tile_h)
                try:
                    sub = frame_para_desenhar.subsurface(rect).copy()
                except ValueError:
                    continue
                
                # Checagem de transparência por canal alpha ou colorkey
                has_pixel = False
                for tx in range(tile_w):
                    for ty in range(tile_h):
                        pixel_color = sub.get_at((tx, ty))
                        if len(pixel_color) > 3 and pixel_color[3] <= 10:
                            continue
                        if colorkey is not None:
                            if pixel_color[:3] == colorkey[:3]:
                                continue
                        has_pixel = True
                        break
                    if has_pixel:
                        break
                
                if not has_pixel:
                    continue

                fragments.append({
                    "surf": sub,
                    "rel_x": float(c * tile_w),
                    "rel_y": float(r * tile_h),
                    "x_offset": 0.0,
                    "y_offset": 0.0,
                    "vx": random.uniform(-4.5, 4.5),
                    "vy": random.uniform(-8.0, -2.0),
                    "rot": 0.0,
                    "vrot": random.uniform(-15.0, 15.0),
                    "alpha": 255.0
                })

    tempo_inicio_animacao = pygame.time.get_ticks()
    
    while pygame.time.get_ticks() - tempo_inicio_animacao < 1000:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

        # 1. Baseia o frame na tela de fundo capturada sem o player
        screen_temp = screen_bg.copy()

        # 2. Atualiza e desenha cada fragmento
        gravity = 0.35
        for f in fragments:
            f["x_offset"] += f["vx"]
            f["y_offset"] += f["vy"]
            f["vy"] += gravity
            f["vx"] *= 0.98
            f["rot"] += f["vrot"]
            f["alpha"] = max(0.0, f["alpha"] - 4.5)

            if f["alpha"] > 0:
                rot_surf = pygame.transform.rotate(f["surf"], f["rot"])
                rot_surf.set_alpha(int(f["alpha"]))
                
                cx = pos_x_personagem + f["rel_x"] + f["surf"].get_width() / 2 + f["x_offset"]
                cy = pos_y_personagem + f["rel_y"] + f["surf"].get_height() / 2 + f["y_offset"]
                
                rect = rot_surf.get_rect(center=(int(cx), int(cy)))
                screen_temp.blit(rot_surf, rect.topleft)

        # 3. Desenha o HUD, cronômetro e cursor por cima
        if desenhar_hud_callback:
            try:
                desenhar_hud_callback(screen_temp)
            except Exception as e:
                pass
        if exibir_cronometro_callback:
            try:
                exibir_cronometro_callback(screen_temp)
            except Exception as e:
                pass
        if cursor_imagem and mouse_pos:
            screen_temp.blit(cursor_imagem, mouse_pos)

        tela.blit(screen_temp, (0, 0))
        pygame.display.flip()
        clock.tick(60)


def animar_spawn_portal(tela, mapa, pos_x, pos_y, largura, altura, duracao, frames_animacao, direcao_atual, Som_portal):
    """
    Exibe um efeito cinemático de portal dimensional e materialização de partículas para o spawn do personagem.
    Duração recomendada: ~2000ms.
    """
    import pygame
    import random
    import math

    inicio = pygame.time.get_ticks()
    relogio = pygame.time.Clock()

    qualidade = carregar_qualidade_grafica()
    mult_particulas = 1.0
    if qualidade == "media":
        mult_particulas = 0.5
    elif qualidade == "baixa":
        mult_particulas = 0.2

    centro_x = pos_x + largura // 2
    centro_y = pos_y + altura // 2

    # Toca o som do portal no início
    if Som_portal:
        try:
            Som_portal.play()
        except:
            pass

    # Lista de partículas
    # Cada partícula: {"x", "y", "vx", "vy", "color", "size", "alpha", "life", "type"}
    particulas = []

    # Obter imagem base do jogador
    player_img = None
    if frames_animacao and direcao_atual in frames_animacao and len(frames_animacao[direcao_atual]) > 0:
        player_img = frames_animacao[direcao_atual][0]

    portal_max_raio_x = 65
    portal_max_raio_y = 25

    while True:
        agora = pygame.time.get_ticks()
        decorrido = agora - inicio
        if decorrido >= duracao:
            break

        progresso = decorrido / duracao

        # 1. Desenhar fundo do mapa completo
        tela.blit(mapa, (0, 0))

        # 2. Portal - Raio atual (abre nos primeiros 30%, fica aberto até 80%, depois fecha)
        if progresso < 0.3:
            fator_portal = progresso / 0.3
        elif progresso < 0.8:
            fator_portal = 1.0 + 0.05 * math.sin(agora * 0.02)
        else:
            fator_portal = max(0.0, 1.0 - (progresso - 0.8) / 0.2)

        raio_x = portal_max_raio_x * fator_portal
        raio_y = portal_max_raio_y * fator_portal

        # Spawna partículas de energia do portal
        if progresso < 0.8 and fator_portal > 0.1:
            num_spawns = int(3 * mult_particulas)
            for _ in range(max(1, num_spawns)):
                angulo = random.uniform(0, 2 * math.pi)
                px = centro_x + math.cos(angulo) * raio_x
                py = (centro_y + altura // 2.5) + math.sin(angulo) * raio_y

                velocidade = random.uniform(1.5, 3.5)
                vx = -math.sin(angulo) * velocidade + random.uniform(-0.5, 0.5)
                vy = math.cos(angulo) * (velocidade * 0.3) - random.uniform(0.5, 1.5)
                partic_cor = random.choice([
                    (0, 255, 255),  # Ciano
                    (143, 33, 252), # Roxo
                    (255, 255, 255) # Branco
                ])
                partic_size = random.uniform(2, 5)
                particulas.append({
                    "x": px,
                    "y": py,
                    "vx": vx,
                    "vy": vy,
                    "color": partic_cor,
                    "size": partic_size,
                    "life": random.randint(20, 40),
                    "type": "portal"
                })

        # Spawna partículas de reconstrução (convergem para o corpo do jogador)
        # Ocorre entre 20% e 75% da animação
        if 0.2 <= progresso <= 0.75:
            num_conv = int(5 * mult_particulas)
            for _ in range(max(1, num_conv)):
                angulo = random.uniform(0, 2 * math.pi)
                dist_partida = random.uniform(90, 160)
                px = centro_x + math.cos(angulo) * dist_partida
                py = centro_y + math.sin(angulo) * dist_partida

                tx = pos_x + random.uniform(0, largura)
                ty = pos_y + random.uniform(0, altura)

                frames_to_target = random.uniform(20, 35)
                vx = (tx - px) / frames_to_target
                vy = (ty - py) / frames_to_target

                partic_cor = random.choice([
                    (0, 255, 255),
                    (200, 255, 255),
                    (143, 33, 252)
                ])
                particulas.append({
                    "x": px,
                    "y": py,
                    "vx": vx,
                    "vy": vy,
                    "color": partic_cor,
                    "size": random.uniform(2, 4),
                    "life": int(frames_to_target),
                    "type": "reconstrucao",
                    "tx": tx,
                    "ty": ty
                })

        # Desenhar base do portal (concentric ellipses) no chão
        if raio_x > 2 and raio_y > 2:
            for i in range(3):
                mult_r = 1.0 - i * 0.2
                rx = int(raio_x * mult_r)
                ry = int(raio_y * mult_r)
                if rx > 1 and ry > 1:
                    s_portal = pygame.Surface((rx * 2, ry * 2), pygame.SRCALPHA)
                    cor_rgba = (
                        143 if i == 1 else 0,
                        33 if i == 1 else 255,
                        252 if i == 1 else 255,
                        int(150 * (1.0 - i * 0.2) * (1.0 if progresso < 0.8 else fator_portal))
                    )
                    pygame.draw.ellipse(s_portal, cor_rgba, (0, 0, rx * 2, ry * 2), int(2 + i))
                    tela.blit(s_portal, (centro_x - rx, (centro_y + altura // 2.5) - ry))

        # 3. Desenhar e atualizar partículas
        novas_particulas = []
        for p in particulas:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1

            if p["type"] == "reconstrucao":
                dx = p["tx"] - p["x"]
                dy = p["ty"] - p["y"]
                dist = math.hypot(dx, dy)
                if dist < 6:
                    p["vx"] = random.uniform(-0.5, 0.5)
                    p["vy"] = random.uniform(-0.5, 0.5)
                    p["type"] = "faisca"
                    p["life"] = random.randint(5, 12)
            elif p["type"] == "portal":
                p["vx"] *= 0.96
                p["vy"] += 0.02

            if p["life"] > 0:
                pygame.draw.circle(tela, p["color"], (int(p["x"]), int(p["y"])), int(p["size"]))
                novas_particulas.append(p)
        particulas = novas_particulas

        # 4. Materialização do jogador (Geovana)
        # Ocorre gradualmente a partir de 30% até 85%
        if progresso >= 0.3 and player_img:
            alpha_progresso = min(1.0, (progresso - 0.3) / 0.5)
            player_alpha = int(255 * alpha_progresso)

            surf_player = pygame.Surface((largura, altura), pygame.SRCALPHA)
            surf_player.blit(player_img, (0, 0))
            surf_player.set_alpha(player_alpha)

            # Efeito de Glitch/Desalinhamento Temporal
            chance_glitch = 0.5 * (1.0 - alpha_progresso)
            if random.random() < chance_glitch and qualidade != "baixa":
                fatias = random.randint(3, 7)
                altura_fatia = altura // fatias
                for f in range(fatias):
                    fy = f * altura_fatia
                    offset_x = random.randint(-12, 12)
                    tela.blit(surf_player, (pos_x + offset_x, pos_y + fy), pygame.Rect(0, fy, largura, altura_fatia))
                    if random.random() < 0.4:
                        pygame.draw.line(
                            tela,
                            (0, 255, 255),
                            (pos_x - 15, pos_y + fy + random.randint(0, altura_fatia)),
                            (pos_x + largura + 15, pos_y + fy + random.randint(0, altura_fatia)),
                            random.randint(1, 2)
                        )
            else:
                tela.blit(surf_player, (pos_x, pos_y))

            # Adiciona um contorno brilhante sutil de energia (neon)
            if alpha_progresso < 0.95 and qualidade != "baixa":
                try:
                    mask = pygame.mask.from_surface(player_img)
                    mask_surf = mask.to_surface(setcolor=(0, 255, 255, int(120 * (1.0 - alpha_progresso))), unsetcolor=(0, 0, 0, 0))
                    tela.blit(mask_surf, (pos_x + random.randint(-2, 2), pos_y + random.randint(-2, 2)))
                except:
                    pass

        pygame.display.flip()
        relogio.tick(60)
