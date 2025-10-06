from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .common import BaseParser


class HysteriaParser(BaseParser):
    """
    Parses a Hysteria, Hy2, or Hysteria2 configuration link.
    """

    def __init__(self, config_uri: str, idx: int, scheme: str):
        super().__init__(config_uri)
        self.idx = idx
        self.scheme = scheme

    def parse(self) -> Optional[Dict[str, Any]]:
        """
        Parse the Hysteria configuration link.

        Returns:
            A dictionary representing the Clash proxy, or None if parsing fails.
        """
        p = urlparse(self.config_uri)
        name = self.sanitize_str(p.fragment or f"{self.scheme}-{self.idx}")
        if not p.hostname or not p.port:
            return None

        q = parse_qs(p.query)
        proxy = {
            "name": name,
            "type": "hysteria2" if self.scheme in ("hy2", "hysteria2") else "hysteria",
            "server": self.sanitize_str(p.hostname),
            "port": p.port,
        }
        passwd_q = q.get("password", [None])[0]
        passwd = self.sanitize_str(p.password or passwd_q)
        if p.username and not passwd:
            passwd = self.sanitize_str(p.username)
        if passwd:
            proxy["password"] = passwd

        for key in ("auth", "peer", "sni", "insecure", "alpn", "obfs", "obfs-password"):
            if key in q:
                proxy[key] = self.sanitize_str(q[key][0])

        up_keys = ["upmbps", "up", "up_mbps"]
        down_keys = ["downmbps", "down", "down_mbps"]
        for k in up_keys:
            if k in q:
                proxy["upmbps"] = self.sanitize_str(q[k][0])
                break
        for k in down_keys:
            if k in q:
                proxy["downmbps"] = self.sanitize_str(q[k][0])
                break
        return proxy

    def get_identifier(self) -> Optional[str]:
        """
        Get the identifier (password) for the Hysteria configuration.
        """
        p = urlparse(self.config_uri)
        q = parse_qs(p.query)
        passwd_q = q.get("password", [None])[0]
        passwd = self.sanitize_str(p.password or passwd_q)
        if p.username and not passwd:
            passwd = self.sanitize_str(p.username)
        return passwd