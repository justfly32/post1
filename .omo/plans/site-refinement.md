# 개인 사이트 자동화 고도화 (Python + Jinja2 Generator)

## TL;DR

> **Quick Summary**: Hermes agent의 LLM이 직접 HTML을 수정하던 방식을 Python + Jinja2 정적 생성기로 교체하여 데이터-프레젠테이션을 완전 분리하고, GitHub Contribution 스타일 히트맵과 통계 요약을 추가하여 사이트를 더 세련되게 개선
>
> **Deliverables**:
> - `scripts/generate_site.py` — 메인 정적 생성기
> - `templates/base.html` — Jinja2 베이스 템플릿 (모든 정적 섹션 보존)
> - `templates/timeline.html` — 활동 타임라인 템플릿
> - `templates/cron.html` — 크론 작업 템플릿
> - `templates/heatmap.html` — GitHub Contribution 스타일 히트맵
> - `templates/stats.html` — 통계 요약 카드
> - `site_data/activities.json` — 중간 데이터 (디버깅/확장용)
> - `tests/test_parser.py` — 파서 단위테스트
> - `tests/test_generator.py` — 생성기 테스트
> - Hermes cron prompt 교체 (LLM HTML 편집 → Python 실행)
>
> **Estimated Effort**: Medium (4-6시간)
> **Parallel Execution**: YES — 6 waves, 최대 6 concurrent tasks
> **Critical Path**: Task 1 → Task 7 → Task 15 → F1-F4

---

## Context

### Original Request
> "개인 사이트인데 헤르메스 에이전트와 한 일들을 자동으로 업데이트 시키고 있어. 좀 더 세련되게 만들 방안 제안해줘"

### Interview Summary
**Key Discussions**:
- **현재 방식 문제**: Hermes cron (매일 07:00 KST)이 LLM으로 daily_memory 읽고 index.html 직접 수정 → 구조 깨짐 위험, LLM 비용, merge conflict 이력
- **해결 방향**: Python + Jinja2 정적 생성기 도입, 데이터-프레젠테이션 완전 분리
- **전체 한 번에 (Phase 1 + 2)**: 데이터 분리 + 시각화 고도화를 하나의 계획으로
- **데이터 범위**: daily_memories + cron_jobs만 (kanban/세션/로그 제외)
- **디자인**: 현행 HTML5 UP Editorial 유지 + 히트맵/통계 보강
- **히트맵**: GitHub Contribution 스타일 (CSS Grid, 라이브러리 불필요)
- **테스트**: 파서 TDD + 템플릿 test-after + agent QA

**Research Findings**:
- **daily_memories 포맷 불일치**: `다음 할일` vs `다음 할 일` (띄어쓰기 차이), `주요 작업`/`주요 논의`/`진행/논의` 등 다양한 섹션 헤더
- **날짜 파일 누락**: 2026-05-24.md 존재하지 않음 (13개 파일, 5/12-5/25)
- **cron_jobs.json**: 8개 job 중 6개 enabled, 2개 disabled
- **Git 히스토리**: 이미 1회 merge conflict + 1회 라인번호 오염(LLM 실수) 발생
- **GitHub remote**: `github.com:justfly32/post1.git`
- **기존 cron prompt**: ~2000자 LLM 프롬프트가 HTML 직접 수정 (no_agent: false)

### Metis Review
**Identified Gaps** (addressed):
- **SECTION_ALIASES 필요**: `다음 할일`/`다음 할 일` 등 변종 헤더 매핑
- **날짜 누락 처리**: 없는 daily_memory 파일 → skip (crash 금지)
- **enabled 필터링**: cron_jobs.json에서 enabled: true만 표시
- **Idempotency**: 타임스탬프 제외 동일 입력 → 동일 출력 (불필요한 git diff 방지)
- **Markdown-to-HTML**: daily_memory 내 목록/볼드 텍스트 변환 필요
- **Race condition 방지**: 이전 크론 실행중 새 실행 금지
- **정적 섹션 보존**: intro/에이전트 헤르/사용자 정보/메모리 시스템/CTA/footer는 템플릿에 하드코딩

---

## Work Objectives

### Core Objective
Hermes agent의 활동 내역(index.html) 자동 업데이트 방식을 Python + Jinja2 정적 생성기로 전환하고 GitHub Contribution 스타일 히트맵과 통계 요약을 추가하여 사이트를 더 세련되게 개선한다.

### Concrete Deliverables
1. `scripts/generate_site.py` — 메인 생성기 (idempotent)
2. `templates/` — Jinja2 템플릿 5개 (base, timeline, cron, heatmap, stats)
3. `site_data/activities.json` — 중간 데이터 레이어
4. `tests/test_parser.py` + `tests/test_generator.py` — 테스트
5. Cron job prompt 교체 — LLM HTML 편집 → Python 실행
6. 활동 히트맵 — GitHub Contribution 스타일 (CSS Grid)
7. 통계 요약 카드 — 주간 활동 수, 연속 활동일, 활성 크론 수

### Definition of Done
- [ ] `python3 scripts/generate_site.py` 실행 → `index.html` 생성됨 (기존 디자인 유지)
- [ ] `python3 -m pytest tests/ -v` → 모든 테스트 통과
- [ ] `diff <(python3 scripts/generate_site.py) <(python3 scripts/generate_site.py)` → 타임스탬프 라인만 차이
- [ ] 브라우저에서 `index.html` 열었을 때 모든 섹션 정상 표시
- [ ] 히트맵 Grid가 7xN 레이아웃으로 렌더링됨
- [ ] 통계 카드에 "이번주 N개 활동", "연속 N일 활동" 등 표시
- [ ] Hermes cron이 Python 스크립트로 변경되어 정상 실행됨
- [ ] Telegram 알림 정상 전송

### Must Have
- 13개 기존 daily_memory 파일 전부 파싱 가능 (SECTION_ALIASES로 변종 대응)
- 없는 날짜(daily_memory 누락) → skip, crash 금지
- 생성된 index.html이 기존 정적 섹션(intro, 에이전트 헤르, 사용자 정보, 메모리 시스템, CTA, footer)을 그대로 보존
- 히트맵은 요일(일-토) x 주 단위 7xN CSS Grid
- cron job은 enabled: true인 작업만 표시
- git push 실패 시 비-zero exit code + 명확한 에러 메시지

### Must NOT Have (Guardrails)
- kanban/세션/로그 데이터 수집 금지 (이번 Plan scope 외)
- 프레임워크 마이그레이션 금지 (Astro/Hugo/Next.js)
- 웹 서버/CMS/관리자 인터페이스 금지
- JavaScript 프레임워크 도입 금지 (React/Vue)
- CSS 리팩토링 또는 별도 CSS 파일 분리 금지
- 기존 `assets/js/*.js` 파일 수정 금지
- CI/CD 파이프라인 구축 금지
- 기존 `index.html` 외 파일 수정 금지 (site_data/activities.json는 예외)

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.
> Acceptance criteria requiring "user manually tests/confirms" are FORBIDDEN.

### Test Decision
- **Infrastructure exists**: YES (`python3`, `pytest` 사용 가능)
- **Automated tests**: Hybrid — Parser: TDD / Templates: tests-after / Generator: agent QA
- **Framework**: `pytest` (Python)

### QA Policy
Every task MUST include agent-executed QA scenarios. Evidence saved to `.omo/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Python generator**: Use Bash — Run script, check exit code, validate output file
- **HTML structure**: Use Bash (Python/html.parser) — Parse generated HTML, assert structure
- **Idempotency**: Use Bash — Run generator twice, `diff` output (expect timestamp-only difference)
- **Cron integration**: Use Bash — Simulate cron execution, check git status

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation):
├── Task 1: 프로젝트 구조 + 의존성 [quick]
├── Task 2: 데이터 모델 정의 [quick]
├── Task 3: HTML 구조 분석 리포트 [quick]
├── Task 4: daily_memories 파서 [quick]
└── Task 5: cron_jobs.json 리더 [quick]

Wave 2 (After Wave 1 — templates, 내부 순차):
├── Task 6: Base 템플릿 (Jinja2) [writing]
├── Task 8: 타임라인 + 크론 템플릿 [writing]  (depends: Task 6)
└── Task 7: 메인 생성기 (generate_site.py) [deep]  (depends: Task 6, 8)

Wave 3 (After Wave 2 — Phase 2 visualization):
├── Task 9: 활동 히트맵 템플릿 [visual-engineering]
├── Task 10: 통계 요약 카드 [visual-engineering]
└── Task 11: 활동 카테고리 분석 [visual-engineering]

Wave 4 (After Wave 3 — testing):
├── Task 12: 파서 단위테스트 [quick]
├── Task 13: 생성기 + 템플릿 테스트 [quick]
└── Task 14: 통합 테스트 [unspecified-high]

Wave 5 (After Wave 4 — deployment):
└── Task 15: Hermes cron prompt 교체 + E2E 검증 [unspecified-high]

Wave FINAL (After ALL — 4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
```

### Dependency Matrix
- **1-5**: 없음 → 6, 8
- **6**: 1, 2, 3 → 8
- **8**: 6 → 7
- **7**: 1, 2, 3, 4, 5, 6, 8 → 9, 10, 11, 12, 13, 14
- **9-11**: 7 → 14 (통합)
- **12-14**: 4, 5, 7 → 15
- **15**: 12, 13, 14 → F1-F4

### Agent Dispatch Summary
- **Wave 1 (5)**: T1-T5 → `quick`
- **Wave 2 (3, sequential)**: T6(`writing`) → T8(`writing`) → T7(`deep`)
- **Wave 3 (3)**: T9-T11 → `visual-engineering`
- **Wave 4 (3)**: T12-T13 → `quick`, T14 → `unspecified-high`
- **Wave 5 (1)**: T15 → `unspecified-high`
- **FINAL (4)**: F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. 프로젝트 구조 생성 및 의존성 설치

  **What to do**:
  - 디렉토리 구조 생성: `scripts/`, `templates/`, `tests/`, `site_data/`
  - 의존성 설치: `pip3 install jinja2 python-dateutil`
  - `.gitignore`에 `site_data/activities.json` 추가 (생성물이므로)
  - 필요한 Python 내장 모듈 확인: `html.parser`, `json`, `os`, `re`, `datetime`, `collections`

  **Must NOT do**:
  - 기존 `assets/`, `images/`, `*.html` 파일 수정 금지
  - `node_modules` 또는 `package.json` 생성 금지

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5)
  - **Blocks**: 6 (Base template needs directory to exist)
  - **Blocked By**: None (can start immediately)

  **References**:
  - 기존 `brief_schedule_manager.py` (`~/.hermes/scripts/brief_schedule_manager.py`) — Hermes Python 스크립트 패턴 참고 (shebang, logging, exit code)
  - `/Users/bearj/personal-site/index.html:1-455` — 현재 전체 HTML 구조

  **Acceptance Criteria**:
  - [ ] `ls scripts/ templates/ tests/ site_data/` → 모든 디렉토리 존재
  - [ ] `python3 -c "import jinja2; print(jinja2.__version__)"` → 버전 출력 (에러 없음)
  - [ ] `.gitignore`에 `site_data/activities.json` 포함 확인

  **QA Scenarios**:
  ```
  Scenario: 디렉토리 및 의존성 검증
    Tool: Bash
    Preconditions: None
    Steps:
      1. ls -d scripts/ templates/ tests/ site_data/
      2. python3 -c "import jinja2; print('OK')"
    Expected Result: 모든 디렉토리 존재, jinja2 import 성공
    Evidence: .omo/evidence/task-1-scaffold.txt
  ```

- [x] 2. 데이터 모델 정의

  **What to do**:
  - `scripts/models.py` 생성:
    - `@dataclass Activity`: date, completed (list), main_work (list), next_steps (list), raw_sections (dict)
    - `@dataclass CronJob`: id, name, schedule_display, status (active/paused/error)
    - `@dataclass SiteData`: generated_at, activities (list[Activity]), cron_jobs (list[CronJob]), stats (dict)
  - `SECTION_ALIASES` 상수 정의:
    ```python
    SECTION_ALIASES = {
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
    }
    ```
  - `CRON_SCHEDULE_DISPLAY` 함수: cron 표현식 → 한국어 표시 ("0 8 * * *" → "매일 08:00 KST")
  - `DATE_FORMAT = "%Y-%m-%d"`, `KST = timezone(timedelta(hours=9))`

  **Must NOT do**:
  - ORM, DB 스키마 사용 금지 (순수 dataclass만)

  **References**:
  - `/Users/bearj/.hermes/memories/daily_memories/2026-05-25.md` — daily_memory 대표 포맷
  - `/Users/bearj/.hermes/cron/jobs.json` — cron job JSON 스키마
  - `/Users/bearj/personal-site/index.html:408-416` — cron 표시 포맷 ("매일 08:00 KST")

  **Acceptance Criteria**:
  - [ ] `python3 -c "from scripts.models import SiteData; print('OK')"` → import 성공
  - [ ] `python3 -c "from scripts.models import SECTION_ALIASES; assert len(SECTION_ALIASES) >= 10"` → 10개 이상 alias

  **QA Scenarios**:
  ```
  Scenario: 데이터 모델 import + 상수 검증
    Tool: Bash
    Preconditions: Task 1 완료
    Steps:
      1. python3 -c "from scripts.models import SiteData, SECTION_ALIASES; s=SiteData(generated_at='', activities=[], cron_jobs=[], stats={}); print('SiteData OK')"
      2. python3 -c "from scripts.models import SECTION_ALIASES; assert '다음 할일' in SECTION_ALIASES; assert '다음 할 일' in SECTION_ALIASES; print('SECTION_ALIASES OK')"
    Expected Result: 모든 import 성공, SECTION_ALIASES에 양쪽 변종 포함
    Evidence: .omo/evidence/task-2-models.txt
  ```

- [x] 3. 기존 HTML 구조 분석 및 템플릿 분할 기준 정의

  **What to do**:
  - `scripts/analyze_html.py` 생성 (참고용, 실행은 generate_site.py에서)
  - 현재 `index.html`에서 다음 정보 추출:
    - 정적 섹션 범위: `#intro`, `#first` (에이전트 헤르), `#second` (사용자 정보), `#third` (메모리 시스템), `#cta`, `#footer`, `#spacer`
    - 동적 섹션 범위: `#fourth` (활동 타임라인), `#fifth` (크론 작업)
    - 인라인 `<style>` 블록: lines 13-199 (전체 내용)
    - `<head>` 요소: title, meta, link 태그
    - `<script>` 태그: lines 444-451 (6개 JS)
    - 사이드바 네비게이션: `<nav>` 내부 링크 목록
  - 템플릿 분할 계획 문서화:
    - `base.html`: DOCTYPE ~ `</html>` 전체 (block으로 동적 부분 표시)
    - `timeline.html`: `#fourth` section 내부 `{% block timeline %}`
    - `cron.html`: `#fifth` section 내부 `{% block cron_jobs %}`
    - `heatmap.html`: `#fourth` section 내 신규 block `{% block heatmap %}`
    - `stats.html`: `#fourth` section 내 신규 block `{% block stats %}`

  **Must NOT do**:
  - 실제 index.html 수정 금지 (읽기만)

  **References**:
  - `/Users/bearj/personal-site/index.html:1-455` — 전체 HTML

  **Acceptance Criteria**:
  - [ ] 보고서에 각 정적 섹션의 시작/끝 라인 번호 명시
  - [ ] 템플릿 분할 계획 문서화 완료

  **QA Scenarios**:
  ```
  Scenario: HTML 구조 분석 검증
    Tool: Bash
    Preconditions: None
    Steps:
      1. grep -n '<section id=' index.html | head -10
      2. grep -n '<!-- Scripts -->' index.html
    Expected Result: 7개 section ID 확인, Scripts 섹션 위치 확인
    Evidence: .omo/evidence/task-3-html-analysis.txt
  ```

- [x] 4. daily_memories 파서 (Parser)

  **What to do**:
  - `scripts/parser.py` 생성:
    - `parse_daily_memory(filepath: str) -> Activity | None`: 단일 파일 파싱
    - `parse_all_memories(memories_dir: str) -> list[Activity]`: 디렉토리 전체 파싱
    - `memory_to_html(content: str) -> str`: 마크다운 리스트/볼드 → HTML 변환
  - 파싱 로직:
    1. `# YYYY-MM-DD 작업 기록` 헤더에서 날짜 추출
    2. `## 섹션명` 으로 섹션 분할
    3. 섹션명을 SECTION_ALIASES로 표준화
    4. 각 섹션 내 `- item`을 리스트로 파싱
    5. 인덴트된 서브아이템 처리 (공백 2개 → 하위 항목)
    6. **bold** 텍스트를 `<strong>`으로 변환
  - 오류 처리:
    - 파일 없음 → None 반환 (skip)
    - 빈 파일 → None 반환 (skip)
    - 알 수 없는 섹션 → `raw_sections`에 보존 (무시하지 않음)
    - 날짜 파싱 실패 → filename에서 날짜 추출
  - `memory_to_html()` 변환 규칙:
    - `- item` → `<li>item</li>`
    - `  - subitem` (2-space indent) → 내부 `<ul><li>subitem</li></ul>`
    - `**text**` → `<strong>text</strong>`
    - 빈 줄 → `</ul><ul>` (리스트 분리)

  **Must NOT do**:
  - 외부 markdown 라이브러리 사용 금지 (python-dateutil만 허용)
  - 파일 시스템 쓰기 금지 (read-only)

  **References**:
  - `/Users/bearj/.hermes/memories/daily_memories/2026-05-25.md` — 표준 포맷
  - `/Users/bearj/.hermes/memories/daily_memories/2026-05-16.md` — `보관 위치` 섹션 포함 (변종)
  - `/Users/bearj/.hermes/memories/daily_memories/2026-05-21.md` — `모델 변경` 섹션 포함 (변종)
  - `/Users/bearj/.hermes/memories/daily_memories/2026-05-22.md` — `진행/논의` 섹션 포함 (변종)
  - `scripts/models.py` — Activity dataclass, SECTION_ALIASES

  **Acceptance Criteria**:
  - [ ] 13개 기존 daily_memory 파일 전부 파싱 성공 (assert all are not None)
  - [ ] 없는 파일 → None 반환 (crash 금지)
  - [ ] `memory_to_html("**text**")` → `<strong>text</strong>`

  **QA Scenarios**:
  ```
  Scenario: 13개 daily_memory 파일 전부 파싱
    Tool: Bash
    Preconditions: Task 1, 2 완료
    Steps:
      1. python3 -c "from scripts.parser import parse_all_memories; acts=parse_all_memories('/Users/bearj/.hermes/memories/daily_memories/'); assert len(acts) == 13; print(f'Parsed {len(acts)} activities OK')"
      2. python3 -c "from scripts.parser import parse_daily_memory; r=parse_daily_memory('/nonexistent.md'); assert r is None; print('Missing file → None OK')"
    Expected Result: 13개 파싱 성공, 없는 파일 None 반환
    Evidence: .omo/evidence/task-4-parser.txt

  Scenario: memory_to_html 변환
    Tool: Bash
    Preconditions: Task 2 완료
    Steps:
      1. python3 -c "from scripts.parser import memory_to_html; h=memory_to_html('- **AI 보고서** 작성\\n  - 세부 분석'); assert '<strong>AI 보고서</strong>' in h; assert '<li>' in h; print('HTML conversion OK')"
    Expected Result: 마크다운 → HTML 변환 정상
    Evidence: .omo/evidence/task-4-html-convert.txt
  ```

- [x] 5. cron_jobs.json 리더 (Reader)

  **What to do**:
  - `scripts/cron_reader.py` 생성:
    - `read_cron_jobs(filepath: str) -> list[CronJob]`: JSON 읽고 enabled 필터링
    - `cron_to_display(expr: str) -> str`: cron 표현식 → 한국어 표시
    - `get_job_status(job: dict) -> str`: last_status 기반 상태 문자열
  
  - `cron_to_display()` 변환 표:
    - `"0 8 * * *"` → `"매일 08:00 KST"`
    - `"0 0 * * *"` → `"매일 00:00 KST"`
    - `"0 7 * * *"` → `"매일 07:00 KST"`
    - `"0 16 * * *"` → `"매일 16:00 KST"`
    - 기본: `"0 H * * *"` → `"매일 H:00 KST"` (포괄 패턴)
  - 오류 처리:
    - 파일 없음 → 빈 리스트 반환
    - JSON 파싱 실패 → try/except → 빈 리스트
    - `enabled` 필드 없음 → 기본 True

  **Must NOT do**:
  - cron job 수정 금지 (읽기만)
  - disabled job 표시 금지

  **References**:
  - `/Users/bearj/.hermes/cron/jobs.json` — 전체 크론 설정
  - `/Users/bearj/personal-site/index.html:385-416` — 현재 크론 표시 포맷
  - `scripts/models.py` — CronJob dataclass

  **Acceptance Criteria**:
  - [ ] `python3 -c "from scripts.cron_reader import read_cron_jobs; jobs=read_cron_jobs('/Users/bearj/.hermes/cron/jobs.json'); assert all(j.status == 'active' for j in jobs)"` — enabled만 반환
  - [ ] `python3 -c "from scripts.cron_reader import cron_to_display; assert '08:00' in cron_to_display('0 8 * * *')"` — 변환 정상
  - [ ] 없는 파일 → 빈 리스트 (crash 금지)

  **QA Scenarios**:
  ```
  Scenario: 크론 작업 읽기 및 필터링
    Tool: Bash
    Preconditions: Task 1, 2 완료
    Steps:
      1. python3 -c "from scripts.cron_reader import read_cron_jobs; j=read_cron_jobs('/Users/bearj/.hermes/cron/jobs.json'); assert len(j) > 0; print(f'{len(j)} enabled jobs')"
      2. python3 -c "from scripts.cron_reader import cron_to_display; print(cron_to_display('0 8 * * *')); print(cron_to_display('0 0 * * *'))"
    Expected Result: 6개 enabled jobs 반환, cron 표시 정상 변환
    Evidence: .omo/evidence/task-5-cron-reader.txt

  Scenario: 없는 파일 처리
    Tool: Bash
    Preconditions: None
    Steps:
      1. python3 -c "from scripts.cron_reader import read_cron_jobs; j=read_cron_jobs('/nonexistent.json'); assert j == []; print('Missing file → empty list OK')"
    Expected Result: 없는 파일 → 빈 리스트
    Evidence: .omo/evidence/task-5-cron-missing.txt
  ```

- [x] 6. Base 템플릿 (Jinja2)

  **What to do**:
  - `templates/base.html` 생성:
    - 기존 `index.html`에서 **정적 섹션만** 추출하여 템플릿으로 변환
    - `{% block head %}`, `{% block style %}`, `{% block sidebar %}`, `{% block content %}` 구조
    - 동적 부분은 `{% block timeline %}`, `{% block cron_jobs %}`, `{% block heatmap %}`, `{% block stats %}` 플레이스홀더
    - `<!-- Last updated: {{ generated_at }} -->` — Jinja2 변수로 대체
  - 보존해야 할 요소 (Task 3 분석 결과 기반):
    - `<head>` 전체 (title, meta, link, inline `<style>` lines 13-199)
    - `<body class="is-preload">`
    - `#wrapper`, `#sidebar` (nav 포함, 모든 정적 링크)
    - `#main` 내 모든 정적 section: `#intro`, `#first`, `#second`, `#third`, `#cta`, `#spacer`
    - `#footer`
    - `<script>` 태그 6개 (lines 444-451)
  - Jinja2 whitespace control 사용: `{%-` / `-%}`로 불필요한 빈 줄 제거
  - `{{ last_updated }}` 변수로 타임스탬프 처리

  **Must NOT do**:
  - 정적 섹션 내용 변경 금지 (intro, first, second, third, cta, footer)
  - CSS/JS 수정 금지
  - HTML5 UP 템플릿 크레딧 제거 금지

  **References**:
  - `/Users/bearj/personal-site/index.html:1-455` — 전체 HTML (정적 섹션 템플릿화 대상)
  - Task 3 분석 결과 (정적/동적 섹션 경계)
  - Jinja2 Template Designer Docs: `https://jinja.palletsprojects.com/en/3.1.x/templates/`

  **Acceptance Criteria**:
  - [ ] `python3 -c "import jinja2; env=jinja2.Environment(loader=jinja2.FileSystemLoader('templates/')); tmpl=env.get_template('base.html'); print('Template loads OK')"` — 템플릿 로드 성공
  - [ ] `python3 -c "..."` 로 렌더링했을 때 DOCTYPE, `<html>`, `<head>`, `<body>`, `</html>` 모두 포함
  - [ ] 기존 정적 섹션 텍스트("저에 대해", "에이전트 헤르", "사용자 정보", "메모리 시스템")가 렌더링 결과에 모두 포함

  **QA Scenarios**:
  ```
  Scenario: 템플릿 로드 및 기본 렌더링
    Tool: Bash
    Preconditions: Task 1, 3 완료
    Steps:
      1. python3 -c "
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates/'), autoescape=False)
    tmpl = env.get_template('base.html')
    html = tmpl.render(generated_at='2026-05-26 07:00 KST', timeline='', cron_jobs='', heatmap='', stats='')
    assert '<!DOCTYPE HTML>' in html
    assert '</html>' in html
    assert '저에 대해' in html
    assert '에이전트 헤르' in html
    assert '사용자 정보' in html
    assert '메모리 시스템' in html
    assert 'Last updated: 2026-05-26 07:00 KST' in html
    assert 'jquery.min.js' in html
    print(f'Generated {len(html)} chars, all sections present')
    "
    Expected Result: 모든 정적 섹션 포함, 6개 JS 태그 포함
    Evidence: .omo/evidence/task-6-template-base.txt
  ```

- [x] 7. 메인 생성기 (generate_site.py)

  **What to do**:
  - `scripts/generate_site.py` 생성:
    - **파이프라인**: 파서(데이터 수집) → 데이터 병합 → 템플릿 렌더링 → 파일 쓰기
    - **CLI 인자** (argparse):
      - `--dry-run`: stdout으로 출력 (파일 쓰지 않음)
      - `--output`: 출력 파일 경로 (기본: index.html)
      - `--memories-dir`: daily_memories 경로 (기본: ~/.hermes/memories/daily_memories/)
      - `--cron-jobs`: cron_jobs.json 경로 (기본: ~/.hermes/cron/jobs.json)
    - **데이터 병합**:
      1. `parse_all_memories()` → list[Activity]
      2. `read_cron_jobs()` → list[CronJob]
      3. **Activity → timeline items 변환** (`flatten_activities()`):
         - 각 Activity의 `completed`, `main_work`, `next_steps` 리스트를 개별 item으로 분해
         - 각 item은 `{section_type, date, title, description, section_index, item_index}` dict
         - 예: Activity(date="2026-05-14", completed=["gateway 재시작", "크론 조회"]) → 
           `{section_type:"completed", date:"2026-05-14", title:"gateway 재시작", description:""}`,
           `{section_type:"completed", date:"2026-05-14", title:"크론 조회", description:""}`
         - section_type 값: `completed`, `main_work`, `main_discussion`, `next_steps`, `in_progress`
         - `raw_sections`에서 섹션 헤더를 section_type으로 매핑 (SECTION_ALIASES 활용)
      4. 통계 계산: total_activities, weekly_count, streak_days, active_cron_count
      5. `SiteData` 생성 (flatten된 items 포함)
      6. `site_data/activities.json`에 저장 (디버깅용)
    - **템플릿 렌더링**:
      1. Jinja2 Environment 설정 (FileSystemLoader, autoescape=False)
      2. timeline HTML: flatten된 items를 timeline.html 템플릿으로 렌더링
      3. cron HTML: CronJob 목록을 cron.html 템플릿으로 렌더링
      4. heatmap + stats HTML 생성
      5. base.html에 모두 주입하여 최종 HTML 생성
    - **Idempotency**:
      - 타임스탬프(`generated_at`)를 제외한 모든 입력이 동일하면 출력도 동일
      - 날짜 정렬 보장 (최신순, stable sort)
    - **오류 처리**:
      - `main()` 전체를 try/except로 감싸고 stderr에 에러 출력 후 exit(1)
      - 각 단계별 실패 시 명확한 로그 메시지
    - **사용자 락 파일**: `/tmp/generate_site.lock` 생성 → 중복 실행 방지

  **Must NOT do**:
  - `index.html` 외 다른 파일 수정 금지 (site_data/activities.json는 예외)
  - LLM/API 호출 금지 (순수 Python 로직만)
  - 웹 서버 모드 금지 (CLI 전용)

  **References**:
  - `scripts/models.py` — SiteData, Activity, CronJob dataclass
  - `scripts/parser.py` — parse_all_memories()
  - `scripts/cron_reader.py` — read_cron_jobs()
  - `templates/base.html` — Jinja2 base template
  - `/Users/bearj/.hermes/scripts/brief_schedule_manager.py` — Hermes cron script 패턴 (shebang, logging, exit code)

  **Acceptance Criteria**:
  - [ ] `python3 scripts/generate_site.py --dry-run` → stdout에 HTML 출력 (파일 변경 없음)
  - [ ] `python3 scripts/generate_site.py` → `index.html` 생성됨
  - [ ] `python3 scripts/generate_site.py` → `site_data/activities.json` 생성됨
  - [ ] 동일 입력에 2회 실행 → 타임스탬프 라인만 다름 (idempotency)

  **QA Scenarios**:
  ```
  Scenario: Dry-run 모드
    Tool: Bash
    Preconditions: Task 1-6, 8 완료
    Steps:
      1. python3 scripts/generate_site.py --dry-run | head -5
      2. git diff --stat index.html  # index.html 변경 없어야 함
    Expected Result: stdout에 HTML 출력, index.html 변경 없음
    Evidence: .omo/evidence/task-7-dryrun.txt

  Scenario: 정상 실행 및 Idempotency
    Tool: Bash
    Preconditions: Task 1-6, 8 완료
    Steps:
      1. python3 scripts/generate_site.py --output /tmp/test_a.html
      2. python3 scripts/generate_site.py --output /tmp/test_b.html
      3. diff /tmp/test_a.html /tmp/test_b.html | grep -v "Last updated" || echo "IDENTICAL (ignoring timestamp)"
    Expected Result: 타임스탬프 라인만 다르고 나머지 동일
    Evidence: .omo/evidence/task-7-idempotent.txt

  Scenario: 사이트 데이터 JSON 생성
    Tool: Bash
    Preconditions: Task 1-6, 8 완료
    Steps:
      1. python3 -c "import json; d=json.load(open('site_data/activities.json')); assert len(d['activities']) > 0; assert len(d['cron_jobs']) > 0; print(f'{len(d[\"activities\"])} activities, {len(d[\"cron_jobs\"])} cron jobs')"
    Expected Result: activities에 13개 항목, cron_jobs에 6개 항목
    Evidence: .omo/evidence/task-7-sitedata.txt

  Scenario: 락 파일 중복 실행 방지
    Tool: Bash
    Preconditions: Task 1-6, 8 완료
    Steps:
      1. python3 -c "
    import subprocess, threading, sys
    def run(): subprocess.run(['python3', 'scripts/generate_site.py', '--output', '/tmp/test_lock.html'], capture_output=True)
    t1 = threading.Thread(target=run)
    t2 = threading.Thread(target=run)
    t1.start(); t2.start()
    t1.join(); t2.join()
    print('Concurrent execution handled')
    "
    Expected Result: 한쪽은 성공, 다른 쪽은 lock 에러로 실패 (둘 다 crash는 금지)
    Evidence: .omo/evidence/task-7-lock.txt
  ```

- [x] 8. 타임라인 + 크론 템플릿 (Phase 1 동적 섹션)

  **What to do**:
  - `templates/timeline.html` 생성:
    - `{% for activity in activities %}` 루프
    - 각 활동을 `<section>`으로 렌더링 (현재 index.html 포맷 유지):
      ```html
      <section>
        <span class="icon solid fa-{icon}"></span>
        <h3>{날짜}</h3>
        <p><strong>{활동명}</strong> — {설명}</p>
      </section>
    ```
    - 섹션 타입별 아이콘 매핑:
      - `completed` → `fa-check-circle`
      - `main_work` → `fa-tasks`
      - `main_discussion` → `fa-comments`
      - `in_progress` → `fa-spinner`
      - `next_steps` → `fa-arrow-right`
    - 최신순 정렬 (날짜 내림차순)
    - `forloop.first`로 첫 항목에 `active` 클래스 추가
    - Jina2 whitespace control로 HTML 포맷팅
  - `templates/cron.html` 생성:
    - `{% for job in cron_jobs %}` 루프
    - 각 job을 `<section>`으로 렌더링:
      ```html
      <section>
        <span class="icon solid fa-{icon}"></span>
        <h3>{job.name}</h3>
        <p>{job.schedule_display}<br/>Job ID: <code>{job.id}</code><br/>상태: <span style="color:{color}">{status_text}</span></p>
      </section>
      ```
    - 상태별 색상: active → `green`, paused → `orange`, error → `red`
    - 상태 텍스트: active → `✅ active`, paused → `⏸️ paused`, error → `❌ error`

  **Must NOT do**:
  - JS로 동적 렌더링 금지 (서버사이드 정적 생성)
  - 외부 아이콘/폰트 추가 금지 (기존 FontAwesome 사용)

  **References**:
  - `index.html:251-413` — 기존 FontAwesome 아이콘 사용 패턴 (24개 `fa-*` 클래스)
  - `index.html:170-230` — 기존 `<section>` 렌더링 포맷 (각 활동 블록 구조)
  - `Task 2:311-320` — `Activity.section_type` enum (completed, main_work 등 값 정의)
  - `Task 4:352-368` — 파서가 출력하는 `Activity` 객체 리스트 구조
  - `Task 5:398-410` — cron_reader가 출력하는 `CronJob` 객체 구조

  **Acceptance Criteria**:
  - [ ] timeline.html → `{% for activity in activities %}` 루프, 섹션 타입별 아이콘, 최신순 정렬 포함
  - [ ] cron.html → `{% for job in cron_jobs %}` 루프, 상태별 색상/텍스트 포함
  - [ ] `python3 -c "from jinja2 import Environment; env=Environment(loader=FileSystemLoader('templates/')); tmpl=env.get_template('timeline.html'); assert 'fa-check-circle' in tmpl.render(activities=[{'section_type':'completed','date':'2026-05-25','title':'test','description':'test'}])"`

  **QA Scenarios**:
  ```
  Scenario: 타임라인 템플릿 렌더링 — 모든 섹션 타입
    Tool: Bash
    Preconditions: Task 6 완료
    Steps:
      1. python3 -c "
    import jinja2, os
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates/'))
    tmpl = env.get_template('timeline.html')
    activities = [
      {'section_type': 'completed', 'date': '2026-05-12', 'title': '테스트', 'description': '완료 항목', 'section_index': 0, 'item_index': 0},
      {'section_type': 'main_work', 'date': '2026-05-13', 'title': '주요 작업', 'description': '작업 설명', 'section_index': 1, 'item_index': 0},
    ]
    html = tmpl.render(activities=activities, cron_jobs=[])
    assert 'fa-check-circle' in html
    assert 'fa-tasks' in html
    assert '2026-05-12' in html
    print('Timeline render OK')
    "
    Expected Result: 모든 섹션 타입이 올바른 아이콘 + 날짜 포맷으로 렌더링
    Evidence: .omo/evidence/task-8-timeline.txt

  Scenario: 크론 템플릿 렌더링 — 모든 상태
    Tool: Bash
    Preconditions: Task 6 완료
    Steps:
      1. python3 -c "
    import jinja2, os
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates/'))
    tmpl = env.get_template('cron.html')
    jobs = [
      {'id': 'job1', 'name': 'Test Job', 'schedule_display': '매일 07:00', 'status': 'active'},
      {'id': 'job2', 'name': 'Paused Job', 'schedule_display': '매주 월', 'status': 'paused'},
    ]
    html = tmpl.render(cron_jobs=jobs)
    assert '✅ active' in html
    assert '⏸️ paused' in html
    print('Cron render OK')
    "
    Expected Result: active/paused 상태가 올바른 색상 + 텍스트로 렌더링
    Evidence: .omo/evidence/task-8-cron.txt

  Scenario: 빈 데이터
    Tool: Bash
    Preconditions: Task 6 완료
    Steps:
      1. python3 -c "
    import jinja2, os
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates/'))
    tmpl = env.get_template('timeline.html')
    html = tmpl.render(activities=[], cron_jobs=[])
    assert len(html) > 0  # 빈 리스트여도 crash 금지
    print('Empty data OK')
    "
    Expected Result: 빈 리스트 입력 시 crash 없이 빈 섹션 렌더링
    Evidence: .omo/evidence/task-8-empty.txt
  ```

- [x] 9. 활동 히트맵 템플릿 (GitHub Contribution 스타일)

  **What to do**:
  - `templates/heatmap.html` 생성:
    - GitHub Contribution 스타일 7xN CSS Grid (일~토 x 주)
    - 데이터: daily_memories 존재 여부 기반 활동량 (0-4 레벨)
    - 레벨 계산: 해당 날짜의 completed 항목 수
      - 0개 = level 0 (회색)
      - 1-2개 = level 1 (연두)
      - 3-4개 = level 2 (초록)
      - 5-7개 = level 3 (진한 초록)
      - 8+개 = level 4 (아주 진한 초록)
    - 레벨 기준 근거 (실제 daily_memory 13개 파일 분석):
      - completed 항목 수 범위: 1-7 (평균 ~3.5)
      - `daily_memories/2026-05-13.md`: 7개 (최대)
      - `daily_memories/2026-05-15.md`: 5개
      - `daily_memories/2026-05-25.md`: 6개
      - `daily_memories/2026-05-12.md`: 2개 (최소)
      - 8+는 예외적 활동 폭주 상황 대비한 상한값
    - CSS Grid 레이아웃:
      ```css
      .heatmap-grid {
        display: grid;
        grid-template-rows: repeat(7, 12px);
        grid-template-columns: repeat(auto-fill, 12px);
        gap: 2px;
      }
      .heatmap-cell { width: 12px; height: 12px; border-radius: 2px; }
      .level-0 { background: #ebedf0; }
      .level-1 { background: #9be9a8; }
      .level-2 { background: #40c463; }
      .level-3 { background: #30a14e; }
      .level-4 { background: #216e39; }
      ```
    - 요일 레이블 (좌측): "월", "(화)", "수", "(목)", "금", "(토)", "일"
    - 월 레이블 (상단): "1월", "2월", ...
    - 현재 날짜 기준 최근 20주 표시
    - 빈 셀(데이터 없는 날짜) → level 0 (회색)
    - 셀에 `title` 속성으로 툴팁: "2026-05-25: 5 activities"
    - 모든 CSS는 `<style>` 블록으로 템플릿에 인라인 포함 (별도 CSS 파일 금지)
    - `{% if has_activities %}` 가드 (데이터 없을 때 섹션 숨김)
  - `generate_site.py`에 히트맵 데이터 생성 로직 추가:
    - `compute_heatmap_data(activities: list[Activity]) -> dict`: 날짜별 레벨 매트릭스

  **Must NOT do**:
  - JavaScript로 히트맵 구현 금지 (순수 CSS Grid)
  - 외부 라이브러리(Chart.js, D3.js) 사용 금지

  **References**:
  - GitHub Contribution Graph — CSS Grid 패턴 (52주 × 7일)
  - Task 2 데이터 모델 (Activity.completed 리스트)
  - `templates/base.html` — `{% block heatmap %}` 플레이스홀더

  **Acceptance Criteria**:
  - [ ] 히트맵 템플릿 → `<div class="heatmap-grid">` 포함, 20주 × 7일 그리드
  - [ ] `level-0` ~ `level-4` 클래스 셀 포함
  - [ ] 툴팁 (`title` 속성) 포함
  - [ ] `python3 -c "from scripts.generate_site import compute_heatmap_data; d=compute_heatmap_data([]); assert len(d) > 0"`

  **QA Scenarios**:
  ```
  Scenario: 히트맵 렌더링
    Tool: Bash
    Preconditions: Task 7 완료
    Steps:
      1. python3 -c "
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates/'))
    tmpl = env.get_template('heatmap.html')
    html = tmpl.render(heatmap_data={'2026-05-25': 3, '2026-05-24': 0, '2026-05-23': 5}, show_heatmap=True)
    assert 'heatmap-grid' in html
    assert 'level-3' in html or 'level-2' in html
    assert '2026-05-25' in html or 'title=' in html
    print('Heatmap render OK')
    "
    Expected Result: CSS Grid 구조, 레벨별 셀, 툴팁 포함
    Evidence: .omo/evidence/task-9-heatmap.txt

  Scenario: 전체 생성에 히트맵 포함
    Tool: Bash
    Preconditions: Task 7 완료
    Steps:
      1. python3 scripts/generate_site.py --dry-run | grep -c 'heatmap-grid'
    Expected Result: 1 이상 (heatmap 섹션 존재)
    Evidence: .omo/evidence/task-9-heatmap-integration.txt
  ```

- [x] 10. 통계 요약 카드

  **What to do**:
  - `templates/stats.html` 생성:
    - 4개 요약 카드 (기존 `.features` CSS 활용):
      ```html
      <div class="features" style="margin-bottom: 2em;">
        <section>
          <span class="icon solid fa-chart-bar"></span>
          <h3>이번 주 활동</h3>
          <p style="font-size: 2em; font-weight: bold; color: #2b2b2b;">{{ weekly_count }}</p>
          <p>이번 주 {{ weekly_count }}개 활동 완료</p>
        </section>
        <section>
          <span class="icon solid fa-fire"></span>
          <h3>연속 활동</h3>
          <p style="font-size: 2em; font-weight: bold; color: #2b2b2b;">{{ streak_days }}일</p>
          <p>최장 {{ max_streak }}일 연속 기록</p>
        </section>
        <section>
          <span class="icon solid fa-clock"></span>
          <h3>총 활동</h3>
          <p style="font-size: 2em; font-weight: bold; color: #2b2b2b;">{{ total_count }}</p>
          <p>{{ total_days }}일간 {{ total_count }}개 활동</p>
        </section>
        <section>
          <span class="icon solid fa-cog"></span>
          <h3>자동화</h3>
          <p style="font-size: 2em; font-weight: bold; color: #2b2b2b;">{{ active_cron_count }}</p>
          <p>{{ active_cron_count }}개 크론 활성</p>
        </section>
      </div>
    ```
  - `generate_site.py`에 통계 계산 로직 추가:
    - `weekly_count`: 최근 7일간 completed 항목 총합
    - `streak_days`: 오늘부터 거슬러 올라가 연속으로 daily_memory가 있는 일수
    - `max_streak`: 전체 기간 중 최장 연속 일수
    - `total_count`: 전체 completed 항목 총합
    - `total_days`: daily_memory가 존재하는 총 일수
    - `active_cron_count`: enabled 상태인 크론 수
  - `{% if show_stats %}` 가드 (데이터 없을 때 섹션 숨김)

  **Must NOT do**:
  - 숫자에 콤마/포맷팅 과도하게 금지 (한국어 + 숫자만)

  **References**:
  - `/Users/bearj/personal-site/index.html:136-151` — `.features` / `.feature` CSS 클래스
  - Task 7의 stats 계산 (weekly_count, streak_days 등)

  **Acceptance Criteria**:
  - [ ] 통계 템플릿 → 4개 `<section>` 카드 포함
  - [ ] 각 카드에 숫자 표시 (`<p style="font-size: 2em">`)
  - [ ] `python3 scripts/generate_site.py --dry-run | grep -c "이번 주 활동"` → 1

  **QA Scenarios**:
  ```
  Scenario: 통계 카드 렌더링
    Tool: Bash
    Preconditions: Task 7 완료
    Steps:
      1. python3 -c "
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates/'))
    tmpl = env.get_template('stats.html')
    html = tmpl.render(weekly_count=12, streak_days=5, max_streak=13, total_count=47, total_days=13, active_cron_count=6, show_stats=True)
    assert '12' in html and '5' in html and '47' in html and '6' in html
    assert '이번 주 활동' in html
    assert '연속 활동' in html
    assert '총 활동' in html
    assert '자동화' in html
    print('Stats render OK')
    "
    Expected Result: 4개 카드, 각각 숫자와 레이블 표시
    Evidence: .omo/evidence/task-10-stats.txt
  ```

- [x] 11. 활동 카테고리 분석

  **What to do**:
  - `templates/categories.html` (또는 `stats.html`에 통합) 생성:
    - daily_memory 섹션 헤더 기반 활동 유형 분류 막대그래프
    - CSS-only 가로 막대:
      ```html
      <div class="category-bar">
        <div class="category-label">개발</div>
        <div class="category-track">
          <div class="category-fill" style="width: 45%;"></div>
        </div>
        <div class="category-pct">45%</div>
      </div>
    ```
    - 카테고리 분류 로직:
      - `completed`의 항목 키워드 기반 분류
      - 키워드 → 카테고리 매핑:
        - "개발/구현": 구현, 개발, 코드, 스크립트, API, 작성, 구축
        - "리서치": 분석, 조사, 리서치, 탐구, 비교, 테스트
        - "문서화": 보고서, 문서, 정리, 기록, 개요
        - "자동화": 크론, 자동화, 파이프라인, 배포, cron
        - "기타": 위 매핑에 없는 항목
    - `generate_site.py`에 카테고리 분석 로직 추가:
      - 키워드 기반 분류 + 퍼센티지 계산

  **Must NOT do**:
  - JavaScript로 애니메이션 구현 금지 (순수 CSS)
  - chart 라이브러리 금지

  **References**:
  - `daily_memories/*.md:## 완료` — 13개 파일의 completed 항목 전체 리스트
  - `daily_memories/2026-05-14.md:4-6` — 키워드 샘플: "설치", "조회", "조사"
  - `daily_memories/2026-05-25.md:4-20` — 키워드 샘플: "작성", "구축", "검색", "분석"
  - `daily_memories/2026-05-13.md:4-10` — 키워드 샘플: "생성", "설정", "테스트"
  - `Task 4:352-368` — 파서가 출력하는 `Activity.section_items` 구조

  **Acceptance Criteria**:
  - [ ] categories.html → 카테고리별 가로 막대 포함, CSS-only 구현
  - [ ] 카테고리 분류 로직 → 13개 daily_memory completed 항목 전부 분류 가능
  - [ ] `python3 -c "from scripts.generate_site import compute_categories; c=compute_categories([{'section_type':'completed','title':'API 작성 완료'}]); assert '개발/구현' in c and c['개발/구현'] > 0"`
  - [ ] 전체 퍼센티지 합계 100% (반올림 오차 허용)

  **QA Scenarios**:
  ```
  Scenario: 카테고리 분석 — 실제 데이터 기반
    Tool: Bash
    Preconditions: Task 7 완료 (통합 검증은 Task 14에서)
    Steps:
      1. python3 -c "
    from scripts.generate_site import compute_categories
    categories = compute_categories(sample_activities)
    total = sum(categories.values())
    assert abs(total - 100) < 2  # 반올림 허용
    assert '개발/구현' in categories or '기타' in categories
    for k, v in categories.items():
      assert 0 <= v <= 100
    print(f'Categories OK: {categories}')
    "
    Expected Result: 전체 completed 항목이 카테고리 중 하나로 분류, 합계 100%
    Evidence: .omo/evidence/task-11-categories.txt

  Scenario: 빈 입력 처리
    Tool: Bash
    Preconditions: Task 7 완료 (통합 검증은 Task 14에서)
    Steps:
      1. python3 -c "
    from scripts.generate_site import compute_categories
    categories = compute_categories([])
    assert categories == {} or sum(categories.values()) == 0
    print('Empty categories OK')
    "
    Expected Result: 빈 리스트 → 빈 dict 또는 0, crash 금지
    Evidence: .omo/evidence/task-11-empty.txt
  ```

- [x] 12. 파서 단위테스트 (TDD)

  **What to do**:
  - `tests/conftest.py`: 테스트 fixture (샘플 daily_memory 데이터)
  - `tests/test_parser.py`:
    - `test_parse_standard_file`: 표준 포맷 (2026-05-25.md 스타일) 파싱 검증
    - `test_parse_with_section_variants`: `다음 할일`/`다음 할 일` 양쪽 처리 검증
    - `test_parse_with_unusual_sections`: `보관 위치`, `완성된 가이드`, `모델 변경` 섹션 처리
    - `test_parse_missing_file`: 없는 파일 → None 반환
    - `test_parse_empty_file`: 빈 파일 → None 반환
    - `test_memory_to_html_bold`: `**text**` → `<strong>text</strong>`
    - `test_memory_to_html_list`: `- item` → `<li>item</li>`
    - `test_memory_to_html_nested_list`: 인덴트된 서브아이템 처리
    - `test_memory_to_html_mixed`: 복합 포맷 처리
    - `test_parse_all_memories_count`: 13개 기존 파일 전부 파싱 → 13개 Activity
    - `test_date_extraction_from_filename`: 파일명에서 날짜 추출 (헤더 없을 때)
  - `tests/test_cron_reader.py`:
    - `test_read_enabled_jobs`: enabled만 필터링
    - `test_cron_to_display_known`: 알려진 스케줄 변환
    - `test_cron_to_display_fallback`: 알 수 없는 스케줄 포괄 처리
    - `test_read_missing_file`: 없는 파일 → 빈 리스트
    - `test_read_malformed_json`: 깨진 JSON → 빈 리스트
  - 테스트 데이터: 실제 파일을 복사하지 않고 `tmp_path` fixture로 인메모리 테스트
  - `pytest` 마커: `@pytest.mark.slow` (실제 daily_memories 읽는 테스트)

  **Must NOT do**:
  - 실제 Hermes daily_memories 파일 수정 금지
  - 네트워크 의존성 금지

  **References**:
  - `scripts/parser.py` — 테스트 대상
  - `scripts/cron_reader.py` — 테스트 대상
  - `/Users/bearj/.hermes/memories/daily_memories/2026-05-25.md` — 표준 샘플
  - `/Users/bearj/.hermes/memories/daily_memories/2026-05-16.md` — 변종 샘플 (`보관 위치`)

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/test_parser.py -v` → 10개 이상 테스트, 모두 PASS
  - [ ] `python3 -m pytest tests/test_cron_reader.py -v` → 5개 이상 테스트, 모두 PASS
  - [ ] 테스트 커버리지: SECTION_ALIASES 모든 변종 커버

  **QA Scenarios**:
  ```
  Scenario: 파서 단위테스트 실행
    Tool: Bash
    Preconditions: Task 1, 4, 5 완료
    Steps:
      1. python3 -m pytest tests/test_parser.py tests/test_cron_reader.py -v
    Expected Result: 모든 테스트 PASS, 실패 0
    Evidence: .omo/evidence/task-12-pytest.txt
  ```

- [x] 13. 생성기 + 템플릿 테스트

  **What to do**:
  - `tests/test_generator.py`:
    - `test_generated_html_has_doctype`: `<!DOCTYPE HTML>` 포함
    - `test_generated_html_has_html_close`: `</html>` 포함
    - `test_generated_html_has_all_static_sections`: "저에 대해", "에이전트 헤르", "사용자 정보", "메모리 시스템" 모두 포함
    - `test_generated_html_has_scripts`: 6개 JS script 태그 모두 포함
    - `test_generated_html_has_timeline`: `id="fourth"` 섹션 포함
    - `test_generated_html_has_cron`: `id="fifth"` 섹션 포함
    - `test_generated_html_has_timestamp`: `Last updated:` 주석 포함
    - `test_generated_html_has_heatmap`: `heatmap-grid` 클래스 포함 (Task 9 완료 시)
    - `test_generated_html_has_stats`: 통계 카드 포함 (Task 10 완료 시)
    - `test_generated_html_korean_encoding`: UTF-8, 한글 깨짐 없음
    - `test_generated_html_valid_structure`: `html.parser`로 파싱 가능 (well-formed)
  - `tests/test_idempotency.py`:
    - `test_idempotency_except_timestamp`: 2회 생성 → 타임스탬프 라인만 차이 확인
    - `test_idempotency_stable_sort`: 동일 입력 → 동일 순서
  - `tests/test_stats.py`:
    - `test_weekly_count`: 최근 7일 completed 항목 수 계산
    - `test_streak_days`: 연속 활동일 계산
    - `test_max_streak`: 최장 연속 기록 계산

  **Must NOT do**:
  - 실제 index.html 덮어쓰기 금지 (테스트는 --dry-run 또는 /tmp 사용)

  **References**:
  - `scripts/generate_site.py` — 테스트 대상
  - `templates/base.html` — 테스트 대상
  - `templates/timeline.html`, `templates/cron.html` — 테스트 대상

  **Acceptance Criteria**:
  - [ ] 모든 생성기 테스트 PASS (11개 이상)
  - [ ] Idempotency 테스트: 타임스탬프 제외 동일 증명
  - [ ] HTML 파서로 파싱 가능 (well-formed 검증)

  **QA Scenarios**:
  ```
  Scenario: 생성기 + 템플릿 테스트
    Tool: Bash
    Preconditions: Task 1-10 완료, pytest 설치
    Steps:
      1. python3 -m pytest tests/test_generator.py tests/test_idempotency.py tests/test_stats.py -v
    Expected Result: 모든 테스트 PASS
    Evidence: .omo/evidence/task-13-gen-tests.txt
  ```

- [x] 14. 통합 테스트

  **What to do**:
  - `tests/test_integration.py`:
    - `test_end_to_end_generation`: 실제 환경에서 `generate_site.py` 실행 → 파일 생성 확인
      ```python
      import subprocess
      result = subprocess.run(['python3', 'scripts/generate_site.py', '--output', '/tmp/test_site.html'], capture_output=True, text=True)
      assert result.returncode == 0
      assert os.path.exists('/tmp/test_site.html')
      ```
    - `test_generated_html_diff`: 기존 git HEAD의 index.html과 구조 비교
      - 새 생성기 출력이 기존과 동일한 정적 섹션 포함하는지 확인
      - 동적 섹션 내용은 다를 수 있음 (허용)
    - `test_cron_section_count`: 생성된 HTML의 cron section 개수 = enabled job 수
      ```python
      from html.parser import HTMLParser
      # cron 섹션 내 <section> 태그 카운트
      ```
    - `test_heatmap_no_crash`: 히트맵 데이터가 비어있어도 crash 없이 HTML 생성
    - `test_empty_memories_dir`: 빈 memories 디렉토리 → 기본 HTML 생성 (timeline 섹션은 비어있음)
    - `test_lock_file_cleanup`: 정상 종료 후 lock 파일 삭제 확인
    - `test_git_integration_simulation`: git add → commit → push 시뮬레이션 (--dry-run으로 git diff만 확인)

  **Must NOT do**:
  - 실제 git push 실행 금지 (테스트에서는 --dry-run만)
  - 실제 Hermes cron 수정 금지

  **References**:
  - `scripts/generate_site.py` — CLI 인터페이스
  - `/Users/bearj/personal-site/.git` — Git 저장소 (diff 참조용)

  **Acceptance Criteria**:
  - [ ] E2E 테스트: generate → 파일 생성 → 구조 검증 → 모두 PASS
  - [ ] Cron 섹션 카운트 = 실제 enabled job 수와 일치
  - [ ] 빈 데이터 → crash 없이 기본 HTML 생성

  **QA Scenarios**:
  ```
  Scenario: E2E 통합 테스트
    Tool: Bash
    Preconditions: Task 1-13 완료
    Steps:
      1. python3 -m pytest tests/test_integration.py -v --timeout=30
    Expected Result: 모든 통합 테스트 PASS (30초 이내)
    Evidence: .omo/evidence/task-14-integration.txt
  ```

- [x] 15. Hermes cron prompt 교체 및 E2E 검증

  **What to do**:
  1. **cron prompt 변경** (ID: 15e77e7ffb49):
     - 기존: ~2000자 LLM prompt (HTML 직접 수정)
     - 변경: 아래 내용으로 교체
       ```
       [IMPORTANT: Cron job — run the site generator script.]

       Run the following commands in order:

       1. cd /Users/bearj/personal-site
       2. python3 scripts/generate_site.py
          If this fails, capture stderr and abort with error message.
       3. git add -A
       4. git commit -m "Update personal site $(TZ=Asia/Seoul date +%Y-%m-%d)"
       5. git pull --rebase origin main (to avoid push conflicts)
       6. git push origin main

       After completion, send a Telegram message to 'telegram:SC Jeo' with:
       "✅ Personal site updated at $(TZ=Asia/Seoul date +%Y-%m-%d %H:%M KST)
       📋 Timeline: [count from git diff --stat]
       🔗 https://github.com/justfly32/post1"
       ```
     - 핵심: `no_agent: false` 유지 (Hermes agent가 명령 실행 + Telegram 발송)
     - LLM이 HTML을 편집하지 않고 **스크립트만 실행**하도록 변경
  2. **이전 cron 비활성화**:
     - 기존 LLM cron prompt 저장 (백업): `cron/jobs.json.bak`
     - 새 prompt로 교체 (hermes cron update 명령어 사용)
  3. **수동 E2E 검증**:
     - 모든 파일 git add 완료
     - `python3 scripts/generate_site.py` 수동 실행
     - 생성된 `index.html`을 브라우저에서 시각 확인
     - `git diff --stat`로 변경 사항 검토
     - `git push` 정상 동작 확인
  4. **에러 처리**:
     - Python 스크립트 실패 → Telegram에 에러 메시지 전송
     - git push 실패 → `git pull --rebase` 재시도 후 재push

  **Must NOT do**:
  - 다른 cron job 수정 금지
  - Hermes 설정 파일 직접 수정 금지 (hermes CLI 통해서만 변경)
  - 기존 cron prompt 백업 없이 삭제 금지

  **References**:
  - `/Users/bearj/.hermes/cron/jobs.json` — Job ID `15e77e7ffb49` prompt 필드
  - `/Users/bearj/.hermes/scripts/update_personal_site.sh` — 기존 접근법 (참고용)
  - `python3 scripts/generate_site.py` — 실행할 스크립트
  - `git remote -v` → `github.com:justfly32/post1.git`

  **Acceptance Criteria**:
  - [ ] `hermes cron list | grep "Update personal site"` → 새 prompt 확인
  - [ ] `python3 scripts/generate_site.py` → exit 0
  - [ ] `git diff --stat HEAD` → index.html 변경 감지
  - [ ] `git push origin main` → 성공 (또는 "Everything up-to-date")

  **QA Scenarios**:
  ```
  Scenario: 수동 E2E 실행
    Tool: Bash
    Preconditions: Tasks 1-14 완료, git clean 상태
    Steps:
      1. python3 scripts/generate_site.py --dry-run | head -20
      2. python3 scripts/generate_site.py
      3. git diff --stat index.html
      4. python3 -m pytest tests/ -v
    Expected Result: 스크립트 정상 실행, git diff 변경 감지, 모든 테스트 PASS
    Evidence: .omo/evidence/task-15-e2e.txt
  ```

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE.

- [x] F1. **Plan Compliance Audit** — `oracle`
  For each "Must Have" (13개 기존 파일 파싱, 정적 섹션 보존, 히트맵 CSS Grid, enabled cron only, git push 실패 처리): verify implementation exists (read file, run script, check output). For each "Must NOT Have" (kanban 제외, 프레임워크 금지, JS/CSS 수정 금지 등): search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.omo/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [15/15] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run: `python3 -m pytest tests/ -v` (all tests pass). Review all Python files for: bare `except:`, `sys.exit(1)` without error message, hardcoded paths that should be configurable, missing docstrings, import *. Check Jinja2 templates for: hardcoded Korean text that should be template variables, whitespace issues, broken HTML structure. Check `generate_site.py` for: lock file not released on error, missing `__main__` guard.
  Output: `Tests [N/N] | Python [PASS/ISSUES] | Templates [PASS/ISSUES] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill if browser available)
  Start from clean state (git stash). Execute every QA scenario from every task — follow exact steps, capture evidence. Run full generation pipeline: `python3 scripts/generate_site.py`. Open `index.html` in browser (if possible) to verify: all 7 sections visible, heatmap grid renders, stats cards show numbers, Korean text correct. Test edge cases: `--memories-dir /nonexistent`, `--cron-jobs /nonexistent`, concurrent run (lock file).
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance: no HTML files besides index.html modified, no assets/ files touched, no JS/CSS refactoring. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [15/15 compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **1-5**: `chore: project scaffolding and data models`
- **6-8**: `feat: Jinja2 templates and core generator`
- **9-11**: `feat: activity heatmap, stats, and category analysis`
- **12-14**: `test: parser, generator, and integration tests`
- **15**: `chore: update Hermes cron prompt for Python generator`

## Success Criteria

### Verification Commands
```bash
python3 scripts/generate_site.py --dry-run          # stdout 출력 확인
python3 scripts/generate_site.py                     # index.html 생성
python3 -m pytest tests/ -v                          # 모든 테스트 통과
diff <(python3 scripts/generate_site.py --output /tmp/a.html && cat /tmp/a.html) <(python3 scripts/generate_site.py --output /tmp/b.html && cat /tmp/b.html) | grep -v "Last updated" | wc -l  # 0이어야 함
python3 -c "from html.parser import HTMLParser; p=HTMLParser(); p.feed(open('index.html').read()); print('HTML VALID')"
file index.html | grep -i utf                        # UTF-8 확인
```

### Final Checklist
- [ ] 모든 "Must Have" 구현 완료
- [ ] 모든 "Must NOT Have" 침범 없음
- [ ] `pytest tests/ -v` → all pass
- [ ] 생성된 HTML 브라우저 정상 렌더링
- [ ] 히트맵 7xN CSS Grid 표시
- [ ] 통계 카드 표시
- [ ] cron job 정상 실행 (매일 07:00 KST)
- [ ] Telegram 알림 정상 전송
