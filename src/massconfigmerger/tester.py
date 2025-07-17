from __future__ import annotations

import asyncio
import logging
import re
import socket
import sys
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - optional dependency
    from geoip2.database import Reader

try:
    from aiohttp.resolver import AsyncResolver
    import aiodns  # noqa: F401
except Exception:  # pragma: no cover - optional dependency
    AsyncResolver = None  # type: ignore
    aiodns = None  # type: ignore

from .config import Settings


class NodeTester:
    """Utility class for node latency testing and GeoIP lookup."""

    _geoip_reader: Optional["Reader"]

    def __init__(self, config: Settings) -> None:
        self.config = config
        self.dns_cache: dict[str, str] = {}
        self.resolver: Optional[AsyncResolver] = None
        self._geoip_reader: Optional["Reader"] = None

    async def test_connection(self, host: str, port: int) -> Optional[float]:
        """Return latency in seconds or ``None`` on failure."""
        if not self.config.enable_url_testing:
            return None

        start = time.time()
        target = host
        try:
            if "aiodns" in sys.modules and AsyncResolver is not None:
                if self.resolver is None:
                    try:
                        self.resolver = AsyncResolver()
                    except Exception as exc:  # pragma: no cover - env specific
                        logging.debug("AsyncResolver init failed: %s", exc)
                        self.resolver = None
                if self.resolver is not None:
                    try:
                        if host not in self.dns_cache:
                            result = await self.resolver.resolve(host, port)
                            if result:
                                self.dns_cache[host] = result[0]["host"]
                        target = self.dns_cache.get(host, host)
                    except Exception as exc:  # pragma: no cover - env specific
                        logging.debug("DNS resolve failed: %s", exc)
                        target = host

            _, writer = await asyncio.wait_for(
                asyncio.open_connection(target, port),
                timeout=self.config.connect_timeout,
            )
            writer.close()
            await writer.wait_closed()
            return time.time() - start
        except (OSError, asyncio.TimeoutError) as exc:
            logging.debug("Connection test failed: %s", exc)
            return None

    async def lookup_country(self, host: str) -> Optional[str]:
        """Return ISO country code for ``host`` if GeoIP database configured."""
        if not host or not self.config.geoip_db:
            return None
        try:
            from geoip2.database import Reader
            from geoip2.errors import AddressNotFoundError
        except ImportError:  # pragma: no cover - optional dependency
            return None

        if self._geoip_reader is None:
            try:
                self._geoip_reader = Reader(self.config.geoip_db)
            except OSError as exc:
                logging.debug("GeoIP reader init failed: %s", exc)
                self._geoip_reader = None
                return None

        try:
            ip = host
            if not re.match(r"^[0-9.]+$", host):
                info = await asyncio.get_running_loop().getaddrinfo(host, None)
                ip = info[0][4][0]
            assert self._geoip_reader is not None
            resp = self._geoip_reader.country(ip)
            return resp.country.iso_code
        except (OSError, socket.gaierror, AddressNotFoundError) as exc:
            logging.debug("GeoIP lookup failed: %s", exc)
            return None

    async def close(self) -> None:
        """Close any resolver resources if initialized."""
        if self.resolver is not None:
            try:
                close = getattr(self.resolver, "close", None)
                if asyncio.iscoroutinefunction(close):
                    await close()  # type: ignore[misc]
                elif callable(close):
                    close()
            except Exception as exc:  # pragma: no cover - env specific
                logging.debug("Resolver close failed: %s", exc)
            self.resolver = None

        if self._geoip_reader is not None:
            reader = self._geoip_reader
            self._geoip_reader = None
            try:
                close = getattr(reader, "close", None)
                if asyncio.iscoroutinefunction(close):
                    await close()  # type: ignore[misc]
                elif callable(close):
                    close()
            except Exception as exc:  # pragma: no cover - env specific
                logging.debug("GeoIP reader close failed: %s", exc)
