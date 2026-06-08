param(
  [string]$Python = "",
  [string]$Wheelhouse = "",
  [string]$Requirements = "",
  [string]$MempalaceSource = "",
  [string]$MempalacePackage = "",
  [switch]$Clean
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $Requirements) {
  $Requirements = Join-Path $RepoRoot "requirements-dreamseed.txt"
}
if (-not $Wheelhouse) {
  $Wheelhouse = Join-Path $RepoRoot "vendor\python-wheels"
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
  $sourceCandidates += (Join-Path $RepoRoot "vendor\mempalace-evolve")

  foreach ($candidate in $sourceCandidates) {
    if (-not $candidate) { continue }
    $full = try { [System.IO.Path]::GetFullPath($candidate) } catch { $candidate }
    if (Test-Path -LiteralPath (Join-Path $full "pyproject.toml")) {
      return "$full[mcp]"
    }
  }

  return "mempalace-evolve[mcp] @ git+https://github.com/a2328275243/mempalace-evolve.git"
}

$ResolvedPython = Resolve-PythonCommand -Requested $Python

function Invoke-DreamSeedPython {
  param([string[]]$Arguments)
  & $ResolvedPython.Exe @($ResolvedPython.Prefix) @Arguments
}

if ($Clean -and (Test-Path -LiteralPath $Wheelhouse)) {
  Get-ChildItem -LiteralPath $Wheelhouse -File | Remove-Item -Force
}

New-Item -ItemType Directory -Force -Path $Wheelhouse | Out-Null

$mempalaceSpec = Resolve-MempalaceSpec
$wheelArgs = @(
  "-m", "pip", "wheel",
  "--wheel-dir", $Wheelhouse,
  "-r", $Requirements,
  $mempalaceSpec
)

Write-Host "Building DreamSeed Python wheelhouse: $Wheelhouse" -ForegroundColor Cyan
Invoke-DreamSeedPython $wheelArgs
Write-Host "Wheelhouse ready: $Wheelhouse" -ForegroundColor Green
