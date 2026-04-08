"""Shared test fixtures for all test types."""

import pytest
import os
from typing import AsyncGenerator
from dotenv import find_dotenv, load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Load environment variables
load_dotenv(find_dotenv())


@pytest.fixture(name="session", scope="function")
async def session_fixture() -> AsyncGenerator[AsyncSession, None]:
    """Create async database session using real PostgreSQL.

    Used by both E2E and integration tests that require PostgreSQL-specific features.
    """
    # Get DATABASE_URL from environment
    database_url = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL"))
    if not database_url:
        pytest.skip("DATABASE_URL not set - skipping test requiring PostgreSQL")

    # Convert to async URL if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    # Create async engine for tests with real PostgreSQL
    async_engine = create_async_engine(
        database_url,
        echo=False,
    )

    # Create session
    async_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    # Clean up engine
    await async_engine.dispose()
