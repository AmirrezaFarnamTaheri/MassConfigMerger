"""Prometheus metrics exporter for ConfigStream.

Exposes VPN node metrics in Prometheus format for monitoring.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict

from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

logger = logging.getLogger(__name__)


# Define metrics
vpn_nodes_total = Gauge(
    "configstream_vpn_nodes_total", "Total number of VPN nodes tested"
)

vpn_nodes_successful = Gauge(
    "configstream_vpn_nodes_successful", "Number of successful VPN nodes"
)

vpn_nodes_failed = Gauge("configstream_vpn_nodes_failed", "Number of failed VPN nodes")

vpn_avg_ping_ms = Gauge(
    "configstream_avg_ping_milliseconds", "Average ping time in milliseconds"
)

vpn_nodes_by_protocol = Gauge(
    "configstream_nodes_by_protocol", "Number of nodes by protocol", ["protocol"]
)

vpn_nodes_by_country = Gauge(
    "configstream_nodes_by_country", "Number of nodes by country", ["country"]
)

vpn_test_cycles_total = Counter(
    "configstream_test_cycles_total", "Total number of test cycles run"
)

vpn_test_duration_seconds = Histogram(
    "configstream_test_duration_seconds", "Duration of test cycles in seconds"
)

vpn_avg_quality_score = Gauge(
    "configstream_avg_quality_score", "Average network quality score (0-100)"
)

vpn_info = Info("configstream", "ConfigStream version and configuration info")


class PrometheusExporter:
    """Prometheus metrics exporter.

    Reads test results and updates Prometheus metrics.

    Example:
        >>> exporter = PrometheusExporter(data_dir=Path("./data"))
        >>> exporter.start(port=9090)
    """

    def __init__(self, data_dir: Path):
        """Initialize exporter.

        Args:
            data_dir: Directory containing test results
        """
        self.data_dir = data_dir
        self.current_file = data_dir / "current_results.json"

        # Set version info
        vpn_info.info({"version": "0.4.0", "python_version": "3.10+"})

    def update_metrics(self):
        """Update all metrics from current test results."""
        if not self.current_file.exists():
            logger.warning("No test results file found")
            return

        try:
            data = json.loads(self.current_file.read_text())

            nodes = data.get("nodes", [])
            successful = [n for n in nodes if n.get("ping_ms", 0) > 0]
            failed = [n for n in nodes if n.get("ping_ms", 0) < 0]

            # Update basic counts
            vpn_nodes_total.set(len(nodes))
            vpn_nodes_successful.set(len(successful))
            vpn_nodes_failed.set(len(failed))

            # Update average ping
            if successful:
                avg_ping = sum(n["ping_ms"] for n in successful) / len(successful)
                vpn_avg_ping_ms.set(avg_ping)

            # Update protocol distribution
            protocols: Dict[str, int] = {}
            for node in nodes:
                proto = node.get("protocol", "unknown")
                protocols[proto] = protocols.get(proto, 0) + 1

            for protocol, count in protocols.items():
                vpn_nodes_by_protocol.labels(protocol=protocol).set(count)

            # Update country distribution
            countries: Dict[str, int] = {}
            for node in nodes:
                country = node.get("country", "unknown")
                countries[country] = countries.get(country, 0) + 1

            for country, count in countries.items():
                vpn_nodes_by_country.labels(country=country).set(count)

            # Update quality score
            quality_scores = [
                n.get("quality_score", 0)
                for n in successful
                if n.get("quality_score", 0) > 0
            ]
            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)
                vpn_avg_quality_score.set(avg_quality)

            logger.debug(f"Updated metrics: {len(nodes)} nodes")

        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    def start(self, port: int = 9090, update_interval: int = 30):
        """Start Prometheus HTTP server.

        Args:
            port: Port to listen on
            update_interval: Seconds between metric updates
        """
        import time

        # Start HTTP server
        start_http_server(port)
        logger.info(f"Prometheus exporter started on port {port}")

        # Update metrics periodically
        try:
            while True:
                self.update_metrics()
                time.sleep(update_interval)
        except KeyboardInterrupt:
            logger.info("Prometheus exporter stopped")


def start_exporter(data_dir: Path, port: int = 9090):
    """Start Prometheus exporter.

    Args:
        data_dir: Directory containing test results
        port: Port to listen on
    """
    exporter = PrometheusExporter(data_dir)
    exporter.start(port=port)
