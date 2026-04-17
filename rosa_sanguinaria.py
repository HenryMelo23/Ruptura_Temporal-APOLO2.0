"""
ROSA SANGUINÁRIA: Flor Biomecânica Mortal
Simulação Dinâmica de Alto Desempenho @ 100 FPS
Arquitetura: Máquina de Estados + Motor de Partículas + Física Vetorial
Design: Pétalas animadas + Miolo pulsante + Rotação direcional
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
# PALETA DE CORES (ROSA SANGUINÁRIA)
# ============================================================================
class Paleta:
    # Fundo
    VAZIO_ESPACIAL = (15, 15, 20)
    
    # Pétalas (gradiente vermelho/rosa)
    VERMELHO_SANGUE = (180, 20, 30)
    VERMELHO_ESCURO = (120, 15, 25)
    ROSA_INTENSO = (255, 50, 80)
    ROSA_CLARO = (255, 120, 150)
    ROSA_NEON = (255, 80, 180)
    
    # Miolo
    AMARELO_POLEN = (255, 220, 80)
    LARANJA_MIOLO = (255, 160, 40)
    DOURADO = (255, 200, 100)
    
    # Caule e Folhas
    VERDE_CAULE = (40, 100, 50)
    VERDE_FOLHA = (60, 140, 70)
    VERDE_ESCURO = (30, 80, 40)
    
    # Energia
    VERMELHO_ENERGIA = (255, 30, 50)
    ROSA_ENERGIA = (255, 100, 180)
    
    # Rastro
    VERMELHO_RASTRO = (255, 50, 100)
    ROSA_RASTRO = (255, 150, 200)

# ============================================================================
# MÁQUINA DE ESTADOS
# ============================================================================
class EstadoRosaSanguinaria(Enum):
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
    vida: float
    tamanho: float
    cor: Tuple[int, int, int]
    
    def atualizar(self, dt: float, alvo_x: float, alvo_y: float, forca_atracao: float):
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
# PARTÍCULA DE RASTRO
# ============================================================================
@dataclass
class ParticulaRastro:
    x: float
    y: float
    tamanho: float
    vida: float
    cor: Tuple[int, int, int]
    
    def atualizar(self, dt: float):
        self.vida -= 5.0 * dt  # Aumentado de 3.0 para 5.0 (desaparece MUITO mais rápido)
        self.tamanho *= 0.85  # Diminui ainda mais rápido
        return self.vida > 0

# ============================================================================
# PÓLEN EXPLOSIVO
# ============================================================================
@dataclass
class PolenExplosivo:
    x: float
    y: float
    tempo_vida: float  # Tempo até explodir (2s)
    tamanho: float
    fase_pulsacao: float
    explodiu: bool = False
    
    def atualizar(self, dt: float):
        """Atualiza pólen e verifica se deve explodir"""
        self.tempo_vida -= dt
        self.fase_pulsacao += dt * 8  # Pulsação rápida
        
        if self.tempo_vida <= 0 and not self.explodiu:
            self.explodiu = True
            return True  # Sinal para criar explosão
        
        return False
    
    def renderizar(self, tela: pygame.Surface):
        """Renderiza pólen pulsante com efeitos visuais aprimorados"""
        if self.explodiu:
            return
        
        # Pulsação (aumenta conforme se aproxima da explosão)
        urgencia = max(0, 1 - (self.tempo_vida / 2.0))  # 0 a 1
        pulso = math.sin(self.fase_pulsacao) * (3 + urgencia * 5)
        
        raio = int(self.tamanho + pulso)
        
        # Cor muda conforme se aproxima da explosão
        if self.tempo_vida > 1.5:
            # Verde/amarelo (seguro)
            cor_externa = Paleta.AMARELO_POLEN
            cor_media = Paleta.DOURADO
            cor_interna = (255, 255, 200)
        elif self.tempo_vida > 0.5:
            # Laranja (alerta)
            cor_externa = Paleta.LARANJA_MIOLO
            cor_media = Paleta.AMARELO_POLEN
            cor_interna = Paleta.DOURADO
        else:
            # Vermelho (perigo!)
            cor_externa = Paleta.VERMELHO_ENERGIA
            cor_media = Paleta.ROSA_ENERGIA
            cor_interna = Paleta.AMARELO_POLEN
        
        # === HALO EXTERNO (pulsante) ===
        if urgencia > 0.3:
            raio_halo = raio + int(urgencia * 8)
            alpha_halo = int(urgencia * 100)
            s = pygame.Surface((raio_halo * 2 + 10, raio_halo * 2 + 10), pygame.SRCALPHA)
            pygame.draw.circle(s, (*cor_externa, alpha_halo), 
                             (raio_halo + 5, raio_halo + 5), raio_halo)
            tela.blit(s, (int(self.x - raio_halo - 5), int(self.y - raio_halo - 5)), 
                     special_flags=pygame.BLEND_ALPHA_SDL2)
        
        # === CAMADAS DO PÓLEN ===
        # Camada externa
        pygame.draw.circle(tela, cor_externa, (int(self.x), int(self.y)), raio)
        
        # Camada média
        raio_medio = max(1, raio - 2)
        pygame.draw.circle(tela, cor_media, (int(self.x), int(self.y)), raio_medio)
        
        # Núcleo interno
        raio_interno = max(1, raio - 4)
        pygame.draw.circle(tela, cor_interna, (int(self.x), int(self.y)), raio_interno)
        
        # === BRILHO CENTRAL ===
        pygame.draw.circle(tela, (255, 255, 255), 
                          (int(self.x - 2), int(self.y - 2)), 2)
        
        # === PARTÍCULAS ORBITANDO (quando crítico) ===
        if self.tempo_vida < 0.8:
            num_particulas = 6
            raio_orbita = raio + 6
            for i in range(num_particulas):
                angulo = (i / num_particulas) * 2 * math.pi + self.fase_pulsacao * 2
                px = self.x + math.cos(angulo) * raio_orbita
                py = self.y + math.sin(angulo) * raio_orbita
                pygame.draw.circle(tela, cor_externa, (int(px), int(py)), 2)
        
        # === INDICADOR DE TEMPO (anel) ===
        if self.tempo_vida < 1.0:
            # Anel que se fecha conforme o tempo passa
            progresso = 1 - (self.tempo_vida / 1.0)
            angulo_fim = progresso * 2 * math.pi
            
            # Desenha arco
            raio_anel = raio + 4
            pontos = []
            num_pontos = int(progresso * 32)
            for i in range(num_pontos + 1):
                ang = (i / 32) * 2 * math.pi
                px = self.x + math.cos(ang) * raio_anel
                py = self.y + math.sin(ang) * raio_anel
                pontos.append((int(px), int(py)))
            
            if len(pontos) > 1:
                pygame.draw.lines(tela, cor_externa, False, pontos, 3)

# ============================================================================
# EXPLOSÃO DE PÓLEN (VISUAL APRIMORADO)
# ============================================================================
@dataclass
class ExplosaoPolem:
    x: float
    y: float
    raio: float
    raio_max: float
    vida: float  # 0.0 a 1.0
    particulas_explosao: List = None
    
    def __post_init__(self):
        """Inicializa partículas da explosão"""
        if self.particulas_explosao is None:
            self.particulas_explosao = []
            # Cria 24 partículas em todas as direções
            for i in range(24):
                angulo = (i / 24) * 2 * math.pi
                velocidade = random.uniform(80, 150)
                
                self.particulas_explosao.append({
                    'angulo': angulo,
                    'velocidade': velocidade,
                    'distancia': 0,
                    'tamanho': random.uniform(3, 8),
                    'cor_idx': i % 3  # 3 cores diferentes
                })
    
    def atualizar(self, dt: float):
        """Expande explosão e atualiza partículas"""
        # Expande onda de choque
        self.raio += 250 * dt  # 250 pixels/segundo (mais rápido)
        
        # Atualiza partículas
        for p in self.particulas_explosao:
            p['distancia'] += p['velocidade'] * dt
        
        # Decai vida
        self.vida -= 1.5 * dt  # 0.66 segundos de duração
        
        return self.vida > 0 and self.raio < self.raio_max
    
    def renderizar(self, tela: pygame.Surface):
        """Renderiza explosão com múltiplas camadas e partículas"""
        if self.vida <= 0:
            return
        
        # Alpha baseado na vida
        alpha = int(self.vida * 255)
        
        # === ONDA DE CHOQUE (múltiplas camadas) ===
        camadas = [
            (self.raio, Paleta.VERMELHO_ENERGIA, 1.0),
            (self.raio * 0.85, Paleta.ROSA_ENERGIA, 0.8),
            (self.raio * 0.7, Paleta.LARANJA_MIOLO, 0.6),
            (self.raio * 0.55, Paleta.AMARELO_POLEN, 0.4),
            (self.raio * 0.4, (255, 255, 200), 0.3),
        ]
        
        for raio_camada, cor_base, intensidade in camadas:
            if raio_camada > 0:
                alpha_camada = int(alpha * intensidade)
                
                # Círculo preenchido
                s = pygame.Surface((int(raio_camada * 2 + 20), int(raio_camada * 2 + 20)), pygame.SRCALPHA)
                pygame.draw.circle(s, (*cor_base, alpha_camada), 
                                 (int(raio_camada + 10), int(raio_camada + 10)), 
                                 int(raio_camada))
                tela.blit(s, (int(self.x - raio_camada - 10), int(self.y - raio_camada - 10)), 
                         special_flags=pygame.BLEND_ALPHA_SDL2)
                
                # Borda brilhante
                if intensidade > 0.5:
                    pygame.draw.circle(tela, cor_base, 
                                     (int(self.x), int(self.y)), 
                                     int(raio_camada), 3)
        
        # === PARTÍCULAS RADIAIS ===
        cores_particulas = [
            Paleta.VERMELHO_ENERGIA,
            Paleta.ROSA_ENERGIA,
            Paleta.AMARELO_POLEN
        ]
        
        for p in self.particulas_explosao:
            if p['distancia'] < self.raio_max:
                # Posição da partícula
                px = self.x + math.cos(p['angulo']) * p['distancia']
                py = self.y + math.sin(p['angulo']) * p['distancia']
                
                # Tamanho diminui com a distância
                tamanho = p['tamanho'] * (1 - p['distancia'] / self.raio_max)
                
                if tamanho > 0.5:
                    cor = cores_particulas[p['cor_idx']]
                    pygame.draw.circle(tela, cor, (int(px), int(py)), int(tamanho))
                    
                    # Rastro da partícula
                    rastro_dist = p['distancia'] * 0.7
                    rastro_x = self.x + math.cos(p['angulo']) * rastro_dist
                    rastro_y = self.y + math.sin(p['angulo']) * rastro_dist
                    pygame.draw.line(tela, cor, 
                                   (int(rastro_x), int(rastro_y)), 
                                   (int(px), int(py)), 2)
        
        # === NÚCLEO BRILHANTE ===
        if self.vida > 0.5:
            raio_nucleo = int(15 * self.vida)
            # Brilho branco intenso
            pygame.draw.circle(tela, (255, 255, 255), (int(self.x), int(self.y)), raio_nucleo)
            # Halo amarelo
            pygame.draw.circle(tela, Paleta.AMARELO_POLEN, (int(self.x), int(self.y)), raio_nucleo + 5, 3)
            # Halo laranja
            pygame.draw.circle(tela, Paleta.LARANJA_MIOLO, (int(self.x), int(self.y)), raio_nucleo + 10, 2)
    
    def obter_hitbox(self) -> pygame.Rect:
        """Retorna hitbox da explosão para detecção de colisão"""
        return pygame.Rect(
            int(self.x - self.raio),
            int(self.y - self.raio),
            int(self.raio * 2),
            int(self.raio * 2)
        )

# ============================================================================
# ROSA SANGUINÁRIA: CLASSE PRINCIPAL
# ============================================================================
class RosaSanguinaria:
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
        self.altura = 140
        
        # Máquina de Estados
        self.estado = EstadoRosaSanguinaria.REPOUSANDO
        self.tempo_estado = 0.0
        
        # Alvo de Ataque
        self.alvo_x = 0.0
        self.alvo_y = 0.0
        
        # Sistemas de Partículas
        self.particulas_energia: List[ParticulaEnergia] = []
        self.particulas_rastro: List[ParticulaRastro] = []
        
        # Sistema de Pólen Explosivo
        self.polens_explosivos: List[PolenExplosivo] = []
        self.explosoes: List[ExplosaoPolem] = []
        self.distancia_percorrida = 0.0  # Rastreia distância para spawnar pólen
        self.ultima_pos_x = x
        self.ultima_pos_y = y
        
        # Animação Orgânica
        self.fase_pulsacao = 0.0
        
        # Sistema de Pétalas
        self.angulo_rotacao = 0.0  # Graus (rotação direcional)
        self.angulo_rotacao_petalas = 0.0  # Graus (rotação horária das pétalas)
        self.fase_petalas = 0.0  # Abertura/fechamento das pétalas
        self.velocidade_petalas = 8.0  # rad/s
        self.velocidade_rotacao_petalas = 30.0  # graus/s (rotação horária)
        self.num_petalas = 12  # Número de pétalas (mais parruda)
    
    # ========================================================================
    # RENDERIZAÇÃO: PIXEL ART DA ROSA
    # ========================================================================
    
    def _criar_sprite_rosa(self) -> pygame.Surface:
        """Cria sprite da rosa sanguinária em pixel art"""
        largura_sprite = 140
        altura_sprite = 140
        
        sprite = pygame.Surface((largura_sprite, altura_sprite), pygame.SRCALPHA)
        
        cx = largura_sprite // 2
        cy = altura_sprite // 2
        
        # Pulsação do miolo
        pulso = int(math.sin(self.fase_pulsacao) * 3)
        
        # Abertura das pétalas (0 = fechada, 1 = aberta)
        abertura = (math.sin(self.fase_petalas) + 1) / 2
        
        # === PÉTALAS (CAMADA PRINCIPAL) ===
        self._desenhar_petalas(sprite, cx, cy, abertura)
        
        # === MIOLO (CAMADA DE FRENTE) ===
        self._desenhar_miolo(sprite, cx, cy, pulso)
        
        return sprite
    
    def _desenhar_petalas(self, sprite: pygame.Surface, cx: int, cy: int, abertura: float):
        """Desenha pétalas da rosa com animação de abertura e rotação horária"""
        # Raio base das pétalas
        raio_base = 18
        raio_ponta = 45 + int(abertura * 15)  # Pétalas se estendem ao abrir (45-60px)
        
        # Largura das pétalas (MAIS GROSSAS)
        largura_base = 28  # Aumentado de 18 para 28
        largura_ponta = 20  # Aumentado de 12 para 20
        
        # Desenha cada pétala
        for i in range(self.num_petalas):
            # Ângulo da pétala
            angulo = (i / self.num_petalas) * 2 * math.pi
            
            # Adiciona rotação horária contínua
            angulo_final = angulo + math.radians(self.angulo_rotacao_petalas)
            
            # Calcula pontos da pétala
            # Base (próxima ao miolo)
            base_x = cx + math.cos(angulo_final) * raio_base
            base_y = cy + math.sin(angulo_final) * raio_base
            
            # Ponta (extremidade da pétala)
            ponta_x = cx + math.cos(angulo_final) * raio_ponta
            ponta_y = cy + math.sin(angulo_final) * raio_ponta
            
            # Laterais da pétala (formato de gota mais larga)
            angulo_perp = angulo_final + math.pi / 2
            
            # Base esquerda
            base_esq_x = base_x + math.cos(angulo_perp) * (largura_base / 2)
            base_esq_y = base_y + math.sin(angulo_perp) * (largura_base / 2)
            
            # Base direita
            base_dir_x = base_x - math.cos(angulo_perp) * (largura_base / 2)
            base_dir_y = base_y - math.sin(angulo_perp) * (largura_base / 2)
            
            # Ponta esquerda
            ponta_esq_x = ponta_x + math.cos(angulo_perp) * (largura_ponta / 2)
            ponta_esq_y = ponta_y + math.sin(angulo_perp) * (largura_ponta / 2)
            
            # Ponta direita
            ponta_dir_x = ponta_x - math.cos(angulo_perp) * (largura_ponta / 2)
            ponta_dir_y = ponta_y - math.sin(angulo_perp) * (largura_ponta / 2)
            
            # Pontos da pétala (formato de gota robusta)
            pontos_petala = [
                (base_esq_x, base_esq_y),
                (ponta_esq_x, ponta_esq_y),
                (ponta_x, ponta_y),  # Ponta afiada
                (ponta_dir_x, ponta_dir_y),
                (base_dir_x, base_dir_y)
            ]
            
            # Gradiente de cor (pétalas alternadas em grupos de 3)
            grupo = i % 3
            if grupo == 0:
                cor_petala = Paleta.VERMELHO_SANGUE
                cor_borda = Paleta.VERMELHO_ESCURO
                cor_detalhe = Paleta.ROSA_INTENSO
            elif grupo == 1:
                cor_petala = Paleta.ROSA_INTENSO
                cor_borda = Paleta.VERMELHO_SANGUE
                cor_detalhe = Paleta.ROSA_CLARO
            else:
                cor_petala = Paleta.VERMELHO_ESCURO
                cor_borda = Paleta.VERMELHO_SANGUE
                cor_detalhe = Paleta.ROSA_INTENSO
            
            # Desenha pétala
            pygame.draw.polygon(sprite, cor_petala, pontos_petala)
            
            # Borda da pétala (mais grossa)
            pygame.draw.polygon(sprite, cor_borda, pontos_petala, 3)
            
            # Nervura central da pétala (mais grossa)
            pygame.draw.line(sprite, cor_detalhe,
                           (base_x, base_y), (ponta_x, ponta_y), 3)
            
            # Nervuras laterais (detalhes) - mais nervuras para pétalas maiores
            for j in range(4):  # 4 nervuras laterais
                offset = (j + 1) / 5
                meio_x = base_x + (ponta_x - base_x) * offset
                meio_y = base_y + (ponta_y - base_y) * offset
                
                # Nervura esquerda
                nerv_esq_x = meio_x + math.cos(angulo_perp) * 8
                nerv_esq_y = meio_y + math.sin(angulo_perp) * 8
                pygame.draw.line(sprite, cor_detalhe,
                               (meio_x, meio_y), (nerv_esq_x, nerv_esq_y), 2)
                
                # Nervura direita
                nerv_dir_x = meio_x - math.cos(angulo_perp) * 8
                nerv_dir_y = meio_y - math.sin(angulo_perp) * 8
                pygame.draw.line(sprite, cor_detalhe,
                               (meio_x, meio_y), (nerv_dir_x, nerv_dir_y), 2)
            
            # Ponta brilhante (rosa neon) - maior
            pygame.draw.circle(sprite, Paleta.ROSA_NEON,
                             (int(ponta_x), int(ponta_y)), 4)
    
    def _desenhar_miolo(self, sprite: pygame.Surface, cx: int, cy: int, pulso: int):
        """Desenha miolo pulsante da rosa"""
        # Raio do miolo (pulsante)
        raio_externo = 18 + pulso
        raio_medio = 14 + pulso
        raio_interno = 10
        
        # Círculo externo (laranja)
        pygame.draw.circle(sprite, Paleta.LARANJA_MIOLO, (cx, cy), raio_externo)
        
        # Círculo médio (dourado)
        pygame.draw.circle(sprite, Paleta.DOURADO, (cx, cy), raio_medio)
        
        # Círculo interno (amarelo pólen)
        pygame.draw.circle(sprite, Paleta.AMARELO_POLEN, (cx, cy), raio_interno)
        
        # Grãos de pólen (detalhes)
        num_graos = 12
        raio_graos = 8
        for i in range(num_graos):
            angulo = (i / num_graos) * 2 * math.pi + self.fase_pulsacao * 0.5
            grao_x = cx + math.cos(angulo) * raio_graos
            grao_y = cy + math.sin(angulo) * raio_graos
            
            tamanho_grao = 2 if i % 2 == 0 else 1
            pygame.draw.circle(sprite, Paleta.LARANJA_MIOLO,
                             (int(grao_x), int(grao_y)), tamanho_grao)
        
        # Brilho central
        pygame.draw.circle(sprite, (255, 255, 200), (cx - 3, cy - 3), 3)
    
    def _calcular_angulo_movimento(self) -> float:
        """Calcula ângulo baseado na direção de movimento"""
        if abs(self.vx) < 0.1 and abs(self.vy) < 0.1:
            return self.angulo_rotacao
        
        angulo_rad = math.atan2(-self.vy, self.vx)
        return math.degrees(angulo_rad)
    
    def _desenhar_particulas_energia(self, tela: pygame.Surface):
        """Renderiza partículas de energia"""
        for p in self.particulas_energia:
            tamanho = int(p.tamanho * p.vida)
            if tamanho > 0:
                pygame.draw.circle(tela, p.cor, 
                                 (int(p.x), int(p.y)), tamanho)
    
    def _desenhar_rastro(self, tela: pygame.Surface):
        """Renderiza rastro de pétalas"""
        for r in self.particulas_rastro:
            tamanho = max(1, int(r.tamanho * r.vida))
            cor_base = Paleta.VERMELHO_RASTRO if r.vida > 0.5 else Paleta.ROSA_RASTRO
            pygame.draw.circle(tela, cor_base, 
                             (int(r.x), int(r.y)), tamanho)
    
    def _desenhar_polens_explosivos(self, tela: pygame.Surface):
        """Renderiza pólen explosivo"""
        for polen in self.polens_explosivos:
            polen.renderizar(tela)
    
    def _desenhar_explosoes(self, tela: pygame.Surface):
        """Renderiza explosões"""
        for explosao in self.explosoes:
            explosao.renderizar(tela)
    
    def renderizar(self, tela: pygame.Surface):
        """Pipeline de renderização completo"""
        # 1. Explosões (fundo)
        self._desenhar_explosoes(tela)
        
        # 2. Pólen explosivo
        self._desenhar_polens_explosivos(tela)
        
        # 3. Rastro
        self._desenhar_rastro(tela)
        
        # 4. Partículas de energia
        if self.estado == EstadoRosaSanguinaria.CARREGANDO:
            self._desenhar_particulas_energia(tela)
        
        # 5. Sprite rotacionado
        sprite = self._criar_sprite_rosa()
        sprite_rotacionado = pygame.transform.rotate(sprite, self.angulo_rotacao)
        
        # Centraliza sprite
        rect = sprite_rotacionado.get_rect(center=(int(self.x), int(self.y)))
        tela.blit(sprite_rotacionado, rect)
        
        # 6. Debug
        fonte = pygame.font.Font(None, 20)
        texto = fonte.render(self.estado.value, True, (255, 255, 255))
        tela.blit(texto, (int(self.x) - 40, int(self.y) - 80))
    
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
    # MOTOR DE PARTÍCULAS E PÓLEN EXPLOSIVO
    # ========================================================================
    
    def _gerar_polen_explosivo(self):
        """Gera pólen explosivo na posição atual"""
        # Gera 4 pólens em posições ligeiramente aleatórias
        for _ in range(4):
            offset_x = random.uniform(-8, 8)
            offset_y = random.uniform(-8, 8)
            
            polen = PolenExplosivo(
                x=self.x + offset_x,
                y=self.y + offset_y,
                tempo_vida=2.0,  # 2 segundos até explodir
                tamanho=random.uniform(4, 7),
                fase_pulsacao=random.uniform(0, math.pi * 2)
            )
            self.polens_explosivos.append(polen)
    
    def _atualizar_polens_explosivos(self, dt: float):
        """Atualiza pólen e cria explosões"""
        polens_para_remover = []
        
        for polen in self.polens_explosivos:
            deve_explodir = polen.atualizar(dt)
            
            if deve_explodir:
                # Cria explosão
                explosao = ExplosaoPolem(
                    x=polen.x,
                    y=polen.y,
                    raio=0,
                    raio_max=80,  # Raio máximo da explosão
                    vida=1.0
                )
                self.explosoes.append(explosao)
                polens_para_remover.append(polen)
                
                # LIMPA COMPLETAMENTE O RASTRO ROSA quando pólen explode
                # Remove TODAS as partículas de rastro (não apenas próximas)
                self.particulas_rastro.clear()
        
        # Remove pólen que explodiu
        for polen in polens_para_remover:
            self.polens_explosivos.remove(polen)
    
    def _atualizar_explosoes(self, dt: float):
        """Atualiza explosões"""
        self.explosoes = [
            exp for exp in self.explosoes
            if exp.atualizar(dt)
        ]
    
    def _verificar_distancia_percorrida(self):
        """Verifica se percorreu 5 pixels e gera pólen"""
        dx = self.x - self.ultima_pos_x
        dy = self.y - self.ultima_pos_y
        dist = math.hypot(dx, dy)
        
        self.distancia_percorrida += dist
        
        # A cada 5 pixels, gera pólen
        if self.distancia_percorrida >= 5:
            self._gerar_polen_explosivo()
            self.distancia_percorrida = 0
        
        # Atualiza última posição
        self.ultima_pos_x = self.x
        self.ultima_pos_y = self.y
    
    def _gerar_particulas_carregamento(self):
        """Gera partículas de energia (pétalas de energia)"""
        for _ in range(3):
            angulo = random.uniform(0, 2 * math.pi)
            raio = random.uniform(80, 150)
            
            px = self.x + math.cos(angulo) * raio
            py = self.y + math.sin(angulo) * raio
            
            vx = random.uniform(-50, 50)
            vy = random.uniform(-50, 50)
            
            cor = random.choice([Paleta.VERMELHO_ENERGIA, Paleta.ROSA_ENERGIA])
            
            particula = ParticulaEnergia(
                x=px, y=py, vx=vx, vy=vy,
                vida=1.0, tamanho=random.uniform(3, 6), cor=cor
            )
            self.particulas_energia.append(particula)
    
    def _gerar_rastro(self):
        """Gera rastro de pétalas durante ataque"""
        rastro_x = self.x - self.vx * 0.05
        rastro_y = self.y - self.vy * 0.05
        
        for _ in range(2):
            offset_x = random.uniform(-10, 10)
            offset_y = random.uniform(-10, 10)
            
            particula = ParticulaRastro(
                x=rastro_x + offset_x,
                y=rastro_y + offset_y,
                tamanho=random.uniform(6, 14),
                vida=1.0,
                cor=Paleta.VERMELHO_RASTRO
            )
            self.particulas_rastro.append(particula)
    
    # ========================================================================
    # MÁQUINA DE ESTADOS
    # ========================================================================
    
    def _atualizar_repousando(self, dt: float):
        """Estado: REPOUSANDO"""
        self.fase_pulsacao += dt * 3
        self.fase_petalas += dt * 2  # Pétalas respirando suavemente
        
        # Rotação horária lenta
        self.angulo_rotacao_petalas += self.velocidade_rotacao_petalas * dt * 0.3
        if self.angulo_rotacao_petalas >= 360:
            self.angulo_rotacao_petalas -= 360
        
        self.x = self.origem_x
        self.y = self.origem_y
        
        # LIMPA RASTRO ROSA quando está repousando
        # Rastro desaparece rapidamente
        self.particulas_rastro = [
            r for r in self.particulas_rastro 
            if r.atualizar(dt)
        ]
    
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
        
        self.fase_pulsacao += dt * 10  # Pulsação intensa
        self.fase_petalas += dt * self.velocidade_petalas  # Pétalas abrindo
        
        # Rotação horária rápida durante carregamento
        self.angulo_rotacao_petalas += self.velocidade_rotacao_petalas * dt * 2
        if self.angulo_rotacao_petalas >= 360:
            self.angulo_rotacao_petalas -= 360
        
        if self.tempo_estado >= DURACAO_CARREGAMENTO:
            self.estado = EstadoRosaSanguinaria.ATACANDO
            self.tempo_estado = 0.0
            self.particulas_energia.clear()
    
    def _atualizar_atacando(self, dt: float):
        """Estado: ATACANDO"""
        self._gerar_rastro()
        
        chegou = self._mover_para_alvo(dt, VELOCIDADE_ATAQUE)
        
        # Verifica distância percorrida e gera pólen
        self._verificar_distancia_percorrida()
        
        # Atualiza ângulo
        self.angulo_rotacao = self._calcular_angulo_movimento()
        
        # Pétalas totalmente abertas e girando muito rápido
        self.fase_petalas += dt * self.velocidade_petalas * 2
        
        # Rotação horária muito rápida durante ataque
        self.angulo_rotacao_petalas += self.velocidade_rotacao_petalas * dt * 4
        if self.angulo_rotacao_petalas >= 360:
            self.angulo_rotacao_petalas -= 360
        
        self.particulas_rastro = [
            r for r in self.particulas_rastro 
            if r.atualizar(dt)
        ]
        
        if chegou:
            # CRÍTICO: Rosa fica no ponto Y (colisão)
            # O ponto Y se torna a nova origem X
            self.origem_x = self.x
            self.origem_y = self.y
            
            # Muda para estado REPOUSANDO (não RETORNANDO)
            # Rosa fica girando no local esperando próximo ataque
            self.estado = EstadoRosaSanguinaria.REPOUSANDO
            self.tempo_estado = 0.0
    
    def _atualizar_retornando(self, dt: float):
        """Estado: RETORNANDO"""
        chegou = self._mover_para_alvo(dt, VELOCIDADE_RETORNO)
        
        # Atualiza ângulo
        self.angulo_rotacao = self._calcular_angulo_movimento()
        
        # Pétalas fechando gradualmente
        self.fase_petalas += dt * self.velocidade_petalas
        
        # Rotação horária moderada durante retorno
        self.angulo_rotacao_petalas += self.velocidade_rotacao_petalas * dt
        if self.angulo_rotacao_petalas >= 360:
            self.angulo_rotacao_petalas -= 360
        
        self.particulas_rastro = [
            r for r in self.particulas_rastro 
            if r.atualizar(dt)
        ]
        
        self.fase_pulsacao += dt * 2
        
        if chegou:
            self.estado = EstadoRosaSanguinaria.REPOUSANDO
            self.tempo_estado = 0.0
    
    def atualizar(self, dt: float):
        """Loop principal"""
        # Atualiza pólen explosivo e explosões
        self._atualizar_polens_explosivos(dt)
        self._atualizar_explosoes(dt)
        
        if self.estado == EstadoRosaSanguinaria.REPOUSANDO:
            self._atualizar_repousando(dt)
        elif self.estado == EstadoRosaSanguinaria.CARREGANDO:
            self._atualizar_carregando(dt)
        elif self.estado == EstadoRosaSanguinaria.ATACANDO:
            self._atualizar_atacando(dt)
        elif self.estado == EstadoRosaSanguinaria.RETORNANDO:
            self._atualizar_retornando(dt)
    
    # ========================================================================
    # API PÚBLICA
    # ========================================================================
    
    def iniciar_ataque(self, alvo_x: float, alvo_y: float):
        """Inicia ataque"""
        if self.estado != EstadoRosaSanguinaria.REPOUSANDO:
            return False
        
        dist = math.hypot(alvo_x - self.origem_x, alvo_y - self.origem_y)
        if dist < DISTANCIA_MINIMA_ALVO:
            return False
        
        self.alvo_x = alvo_x
        self.alvo_y = alvo_y
        self.estado = EstadoRosaSanguinaria.CARREGANDO
        self.tempo_estado = 0.0
        
        # Calcula ângulo inicial
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
    
    def obter_explosoes_ativas(self) -> List[ExplosaoPolem]:
        """Retorna lista de explosões ativas para detecção de colisão"""
        return self.explosoes
    
    def obter_polens_ativos(self) -> List[PolenExplosivo]:
        """Retorna lista de pólen ativo"""
        return self.polens_explosivos

# ============================================================================
# DEMONSTRAÇÃO
# ============================================================================
def main():
    pygame.init()
    
    LARGURA = 1920
    ALTURA = 1080
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("ROSA SANGUINÁRIA @ 100 FPS")
    
    clock = pygame.time.Clock()
    
    rosa = RosaSanguinaria(LARGURA // 4, ALTURA // 2)
    
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
                rosa.iniciar_ataque(alvo_x, alvo_y)
            
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_SPACE:
                    rosa.iniciar_ataque(alvo_x, alvo_y)
        
        rosa.atualizar(dt)
        
        tela.fill(Paleta.VAZIO_ESPACIAL)
        
        # Desenha alvo
        pygame.draw.circle(tela, (100, 255, 100), (int(alvo_x), int(alvo_y)), 10, 2)
        pygame.draw.line(tela, (100, 255, 100), 
                        (int(alvo_x) - 15, int(alvo_y)), 
                        (int(alvo_x) + 15, int(alvo_y)), 2)
        pygame.draw.line(tela, (100, 255, 100), 
                        (int(alvo_x), int(alvo_y) - 15), 
                        (int(alvo_x), int(alvo_y) + 15), 2)
        
        rosa.renderizar(tela)
        
        # HUD
        fonte = pygame.font.Font(None, 30)
        fps_texto = fonte.render(f"FPS: {int(clock.get_fps())}", True, (0, 255, 0))
        angulo_texto = fonte.render(f"Ângulo: {int(rosa.angulo_rotacao)}°", True, (255, 100, 150))
        rotacao_texto = fonte.render(f"Rotação Pétalas: {int(rosa.angulo_rotacao_petalas)}°", True, (255, 150, 200))
        petalas_texto = fonte.render(f"Pétalas: {rosa.num_petalas}", True, (255, 200, 100))
        polen_texto = fonte.render(f"Pólen Ativo: {len(rosa.polens_explosivos)}", True, (255, 255, 100))
        explosoes_texto = fonte.render(f"Explosões: {len(rosa.explosoes)}", True, (255, 100, 100))
        instrucoes = fonte.render("ESPAÇO: Atacar | CLIQUE: Definir Alvo", True, (255, 255, 255))
        
        tela.blit(fps_texto, (10, 10))
        tela.blit(angulo_texto, (10, 40))
        tela.blit(rotacao_texto, (10, 70))
        tela.blit(petalas_texto, (10, 100))
        tela.blit(polen_texto, (10, 130))
        tela.blit(explosoes_texto, (10, 160))
        tela.blit(instrucoes, (10, 190))
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
