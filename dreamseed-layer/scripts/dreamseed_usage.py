from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize DreamSeed provider and legacy usage without printing secrets.")
    sub = parser.add_subparsers(dest="command")
    summary = sub.add_parser("summary", help="Show usage summary")
    summary.add_argument("--root", default=str(ROOT))
    summary.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.command:
        args.command = "summary"
        args.root = str(ROOT)
        args.json = False

    if args.command == "summary":
        report = build_summary(Path(args.root).resolve())
        if args.json:
            print_json(report)
        else:
            print_table(report)
        return 0 if report["ok"] else 1
    return 2


def build_summary(root: Path) -> dict[str, Any]:
    provider = provider_summary(root)
    history = legacy_history_summary(root)
    usage = legacy_usage_rollups(root)
    return {
        "ok": True,
        "root": str(root),
        "provider": provider,
        "legacyHistory": history,
        "usage": usage,
        "notes": [
            "Secrets are redacted and provider API keys are not read into output.",
            "Usage data is best-effort from local provider and legacy archives.",
        ],
    }


def provider_summary(root: Path) -> dict[str, Any]:
    paths = [
        root / "config" / "providers.local.json",
        root / ".dreamseed" / "providers.local.json",
        root / "config" / "providers.example.json",
    ]
    for path in paths:
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        providers = data.get("providers") or {}
        active = data.get("activeProvider") or next(iter(providers), None)
        active_provider = providers.get(active, {}) if active else {}
        return {
            "configPath": str(path),
            "activeProvider": active,
            "providerCount": len(providers),
            "activeModel": active_provider.get("model"),
            "activeType": active_provider.get("type"),
            "activeBaseUrl": redact_url(active_provider.get("baseUrl", "")),
            "auth": describe_auth(active_provider),
        }
    return {"configPath": None, "activeProvider": None, "providerCount": 0}


def legacy_history_summary(root: Path) -> dict[str, Any]:
    manifest = read_json(root / "legacy-history" / "claude-code" / "manifest.json")
    if not isinstance(manifest, dict):
        return {"present": False}
    return {
        "present": True,
        "importedAt": manifest.get("imported_at"),
        "recordCount": manifest.get("record_count", 0),
        "sessionCount": manifest.get("session_count", 0),
        "projectCount": manifest.get("project_count", 0),
        "policy": manifest.get("policy"),
    }


def legacy_usage_rollups(root: Path) -> dict[str, Any]:
    rollup_path = root / "legacy-history" / "claude-code" / "raw" / "cc-switch" / "usage_daily_rollups.json"
    data = read_json(rollup_path)
    if data is None:
        return {"present": False, "path": str(rollup_path)}

    rows = flatten_usage_rows(data)
    by_model: dict[str, dict[str, Any]] = {}
    by_date: dict[str, int] = defaultdict(int)
    for row in rows:
        model = str(row.get("model") or row.get("provider") or "unknown")
        date = str(row.get("date") or row.get("day") or row.get("created_at") or "unknown")[:10]
        count = numeric_count(row)
        model_key = model.lower()
        if model_key not in by_model:
            by_model[model_key] = {"name": model, "count": 0}
        by_model[model_key]["count"] += count
        by_date[date] += count
    return {
        "present": True,
        "path": str(rollup_path),
        "rows": len(rows),
        "byModel": sorted(by_model.values(), key=lambda item: str(item["name"]).lower())[:20],
        "byDate": [{"date": key, "count": value} for key, value in sorted(by_date.items())[-30:]],
    }


def flatten_usage_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("rows", "items", "usage", "daily", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        rows: list[dict[str, Any]] = []
        for key, value in data.items():
            if isinstance(value, dict):
                item = {"date": key, **value}
                rows.append(item)
        return rows
    return []


def numeric_count(row: dict[str, Any]) -> int:
    for key in ("requests", "count", "calls", "total_requests", "input_tokens", "tokens"):
        value = row.get(key)
        if isinstance(value, (int, float)):
            return int(value)
    return 1


def describe_auth(provider: dict[str, Any]) -> str:
    if provider.get("apiKeyEnv"):
        return f"env:{provider['apiKeyEnv']}"
    if provider.get("apiKey"):
        return "inline:redacted"
    return "none"


def redact_url(url: str) -> str:
    if not url:
        return ""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return "<invalid-url>"


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def print_table(report: dict[str, Any]) -> None:
    provider = report["provider"]
    history = report["legacyHistory"]
    usage = report["usage"]
    print("DreamSeed usage summary")
    print(f"Provider: {provider.get('activeProvider') or '<none>'} model={provider.get('activeModel') or '<none>'} auth={provider.get('auth') or '<none>'}")
    print(f"Legacy history: sessions={history.get('sessionCount', 0)} records={history.get('recordCount', 0)} projects={history.get('projectCount', 0)}")
    print(f"Legacy usage rows: {usage.get('rows', 0) if usage.get('present') else 0}")
    if usage.get("byModel"):
        print("Usage by model/provider:")
        for item in usage["byModel"]:
            print(f"  - {item['name']}: {item['count']}")


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
