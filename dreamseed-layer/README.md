# DreamSeed Code

DreamSeed Code 是本仓库自带的本地智能体，和 MemPalace 自动进化记忆系统配套使用。它提供 `dreamseed` 终端命令、DreamSeed Desktop 桌面端、模型管理器、MCP 管理、审批门禁、任务队列、本地历史和检查脚本。

如果你只想使用 MemPalace 记忆系统，可以回到仓库根目录安装 Python 包；如果你想使用完整组合，就在安装根目录 Python 包后进入 `dreamseed-layer/` 安装 DreamSeed。

DreamSeed 自带轻量 Provider Bridge，可以把 OpenAI-compatible 上游模型接成本地可用的接口，例如 GLM、DeepSeek-compatible、Gemini-compatible 或本地 Ollama 服务，不要求用户先安装 CC Switch。

Start here:

- [Installation](docs/installation.md)
- [DreamSeed Code guide](DREAMSEED.md)
- [Agent operating guide](AGENTS.md)

Install the command from a clone:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-dreamseed.ps1
dreamseed --help
```

or with npm:

```powershell
npm install -g .
dreamseed --help
```

Configure and switch model endpoints without CC Switch:

```powershell
dreamseed manager
```

This opens the local DreamSeed Model Manager before you enter the agent. The manager lets you add, edit, delete, test, and switch saved model endpoints. It writes your private config to `%APPDATA%\DreamSeed\providers.local.json` by default and does not publish API keys.

Open the native desktop app:

```powershell
dreamseed desktop
```

or from source:

```powershell
node bin\dreamseed-agent.js desktop
```

DreamSeed Desktop is an Electron app under `desktop/`. It shares the same local provider config, local history archive, approval gate, task runner state, and release audit rules as the terminal CLI. It is meant for users who prefer a desktop workspace instead of a terminal-only workflow.

Desktop capabilities:

| Area | What it does |
| --- | --- |
| Project sidebar | Shows project groups, useful history sessions, desktop-created threads, and recent task context. |
| Model panel | Adds, edits, deletes, tests, diagnoses, and switches providers using the same config read by `dreamseed provider ...`. |
| Conversation view | Shows useful project history, imported legacy sessions, desktop threads, and concise model/session summaries. |
| Task Runner | Runs multiple tasks with independent status, output, cancellation, artifacts, and persisted queue state. |
| Workbench | Provides a review-oriented diff viewer, command output area, and terminal split for project work. |
| Approval gate | Auto-allows low-risk reads, asks for high-risk actions, and blocks critical destructive operations. |
| Artifacts timeline | Keeps local command/file/result/failure artifacts out of Git. |
| Health surface | Mirrors provider, MCP, hook, memory, history, eval, and audit checks for non-terminal users. |

Terminal and desktop are one system:

- Models added in the desktop model panel are visible from `dreamseed provider list/status/use`.
- Models configured in the terminal are visible in the desktop model panel.
- Desktop task threads are written to shared local history so `/resume` can recover useful completed work.
- Imported legacy history stays private in `legacy-history/`; desktop reads summaries and entry points without injecting all history into prompts.
- Memory still follows the candidate review path. Desktop does not write directly to MemPalace.

For Windows desktop users, install a shortcut after dependencies are installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-dreamseed-desktop-shortcut.ps1
```

If double-clicking the shortcut does nothing, check `%APPDATA%\DreamSeed\logs\dreamseed-desktop-launch.log`, then rerun `npm install` and the shortcut installer from the current source directory.

Import old compatible-agent history into DreamSeed's private archive:

```powershell
python scripts\import_claude_history.py import
python scripts\import_claude_history.py search "keyword"
python scripts\import_claude_history.py sync-native-resume --target-cwd .
dreamseed
/resume
```

The import keeps raw history in `legacy-history/` and writes only reviewable summaries to `memory-candidates/`; neither directory is published. `sync-native-resume` mirrors archive entries into the private local native resume index so DreamSeed's normal `/resume` picker can find them. It does not write to MemPalace.

Controlled self-evolution:

```powershell
dreamseed evolve status
dreamseed evolve propose --title "Improve verification note" --problem "A repeated failure needs a durable fix" --change "Tighten the relevant skill or script"
dreamseed evolve inspect <proposal-id>
dreamseed evolve apply <proposal-id> --yes
dreamseed evolve verify <proposal-id>
dreamseed evolve memory-candidate <proposal-id> --lesson "Reusable lesson after verification"
```

`propose` creates a reviewable candidate under `self-evolve-candidates/`. It does not modify source files. To apply, stage replacement files under `self-evolve-candidates/<proposal-id>/files/<relative-path>` and run `apply --yes`. The apply path backs up originals under `self-evolve-backups/`, blocks private paths and likely secrets, and runs the DreamSeed audit by default. Both local self-evolution directories are excluded from Git.

Local smoke checks:

```powershell
$env:DREAMSEED_COMPAT_KERNEL_JS = "<path-to-compatible-kernel.js>"
node bin\dreamseed-agent.js --help
node bin\dreamseed-agent.js fast --print "Output exactly: ok"
node bin\dreamseed-agent.js compat --help
node bin\dreamseed-agent.js manager --no-open
node bin\dreamseed-agent.js provider status
node --check desktop\desktop.js
npm install
node bin\dreamseed-agent.js desktop --smoke
node bin\dreamseed-agent.js desktop --render-smoke
node scripts\provider_bridge.mjs --config "$env:APPDATA\DreamSeed\providers.local.json"
python scripts\dreamseed_self_evolve.py status
scripts\dreamseed-memory-bridge.ps1 -Mode status
python scripts\import_claude_history.py status
scripts\install-python-deps.ps1
scripts\dreamseed-audit.ps1
scripts\package-dreamseed.ps1
```
