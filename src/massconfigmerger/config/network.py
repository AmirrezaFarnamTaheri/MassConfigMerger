from __future__ import annotations

from typing import Dict, Optional

from pydantic import Field

from .base import BaseConfig


class NetworkSettings(BaseConfig):
    """Settings related to network requests, timeouts, and proxies."""

    request_timeout: int = Field(10, description="General timeout for HTTP requests in seconds.")
    concurrent_limit: int = Field(
        20, description="Maximum number of concurrent HTTP requests."
    )
    connection_limit: int = Field(
        100,
        description="Maximum number of simultaneous TCP connections in the pool. 0 for unlimited.",
    )
    retry_attempts: int = Field(
        3, description="Number of retry attempts for failed HTTP requests."
    )
    retry_base_delay: float = Field(
        1.0, description="Base delay for exponential backoff between retries."
    )
    retry_jitter: float = Field(
        0.5, description="Amount of random jitter to apply to retry delays (0 to 1)."
    )
    connect_timeout: float = Field(
        3.0, description="Connection timeout for testing individual VPN configs in seconds."
    )
    http_proxy: Optional[str] = Field(
        None, alias="HTTP_PROXY", description="URL for an HTTP proxy (e.g., 'http://user:pass@host:port')."
    )
    socks_proxy: Optional[str] = Field(
        None, alias="SOCKS_PROXY", description="URL for a SOCKS proxy (e.g., 'socks5://user:pass@host:port')."
    )
    headers: Dict[str, str] = Field(
        default={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        },
        description="Default headers to use for all HTTP requests.",
    )