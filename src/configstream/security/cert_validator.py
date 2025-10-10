# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""SSL/TLS certificate validation.

This module validates SSL certificates for VPN endpoints to detect
expired, self-signed, or otherwise problematic certificates.
"""
from __future__ import annotations

import asyncio
import logging
import ssl
from dataclasses import dataclass, field
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
    errors: List[str] = field(default_factory=list)
    serial_number: Optional[str] = None
    version: Optional[int] = None


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
        """Validate SSL certificate for host.

        Args:
            host: Hostname to check
            port: Port number (default: 443)
            timeout: Connection timeout in seconds

        Returns:
            CertificateInfo with validation results
        """
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT

        errors = []

        try:
            # Create SSL context that will verify certificates
            context = ssl.create_default_context()

            # Also create unverified context to get cert even if invalid
            unverified_context = ssl._create_unverified_context()

            # Try verified connection first
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port, ssl=context),
                    timeout=timeout
                )

                # Get SSL object and certificate
                ssl_object = writer.get_extra_info('ssl_object')
                cert = ssl_object.getpeercert()

                writer.close()
                await writer.wait_closed()

            except ssl.SSLError as e:
                # Certificate verification failed, try to get cert anyway
                errors.append(f"SSL verification failed: {str(e)}")

                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port, ssl=unverified_context),
                    timeout=timeout
                )

                ssl_object = writer.get_extra_info('ssl_object')
                cert = ssl_object.getpeercert()

                writer.close()
                await writer.wait_closed()

            # Parse certificate
            return self._parse_certificate(cert, errors)

        except asyncio.TimeoutError:
            errors.append("Connection timeout")
        except ConnectionRefusedError:
            errors.append("Connection refused")
        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")

        # Return error result
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