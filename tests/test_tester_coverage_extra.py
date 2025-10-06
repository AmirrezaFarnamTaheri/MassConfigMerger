from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.testing import DNSResolver, GeoIPLookup, NodeTester


@pytest.fixture
def mock_settings(tmp_path):
    """Fixture for mock settings."""
    settings = Settings()
    settings.processing.geoip_db = str(tmp_path / "GeoLite2-City.mmdb")
    return settings


@pytest.mark.asyncio
async def test_geoip_import_error(mock_settings):
    """Test that GeoIPLookup handles ImportError for geoip2."""
    with patch.dict(sys.modules, {"geoip2": None}):
        from importlib import reload
        from massconfigmerger.testing import geoip

        reload(geoip)

        resolver = DNSResolver()
        lookup = geoip.GeoIPLookup(mock_settings, resolver)
        assert lookup._get_reader() is None

    # Restore by reloading again outside the patch context
    from importlib import reload
    from massconfigmerger.testing import geoip

    reload(geoip)


@pytest.mark.asyncio
async def test_lookup_geo_data_cache_hit(mock_settings):
    """Test that geoip lookups are cached."""
    tester = NodeTester(mock_settings)
    host = "example.com"
    mock_geo_data = ("US", "Test ISP", 38.0, -97.0)

    tester.geoip_lookup.geoip_cache[host] = mock_geo_data

    result = await tester.lookup_geo_data(host)
    assert result == mock_geo_data

    with patch.object(tester.resolver, "resolve", new_callable=AsyncMock) as mock_resolve:
        await tester.lookup_geo_data(host)
        mock_resolve.assert_not_awaited()


@pytest.mark.asyncio
async def test_lookup_geo_data_country_db_fallback(mock_settings, monkeypatch):
    """Test the fallback to country DB if city DB is not available."""
    mock_reader_instance = MagicMock()
    mock_country_response = MagicMock()
    mock_country_response.country.iso_code = "DE"
    mock_reader_instance.country.return_value = mock_country_response
    del mock_reader_instance.city

    mock_reader = MagicMock(return_value=mock_reader_instance)
    monkeypatch.setattr("massconfigmerger.testing.geoip.Reader", mock_reader)

    tester = NodeTester(mock_settings)
    tester.resolver.resolve = AsyncMock(return_value="1.1.1.1")

    country, isp, lat, lon = await tester.lookup_geo_data("example.com")

    assert country == "DE"
    assert isp is None
    assert lat is None
    assert lon is None
    assert "example.com" in tester.geoip_lookup.geoip_cache
    assert tester.geoip_lookup.geoip_cache["example.com"] == ("DE", None, None, None)