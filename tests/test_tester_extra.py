from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.testing import DNSResolver, GeoIPLookup


@pytest.mark.asyncio
async def test_lookup_geo_data_empty_host():
    """Test lookup_geo_data with an empty host string."""
    settings = Settings()
    resolver = DNSResolver()
    geoip = GeoIPLookup(settings, resolver)
    result = await geoip.lookup("")
    assert result == (None, None, None, None)


@patch("massconfigmerger.testing.geoip.Reader", side_effect=ValueError("Test ValueError"))
def test_get_geoip_reader_value_error(mock_reader, caplog):
    """Test GeoIPLookup._get_reader handles ValueError on init."""
    settings = Settings()
    settings.processing.geoip_db = "dummy.mmdb"
    resolver = DNSResolver()
    geoip = GeoIPLookup(settings, resolver)

    reader = geoip._get_reader()

    assert reader is None
    assert "GeoIP reader init failed" in caplog.text


def test_missing_geoip2_dependency():
    """Test that GeoIPLookup handles a missing geoip2 dependency."""
    with patch.dict(sys.modules, {"geoip2": None}):
        from importlib import reload
        from massconfigmerger.testing import geoip

        reload(geoip)

        settings = Settings()
        settings.processing.geoip_db = "dummy.mmdb"
        resolver = DNSResolver()
        lookup = geoip.GeoIPLookup(settings, resolver)
        # _get_reader should return None without raising an error
        assert lookup._get_reader() is None

    # Reload to restore
    from importlib import reload
    from massconfigmerger.testing import geoip
    reload(geoip)


def test_missing_aiodns_dependency():
    """Test that DNSResolver handles a missing aiodns dependency."""
    with patch.dict(sys.modules, {"aiohttp.resolver": None, "aiodns": None}):
        from importlib import reload
        from massconfigmerger.testing import dns

        reload(dns)

        resolver = dns.DNSResolver()
        # _get_async_resolver should return None without raising an error
        assert resolver._get_async_resolver() is None

    # Reload to restore
    from importlib import reload
    from massconfigmerger.testing import dns
    reload(dns)