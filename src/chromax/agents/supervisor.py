"""SupervisorAgent — classifies queries and routes to specialist agents."""

from __future__ import annotations

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

# ---------- Classification prompt ----------

_CLASSIFY_PROMPT = """\
Classify this codebase question into exactly one of these categories:

- structure: file tree, directory layout, what files or folders exist
- analyzer: code logic, how a function works, algorithm details, implementation explanation
- navigation: finding where specific code, a feature, or a concept is located
- search: finding code similar to a description, semantic similarity search

Respond with ONLY the category name (structure / analyzer / navigation / search).
Do not add any other text or punctuation.

Question: {question}"""

_VALID_CATEGORIES = frozenset({"structure", "analyzer", "navigation", "search"})


def classify_query(question: str) -> str:
    """Use the LLM to classify a question into a routing category.

    Returns one of: 'structure', 'analyzer', 'navigation', 'search'.
    Falls back to 'analyzer' if the LLM returns an unexpected value.
    """
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    response = llm.invoke(_CLASSIFY_PROMPT.format(question=question))
    category = response.content.strip().lower().rstrip(".")
    return category if category in _VALID_CATEGORIES else "analyzer"


# ---------- Routing ----------

def route(question: str, repo: str) -> str:
    """Classify a question and delegate to the appropriate specialist agent."""
    from chromax.agents.structure import ask as ask_structure
    from chromax.agents.analyzer import ask as ask_analyzer
    from chromax.agents.navigation import ask as ask_navigation
    from chromax.agents.search import ask as ask_search

    specialist = {
        "structure": ask_structure,
        "analyzer": ask_analyzer,
        "navigation": ask_navigation,
        "search": ask_search,
    }
    category = classify_query(question)
    return specialist[category](question, repo)


# ---------- Session-aware routing ----------

def ask_with_session(question: str, repo: str, session_id: str) -> str:
    """Ask a question with conversation history loaded from disk.

    Uses the full-toolset agent (basic) so the LLM has context continuity
    across multi-turn conversations without re-classifying each turn.
    """
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from chromax.agents.basic import SYSTEM_PROMPT, build_graph
    from chromax.memory.conversation import load_session, save_session

    history = load_session(session_id)

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history:
        if msg["role"] == "human":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=f"Repository: {repo}\n\nQuestion: {question}"))

    graph = build_graph()
    result = graph.invoke({"messages": messages}, config={"recursion_limit": 25})
    answer = result["messages"][-1].content

    history.append({"role": "human", "content": question})
    history.append({"role": "ai", "content": answer})
    save_session(session_id, history)

    return answer
