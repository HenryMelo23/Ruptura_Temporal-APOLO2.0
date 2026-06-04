"""
GAME MANAGER - Sistema de Gerenciamento de Estados
Substitui subprocess por transições fluidas entre telas
"""

import Caminhos
import pygame
import sys
import importlib
from enum import Enum
from qa_logger import instalar_captura_global, instalar_filtro_prints

instalar_captura_global()
instalar_filtro_prints()

class EstadoJogo(Enum):
    """Estados possíveis do jogo"""
    MENU_PRINCIPAL = "menu_principal"
    TUTORIAL = "tutorial"
    JOGO_FASE_1 = "jogo_fase_1"
    JOGO_FASE_2 = "jogo_fase_2"
    JOGO_FASE_3 = "jogo_fase_3"
    JOGO_FASE_4 = "jogo_fase_4"
    JOGO_FASE_5 = "jogo_fase_5"
    JOGO_PRINCIPAL = "jogo_principal"  # Alias para compatibilidade
    GAME_OVER = "game_over"
    CONFIGURACOES = "configuracoes"
    SAIR = "sair"

class GameManager:
    """
    Gerenciador central do jogo que controla transições entre estados
    sem usar subprocess
    """
    
    def __init__(self):
        pygame.init()
        self.estado_atual = EstadoJogo.MENU_PRINCIPAL
        self.proximo_estado = None
        self.rodando = True
        self.dados_compartilhados = {}  # Dados que persistem entre estados
        
    def mudar_estado(self, novo_estado: EstadoJogo, dados=None):
        """
        Solicita mudança de estado
        
        Args:
            novo_estado: Próximo estado do jogo
            dados: Dados opcionais para passar ao próximo estado
        """
        self.proximo_estado = novo_estado
        if novo_estado == EstadoJogo.SAIR:
            self.rodando = False
        if dados:
            self.dados_compartilhados.update(dados)
    
    def executar_estado(self):
        """Executa o estado atual e retorna se deve continuar"""
        
        if self.estado_atual == EstadoJogo.MENU_PRINCIPAL:
            from Ruptura_Temporal import executar_menu_principal
            resultado = executar_menu_principal(self)
            
        elif self.estado_atual == EstadoJogo.TUTORIAL:
            from Tutorial import executar_tutorial
            resultado = executar_tutorial(self)
            
        elif self.estado_atual in [EstadoJogo.JOGO_PRINCIPAL, EstadoJogo.JOGO_FASE_1]:
            # Fase 1 ou modo offline
            import Variaveis
            Variaveis.reset_game_session()
            modo = self.dados_compartilhados.get('modo_jogo', 'offline')
            
            if modo == 'offline':
                if 'GAME' in sys.modules:
                    importlib.reload(sys.modules['GAME'])
                import GAME
                resultado = GAME.executar_jogo(self)
            else:
                if 'GAMERE' in sys.modules:
                    importlib.reload(sys.modules['GAMERE'])
                import GAMERE
                resultado = GAMERE.executar_jogo(self)
                
        elif self.estado_atual == EstadoJogo.JOGO_FASE_2:
            import Variaveis
            Variaveis.reset_phase_state()
            if 'GAME2' in sys.modules:
                importlib.reload(sys.modules['GAME2'])
            import GAME2
            resultado = GAME2.executar_jogo(self)
            
        elif self.estado_atual == EstadoJogo.JOGO_FASE_3:
            import Variaveis
            Variaveis.reset_phase_state()
            if 'GAME3' in sys.modules:
                importlib.reload(sys.modules['GAME3'])
            import GAME3
            resultado = GAME3.executar_jogo(self)
            
        elif self.estado_atual == EstadoJogo.JOGO_FASE_4:
            import Variaveis
            Variaveis.reset_phase_state()
            if 'GAME4' in sys.modules:
                importlib.reload(sys.modules['GAME4'])
            import GAME4
            resultado = GAME4.executar_jogo(self)
            
        elif self.estado_atual == EstadoJogo.JOGO_FASE_5:
            import Variaveis
            Variaveis.reset_phase_state()
            if 'GAME5' in sys.modules:
                importlib.reload(sys.modules['GAME5'])
            import GAME5
            resultado = GAME5.executar_jogo(self)
                
        elif self.estado_atual == EstadoJogo.GAME_OVER:
            from Game_Over import executar_game_over
            resultado = executar_game_over(self)
            
        elif self.estado_atual == EstadoJogo.SAIR:
            self.rodando = False
            return False
            
        # Aplica transição de estado se houver
        estados_jogaveis = {
            EstadoJogo.JOGO_PRINCIPAL,
            EstadoJogo.JOGO_FASE_1,
            EstadoJogo.JOGO_FASE_2,
            EstadoJogo.JOGO_FASE_3,
            EstadoJogo.JOGO_FASE_4,
            EstadoJogo.JOGO_FASE_5,
        }

        # Se uma fase terminou sem escolher outra tela, nao reabre a mesma fase.
        # Isso cobre pygame.QUIT/sys.exit interceptados como CleanExit nos GAME*.py.
        if self.estado_atual in estados_jogaveis and self.proximo_estado is None:
            self.rodando = False
            return False

        if self.proximo_estado:
            if self.proximo_estado == EstadoJogo.GAME_OVER:
                if self.estado_atual not in [EstadoJogo.GAME_OVER, EstadoJogo.MENU_PRINCIPAL, EstadoJogo.SAIR, EstadoJogo.CONFIGURACOES]:
                    self.dados_compartilhados['fase_antes_do_game_over'] = self.estado_atual
            else:
                import Variaveis
                if not (self.estado_atual == EstadoJogo.GAME_OVER and Variaveis.snapshot_para_carregar is not None):
                    Variaveis.limpar_historico_rewind()
            self.estado_atual = self.proximo_estado
            self.proximo_estado = None
            
        return self.rodando
    
    def executar(self):
        """Loop principal do gerenciador"""
        while self.rodando:
            continuar = self.executar_estado()
            if not continuar:
                break
        
        pygame.quit()
        sys.exit()

# Instância global do gerenciador
_game_manager = None

def obter_game_manager():
    """Retorna a instância global do GameManager"""
    global _game_manager
    if _game_manager is None:
        _game_manager = GameManager()
    return _game_manager

if __name__ == "__main__":
    manager = obter_game_manager()
    manager.executar()
