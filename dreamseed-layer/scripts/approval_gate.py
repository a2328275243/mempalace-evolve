from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "approval.policy.json"
RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
EXPECTED_MODE = "auto-review"
REDACT_RE = re.compile(
    r"sk-[A-Za-z0-9_-]{20,}|(?i:(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]{8,})"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="DreamSeed risk approval gate")
    sub = parser.add_subparsers(dest="action")

    hook = sub.add_parser("hook", help="Run as a PermissionRequest hook")
    hook.add_argument("--hook-input", default="")

    check = sub.add_parser("check", help="Classify a tool request")
    check.add_argument("--tool", default="Bash")
    check.add_argument("--command", default="")
    check.add_argument("--path", default="")
    check.add_argument("--input-json", default="")
    check.add_argument("--json", action="store_true")

    status = sub.add_parser("status", help="Show approval policy status")
    status.add_argument("--json", action="store_true")

    audit = sub.add_parser("audit", help="Audit policy and settings integration")
    audit.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if not args.action:
        args.action = "status"
        args.json = False

    policy = load_policy()
    if args.action == "hook":
        return run_hook(policy, args.hook_input)
    if args.action == "check":
        payload = check_request(policy, args)
        print_output(payload, args.json)
        return 0
    if args.action == "status":
        payload = status_report(policy)
        print_output(payload, args.json)
        return 0 if payload["ok"] else 1
    if args.action == "audit":
        payload = audit_report(policy)
        print_output(payload, args.json)
        return 0 if payload["ok"] else 1
    return 2


def load_policy() -> dict[str, Any]:
    try:
        data = json.loads(POLICY_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"ok": False, "error": str(exc), "path": str(POLICY_PATH)}
    data.setdefault("ok", True)
    return data


def run_hook(policy: dict[str, Any], hook_input_path: str = "") -> int:
    payload = read_hook_input(hook_input_path)
    result = classify_hook_payload(policy, payload)
    write_audit_log(policy, result)

    if result["decision"] == "allow":
        updated_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
        print_json(
            {
                "suppressOutput": True,
                "hookSpecificOutput": {
                    "hookEventName": "PermissionRequest",
                    "decision": {"behavior": "allow", "updatedInput": updated_input},
                },
            }
        )
        return 0

    if result["decision"] == "deny":
        print_json(
            {
                "suppressOutput": True,
                "hookSpecificOutput": {
                    "hookEventName": "PermissionRequest",
                    "decision": {
                        "behavior": "deny",
                        "message": "DreamSeed approval gate blocked this critical-risk action: "
                        + "; ".join(result["reasons"][:3]),
                    },
                },
            }
        )
        return 0

    # No decision means the native permission prompt asks the user.
    print_json({"suppressOutput": True})
    return 0


def read_hook_input(hook_input_path: str = "") -> dict[str, Any]:
    try:
        if hook_input_path:
            text = Path(hook_input_path).read_text(encoding="utf-8-sig")
        else:
            text = sys.stdin.read()
        return json.loads(text) if text.strip() else {}
    except Exception as exc:
        return {"hook_event_name": "PermissionRequest", "tool_name": "unknown", "tool_input": {}, "read_error": str(exc)}


def check_request(policy: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if args.input_json:
        data = json.loads(Path(args.input_json).read_text(encoding="utf-8-sig"))
        if "hook_event_name" in data:
            return classify_hook_payload(policy, data)
        return classify_tool_request(policy, str(data.get("tool_name") or args.tool), data.get("tool_input") or data)

    tool_input: dict[str, Any] = {}
    if args.command:
        tool_input["command"] = args.command
    if args.path:
        tool_input["path"] = args.path
    return classify_tool_request(policy, args.tool, tool_input)


def classify_hook_payload(policy: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return classify_tool_request(policy, str(payload.get("tool_name") or "unknown"), payload.get("tool_input") or {})


def classify_tool_request(policy: dict[str, Any], tool_name: str, tool_input: Any) -> dict[str, Any]:
    tool = normalize_tool(tool_name)
    reasons: list[str] = []
    tags: list[str] = []
    risk = "medium"
    command = extract_command(tool_input)

    if tool.lower() in {"bash", "shell"} and command:
        shell_result = classify_shell_command(policy, command)
        risk = shell_result["risk"]
        reasons.append("shell request classified by command content")
        tags.append("tool-shell")
        reasons.extend(shell_result["reasons"])
        tags.extend(shell_result["tags"])
    elif tool in set(policy.get("lowRiskTools") or []):
        risk = "low"
        reasons.append(f"{tool} is listed as low-risk")
        tags.append("tool-low-risk")
    elif tool in set(policy.get("mediumRiskTools") or []):
        risk = "medium"
        reasons.append(f"{tool} may change files or use network context")
        tags.append("tool-medium-risk")
    elif tool in set(policy.get("highRiskTools") or []):
        risk = "high"
        reasons.append(f"{tool} can execute high-impact actions")
        tags.append("tool-high-risk")
    else:
        risk = "medium"
        reasons.append(f"{tool} is not explicitly low-risk")
        tags.append("tool-unknown")

    path_result = classify_paths(policy, extract_paths(tool_input))
    risk = max_risk(risk, path_result["risk"])
    reasons.extend(path_result["reasons"])
    tags.extend(path_result["tags"])

    decision = decision_for_risk(policy, risk)
    return {
        "ok": True,
        "tool": tool,
        "risk": risk,
        "decision": decision,
        "tags": sorted(set(tags)),
        "reasons": reasons or ["no special risk signal"],
        "commandPreview": redact(command)[:240] if command else "",
    }


def classify_shell_command(policy: dict[str, Any], command: str) -> dict[str, Any]:
    reasons: list[str] = []
    tags: list[str] = []
    stripped = command.strip()
    risk = "medium"

    if any_matches(policy.get("denyShellPatterns") or [], stripped):
        return {
            "risk": "critical",
            "reasons": ["command matched a critical deny pattern"],
            "tags": ["shell-critical"],
        }

    if any_matches(policy.get("askShellPatterns") or [], stripped):
        risk = "high"
        reasons.append("command matched a risky shell pattern")
        tags.append("shell-risk")
    elif any_matches(policy.get("safeShellPatterns") or [], stripped):
        risk = "low"
        reasons.append("command matched a read-only shell pattern")
        tags.append("shell-readonly")
    else:
        risk = "medium"
        reasons.append("shell command is not in the read-only allowlist")
        tags.append("shell-unclassified")

    if has_shell_control_operator(stripped):
        risk = max_risk(risk, "medium")
        reasons.append("command contains shell control operators")
        tags.append("shell-compound")

    return {"risk": risk, "reasons": reasons, "tags": tags}


def classify_paths(policy: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    risk = "low"
    reasons: list[str] = []
    tags: list[str] = []
    for raw in paths:
        path = str(raw)
        if any_matches(policy.get("privatePathPatterns") or [], path):
            risk = max_risk(risk, "high")
            reasons.append("path targets private DreamSeed data")
            tags.append("private-path")
        if any_matches(policy.get("systemPathPatterns") or [], path):
            risk = max_risk(risk, "high")
            reasons.append("path targets a system or archived runtime directory")
            tags.append("system-path")
    return {"risk": risk, "reasons": reasons, "tags": tags}


def extract_command(tool_input: Any) -> str:
    if isinstance(tool_input, dict):
        for key in ("command", "cmd", "script", "shell_command"):
            value = tool_input.get(key)
            if isinstance(value, str):
                return value
    return ""


def extract_paths(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in ("path", "file", "dir", "source", "dest")) and isinstance(item, str):
                paths.append(item)
            else:
                paths.extend(extract_paths(item))
    elif isinstance(value, list):
        for item in value:
            paths.extend(extract_paths(item))
    return paths[:50]


def normalize_tool(name: str) -> str:
    aliases = {"shell": "Bash", "bash": "Bash", "read": "Read", "grep": "Grep", "glob": "Glob"}
    raw = str(name or "unknown").strip()
    return aliases.get(raw.lower(), raw)


def any_matches(patterns: list[str], value: str) -> bool:
    return any(re.search(pattern, value) for pattern in patterns)


def has_shell_control_operator(command: str) -> bool:
    return any(token in command for token in ("&&", "||", ";", "|", "`", "$(", ">"))


def max_risk(left: str, right: str) -> str:
    return left if RISK_ORDER.get(left, 1) >= RISK_ORDER.get(right, 1) else right


def decision_for_risk(policy: dict[str, Any], risk: str) -> str:
    decisions = policy.get("decisions") or {}
    return str(decisions.get(risk) or "ask")


def status_report(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(policy.get("ok")),
        "policyPath": str(POLICY_PATH),
        "mode": policy.get("mode"),
        "decisions": policy.get("decisions"),
        "lowRiskTools": policy.get("lowRiskTools", []),
        "log": policy.get("log", {}),
    }


def audit_report(policy: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    settings_path = ROOT / ".dreamseed" / "settings.json"
    settings = read_json(settings_path)

    if not policy.get("ok"):
        failures.append(f"approval policy is invalid: {policy.get('error')}")
    if policy.get("mode") != EXPECTED_MODE:
        failures.append(f"approval policy mode must be {EXPECTED_MODE}")
    for key in ("low", "medium", "high", "critical"):
        if key not in (policy.get("decisions") or {}):
            failures.append(f"approval policy is missing decision for {key}")

    permission_hooks = (((settings or {}).get("hooks") or {}).get("PermissionRequest") or [])
    hook_commands = [
        str(hook.get("command") or "")
        for group in permission_hooks
        for hook in (group.get("hooks", []) if isinstance(group, dict) else [])
        if isinstance(hook, dict)
    ]
    if not any("dreamseed-approval-gate.ps1" in command or "approval_gate.py" in command for command in hook_commands):
        failures.append("PermissionRequest hook is not wired to DreamSeed approval gate")

    samples = [
        ("Read", {"file_path": "README.md"}, "allow"),
        ("Bash", {"command": "git status --short"}, "allow"),
        ("Bash", {"command": "Remove-Item -LiteralPath D:\\data -Recurse -Force"}, "ask"),
        ("Bash", {"command": "shutdown /s /t 0"}, "deny"),
    ]
    sample_results = []
    for tool, tool_input, expected in samples:
        result = classify_tool_request(policy, tool, tool_input)
        sample_results.append(result)
        if result["decision"] != expected:
            failures.append(f"approval sample {tool} expected {expected}, got {result['decision']}")

    return {
        "ok": not failures,
        "policyPath": str(POLICY_PATH),
        "settingsPath": str(settings_path),
        "hookCount": len(hook_commands),
        "failures": failures,
        "warnings": warnings,
        "samples": sample_results,
    }


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def write_audit_log(policy: dict[str, Any], result: dict[str, Any]) -> None:
    log_config = policy.get("log") or {}
    if not log_config.get("enabled", False):
        return
    try:
        directory = ROOT / str(log_config.get("directory") or "logs/approval-gate")
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (datetime.now().strftime("%Y%m%d") + ".jsonl")
        record = {
            "time": datetime.now(timezone.utc).isoformat(),
            "tool": result.get("tool"),
            "risk": result.get("risk"),
            "decision": result.get("decision"),
            "tags": result.get("tags", []),
            "reasons": result.get("reasons", [])[:5],
            "commandPreview": result.get("commandPreview", ""),
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        return


def redact(text: str) -> str:
    return REDACT_RE.sub("<redacted>", text)


def print_output(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print_json(payload)
        return
    if "risk" in payload:
        print(f"DreamSeed approval: decision={payload['decision']} risk={payload['risk']} tool={payload['tool']}")
        for reason in payload.get("reasons", []):
            print(f"  - {reason}")
        return
    print_json(payload)


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
