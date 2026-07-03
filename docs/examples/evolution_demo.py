"""
Evolution Pipeline Example

Shows how the self-evolving memory system works:
- Transcript analysis
- Candidate extraction
- Scoring and promotion
- Automatic cleanup
"""
from mempalace_evolve import MemPalace

palace = MemPalace("evolution_demo")

# Simulate a coding session transcript
transcript = [
    "User: How do I add authentication?",
    "Agent: You should use JWT tokens with refresh token rotation.",
    "User: Should I store tokens in localStorage?",
    "Agent: No! localStorage is vulnerable to XSS. Use httpOnly cookies instead.",
    "User: What about the refresh token?",
    "Agent: Store refresh tokens in an httpOnly, Secure, SameSite=Strict cookie.",
    "User: Got it. Implement it now.",
    "Agent: I'll create an auth middleware with JWT verification.",
]

print("=== Feeding transcript to evolution pipeline ===")
for msg in transcript:
    palace.remember(msg, room="session")

# Run evolution: extract patterns, score, promote/drop
report = palace.evolve()
print(f"Evolution complete:")
print(f"  Promoted: {report['promoted']}")
print(f"  Dropped: {report['dropped']}")

# See what survived
top = palace.top_memories(5)
print(f"\nTop {len(top)} important memories after evolution:")
for mem in top:
    print(f"  [{mem['score']:.2f}] {mem['content'][:80]}")

print("\nThe system learned that httpOnly cookies are the secure pattern!")
