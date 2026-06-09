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
            elif "game_over" in dados and dados.get("game_over"):
                fase_solicitada = -1
    except Exception as e:
        registrar_erro("Multiplayer: erro ao processar pacotes cooperativos", e)

    return fase_solicitada


def atualizar(fase_atual, pos_x, pos_y, direcao, vida, vida_maxima, morto=False):
    global _ultimo_envio_ms

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
