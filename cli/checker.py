from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from .vault import SECRET_RE, Vault
except ImportError:
    from vault import SECRET_RE, Vault

WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def _aliases(vault: Vault) -> dict[str, list[Path]]:
    by_name: dict[str, list[Path]] = {}
    for path in vault.markdown(include_archive=True):
        rel = vault.rel(path)
        stem_rel = rel[:-3] if rel.endswith(".md") else rel
        for alias in {rel, stem_rel, path.stem}:
            by_name.setdefault(alias.replace("\\", "/"), []).append(path)
    return by_name


def _resolve_link(vault: Vault, source: Path, target: str, aliases: dict[str, list[Path]]) -> Path | None:
    target = target.replace("\\", "/").strip()
    if not target:
        return source
    if target.endswith(".md"):
        target = target[:-3]

    candidates = [
        vault.root / f"{target}.md",
        source.parent / f"{target}.md",
    ]
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.exists() and (resolved == vault.root or vault.root in resolved.parents):
            return resolved

    matches = aliases.get(target) or aliases.get(Path(target).name)
    if matches and len(matches) == 1:
        return matches[0]
    return None


def check(vault: Vault) -> dict[str, Any]:
    aliases = _aliases(vault)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for path in vault.markdown():
        rel = vault.rel(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if SECRET_RE.search(line) and "<redacted>" not in line and "${" not in line:
                errors.append({"kind": "secret_candidate", "path": rel, "line": line_no})
            for match in WIKI_LINK_RE.finditer(line):
                target = match.group(1).replace("\\", "/").strip()
                if _resolve_link(vault, path, target, aliases) is None:
                    errors.append({"kind": "missing_or_ambiguous_link", "path": rel, "line": line_no, "target": target})
        if rel.startswith("daily/"):
            lines = [line for line in text.splitlines() if line.startswith("- [[")]
            duplicates = sorted({line for line in lines if lines.count(line) > 1})
            for line in duplicates:
                warnings.append({"kind": "duplicate_daily_link", "path": rel, "line": line})

    return {"errors": errors, "warnings": warnings, "error_count": len(errors), "warning_count": len(warnings)}
