"""ConfigStream - VPN Configuration Aggregator"""

__version__ = "1.0.0"
__author__ = "Amirreza Farnam Taheri"

# Import core components if they exist
__all__ = []

try:
    pass

    __all__.extend(["Settings", "settings"])
except ImportError:
    pass

try:
    pass

    __all__.extend(["Proxy", "ProxyTester", "test_proxy", "parse_config"])
except ImportError:
    pass

try:
    pass

    __all__.append("run_full_pipeline")
except ImportError:
    pass