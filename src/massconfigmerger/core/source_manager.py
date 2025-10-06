"""Core components for fetching and managing VPN configuration sources.

This module defines the `SourceManager`, a class responsible for handling
all aspects of fetching configuration data from web sources. This includes
managing aiohttp client sessions, fetching content from multiple URLs
concurrently, and a mechanism for checking the availability of sources
and pruning those that consistently fail.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Set

import aiohttp
from tqdm import tqdm

from .. import constants
from ..config import Settings
from ..exceptions import NetworkError
from . import utils


class SourceManager:
    """
    Manages fetching, filtering, and maintaining VPN configuration sources.

    This class encapsulates the logic for handling aiohttp sessions,
    concurrently fetching data from a list of URLs, and performing
    health checks on sources to prune failing ones.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the SourceManager.

        Args:
            settings: The application settings object, which provides
                      networking and proxy configurations.
        """
        self.settings = settings
        self.session: aiohttp.ClientSession | None = None
        # Circuit Breaker state
        self._circuit_states: Dict[str, str] = {}  # "CLOSED", "OPEN", "HALF_OPEN"
        self._failure_counts: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        # Circuit Breaker parameters
        self.FAILURE_THRESHOLD = 3
        self.RETRY_TIMEOUT = 60  # 60 seconds

    async def get_session(self) -> aiohttp.ClientSession:
        """
        Get the aiohttp ClientSession, creating it if it doesn't exist.

        This method ensures that a single session is reused for multiple
        requests, which is more efficient. It configures the session with
        the appropriate connector.

        Returns:
            An active aiohttp.ClientSession instance.
        """
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(limit=self.settings.network.concurrent_limit)
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session

    async def close_session(self) -> None:
        """Close the aiohttp session if it is open."""
        if self.session and not self.session.closed:
            await self.session.close()

    def _get_circuit_state(self, url: str) -> str:
        """Get the current state of the circuit for a given URL."""
        state = self._circuit_states.get(url, "CLOSED")
        if state == "OPEN":
            if time.time() - self._last_failure_time.get(url, 0) > self.RETRY_TIMEOUT:
                self._circuit_states[url] = "HALF_OPEN"
                return "HALF_OPEN"
        return state

    async def fetch_sources(self, sources: List[str]) -> Set[str]:
        """
        Fetch configurations from a list of source URLs.

        This method concurrently fetches content from all provided URLs,
        parses the text to extract configuration links, and returns a
        unified set of all found configurations.

        Args:
            sources: A list of source URLs to fetch.

        Returns:
            A set of unique configuration links found in the sources.
        """
        configs: Set[str] = set()
        semaphore = asyncio.Semaphore(self.settings.network.concurrent_limit)
        session = await self.get_session()
        proxy = utils.choose_proxy(self.settings)

        async def fetch_one(url: str) -> Set[str]:
            circuit_state = self._get_circuit_state(url)
            if circuit_state == "OPEN":
                logging.debug("Circuit for %s is open, skipping fetch.", url)
                return set()

            try:
                async with semaphore:
                    text = await utils.fetch_text(
                        session,
                        url,
                        timeout=self.settings.network.request_timeout,
                        retries=self.settings.network.retry_attempts,
                        base_delay=self.settings.network.retry_base_delay,
                        proxy=proxy,
                    )
                # Success
                if circuit_state == "HALF_OPEN":
                    logging.info("Circuit for %s has been closed.", url)
                self._circuit_states.pop(url, None)
                self._failure_counts.pop(url, None)
                self._last_failure_time.pop(url, None)
                return utils.parse_configs_from_text(text)
            except NetworkError as e:
                # Failure
                self._failure_counts[url] = self._failure_counts.get(url, 0) + 1
                if self._failure_counts[url] >= self.FAILURE_THRESHOLD:
                    self._circuit_states[url] = "OPEN"
                    self._last_failure_time[url] = time.time()
                    logging.warning(
                        "Circuit for %s opened after %d failures.",
                        url,
                        self._failure_counts[url],
                    )
                if circuit_state == "HALF_OPEN":
                    self._circuit_states[url] = "OPEN"
                    self._last_failure_time[url] = time.time()

                logging.warning("Failed to fetch %s: %s", url, e)
                return set()

        tasks = [asyncio.create_task(fetch_one(u)) for u in sources]
        for task in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc="Fetching sources",
            unit="source",
        ):
            configs.update(await task)
        return configs

    async def check_and_update_sources(
        self,
        path: Path,
        max_failures: int = 3,
        prune: bool = True,
    ) -> List[str]:
        """
        Check the availability of sources and optionally prune failing ones.

        This method reads a list of source URLs from a file, tests each one
        for availability, and updates a failure count. If a source exceeds
        the `max_failures` threshold, it is removed from the list.

        Args:
            path: The path to the file containing the source URLs.
            max_failures: The maximum number of consecutive failures before
                          a source is pruned.
            prune: If True, remove failing sources from the file.

        Returns:
            A list of source URLs that were found to be available.
        """
        if not path.exists():
            logging.warning("sources file not found: %s", path)
            return []

        failures_path = path.with_suffix(constants.SOURCES_FAILURES_FILE_SUFFIX)
        try:
            failures = json.loads(failures_path.read_text())
        except (OSError, json.JSONDecodeError):
            failures = {}

        with path.open() as f:
            sources = [line.strip() for line in f if line.strip()]

        valid_sources: List[str] = []
        removed: List[str] = []
        semaphore = asyncio.Semaphore(self.settings.network.concurrent_limit)
        session = await self.get_session()
        proxy = utils.choose_proxy(self.settings)

        async def check(url: str) -> tuple[str, bool]:
            try:
                async with semaphore:
                    text = await utils.fetch_text(
                        session,
                        url,
                        timeout=self.settings.network.request_timeout,
                        retries=self.settings.network.retry_attempts,
                        base_delay=self.settings.network.retry_base_delay,
                        proxy=proxy,
                    )
                return url, bool(text and utils.parse_configs_from_text(text))
            except NetworkError as e:
                logging.debug("Source check failed for %s: %s", url, e)
                return url, False

        tasks = [asyncio.create_task(check(u)) for u in sources]
        for task in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc="Checking sources",
            unit="source",
        ):
            url, ok = await task
            if ok:
                failures.pop(url, None)
                valid_sources.append(url)
            else:
                failures[url] = failures.get(url, 0) + 1
                if prune and failures[url] >= max_failures:
                    removed.append(url)

        if prune:
            remaining = [u for u in sources if u not in removed]
            with path.open("w") as f:
                for url in remaining:
                    f.write(f"{url}\n")

            if removed:
                disabled_path = path.with_name(constants.SOURCES_DISABLED_FILE_NAME)
                with disabled_path.open("a") as f:
                    for url in removed:
                        f.write(f"{url}\n")
                # Remove pruned sources from the failures dict
                for url in removed:
                    failures.pop(url, None)

        failures_path.write_text(json.dumps(failures, indent=2))
        logging.info("Valid sources: %d", len(valid_sources))
        return valid_sources
