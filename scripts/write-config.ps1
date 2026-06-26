param(
  [Parameter(Mandatory = $true)]
  [string]$Vault,

  [ValidateSet("en", "ko")]
  [string]$Language = "en",

  [string]$ConfigPath = "$env:USERPROFILE\.obsidian-agent-bridge\config.json"
)

$dir = Split-Path -Parent $ConfigPath
New-Item -ItemType Directory -Force -Path $dir | Out-Null

$config = [ordered]@{
  vault = $Vault
  language = $Language
  dailyFolder = "daily"
  historyTemplate = "# {date} {title}`n`n{summary}`n"
  categoryHints = [ordered]@{
    "projects/engineering/backend" = @("backend", "api", "auth", "database")
    "projects/ai/agents" = @("agent", "mcp", "tool", "memory")
  }
}

$config | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
Write-Output "Wrote $ConfigPath"
