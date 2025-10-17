
import aiohttp
import pytest

from configstream.core import Proxy
from configstream.plugins.default_plugins import (Base64ExportPlugin,
                                                  ClashExportPlugin,
                                                  CountryFilterPlugin,
                                                  LatencyFilterPlugin,
                                                  UrlSourcePlugin)


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
        Proxy(config="p1", protocol="vmess", address="1.1.1.1", port=443, country_code="US"),
        Proxy(config="p2", protocol="vless", address="2.2.2.2", port=443, country_code="DE"),
        Proxy(config="p3", protocol="ss", address="3.3.3.3", port=443, country_code="US"),
    ]
    plugin = CountryFilterPlugin("US")
    filtered_proxies = await plugin.filter_proxies(proxies)

    assert len(filtered_proxies) == 2
    assert all(p.country_code == "US" for p in filtered_proxies)


@pytest.mark.asyncio
async def test_latency_filter_plugin():
    """Test the LatencyFilterPlugin."""
    proxies = [
        Proxy(config="p1", protocol="vmess", address="1.1.1.1", port=443, latency=100),
        Proxy(config="p2", protocol="vless", address="2.2.2.2", port=443, latency=600),
        Proxy(config="p3", protocol="ss", address="3.3.3.3", port=443, latency=400),
    ]
    plugin = LatencyFilterPlugin(500)
    filtered_proxies = await plugin.filter_proxies(proxies)

    assert len(filtered_proxies) == 2
    assert all(p.latency <= 500 for p in filtered_proxies)


@pytest.mark.asyncio
async def test_base64_export_plugin(tmp_path):
    """Test the Base64ExportPlugin."""
    proxies = [
        Proxy(
            config="proxy1",
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            is_working=True,
            is_secure=True,
        )
    ]
    plugin = Base64ExportPlugin()
    await plugin.export(proxies, tmp_path)

    output_file = tmp_path / "vpn_subscription_base64.txt"
    assert output_file.exists()
    assert output_file.read_text() == "cHJveHkx"


@pytest.mark.asyncio
async def test_clash_export_plugin(tmp_path):
    """Test the ClashExportPlugin."""
    proxies = [
        Proxy(
            config="vmess://test",
            protocol="vmess",
            remarks="test",
            address="test.com",
            port=443,
            uuid="uuid",
            _details={},
            is_working=True,
            is_secure=True,
        )
    ]
    plugin = ClashExportPlugin()
    await plugin.export(proxies, tmp_path)

    output_file = tmp_path / "clash.yaml"
    assert output_file.exists()
    assert "name: test" in output_file.read_text()
