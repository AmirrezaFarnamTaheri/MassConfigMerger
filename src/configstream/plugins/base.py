"""Base classes for the ConfigStream plugin system.

This module defines the interfaces that plugins must implement.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PluginMetadata:
    """Metadata for a plugin.

    Attributes:
        name: Plugin name
        version: Plugin version
        author: Plugin author
        description: Short description
        priority: Loading priority (lower = earlier)
    """
    name: str
    version: str
    author: str
    description: str
    priority: int = 100


class ParserPlugin(ABC):
    """Base class for custom configuration parsers.

    Parser plugins can handle custom VPN configuration formats
    beyond the built-in protocols.

    Example:
        class MyCustomParser(ParserPlugin):
            @property
            def metadata(self):
                return PluginMetadata(
                    name="my-parser",
                    version="1.0.0",
                    author="Me",
                    description="Parses my custom format"
                )

            def can_parse(self, config):
                return config.startswith("mycustom://")

            def parse(self, config):
                # Parse and return dict
                return {...}
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass

    @abstractmethod
    def can_parse(self, config: str) -> bool:
        """Check if this plugin can parse the given configuration.

        Args:
            config: Raw configuration string

        Returns:
            True if this plugin can handle this config
        """
        pass

    @abstractmethod
    def parse(self, config: str) -> Dict[str, Any]:
        """Parse configuration string into structured data.

        Args:
            config: Raw configuration string

        Returns:
            Dictionary with parsed data
            Required fields:
            - protocol: str
            - host: str
            - port: int
            Optional fields depend on protocol
        """
        pass


class OutputPlugin(ABC):
    """Base class for custom output formatters.

    Output plugins can generate configuration files in
    custom formats for different VPN clients.

    Example:
        class MyFormatOutput(OutputPlugin):
            @property
            def metadata(self):
                return PluginMetadata(
                    name="myformat",
                    version="1.0.0",
                    author="Me",
                    description="Outputs in my format"
                )

            @property
            def file_extension(self):
                return ".myformat"

            def format(self, nodes):
                # Convert nodes to custom format
                return "..."
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Get file extension for this format (e.g., '.yaml')."""
        pass

    @abstractmethod
    def format(self, nodes: List[Dict[str, Any]]) -> str:
        """Format nodes into output string.

        Args:
            nodes: List of node dictionaries

        Returns:
            Formatted string ready to write to file
        """
        pass


class FilterPlugin(ABC):
    """Base class for custom node filters.

    Filter plugins can implement custom logic for
    filtering VPN nodes based on various criteria.

    Example:
        class CountryFilter(FilterPlugin):
            def __init__(self, allowed_countries):
                self.allowed = allowed_countries

            def filter(self, node):
                return node.get("country") in self.allowed
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass

    @abstractmethod
    def filter(self, node: Dict[str, Any]) -> bool:
        """Check if node should be included.

        Args:
            node: Node dictionary with all metadata

        Returns:
            True if node should be kept, False to filter out
        """
        pass


class TestPlugin(ABC):
    """Base class for custom testing methods.

    Test plugins can add additional testing capabilities
    beyond the built-in tests.

    Example:
        class DNSLeakTest(TestPlugin):
            async def test(self, node):
                # Perform DNS leak test
                return {"dns_leaked": False}
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass

    @abstractmethod
    async def test(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Perform test on node.

        Args:
            node: Node dictionary with host/port/etc

        Returns:
            Dictionary with test results
            Keys should be descriptive (e.g., "dns_leak_detected": bool)
        """
        pass