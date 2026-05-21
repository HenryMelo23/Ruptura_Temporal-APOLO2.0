import os

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
    for line in lines:
        if "global em_teleporte" in line and "tempo_inicio_teleporte" not in line:
            new_lines.append(line.replace("global em_teleporte", "global em_teleporte, tempo_inicio_teleporte"))
        else:
            new_lines.append(line)
            
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

print("Patched global declarations successfully.")
