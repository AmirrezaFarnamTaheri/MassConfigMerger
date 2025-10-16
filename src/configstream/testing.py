from __future__ import annotations

import asyncio
from datetime import datetime

import aiohttp
from aiohttp_proxy import ProxyConnector
from rich.progress import Progress
import geoip2.database
from singbox2proxy import SingBoxProxy

from .core import Proxy

# Configuration
TEST_URL = "https://www.google.com/generate_204"
TEST_TIMEOUT = 10
SECURITY_CHECK_TIMEOUT = 5

# Security test endpoints
SECURITY_TESTS = {
    "redirect": "http://httpbin.org/redirect/1",
    "headers": "http://httpbin.org/headers",
    "content": "http://example.com",
    "ssl": "https://www.howsmyssl.com/a/check",
}


class SingBoxWorker:
    """Worker managing sing-box process for testing proxies."""

    def __init__(self):
        self.proxy: SingBoxProxy | None = None
        self.session: aiohttp.ClientSession | None = None
        self.connector: ProxyConnector | None = None

    async def start(self):
        """Start the sing-box worker."""
        # TODO: Implement persistent worker in future optimization
        pass

    async def stop(self):
        """Stop the sing-box worker."""
        if self.session:
            await self.session.close()
            self.session = None
        if self.proxy:
            await self.proxy.stop()
            self.proxy = None

    async def test_proxy(self, proxy_instance: Proxy):
        """Test a single proxy configuration."""
        self.proxy = SingBoxProxy(proxy_instance.config)
        try:
            await self.proxy.start()
            self.connector = ProxyConnector.from_url(self.proxy.http_proxy_url)
            self.session = aiohttp.ClientSession(connector=self.connector)

            # Basic connectivity test
            start_time = asyncio.get_event_loop().time()
            async with self.session.get(TEST_URL, timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)) as response:
                if response.status == 204:
                    end_time = asyncio.get_event_loop().time()
                    proxy_instance.latency = round((end_time - start_time) * 1000, 2)
                    proxy_instance.is_working = True
                else:
                    proxy_instance.is_working = False
                    return

            # Security tests (non-blocking)
            await self._run_security_tests(proxy_instance)

        except Exception as e:
            proxy_instance.is_working = False
            proxy_instance.security_issues.append(f"Connection failed: {str(e)}")
        finally:
            if self.session and not self.session.closed:
                await self.session.close()
                self.session = None
            if self.proxy:
                await self.proxy.stop()
                self.proxy = None

    async def _run_security_tests(self, proxy: Proxy):
        """Run security tests on proxy."""
        if not self.session:
            return

        try:
            # Test 1: Redirect handling
            async with self.session.get(
                SECURITY_TESTS["redirect"],
                timeout=aiohttp.ClientTimeout(total=SECURITY_CHECK_TIMEOUT),
                allow_redirects=False
            ) as response:
                if response.status not in [301, 302, 307, 308]:
                    proxy.security_issues.append("Improper redirect handling")

            # Test 2: Header preservation
            async with self.session.get(
                SECURITY_TESTS["headers"],
                timeout=aiohttp.ClientTimeout(total=SECURITY_CHECK_TIMEOUT)
            ) as response:
                headers = await response.json()
                if "User-Agent" not in headers.get("headers", {}):
                    proxy.security_issues.append("Headers not preserved")

            # Test 3: Content injection check
            async with self.session.get(
                SECURITY_TESTS["content"],
                timeout=aiohttp.ClientTimeout(total=SECURITY_CHECK_TIMEOUT)
            ) as response:
                text = await response.text()
                if "eval(" in text or "atob(" in text or "<script>alert" in text.lower():
                    proxy.security_issues.append("Content injection detected")
                    proxy.is_secure = False

            # Test 4: SSL/TLS check
            try:
                async with self.session.get(
                    SECURITY_TESTS["ssl"],
                    timeout=aiohttp.ClientTimeout(total=SECURITY_CHECK_TIMEOUT)
                ) as response:
                    ssl_info = await response.json()
                    rating = ssl_info.get("rating", "")
                    if rating and rating != "Probably Okay":
                        proxy.security_issues.append(f"Weak SSL: {rating}")
            except Exception:
                pass  # SSL test is optional

        except Exception as e:
            proxy.security_issues.append(f"Security test error: {str(e)}")

        # Mark proxy as insecure if critical issues found
        if any("injection" in issue.lower() or "malicious" in issue.lower() for issue in proxy.security_issues):
            proxy.is_secure = False
            proxy.is_working = False


async def test_and_geolocate_proxy(proxy: Proxy, worker: SingBoxWorker) -> Proxy:
    """Test a proxy and enrich it with geolocation data."""
    proxy.tested_at = datetime.utcnow().isoformat() + "Z"

    # Geolocate
    _geolocate(proxy)

    # Test connectivity and security
    try:
        await worker.test_proxy(proxy)
    except Exception as e:
        proxy.is_working = False
        proxy.security_issues.append(f"Test failed: {str(e)}")

    return proxy


def _geolocate(proxy: Proxy):
    """Get geolocation info for proxy."""
    try:
        with geoip2.database.Reader("data/GeoLite2-Country.mmdb") as reader:
            response = reader.country(proxy.address)
            proxy.country = response.country.name or "Unknown"
            proxy.country_code = response.country.iso_code or "XX"
    except Exception:
        pass

    try:
        with geoip2.database.Reader("data/GeoLite2-City.mmdb") as reader:
            response = reader.city(proxy.address)
            proxy.city = response.city.name or "Unknown"
    except Exception:
        pass

    try:
        with geoip2.database.Reader("data/ip-to-asn.mmdb") as reader:
            asn_response = reader.asn(proxy.address)
            proxy.asn_number = asn_response.autonomous_system_number
            proxy.asn = f"AS{asn_response.autonomous_system_number} ({asn_response.autonomous_system_organization})"
    except Exception:
        pass


async def process_and_test_proxies(
    proxies: list[Proxy], progress: Progress, max_workers: int = 10
) -> list[Proxy]:
    """Parse and test proxy configurations."""
    if not proxies:
        return []

    task = progress.add_task("[cyan]Testing proxies...", total=len(proxies))
    results: list[Proxy] = []

    # Create workers
    num_workers = min(max_workers, len(proxies))
    workers = [SingBoxWorker() for _ in range(num_workers)]

    async def test_and_update(proxy: Proxy, worker: SingBoxWorker):
        tested = await test_and_geolocate_proxy(proxy, worker)
        results.append(tested)
        progress.update(task, advance=1)

    # Distribute work
    tasks = []
    for i, proxy in enumerate(proxies):
        worker = workers[i % num_workers]
        tasks.append(test_and_update(proxy, worker))

    await asyncio.gather(*tasks, return_exceptions=True)

    # Sort by working status and latency
    working = sorted(
        [p for p in results if p.is_working and p.is_secure and p.latency is not None],
        key=lambda p: p.latency or float("inf"),
    )
    non_working = [p for p in results if not p.is_working or not p.is_secure]

    return working + non_working