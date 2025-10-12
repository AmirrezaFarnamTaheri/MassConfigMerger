"""SSL/TLS certificate validation."""
from __future__ import annotations

import asyncio
import logging
import ssl
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CertificateInfo:
    """SSL certificate information."""

    valid: bool
    subject: dict = field(default_factory=dict)
    issuer: dict = field(default_factory=dict)
    not_before: datetime | None = None
    not_after: datetime | None = None
    days_until_expiry: int = 0
    errors: list[str] = field(default_factory=list)


class CertificateValidator:
    """Validates SSL/TLS certificates."""

    def _parse_and_validate_cert(
        self, cert: dict | None, errors: list[str]
    ) -> CertificateInfo:
        """Helper to parse and validate certificate details."""
        if not cert:
            errors.append("No certificate received")
            return CertificateInfo(valid=False, errors=errors)

        try:
            not_before = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
            not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        except (KeyError, ValueError) as e:
            errors.append(f"Could not parse certificate dates: {e}")
            return CertificateInfo(valid=False, errors=errors)

        days_left = (not_after - datetime.now()).days
        now = datetime.now()
        if now < not_before:
            errors.append("Certificate not yet valid")
        if now > not_after:
            errors.append("Certificate expired")
        if days_left < 30:
            errors.append(f"Certificate expires soon ({days_left} days)")

        return CertificateInfo(
            valid=len(errors) == 0,
            subject=dict(x[0] for x in cert.get("subject", [])),
            issuer=dict(x[0] for x in cert.get("issuer", [])),
            not_before=not_before,
            not_after=not_after,
            days_until_expiry=days_left,
            errors=errors,
        )

    async def validate(self, host: str, port: int = 443) -> CertificateInfo:
        """Validate SSL certificate for host."""
        errors: list[str] = []
        writer = None
        try:
            context = ssl.create_default_context()
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=context), timeout=10.0
            )
            ssl_object = writer.get_extra_info("ssl_object")
            cert = ssl_object.getpeercert()
            return self._parse_and_validate_cert(cert, errors)
        except ssl.SSLError as e:
            errors.append(f"SSL verification failed: {str(e)}")
            logger.debug(
                f"Retrying {host}:{port} with unverified context to fetch cert details."
            )
            unverified_writer = None
            try:
                unverified_context = ssl.create_default_context()
                unverified_context.check_hostname = False
                unverified_context.verify_mode = ssl.CERT_NONE
                _, unverified_writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port, ssl=unverified_context),
                    timeout=10.0,
                )
                ssl_object = unverified_writer.get_extra_info("ssl_object")
                cert = ssl_object.getpeercert() if ssl_object else None
                return self._parse_and_validate_cert(cert, errors)
            except Exception as unverified_e:
                errors.append(f"Unverified fetch failed: {unverified_e}")
                return self._parse_and_validate_cert(None, errors)
            finally:
                if unverified_writer:
                    unverified_writer.close()
                    await unverified_writer.wait_closed()
        except asyncio.TimeoutError:
            errors.append("Connection timeout")
            return self._parse_and_validate_cert(None, errors)
        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")
            return self._parse_and_validate_cert(None, errors)
        finally:
            if writer:
                writer.close()
                await writer.wait_closed()
        return self._parse_and_validate_cert(None, errors)
