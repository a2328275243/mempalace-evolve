# Project Memory

## Project
MemPalace Evolve repository with integrated DreamSeed Code terminal agent. Remote: https://github.com/a2328275243/mempalace-evolve

## Current Snapshot
- Repository contains both MemPalace Evolve Python package (`src/mempalace_evolve/`) and DreamSeed Code terminal agent (`bin/dreamseed-agent.js`, `bin/dreamseed-lite-kernel.js`).
- Latest code-quality pass focused on MemPalace core reliability/performance rather than community/docs work: safer consolidation dedup bucketing, multilingual overlap dedup, Chroma delete loop progress guards, faster SDK `remember()` hot path, test isolation for global Chroma paths, and dev extras that can run MCP tests.
- Latest follow-up moved adaptive scorer learned baselines out of package source into runtime state under `MEMPALACE_ROOT` or `MEMPALACE_ADAPTIVE_BASELINES_PATH`, preventing full tests and normal use from dirtying `src/mempalace_evolve/core/.adaptive_baselines.json`.
- Latest SDK lifecycle pass fixed public `compress_old_memories()` and `purge_expired()` entry points: archive collections now use a public `chromadb.PersistentClient`, compression passes `max_summary_chars` correctly, TTL expiry supports wing filtering, and SDK tests cover both flows.
- Latest CLI lifecycle pass fixed `mempalace purge`, `mempalace compress`, and `mempalace consolidate`: removed unreachable duplicate branches, removed undefined `get_palace()` calls, fixed `json` scope, and added CLI dispatch tests.
- Latest REST lifecycle pass added end-to-end FastAPI coverage for `/lifecycle/purge` and `/lifecycle/compress`, verifying the REST surface reaches the fixed SDK lifecycle paths.
- Latest MCP/embedding reliability pass extended MCP memory writes with SDK metadata/source/ttl/tags support, exposed lifecycle tools via MCP with write locking, added real FastMCP tool-call tests, made test embeddings deterministic through `MEMPALACE_EMBEDDING_BACKEND=hash`, improved hash fallback recall with lexical features, added metadata fallback for constrained hybrid searches, and tuned default Chroma HNSW metadata for write-heavy memory workloads.
- Latest adapter parity pass aligned OpenAI and LangChain tool adapters with SDK/MCP memory semantics by forwarding `metadata`, `source`, `ttl`, `tags`, and recall `room` filters through existing tools without increasing tool count.
- Desktop/Electron installers and old v0.1.1 release artifacts were removed from source. Current release is `dreamseed-code-v0.2.0`.
- Latest pushed MemPalace code commit before the current in-progress pass: `309598f` (`Improve MCP lifecycle and embedding reliability`).
- Local uncommitted Lite Kernel productization changes are in `bin/dreamseed-lite-kernel.js`: native DreamSeed history management, richer slash commands, MultiEdit, tool progress streaming, MCP Content-Length framing and HTTP JSON-RPC support, segmented compact summaries, skill detail loading, safer shell fallback, and tool change previews.
- Terminal UI5 changes are now committed, pushed, packaged, and uploaded: polished box-drawing terminal UI, `/` command palette, Up/Down selection, Tab completion, Enter-to-run selected prefix match, right-bounded assistant reply blocks, tool running/done/error rows, approval/info/status blocks, queued MCP notices, Unicode-width-aware Chinese text layout, and scripted-input smoke support.
- GitHub release `dreamseed-code-v0.2.0` now has assets:
  - `DreamSeed-Code-0.2.0-Setup.exe`, SHA256 `E44CA9DD28BDB80FE519259244AC7EC17E3CE4145AABBD9D3D936D8036840F34`, size 146,565,632 bytes.
  - `DreamSeed-Code-0.2.0-Windows-Full.zip`, SHA256 `BDD1F7635154683E3FDB20FAB8F7DDD401AF936AD61B2748DD1B245E7B215763`, size 146,553,564 bytes.
  - `dreamseed-code-0.2.0-source.zip`, SHA256 `AF9C44B3A0EA9F58E6820558F0C2D013E4BCACB875A6BA9746F4A295137FAE27`, size 396,126 bytes.
- `master` and tag `dreamseed-code-v0.2.0` point at `0332abd`.
- A copy of the refreshed installer exists on the USB drive at `G:\DreamSeed-Code-0.2.0-Setup.exe`, hash-matched with the local dist copy.

## Key Files
- `README.md`: contest template preserved at top; describes Path A MemPalace-only install and Path B DreamSeed terminal agent install, now recommending `Setup.exe` for ordinary Windows users.
- `pyproject.toml`, `src/mempalace_evolve/`: MemPalace package source.
- `bin/dreamseed-lite-kernel.js`: DreamSeed Lite Kernel (~100 KB), no old compatibility kernel fallback.
- `bin/dreamseed-agent.js`: launcher/provider/history/package command surface.
- `.codex-project/OLD_KERNEL_FEATURE_MAP.md`: persistent local map of old 13MB kernel features to offset/line anchors for future rewrite/reference work.
- `scripts/install-dreamseed.ps1`: Windows install script for terminal command.
- `scripts/setup-bootstrap.ps1`: self-extracting setup bootstrap; extracts full kit to `%LOCALAPPDATA%\DreamSeedCode\app`, installs command/runtime to `%LOCALAPPDATA%\DreamSeed`, and creates a desktop shortcut.
- `scripts/build-windows-setup-exe.ps1`: builds single-file `DreamSeed-Code-0.2.0-Setup.exe` by embedding the full kit zip and setup bootstrap with Windows .NET Framework `csc.exe`.
- `scripts/build-windows-full-kit.ps1`: builds offline full zip with portable Node/Python/wheelhouse.
- `.mcp.json`, `.dreamseed/`: MCP, agents, skills, tasks, settings.

## Decisions and Conventions
- Keep repository terminal-only; no Electron desktop app in this version.
- Ordinary Windows users should download and double-click `DreamSeed-Code-0.2.0-Setup.exe`.
- The full zip remains the fallback if Windows blocks the exe.
- Do not publish private provider configs, legacy history, memory candidates, logs, cache, `.dreamseed-memory/`, `dist/`, `node_modules/`, or wheelhouse/vendor dirs.
- MemPalace-only users install from source with `pip install -e ".[mcp]"`.

## Open Loops
- Existing uncommitted README example change remains outside the latest code pass; README top DreamSeed Contest template must remain untouched.
- The new Lite Kernel productization changes are local only; they have passed smoke checks but are not committed, packaged, pushed, or uploaded yet.
- Real external-user smoke is still useful: download `DreamSeed-Code-0.2.0-Setup.exe`, double-click, then run `dreamseed --help` and `dreamseed` on another Windows machine.
- The EXE is unsigned, so Windows SmartScreen may warn. If this becomes a problem, future release work should add code signing or keep the full zip as the low-friction fallback.
- Terminal UI is improved but still the main product-polish track: next refinements could make `/resume` interactive with arrow navigation, improve tool-result collapse/expand, and make approval prompts more like Claude Code/Codex terminal UX.

## Next Step
Continue code/system optimization with another focused pass: inspect remaining REST/API typed parameter parity, batch operation surfaces, or terminal-agent runtime polish, then run full tests before any push.

## Session Log

### 2026-07-09 17:24
- User asked: continue sustained optimization toward the repo goal, focusing only on code/system quality and preserving the full-test-before-upload rule.
- Work completed: researched recent memory/tool-calling risk around memory-induced tool drift; audited OpenAI and LangChain adapters after SDK/REST/MCP parity work; updated existing OpenAI tool schemas and handlers so `mempalace_remember` forwards `metadata`, `source`, `ttl`, and `tags`, and `mempalace_recall` forwards `room`; updated LangChain StructuredTool schemas/functions with the same parameter support; added tests that verify real metadata persistence and room-filtered recall through both adapters without changing tool count.
- Files touched: `src/mempalace_evolve/adapters/openai_adapter.py`, `src/mempalace_evolve/adapters/langchain_adapter.py`, `tests/test_adapters.py`, `.codex-project/PROJECT_MEMORY.md`; pre-existing `README.md` example change remains unstaged.
- Verification: `tests/test_adapters.py` passed `16 passed, 6 skipped, 1 warning`; targeted adapter/SDK/search set passed `78 passed, 6 skipped, 1 warning`; full suite passed `646 passed, 6 skipped, 1 warning in 66.10s`; `git diff --check` passed with CRLF warnings only; generated-file scan for adaptive baselines/sqlite artifacts returned no source/test pollution.
- Result: OpenAI, LangChain, MCP, REST, and SDK entry points are now closer in write metadata and recall-filter behavior, reducing drift between agent integrations.
- Next suggested move: commit and push this adapter parity pass, then continue with REST typed parameter parity (`ttl`/`tags`) or batch/lifecycle API consistency.

### 2026-07-09 17:08
- User asked: continue sustained optimization toward the repo goal, focusing only on code/system quality and preserving the full-test-before-upload rule.
- Work completed: researched recent agent-memory systems guidance around construction/retrieval/lifecycle consistency; audited the MCP adapter after SDK/CLI/REST lifecycle fixes; added MCP support for SDK write metadata (`metadata`, `source`, `ttl`, `tags`); added MCP lifecycle tools (`purge_expired`, `compress_old_memories`, `consolidate`) with a shared write lock; strengthened MCP tests from object-exists smoke checks into real FastMCP `list_tools()` and `call_tool()` coverage; added an explicit `MEMPALACE_EMBEDDING_BACKEND` switch; made pytest use deterministic hash embeddings; improved hash fallback vectors with lexical features so recall works without ONNX; added metadata fallback for constrained hybrid searches; tuned default Chroma HNSW metadata from high-cost indexing defaults to a write-friendlier balance.
- Files touched: `src/mempalace_evolve/adapters/mcp_server.py`, `src/mempalace_evolve/advanced_query.py`, `src/mempalace_evolve/core/chroma_helper.py`, `src/mempalace_evolve/core/embeddings.py`, `tests/conftest.py`, `tests/test_adapters.py`, `.codex-project/PROJECT_MEMORY.md`; pre-existing `README.md` example change remains unstaged.
- Verification: targeted adapter/embedding/lifecycle/SDK/CLI/performance tests passed `97 passed, 6 skipped, 1 warning`; advanced-query/integration/embedding/performance follow-up passed `60 passed`; full suite passed `642 passed, 6 skipped, 1 warning in 59.95s`; `git diff --check` passed with CRLF warnings only; generated-file scan for adaptive baselines/sqlite artifacts returned no source/test pollution.
- Result: MCP now participates in the same lifecycle and metadata behavior as SDK/CLI/REST, while test runs are faster and deterministic without relying on local ONNX performance.
- Next suggested move: commit and push this MCP/embedding reliability pass, then continue with another code/system audit pass around OpenAI/LangChain adapter parity or terminal-agent runtime polish.

### 2026-07-09 16:30
- User asked: continue sustained optimization toward the repo goal, focusing on code/system quality and preserving the full-test-before-upload rule.
- Work completed: researched REST/lifecycle testing directions for memory systems; audited REST lifecycle endpoints after the SDK/CLI lifecycle fixes; added end-to-end FastAPI tests that write memories through REST, adjust lifecycle metadata through the same palace path, then call `/lifecycle/purge` and `/lifecycle/compress` to verify the endpoints reach the fixed SDK paths.
- Files touched: `tests/test_adapters.py`, `.codex-project/PROJECT_MEMORY.md`; pre-existing `README.md` example change remains unstaged.
- Verification: targeted `tests/test_adapters.py tests/test_lifecycle.py tests/test_sdk_v3.py tests/test_cli.py` passed `62 passed, 6 skipped, 1 warning`; full suite passed `640 passed, 6 skipped, 1 warning in 107.13s`; `git diff --check` passed with CRLF warnings only; generated-file scan for adaptive baselines/sqlite artifacts returned no source/test pollution.
- Result: lifecycle management is now covered across SDK, CLI, and REST surfaces, reducing the risk of one entry point silently drifting from the others.
- Next suggested move: commit and push this REST lifecycle coverage pass, then continue with MCP/API consistency checks.

### 2026-07-09 16:24
- User asked: continue sustained optimization toward the repo goal, focusing on code/system quality and preserving the full-test-before-upload rule.
- Work completed: researched memory-agent lifecycle/retention directions; audited lifecycle public surfaces; found CLI lifecycle commands used an undefined `get_palace()` helper and had duplicated unreachable `purge/compress/consolidate` branches; moved `json` import to module scope without shadowing; removed duplicate branches; reused the already-created `MemPalace` instance; added CLI dispatch tests for `purge`, `compress`, and `consolidate`.
- Files touched: `src/mempalace_evolve/cli.py`, `tests/test_cli.py`, `.codex-project/PROJECT_MEMORY.md`; pre-existing `README.md` change remains unstaged.
- Verification: targeted `tests/test_cli.py tests/test_lifecycle.py tests/test_sdk_v3.py tests/test_async_sdk.py` passed 78/78; full suite passed `640 passed, 4 skipped, 1 warning in 87.24s`; `git diff --check` passed with CRLF warnings only; generated-file scan for adaptive baselines/sqlite artifacts returned no source/test pollution.
- Result: CLI lifecycle commands now execute through the public SDK instead of failing at dispatch, making lifecycle management reachable from CLI, REST, and SDK surfaces.
- Next suggested move: commit and push this CLI lifecycle fix, then continue with REST/API consistency checks.

### 2026-07-09 12:44
- User asked: continue sustained optimization toward the repo goal, focusing on code/system quality and preserving the full-test-before-upload rule.
- Work completed: researched current agent memory guidance around write-manage-read loops, consolidation gating, and preserving raw episodes; found broken SDK lifecycle public methods; fixed `find_ttl_expired()` to accept optional `wing` filtering; fixed sync and async `purge_expired()` to consume the actual expired-item list; fixed sync and async `compress_old_memories()` to pass `max_summary_chars`; replaced fragile `self._chroma._client` archive access with public `chromadb.PersistentClient(path=...)` plus the project embedding function; added SDK regression tests for TTL purge and lifecycle compression.
- Files touched: `src/mempalace_evolve/sdk.py`, `src/mempalace_evolve/async_sdk.py`, `src/mempalace_evolve/core/lifecycle.py`, `tests/test_sdk_v3.py`, `.codex-project/PROJECT_MEMORY.md`; pre-existing `README.md` change remains unstaged.
- Verification: targeted `tests/test_lifecycle.py tests/test_sdk_v3.py tests/test_async_sdk.py` passed 75/75; full suite passed `637 passed, 4 skipped, 1 warning in 80.66s`; `git diff --check` passed with CRLF warnings only; generated-file scan for adaptive baselines/sqlite artifacts returned no source/test pollution.
- Result: SDK lifecycle compression and TTL purge are now executable through public APIs and scoped to the current wing, improving the memory manage phase without changing README/contest template.
- Next suggested move: commit and push this lifecycle SDK fix, then continue with another code/system audit pass.

### 2026-07-09 12:34
- User asked: continue the sustained optimization goal, focusing on code/system quality only and keeping full-test-before-upload discipline.
- Work completed: identified `src/mempalace_evolve/core/.adaptive_baselines.json` as mutable runtime state that was being changed by tests; added `get_baselines_path()` with `MEMPALACE_ADAPTIVE_BASELINES_PATH` override and default runtime storage under `MEMPALACE_ROOT`; made baseline cache path-aware; created parent dirs before atomic save; isolated test baseline storage under `.test_tmp`; deleted the tracked generated baseline JSON and ignored it.
- Files touched: `.gitignore`, `src/mempalace_evolve/core/adaptive_scorer.py`, `tests/conftest.py`, `tests/test_adaptive_scorer.py`, `.codex-project/PROJECT_MEMORY.md`; pre-existing `README.md` change remains unstaged.
- Verification: `tests/test_adaptive_scorer.py` passed 26/26; `tests/test_config.py tests/test_layers.py` passed 53/53; full suite passed `635 passed, 4 skipped, 1 warning in 86.66s`; `git diff --check` passed with CRLF warnings only; `fd -H "adaptive_baselines" . src tests .test_tmp` returned no generated baseline file.
- Result: adaptive scoring no longer writes learned runtime state into package source, so full tests are cleaner and reproducible without mutating tracked source files.
- Next suggested move: commit and push this runtime-state isolation pass, then inspect remaining README example change separately without touching the DreamSeed Contest template.

### 2026-07-09 12:24
- User asked: continue sustained optimization of `a2328275243/mempalace-evolve`, focus on code/system quality only, preserve README top contest template, avoid unnecessary C drive installs, verify and record every round, and run complete tests before upload.
- Work completed: researched current agent-memory themes (operation standardization, lifecycle/consolidation, dedup/merge, retrieval stability); installed dev dependencies in repo-local `.venv`; fixed consolidation duplicate detection so length buckets compare adjacent buckets; improved text overlap dedup tokenization for Chinese/no-space text and made `min_overlap_ratio` effective; made `consolidate_daily()` injectable/test-isolated instead of hardcoding `GLOBAL_CHROMA`; isolated tests with repo-local `MEMPALACE_ROOT`; added Chroma delete loop progress guards; optimized SDK `remember()` by avoiding duplicate collection lookup and duplicate ID precheck; expanded `dev` extra so full tests include API/MCP/LangChain extras required by the suite; added regression tests.
- Files touched: `pyproject.toml`, `src/mempalace_evolve/core/chroma_helper.py`, `src/mempalace_evolve/core/consolidation.py`, `src/mempalace_evolve/core/dedup.py`, `src/mempalace_evolve/core/lifecycle.py`, `src/mempalace_evolve/sdk.py`, `tests/conftest.py`, `tests/test_consolidation.py`, `tests/test_dedup.py`, `.codex-project/PROJECT_MEMORY.md`.
- Verification: targeted tests `tests/test_consolidation.py tests/test_dedup.py tests/test_lifecycle.py` passed 81/81; `tests/benchmarks/test_performance.py` passed 6/6 after SDK hot-path optimization; `tests/test_chroma_helper.py` passed 26/26 after delete-loop guard; full suite passed `634 passed, 4 skipped, 1 warning in 83.77s`; `git diff --check` passed with CRLF warnings only.
- Result: core memory dedup/consolidation and Chroma deletion behavior are safer, SDK single-write throughput benchmark is stable, and a fresh dev install can run MCP verification tests.
- Next suggested move: commit and push this focused code/system pass, leaving pre-existing `README.md` and `.adaptive_baselines.json` changes untouched unless the user asks to include them.

### 2026-06-22 15:45
- User asked: implement the prioritized Lite Kernel improvements and update the terminal UI based on the old/new kernel comparison.
- Work completed: updated `bin/dreamseed-lite-kernel.js` with native DreamSeed history listing/resume/rename/archive/delete/cleanup; added `/history`, `/mcp`, `/permissions`, `/doctor`, `/cost`; added `MultiEdit`; added tool progress streaming via `tool_delta`; summarized/collapsed tool output in the terminal UI; added Write/Edit/MultiEdit change previews; added MCP `Content-Length` framing support, default stdio type, and basic HTTP JSON-RPC MCP transport; added segmented compact summary cache path; loaded local skill descriptions from `SKILL.md`; injected agent body into Task subagents; added shell fallback resolution and PowerShell hook fallback; connected custom dangerous command settings; improved rg-first Glob/Grep; fixed repeated-failure matching by tool id.
- Files touched: `bin/dreamseed-lite-kernel.js`, `.codex-project/PROJECT_MEMORY.md`.
- Verification: `vendor\node\win-x64\node.exe --check bin\dreamseed-lite-kernel.js` passed; scripted interactive smoke for `/doctor`, `/history list`, `/permissions`, `/mcp`, `/exit` passed; mock provider tool-loop smoke showed `tool_use`, `tool_delta`, and `tool_result`; native history smoke created and resumed a DreamSeed session; Content-Length MCP smoke discovered and invoked `mcp__mock__echo`; MultiEdit smoke passed inside a project-local temp directory; `git diff --check` passed with only CRLF warning; smoke temp directories were cleaned.
- Result: Lite Kernel is substantially closer to a product-grade terminal agent, with better history, MCP, tools, slash UX, and live feedback. Changes are local only.
- Next suggested move: run one real provider task using the configured DreamSeed/DeepSeek bridge, then package and push if the behavior feels right.

### 2026-06-22 14:05
- User asked: list all identifiable features in the old 13MB kernel and show where each feature appears in that kernel.
- Work completed: statically scanned `D:\Agent\DreamSeed-Packaging-Workspace\runtime\claude-cli.js` without modifying it; generated raw and filtered feature maps under `C:\Users\Lenovo\AppData\Local\Temp\dreamseed-old-kernel-analysis-20260622-140322\`; identified feature anchors for CLI, REPL, Anthropic Messages/SSE, tool loop, builtin tools, MCP, hooks, permissions, compact/history/resume, subagents, skills/plugins, UI, cancellation, git/worktree, update, telemetry, settings, OAuth, Bedrock, Vertex, Azure/Foundry, and Copilot.
- Files touched: `.codex-project/PROJECT_MEMORY.md`, `.codex-project/OLD_KERNEL_FEATURE_MAP.md`.
- Verification: confirmed old kernel path, size 13,047,716 bytes, 12,985,767 chars, 16,668 lines; generated `old-kernel-feature-map-filtered.md` and `.json` with offset/line/column/snippet anchors.
- Result: old kernel feature map is available for planning which modules to keep/rewrite in the Lite Kernel, and the durable local summary is saved at `.codex-project/OLD_KERNEL_FEATURE_MAP.md`.
- Next suggested move: compare this old-kernel feature map against `bin\dreamseed-lite-kernel.js` and decide which missing features should be reimplemented versus intentionally omitted.

### 2026-06-21 20:45
- User asked: rebuild the installer, upload it to GitHub, and copy one copy to the USB drive.
- Work completed: committed terminal UI5 changes in `e74ce14`; fixed full-kit privacy scan false positive for bundled Node `vendor\node\win-x64\node_modules`; fixed Windows PowerShell 5.1 compatibility by replacing `System.IO.Path.GetRelativePath` with a local helper; committed the packaging fix in `0332abd`; rebuilt full offline kit and single-file `Setup.exe`; pushed `master`; force-moved tag `dreamseed-code-v0.2.0` to `0332abd`; uploaded refreshed Release assets with `gh release upload --clobber`; copied the refreshed installer to `G:\DreamSeed-Code-0.2.0-Setup.exe`.
- Files touched: `bin/dreamseed-lite-kernel.js`, `scripts/build-windows-full-kit.ps1`, `.codex-project/PROJECT_MEMORY.md`.
- Verification: `vendor\node\win-x64\node.exe --check bin\dreamseed-lite-kernel.js` passed; PowerShell parser check passed for `scripts\build-windows-full-kit.ps1`; `git diff --check` passed with only CRLF warnings; full-kit offline smoke passed; `Setup.exe` isolated smoke passed; zip private-path scan passed; GitHub Release reports refreshed assets with SHA256 digests; USB copy hash matches local installer hash.
- Result: current GitHub Release `dreamseed-code-v0.2.0` is refreshed and ready for external testing; the USB installer copy is also ready.
- Next suggested move: test the installer on a different Windows machine and continue terminal UI polish based on the real-user feel.

### 2026-06-21 19:51
- User asked: use Computer Use if possible, deeply inspect old-kernel UI ideas, and polish the Lite Kernel terminal UI so it feels closer to the old kernel / Claude Code style.
- Work completed: attempted Computer Use per plugin instructions, but `sky.list_apps()` timed out twice after bootstrap, so Windows UI automation was stopped per policy; inspected the old minified 13MB kernel for visible UI symbols and terminal semantics; upgraded `bin/dreamseed-lite-kernel.js` UI to UI5 with Unicode-safe `\u` box glyphs, ASCII fallback, slash command palette, stable user input box, command selection with Up/Down/Tab/Enter, assistant reply block with right border closure, tool running/done/error rows, approval/info/status blocks, queued MCP notices during prompts/assistant replies, scripted input smoke support, and display-width-aware layout for Chinese/Unicode text.
- Files touched: `bin/dreamseed-lite-kernel.js`, `.codex-project/PROJECT_MEMORY.md`.
- Verification: `vendor\node\win-x64\node.exe --check bin\dreamseed-lite-kernel.js` passed; `git diff --check` passed with only the existing CRLF warning; `slash-ui5-smoke-ok` passed for `/`, `/r`, `/model`, `/status`, `/clear`, `/exit`; `ui5-stream-smoke-ok` passed with a local mock Anthropic SSE provider and Chinese streaming text; Select-String found no mojibake glyph remnants (`鈺`, `鈹`, `锘`) and no stale `process.stdout.write(result)` / cursor variable remnants.
- Result: UI5 is local only, not committed, not packaged, not uploaded. Latest non-installing temp preview is `C:\Users\Lenovo\AppData\Local\Temp\dreamseed-kernel-preview-ui5-20260621-195139\OPEN-DREAMSEED-UI5-PREVIEW.cmd`.
- Next suggested move: user visually tests UI5 preview; if acceptable, rebuild full kit and Setup.exe, then commit/push/release.

### 2026-06-21 18:16
- User asked: improve terminal UI because the preview looked poor, especially requiring `/` to show available slash commands such as `/resume`.
- Work completed: added a slash command registry; added a box-style terminal banner, assistant reply block, user input box, live TTY slash command panel, Up/Down selection, Tab completion for the selected command, Enter-to-run selected command for incomplete slash prefixes, slash-prefix protection so `/r` shows matches instead of being sent to the model, queued MCP status notices so they do not overwrite the active input line, and a scripted-input queue for reliable pipe/smoke tests.
- Files touched: `bin/dreamseed-lite-kernel.js`, `.codex-project/PROJECT_MEMORY.md`.
- Verification: `vendor\node\win-x64\node.exe --check bin\dreamseed-lite-kernel.js` passed; `git diff --check` passed; scripted slash UI2 smoke with `/`, `/r`, `/exit` passed and showed `/resume`; opened a non-installing temp preview window via `C:\Users\Lenovo\AppData\Local\Temp\dreamseed-kernel-preview-ui2-20260621-184241\OPEN-DREAMSEED-UI2-PREVIEW.cmd`.
- Result: terminal UI is improved locally but not committed, packaged, pushed, or uploaded yet.
- Next suggested move: user reviews the preview window; if acceptable, run package scripts and refresh GitHub Release assets.

### 2026-06-21 17:38
- User asked: confirm UI is the next main optimization direction, copy the fixed installer to USB, and push it to the repository/release.
- Work completed: fixed Lite Kernel terminal startup so the prompt appears immediately; changed MCP initialization to background/parallel loading; added lightweight terminal UI helpers, assistant prefix, and tool status lines; prevented setup smoke tests from writing user PATH; added build script guard against self-copy deleting bundled Node; rebuilt full zip/source zip/Setup.exe; copied installer to `G:\DreamSeed-Code-0.2.0-Setup.exe`; pushed commit `3c2d952`; moved tag `dreamseed-code-v0.2.0`; refreshed GitHub Release assets and notes.
- Files touched: `bin/dreamseed-lite-kernel.js`, `scripts/build-windows-full-kit.ps1`, `scripts/build-windows-setup-exe.ps1`, `scripts/setup-bootstrap.ps1`, `.codex-project/PROJECT_MEMORY.md`.
- Verification: Node syntax check passed; PowerShell parser checks passed; `git diff --check` passed; interactive `/exit` startup path measured ~0.14s in local smoke; full-kit offline smoke passed; Setup.exe isolated smoke passed; Release assets list includes refreshed `DreamSeed-Code-0.2.0-Setup.exe`, full zip, and source zip; USB copy hash matches local hash `B8EF065893BBB5FEC90D405A37BB05F564530054D3F5AE19AA519B8FE655DC2B`.
- Result: refreshed v0.2.0 release is published with improved terminal startup/UI and safer installer smoke behavior.
- Next suggested move: continue UI polish as the main next track: better tool cards, command progress, approval prompt layout, `/resume` display, and less noisy MCP status.

### 2026-06-21 13:22
- User asked: make DreamSeed installable as a direct `.exe` so ordinary users do not need to unzip and run scripts manually.
- Work completed: added `scripts/setup-bootstrap.ps1` and `scripts/build-windows-setup-exe.ps1`; changed README to recommend `DreamSeed-Code-0.2.0-Setup.exe`; built the EXE; copied it to `G:\DreamSeed-Code-0.2.0-Setup.exe`; committed and pushed `248d900`; moved tag `dreamseed-code-v0.2.0`; uploaded the EXE and refreshed source zip on the GitHub Release.
- Files touched: `README.md`, `package.json`, `scripts/setup-bootstrap.ps1`, `scripts/build-windows-setup-exe.ps1`, `.codex-project/PROJECT_MEMORY.md`.
- Verification: PowerShell parse checks passed; `git diff --check` passed; generated EXE is 142,160,896 bytes; isolated EXE smoke passed (`dreamseed.cmd` created and `dreamseed --help` succeeded); GitHub Release asset list includes `DreamSeed-Code-0.2.0-Setup.exe`; U disk copy hash matches local hash `FF731C58D7305E12FFC7FC15B80A93507A60262483C23FAFA889FB9603D43142`.
- Result: ordinary Windows users can now download one EXE and double-click to install DreamSeed Code terminal agent with bundled Node/Python/MemPalace dependencies.
- Next suggested move: test the EXE on a separate Windows machine and watch for SmartScreen/permission prompts.

### 2026-06-21 12:03
- User asked: create a Windows full offline kit so users do not need winget or first-install pip network.
- Work completed: added `scripts/build-windows-full-kit.ps1`; installer now prefers `vendor/node/win-x64/node.exe`, `vendor/python/win-x64/python.exe`, and `vendor/python-wheels`; wheelhouse builds from current repo; README and release notes explain source vs full kit.
- Files touched: `.gitignore`, `README.md`, `package.json`, `scripts/build-windows-full-kit.ps1`, `scripts/build-python-wheelhouse.ps1`, `scripts/install-dreamseed.ps1`, `scripts/install-python-deps.ps1`.
- Verification: PowerShell syntax checks passed; built bundled Node/Python and 119-wheel wheelhouse; working-tree offline install smoke passed; full-kit zip offline smoke passed; zip contains bundled Node/Python/wheels and no private-data matches.
- Result: pushed `a288a7c`; moved `dreamseed-code-v0.2.0` tag; uploaded `dreamseed-code-0.2.0-source.zip` and `DreamSeed-Code-0.2.0-Windows-Full.zip` to the release.
- Next suggested move: have a real external Windows user download the full package, install, configure provider, and run `dreamseed --print "Reply exactly: ok"`.

### 2026-06-21 11:14
- User asked: make the installer lower-friction by detecting Node/Python, installing missing runtimes with winget, installing Python dependencies, and running a self-test.
- Work completed: updated `scripts/install-dreamseed.ps1`, `scripts/install-python-deps.ps1`, and `README.md`; pushed commit `b08c0ba`; moved tag `dreamseed-code-v0.2.0`; replaced release zip.
- Files touched: `README.md`, `scripts/install-dreamseed.ps1`, `scripts/install-python-deps.ps1`.
- Verification: PowerShell syntax checks passed; explicit Node/Python install smoke passed; missing Node with `-NoAutoInstall` fails fast with a clear message; zip archive includes installer and `.dreamseed`, with no private-data matches.
- Result: Windows users no longer need to preinstall Node/Python if winget is available; otherwise the installer tells them exactly what to install.
- Next suggested move: run a true clean-user install on another Windows machine using the GitHub release zip.

## History Compression
- 2026-06-20: Integrated DreamSeed Code Lite Kernel terminal agent into the MemPalace Evolve repo, removed old desktop installer artifacts, pushed commit `f2481e5`, created release `dreamseed-code-v0.2.0` with `dreamseed-code-0.2.0-source.zip`.
