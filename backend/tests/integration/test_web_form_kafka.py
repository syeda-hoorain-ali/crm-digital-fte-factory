"""Integration tests for web form Kafka message routing."""

import pytest
import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.channels.web_form_handler import WebFormHandler
from src.kafka.producer import KafkaMessageProducer
from src.kafka.schemas import ChannelMessage, Channel, MessageType, MessageDirection
from src.kafka.topics import KafkaTopic, get_inbound_topic


@pytest.mark.integration
@pytest.mark.kafka
class TestWebFormKafkaRouting:
    """Integration tests for Kafka message routing from web form (T049)."""

    @pytest.mark.asyncio
    async def test_web_form_handler_creates_channel_message(self):
        """Test WebFormHandler creates valid ChannelMessage."""
        handler = WebFormHandler()

        payload = {
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Test Subject",
            "category": "technical",
            "priority": "high",
            "message": "This is a test message",
            "user_agent": "Mozilla/5.0",
            "ip_address": "192.168.1.1"
        }

        channel_message = await handler.process_inbound_message(payload)

        # Verify ChannelMessage structure
        assert isinstance(channel_message, ChannelMessage)
        assert channel_message.channel == Channel.WEBFORM
        assert channel_message.message_type == MessageType.INBOUND
        assert channel_message.direction == MessageDirection.CUSTOMER_TO_SUPPORT
        assert channel_message.customer_contact == payload["email"]
        assert channel_message.customer_name == payload["name"]
        assert channel_message.subject == payload["subject"]
        assert channel_message.body == payload["message"]
        assert channel_message.message_id.startswith("webform-")

        # Verify metadata
        assert channel_message.metadata["category"] == payload["category"]
        assert channel_message.metadata["priority"] == payload["priority"]
        assert channel_message.metadata["source"] == "web_form"
        assert channel_message.metadata["user_agent"] == payload["user_agent"]
        assert channel_message.metadata["ip_address"] == payload["ip_address"]

    @pytest.mark.asyncio
    async def test_web_form_handler_validates_required_fields(self):
        """Test WebFormHandler validates required fields."""
        handler = WebFormHandler()

        # Missing required fields
        invalid_payloads = [
            {"email": "test@example.com", "subject": "Test", "message": "Test"},  # Missing name
            {"name": "Test", "subject": "Test", "message": "Test"},  # Missing email
            {"name": "Test", "email": "test@example.com", "message": "Test"},  # Missing subject
            {"name": "Test", "email": "test@example.com", "subject": "Test"},  # Missing message
        ]

        for payload in invalid_payloads:
            with pytest.raises(ValueError, match="Missing required fields"):
                await handler.process_inbound_message(payload)

    @pytest.mark.asyncio
    async def test_channel_message_serialization(self):
        """Test ChannelMessage can be serialized to JSON."""
        handler = WebFormHandler()

        payload = {
            "name": "Serialization Test",
            "email": "serialize@example.com",
            "subject": "Serialization Test",
            "category": "general",
            "priority": "medium",
            "message": "Testing JSON serialization"
        }

        channel_message = await handler.process_inbound_message(payload)

        # Serialize to dict
        message_dict = channel_message.model_dump(mode='json')

        # Verify serialization
        assert isinstance(message_dict, dict)
        assert message_dict["channel"] == "webform"
        assert message_dict["message_type"] == "inbound"
        assert message_dict["direction"] == "customer_to_support"
        assert message_dict["customer_contact"] == payload["email"]
        assert message_dict["body"] == payload["message"]

        # Verify can be JSON encoded
        json_str = json.dumps(message_dict)
        assert isinstance(json_str, str)

        # Verify can be decoded back
        decoded = json.loads(json_str)
        assert decoded["customer_contact"] == payload["email"]

    @pytest.mark.asyncio
    async def test_kafka_producer_sends_to_correct_topic(self):
        """Test Kafka producer sends messages to correct topic."""
        # Mock Kafka producer
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()

        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = mock_producer

        # Create test message
        handler = WebFormHandler()
        payload = {
            "name": "Topic Test",
            "email": "topic@example.com",
            "subject": "Topic Test",
            "category": "general",
            "priority": "medium",
            "message": "Testing topic routing"
        }

        channel_message = await handler.process_inbound_message(payload)
        channel_message.customer_id = str(uuid.uuid4())

        # Send message
        success = await producer.send_message(channel_message)

        assert success is True

        # Verify send_and_wait was called twice (channel-specific + unified)
        assert mock_producer.send_and_wait.call_count == 2

        # Verify first call is to channel-specific topic
        first_call = mock_producer.send_and_wait.call_args_list[0]
        assert first_call[0][0] == KafkaTopic.WEBFORM_INBOUND

        # Verify second call is to unified topic
        second_call = mock_producer.send_and_wait.call_args_list[1]
        assert second_call[0][0] == KafkaTopic.ALL_INBOUND

    @pytest.mark.asyncio
    async def test_kafka_producer_uses_customer_id_as_key(self):
        """Test Kafka producer uses customer_id as message key for partitioning."""
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()

        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = mock_producer

        # Create test message with customer_id
        handler = WebFormHandler()
        payload = {
            "name": "Key Test",
            "email": "key@example.com",
            "subject": "Key Test",
            "category": "general",
            "priority": "medium",
            "message": "Testing message key"
        }

        channel_message = await handler.process_inbound_message(payload)
        customer_id = str(uuid.uuid4())
        channel_message.customer_id = customer_id

        # Send message
        await producer.send_message(channel_message)

        # Verify key parameter is customer_id encoded
        first_call = mock_producer.send_and_wait.call_args_list[0]
        assert first_call[1]["key"] == customer_id.encode('utf-8')

    @pytest.mark.asyncio
    async def test_kafka_producer_handles_missing_customer_id(self):
        """Test Kafka producer handles messages without customer_id."""
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()

        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = mock_producer

        # Create test message without customer_id
        handler = WebFormHandler()
        payload = {
            "name": "No ID Test",
            "email": "noid@example.com",
            "subject": "No ID Test",
            "category": "general",
            "priority": "medium",
            "message": "Testing without customer ID"
        }

        channel_message = await handler.process_inbound_message(payload)
        # Don't set customer_id

        # Send message
        success = await producer.send_message(channel_message)

        assert success is True

        # Verify key is None when customer_id is not set
        first_call = mock_producer.send_and_wait.call_args_list[0]
        assert first_call[1]["key"] is None

    @pytest.mark.asyncio
    async def test_kafka_producer_sends_serialized_message(self):
        """Test Kafka producer sends properly serialized message."""
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()

        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = mock_producer

        # Create test message
        handler = WebFormHandler()
        payload = {
            "name": "Serialization Test",
            "email": "serial@example.com",
            "subject": "Serialization Test",
            "category": "technical",
            "priority": "high",
            "message": "Testing message serialization"
        }

        channel_message = await handler.process_inbound_message(payload)
        channel_message.customer_id = str(uuid.uuid4())

        # Send message
        await producer.send_message(channel_message)

        # Verify value parameter contains serialized message
        first_call = mock_producer.send_and_wait.call_args_list[0]
        message_value = first_call[1]["value"]

        assert isinstance(message_value, dict)
        assert message_value["channel"] == "webform"
        assert message_value["customer_contact"] == payload["email"]
        assert message_value["body"] == payload["message"]
        assert message_value["metadata"]["category"] == payload["category"]
        assert message_value["metadata"]["priority"] == payload["priority"]

    @pytest.mark.asyncio
    async def test_kafka_producer_handles_send_failure(self):
        """Test Kafka producer handles send failures gracefully."""
        from aiokafka.errors import KafkaError

        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock(side_effect=KafkaError("Connection failed"))

        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = mock_producer

        # Create test message
        handler = WebFormHandler()
        payload = {
            "name": "Failure Test",
            "email": "failure@example.com",
            "subject": "Failure Test",
            "category": "general",
            "priority": "medium",
            "message": "Testing failure handling"
        }

        channel_message = await handler.process_inbound_message(payload)

        # Send message (should handle error)
        success = await producer.send_message(channel_message)

        assert success is False

    @pytest.mark.asyncio
    async def test_kafka_producer_not_started_returns_false(self):
        """Test Kafka producer returns False when not started."""
        producer = KafkaMessageProducer("localhost:9092")
        # Don't start producer

        # Create test message
        handler = WebFormHandler()
        payload = {
            "name": "Not Started Test",
            "email": "notstarted@example.com",
            "subject": "Not Started Test",
            "category": "general",
            "priority": "medium",
            "message": "Testing not started scenario"
        }

        channel_message = await handler.process_inbound_message(payload)

        # Send message (should fail gracefully)
        success = await producer.send_message(channel_message)

        assert success is False

    @pytest.mark.asyncio
    async def test_get_inbound_topic_returns_correct_topic(self):
        """Test get_inbound_topic returns correct topic for webform."""
        # Test with different channel name variations
        assert get_inbound_topic("webform") == KafkaTopic.WEBFORM_INBOUND
        assert get_inbound_topic("web_form") == KafkaTopic.WEBFORM_INBOUND
        assert get_inbound_topic("WEBFORM") == KafkaTopic.WEBFORM_INBOUND

    @pytest.mark.asyncio
    async def test_kafka_producer_send_to_unified_only(self):
        """Test Kafka producer can skip channel-specific topic."""
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()

        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = mock_producer

        # Create test message
        handler = WebFormHandler()
        payload = {
            "name": "Unified Only Test",
            "email": "unified@example.com",
            "subject": "Unified Only Test",
            "category": "general",
            "priority": "medium",
            "message": "Testing unified topic only"
        }

        channel_message = await handler.process_inbound_message(payload)

        # Send message with send_to_unified=False
        success = await producer.send_message(channel_message, send_to_unified=False)

        assert success is True

        # Verify send_and_wait was called only once (channel-specific only)
        assert mock_producer.send_and_wait.call_count == 1

        # Verify call is to channel-specific topic
        first_call = mock_producer.send_and_wait.call_args_list[0]
        assert first_call[0][0] == KafkaTopic.WEBFORM_INBOUND

    @pytest.mark.asyncio
    async def test_channel_message_timestamp_serialization(self):
        """Test ChannelMessage timestamp is properly serialized."""
        handler = WebFormHandler()

        payload = {
            "name": "Timestamp Test",
            "email": "timestamp@example.com",
            "subject": "Timestamp Test",
            "category": "general",
            "priority": "medium",
            "message": "Testing timestamp serialization"
        }

        channel_message = await handler.process_inbound_message(payload)

        # Serialize to dict
        message_dict = channel_message.model_dump(mode='json')

        # Verify timestamp is ISO format string
        assert "timestamp" in message_dict
        assert isinstance(message_dict["timestamp"], str)

        # Verify can be parsed back to datetime
        parsed_timestamp = datetime.fromisoformat(message_dict["timestamp"].replace('Z', '+00:00'))
        assert isinstance(parsed_timestamp, datetime)

    @pytest.mark.asyncio
    async def test_channel_message_attachments_empty_by_default(self):
        """Test ChannelMessage has empty attachments list by default."""
        handler = WebFormHandler()

        payload = {
            "name": "Attachments Test",
            "email": "attachments@example.com",
            "subject": "Attachments Test",
            "category": "general",
            "priority": "medium",
            "message": "Testing attachments field"
        }

        channel_message = await handler.process_inbound_message(payload)

        assert channel_message.attachments == []

    @pytest.mark.asyncio
    async def test_web_form_handler_generates_unique_message_ids(self):
        """Test WebFormHandler generates unique message IDs."""
        handler = WebFormHandler()

        payload = {
            "name": "Unique ID Test",
            "email": "uniqueid@example.com",
            "subject": "Unique ID Test",
            "category": "general",
            "priority": "medium",
            "message": "Testing unique message IDs"
        }

        # Generate multiple messages
        message_ids = set()
        for _ in range(10):
            channel_message = await handler.process_inbound_message(payload)
            message_ids.add(channel_message.message_id)

        # Verify all IDs are unique
        assert len(message_ids) == 10

        # Verify all IDs start with "webform-"
        for message_id in message_ids:
            assert message_id.startswith("webform-")
