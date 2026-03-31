"""Base channel handler interface."""

from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime, timezone

from src.kafka.schemas import ChannelMessage, Channel, MessageType, MessageDirection


class BaseChannelHandler(ABC):
    """Base interface for channel-specific message handlers."""

    def __init__(self, channel: Channel):
        """Initialize channel handler.

        Args:
            channel: Channel type this handler processes
        """
        self.channel = channel

    @abstractmethod
    async def process_inbound_message(self, payload: dict[str, Any]) -> ChannelMessage:
        """Process inbound message from channel webhook.

        Args:
            payload: Raw webhook payload

        Returns:
            Unified ChannelMessage

        Raises:
            ValueError: If payload is invalid
        """
        pass

    @abstractmethod
    async def send_outbound_message(
        self,
        customer_contact: str,
        message_body: str,
        subject: str | None = None,
        thread_id: str | None = None
    ) -> dict[str, Any]:
        """Send outbound message through channel.

        Args:
            customer_contact: Customer email or phone
            message_body: Message content
            subject: Optional subject (for email)
            thread_id: Optional thread ID for replies

        Returns:
            Channel-specific response metadata

        Raises:
            Exception: If send fails
        """
        pass

    @abstractmethod
    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        """Verify webhook signature.

        Args:
            payload: Raw request body
            signature: Signature from request header

        Returns:
            True if signature is valid
        """
        pass

    def create_channel_message(
        self,
        message_id: str,
        customer_contact: str,
        body: str,
        customer_id: str | None = None,
        customer_name: str | None = None,
        subject: str | None = None,
        thread_id: str | None = None,
        parent_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None
    ) -> ChannelMessage:
        """Create unified ChannelMessage from channel-specific data.

        Args:
            message_id: Unique message identifier
            customer_contact: Email or phone number
            body: Message content
            customer_id: Optional customer UUID
            customer_name: Optional customer name
            subject: Optional subject line
            thread_id: Optional thread identifier
            parent_message_id: Optional parent message ID
            metadata: Optional channel-specific metadata
            timestamp: Optional message timestamp

        Returns:
            Unified ChannelMessage
        """
        return ChannelMessage(
            message_id=message_id,
            channel=self.channel,
            message_type=MessageType.INBOUND,
            direction=MessageDirection.CUSTOMER_TO_SUPPORT,
            customer_id=customer_id,
            customer_contact=customer_contact,
            customer_name=customer_name,
            subject=subject,
            body=body,
            thread_id=thread_id,
            parent_message_id=parent_message_id,
            attachments=[],
            metadata=metadata or {},
            timestamp=timestamp or datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            delivery_status=None
        )
