"""
FastAPI route definitions for AutoFlow.

Endpoints:
  POST /run          — run a task, wait for full result
  GET  /run/stream   — run a task, stream steps as SSE
  GET  /tasks        — list task history
  GET  /tasks/{id}   — get a single task by ID
  GET  /tools        — list available tools
  GET  /health       — health check
"""

import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.schemas import TaskRequest, TaskResponse, TaskStatus, StepLog
from app.models.db import TaskRecord
from app.agent.core import run_task, stream_task, TOOL_REGISTRY
from app.database import get_db, AsyncSessionLocal

router = APIRouter()


# ─── Helpers ────────────────────────────────────────────────────────────────

def _validate_task_request(request: TaskRequest):
    if not request.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty.")
    if request.tools:
        unknown = [t for t in request.tools if t not in TOOL_REGISTRY]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown tools: {unknown}. Available: {list(TOOL_REGISTRY.keys())}"
            )


def _record_to_response(record: TaskRecord) -> dict:
    return {
        "id": record.id,
        "task": record.task,
        "tools": record.tools.split(",") if record.tools else None,
        "status": record.status,
        "result": record.result,
        "steps": record.get_steps(),
        "error": record.error,
        "created_at": record.created_at.isoformat(),
    }


# ─── Run (blocking) ─────────────────────────────────────────────────────────

@router.post("/run", response_model=TaskResponse)
async def run_agent_task(request: TaskRequest, db: AsyncSession = Depends(get_db)):
    """
    Run an agent task and wait for the full result.

    Saves the task to history automatically.
    """
    _validate_task_request(request)

    # Save task record immediately so it gets an ID
    record = TaskRecord(
        task=request.task,
        tools=",".join(request.tools) if request.tools else None,
        status=TaskStatus.running,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Run the agent (this blocks until done)
    response = run_task(task=request.task, enabled_tools=request.tools)

    # Persist results
    record.status = response.status
    record.result = response.result
    record.error = response.error
    record.set_steps(response.steps)
    await db.commit()

    return response


# ─── Run (streaming SSE) ────────────────────────────────────────────────────

@router.post("/run/stream")
async def stream_agent_task(request: TaskRequest, db: AsyncSession = Depends(get_db)):
    """
    Run an agent task and stream each step as Server-Sent Events.

    The client receives one JSON event per step as the agent reasons and acts.
    Use this endpoint to power a real-time UI that shows the agent "thinking."

    SSE format:  data: {"step": 1, "type": "tool_call", ...}\\n\\n

    Connect from the browser with:
      const es = new EventSource('/api/v1/run/stream')
    Or use fetch() with a ReadableStream for POST requests.
    """
    _validate_task_request(request)

    # Save record before streaming starts
    record = TaskRecord(
        task=request.task,
        tools=",".join(request.tools) if request.tools else None,
        status=TaskStatus.running,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    task_id = record.id

    async def event_stream():
        """Inner generator that yields SSE events and saves the final result."""
        steps = []
        final_result = None

        # First event: confirm task started with its ID
        yield f"data: {json.dumps({'type': 'start', 'task_id': task_id})}\n\n"

        async for chunk in stream_task(request.task, request.tools):
            yield chunk

            # Parse each chunk to collect steps for DB save
            if chunk.startswith("data: "):
                try:
                    payload = json.loads(chunk[6:])
                    if payload.get("type") == "final":
                        final_result = payload.get("content")
                    if payload.get("type") not in ("done", "error", "start"):
                        steps.append(StepLog(
                            step=payload.get("step", 0),
                            type=payload.get("type", ""),
                            content=payload.get("content", ""),
                            tool_name=payload.get("tool_name"),
                            tool_input=payload.get("tool_input"),
                        ))
                except (json.JSONDecodeError, Exception):
                    pass

        # Persist final results after stream completes
        async with AsyncSessionLocal() as save_session:
            result = await save_session.execute(
                select(TaskRecord).where(TaskRecord.id == task_id)
            )
            saved = result.scalar_one_or_none()
            if saved:
                saved.status = TaskStatus.completed
                saved.result = final_result
                saved.set_steps(steps)
                await save_session.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable Nginx buffering if behind proxy
        },
    )


# ─── Task History ────────────────────────────────────────────────────────────

@router.get("/tasks")
async def list_tasks(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Return the most recent task runs (newest first)."""
    result = await db.execute(
        select(TaskRecord).order_by(desc(TaskRecord.created_at)).limit(limit)
    )
    records = result.scalars().all()
    return {"tasks": [_record_to_response(r) for r in records]}


@router.get("/tasks/{task_id}")
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Return a single task by ID, including all steps."""
    result = await db.execute(
        select(TaskRecord).where(TaskRecord.id == task_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
    return _record_to_response(record)


# ─── Tools ───────────────────────────────────────────────────────────────────

@router.get("/tools")
async def list_tools():
    """List all available tools the agent can use."""
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


# ─── Health ───────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "AutoFlow API"}
