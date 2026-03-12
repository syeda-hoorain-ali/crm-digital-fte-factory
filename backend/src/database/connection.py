"""Database connection management with async support and connection pooling."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy import text

from ..config import settings

logger = logging.getLogger(__name__)


# Global engine instance
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """
    Get or create the async database engine with connection pooling.

    Returns:
        AsyncEngine: SQLAlchemy async engine instance
    """
    global _engine

    if _engine is None:
        # Convert postgresql:// to postgresql+asyncpg:// if needed
        database_url = settings.database_url
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Determine pool class based on environment
        if settings.environment == "test":
            # Use NullPool for testing to avoid connection issues
            pool_kwargs = {
                "poolclass": NullPool,
            }
        else:
            # For async engines, SQLAlchemy automatically uses AsyncAdaptedQueuePool
            # We just need to configure the pool parameters
            pool_kwargs = {
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
                "pool_timeout": settings.db_pool_timeout,
                "pool_pre_ping": True,  # Verify connections before using
                "pool_recycle": 300,  # Recycle connections after 5 minutes
            }

        _engine = create_async_engine(
            database_url,
            echo=settings.enable_debug_logging,
            **pool_kwargs,
        )

        logger.info(
            f"Created async database engine with pool_size={pool_kwargs.get('pool_size', 'N/A')}, "
            f"max_overflow={pool_kwargs.get('max_overflow', 'N/A')}"
        )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the async session factory.

    Returns:
        async_sessionmaker: Session factory for creating database sessions
    """
    global _session_factory

    if _session_factory is None:
        engine = get_async_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        logger.info("Created async session factory")

    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions with automatic cleanup.

    Usage:
        async with get_session() as session:
            result = await session.execute(query)
            await session.commit()

    Yields:
        AsyncSession: Database session
    """
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    This is a raw async generator (not wrapped in @asynccontextmanager)
    for use with FastAPI's Depends() system.

    Usage:
        async def endpoint(session: AsyncSession = Depends(get_session_dependency)):
            result = await session.execute(query)
            await session.commit()

    Yields:
        AsyncSession: Database session
    """
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def test_connection(max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    """
    Test database connection with retry logic and exponential backoff.

    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Initial delay between retries in seconds

    Returns:
        bool: True if connection successful, False otherwise
    """
    engine = get_async_engine()

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                logger.info("Database connection test successful")
                return True
        except (OperationalError, DBAPIError) as e:
            if attempt < max_retries:
                # Exponential backoff: 1s, 2s, 4s, 8s, etc.
                delay = retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"Database connection attempt {attempt}/{max_retries} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"Database connection failed after {max_retries} attempts: {e}"
                )
                return False

    return False


async def close_engine() -> None:
    """Close the database engine and cleanup connections."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed and connections cleaned up")


async def init_db() -> None:
    """
    Initialize database connection with retry logic.

    Raises:
        RuntimeError: If database connection cannot be established
    """
    logger.info("Initializing database connection...")

    if not await test_connection(max_retries=5, retry_delay=1.0):
        raise RuntimeError(
            "Failed to establish database connection after multiple attempts. "
            "Please check your DATABASE_URL and ensure the database is running."
        )

    logger.info("Database connection initialized successfully")
