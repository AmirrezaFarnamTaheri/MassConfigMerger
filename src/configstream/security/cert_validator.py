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

    def _parse_cert_datetime(self, value: str) -> datetime:
        """Parse OpenSSL date strings robustly."""
        fmts = [
            "%b %d %H:%M:%S %Y %Z",  # e.g., 'Jun 12 12:34:56 2025 GMT'
            "%b %d %H:%M:%S %Y",  # without timezone
        ]
        for fmt in fmts:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        # As a last resort, strip trailing timezone token and try again
        parts = value.split()
        if parts and parts[-1].isalpha():
            try:
                return datetime.strptime(" ".join(parts[:-1]), "%b %d %H:%M:%S %Y")
            except ValueError:
                pass
        raise ValueError(f"Unrecognized certificate datetime format: {value}")

    def _flatten_name(self, name_seq) -> dict:
        """Flatten OpenSSL name tuples ((('key','val'),), ...) into a dict."""
        flattened = {}
        for rdn in name_seq or ():
            for k, v in rdn:
                flattened[k] = v
        return flattened

    def _parse_and_validate_cert(
        self, cert: dict | None, errors: list[str]
    ) -> CertificateInfo:
        """Helper to parse and validate certificate details."""
        now = datetime.now()

        if not cert:
            errors.append("No certificate received")
            return CertificateInfo(valid=False, errors=errors)

        try:
            not_before = self._parse_cert_datetime(cert["notBefore"])
            not_after = self._parse_cert_datetime(cert["notAfter"])
        except (KeyError, ValueError) as e:
            errors.append(f"Could not parse certificate dates: {e}")
            return CertificateInfo(valid=False, errors=errors)

        days_left = (not_after - now).days
        if now < not_before:
            errors.append("Certificate not yet valid")
        if now > not_after:
            errors.append("Certificate expired")
        if days_left < 30:
            errors.append(f"Certificate expires soon ({days_left} days)")

        return CertificateInfo(
            valid=len(errors) == 0,
            subject=self._flatten_name(cert.get("subject")),
            issuer=self._flatten_name(cert.get("issuer")),
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
