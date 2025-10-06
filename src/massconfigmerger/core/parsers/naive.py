from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .common import BaseParser


class NaiveParser(BaseParser):
    """
    Parses a NaiveProxy configuration link.
    """

    def __init__(self, config_uri: str, idx: int):
        super().__init__(config_uri)
        self.idx = idx

    def parse(self) -> Optional[Dict[str, Any]]:
        """
        Parse the NaiveProxy configuration link.

        Returns:
            A dictionary representing the Clash proxy, or None if parsing fails.
        """
        p = urlparse(self.config_uri)
        name = self.sanitize_str(p.fragment or f"naive-{self.idx}")
        if not p.hostname or not p.port:
            return None

        return {
            "name": name,
            "type": "http",
            "server": self.sanitize_str(p.hostname),
            "port": p.port,
            "username": self.sanitize_str(p.username or ""),
            "password": self.sanitize_str(p.password or ""),
            "tls": True,
        }