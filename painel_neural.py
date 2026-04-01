import pygame
import requests
import json
import os

pygame.init()

LARGURA = 900
ALTURA = 650
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Telemetria Neural: Umbra")

PRETO = (10, 10, 15)
VERDE_NEON = (0, 255, 100)
ROXO_UMBRA = (138, 43, 226)
BRANCO = (240, 240, 240)
CINZA = (50, 50, 50)
VERMELHO = (255, 50, 50)

try:
    fonte_titulo = pygame.font.SysFont("consolas", 28, bold=True)
    fonte_sub = pygame.font.SysFont("consolas", 20, bold=True)
    fonte_texto = pygame.font.SysFont("consolas", 16)
except:
    fonte_titulo = pygame.font.Font(None, 36)
    fonte_sub = pygame.font.Font(None, 28)
    fonte_texto = pygame.font.Font(None, 22)

def carregar_historico():
    try:
        if os.path.exists("historico_batalhas.json"):
            with open("historico_batalhas.json", "r") as f:
                dados = json.load(f)
                vencedores = [d["vencedor"] for d in dados]
                total = len(vencedores)
                if total == 0: return 0, 0, 0
                
                vitorias = vencedores.count("Umbra")
                taxa = (vitorias / total) * 100
                
                ultimos_50 = vencedores[-50:]
                taxa_50 = (ultimos_50.count("Umbra") / len(ultimos_50)) * 100 if ultimos_50 else 0
                
                return total, taxa, taxa_50
    except:
        pass
    return 0, 0, 0

relogio = pygame.time.Clock()
rodando = True

while rodando:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            rodando = False

    tela.fill(PRETO)

    try:
        resposta = requests.get("http://localhost:5000/dados", timeout=0.1)
        dados_ia = resposta.json()
        conectado = True
    except:
        dados_ia = {}
        conectado = False

    # --- RENDERIZAÇÃO DO CABEÇALHO ---
    titulo = fonte_titulo.render("CÓRTEX ANALÍTICO - UMBRA", True, ROXO_UMBRA)
    tela.blit(titulo, (20, 20))
    
    status_cor = VERDE_NEON if conectado else VERMELHO
    status_txt = "CONECTADO AO COLISEU" if conectado else "AGUARDANDO CONEXÃO FLASK..."
    tela.blit(fonte_texto.render(status_txt, True, status_cor), (20, 60))

    pygame.draw.line(tela, CINZA, (20, 90), (LARGURA - 20, 90), 2)

    # --- RENDERIZAÇÃO DOS DADOS NEURAIS (Se Conectado) ---
    if conectado:
        # 1. Estado Atual
        estado_atual = dados_ia.get("estado_atual", "DESCONHECIDO")
        tela.blit(fonte_sub.render("ESTADO SENSORIAL ATIVO:", True, BRANCO), (20, 110))
        tela.blit(fonte_texto.render(estado_atual, True, VERDE_NEON), (20, 140))

        # 2. Decisões Tomadas
        decisoes = dados_ia.get("decisao_ativa", [])
        decisoes_str = " | ".join(decisoes) if decisoes else "PROCESSANDO..."
        tela.blit(fonte_sub.render("DIRETRIZ DE AÇÃO IMEDIATA:", True, BRANCO), (20, 190))
        tela.blit(fonte_texto.render(decisoes_str, True, ROXO_UMBRA), (20, 220))

        # 3. Viés Bayesiano
        bias = dados_ia.get("bias_bayesiano", [0, 0])
        tela.blit(fonte_sub.render("VIÉS BAYESIANO (PREDIÇÃO DE FUGA):", True, BRANCO), (450, 110))
        tela.blit(fonte_texto.render(f"Eixo X (Esq/Dir): {bias[0]:.4f}", True, VERDE_NEON), (450, 140))
        tela.blit(fonte_texto.render(f"Eixo Y (Cima/Baixo): {bias[1]:.4f}", True, VERDE_NEON), (450, 170))

        # 4. Matriz de Pesos (Gráfico de Barras em Tempo Real)
        tela.blit(fonte_sub.render("ÁRVORE DE DECISÃO (PESOS Q-LEARNING):", True, BRANCO), (20, 290))
        pesos = dados_ia.get("rede_completa", {}).get(estado_atual, {})
        
        y_barra = 330
        if pesos:
            max_peso = max(pesos.values()) if pesos else 1
            min_peso = min(pesos.values()) if pesos else 0
            amplitude = max(1, max_peso - min_peso)

            for acao, valor in pesos.items():
                tela.blit(fonte_texto.render(f"{acao}", True, BRANCO), (20, y_barra))
                
                # Normalização para a barra caber na tela
                largura_barra = int(((valor - min_peso) / amplitude) * 400)
                largura_barra = max(10, largura_barra) 
                
                cor_barra = VERDE_NEON if valor == max_peso else ROXO_UMBRA
                pygame.draw.rect(tela, cor_barra, (180, y_barra, largura_barra, 20))
                tela.blit(fonte_texto.render(f"{valor:.2f}", True, BRANCO), (190 + largura_barra, y_barra))
                
                y_barra += 40
        else:
            tela.blit(fonte_texto.render("Buscando vetores...", True, CINZA), (20, y_barra))

    # --- RENDERIZAÇÃO DO HISTÓRICO GLOBAL ---
    pygame.draw.line(tela, CINZA, (20, ALTURA - 150), (LARGURA - 20, ALTURA - 150), 2)
    tela.blit(fonte_sub.render("RESUMO EVOLUTIVO (HISTÓRICO_BATALHAS.JSON)", True, BRANCO), (20, ALTURA - 130))
    
    total_gen, taxa_geral, taxa_50 = carregar_historico()
    
    tela.blit(fonte_texto.render(f"Gerações: {total_gen}", True, VERDE_NEON), (20, ALTURA - 90))
    tela.blit(fonte_texto.render(f"Letalidade Global: {taxa_geral:.1f}%", True, ROXO_UMBRA), (250, ALTURA - 90))
    tela.blit(fonte_texto.render(f"Letalidade (Últimas 50): {taxa_50:.1f}%", True, ROXO_UMBRA), (550, ALTURA - 90))

    pygame.display.flip()
    relogio.tick(15) # 15 FPS é perfeito para painéis de telemetria

pygame.quit()