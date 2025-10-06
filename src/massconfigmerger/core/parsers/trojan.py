from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .common import BaseParser


class TrojanParser(BaseParser):
    """
    Parses a Trojan configuration link.
    """

    def __init__(self, config_uri: str, idx: int):
        super().__init__(config_uri)
        self.idx = idx

    def parse(self) -> Optional[Dict[str, Any]]:
        """
        Parse the Trojan configuration link.

        Returns:
            A dictionary representing the Clash proxy, or None if parsing fails.
        """
        p = urlparse(self.config_uri)
        q = parse_qs(p.query)
        name = self.sanitize_str(p.fragment or f"trojan-{self.idx}")
        proxy = {
            "name": name,
            "type": "trojan",
            "server": self.sanitize_str(p.hostname or ""),
            "port": p.port or 0,
            "password": self.sanitize_str(p.username or p.password or ""),
        }
        if q.get("sni"):
            proxy["sni"] = self.sanitize_str(q.get("sni")[0])
        if q.get("security"):
            proxy["tls"] = True
        net = q.get("type") or q.get("mode")
        if net:
            proxy["network"] = self.sanitize_str(net[0])
        for key in ("host", "path", "alpn", "flow", "serviceName"):
            if key in q:
                proxy[key] = self.sanitize_str(q[key][0])

        if "ws-headers" in q:
            proxy["ws-headers"] = self.sanitize_headers(q["ws-headers"][0])
        return proxy

    def get_identifier(self) -> Optional[str]:
        """
        Get the identifier (password) for the Trojan configuration.
        """
        p = urlparse(self.config_uri)
        return self.sanitize_str(p.username or p.password)