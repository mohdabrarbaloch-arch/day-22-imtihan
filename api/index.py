"""Vercel serverless entry — routes all /api/* traffic to the FastAPI app."""

from app.main import app

handler = app
