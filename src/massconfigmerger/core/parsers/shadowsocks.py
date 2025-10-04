from __future__ import annotations

import base64
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .common import sanitize_str


def parse(config: str, idx: int) -> Optional[Dict[str, Any]]:
    """
    Parse a Shadowsocks (SS) configuration link.

    Args:
        config: The Shadowsocks configuration link.
        idx: The index of the configuration, used for default naming.

    Returns:
        A dictionary representing the Clash proxy, or None if parsing fails.
    """
    p = urlparse(config)
    name = sanitize_str(p.fragment or f"ss-{idx}")

    server = None
    port = None
    method = None
    password = None

    # Try parsing userinfo first (e.g., ss://method:pass@host:port)
    # This requires 'ss' to be registered as a scheme with a netloc.
    # While not standard, some clients generate these links.
    if p.username and p.password and p.hostname and p.port:
        method = sanitize_str(p.username)
        password = sanitize_str(p.password)
        server = sanitize_str(p.hostname)
        port = p.port
    else:
        # Fallback to base64 decoding
        try:
            base = config.split("://", 1)[1].split("#", 1)[0]
            padded = base + "=" * (-len(base) % 4)
            decoded = base64.b64decode(padded).decode()
            before_at, host_port = decoded.split("@")
            method_raw, password_raw = before_at.split(":")
            server_str, port_str = host_port.split(":")

            method = sanitize_str(method_raw)
            password = sanitize_str(password_raw)
            server = sanitize_str(server_str)
            port = int(port_str)
        except (ValueError, IndexError):
            return None # Invalid format

    if not all([server, port, method, password]):
        return None

    return {
        "name": name,
        "type": "ss",
        "server": server,
        "port": int(port),
        "cipher": method,
        "password": password,
    }