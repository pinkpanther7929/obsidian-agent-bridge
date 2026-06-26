Use `obsidian-agent-bridge` for Obsidian memory routing and recording.

Before work:
- Call MCP tool `obs_route` with `cwd`, relevant paths, and the user request.
- Read only the returned `read_set`.

After meaningful work:
- OAB auto-memory is on by default.
- Map `/oab status`, `/oab on`, `/oab off`, and `/oab set ...` to `obs_oab` or `obs-agent oab`.
- Use a memory-recorder subagent for durable vault recording when subagents are available.
- Call `obs_record` with `dryRun=true`.
- Check that the category and note text are correct.
- Call `obs_record` again with `dryRun=false`.

Use `obs_search` and `obs_read` for targeted Obsidian lookup. Use `obs_check`
when vault health matters.
