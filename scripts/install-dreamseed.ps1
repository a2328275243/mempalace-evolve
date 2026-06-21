param(
  [string]$InstallRoot = "",
  [string]$AppRoot = "",
  [string]$Node = "",
  [string]$Python = "",
  [switch]$AddToUserPath,
  [switch]$NoPathUpdate,
  [switch]$NoAutoInstall,
  [switch]$SkipPythonDeps,
  [switch]$SkipSelfTest,
  [switch]$OfflinePythonDeps
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Parse-Version {
  param([string]$Text)
  $match = [regex]::Match($Text, "(\d+)\.(\d+)(?:\.(\d+))?")
  if (-not $match.Success) { return $null }
  $patch = if ($match.Groups[3].Success) { [int]$match.Groups[3].Value } else { 0 }
  return [version]::new([int]$match.Groups[1].Value, [int]$match.Groups[2].Value, $patch)
}

function Test-MinVersion {
  param([version]$Actual, [version]$Minimum)
  return $Actual -and ($Actual -ge $Minimum)
}

function Join-ExistingCandidate {
  param([string]$Base, [string]$Child)
  if (-not $Base) { return $null }
  try {
    return (Join-Path $Base $Child)
  } catch {
    return $null
  }
}

function Same-Path {
  param([string]$Left, [string]$Right)
  if (-not $Left -or -not $Right) { return $false }
  try {
    return [System.IO.Path]::GetFullPath($Left) -ieq [System.IO.Path]::GetFullPath($Right)
  } catch {
    return $Left.TrimEnd('\') -ieq $Right.TrimEnd('\')
  }
}

function Refresh-ProcessPath {
  $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $user = [Environment]::GetEnvironmentVariable("Path", "User")
  $extra = @(
    (Join-ExistingCandidate $env:ProgramFiles "nodejs"),
    (Join-ExistingCandidate ${env:ProgramFiles(x86)} "nodejs"),
    (Join-ExistingCandidate $env:LOCALAPPDATA "Programs\Python\Python312"),
    (Join-ExistingCandidate $env:LOCALAPPDATA "Programs\Python\Python312\Scripts"),
    (Join-ExistingCandidate $env:ProgramFiles "Python312"),
    (Join-ExistingCandidate $env:ProgramFiles "Python312\Scripts")
  ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
  $env:Path = (@($env:Path, $machine, $user) + $extra | Where-Object { $_ }) -join ";"
}

function Invoke-WingetInstall {
  param(
    [string]$PackageId,
    [string]$FriendlyName
  )

  if ($NoAutoInstall) {
    throw "$FriendlyName was not found. Install it manually or rerun without -NoAutoInstall."
  }

  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if (-not $winget) {
    throw "$FriendlyName was not found and winget is unavailable. Install $FriendlyName manually, then rerun this script."
  }

  Write-Step "Installing $FriendlyName with winget"
  & $winget.Source install --id $PackageId --exact --source winget --accept-package-agreements --accept-source-agreements
  if ($LASTEXITCODE -ne 0) {
    throw "winget failed to install $FriendlyName (exit $LASTEXITCODE). Install it manually, then rerun this script."
  }
  Refresh-ProcessPath
}

function Resolve-NodeRuntime {
  $minimum = [version]"18.0.0"
  $candidates = @()
  if ($Node) { $candidates += $Node }
  if ($env:DREAMSEED_NODE) { $candidates += $env:DREAMSEED_NODE }
  $cmd = Get-Command node -ErrorAction SilentlyContinue
  if ($cmd) { $candidates += $cmd.Source }
  $candidates += @(
    (Join-ExistingCandidate $env:ProgramFiles "nodejs\node.exe"),
    (Join-ExistingCandidate ${env:ProgramFiles(x86)} "nodejs\node.exe")
  )

  foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    $versionText = (& $candidate --version 2>$null | Select-Object -First 1)
    $version = Parse-Version $versionText
    if (Test-MinVersion $version $minimum) {
      return @{ Exe = [System.IO.Path]::GetFullPath($candidate); Version = $version }
    }
  }

  Invoke-WingetInstall -PackageId "OpenJS.NodeJS.LTS" -FriendlyName "Node.js 18+"

  $cmd = Get-Command node -ErrorAction SilentlyContinue
  if ($cmd) {
    $versionText = (& $cmd.Source --version 2>$null | Select-Object -First 1)
    $version = Parse-Version $versionText
    if (Test-MinVersion $version $minimum) {
      return @{ Exe = [System.IO.Path]::GetFullPath($cmd.Source); Version = $version }
    }
  }
  throw "Node.js 18+ was installed or detected, but this PowerShell session cannot resolve it yet. Open a new terminal and rerun this script."
}

function Resolve-PythonRuntime {
  $minimum = [version]"3.10.0"

  $candidates = @()
  if ($Python) {
    $candidates += @{ Exe = $Python; Args = @(); Display = $Python }
  }
  if ($env:DREAMSEED_PYTHON) {
    $candidates += @{ Exe = $env:DREAMSEED_PYTHON; Args = @(); Display = $env:DREAMSEED_PYTHON }
  }
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    $candidates += @{ Exe = $python.Source; Args = @(); Display = $python.Source }
  }
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    $candidates += @{ Exe = $py.Source; Args = @("-3"); Display = "$($py.Source) -3" }
  }
  $candidates += @(
    @{ Exe = (Join-ExistingCandidate $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"); Args = @(); Display = "Python 3.12 user install" },
    @{ Exe = (Join-ExistingCandidate $env:ProgramFiles "Python312\python.exe"); Args = @(); Display = "Python 3.12 machine install" }
  )

  foreach ($candidate in $candidates) {
    if (-not $candidate.Exe -or -not (Test-Path -LiteralPath $candidate.Exe)) { continue }
    $versionText = (& $candidate.Exe @($candidate.Args) --version 2>$null | Select-Object -First 1)
    $version = Parse-Version $versionText
    if (Test-MinVersion $version $minimum) {
      return @{ Exe = [System.IO.Path]::GetFullPath($candidate.Exe); Args = [string[]]$candidate.Args; Version = $version }
    }
  }

  Invoke-WingetInstall -PackageId "Python.Python.3.12" -FriendlyName "Python 3.10+"

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    $versionText = (& $python.Source --version 2>$null | Select-Object -First 1)
    $version = Parse-Version $versionText
    if (Test-MinVersion $version $minimum) {
      return @{ Exe = [System.IO.Path]::GetFullPath($python.Source); Args = @(); Version = $version }
    }
  }
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    $versionText = (& $py.Source -3 --version 2>$null | Select-Object -First 1)
    $version = Parse-Version $versionText
    if (Test-MinVersion $version $minimum) {
      return @{ Exe = [System.IO.Path]::GetFullPath($py.Source); Args = @("-3"); Version = $version }
    }
  }
  throw "Python 3.10+ was installed or detected, but this PowerShell session cannot resolve it yet. Open a new terminal and rerun this script."
}

if (-not $AppRoot) {
  $AppRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
}
if (-not $InstallRoot) {
  $InstallRoot = Join-Path $env:LOCALAPPDATA "DreamSeed"
}

$AppRoot = [System.IO.Path]::GetFullPath($AppRoot)
$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$BinDir = Join-Path $InstallRoot "bin"
$RuntimeDir = Join-Path $InstallRoot "runtime"
$PythonSite = Join-Path $RuntimeDir "python-site"
$DreamSeedCmd = Join-Path $BinDir "dreamseed.cmd"
$Agent = Join-Path $AppRoot "bin\dreamseed-agent.js"
$PythonDepsScript = Join-Path $AppRoot "scripts\install-python-deps.ps1"

if (-not (Test-Path -LiteralPath $Agent)) {
  throw "DreamSeed agent not found: $Agent"
}
if (-not (Test-Path -LiteralPath $PythonDepsScript)) {
  throw "DreamSeed Python dependency installer not found: $PythonDepsScript"
}

Write-Step "Checking runtime dependencies"
$NodeRuntime = Resolve-NodeRuntime
$PythonRuntime = Resolve-PythonRuntime
Write-Host "Node.js: $($NodeRuntime.Exe) ($($NodeRuntime.Version))" -ForegroundColor Green
Write-Host "Python: $($PythonRuntime.Exe) $($PythonRuntime.Args -join ' ') ($($PythonRuntime.Version))" -ForegroundColor Green

New-Item -ItemType Directory -Force -Path $BinDir, $RuntimeDir | Out-Null

if (-not $SkipPythonDeps) {
  Write-Step "Installing DreamSeed Python dependencies"
  $env:DREAMSEED_PYTHON = $PythonRuntime.Exe
  $env:DREAMSEED_PYTHON_ARGS = ($PythonRuntime.Args -join " ")
  $env:DREAMSEED_PYTHON_SITE = $PythonSite

  $depArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $PythonDepsScript,
    "-Target", $PythonSite,
    "-MempalaceSource", $AppRoot
  )
  if ($OfflinePythonDeps) {
    $depArgs += "-Offline"
  }
  & powershell.exe @depArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Python dependency installation failed (exit $LASTEXITCODE)."
  }
} else {
  Write-Host "Skipping Python dependency installation." -ForegroundColor Yellow
}

$PythonArgsLine = $PythonRuntime.Args -join " "

@"
@echo off
set "DREAMSEED_LOCAL_ROOT=$InstallRoot"
set "DREAMSEED_APP_ROOT=$AppRoot"
set "DREAMSEED_PYTHON=$($PythonRuntime.Exe)"
set "DREAMSEED_PYTHON_ARGS=$PythonArgsLine"
set "DREAMSEED_PYTHON_SITE=$PythonSite"
"$($NodeRuntime.Exe)" "$Agent" %*
"@ | Set-Content -LiteralPath $DreamSeedCmd

if (-not $NoPathUpdate -or $AddToUserPath) {
  $Current = [Environment]::GetEnvironmentVariable("Path", "User")
  $Parts = @($Current -split ";" | Where-Object { $_ })
  if (-not ($Parts | Where-Object { Same-Path $_ $BinDir })) {
    [Environment]::SetEnvironmentVariable("Path", (($Parts + $BinDir) -join ";"), "User")
  }
  if (-not ($env:Path -split ";" | Where-Object { Same-Path $_ $BinDir })) {
    $env:Path = "$BinDir;$env:Path"
  }
}

if (-not $SkipSelfTest) {
  Write-Step "Running DreamSeed self-test"
  & $DreamSeedCmd --help | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "DreamSeed self-test failed: dreamseed --help exited with $LASTEXITCODE"
  }
  Write-Host "dreamseed --help passed." -ForegroundColor Green
}

Write-Host ""
Write-Host "DreamSeed installed:"
Write-Host "  $DreamSeedCmd"
if (-not $NoPathUpdate -or $AddToUserPath) { Write-Host "User PATH updated. Open a new terminal, then run: dreamseed" }
