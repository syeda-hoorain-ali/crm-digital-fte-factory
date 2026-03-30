"""E2E test fixtures for end-to-end testing with real services."""

import pytest
import os
from typing import Any, AsyncGenerator
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select, delete

from src.database.models import (
    Customer,
    CustomerIdentifier,
    Conversation,
    Message,
    Ticket,
    AgentMetric,
)


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


@pytest.fixture(name="clean_test_data", scope="function")
async def clean_test_data_fixture(e2e_session: AsyncSession):
    """Clean up test data before and after E2E tests."""

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
            # Delete in order: messages, tickets, agent_metrics, conversations, identifiers, customer
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
            # Delete agent_metrics before conversations (foreign key constraint)
            await e2e_session.execute(
                delete(AgentMetric).where(
                    col(AgentMetric.conversation_id).in_(
                        select(Conversation.id).where(Conversation.customer_id == customer_id)
                    )
                )
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
async def client_with_kafka(kafka_producer):
    """FastAPI async client with Kafka producer initialized."""
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
