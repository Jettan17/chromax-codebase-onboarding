# Chromax -- Codebase Onboarding Agent

Index any GitHub repository and ask natural-language questions about it using a multi-agent RAG pipeline.

```bash
chromax index --repo psf/requests
chromax ask "How does HTTP authentication work?" --repo psf/requests
```

---

## Tech Stack

| Technology | Role | Version Constraint |
|---|---|---|
| Python | Runtime | >= 3.11 |
| LangGraph | Agent orchestration (state machine graphs) | >= 0.2 |
| LangChain | LLM abstractions, tool binding | >= 0.3 |
| Groq (llama-3.3-70b-versatile) | LLM inference (classification and answering) | langchain-groq >= 0.2 |
| ChromaDB | Local vector store for semantic search | >= 0.5 |
| ONNX MiniLM-L6-V2 | Embedding model (runs locally via ChromaDB) | bundled with chromadb |
| PyGitHub | GitHub API access (file fetching, tree listing) | >= 2.3 |
| Typer | CLI framework | >= 0.12 |
| Rich | Terminal formatting (markdown, spinners, colors) | >= 13 |
| tiktoken | Token counting for chunking | >= 0.7 |
| python-dotenv | Environment variable loading from `.env` | >= 1.0 |

---

## Features

- **Semantic indexing** -- chunks and embeds source files into a local ChromaDB vector store.
- **Multi-agent routing** -- supervisor classifies each question and delegates to the right specialist (structure / analyzer / navigation / search / architecture).
- **Architecture analysis** -- dedicated `arch` command with a senior-architect persona for design-level insight.
- **Conversation memory** -- `--session` flag persists multi-turn context across `ask` calls (JSON on disk).
- **Interactive chat** -- `chromax chat` REPL for back-and-forth exploration.
- **In-process caching** -- identical questions for the same repo are answered instantly (1-hour TTL).
- **SHA-based re-index guard** -- skips indexing if the repo HEAD has not changed since last run.
- **Rate-limit resilience** -- exponential backoff on GitHub API rate limits (up to 3 retries).
- **Security** -- `.env` files are never indexed; prompt-injection notice injected into every agent system prompt.

---

## Prerequisites

- Python 3.11 or later
- A GitHub personal access token (read-only `public_repo` scope is enough)
- A Groq API key ([console.groq.com](https://console.groq.com) -- free tier available)

---

## Installation

```bash
git clone https://github.com/Jettan17/chromax-codebase-onboarding
cd chromax-codebase-onboarding

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e ".[dev]"

cp .env.example .env
# Edit .env and fill in your tokens
```

### Required Environment Variables

| Variable | Where to get it |
|---|---|
| `GITHUB_TOKEN` | GitHub > Settings > Developer settings > Personal access tokens |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |

---

## CLI Commands

### `chromax index` -- Index a repository

Downloads all text files (up to 100 KB each), chunks them using language-aware boundary detection, embeds them with MiniLM-L6-V2, and stores them in a local ChromaDB collection at `~/.chromax/db`. Subsequent runs skip re-indexing if the repo HEAD SHA has not changed.

```bash
chromax index --repo psf/requests
chromax index --repo psf/requests --verbose   # show debug logs
```

### `chromax status` -- Check index status

```bash
chromax status --repo psf/requests
# psf/requests - 312 chunks in vector store.
```

### `chromax ask` -- Ask a single question

Routes the question through the supervisor, which classifies it and delegates to the appropriate specialist agent.

```bash
chromax ask "How does HTTP authentication work?" --repo psf/requests
```

With conversation memory (persists context across calls):

```bash
chromax ask "What does this repo do?" --repo psf/requests --session my-session
chromax ask "Where is the retry logic?" --repo psf/requests --session my-session
```

### `chromax arch` -- Architecture analysis

Uses a senior-architect persona to provide deep design-level insight. Omit the question to get a full structured overview (tech stack, module map, data flow, design patterns, weak spots).

```bash
chromax arch --repo psf/requests                              # full overview
chromax arch "What patterns does the auth module use?" --repo psf/requests  # targeted question
```

### `chromax chat` -- Interactive REPL

Multi-turn conversation with automatic session management.

```bash
chromax chat --repo psf/requests
# Chromax chat - psf/requests  (session: chat-a1b2c3d4)
# Type your question and press Enter. Ctrl+C or 'exit' to quit.
#
# You: What is the main entry point?
# ...
# You: exit
```

---

## Project Structure

```
src/chromax/
  __init__.py           # Package root, version string
  __main__.py           # python -m chromax entry point
  cli.py                # Typer CLI (index / status / ask / arch / chat)
  cache.py              # ResponseCache -- in-process TTL cache (1h, sha256 key)
  agents/
    __init__.py
    _base.py            # AgentState, _build_graph(), make_ask() factory
    supervisor.py       # classify_query() + route() + ask_with_session()
    basic.py            # Full-toolset agent, LangChain tool wrappers
    structure.py        # StructureAgent  -- file tree questions
    analyzer.py         # AnalyzerAgent   -- code logic questions
    navigation.py       # NavigationAgent -- "where is X" questions
    search.py           # SearchAgent     -- semantic similarity questions
    arch.py             # ArchitectAgent  -- design / architecture analysis
  indexer/
    __init__.py
    indexer.py           # Indexer class (index, chunk_count, query)
    chunker.py           # File filtering, language detection, text chunking
  memory/
    conversation.py      # load_session / save_session (JSON on disk at ~/.chromax/sessions/)
  tools/
    __init__.py
    github.py            # get_readme, get_file_content, get_repo_structure (with retry)
    search.py            # search_codebase (ChromaDB semantic search wrapper)
tests/
  phase1/                # GitHub tools + basic agent
  phase2/                # Indexer + semantic search
  phase3/                # Routing, memory, edge cases
  phase4/                # CLI, caching
```

---

## Development

Activate the virtual environment first:

```bash
source .venv/Scripts/activate   # Git Bash on Windows
# or
source .venv/bin/activate        # macOS / Linux
```

Then:

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=chromax --cov-report=term-missing

# Lint
ruff check .

# Lint + auto-fix
ruff check --fix .
```

---

## Data Storage

All persistent data lives under `~/.chromax/`:

| Path | Contents |
|---|---|
| `~/.chromax/db/` | ChromaDB vector store (one collection per repo) |
| `~/.chromax/sessions/` | Conversation history JSON files (one per session ID) |

---

## Status

All implementation phases complete. Current version: **0.2.0**.

| Phase | Description | Status |
|---|---|---|
| 1A | Project setup + GitHub auth | Done |
| 1B | Full GitHub tools | Done |
| 1C | Basic LangGraph agent | Done |
| 2A | ChromaDB + indexer pipeline | Done |
| 2B | Semantic search agent | Done |
| 3A | Multi-agent routing | Done |
| 3B | Memory + SHA persistence | Done |
| 3C | Error handling + edge cases | Done |
| 4A | Ruff linting | Done |
| 4B | CLI completeness + caching | Done |
| 4C | README + polish | Done |

---

## Resources

- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
- [LangChain RAG tutorial](https://python.langchain.com/docs/tutorials/rag)
- [ChromaDB docs](https://docs.trychroma.com)
- [PyGitHub](https://pygithub.readthedocs.io)
- [OWASP LLM Top 10](https://genai.owasp.org/llm-top-10)
