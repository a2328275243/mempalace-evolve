"""mempalace setup — interactive MCP configuration wizard.

Detects AI tools (Claude Code / Cursor), collects parameters,
writes MCP server config, and verifies the installation works.
"""

from __future__ import annotations

import json
import platform
import shutil
import sys
import tempfile
from pathlib import Path

from mempalace_evolve.terminal import (
    banner,
    bold,
    bullet,
    cyan,
    dim,
    divider,
    fail,
    green,
    red,
    step,
    yellow,
)


# ── helpers ──────────────────────────────────────────────────────


def _input(prompt: str, default: str = "") -> str:
    """Print prompt and read a line. Returns default on empty input."""
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return val or default


def _confirm(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    val = _input(f"{prompt} ({hint})").lower()
    if not val:
        return default
    return val in ("y", "yes", "是")


# ── environment detection ────────────────────────────────────────


def _detect_os() -> str:
    return platform.system()  # Windows / Darwin / Linux


def _home() -> Path:
    return Path.home()


def _claude_settings_path() -> Path:
    return _home() / ".claude" / "settings.json"


def _cursor_settings_paths() -> list[Path]:
    """Return possible Cursor MCP config paths."""
    home = _home()
    candidates = [
        home / ".cursor" / "mcp.json",
        home / "AppData" / "Roaming" / "Cursor" / "User" / "settings.json",
    ]
    # macOS / Linux
    if _detect_os() == "Darwin":
        candidates.insert(0, home / ".cursor" / "mcp.json")
    return candidates


def _find_claude_config() -> Path | None:
    p = _claude_settings_path()
    return p if p.parent.exists() else None


def _find_cursor_config() -> Path | None:
    for p in _cursor_settings_paths():
        if p.parent.exists():
            return p
    return None


def _which(cmd: str) -> str | None:
    """Check if a command is available on PATH."""
    result = shutil.which(cmd)
    return result


# ── main wizard ──────────────────────────────────────────────────


def run_setup(wing: str | None = None, palace_path: str | None = None) -> bool:
    """Run the setup wizard. Returns True on success."""
    print(banner("MemPalace Setup Wizard"))
    print(dim("  交互式配置 MCP Server，让 AI 自动拥有记忆\n"))

    os_name = _detect_os()
    passed = 0
    failed = 0

    # ── Step 1: Environment check ──
    print(step(1, "环境检测"))
    print(divider())

    # Python
    v = sys.version_info
    if v >= (3, 10):
        print(bullet(f"Python {v.major}.{v.minor}.{v.micro}"))
        passed += 1
    else:
        print(fail(f"Python {v.major}.{v.minor} — 需要 >= 3.10"))
        failed += 1

    # OS
    print(bullet(f"操作系统: {os_name}"))

    # chromadb
    try:
        import chromadb

        print(bullet(f"chromadb {chromadb.__version__}"))
        passed += 1
    except ImportError:
        print(fail("chromadb 未安装 — 先运行 pip install mempalace-evolve"))
        failed += 1

    # mempalace-mcp command
    mcp_cmd = _which("mempalace-mcp")
    if mcp_cmd:
        print(bullet(f"mempalace-mcp 命令可用 ({mcp_cmd})"))
        passed += 1
    else:
        print(yellow("  ! mempalace-mcp 不在 PATH 中，将使用 python -m 方式启动"))
        mcp_cmd = None

    # fastmcp
    try:
        import fastmcp

        print(bullet(f"fastmcp {fastmcp.__version__}"))
        passed += 1
    except ImportError:
        print(fail("fastmcp 未安装 — 运行 pip install 'mempalace-evolve[mcp]'"))
        failed += 1

    print(divider())
    print(dim(f"  通过 {passed} 项") + (red(f"，失败 {failed} 项") if failed else ""))

    if failed > 0:
        print(red("\n  请先解决以上失败项，然后重新运行 mempalace setup"))
        return False

    # ── Step 2: Detect AI tools ──
    print(step(2, "检测 AI 工具"))
    print(divider())

    tools_found = {}

    claude_cfg = _find_claude_config()
    if claude_cfg:
        print(bullet(f"Claude Code 配置目录: {claude_cfg.parent}"))
        tools_found["claude_code"] = claude_cfg
    else:
        print(dim("      - Claude Code: 未检测到 ~/.claude/ 目录"))

    cursor_cfg = _find_cursor_config()
    if cursor_cfg:
        print(bullet(f"Cursor 配置路径: {cursor_cfg}"))
        tools_found["cursor"] = cursor_cfg
    else:
        print(dim("      - Cursor: 未检测到配置目录"))

    print(divider())

    if not tools_found:
        print(yellow("  未检测到 Claude Code 或 Cursor。"))
        print(dim("  配置片段会在下方输出，你可以手动复制到对应配置文件。\n"))
    else:
        print(bullet(f"检测到 {len(tools_found)} 个 AI 工具"))

    # ── Step 3: Collect parameters ──
    print(step(3, "配置参数"))
    print(divider())

    # Wing name
    if wing:
        wing_name = wing
        print(bullet(f"Wing 名称: {wing_name} (命令行指定)"))
    else:
        wing_name = _input("Wing 名称（用于隔离不同项目的记忆）", "global")
        print(bullet(f"Wing 名称: {wing_name}"))

    # Palace path
    if palace_path:
        resolved_path = str(Path(palace_path).resolve())
        print(bullet(f"存储路径: {resolved_path} (命令行指定)"))
    else:
        default_path = str(_home() / ".mempalace")
        raw = _input("记忆存储路径", default_path)
        resolved_path = str(Path(raw).resolve())
        print(bullet(f"存储路径: {resolved_path}"))

    print(divider())

    # ── Step 4: Choose target tool ──
    print(step(4, "选择目标"))
    print(divider())

    # Build command string
    if mcp_cmd:
        cmd_str = "mempalace-mcp"
    else:
        cmd_str = "python"
    args_str = [] if mcp_cmd else ["-m", "mempalace_evolve.adapters.mcp_server"]

    env_vars = {
        "MEMPALACE_PATH": resolved_path,
        "MEMPALACE_WING": wing_name,
    }

    config_entry = {"command": cmd_str}
    if args_str:
        config_entry["args"] = args_str
    config_entry["env"] = env_vars

    if tools_found:
        options = list(tools_found.keys())
        if len(options) == 1:
            target = options[0]
            print(bullet(f"自动选择: {_tool_display(target)}"))
        else:
            print("  检测到多个工具，请选择:")
            for i, name in enumerate(options, 1):
                print(f"    {i}. {_tool_display(name)}")
            print(f"    {len(options) + 1}. 仅输出配置（手动复制）")
            choice = _input(f"请选择 (1-{len(options) + 1})", "1")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    target = options[idx]
                else:
                    target = None
            except ValueError:
                target = options[0]

            if target:
                print(bullet(f"已选择: {_tool_display(target)}"))
    else:
        target = None

    print(divider())

    # ── Step 5: Write config ──
    print(step(5, "写入配置"))
    print(divider())

    # Show the config that will be written
    print(dim("  将写入以下配置:\n"))
    _print_config(config_entry)
    print()

    if not _confirm("确认写入？"):
        print(yellow("\n  已取消。配置片段如下，你可以手动添加:\n"))
        _print_manual_config(config_entry)
        return True

    if target and target in tools_found:
        cfg_path = tools_found[target]
        ok = _write_config(cfg_path, config_entry, target)
        if ok:
            print(bullet(f"配置已写入: {cfg_path}"))
        else:
            return False
    else:
        print(yellow("\n  配置片段如下，手动添加到对应文件即可:\n"))
        _print_manual_config(config_entry)
        print()
        print(bullet("配置已输出"))
        return True

    print(divider())

    # ── Step 6: Verify ──
    print(step(6, "验证安装"))
    print(divider())

    # Verify JSON is valid
    cfg_path = tools_found.get(target)
    if cfg_path and cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            mempalace_cfg = data.get("mcpServers", {}).get("mempalace")
            if mempalace_cfg:
                print(bullet("JSON 格式验证通过"))
                print(bullet("mempalace 配置项已存在"))
            else:
                print(fail("未找到 mempalace 配置项"))
                failed += 1
        except json.JSONDecodeError as e:
            print(fail(f"JSON 格式错误: {e}"))
            return False

    # Verify MCP server can start
    print(dim("  测试 MCP Server 启动..."))
    verify_ok = _verify_mcp_start(resolved_path, wing_name)
    if verify_ok:
        print(bullet("MCP Server 启动测试通过"))
    else:
        print(yellow("  ! MCP Server 启动测试未通过（不影响配置，可能是环境问题）"))

    print(divider())

    # ── Summary ──
    print(bold(green("\n  配置完成！")))
    print(
        dim(f"""
  下一步:
    1. 重启你的 AI 工具（{_tool_display(target) if target else "Claude Code / Cursor"}）
    2. AI 会自动获得记忆工具: remember, recall, add_fact, query_entity, forget, evolve
    3. 试试让 AI 记住点什么："记住这个项目用 FastAPI"

  管理记忆:
    mempalace recall "搜索词"     搜索记忆
    mempalace evolve              手动触发进化
    mempalace doctor              检查环境
""")
    )
    return True


def _tool_display(name: str) -> str:
    return {"claude_code": "Claude Code", "cursor": "Cursor"}.get(name, name)


def _print_config(config_entry: dict) -> None:
    """Pretty-print the config entry."""
    print(dim('  "mempalace": '))
    print("  " + json.dumps(config_entry, indent=4, ensure_ascii=False).replace("\n", "\n  "))


def _print_manual_config(config_entry: dict) -> None:
    """Print full config snippet for manual copy."""
    full = {"mcpServers": {"mempalace": config_entry}}
    print(cyan(json.dumps(full, indent=2, ensure_ascii=False)))


def _write_config(cfg_path: Path, config_entry: dict, tool: str) -> bool:
    """Read existing config, merge mempalace entry, write back with backup."""
    # Ensure directory exists
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing
    existing = {}
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            # Backup
            bak_path = cfg_path.with_suffix(cfg_path.suffix + ".bak")
            shutil.copy2(cfg_path, bak_path)
            print(dim(f"  已备份旧配置: {bak_path}"))
        except (json.JSONDecodeError, OSError) as e:
            print(fail(f"读取配置失败: {e}"))
            return False

    # Merge — for Claude Code, top-level key is "mcpServers"
    servers = existing.setdefault("mcpServers", {})
    servers["mempalace"] = config_entry

    # Write
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError as e:
        print(fail(f"写入配置失败: {e}"))
        # Try to restore backup
        bak_path = cfg_path.with_suffix(cfg_path.suffix + ".bak")
        if bak_path.exists():
            shutil.copy2(bak_path, cfg_path)
            print(dim("  已从备份恢复"))
        return False

    return True


def _verify_mcp_start(palace_path: str, wing: str) -> bool:
    """Try to import and instantiate the MCP server to verify it works."""
    try:
        tmp = tempfile.mkdtemp(prefix="mempalace_setup_verify_")
        from mempalace_evolve.adapters.mcp_server import create_mcp_server

        create_mcp_server(palace_path=tmp, wing="setup_test")
        # If we got here, the server object was created successfully
        shutil.rmtree(tmp, ignore_errors=True)
        return True
    except Exception as e:
        print(dim(f"  验证详情: {e}"))
        return False
