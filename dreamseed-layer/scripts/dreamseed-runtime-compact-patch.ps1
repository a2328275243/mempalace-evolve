param(
  [ValidateSet("status", "apply", "restore")]
  [string]$Action = "status",
  [string]$Runtime = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LocalRoot = if ($env:DREAMSEED_LOCAL_ROOT) { $env:DREAMSEED_LOCAL_ROOT } else { "D:\DreamSeed-Local-Agent" }
if (-not $Runtime) {
  $Runtime = if ($env:DREAMSEED_COMPAT_KERNEL_JS) {
    $env:DREAMSEED_COMPAT_KERNEL_JS
  } else {
    Join-Path $LocalRoot ("runtime\" + "cl" + "aude-cli.js")
  }
}

$NoMemoryOld = 'if(!Y)return d("tengu_sm_compact_no_session_memory",{}),null;'
$NoMemoryNew = 'if(!Y)Y="DreamSeed fast compact rescue: no prior session memory was available, so this compact keeps the recent conversation tail and drops older raw transcript instead of launching the slow agent-acompact summarizer.";'
$MissingIdOld = 'if($=q.findIndex((X)=>X.uuid===z),$===-1)return d("tengu_sm_compact_summarized_id_not_found",{}),null}else'
$MissingIdNew = 'if($=q.findIndex((X)=>X.uuid===z),$===-1)$=q.length-1,d("tengu_sm_compact_summarized_id_not_found",{})}else'

function Get-Status {
  param([string]$Path)
  $Exists = Test-Path -LiteralPath $Path
  $Bytes = if ($Exists) { [System.IO.File]::ReadAllBytes($Path) } else { @() }
  $HasBom = $Bytes.Length -ge 3 -and $Bytes[0] -eq 0xEF -and $Bytes[1] -eq 0xBB -and $Bytes[2] -eq 0xBF
  $Text = if ($Exists) { [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) } else { "" }
  [pscustomobject]@{
    ok = $Exists -and (-not $HasBom) -and $Text.Contains("DreamSeed fast compact rescue") -and $Text.Contains("tengu_sm_compact_summarized_id_not_found")
    runtime = $Path
    exists = $Exists
    sizeBytes = if ($Exists) { (Get-Item -LiteralPath $Path).Length } else { $null }
    hasUtf8Bom = $HasBom
    fastCompactRescue = $Text.Contains("DreamSeed fast compact rescue")
    summarizedIdFallback = $Text.Contains($MissingIdNew)
  }
}

function Write-Utf8NoBom {
  param([string]$Path, [string]$Text)
  $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Text, $Utf8NoBom)
}

function Apply-Patch {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Runtime not found: $Path"
  }
  $Text = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
  $Changed = $false
  if ($Text.Contains($NoMemoryOld)) {
    $Backup = "$Path.before-fast-compact-rescue-$(Get-Date -Format yyyyMMdd-HHmmss).bak"
    Copy-Item -LiteralPath $Path -Destination $Backup -Force
    $Text = $Text.Replace($NoMemoryOld, $NoMemoryNew)
    $Changed = $true
  }
  if ($Text.Contains($MissingIdOld)) {
    if (-not $Changed) {
      $Backup = "$Path.before-fast-compact-rescue-$(Get-Date -Format yyyyMMdd-HHmmss).bak"
      Copy-Item -LiteralPath $Path -Destination $Backup -Force
    }
    $Text = $Text.Replace($MissingIdOld, $MissingIdNew)
    $Changed = $true
  }
  if (-not $Changed -and (Get-Status $Path).hasUtf8Bom) {
    $Backup = "$Path.before-remove-bom-$(Get-Date -Format yyyyMMdd-HHmmss).bak"
    Copy-Item -LiteralPath $Path -Destination $Backup -Force
    $Changed = $true
  }
  if ($Changed) {
    Write-Utf8NoBom $Path $Text
  }
  Get-Status $Path
}

function Restore-LatestBackup {
  param([string]$Path)
  $Dir = Split-Path -Parent $Path
  $Name = Split-Path -Leaf $Path
  $Backup = Get-ChildItem -LiteralPath $Dir -Filter "$Name.before-fast-compact-rescue-*.bak" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if (-not $Backup) {
    throw "No fast compact rescue backup found beside $Path"
  }
  Copy-Item -LiteralPath $Backup.FullName -Destination $Path -Force
  Get-Status $Path
}

switch ($Action) {
  "status" { Get-Status $Runtime | ConvertTo-Json -Depth 4 }
  "apply" { Apply-Patch $Runtime | ConvertTo-Json -Depth 4 }
  "restore" { Restore-LatestBackup $Runtime | ConvertTo-Json -Depth 4 }
}
