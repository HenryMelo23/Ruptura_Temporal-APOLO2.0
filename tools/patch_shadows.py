import glob
import os

pattern1 = """def desenhar_sombra(tela, x, y, largura, altura, offset_y=5):
    \"\"\"Desenha uma sombra elíptica embaixo de um ser com três níveis de qualidade\"\"\"
    modo_sombra = config_graficos.get("sombras_ativas", "dinamicas")
    Variaveis.desenhar_sombra_cacheada(tela, x, y, largura, altura, modo_sombra, offset_y)
    return"""

replace1 = """def desenhar_sombra(tela, x, y, largura, altura, offset_y=5, imagem=None):
    \"\"\"Desenha uma sombra elíptica ou com base no sprite\"\"\"
    modo_sombra = config_graficos.get("sombras_ativas", "dinamicas")
    if imagem is not None and modo_sombra == "dinamicas":
        try:
            from Engine.render_engine import MotorRenderizacao
            if MotorRenderizacao.desenhar_sombra_dinamica_sprite(tela, imagem, x, y, largura, altura, modo_sombra, offset_y):
                return
        except Exception:
            pass
    Variaveis.desenhar_sombra_cacheada(tela, x, y, largura, altura, modo_sombra, offset_y)
    return"""

count = 0
for f in glob.glob('Fases/GAME*.py'):
    if f == 'Fases\\GAME.py' or f == 'Fases/GAME.py':
        continue # Already did GAME.py

    try:
        with open(f, 'r', encoding='utf-8') as file:
            c = file.read()
    except UnicodeDecodeError:
        try:
            with open(f, 'r', encoding='mbcs') as file:
                c = file.read()
        except:
            continue
            
    if pattern1 in c:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(c.replace(pattern1, replace1))
        count += 1
        print(f"Patched {f}")
print(f"Total patched: {count}")
