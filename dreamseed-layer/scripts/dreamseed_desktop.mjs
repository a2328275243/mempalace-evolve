#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const root = path.resolve(__dirname, '..')
const main = path.join(root, 'desktop', 'electron-main.mjs')
const renderSmoke = path.join(root, 'scripts', 'desktop_render_smoke.mjs')

if (process.argv.includes('--smoke')) {
  const requiredFiles = [
    main,
    path.join(root, 'desktop', 'shared-history.mjs'),
    path.join(root, 'desktop', 'preload.cjs'),
    path.join(root, 'desktop', 'index.html'),
    path.join(root, 'desktop', 'desktop.css'),
    path.join(root, 'desktop', 'desktop.js'),
  ]
  for (const required of requiredFiles) {
    if (!existsSync(required)) {
      console.error(`[dreamseed] desktop smoke failed, missing: ${required}`)
      process.exit(1)
    }
  }
  try {
    verifyDesktopWiring()
  } catch (error) {
    console.error(`[dreamseed] desktop smoke failed: ${error.message}`)
    process.exit(1)
  }
  const electronCommand = resolveElectronCommand()
  if (!electronCommand) {
    console.error('[dreamseed] desktop smoke failed, Electron is unavailable')
    process.exit(1)
  }
  const history = await verifyHistoryBackend()
  console.log(JSON.stringify({ ok: true, desktop: 'DreamSeed Desktop', electron: electronCommand.command, history }))
  process.exit(0)
}

const electronCommand = resolveElectronCommand()
if (!electronCommand) {
  console.error('[dreamseed] Electron is not installed for the desktop app.')
  console.error('[dreamseed] Run: npm install')
  process.exit(1)
}

const renderSmokeMode = process.argv.includes('--render-smoke')
const entrypoint = renderSmokeMode ? renderSmoke : main
const passthroughArgs = process.argv.slice(2).filter(arg => arg !== '--render-smoke')

const child = spawn(electronCommand.command, [...electronCommand.args, entrypoint, ...passthroughArgs], {
  cwd: root,
  stdio: 'inherit',
  shell: electronCommand.shell || false,
  env: {
    ...process.env,
    DREAMSEED_APP_ROOT: root,
    DREAMSEED_NODE: process.execPath,
  },
})

child.on('exit', code => process.exit(code ?? 0))
child.on('error', error => {
  console.error(`[dreamseed] failed to launch desktop: ${error.message}`)
  process.exit(1)
})

function resolveElectronCommand() {
  const realExe = path.join(root, 'node_modules', 'electron', 'dist', process.platform === 'win32' ? 'electron.exe' : 'electron')
  if (existsSync(realExe)) return { command: realExe, args: [] }
  const localCmd = path.join(root, 'node_modules', '.bin', process.platform === 'win32' ? 'electron.cmd' : 'electron')
  if (existsSync(localCmd)) return { command: localCmd, args: [], shell: process.platform === 'win32' }
  if (process.env.ELECTRON_BINARY && existsSync(process.env.ELECTRON_BINARY)) return { command: process.env.ELECTRON_BINARY, args: [] }
  const pathElectron = findCommandOnPath(process.platform === 'win32' ? ['electron.cmd', 'electron.exe'] : ['electron'])
  if (pathElectron) return { command: pathElectron, args: [], shell: process.platform === 'win32' && pathElectron.toLowerCase().endsWith('.cmd') }
  return null
}

function findCommandOnPath(candidates) {
  const pathEnv = process.env.PATH || ''
  for (const dir of pathEnv.split(path.delimiter)) {
    if (!dir) continue
    for (const candidate of candidates) {
      const full = path.join(dir, candidate)
      if (existsSync(full)) return full
    }
  }
  return null
}

function verifyDesktopWiring() {
  const mainText = readFileSync(main, 'utf8')
  const sharedHistoryText = readFileSync(path.join(root, 'desktop', 'shared-history.mjs'), 'utf8')
  const preloadText = readFileSync(path.join(root, 'desktop', 'preload.cjs'), 'utf8')
  const indexText = readFileSync(path.join(root, 'desktop', 'index.html'), 'utf8')
  const rendererText = readFileSync(path.join(root, 'desktop', 'desktop.js'), 'utf8')
  const requiredMain = [
    'history:status',
    'history:list',
    'history:search',
    'history:show',
    'provider:list',
    'provider:diagnose',
    'workspace:changes',
    'workspace:diff',
    'task:output',
    'terminal:check',
    'terminal:run',
    'task:cancel',
    'desktop:tasks:list',
    'desktop:tasks:upsert',
    'desktop:settings:update',
    'desktop:threads:list',
    'desktop:threads:create',
    'desktop:threads:update',
    'desktop:artifacts:list',
    'writeDesktopHistorySession',
    'persistDesktopHistorySession',
    './shared-history.mjs',
    'randomUUID',
    'outputLimitForDreamSeed',
    'extractFirstJsonValue',
    "stdio: ['ignore', 'pipe', 'pipe']",
  ]
  const requiredSharedHistory = [
    'writeDesktopHistorySession',
    'writeDesktopNativeResumeBridge',
    'dreamseed-desktop-resume-bridge',
    'nativeSanitizePath',
    'nativeResumePath',
    'source_kind',
    'desktop_thread_id',
  ]
  const requiredPreload = [
    'allowedInvokeChannels',
    'contextBridge',
    'ipcRenderer.invoke',
    'task:cancel',
    'provider:diagnose',
    'task:output',
  ]
  const requiredIndex = [
    'app-shell',
    'sidebar',
    'sidebar-scroll',
    'chat-shell',
    'messageList',
    'taskRunnerPanel',
    'taskQueueList',
    'taskRunnerTitle',
    'taskConcurrencyInput',
    'artifactTimelinePanel',
    'diagnoseModelBtn',
    'workbenchSplit',
    'terminalSplitForm',
    'terminalSplitOutput',
    'reviewSplit',
    'reviewFileList',
    'reviewDiffOutput',
    'historySessionList',
    'historySearchInput',
    'taskPrompt',
    'drawer',
    'panel-models',
    'panel-changes',
    'panel-terminal',
    'panel-health',
    'changedFileList',
    'terminalForm',
    'approvalModal',
    'modelStatusBtn',
    'activeModelName',
    'activeModelDetail',
    'sidebarActiveProject',
    'sidebarActiveModel',
    'providerQuickList',
    'modelCountLabel',
    'modelConfigLabel',
    'newModelBtn',
    'section-actions',
    'sidebar-nav',
    'nav-command',
    'active-context-card',
    'project-list-hidden',
  ]
  const requiredRenderer = [
    'refreshHistory',
    'renderHistory',
    'renderWorkbench',
    'toggleWorkbenchPanel',
    'openReviewWorkbench',
    'makeThreadTitle',
    'showHistorySession',
    'showProjectHome',
    'showProjectHistoryGroup',
    'renderHistoryConversation',
    'normalizeHistorySessions',
    'groupedHistorySessions',
    'bucketHistorySessions',
    'historyBucketKey',
    'compactProjectSessions',
    'historyCardHtml',
    'projectGroupCountLabel',
    'cleanProjectOpeningLine',
    'cleanSessionOpeningLine',
    'projectExcerptMessages',
    'projectHistoryOpeningLine',
    'bestProjectFocus',
    'summaryLabelForSession',
    'isUsefulHistorySession',
    'dedupeHistoryEntries',
    'roleForHistory',
    'providerCapabilityLabel',
    'messageList',
    'renderTaskRunner',
    'renderArtifactsTimeline',
    'pumpTaskQueue',
    'runQueuedTask',
    'cancelTask',
    'handleTaskOutput',
    'persistTask',
    'updateTaskConcurrency',
    'diagnoseProviders',
    'MAX_CONCURRENT_DESKTOP_TASKS',
    'provider:list',
    'renderProviderQuickList',
    'appendAddProviderPill',
    'switchProviderQuick',
    'startNewModel',
    'sortedProviders',
    'refreshChanges',
    'renderDiffReview',
    'diffOutputHtml',
    'appendTerminalLog',
    'runTerminalCommand',
    'renderApprovalModal',
    'summarizeError',
    'openDrawer',
    'setMode',
  ]
  for (const token of requiredMain) {
    if (!mainText.includes(token)) throw new Error(`main process missing ${token}`)
  }
  for (const token of requiredSharedHistory) {
    if (!sharedHistoryText.includes(token)) throw new Error(`shared history missing ${token}`)
  }
  for (const token of requiredPreload) {
    if (!preloadText.includes(token)) throw new Error(`preload missing ${token}`)
  }
  for (const token of requiredIndex) {
    if (!indexText.includes(token)) throw new Error(`history UI missing ${token}`)
  }
  for (const token of requiredRenderer) {
    if (!rendererText.includes(token)) throw new Error(`renderer missing ${token}`)
  }
}

async function verifyHistoryBackend() {
  const script = path.join(root, 'scripts', 'import_claude_history.py')
  const manifest = path.join(root, 'legacy-history', 'claude-code', 'manifest.json')
  if (!existsSync(script) || !existsSync(manifest)) return { checked: false, reason: 'no imported legacy history' }
  const python = process.env.DREAMSEED_PYTHON || 'python'
  const status = await runJson(python, [script, 'status'])
  if (!status.ok || !status.sessions) throw new Error('history status did not report imported sessions')
  const longList = await runJson(python, [script, 'list-sessions', '--limit', '500'])
  if (!Array.isArray(longList.sessions) || longList.sessions.length < Math.min(10, status.sessions || 10)) {
    throw new Error('history list-sessions --limit 500 did not return a valid long session list')
  }
  const listed = await runJson(python, [script, 'list-sessions', '--limit', '1'])
  const session = listed.sessions?.[0]
  if (!session?.session_id) throw new Error('history list-sessions returned no session id')
  const searchNeedle = session.project || session.preview || session.session_id
  const searched = await runJson(python, [script, 'search', searchNeedle, '--limit', '3'])
  const searchSession = searched.results?.find(item => item.session_id === session.session_id) || searched.results?.[0]
  if (searchSession && !Number.isFinite(Number(searchSession.entry_count))) {
    throw new Error('history search result did not include entry_count metadata')
  }
  const shown = await runJson(python, [script, 'show-session', session.session_id, '--tail', '1', '--max-chars', '2000'])
  if (!shown.session?.session_id) throw new Error('history show-session returned no session metadata')
  return { checked: true, sessions: status.sessions, records: status.records, sampleProject: session.project || '' }
}

function runJson(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: root,
      shell: false,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: process.env.PYTHONIOENCODING || 'utf-8' },
    })
    let output = ''
    child.stdout.on('data', chunk => output += chunk.toString())
    child.stderr.on('data', chunk => output += chunk.toString())
    child.on('error', reject)
    child.on('close', code => {
      if (code !== 0) {
        reject(new Error(`history backend exited ${code}: ${output.trim().slice(-1200)}`))
        return
      }
      try {
        resolve(parseJsonFromOutput(output))
      } catch (error) {
        reject(error)
      }
    })
  })
}

function parseJsonFromOutput(text) {
  const raw = String(text || '').trim()
  const start = raw.indexOf('{')
  const end = raw.lastIndexOf('}')
  if (start === -1 || end === -1 || end <= start) {
    throw new Error(`expected JSON output, got: ${raw.slice(-500)}`)
  }
  return JSON.parse(raw.slice(start, end + 1))
}
