from __future__ import annotations

import json
import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import logging

from flask import Flask, jsonify, render_template, request, send_file

logger = logging.getLogger(__name__)

class DashboardData:
    """Manages dashboard data and filtering."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.current_file = data_dir / "current_results.json"
        self.history_file = data_dir / "history.jsonl"

    def get_current_results(self) -> dict[str, Any]:
        """Load current test results."""
        if not self.current_file.exists():
            return {
                "timestamp": None,
                "total_tested": 0,
                "successful": 0,
                "failed": 0,
                "nodes": []
            }

        try:
            return json.loads(self.current_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Error loading current results: {e}")
            return {"timestamp": None, "nodes": []}

    def get_history(self, hours: int = 24) -> list[dict]:
        """Load historical results for specified time period."""
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
            filtered = [n for n in filtered if n["protocol"].lower() == protocol.lower()]

        if country := filters.get("country"):
            filtered = [n for n in filtered if n["country"].lower() == country.lower()]

        if min_ping := filters.get("min_ping"):
            try:
                min_val = int(min_ping)
                filtered = [n for n in filtered if n["ping_ms"] >= min_val]
            except ValueError:
                pass

        if max_ping := filters.get("max_ping"):
            try:
                max_val = int(max_ping)
                filtered = [n for n in filtered if 0 < n["ping_ms"] <= max_val]
            except ValueError:
                pass

        if filters.get("exclude_blocked"):
            filtered = [n for n in filtered if not n["is_blocked"]]

        if search := filters.get("search"):
            search_lower = search.lower()
            filtered = [
                n for n in filtered
                if search_lower in n.get("city", "").lower()
                or search_lower in n.get("organization", "").lower()
                or search_lower in n.get("ip", "")
            ]

        return filtered

    def export_csv(self, nodes: list[dict]) -> str:
        """Export nodes to CSV format."""
        output = StringIO()
        if not nodes:
            return ""

        fieldnames = list(nodes[0].keys())

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(nodes)

        return output.getvalue()

    def export_json(self, nodes: list[dict]) -> str:
        """Export nodes to JSON format."""
        return json.dumps(nodes, indent=2)

def create_app(settings=None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates")

    if settings:
        data_dir = settings.output.current_results_file.parent
    else:
        data_dir = Path("./data")

    dashboard_data = DashboardData(data_dir)

    @app.route("/")
    def index():
        """Serve the main dashboard page."""
        return render_template("dashboard.html")

    @app.route("/api/current")
    def api_current():
        """API endpoint for current results."""
        try:
            data = dashboard_data.get_current_results()
            filters = request.args.to_dict()
            if filters:
                data["nodes"] = dashboard_data.filter_nodes(data["nodes"], filters)
                data["total_tested"] = len(data["nodes"])
                data["successful"] = len([n for n in data["nodes"] if n["ping_ms"] > 0])
                data["failed"] = len([n for n in data["nodes"] if n["ping_ms"] < 0])
            return jsonify(data)
        except Exception as e:
            logger.error(f"Error in api_current: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/history")
    def api_history():
        """API endpoint for historical data."""
        try:
            hours = int(request.args.get("hours", 24))
            history = dashboard_data.get_history(hours)
            return jsonify(history)
        except Exception as e:
            logger.error(f"Error in api_history: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/statistics")
    def api_statistics():
        """API endpoint for aggregated statistics."""
        try:
            data = dashboard_data.get_current_results()
            nodes = data.get("nodes", [])
            protocols = {}
            countries = {}
            avg_ping_by_country = {}
            for node in nodes:
                if node["ping_ms"] > 0:
                    proto = node["protocol"]
                    protocols[proto] = protocols.get(proto, 0) + 1
                    country = node["country"]
                    countries[country] = countries.get(country, 0) + 1
                    if country not in avg_ping_by_country:
                        avg_ping_by_country[country] = []
                    avg_ping_by_country[country].append(node["ping_ms"])
            for country, pings in avg_ping_by_country.items():
                avg_ping_by_country[country] = round(sum(pings) / len(pings), 2)
            return jsonify({
                "total_nodes": len(nodes),
                "successful_nodes": len([n for n in nodes if n["ping_ms"] > 0]),
                "protocols": protocols,
                "countries": countries,
                "avg_ping_by_country": avg_ping_by_country,
                "last_update": data.get("timestamp")
            })
        except Exception as e:
            logger.error(f"Error in api_statistics: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/export/<format>")
    def api_export(format: str):
        """Export data in various formats."""
        try:
            data = dashboard_data.get_current_results()
            filters = request.args.to_dict()
            nodes = dashboard_data.filter_nodes(data["nodes"], filters)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            if format == "csv":
                csv_data = dashboard_data.export_csv(nodes)
                return send_file(
                    BytesIO(csv_data.encode('utf-8')),
                    mimetype="text/csv",
                    as_attachment=True,
                    download_name=f"vpn_nodes_{timestamp}.csv"
                )

            elif format == "json":
                json_data = dashboard_data.export_json(nodes)
                return send_file(
                    BytesIO(json_data.encode('utf-8')),
                    mimetype="application/json",
                    as_attachment=True,
                    download_name=f"vpn_nodes_{timestamp}.json"
                )

            else:
                return jsonify({"error": f"Unsupported format: {format}"}), 400

        except Exception as e:
            logger.error(f"Error in api_export: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    return app

def run_dashboard(host: str = "0.0.0.0", port: int = 8080):
    """Run the dashboard server."""
    app = create_app()
    app.run(host=host, port=port, debug=False)