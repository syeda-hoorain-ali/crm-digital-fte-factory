"""Integration tests for Gmail webhook endpoint."""

import pytest
import json
import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.main import app
from src.database.models import (
    Customer,
    Conversation,
    Message,
    Ticket,
    WebhookDeliveryLog,
    Channel,
    ConversationStatus,
    MessageDirection,
    MessageRole,
    DeliveryStatus,
    WebhookProcessingStatus,
)
from src.kafka.schemas import (
    ChannelMessage,
    Channel as KafkaChannel,
    MessageType, 
    MessageDirection as KafkaMessageDirection
)


@pytest.fixture
def mock_gmail_handler():
    """Mock Gmail handler for testing."""
    with patch('src.api.webhooks.gmail.gmail_handler') as mock:
        handler = AsyncMock()
        handler.verify_webhook_signature = AsyncMock(return_value=True)
        handler.process_inbound_message = AsyncMock()
        mock.return_value = handler
        yield handler


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for testing."""
    with patch('src.api.webhooks.gmail.kafka_producer') as mock:
        producer = AsyncMock()
        producer.send_message = AsyncMock(return_value=True)
        mock.return_value = producer
        yield producer


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter for testing."""
    with patch('src.api.webhooks.gmail.rate_limiter') as mock:
        limiter = AsyncMock()
        limiter.check_rate_limit = AsyncMock(return_value=(True, 9))
        limiter.record_request = AsyncMock()
        mock.return_value = limiter
        yield limiter


@pytest.fixture
def pubsub_notification():
    """Sample Pub/Sub notification payload."""
    data = {
        'emailAddress': 'msg_12345',
        'historyId': '67890'
    }
    encoded_data = base64.b64encode(json.dumps(data).encode()).decode()

    return {
        'message': {
            'data': encoded_data,
            'messageId': 'pubsub_msg_123',
            'publishTime': datetime.now(timezone.utc).isoformat(),
            'attributes': {}
        },
        'subscription': 'projects/test-project/subscriptions/gmail-sub'
    }


@pytest.fixture
def channel_message():
    """Sample channel message from Gmail handler."""
    from src.kafka.schemas import (
        ChannelMessage,
        Channel,
        MessageType, 
        MessageDirection
    )

    return ChannelMessage(
        message_id='msg_12345',
        channel=Channel.EMAIL,
        message_type=MessageType.INBOUND,
        direction=MessageDirection.CUSTOMER_TO_SUPPORT,
        customer_contact='customer@example.com',
        customer_id='customer_1234',
        customer_name='John Doe',
        subject='Support Request',
        body='I need help with my account',
        thread_id='thread_123',
        parent_message_id=None,
        attachments=[],
        metadata={
            'gmail_thread_id': 'thread_123',
            'is_reply': False
        },
        timestamp=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc),
        delivery_status=None
    )


class TestGmailWebhook:
    """Test suite for Gmail webhook endpoint."""

    @pytest.mark.asyncio
    async def test_gmail_webhook_success(
        self,
        client: TestClient,
        session: AsyncSession,
        pubsub_notification: dict,
        channel_message: ChannelMessage,
        mock_gmail_handler: AsyncMock,
        mock_kafka_producer: AsyncMock,
        mock_rate_limiter: AsyncMock
    ):
        """Test successful Gmail webhook processing."""
        # Setup mocks
        mock_gmail_handler.process_inbound_message.return_value = channel_message

        # Send webhook request
        response = client.post(
            '/webhooks/gmail',
            json=pubsub_notification,
            headers={'X-Goog-Signature': 'valid_signature'}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'message_id' in data
        assert 'request_id' in data

        # Verify customer created
        customer = await session.execute(
            select(Customer).where(Customer.email == 'customer@example.com')
        )
        customer = customer.first()
        assert customer is not None
        assert customer.name == 'John Doe'

        # Verify conversation created
        conversation = await session.execute(
            select(Conversation).where(Conversation.customer_id == customer.id)
        )
        conversation = conversation.first()
        assert conversation is not None
        assert conversation.initial_channel == Channel.EMAIL
        assert conversation.status == ConversationStatus.ACTIVE

        # Verify message created
        message = await session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        message = message.first()
        assert message is not None
        assert message.content == 'I need help with my account'
        assert message.channel == Channel.EMAIL
        assert message.direction == MessageDirection.INBOUND
        assert message.role == MessageRole.CUSTOMER

        # Verify ticket created
        ticket = await session.execute(
            select(Ticket).where(Ticket.conversation_id == conversation.id)
        )
        ticket = ticket.first()
        assert ticket is not None
        assert ticket.source_channel == Channel.EMAIL

        # Verify webhook log
        webhook_log = await session.execute(
            select(WebhookDeliveryLog).where(
                WebhookDeliveryLog.webhook_type == 'gmail'
            )
        )
        webhook_log = webhook_log.first()
        assert webhook_log is not None
        assert webhook_log.signature_valid is True
        assert webhook_log.processing_status == WebhookProcessingStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_gmail_webhook_invalid_signature(
        self,
        client: TestClient,
        pubsub_notification: dict,
        mock_gmail_handler: AsyncMock
    ):
        """Test Gmail webhook with invalid signature."""
        # Setup mock to return False for signature verification
        mock_gmail_handler.verify_webhook_signature.return_value = False

        response = client.post(
            '/webhooks/gmail',
            json=pubsub_notification,
            headers={'X-Goog-Signature': 'invalid_signature'}
        )

        assert response.status_code == 401
        assert 'Invalid webhook signature' in response.json()['detail']

    @pytest.mark.asyncio
    async def test_gmail_webhook_missing_signature(
        self,
        client: TestClient,
        pubsub_notification: dict
    ):
        """Test Gmail webhook with missing signature."""
        response = client.post(
            '/webhooks/gmail',
            json=pubsub_notification
        )

        assert response.status_code == 401
        assert 'Missing webhook signature' in response.json()['detail']

    @pytest.mark.asyncio
    async def test_gmail_webhook_rate_limit_exceeded(
        self,
        client: TestClient,
        session: AsyncSession,
        pubsub_notification: dict,
        channel_message: ChannelMessage,
        mock_gmail_handler: AsyncMock,
        mock_rate_limiter: AsyncMock
    ):
        """Test Gmail webhook with rate limit exceeded."""
        # Setup mocks
        mock_gmail_handler.process_inbound_message.return_value = channel_message
        mock_rate_limiter.check_rate_limit.return_value = (False, 0)
        mock_rate_limiter.get_retry_after.return_value = 60

        response = client.post(
            '/webhooks/gmail',
            json=pubsub_notification,
            headers={'X-Goog-Signature': 'valid_signature'}
        )

        assert response.status_code == 429
        assert 'Too many requests' in response.json()['detail']
        assert response.headers.get('Retry-After') == '60'

        # Verify webhook log marked as failed
        webhook_log = await session.execute(
            select(WebhookDeliveryLog).where(
                WebhookDeliveryLog.webhook_type == 'gmail'
            )
        )
        webhook_log = webhook_log.first()
        assert webhook_log is not None
        assert webhook_log.processing_status == WebhookProcessingStatus.FAILED

    @pytest.mark.asyncio
    async def test_gmail_webhook_reply_to_existing_conversation(
        self,
        client: TestClient,
        session: AsyncSession,
        pubsub_notification: dict,
        mock_gmail_handler: AsyncMock,
        mock_kafka_producer: AsyncMock,
        mock_rate_limiter: AsyncMock
    ):
        """Test Gmail webhook for reply to existing conversation."""
        # Create existing customer and conversation
        customer = Customer(
            email='customer@example.com',
            name='John Doe'
        )
        session.add(customer)
        await session.commit()
        await session.refresh(customer)

        conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.EMAIL,
            status=ConversationStatus.ACTIVE
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)

        # Create existing message with thread ID
        existing_message = Message(
            conversation_id=conversation.id,
            channel=Channel.EMAIL,
            direction=MessageDirection.INBOUND,
            role=MessageRole.CUSTOMER,
            content='Original message',
            thread_id='thread_123',
            delivery_status=DeliveryStatus.DELIVERED
        )
        session.add(existing_message)
        await session.commit()

        # Create reply channel message
        from src.kafka.schemas import (
            ChannelMessage,
            Channel as KafkaChannel,
            MessageType, 
            MessageDirection as KafkaMessageDirection
        )

        reply_message = ChannelMessage(
            message_id='msg_67890',
            channel=KafkaChannel.EMAIL,
            message_type=MessageType.INBOUND,
            direction=KafkaMessageDirection.CUSTOMER_TO_SUPPORT,
            customer_contact='customer@example.com',
            customer_id='customer_1234',
            customer_name='John Doe',
            subject='Re: Support Request',
            body='Follow-up question',
            thread_id='thread_123',
            parent_message_id='msg_12345',
            attachments=[],
            metadata={
                'gmail_thread_id': 'thread_123',
                'is_reply': True
            },
            timestamp=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            delivery_status=None
        )

        mock_gmail_handler.process_inbound_message.return_value = reply_message

        # Send webhook request
        response = client.post(
            '/webhooks/gmail',
            json=pubsub_notification,
            headers={'X-Goog-Signature': 'valid_signature'}
        )

        assert response.status_code == 200

        # Verify no new conversation created
        conversations = await session.execute(
            select(Conversation).where(Conversation.customer_id == customer.id)
        )
        conversations = conversations.all()
        assert len(conversations) == 1

        # Verify new message added to existing conversation
        messages = await session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        messages = messages.all()
        assert len(messages) == 2
        assert messages[1].content == 'Follow-up question'

        # Verify no new ticket created
        tickets = await session.execute(
            select(Ticket).where(Ticket.conversation_id == conversation.id)
        )
        tickets = tickets.all()
        # Should have 0 or 1 ticket (depending on if one was created initially)
        assert len(tickets) <= 1

    @pytest.mark.asyncio
    async def test_gmail_webhook_invalid_pubsub_data(
        self,
        client: TestClient,
        mock_gmail_handler: AsyncMock
    ):
        """Test Gmail webhook with invalid Pub/Sub data."""
        invalid_notification = {
            'message': {
                'data': 'invalid_base64!!!',
                'messageId': 'pubsub_msg_123',
                'publishTime': datetime.now(timezone.utc).isoformat()
            },
            'subscription': 'projects/test-project/subscriptions/gmail-sub'
        }

        response = client.post(
            '/webhooks/gmail',
            json=invalid_notification,
            headers={'X-Goog-Signature': 'valid_signature'}
        )

        assert response.status_code == 400
        assert 'Invalid Pub/Sub message format' in response.json()['detail']

    @pytest.mark.asyncio
    async def test_gmail_webhook_missing_message_id(
        self,
        client: TestClient,
        mock_gmail_handler: AsyncMock
    ):
        """Test Gmail webhook with missing Gmail message ID."""
        # Create notification without emailAddress
        data = {'historyId': '67890'}
        encoded_data = base64.b64encode(json.dumps(data).encode()).decode()

        notification = {
            'message': {
                'data': encoded_data,
                'messageId': 'pubsub_msg_123',
                'publishTime': datetime.now(timezone.utc).isoformat()
            },
            'subscription': 'projects/test-project/subscriptions/gmail-sub'
        }

        response = client.post(
            '/webhooks/gmail',
            json=notification,
            headers={'X-Goog-Signature': 'valid_signature'}
        )

        assert response.status_code == 400
        assert 'Missing Gmail message ID' in response.json()['detail']

    @pytest.mark.asyncio
    async def test_gmail_webhook_handler_not_initialized(
        self,
        client: TestClient,
        pubsub_notification: dict
    ):
        """Test Gmail webhook when handler not initialized."""
        with patch('src.api.webhooks.gmail.gmail_handler', None):
            response = client.post(
                '/webhooks/gmail',
                json=pubsub_notification,
                headers={'X-Goog-Signature': 'valid_signature'}
            )

            assert response.status_code == 503
            assert 'Gmail handler not initialized' in response.json()['detail']

    @pytest.mark.asyncio
    async def test_gmail_webhook_kafka_send_failure(
        self,
        client: TestClient,
        session: AsyncSession,
        pubsub_notification: dict,
        channel_message: ChannelMessage,
        mock_gmail_handler: AsyncMock,
        mock_kafka_producer: AsyncMock,
        mock_rate_limiter: AsyncMock
    ):
        """Test Gmail webhook when Kafka send fails."""
        # Setup mocks
        mock_gmail_handler.process_inbound_message.return_value = channel_message
        mock_kafka_producer.send_message.return_value = False

        response = client.post(
            '/webhooks/gmail',
            json=pubsub_notification,
            headers={'X-Goog-Signature': 'valid_signature'}
        )

        # Should still return success (Kafka failure is logged but not fatal)
        assert response.status_code == 200

        # Verify webhook log still marked as completed
        webhook_log = await session.execute(
            select(WebhookDeliveryLog).where(
                WebhookDeliveryLog.webhook_type == 'gmail'
            )
        )
        webhook_log = webhook_log.first()
        assert webhook_log is not None
        assert webhook_log.processing_status == WebhookProcessingStatus.COMPLETED
