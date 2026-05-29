"""Unit tests for scripts/cron_reader.py."""
import json
import pytest

from scripts.cron_reader import cron_to_display, read_cron_jobs
from scripts.models import CronJob


class TestCronToDisplay:
    def test_daily_at_0800_kst(self):
        assert cron_to_display("0 8 * * *") == "매일 08:00 KST"

    def test_daily_at_0000_kst(self):
        assert cron_to_display("0 0 * * *") == "매일 00:00 KST"

    def test_every_minute(self):
        assert cron_to_display("* * * * *") == "매분"

    def test_every_hour_at_00_minute(self):
        assert cron_to_display("0 * * * *") == "매시 00분"

    def test_daily_at_0930_kst(self):
        assert cron_to_display("30 9 * * *") == "매일 09:30 KST"

    def test_non_five_part_input_returns_as_is(self):
        assert cron_to_display("invalid") == "invalid"
        assert cron_to_display("1 2 3 4") == "1 2 3 4"
        assert cron_to_display("1 2 3 4 5 6") == "1 2 3 4 5 6"


class TestReadCronJobs:
    def test_returns_list_of_cronjob_for_valid_json_with_enabled_jobs(self, tmp_path):
        jobs_file = tmp_path / "jobs.json"
        data = {
            "jobs": [
                {
                    "id": "job-1",
                    "name": "Daily Backup",
                    "enabled": True,
                    "schedule": {"expr": "0 8 * * *"},
                    "last_status": "ok",
                }
            ]
        }
        jobs_file.write_text(json.dumps(data), encoding="utf-8")

        result = read_cron_jobs(str(jobs_file))

        assert len(result) == 1
        assert isinstance(result[0], CronJob)
        assert result[0].id == "job-1"
        assert result[0].name == "Daily Backup"
        assert result[0].schedule_display == "매일 08:00 KST"
        assert result[0].status == "ok"

    def test_skips_jobs_with_enabled_false(self, tmp_path):
        jobs_file = tmp_path / "jobs.json"
        data = {
            "jobs": [
                {
                    "id": "enabled-job",
                    "name": "Enabled",
                    "enabled": True,
                    "schedule": {"expr": "0 8 * * *"},
                    "last_status": "ok",
                },
                {
                    "id": "disabled-job",
                    "name": "Disabled",
                    "enabled": False,
                    "schedule": {"expr": "0 9 * * *"},
                    "last_status": "error",
                },
            ]
        }
        jobs_file.write_text(json.dumps(data), encoding="utf-8")

        result = read_cron_jobs(str(jobs_file))

        assert len(result) == 1
        assert result[0].id == "enabled-job"

    def test_returns_empty_list_for_missing_file(self):
        result = read_cron_jobs("/nonexistent/path/jobs.json")
        assert result == []

    def test_returns_empty_list_for_malformed_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json", encoding="utf-8")

        result = read_cron_jobs(str(bad_file))

        assert result == []
