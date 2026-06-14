import queue
import socket
import threading
import time

from net_protocol import decode_packet, encode_packet
from qa_logger import registrar_erro


UDP_GAME_PORT = 5052

fila_udp_envio = queue.Queue()
fila_udp_recebimento = queue.Queue()

_udp_socket = None
_udp_remote_addr = None
_udp_started = False
_udp_mode = "offline"
_udp_lock = threading.Lock()
_rodando_udp = True
_metricas = {
    "udp_conectado": False,
    "udp_modo": "offline",
    "udp_enviados": 0,
    "udp_recebidos": 0,
    "udp_erros": 0,
    "udp_bytes_env": 0,
    "udp_bytes_rec": 0,
    "udp_ultimo_recebido_ms": 0,
    "udp_ultimo_enviado_ms": 0,
}


def iniciar_udp_host(porta=UDP_GAME_PORT):
    global _udp_mode
    _udp_mode = "host"
    return _iniciar_udp("0.0.0.0", porta, None)


def iniciar_udp_cliente(ip_host, porta=UDP_GAME_PORT):
    global _udp_mode
    _udp_mode = "join"
    ok = _iniciar_udp("0.0.0.0", 0, (ip_host, int(porta)))
    if ok:
        enviar_udp({"coop_tipo": "udp_hello", "client_time": _agora_ms()})
    return ok


def enviar_udp(dados):
    if not udp_ativo():
        return False
    fila_udp_envio.put(dados)
    return True


def udp_ativo():
    return _udp_socket is not None and _udp_started


def obter_diagnostico():
    dados = dict(_metricas)
    dados["fila_udp_envio"] = fila_udp_envio.qsize()
    dados["fila_udp_recebimento"] = fila_udp_recebimento.qsize()
    dados["udp_conectado"] = bool(_udp_remote_addr is not None and udp_ativo())
    dados["udp_modo"] = _udp_mode
    if dados["udp_ultimo_recebido_ms"]:
        dados["udp_idade_ultimo_recebido"] = max(0, _agora_ms() - int(dados["udp_ultimo_recebido_ms"]))
    else:
        dados["udp_idade_ultimo_recebido"] = 0
    return dados


def parar_udp():
    global _rodando_udp, _udp_socket, _udp_started, _udp_remote_addr
    _rodando_udp = False
    with _udp_lock:
        sock = _udp_socket
        _udp_socket = None
        _udp_remote_addr = None
        _udp_started = False
    if sock is not None:
        try:
            sock.close()
        except Exception:
            pass


def _iniciar_udp(bind_host, bind_port, remote_addr):
    global _rodando_udp, _udp_remote_addr, _udp_socket, _udp_started
    if _udp_started and _udp_socket is not None:
        return True
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((bind_host, int(bind_port)))
        sock.settimeout(0.05)
        with _udp_lock:
            _rodando_udp = True
            _udp_socket = sock
            _udp_remote_addr = remote_addr
            _udp_started = True
            _metricas["udp_modo"] = _udp_mode
            _metricas["udp_conectado"] = remote_addr is not None
        threading.Thread(target=_udp_recv_loop, daemon=True).start()
        threading.Thread(target=_udp_send_loop, daemon=True).start()
        return True
    except Exception as e:
        _metricas["udp_erros"] += 1
        registrar_erro("Net UDP: erro ao iniciar canal de jogo", e)
        return False


def _udp_recv_loop():
    global _udp_remote_addr
    while _rodando_udp:
        try:
            with _udp_lock:
                sock = _udp_socket
            if sock is None:
                break
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                continue
            pacote = decode_packet(data)
            with _udp_lock:
                if _udp_remote_addr is None:
                    _udp_remote_addr = addr
                _metricas["udp_conectado"] = True
                _metricas["udp_recebidos"] += 1
                _metricas["udp_bytes_rec"] += len(data)
                _metricas["udp_ultimo_recebido_ms"] = _agora_ms()
            if isinstance(pacote, dict) and pacote.get("coop_tipo") != "udp_hello":
                fila_udp_recebimento.put(pacote)
        except Exception as e:
            _metricas["udp_erros"] += 1
            registrar_erro("Net UDP: erro ao receber pacote", e)


def _udp_send_loop():
    while _rodando_udp:
        try:
            try:
                dados = fila_udp_envio.get(timeout=0.05)
            except queue.Empty:
                continue
            with _udp_lock:
                sock = _udp_socket
                remote = _udp_remote_addr
            if sock is None or remote is None:
                continue
            encoded = encode_packet(dados, reliable=False, channel="udp")
            sock.sendto(encoded, remote)
            _metricas["udp_enviados"] += 1
            _metricas["udp_bytes_env"] += len(encoded)
            _metricas["udp_ultimo_enviado_ms"] = _agora_ms()
        except Exception as e:
            _metricas["udp_erros"] += 1
            registrar_erro("Net UDP: erro ao enviar pacote", e)


def _agora_ms():
    return int(time.time() * 1000)
