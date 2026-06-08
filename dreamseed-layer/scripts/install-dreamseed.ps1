param(
  [string]$BinDir = "",
  [switch]$NoPath,
  [switch]$SkipPythonDeps,
  [switch]$OfflinePythonDeps
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $BinDir) {
  $BinDir = Join-Path $env:LOCALAPPDATA "DreamSeed\bin"
}

if (-not (Test-Path -LiteralPath $BinDir)) {
  New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
}

$CmdPath = Join-Path $BinDir "dreamseed.cmd"
$Ps1Path = Join-Path $BinDir "dreamseed.ps1"
$Launcher = Join-Path $RepoRoot "bin\dreamseed-agent.js"

if (-not (Test-Path -LiteralPath $Launcher)) {
  throw "DreamSeed launcher not found: $Launcher"
}

$Cmd = @"
@echo off
node "$Launcher" %*
"@
$Cmd | Set-Content -LiteralPath $CmdPath -Encoding ASCII

$Ps1 = @"
& node "$Launcher" @args
exit `$LASTEXITCODE
"@
$Ps1 | Set-Content -LiteralPath $Ps1Path -Encoding UTF8

if (-not $NoPath) {
  $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $Parts = @()
  if ($UserPath) {
    $Parts = $UserPath -split ";" | Where-Object { $_ }
  }

  $NormalizedBin = [System.IO.Path]::GetFullPath($BinDir).TrimEnd("\")
  $AlreadyPresent = $false
  foreach ($Part in $Parts) {
    try {
      if ([System.IO.Path]::GetFullPath($Part).TrimEnd("\").Equals($NormalizedBin, [System.StringComparison]::OrdinalIgnoreCase)) {
        $AlreadyPresent = $true
        break
      }
    } catch {
      continue
    }
  }

  if (-not $AlreadyPresent) {
    $NewPath = if ($UserPath) { "$UserPath;$BinDir" } else { $BinDir }
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
  }

  if (($env:Path -split ";") -notcontains $BinDir) {
    $env:Path = "$BinDir;$env:Path"
  }
}

$Node = Get-Command node -ErrorAction SilentlyContinue
if (-not $Node) {
  Write-Warning "Node.js was not found in PATH. Install Node.js 18+ before running dreamseed."
}

if (-not $SkipPythonDeps) {
  $InstallPythonDeps = Join-Path $RepoRoot "scripts\install-python-deps.ps1"
  if (Test-Path -LiteralPath $InstallPythonDeps) {
    $InstallArgs = @()
    if ($OfflinePythonDeps) {
      $InstallArgs += "-Offline"
    }
    & $InstallPythonDeps @InstallArgs
  } else {
    Write-Warning "DreamSeed Python dependency installer was not found: $InstallPythonDeps"
  }
}

Write-Host "Installed dreamseed command: $CmdPath" -ForegroundColor Green
Write-Host "PowerShell shim: $Ps1Path" -ForegroundColor Green
if (-not $NoPath) {
  Write-Host "Open a new terminal, then run: dreamseed --help" -ForegroundColor Green
}
