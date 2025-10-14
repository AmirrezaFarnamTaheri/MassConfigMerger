from __future__ import annotations

import logging
from typing import Any, Dict, List

import yaml

from .proxy_parser import ProxyParser


class FormatConverter:
    """Converts a list of proxy configs to various output formats."""

    def __init__(self, configs: List[str]):
        """
        Initialize the FormatConverter.

        Args:
            configs: A list of configuration strings.
        """
        self.configs = configs
        self.proxies = self._generate_clash_proxies()

    def _generate_clash_proxies(self) -> List[Dict[str, Any]]:
        """Generate a list of Clash-compatible proxy dictionaries."""
        parser = ProxyParser()
        proxies: List[Dict[str, Any]] = []
        for i, config in enumerate(self.configs):
            try:
                proxy = parser.config_to_clash_proxy(config, idx=i)
                if proxy:
                    proxies.append(proxy)
            except Exception as e:
                logging.debug(f"Could not parse config for Clash: {config}, error: {e}")
        return proxies

    def to_clash_config(self) -> str:
        """Generate content for a Clash configuration file."""
        if not self.proxies:
            return ""

        proxy_names = [p["name"] for p in self.proxies]

        clash_config = {
            "proxies": self.proxies,
            "proxy-groups": [
                {
                    "name": "PROXY",
                    "type": "select",
                    "proxies": ["DIRECT", "REJECT"] + proxy_names,
                }
            ],
            "rules": ["MATCH,PROXY"],
        }

        class NoAliasDumper(yaml.SafeDumper):
            def ignore_aliases(self, data):
                return True

        return yaml.dump(
            clash_config, Dumper=NoAliasDumper, allow_unicode=True, sort_keys=False
        )

    def to_clash_proxies(self) -> str:
        """Generate content for a Clash proxies-only file."""
        if not self.proxies:
            return ""

        clash_proxies = {"proxies": self.proxies}

        class NoAliasDumper(yaml.SafeDumper):
            def ignore_aliases(self, data):
                return True

        return yaml.dump(
            clash_proxies, Dumper=NoAliasDumper, allow_unicode=True, sort_keys=False
        )
