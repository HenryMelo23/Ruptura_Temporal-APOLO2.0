import os

files_to_patch = [
    "GAME2.py", "GAME3.py", "GAME4.py", "GAME5.py", 
    "GAME5_PLAYER.py", "GAMERE.py", "_build_player.py"
]

patch_line = "        # Apagar o personagem antes de desenhar o teleporte\n        tela.blit(mapa, (pos_x_personagem, pos_y_personagem), pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem))\n\n"

for filename in files_to_patch:
    if not os.path.exists(filename):
        continue
    
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        if "tela.blit(teleporte_sprites[teleporte_index]" in line:
            # Check if we already patched it
            if i > 0 and "Apagar o personagem antes" in lines[i-1] or "Apagar o personagem antes" in lines[i-2]:
                new_lines.append(line)
            else:
                # Add patch
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(indent + "# Apagar o personagem antes de desenhar o teleporte\n")
                new_lines.append(indent + "tela.blit(mapa, (pos_x_personagem, pos_y_personagem), pygame.Rect(pos_x_personagem, pos_y_personagem, largura_personagem, altura_personagem))\n\n")
                new_lines.append(line)
        else:
            new_lines.append(line)
        i += 1
        
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

print("Patched all files successfully.")
