import asyncio
import logging
from datetime import datetime, timezone

import aiohttp
from aiohttp_proxy import ProxyConnector
from singbox2proxy import SingBoxProxy

from .config import ProxyConfig
from .core import Proxy
from .services import IProxyTester

# Remove tester.py - consolidate all here
logger = logging.getLogger(__name__)


class SingBoxTester(IProxyTester):
    """Concrete implementation of IProxyTester using SingBox"""

    def __init__(self):
        self.config = ProxyConfig()
        self.current_test_url_index = 0

    async def test(self, proxy: Proxy) -> Proxy:
        """
        Test a single proxy configuration with fallback URLs.
        Uses centralized configuration for timeouts.
        """
        proxy.tested_at = datetime.now(timezone.utc).isoformat()

        sb_proxy = SingBoxProxy(proxy.config)
        try:
            await sb_proxy.start()
            connector = ProxyConnector.from_url(sb_proxy.http_proxy_url)

            # Try multiple test URLs
            for test_url in self.config.TEST_URLS.values():
                try:
                    async with aiohttp.ClientSession(
                            connector=connector) as session:
                        start_time = asyncio.get_event_loop().time()
                        async with session.get(test_url,
                                               timeout=aiohttp.ClientTimeout(
                                                   total=self.config.
                                                   TEST_TIMEOUT)) as response:
                            if response.status == 204:
                                end_time = asyncio.get_event_loop().time()
                                proxy.latency = round(
                                    (end_time - start_time) * 1000, 2)
                                proxy.is_working = True
                                break

                except TimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Test URL {test_url} failed: {str(e)}")
                    continue

            if not proxy.is_working:
                proxy.security_issues.append("All test URLs failed")

        except Exception as e:
            proxy.is_working = False
            # Mask sensitive data in logs
            if self.config.MASK_SENSITIVE_DATA:
                proxy.security_issues.append(f"Connection failed: [MASKED]")
            else:
                proxy.security_issues.append(f"Connection failed: {str(e)}")
            logger.error(f"Proxy test error: {str(e)[:50]}")

        finally:
            try:
                await sb_proxy.stop()
            except Exception:
                pass

        return proxy
