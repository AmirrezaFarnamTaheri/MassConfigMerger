from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientError

from configstream.config import Settings
from configstream.tester import BlocklistChecker


@pytest.fixture
def config() -> Settings:
    """Fixture for BlocklistChecker tests."""
    settings = Settings()
    settings.security.apivoid_api_key = "test_api_key"
    settings.security.blocklist_detection_threshold = 1
    return settings


@pytest.mark.asyncio
async def test_blocklist_checker_init(config: Settings):
    """Test BlocklistChecker initialization."""
    checker = BlocklistChecker(config)
    assert checker.config == config
    assert checker._session is None


@pytest.mark.asyncio
async def test_get_session(config: Settings):
    """Test get_session creates and reuses a session."""
    checker = BlocklistChecker(config)
    session1 = await checker.get_session()
    session2 = await checker.get_session()
    assert session1 is session2
    assert not session1.closed
    await checker.close()
    assert session1.closed


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_get_session_creation_failure(
    MockClientSession, config: Settings, caplog
):
    """Test get_session handles session creation failure."""
    MockClientSession.side_effect = Exception("Session creation failed")
    checker = BlocklistChecker(config)
    with pytest.raises(Exception, match="Session creation failed"):
        await checker.get_session()
    assert "Failed to create aiohttp session" in caplog.text


@pytest.mark.asyncio
async def test_is_malicious_disabled(config: Settings):
    """Test is_malicious returns False if disabled in config."""
    config.security.apivoid_api_key = None
    checker = BlocklistChecker(config)
    assert not await checker.is_malicious("1.2.3.4")

    config.security.apivoid_api_key = "key"
    config.security.blocklist_detection_threshold = 0
    checker = BlocklistChecker(config)
    assert not await checker.is_malicious("1.2.3.4")


@pytest.mark.asyncio
async def test_is_malicious_invalid_ip(config: Settings):
    """Test is_malicious returns False for an invalid IP address."""
    checker = BlocklistChecker(config)
    assert not await checker.is_malicious("not-an-ip")
    assert not await checker.is_malicious("")


@pytest.mark.asyncio
async def test_is_malicious_private_ip_skipped(config: Settings, caplog):
    """Private IPs should be ignored for blocklist lookups."""

    checker = BlocklistChecker(config)
    with caplog.at_level("DEBUG"):
        assert not await checker.is_malicious("10.0.0.5")
    assert "Skipping blocklist lookup for non-public IP" in caplog.text


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_is_malicious_api_error(MockClientSession, config: Settings, caplog):
    """Test is_malicious handles API returning an error."""
    mock_session = MockClientSession.return_value
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {"error": "Invalid API key"}
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    checker = BlocklistChecker(config)
    checker._session = mock_session
    assert not await checker.is_malicious("1.2.3.4")
    assert "APIVoid API error" in caplog.text


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_is_malicious_http_error(MockClientSession, config: Settings, caplog):
    """Test is_malicious handles non-200 HTTP status."""
    mock_session = MockClientSession.return_value
    mock_resp = AsyncMock()
    mock_resp.status = 500
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    checker = BlocklistChecker(config)
    checker._session = mock_session
    assert not await checker.is_malicious("1.2.3.4")
    assert "APIVoid API request failed with status 500" in caplog.text


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_is_malicious_request_exception(
    MockClientSession, config: Settings, caplog
):
    """Test is_malicious handles request exceptions."""
    mock_session = MockClientSession.return_value
    mock_session.get.side_effect = ClientError("Connection failed")

    checker = BlocklistChecker(config)
    checker._session = mock_session
    assert not await checker.is_malicious("1.2.3.4")
    assert "APIVoid API request failed for IP 1.2.3.4: Connection failed" in caplog.text


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_is_malicious_positive_detection(MockClientSession, config: Settings):
    """Test is_malicious returns True for a malicious IP."""
    mock_session = MockClientSession.return_value
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {
        "data": {"report": {"blacklists": {"detections": 5}}}
    }
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    checker = BlocklistChecker(config)
    checker._session = mock_session
    assert await checker.is_malicious("1.2.3.4")


@pytest.mark.asyncio
@patch("aiohttp.ClientSession")
async def test_is_malicious_no_detection(MockClientSession, config: Settings):
    """Test is_malicious returns False for a clean IP."""
    mock_session = MockClientSession.return_value
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {
        "data": {"report": {"blacklists": {"detections": 0}}}
    }
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    checker = BlocklistChecker(config)
    checker._session = mock_session
    assert not await checker.is_malicious("1.2.3.4")
