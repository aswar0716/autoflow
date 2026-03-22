"""
Topic subscription CRUD + manual trigger endpoints.

Topics are the core entity of the digest engine. Each topic has a search
query, a delivery schedule, and a list of recipient emails. The scheduler
runs them automatically; the /run endpoint allows manual triggering.
"""

import asyncio
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, EmailStr

from app.models.db import TopicRecord, DigestRecord
from app.database import get_db
from app.services.scheduler import schedule_topic, unschedule_topic

router = APIRouter()

VALID_FREQUENCIES = {"hourly", "daily", "weekly"}


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class TopicCreate(BaseModel):
    name: str
    query: str
    frequency: str = "daily"
    recipients: list[str]


class TopicUpdate(BaseModel):
    name: str | None = None
    query: str | None = None
    frequency: str | None = None
    recipients: list[str] | None = None
    is_active: bool | None = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _to_dict(t: TopicRecord) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "query": t.query,
        "frequency": t.frequency,
        "recipients": t.get_recipients(),
        "is_active": t.is_active,
        "next_run": t.next_run.isoformat() if t.next_run else None,
        "last_run": t.last_run.isoformat() if t.last_run else None,
        "created_at": t.created_at.isoformat(),
    }


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("")
async def list_topics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TopicRecord).order_by(desc(TopicRecord.created_at))
    )
    return {"topics": [_to_dict(t) for t in result.scalars().all()]}


@router.post("")
async def create_topic(body: TopicCreate, db: AsyncSession = Depends(get_db)):
    if body.frequency not in VALID_FREQUENCIES:
        raise HTTPException(400, f"frequency must be one of: {VALID_FREQUENCIES}")
    if not body.recipients:
        raise HTTPException(400, "At least one recipient email is required.")

    t = TopicRecord(name=body.name, query=body.query, frequency=body.frequency)
    t.set_recipients(body.recipients)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    next_run = schedule_topic(t)
    if next_run:
        t.next_run = next_run
        await db.commit()
    return _to_dict(t)


@router.get("/{topic_id}")
async def get_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TopicRecord).where(TopicRecord.id == topic_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, f"Topic {topic_id} not found.")
    return _to_dict(t)


@router.patch("/{topic_id}")
async def update_topic(
    topic_id: int, body: TopicUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TopicRecord).where(TopicRecord.id == topic_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, f"Topic {topic_id} not found.")

    if body.name is not None:
        t.name = body.name
    if body.query is not None:
        t.query = body.query
    if body.frequency is not None:
        if body.frequency not in VALID_FREQUENCIES:
            raise HTTPException(400, f"frequency must be one of: {VALID_FREQUENCIES}")
        t.frequency = body.frequency
    if body.recipients is not None:
        t.set_recipients(body.recipients)
    if body.is_active is not None:
        t.is_active = body.is_active
        if not body.is_active:
            unschedule_topic(topic_id)

    await db.commit()
    await db.refresh(t)
    if t.is_active:
        next_run = schedule_topic(t)
        if next_run:
            t.next_run = next_run
            await db.commit()
    return _to_dict(t)


@router.delete("/{topic_id}")
async def delete_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TopicRecord).where(TopicRecord.id == topic_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, f"Topic {topic_id} not found.")
    unschedule_topic(topic_id)
    await db.delete(t)
    await db.commit()
    return {"deleted": topic_id}


# ─── Manual trigger ───────────────────────────────────────────────────────────

@router.post("/{topic_id}/run")
async def run_topic_now(topic_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Manually trigger a digest for a topic immediately.
    Runs in the background so the API responds instantly.
    """
    result = await db.execute(select(TopicRecord).where(TopicRecord.id == topic_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, f"Topic {topic_id} not found.")

    async def _bg_run():
        from app.services.scheduler import _run_topic_job
        await _run_topic_job(topic_id)

    background_tasks.add_task(_bg_run)
    return {"status": "running", "topic_id": topic_id, "message": "Digest generation started in background."}


# ─── Digest history per topic ─────────────────────────────────────────────────

@router.get("/{topic_id}/digests")
async def list_digests(topic_id: int, db: AsyncSession = Depends(get_db)):
    """Return all digests generated for a topic, newest first."""
    result = await db.execute(
        select(DigestRecord)
        .where(DigestRecord.topic_id == topic_id)
        .order_by(desc(DigestRecord.created_at))
    )
    digests = result.scalars().all()
    return {
        "digests": [
            {
                "id": d.id,
                "topic_id": d.topic_id,
                "subject": d.subject,
                "summary": d.summary,
                "status": d.status,
                "error": d.error,
                "sent_to": d.get_sent_to(),
                "created_at": d.created_at.isoformat(),
                "html_content": d.html_content,
            }
            for d in digests
        ]
    }
