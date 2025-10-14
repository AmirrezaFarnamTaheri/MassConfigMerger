"""IP reputation checking against multiple services.

This module integrates with various IP reputation services to identify
potentially malicious or compromised VPN nodes.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from ipaddress import ip_address
from typing import Any, Callable, Coroutine, Dict, Optional

import aiohttp

from ..config import Settings

logger = logging.getLogger(__name__)


class ReputationScore(Enum):
    """IP reputation scores."""

    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"


@dataclass
class ReputationResult:
    """Result from IP reputation check."""

    score: ReputationScore = ReputationScore.UNKNOWN
    abuse_confidence: int = 0
    is_tor: bool = False
    is_proxy: bool = False
    is_vpn: bool = False
    threat_types: list[str] = field(default_factory=list)
    checked_services: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class IPReputationChecker:
    """Checks IP reputation against multiple services."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_keys = settings.security.api_keys or {}

    async def _check_service(
        self,
        service_name: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generic helper to perform a check against a URL-based service."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            logger.error(f"{service_name} check failed: {e}")
            return {"error": str(e)}

    async def check_abuseipdb(self, ip: str) -> Dict[str, Any]:
        """Check AbuseIPDB for IP reputation."""
        api_key = self.api_keys.get("abuseipdb")
        if not api_key:
            return {"error": "No API key configured"}
        return (
            await self._check_service(
                "AbuseIPDB",
                "https://api.abuseipdb.com/api/v2/check",
                headers={"Key": api_key, "Accept": "application/json"},
                params={"ipAddress": ip, "maxAgeInDays": 90, "verbose": ""},
            )
        ).get("data", {})

    async def check_ipapi(self, ip: str) -> Dict[str, Any]:
        """Check ip-api.com for IP information."""
        return await self._check_service(
            "ip-api",
            f"https://ip-api.com/json/{ip}",
            params={
                "fields": "status,message,country,countryCode,region,regionName,"
                "city,zip,lat,lon,timezone,isp,org,as,proxy,hosting"
            },
        )

    async def check_ipqualityscore(self, ip: str) -> Dict[str, Any]:
        """Check IPQualityScore for fraud/proxy detection."""
        api_key = self.api_keys.get("ipqualityscore")
        if not api_key:
            return {"error": "No API key configured"}
        url = f"https://ipqualityscore.com/api/json/ip/{api_key}/{ip}"
        return await self._check_service(
            "IPQualityScore",
            url,
            params={
                "strictness": 0,
                "allow_public_access_points": "true",
            },
        )

    def _process_abuseipdb(self, data: dict, result: ReputationResult):
        if "error" not in data:
            result.abuse_confidence = data.get("abuseConfidenceScore", 0)
            result.details["abuseipdb"] = data
            result.checked_services.append("AbuseIPDB")
            if data.get("isWhitelisted"):
                result.threat_types.append("whitelisted")
            if data.get("isTor"):
                result.is_tor = True
                result.threat_types.append("tor")

    def _process_ipapi(self, data: dict, result: ReputationResult):
        if data.get("status") == "success":
            result.is_proxy = data.get("proxy", False) or result.is_proxy
            result.is_vpn = data.get("hosting", False) or result.is_vpn
            result.details["ipapi"] = data
            result.checked_services.append("ip-api")
            if data.get("proxy"):
                result.threat_types.append("proxy")
            if data.get("hosting"):
                result.threat_types.append("hosting/vpn")

    def _process_ipqualityscore(self, data: dict, result: ReputationResult):
        if "error" not in data:
            result.is_proxy = data.get("proxy", False) or result.is_proxy
            result.is_vpn = data.get("vpn", False) or result.is_vpn
            result.is_tor = data.get("tor", False) or result.is_tor
            result.details["ipqualityscore"] = data
            result.checked_services.append("IPQualityScore")
            if data.get("fraud_score", 0) > 75:
                result.threat_types.append("high_fraud_score")

    def _determine_score(self, result: ReputationResult) -> ReputationScore:
        if result.abuse_confidence > 75:
            return ReputationScore.MALICIOUS
        if result.abuse_confidence > 25 or len(result.threat_types) > 2:
            return ReputationScore.SUSPICIOUS
        return (
            ReputationScore.CLEAN
            if result.checked_services
            else ReputationScore.UNKNOWN
        )

    async def check_all(self, ip: str) -> ReputationResult:
        """Check IP against all available services."""
        logger.info(f"Checking reputation for {ip}")
        result = ReputationResult()
        processors: Dict[str, Callable[[Dict, ReputationResult], None]] = {
            "abuseipdb": self._process_abuseipdb,
            "ip-api": self._process_ipapi,
            "ipqualityscore": self._process_ipqualityscore,
        }
        checks: Dict[str, Coroutine[Any, Any, dict]] = {
            "abuseipdb": self.check_abuseipdb(ip),
            "ip-api": self.check_ipapi(ip),
            "ipqualityscore": self.check_ipqualityscore(ip),
        }

        gathered = await asyncio.gather(*checks.values(), return_exceptions=True)
        for (service, _), res in zip(checks.items(), gathered):
            if isinstance(res, Exception):
                logger.warning(f"{service} check raised exception: {res}")
            elif isinstance(res, dict) and processors.get(service):
                processors[service](res, result)

        result.score = self._determine_score(result)
        masked_ip = self._mask_ip(ip)
        logger.info(
            f"Reputation check complete for {masked_ip}: {result.score.value} "
            f"(confidence: {result.abuse_confidence})"
        )
        return result

    def _mask_ip(self, ip: str) -> str:
        """Mask an IP address for safe logging."""
        try:
            ipa = ip_address(ip)
            return (
                ".".join(ip.split(".")[:3] + ["x"])
                if ipa.version == 4
                else ":".join(ip.split(":")[:-1] + ["xxxx"])
            )
        except ValueError:
            return "x.x.x.x"
