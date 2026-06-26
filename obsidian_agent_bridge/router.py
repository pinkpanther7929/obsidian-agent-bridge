from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .vault import Vault

CATEGORY_HINTS: dict[str, list[str]] = {
    "projects/devops-infra/jenkins": ["jenkins", "pipeline", "build log", "failure", "slack user map"],
    "projects/devops-infra/local-llm": ["local llm", "llm", "mcp", "codex", "claude", "agent", "vs-token-safer", "token"],
    "projects/devops-infra/deploy-web": ["deploy-web", "deploy web", "callback", "frontend deploy"],
    "projects/devops-infra/monitoring": ["monitoring", "prometheus", "grafana", "alert"],
    "projects/devops-infra/logging": ["logging", "elk", "elastic", "kibana", "logstash"],
    "projects/devops-infra/kubernetes": ["kubernetes", "k8s", "pod", "pvc", "cluster"],
    "projects/devops-infra/argocd": ["argocd", "argo cd", "manifest", "sync"],
    "projects/devops-infra/docker-compose": ["docker-compose", "compose"],
    "projects/devops-infra/ftp-package": ["ftp", "package", "artifact"],
    "projects/UnrealEngine/ugs": ["ugs", "unrealgamesync"],
    "projects/UnrealEngine/gauntlet": ["gauntlet"],
    "projects/UnrealEngine/buildtool": ["ubt", "buildtool", "unreal build tool"],
}


@dataclass(frozen=True)
class RouteResult:
    category: str
    confidence: float
    reason: str
    read_set: list[str]


def _text_blob(cwd: str | None, paths: list[str], request: str | None) -> str:
    parts = [cwd or "", request or "", *paths]
    return " ".join(parts).replace("\\", "/").casefold()


def _score_category(category: str, blob: str) -> tuple[int, list[str]]:
    score = 0
    matches: list[str] = []
    category_tokens = Path(category).parts
    for token in category_tokens:
        if token.casefold() in blob:
            score += 2
            matches.append(token)
    for hint in CATEGORY_HINTS.get(category, []):
        if hint.casefold() in blob:
            score += 4 if " " not in hint else 5
            matches.append(hint)
    return score, matches


def route(vault: Vault, *, cwd: str | None = None, paths: list[str] | None = None, request: str | None = None) -> RouteResult:
    paths = paths or []
    blob = _text_blob(cwd, paths, request)
    best_category = "projects/devops-infra"
    best_score = 0
    best_matches: list[str] = []

    for category in CATEGORY_HINTS:
        score, matches = _score_category(category, blob)
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

