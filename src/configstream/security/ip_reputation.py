"""IP reputation checking against multiple services."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

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
    """Result from IP reputation check."""
    score: ReputationScore
    details: dict[str, any]
    checked_services: list[str]

class IPReputationChecker:
    """Checks IP reputation against multiple services."""

    def __init__(self, api_keys: dict[str, str] | None = None):
        self.api_keys = api_keys or {}

    async def check_abuseipdb(self, ip: str) -> dict:
        """Check AbuseIPDB (requires API key)."""
        if "abuseipdb" not in self.api_keys:
            return {"error": "No API key"}

        try:
            url = "https://api.abuseipdb.com/api/v2/check"
            headers = {
                "Key": self.api_keys["abuseipdb"],
                "Accept": "application/json"
            }
            params = {"ipAddress": ip, "maxAgeInDays": 90}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", {})

        except Exception as e:
            logger.error(f"AbuseIPDB check failed: {e}")

        return {"error": "Check failed"}

    async def check_virustotal(self, ip: str) -> dict:
        """Check VirusTotal (requires API key)."""
        if "virustotal" not in self.api_keys:
            return {"error": "No API key"}

        try:
            url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}"
            headers = {"x-apikey": self.api_keys["virustotal"]}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.json()

        except Exception as e:
            logger.error(f"VirusTotal check failed: {e}")

        return {"error": "Check failed"}

    async def check_all(self, ip: str) -> ReputationResult:
        """Check IP against all available services."""
        results = await asyncio.gather(
            self.check_abuseipdb(ip),
            self.check_virustotal(ip),
            return_exceptions=True
        )

        # Analyze results
        abuse_score = 0
        details = {}
        checked = []

        # AbuseIPDB
        if isinstance(results[0], dict) and "error" not in results[0]:
            abuse_score = results[0].get("abuseConfidenceScore", 0)
            details["abuseipdb"] = results[0]
            checked.append("AbuseIPDB")

        # VirusTotal
        if isinstance(results[1], dict) and "error" not in results[1]:
            details["virustotal"] = results[1]
            checked.append("VirusTotal")

        # Determine overall score
        if abuse_score > 75:
            score = ReputationScore.MALICIOUS
        elif abuse_score > 25:
            score = ReputationScore.SUSPICIOUS
        elif checked:
            score = ReputationScore.CLEAN
        else:
            score = ReputationScore.UNKNOWN

        return ReputationResult(
            score=score,
            details=details,
            checked_services=checked
        )