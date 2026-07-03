"""
LangChain Integration Example

Shows how to use MemPalace as a LangChain tool for
memory-augmented LLM chains.
"""
# Note: Requires langchain installed: pip install langchain langchain-openai
try:
    from langchain_openai import ChatOpenAI
    from mempalace_evolve.adapters.langchain_adapter import create_mempalace_tools

    print("=== LangChain Integration Example ===\n")

    # 1. Create LangChain tools from MemPalace
    tools = create_mempalace_tools(palace_path="langchain_demo")

    print(f"Created {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")

    # 2. Bind tools to an LLM
    llm = ChatOpenAI(model="gpt-4o-mini")
    llm_with_tools = llm.bind_tools(tools)

    print("\n3. The LLM can now use memory tools automatically:")
    print("   - remember(): store important information")
    print("   - recall(): retrieve relevant context")
    print("   - add_fact(): build knowledge graph")
    print("\nThis enables long-term memory for your LangChain agents!")

except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install langchain langchain-openai")
    print("Then run this example again.")
