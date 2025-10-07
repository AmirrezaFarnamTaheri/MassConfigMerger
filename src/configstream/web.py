"""Basic Flask server for ConfigStream."""

from __future__ import annotations

import asyncio
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

import nest_asyncio
from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    render_template_string,
    request,
    send_file,
)
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from .config import Settings, load_config
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

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ConfigStream Dashboard</title>
    <style>
        :root {
            color-scheme: light dark;
            --bg: #f7f7fb;
            --fg: #222;
            --accent: #2563eb;
            --accent-contrast: #ffffff;
            --card-bg: #ffffff;
            --border: #d5d7de;
            --muted: #4b5563;
            font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --bg: #0f172a;
                --fg: #f8fafc;
                --card-bg: #1e293b;
                --border: #334155;
                --muted: #94a3b8;
            }
        }
        body {
            margin: 0;
            background: var(--bg);
            color: var(--fg);
            min-height: 100vh;
        }
        header {
            padding: 2rem 1.5rem 0;
            max-width: 960px;
            margin: 0 auto;
        }
        h1 {
            font-size: clamp(2rem, 3vw, 2.75rem);
            margin-bottom: 0.5rem;
        }
        p.subtitle {
            color: var(--muted);
            margin-top: 0;
            max-width: 640px;
        }
        main {
            display: grid;
            gap: 1.5rem;
            padding: 2rem 1.5rem 3rem;
            max-width: 960px;
            margin: 0 auto;
        }
        .grid {
            display: grid;
            gap: 1rem;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 10px 30px rgb(15 23 42 / 12%);
            display: flex;
            flex-direction: column;
            gap: 1rem;
            transition: transform 150ms ease, box-shadow 150ms ease;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 16px 40px rgb(15 23 42 / 18%);
        }
        .card h2 {
            margin: 0;
            font-size: 1.25rem;
        }
        .card p {
            margin: 0;
            color: var(--muted);
            font-size: 0.95rem;
            line-height: 1.5;
        }
        button, .link-button {
            appearance: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.75rem 1rem;
            border-radius: 999px;
            border: 1px solid transparent;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            background: var(--accent);
            color: var(--accent-contrast);
            transition: background 150ms ease, transform 150ms ease;
        }
        button:hover,
        .link-button:hover {
            background: #1d4ed8;
            transform: translateY(-1px);
        }
        .link-button {
            text-decoration: none;
            text-align: center;
        }
        .token-field {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            margin-bottom: 0.25rem;
        }
        .token-field label {
            font-size: 0.8rem;
            color: var(--muted);
            font-weight: 500;
        }
        .token-field input {
            padding: 0.6rem 0.8rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: transparent;
            color: inherit;
            font-size: 0.95rem;
        }
        pre.result {
            margin: 0;
            padding: 0.75rem;
            border-radius: 12px;
            background: rgb(15 23 42 / 8%);
            color: inherit;
            max-height: 240px;
            overflow: auto;
            font-size: 0.85rem;
        }
        pre.result.error {
            border: 1px solid #f87171;
            background: rgb(248 113 113 / 15%);
        }
        footer {
            text-align: center;
            padding: 1.5rem;
            color: var(--muted);
            font-size: 0.85rem;
        }
        @media (max-width: 600px) {
            main {
                padding-left: 1rem;
                padding-right: 1rem;
            }
        }
    </style>
    <script>
        async function submitDashboardAction(event, endpoint, resultId) {
            event.preventDefault();
            const form = event.target;
            const tokenField = form.querySelector('input[name="token"]');
            const token = tokenField ? tokenField.value : '';
            const resultEl = document.getElementById(resultId);
            resultEl.textContent = 'Working…';
            resultEl.classList.remove('error');
            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: Object.assign(
                        {'Content-Type': 'application/json'},
                        token ? {'X-ConfigStream-Token': token} : {}
                    ),
                    body: JSON.stringify(token ? {token} : {}),
                });
                const text = await response.text();
                let payload;
                try {
                    payload = JSON.parse(text);
                } catch (err) {
                    payload = {message: text};
                }
                resultEl.textContent = JSON.stringify(payload, null, 2);
                if (!response.ok) {
                    resultEl.classList.add('error');
                }
            } catch (error) {
                resultEl.textContent = `Request failed: ${error}`;
                resultEl.classList.add('error');
            }
            return false;
        }
    </script>
</head>
<body>
    <header>
        <h1>ConfigStream Dashboard</h1>
        <p class="subtitle">
            Run data aggregation, trigger merger jobs, and inspect the latest reports without
            leaving your browser. Provide the dashboard token if one is configured for this
            instance to authorise protected actions.
        </p>
    </header>
    <main>
        <section class="grid" aria-label="Actions">
            <form class="card" onsubmit="return submitDashboardAction(event, '/aggregate', 'aggregate-result')">
                <div>
                    <h2>Run Aggregation</h2>
                    <p>Fetch all configured sources and build the intermediate dataset.</p>
                </div>
                <div class="token-field">
                    <label for="aggregate-token">Dashboard token (optional)</label>
                    <input type="password" id="aggregate-token" name="token" placeholder="Enter token if required" autocomplete="off" />
                </div>
                <button type="submit">Start Aggregation</button>
                <pre id="aggregate-result" class="result" aria-live="polite"></pre>
            </form>
            <form class="card" onsubmit="return submitDashboardAction(event, '/merge', 'merge-result')">
                <div>
                    <h2>Run Merge</h2>
                    <p>Combine the latest aggregation results and produce distribution files.</p>
                </div>
                <div class="token-field">
                    <label for="merge-token">Dashboard token (optional)</label>
                    <input type="password" id="merge-token" name="token" placeholder="Enter token if required" autocomplete="off" />
                </div>
                <button type="submit">Start Merge</button>
                <pre id="merge-result" class="result" aria-live="polite"></pre>
            </form>
        </section>
        <section class="grid" aria-label="Reports and tools">
            <a class="card link-button" href="/report">
                <div>
                    <h2>View Latest Report</h2>
                    <p>Open the most recent HTML or JSON report generated by the merger.</p>
                </div>
                <span>Open report →</span>
            </a>
            <a class="card link-button" href="/history">
                <div>
                    <h2>Proxy History</h2>
                    <p>Inspect connection success ratios, providers, and timestamps.</p>
                </div>
                <span>View history →</span>
            </a>
            <a class="card link-button" href="/metrics">
                <div>
                    <h2>Metrics Endpoint</h2>
                    <p>Scrape Prometheus-compatible metrics for integration and monitoring.</p>
                </div>
                <span>Open metrics →</span>
            </a>
            <a class="card link-button" href="/health">
                <div>
                    <h2>Health Check</h2>
                    <p>Simple readiness probe returning a JSON status payload.</p>
                </div>
                <span>Check status →</span>
            </a>
        </section>
    </main>
    <footer>
        ConfigStream · Secure dashboard interface
    </footer>
</body>
</html>
"""


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
    """Load configuration from ``CONFIG_PATH``."""
    return load_config(CONFIG_PATH)


@app.route("/")
def index():
    """Display the interactive dashboard."""

    return render_template_string(INDEX_TEMPLATE)


def _extract_token() -> str | None:
    """Return the dashboard token provided via headers, form, or JSON body."""

    header_token = request.headers.get("X-ConfigStream-Token")
    if header_token:
        return header_token

    if request.is_json:
        body: dict[str, Any] | None = request.get_json(silent=True)
        if body:
            token = body.get("token")
            if token:
                return str(token)

    form_token = request.form.get("token")
    if form_token:
        return form_token

    return request.args.get("token")


def _require_dashboard_token(config: Settings) -> None:
    """Abort with 403 if a configured dashboard token is not supplied."""

    expected = config.security.dashboard_token
    if not expected:
        return

    provided = _extract_token()
    if not provided or not secrets.compare_digest(str(expected), provided):
        abort(403, description="Invalid or missing dashboard token")


@app.route("/health")
def health_check():
    """Return a simple health check response."""
    return jsonify({"status": "ok"})


@app.route("/aggregate", methods=["POST"])
def aggregate() -> Response:
    """Run the aggregation pipeline and return the output files."""

    cfg = load_cfg()
    _require_dashboard_token(cfg)
    try:
        out_dir, files = asyncio.run(
            run_aggregation_pipeline(cfg, sources_file=SOURCES_FILE)
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    payload = {"output_dir": str(out_dir), "files": [str(p) for p in files]}
    return jsonify(payload)


@app.route("/merge", methods=["POST"])
def merge() -> Response:
    """Run the VPN merger using the latest aggregated results."""

    nest_asyncio.apply()
    cfg = load_cfg()
    _require_dashboard_token(cfg)
    project_root = _get_root()
    output_dir = project_root / cfg.output.output_dir
    resume_file = output_dir / RAW_SUBSCRIPTION_FILE_NAME
    if not resume_file.exists():
        return jsonify({"error": f"Resume file not found: {resume_file}"}), 404

    try:
        asyncio.run(
            run_merger_pipeline(
                cfg, sources_file=SOURCES_FILE, resume_file=resume_file
            )
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"status": "merge complete"})


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
            {% if history %}
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
            {% else %}
            <tr>
                <td colspan="5" style="text-align:center; color:var(--muted);">No proxy history recorded yet.</td>
            </tr>
            {% endif %}
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
