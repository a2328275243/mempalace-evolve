param(
  [string]$InstallPath = "",
  [string]$SourceUrl = "https://github.com/a2328275243/mempalace-evolve/archive/refs/heads/master.zip",
  [string]$AgentKitUrl = "https://github.com/a2328275243/mempalace-evolve/raw/master/installers/dreamseed-code-agent-kit-v0.1.0.zip",
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

function Find-LocalRepo {
  $Root = Get-ScriptRoot
  $Candidates = @(
    $Root,
    (Split-Path -Parent $Root)
  )
  foreach ($Candidate in $Candidates) {
    if (-not $Candidate) { continue }
    $Project = Join-Path $Candidate "pyproject.toml"
    $MemorySource = Join-Path $Candidate "src\mempalace_evolve"
    if ((Test-Path -LiteralPath $Project) -and (Test-Path -LiteralPath $MemorySource)) {
      return [System.IO.Path]::GetFullPath($Candidate)
    }
  }
  return $null
}

function Select-InstallPath {
  param([string]$Provided)

  if ($Provided) {
    return [System.IO.Path]::GetFullPath($Provided)
  }

  $Default = Join-Path $env:LOCALAPPDATA "DreamSeed"

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

function Require-Command {
  param(
    [string]$Name,
    [string]$Hint
  )
  $Cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if (-not $Cmd) {
    throw "$Name was not found. $Hint"
  }
  return $Cmd.Source
}

function Get-PythonCommand {
  $Python = Get-Command python -ErrorAction SilentlyContinue
  if ($Python) {
    return @($Python.Source)
  }
  $Py = Get-Command py -ErrorAction SilentlyContinue
  if ($Py) {
    return @($Py.Source, "-3")
  }
  throw "Python 3.10+ was not found. Install Python, then run this installer again."
}

function Copy-RepoSource {
  param(
    [string]$Source,
    [string]$Destination
  )

  $ResolvedSource = [System.IO.Path]::GetFullPath($Source)
  $ResolvedDestination = [System.IO.Path]::GetFullPath($Destination)
  if ($ResolvedSource.TrimEnd("\") -ieq $ResolvedDestination.TrimEnd("\")) {
    Write-Host "Using current source folder: $ResolvedSource"
    return
  }

  New-Item -ItemType Directory -Force -Path $ResolvedDestination | Out-Null

  $ExcludeDirs = @(
    ".git", "node_modules", "dist", "build", ".venv", "venv", "env",
    "logs", "cache", "legacy-history", "memory-candidates",
    "self-evolve-candidates", "self-evolve-backups",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", "__pycache__"
  )
  $ExcludeFiles = @(
    "providers.local.json", ".env", "*.pyc", "*.pyo", "*.log",
    "*.sqlite3", "*.db", "chroma.sqlite3"
  )

  $Args = @($ResolvedSource, $ResolvedDestination, "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP")
  $Args += "/XD"
  $Args += $ExcludeDirs
  $Args += "/XF"
  $Args += $ExcludeFiles

  & robocopy @Args | Out-Null
  $Code = $LASTEXITCODE
  if ($Code -gt 7) {
    throw "Failed to copy DreamSeed source. Robocopy exit code: $Code"
  }
}

function Download-RepoSource {
  param(
    [string]$Url,
    [string]$TempRoot
  )

  New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
  $ZipPath = Join-Path $TempRoot "mempalace-evolve.zip"
  $ExtractPath = Join-Path $TempRoot "source"

  Write-Host "Downloading source from $Url"
  Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $ZipPath
  Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractPath -Force

  $Repo = Get-ChildItem -LiteralPath $ExtractPath -Directory |
    Where-Object {
      (Test-Path -LiteralPath (Join-Path $_.FullName "pyproject.toml")) -and
      (Test-Path -LiteralPath (Join-Path $_.FullName "src\mempalace_evolve"))
    } |
    Select-Object -First 1

  if (-not $Repo) {
    throw "Downloaded archive did not contain MemPalace source."
  }
  return $Repo.FullName
}

function Resolve-AgentKit {
  param(
    [string]$SourceRoot,
    [string]$Url,
    [string]$TempRoot
  )

  $LocalKit = Join-Path $SourceRoot "installers\dreamseed-code-agent-kit-v0.1.0.zip"
  if (Test-Path -LiteralPath $LocalKit) {
    return [System.IO.Path]::GetFullPath($LocalKit)
  }

  New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
  $KitPath = Join-Path $TempRoot "dreamseed-code-agent-kit-v0.1.0.zip"
  Write-Host "Downloading DreamSeed agent kit from $Url"
  Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $KitPath
  return $KitPath
}

function Expand-AgentKit {
  param(
    [string]$KitPath,
    [string]$Destination
  )

  $ExtractPath = Join-Path ([System.IO.Path]::GetTempPath()) ("DreamSeedAgentKit-" + [guid]::NewGuid().ToString("N"))
  Expand-Archive -LiteralPath $KitPath -DestinationPath $ExtractPath -Force
  $Layer = Get-ChildItem -LiteralPath $ExtractPath -Directory -Recurse |
    Where-Object { $_.Name -eq "dreamseed-layer" -and (Test-Path -LiteralPath (Join-Path $_.FullName "bin\dreamseed-agent.js")) } |
    Select-Object -First 1

  if (-not $Layer) {
    throw "DreamSeed agent kit is invalid: $KitPath"
  }

  Copy-RepoSource -Source $Layer.FullName -Destination $Destination
}

$InstallRoot = Select-InstallPath -Provided $InstallPath
$AppRoot = Join-Path $InstallRoot "app\mempalace-evolve"
$LocalRoot = Join-Path $InstallRoot "local"
$DreamSeedLayer = Join-Path $InstallRoot "agent\dreamseed-layer"
$LogDir = Join-Path $env:APPDATA "DreamSeed\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogPath = Join-Path $LogDir "dreamseed-installer.log"

try {
  Start-Transcript -LiteralPath $LogPath -Append | Out-Null
} catch {
  Write-Host "Installer log could not start: $LogPath"
}

try {
  Write-Host "DreamSeed Code Windows Installer" -ForegroundColor Green
  Write-Host "Install path: $InstallRoot"

  Write-Step "Checking prerequisites"
  $PythonCmd = Get-PythonCommand
  $Node = Require-Command -Name "node" -Hint "Install Node.js 18+ from https://nodejs.org/"
  $Npm = Require-Command -Name "npm.cmd" -Hint "Install Node.js 18+ with npm."
  Write-Host "Python: $($PythonCmd -join ' ')"
  Write-Host "Node: $Node"
  Write-Host "npm: $Npm"

  Write-Step "Preparing source"
  $LocalRepo = Find-LocalRepo
  $TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("DreamSeedSetup-" + [guid]::NewGuid().ToString("N"))
  if ($LocalRepo) {
    Write-Host "Local repository detected: $LocalRepo"
    $SourceRoot = $LocalRepo
  } else {
    $SourceRoot = Download-RepoSource -Url $SourceUrl -TempRoot $TempRoot
  }
  Copy-RepoSource -Source $SourceRoot -Destination $AppRoot

  if (-not (Test-Path -LiteralPath (Join-Path $DreamSeedLayer "bin\dreamseed-agent.js"))) {
    Write-Step "Installing DreamSeed agent kit"
    $KitPath = Resolve-AgentKit -SourceRoot $SourceRoot -Url $AgentKitUrl -TempRoot $TempRoot
    Expand-AgentKit -KitPath $KitPath -Destination $DreamSeedLayer
  }

  if (-not (Test-Path -LiteralPath (Join-Path $DreamSeedLayer "bin\dreamseed-agent.js"))) {
    throw "DreamSeed agent kit is incomplete: $DreamSeedLayer"
  }

  Write-Step "Installing bundled MemPalace memory runtime with MCP/API support"
  $PythonExe = $PythonCmd[0]
  $PythonArgs = @()
  if ($PythonCmd.Count -gt 1) {
    $PythonArgs = $PythonCmd[1..($PythonCmd.Count - 1)]
  }
  & $PythonExe @PythonArgs -m pip install -e "$AppRoot[api,mcp]"

  Write-Step "Installing desktop dependencies"
  Push-Location $DreamSeedLayer
  try {
    & $Npm install
  } finally {
    Pop-Location
  }

  Write-Step "Creating dreamseed command and desktop shortcut"
  $InstallScript = Join-Path $DreamSeedLayer "scripts\install-dreamseed.ps1"
  $InstallArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", $InstallScript,
    "-InstallRoot", $LocalRoot,
    "-AppRoot", $DreamSeedLayer,
    "-AddToUserPath"
  )
  if (-not $NoDesktopShortcut) {
    $InstallArgs += "-DesktopShortcut"
  }
  & powershell.exe @InstallArgs

  Write-Host ""
  Write-Host "DreamSeed Code installed successfully." -ForegroundColor Green
  Write-Host "Desktop shortcut: DreamSeed Desktop"
  Write-Host "Command: dreamseed"
  Write-Host "Open a new terminal before using dreamseed from PATH."
  Write-Host "Installer log: $LogPath"
} finally {
  try { Stop-Transcript | Out-Null } catch {}
}
