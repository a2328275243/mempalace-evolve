"""Benchmark script for MemPalace Evolve.

Measures:
    - Store throughput (memories/sec)
    - Recall latency (ms)
    - Evolution throughput
    - Memory usage
"""

from __future__ import annotations

import time
import argparse
from pathlib import Path

from mempalace_evolve import MemPalace


def benchmark_store(mem: MemPalace, count: int = 100):
    """Benchmark memory storage throughput."""
    start = time.perf_counter()
    for i in range(count):
        mem.store_memory(
            content=f"Benchmark memory entry {i}: The system uses a custom caching layer for vector search results.",
            category="benchmark",
            importance=0.5,
        )
    elapsed = time.perf_counter() - start
    throughput = count / elapsed
    print(f"  Store: {count} memories in {elapsed:.2f}s ({throughput:.1f} mem/s)")
    return throughput


def benchmark_recall(mem: MemPalace, count: int = 50):
    """Benchmark semantic recall latency."""
    queries = [
        "How does the caching system work?",
        "What is the search pipeline?",
        "Describe the memory evolution process",
        "How are conflicts detected?",
        "What is the knowledge graph schema?",
    ] * (count // 5 + 1)

    start = time.perf_counter()
    for q in queries[:count]:
        mem.recall(q)
    elapsed = time.perf_counter() - start
    avg_latency = (elapsed / count) * 1000  # ms
    print(f"  Recall: {count} queries in {elapsed:.2f}s ({avg_latency:.1f} ms avg)")
    return avg_latency


def main():
    parser = argparse.ArgumentParser(description="MemPalace Evolve Benchmark")
    parser.add_argument("--count", type=int, default=100, help="Number of operations")
    parser.add_argument("--path", type=str, default="./benchmark_palace", help="Palace path")
    args = parser.parse_args()

    print(f"MemPalace Evolve Benchmark ({args.count} ops)")
    print("=" * 60)

    path = Path(args.path)
    if path.exists():
        import shutil
        shutil.rmtree(path)

    mem = MemPalace(str(path), wing="benchmark")

    print("\n[1/3] Store Benchmark")
    throughput = benchmark_store(mem, args.count)

    print("\n[2/3] Recall Benchmark")
    avg_latency = benchmark_recall(mem, args.count)

    print("\n[3/3] Evolution Benchmark")
    start = time.perf_counter()
    mem.evolve()
    elapsed = time.perf_counter() - start
    print(f"  Evolution: {elapsed:.2f}s")

    stats = mem.get_stats()
    print(f"\nPalace Stats: {stats}")

    # Cleanup
    import shutil
    shutil.rmtree(path)

    print("\n" + "=" * 60)
    print("Benchmark complete!")


if __name__ == "__main__":
    main()
