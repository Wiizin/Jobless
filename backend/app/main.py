"""FastAPI app entrypoint — router registration + scheduler lifecycle."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# The Next.js dev frontend runs on a different origin (:3000) than the API
# (:8000), so the browser blocks every request without this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Browsers hide Content-Disposition from JS unless it is explicitly
    # exposed, and the frontend reads the rendered .docx filename from it.
    expose_headers=["Content-Disposition"],
)

app.include_router(profile.router)
app.include_router(offers.router)
app.include_router(documents.router)
app.include_router(applications.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
