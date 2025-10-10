"""Test certificate validation."""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch
from configstream.security.cert_validator import (
    CertificateValidator,
    CertificateInfo
)


def test_certificate_info_dataclass():
    """Test CertificateInfo structure."""
    cert_info = CertificateInfo(
        valid=True,
        subject={"commonName": "example.com"},
        issuer={"commonName": "Let's Encrypt"},
        not_before=datetime(2024, 1, 1),
        not_after=datetime(2025, 1, 1),
        days_until_expiry=90,
        is_self_signed=False
    )

    assert cert_info.valid is True
    assert cert_info.days_until_expiry == 90
    assert cert_info.is_self_signed is False
    print("✓ CertificateInfo structure correct")


@pytest.mark.asyncio
async def test_validate_good_certificate():
    """Test validation of a good certificate (Cloudflare)."""
    validator = CertificateValidator()
    cert_info = await validator.validate("1.1.1.1", 443)

    # Should have some information even if errors
    assert isinstance(cert_info, CertificateInfo)
    assert cert_info.subject or cert_info.errors

    if cert_info.valid:
        print(f"✓ Certificate valid:")
        print(f"  Subject: {cert_info.subject}")
        print(f"  Issuer: {cert_info.issuer}")
        print(f"  Expires in: {cert_info.days_until_expiry} days")
    else:
        print(f"⚠ Certificate validation had issues:")
        print(f"  Errors: {cert_info.errors}")


@pytest.mark.asyncio
async def test_validate_invalid_host():
    """Test validation with invalid host."""
    validator = CertificateValidator()
    cert_info = await validator.validate(
        "invalid.example.com",
        443,
        timeout=2.0
    )

    assert cert_info.valid is False
    assert len(cert_info.errors) > 0
    print(f"✓ Invalid host handled: {cert_info.errors[0]}")


@pytest.mark.asyncio
async def test_validate_non_https_port():
    """Test validation on non-HTTPS port."""
    validator = CertificateValidator()
    cert_info = await validator.validate(
        "1.1.1.1",
        80,  # HTTP port, not HTTPS
        timeout=2.0
    )

    assert cert_info.valid is False
    print("✓ Non-HTTPS port handled gracefully")


@pytest.mark.asyncio
async def test_validate_timeout():
    """Test validation timeout handling."""
    validator = CertificateValidator()
    # Use an IP that will timeout
    cert_info = await validator.validate(
        "192.0.2.1",  # TEST-NET-1
        443,
        timeout=1.0
    )

    assert cert_info.valid is False
    assert "timeout" in str(cert_info.errors).lower()
    print("✓ Timeout handled correctly")


@pytest.mark.asyncio
async def test_validate_expired_certificate():
    """Test validation of an expired certificate."""
    validator = CertificateValidator()
    # expired.badssl.com has an expired certificate
    cert_info = await validator.validate("expired.badssl.com", 443)
    assert cert_info.valid is False
    assert any("expired" in e for e in cert_info.errors)

@pytest.mark.asyncio
async def test_validate_self_signed_certificate():
    """Test validation of a self-signed certificate."""
    validator = CertificateValidator()
    # self-signed.badssl.com has a self-signed certificate
    cert_info = await validator.validate("self-signed.badssl.com", 443)
    assert cert_info.valid is False
    assert any("self-signed" in e for e in cert_info.errors)

if __name__ == "__main__":
    print("Running certificate validation tests...\n")

    test_certificate_info_dataclass()
    asyncio.run(test_validate_good_certificate())
    asyncio.run(test_validate_invalid_host())
    asyncio.run(test_validate_non_https_port())
    asyncio.run(test_validate_timeout())
    asyncio.run(test_validate_expired_certificate())
    asyncio.run(test_validate_self_signed_certificate())