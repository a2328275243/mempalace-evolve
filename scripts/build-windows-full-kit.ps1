param(
  [string]$Version = "",
  [string]$NodeVersion = "",
  [string]$PythonVersion = "",
  [string]$NodeSource = "",
  [string]$PythonSource = "",
  [string]$DistDir = "",
  [string]$CacheDir = "",
  [switch]$Clean,
  [switch]$SkipDownloads,
  [switch]$SkipWheelhouse,
  [switch]$RunOfflineSmoke
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression.FileSystem

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PackageJson = Get-Content -LiteralPath (Join-Path $RepoRoot "package.json") -Raw | ConvertFrom-Json
if (-not $Version) { $Version = $PackageJson.version }
if (-not $DistDir) { $DistDir = Join-Path $RepoRoot "dist" }
if (-not $CacheDir) { $CacheDir = Join-Path ([System.IO.Path]::GetTempPath()) "dreamseed-full-kit-cache" }

$VendorDir = Join-Path $RepoRoot "vendor"
$NodeDir = Join-Path $VendorDir "node\win-x64"
$PythonDir = Join-Path $VendorDir "python\win-x64"
$Wheelhouse = Join-Path $VendorDir "python-wheels"
$NodeExe = Join-Path $NodeDir "node.exe"
$PythonExe = Join-Path $PythonDir "python.exe"
$OutZip = Join-Path $DistDir "DreamSeed-Code-$Version-Windows-Full.zip"

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Remove-Tree {
  param([string]$Path)
  if (Test-Path -LiteralPath $Path) {
    Remove-Item -LiteralPath $Path -Recurse -Force
  }
}

function Copy-DirectoryContents {
  param([string]$Source, [string]$Destination)
  if (-not (Test-Path -LiteralPath $Source)) {
    throw "Source directory not found: $Source"
  }
  $sourceFull = [System.IO.Path]::GetFullPath($Source).TrimEnd('\', '/')
  $destFull = [System.IO.Path]::GetFullPath($Destination).TrimEnd('\', '/')
  if ($sourceFull -ieq $destFull) {
    Write-Host "Source and destination are the same; reusing: $Destination" -ForegroundColor Yellow
    return
  }
  Remove-Tree $Destination
  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
  }
}

function Download-File {
  param([string]$Url, [string]$Destination)
  if ($SkipDownloads) {
    throw "Download needed but -SkipDownloads was set: $Url"
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Write-Host "Downloading: $Url" -ForegroundColor DarkCyan
  Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
}

function Expand-ZipTo {
  param([string]$ZipPath, [string]$Destination)
  Remove-Tree $Destination
  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $Destination)
}

function Find-FirstFile {
  param([string]$Root, [string]$Name)
  return Get-ChildItem -LiteralPath $Root -Recurse -File -Filter $Name -ErrorAction SilentlyContinue |
    Select-Object -First 1
}

function Resolve-LatestNodeVersion {
  if ($NodeVersion) { return $NodeVersion.TrimStart("v") }
  try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $index = Invoke-RestMethod -Uri "https://nodejs.org/dist/index.json" -UseBasicParsing
    $latest = $index |
      Where-Object { $_.lts -and ($_.files -contains "win-x64") } |
      Select-Object -First 1
    if ($latest -and $latest.version) {
      return ([string]$latest.version).TrimStart("v")
    }
  } catch {
    Write-Host "Could not query latest Node.js; falling back to 22.16.0." -ForegroundColor Yellow
  }
  return "22.16.0"
}

function Resolve-LatestPythonVersion {
  if ($PythonVersion) { return $PythonVersion }
  try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $index = Invoke-RestMethod -Uri "https://api.nuget.org/v3-flatcontainer/python/index.json" -UseBasicParsing
    $latest = $index.versions |
      Where-Object { $_ -match '^3\.12\.\d+$' } |
      Sort-Object { [version]$_ } -Descending |
      Select-Object -First 1
    if ($latest) { return [string]$latest }
  } catch {
    Write-Host "Could not query latest Python NuGet package; falling back to 3.12.10." -ForegroundColor Yellow
  }
  return "3.12.10"
}

function Install-NodeRuntime {
  Write-Step "Preparing bundled Node.js"
  if ($NodeSource) {
    $sourceItem = Get-Item -LiteralPath $NodeSource -ErrorAction Stop
    if ($sourceItem.PSIsContainer) {
      Copy-DirectoryContents $sourceItem.FullName $NodeDir
    } elseif ($sourceItem.Extension -ieq ".zip") {
      $tmp = Join-Path $CacheDir "node-source-expanded"
      Expand-ZipTo $sourceItem.FullName $tmp
      $nodeFile = Find-FirstFile $tmp "node.exe"
      if (-not $nodeFile) { throw "node.exe was not found in $NodeSource" }
      Copy-DirectoryContents $nodeFile.Directory.FullName $NodeDir
    } elseif ($sourceItem.Name -ieq "node.exe") {
      Copy-DirectoryContents $sourceItem.Directory.FullName $NodeDir
    } else {
      throw "Unsupported NodeSource: $NodeSource"
    }
  } else {
    $resolved = Resolve-LatestNodeVersion
    $zip = Join-Path $CacheDir "node-v$resolved-win-x64.zip"
    if (-not (Test-Path -LiteralPath $zip)) {
      Download-File "https://nodejs.org/dist/v$resolved/node-v$resolved-win-x64.zip" $zip
    }
    $tmp = Join-Path $CacheDir "node-v$resolved-win-x64"
    Expand-ZipTo $zip $tmp
    $nodeFile = Find-FirstFile $tmp "node.exe"
    if (-not $nodeFile) { throw "node.exe was not found in downloaded Node archive." }
    Copy-DirectoryContents $nodeFile.Directory.FullName $NodeDir
  }
  if (-not (Test-Path -LiteralPath $NodeExe)) { throw "Bundled Node was not prepared: $NodeExe" }
  & $NodeExe --version
}

function Install-PythonRuntime {
  Write-Step "Preparing bundled Python"
  if ($PythonSource) {
    $sourceItem = Get-Item -LiteralPath $PythonSource -ErrorAction Stop
    if ($sourceItem.PSIsContainer) {
      Copy-DirectoryContents $sourceItem.FullName $PythonDir
    } elseif ($sourceItem.Extension -in @(".zip", ".nupkg")) {
      $tmp = Join-Path $CacheDir "python-source-expanded"
      Expand-ZipTo $sourceItem.FullName $tmp
      $pythonFile = Find-FirstFile $tmp "python.exe"
      if (-not $pythonFile) { throw "python.exe was not found in $PythonSource" }
      Copy-DirectoryContents $pythonFile.Directory.FullName $PythonDir
    } elseif ($sourceItem.Name -ieq "python.exe") {
      Copy-DirectoryContents $sourceItem.Directory.FullName $PythonDir
    } else {
      throw "Unsupported PythonSource: $PythonSource"
    }
  } else {
    $resolved = Resolve-LatestPythonVersion
    $zip = Join-Path $CacheDir "python.$resolved.nupkg.zip"
    if (-not (Test-Path -LiteralPath $zip)) {
      Download-File "https://www.nuget.org/api/v2/package/python/$resolved" $zip
    }
    $tmp = Join-Path $CacheDir "python.$resolved"
    Expand-ZipTo $zip $tmp
    $pythonFile = Find-FirstFile $tmp "python.exe"
    if (-not $pythonFile) { throw "python.exe was not found in downloaded Python package." }
    Copy-DirectoryContents $pythonFile.Directory.FullName $PythonDir
  }
  if (-not (Test-Path -LiteralPath $PythonExe)) { throw "Bundled Python was not prepared: $PythonExe" }
  & $PythonExe --version
  & $PythonExe -m pip --version
}

function Build-Wheelhouse {
  if ($SkipWheelhouse) {
    Write-Host "Skipping wheelhouse build." -ForegroundColor Yellow
    return
  }
  Write-Step "Building offline Python wheelhouse"
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\build-python-wheelhouse.ps1") `
    -Python $PythonExe `
    -Wheelhouse $Wheelhouse `
    -MempalaceSource $RepoRoot `
    -Clean
  if ($LASTEXITCODE -ne 0) {
    throw "Wheelhouse build failed with exit code $LASTEXITCODE."
  }
  $wheelCount = (Get-ChildItem -LiteralPath $Wheelhouse -File -Filter "*.whl" -ErrorAction SilentlyContinue | Measure-Object).Count
  if ($wheelCount -lt 3) {
    throw "Wheelhouse looks incomplete: $Wheelhouse"
  }
  Write-Host "Wheelhouse wheels: $wheelCount" -ForegroundColor Green
}

function New-FullKitZip {
  Write-Step "Creating full offline kit"
  New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
  $stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) "dreamseed-full-kit-stage"
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss-ffff"
  $stage = Join-Path $stageRoot "DreamSeed-Code-$Version-Windows-Full-$stamp"
  $sourceZip = Join-Path $stageRoot "source-$stamp.zip"
  Remove-Tree $stage
  New-Item -ItemType Directory -Force -Path $stageRoot, $stage | Out-Null

  Push-Location $RepoRoot
  try {
    git archive --format=zip --output=$sourceZip HEAD
  } finally {
    Pop-Location
  }
  Expand-Archive -LiteralPath $sourceZip -DestinationPath $stage -Force
  Remove-Item -LiteralPath $sourceZip -Force

  New-Item -ItemType Directory -Force -Path (Join-Path $stage "vendor") | Out-Null
  Copy-Item -LiteralPath (Join-Path $VendorDir "node") -Destination (Join-Path $stage "vendor") -Recurse -Force
  Copy-Item -LiteralPath (Join-Path $VendorDir "python") -Destination (Join-Path $stage "vendor") -Recurse -Force
  Copy-Item -LiteralPath $Wheelhouse -Destination (Join-Path $stage "vendor") -Recurse -Force

  $kitReadme = @(
    '# DreamSeed Code Windows Full Kit',
    '',
    'This package includes portable Node.js, portable Python, and a Python wheelhouse.',
    'Install from PowerShell:',
    '',
    '```powershell',
    'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-dreamseed.ps1',
    'dreamseed --help',
    '```',
    '',
    'The installer uses bundled runtimes first. It falls back to system runtimes and winget only if bundled files are missing.'
  ) -join [Environment]::NewLine
  Set-Content -LiteralPath (Join-Path $stage "FULL-KIT.md") -Value $kitReadme -Encoding UTF8

  $private = Get-ChildItem -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object {
      $_.FullName -match '(providers\.local|legacy-history|memory-candidates|self-evolve-candidates|self-evolve-backups|\.dreamseed-memory|node_modules|\.git\\)'
    }
  if ($private) {
    $private | Select-Object FullName
    throw "Private or forbidden files were found in the full kit stage."
  }

  $tmpZip = Join-Path $stageRoot "DreamSeed-Code-$Version-Windows-Full-$stamp.zip"
  if (Test-Path -LiteralPath $OutZip) { Remove-Item -LiteralPath $OutZip -Force }
  Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $tmpZip -Force
  Move-Item -LiteralPath $tmpZip -Destination $OutZip -Force
  Write-Host "Full kit ready: $OutZip" -ForegroundColor Green
}

function Invoke-OfflineSmoke {
  if (-not $RunOfflineSmoke) { return }
  Write-Step "Running offline full-kit smoke"
  $smokeRoot = Join-Path ([System.IO.Path]::GetTempPath()) "dreamseed-full-kit-smoke"
  Remove-Tree $smokeRoot
  New-Item -ItemType Directory -Force -Path $smokeRoot | Out-Null
  Expand-Archive -LiteralPath $OutZip -DestinationPath (Join-Path $smokeRoot "app") -Force
  $installRoot = Join-Path $smokeRoot "local"
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $smokeRoot "app\scripts\install-dreamseed.ps1") `
    -InstallRoot $installRoot `
    -NoAutoInstall `
    -OfflinePythonDeps `
    -NoPathUpdate
  if ($LASTEXITCODE -ne 0) {
    throw "Offline smoke installer failed with exit code $LASTEXITCODE."
  }
  & (Join-Path $installRoot "bin\dreamseed.cmd") --help | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Offline smoke dreamseed --help failed with exit code $LASTEXITCODE."
  }
  Remove-Tree $smokeRoot
  Write-Host "Offline full-kit smoke passed." -ForegroundColor Green
}

if ($Clean) {
  Remove-Tree (Join-Path $VendorDir "node")
  Remove-Tree (Join-Path $VendorDir "python")
  Remove-Tree $Wheelhouse
}

New-Item -ItemType Directory -Force -Path $VendorDir, $CacheDir | Out-Null
Install-NodeRuntime
Install-PythonRuntime
Build-Wheelhouse
New-FullKitZip
Invoke-OfflineSmoke
