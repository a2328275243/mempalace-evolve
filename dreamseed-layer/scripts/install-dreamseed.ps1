param(
  [string]$InstallRoot = "D:\DreamSeed-Local-Agent",
  [string]$AppRoot = "",
  [switch]$AddToUserPath,
  [switch]$DesktopShortcut
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $AppRoot) {
  $AppRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
}

$AppRoot = [System.IO.Path]::GetFullPath($AppRoot)
$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$BinDir = Join-Path $InstallRoot "bin"
$DreamSeedCmd = Join-Path $BinDir "dreamseed.cmd"
$DesktopCmd = Join-Path $BinDir "dreamseed-desktop.cmd"
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

@"
@echo off
set "DREAMSEED_LOCAL_ROOT=$InstallRoot"
set "DREAMSEED_APP_ROOT=$AppRoot"
node "$Agent" desktop
"@ | Set-Content -LiteralPath $DesktopCmd -Encoding ASCII

if ($AddToUserPath) {
  $Current = [Environment]::GetEnvironmentVariable("Path", "User")
  $Parts = @($Current -split ";" | Where-Object { $_ })
  if (-not ($Parts | Where-Object { [System.IO.Path]::GetFullPath($_) -ieq $BinDir })) {
    [Environment]::SetEnvironmentVariable("Path", (($Parts + $BinDir) -join ";"), "User")
  }
}

if ($DesktopShortcut) {
  $Desktop = [Environment]::GetFolderPath("Desktop")
  $ShortcutPath = Join-Path $Desktop "DreamSeed Desktop.lnk"
  $Shell = New-Object -ComObject WScript.Shell
  $Shortcut = $Shell.CreateShortcut($ShortcutPath)
  $Shortcut.TargetPath = $DesktopCmd
  $Shortcut.WorkingDirectory = $AppRoot
  $Shortcut.Description = "DreamSeed Desktop"
  $Shortcut.Save()
}

Write-Host "DreamSeed installed shims:"
Write-Host "  $DreamSeedCmd"
Write-Host "  $DesktopCmd"
if ($AddToUserPath) { Write-Host "User PATH updated. Open a new terminal, then run: dreamseed" }
if ($DesktopShortcut) { Write-Host "Desktop shortcut created: DreamSeed Desktop.lnk" }
