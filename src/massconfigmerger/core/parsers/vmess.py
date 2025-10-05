from __future__ import annotations

import base64
import binascii
import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .common import sanitize_headers, sanitize_str


def parse(config: str, idx: int) -> Optional[Dict[str, Any]]:
    """
    Parse a VMess configuration link.

    Args:
        config: The VMess configuration link.
        idx: The index of the configuration, used for default naming.

    Returns:
        A dictionary representing the Clash proxy, or None if parsing fails.
    """
    name = f"vmess-{idx}"
    after = config.split("://", 1)[1]
    base = after.split("#", 1)[0]
    try:
        # Primary parsing method: base64-encoded JSON
        padded = base + "=" * (-len(base) % 4)
        data = json.loads(base64.b64decode(padded).decode())
        name = sanitize_str(data.get("ps") or data.get("name") or name)
        proxy = {
            "name": name,
            "type": "vmess",
            "server": sanitize_str(data.get("add") or data.get("host", "")),
            "port": int(data.get("port", 0)),
            "uuid": sanitize_str(data.get("id") or data.get("uuid", "")),
            "alterId": int(data.get("aid", 0)),
            "cipher": sanitize_str(data.get("type", "auto")),
        }
        if data.get("tls") or data.get("security"):
            proxy["tls"] = True
        net = sanitize_str(data.get("net") or data.get("type"))
        if net in ("ws", "grpc"):
            proxy["network"] = net

        for key in ("host", "path", "sni", "alpn", "fp", "flow", "serviceName"):
            if data.get(key):
                proxy[key] = sanitize_str(data.get(key))

        if data.get("ws-headers"):
            proxy["ws-headers"] = sanitize_headers(data.get("ws-headers"))

        ws_opts = data.get("ws-opts")
        if ws_opts and isinstance(ws_opts, dict) and ws_opts.get("headers"):
            proxy["ws-headers"] = sanitize_headers(ws_opts.get("headers"))

        return proxy
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        # Fallback parsing method: URL-based
        logging.debug("Fallback Clash parse for vmess: %s", config)
        p = urlparse(config)
        q = parse_qs(p.query)
        security = q.get("security")
        proxy = {
            "name": sanitize_str(p.fragment or name),
            "type": "vmess",
            "server": sanitize_str(p.hostname or ""),
            "port": p.port or 0,
            "uuid": sanitize_str(p.username or ""),
            "alterId": int(q.get("aid", [0])[0]),
            "cipher": sanitize_str(q.get("type", ["auto"])[0]),
        }
        if security:
            proxy["tls"] = True
        net = q.get("type") or q.get("mode")
        if net:
            proxy["network"] = sanitize_str(net[0])
        for key in ("host", "path", "sni", "alpn", "fp", "flow", "serviceName"):
            if key in q:
                proxy[key] = sanitize_str(q[key][0])
        if "ws-headers" in q:
            proxy["ws-headers"] = sanitize_headers(q["ws-headers"][0])
        return proxy
