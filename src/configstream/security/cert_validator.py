"""SSL/TLS certificate validation.

This module validates SSL certificates for VPN endpoints to detect
expired, self-signed, or otherwise problematic certificates.
"""
from __future__ import annotations

import asyncio
import logging
import ssl
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class CertificateInfo:
    """SSL certificate information.

    Attributes:
        valid: Whether certificate is valid
        subject: Certificate subject information
        issuer: Certificate issuer information
        not_before: Certificate valid from date
        not_after: Certificate expires on date
        days_until_expiry: Days until certificate expires
        is_self_signed: Whether certificate is self-signed
        errors: List of validation errors
        serial_number: Certificate serial number
        version: Certificate version
    """
    valid: bool
    subject: Dict[str, str]
    issuer: Dict[str, str]
    not_before: datetime
    not_after: datetime
    days_until_expiry: int
    is_self_signed: bool = False
    errors: List[str] = None
    serial_number: Optional[str] = None
    version: Optional[int] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class CertificateValidator:
    """Validates SSL/TLS certificates.

    Example:
        >>> validator = CertificateValidator()
        >>> cert_info = await validator.validate("example.com", 443)
        >>> print(f"Valid: {cert_info.valid}")
        >>> print(f"Expires in: {cert_info.days_until_expiry} days")
    """

    DEFAULT_TIMEOUT = 10.0

    async def validate(
        self,
        host: str,
        port: int = 443,
        timeout: float = None
    ) -> CertificateInfo:
        """Validate SSL certificate for host."""
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT

        errors: List[str] = []

        try:
            context = ssl.create_default_context()
            unverified_context = ssl._create_unverified_context()

            # Determine if SNI should be used (hostname, not raw IP)
            use_sni = True
            try:
                # Very simple heuristic: if host contains only digits and dots/colons, treat as IP
                # (do not attempt full IP parsing to avoid extra deps)
                use_sni = any(c.isalpha() for c in host)
            except Exception:
                use_sni = True

            # Try verified connection first
            try:
                if use_sni:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port, ssl=context, server_hostname=host),
                        timeout=timeout
                    )
                else:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port, ssl=context),
                        timeout=timeout
                    )
                    errors.append("SNI not used (IP address); hostname verification may be limited")

                ssl_object = writer.get_extra_info('ssl_object')
                cert = ssl_object.getpeercert()

                writer.close()
                await writer.wait_closed()

            except ssl.SSLError as e:
                errors.append(f"SSL verification failed: {str(e)}")
                # Retry unverified to retrieve the certificate details
                if use_sni:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port, ssl=unverified_context, server_hostname=host),
                        timeout=timeout
                    )
                else:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port, ssl=unverified_context),
                        timeout=timeout
                    )

                ssl_object = writer.get_extra_info('ssl_object')
                cert = ssl_object.getpeercert()

                writer.close()
                await writer.wait_closed()

            return self._parse_certificate(cert, errors)

        except asyncio.TimeoutError:
            errors.append("Connection timeout")
        except ConnectionRefusedError:
            errors.append("Connection refused")
        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")

        return CertificateInfo(
            valid=False,
            subject={},
            issuer={},
            not_before=datetime.now(),
            not_after=datetime.now(),
            days_until_expiry=0,
            errors=errors
        )

    def _parse_certificate(
        self,
        cert: Dict,
        errors: List[str]
    ) -> CertificateInfo:
        """Parse certificate dictionary.

        Args:
            cert: Certificate dictionary from SSL connection
            errors: List of existing errors

        Returns:
            CertificateInfo object
        """
        try:
            # Parse dates
            not_before = datetime.strptime(
                cert['notBefore'],
                '%b %d %H:%M:%S %Y %Z'
            )
            not_after = datetime.strptime(
                cert['notAfter'],
                '%b %d %H:%M:%S %Y %Z'
            )

            # Calculate days until expiry
            now = datetime.now()
            days_left = (not_after - now).days

            # Check validity period
            if now < not_before:
                errors.append("Certificate not yet valid")
            if now > not_after:
                errors.append("Certificate expired")
            if days_left < 30:
                errors.append(f"Certificate expires soon ({days_left} days)")

            # Extract subject and issuer
            subject = dict(x[0] for x in cert.get('subject', []))
            issuer = dict(x[0] for x in cert.get('issuer', []))

            # Check if self-signed
            is_self_signed = subject == issuer
            if is_self_signed:
                errors.append("Certificate is self-signed")

            # Get serial number and version
            serial_number = cert.get('serialNumber')
            version = cert.get('version')

            return CertificateInfo(
                valid=len(errors) == 0,
                subject=subject,
                issuer=issuer,
                not_before=not_before,
                not_after=not_after,
                days_until_expiry=days_left,
                is_self_signed=is_self_signed,
                errors=errors,
                serial_number=serial_number,
                version=version
            )

        except Exception as e:
            errors.append(f"Certificate parsing failed: {str(e)}")
            return CertificateInfo(
                valid=False,
                subject={},
                issuer={},
                not_before=datetime.now(),
                not_after=datetime.now(),
                days_until_expiry=0,
                errors=errors
            )