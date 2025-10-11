"""SSL/TLS certificate validation."""
from __future__ import annotations

import asyncio
import logging
import ssl
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class CertificateInfo:
    """SSL certificate information."""
    valid: bool
    subject: dict
    issuer: dict
    not_before: datetime
    not_after: datetime
    days_until_expiry: int
    errors: list[str]

class CertificateValidator:
    """Validates SSL/TLS certificates."""

    async def validate(self, host: str, port: int = 443) -> CertificateInfo:
        """Validate SSL certificate for host."""
        errors = []

        try:
            # Create SSL context
            context = ssl.create_default_context()

            # Connect and get certificate
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=context),
                timeout=10.0
            )

            # Get certificate
            ssl_object = writer.get_extra_info('ssl_object')
            cert = ssl_object.getpeercert()

            writer.close()
            await writer.wait_closed()

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
            days_left = (not_after - datetime.now()).days

            # Check validity
            now = datetime.now()
            if now < not_before:
                errors.append("Certificate not yet valid")
            if now > not_after:
                errors.append("Certificate expired")
            if days_left < 30:
                errors.append(f"Certificate expires soon ({days_left} days)")

            return CertificateInfo(
                valid=len(errors) == 0,
                subject=dict(x[0] for x in cert['subject']),
                issuer=dict(x[0] for x in cert['issuer']),
                not_before=not_before,
                not_after=not_after,
                days_until_expiry=days_left,
                errors=errors
            )

        except ssl.SSLError as e:
            errors.append(f"SSL verification failed: {str(e)}")
            logger.debug(f"Retrying {host}:{port} with unverified context to fetch cert details.")
            reader = writer = None
            try:
                unverified_context = ssl.create_default_context()
                unverified_context.check_hostname = False
                unverified_context.verify_mode = ssl.CERT_NONE
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port, ssl=unverified_context),
                    timeout=10.0
                )
                ssl_object = writer.get_extra_info('ssl_object') if writer else None
                if not ssl_object:
                    errors.append("Unverified fetch failed: no SSL object available")
                else:
                    cert = ssl_object.getpeercert()
                    try:
                        _ = self._parse_certificate(cert, errors)
                    except Exception as parse_e:
                        errors.append(f"Certificate parse failed: {parse_e}")
            except Exception as unverified_e:
                errors.append(f"Unverified fetch failed: {unverified_e}")
            finally:
                try:
                    if writer is not None:
                        writer.close()
                        await writer.wait_closed()
                    if reader is not None:
                        reader.feed_eof()
                except Exception as close_e:
                    errors.append(f"Connection close failed: {close_e}")
            return CertificateInfo(valid=False, errors=errors, subject={}, issuer={}, not_before=datetime.now(), not_after=datetime.now(), days_until_expiry=0)

        except asyncio.TimeoutError:
            errors.append("Connection timeout")
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