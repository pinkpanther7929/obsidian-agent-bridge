from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import Any, Callable

from cli.checker import check
from cli.config import AppConfig
from cli.reader import read_note, search_notes
from cli.recorder import record
from cli.router import route
from cli.vault import Vault, VaultError

PROTOCOL_VERSION = "2024-11-05"


def _json_default(value: object) -> object:
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


def _load_vault(args: dict[str, Any]) -> tuple[AppConfig, Vault]:
    config = AppConfig.load(args.get("config"))
    vault = Vault.open(args.get("vault") or config.vault)
    return config, vault


def _text(data: object, *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)}],
        "isError": is_error,
    }


def tool_route(args: dict[str, Any]) -> dict[str, Any]:
    config, vault = _load_vault(args)
    result = route(
        vault,
        cwd=args.get("cwd"),
        paths=args.get("paths") or [],
        request=args.get("request"),
        category_hints=config.category_hints,
        language=config.language,
    )
    return _text(asdict(result))


def tool_read(args: dict[str, Any]) -> dict[str, Any]:
    _, vault = _load_vault(args)
    result = read_note(
        vault,
        path=_required(args, "path"),
        start=int(args.get("start") or 1),
        lines=args.get("lines"),
    )
    return _text(asdict(result))


def tool_search(args: dict[str, Any]) -> dict[str, Any]:
    _, vault = _load_vault(args)
    hits = search_notes(
        vault,
        query=_required(args, "query"),
        path_prefix=args.get("pathPrefix"),
        limit=int(args.get("limit") or 50),
        regex=bool(args.get("regex")),
        case_sensitive=bool(args.get("caseSensitive")),
    )
    return _text({"query": args.get("query"), "count": len(hits), "results": [asdict(hit) for hit in hits]})


def tool_record(args: dict[str, Any]) -> dict[str, Any]:
    config, vault = _load_vault(args)
    result = record(
        vault,
        category=_required(args, "category"),
        title=_required(args, "title"),
        summary=_required(args, "summary"),
        date=args.get("date"),
        daily_folder=config.daily_folder,
        history_template=config.history_template,
        language=config.language,
        dry_run=bool(args.get("dryRun")),
    )
    return _text(asdict(result))


def tool_check(args: dict[str, Any]) -> dict[str, Any]:
    _, vault = _load_vault(args)
    return _text(check(vault))


def _required(args: dict[str, Any], key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing required argument: {key}")
    return value


TOOLS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "obs_route": tool_route,
    "obs_read": tool_read,
    "obs_search": tool_search,
    "obs_record": tool_record,
    "obs_check": tool_check,
}


TOOL_DEFINITIONS = [
    {
        "name": "obs_route",
        "description": "Route a task to an Obsidian project/category and return minimal notes to read.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cwd": {"type": "string"},
                "paths": {"type": "array", "items": {"type": "string"}},
                "request": {"type": "string"},
                "config": {"type": "string"},
                "vault": {"type": "string"},
            },
        },
    },
    {
        "name": "obs_read",
        "description": "Read one vault-relative note.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start": {"type": "integer"},
                "lines": {"type": "integer"},
                "config": {"type": "string"},
                "vault": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "obs_search",
        "description": "Search non-archive Obsidian Markdown notes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "pathPrefix": {"type": "string"},
                "limit": {"type": "integer"},
                "regex": {"type": "boolean"},
                "caseSensitive": {"type": "boolean"},
                "config": {"type": "string"},
                "vault": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "obs_record",
        "description": "Create a category history note and append a deduplicated daily backlink.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "date": {"type": "string"},
                "dryRun": {"type": "boolean"},
                "config": {"type": "string"},
                "vault": {"type": "string"},
            },
            "required": ["category", "title", "summary"],
        },
    },
    {
        "name": "obs_check",
        "description": "Check the vault for missing/ambiguous links, duplicate daily backlinks, and secret-looking content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "config": {"type": "string"},
                "vault": {"type": "string"},
            },
        },
    },
]


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    req_id = request.get("id")
    if method == "notifications/initialized":
        return None
    try:
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "obsidian-agent-bridge", "version": "0.1.0"},
            }
        elif method == "tools/list":
            result = {"tools": TOOL_DEFINITIONS}
        elif method == "tools/call":
            params = request.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if name not in TOOLS:
                raise ValueError(f"Unknown tool: {name}")
            result = TOOLS[name](arguments)
        elif method == "ping":
            result = {}
        else:
            raise ValueError(f"Unsupported method: {method}")
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    except (ValueError, VaultError, OSError, json.JSONDecodeError) as exc:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(exc)}}


def main() -> int:
    for line in sys.stdin:
        line = line.lstrip("\ufeff")
        first_json = min([pos for pos in (line.find("{"), line.find("[")) if pos >= 0], default=-1)
        if first_json > 0:
            line = line[first_json:]
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
        else:
            response = handle(request)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
