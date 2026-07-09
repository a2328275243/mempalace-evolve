"""Pytest configuration — shared fixtures for all tests."""

import atexit
import logging
import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Use a writable workspace location for tests, scoped to the repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent
_TEST_ROOT = _REPO_ROOT / ".test_tmp"
_TEST_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MEMPALACE_ROOT", str(_TEST_ROOT / "global_mempalace"))
os.environ.setdefault("MEMPALACE_EMBEDDING_BACKEND", "hash")
os.environ.setdefault(
    "MEMPALACE_ADAPTIVE_BASELINES_PATH",
    str(_TEST_ROOT / "adaptive_baselines.json"),
)


def _cleanup_test_root():
    """One-time cleanup of stale test artifacts on pytest session start."""
    count = 0
    for item in _TEST_ROOT.iterdir():
        try:
            if item.is_dir():
                shutil.rmtree(str(item), ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
            count += 1
        except Exception:
            pass
    if count:
        logging.getLogger("mempalace.tests").info(
            "Cleaned up %d stale test artifact(s) in %s", count, _TEST_ROOT
        )


# Register cleanup
atexit.register(_cleanup_test_root)


@pytest.fixture(scope="session")
def test_root():
    """Session-scoped temporary test root. Cleaned at exit."""
    return _TEST_ROOT


@pytest.fixture
def tmp_palace():
    """Create a temporary palace directory in writable workspace and clean up after test."""
    import uuid

    palace_dir = _TEST_ROOT / f"test_palace_{uuid.uuid4().hex[:8]}"
    palace_dir.mkdir(parents=True, exist_ok=True)
    yield str(palace_dir)
    shutil.rmtree(str(palace_dir), ignore_errors=True)


@pytest.fixture
def palace(tmp_palace):
    """Create a MemPalace instance with a temporary directory."""
    from mempalace_evolve.sdk import MemPalace

    return MemPalace(tmp_palace, wing="test")


@pytest.fixture
def palace_with_kg(tmp_palace):
    """Create a MemPalace instance with sample knowledge graph data."""
    from mempalace_evolve.sdk import MemPalace

    p = MemPalace(tmp_palace, wing="test")
    p.add_fact("Python", "is_a", "programming_language")
    p.add_fact("Flask", "uses", "Python")
    p.add_fact("JWT", "is_a", "auth_standard")
    return p
