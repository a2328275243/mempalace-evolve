#!/usr/bin/env node
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import readline from 'node:readline/promises'
import { spawn } from 'node:child_process'
import { stdin as input, stdout as output } from 'node:process'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const root = path.resolve(__dirname, '..')
const legacyHistoryScript = path.join(root, 'scripts', 'import_claude_history.py')
const legacyHistoryDest =
  process.env.DREAMSEED_LEGACY_HISTORY_DIR ||
  path.join(root, 'legacy-history', 'claude-code')

const args = process.argv.slice(2)
const options = parseArgs(args)

if (options.help) {
  printHelp()
  process.exit(0)
}

if (options.version) {
  printVersion()
  process.exit(0)
}

const baseUrl = normalizeBaseUrl(process.env.ANTHROPIC_BASE_URL || process.env.DREAMSEED_BASE_URL)
const model = options.model || process.env.ANTHROPIC_MODEL || process.env.DREAMSEED_MODEL || 'dreamseed-local'
const apiKey =
  process.env.ANTHROPIC_API_KEY ||
  process.env.ANTHROPIC_AUTH_TOKEN ||
  process.env.DREAMSEED_API_KEY ||
  'dreamseed-local'

if (!baseUrl) {
  console.error('[dreamseed-lite] missing provider endpoint.')
  console.error('[dreamseed-lite] set DREAMSEED_PROVIDER_CONFIG so the launcher can start the provider bridge, or set ANTHROPIC_BASE_URL manually.')
  process.exit(1)
}

const system = loadSystemPrompt(options.systemPromptFiles, options.systemPrompts)

try {
  if (options.print) {
    const prompt = options.prompt.length > 0 ? options.prompt.join(' ') : await readStdin()
    const text = await ask([{ role: 'user', content: prompt }])
    writeResult(text, options.outputFormat)
  } else {
    await interactiveLoop()
  }
} catch (error) {
  console.error(`[dreamseed-lite] ${error.message}`)
  process.exit(1)
}

async function interactiveLoop() {
  const rl = readline.createInterface({ input, output })
  const history = []
  console.log('DreamSeed Lite Kernel')
  console.log('Type /resume to continue imported legacy history, or /exit to quit.')

  while (true) {
    const line = await rl.question('dreamseed> ')
    const prompt = line.trim()
    if (!prompt) continue
    if (prompt === '/exit' || prompt === '/quit') break
    if (prompt === '/resume' || prompt.startsWith('/resume ')) {
      await handleResumeCommand(rl, history, prompt)
      continue
    }

    history.push({ role: 'user', content: prompt })
    const text = await ask(history)
    history.push({ role: 'assistant', content: text })
    console.log(text)
  }

  rl.close()
}

async function ask(messages) {
  const response = await fetch(`${baseUrl}/v1/messages`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': apiKey,
      authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      max_tokens: Number(process.env.DREAMSEED_MAX_TOKENS || 4096),
      system: system || undefined,
      messages: messages.map(message => ({
        role: message.role,
        content: message.content,
      })),
      stream: false,
    }),
  })

  const bodyText = await response.text()
  let body
  try {
    body = bodyText ? JSON.parse(bodyText) : {}
  } catch {
    body = { raw: bodyText }
  }

  if (!response.ok) {
    const detail = body?.error?.message || body?.message || bodyText || response.statusText
    throw new Error(`provider request failed (${response.status}): ${detail}`)
  }

  return extractText(body)
}

async function handleResumeCommand(rl, history, prompt) {
  if (!existsSync(legacyHistoryScript)) {
    console.log(`[dreamseed] legacy history script missing: ${legacyHistoryScript}`)
    return
  }
  if (!existsSync(legacyHistoryDest)) {
    console.log('[dreamseed] no imported legacy history found.')
    console.log('Run: dreamseed history import')
    return
  }

  const target = prompt.slice('/resume'.length).trim()
  try {
    if (target) {
      await resumeLegacySession(history, target)
      return
    }

    const sessions = await runLegacyHistoryJson(['list-sessions', '--dest', legacyHistoryDest, '--limit', '12'])
    const choices = sessions.sessions || []
    if (choices.length === 0) {
      console.log('[dreamseed] imported legacy history has no sessions.')
      return
    }

    console.log('')
    console.log('Imported legacy sessions:')
    choices.forEach((session, index) => {
      const project = session.project || 'unknown'
      const time = session.last_time || session.first_time || 'unknown-time'
      const count = session.entry_count || 0
      const preview = compactLine(session.preview || '', 110)
      console.log(`${String(index + 1).padStart(2, ' ')}. ${time}  ${project}  (${count} entries)`)
      if (preview) console.log(`    ${preview}`)
    })
    console.log('')
    const answer = (await rl.question('Resume number, session id, or search text: ')).trim()
    if (!answer) return

    const selectedNumber = Number(answer)
    if (Number.isInteger(selectedNumber) && selectedNumber >= 1 && selectedNumber <= choices.length) {
      await resumeLegacySession(history, choices[selectedNumber - 1].session_id)
      return
    }

    await resumeLegacySession(history, answer)
  } catch (error) {
    console.log(`[dreamseed] /resume failed: ${error.message}`)
  }
}

async function resumeLegacySession(history, target) {
  const payload = await runLegacyHistoryJson([
    'resume-context',
    target,
    '--dest',
    legacyHistoryDest,
    '--limit-entries',
    process.env.DREAMSEED_RESUME_LIMIT_ENTRIES || '18',
    '--max-chars',
    process.env.DREAMSEED_RESUME_MAX_CHARS || '12000',
  ])

  const context = payload.context || ''
  const session = payload.session || {}
  if (!context) {
    console.log('[dreamseed] selected legacy session had no resumable context.')
    return
  }

  history.push({
    role: 'user',
    content:
      '<legacy-claude-code-resume>\n' +
      context +
      '\n</legacy-claude-code-resume>\n\n' +
      'Use this imported legacy session as private context for the current conversation. Do not store it as long-term memory.',
  })
  history.push({
    role: 'assistant',
    content:
      'Legacy session context loaded. I will use it as private session context only and will not promote it to long-term memory.',
  })

  console.log(
    `[dreamseed] resumed legacy session ${session.session_id || target} from ${session.project || 'unknown'} (${session.entry_count || 0} entries).`,
  )
}

async function runLegacyHistoryJson(args) {
  const python = process.env.DREAMSEED_PYTHON || process.env.PYTHON || 'python'
  const childEnv = {
    ...process.env,
    PYTHONIOENCODING: process.env.PYTHONIOENCODING || 'utf-8',
  }

  return await new Promise((resolve, reject) => {
    const child = spawn(python, [legacyHistoryScript, ...args], {
      cwd: root,
      env: childEnv,
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: false,
      windowsHide: true,
    })
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', chunk => {
      stdout += chunk.toString('utf8')
    })
    child.stderr.on('data', chunk => {
      stderr += chunk.toString('utf8')
    })
    child.on('error', reject)
    child.on('exit', code => {
      if (code && code !== 0) {
        reject(new Error((stderr || stdout || `legacy history exited with code ${code}`).trim()))
        return
      }
      try {
        resolve(JSON.parse(stdout))
      } catch (error) {
        reject(new Error(`legacy history returned invalid JSON: ${error.message}`))
      }
    })
  })
}

function extractText(body) {
  if (typeof body === 'string') return body
  if (typeof body?.content === 'string') return body.content
  if (Array.isArray(body?.content)) {
    return body.content
      .map(block => {
        if (typeof block === 'string') return block
        if (block?.type === 'text') return block.text || ''
        if (typeof block?.text === 'string') return block.text
        return ''
      })
      .join('')
      .trim()
  }
  if (typeof body?.completion === 'string') return body.completion
  if (typeof body?.choices?.[0]?.message?.content === 'string') return body.choices[0].message.content
  if (typeof body?.choices?.[0]?.text === 'string') return body.choices[0].text
  return JSON.stringify(body)
}

function compactLine(text, maxLength) {
  const normalized = String(text || '').replace(/\s+/g, ' ').trim()
  if (normalized.length <= maxLength) return normalized
  return normalized.slice(0, Math.max(0, maxLength - 3)).trimEnd() + '...'
}

function writeResult(text, outputFormat) {
  if (outputFormat === 'json') {
    console.log(JSON.stringify({ type: 'result', subtype: 'success', result: text }))
    return
  }
  if (outputFormat === 'stream-json') {
    console.log(JSON.stringify({ type: 'system', subtype: 'init', mcp_servers: [], tools: [] }))
    console.log(JSON.stringify({ type: 'assistant', message: { content: [{ type: 'text', text }] } }))
    console.log(JSON.stringify({ type: 'result', subtype: 'success', result: text }))
    return
  }
  console.log(text)
}

function loadSystemPrompt(files, inlinePrompts) {
  const parts = []
  for (const file of files) {
    if (existsSync(file)) {
      parts.push(readFileSync(file, 'utf8'))
    }
  }
  parts.push(...inlinePrompts)
  return parts.join('\n\n').trim()
}

async function readStdin() {
  const chunks = []
  for await (const chunk of input) {
    chunks.push(Buffer.from(chunk))
  }
  return Buffer.concat(chunks).toString('utf8').trim()
}

function normalizeBaseUrl(value) {
  if (!value) return ''
  return value.replace(/\/+$/, '')
}

function parseArgs(argv) {
  const options = {
    help: false,
    version: false,
    print: false,
    outputFormat: 'text',
    model: '',
    prompt: [],
    systemPromptFiles: [],
    systemPrompts: [],
  }

  const ignoredValueFlags = new Set([
    '--settings',
    '--mcp-config',
    '--add-dir',
    '--agents',
    '--max-turns',
  ])

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    if (arg === '--help' || arg === '-h') {
      options.help = true
    } else if (arg === '--version' || arg === '-v') {
      options.version = true
    } else if (arg === '--print' || arg === '-p') {
      options.print = true
    } else if (arg === '--verbose') {
      continue
    } else if (arg === '--output-format') {
      options.outputFormat = argv[++index] || 'text'
    } else if (arg.startsWith('--output-format=')) {
      options.outputFormat = arg.slice('--output-format='.length)
    } else if (arg === '--model') {
      options.model = argv[++index] || ''
    } else if (arg.startsWith('--model=')) {
      options.model = arg.slice('--model='.length)
    } else if (arg === '--append-system-prompt-file') {
      options.systemPromptFiles.push(argv[++index] || '')
    } else if (arg.startsWith('--append-system-prompt-file=')) {
      options.systemPromptFiles.push(arg.slice('--append-system-prompt-file='.length))
    } else if (arg === '--append-system-prompt') {
      options.systemPrompts.push(argv[++index] || '')
    } else if (arg.startsWith('--append-system-prompt=')) {
      options.systemPrompts.push(arg.slice('--append-system-prompt='.length))
    } else if (ignoredValueFlags.has(arg)) {
      index += 1
    } else if ([...ignoredValueFlags].some(flag => arg.startsWith(`${flag}=`))) {
      continue
    } else if (arg.startsWith('--')) {
      continue
    } else {
      options.prompt.push(arg)
    }
  }

  return options
}

function printHelp() {
  console.log(`DreamSeed Lite Kernel

Usage:
  dreamseed --print "hello"
  dreamseed
  /resume

This source-only fallback talks to an Anthropic-compatible endpoint. The
DreamSeed launcher starts the provider bridge automatically when
DREAMSEED_PROVIDER_CONFIG points to a private provider config.

Inside the interactive shell, /resume lists imported legacy sessions and
loads the selected session as current chat context only.

For full tool/MCP execution, set DREAMSEED_KERNEL_JS or DREAMSEED_KERNEL_CLI
to a compatible runtime kernel.
`)
}

function printVersion() {
  console.log('dreamseed-lite-kernel 0.1.0')
}
