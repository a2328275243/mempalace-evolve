"""Example: Minimal SDK usage — the simplest way to add memory to any agent.

Run:
    pip install mempalace-evolve
    python sdk_basic.py
"""

from mempalace_evolve import MemPalace


def main():
    palace = MemPalace("./demo-memory", wing="my_project")

    # Store memories
    palace.remember("JWT authentication with 24-hour token expiry", room="decisions")
    palace.remember("Database: PostgreSQL 15, ORM: SQLAlchemy 2.0", room="config")
    palace.remember("Error: CORS blocked — fixed by adding middleware", room="errors")

    # Semantic search (no exact match needed)
    results = palace.recall("how does auth work")
    print("Search: 'how does auth work'")
    for r in results:
        print(f"  [{r['distance']:.3f}] {r['content']}")

    # Knowledge graph
    palace.add_fact("api", "built_with", "FastAPI")
    palace.add_fact("api", "connects_to", "PostgreSQL")
    rels = palace.query_entity("api")
    print(f"\nKnowledge graph for 'api': {rels}")

    # Evolution: extract memories from a transcript
    report = palace.evolve(transcript="""
    We decided to use Celery for background jobs instead of Python's threading.
    The reason is we need task persistence and retry logic.
    Error: Redis connection timeout — increased timeout from 5s to 30s.
    """)
    print(f"\nEvolution report: {report['promoted']} promoted, {report['dropped']} dropped")


if __name__ == "__main__":
    main()
