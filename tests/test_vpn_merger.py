from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from massconfigmerger.config import Settings
from massconfigmerger.vpn_merger import run_merger


@pytest.mark.asyncio
@patch("massconfigmerger.vpn_merger.SourceManager")
@patch("massconfigmerger.vpn_merger.ConfigProcessor")
@patch("massconfigmerger.vpn_merger.OutputGenerator")
@patch("pathlib.Path.open", new_callable=mock_open, read_data="http://source1")
async def test_run_merger_from_sources(
    mock_open_file: MagicMock,
    MockOutputGenerator: MagicMock,
    MockConfigProcessor: MagicMock,
    MockSourceManager: MagicMock,
):
    """Test the run_merger function when fetching from sources."""
    # Arrange
    settings = Settings()
    mock_source_manager = MockSourceManager.return_value
    mock_config_processor = MockConfigProcessor.return_value
    mock_output_generator = MockOutputGenerator.return_value

    mock_source_manager.fetch_sources = AsyncMock(return_value={"vless://config1", "ss://config2"})
    mock_config_processor.filter_configs.return_value = {"vless://config1", "ss://config2"}
    # Simulate test results: one success, one failure
    mock_config_processor.test_configs = AsyncMock(return_value=[
        ("vless://config1", 0.1),
        ("ss://config2", None),
    ])
    mock_source_manager.close_session = AsyncMock()

    # Act
    await run_merger(settings, Path("sources.txt"))

    # Assert
    mock_source_manager.fetch_sources.assert_awaited_once_with(["http://source1"])
    mock_config_processor.filter_configs.assert_called_once_with(
        {"vless://config1", "ss://config2"}, None
    )
    mock_config_processor.test_configs.assert_awaited_once_with({"vless://config1", "ss://config2"})

    # Verify that the final configs are sorted correctly (None pings last)
    mock_output_generator.write_outputs.assert_called_once()
    final_configs = mock_output_generator.write_outputs.call_args[0][0]
    assert final_configs == ["vless://config1", "ss://config2"]

    mock_source_manager.close_session.assert_awaited_once()


@pytest.mark.asyncio
@patch("massconfigmerger.vpn_merger.SourceManager")
@patch("massconfigmerger.vpn_merger.ConfigProcessor")
@patch("massconfigmerger.vpn_merger.OutputGenerator")
@patch("pathlib.Path.open", new_callable=mock_open, read_data="vless://resume1\nss://resume2")
async def test_run_merger_with_resume(
    mock_open_file: MagicMock,
    MockOutputGenerator: MagicMock,
    MockConfigProcessor: MagicMock,
    MockSourceManager: MagicMock,
):
    """Test the run_merger function when resuming from a file."""
    # Arrange
    settings = Settings()
    mock_source_manager = MockSourceManager.return_value
    mock_config_processor = MockConfigProcessor.return_value

    mock_config_processor.test_configs = AsyncMock(return_value=[("vless://resume1", 0.2)])
    mock_source_manager.close_session = AsyncMock()

    # Act
    await run_merger(settings, Path("dummy_sources.txt"), resume_file=Path("resume.txt"), top_n=1)

    # Assert
    # fetch_sources should not be called
    MockSourceManager.return_value.fetch_sources.assert_not_called()

    # filter_configs should be called with the configs from the resume file
    mock_config_processor.filter_configs.assert_called_once_with(
        {"vless://resume1", "ss://resume2"}, None
    )

    # Check that top_n logic was applied
    mock_output_generator = MockOutputGenerator.return_value
    mock_output_generator.write_outputs.assert_called_once()
    final_configs = mock_output_generator.write_outputs.call_args[0][0]
    assert len(final_configs) == 1
    assert final_configs == ["vless://resume1"]