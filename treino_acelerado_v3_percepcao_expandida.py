"""
================================================================================
TREINO ACELERADO V3 - PERCEPÇÃO EXPANDIDA
================================================================================

EXPANSÃO DE CONSCIÊNCIA:
- Apolo: 4 componentes → 10 componentes de estado
- Umbra: Discretização mais granular (vida, distância, velocidade)
- Ambos: Consciência de múltiplos projéteis, trajetórias, padrões temporais

CRESCIMENTO ESPERADO:
- Apolo: 300-600 estados → 2000-5000 estados
- Umbra: 400-800 estados → 1500-3000 estados
- Tempo de convergência: 500 episódios → 2000-5000 episódios

EPISÓDIOS RECOMENDADOS: 3000-5000 (deixar rodando 5-10 minutos)
================================================================================
"""

import math
import random
import json
import os
import time
from collections import deque
import torch
import torch.nn as nn
import torch.optim as optim

from habilidade_boss import MemoriaEvolutivaUmbra

try:
    from Variaveis import largura_mapa, altura_mapa, largura_personagem, altura_personagem, largura_boss, altura_boss
except ImportError:
    largura_mapa = 1360
    altura_mapa = 768
    largura_personagem = 50
    altura_personagem = 50
    largura_boss = 80
    altura_boss = 80


class ApoloDQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(ApoloDQN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.LeakyReLU(),
            nn.Linear(128, 64),
            nn.LeakyReLU(),
            nn.Linear(64, output_size)
        )
    def forward(self, x):
        return self.net(x)

class AgenteApoloExpandido:
    def __init__(self, arquivo="apolo_memoria_dqn.pt"):
        self.direcao_x = 0
        self.direcao_y = 0
        self.usar_dash = False
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.input_size = 20
        self.output_size = 5
        
        self.q_network = ApoloDQN(self.input_size, self.output_size).to(self.device)
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()
        
        self.ultimo_estado_tensor = None
        self.acao_anterior = 0
        self.vida_jogador_anterior = 0
        self.vida_boss_anterior = 0
        self.arquivo_memoria = arquivo
        self.taxa_exploracao = 0.20
        self.carregar_memoria()

    def carregar_memoria(self):
        if os.path.exists(self.arquivo_memoria):
            try:
                self.q_network.load_state_dict(torch.load(self.arquivo_memoria, map_location=self.device, weights_only=True))
            except: pass

    def salvar_memoria(self):
        torch.save(self.q_network.state_dict(), self.arquivo_memoria)

    def aplicar_recompensa_direta(self, recompensa_direta):
        if self.ultimo_estado_tensor is not None:
            self.q_network.train()
            q_values = self.q_network(self.ultimo_estado_tensor)
            q_val = q_values[0, self.acao_anterior]
            alvo = q_val.item() + 0.15 * recompensa_direta
            alvo_tensor = torch.tensor(alvo, dtype=torch.float32, device=self.device)
            loss = self.criterion(q_val, alvo_tensor)
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

    def obter_estado_expandido(self, pos_p, pos_boss, projeteis_boss, cd_teleporte, armadilhas_ativas, vida_apolo, vida_boss, velocidade_apolo):
        px, py = pos_p
        bx, by = pos_boss
        
        feat_px = px / max(1, largura_mapa)
        feat_py = py / max(1, altura_mapa)
        feat_bx = bx / max(1, largura_mapa)
        feat_by = by / max(1, altura_mapa)
        
        feat_vida_p = vida_apolo / 1000.0
        feat_vida_b = vida_boss / 1200.0
        
        dist_perigo = 1.0
        dx_perigo = 0.0
        dy_perigo = 0.0
        projeteis_proximos = []
        for proj in projeteis_boss:
            proj_x, proj_y = proj['x'], proj['y']
            d = math.hypot(proj_x - px, proj_y - py)
            if d < 250:
                projeteis_proximos.append((proj_x, proj_y, d))
                
        if projeteis_proximos:
            proj_x, proj_y, d = min(projeteis_proximos, key=lambda p: p[2])
            dist_perigo = d / 250.0
            dx_perigo = (proj_x - px) / max(1.0, d)
            dy_perigo = (proj_y - py) / max(1.0, d)
            
        feat_cd_tele = 1.0 if cd_teleporte else 0.0
        
        feat_armadilhas = [0.0] * 7
        if isinstance(armadilhas_ativas, dict):
            keys = ['vortice_ativo', 'prisao_ativa', 'caminho_espinhos', 'laser_ativo', 'descarga_eletrica', 'praga_ratos', 'miasma_ativo']
            for i, k in enumerate(keys):
                if armadilhas_ativas.get(k): feat_armadilhas[i] = 1.0
        elif armadilhas_ativas:
            feat_armadilhas[random.randint(0, 6)] = 1.0
            
        feat_vel_p = min(1.0, velocidade_apolo / 15.0)
        feat_esferas = 0.0
        feat_vel_b = 0.0
        
        features = [feat_px, feat_py, feat_bx, feat_by, feat_vida_p, feat_vida_b, dist_perigo, dx_perigo, dy_perigo, feat_cd_tele, feat_vel_p, feat_esferas, feat_vel_b] + feat_armadilhas
        tensor = torch.tensor(features, dtype=torch.float32, device=self.device).unsqueeze(0)
        return tensor

    def pensar(self, pos_p, pos_boss, projeteis_boss, cd_teleporte, vida_jogador, vida_boss, armadilhas_ativas, frames_sobrevividos, velocidade_atual):
        self.direcao_x = 0
        self.direcao_y = 0
        self.usar_dash = False

        # RECOMPENSA EXPANDIDA
        recompensa = 0
        
        # Sobrevivência base
        recompensa += 0.5
        
        # Recompensas por mudança de vida
        if self.vida_jogador_anterior > 0:
            delta_vida_apolo = vida_jogador - self.vida_jogador_anterior
            delta_vida_boss = vida_boss - self.vida_boss_anterior
            
            if delta_vida_apolo < 0:
                recompensa -= 50  # Punição por levar dano
            if delta_vida_boss < 0:
                recompensa += 30  # Recompensa por causar dano
            if delta_vida_apolo > 0:
                recompensa += 100  # Recompensa por se curar
        
        # Recompensa por evitar bordas perigosas
        px, py = pos_p
        if px < 100 or px > largura_mapa - 100 or py < 100 or py > altura_mapa - 100:
            recompensa -= 2  # Punição leve por ficar nas bordas
        
        # Recompensa por manter distância segura
        dist_boss = math.hypot(pos_boss[0] - px, pos_boss[1] - py)
        if 300 < dist_boss < 600:
            recompensa += 1  # Distância ideal
        elif dist_boss < 200:
            recompensa -= 3  # Muito perto é perigoso
        
        self.vida_jogador_anterior = vida_jogador
        self.vida_boss_anterior = vida_boss

        # OBTER ESTADO EXPANDIDO
        estado_tensor = self.obter_estado_expandido(
            pos_p, pos_boss, projeteis_boss, cd_teleporte, 
            armadilhas_ativas, vida_jogador, vida_boss, velocidade_atual
        )

        if self.ultimo_estado_tensor is not None:
            self.q_network.train()
            q_values = self.q_network(self.ultimo_estado_tensor)
            q_val = q_values[0, self.acao_anterior]
            alvo = q_val.item() + 0.15 * (recompensa - q_val.item())
            alvo_tensor = torch.tensor(alvo, dtype=torch.float32, device=self.device)
            loss = self.criterion(q_val, alvo_tensor)
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

        # SELEÇÃO DE AÇÃO
        if random.random() < self.taxa_exploracao:
            acao = random.choice([0, 1, 2, 3, 4])
        else:
            with torch.no_grad():
                self.q_network.eval()
                q_vals = self.q_network(estado_tensor)
                acao = torch.argmax(q_vals).item()

        self.ultimo_estado_tensor = estado_tensor
        self.acao_anterior = acao

        if acao == 0:
            self.direcao_y = -1
        elif acao == 1:
            self.direcao_y = 1
        elif acao == 2:
            self.direcao_x = -1
        elif acao == 3:
            self.direcao_x = 1
        elif acao == 4:
            self.usar_dash = True


class SimuladorCombateExpandido:
    def __init__(self, episodios_totais=3000, episodios_por_lote=100):
        self.episodios_totais = episodios_totais
        self.episodios_por_lote = episodios_por_lote
        
        self.umbra = MemoriaEvolutivaUmbra()
        self.apolo = AgenteApoloExpandido()
        
        self.vitorias_umbra = 0
        self.vitorias_apolo = 0
        
        self.exploracao_inicial = 0.25  # Aumentado para mais exploração
        self.exploracao_final = 0.01
        
        print("="*80)
        print("SIMULADOR V3 - PERCEPÇÃO EXPANDIDA")
        print("="*80)
        print(f"Episódios totais: {self.episodios_totais}")
        print(f"Episódios por lote: {self.episodios_por_lote}")
        print(f"Exploração: {self.exploracao_inicial*100:.0f}% → {self.exploracao_final*100:.0f}%")
        print()
        print("EXPANSÃO DE CONSCIÊNCIA:")
        print("  • Apolo: 4 → 10 componentes de estado")
        print("  • Umbra: Discretização mais granular")
        print("  • Detecção de múltiplos projéteis")
        print("  • Consciência de posição no mapa")
        print("  • Análise de velocidade e trajetória")
        print()
        print("CRESCIMENTO ESPERADO:")
        print("  • Apolo: 2000-5000 estados")
        print("  • Umbra: 1500-3000 estados")
        print("  • Tempo: 5-10 minutos")
        print("="*80)
        print()

    def calcular_taxa_exploracao(self, episodio_atual):
        progresso = episodio_atual / self.episodios_totais
        taxa = self.exploracao_inicial * ((self.exploracao_final / self.exploracao_inicial) ** progresso)
        return max(self.exploracao_final, taxa)

    def resetar_episodio(self):
        pos_apolo = [largura_mapa // 2, altura_mapa - 150]
        pos_umbra = [largura_mapa // 2, 150]
        
        vida_apolo = 1000.0
        vida_umbra = 1200.0
        vida_max_apolo = 1000.0
        vida_max_umbra = 1200.0
        
        projeteis_umbra = []
        historico_apolo = deque(maxlen=60)
        
        cd_ataque_umbra = 0
        cd_teleporte_apolo = 0
        cd_habilidade_especial = 0
        
        tempo_simulado = 0
        frames_sobrevividos = 0
        invulneravel_ate = 0
        velocidade_apolo_atual = 0
        
        return {
            'pos_apolo': pos_apolo,
            'pos_umbra': pos_umbra,
            'vida_apolo': vida_apolo,
            'vida_umbra': vida_umbra,
            'vida_max_apolo': vida_max_apolo,
            'vida_max_umbra': vida_max_umbra,
            'projeteis_umbra': projeteis_umbra,
            'historico_apolo': historico_apolo,
            'cd_ataque_umbra': cd_ataque_umbra,
            'cd_teleporte_apolo': cd_teleporte_apolo,
            'cd_habilidade_especial': cd_habilidade_especial,
            'tempo_simulado': tempo_simulado,
            'frames_sobrevividos': frames_sobrevividos,
            'invulneravel_ate': invulneravel_ate,
            'velocidade_apolo_atual': velocidade_apolo_atual,
            'ratos_ativos': [],
            'ratos_adicionais': 0,
            'ultimo_praga': 0,
            'estava_nas_bordas': False,
            'tempo_entrada_bordas': 0,
            'ultimo_tick_dano_bordas': 0,
            'laser_ativo': None
        }

    def simular_frame(self, estado):
        estado['tempo_simulado'] += 16.666
        estado['frames_sobrevividos'] += 1
        
        estado['cd_ataque_umbra'] = max(0, estado['cd_ataque_umbra'] - 16.666)
        estado['cd_teleporte_apolo'] = max(0, estado['cd_teleporte_apolo'] - 16.666)
        estado['cd_habilidade_especial'] = max(0, estado['cd_habilidade_especial'] - 16.666)
        
        # ===== DECISÃO DO APOLO =====
        cd_teleporte_bool = estado['cd_teleporte_apolo'] == 0
        armadilhas_ativas = estado['cd_habilidade_especial'] > 0
        
        self.apolo.pensar(
            estado['pos_apolo'],
            estado['pos_umbra'],
            estado['projeteis_umbra'],
            cd_teleporte_bool,
            estado['vida_apolo'],
            estado['vida_umbra'],
            armadilhas_ativas,
            estado['frames_sobrevividos'],
            estado['velocidade_apolo_atual']
        )
        
        # Aplicar movimento do Apolo
        velocidade_apolo = 5.0
        if self.apolo.usar_dash and cd_teleporte_bool:
            velocidade_apolo = 15.0
            estado['cd_teleporte_apolo'] = 3000
            estado['invulneravel_ate'] = estado['tempo_simulado'] + 300
        
        estado['velocidade_apolo_atual'] = velocidade_apolo
        
        estado['pos_apolo'][0] += self.apolo.direcao_x * velocidade_apolo
        estado['pos_apolo'][1] += self.apolo.direcao_y * velocidade_apolo
        
        estado['pos_apolo'][0] = max(0, min(largura_mapa - largura_personagem, estado['pos_apolo'][0]))
        estado['pos_apolo'][1] = max(0, min(altura_mapa - altura_personagem, estado['pos_apolo'][1]))
        
        estado['historico_apolo'].append(tuple(estado['pos_apolo']))
        
        # ===== DECISÃO DA UMBRA (GRANULAR) =====
        vida_perc_umbra = estado['vida_umbra'] / estado['vida_max_umbra']
        dist_apolo = math.hypot(
            estado['pos_umbra'][0] - estado['pos_apolo'][0],
            estado['pos_umbra'][1] - estado['pos_apolo'][1]
        )
        
        # Análise de movimento do Apolo (velocidade)
        sob_fogo = len(estado['projeteis_umbra']) > 2  # Considera "sob fogo" se há múltiplos projéteis
        
        historico_simplificado = list(estado['historico_apolo'])[-15:] if len(estado['historico_apolo']) >= 15 else []
        
        estado_umbra = self.umbra.discretizar_estado(
            vida_perc_umbra,
            dist_apolo,
            sob_fogo,
            historico_simplificado,
            "Fase_Base"
        )
        
        acoes_umbra = ["ATAQUE"]
        if estado['cd_habilidade_especial'] == 0 and random.random() < 0.15:
            acoes_umbra.append("HABILIDADE_ESPECIAL")
        
        acao_umbra = self.umbra.decidir(estado_umbra, acoes_umbra)
        
        # Executar ação da Umbra
        if acao_umbra == "ATAQUE" and estado['cd_ataque_umbra'] == 0:
            # Predição melhorada (usa velocidade do Apolo)
            if len(estado['historico_apolo']) >= 3:
                vx_apolo = estado['pos_apolo'][0] - estado['historico_apolo'][-3][0]
                vy_apolo = estado['pos_apolo'][1] - estado['historico_apolo'][-3][1]
                tempo_voo = dist_apolo / 9.0
                alvo_x = estado['pos_apolo'][0] + vx_apolo * tempo_voo * 0.7
                alvo_y = estado['pos_apolo'][1] + vy_apolo * tempo_voo * 0.7
            else:
                alvo_x, alvo_y = estado['pos_apolo'][0], estado['pos_apolo'][1]
            
            angulo = math.atan2(
                alvo_y - estado['pos_umbra'][1],
                alvo_x - estado['pos_umbra'][0]
            )
            estado['projeteis_umbra'].append({
                'x': estado['pos_umbra'][0],
                'y': estado['pos_umbra'][1],
                'angulo': angulo,
                'velocidade': 9.0
            })
            estado['cd_ataque_umbra'] = 1800
        
        elif acao_umbra == "HABILIDADE_ESPECIAL":
            estado['cd_habilidade_especial'] = 8000
            if not estado['laser_ativo']:
                estado['laser_ativo'] = {
                    'tempo_inicio': estado['tempo_simulado'],
                    'fase': 'carregando',
                    'rodada': 1,
                    'duracao_carga': 1500,
                    'duracao_disparo': 4000
                }
                
        # ===== ATUALIZAR LASER =====
        laser = estado['laser_ativo']
        if laser:
            tempo_laser = estado['tempo_simulado'] - laser['tempo_inicio']
            origem_laser = (estado['pos_umbra'][0] + largura_boss // 2, estado['pos_umbra'][1] + altura_boss // 2)
            
            if laser['fase'] == 'carregando':
                if tempo_laser >= laser['duracao_carga']:
                    laser['fase'] = 'disparando'
                    laser['tempo_inicio_disparo'] = estado['tempo_simulado']
            elif laser['fase'] == 'disparando':
                t_disp = estado['tempo_simulado'] - laser['tempo_inicio_disparo']
                progresso = min(1.0, t_disp / laser['duracao_disparo'])
                angulo_atual = laser.get('angulo_base', 0) + math.sin(progresso * math.pi * 4) * 0.5
                
                comp_laser = 2500
                fim_x = origem_laser[0] + math.cos(angulo_atual) * comp_laser
                fim_y = origem_laser[1] + math.sin(angulo_atual) * comp_laser
                
                # Hitbox Euclidiano do Laser
                px_c = estado['pos_apolo'][0] + largura_personagem // 2
                py_c = estado['pos_apolo'][1] + altura_personagem // 2
                
                numerador = abs((fim_y - origem_laser[1])*px_c - (fim_x - origem_laser[0])*py_c + fim_x*origem_laser[1] - fim_y*origem_laser[0])
                denominador = math.hypot(fim_y - origem_laser[1], fim_x - origem_laser[0])
                distancia = numerador / denominador if denominador != 0 else 999
                
                dot_product = (px_c - origem_laser[0]) * math.cos(angulo_atual) + (py_c - origem_laser[1]) * math.sin(angulo_atual)
                atingido = distancia < 25 and 0 < dot_product < comp_laser
                
                if atingido and estado['tempo_simulado'] - laser.get('ultimo_dano_laser', 0) > 100:
                    estado['vida_apolo'] -= 45
                    self.umbra.treinar(50.0, prioridade=True)
                    self.apolo.aplicar_recompensa_direta(-30.0)
                    laser['ultimo_dano_laser'] = estado['tempo_simulado']
                    
                if t_disp >= laser['duracao_disparo']:
                    estado['laser_ativo'] = None
        
        # ===== ATUALIZAR PROJÉTEIS =====
        projeteis_ativos = []
        invulneravel = estado['tempo_simulado'] < estado['invulneravel_ate']
        
        for proj in estado['projeteis_umbra']:
            proj['x'] += math.cos(proj['angulo']) * proj['velocidade']
            proj['y'] += math.sin(proj['angulo']) * proj['velocidade']
            
            dist_proj = math.hypot(
                proj['x'] - estado['pos_apolo'][0],
                proj['y'] - estado['pos_apolo'][1]
            )
            
            if dist_proj < 30 and not invulneravel:
                estado['vida_apolo'] -= 50
                self.umbra.treinar(2.0, prioridade=True)
            elif 0 <= proj['x'] <= largura_mapa and 0 <= proj['y'] <= altura_mapa:
                projeteis_ativos.append(proj)
        
        estado['projeteis_umbra'] = projeteis_ativos
        
        # ===== ENXAME DE RATOS =====
        for rato in list(estado['ratos_ativos']):
            dx = estado['pos_apolo'][0] - rato['x']
            dy = estado['pos_apolo'][1] - rato['y']
            dist = math.hypot(dx, dy)
            if dist > 0:
                rato['x'] += (dx/dist) * 6.0
                rato['y'] += (dy/dist) * 6.0
            
            # Colisão com o Player
            if dist < 25 and not invulneravel:
                estado['vida_apolo'] -= 8
                estado['vida_umbra'] = min(estado['vida_max_umbra'], estado['vida_umbra'] + 20)
                estado['ratos_adicionais'] += 1
                self.umbra.treinar(5.0, prioridade=True)
                self.apolo.aplicar_recompensa_direta(-5.0)
                estado['ratos_ativos'].remove(rato)
        
        # ===== APOLO ATACA UMBRA =====
        if random.random() < 0.05:
            estado['vida_umbra'] -= 15
            estado['tomou_tiro_no_dash'] = True
        
        # ===== VERIFICAR FIM DO EPISÓDIO =====
        if estado['vida_apolo'] <= 0:
            self.umbra.treinar(500.0, prioridade=True)
            self.apolo.aplicar_recompensa_direta(-500.0)
            return True, "UMBRA"
        
        if estado['vida_umbra'] <= 0:
            self.umbra.treinar(-500.0, prioridade=True)
            self.apolo.aplicar_recompensa_direta(500.0)
            return True, "APOLO"
        
        if estado['tempo_simulado'] > 30000:
            if estado['vida_umbra'] > estado['vida_apolo']:
                return True, "UMBRA"
            else:
                return True, "APOLO"
        
        return False, None

    def executar_episodio(self, episodio_num):
        estado = self.resetar_episodio()
        
        taxa_exploracao = self.calcular_taxa_exploracao(episodio_num)
        self.umbra.exploracao = taxa_exploracao
        self.apolo.taxa_exploracao = taxa_exploracao
        
        frames = 0
        max_frames = 2000
        
        while frames < max_frames:
            terminado, vencedor = self.simular_frame(estado)
            
            if terminado:
                if vencedor == "UMBRA":
                    self.vitorias_umbra += 1
                else:
                    self.vitorias_apolo += 1
                return vencedor
            
            frames += 1
        
        return "TIMEOUT"

    def executar_treinamento(self):
        inicio_total = time.time()
        
        for lote in range(0, self.episodios_totais, self.episodios_por_lote):
            inicio_lote = time.time()
            
            episodios_neste_lote = min(self.episodios_por_lote, self.episodios_totais - lote)
            
            for i in range(episodios_neste_lote):
                episodio_global = lote + i
                vencedor = self.executar_episodio(episodio_global)
            
            tempo_lote = time.time() - inicio_lote
            progresso = ((lote + episodios_neste_lote) / self.episodios_totais) * 100
            
            print(f"[LOTE {lote//self.episodios_por_lote + 1}] Episódios {lote+1}-{lote+episodios_neste_lote}")
            print(f"  Progresso: {progresso:.1f}%")
            print(f"  Placar: Umbra {self.vitorias_umbra} x {self.vitorias_apolo} Apolo")
            print(f"  Q-Table Umbra: {0} estados")
            print(f"  Q-Table Apolo: {0} estados")
            print(f"  Taxa Exploração: {self.umbra.exploracao*100:.2f}%")
            print(f"  Tempo do lote: {tempo_lote:.2f}s")
            print()
            
            if lote + episodios_neste_lote < self.episodios_totais:
                time.sleep(2)
        
        tempo_total = time.time() - inicio_total
        
        print("="*80)
        print("TREINAMENTO CONCLUÍDO")
        print("="*80)
        print(f"Tempo total: {tempo_total:.2f}s ({tempo_total/60:.1f} minutos)")
        print(f"Episódios executados: {self.episodios_totais}")
        print(f"Placar final: Umbra {self.vitorias_umbra} x {self.vitorias_apolo} Apolo")
        print(f"Taxa de vitória Umbra: {(self.vitorias_umbra/self.episodios_totais)*100:.1f}%")
        print(f"Taxa de vitória Apolo: {(self.vitorias_apolo/self.episodios_totais)*100:.1f}%")
        print(f"Estados na Q-Table Umbra: {0}")
        print(f"Estados na Q-Table Apolo: {0}")
        print("="*80)
        print()
        
        print("Salvando memórias...")
        self.umbra.salvar()
        self.apolo.salvar_memoria()
        print("✓ memoria_umbra.json atualizado")
        print("✓ apolo_memoria.json atualizado")
        print()
        print("Treinamento expandido finalizado com sucesso!")


def main():
    print()
    print("+" + "="*78 + "+")
    print("|" + " "*18 + "TREINO ACELERADO V3" + " "*40 + "|")
    print("|" + " "*24 + "PERCEPÇÃO EXPANDIDA" + " "*36 + "|")
    print("+" + "="*78 + "+")
    print()
    
    # CONFIGURAÇÃO PARA TREINAMENTO LONGO
    EPISODIOS_TOTAIS = 3000  # Aumentado de 500
    EPISODIOS_POR_LOTE = 100  # Aumentado de 50
    
    print("⚠️  AVISO: Este treinamento levará 5-10 minutos.")
    print("   Deixe rodando e monitore o crescimento das Q-Tables.")
    print()
    
    simulador = SimuladorCombateExpandido(
        episodios_totais=EPISODIOS_TOTAIS,
        episodios_por_lote=EPISODIOS_POR_LOTE
    )
    
    try:
        simulador.executar_treinamento()
    except KeyboardInterrupt:
        print()
        print("="*80)
        print("TREINAMENTO INTERROMPIDO PELO USUÁRIO")
        print("="*80)
        print("Salvando progresso atual...")
        simulador.umbra.salvar()
        simulador.apolo.salvar_memoria()
        print("✓ Memórias salvas com sucesso")
    except Exception as e:
        print()
        print("="*80)
        print("ERRO DURANTE O TREINAMENTO")
        print("="*80)
        print(f"Erro: {e}")
        print()
        print("Tentando salvar progresso...")
        try:
            simulador.umbra.salvar()
            simulador.apolo.salvar_memoria()
            print("✓ Memórias salvas com sucesso")
        except:
            print("✗ Falha ao salvar memórias")


if __name__ == "__main__":
    main()
