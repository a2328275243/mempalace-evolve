"""Tests for CLI command dispatch."""

from __future__ import annotations

import json


class FakePalace:
    calls: list[tuple[str, dict]] = []

    def __init__(self, palace_path=None):
        self.palace_path = palace_path

    def purge_expired(self, **kwargs):
        self.calls.append(("purge_expired", kwargs))
        return {"purged": 1}

    def compress_old_memories(self, **kwargs):
        self.calls.append(("compress_old_memories", kwargs))
        return {"rooms_compressed": 1}

    def consolidate(self, **kwargs):
        self.calls.append(("consolidate", kwargs))
        return {"status": "success"}


def _run_cli(monkeypatch, capsys, argv):
    from mempalace_evolve import cli
    import mempalace_evolve.sdk as sdk

    FakePalace.calls = []
    monkeypatch.setattr(sdk, "MemPalace", FakePalace)
    monkeypatch.setattr("sys.argv", ["mempalace", *argv])

    cli.main()
    return json.loads(capsys.readouterr().out)


def test_cli_purge_dispatches_to_sdk(monkeypatch, capsys):
    result = _run_cli(
        monkeypatch,
        capsys,
        ["purge", "--ttl-days", "3", "--ttl-summary", "9", "--palace", "tmp-palace"],
    )

    assert result == {"purged": 1}
    assert FakePalace.calls == [
        ("purge_expired", {"ttl_days": 3, "ttl_summary_days": 9}),
    ]


def test_cli_compress_dispatches_to_sdk(monkeypatch, capsys):
    result = _run_cli(
        monkeypatch,
        capsys,
        ["compress", "--after-days", "2", "--max-chars", "123"],
    )

    assert result == {"rooms_compressed": 1}
    assert FakePalace.calls == [
        ("compress_old_memories", {"compress_after_days": 2, "max_chars": 123}),
    ]


def test_cli_consolidate_dispatches_to_sdk(monkeypatch, capsys):
    result = _run_cli(monkeypatch, capsys, ["consolidate", "--dry-run"])

    assert result == {"status": "success"}
    assert FakePalace.calls == [
        ("consolidate", {"dry_run": True}),
    ]


def test_cli_serve_forwards_wing(monkeypatch):
    from mempalace_evolve import cli
    import mempalace_evolve.sdk as sdk
    import mempalace_evolve.adapters.rest_api as rest_api

    calls = []
    monkeypatch.setattr(sdk, "MemPalace", FakePalace)
    monkeypatch.setattr(
        rest_api,
        "serve",
        lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["mempalace", "serve", "--wing", "project-alpha", "--palace", "tmp-palace"],
    )

    cli.main()

    assert calls == [
        {
            "host": "0.0.0.0",
            "port": 8765,
            "palace_path": "tmp-palace",
            "wing": "project-alpha",
            "api_key": None,
        }
    ]


def test_rest_serve_forwards_wing_to_app(monkeypatch, tmp_path):
    import uvicorn
    from mempalace_evolve.adapters import rest_api

    captured = {}
    fake_app = object()
    monkeypatch.setattr(
        rest_api,
        "create_app",
        lambda *args, **kwargs: captured.update(create=(args, kwargs)) or fake_app,
    )
    monkeypatch.setattr(
        uvicorn,
        "run",
        lambda app, host, port: captured.update(run=(app, host, port)),
    )

    rest_api.serve(
        host="127.0.0.1",
        port=9876,
        palace_path=str(tmp_path),
        wing="project-beta",
        api_key="secret",
    )

    assert captured["create"] == (
        (str(tmp_path),),
        {"wing": "project-beta", "api_key": "secret"},
    )
    assert captured["run"] == (fake_app, "127.0.0.1", 9876)
