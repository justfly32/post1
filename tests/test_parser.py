"""Unit tests for scripts/parser.py."""
import pytest

from scripts.models import Activity
from scripts.parser import parse_daily_memory, parse_all_memories, memory_to_html


class TestParseDailyMemory:
    def test_returns_activity_for_valid_markdown_with_completed(self, tmp_path):
        md = tmp_path / "2024-01-15.md"
        md.write_text("# 2024-01-15\n\n## 완료\n- Task A\n- Task B\n", encoding="utf-8")

        result = parse_daily_memory(str(md))

        assert isinstance(result, Activity)
        assert result.date == "2024-01-15"
        assert result.completed == ["Task A", "Task B"]

    def test_returns_activity_for_valid_markdown_with_main_work_and_next_steps(self, tmp_path):
        md = tmp_path / "2024-01-16.md"
        md.write_text(
            "# 2024-01-16\n\n## 주요 작업\n- Work item 1\n\n## 다음 할일\n- Next step 1\n",
            encoding="utf-8",
        )

        result = parse_daily_memory(str(md))

        assert isinstance(result, Activity)
        assert result.date == "2024-01-16"
        assert result.main_work == ["Work item 1"]
        assert result.next_steps == ["Next step 1"]

    def test_uses_section_aliases_to_normalize_names(self, tmp_path):
        md = tmp_path / "2024-01-17.md"
        md.write_text(
            "# 2024-01-17\n\n## 주요 작업\n- Aliased work\n",
            encoding="utf-8",
        )

        result = parse_daily_memory(str(md))

        assert result.main_work == ["Aliased work"]

    def test_returns_none_for_nonexistent_file(self):
        result = parse_daily_memory("/nonexistent/path/file.md")
        assert result is None

    def test_returns_none_for_empty_file(self, tmp_path):
        md = tmp_path / "empty.md"
        md.write_text("", encoding="utf-8")

        result = parse_daily_memory(str(md))

        assert result is None

    def test_handles_nested_list_items(self, tmp_path):
        md = tmp_path / "2024-01-18.md"
        md.write_text(
            "# 2024-01-18\n\n## 완료\n- Parent item\n  - Nested item\n",
            encoding="utf-8",
        )

        result = parse_daily_memory(str(md))

        assert result.completed == ["Parent item", "  Nested item"]

    def test_handles_bold_markdown_in_content(self, tmp_path):
        md = tmp_path / "2024-01-19.md"
        md.write_text(
            "# 2024-01-19\n\n## 완료\n- **Bold** task\n",
            encoding="utf-8",
        )

        result = parse_daily_memory(str(md))

        assert result.completed == ["**Bold** task"]


class TestParseAllMemories:
    def test_returns_sorted_list_for_directory_with_md_files(self, tmp_path):
        (tmp_path / "2024-01-20.md").write_text("# 2024-01-20\n\n## 완료\n- A\n", encoding="utf-8")
        (tmp_path / "2024-01-18.md").write_text("# 2024-01-18\n\n## 완료\n- B\n", encoding="utf-8")
        (tmp_path / "2024-01-19.md").write_text("# 2024-01-19\n\n## 완료\n- C\n", encoding="utf-8")

        result = parse_all_memories(str(tmp_path))

        assert len(result) == 3
        assert [a.date for a in result] == ["2024-01-18", "2024-01-19", "2024-01-20"]

    def test_returns_empty_list_for_nonexistent_directory(self):
        result = parse_all_memories("/nonexistent/dir")
        assert result == []

    def test_skips_files_that_return_none(self, tmp_path):
        (tmp_path / "valid.md").write_text("# 2024-01-20\n\n## 완료\n- A\n", encoding="utf-8")
        (tmp_path / "empty.md").write_text("", encoding="utf-8")

        result = parse_all_memories(str(tmp_path))

        assert len(result) == 1
        assert result[0].date == "2024-01-20"


class TestMemoryToHtml:
    def test_converts_dash_item_to_ul_li(self):
        assert memory_to_html("- item") == "<ul><li>item</li></ul>"

    def test_converts_bold_markdown_to_strong(self):
        assert memory_to_html("- **bold** text") == "<ul><li><strong>bold</strong> text</li></ul>"

    def test_handles_empty_string(self):
        assert memory_to_html("") == ""

    def test_handles_nested_items_with_proper_nesting(self):
        result = memory_to_html("- parent\n  - child")
        assert result == "<ul><li>parent</li><ul><li>child</li></ul></ul>"

    def test_empty_line_between_items_closes_and_reopens_ul(self):
        result = memory_to_html("- item1\n\n- item2")
        assert result == "<ul><li>item1</li></ul><ul><li>item2</li></ul>"
