# Chromax Architecture Codemap

**Last Updated:** 2026-03-09
**Version:** 0.2.0
**Entry Points:** `src/chromax/cli.py` (Typer app), `src/chromax/__main__.py` (python -m)

---

## High-Level Architecture

```
                        User
                         |
                    chromax CLI
                    (cli.py / Typer)
                         |
          +--------------+--------------+
          |              |              |
        index          ask/chat       status
          |              |              |
          v              v              v
       Indexer      Supervisor      Indexer
      (indexer/)   (supervisor.py)  .chunk_count()
          |              |
          |     +--------+--------+
          |     |  classify_query |
          |     |  (LLM @ temp=0) |
          |     +--------+--------+
          |              |
          |     routes to one of:
          |     +-----+------+------+------+------+
          |     |     |      |      |      |      |
          |     v     v      v      v      v      v
          |   Struct Analyz Navig Search  Arch  Basic
          |   Agent  Agent  Agent  Agent  Agent Agent
          |     |     |      |      |      |     |
          |     +-----+------+------+------+-----+
          |              |
          |              v
          |     LangGraph ReAct Loop
          |     (agent node <-> tools node)
          |              |
          |       +------+------+
          |       |      |      |
          v       v      v      v
       GitHub   GitHub ChromaDB  ResponseCache
        API      API   (search)   (in-process)
       (fetch)  (tools)
          |
          v
       ChromaDB
       (store chunks)
```

---

## Module Map

### `cli.py` -- Command-Line Interface

| Export | Type | Purpose |
|---|---|---|
| `app` | `typer.Typer` | Root CLI application |
| `index()` | command | Fetch repo, chunk, embed, store |
| `status()` | command | Print chunk count for a repo |
| `ask()` | command | Single-question routing |
| `arch()` | command | Architecture analysis (overview or targeted) |
| `chat()` | command | Multi-turn interactive REPL |

Dependencies: `chromax.indexer.indexer`, `chromax.agents.supervisor`, `chromax.agents.arch`

### `agents/_base.py` -- Agent Factory

| Export | Type | Purpose |
|---|---|---|
| `AgentState` | TypedDict | LangGraph state schema (`messages` list) |
| `_build_graph(tools)` | function | Compiles a LangGraph `StateGraph` with agent+tools nodes |
| `make_ask(tools, prompt)` | function | Returns a bound `ask(question, repo) -> str` closure |
| `PROMPT_INJECTION_NOTICE` | str | Security notice appended to all system prompts |

Key detail: `_build_graph` creates a two-node graph (agent, tools) with a conditional edge. The agent node calls `ChatGroq(model="llama-3.3-70b-versatile", temperature=0)` with tools bound. If the LLM returns tool calls, control flows to the `ToolNode`; otherwise the graph ends. Recursion limit is 25.

### `agents/supervisor.py` -- Query Router

| Export | Type | Purpose |
|---|---|---|
| `classify_query(question)` | function | LLM-based classification into 5 categories |
| `route(question, repo)` | function | Classify then dispatch to specialist agent |
| `ask_with_session(question, repo, session_id)` | function | Session-aware routing via basic agent |

Categories: `structure`, `analyzer`, `navigation`, `search`, `architecture`. Falls back to `analyzer` on unrecognized output.

The `route()` function checks the `ResponseCache` before calling any agent and stores answers after.

`ask_with_session()` bypasses classification entirely -- it uses the full-toolset basic agent with conversation history loaded from disk (last 20 messages).

### `agents/basic.py` -- Full-Toolset Agent

| Export | Type | Purpose |
|---|---|---|
| `tool_search_codebase` | LangChain tool | Semantic search wrapper |
| `tool_get_readme` | LangChain tool | GitHub README fetcher |
| `tool_get_repo_structure` | LangChain tool | GitHub tree fetcher |
| `tool_get_file_content` | LangChain tool | GitHub file reader |
| `build_graph()` | function | Build and compile LangGraph agent |
| `ask(question, repo)` | function | One-shot question answering |

All other specialist agents (structure, analyzer, navigation, search, arch) are built using `make_ask()` from `_base.py`, each with a subset of these tools and a specialized system prompt.

### `agents/` -- Specialist Agents

| Agent | File | Tools Used | Specialty |
|---|---|---|---|
| StructureAgent | `structure.py` | readme, repo_structure | File tree / directory layout |
| AnalyzerAgent | `analyzer.py` | all 4 tools | Code logic / how things work |
| NavigationAgent | `navigation.py` | all 4 tools | Finding where code lives |
| SearchAgent | `search.py` | search_codebase, readme | Semantic similarity queries |
| ArchitectAgent | `arch.py` | all 4 tools | System design, patterns, trade-offs |

Each agent is a single-file module exporting an `ask(question, repo) -> str` function created by `make_ask()`.

### `indexer/indexer.py` -- Indexing Pipeline

| Export | Type | Purpose |
|---|---|---|
| `Indexer(repo)` | class | Manages a ChromaDB collection for one repo |
| `Indexer.index()` | method | Full pipeline: fetch files, chunk, embed, store |
| `Indexer.chunk_count()` | method | Count of chunks in the collection |
| `Indexer.query(text, n)` | method | Semantic similarity search against stored chunks |

Storage: `~/.chromax/db/` (ChromaDB PersistentClient). Collection name: `chromax__owner__repo`.

SHA guard: Stores `last_indexed_sha` in collection metadata. On subsequent `index()` calls, compares current HEAD SHA and short-circuits if unchanged.

### `indexer/chunker.py` -- File Chunking

| Export | Type | Purpose |
|---|---|---|
| `Chunk` | dataclass | Content + metadata (file_path, language, lines, repo) |
| `is_text_file(path, size)` | function | Filter: known text extensions, max 100 KB |
| `chunk_file(content, path, repo)` | function | Split file into overlapping chunks |
| `language_from_path(path)` | function | Extension-to-language mapping |

Chunking strategy:
1. Detect language from file extension.
2. Find top-level boundaries (function/class definitions) using language-specific regex.
3. If boundaries found: merge adjacent boundaries up to 60-line chunks.
4. If no boundaries: fixed sliding window (60 lines, 5-line overlap).

### `tools/github.py` -- GitHub API Layer

| Export | Type | Purpose |
|---|---|---|
| `get_readme(repo)` | function | Fetch decoded README content |
| `get_repo_structure(repo, max_depth)` | function | Tree listing (default depth 3) |
| `get_file_content(repo, path)` | function | Fetch single file (max 100 KB) |

All public functions wrap internal `_raw` variants with error handling. The `_with_retry` decorator applies exponential backoff (1s, 2s, 4s) on `RateLimitExceededException`.

### `tools/search.py` -- Semantic Search

| Export | Type | Purpose |
|---|---|---|
| `SearchResult` | dataclass | Content + metadata + L2 distance score |
| `search_codebase(query, repo, n)` | function | Query ChromaDB, return ranked results |

### `memory/conversation.py` -- Session Persistence

| Export | Type | Purpose |
|---|---|---|
| `load_session(id)` | function | Load message history from JSON file |
| `save_session(id, messages)` | function | Persist message history to JSON file |
| `clear_session(id)` | function | Delete a session file |

Storage: `~/.chromax/sessions/{session_id}.json`. Session IDs are validated against `[a-zA-Z0-9_-]{1,128}` to prevent path traversal.

### `cache.py` -- Response Cache

| Export | Type | Purpose |
|---|---|---|
| `ResponseCache` | class | In-memory TTL cache (default 1 hour) |
| `_cache` | singleton | Module-level instance used by `supervisor.route()` |

Key = `sha256(repo + normalized_question)[:16]`. Cache is process-scoped and lost on exit.

---

## Data Flow: Asking a Question

```
1. User runs: chromax ask "How does auth work?" --repo psf/requests

2. cli.py validates repo format (owner/name regex).

3. Without --session:
   a. supervisor.route() checks ResponseCache.
   b. On cache miss, classify_query() sends the question to Groq LLM (temp=0)
      with a classification prompt. Returns one of: structure, analyzer,
      navigation, search, architecture.
   c. The matching specialist agent is invoked.

4. With --session:
   a. supervisor.ask_with_session() loads history from
      ~/.chromax/sessions/{session_id}.json.
   b. Builds message list: system prompt + last 20 history messages + new question.
   c. Invokes the basic (full-toolset) agent -- no classification needed.

5. Agent execution (LangGraph ReAct loop):
   a. Agent node: LLM decides which tools to call (or to respond directly).
   b. Tools node: executes tool calls (GitHub API / ChromaDB search).
   c. Loop continues until LLM responds without tool calls (max 25 iterations).

6. Answer is extracted from the last message, cached (if routed), and printed
   as rendered Markdown via Rich.
```

---

## Data Flow: Indexing a Repository

```
1. User runs: chromax index --repo psf/requests

2. Indexer.__init__() opens ChromaDB PersistentClient at ~/.chromax/db/,
   gets or creates collection "chromax__psf__requests".

3. Indexer.index():
   a. Fetch HEAD SHA via GitHub API.
   b. Compare with stored last_indexed_sha in collection metadata.
   c. If unchanged -> short-circuit, return stats with chunks_skipped = count.
   d. If changed -> fetch full file tree via get_git_tree(recursive=True).

4. For each file:
   a. is_text_file() filters by extension and size (max 100 KB).
   b. get_file_content() fetches raw content via GitHub API.
   c. chunk_file() splits content into Chunk objects (boundary-aware or fixed-window).

5. _store_chunks() upserts into ChromaDB:
   a. Generate stable IDs: "{file_path}:{start_line}:{content_sha256[:16]}".
   b. Check which IDs already exist in the collection.
   c. Add only new chunks (documents + metadata).

6. Update collection metadata with current HEAD SHA.
```

---

## Key Design Patterns

| Pattern | Where | Description |
|---|---|---|
| Supervisor-Dispatch | `supervisor.py` | LLM classifies the question, then routes to the right specialist agent. Single entry point, fan-out to specialists. |
| LangGraph ReAct Loop | `_base.py:_build_graph()` | Two-node state graph (agent, tools) with conditional edge. Agent decides tool calls; loop until done. |
| Factory Function | `_base.py:make_ask()` | Creates bound `ask()` closures with pre-compiled graphs. Each specialist agent is a one-liner: `ask = make_ask(TOOLS, PROMPT)`. |
| Semantic Search (RAG) | `indexer/`, `tools/search.py` | Chunk, embed, store, retrieve. ChromaDB handles embedding + L2 similarity. |
| SHA-based Idempotency | `indexer.py:index()` | Stores HEAD SHA in ChromaDB metadata. Prevents redundant API calls on unchanged repos. |
| Content-addressed Dedup | `indexer.py:_chunk_id()` | Chunk IDs are derived from file path + line + content hash. Same content never stored twice. |
| Exponential Backoff | `tools/github.py:_with_retry` | Decorator retries GitHub API calls on rate limits (1s, 2s, 4s delays). |
| In-Process TTL Cache | `cache.py` | SHA256-keyed in-memory cache with 1-hour TTL. Avoids redundant LLM calls within a session. |
| Prompt Injection Defense | `_base.py:PROMPT_INJECTION_NOTICE` | Every agent system prompt includes a notice to treat tool output as untrusted data. |
| Session ID Validation | `memory/conversation.py` | Regex-based allowlist prevents path traversal in session file names. |

---

## External Dependencies

| Package | Purpose |
|---|---|
| langgraph | Agent state machine orchestration |
| langchain / langchain-core | LLM abstractions, tool binding, message types |
| langchain-groq | Groq LLM provider integration |
| langchain-chroma | ChromaDB LangChain integration |
| chromadb | Local vector database (embedding + similarity search) |
| PyGitHub | GitHub REST API client |
| typer | CLI framework (argument parsing, help generation) |
| rich | Terminal output (Markdown rendering, progress spinners) |
| tiktoken | Token counting |
| python-dotenv | `.env` file loading |

---

## Related Documentation

- [README.md](/README.md) -- Installation, usage, CLI reference
- [CONTRIBUTING.md](/CONTRIBUTING.md) -- Contribution guidelines
- [CHANGELOG.md](/CHANGELOG.md) -- Version history
