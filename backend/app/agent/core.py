"""
AutoFlow Agent Core

This is where the LangChain agent is assembled. The key components are:

1. LLM (GPT-4o): The brain that reasons about what to do next.
2. Tools: The hands — search, email, summarize, etc.
3. Agent: The loop that keeps calling LLM → pick tool → run tool → repeat
   until the task is complete.

We use LangGraph's create_react_agent which implements the ReAct pattern:
  Reason → Act → Observe → Reason → Act → ...
This is the most widely used agent pattern in production systems.
"""

import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.agent.tools.search import get_search_tool
from app.agent.tools.summarize import summarize_text
from app.agent.tools.email import send_email
from app.models.schemas import StepLog, TaskResponse, TaskStatus


# Registry mapping tool names → tool objects
# This lets the API selectively enable tools per task
TOOL_REGISTRY = {
    "search": get_search_tool,   # callable so we init fresh each time
    "summarize": lambda: summarize_text,
    "email": lambda: send_email,
}


def build_agent(enabled_tools: Optional[list[str]] = None):
    """
    Construct a LangGraph ReAct agent with the specified tools.

    Args:
        enabled_tools: list of tool names from TOOL_REGISTRY.
                       If None, all tools are enabled.

    Returns:
        A compiled LangGraph agent ready to invoke.
    """
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,          # 0 = deterministic, best for task execution
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    if enabled_tools is None:
        tools = [factory() for factory in TOOL_REGISTRY.values()]
    else:
        tools = [
            TOOL_REGISTRY[name]()
            for name in enabled_tools
            if name in TOOL_REGISTRY
        ]

    agent = create_react_agent(llm, tools)
    return agent


def run_task(task: str, enabled_tools: Optional[list[str]] = None) -> TaskResponse:
    """
    Run a task through the AutoFlow agent and return structured results.

    The agent will:
    1. Receive the task as a HumanMessage
    2. Reason about which tools to use
    3. Execute tools in sequence
    4. Return a final answer

    We capture every intermediate step to build a step-by-step audit log.
    """
    agent = build_agent(enabled_tools)

    system_prompt = (
        "You are AutoFlow, a business workflow automation agent. "
        "You help users complete multi-step business tasks autonomously. "
        "Break tasks into logical steps, use the right tools, and always "
        "return a clear, actionable final answer."
    )

    try:
        result = agent.invoke({
            "messages": [HumanMessage(content=task)],
        }, config={"configurable": {"system_message": system_prompt}})

        steps = _parse_steps(result["messages"])
        final_answer = _extract_final_answer(result["messages"])

        return TaskResponse(
            status=TaskStatus.completed,
            result=final_answer,
            steps=steps,
        )

    except Exception as e:
        return TaskResponse(
            status=TaskStatus.failed,
            error=str(e),
        )


def _parse_steps(messages: list) -> list[StepLog]:
    """
    Convert LangGraph message history into structured StepLog entries.

    LangGraph returns a flat list of messages:
    - HumanMessage: the original task
    - AIMessage: agent reasoning + tool call decisions
    - ToolMessage: results from tool executions
    - Final AIMessage: the answer
    """
    steps = []
    step_num = 0

    for msg in messages:
        if isinstance(msg, HumanMessage):
            continue  # skip the input

        if isinstance(msg, AIMessage):
            # Check if this AIMessage contains tool calls (intermediate step)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    step_num += 1
                    steps.append(StepLog(
                        step=step_num,
                        type="tool_call",
                        content=f"Calling tool: {tc['name']}",
                        tool_name=tc["name"],
                        tool_input=tc["args"],
                    ))
            else:
                # Final answer message
                step_num += 1
                steps.append(StepLog(
                    step=step_num,
                    type="final",
                    content=msg.content,
                ))

        elif isinstance(msg, ToolMessage):
            step_num += 1
            steps.append(StepLog(
                step=step_num,
                type="tool_result",
                tool_name=msg.name,
                content=str(msg.content)[:500],  # truncate long results
            ))

    return steps


def _extract_final_answer(messages: list) -> str:
    """Extract the last AI message content as the final answer."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            return msg.content
    return "Task completed."
