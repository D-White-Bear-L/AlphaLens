"""Main FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting News Trace Backend...")
    logger.info(f"Model: {settings.model}")
    logger.info(f"API Provider: {settings.api_provider}")
    logger.info(f"Database: {settings.database_url}")
    
    # Initialize database (if sqlalchemy is available)
    try:
        from app.database import init_database, SQLALCHEMY_AVAILABLE
        if SQLALCHEMY_AVAILABLE:
            init_database()
            logger.info("Database initialized")
        else:
            logger.info("Database features disabled (sqlalchemy not installed)")
    except Exception as e:
        logger.warning(f"Database initialization warning: {str(e)}")
    
    # Install playwright browsers if needed
    try:
        from playwright.async_api import async_playwright
        logger.info("Playwright is available")
    except ImportError:
        logger.warning("Playwright not installed. Run: playwright install")
    
    yield
    
    # Shutdown
    logger.info("Shutting down News Trace Backend...")


# Create FastAPI app
app = FastAPI(
    title="Financial News Trace Backend",
    description="Backend API for tracing financial news sources using AI agents",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["news-trace"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Financial News Trace Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )

