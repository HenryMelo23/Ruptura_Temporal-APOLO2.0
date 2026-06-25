"""Compatibilidade para o fluxo antigo de Game Over.

As fases ainda chamam ``python Game_Over.py`` em alguns caminhos sem
``game_manager``. O arquivo real fica em ``Menus/Game_Over.py``; este wrapper
mantem esses caminhos funcionando sem duplicar a tela.
"""

from __future__ import annotations

import sitecustomize  # noqa: F401 - garante imports legados das subpastas

from Menus.Game_Over import (  # noqa: F401
    executar_game_over,
    tentar_novamente_com_refragmentacao,
    tratar_tentar_novamente,
)


if __name__ == "__main__":
    executar_game_over()
