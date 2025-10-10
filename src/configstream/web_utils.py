# ConfigStream
# Copyright (C) 2025 Amirreza "Farnam" Taheri
# This program comes with ABSOLUTELY NO WARRANTY; for details type `show w`.
# This is free software, and you are welcome to redistribute it
# under certain conditions; type `show c` for details.
# For more information, see <https://amirrezafarnamtaheri.github.io/configStream/>.

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


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
