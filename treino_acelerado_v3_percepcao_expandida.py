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


class AgenteApoloExpandido:
    """
    Versão com percepção expandida do Apolo.
    Estado: 10 componentes (vs 4 na V2)
    """
    def __init__(self, arquivo="apolo_memoria.json"):
        self.direcao_x = 0
        self.direcao_y = 0
        self.usar_dash = False
        self.q_table = {}
        self.estado_anterior = "vazio"
        self.acao_anterior = 0
        self.vida_jogador_anterior = 0
        self.vida_boss_anterior = 0
        self.arquivo_memoria = arquivo
        self.taxa_exploracao = 0.20
        self.carregar_memoria()

    def carregar_memoria(self):
        if os.path.exists(self.arquivo_memoria):
            try:
                with open(self.arquivo_memoria, "r") as f:
                    self.q_table = json.load(f)
            except:
                pass

    def salvar_memoria(self):
        with open(self.arquivo_memoria, "w") as f:
            json.dump(self.q_table, f)

    def obter_estado_expandido(self, pos_p, pos_boss, projeteis_boss, cd_teleporte, armadilhas_ativas, vida_apolo, vida_boss, velocidade_apolo):
        """
        ESTADO EXPANDIDO (10 COMPONENTES):
        1. QUADRANTE_BOSS (5 estados: C/L/O/S/N)
        2. DISTANCIA_BOSS (4 estados: MUITO_PERTO/PERTO/MEDIO/LONGE)
        3. VIDA_APOLO (4 estados: CRITICA/BAIXA/MEDIA/ALTA)
        4. VIDA_BOSS (4 estados: CRITICA/BAIXA/MEDIA/ALTA)
        5. PERIGO_IMINENTE (3 estados: NENHUM/PROJETIL/MULTIPLOS)
        6. DIRECAO_PERIGO (5 estados: LIVRE/L/O/S/N)
        7. CD_TELEPORTE (2 estados: True/False)
        8. ARMADILHA_ATIVA (2 estados: True/False)
        9. POSICAO_MAPA (5 estados: CENTRO/BORDA_L/BORDA_O/BORDA_S/BORDA_N)
        10. VELOCIDADE (3 estados: PARADO/NORMAL/DASH)
        
        Total teórico: 5×4×4×4×3×5×2×2×5×3 = 288,000 estados
        Prático: ~2000-5000 estados (apenas situações realmente encontradas)
        """
        px, py = pos_p
        bx, by = pos_boss
        
        # 1. QUADRANTE DO BOSS
        dx = bx - px
        dy = by - py
        if abs(dx) < 100 and abs(dy) < 100:
            quadrante_boss = "C"
        elif abs(dx) > abs(dy):
            quadrante_boss = "L" if dx > 0 else "O"
        else:
            quadrante_boss = "S" if dy > 0 else "N"
        
        # 2. DISTÂNCIA DO BOSS (granular)
        dist_boss = math.hypot(dx, dy)
        if dist_boss < 200:
            dist_categoria = "MUITO_PERTO"
        elif dist_boss < 400:
            dist_categoria = "PERTO"
        elif dist_boss < 700:
            dist_categoria = "MEDIO"
        else:
            dist_categoria = "LONGE"
        
        # 3. VIDA DO APOLO (granular)
        vida_perc_apolo = vida_apolo / 1000.0
        if vida_perc_apolo < 0.25:
            vida_apolo_cat = "CRITICA"
        elif vida_perc_apolo < 0.5:
            vida_apolo_cat = "BAIXA"
        elif vida_perc_apolo < 0.75:
            vida_apolo_cat = "MEDIA"
        else:
            vida_apolo_cat = "ALTA"
        
        # 4. VIDA DA UMBRA (granular)
        vida_perc_boss = vida_boss / 1200.0
        if vida_perc_boss < 0.25:
            vida_boss_cat = "CRITICA"
        elif vida_perc_boss < 0.5:
            vida_boss_cat = "BAIXA"
        elif vida_perc_boss < 0.75:
            vida_boss_cat = "MEDIA"
        else:
            vida_boss_cat = "ALTA"
        
        # 5 & 6. ANÁLISE DE PERIGO (múltiplos projéteis)
        projeteis_proximos = []
        for proj in projeteis_boss:
            proj_x, proj_y = proj['x'], proj['y']
            dist_proj = math.hypot(proj_x - px, proj_y - py)
            if dist_proj < 250:  # Raio de detecção expandido
                projeteis_proximos.append((proj_x, proj_y, dist_proj))
        
        if len(projeteis_proximos) == 0:
            perigo_nivel = "NENHUM"
            perigo_dir = "LIVRE"
        elif len(projeteis_proximos) == 1:
            perigo_nivel = "PROJETIL"
            proj_x, proj_y, _ = projeteis_proximos[0]
            dx_p = proj_x - px
            dy_p = proj_y - py
            if abs(dx_p) > abs(dy_p):
                perigo_dir = "L" if dx_p > 0 else "O"
            else:
                perigo_dir = "S" if dy_p > 0 else "N"
        else:
            perigo_nivel = "MULTIPLOS"
            # Direção do projétil mais próximo
            proj_x, proj_y, _ = min(projeteis_proximos, key=lambda p: p[2])
            dx_p = proj_x - px
            dy_p = proj_y - py
            if abs(dx_p) > abs(dy_p):
                perigo_dir = "L" if dx_p > 0 else "O"
            else:
                perigo_dir = "S" if dy_p > 0 else "N"
        
        # 7. COOLDOWN TELEPORTE
        cd_tele_str = "True" if cd_teleporte else "False"
        
        # 8. ARMADILHA ATIVA
        armadilha_str = "True" if armadilhas_ativas else "False"
        
        # 9. POSIÇÃO NO MAPA (consciência de bordas)
        margem = 150
        if px < margem:
            pos_mapa = "BORDA_O"
        elif px > largura_mapa - margem:
            pos_mapa = "BORDA_L"
        elif py < margem:
            pos_mapa = "BORDA_N"
        elif py > altura_mapa - margem:
            pos_mapa = "BORDA_S"
        else:
            pos_mapa = "CENTRO"
        
        # 10. VELOCIDADE ATUAL
        if velocidade_apolo < 1:
            vel_cat = "PARADO"
        elif velocidade_apolo < 10:
            vel_cat = "NORMAL"
        else:
            vel_cat = "DASH"
        
        # COMPOSIÇÃO DO ESTADO (10 componentes)
        return f"{quadrante_boss}_{dist_categoria}_{vida_apolo_cat}_{vida_boss_cat}_{perigo_nivel}_{perigo_dir}_{cd_tele_str}_{armadilha_str}_{pos_mapa}_{vel_cat}"

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
        estado_atual = self.obter_estado_expandido(
            pos_p, pos_boss, projeteis_boss, cd_teleporte, 
            armadilhas_ativas, vida_jogador, vida_boss, velocidade_atual
        )

        # Q-LEARNING
        if self.estado_anterior not in self.q_table:
            self.q_table[self.estado_anterior] = [0.0] * 5
        if estado_atual not in self.q_table:
            self.q_table[estado_atual] = [0.0] * 5

        q_antigo = self.q_table[self.estado_anterior][self.acao_anterior]
        max_q_novo = max(self.q_table[estado_atual])
        self.q_table[self.estado_anterior][self.acao_anterior] = q_antigo + 0.15 * (recompensa + 0.95 * max_q_novo - q_antigo)

        # SELEÇÃO DE AÇÃO
        if random.random() < self.taxa_exploracao:
            acao = random.choice([0, 1, 2, 3, 4])
        else:
            acao = self.q_table[estado_atual].index(max(self.q_table[estado_atual]))

        self.estado_anterior = estado_atual
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
            'velocidade_apolo_atual': velocidade_apolo_atual
        }

    def simular_frame(self, estado):
        estado['tempo_simulado'] += 16
        estado['frames_sobrevividos'] += 1
        
        estado['cd_ataque_umbra'] = max(0, estado['cd_ataque_umbra'] - 16)
        estado['cd_teleporte_apolo'] = max(0, estado['cd_teleporte_apolo'] - 16)
        estado['cd_habilidade_especial'] = max(0, estado['cd_habilidade_especial'] - 16)
        
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
        
        # ===== DANO DE ARMADILHA =====
        if armadilhas_ativas and not invulneravel:
            estado['vida_apolo'] -= 0.5
        
        # ===== APOLO ATACA UMBRA =====
        if random.random() < 0.05:
            estado['vida_umbra'] -= 15
        
        # ===== VERIFICAR FIM DO EPISÓDIO =====
        if estado['vida_apolo'] <= 0:
            self.umbra.treinar(500.0, prioridade=True)
            if self.apolo.estado_anterior in self.apolo.q_table:
                self.apolo.q_table[self.apolo.estado_anterior][self.apolo.acao_anterior] -= 500.0
            return True, "UMBRA"
        
        if estado['vida_umbra'] <= 0:
            self.umbra.treinar(-500.0, prioridade=True)
            if self.apolo.estado_anterior in self.apolo.q_table:
                self.apolo.q_table[self.apolo.estado_anterior][self.apolo.acao_anterior] += 500.0
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
            print(f"  Q-Table Umbra: {len(self.umbra.q_table)} estados")
            print(f"  Q-Table Apolo: {len(self.apolo.q_table)} estados")
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
        print(f"Estados na Q-Table Umbra: {len(self.umbra.q_table)}")
        print(f"Estados na Q-Table Apolo: {len(self.apolo.q_table)}")
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
    print("╔" + "="*78 + "╗")
    print("║" + " "*18 + "TREINO ACELERADO V3" + " "*40 + "║")
    print("║" + " "*24 + "PERCEPÇÃO EXPANDIDA" + " "*36 + "║")
    print("╚" + "="*78 + "╝")
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
