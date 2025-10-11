"""Hysteria protocol support.

Hysteria is a modern protocol optimized for lossy networks.
"""
from __future__ import annotations

import base64
import json
from typing import Dict, Any
from urllib.parse import parse_qs, urlparse


def parse_hysteria(config: str) -> Dict[str, Any]:
    """Parse Hysteria configuration.

    Format: hysteria://host:port?...params

    Args:
        config: Hysteria configuration string

    Returns:
        Dictionary with parsed configuration
    """
    if not config.startswith("hysteria://"):
        raise ValueError("Not a Hysteria configuration")

    # Parse URL
    parsed = urlparse(config)

    # Extract host and port
    host = parsed.hostname
    port = parsed.port or 443

    # Parse query parameters
    params = parse_qs(parsed.query)

    return {
        "protocol": "hysteria",
        "host": host,
        "port": port,
        "auth": params.get("auth", [""])[0],
        "peer": params.get("peer", [""])[0],
        "insecure": params.get("insecure", ["0"])[0] == "1",
        "alpn": params.get("alpn", [""])[0],
        "obfs": params.get("obfs", [""])[0],
        "protocol_version": params.get("protocol", [""])[0]
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