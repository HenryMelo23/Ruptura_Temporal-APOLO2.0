import math


_ESTADO_BOSS_MANIFESTACOES = {}


def _normalizar_tipo(disparo):
    if not isinstance(disparo, dict):
        return ""
    return str(disparo.get("tipo_manifestacao") or "")


def _efeito_texto(efeitos_texto, texto, rect, tempo_atual, cor):
    if efeitos_texto is None or rect is None:
        return
    efeitos_texto.append({
        "texto": texto,
        "x": rect.centerx,
        "y": rect.top - 46,
        "tempo_inicio": int(tempo_atual),
        "cor": cor,
    })


def aplicar_efeito_boss(disparo, dano, tempo_atual, efeitos_texto=None, boss_rect=None, boss_chave="boss"):
    """Aplica efeitos reduzidos de manifestacoes em bosses sem exigir um dict de inimigo comum."""
    tipo = _normalizar_tipo(disparo)
    if not tipo:
        return dano

    estado = _ESTADO_BOSS_MANIFESTACOES.setdefault(str(boss_chave), {})
    agora = int(tempo_atual)
    dano_final = float(dano)

    if tipo == "lacerante_corte":
        lac = estado.setdefault("lacerante", {"stacks": 0, "expira_ms": 0})
        if agora > int(lac.get("expira_ms", 0)):
            lac["stacks"] = 0
        lac["stacks"] = min(4, int(lac.get("stacks", 0)) + 1)
        lac["expira_ms"] = agora + 5200
        estagio = int(disparo.get("estagio_corte", 0) or 0)
        dano_final *= 1.10 + lac["stacks"] * 0.06 + (0.18 if estagio == 2 else 0.0)
        _efeito_texto(efeitos_texto, f"RASGO x{lac['stacks']}", boss_rect, agora, (255, 64, 116))

    elif tipo == "parasitica_semente":
        par = estado.setdefault("parasitica", {"stacks": 0, "expira_ms": 0})
        if agora > int(par.get("expira_ms", 0)):
            par["stacks"] = 0
        par["stacks"] = min(3, int(par.get("stacks", 0)) + 1)
        par["expira_ms"] = agora + 6400
        dano_final *= 1.07 + par["stacks"] * 0.035
        _efeito_texto(efeitos_texto, f"PARASITA x{par['stacks']}", boss_rect, agora, (128, 255, 112))

    elif tipo == "condutora_fio":
        ultimo = int(estado.get("condutora_ultimo_ms", 0))
        estado["condutora_ultimo_ms"] = agora
        dano_final *= 1.12 if agora - ultimo > 650 else 1.06
        _efeito_texto(efeitos_texto, "CURTO", boss_rect, agora, (80, 230, 255))

    elif tipo == "gravitante_orbe":
        fase = math.sin(agora * 0.006)
        dano_final *= 1.10 + max(0.0, fase) * 0.04
        _efeito_texto(efeitos_texto, "COLAPSO", boss_rect, agora, (180, 120, 255))

    elif tipo == "ancorada_disparo":
        anc = estado.setdefault("ancorada", {"stacks": 0, "expira_ms": 0})
        if agora > int(anc.get("expira_ms", 0)):
            anc["stacks"] = 0
        anc["stacks"] = min(3, int(anc.get("stacks", 0)) + 1)
        anc["expira_ms"] = agora + 7000
        dano_final *= 1.08 + anc["stacks"] * 0.04
        _efeito_texto(efeitos_texto, f"ANCORA x{anc['stacks']}", boss_rect, agora, (255, 210, 90))

    return max(1.0, dano_final)
