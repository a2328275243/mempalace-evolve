"""Tests for core/config.py — config parsing, project resolution, lifecycle config."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from mempalace_evolve.core.config import (
    UserConfig,
    get_config,
    _yaml_safe_load,
    atomic_write,
    atomic_write_json,
    GLOBAL_PALACE,
    COLLECTION_NAME,
    IDENTITY_FILE,
    YAML_FILE,
    YAML_ALT,
)


# ---------------------------------------------------------------------------
# _yaml_safe_load  (returns dict only — lists at top level become {})
# ---------------------------------------------------------------------------

class TestYamlSafeLoad:
    def test_simple_key_value(self):
        yaml = "key: value\nfoo: bar"
        result = _yaml_safe_load(yaml)
        assert result == {"key": "value", "foo": "bar"}

    def test_list_items_at_top_level_becomes_empty(self):
        """Top-level list is not supported by the mini parser (returns {})."""
        yaml = "- item1\n- item2\n- item3"
        result = _yaml_safe_load(yaml)
        assert result == {}

    def test_nested_dict(self):
        yaml = "outer:\n  inner: value\n  other: 42"
        result = _yaml_safe_load(yaml)
        assert result == {"outer": {"inner": "value", "other": 42}}

    def test_inline_comment(self):
        yaml = "key: value  # this is a comment\nfoo: bar"
        result = _yaml_safe_load(yaml)
        assert result == {"key": "value", "foo": "bar"}

    def test_empty_yaml(self):
        assert _yaml_safe_load("") == {}
        assert _yaml_safe_load("# just a comment") == {}

    def test_boolean_values(self):
        yaml = "enabled: true\ndisabled: false"
        result = _yaml_safe_load(yaml)
        assert result == {"enabled": True, "disabled": False}

    def test_numeric_values(self):
        yaml = "count: 42\nratio: 3.14"
        result = _yaml_safe_load(yaml)
        assert result == {"count": 42, "ratio": 3.14}

    def test_quoted_string_has_quotes_stripped(self):
        """The mini parser strips surrounding quotes from values."""
        yaml = 'name: "hello world"\ncode: ''123'''
        result = _yaml_safe_load(yaml)
        # "hello world" -> quotes stripped -> "hello world"
        # '123' -> quotes stripped -> 123 (parsed as int)
        assert result["name"] == "hello world"
        # 123 is valid integer, so it is parsed as int not str
        assert result["code"] == 123

    def test_null_value(self):
        yaml = "key: null\nother: ~"
        result = _yaml_safe_load(yaml)
        assert result == {"key": None, "other": None}

    def test_nested_list_in_dict(self):
        """Lists within dicts are supported."""
        yaml = "items:\n  - a\n  - b\n  - c"
        result = _yaml_safe_load(yaml)
        assert result["items"] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# atomic_write / atomic_write_json
# ---------------------------------------------------------------------------

class TestAtomicWrite:
    def test_write_read(self, tmp_palace):
        path = Path(tmp_palace) / "test.txt"
        atomic_write(path, "hello world")
        assert path.read_text() == "hello world"

    def test_write_json(self, tmp_palace):
        path = Path(tmp_palace) / "data.json"
        data = {"key": "value", "nums": [1, 2, 3]}
        atomic_write_json(path, data)
        loaded = json.loads(path.read_text())
        assert loaded == data

    def test_write_overwrites(self, tmp_palace):
        path = Path(tmp_palace) / "overwrite.txt"
        atomic_write(path, "first")
        atomic_write(path, "second")
        assert path.read_text() == "second"

    def test_nested_directory_creates(self, tmp_palace):
        path = Path(tmp_palace) / "a" / "b" / "c" / "deep.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, "nested")
        assert path.exists()
        assert path.read_text() == "nested"


# ---------------------------------------------------------------------------
# UserConfig
# ---------------------------------------------------------------------------

class TestUserConfig:
    def test_default_identity_path(self, tmp_palace):
        """Identity file path defaults to config_dir / identity.txt."""
        config = UserConfig(config_dir=tmp_palace)
        identity = config.resolve_identity_path()
        assert identity.endswith(IDENTITY_FILE)

    def test_collection_name_constant(self, tmp_palace):
        config = UserConfig(config_dir=tmp_palace)
        assert config.collection_name == COLLECTION_NAME

    def test_palace_path_points_to_global(self, tmp_palace):
        """palace_path property returns the global chroma path."""
        config = UserConfig(config_dir=tmp_palace)
        assert "palace" in config.palace_path

    def test_load_yaml_nonexistent(self, tmp_palace):
        config = UserConfig(config_dir=tmp_palace)
        result = config._load_yaml(Path(tmp_palace) / "nonexistent.yaml")
        assert result is None

    def test_load_yaml_simple(self, tmp_palace):
        yaml_path = Path(tmp_palace) / YAML_FILE
        yaml_path.write_text("key: value\nlist_key:\n  - a\n  - b", encoding="utf-8")
        config = UserConfig(config_dir=tmp_palace)
        result = config._load_yaml(yaml_path)
        assert isinstance(result, dict)
        assert "key" in result

    def test_lifecycle_config_defaults(self, tmp_palace):
        """lifecycle_config returns defaults when no YAML is present."""
        config = UserConfig(config_dir=tmp_palace)
        lc = config.lifecycle_config
        assert lc["decay_lambda"] == 0.02
        assert lc["compress_after_days"] == 60
        assert lc["max_total_drawers"] == 500
        assert lc["max_drawers_per_wing"] == 200
        assert lc["conflict_threshold"] == 0.95

    def test_lifecycle_config_custom(self, tmp_palace):
        """lifecycle_config merges custom values from YAML."""
        yaml_path = Path(tmp_palace) / YAML_FILE
        yaml_path.write_text(
            "lifecycle:\n  decay_lambda: 0.05\n  max_total_drawers: 1000\n",
            encoding="utf-8",
        )
        config = UserConfig(config_dir=tmp_palace)
        lc = config.lifecycle_config
        assert lc["decay_lambda"] == 0.05
        assert lc["max_total_drawers"] == 1000
        assert lc["compress_after_days"] == 60  # default preserved

    def test_scan_all_mempalaces_empty(self, tmp_palace):
        config = UserConfig(config_dir=tmp_palace)
        files = config.scan_all_mempalaces()
        assert isinstance(files, list)

    def test_scan_all_mempalaces_global_md(self, tmp_palace):
        # Create a .md file in the config dir (global palace)
        md_path = Path(tmp_palace) / "test_memory.md"
        md_path.write_text("# memory", encoding="utf-8")
        config = UserConfig(config_dir=tmp_palace)
        files = config.scan_all_mempalaces()
        found = any(f["name"] == "test_memory.md" for f in files)
        assert found

    def test_get_projects_no_yaml(self, tmp_palace):
        config = UserConfig(config_dir=tmp_palace)
        projects = config.get_projects()
        assert isinstance(projects, list)

    def test_get_rooms_for_wing(self, tmp_palace):
        """
        A project with a palace_path can have a per-project YAML.
        get_rooms_for_wing reads the palace's mempalace.yaml, looking for 'wings'.
        'projects' and 'wings' must be in the SAME YAML file because
        get_rooms_for_wing loads palace_path/YAML_FILE first and returns
        immediately if that file exists (even without wings).
        """
        # Write the global config YAML with projects
        yaml_path = Path(tmp_palace) / YAML_FILE
        yaml_path.write_text(
            "projects:\n"
            '  - name: my-wing\n'
            f"    path: {tmp_palace}\n"
            f"    palace_path: {tmp_palace}\n"
            "    type: local\n"
            "wings:\n"
            "  my-wing:\n"
            "    rooms:\n"
            "      - decisions\n"
            "      - errors\n",
            encoding="utf-8",
        )
        config = UserConfig(config_dir=tmp_palace)
        rooms = config.get_rooms_for_wing("my-wing")
        assert len(rooms) >= 1
        found = any(r["name"] == "decisions" for r in rooms)
        assert found

    def test_resolve_palace_path_global_default(self, tmp_palace):
        config = UserConfig(config_dir=tmp_palace)
        path = config.resolve_palace_path("non-existent-wing")
        # Unknown wing falls back to global chroma path
        assert path == config.palace_path

    def test_resolve_wing_fallback(self, tmp_palace):
        """Unregistered path uses directory name as wing name."""
        config = UserConfig(config_dir=tmp_palace)
        wing = config.resolve_wing(tmp_palace)
        assert wing == Path(tmp_palace).name

    def test_resolve_identity_with_wing(self, tmp_palace):
        """resolve_identity_path with a known wing returns the project identity path."""
        yaml_path = Path(tmp_palace) / YAML_FILE
        yaml_path.write_text(
            "projects:\n"
            '  - name: test-wing\n'
            f"    path: {tmp_palace}\n"
            f"    palace_path: {tmp_palace}\n"
            "    type: local\n",
            encoding="utf-8",
        )
        # Create identity file in the project palace
        ident = Path(tmp_palace) / IDENTITY_FILE
        ident.write_text("test-identity", encoding="utf-8")

        config = UserConfig(config_dir=tmp_palace)
        path = config.resolve_identity_path("test-wing")
        assert path == str(ident)

    def test_get_config_singleton(self, tmp_palace):
        """get_config returns the same instance on repeated calls."""
        import mempalace_evolve.core.config as cfg_mod
        cfg_mod._config = None
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2
