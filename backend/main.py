"""
CS2 Market Intelligence Platform - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import items, opportunities, events
from database import init_db, SessionLocal
from seed_data import DatabaseSeeder
from collectors.real_data_collector import start_real_data_collection, stop_real_data_collection
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@app.on_event("startup")
def startup_event():
    """Initialize database and start data collection on startup"""
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
        
        # Seed database if empty
        db = SessionLocal()
        try:
            DatabaseSeeder.seed_all(db)
            logger.info("Database seeding complete")
        finally:
            db.close()
        
        # Start real-time data collection from Steam API
        logger.info("Starting real-time market data collection...")
        start_real_data_collection()
        logger.info("Real-time data collection started")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down...")
    stop_real_data_collection()
    logger.info("Real-time data collection stopped")

# Include routers
app.include_router(items.router)
app.include_router(opportunities.router)
app.include_router(events.router)

# Include admin router (for data collection management)
from routers import admin
app.include_router(admin.router)

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
        "docs": "/api/docs",
        "data_source": "Real-time Steam API + Initial seed data"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
