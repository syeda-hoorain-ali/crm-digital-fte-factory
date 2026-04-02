"""Kafka consumer service that processes inbound messages and invokes the agent."""

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from aiokafka import AIOKafkaConsumer
from agents import Runner

from ..agent.customer_success_agent import customer_success_agent, CustomerSuccessContext
from ..agent.hooks import RunHooks
from ..agent.session import PostgresSession
from ..database.connection import get_session
from ..database.models import Channel, ConversationStatus
from ..database.queries import get_conversation
from ..kafka.schemas import ChannelMessage
from ..channels.gmail_handler import GmailHandler
from ..channels.whatsapp_handler import WhatsAppHandler

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
        try:
            async with get_session() as session:
                # Get conversation from database
                if not channel_message.customer_id:
                    logger.warning("No customer_id in message, skipping agent invocation")
                    return None

                # Find conversation by customer and thread
                # For now, we'll use the conversation_id from the message metadata if available
                # Otherwise, we need to query by customer_id and thread_id
                conversation_id_str = channel_message.metadata.get("conversation_id")

                if not conversation_id_str:
                    logger.warning("No conversation_id in message metadata, skipping agent invocation")
                    return None

                conversation_id = UUID(conversation_id_str)
                conversation = await get_conversation(session, conversation_id)

                if not conversation:
                    logger.warning(f"Conversation {conversation_id} not found")
                    return None

                # Initialize agent context
                ctx = CustomerSuccessContext(
                    db_session=session,
                    customer_id=channel_message.customer_id,
                    customer_email=channel_message.customer_contact if channel_message.channel == Channel.EMAIL else None,
                    customer_phone=channel_message.customer_contact if channel_message.channel == Channel.WHATSAPP else None,
                    channel=channel_message.channel.value,
                    conversation_id=str(conversation_id),
                )

                # Create agent session for conversation memory
                agent_session = PostgresSession(
                    session=session,
                    conversation_id=conversation_id,
                    channel=channel_message.channel,
                )

                # Create hooks for observability
                hooks = RunHooks(
                    session=session,
                    conversation_id=conversation_id,
                    correlation_id=channel_message.message_id,
                )

                # Execute agent
                logger.info(f"Invoking agent for message {channel_message.message_id}")
                result = await Runner.run(
                    customer_success_agent,
                    channel_message.body,
                    session=agent_session,
                    context=ctx,
                    hooks=hooks,
                )

                logger.info(
                    f"Agent completed for message {channel_message.message_id}",
                    extra={
                        "message_id": channel_message.message_id,
                        "response_length": len(result.final_output) if result.final_output else 0,
                        "escalated": ctx.escalation_triggered,
                    },
                )

                return result.final_output

        except Exception as e:
            logger.error(f"Failed to invoke agent: {e}", exc_info=True)
            return None

    async def _send_response(
        self, channel_message: ChannelMessage, response_text: str
    ) -> None:
        """Send agent response via the appropriate channel.

        Args:
            channel_message: Original inbound message
            response_text: Agent's response text
        """
        try:
            if channel_message.channel == Channel.EMAIL:
                await self._send_email_response(channel_message, response_text)
            elif channel_message.channel == Channel.WHATSAPP:
                await self._send_whatsapp_response(channel_message, response_text)
            else:
                logger.warning(f"No handler for channel: {channel_message.channel.value}")

        except Exception as e:
            logger.error(
                f"Failed to send response via {channel_message.channel.value}: {e}",
                exc_info=True,
            )

    async def _send_email_response(
        self, channel_message: ChannelMessage, response_text: str
    ) -> None:
        """Send email response via Gmail handler.

        Args:
            channel_message: Original inbound email message
            response_text: Agent's response text
        """
        if not self.gmail_handler:
            logger.warning("Gmail handler not configured, cannot send email response")
            return

        try:
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

        except Exception as e:
            logger.error(f"Failed to send email response: {e}", exc_info=True)
            raise

    async def _send_whatsapp_response(
        self, channel_message: ChannelMessage, response_text: str
    ) -> None:
        """Send WhatsApp response via Twilio handler.

        Args:
            channel_message: Original inbound WhatsApp message
            response_text: Agent's response text
        """
        if not self.whatsapp_handler:
            logger.warning("WhatsApp handler not configured, cannot send response")
            return

        try:
            # Send WhatsApp message
            result = await self.whatsapp_handler.send_outbound_message(
                customer_contact=channel_message.customer_contact,
                message_body=response_text,
            )

            logger.info(
                f"WhatsApp response sent to {channel_message.customer_contact}",
                extra={"message_sid": result.get("message_sid")},
            )

        except Exception as e:
            logger.error(f"Failed to send WhatsApp response: {e}", exc_info=True)
            raise
