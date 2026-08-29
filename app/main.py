"""Imtihan — FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.core.config import settings
from app.core.database import Base, engine
from app.routers import analytics, auth, exams, submissions

# --- rate limiter ---
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Imtihan API",
    description="Online exam & quiz platform for tuition centers — auto-grading, negative marking, exam codes, analytics.",
    version=settings.app_version,
)

app.state.limiter = limiter

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429, content={"detail": "Too many requests — slow down please."}
    )


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


app.include_router(auth.router)
app.include_router(exams.router)
app.include_router(submissions.router)
app.include_router(analytics.router)

# Serve the SPA at / (index.html) with static assets
_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
