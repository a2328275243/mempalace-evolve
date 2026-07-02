# Old Kernel Feature Map

## Source

- Old kernel: `D:\Agent\DreamSeed-Packaging-Workspace\runtime\claude-cli.js`
- Size: `13,047,716` bytes
- Approx chars: `12,985,767`
- Approx lines: `16,668`
- Static scan report, temporary source: `C:\Users\Lenovo\AppData\Local\Temp\dreamseed-old-kernel-analysis-20260622-140322\old-kernel-feature-map-filtered.md`

## Notes

The old kernel is a compressed/minified single JavaScript bundle. The positions below are feature anchors, not clean module boundaries. `offset` is the most reliable reference; `line` and `col` are helper coordinates for quick lookup.

## Feature Anchors

| Feature | Old Kernel Anchor |
|---|---|
| Version / entry banner | `Version: 2.1.88` offset `178`, line `4`; `Want to see the unminified source` offset `200`, line `6` |
| CLI argument parsing | `--help` offset `898102`, line `129`; `--print` offset `3776811`, line `544`; `CLAUDE_CODE_SIMPLE` offset `48097`, line `8` |
| Non-interactive `--print` mode | `stream-json` offset `11537570`, line `7870`; `max-turns` offset `12929674`, line `16615`; `--output-format` offset `11537584`, line `7870` |
| TTY / REPL input | `setRawMode` offset `3745143`, line `544`; `process.stdin.setEncoding` offset `3776845`, line `544`; `process.stdout.on("error"` offset `142652`, line `48` |
| Anthropic SDK client | `/v1/messages` offset `94909`, line `38`; `ANTHROPIC_API_KEY` offset `114711`, line `40`; `ANTHROPIC_AUTH_TOKEN` offset `114754`, line `40` |
| Messages SSE state machine | `message_start` offset `61794`, line `11`; `message_stop` offset `61848`, line `11`; `content_block_delta` offset `61907`, line `11` |
| Tool-use assembly | `tool_use` offset `78209`, line `16`; `server_tool_use` offset `78230`, line `16`; `mcp_tool_use` offset `78258`, line `16`; `tool_result` offset `89923`, line `38` |
| Read tool | `The file_path parameter must be an absolute path` offset `3727224`, line `524`; `Read a file` offset `3728598`, line `533`; `readFile` offset `135451`, line `47` |
| Write tool | `writeFile` offset `134232`, line `47`; `Edit, Write, and NotebookEdit tools` offset `37703`, line `8` |
| Edit / MultiEdit tools | `replace_all` offset `5414981`, line `1561`; `old_string` offset `8698941`, line `2977`; `new_string` offset `8698954`, line `2977` |
| Glob / Grep tools | `Glob` offset `745619`, line `109`; `ripgrep` offset `989288`, line `169`; `regex` offset `265289`, line `66` |
| Bash tool | `Bash` offset `988391`, line `169`; `safeFlags` offset `4389436`, line `813`; `Shell command failed` offset `127045`, line `47` |
| TodoWrite tool | `TodoWrite` offset `6499801`, line `1712`; `pending` offset `32370`, line `8`; `completed` offset `88188`, line `16` |
| WebFetch / WebSearch | `WebFetch` offset `986538`, line `169`; `WebSearch` offset `26724`, line `8`; `WebSearch does not support wildcards` offset `1033960`, line `188` |
| NotebookRead / NotebookEdit | `NotebookRead` offset `1033812`, line `188`; `NotebookEdit` offset `37720`, line `8`; `Jupyter` offset `3727855`, line `530` |
| ExitPlanMode | `ExitPlanMode` offset `4903869`, line `1021`; `exit_plan_mode` offset `9083105`, line `3191` |
| MCP JSON-RPC protocol | `jsonrpc` offset `528606`, line `94`; `method:JK("initialize")` offset `530584`, line `94`; `tools/list` offset `535150`, line `94` |
| MCP config / proxy | `mcp_tool_use` offset `78258`, line `16`; `MCP_PROXY_URL` offset `855839`, line `119`; `MCP_PROXY_PATH` offset `855877`, line `119` |
| MCP stdio / SSE transport | `Content-Length` offset `213014`, line `52`; `EventSource` offset `819870`, line `119`; `stdio` offset `880905`, line `128` |
| Hook events | `PreToolUse` offset `996894`, line `169`; `PostToolUse` offset `996907`, line `169`; `PostCompact` offset `26098`, line `8` |
| Hook execution protocol | `hookEventName` offset `8088231`, line `2161`; `permissionDecision` offset `8088269`, line `2161`; `additionalSystemPrompt` nearby in hook protocol block |
| Permissions / approval engine | `permissions` offset `223355`, line `58`; `bypassPermissions` offset `995781`, line `169`; `defaultMode` offset `1038452`, line `188` |
| Dangerous command / safety checks | `destructiveHint` offset `534569`, line `94`; `dangerous` offset `114907`, line `40`; `rm -rf` offset `5080675`, line `1485` |
| Compact / context compression | `compaction_delta` offset `84378`, line `16`; `continuation summary` offset `88210`, line `16`; `conversation history will be replaced` offset `88349`, line `16` |
| Token / cost accounting | `claude_code.token.usage` offset `37472`, line `8`; `totalCostUSD` offset `30132`, line `8`; `cacheReadInputTokens` offset `34782`, line `8` |
| History / resume | `resume work efficiently` offset `88288`, line `16`; `history` offset `88362`, line `16`; `session_id` offset `3644962`, line `471` |
| Subagent / Task | `Task` offset `24180`, line `8`; `sdkAgentProgressSummariesEnabled` offset `30608`, line `8`; `agentColorMap` offset `31254`, line `8` |
| Skills API / local skills | `/v1/skills` offset `99011`, line `39`; `skills` offset `99015`, line `39`; `skills-2025-10-02` offset `99105`, line `39` |
| Plugin marketplace | `registeredHooks` offset `31779`, line `8`; `pluginRoot` offset `42332`, line `8`; `reserved for official Anthropic marketplaces` offset `1003499`, line `169` |
| Slash command system | `/login` offset `2554363`, line `348`; `/doctor` offset `4383965`, line `813`; `/review` offset `4938355`, line `1376`; `/permissions` and `/mcp` appear around command registry sections |
| Terminal UI symbols / folding | `ctrl+o` / `expand` / `⎿` / arrows appear in UI string blocks; some Unicode snippets render poorly from minified source, use raw scan report for exact snippets |
| Interrupt / cancellation / shutdown | `AbortController` offset `78595`, line `16`; `SIGINT` offset `874864`, line `126`; `Request was aborted` offset `51861`, line `8` |
| Git / repository detection | `Parsed repository` offset `953483`, line `147`; `git diff` offset `4391021`, line `813`; `git log` offset `4392093`, line `813` |
| Remote session / worktree | `sessionIngressToken` offset `30727`, line `8`; `worktreePath` offset `897780`, line `129`; `remote-review` offset `897820`, line `129` |
| tmux / PTY / terminal task | `tmux` offset `990803`, line `169`; `terminal status` offset `544427`, line `94`; `pty` offset `141687`, line `48` |
| Autoupdate / version checking | `version` offset `53772`, line `8`; `latest` offset `60054`, line `10`; `release` offset `56496`, line `8` |
| Telemetry / Statsig / Sentry / OpenTelemetry | `DISABLE_TELEMETRY` offset `900797`, line `129`; `opentelemetry` offset `3497630`, line `470`; `claude_code.session.count` offset `36911`, line `8` |
| Settings / `.claude` config | `.claude` offset `130`, line `2`; `CLAUDE_CONFIG_DIR` offset `48845`, line `8`; `settings.json` offset `907636`, line `132` |
| OAuth / login / logout | `ANTHROPIC_AUTH_TOKEN` offset `114754`, line `40`; `oauth` offset `30754`, line `8`; `login` offset `243026`, line `63` |
| AWS Bedrock | `AWS_REGION` offset `48431`, line `8`; `Bedrock` offset `1044023`, line `188`; `ConverseStream` offset `2248313`, line `300` |
| Google Vertex | `Vertex` offset `2405762`, line `300`; `googleapis` offset `3266331`, line `427`; `GOOGLE_APPLICATION_CREDENTIALS` offset `3411876`, line `454` |
| Azure / Foundry | `azure-app-service` offset `994301`, line `169`; `AZURE_` offset `994335`, line `169`; `Foundry` offset `2405773`, line `300` |
| GitHub Copilot adapter | `Copilot` offset `5918275`, line `1563`; `GITHUB_TOKEN` offset `6745354`, line `1825` |

## Keep / Rewrite / Omit Guidance

### Worth Reimplementing In Lite Kernel

- CLI / REPL / `--print`
- Anthropic-compatible Messages + SSE
- Tool loop and core tools: Read, Write, Edit, Glob, Grep, Bash, TodoWrite
- WebFetch / WebSearch if provider/tool policy supports it
- MCP protocol and stdio/SSE transports
- Hooks: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, SubagentStop, PreCompact, PostCompact
- Permissions / approval UI
- Compact / context trimming
- History / resume
- Subagent / Task
- Local skills and local agents
- Git/repository helpers
- Terminal UI folding, tool result display, interrupt/cancel handling

### Can Stay Omitted Unless Needed

- AWS Bedrock SDK
- Google Vertex SDK
- Azure / Foundry SDK
- GitHub Copilot adapter
- Plugin marketplace
- Telemetry / Statsig / Sentry / OpenTelemetry
- Silent autoupdate
- tmux / remote session / worktree cloud review
- Notebook tools unless the product explicitly supports notebooks

## Next Lookup Command

Use `rg` or a small offset scanner against:

```powershell
$file = 'D:\Agent\DreamSeed-Packaging-Workspace\runtime\claude-cli.js'
rg -n --fixed-strings 'TodoWrite' $file
```

For offset-level lookup, reuse the generated JSON report:

`C:\Users\Lenovo\AppData\Local\Temp\dreamseed-old-kernel-analysis-20260622-140322\old-kernel-feature-map-filtered.json`
