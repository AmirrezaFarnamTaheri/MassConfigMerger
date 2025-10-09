from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.config import Settings
from configstream.tester import NodeTester


@pytest.fixture
def mock_settings(tmp_path):
    """Fixture for mock settings."""
    settings = Settings()
    settings.processing.geoip_db = str(tmp_path / "GeoLite2-City.mmdb")
    return settings


@pytest.mark.asyncio
async def test_geoip_import_error(mock_settings):
    """Test that NodeTester handles ImportError for geoip2."""
    with patch.dict(sys.modules, {"geoip2": None}):
        # We need to re-import the module to trigger the ImportError handling
        from importlib import reload
        from configstream import tester as t
        reload(t)

        # Now create an instance of the reloaded NodeTester
        tester_instance = t.NodeTester(mock_settings)
        assert tester_instance._get_geoip_reader() is None

        # Restore original module
        reload(t)


@pytest.mark.asyncio
async def test_lookup_geo_data_cache_hit(mock_settings):
    """Test that geoip lookups are cached."""
    tester = NodeTester(mock_settings)
    host = "example.com"
    mock_geo_data = ("US", "Test ISP", 38.0, -97.0)

    tester.geoip_cache[host] = mock_geo_data

    result = await tester.lookup_geo_data(host)

    assert result == mock_geo_data


@pytest.mark.asyncio
async def test_lookup_geo_data_country_db_fallback(mock_settings, monkeypatch):
    """Test the fallback to country DB if city DB is not available."""
    mock_reader_instance = MagicMock()

    # Mock the country response
    mock_country_response = MagicMock()
    mock_country_response.country.iso_code = "DE"
    mock_reader_instance.country.return_value = mock_country_response

    # Remove the 'city' attribute to simulate a country-only DB
    del mock_reader_instance.city

    mock_reader = MagicMock(return_value=mock_reader_instance)
    monkeypatch.setattr("configstream.tester.Reader", mock_reader)

    tester = NodeTester(mock_settings)
    tester.resolve_host = AsyncMock(return_value="1.1.1.1")

    country, isp, lat, lon = await tester.lookup_geo_data("example.com")

    assert country == "DE"
    assert isp is None
    assert lat is None
    assert lon is None

    # Ensure it was cached
    assert "example.com" in tester.geoip_cache
    assert tester.geoip_cache["example.com"] == ("DE", None, None, None)
