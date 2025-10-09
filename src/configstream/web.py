"""Modern Flask web interface for ConfigStream with enhanced UI/UX."""

from __future__ import annotations

import asyncio
import io
import json
import os
import secrets
import shutil
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import nest_asyncio
import yaml
from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    render_template_string,
    request,
    send_file,
)
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from .config import Settings, load_config
from .constants import (
    HTML_REPORT_FILE_NAME,
    JSON_REPORT_FILE_NAME,
    RAW_SUBSCRIPTION_FILE_NAME,
    SOURCES_FILE,
)
from .core.file_utils import find_project_root
from .db import Database
from .pipeline import run_aggregation_pipeline
from .vpn_merger import run_merger as run_merger_pipeline


def create_app(settings_override: Optional[Settings] = None) -> Flask:
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, template_folder="templates")

    # Use provided settings or load default
    app.config["SETTINGS"] = settings_override or load_config()

    @app.context_processor
    def inject_utility_functions():
        """Inject utility functions into the template context."""
        return {"float": float}

    def _get_root() -> Path:
        """Get project root or fall back to CWD if not in a project env."""
        try:
            return find_project_root()
        except FileNotFoundError:
            return Path.cwd()

    def load_cfg() -> Settings:
        """Load configuration from the app context."""
        return app.config["SETTINGS"]

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

    def _get_request_settings() -> Settings:
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
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
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

    def _serialize_history(
        history_data: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        for key, stats in history_data.items():
            successes = _coerce_int(stats.get("successes"))
            failures = _coerce_int(stats.get("failures"))
            total = successes + failures
            reliability = (successes / total) if total else 0.0
            status, status_class = _classify_reliability(successes, failures)
            latency = _coerce_float(stats.get("latency_ms")) or _coerce_float(
                stats.get("latency")
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
        db_path = project_root / cfg.output.output_dir / cfg.output.history_db_file
        history_preview = []
        preview_limit = 5
        try:
            if db_path.exists():
                history_data = _run_async_task(_read_history(db_path))
                all_entries = _serialize_history(history_data)
                history_preview = all_entries[:preview_limit]
        except Exception as e:
            app.logger.warning("Could not fetch history for dashboard: %s", e)
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
                run_merger_pipeline(
                    cfg, sources_file=SOURCES_FILE, resume_file=resume_file
                )
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
            "<h1>VPN Report</h1><pre>{{ data }}</pre>",
            data=json.dumps(data, indent=2),
        )
        return html

    @app.get("/api/history")
    def history_api() -> Any:
        """Return proxy history statistics as JSON."""
        cfg = load_cfg()
        project_root = _get_root()
        db_path = project_root / cfg.output.output_dir / cfg.output.history_db_file
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

    @app.route("/analytics")
    def analytics():
        """Render the analytics page."""
        return render_template("analytics.html")

    @app.route("/history")
    def history():
        """Display the proxy history from the database."""
        cfg = load_cfg()
        project_root = _get_root()
        db_path = project_root / cfg.output.output_dir / cfg.output.history_db_file
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
        if "\n" in raw_url or "\r" in raw_url or len(url) > 2048:
            return jsonify({"error": "Invalid URL format"}), 400
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return jsonify({"error": "Only http/https URLs with host are allowed"}), 400
        project_root = _get_root()
        sources_file = project_root / SOURCES_FILE
        existing = []
        if sources_file.exists():
            existing = sources_file.read_text(encoding="utf-8").splitlines()
        if any(line.strip() == url for line in existing):
            return jsonify({"message": "Source already exists"}), 200
        new_lines = [*existing, url] if existing else [url]
        tmp_path = sources_file.with_suffix(sources_file.suffix + ".tmp")
        tmp_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        tmp_path.replace(sources_file)
        return jsonify({"message": "Source added successfully"}), 200

    @app.post("/api/sources/remove")
    def remove_source():
        """Remove a subscription source."""
        data = request.get_json(silent=True) or {}
        raw_url = data.get("url")
        if not raw_url or not isinstance(raw_url, str):
            return jsonify({"error": "URL is required"}), 400
        url_to_remove = raw_url.strip()
        if (
            "\n" in url_to_remove
            or "\r" in url_to_remove
            or len(url_to_remove) > 2048
        ):
            return jsonify({"error": "Invalid URL format"}), 400
        project_root = _get_root()
        sources_file = project_root / SOURCES_FILE
        if not sources_file.exists():
            return jsonify({"error": "Sources file not found"}), 404
        original = sources_file.read_text(encoding="utf-8").splitlines()
        filtered = [line for line in original if line.strip() != url_to_remove]
        if len(filtered) == len(original):
            return jsonify({"message": "Source not found"}), 200
        tmp_path = sources_file.with_suffix(sources_file.suffix + ".tmp")
        tmp_path.write_text(
            "\n".join(filtered) + ("\n" if filtered else ""), encoding="utf-8"
        )
        tmp_path.replace(sources_file)
        return jsonify({"message": "Source removed successfully"}), 200

    @app.route("/settings")
    def settings():
        """Display the current application settings."""
        cfg = load_cfg()
        config_path = cfg.config_file or "Default (no file loaded)"
        try:
            config_dict = cfg.model_dump(exclude={"config_file"})
            config_content = yaml.dump(
                config_dict, default_flow_style=False, sort_keys=False
            )
        except Exception:
            config_content = "# Could not serialize current settings."
        return render_template(
            "settings.html",
            config_path=str(config_path),
            config_content=config_content,
        )

    @app.route("/logs")
    def logs():
        """Display application logs."""
        log_file = (_get_root() / "web_server.log").resolve()
        root = _get_root().resolve()
        if not str(log_file).startswith(str(root)):
            abort(400)
        log_content = "Log file not found."
        if log_file.exists() and log_file.is_file():
            try:
                max_bytes = 512 * 1024  # 512 KB cap
                size = log_file.stat().st_size
                with open(log_file, "rb") as f:
                    if size > max_bytes:
                        f.seek(-max_bytes, 2)
                    data = f.read()
                log_content = data.decode("utf-8", errors="replace")
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
        _get_request_settings()
        root = _get_root()
        candidate_names = {"config.yaml", "sources.txt", "proxy_history.db"}
        max_total_bytes = 50 * 1024 * 1024
        sizes: List[tuple[Path, int]] = []
        for name in candidate_names:
            if Path(name).name != name:
                continue
            p = (root / name).resolve()
            if not str(p).startswith(str(root)):
                continue
            try:
                st = p.lstat()
            except OSError:
                continue
            if not p.exists() or not p.is_file() or p.is_symlink():
                continue
            sizes.append((p, st.st_size))
        total_bytes = sum(size for _, size in sizes)
        if total_bytes > max_total_bytes:
            return jsonify({"error": "Backup exceeds allowed size"}), 400
        memory_file = io.BytesIO()
        compression = getattr(zipfile, "ZIP_DEFLATED", zipfile.ZIP_STORED)
        with zipfile.ZipFile(memory_file, "w", compression) as zf:
            for file_path, _ in sizes:
                arcname = file_path.name
                if Path(arcname).name != arcname:
                    continue
                try:
                    with open(file_path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                zi = zipfile.ZipInfo(arcname)
                zi.external_attr = (0o600 & 0xFFFF) << 16
                zf.writestr(zi, data)
        memory_file.seek(0)
        return send_file(
            memory_file,
            download_name="configstream_backup.zip",
            as_attachment=True,
            mimetype="application/zip",
        )

    @app.post("/api/import-backup")
    def import_backup():
        """Import a zip archive to restore application data atomically."""
        if "backup_file" not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files["backup_file"]
        if not file or file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        filename = Path(file.filename)
        if filename.suffix.lower() != ".zip":
            return (
                jsonify({"error": "Invalid file type. Please upload a .zip file."}),
                400,
            )
        content_type = (file.mimetype or "").lower()
        if content_type not in {
            "application/zip",
            "application/x-zip-compressed",
            "multipart/x-zip",
        }:
            return jsonify({"error": "Invalid content-type for zip upload."}), 400
        data = file.read()
        if not data:
            return jsonify({"error": "Empty archive."}), 400
        memory_file = io.BytesIO(data)
        project_root = _get_root().resolve()
        tmp_dir = project_root / ".restore_tmp"
        try:
            with zipfile.ZipFile(memory_file, "r") as zf:
                if zf.testzip() is not None:
                    return jsonify({"error": "Corrupted zip archive."}), 400
                allowed_names = {"config.yaml",
                                 "sources.txt", "proxy_history.db"}
                max_total_uncompressed = 50 * 1024 * 1024
                max_file_uncompressed = 10 * 1024 * 1024
                total_uncompressed = 0
                tmp_dir.mkdir(parents=True, exist_ok=True)
                staged_paths: list[tuple[Path, zipfile.ZipInfo]] = []
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    member_path = Path(member.filename)
                    if (
                        member_path.is_absolute()
                        or member_path.drive
                        or member_path.parent != Path(".")
                        or member_path.name not in allowed_names
                    ):
                        return (
                            jsonify(
                                {"error": f"Disallowed file in archive: {member.filename}"}
                            ),
                            400,
                        )
                    if member.file_size > max_file_uncompressed:
                        return (
                            jsonify(
                                {"error": f"File too large in archive: {member.filename}"}),
                            400,
                        )
                    total_uncompressed += int(member.file_size or 0)
                    if total_uncompressed > max_total_uncompressed:
                        return jsonify({"error": "Archive content too large"}), 400
                    staged_target = (tmp_dir / member_path.name).resolve()
                    with zf.open(member, "r") as src, open(
                        staged_target, "wb"
                    ) as dst:
                        shutil.copyfileobj(src, dst)
                    os.chmod(staged_target, 0o600)
                    staged_paths.append((staged_target, member))
                for staged_target, member in staged_paths:
                    final_target = (
                        project_root / Path(member.filename).name
                    ).resolve()
                    staged_target.replace(final_target)
            return jsonify({"message": "Backup imported successfully."}), 200
        except zipfile.BadZipFile:
            return jsonify({"error": "Invalid zip file."}), 400
        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)

    return app


def main() -> None:
    """Run the Flask development server."""
    app = create_app()
    app.wsgi_app = DispatcherMiddleware(
        app.wsgi_app, {"/metrics": make_wsgi_app()})
    app.run(host="0.0.0.0", port=8080, debug=False)


if __name__ == "__main__":
    main()
