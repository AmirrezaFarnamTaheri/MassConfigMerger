"""Prometheus metrics definitions for the ConfigStream application."""

from prometheus_client import Counter, Histogram

# --- Source Metrics ---
SOURCES_FETCHED_TOTAL = Counter(
    "configstream_sources_fetched", "Total number of sources fetched."
)
SOURCES_FAILED_TOTAL = Counter(
    "configstream_sources_failed", "Total number of sources that failed to fetch."
)

# --- Config Metrics ---
CONFIGS_TESTED_TOTAL = Counter(
    "configstream_configs_tested", "Total number of configurations tested."
)
CONFIGS_REACHABLE_TOTAL = Counter(
    "configstream_configs_reachable", "Total number of reachable configurations found."
)

# --- Performance Metrics ---
CONFIG_LATENCY_SECONDS = Histogram(
    "configstream_config_latency_seconds",
    "Latency of tested configurations in seconds.",
    buckets=[0.1, 0.2, 0.5, 1, 2, 5, 10, float("inf")],
)
