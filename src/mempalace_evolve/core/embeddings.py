"""Singleton embedding function with lazy ONNX loading and caching.

Implements the full chromadb.api.types.EmbeddingFunction protocol.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
import time as _time
from typing import Any

logger = logging.getLogger("mempalace.embeddings")

_EF_LOCK = threading.RLock()
_EF_INSTANCE: "CachedEmbeddingFunction | None" = None
_EF_LOAD_ATTEMPTED = False
_EF_LOAD_ERROR: str | None = None

EMBEDDING_DIM = 384


def _hash_embed(texts: list[str], dim: int = EMBEDDING_DIM) -> list[list[float]]:
    """Deterministic lexical hash embeddings for when ONNX is unavailable."""
    embeddings = []
    for text in texts:
        vec = [0.0] * dim
        raw_tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", str(text).lower())
        if not raw_tokens:
            raw_tokens = [str(text).lower()]
        features = []
        for token in raw_tokens:
            features.append(token)
            if len(token) > 16:
                features.extend(token)
        for token in features:
            h = hashlib.md5(token.encode()).digest()
            idx = int.from_bytes(h[:4], "big") % dim
            vec[idx] += 1.0
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        embeddings.append(vec)
    return embeddings


class CachedEmbeddingFunction:
    """Cached ONNX embedding with fallback, implements full ChromaDB EmbeddingFunction protocol."""

    def __init__(self):
        self._onnx_ef = None
        self._init_lock = threading.Lock()
        self._use_fallback = False
        self._backend = os.environ.get("MEMPALACE_EMBEDDING_BACKEND", "auto").strip().lower()
        self._load_time = 0.0
        self._call_count = 0

    def _ensure_init(self):
        if self._onnx_ef is not None or self._use_fallback:
            return
        with self._init_lock:
            if self._onnx_ef is not None or self._use_fallback:
                return
            if self._backend == "hash":
                self._use_fallback = True
                return
            try:
                from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

                t0 = _time.time()
                self._onnx_ef = ONNXMiniLM_L6_V2()
                self._load_time = _time.time() - t0
                logger.debug("ONNX embedding model loaded in %.1fs", self._load_time)
            except Exception as e:
                logger.warning(
                    "ONNX embedding unavailable (%s), falling back to hash embeddings. "
                    "Semantic search quality will be reduced.",
                    e,
                )
                self._use_fallback = True

    def name(self) -> str:
        return "cached-onnx-minilm-l6-v2"

    def __call__(self, input) -> list[list[float]]:
        self._call_count += 1
        self._ensure_init()
        if self._use_fallback or self._onnx_ef is None:
            return _hash_embed(list(input))
        return self._onnx_ef(input)

    def embed_query(self, input) -> list[list[float]]:
        """Embed query texts (same as __call__ for this model)."""
        return self.__call__(input)

    def embed_with_retries(self, input, **retry_kwargs):
        """Embed with retry support."""
        return self.__call__(input)

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> list[str]:
        return ["cosine", "l2", "ip"]

    def is_legacy(self) -> bool:
        return self.name() != "default"

    def get_config(self) -> dict[str, Any]:
        return {"model_name": self.name()}

    def validate_config(self, config: dict[str, Any]) -> bool:
        return config.get("model_name") == self.name()

    def validate_config_update(
        self, old_config: dict[str, Any], new_config: dict[str, Any]
    ) -> bool:
        return self.validate_config(new_config)

    def build_from_config(self, config: dict[str, Any]):
        """Build from config dict."""
        return self

    @property
    def is_fallback(self) -> bool:
        self._ensure_init()
        return self._use_fallback


def get_cached_ef() -> CachedEmbeddingFunction:
    """Get the global cached embedding function singleton."""
    global _EF_INSTANCE, _EF_LOAD_ATTEMPTED, _EF_LOAD_ERROR
    if _EF_INSTANCE is not None:
        return _EF_INSTANCE
    with _EF_LOCK:
        if _EF_INSTANCE is not None:
            return _EF_INSTANCE
        _EF_LOAD_ATTEMPTED = True
        try:
            _EF_INSTANCE = CachedEmbeddingFunction()
        except Exception as e:
            _EF_LOAD_ERROR = str(e)
            raise
        return _EF_INSTANCE


def get_ef_status() -> dict:
    """Return embedding function status for monitoring."""
    ef = get_cached_ef()
    return {
        "loaded": _EF_LOAD_ATTEMPTED,
        "backend": ef._backend if ef else "unknown",
        "fallback": ef.is_fallback if ef else True,
        "load_time_s": round(ef._load_time, 2) if ef else 0,
        "call_count": ef._call_count if ef else 0,
        "error": _EF_LOAD_ERROR,
    }
