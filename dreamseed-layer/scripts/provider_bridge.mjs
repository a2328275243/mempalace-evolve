#!/usr/bin/env node
import http from 'node:http'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'

const VERSION = '0.1.0'
const args = parseArgs(process.argv.slice(2))
const port = Number(args.port || process.env.DREAMSEED_PROVIDER_PORT || 17891)
const host = args.host || process.env.DREAMSEED_PROVIDER_HOST || '127.0.0.1'
const configPath =
  args.config ||
  process.env.DREAMSEED_PROVIDER_CONFIG ||
  'config/providers.local.json'
const activeProviderName = args.provider || process.env.DREAMSEED_PROVIDER

const config = loadProviderConfig(configPath)
const providerName = activeProviderName || config.activeProvider
const provider = selectProvider(config, providerName)
const configId = providerConfigId(providerName, provider)
const shutdownToken = process.env.DREAMSEED_PROVIDER_SHUTDOWN_TOKEN || ''

const server = http.createServer(async (req, res) => {
  try {
    await route(req, res)
  } catch (error) {
    writeError(res, error)
  }
})

server.listen(port, host, () => {
  console.log(
    JSON.stringify({
      ok: true,
      bridge: 'dreamseed-provider-bridge',
      version: VERSION,
      provider: providerName,
      model: provider.model,
      baseUrl: redactUrl(provider.baseUrl),
      configId,
      listen: `http://${host}:${port}`,
    }),
  )
})

async function route(req, res) {
  const url = new URL(req.url || '/', `http://${host}:${port}`)
  if (req.method === 'OPTIONS') {
    res.writeHead(204, corsHeaders())
    res.end()
    return
  }

  if (req.method === 'GET' && url.pathname === '/health') {
    writeJson(res, {
      ok: true,
      bridge: 'dreamseed-provider-bridge',
      version: VERSION,
      provider: providerName,
      model: provider.model,
      configId,
    })
    return
  }

  if (req.method === 'POST' && url.pathname === '/shutdown' && shutdownToken) {
    const providedToken = req.headers['x-dreamseed-shutdown-token']
    if (providedToken !== shutdownToken) {
      writeJson(
        res,
        {
          type: 'error',
          error: {
            type: 'permission_error',
            message: 'Invalid DreamSeed provider bridge shutdown token.',
          },
        },
        403,
      )
      return
    }
    writeJson(res, { ok: true, shutdown: true })
    res.once('finish', () => {
      server.close(() => {})
      server.closeIdleConnections?.()
      server.closeAllConnections?.()
      server.unref()
    })
    return
  }

  if (req.method === 'GET' && url.pathname === '/v1/models') {
    writeJson(res, {
      data: [
        {
          type: 'model',
          id: provider.model,
          display_name: provider.model,
        },
      ],
      has_more: false,
    })
    return
  }

  if (req.method === 'POST' && url.pathname === '/v1/messages') {
    const body = await readJson(req)
    const message = await createMessage(body)
    if (body.stream) {
      writeAnthropicSse(res, message)
    } else {
      writeJson(res, message)
    }
    return
  }

  writeJson(
    res,
    {
      type: 'error',
      error: {
        type: 'not_found_error',
        message: `DreamSeed provider bridge has no route for ${req.method} ${url.pathname}`,
      },
    },
    404,
  )
}

async function createMessage(body) {
  if (provider.type === 'anthropic-messages') {
    return forwardAnthropicMessage(body)
  }
  return createViaOpenAiChat(body)
}

async function forwardAnthropicMessage(body) {
  const upstream = await fetchJson(joinUrl(provider.baseUrl, provider.messagesPath || '/v1/messages'), {
    method: 'POST',
    headers: providerHeaders('anthropic'),
    body: JSON.stringify({ ...body, stream: false, model: provider.model || body.model }),
  })
  return normalizeAnthropicMessage(upstream)
}

async function createViaOpenAiChat(body) {
  const requestBody = toOpenAiChatRequest(body)
  const upstream = await fetchJson(
    joinUrl(provider.baseUrl, provider.chatCompletionsPath || '/v1/chat/completions'),
    {
      method: 'POST',
      headers: providerHeaders('openai'),
      body: JSON.stringify(requestBody),
    },
  )
  return openAiChatToAnthropicMessage(upstream, requestBody.model)
}

function toOpenAiChatRequest(body) {
  const messages = []
  const systemText = joinText([
    provider.systemPrefix,
    systemToText(body.system),
    provider.systemSuffix,
  ])
  if (systemText) messages.push({ role: 'system', content: systemText })

  for (const message of body.messages || []) {
    messages.push(...anthropicMessageToOpenAiMessages(message))
  }
  if (messages.length === 0) {
    messages.push({ role: 'user', content: '' })
  }

  const request = {
    model: process.env.DREAMSEED_MODEL || provider.model || body.model,
    messages,
    stream: false,
    max_tokens: body.max_tokens || provider.maxTokens || 4096,
  }

  for (const key of ['temperature', 'top_p', 'presence_penalty', 'frequency_penalty']) {
    if (body[key] !== undefined) request[key] = body[key]
  }
  if (Array.isArray(body.stop_sequences) && body.stop_sequences.length > 0) {
    request.stop = body.stop_sequences
  }

  const tools = anthropicToolsToOpenAiTools(body.tools)
  if (tools.length > 0) {
    request.tools = tools
    request.tool_choice = anthropicToolChoiceToOpenAi(body.tool_choice)
  }

  return request
}

function anthropicMessageToOpenAiMessages(message) {
  const role = message.role === 'assistant' ? 'assistant' : 'user'
  if (!Array.isArray(message.content)) {
    return [{ role, content: String(message.content ?? '') }]
  }

  const out = []
  const textParts = []
  const toolCalls = []

  for (const block of message.content) {
    if (!block || typeof block !== 'object') continue
    if (block.type === 'text') {
      textParts.push(block.text || '')
    } else if (block.type === 'tool_use') {
      toolCalls.push({
        id: block.id || `tool_${toolCalls.length + 1}`,
        type: 'function',
        function: {
          name: block.name || 'tool',
          arguments: JSON.stringify(block.input || {}),
        },
      })
    } else if (block.type === 'tool_result') {
      const toolText = contentToText(block.content)
      out.push({
        role: 'tool',
        tool_call_id: block.tool_use_id || block.id || `tool_${out.length + 1}`,
        content: toolText,
      })
    } else if (block.type === 'image') {
      textParts.push('[image omitted by DreamSeed provider bridge]')
    }
  }

  const text = joinText(textParts)
  if (role === 'assistant' && toolCalls.length > 0) {
    out.unshift({
      role: 'assistant',
      content: text || null,
      tool_calls: toolCalls,
    })
  } else if (text || out.length === 0) {
    out.unshift({ role, content: text })
  }

  return out
}

function anthropicToolsToOpenAiTools(tools) {
  if (!Array.isArray(tools)) return []
  return tools
    .filter(tool => tool && tool.name)
    .map(tool => ({
      type: 'function',
      function: {
        name: tool.name,
        description: tool.description || '',
        parameters: tool.input_schema || { type: 'object', properties: {} },
      },
    }))
}

function anthropicToolChoiceToOpenAi(choice) {
  if (!choice || choice.type === 'auto' || choice.type === 'any') return 'auto'
  if (choice.type === 'none') return 'none'
  if (choice.type === 'tool' && choice.name) {
    return { type: 'function', function: { name: choice.name } }
  }
  return 'auto'
}

function openAiChatToAnthropicMessage(payload, model) {
  const choice = payload.choices?.[0] || {}
  const message = choice.message || {}
  let text = contentToText(message.content)
  if (!text && provider.emptyContentFallback === 'reasoning') {
    text = contentToText(message.reasoning || message.reasoning_content)
  }

  const content = []
  if (text) content.push({ type: 'text', text })

  const toolCalls = Array.isArray(message.tool_calls) ? message.tool_calls : []
  for (const call of toolCalls) {
    const fn = call.function || {}
    content.push({
      type: 'tool_use',
      id: call.id || `tool_${content.length + 1}`,
      name: fn.name || call.name || 'tool',
      input: parseJsonObject(fn.arguments),
    })
  }

  return {
    id: payload.id || `msg_${Date.now()}`,
    type: 'message',
    role: 'assistant',
    model: payload.model || model || provider.model,
    content,
    stop_reason: toolCalls.length > 0 ? 'tool_use' : finishReasonToAnthropic(choice.finish_reason),
    stop_sequence: null,
    usage: {
      input_tokens: payload.usage?.prompt_tokens || 0,
      cache_creation_input_tokens: 0,
      cache_read_input_tokens: 0,
      output_tokens: payload.usage?.completion_tokens || 0,
    },
  }
}

function normalizeAnthropicMessage(payload) {
  return {
    id: payload.id || `msg_${Date.now()}`,
    type: 'message',
    role: payload.role || 'assistant',
    model: payload.model || provider.model,
    content: Array.isArray(payload.content) ? payload.content : [{ type: 'text', text: contentToText(payload.content) }],
    stop_reason: payload.stop_reason || 'end_turn',
    stop_sequence: payload.stop_sequence || null,
    usage: {
      input_tokens: payload.usage?.input_tokens || 0,
      cache_creation_input_tokens: payload.usage?.cache_creation_input_tokens || 0,
      cache_read_input_tokens: payload.usage?.cache_read_input_tokens || 0,
      output_tokens: payload.usage?.output_tokens || 0,
    },
  }
}

function writeAnthropicSse(res, message) {
  res.writeHead(200, {
    ...corsHeaders(),
    'content-type': 'text/event-stream; charset=utf-8',
    'cache-control': 'no-cache',
    connection: 'keep-alive',
  })

  const messageStart = {
    type: 'message_start',
    message: {
      id: message.id,
      type: 'message',
      role: 'assistant',
      model: message.model,
      content: [],
      stop_reason: null,
      stop_sequence: null,
      usage: {
        input_tokens: message.usage?.input_tokens || 0,
        cache_creation_input_tokens: 0,
        cache_read_input_tokens: 0,
        output_tokens: 0,
      },
    },
  }
  sse(res, 'message_start', messageStart)

  let index = 0
  for (const block of message.content || []) {
    if (block.type === 'tool_use') {
      sse(res, 'content_block_start', {
        type: 'content_block_start',
        index,
        content_block: {
          type: 'tool_use',
          id: block.id,
          name: block.name,
          input: {},
        },
      })
      sse(res, 'content_block_delta', {
        type: 'content_block_delta',
        index,
        delta: {
          type: 'input_json_delta',
          partial_json: JSON.stringify(block.input || {}),
        },
      })
      sse(res, 'content_block_stop', { type: 'content_block_stop', index })
      index += 1
      continue
    }

    const text = block.text || ''
    sse(res, 'content_block_start', {
      type: 'content_block_start',
      index,
      content_block: { type: 'text', text: '' },
    })
    if (text) {
      sse(res, 'content_block_delta', {
        type: 'content_block_delta',
        index,
        delta: { type: 'text_delta', text },
      })
    }
    sse(res, 'content_block_stop', { type: 'content_block_stop', index })
    index += 1
  }

  sse(res, 'message_delta', {
    type: 'message_delta',
    delta: {
      stop_reason: message.stop_reason || 'end_turn',
      stop_sequence: message.stop_sequence || null,
    },
    usage: { output_tokens: message.usage?.output_tokens || 0 },
  })
  sse(res, 'message_stop', { type: 'message_stop' })
  res.end()
}

function sse(res, event, data) {
  res.write(`event: ${event}\n`)
  res.write(`data: ${JSON.stringify(data)}\n\n`)
}

async function fetchJson(url, options) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), provider.timeoutMs || 120000)
  try {
    const response = await fetch(url, { ...options, signal: controller.signal })
    const text = await response.text()
    if (!response.ok) {
      const error = new Error(`upstream ${response.status}: ${text.slice(0, 500)}`)
      error.statusCode = response.status
      throw error
    }
    try {
      return JSON.parse(text)
    } catch {
      const error = new Error(`upstream returned non-JSON response: ${text.slice(0, 500)}`)
      error.statusCode = 502
      throw error
    }
  } finally {
    clearTimeout(timeout)
  }
}

async function readJson(req) {
  const chunks = []
  let size = 0
  for await (const chunk of req) {
    size += chunk.length
    if (size > 25 * 1024 * 1024) {
      const error = new Error('request body is too large')
      error.statusCode = 413
      throw error
    }
    chunks.push(chunk)
  }
  const raw = Buffer.concat(chunks).toString('utf8')
  return raw ? JSON.parse(raw) : {}
}

function writeJson(res, body, statusCode = 200) {
  res.writeHead(statusCode, {
    ...corsHeaders(),
    'content-type': 'application/json; charset=utf-8',
  })
  res.end(JSON.stringify(body))
}

function writeError(res, error) {
  const statusCode = error.statusCode || 500
  writeJson(
    res,
    {
      type: 'error',
      error: {
        type: statusCode >= 500 ? 'api_error' : 'invalid_request_error',
        message: error.message || String(error),
      },
    },
    statusCode,
  )
}

function providerHeaders(kind) {
  const apiKey = provider.apiKey || (provider.apiKeyEnv ? process.env[provider.apiKeyEnv] : null)
  if (!apiKey) {
    const error = new Error(`provider '${providerName}' is missing apiKey or apiKeyEnv`)
    error.statusCode = 500
    throw error
  }
  const headers = {
    accept: 'application/json',
    'content-type': 'application/json',
    ...provider.headers,
  }
  if (kind === 'anthropic') {
    headers['anthropic-version'] = provider.anthropicVersion || '2023-06-01'
    headers['x-api-key'] = apiKey
    headers.authorization = `Bearer ${apiKey}`
  } else {
    headers.authorization = `Bearer ${apiKey}`
  }
  return headers
}

function corsHeaders() {
  return {
    'access-control-allow-origin': '*',
    'access-control-allow-methods': 'GET,POST,OPTIONS',
    'access-control-allow-headers': 'authorization,content-type,x-api-key,anthropic-version',
  }
}

function loadProviderConfig(path) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'))
  } catch (error) {
    throw new Error(`failed to read provider config at ${path}: ${error.message}`)
  }
}

function selectProvider(data, name) {
  if (!data || typeof data !== 'object' || !data.providers || typeof data.providers !== 'object') {
    throw new Error('provider config must contain a providers object')
  }
  const selectedName = name || Object.keys(data.providers)[0]
  const selected = data.providers[selectedName]
  if (!selected) throw new Error(`provider '${selectedName}' was not found in provider config`)
  if (!selected.baseUrl) throw new Error(`provider '${selectedName}' is missing baseUrl`)
  if (!selected.model) throw new Error(`provider '${selectedName}' is missing model`)
  return {
    type: 'openai-chat',
    chatCompletionsPath: '/v1/chat/completions',
    timeoutMs: 120000,
    ...selected,
    baseUrl: String(selected.baseUrl).replace(/\/+$/, ''),
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

function systemToText(system) {
  if (!system) return ''
  return contentToText(system)
}

function contentToText(content) {
  if (content === undefined || content === null) return ''
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .map(item => {
        if (typeof item === 'string') return item
        if (!item || typeof item !== 'object') return ''
        if (item.type === 'text') return item.text || ''
        if (item.type === 'tool_result') return contentToText(item.content)
        if (typeof item.content === 'string') return item.content
        return ''
      })
      .filter(Boolean)
      .join('\n')
  }
  return String(content)
}

function joinText(parts) {
  return parts.map(part => contentToText(part).trim()).filter(Boolean).join('\n\n')
}

function finishReasonToAnthropic(reason) {
  if (reason === 'length') return 'max_tokens'
  if (reason === 'tool_calls') return 'tool_use'
  return 'end_turn'
}

function parseJsonObject(raw) {
  if (!raw) return {}
  if (typeof raw === 'object') return raw
  try {
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function joinUrl(baseUrl, path) {
  return `${String(baseUrl).replace(/\/+$/, '')}/${String(path).replace(/^\/+/, '')}`
}

function redactUrl(url) {
  try {
    const parsed = new URL(url)
    return `${parsed.protocol}//${parsed.host}`
  } catch {
    return '<invalid-url>'
  }
}

function providerConfigId(name, selectedProvider) {
  const stable = {
    name,
    type: selectedProvider.type,
    baseUrl: redactUrl(selectedProvider.baseUrl),
    model: selectedProvider.model,
    chatCompletionsPath: selectedProvider.chatCompletionsPath,
    messagesPath: selectedProvider.messagesPath,
  }
  return createHash('sha256').update(JSON.stringify(stable)).digest('hex').slice(0, 16)
}
