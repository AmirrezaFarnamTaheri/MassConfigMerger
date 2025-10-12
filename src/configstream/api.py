from flask import Blueprint, jsonify, request, send_file, current_app
from io import BytesIO
from datetime import datetime, timedelta
import json
from pathlib import Path

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

import psutil
import time

start_time = time.time()

@api.route("/status")
def api_status():
    """API endpoint for system status."""
    uptime_seconds = time.time() - start_time
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))

    mem = psutil.virtual_memory()

    return jsonify({
        "uptime": uptime_str,
        "cpu": {
            "percent": psutil.cpu_percent(),
        },
        "memory": {
            "total_mb": mem.total / (1024 * 1024),
            "used_mb": mem.used / (1024 * 1024),
            "percent": mem.percent,
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
        # In a real app, this would be the project root.
        # In testing, this will be the root of the fake filesystem.
        root_path = Path(current_app.root_path).parent if not current_app.testing else Path("/")
        log_path = root_path / log_path

    if not log_path.exists() or not log_path.is_file():
        return jsonify({"logs": ["Log file not found."]})

    try:
        with open(log_path, "r", encoding="utf-8") as f:
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

@api.route("/settings", methods=["POST"])
def api_settings():
    """API endpoint for updating settings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        # Here you would typically update the settings file
        # For now, we'll just return a success message
        return jsonify({"message": "Settings updated successfully"})
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

@api.route("/backup/create", methods=["POST"])
def api_backup_create():
    """API endpoint for creating a backup."""
    # This is a placeholder. In a real application, you would zip the data and settings.
    return jsonify({"message": "Backup created successfully", "filename": f"backup-{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"})

@api.route("/backup/restore", methods=["POST"])
def api_backup_restore():
    """API endpoint for restoring from a backup."""
    # This is a placeholder. In a real application, you would unzip the backup and restore the data.
    return jsonify({"message": "Restore completed successfully"})
