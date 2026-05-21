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
        content = f.read()
        
    # We want to remove references to teleporte_timer and teleporte_index from globals
    content = content.replace(", teleporte_timer, teleporte_duration, teleporte_index", ", teleporte_duration")
    
    # And we want to remove the block:
    # teleporte_timer += velocidade_personagem
    # if teleporte_timer >= teleporte_duration:
    #     teleporte_index = (teleporte_index + 1) % len(teleporte_sprites)
    #     teleporte_timer = 0
    
    # We can use regex to remove it
    pattern = r"(\s+teleporte_timer \+= velocidade_personagem\n\s+if teleporte_timer >= teleporte_duration:\n\s+teleporte_index = \(teleporte_index \+ 1\) % len\(teleporte_sprites\)\n\s+teleporte_timer = 0\n)"
    content = re.sub(pattern, "\n", content)
    
    # Some files might have different spacing, let's just do a more flexible regex
    pattern2 = r"\s*teleporte_timer\s*\+=\s*velocidade_personagem\s*\n\s*if\s*teleporte_timer\s*>=\s*teleporte_duration:\s*\n\s*teleporte_index\s*=\s*\(teleporte_index\s*\+\s*1\)\s*%\s*len\(teleporte_sprites\)\s*\n\s*teleporte_timer\s*=\s*0\s*\n"
    content = re.sub(pattern2, "\n", content)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

print("Cleanup successful.")
