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

    # Parse once to robustly handle IPv6 and percent-encoding
    parsed = urlparse(config)
    if parsed.scheme != "tuic":
        raise ValueError("Not a TUIC configuration")

    uuid = parsed.username or ""
    password = parsed.password or ""

    host = parsed.hostname or ""
    try:
        port = int(parsed.port) if parsed.port is not None else 443
    except Exception:
        raise ValueError(f"Invalid port in TUIC configuration: {parsed.netloc}")

    # Parse query params
    params = parse_qs(parsed.query or "")

    return {
        "protocol": "tuic",
        "host": host,
        "port": port,
        "uuid": uuid,
        "password": password,
        "congestion_control": params.get("congestion_control", ["bbr"])[0],
        "alpn": params.get("alpn", ["h3"])[0],
        "sni": params.get("sni", [""])[0]
    }