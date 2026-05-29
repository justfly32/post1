#!/usr/bin/env python3
"""Generate index.html from daily memories + cron jobs."""

import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running as script without package install
sys.path.insert(0, str(Path(__file__).parent))

from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound

from models import Activity, CronJob
from parser import parse_all_memories
from cron_reader import read_cron_jobs

KST = timezone(timedelta(hours=9))

# Icon mapping based on keywords in activity text
ICON_KEYWORDS = [
    ("fa-rocket", ["시작", "설치", "초기", "런칭", "배포"]),
    ("fa-code", ["개발", "코딩", "구현", "스크립트", "프로그램", "빌드", "리팩토링"]),
    ("fa-file-invoice", ["보고서", "리포트", "문서", "템플릿", "디자인"]),
    ("fa-columns", ["칸반", "보드", "워크플로", "시스템"]),
    ("fa-database", ["메모리", "데이터", "백업", "동기화", "저장", "구조"]),
    ("fa-file-powerpoint", ["PPT", "PPTX", "프레젠테이션", "슬라이드"]),
    ("fa-flask", ["분석", "연구", "탐구", "실험", "조사"]),
    ("fa-cloud-upload-alt", ["업로드", "OAuth", "토큰", "갱신", "API"]),
    ("fa-paint-brush", ["이미지", "디자인", "UI", "UX", "그래픽"]),
    ("fa-utensils", ["검색", "매장", "음식", "요식", "자동화 전략"]),
    ("fa-chart-line", ["주식", "투자", "금융", "경제", "분석"]),
    ("fa-bug", ["버그", "디버깅", "오류", "수정", "fix"]),
    ("fa-cogs", ["설정", "구성", "환경", "자동화"]),
    ("fa-book", ["학습", "공부", "교육", "강의", "책"]),
    ("fa-users", ["회의", "협업", "팀", "토론", "미팅"]),
    ("fa-check-circle", ["완료", "성공", "확인", "승인"]),
]

# Category mapping
CATEGORY_MAP = {
    "개발": ["개발", "코딩", "구현", "스크립트", "프로그램", "빌드", "리팩토링", "버그", "디버깅", "fix"],
    "연구": ["보고서", "리포트", "분석", "연구", "탐구", "조사", "학습", "공부"],
    "자동화": ["자동화", "크론", "스케줄", "동기화", "백업", "워크플로"],
    "설계": ["설계", "디자인", "템플릿", "UI", "UX", "구조"],
    "운영": ["배포", "런칭", "업로드", "동기화", "설정", "환경"],
    "협업": ["회의", "협업", "팀", "토론", "미팅", "커뮤니케이션"],
}


def _pick_icon(text: str) -> str:
    """Pick Font Awesome icon based on keywords in text."""
    text_lower = text.lower()
    for icon, keywords in ICON_KEYWORDS:
        for kw in keywords:
            if kw.lower() in text_lower:
                return icon
    return "fa-check-circle"


def flatten_activities(activities: list[Activity]) -> list[dict]:
    """Convert Activity objects to display-ready timeline items.

    For each activity, extract completed/main_work items as timeline entries.
    Returns list of {date, icon, title, detail, category} dicts.
    Use icon based on keywords: 'fa-rocket' for new, 'fa-code' for dev, etc.
    """
    items = []
    for activity in activities:
        # Combine completed and main_work for timeline
        all_items = []
        if activity.completed:
            all_items.extend(activity.completed)
        if activity.main_work:
            all_items.extend(activity.main_work)

        for raw_item in all_items:
            # Skip nested items (those starting with "  ")
            if raw_item.startswith("  "):
                continue

            # Extract title and detail
            if " — " in raw_item:
                title, detail = raw_item.split(" — ", 1)
            elif " - " in raw_item:
                title, detail = raw_item.split(" - ", 1)
            else:
                title = raw_item
                detail = ""

            # Clean title of markdown bold
            title = title.replace("**", "").strip()
            detail = detail.strip()

            icon = _pick_icon(title + " " + detail)

            items.append({
                "date": activity.date,
                "icon": icon,
                "title": title,
                "detail": detail,
                "category": "",
            })

    # Sort by date descending for timeline display
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


def build_heatmap_data(activities: list[Activity], days: int = 90) -> list[dict]:
    """Build GitHub-style contribution heatmap.

    Groups activity counts by date. Creates 7 rows (Mon-Sun) x N columns.
    Each cell: {date, count, level(0-4), today(bool)}.
    Row label: 요일 names.
    """
    if not activities:
        return []

    # Count activities per date
    date_counts: dict[str, int] = Counter()
    for activity in activities:
        date_counts[activity.date] += len(activity.completed or []) + len(activity.main_work or [])

    # Build date range: last N days ending on today
    today = datetime.now(KST).date()
    end_date = today
    start_date = end_date - timedelta(days=days - 1)

    # Generate all dates in range
    all_dates = []
    current = start_date
    while current <= end_date:
        all_dates.append(current)
        current += timedelta(days=1)

    # Group by weekday (0=Monday)
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    rows = []

    for weekday in range(7):
        cells = []
        for date_obj in all_dates:
            if date_obj.weekday() != weekday:
                continue
            date_str = date_obj.isoformat()
            count = date_counts.get(date_str, 0)
            # Level: 0=none, 1=1, 2=2-3, 3=4-6, 4=7+
            if count == 0:
                level = 0
            elif count == 1:
                level = 1
            elif count <= 3:
                level = 2
            elif count <= 6:
                level = 3
            else:
                level = 4

            cells.append({
                "date": date_str,
                "count": count,
                "level": level,
                "today": date_obj == today,
            })

        if cells:
            rows.append({
                "label": weekday_names[weekday],
                "cells": cells,
            })

    return rows


def compute_stats(activities: list[Activity]) -> list[dict]:
    """Compute summary stats.

    Returns list of {value, label}: total activities, active days, avg per day, etc.
    """
    if not activities:
        return []

    total_items = 0
    active_days = 0
    date_counts: dict[str, int] = Counter()

    for activity in activities:
        count = len(activity.completed or []) + len(activity.main_work or [])
        total_items += count
        if count > 0:
            active_days += 1
        date_counts[activity.date] = count

    # Most active date
    most_active_date = ""
    most_active_count = 0
    if date_counts:
        most_active_date, most_active_count = date_counts.most_common(1)[0]

    # Date range
    dates = sorted(date_counts.keys())
    total_days = 1
    if len(dates) >= 2:
        first = datetime.strptime(dates[0], "%Y-%m-%d").date()
        last = datetime.strptime(dates[-1], "%Y-%m-%d").date()
        total_days = max(1, (last - first).days + 1)

    avg_per_day = round(total_items / total_days, 1) if total_days > 0 else 0

    stats = [
        {"value": total_items, "label": "총 활동"},
        {"value": active_days, "label": "활동 일수"},
        {"value": avg_per_day, "label": "일 평균"},
    ]

    if most_active_date:
        stats.append({
            "value": f"{most_active_date} ({most_active_count})",
            "label": "최다 활동일",
        })

    return stats


def categorize_activities(timeline_items: list[dict]) -> list[dict]:
    """Simple keyword-based categorization.

    Keywords maps: 개발->dev, 보고서->writing, 자동화->automation, etc.
    Returns list of {name, count} sorted by count desc.
    """
    counts: dict[str, int] = Counter()

    for item in timeline_items:
        text = (item.get("title", "") + " " + item.get("detail", "")).lower()
        matched = False
        for cat_name, keywords in CATEGORY_MAP.items():
            for kw in keywords:
                if kw.lower() in text:
                    counts[cat_name] += 1
                    matched = True
                    break
            if matched:
                break
        if not matched:
            counts["기타"] += 1

    return [{"name": name, "count": count} for name, count in counts.most_common()]


def render_site(activities, cron_jobs, output_path="index.html", dry_run: bool = False):
    """Main render function.

    1. Flatten activities
    2. Build heatmap
    3. Compute stats
    4. Categorize
    5. Load Jinja2 Environment with FileSystemLoader
    6. Render base.html with all data
    7. Write to output_path
    8. Print summary
    """
    # 1. Flatten activities
    timeline_items = flatten_activities(activities)

    # 2. Build heatmap
    heatmap_rows = build_heatmap_data(activities)

    # 3. Compute stats
    stats_cards = compute_stats(activities)

    # 4. Categorize
    categories = categorize_activities(timeline_items)

    # 5. Load Jinja2
    env = Environment(loader=FileSystemLoader("templates/"))
    try:
        template = env.get_template("base.html")
    except TemplateNotFound:
        print("ERROR: templates/base.html not found", file=sys.stderr)
        sys.exit(1)

    # 6. Render
    generated_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    html = template.render(
        generated_at=generated_at,
        timeline_items=timeline_items,
        cron_jobs=cron_jobs,
        heatmap_rows=heatmap_rows,
        stats_cards=stats_cards,
        categories=categories,
    )

    # 7. Write or print
    if dry_run:
        print(html)
    else:
        output = Path(output_path)
        output.write_text(html, encoding="utf-8")

    # 8. Print summary
    print(
        f"Generated {output_path}: {len(timeline_items)} activities, "
        f"{len(cron_jobs)} cron jobs, updated {generated_at}"
    )


def main():
    parser = argparse.ArgumentParser(description="Generate Bear J's personal homepage")
    parser.add_argument(
        "--memories-dir",
        default=str(Path.home() / ".hermes" / "memories" / "daily_memories"),
        help="Directory containing daily memory .md files (default: ~/.hermes/memories/daily_memories)",
    )
    parser.add_argument(
        "--cron-file",
        default=str(Path.home() / ".hermes" / "cron" / "jobs.json"),
        help="Path to cron jobs JSON file",
    )
    parser.add_argument(
        "--output",
        default="index.html",
        help="Output HTML file path (default: index.html)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated HTML to stdout instead of writing to file",
    )
    args = parser.parse_args()

    # Parse memories (gracefully handle missing dir)
    activities = []
    memories_path = Path(args.memories_dir)
    if memories_path.exists():
        activities = parse_all_memories(str(memories_path))
    else:
        print(f"Warning: memories directory not found: {args.memories_dir}")

    # Read cron jobs (gracefully handle missing file)
    cron_jobs = []
    cron_path = Path(args.cron_file)
    if cron_path.exists():
        cron_jobs = read_cron_jobs(str(cron_path))
    else:
        print(f"Warning: cron file not found: {args.cron_file}")

    render_site(activities, cron_jobs, args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
