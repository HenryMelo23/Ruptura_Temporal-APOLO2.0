"""
ENXAME PARASITA - Habilidade Otimizada da Umbra
Substitui "Bordas Tóxicas" com performance superior

Mecânica:
- Ratos/Sombras perseguem o player por 5 segundos
- 3 tipos de IA leve (Direto, Predição, Ziguezague)
- Lifesteal: Dano ao player cura a Umbra
- Sistema de Bonus: +1 rato por acerto (máximo 5 ratos)
- Compatível com DQN do Apolo (inserido em projeteis_boss)

Autor: Engenheiro de Jogos Python
Otimizado para: 60+ FPS
"""

import math
import pygame
import random

# ============================================================================
# VARIÁVEIS GLOBAIS
# ============================================================================

lista_ratos = []  # Lista global de ratos ativos


# ============================================================================
# FUNÇÕES PRINCIPAIS
# ============================================================================

def invocar_enxame(agora, estado_ia, pos_umbra_x, pos_umbra_y, pos_player_x, pos_player_y, 
                   historico_player):
    """
    Invoca o Enxame Parasita ao redor da Umbra.
    
    Args:
        agora (int): Timestamp atual em ms
        estado_ia (dict): Estado da IA da Umbra
        pos_umbra_x (float): Posição X da Umbra
        pos_umbra_y (float): Posição Y da Umbra
        pos_player_x (float): Posição X do player
        pos_player_y (float): Posição Y do player
        historico_player (deque): Histórico de posições do player
    """
    global lista_ratos
    
    # Número de ratos: 2 base + bonus (máximo 5 total)
    ratos_bonus = estado_ia.get('ratos_bonus', 0)
    num_ratos = min(5, 2 + ratos_bonus)  # Limite de 5 para performance
    
    # Centro da Umbra
    centro_umbra_x = pos_umbra_x + 50  # Ajuste para centro do boss
    centro_umbra_y = pos_umbra_y + 50
    
    # Calcular velocidade do player (para predição)
    velocidade_player_x = 0
    velocidade_player_y = 0
    if len(historico_player) >= 2:
        velocidade_player_x = pos_player_x - historico_player[-2][0]
        velocidade_player_y = pos_player_y - historico_player[-2][1]
    
    # Invocar ratos em círculo ao redor da Umbra
    for i in range(num_ratos):
        # Posição inicial em círculo
        angulo = (2 * math.pi * i) / num_ratos
        raio_spawn = 80  # Distância da Umbra
        
        rato_x = centro_umbra_x + math.cos(angulo) * raio_spawn
        rato_y = centro_umbra_y + math.sin(angulo) * raio_spawn
        
        # Determinar tipo de IA (distribuição equilibrada)
        tipo = i % 3  # 0=Direto, 1=Predição, 2=Ziguezague
        
        # Criar rato
        rato = {
            'x': rato_x,
            'y': rato_y,
            'tipo': tipo,
            'velocidade': 4.5,  # Velocidade base
            'tempo_nascimento': agora,
            'ttl': 5000,  # 5 segundos de vida
            'tamanho': 12,  # Tamanho da hitbox
            'angulo_zigzag': random.uniform(0, 2 * math.pi),  # Para tipo 2
            # Dados para predição (tipo 1)
            'alvo_pred_x': pos_player_x + (velocidade_player_x * 10),
            'alvo_pred_y': pos_player_y + (velocidade_player_y * 10)
        }
        
        lista_ratos.append(rato)
    
    # Atualizar estado da IA
    estado_ia['ultimo_enxame'] = agora
    
    # Log de invocação
    print(f"[ENXAME] {num_ratos} ratos invocados (bonus: {ratos_bonus})")


def atualizar_ratos(agora, pos_player_x, pos_player_y, estado_ia, projeteis_boss):
    """
    Atualiza posição e comportamento dos ratos.
    Remove ratos expirados (TTL).
    Insere ratos em projeteis_boss para compatibilidade com DQN.
    
    Args:
        agora (int): Timestamp atual em ms
        pos_player_x (float): Posição X do player
        pos_player_y (float): Posição Y do player
        estado_ia (dict): Estado da IA da Umbra
        projeteis_boss (list): Lista de projéteis da Umbra (para DQN)
    
    Returns:
        list: Lista de ratos ainda vivos
    """
    global lista_ratos
    
    ratos_vivos = []
    
    for rato in lista_ratos:
        # Verificar TTL (Time To Live)
        idade = agora - rato['tempo_nascimento']
        if idade >= rato['ttl']:
            continue  # Rato expirou, não adiciona à lista de vivos
        
        # ===== COMPORTAMENTO POR TIPO =====
        
        if rato['tipo'] == 0:
            # TIPO 0: DIRETO (vetor simples)
            dx = pos_player_x - rato['x']
            dy = pos_player_y - rato['y']
            dist = math.hypot(dx, dy)
            
            if dist > 0:
                rato['x'] += (dx / dist) * rato['velocidade']
                rato['y'] += (dy / dist) * rato['velocidade']
        
        elif rato['tipo'] == 1:
            # TIPO 1: PREDIÇÃO (mira na posição futura)
            dx = rato['alvo_pred_x'] - rato['x']
            dy = rato['alvo_pred_y'] - rato['y']
            dist = math.hypot(dx, dy)
            
            if dist > 0:
                rato['x'] += (dx / dist) * rato['velocidade']
                rato['y'] += (dy / dist) * rato['velocidade']
            
            # Atualizar alvo de predição a cada frame (suavizado)
            rato['alvo_pred_x'] = rato['alvo_pred_x'] * 0.95 + pos_player_x * 0.05
            rato['alvo_pred_y'] = rato['alvo_pred_y'] * 0.95 + pos_player_y * 0.05
        
        elif rato['tipo'] == 2:
            # TIPO 2: ZIGUEZAGUE (curva senoidal)
            dx = pos_player_x - rato['x']
            dy = pos_player_y - rato['y']
            dist = math.hypot(dx, dy)
            
            if dist > 0:
                # Vetor base em direção ao player
                vx_base = (dx / dist) * rato['velocidade']
                vy_base = (dy / dist) * rato['velocidade']
                
                # Adicionar componente perpendicular (ziguezague)
                rato['angulo_zigzag'] += 0.15  # Velocidade da oscilação
                offset_perpendicular = math.sin(rato['angulo_zigzag']) * 2.5
                
                # Vetor perpendicular (rotação 90°)
                vx_perp = -vy_base / rato['velocidade'] * offset_perpendicular
                vy_perp = vx_base / rato['velocidade'] * offset_perpendicular
                
                rato['x'] += vx_base + vx_perp
                rato['y'] += vy_base + vy_perp
        
        # ===== COMPATIBILIDADE COM DQN =====
        # Inserir rato como "projétil" para o Apolo enxergar
        rato_como_projetil = {
            'rect': pygame.Rect(
                int(rato['x'] - rato['tamanho'] / 2),
                int(rato['y'] - rato['tamanho'] / 2),
                rato['tamanho'],
                rato['tamanho']
            ),
            'x': rato['x'],
            'y': rato['y'],
            'tipo': 'enxame',  # Identificador especial
            'angulo': math.atan2(pos_player_y - rato['y'], pos_player_x - rato['x'])
        }
        
        # Adicionar à lista de projéteis (DQN verá como ameaça)
        projeteis_boss.append(rato_como_projetil)
        
        # Manter rato vivo
        ratos_vivos.append(rato)
    
    # Atualizar lista global
    lista_ratos = ratos_vivos
    
    return ratos_vivos


def verificar_colisao_ratos(pos_player_x, pos_player_y, largura_player, altura_player,
                            vida_umbra, vida_maxima_umbra, estado_ia, agora, efeitos_texto):
    """
    Verifica colisão dos ratos com o player.
    Aplica dano, cura a Umbra (lifesteal) e incrementa bonus.
    
    Args:
        pos_player_x (float): Posição X do player
        pos_player_y (float): Posição Y do player
        largura_player (int): Largura da hitbox do player
        altura_player (int): Altura da hitbox do player
        vida_umbra (float): Vida atual da Umbra
        vida_maxima_umbra (float): Vida máxima da Umbra
        estado_ia (dict): Estado da IA da Umbra
        agora (int): Timestamp atual em ms
        efeitos_texto (list): Lista de efeitos de texto flutuante
    
    Returns:
        tuple: (dano_causado, vida_umbra_atualizada)
    """
    global lista_ratos
    
    dano_total = 0
    cura_total = 0
    ratos_sobreviventes = []
    
    # Hitbox do player
    rect_player = pygame.Rect(pos_player_x, pos_player_y, largura_player, altura_player)
    
    for rato in lista_ratos:
        # Hitbox do rato
        rect_rato = pygame.Rect(
            int(rato['x'] - rato['tamanho'] / 2),
            int(rato['y'] - rato['tamanho'] / 2),
            rato['tamanho'],
            rato['tamanho']
        )
        
        # Verificar colisão
        if rect_player.colliderect(rect_rato):
            # DANO AO PLAYER
            dano = 15  # Dano fixo por rato
            dano_total += dano
            
            # CURA DA UMBRA (Lifesteal)
            cura = 15
            vida_umbra = min(vida_maxima_umbra, vida_umbra + cura)
            cura_total += cura
            
            # INCREMENTAR BONUS (máximo 5 ratos totais)
            ratos_bonus_atual = estado_ia.get('ratos_bonus', 0)
            if ratos_bonus_atual < 3:  # 2 base + 3 bonus = 5 total
                estado_ia['ratos_bonus'] = ratos_bonus_atual + 1
            
            # EFEITO VISUAL (Dano)
            efeitos_texto.append({
                "texto": f"-{dano} VENENO!",
                "x": pos_player_x + random.randint(-20, 20),
                "y": pos_player_y - 30,
                "tempo_inicio": agora,
                "cor": (180, 50, 200)  # Roxo venenoso
            })
            
            # EFEITO VISUAL (Cura da Umbra)
            efeitos_texto.append({
                "texto": f"+{cura} SIFÃO!",
                "x": rato['x'],
                "y": rato['y'] - 20,
                "tempo_inicio": agora,
                "cor": (50, 255, 150)  # Verde de cura
            })
            
            # Rato é destruído após colisão
            # (não adiciona à lista de sobreviventes)
        else:
            # Rato sobrevive
            ratos_sobreviventes.append(rato)
    
    # Atualizar lista global
    lista_ratos = ratos_sobreviventes
    
    return dano_total, vida_umbra


def renderizar_ratos(tela, agora):
    """
    Renderiza os ratos na tela com visual otimizado.
    
    Args:
        tela (pygame.Surface): Superfície de renderização
        agora (int): Timestamp atual em ms
    """
    global lista_ratos
    
    for rato in lista_ratos:
        # Calcular fade baseado no TTL restante
        idade = agora - rato['tempo_nascimento']
        vida_restante = rato['ttl'] - idade
        
        # Fade nos últimos 1000ms
        if vida_restante < 1000:
            alpha = int((vida_restante / 1000.0) * 255)
        else:
            alpha = 255
        
        # Posição central
        x = int(rato['x'])
        y = int(rato['y'])
        tamanho = rato['tamanho']
        
        # ===== RENDERIZAÇÃO OTIMIZADA =====
        
        # Criar surface com alpha
        s_rato = pygame.Surface((tamanho * 2, tamanho * 2), pygame.SRCALPHA)
        
        # Cor baseada no tipo
        if rato['tipo'] == 0:
            cor_base = (120, 40, 140)  # Roxo escuro (Direto)
        elif rato['tipo'] == 1:
            cor_base = (140, 40, 120)  # Roxo avermelhado (Predição)
        else:
            cor_base = (100, 40, 140)  # Roxo azulado (Ziguezague)
        
        # Pulso sutil
        pulso = math.sin(agora * 0.01 + rato['x']) * 2
        raio_atual = tamanho // 2 + int(pulso)
        
        # Sombra (offset)
        pygame.draw.circle(s_rato, (0, 0, 0, alpha // 2), 
                          (tamanho + 2, tamanho + 2), raio_atual)
        
        # Corpo principal
        pygame.draw.circle(s_rato, (*cor_base, alpha), 
                          (tamanho, tamanho), raio_atual)
        
        # Brilho central
        raio_brilho = max(2, raio_atual // 3)
        pygame.draw.circle(s_rato, (200, 150, 255, alpha), 
                          (tamanho - 2, tamanho - 2), raio_brilho)
        
        # Blit na tela
        tela.blit(s_rato, (x - tamanho, y - tamanho))
        
        # ===== TRAIL EFFECT (Rastro) =====
        # Apenas para tipo 2 (Ziguezague) para diferenciação visual
        if rato['tipo'] == 2 and alpha > 100:
            trail_alpha = alpha // 3
            trail_size = tamanho // 2
            s_trail = pygame.Surface((trail_size * 2, trail_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s_trail, (*cor_base, trail_alpha), 
                             (trail_size, trail_size), trail_size)
            tela.blit(s_trail, (x - trail_size - 5, y - trail_size))


def limpar_enxame():
    """Limpa todos os ratos (útil para reset de fase)."""
    global lista_ratos
    lista_ratos = []


def obter_num_ratos_ativos():
    """Retorna o número de ratos ativos."""
    global lista_ratos
    return len(lista_ratos)


# ============================================================================
# INTEGRAÇÃO COM HABILIDADE_BOSS.PY
# ============================================================================

def node_enxame_parasita(agora, estado_ia, pos_umbra_x, pos_umbra_y, 
                         pos_player_x, pos_player_y, historico_player):
    """
    Nódulo de decisão para invocar Enxame Parasita.
    Compatível com a arquitetura de habilidade_boss.py
    
    Args:
        agora (int): Timestamp atual
        estado_ia (dict): Estado da IA da Umbra
        pos_umbra_x (float): Posição X da Umbra
        pos_umbra_y (float): Posição Y da Umbra
        pos_player_x (float): Posição X do player
        pos_player_y (float): Posição Y do player
        historico_player (deque): Histórico de posições
    """
    invocar_enxame(agora, estado_ia, pos_umbra_x, pos_umbra_y, 
                   pos_player_x, pos_player_y, historico_player)
    
    estado_ia['ultimo_enxame'] = agora
    estado_ia['dano_recente'] = 0  # Reset de dano recente


# ============================================================================
# EXEMPLO DE USO NO LOOP PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    """
    Exemplo de integração no loop principal do jogo.
    """
    
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║                    ENXAME PARASITA - TESTE STANDALONE                   ║
    ║                                                                          ║
    ║  Habilidade otimizada para substituir Bordas Tóxicas                    ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Simulação de uso
    import time
    from collections import deque
    
    # Estado simulado
    agora = int(time.time() * 1000)
    estado_ia = {'ratos_bonus': 0}
    historico_player = deque(maxlen=60)
    
    # Posições simuladas
    pos_umbra_x, pos_umbra_y = 640, 360
    pos_player_x, pos_player_y = 400, 300
    
    # Invocar enxame
    print("\n[TESTE] Invocando enxame...")
    invocar_enxame(agora, estado_ia, pos_umbra_x, pos_umbra_y, 
                   pos_player_x, pos_player_y, historico_player)
    
    print(f"[TESTE] Ratos ativos: {obter_num_ratos_ativos()}")
    print(f"[TESTE] Bonus atual: {estado_ia.get('ratos_bonus', 0)}")
    
    # Simular atualização
    print("\n[TESTE] Simulando 10 frames...")
    for i in range(10):
        agora += 16  # ~60 FPS
        projeteis_boss = []
        ratos_vivos = atualizar_ratos(agora, pos_player_x, pos_player_y, 
                                       estado_ia, projeteis_boss)
        print(f"  Frame {i+1}: {len(ratos_vivos)} ratos vivos, "
              f"{len(projeteis_boss)} projéteis para DQN")
    
    print("\n[TESTE] Teste concluído!")
