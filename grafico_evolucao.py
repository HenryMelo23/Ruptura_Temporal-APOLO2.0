import json
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os
from matplotlib.lines import Line2D

arquivo_historico = "historico_batalhas.json"

# Figura ampliada para acomodar os dois ecossistemas e o painel unificado
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
fig.canvas.manager.set_window_title('Centro de Comando Neural: Telemetria Absoluta')

def atualizar_grafico(frame):
    if os.path.exists(arquivo_historico):
        try:
            with open(arquivo_historico, "r") as f:
                dados = json.load(f)
        except Exception:
            return
            
        if len(dados) == 0:
            return

        geracoes = [d["geracao"] for d in dados]
        duracoes = [d["duracao"] for d in dados]
        vencedores = [d["vencedor"] for d in dados]

        ax1.clear()
        ax2.clear()
        
        # ==========================================
        # EIXO ESQUERDO: DURAÇÃO E LETALIDADE
        # ==========================================
        cores = ['blue' if v == 'Apolo' else 'purple' for v in vencedores]
        ax1.scatter(geracoes, duracoes, c=cores, s=45, alpha=0.7, edgecolors='none')
        ax1.plot(geracoes, duracoes, color='gray', linestyle='--', alpha=0.3)

        if len(duracoes) >= 5:
            medias_moveis_5 = [sum(duracoes[i-5:i])/5 for i in range(5, len(duracoes)+1)]
            ax1.plot(geracoes[4:], medias_moveis_5, color='red', linewidth=1.5, alpha=0.8, label='Microtendência (5 ger)')

        if len(duracoes) >= 20:
            medias_moveis_20 = [sum(duracoes[i-20:i])/20 for i in range(20, len(duracoes)+1)]
            ax1.plot(geracoes[19:], medias_moveis_20, color='darkorange', linewidth=2.5, label='Macrotendência (20 ger)')

        ax1.set_title("Sobrevivência e Duração do Combate", fontsize=13, fontweight='bold')
        ax1.set_xlabel("Gerações de Combate", fontsize=11)
        ax1.set_ylabel("Duração do Combate (Segundos)", fontsize=11)
        ax1.grid(True, linestyle=':', alpha=0.5)

        legend_elements_ax1 = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='purple', markersize=10, label='Vitória: Umbra'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='Vitória: Apolo')
        ]
        if len(duracoes) >= 5:
            legend_elements_ax1.append(Line2D([0], [0], color='red', lw=1.5, label='Média 5 ger'))
        if len(duracoes) >= 20:
            legend_elements_ax1.append(Line2D([0], [0], color='darkorange', lw=2.5, label='Tendência (20 ger)'))
        ax1.legend(handles=legend_elements_ax1, loc='upper left')

        # ==========================================
        # EIXO DIREITO: SUPREMACIA CUMULATIVA
        # ==========================================
        vitorias_umbra_cumulativas = []
        vitorias_apolo_cumulativas = []
        acc_umbra = 0
        acc_apolo = 0
        
        for v in vencedores:
            if v == 'Umbra':
                acc_umbra += 1
            elif v == 'Apolo':
                acc_apolo += 1
            vitorias_umbra_cumulativas.append(acc_umbra)
            vitorias_apolo_cumulativas.append(acc_apolo)

        ax2.plot(geracoes, vitorias_umbra_cumulativas, color='purple', linewidth=3, label='Vitórias: Umbra', marker='o', markersize=4)
        ax2.plot(geracoes, vitorias_apolo_cumulativas, color='blue', linewidth=3, label='Vitórias: Apolo', marker='o', markersize=4)
        ax2.fill_between(geracoes, vitorias_umbra_cumulativas, color='purple', alpha=0.1)
        ax2.fill_between(geracoes, vitorias_apolo_cumulativas, color='blue', alpha=0.1)

        ax2.set_title("Supremacia Cumulativa", fontsize=13, fontweight='bold')
        ax2.set_xlabel("Gerações de Combate", fontsize=11)
        ax2.set_ylabel("Total de Vitórias", fontsize=11)
        ax2.grid(True, linestyle=':', alpha=0.5)
        ax2.legend(loc='upper left')

        # ==========================================
        # PAINEL HUD UNIFICADO (Ancorado no Eixo Direito)
        # ==========================================
        total_batalhas = len(vencedores)
        taxa_umbra_geral = (acc_umbra / total_batalhas) * 100 if total_batalhas > 0 else 0
        taxa_apolo_geral = (acc_apolo / total_batalhas) * 100 if total_batalhas > 0 else 0

        ultimas_50 = vencedores[-50:]
        taxa_umbra_50 = (ultimas_50.count('Umbra') / len(ultimas_50)) * 100 if len(ultimas_50) > 0 else 0
        
        duracoes_umbra = [duracoes[i] for i in range(total_batalhas) if vencedores[i] == 'Umbra']
        duracoes_apolo = [duracoes[i] for i in range(total_batalhas) if vencedores[i] == 'Apolo']
        media_tempo_umbra = sum(duracoes_umbra) / len(duracoes_umbra) if duracoes_umbra else 0
        media_tempo_apolo = sum(duracoes_apolo) / len(duracoes_apolo) if duracoes_apolo else 0

        hud_text = (
            f"DIAGNÓSTICO DO COLISEU\n"
            f"{'-'*22}\n"
            f"Gerações Totais: {total_batalhas}\n\n"
            f"[ABATES TOTAIS]\n"
            f"Umbra: {acc_umbra}\n"
            f"Apolo: {acc_apolo}\n\n"
            f"[TAXA DE DOMINAÇÃO]\n"
            f"Global Umbra: {taxa_umbra_geral:.1f}%\n"
            f"Global Apolo: {taxa_apolo_geral:.1f}%\n"
            f"Últ. 50 (Umbra): {taxa_umbra_50:.1f}%\n\n"
            f"[TEMPO DE ABATE]\n"
            f"Blitz Umbra: {media_tempo_umbra:.1f}s\n"
            f"Fuga Apolo:  {media_tempo_apolo:.1f}s"
        )
        
        props = dict(boxstyle='square,pad=0.5', facecolor='#0d0d0d', edgecolor='purple', alpha=0.9)
        ax2.text(1.05, 0.98, hud_text, transform=ax2.transAxes, fontsize=10,
                verticalalignment='top', bbox=props, color='#00ff00', fontfamily='monospace')

        # Calibração milimétrica das bordas para evitar cortes
        plt.subplots_adjust(left=0.05, right=0.85, wspace=0.15)

ani = FuncAnimation(fig, atualizar_grafico, interval=2000, cache_frame_data=False)
plt.show()