import { app, BrowserWindow, dialog, ipcMain, Menu, shell } from 'electron'
import { randomUUID } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawn } from 'node:child_process'
import { writeDesktopHistorySession as persistDesktopHistorySession } from './shared-history.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const appRoot = process.env.DREAMSEED_APP_ROOT || path.resolve(__dirname, '..')
const localRoot = process.env.DREAMSEED_LOCAL_ROOT || 'D:\\DreamSeed-Local-Agent'
const localBin = path.join(localRoot, 'bin', 'dreamseed-local.cmd')
const dreamSeedAgent = path.join(appRoot, 'bin', 'dreamseed-agent.js')
const nodeCommand = resolveNodeCommand()
const privateConfigDir = process.env.DREAMSEED_CONFIG_DIR || path.join(localRoot, 'config')
const providerConfigPath = process.env.DREAMSEED_PROVIDER_CONFIG || path.join(privateConfigDir, 'providers.local.json')
const desktopConfigPath = path.join(privateConfigDir, 'desktop.local.json')
const desktopHistorySessionsDir = path.join(appRoot, 'legacy-history', 'claude-code', 'sessions')
const logDir = path.join(localRoot, 'logs')
const desktopErrorLog = path.join(logDir, 'dreamseed-desktop-main.log')

let mainWindow
const runningTaskProcesses = new Map()

app.setName('DreamSeed Desktop')
logDesktopError('main process starting')
process.on('uncaughtException', error => {
  logDesktopError(`uncaughtException: ${error.stack || error.message || error}`)
})
process.on('unhandledRejection', error => {
  logDesktopError(`unhandledRejection: ${error?.stack || error?.message || error}`)
})

app.whenReady().then(() => {
  logDesktopError('app ready')
  Menu.setApplicationMenu(null)
  registerIpc()
  createWindow()
}).catch(error => {
  logDesktopError(`whenReady failed: ${error.stack || error.message || error}`)
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

function createWindow() {
  logDesktopError('creating window')
  mainWindow = new BrowserWindow({
    width: 1360,
    height: 880,
    minWidth: 1080,
    minHeight: 720,
    title: 'DreamSeed Desktop',
    backgroundColor: '#101417',
    titleBarStyle: 'default',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })
  logDesktopError('window created')
  mainWindow.on('show', () => logDesktopError('window show'))
  mainWindow.on('closed', () => logDesktopError('window closed'))
  mainWindow.webContents.on('did-finish-load', () => logDesktopError('renderer did-finish-load'))
  mainWindow.webContents.on('did-fail-load', (_event, code, description) => logDesktopError(`renderer did-fail-load ${code}: ${description}`))
  mainWindow.webContents.on('console-message', (_event, level, message, line, sourceId) => {
    if (level >= 2) logDesktopError(`renderer console ${level}: ${message} (${sourceId}:${line})`)
  })
  mainWindow.webContents.on('preload-error', (_event, preloadPath, error) => {
    logDesktopError(`preload error in ${preloadPath}: ${error.stack || error.message || error}`)
  })
  mainWindow.webContents.on('render-process-gone', (_event, details) => logDesktopError(`renderer gone: ${JSON.stringify(details)}`))
  mainWindow.once('ready-to-show', () => {
    logDesktopError('ready-to-show')
    mainWindow.show()
    mainWindow.focus()
  })
  mainWindow.loadFile(path.join(__dirname, 'index.html')).catch(error => {
    logDesktopError(`loadFile failed: ${error.stack || error.message || error}`)
  })
}

function logDesktopError(message) {
  try {
    mkdirSync(logDir, { recursive: true })
    writeFileSync(desktopErrorLog, `[${new Date().toISOString()}] ${message}\n`, { flag: 'a' })
  } catch {
    // Last-resort logging must never crash the desktop process.
  }
}

function registerIpc() {
  ipcMain.handle('status:get', () => statusPayload())
  ipcMain.handle('project:list', () => ({ projects: readDesktopConfig().projects || [], activeProject: readDesktopConfig().activeProject || '' }))
  ipcMain.handle('project:choose', chooseProject)
  ipcMain.handle('project:save', (_event, payload) => saveProject(payload || {}))
  ipcMain.handle('project:delete', (_event, id) => deleteProject(id))
  ipcMain.handle('project:active', (_event, id) => setActiveProject(id))

  ipcMain.handle('provider:list', () => publicProviderConfig())
  ipcMain.handle('provider:save', (_event, payload) => saveProvider(payload || {}))
  ipcMain.handle('provider:delete', (_event, name) => deleteProvider(name))
  ipcMain.handle('provider:active', (_event, name) => setActiveProvider(name))
  ipcMain.handle('provider:test', () => runDreamSeed(['provider', 'test'], activeProjectPath(), 45000))
  ipcMain.handle('provider:diagnose', () => runDreamSeed(['provider', 'diagnose', '--all'], activeProjectPath(), 60000))

  ipcMain.handle('history:status', () => historyStatus())
  ipcMain.handle('history:list', (_event, payload) => listHistorySessions(payload || {}))
  ipcMain.handle('history:search', (_event, payload) => searchHistory(payload || {}))
  ipcMain.handle('history:show', (_event, payload) => showHistorySession(payload || {}))

  ipcMain.handle('workspace:changes', (_event, payload) => workspaceChanges(payload || {}))
  ipcMain.handle('workspace:diff', (_event, payload) => workspaceDiff(payload || {}))

  ipcMain.handle('task:run', (event, payload) => runTask(payload || {}, event.sender))
  ipcMain.handle('task:cancel', (_event, payload) => cancelRunningTask(payload || {}))
  ipcMain.handle('terminal:open', (_event, payload) => openDreamSeedTerminal(selectedProjectPath(payload?.projectId), payload?.mode || 'work'))
  ipcMain.handle('terminal:check', (_event, payload) => terminalCheck(payload || {}))
  ipcMain.handle('terminal:run', (_event, payload) => terminalRun(payload || {}))
  ipcMain.handle('doctor:run', (_event, name) => runDoctor(name || 'context'))
  ipcMain.handle('memory:audit', () => runDreamSeed(['memory', 'audit'], activeProjectPath(), 45000))
  ipcMain.handle('evolve:status', () => runDreamSeed(['evolve', 'status'], activeProjectPath(), 45000))
  ipcMain.handle('desktop:threads:list', () => listThreads())
  ipcMain.handle('desktop:threads:create', (_event, payload) => createThread(payload || {}))
  ipcMain.handle('desktop:threads:update', (_event, payload) => updateThread(payload || {}))
  ipcMain.handle('desktop:threads:select', (_event, id) => selectThread(id))
  ipcMain.handle('desktop:tasks:list', () => listTasks())
  ipcMain.handle('desktop:tasks:upsert', (_event, payload) => upsertTask(payload || {}))
  ipcMain.handle('desktop:settings:update', (_event, payload) => updateDesktopSettings(payload || {}))
  ipcMain.handle('desktop:artifacts:list', (_event, payload) => listArtifacts(payload || {}))
  ipcMain.handle('desktop:artifacts:add', (_event, payload) => addArtifact(payload || {}))
  ipcMain.handle('desktop:openPath', (_event, targetPath) => shell.openPath(String(targetPath || '')))
}

function statusPayload() {
  const desktop = readDesktopConfig()
  const provider = readProviderConfig()
  return {
    appRoot,
    localRoot,
    providerConfigPath,
    desktopConfigPath,
    activeProvider: provider.activeProvider || '',
    providerCount: Object.keys(provider.providers || {}).length,
    activeProject: desktop.activeProject || '',
    projectCount: (desktop.projects || []).length,
  }
}

async function chooseProject() {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Add DreamSeed Project',
    properties: ['openDirectory'],
  })
  if (result.canceled || !result.filePaths[0]) return null
  const projectPath = result.filePaths[0]
  return saveProject({
    name: path.basename(projectPath),
    path: projectPath,
    mode: 'work',
    activate: true,
  })
}

function readDesktopConfig() {
  if (!existsSync(desktopConfigPath)) return defaultDesktopConfig()
  const data = JSON.parse(readFileSync(desktopConfigPath, 'utf8'))
  if (!Array.isArray(data.projects)) data.projects = []
  if (!Array.isArray(data.threads)) data.threads = []
  if (!Array.isArray(data.artifacts)) data.artifacts = []
  if (!Array.isArray(data.tasks)) data.tasks = []
  if (!data.settings || typeof data.settings !== 'object') data.settings = {}
  return data
}

function defaultDesktopConfig() {
  return {
    activeProject: '',
    activeThread: '',
    projects: [],
    threads: [],
    tasks: [],
    artifacts: [],
    settings: { maxConcurrentTasks: 2 },
  }
}

function writeDesktopConfig(config) {
  mkdirSync(path.dirname(desktopConfigPath), { recursive: true })
  writeFileSync(desktopConfigPath, JSON.stringify(config, null, 2) + '\n', 'utf8')
}

function saveProject(body) {
  const config = readDesktopConfig()
  const projectPath = path.resolve(String(body.path || ''))
  if (!existsSync(projectPath)) throw badRequest('project path must exist')
  const id = sanitizeId(body.id || body.name || path.basename(projectPath))
  const project = {
    id,
    name: String(body.name || path.basename(projectPath) || id).trim(),
    path: projectPath,
    mode: normalizeMode(body.mode || 'work'),
    notes: String(body.notes || '').slice(0, 500),
  }
  config.projects = (config.projects || []).filter(item => item.id !== id)
  config.projects.unshift(project)
  if (body.activate !== false || !config.activeProject) config.activeProject = id
  writeDesktopConfig(config)
  return project
}

function deleteProject(id) {
  const config = readDesktopConfig()
  config.projects = (config.projects || []).filter(item => item.id !== id)
  if (config.activeProject === id) config.activeProject = config.projects[0]?.id || ''
  writeDesktopConfig(config)
  return { ok: true }
}

function setActiveProject(id) {
  const config = readDesktopConfig()
  if (!config.projects?.some(item => item.id === id)) throw badRequest(`project '${id}' was not found`)
  config.activeProject = id
  writeDesktopConfig(config)
  return { ok: true }
}

function publicProviderConfig() {
  const config = readProviderConfig()
  return {
    configPath: providerConfigPath,
    activeProvider: config.activeProvider || '',
    providers: Object.entries(config.providers || {}).map(([name, provider]) => publicProvider(name, provider)),
  }
}

function publicProvider(name, provider) {
  return {
    name,
    type: provider.type || 'openai-chat',
    baseUrl: redactUrl(provider.baseUrl || ''),
    model: provider.model || '',
    chatCompletionsPath: provider.chatCompletionsPath || '/v1/chat/completions',
    timeoutMs: provider.timeoutMs || 120000,
    systemPrefix: provider.systemPrefix || '',
    modality: provider.modality || provider.capability || 'text',
    apiKeyEnv: provider.apiKeyEnv || '',
    hasApiKey: Boolean(provider.apiKey),
    auth: provider.apiKey ? 'stored key' : provider.apiKeyEnv ? `env ${provider.apiKeyEnv}` : 'missing',
    agentCapable: provider.agentCapable !== false,
    toolSupport: provider.toolSupport || 'unknown',
  }
}

function saveProvider(body) {
  const config = readProviderConfig()
  const originalName = sanitizeId(body.originalName || '')
  const name = sanitizeId(body.name || '')
  if (!name) throw badRequest('provider name is required')
  const existing = config.providers?.[originalName] || config.providers?.[name] || {}
  const provider = providerFromBody(body, existing)
  config.providers = config.providers || {}
  if (originalName && originalName !== name) delete config.providers[originalName]
  config.providers[name] = provider
  if (body.activate || !config.activeProvider) config.activeProvider = name
  if (originalName && config.activeProvider === originalName) config.activeProvider = name
  writeProviderConfig(config)
  return publicProvider(name, provider)
}

function deleteProvider(name) {
  const config = readProviderConfig()
  if (!config.providers?.[name]) throw badRequest(`provider '${name}' was not found`)
  delete config.providers[name]
  if (config.activeProvider === name) config.activeProvider = Object.keys(config.providers || {})[0] || ''
  writeProviderConfig(config)
  return { ok: true }
}

function setActiveProvider(name) {
  const config = readProviderConfig()
  if (!config.providers?.[name]) throw badRequest(`provider '${name}' was not found`)
  config.activeProvider = name
  writeProviderConfig(config)
  return { ok: true }
}

function providerFromBody(body, existing = {}) {
  const baseUrl = normalizeProviderBaseUrl(body.baseUrl || existing.baseUrl)
  const model = String(body.model || existing.model || '').trim()
  if (!model) throw badRequest('model is required')
  const timeoutMs = Number(body.timeoutMs || existing.timeoutMs || 120000)
  if (!Number.isFinite(timeoutMs) || timeoutMs < 1000) throw badRequest('timeout must be at least 1000 ms')
  const provider = {
    type: String(body.type || existing.type || 'openai-chat'),
    baseUrl,
    model,
    chatCompletionsPath: String(body.chatCompletionsPath || existing.chatCompletionsPath || '/v1/chat/completions'),
    systemPrefix: String(body.systemPrefix ?? existing.systemPrefix ?? defaultProviderSystemPrefix(body.name || '', model)),
    timeoutMs,
    agentCapable: body.agentCapable === undefined ? existing.agentCapable !== false : Boolean(body.agentCapable),
    toolSupport: String(body.toolSupport || existing.toolSupport || 'unknown'),
  }
  if (body.apiKeyEnv) provider.apiKeyEnv = String(body.apiKeyEnv).trim()
  if (body.apiKey) provider.apiKey = String(body.apiKey)
  else if (existing.apiKey) provider.apiKey = existing.apiKey
  else if (!provider.apiKeyEnv && existing.apiKeyEnv) provider.apiKeyEnv = existing.apiKeyEnv
  if (!provider.apiKey && !provider.apiKeyEnv) throw badRequest('api key or api key env is required')
  return provider
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

function readProviderConfig() {
  if (!existsSync(providerConfigPath)) return { activeProvider: '', providers: {} }
  const data = JSON.parse(readFileSync(providerConfigPath, 'utf8'))
  if (!data.providers || typeof data.providers !== 'object') data.providers = {}
  return data
}

function writeProviderConfig(config) {
  mkdirSync(path.dirname(providerConfigPath), { recursive: true })
  writeFileSync(providerConfigPath, JSON.stringify(config, null, 2) + '\n', 'utf8')
}

function runTask(payload, sender) {
  const projectPath = selectedProjectPath(payload.projectId)
  const mode = normalizeMode(payload.mode || 'work')
  const prompt = String(payload.prompt || '').trim()
  const taskId = sanitizeId(payload.runId || payload.taskId || '')
  if (!prompt) throw badRequest('task prompt is required')
  const modePrompt = {
    work: prompt,
    plan: `Plan mode. Analyze first, produce a concrete implementation plan, and do not modify files unless the user approves.\n\n${prompt}`,
    review: `Review mode. Prioritize bugs, regressions, risks, and missing tests. Findings first.\n\n${prompt}`,
    debug: `Debug mode. Reproduce or isolate the issue, identify likely causes, and verify the fix path.\n\n${prompt}`,
    release: `Release mode. Check audit, smoke, package, private-data exclusions, and publish readiness.\n\n${prompt}`,
  }[mode]
  return runDreamSeed(['--print', '--output-format', 'text', '--max-turns', '1', modePrompt], projectPath, 180000, {
    taskId,
    onOutput: chunk => sendTaskOutput(sender, taskId, chunk),
  })
}

function sendTaskOutput(sender, taskId, chunk) {
  if (!sender || sender.isDestroyed?.() || !taskId || !chunk) return
  sender.send('task:output', {
    taskId,
    chunk: String(chunk).slice(0, 16000),
    at: new Date().toISOString(),
  })
}

function cancelRunningTask(payload) {
  const taskId = sanitizeId(payload.runId || payload.taskId || '')
  if (!taskId) throw badRequest('task id is required')
  const record = runningTaskProcesses.get(taskId)
  if (!record) return { ok: false, cancelled: false, message: 'task is not running' }
  record.cancelled = true
  terminateChildProcess(record.child)
  return { ok: true, cancelled: true }
}

function runDoctor(name) {
  const allowed = new Map([
    ['context', ['doctor', 'context']],
    ['kernel', ['doctor', 'kernel']],
    ['mcp', ['doctor', 'mcp']],
    ['hooks', ['doctor', 'hooks']],
    ['provider', ['provider', 'health']],
    ['memory', ['memory', 'audit']],
    ['evolve', ['evolve', 'status']],
  ])
  return runDreamSeed(allowed.get(name) || allowed.get('context'), activeProjectPath(), 60000)
}

function historyStatus() {
  return runDreamSeedJson(['history', 'status'], activeProjectPath(), 45000)
}

function listHistorySessions(payload) {
  const args = ['history', 'list-sessions', '--limit', String(clampInt(payload.limit, 1, 500, 40))]
  const query = String(payload.query || '').trim()
  const project = String(payload.project || '').trim()
  if (project) args.push('--project', project)
  if (query) args.push('--query', query)
  return runDreamSeedJson(args, activeProjectPath(), 60000)
}

function searchHistory(payload) {
  const query = String(payload.query || '').trim()
  if (!query) return { ok: true, query: '', count: 0, results: [] }
  return runDreamSeedJson(['history', 'search', query, '--limit', String(clampInt(payload.limit, 1, 200, 30))], activeProjectPath(), 60000)
}

function showHistorySession(payload) {
  const target = String(payload.target || '').trim()
  if (!target) throw badRequest('history session id is required')
  return runDreamSeedJson([
    'history',
    'show-session',
    target,
    '--tail',
    String(clampInt(payload.tail, 1, 120, 30)),
    '--max-chars',
    String(clampInt(payload.maxChars, 1000, 30000, 12000)),
  ], activeProjectPath(), 60000)
}

function workspaceChanges(payload) {
  return runProcess('git', ['status', '--short'], selectedProjectPath(payload.projectId), 20000)
    .then(output => ({ ok: true, output: output || '' }))
    .catch(error => ({ ok: false, output: String(error.message || error) }))
}

async function workspaceDiff(payload) {
  const cwd = selectedProjectPath(payload.projectId)
  const mode = String(payload.mode || 'diff')
  const args = mode === 'status'
    ? ['status', '--short']
    : mode === 'stat'
    ? ['diff', '--stat']
    : mode === 'cached'
      ? ['diff', '--cached', '--no-ext-diff', '--']
      : ['diff', '--no-ext-diff', '--']
  try {
    const [status, diff] = await Promise.all([
      runProcess('git', ['status', '--short'], cwd, 20000).catch(error => String(error.message || error)),
      runProcess('git', args, cwd, 45000).catch(error => String(error.message || error)),
    ])
    return {
      ok: true,
      mode,
      status: status || '',
      output: diff || '',
      files: parseGitStatus(status || ''),
    }
  } catch (error) {
    return { ok: false, mode, status: '', output: String(error.message || error), files: [] }
  }
}

async function terminalCheck(payload) {
  const command = String(payload.command || '').trim()
  if (!command) throw badRequest('terminal command is required')
  return checkApproval(command, selectedProjectPath(payload.projectId))
}

async function terminalRun(payload) {
  const command = String(payload.command || '').trim()
  if (!command) throw badRequest('terminal command is required')
  const cwd = selectedProjectPath(payload.projectId)
  const approval = await checkApproval(command, cwd)
  if (approval.decision === 'deny') {
    return { ok: false, blocked: true, approval, output: approval.reasons?.join('\n') || 'Command denied by approval gate.' }
  }
  if (approval.decision !== 'allow' && payload.approved !== true) {
    return { ok: false, needsApproval: true, approval, output: approval.reasons?.join('\n') || 'Approval required.' }
  }
  const output = await runShellCommand(command, cwd, clampInt(payload.timeoutMs, 1000, 180000, 90000))
  return { ok: true, approval, output }
}

async function checkApproval(command, cwd) {
  const output = await runDreamSeed(['approval', 'check', '--tool', 'Bash', '--command', command, '--path', cwd, '--json'], cwd, 30000)
  const result = parseJsonFromOutput(output)
  return {
    ok: result.ok !== false,
    risk: result.risk || 'medium',
    decision: result.decision || 'ask',
    tags: result.tags || [],
    reasons: result.reasons || [],
    commandPreview: result.commandPreview || redactCommand(command),
  }
}

function runShellCommand(command, cwd, timeoutMs) {
  return runProcess('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', command], cwd, timeoutMs)
}

function parseGitStatus(text) {
  return String(text || '')
    .split(/\r?\n/)
    .map(line => line.trimEnd())
    .filter(Boolean)
    .map(line => ({
      status: line.slice(0, 2).trim() || '??',
      path: line.slice(3).trim() || line.trim(),
    }))
}

function listThreads() {
  const config = readDesktopConfig()
  return {
    activeThread: config.activeThread || '',
    threads: (config.threads || []).slice(0, 80),
  }
}

function createThread(payload) {
  const config = readDesktopConfig()
  const now = new Date().toISOString()
  const projectId = String(payload.projectId || config.activeProject || '')
  const projectPath = selectedProjectPath(projectId)
  const title = summarizeText(payload.title || payload.prompt || 'New task thread', 80)
  const thread = {
    id: randomUUID(),
    title,
    projectId,
    projectPath,
    mode: normalizeMode(payload.mode || 'work'),
    status: String(payload.status || 'open'),
    prompt: String(payload.prompt || ''),
    summary: summarizeText(payload.summary || payload.prompt || '', 220),
    historySessionId: '',
    historySessionFile: '',
    createdAt: now,
    updatedAt: now,
  }
  const persisted = writeDesktopHistorySession(thread, { phase: 'create' })
  thread.historySessionId = persisted.sessionId
  thread.historySessionFile = persisted.sessionFile
  config.threads = [thread, ...(config.threads || [])].slice(0, 80)
  config.activeThread = thread.id
  writeDesktopConfig(config)
  return thread
}

function updateThread(payload) {
  const config = readDesktopConfig()
  const id = String(payload.id || '')
  const thread = (config.threads || []).find(item => item.id === id)
  if (!thread) throw badRequest(`thread '${id}' was not found`)
  if (payload.title !== undefined) thread.title = summarizeText(payload.title, 80)
  if (payload.prompt !== undefined) thread.prompt = String(payload.prompt || '')
  if (payload.summary !== undefined) thread.summary = summarizeText(payload.summary, 220)
  if (payload.output !== undefined) thread.outputPreview = summarizeText(payload.output, 1200)
  if (payload.status !== undefined) thread.status = String(payload.status || 'open').slice(0, 40)
  if (payload.mode !== undefined) thread.mode = normalizeMode(payload.mode)
  thread.updatedAt = new Date().toISOString()
  const persisted = writeDesktopHistorySession(thread, {
    phase: thread.status === 'failed' ? 'failed' : 'update',
    output: payload.output,
  })
  thread.historySessionId = persisted.sessionId
  thread.historySessionFile = persisted.sessionFile
  config.activeThread = thread.id
  writeDesktopConfig(config)
  return thread
}

function writeDesktopHistorySession(thread, options = {}) {
  return persistDesktopHistorySession(thread, {
    ...options,
    appRoot,
    localRoot,
    defaultProjectPath: selectedProjectPath(thread.projectId),
    historySessionsDir: desktopHistorySessionsDir,
  })
}

function selectThread(id) {
  const config = readDesktopConfig()
  const thread = (config.threads || []).find(item => item.id === id)
  if (!thread) throw badRequest(`thread '${id}' was not found`)
  config.activeThread = thread.id
  writeDesktopConfig(config)
  return thread
}

function listTasks() {
  const config = readDesktopConfig()
  const tasks = (config.tasks || [])
    .map(task => normalizePersistedTask(task))
    .filter(Boolean)
    .slice(0, 120)
  return {
    tasks,
    settings: {
      maxConcurrentTasks: clampInt(config.settings?.maxConcurrentTasks, 1, 6, 2),
    },
  }
}

function upsertTask(payload) {
  const config = readDesktopConfig()
  const task = normalizePersistedTask(payload)
  if (!task?.id) throw badRequest('task id is required')
  const tasks = (config.tasks || []).filter(item => item.id !== task.id)
  config.tasks = [task, ...tasks].slice(0, 120)
  writeDesktopConfig(config)
  return { ok: true, task }
}

function updateDesktopSettings(payload) {
  const config = readDesktopConfig()
  config.settings = config.settings || {}
  if (payload.maxConcurrentTasks !== undefined) {
    config.settings.maxConcurrentTasks = clampInt(payload.maxConcurrentTasks, 1, 6, 2)
  }
  writeDesktopConfig(config)
  return {
    ok: true,
    settings: {
      maxConcurrentTasks: clampInt(config.settings.maxConcurrentTasks, 1, 6, 2),
    },
  }
}

function normalizePersistedTask(task) {
  if (!task || typeof task !== 'object') return null
  const status = ['queued', 'running', 'done', 'failed', 'cancelled', 'cancelling'].includes(task.status)
    ? task.status
    : 'queued'
  return {
    id: sanitizeId(task.id || ''),
    threadId: sanitizeId(task.threadId || ''),
    title: summarizeText(task.title || task.prompt || 'Task', 120),
    prompt: clipText(task.prompt || '', 12000),
    output: clipText(task.output || '', 24000),
    status,
    mode: normalizeMode(task.mode || 'work'),
    projectId: sanitizeId(task.projectId || ''),
    projectName: summarizeText(task.projectName || '', 120),
    createdAt: normalizeIso(task.createdAt) || new Date().toISOString(),
    startedAt: normalizeIso(task.startedAt) || '',
    finishedAt: normalizeIso(task.finishedAt) || '',
    updatedAt: normalizeIso(task.updatedAt) || new Date().toISOString(),
  }
}

function listArtifacts(payload) {
  const config = readDesktopConfig()
  const projectId = String(payload.projectId || config.activeProject || '')
  const artifacts = (config.artifacts || [])
    .filter(item => !projectId || !item.projectId || item.projectId === projectId)
    .slice(0, clampInt(payload.limit, 1, 120, 50))
  return { artifacts }
}

function addArtifact(payload) {
  const config = readDesktopConfig()
  const now = new Date().toISOString()
  const artifact = {
    id: `artifact-${Date.now().toString(36)}`,
    type: summarizeText(payload.type || 'event', 40),
    title: summarizeText(payload.title || 'Desktop event', 100),
    summary: summarizeText(payload.summary || '', 360),
    projectId: String(payload.projectId || config.activeProject || ''),
    threadId: String(payload.threadId || config.activeThread || ''),
    path: summarizeText(payload.path || '', 260),
    createdAt: now,
  }
  config.artifacts = [artifact, ...(config.artifacts || [])].slice(0, 160)
  writeDesktopConfig(config)
  return artifact
}

function runDreamSeed(args, cwd, timeoutMs, options = {}) {
  if (existsSync(dreamSeedAgent)) {
    return runProcess(nodeCommand, [dreamSeedAgent, ...args], cwd, timeoutMs, { ...options, maxOutputChars: outputLimitForDreamSeed(args) })
  }
  return runProcess('dreamseed', args, cwd, timeoutMs, { ...options, maxOutputChars: outputLimitForDreamSeed(args) })
}

async function runDreamSeedJson(args, cwd, timeoutMs) {
  const text = await runDreamSeed(args, cwd, timeoutMs)
  return parseJsonFromOutput(text)
}

function outputLimitForDreamSeed(args) {
  const joined = (args || []).join(' ')
  if (/^history\s+list-sessions\b/.test(joined)) return 5_000_000
  if (/^history\s+search\b/.test(joined)) return 700_000
  if (/^history\s+show-session\b/.test(joined)) return 160_000
  if (/--json\b/.test(joined) || /^doctor\b|^memory\s+audit\b|^evolve\s+status\b|^provider\b/.test(joined)) return 240_000
  return 24_000
}

function parseJsonFromOutput(text) {
  const raw = String(text || '').trim()
  const parsed = extractFirstJsonValue(raw)
  if (!parsed) {
    throw badRequest(`DreamSeed command did not return JSON\n${raw.slice(-2000)}`)
  }
  return parsed
}

function extractFirstJsonValue(raw) {
  for (let start = 0; start < raw.length; start += 1) {
    const opener = raw[start]
    if (opener !== '{' && opener !== '[') continue
    const stack = []
    let inString = false
    let escaped = false
    for (let index = start; index < raw.length; index += 1) {
      const char = raw[index]
      if (inString) {
        if (escaped) {
          escaped = false
        } else if (char === '\\') {
          escaped = true
        } else if (char === '"') {
          inString = false
        }
        continue
      }
      if (char === '"') {
        inString = true
      } else if (char === '{' || char === '[') {
        stack.push(char)
      } else if (char === '}' || char === ']') {
        const expected = char === '}' ? '{' : '['
        if (stack.at(-1) !== expected) break
        stack.pop()
        if (stack.length === 0) {
          try {
            return JSON.parse(raw.slice(start, index + 1))
          } catch {
            break
          }
        }
      }
    }
  }
  try {
    return JSON.parse(raw)
  } catch (error) {
    throw badRequest(`DreamSeed JSON parse failed: ${error.message}\n${raw.slice(-2000)}`)
  }
}

function runProcess(command, args, cwd, timeoutMs, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      env: dreamSeedEnv(),
    })
    const taskId = sanitizeId(options.taskId || '')
    if (taskId) {
      runningTaskProcesses.set(taskId, {
        child,
        cancelled: false,
        startedAt: new Date().toISOString(),
      })
    }
    let output = ''
    const timer = setTimeout(() => {
      if (taskId) {
        const record = runningTaskProcesses.get(taskId)
        if (record) record.timedOut = true
      }
      terminateChildProcess(child)
      reject(badRequest(`task timed out after ${timeoutMs} ms`))
    }, timeoutMs)
    child.stdout.on('data', chunk => {
      const text = chunk.toString()
      output += text
      options.onOutput?.(text)
    })
    child.stderr.on('data', chunk => {
      const text = chunk.toString()
      output += text
      options.onOutput?.(text)
    })
    child.on('error', error => {
      clearTimeout(timer)
      if (taskId) runningTaskProcesses.delete(taskId)
      reject(error)
    })
    child.on('close', code => {
      clearTimeout(timer)
      const record = taskId ? runningTaskProcesses.get(taskId) : null
      if (taskId) runningTaskProcesses.delete(taskId)
      const maxOutputChars = clampInt(options.maxOutputChars, 1000, 5_000_000, 24_000)
      const text = output.trim()
      const clipped = text.length > maxOutputChars ? text.slice(-maxOutputChars) : text
      if (record?.cancelled) {
        reject(badRequest(`task cancelled\n${clipped}`.trim()))
        return
      }
      if (code !== 0) reject(badRequest(`exit ${code}\n${clipped}`))
      else resolve(clipped)
    })
  })
}

function terminateChildProcess(child) {
  if (!child?.pid) return
  if (process.platform === 'win32') {
    spawn('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], {
      stdio: 'ignore',
      windowsHide: true,
    }).on('error', () => {
      try { child.kill() } catch {}
    })
    return
  }
  try {
    child.kill('SIGTERM')
  } catch {}
}

function dreamSeedEnv() {
  const localHome = path.join(localRoot, 'home')
  const pythonSite = process.env.DREAMSEED_PYTHON_SITE || path.join(appRoot, '.dreamseed-runtime', 'python-site')
  const mempalaceSrc = process.env.DREAMSEED_MEMPALACE_SRC || 'D:\\mempalace-evolve\\src'
  const pythonPath = prependEnvPath(process.env.PYTHONPATH || '', [pythonSite, mempalaceSrc])
  return {
    ...process.env,
    DREAMSEED_LOCAL_ROOT: localRoot,
    USERPROFILE: localHome,
    HOME: localHome,
    CLAUDE_CONFIG_DIR: path.join(localHome, '.claude'),
    DREAMSEED_HOME: localHome,
    DREAMSEED_APP_ROOT: appRoot,
    DREAMSEED_CONFIG_DIR: privateConfigDir,
    DREAMSEED_PROVIDER_CONFIG: providerConfigPath,
    DREAMSEED_PROVIDER_PORT: process.env.DREAMSEED_PROVIDER_PORT || '17891',
    DREAMSEED_MEMORY_DIR: process.env.DREAMSEED_MEMORY_DIR || path.join(localRoot, 'memory'),
    DREAMSEED_MEMORY_CANDIDATES_DIR: process.env.DREAMSEED_MEMORY_CANDIDATES_DIR || path.join(localRoot, 'memory-candidates'),
    DREAMSEED_COMPAT_KERNEL_JS: process.env.DREAMSEED_COMPAT_KERNEL_JS || path.join(localRoot, 'runtime', 'claude-cli.js'),
    DREAMSEED_PYTHON: process.env.DREAMSEED_PYTHON || 'D:\\Anaconda\\python.exe',
    DREAMSEED_PYTHON_SITE: pythonSite,
    DREAMSEED_MEMPALACE_SRC: mempalaceSrc,
    DREAMSEED_QUIET: '1',
    PYTHONIOENCODING: process.env.PYTHONIOENCODING || 'utf-8',
    PYTHONDONTWRITEBYTECODE: process.env.PYTHONDONTWRITEBYTECODE || '1',
    PYTHONPATH: pythonPath,
    DREAMSEED_OUTPUT_COMPRESS: process.env.DREAMSEED_OUTPUT_COMPRESS || 'auto',
    DREAMSEED_OUTPUT_COMPRESS_LIMIT: process.env.DREAMSEED_OUTPUT_COMPRESS_LIMIT || '12000',
    ENABLE_CLAUDE_CODE_SM_COMPACT: process.env.ENABLE_CLAUDE_CODE_SM_COMPACT || '1',
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: process.env.CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC || '1',
    DISABLE_AUTOUPDATER: process.env.DISABLE_AUTOUPDATER || '1',
    DISABLE_TELEMETRY: process.env.DISABLE_TELEMETRY || '1',
    CLAUDE_CODE_ENABLE_TELEMETRY: process.env.CLAUDE_CODE_ENABLE_TELEMETRY || '0',
    OTEL_METRICS_EXPORTER: process.env.OTEL_METRICS_EXPORTER || 'none',
    OTEL_LOGS_EXPORTER: process.env.OTEL_LOGS_EXPORTER || 'none',
    OTEL_TRACES_EXPORTER: process.env.OTEL_TRACES_EXPORTER || 'none',
    CLAUDE_CODE_OTEL_SHUTDOWN_TIMEOUT_MS: process.env.CLAUDE_CODE_OTEL_SHUTDOWN_TIMEOUT_MS || '250',
    CLAUDE_CODE_OTEL_FLUSH_TIMEOUT_MS: process.env.CLAUDE_CODE_OTEL_FLUSH_TIMEOUT_MS || '250',
  }
}

function prependEnvPath(current, candidates) {
  const parts = String(current || '').split(path.delimiter).filter(Boolean)
  for (const candidate of candidates.filter(Boolean).reverse()) {
    if (!existsSync(candidate)) continue
    const normalized = path.resolve(candidate).toLowerCase()
    if (!parts.some(part => path.resolve(part).toLowerCase() === normalized)) {
      parts.unshift(candidate)
    }
  }
  return parts.join(path.delimiter)
}

function resolveNodeCommand() {
  for (const candidate of [
    process.env.DREAMSEED_NODE,
    path.join(localRoot, 'node', 'node.exe'),
    path.join(appRoot, 'node', 'node.exe'),
    'D:\\clcude\\node\\node.exe',
  ]) {
    if (candidate && existsSync(candidate)) return candidate
  }
  return 'node'
}

function summarizeText(value, max) {
  return String(value || '').replace(/\s+/g, ' ').trim().slice(0, max)
}

function clipText(value, max) {
  const text = String(value || '').trim()
  return text.length > max ? text.slice(-max) : text
}

function normalizeIso(value) {
  const date = new Date(value || '')
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}

function redactCommand(command) {
  return String(command || '').replace(/sk-[A-Za-z0-9_-]{20,}|((api[_-]?key|token|secret|password)\s*[:=]\s*)['"]?[^'"\s]+/gi, '$1[redacted]').slice(0, 240)
}

function openDreamSeedTerminal(cwd, mode) {
  const command = existsSync(localBin) ? localBin : 'dreamseed'
  const title = `DreamSeed ${normalizeMode(mode)}`
  const ps = `Start-Process -FilePath cmd.exe -ArgumentList '/k','title ${title} && cd /d "${cwd}" && "${command}"'`
  spawn('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps], { detached: true, stdio: 'ignore', windowsHide: true }).unref()
  return { ok: true }
}

function activeProjectPath() {
  return selectedProjectPath(readDesktopConfig().activeProject)
}

function selectedProjectPath(id) {
  const config = readDesktopConfig()
  const project = (config.projects || []).find(item => item.id === id) || (config.projects || [])[0]
  return project?.path && existsSync(project.path) ? project.path : process.cwd()
}

function normalizeProviderBaseUrl(value) {
  const text = String(value || '').trim().replace(/\/+$/, '')
  if (!/^https?:\/\//i.test(text)) throw badRequest('base url must start with http:// or https://')
  return text
}

function sanitizeId(value) {
  return String(value || '').trim().replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80)
}

function normalizeMode(value) {
  return ['work', 'plan', 'review', 'debug', 'release'].includes(value) ? value : 'work'
}

function clampInt(value, min, max, fallback) {
  const number = Number.parseInt(value, 10)
  if (!Number.isFinite(number)) return fallback
  return Math.max(min, Math.min(max, number))
}

function redactUrl(value) {
  return String(value || '').replace(/([?&](?:key|token|api_key)=)[^&]+/gi, '$1redacted')
}

function badRequest(message) {
  const error = new Error(message)
  error.statusCode = 400
  return error
}
