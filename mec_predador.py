"""
MEC-PREDADOR: Criatura Biomecânica Alienígena Quadrúpede COM ASAS
Simulação Dinâmica de Alto Desempenho @ 100 FPS
Arquitetura: Máquina de Estados + Motor de Partículas + Física Vetorial Euclidiana
NOVO: Sistema de Asas Animadas + Rotação Direcional
"""

import pygame
import math
import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple

# ============================================================================
# CONSTANTES FÍSICAS E TEMPORAIS
# ============================================================================
FPS_TARGET = 100
DURACAO_CARREGAMENTO = 2000  # ms (cravado)
VELOCIDADE_ATAQUE = 800  # pixels/segundo
VELOCIDADE_RETORNO = 200  # pixels/segundo
DISTANCIA_MINIMA_ALVO = 100  # pixels

# ============================================================================
# PALETA DE CORES (32-BIT ERA)
# ============================================================================
class Paleta:
    # Fundo
    VAZIO_ESPACIAL = (15, 15, 20)
    
    # Corpo Biomecânico
    VERDE_ESCURO = (25, 80, 45)
    VERDE_CLARO = (50, 180, 90)
    ROXO_PROFUNDO = (60, 20, 80)
    ROXO_CLARO = (140, 60, 180)
    
    # Detalhes Orgânicos
    ROSA_NEON = (255, 50, 150)
    ROSA_NEON_BRILHO = (255, 120, 200)
    
    # Energia
    AMARELO_ENERGIA = (255, 240, 80)
    LARANJA_ENERGIA = (255, 140, 40)
    
    # Rastro Cinético
    CIANO_VIBRANTE = (0, 255, 255)
    CIANO_DISSIPATIVO = (0, 180, 200)

# ============================================================================
# MÁQUINA DE ESTADOS
# ============================================================================
class EstadoMecPredador(Enum):
    REPOUSANDO = "REPOUSANDO"
    CARREGANDO = "CARREGANDO"
    ATACANDO = "ATACANDO"
    RETORNANDO = "RETORNANDO"

# ============================================================================
# PARTÍCULA DE ENERGIA
# ============================================================================
@dataclass
class ParticulaEnergia:
    x: float
    y: float
    vx: float
    vy: float
    vida: float  # 0.0 a 1.0
    tamanho: float
    cor: Tuple[int, int, int]
    
    def atualizar(self, dt: float, alvo_x: float, alvo_y: float, forca_atracao: float):
        """Atualiza física da partícula com atração gravitacional ao núcleo"""
        dx = alvo_x - self.x
        dy = alvo_y - self.y
        dist = math.hypot(dx, dy)
        
        if dist > 1:
            dx_norm = dx / dist
            dy_norm = dy / dist
            
            self.vx += dx_norm * forca_atracao * dt
            self.vy += dy_norm * forca_atracao * dt
        
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vida -= 0.3 * dt
        
        return self.vida > 0

# ============================================================================
# PARTÍCULA DE RASTRO CINÉTICO
# ============================================================================
@dataclass
class ParticulaRastro:
    x: float
    y: float
    tamanho: float
    vida: float  # 0.0 a 1.0
    cor: Tuple[int, int, int]
    
    def atualizar(self, dt: float):
        """Dissipação temporal do rastro"""
        self.vida -= 1.2 * dt
        self.tamanho *= 0.95
        return self.vida > 0

# ============================================================================
# MEC-PREDADOR: CLASSE PRINCIPAL COM ASAS
# ============================================================================
class MecPredador:
    def __init__(self, x: float, y: float):
        # Posição e Física
        self.origem_x = x
        self.origem_y = y
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        
        # Dimensões
        self.largura = 140
        self.altura = 100
        
        # Máquina de Estados
        self.estado = EstadoMecPredador.REPOUSANDO
        self.tempo_estado = 0.0
        
        # Alvo de Ataque
        self.alvo_x = 0.0
        self.alvo_y = 0.0
        
        # Sistemas de Partículas
        self.particulas_energia: List[ParticulaEnergia] = []
        self.particulas_rastro: List[ParticulaRastro] = []
        
        # Animação Orgânica
        self.fase_pulsacao = 0.0
        
        # === SISTEMA DE ASAS E ROTAÇÃO ===
        self.angulo_rotacao = 0.0  # Graus (0 = direita)
        self.fase_batida_asas = 0.0  # Radianos (0-2π)
        self.velocidade_batida = 12.0  # rad/s
        self.sprite_cache = {}
    
    # ========================================================================
    # RENDERIZAÇÃO: PIXEL ART COM ASAS E ROTAÇÃO
    # ========================================================================
    
    def _criar_sprite_pixel_art(self) -> pygame.Surface:
        """Cria sprite base em pixel art com asas animadas"""
        largura_sprite = 140
        altura_sprite = 100
        
        sprite = pygame.Surface((largura_sprite, altura_sprite), pygame.SRCALPHA)
        
        cx = largura_sprite // 2
        cy = altura_sprite // 2
        
        pulso = int(math.sin(self.fase_pulsacao) * 2)
        batida = (math.sin(self.fase_batida_asas) + 1) / 2  # 0-1
        
        # === ASAS (CAMADA DE FUNDO) ===
        self._desenhar_asas_pixel_art(sprite, cx, cy, batida)
        
        # === PERNAS TRASEIRAS ===
        pygame.draw.line(sprite, Paleta.ROXO_PROFUNDO, 
                        (cx - 20, cy + 10), (cx - 25, cy + 25), 4)
        pygame.draw.circle(sprite, Paleta.VERDE_ESCURO, 
                          (cx - 25, cy + 25), 4)
        
        pygame.draw.line(sprite, Paleta.ROXO_PROFUNDO, 
                        (cx - 10, cy + 10), (cx - 15, cy + 25), 4)
        pygame.draw.circle(sprite, Paleta.VERDE_ESCURO, 
                          (cx - 15, cy + 25), 4)
        
        # === CORPO PRINCIPAL ===
        pygame.draw.ellipse(sprite, Paleta.VERDE_ESCURO, 
                           (cx - 30, cy - 5, 35, 25))
        pygame.draw.ellipse(sprite, Paleta.ROXO_PROFUNDO, 
                           (cx - 27, cy - 2, 29, 19), 2)
        
        pygame.draw.ellipse(sprite, Paleta.VERDE_CLARO, 
                           (cx - 10, cy - 10, 40, 30))
        pygame.draw.ellipse(sprite, Paleta.ROXO_CLARO, 
                           (cx - 7, cy - 7, 34, 24), 2)
        
        # === PERNAS DIANTEIRAS ===
        pygame.draw.line(sprite, Paleta.ROXO_PROFUNDO, 
                        (cx + 15, cy + 5), (cx + 10, cy + 22), 5)
        pygame.draw.circle(sprite, Paleta.VERDE_CLARO, 
                          (cx + 10, cy + 22), 5)
        
        pygame.draw.line(sprite, Paleta.ROXO_PROFUNDO, 
                        (cx + 25, cy + 5), (cx + 20, cy + 22), 5)
        pygame.draw.circle(sprite, Paleta.VERDE_CLARO, 
                          (cx + 20, cy + 22), 5)
        
        # === CABEÇA ===
        pygame.draw.ellipse(sprite, Paleta.VERDE_ESCURO, 
                           (cx + 20, cy - 15, 30, 25))
        
        pygame.draw.arc(sprite, Paleta.ROXO_PROFUNDO, 
                       (cx + 22, cy - 13, 26, 21), 0, math.pi, 3)
        
        # Mandíbulas
        pontos_sup = [(cx + 45, cy - 10), (cx + 55, cy - 7), (cx + 50, cy - 3)]
        pygame.draw.polygon(sprite, Paleta.ROSA_NEON, pontos_sup)
        
        pontos_inf = [(cx + 45, cy), (cx + 55, cy - 3), (cx + 50, cy + 3)]
        pygame.draw.polygon(sprite, Paleta.ROSA_NEON, pontos_inf)
        
        pygame.draw.line(sprite, Paleta.ROSA_NEON_BRILHO, 
                        (cx + 52, cy - 5), (cx + 58, cy - 5), 2)
        
        # === NÚCLEO DE ENERGIA ===
        nucleo_x = cx - 5
        nucleo_y = cy - 10
        
        raio_brilho = 12 + pulso
        pygame.draw.circle(sprite, Paleta.LARANJA_ENERGIA, 
                          (nucleo_x, nucleo_y), raio_brilho)
        pygame.draw.circle(sprite, Paleta.AMARELO_ENERGIA, 
                          (nucleo_x, nucleo_y), 8)
        
        for i in range(3):
            offset = i * 8
            pygame.draw.line(sprite, Paleta.AMARELO_ENERGIA, 
                           (nucleo_x, nucleo_y), 
                           (cx, cy + offset - 5), 2)
        
        return sprite
    
    def _desenhar_asas_pixel_art(self, sprite: pygame.Surface, cx: int, cy: int, batida: float):
        """Desenha asas biomecânicas com animação de batida"""
        angulo_asa = batida * 45  # 0° a 45°
        comprimento_asa = 35
        largura_asa_base = 12
        largura_asa_ponta = 6
        
        # === ASA ESQUERDA (SUPERIOR) ===
        asa_esq_base_x = cx - 10
        asa_esq_base_y = cy - 8
        
        angulo_rad = math.radians(180 - angulo_asa)
        asa_esq_ponta_x = asa_esq_base_x + math.cos(angulo_rad) * comprimento_asa
        asa_esq_ponta_y = asa_esq_base_y + math.sin(angulo_rad) * comprimento_asa
        
        pontos_asa_esq = [
            (asa_esq_base_x, asa_esq_base_y - largura_asa_base // 2),
            (asa_esq_ponta_x, asa_esq_ponta_y - largura_asa_ponta // 2),
            (asa_esq_ponta_x, asa_esq_ponta_y + largura_asa_ponta // 2),
            (asa_esq_base_x, asa_esq_base_y + largura_asa_base // 2),
        ]
        
        pygame.draw.polygon(sprite, Paleta.VERDE_ESCURO, pontos_asa_esq)
        pygame.draw.line(sprite, Paleta.ROXO_PROFUNDO,
                        (asa_esq_base_x, asa_esq_base_y),
                        (asa_esq_ponta_x, asa_esq_ponta_y), 3)
        
        for i in range(3):
            offset = (i + 1) / 4
            meio_x = asa_esq_base_x + (asa_esq_ponta_x - asa_esq_base_x) * offset
            meio_y = asa_esq_base_y + (asa_esq_ponta_y - asa_esq_base_y) * offset
            perp_x = meio_x + math.sin(angulo_rad) * 8
            perp_y = meio_y - math.cos(angulo_rad) * 8
            pygame.draw.line(sprite, Paleta.ROXO_CLARO,
                           (meio_x, meio_y), (perp_x, perp_y), 2)
        
        pygame.draw.lines(sprite, Paleta.ROSA_NEON, False, pontos_asa_esq, 2)
        pygame.draw.circle(sprite, Paleta.ROSA_NEON_BRILHO,
                          (int(asa_esq_ponta_x), int(asa_esq_ponta_y)), 4)
        
        # === ASA DIREITA (INFERIOR) ===
        asa_dir_base_x = cx - 10
        asa_dir_base_y = cy + 8
        
        angulo_rad_dir = math.radians(180 + angulo_asa)
        asa_dir_ponta_x = asa_dir_base_x + math.cos(angulo_rad_dir) * comprimento_asa
        asa_dir_ponta_y = asa_dir_base_y + math.sin(angulo_rad_dir) * comprimento_asa
        
        pontos_asa_dir = [
            (asa_dir_base_x, asa_dir_base_y - largura_asa_base // 2),
            (asa_dir_ponta_x, asa_dir_ponta_y - largura_asa_ponta // 2),
            (asa_dir_ponta_x, asa_dir_ponta_y + largura_asa_ponta // 2),
            (asa_dir_base_x, asa_dir_base_y + largura_asa_base // 2),
        ]
        
        pygame.draw.polygon(sprite, Paleta.VERDE_ESCURO, pontos_asa_dir)
        pygame.draw.line(sprite, Paleta.ROXO_PROFUNDO,
                        (asa_dir_base_x, asa_dir_base_y),
                        (asa_dir_ponta_x, asa_dir_ponta_y), 3)
        
        for i in range(3):
            offset = (i + 1) / 4
            meio_x = asa_dir_base_x + (asa_dir_ponta_x - asa_dir_base_x) * offset
            meio_y = asa_dir_base_y + (asa_dir_ponta_y - asa_dir_base_y) * offset
            perp_x = meio_x + math.sin(angulo_rad_dir) * 8
            perp_y = meio_y - math.cos(angulo_rad_dir) * 8
            pygame.draw.line(sprite, Paleta.ROXO_CLARO,
                           (meio_x, meio_y), (perp_x, perp_y), 2)
        
        pygame.draw.lines(sprite, Paleta.ROSA_NEON, False, pontos_asa_dir, 2)
        pygame.draw.circle(sprite, Paleta.ROSA_NEON_BRILHO,
                          (int(asa_dir_ponta_x), int(asa_dir_ponta_y)), 4)
    
    def _calcular_angulo_movimento(self) -> float:
        """Calcula ângulo baseado na direção de movimento"""
        if abs(self.vx) < 0.1 and abs(self.vy) < 0.1:
            return self.angulo_rotacao
        
        angulo_rad = math.atan2(-self.vy, self.vx)
        return math.degrees(angulo_rad)
    
    def _desenhar_particulas_energia(self, tela: pygame.Surface):
        """Renderiza partículas de carregamento"""
        for p in self.particulas_energia:
            tamanho = int(p.tamanho * p.vida)
            if tamanho > 0:
                pygame.draw.circle(tela, p.cor, 
                                 (int(p.x), int(p.y)), tamanho)
    
    def _desenhar_rastro_cinetico(self, tela: pygame.Surface):
        """Renderiza rastro dissipativo"""
        for r in self.particulas_rastro:
            tamanho = max(1, int(r.tamanho * r.vida))
            cor_base = Paleta.CIANO_VIBRANTE if r.vida > 0.5 else Paleta.CIANO_DISSIPATIVO
            pygame.draw.circle(tela, cor_base, 
                             (int(r.x), int(r.y)), tamanho)
    
    def renderizar(self, tela: pygame.Surface):
        """Pipeline de renderização completo com rotação"""
        # 1. Rastro cinético
        self._desenhar_rastro_cinetico(tela)
        
        # 2. Partículas de energia
        if self.estado == EstadoMecPredador.CARREGANDO:
            self._desenhar_particulas_energia(tela)
        
        # 3. Sprite rotacionado
        sprite = self._criar_sprite_pixel_art()
        sprite_rotacionado = pygame.transform.rotate(sprite, self.angulo_rotacao)
        
        # Centraliza sprite rotacionado
        rect = sprite_rotacionado.get_rect(center=(int(self.x), int(self.y)))
        tela.blit(sprite_rotacionado, rect)
        
        # 4. Debug
        fonte = pygame.font.Font(None, 20)
        texto = fonte.render(self.estado.value, True, (255, 255, 255))
        tela.blit(texto, (int(self.x) - 40, int(self.y) - 70))
    
    # ========================================================================
    # FÍSICA E MOVIMENTAÇÃO
    # ========================================================================
    
    def _mover_para_alvo(self, dt: float, velocidade: float):
        """Movimento vetorial puro"""
        dx = self.alvo_x - self.x
        dy = self.alvo_y - self.y
        dist = math.hypot(dx, dy)
        
        if dist > 1:
            dx_norm = dx / dist
            dy_norm = dy / dist
            
            deslocamento = velocidade * dt
            
            if deslocamento >= dist:
                self.x = self.alvo_x
                self.y = self.alvo_y
                self.vx = 0
                self.vy = 0
                return True
            else:
                self.x += dx_norm * deslocamento
                self.y += dy_norm * deslocamento
                self.vx = dx_norm * velocidade
                self.vy = dy_norm * velocidade
                return False
        else:
            self.vx = 0
            self.vy = 0
            return True
    
    # ========================================================================
    # MOTOR DE PARTÍCULAS
    # ========================================================================
    
    def _gerar_particulas_carregamento(self):
        """Gera partículas de energia"""
        for _ in range(3):
            angulo = random.uniform(0, 2 * math.pi)
            raio = random.uniform(80, 150)
            
            px = self.x + math.cos(angulo) * raio
            py = self.y + math.sin(angulo) * raio
            
            vx = random.uniform(-50, 50)
            vy = random.uniform(-50, 50)
            
            cor = random.choice([Paleta.AMARELO_ENERGIA, Paleta.LARANJA_ENERGIA])
            
            particula = ParticulaEnergia(
                x=px, y=py, vx=vx, vy=vy,
                vida=1.0, tamanho=random.uniform(2, 5), cor=cor
            )
            self.particulas_energia.append(particula)
    
    def _gerar_rastro_cinetico(self):
        """Gera rastro durante ataque"""
        rastro_x = self.x - self.vx * 0.05
        rastro_y = self.y - self.vy * 0.05
        
        for _ in range(2):
            offset_x = random.uniform(-10, 10)
            offset_y = random.uniform(-10, 10)
            
            particula = ParticulaRastro(
                x=rastro_x + offset_x,
                y=rastro_y + offset_y,
                tamanho=random.uniform(5, 12),
                vida=1.0,
                cor=Paleta.CIANO_VIBRANTE
            )
            self.particulas_rastro.append(particula)
    
    # ========================================================================
    # MÁQUINA DE ESTADOS
    # ========================================================================
    
    def _atualizar_repousando(self, dt: float):
        """Estado: REPOUSANDO"""
        self.fase_pulsacao += dt * 3
        self.fase_batida_asas += dt * 4  # Batida lenta
        
        self.x = self.origem_x
        self.y = self.origem_y
    
    def _atualizar_carregando(self, dt: float):
        """Estado: CARREGANDO"""
        self.tempo_estado += dt * 1000
        
        self.x = self.origem_x
        self.y = self.origem_y
        
        self._gerar_particulas_carregamento()
        
        self.particulas_energia = [
            p for p in self.particulas_energia 
            if p.atualizar(dt, self.x, self.y, 500)
        ]
        
        self.fase_pulsacao += dt * 8
        self.fase_batida_asas += dt * self.velocidade_batida  # Batida rápida
        
        if self.tempo_estado >= DURACAO_CARREGAMENTO:
            self.estado = EstadoMecPredador.ATACANDO
            self.tempo_estado = 0.0
            self.particulas_energia.clear()
    
    def _atualizar_atacando(self, dt: float):
        """Estado: ATACANDO"""
        self._gerar_rastro_cinetico()
        
        chegou = self._mover_para_alvo(dt, VELOCIDADE_ATAQUE)
        
        # Atualiza ângulo baseado no movimento
        self.angulo_rotacao = self._calcular_angulo_movimento()
        
        # Batida de asas muito rápida
        self.fase_batida_asas += dt * self.velocidade_batida * 2
        
        self.particulas_rastro = [
            r for r in self.particulas_rastro 
            if r.atualizar(dt)
        ]
        
        if chegou:
            self.estado = EstadoMecPredador.RETORNANDO
            self.tempo_estado = 0.0
            self.alvo_x = self.origem_x
            self.alvo_y = self.origem_y
    
    def _atualizar_retornando(self, dt: float):
        """Estado: RETORNANDO"""
        chegou = self._mover_para_alvo(dt, VELOCIDADE_RETORNO)
        
        # Atualiza ângulo
        self.angulo_rotacao = self._calcular_angulo_movimento()
        
        # Batida de asas moderada
        self.fase_batida_asas += dt * self.velocidade_batida
        
        self.particulas_rastro = [
            r for r in self.particulas_rastro 
            if r.atualizar(dt)
        ]
        
        self.fase_pulsacao += dt * 2
        
        if chegou:
            self.estado = EstadoMecPredador.REPOUSANDO
            self.tempo_estado = 0.0
    
    def atualizar(self, dt: float):
        """Loop principal"""
        if self.estado == EstadoMecPredador.REPOUSANDO:
            self._atualizar_repousando(dt)
        elif self.estado == EstadoMecPredador.CARREGANDO:
            self._atualizar_carregando(dt)
        elif self.estado == EstadoMecPredador.ATACANDO:
            self._atualizar_atacando(dt)
        elif self.estado == EstadoMecPredador.RETORNANDO:
            self._atualizar_retornando(dt)
    
    # ========================================================================
    # API PÚBLICA
    # ========================================================================
    
    def iniciar_ataque(self, alvo_x: float, alvo_y: float):
        """Inicia ataque"""
        if self.estado != EstadoMecPredador.REPOUSANDO:
            return False
        
        dist = math.hypot(alvo_x - self.origem_x, alvo_y - self.origem_y)
        if dist < DISTANCIA_MINIMA_ALVO:
            return False
        
        self.alvo_x = alvo_x
        self.alvo_y = alvo_y
        self.estado = EstadoMecPredador.CARREGANDO
        self.tempo_estado = 0.0
        
        # Calcula ângulo inicial para o alvo
        dx = alvo_x - self.x
        dy = alvo_y - self.y
        self.angulo_rotacao = math.degrees(math.atan2(-dy, dx))
        
        return True
    
    def obter_hitbox(self) -> pygame.Rect:
        """Retorna hitbox"""
        return pygame.Rect(
            int(self.x - self.largura // 2), 
            int(self.y - self.altura // 2), 
            self.largura, 
            self.altura
        )

# ============================================================================
# DEMONSTRAÇÃO
# ============================================================================
def main():
    pygame.init()
    
    LARGURA = 1920
    ALTURA = 1080
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("MEC-PREDADOR COM ASAS @ 100 FPS")
    
    clock = pygame.time.Clock()
    
    predador = MecPredador(LARGURA // 4, ALTURA // 2)
    
    alvo_x = LARGURA * 3 // 4
    alvo_y = ALTURA // 2
    
    rodando = True
    while rodando:
        dt = clock.tick(FPS_TARGET) / 1000.0
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            
            if evento.type == pygame.MOUSEBUTTONDOWN:
                alvo_x, alvo_y = evento.pos
                predador.iniciar_ataque(alvo_x, alvo_y)
            
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_SPACE:
                    predador.iniciar_ataque(alvo_x, alvo_y)
        
        predador.atualizar(dt)
        
        tela.fill(Paleta.VAZIO_ESPACIAL)
        
        pygame.draw.circle(tela, (255, 0, 0), (int(alvo_x), int(alvo_y)), 10, 2)
        pygame.draw.line(tela, (255, 0, 0), 
                        (int(alvo_x) - 15, int(alvo_y)), 
                        (int(alvo_x) + 15, int(alvo_y)), 2)
        pygame.draw.line(tela, (255, 0, 0), 
                        (int(alvo_x), int(alvo_y) - 15), 
                        (int(alvo_x), int(alvo_y) + 15), 2)
        
        predador.renderizar(tela)
        
        fonte = pygame.font.Font(None, 30)
        fps_texto = fonte.render(f"FPS: {int(clock.get_fps())}", True, (0, 255, 0))
        angulo_texto = fonte.render(f"Ângulo: {int(predador.angulo_rotacao)}°", True, (255, 255, 0))
        instrucoes = fonte.render("ESPAÇO: Atacar | CLIQUE: Definir Alvo", True, (255, 255, 255))
        
        tela.blit(fps_texto, (10, 10))
        tela.blit(angulo_texto, (10, 40))
        tela.blit(instrucoes, (10, 70))
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
