from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HIGH_RISK = {"browser", "desktop", "network-write", "filesystem-write", "credentialed"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and manage DreamSeed MCP registry.")
    sub = parser.add_subparsers(dest="command")

    for name in ("list", "candidates", "smoke"):
        p = sub.add_parser(name)
        p.add_argument("--root", default=str(ROOT))
        p.add_argument("--json", action="store_true")

    inspect = sub.add_parser("inspect")
    inspect.add_argument("name")
    inspect.add_argument("--root", default=str(ROOT))
    inspect.add_argument("--json", action="store_true")

    enable = sub.add_parser("enable")
    enable.add_argument("name")
    enable.add_argument("--root", default=str(ROOT))
    enable.add_argument("--yes", action="store_true")
    enable.add_argument("--allow-high-risk", action="store_true")
    enable.add_argument("--json", action="store_true")

    disable = sub.add_parser("disable")
    disable.add_argument("name")
    disable.add_argument("--root", default=str(ROOT))
    disable.add_argument("--yes", action="store_true")
    disable.add_argument("--json", action="store_true")

    test = sub.add_parser("test")
    test.add_argument("name")
    test.add_argument("--root", default=str(ROOT))
    test.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if not args.command:
        args.command = "smoke"
        args.root = str(ROOT)
        args.json = False

    root = Path(args.root).resolve()
    if args.command == "list":
        output = build_report(root)
    elif args.command == "candidates":
        output = list_candidates(root)
    elif args.command == "inspect":
        output = inspect_entry(root, args.name)
    elif args.command == "enable":
        output = enable_entry(root, args.name, yes=args.yes, allow_high_risk=args.allow_high_risk)
    elif args.command == "disable":
        output = disable_entry(root, args.name, yes=args.yes)
    elif args.command == "test":
        output = test_entry(root, args.name)
    elif args.command == "smoke":
        report = build_report(root)
        output = {**report, "ok": len(report["failures"]) == 0}
    else:
        return 2

    if getattr(args, "json", False):
        print_json(output)
    else:
        print_table(output, command=args.command)
    return 0 if output.get("ok", True) else 1


def registry_path(root: Path) -> Path:
    return root / "config" / "mcp.registry.json"


def config_path(root: Path) -> Path:
    return root / ".mcp.json"


def audit_path(root: Path) -> Path:
    return root / "logs" / "mcp-audit.log"


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_report(root: Path) -> dict[str, Any]:
    config = read_json(config_path(root)) or {}
    registry = read_json(registry_path(root)) or {}
    config_servers = config.get("mcpServers") or {}
    registry_servers = registry.get("servers") or {}
    candidates = registry.get("candidates") or {}
    failures: list[str] = []
    warnings: list[str] = []
    servers: list[dict[str, Any]] = []

    for name, server in sorted(config_servers.items()):
        registered = registry_servers.get(name)
        if not registered:
            warnings.append(f"Configured MCP server is missing from registry: {name}")
        command = str(server.get("command") or "")
        command_found = command_exists(command)
        if not command:
            failures.append(f"MCP server has no command: {name}")
        servers.append(server_summary(name, server, registered, configured=True, command_found=command_found))

    for name in sorted(set(registry_servers) - set(config_servers)):
        registered = registry_servers[name]
        if registered.get("defaultEnabled"):
            failures.append(f"Default registry MCP server is not configured: {name}")
        servers.append(server_summary(name, {}, registered, configured=False, command_found=None))

    for name, candidate in sorted(candidates.items()):
        if candidate.get("defaultState") == "enabled":
            failures.append(f"MCP candidate must not default to enabled: {name}")
        if not candidate.get("acceptance"):
            warnings.append(f"MCP candidate has no acceptance checks: {name}")

    return {
        "ok": len(failures) == 0,
        "root": str(root),
        "registryPath": str(registry_path(root)),
        "configPath": str(config_path(root)),
        "servers": servers,
        "candidateCount": len(candidates),
        "failures": failures,
        "warnings": warnings,
        "policy": registry.get("policy", {}),
        "riskTags": registry.get("riskTags", []),
    }


def server_summary(name: str, server: dict[str, Any], registered: Any, configured: bool, command_found: bool | None) -> dict[str, Any]:
    registered = registered if isinstance(registered, dict) else {}
    command = str(server.get("command") or registered.get("command") or "")
    risk = registered.get("risk", [])
    return {
        "name": name,
        "configured": configured,
        "registered": bool(registered),
        "command": command,
        "commandFound": command_found,
        "risk": risk,
        "highRisk": bool(set(risk) & HIGH_RISK),
        "network": registered.get("network"),
        "readWrite": registered.get("readWrite"),
        "outputLimitChars": registered.get("outputLimitChars"),
        "secretSource": registered.get("secretSource", "none"),
    }


def command_exists(command: str) -> bool:
    if not command:
        return False
    return bool(Path(command).exists() if "\\" in command or "/" in command else shutil.which(command))


def list_candidates(root: Path) -> dict[str, Any]:
    registry = read_json(registry_path(root)) or {}
    candidates = registry.get("candidates") or {}
    return {
        "ok": True,
        "candidates": [
            {
                "name": name,
                "source": data.get("source"),
                "risk": data.get("risk", []),
                "defaultState": data.get("defaultState", "candidate"),
                "network": data.get("network"),
                "readWrite": data.get("readWrite"),
                "acceptance": data.get("acceptance", []),
            }
            for name, data in sorted(candidates.items())
        ],
    }


def inspect_entry(root: Path, name: str) -> dict[str, Any]:
    registry = read_json(registry_path(root)) or {}
    config = read_json(config_path(root)) or {}
    entry = (registry.get("servers") or {}).get(name)
    location = "servers"
    if not entry:
        entry = (registry.get("candidates") or {}).get(name)
        location = "candidates"
    if not entry:
        return {"ok": False, "error": f"MCP entry not found: {name}"}
    return {
        "ok": True,
        "name": name,
        "location": location,
        "configured": name in (config.get("mcpServers") or {}),
        "entry": redact_entry(entry),
    }


def enable_entry(root: Path, name: str, yes: bool, allow_high_risk: bool) -> dict[str, Any]:
    if not yes:
        return {"ok": False, "error": "Refusing to enable MCP without --yes"}
    registry = read_json(registry_path(root)) or {}
    candidates = registry.get("candidates") or {}
    servers = registry.setdefault("servers", {})
    entry = servers.get(name) or candidates.get(name)
    if not entry:
        return {"ok": False, "error": f"MCP entry not found: {name}"}
    risks = set(entry.get("risk") or [])
    if risks & HIGH_RISK and name not in servers and not allow_high_risk:
        return {"ok": False, "error": f"High-risk MCP candidate requires --allow-high-risk: {name}", "risk": sorted(risks)}

    config = read_json(config_path(root)) or {"mcpServers": {}}
    config.setdefault("mcpServers", {})[name] = mcp_config_from_entry(entry)
    servers[name] = normalize_server_entry(entry)
    if name in candidates:
        candidates[name]["defaultState"] = "disabled"
    write_json(config_path(root), config)
    write_json(registry_path(root), registry)
    append_audit(root, "enable", name, {"risk": sorted(risks), "allowHighRisk": allow_high_risk})
    return {"ok": True, "status": "enabled", "name": name, "risk": sorted(risks)}


def disable_entry(root: Path, name: str, yes: bool) -> dict[str, Any]:
    if not yes:
        return {"ok": False, "error": "Refusing to disable MCP without --yes"}
    config = read_json(config_path(root)) or {"mcpServers": {}}
    existed = bool((config.get("mcpServers") or {}).pop(name, None))
    write_json(config_path(root), config)
    append_audit(root, "disable", name, {"existed": existed})
    return {"ok": True, "status": "disabled", "name": name, "existed": existed}


def test_entry(root: Path, name: str) -> dict[str, Any]:
    inspected = inspect_entry(root, name)
    if not inspected.get("ok"):
        return inspected
    entry = inspected["entry"]
    command = str(entry.get("command") or "")
    checks = {
        "schema": bool(entry.get("source") and entry.get("risk") is not None),
        "commandPresent": bool(command),
        "commandFound": command_exists(command),
        "secretsNotInline": not has_inline_secret(entry),
        "outputLimit": isinstance(entry.get("outputLimitChars"), int) and entry.get("outputLimitChars") > 0,
    }
    return {"ok": all(checks.values()), "name": name, "checks": checks, "configured": inspected.get("configured")}


def mcp_config_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    config = {
        "type": entry.get("type", "stdio"),
        "command": entry.get("command"),
        "args": entry.get("args", []),
    }
    if entry.get("env"):
        config["env"] = entry["env"]
    return config


def normalize_server_entry(entry: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(entry)
    normalized["defaultEnabled"] = True
    normalized.pop("defaultState", None)
    return normalized


def has_inline_secret(data: Any) -> bool:
    text = json.dumps(data, ensure_ascii=False)
    lowered = text.lower()
    return any(marker in lowered for marker in ("api_key", "apikey", "password", "bearer ")) and "env" not in lowered


def redact_entry(entry: dict[str, Any]) -> dict[str, Any]:
    redacted = json.loads(json.dumps(entry))
    for key in list(redacted):
        if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower():
            redacted[key] = "<redacted>"
    return redacted


def append_audit(root: Path, action: str, name: str, meta: dict[str, Any]) -> None:
    path = audit_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"at": datetime.now(timezone.utc).isoformat(), "action": action, "name": name, "meta": meta}
    path.write_text("", encoding="utf-8") if not path.exists() else None
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def print_table(report: dict[str, Any], command: str) -> None:
    if command == "candidates":
        print("DreamSeed MCP candidates")
        for candidate in report.get("candidates", []):
            print(f"  - {candidate['name']} state={candidate['defaultState']} risk={','.join(candidate.get('risk') or []) or 'none'}")
        return
    if command == "inspect":
        print("DreamSeed MCP inspect")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print("DreamSeed MCP doctor")
    for server in report.get("servers", []):
        print(
            f"  - {server['name']} configured={server.get('configured')} registered={server.get('registered')} "
            f"risk={','.join(server.get('risk') or []) or 'none'}"
        )
    for warning in report.get("warnings", []):
        print(f"Warning: {warning}")
    for failure in report.get("failures", []):
        print(f"Failure: {failure}")
    if "status" in report:
        print(f"{report['name']}: {report['status']}")


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
