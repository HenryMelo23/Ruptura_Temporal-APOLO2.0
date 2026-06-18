"""Compatibility launcher for running phase 5 from the project root.

The actual implementation lives in Fases/GAME5.py after the project
reorganization.
"""

from Fases.GAME5 import _StandaloneGame5Manager, executar_jogo


if __name__ == "__main__":
    executar_jogo(_StandaloneGame5Manager())
