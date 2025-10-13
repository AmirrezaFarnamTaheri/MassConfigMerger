"""Utility helpers and Flask views for the ConfigStream dashboard."""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, current_app, render_template
from flask_wtf.csrf import CSRFProtect

from .config import load_config
from .scheduler import TestScheduler

csrf = CSRFProtect()

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _normalize_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure a node dictionary exposes consistent keys."""

    normalized: Dict[str, Any] = dict(node)
    country_value = str(normalized.get("country") or "").strip()
    country_code = str(normalized.get("country_code") or "").strip()
    fallback_country = (
        country_value
        or country_code
        or str(normalized.get("city") or "").strip()
        or "Unknown"
    )
    normalized["country"] = country_value or fallback_country
    normalized["country_code"] = country_code or fallback_country
    return normalized


def _coerce_ping(value: Any) -> float | None:
    """Attempt to convert a ping value into a float."""

    try:
        ping = float(value)
    except (TypeError, ValueError):
        return None
    if ping != ping or ping in (float("inf"), float("-inf")):
        return None
    return ping

def get_current_results(data_dir: Path, logger_instance) -> Dict[str, Any]:
    """Load current test results."""
    current_file = data_dir / "current_results.json"
    default_payload = {
        "timestamp": None,
        "total_tested": 0,
        "successful": 0,
        "failed": 0,
        "nodes": [],
    }
    if not current_file.exists():
        return default_payload
    try:
        data = json.loads(current_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("current_results.json root is not an object")

        unexpected_keys = sorted(set(data.keys()) - set(default_payload.keys()))
        if unexpected_keys:
            logger_instance.warning(
                "Ignoring unexpected keys in current results: %s",
                ", ".join(unexpected_keys),
            )

        merged = {**default_payload, **{k: v for k, v in data.items() if k in default_payload}}
        nodes_raw = merged.get("nodes", [])
        if not isinstance(nodes_raw, list):
            logger_instance.warning("'nodes' entry is not a list; resetting to empty list")
            nodes_raw = []

        normalized_nodes: List[Dict[str, Any]] = []
        for index, raw_node in enumerate(nodes_raw):
            if isinstance(raw_node, dict):
                normalized_nodes.append(_normalize_node(raw_node))
            else:
                logger_instance.warning(
                    "Skipping non-object node entry at index %s in current results", index
                )

        merged["nodes"] = normalized_nodes
        if merged.get("total_tested", 0) == 0:
            merged["total_tested"] = len(normalized_nodes)
        return merged
    except Exception as e:
        logger_instance.error(f"Error loading current results: {e}")
        return default_payload

def get_history(data_dir: Path, hours: int, logger_instance) -> List[Dict]:
    """Load historical results."""
    history_file = data_dir / "history.jsonl"
    if not history_file.exists():
        return []
    history: List[Dict] = []
    now_utc = datetime.now(timezone.utc)
    cutoff_time = now_utc - timedelta(hours=hours)

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    ts_raw = data.get("timestamp", "")
                    if not ts_raw:
                        continue
                    try:
                        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    except ValueError:
                        logger_instance.warning(
                            "Skipping entry with invalid timestamp: %r", ts_raw
                        )
                        continue

                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)

                    ts_utc = ts.astimezone(timezone.utc)
                    if ts_utc >= cutoff_time:
                        history.append(data)
                except json.JSONDecodeError:
                    logger_instance.warning(
                        "Skipping malformed JSON line in history: %s", line.strip()
                    )
                    continue
    except Exception as e:
        logger_instance.error(f"Error loading history: {e}")
    return history

def filter_nodes(nodes: List[Dict], filters: dict) -> List[Dict]:
    """Apply query filters to a sequence of nodes."""

    normalized_nodes = [_normalize_node(n) for n in nodes if isinstance(n, dict)]
    filtered = normalized_nodes

    protocol = (filters.get("protocol") or "").strip()
    if protocol:
        filtered = [
            n for n in filtered
            if str(n.get("protocol", "")).lower() == protocol.lower()
        ]

    country = (filters.get("country") or "").strip()
    if country:
        filtered = [
            n for n in filtered
            if country.lower() in {
                str(n.get("country", "")).lower(),
                str(n.get("country_code", "")).lower(),
            }
        ]

    min_ping = filters.get("min_ping")
    min_ping_value = _coerce_ping(min_ping) if min_ping is not None else None
    if min_ping_value is not None:
        filtered = [
            n for n in filtered
            if (ping := _coerce_ping(n.get("ping_ms"))) is not None and ping >= min_ping_value
        ]

    max_ping = filters.get("max_ping")
    max_ping_value = _coerce_ping(max_ping) if max_ping is not None else None
    if max_ping_value is not None:
        filtered = [
            n for n in filtered
            if (ping := _coerce_ping(n.get("ping_ms"))) is not None and 0 < ping <= max_ping_value
        ]

    if str(filters.get("exclude_blocked", "")).lower() in {"1", "true", "yes", "on"}:
        filtered = [n for n in filtered if not bool(n.get("is_blocked"))]

    search = (filters.get("search") or "").strip().lower()
    if search:
        filtered = [
            n for n in filtered
            if search in str(n.get("city", "")).lower()
            or search in str(n.get("organization", "")).lower()
            or search in str(n.get("ip", ""))
            or search in str(n.get("country", "")).lower()
            or search in str(n.get("country_code", "")).lower()
        ]

    return filtered

def export_csv(nodes: List[Dict]) -> str:
    """Export nodes to CSV format."""
    output = StringIO()
    if not nodes:
        return ""
    all_keys = set()
    for n in nodes:
        all_keys.update(n.keys())
    fieldnames = sorted(all_keys)
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for n in nodes:
        row = {k: n.get(k, "") for k in fieldnames}
        writer.writerow(row)
    return output.getvalue()

def export_json(nodes: List[Dict]) -> str:
    """Export nodes to JSON format."""
    return json.dumps(nodes, indent=2)


def export_raw(nodes: List[Dict]) -> str:
    """Export nodes to a newline-separated list of configurations."""

    lines = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        config = node.get("config")
        if isinstance(config, str) and config.strip():
            lines.append(config.strip())
    return "\n".join(lines)


def export_base64(nodes: List[Dict]) -> str:
    """Export configurations encoded as a single base64 payload."""

    raw_data = export_raw(nodes)
    if not raw_data:
        return ""
    return base64.b64encode(raw_data.encode("utf-8")).decode("utf-8")

def create_app(settings=None, data_dir=DATA_DIR) -> Flask:
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

    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    app.config["settings"] = settings
    app.config["scheduler"] = TestScheduler(settings, data_dir)
    app.config["data_dir"] = data_dir

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
        return {**sri, 'now': datetime.utcnow}

    from .api import api
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
        settings_dict = json.loads(settings.model_dump_json())
        return render_template("settings.html", settings=settings_dict)

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
