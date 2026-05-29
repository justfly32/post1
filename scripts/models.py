"""Data models for site generation."""
from dataclasses import dataclass, field
from datetime import timezone, timedelta

DATE_FORMAT = "%Y-%m-%d"
KST = timezone(timedelta(hours=9))

SECTION_ALIASES: dict[str, str] = {
    "완료": "completed",
    "주요 작업": "main_work",
    "주요 논의": "main_discussion",
    "진행/논의": "in_progress",
    "다음 할일": "next_steps",
    "다음 할 일": "next_steps",
    "보관 위치": "storage",
    "참고": "reference",
    "완성된 가이드": "completed_guide",
    "모델 변경": "model_change",
    "논의": "discussion",
    "일정": "schedule",
}


@dataclass
class Activity:
    """Daily activity record."""
    date: str
    completed: list[str] = field(default_factory=list)
    main_work: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    raw_sections: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class CronJob:
    """Scheduled cron job for site generation."""
    id: str
    name: str
    schedule_display: str
    status: str


@dataclass
class SiteData:
    """Root data structure for site generation."""
    generated_at: str
    activities: list[Activity] = field(default_factory=list)
    cron_jobs: list[CronJob] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
