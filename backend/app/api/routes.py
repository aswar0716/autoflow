"""
FastAPI route definitions for AutoFlow.

These endpoints are what the frontend (and any external client) calls.
Keeping routes thin — they validate input, delegate to the agent, return results.
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import TaskRequest, TaskResponse
from app.agent.core import run_task, TOOL_REGISTRY

router = APIRouter()


@router.post("/run", response_model=TaskResponse)
async def run_agent_task(request: TaskRequest):
    """
    Run an agent task.

    Send a natural-language task and optionally specify which tools the agent
    can use. The agent will autonomously plan and execute the steps needed.

    Example request body:
      {
        "task": "Search for the latest news about OpenAI and summarize it",
        "tools": ["search", "summarize"]
      }
    """
    if not request.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty.")

    # Validate requested tools exist
    if request.tools:
        unknown = [t for t in request.tools if t not in TOOL_REGISTRY]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown tools: {unknown}. Available: {list(TOOL_REGISTRY.keys())}"
            )

    response = run_task(task=request.task, enabled_tools=request.tools)
    return response


@router.get("/tools")
async def list_tools():
    """
    List all available tools the agent can use.

    Useful for the frontend to dynamically render the tool selection UI.
    """
    return {
        "tools": [
            {
                "name": "search",
                "description": "Search the web for current information using Tavily",
                "icon": "search",
            },
            {
                "name": "summarize",
                "description": "Summarize long text into key points and action items",
                "icon": "document",
            },
            {
                "name": "email",
                "description": "Send an email via SendGrid",
                "icon": "mail",
            },
        ]
    }


@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "AutoFlow API"}
