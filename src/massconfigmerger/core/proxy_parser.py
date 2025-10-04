from __future__ import annotations

import base64
import binascii
import json
import logging
from urllib.parse import parse_qs, urlparse
from typing import Any, Dict, List, Optional, Union

class ProxyParser:
    """A class to parse different proxy protocols from their config links."""

    def _sanitize_str(self, value: Any) -> Any:
        """Strip whitespace and remove newlines from string values."""
        if isinstance(value, str):
            return value.strip().replace("\n", "").replace("\r", "")
        return value

    def _sanitize_headers(self, headers_data: Any) -> Any:
        """Sanitize ws-headers, which can be a dict, a JSON string, or a base64-encoded JSON string."""
        if not headers_data:
            return None

        headers = headers_data
        if isinstance(headers_data, str):
            try:
                # Attempt to decode from base64, then parse JSON
                padded = headers_data + "=" * (-len(headers_data) % 4)
                decoded_json = base64.urlsafe_b64decode(padded).decode()
                headers = json.loads(decoded_json)
            except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
                try:
                    # If not base64, maybe it's a plain JSON string
                    headers = json.loads(headers_data)
                except (json.JSONDecodeError, TypeError):
                    # Otherwise, treat as a plain string
                    pass

        if isinstance(headers, dict):
            return {
                self._sanitize_str(k): self._sanitize_str(v)
                for k, v in headers.items()
            }

        return self._sanitize_str(headers)

    def __init__(self):
        self.parsers = {
            "vmess": self._parse_vmess,
            "vless": self._parse_vless,
            "reality": self._parse_reality,
            "trojan": self._parse_trojan,
            "ss": self._parse_ss,
            "shadowsocks": self._parse_ss,
            "ssr": self._parse_ssr,
            "shadowsocksr": self._parse_ssr,
            "naive": self._parse_naive,
            "hy2": self._parse_hysteria,
            "hysteria2": self._parse_hysteria,
            "hysteria": self._parse_hysteria,
            "tuic": self._parse_tuic,
        }

    def config_to_clash_proxy(
        self,
        config: str,
        idx: int = 0,
        protocol: Optional[str] = None,
    ) -> Optional[Dict[str, Union[str, int, bool]]]:
        """Convert a single config link to a Clash proxy dictionary."""
        try:
            scheme = (protocol or config.split("://", 1)[0]).lower()
            parser = self.parsers.get(scheme)
            if parser:
                return parser(config, idx, scheme)
            else:
                return self._parse_fallback(config, idx, scheme)
        except (
            ValueError,
            binascii.Error,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            logging.debug("config_to_clash_proxy failed: %s", exc)
            return None

    def _parse_vmess(self, config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
        name = f"{scheme}-{idx}"
        after = config.split("://", 1)[1]
        base = after.split("#", 1)[0]
        try:
            padded = base + "=" * (-len(base) % 4)
            data = json.loads(base64.b64decode(padded).decode())
            name = self._sanitize_str(data.get("ps") or data.get("name") or name)
            proxy = {
                "name": name,
                "type": "vmess",
                "server": self._sanitize_str(data.get("add") or data.get("host", "")),
                "port": int(data.get("port", 0)),
                "uuid": self._sanitize_str(data.get("id") or data.get("uuid", "")),
                "alterId": int(data.get("aid", 0)),
                "cipher": self._sanitize_str(data.get("type", "auto")),
            }
            if data.get("tls") or data.get("security"):
                proxy["tls"] = True
            net = self._sanitize_str(data.get("net") or data.get("type"))
            if net in ("ws", "grpc"):
                proxy["network"] = net

            for key in ("host", "path", "sni", "alpn", "fp", "flow", "serviceName"):
                if data.get(key):
                    proxy[key] = self._sanitize_str(data.get(key))

            if data.get("ws-headers"):
                proxy["ws-headers"] = self._sanitize_headers(data.get("ws-headers"))

            ws_opts = data.get("ws-opts")
            if ws_opts and isinstance(ws_opts, dict) and ws_opts.get("headers"):
                proxy["ws-headers"] = self._sanitize_headers(ws_opts.get("headers"))

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
                "name": self._sanitize_str(p.fragment or name),
                "type": "vmess",
                "server": self._sanitize_str(p.hostname or ""),
                "port": p.port or 0,
                "uuid": self._sanitize_str(p.username or ""),
                "alterId": int(q.get("aid", [0])[0]),
                "cipher": self._sanitize_str(q.get("type", ["auto"])[0]),
            }
            if security:
                proxy["tls"] = True
            net = q.get("type") or q.get("mode")
            if net:
                proxy["network"] = self._sanitize_str(net[0])
            for key in ("host", "path", "sni", "alpn", "fp", "flow", "serviceName"):
                if key in q:
                    proxy[key] = self._sanitize_str(q[key][0])
            if "ws-headers" in q:
                proxy["ws-headers"] = self._sanitize_headers(q["ws-headers"][0])
            return proxy

    def _parse_vless(self, config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
        p = urlparse(config)
        q = parse_qs(p.query)
        name = self._sanitize_str(p.fragment or f"{scheme}-{idx}")
        security = q.get("security")
        proxy = {
            "name": name,
            "type": "vless",
            "server": self._sanitize_str(p.hostname or ""),
            "port": p.port or 0,
            "uuid": self._sanitize_str(p.username or ""),
            "encryption": self._sanitize_str(q.get("encryption", ["none"])[0]),
        }
        if security:
            proxy["tls"] = True
        net = q.get("type") or q.get("mode")
        if net:
            proxy["network"] = self._sanitize_str(net[0])
        for key in ("host", "path", "sni", "alpn", "fp", "flow", "serviceName"):
            if key in q:
                proxy[key] = self._sanitize_str(q[key][0])

        pbk_q = q.get("pbk") or q.get("public-key") or q.get("publicKey") or q.get("public_key") or q.get("publickey")
        sid_q = q.get("sid") or q.get("short-id") or q.get("shortId") or q.get("short_id") or q.get("shortid")
        spider_q = q.get("spiderX") or q.get("spider-x") or q.get("spider_x")

        pbk = self._sanitize_str(pbk_q[0]) if pbk_q else None
        sid = self._sanitize_str(sid_q[0]) if sid_q else None
        spider = self._sanitize_str(spider_q[0]) if spider_q else None

        if pbk: proxy["pbk"] = pbk
        if sid: proxy["sid"] = sid
        if spider: proxy["spiderX"] = spider

        reality_opts = {}
        if pbk: reality_opts["public-key"] = pbk
        if sid: reality_opts["short-id"] = sid
        if spider: reality_opts["spider-x"] = spider
        if reality_opts: proxy["reality-opts"] = reality_opts

        if "ws-headers" in q:
            proxy["ws-headers"] = self._sanitize_headers(q["ws-headers"][0])
        return proxy

    def _parse_reality(self, config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
        p = urlparse(config)
        q = parse_qs(p.query)
        name = self._sanitize_str(p.fragment or f"{scheme}-{idx}")
        proxy = {
            "name": name,
            "type": "vless",
            "server": self._sanitize_str(p.hostname or ""),
            "port": p.port or 0,
            "uuid": self._sanitize_str(p.username or ""),
            "encryption": self._sanitize_str(q.get("encryption", ["none"])[0]),
            "tls": True,
        }
        for key in ("sni", "alpn", "fp", "serviceName", "flow", "host", "path"):
            if key in q:
                proxy[key] = self._sanitize_str(q[key][0])

        pbk_q = q.get("pbk") or q.get("public-key") or q.get("publicKey") or q.get("public_key") or q.get("publickey")
        sid_q = q.get("sid") or q.get("short-id") or q.get("shortId") or q.get("short_id") or q.get("shortid")
        spider_q = q.get("spiderX") or q.get("spider-x") or q.get("spider_x")

        pbk = self._sanitize_str(pbk_q[0]) if pbk_q else None
        sid = self._sanitize_str(sid_q[0]) if sid_q else None
        spider = self._sanitize_str(spider_q[0]) if spider_q else None

        if pbk: proxy["pbk"] = pbk
        if sid: proxy["sid"] = sid
        if spider: proxy["spiderX"] = spider

        reality_opts = {}
        if pbk: reality_opts["public-key"] = pbk
        if sid: reality_opts["short-id"] = sid
        if spider: reality_opts["spider-x"] = spider
        if reality_opts: proxy["reality-opts"] = reality_opts

        net = q.get("type") or q.get("mode")
        if net:
            proxy["network"] = self._sanitize_str(net[0])

        if "ws-headers" in q:
            proxy["ws-headers"] = self._sanitize_headers(q["ws-headers"][0])
        return proxy

    def _parse_trojan(self, config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
        p = urlparse(config)
        q = parse_qs(p.query)
        name = self._sanitize_str(p.fragment or f"{scheme}-{idx}")
        proxy = {
            "name": name,
            "type": "trojan",
            "server": self._sanitize_str(p.hostname or ""),
            "port": p.port or 0,
            "password": self._sanitize_str(p.username or p.password or ""),
        }
        if q.get("sni"):
            proxy["sni"] = self._sanitize_str(q.get("sni")[0])
        if q.get("security"):
            proxy["tls"] = True
        net = q.get("type") or q.get("mode")
        if net:
            proxy["network"] = self._sanitize_str(net[0])
        for key in ("host", "path", "alpn", "flow", "serviceName"):
            if key in q:
                proxy[key] = self._sanitize_str(q[key][0])

        if "ws-headers" in q:
            proxy["ws-headers"] = self._sanitize_headers(q["ws-headers"][0])
        return proxy

    def _parse_ss(self, config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
        p = urlparse(config)
        name = self._sanitize_str(p.fragment or f"{scheme}-{idx}")
        if p.username and p.password and p.hostname and p.port:
            method = self._sanitize_str(p.username)
            password = self._sanitize_str(p.password)
            server = self._sanitize_str(p.hostname)
            port = p.port
        else:
            base = config.split("://", 1)[1].split("#", 1)[0]
            padded = base + "=" * (-len(base) % 4)
            decoded = base64.b64decode(padded).decode()
            before_at, host_port = decoded.split("@")
            method_raw, password_raw = before_at.split(":")
            server_str, port_str = host_port.split(":")
            method = self._sanitize_str(method_raw)
            password = self._sanitize_str(password_raw)
            server = self._sanitize_str(server_str)
            port = int(port_str)
        return {
            "name": name,
            "type": "ss",
            "server": server,
            "port": int(port),
            "cipher": method,
            "password": password,
        }

    def _parse_ssr(self, config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
        base = config.split("://", 1)[1].split("#", 1)[0]
        name = f"{scheme}-{idx}"
        try:
            padded = base + "=" * (-len(base) % 4)
            decoded = base64.urlsafe_b64decode(padded).decode()
            main, _, tail = decoded.partition("/")
            parts = main.split(":")
            if len(parts) < 6: return None
            server, port_str, proto, method, obfs, pwd_enc = parts[:6]

            try:
                password_decoded = base64.urlsafe_b64decode(pwd_enc + "=" * (-len(pwd_enc) % 4)).decode()
                password = self._sanitize_str(password_decoded)
            except (binascii.Error, UnicodeDecodeError):
                password = self._sanitize_str(pwd_enc)

            q = parse_qs(tail[1:]) if tail.startswith("?") else {}
            proxy = {
                "name": name,
                "type": "ssr",
                "server": self._sanitize_str(server),
                "port": int(port_str),
                "cipher": self._sanitize_str(method),
                "password": password,
                "protocol": self._sanitize_str(proto),
                "obfs": self._sanitize_str(obfs),
            }

            for param, key in [("obfsparam", "obfs-param"), ("protoparam", "protocol-param"), ("remarks", "name"), ("group", "group")]:
                if param in q:
                    try:
                        val = base64.urlsafe_b64decode(q[param][0] + "=" * (-len(q[param][0]) % 4)).decode()
                    except (binascii.Error, UnicodeDecodeError):
                        val = q[param][0]
                    proxy[key] = self._sanitize_str(val)

            if "udpport" in q:
                try:
                    proxy["udpport"] = int(q["udpport"][0])
                except ValueError:
                    logging.debug("Could not parse udpport '%s' as integer.", q["udpport"][0])
            if "uot" in q:
                proxy["uot"] = self._sanitize_str(q["uot"][0])
            return proxy
        except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
            logging.debug("SSRs parse failed: %s", exc)
            return None

    def _parse_naive(self, config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
        p = urlparse(config)
        name = self._sanitize_str(p.fragment or f"{scheme}-{idx}")
        if not p.hostname or not p.port:
            return None
        return {
            "name": name,
            "type": "http",
            "server": self._sanitize_str(p.hostname),
            "port": p.port,
            "username": self._sanitize_str(p.username or ""),
            "password": self._sanitize_str(p.password or ""),
            "tls": True,
        }

    def _parse_hysteria(self, config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
        p = urlparse(config)
        name = self._sanitize_str(p.fragment or f"{scheme}-{idx}")
        if not p.hostname or not p.port:
            return None
        q = parse_qs(p.query)
        proxy = {
            "name": name,
            "type": "hysteria2" if scheme in ("hy2", "hysteria2") else "hysteria",
            "server": self._sanitize_str(p.hostname),
            "port": p.port,
        }
        passwd_q = q.get("password", [None])[0]
        passwd = self._sanitize_str(p.password or passwd_q)
        if p.username and not passwd:
            passwd = self._sanitize_str(p.username)
        if passwd:
            proxy["password"] = passwd

        for key in ("auth", "peer", "sni", "insecure", "alpn", "obfs", "obfs-password"):
            if key in q:
                proxy[key] = self._sanitize_str(q[key][0])

        up_keys = ["upmbps", "up", "up_mbps"]
        down_keys = ["downmbps", "down", "down_mbps"]
        for k in up_keys:
            if k in q:
                proxy["upmbps"] = self._sanitize_str(q[k][0])
                break
        for k in down_keys:
            if k in q:
                proxy["downmbps"] = self._sanitize_str(q[k][0])
                break
        return proxy

    def _parse_tuic(self, config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
        p = urlparse(config)
        name = self._sanitize_str(p.fragment or f"{scheme}-{idx}")
        if not p.hostname or not p.port:
            return None
        q = parse_qs(p.query)
        proxy = {
            "name": name,
            "type": "tuic",
            "server": self._sanitize_str(p.hostname),
            "port": p.port,
        }
        uuid = self._sanitize_str(p.username or q.get("uuid", [None])[0])
        passwd = self._sanitize_str(p.password or q.get("password", [None])[0])
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
                    proxy[out_key] = self._sanitize_str(q[k][0])
                    break
        return proxy

    def _parse_fallback(self, config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
        p = urlparse(config)
        name = self._sanitize_str(p.fragment or f"{scheme}-{idx}")
        if not p.hostname or not p.port:
            return None
        typ = "socks5" if scheme.startswith("socks") else "http"
        return {
            "name": name,
            "type": typ,
            "server": self._sanitize_str(p.hostname),
            "port": p.port,
        }