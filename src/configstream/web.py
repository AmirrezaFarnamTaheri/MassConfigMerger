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

    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>ConfigStream Control Panel</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 2rem 1rem;
                color: #1a202c;
            }

            .container {
                max-width: 1400px;
                margin: 0 auto;
            }

            .header {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 2rem;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
                margin-bottom: 2rem;
                text-align: center;
            }

            .logo {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 1rem;
                margin-bottom: 0.5rem;
            }

            .logo-icon {
                width: 64px;
                height: 64px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }

            .logo-icon svg {
                width: 36px;
                height: 36px;
                fill: white;
            }

            .logo h1 {
                font-size: 2.5rem;
                font-weight: 800;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }

            .tagline {
                color: #64748b;
                font-size: 1.1rem;
                margin-top: 0.5rem;
            }

            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 2rem;
                margin-bottom: 2rem;
            }

            .card {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 2rem;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
            }

            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
            }

            .card h2 {
                font-size: 1.5rem;
                margin-bottom: 1rem;
                color: #1a202c;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .card-icon {
                width: 32px;
                height: 32px;
                padding: 6px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .card-icon svg {
                width: 20px;
                height: 20px;
                fill: white;
            }

            .button-row {
                display: flex;
                gap: 1rem;
                margin-top: 1.5rem;
            }

            button.action {
                flex: 1;
                padding: 1rem 2rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }

            button.action:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
            }

            button.action:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }

            .links {
                list-style: none;
                display: grid;
                gap: 0.75rem;
            }

            .links a {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 1rem 1.25rem;
                background: linear-gradient(to right, #f8fafc, #f1f5f9);
                border-radius: 10px;
                color: #334155;
                text-decoration: none;
                font-weight: 500;
                transition: all 0.2s ease;
            }

            .links a:hover {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                transform: translateX(5px);
            }

            .links a span {
                font-weight: 700;
                font-size: 1.2rem;
            }

            input[type="password"],
            input[type="text"] {
                width: 100%;
                padding: 0.875rem 1rem;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                font-size: 1rem;
                transition: all 0.2s ease;
                margin-top: 0.5rem;
            }

            input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }

            .token-label {
                font-weight: 600;
                color: #475569;
                margin-top: 1rem;
                display: block;
            }

            #actionOutput {
                margin-top: 1.5rem;
                padding: 1.25rem;
                background: rgba(15, 23, 42, 0.85);
                color: #e2e8f0;
                border-radius: 10px;
                font-family: 'Monaco', 'Courier New', monospace;
                font-size: 0.875rem;
                white-space: pre-wrap;
                word-wrap: break-word;
                min-height: 80px;
                line-height: 1.6;
            }

            table.history {
                width: 100%;
                border-collapse: collapse;
                margin-top: 1rem;
            }

            table.history thead {
                background: linear-gradient(to right, #f8fafc, #f1f5f9);
            }

            table.history th {
                padding: 1rem;
                text-align: left;
                font-weight: 600;
                color: #475569;
                font-size: 0.875rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }

            table.history td {
                padding: 1rem;
                border-bottom: 1px solid #e2e8f0;
                color: #334155;
            }

            table.history tbody tr:hover {
                background: #f8fafc;
            }

            .geo {
                font-size: 0.8rem;
                color: #64748b;
                margin-top: 0.25rem;
            }

            .status-badge {
                padding: 0.375rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }

            .status-healthy {
                background: #dcfce7;
                color: #166534;
            }

            .status-warning {
                background: #fef3c7;
                color: #92400e;
            }

            .status-critical {
                background: #fee2e2;
                color: #991b1b;
            }

            .status-untested {
                background: #f1f5f9;
                color: #475569;
            }

            footer {
                text-align: center;
                padding: 2rem;
                color: rgba(255, 255, 255, 0.8);
                font-size: 0.9rem;
            }

            @media (max-width: 768px) {
                .grid {
                    grid-template-columns: 1fr;
                }

                .button-row {
                    flex-direction: column;
                }

                .logo h1 {
                    font-size: 2rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header class="header">
                <div class="logo">
                    <div class="logo-icon">
                        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5zm0 18c-3.87-.96-7-5.05-7-9V8.26l7-3.12 7 3.12V11c0 3.95-3.13 8.04-7 9z"/>
                            <circle cx="12" cy="12" r="3"/>
                        </svg>
                    </div>
                    <h1>ConfigStream</h1>
                </div>
                <p class="tagline">VPN Configuration Management & Aggregation Platform</p>
            </header>

            <div class="grid">
                <div class="card">
                    <h2>
                        <div class="card-icon">
                            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                            </svg>
                        </div>
                        Pipeline Actions
                    </h2>
                    <p style="color: #64748b; margin-bottom: 1rem;">
                        Execute aggregation and merge operations. Provide the optional API token if enforcement is enabled.
                    </p>
                    <label class="token-label" for="apiToken">API Token (optional)</label>
                    <input id="apiToken" type="password" placeholder="Enter token if configured" autocomplete="off" />
                    <div class="button-row">
                        <button class="action" id="aggregateBtn">Run Aggregation</button>
                        <button class="action" id="mergeBtn">Run Merge</button>
                    </div>
                    <pre id="actionOutput" aria-live="polite">Awaiting action…</pre>
                </div>

                <div class="card">
                    <h2>
                        <div class="card-icon">
                            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                            </svg>
                        </div>
                        Resources & Reports
                    </h2>
                    <p style="color: #64748b; margin-bottom: 1rem;">
                        Access generated reports, metrics, and operational endpoints.
                    </p>
                    <ul class="links">
                        <li><a href="/report" rel="noopener">Latest Report<span>→</span></a></li>
                        <li><a href="/history" rel="noopener">Detailed Proxy History<span>→</span></a></li>
                        <li><a href="/metrics" rel="noopener">Prometheus Metrics<span>→</span></a></li>
                        <li><a href="/health" rel="noopener">Health Check<span>→</span></a></li>
                    </ul>
                </div>
            </div>

            <div class="card">
                <h2>
                    <div class="card-icon">
                        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
                        </svg>
                    </div>
                    Top Performing Proxies
                </h2>
                <p style="color: #64748b; margin-bottom: 1rem;">
                    Recent proxy test results ranked by reliability.
                </p>
                <table class="history" aria-label="Top proxies preview">
                    <thead>
                        <tr>
                            <th>Proxy</th>
                            <th>Success Rate</th>
                            <th>Tests</th>
                            <th>Status</th>
                            <th>Last Tested</th>
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
            </div>

            <footer>
                <p>ConfigStream v1.0 · Secure VPN Configuration Management</p>
                <p style="margin-top: 0.5rem; font-size: 0.8rem;">Metrics refresh automatically. Reload after running actions to view latest data.</p>
            </footer>
        </div>

        <script>
            const previewLimit = {{ preview_limit | tojson }};
            const historyTableBody = document.getElementById('historyTableBody');
            const output = document.getElementById('actionOutput');
            const tokenField = document.getElementById('apiToken');

            function setOutput(message, isError = false) {
                output.textContent = message;
                output.style.background = isError ? 'rgba(220, 38, 38, 0.9)' : 'rgba(15, 23, 42, 0.85)';
            }

            async function callAction(endpoint, buttonId) {
                const btn = document.getElementById(buttonId);
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
                    if (!response.ok) return;
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

    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Proxy History - ConfigStream</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 2rem 1rem;
                color: #1a202c;
            }

            .container {
                max-width: 1600px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 2rem;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
            }

            header {
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 1.5rem;
                margin-bottom: 2rem;
            }

            h1 {
                font-size: 2rem;
                font-weight: 800;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 1rem;
            }

            .back-link {
                display: inline-block;
                padding: 0.5rem 1rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.2s ease;
                margin-bottom: 1rem;
            }

            .back-link:hover {
                transform: translateX(-5px);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }

            .summary {
                display: flex;
                gap: 1rem;
                flex-wrap: wrap;
                margin-bottom: 2rem;
            }

            .pill {
                padding: 0.75rem 1.5rem;
                background: linear-gradient(to right, #f8fafc, #f1f5f9);
                border-radius: 999px;
                font-weight: 600;
                color: #334155;
                font-size: 0.875rem;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            }

            thead {
                background: linear-gradient(to right, #667eea, #764ba2);
                color: white;
            }

            th {
                padding: 1.25rem 1rem;
                text-align: left;
                font-weight: 600;
                font-size: 0.875rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }

            td {
                padding: 1.25rem 1rem;
                border-bottom: 1px solid #e2e8f0;
                color: #334155;
            }

            tbody tr:hover {
                background: #f8fafc;
            }

            tbody tr:last-child td {
                border-bottom: none;
            }

            .geo {
                font-size: 0.8rem;
                color: #64748b;
                margin-top: 0.25rem;
            }

            .status-badge {
                padding: 0.375rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }

            .status-healthy {
                background: #dcfce7;
                color: #166534;
            }

            .status-warning {
                background: #fef3c7;
                color: #92400e;
            }

            .status-critical {
                background: #fee2e2;
                color: #991b1b;
            }

            .status-untested {
                background: #f1f5f9;
                color: #475569;
            }

            @media (max-width: 768px) {
                .container {
                    padding: 1rem;
                }

                table {
                    font-size: 0.875rem;
                }

                th, td {
                    padding: 0.75rem 0.5rem;
                }

                h1 {
                    font-size: 1.5rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <a href="/" class="back-link">← Back to Dashboard</a>
                <h1>Complete Proxy History</h1>
            </header>

            <section class="summary">
                <div class="pill">📊 Total Tracked: {{ summary.total }}</div>
                <div class="pill">✅ Healthy: {{ summary.healthy }}</div>
                <div class="pill">⚠️ Critical: {{ summary.critical }}</div>
                <div class="pill">❓ Untested: {{ summary.untested }}</div>
                <div class="pill">🕐 Generated: {{ summary.generated_at }} UTC</div>
            </section>

            <table aria-label="Complete proxy history">
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
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})
    app.run(host="0.0.0.0", port=8080, debug=False)


if __name__ == "__main__":
    main()