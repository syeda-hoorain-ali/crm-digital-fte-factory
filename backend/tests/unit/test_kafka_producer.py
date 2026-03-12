"""Unit tests for Kafka producer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from src.kafka.producer import KafkaMessageProducer
from src.kafka.schemas import ChannelMessage, Channel, MessageType, MessageDirection
from src.kafka.topics import KafkaTopic
from datetime import datetime


@pytest.fixture
def sample_channel_message():
    """Create sample channel message for testing."""
    return ChannelMessage(
        message_id="msg-123",
        channel=Channel.EMAIL,
        message_type=MessageType.INBOUND,
        direction=MessageDirection.CUSTOMER_TO_SUPPORT,
        customer_id="customer-123",
        customer_contact="test@example.com",
        customer_name="Test Customer",
        subject="Test Subject",
        body="Test message body",
        timestamp=datetime.utcnow()
    )


class TestKafkaMessageProducer:
    """Test suite for Kafka message producer."""

    @pytest.mark.asyncio
    async def test_start_producer(self):
        """Test starting Kafka producer."""
        producer = KafkaMessageProducer("localhost:9092")

        with patch.object(AIOKafkaProducer, 'start', new_callable=AsyncMock) as mock_start:
            await producer.start()

            assert producer.producer is not None
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_producer(self):
        """Test stopping Kafka producer."""
        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = AsyncMock(spec=AIOKafkaProducer)

        await producer.stop()

        producer.producer.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_success(self, sample_channel_message):
        """Test sending message successfully."""
        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = AsyncMock(spec=AIOKafkaProducer)
        producer.producer.send_and_wait = AsyncMock()

        result = await producer.send_message(sample_channel_message)

        assert result is True
        # Should send to both channel-specific and unified topics
        assert producer.producer.send_and_wait.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_channel_specific_only(self, sample_channel_message):
        """Test sending message to channel-specific topic only."""
        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = AsyncMock(spec=AIOKafkaProducer)
        producer.producer.send_and_wait = AsyncMock()

        result = await producer.send_message(sample_channel_message, send_to_unified=False)

        assert result is True
        # Should send to channel-specific topic only
        assert producer.producer.send_and_wait.call_count == 1

    @pytest.mark.asyncio
    async def test_send_message_producer_not_started(self, sample_channel_message):
        """Test sending message when producer not started."""
        producer = KafkaMessageProducer("localhost:9092")

        result = await producer.send_message(sample_channel_message)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_kafka_error(self, sample_channel_message):
        """Test sending message with Kafka error."""
        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = AsyncMock(spec=AIOKafkaProducer)
        producer.producer.send_and_wait = AsyncMock(side_effect=KafkaError("Connection failed"))

        result = await producer.send_message(sample_channel_message)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_with_customer_id_key(self, sample_channel_message):
        """Test message is sent with customer_id as key."""
        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = AsyncMock(spec=AIOKafkaProducer)
        producer.producer.send_and_wait = AsyncMock()

        await producer.send_message(sample_channel_message)

        # Verify key is customer_id encoded
        call_args = producer.producer.send_and_wait.call_args_list[0]
        assert call_args[1]['key'] == b'customer-123'

    @pytest.mark.asyncio
    async def test_send_message_without_customer_id(self):
        """Test sending message without customer_id."""
        message = ChannelMessage(
            message_id="msg-123",
            channel=Channel.EMAIL,
            message_type=MessageType.INBOUND,
            direction=MessageDirection.CUSTOMER_TO_SUPPORT,
            customer_id=None,
            customer_contact="test@example.com",
            body="Test body",
            timestamp=datetime.utcnow()
        )

        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = AsyncMock(spec=AIOKafkaProducer)
        producer.producer.send_and_wait = AsyncMock()

        await producer.send_message(message)

        # Verify key is None when no customer_id
        call_args = producer.producer.send_and_wait.call_args_list[0]
        assert call_args[1]['key'] is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test producer as async context manager."""
        producer = KafkaMessageProducer("localhost:9092")

        with patch.object(producer, 'start', new_callable=AsyncMock) as mock_start, \
             patch.object(producer, 'stop', new_callable=AsyncMock) as mock_stop:

            async with producer:
                pass

            mock_start.assert_called_once()
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_serialization(self, sample_channel_message):
        """Test message is properly serialized."""
        producer = KafkaMessageProducer("localhost:9092")
        producer.producer = AsyncMock(spec=AIOKafkaProducer)
        producer.producer.send_and_wait = AsyncMock()

        await producer.send_message(sample_channel_message)

        # Verify message dict is passed
        call_args = producer.producer.send_and_wait.call_args_list[0]
        message_value = call_args[1]['value']
        assert isinstance(message_value, dict)
        assert message_value['message_id'] == 'msg-123'
        assert message_value['channel'] == 'email'
