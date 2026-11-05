from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from .anchors import apply_fixes, verify_anchors
    from .vault import SECRET_RE, Vault
except ImportError:
    from anchors import apply_fixes, verify_anchors
    from vault import SECRET_RE, Vault

WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#]+(?:#[^)]*)?)\)")


def _aliases(vault: Vault) -> dict[str, list[Path]]:
    by_name: dict[str, list[Path]] = {}
    for path in vault.markdown(include_archive=True):
        rel = vault.rel(path)
        stem_rel = rel[:-3] if rel.endswith(".md") else rel
        for alias in {rel, stem_rel, path.stem}:
            by_name.setdefault(alias.replace("\\", "/"), []).append(path)
    return by_name


def _resolve_link(vault: Vault, source: Path, target: str, aliases: dict[str, list[Path]]) -> str:
    target = target.replace("\\", "/").strip()
    if not target:
        return "ok"
    if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
        return "ok"
    target = target.split("#", 1)[0].strip()
    if not target:
        return "ok"
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
            return "ok"

    matches = aliases.get(target) or aliases.get(Path(target).name)
    if matches and len(matches) == 1:
        return "ok"
    if matches and len(matches) > 1:
        return "ambiguous_link"
    return "missing_link"


def _link_targets(line: str) -> list[str]:
    targets = [match.group(1) for match in WIKI_LINK_RE.finditer(line)]
    for match in MD_LINK_RE.finditer(line):
        target = match.group(1)
        if target.endswith(".md") or ".md#" in target or "/" in target:
            targets.append(target)
    return targets


def _frontmatter(text: str) -> dict[str, str]:
    """Flat `key: value` pairs from the leading --- block (enough for status / supersedes fields)."""
    nl = chr(10)
    if not text.startswith("---" + nl):
        return {}
    end = text.find(nl + "---", 3)
    if end < 0:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].split(nl):
        key, sep, value = line.partition(":")
        if sep:
            data[key.strip()] = value.strip()
    return data


def _retired_citations(texts: dict[str, str]) -> list[dict[str, Any]]:
    """Notes that still cite a superseded/deprecated decision as if it were current."""
    retired = {}
    for rel, text in texts.items():
        meta = _frontmatter(text)
        if "/decisions/" in rel and meta.get("status") in {"superseded", "deprecated"}:
            retired[rel[:-3]] = meta
    found: list[dict[str, Any]] = []
    for rel, text in texts.items():
        if rel.startswith("daily/") or rel.endswith("index.md") or rel[:-3] in retired:
            continue
        meta = _frontmatter(text)
        for target in sorted({t.replace(chr(92), "/").strip() for t in WIKI_LINK_RE.findall(text)}):
            target = target[:-3] if target.endswith(".md") else target
            old = retired.get(target)
            if old is None:
                continue
            # The decision that replaced it (and its own back-link) is expected to mention it.
            if target in meta.get("supersedes", "") or rel[:-3] in old.get("superseded_by", ""):
                continue
            found.append({"kind": "cites_retired_decision", "path": rel, "target": target, "status": old["status"],
                          "superseded_by": old.get("superseded_by", "")})
    return found


def check(vault: Vault, *, verify_code: bool = False, fix_anchors: bool = False, apply: bool = False) -> dict[str, Any]:
    aliases = _aliases(vault)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    texts: dict[str, str] = {}

    for path in vault.markdown():
        rel = vault.rel(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        texts[rel] = text
        for line_no, line in enumerate(text.splitlines(), start=1):
            if SECRET_RE.search(line) and "<redacted>" not in line and "${" not in line:
                errors.append({"kind": "secret_candidate", "path": rel, "line": line_no})
            for target in _link_targets(line):
                normalized = target.replace("\\", "/").strip()
                status = _resolve_link(vault, path, normalized, aliases)
                if status != "ok":
                    errors.append({"kind": status, "path": rel, "line": line_no, "target": normalized})
        if rel.startswith("daily/"):
            lines = [line for line in text.splitlines() if line.startswith("- [[")]
            duplicates = sorted({line for line in lines if lines.count(line) > 1})
            for line in duplicates:
                warnings.append({"kind": "duplicate_daily_link", "path": rel, "line": line})

    warnings.extend(_retired_citations(texts))
    extra: dict[str, Any] = {}
    if verify_code or fix_anchors:
        fixes: list[dict[str, Any]] = []
        fixed_rows = 0
        for rel, text in texts.items():
            findings = verify_anchors(rel, text) if "Code Anchors" in text else []
            warnings.extend({k: v for k, v in f.items() if k not in {"raw", "old_path", "old_line"}} for f in findings)
            movable = [f for f in findings if "new_line" in f]
            if fix_anchors and movable:
                new_text, changed = apply_fixes(text, movable)
                fixes.extend({"path": rel, "anchor": f["anchor"], "new_line": f["new_line"]} for f in movable)
                if apply and changed:
                    vault.write_text(rel, new_text)
                    fixed_rows += changed
        if fix_anchors:
            extra = {"fix_preview" if not apply else "fixed_anchors": fixes if not apply else fixed_rows, "applied": apply}
    return {"errors": errors, "warnings": warnings, "error_count": len(errors), "warning_count": len(warnings), **extra}
