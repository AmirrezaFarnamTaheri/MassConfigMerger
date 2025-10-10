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
            url = f"http://ip-api.com/json/{ip}"
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

        # Run all checks in parallel
        results = await asyncio.gather(
            self.check_abuseipdb(ip),
            self.check_ipapi(ip),
            self.check_ipqualityscore(ip),
            return_exceptions=True
        )

        # Initialize result
        abuse_confidence = 0
        is_proxy = False
        is_vpn = False
        is_tor = False
        threat_types = []
        checked_services = []
        details = {}

        # Process AbuseIPDB results
        if isinstance(results[0], dict) and "error" not in results[0]:
            abuse_confidence = results[0].get("abuseConfidenceScore", 0)
            details["abuseipdb"] = results[0]
            checked_services.append("AbuseIPDB")

            # Extract threat information
            if results[0].get("isWhitelisted"):
                threat_types.append("whitelisted")
            if results[0].get("isTor"):
                is_tor = True
                threat_types.append("tor")

        # Process ip-api results
        if isinstance(results[1], dict) and results[1].get("status") == "success":
            is_proxy = results[1].get("proxy", False)
            is_vpn = results[1].get("hosting", False)  # Hosting often indicates VPN/proxy
            details["ipapi"] = results[1]
            checked_services.append("ip-api")

            if is_proxy:
                threat_types.append("proxy")
            if is_vpn:
                threat_types.append("hosting/vpn")

        # Process IPQualityScore results
        if isinstance(results[2], dict) and "error" not in results[2]:
            if results[2].get("proxy"):
                is_proxy = True
            if results[2].get("vpn"):
                is_vpn = True
            if results[2].get("tor"):
                is_tor = True

            details["ipqualityscore"] = results[2]
            checked_services.append("IPQualityScore")

            fraud_score = results[2].get("fraud_score", 0)
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

        logger.info(
            f"Reputation check complete for {ip}: {score.value} "
            f"(confidence: {abuse_confidence})"
        )

        return result