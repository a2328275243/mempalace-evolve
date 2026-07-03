"""Benchmarks for mempalace-evolve core operations.

Run with: python -m pytest tests/benchmarks/ -v
For detailed timing: python -m pytest tests/benchmarks/ -v --benchmark-only
"""

import time
from pathlib import Path
import pytest
import tempfile
import shutil


@pytest.fixture(scope="module")
def bench_dir():
    d = Path(tempfile.mkdtemp(prefix="mempalace_bench_"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_mempalace_init(bench_dir):
    """Benchmark MemPalace initialization."""
    from mempalace_evolve import MemPalace

    start = time.perf_counter()
    palace = MemPalace(str(bench_dir / "init_test"), wing="bench")
    elapsed = time.perf_counter() - start
    palace.close()
    assert elapsed < 5.0, f"Init took {elapsed:.2f}s (expected <5s)"
    print(f"\n  MemPalace init: {elapsed:.3f}s")


def test_remember_throughput(bench_dir):
    """Benchmark remember throughput (memories/sec)."""
    from mempalace_evolve import MemPalace

    palace = MemPalace(str(bench_dir / "throughput_test"), wing="bench")
    n = 100
    start = time.perf_counter()
    for i in range(n):
        palace.remember(f"Benchmark memory number {i}", room="bench")
    elapsed = time.perf_counter() - start
    palace.close()
    rate = n / elapsed if elapsed > 0 else 0
    print(f"\n  Remember {n} items: {elapsed:.3f}s ({rate:.0f} items/sec)")
    assert rate > 10, f"Throughput too low: {rate:.0f} items/sec"


def test_recall_latency(bench_dir):
    """Benchmark recall latency."""
    from mempalace_evolve import MemPalace

    palace = MemPalace(str(bench_dir / "latency_test"), wing="bench")
    # Seed some memories
    for i in range(50):
        palace.remember(f"Cached search result #{i} for query diversity", room="bench")

    n = 20
    latencies = []
    for _ in range(n):
        start = time.perf_counter()
        palace.recall("search result diversity", room="bench", limit=5)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

    palace.close()
    avg = sum(latencies) / len(latencies)
    p99 = sorted(latencies)[-1]
    print(f"\n  Recall avg: {avg*1000:.1f}ms, p99: {p99*1000:.1f}ms")
    assert avg < 2.0, f"Avg recall latency too high: {avg*1000:.1f}ms"


def test_batch_remember_vs_individual(bench_dir):
    """Benchmark batch_add_drawers vs individual add_drawer."""
    from mempalace_evolve.core.chroma_helper import get_collection, batch_add_drawers, add_drawer

    col = get_collection(str(bench_dir / "batch_bench"), create=True)
    n = 50

    # Individual
    start = time.perf_counter()
    for i in range(n):
        add_drawer(col, "bench", "batch", f"Individual memory #{i}",
                   source_file="bench.py", chunk_index=i)
    individual_time = time.perf_counter() - start

    # Clean up
    col.delete(where={"room": "batch"})

    # Batch
    drawers = [
        {
            "wing": "bench",
            "room": "batch",
            "content": f"Batch memory #{i}",
            "source_file": "bench.py",
            "chunk_index": i,
        }
        for i in range(n)
    ]
    start = time.perf_counter()
    added, skipped = batch_add_drawers(col, drawers)
    batch_time = time.perf_counter() - start

    improvement = (individual_time - batch_time) / individual_time * 100 if individual_time > 0 else 0
    print(f"\n  Individual: {individual_time:.3f}s, Batch: {batch_time:.3f}s ({improvement:.0f}% faster)")
    assert added == n, f"Expected {n} added, got {added}"


def test_async_sdk_throughput(bench_dir):
    """Benchmark async SDK operations."""
    import asyncio
    from mempalace_evolve import AsyncMemPalace

    async def run():
        async with AsyncMemPalace(str(bench_dir / "async_bench"), wing="bench") as palace:
            n = 50
            start = time.perf_counter()
            for i in range(n):
                await palace.remember(f"Async memory #{i}", room="bench")
            elapsed = time.perf_counter() - start
            rate = n / elapsed if elapsed > 0 else 0
            print(f"\n  Async remember {n} items: {elapsed:.3f}s ({rate:.0f} items/sec)")

    asyncio.run(run())


def test_knowledge_graph_operations(bench_dir):
    """Benchmark knowledge graph fact addition and query."""
    from mempalace_evolve import MemPalace

    palace = MemPalace(str(bench_dir / "kg_bench"), wing="bench")
    n = 50
    start = time.perf_counter()
    for i in range(n):
        palace.add_fact(f"Entity{i}", f"relation_{i%10}", f"Value{i}")
    elapsed = time.perf_counter() - start
    rate = n / elapsed if elapsed > 0 else 0
    print(f"\n  KG facts ({n}): {elapsed:.3f}s ({rate:.0f} facts/sec)")

    # Query
    start = time.perf_counter()
    for i in range(10):
        palace.query_entity(f"Entity{i}", direction="outgoing")
    query_time = time.perf_counter() - start
    print(f"  KG queries (10): {query_time*1000:.1f}ms")
    palace.close()
