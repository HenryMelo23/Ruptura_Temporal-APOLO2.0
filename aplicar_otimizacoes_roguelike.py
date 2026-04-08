#!/usr/bin/env python3
"""
SCRIPT DE APLICAÇÃO AUTOMÁTICA DE OTIMIZAÇÕES ROGUELIKE
Aplica as otimizações do GAMERE nos arquivos GAME.py, GAME2.py, GAME3.py e GAME4.py
"""

import os
import re

# Código das otimizações a serem adicionadas
IMPORTS_THREADING = """import threading
import time

# Lock para sincronização de inimigos (otimização roguelike)
lock_inimigos = threading.Lock()
"""

VARIAVEIS_THREADING = """
# ===== VARIÁVEIS DE THREADING E CRESCIMENTO ROGUELIKE =====
tempo_anterior_thread = 0
tempo_movimento_thread = 0
tempo_parado_thread = 0
movendo_thread = True
max_inimigos = 5  # Começa com 5, cresce até 12
inimigos_eliminados = 0
"""

FUNCAO_THREAD = """
def thread_atualizar_inimigos():
    \"\"\"Thread dedicada para atualizar movimento dos inimigos (otimização roguelike)\"\"\"
    global inimigos_comum, pos_x_personagem, pos_y_personagem
    global movendo_thread, tempo_anterior_thread, tempo_movimento_thread, tempo_parado_thread
    
    ultimo_tempo = time.time()
    
    while True:
        try:
            agora_thread = pygame.time.get_ticks()
            
            if inimigos_comum and len(inimigos_comum) > 0:
                with lock_inimigos:
                    if movendo_thread:
                        if agora_thread - tempo_anterior_thread >= tempo_movimento_thread:
                            tempo_anterior_thread = agora_thread
                            movendo_thread = False
                            tempo_movimento_thread = random.randint(3000, 7000)
                        
                        # Atualizar movimento dos inimigos
                        for inimigo in inimigos_comum:
                            dx = pos_x_personagem - inimigo["rect"].x
                            dy = pos_y_personagem - inimigo["rect"].y
                            distancia = math.sqrt(dx**2 + dy**2)
                            
                            if distancia > 0:
                                velocidade_inimigo = 2
                                inimigo["rect"].x += int((dx / distancia) * velocidade_inimigo)
                                inimigo["rect"].y += int((dy / distancia) * velocidade_inimigo)
                    else:
                        if agora_thread - tempo_anterior_thread >= tempo_parado_thread:
                            tempo_anterior_thread = agora_thread
                            movendo_thread = True
                            tempo_parado_thread = random.randint(10, 3000)
        except Exception as e:
            print(f"Erro na thread de inimigos: {e}")
        
        time.sleep(0.01)  # 100 FPS na thread
"""

FUNCAO_CRESCIMENTO = """
def aplicar_crescimento_personalizado():
    \"\"\"Sistema de crescimento escalável para roguelike\"\"\"
    global vida_inimigo_maxima, dano_inimigo, max_inimigos, inimigos_eliminados
    
    # Crescimento dos atributos do inimigo
    vida_inimigo_maxima = 30 + (inimigos_eliminados * 2)
    dano_inimigo = 10 + (inimigos_eliminados * 0.5)
    
    # Crescimento balanceado do número máximo de inimigos
    # A cada 30 eliminações aumenta o número de inimigos até o limite de 12
    if inimigos_eliminados % 30 == 0 and max_inimigos < 12:
        max_inimigos += 1
        print(f"[ROGUELIKE] Máximo de inimigos aumentado para {max_inimigos}")
"""

def adicionar_imports(conteudo):
    """Adiciona imports de threading se não existirem"""
    if "import threading" not in conteudo:
        # Adiciona após os imports existentes
        padrao = r"(import pygame.*?\n)"
        conteudo = re.sub(padrao, r"\1" + IMPORTS_THREADING, conteudo, count=1)
    return conteudo

def adicionar_variaveis(conteudo):
    """Adiciona variáveis de threading"""
    if "lock_inimigos" not in conteudo:
        # Adiciona após pygame.init()
        padrao = r"(pygame\.init\(\).*?\n)"
        conteudo = re.sub(padrao, r"\1" + VARIAVEIS_THREADING, conteudo, count=1)
    return conteudo

def adicionar_funcoes(conteudo):
    """Adiciona funções de threading e crescimento"""
    if "thread_atualizar_inimigos" not in conteudo:
        # Adiciona antes do loop principal
        padrao = r"(# Loop principal|while True:|# ===== LOOP PRINCIPAL =====)"
        conteudo = re.sub(padrao, FUNCAO_THREAD + "\n" + FUNCAO_CRESCIMENTO + "\n\n\\1", conteudo, count=1)
    return conteudo

def adicionar_lock_renderizacao(conteudo):
    """Adiciona lock na renderização de inimigos"""
    # Procura por loops de renderização de inimigos
    padrao = r"(for inimigo in inimigos_comum:)"
    if re.search(padrao, conteudo):
        # Adiciona with lock_inimigos antes do for
        conteudo = re.sub(
            r"(\s+)(for inimigo in inimigos_comum:)",
            r"\1with lock_inimigos:\n\1    \2",
            conteudo
        )
    return conteudo

def otimizar_fps(conteudo):
    """Otimiza FPS de 60 para 100"""
    conteudo = re.sub(r"\.tick\(60\)", ".tick(100)", conteudo)
    conteudo = re.sub(r"FPS\s*=\s*60", "FPS = 100", conteudo)
    return conteudo

def inicializar_thread(conteudo):
    """Adiciona inicialização da thread"""
    codigo_init = """
# Inicializar thread de inimigos (otimização roguelike)
tempo_anterior_thread = pygame.time.get_ticks()
tempo_movimento_thread = random.randint(2000, 7000)
tempo_parado_thread = random.randint(500, 700)
movendo_thread = True
threading.Thread(target=thread_atualizar_inimigos, daemon=True).start()
print("[ROGUELIKE] Thread de inimigos iniciada")
"""
    
    if "thread_atualizar_inimigos" in conteudo and "threading.Thread(target=thread_atualizar_inimigos" not in conteudo:
        # Adiciona antes do loop principal
        padrao = r"(while True:)"
        conteudo = re.sub(padrao, codigo_init + "\n\\1", conteudo, count=1)
    
    return conteudo

def processar_arquivo(caminho):
    """Processa um arquivo GAME aplicando todas as otimizações"""
    print(f"\n{'='*80}")
    print(f"Processando: {caminho}")
    print(f"{'='*80}")
    
    if not os.path.exists(caminho):
        print(f"❌ Arquivo não encontrado: {caminho}")
        return False
    
    # Ler arquivo
    with open(caminho, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    conteudo_original = conteudo
    
    # Aplicar otimizações
    print("  ⏳ Adicionando imports...")
    conteudo = adicionar_imports(conteudo)
    
    print("  ⏳ Adicionando variáveis...")
    conteudo = adicionar_variaveis(conteudo)
    
    print("  ⏳ Adicionando funções...")
    conteudo = adicionar_funcoes(conteudo)
    
    print("  ⏳ Adicionando locks de renderização...")
    conteudo = adicionar_lock_renderizacao(conteudo)
    
    print("  ⏳ Otimizando FPS...")
    conteudo = otimizar_fps(conteudo)
    
    print("  ⏳ Inicializando thread...")
    conteudo = inicializar_thread(conteudo)
    
    # Verificar se houve mudanças
    if conteudo == conteudo_original:
        print("  ℹ️  Nenhuma mudança necessária (já otimizado)")
        return True
    
    # Criar backup
    backup_path = caminho + ".backup"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(conteudo_original)
    print(f"  ✅ Backup criado: {backup_path}")
    
    # Salvar arquivo otimizado
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    print(f"  ✅ Arquivo otimizado salvo")
    
    return True

def main():
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "APLICADOR DE OTIMIZAÇÕES ROGUELIKE" + " "*30 + "║")
    print("║" + " "*20 + "Threading + Crescimento Escalável" + " "*25 + "║")
    print("╚" + "="*78 + "╝")
    print("\n")
    
    arquivos = ["GAME.py", "GAME2.py", "GAME3.py", "GAME4.py"]
    
    resultados = []
    
    for arquivo in arquivos:
        sucesso = processar_arquivo(arquivo)
        resultados.append((arquivo, sucesso))
    
    # Resumo
    print("\n" + "="*80)
    print("RESUMO DA APLICAÇÃO")
    print("="*80)
    
    for arquivo, sucesso in resultados:
        status = "✅ SUCESSO" if sucesso else "❌ FALHOU"
        print(f"{arquivo:.<50} {status}")
    
    total = len(resultados)
    sucessos = sum(1 for _, s in resultados if s)
    
    print("\n" + "="*80)
    print(f"RESULTADO FINAL: {sucessos}/{total} arquivos processados com sucesso")
    print("="*80)
    
    if sucessos == total:
        print("\n✅ TODAS AS OTIMIZAÇÕES APLICADAS COM SUCESSO!")
        print("\nPróximos passos:")
        print("  1. Testar cada fase (GAME.py, GAME2.py, GAME3.py, GAME4.py)")
        print("  2. Verificar FPS e responsividade")
        print("  3. Ajustar balanceamento se necessário")
        print("  4. Backups criados (.backup) caso precise reverter")
        print("\n")
        return 0
    else:
        print("\n⚠️  ALGUMAS OTIMIZAÇÕES FALHARAM")
        print("Verifique os erros acima e aplique manualmente se necessário")
        print("\n")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
