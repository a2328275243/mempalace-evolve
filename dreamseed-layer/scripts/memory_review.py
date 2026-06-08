from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_DIR = Path(
    os.environ.get("DREAMSEED_MEMORY_CANDIDATES_DIR")
    or os.environ.get("DREAMSEED_CANDIDATE_DIR")
    or ROOT / "memory-candidates"
)
REVIEWED_DIR = CANDIDATE_DIR / "reviewed"
REJECTED_DIR = CANDIDATE_DIR / "rejected"


GOOD_KEYWORDS = [
    "稳定偏好",
    "用户偏好",
    "默认",
    "不要",
    "以后",
    "需要记住",
    "项目决策",
    "架构",
    "路径",
    "配置",
    "错误模式",
    "根因",
    "修复",
    "迁移",
    "部署",
    "policy",
    "decision",
    "preference",
    "error pattern",
]

NOISE_PATTERNS = [
    "many tool calls; checkpoint before compact",
    "checkpoint before compact",
    "generic checkpoint",
    "status update",
    "this session is being continued from a previous conversation",
    "<local-command-caveat>",
    "output exactly: ok",
    "reply exactly: ok",
    "用户要求继续",
    "继续",
    "只回复ok",
    "只回复 ok",
    "临时调试",
    "随便聊聊",
]

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{20,}",
    r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}",
]

PATH_OR_DECISION_RE = re.compile(
    r"([A-Za-z]:\\[^\s]+|/[\w./-]+|[\w.-]+\.(py|js|mjs|json|ps1|md|toml|yaml|yml)|\b(decision|policy|root cause|workaround)\b)",
    re.IGNORECASE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Review DreamSeed memory candidates")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List pending candidates")
    list_parser.add_argument("--limit", type=int, default=30)
    list_parser.add_argument("--all", action="store_true")
    list_parser.add_argument("--rejects", action="store_true", help="Show candidates that would be rejected")

    inspect_parser = sub.add_parser("inspect", help="Inspect one candidate")
    inspect_parser.add_argument("id")

    apply_parser = sub.add_parser("apply", help="Move acceptable candidates to reviewed/")
    apply_parser.add_argument("id", nargs="?", help="Candidate id or path; omit with --all")
    apply_parser.add_argument("--all", action="store_true", help="Review all pending candidates")
    apply_parser.add_argument("--min-score", type=float, default=0.55)
    apply_parser.add_argument("--verbose", action="store_true")

    reject_parser = sub.add_parser("reject", help="Move candidates to rejected/")
    reject_parser.add_argument("id", nargs="?", help="Candidate id or path; omit with --all-noisy")
    reject_parser.add_argument("--all-noisy", action="store_true", help="Reject all noisy or secret-bearing candidates")
    reject_parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()
    ensure_dirs()

    if args.command == "list":
        candidates = [candidate_summary(p) for p in pending_candidates()]
        if not args.rejects:
            candidates = [c for c in candidates if c["decision"]["action"] != "reject"]
        total = len(candidates)
        shown = candidates if args.all else candidates[: max(0, args.limit)]
        print_json({"ok": True, "total": total, "shown": len(shown), "pending": shown})
        return 0

    if args.command == "inspect":
        path = resolve_candidate(args.id)
        data = load_json(path)
        print_json({"ok": True, "candidate": data, "decision": review_decision(data), "path": str(path)})
        return 0

    if args.command == "apply":
        targets = pending_candidates() if args.all else [resolve_candidate(args.id)]
        results = [apply_candidate(path, min_score=args.min_score) for path in targets]
        print_json({"ok": True, **summarize_results(results, verbose=args.verbose)})
        return 0

    if args.command == "reject":
        targets = pending_candidates() if args.all_noisy else [resolve_candidate(args.id)]
        results = []
        for path in targets:
            data = load_json(path)
            decision = review_decision(data)
            if args.all_noisy and decision["action"] != "reject":
                results.append({"path": str(path), "status": "kept", "reason": decision["reason"]})
                continue
            results.append(move_with_review(path, REJECTED_DIR, "rejected", decision["reason"], decision))
        print_json({"ok": True, **summarize_results(results, verbose=args.verbose)})
        return 0

    return 2


def ensure_dirs() -> None:
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
    REVIEWED_DIR.mkdir(exist_ok=True)
    REJECTED_DIR.mkdir(exist_ok=True)


def pending_candidates() -> list[Path]:
    return sorted(
        p
        for p in CANDIDATE_DIR.glob("*.json")
        if p.is_file() and not p.name.startswith(".")
    )


def resolve_candidate(value: str | None) -> Path:
    if not value:
        raise SystemExit("candidate id/path required")
    path = Path(value)
    if path.exists():
        return path
    if not value.endswith(".json"):
        by_id = CANDIDATE_DIR / f"{value}.json"
        if by_id.exists():
            return by_id
    matches = list(CANDIDATE_DIR.glob(f"*{value}*.json"))
    if len(matches) == 1:
        return matches[0]
    raise SystemExit(f"candidate not found or ambiguous: {value}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def candidate_summary(path: Path) -> dict[str, Any]:
    data = load_json(path)
    decision = review_decision(data)
    return {
        "id": data.get("id") or path.stem,
        "score": decision["overall_score"],
        "raw_score": data.get("score"),
        "summary": data.get("summary", "")[:180],
        "decision": decision,
        "path": str(path),
    }


def review_decision(data: dict[str, Any]) -> dict[str, Any]:
    text = candidate_text(data)
    lowered = text.lower()
    visible = str(data.get("summary", "")) + " " + str(data.get("text", ""))
    scores = candidate_scores(data, text)
    overall = round(
        0.22 * scores["stability"]
        + 0.18 * scores["specificity"]
        + 0.24 * scores["reuse_value"]
        + 0.24 * scores["decision_value"]
        + 0.12 * safe_float(data.get("score"))
        - 0.35 * scores["pollution_risk"],
        3,
    )
    overall = max(0.0, min(1.0, overall))

    if any(re.search(pattern, text) for pattern in SECRET_PATTERNS):
        return decision("reject", "contains possible secret/token", scores, 0.0)
    if any(pattern in lowered for pattern in NOISE_PATTERNS):
        return decision("reject", "generic checkpoint or low-value chatter", scores, min(overall, 0.05))
    if looks_like_mojibake_or_empty_ack(visible):
        return decision("reject", "mojibake or empty acknowledgement", scores, min(overall, 0.05))
    if scores["pollution_risk"] >= 0.75:
        return decision("reject", "high pollution risk", scores, overall)

    has_good_signal = any(keyword.lower() in lowered for keyword in GOOD_KEYWORDS)
    durable_signal = max(scores["stability"], scores["reuse_value"], scores["decision_value"])
    if overall >= 0.65 and (has_good_signal or durable_signal >= 0.55):
        return decision("reviewed", "durable signal with sufficient score", scores, overall)
    if overall >= 0.78:
        return decision("reviewed", "high score", scores, overall)
    return decision("pending", "needs human review or stronger durable signal", scores, overall)


def candidate_text(data: dict[str, Any]) -> str:
    return " ".join(str(data.get(key, "")) for key in ("summary", "text", "source", "reasons", "review"))


def candidate_scores(data: dict[str, Any], text: str) -> dict[str, float]:
    lowered = text.lower()
    line_count = max(1, text.count("\n") + 1)
    stability = signal_score(
        lowered,
        [
            "稳定偏好",
            "用户偏好",
            "preference",
            "以后",
            "默认",
            "不要",
            "需要记住",
            "always",
            "never",
        ],
    )
    decision_value = signal_score(
        lowered,
        [
            "项目决策",
            "decision",
            "policy",
            "架构",
            "迁移",
            "部署",
            "配置",
            "保持",
            "只允许",
        ],
    )
    reuse_value = signal_score(
        lowered,
        [
            "错误模式",
            "error pattern",
            "root cause",
            "根因",
            "修复",
            "workaround",
            "failed",
            "failure",
        ],
    )
    specificity = min(1.0, 0.15 + 0.17 * len(PATH_OR_DECISION_RE.findall(text)))
    pollution = 0.0
    if any(pattern in lowered for pattern in NOISE_PATTERNS):
        pollution += 0.8
    if len(text) > 12000 or line_count > 220:
        pollution += 0.35
    if re.search(r"(?i)(debug log|trace dump|stack dump|raw output|stdout|stderr)", text):
        pollution += 0.25
    if len(text.strip()) < 80:
        pollution += 0.3
    if safe_float(data.get("score")) < 0.25:
        pollution += 0.1
    return {
        "stability": round(min(1.0, stability), 3),
        "specificity": round(min(1.0, specificity), 3),
        "reuse_value": round(min(1.0, reuse_value), 3),
        "pollution_risk": round(min(1.0, pollution), 3),
        "decision_value": round(min(1.0, decision_value), 3),
    }


def signal_score(text: str, needles: list[str]) -> float:
    hits = sum(1 for needle in needles if needle.lower() in text)
    if hits == 0:
        return 0.0
    return min(1.0, 0.35 + hits * 0.18)


def decision(action: str, reason: str, scores: dict[str, float], overall: float) -> dict[str, Any]:
    return {"action": action, "reason": reason, "scores": scores, "overall_score": round(overall, 3)}


def safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def looks_like_mojibake_or_empty_ack(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text).lower()
    if normalized in {"ok", "user:ok", "assistant:ok", "user:只回复okassistant:ok"}:
        return True
    if normalized.count("?") >= 8 and len(normalized) < 120:
        return True
    if "user:只回复ok" in normalized or normalized.endswith("assistant:ok"):
        return True
    mojibake_markers = ["鍙", "鐢", "绋", "閿", "璺", "淇"]
    return sum(1 for marker in mojibake_markers if marker in normalized) >= 3


def apply_candidate(path: Path, min_score: float = 0.55) -> dict[str, Any]:
    data = load_json(path)
    decision_data = review_decision(data)
    score = float(decision_data["overall_score"])
    if decision_data["action"] == "reject":
        return move_with_review(path, REJECTED_DIR, "rejected", decision_data["reason"], decision_data)
    if decision_data["action"] != "reviewed" or score < min_score:
        return {"path": str(path), "status": "pending", "reason": decision_data["reason"], "score": score, "scores": decision_data["scores"]}
    return move_with_review(path, REVIEWED_DIR, "reviewed", decision_data["reason"], decision_data)


def move_with_review(path: Path, dest_dir: Path, status: str, reason: str, decision_data: dict[str, Any]) -> dict[str, Any]:
    data = load_json(path)
    data["review"] = {
        "status": status,
        "reason": reason,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer": "memory_review.py",
        "scores": decision_data.get("scores", {}),
        "overall_score": decision_data.get("overall_score", 0),
        "promotion_policy": "memory_review.py apply -> reviewed/ -> memory_promote.py promote-reviewed",
    }
    dest = dest_dir / path.name
    data_path = path.with_suffix(".reviewing.json")
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.move(str(data_path), str(dest))
    path.unlink(missing_ok=True)
    return {"path": str(dest), "status": status, "reason": reason, "score": decision_data.get("overall_score", 0)}


def summarize_results(results: list[dict[str, Any]], verbose: bool = False) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for result in results:
        status = str(result.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    payload: dict[str, Any] = {
        "total": len(results),
        "counts": counts,
        "sample": results[:10],
    }
    if verbose:
        payload["results"] = results
    return payload


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
