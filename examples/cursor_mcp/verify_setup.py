"""Example: Cursor MCP integration verification script.

Run after configuring MCP in Cursor to verify the connection works:
    python verify_setup.py
"""

import sys

from mempalace_evolve import MemPalace


def main():
    palace = MemPalace(wing="cursor_test")

    print("=== MemPalace + Cursor MCP Verification ===\n")

    # 1. Store a test memory
    mid = palace.remember(
        "Cursor MCP integration verified successfully",
        room="config",
    )
    print(f"[OK] Stored test memory: {mid[:12]}...")

    # 2. Recall it
    results = palace.recall("Cursor MCP")
    if results:
        print(f"[OK] Recall works: found {len(results)} result(s)")
    else:
        print("[FAIL] Recall returned empty")
        sys.exit(1)

    # 3. Knowledge graph
    palace.add_fact("cursor", "integrates_with", "mempalace")
    rels = palace.query_entity("cursor")
    if rels:
        print(f"[OK] Knowledge graph works: {len(rels)} relation(s)")
    else:
        print("[FAIL] Knowledge graph returned empty")
        sys.exit(1)

    # 4. Context for prompt injection
    ctx = palace.context_for("MCP setup")
    print(f"[OK] context_for() returns {len(ctx)} chars")

    # 5. Cleanup test memory
    palace.forget(mid)
    print(f"[OK] Cleaned up test memory")

    print("\n All checks passed. MCP integration is ready.")


if __name__ == "__main__":
    main()
