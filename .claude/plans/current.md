# Implementation Plan: `chromax arch` — Architecture Expert CLI Subcommand

Created: 2026-03-08T00:00:00Z
Updated: 2026-03-08T01:00:00Z
Status: completed

## Requirements

Add a new `chromax arch` subcommand to the chromax CLI that acts as a codebase-aware architecture expert.

**Usage modes:**
```bash
chromax arch --repo owner/name                        # Full architectural overview
chromax arch "how should I structure auth?" --repo owner/name  # Targeted Q&A
chromax arch --repo owner/name --session abc123       # Multi-turn arch conversation
```

**Behaviour:**
- When called with no QUESTION → produce a structured architectural overview (tech stack, module map, data flow, patterns, weak spots)
- When called with a QUESTION → answer with full architectural reasoning (trade-offs, alternatives, recommendation)
- When called with `--session` → use session-aware full-toolset agent for multi-turn context (same pattern as `chromax ask --session`)
- Always uses a senior architect persona with access to all four tools (search, file content, README, repo structure)

**Does NOT change:**
- Existing `ask`, `index`, `chat`, `status` commands
- Supervisor routing (arch is a standalone command, not a routed type)
- Cache behaviour (arch answers are NOT cached — architectural context is query-specific and benefits from fresh tool calls)

---

## Implementation Phases

### Phase 1: Create `src/chromax/agents/arch.py`

New specialist agent dedicated to architecture questions.

- [ ] Define `ARCH_SYSTEM_PROMPT` — senior solutions architect persona:
  - 15+ years experience across distributed systems, monoliths, microservices
  - Prioritise trade-off analysis over opinions
  - Name patterns explicitly (hexagonal, CQRS, event sourcing, layered, etc.)
  - Call out coupling, single points of failure, and scaling concerns
  - Reference specific file paths and line ranges from the codebase
  - Standard prompt-injection defence clause (same pattern as other agents)
  - **Explicit scope boundary vs StructureAgent**: system prompt must instruct the agent NOT to merely list files and directories (that is the StructureAgent's job). The arch agent must always go one level deeper — explain *why* things are structured the way they are, what design pattern it represents, and what the trade-offs are. Raw structural facts are only useful as evidence for a higher-level architectural point.
- [ ] Define `OVERVIEW_PROMPT` — the default question used when no QUESTION arg is supplied:
  - Asks for: tech stack table, module map, data flow narrative, key design patterns, notable decisions, architectural weak spots, suggested questions
- [ ] Define `ARCH_TOOLS` — uses all four tools: `tool_search_codebase`, `tool_get_readme`, `tool_get_repo_structure`, `tool_get_file_content`
- [ ] Create `ask_arch = make_ask(ARCH_SYSTEM_PROMPT, ARCH_TOOLS)` using existing factory
- [ ] Export `ask_arch` from `src/chromax/agents/__init__.py`

### Phase 1b: Update `src/chromax/agents/supervisor.py` — Add "architecture" routing

So that `chromax ask "what's the architecture?" --repo ...` also reaches the ArchitectAgent, not the AnalyzerAgent:

- [ ] Add `"architecture"` as a valid return value in `classify_query()` — update the classification prompt to include it alongside the existing 4 types, with guidance like: "architecture: questions about high-level design patterns, system structure, component relationships, trade-offs, or asking for an overview of how the system is designed"
- [ ] Add `"architecture": ask_arch` to the `specialist` routing dict in `route()`
- [ ] Fallback still `"analyzer"` on error — no change needed there
- [ ] Add test in `tests/phase5/test_arch_agent.py`: `test_supervisor_routes_arch_question` — assert that `classify_query("what design patterns does this codebase use?")` returns `"architecture"` (mocked LLM response)

### Phase 2: Update `src/chromax/cli.py`

Add the `arch` Typer command following existing command conventions.

- [ ] Add `from chromax.agents import ask_arch` import (alongside existing agent imports)
- [ ] Define `@app.command()` for `arch`:
  - `question: Optional[str] = typer.Argument(None, help="Architecture question (omit for full overview)")`
  - `repo: str = typer.Option(..., "--repo", "-r", help="GitHub repo (owner/name)")`
  - `session: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID for multi-turn")`
- [ ] Validate repo format using existing `_validate_repo()` helper
- [ ] Validate session ID using existing session regex if `--session` provided
- [ ] Routing logic:
  - If `session` provided → use `ask_with_session(effective_question, repo, session)` (same as `ask` command session path)
  - If no session → use `ask_arch(effective_question, repo)` directly
  - `effective_question = question or OVERVIEW_PROMPT` (from arch.py)
- [ ] Output: `console.print(Markdown(answer))` — same as `ask` command
- [ ] Error handling: `err_console.print` + `raise typer.Exit(code=1)` on failure — same pattern as existing commands

### Phase 3: Tests

- [ ] Create `tests/phase5/` directory with `__init__.py`
- [ ] Create `tests/phase5/test_arch_agent.py`:
  - `test_ask_arch_returns_string` — call `ask_arch` with a simple arch question against a known indexed repo, assert returns non-empty string
  - `test_ask_arch_overview_prompt_not_empty` — assert `OVERVIEW_PROMPT` is a non-empty string (guards against accidental blank default)
  - `test_arch_system_prompt_contains_injection_defence` — assert `ARCH_SYSTEM_PROMPT` contains "untrusted" or "data only" (same defence clause as other agents)
- [ ] Create `tests/phase5/test_arch_cli.py` using `typer.testing.CliRunner`:
  - `test_arch_missing_repo_arg` — `chromax arch "question"` without `--repo` exits non-zero
  - `test_arch_invalid_repo_format` — `chromax arch --repo notaslash` exits 1 with error message
  - `test_arch_invalid_session_id` — `chromax arch --repo owner/name --session "../../evil"` exits 1
  - `test_arch_help_shows_command` — `chromax --help` output contains "arch"

---

## Dependencies

- No new packages required — uses existing LangGraph, LangChain, Groq, Typer stack
- `make_ask()` factory in `_base.py` handles agent compilation
- All four tools (`tool_search_codebase`, `tool_get_readme`, `tool_get_repo_structure`, `tool_get_file_content`) already exist in `tools/`
- `ask_with_session` already handles the `--session` path; `arch` just calls it the same way `ask` does

---

## Risks

- MEDIUM: LLM may not follow the structured overview format reliably — mitigate with explicit section headers in `OVERVIEW_PROMPT` (tell it to use `##` headers for each section)
- LOW: `ask_arch` uses all four tools — recursion_limit=25 is shared with other agents; verify it's sufficient for a full overview call (typically 6-10 tool calls)
- LOW: `OVERVIEW_PROMPT` injected as the question will be cached by `ResponseCache` in the session path; this is acceptable behaviour (overview of the same repo in the same session can be cached)
- LOW: `agents/__init__.py` must export `ask_arch` — easy to miss, covered by import test
- LOW: Adding `"architecture"` to the supervisor's classification prompt may shift borderline questions away from `"analyzer"` — acceptable since ArchitectAgent has a superset of AnalyzerAgent's tools; verify the fallback still works
- LOW: Future extensibility — `chromax security` and `chromax deps` could follow the same pattern if they need a no-question overview mode, but should NOT be added until there's a concrete need. The pattern established here (standalone command + supervisor routing entry) is the template to follow.

---

## TDD Recommended: Yes

**Reason:** New CLI command with clear input/output contracts. CliRunner tests can be written first to define the expected argument surface (`--repo` required, invalid session rejected, etc.) before the command is wired up. Agent unit tests define the prompt contract before writing the system prompt.

---

## Test Strategy

### Detected Code Types

| Phase | Files | Code Type | Primary Tests | Secondary Tests |
|-------|-------|-----------|---------------|-----------------|
| 1 | `src/chromax/agents/arch.py` | Utility / Agent | Unit | - |
| 2 | `src/chromax/cli.py` | CLI Entry Point | Unit (CliRunner) | - |
| 3 | `tests/phase5/` | Test files | - | - |

### Test Execution Plan
1. Unit tests — CliRunner (fast, no network, no LLM)
2. Unit tests — agent prompt assertions (no network)
3. (Manual / integration) — live call against a real indexed repo to verify output quality
