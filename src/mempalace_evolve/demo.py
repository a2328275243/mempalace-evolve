"""mempalace demo — one-command showcase of all features."""
import tempfile
import shutil
import time

from mempalace_evolve.terminal import (
    banner, step, bullet, dim, green, yellow, cyan, bold, divider, magenta,
)


def run_demo(keep_data: bool = False) -> None:
    """Run a self-contained demo with colored output."""
    tmp = tempfile.mkdtemp(prefix="mempalace_demo_")
    try:
        _run(tmp)
    finally:
        if not keep_data:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"\n  {dim('Demo data kept at:')} {tmp}")


def _run(palace_path: str) -> None:
    from mempalace_evolve.sdk import MemPalace

    print(banner("MemPalace Evolve — Self-Evolving Memory for AI Agents"))
    print(dim("  Zero config · One dependency · Works offline\n"))

    palace = MemPalace(palace_path, wing="demo")

    # --- Step 1: Store memories ---
    print(step(1, "存储记忆 (Store Memories)"))
    memories = [
        ("Decided to use FastAPI with PostgreSQL for the API layer", "decisions"),
        ("CORS blocked requests from localhost:3000 — fixed by adding Allow-Origin middleware", "errors"),
        ("Redis cache layer with 30-minute TTL for session data", "config"),
        ("Microservices architecture with RabbitMQ event-driven communication", "architecture"),
    ]
    for content, room in memories:
        did = palace.remember(content, room=room)
        print(bullet(f"[{room}] {content[:60]}"))
    print(dim(f"      → 已存储 {len(memories)} 条记忆"))

    # --- Step 2: Semantic search ---
    print(step(2, "语义搜索 (Semantic Search)"))
    queries = [
        ("cross-origin request handling", "CORS"),
        ("which database do we use", "PostgreSQL"),
        ("how do services communicate", "RabbitMQ"),
    ]
    for query, expect_keyword in queries:
        results = palace.recall(query, limit=1, threshold=1.5)
        if results:
            r = results[0]
            dist = r["distance"]
            content = r["content"][:60]
            score_color = green if dist < 0.4 else yellow
            print(f"      {cyan('Q:')} {query}")
            print(f"      {green('→')} {content}  {score_color(f'[{dist:.3f}]')}")
        else:
            print(f"      {cyan('Q:')} {query}  {dim('(no match)')}")

    # --- Step 3: Knowledge graph ---
    print(step(3, "知识图谱 (Knowledge Graph)"))
    facts = [
        ("API", "built_with", "FastAPI"),
        ("API", "stores_data_in", "PostgreSQL"),
        ("API", "caches_with", "Redis"),
        ("System", "uses", "RabbitMQ"),
        ("RabbitMQ", "enables", "事件驱动架构"),
    ]
    for s, p, o in facts:
        palace.add_fact(s, p, o)
    print(dim(f"      → 已添加 {len(facts)} 条知识三元组"))

    rels = palace.query_entity("API")
    print(f"      {bold('查询: API 的关系')}")
    for r in rels:
        print(f"        {magenta(r['subject'])} ─{r['predicate']}→ {cyan(r['object'])}")

    # --- Step 4: Evolution pipeline ---
    print(step(4, "进化管道 (Evolution Pipeline)"))
    transcript = (
        "We decided to use JWT for authentication with 24-hour token expiry.\n"
        "The session-based approach was rejected due to scalability concerns.\n"
        "Error: Redis connection timeout — increased pool timeout from 5s to 30s.\n"
        "Config: log level set to INFO, debug mode disabled in production.\n"
    )
    report = palace.evolve(transcript=transcript)
    promoted = report.get("promoted", 0)
    dropped = report.get("dropped", 0)
    candidates = report.get("candidates", 0)
    print(f"      候选提取: {cyan(str(candidates))} 条")
    print(f"      晋升存储: {green(str(promoted))} 条")
    print(f"      丢弃低分: {dim(str(dropped))} 条")

    # --- Step 5: Summary ---
    print(step(5, "总结 (Summary)"))
    print(divider())
    total = len(memories) + promoted
    print(f"      记忆总数: {bold(str(total))}")
    print(f"      知识图谱: {bold(str(len(facts)))} 条三元组")
    print(f"      进化管道: 从对话中自动提取并存储了 {green(str(promoted))} 条新记忆")
    print(divider())
    print()
    print(bold(green("  ✓ Demo 完成！")))
    print(dim("    安装后即可使用: from mempalace_evolve import MemPalace"))
    print(dim("    更多用法: mempalace --help | mempalace playground"))
    print()


if __name__ == "__main__":
    run_demo()
