# Chromax — Codebase Onboarding Agent

Index any GitHub repo and ask natural language questions about it.

```bash
chromax index --repo langchain-ai/langchain
chromax ask "How does the memory module work?" --repo langchain-ai/langchain
```

---

## Status

🚧 **In development** — following the [4-week build plan](docs/plan.md).

| Phase | Description | Status |
|-------|-------------|--------|
| 1A | Project setup + GitHub auth | ⬜ Not started |
| 1B | Full GitHub tools | ⬜ Not started |
| 1C | Basic LangGraph agent | ⬜ Not started |
| 2A | ChromaDB + indexer pipeline | ⬜ Not started |
| 2B | Semantic search agent | ⬜ Not started |
| 3A | Multi-agent refactor | ⬜ Not started |
| 3B | Memory + persistence | ⬜ Not started |
| 3C | Error handling + edge cases | ⬜ Not started |
| 4A | CLI interface | ⬜ Not started |
| 4B | Caching + polish | ⬜ Not started |
| 4C | Ship | ⬜ Not started |

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/chromax-codebase-onboarding
cd chromax-codebase-onboarding

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -e ".[dev]"

cp .env.example .env
# Fill in GITHUB_TOKEN and ANTHROPIC_API_KEY
```

## Usage

```bash
# Index a repository
chromax index --repo psf/requests

# Ask a question
chromax ask "How does HTTP authentication work?" --repo psf/requests

# Interactive chat session
chromax chat --repo psf/requests

# Check index status
chromax status --repo psf/requests
```

## Architecture

```
chromax ask "How does auth work?" --repo psf/requests
        │
        ▼
  SupervisorAgent (routes to best specialist)
        │
   ┌────┴─────────────┐
   ▼                  ▼
SearchAgent      NavigationAgent  ...
   │
   ▼
ChromaDB (semantic search over indexed chunks)
   │
   ▼
Claude Haiku (generates answer with citations)
```

## Resources

- [LangGraph Academy](https://academy.langchain.com)
- [LangChain RAG Tutorial](https://python.langchain.com/docs/tutorials/rag)
- [ChromaDB Docs](https://docs.trychroma.com)
- [PyGitHub](https://pygithub.readthedocs.io)
- [OWASP LLM Top 10](https://genai.owasp.org/llm-top-10)
