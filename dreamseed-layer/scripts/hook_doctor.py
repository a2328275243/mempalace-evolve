from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit DreamSeed hooks for reliability and memory safety.")
    sub = parser.add_subparsers(dest="command")
    audit = sub.add_parser("audit", help="Audit configured hooks")
    audit.add_argument("--root", default=str(ROOT))
    audit.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.command:
        args.command = "audit"
        args.root = str(ROOT)
        args.json = False

    report = audit_hooks(Path(args.root).resolve())
    if args.json:
        print_json(report)
    else:
        print_table(report)
    return 0 if report["ok"] else 1


def audit_hooks(root: Path) -> dict[str, Any]:
    settings_path = root / ".dreamseed" / "settings.json"
    approval_policy_path = root / "config" / "approval.policy.json"
    settings = read_json(settings_path)
    approval_policy = read_json(approval_policy_path)
    failures: list[str] = []
    warnings: list[str] = []
    hooks_report: list[dict[str, Any]] = []
    if not isinstance(settings, dict):
        return {"ok": False, "root": str(root), "failures": ["settings.json is invalid or missing"], "warnings": [], "hooks": []}

    hooks = settings.get("hooks") or {}
    for event_name, groups in hooks.items():
        for group_index, group in enumerate(groups if isinstance(groups, list) else []):
            for hook_index, hook in enumerate(group.get("hooks", []) if isinstance(group, dict) else []):
                command = str(hook.get("command") or "")
                timeout = hook.get("timeout")
                shell = hook.get("shell")
                scripts = referenced_scripts(command, root)
                missing_scripts = [str(path) for path in scripts if not path.exists()]
                direct_memory_write = looks_like_direct_memory_write(command)
                item = {
                    "event": event_name,
                    "group": group_index,
                    "hook": hook_index,
                    "type": hook.get("type"),
                    "shell": shell,
                    "timeout": timeout,
                    "async": hook.get("async"),
                    "statusMessage": hook.get("statusMessage"),
                    "referencedScripts": [str(path) for path in scripts],
                    "missingScripts": missing_scripts,
                    "directMemoryWrite": direct_memory_write,
                }
                hooks_report.append(item)
                if not command:
                    failures.append(f"{event_name}[{group_index}].hooks[{hook_index}] has no command")
                if missing_scripts:
                    failures.append(f"{event_name}[{group_index}].hooks[{hook_index}] references missing script: {', '.join(missing_scripts)}")
                if not isinstance(timeout, int) or timeout <= 0:
                    warnings.append(f"{event_name}[{group_index}].hooks[{hook_index}] has no positive timeout")
                if shell not in {"powershell", "bash", "sh", "cmd", None}:
                    warnings.append(f"{event_name}[{group_index}].hooks[{hook_index}] has unusual shell: {shell}")
                if direct_memory_write:
                    failures.append(f"{event_name}[{group_index}].hooks[{hook_index}] appears to write long-term memory directly")

    if "UserPromptSubmit" in hooks:
        warnings.append("UserPromptSubmit hook is configured; keep it disabled unless it has an explicit smoke test.")
    permission_hooks = hooks.get("PermissionRequest") or []
    permission_commands = [
        str(hook.get("command") or "")
        for group in permission_hooks if isinstance(group, dict)
        for hook in group.get("hooks", []) if isinstance(hook, dict)
    ]
    approval_hook_wired = any("dreamseed-approval-gate.ps1" in command or "approval_gate.py" in command for command in permission_commands)
    if not approval_hook_wired:
        failures.append("PermissionRequest hook is not wired to DreamSeed approval gate")
    if not isinstance(approval_policy, dict):
        failures.append("config/approval.policy.json is invalid or missing")
    elif (approval_policy.get("mode") != "auto-review") or ("critical" not in (approval_policy.get("decisions") or {})):
        failures.append("approval policy must define auto-review mode and critical decision handling")

    return {
        "ok": len(failures) == 0,
        "root": str(root),
        "settingsPath": str(settings_path),
        "hooks": hooks_report,
        "failures": failures,
        "warnings": warnings,
        "tracePolicy": {
            "directory": "logs/hook-trace",
            "publish": False,
            "contents": "summary-only; no prompts, no secrets",
        },
        "approvalGate": {
            "enabled": approval_hook_wired,
            "policyPath": str(approval_policy_path),
            "mode": approval_policy.get("mode") if isinstance(approval_policy, dict) else None,
            "permissionHookCount": len(permission_commands),
        },
    }


def referenced_scripts(command: str, root: Path) -> list[Path]:
    scripts: list[Path] = []
    expanded = command.replace("$env:DREAMSEED_ROOT", str(root))
    for match in re.finditer(r"([A-Za-z]:\\[^\"'\s]+scripts\\[^\"'\s]+|[^\"'\s]+scripts\\[^\"'\s]+)", expanded):
        raw = match.group(1).rstrip(";")
        scripts.append(Path(raw))
    return scripts


def looks_like_direct_memory_write(command: str) -> bool:
    lowered = command.lower()
    if "dreamseed-memory-bridge" in lowered or "memory_review.py" in lowered or "memory_promote.py" in lowered:
        return False
    return "mempalace" in lowered and any(term in lowered for term in ["remember", "add_fact", "write", "promote"])


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def print_table(report: dict[str, Any]) -> None:
    print("DreamSeed hook doctor")
    for hook in report.get("hooks", []):
        print(
            f"  - {hook['event']} shell={hook.get('shell')} timeout={hook.get('timeout')} "
            f"async={hook.get('async')} missing={len(hook.get('missingScripts') or [])}"
        )
    for warning in report.get("warnings", []):
        print(f"Warning: {warning}")
    for failure in report.get("failures", []):
        print(f"Failure: {failure}")


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
