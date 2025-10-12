"""Web dashboard for ConfigStream."""
# ... your existing imports ...

import json
import csv
from io import StringIO
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
import logging

from flask import Flask, render_template, current_app
from flask_wtf.csrf import CSRFProtect
import base64
import hashlib

from .config import load_config
from .scheduler import TestScheduler
from .api import api

csrf = CSRFProtect()

logger = logging.getLogger(__name__)

# ... your existing Flask app initialization ...
# app = Flask(__name__)  # This probably already exists


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

    def get_current_results(self) -> Dict[str, Any]:
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

    def get_history(self, hours: int = 24) -> List[Dict]:
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

                    data = json.loads(line)
                    timestamp = datetime.fromisoformat(data["timestamp"])

                    if timestamp >= cutoff_time:
                        history.append(data)
        except Exception as e:
            logger.error(f"Error loading history: {e}")

        return history

    def filter_nodes(self, nodes: List[Dict], filters: dict) -> List[Dict]:
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

    def export_csv(self, nodes: List[Dict]) -> str:
        """Export nodes to CSV format."""
        output = StringIO()
        if not nodes:
            return ""

        # Aggregate all keys across nodes to avoid missing columns
        all_keys = set()
        for n in nodes:
            all_keys.update(n.keys())
        fieldnames = sorted(all_keys)

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for n in nodes:
            # Ensure all keys exist to avoid KeyError and keep columns aligned
            row = {k: n.get(k, "") for k in fieldnames}
            writer.writerow(row)
        return output.getvalue()

    def export_json(self, nodes: List[Dict]) -> str:
        """Export nodes to JSON format.

        Args:
            nodes: List of node dictionaries

        Returns:
            JSON formatted string
        """
        return json.dumps(nodes, indent=2)


# Initialize dashboard data manager path only
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

def create_app(settings=None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    if not settings:
        settings = load_config()

    if not settings.security.secret_key:
        if app.testing:
            import secrets
            generated = secrets.token_urlsafe(32)
            app.logger.warning("SECRET_KEY missing; generating ephemeral key for testing.")
            app.config["SECRET_KEY"] = generated
        else:
            raise RuntimeError("SECRET_KEY is not configured. Set `security.secret_key` in your config.")
    else:
        app.config["SECRET_KEY"] = settings.security.secret_key
    csrf.init_app(app)

    app.config["settings"] = settings
    app.config["dashboard_data"] = DashboardData(DATA_DIR)
    app.config["scheduler"] = TestScheduler(settings, DATA_DIR)

    def get_sri_map(paths):
        sri = {}
        for key, rel_path in paths.items():
            static_file_path = Path(app.static_folder) / rel_path
            if not static_file_path.exists():
                logger.error("Static asset missing for SRI: %s", static_file_path)
                continue
            with open(static_file_path, "rb") as f:
                file_bytes = f.read()
                digest = hashlib.sha384(file_bytes).digest()
                sri[key] = "sha384-" + base64.b64encode(digest).decode()
        return sri

    @app.context_processor
    def inject_sri():
        sri = get_sri_map({
            "tailwind_sri": "css/tailwind-3.4.3.min.css",
            "fontawesome_sri": "css/all.min.css",
            "styles_sri": "css/styles.css",
        })
        return sri

    app.register_blueprint(api, url_prefix='/api')

    @app.route("/")
    def index():
        """Serve the main dashboard page."""
        return render_template("index.html")

    @app.route("/dashboard")
    def dashboard():
        """Serve the main dashboard page."""
        return render_template("dashboard.html")

    @app.route("/documentation")
    def documentation():
        return render_template("documentation.html")

    @app.route("/quick-start")
    def quick_start():
        return render_template("quick-start.html")

    @app.route("/roadmap")
    def roadmap():
        return render_template("roadmap.html")

    @app.route("/history")
    def history():
        return render_template("history.html")




    @app.route("/settings")
    def settings_page():
        settings = current_app.config["settings"]
        return render_template("settings.html", settings=settings.model_dump())

    @app.route("/sources")
    def sources():
        settings = current_app.config["settings"]
        sources_file = Path(settings.sources.sources_file)
        if not sources_file.is_absolute():
            sources_file = Path(current_app.root_path).parent / sources_file

        sources = []
        if sources_file.exists():
            with open(sources_file, "r", encoding="utf-8") as f:
                sources = [line.strip() for line in f if line.strip()]

        return render_template("sources.html", sources=sources)

    @app.route("/system")
    def system():
        scheduler = app.config["scheduler"]
        jobs = scheduler.get_jobs()
        return render_template("system.html", jobs=jobs)

    @app.route("/api-docs")
    def api_docs():
        return render_template("api-docs.html")

    @app.route("/export")
    def export():
        """Render the export page."""
        return render_template("export.html")

    return app

def run_dashboard(host: str = "0.0.0.0", port: int = 8080):
    """Run the dashboard server."""
    app = create_app()
    app.run(host=host, port=port, debug=False)
