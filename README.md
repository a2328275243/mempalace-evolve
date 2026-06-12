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

# MemPalace Evolve

MemPalace Evolve 是一个给本地智能体使用的自动进化记忆系统。它把项目决策、稳定偏好、错误模式和可复用经验整理成可检索、可审核、可迭代的长期记忆。

这个仓库提供两个入口：

| 入口 | 适合谁 | 怎么安装 |
| --- | --- | --- |
| MemPalace 自动进化记忆系统 | 想把记忆能力接到 Claude Code、Cursor 或自制智能体里的用户 | 按下面的 Python / MCP / SDK 方式安装 |
| DreamSeed Code 安装器 | 想直接使用 DreamSeed 终端端和桌面端的 Windows 用户 | 下载 `DreamSeed-Code-0.1.1-Setup.exe` 并安装 |

DreamSeed Code 里已经内置 MemPalace 记忆能力。只使用 DreamSeed Code 的用户不需要再额外安装 MemPalace。

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

如果你的智能体支持 MCP，推荐这样安装：

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
- 项目历史与 `/resume`
- 内置终端、diff viewer、任务线程和审批门禁
- MemPalace 记忆候选池审核系统

安装完成后：

```powershell
dreamseed
```

也可以双击桌面上的 `DreamSeed Desktop`。

桌面端和终端端是一体的：它们使用同一套模型配置、同一份项目历史、同一个 `/resume` 归档和同一个 MemPalace 记忆系统。

## 备用安装方式

如果你下载的是整个仓库，可以运行：

```powershell
DreamSeed-Setup-Windows.cmd
```

它会优先使用 `installers` 文件夹里的完整安装包。只有本地包不完整时，才会尝试从 GitHub 下载。

已经安装过的用户可以直接更新：

```powershell
dreamseed update
```

如果旧版本的 `dreamseed` 命令不可用，就重新运行 `DreamSeed-Code-0.1.1-Setup.exe` 覆盖安装。

## 记忆不会乱写

MemPalace 的长期记忆默认走审核流程：

```text
memory-candidates -> reviewed -> promote-reviewed -> MemPalace
```

稳定偏好、项目决策、错误模式更容易保留；临时调试、空回复、长日志和泛泛 checkpoint 会被降权或拒绝。
