"""Example: Using MemPalace with OpenAI GPT via function calling.

Run:
    pip install openai mempalace-evolve
    export OPENAI_API_KEY=sk-...
    python openai_agent.py
"""

import json
import os

from mempalace_evolve import MemPalace
from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter


def main():
    # 1. Initialize MemPalace
    palace = MemPalace("./agent-memory", wing="demo")
    adapter = OpenAIAdapter(palace)

    # 2. Store some initial knowledge
    palace.remember("Project uses FastAPI with SQLAlchemy ORM", room="architecture")
    palace.remember("Database is PostgreSQL 15 running on port 5432", room="config")
    palace.add_fact("project", "uses", "FastAPI")
    palace.add_fact("project", "uses", "PostgreSQL")

    # 3. Show how to use with OpenAI API
    print("=== OpenAI Function Calling Demo ===\n")

    tools = adapter.get_tools()
    print(f"Registered {len(tools)} tools:")
    for t in tools:
        print(f"  - {t['function']['name']}: {t['function']['description']}")

    # Simulate handling a tool call from GPT
    print("\n--- Simulating tool call: mempalace_recall ---")
    result = adapter.handle_tool_call("mempalace_recall", {"query": "database config"})
    data = json.loads(result)
    for r in data["results"]:
        print(f"  Found: {r['content'][:80]}...")

    # Simulate storing a decision
    print("\n--- Simulating tool call: mempalace_remember ---")
    result = adapter.handle_tool_call("mempalace_remember", {
        "content": "Switched from REST to GraphQL for the API gateway",
        "room": "decisions",
    })
    print(f"  {result}")

    # 4. Verify recall works
    print("\n--- Verifying recall ---")
    results = palace.recall("API gateway decision")
    for r in results:
        print(f"  [{r['distance']:.3f}] {r['content'][:80]}...")

    print("\nDone! In a real app, you'd pass `tools` to client.chat.completions.create().")


if __name__ == "__main__":
    main()
