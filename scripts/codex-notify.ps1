[CmdletBinding()]
param(
  [Parameter(ValueFromPipeline = $true)]
  [AllowEmptyString()]
  [string]$PipedInput,
  [Parameter(ValueFromRemainingArguments = $true, Position = 0)]
  [string[]]$RemainingArgs
)

$ErrorActionPreference = "Continue"

$RepoPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AutoRecorder = Join-Path $RepoPath "cli\auto_record.py"
$LogDir = Join-Path $HOME ".obsidian-agent-bridge"
$LogPath = Join-Path $LogDir "codex-auto-record.log"
$OriginalNotify = "C:\Users\hsublee\AppData\Local\OpenAI\Codex\runtimes\cua_node\1b23c930bdf84ed6\bin\node_modules\@oai\sky\bin\windows\codex-computer-use.exe"
$StdinPayload = if ([string]::IsNullOrEmpty($PipedInput)) { [Console]::In.ReadToEnd() } else { $PipedInput }

if (-not (Test-Path -LiteralPath $LogDir)) {
  New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-OabLog {
  param([string]$Message)
  try {
    "[$(Get-Date -Format o)] $Message" | Add-Content -LiteralPath $LogPath -Encoding UTF8 -ErrorAction Stop
  }
  catch {
  }
}

try {
  if (Test-Path -LiteralPath $OriginalNotify) {
    if ([string]::IsNullOrWhiteSpace($StdinPayload)) {
      Write-OabLog "native notify skipped: missing stdin payload"
    }
    else {
      $process = [System.Diagnostics.Process]::new()
      $process.StartInfo.FileName = $OriginalNotify
      foreach ($arg in $RemainingArgs) {
        [void]$process.StartInfo.ArgumentList.Add($arg)
      }
      $process.StartInfo.RedirectStandardInput = $true
      $process.StartInfo.RedirectStandardOutput = $true
      $process.StartInfo.RedirectStandardError = $true
      $process.StartInfo.UseShellExecute = $false
      $process.StartInfo.CreateNoWindow = $true
      [void]$process.Start()
      $process.StandardInput.Write($StdinPayload)
      $process.StandardInput.Close()
      if (-not $process.WaitForExit(750)) {
        $process.Kill()
        Write-OabLog "native notify timed out after 750ms"
      }
    }
  }
}
catch {
  Write-OabLog "native notify failed: $($_.Exception.Message)"
}

try {
  $eventName = if ($RemainingArgs.Count -gt 0) { $RemainingArgs[0] } else { "turn-ended" }
  & python -X utf8 $AutoRecorder --cwd (Get-Location).Path --event $eventName --json 2>&1 | ForEach-Object {
    Write-OabLog "$_"
  }
}
catch {
  Write-OabLog "auto record failed: $($_.Exception.Message)"
}
