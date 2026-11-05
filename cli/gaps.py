"""Routing gaps: remember queries that found nothing, so category hints can be improved later.

obs_route (no category matched) and obs_search (zero hits) append one JSON line to `<vault>/.oab/routing-gaps.jsonl`.
`obs_check --routing-gaps` summarises the most frequent words so a human can add them to a category's index.md.
Logging is best effort and never raises; set OBS_ROUTING_GAPS=off to disable it.
"""
from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from typing import Any

try:
    from .vault import Vault
except ImportError:
    from vault import Vault

LOG_REL = ".oab/routing-gaps.jsonl"
MAX_BYTES = 200_000
WORD_RE = re.compile(r"[A-Za-z0-9가-힣_-]{2,}")
IGNORE = {"the", "and", "for", "with", "this", "that", "what", "how", "please", "확인", "해줘", "관련", "작업", "진행", "해주세요"}


def log_gap(vault: Vault, kind: str, text: str | None, cwd: str | None = None) -> None:
    text = (text or "").strip()
    if not text or os.environ.get("OBS_ROUTING_GAPS", "").casefold() == "off":
        return
    try:
        path = vault.path(LOG_REL, create_parent=True)
        if path.exists() and path.stat().st_size > MAX_BYTES:
            return
        entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind, "text": text[:200], "cwd": (cwd or "")[:200]}
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        return


def report(vault: Vault, limit: int = 20) -> dict[str, Any]:
    path = vault.path(LOG_REL)
    if not path.exists():
        return {"entries": 0, "top_words": [], "recent": []}
    entries = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-2000:]:
        try:
            entries.append(json.loads(line))
        except ValueError:
            continue
    words: Counter[str] = Counter()
    for entry in entries:
        words.update({w.casefold() for w in WORD_RE.findall(entry.get("text", "")) if w.casefold() not in IGNORE})
    return {
        "entries": len(entries),
        "by_kind": dict(Counter(e.get("kind", "") for e in entries)),
        "top_words": [{"word": w, "count": c} for w, c in words.most_common(limit)],
        "recent": [{"ts": e.get("ts"), "kind": e.get("kind"), "text": e.get("text")} for e in entries[-5:]],
        "hint": f"Add frequent words to the matching category index.md ({LOG_REL} lists the raw queries).",
    }
