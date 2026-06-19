#!/usr/bin/env python3
"""DreamSeed kernel doctor: inspect the active DreamSeed Lite Kernel."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def file_info(path: Path) -> dict:
    exists = path.exists()
    info = {
        "path": str(path),
        "exists": exists,
        "sizeBytes": path.stat().st_size if exists and path.is_file() else None,
    }
    if exists and path.is_file():
        try:
            data = path.read_bytes()
            info["sha256"] = hashlib.sha256(data).hexdigest()
        except OSError:
            info["sha256"] = None
    return info


def build_report() -> dict:
    root = repo_root()
    lite_default = root / "bin" / "dreamseed-lite-kernel.js"
    kernel_value = (
        os.environ.get("DREAMSEED_KERNEL_JS")
        or os.environ.get("DREAMSEED_COMPAT_KERNEL_JS")
        or str(lite_default)
    )
    kernel_path = Path(kernel_value)
    launcher = root / "bin" / "dreamseed-agent.js"
    graph_doc = root / "docs" / "kernel-knowledge-graph.md"
    kernel_ok = kernel_path.exists() and kernel_path.is_file()
    return {
        "ok": kernel_ok and launcher.exists(),
        "mode": "lite-kernel-only",
        "kernel": file_info(kernel_path),
        "launcher": file_info(launcher),
        "knowledgeGraph": file_info(graph_doc),
        "recommendations": [
            "DreamSeed Lite Kernel is the only kernel. There is no fallback to claude-cli.js.",
            "Override the kernel path with DREAMSEED_KERNEL_JS only when developing a kernel variant.",
            "Run scripts/dreamseed-audit.ps1 before publishing to verify packaging integrity.",
        ],
    }


def print_table(report: dict) -> None:
    print("DreamSeed kernel doctor")
    print(f"Mode: {report['mode']}")
    print(
        f"Kernel: {report['kernel']['path']} "
        f"({'ok' if report['kernel']['exists'] else 'missing'})"
    )
    if report["kernel"].get("sizeBytes") is not None:
        print(f"  size: {report['kernel']['sizeBytes']} bytes")
    if report["kernel"].get("sha256"):
        print(f"  sha256: {report['kernel']['sha256']}")
    print(
        f"Launcher: {report['launcher']['path']} "
        f"({'ok' if report['launcher']['exists'] else 'missing'})"
    )
    print(
        f"Knowledge graph: {report['knowledgeGraph']['path']} "
        f"({'ok' if report['knowledgeGraph']['exists'] else 'missing'})"
    )
    print("Notes:")
    for line in report["recommendations"]:
        print(f"  - {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the DreamSeed Lite Kernel installation.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()
    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_table(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
