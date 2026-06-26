from __future__ import annotations

import re
from dataclasses import dataclass

try:
    from .vault import Vault
except ImportError:
    from vault import Vault


@dataclass(frozen=True)
class ReadResult:
    path: str
    start: int
    end: int
    content: str


@dataclass(frozen=True)
class SearchHit:
    path: str
    line: int
    text: str


def read_note(vault: Vault, *, path: str, start: int = 1, lines: int | None = None) -> ReadResult:
    note = vault.path(path)
    content_lines = note.read_text(encoding="utf-8", errors="replace").splitlines()
    first = max(start, 1)
    last = len(content_lines) if lines is None else min(len(content_lines), first + max(lines, 0) - 1)
    selected = content_lines[first - 1 : last]
    return ReadResult(vault.rel(note), first, last, "\n".join(selected))


def search_notes(
    vault: Vault,
    *,
    query: str,
    path_prefix: str | None = None,
    limit: int = 50,
    regex: bool = False,
    case_sensitive: bool = False,
) -> list[SearchHit]:
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(query if regex else re.escape(query), flags)
    hits: list[SearchHit] = []
    for note in vault.markdown(prefix=path_prefix):
        lines = note.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_no, line in enumerate(lines, start=1):
            if pattern.search(line):
                hits.append(SearchHit(vault.rel(note), line_no, line.strip()))
                if len(hits) >= limit:
                    return hits
    return hits
