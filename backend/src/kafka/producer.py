"""Kafka producer for message routing."""

import json
import logging
from typing import Optional
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from .schemas import ChannelMessage
from .topics import get_inbound_topic, KafkaTopic

logger = logging.getLogger(__name__)


class KafkaMessageProducer:
    """Kafka producer for routing channel messages."""

    def __init__(self, bootstrap_servers: str):
        """Initialize Kafka producer.

        Args:
            bootstrap_servers: Kafka bootstrap servers (e.g., "localhost:9092")
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        """Start Kafka producer."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            compression_type='gzip',
            acks='all',  # Wait for all replicas
        )
        await self.producer.start()
        logger.info("Kafka producer started")

    async def stop(self) -> None:
        """Stop Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def send_message(
        self,
        message: ChannelMessage,
        send_to_unified: bool = True
    ) -> bool:
        """Send message to Kafka topic.

        Args:
            message: Channel message to send
            send_to_unified: Also send to unified all.inbound topic

        Returns:
            True if successful, False otherwise
        """
        if not self.producer:
            logger.error("Kafka producer not started")
            return False

        try:
            # Get channel-specific topic
            channel_topic = get_inbound_topic(message.channel.value)

            # Serialize message
            message_dict = message.model_dump(mode='json')

            # Send to channel-specific topic
            await self.producer.send_and_wait(
                channel_topic,
                value=message_dict,
                key=message.customer_id.encode('utf-8') if message.customer_id else None
            )
            logger.info(
                f"Message {message.message_id} sent to {channel_topic}",
                extra={
                    "message_id": message.message_id,
                    "channel": message.channel.value,
                    "topic": channel_topic
                }
            )

            # Also send to unified topic for agent consumption
            if send_to_unified:
                await self.producer.send_and_wait(
                    KafkaTopic.ALL_INBOUND.value,
                    value=message_dict,
                    key=message.customer_id.encode('utf-8') if message.customer_id else None
                )
                logger.info(
                    f"Message {message.message_id} sent to unified topic",
                    extra={
                        "message_id": message.message_id,
                        "topic": KafkaTopic.ALL_INBOUND.value
                    }
                )

            return True

        except KafkaError as e:
            logger.error(
                f"Failed to send message to Kafka: {e}",
                extra={
                    "message_id": message.message_id,
                    "channel": message.channel.value,
                    "error": str(e)
                },
                exc_info=True
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending message: {e}",
                extra={"message_id": message.message_id},
                exc_info=True
            )
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
