from unittest.mock import patch, MagicMock
import json
from pathlib import Path

from configstream.metrics.prometheus_exporter import (
    start_exporter,
    PrometheusExporter,
    vpn_nodes_total,
    vpn_nodes_successful,
    vpn_avg_ping_ms,
    vpn_nodes_by_protocol,
    vpn_nodes_by_country,
    vpn_avg_quality_score,
)


@patch("configstream.metrics.prometheus_exporter.PrometheusExporter.start")
def test_start_exporter(mock_start: MagicMock, tmp_path: Path):
    """Test that the exporter starts the http server on the correct port."""
    start_exporter(data_dir=tmp_path, port=9999)
    mock_start.assert_called_once_with(port=9999)


def test_metrics_definition():
    """Test that the Prometheus metrics are defined correctly."""
    assert vpn_nodes_total._name == "configstream_vpn_nodes_total"
    assert vpn_nodes_total._documentation == "Total number of VPN nodes tested"

    assert vpn_nodes_successful._name == "configstream_vpn_nodes_successful"
    assert vpn_nodes_successful._documentation == "Number of successful VPN nodes"

    assert vpn_avg_ping_ms._name == "configstream_avg_ping_milliseconds"
    assert vpn_avg_ping_ms._documentation == "Average ping time in milliseconds"


def test_update_metrics(tmp_path: Path):
    """Test that update_metrics updates the metrics correctly."""
    data_dir = tmp_path
    exporter = PrometheusExporter(data_dir)
    results_file = data_dir / "current_results.json"
    results_data = {
        "nodes": [
            {
                "protocol": "VLESS",
                "country": "US",
                "ping_ms": 120,
                "quality_score": 80,
            },
            {
                "protocol": "SS",
                "country": "DE",
                "ping_ms": -1,
                "quality_score": 0,
            },
        ]
    }
    results_file.write_text(json.dumps(results_data))

    exporter.update_metrics()

    assert vpn_nodes_total._value.get() == 2
    assert vpn_nodes_successful._value.get() == 1
    assert vpn_avg_ping_ms._value.get() == 120
    assert vpn_nodes_by_protocol.labels(protocol="VLESS")._value.get() == 1
    assert vpn_nodes_by_protocol.labels(protocol="SS")._value.get() == 1
    assert vpn_nodes_by_country.labels(country="US")._value.get() == 1
    assert vpn_nodes_by_country.labels(country="DE")._value.get() == 1
    assert vpn_avg_quality_score._value.get() == 80


def test_update_metrics_no_file(tmp_path: Path):
    """Test that update_metrics handles a missing file gracefully."""
    data_dir = tmp_path
    exporter = PrometheusExporter(data_dir)
    vpn_nodes_total.set(0)
    exporter.update_metrics()
    assert vpn_nodes_total._value.get() == 0
