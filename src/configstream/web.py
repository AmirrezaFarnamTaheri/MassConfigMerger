"""Flask web interface for ConfigStream."""

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
    render_template_string,
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
    """Load configuration from ``CONFIG_PATH``."""
    return load_config(CONFIG_PATH)


def _run_async_task(coro: asyncio.Future) -> Any:
    """Execute *coro* in a way that tolerates nested event loops."""

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

    token_from_header = header_token.strip() if header_token else None
    if token_from_header == "":
        token_from_header = None

    token_from_bearer = None
    if auth_header:
        scheme, _, value = auth_header.partition(" ")
        scheme = scheme.strip().lower()
        value = value.strip()
        if scheme == "bearer" and value:
            token_from_bearer = value

    # If both are provided and non-empty, reject to avoid ambiguity
    if token_from_header and token_from_bearer:
        return None

    token = token_from_header or token_from_bearer
    if token and token.strip():
        return token.strip()
    return None


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
            "country": stats.get("country") or stats.get("location"),
            "isp": stats.get("isp"),
            "latency_ms": latency,
        }
        entries.append(entry)

    entries.sort(
        key=lambda item: (
            item["reliability"],
            item["successes"],
            -item["failures"],
            item["key"],
        ),
        reverse=True,
    )
    return entries


async def _read_history(db_path: Path) -> Dict[str, Dict[str, Any]]:
    db = Database(db_path)
    try:
        await db.connect()
        return await db.get_proxy_history()
    finally:
        await db.close()


def _load_history_preview(limit: int = 5) -> List[Dict[str, Any]]:
    try:
        cfg = load_cfg()
        project_root = _get_root()
        db_path = project_root / cfg.output.history_db_file
        history_data = _run_async_task(_read_history(db_path))
        entries = _serialize_history(history_data)
        return entries[:limit]
    except Exception:  # pragma: no cover - defensive guard for dashboard
        logging.getLogger(__name__).debug("History preview unavailable", exc_info=True)
        return []


@app.route("/")
def index():
    """Display the main dashboard with quick actions."""

    history_preview = _load_history_preview()
    preview_limit = len(history_preview) if history_preview else 5
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>ConfigStream Control Panel</title>
        <style>
            :root {
                color-scheme: light dark;
                --bg: #f5f7fb;
                --card-bg: rgba(255, 255, 255, 0.85);
                --card-border: rgba(15, 23, 42, 0.08);
                --accent: #2563eb;
                --accent-hover: #1d4ed8;
                --danger: #dc2626;
                --warning: #f59e0b;
                --success: #16a34a;
                --text: #0f172a;
            }
            @media (prefers-color-scheme: dark) {
                :root {
                    --bg: #0f172a;
                    --card-bg: rgba(15, 23, 42, 0.85);
                    --card-border: rgba(148, 163, 184, 0.15);
                    --text: #e2e8f0;
                }
            }
            * { box-sizing: border-box; }
            body {
                margin: 0;
                padding: 2.5rem;
                font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, rgba(37,99,235,0.08), rgba(22,163,74,0.06)) var(--bg);
                color: var(--text);
            }
            .container {
                max-width: 1080px;
                margin: 0 auto;
            }
            header {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
                margin-bottom: 2rem;
            }
            header h1 {
                margin: 0;
                font-size: 2.4rem;
            }
            header p {
                margin: 0;
                max-width: 60ch;
                line-height: 1.5;
                color: rgba(15, 23, 42, 0.7);
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 1.5rem;
            }
            .card {
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 18px;
                padding: 1.5rem;
                backdrop-filter: blur(6px);
                box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
            }
            .card h2 {
                margin-top: 0;
                font-size: 1.35rem;
            }
            .card p {
                line-height: 1.5;
                color: rgba(15, 23, 42, 0.75);
            }
            label.token-label {
                display: block;
                margin-top: 1rem;
                margin-bottom: 0.35rem;
                font-weight: 600;
            }
            input[type="password"] {
                width: 100%;
                padding: 0.65rem 0.75rem;
                border-radius: 10px;
                border: 1px solid rgba(148, 163, 184, 0.6);
                background: rgba(255, 255, 255, 0.7);
                color: inherit;
            }
            input[type="password"]:focus {
                outline: 2px solid rgba(37, 99, 235, 0.45);
                outline-offset: 2px;
            }
            .button-row {
                display: flex;
                gap: 0.75rem;
                margin-top: 1rem;
                flex-wrap: wrap;
            }
            button.action {
                flex: 1 1 160px;
                padding: 0.75rem 1rem;
                border-radius: 12px;
                border: none;
                background: linear-gradient(135deg, var(--accent), #3b82f6);
                color: white;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.18s ease, box-shadow 0.18s ease;
            }
            button.action:hover:enabled {
                transform: translateY(-2px);
                box-shadow: 0 12px 25px rgba(37, 99, 235, 0.25);
            }
            button.action:disabled {
                opacity: 0.6;
                cursor: progress;
            }
            pre#actionOutput {
                margin-top: 1rem;
                padding: 1rem;
                background: rgba(15, 23, 42, 0.75);
                color: #e2e8f0;
                border-radius: 12px;
                max-height: 220px;
                overflow: auto;
                font-size: 0.9rem;
            }
            ul.links {
                list-style: none;
                padding: 0;
                margin: 1rem 0 0;
                display: grid;
                gap: 0.75rem;
            }
            ul.links a {
                display: inline-flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem 1rem;
                border-radius: 12px;
                background: rgba(37, 99, 235, 0.08);
                color: inherit;
                text-decoration: none;
                font-weight: 600;
                transition: background 0.2s ease;
            }
            ul.links a:hover {
                background: rgba(37, 99, 235, 0.16);
            }
            table.history {
                width: 100%;
                border-collapse: collapse;
                margin-top: 1rem;
            }
            table.history th,
            table.history td {
                padding: 0.65rem 0.75rem;
                text-align: left;
                border-bottom: 1px solid rgba(148, 163, 184, 0.25);
            }
            table.history tbody tr:hover {
                background: rgba(148, 163, 184, 0.12);
            }
            .status-badge {
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                padding: 0.35rem 0.6rem;
                border-radius: 999px;
                font-size: 0.78rem;
                font-weight: 600;
                letter-spacing: 0.01em;
            }
            .status-healthy { background: rgba(22, 163, 74, 0.12); color: var(--success); }
            .status-warning { background: rgba(245, 158, 11, 0.12); color: var(--warning); }
            .status-critical { background: rgba(220, 38, 38, 0.12); color: var(--danger); }
            .status-untested { background: rgba(148, 163, 184, 0.18); color: rgba(15, 23, 42, 0.7); }
            .geo { font-size: 0.82rem; color: rgba(15, 23, 42, 0.6); }
            footer {
                margin-top: 2rem;
                text-align: center;
                font-size: 0.85rem;
                color: rgba(15, 23, 42, 0.6);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>ConfigStream Control Panel</h1>
                <p>Run aggregation and merge pipelines, inspect generated reports, and monitor proxy health without leaving your browser.</p>
            </header>
            <div class="grid">
                <section class="card" aria-labelledby="operations-heading">
                    <h2 id="operations-heading">Automated Operations</h2>
                    <p>Trigger the data aggregation and merging workflows. Provide the optional API token if enforcement is enabled in your configuration.</p>
                    <label class="token-label" for="apiToken">API Token (optional)</label>
                    <input id="apiToken" type="password" placeholder="Provide token if configured" autocomplete="off" />
                    <div class="button-row">
                        <button class="action" id="aggregateBtn">Run Aggregation</button>
                        <button class="action" id="mergeBtn">Run Merge</button>
                    </div>
                    <pre id="actionOutput" aria-live="polite">Awaiting action…</pre>
                </section>
                <section class="card" aria-labelledby="resources-heading">
                    <h2 id="resources-heading">Key Resources</h2>
                    <p>Open generated artifacts and operational endpoints in new tabs.</p>
                    <ul class="links">
                        <li><a href="/report" rel="noopener">Latest Report<span>→</span></a></li>
                        <li><a href="/history" rel="noopener">Detailed Proxy History<span>→</span></a></li>
                        <li><a href="/metrics" rel="noopener">Prometheus Metrics<span>→</span></a></li>
                        <li><a href="/health" rel="noopener">Health Check<span>→</span></a></li>
                    </ul>
                </section>
                <section class="card" aria-labelledby="history-heading">
                    <h2 id="history-heading">Top Performing Proxies</h2>
                    <p>Recent proxy test results ranked by reliability.</p>
                    <table class="history" aria-describedby="history-heading">
                        <thead>
                            <tr>
                                <th scope="col">Proxy</th>
                                <th scope="col">Success Rate</th>
                                <th scope="col">Tests</th>
                                <th scope="col">Status</th>
                                <th scope="col">Last Tested</th>
                            </tr>
                        </thead>
                        <tbody id="historyTableBody">
                            {% if history_preview %}
                                {% for entry in history_preview %}
                                <tr>
                                    <td>
                                        <strong>{{ entry.key }}</strong>
                                        <div class="geo">
                                            {% if entry.country %}
                                                {{ entry.country }}{% if entry.isp %} · {{ entry.isp }}{% endif %}
                                            {% elif entry.isp %}
                                                {{ entry.isp }}
                                            {% else %}
                                                —
                                            {% endif %}
                                        </div>
                                    </td>
                                    <td>{{ '%.2f'|format(entry.reliability_percent) }}%</td>
                                    <td>{{ entry.tests }}</td>
                                    <td><span class="status-badge {{ entry.status_class }}">{{ entry.status }}</span></td>
                                    <td>{{ entry.last_tested }}</td>
                                </tr>
                                {% endfor %}
                            {% else %}
                                <tr><td colspan="5">No proxy history recorded yet.</td></tr>
                            {% endif %}
                        </tbody>
                    </table>
                </section>
            </div>
            <footer>
                Metrics refreshed automatically from live data. Reload the page after running actions to view the latest summaries.
            </footer>
        </div>
        <script>
            const previewLimit = {{ preview_limit | tojson }};
            const historyTableBody = document.getElementById('historyTableBody');
            const output = document.getElementById('actionOutput');
            const tokenField = document.getElementById('apiToken');

            function setOutput(message, isError = false) {
                output.textContent = message;
                output.style.background = isError ? 'rgba(220,38,38,0.85)' : 'rgba(15,23,42,0.85)';
            }

            async function callAction(endpoint, button) {
                const btn = document.getElementById(button);
                const token = tokenField.value.trim();
                const headers = { 'Content-Type': 'application/json' };
                if (token) {
                    headers['X-API-Key'] = token;
                }
                setOutput('Running ' + endpoint + '…');
                btn.disabled = true;
                try {
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers,
                        body: JSON.stringify(token ? { token } : {})
                    });
                    const payload = await response.json().catch(() => ({ error: 'Invalid JSON response' }));
                    if (!response.ok) {
                        throw new Error(payload.error || response.statusText);
                    }
                    setOutput(JSON.stringify(payload, null, 2));
                } catch (err) {
                    console.error(err);
                    setOutput('Error: ' + err.message, true);
                } finally {
                    btn.disabled = false;
                }
            }

            document.getElementById('aggregateBtn').addEventListener('click', () => {
                callAction('/api/aggregate', 'aggregateBtn');
            });
            document.getElementById('mergeBtn').addEventListener('click', () => {
                callAction('/api/merge', 'mergeBtn');
            });

            async function refreshHistoryPreview() {
                try {
                    const response = await fetch(`/api/history?limit=${previewLimit}`);
                    if (!response.ok) {
                        return;
                    }
                    const data = await response.json();
                    const items = data.items || [];
                    if (!items.length) {
                        historyTableBody.innerHTML = '<tr><td colspan="5">No proxy history recorded yet.</td></tr>';
                        return;
                    }
                    historyTableBody.innerHTML = items.map(entry => `
                        <tr>
                            <td><strong>${entry.key}</strong><div class="geo">${entry.country ? entry.country + (entry.isp ? ' · ' + entry.isp : '') : (entry.isp || '—')}</div></td>
                            <td>${entry.reliability_percent.toFixed(2)}%</td>
                            <td>${entry.tests}</td>
                            <td><span class="status-badge ${entry.status_class}">${entry.status}</span></td>
                            <td>${entry.last_tested}</td>
                        </tr>
                    `).join('');
                } catch (err) {
                    console.error('Failed to refresh history preview', err);
                }
            }

            refreshHistoryPreview();
        </script>
    </body>
    </html>
    """
    return render_template_string(
        template,
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
    except Exception as exc:  # pragma: no cover - logged for diagnostics
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


@app.route("/aggregate", methods=["GET"])
def aggregate_legacy():
    """Guide users towards the secured API endpoint."""

    return (
        jsonify(
            {
                "error": "Use POST /api/aggregate. Actions now require an explicit request.",
            }
        ),
        405,
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
    except Exception as exc:  # pragma: no cover - logged for diagnostics
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


@app.route("/merge", methods=["GET"])
def merge_legacy():
    """Guide legacy callers toward the secured merge API."""

    return (
        jsonify(
            {
                "error": "Use POST /api/merge. Operations must be triggered explicitly.",
            }
        ),
        405,
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

    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>Proxy History</title>
        <style>
            body {
                font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                margin: 0;
                padding: 2rem;
                background: #0f172a;
                color: #e2e8f0;
            }
            a { color: #60a5fa; }
            .wrap { max-width: 1100px; margin: 0 auto; }
            header { margin-bottom: 1.5rem; }
            header h1 { margin: 0; font-size: 2rem; }
            header p { margin: 0.35rem 0 0; color: #94a3b8; }
            .summary {
                display: flex;
                gap: 1rem;
                flex-wrap: wrap;
                margin-bottom: 1.5rem;
            }
            .summary .pill {
                padding: 0.65rem 1rem;
                border-radius: 999px;
                background: rgba(148, 163, 184, 0.12);
                border: 1px solid rgba(148, 163, 184, 0.2);
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background: rgba(15, 23, 42, 0.75);
                border-radius: 16px;
                overflow: hidden;
            }
            thead { background: rgba(15, 23, 42, 0.9); }
            th, td {
                padding: 0.85rem 1rem;
                text-align: left;
                border-bottom: 1px solid rgba(148, 163, 184, 0.12);
            }
            tbody tr:hover { background: rgba(59, 130, 246, 0.12); }
            .status-badge {
                display: inline-block;
                padding: 0.35rem 0.7rem;
                border-radius: 999px;
                font-size: 0.8rem;
                font-weight: 600;
            }
            .status-healthy { background: rgba(34, 197, 94, 0.18); color: #4ade80; }
            .status-warning { background: rgba(234, 179, 8, 0.2); color: #facc15; }
            .status-critical { background: rgba(239, 68, 68, 0.25); color: #f87171; }
            .status-untested { background: rgba(148, 163, 184, 0.25); color: #cbd5f5; }
            .geo { font-size: 0.82rem; color: #94a3b8; }
        </style>
    </head>
    <body>
        <div class="wrap">
            <header>
                <h1>Proxy History</h1>
                <p>Reliability metrics for recently tested proxies. <a href="/">Back to dashboard</a></p>
            </header>
            <section class="summary">
                <div class="pill">Total tracked: {{ summary.total }}</div>
                <div class="pill">Healthy: {{ summary.healthy }}</div>
                <div class="pill">Critical: {{ summary.critical }}</div>
                <div class="pill">Untested: {{ summary.untested }}</div>
                <div class="pill">Generated: {{ summary.generated_at }} UTC</div>
            </section>
            <table aria-label="Proxy History">
                <thead>
                    <tr>
                        <th scope="col">Proxy</th>
                        <th scope="col">Successes</th>
                        <th scope="col">Failures</th>
                        <th scope="col">Success Rate</th>
                        <th scope="col">Tests</th>
                        <th scope="col">Status</th>
                        <th scope="col">Last Tested (UTC)</th>
                    </tr>
                </thead>
                <tbody>
                    {% if entries %}
                        {% for entry in entries %}
                        <tr>
                            <td>
                                <strong>{{ entry.key }}</strong>
                                <div class="geo">
                                    {% if entry.country %}
                                        {{ entry.country }}{% if entry.isp %} · {{ entry.isp }}{% endif %}
                                    {% elif entry.isp %}
                                        {{ entry.isp }}
                                    {% else %}
                                        —
                                    {% endif %}
                                </div>
                            </td>
                            <td>{{ entry.successes }}</td>
                            <td>{{ entry.failures }}</td>
                            <td>{{ '%.2f'|format(entry.reliability_percent) }}%</td>
                            <td>{{ entry.tests }}</td>
                            <td><span class="status-badge {{ entry.status_class }}">{{ entry.status }}</span></td>
                            <td>{{ entry.last_tested }}</td>
                        </tr>
                        {% endfor %}
                    {% else %}
                        <tr><td colspan="7">No proxy history recorded yet.</td></tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, entries=entries, summary=summary)


def main() -> None:
    """Run the Flask development server."""
    # Add prometheus wsgi middleware to route /metrics requests
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})
    app.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
