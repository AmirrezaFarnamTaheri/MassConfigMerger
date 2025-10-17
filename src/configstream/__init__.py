"""ConfigStream - VPN Configuration Aggregator"""

__version__ = "1.0.0"
__author__ = "Amirreza Farnam Taheri"

# Import core components if they exist
__all__ = []

try:
    from .config import Settings, settings
    __all__.extend(["Settings", "settings"])
except ImportError:
    pass

try:
    from .core import Proxy, ProxyTester, test_proxy, parse_config
    __all__.extend(["Proxy", "ProxyTester", "test_proxy", "parse_config"])
except ImportError:
    pass

try:
    from .pipeline import run_full_pipeline
    __all__.append("run_full_pipeline")
except ImportError:
    pass
