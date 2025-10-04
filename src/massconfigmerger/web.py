"""Basic Flask server for MassConfigMerger."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from flask import Flask, render_template_string, send_file

from .config import load_config
from .aggregator_tool import run_pipeline as run_aggregator_pipeline
from .vpn_merger import run_merger as run_merger_pipeline
from .constants import SOURCES_FILE

app = Flask(__name__)

CONFIG_PATH = Path("config.yaml")


def load_cfg():
    """Load configuration from ``CONFIG_PATH``."""
    return load_config(CONFIG_PATH)


@app.route("/aggregate")
def aggregate() -> dict:
    """Run the aggregation pipeline and return the output files."""
    cfg = load_cfg()
    # The new run_pipeline doesn't use CHANNELS_FILE directly, it's handled in the aggregator
    out_dir, files = asyncio.run(
        run_aggregator_pipeline(cfg, sources_file=SOURCES_FILE)
    )
    return {"output_dir": str(out_dir), "files": [str(p) for p in files]}


@app.route("/merge")
def merge() -> dict:
    """Run the VPN merger using the latest aggregated results."""
    cfg = load_cfg()
    resume_file = Path(cfg.output_dir) / "vpn_subscription_raw.txt"
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
    html_report = Path(cfg.output_dir) / "vpn_report.html"
    if html_report.exists():
        return send_file(html_report)
    json_report = Path(cfg.output_dir) / "vpn_report.json"
    if not json_report.exists():
        return "Report not found", 404
    data = json.loads(json_report.read_text())
    html = render_template_string(
        "<h1>VPN Report</h1><pre>{{ data }}</pre>", data=json.dumps(data, indent=2)
    )
    return html


def main() -> None:
    """Run the Flask development server."""
    app.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()