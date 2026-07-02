"""
FastAPI server for CS2 Market Intelligence Platform
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import settings
from database import init_db
from api.routes import items, opportunities, events, auth, portfolio, market

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
app.include_router(market.router)


@app.middleware("http")
async def cache_control_middleware(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/items/") or path.startswith("/market/") or path.startswith("/events/"):
        response.headers["Cache-Control"] = "public, max-age=30, s-maxage=60"
    elif path == "/health":
        response.headers["Cache-Control"] = "public, max-age=5"
    return response


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
