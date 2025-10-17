"""
Tests for the MaliciousNodeDetector security module
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from configstream.core import Proxy
from configstream.security.malicious_detector import (MaliciousNodeDetector,
                                                      SecurityTest)

# Use a proxy config string that is valid for the ProxyConnector to parse
VALID_PROXY_CONFIG = "socks5://127.0.0.1:1080"


@pytest.fixture
def detector():
    """Create a detector instance for testing"""
    return MaliciousNodeDetector()


@pytest.fixture
def sample_proxy():
    """Create a sample proxy for testing"""
    return Proxy(
        config=VALID_PROXY_CONFIG,  # Use a valid format
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        country_code="US",
        asn="AS1234",
    )


@pytest.fixture
def mock_session():
    """
    Create a mock aiohttp session that correctly handles the async context manager.
    """
    session = AsyncMock(spec=aiohttp.ClientSession)

    # This is the object that will be returned by __aenter__
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)

    # This is the context manager object returned by session.get()
    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = mock_response

    # Make session.get a regular MagicMock that returns the context manager
    session.get = MagicMock(return_value=context_manager)

    # Add a helper to configure the mock response for each test
    def _configure_get(status=200, text="", json_data=None, history=None, side_effect=None):
        if side_effect:
            context_manager.__aenter__.side_effect = side_effect
        else:
            context_manager.__aenter__.side_effect = None
            mock_response.status = status
            mock_response.text = AsyncMock(return_value=text)
            mock_response.json = AsyncMock(return_value=json_data or {})
            mock_response.history = history or []
            context_manager.__aenter__.return_value = mock_response

    session.configure_get = _configure_get
    return session


class TestContentInjection:
    """Tests for content injection detection"""

    @pytest.mark.asyncio
    async def test_clean_content_passes(self, detector, mock_session, sample_proxy):
        mock_session.configure_get(text="<html><body>Clean content</body></html>")
        result = await detector._test_content_injection(mock_session, sample_proxy)
        assert result.passed is True
        assert result.severity == "none"

    @pytest.mark.asyncio
    async def test_injected_content_fails(self, detector, mock_session, sample_proxy):
        malicious_content = """
        <html><body>
        <script>document.domain='attacker.com'</script>
        <script>location.href='http://evil.com'</script>
        <script>eval('malicious code')</script>
        </body></html>
        """
        mock_session.configure_get(text=malicious_content)
        result = await detector._test_content_injection(mock_session, sample_proxy)
        assert result.passed is False
        assert result.severity == "critical"

    @pytest.mark.asyncio
    async def test_timeout_handled_gracefully(self, detector, mock_session, sample_proxy):
        mock_session.configure_get(side_effect=asyncio.TimeoutError())
        result = await detector._test_content_injection(mock_session, sample_proxy)
        assert result.passed is False
        assert result.severity == "medium"


class TestHeaderManipulation:
    """Tests for header manipulation detection"""

    @pytest.mark.asyncio
    async def test_headers_preserved(self, detector, mock_session, sample_proxy):
        response_data = {
            "headers": {
                "X-Custom-Header": "test-value-12345",
                "X-Another-Header": "another-value",
                "User-Agent": "ConfigStream-SecurityTest/1.0",
            }
        }
        mock_session.configure_get(json_data=response_data)
        result = await detector._test_header_manipulation(mock_session, sample_proxy)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_headers_stripped(self, detector, mock_session, sample_proxy):
        # This response strips ALL custom headers.
        # len(missing_headers) will be 3, which is > the threshold of 2.
        response_data = {"headers": {}}
        mock_session.configure_get(json_data=response_data)
        result = await detector._test_header_manipulation(mock_session, sample_proxy)
        assert result.passed is False
        assert result.severity == "high"


class TestDNSLeak:
    """Tests for DNS leak detection"""

    @pytest.mark.asyncio
    async def test_no_dns_leak(self, detector, mock_session, sample_proxy):
        mock_session.configure_get(status=200)
        result = await detector._test_dns_leak(mock_session, sample_proxy)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_possible_dns_leak(self, detector, mock_session, sample_proxy):
        mock_session.configure_get(status=404)
        result = await detector._test_dns_leak(mock_session, sample_proxy)
        assert result.passed is False
        assert result.severity == "high"


class TestRedirectHijacking:
    """Tests for redirect hijacking detection"""

    @pytest.mark.asyncio
    async def test_normal_redirects(self, detector, mock_session, sample_proxy):
        mock_session.configure_get(history=[1, 2])
        result = await detector._test_redirect_hijacking(mock_session, sample_proxy)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_excessive_redirects(self, detector, mock_session, sample_proxy):
        mock_session.configure_get(history=[1, 2, 3, 4])
        result = await detector._test_redirect_hijacking(mock_session, sample_proxy)
        assert result.passed is False
        assert result.severity == "medium"


class TestMalwareReputation:
    """Tests for malware reputation checking"""

    @pytest.mark.asyncio
    async def test_clean_reputation(self, detector, sample_proxy):
        result = await detector._test_malware_reputation(sample_proxy)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_malicious_asn(self, detector, sample_proxy):
        sample_proxy.asn = "AS13335"  # Known malicious
        result = await detector._test_malware_reputation(sample_proxy)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_blocked_country(self, detector, sample_proxy):
        sample_proxy.country_code = "IR"  # Known blocked
        detector.config.SECURITY["blocked_countries"] = ["IR"]
        result = await detector._test_malware_reputation(sample_proxy)
        assert result.passed is False


class TestSuspiciousPorts:
    """Tests for suspicious port detection"""

    @pytest.mark.asyncio
    async def test_normal_port(self, detector, sample_proxy):
        sample_proxy.port = 12345
        result = await detector._test_suspicious_ports(sample_proxy)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_reserved_port(self, detector, sample_proxy):
        sample_proxy.port = 22  # Reserved
        result = await detector._test_suspicious_ports(sample_proxy)
        assert result.passed is False


class TestOverallDetection:
    """Tests for overall maliciousness detection"""

    @patch("configstream.security.malicious_detector.aiohttp.ClientSession")
    @patch("configstream.security.malicious_detector.ProxyConnector.from_url")
    @pytest.mark.asyncio
    async def test_clean_proxy_overall(self, mock_connector, mock_session, detector, sample_proxy):
        """A clean proxy should score 0 and pass all checks."""
        with patch.multiple(
            detector,
            _test_content_injection=AsyncMock(return_value=SecurityTest("test", True, "none", "")),
            _test_header_manipulation=AsyncMock(
                return_value=SecurityTest("test", True, "none", "")
            ),
            _test_dns_leak=AsyncMock(return_value=SecurityTest("test", True, "none", "")),
            _test_redirect_hijacking=AsyncMock(return_value=SecurityTest("test", True, "none", "")),
            _test_malware_reputation=AsyncMock(return_value=SecurityTest("test", True, "none", "")),
            _test_suspicious_ports=AsyncMock(return_value=SecurityTest("test", True, "none", "")),
        ):
            result = await detector.detect_malicious(sample_proxy)

        assert result["is_malicious"] is False
        assert result["score"] == 0
        assert result["severity"] == "low"

    @patch("configstream.security.malicious_detector.aiohttp.ClientSession")
    @patch("configstream.security.malicious_detector.ProxyConnector.from_url")
    @pytest.mark.asyncio
    async def test_malicious_proxy_overall(
        self, mock_connector, mock_session, detector, sample_proxy
    ):
        """A malicious proxy should score high and be flagged."""
        with patch.multiple(
            detector,
            _test_content_injection=AsyncMock(
                return_value=SecurityTest("test", False, "critical", "")
            ),
            _test_header_manipulation=AsyncMock(
                return_value=SecurityTest("test", False, "high", "")
            ),
            _test_dns_leak=AsyncMock(return_value=SecurityTest("test", False, "high", "")),
            _test_redirect_hijacking=AsyncMock(
                return_value=SecurityTest("test", False, "medium", "")
            ),
            _test_malware_reputation=AsyncMock(
                return_value=SecurityTest("test", False, "high", "")
            ),
            _test_suspicious_ports=AsyncMock(
                return_value=SecurityTest("test", False, "medium", "")
            ),
        ):
            result = await detector.detect_malicious(sample_proxy)

        assert result["is_malicious"] is True
        assert result["score"] >= 70
        assert result["severity"] == "critical"
