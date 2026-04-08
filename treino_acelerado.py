"""
================================================================================
TREINO ACELERADO HEADLESS - UMBRA VS APOLO (SELF-PLAY)
================================================================================

Script de convergência Q-Learning em ambiente matemático puro.
Executa milhares de frames/segundo sem renderização visual.

PILARES ARQUITETURAIS:
1. Ambiente Headless Absoluto (sem pygame.display)
2. Proteção da Memória Bayesiana (desativa registrar_esquiva_player)
3. Simulação Assíncrona do Embate (loop de episódios)
4. Taxa de Exploração Controlada (20% → 1% com decaimento)
5. Salvamento Seguro (sobrescreve JSONs ao final)
6. Gerenciamento Térmico (lotes de 50 episódios + sleep)

AUTOR: Sistema de Treinamento Autônomo
DATA: 2024
================================================================================
"""

import math
import random
import json
import os
import time
from collections import deque

# Importações mínimas necessárias (sem pygame.display)
from habilidade_boss import MemoriaEvolutivaUmbra

# Constantes do ambiente (importadas de Variaveis.py)
try:
    from Variaveis import largura_mapa, altura_mapa, largura_personagem, altura_personagem, largura_boss, altura_boss
except ImportError:
    # Fallback caso Variaveis.py não esteja acessível
    largura_mapa = 1360
    altura_mapa = 768
    largura_personagem = 50
    altura_personagem = 50
    largura_boss = 80
    altura_boss = 80


class AgenteApoloHeadless:
    """
    Versão headless do Apolo para treinamento acelerado.
    Idêntica à classe original, mas sem dependências de pygame.
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

    def obter_estado(self, pos_p, pos_boss, projeteis_boss, cd_teleporte, armadilhas_ativas):
        """
        Versão simplificada do obter_estado para ambiente headless.
        Retorna: [QUADRANTE_BOSS]_[PERIGO_DIR]_[CD_TELEPORTE]_[CHAO_STATUS]
        """
        px, py = pos_p
        bx, by = pos_boss
        
        # 1. QUADRANTE DO BOSS
        dx = bx - px
        dy = by - py
        if abs(dx) > abs(dy):
            quadrante_boss = "L" if dx > 0 else "O"
        else:
            quadrante_boss = "S" if dy > 0 else "N"
        
        # 2. PERIGO DE PROJÉTEIS
        perigo_dir = "LIVRE"
        for proj in projeteis_boss:
            proj_x, proj_y = proj['x'], proj['y']
            if math.hypot(proj_x - px, proj_y - py) < 150:
                dx_p = proj_x - px
                dy_p = proj_y - py
                if abs(dx_p) > abs(dy_p):
                    perigo_dir = "L" if dx_p > 0 else "O"
                else:
                    perigo_dir = "S" if dy_p > 0 else "N"
                break
        
        # 3. CHÃO LETAL (armadilhas ativas)
        chao_status = "LETAL" if armadilhas_ativas else "SEGURO"
        
        return f"{quadrante_boss}_{perigo_dir}_{cd_teleporte}_{chao_status}"

    def pensar(self, pos_p, pos_boss, projeteis_boss, cd_teleporte, vida_jogador, vida_boss, armadilhas_ativas):
        """
        Versão headless do método pensar.
        """
        self.direcao_x = 0
        self.direcao_y = 0
        self.usar_dash = False

        # Cálculo de recompensa
        recompensa = 0
        if self.vida_jogador_anterior > 0:
            if vida_jogador < self.vida_jogador_anterior:
                recompensa -= 50
            if vida_boss < self.vida_boss_anterior:
                recompensa += 30
            if vida_jogador > self.vida_jogador_anterior:
                recompensa += 100

        self.vida_jogador_anterior = vida_jogador
        self.vida_boss_anterior = vida_boss

        # Obter estado atual
        estado_atual = self.obter_estado(pos_p, pos_boss, projeteis_boss, cd_teleporte, armadilhas_ativas)

        # Inicializar estados na Q-Table
        if self.estado_anterior not in self.q_table:
            self.q_table[self.estado_anterior] = [0.0] * 5
        if estado_atual not in self.q_table:
            self.q_table[estado_atual] = [0.0] * 5

        # Atualização Q-Learning (Bellman)
        q_antigo = self.q_table[self.estado_anterior][self.acao_anterior]
        max_q_novo = max(self.q_table[estado_atual])
        self.q_table[self.estado_anterior][self.acao_anterior] = q_antigo + 0.2 * (recompensa + 0.9 * max_q_novo - q_antigo)

        # Seleção de ação (epsilon-greedy)
        if random.random() < self.taxa_exploracao:
            acao = random.choice([0, 1, 2, 3, 4])
        else:
            acao = self.q_table[estado_atual].index(max(self.q_table[estado_atual]))

        self.estado_anterior = estado_atual
        self.acao_anterior = acao

        # Tradução de ação para movimento
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


class SimuladorCombateHeadless:
    """
    Simulador matemático puro de combate Umbra vs Apolo.
    Opera sem renderização visual, executando apenas física e colisões.
    """
    
    def __init__(self, episodios_totais=500, episodios_por_lote=50):
        self.episodios_totais = episodios_totais
        self.episodios_por_lote = episodios_por_lote
        
        # Instanciar IAs
        self.umbra = MemoriaEvolutivaUmbra()
        self.apolo = AgenteApoloHeadless()
        
        # Estatísticas
        self.vitorias_umbra = 0
        self.vitorias_apolo = 0
        
        # Configurações de decaimento de exploração
        self.exploracao_inicial = 0.20
        self.exploracao_final = 0.01
        
        print("="*80)
        print("SIMULADOR DE COMBATE HEADLESS INICIALIZADO")
        print("="*80)
        print(f"Episódios totais: {self.episodios_totais}")
        print(f"Episódios por lote: {self.episodios_por_lote}")
        print(f"Exploração: {self.exploracao_inicial*100:.0f}% → {self.exploracao_final*100:.0f}%")
        print("="*80)
        print()

    def calcular_taxa_exploracao(self, episodio_atual):
        """
        Decaimento exponencial da taxa de exploração.
        Episódio 0: 20%
        Episódio final: 1%
        """
        progresso = episodio_atual / self.episodios_totais
        taxa = self.exploracao_inicial * ((self.exploracao_final / self.exploracao_inicial) ** progresso)
        return max(self.exploracao_final, taxa)

    def resetar_episodio(self):
        """
        Reseta o estado do jogo para um novo episódio.
        """
        # Posições iniciais
        pos_apolo = [largura_mapa // 2, altura_mapa - 150]
        pos_umbra = [largura_mapa // 2, 150]
        
        # Vidas
        vida_apolo = 1000.0
        vida_umbra = 1600.0
        vida_max_apolo = 1000.0
        vida_max_umbra = 1600.0
        
        # Projéteis e armadilhas
        projeteis_umbra = []
        
        # Histórico de movimento do Apolo (para discretização da Umbra)
        historico_apolo = deque(maxlen=60)
        
        # Cooldowns
        cd_ataque_umbra = 0
        cd_teleporte_apolo = 0
        cd_habilidade_especial = 0
        
        # Tempo simulado
        tempo_simulado = 0
        
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
            'tempo_simulado': tempo_simulado
        }

    def simular_frame(self, estado):
        """
        Simula um único frame matemático do combate.
        Retorna True se o episódio terminou, False caso contrário.
        """
        # Incrementar tempo
        estado['tempo_simulado'] += 16  # ~60 FPS
        
        # Atualizar cooldowns
        estado['cd_ataque_umbra'] = max(0, estado['cd_ataque_umbra'] - 16)
        estado['cd_teleporte_apolo'] = max(0, estado['cd_teleporte_apolo'] - 16)
        estado['cd_habilidade_especial'] = max(0, estado['cd_habilidade_especial'] - 16)
        
        # ===== DECISÃO DO APOLO =====
        cd_teleporte_bool = estado['cd_teleporte_apolo'] == 0
        armadilhas_ativas = estado['cd_habilidade_especial'] > 0  # Simplificação
        
        self.apolo.pensar(
            estado['pos_apolo'],
            estado['pos_umbra'],
            estado['projeteis_umbra'],
            cd_teleporte_bool,
            estado['vida_apolo'],
            estado['vida_umbra'],
            armadilhas_ativas
        )
        
        # Aplicar movimento do Apolo
        velocidade_apolo = 5.0
        if self.apolo.usar_dash and cd_teleporte_bool:
            velocidade_apolo = 15.0
            estado['cd_teleporte_apolo'] = 3000  # 3 segundos
        
        estado['pos_apolo'][0] += self.apolo.direcao_x * velocidade_apolo
        estado['pos_apolo'][1] += self.apolo.direcao_y * velocidade_apolo
        
        # Limitar posição do Apolo aos limites do mapa
        estado['pos_apolo'][0] = max(0, min(largura_mapa - largura_personagem, estado['pos_apolo'][0]))
        estado['pos_apolo'][1] = max(0, min(altura_mapa - altura_personagem, estado['pos_apolo'][1]))
        
        # Registrar histórico (SEM atualizar memória Bayesiana - PILAR 2)
        estado['historico_apolo'].append(tuple(estado['pos_apolo']))
        
        # ===== DECISÃO DA UMBRA =====
        vida_perc_umbra = estado['vida_umbra'] / estado['vida_max_umbra']
        dist_apolo = math.hypot(
            estado['pos_umbra'][0] - estado['pos_apolo'][0],
            estado['pos_umbra'][1] - estado['pos_apolo'][1]
        )
        sob_fogo = len(estado['projeteis_umbra']) > 0  # Simplificação
        
        estado_umbra = self.umbra.discretizar_estado(
            vida_perc_umbra,
            dist_apolo,
            sob_fogo,
            list(estado['historico_apolo']),
            "Fase_Base"
        )
        
        # Ações disponíveis da Umbra
        acoes_umbra = ["ATAQUE"]
        if estado['cd_habilidade_especial'] == 0:
            acoes_umbra.append("HABILIDADE_ESPECIAL")
        
        acao_umbra = self.umbra.decidir(estado_umbra, acoes_umbra)
        
        # Executar ação da Umbra
        if acao_umbra == "ATAQUE" and estado['cd_ataque_umbra'] == 0:
            # Criar projétil
            angulo = math.atan2(
                estado['pos_apolo'][1] - estado['pos_umbra'][1],
                estado['pos_apolo'][0] - estado['pos_umbra'][0]
            )
            estado['projeteis_umbra'].append({
                'x': estado['pos_umbra'][0],
                'y': estado['pos_umbra'][1],
                'angulo': angulo,
                'velocidade': 9.0
            })
            estado['cd_ataque_umbra'] = 1250
        
        elif acao_umbra == "HABILIDADE_ESPECIAL":
            estado['cd_habilidade_especial'] = 8000  # 8 segundos
            # Armadilha ativa (simplificação: dano contínuo)
        
        # ===== ATUALIZAR PROJÉTEIS =====
        projeteis_ativos = []
        for proj in estado['projeteis_umbra']:
            proj['x'] += math.cos(proj['angulo']) * proj['velocidade']
            proj['y'] += math.sin(proj['angulo']) * proj['velocidade']
            
            # Verificar colisão com Apolo
            dist_proj = math.hypot(
                proj['x'] - estado['pos_apolo'][0],
                proj['y'] - estado['pos_apolo'][1]
            )
            
            if dist_proj < 30:  # Raio de colisão
                estado['vida_apolo'] -= 50
                self.umbra.treinar(2.0, prioridade=True)  # Recompensa por acerto
                # Projétil destruído, não adiciona à lista
            elif 0 <= proj['x'] <= largura_mapa and 0 <= proj['y'] <= altura_mapa:
                projeteis_ativos.append(proj)
        
        estado['projeteis_umbra'] = projeteis_ativos
        
        # ===== DANO DE ARMADILHA =====
        if armadilhas_ativas:
            estado['vida_apolo'] -= 0.5  # Dano contínuo por frame
        
        # ===== VERIFICAR FIM DO EPISÓDIO =====
        if estado['vida_apolo'] <= 0:
            self.umbra.treinar(500.0, prioridade=True)
            self.apolo.q_table[self.apolo.estado_anterior][self.apolo.acao_anterior] -= 500.0
            return True, "UMBRA"
        
        if estado['vida_umbra'] <= 0:
            self.umbra.treinar(-500.0, prioridade=True)
            self.apolo.q_table[self.apolo.estado_anterior][self.apolo.acao_anterior] += 500.0
            return True, "APOLO"
        
        # Timeout (30 segundos simulados)
        if estado['tempo_simulado'] > 30000:
            # Empate: quem tem mais vida ganha
            if estado['vida_umbra'] > estado['vida_apolo']:
                return True, "UMBRA"
            else:
                return True, "APOLO"
        
        return False, None

    def executar_episodio(self, episodio_num):
        """
        Executa um episódio completo de combate.
        """
        estado = self.resetar_episodio()
        
        # Atualizar taxa de exploração
        taxa_exploracao = self.calcular_taxa_exploracao(episodio_num)
        self.umbra.exploracao = taxa_exploracao
        self.apolo.taxa_exploracao = taxa_exploracao
        
        # Loop de frames
        frames = 0
        max_frames = 2000  # Limite de segurança
        
        while frames < max_frames:
            terminado, vencedor = self.simular_frame(estado)
            
            if terminado:
                if vencedor == "UMBRA":
                    self.vitorias_umbra += 1
                else:
                    self.vitorias_apolo += 1
                return vencedor
            
            frames += 1
        
        # Timeout forçado
        return "TIMEOUT"

    def executar_treinamento(self):
        """
        Executa o treinamento completo em lotes.
        """
        inicio_total = time.time()
        
        for lote in range(0, self.episodios_totais, self.episodios_por_lote):
            inicio_lote = time.time()
            
            episodios_neste_lote = min(self.episodios_por_lote, self.episodios_totais - lote)
            
            for i in range(episodios_neste_lote):
                episodio_global = lote + i
                vencedor = self.executar_episodio(episodio_global)
            
            # Fim do lote: exibir estatísticas
            tempo_lote = time.time() - inicio_lote
            progresso = ((lote + episodios_neste_lote) / self.episodios_totais) * 100
            
            print(f"[LOTE {lote//self.episodios_por_lote + 1}] Episódios {lote+1}-{lote+episodios_neste_lote}")
            print(f"  Progresso: {progresso:.1f}%")
            print(f"  Placar: Umbra {self.vitorias_umbra} x {self.vitorias_apolo} Apolo")
            print(f"  Q-Table Umbra: {len(self.umbra.q_table)} estados")
            print(f"  Q-Table Apolo: {len(self.apolo.q_table)} estados")
            print(f"  Taxa Exploração: {self.umbra.exploracao*100:.2f}%")
            print(f"  Tempo do lote: {tempo_lote:.2f}s")
            print(f"  FPS simulado: {episodios_neste_lote * 1000 / tempo_lote:.0f} frames/s")
            print()
            
            # PILAR 6: Gerenciamento Térmico
            if lote + episodios_neste_lote < self.episodios_totais:
                print("  [RESFRIAMENTO] Aguardando 2 segundos...")
                time.sleep(2)
                print()
        
        # Estatísticas finais
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
        
        # PILAR 5: Salvamento Seguro
        print("Salvando memórias...")
        self.umbra.salvar()
        self.apolo.salvar_memoria()
        print("✓ memoria_umbra.json atualizado")
        print("✓ apolo_memoria.json atualizado")
        print()
        print("Treinamento acelerado finalizado com sucesso!")


def main():
    """
    Ponto de entrada do script.
    """
    print()
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "TREINO ACELERADO HEADLESS" + " "*33 + "║")
    print("║" + " "*25 + "UMBRA VS APOLO" + " "*40 + "║")
    print("╚" + "="*78 + "╝")
    print()
    
    # Configuração do treinamento
    EPISODIOS_TOTAIS = 500
    EPISODIOS_POR_LOTE = 50
    
    # Criar simulador
    simulador = SimuladorCombateHeadless(
        episodios_totais=EPISODIOS_TOTAIS,
        episodios_por_lote=EPISODIOS_POR_LOTE
    )
    
    # Executar treinamento
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
