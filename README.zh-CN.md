简体中文 | [English](README.md)

---

# MemPalace Evolve（记忆宫殿进化版）

> 面向 AI 工具的自我进化长期记忆系统

MemPalace Evolve 为 AI 助手提供了一个可以**存储事实、回忆上下文、促进有用记忆、衰减噪声记忆、解决冲突**的记忆层，并通过 Python SDK、REST API、LangChain 工具或 MCP 协议进行访问。

**核心理念：让 AI 助手跨会话记住项目，无需用户每次重复同样的背景信息。**

---

## 🎯 为什么需要 MemPalace？

大多数 AI 工具的记忆很弱。一次对话结束后，上下文消失，下一次会话从零开始。

MemPalace 专为长期工作场景设计：

- 📚 研究项目
- 💻 编码项目  
- ✍️ 写作项目
- 🧠 个人知识库
- 🤖 需要持久上下文的 AI Agent

它不是代码生成工具，而是**你可以接入现有 AI 客户端的记忆层**。

---

## ✨ 核心特性

- **🧠 持久记忆**：存储事实、决策、关系和项目上下文
- **🔍 语义检索**：检索与当前任务相关的记忆
- **🕸️ 知识图谱**：连接实体和关系，而非仅保存平面笔记
- **📈 记忆进化**：促进有用记忆，衰减弱记忆，减少重复
- **🔌 多适配器**：Python SDK、REST API、MCP 服务器、OpenAI 格式、LangChain 工具
- **🏗️ 项目隔离**：使用 `wing` 名称按项目、工具或用户隔离记忆

---

## 🚀 快速开始

需要 Python 3.10+：

```bash
git clone https://github.com/a2328275243/mempalace-evolve.git
cd mempalace-evolve
pip install -e ".[mcp]"
```

运行健康检查：

```bash
mempalace doctor
```

使用 Python SDK：

```python
from mempalace_evolve import MemPalace

memory = MemPalace("./.mempalace", wing="demo")

memory.store_memory(
    content="该项目使用两阶段检索流水线。",
    category="architecture",
    importance=0.8,
)

results = memory.recall("检索是如何工作的？")
for item in results:
    print(item.content)
```

---

## 🔌 与 MCP 客户端集成

安装 MCP 支持：

```bash
pip install -e ".[mcp]"
```

在任何支持 MCP 的客户端中添加 MemPalace 作为 MCP 服务器：

```json
{
  "mcpServers": {
    "mempalace": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mempalace_evolve.adapters.mcp_server"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "MEMPALACE_PATH": ".mempalace",
        "MEMPALACE_WING": "default"
      }
    }
  }
}
```

重启客户端后即可使用记忆存储、检索、进化、审计和查询工具。

- `MEMPALACE_PATH`：控制记忆数据库的存储位置
- `MEMPALACE_WING`：隔离记忆空间，例如每个项目一个 wing

---

## 🔧 其他集成方式

**REST API：**
```bash
pip install -e ".[api]"
mempalace-server
```

**LangChain 工具：**
```bash
pip install -e ".[langchain]"
python examples/langchain_agent.py
```

**Cursor MCP 示例：**
```bash
python examples/cursor_mcp/verify_setup.py
```

**Claude Code Hook 示例：**
```bash
python examples/claude_code_hook/stop_hook.py
```

---

## 📁 项目结构

```
src/mempalace_evolve/    核心记忆系统、进化流水线、适配器、CLI 和 SDK
tests/                   回归测试
examples/                小型集成示例
docs/                    文档
pyproject.toml           包元数据和可选依赖
```

---

## 🛠️ 开发

```bash
pip install -e ".[dev,mcp]"
python -m pytest tests/ -v
python -m mempalace_evolve.cli doctor
```

---

## 🧭 当前方向

- 更好的自动摘要
- 更强的冲突检测
- 更完善的知识图谱提取
- 更清晰的记忆促进和衰减
- 能展示跨会话记忆改进的示例

---

## 📊 与同类方案对比

| 特性 | MemPalace | 传统 RAG | 向量数据库 | 云端知识图谱 |
|-----|-----------|----------|-----------|------------|
| 自我进化 | ✅ | ❌ | ❌ | ❌ |
| 本地优先 | ✅ | ✅ | ✅ | ❌ |
| 知识图谱 | ✅ | ❌ | ❌ | ✅ |
| 记忆促进 | ✅ | ❌ | ❌ | ❌ |
| 冲突检测 | ✅ | ❌ | ❌ | ❌ |
| 免费开源 | ✅ | 视情况 | 视情况 | ❌ |
| MCP 就绪 | ✅ | ❌ | ❌ | ❌ |

---

## 📄 许可

MIT。详见 `LICENSE`。
