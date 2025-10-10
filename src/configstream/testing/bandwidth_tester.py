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
        test_url: str = "http://speedtest.tele2.net",
        proxy: Optional[str] = None
    ):
        """Initialize bandwidth tester.

        Args:
            test_url: Base URL for speed test server
            proxy: Optional proxy URL (e.g., "http://127.0.0.1:1080")
        """
        self.test_url = test_url
        self.proxy = proxy

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
                    proxy=self.proxy
                ) as response:
                    response.raise_for_status()

                    async for chunk in response.content.iter_chunked(self.CHUNK_SIZE):
                        total_bytes += len(chunk)

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

    async def test_full(self) -> BandwidthResult:
        """Run complete bandwidth test (download + upload).

        Returns:
            BandwidthResult with all test metrics
        """
        start = time.time()
        error = None

        try:
            # Run download test
            logger.info("Starting download test...")
            download_mbps = await self.test_download()

            # Small delay between tests
            await asyncio.sleep(0.5)

            # Run upload test
            logger.info("Starting upload test...")
            upload_mbps = await self.test_upload()

            duration_ms = int((time.time() - start) * 1000)

            if download_mbps == 0.0 and upload_mbps == 0.0:
                error = "Both download and upload tests failed"

            return BandwidthResult(
                download_mbps=download_mbps,
                upload_mbps=upload_mbps,
                test_duration_ms=duration_ms,
                error=error
            )

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            return BandwidthResult(
                download_mbps=0.0,
                upload_mbps=0.0,
                test_duration_ms=duration_ms,
                error=str(e)
            )


# Convenience function for quick tests
async def quick_bandwidth_test(
    proxy: Optional[str] = None
) -> BandwidthResult:
    """Quick bandwidth test with default settings.

    Args:
        proxy: Optional proxy URL

    Returns:
        BandwidthResult with test metrics

    Example:
        >>> result = await quick_bandwidth_test()
        >>> print(f"Down: {result.download_mbps} Mbps")
    """
    tester = BandwidthTester(proxy=proxy)
    return await tester.test_full()