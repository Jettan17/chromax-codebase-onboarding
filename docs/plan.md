# Chromax Codebase Onboarding Agent — Implementation Plan

**Goal:** Ship an agent that indexes a GitHub repo and answers codebase questions.

Each phase ends with a concrete test so you can stop, verify it works, and pick up again confidently.

---

## PHASE 1A — Project Setup + GitHub Auth
**Days 1–2 | ~3 hrs**

### Tasks
- [ ] Initialize Python project (`pyproject.toml`, virtual env)
- [ ] Install core deps: `langgraph`, `langchain`, `anthropic`, `PyGitHub`, `python-dotenv`
- [ ] Create `.env` with `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`
- [ ] Implement `get_readme(repo: str) -> str` tool
- [ ] Wire tool into a minimal LangGraph node (no agent yet, just tool call)

### Files Created
- `pyproject.toml`
- `.env.example`
- `src/chromax/tools/github.py` → `get_readme`
- `src/chromax/tools/__init__.py`
- `tests/phase1/test_get_readme.py`

### Test Checkpoint ✓
```bash
python -m pytest tests/phase1/test_get_readme.py -v
# PASS: get_readme("langchain-ai/langchain") returns non-empty string with "README"
```

---

## PHASE 1B — Full GitHub Tools
**Days 3–4 | ~3 hrs**

### Tasks
- [ ] Implement `get_repo_structure(repo: str) -> str` — tree of files/dirs
- [ ] Implement `get_file_content(repo: str, path: str) -> str` — raw file content
- [ ] Add error handling: private repos, rate limits, file-not-found
- [ ] Unit tests for each tool

### Files Created/Modified
- `src/chromax/tools/github.py` → add `get_repo_structure`, `get_file_content`
- `tests/phase1/test_github_tools.py`

### Test Checkpoint ✓
```bash
python -m pytest tests/phase1/ -v
# PASS: All 3 tools return correct data for a public test repo
# PASS: Private repo returns graceful error message
# PASS: Missing file returns graceful error message
```

---

## PHASE 1C — Basic LangGraph Agent
**Days 5–7 | ~4 hrs**

### Tasks
- [ ] Build LangGraph graph with 3 tools bound to an LLM (Claude Haiku)
- [ ] Add system prompt: "You are a codebase expert. Use tools to answer questions."
- [ ] CLI entry: `python -m chromax ask "<question>" --repo <owner/repo>`
- [ ] Read OWASP LLM Top 10 (note risks: prompt injection via code, data leakage)

### Files Created/Modified
- `src/chromax/agents/basic.py` — LangGraph graph definition
- `src/chromax/main.py` — CLI entry point
- `tests/phase1/test_basic_agent.py`

### Test Checkpoint ✓
```bash
python -m chromax ask "What does this repo do?" --repo langchain-ai/langchain
# PASS: Returns a paragraph summary with at least 1 file reference (e.g., "README.md")
# PASS: Response is grounded (mentions actual repo name/topics)
```

**→ Week 1 complete. You have a working agent that reads GitHub on-demand.**

---

## PHASE 2A — ChromaDB + Indexer Pipeline
**Days 1–5 | ~4 hrs/day**

### Tasks
- [ ] Install deps: `chromadb`, `langchain-chroma`, `tiktoken`
- [ ] Build `Indexer` class: `clone_or_fetch(repo)` → `parse_files()` → `chunk()` → `embed()` → `store()`
- [ ] Chunking strategy: by function/class using simple regex (skip tree-sitter for now)
- [ ] Metadata per chunk: `file_path`, `language`, `start_line`, `end_line`, `repo`
- [ ] Skip binary files, files > 100KB, and non-text extensions
- [ ] Persist ChromaDB to `~/.chromax/db/` (reuse across runs)
- [ ] CLI: `python -m chromax index --repo <owner/repo>`

### Files Created/Modified
- `src/chromax/indexer/indexer.py` — `Indexer` class
- `src/chromax/indexer/chunker.py` — chunking logic
- `src/chromax/indexer/__init__.py`
- `tests/phase2/test_indexer.py`

### Test Checkpoint ✓
```bash
python -m chromax index --repo psf/requests
python -m pytest tests/phase2/test_indexer.py -v
# PASS: ChromaDB collection has > 50 chunks
# PASS: Each chunk has metadata: file_path, language, start_line, end_line
# PASS: Binary files (images, etc.) were skipped
# PASS: Running index again does NOT duplicate chunks (idempotent)
```

---

## PHASE 2B — Semantic Search Agent
**Days 6–7 | ~3 hrs**

### Tasks
- [ ] Add `search_codebase(query: str) -> list[Result]` tool using ChromaDB
- [ ] Update agent: try semantic search first, fall back to GitHub API tools
- [ ] Citations in responses: every claim includes `file_path:line_range`
- [ ] Update CLI: `python -m chromax ask "<question>" --repo <owner/repo>`

### Files Created/Modified
- `src/chromax/tools/search.py` — `search_codebase` tool
- `src/chromax/agents/basic.py` — add search tool
- `tests/phase2/test_semantic_search.py`

### Test Checkpoint ✓
```bash
# Requires psf/requests indexed from Phase 2A
python -m chromax ask "How does HTTP auth work?" --repo psf/requests
# PASS: Response mentions auth.py or similar with line references
# PASS: Response does NOT hallucinate file names not in the repo
python -m pytest tests/phase2/ -v
```

**→ Week 2 complete. Agent indexes a repo and answers via semantic search with citations.**

---

## PHASE 3A — Multi-Agent Refactor
**Days 1–3 | ~4 hrs/day**

### Tasks
- [ ] Split into 4 specialized agents:
  - `StructureAgent` — file tree, repo layout questions
  - `AnalyzerAgent` — code logic, function behavior questions
  - `NavigationAgent` — "where is X?" location questions
  - `SearchAgent` — semantic similarity questions
- [ ] Build `SupervisorAgent` that classifies query → routes to specialist
- [ ] Each agent gets only the tools it needs (principle of least privilege)

### Files Created/Modified
- `src/chromax/agents/structure.py`
- `src/chromax/agents/analyzer.py`
- `src/chromax/agents/navigation.py`
- `src/chromax/agents/search.py`
- `src/chromax/agents/supervisor.py`
- `tests/phase3/test_routing.py`

### Test Checkpoint ✓
```bash
python -m pytest tests/phase3/test_routing.py -v
# PASS: "What files are in the project?" → routed to StructureAgent
# PASS: "How does the retry logic work?" → routed to AnalyzerAgent
# PASS: "Where is the auth code?" → routed to NavigationAgent
# PASS: "Find code similar to async request handling" → routed to SearchAgent
```

---

## PHASE 3B — Memory + Persistence
**Days 4–5 | ~3 hrs**

### Tasks
- [ ] Add conversation memory via `thread_id` (LangGraph checkpointer)
- [ ] Persist repo index state: track last-indexed commit SHA, skip if unchanged
- [ ] CLI: `chromax ask` remembers conversation within a session via `--session <id>`
- [ ] Store session history in `~/.chromax/sessions/`

### Files Created/Modified
- `src/chromax/memory/conversation.py`
- `src/chromax/memory/__init__.py`
- Updated `src/chromax/indexer/indexer.py` (SHA tracking)
- `tests/phase3/test_memory.py`

### Test Checkpoint ✓
```bash
python -m pytest tests/phase3/test_memory.py -v
# PASS: Second question in session references context from first question
# PASS: Re-indexing same repo at same SHA skips all files (0 new chunks)
# PASS: Re-indexing after a new commit processes only changed files
```

---

## PHASE 3C — Error Handling + Edge Cases
**Days 6–7 | ~3 hrs**

### Tasks
- [ ] Rate limit handling: exponential backoff on GitHub 429/403
- [ ] Large file handling: skip files > 100KB, log warning
- [ ] Private repo handling: clear error if token lacks access
- [ ] Unsupported language: skip gracefully, don't crash
- [ ] "I don't know" responses when confidence is low (no relevant chunks)
- [ ] Binary file detection: check extension + MIME type

### Files Created/Modified
- `src/chromax/tools/github.py` — error handling improvements
- `src/chromax/indexer/indexer.py` — edge case handling
- `tests/phase3/test_edge_cases.py`

### Test Checkpoint ✓
```bash
python -m pytest tests/phase3/test_edge_cases.py -v
# PASS: Rate limit triggers backoff (mock 429 response)
# PASS: 500KB file is skipped with log message
# PASS: Private repo without access returns "Repository not accessible" message
# PASS: Unknown question returns "I don't have enough information about that in this repo"
```

**→ Week 3 complete. Multi-agent system handles real-world repos.**

---

## PHASE 4A — CLI Interface
**Days 1–2 | ~3 hrs**

### Tasks
- [ ] Install `typer` (or `click`) for rich CLI
- [ ] Commands:
  - `chromax index --repo <owner/repo>` — index a repo
  - `chromax ask "<question>" --repo <owner/repo>` — one-shot question
  - `chromax chat --repo <owner/repo>` — interactive session
  - `chromax status --repo <owner/repo>` — show index stats
- [ ] Rich output: colored text, progress bars during indexing
- [ ] Install as package: `pip install -e .`

### Files Created/Modified
- `src/chromax/cli.py` — Typer app
- Updated `pyproject.toml` — entry point `chromax = "chromax.cli:app"`
- `tests/phase4/test_cli.py`

### Test Checkpoint ✓
```bash
pip install -e .
chromax --help
chromax index --repo psf/requests
chromax ask "What HTTP methods does this support?" --repo psf/requests
chromax status --repo psf/requests
python -m pytest tests/phase4/test_cli.py -v
# PASS: All commands run without error
# PASS: Progress bar shown during indexing
# PASS: Output includes file citations
```

---

## PHASE 4B — Caching + Polish
**Days 3–4 | ~3 hrs**

### Tasks
- [ ] File-level caching: track file hash, skip unchanged files on re-index
- [ ] Response caching: cache identical questions per repo (TTL: 1 hour)
- [ ] Clean up logging: INFO for normal ops, DEBUG for verbose
- [ ] Write `README.md` with install instructions + demo

### Files Created/Modified
- `src/chromax/indexer/cache.py`
- Updated `src/chromax/indexer/indexer.py`
- `README.md`
- `tests/phase4/test_caching.py`

### Test Checkpoint ✓
```bash
python -m pytest tests/phase4/test_caching.py -v
# PASS: Re-indexing unchanged repo processes 0 new files
# PASS: Same question asked twice returns cached response (< 100ms second time)
# PASS: Cache expires after TTL and re-fetches
```

---

## PHASE 4C — Ship
**Days 5–7 | ~2 hrs**

### Tasks
- [ ] Push to GitHub with public repo
- [ ] Add `CONTRIBUTING.md` and `LICENSE`
- [ ] Record demo (terminal recording via `asciinema` or screen capture)
- [ ] Share with 3 people, collect feedback
- [ ] Tag `v0.1.0` release

### Test Checkpoint ✓
```
[ ] GitHub repo is public
[ ] README has install instructions that work from scratch
[ ] 3 people tried it and reported back
[ ] v0.1.0 tagged on GitHub
```

**→ Week 4 complete. You shipped it.**

---

## Architecture Overview

```
chromax ask "How does auth work?" --repo psf/requests
        │
        ▼
  SupervisorAgent
  (classifies query)
        │
   ┌────┴────┐
   ▼         ▼
SearchAgent  NavigationAgent  ...
   │
   ▼
ChromaDB (semantic search)
   │
   ▼
LLM (Claude Haiku)
generates answer with citations
```

---

## Dependency Stack

```
langgraph          # agent orchestration
langchain          # tools, chains, RAG utilities
langchain-anthropic # Claude LLM
langchain-chroma   # ChromaDB integration
chromadb           # vector store
PyGitHub           # GitHub API client
typer              # CLI framework
rich               # terminal output
python-dotenv      # env var management
tiktoken           # token counting for chunking
pytest             # testing
```

---

## Resources (from syllabus)

- LangGraph: https://academy.langchain.com (Modules 1, 2, 4, 5, 6)
- RAG tutorial: https://python.langchain.com/docs/tutorials/rag
- ChromaDB: https://docs.trychroma.com
- GitHub API: https://pygithub.readthedocs.io
- Code parsing (optional): https://tree-sitter.github.io/tree-sitter
- Security: https://genai.owasp.org/llm-top-10
- UI (optional): https://streamlit.io
