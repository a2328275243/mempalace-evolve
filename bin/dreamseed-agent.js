#!/usr/bin/env node
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { tmpdir } from 'node:os'
import { fileURLToPath } from 'node:url'
import { spawn, spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { createInterface } from 'node:readline/promises'
import { stdin as input, stdout as output } from 'node:process'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const root = path.resolve(__dirname, '..')
const packageVersion = readPackageVersion()
const packagedRuntime = process.env.DREAMSEED_PACKAGED === '1' || root.toLowerCase().includes('.asar')
const packagedCwd = packagedRuntime
  ? path.resolve(process.env.DREAMSEED_INSTALL_ROOT || path.dirname(process.execPath))
  : root

let args = normalizeKernelArgs(process.argv.slice(2))
const env = { ...process.env }

if (isBareNonInteractiveLaunch(args, env)) {
  printBareNonInteractiveHelp()
  process.exit(2)
}

if (isVersionRequest(args)) {
  console.log(`${packageVersion} (DreamSeed Code)`)
  process.exit(0)
}

if (isHelpRequest(args)) {
  printLauncherHelp()
  process.exit(0)
}

if (isPrintWithoutInput(args)) {
  console.error('[dreamseed] --print requires a prompt argument or stdin input.')
  console.error('Example: dreamseed --print "Reply exactly: ok"')
  process.exit(2)
}

const currentProject = process.cwd()
const localRoot = resolveLocalRoot(env)
const localHome = env.DREAMSEED_HOME || path.join(localRoot, 'home')
mkdirSync(localHome, { recursive: true })
const legacyHistoryDir = resolveLegacyHistoryDir(env, root, localRoot)
const runtimeDir =
  env.DREAMSEED_RUNTIME_DIR ||
  path.join(localRoot, 'runtime')
const pythonSite = env.DREAMSEED_PYTHON_SITE || path.join(runtimeDir, 'python-site')
const bundledMempalaceSrc = path.join(root, 'vendor', 'mempalace-evolve', 'src')
// DreamSeed Lite Kernel: single source of truth, no fallback to legacy claude-cli.
const liteKernelJs = packagedRuntime
  ? path.join(packagedCwd, 'resources', 'kernel', 'dreamseed-lite-kernel.js')
  : path.join(root, 'bin', 'dreamseed-lite-kernel.js')
const defaultKernelJs = firstExistingPath([
  env.DREAMSEED_KERNEL_JS,
  env.DREAMSEED_COMPAT_KERNEL_JS,
  liteKernelJs,
])
const memoryDir =
  env.DREAMSEED_MEMORY_DIR ||
  path.join(currentProject, '.dreamseed-memory')
const mempalaceSrc =
  env.DREAMSEED_MEMPALACE_SRC ||
  (existsSync(bundledMempalaceSrc)
    ? bundledMempalaceSrc
    : '')
const staticMcpConfig = path.join(root, '.mcp.json')
const dreamseedDir = path.join(root, '.dreamseed')
const settingsFile = path.join(dreamseedDir, 'settings.json')
const promptFile = path.join(root, 'docs', 'dreamseed-system-prompt.md')
const providerBridgeScript = path.join(root, 'scripts', 'provider_bridge.mjs')
const providerManagerScript = path.join(root, 'scripts', 'provider_manager.mjs')
const importHistoryScript = path.join(root, 'scripts', 'import_claude_history.py')
const selfEvolveScript = path.join(root, 'scripts', 'dreamseed_self_evolve.py')
const contextDoctorScript = path.join(root, 'scripts', 'dreamseed_context_doctor.py')
const compactCacheScript = path.join(root, 'scripts', 'dreamseed_compact_cache.py')
const usageScript = path.join(root, 'scripts', 'dreamseed_usage.py')
const mcpDoctorScript = path.join(root, 'scripts', 'mcp_doctor.py')
const hookDoctorScript = path.join(root, 'scripts', 'hook_doctor.py')
const kernelDoctorScript = path.join(root, 'scripts', 'kernel_doctor.py')
const memoryCliScript = path.join(root, 'scripts', 'dreamseed_memory_cli.py')
const evalScript = path.join(root, 'scripts', 'dreamseed_eval.py')
const providerToolsScript = path.join(root, 'scripts', 'provider_tools.py')
const approvalGateScript = path.join(root, 'scripts', 'approval_gate.py')
const updateScript = packagedRuntime
  ? path.join(packagedCwd, 'Update-DreamSeed-Code.ps1')
  : path.join(root, 'scripts', 'update-dreamseed-code.ps1')
const providerConfig = resolveProviderConfig(env, currentProject, root)
const providerConfigTarget =
  providerConfig ||
  preferredLocalProviderConfigPath(env, root) ||
  path.join(localRoot, 'config', 'providers.local.json')
const runtimeLocalConfigPath = path.join(path.dirname(providerConfigTarget), 'runtime.local.json')
const providerPort = Number(env.DREAMSEED_PROVIDER_PORT || 17891)
const providerConfigId = providerConfig ? readProviderConfigId(providerConfig, env.DREAMSEED_PROVIDER) : null
applyRuntimeLocalConfig(env, runtimeLocalConfigPath)
let helperAppReady = false
let helperAppRoot = ''

env.DREAMSEED_LOCAL_ROOT = env.DREAMSEED_LOCAL_ROOT || localRoot
env.DREAMSEED_RUNTIME_DIR = env.DREAMSEED_RUNTIME_DIR || runtimeDir
env.DREAMSEED_CONFIG_DIR = env.DREAMSEED_CONFIG_DIR || path.dirname(providerConfigTarget)
env.DREAMSEED_PROVIDER_CONFIG = env.DREAMSEED_PROVIDER_CONFIG || providerConfigTarget
env.DREAMSEED_LEGACY_HISTORY_DIR = env.DREAMSEED_LEGACY_HISTORY_DIR || legacyHistoryDir
if (defaultKernelJs && !env.DREAMSEED_KERNEL_JS && !env.DREAMSEED_COMPAT_KERNEL_JS) {
  env.DREAMSEED_KERNEL_JS = defaultKernelJs
}

const pythonRuntime = resolvePythonRuntime(env)
env.DREAMSEED_PYTHON = pythonRuntime.command
env.DREAMSEED_PYTHON_ARGS = pythonRuntime.args.join(' ')
env.DREAMSEED_PYTHON_MISSING = pythonRuntime.missing ? '1' : ''
env.DREAMSEED_PYTHON_SITE = pythonSite
env.PYTHONIOENCODING = env.PYTHONIOENCODING || 'utf-8'
let gitBashRuntime = resolveGitBashRuntime(env)
configureGitBashEnv(env, gitBashRuntime)

if (isManagerCommand(args)) {
  await runManagerCommand(args.slice(1), env)
  process.exit(0)
}


if (isProviderCommand(args)) {
  await runProviderCommand(args.slice(1), env, currentProject, root)
  process.exit(0)
}

if (isMcpCommand(args)) {
  await runMcpCommand(args.slice(1), env)
  process.exit(0)
}

if (isMemoryCommand(args)) {
  await runMemoryCommand(args.slice(1), env)
  process.exit(0)
}

if (isEvalCommand(args)) {
  await runEvalCommand(args.slice(1), env)
  process.exit(0)
}

if (isHistoryCommand(args)) {
  await runHistoryCommand(args.slice(1), env)
  process.exit(0)
}

if (isEvolveCommand(args)) {
  await runEvolveCommand(args.slice(1), env)
  process.exit(0)
}

if (isDoctorCommand(args)) {
  await runDoctorCommand(args.slice(1), env)
  process.exit(0)
}

if (isCompactCacheCommand(args)) {
  await runCompactCacheCommand(args.slice(1), env)
  process.exit(0)
}

if (isUsageCommand(args)) {
  await runUsageCommand(args.slice(1), env)
  process.exit(0)
}

if (isApprovalCommand(args)) {
  await runApprovalCommand(args.slice(1), env)
  process.exit(0)
}

if (isUpdateCommand(args)) {
  await runUpdateCommand(args.slice(1), env)
  process.exit(0)
}

if (requiresWindowsGitBash(args, env) && !env['CLAUDE_CODE_GIT_BASH_PATH']) {
  gitBashRuntime = repairGitBashRuntimeIfPossible(env, args)
  configureGitBashEnv(env, gitBashRuntime)
  if (!env['CLAUDE_CODE_GIT_BASH_PATH']) {
    printGitBashUnavailable()
    process.exit(1)
  }
}

env.DREAMSEED_ROOT = root
env.DREAMSEED_HOME = localHome
env.USERPROFILE = localHome
env.HOME = localHome
env.CLAUDE_CONFIG_DIR = path.join(localHome, '.claude')
env.DREAMSEED_MEMORY_DIR = memoryDir
env.DREAMSEED_OUTPUT_COMPRESS = env.DREAMSEED_OUTPUT_COMPRESS || 'off'
env.DREAMSEED_OUTPUT_COMPRESS_LIMIT = env.DREAMSEED_OUTPUT_COMPRESS_LIMIT || '12000'
env.ENABLE_CLAUDE_CODE_SM_COMPACT = env.ENABLE_CLAUDE_CODE_SM_COMPACT || '1'
if (mempalaceSrc) {
  env.DREAMSEED_MEMPALACE_SRC = mempalaceSrc
}
env.MEMPALACE_PATH = env.MEMPALACE_PATH || memoryDir
env.MEMPALACE_WING = env.MEMPALACE_WING || path.basename(currentProject) || 'dreamseed'
env.DREAMSEED_COWORK_MEMORY_PATH_OVERRIDE =
  env.DREAMSEED_COWORK_MEMORY_PATH_OVERRIDE || memoryDir
env.PYTHONIOENCODING = env.PYTHONIOENCODING || 'utf-8'

if (existsSync(pythonSite)) {
  env.PYTHONPATH = prependPath(env.PYTHONPATH, pythonSite)
}
if (mempalaceSrc && existsSync(mempalaceSrc)) {
  env.PYTHONPATH = prependPath(env.PYTHONPATH, mempalaceSrc)
}

const mcpConfig = writeRuntimeMcpConfig() || staticMcpConfig

let providerBridge = null
try {
  providerBridge = await maybeStartProviderBridge({
    configPath: providerConfig,
    scriptPath: providerBridgeScript,
    port: providerPort,
    expectedConfigId: providerConfigId,
    env,
  })
} catch (bridgeError) {
  if (!env.DREAMSEED_QUIET) {
    console.error('[dreamseed] provider bridge startup failed: ' + (bridgeError.message || bridgeError))
  }
}
if (providerBridge) {
  env.DREAMSEED_PROVIDER_CONFIG = providerConfig
  env.DREAMSEED_PROVIDER_PORT = String(providerBridge.port)
  env.ANTHROPIC_BASE_URL = `http://127.0.0.1:${providerBridge.port}`
  env.ANTHROPIC_AUTH_TOKEN = env.DREAMSEED_BRIDGE_AUTH_TOKEN || 'dreamseed-local'
  delete env.ANTHROPIC_API_KEY
  if (providerBridge.health?.model) {
    env.ANTHROPIC_MODEL = providerBridge.health.model
    env.ANTHROPIC_DEFAULT_OPUS_MODEL = providerBridge.health.model
    env.ANTHROPIC_DEFAULT_SONNET_MODEL = providerBridge.health.model
    env.ANTHROPIC_DEFAULT_HAIKU_MODEL = providerBridge.health.model
  }
  if (!env.DREAMSEED_QUIET) {
    console.error(
      `[dreamseed] provider bridge ${providerBridge.health.provider || 'local'} ${providerBridge.health.model || ''} at http://127.0.0.1:${providerBridge.port}`,
    )
  }
}

const injected = []
if (existsSync(settingsFile) && !hasFlag(args, '--settings')) {
  injected.push('--settings', settingsFile)
}
if (existsSync(mcpConfig) && !hasFlag(args, '--mcp-config')) {
  injected.push('--mcp-config', mcpConfig)
}
if (existsSync(root) && !hasFlag(args, '--add-dir') && !env.DREAMSEED_DISABLE_CAPABILITIES) {
  injected.push('--add-dir', root)
}
const dreamseedAgents = loadDreamSeedAgents()
if (
  Object.keys(dreamseedAgents).length > 0 &&
  !hasFlag(args, '--agents') &&
  !env.DREAMSEED_DISABLE_AGENTS
) {
  injected.push('--agents', JSON.stringify(dreamseedAgents))
}
if (existsSync(promptFile) && !hasFlag(args, '--append-system-prompt') && !hasFlag(args, '--append-system-prompt-file')) {
  injected.push('--append-system-prompt-file', promptFile)
}

let command
let commandArgs

const kernelSelection = selectKernel({
  env,
})

if (kernelSelection.kind === 'js') {
  command = process.execPath
  commandArgs = [kernelSelection.value, ...injected, ...args]
} else if (kernelSelection.kind === 'cli') {
  command = kernelSelection.value
  commandArgs = [...injected, ...args]
} else {
  command = 'dreamseed-kernel'
  commandArgs = [...injected, ...args]
}

const child = spawn(command, commandArgs, {
  stdio: 'inherit',
  env,
  cwd: currentProject,
  shell: false,
  windowsHide: true,
})

child.on('error', error => {
  console.error(`[dreamseed] failed to start ${kernelSelection.label}: ${error.message}`)
  console.error('[dreamseed] configure DREAMSEED_COMPAT_KERNEL_JS or DREAMSEED_KERNEL_CLI to point at a compatible runtime.')
  process.exit(1)
})

child.on('exit', (code, signal) => {
  if (providerBridge?.ownedProcess) {
    providerBridge.ownedProcess.kill()
  }
  if (signal) {
    process.kill(process.pid, signal)
    return
  }
  process.exit(code ?? 0)
})


function isProviderCommand(argv) {
  return argv[0] === 'provider' || argv[0] === 'providers'
}

function isMcpCommand(argv) {
  return argv[0] === 'mcp' || argv[0] === 'mcps'
}

function isMemoryCommand(argv) {
  return argv[0] === 'memory' || argv[0] === 'memories'
}

function isEvalCommand(argv) {
  return argv[0] === 'eval' || argv[0] === 'evals'
}

function isManagerCommand(argv) {
  return argv[0] === 'manager' || argv[0] === 'models-ui' || argv[0] === 'model-manager'
}

function isHistoryCommand(argv) {
  return argv[0] === 'history' || argv[0] === 'legacy-history'
}

function isEvolveCommand(argv) {
  return argv[0] === 'evolve' || argv[0] === 'self-evolve'
}

function isDoctorCommand(argv) {
  return argv[0] === 'doctor' || argv[0] === 'doctors'
}

function isCompactCacheCommand(argv) {
  return argv[0] === 'compact-cache' || argv[0] === 'compactcache'
}

function isUsageCommand(argv) {
  return argv[0] === 'usage' || argv[0] === 'use-summary'
}

function isApprovalCommand(argv) {
  return argv[0] === 'approval' || argv[0] === 'approvals' || argv[0] === 'permission' || argv[0] === 'permissions'
}

function isUpdateCommand(argv) {
  return argv[0] === 'update' || argv[0] === 'upgrade'
}

function normalizeKernelArgs(argv) {
  const command = argv[0]
  // Accept legacy aliases as a no-op: lite is now the only kernel.
  if (command === 'fast' || command === 'lite' || command === 'compat' || command === 'compatible') {
    return argv.slice(1)
  }
  return argv
}

function resolveLocalRoot(runtimeEnv) {
  if (runtimeEnv.DREAMSEED_LOCAL_ROOT) return path.resolve(runtimeEnv.DREAMSEED_LOCAL_ROOT)
  if (runtimeEnv.LOCALAPPDATA) return path.join(runtimeEnv.LOCALAPPDATA, 'DreamSeed')
  if (runtimeEnv.APPDATA) return path.join(runtimeEnv.APPDATA, 'DreamSeed')
  if (runtimeEnv.USERPROFILE) return path.join(runtimeEnv.USERPROFILE, '.dreamseed')
  return path.join(process.cwd(), '.dreamseed-local')
}

function resolveLegacyHistoryDir(runtimeEnv, appRoot, privateRoot) {
  if (runtimeEnv.DREAMSEED_LEGACY_HISTORY_DIR) return path.resolve(runtimeEnv.DREAMSEED_LEGACY_HISTORY_DIR)
  const candidates = [
    path.join(privateRoot, 'legacy-history', 'claude-code'),
    path.join(privateRoot, 'app', 'dreamseed-code-0.1.0', 'legacy-history', 'claude-code'),
  ]
  if (!String(appRoot || '').toLowerCase().includes('.asar')) {
    candidates.push(path.join(appRoot, 'legacy-history', 'claude-code'))
  }
  return firstExistingPath(candidates) || path.join(privateRoot, 'legacy-history', 'claude-code')
}

function firstExistingPath(candidates) {
  for (const candidate of candidates || []) {
    if (!candidate) continue
    try {
      if (existsSync(candidate)) return candidate
    } catch {
      // Ignore malformed candidate paths and continue with the next fallback.
    }
  }
  return ''
}

function applyRuntimeLocalConfig(targetEnv, configPath) {
  let config = {}
  try {
    if (configPath && existsSync(configPath)) config = JSON.parse(readFileSync(configPath, 'utf8'))
  } catch {
    config = {}
  }
  const proxy = String(
    targetEnv.DREAMSEED_PROXY ||
    targetEnv.DREAMSEED_HTTP_PROXY ||
    config.proxy ||
    config.httpProxy ||
    '',
  ).trim()
  if (!proxy) return
  for (const name of ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']) {
    if (!targetEnv[name]) targetEnv[name] = proxy
  }
  if (!targetEnv.NO_PROXY && !targetEnv.no_proxy) {
    targetEnv.NO_PROXY = '127.0.0.1,localhost,::1'
    targetEnv.no_proxy = targetEnv.NO_PROXY
  }
}

function readPackageVersion() {
  try {
    const pkg = JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8'))
    return pkg.version || '0.1.0'
  } catch {
    return '0.1.0'
  }
}

function resolvePythonRuntime(runtimeEnv) {
  const explicit = runtimeEnv.DREAMSEED_PYTHON
  const explicitArgs = splitRuntimeArgs(runtimeEnv.DREAMSEED_PYTHON_ARGS)
  if (explicit) {
    const explicitLooksLikePath = /[\\/]/.test(explicit) || /^[A-Za-z]:/.test(explicit)
    if (existsSync(explicit)) {
      const explicitCommand = resolveRunnableCommand(explicit, pythonVersionCheckArgs(explicitArgs))
      if (explicitCommand) return { command: explicitCommand, args: explicitArgs }
    }
    if (!explicitLooksLikePath) {
      const explicitCommand = resolveRunnableCommand(explicit, pythonVersionCheckArgs(explicitArgs))
      if (explicitCommand) return { command: explicitCommand, args: explicitArgs }
    }
  }
  for (const candidate of [
    path.join(localRoot, 'python', 'python.exe'),
    path.join(packagedCwd, 'python', 'python.exe'),
    path.join(root, 'python', 'python.exe'),
  ]) {
    const runnable = resolveRunnableCommand(candidate, pythonVersionCheckArgs())
    if (runnable) return { command: runnable, args: [] }
  }
  const pathPython = resolveRunnableCommand('python', pythonVersionCheckArgs())
  if (pathPython) return { command: pathPython, args: [] }
  const pyCommand = process.platform === 'win32' ? resolveRunnableCommand('py', pythonVersionCheckArgs(['-3'])) : ''
  if (pyCommand) return { command: pyCommand, args: ['-3'] }
  for (const candidate of pythonInstallCandidates(runtimeEnv)) {
    const runnable = resolveRunnableCommand(candidate, pythonVersionCheckArgs())
    if (runnable) return { command: runnable, args: [] }
  }
  return { command: '', args: [], missing: true }
}

function resolveGitBashRuntime(runtimeEnv) {
  if (runtimeEnv.DREAMSEED_TEST_NO_SYSTEM_GIT_BASH === '1') return { path: '' }
  const explicit = runtimeEnv.DREAMSEED_GIT_BASH_PATH || runtimeEnv['CLAUDE_CODE_GIT_BASH_PATH']
  if (explicit && isRunnableGitBash(explicit)) return { path: explicit }

  for (const candidate of gitBashCandidates(runtimeEnv)) {
    if (isRunnableGitBash(candidate)) return { path: candidate }
  }

  const gitCommand = resolveRunnableCommand('git', ['--version'])
  if (gitCommand) {
    const gitBash = path.resolve(path.dirname(gitCommand), '..', '..', 'bin', 'bash.exe')
    if (isRunnableGitBash(gitBash)) return { path: gitBash }
  }

  return { path: '' }
}

function configureGitBashEnv(targetEnv, runtime) {
  if (runtime?.path) {
    targetEnv.DREAMSEED_GIT_BASH_PATH = runtime.path
    targetEnv['CLAUDE_CODE_GIT_BASH_PATH'] = runtime.path
    targetEnv.SHELL = runtime.path
  } else {
    delete targetEnv.DREAMSEED_GIT_BASH_PATH
    delete targetEnv['CLAUDE_CODE_GIT_BASH_PATH']
  }
}

function requiresWindowsGitBash(argv, runtimeEnv) {
  if (process.platform !== 'win32') return false
  if (runtimeEnv.DREAMSEED_ALLOW_MISSING_GIT_BASH === '1') return false
  try {
    const selection = selectKernel({ env: runtimeEnv })
    return selection.kind === 'js' || selection.kind === 'cli'
  } catch {
    return true
  }
}

function repairGitBashRuntimeIfPossible(runtimeEnv, argv) {
  let runtime = resolveGitBashRuntime(runtimeEnv)
  if (runtime.path) return runtime
  if (!shouldAttemptGitBashAutoInstall(runtimeEnv, argv)) return runtime
  console.error('[dreamseed] Git Bash was not found. Trying to install Git for Windows automatically...')
  console.error('[dreamseed] This is required by the bundled compatible Windows kernel.')
  installGitForWindows(runtimeEnv)
  runtime = resolveGitBashRuntime({ ...process.env, ...runtimeEnv })
  if (runtime.path) {
    try {
      if (process.platform === 'win32') {
        spawnSync('setx.exe', ['DREAMSEED_GIT_BASH_PATH', runtime.path], { stdio: 'ignore', windowsHide: true })
      }
    } catch {
      // Persisting the path is best-effort; the current process can continue with env vars.
    }
    console.error(`[dreamseed] Git Bash configured: ${runtime.path}`)
  }
  return runtime
}

function shouldAttemptGitBashAutoInstall(runtimeEnv, argv) {
  if (runtimeEnv.DREAMSEED_SKIP_GIT_INSTALL === '1') return false
  if (runtimeEnv.DREAMSEED_DESKTOP_TASK_ID) return false
  if (runtimeEnv.CI === '1' || runtimeEnv.GITHUB_ACTIONS === 'true') return false
  if (argv.some(arg => arg === '--no-auto-install' || arg === '--skip-deps')) return false
  return Boolean(process.stdout.isTTY || process.stdin.isTTY)
}

function installGitForWindows(runtimeEnv) {
  const winget = resolveRunnableCommand('winget', ['--version'])
  if (!winget) {
    console.error('[dreamseed] winget was not found, so Git for Windows cannot be installed automatically.')
    return false
  }
  const attempts = [
    ['install', '--id', 'Git.Git', '-e', '--source', 'winget', '--scope', 'user', '--accept-package-agreements', '--accept-source-agreements'],
    ['install', '--id', 'Git.Git', '-e', '--source', 'winget', '--accept-package-agreements', '--accept-source-agreements'],
  ]
  for (const attempt of attempts) {
    try {
      const result = spawnSync(winget, attempt, {
        stdio: 'inherit',
        env: runtimeEnv,
        windowsHide: false,
      })
      if (!result.error && result.status === 0 && resolveGitBashRuntime({ ...process.env, ...runtimeEnv }).path) return true
    } catch (error) {
      console.error(`[dreamseed] winget Git install attempt failed: ${error.message}`)
    }
  }
  return false
}

function printGitBashUnavailable() {
  console.error('[dreamseed] Git Bash is still missing, so the compatible Windows kernel cannot start.')
  console.error('[dreamseed] Fix:')
  console.error('  1. Install Git for Windows: https://git-scm.com/downloads/win')
  console.error('  2. Close this terminal and open a new one.')
  console.error('  3. Run: dreamseed')
  console.error('[dreamseed] If Git is installed in a custom location, set:')
  console.error('  setx DREAMSEED_GIT_BASH_PATH "C:\\Program Files\\Git\\bin\\bash.exe"')
}

function gitBashCandidates(runtimeEnv) {
  const candidates = []
  if (runtimeEnv.LOCALAPPDATA) candidates.push(path.join(runtimeEnv.LOCALAPPDATA, 'Programs', 'Git', 'bin', 'bash.exe'))
  if (runtimeEnv.ProgramFiles) candidates.push(path.join(runtimeEnv.ProgramFiles, 'Git', 'bin', 'bash.exe'))
  if (runtimeEnv['ProgramFiles(x86)']) candidates.push(path.join(runtimeEnv['ProgramFiles(x86)'], 'Git', 'bin', 'bash.exe'))
  return [...new Set(candidates.filter(Boolean))]
}

function isRunnableGitBash(candidate) {
  if (!candidate || !existsSync(candidate)) return false
  try {
    const result = spawnSync(candidate, ['--version'], { stdio: 'ignore', windowsHide: true })
    return !result.error && result.status === 0
  } catch {
    return false
  }
}

function pythonInstallCandidates(runtimeEnv) {
  const candidates = [
    path.join(localRoot, 'python', 'python.exe'),
    path.join(root, 'python', 'python.exe'),
    path.join(packagedCwd, 'python', 'python.exe'),
  ]
  const addVersionedRoots = base => {
    if (!base) return
    for (const versionDir of ['Python312', 'Python311', 'Python310']) {
      candidates.push(path.join(base, versionDir, 'python.exe'))
    }
  }
  if (runtimeEnv.LOCALAPPDATA) addVersionedRoots(path.join(runtimeEnv.LOCALAPPDATA, 'Programs', 'Python'))
  addVersionedRoots(runtimeEnv.ProgramFiles)
  addVersionedRoots(runtimeEnv['ProgramFiles(x86)'])
  return [...new Set(candidates.filter(Boolean))]
}

function pythonVersionCheckArgs(prefixArgs = []) {
  return [
    ...prefixArgs,
    '-c',
    'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 12)',
  ]
}

function splitRuntimeArgs(value) {
  return String(value || '').split(/\s+/).map(part => part.trim()).filter(Boolean)
}

function resolveRunnableCommand(command, args = []) {
  for (const candidate of commandCandidates(command)) {
    try {
      const result = spawnSync(candidate, args, { stdio: 'ignore', windowsHide: true })
      if (!result.error && result.status === 0) return candidate
    } catch {
      // Continue trying other command candidates.
    }
  }
  return ''
}

function commandCandidates(command) {
  if (!command) return []
  const looksLikePath = /[\\/]/.test(command) || /^[A-Za-z]:/.test(command)
  if (looksLikePath) return existsSync(command) ? [command] : []
  const resolved = resolveCommandPaths(command)
  return [...resolved, command].filter(Boolean)
}

function resolveCommandPaths(command) {
  try {
    const checker = process.platform === 'win32' ? 'where.exe' : 'which'
    const result = spawnSync(checker, [command], { encoding: 'utf8', windowsHide: true })
    if (result.error || result.status !== 0) return []
    return String(result.stdout || '')
      .split(/\r?\n/)
      .map(line => line.trim())
      .filter(Boolean)
      .filter(candidate => existsSync(candidate))
      .filter(candidate => !/\\WindowsApps\\/i.test(candidate))
  } catch {
    return []
  }
}

function materializePythonHelper(scriptPath) {
  const original = path.resolve(String(scriptPath || ''))
  if (!packagedRuntime && !original.toLowerCase().includes('.asar')) {
    return { scriptPath: original, root }
  }
  const helperRoot = ensurePackagedHelperApp()
  const relative = safeRelativePath(root, original) || path.join('scripts', path.basename(original))
  return {
    scriptPath: path.join(helperRoot, relative),
    root: helperRoot,
  }
}

function ensurePackagedHelperApp() {
  if (helperAppReady && helperAppRoot) return helperAppRoot
  const signature = helperAppSignature().slice(0, 12)
  const preferred = path.join(runtimeDir, `helper-app-${signature}`)
  try {
    ensureHelperApp(preferred)
    return helperAppRoot
  } catch (error) {
    const fallbackRuntime = path.join(tmpdir(), 'DreamSeed', 'runtime')
    const fallback = path.join(fallbackRuntime, `helper-app-${signature}`)
    ensureHelperApp(fallback)
    return helperAppRoot
  }
}

function ensureHelperApp(helperRoot) {
  if (helperAppReady && helperAppRoot === helperRoot) return
  const markerPath = path.join(helperRoot, '.dreamseed-helper.json')
  const expectedSignature = helperAppSignature()
  let shouldRefresh = true
  try {
    const marker = JSON.parse(readFileSync(markerPath, 'utf8'))
    shouldRefresh =
      marker?.signature !== expectedSignature ||
      !existsSync(path.join(helperRoot, 'scripts', 'mcp_doctor.py')) ||
      !existsSync(path.join(helperRoot, '.mcp-tools', 'github-mcp-server.exe'))
  } catch {
    shouldRefresh = true
  }
  if (shouldRefresh) {
    rmSync(helperRoot, { recursive: true, force: true, maxRetries: 3, retryDelay: 200 })
  }
  mkdirSync(helperRoot, { recursive: true })
  for (const entry of ['scripts', 'config', '.dreamseed', 'docs', '.mcp.json', '.mcp-tools', 'package.json', 'requirements-dreamseed.txt']) {
    copyPackagedEntry(path.join(root, entry), path.join(helperRoot, entry))
  }
  writeFileSync(
    markerPath,
    JSON.stringify({ version: packageVersion, signature: expectedSignature, refreshedAt: new Date().toISOString() }, null, 2) + '\n',
    'utf8',
  )
  updateCompatibilityHelperCache(helperRoot)
  helperAppReady = true
  helperAppRoot = helperRoot
}

function updateCompatibilityHelperCache(helperRoot) {
  const compatibilityRoot = path.join(runtimeDir, 'helper-app')
  if (path.resolve(compatibilityRoot).toLowerCase() === path.resolve(helperRoot).toLowerCase()) return
  try {
    rmSync(compatibilityRoot, { recursive: true, force: true, maxRetries: 2, retryDelay: 100 })
    for (const entry of ['scripts', 'config', '.dreamseed', 'docs', '.mcp.json', '.mcp-tools', 'package.json', 'requirements-dreamseed.txt', '.dreamseed-helper.json']) {
      copyPackagedEntry(path.join(helperRoot, entry), path.join(compatibilityRoot, entry))
    }
  } catch {
    // The versioned helper directory is authoritative; the compatibility cache is best-effort.
  }
}

function helperAppSignature() {
  const asarPath = packagedRuntime ? root.slice(0, root.toLowerCase().indexOf('.asar') + '.asar'.length) : root
  let asarStamp = ''
  try {
    const stat = statSync(asarPath)
    asarStamp = `${stat.size}:${Math.trunc(stat.mtimeMs)}`
  } catch {
    asarStamp = ''
  }
  return createHash('sha256').update([packageVersion, asarStamp].join('|')).digest('hex')
}

function safeRelativePath(base, target) {
  try {
    const relative = path.relative(base, target)
    if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) return ''
    return relative
  } catch {
    return ''
  }
}

function copyPackagedEntry(source, target) {
  try {
    const entries = readdirSync(source, { withFileTypes: true })
    mkdirSync(target, { recursive: true })
    for (const entry of entries) {
      if (shouldSkipHelperCopy(entry.name)) continue
      copyPackagedEntry(path.join(source, entry.name), path.join(target, entry.name))
    }
    return
  } catch (error) {
    if (!['ENOTDIR', 'ENOENT'].includes(error?.code)) {
      // Fall through and try reading it as a single file; Electron asar can be conservative here.
    }
  }
  try {
    mkdirSync(path.dirname(target), { recursive: true })
    writeFileSync(target, readFileSync(source))
  } catch {
    // Optional helper assets are copied best-effort. The called script will report if a required file is missing.
  }
}

function shouldSkipHelperCopy(name) {
  return /^(node_modules|dist|legacy-history|memory-candidates|self-evolve-candidates|self-evolve-backups|logs|cache|__pycache__|\.cache)$/i.test(String(name || '')) ||
    /\.pyc$/i.test(String(name || ''))
}

function pythonPrefixArgs(runtimeEnv) {
  return splitRuntimeArgs(runtimeEnv.DREAMSEED_PYTHON_ARGS)
}

function selectKernel({ env: runtimeEnv }) {
  // DreamSeed Lite Kernel only. Legacy claude-cli fallback removed in plan B.
  const kernelJs = firstExistingPath([
    runtimeEnv.DREAMSEED_KERNEL_JS,
    runtimeEnv.DREAMSEED_COMPAT_KERNEL_JS,
    liteKernelJs,
  ])
  if (kernelJs) {
    return { kind: 'js', value: kernelJs, label: 'DreamSeed Lite Kernel' }
  }
  throw new Error('[dreamseed] DreamSeed Lite Kernel was not found. Reinstall DreamSeed Code or set DREAMSEED_KERNEL_JS to a kernel JS file.')
}

async function runDoctorCommand(argv, runtimeEnv) {
  const command = !argv[0] || argv[0].startsWith('--') ? 'context' : argv[0]
  const rest = command === 'context' && (!argv[0] || argv[0].startsWith('--')) ? argv : argv.slice(1)
  if (command === 'context' || command === 'tokens' || command === 'token') {
    await runPythonHelper(contextDoctorScript, rest, runtimeEnv, 'context doctor')
    return
  }
  if (command === 'mcp' || command === 'mcps') {
    const commandArgs = rest.length === 0 || rest[0].startsWith('--') ? ['smoke', ...rest] : rest
    await runPythonHelper(mcpDoctorScript, commandArgs, runtimeEnv, 'mcp doctor')
    return
  }
  if (command === 'hooks' || command === 'hook') {
    const commandArgs = rest.length === 0 || rest[0].startsWith('--') ? ['audit', ...rest] : rest
    await runPythonHelper(hookDoctorScript, commandArgs, runtimeEnv, 'hook doctor')
    return
  }
  if (command === 'kernel' || command === 'kernels' || command === 'runtime') {
    await runPythonHelper(kernelDoctorScript, rest, runtimeEnv, 'kernel doctor')
    return
  }
  console.error('[dreamseed] unknown doctor command: ' + command)
  console.error('Try: dreamseed doctor context | dreamseed doctor mcp | dreamseed doctor hooks | dreamseed doctor kernel')
  process.exit(2)
}

async function runUsageCommand(argv, runtimeEnv) {
  const commandArgs = argv.length === 0 || argv[0].startsWith('--') ? ['summary', ...argv] : argv
  await runPythonHelper(usageScript, commandArgs, runtimeEnv, 'usage summary')
}

async function runCompactCacheCommand(argv, runtimeEnv) {
  const commandArgs = argv.length === 0 || argv[0].startsWith('--') ? ['status', ...argv] : argv
  await runPythonHelper(compactCacheScript, commandArgs, runtimeEnv, 'compact cache')
}

async function runApprovalCommand(argv, runtimeEnv) {
  const commandArgs = argv.length === 0 || argv[0].startsWith('--') ? ['status', ...argv] : argv
  await runPythonHelper(approvalGateScript, commandArgs, runtimeEnv, 'approval gate')
}

async function runUpdateCommand(argv, runtimeEnv) {
  if (argv.includes('--help') || argv.includes('-h')) {
    console.log(`DreamSeed update

Usage:
  dreamseed update              Pull latest from upstream and reinstall.
  dreamseed update --check      Check if an update is available.
  dreamseed update -CheckOnly   Same as --check (legacy alias).

DreamSeed Code is source-based. Updates run via 'git pull' in the repo
cloned to disk, then refresh the launcher shim. Local provider config,
model keys, history, memory, logs, and caches under %LOCALAPPDATA%\\DreamSeed
are never touched.`)
    return
  }
  if (!existsSync(updateScript)) {
    throw new Error(`[dreamseed] updater script missing: ${updateScript}`)
  }
  // Normalize --check to -CheckOnly for the PowerShell script.
  const psArgs = argv.map(arg => {
    const lower = String(arg || '').toLowerCase()
    if (lower === '--check' || lower === '-check' || lower === '--check-only' || lower === '-check-only') {
      return '-CheckOnly'
    }
    return arg
  })
  const args = [
    '-NoProfile',
    '-ExecutionPolicy',
    'Bypass',
    '-File',
    updateScript,
    ...psArgs,
  ]
  const powershell = resolvePowerShellCommand(runtimeEnv)
  const child = spawn(powershell, args, {
    stdio: 'inherit',
    env: runtimeEnv,
    cwd: root,
    shell: false,
    windowsHide: true,
  })
  await waitForChild(child, '[dreamseed] update')
}

function isUpdateCheckOnly(argv) {
  return argv.some(arg => {
    const normalized = String(arg || '').toLowerCase()
    return normalized === '-checkonly' || normalized === '--checkonly' || normalized === '-check-only' || normalized === '--check-only'
  })
}

function resolvePowerShellCommand(runtimeEnv) {
  const candidates = [
    runtimeEnv.DREAMSEED_POWERSHELL,
    runtimeEnv.SystemRoot ? path.join(runtimeEnv.SystemRoot, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe') : '',
    runtimeEnv.SystemRoot ? path.join(runtimeEnv.SystemRoot, 'Sysnative', 'WindowsPowerShell', 'v1.0', 'powershell.exe') : '',
    'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe',
    'powershell.exe',
  ]
  for (const candidate of candidates) {
    if (!candidate) continue
    if (candidate === 'powershell.exe') return candidate
    try {
      if (existsSync(candidate)) return candidate
    } catch {
      // Continue to the next PowerShell fallback.
    }
  }
  return 'powershell.exe'
}

async function runMcpCommand(argv, runtimeEnv) {
  const commandArgs = argv.length === 0 || argv[0].startsWith('--') ? ['list', ...argv] : argv
  await runPythonHelper(mcpDoctorScript, commandArgs, runtimeEnv, 'mcp')
}

async function runMemoryCommand(argv, runtimeEnv) {
  const commandArgs = argv.length === 0 || argv[0].startsWith('--') ? ['audit', ...argv] : argv
  await runPythonHelper(memoryCliScript, commandArgs, runtimeEnv, 'memory')
}

async function runEvalCommand(argv, runtimeEnv) {
  const commandArgs = argv.length === 0 || argv[0].startsWith('--') ? ['run', ...argv] : argv
  await runPythonHelper(evalScript, commandArgs, runtimeEnv, 'eval')
}

async function runPythonHelper(scriptPath, argv, runtimeEnv, label) {
  const helperScript = materializePythonHelper(scriptPath)
  if (!existsSync(helperScript.scriptPath)) {
    throw new Error(`[dreamseed] ${label} script missing: ${helperScript.scriptPath}`)
  }

  const helperEnv = {
    ...runtimeEnv,
    DREAMSEED_ROOT: helperScript.root,
    PYTHONIOENCODING: runtimeEnv.PYTHONIOENCODING || 'utf-8',
  }
  const captureOutput = shouldCaptureHelperOutput(argv, helperEnv)
  const child = spawn(helperEnv.DREAMSEED_PYTHON || 'python', [...pythonPrefixArgs(helperEnv), helperScript.scriptPath, ...argv], {
    stdio: captureOutput ? ['ignore', 'pipe', 'pipe'] : 'inherit',
    env: helperEnv,
    cwd: helperScript.root,
    shell: false,
    windowsHide: true,
  })
  let stdoutText = ''
  let stderrText = ''
  if (captureOutput) {
    child.stdout.on('data', chunk => {
      stdoutText += chunk.toString('utf8')
    })
    child.stderr.on('data', chunk => {
      stderrText += chunk.toString('utf8')
    })
  }

  await new Promise((resolve, reject) => {
    child.on('error', reject)
    child.on('exit', code => {
      if (captureOutput) {
        writePossiblyCompressedOutput(stdoutText, 'stdout', helperEnv)
        writePossiblyCompressedOutput(stderrText, 'stderr', helperEnv)
      }
      if (code && code !== 0) {
        reject(new Error(`[dreamseed] ${label} exited with code ${code}`))
      } else {
        resolve()
      }
    })
  })
}

function shouldCaptureHelperOutput(argv, runtimeEnv) {
  const mode = String(runtimeEnv.DREAMSEED_OUTPUT_COMPRESS || 'off').toLowerCase()
  if (mode === 'off') return false
  if (argv.some(arg => arg === '--json' || String(arg).startsWith('--json='))) return false
  return mode === 'auto' || mode === 'always'
}

function writePossiblyCompressedOutput(text, streamName, runtimeEnv) {
  if (!text) return
  const mode = String(runtimeEnv.DREAMSEED_OUTPUT_COMPRESS || 'off').toLowerCase()
  const limit = Number(runtimeEnv.DREAMSEED_OUTPUT_COMPRESS_LIMIT || 12000)
  const shouldCompress =
    mode === 'always' ||
    (mode === 'auto' && Number.isFinite(limit) && limit > 0 && text.length > limit)
  const target = streamName === 'stderr' ? process.stderr : process.stdout
  if (!shouldCompress || containsSecretLikeDiagnostic(text)) {
    target.write(text)
    return
  }
  target.write(compressOutputText(text))
  if (!text.endsWith('\n')) target.write('\n')
}

function containsSecretLikeDiagnostic(text) {
  return /(api[_-]?key|token|secret|password)\s*[:=]|sk-[A-Za-z0-9_-]{20,}/i.test(text)
}

function compressOutputText(text) {
  const lines = text.split(/\r?\n/)
  const keep = new Set()
  const important = /(error|failed|failure|exception|traceback|warning|denied|missing|invalid|\b[A-Za-z]:\\[^:\s]+:\d+|\/[^:\s]+:\d+)/i
  for (let index = 0; index < lines.length; index += 1) {
    if (!important.test(lines[index])) continue
    keep.add(index)
    if (index > 0) keep.add(index - 1)
    if (index + 1 < lines.length) keep.add(index + 1)
  }
  const keepLast = 20
  for (let index = Math.max(0, lines.length - keepLast); index < lines.length; index += 1) {
    keep.add(index)
  }
  const selected = [...keep].sort((left, right) => left - right).map(index => lines[index])
  const omitted = Math.max(0, lines.length - selected.length)
  return `[dreamseed-output-compress] kept=${selected.length} omitted=${omitted}\n${selected.join('\n')}\n`
}

async function runManagerCommand(argv, runtimeEnv) {
  if (!existsSync(providerManagerScript)) {
    throw new Error(`[dreamseed] model manager script missing: ${providerManagerScript}`)
  }

  const child = spawn(process.execPath, [providerManagerScript, ...argv], {
    stdio: 'inherit',
    env: packagedNodeEnv(runtimeEnv),
    cwd: packagedCwd,
    shell: false,
    windowsHide: true,
  })

  await new Promise((resolve, reject) => {
    child.on('error', reject)
    child.on('exit', code => {
      if (code && code !== 0) {
        reject(new Error(`[dreamseed] model manager exited with code ${code}`))
      } else {
        resolve()
      }
    })
  })
}

async function runEvolveCommand(argv, runtimeEnv) {
  const helperScript = materializePythonHelper(selfEvolveScript)
  if (!existsSync(helperScript.scriptPath)) {
    throw new Error(`[dreamseed] self-evolve script missing: ${helperScript.scriptPath}`)
  }

  const commandArgs = argv.length === 0 || argv[0].startsWith('--') ? ['status', ...argv] : argv
  const helperEnv = { ...runtimeEnv, DREAMSEED_ROOT: helperScript.root }
  const child = spawn(helperEnv.DREAMSEED_PYTHON || 'python', [...pythonPrefixArgs(helperEnv), helperScript.scriptPath, ...commandArgs], {
    stdio: 'inherit',
    env: helperEnv,
    cwd: helperScript.root,
    shell: false,
    windowsHide: true,
  })

  await new Promise((resolve, reject) => {
    child.on('error', reject)
    child.on('exit', code => {
      if (code && code !== 0) {
        reject(new Error(`[dreamseed] self-evolve command exited with code ${code}`))
      } else {
        resolve()
      }
    })
  })
}

function printHistoryPythonUnavailable(commandArgs) {
  const command = commandArgs[0] || 'status'
  const reason = 'Python 3.10+ was not found. Install Python or rerun the DreamSeed installer after Python is available.'
  if (command === 'list-sessions') {
    console.log(JSON.stringify({ ok: true, status: 'unavailable', reason, count: 0, total_matches: 0, sessions: [] }, null, 2))
    return
  }
  if (command === 'search') {
    console.log(JSON.stringify({ ok: true, status: 'unavailable', reason, query: commandArgs[1] || '', count: 0, results: [] }, null, 2))
    return
  }
  if (command === 'show-session') {
    console.log(JSON.stringify({ ok: false, status: 'unavailable', reason, session: null }, null, 2))
    return
  }
  console.log(JSON.stringify({ ok: true, status: 'unavailable', reason, records: 0, sessions: 0, projects: 0, top_projects: [] }, null, 2))
}
async function runHistoryCommand(argv, runtimeEnv) {
  const helperScript = materializePythonHelper(importHistoryScript)
  if (!existsSync(helperScript.scriptPath)) {
    throw new Error(`[dreamseed] legacy history importer missing: ${helperScript.scriptPath}`)
  }

  const commandArgs = argv.length === 0 || argv[0].startsWith('--') ? ['status', ...argv] : argv
  if (runtimeEnv.DREAMSEED_PYTHON_MISSING === '1') {
    printHistoryPythonUnavailable(commandArgs)
    return
  }
  const helperEnv = { ...runtimeEnv, DREAMSEED_ROOT: helperScript.root }
  const child = spawn(helperEnv.DREAMSEED_PYTHON || 'python', [...pythonPrefixArgs(helperEnv), helperScript.scriptPath, ...commandArgs], {
    stdio: 'inherit',
    env: helperEnv,
    cwd: helperScript.root,
    shell: false,
    windowsHide: true,
  })

  await new Promise((resolve, reject) => {
    child.on('error', error => {
      if (error?.code === 'ENOENT') {
        printHistoryPythonUnavailable(commandArgs)
        resolve()
      } else {
        reject(error)
      }
    })
    child.on('exit', code => {
      if (code && code !== 0) {
        reject(new Error(`[dreamseed] legacy history command exited with code ${code}`))
      } else {
        resolve()
      }
    })
  })
}

async function runProviderCommand(argv, runtimeEnv, projectDir, repoRoot) {
  const command = !argv[0] || argv[0].startsWith('--') ? 'status' : argv[0]
  const optionArgs = command === 'status' ? argv : argv.slice(1)
  const options = parseProviderOptions(optionArgs)

  if (options.help || command === 'help') {
    printProviderHelp()
    return
  }

  if (command === 'setup' || command === 'configure' || command === 'config') {
    await setupProvider(options, runtimeEnv, projectDir)
    return
  }

  if (command === 'status') {
    printProviderStatus(options, runtimeEnv, projectDir, repoRoot)
    return
  }

  if (command === 'list' || command === 'ls') {
    printProviderList(options, runtimeEnv, projectDir, repoRoot)
    return
  }

  if (command === 'use' || command === 'switch' || command === 'activate') {
    useProvider(options, runtimeEnv, projectDir, repoRoot)
    return
  }

  if (command === 'path') {
    console.log(resolveProviderWritePath(options, runtimeEnv, projectDir))
    return
  }

  if (command === 'test' || command === 'doctor') {
    await testProvider(options, runtimeEnv, projectDir, repoRoot)
    return
  }

  if (command === 'templates' || command === 'template' || command === 'export-redacted' || command === 'import-redacted' || command === 'latency' || command === 'health' || command === 'discover' || command === 'tools-test' || command === 'tool-test' || command === 'diagnose') {
    await runPythonHelper(providerToolsScript, [command, ...optionArgs], runtimeEnv, 'provider ' + command)
    return
  }

  console.error('[dreamseed] unknown provider command: ' + command)
  printProviderHelp()
  process.exit(2)
}

function printProviderHelp() {
  console.log('DreamSeed provider commands\n')
  console.log('Usage:')
  console.log('  dreamseed provider setup --name NAME --url URL --key KEY --model MODEL')
  console.log('  dreamseed provider list')
  console.log('  dreamseed provider use NAME')
  console.log('  dreamseed provider status')
  console.log('  dreamseed provider test [--prompt TEXT]')
  console.log('  dreamseed provider templates')
  console.log('  dreamseed provider latency')
  console.log('  dreamseed provider health')
  console.log('  dreamseed provider export-redacted')
  console.log('  dreamseed provider import-redacted --from FILE --yes')
  console.log('  dreamseed provider discover')
  console.log('  dreamseed provider tools-test [--all] [--save]')
  console.log('  dreamseed provider diagnose [--all]')
  console.log('  dreamseed provider path\n')
  console.log('Setup stores a private providers.local.json outside the publish layer.')
  console.log('The default upstream type is OpenAI-compatible /v1/chat/completions.')
  console.log('Add or update a model with setup --name, then switch with use NAME.')
  console.log('Secrets are never printed by list, status, test, diagnose, or tools-test output.')
}

async function setupProvider(options, runtimeEnv, projectDir) {
  const configPath = resolveProviderWritePath(options, runtimeEnv, projectDir)
  const existing = readProviderConfigFile(configPath) || { activeProvider: 'default', providers: {} }
  const defaultName = existing.activeProvider || Object.keys(existing.providers || {})[0] || 'default'

  const providerName = sanitizeProviderName(
    optionValue(options, ['name', 'provider']) ||
      (await askLine('Provider name', defaultName || 'default')),
  )

  const existingProvider = existing.providers?.[providerName] || {}
  const rawUrl =
    optionValue(options, ['url', 'base-url', 'baseUrl', 'endpoint']) ||
    (await askLine('Base URL', existingProvider.baseUrl || 'https://api.openai.com'))
  const baseUrl = normalizeProviderBaseUrl(rawUrl)

  const keyEnv = optionValue(options, ['key-env', 'api-key-env', 'apiKeyEnv'])
  let apiKey = optionValue(options, ['key', 'api-key', 'apiKey', 'token'])
  if (!keyEnv && !apiKey && !existingProvider.apiKey) {
    apiKey = await askSecret('API key: ')
  }

  const noDiscover = Boolean(options['no-discover'] || options.noDiscover)
  let discoveredModels = []
  if (!noDiscover && apiKey) {
    discoveredModels = await discoverProviderModels(baseUrl, apiKey, Boolean(options.verbose))
  }

  let model = optionValue(options, ['model']) || existingProvider.model
  if (!model && discoveredModels.length === 1) {
    model = discoveredModels[0]
  } else if (!model && discoveredModels.length > 1 && input.isTTY) {
    model = await chooseDiscoveredModel(discoveredModels)
  }
  if (!model) {
    model = await askLine('Model', discoveredModels[0] || 'gpt-4o-mini')
  }

  const timeoutMs = Number(optionValue(options, ['timeout-ms', 'timeoutMs']) || existingProvider.timeoutMs || 120000)
  const chatPath = optionValue(options, ['chat-path', 'chatCompletionsPath']) || existingProvider.chatCompletionsPath || '/v1/chat/completions'

  const provider = {
    type: optionValue(options, ['type']) || existingProvider.type || 'openai-chat',
    baseUrl,
    model,
    chatCompletionsPath: chatPath,
    systemPrefix:
      optionValue(options, ['system-prefix', 'systemPrefix']) ||
      existingProvider.systemPrefix ||
      defaultProviderSystemPrefix(providerName, model),
    timeoutMs,
  }

  if (keyEnv) {
    provider.apiKeyEnv = keyEnv
  } else if (apiKey) {
    provider.apiKey = apiKey
  } else if (existingProvider.apiKey) {
    provider.apiKey = existingProvider.apiKey
  } else if (existingProvider.apiKeyEnv) {
    provider.apiKeyEnv = existingProvider.apiKeyEnv
  }

  const nextConfig = {
    activeProvider: providerName,
    providers: {
      ...(existing.providers || {}),
      [providerName]: provider,
    },
  }

  mkdirSync(path.dirname(configPath), { recursive: true })
  writeFileSync(configPath, JSON.stringify(nextConfig, null, 2) + '\n', 'utf8')

  console.log('[dreamseed] provider configured')
  console.log('Config: ' + configPath)
  console.log('Provider: ' + providerName)
  console.log('Base URL: ' + displayProviderUrl(baseUrl))
  console.log('Model: ' + model)
  console.log('Auth: ' + describeProviderAuth(provider, runtimeEnv))
}

function defaultProviderSystemPrefix(name, model) {
  const label = `${name} ${model}`.toLowerCase()
  if (/(gemini|gemma)/.test(label)) {
    return 'Use OpenAI-compatible tool_calls exactly when tools are provided; keep final user-facing text in message.content.'
  }
  if (/(deepseek|coder)/.test(label)) {
    return 'When a tool is needed, emit valid tool_calls JSON only through the OpenAI tools field; do not describe tool calls in prose.'
  }
  if (/(glm|zhipu|bigmodel)/.test(label)) {
    return 'Prefer native OpenAI-compatible tool_calls and keep concise visible final answers.'
  }
  return 'Always place the final answer in visible message content. Use OpenAI-compatible tool_calls when tools are available.'
}


function printProviderList(options, runtimeEnv, projectDir, repoRoot) {
  const explicitPath = optionValue(options, ['path', 'config'])
  const configPath = explicitPath
    ? path.resolve(explicitPath)
    : resolveProviderConfig(runtimeEnv, projectDir, repoRoot)

  if (!configPath || !existsSync(configPath)) {
    console.log('[dreamseed] no provider configured')
    console.log('Run: dreamseed provider setup --name default --url <url> --key <key> --model <model>')
    return
  }

  const data = readProviderConfigFile(configPath)
  const providers = data?.providers || {}
  const names = Object.keys(providers)
  if (names.length === 0) {
    console.log('[dreamseed] provider config has no providers')
    console.log('Config: ' + configPath)
    return
  }

  console.log('[dreamseed] providers')
  console.log('Config: ' + configPath)
  for (const name of names) {
    const provider = providers[name]
    const marker = name === data.activeProvider ? '*' : ' '
    console.log(
      marker +
        ' ' +
        name +
        '  model=' +
        (provider.model || '<missing>') +
        '  url=' +
        displayProviderUrl(provider.baseUrl) +
        '  auth=' +
        describeProviderAuth(provider, runtimeEnv) +
        '  capability=' +
        describeProviderCapability(name, provider),
    )
  }
}

function useProvider(options, runtimeEnv, projectDir, repoRoot) {
  const explicitPath = optionValue(options, ['path', 'config'])
  const configPath = explicitPath
    ? path.resolve(explicitPath)
    : resolveProviderConfig(runtimeEnv, projectDir, repoRoot) || resolveProviderWritePath(options, runtimeEnv, projectDir)

  if (!configPath || !existsSync(configPath)) {
    throw new Error('[dreamseed] no provider config found. Run: dreamseed provider setup')
  }

  const data = readProviderConfigFile(configPath)
  const providerName =
    optionValue(options, ['provider', 'name']) ||
    (Array.isArray(options._) && options._[0] ? String(options._[0]) : '')

  if (!providerName) {
    printProviderList(options, runtimeEnv, projectDir, repoRoot)
    throw new Error('[dreamseed] choose a provider with: dreamseed provider use <name>')
  }

  if (!data.providers?.[providerName]) {
    printProviderList(options, runtimeEnv, projectDir, repoRoot)
    throw new Error("[dreamseed] provider '" + providerName + "' was not found")
  }

  data.activeProvider = providerName
  writeFileSync(configPath, JSON.stringify(data, null, 2) + '\n', 'utf8')

  const provider = data.providers[providerName]
  console.log('[dreamseed] active provider switched')
  console.log('Config: ' + configPath)
  console.log('Provider: ' + providerName)
  console.log('Base URL: ' + displayProviderUrl(provider.baseUrl))
  console.log('Model: ' + (provider.model || '<missing>'))
}

function printProviderStatus(options, runtimeEnv, projectDir, repoRoot) {
  const explicitPath = optionValue(options, ['path', 'config'])
  const configPath = explicitPath
    ? path.resolve(explicitPath)
    : resolveProviderConfig(runtimeEnv, projectDir, repoRoot)

  if (!configPath || !existsSync(configPath)) {
    console.log('[dreamseed] no provider configured')
    console.log('Run: dreamseed provider setup')
    console.log('Default private path: ' + resolveProviderWritePath({}, runtimeEnv, projectDir))
    return
  }

  const data = readProviderConfigFile(configPath)
  const providerName = optionValue(options, ['provider', 'name']) || runtimeEnv.DREAMSEED_PROVIDER || data?.activeProvider || Object.keys(data?.providers || {})[0]
  const provider = data?.providers?.[providerName]

  if (!provider) {
    console.log('[dreamseed] provider config found, but active provider is missing')
    console.log('Config: ' + configPath)
    return
  }

  console.log('[dreamseed] provider configured')
  console.log('Config: ' + configPath)
  console.log('Provider: ' + providerName)
  console.log('Type: ' + (provider.type || 'openai-chat'))
  console.log('Base URL: ' + displayProviderUrl(provider.baseUrl))
  console.log('Model: ' + (provider.model || '<missing>'))
  console.log('Auth: ' + describeProviderAuth(provider, runtimeEnv))
  console.log('Capability: ' + describeProviderCapability(providerName, provider))
}

async function testProvider(options, runtimeEnv, projectDir, repoRoot) {
  const configPath =
    optionValue(options, ['path', 'config']) ||
    resolveProviderConfig(runtimeEnv, projectDir, repoRoot)
  if (!configPath || !existsSync(configPath)) {
    throw new Error('[dreamseed] no provider config found. Run: dreamseed provider setup')
  }

  const data = readProviderConfigFile(configPath)
  const providerName =
    optionValue(options, ['provider', 'name']) ||
    runtimeEnv.DREAMSEED_PROVIDER ||
    data?.activeProvider ||
    Object.keys(data?.providers || {})[0]
  const provider = data?.providers?.[providerName]
  if (!provider) {
    throw new Error("[dreamseed] provider '" + (providerName || '<missing>') + "' was not found")
  }

  const apiKey = provider.apiKey || (provider.apiKeyEnv ? runtimeEnv[provider.apiKeyEnv] : '')
  if (!apiKey) {
    throw new Error('[dreamseed] provider key is missing; store apiKey in private config or set ' + (provider.apiKeyEnv || 'apiKeyEnv'))
  }

  const providerType = provider.type || 'openai-chat'
  const prompt = optionValue(options, ['prompt']) || 'Reply exactly: ok'
  const result =
    providerType === 'anthropic-messages'
      ? await testAnthropicProviderDirect(provider, apiKey, prompt)
      : await testOpenAiProviderDirect(provider, apiKey, prompt)

  console.log('[dreamseed] provider test passed')
  console.log('Provider: ' + providerName)
  console.log('Mode: direct ' + providerType)
  console.log('Base URL: ' + displayProviderUrl(provider.baseUrl))
  console.log('Model: ' + (result.model || provider.model || '<unknown>'))
  console.log('Output: ' + result.output.slice(0, 1000))
}

async function testOpenAiProviderDirect(provider, apiKey, prompt) {
  const route = provider.chatCompletionsPath || '/v1/chat/completions'
  const response = await fetch(joinProviderUrl(provider.baseUrl, route), {
    method: 'POST',
    headers: {
      accept: 'application/json',
      'content-type': 'application/json',
      authorization: 'Bearer ' + apiKey,
      'x-api-key': apiKey,
      ...(provider.headers || {}),
    },
    body: JSON.stringify({
      model: provider.model,
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 64,
      stream: false,
    }),
  })
  const text = await response.text()
  if (!response.ok) {
    throw new Error('provider direct test failed (' + response.status + '): ' + text.slice(0, 500))
  }
  const payload = text ? JSON.parse(text) : {}
  return {
    model: payload.model || provider.model,
    output: openAiResponseText(payload),
  }
}

async function testAnthropicProviderDirect(provider, apiKey, prompt) {
  const route = provider.messagesPath || '/v1/messages'
  const response = await fetch(joinProviderUrl(provider.baseUrl, route), {
    method: 'POST',
    headers: {
      accept: 'application/json',
      'content-type': 'application/json',
      authorization: 'Bearer ' + apiKey,
      'x-api-key': apiKey,
      ...(provider.headers || {}),
    },
    body: JSON.stringify({
      model: provider.model,
      max_tokens: 64,
      messages: [{ role: 'user', content: prompt }],
      stream: false,
    }),
  })
  const text = await response.text()
  if (!response.ok) {
    throw new Error('provider direct test failed (' + response.status + '): ' + text.slice(0, 500))
  }
  const payload = text ? JSON.parse(text) : {}
  return {
    model: payload.model || provider.model,
    output: contentToVisibleText(payload.content),
  }
}

function openAiResponseText(payload) {
  const choices = payload?.choices || []
  if (!Array.isArray(choices) || choices.length === 0) return ''
  const message = choices[0]?.message || {}
  if (typeof message.content === 'string') return message.content
  if (Array.isArray(message.content)) {
    return message.content
      .map(part => (typeof part === 'string' ? part : part?.text || ''))
      .filter(Boolean)
      .join('\n')
  }
  return ''
}

async function stopOwnedProviderBridge(bridge, shutdownToken) {
  if (!bridge?.ownedProcess) return

  if (bridge.ownedProcess.exitCode === null && !bridge.ownedProcess.killed) {
    bridge.ownedProcess.kill()
  }
  await waitForProcessExit(bridge.ownedProcess, 2000)
}

async function waitForProcessExit(child, timeoutMs) {
  if (!child || child.exitCode !== null) return
  await new Promise(resolve => {
    const timeout = setTimeout(resolve, timeoutMs)
    child.once('exit', () => {
      clearTimeout(timeout)
      resolve()
    })
  })
}

function parseProviderOptions(argv) {
  const out = { _: [] }
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    if (!arg.startsWith('--')) {
      out._.push(arg)
      continue
    }
    const eq = arg.indexOf('=')
    const key = eq >= 0 ? arg.slice(2, eq) : arg.slice(2)
    if (key === 'help' || key === 'h') {
      out.help = true
      continue
    }
    if (eq >= 0) {
      out[key] = arg.slice(eq + 1)
      continue
    }
    const next = argv[index + 1]
    if (next && !next.startsWith('--')) {
      out[key] = next
      index += 1
    } else {
      out[key] = true
    }
  }
  return out
}

function optionValue(options, names) {
  for (const name of names) {
    if (options[name] !== undefined && options[name] !== true) return String(options[name])
  }
  return ''
}

function resolveProviderWritePath(options, runtimeEnv, projectDir) {
  const explicit = optionValue(options, ['path', 'config'])
  if (explicit) return path.resolve(explicit)
  if (options.project) return path.join(projectDir, '.dreamseed', 'providers.local.json')
  const localConfig = preferredLocalProviderConfigPath(runtimeEnv, root)
  if (localConfig) return localConfig
  const appDataDir = runtimeEnv.APPDATA
  if (appDataDir) return path.join(appDataDir, 'DreamSeed', 'providers.local.json')
  const homeDir = runtimeEnv.DREAMSEED_HOME || runtimeEnv.HOME || runtimeEnv.USERPROFILE
  if (homeDir) return path.join(homeDir, '.dreamseed', 'providers.local.json')
  return path.join(projectDir, '.dreamseed', 'providers.local.json')
}

function readProviderConfigFile(configPath) {
  if (!configPath || !existsSync(configPath)) return null
  try {
    const data = JSON.parse(readFileSync(configPath, 'utf8'))
    if (!data.providers || typeof data.providers !== 'object') data.providers = {}
    return data
  } catch (error) {
    throw new Error('[dreamseed] failed to read provider config at ' + configPath + ': ' + error.message)
  }
}

function sanitizeProviderName(value) {
  const name = String(value || 'default').trim().toLowerCase().replace(/[^a-z0-9_.-]+/g, '-').replace(/^-+|-+$/g, '')
  return name || 'default'
}

function normalizeProviderBaseUrl(value) {
  const raw = String(value || '').trim()
  if (!raw) throw new Error('[dreamseed] provider base URL is required')
  const parsed = new URL(raw)
  parsed.search = ''
  parsed.hash = ''
  return parsed.toString().replace(/\/+$/, '')
}

function displayProviderUrl(value) {
  try {
    const parsed = new URL(value)
    parsed.username = ''
    parsed.password = ''
    parsed.search = ''
    parsed.hash = ''
    return parsed.toString().replace(/\/+$/, '')
  } catch {
    return '<invalid-url>'
  }
}

function describeProviderCapability(name, provider) {
  const modality = inferProviderModality(name, provider)
  if (provider.agentCapable === false) return `agent=no modality=${modality}`
  if (provider.toolSupport) {
    const agent = provider.agentCapable === false ? 'no' : 'yes'
    return `agent=${agent} modality=${modality} tools=${provider.toolSupport}`
  }
  if (modality !== 'text') return `agent=probably-no modality=${modality}`
  return 'agent=unknown modality=text run provider tools-test'
}

function inferProviderModality(name, provider) {
  if (provider.modality || provider.capability) return String(provider.modality || provider.capability)
  const label = `${name} ${provider.model || ''}`
  if (/(image|img|dall[-_ ]?e|flux|sdxl|stable-diffusion|midjourney)/i.test(label)) return 'image'
  if (/(embedding|rerank|tts|audio|whisper)/i.test(label)) return 'non-agent'
  return 'text'
}

function describeProviderAuth(provider, runtimeEnv) {
  if (provider.apiKeyEnv) {
    return runtimeEnv[provider.apiKeyEnv] ? 'env ' + provider.apiKeyEnv + ' is set' : 'env ' + provider.apiKeyEnv + ' is missing'
  }
  if (provider.apiKey) return 'stored in private config'
  return 'missing'
}

async function discoverProviderModels(baseUrl, apiKey, verbose) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 5000)
  try {
    const response = await fetch(joinProviderUrl(baseUrl, '/v1/models'), {
      signal: controller.signal,
      headers: {
        accept: 'application/json',
        authorization: 'Bearer ' + apiKey,
        'x-api-key': apiKey,
      },
    })
    if (!response.ok) return []
    const payload = await response.json()
    const rawModels = Array.isArray(payload.data) ? payload.data : Array.isArray(payload.models) ? payload.models : []
    return rawModels
      .map(model => (typeof model === 'string' ? model : model?.id || model?.name))
      .filter(Boolean)
  } catch (error) {
    if (verbose) console.error('[dreamseed] model discovery skipped: ' + error.message)
    return []
  } finally {
    clearTimeout(timeout)
  }
}

async function chooseDiscoveredModel(models) {
  console.log('Discovered models:')
  models.slice(0, 12).forEach((model, index) => {
    console.log('  ' + (index + 1) + '. ' + model)
  })
  const answer = await askLine('Model number or name', models[0])
  const selectedIndex = Number(answer)
  if (Number.isInteger(selectedIndex) && selectedIndex >= 1 && selectedIndex <= models.length) {
    return models[selectedIndex - 1]
  }
  return answer
}

async function askLine(label, defaultValue = '') {
  if (!input.isTTY) {
    if (defaultValue) return defaultValue
    throw new Error('[dreamseed] missing required option for non-interactive provider setup: ' + label)
  }
  const rl = createInterface({ input, output })
  try {
    const suffix = defaultValue ? ' [' + defaultValue + ']' : ''
    const answer = await rl.question(label + suffix + ': ')
    return answer.trim() || defaultValue
  } finally {
    rl.close()
  }
}

async function askSecret(label) {
  if (!input.isTTY || typeof input.setRawMode !== 'function') {
    return askLine(label.replace(/:\s*$/, ''), '')
  }
  return new Promise(resolve => {
    let value = ''
    const wasRaw = input.isRaw
    output.write(label)
    input.resume()
    input.setRawMode(true)
    input.setEncoding('utf8')
    const done = () => {
      input.off('data', onData)
      input.setRawMode(Boolean(wasRaw))
      output.write('\n')
      resolve(value)
    }
    const onData = chunk => {
      for (const char of String(chunk)) {
        if (char === '\u0003') {
          output.write('\n')
          process.exit(130)
        }
        if (char === '\r' || char === '\n') {
          done()
          return
        }
        if (char === '\b' || char === '\u007f') {
          value = value.slice(0, -1)
          continue
        }
        value += char
      }
    }
    input.on('data', onData)
  })
}

function joinProviderUrl(baseUrl, routePath) {
  return String(baseUrl).replace(/\/+$/, '') + '/' + String(routePath).replace(/^\/+/, '')
}

function contentToVisibleText(content) {
  if (typeof content === 'string') return content
  if (!Array.isArray(content)) return ''
  return content
    .map(block => {
      if (typeof block === 'string') return block
      if (block?.type === 'text') return block.text || ''
      if (block?.type === 'tool_use') return '[tool_use:' + (block.name || 'tool') + ']'
      return ''
    })
    .filter(Boolean)
    .join('\n')
}


function hasFlag(argv, name) {
  return argv.some(arg => arg === name || arg.startsWith(`${name}=`))
}

function prependPath(current, value) {
  if (!value) return current || ''
  const parts = current ? current.split(path.delimiter).filter(Boolean) : []
  const normalizedValue = normalizeFsPath(value)
  const alreadyPresent = parts.some(part => normalizeFsPath(part) === normalizedValue)
  return alreadyPresent ? parts.join(path.delimiter) : [value, ...parts].join(path.delimiter)
}

function normalizeFsPath(value) {
  return path.resolve(value).toLowerCase()
}

function uniquePaths(values) {
  const seen = new Set()
  const result = []
  for (const value of values.filter(Boolean)) {
    const normalized = normalizeFsPath(value)
    if (seen.has(normalized)) continue
    seen.add(normalized)
    result.push(value)
  }
  return result
}

function writeRuntimeMcpConfig() {
  if (env.DREAMSEED_DISABLE_MEMPALACE_MCP) return null

  const config = {
    mcpServers: {
      mempalace: {
        type: 'stdio',
        command: env.DREAMSEED_PYTHON || 'python',
        args: [...pythonPrefixArgs(env), '-m', 'mempalace_evolve.adapters.mcp_server'],
        env: {
          PYTHONIOENCODING: env.PYTHONIOENCODING || 'utf-8',
          PYTHONPATH: env.PYTHONPATH || '',
          MEMPALACE_PATH: env.MEMPALACE_PATH || memoryDir,
          MEMPALACE_WING: env.MEMPALACE_WING || 'dreamseed',
          DREAMSEED_ROOT: root,
          DREAMSEED_MEMORY_DIR: memoryDir,
          DREAMSEED_PYTHON_SITE: pythonSite,
        },
      },
    },
  }
  if (mempalaceSrc) {
    config.mcpServers.mempalace.env.DREAMSEED_MEMPALACE_SRC = mempalaceSrc
  }

  let firstError = null
  for (const candidateDir of uniquePaths([runtimeDir, path.join(tmpdir(), 'DreamSeed', 'runtime')])) {
    try {
      mkdirSync(candidateDir, { recursive: true })
      const generatedPath = path.join(candidateDir, 'mcp.generated.json')
      writeFileSync(generatedPath, `${JSON.stringify(config, null, 2)}\n`, 'utf8')
      return generatedPath
    } catch (error) {
      firstError = firstError || error
    }
  }

  if (!env.DREAMSEED_QUIET && firstError) {
    console.error(`[dreamseed] could not write runtime MCP config: ${firstError.message}`)
  }
  return null
}

function isHelpRequest(argv) {
  return argv.some(arg => arg === '--help' || arg === '-h')
}

function isVersionRequest(argv) {
  return argv.some(arg => arg === '--version' || arg === '-v' || arg === 'version')
}

function printLauncherHelp() {
  console.log(`DreamSeed Code launcher

Usage:
  dreamseed [kernel arguments...]
  node bin/dreamseed-agent.js [kernel arguments...]

Runtime:
  DREAMSEED_KERNEL_JS   Override path to the kernel JS file. Defaults to
                        bin/dreamseed-lite-kernel.js inside this install.
  DREAMSEED_COMPAT_KERNEL_JS
                        Legacy alias for DREAMSEED_KERNEL_JS. Recognized for
                        backward compatibility.
  DREAMSEED_PROVIDER_CONFIG
                        Optional private provider config. When present,
                        DreamSeed starts scripts/provider_bridge.mjs and exposes
                        an Anthropic-compatible local endpoint.

Provider shortcuts:
  dreamseed manager
                        Open the local DreamSeed Model Manager in a browser.
                        Use it to add, edit, delete, test, and switch models
                        before entering the agent.
  dreamseed provider setup
                        Configure an OpenAI-compatible model endpoint by entering
                        only a base URL, API key, and model name.
  dreamseed provider list
                        Show all configured providers without printing secrets.
  dreamseed provider use NAME
                        Switch the active provider/model.
  dreamseed provider status
                        Show the active provider without printing secrets.
  dreamseed provider test
                        Send a small request through the local provider bridge.
  dreamseed provider templates
                        Show publishable provider templates without secrets.
  dreamseed provider latency
                        Check local provider bridge health and latency.
  dreamseed provider health
                        Show active provider health without printing secrets.
  dreamseed provider export-redacted
                        Print provider config with secrets redacted.
  dreamseed provider import-redacted --from FILE --yes
                        Import a redacted provider template into private config.
  dreamseed provider discover
                        Discover model names from the active provider when supported.
  dreamseed provider tools-test [--all] [--save]
                        Verify OpenAI tool_calls support without printing secrets.
  dreamseed provider diagnose [--all]
                        Classify model/tool compatibility and prompt adapter hints.
  dreamseed mcp list
                        List configured MCP servers and registry metadata.
  dreamseed mcp candidates
                        List external MCP candidates; they are disabled by default.
  dreamseed mcp inspect NAME
                        Inspect a registered MCP server or candidate.
  dreamseed mcp enable NAME --yes
                        Enable a reviewed MCP entry. High-risk candidates also
                        require --allow-high-risk.
  dreamseed mcp disable NAME --yes
                        Disable an MCP server from .mcp.json.
  dreamseed mcp test NAME
                        Test an MCP server or candidate without enabling it.
  dreamseed memory audit
                        Audit memory candidates without printing full private text.
  dreamseed memory candidates
                        List memory candidates through the review gate.
  dreamseed memory reject-noisy
                        Reject noisy memory candidates.
  dreamseed memory promote-reviewed
                        Promote reviewed candidates only; requires --yes or --dry-run.
  dreamseed eval run --suite smoke
                        Run lightweight evaluation suites with local failure artifacts.
  dreamseed history status
                        Show imported legacy history status.
  dreamseed history search "keyword"
                        Search the private legacy history archive without
                        promoting it into long-term memory.
  dreamseed history import
                        Import a local legacy recovery archive into
                        legacy-history/ and memory-candidates/.
  dreamseed evolve status
                        Show the controlled self-evolution queue.
  dreamseed evolve propose
                        Create a reviewable improvement candidate. It does not
                        modify source files until apply --yes is used.
  dreamseed evolve apply ID --yes
                        Apply staged proposal files with backups and audit.
  dreamseed evolve rollback ID --yes
                        Restore files from the proposal backup.
  dreamseed evolve score ID
                        Score a self-evolution proposal before applying it.
  dreamseed evolve test ID
                        Run proposal verification without applying source changes.
  dreamseed evolve archive-failure ID
                        Archive a failed proposal locally; it is excluded from packages.
  dreamseed evolve memory-candidate ID
                        Write a reviewed proposal lesson as a memory candidate only.
  dreamseed doctor context
                        Inspect prompt, skill, agent, MCP, memory, and resume
                        context size without changing runtime behavior.
  dreamseed compact-cache build|status|show
                        Build or inspect local project summary cache for faster
                        manual compact handoffs.
  dreamseed doctor mcp
                        Audit MCP registry and configured MCP servers.
  dreamseed doctor hooks
                        Audit hook commands, timeouts, scripts, and memory
                        promotion safety.
  dreamseed doctor kernel
                        Inspect compatible runtime routing and known slow paths.
  dreamseed usage summary
                        Summarize provider, history, and legacy usage without
                        printing secrets.
  dreamseed approval status
                        Show the auto-review approval policy without printing
                        private command payloads.
  dreamseed approval audit
                        Verify PermissionRequest wiring and sample risk
                        decisions.
  dreamseed approval check --tool Bash --command "git status --short"
                        Classify a tool request as allow, ask, or deny.
  dreamseed update
                        Update the DreamSeed Code terminal runtime from the public
                        DreamSeed package while preserving local config,
                        history, memory, logs, and model keys.
  /resume
                        Inside the interactive runtime, list imported
                        legacy sessions and load the selected session as
                        current conversation context only.

DreamSeed automatically wires:
  .dreamseed/settings.json
  .dreamseed/skills
  .dreamseed/agents
  .mcp.json
  docs/dreamseed-system-prompt.md
  DREAMSEED_MEMORY_DIR / MemPalace environment
`)
}

function resolveProviderConfig(runtimeEnv, projectDir, repoRoot) {
  const homeDir = runtimeEnv.DREAMSEED_HOME || runtimeEnv.HOME || runtimeEnv.USERPROFILE
  const appDataDir = runtimeEnv.APPDATA
  const localConfig = preferredLocalProviderConfigPath(runtimeEnv, repoRoot)
  const candidates = [
    runtimeEnv.DREAMSEED_PROVIDER_CONFIG,
    localConfig,
    path.join(projectDir, '.dreamseed', 'providers.local.json'),
    homeDir ? path.join(homeDir, '.dreamseed', 'providers.local.json') : null,
    appDataDir ? path.join(appDataDir, 'DreamSeed', 'providers.local.json') : null,
    path.join(repoRoot, 'config', 'providers.local.json'),
  ].filter(Boolean)
  return candidates.find(candidate => existsSync(candidate))
}

function isPrintWithoutInput(argv) {
  if (!hasFlag(argv, '--print')) return false
  const valueFlags = new Set([
    '--output-format',
    '--max-turns',
    '--model',
    '--settings',
    '--mcp-config',
    '--add-dir',
    '--agents',
    '--append-system-prompt',
    '--append-system-prompt-file',
    '--permission-mode',
    '--cwd',
  ])
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    if (!arg || arg === '--print') continue
    if (arg === '--') return index + 1 < argv.length
    if (arg.startsWith('--') && arg.includes('=')) continue
    if (valueFlags.has(arg)) {
      index += 1
      continue
    }
    if (arg.startsWith('-')) continue
    return false
  }
  return true
}

function isBareNonInteractiveLaunch(argv, runtimeEnv) {
  if (argv.length !== 0) return false
  if (runtimeEnv.DREAMSEED_ALLOW_NON_TTY_INTERACTIVE === '1') return false
  return process.stdin.isTTY !== true && process.stdout.isTTY !== true
}

function printBareNonInteractiveHelp() {
  console.error('[dreamseed] interactive mode requires a real terminal.')
  console.error('Open Command Prompt or PowerShell and run: dreamseed')
  console.error('For non-interactive use, run: dreamseed --print "Reply exactly: ok"')
}

function preferredLocalProviderConfigPath(runtimeEnv, repoRoot) {
  if (runtimeEnv.DREAMSEED_CONFIG_DIR) {
    return path.join(runtimeEnv.DREAMSEED_CONFIG_DIR, 'providers.local.json')
  }
  if (runtimeEnv.DREAMSEED_LOCAL_ROOT) {
    return path.join(runtimeEnv.DREAMSEED_LOCAL_ROOT, 'config', 'providers.local.json')
  }
  if (runtimeEnv.LOCALAPPDATA) {
    return path.join(runtimeEnv.LOCALAPPDATA, 'DreamSeed', 'config', 'providers.local.json')
  }
  const candidates = [
    !packagedRuntime && inferLocalRootFromRepo(repoRoot) ? path.join(inferLocalRootFromRepo(repoRoot), 'config', 'providers.local.json') : null,
  ].filter(Boolean)
  return candidates.find(candidate => candidate && (existsSync(candidate) || existsSync(path.dirname(candidate)))) || candidates[0] || ''
}

function inferLocalRootFromRepo(repoRoot) {
  const normalized = path.normalize(repoRoot || '')
  const marker = `${path.sep}app${path.sep}`
  const index = normalized.toLowerCase().lastIndexOf(marker)
  return index > 0 ? normalized.slice(0, index) : ''
}

async function maybeStartProviderBridge({ configPath, scriptPath, port, expectedConfigId, env: runtimeEnv }) {
  if (!configPath || runtimeEnv.DREAMSEED_DISABLE_PROVIDER_BRIDGE) return null
  if (!existsSync(scriptPath)) {
    throw new Error(`[dreamseed] provider bridge script missing: ${scriptPath}`)
  }

  let selectedPort = port
  for (let offset = 0; offset < 20; offset += 1) {
    const candidatePort = port + offset
    const existing = await readProviderBridgeHealth(candidatePort)
    if (!existing?.ok) {
      selectedPort = candidatePort
      break
    }
    if (!expectedConfigId || existing.configId === expectedConfigId) {
      return { health: existing, ownedProcess: null, port: candidatePort }
    }
  }

  const child = spawn(process.execPath, [scriptPath, '--config', configPath, '--port', String(selectedPort)], {
    stdio: 'ignore',
    env: packagedNodeEnv(runtimeEnv),
    cwd: packagedRuntime ? packagedCwd : path.dirname(scriptPath),
    shell: false,
    windowsHide: true,
  })

  const deadline = Date.now() + 15000
  while (Date.now() < deadline) {
    await sleep(250)
    const health = await readProviderBridgeHealth(selectedPort)
    if (health?.ok && (!expectedConfigId || health.configId === expectedConfigId)) {
      return { health, ownedProcess: child, port: selectedPort }
    }
  }

  child.kill()
  throw new Error(`[dreamseed] provider bridge did not become healthy on port ${selectedPort}`)
}

async function readProviderBridgeHealth(port) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 1500)
  try {
    const response = await fetch(`http://127.0.0.1:${port}/health`, {
      signal: controller.signal,
    })
    if (!response.ok) return null
    return await response.json()
  } catch {
    return null
  } finally {
    clearTimeout(timeout)
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function packagedNodeEnv(runtimeEnv) {
  if (!packagedRuntime) return runtimeEnv
  return { ...runtimeEnv, ELECTRON_RUN_AS_NODE: '1' }
}

function waitForChild(child, label) {
  return new Promise((resolve, reject) => {
    child.on('error', reject)
    child.on('exit', code => {
      if (code && code !== 0) reject(new Error(`${label} exited with code ${code}`))
      else resolve()
    })
  })
}

function readProviderConfigId(configPath, explicitProviderName) {
  try {
    const data = JSON.parse(readFileSync(configPath, 'utf8'))
    const providerName = explicitProviderName || data.activeProvider || Object.keys(data.providers || {})[0]
    const provider = data.providers?.[providerName]
    if (!provider) return null
    const stable = {
      name: providerName,
      type: provider.type || 'openai-chat',
      baseUrl: redactUrl(provider.baseUrl),
      model: provider.model,
      chatCompletionsPath: provider.chatCompletionsPath || '/v1/chat/completions',
      messagesPath: provider.messagesPath,
    }
    return createHash('sha256').update(JSON.stringify(stable)).digest('hex').slice(0, 16)
  } catch {
    return null
  }
}

function redactUrl(url) {
  try {
    const parsed = new URL(url)
    return `${parsed.protocol}//${parsed.host}`
  } catch {
    return '<invalid-url>'
  }
}

function loadDreamSeedAgents() {
  const agentsDir = path.join(dreamseedDir, 'agents')
  if (!existsSync(agentsDir)) return {}

  const agents = {}
  for (const entry of readdirSync(agentsDir, { withFileTypes: true })) {
    if (!entry.isFile() || !entry.name.endsWith('.md')) continue
    const filePath = path.join(agentsDir, entry.name)
    const raw = readFileSync(filePath, 'utf8')
    const parsed = parseAgentMarkdown(raw)
    if (!parsed?.frontmatter.name || !parsed.frontmatter.description) continue

    const name = String(parsed.frontmatter.name)
    agents[name] = {
      description: String(parsed.frontmatter.description),
      prompt: parsed.body,
    }

    for (const key of ['tools', 'disallowedTools', 'skills', 'mcpServers']) {
      if (parsed.frontmatter[key] !== undefined) agents[name][key] = parsed.frontmatter[key]
    }
    for (const key of ['model', 'permissionMode', 'memory', 'initialPrompt', 'isolation']) {
      if (typeof parsed.frontmatter[key] === 'string') agents[name][key] = parsed.frontmatter[key]
    }
    for (const key of ['maxTurns', 'effort']) {
      if (typeof parsed.frontmatter[key] === 'number') agents[name][key] = parsed.frontmatter[key]
    }
    if (typeof parsed.frontmatter.background === 'boolean') {
      agents[name].background = parsed.frontmatter.background
    }
  }
  return agents
}

function parseAgentMarkdown(raw) {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/)
  if (!match) return null
  return {
    frontmatter: parseSimpleYaml(match[1]),
    body: match[2].trim(),
  }
}

function parseSimpleYaml(yaml) {
  const result = {}
  const lines = yaml.split(/\r?\n/)
  let currentKey = null
  for (const rawLine of lines) {
    const line = rawLine.replace(/\t/g, '  ')
    if (!line.trim() || line.trimStart().startsWith('#')) continue

    const keyValue = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/)
    if (keyValue) {
      currentKey = keyValue[1]
      const value = keyValue[2]
      if (value === '') {
        result[currentKey] = []
      } else {
        result[currentKey] = parseScalar(value)
        currentKey = null
      }
      continue
    }

    const listItem = line.match(/^\s*-\s*(.*)$/)
    if (listItem && currentKey) {
      if (!Array.isArray(result[currentKey])) result[currentKey] = []
      result[currentKey].push(parseScalar(listItem[1]))
    }
  }
  return result
}

function parseScalar(value) {
  const trimmed = value.trim()
  if (trimmed === 'true') return true
  if (trimmed === 'false') return false
  if (/^-?\d+$/.test(trimmed)) return Number(trimmed)
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1)
  }
  return trimmed
}

