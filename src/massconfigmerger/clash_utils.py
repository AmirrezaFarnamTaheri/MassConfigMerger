from __future__ import annotations
from typing import Any, Dict, List, Optional, Union

import yaml

from .core.proxy_parser import ProxyParser

_proxy_parser = ProxyParser()


def config_to_clash_proxy(
    config: str,
    idx: int = 0,
    protocol: Optional[str] = None,
) -> Optional[Dict[str, Union[str, int, bool]]]:
    """Convert a single config link to a Clash proxy dictionary."""
    return _proxy_parser.config_to_clash_proxy(config, idx, protocol)


def flag_emoji(country: Optional[str]) -> str:
    """Return flag emoji for a 2-letter country code."""
    if not country or len(country) != 2:
        return "🏳"
    offset = 127397
    return chr(ord(country[0].upper()) + offset) + chr(ord(country[1].upper()) + offset)


def build_clash_config(proxies: List[Dict[str, Any]]) -> str:
    """Return a Clash YAML config with default groups and rule."""
    if not proxies:
        return ""

    names = [p["name"] for p in proxies]
    auto_select = "⚡ Auto-Select"
    manual = "🔰 MANUAL"
    groups = [
        {
            "name": auto_select,
            "type": "url-test",
            "proxies": names,
            "url": "http://www.gstatic.com/generate_204",
            "interval": 300,
        },
        {"name": manual, "type": "select", "proxies": [auto_select, *names]},
    ]
    rules = [f"MATCH,{manual}"]
    return yaml.safe_dump(
        {"proxies": proxies, "proxy-groups": groups, "rules": rules},
        allow_unicode=True,
        sort_keys=False,
    )
