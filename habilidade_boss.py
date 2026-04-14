import pygame
import math
import random
from Variaveis import espacamento, largura_mapa, altura_mapa, largura_personagem, altura_personagem, largura_boss, altura_boss
import json
import sys
import os
import json
import torch
import torch.nn as nn
import torch.optim as optim

class UmbraDQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(UmbraDQN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.LeakyReLU(),
            nn.Linear(128, 64),
            nn.LeakyReLU(),
            nn.Linear(64, output_size)
        )
    def forward(self, x):
        return self.net(x)

class MemoriaEvolutivaUmbra:
    def __init__(self, arquivo="memoria_umbra_dqn.pt"):
        self.arquivo = arquivo
        self.gamma = 0.95
        self.exploracao = 0.50
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.input_size = 18
        self.acoes_base = [
            "FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR", "ATAQUE", "SIFON", "TELEPORTE",
            "TRANSMUTAR_VORTICE", "TRANSMUTAR_GRAVIDADE", "TRANSMUTAR_NECROSE", 
            "TRANSMUTAR_RESSONANCIA", "TRANSMUTAR_HEMORRAGIA", "TRANSMUTAR_ATRITO", 
            "TRANSMUTAR_RASTRO", "VORTICE", "PRISAO", "MIASMA", "DESCARGA_ELETRICA", 
            "PRAGA_RATOS", "LASER_SOBRECARGA", "CAMINHO_ESPINHOS", "NENHUMA"
        ]
        self.output_size = len(self.acoes_base)
        
        self.q_network = UmbraDQN(self.input_size, self.output_size).to(self.device)
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()
        
        self.tendencias = {"TOTAL": 0, "ESQUERDA": 0, "DIREITA": 0, "CIMA": 0, "BAIXO": 0}
        self.ultimo_estado_tensor = None
        self.ultima_acao_idx = None
        
        self._carregar()

    def _carregar(self):
        if os.path.exists(self.arquivo):
            try:
                self.q_network.load_state_dict(torch.load(self.arquivo, map_location=self.device, weights_only=True))
            except:
                pass
        if os.path.exists("tendencias_umbra.json"):
            try:
                with open("tendencias_umbra.json", 'r') as f:
                    self.tendencias = json.load(f)
            except: pass

    def salvar(self):
        torch.save(self.q_network.state_dict(), self.arquivo)
        with open("tendencias_umbra.json", 'w') as f:
            json.dump(self.tendencias, f)

    def registrar_esquiva_player(self, vx, vy):
        t = self.tendencias
        if abs(vx) > 0.5 or abs(vy) > 0.5:
            if vx > 1: t["DIREITA"] += 1
            elif vx < -1: t["ESQUERDA"] += 1
            if vy > 1: t["BAIXO"] += 1
            elif vy < -1: t["CIMA"] += 1
            t["TOTAL"] += 1

    def calcular_bias_bayesiano(self):
        t = self.tendencias
        total = max(1, t["TOTAL"])
        bias_x = (t.get("DIREITA", 0) - t.get("ESQUERDA", 0)) / total
        bias_y = (t.get("BAIXO", 0) - t.get("CIMA", 0)) / total
        return bias_x, bias_y

    def discretizar_estado(self, vida_perc, dist_player, sob_fogo, historico_player, mapa_atual="Fase_Base", player_pos=None, boss_pos=None, armadilhas=None, ameaca_vec=(0.0, 0.0)):
        feat_vida = float(vida_perc)
        feat_dist = float(dist_player) / 2000.0 
        feat_fogo = 1.0 if sob_fogo else 0.0
        
        vx_p, vy_p = 0.0, 0.0
        if historico_player and len(historico_player) >= 3:
            p1, p3 = historico_player[-3], historico_player[-1]
            vx_p = (p3[0] - p1[0]) / 30.0
            vy_p = (p3[1] - p1[1]) / 30.0
            
        feat_vx = max(-1.0, min(1.0, vx_p))
        feat_vy = max(-1.0, min(1.0, vy_p))
        
        dx, dy = 0.0, 0.0
        if player_pos and boss_pos:
            px = player_pos[0] if isinstance(player_pos, (tuple, list)) else player_pos.get('x', 0)
            py = player_pos[1] if isinstance(player_pos, (tuple, list)) else player_pos.get('y', 0)
            bx = boss_pos[0] if isinstance(boss_pos, (tuple, list)) else boss_pos.get('x', 0)
            by = boss_pos[1] if isinstance(boss_pos, (tuple, list)) else boss_pos.get('y', 0)
            dx = (bx - px) / 1000.0
            dy = (by - py) / 1000.0
            
        feat_armadilhas = [0.0] * 8
        if armadilhas:
            keys = ['vortice_ativo', 'prisao_ativa', 'caminho_espinhos', 'laser_ativo', 'descarga_eletrica', 'miasma_ativo', 'praga_ratos', 'parede_ativa']
            for i, k in enumerate(keys):
                if armadilhas.get(k): feat_armadilhas[i] = 1.0
                
        map_val = 0.0
        if mapa_atual:
            map_str = str(mapa_atual).lower()
            if "fase" in map_str:
                num = ''.join(filter(str.isdigit, map_str))
                if num: map_val = float(num) / 10.0
                
        features = [feat_vida, feat_dist, feat_fogo, feat_vx, feat_vy, dx, dy] + feat_armadilhas + [map_val, ameaca_vec[0], ameaca_vec[1]]
        tensor = torch.tensor(features, dtype=torch.float32, device=self.device).unsqueeze(0)
        return tensor

    def decidir(self, estado_tensor, acoes_disponiveis):
        import random
        if random.random() < self.exploracao:
            acao_escolhida = random.choice(acoes_disponiveis)
            self.ultima_acao_idx = self.acoes_base.index(acao_escolhida) if acao_escolhida in self.acoes_base else 0
            self.ultimo_estado_tensor = estado_tensor
            return acao_escolhida
            
        with torch.no_grad():
            self.q_network.eval()
            q_values = self.q_network(estado_tensor)
            
        best_q = -float('inf')
        best_action = random.choice(acoes_disponiveis)
        for acao in acoes_disponiveis:
            if acao in self.acoes_base:
                idx = self.acoes_base.index(acao)
                q_val = q_values[0, idx].item()
                if q_val > best_q:
                    best_q = q_val
                    best_action = acao
                    
        self.ultima_acao_idx = self.acoes_base.index(best_action) if best_action in self.acoes_base else 0
        self.ultimo_estado_tensor = estado_tensor
        return best_action

    def treinar(self, recompensa, prioridade=False):
        if self.ultimo_estado_tensor is not None and self.ultima_acao_idx is not None:
            self.q_network.train()
            # Forward pass: estimação atual
            q_values = self.q_network(self.ultimo_estado_tensor)
            q_val = q_values[0, self.ultima_acao_idx]
            
            # Aproximação da recompensa (regressão isolada na função de custo)
            alvo = q_val.item() + (0.2 if prioridade else 0.1) * (recompensa - q_val.item())
            alvo_tensor = torch.tensor(alvo, dtype=torch.float32, device=self.device)
            
            loss = self.criterion(q_val, alvo_tensor)
            
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

def aplicar_inteligencia_q_ao_grafo(pesos, estado_ia, memoria, vida_perc, dist_p, sob_fogo, historico):
    estado_tensor = memoria.discretizar_estado(vida_perc, dist_p, sob_fogo, historico, player_pos=None, boss_pos=None, armadilhas=estado_ia)
    
    with torch.no_grad():
        memoria.q_network.eval()
        q_values = memoria.q_network(estado_tensor)
        
    for acao in pesos.keys():
        if acao in memoria.acoes_base:
            idx = memoria.acoes_base.index(acao)
            pesos[acao] += q_values[0, idx].item() * 2.0 
    
    return pesos


def calcular_bias_bayesiano(self):
    t = self.q_table.get("tendencias", {"TOTAL": 0})
    total = max(1, t["TOTAL"])
    
    # Retornamos o bias (desvio) estatístico
    bias_x = (t.get("DIREITA", 0) - t.get("ESQUERDA", 0)) / total
    bias_y = (t.get("BAIXO", 0) - t.get("CIMA", 0)) / total
    return bias_x, bias_y


def calcular_distancia(p1, p2):
    r"""
    Calcula a distância euclidiana: $d = \sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}$
    """
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def calcular_poh(player_pos, boss_pos, historico_player, confianca_ia):
    if len(historico_player) < 60: return 0
    # Vetores de estabilidade
    p_ini, p_mid, p_end = historico_player[0], historico_player[30], historico_player[-1]
    v1 = (p_mid[0] - p_ini[0], p_mid[1] - p_ini[1])
    v2 = (p_end[0] - p_mid[0], p_end[1] - p_mid[1])
    
    estabilidade = 1.0 if (abs(v1[0]-v2[0]) < 5 and abs(v1[1]-v2[1]) < 5) else 0.5
    fator_dist = max(0.3, 1.0 - (calcular_distancia(player_pos, boss_pos) / 1500))
    
    return confianca_ia * estabilidade * fator_dist

def node_ataque_direcionado(agora, estado_ia, bx, by, px, py, historico_player, memoria):
    if agora - estado_ia.get('ultimo_attack', 0) >= estado_ia.get('intervalo', 1250):
        centro_bx = bx + (largura_boss // 2)
        centro_by = by + (altura_boss // 2)
        centro_px = px + (largura_personagem // 2)
        centro_py = py + (altura_personagem // 2)
        
        distancia = math.hypot(centro_px - centro_bx, centro_py - centro_by)
        vel_projetil = 11  # Projétil mais veloz
        tempo_voo = distancia / vel_projetil
        
        # Detecta estático e canto
        parado = len(historico_player) >= 5 and all(math.hypot(p[0]-px, p[1]-py) < 4 for p in historico_player[-5:])
        no_canto = px < 80 or px > largura_mapa - 120 or py < 80 or py > altura_mapa - 120

        if parado:
            # Alvo imóvel: tiro 100% direto ao centro, sem ruído
            alvo_x, alvo_y = centro_px, centro_py
        else:
            # Usa velocidade real dos últimos 2 frames como delta calibrado
            if len(historico_player) >= 2:
                vx_real = (centro_px - (historico_player[-2][0] + largura_personagem // 2))
                vy_real = (centro_py - (historico_player[-2][1] + altura_personagem // 2))
            else:
                vx_real, vy_real = 0.0, 0.0
            
            # Lead proporcional: menos lead em distâncias grandes (evita over-shoot)
            fator_lead = max(0.55, 1.0 - (distancia / 1800.0))

            # Se perto de canto, reduz lead para n atirar na parede
            if no_canto:
                fator_lead *= 0.5

            alvo_x = centro_px + vx_real * tempo_voo * fator_lead
            alvo_y = centro_py + vy_real * tempo_voo * fator_lead
            alvo_x = max(50, min(largura_mapa - 50, alvo_x))
            alvo_y = max(50, min(altura_mapa - 50, alvo_y))

        angulo = math.atan2(alvo_y - centro_by, alvo_x - centro_bx)
        
        estado_ia['projeteis'].append({
            "rect": pygame.Rect(centro_bx - 6, centro_by - 6, 12, 12),
            "angulo": angulo,
            "velocidade": vel_projetil,
            "tipo": "comum"
        })
        estado_ia['ultimo_attack'] = agora


def node_caminho_espinhos(agora, estado_ia, bx, by, px, py, historico_player):
    """Padrão A (X): 4 raios diagonais do centro. Padrão B (H3): 3 linhas horizontais.
    Toque = stun 4s + 2 tiros rápidos na Umbra."""
    centro_bx = bx + (largura_boss // 2)
    centro_by = by + (altura_boss // 2)

    padrao = estado_ia.get('espinho_padrao_ultimo', 'B')
    proximo = 'A' if padrao == 'B' else 'B'
    estado_ia['espinho_padrao_ultimo'] = proximo

    if proximo == 'A':
        raios = []
        for ang_base in [math.pi*0.25, math.pi*0.75, math.pi*1.25, math.pi*1.75]:
            raios.append({'origem': (centro_bx, centro_by), 'angulo': ang_base, 'comprimento': 1200})
        estado_ia['caminho_espinhos'] = {
            'padrao': 'X', 'raios': raios, 'largura_maxima': 90,
            'tempo_inicio': agora, 'fase': 'crescimento',
            'duracao_crescimento': 1800, 'duracao_expansao': 1600,
            'ultimo_espinho_hit': 0
        }
    else:
        linhas = []
        for frac in [0.25, 0.50, 0.75]:
            y_linha = int(altura_mapa * frac)
            linhas.append({'origem': (0, y_linha), 'angulo': 0, 'comprimento': largura_mapa})
        estado_ia['caminho_espinhos'] = {
            'padrao': 'H3', 'raios': linhas, 'largura_maxima': 80,
            'tempo_inicio': agora, 'fase': 'crescimento',
            'duracao_crescimento': 1400, 'duracao_expansao': 1600,
            'ultimo_espinho_hit': 0
        }

    estado_ia['ultimo_espinhos'] = agora

# --- NÓDULOS DE PENSAMENTO (AÇÕES DO GRAFO) ---

def node_furia(agora, estado_ia, hitbox_centro, centro_mapa, boss_pos):
    """Nódulo de ataque em espiral 360."""
    dist_ao_centro = calcular_distancia(centro_mapa, (boss_pos['x'], boss_pos['y']))
    
    if estado_ia['furia_fase'] == "caminhando":
        if dist_ao_centro > 15:
            estado_ia['f_fuga_x'] = (centro_mapa[0] - boss_pos['x']) / dist_ao_centro * 5
            estado_ia['f_fuga_y'] = (centro_mapa[1] - boss_pos['y']) / dist_ao_centro * 5
        else:
            estado_ia['furia_fase'] = "espiral"
            estado_ia['angulo_furia'] = 0
    elif estado_ia['furia_fase'] == "espiral":
        estado_ia['projeteis'].append({
            "rect": pygame.Rect(hitbox_centro[0], hitbox_centro[1], 35, 35),
            "angulo": estado_ia['angulo_furia'], "velocidade": 4.0, "tipo": "furia"
        })
        estado_ia['angulo_furia'] += 0.15
        if estado_ia['angulo_furia'] >= 2 * math.pi:
            estado_ia['furia_fase'] = "espera"
            estado_ia['ultimo_furia'] = agora

def node_sifon(agora, estado_ia, boss_pos, centro_mapa):
    """
    Nódulo de Estase e Cura: O Boss torna-se o epicentro do mapa.
    """
    # 1. CÁLCULO DE DESLOCAMENTO AO CENTRO
    dx = centro_mapa[0] - boss_pos['x']
    dy = centro_mapa[1] - boss_pos['y']
    dist_ao_centro = math.hypot(dx, dy)

    # Se ainda não chegou ao centro, move-se rapidamente para lá
    if dist_ao_centro > 5:
        estado_ia['f_fuga_x'] = (dx / dist_ao_centro) * 8
        estado_ia['f_fuga_y'] = (dy / dist_ao_centro) * 8
    else:
        # Chegou ao centro: Ancoragem absoluta
        estado_ia['f_fuga_x'], estado_ia['f_fuga_y'] = 0, 0
        
    # 2. GESTÃO DO TEMPO DE ATIVAÇÃO (4 SEGUNDOS)
    # Verificamos se o tempo de duração expirou
    if agora - estado_ia.get('ultimo_parede', 0) > 6000:
        estado_ia['parede_ativa'] = False
        # O SEGREDO: O cooldown começa a contar AGORA
        estado_ia['ultimo_sifon_fim'] = agora

def node_teleporte(agora, estado_ia, boss_pos, player_pos, historico_player, tipo="fuga"):
    """
    Nódulo de Translocação Visionário: Substitui o acaso por intenção tática.
    """
    bx, by = boss_pos['x'], boss_pos['y']
    px, py = player_pos[0], player_pos[1]
    
    if tipo == "fuga":
        # ESTRATÉGIA DE MAXIMIZAÇÃO DE DISTÂNCIA
        cantos = [(150, 150), (1150, 150), (150, 620), (1150, 620)]
        alvo_x, alvo_y = max(cantos, key=lambda c: math.hypot(c[0] - px, c[1] - py))
    else:
        # ESTRATÉGIA DE INTERCEPTAÇÃO PREDITIVA
        # Se houver histórico, projeta o salto à frente do seu vetor de movimento
        if len(historico_player) >= 2:
            vx = px - historico_player[-2][0]
            vy = py - historico_player[-2][1]
            alvo_x = px + (vx * 25) # Intercepta 25 frames à frente
            alvo_y = py + (vy * 25)
        else:
            # Flanqueamento Lateral em caso de alvo estático
            alvo_x = px + (350 if bx < px else -350)
            alvo_y = py

    alvo_x = max(150, min(1150, alvo_x))
    alvo_y = max(150, min(620, alvo_y))
    
    # Materialização do Projétil Sinalizador
    estado_ia['proj_tele'] = {
        "rect": pygame.Rect(bx, by, 30, 30),
        "angulo": math.atan2(alvo_y - by, alvo_x - bx),
        "tipo": tipo, 
        "alvo_pos": (alvo_x, alvo_y), 
        "velocidade": 12 # Velocidade calibrada para resposta tática
    }
    
    estado_ia['ultimo_teleporte'] = agora
    estado_ia['fase_tele'] = "disparando"

def node_teleporte_sinalizador(agora, estado_ia, boss_pos, alvo_pos):
    """
    Cria o 'Sinalizador de Translocação' (Círculo Azul).
    Ele viajará da posição atual até o alvo_pos.
    """
    # Nota: boss_pos deve ser passado como {'x': ..., 'y': ...}
    start_x, start_y = boss_pos['x'], boss_pos['y']
    target_x, target_y = alvo_pos
    
    dx = target_x - start_x
    dy = target_y - start_y
    dist_total = math.hypot(dx, dy)
    ang = math.atan2(dy, dx)
    
    # Define o projétil sinalizador na memória da IA
    estado_ia['proj_tele'] = {
        'x': start_x, 'y': start_y,       # Posição atual do projétil
        'start_pos': (start_x, start_y),  # Origem
        'target_pos': (target_x, target_y), # Destino final
        'angulo': ang,
        'velocidade': 17,                 # Aumentado para maior fluidez
        'dist_total': dist_total,
        'dist_percorrida': 0,
        'cor_sinal': (0, 120, 255),       # Azul Neon
        'raio': 15 
    }
    
    estado_ia['ultimo_teleporte'] = agora
    estado_ia['fase_tele'] = "projetil_viajando"

def node_descarga_eletrica(agora, estado_ia, bx, by, px, py):
    # CALIBRAÇÃO DE CENTRO: Garante que os raios saiam da alma do boss
    centro_bx = bx + (largura_boss // 2)
    centro_by = by + (altura_boss // 2)
    centro_px = px + (largura_personagem // 2)
    centro_py = py + (altura_personagem // 2)

    angulo_disparo = math.atan2(centro_py - centro_by, centro_px - centro_bx)
    estado_ia['descarga_eletrica'] = {
        'x': centro_bx,
        'y': centro_by,
        'angulo_base': angulo_disparo,
        'raio_maximo': 380.0,
        'abertura': 0.9, 
        'duracao': 1800,
        'tempo_inicio': agora,
        'dano_por_tick': 12
    }
    estado_ia['ultimo_descarga'] = agora

# --- MOTOR DE DECISÃO (O GRAFO) ---

def processar_ia_umbra(agora, boss_pos, player_pos, historico_player, disparos_player, estado_ia, config_boss, memoria):
    import math
    import random
    
    bx, by = boss_pos['x'], boss_pos['y']
    px, py = player_pos[0], player_pos[1]
    centro_mapa = estado_ia.get('centro_mapa', (680, 384))
    
    if estado_ia.get('parede_ativa'):
        node_sifon(agora, estado_ia, boss_pos, centro_mapa)
        return estado_ia

    if estado_ia.get('fase_tele') != "espera":
        return estado_ia

    vida_p = config_boss.get('vida_atual', 1600) / max(1, config_boss.get('vida_max', 1600))
    dist_p = math.hypot(px - bx, py - by)
    sob_fogo = len(disparos_player)
    mapa_atual = config_boss.get('mapa_atual')
    
    estado_composto = memoria.discretizar_estado(vida_p, dist_p, sob_fogo, historico_player, mapa_atual, player_pos, boss_pos, estado_ia)

    acoes_disponiveis = ["ATAQUE"]

    if agora - estado_ia.get('ultimo_teleporte', 0) >= 10000:
        acoes_disponiveis.append("TELEPORTE")
        
    if agora - estado_ia.get('ultimo_sifon_fim', 0) >= 15000 or estado_ia.get('ultimo_sifon_fim') == 0:
        acoes_disponiveis.append("SIFON")

    if agora - estado_ia.get('ultimo_transmutar', 0) >= 25000:
        ultima_dim = estado_ia.get('ultima_dimensao_usada', "")
        if ultima_dim != "vortice": acoes_disponiveis.append("TRANSMUTAR_VORTICE")
        if ultima_dim != "gravidade": acoes_disponiveis.append("TRANSMUTAR_GRAVIDADE")
        if ultima_dim != "necrose": acoes_disponiveis.append("TRANSMUTAR_NECROSE")
        if ultima_dim != "ressonancia": acoes_disponiveis.append("TRANSMUTAR_RESSONANCIA")
        if ultima_dim != "hemorragia": acoes_disponiveis.append("TRANSMUTAR_HEMORRAGIA")
        if ultima_dim != "atrito": acoes_disponiveis.append("TRANSMUTAR_ATRITO")
        if ultima_dim != "rastro": acoes_disponiveis.append("TRANSMUTAR_RASTRO")

    if mapa_atual == "Sprites/Fase1.png" and agora - estado_ia.get('ultimo_vortice', 0) >= 12000:
        acoes_disponiveis.append("VORTICE")
    elif mapa_atual == "Sprites/Fase2.png" and agora - estado_ia.get('ultimo_prisao', 0) >= 9000:
        acoes_disponiveis.append("PRISAO")
    elif mapa_atual == "Sprites/Fase3.png" and agora - estado_ia.get('ultimo_miasma', 0) >= 10000:
        acoes_disponiveis.append("MIASMA")
    elif mapa_atual == "Sprites/Fase4.png" and agora - estado_ia.get('ultimo_descarga', 0) >= 11000:
        acoes_disponiveis.append("DESCARGA_ELETRICA")
    elif mapa_atual == "Sprites/Fase6.png" and agora - estado_ia.get('ultimo_espinhos', 0) >= 8000:
        acoes_disponiveis.append("CAMINHO_ESPINHOS")
    elif mapa_atual == "Sprites/Fase7.png" and agora - estado_ia.get('ultimo_laser', 0) >= 11000:
        acoes_disponiveis.append("LASER_SOBRECARGA")
    elif mapa_atual == "Sprites/Fase9.png" and agora - estado_ia.get('ultimo_praga_ratos', 0) >= 12000:
        acoes_disponiveis.append("PRAGA_RATOS")

    decisao = memoria.decidir(estado_composto, acoes_disponiveis)

    if estado_ia.get('laser_ativo'):
        decisao = "NENHUMA"

    acoes_simultaneas = estado_ia.get('decisoes_ativas', [])
    if decisao not in acoes_simultaneas and decisao != "NENHUMA":
        acoes_simultaneas.append(decisao)
    estado_ia['decisoes_ativas'] = acoes_simultaneas

    if decisao == "SIFON":
        estado_ia['parede_ativa'] = True
        estado_ia['ultimo_parede'] = agora
        estado_ia['dano_recente'] = 0 
        node_sifon(agora, estado_ia, boss_pos, centro_mapa)

    elif decisao.startswith("TRANSMUTAR_"):
        estado_ia['iniciar_transicao_mapa'] = True
        estado_ia['ultimo_transmutar'] = agora
        estado_ia['primeira_transmutacao_feita'] = True
        estado_ia['dano_recente'] = 0 
        estado_ia['tempo_inicio_dimensao'] = agora
        estado_ia['duracao_dimensao'] = 30000
        
        estado_ia['ultimo_vortice'] = agora
        estado_ia['ultimo_prisao'] = agora
        estado_ia['ultimo_miasma'] = agora
        estado_ia['ultimo_descarga'] = agora
        estado_ia['ultimo_espinhos'] = agora
        estado_ia['ultimo_laser'] = agora
        estado_ia['ultimo_praga_ratos'] = agora
        
        dimensao_escolhida = decisao.split("_")[1].lower()
        mapas = {
            "vortice": "Sprites/Fase1.png",
            "gravidade": "Sprites/Fase2.png",
            "necrose": "Sprites/Fase3.png",
            "ressonancia": "Sprites/Fase4.png",
            "hemorragia": "Sprites/Fase6.png",
            "atrito": "Sprites/Fase7.png",
            "rastro": "Sprites/Fase9.png"
        }
        
        estado_ia['mapa_alvo'] = mapas[dimensao_escolhida]
        estado_ia['dimensao_ativa'] = dimensao_escolhida
        estado_ia['ultima_dimensao_usada'] = dimensao_escolhida 
        
        vec_x, vec_y = bx - px, by - py
        mag = math.hypot(vec_x, vec_y)
        alvo_x, alvo_y = (bx + (vec_x/max(1, mag))*600, by + (vec_y/max(1, mag))*600)
        
        from Variaveis import espacamento, largura_mapa, altura_mapa
        alvo_x_f = max(espacamento, min(largura_mapa - 100, alvo_x))
        alvo_y_f = max(espacamento, min(altura_mapa - 150, alvo_y))
        node_teleporte_sinalizador(agora, estado_ia, boss_pos, (alvo_x_f, alvo_y_f))
    
    elif decisao == "VORTICE":
        node_vortice_temporal(agora, estado_ia, px, py, memoria)
        estado_ia['dano_recente'] = 0
    
    elif decisao == "MIASMA":
        node_miasma_toxico(agora, estado_ia)
        estado_ia['dano_recente'] = 0
    
    elif decisao == "DESCARGA_ELETRICA":
        node_descarga_eletrica(agora, estado_ia, bx, by, px, py)
        estado_ia['dano_recente'] = 0

    elif decisao == "PRISAO":
        node_prisao_criogenica(agora, estado_ia, px, py, historico_player)
        estado_ia['dano_recente'] = 0

    elif decisao == "PRAGA_RATOS":
        estado_ia['praga_ratos'] = {
            'tempo_inicio': agora,
            'duracao': 9000
        }
        estado_ia['ultimo_praga_ratos'] = agora
        estado_ia['dano_recente'] = 0

    elif decisao == "LASER_SOBRECARGA":
        estado_ia['laser_ativo'] = {
            'tempo_inicio': agora,
            'fase': 'carregando',
            'rodada': 1,
            'duracao_carga': 1500,
            'duracao_disparo': 4000
        }
        estado_ia['ultimo_laser'] = agora
        estado_ia['carga_atrito'] = 0
        estado_ia['dano_recente'] = 0

    elif decisao == "TELEPORTE":
        vec_x, vec_y = bx - px, by - py
        mag = math.hypot(vec_x, vec_y)
        
        if mag < 200:
            alvo_x, alvo_y = bx + (vec_x/max(1, mag))*600, by + (vec_y/max(1, mag))*600
        else:
            ang_player = math.atan2(py - by, px - bx)
            ang_flanco = ang_player + random.choice([math.pi/2, -math.pi/2])
            alvo_x = px + math.cos(ang_flanco) * 450
            alvo_y = py + math.sin(ang_flanco) * 450

        from Variaveis import espacamento, largura_mapa, altura_mapa
        alvo_x_f = max(espacamento, min(largura_mapa - 100, alvo_x))
        alvo_y_f = max(espacamento, min(altura_mapa - 150, alvo_y))
        
        node_teleporte_sinalizador(agora, estado_ia, boss_pos, (alvo_x_f, alvo_y_f))

    elif decisao == "CAMINHO_ESPINHOS":
        node_caminho_espinhos(agora, estado_ia, bx, by, px, py, historico_player)
        estado_ia['dano_recente'] = 0
            
    elif decisao == "ATAQUE":
        node_ataque_direcionado(agora, estado_ia, bx, by, px, py, historico_player, memoria)
        
    return estado_ia


def node_miasma_toxico(agora, estado_ia):
    estado_ia['miasma_ativo'] = {
        'tempo_inicio': agora,
        'duracao': 4500 
    }
    estado_ia['ultimo_miasma'] = agora

def node_vortice_temporal(agora, estado_ia, px, py, memoria):
    """Nódulo de Singularidade: Ancorado no centro do tecido dimensional."""
    alvo_x = largura_mapa // 2
    alvo_y = altura_mapa // 2
    
    estado_ia['vortice_ativo'] = {
        'x': alvo_x, 
        'y': alvo_y,
        'tempo_inicio': agora, 
        'duracao': 8000, 
        'forca': 2.8
    }
    estado_ia['ultimo_vortice'] = agora

def node_prisao_criogenica(agora, estado_ia, px, py, historico_player):
    """Nódulo de Congelamento: Intercepta a rota de fuga com Zero Absoluto."""
    if len(historico_player) >= 5:
        # Calcula o vetor de movimento dos últimos frames
        vx = px - historico_player[-5][0]
        vy = py - historico_player[-5][1]
        
        # Projeta a armadilha à frente do jogador
        alvo_x = px + (vx * 6)
        alvo_y = py + (vy * 6)
    else:
        alvo_x, alvo_y = px, py

    # Contenção nos limites do mapa
    alvo_x = max(80, min(1280, alvo_x))
    alvo_y = max(80, min(680, alvo_y))
    
    estado_ia['prisao_ativa'] = {
        'rect': pygame.Rect(alvo_x - 60, alvo_y - 60, 120, 120),
        'tempo_inicio': agora,
        'duracao': 3500, # 3.5 segundos de armadilha no chão
        'x': alvo_x,
        'y': alvo_y
    }
    estado_ia['ultimo_prisao'] = agora


def movimentacao_inteligente_umbra(agora, boss_pos, player_pos, disparos, estado_mov, dados_player, memoria, historico_player):
    if estado_mov.get('parede_ativa'):
        estado_mov['vel_x'], estado_mov['vel_y'] = 0, 0
        return estado_mov.get('centro_mapa', (680, 384)), "SIFON_STASIS"
    if estado_mov.get('laser_ativo'):
        estado_mov['vel_x'], estado_mov['vel_y'] = 0, 0
        return (boss_pos[0], boss_pos[1]), "LASER_STASIS"

    import math, random
    bx, by = boss_pos[0], boss_pos[1]
    px, py = player_pos[0], player_pos[1]
    dist_p = math.hypot(bx - px, by - py)

    VEL_MAX = 3.0
    AGILIDADE = 0.3
    RAIO_SEGURANCA = 340

    # PROTOCOLO DE VISÃO DE BALA
    tiro_ameaca = None
    ameaca_x, ameaca_y = 0.0, 0.0
    for d in disparos:
        dx_tiro = bx - d["rect"].centerx
        vx_tiro = math.cos(d["angulo"])
        if (dx_tiro > 0 and vx_tiro > 0) or (dx_tiro < 0 and vx_tiro < 0):
            dist_h = math.hypot(d["rect"].centerx - bx, d["rect"].centery - by)
            if dist_h < 400:
                tiro_ameaca = d
                ameaca_x = math.cos(d["angulo"])
                ameaca_y = math.sin(d["angulo"])
                break

    vida_perc = dados_player['vida_atual'] / dados_player['vida_max']
    sob_fogo = 1.0 if tiro_ameaca else 0.0
    estado_atual = memoria.discretizar_estado(vida_perc, dist_p, sob_fogo, historico_player, dados_player.get('mapa_atual', 'Fase_Base'), player_pos, boss_pos, estado_mov, ameaca_vec=(ameaca_x, ameaca_y))
    
    estrategias = ["FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR"]
    decisao = memoria.decidir(estado_atual, estrategias)

    # MOVIMENTO PADRAO (Se chegou aqui n deu dash)
    if decisao == "FUGIR":
        ang_fuga = math.atan2(by - py, bx - px)
        alvo_x, alvo_y = bx + math.cos(ang_fuga) * 600, by + math.sin(ang_fuga) * 600
    elif decisao == "INTERCEPTAR":
        alvo_x = px + (px - bx) * 0.3; alvo_y = py + (py - by) * 0.3
    elif decisao == "ORBITAR":
        ang = math.atan2(by - py, bx - px) + 0.7
        alvo_x, alvo_y = px + math.cos(ang) * 450, py + math.sin(ang) * 450
    else: 
        ang = math.atan2(by - py, bx - px)
        alvo_x, alvo_y = px + math.cos(ang) * 300, py + math.sin(ang) * 300

    limite_x_min = int(espacamento)
    limite_x_max = int(largura_mapa - largura_boss - espacamento)
    limite_y_min = int(espacamento)
    limite_y_max = int(altura_mapa - altura_boss - espacamento)
    estado_mov['alvo_ia'] = (max(limite_x_min, min(limite_x_max, alvo_x)), max(limite_y_min, min(limite_y_max, alvo_y)))
    
    dx_a, dy_a = estado_mov['alvo_ia'][0] - bx, estado_mov['alvo_ia'][1] - by
    mag_a = math.hypot(dx_a, dy_a)
    vec_alvo_x = (dx_a / mag_a) if mag_a > 0 else 0
    vec_alvo_y = (dy_a / mag_a) if mag_a > 0 else 0

    rx, ry = bx - px, by - py
    dist_r = math.hypot(rx, ry)
    f_rep_x = f_rep_y = 0
    if dist_r < RAIO_SEGURANCA:
        f_rep_x, f_rep_y = (rx/dist_r) * 1.5, (ry/dist_r) * 1.5

    v_desejada_x = (vec_alvo_x + f_rep_x) * VEL_MAX
    v_desejada_y = (vec_alvo_y + f_rep_y) * VEL_MAX
    vx = estado_mov.get('vel_x', 0)
    vy = estado_mov.get('vel_y', 0)
    vx += (v_desejada_x - vx) * AGILIDADE
    vy += (v_desejada_y - vy) * AGILIDADE
    estado_mov['vel_x'], estado_mov['vel_y'] = vx, vy

    nx = max(int(espacamento), min(int(largura_mapa - largura_boss - espacamento), int(bx + vx)))
    ny = max(int(espacamento), min(int(altura_mapa - altura_boss - espacamento), int(by + vy)))

    return (nx, ny), "GENERATIVE_MOVE"


# --- MOTOR DE VFX PROCEDURAL (PLASMA & PARTÍCULAS) ---

def gerar_burst_desfragmentacao(x, y, estado_ia, cor_base=(0, 255, 100)):
    """
    OTIMIZADO: Gera explosão de fragmentos com MENOS partículas (15-20 ao invés de 15-25).
    Cor padrão: Verde para combinar com projéteis da Umbra.
    """
    if 'vfx_particulas' not in estado_ia:
        estado_ia['vfx_particulas'] = []
        
    # OTIMIZAÇÃO: Reduzido de 15-25 para 10-15 partículas
    for _ in range(random.randint(10, 15)):
        ang = random.uniform(0, math.pi * 2)
        forca = random.uniform(1.0, 4.0)  # OTIMIZAÇÃO: Reduzida força máxima
        vida = random.randint(15, 40)  # OTIMIZAÇÃO: Reduzida vida máxima
        estado_ia['vfx_particulas'].append({
            'x': x, 'y': y,
            'vx': math.cos(ang) * forca,
            'vy': math.sin(ang) * forca,
            'vida': vida,
            'vida_max': vida,
            'cor': cor_base,
            'tam': random.randint(2, 4)  # OTIMIZAÇÃO: Reduzido tamanho máximo
        })

def renderizar_vfx_umbra(tela, agora, estado_ia):
    """
    DESIGN OTIMIZADO: Projéteis verdes da Umbra com menos partículas.
    Renderiza esferas de plasma verde com aura pulsante.
    """
    
    # 1. GESTÃO OTIMIZADA DE PARTÍCULAS (REDUZIDO)
    particulas_vivas = []
    vfx_pool = estado_ia.get('vfx_particulas', [])
    
    # OTIMIZAÇÃO: Processa apenas a cada 2 frames para reduzir carga
    if len(vfx_pool) > 0 and agora % 2 == 0:
        for p in vfx_pool:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vida'] -= 2  # Decrementa 2 para compensar o skip de frame
            p['vx'] *= 0.94
            p['vy'] *= 0.94
            
            if p['vida'] > 0:
                alfa = int((p['vida'] / p['vida_max']) * 255)
                s = pygame.Surface((p['tam']*2, p['tam']*2), pygame.SRCALPHA)
                cor_rgb = p['cor'][:3] if isinstance(p['cor'], (tuple, list)) and len(p['cor']) >= 3 else (0, 255, 100)
                pygame.draw.circle(s, (*cor_rgb, alfa), (p['tam'], p['tam']), p['tam'])
                tela.blit(s, (p['x'] - p['tam'], p['y'] - p['tam']))
                particulas_vivas.append(p)
    else:
        particulas_vivas = vfx_pool
            
    estado_ia['vfx_particulas'] = particulas_vivas

    # 2. RENDERIZAÇÃO OTIMIZADA DE PROJÉTEIS (VERDE)
    for proj in estado_ia.get('projeteis', []):
        x, y = proj['rect'].center
        tipo = proj.get('tipo', 'comum')
        
        # Cores Verde da Umbra
        if tipo == "furia":
            cor_aura = (138, 43, 226)  # Púrpura de Fúria (mantém especial)
            raio_base = 15
            camadas = 3
        else:
            cor_aura = (0, 255, 100)  # Verde Brilhante
            raio_base = 8
            camadas = 2  # OTIMIZAÇÃO: Reduzido de 3 para 2 camadas
            
        pulsar = math.sin(agora * 0.02) * 2  # OTIMIZAÇÃO: Reduzido amplitude
        
        # A. AURA TRANSLÚCIDA PULSANTE (OTIMIZADA)
        for nivel in range(camadas, 0, -1):
            raio_vfx = raio_base + (nivel * 3) + pulsar  # OTIMIZAÇÃO: Reduzido multiplicador
            opacidade = 70 // nivel  # OTIMIZAÇÃO: Reduzida opacidade base
            circulo_aura = pygame.Surface((raio_vfx * 2, raio_vfx * 2), pygame.SRCALPHA)
            pygame.draw.circle(circulo_aura, (*cor_aura, opacidade), (raio_vfx, raio_vfx), raio_vfx)
            tela.blit(circulo_aura, (x - raio_vfx, y - raio_vfx))
            
        # B. NÚCLEO BRILHANTE (SIMPLIFICADO)
        pygame.draw.circle(tela, (255, 255, 255), (x, y), raio_base)
        pygame.draw.circle(tela, cor_aura, (x, y), raio_base + 1, 1)  # OTIMIZAÇÃO: Reduzida espessura