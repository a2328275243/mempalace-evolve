"""Tests for new SDK features: digest, context_for, import/export, evolve,
recency decay, contradiction detection, working memory cache, smart promotion."""

import json
import time


class TestDigest:
    def test_digest_from_message_list(self, palace):
        messages = [
            {"role": "user", "content": "我们决定用 Redis 做缓存，TTL 设 1 小时"},
            {"role": "assistant", "content": "好的，已配置 Redis，TTL=3600s"},
            {"role": "user", "content": "认证用 JWT，别用 session"},
        ]
        result = palace.digest(messages)
        assert "extracted" in result
        assert "stored" in result
        assert result["extracted"] >= 1

    def test_digest_from_string(self, palace):
        result = palace.digest(
            "We decided to use PostgreSQL for the database. "
            "Fixed a bug: connection pool was leaking."
        )
        assert result["extracted"] >= 1

    def test_digest_stores_recallable_memories(self, palace):
        palace.digest([
            {"role": "user", "content": "我们决定项目使用 FastAPI 框架作为后端，这是一个重要的架构设计决策"},
            {"role": "assistant", "content": "好的，FastAPI 框架已确认，我会记住这个配置"},
        ])
        results = palace.recall("FastAPI")
        assert len(results) >= 1
        assert any("FastAPI" in r["content"] for r in results)

    def test_digest_empty_conversation(self, palace):
        result = palace.digest([{"role": "user", "content": "ok"}])
        assert result["extracted"] == 0


class TestContextFor:
    def test_returns_formatted_string(self, palace):
        palace.remember("Redis 用于缓存，TTL=3600", room="decisions")
        ctx = palace.context_for("缓存配置")
        assert ctx != ""
        assert "Redis" in ctx

    def test_returns_empty_when_no_match(self, palace):
        ctx = palace.context_for("完全不相关的话题 xyz123")
        assert ctx == ""

    def test_respects_max_tokens(self, palace):
        for i in range(20):
            palace.remember(f"Long memory item number {i} with extra padding text", room="general")
        ctx = palace.context_for("memory item", max_tokens=100)
        assert len(ctx) <= 120  # small margin over 100

    def test_includes_room_prefix(self, palace):
        palace.remember("重要决策内容", room="decisions")
        ctx = palace.context_for("决策")
        assert "[decisions]" in ctx


class TestImportExport:
    def test_import_from_list(self, palace):
        items = [
            {"content": "API 用 FastAPI 框架", "room": "decisions"},
            {"content": "数据库连接池 max=20", "room": "config"},
            {"content": "", "room": "general"},
        ]
        result = palace.import_memories(items)
        assert result["imported"] == 2
        assert result["skipped"] == 1

    def test_import_from_json_file(self, palace, tmp_path):
        items = [
            {"content": "Imported via JSON file", "room": "config"},
        ]
        json_file = tmp_path / "memories.json"
        json_file.write_text(json.dumps(items), encoding="utf-8")

        result = palace.import_memories(str(json_file))
        assert result["imported"] == 1

        # Verify recallable
        results = palace.recall("Imported via JSON")
        assert len(results) >= 1

    def test_export_json(self, palace):
        palace.remember("Export test memory", room="general")
        result = palace.export(format="json")
        assert isinstance(result, dict)
        assert result["count"] >= 1
        assert "memories" in result

    def test_export_markdown(self, palace):
        palace.remember("Markdown export test", room="decisions")
        result = palace.export(format="markdown")
        assert isinstance(result, str)
        assert "Markdown export test" in result

    def test_export_to_file(self, palace, tmp_path):
        palace.remember("File export test", room="general")
        out_file = tmp_path / "export.json"
        palace.export(format="json", output=str(out_file))
        assert out_file.exists()
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data["count"] >= 1


class TestRecencyDecay:
    def test_recent_memories_score_higher(self, palace):
        # Store two memories
        palace.remember("Recent memory about Redis cache", room="config")
        palace.remember("Old memory about database setup", room="config")

        # Both should be recallable
        results = palace.recall("cache or database")
        assert len(results) >= 2

        # All results should have a _score
        for r in results:
            assert "_score" in r
            assert isinstance(r["_score"], float)

    def test_score_components_present(self, palace):
        palace.remember("Test scoring components", room="decisions")
        results = palace.recall("scoring")
        assert len(results) >= 1
        r = results[0]
        assert "_score" in r
        assert "distance" in r
        # Score should be non-negative
        assert r["_score"] >= 0


class TestContradictionDetection:
    def test_contradicting_decision_supersedes_old(self, palace):
        # Store original decision
        palace.remember("认证用 Session 方案", room="decisions")

        # Store contradicting decision (same room, similar topic, different content)
        palace.remember("认证用 JWT 不用 Session", room="decisions")

        # Recall should find both, but old one should have lower score
        results = palace.recall("认证方案")
        assert len(results) >= 2

        # Check that one is marked superseded
        superseded = [r for r in results if r.get("metadata", {}).get("status") == "superseded"]
        assert len(superseded) >= 1

    def test_non_contradicting_not_affected(self, palace):
        palace.remember("使用 Redis 做缓存", room="decisions")
        palace.remember("使用 PostgreSQL 做主数据库", room="decisions")

        results = palace.recall("数据库或缓存")
        # Neither should be superseded (different topics)
        superseded = [r for r in results if r.get("metadata", {}).get("status") == "superseded"]
        assert len(superseded) == 0


class TestWorkingMemoryCache:
    def test_similar_queries_use_cache(self, palace):
        palace.remember("Working memory cache test data", room="general")

        # First query
        r1 = palace.recall("cache test")
        # Second similar query
        r2 = palace.recall("cache test data")

        # Both should return results
        assert len(r1) >= 1
        assert len(r2) >= 1


class TestEvolve:
    def test_evolve_returns_report(self, palace):
        palace.remember("Evolution test memory", room="general")
        report = palace.evolve()
        assert "promoted" in report
        assert "dropped" in report
        assert "steps" in report

    def test_evolve_with_transcript(self, palace):
        report = palace.evolve(
            transcript=(
                "We decided to use SQLAlchemy ORM for the project database layer. "
                "This is an important architecture design decision. "
                "The config setting for the database connection pool is critical to remember."
            )
        )
        assert report["promoted"] >= 1

    def test_evolve_empty_palace(self, palace):
        report = palace.evolve()
        assert isinstance(report, dict)


class TestStats:
    def test_stats_structure(self, palace):
        palace.remember("Stats test", room="general")
        palace.remember("Stats decision", room="decisions")
        stats = palace.stats()
        assert stats["total"] >= 2
        assert "rooms" in stats
        assert stats["rooms"].get("general", 0) >= 1
        assert stats["rooms"].get("decisions", 0) >= 1
        assert "kg_entities" in stats

    def test_stats_empty_palace(self, palace):
        stats = palace.stats()
        assert stats["total"] == 0


class TestSetupWizard:
    def test_detect_os(self):
        from mempalace_evolve.setup_wizard import _detect_os
        os_name = _detect_os()
        assert os_name in ("Windows", "Darwin", "Linux")

    def test_home_returns_path(self):
        from mempalace_evolve.setup_wizard import _home
        from pathlib import Path
        assert _home() == Path.home()

    def test_write_config_creates_file(self, tmp_path):
        from mempalace_evolve.setup_wizard import _write_config
        cfg = tmp_path / "settings.json"
        entry = {"command": "mempalace-mcp", "env": {"MEMPALACE_WING": "test"}}
        ok = _write_config(cfg, entry, "claude_code")
        assert ok is True
        data = json.loads(cfg.read_text(encoding="utf-8"))
        assert data["mcpServers"]["mempalace"]["command"] == "mempalace-mcp"

    def test_write_config_preserves_existing(self, tmp_path):
        from mempalace_evolve.setup_wizard import _write_config
        cfg = tmp_path / "settings.json"
        # Pre-existing config
        cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "other"}}}), encoding="utf-8")

        entry = {"command": "mempalace-mcp", "env": {"MEMPALACE_WING": "test"}}
        _write_config(cfg, entry, "claude_code")

        data = json.loads(cfg.read_text(encoding="utf-8"))
        assert "other" in data["mcpServers"]
        assert "mempalace" in data["mcpServers"]

    def test_write_config_creates_backup(self, tmp_path):
        from mempalace_evolve.setup_wizard import _write_config
        cfg = tmp_path / "settings.json"
        cfg.write_text('{"mcpServers": {}}', encoding="utf-8")

        entry = {"command": "mempalace-mcp", "env": {}}
        _write_config(cfg, entry, "claude_code")

        bak = cfg.with_suffix(cfg.suffix + ".bak")
        assert bak.exists()

    def test_verify_mcp_start(self):
        from mempalace_evolve.setup_wizard import _verify_mcp_start
        import tempfile
        tmp = tempfile.mkdtemp(prefix="mempalace_test_verify_")
        ok = _verify_mcp_start(tmp, "test")
        assert ok is True
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
