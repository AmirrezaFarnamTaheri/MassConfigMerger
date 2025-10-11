import pytest
from unittest.mock import patch, MagicMock

from configstream.metrics.prometheus_exporter import (
    start_exporter,
    nodes_total,
    nodes_successful,
    avg_ping,
)


@patch("configstream.metrics.prometheus_exporter.start_http_server")
def test_start_exporter(mock_start_http_server: MagicMock):
    """Test that the exporter starts the http server on the correct port."""
    start_exporter(port=9999)
    mock_start_http_server.assert_called_once_with(9999)


def test_metrics_definition():
    """Test that the Prometheus metrics are defined correctly."""
    assert nodes_total._name == "vpn_nodes_total"
    assert nodes_total._documentation == "Total VPN nodes"

    assert nodes_successful._name == "vpn_nodes_successful"
    assert nodes_successful._documentation == "Successful nodes"

    assert avg_ping._name == "vpn_avg_ping_ms"
    assert avg_ping._documentation == "Average ping"