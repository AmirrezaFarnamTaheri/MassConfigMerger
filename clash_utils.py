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
                net = data.get("net") or data.get("type")
                if net in ("ws", "grpc"):
                    proxy["network"] = net
                if data.get("host"):
                    proxy["host"] = data.get("host")
                if data.get("path"):
                    proxy["path"] = data.get("path")
                if data.get("sni"):
                    proxy["sni"] = data.get("sni")
                if data.get("fp"):
                    proxy["fp"] = data.get("fp")
                if data.get("flow"):
                    proxy["flow"] = data.get("flow")
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
                net = q.get("type") or q.get("mode")
                if net:
                    proxy["network"] = net[0]
                for key in ("host", "path", "sni", "fp", "flow"):
                    if key in q:
                        proxy[key] = q[key][0]
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
            net = q.get("type") or q.get("mode")
            if net:
                proxy["network"] = net[0]
            for key in ("host", "path", "sni", "fp", "flow"):
                if key in q:
                    proxy[key] = q[key][0]
            return proxy
        elif scheme == "reality":
            p = urlparse(config)
            q = parse_qs(p.query)
            proxy = {
                "name": p.fragment or name,
                "type": "vless",
                "server": p.hostname or "",
                "port": p.port or 0,
                "uuid": p.username or "",
                "encryption": q.get("encryption", ["none"])[0],
                "tls": True,
            }
            for key in ("sni", "fp", "pbk", "sid"):
                if key in q:
                    proxy[key] = q[key][0]
            flows = q.get("flow")
            if flows:
                proxy["flow"] = flows[0]
            net = q.get("type") or q.get("mode")
            if net:
                proxy["network"] = net[0]
            for key in ("host", "path"):
                if key in q:
                    proxy[key] = q[key][0]
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
                main, _, tail = decoded.partition("/")
                parts = main.split(":")
                if len(parts) < 6:
                    return None
                server, port, proto, method, obfs, pwd_enc = parts[:6]
                try:
                    password = base64.urlsafe_b64decode(
                        pwd_enc + "=" * (-len(pwd_enc) % 4)
                    ).decode()
                except (binascii.Error, UnicodeDecodeError):
                    password = pwd_enc
                q = parse_qs(tail[1:]) if tail.startswith("?") else {}
                proxy = {
                    "name": name,
                    "type": "ssr",
                    "server": server,
                    "port": int(port),
                    "cipher": method,
                    "password": password,
                    "protocol": proto,
                    "obfs": obfs,
                }
                if "obfsparam" in q:
                    try:
                        proxy["obfs-param"] = base64.urlsafe_b64decode(
                            q["obfsparam"][0] + "=" * (-len(q["obfsparam"][0]) % 4)
                        ).decode()
                    except (binascii.Error, UnicodeDecodeError):
                        proxy["obfs-param"] = q["obfsparam"][0]
                if "protoparam" in q:
                    try:
                        proxy["protocol-param"] = base64.urlsafe_b64decode(
                            q["protoparam"][0] + "=" * (-len(q["protoparam"][0]) % 4)
                        ).decode()
                    except (binascii.Error, UnicodeDecodeError):
                        proxy["protocol-param"] = q["protoparam"][0]
                if "remarks" in q:
                    try:
                        proxy["name"] = base64.urlsafe_b64decode(
                            q["remarks"][0] + "=" * (-len(q["remarks"][0]) % 4)
                        ).decode()
                    except (binascii.Error, UnicodeDecodeError):
                        proxy["name"] = q["remarks"][0]
                if "group" in q:
                    try:
                        proxy["group"] = base64.urlsafe_b64decode(
                            q["group"][0] + "=" * (-len(q["group"][0]) % 4)
                        ).decode()
                    except (binascii.Error, UnicodeDecodeError):
                        proxy["group"] = q["group"][0]
                return proxy
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
        elif scheme in ("hy2", "hysteria2", "hysteria"):
            p = urlparse(config)
            if not p.hostname or not p.port:
                return None
            q = parse_qs(p.query)
            proxy = {
                "name": p.fragment or name,
                "type": "hysteria2" if scheme in ("hy2", "hysteria2") else "hysteria",
                "server": p.hostname,
                "port": p.port,
            }
            if p.username and not p.password:
                proxy["password"] = p.username
            if p.password:
                proxy["password"] = p.password
            for key in (
                "auth",
                "password",
                "peer",
                "sni",
                "insecure",
                "alpn",
                "obfs",
                "obfs-password",
            ):
                if key in q and key not in proxy:
                    proxy[key.replace("-", "_")] = q[key][0]
            return proxy
        elif scheme == "tuic":
            p = urlparse(config)
            if not p.hostname or not p.port:
                return None
            q = parse_qs(p.query)
            proxy = {
                "name": p.fragment or name,
                "type": "tuic",
                "server": p.hostname,
                "port": p.port,
            }
            if p.username:
                proxy["uuid"] = p.username
            if p.password:
                proxy["password"] = p.password
            for key in ("alpn", "congestion-control", "udp-relay-mode"):
                if key in q:
                    proxy[key] = q[key][0]
            return proxy
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
