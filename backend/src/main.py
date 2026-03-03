"""FastAPI application for Customer Success Agent API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .api.routes.agent import router as agent_router
from .database.connection import init_db, close_engine, get_session

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown events:
    - Startup: Validate configuration and initialize database connection
    - Shutdown: Cleanup database connections
    """
    # Startup
    logger.info("Starting up...")

    # Step 1: Validate configuration on startup
    try:
        logger.info("Validating configuration...")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Log Level: {settings.log_level}")
        logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise RuntimeError(
            f"Configuration validation failed. Please check your .env file and environment variables: {e}"
        ) from e

    # Step 2: Initialize database connection
    try:
        logger.info("Initializing database connection...")
        await init_db()
        logger.info("Database connection initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise RuntimeError(
            f"Database initialization failed. Please check your DATABASE_URL: {e}"
        ) from e

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_engine()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Customer Success Agent API",
    description="Production-ready customer support agent with OpenAI Agents SDK",
    version="1.0.0",
    lifespan=lifespan,
)


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
app.include_router(agent_router)

@app.get("/health")
async def health_check():
    """
    Health check endpoint with database connectivity verification.

    Returns:
        dict: Health status with database connectivity information

    Raises:
        HTTPException: 503 status if database is not accessible
    """
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )

