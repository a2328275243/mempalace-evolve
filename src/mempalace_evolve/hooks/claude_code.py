"""Claude Code Stop hook — auto-digest session transcripts.

Usage in .claude/settings.json:
{
  "hooks": {
    "Stop": [{
      "type": "command",
      "command": "python -m mempalace_evolve.hooks.claude_code \"$TRANSCRIPT_PATH\""
    }]
  }
}

Or pipe transcript via stdin:
  cat transcript.jsonl | python -m mempalace_evolve.hooks.claude_code
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from mempalace_evolve.sdk import MemPalace

logger = logging.getLogger("mempalace_evolve.hooks")

# Default palace location
DEFAULT_PALACE = os.environ.get(
    "MEMPALACE_PATH",
    str(Path.home() / ".mempalace" / "palace"),
)
DEFAULT_WING = os.environ.get("MEMPALACE_WING", "global")


def _read_transcript(source: str | None = None) -> str:
    """Read transcript from file path, stdin, or env var."""
    # 1. Explicit file path argument
    if source and Path(source).exists():
        return Path(source).read_text(encoding="utf-8")

    # 2. Environment variable pointing to file
    env_path = os.environ.get("CLAUDE_TRANSCRIPT_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path).read_text(encoding="utf-8")

    # 3. Read from stdin (piped)
    if not sys.stdin.isatty():
        return sys.stdin.read()

    return ""


def _parse_jsonl_transcript(raw: str) -> str:
    """Parse JSONL transcript into plain text for digest."""
    lines = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle structured content blocks
                text_parts = [
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                content = "\n".join(text_parts)
            if content.strip():
                lines.append(f"{role}: {content.strip()}")
        except json.JSONDecodeError:
            # Plain text line
            if line:
                lines.append(line)
    return "\n\n".join(lines) if lines else raw


def run_stop_hook(
    source: str | None = None,
    palace_path: str | None = None,
    wing: str | None = None,
) -> dict:
    """Run the Stop hook: read transcript → digest → evolve.

    Args:
        source: Path to transcript file (optional).
        palace_path: MemPalace storage path (default: ~/.mempalace/palace).
        wing: Wing name (default: from env or "global").

    Returns:
        Dict with extraction results.
    """
    palace_path = palace_path or DEFAULT_PALACE
    wing = wing or DEFAULT_WING

    raw = _read_transcript(source)
    if not raw or len(raw.strip()) < 50:
        return {"status": "skipped", "reason": "transcript too short"}

    # Parse JSONL if applicable
    transcript = _parse_jsonl_transcript(raw)

    # Initialize palace and digest
    palace = MemPalace(palace_path, wing=wing)

    digest_result = palace.digest(transcript)
    evolve_result = palace.evolve(transcript=transcript)

    result = {
        "status": "ok",
        "extracted": digest_result.get("extracted", 0),
        "stored": len(digest_result.get("stored", [])),
        "triples": digest_result.get("triples", 0),
        "promoted": evolve_result.get("promoted", 0),
        "dropped": evolve_result.get("dropped", 0),
    }

    logger.info(
        "Stop hook: extracted=%d, stored=%d, promoted=%d",
        result["extracted"], result["stored"], result["promoted"],
    )
    return result


# Allow running as: python -m mempalace_evolve.hooks.claude_code [path]
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    source_arg = sys.argv[1] if len(sys.argv) > 1 else None
    result = run_stop_hook(source=source_arg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
