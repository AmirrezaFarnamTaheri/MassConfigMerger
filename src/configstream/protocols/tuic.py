"""TUIC protocol support.

TUIC is a proxy protocol based on QUIC.
"""
from __future__ import annotations

import json
from typing import Dict, Any
from urllib.parse import parse_qs, urlparse


def parse_tuic(config: str) -> Dict[str, Any]:
    """Parse TUIC configuration.

    Format: tuic://uuid:password@host:port?...params

    Args:
        config: TUIC configuration string

    Returns:
        Dictionary with parsed configuration
    """
    if not config.startswith("tuic://"):
        raise ValueError("Not a TUIC configuration")

    # Remove protocol
    config = config.replace("tuic://", "")

    # Extract credentials and host
    if "@" in config:
        creds, host_part = config.split("@", 1)
        uuid, password = creds.split(":", 1) if ":" in creds else (creds, "")
    else:
        uuid = ""
        password = ""
        host_part = config

    # Extract host and port
    if "?" in host_part:
        host_port, params_str = host_part.split("?", 1)
        params = parse_qs(params_str)
    else:
        host_port = host_part
        params = {}

    if ":" in host_port:
        host, port = host_port.rsplit(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 443

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