"""Basic Flask server for MassConfigMerger."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from flask import Flask, render_template_string, send_file

from .config import load_config
from .aggregator_tool import run_pipeline, SOURCES_FILE, CHANNELS_FILE
from .vpn_merger import detect_and_run
from .result_processor import CONFIG

app = Flask(__name__)

CONFIG_PATH = Path("config.yaml")


def load_cfg():
    """Load configuration from ``CONFIG_PATH``."""
    return load_config(CONFIG_PATH)


def run_aggregator() -> tuple[Path, list[Path]]:
    """Run the aggregation pipeline synchronously."""
    cfg = load_cfg()
    return asyncio.run(
        run_pipeline(cfg, sources_file=SOURCES_FILE, channels_file=CHANNELS_FILE)
    )


def run_merger() -> None:
    """Run the VPN merger using the latest aggregated results."""
    cfg = load_cfg()
    CONFIG.output_dir = cfg.output_dir
    CONFIG.resume_file = str(Path(cfg.output_dir) / "vpn_subscription_raw.txt")
    detect_and_run(Path(SOURCES_FILE))


@app.route("/aggregate")
def aggregate() -> dict:
    out_dir, files = run_aggregator()
    return {"output_dir": str(out_dir), "files": [str(p) for p in files]}


@app.route("/merge")
def merge() -> dict:
    run_merger()
    return {"status": "merge complete"}


@app.route("/report")
def report():
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
    app.run()


if __name__ == "__main__":
    main()
