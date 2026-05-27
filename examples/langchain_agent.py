"""Example: Using MemPalace with LangChain agents.

Run:
    pip install mempalace-evolve[langchain] langchain-openai
    export OPENAI_API_KEY=sk-...
    python langchain_agent.py
"""

import json

from mempalace_evolve import MemPalace
from mempalace_evolve.adapters.langchain_adapter import LangChainAdapter


def main():
    # 1. Initialize
    palace = MemPalace("./agent-memory", wing="langchain_demo")
    adapter = LangChainAdapter(palace)

    # 2. Get LangChain StructuredTool instances
    tools = adapter.get_tools()
    print(f"=== LangChain Adapter Demo ===\n")
    print(f"Registered {len(tools)} tools:")
    for t in tools:
        print(f"  - {t.name}: {t.description}")

    # 3. Use tools directly (same as LangChain agent would)
    print("\n--- Calling mempalace_remember ---")
    result = tools[0].invoke({"content": "Using LangChain with ReAct agent pattern", "room": "decisions"})
    print(f"  {result}")

    print("\n--- Calling mempalace_recall ---")
    result = tools[1].invoke({"query": "agent pattern", "limit": 3})
    print(f"  {result}")

    print("\n--- Calling mempalace_add_fact ---")
    result = tools[2].invoke({"subject": "agent", "uses": "ReAct", "object": "ReAct"})
    print(f"  {result}")

    # 4. How to use with a real LangChain agent:
    print("\n=== Integration Code (copy-paste) ===")
    print("""
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent

llm = ChatOpenAI(model="gpt-4", temperature=0)
agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    verbose=True,
)
response = agent.run("What database does the project use?")
""")

    print("Done!")


if __name__ == "__main__":
    main()
