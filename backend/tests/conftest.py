"""Test fixtures for database models."""

import pytest
import os
from typing import Any, AsyncGenerator, Generator
from dotenv import find_dotenv, load_dotenv
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from fastapi.testclient import TestClient
from sqlmodel import col, create_engine, Session, SQLModel
from sqlmodel.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine


from src.database.models import (
    Customer,
    CustomerIdentifier,
    Conversation,
    Message,
    Ticket,
    ChannelConfiguration,
    MessageAttachment,
    WebhookDeliveryLog,
    RateLimitEntry,
    Channel,
    IdentifierType,
    ConversationStatus,
    MessageDirection,
    MessageRole,
    DeliveryStatus,
    Priority,
    TicketStatus,
    WebhookProcessingStatus,
)

load_dotenv(find_dotenv())


@pytest.fixture(name="kafka_producer", scope="function")
async def kafka_producer_fixture() -> AsyncGenerator[Any, None]:
    """Create Kafka producer for E2E tests."""
    from src.kafka.producer import KafkaMessageProducer

    # Get Kafka bootstrap servers from environment
    kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    producer = None
    try:
        producer = KafkaMessageProducer(kafka_servers)
        await producer.start()
        yield producer
    except Exception as e:
        pytest.skip(f"Kafka not available: {e}")
    finally:
        if producer:
            await producer.stop()


@pytest.fixture(name="kafka_consumer", scope="function")
async def kafka_consumer_fixture() -> AsyncGenerator[AIOKafkaConsumer, None]:
    """Create Kafka consumer for E2E tests to verify message delivery."""

    # Get Kafka bootstrap servers from environment
    kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    consumer = None
    try:
        # Subscribe to all inbound topics
        consumer = AIOKafkaConsumer(
            "customer-intake.all.inbound",
            "customer-intake.webform.inbound",
            "customer-intake.email.inbound",
            "customer-intake.whatsapp.inbound",
            bootstrap_servers=kafka_servers,
            auto_offset_reset='latest',  # Only read new messages
            enable_auto_commit=False,
            group_id=f"test-consumer-{os.getpid()}",  # Unique group per test run
            consumer_timeout_ms=5000  # 5 second timeout
        )
        await consumer.start()
        yield consumer
    except KafkaError as e:
        pytest.skip(f"Kafka not available: {e}")
    finally:
        if consumer:
            await consumer.stop()


@pytest.fixture(name="engine")
def engine_fixture() -> Engine:
    """Create in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
async def session_fixture() -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for testing (SQLite for unit/integration tests)."""
    # Create async engine for unit/integration tests
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


@pytest.fixture(name="e2e_session", scope="function")
async def e2e_session_fixture() -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for E2E tests using real PostgreSQL."""
    # Get DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set - skipping E2E test")

    # Convert to async URL if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    # Create async engine for E2E tests with real PostgreSQL
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


@pytest.fixture(name="clean_test_data", scope="function")
async def clean_test_data_fixture(e2e_session: AsyncSession):
    """Clean up test data before and after E2E tests."""
    from sqlmodel import select, delete

    # Test identifiers from environment variables
    test_emails = []
    test_phones = []

    # Gmail E2E test emails
    sender_email = os.getenv("GMAIL_TEST_SENDER_EMAIL")
    receiver_email = os.getenv("GMAIL_TEST_RECEIVER_EMAIL")
    if sender_email:
        test_emails.append(sender_email)
    if receiver_email:
        test_emails.append(receiver_email)

    # WhatsApp E2E test phone
    whatsapp_from = os.getenv("TWILIO_TEST_FROM_NUMBER", "")
    if whatsapp_from:
        # Remove whatsapp: prefix if present
        phone = whatsapp_from.replace("whatsapp:", "")
        test_phones.append(phone)

    # Fallback hardcoded values for backward compatibility
    test_emails.extend([
        "alice@example.com",
        "ratelimit@example.com",
        "reopen@example.com",
        "continuity@example.com",
        "bob@example.com"
    ])

    async def cleanup():
        """Delete all test data for test identifiers."""
        # Collect all customer IDs to clean
        customer_ids = set()

        # Find customers by email
        for email in test_emails:
            result = await e2e_session.execute(
                select(CustomerIdentifier).where(CustomerIdentifier.identifier_value == email)
            )
            identifier = result.scalars().first()
            if identifier:
                customer_ids.add(identifier.customer_id)

        # Find customers by phone
        for phone in test_phones:
            result = await e2e_session.execute(
                select(CustomerIdentifier).where(CustomerIdentifier.identifier_value == phone)
            )
            identifier = result.scalars().first()
            if identifier:
                customer_ids.add(identifier.customer_id)

        # Delete all data for collected customer IDs
        for customer_id in customer_ids:
            # Delete in order: messages, tickets, conversations, identifiers, customer
            await e2e_session.execute(
                delete(Message).where(
                    col(Message.conversation_id).in_(
                        select(Conversation.id).where(Conversation.customer_id == customer_id)
                    )
                )
            )
            await e2e_session.execute(
                delete(Ticket).where(col(Ticket.customer_id) == customer_id)
            )
            await e2e_session.execute(
                delete(Conversation).where(col(Conversation.customer_id) == customer_id)
            )
            await e2e_session.execute(
                delete(CustomerIdentifier).where(col(CustomerIdentifier.customer_id) == customer_id)
            )
            await e2e_session.execute(
                delete(Customer).where(col(Customer.id) == customer_id)
            )

            await e2e_session.commit()

    # Clean before test
    await cleanup()

    yield

    # Clean after test
    await cleanup()


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    from src.main import app
    return TestClient(app)


@pytest.fixture
async def client_with_kafka(kafka_producer):
    """FastAPI async client with Kafka producer initialized."""
    from httpx import AsyncClient, ASGITransport
    from src.main import app
    from src.api.webhooks import web_form, whatsapp, gmail

    # Inject Kafka producer into webhook modules
    web_form.kafka_producer = kafka_producer
    whatsapp.kafka_producer = kafka_producer
    gmail.kafka_producer = kafka_producer

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client

    # Cleanup
    web_form.kafka_producer = None
    whatsapp.kafka_producer = None
    gmail.kafka_producer = None


@pytest.fixture
def sync_session(engine: Engine) -> Generator[Session, Any, None]:
    """Create synchronous database session for testing."""
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def sample_customer(sync_session: Session) -> Customer:
    """Create sample customer for testing."""
    customer = Customer(
        email="test@example.com",
        phone="+1234567890",
        name="Test Customer",
        metadata_={"source": "test"}
    )
    sync_session.add(customer)
    sync_session.commit()
    sync_session.refresh(customer)
    return customer


@pytest.fixture
def sample_conversation(sync_session: Session, sample_customer: Customer) -> Conversation:
    """Create sample conversation for testing."""
    conversation = Conversation(
        customer_id=sample_customer.id,
        initial_channel=Channel.EMAIL,
        status=ConversationStatus.ACTIVE,
        sentiment_score=0.5
    )
    sync_session.add(conversation)
    sync_session.commit()
    sync_session.refresh(conversation)
    return conversation


@pytest.fixture
def sample_message(sync_session: Session, sample_conversation: Conversation) -> Message:
    """Create sample message for testing."""
    message = Message(
        conversation_id=sample_conversation.id,
        channel=Channel.EMAIL,
        direction=MessageDirection.INBOUND,
        role=MessageRole.CUSTOMER,
        content="Test message content",
        delivery_status=DeliveryStatus.PENDING
    )
    sync_session.add(message)
    sync_session.commit()
    sync_session.refresh(message)
    return message
