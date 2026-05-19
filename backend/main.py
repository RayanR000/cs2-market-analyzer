"""
CS2 Market Intelligence Platform - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import items, opportunities, events
import uvicorn

app = FastAPI(
    title="CS2 Market Intelligence API",
    description="Backend API for CS2 market tracking and analysis",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(items.router)
app.include_router(opportunities.router)
app.include_router(events.router)

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "cs2-market-api"}

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "CS2 Market Intelligence API",
        "version": "0.1.0",
        "docs": "/api/docs"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
