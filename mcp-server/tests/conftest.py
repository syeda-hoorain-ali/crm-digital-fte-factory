import os
import pytest
from collections.abc import AsyncGenerator
from sqlmodel import create_engine, Session, SQLModel
from sqlmodel.pool import StaticPool
from src.database.session import get_session
from src.database.models import Customer, SupportTicket, DocumentationResult, EscalationRecord
from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session

from src.main import mcp


@pytest.fixture(name="session")
def session_fixture():
    # Use PostgreSQL for tests to match production behavior

    # Prioritize testing database URL, then fall back to general DATABASE_URL
    database_url = os.getenv("TESTING_DATABASE_URL") or os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("Either TESTING_DATABASE_URL or DATABASE_URL must be set for tests")

    engine = create_engine(
        database_url,
        # Additional connection parameters for PostgreSQL
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    SQLModel.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
async def client_session() -> AsyncGenerator[ClientSession]:
    # The `client` fixture creates a connected client that can be reused across multiple tests.
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as _session:
        yield _session
