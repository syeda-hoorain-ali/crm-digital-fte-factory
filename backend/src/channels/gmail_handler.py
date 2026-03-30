"""Gmail channel handler with Pub/Sub integration."""

import logging
from typing import Any
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials

from ..kafka.schemas import Channel, ChannelMessage
from ..utils.hmac_validator import HMACValidator
from .base import BaseChannelHandler
from .gmail_client import GmailClient
from .email_parser import EmailParser

logger = logging.getLogger(__name__)


class GmailHandler(BaseChannelHandler):
    """Handler for Gmail email channel with Pub/Sub notifications."""

    def __init__(
        self,
        credentials: Credentials,
        webhook_secret: str
    ):
        """Initialize Gmail handler.

        Args:
            credentials: Google OAuth2 credentials
            webhook_secret: Secret for HMAC signature verification
        """
        super().__init__(Channel.EMAIL)
        self.gmail_client = GmailClient(credentials)
        self.hmac_validator = HMACValidator(webhook_secret)
        self.parser = EmailParser()

    async def initialize(self) -> None:
        """Initialize Gmail API client."""
        await self.gmail_client.initialize()
        logger.info("Gmail handler initialized")

    async def process_inbound_message(self, payload: dict[str, Any]) -> ChannelMessage | None:
        """Process inbound email from Gmail Pub/Sub notification.

        Args:
            payload: Pub/Sub notification payload with history_id or message_id

        Returns:
            Unified ChannelMessage, or None if no new messages to process

        Raises:
            ValueError: If payload is invalid or message cannot be retrieved
        """
        # Check if this is a history notification (from Pub/Sub watch)
        history_id = payload.get('history_id')
        message_id = payload.get('message_id')

        if history_id:
            # Fetch history to get new message IDs
            # Note: There's a race condition where Gmail Pub/Sub sends notifications
            # before the History API has the data. Retry with delay if empty.
            print(f"[GMAIL] Fetching history from ID: {history_id}")

            max_retries = 3
            retry_delay = 2  # seconds
            history_response = None

            for attempt in range(max_retries):
                # Don't filter by historyTypes - get ALL events to catch self-sent emails
                history_response = await self.gmail_client.get_history(
                    start_history_id=history_id,
                    history_types=None  # Get all history events
                )

                history_records = history_response.get('history', [])

                if history_records:
                    # Got history data, break out of retry loop
                    print(f"[GMAIL] History response (attempt {attempt + 1}): {history_response}")
                    print(f"[GMAIL] History records count: {len(history_records)}")
                    break

                if attempt < max_retries - 1:
                    # Empty history, but we have retries left
                    print(f"[GMAIL] History empty on attempt {attempt + 1}, retrying in {retry_delay}s...")
                    import asyncio
                    await asyncio.sleep(retry_delay)
                else:
                    # Final attempt, still empty
                    print(f"[GMAIL] History response (final attempt): {history_response}")
                    print(f"[GMAIL] History records count: 0")

            # Extract message IDs from history
            history_records = history_response.get('history', [])

            if not history_records:
                # No history records - this could be:
                # 1. A notification for a non-message event (label change, deletion)
                # 2. A self-sent email (Gmail doesn't track these in History API)
                #
                # Fallback: Search for recent messages in INBOX
                print(f"[GMAIL] No history records - falling back to recent message search")
                logger.info(f"No history in {history_id} - searching recent messages")

                recent_messages = await self.gmail_client.search_recent_messages(max_results=1)

                if not recent_messages:
                    print(f"[GMAIL] No recent messages found - skipping")
                    logger.info("No recent messages found - skipping notification")
                    return None

                # Use the most recent message
                message_id = recent_messages[0]['id']
                print(f"[GMAIL] Found recent message ID: {message_id}")
                logger.info(f"Using recent message from fallback search: {message_id}")
            else:
                # Process the first new message from history (most recent)
                for record in history_records:
                    print(f"[GMAIL] Processing history record: {record}")

                    # Try messagesAdded first (when filtered by historyTypes)
                    messages_added = record.get('messagesAdded', [])
                    if messages_added:
                        message_id = messages_added[0]['message']['id']
                        print(f"[GMAIL] Found message ID from messagesAdded: {message_id}")
                        break

                    # Try messages array (when not filtered)
                    messages = record.get('messages', [])
                    if messages:
                        message_id = messages[0]['id']
                        print(f"[GMAIL] Found message ID from messages: {message_id}")
                        break

                if not message_id:
                    # History exists but no message IDs found
                    print(f"[GMAIL] No message IDs in history records - skipping")
                    logger.info(f"No message IDs found in history {history_id} - skipping")
                    return None

        elif not message_id:
            raise ValueError("Missing both message_id and history_id in payload")

        try:
            # Fetch full message from Gmail API
            gmail_message = await self.gmail_client.get_message(message_id)

            # Parse message
            parsed = self.parser.parse_gmail_message(gmail_message)

            # Filter out non-inbound messages
            labels = parsed.get('labels', [])

            # Skip SENT messages (outbound emails we sent)
            if 'SENT' in labels and 'INBOX' not in labels:
                print(f"[GMAIL] Skipping SENT message (outbound): {message_id}")
                logger.info(f"Skipping outbound SENT message: {message_id}")
                return None

            # Skip DRAFT messages
            if 'DRAFT' in labels:
                print(f"[GMAIL] Skipping DRAFT message: {message_id}")
                logger.info(f"Skipping DRAFT message: {message_id}")
                return None

            # Only process messages in INBOX (inbound customer messages)
            if 'INBOX' not in labels:
                print(f"[GMAIL] Skipping non-INBOX message: {message_id} (labels: {labels})")
                logger.info(f"Skipping non-INBOX message: {message_id}")
                return None

            # Extract sender information
            sender_info = self.parser.extract_sender_info(parsed)
            customer_email = sender_info.get('email')
            customer_name = sender_info.get('name')

            if not customer_email:
                raise ValueError("Could not extract sender email address")

            # Skip messages from our own email address (loop prevention)
            # This prevents processing our own outbound replies as inbound messages
            our_email = self.gmail_client.credentials.token  # This won't work, need to get from config
            # For now, we rely on SENT label filtering above

            # Detect threading information
            thread_info = self.parser.detect_thread_info(parsed)

            # Parse timestamp
            timestamp = self.parser.parse_timestamp(parsed.get('date'))
            if not timestamp:
                timestamp = datetime.now(timezone.utc)

            # Create channel message
            channel_message = self.create_channel_message(
                message_id=parsed['message_id'],
                customer_contact=customer_email,
                body=parsed['body'],
                customer_name=customer_name,
                subject=parsed.get('subject'),
                thread_id=parsed.get('thread_id'),
                parent_message_id=thread_info.get('parent_message_id'),
                metadata={
                    'gmail_thread_id': parsed.get('thread_id'),
                    'message_id_header': parsed.get('message_id_header'),
                    'in_reply_to': thread_info.get('in_reply_to'),
                    'references': thread_info.get('references'),
                    'is_reply': thread_info.get('is_reply'),
                    'labels': parsed.get('labels', []),
                    'snippet': parsed.get('snippet', ''),
                    'attachments': parsed.get('attachments', [])
                },
                timestamp=timestamp
            )

            logger.info(
                f"Processed inbound email from {customer_email}",
                extra={
                    "message_id": message_id,
                    "thread_id": parsed.get('thread_id'),
                    "is_reply": thread_info.get('is_reply')
                }
            )

            return channel_message

        except Exception as e:
            logger.error(
                f"Failed to process inbound email: {e}",
                extra={"message_id": message_id},
                exc_info=True
            )
            raise ValueError(f"Failed to process email message: {e}")

    async def send_outbound_message(
        self,
        customer_contact: str,
        message_body: str,
        subject: str | None = None,
        thread_id: str | None = None
    ) -> dict[str, Any]:
        """Send outbound email through Gmail.

        Args:
            customer_contact: Customer email address
            message_body: Email body text
            subject: Email subject (required for new threads)
            thread_id: Gmail thread ID for replies

        Returns:
            Sent message metadata

        Raises:
            ValueError: If required parameters are missing
            Exception: If send fails
        """
        # Validate required fields
        if not subject and not thread_id:
            raise ValueError("Subject is required for new email threads")

        # Default subject for replies
        if not subject:
            subject = "Re: Support Request"

        try:
            # Send email via Gmail API
            sent_message = await self.gmail_client.send_message(
                to=customer_contact,
                subject=subject,
                body=message_body,
                thread_id=thread_id
            )

            logger.info(
                f"Sent outbound email to {customer_contact}",
                extra={
                    "message_id": sent_message['id'],
                    "thread_id": sent_message.get('threadId')
                }
            )

            return {
                'message_id': sent_message['id'],
                'thread_id': sent_message.get('threadId'),
                'status': 'sent'
            }

        except Exception as e:
            logger.error(
                f"Failed to send email to {customer_contact}: {e}",
                exc_info=True
            )
            raise

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        """Verify Gmail webhook signature using HMAC.

        Args:
            payload: Raw request body bytes
            signature: Signature from X-Goog-Signature header

        Returns:
            True if signature is valid
        """
        return self.hmac_validator.verify_signature(
            payload=payload,
            provided_signature=signature,
            signature_prefix=None  # Gmail doesn't use prefix
        )

    async def setup_push_notifications(
        self,
        pubsub_topic: str,
        label_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """Set up Gmail push notifications via Pub/Sub.

        Args:
            pubsub_topic: Google Cloud Pub/Sub topic name
            label_ids: Gmail label IDs to watch (default: INBOX)

        Returns:
            Watch response with expiration

        Raises:
            Exception: If setup fails
        """
        try:
            watch_response = await self.gmail_client.watch_mailbox(
                topic_name=pubsub_topic,
                label_ids=label_ids
            )

            logger.info(
                "Gmail push notifications configured",
                extra={
                    "topic": pubsub_topic,
                    "expiration": watch_response.get('expiration')
                }
            )

            return watch_response

        except Exception as e:
            logger.error(f"Failed to setup push notifications: {e}", exc_info=True)
            raise

    async def stop_push_notifications(self) -> None:
        """Stop Gmail push notifications.

        Raises:
            Exception: If stop fails
        """
        try:
            await self.gmail_client.stop_watch()
            logger.info("Gmail push notifications stopped")
        except Exception as e:
            logger.error(f"Failed to stop push notifications: {e}", exc_info=True)
            raise
