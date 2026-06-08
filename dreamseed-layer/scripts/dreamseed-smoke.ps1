param(
  [string]$Prompt = "Reply exactly: ok",
  [switch]$SkipModelCall,
  [switch]$SkipPackage
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Failures = New-Object System.Collections.Generic.List[string]
$Results = New-Object System.Collections.Generic.List[string]

function Add-Result([string]$Message) {
  $Results.Add($Message) | Out-Null
}

function Add-Failure([string]$Message) {
  $Failures.Add($Message) | Out-Null
}

function Resolve-DreamSeedCommand {
  foreach ($LocalLauncher in @(
    "D:\DreamSeed-Local-Agent\bin\dreamseed-local.cmd",
    "D:\DreamSeed-Local-Agent\bin\dreamseed.cmd"
  )) {
    if (Test-Path -LiteralPath $LocalLauncher) {
      return $LocalLauncher
    }
  }

  $Command = Get-Command dreamseed -ErrorAction SilentlyContinue
  if ($Command) {
    return $Command.Source
  }

  $Agent = Join-Path $RepoRoot "bin\dreamseed-agent.js"
  if (Test-Path -LiteralPath $Agent) {
    return $Agent
  }

  return $null
}

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

function Invoke-SmokeStep([string]$Name, [scriptblock]$Action) {
  Write-Host "==> $Name" -ForegroundColor Cyan
  $Start = Get-Date
  try {
    $PreviousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
      $Output = & $Action 2>&1
      $Code = if ($LASTEXITCODE -ne $null) { $LASTEXITCODE } else { 0 }
    } finally {
      $ErrorActionPreference = $PreviousErrorActionPreference
    }
    if ($Code -ne 0) {
      Add-Failure "${Name}: exit code $Code`n$($Output -join "`n")"
      Write-Host "FAIL $Name" -ForegroundColor Red
      return
    }
    $Elapsed = [int]((Get-Date) - $Start).TotalSeconds
    Add-Result "${Name}: ok (${Elapsed}s)"
    Write-Host "OK $Name (${Elapsed}s)" -ForegroundColor Green
  } catch {
    Add-Failure "${Name}: $($_.Exception.Message)"
    Write-Host "FAIL $Name" -ForegroundColor Red
  }
}

$DreamSeed = Resolve-DreamSeedCommand
if (-not $DreamSeed) {
  throw "Could not find dreamseed command or local launcher."
}

if (-not $env:PYTHONIOENCODING) {
  $env:PYTHONIOENCODING = "utf-8"
}
$env:PATH = "D:\DreamSeed-Local-Agent\bin;$env:PATH"

Invoke-SmokeStep "dreamseed --help" {
  & $DreamSeed --help
}

Invoke-SmokeStep "dreamseed interactive entry" {
  $Output = "/exit" | & $DreamSeed
  $Text = $Output -join "`n"
  if ($Text -match "DreamSeed Code launcher") {
    throw "bare dreamseed showed launcher help instead of entering the runtime"
  }
  $Output
}

Invoke-SmokeStep "dreamseed provider status" {
  & $DreamSeed provider status
}

Invoke-SmokeStep "dreamseed history status" {
  & $DreamSeed history status
}

Invoke-SmokeStep "dreamseed evolve status" {
  & $DreamSeed evolve status
}

Invoke-SmokeStep "dreamseed doctor context" {
  $Output = & $DreamSeed doctor context --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

Invoke-SmokeStep "dreamseed usage summary" {
  $Output = & $DreamSeed usage summary --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

Invoke-SmokeStep "dreamseed doctor mcp" {
  $Output = & $DreamSeed doctor mcp --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

Invoke-SmokeStep "dreamseed doctor hooks" {
  $Output = & $DreamSeed doctor hooks --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

Invoke-SmokeStep "dreamseed approval status" {
  $Output = & $DreamSeed approval status --json
  $Json = $Output -join "`n" | ConvertFrom-Json
  if (-not $Json.ok) {
    throw "approval status is not ok"
  }
  $Output
}

Invoke-SmokeStep "dreamseed approval audit" {
  $Output = & $DreamSeed approval audit --json
  $Json = $Output -join "`n" | ConvertFrom-Json
  if (-not $Json.ok) {
    throw "approval audit is not ok"
  }
  $Output
}

Invoke-SmokeStep "dreamseed approval check safe shell" {
  $Output = & $DreamSeed approval check --tool Bash --command "git status --short" --json
  $Json = $Output -join "`n" | ConvertFrom-Json
  if ($Json.decision -ne "allow") {
    throw "safe shell expected allow, got $($Json.decision)"
  }
  $Output
}

Invoke-SmokeStep "dreamseed approval check risky shell" {
  $Output = & $DreamSeed approval check --tool Bash --command "Remove-Item -LiteralPath D:\data -Recurse -Force" --json
  $Json = $Output -join "`n" | ConvertFrom-Json
  if ($Json.decision -ne "ask") {
    throw "risky shell expected ask, got $($Json.decision)"
  }
  $Output
}

Invoke-SmokeStep "dreamseed approval check critical shell" {
  $Output = & $DreamSeed approval check --tool Bash --command "shutdown /s /t 0" --json
  $Json = $Output -join "`n" | ConvertFrom-Json
  if ($Json.decision -ne "deny") {
    throw "critical shell expected deny, got $($Json.decision)"
  }
  $Output
}

Invoke-SmokeStep "dreamseed memory audit" {
  $Output = & $DreamSeed memory audit --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

Invoke-SmokeStep "dreamseed mcp list" {
  $Output = & $DreamSeed mcp list --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

Invoke-SmokeStep "dreamseed mcp candidates" {
  $Output = & $DreamSeed mcp candidates --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

Invoke-SmokeStep "dreamseed provider templates" {
  $Output = & $DreamSeed provider templates --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

Invoke-SmokeStep "dreamseed provider health" {
  $Output = & $DreamSeed provider health --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

Invoke-SmokeStep "dreamseed provider latency" {
  $Output = & $DreamSeed provider latency --json
  $Json = $Output -join "`n" | ConvertFrom-Json
  if (-not $Json.ok) {
    throw "provider latency failed: $($Json.error)"
  }
  $Output
}

Invoke-SmokeStep "dreamseed eval run smoke" {
  $Output = & $DreamSeed eval run --suite smoke --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

Invoke-SmokeStep "dreamseed_output_compress.py smoke" {
  $PythonRunner = Get-PythonRunner
  if (-not $PythonRunner) {
    throw "Python is unavailable."
  }
  $Output = & $PythonRunner.Command @($PythonRunner.Args) (Join-Path $RepoRoot "scripts\dreamseed_output_compress.py") smoke --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

Invoke-SmokeStep "dreamseed_output_compress.py policy" {
  $PythonRunner = Get-PythonRunner
  if (-not $PythonRunner) {
    throw "Python is unavailable."
  }
  $Output = & $PythonRunner.Command @($PythonRunner.Args) (Join-Path $RepoRoot "scripts\dreamseed_output_compress.py") policy --json
  $Output -join "`n" | ConvertFrom-Json | Out-Null
  $Output
}

if (-not $SkipModelCall) {
  Invoke-SmokeStep "dreamseed provider test" {
    & $DreamSeed provider test --prompt $Prompt
  }

  Invoke-SmokeStep "dreamseed --print" {
    & $DreamSeed --print --output-format text --max-turns 1 $Prompt
  }
}

Invoke-SmokeStep "dreamseed-audit.ps1" {
  powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\dreamseed-audit.ps1")
}

if (-not $SkipPackage) {
  Invoke-SmokeStep "package-dreamseed.ps1" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\package-dreamseed.ps1")
  }

  Invoke-SmokeStep "package-dreamseed.ps1 full-local-kit" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "scripts\package-dreamseed.ps1") -Mode full-local-kit
  }

  Invoke-SmokeStep "dreamseed eval zip-check" {
    $Output = & $DreamSeed eval zip-check --json
    $Json = $Output -join "`n" | ConvertFrom-Json
    if (-not $Json.ok) {
      throw "zip-check failed"
    }
    $Output
  }
}

Write-Host ""
Write-Host "Smoke summary" -ForegroundColor Cyan
foreach ($Result in $Results) {
  Write-Host "  - $Result" -ForegroundColor Green
}

if ($Failures.Count -gt 0) {
  Write-Host ""
  Write-Host "Smoke failed:" -ForegroundColor Red
  foreach ($Failure in $Failures) {
    Write-Host "  - $Failure" -ForegroundColor Red
  }
  exit 1
}

Write-Host "DreamSeed smoke passed." -ForegroundColor Green
exit 0
