"""Parse daily_memory markdown files into Activity dataclasses."""
import os
import re
from pathlib import Path
from typing import Optional

try:
    from .models import Activity, SECTION_ALIASES
except ImportError:
    from models import Activity, SECTION_ALIASES


def parse_daily_memory(filepath: str) -> Optional[Activity]:
    """Parse a single daily_memory markdown file into an Activity.

    Args:
        filepath: Path to the daily_memory .md file.

    Returns:
        Activity instance or None if file is missing/empty.
    """
    if not os.path.exists(filepath):
        return None

    with open(filepath, encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        return None

    # Extract date from header or filename
    date_match = re.search(r"# (\d{4}-\d{2}-\d{2})", content)
    if date_match:
        date = date_match.group(1)
    else:
        # Fallback to filename — try YYYYMMDD format (e.g. world_news_20260601.md)
        stem = Path(filepath).stem
        yyyymmdd = re.search(r"(\d{4})(\d{2})(\d{2})", stem)
        if yyyymmdd:
            date = f"{yyyymmdd.group(1)}-{yyyymmdd.group(2)}-{yyyymmdd.group(3)}"
        else:
            # Try YYYY-MM-DD already in stem
            date = stem

    # Initialize result with known fields
    result = Activity(date=date)

    # Parse sections
    # Split by ## section headers
    section_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    parts = section_pattern.split(content)

    # First part is header/content before first ##, skip it
    current_section = None
    current_items = []

    for i, part in enumerate(parts[1:], 1):
        if i % 2 == 1:
            # Odd index = section name
            current_section = part.strip()
            current_items = []
        else:
            # Even index = section content
            section_name = current_section
            items = _parse_items(part)

            # Map section name
            normalized = SECTION_ALIASES.get(section_name, section_name)

            # Assign to appropriate field or raw_sections
            if normalized in ("completed", "main_work", "next_steps"):
                setattr(result, normalized, items)
            else:
                if normalized not in result.raw_sections:
                    result.raw_sections[normalized] = []
                result.raw_sections[normalized].extend(items)

    return result


def _parse_items(content: str) -> list[str]:
    """Parse list items from section content.

    Handles:
    - `- item` → top-level item
    - `  - subitem` (2-space indent) → nested, prepended with "  "

    Args:
        content: Section content string.

    Returns:
        List of item strings. Nested items have "  " prefix.
    """
    lines = content.split("\n")
    items = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("-"):
            # Determine indent level
            indent = len(line) - len(line.lstrip())
            if indent >= 2:
                # Nested item, keep 2-space prefix to indicate nesting
                items.append("  " + stripped[1:].strip())
            else:
                items.append(stripped[1:].strip())

    return items


def parse_all_memories(memories_dir: str) -> list[Activity]:
    """Parse all daily_memory markdown files in a directory.

    Args:
        memories_dir: Directory containing .md memory files.

    Returns:
        List of Activity instances, sorted by date ascending.
        Files that return None are skipped.
    """
    path = Path(memories_dir)
    if not path.exists():
        return []

    activities = []
    for filepath in path.glob("*.md"):
        activity = parse_daily_memory(str(filepath))
        if activity is not None:
            activities.append(activity)

    # Sort by date ascending
    activities.sort(key=lambda a: a.date)
    return activities


def memory_to_html(content: str) -> str:
    """Convert markdown content to HTML.

    Handles:
    - `- item` → `<li>item</li>`
    - `  - subitem` (2-space indent) → nested `<ul><li>subitem</li></ul>`
    - `**text**` → `<strong>text</strong>`
    - Empty lines → `</ul><ul>` (list separation)

    Args:
        content: Markdown content string.

    Returns:
        HTML string.
    """
    if not content:
        return ""

    lines = content.split("\n")
    html_parts = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            # Empty line - close and reopen list for separation
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue

        if stripped.startswith("-"):
            # List item
            indent = len(line) - len(line.lstrip())
            item_text = stripped[1:].strip()

            if indent >= 2:
                # Nested item - wrap in nested ul
                if not in_list:
                    html_parts.append("<ul>")
                    in_list = True
                html_parts.append(f'<ul><li>{_apply_bold(item_text)}</li></ul>')
            else:
                # Top-level item
                if not in_list:
                    html_parts.append("<ul>")
                    in_list = True
                html_parts.append(f"<li>{_apply_bold(item_text)}</li>")
        else:
            # Non-list line (shouldn't happen in section content, but handle it)
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<p>{_apply_bold(stripped)}</p>")

    # Close any open list
    if in_list:
        html_parts.append("</ul>")

    return "".join(html_parts)


def _apply_bold(text: str) -> str:
    """Apply **bold** markdown to HTML <strong> tags.

    Args:
        text: Text that may contain **bold** markers.

    Returns:
        Text with **text** converted to <strong>text</strong>.
    """
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)