param(
  [string]$InstallRoot = "",
  [switch]$RemoveFromUserPath
)

if (-not $InstallRoot) {
  $InstallRoot = Join-Path $env:LOCALAPPDATA "DreamSeed"
}

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$BinDir = Join-Path $InstallRoot "bin"
$DreamSeedCmd = Join-Path $BinDir "dreamseed.cmd"

if (Test-Path -LiteralPath $DreamSeedCmd) {
  Remove-Item -LiteralPath $DreamSeedCmd -Force
  Write-Host "Removed $DreamSeedCmd"
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

Write-Host "DreamSeed uninstall helper finished. Local history, provider config, memory, and logs were not deleted."
