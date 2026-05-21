import pygame
import requests
import json
import os

pygame.init()

LARGURA = 1000
ALTURA = 700
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Telemetria Neural: Umbra")

PRETO_FUNDO = (12, 12, 18)
PRETO_PAINEL = (20, 20, 28)
VERDE_NEON = (0, 255, 128)
ROXO_UMBRA = (150, 50, 255)
BRANCO = (240, 240, 240)
CINZA = (60, 60, 70)
VERMELHO = (255, 60, 60)
AZUL_DADOS = (0, 180, 255)

try:
    fonte_titulo = pygame.font.SysFont("consolas", 32, bold=True)
    fonte_sub = pygame.font.SysFont("consolas", 18, bold=True)
    fonte_texto = pygame.font.SysFont("consolas", 14)
    fonte_barras = pygame.font.SysFont("consolas", 12)
except:
    fonte_titulo = pygame.font.Font(None, 36)
    fonte_sub = pygame.font.Font(None, 24)
    fonte_texto = pygame.font.Font(None, 20)
    fonte_barras = pygame.font.Font(None, 18)

# Dicionário estático absoluto de todas as ações possíveis
ACOES_MECANICAS = [
    "ATAQUE", "SIFON", "TELEPORTE", 
    "CERCAR", "FUGIR", "INTERCEPTAR", 
    "ORBITAR", "VORTICE", "PRISAO", 
    "MIASMA", "DESCARGA_ELETRICA", "CAMINHO_ESPINHOS", 
    "TRANSMUTAR_VORTICE", "TRANSMUTAR_GRAVIDADE", "TRANSMUTAR_NECROSE", 
    "TRANSMUTAR_RESSONANCIA", "TRANSMUTAR_HEMORRAGIA", "TRANSMUTAR_ATRITO"
]

def carregar_historico():
    try:
        if os.path.exists("saves/historico_batalhas.json"):
            with open("saves/historico_batalhas.json", "r") as f:
                dados = json.load(f)
                vencedores = [d.get("vencedor", "") for d in dados]
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

def desenhar_painel(superficie, x, y, larg, alt, titulo, cor_borda):
    pygame.draw.rect(superficie, PRETO_PAINEL, (x, y, larg, alt), border_radius=8)
    pygame.draw.rect(superficie, cor_borda, (x, y, larg, alt), 2, border_radius=8)
    if titulo:
        txt = fonte_sub.render(titulo, True, BRANCO)
        superficie.blit(txt, (x + 15, y + 15))
        pygame.draw.line(superficie, CINZA, (x + 10, y + 40), (x + larg - 10, y + 40), 1)

relogio = pygame.time.Clock()
rodando = True

while rodando:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            rodando = False

    tela.fill(PRETO_FUNDO)

    try:
        resposta = requests.get("http://localhost:5000/dados", timeout=0.1)
        dados_ia = resposta.json()
        conectado = True
    except:
        dados_ia = {}
        conectado = False

    titulo = fonte_titulo.render("CÓRTEX ANALÍTICO - UMBRA", True, ROXO_UMBRA)
    tela.blit(titulo, (30, 20))
    
    status_cor = VERDE_NEON if conectado else VERMELHO
    status_txt = "STATUS: CONECTADO AO COLISEU NEURAL" if conectado else "STATUS: AGUARDANDO CONEXÃO FLASK..."
    tela.blit(fonte_sub.render(status_txt, True, status_cor), (30, 60))

    if conectado:
        desenhar_painel(tela, 30, 100, 450, 140, "ESTADO SENSORIAL & DIRETRIZ", AZUL_DADOS)
        estado_atual = dados_ia.get("estado_atual", "DESCONHECIDO")
        tela.blit(fonte_texto.render("Vetor de Estado Ativo:", True, CINZA), (45, 150))
        tela.blit(fonte_sub.render(estado_atual, True, VERDE_NEON), (45, 170))
        
        decisoes = dados_ia.get("decisao_ativa", [])
        decisoes_str = " | ".join(decisoes) if decisoes else "PROCESSANDO..."
        tela.blit(fonte_texto.render("Ação Imediata:", True, CINZA), (45, 200))
        tela.blit(fonte_sub.render(decisoes_str, True, ROXO_UMBRA), (45, 220))

        desenhar_painel(tela, 500, 100, 470, 140, "VIÉS BAYESIANO (PREDIÇÃO)", AZUL_DADOS)
        bias = dados_ia.get("bias_bayesiano", [0, 0])
        tela.blit(fonte_texto.render(f"Eixo X (Esquerda / Direita) : {bias[0]:.4f}", True, BRANCO), (515, 160))
        tela.blit(fonte_texto.render(f"Eixo Y (Cima / Baixo)      : {bias[1]:.4f}", True, BRANCO), (515, 190))

        desenhar_painel(tela, 30, 260, 940, 300, "ÁRVORE DE DECISÃO (MATRIZ DUPLA)", ROXO_UMBRA)
        pesos = dados_ia.get("rede_completa", {}).get(estado_atual, {})
        
        # Garante que todas as ações sejam exibidas, mesmo que a IA ainda não as conheça neste estado
        acoes_exibicao = list(ACOES_MECANICAS)
        for a in pesos.keys():
            if a not in acoes_exibicao:
                acoes_exibicao.append(a)
                
        max_peso = max(pesos.values()) if pesos else 0
        min_peso = min(pesos.values()) if pesos else 0
        amplitude = max(0.0001, max_peso - min_peso)

        y_inicial = 310
        passo_y = 25 # Altura reduzida para acomodar as duas colunas perfeitamente

        for i, acao in enumerate(acoes_exibicao):
            # Lógica de Coluna Dupla
            coluna = i % 2
            linha = i // 2
            
            x_base = 45 if coluna == 0 else 510
            y_barra = y_inicial + (linha * passo_y)
            
            if y_barra > 530: # Proteção visual do limite inferior do painel
                break
                
            valor = pesos.get(acao, 0.0)
            
            # Textos e Rótulos
            tela.blit(fonte_barras.render(f"{acao[:18]:<18}", True, BRANCO), (x_base, y_barra + 2))
            
            largura_maxima = 160
            x_barra = x_base + 160
            largura_barra = int(((valor - min_peso) / amplitude) * largura_maxima)
            largura_barra = max(3, min(largura_maxima, largura_barra)) 
            
            # Dinâmica de cores
            if valor == 0.0 and max_peso == 0.0 and min_peso == 0.0:
                cor_barra = CINZA # Estado inexplorado
            elif valor == max_peso:
                cor_barra = VERDE_NEON
            elif valor >= 0:
                cor_barra = AZUL_DADOS
            else:
                cor_barra = VERMELHO
            
            pygame.draw.rect(tela, CINZA, (x_barra, y_barra, largura_maxima, 14), border_radius=3)
            pygame.draw.rect(tela, cor_barra, (x_barra, y_barra, largura_barra, 14), border_radius=3)
            
            tela.blit(fonte_barras.render(f"{valor:.4f}", True, BRANCO), (x_barra + largura_maxima + 10, y_barra + 2))

    desenhar_painel(tela, 30, 580, 940, 100, "RESUMO EVOLUTIVO", CINZA)
    total_gen, taxa_geral, taxa_50 = carregar_historico()
    
    tela.blit(fonte_texto.render(f"Gerações Processadas: {total_gen}", True, VERDE_NEON), (45, 635))
    tela.blit(fonte_texto.render(f"Letalidade Global: {taxa_geral:.2f}%", True, BRANCO), (350, 635))
    tela.blit(fonte_texto.render(f"Letalidade (Últimas 50): {taxa_50:.2f}%", True, ROXO_UMBRA), (650, 635))

    pygame.display.flip()
    relogio.tick(15)

pygame.quit()