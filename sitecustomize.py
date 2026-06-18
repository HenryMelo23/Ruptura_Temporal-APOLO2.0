"""Project import bootstrap.

Python imports this module automatically when the repository root is on
``sys.path``. Keep the legacy flat imports working after source files were
organized into subfolders.
"""

from __future__ import annotations

import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SUBFOLDERS = (
    "Fases",
    "Manifestacoes",
    "Aureas",
    "Rede",
    "Boss",
    "Menus",
    "Engine",
)

for folder in reversed(SUBFOLDERS):
    path = str(BASE_DIR / folder)
    if path not in sys.path:
        sys.path.insert(0, path)
