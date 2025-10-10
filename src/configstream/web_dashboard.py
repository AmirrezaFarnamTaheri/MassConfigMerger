# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

"""Enhanced web dashboard with real-time monitoring and filtering."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file

from .config import Settings, load_config


class DashboardData:
    """Manages dashboard data and filtering."""

    def __init__(self, settings: Settings):
        """Initialize with application settings."""
        self.settings = settings
        self.current_file = settings.output.current_results_file
        self.history_file = settings.output.history_file
        self.data_dir = self.current_file.parent

    def get_current_results(self) -> dict[str, Any]:
        """Load current test results."""
        if not self.current_file.exists():
            return {"timestamp": None, "nodes": []}
        return json.loads(self.current_file.read_text())

    def get_history(self, hours: int = 24) -> list[dict]:
        """Load historical results for specified time period."""
        if not self.history_file.exists():
            return []

        cutoff_time = datetime.now() - timedelta(hours=hours)
        history = []

        with open(self.history_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    timestamp = datetime.fromisoformat(data["timestamp"])
                    if timestamp >= cutoff_time:
                        history.append(data)
                except (json.JSONDecodeError, KeyError):
                    continue  # Skip corrupted lines

        return history

    def filter_nodes(self, nodes: list[dict], filters: dict) -> list[dict]:
        """Apply filters to node list."""
        filtered = nodes

        if protocol := filters.get("protocol"):
            filtered = [n for n in filtered if n.get("protocol", "").lower() == protocol.lower()]
        if country := filters.get("country"):
            filtered = [n for n in filtered if n.get("country", "").lower() == country.lower()]
        if min_ping := filters.get("min_ping"):
            filtered = [n for n in filtered if n.get("ping_ms", 0) >= int(min_ping)]
        if max_ping := filters.get("max_ping"):
            filtered = [n for n in filtered if 0 < n.get("ping_ms", 0) <= int(max_ping)]
        if filters.get("exclude_blocked"):
            filtered = [n for n in filtered if not n.get("is_blocked")]
        if search := filters.get("search", "").lower():
            filtered = [
                n
                for n in filtered
                if search in n.get("city", "").lower()
                or search in n.get("organization", "").lower()
                or search in n.get("ip", "")
            ]

        return filtered

    def export_csv(self, nodes: list[dict]) -> str:
        """Export nodes to CSV format."""
        if not nodes:
            return ""
        output = StringIO()
        fieldnames = sorted(list(nodes[0].keys()))
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(nodes)
        return output.getvalue()

    def export_json(self, nodes: list[dict]) -> str:
        """Export nodes to JSON format."""
        return json.dumps(nodes, indent=2)


def create_app(settings: Settings | None = None) -> Flask:
    """Create and configure the Flask application."""
    if settings is None:
        settings = load_config()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    dashboard_data = DashboardData(settings)

    @app.route("/")
    def index():
        """Serve the main dashboard page."""
        return render_template("dashboard.html")

    @app.route("/api/current")
    def api_current():
        """API endpoint for current results."""
        data = dashboard_data.get_current_results()
        filters = request.args.to_dict()
        if filters:
            data["nodes"] = dashboard_data.filter_nodes(data["nodes"], filters)
        return jsonify(data)

    @app.route("/api/history")
    def api_history():
        """API endpoint for historical data."""
        hours = int(request.args.get("hours", 24))
        history = dashboard_data.get_history(hours)
        return jsonify(history)

    @app.route("/api/statistics")
    def api_statistics():
        """API endpoint for aggregated statistics."""
        data = dashboard_data.get_current_results()
        nodes = data.get("nodes", [])
        protocols, countries, avg_ping_by_country = {}, {}, {}

        for node in nodes:
            if node.get("ping_ms", 0) > 0:
                proto = node.get("protocol")
                if proto:
                    protocols[proto] = protocols.get(proto, 0) + 1
                country = node.get("country")
                if country:
                    countries[country] = countries.get(country, 0) + 1
                    if country not in avg_ping_by_country:
                        avg_ping_by_country[country] = []
                    avg_ping_by_country[country].append(node["ping_ms"])

        for country, pings in avg_ping_by_country.items():
            avg_ping_by_country[country] = sum(pings) / len(pings) if pings else 0

        return jsonify({
            "total_nodes": len(nodes),
            "successful_nodes": len([n for n in nodes if n.get("ping_ms", 0) > 0]),
            "protocols": protocols,
            "countries": countries,
            "avg_ping_by_country": avg_ping_by_country,
            "last_update": data.get("timestamp"),
        })

    @app.route("/api/export/<file_format>")
    def api_export(file_format: str):
        """Export data in various formats."""
        data = dashboard_data.get_current_results()
        filters = request.args.to_dict()
        nodes = dashboard_data.filter_nodes(data.get("nodes", []), filters)
        now = datetime.now().strftime("%Y%m%d_%H%M%S")

        if file_format == "csv":
            csv_data = dashboard_data.export_csv(nodes)
            return send_file(
                BytesIO(csv_data.encode()),
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"configstream_nodes_{now}.csv",
            )
        elif file_format == "json":
            json_data = dashboard_data.export_json(nodes)
            return send_file(
                BytesIO(json_data.encode()),
                mimetype="application/json",
                as_attachment=True,
                download_name=f"configstream_nodes_{now}.json",
            )

        return jsonify({"error": "Unsupported format"}), 400

    return app


def run_dashboard(host: str = "0.0.0.0", port: int = 8080):
    """Run the dashboard server."""
    app = create_app()
    app.run(host=host, port=port, debug=False)