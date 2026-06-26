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
