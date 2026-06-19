param(
  [string]$DreamSeedCmd = "",
  [switch]$IncludeRenderSmoke
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-DreamSeedCmd {
  param([string]$Provided)
  if ($Provided) {
    $Path = [System.IO.Path]::GetFullPath($Provided)
    if (-not (Test-Path -LiteralPath $Path)) { throw "dreamseed.cmd not found: $Path" }
    return $Path
  }
  $ScriptRoot = Split-Path -Parent $PSCommandPath
  $AppRoot = Split-Path -Parent $ScriptRoot
  $Candidates = @(
    (Join-Path $AppRoot "dist\DreamSeed-Code-0.1.1-win32-x64\dreamseed.cmd"),
    (Join-Path $AppRoot "dist\DreamSeed-Code-0.1.0-win32-x64\dreamseed.cmd")
  )
  foreach ($Candidate in $Candidates) {
    if (Test-Path -LiteralPath $Candidate) { return [System.IO.Path]::GetFullPath($Candidate) }
  }
  throw "dreamseed.cmd was not found. Build the Windows package first."
}

function Invoke-DreamSeed {
  param(
    [string]$Command,
    [string[]]$Arguments,
    [string]$Cwd,
    [int]$ExpectedExit = 0
  )
  Push-Location -LiteralPath $Cwd
  $PreviousErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    $Output = & $Command @Arguments 2>&1 | Out-String
    $ExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
  } finally {
    $ErrorActionPreference = $PreviousErrorActionPreference
    Pop-Location
  }
  if ($ExitCode -ne $ExpectedExit) {
    throw "Command failed: dreamseed $($Arguments -join ' ') exit=$ExitCode output=$($Output.Trim())"
  }
  return $Output.Trim()
}

function Parse-JsonOutput {
  param([string]$Text, [string]$Label)
  $Start = $Text.IndexOf("{")
  $End = $Text.LastIndexOf("}")
  if ($Start -lt 0 -or $End -le $Start) { throw "$Label did not return JSON: $Text" }
  return $Text.Substring($Start, $End - $Start + 1) | ConvertFrom-Json
}

function Assert-Equal {
  param([string]$Name, [string]$Actual, [string]$Expected)
  if ($Actual -ine $Expected) {
    throw "$Name mismatch.`nactual:   $Actual`nexpected: $Expected"
  }
}

$DreamSeed = Resolve-DreamSeedCmd -Provided $DreamSeedCmd
$SmokeRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("dreamseed-clean-user-smoke-" + $PID)
$LocalAppData = Join-Path $SmokeRoot "LocalAppData"
$AppData = Join-Path $SmokeRoot "AppData\Roaming"
$UserProfile = Join-Path $SmokeRoot "User"
$ChineseProjectName = -join ([char[]](0x9879, 0x76ee, 0x7a7a, 0x7528, 0x6237))
$Project = Join-Path $SmokeRoot $ChineseProjectName
$ExpectedLocalRoot = Join-Path $LocalAppData "DreamSeed"
$ExpectedProviderConfig = Join-Path $ExpectedLocalRoot "config\providers.local.json"

$Saved = @{}
foreach ($Name in @(
  "PATH",
  "LOCALAPPDATA",
  "APPDATA",
  "USERPROFILE",
  "HOME",
  "DREAMSEED_LOCAL_ROOT",
  "DREAMSEED_PROVIDER_CONFIG",
  "DREAMSEED_CONFIG_DIR",
  "DREAMSEED_PYTHON",
  "DREAMSEED_PYTHON_ARGS",
  "DREAMSEED_GIT_BASH_PATH",
  "CLAUDE_CODE_GIT_BASH_PATH",
  "DREAMSEED_TEST_NO_SYSTEM_GIT_BASH",
  "DREAMSEED_SKIP_GIT_INSTALL",
  "HTTPS_PROXY",
  "HTTP_PROXY"
)) {
  $Saved[$Name] = [Environment]::GetEnvironmentVariable($Name, "Process")
}

try {
  New-Item -ItemType Directory -Force -Path $LocalAppData, $AppData, $UserProfile, $Project | Out-Null

  $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
  $env:LOCALAPPDATA = $LocalAppData
  $env:APPDATA = $AppData
  $env:USERPROFILE = $UserProfile
  $env:HOME = $UserProfile
  $env:DREAMSEED_LOCAL_ROOT = $ExpectedLocalRoot
  Remove-Item Env:\DREAMSEED_PROVIDER_CONFIG -ErrorAction SilentlyContinue
  Remove-Item Env:\DREAMSEED_CONFIG_DIR -ErrorAction SilentlyContinue
  $env:DREAMSEED_PYTHON = "C:\missing\python.exe"
  $env:DREAMSEED_PYTHON_ARGS = ""
  $env:DREAMSEED_GIT_BASH_PATH = "C:\missing\bash.exe"
  $env:CLAUDE_CODE_GIT_BASH_PATH = "C:\missing\bash.exe"

  $Version = Invoke-DreamSeed -Command $DreamSeed -Arguments @("--version") -Cwd $Project
  $ProviderPath = Invoke-DreamSeed -Command $DreamSeed -Arguments @("provider", "path") -Cwd $Project
  Assert-Equal -Name "provider path" -Actual $ProviderPath -Expected $ExpectedProviderConfig

  $ProviderStatus = Invoke-DreamSeed -Command $DreamSeed -Arguments @("provider", "status") -Cwd $Project
  if ($ProviderStatus -notmatch "not configured|provider configured") {
    throw "provider status returned unexpected output: $ProviderStatus"
  }

  $ManagerJson = Parse-JsonOutput -Text (Invoke-DreamSeed -Command $DreamSeed -Arguments @("manager", "--smoke") -Cwd $Project) -Label "manager smoke"
  Assert-Equal -Name "manager provider config" -Actual ([string]$ManagerJson.configPath) -Expected $ExpectedProviderConfig

  $DesktopJson = Parse-JsonOutput -Text (Invoke-DreamSeed -Command $DreamSeed -Arguments @("desktop", "--smoke") -Cwd $Project) -Label "desktop smoke"
  Assert-Equal -Name "desktop provider config" -Actual ([string]$DesktopJson.providerConfigPath) -Expected $ExpectedProviderConfig

  $HistoryJson = Parse-JsonOutput -Text (Invoke-DreamSeed -Command $DreamSeed -Arguments @("history", "status") -Cwd $Project) -Label "history status"
  if (-not $HistoryJson.ok) { throw "history status should degrade cleanly for a clean user" }

  $BareError = Invoke-DreamSeed -Command $DreamSeed -Arguments @() -Cwd $Project -ExpectedExit 2
  if ($BareError -notmatch "interactive mode requires a real terminal") { throw "bare non-TTY launch did not explain the fix: $BareError" }
  if ($BareError -match "provider bridge|Input must be provided") { throw "bare non-TTY launch should not start provider bridge or fall through to kernel print mode: $BareError" }

  $PrintError = Invoke-DreamSeed -Command $DreamSeed -Arguments @("--print") -Cwd $Project -ExpectedExit 2
  if ($PrintError -notmatch "--print requires") { throw "--print guard did not explain the missing prompt: $PrintError" }
  if ($PrintError -match "provider bridge") { throw "--print guard started provider bridge before rejecting empty input" }

  $env:DREAMSEED_TEST_NO_SYSTEM_GIT_BASH = "1"
  $env:DREAMSEED_SKIP_GIT_INSTALL = "1"
  $NoGitError = Invoke-DreamSeed -Command $DreamSeed -Arguments @("--print", "Reply exactly: ok") -Cwd $Project -ExpectedExit 1
  if ($NoGitError -notmatch "Git Bash is still missing") { throw "missing Git Bash guard did not explain the fix: $NoGitError" }
  if ($NoGitError -match "provider bridge") { throw "missing Git Bash guard started provider bridge before dependency validation" }
  Remove-Item Env:\DREAMSEED_TEST_NO_SYSTEM_GIT_BASH -ErrorAction SilentlyContinue
  Remove-Item Env:\DREAMSEED_SKIP_GIT_INSTALL -ErrorAction SilentlyContinue

  $UpdateHelp = Invoke-DreamSeed -Command $DreamSeed -Arguments @("update", "--help") -Cwd $Project
  if ($UpdateHelp -match "\[dreamseed\] provider bridge|updater started") { throw "update --help should not start provider bridge or updater" }

  $RenderSmoke = $null
  if ($IncludeRenderSmoke) {
    $RenderSmoke = Parse-JsonOutput -Text (Invoke-DreamSeed -Command $DreamSeed -Arguments @("desktop", "--render-smoke") -Cwd $Project) -Label "desktop render smoke"
    if (-not $RenderSmoke.ok) { throw "desktop render smoke failed" }
  }

  [pscustomobject]@{
    ok = $true
    dreamseed = $DreamSeed
    version = $Version
    smokeRoot = $SmokeRoot
    localRoot = $ExpectedLocalRoot
    providerConfig = $ExpectedProviderConfig
    managerProviderConfig = [string]$ManagerJson.configPath
    desktopProviderConfig = [string]$DesktopJson.providerConfigPath
    noNodePath = $true
    badPythonEnv = $true
    badGitBashEnv = $true
    renderSmoke = [bool]$IncludeRenderSmoke
  } | ConvertTo-Json -Depth 4
} finally {
  foreach ($Name in $Saved.Keys) {
    if ($null -eq $Saved[$Name]) {
      Remove-Item "Env:\$Name" -ErrorAction SilentlyContinue
    } else {
      [Environment]::SetEnvironmentVariable($Name, $Saved[$Name], "Process")
    }
  }
  if (Test-Path -LiteralPath $SmokeRoot) {
    Remove-Item -LiteralPath $SmokeRoot -Recurse -Force -ErrorAction SilentlyContinue
  }
}
