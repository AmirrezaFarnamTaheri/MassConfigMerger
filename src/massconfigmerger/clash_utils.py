"""Utility functions for handling Clash-compatible configurations.

This module provides a set of helpers for converting standard VPN configuration
links into the dictionary format required by Clash, generating flag emojis from
country codes, and building a complete Clash configuration file with default
proxy groups and rules.
"""
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
    """
    Convert a single VPN configuration link to a Clash proxy dictionary.

    This function serves as a wrapper around the `ProxyParser`'s conversion
    logic, providing a simple, direct way to transform a config link into
    a Clash-compatible dictionary.

    Args:
        config: The VPN configuration link (e.g., "vmess://...").
        idx: A unique index for the proxy, used to generate a name if one
             cannot be determined from the link.
        protocol: The protocol of the configuration, if known.

    Returns:
        A dictionary representing the Clash proxy, or None if conversion fails.
    """
    return _proxy_parser.config_to_clash_proxy(config, idx, protocol)


def flag_emoji(country: Optional[str]) -> str:
    """
    Return the flag emoji for a two-letter country code.

    Args:
        country: A two-letter ISO 3166-1 alpha-2 country code.

    Returns:
        A string containing the corresponding flag emoji, or a default
        white flag if the country code is invalid.
    """
    if not country or len(country) != 2:
        return "🏳"
    offset = 127397
    return chr(ord(country[0].upper()) + offset) + chr(ord(country[1].upper()) + offset)


def build_clash_config(proxies: List[Dict[str, Any]]) -> str:
    """
    Return a Clash YAML configuration with default groups and rules.

    This function takes a list of Clash proxy dictionaries and constructs a
    complete, ready-to-use Clash configuration file as a YAML string. It
    includes default proxy groups for automatic and manual selection.

    Args:
        proxies: A list of Clash proxy dictionaries.

    Returns:
        A string containing the full Clash configuration in YAML format.
    """
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