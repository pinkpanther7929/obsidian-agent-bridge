from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CATEGORY_HINTS: dict[str, list[str]] = {
    "projects/engineering/backend": ["backend", "api", "auth", "database", "session"],
    "projects/engineering/frontend": ["frontend", "ui", "web", "react", "css"],
    "projects/engineering/build": ["build", "ci", "pipeline", "test", "failure"],
    "projects/operations/deploy": ["deploy", "release", "kubernetes", "docker", "argocd"],
    "projects/ai/agents": ["agent", "codex", "claude", "mcp", "tool", "memory"],
    "projects/ai/local-models": ["local llm", "llm", "model", "inference", "token"],
}

DEFAULT_HISTORY_TEMPLATES = {
    "en": "# {date} {title}\n\n{summary}\n",
    "ko": "# {date} {title}\n\n{summary}\n",
}


def default_config_path() -> Path:
    env_path = os.environ.get("OBS_AGENT_CONFIG")
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".obsidian-agent-bridge" / "config.json"


@dataclass(frozen=True)
class AppConfig:
    vault: str | None = None
    language: str = "en"
    daily_folder: str = "daily"
    history_template: str = "# {date} {title}\n\n{summary}\n"
    category_hints: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_HINTS))

    @classmethod
    def load(cls, path: str | None = None) -> "AppConfig":
        config_path = Path(path).expanduser() if path else default_config_path()
        if not config_path.exists():
            return cls()
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config root must be an object")
        language = _language(data.get("language"))
        return cls(
            vault=_optional_str(data.get("vault")),
            language=language,
            daily_folder=_str_value(data.get("dailyFolder"), "dailyFolder", default="daily"),
            history_template=_str_value(
                data.get("historyTemplate"),
                "historyTemplate",
                default=DEFAULT_HISTORY_TEMPLATES[language],
            ),
            category_hints=_category_hints(data.get("categoryHints")),
        )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("vault must be a string")
    return value


def _str_value(value: Any, name: str, *, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip().strip("/")


def _language(value: Any) -> str:
    if value is None:
        return "en"
    if not isinstance(value, str):
        raise ValueError("language must be a string")
    normalized = value.strip().casefold()
    if normalized in {"en", "english"}:
        return "en"
    if normalized in {"ko", "kr", "kor", "korean", "\ud55c\uad6d\uc5b4"}:
        return "ko"
    raise ValueError("language must be 'en' or 'ko'")


def _category_hints(value: Any) -> dict[str, list[str]]:
    if value is None:
        return dict(DEFAULT_CATEGORY_HINTS)
    if not isinstance(value, dict):
        raise ValueError("categoryHints must be an object")
    result: dict[str, list[str]] = {}
    for category, hints in value.items():
        if not isinstance(category, str) or not category.strip():
            raise ValueError("categoryHints keys must be non-empty strings")
        if not isinstance(hints, list) or not all(isinstance(item, str) for item in hints):
            raise ValueError(f"categoryHints.{category} must be a string array")
        result[category.strip().replace("\\", "/").strip("/")] = [hint.strip() for hint in hints if hint.strip()]
    return result
