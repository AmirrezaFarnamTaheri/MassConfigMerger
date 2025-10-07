"""Basic Flask server for ConfigStream."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template_string, send_file
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import nest_asyncio

from .config import load_config
from .constants import (
    CONFIG_FILE_NAME,
    HTML_REPORT_FILE_NAME,
    JSON_REPORT_FILE_NAME,
    RAW_SUBSCRIPTION_FILE_NAME,
    SOURCES_FILE,
)
from .core.file_utils import find_project_root
from .db import Database
from .pipeline import run_aggregation_pipeline
from .vpn_merger import run_merger as run_merger_pipeline

app = Flask(__name__)

CONFIG_PATH = Path(CONFIG_FILE_NAME)


def _get_root() -> Path:
    """Get project root or fall back to CWD if not in a project env."""
    try:
        return find_project_root()
    except FileNotFoundError:
        return Path.cwd()


def load_cfg():
    """Load configuration from ``CONFIG_PATH``."""
    return load_config(CONFIG_PATH)


@app.route("/")
def index():
    """Display the main dashboard with links to other pages."""
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ConfigStream Dashboard</title>
        <style>
            body { font-family: sans-serif; margin: 40px; }
            h1 { color: #333; }
            ul { list-style-type: none; padding: 0; }
            li { margin: 10px 0; }
            a { text-decoration: none; color: #fff; font-size: 1.2em; }
            a:hover { text-decoration: underline; }
            .action-btn {
                display: inline-block;
                padding: 10px 15px;
                background-color: #28a745;
                border-radius: 5px;
                text-align: center;
            }
            .report-link {
                display: inline-block;
                padding: 10px 15px;
                background-color: #17a2b8;
                border-radius: 5px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <h1>ConfigStream Dashboard</h1>
        <ul>
            <li><a href="/aggregate" class="action-btn">Run Aggregation</a></li>
            <li><a href="/merge" class="action-btn">Run Merge</a></li>
            <li><a href="/report" class="report-link">View Latest Report</a></li>
            <li><a href="/history" class="report-link">View Proxy History</a></li>
            <li><a href="/metrics" class="report-link">View Metrics</a></li>
            <li><a href="/health" class="report-link">Health Check</a></li>
        </ul>
    </body>
    </html>
    """
    return render_template_string(template)


@app.route("/health")
def health_check():
    """Return a simple health check response."""
    return jsonify({"status": "ok"})


@app.route("/aggregate")
def aggregate() -> dict:
    """Run the aggregation pipeline and return the output files."""
    cfg = load_cfg()
    out_dir, files = asyncio.run(
        run_aggregation_pipeline(cfg, sources_file=SOURCES_FILE)
    )
    return {"output_dir": str(out_dir), "files": [str(p) for p in files]}


@app.route("/merge")
def merge() -> dict:
    """Run the VPN merger using the latest aggregated results."""
    nest_asyncio.apply()
    cfg = load_cfg()
    project_root = _get_root()
    output_dir = project_root / cfg.output.output_dir
    resume_file = output_dir / RAW_SUBSCRIPTION_FILE_NAME
    if not resume_file.exists():
        return {"error": f"Resume file not found: {resume_file}"}, 404

    asyncio.run(
        run_merger_pipeline(cfg, sources_file=SOURCES_FILE, resume_file=resume_file)
    )
    return {"status": "merge complete"}


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


@app.route("/history")
def history():
    """Display the proxy history from the database."""
    cfg = load_cfg()
    project_root = _get_root()
    db_path = project_root / cfg.output.history_db_file

    async def _fetch_history():
        db = Database(db_path)
        try:
            await db.connect()
            return await db.get_proxy_history()
        finally:
            await db.close()

    history_data = asyncio.run(_fetch_history())

    def _safe_ratio(stats: dict) -> float:
        try:
            succ = int(stats.get("successes", 0) or 0)
            fail = int(stats.get("failures", 0) or 0)
            total = succ + fail
            return (succ / total) if total > 0 else 0.0
        except (ValueError, TypeError):
            return 0.0

    sorted_history = sorted(
        history_data.items(),
        key=lambda item: _safe_ratio(item[1]),
        reverse=True,
    )

    for _, stats in sorted_history:
        ts = stats.get("last_tested")
        if ts:
            try:
                stats["last_tested"] = datetime.fromtimestamp(int(ts)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except (ValueError, TypeError, OSError):
                stats["last_tested"] = "N/A"
        else:
            stats["last_tested"] = "N/A"

    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Proxy History</title>
        <style>
            body { font-family: sans-serif; }
            table { width: 80%; margin: 20px auto; border-collapse: collapse; }
            th, td { border: 1px solid #ccc; padding: 10px; text-align: left; }
            th { background-color: #eee; }
            h1 { text-align: center; }
        </style>
    </head>
    <body>
        <h1>Proxy History</h1>
        <p style="text-align:center;"><a href="/">Back to Dashboard</a></p>
        <table>
            <tr>
                <th>Proxy (Host:Port)</th>
                <th>Successes</th>
                <th>Failures</th>
                <th>Reliability</th>
                <th>Last Tested (UTC)</th>
            </tr>
            {% for key, stats in history %}
            <tr>
                <td>{{ key }}</td>
                <td>{{ stats.get("successes", "N/A") }}</td>
                <td>{{ stats.get("failures", "N/A") }}</td>
                <td>
                    {% set succ = (stats.get("successes", 0) or 0) | int %}
                    {% set fail = (stats.get("failures", 0) or 0) | int %}
                    {% set total = succ + fail %}
                    {% if total > 0 %}
                        {{ "%.2f"|format(succ * 100 / total) }}%
                    {% else %}
                        0.00%
                    {% endif %}
                </td>
                <td>{{ stats.last_tested }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(template, history=sorted_history)


def main() -> None:
    """Run the Flask development server."""
    # Add prometheus wsgi middleware to route /metrics requests
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})
    app.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
