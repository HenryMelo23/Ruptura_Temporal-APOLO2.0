import pygame
import random
import math
import threading

# Cache Global de Superfícies de Transparência
_VFX_SURFACE_CACHE = {}

def obter_superficie_particula(tamanho, cor, alpha):
    """Retorna uma Surface do Pygame em cache, otimizando milhares de criações por frame."""
    chave = (tamanho, cor, alpha)
    if chave not in _VFX_SURFACE_CACHE:
        surf = pygame.Surface((tamanho * 2, tamanho * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*cor, alpha), (tamanho, tamanho), tamanho)
        _VFX_SURFACE_CACHE[chave] = surf
    return _VFX_SURFACE_CACHE[chave]


class ApoloVFXManager:
    """
    Motor de Efeitos Visuais Centralizado.
    Utiliza Zero-Allocation via Caching e Multithreading para isolar cálculos de física.
    """
    def __init__(self):
        self.particulas = []
        self.render_buffer = []  # Lista segura para a thread de desenho
        self.lock = threading.Lock()
        self.running = True
        
        self.config = {
            'player_core': (255, 255, 255),
            'player_aura': (0, 210, 255),
            'fase_critica': (255, 50, 50),
            'duracao_impacto': 800  # ms
        }
        
        # Inicia a thread de background para física
        self.thread_fisica = threading.Thread(target=self._loop_fisica_background, daemon=True)
        self.thread_fisica.start()

    def _loop_fisica_background(self):
        """Thread daemon que processa atrito, movimento e fade out das partículas."""
        clock = pygame.time.Clock()
        while self.running:
            try:
                agora = pygame.time.get_ticks()
            except pygame.error:
                continue
                
            friccao = 0.94
            
            with self.lock:
                particulas_processar = self.particulas[:250] # Limite alto, a thread aguenta tranquilo
                novas_particulas = []
                novo_render_buffer = []
                
                for p in particulas_processar:
                    tempo_decorrido = agora - p['inicio']
                    if tempo_decorrido < p['vida']:
                        p['vx'] *= friccao
                        p['vy'] *= friccao
                        p['x'] += p['vx']
                        p['y'] += p['vy']
                        
                        fator_vida = 1.0 - (tempo_decorrido / p['vida'])
                        alpha = max(0, min(255, int(fator_vida * 255)))
                        
                        if alpha > 10:
                            novas_particulas.append(p)
                            # Discretizar alpha em steps de 10 para evitar estourar a RAM no Cache
                            alpha_quantizado = (alpha // 10) * 10
                            novo_render_buffer.append((p['x'], p['y'], p['tamanho'], p['cor'][:3], alpha_quantizado))
                
                self.particulas = novas_particulas
                self.render_buffer = novo_render_buffer
                
            clock.tick(120)  # Fisica processa até 120 ticks assíncronos

    def renderizar_plasma_apolo(self, tela, centro, agora, especial=False):
        """
        Esfera de energia com mistura de verde e azul. Usa cache para máxima performance.
        """
        x, y = int(centro[0]), int(centro[1])
        raio_base = 6
        cor_verde = (0, 255, 150)
        cor_azul = (0, 150, 255)
        pulsar = math.sin(agora * 0.02) * 2
        
        for nivel in range(2, 0, -1):
            raio_vfx = max(1, int(raio_base + (nivel * 3) + pulsar))
            opacidade = int((70 // nivel) // 10) * 10 # quantizado
            surf_v = obter_superficie_particula(raio_vfx, cor_verde, opacidade)
            tela.blit(surf_v, (x - raio_vfx, y - raio_vfx))
            
            raio_vfx_a = max(1, int(raio_base + (nivel * 3) - pulsar))
            surf_a = obter_superficie_particula(raio_vfx_a, cor_azul, opacidade)
            tela.blit(surf_a, (x - raio_vfx_a + 2, y - raio_vfx_a))

        pygame.draw.circle(tela, (255, 255, 255), (x, y), raio_base)
        pygame.draw.circle(tela, cor_verde, (x - 1, y), raio_base + 2, 1)
        pygame.draw.circle(tela, cor_azul, (x + 1, y), raio_base + 2, 1)
        
        random.seed(int(agora // 80) + int(x + y))
        for _ in range(2):
            ang_ele = random.uniform(0, math.pi * 2)
            d_ele = raio_base + 6
            p_inicio = (x + math.cos(ang_ele) * raio_base, y + math.sin(ang_ele) * raio_base)
            p_fim = (x + math.cos(ang_ele) * d_ele, y + math.sin(ang_ele) * d_ele)
            pygame.draw.line(tela, random.choice([cor_verde, cor_azul]), p_inicio, p_fim, 1)
        random.seed()

    def criar_impacto_fragmentado(self, x, y, cor=None):
        """
        Adiciona partículas na thread-safe list para avaliação física paralela.
        """
        if cor is None:
            cor = self.config['player_aura']
        
        if isinstance(cor, (tuple, list)) and len(cor) >= 3:
            cor = tuple(max(0, min(255, int(c))) for c in cor[:3])
        else:
            cor = (0, 210, 255)
            
        agora = pygame.time.get_ticks()
        novas = []
        for _ in range(40):
            angulo = random.uniform(0, math.pi * 2)
            velocidade = random.uniform(3.0, 12.0)
            novas.append({
                'x': x,
                'y': y,
                'vx': math.cos(angulo) * velocidade,
                'vy': math.sin(angulo) * velocidade,
                'inicio': agora,
                'vida': random.randint(500, 800),
                'cor': cor,
                'tamanho': random.randint(2, 5)
            })
        
        with self.lock:
            self.particulas.extend(novas)

    def atualizar_e_desenhar(self, tela, agora):
        """
        Lê as partículas do render_buffer da thread e blita via CACHE O(1).
        Zero processamento físico.
        """
        with self.lock:
            # Shallow copy ultra-rápida (só cópia referencial)
            buffer = self.render_buffer[:]
            
        for x, y, tam, cor, alpha in buffer:
            surf = obter_superficie_particula(tam, cor, alpha)
            tela.blit(surf, (int(x - tam), int(y - tam)))
