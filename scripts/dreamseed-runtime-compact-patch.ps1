param(
  [ValidateSet("status", "apply", "restore")]
  [string]$Action = "status",
  [string]$Runtime = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# DreamSeed Lite Kernel (plan B) does not need the legacy compact-rescue patch
# that targeted the 13 MB claude-cli.js runtime. The lite kernel ships its own
# compact engine with incremental summary caching. This script is kept as a
# no-op shim so older hooks or docs that still invoke it do not break.

function Get-Status {
  param([string]$Path)
  [pscustomobject]@{
    ok = $true
    runtime = "DreamSeed Lite Kernel (no legacy patch needed)"
    exists = $false
    sizeBytes = $null
    hasUtf8Bom = $false
    fastCompactRescue = $true
    summarizedIdFallback = $true
    backupCount = 0
    note = "Legacy claude-cli.js compact patch is obsolete under DreamSeed Lite Kernel."
  }
}

$Status = Get-Status -Path $Runtime
switch ($Action) {
  "status" {
    Write-Host "DreamSeed compact patch status"
    Write-Host "  runtime : $($Status.runtime)"
    Write-Host "  note    : $($Status.note)"
    $Status
  }
  "apply" {
    Write-Host "No compact patch needed: DreamSeed Lite Kernel already ships fast incremental compact."
  }
  "restore" {
    Write-Host "No compact patch to restore: DreamSeed Lite Kernel has no legacy patch backup."
  }
}
