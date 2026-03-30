"""Integration test fixtures for testing with real PostgreSQL database."""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from src.database.models import (
    Customer,
    CustomerIdentifier,
    Conversation,
    Message,
    Ticket,
    KnowledgeBase,
    Channel,
    ConversationStatus,
    MessageDirection,
    MessageRole,
    IdentifierType,
    TicketStatus,
    Priority,
)
from tests.integration.test_helpers import (
    cleanup_customer_data,
    cleanup_conversation_data,
    cleanup_knowledge_base_entry,
    cleanup_customer_identifier,
)


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client for integration tests."""
    from src.main import app
    return TestClient(app)


@pytest.fixture
async def test_customer(session: AsyncSession):
    """Create test customer for integration tests with automatic cleanup."""
    from src.database.queries.customer import create_customer
    unique_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    customer = await create_customer(
        session,
        email=unique_email,
        phone="+1234567890",
        name="Test Customer",
        meta_data={"tier": "standard"}
    )
    await session.commit()

    try:
        yield customer
    finally:
        # Cleanup: Delete all data associated with this customer
        try:
            await cleanup_customer_data(session, customer.id)
        except Exception as e:
            print(f"Warning: Cleanup failed for customer {customer.id}: {e}")


@pytest.fixture
async def test_customer_premium(session: AsyncSession):
    """Create premium test customer for integration tests with automatic cleanup."""
    from src.database.queries.customer import create_customer
    unique_email = f"premium-{uuid.uuid4().hex[:8]}@example.com"
    customer = await create_customer(
        session,
        email=unique_email,
        phone="+9876543210",
        name="Premium Customer",
        meta_data={"tier": "premium"}
    )
    await session.commit()

    try:
        yield customer
    finally:
        # Cleanup: Delete all data associated with this customer
        try:
            await cleanup_customer_data(session, customer.id)
        except Exception as e:
            print(f"Warning: Cleanup failed for premium customer {customer.id}: {e}")


@pytest.fixture
async def test_customer_identifier_email(session: AsyncSession, test_customer: Customer):
    """Create email identifier for test customer with automatic cleanup."""
    from src.database.queries.customer import create_customer_identifier
    assert test_customer.email is not None, "Test customer must have email"
    identifier = await create_customer_identifier(
        session,
        test_customer.id,
        IdentifierType.EMAIL,
        test_customer.email
    )
    await session.commit()

    try:
        yield identifier
    finally:
        # Cleanup: Delete this identifier (customer cleanup will handle it, but explicit is safer)
        try:
            await cleanup_customer_identifier(session, identifier.id)
        except Exception:
            pass  # May already be deleted by customer cleanup


@pytest.fixture
async def test_customer_identifier_phone(session: AsyncSession, test_customer: Customer):
    """Create phone identifier for test customer with automatic cleanup."""
    from src.database.queries.customer import create_customer_identifier
    assert test_customer.phone is not None, "Test customer must have phone"
    identifier = await create_customer_identifier(
        session,
        test_customer.id,
        IdentifierType.PHONE,
        test_customer.phone
    )
    await session.commit()

    try:
        yield identifier
    finally:
        # Cleanup: Delete this identifier (customer cleanup will handle it, but explicit is safer)
        try:
            await cleanup_customer_identifier(session, identifier.id)
        except Exception:
            pass  # May already be deleted by customer cleanup


@pytest.fixture
async def test_conversation(session: AsyncSession, test_customer: Customer):
    """Create test conversation for integration tests with automatic cleanup."""
    from src.database.queries.conversation import create_conversation
    conversation = await create_conversation(
        session,
        test_customer.id,
        Channel.EMAIL,
        status=ConversationStatus.ACTIVE
    )
    await session.commit()

    try:
        yield conversation
    finally:
        # Cleanup: Delete conversation and related data (customer cleanup will handle it, but explicit is safer)
        try:
            await cleanup_conversation_data(session, conversation.id)
        except Exception:
            pass  # May already be deleted by customer cleanup


@pytest.fixture
async def test_message(session: AsyncSession, test_conversation: Conversation):
    """Create test message for integration tests with automatic cleanup."""
    from src.database.queries.message import create_message
    message = await create_message(
        session,
        test_conversation.id,
        MessageRole.CUSTOMER,
        "Test message content",
        MessageDirection.INBOUND,
        Channel.EMAIL
    )
    await session.commit()

    try:
        yield message
    finally:
        # Cleanup: Message will be deleted by conversation cleanup, no explicit cleanup needed
        pass


@pytest.fixture
async def test_ticket(session: AsyncSession, test_customer: Customer, test_conversation: Conversation):
    """Create test ticket for integration tests with automatic cleanup."""
    from src.database.queries.ticket import create_ticket
    ticket = await create_ticket(
        session,
        test_customer.id,
        test_conversation.id,
        category="technical",
        priority=Priority.MEDIUM,
        source_channel=Channel.EMAIL
    )
    await session.commit()

    try:
        yield ticket
    finally:
        # Cleanup: Ticket will be deleted by conversation/customer cleanup, no explicit cleanup needed
        pass


@pytest.fixture
async def test_knowledge_article(session: AsyncSession):
    """Create test knowledge base article for integration tests with automatic cleanup."""
    from src.database.queries.knowledge_base import create_knowledge_base_entry
    # Create a simple embedding vector (384 dimensions for all-MiniLM-L6-v2)
    embedding = [0.1] * 384
    article = await create_knowledge_base_entry(
        session,
        title="Test Article",
        content="This is test content for the knowledge base.",
        embedding=embedding,
        category="test",
        metadata={"source": "test"}
    )
    await session.commit()

    try:
        yield article
    finally:
        # Cleanup: Delete knowledge base entry
        try:
            await cleanup_knowledge_base_entry(session, article.id)
        except Exception as e:
            print(f"Warning: Cleanup failed for knowledge article {article.id}: {e}")
