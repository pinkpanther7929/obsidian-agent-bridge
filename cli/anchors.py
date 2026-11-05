"""Code Anchors: a small table in a category index.md that points an agent at real code.

```
## Code Anchors
Root: D:\\devops-infra.main
| Component | Location | Symbol / role |
| --- | --- | --- |
| wiki-relay LLM call | docker-compose/wiki-relay/app.py:395 | `call_qwen` sends requests to Strata |
```

`parse_anchors` feeds obs_route (so an agent can jump straight to the code without a search subagent).
`verify_anchors` / `apply_fixes` detect drift (file moved or deleted, symbol moved to another line) and can
rewrite the line numbers. Drift is only reported; nothing is changed unless the caller asks to apply.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SECTION_RE = re.compile(r"^##\s+Code Anchors\s*$", re.IGNORECASE | re.MULTILINE)
ROOT_RE = re.compile(r"^\s*root\s*[:=]\s*`?([^`\n]+?)`?\s*$", re.IGNORECASE | re.MULTILINE)
LOCATION_RE = re.compile(r"^`?(?P<path>.+?):(?P<line>\d+)(?:-\d+)?`?$")
BACKTICK_RE = re.compile(r"`([^`]+)`")
DEFINITION_RE = re.compile(r"\b(def|class|function|func|interface|struct|enum|void|public|private|static|const|let|var|type)\b")
MAX_ANCHORS = 15


def _section(text: str) -> tuple[str, int] | None:
    match = SECTION_RE.search(text)
    if not match:
        return None
    start = match.end()
    following = re.search(r"^##\s", text[start:], re.MULTILINE)
    end = start + following.start() if following else len(text)
    return text[start:end], start


def parse_anchors(text: str, limit: int = MAX_ANCHORS) -> tuple[str, list[dict[str, Any]]]:
    """Return (root, anchors). Each anchor: component, path, line, symbol, note, raw (the original row)."""
    found = _section(text)
    if not found:
        return "", []
    body, _ = found
    root_match = ROOT_RE.search(body)
    root = root_match.group(1).strip() if root_match else ""
    anchors: list[dict[str, Any]] = []
    for raw in body.splitlines():
        if not raw.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: "):
            continue
        location = LOCATION_RE.match(cells[1])
        if not location:
            continue
        note = cells[2] if len(cells) > 2 else ""
        symbols = BACKTICK_RE.findall(note)
        anchors.append({
            "component": cells[0],
            "path": location.group("path").strip().strip("`"),
            "line": int(location.group("line")),
            "symbol": symbols[0] if symbols else "",
            "note": note,
            "raw": raw,
        })
        if len(anchors) >= limit:
            break
    return root, anchors


def compact(anchors: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Small shape for obs_route responses (keeps the payload around 300 tokens)."""
    return [{"component": a["component"], "location": f'{a["path"]}:{a["line"]}', "note": a["note"][:80]} for a in anchors]


def _resolve(root: str, path: str) -> Path | None:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return Path(root) / candidate if root else None


def _find_symbol_line(lines: list[str], symbol: str, near: int) -> int | None:
    word = re.compile(r"(?<![\w])" + re.escape(symbol) + r"(?![\w])")
    hits = [i + 1 for i, line in enumerate(lines) if word.search(line)]
    if not hits:
        return None
    definitions = [n for n in hits if DEFINITION_RE.search(lines[n - 1]) or re.search(re.escape(symbol) + r"\s*[=(:]", lines[n - 1])]
    pool = definitions or hits
    return min(pool, key=lambda n: abs(n - near))


def verify_anchors(note_rel: str, text: str) -> list[dict[str, Any]]:
    """Check every anchor of one note against the code on disk. Empty list means all anchors are accurate."""
    root, anchors = parse_anchors(text, limit=10_000)
    findings: list[dict[str, Any]] = []
    for anchor in anchors:
        base = {"path": note_rel, "component": anchor["component"], "anchor": f'{anchor["path"]}:{anchor["line"]}'}
        target = _resolve(root, anchor["path"])
        if target is None:
            findings.append({**base, "kind": "anchor_root_unknown"})
            continue
        if not target.is_file():
            findings.append({**base, "kind": "anchor_file_missing", "resolved": str(target)})
            continue
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        symbol = anchor["symbol"]
        if anchor["line"] > len(lines):
            kind = "anchor_line_out_of_range"
        elif not symbol or re.search(r"(?<![\w])" + re.escape(symbol) + r"(?![\w])", lines[anchor["line"] - 1]):
            continue
        else:
            kind = "anchor_drift"
        moved = _find_symbol_line(lines, symbol, anchor["line"]) if symbol else None
        if moved is None:
            findings.append({**base, "kind": "anchor_symbol_missing" if symbol else kind, "symbol": symbol})
        else:
            findings.append({**base, "kind": kind, "symbol": symbol, "new_line": moved, "raw": anchor["raw"],
                             "old_path": anchor["path"], "old_line": anchor["line"]})
    return findings


def apply_fixes(text: str, findings: list[dict[str, Any]]) -> tuple[str, int]:
    """Rewrite `path:line` to the found line for drift findings. Returns (new_text, changed_rows)."""
    changed = 0
    for finding in findings:
        if "new_line" not in finding:
            continue
        old = f'{finding["old_path"]}:{finding["old_line"]}'
        row = finding["raw"]
        new_row = row.replace(old, f'{finding["old_path"]}:{finding["new_line"]}', 1)
        if new_row != row and row in text:
            text = text.replace(row, new_row, 1)
            changed += 1
    return text, changed
