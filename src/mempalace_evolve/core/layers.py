"""
MemPalace 4 层记忆栈
===================
L0: 身份层 (~100 tokens)
L1: 关键事实层 (~500-800 tokens, top 15 drawers)
L2: 按需检索层 (wing/room 过滤)
L3: 深度语义搜索层
MemoryStack: 统一接口
"""

import logging
from pathlib import Path

logger = logging.getLogger("mempalace.layers")

from mempalace_evolve.core.config import get_config, GLOBAL_CHROMA
from mempalace_evolve.core.chroma_helper import get_collection
from mempalace_evolve.core.lifecycle import decay_score


class Layer0:
    """身份层：读取 identity.txt"""

    def __init__(self, identity_path: str = None):
        self.identity_path = identity_path
        self._text = None

    def render(self) -> str:
        if self._text is not None:
            return self._text

        path = Path(self.identity_path) if self.identity_path else None
        if path and path.exists():
            try:
                self._text = path.read_text(encoding="utf-8").strip()
                return self._text
            except Exception:
                logger.debug("failed to read identity file", exc_info=True)

        # 确保永远不会返回 None，避免 token_estimate() 中 len(None) 崩溃
        self._text = ""
        return self._text

    def token_estimate(self) -> int:
        return len(self.render()) // 4


class Layer1:
    """关键事实层：自动提取最高权重的 top 15 条记忆"""

    MAX_DRAWERS = 15
    MAX_CHARS = 3200

    def __init__(self, palace_path: str = None, wing: str = None):
        self.palace_path = palace_path or str(GLOBAL_CHROMA)
        self.wing = wing
        self._cache = None
        self._cache_time = 0
        self._cache_ttl = 300  # 5 分钟缓存
        self._data_hash = None
        # 预编译正则（避免每次 generate 时重新编译）
        self._re_shorten = None

    def generate(self, force_refresh: bool = False) -> str:
        import time
        now = time.time()
        if not force_refresh and self._cache and (now - self._cache_time) < self._cache_ttl:
            if self._data_hash is not None:
                col_check = get_collection(self.palace_path, create=False)
                if col_check:
                    current_hash = self._quick_data_hash(col_check)
                    if current_hash == self._data_hash:
                        return self._cache
            # Data changed or no hash -> fall through

        col = get_collection(self.palace_path, create=False)
        if not col or col.count() == 0:
            self._cache = "## L1 -- 关键事实\n（Palace 为空）"
            self._cache_time = time.time()
            self._data_hash = "empty"
            return self._cache

        # 优化：如果无 wing 过滤，用向量搜索快速获取 top drawers
        # 代替全量扫描+排序，通过多次 query 按重要性范围筛选
        all_drawers = []
        where_filter = None
        if self.wing:
            where_filter = {"wing": self.wing}

        # 阶段 1: 先尝试获取高重要性 (>=0.8) 的 drawers（通常数量少）
        high_importance_drawers = self._fetch_by_importance(
            col, where_filter, min_importance=0.8, limit=self.MAX_DRAWERS
        )
        all_drawers.extend(high_importance_drawers)

        # 阶段 2: 如果高重要性不够，补充中等重要性 (>=0.4)
        if len(all_drawers) < self.MAX_DRAWERS:
            medium_drawers = self._fetch_by_importance(
                col, where_filter, min_importance=0.4, limit=self.MAX_DRAWERS * 3
            )
            # 去重（按 id）
            existing_ids = {d["_id"] for d in all_drawers}
            for d in medium_drawers:
                if d["_id"] not in existing_ids:
                    all_drawers.append(d)
                    existing_ids.add(d["_id"])

        # 阶段 3: 仍然不够时，用全量扫描（仅在 wing 过滤且数量少时）
        if len(all_drawers) < self.MAX_DRAWERS and where_filter:
            remaining = self._fetch_all_batched(col, where_filter)
            existing_ids = {d["_id"] for d in all_drawers}
            for d in remaining:
                if d["_id"] not in existing_ids:
                    all_drawers.append(d)
                    existing_ids.add(d["_id"])

        if not all_drawers:
            self._cache = "## L1 -- 关键事实\n（无可用记忆）"
            self._cache_time = time.time()
            self._data_hash = "empty"
            return self._cache

        # 按重要性排序，取 top 15
        all_drawers.sort(key=lambda d: d["score"], reverse=True)
        top = all_drawers[: self.MAX_DRAWERS]

        # 按房间分组，格式化输出
        rooms = {}
        for d in top:
            room = d["room"]
            if room not in rooms:
                rooms[room] = []
            rooms[room].append(d)

        lines = ["## L1 -- 关键事实\n"]
        total_chars = len(lines[0])

        for room, drawers in sorted(rooms.items()):
            section = f"\n### {room}\n"
            for d in drawers:
                text = d["text"]
                snippet = text[:200].replace("\n", " ").strip()
                if len(text) > 200:
                    snippet += "..."
                entry = f"- [{d['wing']}] {snippet} ({d['source']})\n"
                # 单条超限保护
                if total_chars + len(section) + len(entry) > self.MAX_CHARS:
                    lines.append(section)
                    total_chars += len(section)
                    lines.append("\n... (更多内容请用 L3 搜索)\n")
                    return "".join(lines)
                section += entry

            if total_chars + len(section) > self.MAX_CHARS:
                lines.append("\n... (更多内容请用 L3 搜索)\n")
                break

            lines.append(section)
            total_chars += len(section)

        result = "".join(lines)
        self._cache = result
        self._cache_time = now
        self._data_hash = self._quick_data_hash(col)
        return result

    # ------------------------------------------------------------------

    def _quick_data_hash(self, col):
        """Compute a lightweight hash of the collection state.
        Uses count + first 20 IDs/metadata for fast staleness detection.
        """
        try:
            count = col.count()
            if count == 0:
                return "empty"
            sample = col.get(limit=20, include=["metadatas"])
            if not sample["ids"]:
                return "empty"
            parts = [str(count)]
            for j, doc_id in enumerate(sample["ids"]):
                meta = sample["metadatas"][j] if sample["metadatas"] else {}
                w = meta.get("wing", "")
                r = meta.get("room", "")
                imp = meta.get("importance", "0.5")
                parts.append(f"{doc_id}|{w}|{r}|{imp}")
            import hashlib
            return hashlib.md5("|".join(parts).encode()).hexdigest()[:16]
        except Exception:
            return None

    # Layer1 内部辅助方法
    # ------------------------------------------------------------------

    def _fetch_by_importance(self, col, where_filter, min_importance: float,
                             limit: int) -> list[dict]:
        """按重要性下限筛选 drawers，返回已排序的列表。

        使用 ChromaDB get + Python 侧过滤代替全量扫描。
        """
        drawers = []
        try:
            fetch_limit = min(limit * 5, 500)
            kwargs = {
                "include": ["metadatas", "documents"],
                "limit": fetch_limit,
            }
            if where_filter:
                kwargs["where"] = where_filter
            results = col.get(**kwargs)
            if not results["ids"]:
                return []

            for i, doc_id in enumerate(results["ids"]):
                meta = results["metadatas"][i] if results["metadatas"] else {}
                doc = results["documents"][i] if results["documents"] else ""
                imp = float(meta.get("importance", 0.5))
                if imp >= min_importance:
                    drawers.append({
                        "_id": doc_id,
                        "text": doc,
                        "wing": meta.get("wing", "?"),
                        "room": meta.get("room", "general"),
                        "source": meta.get("source_file", "?"),
                        "score": imp,
                    })
        except Exception:
            logger.debug("_fetch_by_importance failed", exc_info=True)

        return drawers

    def _fetch_all_batched(self, col, where_filter) -> list[dict]:
        """全量获取所有 drawers（仅在前面阶段数量不足时使用）。"""
        drawers = []
        try:
            from mempalace_evolve.core.chroma_helper import get_all_metadata
            all_items = get_all_metadata(col)
            for item in all_items:
                meta = item.get("metadata", {})
                doc = item.get("document", "")
                # 应用 where_filter
                if where_filter:
                    if isinstance(where_filter, dict):
                        if "$and" in where_filter:
                            conditions = where_filter["$and"]
                            match = all(
                                meta.get(k) == v
                                for cond in conditions
                                for k, v in cond.items()
                            )
                        else:
                            match = all(
                                meta.get(k) == v
                                for k, v in where_filter.items()
                            )
                        if not match:
                            continue
                imp = float(meta.get("importance", 0.5))
                drawers.append({
                    "_id": item.get("id"),
                    "text": doc,
                    "wing": meta.get("wing", "?"),
                    "room": meta.get("room", "general"),
                    "source": meta.get("source_file", "?"),
                    "score": imp,
                })
        except Exception:
            logger.debug("_fetch_all_batched failed", exc_info=True)
        return drawers


class Layer2:
    """按需检索层：按 wing/room 过滤获取"""

    def __init__(self, palace_path: str = None):
        self.palace_path = palace_path or str(GLOBAL_CHROMA)

    def retrieve(self, wing: str = None, room: str = None, n_results: int = 10) -> str:
        col = get_collection(self.palace_path, create=False)
        if not col:
            return "## L2 -- 按需检索\n（Palace 不可用）"

        # 构建 where 过滤
        where = None
        if wing and room:
            where = {"$and": [{"wing": wing}, {"room": room}]}
        elif wing:
            where = {"wing": wing}
        elif room:
            where = {"room": room}

        try:
            results = col.get(
                where=where,
                include=["metadatas", "documents"],
                limit=n_results,
            )
        except Exception as e:
            return f"## L2 -- 按需检索\n查询失败: {e}"

        if not results["ids"]:
            return f"## L2 -- 按需检索\n（无匹配结果: wing={wing}, room={room}）"

        lines = [f"## L2 -- 按需检索 (wing={wing}, room={room})\n"]
        for i, doc_id in enumerate(results["ids"]):
            meta = results["metadatas"][i] if results["metadatas"] else {}
            doc = results["documents"][i] if results["documents"] else ""
            snippet = doc[:300].replace("\n", " ").strip()
            w = meta.get("wing", "?")
            r = meta.get("room", "?")
            src = meta.get("source_file", "?")
            lines.append(f"[{w}/{r}] {snippet} ({src})\n")

        return "".join(lines)


class Layer3:
    """深度语义搜索层"""

    def __init__(self, palace_path: str = None):
        self.palace_path = palace_path or str(GLOBAL_CHROMA)

    def search(self, query: str, wing: str = None, room: str = None,
               n_results: int = 5) -> str:
        results = self.search_raw(query, wing, room, n_results)
        if not results:
            return f'## L3 -- 搜索结果\n（无结果: "{query}"）'

        lines = [f'## L3 -- 搜索结果 "{query}"\n']
        for r in results:
            lines.append(
                f"[{r['wing']}/{r['room']}] "
                f"相似度={r['similarity']:.3f} "
                f"({r['source_file']})\n"
                f"  {r['text'][:300].replace(chr(10), ' ')}\n"
            )
        return "".join(lines)

    def search_raw(self, query: str, wing: str = None, room: str = None,
                   n_results: int = 5, time_range=None, time_bonus_weight: float = 0.0,
                   adaptive: bool = False, cross_wing_diversity: bool = False) -> list[dict]:
        # 共指消解：将查询中的代词替换为实际实体名
        _resolve_query = None
        try:
            from mempalace_evolve.core.optional.coref_resolver import resolve_query as _resolve_query
            logger.info("Coreference resolution enabled")
        except ImportError:
            logger.warning("coref_resolver not installed - coreference resolution disabled.")
        except Exception as e:
            logger.warning(f"Coreference resolution failed to load: {e}")

        if _resolve_query:
            try:
                resolved_query = _resolve_query(query)
                if resolved_query != query:
                    query = resolved_query
            except Exception as e:
                logger.debug(f"Coreference resolution failed for query: {e}")

        col = get_collection(self.palace_path, create=False)
        if not col or col.count() == 0:
            return []

        where = None
        if wing and room:
            where = {"$and": [{"wing": wing}, {"room": room}]}
        elif wing:
            where = {"wing": wing}
        elif room:
            where = {"room": room}

        # 跨翼搜索时多取一些结果用于重排
        fetch_n = n_results
        total = col.count()
        if cross_wing_diversity and not wing:
            fetch_n = min(n_results * 3, total)

        try:
            results = col.query(
                query_texts=[query],
                where=where,
                n_results=min(fetch_n, total),
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            logger.warning("L3 search query failed", exc_info=True)
            return []

        output = []
        if not results["ids"] or not results["ids"][0]:
            return output

        metas = results["metadatas"][0]
        docs = results["documents"][0]
        dists = results["distances"][0]

        for i, doc_id in enumerate(results["ids"][0]):
            meta = metas[i] if metas else {}
            doc = docs[i] if docs else ""
            dist = dists[i] if dists else 0

            # 过滤已废弃的旧版本（superseded 状态）
            if meta.get("status") == "superseded":
                continue

            output.append({
                "id": doc_id,
                "text": doc,
                "wing": meta.get("wing", "?"),
                "room": meta.get("room", "general"),
                "source_file": meta.get("source_file", "?"),
                "similarity": 1 - dist,
                "distance": dist,
                "metadata": meta,
            })

        # 自适应评分
        if adaptive and output:
            try:
                from mempalace_evolve.core.adaptive_scorer import get_wing_adjusted_confidence, adjust_scores, update_wing_baseline
                raw_distances = [r["distance"] for r in output]
                # 更新 wing 历史基线
                wing_name = wing or "global"
                update_wing_baseline(wing_name, raw_distances)
                # 用 wing 感知的置信度
                conf = get_wing_adjusted_confidence(wing_name, raw_distances)
                output = adjust_scores(output, conf)
                # 用 adjusted_similarity 替换 similarity
                for r in output:
                    r["similarity"] = r.pop("adjusted_similarity", r["similarity"])
            except Exception:
                logger.warning("adaptive scoring failed", exc_info=True)

        # 精确匹配奖励（数字和实体）— 预编译正则
        if output:
            try:
                if self._re_shorten is None:
                    import re as _re
                    self._re_shorten = (
                        _re.compile(r'\d+[\.\d]*[万亿千百]?[%％]?|[\d]+\.[\d]+'),
                        _re.compile(r'[A-Z][a-zA-Z]{2,}|[\u4e00-\u9fff]{2,4}'),
                    )
                _num_pattern, _ent_pattern = self._re_shorten
                query_nums = set(_num_pattern.findall(query))
                query_ents = set(_ent_pattern.findall(query))

                for r in output:
                    doc_text = r.get("text", "")
                    bonus = 0.0
                    # 数字精确匹配奖励
                    for num in query_nums:
                        if num in doc_text:
                            bonus += 0.08
                    # 实体精确匹配奖励
                    for ent in query_ents:
                        if ent in doc_text:
                            bonus += 0.04
                    # 上限 0.15
                    bonus = min(bonus, 0.15)
                    if bonus > 0:
                        r["similarity"] = min(1.0, r["similarity"] + bonus)
                        r["exact_match_bonus"] = round(bonus, 3)
            except Exception:
                logger.debug("exact match bonus failed", exc_info=True)

        # 时间感知加权
        _time_overlap_score = None
        if time_range and time_bonus_weight > 0 and output:
            try:
                from mempalace_evolve.core.optional.time_parser import time_overlap_score as _time_overlap_score
                logger.info("Time-aware weighting enabled")
            except ImportError:
                logger.warning("time_parser not installed - time-aware weighting disabled.")
            except Exception as e:
                logger.warning(f"Time parser failed to load: {e}")

            if _time_overlap_score:
                try:
                    q_start, q_end = time_range
                    for r in output:
                        filed_at = r["metadata"].get("filed_at", "")
                        bonus = _time_overlap_score(filed_at, q_start, q_end)
                        r["similarity"] = r["similarity"] * (1 - time_bonus_weight) + bonus * time_bonus_weight
                    output.sort(key=lambda x: -x["similarity"])
                except Exception as e:
                    logger.debug(f"Time-aware weighting failed: {e}")

        # 跨翼多样性重排
        if cross_wing_diversity and not wing and output:
            output = self._diversity_rerank(output, n_results)

        return output[:n_results]

    def _diversity_rerank(self, results: list, n_results: int) -> list:
        """
        跨翼多样性重排：轮流抽取各翼最优结果，确保多样性。
        """
        wing_groups = {}
        for r in results:
            w = r["wing"]
            if w not in wing_groups:
                wing_groups[w] = []
            wing_groups[w].append(r)

        # 每翼内按相似度排序
        for w in wing_groups:
            wing_groups[w].sort(key=lambda x: -x.get("similarity", 0))

        # 按翼的最高相似度排序翼顺序
        wings_ordered = sorted(
            wing_groups.keys(),
            key=lambda w: -wing_groups[w][0].get("similarity", 0)
        )

        # 轮流抽取
        final = []
        while len(final) < n_results and wing_groups:
            for w in wings_ordered:
                if w in wing_groups and wing_groups[w]:
                    final.append(wing_groups[w].pop(0))
                if not wing_groups.get(w):
                    del wing_groups[w]
            wings_ordered = [w for w in wings_ordered if w in wing_groups]

        return final[:n_results]

    def search_bundled(self, query: str, wing: str = None, room: str = None,
                       n_results: int = 5, max_hops: int = 2) -> dict:
        """
        增强搜索：返回直接命中 + 通过 KG 关联的记忆束。

        Returns:
            {"direct_hits": [...], "bundles": [...]}
        """
        hits = self.search_raw(query, wing=wing, room=room, n_results=n_results)

        if not hits:
            return {"direct_hits": [], "bundles": []}

        _BundleScorer = None
        try:
            from mempalace_evolve.core.optional.bundle_scorer import BundleScorer as _BundleScorer
            logger.info("Bundle scoring enabled")
        except ImportError:
            logger.warning("bundle_scorer not installed - bundle scoring disabled.")
        except Exception as e:
            logger.warning(f"Bundle scorer failed to load: {e}")

        bundles = []
        if _BundleScorer:
            try:
                from mempalace_evolve.core.knowledge_graph import KnowledgeGraph
                kg = KnowledgeGraph()
                scorer = _BundleScorer(kg=kg, palace_path=self.palace_path)
                hit_ids = [h["id"] for h in hits]
                hit_texts = [h["text"] for h in hits]
                bundles = scorer.find_bundles(hit_ids, hit_texts, max_hops=max_hops)
            except Exception as e:
                logger.warning(f"Bundle scoring failed: {e}")

        return {
            "direct_hits": hits,
            "bundles": bundles,
        }


class MemoryStack:
    """统一记忆接口"""

    def __init__(self, palace_path: str = None, identity_path: str = None):
        config = get_config()
        self.palace_path = palace_path or config.palace_path
        self.identity_path = identity_path or config.resolve_identity_path()

        self.l0 = Layer0(self.identity_path)
        self.l1 = Layer1(self.palace_path)
        self.l2 = Layer2(self.palace_path)
        self.l3 = Layer3(self.palace_path)

    def wake_up(self, wing: str = None) -> str:
        """唤醒：L0 + L1，~600-900 tokens"""
        l0_text = self.l0.render()
        self.l1 = Layer1(self.palace_path, wing=wing)
        l1_text = self.l1.generate()
        return l0_text + "\n\n" + l1_text

    def recall(self, wing: str = None, room: str = None, n_results: int = 10) -> str:
        """按需回忆：L2"""
        return self.l2.retrieve(wing, room, n_results)

    def search(self, query: str, wing: str = None, room: str = None,
               n_results: int = 5) -> str:
        """深度搜索：L3"""
        return self.l3.search(query, wing, room, n_results)

    def status(self) -> dict:
        """全层状态"""
        col = get_collection(self.palace_path, create=False)
        count = col.count() if col else 0
        return {
            "palace_path": self.palace_path,
            "total_drawers": count,
            "l0_tokens": self.l0.token_estimate(),
            "l1_max_drawers": Layer1.MAX_DRAWERS,
            "l1_max_chars": Layer1.MAX_CHARS,
        }


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="MemPalace 记忆栈")
    parser.add_argument("command", choices=["wake-up", "search", "recall", "status"])
    parser.add_argument("--query", help="搜索查询")
    parser.add_argument("--wing", help="翼/项目名")
    parser.add_argument("--room", help="房间名")
    parser.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()
    stack = MemoryStack()

    if args.command == "wake-up":
        print(stack.wake_up(wing=args.wing))
    elif args.command == "search":
        if not args.query:
            print("需要 --query 参数")
            sys.exit(1)
        print(stack.search(args.query, wing=args.wing, room=args.room, n_results=args.limit))
    elif args.command == "recall":
        print(stack.recall(wing=args.wing, room=args.room, n_results=args.limit))
    elif args.command == "status":
        import json
        print(json.dumps(stack.status(), ensure_ascii=False, indent=2))
