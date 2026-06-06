"""Kafka consumer service that processes inbound messages and invokes the agent."""

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from aiokafka import AIOKafkaConsumer

from ..database.connection import get_session
from ..database.models import Channel, MessageRole
from ..kafka.schemas import ChannelMessage
from ..channels.gmail_handler import GmailHandler
from ..channels.whatsapp_handler import WhatsAppHandler
from .agent_invocation_service import AgentInvocationService

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    """Service that consumes messages from Kafka and invokes the agent."""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str = "customer-success-agent-group",
        gmail_handler: GmailHandler | None = None,
        whatsapp_handler: Any | None = None,
    ):
        """Initialize Kafka consumer service.

        Args:
            bootstrap_servers: Kafka broker addresses
            group_id: Consumer group ID
            gmail_handler: Gmail handler for sending email responses
            whatsapp_handler: WhatsApp handler for sending WhatsApp responses
        """
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.gmail_handler = gmail_handler
        self.whatsapp_handler = whatsapp_handler
        self.consumer: AIOKafkaConsumer | None = None
        self.running = False
        self._task: asyncio.Task | None = None
        self.agent_service = AgentInvocationService()

    async def start(self) -> None:
        """Start the Kafka consumer service."""
        if self.running:
            logger.warning("Kafka consumer service already running")
            return

        try:
            # Initialize consumer
            self.consumer = AIOKafkaConsumer(
                "customer-intake.email.inbound",
                "customer-intake.whatsapp.inbound",
                "customer-intake.webform.inbound",
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset="latest",  # Start from latest messages
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )

            await self.consumer.start()
            self.running = True
            logger.info(f"Kafka consumer started (group: {self.group_id})")

            # Start consuming in background
            self._task = asyncio.create_task(self._consume_loop())

        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop the Kafka consumer service."""
        if not self.running:
            return

        self.running = False

        # Cancel consume task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Stop consumer
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

    async def _consume_loop(self) -> None:
        """Main consume loop that processes messages."""
        logger.info("Starting Kafka consume loop...")

        if not self.consumer:
            logger.warning("Kafka consumer service not running")
            return

        try:
            async for message in self.consumer:
                try:
                    await self._process_message(message)
                except Exception as e:
                    logger.error(
                        f"Error processing message from {message.topic}: {e}",
                        extra={
                            "topic": message.topic,
                            "partition": message.partition,
                            "offset": message.offset,
                        },
                        exc_info=True,
                    )
                    # Continue processing other messages even if one fails

        except asyncio.CancelledError:
            logger.info("Kafka consume loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Fatal error in consume loop: {e}", exc_info=True)
            raise

    async def _process_message(self, message: Any) -> None:
        """Process a single Kafka message.

        Args:
            message: Kafka message with ChannelMessage payload
        """
        logger.info(
            f"Processing message from {message.topic}",
            extra={
                "topic": message.topic,
                "partition": message.partition,
                "offset": message.offset,
            },
        )

        try:
            # Parse message payload
            channel_message = ChannelMessage(**message.value)

            logger.info(
                f"Parsed ChannelMessage: {channel_message.message_id}",
                extra={
                    "message_id": channel_message.message_id,
                    "channel": channel_message.channel.value,
                    "customer_id": channel_message.customer_id,
                    "customer_contact": channel_message.customer_contact,
                },
            )

            # Invoke agent to process message
            agent_response = await self._invoke_agent(channel_message)

            # Send response via appropriate channel
            if agent_response:
                await self._send_response(channel_message, agent_response)

        except Exception as e:
            logger.error(f"Failed to process message: {e}", exc_info=True)
            raise

    async def _invoke_agent(self, channel_message: ChannelMessage) -> str | None:
        """Invoke the customer success agent to process the message.

        Args:
            channel_message: Parsed channel message

        Returns:
            Agent response text, or None if no response needed
        """
        async with get_session() as session:
            return await self.agent_service.invoke_agent(session, channel_message)

    async def _send_response(
        self, channel_message: ChannelMessage, response_text: str
    ) -> None:
        """Send agent response via the appropriate channel.

        Args:
            channel_message: Original inbound message
            response_text: Agent's response text
        """
        delivery_status = "pending"  # Default to pending, update to delivered on success

        try:
            if channel_message.channel == Channel.EMAIL:
                await self._send_email_response(channel_message, response_text)
            elif channel_message.channel == Channel.WHATSAPP:
                await self._send_whatsapp_response(channel_message, response_text)
            elif channel_message.channel == Channel.WEB_FORM:
                # Web form submissions should receive email responses
                await self._send_email_response(channel_message, response_text)
            else:
                logger.warning(f"No handler for channel: {channel_message.channel.value}")
                # Still mark as failed since no handler exists
                raise ValueError(f"No handler for channel: {channel_message.channel.value}")

            # If we reach here, sending was successful
            delivery_status = "delivered"

        except Exception as e:
            logger.error(
                f"Failed to send response via {channel_message.channel.value}: {e}",
                exc_info=True,
            )
            delivery_status = "failed"

        finally:
            # Always update agent message delivery status (delivered or failed)
            try:
                async with get_session() as session:
                    conversation_id_str = channel_message.metadata.get("conversation_id")
                    if conversation_id_str:
                        from src.database.queries.message import get_latest_message, update_message

                        conversation_id = UUID(conversation_id_str)
                        agent_message = await get_latest_message(session, conversation_id)

                        if agent_message and agent_message.role == MessageRole.AGENT:
                            await update_message(
                                session,
                                agent_message.id,
                                delivery_status=delivery_status
                            )
                            await session.commit()
                            logger.info(f"Updated agent message delivery status to {delivery_status}")
            except Exception as update_error:
                logger.error(f"Failed to update agent message delivery status: {update_error}")

    async def _send_email_response(
        self, channel_message: ChannelMessage, response_text: str
    ) -> None:
        """Send email response via Gmail handler.

        Args:
            channel_message: Original inbound email message
            response_text: Agent's response text
        """
        if not self.gmail_handler:
            logger.error("Gmail handler not configured, cannot send email response")
            raise RuntimeError("Gmail handler not configured")

        # Extract threading information
        thread_id = channel_message.thread_id
        subject = channel_message.subject or "Re: Support Request"

        # Send reply
        result = await self.gmail_handler.send_outbound_message(
            customer_contact=channel_message.customer_contact,
            message_body=response_text,
            subject=subject,
            thread_id=thread_id,
        )

        logger.info(
            f"Email response sent to {channel_message.customer_contact}",
            extra={
                "message_id": result.get("message_id"),
                "thread_id": result.get("thread_id"),
            },
        )

    async def _send_whatsapp_response(
        self, channel_message: ChannelMessage, response_text: str
    ) -> None:
        """Send WhatsApp response via Twilio handler.

        Args:
            channel_message: Original inbound WhatsApp message
            response_text: Agent's response text
        """
        if not self.whatsapp_handler:
            logger.error("WhatsApp handler not configured, cannot send response")
            raise RuntimeError("WhatsApp handler not configured")

        # Send WhatsApp message
        result = await self.whatsapp_handler.send_outbound_message(
            customer_contact=channel_message.customer_contact,
            message_body=response_text,
        )

        logger.info(
            f"WhatsApp response sent to {channel_message.customer_contact}",
            extra={"message_sid": result.get("message_sid")},
        )
