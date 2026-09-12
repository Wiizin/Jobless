"""FastAPI app entrypoint — router registration + scheduler lifecycle."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import applications, documents, offers, profile
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="jobless",
    description="AI-powered job/internship application assistant — human-in-the-loop by design.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(profile.router)
app.include_router(offers.router)
app.include_router(documents.router)
app.include_router(applications.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
