import os
import re

files_to_patch = [
    "GAME.py", "GAME2.py", "GAME3.py", "GAME4.py", "GAME5.py", 
    "GAME5_PLAYER.py", "GAMERE.py", "_build_player.py"
]

for filename in files_to_patch:
    if not os.path.exists(filename):
        continue
    
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    new_lines = []
    modified = False
    
    for line in lines:
        if "tela.blit(teleporte_sprites" in line:
            modified = True
            continue # Wipe it out
        if "teleporte_index = (teleporte_index" in line:
            modified = True
            continue # Wipe it out
        new_lines.append(line)
        
    if modified:
        with open(filename, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"Patched {filename}")

print("Wipe complete.")
