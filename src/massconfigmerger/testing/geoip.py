from __future__ import annotations

import logging
import socket
from typing import Optional

try:  # pragma: no cover - optional dependency
    from geoip2.database import Reader
    from geoip2.errors import AddressNotFoundError
except ImportError:
    Reader = None
    AddressNotFoundError = None

from ..config import Settings
from .dns import DNSResolver, is_ip_address


class GeoIPLookup:
    """A utility class for performing GeoIP lookups."""

    _geoip_reader: Optional[Reader] = None

    def __init__(self, config: Settings, resolver: DNSResolver):
        self.config = config
        self.resolver = resolver
        self.geoip_cache: dict[str, tuple] = {}

    def _get_reader(self) -> Optional[Reader]:
        """Lazily initialize and return the GeoIP database reader."""
        if self._geoip_reader is None and self.config.processing.geoip_db and Reader:
            try:
                self._geoip_reader = Reader(str(self.config.processing.geoip_db))
            except (OSError, ValueError) as exc:
                logging.error("GeoIP reader init failed: %s", exc)
        return self._geoip_reader

    async def lookup(self, host: str) -> tuple[Optional[str], Optional[str], Optional[float], Optional[float]]:
        """
        Return the geo-data for a host.

        Returns a tuple of (country, isp, latitude, longitude).
        """
        if not host:
            return None, None, None, None
        if host in self.geoip_cache:
            return self.geoip_cache[host]

        reader = self._get_reader()
        if not reader:
            return None, None, None, None

        try:
            ip = await self.resolver.resolve(host)
            if not ip or not is_ip_address(ip):
                logging.debug("Skipping GeoIP lookup; unresolved host: %s", host)
                return None, None, None, None

            if hasattr(reader, "city"):
                resp = reader.city(ip)
                country = resp.country.iso_code
                isp = resp.traits.isp
                latitude = resp.location.latitude
                longitude = resp.location.longitude
            else:
                resp = reader.country(ip)
                country = resp.country.iso_code
                isp, latitude, longitude = None, None, None

            geo_data = (country, isp, latitude, longitude)
            if any(geo_data):
                self.geoip_cache[host] = geo_data
            return geo_data
        except (OSError, socket.gaierror, AddressNotFoundError) as exc:
            logging.debug("GeoIP lookup failed for %s: %s", host, exc)
            return None, None, None, None

    def close(self) -> None:
        """Gracefully close the GeoIP reader."""
        if self._geoip_reader:
            try:
                self._geoip_reader.close()
            except Exception as exc:
                logging.debug("GeoIP reader close failed: %s", exc)
            self._geoip_reader = None