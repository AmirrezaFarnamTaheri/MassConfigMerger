from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .common import BaseParser
from ...exceptions import ParserError


class TuicParser(BaseParser):
    """
    Parses a TUIC configuration link.
    """

    def __init__(self, config_uri: str, idx: int):
        super().__init__(config_uri)
        self.idx = idx

    def parse(self) -> Dict[str, Any]:
        """
        Parse the TUIC configuration link.

        Returns:
            A dictionary representing the Clash proxy.
        Raises:
            ParserError: If the hostname or port is missing.
        """
        p = urlparse(self.config_uri)
        name = self.sanitize_str(p.fragment or f"tuic-{self.idx}")
        if not p.hostname or not p.port:
            raise ParserError(
                f"Missing hostname or port in TUIC link: {self.config_uri}"
            )

        q = parse_qs(p.query)
        proxy = {
            "name": name,
            "type": "tuic",
            "server": self.sanitize_str(p.hostname),
            "port": p.port,
        }
        uuid = self.sanitize_str(q.get("uuid", [None])[0] or p.username)
        passwd = self.sanitize_str(q.get("password", [None])[0] or p.password)
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
                    proxy[out_key] = self.sanitize_str(q[k][0])
                    break
        return proxy

    def get_identifier(self) -> Optional[str]:
        """
        Get the identifier (UUID or password) for the TUIC configuration.
        """
        p = urlparse(self.config_uri)
        q = parse_qs(p.query)
        passwd_q = q.get("password", [None])[0]
        if passwd_q:
            return self.sanitize_str(passwd_q)
        uuid = self.sanitize_str(p.username or q.get("uuid", [None])[0])
        if uuid:
            return uuid
        return self.sanitize_str(p.password)
