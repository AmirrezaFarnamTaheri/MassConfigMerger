import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from rich.progress import Progress

from src.configstream.pipeline import run_full_pipeline
from src.configstream.core import Proxy


@pytest.fixture
def mock_progress():
    progress = MagicMock(spec=Progress)
    progress.console = MagicMock()
    return progress


@pytest.mark.asyncio
@patch("src.configstream.pipeline.PluginManager")
@patch("src.configstream.pipeline.parse_config")
@patch("src.configstream.pipeline.SingBoxTester")
async def test_run_full_pipeline_success(
    mock_tester,
    mock_parse_config,
    mock_plugin_manager,
    mock_progress,
    tmp_path,
):
    """Test the full pipeline with successful execution."""
    # Arrange
    sources = ["http://source1.com", "http://source2.com"]
    output_dir = str(tmp_path)

    # Mock the plugin manager and its plugins
    mock_pm_instance = mock_plugin_manager.return_value
    mock_source_plugin = AsyncMock()
    mock_source_plugin.fetch_proxies.side_effect = [["proxy1"], ["proxy2"]]
    mock_pm_instance.source_plugins = {"url_source": mock_source_plugin}

    mock_export_plugin = AsyncMock()
    mock_pm_instance.export_plugins = {
        "base64_export": mock_export_plugin,
        "clash_export": mock_export_plugin,
        "raw_export": mock_export_plugin,
        "proxies_json_export": mock_export_plugin,
        "stats_json_export": mock_export_plugin,
    }

    proxy_obj1 = Proxy(config="proxy1", protocol="vmess", address="1.1.1.1", port=443)
    proxy_obj2 = Proxy(config="proxy2", protocol="vless", address="2.2.2.2", port=443)
    mock_parse_config.side_effect = [proxy_obj1, proxy_obj2]

    # Mock the tester
    mock_tester_instance = mock_tester.return_value
    async def test_side_effect(proxy):
        if proxy.config == "proxy1":
            proxy.is_working = True
            proxy.latency = 100
        else:
            proxy.is_working = False
        return proxy
    mock_tester_instance.test.side_effect = test_side_effect

    # Act
    await run_full_pipeline(sources, output_dir, mock_progress)

    # Assert
    assert mock_source_plugin.fetch_proxies.call_count == 2
    assert mock_parse_config.call_count == 2
    assert mock_tester_instance.test.call_count == 2
    assert mock_export_plugin.export.call_count == 5


@pytest.mark.asyncio
@patch("src.configstream.pipeline.PluginManager")
async def test_run_full_pipeline_no_configs_fetched(mock_plugin_manager, mock_progress):
    """Test pipeline when no configs are fetched."""
    mock_pm_instance = mock_plugin_manager.return_value
    mock_source_plugin = AsyncMock()
    mock_source_plugin.fetch_proxies.return_value = []
    mock_pm_instance.source_plugins = {"url_source": mock_source_plugin}

    await run_full_pipeline(["http://source.com"], "/tmp", mock_progress)

    mock_progress.console.print.assert_called_with("[bold red]No configurations fetched. Exiting.[/bold red]")


@pytest.mark.asyncio
@patch("src.configstream.pipeline.PluginManager")
@patch("src.configstream.pipeline.parse_config")
@patch("src.configstream.pipeline.SingBoxTester")
async def test_run_full_pipeline_no_working_proxies(
    mock_tester,
    mock_parse_config,
    mock_plugin_manager,
    mock_progress,
    tmp_path
):
    """Test pipeline when no working proxies are found after filtering."""
    mock_pm_instance = mock_plugin_manager.return_value
    mock_source_plugin = AsyncMock()
    mock_source_plugin.fetch_proxies.return_value = ["proxy1"]
    mock_pm_instance.source_plugins = {"url_source": mock_source_plugin}

    mock_filter_plugin = AsyncMock()
    mock_filter_plugin.filter_proxies.return_value = []
    mock_pm_instance.filter_plugins = {"latency_filter": mock_filter_plugin}

    mock_export_plugin = AsyncMock()
    mock_pm_instance.export_plugins = {
        "base64_export": mock_export_plugin,
        "clash_export": mock_export_plugin,
        "raw_export": mock_export_plugin,
        "proxies_json_export": mock_export_plugin,
        "stats_json_export": mock_export_plugin,
    }

    mock_parse_config.return_value = Proxy(config="proxy1")

    mock_tester_instance = mock_tester.return_value
    mock_tester_instance.test = AsyncMock(return_value=Proxy(config="proxy1", is_working=True, latency=1000))

    await run_full_pipeline(
        sources=["http://source.com"],
        output_dir=str(tmp_path),
        progress=mock_progress,
        max_latency=500
    )

    assert mock_tester_instance.test.call_count == 1
    assert mock_export_plugin.export.call_count == 5