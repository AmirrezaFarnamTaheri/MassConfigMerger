from __future__ import annotations

from typing import List, Optional, Set

from pydantic import Field

from .base import BaseConfig


class FilteringSettings(BaseConfig):
    """Settings for filtering configurations at different stages of the pipeline."""

    fetch_protocols: List[str] = Field(
        default_factory=list,
        description="List of VPN protocols to fetch from sources (e.g., ['VLESS', 'SS']).",
    )
    include_patterns: List[str] = Field(
        default_factory=list,
        description="List of regex patterns to apply to include configs.",
    )
    exclude_patterns: List[str] = Field(
        default_factory=list,
        description="List of regex patterns to apply to exclude configs.",
    )
    merge_include_protocols: Set[str] = Field(
        default={"SHADOWSOCKS", "SHADOWSOCKSR", "TROJAN", "REALITY", "VMESS", "VLESS", "HYSTERIA", "HYSTERIA2", "TUIC", "NAIVE", "JUICITY", "WIREGUARD", "SHADOWTLS", "BROOK"},
        description="Set of protocols to include in the final merged output.",
    )
    merge_exclude_protocols: Set[str] = Field(
        default={"OTHER"},
        description="Set of protocols to exclude from the final merged output.",
    )
    include_countries: Optional[Set[str]] = Field(
        None, description="Set of ISO country codes to include (e.g., {'US', 'CA'}). Requires GeoIP."
    )
    exclude_countries: Optional[Set[str]] = Field(
        None, description="Set of ISO country codes to exclude (e.g., {'IR', 'CN'}). Requires GeoIP."
    )
    include_isps: Optional[Set[str]] = Field(
        None, description="Set of ISP names to include (e.g., {'Google', 'Amazon'}). Requires GeoIP."
    )
    exclude_isps: Optional[Set[str]] = Field(
        None, description="Set of ISP names to exclude. Requires GeoIP."
    )
    max_ping_ms: Optional[int] = Field(
        1000, description="Maximum acceptable ping in milliseconds for a config to be included."
    )
    tls_fragment: Optional[str] = Field(
        None, description="Filter configs to only include those with a specific TLS fragment."
    )