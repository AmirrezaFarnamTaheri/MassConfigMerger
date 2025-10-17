import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from rich.progress import Progress

from src.configstream.pipeline import run_full_pipeline
from src.configstream.core import Proxy


@pytest.fixture
def mock_progress():
    """Fixture for a mock Rich Progress object."""
    progress = MagicMock(spec=Progress)
    progress.add_task.return_value = 1
    progress.console = MagicMock()
    return progress


@pytest.mark.asyncio
@patch("src.configstream.pipeline.fetch_configs", new_callable=AsyncMock)
@patch("src.configstream.pipeline.parse_config")
@patch("src.configstream.pipeline.ProxyTester")
async def test_run_full_pipeline_success(
    mock_proxy_tester,
    mock_parse_config,
    mock_fetch_configs,
    mock_progress,
    tmp_path,
):
    """Test the full pipeline with a successful run."""
    # Arrange
    sources = ["http://source1.com"]
    output_dir = tmp_path

    # Mock fetching
    mock_fetch_configs.return_value = ["proxy1", "proxy2"]

    # Mock parsing
    proxy_obj1 = Proxy(config="proxy1", protocol="vmess", address="1.1.1.1", port=443)
    proxy_obj2 = Proxy(config="proxy2", protocol="vless", address="2.2.2.2", port=443)
    mock_parse_config.side_effect = [proxy_obj1, proxy_obj2]

    # Mock testing
    mock_tester_instance = mock_proxy_tester.return_value
    async def test_side_effect(proxy):
        proxy.is_working = True
        proxy.latency = 100
        return proxy
    mock_tester_instance.test.side_effect = test_side_effect

    # Act
    await run_full_pipeline(sources, str(output_dir), mock_progress)

    # Assert
    mock_fetch_configs.assert_called_once()
    assert mock_parse_config.call_count == 2
    assert mock_tester_instance.test.call_count == 2
    assert (output_dir / "proxies.json").exists()
    assert (output_dir / "statistics.json").exists()


@pytest.mark.asyncio
@patch("src.configstream.pipeline.fetch_configs", new_callable=AsyncMock)
async def test_run_full_pipeline_no_configs_fetched(mock_fetch_configs, mock_progress):
    """Test the pipeline when no configurations are fetched."""
    # Arrange
    mock_fetch_configs.return_value = []

    # Act
    await run_full_pipeline(["http://source.com"], "/tmp", mock_progress)

    # Assert
    mock_progress.console.print.assert_called_with("[bold red]No configurations fetched. Exiting.[/bold red]")


@pytest.mark.asyncio
@patch("src.configstream.pipeline.fetch_configs", new_callable=AsyncMock)
@patch("src.configstream.pipeline.parse_config")
@patch("src.configstream.pipeline.ProxyTester")
async def test_run_full_pipeline_no_working_proxies(
    mock_proxy_tester,
    mock_parse_config,
    mock_fetch_configs,
    mock_progress,
    tmp_path: Path,
):
    """Test the pipeline when proxies are fetched but none are working."""
    # Arrange
    mock_fetch_configs.return_value = ["proxy1"]
    mock_parse_config.return_value = Proxy(config="proxy1", protocol="test", address="test.com", port=1)

    mock_tester_instance = mock_proxy_tester.return_value
    async def test_side_effect(proxy):
        proxy.is_working = False
        return proxy
    mock_tester_instance.test.side_effect = test_side_effect

    # Act
    await run_full_pipeline(["http://source.com"], str(tmp_path), mock_progress)

    # Assert
    assert mock_tester_instance.test.call_count == 1
    # Check that the stats file reflects 0 working proxies
    stats_content = (tmp_path / "statistics.json").read_text()
    import json
    stats_data = json.loads(stats_content)
    assert stats_data["working"] == 0
    assert stats_data["total_tested"] == 1