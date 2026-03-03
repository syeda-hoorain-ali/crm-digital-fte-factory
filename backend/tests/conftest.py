"""Pytest configuration and fixtures for CRM backend tests."""

import asyncio
import pytest
import pytest_asyncio
from uuid import uuid4
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.database.models import (
    Customer,
    CustomerIdentifier,
    Conversation,
    Message,
    Ticket,
    KnowledgeBase,
    IdentifierType,
    Channel,
    ConversationStatus,
    MessageRole,
    MessageDirection,
    DeliveryStatus,
    Priority,
    TicketStatus,
)
from src.config import settings


# ============================================================================
# Event Loop Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Session Fixtures
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create async database engine for tests.

    Uses the same database as production but with transaction rollback for isolation.
    Each test runs in its own transaction that is rolled back after completion.
    """
    # Use the same database URL from settings
    test_db_url = settings.database_url

    # Ensure asyncpg driver is used
    if test_db_url.startswith("postgresql://"):
        test_db_url = test_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Remove sslmode and channel_binding parameters (asyncpg doesn't support them in URL)
    if "?" in test_db_url:
        base_url, params = test_db_url.split("?", 1)
        param_pairs = [p for p in params.split("&") if not p.startswith(("sslmode=", "channel_binding="))]
        if param_pairs:
            test_db_url = f"{base_url}?{'&'.join(param_pairs)}"
        else:
            test_db_url = base_url

    # For asyncpg, SSL must be configured via connect_args, not URL parameters
    engine = create_async_engine(
        test_db_url,
        echo=False,
        poolclass=NullPool,  # Disable connection pooling for tests
        connect_args={"ssl": "require"},  # SSL configuration for asyncpg
    )

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async with db_engine.connect() as conn:
        await conn.begin()  # outer transaction, never committed

        async with AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",  # allows inner commits via savepoints
        ) as session:
            yield session

        await conn.rollback()  # always rolls back, leaving DB clean


# ============================================================================
# Test Data Fixtures - Customers
# ============================================================================

@pytest_asyncio.fixture
async def test_customer(db_session: AsyncSession) -> Customer:
    """Create a test customer."""
    customer = Customer(
        id=uuid4(),
        email="test@example.com",
        phone="+1234567890",
        name="Test Customer",
        meta_data={"tier": "standard"},
    )
    db_session.add(customer)
    await db_session.flush()
    await db_session.refresh(customer)
    return customer


@pytest_asyncio.fixture
async def test_customer_premium(db_session: AsyncSession) -> Customer:
    """Create a premium tier test customer."""
    customer = Customer(
        id=uuid4(),
        email="premium@example.com",
        phone="+1987654321",
        name="Premium Customer",
        meta_data={"tier": "premium", "account_value": 50000},
    )
    db_session.add(customer)
    await db_session.flush()
    await db_session.refresh(customer)
    return customer


# ============================================================================
# Test Data Fixtures - Customer Identifiers
# ============================================================================

@pytest_asyncio.fixture
async def test_customer_identifier_email(
    db_session: AsyncSession, test_customer: Customer
) -> CustomerIdentifier:
    """Create email identifier for test customer."""
    identifier = CustomerIdentifier(
        id=uuid4(),
        customer_id=test_customer.id,
        identifier_type=IdentifierType.EMAIL,
        identifier_value=test_customer.email,
        verified=True,
    )
    db_session.add(identifier)
    await db_session.flush()
    await db_session.refresh(identifier)
    return identifier


@pytest_asyncio.fixture
async def test_customer_identifier_phone(
    db_session: AsyncSession, test_customer: Customer
) -> CustomerIdentifier:
    """Create phone identifier for test customer."""
    identifier = CustomerIdentifier(
        id=uuid4(),
        customer_id=test_customer.id,
        identifier_type=IdentifierType.PHONE,
        identifier_value=test_customer.phone,
        verified=False,
    )
    db_session.add(identifier)
    await db_session.flush()
    await db_session.refresh(identifier)
    return identifier


# ============================================================================
# Test Data Fixtures - Conversations
# ============================================================================

@pytest_asyncio.fixture
async def test_conversation(
    db_session: AsyncSession, test_customer: Customer
) -> Conversation:
    """Create a test conversation."""
    conversation = Conversation(
        id=uuid4(),
        customer_id=test_customer.id,
        initial_channel=Channel.API,
        status=ConversationStatus.ACTIVE,
        sentiment_score=0.5,
    )
    db_session.add(conversation)
    await db_session.flush()
    await db_session.refresh(conversation)
    return conversation


@pytest_asyncio.fixture
async def test_conversation_escalated(
    db_session: AsyncSession, test_customer: Customer
) -> Conversation:
    """Create an escalated test conversation."""
    conversation = Conversation(
        id=uuid4(),
        customer_id=test_customer.id,
        initial_channel=Channel.EMAIL,
        status=ConversationStatus.ESCALATED,
        sentiment_score=-0.7,
        escalated_to="support-team@example.com",
    )
    db_session.add(conversation)
    await db_session.flush()
    await db_session.refresh(conversation)
    return conversation


# ============================================================================
# Test Data Fixtures - Messages
# ============================================================================

@pytest_asyncio.fixture
async def test_message_customer(
    db_session: AsyncSession, test_conversation: Conversation
) -> Message:
    """Create a customer message."""
    message = Message(
        id=uuid4(),
        conversation_id=test_conversation.id,
        channel=Channel.API,
        direction=MessageDirection.INBOUND,
        role=MessageRole.CUSTOMER,
        content="I need help with my account",
        sentiment_score=0.2,
    )
    db_session.add(message)
    await db_session.flush()
    await db_session.refresh(message)
    return message


@pytest_asyncio.fixture
async def test_message_agent(
    db_session: AsyncSession, test_conversation: Conversation
) -> Message:
    """Create an agent message."""
    message = Message(
        id=uuid4(),
        conversation_id=test_conversation.id,
        channel=Channel.API,
        direction=MessageDirection.OUTBOUND,
        role=MessageRole.AGENT,
        content="I'd be happy to help you with your account.",
        tokens_used=50,
        latency_ms=250,
        delivery_status=DeliveryStatus.SENT,
    )
    db_session.add(message)
    await db_session.flush()
    await db_session.refresh(message)
    return message


# ============================================================================
# Test Data Fixtures - Tickets
# ============================================================================

@pytest_asyncio.fixture
async def test_ticket(
    db_session: AsyncSession,
    test_conversation: Conversation,
    test_customer: Customer,
) -> Ticket:
    """Create a test ticket."""
    ticket = Ticket(
        id=uuid4(),
        conversation_id=test_conversation.id,
        customer_id=test_customer.id,
        source_channel=Channel.API,
        category="technical",
        priority=Priority.MEDIUM,
        status=TicketStatus.OPEN,
    )
    db_session.add(ticket)
    await db_session.flush()
    await db_session.refresh(ticket)
    return ticket


@pytest_asyncio.fixture
async def test_ticket_high_priority(
    db_session: AsyncSession,
    test_conversation_escalated: Conversation,
    test_customer_premium: Customer,
) -> Ticket:
    """Create a high priority test ticket."""
    ticket = Ticket(
        id=uuid4(),
        conversation_id=test_conversation_escalated.id,
        customer_id=test_customer_premium.id,
        source_channel=Channel.EMAIL,
        category="billing",
        priority=Priority.HIGH,
        status=TicketStatus.IN_PROGRESS,
    )
    db_session.add(ticket)
    await db_session.flush()
    await db_session.refresh(ticket)
    return ticket


# ============================================================================
# Test Data Fixtures - Knowledge Base
# ============================================================================

@pytest_asyncio.fixture
async def test_knowledge_article(db_session: AsyncSession) -> KnowledgeBase:
    """Create a test knowledge base article."""
    # Create a dummy embedding (384 dimensions for all-MiniLM-L6-v2)
    dummy_embedding = [0.1] * 384

    article = KnowledgeBase(
        id=uuid4(),
        title="How to Reset Your Password",
        content="To reset your password, go to Settings > Security > Reset Password. Follow the instructions sent to your email.",
        category="account",
        embedding=dummy_embedding,
    )
    db_session.add(article)
    await db_session.flush()
    await db_session.refresh(article)
    return article


@pytest_asyncio.fixture
async def test_knowledge_articles(db_session: AsyncSession) -> list[KnowledgeBase]:
    """Create multiple test knowledge base articles."""
    dummy_embedding = [0.1] * 384

    articles = [
        KnowledgeBase(
            id=uuid4(),
            title="Getting Started Guide",
            content="Welcome to CloudStream CRM! This guide will help you get started with the platform.",
            category="onboarding",
            embedding=dummy_embedding,
        ),
        KnowledgeBase(
            id=uuid4(),
            title="Billing FAQ",
            content="Common questions about billing, invoices, and payment methods.",
            category="billing",
            embedding=dummy_embedding,
        ),
        KnowledgeBase(
            id=uuid4(),
            title="API Documentation",
            content="Complete API reference for CloudStream CRM integration.",
            category="technical",
            embedding=dummy_embedding,
        ),
    ]

    for article in articles:
        db_session.add(article)

    await db_session.flush()
    for article in articles:
        await db_session.refresh(article)

    return articles


# ============================================================================
# Mock Fixtures for Unit Tests
# ============================================================================

@pytest.fixture
def mock_customer_context():
    """Mock CustomerSuccessContext for unit tests."""
    from src.agent.context import CustomerSuccessContext
    from unittest.mock import create_autospec
    from sqlalchemy.ext.asyncio import AsyncSession

    # Create a mock that passes isinstance checks
    mock_session = create_autospec(AsyncSession, instance=True)

    context = CustomerSuccessContext(
        db_session=mock_session,
        customer_id=str(uuid4()),
        customer_email="test@example.com",
        customer_phone="+1234567890",
        conversation_id=str(uuid4()),
        channel="api",
    )
    return context


@pytest.fixture
def mock_run_context_wrapper(mock_customer_context):
    """Mock RunContextWrapper for unit tests."""
    from unittest.mock import MagicMock

    wrapper = MagicMock()
    wrapper.context = mock_customer_context
    return wrapper
