"""FastAPI application entry point."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.config import get_config
from app.common.logging import setup_logging
from app.api.routes import router

# Setup logging
config = get_config()
setup_logging(log_level=config.log_level, json_logging=config.json_logging)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=config.api_title,
    version=config.api_version,
    description="Multi-modal vehicle identification pipeline for traffic cameras",
    docs_url="/docs" if config.is_development else None,
    redoc_url="/redoc" if config.is_development else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if config.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, tags=["TrafficIQ"])

# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info(f"TrafficIQ API starting (Environment: {config.environment})")
    config.setup_artifacts_dir()
    logger.info("Artifacts directory ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("TrafficIQ API shutting down")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=config.log_level.lower(),
    )
