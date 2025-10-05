"""Basic Flask server for MassConfigMerger."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template_string, send_file

from .config import load_config
from .constants import SOURCES_FILE
from .db import Database
from .pipeline import run_aggregation_pipeline
from .vpn_merger import run_merger as run_merger_pipeline

app = Flask(__name__)

CONFIG_PATH = Path("config.yaml")


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
        <title>MassConfigMerger Dashboard</title>
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
        <h1>MassConfigMerger Dashboard</h1>
        <ul>
            <li><a href="/aggregate" class="action-btn">Run Aggregation</a></li>
            <li><a href="/merge" class="action-btn">Run Merge</a></li>
            <li><a href="/report" class="report-link">View Latest Report</a></li>
            <li><a href="/history" class="report-link">View Proxy History</a></li>
        </ul>
    </body>
    </html>
    """
    return render_template_string(template)


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
    cfg = load_cfg()
    resume_file = Path(cfg.output.output_dir) / "vpn_subscription_raw.txt"
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
    html_report = Path(cfg.output.output_dir) / "vpn_report.html"
    if html_report.exists():
        return send_file(html_report)
    json_report = Path(cfg.output.output_dir) / "vpn_report.json"
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
    db = Database(cfg.output.history_db_file)

    async def get_history():
        await db.connect()
        history_data = await db.get_proxy_history()
        await db.close()
        return history_data

    history_data = asyncio.run(get_history())

    sorted_history = sorted(
        history_data.items(),
        key=lambda item: (
            item[1]["successes"] / (item[1]["successes"] + item[1]["failures"])
            if (item[1]["successes"] + item[1]["failures"]) > 0
            else 0
        ),
        reverse=True,
    )

    for _, stats in sorted_history:
        if stats["last_tested"]:
            stats["last_tested"] = datetime.fromtimestamp(
                int(stats["last_tested"])
            ).strftime("%Y-%m-%d %H:%M:%S")
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
                <td>{{ stats.successes }}</td>
                <td>{{ stats.failures }}</td>
                <td>
                    {% if (stats.successes + stats.failures) > 0 %}
                        {{ "%.2f"|format(stats.successes * 100 / (stats.successes + stats.failures)) }}%
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
    app.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()