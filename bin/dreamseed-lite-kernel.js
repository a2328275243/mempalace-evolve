#!/usr/bin/env node
// DreamSeed Lite Kernel v0.2.0
import { existsSync, mkdirSync, readFileSync, writeFileSync, readdirSync, appendFileSync, statSync, renameSync, unlinkSync } from "node:fs";
import { rename } from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { createInterface } from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import os from "node:os";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");
// P11-E: prefer env override, then existing repo-root .dreamseed (back-compat),
// then user-home .dreamseed (works when ROOT is read-only / Program Files install).
function _resolveDreamseedDir() {
  if (process.env.DREAMSEED_DIR) return process.env.DREAMSEED_DIR;
  const repoLocal = path.join(ROOT, ".dreamseed");
  try { if (existsSync(repoLocal)) return repoLocal; } catch (_) {}
  return path.join(os.homedir(), ".dreamseed");
}
const DREAMSEED_DIR = _resolveDreamseedDir();
const HISTORY_DIR = process.env.DREAMSEED_HISTORY_DIR || path.join(DREAMSEED_DIR, "history");
const CACHE_DIR = process.env.DREAMSEED_CACHE_DIR || path.join(DREAMSEED_DIR, "cache");
const LOG_DIR = process.env.DREAMSEED_LOG_DIR || path.join(DREAMSEED_DIR, "logs");
const SETTINGS_FILE = process.env.DREAMSEED_SETTINGS_FILE || path.join(DREAMSEED_DIR, "settings.json");
const MCP_CONFIG = process.env.DREAMSEED_MCP_CONFIG || path.join(ROOT, ".mcp.json");
const PROMPT_FILE = path.join(ROOT, "docs", "dreamseed-system-prompt.md");
const AGENTS_DIR = path.join(DREAMSEED_DIR, "agents");
const SKILLS_DIR = process.env.DREAMSEED_SKILLS_DIR || path.join(DREAMSEED_DIR, "skills");
const LEGACY_HISTORY_SCRIPT = path.join(ROOT, "scripts", "import_claude_history.py");
const LEGACY_HISTORY_DEST = process.env.DREAMSEED_LEGACY_HISTORY_DIR || path.join(ROOT, "legacy-history", "claude-code");
const HOOKS_DIR = process.env.DREAMSEED_HOOKS_DIR || path.join(DREAMSEED_DIR, "hooks");
const MEMORY_DIR = process.env.DREAMSEED_MEMORY_DIR || path.join(process.cwd(), ".dreamseed-memory");
const MEMPALACE_MCP_SCRIPT = path.join(ROOT, "scripts", "dreamseed-mempalace-mcp.ps1");
const APPROVAL_GATE_SCRIPT = path.join(ROOT, "scripts", "approval_gate.py");

for (const d of [DREAMSEED_DIR, HISTORY_DIR, CACHE_DIR, LOG_DIR]) {
  try { mkdirSync(d, { recursive: true }); } catch (_) {}
}

const VERSION = "0.2.0";
const args = process.argv.slice(2);
const options = parseArgs(args);
if (options.help) { printHelp(); process.exit(0); }
if (options.version) { console.log(`dreamseed-lite-kernel ${VERSION}`); process.exit(0); }

const baseUrl = normalizeUrl(process.env.ANTHROPIC_BASE_URL || process.env.DREAMSEED_BASE_URL);
const model = options.model || process.env.ANTHROPIC_MODEL || process.env.DREAMSEED_MODEL || "dreamseed-local";
const apiKey = process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_AUTH_TOKEN || process.env.DREAMSEED_API_KEY || "dreamseed-local";
const maxTokens = Number(process.env.DREAMSEED_MAX_TOKENS || 8192);
const contextLimit = Number(process.env.DREAMSEED_CONTEXT_LIMIT || 128000);

if (!baseUrl) {
  console.error("[dreamseed] missing provider endpoint. Set DREAMSEED_PROVIDER_CONFIG or ANTHROPIC_BASE_URL.");
  process.exit(1);
}

// Fix P1 third-round: loadSystemPrompt reads BUILTIN_TOOLS which is defined later in the file.
// Use a lazy getter so the eager const init does not hit a Temporal Dead Zone.
let _systemPromptCache = null;
function getSystemPrompt() {
  if (_systemPromptCache === null) _systemPromptCache = loadSystemPrompt() || "";
  return _systemPromptCache;
}
const mcpClients = new Map();
const sessionId = randomUUID();
const projectDir = process.cwd();
const projectName = path.basename(projectDir) || projectDir.replace(/[\\\/:]/g, "") || "workspace";

const hookScripts = loadHookScripts();
const permissions = loadPermissions();
const agents = loadAgents();
const skills = loadSkills();

let cancellation = null;
let currentSession = null;
let turnCount = 0;
// Fix P5-I: shared readline reference for approval prompts in interactive mode.
let _activeReadline = null;

// Fix P1 third-round: wrap entry in async main() so module-top-level finishes
// initializing all const declarations (BUILTIN_TOOLS at L334, etc.) before
// any awaited work runs. Top-level await would otherwise pause the module
// body and trigger Temporal Dead Zone errors when initMcpClients/runToolLoop
// reference BUILTIN_TOOLS.
async function main() {
  if (options.print) {
    const prompt = options.prompt.length > 0 ? options.prompt.join(" ") : await readStdin();
    const result = await runPrintMode(prompt);
    writeResult(result, options.outputFormat);
  } else {
    await runInteractiveMode();
  }
}
main().catch((error) => {
  // Fix RT-3: structured error NDJSON for json/stream-json/ndjson formats so
  // desktop UI / CI consumers can parse failures without scraping stderr.
  const fmt = (typeof options !== "undefined" && options && options.outputFormat) || "";
  const msg = error && error.message ? error.message : String(error);
  if (fmt === "json" || fmt === "stream-json" || fmt === "ndjson") {
    try {
      console.log(JSON.stringify({ type: "error", error: { type: "kernel_error", message: msg } }));
    } catch (_) {
      console.error(`[dreamseed] ${msg}`);
    }
  } else {
    console.error(`[dreamseed] ${msg}`);
  }
  if (error && error.stack && process.env.DREAMSEED_DEBUG) console.error(error.stack);
  process.exit(1);
});


// Fix #33: structured JSON logging to ~/.dreamseed/logs/kernel.log
function logEvent(level, module, msg, extra) {
  try {
    const entry = JSON.stringify({
      ts: new Date().toISOString(), level, module, msg,
      ...(extra || {}),
    }) + "\n";
    const logFile = path.join(LOG_DIR, "kernel.log");
    appendFileSync(logFile, entry);
    // Rotate if > 10MB
    try {
      const st = statSync(logFile);
      if (st.size > 10 * 1024 * 1024) {
        const rotated = logFile + ".1";
        renameSync(logFile, rotated);
      }
    } catch (_) {}
  } catch (_) {}
}
function logInfo(msg, extra) { logEvent("info", "kernel", msg, extra); }
// Fix P2: atomic JSON write - write to .tmp then rename, so a crash mid-write
// cannot leave a half-written JSON file that will fail to parse next start.
function writeJsonAtomic(filePath, obj) {
  try {
    const tmp = filePath + ".tmp." + process.pid + "." + Math.random().toString(36).slice(2, 8);
    writeFileSync(tmp, typeof obj === "string" ? obj : JSON.stringify(obj, null, 2), "utf8");
    renameSync(tmp, filePath);
    return true;
  } catch (e) {
    return false;
  }
}

function logWarn(msg, extra) { logEvent("warn", "kernel", msg, extra); }
function logError(msg, extra) { logEvent("error", "kernel", msg, extra); }

// Fix #22: SIGINT handler for graceful shutdown
let sigintCount = 0; let _sigintHardTimer = null;
process.on("SIGINT", () => {
  sigintCount++;
  if (sigintCount >= 2) { try { logInfo("second SIGINT - hard exit"); } catch (_) {} process.exit(130); }
    if (sigintCount === 1) {
    try { logInfo("SIGINT received, aborting current turn"); } catch (_) {}
    if (cancellation) try { cancellation.abort(); } catch (_) {}
    // Give in-flight tool/model work a short grace to dispose, then clean up.
    // Fix P6-D: 500ms was too tight for SessionEnd hooks + MCP teardown to
    // complete; raise grace to 3000ms. User can press Ctrl-C twice to force.
    setTimeout(async () => {
      try {
        if (currentSession) {
          await runHooks("SessionEnd", { sessionId, turnCount });
          await shutdownMcpClients();
        }
      } catch (_) {}
      process.exit(130);
    }, 3000);
  } else {
    try { logInfo("Second SIGINT, force exit"); } catch (_) {}
    process.exit(130);
  }
});
process.on("SIGTERM", () => {
  if (cancellation) try { cancellation.abort(); } catch (_) {}
  process.exit(143);
});
process.on("uncaughtException", (err) => {
  try { logError("uncaughtException", { error: err.message, stack: err.stack }); } catch (_) {}
  console.error(`[dreamseed] uncaught: ${err.message}`);
  process.exit(1);
});
process.on("unhandledRejection", (reason) => {
  try { logError("unhandledRejection", { reason: String(reason), stack: reason && reason.stack }); } catch (_) {}
  // Fix P8-18: surface the failure so the user sees it instead of a silently
  // hung process; do not exit because Node's default behaviour will become
  // exit-on-rejection in future versions and we do not want surprise restarts.
  try { console.error(`[dreamseed] unhandledRejection: ${reason && reason.message ? reason.message : reason}`); } catch (_) {}
});

// ===== SSE Streaming Client =====
async function* streamMessages(messages, tools) {
  const body = {
    model, max_tokens: maxTokens, messages,
    system: getSystemPrompt() || undefined,
    stream: true,
  };
  if (tools && tools.length > 0) {
    body.tools = tools;
    body.tool_choice = { type: "auto" };
  }

  const controller = new AbortController();
  if (cancellation) cancellation.register(() => controller.abort());

  let response;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      response = await fetch(`${baseUrl}/v1/messages`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-api-key": apiKey,
          authorization: `Bearer ${apiKey}`,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      // Fix P1: retry on 5xx only; 4xx fail-fast (quota, auth, bad request)
      if (response.status >= 500 && response.status < 600 && attempt < 2) {
        // Fix P4-F: release prior 5xx response body so the keep-alive socket is freed before retry.
        try { await response.text(); } catch (_) {}
        try { await sleep(1000 * (attempt + 1), controller.signal); } catch (_) { throw new Error("aborted"); }
        continue;
      }
      break;
    } catch (err) {
      if (controller.signal.aborted) throw err; // abort takes priority
      if (attempt === 2) throw err;
      try { await sleep(200 * (attempt + 1), controller.signal); } catch (_) { throw err; }
    }
  }

  if (!response.ok) {
    const text = await response.text();
    let detail = text;
    try { detail = JSON.parse(text)?.error?.message || text; } catch (_) {}
    const err = new Error(`provider error (${response.status}): ${detail}`);
    err.statusCode = response.status;
    err.isQuota = response.status === 429;
    if (err.isQuota) err.message = `Quota exceeded (429). The provider reports you have hit a usage limit. Detail: ${detail}`;
    throw err;
  }

  let currentBlock = null;
  const message = { role: "assistant", content: [], usage: { input_tokens: 0, output_tokens: 0 } };
  const textBlocks = [];
  let buffer = "";
  // Fix P6-F: cap SSE buffer so an upstream that never emits a newline cannot exhaust memory.
  const SSE_BUFFER_CAP = 4 * 1024 * 1024;
  // Fix #27: 120s no-new-event watchdog
  let lastEventTime = Date.now();
  const watchdog = setInterval(() => {
    if (Date.now() - lastEventTime > 120000) { try { controller.abort(); } catch (_) {} }
  }, 5000);

  try {
    for await (const chunk of response.body) {
      lastEventTime = Date.now();
      const decoded = new TextDecoder().decode(chunk);
      if (buffer.length + decoded.length > SSE_BUFFER_CAP) buffer = buffer.slice(-Math.floor(SSE_BUFFER_CAP / 2));
      buffer += decoded;
    // Fix #12 #13: handle \r\n and multi-line data fields
    const rawLines = buffer.split("\n");
    buffer = rawLines.pop() || "";
    const events = [];
    let curData = null;
    for (const rl of rawLines) {
      const line = rl.endsWith("\r") ? rl.slice(0, -1) : rl;
      if (line === "") {
        if (curData !== null) { events.push(curData); curData = null; }
        continue;
      }
      if (line.startsWith("data: ")) {
        const d = line.slice(6);
        curData = curData === null ? d : curData + "\n" + d;
      } else if (line.startsWith("data:")) {
        const d = line.slice(5);
        curData = curData === null ? d : curData + "\n" + d;
      }
    }
    if (curData !== null) events.push(curData);

    for (const dataStr of events) {
      if (dataStr === "[DONE]") continue;
      let event;
      try { event = JSON.parse(dataStr); } catch (_) { continue; }

      if (event.type === "message_start") {
        message.id = event.message?.id || message.id;
        message.usage = event.message?.usage || message.usage;
      } else if (event.type === "content_block_start") {
        currentBlock = event.content_block;
        currentBlock._index = event.index;
        if (currentBlock.type === "text") {
          currentBlock.text = "";
          textBlocks.push(currentBlock);
        }
      } else if (event.type === "content_block_delta") {
        if (currentBlock && event.delta?.type === "text_delta") {
          currentBlock.text = (currentBlock.text || "") + (event.delta.text || "");
          // Fix #6: stream to stdout in both print and interactive modes (when not in tool execution)
          if (((options.print && (!options.outputFormat || options.outputFormat === "text")) || (currentSession && currentSession.streamToStdout))) {
            // Fix RT-3: only write streaming text to stdout in text mode.
            // For json/stream-json/ndjson, text is captured into _ndjsonEvents
            // and emitted as structured events by writeResult.
            const _td = event.delta.text || "";
            if (_td) { _textStreamed = true; }
            process.stdout.write(_td);
          }
        } else if (currentBlock && event.delta?.type === "input_json_delta") {
          currentBlock._partialJson = (currentBlock._partialJson || "") + (event.delta.partial_json || "");
        }
      } else if (event.type === "content_block_stop") {
        if (currentBlock) {
          if (currentBlock.type === "tool_use" && currentBlock._partialJson) {
            try { currentBlock.input = JSON.parse(currentBlock._partialJson); } catch (_) { currentBlock.input = {}; }
          }
          message.content.push(currentBlock);
          currentBlock = null;
        }
      } else if (event.type === "message_delta") {
        message.stop_reason = event.delta?.stop_reason || "end_turn";
        message.usage.output_tokens = event.usage?.output_tokens || 0;
      } else if (event.type === "message_stop") {
        yield { type: "message", message };
        return;
      } else if (event.type === "error") {
        throw new Error(event.error?.message || "stream error");
      }
    }
  }

  } finally {
    clearInterval(watchdog);
  }
  // If stream ended without message_stop, yield what we have
  if (message.content.length > 0) {
    message.stop_reason = message.stop_reason || "end_turn";
    yield { type: "message", message };
  }
}

async function sendNonStreaming(messages, tools) {
  const body = {
    model, max_tokens: maxTokens, messages,
    system: getSystemPrompt() || undefined,
    stream: false,
  };
  if (tools && tools.length > 0) {
    body.tools = tools;
    body.tool_choice = { type: "auto" };
  }

  // Fix P1: cancellation + 120s timeout for non-streaming fallback
  const controller = new AbortController();
  if (cancellation) cancellation.register(() => controller.abort());
  const timer = setTimeout(() => { try { controller.abort(); } catch (_) {} }, 120000);

  const response = await fetch(`${baseUrl}/v1/messages`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": apiKey,
      authorization: `Bearer ${apiKey}`,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  }).finally(() => clearTimeout(timer));

  if (!response.ok) {
    const text = await response.text();
    let detail = text;
    try { detail = JSON.parse(text)?.error?.message || text; } catch (_) {}
    throw new Error(`provider error (${response.status}): ${detail}`);
  }

  return await response.json();
}


// ===== Tool Registry =====
const BUILTIN_TOOLS = {
  read: {
    name: "Read", description: "Read a file from the local filesystem.",
    category: "readonly",
    input_schema: {
      type: "object", properties: {
        file_path: { type: "string", description: "Absolute path to the file" },
        offset: { type: "number", description: "Line number to start reading from" },
        limit: { type: "number", description: "Maximum number of lines to read" },
      }, required: ["file_path"]
    },
    async execute(input) {
      const fp = input.file_path || input.image_path;
      if (!fp) return { content: "file_path is required", is_error: true };
      if (!existsSync(fp)) return { content: `File not found: ${fp}`, is_error: true };
      try {
        const stat = await fsStat(fp);
        if (stat.size > 10 * 1024 * 1024) return { content: `[binary file, ${stat.size} bytes]`, is_error: false };
        const raw = readFileSync(fp, "utf8");
        const lines = raw.split(/\r?\n/);
        const start = Math.max(0, (input.offset || 1) - 1);
        const end = input.limit ? start + input.limit : Math.min(start + 2000, lines.length);
        const selected = lines.slice(start, end);
        const numbered = selected.map((l, i) => `${start + i + 1}: ${l}`).join("\n");
        return { content: numbered || "(empty file)", is_error: false };
      } catch (e) {
        return { content: `Read error: ${e.message}`, is_error: true };
      }
    }
  },
  write: {
    name: "Write", description: "Write a file to the local filesystem.",
    category: "mutating",
    input_schema: {
      type: "object", properties: {
        file_path: { type: "string", description: "Absolute path to the file" },
        content: { type: "string", description: "Content to write" },
      }, required: ["file_path", "content"]
    },
    async execute(input) {
      const fp = input.file_path;
      if (!fp) return { content: "file_path is required", is_error: true };
      if (!isPathSafe(fp)) return { content: `Path not allowed: ${fp}`, is_error: true };
      try {
        mkdirSync(path.dirname(fp), { recursive: true });
        const tmp = fp + ".tmp." + randomUUID().slice(0, 8);
        writeFileSync(tmp, String(input.content || ""), "utf8");
        await rename(tmp, fp);
        return { content: `Wrote ${input.content.length} bytes to ${fp}`, is_error: false };
      } catch (e) {
        return { content: `Write error: ${e.message}`, is_error: true };
      }
    }
  },
  edit: {
    name: "Edit", description: "Make targeted edits to a file.",
    category: "mutating",
    input_schema: {
      type: "object", properties: {
        file_path: { type: "string", description: "Absolute path to the file" },
        old_string: { type: "string", description: "Text to replace" },
        new_string: { type: "string", description: "Replacement text" },
        replace_all: { type: "boolean", description: "Replace all occurrences" },
      }, required: ["file_path", "old_string", "new_string"]
    },
    async execute(input) {
      const fp = input.file_path;
      if (!fp || !existsSync(fp)) return { content: `File not found: ${fp}`, is_error: true };
      try {
        const raw = readFileSync(fp, "utf8");
        // Fix P4-B: tolerate CRLF/LF mismatch. If exact old_string is not found
        // in raw but appears with the file's actual line ending, retry with that.
        let oldStr = input.old_string;
        let newStr = input.new_string;
        const fileHasCRLF = raw.includes("\r\n");
        const oldHasCR = oldStr.includes("\r");
        if (fileHasCRLF && !oldHasCR && !raw.includes(oldStr)) {
          oldStr = oldStr.replace(/\n/g, "\r\n");
          newStr = newStr.replace(/\n/g, "\r\n");
        } else if (!fileHasCRLF && oldHasCR && !raw.includes(oldStr)) {
          oldStr = oldStr.replace(/\r\n/g, "\n");
          newStr = newStr.replace(/\r\n/g, "\n");
        }
        // Count by literal substring scan (not regex) so special chars are safe.
        let count = 0;
        let scan = 0;
        while (true) {
          const idx = raw.indexOf(oldStr, scan);
          if (idx < 0) break;
          count++;
          scan = idx + oldStr.length;
        }
        if (count === 0) return { content: "old_string not found in file", is_error: true };
        if (count > 1 && !input.replace_all) return { content: `old_string found ${count} times; use replace_all:true`, is_error: true };
        // Fix P4-A: split/join is literal-safe. Avoid String.prototype.replace which
        // interprets $&, $1, $` and $' in the replacement.
        const replaced = input.replace_all
          ? raw.split(oldStr).join(newStr)
          : (() => { const i = raw.indexOf(oldStr); return raw.slice(0, i) + newStr + raw.slice(i + oldStr.length); })();
        const tmp = fp + ".tmp." + randomUUID().slice(0, 8);
        writeFileSync(tmp, replaced, "utf8");
        await rename(tmp, fp);
        return { content: `Replaced ${input.replace_all ? count : 1} occurrence(s) in ${fp}`, is_error: false };
      } catch (e) {
        return { content: `Edit error: ${e.message}`, is_error: true };
      }
    }
  },
  glob: {
    name: "Glob", description: "Find files matching a glob pattern.",
    category: "readonly",
    input_schema: {
      type: "object", properties: {
        pattern: { type: "string", description: "Glob pattern" },
        path: { type: "string", description: "Directory to search in" },
      }, required: ["pattern"]
    },
    async execute(input) {
      const cwd = input.path || projectDir;
      const pattern = input.pattern;
      try {
        const results = await globSearch(cwd, pattern);
        return { content: results.slice(0, 100).join("\n") || "(no matches)", is_error: false };
      } catch (e) {
        return { content: `Glob error: ${e.message}`, is_error: true };
      }
    }
  },
  grep: {
    name: "Grep", description: "Search for a pattern in files.",
    category: "readonly",
    input_schema: {
      type: "object", properties: {
        pattern: { type: "string", description: "Regex pattern to search for" },
        path: { type: "string", description: "Directory or file to search in" },
        include: { type: "string", description: "File pattern to include" },
      }, required: ["pattern"]
    },
    async execute(input) {
      const cwd = input.path || projectDir;
      try {
        const results = await grepSearch(cwd, input.pattern, input.include);
        return { content: results.slice(0, 100).join("\n") || "(no matches)", is_error: false };
      } catch (e) {
        return { content: `Grep error: ${e.message}`, is_error: true };
      }
    }
  },
  bash: {
    name: "Bash", description: "Execute a shell command.",
    category: "mutating",
    input_schema: {
      type: "object", properties: {
        command: { type: "string", description: "Shell command to execute" },
        timeout: { type: "number", description: "Timeout in milliseconds" },
        background: { type: "boolean", description: "Run in background and return PID" },
      }, required: ["command"]
    },
    async execute(input) {
      const cmd = String(input.command || "").trim();
      if (!cmd) return { content: "command is required", is_error: true };
      if (isDangerousCommand(cmd)) return { content: `Command blocked for safety: ${cmd}`, is_error: true };
      if (input.background) {
        try {
          const _bgShell = process.env.DREAMSEED_SHELL || "powershell.exe";
          const _bgIsPwsh = _bgShell.includes("powershell");
          const _bgCmd = _bgIsPwsh ? cmd.replace(/&&/g, ";") : cmd;
          const child = spawn(_bgShell,
            _bgIsPwsh ? ["-NoProfile","-Command",_bgCmd] : ["-c",_bgCmd],
            { cwd: projectDir, env: process.env, stdio: "ignore", detached: true, windowsHide: true });
          child.unref();
          return { content: `Background process started (PID: ${child.pid})`, is_error: false };
        } catch (e) { return { content: `Background spawn error: ${e.message}`, is_error: true }; }
      }
      try {
        const result = await runShell(cmd, input.timeout || 120000);
        return { content: result, is_error: false };
      } catch (e) {
        return { content: `Bash error: ${e.message}`, is_error: true };
      }
    }
  },
  todoWrite: {
    name: "TodoWrite", description: "Create and manage a task list.",
    category: "mutating",
    input_schema: {
      type: "object", properties: {
        todos: { type: "array", items: { type: "object", properties: {
          content: { type: "string" }, status: { type: "string", enum: ["pending", "in_progress", "completed"] },
          priority: { type: "string", enum: ["high", "medium", "low"] }
        }, required: ["content", "status"] } }
      }, required: ["todos"]
    },
    async execute(input) {
      const todosDir = path.join(DREAMSEED_DIR, "state");
      mkdirSync(todosDir, { recursive: true });
      const fp = path.join(todosDir, "todos.json");
      writeJsonAtomic(fp, { todos: input.todos, updated: new Date().toISOString() });
      const counts = { pending: 0, in_progress: 0, completed: 0 };
      for (const t of input.todos) { counts[t.status] = (counts[t.status] || 0) + 1; }
      return { content: `Todo list updated: ${counts.pending} pending, ${counts.in_progress} in progress, ${counts.completed} completed`, is_error: false };
    }
  },
  webFetch: {
    name: "WebFetch", description: "Fetch content from a URL.",
    category: "readonly",
    input_schema: {
      type: "object", properties: {
        url: { type: "string", description: "URL to fetch" },
      }, required: ["url"]
    },
    async execute(input) {
      const url = input.url;
      if (!url) return { content: "url is required", is_error: true };
      if (!/^https?:\/\//i.test(url)) return { content: "Only http/https URLs are allowed", is_error: true };
      try {
        const resp = await fetch(url, { signal: AbortSignal.timeout(Number(process.env.DREAMSEED_WEBFETCH_TIMEOUT || 15000)), redirect: "follow" });
        const raw = await resp.text();
        // Fix #25: strip HTML tags, extract text
        let text = raw;
        const ct = (resp.headers.get("content-type") || "").toLowerCase();
        if (ct.includes("html") || /<\s*(html|body|head|script|div)[^>]*>/i.test(text)) {
          text = text
            .replace(/<script[\s\S]*?<\/script>/gi, "")
            .replace(/<style[\s\S]*?<\/style>/gi, "")
            .replace(/<noscript[\s\S]*?<\/noscript>/gi, "")
            .replace(/<(br|hr|p|div|h[1-6]|li|tr)[^>]*>/gi, "\n")
            .replace(/<[^>]+>/g, " ")
            .replace(/&nbsp;/gi, " ")
            .replace(/&amp;/gi, "&")
            .replace(/&lt;/gi, "<")
            .replace(/&gt;/gi, ">")
            .replace(/&quot;/gi, '"')
            .replace(/&#39;/gi, "'")
            .replace(/[ \t]+/g, " ")
            .replace(/\n{3,}/g, "\n\n")
            .trim();
        }
        const truncated = text.slice(0, 50000);
        return { content: truncated + (text.length > 50000 ? "\n...(truncated)" : ""), is_error: false };
      } catch (e) {
        return { content: `WebFetch error: ${e.message}`, is_error: true };
      }
    }
  },
  webSearch: {
    name: "WebSearch", description: "Search the web.",
    category: "readonly",
    input_schema: {
      type: "object", properties: {
        query: { type: "string", description: "Search query" },
      }, required: ["query"]
    },
    async execute(input) {
      const backend = process.env.DREAMSEED_WEB_SEARCH_BACKEND;
      const query = input.query || "";
      if (!backend) {
        return { content: `Web search is not configured. Set DREAMSEED_WEB_SEARCH_BACKEND. Query: ${query}`, is_error: true };
      }
      try {
        if (backend.startsWith("http")) {
          const resp = await fetch(`${backend}?q=${encodeURIComponent(query)}`, { signal: AbortSignal.timeout(20000), headers: { "accept": "application/json" } });
          const data = await resp.json();
          const results = (data.results || data.items || []).slice(0, 10).map((r, i) => `${i+1}. ${r.title || ""} - ${r.url || r.link || ""}\n${(r.snippet || r.content || "").slice(0, 200)}`).join("\n\n");
          return { content: results || "(no results)", is_error: false };
        }
        return { content: `Unknown web search backend: ${backend}`, is_error: true };
      } catch (e) {
        return { content: `WebSearch error: ${e.message}`, is_error: true };
      }
    }
  },
  task: {
    name: "Task", description: "Launch a subagent to handle a task.",
    category: "mutating",
    input_schema: {
      type: "object", properties: {
        description: { type: "string", description: "Short description of the task" },
        prompt: { type: "string", description: "Task for the subagent" },
        subagent_type: { type: "string", description: "Type of subagent" },
      }, required: ["description", "prompt"]
    },
    async execute(input) {
      const parentDepth = currentSession?.subagentDepth || 0;
      if (parentDepth >= 3) {
        return { content: "Maximum subagent depth (3) reached", is_error: true };
      }
      try {
        const subMsgs = [
          { role: "user", content: input.prompt }
        ];
        const subDepth = parentDepth + 1;
        // Fix P9-L: persist subDepth into currentSession so nested Task calls
        // actually see the incremented depth instead of always reading 0.
        const savedDepth = currentSession?.subagentDepth;
        if (currentSession) currentSession.subagentDepth = subDepth;
        let subResult;
        try {
          subResult = await runToolLoop(subMsgs, input.subagent_type, subDepth);
        } finally {
          if (currentSession) currentSession.subagentDepth = savedDepth;
        }
        await runHooks("SubagentStop", { sessionId, subagentType: input.subagent_type, subDepth, subResult: subResult?.slice(0, 500), turnCount });
        return { content: subResult, is_error: false };
      } catch (e) {
        return { content: `Subagent error: ${e.message}`, is_error: true };
      }
    }
  },
  exitPlanMode: {
    name: "ExitPlanMode", description: "Exit plan mode and return to regular mode.",
    category: "readonly",
    input_schema: {
      type: "object", properties: {
        plan: { type: "string", description: "Summary of the plan created" },
      }, required: ["plan"]
    },
    async execute(input) {
      return { content: `Plan mode exited. Plan: ${input.plan || "(no plan summary)"}`, is_error: false };
    }
  },
};

// Fix #1: case-insensitive tool name lookup that handles camelCase keys
const BUILTIN_TOOLS_BY_NAME = {};
for (const _key of Object.keys(BUILTIN_TOOLS)) {
  const _t = BUILTIN_TOOLS[_key];
  if (_t && _t.name) BUILTIN_TOOLS_BY_NAME[_t.name] = _t;
}
function lookupBuiltinTool(name) {
  if (!name) return null;
  if (BUILTIN_TOOLS_BY_NAME[name]) return BUILTIN_TOOLS_BY_NAME[name];
  const lc = String(name).toLowerCase();
  for (const _k of Object.keys(BUILTIN_TOOLS_BY_NAME)) {
    if (_k.toLowerCase() === lc) return BUILTIN_TOOLS_BY_NAME[_k];
  }
  for (const _k of Object.keys(BUILTIN_TOOLS)) {
    if (_k.toLowerCase() === lc) return BUILTIN_TOOLS[_k];
  }
  return null;
}

function getToolDefinitions() {
  const defs = Object.values(BUILTIN_TOOLS).map(t => ({
    name: t.name, description: t.description, input_schema: t.input_schema
  }));
  for (const [name, client] of mcpClients) {
    if (client.tools) {
      for (const tool of client.tools) {
        defs.push({ name: `mcp__${name}__${tool.name}`, description: tool.description || `MCP tool from ${name}`, input_schema: tool.inputSchema || { type: "object", properties: {} } });
      }
    }
  }
  return defs;
}

async function executeTool(name, input) {
  const builtin = lookupBuiltinTool(name);
  if (builtin) return await builtin.execute(input);

  if (name.startsWith("mcp__")) {
    const parts = name.split("__");
    const serverName = parts[1];
    const toolName = parts.slice(2).join("__");
    const client = mcpClients.get(serverName);
    if (!client) return { content: `MCP server ${serverName} not found`, is_error: true };
    try {
      const result = await client.callTool(toolName, input);
      return { content: typeof result === "string" ? result : JSON.stringify(result), is_error: false };
    } catch (e) {
      return { content: `MCP tool error: ${e.message}`, is_error: true };
    }
  }

  return { content: `Unknown tool: ${name}`, is_error: true };
}


// Fix P2: context trimmer - trim old tool_result content before each API call
function trimContext(messages) {
  // Fix P5-G: return a request-only trimmed copy, never mutate the caller's array
  // or the per-message content blocks. Persistence and /resume rely on the originals.
  const keepFull = 3;
  // Walk backwards once to find which messages are "recent" enough to keep verbatim.
  let asstSeen = 0;
  const verbatimFlags = new Array(messages.length).fill(true);
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === "assistant") asstSeen++;
    if (asstSeen > keepFull) verbatimFlags[i] = false;
  }
  const out = new Array(messages.length);
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i];
    if (verbatimFlags[i] || m.role !== "user" || !Array.isArray(m.content)) {
      out[i] = m;
      continue;
    }
    let mutated = false;
    let newContent = null;
    for (let bi = 0; bi < m.content.length; bi++) {
      const b = m.content[bi];
      if (b && b.type === "tool_result" && typeof b.content === "string" && b.content.length > 500) {
        if (!mutated) { newContent = m.content.slice(); mutated = true; }
        const lineCount = (b.content.match(/\n/g) || []).length + 1;
        newContent[bi] = { ...b, content: "[tool succeeded, original output was " + lineCount + " lines, truncated]" };
      }
    }
    out[i] = mutated ? { ...m, content: newContent } : m;
  }
  return out;
}

// ===== Tool Loop =====
async function runToolLoop(messages, agentType, depth) {
  const maxTurns = options.maxTurns || 100;
  const tools = getToolDefinitions();
  let finalText = "";
  let autoCompactedThisLoop = false;
  // Fix P2-4 third-round: scope failure-detection queue per invocation so subagents do not pollute parent.
  const localFailureQueue = [];
      const localToolBlacklist = new Set();

  // Fix P5-G: trimContext used to mutate messages in place, but the same array is
  // later persisted by saveSessionMessages. That meant every long session permanently
  // lost its older tool_result content on disk and on next /resume. Now we build a
  // request-only trimmed view, send THAT to the model, and keep the caller's array intact.
  // (assigned below into requestMessages on each turn)

  _textStreamed = false;  // Fix P8-1: reset per-invocation so prior text-streamed state does not leak across turns
  for (let turn = 0; turn < maxTurns; turn++) {
    turnCount++;
    // Fix P1: cancellation stack - save previous to restore after subagent
    const prevCancellation = cancellation;
    cancellation = new CancellationManager();
    try {
    let message;
    try {
      // Fix P5-G: send a trimmed copy to the model; never mutate persistent messages.
      const requestMessages = trimContext(messages);
      const stream = streamMessages(requestMessages, tools);
      for await (const event of stream) {
        if (event.type === "message") {
          message = event.message;
        }
      }
    } catch (err) {
      if (err.isQuota) {
        return `Quota exceeded: ${err.message}`;
      }
      if (turn === 0) throw err;
      return `Error after ${turn} turns: ${err.message}`;
    }

    if (!message) return "No response from model";

    messages.push({ role: "assistant", content: message.content });

    // Fix #15: auto-compact if context grows large
    if (!autoCompactedThisLoop && messages.length > 40) {
      const tk = estimateTokens(messages);
      if (tk > contextLimit * 0.8) {
        const compacted = await compactMessages(messages, "auto");
        messages.length = 0;
        messages.push(...compacted);
        autoCompactedThisLoop = true;
        if (!options.print) console.error(`[dreamseed] auto-compacted to ~${estimateTokens(messages)} tokens`);
      }
    }

    const toolUses = (message.content || []).filter(b => b.type === "tool_use");
    const textBlocks = (message.content || []).filter(b => b.type === "text");

    // Fix #34 + P7-M: record events for stream-json output, only at the top
    // level. Subagent (depth>0) text / tool_use / tool_result events stay
    // private so the parent NDJSON stream is not polluted.
    const isStreamJson = (options.outputFormat === "stream-json" || options.outputFormat === "ndjson" || options.outputFormat === "json") && depth === 0;
    if (isStreamJson) {
      // Fix P10-A: stream NDJSON events immediately so the desktop UI can
      // render tool cards in real time, instead of buffering until the run
      // finishes. The trailing result event is still emitted by writeResult.
      for (const tb of textBlocks) {
        if (tb.text) emitNdjson({ type: "text", content: tb.text });
      }
      for (const tu of toolUses) {
        emitNdjson({ type: "tool_use", id: tu.id, name: tu.name, input: tu.input });
      }
    }

    if (textBlocks.length > 0) {
      finalText = textBlocks.map(b => b.text || "").join("\n");
    }

    if (toolUses.length === 0) {
      return finalText || "(no response)";
    }

    // Execute tools with proper isolation
    const toolResults = [];
    const readonlyTools = toolUses.filter(t => {
      const def = lookupBuiltinTool(t.name);
      return def?.category === "readonly";
    });
    const mutatingTools = toolUses.filter(t => {
      const def = lookupBuiltinTool(t.name);
      return def?.category !== "readonly";
    });

    // Run readonly tools in parallel
    if (readonlyTools.length > 0) {
      const results = await Promise.allSettled(
        readonlyTools.map(t => executeToolSafely(t, localToolBlacklist))
      );
      for (let i = 0; i < readonlyTools.length; i++) {
        toolResults.push({
          tool_use_id: readonlyTools[i].id,
          type: "tool_result",
          content: results[i].status === "fulfilled" ? results[i].value.content : `Error: ${results[i].reason?.message}`,
          is_error: results[i].status === "rejected" || results[i].value?.is_error,
        });
      }
    }

    // Run mutating tools sequentially
    for (const tool of mutatingTools) {
      const result = await executeToolSafely(tool, localToolBlacklist);
      toolResults.push({
        tool_use_id: tool.id,
        type: "tool_result",
        content: result.content,
        is_error: result.is_error,
      });
    }

    // Check for repeated failures and feed a corrective hint back to the model
    const _repeated = checkRepeatedFailures(toolUses, toolResults, localFailureQueue);
    if (_repeated && _repeated.length > 0) {
      const hint = _repeated.map(r => `Tool ${r.name} has now failed 3 times with the same input. Last error: ${r.error}. Please change your approach.`).join("\n");
      messages.push({ role: "user", content: hint });
      // Fix P11-B: blacklist these (tool,input) so the very next turn cannot retry them.
      for (const r of _repeated) {
        const tu = toolUses.find(t => t.name === r.name);
        if (tu) localToolBlacklist.add(_toolKey(tu.name, tu.input || {}));
      }
    }

    // Fix #34 + P7-M: record tool_result events only at the top level.
    if ((options.outputFormat === "stream-json" || options.outputFormat === "ndjson" || options.outputFormat === "json") && depth === 0) {
      // Fix P10-A: stream tool_result events immediately too.
      for (const tr of toolResults) {
        emitNdjson({ type: "tool_result", tool_use_id: tr.tool_use_id, content: tr.content, is_error: tr.is_error });
      }
    }
    // Fix P2: Stop hook after tool execution
    await runHooks("Stop", { sessionId, turnCount, toolResults: toolResults.map(t => ({ name: t.tool_use_id, is_error: t.is_error })) });
    for (const tr of toolResults) {
      messages.push({ role: "user", content: [tr] });
    }

    } finally {
      // Fix P1: restore parent cancellation on ALL paths (return/throw/continue)
      cancellation = prevCancellation;
    }
  }

  return finalText || "(max turns reached)";
}

async function executeToolSafely(toolUse, _blacklist) {
  try {
    // Fix P11-B: skip immediately if this exact (tool, input) was marked as repeatedly failing.
    if (_blacklist && _blacklist.has(_toolKey(toolUse.name, toolUse.input || {}))) {
      return { content: `Skipped ${toolUse.name}: this exact input failed 3 times in this session. Try a different approach.`, is_error: true };
    }
    // Fix #2: Permission check before execution
    const permDecision = checkPermission(toolUse.name, toolUse.input || {});
    if (permDecision === "deny") {
      return { content: `Permission denied for ${toolUse.name}`, is_error: true };
    }
    if (permDecision === "ask" && !process.env.DREAMSEED_AUTO_APPROVE) {
      // Fix P11-A: risk-aware auto-approve for --print mode using approval.policy.json.
      if (options.print) {
        const _risk = classifyToolRisk(toolUse.name, toolUse.input || {});
        if (_risk === "low" || _risk === "medium") {
          await runHooks("PreToolUse", { toolName: toolUse.name, toolInput: toolUse.input || {}, sessionId, turnCount });
          const _r = await executeTool(toolUse.name, toolUse.input || {});
          await runHooks("PostToolUse", { toolName: toolUse.name, toolInput: toolUse.input || {}, result: _r, sessionId, turnCount });
          return _r;
        }
      }
      // Fix P2: PermissionRequest hook (allow user-defined hook to decide)
      try {
        const hookResult = await runHooks("PermissionRequest", { toolName: toolUse.name, toolInput: toolUse.input || {}, sessionId, turnCount });
        if (hookResult && hookResult.permissionDecision === "allow") {
          await runHooks("PreToolUse", { toolName: toolUse.name, toolInput: toolUse.input || {}, sessionId, turnCount });
          const r = await executeTool(toolUse.name, toolUse.input || {});
          await runHooks("PostToolUse", { toolName: toolUse.name, toolInput: toolUse.input || {}, result: r, sessionId, turnCount });
          return r;
        }
        if (hookResult && hookResult.permissionDecision === "deny") {
          return { content: `PermissionRequest hook denied ${toolUse.name}`, is_error: true };
        }
      } catch (_) {}
      // In non-interactive mode, deny; in interactive, would prompt
      if (!options.print && input.isTTY) {
        // Fix P5-I: reuse the main-loop readline to avoid two readers fighting for stdin.
        const rlForApproval = _activeReadline || createInterface({ input, output });
        const answer = await rlForApproval.question(`[approval] ${toolUse.name} - allow? (y/N): `);
        if (rlForApproval !== _activeReadline) try { rlForApproval.close(); } catch (_) {}
        if (answer.trim().toLowerCase() !== "y") {
          return { content: `User denied ${toolUse.name}`, is_error: true };
        }
      } else {
        return { content: `Permission required for ${toolUse.name}: this is a high-risk action and --print is non-interactive. Run dreamseed in interactive terminal mode to approve, or set DREAMSEED_AUTO_APPROVE=1 in the parent shell before launching dreamseed (it must be a parent env var, not "set X=1 && ..." inside Bash).`, is_error: true };
      }
    }
    // Fix P2: PreToolUse/PostToolUse hooks
    await runHooks("PreToolUse", { toolName: toolUse.name, toolInput: toolUse.input || {}, sessionId, turnCount });
    const result = await executeTool(toolUse.name, toolUse.input || {});
    await runHooks("PostToolUse", { toolName: toolUse.name, toolInput: toolUse.input || {}, result, sessionId, turnCount });
    return result;
  } catch (err) {
    return { content: `Tool execution error: ${err.message}`, is_error: true };
  }
}


// Fix P11-A: load approval.policy.json risk classes for print-mode auto-approve.
let _approvalPolicyCache = null;
function loadApprovalPolicy() {
  if (_approvalPolicyCache !== null) return _approvalPolicyCache;
  try {
    const root = process.env.DREAMSEED_ROOT || path.dirname(path.dirname(process.argv[1] || ""));
    const candidates = [
      path.join(root, "config", "approval.policy.json"),
      path.join(DREAMSEED_DIR, "..", "config", "approval.policy.json"),
    ];
    for (const cp of candidates) {
      if (existsSync(cp)) {
        const txt = readFileSync(cp, "utf8").replace(/^\uFEFF/, "");
        _approvalPolicyCache = JSON.parse(txt);
        return _approvalPolicyCache;
      }
    }
  } catch (_) { /* ignore */ }
  _approvalPolicyCache = false;
  return _approvalPolicyCache;
}
function classifyToolRisk(toolName, input) {
  const pol = loadApprovalPolicy();
  if (!pol) return null;
  const low = pol.lowRiskTools || [];
  const med = pol.mediumRiskTools || [];
  const high = pol.highRiskTools || [];
  if (low.includes(toolName)) return "low";
  if (med.includes(toolName)) return "medium";
  if (toolName === "Bash" || toolName === "Shell") {
    const cmd = (input && (input.command || input.cmd)) || "";
    const safe = (pol.safeShellPatterns || []).some(p => { try { return new RegExp(p).test(cmd); } catch { return false; } });
    if (safe) return "low";
    const ask = (pol.askShellPatterns || []).some(p => { try { return new RegExp(p).test(cmd); } catch { return false; } });
    if (ask) return "high";
    return "medium";
  }
  if (high.includes(toolName)) return "high";
  return null;
}

// Fix P11-B: tool-input blacklist per turn loop, populated by checkRepeatedFailures.
function _toolKey(name, input) { return `${name}:${JSON.stringify(input || {})}`; }

function checkPermission(toolName, input) {
  if (!permissions) return "allow";
  // Check deny patterns first
  for (const pattern of permissions.deny || []) {
    if (matchesPermissionPattern(pattern, toolName, input)) return "deny";
  }
  // Check allow patterns
  for (const pattern of permissions.allow || []) {
    if (matchesPermissionPattern(pattern, toolName, input)) return "allow";
  }
  return permissions.defaultMode || "ask";
}

function matchesPermissionPattern(pattern, toolName, input) {
  // Pattern: "Read" matches Read tool
  // Pattern: "Bash(git status:*)" matches Bash with git status prefix
  // Pattern: "!Bash(rm -rf:*)" is handled by deny list
  // In deny list, "!Tool(...)" means "deny everything EXCEPT this pattern"
  if (pattern.startsWith("!")) {
    const inner = pattern.slice(1);
    const m2 = inner.match(/^(\w+)(?:\((.+)\))?$/);
    if (!m2) return false;
    if (m2[1].toLowerCase() !== toolName.toLowerCase()) return true; // different tool -> deny
    if (!m2[2]) return false; // matches this exact tool -> exempt
    const cmdStr2 = typeof input === "object" ? (input.command || JSON.stringify(input)) : String(input);
    const prefix2 = m2[2].split(":")[0].trim();
    if (prefix2 === "*") return false;
    // Fix P8-9: token-aware match for negated patterns too.
    const cmdT = cmdStr2.toLowerCase().split(/\s+/).filter(Boolean);
    const prefT = prefix2.toLowerCase().split(/\s+/).filter(Boolean);
    if (prefT.length === 0) return true;
    if (cmdT.length < prefT.length) return true;
    for (let i = 0; i < prefT.length; i++) {
      if (cmdT[i] !== prefT[i]) return true;
    }
    return false;
  }
  const m = pattern.match(/^(\w+)(?:\((.+)\))?$/);
  if (!m) return false;
  const ptool = m[1];
  if (ptool.toLowerCase() !== toolName.toLowerCase()) return false;
  if (!m[2]) return true; // matches any usage of this tool
  // Check command prefix for Bash
  const cmdStr = typeof input === "object" ? (input.command || JSON.stringify(input)) : String(input);
  const parts = m[2].split(":");
  const prefix = parts[0].trim();
  if (prefix === "*") return true;
  // Fix P8-9: token-aware prefix match. "Bash(git:*)" must match "git push"
  // but NOT "github-cli push"; "Bash(git status:*)" must match "git status -sb"
  // but not "git stash". Compare token-by-token using the first prefix tokens.
  const cmdTokens = cmdStr.toLowerCase().split(/\s+/).filter(Boolean);
  const prefTokens = prefix.toLowerCase().split(/\s+/).filter(Boolean);
  if (prefTokens.length === 0) return false;
  if (cmdTokens.length < prefTokens.length) return false;
  for (let i = 0; i < prefTokens.length; i++) {
    if (cmdTokens[i] !== prefTokens[i]) return false;
  }
  return true;
}

// Fix P2-4 third-round: per-runToolLoop failure queue. Module-level stub kept only so
// legacy /clear handler stays harmless when no loop is active.
const recentToolResults = [];
function checkRepeatedFailures(toolUses, results, queue) {
  // Fix P2-G: also report repeated failures so caller can inject a system hint to the model.
  const repeated = [];
  for (let i = 0; i < toolUses.length; i++) {
    const tool = toolUses[i];
    const result = results[i];
    if (!result || !result.is_error) continue;
    const key = `${tool.name}:${JSON.stringify(tool.input || {})}`;
    const q = queue || recentToolResults;
    q.push({ key, error: result.content, time: Date.now() });
    if (q.length > 20) q.shift();
    const recent = q.filter(r => r.key === key);
    if (recent.length >= 3) {
      console.error(`[dreamseed] tool ${tool.name} failed 3 times with same input: ${recent[0].error}`);
      repeated.push({ name: tool.name, error: String(recent[0].error || "").slice(0, 300) });
      // Reset so the same warning is not emitted on every subsequent turn.
      while (true) {
        const idx = q.findIndex(r => r.key === key);
        if (idx === -1) break;
        q.splice(idx, 1);
      }
    }
  }
  return repeated;
}


// ===== MCP Client =====
async function initMcpClients() {
  if (!existsSync(MCP_CONFIG)) return;
  try {
    const config = JSON.parse(readFileSync(MCP_CONFIG, "utf8").replace(/^\uFEFF/, ""));
    const servers = config.mcpServers || {};
    for (const [name, server] of Object.entries(servers)) {
      try {
        const client = await startMcpServer(name, server);
        if (client) mcpClients.set(name, client);
      } catch (err) {
        console.error(`[dreamseed] MCP server ${name} failed to start: ${err.message}`);
      }
    }
  } catch (err) {
    console.error(`[dreamseed] failed to load MCP config: ${err.message}`);
  }
}

async function startMcpServer(name, config) {
  if (config.type === "stdio") {
    const cmd = config.command;
    const args = config.args || [];
    const env = { ...process.env, ...(config.env || {}) };
    const child = spawn(cmd, args, { env, stdio: ["pipe", "pipe", "pipe"], shell: false, windowsHide: true });
    const client = {
      name, child,
      tools: [],
      async callTool(toolName, args) { return null; /* overridden after init */ }
    };

    try { child.stdout.setEncoding("utf8"); } catch (_) {}
    // Fix #4 #5: Buffered NDJSON stdout reader
    let stdoutBuf = "";
    const responseHandlers = new Map(); // id -> {resolve, reject, timer}
    // Fix P5-F + P6-B: cap the line buffer so a misbehaving server that never
    // sends a newline cannot grow memory unbounded. When we hit the cap we keep
    // only the data after the last newline so we never break a half-received
    // JSON-RPC frame in the middle.
    child.stdout.on("data", (chunk) => {
      stdoutBuf += chunk.toString("utf8");
      if (stdoutBuf.length > 8 * 1024 * 1024) {
        const lastNl = stdoutBuf.lastIndexOf("\n");
        if (lastNl > 0) {
          stdoutBuf = stdoutBuf.slice(lastNl + 1);
        } else {
          // No newline at all in 8 MB - this server is broken; reset and warn.
          stdoutBuf = "";
          try { logWarn("MCP stdout buffer overflow without newline", { name }); } catch (_) {}
        }
      }
      let nl;
      while ((nl = stdoutBuf.indexOf("\n")) >= 0) {
        const line = stdoutBuf.slice(0, nl).trim();
        stdoutBuf = stdoutBuf.slice(nl + 1);
        if (!line) continue;
        let msg;
        try { msg = JSON.parse(line); } catch (_) { continue; }
        if (msg.id !== undefined && responseHandlers.has(msg.id)) {
          const h = responseHandlers.get(msg.id);
          responseHandlers.delete(msg.id);
          clearTimeout(h.timer);
          if (msg.error) h.reject(new Error(msg.error.message || "MCP error"));
          else h.resolve(msg.result);
        }
        // Notifications without id are ignored (server-sent log etc.)
      }
    });
    child.stderr.on("data", (chunk) => { /* swallow stderr */ });

    // Fix P5-A/B/C/F: harden rpcCall. Dead clients fail fast, stdin.write is
    // guarded so a crashed child throws a clean reject instead of leaking out
    // of the Promise boundary, and the id counter starts at 1 to avoid the
    // reserved 9001/9002 init ids (P5-D).
    function rpcCall(id, method, params, timeoutMs) {
      return new Promise((resolve, reject) => {
        if (client._dead) { reject(new Error(`MCP ${name} is dead`)); return; }
        const timer = setTimeout(() => {
          responseHandlers.delete(id);
          reject(new Error(`MCP ${method} timeout`));
        }, timeoutMs || 30000);
        responseHandlers.set(id, { resolve, reject, timer });
        try {
          child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
        } catch (e) {
          clearTimeout(timer);
          responseHandlers.delete(id);
          reject(new Error(`MCP ${method} write failed: ${e.message}`));
        }
      });
    }

    // Override callTool to use buffered reader (fix #4)
    client.callTool = async function(toolName, args2) {
      const id = client._nextId = (client._nextId || 0) + 1;
      try {
        const result = await rpcCall(id, "tools/call", { name: toolName, arguments: args2 }, 60000);
        return result?.content?.[0]?.text || (typeof result === "string" ? result : JSON.stringify(result));
      } catch (e) {
        throw e;
      }
    };

    // Initialize (fix #3 #4)
    try {
      // Fix P4-E: 5s was too tight for cold MCP servers (PowerShell, node); 15s is the upstream MCP recommended ceiling.
      await rpcCall(1, "initialize", { protocolVersion: "2024-11-05", capabilities: {}, clientInfo: { name: "dreamseed", version: VERSION } }, 15000);
    } catch (e) {
      console.error(`[dreamseed] MCP ${name} initialize failed: ${e.message}`);
      try { child.kill(); } catch (_) {}
      return null;
    }

    // Fix #3: Send initialized notification (no id, no response expected)
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized", params: {} }) + "\n");

    // List tools (fix #5: use buffered reader)
    // P3-13: heartbeat ping every 30s, 3 fails = dead
    client._dead = false;
    client._heartbeat = setInterval(async () => {
      if (client._dead) return;
      try {
        const id = client._nextId = (client._nextId || 0) + 1;
        await rpcCall(id, "ping", {}, 5000);
        // Fix P5-B: a single successful ping clears the streak so a long-running
        // session is not killed by failures spread across hours.
        client._heartbeatFails = 0;
      } catch (_) {
        client._heartbeatFails = (client._heartbeatFails || 0) + 1;
        if (client._heartbeatFails >= 3) {
          client._dead = true;
          // Fix P6-L: stop the heartbeat ticker once we have given up on this server.
          try { if (client._heartbeat) clearInterval(client._heartbeat); } catch (_) {}
          try { child.kill("SIGKILL"); } catch (_) {}
        }
      }
    }, 30000);
    // Fix P8-15: do not let the heartbeat ticker keep the event loop alive
    // after the user already wants to quit.
    try { client._heartbeat.unref?.(); } catch (_) {}
    client._heartbeatFails = 0;

    // P3-14: crash recovery - restart once on crash
    child.on("exit", (code) => {
      if (client._dead || client._shuttingDown) return;
      // Fix P2-H: mark current client dead immediately so callTool stops queueing requests
      client._dead = true;
      try { if (client._heartbeat) clearInterval(client._heartbeat); } catch (_) {}
      console.error(`[dreamseed] MCP server ${name} crashed (exit ${code}), attempting restart`);
      client._restartCount = (client._restartCount || 0) + 1;
      if (client._restartCount <= 1) {
        const prevRestart = client._restartCount;
        setTimeout(() => {
          // Only restart if no replacement was already installed by another path
          const cur = mcpClients.get(name);
          if (cur && cur !== client && !cur._dead) return;
          try {
            startMcpServer(name, config).then(c => {
              if (c) { c._restartCount = prevRestart; mcpClients.set(name, c); }
              else { mcpClients.delete(name); }
            }).catch(() => mcpClients.delete(name));
          } catch (_) { mcpClients.delete(name); }
        }, 1000);
      } else {
        mcpClients.delete(name);
      }
    });

    try {
      const listResult = await rpcCall(2, "tools/list", {}, 8000);
      client.tools = listResult?.tools || [];
    } catch (e) {
      console.error(`[dreamseed] MCP ${name} tools/list failed: ${e.message}`);
      client.tools = [];
    }

    return client;
  }
  return null;
}

async function shutdownMcpClients() {
  // Fix P8-12: wait for each child to actually exit (or SIGKILL after 1s) so the
  // process does not return from main() while orphaned grandchildren are still
  // tearing down. Run them in parallel so the total wait stays at ~1s worst case.
  const kills = [];
  for (const [name, client] of mcpClients) {
    try {
      if (client._heartbeat) clearInterval(client._heartbeat);
      client._shuttingDown = true;
      const ch = client.child;
      try { ch?.kill("SIGTERM"); } catch (_) {}
      kills.push(new Promise((res) => {
        let done = false;
        const finish = () => { if (done) return; done = true; clearTimeout(t); res(); };
        const t = setTimeout(() => { try { ch?.kill("SIGKILL"); } catch (_) {} finish(); }, 1000);
        if (ch && typeof ch.on === "function") {
          ch.on("exit", finish);
        } else { finish(); }
      }));
    } catch (_) {}
  }
  await Promise.all(kills);
}


// ===== Permissions Engine =====
function loadPermissions() {
  if (!existsSync(SETTINGS_FILE)) return { defaultMode: "ask", allow: [], deny: [] };
  try {
    const settings = JSON.parse(readFileSync(SETTINGS_FILE, "utf8"));
    return {
      defaultMode: settings.permissions?.defaultMode || "ask",
      allow: settings.permissions?.allow || [],
      deny: settings.permissions?.deny || [],
    };
  } catch (_) {
    return { defaultMode: "ask", allow: [], deny: [] };
  }
}

function isPathSafe(filePath) {
  // Fix #10: only allow writes inside projectDir or ROOT; refuse temp by default
  const normalized = path.resolve(filePath).toLowerCase();
  const projectRoot = projectDir.toLowerCase();
  const rootDir = ROOT.toLowerCase();
  // Fix P9-B: handle drive-root projectDir (e.g. "d:\"). path.sep alone would
  // double the separator ("d:\\") and reject every real path like "d:\foo".
  const projBound = projectRoot.endsWith(path.sep.toLowerCase()) ? projectRoot : projectRoot + path.sep.toLowerCase();
  const rootBound = rootDir.endsWith(path.sep.toLowerCase()) ? rootDir : rootDir + path.sep.toLowerCase();
  if (normalized === projectRoot || normalized.startsWith(projBound)) return true;
  if (normalized === rootDir || normalized.startsWith(rootBound)) return true;
  // Reject any executable extensions in temp/system dirs
  const isExecutable = /\.(exe|bat|cmd|ps1|sh|com|scr|vbs|wsf|msi)$/i.test(normalized);
  if (isExecutable) return false;
  // Allow non-executable writes only into the project's own .dreamseed-* areas
  if (normalized.includes("\\.dreamseed-memory\\") || normalized.includes("/.dreamseed-memory/")) return true;
  return false;
}

function isDangerousCommand(cmd) {
  // Fix #28: check settings.json dangerousCommands first
  try {
    const extra = permissions?.dangerousCommands;
    if (Array.isArray(extra) && extra.length > 0) {
      const lc = String(cmd).toLowerCase();
      for (const p of extra) {
        try { if (new RegExp(p, "i").test(lc)) return true; } catch (_) {}
      }
    }
  } catch (_) {}
  // Fix #9: token-aware danger detection that handles whitespace, quotes, parameter order
  const norm = String(cmd).toLowerCase().replace(/["']/g, "").replace(/\s+/g, " ").trim();
  // Patterns are regex; matched against normalized command
  const dangerousPatterns = [
    // Linux destructive
    /\brm\s+(-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r)\s+(\/|~|\.|\*|[a-z]:[\\/])/,
    /\bmkfs\./,
    /\bdd\s+if=.+\s+of=\/dev\//,
    /:\(\)\s*\{[^}]*:\|:[^}]*\}/, // fork bomb
    /\bchmod\s+(-r\s+)?777\s+\//,
    /\b(wget|curl)\s+[^|]+\|\s*(sh|bash|zsh|fish)\b/,
    />\s*\/dev\/(sda|sdb|nvme|hda)/,
    // Windows destructive — match parameters in any order
    /\bremove-item\b.*-recurse.*\b[a-z]:\\?(\s|$)/,
    /\bremove-item\b.*\b[a-z]:\\?\s+.*-recurse/,
    /\bget-childitem\b.*\|\s*remove-item\b/,
    /\bremove-item\b[^|]*\b[a-z]:[\\/]/,
    /\bremove-item\b[^|]*-recurse\b[^|]*-force\b/,

    /\bdel(\s+\/[fqs])+\s+[a-z]:[\\/]/,
    /\brd(\s+\/[sq])+\s+[a-z]:[\\/]/,
    /\brmdir(\s+\/[sq])+\s+[a-z]:[\\/]/,
    /\bformat\s+[a-z]:/,
    /\bfdisk\b/,
    /\bdiskpart\b/,
    /\bshutdown\s+\/[srt]/,
    // Force-pipe install
    /\biwr\s+[^|]+\|\s*iex\b/,
    /\binvoke-webrequest\s+[^|]+\|\s*invoke-expression\b/,
  ];
  for (const pat of dangerousPatterns) {
    if (pat.test(norm)) return true;
  }
  return false;
}


// ===== History Persistence =====
function getSessionFile() {
  const projectHash = createHash("sha256").update(projectDir).digest("hex").slice(0, 12);
  const date = new Date().toISOString().slice(0, 10);
  return path.join(HISTORY_DIR, `session-${projectHash}-${date}-${sessionId.slice(0, 8)}.jsonl`);
}

let sessionFile = null;

function saveHistoryEvent(event) {
  if (!sessionFile) {
    sessionFile = getSessionFile();
  }
  // Fix P6-E: defer the append to the next tick so a model stream stays
  // responsive. Order is preserved because setImmediate is FIFO within a
  // turn; each event still appends with flag "a" so concurrent appends are
  // safe at the OS level.
  setImmediate(() => {
    try {
      try {
        const st = statSync(sessionFile);
        if (st.size > 50 * 1024 * 1024) {
          const rotated = sessionFile.replace(".jsonl", ".1.jsonl");
          renameSync(sessionFile, rotated);
        }
      } catch (_) {}
      const line = JSON.stringify({ ts: new Date().toISOString(), ...event }) + "\n";
      writeFileSync(sessionFile, line, { flag: "a" });
    } catch (err) {
      console.error(`[dreamseed] failed to save history: ${err.message}`);
    }
  });
}

let historyLock = null;
async function acquireHistoryLock() {
  if (!sessionFile) return true;
  const lockPath = sessionFile + ".lock";
  const start = Date.now();
  while (Date.now() - start < 5000) {
    try {
      writeFileSync(lockPath, String(process.pid), { flag: "wx" });
      historyLock = lockPath;
      return true;
    } catch (_) { /* contended */ }
    // Fix P8-16: detect stale lock from a crashed prior run. If the lockfile is
    // older than 60s and the PID inside is not us, treat as stale and remove.
    try {
      const st = statSync(lockPath);
      if (Date.now() - st.mtimeMs > 60000) {
        let oldPid = 0;
        try { oldPid = Number(readFileSync(lockPath, "utf8")) || 0; } catch (_) {}
        if (oldPid !== process.pid) {
          try { unlinkSync(lockPath); } catch (_) {}
          continue;
        }
      }
    } catch (_) {}
    await new Promise((r) => setTimeout(r, 10));
  }
  return false; // timeout
}
function releaseHistoryLock() {
  if (historyLock) {
    try { unlinkSync(historyLock); } catch (_) {}
    historyLock = null;
  }
}

async function saveSessionMessages(messages) {
  // Fix #8: persist full structured messages so /resume can restore tool_use/tool_result
  try {
    if (!sessionFile) sessionFile = getSessionFile();
    if (!(await acquireHistoryLock())) return;
    const fullFile = sessionFile.replace(".jsonl", ".messages.json");
    writeJsonAtomic(fullFile, {
      sessionId, projectDir, projectName, updated: new Date().toISOString(),
      messages,
    });
    // Also keep a small preview summary for listing
    const compact = messages.map(m => ({
      role: m.role,
      preview: typeof m.content === "string" ? m.content.slice(0, 200) :
        (m.content || []).map(b => b?.type === "text" ? (b.text || "").slice(0, 100) : `[${b?.type}]`).join(" ").slice(0, 200),
    }));
    writeJsonAtomic(sessionFile.replace(".jsonl", ".summary.json"), { sessionId, projectDir, projectName, messages: compact, updated: new Date().toISOString() });
    releaseHistoryLock();
  } catch (e) { try { logError("saveSessionMessages failed", { error: e.message }); } catch(_) {} releaseHistoryLock(); }
}


// ===== Context Compaction =====
function estimateTokens(messages) {
  // Fix P0: accumulate strings then count, instead of crashing with number.match()
  let cjk = 0;
  let nonCjk = 0;
  const cjkRe = /[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u2600-\u27bf\ud800-\udfff]/g;
  function add(text) {
    if (!text) return;
    const matches = text.match(cjkRe);
    const cjkLen = matches ? matches.length : 0;
    cjk += cjkLen;
    nonCjk += text.length - cjkLen;
  }
  for (const m of messages) {
    if (typeof m.content === "string") add(m.content);
    else if (Array.isArray(m.content)) {
      for (const b of m.content) {
        if (b && b.type === "text") add(b.text || "");
        else if (b) add(JSON.stringify(b));
      }
    }
  }
  // 4 chars/token English, 2 chars/token CJK
  return Math.ceil(nonCjk / 4 + cjk / 2);
}

async function compactMessages(messages, instructions) {
  const estimated = estimateTokens(messages);
  const limit = contextLimit * 0.8;
  if (estimated <= limit && instructions !== "force") return messages;

  const systemMsgs = messages.filter(m => m.role === "system");
  const userAssistantMsgs = messages.filter(m => m.role !== "system");
  if (userAssistantMsgs.length <= 12 && instructions !== "force") return messages;

  const keepRecent = Math.min(8, userAssistantMsgs.length);
  const recent = userAssistantMsgs.slice(-keepRecent);
  const older = userAssistantMsgs.slice(0, -keepRecent);

  // Fix P2: PreCompact hook
  await runHooks("PreCompact", { sessionId, turnCount, estimatedTokens: estimated, messageCount: messages.length });
  // Fix #7: Try real model-based summary with cache fallback
  let summary;
  try {
    summary = await modelSummarize(older, instructions);
  } catch (e) {
    if (process.env.DREAMSEED_DEBUG) console.error(`[dreamseed] model compact failed: ${e.message}; using heuristic`);
    summary = heuristicSummary(older, instructions);
  }
  const compacted = [...systemMsgs, { role: "user", content: summary }, ...recent];
  // Fix P2: PostCompact hook
  await runHooks("PostCompact", { sessionId, turnCount, compactedTokens: estimateTokens(compacted) });
  return compacted;
}

async function modelSummarize(messages, instructions) {
  // Fix #31: Use cache to avoid recomputing same prefix
  // Fix P3-C: include instructions in cache key so different instructions don't collide
  // Fix P6-K: include model in cache key so switching models does not reuse a stale summary.
  const _cacheBase = JSON.stringify({ model, instr: instructions || "", msgs: messages.map(m => ({ r: m.role, c: typeof m.content === "string" ? m.content : JSON.stringify(m.content) })) });
  const cacheKey = createHash("sha256").update(_cacheBase).digest("hex").slice(0, 32);
  const cacheFile = path.join(DREAMSEED_DIR, "cache", "compact-" + cacheKey + ".json");
  try {
    if (existsSync(cacheFile)) {
      const cached = JSON.parse(readFileSync(cacheFile, "utf8"));
      if (cached.summary && cached.ts) {
        const age = Date.now() - new Date(cached.ts).getTime();
        if (age < 7 * 86400000) return cached.summary; // 7-day TTL
        try { unlinkSync(cacheFile); } catch (_) {}
      }
    }
  } catch (_) {}

  const transcript = messages.slice(0, 30).map(m => {
    const text = typeof m.content === "string" ? m.content :
      Array.isArray(m.content) ? m.content.map(b => b.type === "text" ? (b.text || "") : b.type === "tool_use" ? `[tool ${b.name}]` : b.type === "tool_result" ? "[tool result]" : "").join(" ") :
      "";
    return `${m.role}: ${text.slice(0, 800)}`;
  }).join("\n\n");

  const prompt = `Summarize the following conversation between a user and an AI assistant. Keep all key facts, decisions, file paths, and pending tasks. Be concise but complete.${instructions && instructions !== "auto" && instructions !== "force" ? "\n\nUser additional instructions: " + instructions : ""}\n\n--- Conversation ---\n${transcript}\n--- End ---\n\nProvide the summary now:`;

  const summaryMsgs = [{ role: "user", content: prompt }];
  const body = { model, max_tokens: 2048, messages: summaryMsgs, stream: false };
  if (getSystemPrompt()) body.system = "You are a precise conversation summarizer.";

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 60000);
  let response;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      response = await fetch(`${baseUrl}/v1/messages`, {
        method: "POST",
        headers: { "content-type": "application/json", "x-api-key": apiKey, authorization: `Bearer ${apiKey}`, "anthropic-version": "2023-06-01" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (response.status >= 500 && attempt < 1) { try { await response.text(); } catch (_) {} try { await new Promise(r => setTimeout(r, 1000)); } catch (_) {} continue; }
      break;
    } catch (err) { if (controller.signal.aborted) throw err; if (attempt === 1) throw err; }
  }
  try {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const text = (data.content || []).filter(b => b.type === "text").map(b => b.text || "").join("\n").trim();
    if (!text) throw new Error("empty summary");
    const summary = `[Compact summary of earlier conversation]\n${text}\n[End of summary]`;
    try {
      mkdirSync(path.dirname(cacheFile), { recursive: true });
      writeJsonAtomic(cacheFile, { summary, ts: new Date().toISOString() });
    // Fix P2: LRU eviction - keep max 50 cache files
    try {
      const cacheDir = path.dirname(cacheFile);
      if (existsSync(cacheDir)) {
        const files = readdirSync(cacheDir).filter(f => f.startsWith("compact-")).map(f => ({
          name: f, mtime: statSync(path.join(cacheDir, f)).mtimeMs || 0
        })).sort((a, b) => a.mtime - b.mtime);
        for (let i = 0; i < files.length - 50; i++) {
          try { unlinkSync(path.join(cacheDir, files[i].name)); } catch (_) {}
        }
      }
    } catch (_) {}
    } catch (_) {}
    return summary;
  } finally {
    clearTimeout(timer);
  }
}

function heuristicSummary(messages, instructions) {
  // Fix P2-K: take a head + tail slice instead of only the first 5, to keep both
  // the original goal and the most recent decisions when the model summary fails.
  const users = messages.filter(m => m.role === "user");
  const assistants = messages.filter(m => m.role === "assistant");
  const headUsers = users.slice(0, 3);
  const tailUsers = users.slice(-4);
  const headAsst = assistants.slice(0, 3);
  const tailAsst = assistants.slice(-4);
  const seen = new Set();
  const dedup = (arr) => arr.filter(m => { const k = m === null ? "n" : (typeof m.content === "string" ? m.content : JSON.stringify(m.content)).slice(0,120); if (seen.has(k)) return false; seen.add(k); return true; });
  const parts = ["[Previous conversation summary - heuristic]"];
  if (instructions && instructions !== "auto" && instructions !== "force") parts.push(`User instructions: ${instructions}`);
  for (const m of dedup([...headUsers, ...tailUsers])) {
    const text = typeof m.content === "string" ? m.content : "[tool results]";
    parts.push(`User: ${text.slice(0, 400)}`);
  }
  for (const m of dedup([...headAsst, ...tailAsst])) {
    const text = typeof m.content === "string" ? m.content :
      (Array.isArray(m.content) ? m.content.filter(b => b && b.type === "text").map(b => b.text || "").join(" ").slice(0, 400) : "[tool calls]");
    parts.push(`Assistant: ${text.slice(0, 400)}`);
  }
  parts.push("[End of summary. Continue the conversation.]");
  return parts.join("\n");
}


// ===== Hooks Engine =====
function loadHookScripts() {
  if (!existsSync(HOOKS_DIR)) return [];
  try {
    const entries = readdirSync(HOOKS_DIR, { withFileTypes: true });
    return entries.filter(e => e.isFile() && (e.name.endsWith(".ps1") || e.name.endsWith(".py") || e.name.endsWith(".mjs"))).map(e => path.join(HOOKS_DIR, e.name));
  } catch (_) {
    return [];
  }
}

let lastHookResult = null;

async function runHooks(event, context) {
  if (hookScripts.length === 0) return null;
  // Fix P4-C: run hooks in parallel instead of serially. With N hooks and a 10s
  // timeout each, the worst case used to be N*10s; now it is just 10s.
  // Fix P4-D: feed the JSON event context on stdin and close stdin immediately so
  // hooks that follow the standard "read JSON from stdin" protocol get EOF without
  // waiting for the 10s kill timeout.
  const ctxJson = JSON.stringify({ hookEventName: event, ...(context || {}) });
  const collected = { additionalSystemPrompt: "", permissionDecision: null, continueFlag: true, rawOutputs: [] };
  const runOne = (script) => new Promise((resolveOne) => {
    try {
      const runner = script.endsWith(".ps1") ? "powershell.exe" : script.endsWith(".py") ? (process.env.DREAMSEED_PYTHON || "python") : process.execPath;
      const args = script.endsWith(".ps1") ? ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script] : [script];
      const child = spawn(runner, args, {
        env: { ...process.env, DREAMSEED_HOOK_EVENT: event, DREAMSEED_HOOK_CONTEXT: ctxJson },
        stdio: ["pipe", "pipe", "pipe"],
        shell: false,
        windowsHide: true,
      });
      // Provide the same context on stdin so JSON-on-stdin hooks work, then close.
      try { child.stdin.write(ctxJson); } catch (_) {}
      try { child.stdin.end(); } catch (_) {}
      try { child.stdout.setEncoding("utf8"); child.stderr.setEncoding("utf8"); } catch (_) {}
      let hookStdout = "";
      let hookStderr = "";
      // Fix P6-G: cap hook output so a chatty hook cannot exhaust memory.
      const HOOK_OUT_CAP = 256 * 1024;
      child.stdout.on("data", (chunk) => { if (hookStdout.length < HOOK_OUT_CAP) hookStdout += chunk.toString("utf8"); });
      child.stderr.on("data", (chunk) => { if (hookStderr.length < HOOK_OUT_CAP) hookStderr += chunk.toString("utf8"); });
      const timeout = setTimeout(() => { try { child.kill("SIGKILL"); } catch (_) {} }, 10000);
      const finish = () => {
        clearTimeout(timeout);
        const trimmed = hookStdout.trim();
        const result = { trimmed, stderr: hookStderr };
        resolveOne({ script, result });
      };
      child.on("exit", finish);
      child.on("error", finish);
    } catch (e) {
      try { logWarn("hook failed", { script, error: e.message }); } catch (_) {}
      resolveOne({ script, result: { trimmed: "", stderr: "" } });
    }
  });

  const settled = await Promise.all(hookScripts.map(runOne));
  // Merge results in script order so behaviour stays deterministic.
  for (const { script, result } of settled) {
    const trimmed = result.trimmed;
    if (trimmed) {
      collected.rawOutputs.push(trimmed);
      try {
        const parsed = JSON.parse(trimmed);
        if (parsed.additionalSystemPrompt) collected.additionalSystemPrompt += "\n" + parsed.additionalSystemPrompt;
        if (parsed.permissionDecision && !collected.permissionDecision) collected.permissionDecision = parsed.permissionDecision;
        if (parsed.continue === false) collected.continueFlag = false;
      } catch (_) {
        if (event === "SessionStart" || event === "UserPromptSubmit" || event === "PreCompact") {
          collected.additionalSystemPrompt += "\n" + trimmed.slice(0, 4000);
        }
      }
    }
    if (result.stderr && result.stderr.trim()) {
      try { logWarn("hook stderr", { script, stderr: result.stderr.slice(0, 500) }); } catch (_) {}
    }
  }
  lastHookResult = collected;
  return collected;
}


// ===== Agents & Skills =====
function loadAgents() {
  if (!existsSync(AGENTS_DIR)) return {};
  try {
    const agents = {};
    for (const entry of readdirSync(AGENTS_DIR, { withFileTypes: true })) {
      if (!entry.isFile() || !entry.name.endsWith(".md")) continue;
      const raw = readFileSync(path.join(AGENTS_DIR, entry.name), "utf8");
      const parsed = parseFrontmatter(raw);
      if (parsed?.name) agents[parsed.name] = parsed;
    }
    return agents;
  } catch (_) { return {}; }
}

function loadSkills() {
  if (!existsSync(SKILLS_DIR)) return [];
  try {
    return readdirSync(SKILLS_DIR, { withFileTypes: true })
      .filter(e => e.isDirectory())
      .map(e => ({ name: e.name, path: path.join(SKILLS_DIR, e.name) }));
  } catch (_) { return []; }
}

function parseFrontmatter(raw) {
  // Fix P7-C: support arrays (inline [a, b, c] and YAML-ish list blocks),
  // values containing colons (e.g. "description: a: b"), and quoted strings
  // that may themselves contain a colon.
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!match) return null;
  const fm = {};
  const lines = match[1].split(/\r?\n/);
  let curKey = null;
  for (const line of lines) {
    // list item under the current array key, e.g. "  - read"
    const listItem = line.match(/^\s+-\s+(.*)$/);
    if (listItem && curKey && Array.isArray(fm[curKey])) {
      fm[curKey].push(listItem[1].trim().replace(/^["']|["']$/g, ""));
      continue;
    }
    // key: value  (value may contain colons; only the FIRST colon splits)
    const kv = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (kv) {
      curKey = kv[1];
      let val = kv[2].trim();
      if (val === "") {
        // likely a YAML block-list; start an array and collect following "- " items
        fm[curKey] = [];
      } else if (/^\[.*\]$/.test(val)) {
        // inline array: [a, b, c]
        fm[curKey] = val.slice(1, -1).split(",").map(x => x.trim().replace(/^["']|["']$/g, "")).filter(Boolean);
      } else {
        fm[curKey] = val.replace(/^["']|["']$/g, "");
      }
      continue;
    }
  }
  fm.body = match[2].trim();
  return fm;
}


// ===== System Prompt =====
function loadSystemPrompt() {
  // Fix #20: assemble system prompt with proper structure
  const parts = [];

  // 1. Base identity
  if (existsSync(PROMPT_FILE)) {
    parts.push(readFileSync(PROMPT_FILE, "utf8"));
  }

  // 2. Tool list summary
  const toolNames = Object.values(BUILTIN_TOOLS).map(t => t.name).filter(Boolean);
  if (toolNames.length > 0) {
    parts.push(`# Available Tools\nYou have access to these tools: ${toolNames.join(", ")}.\nMCP tools (if any) are exposed as mcp__SERVER__TOOL.`);
  }

  // 3. Permissions summary (no full pattern dump - just behavioral hint)
  const permMode = permissions?.defaultMode || "ask";
  parts.push(`# Permissions\nDefault permission mode: ${permMode}. You can read files freely; writes and shell commands may require approval.`);

  // Fix CWD-INJECT: make sure the model knows where it is on disk.
  parts.push(`# Working Directory\nYou are running in the directory: ${projectDir}\nProject name: ${projectName}\nPlatform: ${process.platform}\nNode.js: ${process.version}\n\nWhen the user uses relative paths, resolve them against this directory. Do not invent paths from training data (such as /Users/.../Dev/...). Use Glob/Grep to discover files.`);

  // 4. Agent definitions (Fix #19)
  if (agents && Object.keys(agents).length > 0) {
    const agentLines = Object.entries(agents).map(([name, a]) => `- ${name}: ${a.description || a.body?.slice(0, 80) || ""}`);
    parts.push(`# Available Subagents\n${agentLines.join("\n")}\n\nUse the Task tool with the agent name to delegate work.`);
  }

  // 5. Skill listing (Fix #19)
  if (skills && skills.length > 0) {
    parts.push(`# Available Skills\n${skills.map(s => `- ${s.name}`).join("\n")}`);
  }

  // 6. Project instructions (DREAMSEED.md / AGENTS.md)
  const projectMd = path.join(projectDir, "DREAMSEED.md");
  const projectAgentsMd = path.join(projectDir, "AGENTS.md");
  if (existsSync(projectMd)) {
    try { parts.push(`# Project Instructions (DREAMSEED.md)\n${readFileSync(projectMd, "utf8")}`); } catch (_) {}
  }
  if (existsSync(projectAgentsMd)) {
    try { parts.push(`# Project Agents Guide (AGENTS.md)\n${readFileSync(projectAgentsMd, "utf8")}`); } catch (_) {}
  }

  // 7. Memory hint
  parts.push(`# Memory\nMemPalace memory tools (if available via MCP) let you recall past project context.`);

  // 8. Additional system prompts from CLI flags
  for (const file of options.systemPromptFiles) {
    if (existsSync(file)) parts.push(readFileSync(file, "utf8"));
  }
  parts.push(...options.systemPrompts);

  // 8b. Inject lastHookResult additionalSystemPrompt (Fix P2)
  if (lastHookResult?.additionalSystemPrompt) {
    parts.push(`# Hook Context\n${lastHookResult.additionalSystemPrompt.slice(0, 4000)}`);
  }
  // Fix P7-I: truncate by dropping lowest-priority parts instead of slicing
  // mid-sentence. Priority order (highest first): base identity, tools,
  // permissions, agents, project instructions, hook context, append-prompts,
  // memory hint. Drop from the tail until under budget.
  const MAX_PROMPT_CHARS = 16000;
  let combined = parts.join("\n\n").trim();
  if (combined.length > MAX_PROMPT_CHARS) {
    while (parts.length > 2 && combined.length > MAX_PROMPT_CHARS) {
      parts.pop();
      combined = parts.join("\n\n").trim();
    }
    if (combined.length > MAX_PROMPT_CHARS) {
      combined = combined.slice(0, MAX_PROMPT_CHARS) + "\n\n[system prompt truncated]";
    }
  }
  return combined;
}

// ===== Cancellation Manager =====
class CancellationManager {
  constructor() { this._disposers = []; this._aborted = false; }
  register(disposer) { if (this._aborted) disposer(); else this._disposers.push(disposer); }
  abort() {
    if (this._aborted) return; // Fix P8-11: idempotent, dispose exactly once
    this._aborted = true;
    // Fix P8-7: iterate a reversed COPY so a disposer throwing mid-way still
    // lets later disposers run; clear the list before invoking so re-entry from
    // a disposer cannot double-fire.
    const list = this._disposers.slice().reverse();
    this._disposers = [];
    for (const d of list) { try { d(); } catch (_) {} }
  }
}

// ===== Shell Execution =====
async function runShell(cmd, timeoutMs) {
  const shell = process.env.DREAMSEED_SHELL || "powershell.exe";
  const isPwsh = shell.endsWith("powershell.exe") || shell.endsWith("pwsh.exe");
  // P11-F: PowerShell 5.1 (Windows default) rejects "&&" as a statement separator.
  // Translate "cmd1 && cmd2" to "cmd1; cmd2" so model-generated bash-isms still run.
  // Keep "||" untouched (it is a valid PowerShell operator). Only "&&" is the problem.
  let effCmd = cmd;
  if (isPwsh) {
    effCmd = cmd.replace(/&&/g, ";");
  }
  const shellArgs = isPwsh
    ? ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", effCmd]
    : ["-c", effCmd];

  const child = spawn(shell, shellArgs, {
    cwd: projectDir,
    env: process.env,
    stdio: ["pipe", "pipe", "pipe"],
    shell: false,
    windowsHide: true,
  });

  let _childExited = false;
  if (cancellation) {
    const _killClosure = () => {
      if (_childExited) return; // Fix P7-A: do not kill an already-exited (possibly reused) PID
      try { child.kill("SIGTERM"); setTimeout(() => { if (!_childExited) { try { child.kill("SIGKILL"); } catch (_) {} } }, 1000); } catch (_) {}
    };
    cancellation.register(_killClosure);
  }

  try { child.stdout.setEncoding("utf8"); child.stderr.setEncoding("utf8"); } catch (_) {}
  // Fix P5-E: cap stdout/stderr accumulation so a runaway command cannot drive
  // the kernel out of memory. Final output is also re-truncated below for the
  // model.
  const STDOUT_CAP = 4 * 1024 * 1024;
  const STDERR_CAP = 1 * 1024 * 1024;
  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (chunk) => {
    if (stdout.length < STDOUT_CAP) {
      stdout += chunk.toString();
      if (stdout.length > STDOUT_CAP) stdout = stdout.slice(0, STDOUT_CAP) + "\n...(stdout cap reached)\n";
    }
  });
  child.stderr.on("data", (chunk) => {
    if (stderr.length < STDERR_CAP) {
      stderr += chunk.toString();
      if (stderr.length > STDERR_CAP) stderr = stderr.slice(0, STDERR_CAP) + "\n...(stderr cap reached)\n";
    }
  });

  const result = await new Promise((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      try { child.kill("SIGKILL"); } catch (_) {}
      _childExited = true; // Fix P8-6: close race between timeout-kill and later cancellation
      const partial = `Command timed out after ${timeoutMs}ms\nStdout:\n${stdout.slice(0, 10000)}\nStderr:\n${stderr.slice(0, 5000)}`;
      resolve(partial);
    }, timeoutMs);

    child.on("exit", (code) => {
      _childExited = true;
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      const out = stdout.slice(0, 30000);
      const err = stderr.slice(0, 10000);
      const truncated = stdout.length > 30000 ? "\n...(stdout truncated)" : "";
      resolve(`${out}${truncated}${err ? "\nStderr:\n" + err : ""}`.trim() || `(exit code ${code})`);
    });

    child.on("error", (err) => {
      _childExited = true;
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(err);
    });
  });

  return result;
}

// ===== Glob & Grep Helpers =====
async function globSearch(cwd, pattern) {
  try {
    const safeCwd = cwd.replace(/'/g, "''");
    const safePattern = pattern.replace(/'/g, "''");
    const child = spawn("powershell.exe", ["-NoProfile", "-Command", `Get-ChildItem -Path '${safeCwd}' -Recurse -Filter '${safePattern}' -ErrorAction SilentlyContinue | Select-Object -First 100 -ExpandProperty FullName`], { stdio: ["pipe", "pipe", "pipe"], shell: false, windowsHide: true });
    try { child.stdout.setEncoding("utf8"); } catch (_) {}
    // Fix P5-E: cap glob/grep stdout buffer too.
    const GLOB_CAP = 2 * 1024 * 1024;
    let out = "";
    child.stdout.on("data", (c) => {
      if (out.length < GLOB_CAP) {
        out += c.toString();
        if (out.length > GLOB_CAP) out = out.slice(0, GLOB_CAP);
      }
    });
    await new Promise((resolve) => {
  let done = false;
  const finish = () => { if (done) return; done = true; try { clearTimeout(t); } catch (_) {} resolve(); };
  const t = setTimeout(() => { try { child.kill("SIGKILL"); } catch (_) {} finish(); }, 15000);
  if (cancellation) cancellation.register(() => { try { child.kill("SIGKILL"); } catch (_) {} finish(); });
  child.on("exit", () => { finish(); });
  child.on("error", () => { finish(); });
});
    return out.trim().split(/\r?\n/).filter(Boolean);
  } catch (_) { return []; }
}

async function grepSearch(cwd, pattern, include) {
  try {
    const safePattern = pattern.replace(/'/g, "''");
    const safeCwd = cwd.replace(/'/g, "''");
    const safeInclude = include ? include.replace(/'/g, "''") : "";
    const includeFilter = safeInclude ? `-Include '${safeInclude}'` : "";
    const child = spawn("powershell.exe", ["-NoProfile", "-Command", `Get-ChildItem -Path '${safeCwd}' -Recurse ${includeFilter} -ErrorAction SilentlyContinue | Select-String -Pattern '${safePattern}' -CaseSensitive | Select-Object -First 100 | ForEach-Object { $_.Path + ':' + $_.LineNumber + ': ' + $_.Line }`], { stdio: ["pipe", "pipe", "pipe"], shell: false, windowsHide: true });
    try { child.stdout.setEncoding("utf8"); } catch (_) {}
    // Fix P5-E: cap glob/grep stdout buffer too.
    const GLOB_CAP = 2 * 1024 * 1024;
    let out = "";
    child.stdout.on("data", (c) => {
      if (out.length < GLOB_CAP) {
        out += c.toString();
        if (out.length > GLOB_CAP) out = out.slice(0, GLOB_CAP);
      }
    });
    await new Promise((resolve) => {
  let done = false;
  const finish = () => { if (done) return; done = true; try { clearTimeout(t); } catch (_) {} resolve(); };
  const t = setTimeout(() => { try { child.kill("SIGKILL"); } catch (_) {} finish(); }, 15000);
  if (cancellation) cancellation.register(() => { try { child.kill("SIGKILL"); } catch (_) {} finish(); });
  child.on("exit", () => { finish(); });
  child.on("error", () => { finish(); });
});
    return out.trim().split(/\r?\n/).filter(Boolean);
  } catch (_) { return []; }
}

async function fsStat(fp) {
  const { stat } = await import("node:fs/promises");
  return stat(fp);
}


// ===== Interactive Mode =====
async function runInteractiveMode() {
  // Fix P7-D: every cleanup happens in finally so a throw in initMcpClients,
  // SessionStart hook, or the main loop still releases the readline and MCP
  // children instead of leaving the process wedged.
  const rl = createInterface({ input, output });
  _activeReadline = rl;
  try {
  await initMcpClients();
  await runHooks("SessionStart", { sessionId, projectDir, projectName });

  const messages = [];
  currentSession = { id: sessionId, messages, subagentDepth: 0 };

  console.log(`DreamSeed Code v${VERSION}`);
  console.log(`${model} · ${projectName}`);
  console.log("Type /resume to continue imported legacy history, or /exit to quit.");

  while (true) {
    const line = await rl.question("dreamseed> ");
    const prompt = line.trim();
    if (!prompt) continue;
    if (prompt === "/exit" || prompt === "/quit") break;
    if (prompt === "/help") { printSlashHelp(); continue; }
    if (prompt === "/model") { console.log(`Active model: ${model}`); continue; }
    if (prompt === "/clear") {
      messages.length = 0;
      // Fix #14: reset tool failure tracking on /clear
      while (recentToolResults.length > 0) recentToolResults.pop();
      console.log("Conversation cleared.");
      continue;
    }
    if (prompt === "/compact" || prompt.startsWith("/compact ")) {
      const instructions = prompt.slice("/compact".length).trim();
      const compacted = await compactMessages(messages, instructions);
      messages.length = 0;
      messages.push(...compacted);
      console.log(`[dreamseed] compacted to ${messages.length} messages (~${estimateTokens(messages)} tokens)`);
      continue;
    }
    if (prompt === "/status") {
      console.log(`Session: ${sessionId.slice(0, 8)} | Turns: ${turnCount} | Messages: ${messages.length} | Tokens: ~${estimateTokens(messages)}`);
      console.log(`MCP servers: ${mcpClients.size} | Hooks: ${hookScripts.length} | Agents: ${Object.keys(agents).length}`);
      continue;
    }
    if (prompt === "/resume" || prompt.startsWith("/resume ")) {
      await handleResumeCommand(rl, messages, prompt);
      continue;
    }

    saveHistoryEvent({ type: "user_input", content: prompt });
    const hookRes = await runHooks("UserPromptSubmit", { prompt, sessionId, turnCount, projectDir });
    if (hookRes?.continueFlag === false) { console.log("[dreamseed] hook requested stop"); continue; }
    if (hookRes?.additionalSystemPrompt) { messages.push({ role: "system", content: hookRes.additionalSystemPrompt.slice(0, 4000) }); }
    messages.push({ role: "user", content: prompt });

    try {
      const result = await runToolLoop(messages, null, 0);
      console.log(result);
      saveHistoryEvent({ type: "assistant_response", content: result.slice(0, 500) });
    } catch (err) {
      console.error(`[dreamseed] error: ${err.message}`);
      saveHistoryEvent({ type: "error", content: err.message });
    }

    await saveSessionMessages(messages);
  }

  } catch (e) {
    console.error(`[dreamseed] interactive mode aborted: ${e && e.message ? e.message : e}`);
    if (e && e.stack && process.env.DREAMSEED_DEBUG) console.error(e.stack);
  } finally {
    try { await runHooks("SessionEnd", { sessionId, turnCount }); } catch (_) {}
    try { await shutdownMcpClients(); } catch (_) {}
    _activeReadline = null;
    try { rl.close(); } catch (_) {}
    console.log("Goodbye.");
  }
}

// ===== Print Mode =====
async function runPrintMode(prompt) {
  await initMcpClients();
  const messages = [{ role: "user", content: prompt }];
  currentSession = { id: sessionId, messages, subagentDepth: 0 };
  // Fix P10-A: emit system init NOW (after MCP/tools are known) so consumers
  // of the NDJSON stream see the init line BEFORE any tool_use event.
  if (options.outputFormat === "json" || options.outputFormat === "stream-json" || options.outputFormat === "ndjson") {
    emitNdjsonInit();
  }

  // Fix P2: timeout support
  const timeoutTimer = setTimeout(() => { if (cancellation) cancellation.abort(); }, options.timeout || 300000);
  try {
    const result = await runToolLoop(messages, null, 0);
    clearTimeout(timeoutTimer);
    return result;
  } finally {
    // Fix P7-K: always tear down MCP servers, even on error, so we never leak
    // child processes when --print exits via an exception path.
    try { await shutdownMcpClients(); } catch (_) {}
  }
}

// ===== /resume Command =====
async function handleResumeCommand(rl, messages, prompt) {
  if (!existsSync(LEGACY_HISTORY_SCRIPT)) {
    console.log("[dreamseed] legacy history script missing.");
    return;
  }
  if (!existsSync(LEGACY_HISTORY_DEST)) {
    console.log("[dreamseed] no imported legacy history found. Run: dreamseed history import");
    return;
  }

  const target = prompt.slice("/resume".length).trim();
  try {
    if (target) {
      await resumeLegacySession(messages, target);
      return;
    }

    const sessions = await runLegacyHistoryJson(["list-sessions", "--dest", LEGACY_HISTORY_DEST, "--limit", "12"]);
    const choices = sessions.sessions || [];
    if (choices.length === 0) {
      console.log("[dreamseed] no legacy sessions found.");
      return;
    }

    console.log("\nImported legacy sessions:");
    choices.forEach((s, i) => {
      const project = s.project || "unknown";
      const time = s.last_time || s.first_time || "unknown";
      console.log(`${String(i + 1).padStart(2)}. ${time}  ${project}  (${s.entry_count || 0} entries)`);
      if (s.preview) console.log(`    ${(s.preview || "").replace(/\s+/g, " ").trim().slice(0, 110)}`);
    });

    const answer = (await rl.question("\nResume number, session id, or search text: ")).trim();
    if (!answer) return;

    const num = Number(answer);
    if (Number.isInteger(num) && num >= 1 && num <= choices.length) {
      await resumeLegacySession(messages, choices[num - 1].session_id);
    } else {
      await resumeLegacySession(messages, answer);
    }
  } catch (err) {
    console.log(`[dreamseed] /resume failed: ${err.message}`);
  }
}

async function resumeLegacySession(messages, target) {
  const payload = await runLegacyHistoryJson([
    "resume-context", target, "--dest", LEGACY_HISTORY_DEST,
    "--limit-entries", process.env.DREAMSEED_RESUME_LIMIT_ENTRIES || "18",
    "--max-chars", process.env.DREAMSEED_RESUME_MAX_CHARS || "12000",
  ]);

  const context = payload.context || "";
  if (!context) { console.log("[dreamseed] no resumable context."); return; }

  // Fix #32: sort entries by timestamp before injecting
  const entries = payload.entries || [];
  if (entries.length > 0) {
    entries.sort((a, b) => {
      const ta = a.timestamp || a.first_timestamp || 0;
      const tb = b.timestamp || b.first_timestamp || 0;
      return ta - tb;
    });
  }

  messages.push({
    role: "user",
    content: `<legacy-resume>\n${context}\n</legacy-resume>\n\nUse this as private context. Do not store as long-term memory.`,
  });
  messages.push({
    role: "assistant",
    content: "Legacy session context loaded. I will use it as private session context only.",
  });

  const session = payload.session || {};
  console.log(`[dreamseed] resumed session ${session.session_id || target} (${session.entry_count || 0} entries).`);
}

function resolvePythonExe() {
  // Fix P9-P: Windows users often only have the "py" launcher, not "python"
  // on PATH. Probe a small list so /resume does not fail with ENOENT.
  const env = process.env;
  const candidates = [];
  if (env.DREAMSEED_PYTHON) candidates.push(env.DREAMSEED_PYTHON);
  if (env.PYTHON) candidates.push(env.PYTHON);
  candidates.push("python", "python3", "py", "py -3");
  for (const c of candidates) {
    const parts = c.split(" ");
    try {
      const { execSync } = require("child_process");
      execSync(parts[0] + " --version", { stdio: "ignore", windowsHide: true, shell: parts.length > 1 });
      return c;
    } catch (_) {}
  }
  return "python"; // last resort; spawn will emit ENOENT with a clear message
}

async function runLegacyHistoryJson(args) {
  const python = resolvePythonExe();
  const parts = python.split(" ");
  const exe = parts[0];
  const preArgs = parts.slice(1);
  const child = spawn(exe, [...preArgs, LEGACY_HISTORY_SCRIPT, ...args], {
    cwd: ROOT, env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    stdio: ["ignore", "pipe", "pipe"], shell: false, windowsHide: true,
  });
  try { child.stdout.setEncoding("utf8"); child.stderr.setEncoding("utf8"); } catch (_) {}
  // Fix P5-E: defensive cap for the legacy history reader.
  const LH_OUT_CAP = 32 * 1024 * 1024;
  const LH_ERR_CAP = 1 * 1024 * 1024;
  let stdout = "", stderr = "";
  child.stdout.on("data", (c) => {
    if (stdout.length < LH_OUT_CAP) {
      stdout += c.toString("utf8");
      if (stdout.length > LH_OUT_CAP) stdout = stdout.slice(0, LH_OUT_CAP);
    }
  });
  child.stderr.on("data", (c) => {
    if (stderr.length < LH_ERR_CAP) {
      stderr += c.toString("utf8");
      if (stderr.length > LH_ERR_CAP) stderr = stderr.slice(0, LH_ERR_CAP);
    }
  });
  return new Promise((resolve, reject) => {
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code && code !== 0) return reject(new Error((stderr || stdout || `exit ${code}`).trim()));
      try { resolve(JSON.parse(stdout)); } catch (e) { reject(new Error(`invalid JSON: ${e.message}`)); }
    });
  });
}


// ===== Utilities =====
function parseArgs(argv) {
  const opts = { help: false, version: false, print: false, outputFormat: "text", model: "", prompt: [], systemPromptFiles: [], systemPrompts: [], maxTurns: 100, timeout: 300000 };
  const ignoredFlags = new Set(["--settings", "--mcp-config", "--add-dir", "--agents"]);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") opts.help = true;
    else if (a === "--version" || a === "-v") opts.version = true;
    else if (a === "--print" || a === "-p") opts.print = true;
    else if (a === "--verbose") continue;
    else if (a === "--output-format") opts.outputFormat = argv[++i] || "text";
    else if (a.startsWith("--output-format=")) opts.outputFormat = a.slice("--output-format=".length);
    else if (a === "--model") opts.model = argv[++i] || "";
    else if (a.startsWith("--model=")) opts.model = a.slice("--model=".length);
    else if (a === "--max-turns") { const _mt = Number(argv[++i]); opts.maxTurns = Number.isFinite(_mt) && _mt > 0 ? Math.floor(_mt) : 100; }
    else if (a.startsWith("--max-turns=")) { const _mt = Number(a.slice("--max-turns=".length)); opts.maxTurns = Number.isFinite(_mt) && _mt > 0 ? Math.floor(_mt) : 100; }
    else if (a === "--timeout") { const _to = Number(argv[++i]); opts.timeout = Number.isFinite(_to) && _to >= 1000 ? _to : 300000; }
    else if (a.startsWith("--timeout=")) { const _to = Number(a.slice("--timeout=".length)); opts.timeout = Number.isFinite(_to) && _to >= 1000 ? _to : 300000; }
    else if (a === "--append-system-prompt-file") opts.systemPromptFiles.push(argv[++i] || "");
    else if (a.startsWith("--append-system-prompt-file=")) opts.systemPromptFiles.push(a.slice("--append-system-prompt-file=".length));
    else if (a === "--append-system-prompt") opts.systemPrompts.push(argv[++i] || "");
    else if (a.startsWith("--append-system-prompt=")) opts.systemPrompts.push(a.slice("--append-system-prompt=".length));
    else if (ignoredFlags.has(a)) i += 1;
    else if (a.startsWith("--")) continue;
    else opts.prompt.push(a);
  }
  return opts;
}

const _ndjsonEvents = [];
let _ndjsonInitEmitted = false;
function emitNdjsonInit() {
  if (_ndjsonInitEmitted) return;
  _ndjsonInitEmitted = true;
  try {
    emitNdjson({ type: "system", subtype: "init", mcp_servers: Array.from(mcpClients.keys()), tools: getToolDefinitions().map(t => ({ name: t.name, description: t.description })) });
  } catch (_) {}
}
let _textStreamed = false;  // Fix RT-4: tracks whether SSE already wrote model text to stdout
function emitNdjson(event) {
  console.log(JSON.stringify(event));
}
function writeResult(text, format) {
  // Fix P10-A: NDJSON events are now streamed live as they happen (see tool
  // loop). writeResult only emits the trailing "result" event in NDJSON modes.
  // The leading "system init" event is emitted by emitNdjsonInit() at run start.
  if (format === "json" || format === "stream-json" || format === "ndjson") {
    if (!_ndjsonInitEmitted) emitNdjsonInit();
    // Drain any leftover _ndjsonEvents from older code paths (defensive; the
    // streaming sites above now bypass the buffer).
    for (const ev of _ndjsonEvents) {
      emitNdjson(ev);
    }
    emitNdjson({ type: "result", subtype: "success", result: text });
  } else {
    // Fix RT-4: SSE has already streamed deltas to stdout in text mode.
    // Avoid double-printing the same text. Only emit a trailing newline,
    // or fall back to printing the full string if streaming did not happen.
    if (_textStreamed) {
      process.stdout.write("\n");
    } else {
      console.log(text);
    }
  }
}

async function readStdin() {
  const chunks = [];
  for await (const chunk of input) chunks.push(Buffer.from(chunk));
  const text = Buffer.concat(chunks).toString("utf8").trim();
  // Fix P9-Q (implements the previously-vacuous P8-10): an empty stdin in
  // --print mode silently produced a zero-byte prompt, wasting a model call
  // and confusing the desktop UI. Fail fast with a clear message instead.
  if (!text) {
    const err = new Error("No prompt provided via stdin or prompt argument (use --help for usage).");
    err.code = "EMPTY_PROMPT";
    throw err;
  }
  return text;
}

function normalizeUrl(url) {
  return String(url || "").replace(/\/+$/, "");
}

function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal && signal.aborted) return reject(new Error("aborted"));
    const t = setTimeout(resolve, ms);
    if (signal) {
      const onAbort = () => { clearTimeout(t); reject(new Error("aborted")); };
      signal.addEventListener("abort", onAbort, { once: true });
    }
  });
}

function printHelp() {
  console.log(`DreamSeed Lite Kernel v${VERSION}

Usage:
  dreamseed --print "hello"
  dreamseed

Inside the interactive shell:
  /resume       List and load imported legacy sessions
  /compact      Compress conversation context
  /clear        Clear current conversation
  /model        Show active model
  /status       Show session statistics
  /help         Show this help
  /exit         Exit

The DreamSeed launcher starts the provider bridge automatically when
DREAMSEED_PROVIDER_CONFIG points to a private provider config.
`);
}

function printSlashHelp() {
  console.log(`Slash commands:
  /resume [id]  Resume legacy session
  /compact [instr]  Compress context
  /clear        Clear conversation
  /model        Show active model
  /status       Session stats
  /help         This help
  /exit         Exit`);
}

