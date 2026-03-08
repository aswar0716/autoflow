"""
Database setup using SQLAlchemy (async).

SQLite is used for development — zero config, single file, perfect for MVP.
SQLAlchemy is the ORM (Object Relational Mapper): it lets us interact with the
database using Python objects instead of raw SQL strings.

We use the async version (create_async_engine) so database calls don't block
FastAPI's event loop while the agent is running.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# aiosqlite is the async driver for SQLite
DATABASE_URL = "sqlite+aiosqlite:///./autoflow.db"

engine = create_async_engine(DATABASE_URL, echo=False)

# Session factory — each request gets its own session
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class all database models inherit from."""
    pass


async def init_db():
    """Create all tables on startup if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a database session per request."""
    async with AsyncSessionLocal() as session:
        yield session
