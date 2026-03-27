"""
Global digest endpoints.

Provides a single-digest lookup by ID so the frontend can render a
shareable /digest/[id] page without knowing which topic it belongs to.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.models.db import DigestRecord, TopicRecord
from app.database import get_db

router = APIRouter()


@router.get("/{digest_id}")
async def get_digest(digest_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DigestRecord).where(DigestRecord.id == digest_id)
    )
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(404, f"Digest {digest_id} not found.")

    # Fetch topic name for display
    topic_result = await db.execute(
        select(TopicRecord).where(TopicRecord.id == d.topic_id)
    )
    topic = topic_result.scalar_one_or_none()

    return {
        "id": d.id,
        "topic_id": d.topic_id,
        "topic_name": topic.name if topic else "Unknown Topic",
        "subject": d.subject,
        "summary": d.summary,
        "html_content": d.html_content,
        "status": d.status,
        "error": d.error,
        "sent_to": d.get_sent_to(),
        "created_at": d.created_at.isoformat(),
    }
