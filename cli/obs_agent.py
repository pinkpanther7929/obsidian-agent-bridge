from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

if __package__ in {None, ""}:
    from checker import check
    from recorder import record
    from router import route
    from vault import Vault, VaultError
else:
    from .checker import check
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
    vault = Vault.open(args.vault)
    result = route(vault, cwd=args.cwd, paths=args.path or [], request=args.request)
    emit(asdict(result), args.json)
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    vault = Vault.open(args.vault)
    result = record(
        vault,
        category=args.category,
        title=args.title,
        summary=args.summary,
        date=args.date,
        dry_run=args.dry_run,
    )
    emit(asdict(result), args.json)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    vault = Vault.open(args.vault)
    result = check(vault)
    emit(result, args.json)
    return 1 if result["error_count"] else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Obsidian memory bridge for coding agents.")
    parser.add_argument("--vault", help="Vault root. Defaults to OBSIDIAN_VAULT_PATH or the built-in user vault.")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
