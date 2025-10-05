from __future__ import annotations

import binascii
import json
import logging
from typing import Any, Callable, Dict, Optional, Union

from .parsers import (
    fallback,
    hysteria,
    naive,
    shadowsocks,
    ssr,
    trojan,
    tuic,
    vless,
    vmess,
)


class ProxyParser:
    """
    A class to parse different proxy protocols from their config links.

    This class acts as a facade, delegating the parsing of specific
    protocols to dedicated modules in the `parsers` subpackage.
    """

    def __init__(self):
        """Initialize the parser and map schemes to parsing functions."""
        self.parsers: Dict[str, Callable[..., Optional[Dict[str, Any]]]] = {
            "vmess": vmess.parse,
            "vless": vless.parse,
            "reality": vless.parse_reality,
            "trojan": trojan.parse,
            "ss": shadowsocks.parse,
            "shadowsocks": shadowsocks.parse,
            "ssr": ssr.parse,
            "shadowsocksr": ssr.parse,
            "naive": naive.parse,
            "hy2": hysteria.parse,
            "hysteria2": hysteria.parse,
            "hysteria": hysteria.parse,
            "tuic": tuic.parse,
        }

    def config_to_clash_proxy(
        self,
        config: str,
        idx: int = 0,
        protocol: Optional[str] = None,
    ) -> Optional[Dict[str, Union[str, int, bool]]]:
        """
        Convert a single config link to a Clash proxy dictionary.

        Args:
            config: The configuration link string.
            idx: A unique index for the configuration.
            protocol: The protocol scheme of the configuration.

        Returns:
            A dictionary representing the Clash proxy, or None if parsing fails.
        """
        try:
            scheme = (protocol or config.split("://", 1)[0]).lower()
            parser = self.parsers.get(scheme)

            if parser:
                # Hysteria parser has a different signature
                if scheme in ("hy2", "hysteria2", "hysteria"):
                    return parser(config, idx, scheme)
                return parser(config, idx)
            else:
                return fallback.parse(config, idx, scheme)
        except (
            ValueError,
            binascii.Error,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            logging.debug("config_to_clash_proxy failed for '%s': %s", config, exc)
            return None
