from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .common import BaseParser


def parse(config: str, idx: int, scheme: str) -> Optional[Dict[str, Any]]:
    """
    Parse a generic or unknown configuration link as a fallback.

    Args:
        config: The configuration link.
        idx: The index of the configuration, used for default naming.
        scheme: The protocol scheme.

    Returns:
        A dictionary representing the Clash proxy, or None if parsing fails.
    """
    p = urlparse(config)
    name = BaseParser.sanitize_str(p.fragment or f"{scheme}-{idx}")
    if not p.hostname or not p.port:
        return None

    # Assume socks5 for any scheme starting with 'socks', otherwise http.
    typ = "socks5" if scheme.startswith("socks") else "http"

    return {
        "name": name,
        "type": typ,
        "server": BaseParser.sanitize_str(p.hostname),
        "port": p.port,
    }
