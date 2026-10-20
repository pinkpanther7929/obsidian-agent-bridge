from __future__ import annotations

# A handoff is the single, overwritten "where are we" note an agent reads first when it
# picks up work another model started. It is capped in size so switching models stays cheap;
# history belongs in obs_record notes, rules in obs_decision.

from dataclasses import dataclass
from datetime import datetime

try:
    from .recorder import normalize_category
    from .vault import Vault, VaultError, assert_no_secrets
except ImportError:
    from recorder import normalize_category
    from vault import Vault, VaultError, assert_no_secrets

MAX_CHARS = 4000
FIELDS = {
    "goal": "Goal",
    "state": "State",
    "next": "Next",
    "files": "Files",
    "decisions": "Decisions",
    "blockers": "Blockers / failed attempts",
}
REQUIRED = ("goal", "state", "next")


@dataclass(frozen=True)
class HandoffResult:
    path: str
    exists: bool
    chars: int
    text: str = ""


def handoff_rel(category: str, *, language: str = "en") -> str:
    return f"{normalize_category(category, language=language)}/handoff.md"


def read_handoff(vault: Vault, *, category: str, language: str = "en") -> HandoffResult:
    rel = handoff_rel(category, language=language)
    if not vault.path(rel).exists():
        return HandoffResult(rel, False, 0)
    text = vault.read_text(rel)
    return HandoffResult(rel, True, len(text), text)


def write_handoff(
    vault: Vault,
    *,
    category: str,
    fields: dict[str, str],
    by: str = "agent",
    language: str = "en",
    dry_run: bool = False,
) -> HandoffResult:
    unknown = sorted(set(fields) - set(FIELDS))
    if unknown:
        raise VaultError(f"Unknown handoff fields: {', '.join(unknown)} (allowed: {', '.join(FIELDS)})")
    missing = [name for name in REQUIRED if not (fields.get(name) or "").strip()]
    if missing:
        raise VaultError(f"Missing handoff fields: {', '.join(missing)}")

    rel = handoff_rel(category, language=language)
    if not vault.path(rel.rsplit("/", 1)[0] + "/index.md").exists():
        raise VaultError(f"Category index not found: {rel.rsplit('/', 1)[0]}/index.md")

    sections = [
        f"## {title}\n{fields[name].strip()}"
        for name, title in FIELDS.items()
        if (fields.get(name) or "").strip()
    ]
    stamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
    text = f"---\nupdated: {stamp}\nby: {by}\n---\n# Handoff\n\n" + "\n\n".join(sections)
    if len(text) > MAX_CHARS:
        raise VaultError(
            f"Handoff is {len(text)} chars, limit {MAX_CHARS}. Keep only current state; "
            "move history to obs_record and rules to obs_decision."
        )
    assert_no_secrets(text)
    if not dry_run:
        vault.write_text(rel, text)
    return HandoffResult(rel, True, len(text), text if dry_run else "")
