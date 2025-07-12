from __future__ import annotations

import base64
import binascii
import json
import logging
from urllib.parse import parse_qs, urlparse
from typing import Dict, Optional, Union


def config_to_clash_proxy(
    config: str,
    idx: int = 0,
    protocol: Optional[str] = None,
) -> Optional[Dict[str, Union[str, int, bool]]]:
    """Convert a single config link to a Clash proxy dictionary."""
    try:
        q = {}
        scheme = (protocol or config.split("://", 1)[0]).lower()
        name = f"{scheme}-{idx}"
        if scheme == "vmess":
            after = config.split("://", 1)[1]
            base = after.split("#", 1)[0]
            try:
                padded = base + "=" * (-len(base) % 4)
                data = json.loads(base64.b64decode(padded).decode())
                name = data.get("ps") or data.get("name") or name
                proxy = {
                    "name": name,
                    "type": "vmess",
                    "server": data.get("add") or data.get("host", ""),
                    "port": int(data.get("port", 0)),
                    "uuid": data.get("id") or data.get("uuid", ""),
                    "alterId": int(data.get("aid", 0)),
                    "cipher": data.get("type", "auto"),
                }
                if data.get("tls") or data.get("security"):
                    proxy["tls"] = True
                return proxy
            except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                logging.debug("Fallback Clash parse for vmess: %s", exc)
                p = urlparse(config)
                q = parse_qs(p.query)
                security = q.get("security")
                proxy = {
                    "name": p.fragment or name,
                    "type": "vmess",
                    "server": p.hostname or "",
                    "port": p.port or 0,
                    "uuid": p.username or "",
                    "alterId": int(q.get("aid", [0])[0]),
                    "cipher": q.get("type", ["auto"])[0],
                }
                if security:
                    proxy["tls"] = True
                return proxy
        elif scheme == "vless":
            p = urlparse(config)
            q = parse_qs(p.query)
            security = q.get("security")
            proxy = {
                "name": p.fragment or name,
                "type": "vless",
                "server": p.hostname or "",
                "port": p.port or 0,
                "uuid": p.username or "",
                "encryption": q.get("encryption", ["none"])[0],
            }
            if security:
                proxy["tls"] = True
            return proxy
        elif scheme == "reality":
            p = urlparse(config)
            q = parse_qs(p.query)
            security = q.get("security")
            proxy = {
                "name": p.fragment or name,
                "type": "vless",
                "server": p.hostname or "",
                "port": p.port or 0,
                "uuid": p.username or "",
                "encryption": q.get("encryption", ["none"])[0],
                "tls": True,
            }
            flows = q.get("flow")
            if flows:
                proxy["flow"] = flows[0]
            return proxy
        elif scheme == "trojan":
            p = urlparse(config)
            q = parse_qs(p.query)
            security = q.get("security")
            proxy = {
                "name": p.fragment or name,
                "type": "trojan",
                "server": p.hostname or "",
                "port": p.port or 0,
                "password": p.username or p.password or "",
            }
            sni_vals = q.get("sni")
            if sni_vals:
                proxy["sni"] = sni_vals[0]
            if security:
                proxy["tls"] = True
            return proxy
        elif scheme in ("ss", "shadowsocks"):
            p = urlparse(config)
            if p.username and p.password and p.hostname and p.port:
                method = p.username
                password = p.password
                server = p.hostname
                port = p.port
            else:
                base = config.split("://", 1)[1].split("#", 1)[0]
                padded = base + "=" * (-len(base) % 4)
                decoded = base64.b64decode(padded).decode()
                before_at, host_port = decoded.split("@")
                method, password = before_at.split(":")
                server_str, port_str = host_port.split(":")
                server = server_str
                port = int(port_str)
            return {
                "name": p.fragment or name,
                "type": "ss",
                "server": server,
                "port": int(port),
                "cipher": method,
                "password": password,
            }
        elif scheme in ("ssr", "shadowsocksr"):
            base = config.split("://", 1)[1].split("#", 1)[0]
            try:
                padded = base + "=" * (-len(base) % 4)
                decoded = base64.urlsafe_b64decode(padded).decode()
                host_part = decoded.split("/", 1)[0]
                if ":" not in host_part:
                    return None
                server_str, port_str = host_part.split(":", 1)
                server = server_str
                port = int(port_str)
                return {
                    "name": name,
                    "type": "ssr",
                    "server": server,
                    "port": int(port),
                }
            except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
                logging.debug("SSRs parse failed: %s", exc)
                return None
        elif scheme == "naive":
            p = urlparse(config)
            if not p.hostname or not p.port:
                return None
            return {
                "name": p.fragment or name,
                "type": "http",
                "server": p.hostname,
                "port": p.port,
                "username": p.username or "",
                "password": p.password or "",
                "tls": True,
            }
        else:
            p = urlparse(config)
            if not p.hostname or not p.port:
                return None
            typ = "socks5" if scheme.startswith("socks") else "http"
            return {
                "name": p.fragment or name,
                "type": typ,
                "server": p.hostname,
                "port": p.port,
            }
    except (ValueError, binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        logging.debug("config_to_clash_proxy failed: %s", exc)
        return None
