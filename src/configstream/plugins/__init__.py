from abc import ABC, abstractmethod
from typing import Any, Dict, List
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

from ..core import Proxy

class Plugin(ABC):
    """Base plugin interface"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin"""
        pass

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin logic"""
        pass


class SourcePlugin(Plugin):
    """Plugin for fetching proxy sources"""

    @abstractmethod
    async def fetch_proxies(self, url: str) -> List[str]:
        """Fetch proxies from source"""
        pass


class FilterPlugin(Plugin):
    """Plugin for filtering proxies"""

    @abstractmethod
    async def filter_proxies(self, proxies: List['Proxy']) -> List['Proxy']:
        """Filter proxies based on criteria"""
        pass


class ExportPlugin(Plugin):
    """Plugin for exporting configurations"""

    @abstractmethod
    async def export(self, proxies: List['Proxy'], output_path: Path) -> None:
        """Export proxies to specific format"""
        pass
