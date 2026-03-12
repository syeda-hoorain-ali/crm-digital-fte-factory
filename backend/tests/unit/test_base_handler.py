"""Unit tests for base channel handler."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from src.channels.base import BaseChannelHandler
from src.kafka.schemas import Channel, MessageType, MessageDirection


class ConcreteChannelHandler(BaseChannelHandler):
    """Concrete implementation for testing."""

    async def process_inbound_message(self, payload):
        return self.create_channel_message(
            message_id="msg-123",
            customer_contact="test@example.com",
            body="Test message"
        )

    async def send_outbound_message(self, customer_contact, message_body, subject=None, thread_id=None):
        return {"status": "sent"}

    async def verify_webhook_signature(self, payload, signature):
        return True


class TestBaseChannelHandler:
    """Test suite for base channel handler."""

    def test_handler_initialization(self):
        """Test handler initialization with channel."""
        handler = ConcreteChannelHandler(Channel.EMAIL)

        assert handler.channel == Channel.EMAIL

    def test_create_channel_message_minimal(self):
        """Test creating channel message with minimal fields."""
        handler = ConcreteChannelHandler(Channel.EMAIL)

        message = handler.create_channel_message(
            message_id="msg-123",
            customer_contact="test@example.com",
            body="Test message body"
        )

        assert message.message_id == "msg-123"
        assert message.channel == Channel.EMAIL
        assert message.message_type == MessageType.INBOUND
        assert message.direction == MessageDirection.CUSTOMER_TO_SUPPORT
        assert message.customer_contact == "test@example.com"
        assert message.body == "Test message body"
        assert message.customer_id is None
        assert message.customer_name is None
        assert message.subject is None

    def test_create_channel_message_full(self):
        """Test creating channel message with all fields."""
        handler = ConcreteChannelHandler(Channel.EMAIL)
        timestamp = datetime.utcnow()

        message = handler.create_channel_message(
            message_id="msg-123",
            customer_contact="test@example.com",
            body="Test message body",
            customer_id="customer-456",
            customer_name="Test Customer",
            subject="Test Subject",
            thread_id="thread-789",
            parent_message_id="parent-msg-101",
            metadata={"source": "gmail"},
            timestamp=timestamp
        )

        assert message.message_id == "msg-123"
        assert message.customer_id == "customer-456"
        assert message.customer_name == "Test Customer"
        assert message.subject == "Test Subject"
        assert message.thread_id == "thread-789"
        assert message.parent_message_id == "parent-msg-101"
        assert message.metadata == {"source": "gmail"}
        assert message.timestamp == timestamp

    def test_create_channel_message_default_timestamp(self):
        """Test channel message gets default timestamp."""
        handler = ConcreteChannelHandler(Channel.EMAIL)

        message = handler.create_channel_message(
            message_id="msg-123",
            customer_contact="test@example.com",
            body="Test message"
        )

        assert message.timestamp is not None
        assert message.received_at is not None

    def test_create_channel_message_different_channels(self):
        """Test creating messages for different channels."""
        email_handler = ConcreteChannelHandler(Channel.EMAIL)
        whatsapp_handler = ConcreteChannelHandler(Channel.WHATSAPP)

        email_message = email_handler.create_channel_message(
            message_id="msg-1",
            customer_contact="test@example.com",
            body="Email message"
        )

        whatsapp_message = whatsapp_handler.create_channel_message(
            message_id="msg-2",
            customer_contact="+1234567890",
            body="WhatsApp message"
        )

        assert email_message.channel == Channel.EMAIL
        assert whatsapp_message.channel == Channel.WHATSAPP

    @pytest.mark.asyncio
    async def test_process_inbound_message_abstract(self):
        """Test process_inbound_message is implemented."""
        handler = ConcreteChannelHandler(Channel.EMAIL)

        message = await handler.process_inbound_message({"test": "payload"})

        assert message is not None
        assert message.message_id == "msg-123"

    @pytest.mark.asyncio
    async def test_send_outbound_message_abstract(self):
        """Test send_outbound_message is implemented."""
        handler = ConcreteChannelHandler(Channel.EMAIL)

        result = await handler.send_outbound_message(
            customer_contact="test@example.com",
            message_body="Test message"
        )

        assert result == {"status": "sent"}

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_abstract(self):
        """Test verify_webhook_signature is implemented."""
        handler = ConcreteChannelHandler(Channel.EMAIL)

        is_valid = await handler.verify_webhook_signature(
            payload=b"test payload",
            signature="test_signature"
        )

        assert is_valid is True

    def test_create_channel_message_empty_metadata(self):
        """Test channel message with empty metadata."""
        handler = ConcreteChannelHandler(Channel.EMAIL)

        message = handler.create_channel_message(
            message_id="msg-123",
            customer_contact="test@example.com",
            body="Test message",
            metadata={}
        )

        assert message.metadata == {}

    def test_create_channel_message_attachments_default(self):
        """Test channel message has empty attachments by default."""
        handler = ConcreteChannelHandler(Channel.EMAIL)

        message = handler.create_channel_message(
            message_id="msg-123",
            customer_contact="test@example.com",
            body="Test message"
        )

        assert message.attachments == []

    def test_create_channel_message_delivery_status_none(self):
        """Test channel message has None delivery_status for inbound."""
        handler = ConcreteChannelHandler(Channel.EMAIL)

        message = handler.create_channel_message(
            message_id="msg-123",
            customer_contact="test@example.com",
            body="Test message"
        )

        assert message.delivery_status is None
