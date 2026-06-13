import json
import queue
import threading

import pygame

import Variaveis
from qa_logger import registrar_erro


_conn = None
_threads_started = False
_modo = "offline"
_remote = {
    "ativo": False,
    "x": 0,
    "y": 0,
    "net_x": 0.0,
    "net_y": 0.0,
    "render_x": 0.0,
    "render_y": 0.0,
    "vel_x_estimada": 0.0,
    "vel_y_estimada": 0.0,
    "direcao": "down",
    "vida": 0,
    "vida_maxima": 0,
    "morto": False,
    "fase": 1,
    "ultimo_ms": 0,
}
_ultimo_envio_ms = 0
_ultimo_fase_enviada = None
_fase_atual = 1
_ultimo_mundo_envio_ms = 0
_world_snapshot = None
_world_snapshot_recebido_ms = 0
_world_snapshot_seq_aplicado = None
_mundo_seq_envio = 0
_proximo_coop_id = 1
_convites = {}
_debug_visivel = False
_debug_tecla_f10_ativa = False
_diagnostico = {
    "pacotes_processados_frame": 0,
    "fila_envio": 0,
    "fila_recebimento": 0,
    "tempo_desde_ultimo_snapshot": 0,
    "qtd_inimigos_snapshot": 0,
    "tamanho_snapshot_json": 0,
}

COOP_INIMIGO_VIDA_MULT = 1.45
COOP_BOSS_VIDA_MULT = 1.75
COOP_SYNC_PLAYER_MS = 33
COOP_SYNC_MUNDO_MS = 80
COOP_CONVITE_DELAY_MS = 4000
COOP_SILENCIO_CONFIRMA_MS = 10000
COOP_INTERPOLACAO_POS = 0.18
COOP_EXTRAPOLACAO_MAX_MS = 150
COOP_MAX_PACOTES_POR_FRAME = 20
COOP_ENTIDADE_TIMEOUT_MS = 450


def _ler_modo_jogo():
    try:
        with open("saves/modo_jogo.json", "r") as f:
            dados = json.load(f)
        return dados.get("modo", "offline"), dados.get("ip")
    except Exception:
        return "offline", None


def modo_multiplayer():
    modo, _ = _ler_modo_jogo()
    return modo in ("host", "join")


def modo_atual():
    global _modo
    if _modo == "offline":
        _modo, _ = _ler_modo_jogo()
    return _modo


def eh_host():
    return modo_atual() == "host"


def eh_cliente():
    return modo_atual() == "join"


def frames_jogador_local(frames_host, frames_cliente):
    return frames_cliente if eh_cliente() else frames_host


def fase_atual():
    return int(_fase_atual or _remote.get("fase", 1) or 1)


def multiplicador_vida_inimigo():
    return COOP_INIMIGO_VIDA_MULT if modo_multiplayer() else 1.0


def multiplicador_vida_boss():
    return COOP_BOSS_VIDA_MULT if modo_multiplayer() else 1.0


def aplicar_multiplicador_vida_inimigo(valor):
    return int(float(valor) * multiplicador_vida_inimigo())


def aplicar_multiplicador_vida_boss(valor):
    return int(float(valor) * multiplicador_vida_boss())


def inicializar_se_preciso():
    global _conn, _threads_started, _modo

    _modo, ip = _ler_modo_jogo()
    if _modo not in ("host", "join"):
        return False

    if _conn is not None:
        return True

    try:
        from rede import (
            anunciar_host_udp,
            conectar_ao_host,
            descobrir_host_udp,
            iniciar_host,
            thread_envio,
            thread_recebimento,
        )

        if _modo == "host":
            anunciar_host_udp()
            _conn = iniciar_host()
        else:
            ip_host = ip or descobrir_host_udp()
            if not ip_host:
                return False
            _conn = conectar_ao_host(ip_host)

        if _conn is None:
            return False

        if not _threads_started:
            threading.Thread(target=thread_envio, args=(_conn,), daemon=True).start()
            threading.Thread(target=thread_recebimento, args=(_conn,), daemon=True).start()
            _threads_started = True

        return True
    except Exception as e:
        registrar_erro("Multiplayer: erro ao inicializar conexao cooperativa", e)
        return False


def enviar_transicao_fase(fase_destino):
    global _ultimo_fase_enviada
    if not inicializar_se_preciso():
        return
    if _ultimo_fase_enviada == fase_destino:
        return
    try:
        from rede import fila_envio

        fila_envio.put({"coop_tipo": "fase", "fase": int(fase_destino)})
        _ultimo_fase_enviada = fase_destino
    except Exception as e:
        registrar_erro("Multiplayer: erro ao enviar transicao de fase", e)


def _processar_pacotes(fase_atual):
    global _world_snapshot, _world_snapshot_recebido_ms
    fase_solicitada = None
    if not inicializar_se_preciso():
        return None

    try:
        from rede import fila_recebimento
        processados = 0

        while processados < COOP_MAX_PACOTES_POR_FRAME:
            try:
                dados = fila_recebimento.get_nowait()
            except queue.Empty:
                break
            processados += 1

            if not isinstance(dados, dict):
                continue

            if dados.get("coop_tipo") == "player":
                agora = pygame.time.get_ticks()
                estava_ativo = bool(_remote.get("ativo"))
                novo_x = float(dados.get("x", _remote["x"]))
                novo_y = float(dados.get("y", _remote["y"]))
                antigo_x = float(_remote.get("net_x", _remote["x"]))
                antigo_y = float(_remote.get("net_y", _remote["y"]))
                ultimo_ms = int(_remote.get("ultimo_ms", agora))
                delta_ms = max(1, agora - ultimo_ms)
                _remote.update({
                    "ativo": True,
                    "x": int(novo_x),
                    "y": int(novo_y),
                    "net_x": novo_x,
                    "net_y": novo_y,
                    "render_x": float(_remote.get("render_x", novo_x)) if estava_ativo else novo_x,
                    "render_y": float(_remote.get("render_y", novo_y)) if estava_ativo else novo_y,
                    "vel_x_estimada": (novo_x - antigo_x) / delta_ms,
                    "vel_y_estimada": (novo_y - antigo_y) / delta_ms,
                    "direcao": dados.get("direcao", _remote["direcao"]) or "down",
                    "vida": dados.get("vida", _remote["vida"]),
                    "vida_maxima": dados.get("vida_maxima", _remote["vida_maxima"]),
                    "morto": bool(dados.get("morto", False)),
                    "fase": int(dados.get("fase", fase_atual)),
                    "ultimo_ms": agora,
                })
            elif dados.get("coop_tipo") == "fase":
                try:
                    fase_solicitada = int(dados.get("fase", fase_atual))
                except Exception:
                    fase_solicitada = None
            elif dados.get("coop_tipo") == "mundo":
                if int(dados.get("fase", fase_atual)) == int(fase_atual):
                    _world_snapshot = dados
                    _world_snapshot_recebido_ms = pygame.time.get_ticks()
            elif dados.get("coop_tipo") == "convite":
                _registrar_convite_remoto(dados, fase_atual)
            elif dados.get("coop_tipo") == "barreira":
                _registrar_barreira_remota(dados, fase_atual)
            elif "game_over" in dados and dados.get("game_over"):
                fase_solicitada = -1
        _diagnostico["pacotes_processados_frame"] = processados
        _diagnostico["fila_recebimento"] = fila_recebimento.qsize()
    except Exception as e:
        registrar_erro("Multiplayer: erro ao processar pacotes cooperativos", e)

    return fase_solicitada


def _obter_coop_id(inimigo):
    global _proximo_coop_id
    if not isinstance(inimigo, dict):
        return None
    coop_id = inimigo.get("coop_id") or inimigo.get("_coop_id")
    if coop_id is None:
        coop_id = _proximo_coop_id
        _proximo_coop_id += 1
        inimigo["coop_id"] = coop_id
    return str(coop_id)


def _suavizar_rect_remoto(entidade, agora=None):
    rect = entidade.get("rect") if isinstance(entidade, dict) else None
    if rect is None:
        return
    agora = pygame.time.get_ticks() if agora is None else agora
    net_x = float(entidade.get("net_x", rect.x))
    net_y = float(entidade.get("net_y", rect.y))
    render_x = float(entidade.get("render_x", net_x))
    render_y = float(entidade.get("render_y", net_y))
    ultimo_ms = int(entidade.get("ultimo_snapshot_ms", agora))

    atraso_ms = max(0, agora - ultimo_ms)
    extra_ms = min(COOP_EXTRAPOLACAO_MAX_MS, atraso_ms)
    alvo_x = net_x + float(entidade.get("vel_x_estimada", 0.0)) * extra_ms
    alvo_y = net_y + float(entidade.get("vel_y_estimada", 0.0)) * extra_ms

    render_x += (alvo_x - render_x) * COOP_INTERPOLACAO_POS
    render_y += (alvo_y - render_y) * COOP_INTERPOLACAO_POS

    entidade["render_x"] = render_x
    entidade["render_y"] = render_y
    rect.x = int(round(render_x))
    rect.y = int(round(render_y))


def _posicao_remota_suavizada(agora=None):
    agora = pygame.time.get_ticks() if agora is None else agora
    net_x = float(_remote.get("net_x", _remote.get("x", 0)))
    net_y = float(_remote.get("net_y", _remote.get("y", 0)))
    render_x = float(_remote.get("render_x", net_x))
    render_y = float(_remote.get("render_y", net_y))
    ultimo_ms = int(_remote.get("ultimo_ms", agora))

    atraso_ms = max(0, agora - ultimo_ms)
    extra_ms = min(COOP_EXTRAPOLACAO_MAX_MS, atraso_ms)
    alvo_x = net_x + float(_remote.get("vel_x_estimada", 0.0)) * extra_ms
    alvo_y = net_y + float(_remote.get("vel_y_estimada", 0.0)) * extra_ms

    render_x += (alvo_x - render_x) * COOP_INTERPOLACAO_POS
    render_y += (alvo_y - render_y) * COOP_INTERPOLACAO_POS
    _remote["render_x"] = render_x
    _remote["render_y"] = render_y
    return int(round(render_x)), int(round(render_y))


def _serializar_inimigo(inimigo):
    rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
    if rect is None:
        return None
    return {
        "coop_id": _obter_coop_id(inimigo),
        "x": int(rect.x),
        "y": int(rect.y),
        "w": int(rect.width),
        "h": int(rect.height),
        "vida": float(inimigo.get("vida", 1)),
        "vida_maxima": float(inimigo.get("vida_maxima", inimigo.get("vida", 1))),
        "tipo": inimigo.get("tipo", 1),
        "elite": bool(inimigo.get("elite", False)),
        "pos_x": float(inimigo.get("pos_x", rect.x)),
        "pos_y": float(inimigo.get("pos_y", rect.y)),
        "estado": inimigo.get("estado"),
    }


def _criar_inimigo_remoto(dados, criar_inimigo):
    x = int(dados.get("x", 0))
    y = int(dados.get("y", 0))
    tipo = dados.get("tipo", 1)
    elite = bool(dados.get("elite", False))
    if criar_inimigo is not None:
        for kwargs in ({"tipo": tipo, "is_elite": elite}, {"tipo": tipo}, {"is_elite": elite}, {}):
            try:
                inimigo = criar_inimigo(x, y, **kwargs)
                _aplicar_inimigo_remoto(inimigo, dados, inicial=True)
                return inimigo
            except TypeError:
                continue
            except Exception:
                break
    rect = pygame.Rect(x, y, int(dados.get("w", 32)), int(dados.get("h", 32)))
    inimigo = {"rect": rect, "image": None}
    _aplicar_inimigo_remoto(inimigo, dados, inicial=True)
    return inimigo


def _aplicar_inimigo_remoto(inimigo, dados, inicial=False):
    agora = pygame.time.get_ticks()
    rect = inimigo.get("rect")
    if rect is None:
        rect = pygame.Rect(0, 0, int(dados.get("w", 32)), int(dados.get("h", 32)))
        inimigo["rect"] = rect
    novo_x = float(dados.get("x", rect.x))
    novo_y = float(dados.get("y", rect.y))
    antigo_x = float(inimigo.get("net_x", rect.x))
    antigo_y = float(inimigo.get("net_y", rect.y))
    ultimo_ms = int(inimigo.get("ultimo_snapshot_ms", agora))
    delta_ms = max(1, agora - ultimo_ms)

    inimigo["coop_id"] = str(dados.get("coop_id", inimigo.get("coop_id", "")))
    inimigo["net_x"] = novo_x
    inimigo["net_y"] = novo_y
    inimigo["vel_x_estimada"] = 0.0 if inicial else (novo_x - antigo_x) / delta_ms
    inimigo["vel_y_estimada"] = 0.0 if inicial else (novo_y - antigo_y) / delta_ms
    inimigo["ultimo_snapshot_ms"] = agora
    if inicial or "render_x" not in inimigo:
        inimigo["render_x"] = novo_x
        inimigo["render_y"] = novo_y
        rect.x = int(round(novo_x))
        rect.y = int(round(novo_y))
    rect.width = int(dados.get("w", rect.width))
    rect.height = int(dados.get("h", rect.height))
    inimigo["vida"] = float(dados.get("vida", inimigo.get("vida", 1)))
    inimigo["vida_maxima"] = float(dados.get("vida_maxima", inimigo.get("vida_maxima", inimigo["vida"])))
    inimigo["tipo"] = dados.get("tipo", inimigo.get("tipo", 1))
    inimigo["elite"] = bool(dados.get("elite", inimigo.get("elite", False)))
    inimigo["pos_x"] = float(dados.get("pos_x", rect.x))
    inimigo["pos_y"] = float(dados.get("pos_y", rect.y))
    if dados.get("estado") is not None:
        inimigo["estado"] = dados.get("estado")
    _suavizar_rect_remoto(inimigo, agora)


def sincronizar_mundo(fase_atual, inimigos, criar_inimigo=None, boss=None, economia=None):
    """Host envia o mundo; client aplica o snapshot para ver os mesmos inimigos e economia."""
    global _fase_atual, _mundo_seq_envio, _ultimo_mundo_envio_ms, _world_snapshot_seq_aplicado
    _fase_atual = int(fase_atual or 1)
    if not modo_multiplayer() or not inicializar_se_preciso():
        return None

    if eh_host():
        agora = pygame.time.get_ticks()
        if agora - _ultimo_mundo_envio_ms >= COOP_SYNC_MUNDO_MS:
            try:
                from rede import fila_envio
                _mundo_seq_envio += 1
                pacote = {
                    "coop_tipo": "mundo",
                    "fase": int(fase_atual),
                    "seq": _mundo_seq_envio,
                    "inimigos": [d for d in (_serializar_inimigo(i) for i in list(inimigos or [])) if d],
                    "boss": boss or {},
                    "economia": economia or {},
                }
                fila_envio.put(pacote)
                _ultimo_mundo_envio_ms = agora
                _diagnostico["fila_envio"] = fila_envio.qsize()
                _diagnostico["qtd_inimigos_snapshot"] = len(pacote["inimigos"])
                _diagnostico["tamanho_snapshot_json"] = len(json.dumps(pacote, separators=(",", ":")))
            except Exception as e:
                registrar_erro("Multiplayer: erro ao enviar snapshot de mundo", e)
        return None

    agora = pygame.time.get_ticks()
    if not _world_snapshot or int(_world_snapshot.get("fase", fase_atual)) != int(fase_atual):
        for inimigo in list(inimigos or []):
            _suavizar_rect_remoto(inimigo, agora)
        return None

    _diagnostico["tempo_desde_ultimo_snapshot"] = max(0, agora - int(_world_snapshot_recebido_ms or agora))
    dados_inimigos = _world_snapshot.get("inimigos", [])
    seq = _world_snapshot.get("seq")
    if seq != _world_snapshot_seq_aplicado:
        existentes = {
            str(inimigo.get("coop_id")): inimigo
            for inimigo in list(inimigos or [])
            if isinstance(inimigo, dict) and inimigo.get("coop_id") is not None
        }
        ids_recebidos = set()
        for dados in dados_inimigos:
            coop_id = str(dados.get("coop_id", ""))
            if not coop_id:
                continue
            ids_recebidos.add(coop_id)
            inimigo = existentes.get(coop_id)
            if inimigo is None:
                inimigo = _criar_inimigo_remoto(dados, criar_inimigo)
                inimigos.append(inimigo)
            else:
                _aplicar_inimigo_remoto(inimigo, dados)
            inimigo["_coop_seen_ms"] = agora

        for inimigo in list(inimigos):
            coop_id = str(inimigo.get("coop_id", ""))
            if coop_id and coop_id not in ids_recebidos:
                visto_ms = int(inimigo.get("_coop_seen_ms", agora))
                if agora - visto_ms >= COOP_ENTIDADE_TIMEOUT_MS:
                    inimigos.remove(inimigo)
        _world_snapshot_seq_aplicado = seq

    for inimigo in list(inimigos or []):
        _suavizar_rect_remoto(inimigo, agora)
    _diagnostico["qtd_inimigos_snapshot"] = len(dados_inimigos)
    return _world_snapshot


def _estado_convite(chave):
    return _convites.setdefault(chave, {
        "local": False,
        "remoto": False,
        "inicio_ms": None,
        "concluido": False,
        "barreira_local": False,
        "barreira_remota": False,
    })


def _registrar_convite_remoto(dados, fase_atual):
    if int(dados.get("fase", fase_atual)) != int(fase_atual):
        return
    estado = _estado_convite(str(dados.get("acao", "")))
    estado["remoto"] = True
    if estado["local"] and estado["inicio_ms"] is None:
        estado["inicio_ms"] = pygame.time.get_ticks()


def _registrar_barreira_remota(dados, fase_atual):
    if int(dados.get("fase", fase_atual)) != int(fase_atual):
        return
    estado = _estado_convite(str(dados.get("acao", "")))
    estado["barreira_remota"] = True


def solicitar_acao(acao, fase_atual):
    if not modo_multiplayer():
        return True
    estado = _estado_convite(acao)
    if not estado["local"]:
        estado["local"] = True
        try:
            from rede import fila_envio
            fila_envio.put({"coop_tipo": "convite", "acao": acao, "fase": int(fase_atual)})
        except Exception as e:
            registrar_erro("Multiplayer: erro ao enviar convite cooperativo", e)
    if estado["remoto"] and estado["inicio_ms"] is None:
        estado["inicio_ms"] = pygame.time.get_ticks()
    return False


def acao_confirmada(acao, fase_atual, delay_ms=COOP_CONVITE_DELAY_MS, assumir_sim_apos_ms=None):
    if not modo_multiplayer():
        return False
    _processar_pacotes(fase_atual)
    estado = _estado_convite(acao)
    if estado["inicio_ms"] is None and (estado["local"] or estado["remoto"]):
        estado["inicio_ms"] = pygame.time.get_ticks()
    if assumir_sim_apos_ms and (estado["local"] or estado["remoto"]):
        if pygame.time.get_ticks() - int(estado.get("inicio_ms") or 0) >= int(assumir_sim_apos_ms):
            _convites.pop(acao, None)
            return True
    if not (estado["local"] and estado["remoto"]):
        return False
    if pygame.time.get_ticks() - estado["inicio_ms"] < int(delay_ms):
        return False
    _convites.pop(acao, None)
    return True


def cancelar_acao(acao):
    _convites.pop(acao, None)


def desenhar_status_acao(tela, fonte, acao, fase_atual, delay_ms=COOP_CONVITE_DELAY_MS, assumir_sim_apos_ms=None):
    if not modo_multiplayer() or tela is None:
        return
    estado = _estado_convite(acao)
    if not (estado["local"] or estado["remoto"]):
        return
    restante = None
    if estado["local"] and estado["remoto"] and estado["inicio_ms"] is not None:
        restante = max(0.0, (int(delay_ms) - (pygame.time.get_ticks() - estado["inicio_ms"])) / 1000.0)
    texto_acao = "loja" if acao.startswith("loja") else ("boss" if acao.startswith("boss") else "pause")
    if restante is None:
        texto = f"Aguardando o outro jogador para abrir {texto_acao}"
        if assumir_sim_apos_ms and estado["inicio_ms"] is not None:
            restante_auto = max(0.0, (int(assumir_sim_apos_ms) - (pygame.time.get_ticks() - estado["inicio_ms"])) / 1000.0)
            texto = f"Aguardando {texto_acao}: silencio confirma em {restante_auto:.1f}s"
    else:
        texto = f"{texto_acao.capitalize()} em {restante:.1f}s"
    fonte = fonte or pygame.font.Font(None, 28)
    surf = fonte.render(texto, True, (255, 245, 190))
    pad = 18
    rect = pygame.Rect(0, 0, surf.get_width() + pad * 2, surf.get_height() + pad)
    rect.center = (tela.get_width() // 2, 82)
    painel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(painel, (16, 14, 24, 215), painel.get_rect(), border_radius=8)
    pygame.draw.rect(painel, (0, 220, 255, 180), painel.get_rect(), 1, border_radius=8)
    painel.blit(surf, (pad, pad // 2))
    tela.blit(painel, rect.topleft)


def aguardar_barreira(acao, fase_atual, tela=None, fonte=None, mensagem="Aguardando o outro jogador...", delay_ms=COOP_CONVITE_DELAY_MS, timeout_ms=45000):
    if not modo_multiplayer():
        return
    estado = _estado_convite(acao)
    if not estado["barreira_local"]:
        estado["barreira_local"] = True
        try:
            from rede import fila_envio
            fila_envio.put({"coop_tipo": "barreira", "acao": acao, "fase": int(fase_atual)})
        except Exception as e:
            registrar_erro("Multiplayer: erro ao enviar barreira cooperativa", e)

    clock = pygame.time.Clock()
    inicio_saida = None
    inicio_espera = pygame.time.get_ticks()
    while True:
        _processar_pacotes(fase_atual)
        if estado.get("barreira_remota"):
            if inicio_saida is None:
                inicio_saida = pygame.time.get_ticks()
            if pygame.time.get_ticks() - inicio_saida >= int(delay_ms):
                break
        if timeout_ms and pygame.time.get_ticks() - inicio_espera >= int(timeout_ms):
            registrar_erro("Multiplayer: tempo limite aguardando barreira cooperativa")
            break
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
        if tela is not None:
            fonte_local = fonte or pygame.font.Font(None, 30)
            texto = mensagem
            if inicio_saida is not None:
                texto = f"Liberando em {max(0.0, (int(delay_ms) - (pygame.time.get_ticks() - inicio_saida)) / 1000.0):.1f}s"
            surf = fonte_local.render(texto, True, (255, 245, 190))
            painel = pygame.Surface((surf.get_width() + 40, surf.get_height() + 28), pygame.SRCALPHA)
            pygame.draw.rect(painel, (16, 14, 24, 230), painel.get_rect(), border_radius=8)
            pygame.draw.rect(painel, (0, 220, 255, 180), painel.get_rect(), 1, border_radius=8)
            painel.blit(surf, (20, 14))
            tela.blit(painel, painel.get_rect(center=(tela.get_width() // 2, tela.get_height() // 2)).topleft)
            pygame.display.flip()
        clock.tick(30)
    _convites.pop(acao, None)


def atualizar(fase_atual, pos_x, pos_y, direcao, vida, vida_maxima, morto=False):
    global _fase_atual, _ultimo_envio_ms
    _fase_atual = int(fase_atual or 1)

    if not inicializar_se_preciso():
        return None

    fase_solicitada = _processar_pacotes(fase_atual)

    agora = pygame.time.get_ticks()
    if agora - _ultimo_envio_ms >= COOP_SYNC_PLAYER_MS:
        try:
            from rede import fila_envio

            fila_envio.put({
                "coop_tipo": "player",
                "fase": int(fase_atual),
                "x": int(pos_x),
                "y": int(pos_y),
                "direcao": direcao or "down",
                "vida": int(max(0, vida)),
                "vida_maxima": int(max(1, vida_maxima)),
                "morto": bool(morto),
            })
            _ultimo_envio_ms = agora
            _diagnostico["fila_envio"] = fila_envio.qsize()
        except Exception as e:
            registrar_erro("Multiplayer: erro ao enviar estado do jogador", e)

    if fase_solicitada == fase_atual:
        return None
    return fase_solicitada


def desenhar_jogador_remoto(tela, fase_atual, frame_atual, frames_host, frames_cliente, sprite_morto=None):
    if not modo_multiplayer() or not _remote.get("ativo"):
        return
    if int(_remote.get("fase", fase_atual)) != int(fase_atual):
        return
    if pygame.time.get_ticks() - int(_remote.get("ultimo_ms", 0)) > 2500:
        return

    x, y = _posicao_remota_suavizada()
    if _remote.get("morto") and sprite_morto is not None:
        tela.blit(sprite_morto, (x, y))
        return

    frames_por_direcao = frames_cliente if modo_atual() == "host" else frames_host
    direcao = _remote.get("direcao") or "down"
    frames = frames_por_direcao.get(direcao) or frames_por_direcao.get("down")
    if not frames:
        return
    tela.blit(frames[frame_atual % len(frames)], (x, y))


def jogador_remoto_rect(fase_atual, largura, altura):
    if not modo_multiplayer() or not _remote.get("ativo"):
        return None
    if int(_remote.get("fase", fase_atual)) != int(fase_atual):
        return None
    if pygame.time.get_ticks() - int(_remote.get("ultimo_ms", 0)) > 2500:
        return None
    x, y = _posicao_remota_suavizada()
    return pygame.Rect(x, y, int(largura), int(altura))


def obter_diagnostico():
    dados = dict(_diagnostico)
    dados["modo"] = modo_atual()
    dados["snapshot_ms"] = COOP_SYNC_MUNDO_MS
    dados["player_ms"] = COOP_SYNC_PLAYER_MS
    dados["interpolacao"] = COOP_INTERPOLACAO_POS
    return dados


def desenhar_diagnostico(tela, fonte=None):
    global _debug_tecla_f10_ativa, _debug_visivel
    if not modo_multiplayer() or tela is None:
        return
    try:
        teclas = pygame.key.get_pressed()
        f10_pressionado = bool(teclas[pygame.K_F10])
        if f10_pressionado and not _debug_tecla_f10_ativa:
            _debug_visivel = not _debug_visivel
        _debug_tecla_f10_ativa = f10_pressionado
    except Exception:
        pass
    if not _debug_visivel:
        return

    fonte = fonte or pygame.font.Font(None, 22)
    dados = obter_diagnostico()
    linhas = [
        f"COOP {dados['modo']} | player {dados['player_ms']}ms | mundo {dados['snapshot_ms']}ms",
        f"fila out/in: {dados['fila_envio']}/{dados['fila_recebimento']} | pacotes/frame: {dados['pacotes_processados_frame']}",
        f"snapshot: {dados['tempo_desde_ultimo_snapshot']}ms | inimigos: {dados['qtd_inimigos_snapshot']} | json: {dados['tamanho_snapshot_json']}b",
        f"interp: {dados['interpolacao']:.2f} | extrap max: {COOP_EXTRAPOLACAO_MAX_MS}ms",
    ]
    largura = max(fonte.size(linha)[0] for linha in linhas) + 24
    altura = len(linhas) * (fonte.get_linesize() + 2) + 18
    painel = pygame.Surface((largura, altura), pygame.SRCALPHA)
    pygame.draw.rect(painel, (10, 12, 20, 220), painel.get_rect(), border_radius=6)
    pygame.draw.rect(painel, (0, 220, 255, 120), painel.get_rect(), 1, border_radius=6)
    y = 9
    for linha in linhas:
        surf = fonte.render(linha, True, (210, 245, 255))
        painel.blit(surf, (12, y))
        y += fonte.get_linesize() + 2
    tela.blit(painel, (18, 78))


def aplicar_transicao_recebida(fase_solicitada, game_manager):
    if not fase_solicitada or game_manager is None:
        return False

    from game_manager import EstadoJogo

    if fase_solicitada == -1:
        game_manager.mudar_estado(EstadoJogo.GAME_OVER)
        return True

    mapa = {
        1: EstadoJogo.JOGO_FASE_1,
        2: EstadoJogo.JOGO_FASE_2,
        3: EstadoJogo.JOGO_FASE_3,
        4: EstadoJogo.JOGO_FASE_4,
    }
    estado = mapa.get(int(fase_solicitada))
    if estado is None:
        return False
    game_manager.mudar_estado(estado, dados={"modo_jogo": modo_atual(), "fase": int(fase_solicitada)})
    return True
