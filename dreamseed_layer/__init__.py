#!/usr/bin/env python3
"""DreamSeed CLI Entry Point - 智能体操作系统入口"""

import sys
import os
from pathlib import Path

# 将 dreamseed-layer 添加到路径
SCRIPT_DIR = Path(__file__).parent
DREAMSEED_LAYER = SCRIPT_DIR / "dreamseed-layer"

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
        # 启动模型管理器 UI
        try:
            from dreamseed_layer.manager_ui import start_manager
            start_manager()
        except ImportError as e:
            print(f"错误: 无法启动模型管理器 - {e}")
            print("请确保已正确安装 dreamseed-layer 依赖")
            sys.exit(1)
    elif command == "doctor":
        # 环境检查
        print("🔍 检查 DreamSeed 环境...")
        os.system(f'powershell -File "{DREAMSEED_LAYER}/scripts/dreamseed-doctor.ps1"')
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