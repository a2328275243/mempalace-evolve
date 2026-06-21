param(
  [string]$PackageZip = "",
  [string]$InstallBase = "",
  [string]$InstallRoot = "",
  [switch]$NoDesktopShortcut
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Remove-Tree {
  param([string]$Path)
  if ($Path -and (Test-Path -LiteralPath $Path)) {
    Remove-Item -LiteralPath $Path -Recurse -Force
  }
}

function Resolve-DefaultZip {
  $here = Split-Path -Parent $PSCommandPath
  $match = Get-ChildItem -LiteralPath $here -File -Filter "DreamSeed-Code-*-Windows-Full.zip" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($match) { return $match.FullName }
  throw "DreamSeed Windows full package was not found next to setup-bootstrap.ps1."
}

function New-DesktopShortcut {
  param(
    [string]$ShortcutPath,
    [string]$DreamSeedCmd
  )
  $shell = New-Object -ComObject WScript.Shell
  $shortcut = $shell.CreateShortcut($ShortcutPath)
  $shortcut.TargetPath = "$env:ComSpec"
  $shortcut.Arguments = "/k `"`"$DreamSeedCmd`"`""
  $shortcut.WorkingDirectory = [Environment]::GetFolderPath("UserProfile")
  $shortcut.IconLocation = "$env:SystemRoot\System32\cmd.exe,0"
  $shortcut.Save()
}

function Resolve-PowerShellExe {
  $systemRoot = $env:SystemRoot
  if ($systemRoot) {
    $windowsPowerShell = Join-Path $systemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    if (Test-Path -LiteralPath $windowsPowerShell) { return $windowsPowerShell }
  }
  $cmd = Get-Command powershell.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  throw "Windows PowerShell was not found."
}

if (-not $PackageZip) { $PackageZip = $env:DREAMSEED_SETUP_PACKAGE_ZIP }
if (-not $PackageZip) { $PackageZip = Resolve-DefaultZip }
if (-not $InstallBase) { $InstallBase = $env:DREAMSEED_SETUP_BASE }
if (-not $InstallBase) { $InstallBase = Join-Path $env:LOCALAPPDATA "DreamSeedCode" }
if (-not $InstallRoot) { $InstallRoot = $env:DREAMSEED_SETUP_INSTALL_ROOT }
if (-not $InstallRoot) { $InstallRoot = Join-Path $env:LOCALAPPDATA "DreamSeed" }
if ($env:DREAMSEED_SETUP_NO_DESKTOP_SHORTCUT -eq "1") { $NoDesktopShortcut = $true }

$PackageZip = [System.IO.Path]::GetFullPath($PackageZip)
$InstallBase = [System.IO.Path]::GetFullPath($InstallBase)
$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$AppRoot = Join-Path $InstallBase "app"
$StageRoot = Join-Path $InstallBase "install-stage"
$Stage = Join-Path $StageRoot ([guid]::NewGuid().ToString("N"))
$Previous = Join-Path $InstallBase "app.previous"
$PowerShellExe = Resolve-PowerShellExe

if (-not (Test-Path -LiteralPath $PackageZip)) {
  throw "DreamSeed full package not found: $PackageZip"
}

Write-Host "DreamSeed Code Setup" -ForegroundColor Green
Write-Host "Package: $PackageZip"
Write-Host "App:     $AppRoot"
Write-Host "Data:    $InstallRoot"

Write-Step "Extracting DreamSeed Code"
New-Item -ItemType Directory -Force -Path $StageRoot | Out-Null
Remove-Tree $Stage
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
[System.IO.Compression.ZipFile]::ExtractToDirectory($PackageZip, $Stage)

$Installer = Join-Path $Stage "scripts\install-dreamseed.ps1"
$Agent = Join-Path $Stage "bin\dreamseed-agent.js"
$BundledNode = Join-Path $Stage "vendor\node\win-x64\node.exe"
$BundledPython = Join-Path $Stage "vendor\python\win-x64\python.exe"
$Wheelhouse = Join-Path $Stage "vendor\python-wheels"
foreach ($required in @($Installer, $Agent, $BundledNode, $BundledPython, $Wheelhouse)) {
  if (-not (Test-Path -LiteralPath $required)) {
    throw "Extracted package is incomplete: $required"
  }
}

Write-Step "Installing application files"
New-Item -ItemType Directory -Force -Path $InstallBase | Out-Null
Remove-Tree $Previous
if (Test-Path -LiteralPath $AppRoot) {
  Move-Item -LiteralPath $AppRoot -Destination $Previous -Force
}
Move-Item -LiteralPath $Stage -Destination $AppRoot -Force

try {
  Write-Step "Registering dreamseed command"
  & $PowerShellExe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $AppRoot "scripts\install-dreamseed.ps1") `
    -AppRoot $AppRoot `
    -InstallRoot $InstallRoot `
    -NoAutoInstall `
    -OfflinePythonDeps
  if ($LASTEXITCODE -ne 0) {
    throw "DreamSeed command installer failed with exit code $LASTEXITCODE."
  }

  $DreamSeedCmd = Join-Path $InstallRoot "bin\dreamseed.cmd"
  if (-not (Test-Path -LiteralPath $DreamSeedCmd)) {
    throw "dreamseed command was not created: $DreamSeedCmd"
  }

  if (-not $NoDesktopShortcut) {
    Write-Step "Creating desktop shortcut"
    $desktop = [Environment]::GetFolderPath("DesktopDirectory")
    if ($desktop) {
      New-DesktopShortcut -ShortcutPath (Join-Path $desktop "DreamSeed Code.lnk") -DreamSeedCmd $DreamSeedCmd
    }
  }

  Write-Host ""
  Write-Host "DreamSeed Code installed successfully." -ForegroundColor Green
  Write-Host "Open a new terminal and run: dreamseed"
  Write-Host "Or double-click the 'DreamSeed Code' desktop shortcut."
} catch {
  if (Test-Path -LiteralPath $AppRoot) {
    Remove-Tree $AppRoot
  }
  if (Test-Path -LiteralPath $Previous) {
    Move-Item -LiteralPath $Previous -Destination $AppRoot -Force
  }
  throw
} finally {
  Remove-Tree $Stage
  try {
    $remaining = Get-ChildItem -LiteralPath $StageRoot -Force -ErrorAction SilentlyContinue
    if (-not $remaining) { Remove-Item -LiteralPath $StageRoot -Force -ErrorAction SilentlyContinue }
  } catch {
  }
}
