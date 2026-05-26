"""Example: Using MemPalace with OpenAI function calling."""

from mempalace_evolve import MemPalace
from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter

# Initialize
palace = MemPalace("./my-project-memory")
adapter = OpenAIAdapter(palace)

# Get tool definitions for OpenAI API
tools = adapter.get_tools()
print("Tools for OpenAI:", [t["function"]["name"] for t in tools])

# Simulate storing a memory
result = adapter.handle_tool_call("mempalace_remember", {
    "content": "The project uses PostgreSQL with pgvector for embeddings",
    "room": "decisions",
})
print("Store result:", result)

# Simulate recalling
result = adapter.handle_tool_call("mempalace_recall", {
    "query": "what database do we use?",
    "limit": 3,
})
print("Recall result:", result)

# Direct SDK usage
palace.remember("FastAPI is the web framework", room="architecture")
palace.add_fact("project", "uses", "FastAPI")
palace.add_fact("project", "uses", "PostgreSQL")

results = palace.recall("web framework")
print("Direct recall:", results)
