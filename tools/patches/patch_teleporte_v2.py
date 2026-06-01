import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.chdir(PROJECT_ROOT)

files_to_patch = [
    "GAME.py", "GAME2.py", "GAME3.py", "GAME4.py", "GAME5.py", 
    "GAME5_PLAYER.py", "GAMERE.py", "scripts/build_player.py"
]

for filename in files_to_patch:
    if not os.path.exists(filename):
        continue
    
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
        
    old_call = "animar_teleporte_plasma(tela, mapa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, teleporte_duration // 2)"
    new_call = "animar_teleporte_plasma(tela, mapa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, teleporte_duration // 2, ultima_tecla_movimento, distancia_dash, largura_mapa, altura_mapa)"
    
    content = content.replace(old_call, new_call)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

print("Patch V2 applied successfully.")
