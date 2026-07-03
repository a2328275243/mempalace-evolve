"""
knowledge_graph.py — Temporal Entity-Relationship Graph for MemPalace
=====================================================================

Real knowledge graph with:
  - Entity nodes (people, projects, tools, concepts)
  - Typed relationship edges (daughter_of, does, loves, works_on, etc.)
  - Temporal validity (valid_from → valid_to — knows WHEN facts are true)
  - Closet references (links back to the verbatim memory)

Storage: SQLite (local, no dependencies, no subscriptions)
Query: entity-first traversal with time filtering

This is what competes with Zep's temporal knowledge graph.
Zep uses Neo4j in the cloud ($25/mo+). We use SQLite locally (free).

Usage:
    from mempalace.knowledge_graph import KnowledgeGraph

    kg = KnowledgeGraph()
    kg.add_triple("Max", "child_of", "Alice", valid_from="2015-04-01")
    kg.add_triple("Max", "does", "swimming", valid_from="2025-01-01")
    kg.add_triple("Max", "loves", "chess", valid_from="2025-10-01")

    # Query: everything about Max
    kg.query_entity("Max")

    # Query: what was true about Max in January 2026?
    kg.query_entity("Max", as_of="2026-01-15")

    # Query: who is connected to Alice?
    kg.query_entity("Alice", direction="both")

    # Invalidate: Max's sports injury resolved
    kg.invalidate("Max", "has_issue", "sports_injury", ended="2026-02-15")
"""

import atexit
import hashlib
import json
import logging
import os
import sqlite3
from datetime import date, datetime, timezone
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("mempalace.kg")


DEFAULT_KG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_graph.sqlite3")


class KnowledgeGraph:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_KG_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._persistent_conn = None
        self._init_db()
        atexit.register(self.close)

    def close(self):
        """Close the persistent SQLite connection safely."""
        if self._persistent_conn is not None:
            try:
                self._persistent_conn.close()
            except Exception:
                pass
            self._persistent_conn = None

    def _init_db(self):
        conn = self._new_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT DEFAULT 'unknown',
                properties TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS triples (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                valid_from TEXT,
                valid_to TEXT,
                confidence REAL DEFAULT 1.0,
                source_closet TEXT,
                source_file TEXT,
                extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject) REFERENCES entities(id),
                FOREIGN KEY (object) REFERENCES entities(id)
            );

            CREATE INDEX IF NOT EXISTS idx_triples_subject ON triples(subject);
            CREATE INDEX IF NOT EXISTS idx_triples_object ON triples(object);
            CREATE INDEX IF NOT EXISTS idx_triples_predicate ON triples(predicate);
            CREATE INDEX IF NOT EXISTS idx_triples_valid ON triples(valid_from, valid_to);
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
        """)

        # 安全迁移：添加 canonical_name 列（幂等）
        try:
            conn.execute("ALTER TABLE entities ADD COLUMN canonical_name TEXT")
        except Exception:
            pass  # 列已存在

        # canonical_name 索引必须在 ALTER TABLE 之后创建
        try:
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_canonical_name ON entities(canonical_name);
            """)
        except Exception:
            logger.debug("canonical_name index creation skipped")

        # 迁移记录表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 记录此次迁移
        try:
            conn.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                (1, "add_canonical_name")
            )
        except Exception:
            pass  # 已记录

        conn.commit()
        conn.close()


    def _new_conn(self):
        """Create a new connection with optimized WAL-mode PRAGMAs."""
        if self.db_path == ":memory:":
            # Shared cache so multiple connections see the same in-memory database
            conn = sqlite3.connect("file::memory:?cache=shared", uri=True)
        else:
            conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA foreign_keys=ON")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @contextmanager
    def _get_conn(self):
        """Context manager yielding an optimized connection."""
        conn = self._new_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    def _conn(self):
        """获取持久数据库连接。首次调用时初始化 PRAGMA，后续复用同一连接。"""
        if self._persistent_conn is not None:
            try:
                self._persistent_conn.execute("SELECT 1")
                return self._persistent_conn
            except Exception:
                self._persistent_conn = None

        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        self._persistent_conn = conn
        return conn

    def _entity_id(self, name: str) -> str:
        return name.lower().replace(" ", "_").replace("'", "")

    # ── Write operations ──────────────────────────────────────────────────

    def add_entity(self, name: str, entity_type: str = "unknown", properties: dict = None):
        """Add or update an entity node."""
        eid = self._entity_id(name)
        props = json.dumps(properties or {})
        with self._get_conn() as conn:
            # Preserve existing canonical_name on update
            existing = conn.execute(
                "SELECT canonical_name FROM entities WHERE id=?", (eid,)
            ).fetchone()
            canonical = existing[0] if existing and existing[0] else None

            if canonical:
                conn.execute(
                    "INSERT OR REPLACE INTO entities (id, name, type, properties, canonical_name) VALUES (?, ?, ?, ?, ?)",
                    (eid, name, entity_type, props, canonical),
                )
            else:
                conn.execute(
                    "INSERT OR REPLACE INTO entities (id, name, type, properties) VALUES (?, ?, ?, ?)",
                    (eid, name, entity_type, props),
                )
            conn.commit()

            return eid

    def remove_entity(self, name: str) -> bool:
        """Remove an entity and all its relationships.

        Args:
            name: Entity name to remove.

        Returns:
            True if entity was removed, False if not found.
        """
        eid = self._entity_id(name)
        with self._get_conn() as conn:

            # Delete triples where this entity is subject or object (by entity ID)
            conn.execute("DELETE FROM triples WHERE subject=? OR object=?", (eid, eid))

            # Delete the entity itself
            conn.execute("PRAGMA foreign_keys = OFF")
            cursor = conn.execute("DELETE FROM entities WHERE id=?", (eid,))
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()

            return cursor.rowcount > 0

    def add_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        valid_from: str = None,
        valid_to: str = None,
        confidence: float = 1.0,
        source_closet: str = None,
        source_file: str = None,
    ):
        """
        Add a relationship triple: subject → predicate → object.

        Examples:
            add_triple("Max", "child_of", "Alice", valid_from="2015-04-01")
            add_triple("Max", "does", "swimming", valid_from="2025-01-01")
            add_triple("Alice", "worried_about", "Max injury", valid_from="2026-01", valid_to="2026-02")
        """
        sub_id = self._entity_id(subject)
        obj_id = self._entity_id(obj)
        pred = predicate.lower().replace(" ", "_")

        # Auto-create entities if they don't exist
        with self._get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO entities (id, name) VALUES (?, ?)", (sub_id, subject))
            conn.execute("INSERT OR IGNORE INTO entities (id, name) VALUES (?, ?)", (obj_id, obj))

            # Check for existing identical triple
            existing = conn.execute(
                "SELECT id FROM triples WHERE subject=? AND predicate=? AND object=? AND valid_to IS NULL",
                (sub_id, pred, obj_id),
            ).fetchone()

            if existing:

                return existing[0]  # Already exists and still valid

            triple_id = f"t_{sub_id}_{pred}_{obj_id}_{hashlib.md5(f'{valid_from}{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:8]}"

            conn.execute(
                """INSERT INTO triples (id, subject, predicate, object, valid_from, valid_to, confidence, source_closet, source_file)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    triple_id,
                    sub_id,
                    pred,
                    obj_id,
                    valid_from,
                    valid_to,
                    confidence,
                    source_closet,
                    source_file,
                ),
            )
            conn.commit()

            return triple_id

    def invalidate(self, subject: str, predicate: str, obj: str, ended: str = None):
        """Mark a relationship as no longer valid (set valid_to date)."""
        sub_id = self._entity_id(subject)
        obj_id = self._entity_id(obj)
        pred = predicate.lower().replace(" ", "_")
        ended = ended or datetime.now(timezone.utc).date().isoformat()

        with self._get_conn() as conn:
            conn.execute(
                "UPDATE triples SET valid_to=? WHERE subject=? AND predicate=? AND object=? AND valid_to IS NULL",
                (ended, sub_id, pred, obj_id),
            )
            conn.commit()


            # ── Canonical name operations ──────────────────────────────────────────

    def set_canonical_name(self, name: str, canonical: str):
        """设置实体的规范名（仅更新 display field，不改变 id）"""
        eid = self._entity_id(name)
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE entities SET canonical_name=? WHERE id=?",
                (canonical, eid),
            )
            conn.commit()


    def query_entity_by_canonical(self, canonical: str, direction: str = "both",
                                   as_of: str = None) -> list:
        """通过规范名查询实体关系（查询所有 canonical_name 匹配的实体）"""
        with self._get_conn() as conn:
            matching_ids = conn.execute(
                "SELECT id FROM entities WHERE canonical_name=? OR name=?",
                (canonical, canonical),
            ).fetchall()


            time_filter = ""
            time_params = []
            if as_of:
                time_filter = " AND (t.valid_from IS NULL OR t.valid_from <= ?) AND (t.valid_to IS NULL OR t.valid_to >= ?)"
                time_params = [as_of, as_of]

            results = []
            for (eid,) in matching_ids:
                if direction == "both":
                    query = (
                        "SELECT 'outgoing' as dir, t.*, e.name as other_name FROM triples t"
                        " JOIN entities e ON t.object = e.id WHERE t.subject = ?"
                        + time_filter
                        + " UNION ALL "
                        "SELECT 'incoming' as dir, t.*, e.name as other_name FROM triples t"
                        " JOIN entities e ON t.subject = e.id WHERE t.object = ?"
                        + time_filter
                    )
                    params = [eid] + time_params + [eid] + time_params
                    for row in conn.execute(query, params).fetchall():
                        dir_flag = row[0]
                        if dir_flag == "outgoing":
                            results.append({
                                "direction": "outgoing",
                                "subject": canonical,
                                "predicate": row[3],
                                "object": row[11],
                                "valid_from": row[5],
                                "valid_to": row[6],
                                "current": row[6] is None,
                            })
                        else:
                            results.append({
                                "direction": "incoming",
                                "subject": row[11],
                                "predicate": row[3],
                                "object": canonical,
                                "valid_from": row[5],
                                "valid_to": row[6],
                                "current": row[6] is None,
                            })
                elif direction == "outgoing":
                    query = "SELECT t.*, e.name as obj_name FROM triples t JOIN entities e ON t.object = e.id WHERE t.subject = ?"
                    params = [eid]
                    if as_of:
                        query += time_filter
                        params.extend(time_params)
                    for row in conn.execute(query, params).fetchall():
                        results.append({
                            "direction": "outgoing",
                            "subject": canonical,
                            "predicate": row[2],
                            "object": row[10],
                            "valid_from": row[4],
                            "valid_to": row[5],
                            "current": row[5] is None,
                        })
                elif direction == "incoming":
                    query = "SELECT t.*, e.name as sub_name FROM triples t JOIN entities e ON t.subject = e.id WHERE t.object = ?"
                    params = [eid]
                    if as_of:
                        query += time_filter
                        params.extend(time_params)
                    for row in conn.execute(query, params).fetchall():
                        results.append({
                            "direction": "incoming",
                            "subject": row[10],
                            "predicate": row[2],
                            "object": canonical,
                            "valid_from": row[4],
                            "valid_to": row[5],
                            "current": row[5] is None,
                        })

            return results

    def get_all_entity_names(self) -> list:
        """获取所有实体名（含 canonical_name）"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT name, canonical_name FROM entities"
            ).fetchall()

            return [{"name": r[0], "canonical_name": r[1]} for r in rows]

            # ── Query operations ──────────────────────────────────────────────────

    def query_entity(self, name: str, as_of: str = None, direction: str = "outgoing"):
        """
        Get all relationships for an entity.

        direction: "outgoing" (entity → ?), "incoming" (? → entity), "both"
        as_of: date string — only return facts valid at that time
        """
        eid = self._entity_id(name)
        with self._get_conn() as conn:

            results = []
            time_filter = ""
            time_params = []
            if as_of:
                time_filter = " AND (t.valid_from IS NULL OR t.valid_from <= ?) AND (t.valid_to IS NULL OR t.valid_to >= ?)"
                time_params = [as_of, as_of]

            if direction == "both":
                # 合并 outgoign + incoming 为单次查询（避免两次 JOIN）
                query = (
                    "SELECT 'outgoing' as dir, t.*, e.name as other_name FROM triples t"
                    " JOIN entities e ON t.object = e.id WHERE t.subject = ?"
                    + time_filter
                    + " UNION ALL "
                    "SELECT 'incoming' as dir, t.*, e.name as other_name FROM triples t"
                    " JOIN entities e ON t.subject = e.id WHERE t.object = ?"
                    + time_filter
                )
                params = [eid] + time_params + [eid] + time_params
                for row in conn.execute(query, params).fetchall():
                    dir_flag = row[0]
                    if dir_flag == "outgoing":
                        results.append({
                            "direction": "outgoing",
                            "subject": name,
                            "predicate": row[3],
                            "object": row[11],
                            "valid_from": row[5],
                            "valid_to": row[6],
                            "confidence": row[7],
                            "source_closet": row[8],
                            "current": row[6] is None,
                        })
                    else:
                        results.append({
                            "direction": "incoming",
                            "subject": row[11],
                            "predicate": row[3],
                            "object": name,
                            "valid_from": row[5],
                            "valid_to": row[6],
                            "confidence": row[7],
                            "source_closet": row[8],
                            "current": row[6] is None,
                        })
            elif direction == "outgoing":
                query = "SELECT t.*, e.name as obj_name FROM triples t JOIN entities e ON t.object = e.id WHERE t.subject = ?"
                params = [eid]
                if as_of:
                    query += " AND (t.valid_from IS NULL OR t.valid_from <= ?) AND (t.valid_to IS NULL OR t.valid_to >= ?)"
                    params.extend([as_of, as_of])
                for row in conn.execute(query, params).fetchall():
                    results.append({
                        "direction": "outgoing",
                        "subject": name,
                        "predicate": row[2],
                        "object": row[10],
                        "valid_from": row[4],
                        "valid_to": row[5],
                        "confidence": row[6],
                        "source_closet": row[7],
                        "current": row[5] is None,
                    })
            elif direction == "incoming":
                query = "SELECT t.*, e.name as sub_name FROM triples t JOIN entities e ON t.subject = e.id WHERE t.object = ?"
                params = [eid]
                if as_of:
                    query += " AND (t.valid_from IS NULL OR t.valid_from <= ?) AND (t.valid_to IS NULL OR t.valid_to >= ?)"
                    params.extend([as_of, as_of])
                for row in conn.execute(query, params).fetchall():
                    results.append({
                        "direction": "incoming",
                        "subject": row[10],
                        "predicate": row[2],
                        "object": name,
                        "valid_from": row[4],
                        "valid_to": row[5],
                        "confidence": row[6],
                        "source_closet": row[7],
                        "current": row[5] is None,
                    })


            return results

    def query_relationship(self, predicate: str, as_of: str = None):
        """Get all triples with a given relationship type."""
        pred = predicate.lower().replace(" ", "_")
        with self._get_conn() as conn:
            query = """
                SELECT t.*, s.name as sub_name, o.name as obj_name
                FROM triples t
                JOIN entities s ON t.subject = s.id
                JOIN entities o ON t.object = o.id
                WHERE t.predicate = ?
            """
            params = [pred]
            if as_of:
                query += " AND (t.valid_from IS NULL OR t.valid_from <= ?) AND (t.valid_to IS NULL OR t.valid_to >= ?)"
                params.extend([as_of, as_of])

            results = []
            for row in conn.execute(query, params).fetchall():
                results.append(
                    {
                        "subject": row[10],
                        "predicate": pred,
                        "object": row[11],
                        "valid_from": row[4],
                        "valid_to": row[5],
                        "current": row[5] is None,
                    }
                )

            return results

    def timeline(self, entity_name: str = None):
        """Get all facts in chronological order, optionally filtered by entity."""
        with self._get_conn() as conn:
            if entity_name:
                eid = self._entity_id(entity_name)
                rows = conn.execute(
                    """
                    SELECT t.*, s.name as sub_name, o.name as obj_name
                    FROM triples t
                    JOIN entities s ON t.subject = s.id
                    JOIN entities o ON t.object = o.id
                    WHERE (t.subject = ? OR t.object = ?)
                    ORDER BY CASE WHEN t.valid_from IS NULL THEN 1 ELSE 0 END, t.valid_from ASC
                    LIMIT 100
                """,
                    (eid, eid),
                ).fetchall()
            else:
                rows = conn.execute("""
                    SELECT t.*, s.name as sub_name, o.name as obj_name
                    FROM triples t
                    JOIN entities s ON t.subject = s.id
                    JOIN entities o ON t.object = o.id
                    ORDER BY CASE WHEN t.valid_from IS NULL THEN 1 ELSE 0 END, t.valid_from ASC
                    LIMIT 100
                """).fetchall()


            return [
                {
                    "subject": r[10],
                    "predicate": r[2],
                    "object": r[11],
                    "valid_from": r[4],
                    "valid_to": r[5],
                    "current": r[5] is None,
                }
                for r in rows
            ]

            # ── Stats ─────────────────────────────────────────────────────────────

    def import_triples(self, triples: list[dict]) -> dict:
        """Import multiple triples in a batch operation.
        Args:
            triples: List of triples, each with:
                - subject (str, required)
                - predicate (str, optional, default "related_to")
                - object (str, required, the object entity)
                - valid_from (str, optional)
                - valid_to (str, optional)
                - confidence (float, optional, default 1.0)
                - source_closet (str, optional)
                - source_file (str, optional)
        Returns:
            {"added": int, "skipped": int, "total": int}
        """
        added = 0
        skipped = 0
        for t in triples:
            try:
                self.add_triple(
                    subject=t["subject"],
                    predicate=t.get("predicate", "related_to"),
                    obj=t["object"],
                    valid_from=t.get("valid_from"),
                    valid_to=t.get("valid_to"),
                    confidence=t.get("confidence", 1.0),
                    source_closet=t.get("source_closet"),
                    source_file=t.get("source_file"),
                )
                added += 1
            except Exception as e:
                logger.warning("Skipped triple import: %s", e)
                skipped += 1
        return {"added": added, "skipped": skipped, "total": len(triples)}

    def find_entity_by_fuzzy(self, name: str, threshold: float = 0.6) -> list[dict]:
        """Fuzzy-match entity names, useful for 'did you mean?' scenarios.
        Uses SQLite LIKE for substring matching and difflib for similarity.
        Args:
            name: Entity name to search for.
            threshold: Minimum similarity ratio (0-1).
        Returns:
            List of matching entities with name, type, and similarity.
        """
        from difflib import SequenceMatcher
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT name, type, properties FROM entities"
            ).fetchall()
        matches = []
        for row in rows:
            ename = row[0]
            if ename.lower() == name.lower():
                matches.append({"name": ename, "type": row[1], "similarity": 1.0})
                continue
            if name.lower() in ename.lower() or ename.lower() in name.lower():
                ratio = len(name) / max(len(ename), 1) if len(ename) >= len(name) else len(ename) / max(len(name), 1)
                matches.append({"name": ename, "type": row[1], "similarity": round(ratio, 3)})
                continue
            ratio = SequenceMatcher(None, name.lower(), ename.lower()).ratio()
            if ratio >= threshold:
                matches.append({"name": ename, "type": row[1], "similarity": round(ratio, 3)})
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches

    def graph_traverse(self, start_entity: str, max_depth: int = 2, direction: str = "both") -> list[dict]:
        """Traverse the knowledge graph from a starting entity using BFS.
        Returns edges found at each depth level.
        Args:
            start_entity: Name of the starting entity.
            max_depth: Maximum traversal depth (default 2).
            direction: "outgoing", "incoming", or "both".
        Returns:
            List of edges with depth, subject, predicate, object.
        """
        visited_entities = set()
        edges = []
        current_level = {start_entity}
        for depth in range(max_depth):
            if not current_level:
                break
            next_level = set()
            for entity in current_level:
                if entity in visited_entities:
                    continue
                visited_entities.add(entity)
                if direction in ("outgoing", "both"):
                    for rel in self.query_entity(entity, direction="outgoing"):
                        if rel.get("current", True):
                            edges.append({
                                "depth": depth + 1,
                                "subject": entity,
                                "predicate": rel["predicate"],
                                "object": rel["object"],
                            })
                            next_level.add(rel["object"])
                if direction in ("incoming", "both"):
                    for rel in self.query_entity(entity, direction="incoming"):
                        if rel.get("current", True):
                            edges.append({
                                "depth": depth + 1,
                                "subject": rel["subject"],
                                "predicate": rel["predicate"],
                                "object": entity,
                            })
                            next_level.add(rel["subject"])
            current_level = next_level - visited_entities
        return edges

    def stats(self):
        with self._get_conn() as conn:
            # 合并 3 次 COUNT 为单次查询
            row = conn.execute(
                "SELECT COUNT(*) FROM entities;"
            ).fetchone()
            entities = row[0]
            row = conn.execute(
                "SELECT COUNT(*) as total, SUM(CASE WHEN valid_to IS NULL THEN 1 ELSE 0 END) as current FROM triples"
            ).fetchone()
            triples = row[0]
            current = row[1]
            expired = triples - current
            predicates = [
                r[0]
                for r in conn.execute(
                    "SELECT DISTINCT predicate FROM triples ORDER BY predicate"
                ).fetchall()
            ]

            return {
                "entities": entities,
                "triples": triples,
                "current_facts": current,
                "expired_facts": expired,
                "relationship_types": predicates,
            }


