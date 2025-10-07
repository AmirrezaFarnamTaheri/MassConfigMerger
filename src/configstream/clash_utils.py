"""Utility functions for handling Clash-compatible configurations.

This module provides a set of helpers for converting standard VPN configuration
links into the dictionary format required by Clash.
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