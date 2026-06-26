from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .router import slugify
from .vault import Vault, VaultError, assert_no_secrets


@dataclass(frozen=True)
class RecordResult:
    note_path: str
    daily_path: str
    daily_added: bool
    dry_run: bool


def normalize_category(category: str) -> str:
    category = category.strip().replace("\\", "/").strip("/")
    if category.startswith("projects/"):
        return category
    parts = category.split("/")
    if len(parts) == 2:
        return f"projects/{parts[0]}/{parts[1]}"
    raise VaultError("Category must look like 'devops-infra/local-llm' or 'projects/devops-infra/local-llm'")


def record(
    vault: Vault,
    *,
    category: str,
    title: str,
    summary: str,
    date: str | None = None,
    dry_run: bool = False,
) -> RecordResult:
    day = date or dt.date.today().isoformat()
    category_path = normalize_category(category)
    index_path = vault.path(f"{category_path}/index.md")
    if not index_path.exists():
        raise VaultError(f"Category index not found: {category_path}/index.md")

    slug = slugify(title)
    note_rel = f"{category_path}/history/{day}-{slug}.md"
    daily_rel = f"daily/{day}.md"
    link = f"- [[{note_rel[:-3]}|{category_path.replace('projects/', '')}: {title}]]"
    text = f"# {day} {title}\n\n{summary.strip()}\n"
    assert_no_secrets(text)

    if dry_run:
        return RecordResult(note_rel, daily_rel, False, True)

    vault.write_text(note_rel, text)
    daily_added = vault.append_unique_line(daily_rel, link)
    return RecordResult(note_rel, daily_rel, daily_added, False)

