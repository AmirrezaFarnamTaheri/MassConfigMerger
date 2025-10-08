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
import io
import zipfile

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

app = Flask(__name__, template_folder="templates")
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
    """Modern dashboard with enhanced UI."""
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
    html = render_template_string(
        "<h1>VPN Report</h1><pre>{{ data }}</pre>", data=json.dumps(data, indent=2)
    )
    return html


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


@app.route("/sources")
def sources():
    """Display and manage subscription sources."""
    project_root = _get_root()
    sources_file = project_root / SOURCES_FILE
    if sources_file.exists():
        sources_content = sources_file.read_text()
    else:
        sources_content = "# No sources file found, please create one."
    return render_template("sources.html", sources_content=sources_content)


@app.post("/api/sources/add")
def add_source():
    """Add a new subscription source."""
    data = request.get_json(silent=True) or {}
    raw_url = data.get("url")
    if not raw_url or not isinstance(raw_url, str):
        return jsonify({"error": "URL is required"}), 400

    url = raw_url.strip()
    # Basic sanitation: prevent newlines and enforce length and scheme
    if "\n" in url or "\r" in url or len(url) > 2048:
        return jsonify({"error": "Invalid URL format"}), 400
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return jsonify({"error": "Only http/https URLs with host are allowed"}), 400

    project_root = _get_root()
    """Remove a subscription source."""
    data = request.get_json(silent=True) or {}
    raw_url = data.get("url")
    if not raw_url or not isinstance(raw_url, str):
        return jsonify({"error": "URL is required"}), 400

    url_to_remove = raw_url.strip()
    if "\n" in url_to_remove or "\r" in url_to_remove or len(url_to_remove) > 2048:
        return jsonify({"error": "Invalid URL format"}), 400

    project_root = _get_root()
    sources_file = project_root / SOURCES_FILE
    if not sources_file.exists():
        return jsonify({"error": "Sources file not found"}), 404

    original = sources_file.read_text(encoding="utf-8").splitlines()
    # Normalize lines and remove exact matches only
    filtered = [line for line in original if line.strip() != url_to_remove]

    # If no change, return idempotent response
    if len(filtered) == len(original):
        return jsonify({"message": "Source not found"}), 200

    # Atomic write
    tmp_path = sources_file.with_suffix(sources_file.suffix + ".tmp")
    tmp_path.write_text("\n".join(filtered), encoding="utf-8")
    tmp_path.replace(sources_file)

@app.post("/api/sources/remove")
def remove_source():
    """Remove a subscription source."""
    data = request.get_json()
    url_to_remove = data.get("url")
    if not url_to_remove:
        return jsonify({"error": "URL is required"}), 400

    project_root = _get_root()
    sources_file = project_root / SOURCES_FILE
    if not sources_file.exists():
        return jsonify({"error": "Sources file not found"}), 404

    lines = sources_file.read_text().splitlines()
    new_lines = [line for line in lines if line.strip() != url_to_remove.strip()]

    sources_file.write_text("\n".join(new_lines))

    return jsonify({"message": "Source removed successfully"})


from collections import Counter

@app.route("/analytics")
def analytics():
    """Display analytics dashboard."""
    cfg = load_cfg()
    project_root = _get_root()
    db_path = project_root / cfg.output.history_db_file
    history_data = _run_async_task(_read_history(db_path))
    entries = _serialize_history(history_data)

    # Process data for charts
    protocol_counts = Counter(entry["key"].split("://")[0] for entry in entries)
    country_counts = Counter(entry["country"] for entry in entries if entry["country"])

    # Prepare data for Chart.js
    protocol_labels = list(protocol_counts.keys())
    protocol_values = list(protocol_counts.values())

    country_labels = list(country_counts.keys())
    country_values = list(country_counts.values())

    return render_template(
        "analytics.html",
        protocol_labels=protocol_labels,
        protocol_values=protocol_values,
        country_labels=country_labels,
        country_values=country_values,
    )


@app.route("/settings")
def settings():
    """Display the current application settings."""
    cfg = load_cfg()
    config_path = cfg.config_file or "Default (no file loaded)"

    # To display the raw config, we read it from the file
    if cfg.config_file and cfg.config_file.exists():
        config_content = cfg.config_file.read_text()
    else:
        config_content = "# No config file loaded. Using default settings."

    return render_template("settings.html", config_path=config_path, config_content=config_content)


@app.route("/logs")
def logs():
    """Display application logs."""
    log_file = _get_root() / "web_server.log"
    log_content = "Log file not found."
    if log_file.exists():
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()
                log_content = "".join(lines[-100:])
        except Exception as e:
            log_content = f"Error reading log file: {e}"

    return render_template("logs.html", log_content=log_content)


@app.route("/backup")
def backup():
    """Render the backup and restore page."""
    return render_template("backup.html")


@app.get("/api/export-backup")
def export_backup():
    """Export critical application files as a zip archive."""
    project_root = _get_root()
    files_to_backup = [
        project_root / CONFIG_FILE_NAME,
        project_root / SOURCES_FILE,
        project_root / "proxy_history.db",
    ]

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in files_to_backup:
            if file_path.exists() and file_path.is_file():
                zf.write(file_path, arcname=file_path.name)

    memory_file.seek(0)
    return send_file(
        memory_file,
        download_name="configstream_backup.zip",
        as_attachment=True,
        mimetype="application/zip",
    )


@app.post("/api/import-backup")
def import_backup():
    """Import a zip archive to restore application data."""
    if "backup_file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["backup_file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.endswith(".zip"):
        project_root = _get_root()
        try:
            with zipfile.ZipFile(file, "r") as zf:
                root_resolved = project_root.resolve()
                for member in zf.infolist():
                    # Reject absolute paths or drive changes
                    member_path = Path(member.filename)
                    if member_path.is_absolute() or member_path.drive:
                        return jsonify({"error": f"Invalid absolute path in archive: {member.filename}"}), 400
                    # Normalize and resolve against project root
                    target_path = (root_resolved / member_path).resolve()
                    if not str(target_path).startswith(str(root_resolved)):
                        return jsonify({"error": f"Invalid file path in archive: {member.filename}"}), 400
                    # Create parent directories and write file safely
                    if member.is_dir():
                        target_path.mkdir(parents=True, exist_ok=True)
                    else:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member, "r") as src, open(target_path, "wb") as dst:
                            dst.write(src.read())
            return jsonify({"message": "Backup imported successfully."})
        except zipfile.BadZipFile:
            return jsonify({"error": "Invalid zip file."}), 400
        except Exception as e:
            return jsonify({"error": f"An error occurred: {e}"}), 500

    return jsonify({"error": "Invalid file type. Please upload a .zip file."}), 400


def main() -> None:
    """Run the Flask development server."""
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})
    app.run(host="0.0.0.0", port=8080, debug=False)


if __name__ == "__main__":
    main()