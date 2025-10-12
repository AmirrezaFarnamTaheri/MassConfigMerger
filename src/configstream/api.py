from flask import Blueprint, jsonify, request, send_file, current_app
from io import BytesIO
from datetime import datetime, timedelta
import json
from pathlib import Path
import psutil
import time

api = Blueprint('api', __name__)

@api.route("/current")
def api_current():
    """API endpoint for current test results."""
    try:
        dashboard_data = current_app.config["dashboard_data"]
        data = dashboard_data.get_current_results()
        filters = request.args.to_dict()
        if filters:
            data["nodes"] = dashboard_data.filter_nodes(data["nodes"], filters)
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
        dashboard_data = current_app.config["dashboard_data"]
        hours = int(request.args.get("hours", 24))
        history = dashboard_data.get_history(hours)
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route("/statistics")
def api_statistics():
    """API endpoint for aggregated statistics."""
    try:
        dashboard_data = current_app.config["dashboard_data"]
        data = dashboard_data.get_current_results()
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

@api.route("/export/<format>")
def api_export(format: str):
    """Export data in various formats."""
    try:
        dashboard_data = current_app.config["dashboard_data"]
        data = dashboard_data.get_current_results()
        filters = request.args.to_dict()
        nodes = dashboard_data.filter_nodes(data["nodes"], filters)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if format == "csv":
            csv_data = dashboard_data.export_csv(nodes)
            return send_file(
                BytesIO(csv_data.encode('utf-8')),
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"vpn_nodes_{timestamp}.csv"
            )
        elif format == "json":
            payload_obj = {
                "exported_at": timestamp,
                "count": len(nodes),
                "nodes": nodes,
            }
            payload = json.dumps(payload_obj, indent=2)
            return send_file(
                BytesIO(payload.encode('utf-8')),
                mimetype="application/json",
                as_attachment=True,
                download_name=f"vpn_nodes_{timestamp}.json"
            )
        return jsonify({"error": f"Unsupported format: {format}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route("/status")
def api_status():
    """API endpoint for system status."""
    try:
        # System uptime rather than current process uptime
        uptime_seconds = time.time() - psutil.boot_time()
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))

        # Use system-wide CPU percent; interval=None uses last computed or returns instantly
        cpu_pct = psutil.cpu_percent(interval=None)

        mem = psutil.virtual_memory()
        mem_total_mb = round(mem.total / (1024 * 1024), 2)
        mem_used_mb = round(mem.used / (1024 * 1024), 2)

        return jsonify({
            "uptime": uptime_str,
            "cpu": {
                "percent": cpu_pct,
            },
            "memory": {
                "total_mb": mem_total_mb,
                "used_mb": mem_used_mb,
                "percent": mem.percent,
            }
        })
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve system status: {e}"}), 500

@api.route("/logs")
def api_logs():
    """API endpoint for application logs."""
    settings = current_app.config["settings"]
    if settings.security.api_key and request.headers.get("X-API-Key") != settings.security.api_key:
        return jsonify({"error": "Unauthorized"}), 401

    log_file = settings.output.log_file or "configstream.log"
    log_path = Path(log_file)

    # In a real app, this would be the project root.
    # In testing, this will be the root of the fake filesystem.
    root_path = Path(current_app.root_path).parent if not current_app.testing else Path("/")

    if not log_path.is_absolute():
        log_path = root_path / log_path

    # Security: Prevent path traversal attacks
    try:
        resolved_log_path = log_path.resolve(strict=True)
        resolved_root_path = root_path.resolve(strict=True)
        try:
            resolved_log_path.relative_to(resolved_root_path)
        except Exception:
            return jsonify({"error": "Log file path is outside the allowed directory"}), 400
    except (ValueError, FileNotFoundError):
        return jsonify({"error": "Invalid log file path"}), 400

    if not resolved_log_path.is_file():
        return jsonify({"logs": ["Log file not found."]})

    try:
        with open(resolved_log_path, "r", encoding="utf-8") as f:
            logs = f.readlines()
        return jsonify({"logs": [line.strip() for line in logs[-100:]]})
    except Exception as e:
        return jsonify({"logs": [f"Error reading log file: {e}"]})

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

@api.route("/sources", methods=["POST"])
def api_add_source():
    """API endpoint for adding a new source."""
    try:
        data = request.get_json()
        url = data.get("url")
        if not url:
            return jsonify({"error": "URL is required"}), 400

        settings = current_app.config["settings"]
        sources_file = Path(settings.sources.sources_file)
        if not sources_file.is_absolute():
            sources_file = Path(current_app.root_path).parent / sources_file

        try:
            with open(sources_file, "a", encoding="utf-8") as f:
                f.write(f"\n{url}")
        except IOError as e:
            return jsonify({"error": f"Failed to write to sources file: {e}"}), 500

        return jsonify({"message": "Source added successfully"})
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500
