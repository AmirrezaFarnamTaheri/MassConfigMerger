import time
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import psutil
from flask import Blueprint, jsonify, request, send_file, current_app

from . import web_dashboard

api = Blueprint('api', __name__)

@api.route("/current")
def api_current():
    """API endpoint for current test results."""
    try:
        data_dir = current_app.config["data_dir"]
        data = web_dashboard.get_current_results(data_dir, current_app.logger)
        filters = request.args.to_dict()
        if filters:
            data["nodes"] = web_dashboard.filter_nodes(data["nodes"], filters)
            data["total_tested"] = len(data["nodes"])
            data["successful"] = len([n for n in data["nodes"] if n["ping_ms"] > 0])
            data["failed"] = len([n for n in data["nodes"] if n["ping_ms"] < 0])
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route("/history")
def api_history():
    """API endpoint for historical data."""
    try:
        data_dir = current_app.config["data_dir"]
        hours = int(request.args.get("hours", 24))
        history = web_dashboard.get_history(data_dir, hours, current_app.logger)
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route("/statistics")
def api_statistics():
    """API endpoint for aggregated statistics."""
    try:
        data_dir = current_app.config["data_dir"]
        data = web_dashboard.get_current_results(data_dir, current_app.logger)
        nodes = data.get("nodes", [])
        protocols = {}
        countries = {}
        avg_ping_by_country = {}
        for node in nodes:
            if node.get("ping_ms", -1) > 0:
                proto = node["protocol"]
                protocols[proto] = protocols.get(proto, 0) + 1
                country = node.get("country_code", "Unknown")
                countries[country] = countries.get(country, 0) + 1
                if country not in avg_ping_by_country:
                    avg_ping_by_country[country] = []
                avg_ping_by_country[country].append(node["ping_ms"])
        for country, pings in avg_ping_by_country.items():
            avg_ping_by_country[country] = round(sum(pings) / len(pings), 2)
        return jsonify({
            "total_nodes": len(nodes),
            "successful_nodes": len([n for n in nodes if n.get("ping_ms", -1) > 0]),
            "protocols": protocols,
            "countries": countries,
            "avg_ping_by_country": avg_ping_by_country,
            "last_update": data.get("timestamp")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

import json

@api.route("/export/<format>")
def api_export(format: str):
    """Export data in various formats."""
    try:
        data_dir = current_app.config["data_dir"]
        data = web_dashboard.get_current_results(data_dir, current_app.logger)
        filters = request.args.to_dict()
        nodes = web_dashboard.filter_nodes(data["nodes"], filters)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if format == "csv":
            csv_data = web_dashboard.export_csv(nodes)
            return send_file(
                BytesIO(csv_data.encode('utf-8')),
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"vpn_nodes_{timestamp}.csv"
            )
        elif format == "json":
            payload = {
                "exported_at": datetime.now().isoformat(timespec="seconds"),
                "count": len(nodes),
                "nodes": nodes,
            }
            return send_file(
                BytesIO(json.dumps(payload, ensure_ascii=False).encode("utf-8")),
                mimetype="application/json",
                as_attachment=True,
                download_name=f"vpn_nodes_{timestamp}.json",
            )
        return jsonify({"error": f"Unsupported format: {format}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

start_time = time.time()

@api.route("/status")
def api_status():
    """API endpoint for system status."""
    uptime_seconds = time.time() - start_time
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))

    try:
        psutil.cpu_percent(interval=None)
        cpu_pct_raw = psutil.cpu_percent(interval=0.1)
    except Exception:
        cpu_pct_raw = 0.0
    cpu_pct = float(cpu_pct_raw)
    if not (cpu_pct == cpu_pct) or cpu_pct in (float("inf"), float("-inf")):
        cpu_pct = 0.0
    cpu_pct = max(0.0, min(100.0, cpu_pct))

    try:
        mem = psutil.virtual_memory()
        total = float(getattr(mem, "total", 0.0) or 0.0)
        used = float(getattr(mem, "used", 0.0) or 0.0)
        percent = float(getattr(mem, "percent", 0.0) or 0.0)
    except Exception:
        total = used = percent = 0.0

    if not (total == total) or total in (float("inf"), float("-inf")) or total < 0:
        total = 0.0
    if not (used == used) or used in (float("inf"), float("-inf")) or used < 0:
        used = 0.0
    if not (percent == percent) or percent in (float("inf"), float("-inf")) or percent < 0:
        percent = 0.0

    percent = max(0.0, min(100.0, percent))
    mem_total_mb = round(total / (1024 * 1024), 2) if total > 0 else 0.0
    mem_used_mb = round(min(used, total) / (1024 * 1024), 2) if total > 0 else 0.0

    return jsonify({
        "uptime": uptime_str,
        "cpu": {
            "percent": cpu_pct,
        },
        "memory": {
            "total_mb": mem_total_mb,
            "used_mb": mem_used_mb,
            "percent": percent,
        }
    })

@api.route("/logs")
def api_logs():
    """API endpoint for application logs."""
    settings = current_app.config["settings"]
    if settings.security.api_key and request.headers.get("X-API-Key") != settings.security.api_key:
        return jsonify({"error": "Unauthorized"}), 401

    log_file = settings.output.log_file or "configstream.log"
    log_path = Path(log_file)

    if not log_path.is_absolute():
        root_path = Path(current_app.root_path).parent
        log_path = root_path / log_path

    try:
        resolved_log_path = log_path.resolve(strict=True)
        resolved_root_path = Path(current_app.root_path).parent.resolve(strict=True)
        resolved_log_path.relative_to(resolved_root_path)
    except FileNotFoundError:
        return jsonify({"logs": ["Log file not found."]}), 200
    except (ValueError, Exception):
        return jsonify({"error": "Log file path is outside the allowed directory"}), 400

    try:
        with open(resolved_log_path, "r", encoding="utf-8") as f:
            logs = f.readlines()
        return jsonify({"logs": [line.strip() for line in logs[-100:]]}), 200
    except Exception as e:
        current_app.logger.exception("Error reading log file: %s", resolved_log_path)
        return jsonify({"logs": [f"Error reading log file: {e}"]}), 500

@api.route("/scheduler/jobs")
def api_scheduler_jobs():
    """API endpoint for scheduler jobs."""
    settings = current_app.config["settings"]
    scheduler = current_app.config["scheduler"]
    if settings.security.api_key and request.headers.get("X-API-Key") != settings.security.api_key:
        return jsonify({"error": "Unauthorized"}), 401
    jobs = []
    running_job_ids = {j.id for j in scheduler.scheduler.get_jobs() if j.next_run_time is not None}
    for job in scheduler.scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
            "is_running": job.id in running_job_ids
        })
    return jsonify({"jobs": jobs})

@api.route("/settings", methods=["POST"])
def api_settings():
    """API endpoint for updating settings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        # This is a placeholder. In a real application, you would update the settings file.
        # For now, we'll just return a success message
        return jsonify({"message": "Settings updated successfully"})
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

@api.route("/sources", methods=["POST"])
def api_add_source():
    """API endpoint for adding a new source."""
    try:
        data = request.get_json(silent=True) or {}
        url = (data.get("url") or "").strip()
        if not url:
            return jsonify({"error": "URL is required"}), 400
        if not (url.startswith("http://") or url.startswith("https://")):
            return jsonify({"error": "URL must start with http:// or https://"}), 400

        settings = current_app.config["settings"]
        sources_file = Path(settings.sources.sources_file)
        if not sources_file.is_absolute():
            sources_file = Path(current_app.root_path).parent / sources_file

        try:
            resolved_sources = sources_file.resolve()
            allowed_root = (Path(current_app.root_path).parent).resolve()
            resolved_sources.relative_to(allowed_root)
        except Exception:
            return jsonify({"error": "Invalid sources file path"}), 400

        sources_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            append_newline = True
            if sources_file.exists() and sources_file.stat().st_size > 0:
                with open(sources_file, "rb") as f:
                    f.seek(-1, 2)
                    append_newline = f.read(1) != b"\n"
            with open(sources_file, "a", encoding="utf-8") as f:
                if append_newline:
                    f.write("\n")
                f.write(url)
        except IOError as e:
            return jsonify({"error": f"Failed to write to sources file: {e}"}), 500

        return jsonify({"message": "Source added successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500