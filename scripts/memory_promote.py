from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
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
PROMOTED_DIR = CANDIDATE_DIR / "promoted"


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote reviewed DreamSeed memory candidates into MemPalace")
    sub = parser.add_subparsers(dest="command", required=True)

    promote_parser = sub.add_parser("promote-reviewed", help="Promote reviewed candidates only")
    promote_parser.add_argument("id", nargs="?", help="Reviewed candidate id/path; omit with --all")
    promote_parser.add_argument("--all", action="store_true")
    promote_parser.add_argument("--dry-run", action="store_true")
    promote_parser.add_argument("--room", default="project")

    args = parser.parse_args()
    ensure_dirs()

    if args.command == "promote-reviewed":
        targets = reviewed_candidates() if args.all else [resolve_reviewed(args.id)]
        results = [promote(path, room=args.room, dry_run=args.dry_run) for path in targets]
        print_json({"ok": True, "results": results})
        return 0

    return 2


def ensure_dirs() -> None:
    REVIEWED_DIR.mkdir(parents=True, exist_ok=True)
    PROMOTED_DIR.mkdir(parents=True, exist_ok=True)


def ensure_mempalace_path() -> None:
    for value in (
        os.environ.get("DREAMSEED_MEMPALACE_SRC", ""),
        os.environ.get("DREAMSEED_PYTHON_SITE", ""),
    ):
        if value and Path(value).exists() and value not in sys.path:
            sys.path.insert(0, value)


def reviewed_candidates() -> list[Path]:
    return sorted(p for p in REVIEWED_DIR.glob("*.json") if p.is_file())


def resolve_reviewed(value: str | None) -> Path:
    if not value:
        raise SystemExit("reviewed candidate id/path required")
    path = Path(value)
    if path.exists():
        return path
    if not value.endswith(".json"):
        by_id = REVIEWED_DIR / f"{value}.json"
        if by_id.exists():
            return by_id
    matches = list(REVIEWED_DIR.glob(f"*{value}*.json"))
    if len(matches) == 1:
        return matches[0]
    raise SystemExit(f"reviewed candidate not found or ambiguous: {value}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def promote(path: Path, room: str = "project", dry_run: bool = False) -> dict[str, Any]:
    data = load_json(path)
    review = data.get("review") or {}
    if review.get("status") != "reviewed":
        return {"path": str(path), "status": "blocked", "reason": "candidate is not reviewed"}

    content = data.get("text") or data.get("summary") or ""
    if not str(content).strip():
        return {"path": str(path), "status": "blocked", "reason": "empty content"}

    if dry_run:
        return {"path": str(path), "status": "dry-run", "room": room, "summary": data.get("summary", "")[:180]}

    ensure_mempalace_path()
    from mempalace_evolve.sdk import MemPalace

    palace_path = Path(os.environ.get("MEMPALACE_PATH") or os.environ.get("DREAMSEED_MEMORY_DIR") or ROOT / "memory")
    wing = os.environ.get("MEMPALACE_WING") or "dreamseed"
    palace = MemPalace(palace_path, wing=wing)
    drawer_id = palace.remember(
        content=str(content),
        room=room,
        metadata={
            "source": "dreamseed-reviewed-candidate",
            "candidate_id": data.get("id") or path.stem,
            "candidate_score": data.get("score"),
            "reviewed_at": review.get("reviewed_at"),
        },
        source=str(path),
    )

    data["promotion"] = {
        "status": "promoted",
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "promoter": "memory_promote.py",
        "drawer_id": drawer_id,
        "room": room,
        "wing": wing,
        "palace_path": str(palace_path),
    }
    dest = PROMOTED_DIR / path.name
    temp = path.with_suffix(".promoting.json")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.move(str(temp), str(dest))
    path.unlink(missing_ok=True)
    return {"path": str(dest), "status": "promoted", "drawer_id": drawer_id}


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
