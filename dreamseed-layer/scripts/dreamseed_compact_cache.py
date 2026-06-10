from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or inspect DreamSeed compact summary cache.")
    sub = parser.add_subparsers(dest="command")
    for name in ("build", "status", "show"):
        p = sub.add_parser(name)
        p.add_argument("--root", default=str(ROOT))
        p.add_argument("--local-root", default=os.environ.get("DREAMSEED_LOCAL_ROOT", r"D:\DreamSeed-Local-Agent"))
        p.add_argument("--max-files", type=int, default=160)
        p.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.command:
        args.command = "status"
        args.root = str(ROOT)
        args.local_root = os.environ.get("DREAMSEED_LOCAL_ROOT", r"D:\DreamSeed-Local-Agent")
        args.max_files = 160
        args.json = False

    root = Path(args.root).resolve()
    local_root = Path(args.local_root)
    if args.command == "build":
        output = build_cache(root, local_root, args.max_files)
    elif args.command == "show":
        output = read_cache(root, local_root)
    else:
        output = cache_status(root, local_root)

    if args.json:
        print(json.dumps(output, ensure_ascii=True, indent=2, default=str))
    else:
        print_table(output, args.command)
    return 0 if output.get("ok", True) else 1


def cache_path(root: Path, local_root: Path) -> Path:
    return local_root / "cache" / "compact-summaries.json"


def native_projects_dir(local_root: Path) -> Path:
    return local_root / "home" / ("." + "claude") / "projects"


def build_cache(root: Path, local_root: Path, max_files: int) -> dict[str, Any]:
    project_dir = native_projects_dir(local_root)
    files = sorted(project_dir.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)[:max_files]
    projects: dict[str, dict[str, Any]] = {}
    for file in files:
        summary = summarize_jsonl(file)
        if not summary:
            continue
        key = summary["cwd"] or file.parent.name
        item = projects.setdefault(
            key,
            {
                "project": key,
                "sessionCount": 0,
                "lastTime": "",
                "recentTitles": [],
                "recentSummaries": [],
            },
        )
        item["sessionCount"] += 1
        if summary["lastTime"] and summary["lastTime"] > item["lastTime"]:
            item["lastTime"] = summary["lastTime"]
        for title in summary["titles"]:
            if title and title not in item["recentTitles"]:
                item["recentTitles"].append(title)
        for text in summary["summaries"]:
            if text and text not in item["recentSummaries"]:
                item["recentSummaries"].append(text)

    payload = {
        "ok": True,
        "kind": "dreamseed-compact-summary-cache",
        "builtAt": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "localRoot": str(local_root),
        "source": str(project_dir),
        "fileCount": len(files),
        "projectCount": len(projects),
        "projects": [
            {
                **value,
                "recentTitles": value["recentTitles"][:8],
                "recentSummaries": value["recentSummaries"][:8],
            }
            for value in sorted(projects.values(), key=lambda item: item.get("lastTime", ""), reverse=True)
        ][:80],
    }
    out = cache_path(root, local_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "kind": payload["kind"],
        "builtAt": payload["builtAt"],
        "root": payload["root"],
        "localRoot": payload["localRoot"],
        "source": payload["source"],
        "fileCount": payload["fileCount"],
        "projectCount": payload["projectCount"],
        "cachePath": str(out),
    }


def summarize_jsonl(path: Path) -> dict[str, Any] | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return None
    titles: list[str] = []
    summaries: list[str] = []
    cwd = ""
    last_time = ""
    for raw in lines[-160:]:
        try:
            item = json.loads(raw)
        except Exception:
            continue
        cwd = cwd or str(item.get("cwd") or item.get("targetCwd") or "")
        timestamp = str(item.get("timestamp") or "")
        if timestamp > last_time:
            last_time = timestamp
        item_type = str(item.get("type") or "")
        if item_type == "custom-title" and item.get("customTitle"):
            titles.append(clean(item.get("customTitle"), 140))
        elif item_type == "last-prompt" and item.get("lastPrompt"):
            titles.append(clean(item.get("lastPrompt"), 140))
        elif item_type == "assistant":
            text = assistant_text(item)
            if text:
                summaries.append(clean(text, 240))
    return {
        "cwd": cwd,
        "lastTime": last_time,
        "titles": dedupe(titles)[:4],
        "summaries": dedupe(summaries)[:4],
    }


def assistant_text(item: dict[str, Any]) -> str:
    message = item.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
    return ""


def clean(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def cache_status(root: Path, local_root: Path) -> dict[str, Any]:
    path = cache_path(root, local_root)
    if not path.exists():
        return {"ok": True, "exists": False, "cachePath": str(path), "recommendation": "Run build before long manual /compact."}
    data = read_cache(root, local_root)
    return {
        "ok": True,
        "exists": True,
        "cachePath": str(path),
        "builtAt": data.get("builtAt"),
        "projectCount": data.get("projectCount", 0),
        "fileCount": data.get("fileCount", 0),
    }


def read_cache(root: Path, local_root: Path) -> dict[str, Any]:
    path = cache_path(root, local_root)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return {"ok": True, "cachePath": str(path), **data}
    except Exception as exc:
        return {"ok": False, "exists": path.exists(), "cachePath": str(path), "error": str(exc)}


def print_table(output: dict[str, Any], command: str) -> None:
    if command == "show":
        print(f"DreamSeed compact cache: {output.get('cachePath')}")
        for item in output.get("projects", [])[:10]:
            title = "; ".join(item.get("recentTitles") or []) or "no title"
            print(f"  - {item.get('project')} sessions={item.get('sessionCount')} {title}")
        return
    print(f"DreamSeed compact cache ok={output.get('ok')} exists={output.get('exists', True)} path={output.get('cachePath')}")
    if output.get("projectCount") is not None:
        print(f"projects={output.get('projectCount')} files={output.get('fileCount')}")


if __name__ == "__main__":
    raise SystemExit(main())
