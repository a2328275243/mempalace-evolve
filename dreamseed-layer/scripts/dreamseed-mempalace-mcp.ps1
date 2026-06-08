param()

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot

if (-not $env:DREAMSEED_ROOT) {
  $env:DREAMSEED_ROOT = $RepoRoot
}
if (-not $env:DREAMSEED_MEMORY_DIR) {
  $env:DREAMSEED_MEMORY_DIR = Join-Path (Get-Location) ".dreamseed-memory"
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
& $Python -m mempalace_evolve.adapters.mcp_server
exit $LASTEXITCODE
