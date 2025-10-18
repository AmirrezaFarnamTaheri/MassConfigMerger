from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..core import Proxy


class Plugin(ABC):
    """Base plugin interface"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize plugin"""

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute plugin logic"""


class SourcePlugin(Plugin):
    """Plugin for fetching proxy sources"""

    @abstractmethod
    async def fetch_proxies(self, url: str) -> list[str]:
        """Fetch proxies from source"""


class FilterPlugin(Plugin):
    """Plugin for filtering proxies"""

    @abstractmethod
    async def filter_proxies(self, proxies: list["Proxy"]) -> list["Proxy"]:
        """Filter proxies based on criteria"""


class ExportPlugin(Plugin):
    """Plugin for exporting configurations"""

    @abstractmethod
    async def export(self, proxies: list["Proxy"], output_path: Path) -> None:
        """Export proxies to specific format"""
