"""Network testing utilities for VPN nodes.

This module provides the `NodeTester` class, which is a core component for
verifying the connectivity and performance of VPN configurations. It includes
methods for testing TCP connections, measuring latency, resolving hostnames
with an asynchronous DNS resolver, and looking up the geographic location
of servers using a GeoIP database.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import socket
import sys
import time
from typing import Optional

import aiohttp

try:  # pragma: no cover - optional dependency
    from geoip2.database import Reader
    from geoip2.errors import AddressNotFoundError
except ImportError:
    Reader = None
    AddressNotFoundError = None

try:
    from aiohttp.resolver import AsyncResolver
    import aiodns  # noqa: F401
except Exception:  # pragma: no cover - optional dependency
    AsyncResolver = None  # type: ignore
    aiodns = None  # type: ignore

from .config import Settings


import ipaddress


def _is_ip_address(host: str) -> bool:
    """Check if the given host is a valid IP address."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


class NodeTester:
    """A utility class for testing node latency and performing GeoIP lookups."""

    _resolver: Optional[AsyncResolver]
    _geoip_reader: Optional[Reader]

    def __init__(self, config: Settings) -> None:
        """Initialize the NodeTester."""
        self.config = config
        self.dns_cache: dict[str, str] = {}
        self._resolver = None
        self._geoip_reader = None

    def _get_resolver(self) -> Optional[AsyncResolver]:
        """Lazily initialize and return the asynchronous DNS resolver."""
        if self._resolver is None and "aiodns" in sys.modules and AsyncResolver:
            try:
                self._resolver = AsyncResolver()
            except Exception as exc:  # pragma: no cover - env specific
                logging.debug("AsyncResolver init failed: %s", exc)
        return self._resolver

    def _get_geoip_reader(self) -> Optional[Reader]:
        """Lazily initialize and return the GeoIP database reader."""
        if self._geoip_reader is None and self.config.processing.geoip_db and Reader:
            try:
                self._geoip_reader = Reader(str(self.config.processing.geoip_db))
            except (OSError, ValueError) as exc:
                logging.error("GeoIP reader init failed: %s", exc)
                # Avoid retrying initialization by setting a placeholder
                self._geoip_reader = None
        return self._geoip_reader

    async def resolve_host(self, host: str) -> str:
        """Resolve a hostname to an IP address, with caching."""
        if host in self.dns_cache:
            return self.dns_cache[host]
        if _is_ip_address(host):
            return host

        resolver = self._get_resolver()
        if resolver:
            try:
                result = await resolver.resolve(host)
                if result:
                    ip = result[0]["host"]
                    self.dns_cache[host] = ip
                    return ip
            except Exception as exc:  # pragma: no cover - env specific
                logging.debug("Async DNS resolve failed for %s: %s", host, exc)

        try:
            info = await asyncio.get_running_loop().getaddrinfo(host, None)
            ip = info[0][4][0]
            self.dns_cache[host] = ip
            return ip
        except (OSError, socket.gaierror) as exc:
            logging.debug("Standard DNS lookup failed for %s: %s", host, exc)
            return host

    async def test_connection(self, host: str, port: int) -> Optional[float]:
        """Test a TCP connection to a given host and port, returning the latency."""
        if not self.config.processing.enable_url_testing:
            return None

        start_time = time.time()
        try:
            target_ip = await self.resolve_host(host)
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(target_ip, port),
                timeout=self.config.network.connect_timeout,
            )
            writer.close()
            await writer.wait_closed()
            return time.time() - start_time
        except (OSError, asyncio.TimeoutError) as exc:
            logging.debug("Connection test failed for %s:%d: %s", host, port, exc)
            return None

    async def lookup_country(self, host: str) -> Optional[str]:
        """Return the ISO country code for a host using the GeoIP database."""
        if not host:
            return None

        geoip_reader = self._get_geoip_reader()
        if not geoip_reader:
            return None

        try:
            ip = await self.resolve_host(host)
            resp = geoip_reader.country(ip)
            return resp.country.iso_code
        except (OSError, socket.gaierror, AddressNotFoundError) as exc:
            logging.debug("GeoIP lookup failed for %s: %s", host, exc)
            return None

    async def _close_resource(self, resource: object | None, name: str):
        """Helper to gracefully close a resource."""
        if resource:
            try:
                close = getattr(resource, "close", None)
                if asyncio.iscoroutinefunction(close):
                    await close()
                elif callable(close):
                    close()
            except Exception as exc:  # pragma: no cover
                logging.debug("%s close failed: %s", name, exc)

    async def close(self) -> None:
        """Gracefully close any open resources."""
        await self._close_resource(self._resolver, "Resolver")
        self._resolver = None
        await self._close_resource(self._geoip_reader, "GeoIP reader")
        self._geoip_reader = None


class BlocklistChecker:
    """A utility for checking IPs against a blocklist."""

    def __init__(self, config: Settings):
        self.config = config
        self._session: aiohttp.ClientSession | None = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp client session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.config.network.headers)
        return self._session

    async def is_malicious(self, ip_address: str) -> bool:
        """Check if an IP address is considered malicious based on blocklist detections."""
        if (
            not self.config.security.apivoid_api_key
            or self.config.security.blocklist_detection_threshold <= 0
        ):
            return False

        session = await self.get_session()
        url = "https://api.apivoid.com/v2/ip-reputation"
        payload = {"ip": ip_address}
        headers = {
            "Accept": "application/json",
            "X-API-Key": self.config.security.apivoid_api_key,
        }

        try:
            async with session.post(
                url, json=payload, headers=headers, timeout=self.config.network.request_timeout
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    detections = data.get("blacklists", {}).get("detections", 0)
                    if detections >= self.config.security.blocklist_detection_threshold:
                        logging.info(
                            "IP %s is on %d blacklists, marking as malicious.",
                            ip_address,
                            detections,
                        )
                        return True
                else:
                    logging.warning(
                        "APIVoid API request failed with status %d for IP %s",
                        resp.status,
                        ip_address,
                    )
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as exc:
            logging.warning("APIVoid API request failed for IP %s: %s", ip_address, exc)

        return False

    async def close(self) -> None:
        """Close the aiohttp client session."""
        if self._session and not self._session.closed:
            await self._session.close()
