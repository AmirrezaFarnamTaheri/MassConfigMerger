from __future__ import annotations

import base64
import binascii
import json
import logging
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from .common import BaseParser
from ...exceptions import ParserError


class VmessParser(BaseParser):
    """
    Parses a VMess configuration link.
    """

    def __init__(self, config_uri: str, idx: int):
        super().__init__(config_uri)
        self.idx = idx

    def parse(self) -> Dict[str, Any]:
        """
        Parse the VMess configuration link.

        Returns:
            A dictionary representing the Clash proxy.
        Raises:
            ParserError: If parsing fails.
        """
        name = f"vmess-{self.idx}"
        after = self.config_uri.split("://", 1)[1]
        base = after.split("#", 1)[0]
        try:
            # Primary parsing method: base64-encoded JSON
            padded = base + "=" * (-len(base) % 4)
            data = json.loads(base64.b64decode(padded).decode())
            name = self.sanitize_str(data.get("ps") or data.get("name") or name)
            proxy = {
                "name": name,
                "type": "vmess",
                "server": self.sanitize_str(data.get("add") or data.get("host", "")),
                "port": int(data.get("port", 0)),
                "uuid": self.sanitize_str(data.get("id") or data.get("uuid", "")),
                "alterId": int(data.get("aid", 0)),
                "cipher": self.sanitize_str(data.get("type", "auto")),
            }
            if data.get("tls") or data.get("security"):
                proxy["tls"] = True
            net = self.sanitize_str(data.get("net") or data.get("type"))
            if net in ("ws", "grpc"):
                proxy["network"] = net

            for key in ("host", "path", "sni", "alpn", "fp", "flow", "serviceName"):
                if data.get(key):
                    proxy[key] = self.sanitize_str(data.get(key))

            if data.get("ws-headers"):
                proxy["ws-headers"] = self.sanitize_headers(data.get("ws-headers"))

            ws_opts = data.get("ws-opts")
            if ws_opts and isinstance(ws_opts, dict) and ws_opts.get("headers"):
                proxy["ws-headers"] = self.sanitize_headers(ws_opts.get("headers"))

            return proxy
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError) as e1:
            # Fallback parsing method: URL-based
            logging.debug("Fallback Clash parse for vmess: %s", self.config_uri)
            try:
                p = urlparse(self.config_uri)
                q = parse_qs(p.query)
                security = q.get("security")
                proxy = {
                    "name": self.sanitize_str(p.fragment or name),
                    "type": "vmess",
                    "server": self.sanitize_str(p.hostname or ""),
                    "port": p.port or 0,
                    "uuid": self.sanitize_str(p.username or ""),
                    "alterId": int(q.get("aid", [0])[0]),
                    "cipher": self.sanitize_str(q.get("type", ["auto"])[0]),
                }
                if security:
                    proxy["tls"] = True
                net = q.get("type") or q.get("mode")
                if net:
                    proxy["network"] = self.sanitize_str(net[0])
                for key in ("host", "path", "sni", "alpn", "fp", "flow", "serviceName"):
                    if key in q:
                        proxy[key] = self.sanitize_str(q[key][0])
                if "ws-headers" in q:
                    proxy["ws-headers"] = self.sanitize_headers(q["ws-headers"][0])
                return proxy
            except Exception as e2:
                raise ParserError(f"Failed to parse vmess link: {self.config_uri}") from e2

    def get_identifier(self) -> Optional[str]:
        """
        Get the identifier (UUID) for the VMess configuration.
        """
        try:
            after = self.config_uri.split("://", 1)[1]
            base = after.split("#", 1)[0]
            padded = base + "=" * (-len(base) % 4)
            data = json.loads(base64.b64decode(padded).decode())
            return self.sanitize_str(data.get("id") or data.get("uuid"))
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            p = urlparse(self.config_uri)
            return self.sanitize_str(p.username or "")