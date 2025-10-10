# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

from __future__ import annotations

import binascii
import json
import logging
from typing import Any, Callable, Dict, Optional, Union

from ..exceptions import ParserError
from .parsers import (
    fallback,
)
from .parsers.hysteria import HysteriaParser
from .parsers.naive import NaiveParser
from .parsers.shadowsocks import ShadowsocksParser
from .parsers.ssr import SsrParser
from .parsers.trojan import TrojanParser
from .parsers.tuic import TuicParser
from .parsers.vmess import VmessParser
from .parsers.vless import VlessParser


class ProxyParser:
    """
    A class to parse different proxy protocols from their config links.

    This class acts as a facade, delegating the parsing of specific
    protocols to dedicated modules in the `parsers` subpackage.
    """

    def __init__(self):
        """Initialize the parser and map schemes to parsing functions."""
        self.parsers: Dict[str, Callable[..., Optional[Dict[str, Any]]]] = {
            "vmess": VmessParser,
            "vless": VlessParser,
            "reality": VlessParser,
            "trojan": TrojanParser,
            "ss": ShadowsocksParser,
            "shadowsocks": ShadowsocksParser,
            "ssr": SsrParser,
            "shadowsocksr": SsrParser,
            "naive": NaiveParser,
            "hy2": HysteriaParser,
            "hysteria2": HysteriaParser,
            "hysteria": HysteriaParser,
            "tuic": TuicParser,
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

            if not parser:
                return fallback.parse(config, idx, scheme)

            if scheme in (
                "vmess",
                "vless",
                "reality",
                "trojan",
                "ss",
                "shadowsocks",
                "ssr",
                "shadowsocksr",
                "naive",
                "tuic",
            ):
                return parser(config, idx).parse()
            elif scheme in ("hy2", "hysteria2", "hysteria"):
                return parser(config, idx, scheme).parse()
            else:  # old function-based parsers
                return parser(config, idx)
        except (
            ParserError,
            ValueError,
            binascii.Error,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            logging.debug(
                "config_to_clash_proxy failed for '%s': %s", config, exc)
            return None
