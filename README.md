# obsidian-agent-bridge

English | [Korean](README.ko.md)

Local-first Obsidian memory bridge for Claude Code, Codex, and MCP-compatible coding agents.

It routes a task to the right vault category, returns a small read set, records completed work into history notes, and checks vault hygiene. Everything stays on your machine.

## Install

### Claude Code

Fast local setup:

```powershell
git clone https://github.com/pinkpanther7929/obsidian-agent-bridge.git D:\obsidian-agent-bridge
cd D:\obsidian-agent-bridge
.\scripts\write-config.ps1 -Vault "$env:USERPROFILE\Documents\Obsidian Vault" -Language en
.\scripts\install-claude.ps1
```

This registers the MCP server in Claude Code:

```powershell
claude mcp add -s user obsidian-agent-bridge -e PYTHONPATH=D:\obsidian-agent-bridge -- python -m mcp_server.server
```

Plugin-ready metadata is included at `.claude-plugin/plugin.json`, so this repo can also be used as a Claude Code plugin source when added to a Claude plugin marketplace/workflow.

### Codex

Install from GitHub through npm:

```powershell
npm install -g github:pinkpanther7929/obsidian-agent-bridge
```

Then register the MCP server:

```powershell
git clone https://github.com/pinkpanther7929/obsidian-agent-bridge.git D:\obsidian-agent-bridge
cd D:\obsidian-agent-bridge
.\scripts\write-config.ps1 -Vault "$env:USERPROFILE\Documents\Obsidian Vault" -Language en
.\scripts\install-codex.ps1
```

Restart Codex after registration. The installer appends this block to `~/.codex/config.toml` if missing:

```toml
[mcp_servers.obsidian_agent_bridge]
command = 'powershell.exe'
args = ['-NoProfile', '-File', 'D:\obsidian-agent-bridge\scripts\run-mcp.ps1']
startup_timeout_sec = 30
```

Global commands after npm install:

```powershell
obs-agent route --request "Update project memory" --json
obs-agent-mcp
```

## What It Does

- Routes tasks from `cwd`, file paths, and request text to a project/category.
- Returns a minimal `read_set` so agents do not load the whole vault.
- Records completed work into `projects/<project>/<category>/history/`.
- Appends one deduplicated daily backlink.
- Reads/searches vault notes safely, excluding `archive/` by default.
- Checks missing/ambiguous note links, duplicate daily backlinks, and secret-looking content.
- Supports English and Korean messages through config.

## Repository Layout

```text
obsidian-agent-bridge/
  .claude-plugin/plugin.json
  bin/                  # npm command wrappers
  cli/                  # CLI implementation
  mcp_server/           # dependency-free stdio MCP server
  scripts/              # setup and run helpers
  agents/
  skills/
  examples/
  tests/
```

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

`language` supports `en` and `ko`. `--vault` wins over config. Routing also scans `projects/*/*/index.md` for category names, headings, and wikilinks.

## CLI

```powershell
obs-agent route --cwd C:\work\app --request "Fix stale login sessions" --json
obs-agent read --path CODEX.md --json
obs-agent search --query "session" --path-prefix projects --json
obs-agent record --category engineering/backend --title "auth session fix" --summary "Fixed stale session cleanup." --dry-run --json
obs-agent check --json
```

Without npm install, use:

```powershell
python cli\obs_agent.py route --request "Fix stale login sessions" --json
```

## MCP Tools

Run server:

```powershell
python -m mcp_server.server
# or
obs-agent-mcp
```

Tools:

- `obs_route`
- `obs_read`
- `obs_search`
- `obs_record`
- `obs_check`

Recommended agent flow:

1. Call `obs_route`.
2. Read only returned `read_set` through `obs_read`.
3. Do the user task.
4. Preview with `obs_record` and `dry_run: true`.
5. Record final work with `obs_record`.
6. Optionally run `obs_check`.

See [`examples/`](examples/) for Claude/Codex config snippets and [`examples/AGENTS.md`](examples/AGENTS.md) for project instructions.

## Development

```powershell
python -m unittest discover -s tests
python -m py_compile cli\*.py mcp_server\*.py
```
