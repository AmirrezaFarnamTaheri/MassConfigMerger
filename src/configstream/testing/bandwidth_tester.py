"""Bandwidth testing for VPN nodes.

This module provides speed testing capabilities to measure download and
upload speeds through VPN connections.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class BandwidthResult:
    """Results from bandwidth test.

    Attributes:
        download_mbps: Download speed in megabits per second
        upload_mbps: Upload speed in megabits per second
        test_duration_ms: Total test duration in milliseconds
        error: Error message if test failed
    """
    download_mbps: float
    upload_mbps: float
    test_duration_ms: int
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if test was successful."""
        return self.error is None and self.download_mbps > 0


class BandwidthTester:
    """Tests download/upload speeds through VPN nodes.

    This class uses standard speed test servers to measure actual
    throughput rather than just latency.

    Example:
        >>> tester = BandwidthTester()
        >>> result = await tester.test_download()
        >>> print(f"Download: {result:.2f} Mbps")
    """

    # Test configuration
    DOWNLOAD_SIZE_MB = 5  # 5MB download test
    UPLOAD_SIZE_MB = 2    # 2MB upload test
    TIMEOUT_SECONDS = 30  # 30 second timeout
    CHUNK_SIZE = 8192     # Read in 8KB chunks

    def __init__(
        self,
        test_url: str = "https://speedtest.tele2.net",
        proxy: Optional[str] = None
    ):
        if not test_url.startswith("https://"):
            raise ValueError("test_url must use HTTPS")
        self.test_url = test_url.rstrip("/")
        self.proxy = proxy

    async def test_upload(self) -> float:
        """Test upload speed in Mbps."""
        try:
            data_size = self.UPLOAD_SIZE_MB * 1024 * 1024
            data = b'0' * data_size

            connector = aiohttp.TCPConnector(
                limit=1,
                limit_per_host=1,
                force_close=True
            )
            timeout = aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                start_time = time.time()

                upload_url = f"{self.test_url}/upload"
                resp = await session.options(upload_url, proxy=self.proxy)
                if resp.status >= 400:
                    logger.error(f"Upload endpoint not available at {upload_url} (HTTP {resp.status})")
                    return 0.0

                async with session.post(
                    upload_url,
                    data=data,
                    proxy=self.proxy
                ) as response:
                    if response.status >= 400:
                        logger.error(f"Upload failed (HTTP {response.status})")
                        return 0.0
                    await response.read()

                elapsed = time.time() - start_time
                mbps = (data_size * 8) / (elapsed * 1_000_000)
                logger.debug(
                    f"Upload test: {data_size} bytes in {elapsed:.2f}s = {mbps:.2f} Mbps"
                )
                return round(mbps, 2)
        except asyncio.TimeoutError:
            logger.warning("Upload test timed out")
            return 0.0
        except Exception as e:
            logger.error(f"Upload test failed: {e}")
            return 0.0

    async def test_download(self) -> float:
        """Test download speed in Mbps.

        Downloads a test file and measures throughput.

        Returns:
            Download speed in megabits per second, or 0.0 on failure
        """
        try:
            # Construct download URL
            url = f"{self.test_url}/{self.DOWNLOAD_SIZE_MB}MB.zip"

            # Configure connector
            connector = aiohttp.TCPConnector(
                limit=1,
                limit_per_host=1,
                force_close=True
            )

            # Create session with optional proxy
            timeout = aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:

                start_time = time.time()
                total_bytes = 0

                # Download file in chunks
                async with session.get(
                    url,
                    proxy=self.proxy,
                    headers={"Accept-Encoding": "identity"}
                ) as response:
                    response.raise_for_status()

                    expected_bytes = self.DOWNLOAD_SIZE_MB * 1024 * 1024
                    content_length = response.headers.get("Content-Length")
                    if content_length is not None and int(content_length) < expected_bytes:
                        logger.warning(
                            f"Download payload smaller than expected: {content_length} < {expected_bytes}"
                        )
                        return 0.0

                    async for chunk in response.content.iter_chunked(self.CHUNK_SIZE):
                        total_bytes += len(chunk)

                if total_bytes < expected_bytes:
                    logger.warning(
                        f"Downloaded fewer bytes than expected: {total_bytes} < {expected_bytes}"
                    )
                    return 0.0

                elapsed = time.time() - start_time

                # Calculate Mbps: (bytes * 8 bits/byte) / (seconds * 1,000,000 bits/Mb)
                mbps = (total_bytes * 8) / (elapsed * 1_000_000)

                logger.debug(
                    f"Download test: {total_bytes} bytes in {elapsed:.2f}s = {mbps:.2f} Mbps"
                )

                return round(mbps, 2)

        except asyncio.TimeoutError:
            logger.warning("Download test timed out")
            return 0.0
        except Exception as e:
            logger.error(f"Download test failed: {e}")
            return 0.0

    async def test_upload(self) -> float:
        """Test upload speed in Mbps.

        Uploads random data and measures throughput.

        Returns:
            Upload speed in megabits per second, or 0.0 on failure
        """
        try:
            # Generate random data for upload
            data_size = self.UPLOAD_SIZE_MB * 1024 * 1024
            # Use bytearray of zeros for efficiency (compresses well)
            data = b'0' * data_size

            connector = aiohttp.TCPConnector(
                limit=1,
                limit_per_host=1,
                force_close=True
            )

            timeout = aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:

                start_time = time.time()

                # Upload data
                # Note: Some speed test servers have upload endpoints
                # This is a simplified version - adjust URL as needed
                async with session.post(
                    f"{self.test_url}/upload.php",
                    data=data,
                    proxy=self.proxy
                ) as response:
                    # Read response to ensure upload completes
                    await response.read()

                elapsed = time.time() - start_time
                mbps = (data_size * 8) / (elapsed * 1_000_000)

                logger.debug(
                    f"Upload test: {data_size} bytes in {elapsed:.2f}s = {mbps:.2f} Mbps"
                )

                return round(mbps, 2)

        except asyncio.TimeoutError:
            logger.warning("Upload test timed out")
            return 0.0
        except Exception as e:
            logger.error(f"Upload test failed: {e}")
            return 0.0

    async def test_full(self, proxy_url: str | None = None) -> BandwidthResult:
        """Run complete bandwidth test."""
        start = time.time()

        try:
            download_mbps = await self.test_download(proxy_url)
            upload_mbps = await self.test_upload(proxy_url)

            duration_ms = int((time.time() - start) * 1000)

            return BandwidthResult(
                download_mbps=round(download_mbps, 2),
                upload_mbps=round(upload_mbps, 2),
                test_duration_ms=duration_ms
            )

        except Exception as e:
            return BandwidthResult(
                download_mbps=0.0,
                upload_mbps=0.0,
                test_duration_ms=0,
                error=str(e)
            )