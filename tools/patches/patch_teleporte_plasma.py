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
        lines = f.readlines()
        
    new_lines = []
    skip = 0
    for i, line in enumerate(lines):
        if skip > 0:
            skip -= 1
            continue
            
        if "Apagar o personagem antes de desenhar o teleporte" in line:
            # We found the block to replace. It spans around 8-10 lines depending on spacing.
            # Look ahead to verify it's the teleport block
            found_teleport = False
            for j in range(1, 8):
                if i + j < len(lines) and "tela.blit(teleporte_sprites" in lines[i+j]:
                    found_teleport = True
                    break
                    
            if found_teleport:
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(indent + "# Animação de teletransporte (plasma procedural)\n")
                new_lines.append(indent + "animar_teleporte_plasma(tela, mapa, pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem, teleporte_duration // 2)\n")
                
                # We need to skip the next lines until we pass the delay
                for j in range(1, 15):
                    if i + j < len(lines):
                        if "pygame.time.delay(" in lines[i+j]:
                            skip = j
                            break
                continue
                
        new_lines.append(line)
        
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

print("Patched teleport sprites to procedural plasma successfully.")
