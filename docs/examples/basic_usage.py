"""
Basic Usage Example - MemPalace Evolve

This example demonstrates the core SDK operations:
- Initialize a memory palace
- Store memories (remember)
- Retrieve memories (recall)
- Delete memories (forget)
"""
from mempalace_evolve import MemPalace

# Initialize with a local storage path
palace = MemPalace("basic_demo")

# 1. Store some memories
print("=== Storing memories ===")
mem1 = palace.remember("The project uses ChromaDB for vector storage", room="architecture")
print(f"  Stored: {mem1}")

mem2 = palace.remember("Use environment variables for API keys, never hardcode", room="security")
print(f"  Stored: {mem2}")

mem3 = palace.remember("FastAPI is used for the REST API layer", room="architecture")
print(f"  Stored: {mem3}")

# 2. Recall relevant memories
print("\n=== Recalling memories about architecture ===")
results = palace.recall("How is the API implemented?", limit=3)
for r in results:
    print(f"  [{r.get('distance', '?'):.3f}] {r.get('content', '')}")

# 3. Add a fact to the knowledge graph
print("\n=== Adding knowledge graph fact ===")
fact_id = palace.add_fact("mempalace-evolve", "uses", "ChromaDB", confidence=0.95)
print(f"  Fact ID: {fact_id}")

# 4. Get stats
stats = palace.stats()
print(f"\n=== Palace Stats ===")
print(f"  Memories: {stats.get('total_memories', 0)}")
print(f"  Facts: {stats.get('total_facts', 0)}")

# 5. Clean up
palace.forget(mem1)
palace.forget(mem2)
palace.forget(mem3)
print("\nCleaned up demo memories.")
