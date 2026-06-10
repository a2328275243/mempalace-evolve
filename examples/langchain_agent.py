"""Example: LangChain agent with persistent memory via MemPalace.

This demo shows the full lifecycle:
  1. Session start → inject relevant memories into system prompt
  2. Agent runs → uses memory tools during conversation
  3. Session end → auto-digest transcript into long-term memory

Run:
    pip install mempalace-evolve[langchain] langchain-openai
    export OPENAI_API_KEY=YOUR_OPENAI_API_KEY
    python langchain_agent.py
"""

import json

from mempalace_evolve import MemPalace
from mempalace_evolve.adapters.langchain_adapter import LangChainAdapter


def main():
    # ─── 1. Initialize MemPalace + Adapter ───────────────────────
    palace = MemPalace("./agent-memory", wing="langchain_demo")
    adapter = LangChainAdapter(palace)

    print("=== LangChain + MemPalace Demo ===\n")

    # ─── 2. Session Start: retrieve context ──────────────────────
    context = adapter.on_session_start({"project": "demo", "user": "dev"})
    print(f"Session context injected: {context or '(empty — first run)'}\n")

    # ─── 3. Get tools for the agent ─────────────────────────────
    tools = adapter.get_tools()
    print(f"Registered {len(tools)} LangChain tools:")
    for t in tools:
        print(f"  - {t.name}")

    # ─── 4. Simulate agent using tools ───────────────────────────
    print("\n--- Agent stores a decision ---")
    result = tools[0].invoke({
        "content": "Using LangChain with ReAct pattern for the coding assistant",
        "room": "decisions",
    })
    print(f"  Stored: {result}")

    print("\n--- Agent recalls relevant info ---")
    result = tools[1].invoke({"query": "what pattern are we using", "limit": 3})
    print(f"  Found: {result}")

    print("\n--- Agent adds a fact ---")
    result = tools[2].invoke({
        "subject": "coding_assistant",
        "predicate": "uses",
        "object": "ReAct pattern",
    })
    print(f"  KG: {result}")

    # ─── 5. Session End: auto-digest transcript ──────────────────
    fake_transcript = """
    user: What pattern should we use for the coding assistant?
    assistant: I recommend the ReAct pattern — it combines reasoning and acting,
    which is ideal for coding tasks that need tool use.
    user: Good, let's go with that. Also remember we decided on GPT-4 as the base model.
    assistant: Noted. I've stored that decision. The architecture is:
    LangChain ReAct agent + GPT-4 + MemPalace for persistent memory.
    """
    adapter.on_session_end(fake_transcript, {"project": "demo"})
    print("\n--- Session ended: transcript digested ---")

    # ─── 6. Verify memories persisted ────────────────────────────
    stats = palace.stats()
    print(f"\nPalace stats: {stats['total']} memories, "
          f"{stats['kg_entities']} KG entities")

    # ─── 7. Show how to wire into a real LangChain agent ─────────
    print("\n=== Copy-paste for real agent ===")
    print("""
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate

palace = MemPalace("./my-memory", wing="my_project")
adapter = LangChainAdapter(palace)
tools = adapter.get_tools()

# Inject memories into system prompt
memory_context = adapter.on_session_start({"project": "my_project"})
prompt = ChatPromptTemplate.from_messages([
    ("system", f"You are a helpful assistant.\\n\\n{memory_context}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

llm = ChatOpenAI(model="gpt-4", temperature=0)
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
response = executor.invoke({"input": "What do you remember about our project?"})
""")
    print("Done!")


if __name__ == "__main__":
    main()
