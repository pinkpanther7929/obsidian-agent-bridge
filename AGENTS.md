Use `obsidian-agent-bridge` for this repository's Obsidian memory workflows.

Before meaningful work:
- Prefer MCP tool `obs_route` with `cwd`, relevant file paths, and the user request.
- Read only the returned `read_set`.

During work:
- Use `obs_search` and `obs_read` for targeted vault lookup.

After meaningful work:
- Call `obs_record` with `dryRun=true`.
- Verify the category, daily link, and note text.
- Call `obs_record` with `dryRun=false` only after the target is correct.

Health check:
- Use `obs_check` when link quality or secret-like content matters.

Fallback if MCP is unavailable:
- Run `python D:\obsidian-agent-bridge\cli\obs_agent.py ...`.
