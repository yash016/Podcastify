"""
Main FastAPI application entry point.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.api.endpoints import outline, episode, health, generate, upload

# Set up logging
setup_logging()
logger = get_logger(__name__)

# Get static files directory
STATIC_DIR = Path(__file__).parent / "static"

# Create FastAPI app
app = FastAPI(
    title="Podcastify API",
    description="AI-powered Socratic learning podcast generation",
    version="0.1.0",
    debug=settings.debug,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(outline.router, prefix="/api/v1", tags=["outline"])
app.include_router(episode.router, prefix="/api/v1", tags=["episode"])
app.include_router(upload.router, prefix="/api", tags=["upload"])  # MVP_0 upload endpoint
app.include_router(generate.router, prefix="/api", tags=["generate"])  # V1 MVP endpoint

# Mount static files (serve index.html)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info("starting_application", environment=settings.app_env)
    # TODO: Initialize database connection
    # TODO: Initialize Redis connection
    # TODO: Initialize Qdrant connection


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("shutting_down_application")
    # TODO: Close database connections
    # TODO: Close Redis connection


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
