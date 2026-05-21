import json
import hashlib
import os

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


def configurar_tela(largura, altura):
    """
    Inicializa a tela do Pygame.
    """
    import pygame
    
    # Tenta inicializar com Double Buffer e VSync ativo.
    try:
        tela = pygame.display.set_mode((largura, altura), pygame.DOUBLEBUF, vsync=1)
    except Exception:
        try:
            tela = pygame.display.set_mode((largura, altura), pygame.DOUBLEBUF)
        except Exception:
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
    except ImportError:
        print("[Trailer] python-vlc nao esta instalado. Pulando.")
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



