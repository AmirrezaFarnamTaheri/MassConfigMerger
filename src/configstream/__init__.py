"""
ConfigStream - VPN Configuration Aggregator

This package provides tools to fetch, test, and manage VPN configurations
from various sources.
"""

__version__ = "1.0.0"
__author__ = "Amirreza 'Farnam' Taheri"

# Import key components to be available at the package level
from .core import Proxy, ProxyTester, parse_config
from .pipeline import run_full_pipeline
from .config import AppSettings

# Define the public API of the package
__all__ = [
    "Proxy",
    "ProxyTester",
    "parse_config",
    "run_full_pipeline",
    "AppSettings",
    "__version__",
    "__author__",
]