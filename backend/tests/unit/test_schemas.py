"""Unit tests for ChannelMessage schema validation."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.kafka.schemas import (
    ChannelMessage,
    Channel,
    MessageType,
    MessageDirection,
    AttachmentMetadata
)


class TestChannelMessageSchema:
    """Test suite for ChannelMessage Pydantic schema."""

    def test_create_minimal_message(self):
        """Test creating message with minimal required fields."""
        message = ChannelMessage(
            message_id="msg-123",
            channel=Channel.EMAIL,
            message_type=MessageType.INBOUND,
            direction=MessageDirection.CUSTOMER_TO_SUPPORT,
            customer_contact="test@example.com",
            body="Test message",
            timestamp=datetime.utcnow()
        )

        assert message.message_id == "msg-123"
        assert message.channel == Channel.EMAIL
        assert message.customer_contact == "test@example.com"
        assert message.body == "Test message"

    def test_create_full_message(self):
        """Test creating message with all fields."""
        timestamp = datetime.utcnow()
        received_at = datetime.utcnow()

        message = ChannelMessage(
            message_id="msg-123",
            channel=Channel.EMAIL,
            message_type=MessageType.INBOUND,
            direction=MessageDirection.CUSTOMER_TO_SUPPORT,
            customer_id="customer-456",
            customer_contact="test@example.com",
            customer_name="Test Customer",
            subject="Test Subject",
            body="Test message body",
            thread_id="thread-789",
            parent_message_id="parent-msg-101",
            attachments=[
                AttachmentMetadata(
                    filename="test.pdf",
                    content_type="application/pdf",
                    size_bytes=1024,
                    storage_path="/storage/test.pdf"
                )
            ],
            metadata={"source": "gmail"},
            timestamp=timestamp,
            received_at=received_at,
            delivery_status="sent"
        )

        assert message.customer_id == "customer-456"
        assert message.customer_name == "Test Customer"
        assert message.subject == "Test Subject"
        assert message.thread_id == "thread-789"
        assert len(message.attachments) == 1
        assert message.metadata == {"source": "gmail"}

    def test_missing_required_fields(self):
        """Test validation error when required fields missing."""
        with pytest.raises(ValidationError) as exc_info:
            ChannelMessage(
                message_id="msg-123",
                # Missing channel, message_type, direction, customer_contact, body, timestamp
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_channel_enum_validation(self):
        """Test channel enum validation."""
        message = ChannelMessage(
            message_id="msg-123",
            channel=Channel.WHATSAPP,
            message_type=MessageType.INBOUND,
            direction=MessageDirection.CUSTOMER_TO_SUPPORT,
            customer_contact="+1234567890",
            body="Test message",
            timestamp=datetime.utcnow()
        )

        assert message.channel == Channel.WHATSAPP

    def test_invalid_channel_value(self):
        """Test validation error for invalid channel."""
        with pytest.raises(ValidationError):
            ChannelMessage(
                message_id="msg-123",
                channel="invalid_channel",
                message_type=MessageType.INBOUND,
                direction=MessageDirection.CUSTOMER_TO_SUPPORT,
                customer_contact="test@example.com",
                body="Test message",
                timestamp=datetime.utcnow()
            )

    def test_message_type_enum(self):
        """Test message type enum values."""
        inbound = ChannelMessage(
            message_id="msg-1",
            channel=Channel.EMAIL,
            message_type=MessageType.INBOUND,
            direction=MessageDirection.CUSTOMER_TO_SUPPORT,
            customer_contact="test@example.com",
            body="Inbound message",
            timestamp=datetime.utcnow()
        )

        outbound = ChannelMessage(
            message_id="msg-2",
            channel=Channel.EMAIL,
            message_type=MessageType.OUTBOUND,
            direction=MessageDirection.SUPPORT_TO_CUSTOMER,
            customer_contact="test@example.com",
            body="Outbound message",
            timestamp=datetime.utcnow()
        )

        assert inbound.message_type == MessageType.INBOUND
        assert outbound.message_type == MessageType.OUTBOUND

    def test_optional_fields_default_none(self):
        """Test optional fields default to None."""
        message = ChannelMessage(
            message_id="msg-123",
            channel=Channel.EMAIL,
            message_type=MessageType.INBOUND,
            direction=MessageDirection.CUSTOMER_TO_SUPPORT,
            customer_contact="test@example.com",
            body="Test message",
            timestamp=datetime.utcnow()
        )

        assert message.customer_id is None
        assert message.customer_name is None
        assert message.subject is None
        assert message.thread_id is None
        assert message.parent_message_id is None
        assert message.received_at is None
        assert message.delivery_status is None

    def test_attachments_default_empty_list(self):
        """Test attachments default to empty list."""
        message = ChannelMessage(
            message_id="msg-123",
            channel=Channel.EMAIL,
            message_type=MessageType.INBOUND,
            direction=MessageDirection.CUSTOMER_TO_SUPPORT,
            customer_contact="test@example.com",
            body="Test message",
            timestamp=datetime.utcnow()
        )

        assert message.attachments == []

    def test_metadata_default_empty_dict(self):
        """Test metadata defaults to empty dict."""
        message = ChannelMessage(
            message_id="msg-123",
            channel=Channel.EMAIL,
            message_type=MessageType.INBOUND,
            direction=MessageDirection.CUSTOMER_TO_SUPPORT,
            customer_contact="test@example.com",
            body="Test message",
            timestamp=datetime.utcnow()
        )

        assert message.metadata == {}

    def test_attachment_metadata_validation(self):
        """Test attachment metadata validation."""
        attachment = AttachmentMetadata(
            filename="document.pdf",
            content_type="application/pdf",
            size_bytes=2048
        )

        assert attachment.filename == "document.pdf"
        assert attachment.content_type == "application/pdf"
        assert attachment.size_bytes == 2048
        assert attachment.storage_path is None

    def test_json_serialization(self):
        """Test message can be serialized to JSON."""
        message = ChannelMessage(
            message_id="msg-123",
            channel=Channel.EMAIL,
            message_type=MessageType.INBOUND,
            direction=MessageDirection.CUSTOMER_TO_SUPPORT,
            customer_contact="test@example.com",
            body="Test message",
            timestamp=datetime.utcnow()
        )

        json_data = message.model_dump(mode='json')

        assert isinstance(json_data, dict)
        assert json_data['message_id'] == "msg-123"
        assert json_data['channel'] == "email"

    def test_datetime_serialization(self):
        """Test datetime fields are properly serialized."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        message = ChannelMessage(
            message_id="msg-123",
            channel=Channel.EMAIL,
            message_type=MessageType.INBOUND,
            direction=MessageDirection.CUSTOMER_TO_SUPPORT,
            customer_contact="test@example.com",
            body="Test message",
            timestamp=timestamp
        )

        json_data = message.model_dump(mode='json')
        assert 'timestamp' in json_data
