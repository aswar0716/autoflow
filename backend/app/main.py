"""
AutoFlow FastAPI Application Entry Point

FastAPI is a modern Python web framework built on top of Starlette and Pydantic.
It auto-generates OpenAPI docs (visit /docs when running) and handles async I/O
efficiently — important when agent tasks involve multiple slow API calls.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes import router

# Load environment variables from .env file before anything else
load_dotenv()

app = FastAPI(
    title="AutoFlow",
    description="AI Agent for Business Workflow Automation",
    version="0.1.0",
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


@app.get("/")
async def root():
    return {
        "message": "AutoFlow API is running",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
