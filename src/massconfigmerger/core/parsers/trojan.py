from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .common import sanitize_headers, sanitize_str


def parse(config: str, idx: int) -> Optional[Dict[str, Any]]:
    """
    Parse a Trojan configuration link.

    Args:
        config: The Trojan configuration link.
        idx: The index of the configuration, used for default naming.

    Returns:
        A dictionary representing the Clash proxy, or None if parsing fails.
    """
    p = urlparse(config)
    q = parse_qs(p.query)
    name = sanitize_str(p.fragment or f"trojan-{idx}")
    proxy = {
        "name": name,
        "type": "trojan",
        "server": sanitize_str(p.hostname or ""),
        "port": p.port or 0,
        "password": sanitize_str(p.username or p.password or ""),
    }
    if q.get("sni"):
        proxy["sni"] = sanitize_str(q.get("sni")[0])
    if q.get("security"):
        proxy["tls"] = True
    net = q.get("type") or q.get("mode")
    if net:
        proxy["network"] = sanitize_str(net[0])
    for key in ("host", "path", "alpn", "flow", "serviceName"):
        if key in q:
            proxy[key] = sanitize_str(q[key][0])

    if "ws-headers" in q:
        proxy["ws-headers"] = sanitize_headers(q["ws-headers"][0])
    return proxy
