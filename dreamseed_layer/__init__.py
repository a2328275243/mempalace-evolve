#!/usr/bin/env python3
"""DreamSeed CLI Entry Point - 智能体操作系统入口"""

import sys
import os
from pathlib import Path

# 修复路径：向上两级到达项目根目录
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DREAMSEED_LAYER = PROJECT_ROOT / "dreamseed-layer"

def main():
    """主入口：根据参数调用对应功能"""
    if len(sys.argv) < 2:
        print("DreamSeed AI Agent OS")
        print("=" * 50)
        print("使用方法:")
        print("  dreamseed              - 启动智能体终端")
        print("  dreamseed manager      - 打开模型管理器")
        print("  dreamseed doctor       - 检查环境状态")
        print("  dreamseed --help       - 显示帮助信息")
        return

    command = sys.argv[1]

    if command == "manager":
        # 启动模型管理器 UI - 使用 package.json 中的脚本
        print("🌐 启动 DreamSeed 模型管理器...")
        print("   浏览器将自动打开 http://127.0.0.1:17941")
        print("   按 Ctrl+C 停止服务\n")
        manager_script = DREAMSEED_LAYER / "scripts" / "provider_manager.mjs"
        if manager_script.exists():
            os.system(f'cd "{DREAMSEED_LAYER}" && npm run manager')
        else:
            print(f"错误: 找不到管理器脚本 {manager_script}")
            sys.exit(1)
    elif command == "doctor":
        # 环境检查
        print("🔍 检查 DreamSeed 环境...")
        # 使用 dreamseed-memory-bridge 进行诊断
        bridge_script = DREAMSEED_LAYER / "scripts" / "dreamseed_memory_bridge.py"
        if bridge_script.exists():
            os.system(f'python "{bridge_script}" doctor')
        else:
            print(f"错误: 找不到诊断脚本 {bridge_script}")
            sys.exit(1)
    else:
        # 启动智能体终端
        print("🚀 启动 DreamSeed 智能体...")
        # 调用 dreamseed-lite-kernel 或外部兼容 CLI
        kernel_path = DREAMSEED_LAYER / "bin" / "dreamseed-lite-kernel.js"
        if kernel_path.exists():
            os.system(f'node "{kernel_path}" ' + ' '.join(sys.argv[1:]))
        else:
            # 回退到外部 CLI
            os.system("dreamseed " + ' '.join(sys.argv[1:]))

if __name__ == "__main__":
    main()