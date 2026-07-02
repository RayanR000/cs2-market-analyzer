"""
FastAPI server for CS2 Market Intelligence Platform
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_db
from api.routes import items, opportunities, events, auth, portfolio

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router)
app.include_router(opportunities.router)
app.include_router(events.router)
app.include_router(auth.router)
app.include_router(portfolio.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": settings.api_version,
        "environment": settings.environment,
    }
