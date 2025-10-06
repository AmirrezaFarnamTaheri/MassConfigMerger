from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.core.config_processor import ConfigResult
from massconfigmerger.vpn_merger import run_merger


@pytest.mark.asyncio
@patch("massconfigmerger.vpn_merger.Database")
@patch("massconfigmerger.vpn_merger.SourceManager")
@patch("massconfigmerger.vpn_merger.ConfigProcessor")
@patch("massconfigmerger.vpn_merger.OutputGenerator")
@patch("massconfigmerger.vpn_merger.pipeline.test_configs", new_callable=AsyncMock)
@patch("pathlib.Path.open", new_callable=mock_open, read_data="http://source1")
async def test_run_merger_from_sources(
    mock_open_file: MagicMock,
    mock_test_configs: AsyncMock,
    MockOutputGenerator: MagicMock,
    MockConfigProcessor: MagicMock,
    MockSourceManager: MagicMock,
    MockDatabase: MagicMock,
):
    """Test the run_merger function when fetching from sources."""
    # Arrange
    settings = Settings()
    mock_db = MockDatabase.return_value
    mock_db.connect = AsyncMock()
    mock_db.get_proxy_history = AsyncMock(return_value={})
    mock_db.update_proxy_history = AsyncMock()
    mock_db.close = AsyncMock()

    mock_source_manager = MockSourceManager.return_value
    mock_config_processor = MockConfigProcessor.return_value
    mock_output_generator = MockOutputGenerator.return_value

    mock_source_manager.fetch_sources = AsyncMock(
        return_value={"vless://config1", "ss://config2"}
    )
    mock_config_processor.filter_configs.return_value = {
        "vless://config1",
        "ss://config2",
    }
    # Simulate test results: one success, one failure
    mock_test_configs.return_value = [
        ConfigResult(
            config="vless://config1",
            protocol="VLESS",
            ping_time=0.1,
            is_reachable=True,
            host="host1",
            port=443,
        ),
        ConfigResult(
            config="ss://config2",
            protocol="SHADOWSOCKS",
            ping_time=None,
            is_reachable=False,
            host="host2",
            port=443,
        ),
    ]
    mock_source_manager.close_session = AsyncMock()

    with patch("massconfigmerger.processing.pipeline.sort_and_trim_results", side_effect=lambda r, c: sorted(r, key=lambda x: not x.is_reachable)):
        # Act
        await run_merger(settings, Path("sources.txt"))

    # Assert
    mock_db.connect.assert_awaited_once()
    mock_source_manager.fetch_sources.assert_awaited_once_with(["http://source1"])
    mock_config_processor.filter_configs.assert_called_once_with(
        {"vless://config1", "ss://config2"}
    )
    mock_test_configs.assert_awaited_once_with(
        list({"vless://config1", "ss://config2"}), settings, {}
    )
    mock_db.update_proxy_history.assert_awaited()
    # Verify that the final configs are sorted correctly (reachable first)
    mock_output_generator.write_outputs.assert_called_once()
    final_configs = mock_output_generator.write_outputs.call_args[0][0]
    assert final_configs == ["vless://config1", "ss://config2"]

    mock_source_manager.close_session.assert_awaited_once()
    mock_db.close.assert_awaited_once()


@pytest.mark.asyncio
@patch("massconfigmerger.vpn_merger.Database")
@patch("massconfigmerger.vpn_merger.SourceManager")
@patch("massconfigmerger.vpn_merger.ConfigProcessor")
@patch("massconfigmerger.vpn_merger.OutputGenerator")
@patch("massconfigmerger.vpn_merger.pipeline.test_configs", new_callable=AsyncMock)
@patch(
    "pathlib.Path.open", new_callable=mock_open, read_data="vless://resume1\nss://resume2"
)
async def test_run_merger_with_resume(
    mock_open_file: MagicMock,
    mock_test_configs: AsyncMock,
    MockOutputGenerator: MagicMock,
    MockConfigProcessor: MagicMock,
    MockSourceManager: MagicMock,
    MockDatabase: MagicMock,
):
    """Test the run_merger function when resuming from a file."""
    # Arrange
    settings = Settings()
    settings.processing.top_n = 1  # Set top_n in settings
    mock_db = MockDatabase.return_value
    mock_db.connect = AsyncMock()
    mock_db.get_proxy_history = AsyncMock(return_value={})
    mock_db.update_proxy_history = AsyncMock()
    mock_db.close = AsyncMock()

    mock_source_manager = MockSourceManager.return_value
    mock_config_processor = MockConfigProcessor.return_value
    mock_config_processor.filter_configs.return_value = {
        "vless://resume1",
        "ss://resume2",
    }

    mock_test_configs.return_value = [
        ConfigResult(
            config="vless://resume1",
            protocol="VLESS",
            ping_time=0.2,
            is_reachable=True,
            host="host1",
            port=443,
        ),
        ConfigResult(
            config="ss://resume2",
            protocol="SHADOWSOCKS",
            ping_time=0.3,
            is_reachable=True,
            host="host2",
            port=443,
        ),
    ]
    mock_source_manager.close_session = AsyncMock()

    # Act
    with patch("massconfigmerger.processing.pipeline.sort_and_trim_results", side_effect=lambda r, c: sorted(r, key=lambda x: not x.is_reachable)[:c.processing.top_n or None]):
        await run_merger(settings, Path("dummy_sources.txt"), resume_file=Path("resume.txt"))

    # Assert
    mock_db.connect.assert_awaited_once()
    # fetch_sources should not be called
    mock_source_manager.fetch_sources.assert_not_called()

    # filter_configs should be called with the configs from the resume file
    mock_config_processor.filter_configs.assert_called_once_with(
        {"vless://resume1", "ss://resume2"}
    )
    mock_test_configs.assert_awaited_once_with(
        list({"vless://resume1", "ss://resume2"}), settings, {}
    )

    # Check that top_n logic was applied
    mock_output_generator = MockOutputGenerator.return_value
    mock_output_generator.write_outputs.assert_called_once()
    final_configs = mock_output_generator.write_outputs.call_args[0][0]
    assert len(final_configs) == 1
    assert final_configs == ["vless://resume1"]
    mock_db.close.assert_awaited_once()