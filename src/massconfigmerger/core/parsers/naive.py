from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .common import sanitize_str


def parse(config: str, idx: int) -> Optional[Dict[str, Any]]:
    """
    Parse a NaiveProxy configuration link.

    Args:
        config: The NaiveProxy configuration link.
        idx: The index of the configuration, used for default naming.

    Returns:
        A dictionary representing the Clash proxy, or None if parsing fails.
    """
    p = urlparse(config)
    name = sanitize_str(p.fragment or f"naive-{idx}")
    if not p.hostname or not p.port:
        return None

    return {
        "name": name,
        "type": "http",
        "server": sanitize_str(p.hostname),
        "port": p.port,
        "username": sanitize_str(p.username or ""),
        "password": sanitize_str(p.password or ""),
        "tls": True,
    }
