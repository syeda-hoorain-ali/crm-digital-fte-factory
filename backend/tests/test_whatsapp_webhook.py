"""Integration tests for WhatsApp webhook endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime
import uuid

from src.database.models import (
    Customer,
    Conversation,
    Message,
    WebhookDeliveryLog,
    Channel,
    ConversationStatus,
    MessageDirection,
    MessageRole,
    DeliveryStatus,
    WebhookProcessingStatus,
)


@pytest.fixture
async def async_client():
    """Async HTTP client for testing."""
    from src.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    producer = MagicMock()
    producer.send_message = AsyncMock(return_value=True)
    return producer


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter."""
    limiter = MagicMock()
    limiter.check_rate_limit = AsyncMock(return_value=(True, 9))
    limiter.record_request = AsyncMock()
    return limiter


@pytest.fixture
def whatsapp_webhook_payload():
    """Sample WhatsApp webhook payload from Twilio."""
    return {
        "MessageSid": "SM123456789",
        "From": "whatsapp:+1234567890",
        "To": "whatsapp:+0987654321",
        "Body": "Hello, I need help with my order",
        "ProfileName": "John Doe",
        "NumMedia": "0"
    }


@pytest.fixture
def whatsapp_status_payload():
    """Sample WhatsApp status callback payload from Twilio."""
    return {
        "MessageSid": "SM123456789",
        "MessageStatus": "delivered",
        "To": "whatsapp:+1234567890",
        "From": "whatsapp:+0987654321"
    }


class TestWhatsAppWebhook:
    """Test WhatsApp webhook endpoint."""

    @pytest.mark.asyncio
    async def test_receive_message_success(
        self,
        async_client: AsyncClient,
        whatsapp_webhook_payload: dict[str, str],
        mock_kafka_producer: MagicMock,
        mock_rate_limiter: MagicMock
    ):
        """Test successful WhatsApp message receipt."""
        # Mock handlers
        with patch("src.api.webhooks.whatsapp.kafka_producer", mock_kafka_producer), \
             patch("src.api.webhooks.whatsapp.rate_limiter", mock_rate_limiter), \
             patch("src.api.webhooks.whatsapp.whatsapp_handler") as mock_handler:

            # Mock handler methods
            mock_handler.verify_webhook_signature = AsyncMock(return_value=True)
            mock_handler.process_inbound_message = AsyncMock(return_value=MagicMock(
                message_id="SM123456789",
                customer_id=None,
                metadata={"requires_escalation": False}
            ))

            # Send request
            response = await async_client.post(
                "/webhooks/whatsapp",
                data=whatsapp_webhook_payload,
                headers={"X-Twilio-Signature": "valid_signature"}
            )

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

            # Verify rate limiter was called
            mock_rate_limiter.check_rate_limit.assert_called_once()
            mock_rate_limiter.record_request.assert_called_once()

            # Verify Kafka producer was called
            mock_kafka_producer.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_message_creates_customer(
        self,
        async_client: AsyncClient,
        session,
        whatsapp_webhook_payload: dict[str, str],
        mock_kafka_producer: MagicMock,
        mock_rate_limiter: MagicMock
    ):
        """Test that new customer is created for unknown phone number."""
        with patch("src.api.webhooks.whatsapp.kafka_producer", mock_kafka_producer), \
             patch("src.api.webhooks.whatsapp.rate_limiter", mock_rate_limiter), \
             patch("src.api.webhooks.whatsapp.whatsapp_handler") as mock_handler:

            mock_handler.verify_webhook_signature = AsyncMock(return_value=True)
            mock_handler.process_inbound_message = AsyncMock(return_value=MagicMock(
                message_id="SM123456789",
                customer_id=None,
                metadata={"requires_escalation": False}
            ))

            response = await async_client.post(
                "/webhooks/whatsapp",
                data=whatsapp_webhook_payload,
                headers={"X-Twilio-Signature": "valid_signature"}
            )

            assert response.status_code == 200

            # Verify customer was created
            from sqlmodel import select
            result = await session.execute(
                select(Customer).where(Customer.phone == "+1234567890")
            )
            customer = result.scalars().first()
            assert customer is not None
            assert customer.name == "John Doe"

    @pytest.mark.asyncio
    async def test_receive_message_invalid_signature(
        self,
        async_client: AsyncClient,
        whatsapp_webhook_payload: MagicMock
    ):
        """Test rejection of invalid signature."""
        with patch("src.api.webhooks.whatsapp.whatsapp_handler") as mock_handler:
            mock_handler.verify_webhook_signature = AsyncMock(return_value=False)

            response = await async_client.post(
                "/webhooks/whatsapp",
                data=whatsapp_webhook_payload,
                headers={"X-Twilio-Signature": "invalid_signature"}
            )

            assert response.status_code == 403
            assert "Invalid signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_receive_message_rate_limit_exceeded(
        self,
        async_client: AsyncClient,
        whatsapp_webhook_payload: dict[str, str],
        mock_rate_limiter: MagicMock
    ):
        """Test rate limit enforcement."""
        # Mock rate limit exceeded
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=(False, 0))
        mock_rate_limiter.get_retry_after = AsyncMock(return_value=60)

        with patch("src.api.webhooks.whatsapp.rate_limiter", mock_rate_limiter), \
             patch("src.api.webhooks.whatsapp.whatsapp_handler") as mock_handler:

            mock_handler.verify_webhook_signature = AsyncMock(return_value=True)

            response = await async_client.post(
                "/webhooks/whatsapp",
                data=whatsapp_webhook_payload,
                headers={"X-Twilio-Signature": "valid_signature"}
            )

            assert response.status_code == 429
            assert "Too many requests" in response.json()["detail"]
            assert response.headers.get("Retry-After") == "60"

    @pytest.mark.asyncio
    async def test_receive_message_escalation_detected(
        self,
        async_client: AsyncClient,
        session,
        whatsapp_webhook_payload: dict[str, str],
        mock_kafka_producer: MagicMock,
        mock_rate_limiter: MagicMock
    ):
        """Test escalation detection creates ticket."""
        # Modify payload to include escalation keyword
        whatsapp_webhook_payload["Body"] = "I need to speak to a human agent"

        with patch("src.api.webhooks.whatsapp.kafka_producer", mock_kafka_producer), \
             patch("src.api.webhooks.whatsapp.rate_limiter", mock_rate_limiter), \
             patch("src.api.webhooks.whatsapp.whatsapp_handler") as mock_handler:

            mock_handler.verify_webhook_signature = AsyncMock(return_value=True)
            mock_handler.process_inbound_message = AsyncMock(return_value=MagicMock(
                message_id="SM123456789",
                customer_id=None,
                metadata={"requires_escalation": True}
            ))

            response = await async_client.post(
                "/webhooks/whatsapp",
                data=whatsapp_webhook_payload,
                headers={"X-Twilio-Signature": "valid_signature"}
            )

            assert response.status_code == 200

            # Verify ticket was created
            from sqlmodel import select
            from src.database.models import Ticket
            result = await session.execute(select(Ticket))
            ticket = result.scalars().first()
            assert ticket is not None
            assert ticket.category == "escalation"

    @pytest.mark.asyncio
    async def test_receive_message_missing_from_field(
        self,
        async_client: AsyncClient,
    ):
        """Test error handling for missing From field."""
        payload = {
            "MessageSid": "SM123456789",
            "Body": "Hello"
        }

        response = await async_client.post(
            "/webhooks/whatsapp",
            data=payload
        )

        assert response.status_code == 400
        assert "Missing From field" in response.json()["detail"]


class TestWhatsAppStatusWebhook:
    """Test WhatsApp status callback endpoint."""

    @pytest.mark.asyncio
    async def test_receive_status_update_success(
        self,
        async_client: AsyncClient,
        session,
        whatsapp_status_payload: dict[str, str]
    ):
        """Test successful status update."""
        # Create existing message
        customer = Customer(
            phone="+1234567890",
            name="Test Customer"
        )
        session.add(customer)
        await session.commit()

        conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.WHATSAPP,
            status=ConversationStatus.ACTIVE
        )
        session.add(conversation)
        await session.commit()

        message = Message(
            conversation_id=conversation.id,
            channel=Channel.WHATSAPP,
            direction=MessageDirection.OUTBOUND,
            role=MessageRole.AGENT,
            content="Test message",
            delivery_status=DeliveryStatus.SENT,
            metadata_={"message_sid": "SM123456789"}
        )
        session.add(message)
        await session.commit()

        with patch("src.api.webhooks.whatsapp.whatsapp_handler") as mock_handler:
            mock_handler.verify_webhook_signature = AsyncMock(return_value=True)

            response = await async_client.post(
                "/webhooks/whatsapp/status",
                data=whatsapp_status_payload,
                headers={"X-Twilio-Signature": "valid_signature"}
            )

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

            # Verify message status was updated
            await session.refresh(message)
            assert message.delivery_status == DeliveryStatus.DELIVERED
            assert message.metadata_["last_status"] == "delivered"

    @pytest.mark.asyncio
    async def test_receive_status_update_read(
        self,
        async_client: AsyncClient,
        session
    ):
        """Test read status update."""
        # Create existing message
        customer = Customer(phone="+1234567890")
        session.add(customer)
        await session.commit()

        conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.WHATSAPP,
            status=ConversationStatus.ACTIVE
        )
        session.add(conversation)
        await session.commit()

        message = Message(
            conversation_id=conversation.id,
            channel=Channel.WHATSAPP,
            direction=MessageDirection.OUTBOUND,
            role=MessageRole.AGENT,
            content="Test",
            delivery_status=DeliveryStatus.DELIVERED,
            metadata_={"message_sid": "SM123456789"}
        )
        session.add(message)
        await session.commit()

        payload = {
            "MessageSid": "SM123456789",
            "MessageStatus": "read"
        }

        with patch("src.api.webhooks.whatsapp.whatsapp_handler") as mock_handler:
            mock_handler.verify_webhook_signature = AsyncMock(return_value=True)

            response = await async_client.post(
                "/webhooks/whatsapp/status",
                data=payload,
                headers={"X-Twilio-Signature": "valid_signature"}
            )

            assert response.status_code == 200

            # Verify read timestamp was added
            await session.refresh(message)
            assert "read_at" in message.metadata_

    @pytest.mark.asyncio
    async def test_receive_status_update_failed(
        self,
        async_client: AsyncClient,
        session
    ):
        """Test failed status update with error details."""
        # Create existing message
        customer = Customer(phone="+1234567890")
        session.add(customer)
        await session.commit()

        conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.WHATSAPP,
            status=ConversationStatus.ACTIVE
        )
        session.add(conversation)
        await session.commit()

        message = Message(
            conversation_id=conversation.id,
            channel=Channel.WHATSAPP,
            direction=MessageDirection.OUTBOUND,
            role=MessageRole.AGENT,
            content="Test",
            delivery_status=DeliveryStatus.SENT,
            metadata_={"message_sid": "SM123456789"}
        )
        session.add(message)
        await session.commit()

        payload = {
            "MessageSid": "SM123456789",
            "MessageStatus": "failed",
            "ErrorCode": "30008",
            "ErrorMessage": "Unknown error"
        }

        with patch("src.api.webhooks.whatsapp.whatsapp_handler") as mock_handler:
            mock_handler.verify_webhook_signature = AsyncMock(return_value=True)

            response = await async_client.post(
                "/webhooks/whatsapp/status",
                data=payload,
                headers={"X-Twilio-Signature": "valid_signature"}
            )

            assert response.status_code == 200

            # Verify error details were stored
            await session.refresh(message)
            assert message.delivery_status == DeliveryStatus.FAILED
            assert message.metadata_["error_code"] == "30008"
            assert message.metadata_["error_message"] == "Unknown error"

    @pytest.mark.asyncio
    async def test_receive_status_update_message_not_found(
        self,
        async_client: AsyncClient,
    ):
        """Test status update for non-existent message."""
        payload = {
            "MessageSid": "SM_NONEXISTENT",
            "MessageStatus": "delivered"
        }

        with patch("src.api.webhooks.whatsapp.whatsapp_handler") as mock_handler:
            mock_handler.verify_webhook_signature = AsyncMock(return_value=True)

            response = await async_client.post(
                "/webhooks/whatsapp/status",
                data=payload,
                headers={"X-Twilio-Signature": "valid_signature"}
            )

            # Should still return 200 (acknowledge receipt)
            assert response.status_code == 200
