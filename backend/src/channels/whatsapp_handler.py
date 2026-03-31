"""WhatsApp channel handler with Twilio integration."""

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from twilio.request_validator import RequestValidator

from ..kafka.schemas import Channel
from .base import BaseChannelHandler
from .twilio_client import TwilioClient


# WhatsApp message limit (Twilio enforces 1600 characters)
WHATSAPP_MESSAGE_LIMIT = 1600

# Escalation keywords
ESCALATION_KEYWORDS = ["human", "agent"]


class WhatsAppHandler(BaseChannelHandler):
    """Handler for WhatsApp messages via Twilio."""

    def __init__(
        self,
        twilio_client: TwilioClient,
        auth_token: str
    ):
        """Initialize WhatsApp handler.

        Args:
            twilio_client: Twilio client for sending messages
            auth_token: Twilio auth token for signature verification
        """
        super().__init__(Channel.WHATSAPP)
        self.twilio_client = twilio_client
        self.request_validator = RequestValidator(auth_token)

    async def process_inbound_message(self, payload: dict[str, Any]):
        """Process inbound WhatsApp message from Twilio webhook.

        Twilio webhook payload format:
        - MessageSid: Unique message identifier
        - From: Sender phone (whatsapp:+1234567890)
        - To: Recipient phone (whatsapp:+1234567890)
        - Body: Message content
        - ProfileName: Sender's WhatsApp profile name
        - NumMedia: Number of media attachments
        - MediaUrl0, MediaContentType0: First media attachment (if any)

        Args:
            payload: Twilio webhook payload

        Returns:
            Unified ChannelMessage

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        required_fields = ["MessageSid", "From", "Body"]
        missing_fields = [field for field in required_fields if not payload.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Extract phone number (remove whatsapp: prefix)
        from_number = payload["From"].replace("whatsapp:", "")
        to_number = payload.get("To", "").replace("whatsapp:", "")

        # Extract message content
        message_body = payload["Body"]

        # Check for escalation keywords
        requires_escalation = self._detect_escalation(message_body)

        # Build metadata
        metadata = {
            "message_sid": payload["MessageSid"],
            "profile_name": payload.get("ProfileName"),
            "to_number": to_number,
            "num_media": int(payload.get("NumMedia", 0)),
            "requires_escalation": requires_escalation
        }

        # Add media attachments if present
        num_media = int(payload.get("NumMedia", 0))
        if num_media > 0:
            media_items = []
            for i in range(num_media):
                media_url = payload.get(f"MediaUrl{i}")
                media_type = payload.get(f"MediaContentType{i}")
                if media_url:
                    media_items.append({
                        "url": media_url,
                        "content_type": media_type
                    })
            metadata["media"] = media_items

        # Create channel message
        return self.create_channel_message(
            message_id=payload["MessageSid"],
            customer_contact=from_number,
            body=message_body,
            customer_name=payload.get("ProfileName"),
            metadata=metadata,
            timestamp=datetime.now(timezone.utc)
        )

    async def send_outbound_message(
        self,
        customer_contact: str,
        message_body: str,
        subject: str | None = None,
        thread_id: str | None = None
    ) -> dict[str, Any]:
        """Send outbound WhatsApp message with automatic message splitting.

        WhatsApp has a 1600 character limit. Messages longer than this
        will be automatically split into multiple messages.

        Args:
            customer_contact: Customer phone number (with or without whatsapp: prefix)
            message_body: Message content
            subject: Not used for WhatsApp (ignored)
            thread_id: Not used for WhatsApp (ignored)

        Returns:
            Response metadata with message SIDs

        Raises:
            Exception: If send fails
        """
        # Split message if needed
        message_parts = self._split_message(message_body)

        # Send all parts
        responses = []
        for i, part in enumerate(message_parts):
            # Add part indicator if message was split
            if len(message_parts) > 1:
                part_text = f"[{i+1}/{len(message_parts)}] {part}"
            else:
                part_text = part

            # Send via Twilio
            response = await self.twilio_client.send_whatsapp_message(
                to=customer_contact,
                body=part_text
            )
            responses.append(response)

        return {
            "message_count": len(message_parts),
            "message_sids": [r["message_sid"] for r in responses],
            "responses": responses
        }

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        url: str
    ) -> bool:
        """Verify Twilio webhook signature using RequestValidator.

        Args:
            payload: Raw request body (form-encoded)
            signature: X-Twilio-Signature header value
            url: Full webhook URL including query parameters

        Returns:
            True if signature is valid
        """
        # Twilio uses form-encoded data, need to parse it
        # The RequestValidator expects a dict of form parameters
        try:
            # Parse form data
            form_data = {}
            if payload:
                # Decode and parse form data
                decoded = payload.decode('utf-8')
                for pair in decoded.split('&'):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        # URL decode the values
                        from urllib.parse import unquote_plus
                        form_data[unquote_plus(key)] = unquote_plus(value)

            # Validate signature
            is_valid = self.request_validator.validate(
                url,
                form_data,
                signature
            )

            return is_valid

        except Exception as e:
            # Log error but don't expose details
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Signature verification failed: {e}", exc_info=True)
            return False

    def _split_message(self, message: str) -> list[str]:
        """Split message into parts that fit WhatsApp's 1600 character limit.

        Splits on sentence boundaries when possible to avoid breaking mid-sentence.
        If a single sentence exceeds the limit, splits on word boundaries.

        Args:
            message: Message to split

        Returns:
            List of message parts, each under 1600 characters
        """
        if len(message) <= WHATSAPP_MESSAGE_LIMIT:
            return [message]

        parts = []
        remaining = message

        while remaining:
            # Strip leading whitespace for next part
            remaining = remaining.lstrip()

            if not remaining:
                break

            if len(remaining) <= WHATSAPP_MESSAGE_LIMIT:
                parts.append(remaining)
                break

            # Try to split on sentence boundary (. ! ?)
            split_pos = WHATSAPP_MESSAGE_LIMIT

            # Look for sentence ending within limit
            sentence_match = None
            for match in re.finditer(r'[.!?]\s+', remaining[:WHATSAPP_MESSAGE_LIMIT]):
                sentence_match = match

            if sentence_match:
                split_pos = sentence_match.end()
            else:
                # No sentence boundary, try word boundary
                last_space = remaining[:WHATSAPP_MESSAGE_LIMIT].rfind(' ')
                if last_space > WHATSAPP_MESSAGE_LIMIT * 0.8:  # At least 80% of limit
                    split_pos = last_space + 1
                else:
                    # Force split at limit (rare case)
                    split_pos = WHATSAPP_MESSAGE_LIMIT

            # Extract part (strip trailing whitespace only)
            part = remaining[:split_pos].rstrip()
            if part:  # Only add non-empty parts
                parts.append(part)
            remaining = remaining[split_pos:]

        return parts if parts else [message]

    def _detect_escalation(self, message: str) -> bool:
        """Detect if message contains escalation keywords.

        Checks for keywords "human" or "agent" (case-insensitive).

        Args:
            message: Message content

        Returns:
            True if escalation keywords detected
        """
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in ESCALATION_KEYWORDS)
