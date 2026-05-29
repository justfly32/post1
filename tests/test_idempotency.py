"""Idempotency tests for site generation."""
from scripts.generate_site import flatten_activities, render_site
from scripts.models import Activity, CronJob


class TestIdempotency:
    def test_idempotent_except_timestamp(self, tmp_path):
        activities = [
            Activity(date="2024-01-15", completed=["Task A"]),
        ]
        cron_jobs = [
            CronJob(id="j1", name="Job", schedule_display="매일 08:00", status="ok"),
        ]
        out1 = tmp_path / "out1.html"
        out2 = tmp_path / "out2.html"
        render_site(activities, cron_jobs, str(out1))
        render_site(activities, cron_jobs, str(out2))

        html1 = out1.read_text(encoding="utf-8")
        html2 = out2.read_text(encoding="utf-8")

        lines1 = [ln for ln in html1.splitlines() if "Last updated:" not in ln]
        lines2 = [ln for ln in html2.splitlines() if "Last updated:" not in ln]
        assert lines1 == lines2

    def test_stable_sort(self):
        activities = [
            Activity(date="2024-01-10", completed=["Z"]),
            Activity(date="2024-01-15", completed=["A"]),
            Activity(date="2024-01-12", completed=["M"]),
        ]
        result1 = flatten_activities(activities)
        result2 = flatten_activities(activities)
        assert [r["title"] for r in result1] == [r["title"] for r in result2]
