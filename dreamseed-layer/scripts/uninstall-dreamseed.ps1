param(
  [string]$InstallRoot = "D:\DreamSeed-Local-Agent",
  [switch]$RemoveFromUserPath,
  [switch]$RemoveDesktopShortcut
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$BinDir = Join-Path $InstallRoot "bin"
$DreamSeedCmd = Join-Path $BinDir "dreamseed.cmd"
$DesktopCmd = Join-Path $BinDir "dreamseed-desktop.cmd"

foreach ($Path in @($DreamSeedCmd, $DesktopCmd)) {
  if (Test-Path -LiteralPath $Path) {
    Remove-Item -LiteralPath $Path -Force
    Write-Host "Removed $Path"
  }
}

if ($RemoveFromUserPath) {
  $Current = [Environment]::GetEnvironmentVariable("Path", "User")
  $Parts = @($Current -split ";" | Where-Object { $_ })
  $Filtered = $Parts | Where-Object {
    try { [System.IO.Path]::GetFullPath($_) -ine $BinDir } catch { $true }
  }
  [Environment]::SetEnvironmentVariable("Path", ($Filtered -join ";"), "User")
  Write-Host "Removed DreamSeed bin from user PATH when present."
}

if ($RemoveDesktopShortcut) {
  $ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "DreamSeed Desktop.lnk"
  if (Test-Path -LiteralPath $ShortcutPath) {
    Remove-Item -LiteralPath $ShortcutPath -Force
    Write-Host "Removed $ShortcutPath"
  }
}

Write-Host "DreamSeed uninstall helper finished. Local history, provider config, memory, and logs were not deleted."
