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

Use `--config <path>` for custom vault paths, daily folders, route hints, and
history templates.

## Flow

1. Run `route`.
2. Read only the returned `read_set`.
3. Complete the user task.
4. Run `record --dry-run` and inspect the note path, daily link, and note text.
5. Run `record` when the target is correct.
