from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.config import Settings
from configstream.core.config_processor import ConfigProcessor
from configstream.core.types import ConfigResult
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
async def test_run_security_checks_not_reachable(processor: ConfigProcessor):
    """Test that _run_security_checks correctly handles non-reachable results."""
    results = [ConfigResult(config="c1", protocol="p1", is_reachable=False)]
    filtered = await processor._run_security_checks(results)
    assert len(filtered) == 1
    assert filtered[0].config == "c1"


@pytest.mark.asyncio
async def test_run_security_checks_is_malicious(settings: Settings):
    """Test that _run_security_checks removes malicious results."""
    # Enable the security check
    settings.security.api_keys = {"abuseipdb": "test-key"}
    processor = ConfigProcessor(settings)

    # Mock the dependencies
    with patch("configstream.security.ip_reputation.IPReputationChecker.check_all", new_callable=AsyncMock) as mock_check:
        from configstream.security.ip_reputation import ReputationResult, ReputationScore
        mock_check.return_value = ReputationResult(score=ReputationScore.MALICIOUS)
        results = [
            ConfigResult(
                config="c1", protocol="p1", is_reachable=True, host="malicious.com"
            )
        ]
        filtered = await processor._run_security_checks(results)
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
