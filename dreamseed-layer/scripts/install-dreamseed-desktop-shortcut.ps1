param(
  [string]$ShortcutName = "DreamSeed Desktop"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LocalLauncher = Join-Path $RepoRoot "scripts\dreamseed-desktop-launch.ps1"
$FallbackLauncher = "D:\DreamSeed-Local-Agent\bin\dreamseed-desktop.ps1"
$Launcher = if (Test-Path -LiteralPath $LocalLauncher) { $LocalLauncher } else { $FallbackLauncher }
if (-not (Test-Path -LiteralPath $Launcher)) {
  throw "Desktop launcher not found: $Launcher"
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "$ShortcutName.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
if ($Launcher.EndsWith(".ps1")) {
  $Shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
  $Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Launcher`""
} else {
  $Shortcut.TargetPath = $Launcher
  $Shortcut.Arguments = ""
}
$Shortcut.WorkingDirectory = Split-Path -Parent $Launcher
$Shortcut.Description = "Open DreamSeed Desktop"
$Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
$Shortcut.Save()

Write-Output "Created shortcut: $ShortcutPath"
