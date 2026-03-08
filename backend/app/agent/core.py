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
import json
from typing import Optional, AsyncGenerator
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.agent.tools.search import get_search_tool
from app.agent.tools.summarize import summarize_text
from app.agent.tools.email import send_email
from app.models.schemas import StepLog, TaskResponse, TaskStatus


# Registry mapping tool names → tool objects
TOOL_REGISTRY = {
    "search": get_search_tool,
    "summarize": lambda: summarize_text,
    "email": lambda: send_email,
}

SYSTEM_PROMPT = (
    "You are AutoFlow, a business workflow automation agent. "
    "You help users complete multi-step business tasks autonomously. "
    "Break tasks into logical steps, use the right tools, and always "
    "return a clear, actionable final answer."
)


def build_agent(enabled_tools: Optional[list[str]] = None):
    """Construct a LangGraph ReAct agent with the specified tools."""
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
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

    return create_react_agent(llm, tools)


def run_task(task: str, enabled_tools: Optional[list[str]] = None) -> TaskResponse:
    """Run a task synchronously and return structured results."""
    agent = build_agent(enabled_tools)

    try:
        result = agent.invoke({
            "messages": [HumanMessage(content=task)],
        })

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


async def stream_task(
    task: str,
    enabled_tools: Optional[list[str]] = None,
) -> AsyncGenerator[str, None]:
    """
    Run a task and stream each step as a Server-Sent Event (SSE).

    SSE format: each message is a line starting with "data: " followed by JSON.
    The browser's EventSource API reads these automatically.

    We use LangGraph's astream_events() which fires events for every internal
    action: model thinking, tool calls, tool results, final answer.
    """
    agent = build_agent(enabled_tools)
    step_num = 0

    try:
        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=task)]},
            version="v2",
        ):
            kind = event["event"]

            # Agent starts calling a tool
            if kind == "on_tool_start":
                step_num += 1
                payload = {
                    "step": step_num,
                    "type": "tool_call",
                    "tool_name": event["name"],
                    "tool_input": event.get("data", {}).get("input", {}),
                    "content": f"Calling tool: {event['name']}",
                }
                yield f"data: {json.dumps(payload)}\n\n"

            # Tool finishes, result is available
            elif kind == "on_tool_end":
                step_num += 1
                output = event.get("data", {}).get("output", "")
                payload = {
                    "step": step_num,
                    "type": "tool_result",
                    "tool_name": event["name"],
                    "content": str(output)[:500],
                }
                yield f"data: {json.dumps(payload)}\n\n"

            # LLM produces its final answer (no tool call)
            elif kind == "on_chat_model_end":
                msg = event.get("data", {}).get("output")
                if msg and hasattr(msg, "content") and not getattr(msg, "tool_calls", None):
                    step_num += 1
                    payload = {
                        "step": step_num,
                        "type": "final",
                        "content": msg.content,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

        # Signal stream is complete
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


def _parse_steps(messages: list) -> list[StepLog]:
    """Convert LangGraph message history into structured StepLog entries."""
    steps = []
    step_num = 0

    for msg in messages:
        if isinstance(msg, HumanMessage):
            continue

        if isinstance(msg, AIMessage):
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
                content=str(msg.content)[:500],
            ))

    return steps


def _extract_final_answer(messages: list) -> str:
    """Extract the last AI message content as the final answer."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            return msg.content
    return "Task completed."
