# Contributing

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/chromax-codebase-onboarding
cd chromax-codebase-onboarding

python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows
# or
source .venv/bin/activate        # macOS / Linux

pip install -e ".[dev]"

cp .env.example .env
# Fill in GITHUB_TOKEN and GROQ_API_KEY
```

## Running tests

```bash
pytest                                        # all tests
pytest tests/phase4/                          # specific phase
pytest --cov=chromax --cov-report=term-missing  # with coverage
```

Some tests make real LLM calls via Groq. If you hit the daily token limit (100K TPD on the free tier), those tests will skip automatically.

## Linting

```bash
ruff check .          # check
ruff check --fix .    # auto-fix
```

All PRs must pass `ruff check` with zero violations.

## Project structure

| Layer | Location | Responsibility |
|-------|----------|----------------|
| CLI | `src/chromax/cli.py` | Entry point, argument parsing |
| Supervisor | `src/chromax/agents/supervisor.py` | Query classification + routing |
| Specialists | `src/chromax/agents/{structure,analyzer,navigation,search}.py` | Domain-specific agents |
| Indexer | `src/chromax/indexer/` | GitHub fetch → chunk → embed → store |
| Memory | `src/chromax/memory/conversation.py` | Session persistence (JSON on disk) |
| Cache | `src/chromax/cache.py` | In-process TTL response cache |
| Tools | `src/chromax/tools/` | GitHub API + ChromaDB search wrappers |

## Key conventions

- **TDD** — write tests before implementation
- **No mocking in integration tests** — use real GitHub API and ChromaDB
- **Error strings at boundaries** — GitHub tools return `"Error: ..."` strings; don't raise at the tool layer
- **Session IDs** — alphanumeric + hyphens/underscores only (enforced by `_validate_session_id`)
- **Repo format** — must match `owner/name` (enforced by `_validate_repo` in CLI)
- **`.env` files** — never indexed (enforced in `chunker.py`)

## Commit style

```
feat: add X
fix: correct Y
chore: update Z
```

One logical change per commit.
