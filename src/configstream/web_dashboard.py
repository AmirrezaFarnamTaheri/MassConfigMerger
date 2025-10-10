"""Enhanced web dashboard with real-time monitoring and filtering."""
from __future__ import annotations

import logging
import json
import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__, template_folder="templates")
logger = logging.getLogger(__name__)


class DashboardData:
    """Manages dashboard data and filtering.

    This class provides methods to:
    - Load current test results
    - Load historical data
    - Filter nodes based on various criteria
    - Export data in different formats
    """

    def __init__(self, data_dir: Path):
        """Initialize dashboard data manager.

        Args:
            data_dir: Directory containing test result files
        """
        self.data_dir = data_dir
        self.current_file = data_dir / "current_results.json"
        self.history_file = data_dir / "history.jsonl"

    def get_current_results(self) -> dict[str, Any]:
        """Load current test results.

        Returns:
            Dictionary with test results and metadata
        """
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
        """Load historical results for specified time period.

        Args:
            hours: Number of hours of history to retrieve

        Returns:
            List of historical test result dictionaries
        """
        if not self.history_file.exists():
            return []

        cutoff_time = datetime.now() - timedelta(hours=hours)
        history = []

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        timestamp = datetime.fromisoformat(data["timestamp"])

                        if timestamp >= cutoff_time:
                            history.append(data)
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Skipping malformed line in history file: {e}")
        except Exception as e:
            logger.error(f"Error loading history: {e}")

        return history

    def filter_nodes(self, nodes: list[dict], filters: dict) -> list[dict]:
        """Apply filters to node list.

        Args:
            nodes: List of node dictionaries
            filters: Dictionary of filter criteria

        Returns:
            Filtered list of nodes
        """
        filtered = nodes

        # Protocol filter
        if protocol := filters.get("protocol"):
            filtered = [n for n in filtered if n["protocol"].lower() == protocol.lower()]

        # Country filter
        if country := filters.get("country"):
            filtered = [n for n in filtered if n["country"].lower() == country.lower()]

        # Min ping filter
        if min_ping := filters.get("min_ping"):
            try:
                min_val = int(min_ping)
                filtered = [n for n in filtered if n["ping_ms"] >= min_val]
            except ValueError:
                pass

        # Max ping filter
        if max_ping := filters.get("max_ping"):
            try:
                max_val = int(max_ping)
                filtered = [n for n in filtered if 0 < n["ping_ms"] <= max_val]
            except ValueError:
                pass

        # Exclude blocked filter
        if filters.get("exclude_blocked"):
            filtered = [n for n in filtered if not n["is_blocked"]]

        # Search term (searches in city, organization, or IP)
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
        """Export nodes to CSV format.

        Args:
            nodes: List of node dictionaries

        Returns:
            CSV formatted string
        """
        output = StringIO()
        if not nodes:
            return ""

        # Get all unique keys from nodes
        fieldnames = list(nodes[0].keys())

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(nodes)

        return output.getvalue()

    def export_json(self, nodes: list[dict]) -> str:
        """Export nodes to JSON format.

        Args:
            nodes: List of node dictionaries

        Returns:
            JSON formatted string
        """
        return json.dumps(nodes, indent=2)


# Initialize dashboard data manager
# Adjust the path to match your project structure
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
dashboard_data = DashboardData(DATA_DIR)

# ============================================================================
# DASHBOARD ROUTES
# ============================================================================

@app.route("/")
def index():
    """Serve the main dashboard page."""
    return render_template("dashboard.html")


@app.route("/api/current")
def api_current():
    """API endpoint for current test results.

    Query parameters:
        protocol: Filter by protocol (e.g., vmess, shadowsocks)
        country: Filter by country code
        min_ping: Minimum ping in ms
        max_ping: Maximum ping in ms
        exclude_blocked: If set, exclude blocked nodes
        search: Search term for city/org/IP

    Returns:
        JSON with current test results
    """
    try:
        # Load current data
        data = dashboard_data.get_current_results()

        # Apply filters if provided
        filters = request.args.to_dict()
        if filters:
            data["nodes"] = dashboard_data.filter_nodes(data["nodes"], filters)
            # Update counts after filtering
            data["total_tested"] = len(data["nodes"])
            data["successful"] = len([n for n in data["nodes"] if n["ping_ms"] > 0])
            data["failed"] = len([n for n in data["nodes"] if n["ping_ms"] < 0])

        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in api_current: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/history")
def api_history():
    """API endpoint for historical data.

    Query parameters:
        hours: Number of hours of history (default: 24)

    Returns:
        JSON array of historical test results
    """
    try:
        hours = int(request.args.get("hours", 24))
        history = dashboard_data.get_history(hours)
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error in api_history: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/statistics")
def api_statistics():
    """API endpoint for aggregated statistics.

    Returns:
        JSON with various statistics about the VPN nodes
    """
    try:
        data = dashboard_data.get_current_results()
        nodes = data.get("nodes", [])

        # Initialize statistics
        protocols = {}
        countries = {}
        avg_ping_by_country = {}

        # Calculate statistics from successful nodes
        for node in nodes:
            if node["ping_ms"] > 0:
                # Protocol counts
                proto = node["protocol"]
                protocols[proto] = protocols.get(proto, 0) + 1

                # Country counts
                country = node["country"]
                countries[country] = countries.get(country, 0) + 1

                # Collect pings by country for averaging
                if country not in avg_ping_by_country:
                    avg_ping_by_country[country] = []
                avg_ping_by_country[country].append(node["ping_ms"])

        # Calculate average ping per country
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
    """Export data in various formats.

    Args:
        format: Export format ('csv' or 'json')

    Query parameters: Same as /api/current (for filtering)

    Returns:
        File download with filtered data
    """
    try:
        # Load and filter data
        data = dashboard_data.get_current_results()
        filters = request.args.to_dict()
        nodes = dashboard_data.filter_nodes(data["nodes"], filters)

        # Generate filename with timestamp
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