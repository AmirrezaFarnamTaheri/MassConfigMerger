from pathlib import Path
import re

SOURCES_FILE = Path("sources.txt")

# Regular expressions shared across modules
PROTOCOL_RE = re.compile(
    r"(?:"
    r"vmess|vless|reality|ssr?|trojan|hy2|hysteria2?|tuic|"
    r"shadowtls|juicity|naive|brook|wireguard|"
    r"socks5|socks4|socks|http|https|grpc|ws|wss|"
    r"tcp|kcp|quic|h2"
    r")://\S+",
    re.IGNORECASE,
)
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=_-]+$")

# Safety limit for base64 decoding to avoid huge payloads
MAX_DECODE_SIZE = 256 * 1024  # 256 kB
