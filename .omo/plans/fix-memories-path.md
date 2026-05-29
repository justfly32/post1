# Fix: daily_memories 기본 경로 수정

## TL;DR
> **Quick Summary**: generator가 Hermes 실제 데이터 저장 경로를 찾도록 `--memories-dir` 기본값 변경
>
> **Deliverables**:
> - `scripts/generate_site.py`: 기본 경로 1줄 수정
>
> **Estimated Effort**: Quick (< 1분)

## Context
Hermes는 daily_memory 파일을 `~/.hermes/memories/daily_memories/`에 저장하는데, generator 기본 경로가 `daily_memories/`(레포 루트)라서 13개 파일을 못 찾고 있음. 크론이 그대로 돌아가면 빈 페이지 생성됨.

## Work Objectives
### Core Objective
`scripts/generate_site.py`의 `--memories-dir` 기본값을 Hermes 실제 경로로 변경

### Must Have
- [ ] `main()` 함수에서 `default="daily_memories"` → `default=str(Path.home() / ".hermes" / "memories" / "daily_memories")`

### Must NOT Have
- `--cron-file` 기본값은 이미 올바르므로 수정 금지

## TODOs

- [x] 1. `scripts/generate_site.py` 기본 경로 수정

  **What to do**:
  - 314번째 줄 `default="daily_memories"` → `default=str(Path.home() / ".hermes" / "memories" / "daily_memories")`
  - `Path`가 이미 import 되어 있으므로 추가 import 불필요
  - 변경 후 `python3 scripts/generate_site.py --dry-run` 실행하여 활동 데이터가 제대로 불러와지는지 확인

  **Recommended Agent Profile**:
  - Category: `quick`

  **Acceptance Criteria**:
  - [ ] `python3 scripts/generate_site.py --dry-run 2>&1 | head -5` 실행 시 Warning 없이 활동 데이터 출력됨
  - [ ] 출력에 `activities` count가 0이 아닌 값으로 표시됨

  **Evidence**:
  - [ ] 터미널 출력 캡처: 활동 데이터가 표시되는지 확인

  **Commit**: YES
  - Message: `fix: update default memories dir to Hermes path`
  - Files: `scripts/generate_site.py`

## Commit Strategy
- **1**: `fix: update default memories dir to Hermes path` - `scripts/generate_site.py`
