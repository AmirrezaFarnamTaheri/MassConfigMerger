import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from rich.progress import Progress

from configstream.pipeline import run_full_pipeline
from configstream.core import Proxy


@pytest.fixture
def mock_progress():
    progress = MagicMock(spec=Progress)
    progress.console = MagicMock()
    return progress


@pytest.mark.asyncio
@patch("configstream.pipeline.fetch_configs")
@patch("configstream.pipeline.parse_config")
@patch("configstream.pipeline.SingBoxTester")
async def test_run_full_pipeline_success(
    mock_tester,
    mock_parse_config,
    mock_fetch_configs,
    mock_progress,
    tmp_path,
):
    """Test the full pipeline with successful execution."""
    # Arrange
    sources = ["http://source1.com", "http://source2.com"]
    output_dir = str(tmp_path)

    mock_fetch_configs.side_effect = [["proxy1"], ["proxy2"]]

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
    assert mock_fetch_configs.call_count == 2
    assert mock_parse_config.call_count == 2
    assert mock_tester_instance.test.call_count == 2
    assert (tmp_path / "clash.yaml").exists()


@pytest.mark.asyncio
@patch("configstream.pipeline.fetch_configs")
async def test_run_full_pipeline_no_configs_fetched(mock_fetch_configs, mock_progress, tmp_path):
    """Test pipeline when no configs are fetched."""
    mock_fetch_configs.return_value = []
    output_dir = str(tmp_path)

    await run_full_pipeline(["http://source.com"], output_dir, mock_progress)

    assert (tmp_path / "clash.yaml").read_text() == "proxies: []\nproxy-groups:\n- name: \"\\U0001F680 ConfigStream\"\n  proxies: []\n  type: select\n"


@pytest.mark.asyncio
@patch("configstream.pipeline.fetch_configs")
@patch("configstream.pipeline.parse_config")
@patch("configstream.pipeline.SingBoxTester")
async def test_run_full_pipeline_no_working_proxies(
    mock_tester,
    mock_parse_config,
    mock_fetch_configs,
    mock_progress,
    tmp_path
):
    """Test pipeline when no working proxies are found after filtering."""
    mock_fetch_configs.return_value = ["proxy1"]

    mock_parse_config.return_value = Proxy(config="proxy1", protocol="vmess", address="1.1.1.1", port=443)

    mock_tester_instance = mock_tester.return_value
    mock_tester_instance.test = AsyncMock(return_value=Proxy(config="proxy1", protocol="vmess", address="1.1.1.1", port=443, is_working=False, latency=1000))

    await run_full_pipeline(
        sources=["http://source.com"],
        output_dir=str(tmp_path),
        progress=mock_progress,
        max_latency=500
    )

    assert mock_tester_instance.test.call_count == 1
    assert not (tmp_path / "clash.yaml").exists() or (tmp_path / "clash.yaml").read_text() == "proxies: []\nproxy-groups:\n- name: \"\\U0001F680 ConfigStream\"\n  proxies: []\n  type: select\n"