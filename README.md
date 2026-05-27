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

# mempalace-evolve

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://github.com/a2328275243/mempalace-evolve/actions/workflows/tests.yml/badge.svg)](https://github.com/a2328275243/mempalace-evolve/actions/workflows/tests.yml)

**给 AI Agent 用的自进化记忆系统。**

Agent 跑完一轮对话就什么都忘了？这个项目让你的 Agent 拥有持久记忆——不只是存起来，还会自己筛选、打分、淘汰，越用越聪明。

不绑定任何框架。OpenAI、Claude、LangChain、自己写的 Agent，都能接。

---

## 为什么需要这个？

| 问题 | mempalace-evolve 的解决方案 |
|------|---------------------------|
| AI 跨会话失忆 | 持久化记忆 + 语义检索，下次对话自动召回相关上下文 |
| 记忆越存越多越乱 | 自进化：自动去重、合并相似、淘汰过时、晋升高质量 |
| 存了但找不到 | 向量语义搜索 + 知识图谱双通道检索 |
| 接入成本高 | 3 行代码接入，支持 MCP/OpenAI/LangChain/REST |

## 安装

```bash
# 从 GitHub 安装（推荐）
pip install git+https://github.com/a2328275243/mempalace-evolve.git

# 需要 MCP 支持（Claude Code / Cursor）
pip install "mempalace-evolve[mcp] @ git+https://github.com/a2328275243/mempalace-evolve.git"

# 需要 REST API
pip install "mempalace-evolve[api] @ git+https://github.com/a2328275243/mempalace-evolve.git"
```

要求：Python >= 3.10 | 核心依赖仅 `chromadb` 一个包 | 不需要 GPU，全部本地运行

## 30 秒体验

安装后直接运行，不需要写任何代码：

```bash
# 验证安装是否正常
python -m mempalace_evolve.cli doctor

# 一键演示全部功能（存储 → 搜索 → 知识图谱 → 自进化）
python -m mempalace_evolve.cli demo

# 交互式体验（输入文字自动存储，/search 搜索）
python -m mempalace_evolve.cli playground
```

---

## 快速上手：两种使用模式

### 模式 A：MCP 协议（AI 自动存取，零代码）

适用于 Claude Code、Cursor 等支持 MCP 的 AI 工具。配置后 AI 自动获得记忆能力，**不需要写任何代码**。

### 模式 B：Python SDK（手动集成到你的 AI 应用）

适用于自建 Agent、OpenAI API 应用、LangChain 项目等。通过代码调用 SDK 接口。

---

## 模式 A：MCP 配置指南（详细）

MCP（Model Context Protocol）让 AI 自动拥有记忆工具。配置一次，之后 AI 会自己决定什么时候存、什么时候搜。

### 第一步：安装

```bash
pip install "mempalace-evolve[mcp] @ git+https://github.com/a2328275243/mempalace-evolve.git"
```

### 第二步：配置 MCP Server

**Claude Code** — 编辑 `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "mempalace": {
      "command": "mempalace-mcp",
      "env": {
        "MEMPALACE_PATH": "~/.mempalace",
        "MEMPALACE_WING": "my_project"
      }
    }
  }
}
```

**Cursor** — 在 Settings → MCP Servers 中添加：

```json
{
  "mempalace": {
    "command": "mempalace-mcp",
    "env": {
      "MEMPALACE_PATH": "~/.mempalace",
      "MEMPALACE_WING": "my_project"
    }
  }
}
```

### 第三步：重启 AI 工具

重启后，AI 自动获得 6 个记忆工具：

| 工具 | 作用 |
|------|------|
| `remember` | 存储一条记忆到指定 room |
| `recall` | 语义搜索相关记忆 |
| `add_fact` | 添加知识图谱三元组 |
| `query_entity` | 查询实体关系 |
| `forget` | 删除指定记忆 |
| `evolve` | 触发一次自进化（清理 + 晋升 + 合并） |

### 配置参数说明

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `MEMPALACE_PATH` | 记忆存储目录 | `~/.mempalace` |
| `MEMPALACE_WING` | 项目/翼名称（隔离不同项目的记忆） | `global` |

**多项目配置示例：**

```json
{
  "mcpServers": {
    "mempalace-web": {
      "command": "mempalace-mcp",
      "env": { "MEMPALACE_PATH": "~/.mempalace", "MEMPALACE_WING": "web_app" }
    },
    "mempalace-ml": {
      "command": "mempalace-mcp",
      "env": { "MEMPALACE_PATH": "~/.mempalace", "MEMPALACE_WING": "ml_project" }
    }
  }
}
```

每个 wing 的记忆完全隔离，互不干扰。也可以用同一个 wing 实现跨项目共享记忆。

---

## 模式 B：Python SDK 完整指南

适用于自建 AI 应用、没有 MCP 的场景。

### 基础用法

```python
from mempalace_evolve import MemPalace

palace = MemPalace("./my-project-memory", wing="my_project")

# 存记忆（指定 room 分类）
palace.remember("数据库用 PostgreSQL，ORM 用 SQLAlchemy", room="decisions")
palace.remember("CORS 问题通过添加中间件解决", room="errors")

# 语义搜索（不需要精确匹配关键词）
results = palace.recall("用了什么数据库")
print(results[0]["content"])
# → "数据库用 PostgreSQL，ORM 用 SQLAlchemy"

# 知识图谱
palace.add_fact("项目", "使用", "PostgreSQL")
palace.add_fact("API", "框架", "FastAPI")
rels = palace.query_entity("项目")
```

### 对话记忆：digest() + context_for()

这是最核心的 API——让你的 AI 应用拥有跨会话记忆：

```python
from mempalace_evolve import MemPalace

palace = MemPalace("./agent-memory", wing="my_agent")

# ═══ 对话结束时：自动提取知识 ═══
palace.digest([
    {"role": "user", "content": "我们决定用 Redis 做缓存，TTL 设 1 小时"},
    {"role": "assistant", "content": "好的，已配置 Redis，TTL=3600s"},
    {"role": "user", "content": "认证用 JWT，别用 session"},
])
# 自动提取关键信息存入记忆，不需要手动指定存什么

# ═══ 下次对话开始时：注入相关上下文 ═══
context = palace.context_for("缓存怎么配置的？")
# 返回: "- [decisions] 我们决定用 Redis 做缓存，TTL 设 1 小时..."

# 把 context 注入到 system prompt
system_prompt = f"""你是一个编程助手。以下是之前对话中的相关记忆：
{context}

请基于这些上下文回答用户问题。"""
```

### 完整集成示例（OpenAI API）

```python
import openai
from mempalace_evolve import MemPalace

palace = MemPalace("./my-app-memory", wing="chatbot")

def chat(user_message: str, history: list) -> str:
    # 1. 检索相关记忆作为上下文
    context = palace.context_for(user_message)

    # 2. 构建 prompt
    system = "你是一个助手。"
    if context:
        system += f"\n\n已知信息（来自之前的对话）:\n{context}"

    messages = [{"role": "system", "content": system}] + history
    messages.append({"role": "user", "content": user_message})

    # 3. 调用 LLM
    response = openai.chat.completions.create(
        model="gpt-4", messages=messages
    )
    reply = response.choices[0].message.content

    # 4. 对话结束后提取记忆
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    palace.digest(history)

    return reply
```

### 自进化：evolve()

每次调用 `evolve()` 会自动执行完整的记忆维护：

```python
report = palace.evolve(transcript="今天的对话内容...")
# report 包含：
# - candidates: 提取了多少候选记忆
# - promoted: 晋升了多少条
# - merged: 合并了多少重复
# - opportunistic: 4 项被动维护结果
```

---

## 自进化原理（核心特色）

这是 mempalace-evolve 区别于普通向量数据库的核心能力。记忆不是存了就不管，系统会**自动维护记忆质量**：

### 主动进化（evolve 时触发）

```
对话结束 → CandidateExtractor 扫描全文
  ↓
关键词匹配 + 内容评分 → 生成候选 (0-10 分)
  ↓
MemoryReviewer 评审:
  score >= 7 → 晋升为长期记忆
  score <  3 → 丢弃
  中间地带   → 等待观察
  ↓
晋升的记忆 → ChromaDB 向量库 → 下次对话自动语义召回
```

### 被动进化（4 项自动维护机制）

每次 `evolve()` 还会执行 4 项后台维护：

| 机制 | 作用 | 触发条件 |
|------|------|----------|
| **低分清理** | 删除评分低且长期未访问的记忆 | 评分 < 0.3 且 90 天未访问 |
| **候选晋升** | 高质量候选记忆自动晋升为正式记忆 | 候选评分 >= 0.45 |
| **孤立实体清理** | 删除知识图谱中无关系的孤立节点 | 实体无任何出入关系 |
| **过时决策标记** | 标记长期未更新的决策为 stale | 180 天未访问的 decisions |

### 反馈回路

每次 `recall()` 搜索记忆时，被召回的记忆会自动更新 `last_accessed` 时间戳。经常被用到的记忆不会被清理，长期不用的会逐渐淘汰。**越用越精准，不用的自动消失。**

### 合并去重

存入相似内容时自动检测重复，合并为一条更完整的记忆，避免信息冗余。

---

## 哪些是自动的？哪些需要手动？如何全自动？

### 自动 vs 手动一览

| 功能 | 是否自动 | 说明 |
|------|----------|------|
| `recall()` 反馈回路 | ✅ 完全自动 | 每次搜索自动更新记忆活跃度，无需任何配置 |
| 合并去重 | ✅ 自动（evolve 时） | evolve 执行时自动检测并合并相似记忆 |
| 低分清理 | ✅ 自动（evolve 时） | evolve 执行时自动清理低分过期记忆 |
| 候选晋升 | ✅ 自动（evolve 时） | evolve 执行时自动晋升高质量候选 |
| 孤立实体清理 | ✅ 自动（evolve 时） | evolve 执行时自动清理 KG 孤立节点 |
| 过时决策标记 | ✅ 自动（evolve 时） | evolve 执行时自动标记过时决策 |
| **触发 evolve 本身** | ⚠️ 需要触发 | 见下方"如何实现全自动" |
| **存储记忆** | ⚠️ 取决于模式 | MCP 模式下 AI 自动存；SDK 模式需代码调用 |

**关键点：** 所有进化机制都是自动的，但需要有人/有代码**触发 `evolve()`**。就像洗衣机会自动洗衣服，但你得按下启动按钮。

### 如何实现全自动（不同模式）

#### MCP 模式（Claude Code / Cursor）

**方法 1：在 CLAUDE.md 或 system prompt 中加一句话（推荐）**

在项目的 `CLAUDE.md` 或 AI 的 system prompt 中添加：

```
每次对话结束前，请调用 evolve 工具执行记忆维护。
```

这样 AI 每次对话结束时会自动调用 evolve，触发全部进化机制。

**方法 2：配置 session hook（完全无感）**

如果你的 AI 工具支持 hook（如 Claude Code），可以配置对话结束时自动触发：

```json
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "stop",
      "command": "python -c \"from mempalace_evolve import MemPalace; MemPalace('~/.mempalace').evolve()\""
    }]
  }
}
```

这样完全不需要 AI 主动调用，session 结束自动进化。

#### SDK 模式（自建 AI 应用）

在你的对话循环结束时加一行代码：

```python
# 对话结束时自动进化
def on_session_end(conversation_history):
    palace.digest(conversation_history)  # 提取知识
    palace.evolve()                      # 触发进化（清理+晋升+合并）
```

或者用定时任务：

```python
import schedule

# 每小时自动进化一次
schedule.every(1).hours.do(lambda: palace.evolve())
```

#### REST API 模式

用 cron 定时调用：

```bash
# 每天凌晨 2 点自动进化
0 2 * * * curl -X POST http://localhost:8765/evolve
```

### 总结

| 模式 | 存储记忆 | 触发进化 | 进化过程 |
|------|----------|----------|----------|
| MCP | AI 自动存 | AI 调用 evolve 工具 / hook 自动触发 | 全自动 |
| SDK | 代码调 `remember()` 或 `digest()` | 代码调 `evolve()` | 全自动 |
| REST | POST /remember | POST /evolve 或 cron | 全自动 |

**一句话：你只需要负责"什么时候触发 evolve"，剩下的全部自动完成。**

---

## 其他适配器

### OpenAI Function Calling

```python
from mempalace_evolve import MemPalace
from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter

palace = MemPalace("./memory")
adapter = OpenAIAdapter(palace)

# 获取 tools 定义，传给 OpenAI API
tools = adapter.get_tools()

# 处理 LLM 返回的 tool call
result = adapter.handle_tool_call(tool_name, arguments)
```

### LangChain

```python
from mempalace_evolve import MemPalace
from mempalace_evolve.adapters.langchain_adapter import LangChainAdapter

palace = MemPalace("./memory")
adapter = LangChainAdapter(palace)
tools = adapter.get_tools()  # 返回 StructuredTool 列表，直接接入 agent
```

### REST API

```bash
# 启动 HTTP 服务
python -m mempalace_evolve.cli serve --port 8765

# 接口：POST /remember, /recall, /kg/add, /kg/query, /evolve
```

---

## 完整 API 参考

| 方法 | 说明 |
|------|------|
| `palace.remember(content, room)` | 存储一条记忆 |
| `palace.recall(query, limit, room)` | 语义搜索记忆 |
| `palace.forget(drawer_id)` | 删除指定记忆 |
| `palace.digest(conversation)` | 从对话自动提取知识 |
| `palace.context_for(query)` | 获取相关上下文（用于 prompt 注入） |
| `palace.add_fact(s, p, o)` | 添加知识图谱三元组 |
| `palace.query_entity(entity)` | 查询实体关系 |
| `palace.evolve(transcript)` | 执行一次完整进化周期 |

---

## CLI 命令

```bash
python -m mempalace_evolve.cli demo          # 一键演示全部功能
python -m mempalace_evolve.cli doctor        # 检查安装环境
python -m mempalace_evolve.cli playground    # 交互式 REPL
python -m mempalace_evolve.cli remember "内容" --room decisions
python -m mempalace_evolve.cli recall "搜索词"
python -m mempalace_evolve.cli serve --port 8765
python -m mempalace_evolve.cli evolve
```

---

## 项目结构

```
src/mempalace_evolve/
├── sdk.py               # 主 SDK（MemPalace 类）
├── cli.py               # 命令行工具
├── demo.py              # 一键演示
├── doctor.py            # 环境检查
├── playground.py        # 交互式 REPL
├── terminal.py          # 终端彩色输出
├── core/                # 核心引擎
│   ├── chroma_helper.py    # ChromaDB 向量存储
│   ├── knowledge_graph.py  # SQLite 知识图谱
│   ├── lifecycle.py        # 生命周期（TTL/遗忘曲线/清理）
│   ├── consolidation.py    # 记忆合并去重
│   ├── adaptive_scorer.py  # 自适应评分
│   ├── layers.py           # 4 层记忆架构
│   └── config.py           # 配置管理
├── evolution/           # 自进化管道
│   ├── pipeline.py      # 进化主流程
│   ├── candidate.py     # 候选提取器
│   ├── reviewer.py      # 评审打分
│   └── opportunistic.py # 4 项被动维护
└── adapters/            # Agent 适配器
    ├── mcp_server.py       # MCP 协议（Claude/Cursor）
    ├── openai_adapter.py   # OpenAI Function Calling
    ├── langchain_adapter.py # LangChain Tools
    └── rest_api.py         # HTTP REST API
```

## License

MIT