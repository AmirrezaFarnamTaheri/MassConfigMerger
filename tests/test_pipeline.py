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
@patch("src.configstream.pipeline._fetch_all_sources", new_callable=AsyncMock)
@patch("src.configstream.pipeline.parse_config")
@patch("src.configstream.pipeline.process_and_test_proxies", new_callable=AsyncMock)
@patch("src.configstream.core.generate_base64_subscription")
@patch("src.configstream.core.generate_clash_config")
@patch("src.configstream.core.generate_raw_configs")
@patch("src.configstream.core.generate_proxies_json")
@patch("src.configstream.core.generate_statistics_json")
async def test_run_full_pipeline_success(
    mock_stats_json,
    mock_proxies_json,
    mock_raw_configs,
    mock_clash_config,
    mock_base64_sub,
    mock_process_and_test,
    mock_parse_config,
    mock_fetch,
    mock_progress,
    tmp_path,
):
    """Test the full pipeline with successful execution."""
    # Arrange
    sources = ["http://source1.com"]
    output_dir = str(tmp_path)

    mock_fetch.return_value = ["proxy1", "proxy2"]

    proxy_obj1 = Proxy(config="proxy1", protocol="vmess", address="1.1.1.1", port=443)
    proxy_obj2 = Proxy(config="proxy2", protocol="vless", address="2.2.2.2", port=443)
    mock_parse_config.side_effect = [proxy_obj1, proxy_obj2]

    tested_proxy1 = Proxy(config="proxy1", protocol="vmess", address="1.1.1.1", port=443, is_working=True, latency=100)
    tested_proxy2 = Proxy(config="proxy2", protocol="vless", address="2.2.2.2", port=443, is_working=False)
    mock_process_and_test.return_value = [tested_proxy1, tested_proxy2]

    # Act
    await run_full_pipeline(sources, output_dir, mock_progress)

    # Assert
    mock_fetch.assert_called_once_with(sources, mock_progress)
    assert mock_parse_config.call_count == 2
    mock_process_and_test.assert_called_once()

    # Check that output files were generated
    output_path = Path(output_dir)
    assert (output_path / "vpn_subscription_base64.txt").exists()
    assert (output_path / "clash.yaml").exists()
    assert (output_path / "configs_raw.txt").exists()
    assert (output_path / "proxies.json").exists()
    assert (output_path / "statistics.json").exists()
    assert (output_path / "metadata.json").exists()


@pytest.mark.asyncio
@patch("src.configstream.pipeline._fetch_all_sources", new_callable=AsyncMock)
async def test_run_full_pipeline_no_configs_fetched(mock_fetch, mock_progress):
    """Test pipeline when no configs are fetched."""
    mock_fetch.return_value = []

    await run_full_pipeline(["http://source.com"], "/tmp", mock_progress)

    mock_progress.console.print.assert_called_with("[bold red]No configurations fetched. Exiting.[/bold red]")


@pytest.mark.asyncio
@patch("src.configstream.pipeline._fetch_all_sources", new_callable=AsyncMock)
@patch("src.configstream.pipeline.parse_config")
@patch("src.configstream.pipeline.process_and_test_proxies", new_callable=AsyncMock)
async def test_run_full_pipeline_no_working_proxies(
    mock_process_and_test,
    mock_parse_config,
    mock_fetch,
    mock_progress,
    tmp_path
):
    """Test pipeline when no working proxies are found after filtering."""
    mock_fetch.return_value = ["proxy1"]
    mock_parse_config.return_value = Proxy(config="proxy1")
    mock_process_and_test.return_value = [Proxy(config="proxy1", is_working=True, is_secure=True, latency=1000)]

    await run_full_pipeline(
        sources=["http://source.com"],
        output_dir=str(tmp_path),
        progress=mock_progress,
        max_latency=500
    )

    mock_progress.console.print.assert_any_call("[bold yellow]No working proxies after filtering.[/bold yellow]")