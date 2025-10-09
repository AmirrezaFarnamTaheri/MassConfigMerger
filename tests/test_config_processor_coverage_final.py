from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from configstream.config import Settings
from configstream.core.config_processor import ConfigProcessor, ConfigResult
from configstream.db import Database


@pytest.fixture
def settings() -> Settings:
    """Fixture for a Settings instance."""
    return Settings()


@pytest.fixture
def processor(settings: Settings) -> ConfigProcessor:
    """Fixture for a ConfigProcessor instance."""
    return ConfigProcessor(settings)


@pytest.mark.asyncio
async def test_filter_malicious_not_reachable(processor: ConfigProcessor):
    """Test that _filter_malicious correctly handles non-reachable results."""
    results = [ConfigResult(config="c1", protocol="p1", is_reachable=False)]
    filtered = await processor._filter_malicious(results)
    assert len(filtered) == 1
    assert filtered[0].config == "c1"


@pytest.mark.asyncio
async def test_filter_malicious_is_malicious(settings: Settings):
    """Test that _filter_malicious removes malicious results."""
    # Enable the security check
    settings.security.apivoid_api_key = "test_key"
    settings.security.blocklist_detection_threshold = 1
    processor = ConfigProcessor(settings)

    # Mock the dependencies
    processor.tester.resolve_host = AsyncMock(return_value="1.2.3.4")
    processor.blocklist_checker.is_malicious = AsyncMock(return_value=True)

    results = [
        ConfigResult(
            config="c1", protocol="p1", is_reachable=True, host="malicious.com"
        )
    ]
    filtered = await processor._filter_malicious(results)
    assert len(filtered) == 0


@pytest.mark.asyncio
async def test_write_history_batch(processor: ConfigProcessor):
    """Test the write_history_batch method."""
    mock_db = MagicMock(spec=Database)
    mock_db.add_proxy_history_batch = AsyncMock()

    batch_data = [("key1", True), ("key2", False)]
    processor.history_batch = list(batch_data)  # Use a copy

    await processor.write_history_batch(mock_db)

    # Assert that the mock was called correctly
    mock_db.add_proxy_history_batch.assert_awaited_once()
    call_args, _ = mock_db.add_proxy_history_batch.await_args
    assert call_args[0] == batch_data

    # Assert that the batch was cleared
    assert not processor.history_batch
