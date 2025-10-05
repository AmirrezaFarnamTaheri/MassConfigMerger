import asyncio
import base64
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from massconfigmerger.config import Settings
from massconfigmerger.core.config_processor import ConfigProcessor, ConfigResult
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
@patch("massconfigmerger.core.source_manager.utils.choose_proxy", return_value=None)
async def test_source_manager_fetch_sources(mock_choose_proxy, settings):
    """Test that the SourceManager can fetch and parse sources."""
    source_manager = SourceManager(settings)
    sources = ["http://example.com/sub1"]

    mock_response = MagicMock()
    mock_response.text = AsyncMock(return_value=VALID_VMESS)
    mock_response.status = 200

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession", return_value=mock_session):
        configs = await source_manager.fetch_sources(sources)
        assert VALID_VMESS in configs


@pytest.mark.asyncio
@patch("massconfigmerger.core.source_manager.utils.choose_proxy", return_value=None)
async def test_source_manager_check_and_update_sources(mock_choose_proxy, settings, tmp_path):
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

    # Test fetch rules
    settings.filtering.fetch_protocols = ["VMESS", "VLESS"]
    filtered = config_processor.filter_configs(configs, use_fetch_rules=True)
    assert VALID_VMESS in filtered
    assert VALID_VLESS in filtered
    assert VALID_TROJAN not in filtered

    # Test merge rules
    settings.filtering.merge_include_protocols = {"TROJAN"}
    settings.filtering.merge_exclude_protocols = set()
    filtered_merge = config_processor.filter_configs(configs, use_fetch_rules=False)
    assert VALID_TROJAN in filtered_merge
    assert VALID_VMESS not in filtered_merge


@pytest.mark.asyncio
async def test_config_processor_test_configs(settings):
    """Test that the ConfigProcessor can test configs."""
    config_processor = ConfigProcessor(settings)
    configs = {VALID_VMESS}
    with patch.object(config_processor.tester, "test_connection", new_callable=AsyncMock) as mock_test:
        mock_test.return_value = 0.1  # 100ms ping
        results = await config_processor.test_configs(configs)
        assert len(results) == 1
        assert results[0].config == VALID_VMESS
        assert results[0].ping_time == 0.1
        assert results[0].is_reachable is True


def test_output_generator_write_outputs(settings, tmp_path):
    """Test that the OutputGenerator can write output files."""
    settings.output.write_base64 = True
    output_generator = OutputGenerator(settings)
    configs = [VALID_VMESS, VALID_VLESS]
    output_dir = tmp_path / "output"
    written_files = output_generator.write_outputs(configs, output_dir)

    assert len(written_files) > 0
    raw_path = output_dir / "vpn_subscription_raw.txt"
    assert raw_path.exists()
    assert raw_path.read_text() == f"{VALID_VMESS}\n{VALID_VLESS}"

    base64_path = output_dir / "vpn_subscription_base64.txt"
    assert base64_path.exists()
    expected_b64 = base64.b64encode(f"{VALID_VMESS}\n{VALID_VLESS}".encode()).decode()
    assert base64_path.read_text() == expected_b64