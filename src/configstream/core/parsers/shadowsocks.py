from __future__ import annotations

import base64
import binascii
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs

from .common import BaseParser
from ...exceptions import ParserError


class ShadowsocksParser(BaseParser):
    """
    Parses a Shadowsocks (SS) configuration link.
    """

    def __init__(self, config_uri: str, idx: int):
        super().__init__(config_uri)
        self.idx = idx

    def parse(self) -> Dict[str, Any]:
        """
        Parse the Shadowsocks configuration link.

        Returns:
            A dictionary representing the Clash proxy.
        Raises:
            ParserError: If parsing fails.
        """
        p = urlparse(self.config_uri)
        name = self.sanitize_str(p.fragment or f"ss-{self.idx}")

        server = p.hostname
        port = p.port
        method = None
        password = None

        if p.username and p.password:
            method = self.sanitize_str(p.username)
            password = self.sanitize_str(p.password)
        elif p.username:
            try:
                userinfo_decoded = base64.b64decode(
                    p.username + "=" * (-len(p.username) % 4)
                ).decode()
                method, password = userinfo_decoded.split(":", 1)
                method = self.sanitize_str(method)
                password = self.sanitize_str(password)
            except (ValueError, IndexError, binascii.Error, UnicodeDecodeError) as e:
                raise ParserError(
                    f"Invalid base64 userinfo in ss link: {self.config_uri}"
                ) from e
        else:
            try:
                base = self.config_uri.split("://", 1)[1].split("#", 1)[0]
                padded = base + "=" * (-len(base) % 4)
                decoded = base64.b64decode(padded).decode()
                before_at, host_port = decoded.split("@")
                method_raw, password_raw = before_at.split(":")
                server_str, port_str = host_port.split(":")

                method = self.sanitize_str(method_raw)
                password = self.sanitize_str(password_raw)
                server = self.sanitize_str(server_str)
                port = int(port_str)
            except (ValueError, IndexError) as e:
                raise ParserError(
                    f"Invalid ss link format: {self.config_uri}") from e

        if not all([server, port, method, password]):
            raise ParserError(
                f"Missing components in ss link: {self.config_uri}")

        proxy = {
            "name": name,
            "type": "ss",
            "server": server,
            "port": int(port),
            "cipher": method,
            "password": password,
        }

        # Parse query parameters for plugin, tfo, udp
        query_params = {k: (v[0] if v else "") for k, v in parse_qs(p.query).items()}

        plugin_val = (query_params.get("plugin") or "").strip()
        if plugin_val:
            if ";" in plugin_val:
                plugin_name, plugin_opts = plugin_val.split(";", 1)
                if plugin_name.strip():
                    proxy["plugin"] = plugin_name.strip()
                if plugin_opts.strip():
                    proxy["plugin-opts"] = plugin_opts.strip()
            else:
                proxy["plugin"] = plugin_val

        tfo_val = str(query_params.get("tfo", "false")).lower()
        if tfo_val == "true":
            proxy["tfo"] = True

        udp_val = str(query_params.get("udp", "false")).lower()
        if udp_val == "true":
            proxy["udp"] = True

        return proxy

    def get_identifier(self) -> Optional[str]:
        """
        Get the identifier (password) for the Shadowsocks configuration.
        """
        p = urlparse(self.config_uri)
        password = None

        if p.password:
            password = self.sanitize_str(p.password)
        elif p.username:
            try:
                userinfo_decoded = base64.b64decode(
                    p.username + "=" * (-len(p.username) % 4)
                ).decode()
                _, password_raw = userinfo_decoded.split(":", 1)
                password = self.sanitize_str(password_raw)
            except (ValueError, IndexError, binascii.Error, UnicodeDecodeError):
                pass

        if not password:
            try:
                base = self.config_uri.split("://", 1)[1].split("#", 1)[0]
                padded = base + "=" * (-len(base) % 4)
                decoded = base64.b64decode(padded).decode()
                before_at, _ = decoded.split("@")
                _, password_raw = before_at.split(":")
                password = self.sanitize_str(password_raw)
            except (ValueError, IndexError, binascii.Error, UnicodeDecodeError):
                pass
        return password
