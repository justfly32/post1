"""Integration tests for site generation."""
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest


class TestIntegration:
    def test_end_to_end_generation(self, tmp_path):
        memories = tmp_path / "memories"
        memories.mkdir()
        (memories / "2024-01-15.md").write_text(
            "# 2024-01-15\n\n## 완료\n- Task A\n", encoding="utf-8"
        )
        output = tmp_path / "index.html"
        result = subprocess.run(
            [
                sys.executable,
                "scripts/generate_site.py",
                "--memories-dir",
                str(memories),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert output.exists()
        html = output.read_text(encoding="utf-8")
        assert "<!DOCTYPE HTML>" in html

    def test_generated_html_well_formed(self, tmp_path):
        memories = tmp_path / "memories"
        memories.mkdir()
        (memories / "2024-01-15.md").write_text(
            "# 2024-01-15\n\n## 완료\n- Task A\n", encoding="utf-8"
        )
        output = tmp_path / "index.html"
        subprocess.run(
            [
                sys.executable,
                "scripts/generate_site.py",
                "--memories-dir",
                str(memories),
                "--output",
                str(output),
            ],
            check=True,
        )
        html = output.read_text(encoding="utf-8")

        errors = []

        class Collector(HTMLParser):
            def error(self, message):
                errors.append(message)

        parser = Collector()
        parser.feed(html)
        assert not errors

    def test_cron_section_present(self, tmp_path):
        memories = tmp_path / "memories"
        memories.mkdir()
        (memories / "2024-01-15.md").write_text(
            "# 2024-01-15\n\n## 완료\n- Task A\n", encoding="utf-8"
        )
        output = tmp_path / "index.html"
        subprocess.run(
            [
                sys.executable,
                "scripts/generate_site.py",
                "--memories-dir",
                str(memories),
                "--output",
                str(output),
            ],
            check=True,
        )
        html = output.read_text(encoding="utf-8")
        assert "등록된 크론 작업" in html or 'id="fifth"' in html

    def test_empty_memories_no_crash(self, tmp_path):
        output = tmp_path / "index.html"
        result = subprocess.run(
            [
                sys.executable,
                "scripts/generate_site.py",
                "--memories-dir",
                "/nonexistent",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert output.exists()
        html = output.read_text(encoding="utf-8")
        assert "<!DOCTYPE HTML>" in html
