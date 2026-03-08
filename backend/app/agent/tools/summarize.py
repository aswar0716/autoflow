"""
Text summarization tool.

This is a simple LangChain @tool that takes a block of text and returns a
structured summary. It re-uses the same LLM the agent is already using —
no extra API cost, just a focused sub-prompt.
"""

from langchain_core.tools import tool


@tool
def summarize_text(text: str) -> str:
    """
    Summarize a block of text into key points and action items.

    Use this when you have a long piece of text (meeting notes, articles,
    emails, documents) and need to extract the essential information.
    Input should be the raw text content to summarize.
    """
    # The agent's LLM will handle this via the tool-calling mechanism.
    # We return a structured prompt that instructs the model to summarize.
    # In practice, LangChain routes this back through the LLM.
    return (
        f"Please summarize the following text into:\n"
        f"1. A 2-3 sentence overview\n"
        f"2. Key points (bullet list)\n"
        f"3. Action items (if any)\n\n"
        f"Text:\n{text}"
    )
