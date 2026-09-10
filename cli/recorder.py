from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

try:
    from .i18n import message
    from .router import slugify
    from .vault import Vault, VaultError, assert_no_secrets
except ImportError:
    from i18n import message
    from router import slugify
    from vault import Vault, VaultError, assert_no_secrets


@dataclass(frozen=True)
class RecordResult:
    note_path: str
    daily_path: str
    daily_added: bool
    dry_run: bool
    daily_link: str
    note_text: str


def normalize_category(category: str, *, language: str = "en") -> str:
    category = category.strip().replace("\\", "/").strip("/")
    if category.startswith("projects/"):
        return category
    parts = category.split("/")
    if len(parts) == 2:
        return f"projects/{parts[0]}/{parts[1]}"
    raise VaultError(message(language, "category_shape"))


def record(
    vault: Vault,
    *,
    category: str,
    title: str,
    summary: str,
    date: str | None = None,
    daily_folder: str = "daily",
    history_template: str = "# {date} {title}\n\n{summary}\n",
    language: str = "en",
    dry_run: bool = False,
) -> RecordResult:
    day = date or dt.date.today().isoformat()
    category_path = normalize_category(category, language=language)
    index_path = vault.path(f"{category_path}/index.md")
    if not index_path.exists():
        raise VaultError(f"Category index not found: {category_path}/index.md")

    slug = slugify(title)
    note_rel = f"{category_path}/history/{day}-{slug}.md"
    daily_rel = f"{daily_folder.strip().strip('/')}/{day}.md"
    link = f"- [[{note_rel[:-3]}|{category_path.replace('projects/', '')}: {title}]]"
    try:
        text = history_template.format(
            category=category_path,
            date=day,
            summary=summary.strip(),
            title=title,
        )
    except KeyError as exc:
        raise VaultError(message(language, "unknown_placeholder", name=exc.args[0])) from exc
    assert_no_secrets(text)

    if dry_run:
        return RecordResult(note_rel, daily_rel, False, True, link, text.rstrip() + "\n")

    vault.write_text(note_rel, text)
    daily_added = vault.append_unique_line(daily_rel, link)
    return RecordResult(note_rel, daily_rel, daily_added, False, link, text.rstrip() + "\n")


# Decision documents (ADR / PRD). Modeled on "AI 에이전트 시대, 결정을 기록하고 강제하는 법":
# an ADR carries the rule, why, how it is enforced, where it applies, and examples.
# A PRD carries why, problem, goal, and the user journey. Both live under
# {category}/decisions/ and are linked from the category index so that they can be
# found — what cannot be found cannot be enforced.
DECISION_FIELDS: dict[str, list[tuple[str, bool]]] = {
    # (field, required)
    "adr": [("decision", True), ("why", True), ("enforce", True), ("scope", False), ("examples", False), ("related", False)],
    "prd": [("why", True), ("problem", True), ("goal", True), ("journey", False), ("related", False)],
}

DECISION_HEADINGS = {
    "en": {
        "decision": "Decision",
        "why": "Why",
        "enforce": "How to enforce",
        "scope": "Scope",
        "examples": "Examples",
        "journey": "User journey",
        "problem": "Problem",
        "goal": "Goal",
        "related": "Related",
    },
    "ko": {
        "decision": "결정 (Decision)",
        "why": "이유 (Why)",
        "enforce": "강제 방법 (How to enforce)",
        "scope": "적용 범위 (Scope)",
        "examples": "예시 (Examples)",
        "journey": "사용자 여정 (Journey)",
        "problem": "문제 (Problem)",
        "goal": "목표 (Goal)",
        "related": "관련 (Related)",
    },
}


@dataclass(frozen=True)
class DecisionResult:
    note_path: str
    index_path: str
    index_added: bool
    daily_path: str
    daily_added: bool
    dry_run: bool
    note_text: str


def record_decision(
    vault: Vault,
    *,
    category: str,
    kind: str,
    title: str,
    fields: dict[str, str],
    status: str = "accepted",
    date: str | None = None,
    daily_folder: str = "daily",
    language: str = "en",
    dry_run: bool = False,
) -> DecisionResult:
    kind = kind.strip().casefold()
    if kind not in DECISION_FIELDS:
        raise VaultError(f"kind must be one of: {', '.join(DECISION_FIELDS)}")
    spec = DECISION_FIELDS[kind]
    known = {name for name, _ in spec}
    unknown = sorted(set(fields) - known)
    if unknown:
        raise VaultError(f"Unknown {kind} field(s): {', '.join(unknown)}. Allowed: {', '.join(known)}")
    missing = [name for name, required in spec if required and not (fields.get(name) or "").strip()]
    if missing:
        raise VaultError(f"Missing required {kind} field(s): {', '.join(missing)}")

    day = date or dt.date.today().isoformat()
    category_path = normalize_category(category, language=language)
    index_rel = f"{category_path}/index.md"
    if not vault.path(index_rel).exists():
        raise VaultError(f"Category index not found: {index_rel}")

    slug = slugify(title)
    note_rel = f"{category_path}/decisions/{day}-{kind}-{slug}.md"
    daily_rel = f"{daily_folder.strip().strip('/')}/{day}.md"
    label = f"{kind.upper()}: {title}"
    index_line = f"- [[{note_rel[:-3]}|{label}]]"
    daily_line = f"- [[{note_rel[:-3]}|{category_path.replace('projects/', '')}: {label}]]"

    headings = DECISION_HEADINGS.get(language, DECISION_HEADINGS["en"])
    lines = [
        "---",
        f"type: {kind}",
        f"status: {status.strip() or 'accepted'}",
        f"date: {day}",
        f"category: {category_path}",
        f"tags: [{kind}, decision]",
        "---",
        f"# {label}",
        "",
    ]
    for name, _ in spec:
        value = (fields.get(name) or "").strip()
        if not value:
            continue
        lines += [f"## {headings[name]}", value, ""]
    text = "\n".join(lines).rstrip() + "\n"
    assert_no_secrets(text)

    if dry_run:
        return DecisionResult(note_rel, index_rel, False, daily_rel, False, True, text)

    vault.write_text(note_rel, text)
    index_added = vault.append_unique_line(index_rel, index_line)
    daily_added = vault.append_unique_line(daily_rel, daily_line)
    return DecisionResult(note_rel, index_rel, index_added, daily_rel, daily_added, False, text)
