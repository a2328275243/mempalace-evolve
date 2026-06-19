param(
  [string]$InstallPath = "",
  [string]$ManifestUrl = "https://api.github.com/repos/a2328275243/mempalace-evolve/commits/master",
  [switch]$CheckOnly,
  [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor 3072
} catch {
  try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}
}

function Get-CurrentVersion {
  param([string]$Root)
  $Pkg = Join-Path $Root "package.json"
  if (-not (Test-Path -LiteralPath $Pkg)) { return "0.0.0" }
  try {
    $Obj = Get-Content -LiteralPath $Pkg -Raw | ConvertFrom-Json
    return [string]$Obj.version
  } catch { return "0.0.0" }
}

function Get-WebRequestArgs {
  $Proxy = $env:DREAMSEED_UPDATE_PROXY
  if (-not $Proxy) { $Proxy = $env:HTTPS_PROXY }
  if (-not $Proxy) { $Proxy = $env:HTTP_PROXY }
  if ($Proxy) { return @{ Proxy = $Proxy; ProxyUseDefaultCredentials = $true } }
  return @{}
}

function Resolve-RepoRoot {
  $ScriptDir = Split-Path -Parent $PSCommandPath
  $Root = Split-Path -Parent $ScriptDir
  if (Test-Path -LiteralPath (Join-Path $Root ".git")) { return $Root }
  $EnvRoot = $env:DREAMSEED_APP_ROOT
  if ($EnvRoot -and (Test-Path -LiteralPath (Join-Path $EnvRoot ".git"))) { return $EnvRoot }
  return $Root
}

$RepoRoot = Resolve-RepoRoot
$LocalRoot = if ($env:DREAMSEED_LOCAL_ROOT) { $env:DREAMSEED_LOCAL_ROOT } else { Join-Path $env:LOCALAPPDATA "DreamSeed" }
$LogDir = Join-Path $LocalRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogPath = Join-Path $LogDir "dreamseed-update.log"
Start-Transcript -LiteralPath $LogPath -Append | Out-Null

try {
  Write-Host "Checking DreamSeed updates..."

  if ($CheckOnly) {
    try {
      $WebArgs = Get-WebRequestArgs
      $Headers = @{ "User-Agent" = "DreamSeed-Update-Check" }
      $Latest = Invoke-RestMethod -UseBasicParsing -Uri $ManifestUrl @WebArgs -Headers $Headers -ErrorAction Stop
      $LatestSha = [string]$Latest.sha
      $LatestDate = [string]$Latest.commit.committer.date
      $Current = Get-CurrentVersion -Root $RepoRoot
      Write-Host "Current version: $Current"
      Write-Host "Latest commit:   $LatestSha ($LatestDate)"
      $Git = Get-Command git -ErrorAction SilentlyContinue
      if ($Git) {
        try {
          Push-Location $RepoRoot
          $LocalSha = (git rev-parse HEAD 2>$null).Trim()
          $RemoteName = (git remote 2>$null | Select-Object -First 1)
          if ($RemoteName) {
            git fetch $RemoteName 2>$null | Out-Null
            $BehindCount = [int](git rev-list --count "HEAD..$RemoteName/master" 2>$null)
            if ($BehindCount -gt 0) {
              Write-Host "Update available: $BehindCount commit(s) behind upstream." -ForegroundColor Yellow
              Write-Host "Run 'dreamseed update' to pull and reinstall."
            } else {
              Write-Host "DreamSeed is up to date (commit $LocalSha)."
            }
          } else {
            Write-Host "No git remote configured. Latest upstream commit: $LatestSha"
          }
          Pop-Location
        } catch {
          Write-Host "Update check (git): $($_.Exception.Message)" -ForegroundColor Yellow
        }
      } else {
        Write-Host "git not found. Latest upstream commit: $LatestSha"
      }
    } catch {
      Write-Host "Update check unavailable: $($_.Exception.Message)" -ForegroundColor Yellow
      Write-Host "DreamSeed Code remains usable."
    }
    return
  }

  $Git = Get-Command git -ErrorAction SilentlyContinue
  if (-not $Git) {
    throw "git is required for updates. Install Git for Windows from https://git-scm.com/downloads/win"
  }

  Push-Location $RepoRoot
  try {
    Write-Host "Fetching latest changes..."
    git fetch --all 2>&1 | ForEach-Object { Write-Host $_ }

    $RemoteName = (git remote 2>$null | Select-Object -First 1)
    if (-not $RemoteName) {
      throw "No git remote configured in $RepoRoot. Re-clone the repository instead."
    }

    $CurrentBranch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
    Write-Host "Pulling from $RemoteName/$CurrentBranch..."
    git pull $RemoteName $CurrentBranch 2>&1 | ForEach-Object { Write-Host $_ }

    if ($LASTEXITCODE -ne 0) {
      throw "git pull failed. Resolve conflicts manually in $RepoRoot"
    }

    $ReqFile = Join-Path $RepoRoot "requirements-dreamseed.txt"
    if (Test-Path -LiteralPath $ReqFile) {
      $Py = Get-Command python -ErrorAction SilentlyContinue
      if (-not $Py) { $Py = Get-Command py -ErrorAction SilentlyContinue }
      if ($Py) {
        Write-Host "Reinstalling Python dependencies..."
        & $Py.Source -m pip install -r $ReqFile --quiet 2>&1 | ForEach-Object { Write-Host $_ }
      }
    }

    $InstallScript = Join-Path $RepoRoot "scripts\install-dreamseed.ps1"
    if (Test-Path -LiteralPath $InstallScript) {
      Write-Host "Refreshing launcher shim..."
      & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $InstallScript -AddToUserPath 2>&1 | ForEach-Object { Write-Host $_ }
    }

    $NewVersion = Get-CurrentVersion -Root $RepoRoot
    Write-Host "DreamSeed Code updated to $NewVersion." -ForegroundColor Green
    Write-Host "Local config, history, memory, logs, and model keys remain under $LocalRoot."
  } finally {
    Pop-Location
  }
} finally {
  try { Stop-Transcript | Out-Null } catch {}
}
