"""Example: Using MemPalace REST API from any language.

Start the server:
    pip install mempalace-evolve[api]
    mempalace-server --port 8765

Then call with curl, httpie, requests, or any HTTP client.
"""

# === Python (requests) ===
import json


def demo_with_requests():
    """Demo using the requests library."""
    try:
        import requests
    except ImportError:
        print("pip install requests")
        return

    BASE = "http://localhost:8765"

    # Health check
    resp = requests.get(f"{BASE}/health")
    print(f"Health: {resp.json()}")

    # Store a memory
    resp = requests.post(f"{BASE}/remember", json={
        "content": "Redis is used for session caching",
        "room": "config",
    })
    print(f"Stored: {resp.json()}")

    # Search memories
    resp = requests.post(f"{BASE}/recall", json={"query": "caching"})
    print(f"Recall: {resp.json()}")

    # Knowledge graph
    resp = requests.post(f"{BASE}/kg/add", json={
        "subject": "app",
        "predicate": "caches_with",
        "object": "Redis",
    })
    print(f"KG add: {resp.json()}")

    resp = requests.post(f"{BASE}/kg/query/app")
    print(f"KG query: {resp.json()}")


def print_curl_examples():
    """Print curl equivalents for reference."""
    print("=== curl examples ===\n")
    print("# Health check")
    print("curl http://localhost:8765/health")
    print()
    print("# Store a memory")
    print('curl -X POST http://localhost:8765/remember -H "Content-Type: application/json" -d \'{"content": "Redis is used for caching", "room": "config"}\'')
    print()
    print("# Search memories")
    print('curl -X POST http://localhost:8765/recall -H "Content-Type: application/json" -d \'{"query": "caching"}\'')
    print()
    print("# Add knowledge graph fact")
    print('curl -X POST http://localhost:8765/kg/add -H "Content-Type: application/json" -d \'{"subject": "app", "predicate": "uses", "object": "Redis"}\'')
    print()
    print("# Query knowledge graph")
    print("curl -X POST http://localhost:8765/kg/query/app")
    print()
    print("# Run evolution")
    print('curl -X POST http://localhost:8765/evolve -H "Content-Type: application/json" -d \'{"transcript": "We decided to use gunicorn with 4 workers"}\'')


if __name__ == "__main__":
    print_curl_examples()
    print("\n")
    try:
        demo_with_requests()
    except Exception as e:
        print(f"(Could not connect to server: {e})")
        print("Start it with: mempalace-server --port 8765")
