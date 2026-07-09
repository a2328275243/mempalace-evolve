"""Memory export — dump palace contents to JSON or Markdown."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("mempalace_evolve.export")


def export_json(collection, wing: str | None = None, output: str | None = None) -> dict:
    """Export all memories to a JSON-serializable dict.

    Args:
        collection: ChromaDB collection.
        wing: Optional wing filter.
        output: Optional file path to write JSON.

    Returns:
        Dict with all memories.
    """
    where = {"wing": wing} if wing else None
    try:
        data = collection.get(where=where, include=["documents", "metadatas"])
    except Exception:
        data = collection.get(include=["documents", "metadatas"])

    memories = []
    if data and data["ids"]:
        for i, doc_id in enumerate(data["ids"]):
            meta = data["metadatas"][i] if data.get("metadatas") else {}
            memories.append({
                "id": doc_id,
                "content": data["documents"][i],
                "wing": meta.get("wing", ""),
                "room": meta.get("room", ""),
                "source_file": meta.get("source_file", ""),
                "importance": meta.get("importance", ""),
                "last_accessed": meta.get("last_accessed", ""),
                "filed_at": meta.get("filed_at", ""),
                "metadata": dict(meta),
            })

    result = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "wing": wing or "all",
        "count": len(memories),
        "memories": memories,
    }

    if output:
        Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2))
        logger.info("Exported %d memories to %s", len(memories), output)

    return result


def export_markdown(collection, wing: str | None = None, output: str | None = None) -> str:
    """Export all memories to Markdown format.

    Args:
        collection: ChromaDB collection.
        wing: Optional wing filter.
        output: Optional file path to write Markdown.

    Returns:
        Markdown string.
    """
    data = export_json(collection, wing=wing)
    lines = [f"# MemPalace Export — {data['wing']}", ""]
    lines.append(f"Exported: {data['exported_at']}  ")
    lines.append(f"Total: {data['count']} memories")
    lines.append("")

    # Group by room
    rooms: dict[str, list] = {}
    for m in data["memories"]:
        room = m.get("room") or "general"
        rooms.setdefault(room, []).append(m)

    for room, mems in sorted(rooms.items()):
        lines.append(f"## {room} ({len(mems)})")
        lines.append("")
        for m in mems:
            content_preview = m["content"][:200].replace("\n", " ")
            lines.append(f"- {content_preview}")
        lines.append("")

    md = "\n".join(lines)

    if output:
        Path(output).write_text(md, encoding="utf-8")
        logger.info("Exported %d memories to %s", data["count"], output)

    return md
