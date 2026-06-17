with open("GAME6.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "projetil_lista" in line:
        print(f"Line {i+1}: {line.strip()}")
