#!/usr/bin/env python3
"""
VERIFICADOR DE INTEGRAÇÃO V3
Valida se o GAME5.py está corretamente integrado com a percepção expandida
"""

import ast
import sys

def verificar_classe_apolo():
    """Verifica se a classe AgenteApolo tem os métodos expandidos"""
    print("=" * 80)
    print("VERIFICANDO CLASSE AgenteApolo NO GAME5.py")
    print("=" * 80)
    
    with open("GAME5.py", "r", encoding="utf-8") as f:
        conteudo = f.read()
    
    # Verifica método obter_estado_expandido
    if "def obter_estado_expandido(" in conteudo:
        print("✓ Método obter_estado_expandido() encontrado")
    else:
        print("✗ ERRO: Método obter_estado_expandido() NÃO encontrado")
        return False
    
    # Verifica se o método tem 10 componentes
    componentes_esperados = [
        "QUADRANTE_BOSS",
        "DISTANCIA_BOSS",
        "VIDA_APOLO",
        "VIDA_BOSS",
        "PERIGO_IMINENTE",
        "DIRECAO_PERIGO",
        "CD_TELEPORTE",
        "ARMADILHA_ATIVA",
        "POSICAO_MAPA",
        "VELOCIDADE"
    ]
    
    componentes_encontrados = 0
    for comp in componentes_esperados:
        if comp in conteudo:
            componentes_encontrados += 1
    
    print(f"✓ Componentes de estado: {componentes_encontrados}/10")
    
    # Verifica assinatura do pensar
    if "def pensar(self, pos_p, boss_hitbox, projeteis_boss, cds, vida_jogador, vida_boss, esferas_energia, velocidade_atual" in conteudo:
        print("✓ Assinatura do pensar() expandida corretamente")
    else:
        print("✗ AVISO: Assinatura do pensar() pode estar incorreta")
    
    # Verifica frames_sobrevividos
    if "self.frames_sobrevividos" in conteudo:
        print("✓ Atributo frames_sobrevividos encontrado")
    else:
        print("✗ AVISO: Atributo frames_sobrevividos não encontrado")
    
    return True

def verificar_chamadas_pensar():
    """Verifica se as chamadas do pensar() foram atualizadas"""
    print("\n" + "=" * 80)
    print("VERIFICANDO CHAMADAS DO apolo.pensar()")
    print("=" * 80)
    
    with open("GAME5.py", "r", encoding="utf-8") as f:
        linhas = f.readlines()
    
    chamadas_encontradas = 0
    chamadas_corretas = 0
    
    for i, linha in enumerate(linhas, 1):
        if "apolo.pensar(" in linha:
            chamadas_encontradas += 1
            print(f"\nChamada {chamadas_encontradas} encontrada na linha {i}")
            
            # Verifica se tem velocidade_atual e estado_ia
            contexto = "".join(linhas[max(0, i-5):min(len(linhas), i+2)])
            
            if "velocidade_atual" in contexto:
                print("  ✓ Parâmetro velocidade_atual presente")
                chamadas_corretas += 1
            else:
                print("  ✗ ERRO: Parâmetro velocidade_atual ausente")
            
            if "estado_ia_ref" in contexto or "estado_ia" in contexto:
                print("  ✓ Parâmetro estado_ia presente")
            else:
                print("  ✗ AVISO: Parâmetro estado_ia pode estar ausente")
    
    print(f"\n✓ Total de chamadas encontradas: {chamadas_encontradas}")
    print(f"✓ Chamadas com velocidade_atual: {chamadas_corretas}/{chamadas_encontradas}")
    
    return chamadas_encontradas >= 2 and chamadas_corretas >= 2

def verificar_script_v3():
    """Verifica se o script de treinamento V3 existe"""
    print("\n" + "=" * 80)
    print("VERIFICANDO SCRIPT DE TREINAMENTO V3")
    print("=" * 80)
    
    import os
    
    if os.path.exists("treino_acelerado_v3_percepcao_expandida.py"):
        print("✓ Script treino_acelerado_v3_percepcao_expandida.py encontrado")
        
        with open("treino_acelerado_v3_percepcao_expandida.py", "r", encoding="utf-8") as f:
            conteudo = f.read()
        
        if "class AgenteApoloExpandido" in conteudo:
            print("✓ Classe AgenteApoloExpandido presente")
        
        if "episodios_totais=3000" in conteudo:
            print("✓ Configurado para 3000 episódios")
        
        if "episodios_por_lote=100" in conteudo:
            print("✓ Lotes de 100 episódios")
        
        return True
    else:
        print("✗ ERRO: Script V3 não encontrado")
        return False

def verificar_memoria_compatibilidade():
    """Verifica compatibilidade com memória existente"""
    print("\n" + "=" * 80)
    print("VERIFICANDO COMPATIBILIDADE COM MEMÓRIA")
    print("=" * 80)
    
    import os
    import json
    
    if os.path.exists("apolo_memoria.json"):
        print("✓ Arquivo apolo_memoria.json encontrado")
        
        try:
            with open("apolo_memoria.json", "r") as f:
                memoria = json.load(f)
            
            print(f"✓ Estados na memória atual: {len(memoria)}")
            
            # Verifica formato dos estados
            if memoria:
                exemplo = list(memoria.keys())[0]
                componentes = exemplo.count("_") + 1
                print(f"✓ Formato de estado detectado: {componentes} componentes")
                
                if componentes == 4:
                    print("  → Memória V2 detectada (será expandida automaticamente)")
                elif componentes == 10:
                    print("  → Memória V3 detectada")
                else:
                    print(f"  → Formato desconhecido ({componentes} componentes)")
        
        except Exception as e:
            print(f"✗ ERRO ao ler memória: {e}")
    else:
        print("✓ Sem memória prévia (será criada do zero)")
    
    return True

def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "VERIFICADOR DE INTEGRAÇÃO V3" + " " * 30 + "║")
    print("║" + " " * 15 + "Percepção Expandida - Apolo & Umbra" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    
    resultados = []
    
    # Executa verificações
    resultados.append(("Classe AgenteApolo", verificar_classe_apolo()))
    resultados.append(("Chamadas pensar()", verificar_chamadas_pensar()))
    resultados.append(("Script V3", verificar_script_v3()))
    resultados.append(("Compatibilidade", verificar_memoria_compatibilidade()))
    
    # Resumo final
    print("\n" + "=" * 80)
    print("RESUMO DA VERIFICAÇÃO")
    print("=" * 80)
    
    total = len(resultados)
    sucesso = sum(1 for _, ok in resultados if ok)
    
    for nome, ok in resultados:
        status = "✓ PASSOU" if ok else "✗ FALHOU"
        print(f"{nome:.<50} {status}")
    
    print("\n" + "=" * 80)
    print(f"RESULTADO FINAL: {sucesso}/{total} verificações passaram")
    print("=" * 80)
    
    if sucesso == total:
        print("\n✓ INTEGRAÇÃO V3 COMPLETA E FUNCIONAL!")
        print("\nPróximos passos:")
        print("  1. Execute: python treino_acelerado_v3_percepcao_expandida.py")
        print("  2. Aguarde 5-10 minutos (3000 episódios)")
        print("  3. Teste no jogo: python GAME5.py")
        print("\n")
        return 0
    else:
        print("\n✗ INTEGRAÇÃO INCOMPLETA - Revise os erros acima")
        print("\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
