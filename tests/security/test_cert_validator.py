import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import ssl
from datetime import datetime, timedelta
import asyncio

from configstream.security.cert_validator import CertificateValidator, CertificateInfo


@pytest.mark.asyncio
async def test_validate_good_certificate():
    """Test validation of a good certificate."""
    validator = CertificateValidator()
    with patch("asyncio.open_connection") as mock_open_connection:
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open_connection.return_value = (mock_reader, mock_writer)
        with patch("ssl.get_server_certificate", new_callable=AsyncMock) as mock_get_cert:
            mock_get_cert.return_value = {
                    "notBefore": (datetime.now() - timedelta(days=1)).strftime('%b %d %H:%M:%S %Y GMT'),
                    "notAfter": (datetime.now() + timedelta(days=1)).strftime('%b %d %H:%M:%S %Y GMT'),
                "subject": ((("commonName", "expired.badssl.com"),),),
                "issuer": ((("commonName", "Test CA"),),),
            }
                cert_info = await validator.validate("example.com", 443)

            assert cert_info.valid is True
            assert not cert_info.errors


@pytest.mark.asyncio
async def test_validate_self_signed_certificate():
    """Test validation of a self-signed certificate."""
    validator = CertificateValidator()
    with patch("asyncio.open_connection") as mock_open_connection:
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open_connection.side_effect = ssl.SSLError(1, "CERTIFICATE_VERIFY_FAILED")

        cert_info = await validator.validate("example.com", 443)

        assert cert_info.valid is False
        assert "SSL verification failed" in str(cert_info.errors)


@pytest.mark.asyncio
async def test_validate_connection_timeout():
    """Test validation with a connection timeout."""
    validator = CertificateValidator()
    with patch("asyncio.open_connection", side_effect=asyncio.TimeoutError):
        cert_info = await validator.validate("example.com", 443)

        assert cert_info.valid is False
        assert "Connection timeout" in cert_info.errors