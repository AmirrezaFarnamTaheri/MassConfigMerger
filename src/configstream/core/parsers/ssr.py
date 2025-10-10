from __future__ import annotations

import base64
import binascii
import logging
from typing import Any, Dict, Optional
from urllib.parse import parse_qs

from .common import BaseParser


class SsrParser(BaseParser):
    """
    Parses a ShadowsocksR (SSR) configuration link.
    """

    def __init__(self, config_uri: str, idx: int):
        super().__init__(config_uri)
        self.idx = idx

    def parse(self) -> Optional[Dict[str, Any]]:
        """
        Parse the ShadowsocksR (SSR) configuration link.

        Returns:
            A dictionary representing the Clash proxy, or None if parsing fails.
        """
        base = self.config_uri.split("://", 1)[1].split("#", 1)[0]
        name = f"ssr-{self.idx}"
        try:
            padded = base + "=" * (-len(base) % 4)
            decoded = base64.urlsafe_b64decode(padded).decode()
            main, _, tail = decoded.partition("/")
            parts = main.split(":")
            if len(parts) < 6:
                return None
            server, port_str, proto, method, obfs, pwd_enc = parts[:6]

            try:
                password_decoded = base64.urlsafe_b64decode(
                    pwd_enc + "=" * (-len(pwd_enc) % 4)
                ).decode()
                password = self.sanitize_str(password_decoded)
            except (binascii.Error, UnicodeDecodeError):
                password = self.sanitize_str(pwd_enc)

            q = parse_qs(tail[1:]) if tail.startswith("?") else {}
            proxy = {
                "name": name,
                "type": "ssr",
                "server": self.sanitize_str(server),
                "port": int(port_str),
                "cipher": self.sanitize_str(method),
                "password": password,
                "protocol": self.sanitize_str(proto),
                "obfs": self.sanitize_str(obfs),
            }

            for param, key in [
                ("obfsparam", "obfs-param"),
                ("protoparam", "protocol-param"),
                ("remarks", "name"),
                ("group", "group"),
            ]:
                if param in q:
                    try:
                        val = base64.urlsafe_b64decode(
                            q[param][0] + "=" * (-len(q[param][0]) % 4)
                        ).decode()
                    except (binascii.Error, UnicodeDecodeError):
                        val = q[param][0]
                    proxy[key] = self.sanitize_str(val)

            if "udpport" in q:
                try:
                    proxy["udpport"] = int(q["udpport"][0])
                except ValueError:
                    logging.debug(
                        "Could not parse udpport '%s' as integer.", q["udpport"][0]
                    )
            if "uot" in q:
                proxy["uot"] = self.sanitize_str(q["uot"][0])
            return proxy
        except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
            logging.debug("SSR parse failed: %s", exc)
            return None
