import pygame
import random
import math

class ApoloVFXManager:
    """
    Motor de Efeitos Visuais Centralizado para o Projeto Ruptura Temporal.
    Gerencia a renderização procedural de plasma e a fragmentação física por impacto.
    """
    def __init__(self):
        self.particulas = []
        self.config = {
            'player_core': (255, 255, 255),
            'player_aura': (0, 210, 255),
            'fase_critica': (255, 50, 50),
            'duracao_impacto': 800  # ms
        }

    def renderizar_plasma_apolo(self, tela, centro, agora, especial=False):
        """
        Substitui o blit estático por uma esfera de energia multicamada.
        Possui núcleo de alta intensidade e aura pulsante.
        """
        x, y = int(centro[0]), int(centro[1])
        cor_aura = self.config['player_aura'] if not especial else self.config['fase_critica']
        raio_base = 6
        
        # 1. Aura Translúcida Pulsante (Glow Procedural)
        # Sincronização temporal para o efeito de pulsação
        pulsar = math.sin(agora * 0.02) * 3
        
        # Renderização em camadas (SRCALPHA para transparência real)
        for nivel in range(3, 0, -1):
            raio_vfx = raio_base + (nivel * 4) + pulsar
            opacidade = 85 // nivel
            circulo_aura = pygame.Surface((raio_vfx * 2, raio_vfx * 2), pygame.SRCALPHA)
            pygame.draw.circle(circulo_aura, (*cor_aura, opacidade), (raio_vfx, raio_vfx), raio_vfx)
            tela.blit(circulo_aura, (x - raio_vfx, y - raio_vfx))

        # 2. Núcleo Hiper-Brilhante (Calor e Intensidade)
        pygame.draw.circle(tela, self.config['player_core'], (x, y), raio_base)
        pygame.draw.circle(tela, cor_aura, (x, y), raio_base + 2, 1)

    def criar_impacto_fragmentado(self, x, y, cor=None):
        """
        Gera o efeito de desfragmentação absoluta exigido (50 pixels radiais).
        Física: Ejeção radial 360 graus com fricção contínua.
        """
        if cor is None:
            cor = self.config['player_aura']
            
        agora = pygame.time.get_ticks()
        for _ in range(50):
            angulo = random.uniform(0, math.pi * 2)
            velocidade = random.uniform(3.0, 11.5) # Explosão caótica
            self.particulas.append({
                'x': x,
                'y': y,
                'vx': math.cos(angulo) * velocidade,
                'vy': math.sin(angulo) * velocidade,
                'inicio': agora,
                'vida': self.config['duracao_impacto'],
                'cor': cor,
                'tamanho': random.randint(2, 5)
            })

    def atualizar_e_desenhar(self, tela, agora):
        """
        Ciclo de vida dos fragmentos: 800ms, Alpha esmaecendo e Fricção.
        Gerencia o pool de partículas para manter performance estável.
        """
        pool_ativo = []
        friccao = 0.94 # Desaceleração viscosa por frame
        
        for p in self.particulas:
            tempo_decorrido = agora - p['inicio']
            
            if tempo_decorrido < p['vida']:
                # Física: Inércia e Fricção
                p['vx'] *= friccao
                p['vy'] *= friccao
                p['x'] += p['vx']
                p['y'] += p['vy']
                
                # Visual: Alpha Linear (Fade out global de 800ms)
                fator_vida = 1.0 - (tempo_decorrido / p['vida'])
                alpha = int(fator_vida * 255)
                
                # Desenho suave do fragmento (Efeito Viscoso)
                surf_p = pygame.Surface((p['tamanho'] * 2, p['tamanho'] * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf_p, (*p['cor'], alpha), (p['tamanho'], p['tamanho']), p['tamanho'])
                tela.blit(surf_p, (int(p['x'] - p['tamanho']), int(p['y'] - p['tamanho'])))
                
                pool_ativo.append(p)
                
        self.particulas = pool_ativo
