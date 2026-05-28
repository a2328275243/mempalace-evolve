# UX 改进计划：让用户感觉有用、安装方便

## 目标
比赛评委 30 秒内感受到价值，零代码体验完整功能。

## 实施顺序

### 1. `terminal.py` — ANSI 颜色工具（~35 行）
- 零依赖，纯 stdlib
- bold/cyan/green/yellow/red/dim/divider/step/bullet
- Windows VT100 兼容

### 2. `demo.py` — 一键演示（~100 行，最高优先）
- `mempalace demo` 命令
- 临时目录，自动清理
- 5 步展示：存储→语义搜索→知识图谱→进化管道→统计
- 彩色输出

### 3. `doctor.py` — 安装诊断（~60 行）
- `mempalace doctor` 命令
- 检查 Python 版本、chromadb、读写测试、可选依赖

### 4. `playground.py` — 交互式 REPL（~80 行）
- `mempalace playground` 命令
- 基于 cmd.Cmd，输入即存储，/search /fact /entity /evolve /quit

### 5. `cli.py` 改造
- 加 --version、demo/doctor/playground 子命令
- 全局 try/except 错误处理

### 6. `README.md` 升级
- 加 badges（PyPI/Python/License/Tests）
- 加"30 秒体验"段落
- 保持中文为主

## 约束
- 零新依赖（纯 ANSI + stdlib）
- 不修改现有 SDK/适配器代码
- 现有 40 测试不受影响
