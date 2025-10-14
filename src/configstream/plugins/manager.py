"""Plugin manager for loading and managing plugins.

This module handles plugin discovery, loading, and registration.
"""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import List

from .base import ParserPlugin, OutputPlugin, FilterPlugin, TestPlugin

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages all plugins for ConfigStream.

    This class handles:
    - Plugin discovery and loading
    - Plugin registration
    - Plugin retrieval by type

    Example:
        >>> manager = PluginManager()
        >>> manager.discover_plugins()
        >>> parsers = manager.get_parsers()
    """

    def __init__(self):
        self.parsers: List[ParserPlugin] = []
        self.outputs: List[OutputPlugin] = []
        self.filters: List[FilterPlugin] = []
        self.tests: List[TestPlugin] = []

    def register_parser(self, parser: ParserPlugin):
        """Register a parser plugin.

        Args:
            parser: Parser plugin instance
        """
        self.parsers.append(parser)
        self.parsers.sort(key=lambda p: p.metadata.priority)
        logger.info(f"Registered parser plugin: {parser.metadata.name}")

    def register_output(self, output: OutputPlugin):
        """Register an output plugin.

        Args:
            output: Output plugin instance
        """
        self.outputs.append(output)
        self.outputs.sort(key=lambda p: p.metadata.priority)
        logger.info(f"Registered output plugin: {output.metadata.name}")

    def register_filter(self, filter_plugin: FilterPlugin):
        """Register a filter plugin.

        Args:
            filter_plugin: Filter plugin instance
        """
        self.filters.append(filter_plugin)
        self.filters.sort(key=lambda p: p.metadata.priority)
        logger.info(f"Registered filter plugin: {filter_plugin.metadata.name}")

    def register_test(self, test: TestPlugin):
        """Register a test plugin.

        Args:
            test: Test plugin instance
        """
        self.tests.append(test)
        self.tests.sort(key=lambda p: p.metadata.priority)
        logger.info(f"Registered test plugin: {test.metadata.name}")

    def get_parsers(self) -> List[ParserPlugin]:
        """Get all registered parser plugins."""
        return self.parsers

    def get_outputs(self) -> List[OutputPlugin]:
        """Get all registered output plugins."""
        return self.outputs

    def get_filters(self) -> List[FilterPlugin]:
        """Get all registered filter plugins."""
        return self.filters

    def get_tests(self) -> List[TestPlugin]:
        """Get all registered test plugins."""
        return self.tests

    def find_parser(self, config: str) -> ParserPlugin | None:
        """Find a parser that can handle this config.

        Args:
            config: Configuration string

        Returns:
            Parser plugin or None if no parser found
        """
        for parser in self.parsers:
            if parser.can_parse(config):
                return parser
        return None

    def get_output_by_name(self, name: str) -> OutputPlugin | None:
        """Get output plugin by name.

        Args:
            name: Plugin name

        Returns:
            Output plugin or None
        """
        for output in self.outputs:
            if output.metadata.name == name:
                return output
        return None

    def discover_plugins(self, plugin_dirs: List[Path] = None):
        """Discover and load plugins from directories.

        Args:
            plugin_dirs: List of directories to search for plugins
                        Defaults to ~/.configstream/plugins
        """
        if plugin_dirs is None:
            plugin_dirs = [Path.home() / ".configstream" / "plugins", Path("./plugins")]

        for plugin_dir in plugin_dirs:
            if not plugin_dir.exists():
                continue

            logger.info(f"Searching for plugins in {plugin_dir}")

            # Add to Python path
            if str(plugin_dir) not in sys.path:
                sys.path.insert(0, str(plugin_dir))

            # Find all Python files
            for py_file in plugin_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                module_name = py_file.stem

                try:
                    # Import module
                    module = importlib.import_module(module_name)

                    # Look for plugin classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)

                        # Check if it's a plugin class
                        if not isinstance(attr, type):
                            continue

                        # Register based on type
                        if issubclass(attr, ParserPlugin) and attr is not ParserPlugin:
                            self.register_parser(attr())
                        elif (
                            issubclass(attr, OutputPlugin) and attr is not OutputPlugin
                        ):
                            self.register_output(attr())
                        elif (
                            issubclass(attr, FilterPlugin) and attr is not FilterPlugin
                        ):
                            self.register_filter(attr())
                        elif issubclass(attr, TestPlugin) and attr is not TestPlugin:
                            self.register_test(attr())

                    logger.info(f"Loaded plugins from {module_name}")

                except Exception as e:
                    logger.error(f"Failed to load plugin {module_name}: {e}")


# Global plugin manager instance
plugin_manager = PluginManager()
