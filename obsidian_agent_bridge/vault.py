from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_VAULT = Path(os.environ.get("OBSIDIAN_VAULT_PATH", str(Path.home() / "Documents" / "Obsidian Vault")))
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|api[_-]?token|password|passwd|secret|bearer)\s*[:=]\s*[^\s<]+"
)


class VaultError(Exception):
    pass


@dataclass(frozen=True)
class Vault:
    root: Path

    @classmethod
    def open(cls, path: str | None = None) -> "Vault":
        root = Path(path).expanduser() if path else DEFAULT_VAULT
        root = root.resolve()
        if not root.exists() or not root.is_dir():
            raise VaultError(f"Vault not found: {root}")
        return cls(root)

    def path(self, rel: str | Path, *, create_parent: bool = False) -> Path:
        candidate = Path(rel)
        path = candidate.resolve() if candidate.is_absolute() else (self.root / candidate).resolve()
        if path != self.root and self.root not in path.parents:
            raise VaultError(f"Path escapes vault: {path}")
        if create_parent:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def rel(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def read_text(self, rel: str | Path) -> str:
        path = self.path(rel)
        if not path.exists():
            raise VaultError(f"Note not found: {rel}")
        return path.read_text(encoding="utf-8", errors="replace")

    def write_text(self, rel: str | Path, text: str) -> str:
        path = self.path(rel, create_parent=True)
        path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")
        return self.rel(path)

    def append_unique_line(self, rel: str | Path, line: str) -> bool:
        path = self.path(rel, create_parent=True)
        existing = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
        if line in existing:
            return False
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            if existing:
                handle.write("\n")
            handle.write(line.rstrip() + "\n")
        return True

    def markdown(self, *, include_archive: bool = False, prefix: str | None = None) -> Iterable[Path]:
        root = self.path(prefix) if prefix else self.root
        skip = {".git", ".obsidian", ".trash"}
        for path in root.rglob("*.md"):
            parts = path.relative_to(self.root).parts
            if any(part in skip for part in parts):
                continue
            if not include_archive and any(part.casefold() == "archive" for part in parts):
                continue
            yield path


def assert_no_secrets(text: str) -> None:
    for line_no, line in enumerate(text.splitlines(), start=1):
        if SECRET_RE.search(line) and "<redacted>" not in line and "${" not in line:
            raise VaultError(f"Secret-looking content at line {line_no}")
