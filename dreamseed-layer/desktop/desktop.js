const api = window.dreamseed

const EN = {
  'app.desktopAgent': 'Desktop Agent',
  'section.recent': 'Project history',
  'section.projects': 'Workspaces',
  'section.projectThreads': 'Projects & chats',
  'context.current': 'Current',
  'settings.title': 'Settings',
  'action.newChat': 'New chat',
  'action.refresh': 'Refresh',
  'action.add': 'Add',
  'action.context': 'Context',
  'action.openTerminal': 'Terminal',
  'action.testModel': 'Test model',
  'action.diagnose': 'Diagnose',
  'action.newModel': 'New model',
  'action.addModel': 'Add model',
  'action.save': 'Save',
  'action.use': 'Use',
  'action.delete': 'Delete',
  'action.run': 'Run',
  'action.cancel': 'Cancel',
  'action.approve': 'Approve',
  'drawer.models': 'Models',
  'drawer.terminal': 'Terminal',
  'drawer.health': 'Health',
  'drawer.changes': 'Changes',
  'workbench.workspace': 'Workspace',
  'workbench.terminalTitle': 'Embedded terminal',
  'workbench.reviewTitle': 'Code review',
  'workbench.closed': 'Workbench closed',
  'review.changedFiles': 'changed files',
  'review.noDiff': 'No diff output',
  'mode.work': 'Work',
  'mode.plan': 'Plan',
  'mode.review': 'Review',
  'field.name': 'Name',
  'field.model': 'Model ID',
  'field.baseUrl': 'Base URL',
  'field.apiKey': 'API Key',
  'field.apiKeyEnv': 'API Key Env',
  'field.chatPath': 'Chat Path',
  'field.timeout': 'Timeout ms',
  'field.agentCapable': 'Allow tool calling',
  'doctor.context': 'Context',
  'doctor.contextSub': 'Prompt and compaction pressure',
  'doctor.kernel': 'Kernel',
  'doctor.kernelSub': 'Startup and compact state',
  'doctor.mcp': 'MCP',
  'doctor.mcpSub': 'Tool registry and risks',
  'doctor.hooks': 'Hooks',
  'doctor.hooksSub': 'Safety and memory pipeline',
  'doctor.memory': 'Memory',
  'doctor.memorySub': 'Candidate review status',
  'doctor.evolve': 'Evolve',
  'doctor.evolveSub': 'Proposal queue',
  'approval.kicker': 'Approval gate',
  'approval.title': 'Approval required',
  'approval.body': 'DreamSeed detected a command that needs approval before running.',
  'placeholder.search': 'Search chats',
  'placeholder.prompt': 'Ask DreamSeed to work in the active project...',
  'placeholder.terminal': 'Run a local command. Risky operations ask first.',
  'state.loading': 'Loading...',
  'state.ready': 'Ready',
  'state.none': 'None',
  'state.noHistory': 'No imported history found.',
  'state.noProjects': 'No projects yet.',
  'state.noModels': 'No models yet.',
  'state.noChanges': 'No changes detected.',
  'state.noOutput': 'No output',
  'state.running': 'Running',
  'message.welcomeTitle': 'Ready when you are',
  'message.welcomeBody': 'Pick a project or continue a thread. Desktop chats and terminal history share the same local archive.',
  'message.historyLoaded': 'History loaded',
  'message.historyFailed': 'History failed to load',
  'message.newChat': 'New chat started.',
  'message.taskEmpty': 'Task text is empty.',
  'message.taskRunning': 'DreamSeed is working...',
  'message.taskFailed': 'Task failed',
  'message.taskQueued': 'Task queued',
  'message.taskDone': 'Task completed',
  'message.taskCancelled': 'Task cancelled',
  'message.providerTesting': 'Testing active model...',
  'message.providerDiagnosing': 'Diagnosing configured models...',
  'message.providerSaved': 'Model saved',
  'message.providerDeleted': 'Model deleted',
  'message.projectAdded': 'Project added',
  'message.terminalOpened': 'DreamSeed terminal opened.',
  'message.terminalRunning': 'Command running...',
  'message.terminalBlocked': 'Command blocked by policy.',
  'message.needsApproval': 'This command needs approval.',
  'history.readOnly': 'Read-only legacy history',
  'history.entries': 'entries',
  'history.records': 'records',
  'history.sessions': 'sessions',
  'history.filtered': 'hidden',
  'history.localSummary': 'DreamSeed summary',
  'history.assistantSummary': 'Assistant summary',
  'history.noThreads': 'No chats',
  'history.projectBadge': 'History',
  'history.projectHome': 'Project',
  'history.desktopThread': 'Desktop',
  'history.excerpts': 'History excerpts',
  'model.toolsVerified': 'tools verified',
  'model.toolsUnknown': 'tools unknown',
  'model.toolsDisabled': 'tools off',
  'model.active': 'active',
  'model.addHint': 'Add model',
  'task.runner': 'Task Runner',
  'task.summary': '{running} running / {queued} queued',
  'task.concurrency': 'Concurrent',
  'task.statusQueued': 'queued',
  'task.statusRunning': 'running',
  'task.statusDone': 'done',
  'task.statusFailed': 'failed',
  'task.statusCancelled': 'cancelled',
  'task.cancel': 'Cancel',
  'artifact.timeline': 'Artifacts',
  'artifact.empty': 'No artifacts yet',
}

const ZH = {
  'app.desktopAgent': '\u684c\u9762\u667a\u80fd\u4f53',
  'section.recent': '\u9879\u76ee\u5386\u53f2',
  'section.projects': '\u5de5\u4f5c\u533a',
  'section.projectThreads': '\u9879\u76ee\u4e0e\u5bf9\u8bdd',
  'context.current': '\u5f53\u524d',
  'settings.title': '\u8bbe\u7f6e',
  'action.newChat': '\u65b0\u5bf9\u8bdd',
  'action.refresh': '\u5237\u65b0',
  'action.add': '\u6dfb\u52a0',
  'action.context': '\u4e0a\u4e0b\u6587',
  'action.openTerminal': '\u7ec8\u7aef',
  'action.testModel': '\u6d4b\u8bd5\u6a21\u578b',
  'action.diagnose': '\u8bca\u65ad',
  'action.newModel': '\u65b0\u6a21\u578b',
  'action.addModel': '\u6dfb\u52a0\u6a21\u578b',
  'action.save': '\u4fdd\u5b58',
  'action.use': '\u4f7f\u7528',
  'action.delete': '\u5220\u9664',
  'action.run': '\u8fd0\u884c',
  'action.cancel': '\u53d6\u6d88',
  'action.approve': '\u6279\u51c6',
  'drawer.models': '\u6a21\u578b',
  'drawer.terminal': '\u7ec8\u7aef',
  'drawer.health': '\u4f53\u68c0',
  'drawer.changes': '\u53d8\u66f4',
  'workbench.workspace': '\u5de5\u4f5c\u53f0',
  'workbench.terminalTitle': '\u5185\u5d4c\u7ec8\u7aef',
  'workbench.reviewTitle': '\u4ee3\u7801\u5ba1\u67e5',
  'workbench.closed': '\u5de5\u4f5c\u53f0\u5df2\u5173\u95ed',
  'review.changedFiles': '\u4e2a\u53d8\u66f4\u6587\u4ef6',
  'review.noDiff': '\u6ca1\u6709 diff \u8f93\u51fa',
  'mode.work': '\u5de5\u4f5c',
  'mode.plan': '\u8ba1\u5212',
  'mode.review': '\u5ba1\u67e5',
  'field.name': '\u540d\u79f0',
  'field.model': '\u6a21\u578b ID',
  'field.baseUrl': 'Base URL',
  'field.apiKey': 'API Key',
  'field.apiKeyEnv': 'API Key Env',
  'field.chatPath': 'Chat Path',
  'field.timeout': '\u8d85\u65f6 ms',
  'field.agentCapable': '\u5141\u8bb8\u5de5\u5177\u8c03\u7528',
  'doctor.context': '\u4e0a\u4e0b\u6587',
  'doctor.contextSub': '\u63d0\u793a\u548c\u538b\u7f29\u538b\u529b',
  'doctor.kernel': '\u5185\u6838',
  'doctor.kernelSub': '\u542f\u52a8\u548c\u538b\u7f29\u72b6\u6001',
  'doctor.mcp': 'MCP',
  'doctor.mcpSub': '\u5de5\u5177\u6ce8\u518c\u548c\u98ce\u9669',
  'doctor.hooks': 'Hooks',
  'doctor.hooksSub': '\u5b89\u5168\u548c\u8bb0\u5fc6\u94fe\u8def',
  'doctor.memory': '\u8bb0\u5fc6',
  'doctor.memorySub': '\u5019\u9009\u6c60\u5ba1\u6838\u72b6\u6001',
  'doctor.evolve': '\u81ea\u8fdb\u5316',
  'doctor.evolveSub': '\u63d0\u6848\u961f\u5217',
  'approval.kicker': '\u5ba1\u6279\u95e8\u7981',
  'approval.title': '\u9700\u8981\u5ba1\u6279',
  'approval.body': 'DreamSeed \u68c0\u6d4b\u5230\u8fd9\u4e2a\u547d\u4ee4\u9700\u8981\u4f60\u6279\u51c6\u540e\u624d\u80fd\u8fd0\u884c\u3002',
  'placeholder.search': '\u641c\u7d22\u5bf9\u8bdd',
  'placeholder.prompt': '\u8ba9 DreamSeed \u5728\u5f53\u524d\u9879\u76ee\u91cc\u5de5\u4f5c...',
  'placeholder.terminal': '\u8fd0\u884c\u672c\u5730\u547d\u4ee4\uff0c\u9ad8\u98ce\u9669\u64cd\u4f5c\u4f1a\u5148\u8be2\u95ee\u3002',
  'state.loading': '\u52a0\u8f7d\u4e2d...',
  'state.ready': '\u5c31\u7eea',
  'state.none': '\u65e0',
  'state.noHistory': '\u6ca1\u6709\u5bfc\u5165\u5386\u53f2\u3002',
  'state.noProjects': '\u8fd8\u6ca1\u6709\u9879\u76ee\u3002',
  'state.noModels': '\u8fd8\u6ca1\u6709\u6a21\u578b\u3002',
  'state.noChanges': '\u6ca1\u6709\u68c0\u6d4b\u5230\u53d8\u66f4\u3002',
  'state.noOutput': '\u6ca1\u6709\u8f93\u51fa',
  'state.running': '\u8fd0\u884c\u4e2d',
  'message.welcomeTitle': '\u968f\u65f6\u5f00\u59cb',
  'message.welcomeBody': '\u9009\u4e00\u4e2a\u9879\u76ee\u6216\u7ee7\u7eed\u4e00\u6bb5\u5bf9\u8bdd\u3002\u684c\u9762\u7aef\u548c\u7ec8\u7aef\u5171\u7528\u540c\u4e00\u5957\u672c\u5730\u5386\u53f2\u5f52\u6863\u3002',
  'message.historyLoaded': '\u5386\u53f2\u5df2\u52a0\u8f7d',
  'message.historyFailed': '\u5386\u53f2\u52a0\u8f7d\u5931\u8d25',
  'message.newChat': '\u5df2\u5f00\u59cb\u65b0\u5bf9\u8bdd\u3002',
  'message.taskEmpty': '\u4efb\u52a1\u5185\u5bb9\u4e3a\u7a7a\u3002',
  'message.taskRunning': 'DreamSeed \u6b63\u5728\u5de5\u4f5c...',
  'message.taskFailed': '\u4efb\u52a1\u5931\u8d25',
  'message.taskQueued': '\u4efb\u52a1\u5df2\u5165\u961f',
  'message.taskDone': '\u4efb\u52a1\u5df2\u5b8c\u6210',
  'message.taskCancelled': '\u4efb\u52a1\u5df2\u53d6\u6d88',
  'message.providerTesting': '\u6b63\u5728\u6d4b\u8bd5\u5f53\u524d\u6a21\u578b...',
  'message.providerDiagnosing': '\u6b63\u5728\u8bca\u65ad\u5df2\u914d\u7f6e\u6a21\u578b...',
  'message.providerSaved': '\u6a21\u578b\u5df2\u4fdd\u5b58',
  'message.providerDeleted': '\u6a21\u578b\u5df2\u5220\u9664',
  'message.projectAdded': '\u9879\u76ee\u5df2\u6dfb\u52a0',
  'message.terminalOpened': 'DreamSeed \u7ec8\u7aef\u5df2\u6253\u5f00\u3002',
  'message.terminalRunning': '\u547d\u4ee4\u8fd0\u884c\u4e2d...',
  'message.terminalBlocked': '\u547d\u4ee4\u5df2\u88ab\u7b56\u7565\u62e6\u622a\u3002',
  'message.needsApproval': '\u8fd9\u4e2a\u547d\u4ee4\u9700\u8981\u5ba1\u6279\u3002',
  'history.readOnly': '\u53ea\u8bfb\u65e7\u5386\u53f2',
  'history.entries': '\u6761',
  'history.records': '\u8bb0\u5f55',
  'history.sessions': '\u4f1a\u8bdd',
  'history.filtered': '\u5df2\u9690\u85cf',
  'history.localSummary': 'DreamSeed \u6458\u8981',
  'history.assistantSummary': '\u6a21\u578b\u6458\u8981',
  'history.noThreads': '\u6682\u65e0\u5bf9\u8bdd',
  'history.projectBadge': '\u5386\u53f2',
  'history.projectHome': '\u9879\u76ee',
  'history.desktopThread': '\u684c\u9762',
  'history.excerpts': '\u5386\u53f2\u6458\u5f55',
  'model.toolsVerified': '\u5de5\u5177\u5df2\u9a8c\u8bc1',
  'model.toolsUnknown': '\u5de5\u5177\u5f85\u9a8c\u8bc1',
  'model.toolsDisabled': '\u5de5\u5177\u5173\u95ed',
  'model.active': '\u5df2\u542f\u7528',
  'model.addHint': '\u6dfb\u52a0\u6a21\u578b',
  'task.runner': '\u4efb\u52a1\u961f\u5217',
  'task.summary': '{running} \u8fd0\u884c / {queued} \u6392\u961f',
  'task.concurrency': '\u5e76\u53d1',
  'task.statusQueued': '\u6392\u961f',
  'task.statusRunning': '\u8fd0\u884c',
  'task.statusDone': '\u5b8c\u6210',
  'task.statusFailed': '\u5931\u8d25',
  'task.statusCancelled': '\u5df2\u53d6\u6d88',
  'task.cancel': '\u53d6\u6d88',
  'artifact.timeline': '\u4ea7\u7269',
  'artifact.empty': '\u6682\u65e0\u4ea7\u7269',
}

const $ = selector => document.querySelector(selector)
const $$ = selector => [...document.querySelectorAll(selector)]

const HISTORY_LOAD_LIMIT = 500
const HISTORY_RENDER_LIMIT = 160
const HISTORY_SEARCH_LIMIT = 120
const MIN_USEFUL_HISTORY_ENTRIES = 4
const ALWAYS_KEEP_HISTORY_ENTRIES = 20
const MAX_CONCURRENT_DESKTOP_TASKS = 2
const NOISY_HISTORY_PREVIEW_PATTERNS = [
  /^\/(?:clear|resume|compact)\b/i,
  /context limit reached/i,
  /\/compact or \/clear/i,
  /oversized recommendation/i,
  /do_not_auto_resume/i,
  /many tool calls;\s*checkpoint before compact/i,
  /^checkpoint\b/i,
  /^ok$/i,
  /^继续$/i,
  /^继续(?:运行|优化|检查|修改)?$/i,
  /^好的?$/i,
  /^再来$/i,
]

const pendingTaskPersist = new Map()

const els = {
  sidebarSubtitle: $('#sidebarSubtitle'),
  historySearchInput: $('#historySearchInput'),
  historyStatusLabel: $('#historyStatusLabel'),
  historySessionList: $('#historySessionList'),
  refreshHistoryBtn: $('#refreshHistoryBtn'),
  projectList: $('#projectList'),
  addProjectBtn: $('#addProjectBtn'),
  activeProviderLabel: $('#activeProviderLabel'),
  sidebarActiveProject: $('#sidebarActiveProject'),
  sidebarActiveModel: $('#sidebarActiveModel'),
  activeModelName: $('#activeModelName'),
  activeModelDetail: $('#activeModelDetail'),
  providerQuickList: $('#providerQuickList'),
  modelCountLabel: $('#modelCountLabel'),
  modelConfigLabel: $('#modelConfigLabel'),
  activeProjectLabel: $('#activeProjectLabel'),
  terminalBtn: $('#terminalBtn'),
  currentContextLabel: $('#currentContextLabel'),
  chatTitle: $('#chatTitle'),
  messageList: $('#messageList'),
  taskRunnerPanel: $('#taskRunnerPanel'),
  taskRunnerTitle: $('#taskRunnerTitle'),
  taskRunnerSummary: $('#taskRunnerSummary'),
  taskQueueList: $('#taskQueueList'),
  taskConcurrencyInput: $('#taskConcurrencyInput'),
  artifactTimelinePanel: $('#artifactTimelinePanel'),
  artifactTimelineTitle: $('#artifactTimelineTitle'),
  artifactTimelineList: $('#artifactTimelineList'),
  workbenchSplit: $('#workbenchSplit'),
  workbenchKicker: $('#workbenchKicker'),
  workbenchTitle: $('#workbenchTitle'),
  workbenchTerminalTab: $('#workbenchTerminalTab'),
  workbenchReviewTab: $('#workbenchReviewTab'),
  closeWorkbenchBtn: $('#closeWorkbenchBtn'),
  terminalSplit: $('#terminalSplit'),
  terminalSplitForm: $('#terminalSplitForm'),
  terminalSplitCommandInput: $('#terminalSplitCommandInput'),
  terminalSplitOutput: $('#terminalSplitOutput'),
  reviewSplit: $('#reviewSplit'),
  reviewFileList: $('#reviewFileList'),
  reviewDiffOutput: $('#reviewDiffOutput'),
  reviewStatusLabel: $('#reviewStatusLabel'),
  refreshReviewBtn: $('#refreshReviewBtn'),
  composerForm: $('#composerForm'),
  taskPrompt: $('#taskPrompt'),
  openTerminalBtn: $('#openTerminalBtn'),
  providerTestBtn: $('#providerTestBtn'),
  changesBtn: $('#changesBtn'),
  sendBtn: $('#sendBtn'),
  drawer: $('#drawer'),
  drawerKicker: $('#drawerKicker'),
  drawerTitle: $('#drawerTitle'),
  closeDrawerBtn: $('#closeDrawerBtn'),
  modelList: $('#modelList'),
  modelForm: $('#modelForm'),
  modelName: $('#modelNameInput'),
  modelId: $('#modelIdInput'),
  baseUrl: $('#baseUrlInput'),
  apiKey: $('#apiKeyInput'),
  apiKeyEnv: $('#apiKeyEnvInput'),
  chatPath: $('#chatPathInput'),
  timeout: $('#timeoutInput'),
  systemPrefix: $('#systemPrefixInput'),
  agentCapable: $('#agentCapableInput'),
  newModelBtn: $('#newModelBtn'),
  diagnoseModelBtn: $('#diagnoseModelBtn'),
  saveModelBtn: $('#saveModelBtn'),
  activateModelBtn: $('#activateModelBtn'),
  deleteModelBtn: $('#deleteModelBtn'),
  terminalForm: $('#terminalForm'),
  terminalCommandInput: $('#terminalCommandInput'),
  terminalOutput: $('#terminalOutput'),
  changedFileList: $('#changedFileList'),
  changesOutput: $('#changesOutput'),
  refreshChangesBtn: $('#refreshChangesBtn'),
  healthOutput: $('#healthOutput'),
  approvalModal: $('#approvalModal'),
  approvalBody: $('#approvalBody'),
  approvalCommand: $('#approvalCommand'),
  approvalReasons: $('#approvalReasons'),
  approvalApproveBtn: $('#approvalApproveBtn'),
  approvalCancelBtn: $('#approvalCancelBtn'),
  langToggleBtn: $('#langToggleBtn'),
  newChatBtn: $('#newChatBtn'),
}

const state = {
  lang: initialLanguage(),
  status: {},
  projects: [],
  activeProject: '',
  providers: [],
  providerConfigPath: '',
  activeProvider: '',
  selectedProvider: '',
  threads: [],
  activeThread: '',
  historyStatus: {},
  historySessions: [],
  selectedHistory: '',
  historyDetail: null,
  historyQuery: '',
  messages: [],
  tasks: [],
  artifacts: [],
  runningTaskCount: 0,
  maxConcurrentTasks: MAX_CONCURRENT_DESKTOP_TASKS,
  mode: 'work',
  drawer: 'models',
  drawerOpen: false,
  activeWorkbenchPanel: '',
  collapsedProjects: readStoredSet('dreamseed.desktop.collapsedProjects'),
  collapsedBuckets: readStoredSet('dreamseed.desktop.collapsedBuckets'),
  diffMode: 'status',
  changedFiles: [],
  changesOutput: '',
  terminalOutput: '',
  pendingApproval: null,
}

wireEvents()
applyI18n()
resetChat()
await refreshAll()

function wireEvents() {
  els.newChatBtn.addEventListener('click', startNewChat)
  els.refreshHistoryBtn.addEventListener('click', () => refreshHistory({ force: true }))
  els.historySearchInput.addEventListener('input', debounce(() => searchHistory(), 280))
  els.historySearchInput.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      event.preventDefault()
      searchHistory()
    }
  })
  els.addProjectBtn.addEventListener('click', addProject)
  els.composerForm.addEventListener('submit', runTask)
  els.taskPrompt.addEventListener('input', autoResizeComposer)
  els.taskPrompt.addEventListener('keydown', event => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) runTask(event)
  })
  els.taskConcurrencyInput.addEventListener('change', updateTaskConcurrency)
  els.openTerminalBtn.addEventListener('click', openTerminal)
  els.terminalBtn.addEventListener('click', openTerminal)
  els.providerTestBtn.addEventListener('click', testProvider)
  els.changesBtn.addEventListener('click', openReviewWorkbench)
  els.closeWorkbenchBtn.addEventListener('click', closeWorkbench)
  els.workbenchTerminalTab.addEventListener('click', () => toggleWorkbenchPanel('terminal', { forceOpen: true }))
  els.workbenchReviewTab.addEventListener('click', () => toggleWorkbenchPanel('review', { forceOpen: true }))
  els.closeDrawerBtn.addEventListener('click', () => setDrawerOpen(false))
  els.newModelBtn.addEventListener('click', startNewModel)
  els.diagnoseModelBtn.addEventListener('click', diagnoseProviders)
  els.saveModelBtn.addEventListener('click', saveProvider)
  els.activateModelBtn.addEventListener('click', activateProvider)
  els.deleteModelBtn.addEventListener('click', deleteProvider)
  els.terminalForm.addEventListener('submit', runTerminalCommand)
  els.terminalSplitForm.addEventListener('submit', runTerminalCommand)
  els.refreshChangesBtn.addEventListener('click', refreshChanges)
  els.refreshReviewBtn.addEventListener('click', refreshChanges)
  els.approvalApproveBtn.addEventListener('click', () => resolveApproval(true))
  els.approvalCancelBtn.addEventListener('click', () => resolveApproval(false))
  els.langToggleBtn.addEventListener('click', toggleLanguage)
  $$('[data-mode]').forEach(button => button.addEventListener('click', () => setMode(button.dataset.mode)))
  $$('[data-drawer]').forEach(button => button.addEventListener('click', () => openDrawer(button.dataset.drawer)))
  $$('[data-doctor]').forEach(button => button.addEventListener('click', () => runDoctor(button.dataset.doctor)))
  $$('[data-diff-mode]').forEach(button => button.addEventListener('click', () => setDiffMode(button.dataset.diffMode)))
  api.onEvent?.('task:output', handleTaskOutput)
}

async function refreshAll() {
  setBusy(true)
  try {
    await Promise.all([loadStatus(), loadProjects(), loadProviders(), loadThreadsSilently(), loadTasksSilently(), loadArtifactsSilently()])
    await refreshHistory({ autoSelect: true })
    renderAll()
  } catch (error) {
    pushMessage('system', 'DreamSeed Desktop', error.message)
  } finally {
    setBusy(false)
  }
}

async function loadStatus() {
  state.status = await invoke('status:get')
}

async function loadProjects() {
  const data = await invoke('project:list')
  state.projects = data.projects || []
  state.activeProject = data.activeProject || state.projects[0]?.id || ''
}

async function loadProviders() {
  const data = await invoke('provider:list')
  state.providers = data.providers || []
  state.providerConfigPath = data.configPath || ''
  state.activeProvider = data.activeProvider || state.providers[0]?.name || ''
  if (!state.selectedProvider) state.selectedProvider = state.activeProvider
}

async function loadThreadsSilently() {
  try {
    const data = await invoke('desktop:threads:list')
    state.threads = data.threads || []
    state.activeThread = data.activeThread || ''
  } catch {
    // Threads are optional desktop metadata; legacy history is the primary list.
    state.threads = []
    state.activeThread = ''
  }
}

async function loadTasksSilently() {
  try {
    const data = await invoke('desktop:tasks:list')
    state.tasks = (data.tasks || []).map(task => normalizeLoadedTask(task))
    state.maxConcurrentTasks = clamp(Number(data.settings?.maxConcurrentTasks || MAX_CONCURRENT_DESKTOP_TASKS), 1, 6)
    for (const task of state.tasks) {
      if (task.wasInterrupted) {
        delete task.wasInterrupted
        persistTask(task)
      }
    }
  } catch {
    state.tasks = []
    state.maxConcurrentTasks = MAX_CONCURRENT_DESKTOP_TASKS
  }
}

async function loadArtifactsSilently() {
  try {
    const data = await invoke('desktop:artifacts:list', { projectId: state.activeProject, limit: 30 })
    state.artifacts = data.artifacts || []
  } catch {
    state.artifacts = []
  }
}

function renderAll() {
  renderHeader()
  renderProjects()
  renderProviders()
  renderHistory()
  renderMessages()
  renderTaskRunner()
  renderArtifactsTimeline()
  renderWorkbench()
  renderDrawer()
  renderTerminal()
  renderChanges()
  renderApprovalModal()
}

function renderHeader() {
  const activeProject = getActiveProject()
  const provider = getActiveProvider()
  const providerCount = state.providers.length
  const providerLabel = provider?.name || state.activeProvider || t('state.none')
  const projectLabel = activeProject?.name || t('state.none')
  els.sidebarSubtitle.textContent = t('app.desktopAgent')
  els.activeProviderLabel.textContent = providerCount > 1 ? `${providerLabel} · ${providerCount}` : providerLabel
  els.activeProviderLabel.textContent = providerCount > 1 ? `${providerLabel} +${providerCount - 1}` : providerLabel
  els.sidebarActiveProject.textContent = projectLabel
  els.sidebarActiveModel.textContent = provider
    ? `${providerLabel} / ${provider.model || t('state.none')}`
    : t('state.noModels')
  els.activeModelName.textContent = providerLabel
  els.activeModelDetail.textContent = provider
    ? `${providerCount} ${t('drawer.models')} / ${provider.model || t('state.none')} / ${providerCapabilityLabel(provider)}`
    : t('state.noModels')
  els.activeProjectLabel.textContent = projectLabel
  els.currentContextLabel.textContent = `${projectLabel} / ${providerLabel}`
  if (!state.selectedHistory && !state.messages.some(item => item.role === 'user')) {
    els.chatTitle.textContent = t('action.newChat')
  }
  $$('.mode-button').forEach(button => button.classList.toggle('active', button.dataset.mode === state.mode))
}

function renderProjects() {
  els.projectList.innerHTML = ''
}

function renderProviders() {
  if (!state.providers.length) {
    els.modelList.innerHTML = emptyState(t('state.noModels'), '')
    els.providerQuickList.innerHTML = ''
    appendAddProviderPill()
    els.modelCountLabel.textContent = '0'
    els.modelConfigLabel.textContent = state.providerConfigPath || ''
    clearProviderForm()
    return
  }
  els.modelCountLabel.textContent = `${state.providers.length}`
  els.modelConfigLabel.textContent = state.providerConfigPath || ''
  renderProviderQuickList()
  els.modelList.innerHTML = ''
  for (const provider of sortedProviders()) {
    const button = document.createElement('button')
    button.type = 'button'
    button.className = `model-item ${provider.name === state.selectedProvider ? 'active' : ''}`
    button.innerHTML = `
      <div class="model-name"><span>${escapeHtml(provider.name)}</span>${provider.name === state.activeProvider ? `<span class="badge">${escapeHtml(t('model.active'))}</span>` : ''}</div>
      <div class="model-meta">${escapeHtml(provider.model || '')}</div>
      <div class="model-meta">${escapeHtml(provider.baseUrl || '')}</div>
      <div class="model-tags">
        <span>${escapeHtml(providerCapabilityLabel(provider))}</span>
        <span>${escapeHtml(provider.modality || 'text')}</span>
        <span>${escapeHtml(provider.auth || '')}</span>
      </div>
    `
    button.addEventListener('click', () => selectProvider(provider.name))
    els.modelList.appendChild(button)
  }
  renderProviderForm()
}

function renderProviderQuickList() {
  els.providerQuickList.innerHTML = ''
  for (const provider of sortedProviders().slice(0, 8)) {
    const button = document.createElement('button')
    button.type = 'button'
    button.className = `provider-pill ${provider.name === state.activeProvider ? 'active' : ''}`
    button.title = `${provider.name} / ${provider.model || ''}`
    button.innerHTML = `
      <strong>${escapeHtml(provider.name)}</strong>
      <span>${escapeHtml(provider.model || '')}</span>
    `
    button.addEventListener('click', () => switchProviderQuick(provider.name))
    els.providerQuickList.appendChild(button)
  }
  appendAddProviderPill()
}

function appendAddProviderPill() {
  const add = document.createElement('button')
  add.type = 'button'
  add.className = 'provider-pill add-provider-pill'
  add.title = t('action.addModel')
  add.innerHTML = `<strong>+</strong><span>${escapeHtml(t('model.addHint'))}</span>`
  add.addEventListener('click', startNewModel)
  els.providerQuickList.appendChild(add)
}

function renderProviderForm() {
  const provider = state.providers.find(item => item.name === state.selectedProvider)
  els.modelForm.dataset.originalName = provider?.name || ''
  els.modelName.value = provider?.name || ''
  els.modelId.value = provider?.model || ''
  els.baseUrl.value = provider?.baseUrl || ''
  els.apiKey.value = ''
  els.apiKey.placeholder = provider?.hasApiKey ? 'stored key kept if blank' : 'paste key or use env'
  els.apiKeyEnv.value = provider?.apiKeyEnv || ''
  els.chatPath.value = provider?.chatCompletionsPath || '/v1/chat/completions'
  els.timeout.value = String(provider?.timeoutMs || 120000)
  els.systemPrefix.value = provider?.systemPrefix || 'Always place the final answer in visible message content.'
  els.agentCapable.checked = provider?.agentCapable !== false
  els.activateModelBtn.disabled = !provider || provider.name === state.activeProvider
  els.deleteModelBtn.disabled = !provider
}

function clearProviderForm() {
  els.modelForm.dataset.originalName = ''
  for (const input of [els.modelName, els.modelId, els.baseUrl, els.apiKey, els.apiKeyEnv]) input.value = ''
  els.chatPath.value = '/v1/chat/completions'
  els.timeout.value = '120000'
  els.systemPrefix.value = 'Always place the final answer in visible message content.'
  els.agentCapable.checked = true
  els.activateModelBtn.disabled = true
  els.deleteModelBtn.disabled = true
}

function renderHistory() {
  const sessions = state.historySessions || []
  const groups = groupedHistorySessions(sessions, state.threads)
  const total = state.historyStatus.sessions || state.historyStatus.total_matches || sessions.length || 0
  const records = state.historyStatus.records || 0
  const filtered = state.historyStatus.filtered_sessions || 0
  els.historyStatusLabel.textContent = total
    ? `${sessions.length}/${total} ${t('history.sessions')}${filtered ? ` | ${filtered} ${t('history.filtered')}` : ''} / ${records} ${t('history.records')}`
    : t('state.noHistory')

  if (!groups.length) {
    els.historySessionList.innerHTML = emptyState(t('state.noProjects'), '')
    return
  }
  els.historySessionList.innerHTML = ''
  const isSearching = Boolean(state.historyQuery)
  for (const group of groups) {
    const projectCollapseKey = `project:${group.key}`
    const projectCollapsed = !isSearching && state.collapsedProjects.has(projectCollapseKey)
    const section = document.createElement('section')
    section.className = `history-project-group ${group.projectId === state.activeProject ? 'active-project' : ''} ${projectCollapsed ? 'collapsed' : ''}`
    section.innerHTML = `
      <button class="history-project-head" type="button" aria-expanded="${projectCollapsed ? 'false' : 'true'}">
        <span class="collapse-caret" aria-hidden="true">${projectCollapsed ? '>' : 'v'}</span>
        <span class="folder-icon" aria-hidden="true"></span>
        <strong>${escapeHtml(group.name)}</strong>
        <span>${escapeHtml(projectGroupCountLabel(group))}</span>
      </button>
    `
    section.querySelector('.history-project-head')?.addEventListener('click', () => toggleProjectCollapse(projectCollapseKey))
    const list = document.createElement('div')
    list.className = 'history-project-list'
    if (!projectCollapsed) {
      const visibleSessions = isSearching ? group.sessions : compactProjectSessions(group)
      for (const bucket of bucketHistorySessions(visibleSessions)) {
        const bucketKey = `${projectCollapseKey}:${bucket.key}`
        const bucketCollapsed = !isSearching && state.collapsedBuckets.has(bucketKey)
        const bucketNode = document.createElement('section')
        bucketNode.className = `history-time-bucket ${bucketCollapsed ? 'collapsed' : ''}`
        bucketNode.innerHTML = `
          <button class="history-time-head" type="button" aria-expanded="${bucketCollapsed ? 'false' : 'true'}">
            <span class="collapse-caret" aria-hidden="true">${bucketCollapsed ? '>' : 'v'}</span>
            <strong>${escapeHtml(bucket.label)}</strong>
            <span>${bucket.sessions.length}</span>
          </button>
        `
        bucketNode.querySelector('.history-time-head')?.addEventListener('click', () => toggleBucketCollapse(bucketKey))
        if (!bucketCollapsed) {
          const bucketList = document.createElement('div')
          bucketList.className = 'history-time-list'
          for (const session of bucket.sessions) {
            const id = session.session_id || session.session_file || `project:${group.key}`
            const button = document.createElement('button')
            button.type = 'button'
            button.className = `conversation-item ${id === state.selectedHistory ? 'active' : ''}`
            button.innerHTML = historyCardHtml(session)
            button.addEventListener('click', () => {
              if (session.kind === 'project-history') showProjectHistoryGroup(group)
              else if (session.kind === 'project-home') showProjectHome(group)
              else if (session.kind === 'thread') showThreadSession(session)
              else showHistorySession(id)
            })
            bucketList.appendChild(button)
          }
          bucketNode.appendChild(bucketList)
        }
        list.appendChild(bucketNode)
      }
    }
    section.appendChild(list)
    els.historySessionList.appendChild(section)
  }
}
function renderMessages() {
  els.messageList.innerHTML = ''
  for (const message of state.messages) {
    const article = document.createElement('article')
    article.className = `message ${message.role || 'system'}`
    const avatar = avatarForRole(message.role)
    article.innerHTML = `
      <div class="avatar">${escapeHtml(avatar)}</div>
      <div class="bubble">
        <div class="message-head">
          <span class="message-title">${escapeHtml(message.title || roleLabel(message.role))}</span>
          <span class="message-time">${escapeHtml(formatTime(message.time))}</span>
        </div>
        <pre class="message-body">${escapeHtml(message.body || '')}</pre>
      </div>
    `
    els.messageList.appendChild(article)
  }
  els.messageList.scrollTop = els.messageList.scrollHeight
}

function renderTaskRunner() {
  const visibleTasks = state.tasks.slice(0, 12)
  els.taskRunnerPanel.hidden = visibleTasks.length === 0
  if (!visibleTasks.length) {
    els.taskQueueList.innerHTML = ''
    return
  }
  const running = state.tasks.filter(task => task.status === 'running' || task.status === 'cancelling').length
  const queued = state.tasks.filter(task => task.status === 'queued').length
  els.taskRunnerTitle.textContent = `${running} / ${state.maxConcurrentTasks}`
  els.taskConcurrencyInput.value = String(state.maxConcurrentTasks)
  els.taskRunnerSummary.textContent = t('task.summary')
    .replace('{running}', String(running))
    .replace('{queued}', String(queued))
  els.taskQueueList.innerHTML = ''
  for (const task of visibleTasks) {
    const card = document.createElement('article')
    card.className = `task-card ${task.status}`
    card.innerHTML = `
      <div class="task-card-head">
        <div class="task-card-title">
          <strong>${escapeHtml(task.title)}</strong>
          <span>${escapeHtml(task.projectName || t('state.none'))} / ${escapeHtml(task.mode || 'work')}</span>
        </div>
        <div class="task-card-actions">
          <span class="task-status-pill">${escapeHtml(taskStatusLabel(task.status))}</span>
          ${task.status === 'queued' || task.status === 'running' ? `<button class="small-button danger" type="button" data-task-cancel="${escapeHtml(task.id)}">${escapeHtml(t('task.cancel'))}</button>` : ''}
        </div>
      </div>
      <pre class="task-output">${escapeHtml(task.output || task.prompt || '')}</pre>
    `
    const cancel = card.querySelector('[data-task-cancel]')
    cancel?.addEventListener('click', () => cancelTask(task.id))
    els.taskQueueList.appendChild(card)
  }
}

function renderArtifactsTimeline() {
  const artifacts = (state.artifacts || []).slice(0, 8)
  els.artifactTimelinePanel.hidden = artifacts.length === 0
  els.artifactTimelineTitle.textContent = String(artifacts.length)
  if (!artifacts.length) {
    els.artifactTimelineList.innerHTML = emptyState(t('artifact.empty'), '')
    return
  }
  els.artifactTimelineList.innerHTML = ''
  for (const artifact of artifacts) {
    const item = document.createElement('article')
    item.className = `artifact-item ${classToken(artifact.type || 'event')}`
    item.innerHTML = `
      <span>${escapeHtml(artifact.type || 'event')}</span>
      <strong>${escapeHtml(artifact.title || 'Artifact')}</strong>
      <small>${escapeHtml(formatTime(artifact.createdAt))}</small>
      <p>${escapeHtml(artifact.summary || '')}</p>
    `
    els.artifactTimelineList.appendChild(item)
  }
}

function taskStatusLabel(status) {
  const key = {
    queued: 'task.statusQueued',
    running: 'task.statusRunning',
    cancelling: 'task.statusCancelled',
    done: 'task.statusDone',
    failed: 'task.statusFailed',
    cancelled: 'task.statusCancelled',
  }[status] || 'state.none'
  return t(key)
}

function renderWorkbench() {
  const open = Boolean(state.activeWorkbenchPanel)
  els.workbenchSplit.hidden = !open
  document.body.classList.toggle('workbench-open', open)
  if (!open) return
  const isTerminal = state.activeWorkbenchPanel === 'terminal'
  els.workbenchKicker.textContent = t('workbench.workspace')
  els.workbenchTitle.textContent = isTerminal ? t('workbench.terminalTitle') : t('workbench.reviewTitle')
  els.workbenchTerminalTab.classList.toggle('active', isTerminal)
  els.workbenchReviewTab.classList.toggle('active', !isTerminal)
  els.terminalSplit.classList.toggle('active', isTerminal)
  els.reviewSplit.classList.toggle('active', !isTerminal)
}

function renderDrawer() {
  document.body.classList.toggle('drawer-open', state.drawerOpen)
  els.drawer.classList.toggle('closed', !state.drawerOpen)
  const titles = {
    models: t('drawer.models'),
    terminal: t('drawer.terminal'),
    changes: t('drawer.changes'),
    health: t('drawer.health'),
  }
  els.drawerTitle.textContent = titles[state.drawer] || 'Panel'
  els.drawerKicker.textContent = 'DreamSeed'
  $$('.drawer-panel').forEach(panel => panel.classList.toggle('active', panel.id === `panel-${state.drawer}`))
  $$('[data-drawer]').forEach(button => {
    button.classList.toggle('active', state.drawerOpen && button.dataset.drawer === state.drawer)
  })
  els.terminalBtn.classList.toggle('active', state.activeWorkbenchPanel === 'terminal')
}

function renderTerminal() {
  const output = state.terminalOutput || 'PS> dreamseed'
  els.terminalOutput.textContent = output
  els.terminalSplitOutput.textContent = output
  els.terminalOutput.scrollTop = els.terminalOutput.scrollHeight
  els.terminalSplitOutput.scrollTop = els.terminalSplitOutput.scrollHeight
}

function renderChanges() {
  $$('[data-diff-mode]').forEach(button => button.classList.toggle('active', button.dataset.diffMode === state.diffMode))
  if (!state.changedFiles.length) {
    els.changedFileList.innerHTML = emptyState(t('state.noChanges'), '')
  } else {
    els.changedFileList.innerHTML = ''
    for (const file of state.changedFiles.slice(0, 100)) {
      const item = document.createElement('div')
      item.className = 'changed-file'
      item.innerHTML = `<span>${escapeHtml(file.status || 'M')}</span><strong>${escapeHtml(file.path || '')}</strong>`
      els.changedFileList.appendChild(item)
    }
  }
  els.changesOutput.textContent = state.changesOutput || 'git status --short'
  renderDiffReview()
}

function renderDiffReview() {
  const files = state.changedFiles || []
  els.reviewStatusLabel.textContent = `${files.length} ${t('review.changedFiles')}`
  if (!files.length) {
    els.reviewFileList.innerHTML = emptyState(t('state.noChanges'), '')
  } else {
    els.reviewFileList.innerHTML = ''
    for (const file of files.slice(0, 120)) {
      const item = document.createElement('button')
      item.type = 'button'
      item.className = 'review-file-item'
      item.innerHTML = `<span>${escapeHtml(file.status || 'M')}</span><strong>${escapeHtml(file.path || '')}</strong>`
      item.addEventListener('click', () => {
        state.diffMode = 'diff'
        refreshChanges()
      })
      els.reviewFileList.appendChild(item)
    }
  }
  els.reviewDiffOutput.innerHTML = diffOutputHtml(state.changesOutput || '')
}

function diffOutputHtml(output) {
  const text = String(output || '').trimEnd()
  if (!text) return emptyState(t('review.noDiff'), state.diffMode === 'status' ? t('state.noChanges') : '')
  const lines = text.split(/\r?\n/).slice(-1200)
  return lines.map((line, index) => {
    const kind = diffLineKind(line)
    return `<div class="diff-line ${kind}"><b>${String(index + 1).padStart(4, ' ')}</b><span>${escapeHtml(line || ' ')}</span></div>`
  }).join('')
}

function diffLineKind(line) {
  if (/^diff --git /.test(line) || /^\+\+\+ /.test(line) || /^--- /.test(line)) return 'file'
  if (/^@@ /.test(line)) return 'hunk'
  if (/^\+/.test(line) && !/^\+\+\+/.test(line)) return 'add'
  if (/^-/.test(line) && !/^---/.test(line)) return 'del'
  if (/^\?\? /.test(line)) return 'new'
  if (/^[MADRCU?!]{1,2}\s/.test(line)) return 'status'
  return 'context'
}

function setMode(mode) {
  state.mode = ['work', 'plan', 'review'].includes(mode) ? mode : 'work'
  if (state.mode === 'review') toggleWorkbenchPanel('review', { forceOpen: true })
  renderHeader()
}

function toggleWorkbenchPanel(name, options = {}) {
  const panel = name === 'review' ? 'review' : 'terminal'
  const shouldClose = !options.forceOpen && state.activeWorkbenchPanel === panel
  state.activeWorkbenchPanel = shouldClose ? '' : panel
  renderWorkbench()
  renderDrawer()
  if (state.activeWorkbenchPanel === 'review') refreshChanges()
  if (state.activeWorkbenchPanel === 'terminal') {
    renderTerminal()
    els.terminalSplitCommandInput.focus()
  }
}

function openReviewWorkbench() {
  toggleWorkbenchPanel('review', { forceOpen: state.activeWorkbenchPanel !== 'review' })
}

function closeWorkbench() {
  state.activeWorkbenchPanel = ''
  renderWorkbench()
  renderDrawer()
}

function openDrawer(name) {
  state.drawer = name || 'models'
  state.drawerOpen = true
  renderDrawer()
  if (state.drawer === 'changes') refreshChanges()
}

function setDrawerOpen(open) {
  state.drawerOpen = Boolean(open)
  renderDrawer()
}

function startNewChat() {
  state.selectedHistory = ''
  state.historyDetail = null
  resetChat()
  els.chatTitle.textContent = t('action.newChat')
  pushMessage('system', 'DreamSeed', t('message.newChat'))
  renderHistory()
}

function resetChat() {
  state.messages = [{
    role: 'system',
    title: t('message.welcomeTitle'),
    body: t('message.welcomeBody'),
    time: new Date().toISOString(),
  }]
  renderMessages()
}

async function refreshHistory(options = {}) {
  if (options.force) {
    state.historySessions = []
    state.historyDetail = null
    state.selectedHistory = ''
    renderHistory()
  }
  els.historyStatusLabel.textContent = t('state.loading')
  try {
    const query = state.historyQuery || ''
    const [status, list] = await Promise.all([
      invoke('history:status'),
      invoke('history:list', { limit: HISTORY_LOAD_LIMIT, query }),
    ])
    state.historyStatus = status || {}
    state.historySessions = normalizeHistorySessions(list.sessions || [], {
      query,
      sourceTotal: list.total_matches || list.count,
    })
    renderHistory()
    const firstGroup = groupedHistorySessions(state.historySessions, state.threads)[0]
    if (options.autoSelect && firstGroup && !state.selectedHistory) {
      showProjectHistoryGroup(firstGroup)
    }
  } catch (error) {
    state.historyStatus = {}
    const summary = summarizeError(error.message)
    els.historyStatusLabel.textContent = t('message.historyFailed')
    els.historySessionList.innerHTML = emptyState(t('message.historyFailed'), summary)
  }
}

async function searchHistory() {
  const query = els.historySearchInput.value.trim()
  state.historyQuery = query
  state.selectedHistory = ''
  state.historyDetail = null
  if (!query) {
    await refreshHistory({ autoSelect: false })
    return
  }
  els.historyStatusLabel.textContent = t('state.loading')
  try {
    const [status, results] = await Promise.all([
      invoke('history:status'),
      invoke('history:search', { query, limit: HISTORY_SEARCH_LIMIT }),
    ])
    state.historyStatus = status || {}
    state.historySessions = normalizeHistorySessions((results.results || []).map(item => ({
      ...item,
      preview: item.snippet || item.preview || '',
      last_time: item.time || item.last_time,
      entry_count: item.entry_count || 0,
    })), {
      query,
      sourceTotal: results.count,
      searchMode: true,
    })
    renderHistory()
  } catch (error) {
    els.historyStatusLabel.textContent = `${t('message.historyFailed')}: ${summarizeError(error.message)}`
  }
}

async function showHistorySession(target, options = {}) {
  if (!target) return
  state.selectedHistory = target
  renderHistory()
  setBusy(true)
  try {
    const detail = await invoke('history:show', { target, tail: 80, maxChars: 24000 })
    state.historyDetail = detail
    renderHistoryConversation(detail)
    if (!options.quiet) els.messageList.focus?.()
  } catch (error) {
    pushMessage('system', t('message.historyFailed'), error.message)
  } finally {
    setBusy(false)
  }
}

function showThreadSession(thread) {
  if (!thread) return
  state.selectedHistory = thread.id
  state.activeThread = thread.id
  els.chatTitle.textContent = thread.title || t('action.newChat')
  els.currentContextLabel.textContent = `${projectNameForId(thread.projectId)} / ${thread.mode || state.mode}`
  state.messages = [
    {
      role: 'user',
      title: state.lang === 'zh' ? '\u4f60' : 'You',
      body: thread.prompt || thread.title || '',
      time: thread.createdAt,
    },
    {
      role: 'assistant',
      title: 'DreamSeed',
      body: thread.summary || t('state.noOutput'),
      time: thread.updatedAt || thread.createdAt,
    },
  ]
  renderHistory()
  renderMessages()
}

function showProjectHome(group) {
  if (!group) return
  state.selectedHistory = `home:${group.key}`
  els.chatTitle.textContent = group.name
  els.currentContextLabel.textContent = projectGroupCountLabel(group)
  const overview = [
    cleanProjectOpeningLine(group),
    group.projectPath ? group.projectPath : '',
  ].filter(Boolean).join('\n')
  const excerpts = projectExcerptMessages(group)
  state.messages = [
    {
      role: 'assistant',
      title: t('history.projectHome'),
      body: overview,
      time: group.latestTime,
    },
    ...excerpts,
  ]
  renderHistory()
  renderMessages()
}

function showProjectHistoryGroup(group) {
  state.selectedHistory = `project:${group.key}`
  const line = cleanProjectOpeningLine(group)
  els.chatTitle.textContent = group.name
  els.currentContextLabel.textContent = `${t('history.readOnly')} / ${group.historyCount || group.sessions.length} ${t('history.sessions')}`
  state.messages = [
    {
      role: 'assistant',
      title: t('history.localSummary'),
      body: line,
      time: group.latestTime,
    },
    ...projectExcerptMessages(group),
  ]
  renderHistory()
  renderProjects()
  renderMessages()
}

function renderHistoryConversation(detail) {
  const session = detail?.session || {}
  const entries = dedupeHistoryEntries(detail?.entries || [])
  const sessionTitle = titleForSession(session)
  els.chatTitle.textContent = sessionTitle
  els.currentContextLabel.textContent = `${t('history.readOnly')} / ${session.entry_count || entries.length} ${t('history.entries')}`
  const summaryMessage = session.assistant_summary
    ? [{
      role: 'assistant',
      title: summaryLabelForSession(session),
      body: cleanSessionOpeningLine(session),
      time: session.last_time || session.first_time,
    }]
    : []
  state.messages = entries.length
    ? [...summaryMessage, ...entries.map(entry => ({
      role: roleForHistory(entry),
      title: titleForHistory(entry),
      body: entry.text || '',
      time: entry.time || session.last_time || session.first_time,
    }))]
    : summaryMessage.length
      ? summaryMessage
      : [{
      role: 'assistant',
      title: 'DreamSeed',
      body: cleanSessionOpeningLine(session),
      time: session.last_time || session.first_time,
    }]
  renderMessages()
}

function dedupeHistoryEntries(entries) {
  const result = []
  const seen = new Set()
  for (const entry of entries) {
    const key = `${entry.time || ''}\n${entry.text || ''}`
    if (!entry.text || seen.has(key)) continue
    seen.add(key)
    result.push(entry)
  }
  return result
}

function normalizeHistorySessions(sessions, options = {}) {
  const seen = new Set()
  const kept = []
  let filtered = 0
  for (const session of sessions || []) {
    const key = session.session_id || session.session_file || `${session.project || ''}:${session.last_time || ''}:${session.preview || ''}`
    if (!key || seen.has(key)) {
      filtered += 1
      continue
    }
    seen.add(key)
    if (!isUsefulHistorySession(session, options)) {
      filtered += 1
      continue
    }
    kept.push(session)
    const limit = options.searchMode ? HISTORY_SEARCH_LIMIT : HISTORY_RENDER_LIMIT
    if (kept.length >= limit) break
  }
  state.historyStatus = {
    ...state.historyStatus,
    filtered_sessions: filtered + Math.max(0, (sessions || []).length - kept.length - filtered),
    useful_sessions: kept.length,
    listed_sessions: (sessions || []).length,
    source_total_matches: options.sourceTotal || state.historyStatus.total_matches || state.historyStatus.sessions || 0,
  }
  return kept
}

function groupedHistorySessions(sessions, threads = []) {
  const groups = new Map()
  const ensureGroup = session => {
    const projectKey = session.project || session.projectPath || projectPathForId(session.projectId) || session.project_name || 'unknown'
    const key = normalizeProjectKey(projectKey)
    const configuredProject = state.projects.find(project => normalizeProjectKey(project.path || project.name || project.id) === key)
    const name = session.project_name || configuredProject?.name || projectNameFromPath(projectKey)
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        name,
        projectId: session.projectId || configuredProject?.id || '',
        projectPath: session.projectPath || configuredProject?.path || projectKey,
        configured: Boolean(configuredProject),
        latest: 0,
        latestTime: '',
        sessions: [],
      })
    }
    const group = groups.get(key)
    if (!group.projectId && session.projectId) group.projectId = session.projectId
    if (!group.projectPath && (session.projectPath || projectKey)) group.projectPath = session.projectPath || projectKey
    if (configuredProject) group.configured = true
    return group
  }
  const add = session => {
    const group = ensureGroup(session)
    const timestamp = Number(session.last_timestamp || Date.parse(session.last_time || session.updatedAt || session.createdAt || '') || 0)
    if (timestamp >= group.latest) {
      group.latest = timestamp
      group.latestTime = session.last_time || session.updatedAt || session.createdAt || group.latestTime
    }
    group.sessions.push(session)
  }
  for (const project of state.projects || []) {
    ensureGroup({
      kind: 'configured-project',
      projectId: project.id,
      projectPath: project.path,
      project: project.path || project.name || project.id,
      project_name: project.name || project.id,
    })
  }
  const persistedThreadIds = new Set(
    (sessions || [])
      .map(session => session.session_id || session.desktop_thread_id || '')
      .filter(Boolean),
  )
  for (const thread of threads || []) {
    const threadHistoryId = thread.historySessionId || thread.id
    if (thread.status !== 'running' && persistedThreadIds.has(threadHistoryId)) continue
    add({
      ...thread,
      kind: 'thread',
      project: thread.projectPath || projectPathForId(thread.projectId),
      projectPath: thread.projectPath || projectPathForId(thread.projectId),
      project_name: projectNameForId(thread.projectId),
      title: thread.title,
      user_preview: thread.prompt || thread.title,
      assistant_summary: thread.summary,
      summary_kind: 'assistant',
      entry_count: thread.turnCount || 2,
      last_time: thread.updatedAt,
      last_timestamp: Date.parse(thread.updatedAt || thread.createdAt || '') || 0,
      session_id: thread.id,
    })
  }
  for (const session of sessions || []) add({ ...session, kind: session.kind || 'history' })
  return [...groups.values()]
    .map(group => ({
      ...group,
      sessions: group.sessions.sort((a, b) => Number(b.last_timestamp || 0) - Number(a.last_timestamp || 0)),
      historyCount: group.sessions.filter(item => item.kind !== 'thread').length,
      threadCount: group.sessions.filter(item => item.kind === 'thread').length,
    }))
    .sort((a, b) => {
      if (a.projectId === state.activeProject && b.projectId !== state.activeProject) return -1
      if (b.projectId === state.activeProject && a.projectId !== state.activeProject) return 1
      return b.latest - a.latest
    })
}

function compactProjectSessions(group) {
  const home = {
    kind: 'project-home',
    session_id: `home:${group.key}`,
    title: group.name,
    user_preview: cleanProjectOpeningLine(group),
    assistant_summary: cleanProjectOpeningLine(group),
    summary_kind: 'local',
    entry_count: group.sessions.length,
    last_time: group.latestTime,
    last_timestamp: group.latest,
  }
  const threads = group.sessions.filter(item => item.kind === 'thread').slice(0, 3)
  const history = group.sessions.filter(item => item.kind !== 'thread')
  const recentHistory = history.slice(0, 5)
  if (!history.length && !threads.length) return [home]
  const allHistory = {
    kind: 'project-history',
    session_id: `project:${group.key}`,
    title: group.name,
    user_preview: cleanProjectOpeningLine(group),
    assistant_summary: cleanProjectOpeningLine(group),
    summary_kind: 'local',
    entry_count: history.length,
    last_time: group.latestTime,
    last_timestamp: group.latest,
  }
  return [home, ...threads, ...recentHistory, ...(history.length > recentHistory.length ? [allHistory] : [])]
}

function bucketHistorySessions(sessions) {
  const buckets = new Map()
  const order = ['pinned', 'today', 'yesterday', 'week', 'older']
  for (const session of sessions || []) {
    const key = historyBucketKey(session)
    if (!buckets.has(key)) buckets.set(key, { key, label: historyBucketLabel(key), sessions: [] })
    buckets.get(key).sessions.push(session)
  }
  return order
    .map(key => buckets.get(key))
    .filter(Boolean)
}

function historyBucketKey(session) {
  if (session.kind === 'project-home' || session.kind === 'project-history') return 'pinned'
  const timestamp = sessionTimestampMs(session)
  if (!timestamp) return 'older'
  const now = new Date()
  const date = new Date(timestamp)
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const startYesterday = startToday - 24 * 60 * 60 * 1000
  const startWeek = startToday - 7 * 24 * 60 * 60 * 1000
  if (timestamp >= startToday) return 'today'
  if (timestamp >= startYesterday) return 'yesterday'
  if (timestamp >= startWeek || sameCalendarWeek(date, now)) return 'week'
  return 'older'
}

function historyBucketLabel(key) {
  const zh = state.lang === 'zh'
  const labels = {
    pinned: zh ? '\u9879\u76ee\u5165\u53e3' : 'Project',
    today: zh ? '\u4eca\u5929' : 'Today',
    yesterday: zh ? '\u6628\u5929' : 'Yesterday',
    week: zh ? '\u8fd1 7 \u5929' : 'This week',
    older: zh ? '\u66f4\u65e9' : 'Earlier',
  }
  return labels[key] || labels.older
}

function sessionTimestampMs(session) {
  const raw = Number(session.last_timestamp || session.updatedAt || session.createdAt || 0)
  if (Number.isFinite(raw) && raw > 0) return raw > 10_000_000_000 ? raw : raw * 1000
  const parsed = Date.parse(session.last_time || session.time || session.updatedAt || session.createdAt || '')
  return Number.isFinite(parsed) ? parsed : 0
}

function sameCalendarWeek(a, b) {
  const start = date => {
    const copy = new Date(date.getFullYear(), date.getMonth(), date.getDate())
    const day = (copy.getDay() + 6) % 7
    copy.setDate(copy.getDate() - day)
    return copy.getTime()
  }
  return start(a) === start(b)
}

function toggleProjectCollapse(key) {
  toggleSetValue(state.collapsedProjects, key)
  writeStoredSet('dreamseed.desktop.collapsedProjects', state.collapsedProjects)
  renderHistory()
}

function toggleBucketCollapse(key) {
  toggleSetValue(state.collapsedBuckets, key)
  writeStoredSet('dreamseed.desktop.collapsedBuckets', state.collapsedBuckets)
  renderHistory()
}

function toggleSetValue(set, key) {
  if (set.has(key)) set.delete(key)
  else set.add(key)
}

function normalizeProjectKey(value) {
  return String(value || 'unknown').trim().toLowerCase()
}

function projectNameFromPath(value) {
  const parts = String(value || '').split(/[\\/]/).filter(Boolean)
  return parts.at(-1) || String(value || 'Unknown')
}

function projectNameForId(id) {
  const project = state.projects.find(item => item.id === id)
  return project?.name || t('state.none')
}

function projectPathForId(id) {
  const project = state.projects.find(item => item.id === id)
  return project?.path || ''
}

function badgeForSession(session) {
  if (session.kind === 'project-home') return t('history.projectHome')
  if (session.kind === 'project-history') return t('history.projectBadge')
  if (session.kind === 'thread') return t('history.desktopThread')
  if (session.source_kind === 'dreamseed-desktop') return t('history.desktopThread')
  return session.kind === 'thread' ? (session.mode || state.mode || 'chat') : String(session.entry_count || 0)
}

function userPreviewForSession(session) {
  return session.user_preview || session.preview || session.prompt || session.title || session.session_id || ''
}

function historyCardHtml(session) {
  if (session.kind === 'project-home') {
    return `
      <div class="conversation-title"><span>${escapeHtml(titleForSession(session))}</span><strong class="badge">${escapeHtml(badgeForSession(session))}</strong></div>
      <div class="conversation-meta">${escapeHtml(formatTime(session.last_time || session.time))}</div>
    `
  }
  if (session.kind === 'project-history') {
    return `
      <div class="conversation-title"><span>${escapeHtml(titleForSession(session))}</span><strong class="badge">${escapeHtml(badgeForSession(session))}</strong></div>
      <div class="conversation-meta">${escapeHtml(`${session.entry_count || 0} ${t('history.sessions')} / ${formatTime(session.last_time || session.time)}`)}</div>
    `
  }
  return `
    <div class="conversation-title"><span>${escapeHtml(titleForSession(session))}</span><strong class="badge">${escapeHtml(badgeForSession(session))}</strong></div>
    <div class="conversation-meta">${escapeHtml(formatTime(session.last_time || session.time))}</div>
  `
}

function summaryLabelForSession(session) {
  return session.summary_kind === 'assistant' ? t('history.assistantSummary') : t('history.localSummary')
}

function projectGroupCountLabel(group) {
  const sessions = Number(group.historyCount || 0)
  const threads = Number(group.threadCount || 0)
  if (sessions && threads) return `${threads} ${t('history.desktopThread')} / ${sessions} ${t('history.sessions')}`
  if (threads) return `${threads} ${t('history.desktopThread')}`
  if (sessions) return `${sessions} ${t('history.sessions')}`
  return group.configured ? t('history.projectHome') : t('history.noThreads')
}

function cleanProjectOpeningLine(group) {
  const count = Number(group.historyCount || group.sessions?.length || 0)
  const focus = bestProjectFocus(group.sessions || [])
  if (state.lang === 'zh') {
    return focus
      ? `${group.name} 已归档 ${count} 段历史，最近主要围绕“${focus}”。`
      : `${group.name} 已加入 DreamSeed。桌面端和终端会共享这个项目的本地历史。`
    if (focus) return `${group.name} 已归档 ${count} 段历史，最近主要围绕“${focus}”。`
    return `${group.name} 已加入 DreamSeed。桌面端和终端会共享这个项目的本地历史。`
  }
  if (focus) return `${group.name} has ${count} archived sessions, most recently about "${focus}".`
  return `${group.name} is ready. Desktop chats and terminal history share this project archive.`
}

function cleanSessionOpeningLine(session) {
  const title = cleanOneLine(session.title || '')
  const recent = bestHistoryFocus(session)
  const project = session.project_name || projectNameFromPath(session.project || '')
  if (state.lang === 'zh') {
    if (title && recent && title !== recent) return `${project} 的这段历史从“${title}”开始，最近关注“${recent}”。`
    if (recent) return `${project} 的这段历史主要围绕“${recent}”。`
    return `${project} 的这段历史已导入，可以作为继续工作的上下文。`
    if (title && recent && title !== recent) return `${project} 的这段历史从“${title}”开始，最近关注“${recent}”。`
    if (recent) return `${project} 的这段历史主要围绕“${recent}”。`
    return `${project} 的这段历史已导入，可以作为继续工作的上下文。`
  }
  if (title && recent && title !== recent) return `${project} history starts with "${title}" and most recently focuses on "${recent}".`
  if (recent) return `${project} history mainly focuses on "${recent}".`
  return `${project} history is imported and can be used as context for continued work.`
}

function projectExcerptMessages(group) {
  const sessions = (group.sessions || [])
    .filter(session => session.kind !== 'thread')
    .filter(session => session.kind !== 'project-home' && session.kind !== 'project-history')
    .slice(0, 6)
  return sessions
    .map(session => {
      const preview = cleanOneLine(userPreviewForSession(session))
      const summary = cleanOneLine(session.assistant_summary || '')
      const lines = [preview, summary && summary !== preview ? summary : ''].filter(Boolean)
      if (!lines.length) return null
      return {
        role: session.summary_kind === 'assistant' ? 'assistant' : 'system',
        title: `${t('history.excerpts')} / ${titleForSession(session)}`,
        body: lines.join('\n'),
        time: session.last_time || session.first_time,
      }
    })
    .filter(Boolean)
}

function projectHistoryOpeningLine(group) {
  const history = group.sessions.filter(item => item.kind !== 'thread')
  const focus = bestProjectFocus(history.length ? history : group.sessions)
  const count = history.length || group.sessions.length || 0
  if (state.lang === 'zh') {
    return focus
      ? `${group.name} 已导入 ${count} 段历史，最近主要围绕“${focus}”。`
      : `${group.name} 的项目历史已导入，可以从这里继续。`
    if (focus) return `${group.name} 已导入 ${count} 段历史，最近主要围绕「${focus}」。`
    return `${group.name} 的项目历史已导入，可以从这里继续。`
  }
  if (focus) return `${group.name} has ${count} imported history sessions, most recently about "${focus}".`
  return `${group.name} history is imported and ready to continue.`
}

function bestProjectFocus(sessions) {
  const candidates = []
  for (const [index, session] of (sessions || []).slice(0, 18).entries()) {
    const focus = bestHistoryFocus(session)
    if (!focus) continue
    const entryCount = Number(session.entry_count || 0)
    const recency = Math.max(0, 18 - index)
    const lengthScore = Math.min(24, focus.length)
    candidates.push({ focus, score: recency * 2 + Math.min(40, entryCount) + lengthScore })
  }
  candidates.sort((a, b) => b.score - a.score)
  return candidates[0]?.focus || ''
}

function sessionOpeningLine(session) {
  const title = cleanOneLine(session.title || '')
  const recent = bestHistoryFocus(session)
  const project = session.project_name || projectNameFromPath(session.project || '')
  if (state.lang === 'zh') {
    if (title && recent && title !== recent) return `${project} 里的这段历史从“${title}”开始，最近关注“${recent}”。`
    if (recent) return `${project} 里的这段历史主要围绕“${recent}”。`
    return `${project} 里的这段历史已导入，可以作为继续工作的上下文。`
    if (title && recent && title !== recent) return `${project} 里这段历史从「${title}」开始，最近关注「${recent}」。`
    if (recent) return `${project} 里这段历史主要围绕「${recent}」。`
    return `${project} 里这段历史已导入，可以作为继续工作的上下文。`
  }
  if (title && recent && title !== recent) return `${project} history starts with "${title}" and most recently focuses on "${recent}".`
  if (recent) return `${project} history mainly focuses on "${recent}".`
  return `${project} history is imported and can be used as context for continued work.`
}

function cleanOneLine(value) {
  return String(value || '')
    .replace(/\[[^\]]*Pasted text[^\]]*\]/gi, '')
    .replace(/^\/(?:clear|resume|compact|init|maintain-assistant)\b/i, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 72)
}

function bestHistoryFocus(session) {
  const summary = cleanOneLine(session.assistant_summary || '')
  const project = cleanOneLine(session.project_name || projectNameFromPath(session.project || ''))
  const summaryFocus = extractQuotedFocus(summary)
  if (summaryFocus) return summaryFocus
  for (const value of [session.user_preview, session.preview, session.title, summary]) {
    const cleaned = cleanOneLine(value || '')
    if (!cleaned || cleaned === project || isNoisyHistoryPreview(cleaned)) continue
    return cleaned
  }
  return ''
}

function extractQuotedFocus(value) {
  const text = cleanOneLine(value)
  const cleanQuoted = text.match(/[“"'「『]([^”"'」』]{2,120})[”"'」』]/)
  if (cleanQuoted) return cleanOneLine(cleanQuoted[1])
  const quoted = text.match(/[「"']([^」"']{2,120})[」"']/)
  if (quoted) return cleanOneLine(quoted[1])
  return ''
}

function isUsefulHistorySession(session, options = {}) {
  const entryCount = Number(session.entry_count || 0)
  const preview = normalizeHistoryPreview(session.preview || session.snippet || '')
  const hasQuery = Boolean(String(options.query || '').trim())
  if (session.source_kind === 'dreamseed-desktop') return entryCount > 0 && !isNoisyHistoryPreview(preview)
  if (options.searchMode && entryCount === 0) return preview.length >= 8 && !isNoisyHistoryPreview(preview)
  if (entryCount <= 0) return false
  if (entryCount <= 2) return false
  if (session.is_resume_stub && entryCount < ALWAYS_KEEP_HISTORY_ENTRIES) return false
  if (isNoisyHistoryPreview(preview)) return false
  if (hasQuery && entryCount >= MIN_USEFUL_HISTORY_ENTRIES) return true
  if (entryCount >= ALWAYS_KEEP_HISTORY_ENTRIES) return true
  if (entryCount < MIN_USEFUL_HISTORY_ENTRIES) return false
  return preview.length >= 8
}

function normalizeHistoryPreview(value) {
  return String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function isNoisyHistoryPreview(preview) {
  const value = normalizeHistoryPreview(preview)
  if (!value) return true
  if (value.length <= 2) return true
  return NOISY_HISTORY_PREVIEW_PATTERNS.some(pattern => pattern.test(value))
}

function roleForHistory(entry) {
  const type = String(entry.type || '').toLowerCase()
  if (type.includes('user') || type.includes('human')) return 'user'
  if (type === 'legacy' || type.includes('reconstructed_user_history')) return 'user'
  if (type.includes('summary')) return 'assistant'
  if (type.includes('assistant') || type.includes('agent')) return 'assistant'
  if (type.includes('tool')) return 'tool'
  return 'system'
}

function titleForHistory(entry) {
  const role = roleForHistory(entry)
  if (role === 'user') return state.lang === 'zh' ? '\u4f60' : 'You'
  if (role === 'assistant') return 'DreamSeed'
  if (role === 'tool') return 'Tool'
  return 'Legacy'
}

async function addProject() {
  setBusy(true)
  try {
    const project = await invoke('project:choose')
    if (project) {
      await loadProjects()
      renderAll()
      pushMessage('system', t('message.projectAdded'), `${project.name}\n${project.path}`)
    }
  } finally {
    setBusy(false)
  }
}

async function setActiveProject(id) {
  if (!id) return
  await invoke('project:active', id)
  await loadProjects()
  await loadArtifactsSilently()
  renderAll()
}

async function openTerminal() {
  toggleWorkbenchPanel('terminal', { forceOpen: state.activeWorkbenchPanel !== 'terminal' })
  if (!state.terminalOutput) appendTerminalLog(t('message.terminalOpened'))
}

async function runTask(event) {
  event?.preventDefault()
  const prompt = els.taskPrompt.value.trim()
  if (!prompt) {
    pushMessage('system', 'DreamSeed', t('message.taskEmpty'))
    return
  }
  const threadTitle = makeThreadTitle(prompt)
  const project = getActiveProject()
  const task = {
    id: `task-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    threadId: '',
    title: threadTitle,
    prompt,
    output: t('message.taskQueued'),
    status: 'queued',
    mode: state.mode,
    projectId: state.activeProject,
    projectName: project?.name || t('state.none'),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
  state.selectedHistory = ''
  els.chatTitle.textContent = threadTitle
  pushMessage('user', state.lang === 'zh' ? '\u4f60' : 'You', prompt)
  els.taskPrompt.value = ''
  autoResizeComposer()
  pushMessage('system', t('message.taskQueued'), threadTitle)
  state.tasks.unshift(task)
  await persistTask(task)
  renderAll()
  try {
    const thread = await invoke('desktop:threads:create', {
      projectId: state.activeProject,
      mode: state.mode,
      title: threadTitle,
      prompt,
      summary: t('message.taskQueued'),
      status: 'queued',
    })
    task.threadId = thread.id
    state.activeThread = thread.id
    await persistTask(task)
  } catch (error) {
    task.status = 'failed'
    task.output = error.message
    await persistTask(task)
  }
  renderTaskRunner()
  pumpTaskQueue()
}

function pumpTaskQueue() {
  while (state.runningTaskCount < state.maxConcurrentTasks) {
    const task = state.tasks.find(item => item.status === 'queued')
    if (!task) break
    runQueuedTask(task)
  }
}

async function runQueuedTask(task) {
  task.status = 'running'
  task.output = t('message.taskRunning')
  task.startedAt = new Date().toISOString()
  task.updatedAt = task.startedAt
  state.runningTaskCount += 1
  await persistTask(task)
  renderTaskRunner()
  try {
    if (task.threadId) {
      await invoke('desktop:threads:update', {
        id: task.threadId,
        status: 'running',
        summary: t('message.taskRunning'),
        mode: task.mode,
      })
    }
    const output = await invoke('task:run', {
      runId: task.id,
      projectId: task.projectId,
      mode: task.mode,
      prompt: task.prompt,
    })
    task.status = 'done'
    task.output = output || t('state.noOutput')
    task.finishedAt = new Date().toISOString()
    await persistTask(task)
    pushMessage('assistant', task.title, task.output)
    await finalizeTaskThread(task, 'done', task.output)
  } catch (error) {
    const cancelled = task.status === 'cancelling' || /cancelled/i.test(error.message || '')
    task.status = cancelled ? 'cancelled' : 'failed'
    task.output = cancelled ? t('message.taskCancelled') : error.message
    task.finishedAt = new Date().toISOString()
    await persistTask(task)
    pushMessage('system', cancelled ? t('message.taskCancelled') : t('message.taskFailed'), `${task.title}\n${task.output}`)
    await finalizeTaskThread(task, task.status, task.output)
  } finally {
    state.runningTaskCount = Math.max(0, state.runningTaskCount - 1)
    task.updatedAt = new Date().toISOString()
    await persistTask(task)
    renderTaskRunner()
    pumpTaskQueue()
  }
}

async function cancelTask(id) {
  const task = state.tasks.find(item => item.id === id)
  if (!task || ['done', 'failed', 'cancelled'].includes(task.status)) return
  if (task.status === 'queued') {
    task.status = 'cancelled'
    task.output = t('message.taskCancelled')
    task.updatedAt = new Date().toISOString()
    await persistTask(task)
    await finalizeTaskThread(task, 'cancelled', task.output)
    renderTaskRunner()
    return
  }
  task.status = 'cancelling'
  task.output = t('message.taskCancelled')
  await persistTask(task)
  renderTaskRunner()
  try {
    await invoke('task:cancel', { runId: task.id })
  } catch (error) {
    task.output = error.message
  }
}

function handleTaskOutput(payload) {
  const task = state.tasks.find(item => item.id === payload?.taskId)
  if (!task || !payload?.chunk) return
  if (!task.output || task.output === t('message.taskRunning')) task.output = ''
  task.output = clipTaskOutput(`${task.output}${payload.chunk}`)
  task.updatedAt = payload.at || new Date().toISOString()
  renderTaskRunner()
  schedulePersistTask(task)
}

async function updateTaskConcurrency() {
  const next = clamp(Number(els.taskConcurrencyInput.value || MAX_CONCURRENT_DESKTOP_TASKS), 1, 6)
  state.maxConcurrentTasks = next
  try {
    await invoke('desktop:settings:update', { maxConcurrentTasks: next })
  } catch (error) {
    pushMessage('system', t('task.runner'), error.message)
  }
  renderTaskRunner()
  pumpTaskQueue()
}

function schedulePersistTask(task) {
  clearTimeout(pendingTaskPersist.get(task.id))
  pendingTaskPersist.set(task.id, setTimeout(() => {
    pendingTaskPersist.delete(task.id)
    persistTask(task)
  }, 450))
}

async function persistTask(task) {
  try {
    await invoke('desktop:tasks:upsert', task)
  } catch {
    // The visible task output should survive the current session even if local metadata is temporarily unavailable.
  }
}

function normalizeLoadedTask(task) {
  const loaded = {
    ...task,
    output: task.output || '',
    status: task.status || 'queued',
  }
  if (loaded.status === 'running' || loaded.status === 'cancelling') {
    loaded.status = 'cancelled'
    loaded.wasInterrupted = true
    loaded.output = loaded.output || 'Task was interrupted by a desktop restart.'
  }
  return loaded
}

function clipTaskOutput(text) {
  const value = String(text || '')
  return value.length > 24000 ? value.slice(-24000) : value
}

async function finalizeTaskThread(task, status, output) {
  if (!task.threadId) return
  try {
    await invoke('desktop:threads:update', {
      id: task.threadId,
      title: task.title,
      prompt: task.prompt,
      summary: summarizeThreadOutput(output || task.output || ''),
      output: output || task.output || '',
      status,
      mode: task.mode,
    })
    await invoke('desktop:artifacts:add', {
      projectId: task.projectId,
      threadId: task.threadId,
      type: `task-${status}`,
      title: task.title,
      summary: summarizeThreadOutput(output || task.output || ''),
    })
    await loadThreadsSilently()
    await loadArtifactsSilently()
    renderArtifactsTimeline()
    await refreshHistory({ autoSelect: false, quiet: true })
    if (status === 'done') await refreshChangesQuiet()
  } catch {
    // History/artifact sync should not hide the task result in the runner.
  }
}

async function testProvider() {
  pushMessage('system', t('action.testModel'), t('message.providerTesting'))
  setBusy(true)
  try {
    const output = await invoke('provider:test')
    replaceLastByRole('system', t('action.testModel'), output)
  } catch (error) {
    replaceLastByRole('system', t('action.testModel'), error.message)
  } finally {
    setBusy(false)
  }
}

async function diagnoseProviders() {
  pushMessage('system', t('action.diagnose'), t('message.providerDiagnosing'))
  setBusy(true)
  try {
    const output = await invoke('provider:diagnose')
    replaceLastByRole('system', t('action.diagnose'), output)
    await addLocalArtifact({
      type: 'provider-diagnose',
      title: t('action.diagnose'),
      summary: summarizeThreadOutput(output || ''),
    })
  } catch (error) {
    replaceLastByRole('system', t('action.diagnose'), error.message)
  } finally {
    setBusy(false)
  }
}

function selectProvider(name) {
  state.selectedProvider = name || ''
  renderProviders()
  if (!name) clearProviderForm()
}

function startNewModel() {
  openDrawer('models')
  selectProvider('')
  els.modelName.focus()
}

async function saveProvider() {
  const payload = {
    originalName: els.modelForm.dataset.originalName || '',
    name: els.modelName.value,
    model: els.modelId.value,
    baseUrl: els.baseUrl.value,
    apiKey: els.apiKey.value,
    apiKeyEnv: els.apiKeyEnv.value,
    chatCompletionsPath: els.chatPath.value,
    timeoutMs: Number(els.timeout.value || 120000),
    systemPrefix: els.systemPrefix.value,
    agentCapable: els.agentCapable.checked,
    activate: true,
  }
  setBusy(true)
  try {
    const saved = await invoke('provider:save', payload)
    state.selectedProvider = saved.name
    await loadProviders()
    renderAll()
    pushMessage('system', t('message.providerSaved'), `${saved.name}\n${saved.model}`)
  } catch (error) {
    pushMessage('system', t('message.providerSaved'), error.message)
  } finally {
    setBusy(false)
  }
}

async function activateProvider() {
  if (!state.selectedProvider) return
  await invoke('provider:active', state.selectedProvider)
  await loadProviders()
  renderAll()
}

async function switchProviderQuick(name) {
  if (!name || name === state.activeProvider) {
    state.selectedProvider = name || state.selectedProvider
    renderProviders()
    return
  }
  state.selectedProvider = name
  setBusy(true)
  try {
    await invoke('provider:active', name)
    await loadProviders()
    renderAll()
  } catch (error) {
    pushMessage('system', t('drawer.models'), error.message)
  } finally {
    setBusy(false)
  }
}

async function deleteProvider() {
  if (!state.selectedProvider) return
  const name = state.selectedProvider
  await invoke('provider:delete', name)
  state.selectedProvider = ''
  await loadProviders()
  renderAll()
  pushMessage('system', t('message.providerDeleted'), name)
}

async function runTerminalCommand(event) {
  event?.preventDefault()
  const input = terminalInputForEvent(event)
  const command = input.value.trim()
  if (!command) return
  toggleWorkbenchPanel('terminal', { forceOpen: true })
  appendTerminalLog(`PS> ${command}\n${t('message.terminalRunning')}`)
  setBusy(true)
  try {
    const approval = await invoke('terminal:check', { projectId: state.activeProject, command })
    if (approval.decision === 'deny') {
      appendTerminalLog(`${t('message.terminalBlocked')}\n${(approval.reasons || []).join('\n')}`)
      return
    }
    let approved = approval.decision === 'allow'
    if (!approved) {
      appendTerminalLog(t('message.needsApproval'))
      approved = await requestApproval(command, approval)
      if (!approved) {
        appendTerminalLog(t('action.cancel'))
        return
      }
    }
    const result = await invoke('terminal:run', { projectId: state.activeProject, command, approved })
    appendTerminalLog(result.output || t('state.noOutput'))
    await addLocalArtifact({
      type: result.ok ? 'terminal-done' : 'terminal-failed',
      title: command,
      summary: summarizeThreadOutput(result.output || ''),
    })
    if (result.ok) input.value = ''
  } catch (error) {
    appendTerminalLog(error.message)
  } finally {
    setBusy(false)
  }
}

async function addLocalArtifact(payload) {
  try {
    await invoke('desktop:artifacts:add', {
      projectId: state.activeProject,
      ...payload,
    })
    await loadArtifactsSilently()
    renderArtifactsTimeline()
  } catch {
    // Artifacts are helpful context, not a blocker for the command/task result.
  }
}

function terminalInputForEvent(event) {
  return event?.currentTarget === els.terminalSplitForm ? els.terminalSplitCommandInput : els.terminalCommandInput
}

async function refreshChanges() {
  state.changesOutput = t('state.loading')
  state.changedFiles = []
  renderChanges()
  setBusy(true)
  try {
    const result = await invoke('workspace:diff', { projectId: state.activeProject, mode: state.diffMode })
    state.changedFiles = result.files || []
    state.changesOutput = result.output || (result.ok ? t('state.noChanges') : t('state.noOutput'))
  } catch (error) {
    state.changedFiles = []
    state.changesOutput = error.message
  } finally {
    setBusy(false)
    renderChanges()
  }
}

async function refreshChangesQuiet() {
  try {
    const result = await invoke('workspace:diff', { projectId: state.activeProject, mode: 'status' })
    state.changedFiles = result.files || []
    state.changesOutput = result.output || ''
    renderChanges()
  } catch {
    // Changes are useful context but not required after every task.
  }
}

function setDiffMode(mode) {
  state.diffMode = ['status', 'diff', 'stat', 'cached'].includes(mode) ? mode : 'status'
  if (!state.activeWorkbenchPanel) state.activeWorkbenchPanel = 'review'
  renderWorkbench()
  refreshChanges()
}

async function runDoctor(name) {
  openDrawer('health')
  els.healthOutput.textContent = t('state.loading')
  setBusy(true)
  try {
    els.healthOutput.textContent = await invoke('doctor:run', name)
  } catch (error) {
    els.healthOutput.textContent = error.message
  } finally {
    setBusy(false)
  }
}

function requestApproval(command, approval) {
  return new Promise(resolve => {
    state.pendingApproval = { command, approval, resolve }
    renderApprovalModal()
  })
}

function resolveApproval(approved) {
  const pending = state.pendingApproval
  if (!pending) return
  state.pendingApproval = null
  renderApprovalModal()
  pending.resolve(Boolean(approved))
}

function renderApprovalModal() {
  const pending = state.pendingApproval
  els.approvalModal.hidden = !pending
  if (!pending) return
  const approval = pending.approval || {}
  els.approvalBody.textContent = `${t('approval.body')} Risk: ${approval.risk || 'unknown'}`
  els.approvalCommand.textContent = pending.command || approval.commandPreview || ''
  els.approvalReasons.innerHTML = (approval.reasons || [])
    .slice(0, 7)
    .map(reason => `<div>${escapeHtml(reason)}</div>`)
    .join('')
}

function pushMessage(role, title, body) {
  state.messages.push({ role, title, body: String(body || ''), time: new Date().toISOString() })
  renderMessages()
}

function replaceLastByRole(role, title, body) {
  for (let index = state.messages.length - 1; index >= 0; index--) {
    if (state.messages[index].role === role) {
      state.messages[index] = { ...state.messages[index], title, body: String(body || ''), time: new Date().toISOString() }
      renderMessages()
      return
    }
  }
  pushMessage(role, title, body)
}

function appendTerminalLog(text) {
  state.terminalOutput = `${state.terminalOutput ? `${state.terminalOutput}\n\n` : ''}${String(text || '')}`.slice(-30000)
  renderTerminal()
}

function autoResizeComposer() {
  els.taskPrompt.style.height = 'auto'
  els.taskPrompt.style.height = `${Math.min(172, Math.max(42, els.taskPrompt.scrollHeight))}px`
}

function toggleLanguage() {
  state.lang = state.lang === 'zh' ? 'en' : 'zh'
  localStorage.setItem('dreamseed.desktop.lang', state.lang)
  applyI18n()
  renderAll()
}

function applyI18n() {
  document.documentElement.lang = state.lang === 'zh' ? 'zh-CN' : 'en'
  els.langToggleBtn.textContent = state.lang === 'zh' ? 'ZH' : 'EN'
  $$('[data-i18n]').forEach(node => {
    node.textContent = t(node.dataset.i18n)
  })
  $$('[data-i18n-placeholder]').forEach(node => {
    node.placeholder = t(node.dataset.i18nPlaceholder)
  })
}

function titleForSession(session) {
  const explicit = String(session.title || '').trim()
  if (explicit) return explicit.slice(0, 72)
  const preview = String(session.preview || '').trim()
  if (preview) return preview.slice(0, 56)
  const project = String(session.project || '').split(/[\\/]/).filter(Boolean).pop()
  return project || session.session_id || 'Legacy session'
}

function roleLabel(role) {
  if (role === 'user') return state.lang === 'zh' ? '\u4f60' : 'You'
  if (role === 'assistant') return 'DreamSeed'
  if (role === 'tool') return 'Tool'
  return 'System'
}

function avatarForRole(role) {
  if (role === 'user') return state.lang === 'zh' ? '\u4f60' : 'You'
  if (role === 'assistant') return 'DS'
  if (role === 'tool') return '$'
  return 'i'
}

function setBusy(isBusy) {
  document.body.classList.toggle('is-busy', Boolean(isBusy))
}

function getActiveProject() {
  return state.projects.find(project => project.id === state.activeProject)
}

function getActiveProvider() {
  return state.providers.find(provider => provider.name === state.activeProvider)
}

function sortedProviders() {
  return [...state.providers].sort((a, b) => {
    if (a.name === state.activeProvider) return -1
    if (b.name === state.activeProvider) return 1
    return String(a.name || '').localeCompare(String(b.name || ''))
  })
}

function providerCapabilityLabel(provider) {
  if (!provider) return t('model.toolsUnknown')
  if (provider.agentCapable === false) return t('model.toolsDisabled')
  const support = String(provider.toolSupport || '').toLowerCase()
  if (support.includes('verified')) return t('model.toolsVerified')
  if (support.includes('not') || support.includes('no')) return t('model.toolsDisabled')
  return t('model.toolsUnknown')
}

function formatTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString(state.lang === 'zh' ? 'zh-CN' : 'en-US', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function invoke(channel, payload) {
  if (!api?.invoke) throw new Error('DreamSeed desktop bridge is unavailable.')
  try {
    return await api.invoke(channel, payload)
  } catch (error) {
    throw new Error(error.message || String(error))
  }
}

function t(key) {
  const dict = state.lang === 'zh' ? ZH : EN
  return dict[key] || EN[key] || key
}

function initialLanguage() {
  const stored = localStorage.getItem('dreamseed.desktop.lang')
  if (stored === 'zh' || stored === 'en') return stored
  return (navigator.language || '').toLowerCase().startsWith('zh') ? 'zh' : 'en'
}

function readStoredSet(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || '[]')
    return new Set(Array.isArray(value) ? value.filter(Boolean) : [])
  } catch {
    return new Set()
  }
}

function writeStoredSet(key, set) {
  localStorage.setItem(key, JSON.stringify([...set].slice(0, 500)))
}

function emptyState(title, body) {
  return `<div class="empty-state"><strong>${escapeHtml(title)}</strong>${body ? `<span>${escapeHtml(body)}</span>` : ''}</div>`
}

function summarizeError(value) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .replace(/DreamSeed JSON parse failed:[^\\n]+/i, 'DreamSeed JSON parse failed')
    .replace(/Error invoking remote method '[^']+':\s*/i, '')
    .slice(0, 260)
}

function summarizeThreadOutput(value) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .replace(/```[\s\S]*?```/g, '[code block]')
    .trim()
    .slice(0, 220)
}

function makeThreadTitle(prompt) {
  const cleaned = cleanOneLine(prompt)
    .replace(/^(please|pls|帮我|请你|麻烦你|能不能|你能不能|继续)\s*/i, '')
    .replace(/[。.!?？].*$/u, '')
    .trim()
  if (!cleaned) return t('action.newChat')
  const limit = /[\u3400-\u9fff]/.test(cleaned) ? 24 : 46
  return cleaned.length > limit ? `${cleaned.slice(0, limit).trim()}...` : cleaned
}

function escapeHtml(text) {
  return String(text ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[char])
}

function classToken(value) {
  return String(value || 'item').replace(/[^a-z0-9_-]/gi, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'item'
}

function clamp(value, min, max) {
  const number = Number(value)
  if (!Number.isFinite(number)) return min
  return Math.min(max, Math.max(min, Math.round(number)))
}

function debounce(fn, wait) {
  let timer
  return (...args) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), wait)
  }
}
