"""Unit test fixtures for fast, isolated testing with SQLite."""

import pytest
from typing import Any, AsyncGenerator, Generator
from sqlmodel import create_engine, Session, SQLModel
from sqlmodel.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.engine import Engine

from src.database.models import (
    Customer,
    Conversation,
    Message,
    Channel,
    ConversationStatus,
    MessageDirection,
    MessageRole,
    DeliveryStatus,
)
from src.agent.context import CustomerSuccessContext


@pytest.fixture(name="engine")
def engine_fixture() -> Engine:
    """Create in-memory SQLite engine for unit testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
async def session_fixture() -> AsyncGenerator[AsyncSession, None]:
    """Create async SQLite session for unit tests.

    Note: This uses SQLite which doesn't support PostgreSQL-specific features.
    For tests requiring PostgreSQL features (UUID, jsonb, etc.), use session instead.
    """
    # Create async engine for unit tests
    async_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sync_session(engine: Engine) -> Generator[Session, Any, None]:
    """Create synchronous database session for unit testing."""
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
async def sample_customer(session: AsyncSession) -> Customer:
    """Create sample customer for async PostgreSQL testing."""
    from src.database.queries.customer import create_customer
    import uuid
    # Use unique email to avoid conflicts
    unique_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    customer = await create_customer(
        session,
        email=unique_email,
        phone="+1234567890",
        name="Test Customer"
    )
    await session.commit()
    return customer


@pytest.fixture
async def sample_conversation(session: AsyncSession, sample_customer: Customer) -> Conversation:
    """Create sample conversation for async PostgreSQL testing."""
    from src.database.queries.conversation import create_conversation
    conversation = await create_conversation(
        session,
        sample_customer.id,
        Channel.EMAIL,
        status=ConversationStatus.ACTIVE
    )
    await session.commit()
    return conversation


@pytest.fixture
async def sample_message(session: AsyncSession, sample_conversation: Conversation) -> Message:
    """Create sample message for async PostgreSQL testing."""
    from src.database.queries.message import create_message
    message = await create_message(
        session,
        sample_conversation.id,
        MessageRole.CUSTOMER,
        "Test message content",
        MessageDirection.INBOUND,
        Channel.EMAIL
    )
    await session.commit()
    return message


@pytest.fixture
def mock_customer_context() -> CustomerSuccessContext:
    """Create mock CustomerSuccessContext for unit testing."""
    return CustomerSuccessContext(
        db_session=None,  # Tests will mock database calls
        customer_id=None,
        customer_email=None,
        customer_phone=None,
        conversation_id=None,
        ticket_id=None,
        sentiment_score=None,
        escalation_triggered=False,
        escalation_reason=None,
        knowledge_articles_retrieved=[],
        channel="api",
        conversation_history=[]
    )
