import Caminhos
import json
import hashlib
import os
import pygame
import random
import math

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
    nomes_validos = ["Racional", "Impulsiva", "Devota", "Vanguarda"]
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
        print(f"[Erro ao carregar upgrades]: {e}")
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
        return ativar_palco_fullscreen(largura, altura)

    desativar_palco()
    tela = pygame.display.set_mode((largura, altura))
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
        print(f"[Trailer] Arquivo nao encontrado em {video_path}")
        return

    # 2. Carrega python-vlc
    try:
        import vlc
    except Exception as e:
        print(f"[Trailer] Erro ao carregar python-vlc: {e}. Pulando.")
        return

    # 3. Executa a reproducao
    try:
        vlc_instance = vlc.Instance('--quiet')
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
        print(f"[Trailer] Erro ao reproduzir: {e}")
        
    # Salva nas configuracoes para nao repetir
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"trailer_assistido": True}, f)
    except Exception as e:
        print(f"[Trailer] Erro ao salvar config: {e}")


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
