"""Unit tests for scripts/generate_site.py."""
import html.parser

import pytest

from scripts.generate_site import (
    build_heatmap_data,
    categorize_activities,
    compute_stats,
    flatten_activities,
    render_site,
)
from scripts.models import Activity, CronJob


class TestFlattenActivities:
    def test_flatten_activities(self):
        activities = [
            Activity(
                date="2024-01-15",
                completed=["Task A", "Task B - detail"],
                main_work=["Main item"],
            ),
        ]
        result = flatten_activities(activities)
        assert len(result) == 3
        assert result[0]["date"] == "2024-01-15"
        assert result[0]["title"] == "Task A"
        assert result[0]["detail"] == ""
        assert result[1]["title"] == "Task B"
        assert result[1]["detail"] == "detail"
        assert result[2]["title"] == "Main item"

    def test_flatten_activities_skips_nested(self):
        activities = [
            Activity(date="2024-01-15", completed=["Parent", "  Nested item"]),
        ]
        result = flatten_activities(activities)
        titles = [r["title"] for r in result]
        assert "Parent" in titles
        assert "Nested item" not in titles
        assert "  Nested item" not in titles

    def test_flatten_activities_extracts_title_detail(self):
        activities = [
            Activity(
                date="2024-01-15",
                completed=["Title - detail", "Title — emdash detail", "No separator"],
            ),
        ]
        result = flatten_activities(activities)
        assert result[0]["title"] == "Title"
        assert result[0]["detail"] == "detail"
        assert result[1]["title"] == "Title"
        assert result[1]["detail"] == "emdash detail"
        assert result[2]["title"] == "No separator"
        assert result[2]["detail"] == ""

    def test_flatten_activities_sorts_by_date_desc(self):
        activities = [
            Activity(date="2024-01-10", completed=["A"]),
            Activity(date="2024-01-15", completed=["B"]),
            Activity(date="2024-01-12", completed=["C"]),
        ]
        result = flatten_activities(activities)
        dates = [r["date"] for r in result]
        assert dates == ["2024-01-15", "2024-01-12", "2024-01-10"]


class TestBuildHeatmap:
    def test_build_heatmap_empty(self):
        assert build_heatmap_data([]) == []

    def test_build_heatmap_has_7_rows(self):
        activities = [
            Activity(date="2024-01-15", completed=["A", "B"], main_work=["C"]),
        ]
        rows = build_heatmap_data(activities, days=90)
        assert len(rows) == 7
        labels = [r["label"] for r in rows]
        assert set(labels) == {"월", "화", "수", "목", "금", "토", "일"}


class TestComputeStats:
    def test_compute_stats_empty(self):
        assert compute_stats([]) == []

    def test_compute_stats_counts(self):
        activities = [
            Activity(date="2024-01-15", completed=["A", "B"], main_work=["C"]),
            Activity(date="2024-01-16", completed=["D"]),
        ]
        stats = compute_stats(activities)
        labels = [s["label"] for s in stats]
        assert "총 활동" in labels
        total = next(s["value"] for s in stats if s["label"] == "총 활동")
        assert total == 4
        active_days = next(s["value"] for s in stats if s["label"] == "활동 일수")
        assert active_days == 2


class TestCategorizeActivities:
    def test_categorize_activities(self):
        items = [
            {"title": "개발 작업", "detail": "코딩 중"},
            {"title": "보고서", "detail": "분석 완료"},
            {"title": "기타 작업", "detail": "something"},
        ]
        result = categorize_activities(items)
        names = [r["name"] for r in result]
        assert "개발" in names
        assert "연구" in names
        assert "기타" in names

    def test_categorize_activities_empty(self):
        assert categorize_activities([]) == []


@pytest.fixture
def sample_activities():
    return [
        Activity(date="2024-01-15", completed=["개발 작업 - 코딩"]),
        Activity(date="2024-01-14", completed=["보고서 작성"]),
    ]


@pytest.fixture
def sample_cron_jobs():
    return [
        CronJob(
            id="test-1",
            name="Test Job",
            schedule_display="매일 08:00 KST",
            status="ok",
        ),
    ]


class TestRenderHtml:
    def test_render_html_has_doctype(self, tmp_path, sample_activities, sample_cron_jobs):
        output = tmp_path / "out.html"
        render_site(sample_activities, sample_cron_jobs, str(output))
        html = output.read_text(encoding="utf-8")
        assert html.startswith("<!DOCTYPE HTML>")

    def test_render_html_has_all_static_sections(
        self, tmp_path, sample_activities, sample_cron_jobs
    ):
        output = tmp_path / "out.html"
        render_site(sample_activities, sample_cron_jobs, str(output))
        html = output.read_text(encoding="utf-8")
        assert "저에 대해" in html
        assert "에이전트 헤르" in html
        assert "사용자 정보" in html
        assert "메모리 시스템" in html

    def test_render_html_has_scripts(self, tmp_path, sample_activities, sample_cron_jobs):
        output = tmp_path / "out.html"
        render_site(sample_activities, sample_cron_jobs, str(output))
        html = output.read_text(encoding="utf-8")
        assert html.count("<script") >= 6

    def test_render_html_has_timestamp(self, tmp_path, sample_activities, sample_cron_jobs):
        output = tmp_path / "out.html"
        render_site(sample_activities, sample_cron_jobs, str(output))
        html = output.read_text(encoding="utf-8")
        assert "Last updated:" in html

    def test_render_html_empty_data_no_crash(self, tmp_path):
        output = tmp_path / "out.html"
        render_site([], [], str(output))
        html = output.read_text(encoding="utf-8")
        assert "<!DOCTYPE HTML>" in html

    def test_render_html_heatmap_present(self, tmp_path, sample_activities, sample_cron_jobs):
        output = tmp_path / "out.html"
        render_site(sample_activities, sample_cron_jobs, str(output))
        html = output.read_text(encoding="utf-8")
        assert "heatmap" in html

    def test_render_html_stats_present(self, tmp_path, sample_activities, sample_cron_jobs):
        output = tmp_path / "out.html"
        render_site(sample_activities, sample_cron_jobs, str(output))
        html = output.read_text(encoding="utf-8")
        assert "stats-grid" in html or "stats-card" in html

    def test_render_html_categories_present(self, tmp_path, sample_activities, sample_cron_jobs):
        output = tmp_path / "out.html"
        render_site(sample_activities, sample_cron_jobs, str(output))
        html = output.read_text(encoding="utf-8")
        assert "category-tags" in html or "category-tag" in html
