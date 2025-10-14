"""TUIC protocol support.

TUIC is a proxy protocol based on QUIC.
"""

from __future__ import annotations

from typing import Dict, Any
from urllib.parse import parse_qs, urlparse


def parse_tuic(config: str) -> Dict[str, Any]:
    """Parse TUIC configuration."""
    if not config.startswith("tuic://"):
        raise ValueError("Not a TUIC configuration")

    parsed = urlparse(config)
    if parsed.scheme != "tuic":
        raise ValueError("Not a TUIC configuration")

    uuid = parsed.username or ""
    password = parsed.password or ""

    host = parsed.hostname or ""
    if not host:
        raise ValueError("TUIC configuration missing host")

    try:
        port = int(parsed.port) if parsed.port is not None else 443
    except Exception:
        raise ValueError(f"Invalid port in TUIC configuration: {parsed.netloc}")
    if port <= 0 or port > 65535:
        raise ValueError(f"Port out of range in TUIC configuration: {port}")

    params = parse_qs(parsed.query or "")

    # Normalize ALPN (comma-separated allowed)
    raw_alpn = params.get("alpn", ["h3"])[0]
    alpn = (
        ",".join([p.strip() for p in raw_alpn.split(",") if p.strip()])
        if raw_alpn
        else "h3"
    )

    return {
        "protocol": "tuic",
        "host": host,
        "port": port,
        "uuid": uuid,
        "password": password,
        "congestion_control": params.get("congestion_control", ["bbr"])[0],
        "alpn": alpn,
        "sni": params.get("sni", [""])[0],
    }
