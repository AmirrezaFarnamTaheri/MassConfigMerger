"""Modern Flask web interface for ConfigStream with enhanced UI/UX."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import nest_asyncio
from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    send_file,
)
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from .config import load_config
from .constants import (
    CONFIG_FILE_NAME,
    HTML_REPORT_FILE_NAME,
    JSON_REPORT_FILE_NAME,
    RAW_SUBSCRIPTION_FILE_NAME,
    SOURCES_FILE,
)
from .core.file_utils import find_marker_from, find_project_root
from .db import Database
from .pipeline import run_aggregation_pipeline
from .vpn_merger import run_merger as run_merger_pipeline

app = Flask(__name__)
CONFIG_PATH = Path(CONFIG_FILE_NAME)


def _get_root() -> Path:
    """Get project root or fall back to CWD if not in a project env."""
    local_root = find_marker_from(Path.cwd())
    if local_root is not None:
        return local_root
    if CONFIG_PATH.exists():
        return Path.cwd()
    try:
        return find_project_root()
    except FileNotFoundError:
        return Path.cwd()


def load_cfg():
    """Load configuration from CONFIG_PATH."""
    return load_config(CONFIG_PATH)


def _run_async_task(coro: asyncio.Future) -> Any:
    """Execute coro in a way that tolerates nested event loops."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)


def _extract_api_token() -> Optional[str]:
    """Extract the API token securely from request headers only."""
    header_token = request.headers.get("X-API-Key")
    auth_header = request.headers.get("Authorization", "")

    token_from_header = None
    if header_token:
        cleaned = header_token.strip()
        if cleaned and len(cleaned) <= 256:
            token_from_header = cleaned

    token_from_bearer: Optional[str] = None
    if auth_header:
        scheme, _, value = auth_header.partition(" ")
        if scheme.strip().lower() == "bearer":
            value = value.strip()
            if value and len(value) <= 256:
                token_from_bearer = value

    return token_from_header or token_from_bearer


def _get_request_settings():
    """Return settings for the current request, enforcing API token checks."""
    cfg = load_cfg()
    expected = getattr(cfg.security, "web_api_token", None)
    if expected:
        provided = _extract_api_token()
        if not provided or not secrets.compare_digest(str(expected), provided):
            abort(401, description="Missing or invalid API token")
    return cfg


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _coerce_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_timestamp(value: Any) -> str:
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return "N/A"
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return "N/A"


def _classify_reliability(successes: int, failures: int) -> tuple[str, str]:
    total = successes + failures
    if total == 0:
        return "Untested", "status-untested"
    reliability = successes / total
    if reliability >= 0.75:
        return "Healthy", "status-healthy"
    if reliability >= 0.5:
        return "Warning", "status-warning"
    return "Critical", "status-critical"


def _serialize_history(history_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for key, stats in history_data.items():
        successes = _coerce_int(stats.get("successes"))
        failures = _coerce_int(stats.get("failures"))
        total = successes + failures
        reliability = (successes / total) if total else 0.0
        status, status_class = _classify_reliability(successes, failures)
        latency = (
            _coerce_float(stats.get("latency_ms"))
            or _coerce_float(stats.get("latency"))
        )
        entry = {
            "key": key,
            "successes": successes,
            "failures": failures,
            "tests": total,
            "reliability": reliability,
            "reliability_percent": round(reliability * 100, 2),
            "status": status,
            "status_class": status_class,
            "last_tested": _format_timestamp(stats.get("last_tested")),
            "country": stats.get("country") or stats.get("geo", {}).get("country"),
            "isp": stats.get("isp") or stats.get("geo", {}).get("isp"),
            "latency": round(latency, 2) if latency is not None else None,
        }
        entries.append(entry)
    entries.sort(key=lambda x: x["reliability"], reverse=True)
    return entries


async def _read_history(db_path: Path) -> Dict[str, Dict[str, Any]]:
    """Read proxy history from the database."""
    db = Database(db_path)
    try:
        await db.connect()
        history = await db.get_proxy_history()
        return history
    finally:
        await db.close()


# ============================================================================
# ROUTES
# ============================================================================

@app.route("/")
def index():
    """Modern dashboard with enhanced UI and navigation to all pages."""
    cfg = load_cfg()
    project_root = _get_root()
    db_path = project_root / cfg.output.history_db_file

    # Fetch top 5 proxies for preview
    try:
        history_data = _run_async_task(_read_history(db_path))
        all_entries = _serialize_history(history_data)
        preview_limit = 5
        history_preview = all_entries[:preview_limit] if all_entries else []
    except Exception:
        history_preview = []
        preview_limit = 5

    return render_template(
        "index.html",
        history_preview=history_preview,
        preview_limit=preview_limit,
    )


@app.route("/health")
def health_check():
    """Return a simple health check response."""
    return jsonify({"status": "ok"})


@app.post("/api/aggregate")
def aggregate_api() -> Any:
    """Run the aggregation pipeline and return the output files."""
    cfg = _get_request_settings()
    started = time.monotonic()
    try:
        out_dir, files = _run_async_task(
            run_aggregation_pipeline(cfg, sources_file=SOURCES_FILE)
        )
    except Exception as exc:
        app.logger.exception("Aggregation failed")
        return jsonify({"error": str(exc)}), 500

    duration = time.monotonic() - started
    return jsonify(
        {
            "status": "ok",
            "output_dir": str(out_dir),
            "files": [str(p) for p in files],
            "file_count": len(files),
            "duration_seconds": round(duration, 3),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.post("/api/merge")
def merge_api() -> Any:
    """Run the VPN merger using the latest aggregated results."""
    cfg = _get_request_settings()
    project_root = _get_root()
    output_dir = project_root / cfg.output.output_dir
    resume_file = output_dir / RAW_SUBSCRIPTION_FILE_NAME
    if not resume_file.exists():
        return jsonify({"error": f"Resume file not found: {resume_file}"}), 404

    started = time.monotonic()
    try:
        _run_async_task(
            run_merger_pipeline(cfg, sources_file=SOURCES_FILE, resume_file=resume_file)
        )
    except Exception as exc:
        app.logger.exception("Merge failed")
        return jsonify({"error": str(exc)}), 500

    duration = time.monotonic() - started
    return jsonify(
        {
            "status": "merge complete",
            "duration_seconds": round(duration, 3),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "resume_file": str(resume_file),
        }
    )


@app.route("/report")
def report():
    """Display the HTML or JSON report."""
    cfg = load_cfg()
    project_root = _get_root()
    output_dir = project_root / cfg.output.output_dir
    html_report = output_dir / HTML_REPORT_FILE_NAME
    if html_report.exists():
        return send_file(html_report)
    json_report = output_dir / JSON_REPORT_FILE_NAME
    if not json_report.exists():
        return "Report not found", 404
    data = json.loads(json_report.read_text())
    return render_template("report.html", data=json.dumps(data, indent=2))


@app.get("/api/history")
def history_api() -> Any:
    """Return proxy history statistics as JSON."""
    cfg = load_cfg()
    project_root = _get_root()
    db_path = project_root / cfg.output.history_db_file
    history_data = _run_async_task(_read_history(db_path))
    entries = _serialize_history(history_data)
    total = len(entries)
    limit = request.args.get("limit", type=int)
    if limit is not None and limit >= 0:
        entries = entries[:limit]
    healthy = sum(1 for entry in entries if entry["status"] == "Healthy")
    critical = sum(1 for entry in entries if entry["status"] == "Critical")
    return jsonify(
        {
            "items": entries,
            "returned": len(entries),
            "total": total,
            "healthy": healthy,
            "critical": critical,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.route("/history")
def history():
    """Display the proxy history from the database."""
    cfg = load_cfg()
    project_root = _get_root()
    db_path = project_root / cfg.output.history_db_file
    history_data = _run_async_task(_read_history(db_path))
    entries = _serialize_history(history_data)
    summary = {
        "total": len(entries),
        "healthy": sum(1 for entry in entries if entry["status"] == "Healthy"),
        "critical": sum(1 for entry in entries if entry["status"] == "Critical"),
        "untested": sum(1 for entry in entries if entry["status"] == "Untested"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }
    return render_template("history.html", entries=entries, summary=summary)


# ============================================================================
# SOURCES MANAGEMENT PAGE
# ============================================================================

@app.route("/sources")
def sources_page():
    """Sources management interface."""
    project_root = _get_root()
    sources_file = project_root / SOURCES_FILE

    sources = []
    if sources_file.exists():
        sources = sources_file.read_text().strip().split('\n')
        sources = [s.strip() for s in sources if s.strip() and not s.startswith('#')]

    return render_template("sources.html", sources=sources)


@app.post("/api/sources")
def add_source():
    """Add a new source to sources file."""
    data = request.get_json()
    url = data.get('url', '').strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    project_root = _get_root()
    sources_file = project_root / SOURCES_FILE

    existing_sources = []
    if sources_file.exists():
        existing_sources = sources_file.read_text().strip().split('\n')

    if url in existing_sources:
        return jsonify({"error": "Source already exists"}), 409

    existing_sources.append(url)
    sources_file.write_text('\n'.join(existing_sources) + '\n')

    return jsonify({"status": "ok", "message": "Source added successfully"}), 201


@app.delete("/api/sources")
def delete_source():
    """Delete a source from sources file."""
    data = request.get_json()
    url = data.get('url', '').strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    project_root = _get_root()
    sources_file = project_root / SOURCES_FILE

    if not sources_file.exists():
        return jsonify({"error": "Sources file not found"}), 404

    sources = sources_file.read_text().strip().split('\n')
    filtered_sources = [s for s in sources if s.strip() != url]

    if len(sources) == len(filtered_sources):
        return jsonify({"error": "Source not found"}), 404

    sources_file.write_text('\n'.join(filtered_sources) + '\n')

    return jsonify({"status": "ok", "message": "Source deleted successfully"})


# ============================================================================
# ANALYTICS DASHBOARD
# ============================================================================

@app.route("/analytics")
def analytics_page():
    """Analytics and statistics dashboard."""
    cfg = load_cfg()
    project_root = _get_root()
    db_path = project_root / cfg.output.history_db_file

    try:
        history_data = _run_async_task(_read_history(db_path))
        entries = _serialize_history(history_data)
    except Exception:
        entries = []

    total_proxies = len(entries)
    healthy = sum(1 for e in entries if e['status'] == 'Healthy')
    warning = sum(1 for e in entries if e['status'] == 'Warning')
    critical = sum(1 for e in entries if e['status'] == 'Critical')
    untested = sum(1 for e in entries if e['status'] == 'Untested')

    total_tests = sum(e['tests'] for e in entries)
    avg_reliability = sum(e['reliability_percent'] for e in entries) / len(entries) if entries else 0

    countries = {}
    for e in entries:
        if e.get('country'):
            countries[e['country']] = countries.get(e['country'], 0) + 1

    return render_template(
        "analytics.html",
        total_proxies=total_proxies,
        healthy=healthy,
        warning=warning,
        critical=critical,
        untested=untested,
        total_tests=total_tests,
        avg_reliability=avg_reliability,
        countries=countries,
        entries=entries
    )


# ============================================================================
# SETTINGS PAGE
# ============================================================================

@app.route("/settings")
def settings_page():
    """Configuration settings interface."""
    cfg = load_cfg()
    return render_template("settings.html", cfg=cfg)


# ============================================================================
# API DOCUMENTATION PAGE
# ============================================================================

@app.route("/api-docs")
def api_docs_page():
    """Interactive API documentation."""
    return render_template("api-docs.html")


# ============================================================================
# LOGS VIEWER PAGE
# ============================================================================

@app.route("/logs")
def logs_page():
    """Log file viewer interface."""
    project_root = _get_root()
    log_file = project_root / "web_server.log"

    log_lines = []
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                log_lines = f.readlines()[-100:]
        except Exception as e:
            log_lines = [f"Error reading log file: {str(e)}"]
    else:
        log_lines = ["Log file not found. Logs will appear here once the server starts generating them."]

    return render_template("logs.html", log_lines=log_lines)


def main() -> None:
    """Run the Flask development server."""
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})
    app.run(host="0.0.0.0", port=8080, debug=False)


if __name__ == "__main__":
    main()