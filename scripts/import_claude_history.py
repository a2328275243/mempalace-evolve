from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(r"D:\Claude Code\recovery\claude_history_recovery_20260515_1311")
DEFAULT_DEST = Path(os.environ.get("DREAMSEED_LEGACY_HISTORY_DIR") or ROOT / "legacy-history" / "claude-code")
DEFAULT_CANDIDATES = Path(
    os.environ.get("DREAMSEED_MEMORY_CANDIDATES_DIR")
    or os.environ.get("DREAMSEED_CANDIDATE_DIR")
    or ROOT / "memory-candidates"
)

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._~+/=-]{12,}"),
]

RAW_COPY_PATHS = [
    Path("claude") / "history.jsonl",
    Path("claude") / "archived-session-index",
    Path("reconstructed_projects_light"),
    Path("claw") / "sessions",
    Path("cc-switch") / "session_log_sync.json",
    Path("cc-switch") / "usage_daily_rollups.json",
]

NATIVE_HISTORY_BRIDGE_TYPES = {
    "dreamseed-desktop-resume-bridge",
    "dreamseed-legacy-resume-bridge",
}

NATIVE_HISTORY_SKIP_SYSTEM_SUBTYPES = {
    "stop_hook_summary",
    "turn_duration",
    "context_compaction",
}

NATIVE_HISTORY_SKIP_TYPES = {
    "file-history-snapshot",
    "file-history-snapshot-update",
    "last-prompt",
    "custom-title",
    "queue-operation",
}

def main() -> int:
    parser = argparse.ArgumentParser(description="Import legacy Claude Code history into DreamSeed")
    sub = parser.add_subparsers(dest="command", required=True)

    import_parser = sub.add_parser("import", help="Import legacy history into a private DreamSeed archive")
    import_parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    import_parser.add_argument("--dest", default=str(DEFAULT_DEST))
    import_parser.add_argument("--candidate-dir", default=str(DEFAULT_CANDIDATES))
    import_parser.add_argument("--no-raw-copy", action="store_true")
    import_parser.add_argument("--candidate-min-sessions", type=int, default=2)

    status_parser = sub.add_parser("status", help="Show imported history status")
    status_parser.add_argument("--dest", default=str(DEFAULT_DEST))

    search_parser = sub.add_parser("search", help="Search imported legacy history")
    search_parser.add_argument("query")
    search_parser.add_argument("--dest", default=str(DEFAULT_DEST))
    search_parser.add_argument("--limit", type=int, default=12)

    list_parser = sub.add_parser("list-sessions", help="List imported legacy sessions")
    list_parser.add_argument("--dest", default=str(DEFAULT_DEST))
    list_parser.add_argument("--limit", type=int, default=12)
    list_parser.add_argument("--project", default="")
    list_parser.add_argument("--query", default="")

    show_parser = sub.add_parser("show-session", help="Show a legacy session tail")
    show_parser.add_argument("target")
    show_parser.add_argument("--dest", default=str(DEFAULT_DEST))
    show_parser.add_argument("--tail", type=int, default=12)
    show_parser.add_argument("--max-chars", type=int, default=1200)

    resume_parser = sub.add_parser("resume-context", help="Build compact context for /resume")
    resume_parser.add_argument("target")
    resume_parser.add_argument("--dest", default=str(DEFAULT_DEST))
    resume_parser.add_argument("--limit-entries", type=int, default=18)
    resume_parser.add_argument("--max-chars", type=int, default=12000)

    sync_parser = sub.add_parser("sync-native-resume", help="Sync imported history into the native /resume index")
    sync_parser.add_argument("--dest", default=str(DEFAULT_DEST))
    sync_parser.add_argument(
        "--claude-config-dir",
        dest="native_config_dir",
        default=os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ("." + "claude")),
    )
    sync_parser.add_argument("--target-cwd", default=os.getcwd())
    sync_parser.add_argument("--limit", type=int, default=0, help="0 means all sessions")
    sync_parser.add_argument("--limit-entries", type=int, default=18)
    sync_parser.add_argument("--max-chars", type=int, default=12000)
    sync_parser.add_argument("--clean", action="store_true", help="Remove old DreamSeed legacy bridge files for this target before syncing")
    sync_parser.add_argument("--include-stubs", action="store_true", help="Also sync tiny /resume-only legacy sessions")

    args = parser.parse_args()
    if args.command == "import":
        result = import_history(
            source=Path(args.source),
            dest=Path(args.dest),
            candidate_dir=Path(args.candidate_dir),
            raw_copy=not args.no_raw_copy,
            candidate_min_sessions=args.candidate_min_sessions,
        )
        print_json({"ok": True, **result})
        return 0
    if args.command == "status":
        print_json({"ok": True, **read_status(Path(args.dest))})
        return 0
    if args.command == "search":
        print_json({"ok": True, **search_history(Path(args.dest), args.query, args.limit)})
        return 0
    if args.command == "list-sessions":
        print_json(
            {
                "ok": True,
                **list_sessions(
                    dest=Path(args.dest),
                    limit=args.limit,
                    project=args.project,
                    query=args.query,
                ),
            }
        )
        return 0
    if args.command == "show-session":
        print_json(
            {
                "ok": True,
                **show_session(
                    dest=Path(args.dest),
                    target=args.target,
                    tail=args.tail,
                    max_chars=args.max_chars,
                ),
            }
        )
        return 0
    if args.command == "resume-context":
        print_json(
            {
                "ok": True,
                **resume_context(
                    dest=Path(args.dest),
                    target=args.target,
                    limit_entries=args.limit_entries,
                    max_chars=args.max_chars,
                ),
            }
        )
        return 0
    if args.command == "sync-native-resume":
        print_json(
            {
                "ok": True,
                **sync_native_resume(
                    dest=Path(args.dest),
                    claude_config_dir=Path(args.native_config_dir),
                    target_cwd=Path(args.target_cwd),
                    limit=args.limit,
                    limit_entries=args.limit_entries,
                    max_chars=args.max_chars,
                    clean=args.clean,
                    include_stubs=args.include_stubs,
                ),
            }
        )
        return 0
    return 2


def import_history(
    source: Path,
    dest: Path,
    candidate_dir: Path,
    raw_copy: bool = True,
    candidate_min_sessions: int = 2,
) -> dict[str, Any]:
    if not source.exists():
        raise SystemExit(f"legacy history source not found: {source}")

    imported_at = now()
    sessions_dir = dest / "sessions"
    raw_dir = dest / "raw"
    candidates_import_dir = candidate_dir
    sessions_dir.mkdir(parents=True, exist_ok=True)
    candidates_import_dir.mkdir(parents=True, exist_ok=True)
    (candidates_import_dir / "reviewed").mkdir(exist_ok=True)
    (candidates_import_dir / "rejected").mkdir(exist_ok=True)
    (candidates_import_dir / "promoted").mkdir(exist_ok=True)

    if raw_copy:
        copy_raw_history(source, raw_dir)

    records = read_all_records(source)
    sessions = group_sessions(records)
    write_sessions(sessions_dir, sessions)
    project_index = build_project_index(sessions)

    manifest = {
        "imported_at": imported_at,
        "source": str(source),
        "dest": str(dest),
        "raw_copy": raw_copy,
        "record_count": len(records),
        "session_count": len(sessions),
        "project_count": len(project_index["projects"]),
        "policy": "Raw legacy history is private archive data. Long-term memory promotion must use memory_review.py then memory_promote.py.",
        "raw_archive": str(raw_dir) if raw_copy else None,
        "sessions_dir": str(sessions_dir),
        "project_index": str(dest / "projects.json"),
        "candidate_dir": str(candidate_dir),
    }
    dest.mkdir(parents=True, exist_ok=True)
    write_json(dest / "manifest.json", manifest)
    write_json(dest / "projects.json", project_index)

    candidate_results = write_project_candidates(
        project_index=project_index,
        candidate_dir=candidates_import_dir,
        archive_manifest=dest / "manifest.json",
        min_sessions=candidate_min_sessions,
    )

    return {
        "manifest": str(dest / "manifest.json"),
        "projects": str(dest / "projects.json"),
        "records": len(records),
        "sessions": len(sessions),
        "projects_count": len(project_index["projects"]),
        "candidates_written": candidate_results["written"],
        "candidate_dir": str(candidate_dir),
        "skipped_sensitive_logs": [
            "cc-switch/proxy_request_logs.json",
            "cc-switch/logs",
        ],
    }


def copy_raw_history(source: Path, raw_dir: Path) -> None:
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    for rel in RAW_COPY_PATHS:
        src = source / rel
        if not src.exists():
            continue
        dst = raw_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def read_all_records(source: Path) -> list[dict[str, Any]]:
    jsonl_files: list[Path] = []
    main_history = source / "claude" / "history.jsonl"
    if main_history.exists():
        jsonl_files.append(main_history)
    reconstructed = source / "reconstructed_projects_light"
    if reconstructed.exists():
        jsonl_files.extend(sorted(reconstructed.rglob("*.jsonl")))

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for file_path in jsonl_files:
        for line_number, item in iter_jsonl(file_path):
            normalized = normalize_record(item, file_path, line_number)
            digest = record_digest(normalized)
            if digest in seen:
                continue
            seen.add(digest)
            normalized["record_hash"] = digest
            records.append(normalized)

    for record in read_archived_session_index(source):
        digest = record_digest(record)
        if digest in seen:
            continue
        seen.add(digest)
        record["record_hash"] = digest
        records.append(record)

    claw_dir = source / "claw" / "sessions"
    if claw_dir.exists():
        for file_path in sorted(claw_dir.glob("*.json")):
            item = read_json_safe(file_path)
            if item is None:
                continue
            normalized = normalize_record(item, file_path, 1)
            normalized["source_kind"] = "claw-session"
            digest = record_digest(normalized)
            if digest in seen:
                continue
            seen.add(digest)
            normalized["record_hash"] = digest
            records.append(normalized)

    return sorted(records, key=lambda item: (item.get("timestamp") or 0, item.get("session_id") or ""))


def read_archived_session_index(source: Path) -> list[dict[str, Any]]:
    index_dir = source / "claude" / "archived-session-index"
    if not index_dir.exists():
        return []

    records: list[dict[str, Any]] = []
    for file_path in sorted(index_dir.glob("*.json")):
        payload = read_json_safe(file_path)
        if not isinstance(payload, list):
            continue
        for index, item in enumerate(payload, start=1):
            if not isinstance(item, dict):
                continue
            original_path = str(item.get("path") or "")
            session_id = session_id_from_archived_path(original_path) or f"{file_path.stem}-{index}"
            display = display_from_archived_summary(item)
            if not display:
                display = json.dumps(item, ensure_ascii=False, default=str)
            timestamp = normalize_timestamp(item.get("last_write"))
            records.append(
                {
                    "session_id": session_id,
                    "project": project_from_archived_path(original_path),
                    "timestamp": timestamp,
                    "iso_time": timestamp_to_iso(timestamp),
                    "type": f"archived-{file_path.stem}",
                    "display": display,
                    "source": str(file_path),
                    "source_line": index,
                    "source_kind": "archived-session-index",
                    "archived_original_path": original_path or None,
                }
            )
    return records


def display_from_archived_summary(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("summary_hint", "status", "recommendation"):
        if item.get(key):
            parts.append(f"{key}: {item[key]}")
    for key in ("head", "tail", "user_samples", "tool_samples", "error_samples", "tail_samples"):
        value = item.get(key)
        if isinstance(value, list) and value:
            parts.append(f"{key}:")
            parts.extend(str(sample) for sample in value[:10])
    return "\n".join(parts)


def session_id_from_archived_path(value: str) -> str:
    if not value:
        return ""
    match = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", value)
    return match.group(1) if match else ""


def project_from_archived_path(value: str) -> str:
    if not value:
        return "archived-session-index"
    normalized = value.replace("/", "\\")
    marker = "\\projects\\"
    if marker not in normalized:
        return "archived-session-index"
    rest = normalized.split(marker, 1)[1]
    parts = [part for part in rest.split("\\") if part]
    if not parts:
        return "archived-session-index"
    return f"archived:{parts[0]}"


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_number, json.loads(line)
            except json.JSONDecodeError:
                yield line_number, {"display": line, "type": "invalid-jsonl-line"}


def classify_record_type(item: dict[str, Any], fallback: str) -> str:
    message = item.get("message") if isinstance(item, dict) else None
    content = message.get("content") if isinstance(message, dict) else item.get("content") if isinstance(item, dict) else None
    block_types = content_block_types(content)
    if "tool_result" in block_types:
        return "tool_result"
    if "tool_use" in block_types and "text" not in block_types:
        return "assistant_tool_use" if "assistant" in fallback else "tool_use"
    return fallback


def content_block_types(value: Any) -> set[str]:
    if isinstance(value, list):
        out: set[str] = set()
        for item in value:
            out.update(content_block_types(item))
        return out
    if isinstance(value, dict):
        block_type = str(value.get("type") or "").strip()
        out = {block_type} if block_type else set()
        if "content" in value:
            out.update(content_block_types(value.get("content")))
        if "text" in value and value.get("text"):
            out.add("text")
        return out
    if isinstance(value, str) and value.strip():
        return {"text"}
    return set()

def normalize_record(item: dict[str, Any], source_path: Path, line_number: int) -> dict[str, Any]:
    display = stringify_display(item)
    session_id = str(item.get("sessionId") or item.get("session_id") or item.get("id") or "").strip()
    if not session_id:
        session_id = hashlib.sha1(str(source_path).encode("utf-8")).hexdigest()[:16]
    project = str(item.get("project") or item.get("cwd") or item.get("workspace") or "unknown").strip() or "unknown"
    timestamp = normalize_timestamp(item.get("timestamp") or item.get("time") or item.get("created_at"))
    record_type = classify_record_type(item, str(item.get("type") or item.get("role") or "legacy").strip() or "legacy")
    return {
        "session_id": session_id,
        "project": project,
        "timestamp": timestamp,
        "iso_time": timestamp_to_iso(timestamp),
        "type": record_type,
        "display": display,
        "source": str(source_path),
        "source_line": line_number,
        "source_kind": "jsonl",
    }


def stringify_display(item: dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return normalize_text(item)
    if "display" in item:
        return normalize_text(item.get("display"))

    message = item.get("message")
    if isinstance(message, dict):
        text = content_to_display(message.get("content"))
        if text:
            return text
        for key in ("text", "error", "message"):
            if key in message:
                return normalize_text(message.get(key))

    for key in ("content", "text", "prompt", "response"):
        if key in item:
            text = content_to_display(item.get(key))
            if text:
                return text
            return normalize_text(item.get(key))
    return normalize_text(item)


def content_to_display(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [content_block_to_display(block) for block in value]
        return "\n".join(part for part in parts if part).strip()
    if isinstance(value, dict):
        return content_block_to_display(value)
    return normalize_text(value)


def content_block_to_display(block: Any) -> str:
    if block is None:
        return ""
    if isinstance(block, str):
        return block
    if not isinstance(block, dict):
        return normalize_text(block)

    block_type = str(block.get("type") or "").strip()
    if block_type == "text":
        return normalize_text(block.get("text"))
    if block_type == "tool_use":
        name = str(block.get("name") or "tool").strip() or "tool"
        tool_input = block.get("input")
        if tool_input in (None, ""):
            return f"[tool_use:{name}]"
        return f"[tool_use:{name}] {trim_text(normalize_text(tool_input), 800)}"
    if block_type == "tool_result":
        content = block.get("content")
        text = content_to_display(content)
        return f"[tool_result] {trim_text(text, 1200)}" if text else "[tool_result]"
    if block_type in {"image", "image_url"}:
        return "[image]"
    if "content" in block:
        return content_to_display(block.get("content"))
    if "text" in block:
        return normalize_text(block.get("text"))
    return normalize_text(block)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def normalize_timestamp(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        raw = int(value)
        if raw > 10_000_000_000:
            raw = raw // 1000
        return raw

    text = str(value).strip()
    if not text:
        return 0
    try:
        raw = int(float(text))
        if raw > 10_000_000_000:
            raw = raw // 1000
        return raw
    except ValueError:
        pass

    try:
        normalized = text.replace("Z", "+00:00")
        return int(datetime.fromisoformat(normalized).timestamp())
    except (ValueError, OSError):
        return 0

def timestamp_to_iso(timestamp: int) -> str | None:
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    except (OSError, ValueError):
        return None


def record_digest(record: dict[str, Any]) -> str:
    stable = {
        "session_id": record.get("session_id"),
        "project": record.get("project"),
        "timestamp": record.get("timestamp"),
        "type": record.get("type"),
        "display": record.get("display"),
    }
    return hashlib.sha1(json.dumps(stable, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def group_sessions(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    sessions: dict[str, dict[str, Any]] = {}
    for record in records:
        session_id = str(record["session_id"])
        session = sessions.setdefault(
            session_id,
            {
                "session_id": session_id,
                "project": record.get("project") or "unknown",
                "first_timestamp": record.get("timestamp") or 0,
                "last_timestamp": record.get("timestamp") or 0,
                "entry_count": 0,
                "sources": [],
                "entries": [],
            },
        )
        if is_better_project(record.get("project"), session.get("project")):
            session["project"] = record.get("project") or session["project"]
        session["entry_count"] += 1
        timestamp = record.get("timestamp") or 0
        if timestamp:
            if not session["first_timestamp"] or timestamp < session["first_timestamp"]:
                session["first_timestamp"] = timestamp
            if timestamp > session["last_timestamp"]:
                session["last_timestamp"] = timestamp
        if record["source"] not in session["sources"]:
            session["sources"].append(record["source"])
        session["entries"].append(record)

    for session in sessions.values():
        session["first_iso_time"] = timestamp_to_iso(session.get("first_timestamp") or 0)
        session["last_iso_time"] = timestamp_to_iso(session.get("last_timestamp") or 0)
        joined = "\n".join(entry.get("display", "") for entry in session["entries"])
        session["content_hash"] = hashlib.sha1(joined.encode("utf-8", errors="replace")).hexdigest()
    return sessions


def is_better_project(candidate: Any, current: Any) -> bool:
    candidate_text = str(candidate or "")
    current_text = str(current or "")
    if not candidate_text or candidate_text == "unknown":
        return False
    if not current_text or current_text == "unknown":
        return True
    if current_text.startswith("archived:") and not candidate_text.startswith("archived:"):
        return True
    if candidate_text.startswith("archived:"):
        return False
    return False


def write_sessions(sessions_dir: Path, sessions: dict[str, dict[str, Any]]) -> None:
    if sessions_dir.exists():
        shutil.rmtree(sessions_dir)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    for session in sessions.values():
        project_dir = sessions_dir / safe_name(session.get("project") or "unknown")
        project_dir.mkdir(parents=True, exist_ok=True)
        out = project_dir / f"{safe_name(session['session_id'])}.json"
        write_json(out, session)


def build_project_index(sessions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    projects: dict[str, dict[str, Any]] = {}
    for session in sessions.values():
        project = session.get("project") or "unknown"
        info = projects.setdefault(
            project,
            {
                "project": project,
                "session_count": 0,
                "entry_count": 0,
                "first_timestamp": 0,
                "last_timestamp": 0,
                "sessions": [],
            },
        )
        info["session_count"] += 1
        info["entry_count"] += int(session.get("entry_count") or 0)
        first = int(session.get("first_timestamp") or 0)
        last = int(session.get("last_timestamp") or 0)
        if first and (not info["first_timestamp"] or first < info["first_timestamp"]):
            info["first_timestamp"] = first
        if last and last > info["last_timestamp"]:
            info["last_timestamp"] = last
        info["sessions"].append(
            {
                "session_id": session["session_id"],
                "entry_count": session["entry_count"],
                "first_iso_time": session.get("first_iso_time"),
                "last_iso_time": session.get("last_iso_time"),
                "content_hash": session.get("content_hash"),
            }
        )

    for info in projects.values():
        info["first_iso_time"] = timestamp_to_iso(info.get("first_timestamp") or 0)
        info["last_iso_time"] = timestamp_to_iso(info.get("last_timestamp") or 0)
        info["sessions"].sort(key=lambda item: item.get("last_iso_time") or "")

    return {
        "generated_at": now(),
        "projects": sorted(projects.values(), key=lambda item: (-item["session_count"], item["project"])),
    }


def write_project_candidates(
    project_index: dict[str, Any],
    candidate_dir: Path,
    archive_manifest: Path,
    min_sessions: int,
) -> dict[str, int]:
    for old_candidate in candidate_dir.glob("memory-candidate-legacy-history-*.json"):
        old_candidate.unlink(missing_ok=True)

    written = 0
    for project in project_index["projects"]:
        if int(project.get("session_count") or 0) < min_sessions:
            continue
        text = (
            f"Legacy Claude Code history is available for project: {project['project']}\n"
            f"Sessions: {project['session_count']}; entries: {project['entry_count']}.\n"
            f"Time range: {project.get('first_iso_time') or 'unknown'} to {project.get('last_iso_time') or 'unknown'}.\n"
            f"Archive manifest: {archive_manifest}\n"
            "Use scripts/import_claude_history.py search to inspect this private archive before asking the user to repeat old context."
        )
        digest = hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()
        candidate = {
            "id": f"memory-candidate-legacy-history-{digest[:16]}",
            "created_at": now(),
            "source": "legacy-claude-code-import",
            "wing": "dreamseed",
            "score": score_project_candidate(project),
            "reasons": ["legacy project history index", "manual-review-required"],
            "promotion_policy": "manual-review-required",
            "allowed_promotion_path": "memory_review.py apply -> reviewed/ -> memory_promote.py promote-reviewed",
            "source_transcript": str(archive_manifest),
            "summary": redact(text)[:500],
            "text": redact(text),
            "hash": digest,
        }
        out = candidate_dir / f"{candidate['id']}.json"
        write_json(out, candidate)
        written += 1
    return {"written": written}


def score_project_candidate(project: dict[str, Any]) -> float:
    sessions = int(project.get("session_count") or 0)
    entries = int(project.get("entry_count") or 0)
    score = 0.52
    if sessions >= 5:
        score += 0.1
    if sessions >= 20:
        score += 0.08
    if entries >= 100:
        score += 0.08
    return min(0.85, round(score, 2))


def read_status(dest: Path) -> dict[str, Any]:
    manifest_path = dest / "manifest.json"
    projects_path = dest / "projects.json"
    manifest = read_json_safe(manifest_path) if manifest_path.exists() else {}
    projects = read_json_safe(projects_path) if projects_path.exists() else {"projects": []}
    legacy_pairs = load_legacy_session_pairs(dest)
    native_pairs = load_native_terminal_session_pairs()
    native_records = sum(int(session.get("entry_count") or 0) for session, _ in native_pairs)
    legacy_records_actual = sum(int(session.get("entry_count") or 0) for session, _ in legacy_pairs)
    native_project_index = summarize_session_projects([session for session, _ in native_pairs])

    imported = bool(manifest_path.exists() or legacy_pairs)
    legacy_sessions = len(legacy_pairs) or (int(manifest.get("session_count") or 0) if isinstance(manifest, dict) else 0)
    legacy_records = legacy_records_actual or (int(manifest.get("record_count") or 0) if isinstance(manifest, dict) else 0)
    legacy_projects = int(manifest.get("project_count") or 0) if isinstance(manifest, dict) else 0
    total_projects = len({*(item.get("project") for item in projects.get("projects", []) if item.get("project")), *native_project_index.keys()})

    top_projects = [
        {
            "project": item.get("project"),
            "sessions": item.get("session_count"),
            "entries": item.get("entry_count"),
        }
        for item in projects.get("projects", [])[:10]
    ]
    for project, stats in native_project_index.items():
        top_projects.append({
            "project": project,
            "sessions": stats["sessions"],
            "entries": stats["entries"],
            "source_kind": "dreamseed-terminal-native",
        })
    top_projects.sort(key=lambda item: (int(item.get("sessions") or 0), int(item.get("entries") or 0)), reverse=True)

    return {
        "status": "imported" if imported else ("native-only" if native_pairs else "not-imported"),
        "manifest": str(manifest_path),
        "records": legacy_records + native_records,
        "sessions": legacy_sessions + len(native_pairs),
        "projects": total_projects or legacy_projects or len(native_project_index),
        "legacy_sessions": legacy_sessions,
        "native_sessions": len(native_pairs),
        "native_records": native_records,
        "native_projects_dir": [str(path) for path in native_history_project_dirs() if path.exists()],
        "top_projects": top_projects[:10],
    }

def search_history(dest: Path, query: str, limit: int) -> dict[str, Any]:
    meta = read_history_meta()
    lowered = query.lower()
    matches = []
    for data, path in iter_all_sessions(dest):
        metadata = session_metadata(data, path)
        if history_meta_hidden(metadata, meta):
            continue
        metadata = apply_history_meta(metadata, meta)
        project = str(data.get("project") or "")
        for entry in data.get("entries", []):
            display = str(entry.get("display") or "")
            haystack = f"{project}\n{display}".lower()
            if lowered not in haystack:
                continue
            matches.append(
                {
                    "project": project,
                    "session_id": data.get("session_id"),
                    "time": entry.get("iso_time"),
                    "type": entry.get("type"),
                    "snippet": snippet(redact(display), query),
                    "preview": metadata.get("preview") or snippet(redact(display), query),
                    "title": metadata.get("title"),
                    "user_preview": metadata.get("user_preview") or snippet(redact(display), query),
                    "assistant_summary": metadata.get("assistant_summary"),
                    "summary_kind": metadata.get("summary_kind"),
                    "project_name": metadata.get("project_name"),
                    "entry_count": metadata.get("entry_count") or len(data.get("entries", [])),
                    "last_time": metadata.get("last_time"),
                    "last_timestamp": metadata.get("last_timestamp"),
                    "is_resume_stub": metadata.get("is_resume_stub", False),
                    "source_kind": metadata.get("source_kind") or "",
                    "session_file": str(path),
                    "_rank": search_rank(query, project, display, entry.get("timestamp") or data.get("last_timestamp") or 0),
                }
            )
            break
    matches.sort(key=lambda item: item.pop("_rank"), reverse=True)
    results = matches[:limit]
    return {"query": query, "count": len(results), "results": results}

def list_sessions(dest: Path, limit: int, project: str = "", query: str = "") -> dict[str, Any]:
    sessions = load_session_summaries(dest)
    meta = read_history_meta()
    project_lower = project.lower().strip()
    query_lower = query.lower().strip()
    filtered: list[dict[str, Any]] = []

    for item in sessions:
        if history_meta_hidden(item, meta):
            continue
        item = apply_history_meta(item, meta)
        haystack = f"{item.get('project') or ''}\n{item.get('preview') or ''}".lower()
        if project_lower and project_lower not in str(item.get("project") or "").lower():
            continue
        if query_lower and query_lower not in haystack:
            continue
        filtered.append(item)

    filtered.sort(
        key=lambda item: (
            0 if item.get("is_resume_stub") else 1,
            int(item.get("last_timestamp") or 0),
        ),
        reverse=True,
    )
    return {
        "count": len(filtered[:limit]),
        "total_matches": len(filtered),
        "sessions": filtered[:limit],
    }


def show_session(dest: Path, target: str, tail: int, max_chars: int) -> dict[str, Any]:
    session, session_file = find_session(dest, target)
    entries = session.get("entries", [])[-max(1, tail) :]
    return {
        "session": session_metadata(session, session_file),
        "entries": [
            {
                "time": entry.get("iso_time"),
                "type": entry.get("type"),
                "text": trim_text(redact(str(entry.get("display") or "")), max_chars),
            }
            for entry in entries
        ],
    }


def resume_context(dest: Path, target: str, limit_entries: int, max_chars: int) -> dict[str, Any]:
    session, session_file = find_session(dest, target)
    return build_resume_context(
        session=session,
        session_file=session_file,
        limit_entries=limit_entries,
        max_chars=max_chars,
    )


def build_resume_context(
    session: dict[str, Any],
    session_file: Path,
    limit_entries: int,
    max_chars: int,
) -> dict[str, Any]:
    entries = session.get("entries", [])[-max(1, limit_entries) :]
    lines = [
        "Legacy Claude Code session resumed as private context.",
        "Do not treat this archive as long-term memory unless the user explicitly asks to review/promote it.",
        f"Project: {session.get('project') or 'unknown'}",
        f"Session ID: {session.get('session_id')}",
        f"Time: {session.get('first_iso_time') or 'unknown'} to {session.get('last_iso_time') or 'unknown'}",
        f"Entries: {session.get('entry_count')}",
        "",
        "Recent transcript tail:",
    ]
    for entry in entries:
        timestamp = entry.get("iso_time") or "unknown-time"
        kind = entry.get("type") or "legacy"
        display = trim_text(redact(str(entry.get("display") or "")), 1600)
        if not display:
            continue
        lines.append(f"[{timestamp}] {kind}: {display}")

    context = trim_text("\n".join(lines), max_chars)
    return {
        "session": session_metadata(session, session_file),
        "context": context,
        "entry_count_included": len(entries),
        "policy": "session-context-only; MemPalace promotion requires memory_review.py apply -> reviewed/ -> memory_promote.py promote-reviewed",
    }


def sync_native_resume(
    dest: Path,
    claude_config_dir: Path,
    target_cwd: Path,
    limit: int,
    limit_entries: int,
    max_chars: int,
    clean: bool,
    include_stubs: bool,
) -> dict[str, Any]:
    sessions_dir = dest / "sessions"
    if not sessions_dir.exists():
        raise SystemExit(f"imported sessions not found: {sessions_dir}")

    target_cwd_text = str(target_cwd.resolve() if target_cwd.exists() else target_cwd)
    project_dir = claude_config_dir / "projects" / native_sanitize_path(target_cwd_text)
    project_dir.mkdir(parents=True, exist_ok=True)

    removed = clean_native_resume_bridges(project_dir) if clean else 0
    sessions = load_session_summaries(dest)
    sessions = [
        item
        for item in sessions
        if include_stubs or not item.get("is_resume_stub")
    ]
    sessions.sort(
        key=lambda item: (
            int(item.get("last_timestamp") or 0),
            int(item.get("entry_count") or 0),
        ),
        reverse=True,
    )
    if limit > 0:
        sessions = sessions[:limit]

    synced = 0
    skipped_existing = 0
    skipped_invalid = 0
    for item in sessions:
        session_file = Path(str(item.get("session_file") or ""))
        session = read_json_safe(session_file)
        if not session:
            skipped_invalid += 1
            continue
        try:
            result = write_native_resume_bridge(
                session=session,
                session_file=session_file,
                project_dir=project_dir,
                target_cwd=target_cwd_text,
                limit_entries=limit_entries,
                max_chars=max_chars,
            )
        except OSError:
            result = "invalid"
        if result == "synced":
            synced += 1
        elif result == "exists":
            skipped_existing += 1
        else:
            skipped_invalid += 1

    manifest = {
        "type": "dreamseed-legacy-resume-sync-manifest",
        "updated_at": now(),
        "legacy_dest": str(dest),
        "claude_config_dir": str(claude_config_dir),
        "target_cwd": target_cwd_text,
        "target_project_dir": str(project_dir),
        "synced": synced,
        "skipped_existing": skipped_existing,
        "skipped_invalid": skipped_invalid,
        "removed": removed,
        "include_stubs": include_stubs,
        "policy": "Native /resume bridge files are session context only. Long-term memory promotion still requires review.",
    }
    manifest_path = project_dir / ".dreamseed-legacy-resume-manifest.json"
    try:
        write_json(manifest_path, manifest)
        manifest["manifest"] = str(manifest_path)
    except OSError as error:
        manifest["manifest"] = str(manifest_path)
        manifest["manifest_warning"] = f"could not write sync manifest: {error}"

    return manifest


def write_native_resume_bridge(
    session: dict[str, Any],
    session_file: Path,
    project_dir: Path,
    target_cwd: str,
    limit_entries: int,
    max_chars: int,
) -> str:
    session_id = str(session.get("session_id") or "").strip()
    try:
        uuid.UUID(session_id)
    except (ValueError, TypeError):
        return "invalid"

    payload = build_resume_context(
        session=session,
        session_file=session_file,
        limit_entries=limit_entries,
        max_chars=max_chars,
    )
    context = payload.get("context") or ""
    if not context:
        return "invalid"

    content_hash = hashlib.sha1(
        json.dumps(
            {
                "session_id": session_id,
                "content_hash": session.get("content_hash"),
                "context": context,
                "target_cwd": target_cwd,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8", errors="replace")
    ).hexdigest()
    out = project_dir / f"{session_id}.jsonl"
    if out.exists():
        try:
            existing_head = out.read_text(encoding="utf-8-sig", errors="replace")[:4096]
        except OSError:
            return "invalid"
        if (
            '"type":"dreamseed-legacy-resume-bridge"' in existing_head
            or '"type": "dreamseed-legacy-resume-bridge"' in existing_head
        ):
            if content_hash in existing_head:
                return "exists"
        else:
            return "exists"

    metadata = session_metadata(session, session_file)
    preview = str(metadata.get("preview") or "").strip()
    project = str(session.get("project") or metadata.get("project") or "unknown")
    title = compact_title(f"Legacy Claude Code: {project}", preview)
    first_prompt = compact_title(f"[Legacy Claude Code] {project}", preview, limit=200)
    timestamp = best_session_iso(session) or now()
    user_uuid = deterministic_uuid(f"dreamseed-legacy-user:{session_id}:{content_hash}")
    assistant_uuid = deterministic_uuid(f"dreamseed-legacy-assistant:{session_id}:{content_hash}")

    user_content = (
        f"{first_prompt}\n\n"
        f"{context}\n\n"
        "Policy: this is imported legacy session context only. Do not promote it to MemPalace unless the user explicitly reviews and promotes it."
    )
    assistant_text = (
        "Legacy Claude Code session context loaded from DreamSeed's private archive. "
        "I will use it as current session context only."
    )
    entries = [
        {
            "type": "dreamseed-legacy-resume-bridge",
            "sessionId": session_id,
            "legacy_content_hash": content_hash,
            "legacy_session_file": str(session_file),
            "legacy_project": project,
            "targetCwd": target_cwd,
            "timestamp": timestamp,
        },
        {
            "parentUuid": None,
            "isSidechain": False,
            "promptId": deterministic_uuid(f"dreamseed-legacy-prompt:{session_id}:{content_hash}"),
            "type": "user",
            "message": {
                "role": "user",
                "content": user_content,
            },
            "uuid": user_uuid,
            "timestamp": timestamp,
            "permissionMode": "default",
            "userType": "external",
            "entrypoint": "cli",
            "cwd": target_cwd,
            "sessionId": session_id,
            "version": "0.1.0",
            "gitBranch": "HEAD",
        },
        {
            "parentUuid": user_uuid,
            "isSidechain": False,
            "message": {
                "id": f"dreamseed-legacy-{session_id}",
                "type": "message",
                "role": "assistant",
                "model": "dreamseed-legacy-resume",
                "content": [{"type": "text", "text": assistant_text}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {
                    "input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "output_tokens": 0,
                },
            },
            "type": "assistant",
            "uuid": assistant_uuid,
            "timestamp": timestamp,
            "userType": "external",
            "entrypoint": "cli",
            "cwd": target_cwd,
            "sessionId": session_id,
            "version": "0.1.0",
            "gitBranch": "HEAD",
        },
        {
            "type": "last-prompt",
            "lastPrompt": first_prompt,
            "sessionId": session_id,
        },
        {
            "type": "custom-title",
            "customTitle": title,
            "sessionId": session_id,
        },
    ]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(json.dumps(entry, ensure_ascii=False, default=str) for entry in entries) + "\n",
        encoding="utf-8",
    )
    timestamp_seconds = int(session.get("last_timestamp") or session.get("first_timestamp") or 0)
    if timestamp_seconds > 0:
        try:
            os.utime(out, (timestamp_seconds, timestamp_seconds))
        except OSError:
            pass
    return "synced"


def clean_native_resume_bridges(project_dir: Path) -> int:
    if not project_dir.exists():
        return 0
    removed = 0
    for path in project_dir.glob("*.jsonl"):
        try:
            head = path.read_text(encoding="utf-8-sig", errors="replace")[:2048]
        except OSError:
            continue
        if (
            '"type":"dreamseed-legacy-resume-bridge"' in head
            or '"type": "dreamseed-legacy-resume-bridge"' in head
        ):
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def native_sanitize_path(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", value)


def deterministic_uuid(value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, value))


def best_session_iso(session: dict[str, Any]) -> str | None:
    return session.get("last_iso_time") or session.get("first_iso_time") or timestamp_to_iso(int(session.get("last_timestamp") or 0))


def compact_title(prefix: str, preview: str, limit: int = 120) -> str:
    text = prefix
    if preview:
        text = f"{prefix} - {preview}"
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 3)].rstrip() + "..."


def native_history_project_dirs() -> list[Path]:
    candidates: list[Path] = []
    if os.environ.get("DREAMSEED_NATIVE_HISTORY_DIR"):
        candidates.append(Path(os.environ["DREAMSEED_NATIVE_HISTORY_DIR"]))
    if os.environ.get("DREAMSEED_LOCAL_ROOT"):
        candidates.append(Path(os.environ["DREAMSEED_LOCAL_ROOT"]) / "home" / ".claude" / "projects")
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        candidates.append(Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects")
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "DreamSeed" / "home" / ".claude" / "projects")
    candidates.append(Path.home() / ".claude" / "projects")

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            key = str(candidate.resolve()).lower()
        except OSError:
            key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def native_history_jsonl_paths() -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    for root in native_history_project_dirs():
        if not root.exists() or not root.is_dir():
            continue
        for path in sorted(root.rglob("*.jsonl")):
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
    return paths


def read_native_terminal_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for file_path in native_history_jsonl_paths():
        file_records: list[dict[str, Any]] = []
        is_bridge_file = False
        for line_number, item in iter_jsonl(file_path):
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "").strip()
            if item_type in NATIVE_HISTORY_BRIDGE_TYPES:
                is_bridge_file = True
                break
            if item_type in NATIVE_HISTORY_SKIP_TYPES:
                continue
            if item_type == "system" and str(item.get("subtype") or "").strip() in NATIVE_HISTORY_SKIP_SYSTEM_SUBTYPES:
                continue
            if not item.get("sessionId"):
                continue
            display = stringify_display(item)
            if not display.strip():
                continue
            normalized = normalize_record(item, file_path, line_number)
            if normalized.get("project") == "unknown":
                normalized["project"] = native_project_from_path(file_path)
            normalized["source_kind"] = "dreamseed-terminal-native"
            digest = record_digest(normalized)
            if digest in seen:
                continue
            seen.add(digest)
            normalized["record_hash"] = digest
            file_records.append(normalized)
        if is_bridge_file:
            continue
        records.extend(file_records)
    return sorted(records, key=lambda item: (item.get("timestamp") or 0, item.get("session_id") or ""))


def native_project_from_path(file_path: Path) -> str:
    try:
        name = file_path.parent.name
    except OSError:
        name = "unknown"
    return name or "unknown"


def load_native_terminal_sessions() -> list[dict[str, Any]]:
    sessions = group_sessions(read_native_terminal_records())
    out: list[dict[str, Any]] = []
    for session in sessions.values():
        session["source_kind"] = "dreamseed-terminal-native"
        out.append(session)
    return out


def load_native_terminal_session_pairs() -> list[tuple[dict[str, Any], Path]]:
    pairs: list[tuple[dict[str, Any], Path]] = []
    for session in load_native_terminal_sessions():
        source = str((session.get("sources") or [""])[0] or "")
        pairs.append((session, Path(source) if source else Path(f"native-{session.get('session_id')}.jsonl")))
    return pairs


def load_legacy_session_pairs(dest: Path) -> list[tuple[dict[str, Any], Path]]:
    pairs: list[tuple[dict[str, Any], Path]] = []
    sessions_dir = dest / "sessions"
    if not sessions_dir.exists():
        return pairs
    for path in sorted(sessions_dir.rglob("*.json")):
        data = read_json_safe(path)
        if data:
            pairs.append((data, path))
    return pairs


def iter_all_sessions(dest: Path):
    for data, path in load_legacy_session_pairs(dest):
        yield data, path
    for session, path in load_native_terminal_session_pairs():
        yield session, path


def summarize_session_projects(sessions: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    projects: dict[str, dict[str, int]] = {}
    for session in sessions:
        project = str(session.get("project") or "unknown")
        entry = projects.setdefault(project, {"sessions": 0, "entries": 0})
        entry["sessions"] += 1
        entry["entries"] += int(session.get("entry_count") or 0)
    return projects


def load_session_summaries(dest: Path) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    for data, path in iter_all_sessions(dest):
        sessions.append(session_metadata(data, path))
    return sessions

def session_metadata(session: dict[str, Any], session_file: Path) -> dict[str, Any]:
    entries = session.get("entries", [])
    previews = session_preview_bundle(session)
    preview = previews["user_preview"] or previews["title"]
    is_resume_stub = session_is_resume_stub(session, preview)
    return {
        "project": session.get("project"),
        "project_name": project_display_name(session.get("project")),
        "session_id": session.get("session_id"),
        "first_time": session.get("first_iso_time"),
        "last_time": session.get("last_iso_time"),
        "first_timestamp": session.get("first_timestamp") or 0,
        "last_timestamp": session.get("last_timestamp") or 0,
        "entry_count": session.get("entry_count"),
        "content_hash": session.get("content_hash"),
        "title": previews["title"],
        "preview": preview,
        "user_preview": previews["user_preview"],
        "assistant_summary": previews["assistant_summary"],
        "summary_kind": previews["summary_kind"],
        "is_resume_stub": is_resume_stub,
        "source_kind": session.get("source_kind") or "",
        "desktop_thread_id": session.get("desktop_thread_id") or "",
        "desktop_mode": session.get("desktop_mode") or "",
        "desktop_status": session.get("desktop_status") or "",
        "session_file": str(session_file),
    }


def session_preview_bundle(session: dict[str, Any]) -> dict[str, str]:
    entries = session.get("entries", [])
    seen: set[str] = set()
    user_texts: list[str] = []
    assistant_texts: list[str] = []
    fallback_texts: list[str] = []

    for entry in entries:
        entry_type = str(entry.get("type") or "").lower()
        text = clean_preview_text(entry.get("display"))
        if not text:
            continue
        key = re.sub(r"\s+", " ", text).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        if is_noisy_preview_text(text):
            continue
        if is_assistant_summary_type(entry_type):
            assistant_texts.append(text)
        elif is_user_history_type(entry_type):
            user_texts.append(text)
        else:
            fallback_texts.append(text)

    project = project_display_name(session.get("project"))
    entry_count = int(session.get("entry_count") or len(entries) or 0)
    user_preview = (user_texts[-1:] or user_texts[:1] or fallback_texts[-1:] or [""])[0]
    title_source = (user_texts[:1] or [user_preview] or [project])[0]
    title = compact_title("", title_source, limit=72).lstrip(" -") or project or "Legacy session"
    if assistant_texts:
        assistant_summary = compact_title("", assistant_texts[-1], limit=220).lstrip(" -")
        summary_kind = "assistant"
    else:
        focus = user_preview or ("" if title == project else title)
        assistant_summary = compact_title(
            "",
            f"{project or 'Project'} 的历史主要围绕「{focus}」。" if focus else f"{project or 'Project'} 的项目历史已导入，可以从这里继续。",
            limit=220,
        ).lstrip(" -")
        summary_kind = "local"

    if summary_kind == "local":
        if focus:
            assistant_summary = compact_title(
                "",
                f"{project or 'Project'} history mainly focuses on \"{focus}\".",
                limit=220,
            ).lstrip(" -")
        else:
            assistant_summary = compact_title(
                "",
                f"{project or 'Project'} history is imported and ready to continue.",
                limit=220,
            ).lstrip(" -")

    return {
        "title": title,
        "user_preview": user_preview,
        "assistant_summary": assistant_summary,
        "summary_kind": summary_kind,
    }


def clean_preview_text(value: Any) -> str:
    text = snippet(redact(str(value or "")), "", radius=180).strip()
    return re.sub(r"\s+", " ", text).strip()


def is_user_history_type(entry_type: str) -> bool:
    if "assistant" in entry_type or "tool" in entry_type:
        return False
    return (
        entry_type in {"legacy", "reconstructed_user_history"}
        or "user" in entry_type
        or "human" in entry_type
    )


def is_assistant_summary_type(entry_type: str) -> bool:
    return "assistant" in entry_type or "summary" in entry_type


def is_noisy_preview_text(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered:
        return True
    if lowered in {"/resume", "resume", "/clear", "/compact", "/init", "/maintain-assistant", "ok"}:
        return True
    if lowered.startswith("/") and len(lowered.split()) <= 1:
        return True
    if lowered.startswith("[tool_result]") or lowered.startswith("[tool_use:"):
        return True
    if "queue-operation" in lowered or "inputvalidationerror" in lowered:
        return True
    return "do_not_auto_resume" in lowered or "context limit reached" in lowered


def project_display_name(project: Any) -> str:
    text = str(project or "").strip()
    if not text or text == "unknown":
        return "Unknown"
    parts = [part for part in re.split(r"[\\/]+", text) if part]
    return parts[-1] if parts else text


def find_session(dest: Path, target: str) -> tuple[dict[str, Any], Path]:
    target_text = str(target or "").strip()
    if not target_text:
        raise SystemExit("session target is required")

    explicit_path = Path(target_text)
    if explicit_path.exists() and explicit_path.is_file():
        if explicit_path.suffix.lower() == ".json":
            data = read_json_safe(explicit_path)
            if data:
                return data, explicit_path
        if explicit_path.suffix.lower() == ".jsonl":
            for data, path in load_native_terminal_session_pairs():
                try:
                    if path.resolve() == explicit_path.resolve():
                        return data, path
                except OSError:
                    if str(path) == str(explicit_path):
                        return data, path

    lowered = target_text.lower()
    exact: list[tuple[dict[str, Any], Path]] = []
    fuzzy: list[tuple[dict[str, Any], Path, int, int]] = []
    for data, path in iter_all_sessions(dest):
        session_id = str(data.get("session_id") or "")
        project = str(data.get("project") or "")
        if session_id == target_text or session_id.lower().startswith(lowered):
            exact.append((data, path))
            continue
        haystack = f"{project}\n" + "\n".join(str(entry.get("display") or "") for entry in data.get("entries", [])[-20:])
        if lowered in haystack.lower():
            stub_penalty = 0 if session_is_resume_stub(data, "") else 1
            fuzzy.append((data, path, stub_penalty, int(data.get("last_timestamp") or 0)))

    if exact:
        exact.sort(key=lambda item: int(item[0].get("last_timestamp") or 0), reverse=True)
        return exact[0]
    if fuzzy:
        fuzzy.sort(key=lambda item: (item[2], item[3]), reverse=True)
        data, path, _, _ = fuzzy[0]
        return data, path

    raise SystemExit(f"legacy session not found: {target_text}")

def session_is_resume_stub(session: dict[str, Any], preview: str) -> bool:
    entries = session.get("entries", [])
    if int(session.get("entry_count") or len(entries) or 0) > 4:
        return False
    text_parts = [
        str(entry.get("display") or "").strip().lower()
        for entry in entries
        if str(entry.get("display") or "").strip()
    ]
    preview_text = preview.strip().lower()
    if preview_text == "/resume":
        return True
    return bool(text_parts) and all(part in {"/resume", "resume"} for part in text_parts)


def trim_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 15)].rstrip() + "\n...[truncated]"


def search_rank(query: str, project: str, display: str, timestamp: Any) -> tuple[int, int]:
    lowered = query.lower()
    project_lower = project.lower()
    display_lower = display.lower()
    score = 0
    if lowered in project_lower:
        score += 10
    if not project.startswith("archived:"):
        score += 5
    if lowered in display_lower:
        score += 2
    return score, normalize_timestamp(timestamp)


def snippet(text: str, query: str, radius: int = 180) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    index = normalized.lower().find(query.lower())
    if index < 0:
        return normalized[: radius * 2]
    start = max(0, index - radius)
    end = min(len(normalized), index + len(query) + radius)
    return normalized[start:end]


def redact(text: str) -> str:
    out = text
    for pattern in SECRET_PATTERNS:
        out = pattern.sub(lambda match: match.group(1) + "[REDACTED]" if match.groups() else "[REDACTED]", out)
    return out


def safe_name(value: str, limit: int = 90) -> str:
    raw = value.strip()
    digest = hashlib.sha1(value.encode("utf-8", errors="replace")).hexdigest()[:10]
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", raw)
    name = name.strip("-._")
    if raw == name and name and len(name) <= limit:
        return name
    if not name or name.lower() in {"d", "e", "f", "c"}:
        name = "project"
    if len(name) > limit:
        name = f"{name[:limit - 11]}-{digest}"
    if not name.endswith(f"-{digest}"):
        name = f"{name[: max(1, limit - 11)]}-{digest}"
    return name


def read_json_safe(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


def read_history_meta() -> dict[str, Any]:
    candidates: list[Path] = []
    if os.environ.get("DREAMSEED_HISTORY_META"):
        candidates.append(Path(os.environ["DREAMSEED_HISTORY_META"]))
    if os.environ.get("DREAMSEED_CONFIG_DIR"):
        candidates.append(Path(os.environ["DREAMSEED_CONFIG_DIR"]) / "history.meta.json")
    if os.environ.get("DREAMSEED_LOCAL_ROOT"):
        candidates.append(Path(os.environ["DREAMSEED_LOCAL_ROOT"]) / "config" / "history.meta.json")
    candidates.append(ROOT / "config" / "history.meta.json")
    for path in candidates:
        data = read_json_safe(path)
        if isinstance(data, dict):
            return data
    return {"sessions": {}}


def history_meta_for(item: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    sessions = meta.get("sessions") if isinstance(meta, dict) else {}
    if not isinstance(sessions, dict):
        return {}
    ids = [
        str(item.get("session_id") or "").strip(),
        str(item.get("desktop_thread_id") or "").strip(),
    ]
    for item_id in ids:
        entry = sessions.get(item_id)
        if isinstance(entry, dict):
            return entry
    return {}


def history_meta_hidden(item: dict[str, Any], meta: dict[str, Any]) -> bool:
    entry = history_meta_for(item, meta)
    return bool(entry.get("hidden") or entry.get("archived"))


def apply_history_meta(item: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    entry = history_meta_for(item, meta)
    title = str(entry.get("title") or "").strip()
    if not title:
        return item
    next_item = dict(item)
    next_item["title"] = title
    next_item["preview"] = title
    next_item["user_preview"] = title
    if entry.get("last_opened_at"):
        next_item["last_opened_at"] = entry.get("last_opened_at")
    return next_item


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def print_json(data: Any) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))


if __name__ == "__main__":
    raise SystemExit(main())





