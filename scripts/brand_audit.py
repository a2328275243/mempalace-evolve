#!/usr/bin/env python3
"""Scan DreamSeed source for legacy brand strings.

The scanner is intentionally conservative: it reports user-visible legacy
branding separately from compatibility/history references so cleanup can happen
without breaking resume import, provider compatibility, or archived context.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SCRIPT_DIR.parent
DEFAULT_ALLOWLIST = DEFAULT_ROOT / "config" / "brand_allowlist.json"

DEFAULT_SCAN_PATHS = [
    "bin",
    "config",
    "docs",
    "manager",
    "scripts",
    ".dreamseed",
    "README.md",
    "DREAMSEED.md",
    "AGENTS.md",
    "package.json",
    ".mcp.json",
    "requirements-dreamseed.txt",
    "restored-src/src/constants",
    "restored-src/src/commands",
    "restored-src/src/components",
    "restored-src/src/screens",
    "restored-src/src/entrypoints",
]

TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".mjs",
    ".md",
    ".ps1",
    ".py",
    ".ts",
    ".tsx",
    ".txt",
    ".yml",
    ".yaml",
}

SEARCH_PATTERN = re.compile(
    r"Claude Code|CLAUDE\.md|Claude\b|\bclaude\b"
)

VISIBLE_FORBIDDEN_PATTERNS = [
    re.compile(r"Welcome to Claude Code", re.I),
    re.compile(r"Claude Code v", re.I),
    re.compile(r"Usage:\s*claude\b", re.I),
    re.compile(r"\bclaude\s+\[options\]", re.I),
    re.compile(r"Run /init.+CLAUDE\.md", re.I),
    re.compile(r"create a CLAUDE\.md", re.I),
    re.compile(r"CLAUDE\.md auto-discovery", re.I),
    re.compile(r"Claude in Chrome", re.I),
    re.compile(r"interrupting Claude", re.I),
    re.compile(r"instructions for Claude", re.I),
    re.compile(r"tell Claude", re.I),
    re.compile(r"Claude Code needs", re.I),
    re.compile(r"Claude's current work", re.I),
    re.compile(r"Welcome back!", re.I),
    re.compile(r"Tips for getting started", re.I),
]

ALLOWED_COMPAT_PATHS = [
    "scripts/import_claude_history.py",
    "scripts/import_ccswitch_provider.py",
]

ALLOWED_COMPAT_MARKERS = [
    "CLAUDE_CONFIG_DIR",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_MODEL",
    "Anthropic-compatible",
    "legacy_namespace",
    "app_type",
    "claude desktop",
    "claude_desktop_config",
    "claude-cli.js",
    '"claude"',
    "'claude'",
    "." + "claude",
    "legacy claude",
    "legacy Claude Code",
    "legacy `claude`",
]

ALLOWED_LEGACY_MARKERS = [
    "legacy history",
    "old claude code history",
    "imported claude code",
    "legacy claude code",
    "legacy-claude-code",
    "claude-code",
    "claude code",
    "import_claude_history.py",
]

ALLOWED_EXTERNAL_MARKERS = [
    "https://",
    "http://",
    "github.com",
    "code." + "claude.com",
    "@anthropic-ai/claude-code",
]

SKIP_DIR_NAMES = {
    ".git",
    ".dreamseed-memory",
    ".dreamseed-runtime",
    "__pycache__",
    "node_modules",
    "legacy-history",
    "memory-candidates",
    "self-evolve-backups",
    "self-evolve-candidates",
}

SKIP_FILE_NAMES = {
    "brand_allowlist.json",
    "brand_audit.py",
}

ALLOWLIST_CATEGORIES = {
    "allowed_compat",
    "allowed_external_reference",
    "allowed_legacy_history",
}


@dataclass
class Finding:
    category: str
    path: str
    line: int
    term: str
    text: str
    allowlist_reason: str | None = None


def iter_files(root: Path, scan_paths: Iterable[str]) -> Iterable[Path]:
    for rel in scan_paths:
        target = (root / rel).resolve()
        if not target.exists():
            continue
        if target.is_file():
            if is_text_candidate(target):
                yield target
            continue
        for current_root, dirs, files in os.walk(target):
            dirs[:] = [name for name in dirs if name not in SKIP_DIR_NAMES]
            for name in files:
                if name in SKIP_FILE_NAMES:
                    continue
                path = Path(current_root) / name
                if is_text_candidate(path):
                    yield path


def is_text_candidate(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    try:
        return path.stat().st_size <= 4_000_000
    except OSError:
        return False


def rel_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def classify(relative_path: str, line_text: str) -> str:
    normalized_path = relative_path.replace("\\", "/")
    lower_path = normalized_path.lower()
    lower_line = line_text.lower()
    stripped = line_text.strip()

    if any(pattern.search(line_text) for pattern in VISIBLE_FORBIDDEN_PATTERNS):
        return "user_visible_forbidden"

    if any(marker.lower() in lower_line for marker in ALLOWED_EXTERNAL_MARKERS):
        return "allowed_external_reference"

    if any(lower_path.endswith(path.lower()) for path in ALLOWED_COMPAT_PATHS):
        return "allowed_compat"

    if any(marker.lower() in lower_line for marker in ALLOWED_COMPAT_MARKERS):
        return "allowed_compat"

    if any(marker in lower_line for marker in ALLOWED_LEGACY_MARKERS):
        return "allowed_legacy_history"

    if lower_path.startswith("restored-src/src/"):
        if is_import_or_module_reference(stripped):
            return "allowed_compat"
        if stripped.startswith(("//", "*")):
            return "needs_review"
        if looks_like_visible_source_text(stripped):
            return "user_visible_forbidden"
        return "allowed_compat"

    if lower_path.startswith(("bin/", "docs/", "manager/", ".dreamseed/")):
        return "user_visible_forbidden"

    return "needs_review"


def is_import_or_module_reference(line_text: str) -> bool:
    return (
        line_text.startswith("import ")
        or line_text.startswith("export ")
        or " from '" in line_text
        or ' from "' in line_text
        or "require('" in line_text
        or 'require("' in line_text
    )


def looks_like_visible_source_text(line_text: str) -> bool:
    if not any(quote in line_text for quote in ("'", '"', "`")):
        return False
    lowered = line_text.lower()
    visible_markers = [
        "text:",
        "message:",
        "description:",
        "title:",
        "label:",
        "content:",
        "placeholder",
        "console.log",
        "write(",
        "notification",
        "prompt",
    ]
    if any(marker in lowered for marker in visible_markers):
        return True
    return any(term in lowered for term in ("claude code", "claude ", " claude", "claude.md", "/btw"))


def scan(root: Path, scan_paths: Iterable[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(set(iter_files(root, scan_paths))):
        relative = rel_path(root, path)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_number, line_text in enumerate(content.splitlines(), start=1):
            for match in SEARCH_PATTERN.finditer(line_text):
                text = line_text.strip()
                findings.append(
                    Finding(
                        category=classify(relative, text),
                        path=relative,
                        line=line_number,
                        term=match.group(0),
                        text=text[:240],
                    )
                )
    return findings


def load_allowlist(path: Path | None) -> list[dict]:
    if path is None:
        return []
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"failed to read brand allowlist {path}: {error}")

    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise SystemExit(f"brand allowlist entries must be a list: {path}")

    normalized = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise SystemExit(f"brand allowlist entry {index} must be an object")
        category = entry.get("category")
        if category not in ALLOWLIST_CATEGORIES:
            raise SystemExit(
                f"brand allowlist entry {index} has invalid category {category!r}"
            )
        path_pattern = str(entry.get("path") or "*").replace("\\", "/")
        contains = entry.get("contains", [])
        if isinstance(contains, str):
            contains = [contains]
        if not isinstance(contains, list) or not all(isinstance(item, str) for item in contains):
            raise SystemExit(f"brand allowlist entry {index} contains must be a string or string list")
        normalized.append(
            {
                "path": path_pattern,
                "contains": contains,
                "term": str(entry.get("term") or ""),
                "category": category,
                "reason": str(entry.get("reason") or "reviewed allowlist entry"),
            }
        )
    return normalized


def apply_allowlist(findings: list[Finding], entries: list[dict]) -> None:
    if not entries:
        return
    for finding in findings:
        if finding.category != "needs_review":
            continue
        for entry in entries:
            if not allowlist_entry_matches(finding, entry):
                continue
            finding.category = entry["category"]
            finding.allowlist_reason = entry["reason"]
            break


def allowlist_entry_matches(finding: Finding, entry: dict) -> bool:
    path = finding.path.replace("\\", "/")
    if not fnmatch.fnmatch(path, entry["path"]):
        return False
    if entry["term"] and entry["term"] != finding.term:
        return False
    contains = entry["contains"]
    if contains and not any(fragment in finding.text for fragment in contains):
        return False
    return True


def summarize(findings: list[Finding]) -> dict:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.category] = counts.get(finding.category, 0) + 1

    by_file: dict[str, int] = {}
    for finding in findings:
        if finding.category != "user_visible_forbidden":
            continue
        by_file[finding.path] = by_file.get(finding.path, 0) + 1

    return {
        "counts": counts,
        "total": len(findings),
        "forbidden_files": [
            {"path": path, "count": count}
            for path, count in sorted(by_file.items(), key=lambda item: (-item[1], item[0]))[:20]
        ],
        "findings": [asdict(finding) for finding in findings],
    }


def print_text_report(summary: dict) -> None:
    counts = summary["counts"]
    print("DreamSeed brand audit")
    print(f"  total matches: {summary['total']}")
    for category in sorted(counts):
        print(f"  {category}: {counts[category]}")
    if summary["forbidden_files"]:
        print("  top user-visible files:")
        for item in summary["forbidden_files"][:10]:
            print(f"    - {item['path']} ({item['count']})")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit DreamSeed source for legacy visible branding.")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="scan source files")
    scan_parser.add_argument("--root", default=str(DEFAULT_ROOT), help="DreamSeed source root")
    scan_parser.add_argument(
        "--allowlist",
        default=None,
        help="Brand allowlist JSON path. Defaults to <root>/config/brand_allowlist.json.",
    )
    scan_parser.add_argument("--no-allowlist", action="store_true", help="do not apply the brand allowlist")
    scan_parser.add_argument("--json", action="store_true", help="emit JSON")
    scan_parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when user-visible or unreviewed matches are found",
    )
    scan_parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="relative path to scan; may be repeated. Defaults to publish and UI source paths.",
    )
    scan_parser.add_argument(
        "--include-runtime",
        action="append",
        dest="runtime_paths",
        help="extra runtime file or directory to scan in addition to the source root",
    )

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.command not in (None, "scan"):
        raise SystemExit(f"unknown command: {args.command}")

    root = Path(getattr(args, "root", DEFAULT_ROOT)).resolve()
    paths = getattr(args, "paths", None) or DEFAULT_SCAN_PATHS
    findings = scan(root, paths)

    for runtime_path in getattr(args, "runtime_paths", None) or []:
        runtime = Path(runtime_path).resolve()
        if runtime.exists():
            findings.extend(scan(runtime.parent if runtime.is_file() else runtime, [runtime.name] if runtime.is_file() else ["."]))

    allowlist_path = None
    if not getattr(args, "no_allowlist", False):
        allowlist_path = Path(getattr(args, "allowlist", None) or (root / "config" / "brand_allowlist.json")).resolve()
    apply_allowlist(findings, load_allowlist(allowlist_path))

    summary = summarize(findings)
    if getattr(args, "json", False):
        print(json.dumps(summary, ensure_ascii=True, indent=2))
    else:
        print_text_report(summary)

    if getattr(args, "strict", False) and (
        summary["counts"].get("user_visible_forbidden", 0)
        or summary["counts"].get("needs_review", 0)
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
