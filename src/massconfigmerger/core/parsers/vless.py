from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .common import BaseParser


class VlessParser(BaseParser):
    """
    Parses a VLESS or Reality configuration link.
    """

    def __init__(self, config_uri: str, idx: int):
        super().__init__(config_uri)
        self.idx = idx

    def _parse_reality_opts(self, q: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to parse and build the reality-opts dictionary."""
        pbk_q = q.get("pbk") or q.get("public-key") or q.get("publicKey") or q.get("public_key") or q.get("publickey")
        sid_q = q.get("sid") or q.get("short-id") or q.get("shortId") or q.get("short_id") or q.get("shortid")
        spider_q = q.get("spiderX") or q.get("spider-x") or q.get("spider_x")

        pbk = self.sanitize_str(pbk_q[0]) if pbk_q else None
        sid = self.sanitize_str(sid_q[0]) if sid_q else None
        spider = self.sanitize_str(spider_q[0]) if spider_q else None

        opts = {}
        if pbk:
            opts["public-key"] = pbk
        if sid:
            opts["short-id"] = sid
        if spider:
            opts["spider-x"] = spider

        return opts, pbk, sid, spider

    def parse(self) -> Optional[Dict[str, Any]]:
        """
        Parse the VLESS or Reality configuration link.
        """
        p = urlparse(self.config_uri)
        q = parse_qs(p.query)
        scheme = p.scheme.lower()
        name = self.sanitize_str(p.fragment or f"{scheme}-{self.idx}")

        proxy = {
            "name": name,
            "type": "vless",
            "server": self.sanitize_str(p.hostname or ""),
            "port": p.port or 0,
            "uuid": self.sanitize_str(p.username or ""),
            "encryption": self.sanitize_str(q.get("encryption", ["none"])[0]),
        }

        if scheme == "reality" or q.get("security") in (["reality"], ["tls"]):
            proxy["tls"] = True

        net = q.get("type") or q.get("mode")
        if net:
            proxy["network"] = self.sanitize_str(net[0])

        for key in ("host", "path", "sni", "alpn", "fp", "flow", "serviceName"):
            if key in q:
                proxy[key] = self.sanitize_str(q[key][0])

        reality_opts, pbk, sid, spider = self._parse_reality_opts(q)
        if pbk:
            proxy["pbk"] = pbk
        if sid:
            proxy["sid"] = sid
        if spider:
            proxy["spiderX"] = spider
        if reality_opts:
            proxy["reality-opts"] = reality_opts

        if "ws-headers" in q:
            proxy["ws-headers"] = self.sanitize_headers(q["ws-headers"][0])

        return proxy

    def get_identifier(self) -> Optional[str]:
        """
        Get the identifier (UUID) for the VLESS/Reality configuration.
        """
        p = urlparse(self.config_uri)
        return self.sanitize_str(p.username)