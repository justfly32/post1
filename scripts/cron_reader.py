"""Read and filter cron jobs from hermes JSON."""
import json
from pathlib import Path
from typing import Optional

try:
    from .models import CronJob
except ImportError:
    from models import CronJob


def read_cron_jobs(filepath: str | None = None) -> list[CronJob]:
    if filepath is None:
        filepath = str(Path.home() / ".hermes" / "cron" / "jobs.json")
    """Read and filter cron jobs from JSON file.

    Args:
        filepath: Path to the hermes cron jobs JSON file.

    Returns:
        List of CronJob objects for enabled jobs only.
        Returns empty list if file missing or malformed.
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return []

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

    except (json.JSONDecodeError, OSError):
        return []

    jobs = data.get("jobs", [])
    result = []

    for job in jobs:
        # Default to enabled=True if field missing
        if job.get("enabled", True) is not True:
            continue

        schedule_display = job.get("schedule_display", "")
        cron_expr = ""
        if "schedule" in job and isinstance(job["schedule"], dict):
            cron_expr = job["schedule"].get("expr", "")

        cron_job = CronJob(
            id=job.get("id", ""),
            name=job.get("name", ""),
            schedule_display=cron_to_display(cron_expr) if cron_expr else schedule_display,
            status=get_job_status(job),
        )
        result.append(cron_job)

    return result


def cron_to_display(expr: str) -> str:
    """Convert cron expression to Korean display string.

    Args:
        expr: Standard 5-field cron expression (e.g., "0 8 * * *")

    Returns:
        Korean display string (e.g., "매일 08:00 KST")
    """
    parts = expr.split()
    if len(parts) != 5:
        return expr

    minute, hour, _, _, _ = parts

    # Don't zero-pad non-numeric values like "H"
    minute_display = minute.zfill(2) if minute.isdigit() else minute
    hour_display = hour.zfill(2) if hour.isdigit() else hour

    if hour == "*" and minute == "*":
        return "매분"
    elif hour == "*":
        return f"매시 {minute_display}분"
    elif minute == "0" and hour != "*":
        return f"매일 {hour_display}:00 KST"
    elif minute == "*":
        return f"매일 {hour_display}시 매분"
    else:
        return f"매일 {hour_display}:{minute_display} KST"


def get_job_status(job: dict) -> str:
    """Derive job status from last_status field.

    Args:
        job: Cron job dictionary from hermes JSON.

    Returns:
        Status string: 'ok', 'error', or 'unknown'.
    """
    last_status = job.get("last_status", "")
    if last_status in ("ok", "error"):
        return last_status
    return "unknown"


if __name__ == "__main__":
    jobs = read_cron_jobs()
    for job in jobs:
        print(f"[{job.id[:8]}] {job.name} - {job.schedule_display} ({job.status})")
