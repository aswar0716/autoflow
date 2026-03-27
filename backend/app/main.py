"""
AutoFlow FastAPI Application Entry Point

FastAPI is a modern Python web framework built on top of Starlette and Pydantic.
It auto-generates OpenAPI docs (visit /docs when running) and handles async I/O
efficiently — important when agent tasks involve multiple slow API calls.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes import router
from app.api.workflow_routes import router as workflow_router
from app.api.topic_routes import router as topic_router
from app.api.digest_routes import router as digest_router
from app.database import init_db
from app.services.scheduler import scheduler, load_scheduled_topics

# Load environment variables from .env file before anything else
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB tables, load scheduled topics, start scheduler."""
    await init_db()
    await load_scheduled_topics()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="AutoFlow",
    description="AI-powered digest automation — subscribe to topics, get web-grounded email digests on a schedule.",
    version="0.4.0",
    lifespan=lifespan,
)

# CORS: Allow the Next.js frontend (running on port 3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routes under /api/v1
app.include_router(router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(topic_router, prefix="/api/v1/topics", tags=["topics"])
app.include_router(digest_router, prefix="/api/v1/digests", tags=["digests"])


@app.get("/")
async def root():
    return {
        "message": "AutoFlow API is running",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
