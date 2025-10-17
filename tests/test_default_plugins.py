import pytest
import aiohttp
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from configstream.plugins.default_plugins import (
    UrlSourcePlugin,
    CountryFilterPlugin,
    LatencyFilterPlugin,
    Base64ExportPlugin,
    ClashExportPlugin,
    RawExportPlugin,
    ProxiesJsonExportPlugin,
    StatsJsonExportPlugin,
)
from configstream.core import Proxy


@pytest.mark.asyncio
async def test_url_source_plugin(aiohttp_client):
    """Test the UrlSourcePlugin."""
    async def handler(request):
        return aiohttp.web.Response(text="proxy1\nproxy2")

    app = aiohttp.web.Application()
    app.router.add_get("/", handler)
    client = await aiohttp_client(app)

    source_url = str(client.server.make_url("/"))
    plugin = UrlSourcePlugin()
    proxies = await plugin.fetch_proxies(source_url)

    assert proxies == ["proxy1", "proxy2"]


@pytest.mark.asyncio
async def test_country_filter_plugin():
    """Test the CountryFilterPlugin."""
    proxies = [
        Proxy(config="p1", protocol="test", address="test.com", port=1, country_code="US"),
        Proxy(config="p2", protocol="test", address="test.com", port=1, country_code="DE"),
        Proxy(config="p3", protocol="test", address="test.com", port=1, country_code="US"),
    ]
    plugin = CountryFilterPlugin("US")
    filtered_proxies = await plugin.filter_proxies(proxies)

    assert len(filtered_proxies) == 2
    assert all(p.country_code == "US" for p in filtered_proxies)


@pytest.mark.asyncio
async def test_latency_filter_plugin():
    """Test the LatencyFilterPlugin."""
    proxies = [
        Proxy(config="p1", protocol="test", address="test.com", port=1, latency=100),
        Proxy(config="p2", protocol="test", address="test.com", port=1, latency=600),
        Proxy(config="p3", protocol="test", address="test.com", port=1, latency=400),
    ]
    plugin = LatencyFilterPlugin(500)
    filtered_proxies = await plugin.filter_proxies(proxies)

    assert len(filtered_proxies) == 2
    assert all(p.latency <= 500 for p in filtered_proxies)


@pytest.mark.asyncio
async def test_base64_export_plugin(tmp_path):
    """Test the Base64ExportPlugin."""
    proxies = [Proxy(config="proxy1", protocol="test", address="test.com", port=1, is_working=True, is_secure=True)]
    plugin = Base64ExportPlugin()
    await plugin.export(proxies, tmp_path)

    output_file = tmp_path / "vpn_subscription_base64.txt"
    assert output_file.exists()
    assert output_file.read_text() == "cHJveHkx"


@pytest.mark.asyncio
async def test_clash_export_plugin(tmp_path):
    """Test the ClashExportPlugin."""
    proxies = [Proxy(config="vmess://test", protocol="vmess", remarks="test", address="test.com", port=443, uuid="uuid", _details={}, is_working=True, is_secure=True)]
    plugin = ClashExportPlugin()
    await plugin.export(proxies, tmp_path)

    output_file = tmp_path / "clash.yaml"
    assert output_file.exists()
    assert "name: test" in output_file.read_text()


@pytest.mark.asyncio
async def test_raw_export_plugin(tmp_path):
    """Test the RawExportPlugin."""
    proxies = [Proxy(config="proxy1", protocol="test", address="test.com", port=1, is_working=True, is_secure=True)]
    plugin = RawExportPlugin()
    await plugin.export(proxies, tmp_path)

    output_file = tmp_path / "configs_raw.txt"
    assert output_file.exists()
    assert output_file.read_text() == "proxy1"


@pytest.mark.asyncio
async def test_proxies_json_export_plugin(tmp_path):
    """Test the ProxiesJsonExportPlugin."""
    proxies = [Proxy(config="proxy1", protocol="vmess", remarks="test", address="test.com", port=443, latency=100, is_working=True, is_secure=True, security_issues=[], tested_at="now", country="US", country_code="US", city="Test", asn="AS123", asn_number=123)]
    plugin = ProxiesJsonExportPlugin()
    await plugin.export(proxies, tmp_path)

    output_file = tmp_path / "proxies.json"
    assert output_file.exists()
    assert '"protocol": "vmess"' in output_file.read_text()


@pytest.mark.asyncio
async def test_stats_json_export_plugin(tmp_path):
    """Test the StatsJsonExportPlugin."""
    proxies = [Proxy(config="proxy1", protocol="vmess", address="test.com", port=1, country_code="US", is_working=True, is_secure=True, latency=100)]
    plugin = StatsJsonExportPlugin()
    await plugin.export(proxies, tmp_path)

    output_file = tmp_path / "statistics.json"
    assert output_file.exists()
    assert '"total_tested": 1' in output_file.read_text()