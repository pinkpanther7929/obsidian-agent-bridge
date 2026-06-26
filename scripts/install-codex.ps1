param(
  [string]$RepoPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$ConfigPath = (Join-Path $HOME ".codex\config.toml")
)

$ErrorActionPreference = "Stop"

$configDir = Split-Path -Parent $ConfigPath
if (-not (Test-Path -LiteralPath $configDir)) {
  New-Item -ItemType Directory -Path $configDir | Out-Null
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
  New-Item -ItemType File -Path $ConfigPath | Out-Null
}

$notifyScript = Join-Path $RepoPath "scripts\codex-notify.ps1"
$existing = Get-Content -LiteralPath $ConfigPath -Raw

if ($existing -notmatch "(?m)^notify\s*=") {
  $notifyBlock = "notify = ['powershell.exe', '-NoProfile', '-File', '$notifyScript', 'turn-ended']`n"
  Set-Content -LiteralPath $ConfigPath -Value ($notifyBlock + $existing) -Encoding UTF8
  $existing = Get-Content -LiteralPath $ConfigPath -Raw
  Write-Host "Registered Codex notify hook: obsidian-agent-bridge auto-record"
}
elseif ($existing -notmatch [regex]::Escape($notifyScript)) {
  Write-Host "Codex notify already exists; not overwriting it."
  Write-Host "Add this manually if desired:"
  Write-Host "notify = ['powershell.exe', '-NoProfile', '-File', '$notifyScript', 'turn-ended']"
}
else {
  Write-Host "Codex notify hook already registered: obsidian-agent-bridge auto-record"
}

$escapedRepoPath = $RepoPath -replace "'", "''"
$serverBlock = @"

[mcp_servers.obsidian_agent_bridge]
command = 'python'
args = ['-m', 'mcp_server.server']
startup_timeout_sec = 30

[mcp_servers.obsidian_agent_bridge.env]
PYTHONPATH = '$escapedRepoPath'
"@

$pattern = "(?ms)^\[mcp_servers\.obsidian_agent_bridge\]\r?\n.*?(?=^\[(?!mcp_servers\.obsidian_agent_bridge(?:\.env)?\])|\z)"
if ($existing -match $pattern) {
  $updated = [regex]::Replace($existing, $pattern, $serverBlock.TrimStart(), 1)
  Set-Content -LiteralPath $ConfigPath -Value $updated -Encoding UTF8
  Write-Host "Updated Codex MCP server: obsidian_agent_bridge"
}
else {
  Add-Content -LiteralPath $ConfigPath -Value $serverBlock
  Write-Host "Registered Codex MCP server: obsidian_agent_bridge"
}
Write-Host "Restart Codex to load it."
