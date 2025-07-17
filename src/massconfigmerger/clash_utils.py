from __future__ import annotations

import base64
import binascii
import json
import logging
from urllib.parse import parse_qs, urlparse
from typing import Any, Dict, List, Optional, Union

import yaml


def config_to_clash_proxy(
    config: str,
    idx: int = 0,
    protocol: Optional[str] = None,
) -> Optional[Dict[str, Union[str, int, bool]]]:
    """Convert a single config link to a Clash proxy dictionary.

    Supported protocols include ``vmess``, ``vless``/``reality``, ``trojan``,
    ``ss``/``ssr``, ``hysteria``/``hysteria2`` and several fallbacks such as plain
    ``socks`` or ``http``.  Each parser attempts to extract every optional argument
    used by real-world sharing links.

    Parsed options by protocol (when available):

    ``vmess``
        ``network`` (``ws`` or ``grpc``), ``host``, ``path``, ``sni``, ``alpn``,
        ``fp``, ``flow``, ``serviceName`` and ``ws-headers``.
    ``vless``/``reality``
        ``encryption``, ``network``, ``host``, ``path``, ``sni``, ``alpn``,
        ``fp``, ``flow``, ``pbk``, ``sid``, ``serviceName``, ``ws-headers`` and
        ``reality-opts``.
    ``trojan``
        ``network`` (``ws``/``grpc``), ``host``, ``path``, ``sni``, ``alpn``,
        ``flow``, ``serviceName`` and ``ws-headers``.
    ``ssr``
        ``protocol``, ``obfs``, ``cipher``, ``password``, ``obfs-param``,
        ``protocol-param``, ``remarks``, ``group``, ``udpport`` and ``uot``.
    ``hysteria2``
        ``auth``, ``password``, ``peer``, ``sni``, ``insecure``, ``alpn``, ``obfs``,
        ``obfs-password``, ``upmbps`` and ``downmbps``.

        Unknown or malformed links result in ``None`` instead of raising an exception.
    """
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
                if data.get("ws-headers"):
                    try:
                        proxy["ws-headers"] = json.loads(data["ws-headers"])
                    except (json.JSONDecodeError, TypeError):
                        proxy["ws-headers"] = data["ws-headers"]
                ws_opts = data.get("ws-opts")
                if ws_opts and isinstance(ws_opts, dict) and ws_opts.get("headers"):
                    proxy["ws-headers"] = ws_opts.get("headers")
                if data.get("serviceName"):
                    proxy["serviceName"] = data.get("serviceName")
                if data.get("sni"):
                    proxy["sni"] = data.get("sni")
                if data.get("alpn"):
                    proxy["alpn"] = data.get("alpn")
                if data.get("fp"):
                    proxy["fp"] = data.get("fp")
                if data.get("flow"):
                    proxy["flow"] = data.get("flow")
                return proxy
            except (
                binascii.Error,
                UnicodeDecodeError,
                json.JSONDecodeError,
                ValueError,
            ) as exc:
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
                for key in ("host", "path", "sni", "alpn", "fp", "flow", "serviceName"):
                    if key in q:
                        proxy[key] = q[key][0]
                if "ws-headers" in q:
                    try:
                        padded = q["ws-headers"][0] + "=" * (
                            -len(q["ws-headers"][0]) % 4
                        )
                        proxy["ws-headers"] = json.loads(
                            base64.urlsafe_b64decode(padded)
                        )
                    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
                        proxy["ws-headers"] = q["ws-headers"][0]
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
            for key in ("host", "path", "sni", "alpn", "fp", "flow", "serviceName"):
                if key in q:
                    proxy[key] = q[key][0]
            pbk = (
                q.get("pbk")
                or q.get("public-key")
                or q.get("publicKey")
                or q.get("public_key")
                or q.get("publickey")
            )
            sid = (
                q.get("sid")
                or q.get("short-id")
                or q.get("shortId")
                or q.get("short_id")
                or q.get("shortid")
            )
            spider = q.get("spiderX") or q.get("spider-x") or q.get("spider_x")
            if pbk:
                proxy["pbk"] = pbk[0]
            if sid:
                proxy["sid"] = sid[0]
            if spider:
                proxy["spiderX"] = spider[0]
            reality_opts = {}
            if pbk:
                reality_opts["public-key"] = pbk[0]
            if sid:
                reality_opts["short-id"] = sid[0]
            if spider:
                reality_opts["spider-x"] = spider[0]
            if reality_opts:
                proxy["reality-opts"] = reality_opts
            if "ws-headers" in q:
                try:
                    padded = q["ws-headers"][0] + "=" * (-len(q["ws-headers"][0]) % 4)
                    proxy["ws-headers"] = json.loads(base64.urlsafe_b64decode(padded))
                except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
                    proxy["ws-headers"] = q["ws-headers"][0]
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
            for key in ("sni", "alpn", "fp", "serviceName"):
                if key in q:
                    proxy[key] = q[key][0]
            pbk = (
                q.get("pbk")
                or q.get("public-key")
                or q.get("publicKey")
                or q.get("public_key")
                or q.get("publickey")
            )
            sid = (
                q.get("sid")
                or q.get("short-id")
                or q.get("shortId")
                or q.get("short_id")
                or q.get("shortid")
            )
            spider = q.get("spiderX") or q.get("spider-x") or q.get("spider_x")
            if pbk:
                proxy["pbk"] = pbk[0]
            if sid:
                proxy["sid"] = sid[0]
            if spider:
                proxy["spiderX"] = spider[0]
            if "ws-headers" in q:
                try:
                    padded = q["ws-headers"][0] + "=" * (-len(q["ws-headers"][0]) % 4)
                    proxy["ws-headers"] = json.loads(base64.urlsafe_b64decode(padded))
                except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
                    proxy["ws-headers"] = q["ws-headers"][0]
            flows = q.get("flow")
            if flows:
                proxy["flow"] = flows[0]
            reality_opts = {}
            if pbk:
                reality_opts["public-key"] = pbk[0]
            if sid:
                reality_opts["short-id"] = sid[0]
            if spider:
                reality_opts["spider-x"] = spider[0]
            if reality_opts:
                proxy["reality-opts"] = reality_opts
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
            net = q.get("type") or q.get("mode")
            if net:
                proxy["network"] = net[0]
            for key in ("host", "path", "alpn", "flow", "serviceName"):
                if key in q:
                    proxy[key] = q[key][0]
            if "ws-headers" in q:
                try:
                    padded = q["ws-headers"][0] + "=" * (-len(q["ws-headers"][0]) % 4)
                    proxy["ws-headers"] = json.loads(base64.urlsafe_b64decode(padded))
                except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
                    proxy["ws-headers"] = q["ws-headers"][0]
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
                server, port_str, proto, method, obfs, pwd_enc = parts[:6]
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
                    "port": int(port_str),
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
                if "udpport" in q:
                    try:
                        proxy["udpport"] = int(q["udpport"][0])
                    except ValueError:
                        proxy["udpport"] = q["udpport"][0]
                if "uot" in q:
                    proxy["uot"] = q["uot"][0]
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
            passwd = p.password or q.get("password", [None])[0]
            if p.username and not passwd:
                passwd = p.username
            if passwd:
                proxy["password"] = passwd
            for key in (
                "auth",
                "peer",
                "sni",
                "insecure",
                "alpn",
                "obfs",
                "obfs-password",
            ):
                if key in q:
                    proxy[key.replace("-", "_")] = q[key][0]
            up_keys = ["upmbps", "up", "up_mbps"]
            down_keys = ["downmbps", "down", "down_mbps"]
            for k in up_keys:
                if k in q:
                    proxy["upmbps"] = q[k][0]
                    break
            for k in down_keys:
                if k in q:
                    proxy["downmbps"] = q[k][0]
                    break
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
            uuid = p.username or q.get("uuid", [None])[0]
            passwd = p.password or q.get("password", [None])[0]
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
                        proxy[out_key] = q[k][0]
                        break
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
    except (
        ValueError,
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        logging.debug("config_to_clash_proxy failed: %s", exc)
        return None


def flag_emoji(country: Optional[str]) -> str:
    """Return flag emoji for a 2-letter country code."""
    if not country or len(country) != 2:
        return "🏳"
    offset = 127397
    return chr(ord(country[0].upper()) + offset) + chr(ord(country[1].upper()) + offset)


def build_clash_config(proxies: List[Dict[str, Any]]) -> str:
    """Return a Clash YAML config with default groups and rule."""
    if not proxies:
        return ""

    names = [p["name"] for p in proxies]
    auto_select = "⚡ Auto-Select"
    manual = "🔰 MANUAL"
    groups = [
        {
            "name": auto_select,
            "type": "url-test",
            "proxies": names,
            "url": "http://www.gstatic.com/generate_204",
            "interval": 300,
        },
        {"name": manual, "type": "select", "proxies": [auto_select, *names]},
    ]
    rules = [f"MATCH,{manual}"]
    return yaml.safe_dump(
        {"proxies": proxies, "proxy-groups": groups, "rules": rules},
        allow_unicode=True,
        sort_keys=False,
    )
