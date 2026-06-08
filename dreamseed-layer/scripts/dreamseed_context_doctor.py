from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect DreamSeed context and token pressure.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = build_report(root, top=max(1, args.top))
    if args.json:
        print_json(report)
    else:
        print_table(report)
    return 0 if report["ok"] else 1


def build_report(root: Path, top: int = 10) -> dict[str, Any]:
    scanned: list[dict[str, Any]] = []
    missing: list[str] = []

    for rel in [
        "docs/dreamseed-system-prompt.md",
        ".mcp.json",
        "config/brand_allowlist.json",
        "config/mcp.registry.json",
        "AGENTS.md",
        "DREAMSEED.md",
        "README.md",
    ]:
        add_file(root, rel, scanned, missing)

    for pattern in [
        ".dreamseed/skills/*/SKILL.md",
        ".dreamseed/agents/*.md",
        "config/*.json",
    ]:
        for path in sorted(root.glob(pattern)):
            add_path(path, root, scanned)

    candidate_dir = root / "memory-candidates"
    candidate_files = sorted(candidate_dir.glob("*.json")) if candidate_dir.exists() else []
    legacy_manifest = read_json(root / "legacy-history" / "claude-code" / "manifest.json")
    history_stats = {
        "legacyManifestPresent": bool(legacy_manifest),
        "recordCount": legacy_manifest.get("record_count", 0) if isinstance(legacy_manifest, dict) else 0,
        "sessionCount": legacy_manifest.get("session_count", 0) if isinstance(legacy_manifest, dict) else 0,
        "projectCount": legacy_manifest.get("project_count", 0) if isinstance(legacy_manifest, dict) else 0,
        "resumePolicy": "summary-only; do not inject raw legacy history into every prompt",
    }

    if candidate_files:
        total_candidate_bytes = sum(p.stat().st_size for p in candidate_files if p.exists())
        scanned.append(
            {
                "path": "memory-candidates/*.json",
                "kind": "memory-candidate-pool",
                "chars": total_candidate_bytes,
                "approxTokens": approx_tokens(total_candidate_bytes),
                "risk": risk_label(total_candidate_bytes),
                "count": len(candidate_files),
            }
        )

    unique = dedupe(scanned)
    largest = sorted(unique, key=lambda item: item["chars"], reverse=True)[:top]
    total_chars = sum(item["chars"] for item in unique)
    report = {
        "ok": True,
        "root": str(root),
        "summary": {
            "scannedItems": len(unique),
            "totalChars": total_chars,
            "approxTokens": approx_tokens(total_chars),
            "memoryCandidateCount": len(candidate_files),
            "legacyHistory": history_stats,
        },
        "largest": largest,
        "recommendations": recommendations(largest, history_stats, len(candidate_files)),
        "missingOptional": missing,
    }
    return report


def add_file(root: Path, rel: str, scanned: list[dict[str, Any]], missing: list[str]) -> None:
    path = root / rel
    if not path.exists():
        missing.append(rel)
        return
    add_path(path, root, scanned)


def add_path(path: Path, root: Path, scanned: list[dict[str, Any]]) -> None:
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
        chars = len(text)
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        chars = len(text)
    except OSError:
        return
    rel = str(path.relative_to(root)).replace("\\", "/")
    scanned.append(
        {
            "path": rel,
            "kind": classify_path(rel),
            "chars": chars,
            "approxTokens": approx_tokens(chars),
            "risk": risk_label(chars),
        }
    )


def classify_path(rel: str) -> str:
    if rel.endswith("dreamseed-system-prompt.md"):
        return "system-prompt"
    if "/skills/" in rel:
        return "skill"
    if "/agents/" in rel:
        return "agent"
    if rel.endswith(".json"):
        return "json-config"
    return "doc"


def approx_tokens(chars: int) -> int:
    return int(math.ceil(max(0, chars) / 4))


def risk_label(chars: int) -> str:
    if chars >= 60000:
        return "high"
    if chars >= 20000:
        return "medium"
    return "low"


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("path"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def recommendations(largest: list[dict[str, Any]], history_stats: dict[str, Any], candidate_count: int) -> list[str]:
    recs: list[str] = []
    for item in largest[:5]:
        if item["risk"] in {"medium", "high"}:
            recs.append(f"Review {item['path']} before adding it to default prompt context.")
        if item["kind"] in {"memory-candidate-pool", "json-config"} and item["chars"] >= 12000:
            recs.append("Use DREAMSEED_OUTPUT_COMPRESS=auto for long tool/log output; keep final answers uncompressed.")
    if candidate_count > 100:
        recs.append("Run memory_review.py reject --all-noisy, then promote only reviewed candidates.")
    if history_stats.get("sessionCount", 0):
        recs.append("Keep /resume summary-based; avoid loading raw legacy sessions into every request.")
    recs.append("Runtime output compression is opt-in: DREAMSEED_OUTPUT_COMPRESS=off|auto|always and DREAMSEED_OUTPUT_COMPRESS_LIMIT=12000.")
    if not recs:
        recs.append("Context footprint is small enough for the current source-first setup.")
    return recs[:10]


def print_table(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print("DreamSeed context doctor")
    print(f"Root: {report['root']}")
    print(f"Scanned: {summary['scannedItems']} items, approx {summary['approxTokens']} tokens")
    print("")
    print("Largest context sources:")
    for item in report["largest"]:
        count = f" count={item['count']}" if "count" in item else ""
        print(f"  - {item['path']}  chars={item['chars']}  tokens~{item['approxTokens']}  risk={item['risk']}{count}")
    print("")
    print("Recommendations:")
    for rec in report["recommendations"]:
        print(f"  - {rec}")


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
