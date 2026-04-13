"""
Sistema de Ratos da Umbra - Ruptura Temporal
=============================================
Mecânica de habilidade do boss que invoca ratos perseguidores.

Características:
- Spawn nos 4 cantos do mapa
- Perseguem o jogador (Apolo)
- Imunes a dano
- Tempo de vida: 5 segundos
- Cooldown: 15 segundos
- Buff permanente: +1 rato por hit bem-sucedido
"""

import pygame
import math
import time


class Rato:
    """
    Representa um rato individual invocado pela Umbra.
    
    Atributos:
        rect (pygame.Rect): Hitbox do rato
        velocidade (float): Velocidade de movimento
        tempo_criacao (float): Timestamp de criação
        tempo_vida (float): Tempo máximo de vida em milissegundos
        cor (tuple): Cor RGB do placeholder
        tamanho (int): Tamanho do quadrado
    """
    
    def __init__(self, x, y, tempo_atual, velocidade=3.5, tempo_vida=5000):
        """
        Inicializa um rato.
        
        Args:
            x (int): Posição X inicial
            y (int): Posição Y inicial
            tempo_atual (int): Timestamp atual em milissegundos
            velocidade (float): Velocidade de movimento (padrão: 3.5)
            tempo_vida (int): Tempo de vida em milissegundos
        """
        self.tamanho = 30
        self.rect = pygame.Rect(x - self.tamanho // 2, y - self.tamanho // 2, 
                                self.tamanho, self.tamanho)
        self.velocidade = velocidade
        self.tempo_criacao = tempo_atual
        self.tempo_vida = tempo_vida
        self.cor = (50, 100, 255)  # Azul placeholder
        self.cor_borda = (100, 150, 255)  # Azul claro para borda
        
        # Posição em float para movimento suave
        self.pos_x = float(x)
        self.pos_y = float(y)
    
    def atualizar(self, alvo_x, alvo_y, tempo_atual):
        """
        Atualiza a posição do rato, movendo-o em direção ao alvo.
        
        Args:
            alvo_x (int): Posição X do alvo (Apolo)
            alvo_y (int): Posição Y do alvo (Apolo)
            tempo_atual (int): Timestamp atual em milissegundos
            
        Returns:
            bool: True se o rato ainda está vivo, False se expirou
        """
        # Verifica se o tempo de vida expirou
        if tempo_atual - self.tempo_criacao >= self.tempo_vida:
            return False  # Rato "explode" (desaparece)
        
        # Calcula direção para o alvo
        dx = alvo_x - self.pos_x
        dy = alvo_y - self.pos_y
        distancia = math.hypot(dx, dy)
        
        # Move em direção ao alvo se não estiver em cima dele
        if distancia > 0:
            # Normaliza e aplica velocidade
            dx_norm = (dx / distancia) * self.velocidade
            dy_norm = (dy / distancia) * self.velocidade
            
            self.pos_x += dx_norm
            self.pos_y += dy_norm
            
            # Atualiza rect para colisão
            self.rect.x = int(self.pos_x - self.tamanho // 2)
            self.rect.y = int(self.pos_y - self.tamanho // 2)
        
        return True  # Rato ainda está vivo
    
    def desenhar(self, tela, tempo_atual):
        """
        Renderiza o rato na tela com efeitos visuais.
        
        Args:
            tela (pygame.Surface): Superfície onde desenhar
            tempo_atual (int): Timestamp atual para animações
        """
        # Efeito de pulso baseado no tempo de vida restante
        tempo_restante = self.tempo_vida - (tempo_atual - self.tempo_criacao)
        percentual_vida = tempo_restante / self.tempo_vida
        
        # Piscar nos últimos 2 segundos
        if tempo_restante < 2000:
            if (tempo_atual // 150) % 2 == 0:
                cor_atual = (255, 100, 100)  # Vermelho quando piscando
            else:
                cor_atual = self.cor
        else:
            cor_atual = self.cor
        
        # Desenha sombra
        sombra_rect = self.rect.copy()
        sombra_rect.x += 3
        sombra_rect.y += 3
        pygame.draw.rect(tela, (0, 0, 0, 100), sombra_rect)
        
        # Desenha corpo do rato
        pygame.draw.rect(tela, cor_atual, self.rect)
        
        # Desenha borda
        pygame.draw.rect(tela, self.cor_borda, self.rect, 2)
        
        # Desenha indicador de tempo de vida (barra no topo)
        barra_largura = int(self.tamanho * percentual_vida)
        barra_rect = pygame.Rect(self.rect.x, self.rect.y - 5, barra_largura, 3)
        cor_barra = (0, 255, 0) if percentual_vida > 0.5 else (255, 255, 0) if percentual_vida > 0.2 else (255, 0, 0)
        pygame.draw.rect(tela, cor_barra, barra_rect)
    
    def colidiu_com_jogador(self, jogador_rect):
        """
        Verifica colisão com o jogador.
        
        Args:
            jogador_rect (pygame.Rect): Hitbox do jogador
            
        Returns:
            bool: True se colidiu, False caso contrário
        """
        return self.rect.colliderect(jogador_rect)


class GerenciadorRatos:
    """
    Gerencia o sistema de spawn, atualização e colisão dos ratos.
    
    Atributos:
        ratos (list): Lista de ratos ativos
        cooldown (int): Tempo de cooldown em milissegundos
        ultimo_spawn (int): Timestamp do último spawn
        ratos_extras (int): Contador de ratos extras (buff permanente)
        ratos_base (int): Quantidade base de ratos por spawn
        dano_rato (int): Dano causado ao jogador por colisão
        cura_umbra_percentual (float): Percentual de cura da Umbra por hit
    """
    
    def __init__(self, largura_mapa, altura_mapa):
        """
        Inicializa o gerenciador de ratos.
        
        Args:
            largura_mapa (int): Largura do mapa
            altura_mapa (int): Altura do mapa
        """
        self.ratos = []
        self.cooldown = 15000  # 15 segundos em milissegundos
        self.ultimo_spawn = 0
        self.ratos_extras = 0  # Buff permanente: +1 por hit
        self.ratos_base = 1  # 1 rato por canto = 4 ratos totais
        
        # Configurações de dano e cura
        self.dano_rato = 80  # Dano causado ao Apolo
        self.cura_umbra_percentual = 0.04  # 4% da vida máxima da Umbra
        
        # Dimensões do mapa
        self.largura_mapa = largura_mapa
        self.altura_mapa = altura_mapa
        
        # Posições dos 4 cantos do mapa (com margem de 50 pixels)
        margem = 50
        self.cantos = [
            (margem, margem),  # Canto superior esquerdo
            (largura_mapa - margem, margem),  # Canto superior direito
            (margem, altura_mapa - margem),  # Canto inferior esquerdo
            (largura_mapa - margem, altura_mapa - margem)  # Canto inferior direito
        ]
    
    def pode_spawnar(self, tempo_atual):
        """
        Verifica se pode spawnar novos ratos.
        
        Args:
            tempo_atual (int): Timestamp atual em milissegundos
            
        Returns:
            bool: True se o cooldown passou, False caso contrário
        """
        return tempo_atual - self.ultimo_spawn >= self.cooldown
    
    def spawnar_ratos(self, tempo_atual):
        """
        Spawna ratos nos 4 cantos do mapa.
        
        Args:
            tempo_atual (int): Timestamp atual em milissegundos
            
        Returns:
            int: Quantidade total de ratos spawnados
        """
        if not self.pode_spawnar(tempo_atual):
            return 0
        
        # Calcula quantidade total de ratos por canto
        ratos_por_canto = self.ratos_base + self.ratos_extras
        total_spawnado = 0
        
        # Spawna ratos em cada canto
        for canto_x, canto_y in self.cantos:
            for i in range(ratos_por_canto):
                # Adiciona pequena variação na posição para não spawnar todos no mesmo lugar
                offset_x = (i % 2) * 20 - 10
                offset_y = (i // 2) * 20 - 10
                
                rato = Rato(
                    canto_x + offset_x,
                    canto_y + offset_y,
                    tempo_atual,
                    velocidade=3.5 + (self.ratos_extras * 0.15)  # Velocidade aumenta com buff (mais lento)
                )
                self.ratos.append(rato)
                total_spawnado += 1
        
        self.ultimo_spawn = tempo_atual
        return total_spawnado
    
    def atualizar(self, tempo_atual, apolo_x, apolo_y):
        """
        Atualiza todos os ratos ativos.
        
        Args:
            tempo_atual (int): Timestamp atual em milissegundos
            apolo_x (int): Posição X do Apolo (centro)
            apolo_y (int): Posição Y do Apolo (centro)
        """
        # Atualiza cada rato e remove os que expiraram
        ratos_vivos = []
        for rato in self.ratos:
            if rato.atualizar(apolo_x, apolo_y, tempo_atual):
                ratos_vivos.append(rato)
        
        self.ratos = ratos_vivos
    
    def desenhar(self, tela, tempo_atual):
        """
        Desenha todos os ratos na tela.
        
        Args:
            tela (pygame.Surface): Superfície onde desenhar
            tempo_atual (int): Timestamp atual
        """
        for rato in self.ratos:
            rato.desenhar(tela, tempo_atual)
    
    def verificar_colisoes(self, apolo_rect, vida_umbra, vida_maxima_umbra):
        """
        Verifica colisões entre ratos e o jogador.
        
        Args:
            apolo_rect (pygame.Rect): Hitbox do Apolo
            vida_umbra (int): Vida atual da Umbra
            vida_maxima_umbra (int): Vida máxima da Umbra
            
        Returns:
            dict: Dicionário com resultados das colisões
                {
                    'hits': int,  # Quantidade de ratos que acertaram
                    'dano_total': int,  # Dano total causado ao Apolo
                    'cura_umbra': int,  # Cura total da Umbra
                    'vida_umbra_nova': int  # Nova vida da Umbra
                }
        """
        hits = 0
        dano_total = 0
        cura_total = 0
        ratos_sobreviventes = []
        
        for rato in self.ratos:
            if rato.colidiu_com_jogador(apolo_rect):
                # Rato acertou o Apolo
                hits += 1
                dano_total += self.dano_rato
                
                # Umbra regenera 4% da vida máxima
                cura = int(vida_maxima_umbra * self.cura_umbra_percentual)
                cura_total += cura
                
                # Buff permanente: +1 rato extra no próximo spawn
                self.ratos_extras += 1
                
                # Rato desaparece após acertar (não adiciona à lista de sobreviventes)
            else:
                # Rato não colidiu, continua vivo
                ratos_sobreviventes.append(rato)
        
        # Atualiza lista de ratos
        self.ratos = ratos_sobreviventes
        
        # Calcula nova vida da Umbra (com limite na vida máxima)
        vida_umbra_nova = min(vida_maxima_umbra, vida_umbra + cura_total)
        
        return {
            'hits': hits,
            'dano_total': dano_total,
            'cura_umbra': cura_total,
            'vida_umbra_nova': vida_umbra_nova
        }
    
    def resetar_partida(self):
        """
        Reseta o sistema para uma nova partida.
        Remove todos os ratos e zera o contador de ratos extras.
        """
        self.ratos.clear()
        self.ratos_extras = 0
        self.ultimo_spawn = 0
    
    def obter_info_debug(self):
        """
        Retorna informações de debug do sistema.
        
        Returns:
            dict: Informações do sistema
        """
        return {
            'ratos_ativos': len(self.ratos),
            'ratos_extras': self.ratos_extras,
            'ratos_proximo_spawn': self.ratos_base + self.ratos_extras,
            'total_proximo_spawn': (self.ratos_base + self.ratos_extras) * 4
        }


# ============================================================================
# EXEMPLO DE INTEGRAÇÃO NO GAME LOOP (GAME5.py)
# ============================================================================

"""
# 1. INICIALIZAÇÃO (antes do loop principal)
# ------------------------------------------

from sistema_ratos_umbra import GerenciadorRatos

# Criar gerenciador de ratos
gerenciador_ratos = GerenciadorRatos(largura_mapa, altura_mapa)


# 2. NO LOOP PRINCIPAL (dentro do while running:)
# ------------------------------------------------

# Obter tempo atual
tempo_atual = pygame.time.get_ticks()

# Calcular centro do Apolo
apolo_centro_x = pos_x_personagem + largura_personagem // 2
apolo_centro_y = pos_y_personagem + altura_personagem // 2

# Spawnar ratos automaticamente quando cooldown passar
if gerenciador_ratos.pode_spawnar(tempo_atual):
    qtd_spawnada = gerenciador_ratos.spawnar_ratos(tempo_atual)
    if qtd_spawnada > 0:
        print(f"[UMBRA] Invocou {qtd_spawnada} ratos!")

# Atualizar posição de todos os ratos
gerenciador_ratos.atualizar(tempo_atual, apolo_centro_x, apolo_centro_y)

# Verificar colisões com o Apolo
personagem_rect = pygame.Rect(pos_x_personagem, pos_y_personagem, 
                               largura_personagem, altura_personagem)

resultado_colisoes = gerenciador_ratos.verificar_colisoes(
    personagem_rect, 
    vida_umbra, 
    vida_maxima_umbra
)

# Aplicar dano ao Apolo
if resultado_colisoes['hits'] > 0:
    vida -= resultado_colisoes['dano_total']
    vida_umbra = resultado_colisoes['vida_umbra_nova']
    
    print(f"[RATO HIT] {resultado_colisoes['hits']} ratos acertaram!")
    print(f"[APOLO] Dano: -{resultado_colisoes['dano_total']}")
    print(f"[UMBRA] Cura: +{resultado_colisoes['cura_umbra']}")
    print(f"[BUFF] Próximo spawn: {gerenciador_ratos.ratos_extras} ratos extras")

# Desenhar ratos na tela (APÓS desenhar o mapa, ANTES de desenhar o Apolo)
gerenciador_ratos.desenhar(tela, tempo_atual)


# 3. RESET DE PARTIDA (quando o jogo reinicia)
# ---------------------------------------------

# Quando Apolo ou Umbra morrem e o jogo reinicia:
gerenciador_ratos.resetar_partida()


# 4. DEBUG INFO (opcional - para mostrar na tela)
# ------------------------------------------------

info = gerenciador_ratos.obter_info_debug()
fonte_debug = pygame.font.Font(None, 24)
texto_debug = fonte_debug.render(
    f"Ratos: {info['ratos_ativos']} | Extras: {info['ratos_extras']} | Próximo: {info['total_proximo_spawn']}", 
    True, (255, 255, 255)
)
tela.blit(texto_debug, (10, 50))
"""
