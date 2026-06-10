param(
  [switch]$Smoke,
  [switch]$Debug
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$AppRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LocalRoot = if ($env:DREAMSEED_LOCAL_ROOT) { $env:DREAMSEED_LOCAL_ROOT } else { Split-Path -Parent (Split-Path -Parent $AppRoot) }
if (-not $LocalRoot) {
  $LocalRoot = "D:\DreamSeed-Local-Agent"
}
$LogDir = Join-Path $LocalRoot "logs"
$LogFile = Join-Path $LogDir "dreamseed-desktop-launch.log"

try {
  if (-not (Test-Path -LiteralPath $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
  }
} catch {
  $FallbackLogDir = Join-Path $env:TEMP "DreamSeed-Local-Agent\logs"
  New-Item -ItemType Directory -Path $FallbackLogDir -Force | Out-Null
  $LogDir = $FallbackLogDir
  $LogFile = Join-Path $LogDir "dreamseed-desktop-launch.log"
}

function Write-LaunchLog([string]$Message) {
  try {
    "[$(Get-Date -Format o)] $Message" | Add-Content -LiteralPath $LogFile -Encoding UTF8
  } catch {
    try {
      $FallbackLogDir = Join-Path $env:TEMP "DreamSeed-Local-Agent\logs"
      New-Item -ItemType Directory -Path $FallbackLogDir -Force | Out-Null
      $FallbackLogFile = Join-Path $FallbackLogDir "dreamseed-desktop-launch.log"
      "[$(Get-Date -Format o)] $Message" | Add-Content -LiteralPath $FallbackLogFile -Encoding UTF8
      $script:LogFile = $FallbackLogFile
      $script:LogDir = $FallbackLogDir
    } catch {
      # Launch logging must never stop the desktop app from starting.
    }
  }
}

function Resolve-Node {
  $Candidates = @(
    (Join-Path $LocalRoot "node\node.exe"),
    (Join-Path $AppRoot "node\node.exe"),
    "D:\clcude\node\node.exe"
  )
  foreach ($Candidate in $Candidates) {
    if ($Candidate -and (Test-Path -LiteralPath $Candidate)) {
      return $Candidate
    }
  }
  $Command = Get-Command node -ErrorAction SilentlyContinue
  if ($Command) {
    return $Command.Source
  }
  return $null
}

function Resolve-Electron {
  $ElectronExe = Join-Path $AppRoot "node_modules\electron\dist\electron.exe"
  if (Test-Path -LiteralPath $ElectronExe) {
    return $ElectronExe
  }
  return $null
}

try {
  $Node = Resolve-Node
  if (-not $Node) {
    throw "Node.js was not found. Run npm install in $AppRoot, or install Node.js 18+."
  }
  $Electron = Resolve-Electron

  $Script = Join-Path $AppRoot "scripts\dreamseed_desktop.mjs"
  $Main = Join-Path $AppRoot "desktop\electron-main.mjs"
  if (-not (Test-Path -LiteralPath $Script)) {
    throw "Desktop script not found: $Script"
  }
  if (-not (Test-Path -LiteralPath $Main)) {
    throw "Desktop main process not found: $Main"
  }

  Write-LaunchLog "Launching DreamSeed Desktop"
  Write-LaunchLog "APP_ROOT=$AppRoot"
  Write-LaunchLog "LOCAL_ROOT=$LocalRoot"
  Write-LaunchLog "NODE=$Node"
  Write-LaunchLog "ELECTRON=$Electron"

  if ($Smoke) {
    & $Node $Script --smoke
    exit $LASTEXITCODE
  }

  if ($Debug) {
    if ($Electron) {
      & $Electron $Main
    } else {
      & $Node $Script
    }
    exit $LASTEXITCODE
  }

  $StdOut = Join-Path $LogDir "dreamseed-desktop.stdout.log"
  $StdErr = Join-Path $LogDir "dreamseed-desktop.stderr.log"
  $Env:DreamSeed_Local_Root = $LocalRoot
  $Env:DREAMSEED_LOCAL_ROOT = $LocalRoot
  $Env:DREAMSEED_APP_ROOT = $AppRoot
  $Env:DREAMSEED_NODE = $Node
  $Env:DREAMSEED_PROVIDER_CONFIG = Join-Path $LocalRoot "config\providers.local.json"
  if ($Electron) {
    Start-Process -FilePath $Electron `
      -ArgumentList @($Main) `
      -WorkingDirectory $AppRoot | Out-Null
    Write-LaunchLog "Started desktop electron process directly."
    exit 0
  }

  Start-Process -FilePath $Node `
    -ArgumentList @($Script) `
    -WorkingDirectory $AppRoot `
    -RedirectStandardOutput $StdOut `
    -RedirectStandardError $StdErr | Out-Null
  Write-LaunchLog "Started desktop process. stdout=$StdOut stderr=$StdErr"
} catch {
  $Message = "DreamSeed Desktop failed to start: $($_.Exception.Message)`nLog: $LogFile"
  Write-LaunchLog $Message
  try {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($Message, "DreamSeed Desktop") | Out-Null
  } catch {
    Write-Error $Message
  }
  exit 1
}
