import pytest
from unittest.mock import patch, AsyncMock
from configstream.security.ip_reputation import IPReputationChecker, ReputationScore, ReputationResult

@pytest.mark.asyncio
async def test_check_all_services():
    """Test checking all IP reputation services."""
    checker = IPReputationChecker(api_keys={"abuseipdb": "test", "ipqualityscore": "test"})
    with patch.object(checker, "check_abuseipdb", new_callable=AsyncMock) as mock_abuseipdb, \
         patch.object(checker, "check_ipapi", new_callable=AsyncMock) as mock_ipapi, \
         patch.object(checker, "check_ipqualityscore", new_callable=AsyncMock) as mock_ipqualityscore:

        mock_abuseipdb.return_value = {"abuseConfidenceScore": 80}
        mock_ipapi.return_value = {"status": "success", "proxy": True}
        mock_ipqualityscore.return_value = {"fraud_score": 90}

        result = await checker.check_all("1.1.1.1")

        assert result.score == ReputationScore.MALICIOUS
        assert result.abuse_confidence == 80
        assert result.is_proxy is True
        assert "high_fraud_score" in result.threat_types


@pytest.mark.asyncio
async def test_check_all_services_clean():
    """Test checking all IP reputation services with a clean IP."""
    checker = IPReputationChecker(api_keys={"abuseipdb": "test", "ipqualityscore": "test"})
    with patch.object(checker, "check_abuseipdb", new_callable=AsyncMock) as mock_abuseipdb, \
         patch.object(checker, "check_ipapi", new_callable=AsyncMock) as mock_ipapi, \
         patch.object(checker, "check_ipqualityscore", new_callable=AsyncMock) as mock_ipqualityscore:

        mock_abuseipdb.return_value = {"abuseConfidenceScore": 0}
        mock_ipapi.return_value = {"status": "success", "proxy": False}
        mock_ipqualityscore.return_value = {"fraud_score": 0}

        result = await checker.check_all("8.8.8.8")

        assert result.score == ReputationScore.CLEAN


@pytest.mark.asyncio
async def test_check_all_services_suspicious():
    """Test checking all IP reputation services with a suspicious IP."""
    checker = IPReputationChecker(api_keys={"abuseipdb": "test", "ipqualityscore": "test"})
    with patch.object(checker, "check_abuseipdb", new_callable=AsyncMock) as mock_abuseipdb, \
         patch.object(checker, "check_ipapi", new_callable=AsyncMock) as mock_ipapi, \
         patch.object(checker, "check_ipqualityscore", new_callable=AsyncMock) as mock_ipqualityscore:

        mock_abuseipdb.return_value = {"abuseConfidenceScore": 30}
        mock_ipapi.return_value = {"status": "success", "proxy": False}
        mock_ipqualityscore.return_value = {"fraud_score": 0}

        result = await checker.check_all("1.2.3.4")

        assert result.score == ReputationScore.SUSPICIOUS


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
async def test_check_abuseipdb_success(mock_get):
    """Test AbuseIPDB check with a successful API call."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"data": {"abuseConfidenceScore": 50}}
    mock_get.return_value.__aenter__.return_value = mock_response

    checker = IPReputationChecker(api_keys={"abuseipdb": "test_key"})
    result = await checker.check_abuseipdb("1.1.1.1")

    assert result["abuseConfidenceScore"] == 50


@pytest.mark.asyncio
async def test_check_ipqualityscore_no_key():
    """Test IPQualityScore check when no API key is provided."""
    checker = IPReputationChecker()
    result = await checker.check_ipqualityscore("1.1.1.1")
    assert "No API key configured" in result["error"]


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
async def test_check_ipapi_failure(mock_get):
    """Test ip-api check with a failed API call."""
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_get.return_value.__aenter__.return_value = mock_response

    checker = IPReputationChecker()
    result = await checker.check_ipapi("1.1.1.1")

    assert "HTTP 500" in result["error"]


def test_ip_masking():
    """Test the IP masking logic."""
    checker = IPReputationChecker()
    assert checker._mask_ip("192.168.1.100") == "192.168.1.x"
    assert checker._mask_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334") == "2001:0db8:85a3:0000:0000:8a2e:0370:xxxx"
    assert checker._mask_ip("invalid-ip") == "x.x.x.x"