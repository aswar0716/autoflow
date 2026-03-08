"""
Web search tool powered by Tavily.

Tavily is an AI-native search API — unlike Google/Bing, it returns clean,
LLM-ready summaries instead of raw HTML links. This is why it's the go-to
choice for LangChain agents in production.
"""

from langchain_community.tools.tavily_search import TavilySearchResults


def get_search_tool() -> TavilySearchResults:
    """
    Returns a LangChain-compatible Tavily search tool.

    max_results=5 gives the agent enough context without burning tokens.
    The tool automatically reads TAVILY_API_KEY from the environment.
    """
    return TavilySearchResults(
        max_results=5,
        description=(
            "Search the web for current information. Use this when you need "
            "up-to-date facts, company info, news, or anything not in your "
            "training data. Input should be a clear search query string."
        ),
    )
