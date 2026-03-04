# Implementation Plan: Phase 4 — CLI Polish, Ruff, Caching, and Release

Created: 2026-03-04T00:00:00Z
Status: pending

## Requirements

Ship a polished, production-ready v0.1.0:

1. **Ruff linting** — add `ruff` to dev dependencies, configure rules, fix all violations. Ensures consistent code style and catches common errors going forward.
2. **CLI completeness** — add `chromax chat` interactive session command (multi-turn, persisted via `--session`); add `typer.testing.CliRunner` unit tests for all CLI commands.
3. **Response caching** — in-memory TTL cache (1 hour) for LLM responses keyed by `(question, repo)` hash. Avoids re-querying the LLM for identical questions within the same process.
4. **README + docs** — write `README.md` with install instructions, usage examples, and a feature overview.
5. **Release prep** — add `LICENSE` (MIT) and `CONTRIBUTING.md`; clean up the dead `src/chromax/main.py` leftover.

---

## Implementation Phases

### Phase 4A: Ruff Linting
- [ ] Add `ruff>=0.4` to `[project.optional-dependencies] dev` in `pyproject.toml`
- [ ] Add `[tool.ruff]` config section: `line-length = 120`, select `["E", "F", "W", "I"]`, ignore `["E501"]`
- [ ] Add `[tool.ruff.lint.isort]` section with `known-first-party = ["chromax"]`
- [ ] Run `python -m ruff check src/ tests/` to identify violations
- [ ] Fix all violations (expected: import ordering, unused imports)
- [ ] Add ruff check to `pyproject.toml` `[tool.pytest.ini_options]` or document in CONTRIBUTING

### Phase 4B: CLI Completeness + Tests
- [ ] Add `chromax chat --repo <owner/repo>` command to `cli.py` — wraps `ask_with_session` with an auto-generated session ID (UUID) or user-supplied `--session`; runs an interactive loop with `typer.prompt`
- [ ] Write `tests/phase4/test_cli.py` using `typer.testing.CliRunner`:
  - `test_help_shows_commands` — `chromax --help` exits 0, lists index/ask/status/chat
  - `test_status_unindexed_repo` — `chromax status --repo owner/nonexistent` exits 0, prints "not indexed"
  - `test_index_missing_repo_arg` — `chromax index` without `--repo` exits non-zero
  - `test_ask_missing_repo_arg` — `chromax ask "q"` without `--repo` exits non-zero
- [ ] Remove dead `src/chromax/main.py` (superseded by `cli.py` + `__main__.py`)

### Phase 4C: Response Caching
- [ ] Create `src/chromax/cache.py` — `ResponseCache` class:
  - `get(question, repo) -> str | None`
  - `set(question, repo, answer) -> None`
  - TTL: 3600 seconds (1 hour)
  - Key: `sha256(f"{repo}:{question.strip().lower()}")[:16]`
- [ ] Wire cache into `supervisor.route()` — check cache before calling specialist agent; store response after
- [ ] Write `tests/phase4/test_caching.py`:
  - `test_cache_hit_returns_same_answer` — second call returns identical string
  - `test_cache_miss_returns_none` — fresh cache returns None for unknown key
  - `test_cache_expires_after_ttl` — monkeypatch `time.time`; expired entry returns None
  - `test_cache_does_not_affect_session_calls` — `ask_with_session` bypasses cache (multi-turn must see live responses)

### Phase 4D: README + Release Prep
- [ ] Write `README.md`:
  - Project description and use-case
  - Prerequisites (`GITHUB_TOKEN`, `GROQ_API_KEY`)
  - Install: `pip install -e .` or `pip install chromax`
  - Quick-start: `chromax index --repo psf/requests` → `chromax ask "..." --repo psf/requests`
  - Command reference table
  - Architecture diagram (ASCII)
  - Contributing section pointing to `CONTRIBUTING.md`
- [ ] Write `CONTRIBUTING.md` — dev setup, `pip install -e ".[dev]"`, running tests, ruff, commit conventions
- [ ] Add `LICENSE` (MIT, 2026, user's name)
- [ ] Verify `pip install -e .` installs `chromax` entry point correctly on a clean path

---

## Dependencies

- `ruff>=0.4` (dev) — linter
- `typer.testing.CliRunner` — already available via installed `typer`
- `src/chromax/cache.py` — new file, no external deps (stdlib `hashlib`, `time`)

---

## Risks

- LOW: Ruff may flag style issues in test files — fixable
- LOW: `chat` interactive loop requires `sys.stdin` to be a TTY; CliRunner tests should mock `typer.prompt`
- LOW: Response cache is in-process only (lost on restart) — acceptable for v0.1.0
- LOW: `main.py` deletion — confirm it's not imported anywhere before removing

---

## TDD Recommended: Yes
**Reason:** Phase 4B (CLI tests) and 4C (cache tests) both have clear input/output contracts that are easy to specify up front. Writing the CliRunner tests before adding the `chat` command and cache ensures the API surface is right before implementation.

---

## Test Strategy

### Detected Code Types

| Phase | Files | Code Type | Primary Tests | Secondary Tests |
|-------|-------|-----------|---------------|-----------------|
| 4A | `pyproject.toml`, `src/` | Config / Utility | Unit (ruff check) | - |
| 4B | `src/chromax/cli.py` | CLI Entry Point | Unit (CliRunner) | - |
| 4C | `src/chromax/cache.py` | Utility | Unit | - |
| 4D | `README.md`, `LICENSE` | Documentation | Manual | - |

### Test Execution Plan

1. Unit tests (CliRunner — fast, no network)
2. Unit tests (cache — no network, monkeypatched time)
3. Ruff check (`python -m ruff check src/ tests/`)
