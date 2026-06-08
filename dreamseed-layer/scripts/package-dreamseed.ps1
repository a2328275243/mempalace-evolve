param(
  [string]$Version = "",
  [ValidateSet("source", "full-local-kit")]
  [string]$Mode = "source"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PackageJson = Get-Content -LiteralPath (Join-Path $RepoRoot "package.json") -Raw | ConvertFrom-Json
if (-not $Version) {
  $Version = $PackageJson.version
}

$DistDir = Join-Path $RepoRoot "dist"
$StageName = if ($Mode -eq "full-local-kit") { "dreamseed-code-$Version-full-local-kit" } else { "dreamseed-code-$Version" }
$DefaultStageRoot = Join-Path ([System.IO.Path]::GetTempPath()) "dreamseed-package-stage"
$StageRoot = if ($env:DREAMSEED_PACKAGE_STAGE_ROOT) { $env:DREAMSEED_PACKAGE_STAGE_ROOT } else { $DefaultStageRoot }
$StageStamp = Get-Date -Format "yyyyMMdd-HHmmss-ffff"
$StageDir = Join-Path $StageRoot "$StageName-$StageStamp"
$ZipPath = if ($Mode -eq "full-local-kit") {
  Join-Path $DistDir "dreamseed-code-full-local-kit.zip"
} else {
  Join-Path $DistDir "dreamseed-code-$Version-source.zip"
}
$TempZipPath = Join-Path $StageRoot "$StageName-$StageStamp.zip"

function Get-PythonRunner {
  if ($env:DREAMSEED_PYTHON -and (Test-Path -LiteralPath $env:DREAMSEED_PYTHON)) {
    return @{ Command = $env:DREAMSEED_PYTHON; Args = @() }
  }

  $Python = Get-Command python -ErrorAction SilentlyContinue
  if ($Python) {
    return @{ Command = $Python.Source; Args = @() }
  }

  $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($PyLauncher) {
    return @{ Command = $PyLauncher.Source; Args = @("-3") }
  }

  return $null
}

function Invoke-BrandAuditForPackage([string]$RootPath) {
  $BrandAuditScript = Join-Path $RootPath "scripts\brand_audit.py"
  if (-not (Test-Path -LiteralPath $BrandAuditScript)) {
    throw "Missing brand audit script in release stage."
  }

  $PythonRunner = Get-PythonRunner
  if (-not $PythonRunner) {
    Write-Host "Warning: Python unavailable; skipped package brand audit." -ForegroundColor Yellow
    return
  }

  $BrandAuditOutput = & $PythonRunner.Command @($PythonRunner.Args) $BrandAuditScript scan --root $RootPath --strict --json 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "Package brand audit strict check failed: $($BrandAuditOutput -join ' ')"
  }

  try {
    $BrandAuditJson = $BrandAuditOutput -join "`n" | ConvertFrom-Json
    $ForbiddenCount = [int]($BrandAuditJson.counts.user_visible_forbidden)
    $ReviewCount = [int]($BrandAuditJson.counts.needs_review)
    if ($ForbiddenCount -gt 0) {
      throw "Package brand audit found $ForbiddenCount user-visible legacy brand matches."
    }
    if ($ReviewCount -gt 0) {
      throw "Package brand audit found $ReviewCount unreviewed legacy brand matches."
    }
  } catch {
    throw "Package brand audit returned unreadable JSON: $($_.Exception.Message)"
  }
}

function Remove-TreeSafely([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    return
  }

  Get-ChildItem -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue |
    ForEach-Object {
      try {
        $_.Attributes = $_.Attributes -band (-bnot [System.IO.FileAttributes]::ReadOnly)
      } catch {
        # Keep going; Remove-Item will report a concrete error if this matters.
      }
    }

  for ($Attempt = 1; $Attempt -le 3; $Attempt++) {
    try {
      Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
      return
    } catch {
      if ($Attempt -eq 3) {
        throw
      }
      Start-Sleep -Milliseconds (250 * $Attempt)
    }
  }
}

function Remove-FileSafely([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    return
  }
  try {
    $Item = Get-Item -LiteralPath $Path -Force
    $Item.Attributes = $Item.Attributes -band (-bnot [System.IO.FileAttributes]::ReadOnly)
  } catch {
    # Remove-Item will report a concrete error if the attribute update mattered.
  }
  for ($Attempt = 1; $Attempt -le 5; $Attempt++) {
    try {
      Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
      return
    } catch {
      if ($Attempt -eq 5) {
        throw
      }
      Start-Sleep -Milliseconds (300 * $Attempt)
    }
  }
}

function Move-FileSafely([string]$Source, [string]$Destination) {
  for ($Attempt = 1; $Attempt -le 5; $Attempt++) {
    try {
      if (Test-Path -LiteralPath $Destination) {
        Remove-FileSafely $Destination
      }
      Move-Item -LiteralPath $Source -Destination $Destination -Force -ErrorAction Stop
      return
    } catch {
      if ($Attempt -eq 5) {
        throw
      }
      Start-Sleep -Milliseconds (300 * $Attempt)
    }
  }
}

function Test-ZipPolicy([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    return $false
  }
  $Archive = [System.IO.Compression.ZipFile]::OpenRead($Path)
  $LegacyNamespace = "." + "claude"
  try {
    $Required = @(
      "bin/dreamseed-agent.js",
      "config/approval.policy.json",
      "config/mcp.registry.json",
      "docs/approval-gate.md",
      "docs/ecosystem-candidates.md",
      "docs/task-contracts.md",
      "docs/release-checklist.md",
      "scripts/approval_gate.py",
      "scripts/dreamseed-approval-gate.ps1",
      "scripts/dreamseed_eval.py",
      "scripts\dreamseed_memory_cli.py",
      "scripts\provider_tools.py",
      ".dreamseed/tasks/release-check.json"
    )
    $Names = @{}
    foreach ($Entry in $Archive.Entries) {
      $SlashName = $Entry.FullName -replace "\\", "/"
      $Names[$SlashName] = $true
      $Name = $Entry.FullName -replace "/", "\"
      $KernelFilePattern = "cli" + "\.js(\.map)?$"
      if ($Name -match "(^|\\)package(\\|$)" -or $Name -match $KernelFilePattern -or $Name.Contains($LegacyNamespace) -or $Name -match "\.dreamseed-runtime" -or $Name -match "\.dreamseed-memory" -or $Name -match "(^|\\)legacy-history(\\|$)" -or $Name -match "(^|\\)memory-candidates(\\|$)" -or $Name -match "(^|\\)self-evolve-candidates(\\|$)" -or $Name -match "(^|\\)self-evolve-backups(\\|$)" -or $Name -match "(^|\\)logs(\\|$)" -or $Name -match "(^|\\)cache(\\|$)" -or $Name -match "(^|\\)\.cache(\\|$)" -or $Name -match "(^|\\)\.dreamseed-deploy-backups(\\|$)" -or $Name -match "(^|\\)__pycache__(\\|$)" -or $Name -match "\.pyc$" -or $Name -match "(^|\\)node_modules(\\|$)" -or $Name -match "(^|\\)providers\.local\.json$") {
        return $false
      }
    }
    foreach ($Rel in $Required) {
      $Normalized = $Rel -replace "\\", "/"
      if (-not $Names.ContainsKey($Normalized)) {
        return $false
      }
    }
    return $true
  } finally {
    $Archive.Dispose()
  }
}

if (Test-Path -LiteralPath $StageDir) {
  Remove-TreeSafely $StageDir
}
New-Item -ItemType Directory -Force -Path $StageRoot | Out-Null
New-Item -ItemType Directory -Force -Path $StageDir | Out-Null
Remove-FileSafely $TempZipPath

$IncludePaths = @(
  ".dreamseed",
  "bin",
  "config",
  "docs",
  "manager",
  "scripts",
  "restored-src",
  "vendor\python-wheels",
  ".mcp.json",
  ".gitignore",
  "AGENTS.md",
  "DREAMSEED.md",
  "README.md",
  "package.json",
  "requirements-dreamseed.txt"
)

foreach ($Rel in $IncludePaths) {
  $Source = Join-Path $RepoRoot $Rel
  if (-not (Test-Path -LiteralPath $Source)) {
    throw "Missing package input: $Rel"
  }
  $Dest = Join-Path $StageDir $Rel
  $Parent = Split-Path -Parent $Dest
  if ($Parent -and -not (Test-Path -LiteralPath $Parent)) {
    New-Item -ItemType Directory -Force -Path $Parent | Out-Null
  }
  Copy-Item -LiteralPath $Source -Destination $Dest -Recurse -Force
}

if ($Mode -eq "full-local-kit") {
  $KitReadmeLines = @(
    "# DreamSeed Full Local Kit",
    "",
    "This package is still private-data-free. It may include dependency helpers and",
    "offline wheelhouse material, but it must not contain provider keys, imported",
    "history, memory databases, self-evolution staging, logs, caches, or local",
    "runtime kernels.",
    "",
    "Recommended setup:",
    "",
    '```powershell',
    'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-dreamseed.ps1',
    'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-python-deps.ps1',
    'dreamseed provider setup --name default --url <url> --key <key> --model <model>',
    'dreamseed-smoke.ps1',
    '```'
  )
  $KitReadme = $KitReadmeLines -join [Environment]::NewLine
  Set-Content -LiteralPath (Join-Path $StageDir "LOCAL-KIT.md") -Value $KitReadme -Encoding UTF8
}

$RestoredNodeModules = Join-Path $StageDir "restored-src\node_modules"
if (Test-Path -LiteralPath $RestoredNodeModules) {
  Remove-Item -LiteralPath $RestoredNodeModules -Recurse -Force
}

Get-ChildItem -LiteralPath $StageDir -Recurse -Directory -Force |
  Where-Object { $_.Name -eq "__pycache__" } |
  ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }

Get-ChildItem -LiteralPath $StageDir -Recurse -File -Force |
  Where-Object { $_.Name -like "*.pyc" } |
  ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }

$Forbidden = @(
  (Join-Path "package" ("cli" + ".js")),
  (Join-Path "package" ("cli" + ".js.map")),
  "package",
  ("." + "claude"),
  "restored-src\node_modules",
  ".dreamseed-runtime",
  ".dreamseed-memory",
  "legacy-history",
  "memory-candidates",
  "self-evolve-candidates",
  "self-evolve-backups",
  "logs",
  "cache",
  ".cache",
  "__pycache__",
  "*.pyc",
  ".omni-memory",
  ".dreamseed-deploy-backups",
  "config\providers.local.json",
  ".dreamseed\providers.local.json"
)

foreach ($Rel in $Forbidden) {
  if (Test-Path -LiteralPath (Join-Path $StageDir $Rel)) {
    throw "Forbidden artifact included in release stage: $Rel"
  }
}

Invoke-BrandAuditForPackage $StageDir

Compress-Archive -Path (Join-Path $StageDir "*") -DestinationPath $TempZipPath -Force

$ZipItems = Add-Type -AssemblyName System.IO.Compression.FileSystem -PassThru | Out-Null
$Archive = [System.IO.Compression.ZipFile]::OpenRead($TempZipPath)
$LegacyNamespace = "." + "claude"
try {
  foreach ($Entry in $Archive.Entries) {
    $Name = $Entry.FullName -replace "/", "\"
    $KernelFilePattern = "cli" + "\.js(\.map)?$"
    if ($Name -match "(^|\\)package(\\|$)" -or $Name -match $KernelFilePattern -or $Name.Contains($LegacyNamespace) -or $Name -match "\.dreamseed-runtime" -or $Name -match "\.dreamseed-memory" -or $Name -match "(^|\\)legacy-history(\\|$)" -or $Name -match "(^|\\)memory-candidates(\\|$)" -or $Name -match "(^|\\)self-evolve-candidates(\\|$)" -or $Name -match "(^|\\)self-evolve-backups(\\|$)" -or $Name -match "(^|\\)logs(\\|$)" -or $Name -match "(^|\\)cache(\\|$)" -or $Name -match "(^|\\)\.cache(\\|$)" -or $Name -match "(^|\\)\.dreamseed-deploy-backups(\\|$)" -or $Name -match "(^|\\)__pycache__(\\|$)" -or $Name -match "\.pyc$" -or $Name -match "(^|\\)node_modules(\\|$)" -or $Name -match "(^|\\)providers\.local\.json$") {
      throw "Forbidden artifact found in zip: $($Entry.FullName)"
    }
  }
} finally {
  $Archive.Dispose()
}

$UsedExistingLockedZip = $false
try {
  Move-FileSafely $TempZipPath $ZipPath
} catch {
  if (Test-ZipPolicy $ZipPath) {
    $UsedExistingLockedZip = $true
    Remove-FileSafely $TempZipPath
  } else {
    throw
  }
}

Write-Host "Created $Mode release: $ZipPath" -ForegroundColor Green
if ($UsedExistingLockedZip) {
  Write-Host "Reused existing validated zip because the target zip was locked by another process." -ForegroundColor Yellow
}
Write-Host "Excluded local runtime kernels and memory databases." -ForegroundColor Green
try {
  Remove-TreeSafely $StageDir
} catch {
  Write-Host "Warning: could not remove temporary package stage: $StageDir" -ForegroundColor Yellow
}
