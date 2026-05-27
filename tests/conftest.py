"""Pytest configuration — shared fixtures for all tests."""

import os
import shutil
import tempfile

import pytest


@pytest.fixture
def tmp_palace(tmp_path):
    """Create a temporary palace directory and clean up after test."""
    palace_dir = tmp_path / "test_palace"
    palace_dir.mkdir()
    yield str(palace_dir)
    shutil.rmtree(str(palace_dir), ignore_errors=True)


@pytest.fixture
def palace(tmp_palace):
    """Create a MemPalace instance with a temporary directory."""
    from mempalace_evolve.sdk import MemPalace
    return MemPalace(tmp_palace, wing="test")
