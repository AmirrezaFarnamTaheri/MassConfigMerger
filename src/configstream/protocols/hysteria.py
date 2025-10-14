"""Hysteria protocol support.

Hysteria is a modern protocol optimized for lossy networks.
"""

from __future__ import annotations

from typing import Dict, Any
from urllib.parse import parse_qs, urlparse


def parse_hysteria(config: str) -> Dict[str, Any]:
    """Parse Hysteria configuration.

    Format: hysteria://host:port?...params
    """
    if not config.startswith("hysteria://"):
        raise ValueError("Not a Hysteria configuration")

    parsed = urlparse(config)

    host = parsed.hostname or ""
    if not host:
        raise ValueError("Hysteria configuration missing host")

    # Validate/normalize port
    if parsed.port is None:
        port = 443
    else:
        try:
            port = int(parsed.port)
        except Exception:
            raise ValueError(f"Invalid port in Hysteria configuration: {parsed.netloc}")
        if port <= 0 or port > 65535:
            raise ValueError(f"Port out of range in Hysteria configuration: {port}")

    params = parse_qs(parsed.query or "")

    # Normalize boolean parameters that may be "1"/"true"/"yes"
    def _as_bool(val: str) -> bool:
        return str(val).lower() in {"1", "true", "yes", "on"}

    return {
        "protocol": "hysteria",
        "host": host,
        "port": port,
        "auth": params.get("auth", [""])[0],
        "peer": params.get("peer", [""])[0],
        "insecure": _as_bool(params.get("insecure", ["0"])[0]),
        "alpn": params.get("alpn", [""])[0],
        "obfs": params.get("obfs", [""])[0],
        "protocol_version": params.get("protocol", [""])[0],
    }


def format_hysteria(config: Dict[str, Any]) -> str:
    """Format Hysteria configuration as URL.

    Args:
        config: Configuration dictionary

    Returns:
        Hysteria URL string
    """
    url = f"hysteria://{config['host']}:{config['port']}"

    params = []
    if config.get("auth"):
        params.append(f"auth={config['auth']}")
    if config.get("peer"):
        params.append(f"peer={config['peer']}")
    if config.get("insecure"):
        params.append("insecure=1")
    if config.get("alpn"):
        params.append(f"alpn={config['alpn']}")

    if params:
        url += "?" + "&".join(params)

    return url
