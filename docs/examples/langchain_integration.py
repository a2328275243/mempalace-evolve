"""LangChain integration example.

Requires: pip install mempalace-evolve[langchain] langchain-openai
"""

from mempalace_evolve import MemPalace
from mempalace_evolve.adapters.langchain_adapter import LangChainAdapter


def main():
    palace = MemPalace("langchain_demo", wing="demo")
    tools = LangChainAdapter(palace).get_tools()

    print("Tools:", [tool.name for tool in tools])
    print("Bind `tools` with `ChatOpenAI(...).bind_tools(tools)` in your agent.")


if __name__ == "__main__":
    main()
