# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-03-08

### Added

- **`chromax arch` command** — codebase-aware architecture expert subcommand.
  - `chromax arch --repo owner/name` — produces a full structured overview: tech stack,
    module map, data flow narrative, key design patterns, architectural decisions, weak spots,
    and suggested follow-up questions.
  - `chromax arch "question" --repo owner/name` — targeted architectural Q&A with
    trade-off reasoning and concrete file-level evidence.
  - `chromax arch --repo owner/name --session <id>` — multi-turn architectural conversation
    with session persistence.
- **`architecture` routing category in supervisor** — `chromax ask "what's the architecture?"`
  now correctly routes to the ArchitectAgent rather than the AnalyzerAgent.
- **`ArchitectAgent`** (`src/chromax/agents/arch.py`) — senior architect persona with access
  to all four tools; explicitly scoped to design reasoning rather than file listing.

---

## [0.1.0] - 2026-03-05

### Added

- Initial release — index any GitHub repo and ask natural language questions about it.
- Multi-agent RAG pipeline with specialist routing (structure, analyzer, navigation, search).
- ChromaDB vector store with local ONNXMiniLM embeddings (no external embedding API).
- `chromax index` — fetch, chunk, and embed a GitHub repository.
- `chromax ask` — single-turn Q&A with automatic agent routing and response caching.
- `chromax chat` — interactive multi-turn REPL with session persistence.
- `chromax status` — show index stats for a repository.
- In-memory response cache (1-hour TTL) for repeated queries.
- Conversation session persistence to `~/.chromax/sessions/`.
- Prompt injection defence on all agents.
