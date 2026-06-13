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
_convites = {}

COOP_INIMIGO_VIDA_MULT = 1.45
COOP_BOSS_VIDA_MULT = 1.75
COOP_SYNC_MUNDO_MS = 120
COOP_CONVITE_DELAY_MS = 4000


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
    global _world_snapshot
    fase_solicitada = None
    if not inicializar_se_preciso():
        return None

    try:
        from rede import fila_recebimento

        while True:
            try:
                dados = fila_recebimento.get_nowait()
            except queue.Empty:
                break

            if not isinstance(dados, dict):
                continue

            if dados.get("coop_tipo") == "player":
                _remote.update({
                    "ativo": True,
                    "x": int(dados.get("x", _remote["x"])),
                    "y": int(dados.get("y", _remote["y"])),
                    "direcao": dados.get("direcao", _remote["direcao"]) or "down",
                    "vida": dados.get("vida", _remote["vida"]),
                    "vida_maxima": dados.get("vida_maxima", _remote["vida_maxima"]),
                    "morto": bool(dados.get("morto", False)),
                    "fase": int(dados.get("fase", fase_atual)),
                    "ultimo_ms": pygame.time.get_ticks(),
                })
            elif dados.get("coop_tipo") == "fase":
                try:
                    fase_solicitada = int(dados.get("fase", fase_atual))
                except Exception:
                    fase_solicitada = None
            elif dados.get("coop_tipo") == "mundo":
                if int(dados.get("fase", fase_atual)) == int(fase_atual):
                    _world_snapshot = dados
            elif dados.get("coop_tipo") == "convite":
                _registrar_convite_remoto(dados, fase_atual)
            elif dados.get("coop_tipo") == "barreira":
                _registrar_barreira_remota(dados, fase_atual)
            elif "game_over" in dados and dados.get("game_over"):
                fase_solicitada = -1
    except Exception as e:
        registrar_erro("Multiplayer: erro ao processar pacotes cooperativos", e)

    return fase_solicitada


def _serializar_inimigo(inimigo):
    rect = inimigo.get("rect") if isinstance(inimigo, dict) else None
    if rect is None:
        return None
    return {
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
                return criar_inimigo(x, y, **kwargs)
            except TypeError:
                continue
            except Exception:
                break
    rect = pygame.Rect(x, y, int(dados.get("w", 32)), int(dados.get("h", 32)))
    return {"rect": rect, "image": None}


def _aplicar_inimigo_remoto(inimigo, dados):
    rect = inimigo.get("rect")
    if rect is None:
        rect = pygame.Rect(0, 0, int(dados.get("w", 32)), int(dados.get("h", 32)))
        inimigo["rect"] = rect
    rect.x = int(dados.get("x", rect.x))
    rect.y = int(dados.get("y", rect.y))
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


def sincronizar_mundo(fase_atual, inimigos, criar_inimigo=None, boss=None, economia=None):
    """Host envia o mundo; client aplica o snapshot para ver os mesmos inimigos e economia."""
    global _fase_atual, _ultimo_mundo_envio_ms
    _fase_atual = int(fase_atual or 1)
    if not modo_multiplayer() or not inicializar_se_preciso():
        return None

    if eh_host():
        agora = pygame.time.get_ticks()
        if agora - _ultimo_mundo_envio_ms >= COOP_SYNC_MUNDO_MS:
            try:
                from rede import fila_envio
                fila_envio.put({
                    "coop_tipo": "mundo",
                    "fase": int(fase_atual),
                    "inimigos": [d for d in (_serializar_inimigo(i) for i in list(inimigos or [])) if d],
                    "boss": boss or {},
                    "economia": economia or {},
                })
                _ultimo_mundo_envio_ms = agora
            except Exception as e:
                registrar_erro("Multiplayer: erro ao enviar snapshot de mundo", e)
        return None

    if not _world_snapshot or int(_world_snapshot.get("fase", fase_atual)) != int(fase_atual):
        return None

    dados_inimigos = _world_snapshot.get("inimigos", [])
    while len(inimigos) < len(dados_inimigos):
        inimigos.append(_criar_inimigo_remoto(dados_inimigos[len(inimigos)], criar_inimigo))
    del inimigos[len(dados_inimigos):]
    for inimigo, dados in zip(inimigos, dados_inimigos):
        _aplicar_inimigo_remoto(inimigo, dados)
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


def acao_confirmada(acao, fase_atual, delay_ms=COOP_CONVITE_DELAY_MS):
    if not modo_multiplayer():
        return False
    _processar_pacotes(fase_atual)
    estado = _estado_convite(acao)
    if not (estado["local"] and estado["remoto"]):
        return False
    if estado["inicio_ms"] is None:
        estado["inicio_ms"] = pygame.time.get_ticks()
        return False
    if pygame.time.get_ticks() - estado["inicio_ms"] < int(delay_ms):
        return False
    _convites.pop(acao, None)
    return True


def cancelar_acao(acao):
    _convites.pop(acao, None)


def desenhar_status_acao(tela, fonte, acao, fase_atual, delay_ms=COOP_CONVITE_DELAY_MS):
    if not modo_multiplayer() or tela is None:
        return
    estado = _estado_convite(acao)
    if not (estado["local"] or estado["remoto"]):
        return
    restante = None
    if estado["local"] and estado["remoto"] and estado["inicio_ms"] is not None:
        restante = max(0.0, (int(delay_ms) - (pygame.time.get_ticks() - estado["inicio_ms"])) / 1000.0)
    texto_acao = "loja" if acao.startswith("loja") else "pause"
    if restante is None:
        texto = f"Aguardando o outro jogador para abrir {texto_acao}"
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
    if agora - _ultimo_envio_ms >= 50:
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

    x = int(_remote.get("x", 0))
    y = int(_remote.get("y", 0))
    if _remote.get("morto") and sprite_morto is not None:
        tela.blit(sprite_morto, (x, y))
        return

    frames_por_direcao = frames_cliente if modo_atual() == "host" else frames_host
    direcao = _remote.get("direcao") or "down"
    frames = frames_por_direcao.get(direcao) or frames_por_direcao.get("down")
    if not frames:
        return
    tela.blit(frames[frame_atual % len(frames)], (x, y))


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
