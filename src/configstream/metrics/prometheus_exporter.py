# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Prometheus metrics exporter."""
from prometheus_client import start_http_server, Gauge, Counter

# Metrics
nodes_total = Gauge('vpn_nodes_total', 'Total VPN nodes')
nodes_successful = Gauge('vpn_nodes_successful', 'Successful nodes')
avg_ping = Gauge('vpn_avg_ping_ms', 'Average ping')

def start_exporter(port: int = 9090):
    """Start Prometheus exporter."""
    start_http_server(port)