import queue
import socket
import threading
import time

from net_protocol import decode_packet, encode_packet
from qa_logger import registrar_erro


CANAL_PLAYER = "player"
CANAL_WORLD = "world"
CANAL_ENEMY_MOVE = "enemy_move"
CANAL_DAMAGE = "damage"
CANAL_HEARTBEAT = "heartbeat"
CANAL_DEFAULT = CANAL_PLAYER

UDP_PLAYER_PORT = 5052
UDP_WORLD_PORT = 5053
UDP_DAMAGE_PORT = 5054
UDP_HEARTBEAT_PORT = 5055
UDP_ENEMY_MOVE_PORT = 5056
UDP_GAME_PORT = UDP_PLAYER_PORT

UDP_CHANNEL_PORTS = {
    CANAL_PLAYER: UDP_PLAYER_PORT,
    CANAL_WORLD: UDP_WORLD_PORT,
    CANAL_ENEMY_MOVE: UDP_ENEMY_MOVE_PORT,
    CANAL_DAMAGE: UDP_DAMAGE_PORT,
    CANAL_HEARTBEAT: UDP_HEARTBEAT_PORT,
}

fila_udp_envio = queue.Queue()
fila_udp_recebimento = queue.Queue()
filas_udp_envio = {canal: queue.Queue() for canal in UDP_CHANNEL_PORTS}
filas_udp_recebimento = {canal: queue.Queue() for canal in UDP_CHANNEL_PORTS}

_udp_sockets = {}
_udp_remote_addrs = {}
_udp_started_channels = set()
_udp_mode = "offline"
_udp_lock = threading.Lock()
_rodando_udp = True
_metricas_por_canal = {
    canal: {
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
    for canal in UDP_CHANNEL_PORTS
}


def iniciar_udp_host(porta=UDP_GAME_PORT):
    global _udp_mode
    _udp_mode = "host"
    base_porta = int(porta or UDP_GAME_PORT)
    portas = dict(UDP_CHANNEL_PORTS)
    portas[CANAL_PLAYER] = base_porta
    return _iniciar_udp_multicanal("0.0.0.0", portas, None)


def iniciar_udp_cliente(ip_host, porta=UDP_GAME_PORT):
    global _udp_mode
    _udp_mode = "join"
    base_porta = int(porta or UDP_GAME_PORT)
    portas = dict(UDP_CHANNEL_PORTS)
    portas[CANAL_PLAYER] = base_porta
    remotos = {canal: (ip_host, int(porta_canal)) for canal, porta_canal in portas.items()}
    ok = _iniciar_udp_multicanal("0.0.0.0", {canal: 0 for canal in portas}, remotos)
    if ok:
        for canal in UDP_CHANNEL_PORTS:
            enviar_udp({"coop_tipo": "udp_hello", "canal": canal, "client_time": _agora_ms()}, canal=canal)
    return ok


def canal_para_pacote(dados):
    tipo = dados.get("coop_tipo") if isinstance(dados, dict) else None
    if tipo == "inimigos_mov":
        return CANAL_ENEMY_MOVE
    if tipo == "mundo":
        return CANAL_WORLD
    if tipo == "dano":
        return CANAL_DAMAGE
    if tipo in ("ping", "pong", "snapshot_request", "udp_hello", "heartbeat"):
        return CANAL_HEARTBEAT
    if tipo == "player":
        return CANAL_PLAYER
    return CANAL_DEFAULT


def enviar_udp(dados, canal=None):
    canal = _normalizar_canal(canal or canal_para_pacote(dados))
    if not udp_conectado(canal):
        return False
    filas_udp_envio[canal].put(dados)
    return True


def udp_ativo(canal=None):
    if canal is not None:
        canal = _normalizar_canal(canal)
        return canal in _udp_started_channels and _udp_sockets.get(canal) is not None
    return any(_udp_sockets.get(canal) is not None for canal in UDP_CHANNEL_PORTS)


def udp_conectado(canal=None):
    if canal is not None:
        canal = _normalizar_canal(canal)
        return bool(_udp_remote_addrs.get(canal) is not None and udp_ativo(canal))
    return any(udp_conectado(canal) for canal in UDP_CHANNEL_PORTS)


def obter_filas_recebimento():
    return [filas_udp_recebimento[canal] for canal in UDP_CHANNEL_PORTS]


def obter_diagnostico():
    agora = _agora_ms()
    dados = {
        "udp_conectado": udp_conectado(),
        "udp_modo": _udp_mode,
        "udp_enviados": 0,
        "udp_recebidos": 0,
        "udp_erros": 0,
        "udp_bytes_env": 0,
        "udp_bytes_rec": 0,
        "udp_ultimo_recebido_ms": 0,
        "udp_ultimo_enviado_ms": 0,
        "fila_udp_envio": sum(filas_udp_envio[canal].qsize() for canal in UDP_CHANNEL_PORTS),
        "fila_udp_recebimento": sum(filas_udp_recebimento[canal].qsize() for canal in UDP_CHANNEL_PORTS),
    }
    for canal in UDP_CHANNEL_PORTS:
        metricas = _metricas_por_canal[canal]
        ultimo_recebido = int(metricas.get("udp_ultimo_recebido_ms", 0) or 0)
        ultimo_enviado = int(metricas.get("udp_ultimo_enviado_ms", 0) or 0)
        idade = max(0, agora - ultimo_recebido) if ultimo_recebido else 0
        prefixo = f"udp_{canal}"
        dados[f"{prefixo}_conectado"] = udp_conectado(canal)
        dados[f"{prefixo}_age"] = idade
        dados[f"{prefixo}_enviados"] = int(metricas.get("udp_enviados", 0) or 0)
        dados[f"{prefixo}_recebidos"] = int(metricas.get("udp_recebidos", 0) or 0)
        dados[f"fila_udp_{canal}_envio"] = filas_udp_envio[canal].qsize()
        dados[f"fila_udp_{canal}_recebimento"] = filas_udp_recebimento[canal].qsize()
        dados["udp_enviados"] += int(metricas.get("udp_enviados", 0) or 0)
        dados["udp_recebidos"] += int(metricas.get("udp_recebidos", 0) or 0)
        dados["udp_erros"] += int(metricas.get("udp_erros", 0) or 0)
        dados["udp_bytes_env"] += int(metricas.get("udp_bytes_env", 0) or 0)
        dados["udp_bytes_rec"] += int(metricas.get("udp_bytes_rec", 0) or 0)
        dados["udp_ultimo_recebido_ms"] = max(dados["udp_ultimo_recebido_ms"], ultimo_recebido)
        dados["udp_ultimo_enviado_ms"] = max(dados["udp_ultimo_enviado_ms"], ultimo_enviado)
    if dados["udp_ultimo_recebido_ms"]:
        dados["udp_idade_ultimo_recebido"] = max(0, agora - int(dados["udp_ultimo_recebido_ms"]))
    else:
        dados["udp_idade_ultimo_recebido"] = 0
    return dados


def parar_udp():
    global _rodando_udp
    _rodando_udp = False
    with _udp_lock:
        sockets = list(_udp_sockets.values())
        _udp_sockets.clear()
        _udp_remote_addrs.clear()
        _udp_started_channels.clear()
    for sock in sockets:
        try:
            sock.close()
        except Exception:
            pass


def _iniciar_udp_multicanal(bind_host, portas, remotos):
    global _rodando_udp
    ok_algum = False
    for canal, porta in portas.items():
        remote_addr = remotos.get(canal) if isinstance(remotos, dict) else remotos
        if _iniciar_udp(canal, bind_host, int(porta), remote_addr):
            ok_algum = True
    return ok_algum


def _iniciar_udp(canal, bind_host, bind_port, remote_addr):
    global _rodando_udp
    canal = _normalizar_canal(canal)
    if udp_ativo(canal):
        return True
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((bind_host, int(bind_port)))
        sock.settimeout(0.05)
        with _udp_lock:
            _rodando_udp = True
            _udp_sockets[canal] = sock
            _udp_remote_addrs[canal] = remote_addr
            _udp_started_channels.add(canal)
            _metricas_por_canal[canal]["udp_modo"] = _udp_mode
            _metricas_por_canal[canal]["udp_conectado"] = remote_addr is not None
        threading.Thread(target=_udp_recv_loop, args=(canal,), daemon=True).start()
        threading.Thread(target=_udp_send_loop, args=(canal,), daemon=True).start()
        return True
    except Exception as e:
        _metricas_por_canal[canal]["udp_erros"] += 1
        registrar_erro(f"Net UDP: erro ao iniciar canal {canal}", e)
        return False


def _udp_recv_loop(canal):
    canal = _normalizar_canal(canal)
    while _rodando_udp:
        try:
            with _udp_lock:
                sock = _udp_sockets.get(canal)
            if sock is None:
                break
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                continue
            pacote = decode_packet(data)
            with _udp_lock:
                if _udp_remote_addrs.get(canal) is None:
                    _udp_remote_addrs[canal] = addr
                _metricas_por_canal[canal]["udp_conectado"] = True
                _metricas_por_canal[canal]["udp_recebidos"] += 1
                _metricas_por_canal[canal]["udp_bytes_rec"] += len(data)
                _metricas_por_canal[canal]["udp_ultimo_recebido_ms"] = _agora_ms()
            if isinstance(pacote, dict) and pacote.get("coop_tipo") != "udp_hello":
                filas_udp_recebimento[canal].put(pacote)
        except Exception as e:
            _metricas_por_canal[canal]["udp_erros"] += 1
            registrar_erro(f"Net UDP: erro ao receber pacote no canal {canal}", e)


def _udp_send_loop(canal):
    canal = _normalizar_canal(canal)
    while _rodando_udp:
        try:
            try:
                dados = filas_udp_envio[canal].get(timeout=0.05)
            except queue.Empty:
                continue
            with _udp_lock:
                sock = _udp_sockets.get(canal)
                remote = _udp_remote_addrs.get(canal)
            if sock is None or remote is None:
                continue
            encoded = encode_packet(dados, reliable=False, channel=f"udp:{canal}")
            sock.sendto(encoded, remote)
            _metricas_por_canal[canal]["udp_enviados"] += 1
            _metricas_por_canal[canal]["udp_bytes_env"] += len(encoded)
            _metricas_por_canal[canal]["udp_ultimo_enviado_ms"] = _agora_ms()
        except Exception as e:
            _metricas_por_canal[canal]["udp_erros"] += 1
            registrar_erro(f"Net UDP: erro ao enviar pacote no canal {canal}", e)


def _normalizar_canal(canal):
    return canal if canal in UDP_CHANNEL_PORTS else CANAL_DEFAULT


def _agora_ms():
    return int(time.time() * 1000)
