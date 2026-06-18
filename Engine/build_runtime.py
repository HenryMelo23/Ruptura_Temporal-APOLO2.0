import os


def obter_limite_fases():
    valor = os.environ.get("RUPTURA_MAX_PHASE")
    if not valor:
        return None
    try:
        limite = int(valor)
    except ValueError:
        return None
    return limite if limite > 0 else None


def fase_disponivel(numero_fase):
    limite = obter_limite_fases()
    return limite is None or numero_fase <= limite
