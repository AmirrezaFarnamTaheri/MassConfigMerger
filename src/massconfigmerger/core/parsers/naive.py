from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlparse

from .common import BaseParser
from ...exceptions import ParserError


class NaiveParser(BaseParser):
    """
    Parses a NaiveProxy configuration link.
    """

    def __init__(self, config_uri: str, idx: int):
        super().__init__(config_uri)
        self.idx = idx

    def parse(self) -> Dict[str, Any]:
        """
        Parse the NaiveProxy configuration link.

        Returns:
            A dictionary representing the Clash proxy.
        Raises:
            ParserError: If the hostname or port is missing.
        """
        p = urlparse(self.config_uri)
        name = self.sanitize_str(p.fragment or f"naive-{self.idx}")
        if not p.hostname or not p.port:
            raise ParserError(f"Missing hostname or port in NaiveProxy link: {self.config_uri}")

        return {
            "name": name,
            "type": "http",
            "server": self.sanitize_str(p.hostname),
            "port": p.port,
            "username": self.sanitize_str(p.username or ""),
            "password": self.sanitize_str(p.password or ""),
            "tls": True,
        }