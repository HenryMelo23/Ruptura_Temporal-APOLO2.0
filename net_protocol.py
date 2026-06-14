import json
import time
import zlib


PROTOCOL_NAME = "RT_COOP"
PROTOCOL_VERSION = 2
MAX_PACKET_BYTES = 256 * 1024
NET_USAR_COMPRESSAO_SNAPSHOT = False

TYPE_LEGACY = "LEGACY_COOP"
TYPE_WORLD_SNAPSHOT = "WORLD_SNAPSHOT"
TYPE_ENEMY_MOVEMENT = "ENEMY_MOVEMENT"
TYPE_PLAYER_STATE = "PLAYER_STATE"
TYPE_DAMAGE_REQUEST = "DAMAGE_REQUEST"
TYPE_VISUAL_EVENT = "VISUAL_EVENT"
TYPE_PING = "PING"
TYPE_PONG = "PONG"
TYPE_HEARTBEAT_FAST = "HEARTBEAT_FAST"
TYPE_UDP_HELLO = "UDP_HELLO"

KNOWN_TYPES = {
    TYPE_LEGACY,
    TYPE_WORLD_SNAPSHOT,
    TYPE_ENEMY_MOVEMENT,
    TYPE_PLAYER_STATE,
    TYPE_DAMAGE_REQUEST,
    TYPE_VISUAL_EVENT,
    TYPE_PING,
    TYPE_PONG,
    TYPE_HEARTBEAT_FAST,
    TYPE_UDP_HELLO,
}


class ProtocolError(ValueError):
    pass


def packet_type_for_legacy(dados):
    tipo = dados.get("coop_tipo") if isinstance(dados, dict) else None
    if tipo == "mundo":
        return TYPE_WORLD_SNAPSHOT
    if tipo == "inimigos_mov":
        return TYPE_ENEMY_MOVEMENT
    if tipo == "player":
        return TYPE_PLAYER_STATE
    if tipo == "dano":
        return TYPE_DAMAGE_REQUEST
    if tipo in ("evento", "eventos"):
        return TYPE_VISUAL_EVENT
    if tipo == "ping":
        return TYPE_PING
    if tipo == "pong":
        return TYPE_PONG
    return TYPE_LEGACY


def normalizar_packet(dados, packet_type=None, reliable=True, channel=None):
    if not isinstance(dados, dict):
        raise ProtocolError("packet must be a dict")
    if dados.get("protocol") == PROTOCOL_NAME:
        validar_packet(dados)
        return dados

    tipo = packet_type or packet_type_for_legacy(dados)
    packet = {
        "protocol": PROTOCOL_NAME,
        "version": PROTOCOL_VERSION,
        "type": tipo,
        "seq": int(dados.get("seq", 0) or 0),
        "time": int(dados.get("host_time", dados.get("timestamp", now_ms())) or now_ms()),
        "reliable": bool(reliable),
        "channel": channel or ("tcp" if reliable else "udp"),
        "payload": dados,
    }
    validar_packet(packet)
    return packet


def validar_packet(packet):
    if not isinstance(packet, dict):
        raise ProtocolError("packet must be a dict")
    if packet.get("protocol") != PROTOCOL_NAME:
        raise ProtocolError("invalid protocol")
    if int(packet.get("version", 0) or 0) != PROTOCOL_VERSION:
        raise ProtocolError("invalid protocol version")
    if packet.get("type") not in KNOWN_TYPES:
        raise ProtocolError(f"unknown packet type: {packet.get('type')}")
    int(packet.get("seq", 0) or 0)
    if not isinstance(packet.get("payload", {}), dict):
        raise ProtocolError("payload must be a dict")
    return True


def encode_packet(dados, reliable=True, channel=None):
    packet = normalizar_packet(dados, reliable=reliable, channel=channel)
    compactar = bool(NET_USAR_COMPRESSAO_SNAPSHOT and packet.get("type") == TYPE_WORLD_SNAPSHOT)
    raw = json.dumps(packet, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if compactar:
        raw = b"Z" + zlib.compress(raw)
    else:
        raw = b"J" + raw
    if len(raw) > MAX_PACKET_BYTES:
        raise ProtocolError("packet too large")
    return raw


def encode_stream_packet(dados, reliable=True, channel="tcp"):
    return encode_packet(dados, reliable=reliable, channel=channel) + b"\n"


def decode_packet(data):
    if not data:
        raise ProtocolError("empty packet")
    if isinstance(data, str):
        data = data.encode("utf-8")
    if len(data) > MAX_PACKET_BYTES:
        raise ProtocolError("packet too large")

    marcador = data[:1]
    conteudo = data[1:] if marcador in (b"J", b"Z") else data
    if marcador == b"Z":
        conteudo = zlib.decompress(conteudo)

    decoded = json.loads(conteudo.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ProtocolError("decoded packet must be dict")
    if decoded.get("protocol") != PROTOCOL_NAME:
        return decoded
    validar_packet(decoded)
    if decoded.get("type") == TYPE_LEGACY:
        return decoded.get("payload", {})
    return decoded.get("payload", {})


def now_ms():
    return int(time.time() * 1000)
