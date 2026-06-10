<!--
╔══════════════════════════════════════════════════════════════════════╗
║  DreamSeed 种梦计划 — AI创造者大赛  官方 README 模板                ║
║                                                                      ║
║  使用说明：                                                          ║
║  1. 将本模板放在参赛仓库根目录 README.md 的顶部                       ║
║  2. 头图使用 DreamField 官方公开活动图片地址                         ║
║  3. 请保留 DREAMFIELD_README_HEADER_START / END 标识                 ║
║  4. 分割线以下供创作者自由编写项目内容                               ║
╚══════════════════════════════════════════════════════════════════════╝
-->

<!-- DREAMFIELD_README_HEADER_START -->

<p align="center">
  <a href="https://www.dreamfield.top">
    <img src="https://www.dreamfield.top/dream-field/contest-readme/assets/dreamseed-readme-banner.png" alt="DreamSeed 种梦计划参赛作品" width="100%" />
  </a>
</p>

<!-- DREAMFIELD_README_HEADER_END -->

---

# MemPalace Evolve + DreamSeed Code

> MemPalace Evolve 是一个给本地智能体使用的自动进化记忆系统。这个仓库里还带了一个自制智能体 DreamSeed Code，支持终端和桌面端，可以直接把 MemPalace 的记忆能力用起来。

## 项目定位

这个项目主要做两件事：

| 部分 | 路径 | 作用 |
| --- | --- | --- |
| MemPalace Evolve | `src/mempalace_evolve/` | 自动进化记忆系统。负责记忆存储、检索、候选审核、评分、去重、知识图谱、SDK、REST 和 MCP 适配。 |
| DreamSeed Code | `dreamseed-layer/` | 仓库自带的本地智能体。支持终端、桌面端、模型管理、MCP 管理、审批门禁、任务队列和本地评测。 |
| Python 启动入口 | `dreamseed_layer/` | 让 Python 包安装后也能启动 DreamSeed。 |
| 示例与测试 | `examples/`, `tests/` | MemPalace 接入示例和回归测试。 |

核心原则：

- 私有模型密钥、历史记录、memory candidates、logs、cache 不进入 Git。
- DreamSeed 默认不依赖 CC Switch，使用内置 OpenAI-compatible Provider Bridge。
- 记忆系统采用候选池审核，不允许 stop hook 直接写长期记忆。
- 高风险 MCP 必须有 registry、risk tag、doctor 检查和显式启用流程。
- 自我迭代走 proposal-first、review-first、test-first，不自动改源码。

## 选择你的安装方式

如果你只需要 MemPalace 自动进化记忆系统，只装 Python 部分即可：

```powershell
git clone https://github.com/<your-name>/mempalace-evolve.git
cd mempalace-evolve
python -m pip install -e .
python -m mempalace_evolve.cli doctor
python -m mempalace_evolve.cli demo
```

可选能力按需安装：

```powershell
python -m pip install -e ".[mcp]"
python -m pip install -e ".[api]"
python -m pip install -e ".[langchain]"
```

如果你想用 MemPalace + DreamSeed 智能体的完整组合，Windows 用户可以直接下载整个仓库：

1. 在 GitHub 页面点击 `Code`。
2. 选择 `Download ZIP`，下载的是整个仓库源码。
3. 解压到一个英文路径或简单路径，例如 `D:\DreamSeed\mempalace-evolve`。
4. 打开 PowerShell，进入仓库目录。

然后执行：

```powershell
cd D:\DreamSeed\mempalace-evolve
python -m pip install -e .
cd dreamseed-layer
npm install
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-dreamseed.ps1
dreamseed --help
```

配置模型：

```powershell
dreamseed provider setup
dreamseed provider status
dreamseed provider test
```

进入终端智能体：

```powershell
dreamseed
```

打开桌面端：

```powershell
dreamseed desktop
```

打开模型管理器：

```powershell
dreamseed manager
```

模型管理器支持在进入智能体前添加、删除、编辑、测试和切换模型。普通 OpenAI-compatible 服务通常只需要：

- Base URL
- API Key
- Model Name

私有配置默认写入本机用户目录，不提交到仓库。


## MemPalace 常用入口

```powershell
mempalace doctor
mempalace demo
mempalace playground
mempalace-mcp
mempalace-server
```

## DreamSeed Desktop 桌面端

DreamSeed Desktop 是 `dreamseed-layer/desktop/` 下的 Electron 原生桌面端。它不是一个独立网页，也不是只套一层壳的模型管理器，而是和终端共用同一套本地后端、模型配置、项目配置、历史记录、任务队列、审批策略和发布审计。

桌面端的设计目标是让普通用户可以像使用桌面软件一样使用 DreamSeed，同时保留终端入口给工程用户和自动化脚本：

- 想快速进入智能体，可以运行 `dreamseed`。
- 想先配置模型，可以运行 `dreamseed manager` 或打开桌面端模型面板。
- 想用桌面软件管理项目、历史、任务和 artifacts，可以运行 `dreamseed desktop`。
- 想做发布检查，可以继续使用 `dreamseed eval`、`dreamseed doctor`、`dreamseed-audit.ps1` 和打包脚本。

仓库默认不提交 `node_modules/`。第一次在源码中运行桌面端时，需要安装 Node 依赖：

```powershell
cd dreamseed-layer
npm install
```

安装后可以直接启动：

```powershell
dreamseed desktop
```

如果还没有把 `dreamseed` 命令安装到 PATH，也可以从源码启动：

```powershell
cd dreamseed-layer
node bin\dreamseed-agent.js desktop
```

Windows 用户可以安装桌面快捷方式：

```powershell
cd dreamseed-layer
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-dreamseed-desktop-shortcut.ps1
```

快捷方式只启动本地源码中的 DreamSeed，不会上传密钥或历史。

### 桌面端功能范围

| 区域 | 功能 | 说明 |
| --- | --- | --- |
| 左侧项目栏 | 项目列表、按时间/项目折叠、历史入口 | 适合同时管理多个代码项目。桌面端新建的项目会写入本地 desktop config，终端仍可通过同一套历史和配置访问。 |
| 会话区 | 类 Codex 风格的项目线程、对话消息、模型摘要 | 每个项目可以有自己的历史线程。短噪声历史会被过滤，长期可恢复历史通过 `/resume` 进入上下文。 |
| 模型栏 | 当前模型、Provider、健康状态 | 读取与终端相同的 provider 配置。桌面端新增、编辑、切换模型后，终端 `dreamseed provider list/status/use` 能看到同一份配置。 |
| 模型抽屉 | 新建、删除、编辑、测试模型 | 支持 OpenAI-compatible、GLM、DeepSeek-compatible、Gemini-compatible、Ollama/local-compatible 等模板。API key 可以保存在本机私有配置，也可以用环境变量名。 |
| Task Runner | 多任务队列、并发数、取消、状态持久化 | 每个任务有独立状态：queued、running、done、failed、cancelled。默认并发较保守，避免把本机和模型接口打满。 |
| 审批弹窗 | 高风险操作确认 | 低风险读取自动放行；写文件、联网写入、执行危险命令、桌面控制等高风险动作需要显式确认；关键危险操作默认拒绝。 |
| Workbench | Diff viewer、内嵌 terminal、命令输出 | 用于查看变更、运行命令、定位失败原因。长输出可以走压缩策略，保留错误、路径、行号和最后 N 行。 |
| Artifacts | 命令、文件、结果、失败工件时间线 | 桌面端和 eval 产生的本地工件进入 logs 或本地 runtime 目录，默认不进入 Git。 |
| Health | Provider、MCP、hook、history、发布检查状态 | 对应终端里的 `doctor`、`eval`、`audit` 命令，方便非终端用户看到当前系统是否健康。 |

### 终端与桌面端是一体的

DreamSeed 的桌面端和终端入口共用同一个本地运行根目录。默认情况下：

- 模型配置读取顺序和终端一致，优先使用本机私有 `providers.local.json`，不会把密钥提交进仓库。
- 桌面端模型面板新增的模型，终端可以通过 `dreamseed provider list`、`dreamseed provider status`、`dreamseed provider use NAME` 使用。
- 终端配置的模型，桌面端模型面板也能显示、测试和切换。
- 桌面端创建的任务线程会写入本地可恢复历史，终端 `/resume` 可以看到有价值的完成任务。
- 终端历史导入后会进入 `legacy-history/` 私有目录，桌面端可以读取摘要和会话入口，但不会把全部旧历史塞进默认提示词。
- 记忆仍然走候选池审核，桌面端不会绕过 `memory-candidates -> reviewed -> promote-reviewed -> MemPalace` 这条路径。

### 桌面端模型配置

添加新模型时最少需要三项：

```text
Base URL
API Key 或 API Key Env
Model Name
```

推荐普通用户直接填 API Key。推荐发布、团队或 CI 场景使用 `API Key Env`，例如：

```powershell
$env:DREAMSEED_API_KEY = "your-private-key"
dreamseed provider setup --name glm --base-url https://example.com/v1 --model glm-5.1 --key-env DREAMSEED_API_KEY
```

桌面端里 `API Key Env` 填的是环境变量名称，不是密钥本身。这样仓库、日志和截图里只会出现变量名，不会出现真实 key。

### 桌面端校验命令

发布前建议至少跑这几项：

```powershell
cd dreamseed-layer
node --check desktop\desktop.js
node bin\dreamseed-agent.js desktop --smoke
node bin\dreamseed-agent.js desktop --render-smoke
```

`--render-smoke` 会以隐藏 Electron 窗口启动桌面端，并检查项目树、模型面板、任务队列、diff viewer、terminal 和 artifacts 区域是否能正常渲染。它用于发布前回归，不会打开用户可见窗口。

桌面端如果双击快捷方式无反应，先看本地日志：

```powershell
$env:APPDATA\DreamSeed\logs\dreamseed-desktop-launch.log
```

常见原因是没有安装 Node 依赖、Electron 未安装、快捷方式指向的源码目录已移动，或被系统策略拦截。重新运行 `npm install` 和 `scripts\install-dreamseed-desktop-shortcut.ps1` 通常可以修复。

## DreamSeed 常用命令

```powershell
dreamseed provider status
dreamseed provider test
dreamseed history status
dreamseed memory audit
dreamseed mcp list
dreamseed doctor context
dreamseed doctor mcp
dreamseed doctor hooks
dreamseed approval audit
dreamseed eval run --suite smoke
```

桌面端和终端共用同一套本地历史与模型配置：

- 终端完成的任务会写入 DreamSeed 本地历史。
- 桌面端任务线程会同步进入可恢复历史。
- `/resume` 只加载选中的历史上下文，不把所有旧历史塞进默认提示词。

## 记忆安全模型

DreamSeed 不直接把 session 结束内容写入长期记忆，而是走候选池：

```text
memory-candidates -> reviewed -> memory_promote.py promote-reviewed -> MemPalace
```

候选会被评分和过滤：

- 稳定偏好、项目决策、路径、错误模式更容易保留。
- 空 OK、继续、临时调试、长日志、泛泛 checkpoint 会被降权或拒绝。
- 疑似密钥不会在审计输出中打印全文。

相关命令：

```powershell
cd dreamseed-layer
dreamseed memory candidates
dreamseed memory review
dreamseed memory reject-noisy
dreamseed memory promote-reviewed
dreamseed memory audit
```

## MCP 与审批门禁

MCP 治理由 `dreamseed-layer/config/mcp.registry.json` 管理。高风险能力需要明确标签，例如：

- `browser`
- `desktop`
- `network-write`
- `filesystem-write`
- `credentialed`

审批门禁用于模拟 Codex 风格的风险请求：低风险读操作自动放行，高风险命令请求确认，关键危险操作直接拒绝。

```powershell
cd dreamseed-layer
dreamseed mcp list
dreamseed doctor mcp
dreamseed approval status
dreamseed approval audit
dreamseed approval check --tool Bash --command "git status --short"
```

## 自我迭代

DreamSeed 支持受控自进化，但不会自动改源码。所有改动先进入 proposal：

```powershell
cd dreamseed-layer
dreamseed evolve status
dreamseed evolve propose
dreamseed evolve score <id>
dreamseed evolve test <id>
dreamseed evolve apply <id> --yes
dreamseed evolve rollback <id> --yes
```

apply 前会经过路径守卫、secret scan、brand audit 和 targeted smoke。失败 proposal 会归档到本地私有目录，不进入 Git。

## 发布到 GitHub

推荐直接上传整个仓库。用户只想用 MemPalace，就在仓库根目录安装 Python 包；用户想用完整组合，就进入 `dreamseed-layer/` 安装 DreamSeed 终端和桌面端。

发布前建议通过：

```powershell
python -B -m pytest
cd dreamseed-layer
node bin\dreamseed-agent.js --help
node --check desktop\desktop.js
node bin\dreamseed-agent.js desktop --smoke
python scripts\brand_audit.py scan --strict
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dreamseed-audit.ps1
```

`scripts\package-dreamseed.ps1` 仍然保留，主要用于本地验收和检查发布内容是否会误带私有数据。正常发布不需要把 `dist/` 上传到仓库。

## 仓库开发检查

根项目 Python 测试：

```powershell
python -m pytest
```

DreamSeed 层检查：

```powershell
cd dreamseed-layer
node --check desktop\desktop.js
node bin\dreamseed-agent.js desktop --render-smoke
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dreamseed-audit.ps1
```

## 不应提交的内容

这些内容必须留在本机：

- `providers.local.json`
- `legacy-history/`
- `memory-candidates/`
- `self-evolve-candidates/`
- `self-evolve-backups/`
- `logs/`
- `cache/`
- `.dreamseed-runtime/`
- 任意 API key、token、cookie、数据库文件

## License

MIT. See [LICENSE](LICENSE).
