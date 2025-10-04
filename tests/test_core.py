import asyncio
import base64
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from massconfigmerger.config import Settings
from massconfigmerger.core.config_processor import ConfigProcessor
from massconfigmerger.core.output_generator import OutputGenerator
from massconfigmerger.core.source_manager import SourceManager

# --- Valid Configs for Testing ---
VMESS_CONFIG_PAYLOAD = json.dumps(
    {
        "add": "1.1.1.1",
        "port": 80,
        "id": "a3b8e-8c6f-4d2b-a1e0-b9c2f3a7e4d2",
        "ps": "test-vmess",
        "tls": "none",
        "net": "ws",
        "path": "/",
        "v": "2",
    }
).encode()
VALID_VMESS = f"vmess://{base64.b64encode(VMESS_CONFIG_PAYLOAD).decode()}"
VALID_VLESS = "vless://a3b8e-8c6f-4d2b-a1e0-b9c2f3a7e4d2@1.1.1.2:443?security=tls&sni=example.com#test-vless"
VALID_TROJAN = "trojan://password@1.1.1.3:443?sni=example.com#test-trojan"


@pytest.fixture
def settings():
    """Return a default Settings object for tests."""
    return Settings()


@pytest.mark.asyncio
async def test_source_manager_fetch_sources(settings):
    """Test that the SourceManager can fetch and parse sources."""
    source_manager = SourceManager(settings)
    sources = ["http://example.com/sub1"]

    # Correctly mock the async context manager for aiohttp session
    mock_response = MagicMock()
    mock_response.text = AsyncMock(return_value=VALID_VMESS)
    mock_response.status = 200

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession", return_value=mock_session):
        configs = await source_manager.fetch_sources(sources)
        assert VALID_VMESS in configs


@pytest.mark.asyncio
async def test_source_manager_check_and_update_sources(settings, tmp_path):
    """Test that the SourceManager can check and update sources."""
    source_manager = SourceManager(settings)
    sources_file = tmp_path / "sources.txt"
    sources_file.write_text("http://example.com/sub1\nhttp://example.com/sub2")

    mock_response_ok = MagicMock()
    mock_response_ok.text = AsyncMock(return_value=VALID_VMESS)
    mock_response_ok.status = 200
    mock_response_fail = MagicMock()
    mock_response_fail.text = AsyncMock(return_value="")
    mock_response_fail.status = 404

    mock_session = MagicMock()
    # Configure the mock to return different responses for different calls
    mock_session.get.return_value.__aenter__.side_effect = [
        mock_response_ok,
        mock_response_fail,
    ]

    with patch("aiohttp.ClientSession", return_value=mock_session):
        valid_sources = await source_manager.check_and_update_sources(sources_file)
        assert "http://example.com/sub1" in valid_sources
        assert "http://example.com/sub2" not in valid_sources


def test_config_processor_filter_configs(settings):
    """Test that the ConfigProcessor can filter configs."""
    config_processor = ConfigProcessor(settings)
    configs = {VALID_VMESS, VALID_VLESS, VALID_TROJAN}
    filtered = config_processor.filter_configs(configs, protocols=["vmess", "vless"])
    assert VALID_VMESS in filtered
    assert VALID_VLESS in filtered
    assert VALID_TROJAN not in filtered


@pytest.mark.asyncio
async def test_config_processor_test_configs(settings):
    """Test that the ConfigProcessor can test configs."""
    config_processor = ConfigProcessor(settings)
    configs = [VALID_VMESS]
    with patch(
        "massconfigmerger.utils.EnhancedConfigProcessor.test_connection",
        new_callable=AsyncMock,
        return_value=0.1,
    ):
        results = await config_processor.test_configs(configs)
        assert len(results) == 1
        assert results[0][0] == VALID_VMESS
        assert results[0][1] is not None


def test_output_generator_write_outputs(settings, tmp_path):
    """Test that the OutputGenerator can write output files."""
    output_generator = OutputGenerator(settings)
    configs = [VALID_VMESS, VALID_VLESS]
    output_dir = tmp_path / "output"
    written_files = output_generator.write_outputs(configs, output_dir)

    assert len(written_files) > 0
    raw_path = output_dir / "vpn_subscription_raw.txt"
    assert raw_path.exists()
    assert raw_path.read_text() == f"{VALID_VMESS}\n{VALID_VLESS}"