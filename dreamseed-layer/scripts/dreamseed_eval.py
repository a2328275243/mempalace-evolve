from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_ROOT = ROOT / "logs" / "evals"


SUITES: dict[str, list[list[str]]] = {
    "smoke": [
        ["node", "bin/dreamseed-agent.js", "--help"],
        ["node", "bin/dreamseed-agent.js", "doctor", "context", "--json"],
        ["node", "bin/dreamseed-agent.js", "doctor", "mcp", "--json"],
        ["node", "bin/dreamseed-agent.js", "doctor", "hooks", "--json"],
        ["node", "bin/dreamseed-agent.js", "approval", "audit", "--json"],
        ["node", "bin/dreamseed-agent.js", "approval", "check", "--tool", "Bash", "--command", "git status --short", "--json"],
        ["node", "bin/dreamseed-agent.js", "memory", "audit", "--json"],
        ["node", "bin/dreamseed-agent.js", "mcp", "list", "--json"],
        ["node", "bin/dreamseed-agent.js", "desktop", "--smoke"],
        ["node", "bin/dreamseed-agent.js", "desktop", "--render-smoke"],
    ],
    "memory": [
        ["node", "bin/dreamseed-agent.js", "memory", "audit", "--json"],
        ["node", "bin/dreamseed-agent.js", "memory", "candidates", "--json"],
    ],
    "mcp": [
        ["node", "bin/dreamseed-agent.js", "mcp", "list", "--json"],
        ["node", "bin/dreamseed-agent.js", "mcp", "candidates", "--json"],
        ["node", "bin/dreamseed-agent.js", "doctor", "mcp", "--json"],
    ],
    "provider": [
        ["node", "bin/dreamseed-agent.js", "provider", "status"],
        ["node", "bin/dreamseed-agent.js", "provider", "templates", "--json"],
    ],
    "release": [
        ["node", "bin/dreamseed-agent.js", "--help"],
        ["node", "bin/dreamseed-agent.js", "provider", "status"],
        ["node", "bin/dreamseed-agent.js", "history", "status"],
        ["node", "bin/dreamseed-agent.js", "evolve", "status"],
        ["node", "bin/dreamseed-agent.js", "doctor", "context", "--json"],
        ["node", "bin/dreamseed-agent.js", "doctor", "mcp", "--json"],
        ["node", "bin/dreamseed-agent.js", "doctor", "hooks", "--json"],
        ["node", "bin/dreamseed-agent.js", "approval", "audit", "--json"],
        ["node", "bin/dreamseed-agent.js", "approval", "check", "--tool", "Bash", "--command", "git status --short", "--json"],
        [sys.executable, "scripts/memory_review.py", "list", "--limit", "5"],
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/dreamseed-audit.ps1"],
        [sys.executable, "scripts/brand_audit.py", "scan", "--strict", "--json"],
        ["node", "bin/dreamseed-agent.js", "desktop", "--smoke"],
        ["node", "bin/dreamseed-agent.js", "desktop", "--render-smoke"],
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/package-dreamseed.ps1"],
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/package-dreamseed.ps1", "-Mode", "full-local-kit"],
        [sys.executable, "scripts/dreamseed_eval.py", "zip-check"],
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DreamSeed evaluation suites.")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run")
    run.add_argument("--suite", choices=["smoke", "release", "memory", "mcp", "provider", "all"], default="smoke")
    run.add_argument("--json", action="store_true")
    run.add_argument("--timeout", type=int, default=180)
    zip_check = sub.add_parser("zip-check")
    zip_check.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.command:
        args.command = "run"
        args.suite = "smoke"
        args.json = False
        args.timeout = 180
    if args.command == "zip-check":
        result = zip_check_releases()
        if args.json:
            print_json(result)
        else:
            print_report({"ok": result["ok"], "results": [{"ok": result["ok"], "suite": "zip", "command": "zip-check"}], "artifactDir": str(resolve_log_root())})
        return 0 if result["ok"] else 1
    if args.command != "run":
        return 2

    result = run_suite(args.suite, timeout=args.timeout)
    if args.json:
        print_json(result)
    else:
        print_report(result)
    return 0 if result["ok"] else 1


def run_suite(name: str, timeout: int) -> dict[str, Any]:
    names = ["smoke", "memory", "mcp", "provider", "release"] if name == "all" else [name]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    log_root = resolve_log_root()
    results = []
    for suite_name in names:
        for command in SUITES[suite_name]:
            results.append(run_command(suite_name, command, timeout=timeout, run_id=run_id, log_root=log_root))
    ok = all(item["ok"] for item in results)
    return {"ok": ok, "suite": name, "runId": run_id, "results": results, "artifactDir": str(log_root / run_id)}


def run_command(suite: str, command: list[str], timeout: int, run_id: str, log_root: Path) -> dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "DREAMSEED_QUIET": "1"}
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
        )
        item = {
            "ok": completed.returncode == 0,
            "suite": suite,
            "command": " ".join(command),
            "exitCode": completed.returncode,
            "startedAt": started,
            "finishedAt": datetime.now(timezone.utc).isoformat(),
            "stdout": completed.stdout[-2000:],
            "stderr": completed.stderr[-2000:],
        }
    except subprocess.TimeoutExpired as exc:
        item = {
            "ok": False,
            "suite": suite,
            "command": " ".join(command),
            "exitCode": None,
            "startedAt": started,
            "finishedAt": datetime.now(timezone.utc).isoformat(),
            "stdout": str(exc.stdout or "")[-2000:],
            "stderr": f"timeout after {timeout}s",
        }
    if not item["ok"]:
        write_failure_artifact(run_id, item, log_root)
    return item


def resolve_log_root() -> Path:
    explicit = os.environ.get("DREAMSEED_EVAL_LOG_DIR", "")
    candidates = [Path(explicit)] if explicit else []
    candidates.extend([DEFAULT_LOG_ROOT, Path(tempfile.gettempdir()) / "dreamseed-evals" / root_fingerprint()])
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except Exception:
            continue
    fallback = Path(tempfile.gettempdir()) / "dreamseed-evals" / root_fingerprint()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def root_fingerprint() -> str:
    import hashlib

    return hashlib.sha256(str(ROOT).encode("utf-8", errors="replace")).hexdigest()[:12]


def write_failure_artifact(run_id: str, item: dict[str, Any], log_root: Path) -> None:
    try:
        directory = log_root / run_id
        directory.mkdir(parents=True, exist_ok=True)
        name = item["command"].replace("/", "_").replace("\\", "_").replace(" ", "_")[:80]
        (directory / f"{name}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        item["artifactWriteError"] = str(exc)


def zip_check_releases() -> dict[str, Any]:
    import zipfile

    dist = ROOT / "dist"
    package = read_json(ROOT / "package.json") or {}
    version = package.get("version", "0.1.0")
    zips = [
        dist / f"dreamseed-code-{version}-source.zip",
        dist / "dreamseed-code-full-local-kit.zip",
    ]
    required = [
        "bin/dreamseed-agent.js",
        "bin/dreamseed-desktop.cmd",
        "config/approval.policy.json",
        "config/mcp.registry.json",
        "docs/approval-gate.md",
        "docs/ecosystem-candidates.md",
        "docs/task-contracts.md",
        "docs/release-checklist.md",
        "scripts/approval_gate.py",
        "scripts/dreamseed-approval-gate.ps1",
        "scripts/dreamseed_desktop.mjs",
        "scripts/desktop_render_smoke.mjs",
        "desktop/electron-main.mjs",
        "desktop/shared-history.mjs",
        "desktop/preload.cjs",
        "desktop/index.html",
        "desktop/desktop.js",
        "desktop/desktop.css",
        "scripts/dreamseed_eval.py",
        "scripts/dreamseed_memory_cli.py",
        "scripts/dreamseed_compact_cache.py",
        "scripts/install-dreamseed.ps1",
        "scripts/uninstall-dreamseed.ps1",
        "scripts/provider_tools.py",
        ".dreamseed/tasks/release-check.json",
    ]
    token_checks = {
        "desktop/electron-main.mjs": ["persistDesktopHistorySession", "./shared-history.mjs", "randomUUID", "writeDesktopHistorySession", "task:cancel", "task:output", "provider:diagnose", "desktop:tasks:list", "desktop:tasks:upsert", "desktop:settings:update", "runningTaskProcesses", "terminateChildProcess", "stdio: ['ignore', 'pipe', 'pipe']"],
        "bin/dreamseed-agent.js": ["preferredLocalProviderConfigPath", "inferLocalRootFromRepo", "DREAMSEED_LOCAL_ROOT", "DREAMSEED_CONFIG_DIR", "compact-cache", "provider diagnose", "defaultProviderSystemPrefix"],
        "desktop/shared-history.mjs": ["writeDesktopHistorySession", "writeDesktopNativeResumeBridge", "dreamseed-desktop-resume-bridge", "nativeResumePath", "nativeSanitizePath", "source_kind", "desktop_thread_id"],
        "scripts/desktop_render_smoke.mjs": ["BrowserWindow", "history-project-group", "history-time-bucket", "conversationItems", "sidebarScroll", "modelChip", "providerPills", "addProviderPill", "newModelDraft", "newModelDrawer", "savedModelVisible", "provider:save", "taskRunner", "taskCards", "taskDone", "task:run", "task:cancel", "workbench", "reviewFiles", "diffLines", "DREAMSEED_DESKTOP_RENDER_SCREENSHOT", "capturePage"],
        "desktop/preload.cjs": ["allowedInvokeChannels", "contextBridge", "ipcRenderer.invoke", "task:cancel", "provider:diagnose", "task:output"],
        "desktop/index.html": ["app-shell", "messageList", "taskRunnerPanel", "taskQueueList", "taskConcurrencyInput", "artifactTimelinePanel", "diagnoseModelBtn", "historySessionList", "workbenchSplit", "terminalSplitForm", "reviewSplit", "reviewDiffOutput", "providerQuickList", "modelCountLabel", "panel-models", "modelStatusBtn", "sidebar-scroll", "section-actions", "sidebar-nav", "nav-command", "active-context-card", "sidebarActiveProject", "sidebarActiveModel", "settings.title", "project-list-hidden"],
        "desktop/desktop.js": ["renderHistoryConversation", "normalizeHistorySessions", "groupedHistorySessions", "bucketHistorySessions", "renderTaskRunner", "renderArtifactsTimeline", "pumpTaskQueue", "runQueuedTask", "cancelTask", "handleTaskOutput", "persistTask", "updateTaskConcurrency", "diagnoseProviders", "MAX_CONCURRENT_DESKTOP_TASKS", "renderProviderQuickList", "appendAddProviderPill", "switchProviderQuick", "startNewModel", "sortedProviders", "renderWorkbench", "toggleWorkbenchPanel", "makeThreadTitle", "renderDiffReview", "diffOutputHtml", "summaryLabelForSession", "isUsefulHistorySession", "showProjectHome", "projectGroupCountLabel", "cleanProjectOpeningLine", "cleanSessionOpeningLine", "projectExcerptMessages", "source_kind", "dedupeHistoryEntries", "roleForHistory", "messageList", "providerCapabilityLabel", "settings.title", "context.current"],
        "desktop/desktop.css": [".app-shell", "drawer-open", "history-project-group", "history-time-bucket", ".task-runner-panel", ".task-card", ".task-output", ".task-concurrency", ".artifact-timeline-panel", ".artifact-item", ".provider-quick-list", ".provider-pill", ".add-provider-pill", ".model-tags", ".workbench-split", ".review-diff-output", ".diff-line b", ".diff-line.add", "active-project", ".message-list", ".conversation-item", ".drawer", ".model-status-chip", ".sidebar-scroll", "scrollbar-gutter", "section-actions", "sidebar-nav", "nav-command", "active-context-card", "project-list-hidden"],
    }
    legacy_namespace = r"\." + "claude"
    forbidden_patterns = [
        r"(^|/)legacy-history(/|$)",
        r"(^|/)memory-candidates(/|$)",
        r"(^|/)self-evolve-candidates(/|$)",
        r"(^|/)self-evolve-backups(/|$)",
        r"(^|/)logs(/|$)",
        r"(^|/)cache(/|$)",
        r"(^|/)\.cache(/|$)",
        r"(^|/)\.dreamseed-runtime(/|$)",
        r"(^|/)providers\.local\.json$",
        r"(^|/)__pycache__(/|$)",
        r"\.pyc$",
        r"(^|/)node_modules(/|$)",
        rf"(^|/){legacy_namespace}(/|$)",
    ]
    results = []
    failures = []
    for zip_path in zips:
        item = {
            "path": str(zip_path),
            "exists": zip_path.exists(),
            "missingRequired": [],
            "forbidden": [],
            "tokenFailures": [],
            "secretFailures": [],
        }
        if not zip_path.exists():
            failures.append(f"missing zip: {zip_path}")
            results.append(item)
            continue
        with zipfile.ZipFile(zip_path) as archive:
            names = [name.replace("\\", "/") for name in archive.namelist()]
            normalized_to_raw = {name.replace("\\", "/"): name for name in archive.namelist()}
            for rel, tokens in token_checks.items():
                raw_name = normalized_to_raw.get(rel)
                if not raw_name:
                    item["tokenFailures"].append(f"{rel}: missing")
                    continue
                text = archive.read(raw_name).decode("utf-8", errors="replace")
                missing_tokens = [token for token in tokens if token not in text]
                if missing_tokens:
                    item["tokenFailures"].append(f"{rel}: missing tokens {', '.join(missing_tokens)}")
            secret_pattern = re.compile(r"ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}")
            for raw_name in archive.namelist():
                name = raw_name.replace("\\", "/")
                if not re.search(r"\.(json|js|mjs|cjs|py|ps1|md|txt|cmd|html|css)$", name):
                    continue
                info = archive.getinfo(raw_name)
                if info.file_size > 2_000_000:
                    continue
                text = archive.read(raw_name).decode("utf-8", errors="replace")
                if secret_pattern.search(text):
                    item["secretFailures"].append(name)
        for rel in required:
            if rel not in names:
                item["missingRequired"].append(rel)
        for name in names:
            if any(re.search(pattern, name) for pattern in forbidden_patterns):
                item["forbidden"].append(name)
        if item["missingRequired"] or item["forbidden"] or item["tokenFailures"] or item["secretFailures"]:
            failures.append(f"zip check failed: {zip_path.name}")
        item["entryCount"] = len(names)
        results.append(item)
    return {"ok": not failures, "results": results, "failures": failures}


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def print_report(result: dict[str, Any]) -> None:
    print("DreamSeed eval " + ("passed" if result["ok"] else "failed"))
    for item in result["results"]:
        marker = "OK" if item["ok"] else "FAIL"
        print(f"  {marker} [{item['suite']}] {item['command']}")
    if not result["ok"]:
        print("Artifacts: " + result["artifactDir"])


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
