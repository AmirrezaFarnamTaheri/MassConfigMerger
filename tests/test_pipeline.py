from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.progress import Progress

from configstream.core import Proxy
from configstream.pipeline import run_full_pipeline


@pytest.fixture
def mock_progress():
    """Fixture for a mock Rich Progress object."""
    progress = MagicMock(spec=Progress)
    progress.add_task = MagicMock(return_value=1)
    progress.update = MagicMock()
    return progress


def create_proxy(config, is_working=False, latency=None):
    """Helper to create valid Proxy objects for tests."""
    return Proxy(
        config=config,
        protocol="test",
        address="1.2.3.4",
        port=80,
        is_working=is_working,
        latency=latency,
    )


@patch("configstream.pipeline.RateLimiter")
@patch("configstream.pipeline.MaliciousNodeDetector")
@patch("configstream.pipeline.SingBoxTester")
@patch("configstream.pipeline.fetch_configs", new_callable=AsyncMock)
@patch("configstream.pipeline.parse_config")
@patch("configstream.pipeline.geolocate_proxy")
@pytest.mark.asyncio
async def test_run_full_pipeline_success(
    mock_geolocate,
    mock_parse,
    mock_fetch,
    mock_tester,
    mock_detector,
    mock_ratelimiter,
    mock_progress,
    tmp_path,
):
    """
    Test the full pipeline with a mix of working, non-working, and malicious proxies.
    """
    # Arrange
    mock_ratelimiter.return_value.is_allowed.return_value = True
    sources = ["http://source1.com"]
    output_dir = str(tmp_path)

    mock_fetch.return_value = ["c1", "c2", "c3"]
    proxies_in = [create_proxy("c1"), create_proxy("c2"), create_proxy("c3")]
    mock_parse.side_effect = proxies_in
    mock_geolocate.side_effect = lambda p, r: p

    async def mock_test_side_effect(proxy):
        if proxy.config == "c1":
            proxy.is_working = True
            proxy.latency = 100
        return proxy

    mock_tester.return_value.test = AsyncMock(side_effect=mock_test_side_effect)

    mock_detector.return_value.detect_malicious = AsyncMock(return_value={"is_malicious": False})

    # Act
    await run_full_pipeline(sources, output_dir, mock_progress)

    # Assert
    assert mock_fetch.call_count == 1
    assert mock_parse.call_count == 3
    assert mock_tester.return_value.test.call_count == 3
    assert mock_detector.return_value.detect_malicious.call_count == 1

    clash_config = (tmp_path / "clash.yaml").read_text()
    # Check for the generated proxy name, not the raw config string
    assert "test-1.2.3.4" in clash_config
    assert "c2" not in clash_config


@patch("configstream.pipeline.RateLimiter")
@patch("configstream.pipeline.MaliciousNodeDetector")
@patch("configstream.pipeline.SingBoxTester")
@patch("configstream.pipeline.fetch_configs", new_callable=AsyncMock)
@patch("configstream.pipeline.parse_config")
@patch("configstream.pipeline.geolocate_proxy")
@pytest.mark.asyncio
async def test_run_full_pipeline_malicious_proxy(
    mock_geolocate,
    mock_parse,
    mock_fetch,
    mock_tester,
    mock_detector,
    mock_ratelimiter,
    mock_progress,
    tmp_path,
):
    """
    Test that a proxy flagged as malicious is filtered out.
    """
    # Arrange
    mock_ratelimiter.return_value.is_allowed.return_value = True
    mock_fetch.return_value = ["config1"]
    mock_parse.return_value = create_proxy("c1")
    mock_geolocate.side_effect = lambda p, r: p

    # Correctly mock the async methods to return awaitables
    mock_tester.return_value.test = AsyncMock(
        return_value=create_proxy("c1", is_working=True, latency=100)
    )
    mock_detector.return_value.detect_malicious = AsyncMock(
        return_value={"is_malicious": True, "severity": "critical", "tests": []}
    )

    # Act
    await run_full_pipeline(["http://source.com"], str(tmp_path), mock_progress)

    # Assert
    assert mock_detector.return_value.detect_malicious.call_count == 1
    clash_config = (tmp_path / "clash.yaml").read_text()
    assert "proxies: []" in clash_config

    stats_file = (tmp_path / "statistics.json").read_text()
    import json

    stats = json.loads(stats_file)
    assert stats["working"] == 0
    assert stats["failed"] == 1
