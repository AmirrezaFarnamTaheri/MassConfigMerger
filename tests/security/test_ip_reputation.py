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