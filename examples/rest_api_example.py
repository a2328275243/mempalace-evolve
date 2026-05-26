"""Example: Using MemPalace REST API with any agent via HTTP."""

import requests

BASE = "http://localhost:8765"

# Store a memory
resp = requests.post(f"{BASE}/remember", json={
    "content": "User prefers dark mode and minimal UI",
    "room": "preferences",
})
print("Remember:", resp.json())

# Recall memories
resp = requests.post(f"{BASE}/recall", json={
    "query": "UI preferences",
    "limit": 3,
})
print("Recall:", resp.json())

# Add to knowledge graph
resp = requests.post(f"{BASE}/kg/add", json={
    "subject": "user",
    "predicate": "prefers",
    "object": "dark_mode",
})
print("KG add:", resp.json())

# Query knowledge graph
resp = requests.post(f"{BASE}/kg/query/user")
print("KG query:", resp.json())

# Run evolution
resp = requests.post(f"{BASE}/evolve", json={
    "transcript": "User asked about auth. We decided to use JWT tokens..."
})
print("Evolve:", resp.json())

# Health check
resp = requests.get(f"{BASE}/health")
print("Health:", resp.json())
