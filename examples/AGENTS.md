Use `obsidian-agent-bridge` for Obsidian memory routing and recording.

Before work:
- Call MCP tool `obs_route` with `cwd`, relevant paths, and the user request.
- Read only the returned `read_set`.

After meaningful work:
- Call `obs_record` with `dryRun=true`.
- Check that the category and note text are correct.
- Call `obs_record` again with `dryRun=false`.

Use `obs_search` and `obs_read` for targeted Obsidian lookup. Use `obs_check`
when vault health matters.
