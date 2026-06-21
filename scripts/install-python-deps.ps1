param(
  [string]$Python = "",
  [string]$Target = "",
  [string]$Requirements = "",
  [string]$Wheelhouse = "",
  [string]$MempalaceSource = "",
  [string]$MempalacePackage = "",
  [switch]$Offline,
  [switch]$NoWheelhouse
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $Requirements) {
  $Requirements = Join-Path $RepoRoot "requirements-dreamseed.txt"
}
if (-not $Wheelhouse) {
  $Wheelhouse = Join-Path $RepoRoot "vendor\python-wheels"
}
if (-not $Target) {
  $Target = if ($env:DREAMSEED_PYTHON_SITE) {
    $env:DREAMSEED_PYTHON_SITE
  } else {
    Join-Path $RepoRoot ".dreamseed-runtime\python-site"
  }
}

if (-not (Test-Path -LiteralPath $Requirements)) {
  throw "DreamSeed Python requirements not found: $Requirements"
}

function Resolve-PythonCommand {
  param([string]$Requested)

  if ($Requested) {
    return @{ Exe = $Requested; Prefix = @() }
  }
  if ($env:DREAMSEED_PYTHON) {
    return @{ Exe = $env:DREAMSEED_PYTHON; Prefix = @() }
  }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    return @{ Exe = $python.Source; Prefix = @() }
  }

  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    return @{ Exe = $py.Source; Prefix = @("-3") }
  }

  throw "Python was not found. Install Python 3.10+ or set DREAMSEED_PYTHON."
}

$ResolvedPython = Resolve-PythonCommand -Requested $Python

function Invoke-DreamSeedPython {
  param([string[]]$Arguments)
  & $ResolvedPython.Exe @($ResolvedPython.Prefix) @Arguments
}

function Resolve-MempalaceSpec {
  if ($MempalacePackage) {
    return $MempalacePackage
  }

  $sourceCandidates = @()
  if ($MempalaceSource) {
    $sourceCandidates += $MempalaceSource
  }
  if ($env:DREAMSEED_MEMPALACE_ROOT) {
    $sourceCandidates += $env:DREAMSEED_MEMPALACE_ROOT
  }
  if ($env:DREAMSEED_MEMPALACE_SRC) {
    $srcPath = $env:DREAMSEED_MEMPALACE_SRC
    $sourceCandidates += $srcPath
    $sourceCandidates += (Split-Path -Parent $srcPath)
  }
  $sourceCandidates += $RepoRoot
  $sourceCandidates += (Join-Path $RepoRoot "vendor\mempalace-evolve")

  foreach ($candidate in $sourceCandidates) {
    if (-not $candidate) { continue }
    $full = try { [System.IO.Path]::GetFullPath($candidate) } catch { $candidate }
    if (Test-Path -LiteralPath (Join-Path $full "pyproject.toml")) {
      return "$full[mcp]"
    }
  }

  if ($Offline) {
    return "mempalace-evolve[mcp]"
  }

  return "mempalace-evolve[mcp] @ git+https://github.com/a2328275243/mempalace-evolve.git"
}

New-Item -ItemType Directory -Force -Path $Target | Out-Null

Write-Host "Using Python: $($ResolvedPython.Exe) $($ResolvedPython.Prefix -join ' ')" -ForegroundColor Cyan
Invoke-DreamSeedPython @("-m", "pip", "--version")

$installArgs = @(
  "-m", "pip", "install",
  "--upgrade",
  "--no-warn-conflicts",
  "--target", $Target
)

$hasWheelhouse = -not $NoWheelhouse -and
  (Test-Path -LiteralPath $Wheelhouse) -and
  ((Get-ChildItem -LiteralPath $Wheelhouse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '\.(whl|tar\.gz|zip)$' } | Select-Object -First 1) -ne $null)

if ($hasWheelhouse) {
  $installArgs += @("--find-links", $Wheelhouse)
  if ($Offline) {
    $installArgs += "--no-index"
  }
} elseif ($Offline) {
  throw "Offline install requested, but no wheels were found in: $Wheelhouse"
}

$mempalaceSpec = Resolve-MempalaceSpec
$installArgs += @("-r", $Requirements, $mempalaceSpec)

Write-Host "Installing DreamSeed Python dependencies into: $Target" -ForegroundColor Cyan
if ($hasWheelhouse) {
  Write-Host "Using wheelhouse: $Wheelhouse" -ForegroundColor Cyan
}
Invoke-DreamSeedPython $installArgs

Write-Host "DreamSeed Python dependencies installed." -ForegroundColor Green
Write-Host "Set DREAMSEED_PYTHON_SITE to use this target explicitly:" -ForegroundColor Green
Write-Host "  $Target" -ForegroundColor Green
