"""
Enhanced Fetcher Module with Robust Error Handling
This module provides improved network fetching with retry logic and detailed error reporting
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientTimeout

# Configure structured logging for better debugging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class FetcherError(Exception):
    """Custom exception for fetcher-related errors"""


class RateLimitError(FetcherError):
    """Raised when rate limiting is detected"""


class FetchResult:
    """Container for fetch results with metadata"""

    def __init__(
        self,
        source: str,
        configs: list[str],
        success: bool,
        error: str | None = None,
        response_time: float | None = None,
        status_code: int | None = None,
    ):
        self.source = source
        self.configs = configs
        self.success = success
        self.error = error
        self.response_time = response_time
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "source": self.source,
            "config_count": len(self.configs),
            "success": self.success,
            "error": self.error,
            "response_time": self.response_time,
            "status_code": self.status_code,
        }


async def fetch_from_source(
    session: aiohttp.ClientSession,
    source: str,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> FetchResult:
    """
    Fetch proxy configurations from a source with enhanced error handling.

    Args:
        session: aiohttp session for making requests
        source: URL to fetch configurations from
        timeout: Maximum time to wait for response
        max_retries: Number of retry attempts
        retry_delay: Initial delay between retries (exponential backoff)

    Returns:
        FetchResult object containing configs and metadata
    """

    # Validate URL format
    try:
        parsed_url = urlparse(source)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL format: {source}")
    except Exception as e:
        logger.error(f"URL validation failed for {source}: {e}")
        return FetchResult(source, [], False, error=str(e))

    # Set up timeout configuration
    timeout_config = ClientTimeout(
        total=timeout,
        connect=timeout / 3,  # Connection timeout is 1/3 of total
        sock_read=timeout / 2,  # Read timeout is 1/2 of total
    )

    # Custom headers to avoid being blocked
    headers = {
        "User-Agent":
        "ConfigStream/1.0 (github.com/YourUsername/ConfigStream)",
        "Accept": "text/plain, application/json, */*",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    last_error = None

    for attempt in range(max_retries):
        try:
            # Start timing the request
            start_time = asyncio.get_event_loop().time()

            logger.debug(f"Attempt {attempt + 1}/{max_retries} for {source}")

            async with session.get(
                    source,
                    timeout=timeout_config,
                    headers=headers,
                    allow_redirects=True,
                    ssl=True,  # Verify SSL certificates
            ) as response:

                # Calculate response time
                response_time = asyncio.get_event_loop().time() - start_time

                # Check for rate limiting
                if response.status == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    raise RateLimitError(
                        f"Rate limited. Retry after {retry_after} seconds")

                # Check for server errors (5xx)
                if 500 <= response.status < 600:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"Server error: {response.status}",
                        headers=response.headers,
                    )

                # Raise for bad status codes
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("Content-Type", "").lower()
                if "html" in content_type and "text/plain" not in content_type:
                    logger.warning(
                        f"Unexpected content type for {source}: {content_type}"
                    )

                # Read and process the response
                text = await response.text(encoding="utf-8", errors="ignore")

                # Parse configurations
                configs = []
                for line in text.splitlines():
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Basic validation for proxy configs
                    # (vmess://, vless://, ss://, trojan://, etc.)
                    if any(
                            line.startswith(prefix) for prefix in [
                                "vmess://",
                                "vless://",
                                "ss://",
                                "trojan://",
                                "hysteria://",
                                "hysteria2://",
                                "tuic://",
                                "wireguard://",
                                "naive://",
                                "http://",
                                "https://",
                                "socks://",
                                "socks5://",
                                "socks4://",
                            ]):
                        configs.append(line)
                    else:
                        logger.debug(
                            f"Skipping invalid config line: {line[:50]}...")

                # Log success
                logger.info(
                    f"Successfully fetched {len(configs)} configs from {source} "
                    f"(Status: {response.status}, Time: {response_time:.2f}s)")

                return FetchResult(
                    source=source,
                    configs=configs,
                    success=True,
                    response_time=response_time,
                    status_code=response.status,
                )

        except RateLimitError as e:
            logger.warning(f"Rate limit hit for {source}: {e}")
            last_error = str(e)
            # Wait longer for rate limits
            await asyncio.sleep(60)

        except TimeoutError:
            last_error = f"Timeout after {timeout} seconds"
            logger.warning(
                f"Timeout fetching {source} (attempt {attempt + 1}/{max_retries})"
            )

        except aiohttp.ClientError as e:
            last_error = f"HTTP error: {e}"
            logger.warning(f"Client error fetching {source}: {e}")

        except Exception as e:
            last_error = f"Unexpected error: {e}"
            logger.error(f"Unexpected error fetching {source}: {e}",
                         exc_info=True)

        # If not the last attempt, wait before retrying
        if attempt < max_retries - 1:
            delay = retry_delay * (2**attempt)  # Exponential backoff
            logger.debug(f"Waiting {delay:.1f}s before retry...")
            await asyncio.sleep(delay)

    # All attempts failed
    logger.error(
        f"Failed to fetch {source} after {max_retries} attempts. Last error: {last_error}"
    )
    return FetchResult(source=source,
                       configs=[],
                       success=False,
                       error=last_error)


async def fetch_multiple_sources(sources: list[str],
                                 max_concurrent: int = 10,
                                 timeout: int = 30) -> dict[str, FetchResult]:
    """
    Fetch from multiple sources concurrently with rate limiting.

    Args:
        sources: List of source URLs
        max_concurrent: Maximum concurrent requests
        timeout: Timeout per request

    Returns:
        Dictionary mapping source URL to FetchResult
    """
    results = {}

    # Create a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(session, source):
        async with semaphore:
            return await fetch_from_source(session, source, timeout)

    # Create session with connection pooling
    connector = aiohttp.TCPConnector(
        limit=100,  # Total connection pool limit
        limit_per_host=10,  # Per-host connection limit
        ttl_dns_cache=300,  # DNS cache timeout
        enable_cleanup_closed=True,  # Clean up closed connections
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_with_semaphore(session, source) for source in sources]

        # Use asyncio.gather with return_exceptions to handle failures gracefully
        fetch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for source, result in zip(sources, fetch_results):
            if isinstance(result, Exception):
                # Handle exceptions that escaped the try-catch
                logger.error(f"Unhandled exception for {source}: {result}")
                results[source] = FetchResult(source=source,
                                              configs=[],
                                              success=False,
                                              error=str(result))
            else:
                results[source] = result

    # Log summary
    successful = sum(1 for r in results.values() if r.success)
    total_configs = sum(len(r.configs) for r in results.values())
    logger.info(
        f"Fetch complete: {successful}/{len(sources)} sources successful, "
        f"{total_configs} total configs collected")

    return results
