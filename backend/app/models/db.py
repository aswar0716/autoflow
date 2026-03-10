"""
Database models (SQLAlchemy ORM).

Each class here maps to a table in the SQLite database.
SQLAlchemy handles creating the table, inserting rows, and querying —
we just work with Python objects.
"""

import json
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskRecord(Base):
    """
    Persists every agent task run for history and debugging.

    Table: tasks
    """
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    tools: Mapped[str] = mapped_column(String(255), nullable=True)   # comma-separated
    status: Mapped[str] = mapped_column(String(20), default="pending")
    result: Mapped[str] = mapped_column(Text, nullable=True)
    steps_json: Mapped[str] = mapped_column(Text, nullable=True)      # JSON array
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def set_steps(self, steps: list):
        self.steps_json = json.dumps([s.model_dump() for s in steps])

    def get_steps(self) -> list:
        if not self.steps_json:
            return []
        return json.loads(self.steps_json)


class WorkflowRecord(Base):
    """
    A saved, reusable workflow — a named configuration of tools and a prompt template.

    Users build these visually in the drag-and-drop canvas, then run them by ID.

    Table: workflows
    """
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    tools_json: Mapped[str] = mapped_column(Text, nullable=False)   # JSON array of tool names
    nodes_json: Mapped[str] = mapped_column(Text, nullable=True)    # React Flow node positions
    edges_json: Mapped[str] = mapped_column(Text, nullable=True)    # React Flow edge connections
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def set_tools(self, tools: list[str]):
        self.tools_json = json.dumps(tools)

    def get_tools(self) -> list[str]:
        return json.loads(self.tools_json) if self.tools_json else []

    def set_nodes(self, nodes: list):
        self.nodes_json = json.dumps(nodes)

    def get_nodes(self) -> list:
        return json.loads(self.nodes_json) if self.nodes_json else []

    def set_edges(self, edges: list):
        self.edges_json = json.dumps(edges)

    def get_edges(self) -> list:
        return json.loads(self.edges_json) if self.edges_json else []
