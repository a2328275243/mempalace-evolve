#!/usr/bin/env node
import { app, BrowserWindow, ipcMain } from 'electron'
import { mkdirSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const root = path.resolve(path.dirname(__filename), '..')
const smokeUserData = path.join(tmpdir(), 'dreamseed-desktop-render-smoke')
let stubActiveProvider = 'glm'
let stubTaskCounter = 0
const stubThreads = []
const stubArtifacts = []
const stubProviders = [
  {
    name: 'glm',
    type: 'openai-chat',
    baseUrl: 'https://example.invalid',
    model: 'GLM-5.1',
    chatCompletionsPath: '/v1/chat/completions',
    timeoutMs: 120000,
    agentCapable: true,
    toolSupport: 'verified',
    auth: 'stored key',
  },
  {
    name: 'gemini-3.5-flash',
    type: 'openai-chat',
    baseUrl: 'https://example.invalid',
    model: 'gemini-3.5-flash',
    chatCompletionsPath: '/v1/chat/completions',
    timeoutMs: 120000,
    agentCapable: false,
    toolSupport: 'unknown',
    auth: 'stored key',
  },
  {
    name: 'deepseek-v4-flash',
    type: 'openai-chat',
    baseUrl: 'https://example.invalid',
    model: 'deepseek-v4-flash',
    chatCompletionsPath: '/v1/chat/completions',
    timeoutMs: 120000,
    agentCapable: false,
    toolSupport: 'unknown',
    auth: 'stored key',
  },
  {
    name: 'gpt-image-2',
    type: 'openai-chat',
    baseUrl: 'https://example.invalid',
    model: 'gpt-image-2',
    chatCompletionsPath: '/v1/chat/completions',
    timeoutMs: 120000,
    agentCapable: false,
    toolSupport: 'not supported',
    modality: 'image',
    auth: 'stored key',
  },
]

mkdirSync(path.join(smokeUserData, 'session'), { recursive: true })
app.disableHardwareAcceleration()
app.commandLine.appendSwitch('disable-gpu')
app.commandLine.appendSwitch('disable-gpu-compositing')
app.setPath('userData', smokeUserData)
app.setPath('sessionData', path.join(smokeUserData, 'session'))

registerStubIpc()

app.whenReady().then(async () => {
  const window = new BrowserWindow({
    show: false,
    width: 1360,
    height: 880,
    minWidth: 1080,
    minHeight: 720,
    paintWhenInitiallyHidden: true,
    webPreferences: {
      preload: path.join(root, 'desktop', 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      backgroundThrottling: false,
    },
  })

  const failures = []
  window.webContents.on('render-process-gone', (_event, details) => {
    failures.push(`renderer gone: ${JSON.stringify(details)}`)
  })
  window.webContents.on('console-message', (_event, level, message) => {
    if (level >= 3) failures.push(`renderer console error: ${message}`)
  })

  await window.loadFile(path.join(root, 'desktop', 'index.html'))
  await waitFor(600)
  await window.webContents.executeJavaScript(`
    document.querySelector('#openTerminalBtn')?.click()
    document.querySelector('#changesBtn')?.click()
    document.querySelector('.add-provider-pill')?.click()
    window.__dreamseedSmokeNewModelDraft = {
      open: document.body.classList.contains('drawer-open'),
      panelActive: document.querySelector('#panel-models')?.classList.contains('active') || false,
      originalName: document.querySelector('#modelForm')?.dataset.originalName || '',
      nameValue: document.querySelector('#modelNameInput')?.value || '',
      focused: document.activeElement?.id || '',
    }
    document.querySelector('#modelNameInput').value = 'desktop-smoke-new'
    document.querySelector('#modelIdInput').value = 'desktop-smoke-model'
    document.querySelector('#baseUrlInput').value = 'https://example.invalid'
    document.querySelector('#apiKeyEnvInput').value = 'DREAMSEED_SMOKE_KEY'
    document.querySelector('#saveModelBtn')?.click()
  `)
  await waitForCondition(window, `
    document.querySelector('#activeModelName')?.textContent === 'desktop-smoke-new' &&
    [...document.querySelectorAll('.model-item')].some(node => (node.textContent || '').includes('desktop-smoke-new'))
  `)
  await window.webContents.executeJavaScript(`
    document.querySelector('.add-provider-pill')?.click()
  `)
  await waitForCondition(window, `
    document.querySelector('#modelForm')?.dataset.originalName === '' &&
    document.querySelector('#modelNameInput')?.value === ''
  `)
  await window.webContents.executeJavaScript(`
    const submitTask = text => {
      const input = document.querySelector('#taskPrompt')
      input.value = text
      input.dispatchEvent(new Event('input', { bubbles: true }))
      document.querySelector('#composerForm')?.requestSubmit()
    }
    submitTask('Desktop task runner smoke A')
    submitTask('Desktop task runner smoke B')
  `)
  await waitForCondition(window, `
    document.querySelectorAll('.task-card.done').length >= 2
  `, 5000)
  const report = await window.webContents.executeJavaScript(`
    (() => {
      const pick = selector => {
        const node = document.querySelector(selector)
        if (!node) return { exists: false }
        const rect = node.getBoundingClientRect()
        return {
          exists: true,
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          overflowY: getComputedStyle(node).overflowY,
          text: (node.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 160),
        }
      }
      const groups = [...document.querySelectorAll('.history-project-group')]
      const buckets = [...document.querySelectorAll('.history-time-bucket')]
      const messages = [...document.querySelectorAll('.message')]
      return {
        title: document.title,
        bodyClass: document.body.className,
        appShell: pick('.app-shell'),
        sidebarScroll: pick('.sidebar-scroll'),
        historyList: pick('#historySessionList'),
        messageList: pick('#messageList'),
        composer: pick('.composer'),
        modelChip: pick('#modelStatusBtn'),
        workbench: pick('#workbenchSplit'),
        terminalSplit: pick('#terminalSplit'),
        reviewSplit: pick('#reviewSplit'),
        reviewDiff: pick('#reviewDiffOutput'),
        drawer: pick('#drawer'),
        projectGroups: groups.length,
        timeBuckets: buckets.length,
        conversationItems: document.querySelectorAll('.conversation-item').length,
        providerPills: document.querySelectorAll('.provider-pill').length,
        addProviderPill: document.querySelectorAll('.add-provider-pill').length,
        taskCards: document.querySelectorAll('.task-card').length,
        taskDone: document.querySelectorAll('.task-card.done').length,
        taskRunnerVisible: !document.querySelector('#taskRunnerPanel')?.hidden,
        taskConcurrency: document.querySelector('#taskConcurrencyInput')?.value || '',
        taskOutputs: [...document.querySelectorAll('.task-output')].map(node => node.textContent || '').join('\\n').slice(0, 300),
        artifactVisible: !document.querySelector('#artifactTimelinePanel')?.hidden,
        artifactItems: document.querySelectorAll('.artifact-item').length,
        reviewFiles: document.querySelectorAll('.review-file-item').length,
        diffLines: document.querySelectorAll('.diff-line').length,
        messages: messages.length,
        chatTitle: document.querySelector('#chatTitle')?.textContent || '',
        activeModel: document.querySelector('#activeModelName')?.textContent || '',
        newModelDraft: window.__dreamseedSmokeNewModelDraft || {},
        newModelDrawer: {
          open: document.body.classList.contains('drawer-open'),
          panelActive: document.querySelector('#panel-models')?.classList.contains('active') || false,
          originalName: document.querySelector('#modelForm')?.dataset.originalName || '',
          nameValue: document.querySelector('#modelNameInput')?.value || '',
          focused: document.activeElement?.id || '',
        },
        savedModelVisible: [...document.querySelectorAll('.model-item')].some(node => (node.textContent || '').includes('desktop-smoke-new')),
      }
    })()
  `)

  const required = [
    ['appShell', report.appShell.exists && report.appShell.width >= 1000 && report.appShell.height >= 700],
    ['sidebarScroll', report.sidebarScroll.exists && /auto|scroll/.test(report.sidebarScroll.overflowY)],
    ['historyList', report.historyList.exists && report.projectGroups >= 2 && report.conversationItems >= 4],
    ['messageList', report.messageList.exists && report.messages >= 1],
    ['composer', report.composer.exists && report.composer.height > 40],
    ['modelChip', report.modelChip.exists && report.activeModel === 'desktop-smoke-new'],
    ['providerPills', report.providerPills >= 4],
    ['addProviderPill', report.addProviderPill >= 1],
    ['newModelDraft', report.newModelDraft.open && report.newModelDraft.panelActive && report.newModelDraft.originalName === '' && report.newModelDraft.nameValue === ''],
    ['savedModelVisible', report.savedModelVisible && report.activeModel === 'desktop-smoke-new'],
    ['newModelDrawer', report.newModelDrawer.open && report.newModelDrawer.panelActive && report.newModelDrawer.originalName === '' && report.newModelDrawer.nameValue === ''],
    ['taskRunner', report.taskRunnerVisible && report.taskCards >= 2 && report.taskDone >= 2 && report.taskConcurrency === '2' && /Desktop task runner smoke/.test(report.taskOutputs)],
    ['artifacts', report.artifactVisible && report.artifactItems >= 2],
    ['workbench', report.workbench.exists && report.workbench.height >= 200],
    ['reviewSplit', report.reviewSplit.exists && report.reviewFiles >= 1 && report.diffLines >= 1],
    ['timeBuckets', report.timeBuckets >= 2],
  ]
  for (const [name, ok] of required) {
    if (!ok) failures.push(`render check failed: ${name}`)
  }

  await waitFor(300)
  const screenshotPath = await maybeWriteScreenshot(window)
  console.log(JSON.stringify({ ok: failures.length === 0, failures, report, screenshotPath }, null, 2))
  await window.destroy()
  app.exit(failures.length === 0 ? 0 : 1)
}).catch(error => {
  console.error(error.stack || error.message || String(error))
  app.exit(1)
})

function registerStubIpc() {
  ipcMain.handle('status:get', () => ({
    appRoot: root,
    localRoot: 'D:\\DreamSeed-Local-Agent',
    activeProvider: 'glm',
    providerCount: 4,
    activeProject: 'dreamseed',
    projectCount: 2,
  }))
  ipcMain.handle('project:list', () => ({
    activeProject: 'dreamseed',
    projects: [
      { id: 'dreamseed', name: 'DreamSeed', path: root, mode: 'work' },
      { id: 'research', name: 'Research Notes', path: 'D:\\Research', mode: 'plan' },
    ],
  }))
  ipcMain.handle('provider:list', () => ({
    activeProvider: stubActiveProvider,
    providers: stubProviders,
  }))
  ipcMain.handle('provider:save', (_event, payload) => {
    const provider = {
      name: String(payload.name || ''),
      type: 'openai-chat',
      baseUrl: String(payload.baseUrl || ''),
      model: String(payload.model || ''),
      chatCompletionsPath: String(payload.chatCompletionsPath || '/v1/chat/completions'),
      timeoutMs: Number(payload.timeoutMs || 120000),
      agentCapable: payload.agentCapable !== false,
      toolSupport: 'verified',
      auth: payload.apiKeyEnv ? `env ${payload.apiKeyEnv}` : 'stored key',
    }
    const index = stubProviders.findIndex(item => item.name === provider.name)
    if (index >= 0) stubProviders[index] = provider
    else stubProviders.unshift(provider)
    stubActiveProvider = provider.name
    return provider
  })
  ipcMain.handle('provider:diagnose', () => 'DreamSeed provider diagnose\n  ok glm: model=GLM-5.1 grade=tools-verified adapter=glm-agent-tools')
  ipcMain.handle('desktop:tasks:list', () => ({ tasks: [], settings: { maxConcurrentTasks: 2 } }))
  ipcMain.handle('desktop:tasks:upsert', (_event, payload) => ({ ok: true, task: payload }))
  ipcMain.handle('desktop:settings:update', (_event, payload) => ({ ok: true, settings: { maxConcurrentTasks: payload.maxConcurrentTasks || 2 } }))
  ipcMain.handle('task:run', async (event, payload) => {
    const runNumber = ++stubTaskCounter
    event.sender.send('task:output', {
      taskId: payload.runId,
      chunk: `stream ${runNumber}: ${payload.prompt || ''}\n`,
      at: new Date().toISOString(),
    })
    await waitFor(160)
    return `Desktop task runner smoke output ${runNumber}: ${payload.prompt || ''}`
  })
  ipcMain.handle('task:cancel', () => ({ ok: true, cancelled: true }))
  ipcMain.handle('desktop:threads:list', () => ({ activeThread: stubThreads[0]?.id || '', threads: stubThreads }))
  ipcMain.handle('desktop:threads:create', (_event, payload) => {
    const thread = {
      id: `desktop-smoke-thread-${stubThreads.length + 1}`,
      title: payload.title || payload.prompt || 'Desktop smoke task',
      projectId: payload.projectId || 'dreamseed',
      projectPath: root,
      mode: payload.mode || 'work',
      status: payload.status || 'queued',
      prompt: payload.prompt || '',
      summary: payload.summary || '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    stubThreads.unshift(thread)
    return thread
  })
  ipcMain.handle('desktop:threads:update', (_event, payload) => {
    const thread = stubThreads.find(item => item.id === payload.id)
    if (!thread) throw new Error(`thread not found: ${payload.id}`)
    Object.assign(thread, payload, { updatedAt: new Date().toISOString() })
    return thread
  })
  ipcMain.handle('desktop:artifacts:add', (_event, payload) => {
    const artifact = { id: `artifact-${stubArtifacts.length + 1}`, ...payload, createdAt: new Date().toISOString() }
    stubArtifacts.unshift(artifact)
    return artifact
  })
  ipcMain.handle('desktop:artifacts:list', () => ({ artifacts: stubArtifacts.slice(0, 30) }))
  ipcMain.handle('history:status', () => ({ status: 'imported', sessions: 8, records: 34, projects: 2 }))
  ipcMain.handle('history:list', () => ({
    ok: true,
    count: 8,
    total_matches: 8,
    sessions: [
      historySession(root, 'desktop-smoke-1', 'Desktop project smoke history', 'DreamSeed desktop and terminal share history.', 6, 'dreamseed-desktop'),
      historySession(root, 'desktop-smoke-2', 'Provider manager smoke history', 'Model switching remains shared with terminal config.', 5, ''),
      historySession(root, 'desktop-smoke-3', 'Approval gate smoke history', 'Risky terminal commands require approval.', 4, ''),
      historySession('D:\\Research', 'research-smoke-1', 'Research project planning', 'Project history groups remain scrollable.', 7, ''),
      historySession('D:\\Research', 'research-smoke-2', 'Memory candidate review', 'Low-value entries stay out of MemPalace.', 9, ''),
      historySession('D:\\Research', 'research-smoke-3', 'Output compression test', 'Long logs are summarized without hiding errors.', 3, ''),
    ],
  }))
  ipcMain.handle('workspace:diff', () => ({
    ok: true,
    mode: 'diff',
    status: ' M desktop/desktop.js\n M desktop/desktop.css',
    output: [
      'diff --git a/desktop/desktop.js b/desktop/desktop.js',
      '--- a/desktop/desktop.js',
      '+++ b/desktop/desktop.js',
      '@@ -1,3 +1,4 @@',
      '-const oldPanel = "drawer"',
      '+const newPanel = "workbench"',
      '+const reviewMode = true',
    ].join('\n'),
    files: [
      { status: 'M', path: 'desktop/desktop.js' },
      { status: 'M', path: 'desktop/desktop.css' },
    ],
  }))
}

function historySession(project, sessionId, preview, summary, count, sourceKind) {
  const now = new Date().toISOString()
  return {
    project,
    project_name: path.basename(project),
    session_id: sessionId,
    first_time: now,
    last_time: now,
    first_timestamp: Math.floor(Date.now() / 1000),
    last_timestamp: Math.floor(Date.now() / 1000),
    entry_count: count,
    title: preview,
    preview,
    user_preview: preview,
    assistant_summary: summary,
    summary_kind: sourceKind ? 'assistant' : 'local',
    source_kind: sourceKind,
  }
}

function waitFor(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function waitForCondition(window, expression, timeoutMs = 3000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    const ok = await window.webContents.executeJavaScript(`Boolean(${expression})`)
    if (ok) return
    await waitFor(80)
  }
  throw new Error(`timed out waiting for render condition: ${expression.replace(/\s+/g, ' ').trim()}`)
}

async function maybeWriteScreenshot(window) {
  const target = process.env.DREAMSEED_DESKTOP_RENDER_SCREENSHOT || ''
  if (!target) return ''
  const out = path.resolve(target)
  mkdirSync(path.dirname(out), { recursive: true })
  if (!window.isVisible()) {
    window.showInactive()
    await waitFor(350)
  }
  await window.webContents.executeJavaScript('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
  const image = await window.webContents.capturePage()
  writeFileSync(out, image.toPNG())
  return out
}
