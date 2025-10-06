from __future__ import annotations

import logging
from typing import Optional

from ..config import Settings
from .connection import ConnectionTester
from .dns import DNSResolver, is_ip_address
from .geoip import GeoIPLookup


class NodeTester:
    """A utility class for testing node latency and performing GeoIP lookups."""

    def __init__(self, config: Settings) -> None:
        """Initialize the NodeTester."""
        self.config = config
        self.resolver = DNSResolver()
        self.connection_tester = ConnectionTester(config.network.connect_timeout)
        self.geoip_lookup = GeoIPLookup(config, self.resolver)

    async def test_connection(self, host: str, port: int) -> Optional[float]:
        """Test a TCP connection to a given host and port, returning the latency."""
        if not self.config.processing.enable_url_testing:
            return None

        target_ip = await self.resolver.resolve(host)
        if not target_ip or not is_ip_address(target_ip):
            logging.debug("Skipping connection test; unresolved host: %s", host)
            return None

        return await self.connection_tester.test(target_ip, port)

    async def lookup_geo_data(self, host: str) -> tuple[Optional[str], Optional[str], Optional[float], Optional[float]]:
        """Return the geo-data for a host using the GeoIP database."""
        return await self.geoip_lookup.lookup(host)

    async def close(self) -> None:
        """Gracefully close any open resources."""
        await self.resolver.close()
        self.geoip_lookup.close()