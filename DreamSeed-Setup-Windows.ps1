param(
  [string]$InstallPath = "",
  [string]$PackageUrl = "https://github.com/a2328275243/mempalace-evolve/releases/download/dreamseed-code-v0.1.1/DreamSeed-Code-0.1.1-Windows-x64.zip",
  [string]$ManifestUrl = "https://github.com/a2328275243/mempalace-evolve/raw/master/installers/dreamseed-update-manifest.json",
  [string]$Proxy = "",
  [switch]$NoDesktopShortcut
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-ScriptRoot {
  if ($PSScriptRoot) { return $PSScriptRoot }
  return Split-Path -Parent $MyInvocation.MyCommand.Path
}

function Resolve-PowerShell {
  $Candidates = @(
    $env:DREAMSEED_POWERSHELL,
    (Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"),
    (Join-Path $env:SystemRoot "Sysnative\WindowsPowerShell\v1.0\powershell.exe"),
    "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    "powershell.exe"
  )
  foreach ($Candidate in $Candidates) {
    if (-not $Candidate) { continue }
    if ($Candidate -eq "powershell.exe") { return $Candidate }
    if (Test-Path -LiteralPath $Candidate) { return $Candidate }
  }
  return "powershell.exe"
}

function Get-DownloadProxy {
  if ($Proxy) { return $Proxy }
  if ($env:DREAMSEED_DOWNLOAD_PROXY) { return $env:DREAMSEED_DOWNLOAD_PROXY }
  if ($env:HTTPS_PROXY) { return $env:HTTPS_PROXY }
  if ($env:HTTP_PROXY) { return $env:HTTP_PROXY }
  return ""
}

function Get-PackageUrls {
  param([string]$PrimaryUrl)
  $Urls = @()
  if ($PrimaryUrl) { $Urls += $PrimaryUrl }
  $Urls += "https://github.com/a2328275243/mempalace-evolve/raw/master/installers/DreamSeed-Code-0.1.1-Windows-x64.zip"
  $Urls | Where-Object { $_ } | Select-Object -Unique
}

function Test-CompletePackage {
  param([string]$Path)
  if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return $false }
  $Info = Get-Item -LiteralPath $Path
  return $Info.Length -gt 104857600
}

function Invoke-DreamSeedDownload {
  param(
    [string]$Url,
    [string]$Destination
  )
  $DownloadProxy = Get-DownloadProxy
  $Curl = Get-Command curl.exe -ErrorAction SilentlyContinue
  if ($Curl) {
    $CurlArgs = @("-L", "--fail", "--retry", "5", "--connect-timeout", "20", "-C", "-", "-o", $Destination)
    if ($DownloadProxy) { $CurlArgs += @("--proxy", $DownloadProxy) }
    $CurlArgs += $Url
    Write-Host "Downloading with curl.exe. If this is slow, set HTTPS_PROXY or DREAMSEED_DOWNLOAD_PROXY." -ForegroundColor Cyan
    & $Curl.Source @CurlArgs
    if ($LASTEXITCODE -eq 0 -and (Test-CompletePackage -Path $Destination)) { return }
    Write-Host "curl.exe download did not complete; trying the next downloader." -ForegroundColor Yellow
  }

  if (Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) {
    try {
      Write-Host "Downloading with BITS transfer." -ForegroundColor Cyan
      $BitsArgs = @{ Source = $Url; Destination = $Destination; ErrorAction = "Stop" }
      if ($DownloadProxy) { Write-Host "BITS uses the Windows proxy settings; explicit proxy is only used by curl/PowerShell." -ForegroundColor Yellow }
      Start-BitsTransfer @BitsArgs
      if (Test-CompletePackage -Path $Destination) { return }
    } catch {
      Write-Host "BITS download failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
  }

  Write-Host "Downloading with PowerShell web request." -ForegroundColor Cyan
  $WebArgs = @{ UseBasicParsing = $true; Uri = $Url; OutFile = $Destination; TimeoutSec = 900 }
  if ($DownloadProxy) {
    $WebArgs.Proxy = $DownloadProxy
    $WebArgs.ProxyUseDefaultCredentials = $true
  }
  Invoke-WebRequest @WebArgs
  if (-not (Test-CompletePackage -Path $Destination)) {
    throw "Downloaded package is incomplete. Check network/proxy, then rerun the installer; partial curl downloads can resume."
  }
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
  $LocalPackage = Join-Path $ScriptRoot "installers\DreamSeed-Code-0.1.1-Windows-x64.zip"
  if (Test-CompletePackage -Path $LocalPackage) {
    return [System.IO.Path]::GetFullPath($LocalPackage)
  }
  if (Test-Path -LiteralPath $LocalPackage) {
    Write-Host "Local package is incomplete or a Git LFS pointer; downloading the full package." -ForegroundColor Yellow
  }

  $PackagePath = Join-Path $TempRoot "DreamSeed-Code-Windows-x64.zip"
  foreach ($CandidateUrl in Get-PackageUrls -PrimaryUrl $Url) {
    try {
      Write-Host "Downloading DreamSeed Code package from $CandidateUrl"
      Invoke-DreamSeedDownload -Url $CandidateUrl -Destination $PackagePath
      return $PackagePath
    } catch {
      Write-Host "Download failed: $($_.Exception.Message)" -ForegroundColor Yellow
      Remove-Item -LiteralPath $PackagePath -Force -ErrorAction SilentlyContinue
    }
  }
  throw "DreamSeed package download failed. Put DreamSeed-Code-0.1.1-Windows-x64.zip under the installers folder, or rerun with -Proxy http://127.0.0.1:7897."
}

function Assert-PackageHash {
  param(
    [string]$PackagePath,
    [string]$Manifest
  )
  try {
    $Data = if (Test-Path -LiteralPath $Manifest) {
      Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
    } else {
      Invoke-RestMethod -UseBasicParsing -Uri $Manifest
    }
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
  $PowerShell = Resolve-PowerShell
  & $PowerShell @Args

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
