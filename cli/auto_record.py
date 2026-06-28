from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import heapq
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

try:
    from .config import AppConfig, default_config_path
    from .recorder import record
    from .router import route
    from .vault import Vault
except ImportError:
    from config import AppConfig, default_config_path
    from recorder import record
    from router import route
    from vault import Vault


DEFAULT_STATE = Path.home() / ".obsidian-agent-bridge" / "auto-record-state.json"
DEFAULT_SESSION_ROOT = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"


def run_git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=str(repo),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def find_repo(start: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "-c", "core.quotepath=false", "rev-parse", "--show-toplevel"],
        cwd=str(start),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    root = proc.stdout.strip()
    return Path(root).resolve() if proc.returncode == 0 and root else None


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_git_path(path: str) -> str:
    path = path.strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path.strip('"').replace("\\", "/")


def should_ignore_path(path: str) -> bool:
    lowered = path.casefold()
    ignored_parts = {".git", ".gradle", ".idea", ".vs", ".vscode", "__pycache__", "node_modules"}
    parts = set(lowered.replace("\\", "/").split("/"))
    if parts.intersection(ignored_parts):
        return True
    return lowered.endswith((".pyc", ".pyo", ".tmp", ".log"))


def changed_files(name_only: str, untracked: str) -> list[str]:
    files: list[str] = []
    for text in (name_only, untracked):
        files.extend(normalize_git_path(line) for line in text.splitlines())
    return sorted({path for path in files if path and not should_ignore_path(path)})


def untracked_signature(repo: Path, untracked: str) -> str:
    lines: list[str] = []
    for raw_path in untracked.splitlines():
        rel_path = normalize_git_path(raw_path)
        if not rel_path or should_ignore_path(rel_path):
            continue
        path = repo / rel_path
        if not path.is_file():
            continue
        try:
            stat = path.stat()
            digest = ""
            if stat.st_size <= 1024 * 1024:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{rel_path}\t{stat.st_size}\t{stat.st_mtime_ns}\t{digest}")
        except OSError:
            lines.append(f"{rel_path}\tunreadable")
    return "\n".join(sorted(lines))


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _head_text(path: Path, line_count: int = 5) -> str:
    lines: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for _ in range(line_count):
                line = handle.readline()
                if not line:
                    break
                lines.append(line)
    except OSError:
        return ""
    return "".join(lines)


def _tail_lines(path: Path, max_bytes: int = 256 * 1024) -> list[str]:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - max_bytes))
            data = handle.read()
    except OSError:
        return []
    return data.decode("utf-8", errors="replace").splitlines()


def latest_session_prompt(session_root: Path, cwd: Path, limit: int = 180) -> str:
    if not session_root.exists():
        return ""
    try:
        candidates = heapq.nlargest(20, session_root.rglob("*.jsonl"), key=_mtime)
    except Exception:
        return ""

    cwd_text = str(cwd).replace("\\", "\\\\")
    for path in candidates:
        head = _head_text(path)
        if head and cwd_text not in head:
            continue
        for line in reversed(_tail_lines(path)[-250:]):
            try:
                event = json.loads(line)
            except Exception:
                continue
            payload = event.get("payload") or {}
            if event.get("type") != "message" or payload.get("role") != "user":
                continue
            content = payload.get("content")
            text = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = "\n".join(
                    str(item.get("text") or "")
                    for item in content
                    if isinstance(item, dict) and item.get("type") in {"input_text", "text"}
                )
            text = " ".join(text.split())
            if text:
                return text[:limit]
    return ""


def redact(text: str) -> str:
    redacted: list[str] = []
    for line in text.splitlines():
        lower = line.casefold()
        if any(token in lower for token in ("token", "password", "secret", "ticket", "webhook", "bearer")):
            redacted.append("[redacted sensitive-looking line]")
        else:
            redacted.append(line)
    return "\n".join(redacted)


def build_summary(repo: Path, branch: str, files: list[str], diff_stat: str, prompt: str) -> str:
    shown = "\n".join(f"- `{path}`" for path in files[:20])
    more = len(files) - 20
    if more > 0:
        shown += f"\n- ... {more} more"
    prompt_line = f"\nPrompt: {prompt}\n" if prompt else ""
    return redact(
        f"Codex auto-recorded work in `{repo}` on branch `{branch or 'unknown'}`.\n"
        f"{prompt_line}\nChanged files:\n{shown}\n\nDiff stat:\n```text\n{diff_stat or '(no diff stat)'}\n```"
    )


def title_from_prompt(prompt: str) -> str:
    text = " ".join(prompt.split())[:80].strip(" .,:;")
    return text.lower() if text else "codex auto record"


def auto_record(
    *,
    cwd: Path,
    config_path: str | None,
    vault_path: str | None,
    state_path: Path,
    session_root: Path,
    event: str,
    force: bool,
) -> dict[str, Any]:
    config = AppConfig.load(config_path)
    if not config.auto_record and not force:
        return {"status": "skipped", "reason": "oab_disabled"}

    repo = find_repo(cwd.resolve())
    if not repo:
        return {"status": "skipped", "reason": "not_git_repo"}

    name_only = run_git(repo, "diff", "--name-only")
    cached_name_only = run_git(repo, "diff", "--cached", "--name-only")
    untracked = run_git(repo, "ls-files", "--others", "--exclude-standard")
    files = changed_files("\n".join([name_only, cached_name_only]), untracked)
    if not files:
        return {"status": "skipped", "reason": "no_changes", "repo": str(repo)}

    diff_stat = run_git(repo, "diff", "--stat")
    cached_stat = run_git(repo, "diff", "--cached", "--stat")
    if cached_stat:
        diff_stat = (diff_stat + "\n" if diff_stat else "") + cached_stat
    if untracked:
        count = len([line for line in untracked.splitlines() if line.strip() and not should_ignore_path(line)])
        if count:
            diff_stat = (diff_stat + "\n" if diff_stat else "") + f"Untracked files: {count}"

    branch = run_git(repo, "branch", "--show-current")
    prompt = latest_session_prompt(session_root, repo) if config.include_prompt else ""
    signature_text = "\n".join(
        [str(repo), event, name_only, cached_name_only, untracked, untracked_signature(repo, untracked), diff_stat]
    )
    signature = hashlib.sha256(signature_text.encode("utf-8", errors="replace")).hexdigest()
    state = load_json(state_path, {})
    repo_key = str(repo).casefold()
    if not force and state.get(repo_key) == signature:
        return {"status": "skipped", "reason": "duplicate", "repo": str(repo)}

    vault = Vault.open(vault_path or config.vault)
    routed = route(
        vault,
        cwd=str(repo),
        paths=files,
        request=prompt or f"Codex auto record {repo.name}",
        category_hints=config.category_hints,
        language=config.language,
    )
    summary = build_summary(repo, branch, files, diff_stat, prompt)
    result = record(
        vault,
        category=routed.category,
        title=title_from_prompt(prompt),
        summary=summary,
        date=dt.date.today().isoformat(),
        daily_folder=config.daily_folder,
        history_template=config.history_template,
        language=config.language,
    )

    state[repo_key] = signature
    save_json(state_path, state)
    return {
        "status": "recorded",
        "event": event,
        "repo": str(repo),
        "category": routed.category,
        "confidence": routed.confidence,
        "result": asdict(result),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automatically record Codex git work into Obsidian.")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--config")
    parser.add_argument("--vault")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--session-root", type=Path, default=DEFAULT_SESSION_ROOT)
    parser.add_argument("--event", default="turn-ended")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = auto_record(
            cwd=args.cwd,
            config_path=args.config,
            vault_path=args.vault,
            state_path=args.state,
            session_root=args.session_root,
            event=args.event,
            force=args.force,
        )
    except Exception as exc:
        result = {"status": "error", "error": str(exc)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result)
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
