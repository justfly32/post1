# Site Refinement Learnings

## T6: Create Jinja2 Base Template (2026-05-26)

### What Was Done
- Created `templates/base.html` from existing `index.html`
- Preserved all static sections exactly as-is: #intro, #first, #second, #third, #cta, #spacer, #footer
- Added 6 Jinja2 blocks: `head`, `sidebar`, `timeline`, `cron_jobs`, `heatmap`, `stats`
- Replaced hardcoded timestamp with `{{ generated_at }}` variable
- Preserved all 7 JS script tags and inline `<style>` block (lines 13-199)
- Used Jinja2 whitespace control where appropriate

### Key Decisions
- **Block placement**: `head` and `sidebar` blocks wrap their respective content, allowing child templates to override or extend. `timeline`, `heatmap`, and `stats` blocks are nested within the #fourth section. `cron_jobs` block replaces the content of #fifth section.
- **Default content**: Timeline and cron_jobs blocks include the original static content as defaults, so the template renders identically to index.html when no blocks are overridden.
- **Structural preservation**: Kept the original HTML structure exactly, including any indentation quirks and the HTML5 UP template credits.

### Verification
- Template loads successfully with Jinja2 Environment
- All 6 blocks are present in source
- Default rendering produces identical output to original index.html
- Child template block overriding works correctly
- All 7 script tags, inline styles, and static sections are preserved in rendered output

### Files Created
- `templates/base.html` — Jinja2 base template with dynamic block placeholders
