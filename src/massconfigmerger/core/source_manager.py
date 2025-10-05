"""Core components for fetching and managing configuration sources."""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Set

import aiohttp
from tqdm import tqdm

from . import utils
from ..config import Settings


class SourceManager:
    """Manages fetching and filtering of VPN configuration sources."""

    def __init__(self, settings: Settings):
        """
        Initialize the SourceManager.

        Args:
            settings: The application settings.
        """
        self.settings = settings
        self.session: aiohttp.ClientSession | None = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get the aiohttp session, creating it if it doesn't exist."""
        if self.session is None or self.session.closed:
            proxy = utils.choose_proxy(self.settings)
            connector = aiohttp.TCPConnector(limit=self.settings.network.concurrent_limit)
            self.session = aiohttp.ClientSession(connector=connector, proxy=proxy)
        return self.session

    async def close_session(self) -> None:
        """Close the aiohttp session if it exists."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def fetch_sources(self, sources: List[str]) -> Set[str]:
        """
        Fetch configurations from a list of sources.

        Args:
            sources: A list of source URLs.

        Returns:
            A set of unique configuration links.
        """
        configs: Set[str] = set()
        semaphore = asyncio.Semaphore(self.settings.network.concurrent_limit)
        session = await self.get_session()

        async def fetch_one(url: str) -> Set[str]:
            async with semaphore:
                text = await utils.fetch_text(
                    session,
                    url,
                    self.settings.network.request_timeout,
                    retries=self.settings.network.retry_attempts,
                    base_delay=self.settings.network.retry_base_delay,
                    proxy=utils.choose_proxy(self.settings),
                )
            if not text:
                logging.warning("Failed to fetch %s", url)
                return set()
            return utils.parse_configs_from_text(text)

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

        Args:
            path: The path to the sources file.
            max_failures: The maximum number of failures before pruning a source.
            prune: Whether to prune failing sources.

        Returns:
            A list of available source URLs.
        """
        if not path.exists():
            logging.warning("sources file not found: %s", path)
            return []

        failures_path = path.with_suffix(".failures.json")
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

        async def check(url: str) -> tuple[str, bool]:
            async with semaphore:
                text = await utils.fetch_text(
                    session,
                    url,
                    self.settings.network.request_timeout,
                    retries=self.settings.network.retry_attempts,
                    base_delay=self.settings.network.retry_base_delay,
                    proxy=utils.choose_proxy(self.settings),
                )
            return url, bool(text and utils.parse_configs_from_text(text))

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
                    f.write(f"{url}\\n")

            if removed:
                disabled_path = path.with_name("sources_disabled.txt")
                with disabled_path.open("a") as f:
                    for url in removed:
                        f.write(f"{url}\\n")

        failures_path.write_text(json.dumps(failures, indent=2))
        logging.info("Valid sources: %d", len(valid_sources))
        return valid_sources
