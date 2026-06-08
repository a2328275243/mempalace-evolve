const state = {
  token: new URLSearchParams(location.search).get('token') || '',
  configPath: '',
  activeProvider: '',
  providers: [],
  selected: '',
  filter: '',
  busy: '',
}

const els = {
  configPath: document.querySelector('#configPath'),
  currentProvider: document.querySelector('#currentProvider'),
  authState: document.querySelector('#authState'),
  modelCount: document.querySelector('#modelCount'),
  listCount: document.querySelector('#listCount'),
  search: document.querySelector('#searchInput'),
  providerList: document.querySelector('#providerList'),
  form: document.querySelector('#providerForm'),
  formTitle: document.querySelector('#formTitle'),
  activeState: document.querySelector('#activeState'),
  notice: document.querySelector('#notice'),
  activateBtn: document.querySelector('#activateBtn'),
  deleteBtn: document.querySelector('#deleteBtn'),
  refreshBtn: document.querySelector('#refreshBtn'),
  newBtn: document.querySelector('#newBtn'),
  discoverBtn: document.querySelector('#discoverBtn'),
  testBtn: document.querySelector('#testBtn'),
  saveBtn: document.querySelector('#saveBtn'),
  resultTitle: document.querySelector('#resultTitle'),
  resultOutput: document.querySelector('#resultOutput'),
  name: document.querySelector('#nameInput'),
  model: document.querySelector('#modelInput'),
  baseUrl: document.querySelector('#baseUrlInput'),
  apiKey: document.querySelector('#apiKeyInput'),
  apiKeyEnv: document.querySelector('#apiKeyEnvInput'),
  chatPath: document.querySelector('#chatPathInput'),
  timeoutMs: document.querySelector('#timeoutInput'),
  systemPrefix: document.querySelector('#systemPrefixInput'),
  testPrompt: document.querySelector('#testPromptInput'),
  activateAfterSave: document.querySelector('#activateAfterSaveInput'),
  templates: [...document.querySelectorAll('[data-template]')],
}

els.refreshBtn.addEventListener('click', () => loadConfig())
els.newBtn.addEventListener('click', () => selectProvider(''))
els.form.addEventListener('submit', event => {
  event.preventDefault()
  saveProvider()
})
els.activateBtn.addEventListener('click', () => setActive())
els.deleteBtn.addEventListener('click', () => deleteProvider())
els.discoverBtn.addEventListener('click', () => discoverModels())
els.testBtn.addEventListener('click', () => testProvider())
els.search.addEventListener('input', () => {
  state.filter = els.search.value.trim().toLowerCase()
  renderList()
})
for (const chip of els.templates) {
  chip.addEventListener('click', () => applyTemplate(chip.dataset.template))
}

try {
  await loadConfig()
} catch (error) {
  showNotice(error.message, 'error')
}

async function loadConfig() {
  return withBusy('refresh', async () => {
    await refreshConfig()
    showNotice('Configuration loaded.', 'ok')
  })
}

async function refreshConfig() {
  const data = await api('/api/config')
  state.configPath = data.configPath
  state.activeProvider = data.activeProvider || ''
  state.providers = data.providers || []
  if (!state.selected && state.activeProvider) state.selected = state.activeProvider
  if (state.selected && !state.providers.some(provider => provider.name === state.selected)) {
    state.selected = state.activeProvider || ''
  }
  render()
}

function render() {
  els.configPath.textContent = state.configPath || 'No private config path resolved'
  els.currentProvider.textContent = state.activeProvider || 'None'
  els.authState.textContent = state.token ? 'Local token' : 'Missing token'
  els.modelCount.textContent = String(state.providers.length)
  renderList()
  renderForm()
  renderBusy()
}

function renderList() {
  const providers = filteredProviders()
  els.listCount.textContent = String(providers.length)
  if (providers.length === 0) {
    const text = state.providers.length === 0 ? 'No saved models. Create one on the right.' : 'No models match this search.'
    els.providerList.innerHTML = `<div class="empty">${escapeHtml(text)}</div>`
    return
  }

  els.providerList.innerHTML = ''
  for (const provider of providers) {
    const item = document.createElement('button')
    item.type = 'button'
    item.className = [
      'provider-item',
      provider.name === state.activeProvider ? 'active' : '',
      provider.name === state.selected ? 'selected' : '',
    ].filter(Boolean).join(' ')
    item.innerHTML = `
      <div class="provider-name">
        <span>${escapeHtml(provider.name)}</span>
        ${provider.name === state.activeProvider ? '<span class="badge">active</span>' : ''}
      </div>
      <div class="provider-meta strong">${escapeHtml(provider.model || '<missing model>')}</div>
      <div class="provider-meta">${escapeHtml(provider.baseUrl || '<missing url>')}</div>
      <div class="provider-auth">${escapeHtml(provider.auth || 'auth unknown')}</div>
    `
    item.addEventListener('click', () => selectProvider(provider.name))
    els.providerList.appendChild(item)
  }
}

function renderForm() {
  const provider = state.providers.find(item => item.name === state.selected)
  const editing = Boolean(provider)
  els.formTitle.textContent = editing ? provider.name : 'New Model'
  els.activeState.textContent = editing && provider.name === state.activeProvider ? 'Active' : 'Not active'
  els.activeState.className = `state-pill ${editing && provider.name === state.activeProvider ? 'active' : ''}`
  els.activateBtn.disabled = !editing || provider.name === state.activeProvider
  els.deleteBtn.disabled = !editing

  if (!editing) {
    els.form.dataset.originalName = ''
    els.name.value = ''
    els.model.value = ''
    els.baseUrl.value = ''
    els.apiKey.value = ''
    els.apiKey.placeholder = 'Paste API key'
    els.apiKeyEnv.value = ''
    els.chatPath.value = '/v1/chat/completions'
    els.timeoutMs.value = '120000'
    els.systemPrefix.value = 'Always place the final answer in visible message content.'
    els.activateAfterSave.checked = true
    return
  }

  els.form.dataset.originalName = provider.name
  els.name.value = provider.name
  els.model.value = provider.model || ''
  els.baseUrl.value = provider.baseUrl || ''
  els.apiKey.value = ''
  els.apiKey.placeholder = provider.hasApiKey ? 'Stored key kept if left blank' : 'Paste API key'
  els.apiKeyEnv.value = provider.apiKeyEnv || ''
  els.chatPath.value = provider.chatCompletionsPath || '/v1/chat/completions'
  els.timeoutMs.value = String(provider.timeoutMs || 120000)
  els.systemPrefix.value = provider.systemPrefix || 'Always place the final answer in visible message content.'
  els.activateAfterSave.checked = provider.name === state.activeProvider
}

function selectProvider(name) {
  state.selected = name
  render()
  showNotice(name ? `Editing ${name}.` : 'Creating a new model endpoint.', 'info')
}

async function saveProvider() {
  return withBusy('save', async () => {
    const originalName = els.form.dataset.originalName || ''
    const payload = formPayload()
    validatePayload(payload, { requireModel: true, editing: Boolean(originalName) })
    payload.originalName = originalName
    payload.activate = els.activateAfterSave.checked
    const saved = await api('/api/providers', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    state.selected = saved.name
    showResult('Saved', `${saved.name}\n${saved.baseUrl}\n${saved.model}`)
    showNotice(`${saved.name} saved${payload.activate ? ' and set active' : ''}.`, 'ok')
    await refreshConfig()
  })
}

async function setActive() {
  const name = state.selected
  if (!name) return
  return withBusy('activate', async () => {
    await api('/api/active', {
      method: 'POST',
      body: JSON.stringify({ name }),
    })
    showResult('Active Model', name)
    showNotice(`${name} is now active.`, 'ok')
    await refreshConfig()
  })
}

async function deleteProvider() {
  const name = state.selected
  if (!name) return
  if (!confirm(`Delete model "${name}"?`)) return
  return withBusy('delete', async () => {
    await api(`/api/providers/${encodeURIComponent(name)}`, { method: 'DELETE' })
    state.selected = ''
    showResult('Deleted', name)
    showNotice(`${name} deleted.`, 'ok')
    await refreshConfig()
  })
}

async function discoverModels() {
  return withBusy('discover', async () => {
    const payload = formPayload()
    validatePayload(payload, { requireModel: false, editing: Boolean(els.form.dataset.originalName) })
    const data = await api('/api/discover', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    if (data.models?.length) {
      if (!els.model.value) els.model.value = data.models[0]
      showResult('Discovered Models', data.models.join('\n'))
      showNotice(`Found ${data.models.length} model${data.models.length === 1 ? '' : 's'}.`, 'ok')
    } else {
      showResult('Discovered Models', 'No models returned.')
      showNotice('The endpoint responded, but returned no models.', 'warn')
    }
  })
}

async function testProvider() {
  return withBusy('test', async () => {
    const payload = formPayload()
    validatePayload(payload, { requireModel: true, editing: Boolean(els.form.dataset.originalName) })
    payload.name = state.selected || payload.name
    payload.prompt = els.testPrompt.value || 'Reply exactly: ok'
    const data = await api('/api/test', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    showResult('Test Result', data.output || JSON.stringify(data, null, 2))
    showNotice('Provider test completed.', 'ok')
  })
}

function formPayload() {
  return {
    name: els.name.value.trim(),
    model: els.model.value.trim(),
    baseUrl: els.baseUrl.value.trim(),
    apiKey: els.apiKey.value,
    apiKeyEnv: els.apiKeyEnv.value.trim(),
    chatCompletionsPath: els.chatPath.value.trim() || '/v1/chat/completions',
    timeoutMs: Number(els.timeoutMs.value || 120000),
    systemPrefix: els.systemPrefix.value,
  }
}

function validatePayload(payload, { requireModel, editing }) {
  const missing = []
  if (!payload.name) missing.push('Name')
  if (!payload.baseUrl) missing.push('Base URL')
  if (requireModel && !payload.model) missing.push('Model')
  if (!editing && !payload.apiKey && !payload.apiKeyEnv) missing.push('API Key or API Key Env')
  if (payload.timeoutMs && (!Number.isFinite(payload.timeoutMs) || payload.timeoutMs < 1000)) missing.push('Timeout >= 1000')
  if (missing.length) throw new Error(`Missing: ${missing.join(', ')}`)
}

function filteredProviders() {
  const filter = state.filter
  if (!filter) return state.providers
  return state.providers.filter(provider =>
    [provider.name, provider.model, provider.baseUrl, provider.auth].some(value =>
      String(value || '').toLowerCase().includes(filter),
    ),
  )
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      authorization: `Bearer ${state.token}`,
      'content-type': 'application/json',
      ...(options.headers || {}),
    },
  })
  const text = await response.text()
  let payload = {}
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = { message: text }
    }
  }
  if (!response.ok) {
    const message = payload.error?.message || payload.message || `Request failed (${response.status})`
    showResult('Error', message)
    showNotice(message, 'error')
    throw new Error(message)
  }
  return payload
}

function showResult(title, output) {
  els.resultTitle.textContent = title
  els.resultOutput.textContent = output || ''
}

async function withBusy(name, fn) {
  if (state.busy) return
  state.busy = name
  renderBusy()
  try {
    return await fn()
  } catch (error) {
    showResult('Error', error.message)
    showNotice(error.message, 'error')
    throw error
  } finally {
    state.busy = ''
    renderBusy()
  }
}

function renderBusy() {
  const busy = state.busy
  els.refreshBtn.disabled = Boolean(busy)
  els.newBtn.disabled = Boolean(busy)
  els.saveBtn.disabled = Boolean(busy)
  els.discoverBtn.disabled = Boolean(busy)
  els.testBtn.disabled = Boolean(busy)
  els.activateBtn.disabled = Boolean(busy) || !state.selected || state.selected === state.activeProvider
  els.deleteBtn.disabled = Boolean(busy) || !state.selected
  els.saveBtn.textContent = busy === 'save' ? 'Saving...' : 'Save'
  els.discoverBtn.textContent = busy === 'discover' ? 'Discovering...' : 'Discover'
  els.testBtn.textContent = busy === 'test' ? 'Testing...' : 'Test'
}

function showNotice(message, type = 'info') {
  els.notice.textContent = message
  els.notice.className = `notice ${type}`
}

function applyTemplate(name) {
  if (name === 'openai') {
    if (!els.name.value) els.name.value = 'openai'
    if (!els.baseUrl.value) els.baseUrl.value = 'https://api.openai.com'
    if (!els.model.value) els.model.value = 'gpt-4o-mini'
  } else if (name === 'glm') {
    if (!els.name.value) els.name.value = 'glm'
    if (!els.baseUrl.value) els.baseUrl.value = 'https://open.bigmodel.cn/api/paas'
    if (!els.model.value) els.model.value = 'glm-4.5'
  } else if (name === 'custom') {
    if (!els.chatPath.value) els.chatPath.value = '/v1/chat/completions'
  }
  showNotice(`${name} template applied.`, 'info')
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}
