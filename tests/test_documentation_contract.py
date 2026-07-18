"""Keep the public quick-start paths aligned with the executable API."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_keeps_contest_template_before_mempalace_content():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.index("DreamSeed Contest") < readme.index("# MemPalace Evolve")


def test_readme_does_not_reintroduce_removed_api_examples():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for stale_reference in ("store_memory(", "item.content", "/v1/memories", "mempalace shell"):
        assert stale_reference not in readme


def test_documented_sdk_example_runs(tmp_path, monkeypatch):
    import runpy

    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(ROOT / "docs" / "examples" / "basic_usage.py"), run_name="__main__")
