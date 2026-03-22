"""
APScheduler integration.

Reads active TopicRecords from the database and schedules digest jobs
based on each topic's frequency. Integrated into FastAPI's lifespan so
the scheduler starts when the server starts and shuts down cleanly.

Frequency options:
  "hourly"  — every hour (useful for testing)
  "daily"   — every day at 08:00 UTC
  "weekly"  — every Monday at 08:00 UTC
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.db import TopicRecord, DigestRecord

logger = logging.getLogger(__name__)

# Global scheduler instance — started/stopped in FastAPI lifespan
scheduler = AsyncIOScheduler(timezone="UTC")

FREQUENCY_TRIGGERS = {
    "hourly": CronTrigger(minute=0),
    "daily":  CronTrigger(hour=8, minute=0),
    "weekly": CronTrigger(day_of_week="mon", hour=8, minute=0),
}


async def _run_topic_job(topic_id: int):
    """Execute a single topic: generate digest, send email, save record."""
    # Import here to avoid circular imports at module load time
    from app.services.digest import run_digest

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TopicRecord).where(TopicRecord.id == topic_id)
        )
        topic = result.scalar_one_or_none()
        if not topic or not topic.is_active:
            return

        logger.info("Running digest for topic %d: %s", topic_id, topic.name)

        # run_digest is synchronous (LangGraph agent) — run in executor to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        digest_result = await loop.run_in_executor(
            None, run_digest, topic.name, topic.query, topic.get_recipients()
        )

        # Persist digest record
        record = DigestRecord(
            topic_id=topic_id,
            subject=digest_result["subject"],
            html_content=digest_result["html"],
            summary=digest_result.get("summary", ""),
            status=digest_result["status"],
            error=digest_result.get("error"),
        )
        record.set_sent_to(digest_result.get("sent_to", []))
        db.add(record)

        # Update topic timestamps
        topic.last_run = datetime.now(timezone.utc)
        await db.commit()

        logger.info(
            "Digest for topic %d completed with status: %s",
            topic_id, digest_result["status"]
        )


async def load_scheduled_topics():
    """
    Read all active topics from DB and register them with the scheduler.
    Called on startup and whenever topics are created/updated.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TopicRecord).where(TopicRecord.is_active == True)  # noqa: E712
        )
        topics = result.scalars().all()

    for topic in topics:
        _schedule_topic(topic)

    logger.info("Scheduled %d active topic(s)", len(topics))


def _schedule_topic(topic: TopicRecord):
    """Register (or replace) a topic's scheduled job."""
    job_id = f"topic_{topic.id}"
    trigger = FREQUENCY_TRIGGERS.get(topic.frequency, FREQUENCY_TRIGGERS["daily"])

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    job = scheduler.add_job(
        _run_topic_job,
        trigger=trigger,
        args=[topic.id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Persist next_run so the UI can display it without querying APScheduler directly
    if job.next_run_time:
        topic.next_run = job.next_run_time.replace(tzinfo=None)

    logger.info(
        "Scheduled topic %d (%s) — next run: %s",
        topic.id, topic.name, job.next_run_time
    )


def schedule_topic(topic: TopicRecord) -> datetime | None:
    """
    Public API — call this after creating/updating a topic.
    Returns the next scheduled run time so the caller can persist it.
    """
    _schedule_topic(topic)
    job = scheduler.get_job(f"topic_{topic.id}")
    if job and job.next_run_time:
        return job.next_run_time.replace(tzinfo=None)
    return None


def unschedule_topic(topic_id: int):
    """Remove a topic's scheduled job (called on delete or deactivate)."""
    job_id = f"topic_{topic_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info("Unscheduled topic %d", topic_id)
