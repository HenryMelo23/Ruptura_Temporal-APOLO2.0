import sys

with open('GAME5.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out = lines[:23]
out.append('if __name__ == "__main__":\n')
out.append('    import multiprocessing as mp\n')
out.append('    mp.freeze_support()\n')

for line in lines[23:]:
    if line.strip() == '':
        out.append(line)
    else:
        out.append('    ' + line)

with open('GAME5.py', 'w', encoding='utf-8') as f:
    f.writelines(out)
print("GAME5.py refatorado com sucesso!")
