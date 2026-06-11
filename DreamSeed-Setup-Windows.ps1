param(
  [string]$InstallPath = "",
  [string]$PackageUrl = "https://github.com/a2328275243/mempalace-evolve/raw/master/installers/DreamSeed-Code-0.1.0-Windows-x64.zip",
  [string]$ManifestUrl = "https://github.com/a2328275243/mempalace-evolve/raw/master/installers/dreamseed-update-manifest.json",
  [switch]$NoDesktopShortcut
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-ScriptRoot {
  if ($PSScriptRoot) { return $PSScriptRoot }
  return Split-Path -Parent $MyInvocation.MyCommand.Path
}

function Select-InstallPath {
  param([string]$Provided)
  if ($Provided) {
    return [System.IO.Path]::GetFullPath($Provided)
  }

  $Default = Join-Path $env:LOCALAPPDATA "DreamSeed\DreamSeed Code"
  try {
    Add-Type -AssemblyName System.Windows.Forms | Out-Null
    $Dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $Dialog.Description = "Choose where DreamSeed Code will be installed"
    $Dialog.SelectedPath = $Default
    $Dialog.ShowNewFolderButton = $true
    $Result = $Dialog.ShowDialog()
    if ($Result -eq [System.Windows.Forms.DialogResult]::OK -and $Dialog.SelectedPath) {
      return [System.IO.Path]::GetFullPath($Dialog.SelectedPath)
    }
  } catch {
    # Fall back to terminal prompt below.
  }

  $Typed = Read-Host "Install path [$Default]"
  if (-not $Typed) { $Typed = $Default }
  return [System.IO.Path]::GetFullPath($Typed)
}

function Resolve-Package {
  param(
    [string]$Url,
    [string]$TempRoot
  )

  $ScriptRoot = Get-ScriptRoot
  $LocalPackage = Join-Path $ScriptRoot "installers\DreamSeed-Code-0.1.0-Windows-x64.zip"
  if (Test-Path -LiteralPath $LocalPackage) {
    return [System.IO.Path]::GetFullPath($LocalPackage)
  }

  $PackagePath = Join-Path $TempRoot "DreamSeed-Code-Windows-x64.zip"
  Write-Host "Downloading DreamSeed Code package from $Url"
  Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $PackagePath
  return $PackagePath
}

function Assert-PackageHash {
  param(
    [string]$PackagePath,
    [string]$Manifest
  )
  try {
    $Data = Invoke-RestMethod -UseBasicParsing -Uri $Manifest
    $Expected = [string]$Data.package.sha256
    if (-not $Expected) { return }
    $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $PackagePath).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected.ToLowerInvariant()) {
      throw "SHA256 mismatch. expected=$Expected actual=$Actual"
    }
    Write-Host "Package SHA256 verified."
  } catch {
    if ($_.Exception.Message -like "SHA256 mismatch*") { throw }
    Write-Host "Package hash check skipped: $($_.Exception.Message)" -ForegroundColor Yellow
  }
}

$TargetRoot = Select-InstallPath -Provided $InstallPath
$LocalRoot = Join-Path $env:LOCALAPPDATA "DreamSeed"
$LogDir = Join-Path $LocalRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogPath = Join-Path $LogDir "dreamseed-installer.log"

try {
  Start-Transcript -LiteralPath $LogPath -Append | Out-Null
} catch {
  Write-Host "Installer log could not start: $LogPath"
}

try {
  Write-Host "DreamSeed Code Windows Installer" -ForegroundColor Green
  Write-Host "Install path: $TargetRoot"

  $TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("DreamSeedSetup-" + [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null

  Write-Step "Resolving package"
  $PackagePath = Resolve-Package -Url $PackageUrl -TempRoot $TempRoot
  Assert-PackageHash -PackagePath $PackagePath -Manifest $ManifestUrl

  Write-Step "Extracting package"
  $ExtractRoot = Join-Path $TempRoot "extract"
  Expand-Archive -LiteralPath $PackagePath -DestinationPath $ExtractRoot -Force
  $PackageDir = Get-ChildItem -LiteralPath $ExtractRoot -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "Install-DreamSeed-Code.ps1") } |
    Select-Object -First 1
  if (-not $PackageDir) {
    throw "DreamSeed package is invalid."
  }

  Write-Step "Installing desktop and terminal runtime"
  $Args = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $PackageDir.FullName "Install-DreamSeed-Code.ps1"),
    "-InstallPath", $TargetRoot
  )
  if ($NoDesktopShortcut) {
    $Args += "-NoDesktopShortcut"
  }
  & powershell.exe @Args

  Write-Host ""
  Write-Host "DreamSeed Code installed successfully." -ForegroundColor Green
  Write-Host "Desktop shortcut: DreamSeed Desktop"
  Write-Host "Command: dreamseed"
  Write-Host "Update later: dreamseed update"
  Write-Host "Local data root: $LocalRoot"
  Write-Host "Installer log: $LogPath"
} finally {
  try { Stop-Transcript | Out-Null } catch {}
}
