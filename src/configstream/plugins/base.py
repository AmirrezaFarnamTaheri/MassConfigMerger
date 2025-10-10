# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Plugin system for custom parsers and outputs."""
from abc import ABC, abstractmethod

class ParserPlugin(ABC):
    """Base class for custom config parsers."""

    @abstractmethod
    def can_parse(self, config: str) -> bool:
        """Check if this plugin can parse the config."""
        pass

    @abstractmethod
    def parse(self, config: str) -> dict:
        """Parse configuration."""
        pass

class OutputPlugin(ABC):
    """Base class for custom output formats."""

    @abstractmethod
    def format(self, nodes: list) -> str:
        """Format nodes for output."""
        pass