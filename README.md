# obsidian-agent-bridge

Local-first Obsidian memory tools for coding agents.

This project turns an Obsidian vault into a small, predictable agent memory
system:

- route tasks to the right project/category notes
- read only the minimal startup context
- record work into category history notes
- append deduplicated daily links
- check for broken links, misplaced notes, and secret-looking content

The first target is CLI usage. MCP servers, Codex skills, and Claude agents can
wrap the same CLI later.

## Quick Start

```powershell
python cli\obs_agent.py route --cwd C:\work\app --path src\auth\session.py
python cli\obs_agent.py record --category engineering/backend --title "auth session fix" --summary "Fixed stale session cleanup."
python cli\obs_agent.py check
```

Default vault:

```text
~/Documents/Obsidian Vault
```

Override with `--vault` or `OBSIDIAN_VAULT_PATH`.

## Commands

### `route`

Suggests a category and minimal read set from cwd, paths, and request text.

```powershell
python cli\obs_agent.py route `
  --cwd C:\work\app `
  --path src\auth\session.py `
  --request "Fix stale login sessions" `
  --json
```

### `record`

Writes a category history note and appends one deduplicated daily backlink.

```powershell
python cli\obs_agent.py record `
  --category engineering/backend `
  --title "auth session fix" `
  --summary "Fixed stale session cleanup." `
  --json
```

### `check`

Scans non-archive Markdown for:

- broken or ambiguous wikilinks
- duplicated daily backlinks
- secret-looking content

```powershell
python cli\obs_agent.py check --json
```

## Agent Shape

The first bundled agent spec is [`agents/vault-curator.md`](agents/vault-curator.md).
It defines policy and delegates filesystem changes to this CLI.
