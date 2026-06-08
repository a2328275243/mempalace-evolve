#!/usr/bin/env python3
"""DreamSeed Manager UI - 模型管理器入口"""

import os
import sys
import webbrowser
import threading
import time

def start_manager():
    """启动模型管理器 Web UI"""
    script_path = os.path.join(
        os.path.dirname(__file__),
        "dreamseed-layer",
        "scripts",
        "manager.ps1"
    )

    print("🌐 启动 DreamSeed 模型管理器...")
    print("   浏览器将自动打开 http://127.0.0.1:8765")
    print("   按 Ctrl+C 停止服务\n")

    # 尝试启动管理器
    try:
        os.system(f'powershell -ExecutionPolicy Bypass -File "{script_path}"')
    except Exception as e:
        print(f"启动失败: {e}")
        print("请手动运行: dreamseed manager")

if __name__ == "__main__":
    start_manager()