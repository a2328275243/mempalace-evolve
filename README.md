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

## 目录

- [安装](#安装)
- [30 秒体验](#30-秒体验)
- [模式 A：MCP 配置（零代码）](#模式-amcp-配置指南详细)
- [模式 B：Python SDK](#模式-bpython-sdk-完整指南)
- [自进化原理](#自进化原理核心特色)
- [自动 / 手动 / 可配置自动](#自动--手动--可配置自动)
- [记忆类型系统](#记忆类型系统认知科学三分法)
- [高级功能](#高级功能)
  - [可配置评分规则](#可配置评分规则)
  - [混合检索（向量 + 知识图谱）](#混合检索向量--知识图谱扩展)
  - [增量进化](#增量进化)
  - [跨项目经验自动共享](#跨项目经验自动共享)
  - [Working Memory 缓存](#working-memory-缓存)
  - [智能晋升机制](#智能晋升机制)
- [完整 API 参考](#完整-api-参考)
- [CLI 命令](#cli-命令)

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

### 第二步：一键配置（推荐）

安装后运行交互式向导，自动检测环境、写入配置：

```bash
mempalace setup
```

向导会自动完成：
1. 检测 Python / chromadb / fastmcp 是否安装
2. 检测 Claude Code / Cursor 配置目录
3. 收集 wing 名称和存储路径
4. 写入 MCP 配置（自动备份旧配置）
5. 验证 MCP Server 能正常启动

也可以跳过交互，直接指定参数：

```bash
mempalace setup --wing my_project --palace ~/.mempalace
```

### 手动配置（备选）

如果向导不适合你的环境，可以手动编辑配置文件：

**Claude Code** — 编辑 `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "mempalace": {
      "command": "mempalace-mcp",
      "env": {
        "MEMPALACE_PATH": "绝对路径/.mempalace",
        "MEMPALACE_WING": "my_project"
      }
    }
  }
}
```

> ⚠️ 注意：`MEMPALACE_PATH` 必须用绝对路径，`~` 在 JSON 配置中不会被展开。

**Cursor** — 在 Settings → MCP Servers 中添加（同样用绝对路径）：

```json
{
  "mempalace": {
    "command": "mempalace-mcp",
    "env": {
      "MEMPALACE_PATH": "绝对路径/.mempalace",
      "MEMPALACE_WING": "my_project"
    }
  }
}
```

> 如果 `mempalace-mcp` 命令找不到，改用：`"command": "python", "args": ["-m", "mempalace_evolve.adapters.mcp_server"]`

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
      "env": { "MEMPALACE_PATH": "C:/Users/你的用户名/.mempalace", "MEMPALACE_WING": "web_app" }
    },
    "mempalace-ml": {
      "command": "mempalace-mcp",
      "env": { "MEMPALACE_PATH": "C:/Users/你的用户名/.mempalace", "MEMPALACE_WING": "ml_project" }
    }
  }
}
```

每个 wing 的 semantic/episodic 记忆相互隔离。procedural 记忆（错误模式、经验教训）自动在所有 wing 间共享。

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

## 自动 / 手动 / 可配置自动

### 完全自动（不需要你做任何事）

- **反馈回路**：每次 `recall()` 搜索时，被命中的记忆自动刷新活跃度。常用的不会被清理，不用的逐渐淘汰。
- **合并去重**：evolve 执行时自动检测相似记忆并合并。
- **低分清理**：评分 < 0.3 且 90 天没被访问的记忆自动删除。
- **候选晋升**：候选区中评分 >= 0.45 的记忆自动晋升为正式记忆。
- **孤立实体清理**：知识图谱中没有任何关系的孤立节点自动删除。
- **过时决策标记**：decisions room 中 180 天没更新的自动标记为 stale。

以上全部在 `evolve()` 被调用时自动执行，不需要额外配置。

### 需要触发的（一次调用，全部执行）

`evolve()` 本身需要被触发。触发一次 = 上面 6 项全部执行。

### 存储记忆

| 模式 | 谁来存 |
|------|--------|
| MCP（Claude Code / Cursor） | AI 自己判断什么值得存，自动调用 remember 工具 |
| SDK（自建应用） | 你的代码调 `palace.remember()` 或 `palace.digest()` |
| REST | 你的代码 POST /remember |

### 如何让 evolve 也变成自动的

**MCP 模式 — 方法 1：告诉 AI 去做**

在项目 `CLAUDE.md` 或 system prompt 里加：

```
对话结束前调用 evolve 工具。
```

AI 看到这句话就会在每次对话结束时自动触发进化。

**MCP 模式 — 方法 2：配 hook（完全无感）**

Claude Code 支持 hook，对话结束时自动执行命令：

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "stop",
      "command": "python -c \"from mempalace_evolve import MemPalace; MemPalace('~/.mempalace').evolve()\""
    }]
  }
}
```

放在 `.claude/settings.json` 里，之后每次对话结束自动进化，AI 和用户都不需要操心。

**SDK 模式 — 对话结束时调一行**

```python
def on_session_end(messages):
    palace.digest(messages)  # 提取知识
    palace.evolve()          # 进化
```

**SDK 模式 — 内置自动进化（最简单）**

```python
# auto_evolve=True 自动启动后台线程，每小时 evolve 一次
palace = MemPalace("./memory", auto_evolve=True, evolve_interval=3600)
# 之后正常使用即可，不需要手动调 evolve()
```

**SDK 模式 — 定时任务**

```python
import schedule
schedule.every(1).hours.do(lambda: palace.evolve())
```

**REST 模式 — cron**

```bash
0 2 * * * curl -X POST http://localhost:8765/evolve
```

### 各模式总览

| 模式 | 存记忆 | 搜记忆 | 进化 | 全自动方案 |
|------|--------|--------|------|-----------|
| MCP | AI 自动 | AI 自动 | AI 调工具 | 加一句 prompt 或配 hook |
| SDK | `remember()` / `digest()` | `recall()` / `context_for()` | `evolve()` | 放在 session end 回调里 |
| REST | POST /remember | POST /recall | POST /evolve | cron 定时 |

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

# 带 API key 认证
python -m mempalace_evolve.cli serve --port 8765 --api-key your-secret-key
# 请求时需带 header: X-API-Key: your-secret-key

# 接口：POST /remember, /recall, /digest, /evolve, /kg/add, /kg/query
# GET /export, /health
```

---

## 记忆类型系统（认知科学三分法）

借鉴认知科学的记忆分类，系统将记忆分为三种类型，各有不同的存储和检索策略：

| 类型 | 含义 | 作用域 | 自动分类规则 |
|------|------|--------|-------------|
| **semantic**（语义记忆） | 事实、配置、决策 | 项目内 | decisions / config / architecture / preferences room |
| **episodic**（情景记忆） | 具体事件、对话记录 | 项目内 | progress / general / daily_summaries room |
| **procedural**（程序记忆） | 经验、模式、教训 | **全局共享** | errors / error_patterns room |

**核心设计：procedural 记忆全局可见。**

项目 A 踩过的坑（OOM、连接池泄漏、部署失败），项目 B 搜索时自动能找到。不需要手动配置跨项目关联。

```python
# 存储时自动分类
palace.remember("数据库用 PostgreSQL", room="decisions")  # → semantic
palace.remember("今天修了登录 bug", room="progress")       # → episodic
palace.remember("OOM 时先查连接池 max 设置", room="errors") # → procedural（全局共享）

# 也可以手动指定类型
palace.remember("通用部署流程", room="general", memory_type="procedural")
```

### 检索策略

每次 `recall()` 自动执行两路并行搜索：

```
查询 "内存溢出怎么办"
  ↓
┌─────────────────────────────────────────────┐
│ 搜索 1: 当前 wing（所有类型）               │
│ 搜索 2: 全局 procedural（所有 wing 的经验） │
└─────────────────────────────────────────────┘
  ↓
合并 + 去重 + KG 扩展
  ↓
返回结果（标记来源：direct / procedural_global / kg_expansion）
```

不需要任何参数控制，经验类记忆天然跨项目流动。

---

## 高级功能

### 可配置评分规则

不同类型的记忆重要性不同。默认情况下所有 room 使用相同的清理阈值，你可以通过 `scoring_config` 自定义：

```python
palace = MemPalace("./memory", scoring_config={
    "rooms": {
        "decisions": {"weight": 2.0, "never_delete": True},  # 决策永不自动删除
        "errors": {"weight": 1.5, "min_score": 0.4},         # 错误模式提高保留阈值
        "config": {"weight": 1.0, "never_delete": True},     # 配置永不删除
    },
    "thresholds": {
        "discard": 0.3,      # 低于此分数 + 过期 → 清理（默认 0.3）
        "promote": 0.7,      # 候选区高于此分数 → 晋升（默认 0.45）
        "stale_days": 180,   # 决策超过此天数未访问 → 标记过时（默认 180）
    }
})
```

**规则说明：**
- `never_delete: True`：该 room 的记忆在低分清理时被跳过，永远不会被自动删除
- `weight`：影响评分计算权重（预留字段，当前版本用于优先级排序）
- `thresholds` 全局生效，覆盖默认值

### 混合检索（向量 + 知识图谱扩展）

`recall()` 默认启用混合检索：先做向量语义搜索，再从结果中提取实体通过知识图谱扩展关联记忆。

```python
# 默认开启混合检索
results = palace.recall("Redis 缓存配置")
# 返回：
# 1. 向量搜索直接命中的记忆
# 2. 通过 KG 关联发现的相关记忆（标记 source: "kg_expansion"）

# 关闭混合检索（纯向量搜索）
results = palace.recall("Redis 缓存配置", hybrid=False)
```

**工作原理：**
```
查询 "Redis 缓存配置"
  ↓
向量搜索 → 找到 3 条直接相关记忆
  ↓
从结果中提取实体 → ["Redis", "caching"]
  ↓
查询知识图谱 → Redis --uses--> RedisCluster, Redis --stores_in--> AWS
  ↓
获取关联实体的记忆 → 补充到结果中
  ↓
返回：直接命中 + KG 扩展，去重后返回
```

### 增量进化

`evolve()` 采用增量策略，不会每次全量扫描所有记忆：

- **合并去重**：只扫描当天新增的记忆（不是全库对比）
- **被动维护**：使用时间戳过滤，只处理上次进化后的变化
- **记录进度**：每次进化完成后记录时间戳，下次从上次位置继续

```python
# 首次：处理所有记忆
palace.evolve()

# 后续：只处理新增的（快很多）
palace.evolve()
```

对于大型记忆库（1000+ 条），增量模式将进化耗时从秒级降低到毫秒级。

### 跨项目经验自动共享

不需要手动配置。procedural 类型的记忆（错误模式、经验教训）自动在所有项目间共享：

```python
# 项目 A 存了一条错误经验
palace_a = MemPalace("./memory", wing="project_a")
palace_a.remember("OOM 时先查连接池 max 设置", room="errors")
# → 自动分类为 procedural，全局可见

# 项目 B 搜索时自动找到
palace_b = MemPalace("./memory", wing="project_b")
results = palace_b.recall("内存溢出")
# → 返回 project_a 的经验，标记 source: "procedural_global"
```

**原理：**
- `errors` / `error_patterns` room 的记忆自动归类为 procedural
- `recall()` 每次都会搜索全局 procedural 记忆（不只搜当前 wing）
- 跨 wing 命中时自动记录 `cross_wing_hits`，用于智能晋升

### Working Memory 缓存

同一个话题连续提问时，不会重复搜索 ChromaDB：

```python
# 第一次搜索：走 ChromaDB
results = palace.recall("Redis 缓存配置")

# 紧接着问相似问题：直接返回缓存（不走数据库）
results = palace.recall("Redis 缓存怎么配的")
# → 话题相似度 > 0.8，命中 working memory，毫秒级返回
```

缓存在话题切换时自动失效，不需要手动管理。

### 智能晋升机制

当一条记忆被 3 个以上不同项目召回时，系统自动将其升级为 procedural 类型（全局共享）：

```
记忆 "连接池 max 不要超过 CPU 核数 * 2"
  ↓
project_a 召回 → cross_wing_hits = 1
project_b 召回 → cross_wing_hits = 2
project_c 召回 → cross_wing_hits = 3 ← 触发晋升
  ↓
自动升级为 procedural → 之后所有项目都能搜到
```

不需要人工干预，系统根据实际使用模式自动识别"通用经验"。

### 间隔复习 (Spaced Repetition)

让重要记忆按照艾宾浩斯遗忘曲线复习：

```python
# 查看有哪些记忆需要复习
due = palace.get_due_for_review()
print(f"待复习记忆: {len(due)} 条")

# 标记某条记忆已复习，系统会自动安排下次复习时间
palace.mark_reviewed("drawer_xxx")

# 或者 snooze 推迟复习
palace.snooze_memory("drawer_xxx", days=3)
```

复习间隔：`1天 → 3天 → 7天 → 14天 → 30天 → 60天 → 90天`

CLI 用法：
```bash
mempalace review                    # 显示待复习记忆
mempalace review --mark drawer_xxx # 标记为已复习
```

**触发条件：** 记忆被召回 2 次以上才进入间隔复习池。

### 重要性自动评分

系统根据多个维度自动计算每条记忆的重要性分数 (0.0 - 1.0)：

| 维度 | 权重 | 说明 |
|------|------|------|
| recall_frequency | 30% | 被召回次数 |
| kg_centrality | 25% | 知识图谱关联数量 |
| recency | 20% | 最近访问时间（30天半衰期） |
| cross_wing_hits | 15% | 跨项目使用次数 |
| content_quality | 10% | 内容长度 + 关键词信号 |

```python
# 获取重要性 Top 10
top = palace.top_memories(10)
for mem in top:
    print(f"[{mem['score']:.2f}] {mem['content'][:50]}...")

# 全量评分
result = palace.score_memories()
print(f"已评分: {result['scored']} 条")
```

CLI 用法：
```bash
mempalace top 20     # 显示 Top 20 最重要记忆
```

### 相似度去重

存入新记忆前自动检查相似内容，避免重复存储：

```python
palace = MemPalace("./memory", scoring_config={
    "dedup_threshold": 0.85,    # 相似度 ≥ 85% 视为重复
    "dedup_action": "skip",     # skip / merge / allow
})
```

- **skip**: 跳过存储，返回已有记忆的 ID
- **merge**: 合并到已有记忆（保留更长的，追加不同的部分）
- **allow**: 忽略阈值，仍存储

```python
# 查找相似记忆
similar = palace.find_similar("Python 3.12 新特性", room="decisions")
for mem in similar:
    print(f"[相似度 {mem['similarity']:.2f}] {mem['content'][:50]}...")
```

CLI 用法：
```bash
mempalace similar "Python 3.12 新特性" --threshold 0.8
```

### 上下文长度控制

防止注入过多记忆撑爆 LLM 上下文窗口：

```python
# 最多注入 2000 字符（约 500 token）
context = palace.context_for("项目架构", max_tokens=2000)

# 小上下文模型（如 GPT-3.5）用更小的限制
context = palace.context_for("项目架构", max_tokens=800)
```

### 记忆导入

从 JSON 文件或其他系统批量导入记忆：

```python
# 从 JSON 文件导入
result = palace.import_memories("exported_memories.json")
# {"imported": 42, "skipped": 3, "errors": []}

# 从列表导入
palace.import_memories([
    {"content": "API 用 FastAPI 框架", "room": "decisions"},
    {"content": "数据库连接池 max=20", "room": "config"},
])
```

JSON 文件格式：每条记忆需要 `content` 字段，可选 `room` 和 `metadata`。

### 记忆库统计

```python
stats = palace.stats()
# {
#     "wing": "my_project",
#     "total": 156,
#     "rooms": {"decisions": 23, "errors": 45, "config": 12, ...},
#     "kg_entities": 34
# }
```

---

| 方法 | 说明 |
|------|------|
| `palace.remember(content, room, memory_type=)` | 存储记忆，自动分类类型（semantic/episodic/procedural） |
| `palace.recall(query, limit=, hybrid=)` | 语义搜索：当前 wing + 全局 procedural 并行检索 |
| `palace.forget(drawer_id)` | 删除指定记忆 |
| `palace.digest(conversation)` | 从对话自动提取知识 + KG 三元组 |
| `palace.context_for(query, max_tokens=)` | 获取上下文，自动控制长度 |
| `palace.import_memories(source)` | 从 JSON 文件或列表批量导入 |
| `palace.export(format, output)` | 导出记忆为 JSON 或 Markdown |
| `palace.stats()` | 查看记忆库统计（数量、分布、KG 实体数） |
| `palace.add_fact(s, p, o)` | 添加知识图谱三元组 |
| `palace.query_entity(entity)` | 查询实体关系 |
| `palace.evolve(transcript)` | 执行一次增量进化周期 |

---

## CLI 命令

```bash
python -m mempalace_evolve.cli setup --wing my_project   # 一键配置 MCP
python -m mempalace_evolve.cli demo          # 一键演示全部功能
python -m mempalace_evolve.cli doctor        # 检查安装环境
python -m mempalace_evolve.cli playground    # 交互式 REPL
python -m mempalace_evolve.cli remember "内容" --room decisions
python -m mempalace_evolve.cli recall "搜索词"
python -m mempalace_evolve.cli evolve
python -m mempalace_evolve.cli export --format json -o memories.json
python -m mempalace_evolve.cli export --format markdown
python -m mempalace_evolve.cli serve --port 8765
python -m mempalace_evolve.cli serve --port 8765 --api-key mysecret
```

---

## 项目结构

```
src/mempalace_evolve/
├── sdk.py               # 主 SDK（MemPalace 类）
├── exceptions.py        # 自定义异常（StorageError/ValidationError 等）
├── export.py            # 记忆导出（JSON/Markdown）
├── cli.py               # 命令行工具
├── setup_wizard.py      # 一键安装向导（mempalace setup）
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
    └── rest_api.py         # HTTP REST API（支持 API key 认证）
```

## License

MIT