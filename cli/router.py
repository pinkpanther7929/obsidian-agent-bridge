from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from .config import DEFAULT_CATEGORY_HINTS
    from .vault import Vault
except ImportError:
    from config import DEFAULT_CATEGORY_HINTS
    from vault import Vault

STOPWORDS = {"current", "history", "index", "issue", "issues", "note", "notes", "project", "projects", "task", "tasks"}


@dataclass(frozen=True)
class RouteResult:
    category: str
    confidence: float
    reason: str
    read_set: list[str]


def _text_blob(cwd: str | None, paths: list[str], request: str | None) -> str:
    parts = [cwd or "", request or "", *paths]
    return " ".join(parts).replace("\\", "/").casefold()


def _words(value: str) -> list[str]:
    return [
        word
        for word in re.split(r"[^A-Za-z0-9가-힣]+", value.casefold())
        if len(word) >= 2 and word not in STOPWORDS
    ]


def _index_hints(vault: Vault, category: str) -> list[str]:
    index = vault.path(f"{category}/index.md")
    if not index.exists():
        return []
    text = index.read_text(encoding="utf-8", errors="replace")
    hints: list[str] = []
    for line in text.splitlines()[:40]:
        if line.startswith("#"):
            hints.extend(_words(line.lstrip("#").strip()))
        for target in re.findall(r"\[\[([^\]|#]+)", line):
            hints.extend(_words(Path(target).name))
    return hints


def _project_categories(vault: Vault) -> Iterable[str]:
    projects = vault.path("projects")
    if not projects.exists():
        return []
    categories: list[str] = []
    for project in projects.iterdir():
        if not project.is_dir():
            continue
        for category in project.iterdir():
            if category.is_dir() and (category / "index.md").exists():
                categories.append(vault.rel(category))
    return categories


def build_category_hints(vault: Vault, seed: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
    hints_by_category: dict[str, list[str]] = {key: list(value) for key, value in (seed or {}).items()}
    for category in _project_categories(vault):
        hints = hints_by_category.setdefault(category, [])
        hints.extend(Path(category).parts)
        hints.extend(_index_hints(vault, category))
        hints_by_category[category] = sorted(set(hint for hint in hints if hint))
    return hints_by_category


def _score_category(category: str, hints: list[str], blob: str) -> tuple[int, list[str]]:
    score = 0
    matches: list[str] = []
    category_tokens = Path(category).parts
    for token in category_tokens:
        if token.casefold() in blob:
            score += 2
            matches.append(token)
    for hint in hints:
        if hint.casefold() in blob:
            score += 4 if " " not in hint else 5
            matches.append(hint)
    return score, matches


def route(
    vault: Vault,
    *,
    cwd: str | None = None,
    paths: list[str] | None = None,
    request: str | None = None,
    category_hints: dict[str, list[str]] | None = None,
) -> RouteResult:
    paths = paths or []
    hints_by_category = build_category_hints(vault, category_hints or DEFAULT_CATEGORY_HINTS)
    blob = _text_blob(cwd, paths, request)
    best_category = "projects"
    best_score = 0
    best_matches: list[str] = []

    for category, hints in hints_by_category.items():
        score, matches = _score_category(category, hints, blob)
        if score > best_score:
            best_category = category
            best_score = score
            best_matches = matches

    if best_score == 0:
        read_set = ["CODEX.md"]
        reason = "No category hint matched; read root routing only."
        confidence = 0.2
    else:
        read_set = ["CODEX.md", f"{best_category}/index.md"]
        reason = "Matched " + ", ".join(sorted(set(best_matches)))
        confidence = min(0.95, 0.35 + best_score / 20)

    read_set = [path for path in read_set if vault.path(path).exists()]
    return RouteResult(best_category, confidence, reason, read_set)


def slugify(value: str) -> str:
    value = value.strip().casefold()
    value = re.sub(r"[^a-z0-9가-힣._-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "note"
