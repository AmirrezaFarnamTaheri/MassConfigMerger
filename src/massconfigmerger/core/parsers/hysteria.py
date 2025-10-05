from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .common import sanitize_str


def parse(config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
    """
    Parse a Hysteria, Hy2, or Hysteria2 configuration link.

    Args:
        config: The Hysteria configuration link.
        idx: The index of the configuration, used for default naming.
        scheme: The protocol scheme (e.g., 'hysteria', 'hy2').

    Returns:
        A dictionary representing the Clash proxy, or None if parsing fails.
    """
    p = urlparse(config)
    name = sanitize_str(p.fragment or f"{scheme}-{idx}")
    if not p.hostname or not p.port:
        return None

    q = parse_qs(p.query)
    proxy = {
        "name": name,
        "type": "hysteria2" if scheme in ("hy2", "hysteria2") else "hysteria",
        "server": sanitize_str(p.hostname),
        "port": p.port,
    }
    passwd_q = q.get("password", [None])[0]
    passwd = sanitize_str(p.password or passwd_q)
    if p.username and not passwd:
        passwd = sanitize_str(p.username)
    if passwd:
        proxy["password"] = passwd

    for key in ("auth", "peer", "sni", "insecure", "alpn", "obfs", "obfs-password"):
        if key in q:
            proxy[key] = sanitize_str(q[key][0])

    up_keys = ["upmbps", "up", "up_mbps"]
    down_keys = ["downmbps", "down", "down_mbps"]
    for k in up_keys:
        if k in q:
            proxy["upmbps"] = sanitize_str(q[k][0])
            break
    for k in down_keys:
        if k in q:
            proxy["downmbps"] = sanitize_str(q[k][0])
            break
    return proxy
