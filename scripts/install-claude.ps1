param(
  [string]$RepoPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
  throw "Claude Code CLI not found on PATH."
}

$runScript = Join-Path $RepoPath "scripts\run-mcp.ps1"
$existing = & claude mcp get obsidian-agent-bridge 2>$null
if ($LASTEXITCODE -eq 0 -and $existing) {
  Write-Host "Claude MCP server already registered: obsidian-agent-bridge"
  exit 0
}

& claude mcp add -s user obsidian-agent-bridge -- powershell.exe -NoProfile -File $runScript
Write-Host "Registered Claude MCP server: obsidian-agent-bridge"
