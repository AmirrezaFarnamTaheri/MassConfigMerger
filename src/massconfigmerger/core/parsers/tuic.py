from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .common import sanitize_str


def parse(config: str, idx: int) -> Optional[Dict[str, Any]]:
    """
    Parse a TUIC configuration link.

    Args:
        config: The TUIC configuration link.
        idx: The index of the configuration, used for default naming.

    Returns:
        A dictionary representing the Clash proxy, or None if parsing fails.
    """
    p = urlparse(config)
    name = sanitize_str(p.fragment or f"tuic-{idx}")
    if not p.hostname or not p.port:
        return None

    q = parse_qs(p.query)
    proxy = {
        "name": name,
        "type": "tuic",
        "server": sanitize_str(p.hostname),
        "port": p.port,
    }
    uuid = sanitize_str(p.username or q.get("uuid", [None])[0])
    passwd = sanitize_str(p.password or q.get("password", [None])[0])
    if uuid:
        proxy["uuid"] = uuid
    if passwd:
        proxy["password"] = passwd

    key_map = {
        "alpn": ["alpn"],
        "congestion-control": ["congestion-control", "congestion_control"],
        "udp-relay-mode": ["udp-relay-mode", "udp_relay_mode"],
    }
    for out_key, keys in key_map.items():
        for k in keys:
            if k in q:
                proxy[out_key] = sanitize_str(q[k][0])
                break
    return proxy
