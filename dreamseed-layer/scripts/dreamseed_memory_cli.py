from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SECRET_RE = re.compile(r"sk-[A-Za-z0-9_-]{20,}|(api[_-]?key|token|secret|password)\s*[:=]", re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser(description="DreamSeed memory candidate CLI")
    sub = parser.add_subparsers(dest="command")

    candidates = sub.add_parser("candidates")
    candidates.add_argument("--json", action="store_true")
    candidates.add_argument("--limit", type=int, default=30)

    review = sub.add_parser("review")
    review.add_argument("--json", action="store_true")
    review.add_argument("--apply", action="store_true")
    review.add_argument("--all", action="store_true")
    review.add_argument("--min-score", default="0.55")

    reject = sub.add_parser("reject-noisy")
    reject.add_argument("--json", action="store_true")

    promote = sub.add_parser("promote-reviewed")
    promote.add_argument("--json", action="store_true")
    promote.add_argument("--dry-run", action="store_true")
    promote.add_argument("--yes", action="store_true")
    promote.add_argument("--room", default="project")

    audit = sub.add_parser("audit")
    audit.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if not args.command:
        args.command = "audit"
        args.json = False

    if args.command == "candidates":
        return proxy(["memory_review.py", "list", "--limit", str(args.limit), "--all"], args.json)
    if args.command == "review":
        command = ["memory_review.py", "apply" if args.apply else "list"]
        if args.all or args.apply:
            command.append("--all")
        if args.apply:
            command.extend(["--min-score", str(args.min_score)])
        return proxy(command, args.json)
    if args.command == "reject-noisy":
        return proxy(["memory_review.py", "reject", "--all-noisy"], args.json)
    if args.command == "promote-reviewed":
        if not args.dry_run and not args.yes:
            print_json({"ok": False, "error": "Refusing to promote memory without --yes or --dry-run"})
            return 1
        command = ["memory_promote.py", "promote-reviewed", "--all", "--room", args.room]
        if args.dry_run:
            command.append("--dry-run")
        return proxy(command, args.json)
    if args.command == "audit":
        payload = audit_memory()
        if args.json:
            print_json(payload)
        else:
            print_audit(payload)
        return 0 if payload["ok"] else 1
    return 2


def proxy(command: list[str], json_output: bool) -> int:
    script = ROOT / "scripts" / command[0]
    completed = subprocess.run(
        [sys.executable, str(script), *command[1:]],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    text = completed.stdout.strip()
    if json_output:
        if text:
            try:
                print_json(json.loads(text))
            except json.JSONDecodeError:
                print_json({"ok": completed.returncode == 0, "stdout": text, "stderr": completed.stderr})
        else:
            print_json({"ok": completed.returncode == 0, "stderr": completed.stderr})
    else:
        if text:
            print(text)
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
    return completed.returncode


def candidate_dir() -> Path:
    import os

    return Path(
        os.environ.get("DREAMSEED_MEMORY_CANDIDATES_DIR")
        or os.environ.get("DREAMSEED_CANDIDATE_DIR")
        or ROOT / "memory-candidates"
    )


def audit_memory() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from memory_review import load_json, review_decision

    base = candidate_dir()
    pending = sorted(base.glob("*.json")) if base.exists() else []
    reviewed = sorted((base / "reviewed").glob("*.json")) if (base / "reviewed").exists() else []
    rejected = sorted((base / "rejected").glob("*.json")) if (base / "rejected").exists() else []
    promoted = sorted((base / "promoted").glob("*.json")) if (base / "promoted").exists() else []
    counts: dict[str, int] = {}
    samples = []
    hashes: dict[str, list[str]] = {}
    secret_hits = 0

    for path in pending:
        try:
            data = load_json(path)
        except Exception:
            counts["invalid"] = counts.get("invalid", 0) + 1
            continue
        decision = review_decision(data)
        action = str(decision.get("action"))
        counts[action] = counts.get(action, 0) + 1
        digest = str(data.get("hash") or data.get("id") or path.stem)
        hashes.setdefault(digest, []).append(path.name)
        text = f"{data.get('summary','')} {data.get('text','')}"
        if SECRET_RE.search(text):
            secret_hits += 1
        if len(samples) < 12:
            samples.append(
                {
                    "id": data.get("id") or path.stem,
                    "action": action,
                    "score": decision.get("overall_score"),
                    "summary": str(data.get("summary", ""))[:160],
                }
            )

    duplicates = {key: value for key, value in hashes.items() if len(value) > 1}
    return {
        "ok": secret_hits == 0,
        "candidateDir": str(base),
        "counts": {
            "pendingFiles": len(pending),
            "reviewedFiles": len(reviewed),
            "rejectedFiles": len(rejected),
            "promotedFiles": len(promoted),
            **counts,
        },
        "duplicates": duplicates,
        "secretHits": secret_hits,
        "promotionPath": "candidate -> reviewed -> memory_promote.py promote-reviewed -> MemPalace",
        "samples": samples,
    }


def print_audit(payload: dict[str, Any]) -> None:
    print("DreamSeed memory audit")
    print(f"Candidate dir: {payload['candidateDir']}")
    for key, value in payload["counts"].items():
        print(f"  {key}: {value}")
    print(f"Secret-like candidates: {payload['secretHits']}")
    if payload["duplicates"]:
        print(f"Duplicate groups: {len(payload['duplicates'])}")
    print("Promotion path: " + payload["promotionPath"])


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
