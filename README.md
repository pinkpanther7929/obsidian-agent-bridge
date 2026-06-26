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
python -m obsidian_agent_bridge route --cwd D:\devops-infra.main --path jenkins\foo.py
python -m obsidian_agent_bridge record --category devops-infra/local-llm --title "vs-token-safer applied" --summary "Configured local token-saving tool."
python -m obsidian_agent_bridge check
```

Default vault:

```text
C:\Users\hsublee\Documents\Obsidian Vault
```

Override with `--vault` or `OBSIDIAN_VAULT_PATH`.

## Commands

### `route`

Suggests a category and minimal read set from cwd, paths, and request text.

```powershell
python -m obsidian_agent_bridge route `
  --cwd D:\devops-infra.main `
  --path jenkins\jenkinsfiles\resources\jenkins_failure_analysis\foo.py `
  --request "Fix Jenkins Slack user mapping" `
  --json
```

### `record`

Writes a category history note and appends one deduplicated daily backlink.

```powershell
python -m obsidian_agent_bridge record `
  --category devops-infra/local-llm `
  --title "vs-token-safer applied" `
  --summary "Configured local token-saving tool." `
  --json
```

### `check`

Scans non-archive Markdown for:

- broken or ambiguous wikilinks
- duplicated daily backlinks
- secret-looking content

```powershell
python -m obsidian_agent_bridge check --json
```

## Agent Shape

The first bundled agent spec is [`agents/vault-curator.md`](agents/vault-curator.md).
It defines policy and delegates filesystem changes to this CLI.
