from habilidade_boss import MemoriaEvolutivaUmbra
import random

def treinar_autonomo():
    # Inicializa a memória
    umbra = MemoriaEvolutivaUmbra()
    
    # Lista de ações que a Umbra pode tomar no jogo
    acoes_possiveis = ["INVESTIDA", "DISPARO", "RECUAR", "ESQUIVA"]
    
  

    for ciclo in range(10000):
        # 1. Simular variáveis de estado
        vida_perc = random.uniform(0.1, 1.0)
        dist_player = random.randint(50, 1000)
        sob_fogo = random.choice([True, False])
        historico_player = [] # Simulando histórico vazio para o treino base
        
        # 2. Obter o estado discretizado
        estado = umbra.discretizar_estado(vida_perc, dist_player, sob_fogo, historico_player)
        
        # 3. Decidir a ação usando o nome correto do método
        acao = umbra.decidir(estado, acoes_possiveis)
        
        # 4. Lógica de Recompensa (O "professor" da IA)
        recompensa = 0
        
        # Premiar recuo/esquiva quando sob fogo ou vida baixa
        if sob_fogo and acao in ["ESQUIVA", "RECUAR"]:
            recompensa += 20
        # Punir investida descuidada com vida baixa
        elif vida_perc < 0.3 and acao == "INVESTIDA":
            recompensa -= 30
        # Premiar ataque quando o player está longe ou em estado calmo
        elif not sob_fogo and acao in ["INVESTIDA", "DISPARO"]:
            recompensa += 10
        else:
            recompensa -= 1 # Pequena punição por indecisão
            
        # 5. Aplicar o aprendizado
        umbra.treinar(recompensa)
        
        if ciclo % 1000 == 0:
            umbra.salvar() # Salva o progresso no JSON




if __name__ == "__main__":
    treinar_autonomo()