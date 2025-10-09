"""Network testing utilities for VPN nodes.

This module provides the `NodeTester` class, which is a core component for
verifying the connectivity and performance of VPN configurations. It includes
methods for testing TCP connections, measuring latency, resolving hostnames
with an asynchronous DNS resolver, and looking up the geographic location
of servers using a GeoIP database.
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
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


def is_ip_address(host: str) -> bool:
    """Check if the given host is a valid IP address."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def is_public_ip_address(ip: str) -> bool:
    """Return ``True`` when *ip* is globally reachable."""

    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return ip_obj.is_global


class NodeTester:
    """A utility class for testing node latency and performing GeoIP lookups."""

    _resolver: Optional[AsyncResolver] = None
    _geoip_reader: Optional[Reader] = None

    def __init__(self, config: Settings) -> None:
        """Initialize the NodeTester."""
        self.config = config
        self.dns_cache: dict[str, str] = {}
        self.geoip_cache: dict[str, str] = {}

    def _get_resolver(self) -> Optional[AsyncResolver]:
        """Lazily initialize and return the asynchronous DNS resolver."""
        if self._resolver is None and sys.modules.get("aiodns") and AsyncResolver:
            try:
                self._resolver = AsyncResolver()
            except Exception as exc:
                logging.debug("AsyncResolver init failed: %s", exc)
        return self._resolver

    def _get_geoip_reader(self) -> Optional[Reader]:
        """Lazily initialize and return the GeoIP database reader."""
        if self._geoip_reader is None and self.config.processing.geoip_db and Reader:
            try:
                self._geoip_reader = Reader(
                    str(self.config.processing.geoip_db))
            except (OSError, ValueError) as exc:
                logging.error("GeoIP reader init failed: %s", exc)
        return self._geoip_reader

    async def resolve_host(self, host: str) -> Optional[str]:
        """Resolve a hostname to an IP address, with caching. Returns None on failure."""
        if host in self.dns_cache:
            return self.dns_cache[host]
        if is_ip_address(host):
            if is_public_ip_address(host):
                self.dns_cache[host] = host
                return host
            logging.debug("Rejecting non-public IP host: %s", host)
            return None

        resolver = self._get_resolver()
        if resolver:
            try:
                result = await resolver.resolve(host)
                if result:
                    ip = result[0]["host"]
                    if is_public_ip_address(ip):
                        self.dns_cache[host] = ip
                        return ip
                    logging.debug(
                        "Async DNS resolve returned non-public IP for %s: %s",
                        host,
                        ip,
                    )
                    return None
            except Exception as exc:
                logging.debug("Async DNS resolve failed for %s: %s", host, exc)

        try:
            info = await asyncio.get_running_loop().getaddrinfo(host, None)
            ip = info[0][4][0]
            if is_public_ip_address(ip):
                self.dns_cache[host] = ip
                return ip
            logging.debug(
                "Standard DNS lookup returned non-public IP for %s: %s",
                host,
                ip,
            )
            return None
        except (OSError, socket.gaierror) as exc:
            logging.debug("Standard DNS lookup failed for %s: %s", host, exc)
            return None

    async def test_connection(self, host: str, port: int) -> Optional[float]:
        """Test a TCP connection to a given host and port, returning the latency."""
        if not self.config.processing.enable_url_testing:
            return None

        start_time = time.time()
        try:
            target_ip = await self.resolve_host(host)
            if not target_ip:
                logging.debug(
                    "Skipping connection test; unresolved host: %s", host)
                return None
            if not is_public_ip_address(target_ip):
                logging.debug(
                    "Skipping connection test; non-public IP resolved for %s: %s",
                    host,
                    target_ip,
                )
                return None
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(target_ip, port),
                timeout=self.config.network.connect_timeout,
            )
            writer.close()
            await writer.wait_closed()
            return time.time() - start_time
        except (OSError, asyncio.TimeoutError) as exc:
            logging.debug("Connection test failed for %s:%d: %s",
                          host, port, exc)
            return None

    async def lookup_geo_data(self, host: str) -> tuple[Optional[str], Optional[str], Optional[float], Optional[float]]:
        """
        Return the geo-data for a host using the GeoIP database.

        Returns a tuple of (country, isp, latitude, longitude).
        """
        if not host:
            return None, None, None, None
        if host in self.geoip_cache:
            return self.geoip_cache[host]

        ip_address: Optional[str]
        if is_ip_address(host):
            ip_address = host
        else:
            ip_address = await self.resolve_host(host)

        if not ip_address:
            logging.debug("Skipping GeoIP lookup; unresolved host: %s", host)
            return None, None, None, None
        if not is_public_ip_address(ip_address):
            logging.debug(
                "Skipping GeoIP lookup; non-public IP resolved for %s: %s",
                host,
                ip_address,
            )
            return None, None, None, None

        geoip_reader = self._get_geoip_reader()
        if not geoip_reader:
            return None, None, None, None

        try:

            # Use city() for more detailed data, fallback to country()
            if hasattr(geoip_reader, "city"):
                resp = geoip_reader.city(ip_address)
                country = resp.country.iso_code
                isp = resp.traits.isp
                latitude = resp.location.latitude
                longitude = resp.location.longitude
            else:
                resp = geoip_reader.country(ip_address)
                country = resp.country.iso_code
                isp, latitude, longitude = None, None, None

            geo_data = (country, isp, latitude, longitude)
            if any(geo_data):
                self.geoip_cache[host] = geo_data
            return geo_data
        except (OSError, socket.gaierror, AddressNotFoundError) as exc:
            logging.debug("GeoIP lookup failed for %s: %s", host, exc)
            return None, None, None, None

    async def _close_resource(self, resource: object | None, name: str):
        """Helper to gracefully close a resource."""
        if resource:
            try:
                close = getattr(resource, "close", None)
                if asyncio.iscoroutinefunction(close):
                    await close()
                elif callable(close):
                    close()
            except Exception as exc:
                logging.debug("%s close failed: %s", name, exc)

    async def close(self) -> None:
        """Gracefully close any open resources."""
        await self._close_resource(self._resolver, "Resolver")
        self._resolver = None
        await self._close_resource(self._geoip_reader, "GeoIP reader")
        self._geoip_reader = None


class BlocklistChecker:
    """A utility for checking IPs against a blocklist."""

    _session: Optional[aiohttp.ClientSession] = None

    def __init__(self, config: Settings):
        self.config = config

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp client session."""
        if self._session is None or self._session.closed:
            try:
                self._session = aiohttp.ClientSession(
                    headers=self.config.network.headers
                )
            except Exception as exc:
                logging.warning("Failed to create aiohttp session: %s", exc)
                raise
        return self._session

    async def is_malicious(self, ip_address: str) -> bool:
        """Check if an IP address is considered malicious based on blocklist detections."""
        if (
            not self.config.security.apivoid_api_key
            or self.config.security.blocklist_detection_threshold <= 0
        ):
            return False

        if not ip_address or not is_ip_address(ip_address):
            return False

        if not is_public_ip_address(ip_address):
            logging.debug(
                "Skipping blocklist lookup for non-public IP: %s", ip_address
            )
            return False

        session = await self.get_session()
        url = "https://endpoint.apivoid.com/iprep/v1/pay-as-you-go/"
        params = {"key": self.config.security.apivoid_api_key, "ip": ip_address}
        headers = {"Accept": "application/json"}

        try:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.config.network.request_timeout,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("error"):
                        logging.warning(
                            "APIVoid API error for IP %s: %s",
                            ip_address,
                            data["error"],
                        )
                        return False

                    detections = (
                        data.get("data", {})
                        .get("report", {})
                        .get("blacklists", {})
                        .get("detections", 0)
                    )
                    if (
                        detections
                        >= self.config.security.blocklist_detection_threshold
                    ):
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
        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            logging.warning(
                "APIVoid API request failed for IP %s: %s", ip_address, exc
            )

        return False

    async def close(self) -> None:
        """Close the aiohttp client session."""
        if self._session and not self._session.closed:
            await self._session.close()

# End of file
