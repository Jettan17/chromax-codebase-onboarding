# Chromax — Codebase Onboarding Agent

Index any GitHub repo and ask natural language questions about it using a multi-agent RAG pipeline.

```bash
chromax index --repo psf/requests
chromax ask "How does HTTP authentication work?" --repo psf/requests
```

---

## Features

- **Semantic indexing** — chunks and embeds source files into a local ChromaDB vector store
- **Multi-agent routing** — supervisor classifies each question and delegates to the right specialist (structure / analyzer / navigation / search)
- **Conversation memory** — `--session` flag persists multi-turn context across `ask` calls
- **Interactive chat** — `chromax chat` REPL for back-and-forth exploration
- **In-process caching** — identical questions for the same repo are answered instantly (1-hour TTL)
- **SHA-based re-index guard** — skips indexing if the repo HEAD hasn't changed since last run
- **Rate-limit resilience** — exponential backoff on GitHub API rate limits
- **Security** — `.env` files never indexed, prompt-injection notice injected into every agent

---

## Architecture

```
chromax ask "How does auth work?" --repo psf/requests
        |
        v
 ResponseCache (check — 1h TTL, sha256 key)
        |
        v (cache miss)
 SupervisorAgent (classify_query via LLM @ temp=0)
        |
   +---------+-----------+-----------+
   v         v           v           v
Structure  Analyzer  Navigation  Search
Agent      Agent      Agent       Agent
   |         |           |           |
   +---------+-----------+-----------+
        |
        v
 ChromaDB  (local vector store — text + embeddings + metadata)
        |
        v
 GitHub API  (get_readme, get_file_content, get_repo_structure)
        |
        v
 Groq LLM  (llama-3.3-70b — answer with citations)
        |
        v
 ResponseCache (store answer)
        |
        v
 Answer
```

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/chromax-codebase-onboarding
cd chromax-codebase-onboarding

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e ".[dev]"

cp .env.example .env
# Edit .env and fill in your tokens
```

### Required environment variables

| Variable | Where to get it |
|----------|----------------|
| `GITHUB_TOKEN` | GitHub → Settings → Developer settings → Personal access tokens (read-only `public_repo` scope is enough) |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) — free tier available |

---

## Usage

### Index a repository

```bash
chromax index --repo psf/requests
```

Downloads all text files ≤ 100 KB, chunks them, embeds them, and stores them in a local ChromaDB collection. Subsequent runs skip re-indexing if the repo HEAD SHA hasn't changed.

### Ask a single question

```bash
chromax ask "How does HTTP authentication work?" --repo psf/requests
```

Add `--session <id>` to carry conversation context across multiple `ask` calls:

```bash
chromax ask "What does this repo do?" --repo psf/requests --session my-session
chromax ask "Where is the retry logic?" --repo psf/requests --session my-session
```

### Interactive chat

```bash
chromax chat --repo psf/requests
# Chromax chat - psf/requests  (session: chat-a1b2c3d4)
# Type your question and press Enter. Ctrl+C or 'exit' to quit.
#
# You: What is the main entry point?
# ...
# You: exit
```

### Check index status

```bash
chromax status --repo psf/requests
# psf/requests - 312 chunks in vector store.
```

### Verbose / debug output

```bash
chromax index --repo psf/requests --verbose
```

---

## Project layout

```
src/chromax/
  agents/
    _base.py          # make_ask() factory shared by all specialists
    supervisor.py     # classify_query() + route() + ask_with_session()
    structure.py      # StructureAgent  — file tree questions
    analyzer.py       # AnalyzerAgent   — code logic questions
    navigation.py     # NavigationAgent — "where is X" questions
    search.py         # SearchAgent     — semantic similarity questions
    basic.py          # Full-toolset agent used in session mode
  indexer/
    indexer.py        # Indexer class (index, chunk_count, query)
    chunker.py        # File filtering + text chunking
    embedder.py       # Embedding wrapper
  memory/
    conversation.py   # load_session / save_session (JSON on disk)
  tools/
    github.py         # get_readme, get_file_content, get_repo_structure
    search.py         # search_codebase (ChromaDB semantic search)
  cache.py            # ResponseCache — in-process TTL cache
  cli.py              # Typer CLI (index / ask / chat / status)
tests/
  phase1/             # GitHub tools + basic agent
  phase2/             # Indexer + semantic search
  phase3/             # Routing, memory, edge cases
  phase4/             # CLI, caching
```

---

## Development

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

## Status

All implementation phases complete.

| Phase | Description | Status |
|-------|-------------|--------|
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
