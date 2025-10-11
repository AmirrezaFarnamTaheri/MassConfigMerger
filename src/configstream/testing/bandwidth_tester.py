"""Bandwidth testing for VPN nodes."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class BandwidthResult:
    """Results from bandwidth test."""
    download_mbps: float
    upload_mbps: float
    test_duration_ms: int
    error: str | None = None

class BandwidthTester:
    """Tests download/upload speeds through VPN nodes."""

    # Test file sizes
    DOWNLOAD_SIZE_MB = 5  # 5MB download test
    UPLOAD_SIZE_MB = 2    # 2MB upload test
    TIMEOUT = 30          # 30 second timeout

    def __init__(self, test_url: str = "http://speedtest.tele2.net"):
        self.test_url = test_url

    async def test_download(self, proxy_url: str | None = None) -> float:
        """Test download speed in Mbps."""
        try:
            url = f"{self.test_url}/{self.DOWNLOAD_SIZE_MB}MB.zip"
            connector = None

            if proxy_url:
                connector = aiohttp.TCPConnector()
                # Configure proxy if needed

            async with aiohttp.ClientSession(connector=connector) as session:
                start_time = time.time()

                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT)
                ) as response:
                    total_bytes = 0
                    async for chunk in response.content.iter_chunked(8192):
                        total_bytes += len(chunk)

                elapsed = time.time() - start_time
                mbps = (total_bytes * 8) / (elapsed * 1_000_000)
                return mbps

        except Exception as e:
            logger.error(f"Download test failed: {e}")
            return 0.0

    async def test_upload(self, proxy_url: str | None = None) -> float:
        """Test upload speed in Mbps."""
        try:
            # Generate random data for upload
            data = b'0' * (self.UPLOAD_SIZE_MB * 1024 * 1024)

            connector = None
            if proxy_url:
                connector = aiohttp.TCPConnector()

            async with aiohttp.ClientSession(connector=connector) as session:
                start_time = time.time()

                async with session.post(
                    f"{self.test_url}/upload.php",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT)
                ) as response:
                    await response.read()

                elapsed = time.time() - start_time
                mbps = (len(data) * 8) / (elapsed * 1_000_000)
                return mbps

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