import { createHash } from 'node:crypto'
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'

export function writeDesktopHistorySession(thread, options = {}) {
  const appRoot = options.appRoot || path.resolve('.')
  const localRoot = options.localRoot || 'D:\\DreamSeed-Local-Agent'
  const defaultProjectPath = options.defaultProjectPath || process.cwd()
  const historySessionsDir =
    options.historySessionsDir || path.join(appRoot, 'legacy-history', 'claude-code', 'sessions')
  const projectPath = thread.projectPath || defaultProjectPath
  const createdAt = normalizeIso(thread.createdAt) || new Date().toISOString()
  const updatedAt = normalizeIso(thread.updatedAt) || createdAt
  const sessionId = isUuid(thread.historySessionId)
    ? thread.historySessionId
    : isUuid(thread.id)
      ? thread.id
      : deterministicUuidFromText(`dreamseed-desktop:${thread.id || projectPath}:${createdAt}`)

  thread.historySessionId = sessionId

  const projectHash = createHash('sha1').update(projectPath || 'unknown').digest('hex').slice(0, 10)
  const sessionDir = path.join(historySessionsDir, `desktop-${projectHash}`)
  const sessionFile = thread.historySessionFile || path.join(sessionDir, `${safeFileName(sessionId)}.json`)
  const output = options.output === undefined ? thread.outputPreview : options.output
  const entries = [
    {
      iso_time: createdAt,
      timestamp: toUnixSeconds(createdAt),
      type: 'dreamseed_desktop_user',
      display: redactHistoryText(thread.prompt || thread.title || ''),
    },
  ]

  const outputText = String(output || '').trim()
  if (outputText) {
    entries.push({
      iso_time: updatedAt,
      timestamp: toUnixSeconds(updatedAt),
      type: options.phase === 'failed' ? 'dreamseed_desktop_assistant_error' : 'dreamseed_desktop_assistant',
      display: redactHistoryText(outputText),
    })
  } else if (thread.summary) {
    entries.push({
      iso_time: updatedAt,
      timestamp: toUnixSeconds(updatedAt),
      type: 'dreamseed_desktop_summary',
      display: redactHistoryText(thread.summary),
    })
  }

  const contentHash = createHash('sha1')
    .update(JSON.stringify({ sessionId, projectPath, entries }, null, 0))
    .digest('hex')
  const payload = {
    source_kind: 'dreamseed-desktop',
    project: projectPath,
    session_id: sessionId,
    desktop_thread_id: thread.id,
    desktop_mode: thread.mode || 'work',
    desktop_status: thread.status || 'open',
    first_iso_time: createdAt,
    last_iso_time: updatedAt,
    first_timestamp: toUnixSeconds(createdAt),
    last_timestamp: toUnixSeconds(updatedAt),
    entry_count: entries.length,
    content_hash: contentHash,
    entries,
  }

  mkdirSync(path.dirname(sessionFile), { recursive: true })
  writeFileSync(sessionFile, JSON.stringify(payload, null, 2) + '\n', 'utf8')
  writeDesktopNativeResumeBridge(payload, sessionFile, { localRoot })
  return { sessionId, sessionFile, nativeResumeFile: nativeResumePath(payload, localRoot) }
}

export function writeDesktopNativeResumeBridge(session, sessionFile, options = {}) {
  const out = nativeResumePath(session, options.localRoot || 'D:\\DreamSeed-Local-Agent')
  if (!out) return ''

  const sessionId = String(session.session_id || '').trim()
  const projectPath = session.project || process.cwd()
  const contentHash = createHash('sha1')
    .update(JSON.stringify({ sessionId, sessionFile, contentHash: session.content_hash }, null, 0))
    .digest('hex')
  const timestamp = session.last_iso_time || session.first_iso_time || new Date().toISOString()
  const userText = summarizeText(
    session.entries?.find(entry => String(entry.type || '').includes('user'))?.display || session.session_id,
    5000,
  )
  const assistantText = summarizeText(
    findLastEntry(session.entries || [], entry =>
      String(entry.type || '').includes('assistant') || String(entry.type || '').includes('summary'),
    )?.display || 'DreamSeed Desktop session saved into the shared local history archive.',
    5000,
  )
  const title = summarizeText(userText || `DreamSeed Desktop ${sessionId}`, 120)
  const userUuid = deterministicUuidFromText(`dreamseed-desktop-user:${sessionId}:${contentHash}`)
  const assistantUuid = deterministicUuidFromText(`dreamseed-desktop-assistant:${sessionId}:${contentHash}`)
  const entries = [
    {
      type: 'dreamseed-desktop-resume-bridge',
      sessionId,
      desktop_thread_id: session.desktop_thread_id || '',
      source_kind: 'dreamseed-desktop',
      desktop_session_file: String(sessionFile),
      desktop_content_hash: contentHash,
      targetCwd: projectPath,
      timestamp,
    },
    {
      parentUuid: null,
      isSidechain: false,
      promptId: deterministicUuidFromText(`dreamseed-desktop-prompt:${sessionId}:${contentHash}`),
      type: 'user',
      message: {
        role: 'user',
        content: `${userText}\n\nDreamSeed Desktop shared-history session. Continue this as normal project context only.`,
      },
      uuid: userUuid,
      timestamp,
      permissionMode: 'default',
      userType: 'external',
      entrypoint: 'desktop',
      cwd: projectPath,
      sessionId,
      version: '0.1.0',
      gitBranch: 'HEAD',
    },
    {
      parentUuid: userUuid,
      isSidechain: false,
      message: {
        id: `dreamseed-desktop-${sessionId}`,
        type: 'message',
        role: 'assistant',
        model: 'dreamseed-desktop',
        content: [{ type: 'text', text: assistantText }],
        stop_reason: 'end_turn',
        stop_sequence: null,
        usage: {
          input_tokens: 0,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
          output_tokens: 0,
        },
      },
      type: 'assistant',
      uuid: assistantUuid,
      timestamp,
      userType: 'external',
      entrypoint: 'desktop',
      cwd: projectPath,
      sessionId,
      version: '0.1.0',
      gitBranch: 'HEAD',
    },
    { type: 'last-prompt', lastPrompt: title, sessionId },
    { type: 'custom-title', customTitle: `DreamSeed Desktop: ${title}`, sessionId },
  ]

  mkdirSync(path.dirname(out), { recursive: true })
  writeFileSync(out, entries.map(entry => JSON.stringify(entry)).join('\n') + '\n', 'utf8')
  return out
}

export function nativeResumePath(session, localRoot) {
  const sessionId = String(session?.session_id || '').trim()
  if (!isUuid(sessionId)) return ''
  const projectPath = session.project || process.cwd()
  return path.join(localRoot, 'home', '.claude', 'projects', nativeSanitizePath(projectPath), `${sessionId}.jsonl`)
}

export function isUuid(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || ''))
}

export function deterministicUuidFromText(value) {
  const chars = createHash('sha1').update(String(value || 'dreamseed')).digest('hex').slice(0, 32).split('')
  chars[12] = '5'
  chars[16] = ((Number.parseInt(chars[16], 16) & 0x3) | 0x8).toString(16)
  const hex = chars.join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export function nativeSanitizePath(value) {
  return String(value || '').replace(/[^A-Za-z0-9]/g, '-')
}

function normalizeIso(value) {
  const date = new Date(value || '')
  if (Number.isNaN(date.getTime())) return ''
  return date.toISOString()
}

function toUnixSeconds(value) {
  const date = new Date(value || '')
  if (Number.isNaN(date.getTime())) return Math.floor(Date.now() / 1000)
  return Math.floor(date.getTime() / 1000)
}

function safeFileName(value) {
  const text = String(value || 'session').replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^-+|-+$/g, '')
  return (text || 'session').slice(0, 120)
}

function redactHistoryText(value) {
  return String(value || '')
    .replace(/sk-[A-Za-z0-9_-]{20,}/g, '[REDACTED]')
    .replace(/((api[_-]?key|token|secret|password)\s*[:=]\s*)['"]?[^'"\s]+/gi, '$1[REDACTED]')
}

function summarizeText(value, max) {
  return String(value || '').replace(/\s+/g, ' ').trim().slice(0, max)
}

function findLastEntry(entries, predicate) {
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    if (predicate(entries[index])) return entries[index]
  }
  return null
}
