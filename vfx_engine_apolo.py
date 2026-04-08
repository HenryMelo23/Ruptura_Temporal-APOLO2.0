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
        DESIGN INVERTIDO: Agora usa o estilo Yin-Yang (verde+azul) da Umbra.
        Esfera de energia com mistura de verde e azul, menos partículas.
        """
        x, y = int(centro[0]), int(centro[1])
        raio_base = 6
        
        # Cores Yin-Yang: Verde e Azul mesclados
        cor_verde = (0, 255, 150)
        cor_azul = (0, 150, 255)
        
        # 1. Aura Dual Pulsante (Yin-Yang)
        pulsar = math.sin(agora * 0.02) * 2
        
        # Camada Verde (Yin)
        for nivel in range(2, 0, -1):
            raio_vfx = raio_base + (nivel * 3) + pulsar
            opacidade = 70 // nivel
            circulo_aura = pygame.Surface((raio_vfx * 2, raio_vfx * 2), pygame.SRCALPHA)
            pygame.draw.circle(circulo_aura, (*cor_verde, opacidade), (raio_vfx, raio_vfx), raio_vfx)
            tela.blit(circulo_aura, (x - raio_vfx, y - raio_vfx))
        
        # Camada Azul (Yang)
        for nivel in range(2, 0, -1):
            raio_vfx = raio_base + (nivel * 3) - pulsar
            opacidade = 70 // nivel
            circulo_aura = pygame.Surface((raio_vfx * 2, raio_vfx * 2), pygame.SRCALPHA)
            pygame.draw.circle(circulo_aura, (*cor_azul, opacidade), (raio_vfx, raio_vfx), raio_vfx)
            tela.blit(circulo_aura, (x - raio_vfx + 2, y - raio_vfx))

        # 2. Núcleo Branco com Borda Dual
        pygame.draw.circle(tela, (255, 255, 255), (x, y), raio_base)
        pygame.draw.circle(tela, cor_verde, (x - 1, y), raio_base + 2, 1)
        pygame.draw.circle(tela, cor_azul, (x + 1, y), raio_base + 2, 1)
        
        # 3. Arcos Elétricos Reduzidos (menos partículas)
        random.seed(int(agora // 80) + int(x + y))
        for _ in range(2):  # Apenas 2 arcos (reduzido)
            ang_ele = random.uniform(0, math.pi * 2)
            d_ele = raio_base + 6
            p_inicio = (x + math.cos(ang_ele) * raio_base, y + math.sin(ang_ele) * raio_base)
            p_fim = (x + math.cos(ang_ele) * d_ele, y + math.sin(ang_ele) * d_ele)
            cor_arco = random.choice([cor_verde, cor_azul])
            pygame.draw.line(tela, cor_arco, p_inicio, p_fim, 1)
        random.seed()

    def criar_impacto_fragmentado(self, x, y, cor=None):
        """
        OTIMIZADO: Gera efeito de desfragmentação com MENOS partículas (25-35 ao invés de 50).
        Física: Ejeção radial 360 graus com fricção contínua.
        """
        if cor is None:
            cor = self.config['player_aura']
        
        # Garante que a cor seja uma tupla válida de 3 inteiros
        if isinstance(cor, (tuple, list)) and len(cor) >= 3:
            cor = tuple(max(0, min(255, int(c))) for c in cor[:3])
        else:
            cor = (0, 210, 255)  # Cor padrão
            
        agora = pygame.time.get_ticks()
        # OTIMIZAÇÃO: Reduzido de 50 para 30 partículas
        for _ in range(30):
            angulo = random.uniform(0, math.pi * 2)
            velocidade = random.uniform(2.5, 9.0)  # OTIMIZAÇÃO: Reduzida velocidade máxima
            self.particulas.append({
                'x': x,
                'y': y,
                'vx': math.cos(angulo) * velocidade,
                'vy': math.sin(angulo) * velocidade,
                'inicio': agora,
                'vida': 600,  # OTIMIZAÇÃO: Reduzida de 800ms para 600ms
                'cor': cor,
                'tamanho': random.randint(2, 4)  # OTIMIZAÇÃO: Reduzido tamanho máximo
            })

    def atualizar_e_desenhar(self, tela, agora):
        """
        OTIMIZADO: Ciclo de vida dos fragmentos com processamento reduzido.
        Gerencia o pool de partículas para manter performance estável.
        """
        pool_ativo = []
        friccao = 0.94
        
        # OTIMIZAÇÃO: Limita número máximo de partículas ativas
        particulas_a_processar = self.particulas[:150]  # Máximo 150 partículas
        
        for p in particulas_a_processar:
            # Validação de cor no início (proteção contra partículas antigas)
            if 'cor' not in p or not isinstance(p.get('cor'), (tuple, list)) or len(p.get('cor', [])) < 3:
                continue
            
            tempo_decorrido = agora - p['inicio']
            
            if tempo_decorrido < p['vida']:
                # Física: Inércia e Fricção
                p['vx'] *= friccao
                p['vy'] *= friccao
                p['x'] += p['vx']
                p['y'] += p['vy']
                
                # Visual: Alpha Linear (Fade out)
                fator_vida = 1.0 - (tempo_decorrido / p['vida'])
                alpha = max(0, min(255, int(fator_vida * 255)))
                
                try:
                    # OTIMIZAÇÃO: Desenha apenas se alpha > 30 (invisíveis são puladas)
                    if alpha > 30:
                        surf_p = pygame.Surface((p['tamanho'] * 2, p['tamanho'] * 2), pygame.SRCALPHA)
                        cor_rgb = p['cor'][:3]
                        cor_rgb = tuple(max(0, min(255, int(c))) for c in cor_rgb)
                        pygame.draw.circle(surf_p, (*cor_rgb, alpha), (p['tamanho'], p['tamanho']), p['tamanho'])
                        tela.blit(surf_p, (int(p['x'] - p['tamanho']), int(p['y'] - p['tamanho'])))
                    
                    pool_ativo.append(p)
                except (ValueError, TypeError):
                    pass
                
        self.particulas = pool_ativo
