from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

if __package__ in {None, ""}:
    from checker import check
    from config import AppConfig
    from oab import set_auto_record, set_option, status
    from reader import read_note, search_notes
    from recorder import record
    from router import route
    from vault import Vault, VaultError
else:
    from .checker import check
    from .config import AppConfig
    from .oab import set_auto_record, set_option, status
    from .reader import read_note, search_notes
    from .recorder import record
    from .router import route
    from .vault import Vault, VaultError

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def emit(data: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        if isinstance(data, dict):
            for key, value in data.items():
                print(f"{key}: {value}")
        else:
            print(data)


def cmd_route(args: argparse.Namespace) -> int:
    config = AppConfig.load(args.config)
    vault = Vault.open(args.vault or config.vault)
    result = route(
        vault,
        cwd=args.cwd,
        paths=args.path or [],
        request=args.request,
        category_hints=config.category_hints,
        language=config.language,
    )
    emit(asdict(result), args.json)
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    config = AppConfig.load(args.config)
    vault = Vault.open(args.vault or config.vault)
    result = record(
        vault,
        category=args.category,
        title=args.title,
        summary=args.summary,
        date=args.date,
        daily_folder=config.daily_folder,
        history_template=config.history_template,
        language=config.language,
        dry_run=args.dry_run,
    )
    emit(asdict(result), args.json)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    config = AppConfig.load(args.config)
    vault = Vault.open(args.vault or config.vault)
    result = check(vault)
    emit(result, args.json)
    return 1 if result["error_count"] else 0


def cmd_read(args: argparse.Namespace) -> int:
    config = AppConfig.load(args.config)
    vault = Vault.open(args.vault or config.vault)
    result = read_note(vault, path=args.path, start=args.start, lines=args.lines)
    emit(asdict(result), args.json)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    config = AppConfig.load(args.config)
    vault = Vault.open(args.vault or config.vault)
    hits = search_notes(
        vault,
        query=args.query,
        path_prefix=args.path_prefix,
        limit=args.limit,
        regex=args.regex,
        case_sensitive=args.case_sensitive,
    )
    emit({"query": args.query, "count": len(hits), "results": [asdict(hit) for hit in hits]}, args.json)
    return 0


def cmd_oab(args: argparse.Namespace) -> int:
    if args.action == "status":
        result = status(args.config)
    elif args.action == "on":
        result = set_auto_record(True, args.config)
    elif args.action == "off":
        result = set_auto_record(False, args.config)
    elif args.action == "set":
        result = set_option(args.key, args.value, args.config)
    else:
        raise ValueError(f"unknown OAB action: {args.action}")
    emit(result, args.json)
    return 0


def parse_bool(value: str) -> bool:
    lowered = value.casefold()
    if lowered in {"1", "true", "yes", "y", "on", "enable", "enabled"}:
        return True
    if lowered in {"0", "false", "no", "n", "off", "disable", "disabled"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean: {value}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Obsidian memory bridge for coding agents.")
    parser.add_argument("--vault", help="Vault root. Defaults to OBSIDIAN_VAULT_PATH or the built-in user vault.")
    parser.add_argument("--config", help="Config JSON path. Defaults to OBS_AGENT_CONFIG or ~/.obsidian-agent-bridge/config.json.")
    sub = parser.add_subparsers(dest="command", required=True)

    route_cmd = sub.add_parser("route", help="Suggest category and minimal notes for a task.")
    route_cmd.add_argument("--cwd")
    route_cmd.add_argument("--path", action="append", help="Changed/open file path. Can be repeated.")
    route_cmd.add_argument("--request", help="User request or task summary.")
    route_cmd.add_argument("--json", action="store_true")
    route_cmd.set_defaults(func=cmd_route)

    record_cmd = sub.add_parser("record", help="Create a history note and append a daily backlink.")
    record_cmd.add_argument("--category", required=True)
    record_cmd.add_argument("--title", required=True)
    record_cmd.add_argument("--summary", required=True)
    record_cmd.add_argument("--date")
    record_cmd.add_argument("--dry-run", action="store_true")
    record_cmd.add_argument("--json", action="store_true")
    record_cmd.set_defaults(func=cmd_record)

    check_cmd = sub.add_parser("check", help="Check links, daily duplicates, and secret-looking content.")
    check_cmd.add_argument("--json", action="store_true")
    check_cmd.set_defaults(func=cmd_check)

    read_cmd = sub.add_parser("read", help="Read one note by vault-relative path.")
    read_cmd.add_argument("--path", required=True)
    read_cmd.add_argument("--start", type=int, default=1)
    read_cmd.add_argument("--lines", type=int)
    read_cmd.add_argument("--json", action="store_true")
    read_cmd.set_defaults(func=cmd_read)

    search_cmd = sub.add_parser("search", help="Search non-archive Markdown notes.")
    search_cmd.add_argument("--query", required=True)
    search_cmd.add_argument("--path-prefix")
    search_cmd.add_argument("--limit", type=int, default=50)
    search_cmd.add_argument("--regex", action="store_true")
    search_cmd.add_argument("--case-sensitive", action="store_true")
    search_cmd.add_argument("--json", action="store_true")
    search_cmd.set_defaults(func=cmd_search)

    oab_cmd = sub.add_parser("oab", help="Control automatic Obsidian memory behavior.")
    oab_sub = oab_cmd.add_subparsers(dest="action", required=True)

    oab_status = oab_sub.add_parser("status", help="Show OAB auto-memory state.")
    oab_status.add_argument("--json", action="store_true")
    oab_status.set_defaults(func=cmd_oab)

    oab_on = oab_sub.add_parser("on", help="Enable OAB auto-memory.")
    oab_on.add_argument("--json", action="store_true")
    oab_on.set_defaults(func=cmd_oab)

    oab_off = oab_sub.add_parser("off", help="Disable OAB auto-memory.")
    oab_off.add_argument("--json", action="store_true")
    oab_off.set_defaults(func=cmd_oab)

    oab_set = oab_sub.add_parser("set", help="Set one OAB boolean option.")
    oab_set.add_argument("key", choices=["autoRecord", "memoryRecorderAgent", "includePrompt"])
    oab_set.add_argument("value", type=parse_bool)
    oab_set.add_argument("--json", action="store_true")
    oab_set.set_defaults(func=cmd_oab)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (VaultError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
