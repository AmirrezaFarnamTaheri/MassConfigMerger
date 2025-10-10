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
import logging
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file

from .config import Settings, load_config

logger = logging.getLogger(__name__)


class DashboardData:
    """Manages dashboard data and filtering."""

    def __init__(self, settings: Settings):
        """Initialize dashboard data manager."""
        self.settings = settings
        self.current_file = settings.output.current_results_file
        self.history_file = settings.output.history_file

    def get_current_results(self) -> dict[str, Any]:
        """Load current test results."""
        default_response = {"timestamp": None, "total_tested": 0, "successful": 0, "failed": 0, "nodes": []}
        if not self.current_file.exists():
            return default_response
        try:
            return json.loads(self.current_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.warning(f"Could not decode current_results.json: {e}. Returning empty results.")
            return default_response

    def get_history(self, hours: int = 24) -> list[dict]:
        """Load historical results."""
        if not self.history_file.exists():
            return []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        history = []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    timestamp = datetime.fromisoformat(data["timestamp"])
                    if timestamp >= cutoff_time:
                        history.append(data)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
        return history

    def filter_nodes(self, nodes: list[dict], filters: dict) -> list[dict]:
        """Apply filters to node list."""
        filtered = nodes
        if protocol := filters.get("protocol"):
            filtered = [n for n in filtered if n.get("protocol", "").lower() == protocol.lower()]
        if country := filters.get("country"):
            filtered = [n for n in filtered if n.get("country", "").lower() == country.lower()]
        if min_ping := filters.get("min_ping"):
            try:
                min_val = int(min_ping)
                filtered = [n for n in filtered if n.get("ping_time", 0) >= min_val]
            except (ValueError, TypeError):
                pass
        if max_ping := filters.get("max_ping"):
            try:
                max_val = int(max_ping)
                filtered = [n for n in filtered if n.get("ping_time", 0) is not None and 0 < n["ping_time"] <= max_val]
            except (ValueError, TypeError):
                pass
        if filters.get("exclude_blocked"):
            filtered = [n for n in filtered if not n.get("is_blocked")]
        if search := filters.get("search"):
            search_lower = search.lower()
            filtered = [
                n for n in filtered
                if search_lower in n.get("city", "").lower()
                or search_lower in n.get("organization", "").lower()
                or search_lower in n.get("host", "")
            ]
        return filtered

    def export_csv(self, nodes: list[dict]) -> str:
        """Export nodes to CSV format."""
        output = StringIO()
        if not nodes:
            return ""
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
        return render_template("dashboard.html")

    @app.route("/api/current")
    def api_current():
        try:
            data = dashboard_data.get_current_results()
            filters = request.args.to_dict()
            if filters:
                data["nodes"] = dashboard_data.filter_nodes(data["nodes"], filters)
                data["total_tested"] = len(data["nodes"])
                successful_nodes = [n for n in data["nodes"] if n.get("ping_time") is not None and n["ping_time"] > 0]
                data["successful"] = len(successful_nodes)
                data["failed"] = data["total_tested"] - data["successful"]
            return jsonify(data)
        except Exception as e:
            logger.error(f"Error in api_current: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/history")
    def api_history():
        try:
            hours = int(request.args.get("hours", 24))
            history = dashboard_data.get_history(hours)
            return jsonify(history)
        except Exception as e:
            logger.error(f"Error in api_history: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/statistics")
    def api_statistics():
        try:
            data = dashboard_data.get_current_results()
            nodes = data.get("nodes", [])
            protocols, countries, avg_ping_by_country = {}, {}, {}
            successful_nodes = [n for n in nodes if n.get("ping_time") is not None and n["ping_time"] > 0]
            for node in successful_nodes:
                if proto := node.get("protocol"):
                    protocols[proto] = protocols.get(proto, 0) + 1
                if country := node.get("country"):
                    countries[country] = countries.get(country, 0) + 1
                    if country not in avg_ping_by_country:
                        avg_ping_by_country[country] = []
                    if ping := node.get("ping_time"):
                        avg_ping_by_country[country].append(ping)
            for country, pings in avg_ping_by_country.items():
                avg_ping_by_country[country] = round(sum(pings) / len(pings), 2) if pings else 0
            return jsonify({
                "total_nodes": len(nodes),
                "successful_nodes": len(successful_nodes),
                "protocols": protocols,
                "countries": countries,
                "avg_ping_by_country": avg_ping_by_country,
                "last_update": data.get("timestamp")
            })
        except Exception as e:
            logger.error(f"Error in api_statistics: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/export/<file_format>")
    def api_export(file_format: str):
        try:
            data = dashboard_data.get_current_results()
            filters = request.args.to_dict()
            nodes = dashboard_data.filter_nodes(data.get("nodes", []), filters)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if file_format == "csv":
                csv_data = dashboard_data.export_csv(nodes)
                return send_file(BytesIO(csv_data.encode('utf-8')), mimetype="text/csv", as_attachment=True, download_name=f"configstream_nodes_{timestamp}.csv")
            elif file_format == "json":
                json_data = dashboard_data.export_json(nodes)
                return send_file(BytesIO(json_data.encode('utf-8')), mimetype="application/json", as_attachment=True, download_name=f"configstream_nodes_{timestamp}.json")
            else:
                return jsonify({"error": f"Unsupported format: {file_format}"}), 400
        except Exception as e:
            logger.error(f"Error in api_export: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    return app


def run_dashboard(host: str = "0.0.0.0", port: int = 8080):
    """Run the dashboard server."""
    app = create_app()
    app.run(host=host, port=port, debug=False)