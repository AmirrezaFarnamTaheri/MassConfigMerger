from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import aiohttp
from aiohttp_proxy import ProxyConnector
from singbox2proxy import SingBoxProxy

from .core import Proxy
from .services import IProxyTester


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


class SingBoxTester(IProxyTester):
    """Concrete implementation of IProxyTester using SingBox."""

    async def test(self, proxy: Proxy) -> Proxy:
        """Test a single proxy configuration."""
        proxy.tested_at = datetime.now(timezone.utc).isoformat()

        sb_proxy = SingBoxProxy(proxy.config)
        try:
            await sb_proxy.start()
            connector = ProxyConnector.from_url(sb_proxy.http_proxy_url)
            async with aiohttp.ClientSession(connector=connector) as session:
                start_time = asyncio.get_event_loop().time()
                async with session.get(TEST_URL, timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)) as response:
                    if response.status == 204:
                        end_time = asyncio.get_event_loop().time()
                        proxy.latency = round((end_time - start_time) * 1000, 2)
                        proxy.is_working = True
                    else:
                        proxy.is_working = False
        except Exception as e:
            proxy.is_working = False
            proxy.security_issues.append(f"Connection failed: {str(e)}")
        finally:
            await sb_proxy.stop()

        return proxy
