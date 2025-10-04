"""Core components for processing and testing configurations."""

import asyncio
import re
from typing import List, Optional, Set, Tuple

from .. import utils
from ..config import Settings


class ConfigProcessor:
    """Processes, tests, and filters VPN configurations."""

    def __init__(self, settings: Settings):
        """
        Initialize the ConfigProcessor.

        Args:
            settings: The application settings.
        """
        self.settings = settings
        self.exclude_patterns = [
            re.compile(p, re.IGNORECASE) for p in settings.exclude_patterns
        ]
        self.include_patterns = [
            re.compile(p, re.IGNORECASE) for p in settings.include_patterns
        ]

    def filter_configs(
        self, configs: Set[str], protocols: Optional[List[str]] = None
    ) -> List[str]:
        """
        Filter configurations based on specified protocols and patterns.

        Args:
            configs: A set of configuration links.
            protocols: A list of protocols to include.

        Returns:
            A list of filtered configuration links.
        """
        filtered = []
        target_protocols = protocols or self.settings.protocols
        if target_protocols:
            target_protocols = [p.lower() for p in target_protocols]

        for link in sorted(c.strip() for c in configs):
            lower_link = link.lower()
            if target_protocols and not any(
                lower_link.startswith(p + "://") for p in target_protocols
            ):
                continue
            if any(r.search(lower_link) for r in self.exclude_patterns):
                continue
            if self.include_patterns and not any(
                r.search(lower_link) for r in self.include_patterns
            ):
                continue
            if not utils.is_valid_config(link):
                continue
            filtered.append(link)
        return filtered

    async def test_configs(
        self, configs: List[str]
    ) -> List[Tuple[str, Optional[float]]]:
        """
        Test the connectivity of a list of configurations.

        Args:
            configs: A list of configuration links.

        Returns:
            A list of tuples, each containing the configuration and its latency.
        """
        results = []
        semaphore = asyncio.Semaphore(self.settings.concurrent_limit)
        tester = utils.EnhancedConfigProcessor(self.settings)

        async def worker(config: str) -> Tuple[str, Optional[float]]:
            async with semaphore:
                host, port = tester.extract_host_port(config)
                if host and port:
                    return config, await tester.test_connection(host, port)
                return config, None

        tasks = [asyncio.create_task(worker(c)) for c in configs]
        for future in asyncio.as_completed(tasks):
            results.append(await future)

        await tester.tester.close()
        return results