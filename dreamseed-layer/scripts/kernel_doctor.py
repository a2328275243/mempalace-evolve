#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def file_info(path: Path) -> dict:
    exists = path.exists()
    return {
        "path": str(path),
        "exists": exists,
        "sizeBytes": path.stat().st_size if exists and path.is_file() else None,
    }


def runtime_patch_status(path: Path) -> dict:
    if not path.exists() or not path.is_file():
        return {
            "checked": False,
            "hasUtf8Bom": None,
            "fastCompactRescue": False,
            "summarizedIdFallback": False,
            "backupCount": 0,
        }
    data = path.read_bytes()
    text = data.decode("utf-8-sig", errors="replace")
    backups = list(path.parent.glob(path.name + ".before-fast-compact-rescue-*.bak"))
    return {
        "checked": True,
        "hasUtf8Bom": data.startswith(b"\xef\xbb\xbf"),
        "fastCompactRescue": "DreamSeed fast compact rescue" in text,
        "summarizedIdFallback": 'tengu_sm_compact_summarized_id_not_found",{})}else' in text,
        "backupCount": len(backups),
    }


def build_report() -> dict:
    root = repo_root()
    local_root = Path(os.environ.get("DREAMSEED_LOCAL_ROOT", "") or root)
    compat_kernel_value = (
        os.environ.get("DREAMSEED_COMPAT_KERNEL_JS")
        or os.environ.get("DREAMSEED_KERNEL_JS")
        or str(local_root / "runtime" / ("cl" + "aude-cli.js"))
    )
    compat_cli = os.environ.get("DREAMSEED_COMPAT_KERNEL_CLI") or os.environ.get("DREAMSEED_KERNEL_CLI") or ""
    compat_kernel = Path(compat_kernel_value)
    graph_doc = root / "docs" / "kernel-knowledge-graph.md"
    compat_ok = compat_kernel.exists() or bool(compat_cli)
    compact_patch = runtime_patch_status(compat_kernel)
    return {
        "ok": compat_ok and graph_doc.exists() and (not compact_patch["checked"] or not compact_patch["hasUtf8Bom"]),
        "mode": "compatible-only",
        "effectiveDefault": "compat",
        "compatKernel": file_info(compat_kernel),
        "compactPatch": compact_patch,
        "compatCli": compat_cli,
        "knowledgeGraph": file_info(graph_doc),
        "knownSlowCluster": [
            "entrypoints/init.ts -> gracefulShutdown",
            "cli/print.ts -> cleanup + structured output flush",
            "utils/telemetry/instrumentation.ts -> beforeExit + shutdown",
            "cli/transports/HybridTransport.ts -> SerialBatchEventUploader",
            "hooks/MCP/history cleanup registered through cleanupRegistry",
        ],
        "recommendations": [
            "DreamSeed now routes all interactive and --print runs through the compatible runtime.",
            "Treat fixed 79-82s delays as compatible-runtime lifecycle issues, not provider bridge issues.",
            "Do not reintroduce a second kernel unless its tool, history, resume, and packaging behavior are fully compatible.",
            "If /compact stalls, run scripts/dreamseed-runtime-compact-patch.ps1 status; fastCompactRescue should be true for the local bundled compatible runtime.",
        ],
    }


def print_table(report: dict) -> None:
    print("DreamSeed kernel doctor")
    print(f"Mode: {report['mode']}")
    print(f"Effective default: {report['effectiveDefault']}")
    print(
        f"Compat kernel: {report['compatKernel']['path']} "
        f"({'ok' if report['compatKernel']['exists'] else 'missing'})"
    )
    patch = report["compactPatch"]
    if patch["checked"]:
        print(
            "Compact patch: "
            f"fastRescue={patch['fastCompactRescue']} "
            f"summarizedIdFallback={patch['summarizedIdFallback']} "
            f"utf8Bom={patch['hasUtf8Bom']} "
            f"backups={patch['backupCount']}"
        )
    if report["compatCli"]:
        print(f"Compat CLI: {report['compatCli']}")
    print(
        f"Knowledge graph: {report['knowledgeGraph']['path']} "
        f"({'ok' if report['knowledgeGraph']['exists'] else 'missing'})"
    )
    print("Known slow cluster:")
    for item in report["knownSlowCluster"]:
        print(f"  - {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect DreamSeed compatible runtime routing.")
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
