import pytest
from unittest.mock import patch, MagicMock

from configstream.metrics.prometheus_exporter import (
    start_exporter,
    vpn_nodes_total,
    vpn_nodes_successful,
    vpn_avg_ping_ms,
)


from pathlib import Path

@patch("configstream.metrics.prometheus_exporter.PrometheusExporter.start")
def test_start_exporter(mock_start: MagicMock, tmp_path: Path):
    """Test that the exporter starts the http server on the correct port."""
    start_exporter(data_dir=tmp_path, port=9999)
    mock_start.assert_called_once_with(port=9999, update_interval=30)


def test_metrics_definition():
    """Test that the Prometheus metrics are defined correctly."""
    assert vpn_nodes_total._name == "configstream_vpn_nodes_total"
    assert vpn_nodes_total._documentation == "Total number of VPN nodes tested"

    assert vpn_nodes_successful._name == "configstream_vpn_nodes_successful"
    assert vpn_nodes_successful._documentation == "Number of successful VPN nodes"

    assert vpn_avg_ping_ms._name == "configstream_avg_ping_milliseconds"
    assert vpn_avg_ping_ms._documentation == "Average ping time in milliseconds"