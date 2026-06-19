from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PATH_OR_DECISION_RE = re.compile(
    r"([A-Za-z]:\\[^\s]+|/[\w./-]+|[\w.-]+\.(py|js|mjs|json|ps1|md|toml|yaml|yml)|\b(decision|policy|root cause|workaround)\b)",
    re.IGNORECASE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="DreamSeed MemPalace bridge")
    parser.add_argument(
        "--mode",
        default="status",
        choices=["status", "doctor", "recall", "candidate", "evolve", "stop-hook"],
    )
    parser.add_argument("--query", default="")
    parser.add_argument("--transcript", default="")
    parser.add_argument("--hook-input", default="")
    args = parser.parse_args()

    ensure_mempalace_path()

    if args.mode == "doctor":
        return run_doctor()

    palace_path = Path(
        os.environ.get("MEMPALACE_PATH")
        or os.environ.get("DREAMSEED_MEMORY_DIR")
        or ".dreamseed-memory"
    )
    wing = os.environ.get("MEMPALACE_WING") or Path.cwd().name or "dreamseed"

    if args.mode == "status":
        from mempalace_evolve.sdk import MemPalace

        palace = MemPalace(palace_path, wing=wing)
        try:
            stats = palace.stats()
            print_json({"ok": True, "path": str(palace.path), "wing": palace.wing, "stats": stats})
        except Exception as exc:
            print_json(
                {
                    "ok": False,
                    "path": str(palace.path),
                    "wing": palace.wing,
                    "error": str(exc),
                    "hint": "MemPalace loaded, but chromadb/vector storage is not ready. Run scripts/install-python-deps.ps1.",
                }
            )
            return 1
        return 0

    if args.mode == "recall":
        if not args.query:
            print_json({"ok": False, "error": "missing --query"})
            return 2
        from mempalace_evolve.sdk import MemPalace

        palace = MemPalace(palace_path, wing=wing)
        print_json({"ok": True, "results": palace.recall(args.query, limit=8)})
        return 0

    if args.mode in ("candidate", "evolve"):
        transcript = read_transcript(args.transcript, args.hook_input)
        if not transcript or len(transcript.strip()) < 50:
            print_json({"ok": True, "status": "skipped", "reason": "no usable transcript"})
            return 0
        candidate = write_memory_candidate(
            transcript=transcript,
            transcript_path=args.transcript or find_transcript_path(args.hook_input),
            source="manual-evolve" if args.mode == "evolve" else "manual-candidate",
            wing=wing,
        )
        print_json(
            {
                "ok": True,
                "status": "candidate-written",
                "candidate": candidate,
                "policy": "review required before MemPalace promotion",
            }
        )
        return 0

    if args.mode == "stop-hook":
        transcript_path = args.transcript or find_transcript_path(args.hook_input)
        transcript = read_transcript(transcript_path, args.hook_input)
        if not transcript or len(transcript.strip()) < 50:
            print_json({"ok": True, "status": "skipped", "reason": "no usable transcript"})
            return 0

        candidate = write_memory_candidate(
            transcript=transcript,
            transcript_path=transcript_path,
            source="stop-hook",
            wing=wing,
        )
        print_json(
            {
                "ok": True,
                "status": "candidate-written",
                "candidate": candidate,
                "policy": "Stop hook writes candidates only; use memory_review.py apply then memory_promote.py promote-reviewed.",
            }
        )
        return 0

    return 2


def candidate_root() -> Path:
    root = (
        os.environ.get("DREAMSEED_MEMORY_CANDIDATES_DIR")
        or os.environ.get("DREAMSEED_CANDIDATE_DIR")
        or candidate_root_from_local_root()
        or str(Path.cwd() / ".dreamseed-memory-candidates")
    )
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    (path / "reviewed").mkdir(exist_ok=True)
    (path / "rejected").mkdir(exist_ok=True)
    (path / "promoted").mkdir(exist_ok=True)
    return path


def candidate_root_from_local_root() -> str:
    local_root = os.environ.get("DREAMSEED_LOCAL_ROOT")
    if not local_root:
        return ""
    return str(Path(local_root) / "memory-candidates")


def write_memory_candidate(
    transcript: str,
    transcript_path: str = "",
    source: str = "stop-hook",
    wing: str = "dreamseed",
) -> dict[str, Any]:
    text = normalize_for_candidate(transcript)
    score, reasons, scores = score_candidate(text)
    now = datetime.now(timezone.utc).isoformat()
    digest = hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()
    candidate = {
        "id": f"memory-candidate-{digest[:16]}",
        "created_at": now,
        "source": source,
        "wing": wing,
        "score": score,
        "candidate_scores": scores,
        "reasons": reasons,
        "promotion_policy": "manual-review-required",
        "allowed_promotion_path": "memory_review.py apply -> reviewed/ -> memory_promote.py promote-reviewed",
        "source_transcript": transcript_path or None,
        "summary": summarize_candidate_text(text),
        "text": text[:6000],
        "hash": digest,
    }
    out = candidate_root() / f"{candidate['id']}.json"
    out.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(out), "id": candidate["id"], "score": score, "scores": scores, "reasons": reasons}


def normalize_for_candidate(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def summarize_candidate_text(text: str, limit: int = 500) -> str:
    return normalize_for_candidate(text)[:limit]


def score_candidate(text: str) -> tuple[float, list[str], dict[str, float]]:
    lowered = text.lower()
    reasons: list[str] = []

    scores = {
        "stability": signal_score(
            lowered,
            ["prefer", "preference", "稳定偏好", "用户偏好", "以后", "总是", "默认", "不要", "需要记住", "always", "never"],
        ),
        "specificity": min(1.0, 0.15 + 0.17 * len(PATH_OR_DECISION_RE.findall(text))),
        "reuse_value": signal_score(
            lowered,
            ["error", "failed", "failure", "错误模式", "报错", "根因", "修复", "workaround", "root cause"],
        ),
        "pollution_risk": 0.0,
        "decision_value": signal_score(
            lowered,
            ["decision", "项目决策", "决定", "架构", "路径", "配置", "policy", "迁移", "部署", "只允许"],
        ),
    }

    if scores["stability"] > 0:
        reasons.append("stable preference")
    if scores["decision_value"] > 0:
        reasons.append("project decision")
    if scores["reuse_value"] > 0:
        reasons.append("error pattern")

    noisy_patterns = [
        "many tool calls; checkpoint before compact",
        "checkpoint before compact",
        "generic checkpoint",
        "用户要求继续",
        "继续",
        "status update",
        "output exactly: ok",
        "reply exactly: ok",
        "只回复ok",
        "只回复 ok",
        "临时调试",
    ]
    if any(pattern in lowered for pattern in noisy_patterns):
        scores["pollution_risk"] += 0.8
        reasons.append("generic checkpoint/noisy candidate")
    if len(text) > 12000 or text.count("\n") > 220:
        scores["pollution_risk"] += 0.35
        reasons.append("long transcript")
    if len(text) < 120:
        scores["pollution_risk"] += 0.25
        reasons.append("short transcript")

    scores = {key: round(min(1.0, max(0.0, value)), 3) for key, value in scores.items()}
    score = round(
        0.22 * scores["stability"]
        + 0.18 * scores["specificity"]
        + 0.24 * scores["reuse_value"]
        + 0.24 * scores["decision_value"]
        + 0.12
        - 0.35 * scores["pollution_risk"],
        2,
    )
    score = max(0.05, min(0.95, score))
    if not reasons:
        reasons.append("low-signal transcript")
    return score, reasons, scores


def signal_score(text: str, needles: list[str]) -> float:
    hits = sum(1 for needle in needles if needle.lower() in text)
    if hits == 0:
        return 0.0
    return min(1.0, 0.35 + hits * 0.18)


def ensure_mempalace_path() -> None:
    for value in (
        os.environ.get("DREAMSEED_MEMPALACE_SRC", ""),
        os.environ.get("DREAMSEED_PYTHON_SITE", ""),
    ):
        if value and Path(value).exists() and value not in sys.path:
            sys.path.insert(0, value)


def run_doctor() -> int:
    ensure_mempalace_path()
    try:
        from mempalace_evolve.doctor import run_doctor as doctor

        return 0 if doctor() else 1
    except Exception as exc:
        print_json({"ok": False, "error": str(exc)})
        return 1


def read_text(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return Path(path).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def read_transcript(transcript_path: str = "", hook_input_path: str = "") -> str:
    if transcript_path and Path(transcript_path).exists():
        return normalize_transcript(read_text(transcript_path))

    hook = read_hook_input(hook_input_path)
    for key in ("transcript_path", "transcriptPath", "agent_transcript_path", "agentTranscriptPath"):
        value = hook.get(key)
        if isinstance(value, str) and Path(value).exists():
            return normalize_transcript(read_text(value))

    for env_key in ("DREAMSEED_TRANSCRIPT_PATH", "TRANSCRIPT_PATH"):
        value = os.environ.get(env_key)
        if value and Path(value).exists():
            return normalize_transcript(read_text(value))

    latest = latest_session_jsonl()
    if latest:
        return normalize_transcript(read_text(latest))

    if hook:
        return json.dumps(hook, ensure_ascii=False)
    return ""


def read_hook_input(path: str = "") -> dict[str, Any]:
    raw = ""
    if path and Path(path).exists():
        raw = read_text(path)
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"input": parsed}
    except json.JSONDecodeError:
        return {"raw": raw}


def find_transcript_path(hook_input_path: str = "") -> str:
    hook = read_hook_input(hook_input_path)
    for key in ("transcript_path", "transcriptPath", "agent_transcript_path", "agentTranscriptPath"):
        value = hook.get(key)
        if isinstance(value, str) and Path(value).exists():
            return value
    latest = latest_session_jsonl()
    return str(latest) if latest else ""


def latest_session_jsonl() -> Path | None:
    roots: list[Path] = []
    config_dir = os.environ.get("DREAMSEED_CONFIG_DIR")
    if config_dir:
        roots.append(Path(config_dir) / "projects")
    roots.append(Path.home() / ".dreamseed" / "projects")
    candidates: list[Path] = []
    for root in roots:
        if root.exists():
            candidates.extend(root.rglob("*.jsonl"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def normalize_transcript(raw: str) -> str:
    lines: list[str] = []
    for line in raw.splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            msg = json.loads(text)
        except json.JSONDecodeError:
            lines.append(text)
            continue
        role = msg.get("role") or msg.get("type") or "event"
        content = msg.get("content") or msg.get("message", {}).get("content", "")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(str(block.get("text") or block.get("content") or ""))
            content = "\n".join(p for p in parts if p)
        if content:
            lines.append(f"{role}: {content}")
    return "\n\n".join(lines) if lines else raw


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
