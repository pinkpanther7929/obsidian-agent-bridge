---
name: obsidian-memory
description: >
  Route, read, record, and check Obsidian-based coding-agent memory using the
  obsidian-agent-bridge CLI.
---

# Obsidian Memory

Use this skill when a coding agent needs durable project memory in an Obsidian
vault.

## Rules

- Read the smallest useful note set.
- Start with route, then read returned notes.
- Record meaningful completed work into category history.
- Append daily notes only as short backlinks.
- OAB auto-memory defaults to on.
- Codex notify hook uses `scripts/codex-notify.ps1` to run `cli/auto_record.py` at turn end.
- Treat `/oab status`, `/oab on`, `/oab off`, and `/oab set ...` as shorthand for the `oab` CLI command or `obs_oab` MCP tool.
- When subagents are available, delegate durable vault recording to a memory-recorder subagent. That subagent should only route, read, and record vault memory.
- Never write credentials, tokens, passwords, or secrets.
- Prefer the CLI over direct Markdown edits.

## Commands

Route work:

```powershell
python cli/obs_agent.py route --cwd <cwd> --path <file> --request <task> --json
```

Record work:

```powershell
python cli/obs_agent.py record --category <project/category> --title <title> --summary <summary> --json
```

Check vault health:

```powershell
python cli/obs_agent.py check --json
```

Control OAB auto-memory:

```powershell
python cli/obs_agent.py oab status --json
python cli/obs_agent.py oab on --json
python cli/obs_agent.py oab off --json
python cli/obs_agent.py oab set memoryRecorderAgent on --json
python cli/auto_record.py --cwd <repo> --json
```

When MCP is configured, prefer these tools:

- `obs_route`
- `obs_read`
- `obs_search`
- `obs_record`
- `obs_check`
- `obs_oab`

Use `--config <path>` for custom vault paths, daily folders, route hints, and
history templates.

## Flow

1. Run `route`.
2. Read only the returned `read_set`.
3. Complete the user task.
4. Run `record --dry-run` and inspect the note path, daily link, and note text.
5. Run `record` when the target is correct.
