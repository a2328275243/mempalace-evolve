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

给 AI Agent 用的自进化记忆系统。

Agent 跑完一轮对话就什么都忘了？这个项目解决的就是这个问题。它给你的 Agent 加上持久记忆——不只是存起来，还会自己筛选、打分、淘汰，越用越聪明。

不绑定任何特定框架。OpenAI、Claude、LangChain、自己写的 Agent，都能接。

## 核心能力

- **4 层记忆架构**：L0 身份/核心事实 → L1 关键知识 → L2 按需检索 → L3 语义搜索，从快到慢逐层查找
- **知识图谱**：实体关系存储，支持时间线追踪，自动过期
- **自进化管道**：对话结束后自动提取候选记忆 → 打分评审 → 达标的晋升为长期记忆，不达标的淘汰
- **向量检索**：基于 ChromaDB，语义相似度搜索，不是关键词匹配
- **每日整合**：自动去重、冲突检测、相似记忆合并
- **自适应评分**：重要性随时间衰减，访问频率影响权重
- **多 Agent 适配**：REST API / OpenAI function calling / Python SDK，随便你怎么接

## 安装

```bash
pip install mempalace-evolve

# 如果要用 REST API 服务
pip install mempalace-evolve[api]
```

要求：Python >= 3.10

## 30 秒上手

```python
from mempalace_evolve import MemPalace

palace = MemPalace("./my-project-memory")

# 存一条记忆
palace.remember("数据库用的 PostgreSQL，ORM 用 SQLAlchemy", room="decisions")

# 语义搜索（不需要精确匹配关键词）
results = palace.recall("用了什么数据库")
print(results[0]["content"])
# → "数据库用的 PostgreSQL，ORM 用 SQLAlchemy"

# 知识图谱
palace.add_fact("项目", "使用", "PostgreSQL")
palace.add_fact("项目", "使用", "FastAPI")
rels = palace.query_entity("项目")
# → [{"predicate": "使用", "object": "PostgreSQL"}, ...]

# 跑一轮进化（从对话中自动提取有价值的记忆）
report = palace.evolve(transcript="我们决定用 JWT 做认证，放弃了 session 方案...")
print(report)  # {"promoted": 1, "dropped": 0, ...}
```

## 接入你的 Agent

### 方式一：REST API（通用，任何语言都能调）

```bash
mempalace-server --port 8765
```

```python
import requests

# 存
requests.post("http://localhost:8765/remember", json={
    "content": "用户喜欢暗色主题",
    "room": "preferences"
})

# 取
resp = requests.post("http://localhost:8765/recall", json={
    "query": "用户的 UI 偏好"
})
print(resp.json()["results"])
```

### 方式二：OpenAI function calling

```python
from openai import OpenAI
from mempalace_evolve import MemPalace
from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter

palace = MemPalace("./memory")
adapter = OpenAIAdapter(palace)

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "记住：部署环境是 AWS ECS"}],
    tools=adapter.get_tools(),  # 自动生成 tool 定义
)

# 处理 tool call
for call in response.choices[0].message.tool_calls:
    result = adapter.handle_tool_call(call.function.name, call.function.arguments)
```

### 方式三：自定义 Agent（继承适配器）

```python
from mempalace_evolve import MemPalace
from mempalace_evolve.adapters.base import AgentAdapter

class MyAgentAdapter(AgentAdapter):
    def on_session_start(self, context):
        # 对话开始时，检索相关记忆注入 prompt
        return self.on_user_input(context.get("first_message", ""), context)

    def on_session_end(self, transcript, context):
        # 对话结束时，跑一轮进化
        self.palace.evolve(transcript=transcript)

# 用法
palace = MemPalace("./memory")
adapter = MyAgentAdapter(palace)
memory_context = adapter.on_session_start({"first_message": "部署出错了"})
# memory_context 包含相关的历史记忆，塞进 system prompt
```

## 自进化是怎么工作的

传统的 Agent 记忆就是个 key-value 存储，存什么全靠手动。这个项目不一样——它有一套自动筛选机制：

```
对话结束
  ↓
CandidateExtractor 扫描对话内容
  ↓ 关键词匹配 + 内容评分
生成候选记忆（score 0-10）
  ↓
MemoryReviewer 评审
  ├── score >= 7 → 晋升为长期记忆
  ├── score < 3  → 直接丢弃
  └── 中间地带   → 等待，超过 7 天未晋升则归档
  ↓
晋升的记忆进入 ChromaDB 向量库
  ↓
下次对话时，语义搜索自动召回相关记忆
```

评分依据：
- 是否包含决策、错误修复、架构设计等关键信息（+2~6 分）
- 内容长度是否足够（太短的没价值）
- 是否包含代码片段（+1）
- 是否是模板/废话（-2）

## 记忆分层

不是所有记忆都一样重要。系统分 4 层，查询时从快到慢：

| 层级 | 内容 | 大小 | 查询方式 |
|------|------|------|----------|
| L0 | 身份/核心事实 | ~100 tokens | 直接加载 |
| L1 | 高重要性知识 | ~500 tokens | 按重要性排序取 top-N |
| L2 | 按需检索 | 不限 | wing/room 过滤 |
| L3 | 深度搜索 | 不限 | 向量语义搜索 |

## 项目结构

```
src/mempalace_evolve/
├── __init__.py          # from mempalace_evolve import MemPalace
├── sdk.py               # 主 SDK，所有操作的入口
├── cli.py               # 命令行工具
├── core/                # 核心引擎（不依赖任何 Agent 框架）
│   ├── config.py        # 配置管理、路径解析
│   ├── knowledge_graph.py  # SQLite 知识图谱
│   ├── chroma_helper.py    # ChromaDB 向量存储
│   ├── layers.py           # 4 层记忆架构
│   ├── adaptive_scorer.py  # 自适应重要性评分
│   ├── consolidation.py    # 每日整合（去重/冲突/合并）
│   └── lifecycle.py        # 生命周期（衰减/压缩/淘汰）
├── evolution/           # 自进化管道
│   ├── pipeline.py      # 管道调度器
│   ├── candidate.py     # 候选提取（从对话中识别有价值内容）
│   └── reviewer.py      # 评审打分
└── adapters/            # Agent 适配器
    ├── base.py          # 抽象基类（继承这个来接入你的 Agent）
    ├── openai_adapter.py   # OpenAI function calling
    └── rest_api.py         # FastAPI REST 服务
```

## CLI 命令

```bash
# 存一条记忆
mempalace remember "Redis 用作缓存层" --room config

# 搜索
mempalace recall "缓存方案" --limit 5

# 启动 REST API
mempalace serve --port 8765

# 手动触发一次进化
mempalace evolve
```

## 依赖

核心只依赖一个包：

- `chromadb` — 向量存储和语义搜索

可选：
- `fastapi` + `uvicorn` — REST API 服务（`pip install mempalace-evolve[api]`）

不需要 GPU，不需要外部服务，SQLite + ChromaDB 全部本地运行。

## License

MIT
