#!/usr/bin/env node
import http from 'node:http'
import { randomBytes } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawn } from 'node:child_process'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const root = path.resolve(__dirname, '..')
const managerRoot = path.join(root, 'manager')
const args = parseArgs(process.argv.slice(2))
const host = args.host || '127.0.0.1'
const requestedPort = Number(args.port || process.env.DREAMSEED_MANAGER_PORT || 17941)
const token = randomBytes(18).toString('hex')
const configPath = resolveProviderWritePath(process.env, process.cwd(), root, args.config)

if (args.smoke) {
  const config = readConfig()
  console.log(JSON.stringify({
    ok: true,
    manager: 'DreamSeed Model Manager',
    configPath,
    activeProvider: config.activeProvider || '',
    providerCount: Object.keys(config.providers || {}).length,
  }, null, 2))
  process.exit(0)
}

let port = requestedPort
const server = http.createServer(async (req, res) => {
  try {
    await route(req, res)
  } catch (error) {
    writeJson(res, { error: { message: error.message || String(error) } }, error.statusCode || 500)
  }
})

server.listen(port, host, () => {
  const url = `http://${host}:${port}/?token=${token}`
  console.log(`[dreamseed] model manager: ${url}`)
  console.log(`[dreamseed] provider config: ${configPath}`)
  if (!args['no-open']) openBrowser(url)
})

server.on('error', error => {
  if (error.code === 'EADDRINUSE' && port < requestedPort + 20) {
    port += 1
    server.listen(port, host)
    return
  }
  throw error
})

async function route(req, res) {
  const url = new URL(req.url || '/', `http://${host}:${port}`)
  if (req.method === 'GET' && url.pathname === '/') return serveFile(res, path.join(managerRoot, 'index.html'), 'text/html; charset=utf-8')
  if (req.method === 'GET' && url.pathname === '/app.css') return serveFile(res, path.join(managerRoot, 'app.css'), 'text/css; charset=utf-8')
  if (req.method === 'GET' && url.pathname === '/app.js') return serveFile(res, path.join(managerRoot, 'app.js'), 'text/javascript; charset=utf-8')

  requireApiToken(req)

  if (req.method === 'GET' && url.pathname === '/api/config') {
    return writeJson(res, publicConfig())
  }

  if (req.method === 'POST' && url.pathname === '/api/providers') {
    const body = await readJson(req)
    const saved = saveProvider(body)
    return writeJson(res, saved)
  }

  if (req.method === 'DELETE' && url.pathname.startsWith('/api/providers/')) {
    const name = decodeURIComponent(url.pathname.slice('/api/providers/'.length))
    deleteProvider(name)
    return writeJson(res, { ok: true })
  }

  if (req.method === 'POST' && url.pathname === '/api/active') {
    const body = await readJson(req)
    setActiveProvider(body.name)
    return writeJson(res, { ok: true })
  }

  if (req.method === 'POST' && url.pathname === '/api/discover') {
    const body = await readJson(req)
    const provider = providerFromBodyOrSaved(body, { requireModel: false })
    const models = await discoverModels(provider)
    return writeJson(res, { models })
  }

  if (req.method === 'POST' && url.pathname === '/api/test') {
    const body = await readJson(req)
    const provider = providerFromBodyOrSaved(body)
    const output = await testProvider(provider, body.prompt || 'Reply exactly: ok')
    return writeJson(res, { output })
  }

  writeJson(res, { error: { message: 'not found' } }, 404)
}

function publicConfig() {
  const config = readConfig()
  return {
    configPath,
    activeProvider: config.activeProvider || '',
    providers: Object.entries(config.providers || {}).map(([name, provider]) => publicProvider(name, provider)),
  }
}

function publicProvider(name, provider) {
  return {
    name,
    type: provider.type || 'openai-chat',
    baseUrl: displayProviderUrl(provider.baseUrl),
    model: provider.model || '',
    chatCompletionsPath: provider.chatCompletionsPath || '/v1/chat/completions',
    systemPrefix: provider.systemPrefix || 'Always place the final answer in visible message content.',
    timeoutMs: provider.timeoutMs || 120000,
    apiKeyEnv: provider.apiKeyEnv || '',
    hasApiKey: Boolean(provider.apiKey),
    auth: describeProviderAuth(provider),
    agentCapable: provider.agentCapable,
    toolSupport: provider.toolSupport || '',
    modality: provider.modality || provider.capability || '',
  }
}

function saveProvider(body) {
  const config = readConfig()
  const originalName = sanitizeProviderName(body.originalName || '')
  const name = sanitizeProviderName(body.name || '')
  if (!name) throw badRequest('provider name is required')
  const existing = config.providers?.[originalName] || config.providers?.[name] || {}
  const provider = providerFromBody(body, existing)
  config.providers = config.providers || {}
  if (originalName && originalName !== name) delete config.providers[originalName]
  config.providers[name] = provider
  if (body.activate || !config.activeProvider) config.activeProvider = name
  if (originalName && config.activeProvider === originalName) config.activeProvider = name
  writeConfig(config)
  return publicProvider(name, provider)
}

function deleteProvider(name) {
  const providerName = sanitizeProviderName(name)
  const config = readConfig()
  if (!config.providers?.[providerName]) throw badRequest(`provider '${providerName}' was not found`)
  delete config.providers[providerName]
  if (config.activeProvider === providerName) {
    config.activeProvider = Object.keys(config.providers || {})[0] || ''
  }
  writeConfig(config)
}

function setActiveProvider(name) {
  const providerName = sanitizeProviderName(name)
  const config = readConfig()
  if (!config.providers?.[providerName]) throw badRequest(`provider '${providerName}' was not found`)
  config.activeProvider = providerName
  writeConfig(config)
}

function providerFromBodyOrSaved(body, options = {}) {
  if (body.name) {
    const config = readConfig()
    const saved = config.providers?.[sanitizeProviderName(body.name)]
    if (saved) return providerFromBody(body, saved, options)
  }
  return providerFromBody(body, {}, options)
}

function providerFromBody(body, existing = {}, options = {}) {
  const requireModel = options.requireModel !== false
  const baseUrl = normalizeProviderBaseUrl(body.baseUrl || existing.baseUrl)
  const model = String(body.model || existing.model || '').trim()
  if (requireModel && !model) throw badRequest('model is required')
  const timeoutMs = Number(body.timeoutMs || existing.timeoutMs || 120000)
  if (!Number.isFinite(timeoutMs) || timeoutMs < 1000) throw badRequest('timeout must be at least 1000 ms')

  const provider = {
    type: String(body.type || existing.type || 'openai-chat'),
    baseUrl,
    model,
    chatCompletionsPath: String(body.chatCompletionsPath || existing.chatCompletionsPath || '/v1/chat/completions'),
    systemPrefix: String(body.systemPrefix ?? existing.systemPrefix ?? 'Always place the final answer in visible message content.'),
    timeoutMs,
  }
  if (body.agentCapable !== undefined) provider.agentCapable = Boolean(body.agentCapable)
  else if (existing.agentCapable !== undefined) provider.agentCapable = Boolean(existing.agentCapable)
  if (body.toolSupport || existing.toolSupport) provider.toolSupport = String(body.toolSupport || existing.toolSupport)
  if (body.modality || existing.modality) provider.modality = String(body.modality || existing.modality)

  if (body.apiKeyEnv) provider.apiKeyEnv = String(body.apiKeyEnv).trim()
  if (body.apiKey) provider.apiKey = String(body.apiKey)
  else if (existing.apiKey) provider.apiKey = existing.apiKey
  else if (!provider.apiKeyEnv && existing.apiKeyEnv) provider.apiKeyEnv = existing.apiKeyEnv

  if (!provider.apiKey && !provider.apiKeyEnv) throw badRequest('api key or api key env is required')
  return provider
}

async function discoverModels(provider) {
  const apiKey = providerApiKey(provider)
  const response = await fetch(joinUrl(provider.baseUrl, '/v1/models'), {
    headers: {
      accept: 'application/json',
      authorization: `Bearer ${apiKey}`,
      'x-api-key': apiKey,
    },
  })
  if (!response.ok) throw badRequest(`model discovery failed (${response.status})`)
  const payload = await response.json()
  const rawModels = Array.isArray(payload.data) ? payload.data : Array.isArray(payload.models) ? payload.models : []
  return rawModels.map(model => (typeof model === 'string' ? model : model?.id || model?.name)).filter(Boolean)
}

async function testProvider(provider, prompt) {
  const apiKey = providerApiKey(provider)
  const response = await fetch(joinUrl(provider.baseUrl, provider.chatCompletionsPath || '/v1/chat/completions'), {
    method: 'POST',
    headers: {
      accept: 'application/json',
      'content-type': 'application/json',
      authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: provider.model,
      messages: [{ role: 'user', content: prompt }],
      stream: false,
      max_tokens: 128,
    }),
  })
  const text = await response.text()
  if (!response.ok) throw badRequest(`provider test failed (${response.status}): ${text.slice(0, 500)}`)
  const payload = JSON.parse(text)
  return contentToText(payload.choices?.[0]?.message?.content || payload.content || '')
}

function providerApiKey(provider) {
  if (provider.apiKey) return provider.apiKey
  if (provider.apiKeyEnv && process.env[provider.apiKeyEnv]) return process.env[provider.apiKeyEnv]
  throw badRequest('provider api key is missing')
}

function readConfig() {
  if (!existsSync(configPath)) return { activeProvider: '', providers: {} }
  const data = JSON.parse(readFileSync(configPath, 'utf8'))
  if (!data.providers || typeof data.providers !== 'object') data.providers = {}
  return data
}

function writeConfig(config) {
  mkdirSync(path.dirname(configPath), { recursive: true })
  writeFileSync(configPath, JSON.stringify(config, null, 2) + '\n', 'utf8')
}

function serveFile(res, filePath, contentType) {
  if (!existsSync(filePath)) return writeJson(res, { error: { message: 'asset missing' } }, 404)
  res.writeHead(200, { 'content-type': contentType, 'cache-control': 'no-store' })
  res.end(readFileSync(filePath))
}

async function readJson(req) {
  const chunks = []
  let size = 0
  for await (const chunk of req) {
    size += chunk.length
    if (size > 2 * 1024 * 1024) throw badRequest('request body is too large')
    chunks.push(chunk)
  }
  const raw = Buffer.concat(chunks).toString('utf8')
  return raw ? JSON.parse(raw) : {}
}

function writeJson(res, body, statusCode = 200) {
  res.writeHead(statusCode, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
  })
  res.end(JSON.stringify(body))
}

function requireApiToken(req) {
  const auth = req.headers.authorization || ''
  if (auth !== `Bearer ${token}`) {
    const error = new Error('unauthorized')
    error.statusCode = 401
    throw error
  }
}

function parseArgs(argv) {
  const out = {}
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    if (!arg.startsWith('--')) continue
    const key = arg.slice(2)
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

function resolveProviderWritePath(env, projectDir, repoRoot, explicitPath) {
  if (explicitPath) return path.resolve(explicitPath)
  if (env.DREAMSEED_PROVIDER_CONFIG) return env.DREAMSEED_PROVIDER_CONFIG
  const localRoot = env.DREAMSEED_LOCAL_ROOT ||
    (env.LOCALAPPDATA ? path.join(env.LOCALAPPDATA, 'DreamSeed') : '')
  if (localRoot) return path.join(localRoot, 'config', 'providers.local.json')
  const appDataDir = env.APPDATA
  if (appDataDir) return path.join(appDataDir, 'DreamSeed', 'config', 'providers.local.json')
  const homeDir = env.DREAMSEED_HOME || env.HOME || env.USERPROFILE
  if (homeDir) return path.join(homeDir, '.dreamseed', 'providers.local.json')
  return path.join(projectDir || repoRoot, '.dreamseed', 'providers.local.json')
}

function sanitizeProviderName(value) {
  return String(value || '').trim().toLowerCase().replace(/[^a-z0-9_.-]+/g, '-').replace(/^-+|-+$/g, '')
}

function normalizeProviderBaseUrl(value) {
  let raw = String(value || '').trim()
  if (!raw) throw badRequest('base url is required')
  if (!/^https?:\/\//i.test(raw)) raw = `https://${raw}`
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

function describeProviderAuth(provider) {
  if (provider.apiKeyEnv) return process.env[provider.apiKeyEnv] ? `env ${provider.apiKeyEnv} is set` : `env ${provider.apiKeyEnv} is missing`
  if (provider.apiKey) return 'stored in private config'
  return 'missing'
}

function joinUrl(baseUrl, routePath) {
  return `${String(baseUrl).replace(/\/+$/, '')}/${String(routePath).replace(/^\/+/, '')}`
}

function contentToText(content) {
  if (content === undefined || content === null) return ''
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content.map(item => (typeof item === 'string' ? item : item?.text || '')).filter(Boolean).join('\n')
  }
  return String(content)
}

function openBrowser(url) {
  if (process.env.DREAMSEED_MANAGER_NO_OPEN) return
  const platform = process.platform
  const child =
    platform === 'win32'
      ? spawn('cmd', ['/c', 'start', '', url], { detached: true, stdio: 'ignore', windowsHide: true })
      : platform === 'darwin'
        ? spawn('open', [url], { detached: true, stdio: 'ignore' })
        : spawn('xdg-open', [url], { detached: true, stdio: 'ignore' })
  child.unref()
}

function badRequest(message) {
  const error = new Error(message)
  error.statusCode = 400
  return error
}
