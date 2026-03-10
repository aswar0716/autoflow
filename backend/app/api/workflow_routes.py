"""
Workflow CRUD + run endpoints.

A "workflow" is a saved, named configuration:
  - which tools are enabled
  - the React Flow node/edge layout (for the visual canvas)

Running a workflow sends a task through the agent with that tool set.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Any

from app.models.db import WorkflowRecord
from app.agent.core import stream_task, TOOL_REGISTRY
from app.database import get_db

router = APIRouter()


# ─── Pydantic schemas (workflow-specific) ────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    tools: list[str]
    nodes: list[Any] = []
    edges: list[Any] = []


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tools: list[str] | None = None
    nodes: list[Any] | None = None
    edges: list[Any] | None = None


class WorkflowRunRequest(BaseModel):
    task: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _to_dict(w: WorkflowRecord) -> dict:
    return {
        "id": w.id,
        "name": w.name,
        "description": w.description,
        "tools": w.get_tools(),
        "nodes": w.get_nodes(),
        "edges": w.get_edges(),
        "created_at": w.created_at.isoformat(),
        "updated_at": w.updated_at.isoformat(),
    }


# ─── CRUD ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_workflows(db: AsyncSession = Depends(get_db)):
    """List all saved workflows, newest first."""
    result = await db.execute(
        select(WorkflowRecord).order_by(desc(WorkflowRecord.updated_at))
    )
    return {"workflows": [_to_dict(w) for w in result.scalars().all()]}


@router.post("")
async def create_workflow(body: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    """Save a new workflow."""
    unknown = [t for t in body.tools if t not in TOOL_REGISTRY]
    if unknown:
        raise HTTPException(400, f"Unknown tools: {unknown}")

    w = WorkflowRecord(name=body.name, description=body.description)
    w.set_tools(body.tools)
    w.set_nodes(body.nodes)
    w.set_edges(body.edges)
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return _to_dict(w)


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single workflow by ID."""
    result = await db.execute(
        select(WorkflowRecord).where(WorkflowRecord.id == workflow_id)
    )
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(404, f"Workflow {workflow_id} not found.")
    return _to_dict(w)


@router.patch("/{workflow_id}")
async def update_workflow(
    workflow_id: int, body: WorkflowUpdate, db: AsyncSession = Depends(get_db)
):
    """Update an existing workflow (partial update)."""
    result = await db.execute(
        select(WorkflowRecord).where(WorkflowRecord.id == workflow_id)
    )
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(404, f"Workflow {workflow_id} not found.")

    if body.name is not None:
        w.name = body.name
    if body.description is not None:
        w.description = body.description
    if body.tools is not None:
        unknown = [t for t in body.tools if t not in TOOL_REGISTRY]
        if unknown:
            raise HTTPException(400, f"Unknown tools: {unknown}")
        w.set_tools(body.tools)
    if body.nodes is not None:
        w.set_nodes(body.nodes)
    if body.edges is not None:
        w.set_edges(body.edges)

    await db.commit()
    await db.refresh(w)
    return _to_dict(w)


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a workflow."""
    result = await db.execute(
        select(WorkflowRecord).where(WorkflowRecord.id == workflow_id)
    )
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(404, f"Workflow {workflow_id} not found.")
    await db.delete(w)
    await db.commit()
    return {"deleted": workflow_id}


# ─── Run ─────────────────────────────────────────────────────────────────────

@router.post("/{workflow_id}/run")
async def run_workflow(
    workflow_id: int, body: WorkflowRunRequest, db: AsyncSession = Depends(get_db)
):
    """
    Run a saved workflow with a task description.

    Loads the workflow's tool set and streams the agent's execution via SSE —
    exactly like /run/stream but the tools come from the saved workflow config.
    """
    result = await db.execute(
        select(WorkflowRecord).where(WorkflowRecord.id == workflow_id)
    )
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(404, f"Workflow {workflow_id} not found.")

    tools = w.get_tools()

    async def event_stream():
        async for chunk in stream_task(body.task, tools if tools else None):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
