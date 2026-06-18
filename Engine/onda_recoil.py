import math


COICE_ONDA_DESLOCAMENTO_PX = 15.0
COICE_ONDA_ATRITO = 0.68
COICE_ONDA_VELOCIDADE_MIN = 0.08
COICE_ONDA_VELOCIDADE_MAX = 8.0


def criar_estado_coice_onda():
    return {"vx": 0.0, "vy": 0.0}


def aplicar_coice_onda(estado, angulo, deslocamento_px=COICE_ONDA_DESLOCAMENTO_PX):
    impulso = deslocamento_px * (1.0 - COICE_ONDA_ATRITO)
    estado["vx"] -= math.cos(angulo) * impulso
    estado["vy"] -= math.sin(angulo) * impulso

    velocidade = math.hypot(estado["vx"], estado["vy"])
    if velocidade > COICE_ONDA_VELOCIDADE_MAX:
        escala = COICE_ONDA_VELOCIDADE_MAX / velocidade
        estado["vx"] *= escala
        estado["vy"] *= escala


def atualizar_coice_onda(pos_x, pos_y, largura, altura, largura_mapa, altura_mapa, estado, dt=1.0):
    vx = estado.get("vx", 0.0)
    vy = estado.get("vy", 0.0)
    if math.hypot(vx, vy) < COICE_ONDA_VELOCIDADE_MIN:
        estado["vx"] = 0.0
        estado["vy"] = 0.0
        return pos_x, pos_y

    dt = max(0.05, min(3.0, float(dt or 1.0)))
    novo_x = max(0, min(largura_mapa - largura, pos_x + vx * dt))
    novo_y = max(0, min(altura_mapa - altura, pos_y + vy * dt))

    if novo_x in (0, largura_mapa - largura):
        estado["vx"] = 0.0
    else:
        estado["vx"] = vx * (COICE_ONDA_ATRITO ** dt)

    if novo_y in (0, altura_mapa - altura):
        estado["vy"] = 0.0
    else:
        estado["vy"] = vy * (COICE_ONDA_ATRITO ** dt)

    return novo_x, novo_y
