"""Basic MemPalace SDK usage."""

from mempalace_evolve import MemPalace


def main():
    palace = MemPalace("basic_demo", wing="demo")

    memory_ids = [
        palace.remember("The project uses ChromaDB for vector storage", room="architecture"),
        palace.remember("Use environment variables for API keys, never hardcode", room="security"),
        palace.remember("FastAPI is used for the REST API layer", room="architecture"),
    ]
    print(f"Stored {len(memory_ids)} memories")

    results = palace.recall("How is the API implemented?", limit=3)
    for result in results:
        print(f"[{result['distance']:.3f}] {result['content']}")

    palace.add_fact("mempalace-evolve", "uses", "ChromaDB")
    stats = palace.stats()
    print(f"Memories: {stats['total']}; KG entities: {stats['kg_entities']}")

    for memory_id in memory_ids:
        palace.forget(memory_id)


if __name__ == "__main__":
    main()
