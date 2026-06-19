param(
  [string]$InstallRoot = "",
  [string]$AppRoot = "",
  [switch]$AddToUserPath
)

if (-not $InstallRoot) {
  $InstallRoot = Join-Path $env:LOCALAPPDATA "DreamSeed"
}

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $AppRoot) {
  $AppRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
}

$AppRoot = [System.IO.Path]::GetFullPath($AppRoot)
$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$BinDir = Join-Path $InstallRoot "bin"
$DreamSeedCmd = Join-Path $BinDir "dreamseed.cmd"
$Agent = Join-Path $AppRoot "bin\dreamseed-agent.js"

if (-not (Test-Path -LiteralPath $Agent)) {
  throw "DreamSeed agent not found: $Agent"
}

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

@"
@echo off
set "DREAMSEED_LOCAL_ROOT=$InstallRoot"
set "DREAMSEED_APP_ROOT=$AppRoot"
node "$Agent" %*
"@ | Set-Content -LiteralPath $DreamSeedCmd -Encoding ASCII

if ($AddToUserPath) {
  $Current = [Environment]::GetEnvironmentVariable("Path", "User")
  $Parts = @($Current -split ";" | Where-Object { $_ })
  if (-not ($Parts | Where-Object { [System.IO.Path]::GetFullPath($_) -ieq $BinDir })) {
    [Environment]::SetEnvironmentVariable("Path", (($Parts + $BinDir) -join ";"), "User")
  }
}

Write-Host "DreamSeed installed:"
Write-Host "  $DreamSeedCmd"
if ($AddToUserPath) { Write-Host "User PATH updated. Open a new terminal, then run: dreamseed" }
