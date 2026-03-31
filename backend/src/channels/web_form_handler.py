"""Web form channel handler."""

import uuid
from datetime import datetime, timezone
from typing import Any

from src.kafka.schemas import Channel
from .base import BaseChannelHandler


class WebFormHandler(BaseChannelHandler):
    """Handler for web form support submissions."""

    def __init__(self):
        """Initialize web form handler."""
        super().__init__(Channel.WEBFORM)

    async def process_inbound_message(self, payload: dict[str, Any]):
        """Process web form submission.

        Args:
            payload: Form submission data with name, email, subject, category, priority, message

        Returns:
            Unified ChannelMessage

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        required_fields = ["name", "email", "subject", "message"]
        missing_fields = [field for field in required_fields if not payload.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Generate unique message ID
        message_id = f"webform-{uuid.uuid4()}"

        # Create channel message
        return self.create_channel_message(
            message_id=message_id,
            customer_contact=payload["email"],
            body=payload["message"],
            customer_name=payload.get("name"),
            subject=payload.get("subject"),
            metadata={
                "category": payload.get("category", "general"),
                "priority": payload.get("priority", "medium"),
                "source": "web_form",
                "user_agent": payload.get("user_agent"),
                "ip_address": payload.get("ip_address"),
            },
            timestamp=datetime.now(timezone.utc)
        )

    async def send_outbound_message(
        self,
        customer_contact: str,
        message_body: str,
        subject: str | None = None,
        thread_id: str | None = None
    ) -> dict[str, Any]:
        """Send outbound message (not applicable for web form).

        Web form is inbound-only. Responses are sent via email.

        Args:
            customer_contact: Customer email
            message_body: Message content
            subject: Optional subject
            thread_id: Optional thread ID

        Returns:
            Response metadata

        Raises:
            NotImplementedError: Web form doesn't support outbound messages
        """
        raise NotImplementedError(
            "Web form channel is inbound-only. Use email channel for responses."
        )

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        """Verify webhook signature (not applicable for web form).

        Web form submissions don't use webhook signatures.
        Security is handled by CORS and rate limiting.

        Args:
            payload: Request body
            signature: Signature header

        Returns:
            Always True (no signature verification needed)
        """
        return True
