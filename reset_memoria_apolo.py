#!/usr/bin/env python3
"""
Script para fazer backup e reset da memória do Apolo após mudança de features.

A remoção da habilidade 'bordas_ativas' reduziu o input_size de 41 para 40 features,
tornando incompatível com a memória antiga.
"""

import os
import shutil
from datetime import datetime

def main():
    arquivo_memoria = "saves/apolo_memoria_dqn.pt"
    
    print("=" * 60)
    print("RESET DE MEMÓRIA DO APOLO")
    print("=" * 60)
    print()
    print("Motivo: Remoção da habilidade 'bordas_ativas'")
    print("Mudança: 41 features → 40 features")
    print()
    
    if not os.path.exists(arquivo_memoria):
        print(f"✓ Arquivo '{arquivo_memoria}' não encontrado.")
        print("  Nenhuma ação necessária. O Apolo iniciará com rede nova.")
        return
    
    # Criar nome do backup com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo_backup = f"saves/apolo_memoria_dqn_backup_{timestamp}.pt"
    
    print(f"Arquivo encontrado: {arquivo_memoria}")
    print()
    print("Opções:")
    print("1. Fazer backup e deletar (recomendado)")
    print("2. Apenas deletar (sem backup)")
    print("3. Cancelar (manter arquivo antigo - pode causar erro)")
    print()
    
    escolha = input("Escolha uma opção (1/2/3): ").strip()
    
    if escolha == "1":
        # Fazer backup
        try:
            shutil.copy2(arquivo_memoria, arquivo_backup)
            print(f"✓ Backup criado: {arquivo_backup}")
            
            # Deletar original
            os.remove(arquivo_memoria)
            print(f"✓ Arquivo original deletado: {arquivo_memoria}")
            print()
            print("✓ Reset concluído com sucesso!")
            print("  O Apolo iniciará com uma rede neural nova.")
            
        except Exception as e:
            print(f"✗ Erro ao fazer backup: {e}")
            return
    
    elif escolha == "2":
        # Apenas deletar
        try:
            os.remove(arquivo_memoria)
            print(f"✓ Arquivo deletado: {arquivo_memoria}")
            print()
            print("✓ Reset concluído!")
            print("  O Apolo iniciará com uma rede neural nova.")
            
        except Exception as e:
            print(f"✗ Erro ao deletar: {e}")
            return
    
    elif escolha == "3":
        print()
        print("⚠ Operação cancelada.")
        print("  ATENÇÃO: Manter o arquivo antigo causará erro de dimensão!")
        print("  Erro esperado: 'size mismatch for fc1.weight: copying a param with shape")
        print("                  torch.Size([128, 41]) from checkpoint, the shape in current")
        print("                  model is torch.Size([128, 40]).'")
        return
    
    else:
        print()
        print("✗ Opção inválida. Operação cancelada.")
        return
    
    print()
    print("=" * 60)
    print("PRÓXIMOS PASSOS:")
    print("=" * 60)
    print("1. Execute o jogo normalmente (GAME5.py)")
    print("2. O Apolo começará a treinar do zero")
    print("3. Monitore o progresso nas primeiras gerações")
    print("4. O comportamento deve melhorar após ~50-100 gerações")
    print()

if __name__ == "__main__":
    main()
