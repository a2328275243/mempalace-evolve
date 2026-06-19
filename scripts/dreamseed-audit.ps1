$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Failures = New-Object System.Collections.Generic.List[string]
$Warnings = New-Object System.Collections.Generic.List[string]

function Add-Failure([string]$Message) {
  $Failures.Add($Message) | Out-Null
}

function Add-Warning([string]$Message) {
  $Warnings.Add($Message) | Out-Null
}

function Require-Path([string]$Path) {
  $Full = Join-Path $RepoRoot $Path
  if (-not (Test-Path -LiteralPath $Full)) {
    Add-Failure "Missing required path: $Path"
  }
}

function Test-Json([string]$Path) {
  $Full = Join-Path $RepoRoot $Path
  try {
    Get-Content -LiteralPath $Full -Raw | ConvertFrom-Json | Out-Null
  } catch {
    Add-Failure "Invalid JSON in ${Path}: $($_.Exception.Message)"
  }
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

function Invoke-BrandAudit {
  $BrandAuditScript = Join-Path $RepoRoot "scripts\brand_audit.py"
  if (-not (Test-Path -LiteralPath $BrandAuditScript)) {
    Add-Failure "Missing required path: scripts\brand_audit.py"
    return
  }

  $PythonRunner = Get-PythonRunner
  if (-not $PythonRunner) {
    Add-Warning "Python is unavailable; skipped brand audit."
    return
  }

  $BrandAuditOutput = & $PythonRunner.Command @($PythonRunner.Args) $BrandAuditScript scan --root $RepoRoot --strict --json 2>&1
  if ($LASTEXITCODE -ne 0) {
    Add-Failure "Brand audit strict check failed: $($BrandAuditOutput -join ' ')"
    return
  }

  try {
    $BrandAuditJson = $BrandAuditOutput -join "`n" | ConvertFrom-Json
    $ForbiddenCount = [int]($BrandAuditJson.counts.user_visible_forbidden)
    $ReviewCount = [int]($BrandAuditJson.counts.needs_review)
    if ($ForbiddenCount -gt 0) {
      Add-Failure "Brand audit found $ForbiddenCount user-visible legacy brand matches. Run: python scripts\brand_audit.py scan"
    }
    if ($ReviewCount -gt 0) {
      Add-Failure "Brand audit found $ReviewCount unreviewed legacy brand matches."
    }
  } catch {
    Add-Failure "Brand audit returned unreadable JSON: $($_.Exception.Message)"
  }
}

Require-Path "bin\dreamseed-agent.js"
Require-Path "bin\dreamseed.cmd"
Require-Path "config\brand_allowlist.json"
Require-Path "config\mcp.registry.json"
Require-Path "config\approval.policy.json"
Require-Path "config\providers.example.json"
Require-Path ".mcp.json"
Require-Path ".dreamseed\settings.json"
Require-Path ".dreamseed\skills\context-economist\SKILL.md"
Require-Path ".dreamseed\skills\mcp-governor\SKILL.md"
Require-Path ".dreamseed\skills\hook-observer\SKILL.md"
Require-Path ".dreamseed\skills\memory-curator\SKILL.md"
Require-Path ".dreamseed\skills\self-evolve\SKILL.md"
Require-Path ".dreamseed\skills\mcp-recommender\SKILL.md"
Require-Path ".dreamseed\skills\verification-runner\SKILL.md"
Require-Path ".dreamseed\skills\ecosystem-governor\SKILL.md"
Require-Path ".dreamseed\agents\memory-architect.md"
Require-Path ".dreamseed\agents\self-improvement-reviewer.md"
Require-Path ".dreamseed\agents\mcp-scout.md"
Require-Path ".dreamseed\agents\ecosystem-integrator.md"
Require-Path "scripts\dreamseed-memory-bridge.ps1"
Require-Path "scripts\dreamseed_memory_bridge.py"
Require-Path "scripts\install-python-deps.ps1"
Require-Path "scripts\build-python-wheelhouse.ps1"
Require-Path "scripts\dreamseed-mempalace-mcp.ps1"
Require-Path "scripts\provider_bridge.mjs"
Require-Path "scripts\provider_manager.mjs"
Require-Path "scripts\import_ccswitch_provider.py"
Require-Path "scripts\import_claude_history.py"
Require-Path "scripts\dreamseed_self_evolve.py"
Require-Path "scripts\dreamseed_context_doctor.py"
Require-Path "scripts\dreamseed_usage.py"
Require-Path "scripts\dreamseed_output_compress.py"
Require-Path "scripts\dreamseed-precompact.ps1"
Require-Path "scripts\dreamseed-runtime-compact-patch.ps1"
Require-Path "scripts\dreamseed_compact_cache.py"
Require-Path "scripts\install-dreamseed.ps1"
Require-Path "scripts\uninstall-dreamseed.ps1"
Require-Path "scripts\dreamseed_memory_cli.py"
Require-Path "scripts\dreamseed_eval.py"
Require-Path "scripts\provider_tools.py"
Require-Path "scripts\mcp_doctor.py"
Require-Path "scripts\hook_doctor.py"
Require-Path "scripts\approval_gate.py"
Require-Path "scripts\dreamseed-approval-gate.ps1"
Require-Path "scripts\package-dreamseed.ps1"
Require-Path "scripts\brand_audit.py"
Require-Path "scripts\dreamseed-smoke.ps1"
Require-Path "manager\index.html"
Require-Path "manager\app.css"
Require-Path "manager\app.js"
Require-Path "requirements-dreamseed.txt"
Require-Path "vendor\python-wheels\README.md"
Require-Path "restored-src"
Require-Path "docs\ecosystem-absorption.md"
Require-Path "docs\ecosystem-candidates.md"
Require-Path "docs\task-contracts.md"
Require-Path "docs\release-checklist.md"
Require-Path "docs\approval-gate.md"
Require-Path ".dreamseed\tasks\release-check.json"
Require-Path ".dreamseed\tasks\mcp-evaluation.json"
Require-Path ".dreamseed\tasks\memory-curation.json"
Require-Path ".dreamseed\tasks\provider-debug.json"
Require-Path ".dreamseed\tasks\ecosystem-candidate-review.json"
Require-Path ".dreamseed\tasks\regression-fix.json"
Require-Path "AGENTS.md"
Require-Path "DREAMSEED.md"
Require-Path "README.md"
Require-Path "package.json"

Test-Json ".mcp.json"
Test-Json "config\brand_allowlist.json"
Test-Json "config\mcp.registry.json"
Test-Json "config\approval.policy.json"
Test-Json "config\providers.example.json"
Test-Json ".dreamseed\settings.json"
Test-Json "package.json"
Test-Json ".dreamseed\tasks\release-check.json"
Test-Json ".dreamseed\tasks\mcp-evaluation.json"
Test-Json ".dreamseed\tasks\memory-curation.json"
Test-Json ".dreamseed\tasks\provider-debug.json"
Test-Json ".dreamseed\tasks\ecosystem-candidate-review.json"
Test-Json ".dreamseed\tasks\regression-fix.json"

$Mcp = Get-Content -LiteralPath (Join-Path $RepoRoot ".mcp.json") -Raw | ConvertFrom-Json
if (-not $Mcp.mcpServers.mempalace) {
  Add-Failure ".mcp.json does not define mcpServers.mempalace"
}
if ($Mcp.mcpServers.mempalace.command -match "^[A-Za-z]:\\") {
  Add-Failure ".mcp.json must not hard-code a machine-local Python path"
}

$McpRegistry = Get-Content -LiteralPath (Join-Path $RepoRoot "config\mcp.registry.json") -Raw | ConvertFrom-Json
if (-not $McpRegistry.servers.mempalace) {
  Add-Failure "config\mcp.registry.json must register mempalace"
}
if (-not $McpRegistry.candidates) {
  Add-Failure "config\mcp.registry.json must include disabled MCP candidates"
}
foreach ($RequiredRiskTag in @("browser", "desktop", "network-write", "filesystem-write", "credentialed")) {
  if ($McpRegistry.riskTags -notcontains $RequiredRiskTag) {
    Add-Failure "config\mcp.registry.json is missing risk tag: $RequiredRiskTag"
  }
}
foreach ($CandidateName in @("browser-automation", "desktop-control", "github-tools")) {
  $Candidate = $McpRegistry.candidates.$CandidateName
  if (-not $Candidate) {
    Add-Failure "config\mcp.registry.json is missing MCP candidate: $CandidateName"
    continue
  }
  if ($Candidate.defaultState -eq "enabled") {
    Add-Failure "MCP candidate must not default to enabled: $CandidateName"
  }
  if (-not $Candidate.acceptance) {
    Add-Failure "MCP candidate must include acceptance checks: $CandidateName"
  }
}

$Requirements = Get-Content -LiteralPath (Join-Path $RepoRoot "requirements-dreamseed.txt") -Raw
foreach ($RequiredDependency in @("chromadb", "fastmcp")) {
  if ($Requirements -notmatch "(?m)^\s*$RequiredDependency\b") {
    Add-Failure "requirements-dreamseed.txt is missing $RequiredDependency"
  }
}

$InstallerText = Get-Content -LiteralPath (Join-Path $RepoRoot "scripts\install-python-deps.ps1") -Raw
foreach ($RequiredText in @("requirements-dreamseed.txt", "vendor\python-wheels", "DREAMSEED_PYTHON_SITE", "mempalace-evolve")) {
  if ($InstallerText -notmatch [regex]::Escape($RequiredText)) {
    Add-Failure "install-python-deps.ps1 is missing dependency installer behavior: $RequiredText"
  }
}

$PackageJson = Get-Content -LiteralPath (Join-Path $RepoRoot "package.json") -Raw | ConvertFrom-Json
if ($PackageJson.name -ne "dreamseed-code") {
  Add-Failure "package.json name must be dreamseed-code"
}
if (-not $PackageJson.bin.dreamseed) {
  Add-Failure "package.json must expose dreamseed bin"
}
if (-not $PackageJson.scripts."approval:audit") {
  Add-Failure "package.json must expose approval:audit script"
}

$ApprovalPolicy = Get-Content -LiteralPath (Join-Path $RepoRoot "config\approval.policy.json") -Raw | ConvertFrom-Json
if ($ApprovalPolicy.mode -ne "auto-review") {
  Add-Failure "config\approval.policy.json must use auto-review mode"
}
foreach ($DecisionName in @("low", "medium", "high", "critical")) {
  if (-not $ApprovalPolicy.decisions.$DecisionName) {
    Add-Failure "config\approval.policy.json is missing decision: $DecisionName"
  }
}
if ($ApprovalPolicy.decisions.low -ne "allow" -or $ApprovalPolicy.decisions.critical -ne "deny") {
  Add-Failure "approval policy must allow low risk and deny critical risk"
}

$Settings = Get-Content -LiteralPath (Join-Path $RepoRoot ".dreamseed\settings.json") -Raw | ConvertFrom-Json
$PermissionHookCommands = @()
if ($Settings.hooks.PermissionRequest) {
  foreach ($Group in $Settings.hooks.PermissionRequest) {
    foreach ($Hook in $Group.hooks) {
      $PermissionHookCommands += [string]$Hook.command
    }
  }
}
if (-not ($PermissionHookCommands -join "`n" -match "dreamseed-approval-gate\.ps1|approval_gate\.py")) {
  Add-Failure ".dreamseed\settings.json must wire PermissionRequest to DreamSeed approval gate"
}
$PreCompactHookCommands = @()
if ($Settings.hooks.PreCompact) {
  foreach ($Group in $Settings.hooks.PreCompact) {
    foreach ($Hook in $Group.hooks) {
      $PreCompactHookCommands += [string]$Hook.command
    }
  }
}
if (-not ($PreCompactHookCommands -join "`n" -match "dreamseed-precompact\.ps1")) {
  Add-Failure ".dreamseed\settings.json must wire PreCompact to DreamSeed compact policy"
}
foreach ($TooBroadAllow in @("Bash(powershell:*)", "Bash(npm:*)", "Bash(python:*)", "Write(scripts/**)", "Edit(scripts/**)")) {
  if ($Settings.permissions.allow -contains $TooBroadAllow) {
    Add-Failure ".dreamseed\settings.json still contains broad allow that bypasses approval gate: $TooBroadAllow"
  }
}

$GitIgnore = Get-Content -LiteralPath (Join-Path $RepoRoot ".gitignore") -Raw
foreach ($Pattern in @("package/", "*.tgz", ".dreamseed-memory/", "legacy-history/", "memory-candidates/", "self-evolve-candidates/", "self-evolve-backups/", "logs/", "logs/hook-trace/", "dist/", "providers.local.json", "history.meta.json", "desktop.local.json", "__pycache__/", "*.pyc")) {
  if ($GitIgnore -notmatch [regex]::Escape($Pattern)) {
    Add-Failure ".gitignore is missing $Pattern"
  }
}

$SkillFiles = Get-ChildItem -LiteralPath (Join-Path $RepoRoot ".dreamseed\skills") -Recurse -Filter "SKILL.md"
foreach ($Skill in $SkillFiles) {
  $Text = Get-Content -LiteralPath $Skill.FullName -Raw
  if ($Text -notmatch "(?s)^---\s*.*?name:\s*[-a-z0-9]+.*?description:\s*.+?---") {
    Add-Failure "Skill frontmatter is incomplete: $($Skill.FullName)"
  }
}

$AgentFiles = Get-ChildItem -LiteralPath (Join-Path $RepoRoot ".dreamseed\agents") -Filter "*.md"
foreach ($Agent in $AgentFiles) {
  $Text = Get-Content -LiteralPath $Agent.FullName -Raw
  if ($Text -notmatch "(?s)^---\s*.*?name:\s*[-a-z0-9]+.*?description:\s*.+?---") {
    Add-Failure "Agent frontmatter is incomplete: $($Agent.FullName)"
  }
}

$LocalKernelRel = Join-Path "package" ("cli" + ".js")
if (Test-Path -LiteralPath (Join-Path $RepoRoot $LocalKernelRel)) {
  Add-Warning "Local compatibility kernel exists. This is okay locally, but package script must exclude it."
}

$PackageScriptText = Get-Content -LiteralPath (Join-Path $RepoRoot "scripts\package-dreamseed.ps1") -Raw
foreach ($RequiredExclusion in @("__pycache__", "*.pyc", "self-evolve-candidates", "self-evolve-backups", "logs", "cache", "providers.local.json", "history.meta.json", "desktop.local.json", "legacy-history", "memory-candidates")) {
  if ($PackageScriptText -notmatch [regex]::Escape($RequiredExclusion)) {
    Add-Failure "package-dreamseed.ps1 is missing release exclusion: $RequiredExclusion"
  }
}
foreach ($RequiredPackageText in @("source", "full-local-kit", "dreamseed-code-full-local-kit.zip")) {
  if ($PackageScriptText -notmatch [regex]::Escape($RequiredPackageText)) {
    Add-Failure "package-dreamseed.ps1 is missing package mode behavior: $RequiredPackageText"
  }
}
foreach ($RequiredApprovalPackageText in @("config/approval.policy.json", "scripts/approval_gate.py", "scripts/dreamseed-approval-gate.ps1", "docs/approval-gate.md")) {
  if ($PackageScriptText -notmatch [regex]::Escape($RequiredApprovalPackageText)) {
    Add-Failure "package-dreamseed.ps1 is missing approval gate package requirement: $RequiredApprovalPackageText"
  }
}

$MemoryReviewText = Get-Content -LiteralPath (Join-Path $RepoRoot "scripts\memory_review.py") -Raw
foreach ($RequiredMemoryText in @("stability", "specificity", "reuse_value", "pollution_risk", "decision_value", "Many tool calls; checkpoint before compact", "memory_review.py apply -> reviewed/ -> memory_promote.py promote-reviewed")) {
  if ($MemoryReviewText -notmatch [regex]::Escape($RequiredMemoryText)) {
    Add-Failure "memory_review.py is missing Memory Candidate 2.0 behavior: $RequiredMemoryText"
  }
}
$MemoryCliText = Get-Content -LiteralPath (Join-Path $RepoRoot "scripts\dreamseed_memory_cli.py") -Raw
foreach ($RequiredMemoryCliText in @("duplicates", "secretHits", "promote-reviewed", "Refusing to promote memory without --yes or --dry-run")) {
  if ($MemoryCliText -notmatch [regex]::Escape($RequiredMemoryCliText)) {
    Add-Failure "dreamseed_memory_cli.py is missing Memory Candidate 3.0 behavior: $RequiredMemoryCliText"
  }
}

$EvalText = Get-Content -LiteralPath (Join-Path $RepoRoot "scripts\dreamseed_eval.py") -Raw
foreach ($RequiredEvalText in @("suite", "logs", "evals", "release", "memory", "mcp", "provider", "zip-check", "package-dreamseed.ps1", "dreamseed-code-full-local-kit.zip")) {
  if ($EvalText -notmatch [regex]::Escape($RequiredEvalText)) {
    Add-Failure "dreamseed_eval.py is missing evaluation harness behavior: $RequiredEvalText"
  }
}

$LauncherText = Get-Content -LiteralPath (Join-Path $RepoRoot "bin\dreamseed-agent.js") -Raw
foreach ($RequiredLauncherText in @("DREAMSEED_OUTPUT_COMPRESS", "DREAMSEED_OUTPUT_COMPRESS_LIMIT", "writePossiblyCompressedOutput", "--json", "containsSecretLikeDiagnostic")) {
  if ($LauncherText -notmatch [regex]::Escape($RequiredLauncherText)) {
    Add-Failure "bin\dreamseed-agent.js is missing controlled output compression behavior: $RequiredLauncherText"
  }
}
foreach ($RequiredLauncherText in @("compact-cache", "provider diagnose", "defaultProviderSystemPrefix")) {
  if ($LauncherText -notmatch [regex]::Escape($RequiredLauncherText)) {
    Add-Failure "bin\dreamseed-agent.js is missing model/compact usability behavior: $RequiredLauncherText"
  }
}
foreach ($RequiredApprovalText in @("approvalGateScript", "isApprovalCommand", "runApprovalCommand", "dreamseed approval audit")) {
  if ($LauncherText -notmatch [regex]::Escape($RequiredApprovalText)) {
    Add-Failure "bin\dreamseed-agent.js is missing approval CLI behavior: $RequiredApprovalText"
  }
}

$ApprovalText = Get-Content -LiteralPath (Join-Path $RepoRoot "scripts\approval_gate.py") -Raw
foreach ($RequiredApprovalText in @("PermissionRequest", "auto-review", "critical", "decision", "commandPreview", "write_audit_log")) {
  if ($ApprovalText -notmatch [regex]::Escape($RequiredApprovalText)) {
    Add-Failure "approval_gate.py is missing approval gate behavior: $RequiredApprovalText"
  }
}

$ProviderToolsText = Get-Content -LiteralPath (Join-Path $RepoRoot "scripts\provider_tools.py") -Raw
foreach ($RequiredProviderToolsText in @("provider_latency", "provider_config_health", "APPDATA", "export-redacted", "import_redacted", "outputPreview", "diagnose_providers", "recommend_prompt_adapter", "lastToolProbe")) {
  if ($ProviderToolsText -notmatch [regex]::Escape($RequiredProviderToolsText)) {
    Add-Failure "provider_tools.py is missing Provider Manager 2.0 diagnostics: $RequiredProviderToolsText"
  }
}

$LegacyNamespace = "." + "claude"
$PublishScanRoots = @("bin", "config", "docs", "manager", "scripts", ".dreamseed", "AGENTS.md", "DREAMSEED.md", "README.md", "package.json", ".mcp.json", "requirements-dreamseed.txt")
foreach ($Rel in $PublishScanRoots) {
  $Full = Join-Path $RepoRoot $Rel
  if (-not (Test-Path -LiteralPath $Full)) { continue }
  $Files = if ((Get-Item -LiteralPath $Full).PSIsContainer) {
    Get-ChildItem -LiteralPath $Full -Recurse -File |
      Where-Object { $_.FullName -notmatch "\\__pycache__\\" -and $_.Name -notlike "*.pyc" }
  } else {
    @(Get-Item -LiteralPath $Full)
  }
  $Matches = $Files | Select-String -Pattern $LegacyNamespace -SimpleMatch -ErrorAction SilentlyContinue
  $AllowedLegacyPatterns = @(
    'CLAUDE_CONFIG_DIR',
    'legacy-history',
    'legacy-claude',
    'legacy claude',
    'legacy Claude Code',
    'Legacy Claude Code',
    '+ "claude"',
    "+ 'claude'",
    'import_claude_history',
    'archived-session-index',
    'claude-code-import',
    '".claude"',
    "'.claude'",
    'home / ".claude"',
    'home / "." + "claude"',
    'DreamSeed / "home" / ".claude"',
    'LOCAL_ROOT'
  )
  foreach ($Match in $Matches) {
    $Line = $Match.Line
    $Allowed = $false
    foreach ($Pat in $AllowedLegacyPatterns) {
      if ($Line -like "*$Pat*") { $Allowed = $true; break }
    }
    if (-not $Allowed) {
      Add-Failure "Forbidden legacy namespace in publish layer: $($Match.Path):$($Match.LineNumber)"
    }
  }
  foreach ($SecretPattern in @("ghp_[A-Za-z0-9_]{20,}", "github_pat_[A-Za-z0-9_]{20,}", "sk-[A-Za-z0-9_-]{20,}")) {
    $SecretMatches = $Files | Select-String -Pattern $SecretPattern -ErrorAction SilentlyContinue
    foreach ($Match in $SecretMatches) {
      Add-Failure "Secret-like token in publish layer: $($Match.Path):$($Match.LineNumber)"
    }
  }
}

foreach ($SecretRel in @("config\providers.local.json", "config\history.meta.json", "config\desktop.local.json", ".dreamseed\providers.local.json")) {
  if (Test-Path -LiteralPath (Join-Path $RepoRoot $SecretRel)) {
    Add-Failure "Private provider config must not live in the publish layer: $SecretRel"
  }
}

foreach ($PrivateRel in @("legacy-history", "memory-candidates", "self-evolve-candidates", "self-evolve-backups")) {
  if (Test-Path -LiteralPath (Join-Path $RepoRoot $PrivateRel)) {
    Add-Warning "Private local import data exists and must stay out of release packages: $PrivateRel"
  }
}

Invoke-BrandAudit

if ($Warnings.Count -gt 0) {
  Write-Host "Warnings:" -ForegroundColor Yellow
  foreach ($Warning in $Warnings) {
    Write-Host "  - $Warning" -ForegroundColor Yellow
  }
}

if ($Failures.Count -gt 0) {
  Write-Host "DreamSeed audit failed:" -ForegroundColor Red
  foreach ($Failure in $Failures) {
    Write-Host "  - $Failure" -ForegroundColor Red
  }
  exit 1
}

Write-Host "DreamSeed audit passed." -ForegroundColor Green
exit 0
