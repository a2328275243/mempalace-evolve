"""Candidate extractor — extract memory candidates from session transcripts.

This is the agent-agnostic version of the logic from stop_unified.py.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("mempalace_evolve.evolution")

# Keywords that indicate memorable content
MEMORY_KEYWORDS = [
    # Decisions
    "decided", "decision", "chose", "选择", "决定", "确定",
    # Errors & fixes
    "error", "fix", "bug", "issue", "错误", "修复", "问题",
    # Architecture
    "architecture", "design", "pattern", "架构", "设计", "模式",
    # Config
    "config", "setting", "install", "配置", "设置", "安装",
    # Important facts
    "important", "remember", "note", "记住", "注意", "关键",
]


class CandidateExtractor:
    """Extract memory candidates from session transcripts."""

    def __init__(self, keywords: list[str] | None = None):
        self.keywords = keywords or MEMORY_KEYWORDS

    def extract(self, transcript: str, context: dict[str, Any] | None = None) -> list[dict]:
        """Extract memory candidates from a transcript.

        Args:
            transcript: Session transcript text.
            context: Optional metadata (session_id, project, etc.)

        Returns:
            List of candidate dicts with content, score, type.
        """
        if not transcript or len(transcript.strip()) < 50:
            return []

        context = context or {}
        candidates = []
        chunks = self._split_into_chunks(transcript)

        for chunk in chunks:
            score = self._score_chunk(chunk)
            if score >= 3:
                candidates.append({
                    "id": self._stable_id(chunk),
                    "content": chunk[:2000],
                    "score": score,
                    "type": self._classify(chunk),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    **context,
                })

        return candidates

    def _split_into_chunks(self, text: str) -> list[str]:
        """Split transcript into meaningful chunks."""
        # Split by double newlines or message boundaries
        chunks = []
        current = []
        for line in text.split("\n"):
            if not line.strip() and current:
                chunk = "\n".join(current).strip()
                if len(chunk) >= 30:
                    chunks.append(chunk)
                current = []
            else:
                current.append(line)
        if current:
            chunk = "\n".join(current).strip()
            if len(chunk) >= 30:
                chunks.append(chunk)
        return chunks

    def _score_chunk(self, chunk: str) -> int:
        """Score a chunk's memorability (0-10)."""
        score = 0
        lower = chunk.lower()

        # Keyword matches
        matches = sum(1 for kw in self.keywords if kw in lower)
        score += min(matches * 2, 6)

        # Length bonus (substantial content)
        if len(chunk) > 200:
            score += 1
        if len(chunk) > 500:
            score += 1

        # Code presence
        if "```" in chunk or "def " in chunk or "class " in chunk:
            score += 1

        # Penalize boilerplate
        if any(bp in lower for bp in ["hello", "hi there", "sure,", "okay,"]):
            score -= 2

        return max(0, min(10, score))

    def _classify(self, chunk: str) -> str:
        """Classify the type of memory."""
        lower = chunk.lower()
        if any(w in lower for w in ["error", "bug", "fix", "错误", "修复"]):
            return "error_pattern"
        if any(w in lower for w in ["decided", "decision", "chose", "决定"]):
            return "decision"
        if any(w in lower for w in ["config", "install", "setup", "配置"]):
            return "config"
        if any(w in lower for w in ["architecture", "design", "架构"]):
            return "architecture"
        return "general"

    def _stable_id(self, content: str) -> str:
        """Generate a stable ID for deduplication."""
        return hashlib.md5(content.strip().encode()).hexdigest()[:12]
