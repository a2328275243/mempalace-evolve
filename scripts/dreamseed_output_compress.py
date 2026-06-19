from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


IMPORTANT_RE = re.compile(
    r"(error|failed|failure|exception|traceback|warning|denied|missing|invalid|\b[A-Za-z]:\\[^:\s]+:\d+|/[^:\s]+:\d+)",
    re.IGNORECASE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compress noisy tool output while preserving actionable lines.")
    sub = parser.add_subparsers(dest="command", required=True)

    compress = sub.add_parser("compress-log", help="Compress a log file or stdin")
    compress.add_argument("path", nargs="?")
    compress.add_argument("--keep-last", type=int, default=20)
    compress.add_argument("--json", action="store_true")

    smoke = sub.add_parser("smoke", help="Run a built-in compressor smoke test")
    smoke.add_argument("--json", action="store_true")
    policy = sub.add_parser("policy", help="Show runtime compression policy")
    policy.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "compress-log":
        text = read_input(args.path)
        result = compress_text(text, keep_last=args.keep_last)
        if args.json:
            print_json(result)
        else:
            print(result["text"])
        return 0

    if args.command == "smoke":
        sample = "\n".join(
            [
                "line 1 normal progress",
                "line 2 normal progress",
                "WARNING: retrying provider bridge",
                "C:\\work\\app.py:42: ValueError: bad state",
                "Traceback (most recent call last):",
                "Exception: boom",
                "tail one",
                "tail two",
            ]
        )
        result = compress_text(sample, keep_last=2)
        ok = "ValueError" in result["text"] and "tail two" in result["text"]
        payload = {"ok": ok, "result": result}
        if args.json:
            print_json(payload)
        else:
            print("DreamSeed output compressor smoke: " + ("ok" if ok else "failed"))
            print(result["text"])
        return 0 if ok else 1
    if args.command == "policy":
        payload = {
            "ok": True,
            "mode": "off|auto|always",
            "defaultMode": "off",
            "limitEnv": "DREAMSEED_OUTPUT_COMPRESS_LIMIT",
            "defaultLimit": 12000,
            "scope": "tool output and long logs only; never user input, final answers, or secret-bearing diagnostics",
            "preserves": ["errors", "exceptions", "paths", "line numbers", "failure summaries", "last N lines"],
        }
        if args.json:
            print_json(payload)
        else:
            print("DreamSeed output compression policy")
            print(f"Default: {payload['defaultMode']}")
            print("Scope: " + payload["scope"])
        return 0
    return 2


def read_input(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8-sig", errors="replace")
    return sys.stdin.read()


def compress_text(text: str, keep_last: int = 20) -> dict[str, Any]:
    lines = text.splitlines()
    keep_indexes: set[int] = set()
    for idx, line in enumerate(lines):
        if IMPORTANT_RE.search(line):
            keep_indexes.add(idx)
            if idx > 0:
                keep_indexes.add(idx - 1)
            if idx + 1 < len(lines):
                keep_indexes.add(idx + 1)

    for idx in range(max(0, len(lines) - keep_last), len(lines)):
        keep_indexes.add(idx)

    selected = [lines[idx] for idx in sorted(keep_indexes)]
    omitted = max(0, len(lines) - len(selected))
    header = f"[dreamseed-output-compress] kept={len(selected)} omitted={omitted}"
    return {
        "ok": True,
        "originalLines": len(lines),
        "keptLines": len(selected),
        "omittedLines": omitted,
        "text": "\n".join([header, *selected]),
    }


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
