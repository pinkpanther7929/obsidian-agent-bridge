# obsidian-agent-bridge

Local-first Obsidian memory tools for coding agents.

`obsidian-agent-bridge` helps an agent treat an Obsidian vault as a small,
predictable memory system instead of a folder full of Markdown files. It routes
work to the right project notes, records completed work in category history, and
checks the vault for memory hygiene issues.

## What It Does

- Routes tasks from `cwd`, file paths, and request text to a project/category.
- Returns a minimal `read_set` so agents do not load the whole vault.
- Records completed work into `projects/<project>/<category>/history/`.
- Appends one deduplicated daily backlink.
- Checks missing/ambiguous note links, duplicate daily backlinks, and
  secret-looking content.
- Reads optional config for vault path, route hints, daily folder, and history
  note template.

The current interface is a CLI. Agent specs, skills, and future MCP tools wrap
the same behavior.

## Repository Layout

```text
obsidian-agent-bridge/
  cli/
    obs_agent.py      # CLI entrypoint
    config.py         # config loading
    router.py         # route scoring and vault-derived hints
    recorder.py       # history + daily writes
    checker.py        # link and secret checks
    vault.py          # safe vault filesystem access
  agents/
    vault-curator.md
  skills/
    obsidian-memory/SKILL.md
  tests/
    test_core.py
```

## Quick Start

```powershell
python cli\obs_agent.py route --cwd C:\work\app --path src\auth\session.py --request "Fix stale login sessions" --json
python cli\obs_agent.py record --category engineering/backend --title "auth session fix" --summary "Fixed stale session cleanup." --dry-run --json
python cli\obs_agent.py check --json
```

Default vault:

```text
~/Documents/Obsidian Vault
```

Override with `--vault`, `OBSIDIAN_VAULT_PATH`, `--config`, or
`OBS_AGENT_CONFIG`.

## Config

Default config path:

```text
~/.obsidian-agent-bridge/config.json
```

Example:

```json
{
  "vault": "~/Documents/Obsidian Vault",
  "language": "en",
  "dailyFolder": "daily",
  "historyTemplate": "# {date} {title}\n\n{summary}\n",
  "categoryHints": {
    "projects/engineering/backend": ["backend", "api", "auth", "database"],
    "projects/ai/agents": ["agent", "mcp", "tool", "memory"]
  }
}
```

`language` supports `en` and `ko`. It localizes route reasons and validation
errors. `--vault` wins over the config file. `historyTemplate` supports `{date}`,
`{title}`, `{summary}`, and `{category}`.

Routing also scans `projects/*/*/index.md`. Category path parts, index headings,
and wikilink targets become route hints, so a vault can work without listing
every category in config.

## Language

Set `"language": "en"` or `"language": "ko"` in config. English is the default.
Korean mode localizes route reasons and validation errors while keeping JSON
field names stable for agents.

## Commands

### `route`

Suggest a category and minimal notes to read.

```powershell
python cli\obs_agent.py route `
  --cwd C:\work\app `
  --path src\auth\session.py `
  --request "Fix stale login sessions" `
  --json
```

Example output:

```json
{
  "category": "projects/engineering/backend",
  "confidence": 0.55,
  "reason": "Matched session",
  "read_set": ["CODEX.md", "projects/engineering/backend/index.md"]
}
```

### `record`

Create a history note and append a daily backlink.

```powershell
python cli\obs_agent.py record `
  --category engineering/backend `
  --title "auth session fix" `
  --summary "Fixed stale session cleanup." `
  --dry-run `
  --json
```

`--dry-run` previews `note_path`, `daily_link`, and `note_text` without writing.

### `check`

Scan non-archive Markdown for vault hygiene issues.

```powershell
python cli\obs_agent.py check --json
```

Checks:

- missing note links
- ambiguous short wikilinks
- relative Markdown links to notes
- duplicate daily backlinks
- secret-looking content

## Agent Workflow

Recommended agent flow:

1. Run `route`.
2. Read only the returned `read_set`.
3. Do the user task.
4. Run `record --dry-run`.
5. Confirm the target category and note text.
6. Run `record`.
7. Optionally run `check`.

Bundled agent/skill docs:

- [`agents/vault-curator.md`](agents/vault-curator.md)
- [`skills/obsidian-memory/SKILL.md`](skills/obsidian-memory/SKILL.md)

## Development

Run tests:

```powershell
python -m unittest discover -s tests
```

GitHub Actions runs the same test command on push and pull request.
