param(
  [ValidateSet("hook", "status", "audit", "check")]
  [string]$Mode = "hook"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot

if (-not $env:DREAMSEED_ROOT) {
  $env:DREAMSEED_ROOT = $RepoRoot
}
if (-not $env:PYTHONIOENCODING) {
  $env:PYTHONIOENCODING = "utf-8"
}

$Python = if ($env:DREAMSEED_PYTHON) { $env:DREAMSEED_PYTHON } else { "python" }
$HookInputPath = ""

try {
  $stdinText = [Console]::In.ReadToEnd()
  if ($stdinText -and $stdinText.Trim().Length -gt 0) {
    $HookInputPath = Join-Path ([IO.Path]::GetTempPath()) ("dreamseed-approval-{0}.json" -f ([Guid]::NewGuid().ToString("N")))
    Set-Content -LiteralPath $HookInputPath -Value $stdinText -Encoding UTF8
  }

  $argsList = @(
    (Join-Path $RepoRoot "scripts\approval_gate.py"),
    $Mode
  )
  if ($HookInputPath) {
    $argsList += @("--hook-input", $HookInputPath)
  }

  & $Python @argsList
  exit $LASTEXITCODE
}
finally {
  if ($HookInputPath -and (Test-Path -LiteralPath $HookInputPath)) {
    Remove-Item -LiteralPath $HookInputPath -Force
  }
}
