param(
  [ValidateSet("status", "doctor", "recall", "candidate", "evolve", "stop-hook")]
  [string]$Mode = "status",
  [string]$Query = "",
  [string]$TranscriptPath = ""
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot

if (-not $env:DREAMSEED_ROOT) {
  $env:DREAMSEED_ROOT = $RepoRoot
}
if (-not $env:DREAMSEED_MEMORY_DIR) {
  $env:DREAMSEED_MEMORY_DIR = Join-Path (Get-Location) ".dreamseed-memory"
}
if (-not $env:DREAMSEED_MEMPALACE_SRC) {
  $BundledMempalaceSrc = Join-Path $RepoRoot "vendor\mempalace-evolve\src"
  if (Test-Path -LiteralPath $BundledMempalaceSrc) {
    $env:DREAMSEED_MEMPALACE_SRC = $BundledMempalaceSrc
  }
}
if (-not $env:MEMPALACE_PATH) {
  $env:MEMPALACE_PATH = $env:DREAMSEED_MEMORY_DIR
}
if (-not $env:MEMPALACE_WING) {
  $env:MEMPALACE_WING = Split-Path -Leaf (Get-Location)
}
if (-not $env:PYTHONIOENCODING) {
  $env:PYTHONIOENCODING = "utf-8"
}

$PythonSite = if ($env:DREAMSEED_PYTHON_SITE) {
  $env:DREAMSEED_PYTHON_SITE
} else {
  Join-Path $RepoRoot ".dreamseed-runtime\python-site"
}

if (Test-Path -LiteralPath $PythonSite) {
  if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$PythonSite;$env:PYTHONPATH"
  } else {
    $env:PYTHONPATH = $PythonSite
  }
}

if ($env:DREAMSEED_MEMPALACE_SRC -and (Test-Path -LiteralPath $env:DREAMSEED_MEMPALACE_SRC)) {
  if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$env:DREAMSEED_MEMPALACE_SRC;$env:PYTHONPATH"
  } else {
    $env:PYTHONPATH = $env:DREAMSEED_MEMPALACE_SRC
  }
}

$Python = if ($env:DREAMSEED_PYTHON) { $env:DREAMSEED_PYTHON } else { "python" }
$HookInputPath = ""

try {
  $stdinText = [Console]::In.ReadToEnd()
  if ($stdinText -and $stdinText.Trim().Length -gt 0) {
    $HookInputPath = Join-Path ([IO.Path]::GetTempPath()) ("dreamseed-hook-{0}.json" -f ([Guid]::NewGuid().ToString("N")))
    Set-Content -LiteralPath $HookInputPath -Value $stdinText -Encoding UTF8
  }

  $argsList = @(
    (Join-Path $RepoRoot "scripts\dreamseed_memory_bridge.py"),
    "--mode", $Mode
  )
  if ($Query) {
    $argsList += @("--query", $Query)
  }
  if ($TranscriptPath) {
    $argsList += @("--transcript", $TranscriptPath)
  }
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
