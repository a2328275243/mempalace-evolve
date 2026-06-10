Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Instructions = @'
DreamSeed compact policy:
- Produce a Codex-style handoff summary, not a transcript.
- Preserve only durable state: active user goal, current constraints, decisions already made, files changed, commands/tests run, failures with exact actionable error text, and concrete next steps.
- Keep exact absolute paths, command names, package names, environment variables, hook names, and line numbers when they are needed to continue work.
- Collapse long tool outputs, audit dumps, package logs, repeated smoke results, provider diagnostics, JSON blobs, and terminal noise into short bullet summaries.
- Do not include raw secrets, API keys, bearer tokens, provider local config contents, private history text, or long memory-candidate bodies.
- Mention cancellation separately when relevant; do not treat an interrupted compact as a root-cause failure.
- Prefer a short structure: Current task, Important facts, Changed files, Verification, Open issues, Next steps.
- Reuse DreamSeed compact summary cache when available; do not re-summarize raw native history unless the user asks.
- If details are uncertain, say so briefly instead of copying large context.
'@

Write-Output $Instructions.Trim()

try {
  $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
  $Script = Join-Path $RepoRoot "scripts\dreamseed_compact_cache.py"
  if (Test-Path -LiteralPath $Script) {
    $Python = $env:DREAMSEED_PYTHON
    if (-not $Python) { $Python = "python" }
    $CacheOutput = & $Python $Script status --json 2>$null
    if ($LASTEXITCODE -eq 0 -and $CacheOutput) {
      Write-Output ""
      Write-Output "DreamSeed compact cache status:"
      Write-Output $CacheOutput
    }
  }
} catch {
  Write-Output ""
  Write-Output "DreamSeed compact cache status: unavailable; continue with policy summary only."
}
