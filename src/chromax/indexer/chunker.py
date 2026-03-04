"""Code chunking logic for the Chromax indexer."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Extensions we consider text/code (skip everything else)
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".sh",
    ".bash", ".zsh", ".fish", ".ps1", ".md", ".rst", ".txt", ".yaml", ".yml",
    ".json", ".toml", ".ini", ".cfg", ".env", ".sql", ".html", ".css", ".scss",
    ".xml", ".tf", ".hcl", ".dockerfile", ".makefile",
}

# Regex patterns to detect top-level function/class boundaries per language
_PYTHON_BOUNDARY = re.compile(r"^(def |class |async def )", re.MULTILINE)
_JS_BOUNDARY = re.compile(
    r"^(export |function |const \w+ = |class |async function )", re.MULTILINE
)
_GENERIC_BOUNDARY = re.compile(r"^(func |def |class |sub |function )", re.MULTILINE)

CHUNK_SIZE = 60       # target lines per chunk
CHUNK_OVERLAP = 5     # overlap lines between chunks


@dataclass
class Chunk:
    content: str
    file_path: str
    language: str
    start_line: int   # 1-indexed
    end_line: int     # 1-indexed, inclusive
    repo: str


def language_from_path(path: str) -> str:
    ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
    mapping = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
        ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
        ".cs": "csharp", ".go": "go", ".rs": "rust", ".rb": "ruby",
        ".php": "php", ".swift": "swift", ".kt": "kotlin",
        ".scala": "scala", ".sh": "bash", ".bash": "bash",
        ".md": "markdown", ".rst": "rst", ".sql": "sql",
        ".yaml": "yaml", ".yml": "yaml", ".json": "json",
        ".toml": "toml", ".html": "html", ".css": "css",
    }
    return mapping.get(ext, "text")


def is_text_file(path: str, size_bytes: int) -> bool:
    """Return True if the file should be indexed."""
    if size_bytes > 100_000:
        return False
    ext = ("." + path.rsplit(".", 1)[-1].lower()) if "." in path else ""
    name = path.split("/")[-1].lower()
    # Accept known text extensions or extensionless files with known names
    return ext in TEXT_EXTENSIONS or name in {"makefile", "dockerfile", "procfile"}


def chunk_file(content: str, file_path: str, repo: str) -> list[Chunk]:
    """Split a file's content into overlapping chunks with metadata."""
    lines = content.splitlines()
    if not lines:
        return []

    lang = language_from_path(file_path)
    boundary_re = _get_boundary_re(lang)

    # Find boundary line indices (0-based)
    boundaries = _find_boundaries(lines, boundary_re)

    if len(boundaries) <= 1:
        # No structure detected — fall back to fixed-size sliding window
        return _fixed_chunks(lines, file_path, lang, repo)

    return _boundary_chunks(lines, boundaries, file_path, lang, repo)


# ---------- helpers ----------

def _get_boundary_re(lang: str):
    if lang == "python":
        return _PYTHON_BOUNDARY
    if lang in ("javascript", "typescript"):
        return _JS_BOUNDARY
    return _GENERIC_BOUNDARY


def _find_boundaries(lines: list[str], pattern) -> list[int]:
    boundaries = [i for i, line in enumerate(lines) if pattern.match(line)]
    boundaries.append(len(lines))  # sentinel
    return boundaries


def _boundary_chunks(
    lines: list[str],
    boundaries: list[int],
    file_path: str,
    lang: str,
    repo: str,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    i = 0
    while i < len(boundaries) - 1:
        start = boundaries[i]
        # Accumulate boundaries until we reach CHUNK_SIZE lines
        end = boundaries[i + 1]
        j = i + 1
        while j < len(boundaries) - 1 and (boundaries[j + 1] - start) <= CHUNK_SIZE:
            end = boundaries[j + 1]
            j += 1

        chunk_lines = lines[start:end]
        if chunk_lines:
            chunks.append(Chunk(
                content="\n".join(chunk_lines),
                file_path=file_path,
                language=lang,
                start_line=start + 1,
                end_line=end,
                repo=repo,
            ))
        i = j

    return chunks


def _fixed_chunks(
    lines: list[str],
    file_path: str,
    lang: str,
    repo: str,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    for start in range(0, len(lines), step):
        end = min(start + CHUNK_SIZE, len(lines))
        chunk_lines = lines[start:end]
        if chunk_lines:
            chunks.append(Chunk(
                content="\n".join(chunk_lines),
                file_path=file_path,
                language=lang,
                start_line=start + 1,
                end_line=end,
                repo=repo,
            ))
    return chunks
