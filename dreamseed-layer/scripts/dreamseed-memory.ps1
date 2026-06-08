param(
  [ValidateSet("status", "doctor", "recall", "candidate", "evolve")]
  [string]$Mode = "status",
  [string]$Query = ""
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $ScriptRoot "dreamseed-memory-bridge.ps1") -Mode $Mode -Query $Query
