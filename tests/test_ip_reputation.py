"""Test IP reputation checking."""
import pytest
import asyncio
import os
from configstream.security.ip_reputation import (
    IPReputationChecker,
    ReputationScore,
    ReputationResult
)


def test_reputation_result_dataclass():
    """Test ReputationResult structure."""
    result = ReputationResult(
        score=ReputationScore.CLEAN,
        abuse_confidence=5,
        is_tor=False,
        is_proxy=False,
        is_vpn=True,
        threat_types=["hosting/vpn"],
        checked_services=["AbuseIPDB", "ip-api"]
    )

    assert result.score == ReputationScore.CLEAN
    assert result.is_vpn is True
    assert len(result.checked_services) == 2
    print("✓ ReputationResult structure correct")


@pytest.mark.asyncio
async def test_check_ipapi_cloudflare():
    """Test ip-api check with Cloudflare DNS (should be clean)."""
    checker = IPReputationChecker()
    result = await checker.check_ipapi("1.1.1.1")

    # Should succeed
    assert "error" not in result
    assert result.get("status") == "success"
    print(f"✓ ip-api check successful: {result.get('org')}")


@pytest.mark.asyncio
async def test_check_all_without_keys():
    """Test check_all without API keys (only ip-api will work)."""
    checker = IPReputationChecker()
    result = await checker.check_all("1.1.1.1")

    assert isinstance(result, ReputationResult)
    assert "ip-api" in result.checked_services
    print(f"✓ Check completed: {result.score.value}")
    print(f"  Services checked: {result.checked_services}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not (os.getenv("ABUSEIPDB_API_KEY") and os.getenv("IPQS_API_KEY")),
    reason="Requires ABUSEIPDB_API_KEY and IPQS_API_KEY environment variables"
)
async def test_check_all_with_keys():
    """Test check_all with API keys.

    Set environment variables before running:
    export ABUSEIPDB_API_KEY=your_key
    export IPQS_API_KEY=your_key
    """
    import os

    api_keys = {}
    if key := os.getenv("ABUSEIPDB_API_KEY"):
        api_keys["abuseipdb"] = key
    if key := os.getenv("IPQS_API_KEY"):
        api_keys["ipqualityscore"] = key

    checker = IPReputationChecker(api_keys=api_keys)
    result = await checker.check_all("1.1.1.1")

    assert isinstance(result, ReputationResult)
    print(f"✓ Full check completed:")
    print(f"  Score: {result.score.value}")
    print(f"  Abuse confidence: {result.abuse_confidence}")
    print(f"  Services: {result.checked_services}")
    print(f"  Threats: {result.threat_types}")


if __name__ == "__main__":
    print("Running IP reputation tests...")
    print("Note: Some tests require API keys\n")

    test_reputation_result_dataclass()
    asyncio.run(test_check_ipapi_cloudflare())
    asyncio.run(test_check_all_without_keys())