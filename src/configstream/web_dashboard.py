"""Enhanced web dashboard with real-time monitoring and filtering."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Optional
import csv

from flask import Flask, jsonify, render_template, request, send_file
from hypercorn.asyncio import serve
from hypercorn.config import Config

from .config import Settings, load_config


class DashboardData:
    """Manages dashboard data and filtering."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.data_dir = Path("./data")
        self.current_file = self.data_dir / "current_results.json"
        self.history_file = self.data_dir / "history.jsonl"

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
                data = json.loads(line)
                timestamp = datetime.fromisoformat(data["timestamp"])
                if timestamp >= cutoff_time:
                    history.append(data)

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
                filtered = [n for n in filtered if n["ping_ms"] >= int(min_ping)]
            except (ValueError, TypeError):
                pass

        if max_ping := filters.get("max_ping"):
            try:
                filtered = [n for n in filtered if 0 < n["ping_ms"] <= int(max_ping)]
            except (ValueError, TypeError):
                pass

        if filters.get("exclude_blocked"):
            filtered = [n for n in filtered if not n.get("is_blocked")]

        if search := filters.get("search"):
            search = search.lower()
            filtered = [
                n for n in filtered
                if search in n.get("city", "").lower()
                or search in n.get("organization", "").lower()
                or search in n.get("ip", "")
            ]

        return filtered

    def export_csv(self, nodes: list[dict]) -> str:
        """Export nodes to CSV format."""
        output = StringIO()
        if not nodes:
            return ""

        writer = csv.DictWriter(output, fieldnames=nodes[0].keys())
        writer.writeheader()
        writer.writerows(nodes)
        return output.getvalue()

    def export_json(self, nodes: list[dict]) -> str:
        """Export nodes to JSON format."""
        return json.dumps(nodes, indent=2)


def create_app(settings: Optional[Settings] = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates")

    if settings is None:
        settings = load_config()
    app.config["SETTINGS"] = settings

    dashboard_data = DashboardData(settings)

    def require_api_key(f):
        """Decorator to protect endpoints with an API key."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = app.config["SETTINGS"].security.api_key
            if api_key:
                provided_key = request.headers.get("X-API-Key")
                # Also check Authorization header for Bearer token
                if not provided_key:
                    auth_header = request.headers.get("Authorization")
                    if auth_header and auth_header.startswith("Bearer "):
                        provided_key = auth_header.split(" ", 1)[1]

                if not provided_key or provided_key != api_key:
                    return jsonify({"error": "Unauthorized"}), 401
            return f(*args, **kwargs)
        return decorated_function

    @app.route("/")
    def index():
        """Serve the main dashboard page."""
        return render_template("dashboard.html")

    @app.route("/api/current")
    @require_api_key
    def api_current():
        """API endpoint for current results."""
        data = dashboard_data.get_current_results()
        filters = request.args.to_dict()

        if filters:
            data["nodes"] = dashboard_data.filter_nodes(data["nodes"], filters)

        return jsonify(data)

    @app.route("/api/history")
    @require_api_key
    def api_history():
        """API endpoint for historical data."""
        hours = int(request.args.get("hours", 24))
        history = dashboard_data.get_history(hours)
        return jsonify(history)

    @app.route("/api/statistics")
    @require_api_key
    def api_statistics():
        """API endpoint for aggregated statistics."""
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
            if pings:
                avg_ping_by_country[country] = sum(pings) / len(pings)

        return jsonify({
            "total_nodes": len(nodes),
            "successful_nodes": len([n for n in nodes if n["ping_ms"] > 0]),
            "protocols": protocols,
            "countries": countries,
            "avg_ping_by_country": avg_ping_by_country,
            "last_update": data.get("timestamp")
        })

    @app.route("/api/export/<format>")
    @require_api_key
    def api_export(format: str):
        """Export data in various formats."""
        data = dashboard_data.get_current_results()
        filters = request.args.to_dict()
        nodes = dashboard_data.filter_nodes(data.get("nodes", []), filters)

        export_fields = [
            "protocol", "country", "city", "ip", "port", "ping_ms",
            "organization", "is_blocked", "timestamp"
        ]

        if format == "csv":
            projected = [
                {k: n.get(k, "") for k in export_fields} for n in nodes
            ]
            csv_data = dashboard_data.export_csv(projected)
            return send_file(
                BytesIO(csv_data.encode()),
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"vpn_nodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

        elif format == "json":
            projected = [
                {k: n.get(k, None) for k in export_fields} for n in nodes
            ]
            json_data = json.dumps(projected, indent=2)
            return send_file(
                BytesIO(json_data.encode()),
                mimetype="application/json",
                as_attachment=True,
                download_name=f"vpn_nodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        return jsonify({"error": "Unsupported format"}), 400

    return app


async def run_dashboard(host: str = "127.0.0.1", port: int = 8080):
    """Run the dashboard server asynchronously."""
    app = create_app()
    config = Config()
    config.bind = [f"{host}:{port}"]
    await serve(app, config)