"""Shared data types for the ConfigStream application."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConfigResult:
    """
    Data class for holding the result of processing a single VPN configuration.
    """
    config: str
    protocol: str
    host: Optional[str] = None
    port: Optional[int] = None
    ping_time: Optional[float] = None
    is_reachable: bool = False
    source_url: str = ""
    country: Optional[str] = None
    isp: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reliability: Optional[float] = None
    is_blocked: bool = False