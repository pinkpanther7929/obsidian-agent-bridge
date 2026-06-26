from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .config import default_config_path
except ImportError:
    from config import default_config_path


DEFAULT_OAB_STATE: dict[str, bool] = {
    "autoRecord": True,
    "memoryRecorderAgent": True,
    "includePrompt": True,
}


def config_path(path: str | None = None) -> Path:
    return Path(path).expanduser() if path else default_config_path()


def read_raw_config(path: str | None = None) -> tuple[Path, dict[str, Any]]:
    resolved = config_path(path)
    if not resolved.exists():
        return resolved, {}
    data = json.loads(resolved.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("config root must be an object")
    return resolved, data


def write_raw_config(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def status(path: str | None = None) -> dict[str, Any]:
    resolved, data = read_raw_config(path)
    state = dict(DEFAULT_OAB_STATE)
    for key in DEFAULT_OAB_STATE:
        value = data.get(key)
        if isinstance(value, bool):
            state[key] = value
    return {"configPath": str(resolved), **state}


def set_option(key: str, value: bool, path: str | None = None) -> dict[str, Any]:
    if key not in DEFAULT_OAB_STATE:
        raise ValueError(f"unknown OAB option: {key}")
    resolved, data = read_raw_config(path)
    data[key] = value
    write_raw_config(resolved, data)
    return status(str(resolved))


def set_auto_record(enabled: bool, path: str | None = None) -> dict[str, Any]:
    return set_option("autoRecord", enabled, path)
