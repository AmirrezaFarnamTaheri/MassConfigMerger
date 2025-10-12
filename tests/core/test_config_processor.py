import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from configstream.core.config_processor import ConfigProcessor, categorize_protocol
from configstream.core.types import ConfigResult
from configstream.config import Settings, ProcessingSettings

@pytest.fixture
def mock_settings():
    """Fixture for a mock Settings object."""
    settings = Settings()
    settings.filtering.fetch_protocols = ["VMess", "Trojan"]
    settings.filtering.merge_include_protocols = {"VMESS", "VLESS"}
    settings.filtering.merge_exclude_protocols = {"TROJAN"}
    settings.filtering.include_isps = ["Google"]
    settings.filtering.exclude_isps = ["Amazon"]

    # Correctly mock the nested processing settings
    settings.processing = ProcessingSettings()
    settings.processing.mux_concurrency = 8
    settings.processing.smux_streams = 4

    return settings

def test_categorize_protocol():
    """Test the protocol categorization function."""
    assert categorize_protocol("vmess://") == "VMess"
    assert categorize_protocol("vless://") == "VLESS"
    assert categorize_protocol("trojan://") == "Trojan"
    assert categorize_protocol("unknown-proto://") == "Other"

def test_filter_configs_fetch_rules(mock_settings):
    """Test filtering with fetch-stage rules."""
    processor = ConfigProcessor(mock_settings)
    configs = {"vmess://config1", "trojan://config2", "vless://config3"}
    filtered = processor.filter_configs(configs, use_fetch_rules=True)
    assert filtered == {"vmess://config1", "trojan://config2"}

def test_filter_configs_merge_rules(mock_settings):
    """Test filtering with merge-stage rules."""
    processor = ConfigProcessor(mock_settings)
    configs = {"vmess://config1", "trojan://config2", "vless://config3"}
    filtered = processor.filter_configs(configs, use_fetch_rules=False)
    assert filtered == {"vmess://config1", "vless://config3"}

def test_filter_by_isp(mock_settings):
    """Test filtering by ISP."""
    processor = ConfigProcessor(mock_settings)
    results = [
        ConfigResult(protocol="p1", config="c1", isp="Google Fiber"),
        ConfigResult(protocol="p2", config="c2", isp="Amazon AWS"),
        ConfigResult(protocol="p3", config="c3", isp="DigitalOcean"),
    ]
    filtered = processor._filter_by_isp(results)
    assert len(filtered) == 1
    assert filtered[0].config == "c1"

@pytest.mark.asyncio
async def test_run_security_checks(mock_settings):
    """Test the security check runner."""
    processor = ConfigProcessor(mock_settings)

    # Mock the security checkers
    mock_ip_checker = AsyncMock()
    mock_cert_validator = AsyncMock()
    processor._ip_reputation_checker = mock_ip_checker
    processor._certificate_validator = mock_cert_validator

    # Mock the results
    results = [
        ConfigResult(protocol="p1", config="c1", host="good.com", port=443, is_reachable=True),
        ConfigResult(protocol="p2", config="c2", host="bad.com", port=443, is_reachable=True),
        ConfigResult(protocol="p3", config="c3", host="unreachable.com", port=443, is_reachable=False),
    ]

    # Mock the return values of the security checkers
    from configstream.security.ip_reputation import ReputationResult, ReputationScore
    mock_ip_checker.check_all.side_effect = [
        ReputationResult(score=ReputationScore.CLEAN),
        ReputationResult(score=ReputationScore.MALICIOUS),
    ]
    from configstream.security.cert_validator import CertificateInfo
    mock_cert_validator.validate.return_value = CertificateInfo(valid=True)

    # Mock the host resolver
    with patch.object(processor.tester, "resolve_host", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.side_effect = ["1.1.1.1", "2.2.2.2"]  # IPs for good.com and bad.com

        safe_results = await processor._run_security_checks(results)

        assert len(safe_results) == 2
        assert safe_results[0].config == "c1"
        assert safe_results[1].config == "c3"
        assert mock_ip_checker.check_all.call_count == 2
        assert mock_cert_validator.validate.call_count == 1

def test_apply_tuning(mock_settings):
    """Test applying tuning parameters to a config."""
    processor = ConfigProcessor(mock_settings)
    config = "vless://user@host:443?type=ws"
    tuned_config = processor.apply_tuning(config)
    assert "mux=8" in tuned_config
    assert "smux=4" in tuned_config
