"""Document ingestion subsystem for mempalace-evolve.

Handles:
- Scanning files in a directory
- Computing content hashes for incremental indexing
- Chunking and batch-embedding into ChromaDB
- Source tracking via a lightweight JSON manifest
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mempalace_evolve.models import (
    Chunk,
    IngestResult,
    IngestSummary,
    Source,
)

logger = logging.getLogger("mempalace_evolve")

_DEFAULT_MANIFEST_NAME = ".mempalace_manifest.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _read_text_file(path: Path) -> str | None:
    """Try to read a file as UTF-8; return None on binary or decode error."""
    try:
        # sniff for null bytes (binary heuristic)
        raw = path.read_bytes()
        if b"\x00" in raw[:2048]:
            return None
        return raw.decode("utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        logger.debug("Skipping %s: %s", path, exc)
        return None


def _default_ignore_patterns() -> set[str]:
    return {
        ".git", "__pycache__", "node_modules", ".venv", "env",
        ".DS_Store", "Thumbs.db", ".gitignore", ".mempalace_manifest.json",
        "*.pyc", "*.pyo",
    }


def _match_ignore(name: str, patterns: set[str]) -> bool:
    for pat in patterns:
        if pat.startswith("*") and name.endswith(pat[1:]):
            return True
        if name == pat:
            return True
    return False


def _load_manifest(palace_path: str) -> dict[str, Any]:
    manifest_path = Path(palace_path) / _DEFAULT_MANIFEST_NAME
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_manifest(palace_path: str, manifest: dict[str, Any]) -> None:
    manifest_path = Path(palace_path) / _DEFAULT_MANIFEST_NAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_directory(
    directory: str,
    *,
    recursive: bool = True,
    ignore_patterns: set[str] | None = None,
    extensions: set[str] | None = None,
) -> list[Path]:
    """Walk *directory* and yield text files that are not ignored.

    Returns sorted file paths.
    """
    base = Path(directory).resolve()
    if not base.is_dir():
        raise NotADirectoryError(f"{directory} is not a directory")

    ignore = _default_ignore_patterns() | (ignore_patterns or set())
    files: list[Path] = []

    walker = base.rglob("*") if recursive else base.glob("*")
    for entry in sorted(walker):
        if not entry.is_file():
            continue
        if _match_ignore(entry.name, ignore):
            continue
        if extensions and entry.suffix.lower() not in extensions:
            continue
        files.append(entry)

    return files


def ingest_file(
    path: str,
    palace: Any,                  # MemPalace instance duck-typed
    *,
    room: str = "documents",
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    force: bool = False,
    manifest: dict[str, Any] | None = None,
) -> IngestResult:
    """Ingest a single text file into the palace.

    Args:
        path: File path to ingest.
        palace: MemPalace SDK instance (duck-typed — needs .remember or .batch_remember).
        room: Target room for all chunks.
        chunk_size: Max characters per chunk.
        chunk_overlap: Overlap between consecutive chunks.
        force: If True, re-index even if the hash matches.
        manifest: Optional manifest dict for incremental indexing.

    Returns:
        IngestResult.
    """
    file_path = Path(path)
    if not file_path.is_file():
        return IngestResult(
            source_id="",
            path=path,
            chunks_created=0,
            chunks_skipped=0,
            status="error",
            error=f"File not found: {path}",
        )

    content = _read_text_file(file_path)
    if content is None:
        return IngestResult(
            source_id="",
            path=path,
            chunks_created=0,
            chunks_skipped=0,
            status="error",
            error=f"Unreadable or binary file: {path}",
        )

    # Source ID stable across re-runs
    stat = file_path.stat()
    source_id = _compute_hash(f"{path}::{stat.st_mtime}::{stat.st_size}")
    content_hash = _compute_hash(content)

    # Incremental check
    manifest = manifest or {}
    cached = manifest.get(path, {})
    if not force and cached.get("hash") == content_hash:
        return IngestResult(
            source_id=source_id,
            path=path,
            chunks_created=0,
            chunks_skipped=0,
            status="skipped",
        )

    # Chunk the content
    lines = content.split("\n")
    chunks: list[dict[str, Any]] = []
    start_line = 0
    current_chunk: list[str] = []
    current_len = 0

    for lineno, line_text in enumerate(lines):
        current_chunk.append(line_text)
        current_len += len(line_text) + 1  # +1 for newline
        if current_len >= chunk_size and current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append({
                "content": chunk_text,
                "room": room,
                "metadata": {
                    "source_id": source_id,
                    "source_path": path,
                    "chunk_index": len(chunks),
                    "start_line": start_line,
                    "end_line": lineno,
                },
            })
            # Retain overlap lines
            overlap_lines = []
            overlap_len = 0
            for ol in reversed(current_chunk):
                if overlap_len >= chunk_overlap:
                    break
                overlap_lines.insert(0, ol)
                overlap_len += len(ol) + 1
            current_chunk = overlap_lines
            current_len = overlap_len
            start_line = max(0, lineno - len(overlap_lines) + 1)

    # Last chunk
    if current_chunk:
        chunk_text = "\n".join(current_chunk)
        chunks.append({
            "content": chunk_text,
            "room": room,
            "metadata": {
                "source_id": source_id,
                "source_path": path,
                "chunk_index": len(chunks),
                "start_line": start_line,
                "end_line": len(lines) - 1,
            },
        })

    if not chunks:
        return IngestResult(
            source_id=source_id,
            path=path,
            chunks_created=0,
            chunks_skipped=0,
            status="skipped",
            error="Empty content",
        )

    # Store via SDK batch
    try:
        result = palace.batch_remember(chunks)
        stored_count = result.get("added", 0) or result.get("stored", len(chunks))
    except Exception as exc:
        logger.exception("batch_remember failed for %s", path)
        return IngestResult(
            source_id=source_id,
            path=path,
            chunks_created=0,
            chunks_skipped=0,
            status="error",
            error=str(exc),
        )

    return IngestResult(
        source_id=source_id,
        path=path,
        chunks_created=stored_count,
        chunks_skipped=len(chunks) - stored_count,
        status="ok",
    )


def ingest_directory(
    directory: str,
    palace: Any,
    *,
    recursive: bool = True,
    room: str = "documents",
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    force: bool = False,
    extensions: set[str] | None = None,
) -> IngestSummary:
    """Ingest all supported files in a directory.

    Uses a local manifest (``.mempalace_manifest.json``) to skip
    previously-indexed, unchanged files.
    """
    palace_path = getattr(palace, "_palace_path", str(Path.cwd()))
    manifest = _load_manifest(palace_path)
    summary = IngestSummary()

    files = scan_directory(
        directory,
        recursive=recursive,
        extensions=extensions,
    )
    summary.total_files = len(files)

    for file_path in files:
        path_str = str(file_path)
        result = ingest_file(
            path_str,
            palace,
            room=room,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            force=force,
            manifest=manifest,
        )
        summary.results.append(result)

        if result.status == "ok":
            summary.indexed += 1
            manifest[path_str] = {
                "hash": _compute_hash(
                    _read_text_file(file_path) or ""
                ),
                "last_indexed": datetime.now(timezone.utc).isoformat(),
            }
        elif result.status == "skipped":
            summary.skipped += 1
        else:
            summary.errors += 1

    _save_manifest(palace_path, manifest)
    return summary


def list_sources(palace_path: str) -> list[Source]:
    """List tracked sources from the ingest manifest."""
    manifest = _load_manifest(palace_path)
    sources: list[Source] = []
    for path, meta in manifest.items():
        sources.append(
            Source(
                source_id=_compute_hash(path),
                path=path,
                kind="file",
                hash=meta.get("hash", ""),
                last_indexed=datetime.fromisoformat(meta["last_indexed"])
                if "last_indexed" in meta
                else None,
                status="indexed",
            )
        )
    return sorted(sources, key=lambda s: s.path)


def purge_source(palace_path: str, source_path: str) -> bool:
    """Remove a source from the manifest (does not delete vector data)."""
    manifest = _load_manifest(palace_path)
    if source_path in manifest:
        del manifest[source_path]
        _save_manifest(palace_path, manifest)
        return True
    return False

