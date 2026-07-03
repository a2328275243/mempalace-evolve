"""
REST API Client Example

Demonstrates how to interact with the mempalace REST API.
Run the server first: mempalace serve
"""
import httpx
import json

BASE_URL = "http://localhost:8964"
API_KEY = "demo-key"  # Set via --api-key when serving

print("=== REST API Example ===")

headers = {"Authorization": f"Bearer {API_KEY}"}

# 1. Health check
print("1. Checking health...")
with httpx.Client() as client:
    resp = client.get(f"{BASE_URL}/health")
    print(f"   Status: {resp.status_code}, Response: {resp.json()}")

# 2. Store a memory
print("\n2. Storing memory...")
with httpx.Client() as client:
    resp = client.post(
        f"{BASE_URL}/remember",
        json={"content": "Use async/await for I/O-bound operations", "room": "best-practices"},
        headers=headers,
    )
    print(f"   Status: {resp.status_code}, ID: {resp.json()['id']}")

# 3. Recall memories
print("\n3. Recalling memories...")
with httpx.Client() as client:
    resp = client.post(
        f"{BASE_URL}/recall",
        json={"query": "async patterns", "limit": 3},
        headers=headers,
    )
    results = resp.json()
    print(f"   Found {len(results)} results:")
    for r in results:
        print(f"     - {r.get('content', '')[:60]}")

# 4. Get stats
print("\n4. Getting stats...")
with httpx.Client() as client:
    resp = client.get(f"{BASE_URL}/stats", headers=headers)
    print(f"   Stats: {resp.json()}")

print("\nRun 'mempalace serve' to try this yourself!")
