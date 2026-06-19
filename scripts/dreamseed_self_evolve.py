from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_DIR = Path(
    os.environ.get("DREAMSEED_EVOLVE_CANDIDATES_DIR")
    or ROOT / "self-evolve-candidates"
)
BACKUP_DIR = Path(
    os.environ.get("DREAMSEED_EVOLVE_BACKUP_DIR")
    or ROOT / "self-evolve-backups"
)
MEMORY_CANDIDATES_DIR = Path(
    os.environ.get("DREAMSEED_MEMORY_CANDIDATES_DIR")
    or os.environ.get("DREAMSEED_CANDIDATE_DIR")
    or ROOT / "memory-candidates"
)

ALLOWED_ROOTS = {
    ".dreamseed",
    "AGENTS.md",
    "DREAMSEED.md",
    "README.md",
    ".gitignore",
    ".mcp.json",
    "bin",
    "config",
    "docs",
    "manager",
    "package.json",
    "requirements-dreamseed.txt",
    "scripts",
}

DENIED_ROOTS = {
    ".dreamseed-memory",
    ".dreamseed-runtime",
    ".mempalace",
    ".pytest_cache",
    ".cache",
    "dist",
    "legacy-history",
    "memory-candidates",
    "node_modules",
    "package",
    "self-evolve-backups",
    "self-evolve-candidates",
}

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._~+/=-]{12,}"),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Controlled DreamSeed self-evolution proposals"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_parser = sub.add_parser("status", help="Show self-evolution status")
    status_parser.add_argument("--json", action="store_true")

    list_parser = sub.add_parser("list", help="List proposals")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--json", action="store_true")

    inspect_parser = sub.add_parser("inspect", help="Inspect one proposal")
    inspect_parser.add_argument("id")

    propose_parser = sub.add_parser("propose", help="Create a proposal candidate")
    propose_parser.add_argument("--title", default="DreamSeed self-evolution proposal")
    propose_parser.add_argument("--problem", default="")
    propose_parser.add_argument("--risk", choices=("low", "medium", "high"), default="medium")
    propose_parser.add_argument("--evidence", action="append", default=[])
    propose_parser.add_argument("--change", action="append", default=[])
    propose_parser.add_argument("--file", action="append", default=[])
    propose_parser.add_argument("--verify", action="append", default=[])
    propose_parser.add_argument("--rollback", action="append", default=[])
    propose_parser.add_argument("--dry-run", action="store_true")

    apply_parser = sub.add_parser("apply", help="Apply staged files from a proposal")
    apply_parser.add_argument("id")
    apply_parser.add_argument("--yes", action="store_true", help="Required to modify files")
    apply_parser.add_argument("--allow-high-risk", action="store_true")
    apply_parser.add_argument("--skip-verify", action="store_true")
    apply_parser.add_argument("--memory-candidate", action="store_true")
    apply_parser.add_argument("--lesson", default="")

    verify_parser = sub.add_parser("verify", help="Run DreamSeed verification gates")
    verify_parser.add_argument("id", nargs="?")
    verify_parser.add_argument("--json", action="store_true")

    score_parser = sub.add_parser("score", help="Score a proposal without applying it")
    score_parser.add_argument("id")
    score_parser.add_argument("--json", action="store_true")

    test_parser = sub.add_parser("test", help="Run verification gates for a proposal")
    test_parser.add_argument("id")
    test_parser.add_argument("--json", action="store_true")

    archive_parser = sub.add_parser("archive-failure", help="Archive a failed proposal locally")
    archive_parser.add_argument("id")
    archive_parser.add_argument("--reason", default="")
    archive_parser.add_argument("--json", action="store_true")

    rollback_parser = sub.add_parser("rollback", help="Rollback an applied proposal")
    rollback_parser.add_argument("id")
    rollback_parser.add_argument("--yes", action="store_true", help="Required to restore files")

    memory_parser = sub.add_parser(
        "memory-candidate",
        help="Write a reviewed-later memory candidate for an applied proposal",
    )
    memory_parser.add_argument("id")
    memory_parser.add_argument("--lesson", default="")

    args = parser.parse_args()

    if args.command == "status":
        return command_status(json_output=args.json)
    if args.command == "list":
        return command_list(limit=args.limit, json_output=args.json)
    if args.command == "inspect":
        return command_inspect(args.id)
    if args.command == "propose":
        return command_propose(args)
    if args.command == "apply":
        return command_apply(args)
    if args.command == "verify":
        return command_verify(args.id, json_output=args.json)
    if args.command == "score":
        return command_score(args.id, json_output=args.json)
    if args.command == "test":
        return command_verify(args.id, json_output=args.json)
    if args.command == "archive-failure":
        return command_archive_failure(args.id, reason=args.reason, json_output=args.json)
    if args.command == "rollback":
        return command_rollback(args)
    if args.command == "memory-candidate":
        result = write_memory_candidate(resolve_proposal(args.id), lesson=args.lesson)
        print_json({"ok": True, "memory_candidate": result})
        return 0

    return 2


def command_status(json_output: bool = False) -> int:
    proposals = list_proposal_paths()
    by_status: dict[str, int] = {}
    for path in proposals:
        data = read_json(path / "proposal.json")
        by_status[str(data.get("status") or "unknown")] = (
            by_status.get(str(data.get("status") or "unknown"), 0) + 1
        )
    payload = {
        "ok": True,
        "root": str(ROOT),
        "proposal_dir": str(PROPOSAL_DIR),
        "backup_dir": str(BACKUP_DIR),
        "memory_candidates_dir": str(MEMORY_CANDIDATES_DIR),
        "proposals": len(proposals),
        "by_status": by_status,
        "audit_script": str(ROOT / "scripts" / "dreamseed-audit.ps1"),
        "allowed_roots": sorted(ALLOWED_ROOTS),
    }
    if json_output:
        print_json(payload)
    else:
        print("DreamSeed self-evolution status")
        print(f"Root: {payload['root']}")
        print(f"Proposal dir: {payload['proposal_dir']}")
        print(f"Backup dir: {payload['backup_dir']}")
        print(f"Proposals: {payload['proposals']}")
        if by_status:
            for name, count in sorted(by_status.items()):
                print(f"  {name}: {count}")
        print("Flow: propose -> stage files -> apply --yes -> verify -> memory-candidate")
    return 0


def command_list(limit: int, json_output: bool = False) -> int:
    items = []
    for path in list_proposal_paths()[: max(0, limit)]:
        data = read_json(path / "proposal.json")
        items.append(proposal_summary(path, data))
    if json_output:
        print_json({"ok": True, "shown": len(items), "proposals": items})
    else:
        if not items:
            print("No self-evolution proposals found.")
            return 0
        for item in items:
            print(
                f"{item['id']}  status={item['status']}  risk={item['risk']}  "
                f"files={item['staged_files']}  {item['title']}"
            )
    return 0


def command_inspect(value: str) -> int:
    path = resolve_proposal(value)
    data = read_json(path / "proposal.json")
    data["proposal_path"] = str(path)
    data["staged_files"] = [str(p) for p in staged_files(path)]
    print_json({"ok": True, "proposal": data})
    return 0


def command_propose(args: argparse.Namespace) -> int:
    rel_files = [normalize_rel_path(value) for value in args.file]
    for rel in rel_files:
        validate_target_rel(rel)

    created_at = now()
    seed = f"{created_at}|{args.title}|{args.problem}|{'|'.join(args.change)}"
    proposal_id = "self-evolve-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    proposal_id += "-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    proposal_path = PROPOSAL_DIR / proposal_id

    data = {
        "id": proposal_id,
        "created_at": created_at,
        "status": "proposed",
        "review": "pending",
        "title": args.title.strip() or "DreamSeed self-evolution proposal",
        "problem": args.problem.strip(),
        "risk": args.risk,
        "evidence": [value.strip() for value in args.evidence if value.strip()],
        "proposed_changes": [value.strip() for value in args.change if value.strip()],
        "target_files": rel_files,
        "verification_plan": (
            [value.strip() for value in args.verify if value.strip()]
            or [
                "python scripts/brand_audit.py scan --strict",
                "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dreamseed-audit.ps1",
                "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dreamseed-smoke.ps1 -SkipModelCall -SkipPackage",
            ]
        ),
        "rollback_plan": (
            [value.strip() for value in args.rollback if value.strip()]
            or [f"python scripts/dreamseed_self_evolve.py rollback {proposal_id} --yes"]
        ),
        "staging": {
            "instructions": "Put replacement files under files/<relative-path>, then run apply --yes.",
            "dir": "files",
        },
        "safety": {
            "allowed_roots": sorted(ALLOWED_ROOTS),
            "denied_roots": sorted(DENIED_ROOTS),
            "requires_explicit_apply": True,
            "secrets_blocked": True,
            "pre_apply_gates": ["path guard", "secret scan", "brand audit", "targeted smoke"],
        },
    }

    if args.dry_run:
        print_json({"ok": True, "dry_run": True, "proposal": data})
        return 0

    proposal_path.mkdir(parents=True, exist_ok=False)
    (proposal_path / "files").mkdir()
    write_json(proposal_path / "proposal.json", data)
    (proposal_path / "REVIEW.md").write_text(render_review(data), encoding="utf-8")
    print_json({"ok": True, "proposal": proposal_summary(proposal_path, data)})
    return 0


def command_apply(args: argparse.Namespace) -> int:
    if not args.yes:
        raise SystemExit("Refusing to modify files without --yes")

    proposal_path = resolve_proposal(args.id)
    proposal_file = proposal_path / "proposal.json"
    data = read_json(proposal_file)
    status = data.get("status")
    if status == "applied":
        raise SystemExit(f"Proposal is already applied: {data.get('id')}")
    if status not in {"proposed", "verify-failed", "rolled-back"}:
        raise SystemExit(f"Proposal is not applyable from status: {status}")
    if data.get("risk") == "high" and not args.allow_high_risk:
        raise SystemExit("High-risk proposal requires --allow-high-risk")

    staged = staged_files(proposal_path)
    if not staged:
        raise SystemExit("No staged files found. Add files under proposal/files/<relative-path> first.")

    file_plan = []
    for staged_path in staged:
        rel = normalize_rel_path(str(staged_path.relative_to(proposal_path / "files")))
        validate_target_rel(rel)
        text = staged_path.read_text(encoding="utf-8-sig")
        validate_publishable_text(rel, text)
        file_plan.append((rel, staged_path, ROOT / rel))

    backup_path = BACKUP_DIR / str(data["id"])
    if backup_path.exists():
        raise SystemExit(f"Backup already exists for proposal: {backup_path}")
    backup_path.mkdir(parents=True)

    manifest = {
        "id": data["id"],
        "created_at": now(),
        "files": [],
    }

    applied = []
    try:
        for rel, staged_path, target_path in file_plan:
            entry = {"path": rel, "existed": target_path.exists()}
            if target_path.exists():
                backup_file = backup_path / "files" / rel
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target_path, backup_file)
                entry["backup"] = str(backup_file.relative_to(backup_path))
            manifest["files"].append(entry)

            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged_path, target_path)
            applied.append(rel)
        write_json(backup_path / "manifest.json", manifest)
    except Exception:
        restore_from_manifest(backup_path / "manifest.json", backup_path, quiet=True)
        raise

    data["status"] = "applied"
    data["applied_at"] = now()
    data["applied_files"] = applied
    data["backup_dir"] = str(backup_path)
    write_json(proposal_file, data)

    verification = None
    if not args.skip_verify:
        verification = run_verification()
        data["last_verification"] = verification
        if not verification["ok"]:
            data["status"] = "verify-failed"
        write_json(proposal_file, data)

    memory_candidate = None
    if args.memory_candidate:
        memory_candidate = write_memory_candidate(proposal_path, lesson=args.lesson)

    print_json(
        {
            "ok": verification["ok"] if verification else True,
            "proposal": data["id"],
            "applied_files": applied,
            "verification": verification,
            "memory_candidate": memory_candidate,
        }
    )
    return 0 if not verification or verification["ok"] else 1


def command_verify(proposal_id: str | None, json_output: bool = False) -> int:
    result = run_verification()
    if proposal_id:
        proposal_path = resolve_proposal(proposal_id)
        proposal_file = proposal_path / "proposal.json"
        data = read_json(proposal_file)
        data["last_verification"] = result
        if data.get("status") == "applied" and not result["ok"]:
            data["status"] = "verify-failed"
        write_json(proposal_file, data)

    if json_output:
        print_json({"ok": result["ok"], "verification": result})
    else:
        print("DreamSeed verification " + ("passed" if result["ok"] else "failed"))
        if result["stdout"].strip():
            print(result["stdout"].strip())
        if result["stderr"].strip():
            print(result["stderr"].strip(), file=sys.stderr)
    return 0 if result["ok"] else 1


def command_score(value: str, json_output: bool = False) -> int:
    proposal_path = resolve_proposal(value)
    data = read_json(proposal_path / "proposal.json")
    score = score_proposal(proposal_path, data)
    if json_output:
        print_json({"ok": True, "proposal": data.get("id") or proposal_path.name, "score": score})
    else:
        print("DreamSeed self-evolution score")
        print(f"Proposal: {data.get('id') or proposal_path.name}")
        print(f"Score: {score['score']} risk={score['risk']} status={score['status']}")
        for reason in score["reasons"]:
            print(f"  - {reason}")
    return 0


def command_archive_failure(value: str, reason: str = "", json_output: bool = False) -> int:
    proposal_path = resolve_proposal(value)
    proposal_file = proposal_path / "proposal.json"
    data = read_json(proposal_file)
    archive_dir = ROOT / "logs" / "self-evolve-failures" / str(data.get("id") or proposal_path.name)
    archive_dir.mkdir(parents=True, exist_ok=True)
    data["status"] = "archived-failure"
    data["archived_at"] = now()
    data["archive_reason"] = reason or "failure archived for review"
    data["archive_dir"] = str(archive_dir)
    write_json(proposal_file, data)
    write_json(archive_dir / "proposal.json", data)
    review = proposal_path / "REVIEW.md"
    if review.exists():
        shutil.copy2(review, archive_dir / "REVIEW.md")
    result = {"ok": True, "proposal": data.get("id"), "archiveDir": str(archive_dir), "reason": data["archive_reason"]}
    if json_output:
        print_json(result)
    else:
        print("Archived failed proposal: " + str(data.get("id")))
        print("Archive: " + str(archive_dir))
    return 0


def command_rollback(args: argparse.Namespace) -> int:
    if not args.yes:
        raise SystemExit("Refusing to restore files without --yes")
    proposal_path = resolve_proposal(args.id)
    proposal_file = proposal_path / "proposal.json"
    data = read_json(proposal_file)
    backup_path = BACKUP_DIR / str(data["id"])
    manifest_file = backup_path / "manifest.json"
    if not manifest_file.exists():
        raise SystemExit(f"Rollback manifest not found: {manifest_file}")

    restored = restore_from_manifest(manifest_file, backup_path)
    data["status"] = "rolled-back"
    data["rolled_back_at"] = now()
    data["rolled_back_files"] = restored
    write_json(proposal_file, data)
    print_json({"ok": True, "proposal": data["id"], "rolled_back_files": restored})
    return 0


def run_verification() -> dict[str, Any]:
    audit_script = ROOT / "scripts" / "dreamseed-audit.ps1"
    if not audit_script.exists():
        return {
            "ok": False,
            "command": "",
            "stdout": "",
            "stderr": f"Missing audit script: {audit_script}",
            "exit_code": 1,
            "verified_at": now(),
        }

    shell = shutil.which("powershell") or shutil.which("pwsh")
    if not shell:
        return {
            "ok": False,
            "command": "",
            "stdout": "",
            "stderr": "PowerShell is required for scripts/dreamseed-audit.ps1",
            "exit_code": 1,
            "verified_at": now(),
        }

    commands = [
        [sys.executable, str(ROOT / "scripts" / "brand_audit.py"), "scan", "--root", str(ROOT), "--strict", "--json"],
        [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(audit_script)],
    ]
    outputs = []
    ok = True
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        outputs.append(
            {
                "command": " ".join(command),
                "ok": completed.returncode == 0,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
        ok = ok and completed.returncode == 0
    return {
        "ok": ok,
        "command": " && ".join(item["command"] for item in outputs),
        "stdout": "\n".join(item["stdout"] for item in outputs),
        "stderr": "\n".join(item["stderr"] for item in outputs),
        "exit_code": 0 if ok else 1,
        "steps": outputs,
        "verified_at": now(),
    }


def score_proposal(proposal_path: Path, data: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    score = 0.35
    staged = staged_files(proposal_path)
    risk = str(data.get("risk") or "medium")
    status = str(data.get("status") or "unknown")
    if data.get("problem"):
        score += 0.1
        reasons.append("has problem statement")
    else:
        reasons.append("missing problem statement")
    if data.get("evidence"):
        score += 0.12
        reasons.append("has evidence")
    else:
        reasons.append("missing evidence")
    if data.get("proposed_changes"):
        score += 0.1
        reasons.append("has proposed changes")
    if data.get("verification_plan"):
        score += 0.1
        reasons.append("has verification plan")
    if data.get("rollback_plan"):
        score += 0.08
        reasons.append("has rollback plan")
    if staged:
        score += 0.1
        reasons.append(f"has staged files: {len(staged)}")
    else:
        reasons.append("no staged files yet")
    if risk == "high":
        score -= 0.12
        reasons.append("high risk requires explicit approval")
    if (data.get("last_verification") or {}).get("ok"):
        score += 0.15
        reasons.append("last verification passed")
    if status == "verify-failed":
        score -= 0.15
        reasons.append("last verification failed")
    return {
        "score": round(max(0.0, min(1.0, score)), 3),
        "risk": risk,
        "status": status,
        "stagedFiles": len(staged),
        "reasons": reasons,
        "policy": "proposal-first; apply requires --yes and verification gates",
    }


def write_memory_candidate(proposal_path: Path, lesson: str = "") -> dict[str, Any]:
    data = read_json(proposal_path / "proposal.json")
    MEMORY_CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    candidate_id = "memory-candidate-self-evolve-" + str(data["id"])
    summary = "DreamSeed self-evolution: " + str(data.get("title") or data["id"])
    text_parts = [
        summary,
        "Problem: " + str(data.get("problem") or "").strip(),
        "Change: " + "; ".join(data.get("proposed_changes") or []),
        "Verification: " + str((data.get("last_verification") or {}).get("ok", "not run")),
    ]
    if lesson:
        text_parts.append("Durable lesson: " + lesson.strip())
    candidate = {
        "id": candidate_id,
        "created_at": now(),
        "source": "dreamseed-self-evolve",
        "score": 0.72 if lesson else 0.62,
        "summary": summary,
        "text": "\n".join(part for part in text_parts if part.strip()),
        "promotion_policy": "memory_review.py apply -> reviewed/ -> memory_promote.py promote-reviewed only",
        "proposal_id": data["id"],
    }
    path = MEMORY_CANDIDATES_DIR / f"{candidate_id}.json"
    write_json(path, candidate)
    return {"id": candidate_id, "path": str(path)}


def list_proposal_paths() -> list[Path]:
    if not PROPOSAL_DIR.exists():
        return []
    return sorted(
        [p for p in PROPOSAL_DIR.iterdir() if (p / "proposal.json").is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def resolve_proposal(value: str) -> Path:
    direct = PROPOSAL_DIR / value
    if (direct / "proposal.json").is_file():
        return direct
    matches = [p for p in list_proposal_paths() if value in p.name]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit(f"Proposal not found: {value}")
    raise SystemExit(f"Proposal id is ambiguous: {value}")


def staged_files(proposal_path: Path) -> list[Path]:
    stage = proposal_path / "files"
    if not stage.exists():
        return []
    return sorted(p for p in stage.rglob("*") if p.is_file())


def proposal_summary(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data.get("id") or path.name,
        "title": data.get("title") or "",
        "status": data.get("status") or "unknown",
        "risk": data.get("risk") or "unknown",
        "created_at": data.get("created_at"),
        "staged_files": len(staged_files(path)),
        "path": str(path),
    }


def normalize_rel_path(value: str) -> str:
    cleaned = str(value).strip().replace("\\", "/")
    if not cleaned:
        raise SystemExit("Empty path is not allowed")
    path = Path(cleaned)
    if path.is_absolute() or ":" in cleaned.split("/", 1)[0]:
        raise SystemExit(f"Absolute paths are not allowed in proposals: {value}")
    parts = [part for part in cleaned.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        raise SystemExit(f"Parent traversal is not allowed in proposals: {value}")
    return "/".join(parts)


def validate_target_rel(rel: str) -> None:
    parts = rel.split("/")
    root_name = parts[0]
    if root_name in DENIED_ROOTS:
        raise SystemExit(f"Refusing to stage private or generated path: {rel}")
    if root_name not in ALLOWED_ROOTS:
        raise SystemExit(f"Path is outside the self-evolution allowlist: {rel}")
    if rel.endswith("providers.local.json") or "/providers.local.json" in rel:
        raise SystemExit(f"Provider secrets are not valid self-evolution targets: {rel}")
    target = (ROOT / rel).resolve()
    if not str(target).lower().startswith(str(ROOT.resolve()).lower()):
        raise SystemExit(f"Resolved path escapes repository root: {rel}")


def validate_publishable_text(rel: str, text: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise SystemExit(f"Refusing to apply staged file with possible secret: {rel}")
    legacy_namespace = "." + "claude"
    if legacy_namespace in text:
        raise SystemExit(f"Refusing to apply publish-layer legacy namespace literal in: {rel}")


def restore_from_manifest(manifest_file: Path, backup_path: Path, quiet: bool = False) -> list[str]:
    if not manifest_file.exists():
        if quiet:
            return []
        raise SystemExit(f"Rollback manifest not found: {manifest_file}")
    manifest = read_json(manifest_file)
    restored = []
    for entry in reversed(manifest.get("files") or []):
        rel = normalize_rel_path(entry["path"])
        target = ROOT / rel
        if entry.get("existed"):
            backup_rel = entry.get("backup")
            if not backup_rel:
                raise SystemExit(f"Missing backup entry for {rel}")
            backup_file = backup_path / backup_rel
            if not backup_file.exists():
                raise SystemExit(f"Missing backup file for {rel}: {backup_file}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_file, target)
        else:
            if target.exists():
                target.unlink()
        restored.append(rel)
    return restored


def render_review(data: dict[str, Any]) -> str:
    lines = [
        "# Self-Evolution Review",
        "",
        f"ID: {data['id']}",
        f"Title: {data['title']}",
        f"Risk: {data['risk']}",
        "",
        "## Problem",
        data.get("problem") or "(not supplied)",
        "",
        "## Evidence",
    ]
    lines.extend("- " + item for item in (data.get("evidence") or ["(not supplied)"]))
    lines.extend(["", "## Proposed Changes"])
    lines.extend("- " + item for item in (data.get("proposed_changes") or ["(not supplied)"]))
    lines.extend(["", "## Target Files"])
    lines.extend("- " + item for item in (data.get("target_files") or ["(none yet)"]))
    lines.extend(["", "## How To Apply"])
    lines.append("Stage replacement files under `files/<relative-path>`.")
    lines.append(f"Run `dreamseed evolve apply {data['id']} --yes`.")
    lines.extend(["", "## Verification"])
    lines.extend("- " + item for item in (data.get("verification_plan") or []))
    lines.extend(["", "## Rollback"])
    lines.extend("- " + item for item in (data.get("rollback_plan") or []))
    return "\n".join(lines) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
