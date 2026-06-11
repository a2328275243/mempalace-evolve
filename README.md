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

MemPalace Evolve 是一个给本地智能体使用的自动进化记忆系统。它把项目决策、稳定偏好、错误模式和可复用经验整理成可以检索、可以审核、可以进化的长期记忆。

这个仓库保持两个公开入口：

| 入口 | 适合谁 | 怎么用 |
| --- | --- | --- |
| MemPalace 自动进化记忆系统 | 想把记忆能力接到 Claude Code、Cursor 或自制智能体里的用户 | 按下面的 Python / MCP / SDK 方式安装 |
| DreamSeed Code 安装器 | 想直接使用我的自制智能体的 Windows 用户 | 下载 `DreamSeed-Setup-Windows.cmd`，选择安装路径后自动安装 |

DreamSeed Code 的记忆部分本来就是 MemPalace。DreamSeed 用户不需要再额外手动安装 MemPalace，只运行安装器即可；安装器会把终端端、桌面端和内置记忆能力一起装好。

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

如果你的智能体支持 MCP，推荐这样接：

```powershell
python -m pip install -e ".[mcp]"
mempalace setup
```

`mempalace setup` 会尝试检测 Claude Code / Cursor，并帮你写入 MCP 配置。完成后重启对应客户端，就可以通过 MCP 调用 MemPalace。

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

普通用户不需要下载 DreamSeed 源码目录。直接下载并运行安装器：

```powershell
DreamSeed-Setup-Windows.cmd
```

安装器会做这些事：

1. 让用户选择安装路径。
2. 解压 DreamSeed Code 一体化 Windows 包。
3. 安装同一套桌面端和终端端运行时。
4. 创建 `dreamseed` 终端命令。
5. 在桌面创建 `DreamSeed Desktop` 快捷方式。
6. 保留本地模型配置、历史、记忆、日志和密钥在用户自己的 `%LOCALAPPDATA%\DreamSeed` 下。

DreamSeed Code 的桌面端和终端端是一体的。桌面快捷方式和 `dreamseed` 命令使用同一个本地运行时、同一套模型配置、同一份历史记录和同一个 MemPalace 记忆系统。

安装完成后：

```powershell
dreamseed
```

或者直接双击桌面上的 `DreamSeed Desktop`。

以后更新 DreamSeed Code：

```powershell
dreamseed update
```

更新会下载新的公开安装包并覆盖程序文件，但不会覆盖用户自己的模型 key、provider 配置、历史记录、MemPalace 记忆、候选记忆、日志和缓存。

## DreamSeed Code 包含什么

DreamSeed Code 是我的自制智能体。用户通过安装器使用它，不需要下载公开源码目录。

它包含：

- 终端入口
- 桌面端
- 模型管理
- 项目历史和 `/resume`
- 多任务队列
- diff viewer
- 内嵌 terminal
- artifacts 时间线
- 高风险操作审批
- MemPalace 记忆候选池审核

## 记忆不会乱写

长期记忆不直接从会话里硬塞进去。默认流程是：

```text
memory-candidates -> reviewed -> promote-reviewed -> MemPalace
```

稳定偏好、项目决策、错误模式更容易留下；临时调试、空回答、长日志和泛泛 checkpoint 会被降权或拒绝。

## 本地隐私

这些内容默认不会上传到仓库：

- 模型密钥和私有 provider 配置
- legacy history
- memory candidates
- self-evolve candidates
- logs
- cache
- 本地数据库文件

## License

MIT. See [LICENSE](LICENSE).
