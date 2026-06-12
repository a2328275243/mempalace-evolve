<!--
=========================================================================
 DreamSeed 种梦计划 AI 创造者大赛 README 模板
 使用说明：
 1. 请保留 DREAMFIELD_README_HEADER_START / END 标识。
 2. 顶部横幅使用 DreamField 官方公开活动图片地址。
 3. 分割线以下为项目正文。
=========================================================================
-->

<!-- DREAMFIELD_README_HEADER_START -->

<p align="center">
  <a href="https://www.dreamfield.top">
    <img src="https://www.dreamfield.top/dream-field/contest-readme/assets/dreamseed-readme-banner.png" alt="DreamSeed 种梦计划参赛作品" width="100%" />
  </a>
</p>

<!-- DREAMFIELD_README_HEADER_END -->

---

# MemPalace Evolve

MemPalace Evolve 是一个面向本地智能体的自动进化记忆系统。它把项目决策、稳定偏好、错误模式和可复用经验整理成可检索、可审核、可迭代的长期记忆。

这个仓库提供两个入口：

| 入口 | 适合谁 | 安装方式 |
| --- | --- | --- |
| MemPalace 自动进化记忆系统 | 想把长期记忆接到 Claude Code、Cursor 或自制智能体里的用户 | 安装这个 Python 包 |
| DreamSeed Code Windows 安装器 | 想直接使用 DreamSeed 桌面端和终端端的 Windows 用户 | 下载并运行安装器 |

DreamSeed Code 已经内置 MemPalace。只使用 DreamSeed Code 的用户，不需要额外安装 MemPalace。

## 只安装 MemPalace

```powershell
git clone https://github.com/a2328275243/mempalace-evolve.git
cd mempalace-evolve
python -m pip install -e .
mempalace doctor
```

安装后可以直接写入和检索记忆：

```powershell
mempalace remember "This project uses FastAPI for the backend" --room decisions
mempalace recall "backend framework"
```

## 接入 Claude Code / Cursor

如果你的智能体支持 MCP，推荐安装 MCP 版本：

```powershell
python -m pip install -e ".[mcp]"
mempalace setup
```

`mempalace setup` 会尝试检测 Claude Code / Cursor，并帮你写入 MCP 配置。完成后重启对应客户端即可使用 MemPalace。

手动配置时，MCP server 命令是：

```powershell
mempalace-mcp
```

最小 MCP 配置示例：

```json
{
  "mcpServers": {
    "mempalace": {
      "command": "mempalace-mcp",
      "args": []
    }
  }
}
```

## 接入自制智能体

Python SDK：

```python
from mempalace_evolve import MemPalace

palace = MemPalace()
palace.remember("User prefers concise answers", room="preferences")
results = palace.recall("user answer style")
```

HTTP API：

```powershell
python -m pip install -e ".[api]"
mempalace serve --port 8765
```

## 安装 DreamSeed Code

普通 Windows 用户不需要下载 DreamSeed 源码目录。直接在 Releases 下载并运行：

```text
DreamSeed-Code-0.1.1-Setup.exe
```

安装器会让你选择安装路径，并同时安装：

- DreamSeed Desktop 桌面端
- `dreamseed` 终端命令
- 模型管理和 Provider 配置
- 项目历史和 `/resume`
- 内置终端、diff viewer、任务线程和风险审批
- MemPalace 记忆候选池审核系统

安装完成后，可以双击桌面上的 `DreamSeed Desktop`，也可以在终端运行：

```powershell
dreamseed
```

桌面端和终端端是一体的：它们使用同一套模型配置、同一份项目历史、同一个 `/resume` 归档和同一个 MemPalace 记忆系统。

## 备用安装方式

如果你下载的是整个仓库，也可以双击或运行：

```powershell
DreamSeed-Setup-Windows.cmd
```

它会优先使用仓库 `installers` 文件夹里的完整离线包。只有本地包缺失或不完整时，才会尝试从 GitHub 下载。

如果下载很慢，可以指定代理：

```powershell
.\DreamSeed-Setup-Windows.ps1 -Proxy http://127.0.0.1:7897
```

已经安装过的用户可以直接更新：

```powershell
dreamseed update
```

如果旧版本的 `dreamseed` 命令不可用，重新运行 `DreamSeed-Code-0.1.1-Setup.exe` 覆盖安装即可。安装器会保留本地模型配置、历史、记忆和日志。

## DreamSeed Code 功能

- 桌面端：项目侧栏、会话历史、模型切换、任务运行状态、内置终端、diff 查看、工具/MCP/skills 面板。
- 终端端：`dreamseed` 命令、`/resume` 历史恢复、provider 管理、MCP 管理、memory audit、自进化候选、doctor 和 eval。
- 模型管理：支持 OpenAI-compatible、GLM、DeepSeek-compatible、Gemini-compatible、Ollama/local-compatible 等模板。
- 工具治理：MCP registry、风险标签、审批门禁、provider tools-test、hook doctor。
- 记忆治理：Stop hook 只写 memory candidates，长期记忆只允许通过审核路径晋升。

## 记忆不会乱写

MemPalace 的长期记忆默认走审核流程：

```text
memory-candidates -> reviewed -> promote-reviewed -> MemPalace
```

稳定偏好、项目决策、错误模式更容易保留；临时调试、空回复、长日志和泛泛 checkpoint 会被降权或拒绝。
