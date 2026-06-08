# -*- coding: utf-8 -*-
import math
import random

import pygame

import condutora_manifestacao
import lacerante_manifestacao
import parasitica_manifestacao
import prismatica_manifestacao


RETORNANTE_JANELA_MS = 4000
RETORNANTE_COOLDOWN_EXTRA_MS = 500
PRISMATICA_COOLDOWN_EXTRA_MS = 3800
GRAVITANTE_COOLDOWN_EXTRA_MS = 450

_EFEITOS = []
_PARTICULAS = []
_LINHAS_CONDUTORAS = []
_PARASITAS = []
_IMPULSOS_GRAVITANTES = []
_RETORNO = None
_RETORNO_EXPIRADO_PENDENTE = False
_MORTOS_PENDENTES = []


CORES = {
    "eletrica": ((40, 230, 255), (235, 255, 255), (35, 105, 255)),
    "lacerante": ((255, 35, 80), (255, 210, 225), (145, 0, 55)),
    "prismatica": ((88, 235, 255), (255, 245, 190), (185, 90, 255)),
    "retornante": ((80, 170, 255), (255, 225, 120), (55, 65, 180)),
    "condutora": ((255, 210, 70), (255, 250, 180), (70, 235, 255)),
    "gravitante": ((135, 95, 255), (90, 235, 255), (30, 20, 85)),
    "parasitica": ((80, 235, 105), (210, 80, 235), (45, 95, 40)),
    "padrao": ((85, 220, 255), (235, 255, 255), (80, 120, 255)),
}


def _manifestacao(chave):
    return str(chave or "eletrica").strip().lower()


def _perfil_efeito(config_graficos=None):
    cfg = config_graficos or {}
    if cfg and not cfg.get("efeitos_visuais", True):
        return "desativado"
    perfil = str(cfg.get("efeitos_manifestacoes", "")).lower()
    if perfil in ("alto", "medio", "baixo", "desativado"):
        return perfil
    if cfg and not cfg.get("particulas_ativas", True):
        return "baixo"
    nivel = str(cfg.get("nivel_detalhes", cfg.get("qualidade_grafica", "alto"))).lower()
    if nivel in ("baixo", "baixa"):
        return "baixo"
    if nivel in ("medio", "media"):
        return "medio"
    return "alto"


def _densidade(perfil, alto=1.0):
    if perfil == "desativado":
        return 0.0
    if perfil == "baixo":
        return 0.34 * alto
    if perfil == "medio":
        return 0.62 * alto
    return alto


def _cor(manifestacao):
    return CORES.get(_manifestacao(manifestacao), CORES["padrao"])


def _dist(ax, ay, bx, by):
    return math.hypot(float(ax) - float(bx), float(ay) - float(by))


def _normalizar(vx, vy):
    comp = math.hypot(vx, vy)
    if comp <= 0.001:
        return 1.0, 0.0
    return vx / comp, vy / comp


def _distancia_segmento(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab2 = abx * abx + aby * aby
    if ab2 <= 0.001:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab2))
    cx = ax + abx * t
    cy = ay + aby * t
    return math.hypot(px - cx, py - cy)


def _texto(efeitos_texto, texto, rect, tempo_atual, cor):
    if efeitos_texto is None or rect is None:
        return
    efeitos_texto.append({
        "texto": texto,
        "x": rect.centerx,
        "y": rect.top - 22,
        "tempo_inicio": int(tempo_atual),
        "cor": cor,
    })


def _registrar_morto(inimigo):
    if inimigo not in _MORTOS_PENDENTES:
        _MORTOS_PENDENTES.append(inimigo)


def _aplicar_dano(inimigo, dano, tempo_atual, efeitos_texto, cor, texto=None):
    if not isinstance(inimigo, dict) or inimigo.get("vida", 1) <= 0:
        return False
    rect = inimigo.get("rect")
    inimigo["vida"] = float(inimigo.get("vida", 0)) - max(0.0, float(dano))
    _texto(efeitos_texto, texto or f"-{int(max(1, dano))}", rect, tempo_atual, cor)
    if inimigo.get("vida", 1) <= 0:
        _registrar_morto(inimigo)
        return True
    return False


def _emitir_particulas(x, y, quantidade, cor, tempo_atual, modo="radial", raio=1.0):
    for i in range(max(0, int(quantidade))):
        ang = random.random() * math.tau
        vel = random.uniform(1.2, 5.8) * raio
        if modo == "tangencial":
            base = ang + math.pi / 2
            vx = math.cos(base) * vel + math.cos(ang) * random.uniform(0.3, 1.2)
            vy = math.sin(base) * vel + math.sin(ang) * random.uniform(0.3, 1.2)
        elif modo == "corte":
            vx = math.cos(ang) * random.uniform(1.0, 7.0)
            vy = math.sin(ang) * random.uniform(0.2, 2.0)
        else:
            vx = math.cos(ang) * vel
            vy = math.sin(ang) * vel
        _PARTICULAS.append({
            "x": float(x),
            "y": float(y),
            "vx": vx,
            "vy": vy,
            "cor": cor,
            "criada_ms": int(tempo_atual),
            "fim_ms": int(tempo_atual) + random.randint(380, 780),
            "tam": random.choice((1, 1, 2, 2, 3)),
            "drag": random.uniform(0.88, 0.96),
        })


def _efeito_base(manifestacao, origem, destino, tempo_atual):
    c1, c2, c3 = _cor(manifestacao)
    ox, oy = origem
    dx, dy = destino
    _EFEITOS.append({
        "tipo": "base",
        "manifestacao": _manifestacao(manifestacao),
        "origem": (float(ox), float(oy)),
        "destino": (float(dx), float(dy)),
        "criada_ms": int(tempo_atual),
        "fim_ms": int(tempo_atual) + 420,
        "cor": c1,
        "cor2": c2,
        "cor3": c3,
        "seed": random.randint(1000, 999999),
    })
    _emitir_particulas(ox, oy, 12, c1, tempo_atual)
    _emitir_particulas(dx, dy, 18, c2, tempo_atual)


def atualizar_estado_retorno(manifestacao, tempo_atual, teleporte_pressionado=False):
    global _RETORNO, _RETORNO_EXPIRADO_PENDENTE
    if _manifestacao(manifestacao) != "retornante":
        _RETORNO_EXPIRADO_PENDENTE = False
        return None
    if _RETORNO_EXPIRADO_PENDENTE:
        _RETORNO_EXPIRADO_PENDENTE = False
        return "expirado"
    if not _RETORNO:
        return None
    if int(tempo_atual) >= int(_RETORNO.get("fim_ms", 0)):
        _RETORNO = None
        return "expirado"
    if not teleporte_pressionado:
        _RETORNO["liberado_para_retorno"] = True
    return "ativo"


def retorno_disponivel(manifestacao, tempo_atual, teleporte_pressionado=False):
    if atualizar_estado_retorno(manifestacao, tempo_atual, teleporte_pressionado) != "ativo" or not _RETORNO:
        return False
    return bool(_RETORNO.get("liberado_para_retorno", False))


def teleporte_retornante_ativo(manifestacao):
    if _manifestacao(manifestacao) != "retornante" or not _RETORNO:
        return False
    return True


def consumir_retorno_manifestacao_retornante(manifestacao, tempo_atual, largura_mapa, altura_mapa, largura_player, altura_player):
    global _RETORNO, _RETORNO_EXPIRADO_PENDENTE
    if atualizar_estado_retorno(manifestacao, tempo_atual, teleporte_pressionado=True) != "ativo":
        return None
    if not _RETORNO or not _RETORNO.get("liberado_para_retorno", False):
        return None
    x, y = _RETORNO["player_pos"]
    x = max(0, min(int(largura_mapa) - int(largura_player), int(x)))
    y = max(0, min(int(altura_mapa) - int(altura_player), int(y)))
    _RETORNO = None
    _RETORNO_EXPIRADO_PENDENTE = False
    return x, y


def aplicar_efeito_teleporte_manifestacao(
    manifestacao,
    origem,
    destino,
    inimigos,
    boss_info=None,
    dano_base=10.0,
    efeitos_texto=None,
    tempo_atual=None,
    largura_mapa=None,
    altura_mapa=None,
    ondas=None,
    retorno_usado=False,
    player_pos_origem=None,
):
    tempo_atual = pygame.time.get_ticks() if tempo_atual is None else int(tempo_atual)
    chave = _manifestacao(manifestacao)
    _efeito_base(chave, origem, destino, tempo_atual)
    if chave == "eletrica":
        _teleporte_eletrico(destino, inimigos, boss_info, dano_base, efeitos_texto, tempo_atual)
        return {"cooldown_extra_ms": 0}
    if chave == "lacerante":
        _teleporte_lacerante(origem, destino, inimigos, boss_info, dano_base, efeitos_texto, tempo_atual)
        return {"cooldown_extra_ms": 0}
    if chave == "prismatica":
        _teleporte_prismatico(origem, destino, ondas, dano_base, tempo_atual, largura_mapa, altura_mapa)
        return {"cooldown_extra_ms": PRISMATICA_COOLDOWN_EXTRA_MS}
    if chave == "retornante":
        _teleporte_retornante(origem, destino, tempo_atual, retorno_usado, player_pos_origem)
        return {"cooldown_extra_ms": RETORNANTE_COOLDOWN_EXTRA_MS if retorno_usado else 0}
    if chave == "condutora":
        _teleporte_condutora(origem, destino, tempo_atual)
        return {"cooldown_extra_ms": 0}
    if chave == "gravitante":
        _teleporte_gravitante(destino, inimigos, dano_base, tempo_atual)
        return {"cooldown_extra_ms": GRAVITANTE_COOLDOWN_EXTRA_MS}
    if chave == "parasitica":
        _teleporte_parasitica(destino, tempo_atual)
        return {"cooldown_extra_ms": 0}
    return {"cooldown_extra_ms": 0}


def _teleporte_eletrico(destino, inimigos, boss_info, dano_base, efeitos_texto, tempo_atual):
    x, y = destino
    c1, c2, _ = _cor("eletrica")
    raio = 128
    dano = float(dano_base) * 0.18
    _EFEITOS.append({"tipo": "anel", "x": x, "y": y, "raio": raio, "cor": c1, "cor2": c2, "criada_ms": tempo_atual, "fim_ms": tempo_atual + 430})
    for inimigo in list(inimigos or []):
        rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
        if rect is None:
            continue
        dist = _dist(rect.centerx, rect.centery, x, y)
        if dist > raio:
            continue
        nx, ny = _normalizar(rect.centerx - x, rect.centery - y)
        rect.x += int(nx * 7)
        rect.y += int(ny * 7)
        inimigo["stun_fim"] = max(int(inimigo.get("stun_fim", 0)), tempo_atual + 200)
        _aplicar_dano(inimigo, dano, tempo_atual, efeitos_texto, c1)
        _EFEITOS.append({"tipo": "raio_curto", "a": (x, y), "b": rect.center, "cor": c2, "criada_ms": tempo_atual, "fim_ms": tempo_atual + 160})
    if boss_info and boss_info.get("vivo") and boss_info.get("rect"):
        rect = boss_info["rect"]
        if _dist(rect.centerx, rect.centery, x, y) <= raio:
            boss_info["atingido_por_onda"] = tempo_atual
            boss_info["hit_flag"] = True
            boss_info["dano_manifestacao"] = float(dano_base) * 0.10


def _teleporte_lacerante(origem, destino, inimigos, boss_info, dano_base, efeitos_texto, tempo_atual):
    ox, oy = origem
    dx, dy = destino
    c1, c2, _ = _cor("lacerante")
    pontos = lacerante_manifestacao._curva_fenda(ox, oy, dx, dy, 42, tempo_atual + random.randint(1, 999999), 22)
    _EFEITOS.append({
        "tipo": "rasgo_lacerante",
        "origem": origem,
        "destino": destino,
        "pontos": pontos,
        "cor": c1,
        "cor2": c2,
        "criada_ms": tempo_atual,
        "fim_ms": tempo_atual + 520,
        "seed": random.randint(1, 999999),
    })
    dano = float(dano_base) * 0.52
    for inimigo in list(inimigos or []):
        rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
        if rect is None:
            continue
        if _distancia_segmento(rect.centerx, rect.centery, ox, oy, dx, dy) <= max(28, min(rect.w, rect.h) * 0.7):
            mult = 1.15 if inimigo.get("laceracao_temporal") else 1.0
            lacerante_manifestacao.aplicar_laceracao(inimigo, tempo_atual)
            _aplicar_dano(inimigo, dano * mult, tempo_atual, efeitos_texto, c1)
    if boss_info and boss_info.get("vivo") and boss_info.get("rect"):
        rect = boss_info["rect"]
        if _distancia_segmento(rect.centerx, rect.centery, ox, oy, dx, dy) <= 42:
            boss_info["atingido_por_onda"] = tempo_atual
            boss_info["hit_flag"] = True
            boss_info["dano_manifestacao"] = float(dano_base) * 0.28


def _teleporte_prismatico(origem, destino, ondas, dano_base, tempo_atual, largura_mapa, altura_mapa):
    global _EFEITOS
    ox, oy = origem
    x, y = destino
    c1, c2, c3 = _cor("prismatica")
    if ondas is not None:
        ondas[:] = [onda for onda in ondas if onda.get("tipo_manifestacao") != "prisma_refracao" or not onda.get("grande_prisma_teleporte")]
        prisma = prismatica_manifestacao.criar_prisma(x, y, tempo_atual, max(1.0, float(dano_base) * 0.22), largura_mapa, altura_mapa)
        prisma["grande_prisma_teleporte"] = True
        prisma["fim_ms"] = tempo_atual + 3800
        prisma["rect"].inflate_ip(34, 34)
        prisma["pos_x"] = float(prisma["rect"].x)
        prisma["pos_y"] = float(prisma["rect"].y)
        ondas.append(prisma)
    _EFEITOS.append({
        "tipo": "prisma_flash",
        "x": x,
        "y": y,
        "origem": (ox, oy),
        "destino": (x, y),
        "cor": c1,
        "cor2": c2,
        "cor3": c3,
        "criada_ms": tempo_atual,
        "fim_ms": tempo_atual + 680,
    })


def _teleporte_retornante(origem, destino, tempo_atual, retorno_usado, player_pos_origem):
    global _RETORNO, _RETORNO_EXPIRADO_PENDENTE
    c1, c2, _ = _cor("retornante")
    if retorno_usado:
        _EFEITOS.append({"tipo": "retorno_fluxo", "origem": origem, "destino": destino, "cor": c1, "cor2": c2, "criada_ms": tempo_atual, "fim_ms": tempo_atual + 460})
        return
    _RETORNO_EXPIRADO_PENDENTE = False
    _RETORNO = {
        "origem": origem,
        "player_pos": player_pos_origem or origem,
        "criada_ms": tempo_atual,
        "fim_ms": tempo_atual + RETORNANTE_JANELA_MS,
        "cor": c1,
        "cor2": c2,
        "liberado_para_retorno": False,
    }


def _teleporte_condutora(origem, destino, tempo_atual):
    c1 = (55, 255, 150)
    c2 = (115, 255, 245)
    c3 = (255, 230, 95)
    _LINHAS_CONDUTORAS[:] = []
    _LINHAS_CONDUTORAS.append({
        "origem": origem,
        "destino": destino,
        "criada_ms": tempo_atual,
        "fim_ms": tempo_atual + 3600,
        "armada_ms": tempo_atual + 220,
        "ultimo_tick_ms": tempo_atual,
        "travessias": {},
        "alvos": [],
        "curto_aplicado": False,
        "seed": random.randint(1, 999999),
        "cor": c1,
        "cor2": c2,
        "cor3": c3,
    })


def _teleporte_gravitante(destino, inimigos, dano_base, tempo_atual):
    x, y = destino
    c1, c2, c3 = _cor("gravitante")
    afetados = []
    raio = 158
    for inimigo in list(inimigos or []):
        rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
        if rect is None or inimigo.get("vida", 1) <= 0:
            continue
        dist = _dist(rect.centerx, rect.centery, x, y)
        if dist > raio:
            continue
        rx, ry = _normalizar(rect.centerx - x, rect.centery - y)
        tangencial = random.choice((-1, 1))
        tx, ty = -ry * tangencial, rx * tangencial
        forca = 9.0 * (1.0 - min(0.7, dist / max(1, raio) * 0.55))
        afetados.append({"alvo": inimigo, "vx": tx * forca + rx * 1.8, "vy": ty * forca + ry * 1.8, "ultimo_colisao": {}})
    _IMPULSOS_GRAVITANTES.append({
        "x": x,
        "y": y,
        "criada_ms": tempo_atual,
        "fim_ms": tempo_atual + 680,
        "afetados": afetados,
        "dano_colisao": max(2.0, float(dano_base) * 0.34),
        "cor": c1,
        "cor2": c2,
        "cor3": c3,
    })
    _EFEITOS.append({"tipo": "orbital", "x": x, "y": y, "raio": raio, "cor": c1, "cor2": c2, "criada_ms": tempo_atual, "fim_ms": tempo_atual + 620})


def _teleporte_parasitica(destino, tempo_atual):
    x, y = destino
    c1, c2, c3 = _cor("parasitica")
    for i in range(3):
        ang = -math.pi / 2 + (i - 1) * 0.85 + random.uniform(-0.25, 0.25)
        _PARASITAS.append({
            "x": float(x) + math.cos(ang) * 18,
            "y": float(y) + math.sin(ang) * 18,
            "vx": math.cos(ang) * random.uniform(2.2, 4.6),
            "vy": math.sin(ang) * random.uniform(2.2, 4.6),
            "criada_ms": tempo_atual,
            "fim_ms": tempo_atual + 4300,
            "estado": "buscando",
            "alvo": None,
            "ultimo_tick_ms": tempo_atual,
            "cor": c1,
            "cor2": c2,
            "cor3": c3,
            "seed": random.randint(1, 999999),
        })
    _EFEITOS.append({"tipo": "eclosao_parasita", "x": x, "y": y, "cor": c1, "cor2": c2, "criada_ms": tempo_atual, "fim_ms": tempo_atual + 560})


def atualizar_efeitos_teleporte_manifestacao(inimigos, boss_info, disparos, tempo_atual, dano_base, efeitos_texto=None, largura_mapa=None, altura_mapa=None, jogador_rect=None):
    tempo_atual = int(tempo_atual)
    _limpar_efeitos_teleporte_expirados(tempo_atual)
    _atualizar_linhas_condutoras(inimigos, tempo_atual, dano_base, efeitos_texto, jogador_rect)
    _atualizar_impulsos_gravitantes(inimigos, tempo_atual, dano_base, efeitos_texto, largura_mapa, altura_mapa)
    _atualizar_parasitas(inimigos, tempo_atual, dano_base, efeitos_texto)
    mortos = list(_MORTOS_PENDENTES)
    _MORTOS_PENDENTES.clear()
    return mortos


def _alvo_linha_condutora(alvos_ids, inimigos):
    vivos = []
    for inimigo in list(inimigos or []):
        if isinstance(inimigo, dict) and id(inimigo) in alvos_ids and inimigo.get("vida", 1) > 0:
            vivos.append(inimigo)
    return vivos


def _jogador_cruzou_linha(linha, jogador_rect):
    if jogador_rect is None:
        return False
    ox, oy = linha["origem"]
    dx, dy = linha["destino"]
    cx, cy = jogador_rect.center
    if _distancia_segmento(cx, cy, ox, oy, dx, dy) > max(18, min(jogador_rect.w, jogador_rect.h) * 0.45):
        return False
    # Evita acionar apenas por estar parado na entrada/saida imediata do teleporte.
    margem_ponta = max(36, min(jogador_rect.w, jogador_rect.h) * 1.6)
    if _dist(cx, cy, ox, oy) < margem_ponta or _dist(cx, cy, dx, dy) < margem_ponta:
        return False
    return True


def _aplicar_curto_condutor(linha, inimigos, tempo_atual, dano_base, efeitos_texto):
    alvos = _alvo_linha_condutora(set(linha.get("alvos", [])), inimigos)
    if not alvos:
        return
    dano = max(1.0, float(dano_base) * condutora_manifestacao.FIO_DANO_MULT * 0.50)
    for inimigo in alvos:
        rect = inimigo.get("rect")
        if rect is None:
            continue
        inimigo["stun_fim"] = max(int(inimigo.get("stun_fim", 0)), int(tempo_atual) + 3000)
        condutora_manifestacao.marcar_alvo(inimigo, tempo_atual, dano_base, efeitos_texto)
        _aplicar_dano(inimigo, dano, tempo_atual, efeitos_texto, linha["cor2"], "CURTO")
        if inimigo.get("vida", 1) <= 0 and inimigo not in _MORTOS_PENDENTES:
            _MORTOS_PENDENTES.append(inimigo)
        _EFEITOS.append({
            "tipo": "curto_condutor",
            "x": rect.centerx,
            "y": rect.centery,
            "cor": linha["cor"],
            "cor2": linha["cor2"],
            "cor3": linha["cor3"],
            "criada_ms": tempo_atual,
            "fim_ms": tempo_atual + 560,
            "seed": random.randint(1, 999999),
        })


def _atualizar_linhas_condutoras(inimigos, tempo_atual, dano_base, efeitos_texto, jogador_rect=None):
    for linha in list(_LINHAS_CONDUTORAS):
        ox, oy = linha["origem"]
        dx, dy = linha["destino"]
        for inimigo in list(inimigos or []):
            rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
            if rect is None or inimigo.get("vida", 1) <= 0:
                continue
            if _distancia_segmento(rect.centerx, rect.centery, ox, oy, dx, dy) > 20:
                continue
            chave = id(inimigo)
            if tempo_atual - int(linha["travessias"].get(chave, 0)) < 440:
                continue
            linha["travessias"][chave] = tempo_atual
            condutora_manifestacao.marcar_alvo(inimigo, tempo_atual, dano_base, efeitos_texto)
            alvos = linha.setdefault("alvos", [])
            if chave not in alvos:
                alvos.append(chave)
            if inimigo.get("fio_condutor", {}).get("carga", 1) > 1:
                _aplicar_dano(inimigo, float(dano_base) * 0.06, tempo_atual, efeitos_texto, linha["cor"])
            _EFEITOS.append({"tipo": "contato_condutor", "x": rect.centerx, "y": rect.centery, "cor": linha["cor"], "cor2": linha["cor2"], "criada_ms": tempo_atual, "fim_ms": tempo_atual + 250})
        if (
            not linha.get("curto_aplicado")
            and tempo_atual >= int(linha.get("armada_ms", 0))
            and _jogador_cruzou_linha(linha, jogador_rect)
        ):
            linha["curto_aplicado"] = True
            _aplicar_curto_condutor(linha, inimigos, tempo_atual, dano_base, efeitos_texto)


def _atualizar_impulsos_gravitantes(inimigos, tempo_atual, dano_base, efeitos_texto, largura_mapa, altura_mapa):
    for impulso in list(_IMPULSOS_GRAVITANTES):
        for item in impulso.get("afetados", []):
            alvo = item.get("alvo")
            rect = alvo.get("rect") if isinstance(alvo, dict) else None
            if rect is None or alvo.get("vida", 1) <= 0:
                continue
            rect.x += int(item.get("vx", 0.0))
            rect.y += int(item.get("vy", 0.0))
            if largura_mapa is not None:
                if rect.left < 0 or rect.right > int(largura_mapa):
                    _aplicar_dano(alvo, impulso["dano_colisao"] * 0.42, tempo_atual, efeitos_texto, impulso["cor2"])
                rect.x = max(0, min(int(largura_mapa) - rect.w, rect.x))
            if altura_mapa is not None:
                if rect.top < 0 or rect.bottom > int(altura_mapa):
                    _aplicar_dano(alvo, impulso["dano_colisao"] * 0.42, tempo_atual, efeitos_texto, impulso["cor2"])
                rect.y = max(0, min(int(altura_mapa) - rect.h, rect.y))
            item["vx"] *= 0.84
            item["vy"] *= 0.84
            for outro in list(inimigos or []):
                if outro is alvo or not isinstance(outro, dict) or outro.get("vida", 1) <= 0:
                    continue
                rect2 = outro.get("rect")
                if rect2 is None or not rect.colliderect(rect2):
                    continue
                chave = id(outro)
                if tempo_atual - int(item.setdefault("ultimo_colisao", {}).get(chave, 0)) < 260:
                    continue
                item["ultimo_colisao"][chave] = tempo_atual
                _aplicar_dano(alvo, impulso["dano_colisao"], tempo_atual, efeitos_texto, impulso["cor2"])
                _aplicar_dano(outro, impulso["dano_colisao"] * 0.75, tempo_atual, efeitos_texto, impulso["cor2"])
                _EFEITOS.append({"tipo": "impacto_gravitante", "x": (rect.centerx + rect2.centerx) / 2, "y": (rect.centery + rect2.centery) / 2, "cor": impulso["cor2"], "criada_ms": tempo_atual, "fim_ms": tempo_atual + 260})


def _escolher_alvo_parasita(parasita, inimigos):
    melhor = None
    melhor_dist = 220.0
    ocupados = {id(p.get("alvo")) for p in _PARASITAS if p.get("estado") == "preso" and p.get("alvo") is not None}
    for inimigo in list(inimigos or []):
        rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
        if rect is None or inimigo.get("vida", 1) <= 0 or id(inimigo) in ocupados:
            continue
        dist = _dist(parasita["x"], parasita["y"], rect.centerx, rect.centery)
        if dist < melhor_dist:
            melhor = inimigo
            melhor_dist = dist
    return melhor


def _atualizar_parasitas(inimigos, tempo_atual, dano_base, efeitos_texto):
    for parasita in list(_PARASITAS):
        alvo = parasita.get("alvo")
        if parasita.get("estado") == "buscando":
            alvo = _escolher_alvo_parasita(parasita, inimigos)
            if alvo is not None:
                parasita["alvo"] = alvo
            if alvo is not None and alvo.get("rect") is not None:
                rect = alvo["rect"]
                nx, ny = _normalizar(rect.centerx - parasita["x"], rect.centery - parasita["y"])
                osc = math.sin(tempo_atual * 0.014 + parasita["seed"]) * 0.8
                parasita["vx"] = parasita["vx"] * 0.72 + (nx - ny * 0.22 * osc) * 4.2
                parasita["vy"] = parasita["vy"] * 0.72 + (ny + nx * 0.22 * osc) * 4.2
                if _dist(parasita["x"], parasita["y"], rect.centerx, rect.centery) < max(18, min(rect.w, rect.h)):
                    parasita["estado"] = "preso"
                    parasita["ultimo_tick_ms"] = tempo_atual
                    parasitica_manifestacao.implantar_semente(alvo, tempo_atual, dano_base, efeitos_texto)
                    _EFEITOS.append({"tipo": "bote_parasita", "x": rect.centerx, "y": rect.centery, "cor": parasita["cor"], "cor2": parasita["cor2"], "criada_ms": tempo_atual, "fim_ms": tempo_atual + 320})
            parasita["x"] += parasita["vx"]
            parasita["y"] += parasita["vy"]
            parasita["vx"] *= 0.94
            parasita["vy"] *= 0.94
        elif alvo is not None and isinstance(alvo, dict) and alvo.get("rect") is not None and alvo.get("vida", 1) > 0:
            rect = alvo["rect"]
            ang = tempo_atual * 0.01 + parasita["seed"]
            parasita["x"] = rect.centerx + math.cos(ang) * (rect.w * 0.34)
            parasita["y"] = rect.centery + math.sin(ang) * (rect.h * 0.34)
            if tempo_atual - int(parasita.get("ultimo_tick_ms", 0)) >= 520:
                parasita["ultimo_tick_ms"] = tempo_atual
                vida_max = float(alvo.get("vida_maxima", alvo.get("vida_inimigo_maxima", max(alvo.get("vida", 1), dano_base * 8))))
                dano = max(1.0, min(float(dano_base) * 0.20, vida_max * 0.015))
                _aplicar_dano(alvo, dano, tempo_atual, efeitos_texto, parasita["cor"])
                if alvo.get("vida", 1) <= vida_max * 0.05 and str(alvo.get("tipo", "")).lower() not in ("boss", "chefe"):
                    _aplicar_dano(alvo, alvo.get("vida", 1) + 1, tempo_atual, efeitos_texto, parasita["cor2"], "execucao")
        else:
            parasita["fim_ms"] = min(int(parasita.get("fim_ms", tempo_atual)), tempo_atual + 120)


def _limpar_efeitos_teleporte_expirados(tempo_atual):
    global _RETORNO, _RETORNO_EXPIRADO_PENDENTE
    _EFEITOS[:] = [e for e in _EFEITOS if tempo_atual < int(e.get("fim_ms", 0))]
    _PARTICULAS[:] = [p for p in _PARTICULAS if tempo_atual < int(p.get("fim_ms", 0))]
    _LINHAS_CONDUTORAS[:] = [l for l in _LINHAS_CONDUTORAS if tempo_atual < int(l.get("fim_ms", 0))]
    _PARASITAS[:] = [p for p in _PARASITAS if tempo_atual < int(p.get("fim_ms", 0))]
    _IMPULSOS_GRAVITANTES[:] = [i for i in _IMPULSOS_GRAVITANTES if tempo_atual < int(i.get("fim_ms", 0))]
    if _RETORNO and tempo_atual >= int(_RETORNO.get("fim_ms", 0)):
        _RETORNO = None
        _RETORNO_EXPIRADO_PENDENTE = True


def limpar_efeitos_teleporte_expirados(tempo_atual=None):
    tempo_atual = pygame.time.get_ticks() if tempo_atual is None else int(tempo_atual)
    _limpar_efeitos_teleporte_expirados(tempo_atual)


def desenhar_efeitos_teleporte_manifestacao(tela, tempo_atual, config_graficos=None):
    perfil = _perfil_efeito(config_graficos)
    if perfil == "desativado":
        return
    tempo_atual = int(tempo_atual)
    _desenhar_linhas_condutoras(tela, tempo_atual, perfil)
    _desenhar_retorno(tela, tempo_atual, perfil)
    for efeito in list(_EFEITOS):
        _desenhar_efeito(tela, efeito, tempo_atual, perfil)
    _desenhar_parasitas(tela, tempo_atual, perfil)
    _desenhar_particulas(tela, tempo_atual, perfil)


def _progresso(efeito, tempo_atual):
    inicio = int(efeito.get("criada_ms", tempo_atual))
    fim = int(efeito.get("fim_ms", tempo_atual))
    return max(0.0, min(1.0, (tempo_atual - inicio) / max(1, fim - inicio)))


def _desenhar_efeito(tela, efeito, tempo_atual, perfil):
    p = _progresso(efeito, tempo_atual)
    fade = max(0.0, 1.0 - p)
    tipo = efeito.get("tipo")
    if tipo == "base":
        ox, oy = efeito["origem"]
        dx, dy = efeito["destino"]
        cor = efeito["cor"]
        cor2 = efeito["cor2"]
        pygame.draw.line(tela, (*cor, int(95 * fade)), (int(ox), int(oy)), (int(dx), int(dy)), 2)
        for x, y, r in ((ox, oy, 26 + p * 18), (dx, dy, 34 + p * 24)):
            surf = pygame.Surface((int(r * 2 + 10), int(r * 2 + 10)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*cor2, int(48 * fade)), (surf.get_width() // 2, surf.get_height() // 2), int(r), 2)
            tela.blit(surf, (int(x - surf.get_width() // 2), int(y - surf.get_height() // 2)), special_flags=pygame.BLEND_RGBA_ADD)
    elif tipo == "anel" or tipo == "orbital":
        raio = int(float(efeito.get("raio", 120)) * (0.15 + 0.95 * p))
        x, y = int(efeito["x"]), int(efeito["y"])
        cor = efeito["cor"]
        surf = pygame.Surface((raio * 2 + 12, raio * 2 + 12), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*cor, int(90 * fade)), (raio + 6, raio + 6), raio, 3)
        if perfil == "alto":
            for i in range(8):
                a = p * math.tau * (2 if tipo == "orbital" else 1) + i * math.tau / 8
                r = raio + math.sin(a * 2) * 6
                px = raio + 6 + math.cos(a) * r
                py = raio + 6 + math.sin(a) * r
                pygame.draw.circle(surf, (*efeito.get("cor2", cor), int(120 * fade)), (int(px), int(py)), 2)
        tela.blit(surf, (x - raio - 6, y - raio - 6), special_flags=pygame.BLEND_RGBA_ADD)
    elif tipo == "rasgo_lacerante":
        pontos = efeito.get("pontos")
        if pontos:
            largura = 34 + 18 * (1.0 - abs(0.5 - p) * 2.0)
            alpha = int(245 * fade)
            lacerante_manifestacao._desenhar_curva_lacerante(
                tela,
                pontos,
                largura,
                alpha,
                p,
                efeito.get("seed", 0),
                True,
            )
            ox, oy = pontos[0]
            dx, dy = pontos[-1]
            nx, ny = _normalizar(-(dy - oy), dx - ox)
            rng = random.Random(int(efeito.get("seed", 0)) + int(p * 80))
            for _ in range(12 if perfil == "alto" else 6):
                t = rng.random()
                px = ox + (dx - ox) * t + nx * rng.uniform(-22, 22)
                py = oy + (dy - oy) * t + ny * rng.uniform(-22, 22)
                cor = efeito["cor2"] if rng.random() < 0.42 else efeito["cor"]
                pygame.draw.line(
                    tela,
                    (*cor, max(0, min(190, int(150 * fade)))),
                    (int(px), int(py)),
                    (int(px + nx * rng.uniform(-16, 16)), int(py + ny * rng.uniform(-16, 16))),
                    1,
                )
    elif tipo == "corte" or tipo == "retorno_fluxo":
        ox, oy = efeito["origem"]
        dx, dy = efeito["destino"]
        cor = efeito["cor"]
        cor2 = efeito["cor2"]
        largura = 6 if tipo == "corte" else 4
        pygame.draw.line(tela, (35, 0, 26), (int(ox), int(oy)), (int(dx), int(dy)), largura + 5)
        pygame.draw.line(tela, cor, (int(ox), int(oy)), (int(dx), int(dy)), largura)
        pygame.draw.line(tela, cor2, (int(ox), int(oy)), (int(dx), int(dy)), 1)
        if perfil != "baixo":
            for i in range(9):
                t = i / 8.0
                px = ox + (dx - ox) * t
                py = oy + (dy - oy) * t
                off = math.sin(t * math.tau * 2 + efeito.get("seed", 0)) * 10
                nx, ny = _normalizar(-(dy - oy), dx - ox)
                pygame.draw.line(tela, cor, (int(px), int(py)), (int(px + nx * off), int(py + ny * off)), 1)
    elif tipo == "prisma_flash":
        x, y = int(efeito["x"]), int(efeito["y"])
        cor, cor2, cor3 = efeito["cor"], efeito["cor2"], efeito["cor3"]
        r = int(34 + p * 86)
        origem = efeito.get("origem")
        if origem:
            ox, oy = origem
            surf = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            vx, vy = _normalizar(x - ox, y - oy)
            lx, ly = -vy, vx
            for desloc, cor_luz, alpha in ((-10, cor2, 50), (0, cor, 72), (10, cor3, 46)):
                pygame.draw.line(
                    surf,
                    (*cor_luz, int(alpha * fade)),
                    (int(ox + lx * desloc), int(oy + ly * desloc)),
                    (int(x + lx * desloc * 0.4), int(y + ly * desloc * 0.4)),
                    2,
                )
            for i in range(5):
                t = (p * 1.4 + i / 5.0) % 1.0
                px = ox + (x - ox) * t
                py = oy + (y - oy) * t
                pygame.draw.circle(surf, (*random.choice((cor, cor2, cor3)), int(90 * fade)), (int(px), int(py)), 3)
            tela.blit(surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
        surf = pygame.Surface((r * 2 + 24, r * 2 + 24), pygame.SRCALPHA)
        local = [(px - x + r + 12, py - y + r + 12) for px, py in pts]
        pygame.draw.polygon(surf, (*cor, int(75 * fade)), local, 0)
        pygame.draw.polygon(surf, (*cor2, int(230 * fade)), local, 2)
        pygame.draw.polygon(
            surf,
            (*cor3, int(170 * fade)),
            [(r + 12, r + 12 - r // 2), (r + 12 + r // 2, r + 12), (r + 12, r + 12 + r // 2), (r + 12 - r // 2, r + 12)],
            1,
        )
        pygame.draw.line(surf, (*cor3, int(190 * fade)), (12, r + 12), (r * 2 + 12, r + 12), 1)
        pygame.draw.line(surf, (*cor, int(170 * fade)), (r + 12, 12), (r + 12, r * 2 + 12), 1)
        tela.blit(surf, (x - r - 12, y - r - 12), special_flags=pygame.BLEND_RGBA_ADD)
    elif tipo in ("contato_condutor", "curto_condutor", "impacto_gravitante", "bote_parasita", "eclosao_parasita", "raio_curto"):
        if tipo == "raio_curto":
            pygame.draw.line(tela, efeito["cor"], efeito["a"], efeito["b"], 2)
            return
        x, y = int(efeito["x"]), int(efeito["y"])
        cor = efeito["cor"]
        r = int((12 if tipo == "curto_condutor" else 8) + p * (46 if tipo == "curto_condutor" else 32))
        largura = 3 if tipo == "curto_condutor" else 2
        pygame.draw.circle(tela, cor, (x, y), r, largura)
        if "cor2" in efeito:
            pygame.draw.circle(tela, efeito["cor2"], (x, y), max(2, r // 3), 1)
        if tipo == "curto_condutor":
            rng = random.Random(int(efeito.get("seed", 0)) + int(p * 16))
            for i in range(8):
                ang = i * math.tau / 8 + rng.uniform(-0.25, 0.25)
                raio_a = r * rng.uniform(0.18, 0.48)
                raio_b = r * rng.uniform(0.72, 1.15)
                a = (int(x + math.cos(ang) * raio_a), int(y + math.sin(ang) * raio_a))
                b = (int(x + math.cos(ang + rng.uniform(-0.18, 0.18)) * raio_b), int(y + math.sin(ang) * raio_b))
                pygame.draw.line(tela, efeito.get("cor3", efeito["cor2"]), a, b, 1)


def _desenhar_linhas_condutoras(tela, tempo_atual, perfil):
    for linha in _LINHAS_CONDUTORAS:
        p = _progresso(linha, tempo_atual)
        fade = 1.0 - p
        ox, oy = linha["origem"]
        dx, dy = linha["destino"]
        cor = linha["cor"]
        cor2 = linha.get("cor2", cor)
        cor3 = linha.get("cor3", cor2)
        vx, vy = _normalizar(dx - ox, dy - oy)
        nx, ny = -vy, vx
        pontos = []
        segmentos = 13 if perfil == "alto" else 8 if perfil == "medio" else 4
        seed = int(linha.get("seed", 0)) + int(tempo_atual // 70)
        rng = random.Random(seed)
        for i in range(segmentos + 1):
            t = i / max(1, segmentos)
            jitter = math.sin(t * math.tau * 3 + tempo_atual * 0.018) * 7.0 + rng.uniform(-3.0, 3.0)
            if i in (0, segmentos):
                jitter = 0.0
            px = ox + (dx - ox) * t + nx * jitter
            py = oy + (dy - oy) * t + ny * jitter
            pontos.append((int(px), int(py)))
        pygame.draw.lines(tela, (6, 72, 48), False, pontos, 8)
        pygame.draw.lines(tela, cor2 if linha.get("curto_aplicado") else cor, False, pontos, 4)
        pygame.draw.lines(tela, (230, 255, 220), False, pontos[1:-1] or pontos, 1)
        if perfil != "baixo":
            for i in range(9 if perfil == "alto" else 5):
                t = (p * 2.4 + i / (9 if perfil == "alto" else 5)) % 1.0
                px = ox + (dx - ox) * t
                py = oy + (dy - oy) * t
                lado = math.sin(tempo_atual * 0.018 + i) * 5
                pygame.draw.circle(tela, cor3 if i % 2 else cor2, (int(px + nx * lado), int(py + ny * lado)), 3)
                if perfil == "alto":
                    pygame.draw.line(
                        tela,
                        cor2,
                        (int(px - vx * 11 + nx * lado), int(py - vy * 11 + ny * lado)),
                        (int(px + vx * 11 + nx * lado), int(py + vy * 11 + ny * lado)),
                        1,
                    )
        for x, y in (linha["origem"], linha["destino"]):
            pygame.draw.circle(tela, (6, 72, 48), (int(x), int(y)), int(20 + 5 * math.sin(tempo_atual * 0.016)), 2)
            pygame.draw.circle(tela, cor2, (int(x), int(y)), int(13 + 4 * math.sin(tempo_atual * 0.019)), 1)


def _desenhar_retorno(tela, tempo_atual, perfil):
    if not _RETORNO:
        return
    p = _progresso(_RETORNO, tempo_atual)
    x, y = _RETORNO["origem"]
    cor, cor2 = _RETORNO["cor"], _RETORNO["cor2"]
    r = int(24 + math.sin(tempo_atual * 0.012) * 6)
    pygame.draw.circle(tela, cor, (int(x), int(y)), r, 2)
    pygame.draw.circle(tela, cor2, (int(x), int(y)), max(4, r // 3), 1)
    if p > 0.72:
        pygame.draw.circle(tela, cor2 if tempo_atual // 90 % 2 else cor, (int(x), int(y)), r + 8, 1)
    if perfil == "alto":
        for i in range(6):
            a = tempo_atual * 0.005 + i * math.tau / 6
            pygame.draw.circle(tela, cor, (int(x + math.cos(a) * (r + 8)), int(y + math.sin(a) * (r + 8))), 2)


def _desenhar_parasitas(tela, tempo_atual, perfil):
    for p in _PARASITAS:
        x, y = int(p["x"]), int(p["y"])
        cor, cor2 = p["cor"], p["cor2"]
        pygame.draw.circle(tela, (18, 35, 18), (x, y), 8)
        pygame.draw.circle(tela, cor, (x, y), 6, 2)
        pygame.draw.circle(tela, cor2, (x, y), 2)
        if perfil != "baixo":
            vx, vy = p.get("vx", 0.0), p.get("vy", 0.0)
            pygame.draw.line(tela, cor, (x, y), (int(x - vx * 3), int(y - vy * 3)), 1)


def _desenhar_particulas(tela, tempo_atual, perfil):
    passo = 0.9 if perfil == "alto" else 0.65 if perfil == "medio" else 0.4
    for part in list(_PARTICULAS):
        part["x"] += part["vx"] * passo
        part["y"] += part["vy"] * passo
        part["vx"] *= part.get("drag", 0.92)
        part["vy"] *= part.get("drag", 0.92)
        fade = max(0.0, min(1.0, (int(part.get("fim_ms", tempo_atual)) - tempo_atual) / 700.0))
        cor = part.get("cor", (120, 220, 255))
        pygame.draw.circle(tela, cor, (int(part["x"]), int(part["y"])), max(1, int(part.get("tam", 1) * fade)))
