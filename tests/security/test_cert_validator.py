import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import ssl
from datetime import datetime, timedelta

from configstream.security.cert_validator import CertificateValidator


@pytest.fixture
def mock_ssl_writer():
    """Provides a mock SSL writer with a valid certificate."""
    mock_writer = AsyncMock(spec=asyncio.StreamWriter)
    mock_ssl_object = MagicMock()
    mock_ssl_object.getpeercert.return_value = {
        "notBefore": (datetime.now() - timedelta(days=30)).strftime(
            "%b %d %H:%M:%S %Y GMT"
        ),
        "notAfter": (datetime.now() + timedelta(days=365)).strftime(
            "%b %d %H:%M:%S %Y GMT"
        ),
        "subject": ((("commonName", "example.com"),),),
        "issuer": ((("commonName", "Test CA"),),),
    }
    mock_writer.get_extra_info = MagicMock(return_value=mock_ssl_object)
    return mock_writer


@pytest.mark.asyncio
async def test_validate_good_certificate(mock_ssl_writer):
    """Test validation of a good certificate."""
    validator = CertificateValidator()
    with patch(
        "asyncio.open_connection", new_callable=AsyncMock
    ) as mock_open_connection:
        mock_open_connection.return_value = (AsyncMock(), mock_ssl_writer)

        cert_info = await validator.validate("example.com", 443)

        assert cert_info.valid is True
        assert not cert_info.errors
        assert cert_info.subject.get("commonName") == "example.com"
        assert cert_info.days_until_expiry > 360


@pytest.mark.asyncio
async def test_validate_self_signed_certificate():
    """Test validation of a self-signed certificate, fetching details on retry."""
    validator = CertificateValidator()

    mock_unverified_writer = AsyncMock(spec=asyncio.StreamWriter)
    mock_ssl_object = MagicMock()
    mock_ssl_object.getpeercert.return_value = {
        "notBefore": (datetime.now() - timedelta(days=1)).strftime(
            "%b %d %H:%M:%S %Y GMT"
        ),
        "notAfter": (datetime.now() + timedelta(days=365)).strftime(
            "%b %d %H:%M:%S %Y GMT"
        ),
        "subject": ((("commonName", "self-signed.badssl.com"),),),
        "issuer": ((("commonName", "self-signed.badssl.com"),),),
    }
    mock_unverified_writer.get_extra_info = MagicMock(return_value=mock_ssl_object)

    with patch("asyncio.open_connection") as mock_open_connection:
        mock_open_connection.side_effect = [
            ssl.SSLError(1, "CERTIFICATE_VERIFY_FAILED"),
            (AsyncMock(), mock_unverified_writer),
        ]

        cert_info = await validator.validate("self-signed.badssl.com", 443)

        assert cert_info.valid is False
        assert "SSL verification failed: CERTIFICATE_VERIFY_FAILED" in cert_info.errors
        assert len(cert_info.errors) == 1
        assert cert_info.subject.get("commonName") == "self-signed.badssl.com"
        assert mock_open_connection.call_count == 2


@pytest.mark.asyncio
async def test_validate_connection_timeout():
    """Test validation with a connection timeout."""
    validator = CertificateValidator()
    with patch(
        "asyncio.open_connection", side_effect=asyncio.TimeoutError
    ) as mock_open_connection:
        cert_info = await validator.validate("example.com", 443)

        assert cert_info.valid is False
        assert "Connection timeout" in cert_info.errors
        assert mock_open_connection.call_count == 1
