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
# 验证安装
python -m mempalace_evolve.cli doctor

# 一键演示全部功能
python -m mempalace_evolve.cli demo
```

输出效果：

```
  ═══════════════════════════════════════════════════════════
  ║ MemPalace Evolve — Self-Evolving Memory for AI Agents ║
  ═══════════════════════════════════════════════════════════

  [1] 存储记忆 (Store Memories)
      ✓ [decisions] Decided to use FastAPI with PostgreSQL...
      ✓ [errors] CORS blocked requests — fixed by adding middleware...

  [2] 语义搜索 (Semantic Search)
      Q: cross-origin request handling
      → CORS blocked requests from localhost:3000...  [0.519]

  [3] 知识图谱 (Knowledge Graph)
      API ─built_with→ FastAPI
      API ─stores_data_in→ PostgreSQL

  [4] 进化管道 (Evolution Pipeline)
      候选提取: 1 条 → 晋升存储: 1 条

  ✓ Demo 完成！
```

## Python SDK 快速上手

```python
from mempalace_evolve import MemPalace

palace = MemPalace("./my-project-memory")

# 存记忆
palace.remember("数据库用的 PostgreSQL，ORM 用 SQLAlchemy", room="decisions")

# 语义搜索（不需要精确匹配关键词）
results = palace.recall("用了什么数据库")
print(results[0]["content"])
# → "数据库用的 PostgreSQL，ORM 用 SQLAlchemy"

# 知识图谱
palace.add_fact("项目", "使用", "PostgreSQL")
rels = palace.query_entity("项目")

# 从对话中自动提取有价值的记忆
report = palace.evolve(transcript="我们决定用 JWT 做认证，放弃了 session 方案...")
# → {"promoted": 1, "dropped": 0, "candidates": 1}
```

## 核心能力

| 能力 | 说明 |
|------|------|
| **4 层记忆** | L0 身份 → L1 关键知识 → L2 按需检索 → L3 语义搜索 |
| **知识图谱** | 实体关系存储，支持时间线追踪 |
| **自进化管道** | 对话结束后自动提取 → 打分 → 晋升/淘汰 |
| **向量检索** | ChromaDB 语义相似度搜索 |
| **多 Agent 适配** | MCP / REST API / OpenAI / LangChain / 自定义 |

## 接入你的 AI Agent

### Claude Code / Cursor（MCP 协议）

在 `~/.claude/settings.json` 里加：

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

重启后自动获得 6 个工具：`remember` / `recall` / `add_fact` / `query_entity` / `forget` / `evolve`

### OpenAI / GPT

```python
from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter

adapter = OpenAIAdapter(palace)
tools = adapter.get_tools()  # 传给 OpenAI API
result = adapter.handle_tool_call(name, arguments)  # 处理 tool call
```

### LangChain

```python
from mempalace_evolve.adapters.langchain_adapter import LangChainAdapter

adapter = LangChainAdapter(palace)
tools = adapter.get_tools()  # 返回 StructuredTool 列表，直接接入 agent
```

### REST API

```bash
python -m mempalace_evolve.cli serve --port 8765
# POST /remember, /recall, /kg/add, /kg/query
```

### 自制 Agent

```python
from mempalace_evolve import MemPalace

palace = MemPalace("./agent-memory", wing="my_agent")

# 对话开始 → 检索相关记忆
memories = palace.recall(user_query, limit=3)

# 对话中 → 存重要信息
palace.remember("决策内容", room="decisions")

# 对话结束 → 自动进化
palace.evolve(transcript=full_transcript)
```

## 自进化原理

```
对话结束 → CandidateExtractor 扫描 → 关键词匹配 + 内容评分 → 生成候选(0-10分)
  ↓
MemoryReviewer 评审:
  score >= 7 → 晋升为长期记忆
  score <  3 → 丢弃
  中间地带   → 等待，超 7 天未晋升则归档
  ↓
晋升的记忆 → ChromaDB 向量库 → 下次对话自动语义召回
```

## CLI 命令

```bash
python -m mempalace_evolve.cli demo          # 一键演示
python -m mempalace_evolve.cli doctor        # 检查安装
python -m mempalace_evolve.cli playground    # 交互式 REPL
python -m mempalace_evolve.cli remember "内容" --room config
python -m mempalace_evolve.cli recall "搜索词"
python -m mempalace_evolve.cli serve --port 8765
python -m mempalace_evolve.cli evolve
```

## 项目结构

```
src/mempalace_evolve/
├── sdk.py               # 主 SDK 入口
├── cli.py               # 命令行 (demo/doctor/playground/...)
├── demo.py / doctor.py / playground.py / terminal.py
├── core/                # 核心引擎
│   ├── chroma_helper.py    # ChromaDB 向量存储
│   ├── knowledge_graph.py  # SQLite 知识图谱
│   ├── lifecycle.py        # 生命周期管理
│   └── ...
├── evolution/           # 自进化管道
│   ├── candidate.py     # 候选提取
│   └── reviewer.py      # 评审打分
└── adapters/            # Agent 适配器
    ├── mcp_server.py    # Claude Code / Cursor
    ├── openai_adapter.py
    ├── langchain_adapter.py
    └── rest_api.py
```

## License

MIT
