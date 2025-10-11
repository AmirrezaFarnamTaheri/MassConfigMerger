"""IP reputation checking against multiple services.

This module integrates with various IP reputation services to identify
potentially malicious or compromised VPN nodes.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Any
from ipaddress import ip_address

import aiohttp

logger = logging.getLogger(__name__)


class ReputationScore(Enum):
    """IP reputation scores."""
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"


@dataclass
class ReputationResult:
    """Result from IP reputation check.

    Attributes:
        score: Overall reputation score
        abuse_confidence: Confidence score from AbuseIPDB (0-100)
        is_tor: Whether IP is a Tor exit node
        is_proxy: Whether IP is a known proxy
        is_vpn: Whether IP is a known VPN
        threat_types: List of threat types detected
        checked_services: List of services that were checked
        details: Raw details from all services
    """
    score: ReputationScore
    abuse_confidence: int = 0
    is_tor: bool = False
    is_proxy: bool = False
    is_vpn: bool = False
    threat_types: list[str] = None
    checked_services: list[str] = None
    details: dict[str, Any] = None

    def __post_init__(self):
        if self.threat_types is None:
            self.threat_types = []
        if self.checked_services is None:
            self.checked_services = []
        if self.details is None:
            self.details = {}


class IPReputationChecker:
    """Checks IP reputation against multiple services.

    Supports:
    - AbuseIPDB (requires API key)
    - IPQualityScore (requires API key)
    - ip-api.com (free, no key required)

    Example:
        >>> checker = IPReputationChecker(
        ...     api_keys={"abuseipdb": "your-key"}
        ... )
        >>> result = await checker.check_all("1.2.3.4")
        >>> print(f"Score: {result.score}")
    """

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        """Initialize reputation checker.

        Args:
            api_keys: Dictionary of API keys for various services
                     Format: {"service_name": "api_key"}
        """
        self.api_keys = api_keys or {}

    async def check_abuseipdb(self, ip: str) -> Dict[str, Any]:
        """Check AbuseIPDB for IP reputation.

        Args:
            ip: IP address to check

        Returns:
            Dictionary with abuse information
        """
        if "abuseipdb" not in self.api_keys:
            return {"error": "No API key configured"}

        try:
            url = "https://api.abuseipdb.com/api/v2/check"
            headers = {
                "Key": self.api_keys["abuseipdb"],
                "Accept": "application/json"
            }
            params = {
                "ipAddress": ip,
                "maxAgeInDays": 90,
                "verbose": ""
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", {})
                    else:
                        return {"error": f"HTTP {resp.status}"}

        except Exception as e:
            logger.error(f"AbuseIPDB check failed: {e}")
            return {"error": str(e)}

    async def check_ipapi(self, ip: str) -> Dict[str, Any]:
        """Check ip-api.com for IP information (free service).

        Args:
            ip: IP address to check

        Returns:
            Dictionary with IP information
        """
        try:
            url = f"https://ip-api.com/json/{ip}"
            params = {
                "fields": "status,message,country,countryCode,region,regionName,"
                         "city,zip,lat,lon,timezone,isp,org,as,proxy,hosting"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"error": f"HTTP {resp.status}"}

        except Exception as e:
            logger.error(f"ip-api check failed: {e}")
            return {"error": str(e)}

    async def check_ipqualityscore(self, ip: str) -> Dict[str, Any]:
        """Check IPQualityScore for fraud/proxy detection.

        Args:
            ip: IP address to check

        Returns:
            Dictionary with quality score information
        """
        if "ipqualityscore" not in self.api_keys:
            return {"error": "No API key configured"}

        try:
            key = self.api_keys["ipqualityscore"]
            url = f"https://ipqualityscore.com/api/json/ip/{key}/{ip}"
            params = {
                "strictness": 0,
                "allow_public_access_points": "true"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"error": f"HTTP {resp.status}"}

        except Exception as e:
            logger.error(f"IPQualityScore check failed: {e}")
            return {"error": str(e)}

    async def check_all(self, ip: str) -> ReputationResult:
        """Check IP against all available services.

        Args:
            ip: IP address to check

        Returns:
            ReputationResult with aggregated data
        """
        logger.info(f"Checking reputation for {ip}")

        checks = {
            "abuseipdb": self.check_abuseipdb(ip),
            "ip-api": self.check_ipapi(ip),
            "ipqualityscore": self.check_ipqualityscore(ip),
        }
        gathered = await asyncio.gather(*checks.values(), return_exceptions=True)

        service_results: dict[str, dict] = {}
        for (service, _), result in zip(checks.items(), gathered):
            if isinstance(result, Exception):
                logger.warning(f"{service} check raised exception: {result}")
                continue
            if isinstance(result, dict):
                service_results[service] = result
            else:
                logger.warning(f"{service} returned unexpected type: {type(result)}")

        # Initialize result
        abuse_confidence = 0
        is_proxy = False
        is_vpn = False
        is_tor = False
        threat_types = []
        checked_services = []
        details = {}

        # Process AbuseIPDB
        abuse_data = service_results.get("abuseipdb")
        if abuse_data and "error" not in abuse_data:
            abuse_confidence = abuse_data.get("abuseConfidenceScore", 0)
            details["abuseipdb"] = abuse_data
            checked_services.append("AbuseIPDB")
            if abuse_data.get("isWhitelisted"):
                threat_types.append("whitelisted")
            if abuse_data.get("isTor"):
                is_tor = True
                threat_types.append("tor")

        # Process ip-api
        ipapi_data = service_results.get("ip-api")
        if ipapi_data and ipapi_data.get("status") == "success":
            is_proxy = ipapi_data.get("proxy", False) or is_proxy
            is_vpn = ipapi_data.get("hosting", False) or is_vpn
            details["ipapi"] = ipapi_data
            checked_services.append("ip-api")
            if ipapi_data.get("proxy"):
                threat_types.append("proxy")
            if ipapi_data.get("hosting"):
                threat_types.append("hosting/vpn")

        # Process IPQualityScore
        ipqs_data = service_results.get("ipqualityscore")
        if ipqs_data and "error" not in ipqs_data:
            if ipqs_data.get("proxy"):
                is_proxy = True
            if ipqs_data.get("vpn"):
                is_vpn = True
            if ipqs_data.get("tor"):
                is_tor = True
            details["ipqualityscore"] = ipqs_data
            checked_services.append("IPQualityScore")
            fraud_score = ipqs_data.get("fraud_score", 0)
            if fraud_score > 75:
                threat_types.append("high_fraud_score")

        # Determine overall reputation score
        if abuse_confidence > 75:
            score = ReputationScore.MALICIOUS
        elif abuse_confidence > 25 or len(threat_types) > 2:
            score = ReputationScore.SUSPICIOUS
        elif checked_services:
            score = ReputationScore.CLEAN
        else:
            score = ReputationScore.UNKNOWN

        result = ReputationResult(
            score=score,
            abuse_confidence=abuse_confidence,
            is_tor=is_tor,
            is_proxy=is_proxy,
            is_vpn=is_vpn,
            threat_types=threat_types,
            checked_services=checked_services,
            details=details
        )

        # Robust IP masking for logs
        try:
            ipa = ip_address(ip)
            if ipa.version == 4:
                parts = ip.split(".")
                masked_ip = ".".join(parts[:3] + ["x"])
            else:
                # IPv6: mask the last hextet
                parts = ip.split(":")
                if len(parts) > 1:
                    parts[-1] = "xxxx"
                masked_ip = ":".join(parts)
        except Exception:
            # Fallback if parsing fails
            masked_ip = "x.x.x.x"

        logger.info(
            f"Reputation check complete for {masked_ip}: {score.value} "
            f"(confidence: {abuse_confidence})")

        return result