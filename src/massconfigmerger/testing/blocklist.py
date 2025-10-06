from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
from typing import Optional

import aiohttp

from ..config import Settings


def is_ip_address(host: str) -> bool:
    """Check if the given host is a valid IP address."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


class BlocklistChecker:
    """A utility for checking IPs against a blocklist."""

    _session: Optional[aiohttp.ClientSession] = None

    def __init__(self, config: Settings):
        self.config = config

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp client session."""
        if self._session is None or self._session.closed:
            try:
                self._session = aiohttp.ClientSession(
                    headers=self.config.network.headers
                )
            except Exception as exc:
                logging.warning("Failed to create aiohttp session: %s", exc)
                raise
        return self._session

    async def is_malicious(self, ip_address: str) -> bool:
        """Check if an IP address is considered malicious based on blocklist detections."""
        if (
            not self.config.security.apivoid_api_key
            or self.config.security.blocklist_detection_threshold <= 0
        ):
            return False

        if not ip_address or not is_ip_address(ip_address):
            return False

        session = await self.get_session()
        url = "https://endpoint.apivoid.com/iprep/v1/pay-as-you-go/"
        params = {"key": self.config.security.apivoid_api_key, "ip": ip_address}
        headers = {"Accept": "application/json"}

        try:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.config.network.request_timeout,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("error"):
                        logging.warning(
                            "APIVoid API error for IP %s: %s",
                            ip_address,
                            data["error"],
                        )
                        return False

                    detections = (
                        data.get("data", {})
                        .get("report", {})
                        .get("blacklists", {})
                        .get("detections", 0)
                    )
                    if (
                        detections
                        >= self.config.security.blocklist_detection_threshold
                    ):
                        logging.info(
                            "IP %s is on %d blacklists, marking as malicious.",
                            ip_address,
                            detections,
                        )
                        return True
                else:
                    logging.warning(
                        "APIVoid API request failed with status %d for IP %s",
                        resp.status,
                        ip_address,
                    )
        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            logging.warning(
                "APIVoid API request failed for IP %s: %s", ip_address, exc
            )

        return False

    async def close(self) -> None:
        """Close the aiohttp client session."""
        if self._session and not self._session.closed:
            await self._session.close()