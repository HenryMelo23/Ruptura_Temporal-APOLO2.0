"""
================================================================================
DIAGNÓSTICO DE Q-TABLES
================================================================================

Script para analisar o estado das Q-Tables após o treinamento.
Identifica problemas de balanceamento e convergência.

================================================================================
"""

import json
import os
from collections import Counter

def analisar_qtable_umbra():
    """Analisa a Q-Table da Umbra."""
    print("="*80)
    print("ANÁLISE DA Q-TABLE DA UMBRA")
    print("="*80)
    
    if not os.path.exists("memoria_umbra.json"):
        print("❌ Arquivo memoria_umbra.json não encontrado!")
        return
    
    with open("memoria_umbra.json", "r") as f:
        memoria = json.load(f)
    
    # 1. Tamanho total
    total_estados = len(memoria)
    print(f"\n📊 Total de estados: {total_estados}")
    
    if total_estados > 1000:
        print(f"   ⚠️  ALERTA: Q-Table muito grande! (esperado: 300-800)")
    elif total_estados < 100:
        print(f"   ⚠️  ALERTA: Q-Table muito pequena! (esperado: 300-800)")
    else:
        print(f"   ✅ Tamanho adequado")
    
    # 2. Memória Bayesiana
    if "tendencias" in memoria:
        tendencias = memoria["tendencias"]
        print(f"\n🧠 Memória Bayesiana:")
        print(f"   ESQUERDA: {tendencias.get('ESQUERDA', 0):,}")
        print(f"   DIREITA:  {tendencias.get('DIREITA', 0):,}")
        print(f"   CIMA:     {tendencias.get('CIMA', 0):,}")
        print(f"   BAIXO:    {tendencias.get('BAIXO', 0):,}")
        print(f"   TOTAL:    {tendencias.get('TOTAL', 0):,}")
        
        # Verificar se foi corrompida
        total = tendencias.get('TOTAL', 0)
        if total > 10000000:  # Mais de 10 milhões
            print(f"   ⚠️  ALERTA: Memória Bayesiana pode ter sido corrompida!")
            print(f"   (Valores muito altos indicam registro durante treino acelerado)")
    
    # 3. Análise de ações
    acoes_counter = Counter()
    valores_q = []
    
    for estado, acoes in memoria.items():
        if estado in ["tendencias", "neurogenese"]:
            continue
        
        if isinstance(acoes, dict):
            for acao, valor in acoes.items():
                acoes_counter[acao] += 1
                valores_q.append(valor)
    
    print(f"\n🎯 Ações aprendidas:")
    for acao, count in acoes_counter.most_common(10):
        print(f"   {acao}: {count} estados")
    
    # 4. Estatísticas de valores Q
    if valores_q:
        print(f"\n📈 Estatísticas de valores Q:")
        print(f"   Mínimo:  {min(valores_q):.2f}")
        print(f"   Máximo:  {max(valores_q):.2f}")
        print(f"   Média:   {sum(valores_q)/len(valores_q):.2f}")
        
        positivos = sum(1 for v in valores_q if v > 0)
        negativos = sum(1 for v in valores_q if v < 0)
        print(f"   Positivos: {positivos} ({positivos/len(valores_q)*100:.1f}%)")
        print(f"   Negativos: {negativos} ({negativos/len(valores_q)*100:.1f}%)")
    
    # 5. Análise de estados
    print(f"\n🔍 Amostra de estados (primeiros 5):")
    count = 0
    for estado, acoes in memoria.items():
        if estado in ["tendencias", "neurogenese"]:
            continue
        if count >= 5:
            break
        print(f"   {estado}")
        if isinstance(acoes, dict):
            for acao, valor in list(acoes.items())[:3]:
                print(f"      {acao}: {valor:.3f}")
        count += 1


def analisar_qtable_apolo():
    """Analisa a Q-Table do Apolo."""
    print("\n" + "="*80)
    print("ANÁLISE DA Q-TABLE DO APOLO")
    print("="*80)
    
    if not os.path.exists("apolo_memoria.json"):
        print("❌ Arquivo apolo_memoria.json não encontrado!")
        return
    
    with open("apolo_memoria.json", "r") as f:
        memoria = json.load(f)
    
    # 1. Tamanho total
    total_estados = len(memoria)
    print(f"\n📊 Total de estados: {total_estados}")
    
    if total_estados > 1000:
        print(f"   ⚠️  ALERTA: Q-Table muito grande! (esperado: 300-800)")
    elif total_estados < 100:
        print(f"   ⚠️  ALERTA: Q-Table muito pequena! (esperado: 300-800)")
    else:
        print(f"   ✅ Tamanho adequado")
    
    # 2. Análise de valores Q
    todos_valores = []
    for estado, valores in memoria.items():
        if isinstance(valores, list):
            todos_valores.extend(valores)
    
    if todos_valores:
        print(f"\n📈 Estatísticas de valores Q:")
        print(f"   Mínimo:  {min(todos_valores):.2f}")
        print(f"   Máximo:  {max(todos_valores):.2f}")
        print(f"   Média:   {sum(todos_valores)/len(todos_valores):.2f}")
        
        positivos = sum(1 for v in todos_valores if v > 0)
        negativos = sum(1 for v in todos_valores if v < 0)
        zeros = sum(1 for v in todos_valores if v == 0)
        
        print(f"   Positivos: {positivos} ({positivos/len(todos_valores)*100:.1f}%)")
        print(f"   Negativos: {negativos} ({negativos/len(todos_valores)*100:.1f}%)")
        print(f"   Zeros:     {zeros} ({zeros/len(todos_valores)*100:.1f}%)")
        
        if zeros / len(todos_valores) > 0.8:
            print(f"   ⚠️  ALERTA: Muitos valores zero! Apolo pode não ter aprendido.")
    
    # 3. Análise de ações preferidas
    print(f"\n🎯 Ações preferidas por estado:")
    acoes_nomes = ["CIMA", "BAIXO", "ESQUERDA", "DIREITA", "DASH"]
    acoes_counter = Counter()
    
    for estado, valores in memoria.items():
        if isinstance(valores, list) and len(valores) == 5:
            acao_preferida = valores.index(max(valores))
            acoes_counter[acoes_nomes[acao_preferida]] += 1
    
    for acao, count in acoes_counter.most_common():
        print(f"   {acao}: {count} estados ({count/total_estados*100:.1f}%)")
    
    # 4. Amostra de estados
    print(f"\n🔍 Amostra de estados (primeiros 5):")
    count = 0
    for estado, valores in memoria.items():
        if count >= 5:
            break
        print(f"   {estado}")
        if isinstance(valores, list):
            for i, v in enumerate(valores):
                print(f"      {acoes_nomes[i]}: {v:.3f}")
        count += 1


def comparar_versoes():
    """Compara versões de backup se existirem."""
    print("\n" + "="*80)
    print("COMPARAÇÃO COM BACKUPS")
    print("="*80)
    
    arquivos = [
        ("memoria_umbra.json", "memoria_umbra_v1.json", "Umbra"),
        ("apolo_memoria.json", "apolo_memoria_v1.json", "Apolo")
    ]
    
    for atual, backup, nome in arquivos:
        if os.path.exists(atual) and os.path.exists(backup):
            with open(atual, "r") as f:
                atual_data = json.load(f)
            with open(backup, "r") as f:
                backup_data = json.load(f)
            
            print(f"\n{nome}:")
            print(f"   Backup:  {len(backup_data)} estados")
            print(f"   Atual:   {len(atual_data)} estados")
            
            diff = len(atual_data) - len(backup_data)
            if diff > 0:
                print(f"   Crescimento: +{diff} estados ({diff/len(backup_data)*100:.1f}%)")
            elif diff < 0:
                print(f"   Redução: {diff} estados ({abs(diff)/len(backup_data)*100:.1f}%)")
            else:
                print(f"   ⚠️  Sem mudanças!")


def diagnostico_completo():
    """Executa diagnóstico completo."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*25 + "DIAGNÓSTICO DE Q-TABLES" + " "*30 + "║")
    print("╚" + "="*78 + "╝")
    print()
    
    analisar_qtable_umbra()
    analisar_qtable_apolo()
    comparar_versoes()
    
    print("\n" + "="*80)
    print("RECOMENDAÇÕES")
    print("="*80)
    
    # Carregar dados para recomendações
    umbra_size = 0
    apolo_size = 0
    
    if os.path.exists("memoria_umbra.json"):
        with open("memoria_umbra.json", "r") as f:
            umbra_size = len(json.load(f))
    
    if os.path.exists("apolo_memoria.json"):
        with open("apolo_memoria.json", "r") as f:
            apolo_size = len(json.load(f))
    
    print()
    
    # Recomendações baseadas em tamanho
    if umbra_size > 1500:
        print("⚠️  Q-Table Umbra muito grande!")
        print("   → Execute treino_acelerado_v2_balanceado.py")
        print("   → Simplifica a discretização de estados")
    
    if apolo_size < 200:
        print("⚠️  Q-Table Apolo muito pequena!")
        print("   → Apolo não está aprendendo")
        print("   → Execute treino_acelerado_v2_balanceado.py")
        print("   → Adiciona recompensas por sobrevivência")
    
    if 300 <= umbra_size <= 800 and 300 <= apolo_size <= 800:
        print("✅ Q-Tables em tamanho ideal!")
        print("   → Treinamento bem-sucedido")
        print("   → Pronto para combate contra humanos")
    
    print()


if __name__ == "__main__":
    diagnostico_completo()
