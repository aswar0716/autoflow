from pydantic import BaseModel
from typing import Any, Optional
from enum import Enum


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class TaskRequest(BaseModel):
    """Payload sent by the client to run an agent task."""
    task: str
    tools: Optional[list[str]] = None  # e.g. ["search", "email"] — None means all tools


class StepLog(BaseModel):
    """A single reasoning/action step taken by the agent."""
    step: int
    type: str          # "thought" | "tool_call" | "tool_result" | "final"
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[Any] = None


class TaskResponse(BaseModel):
    """Response returned after running a task."""
    status: TaskStatus
    result: Optional[str] = None
    steps: list[StepLog] = []
    error: Optional[str] = None
