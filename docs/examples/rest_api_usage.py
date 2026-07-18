"""REST API client example.

Start the server first:
    mempalace serve --api-key demo-key
"""

import httpx


BASE_URL = "http://127.0.0.1:8765"
API_KEY = "demo-key"


def main():
    headers = {"X-API-Key": API_KEY}
    with httpx.Client(base_url=BASE_URL, headers=headers) as client:
        health = client.get("/health")
        health.raise_for_status()
        print("Health:", health.json())

        stored = client.post(
            "/remember",
            json={"content": "Use async/await for I/O-bound operations", "room": "best-practices"},
        )
        stored.raise_for_status()
        print("Stored:", stored.json()["drawer_id"])

        recalled = client.post("/recall", json={"query": "async patterns", "limit": 3})
        recalled.raise_for_status()
        for result in recalled.json()["results"]:
            print("Recall:", result["content"])

        stats = client.get("/stats")
        stats.raise_for_status()
        print("Stats:", stats.json())


if __name__ == "__main__":
    main()
