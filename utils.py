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
        with open("config_graficos.json", "r") as f:
            cfg = json.load(f)
            return cfg.get("qualidade_grafica", "alta")
    except:
        return "alta"

def animar_teleporte_plasma(tela, mapa, pos_x, pos_y, largura, altura, duracao, direcao, distancia_dash, largura_mapa, altura_mapa):
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
