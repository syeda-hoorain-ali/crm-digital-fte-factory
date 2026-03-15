"""WhatsApp test helper for E2E testing with real message sending via Twilio."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


class WhatsAppTestHelper:
    """Helper class for WhatsApp E2E testing with real Twilio operations.

    Note: Twilio API is synchronous. Methods that need to be awaited in async
    tests use asyncio.to_thread() to run sync operations in thread pool.
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str
    ):
        """Initialize WhatsApp test helper.

        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: WhatsApp sender number (format: whatsapp:+1234567890)
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
        self.client: Optional[Client] = None

    def initialize(self) -> None:
        """Initialize Twilio client.

        Note: This is synchronous as Twilio API doesn't support async.
        """
        try:
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("WhatsApp test helper initialized")

            # Try to verify credentials by fetching account info
            # Skip if using test credentials (they have limited API access)
            try:
                account = self.client.api.accounts(self.account_sid).fetch()
                logger.info(f"Connected to Twilio account: {account.friendly_name}")
            except Exception as verify_error:
                # If verification fails (e.g., test credentials), just log and continue
                # The actual message sending will fail if credentials are invalid
                logger.warning(
                    f"Could not verify account (may be using test credentials): {verify_error}"
                )

        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp test helper: {e}", exc_info=True)
            raise

    def send_test_message(
        self,
        to: str,
        body: str,
        media_url: Optional[str] = None
    ) -> dict[str, Any]:
        """Send a test WhatsApp message (synchronous).

        Args:
            to: Recipient phone number (with or without whatsapp: prefix)
            body: Message content
            media_url: Optional media URL for attachments

        Returns:
            Sent message metadata with sid and status

        Raises:
            RuntimeError: If client not initialized
            TwilioRestException: If send fails
        """
        if not self.client:
            raise RuntimeError("Twilio client not initialized. Call initialize() first.")

        try:
            # Ensure phone number has whatsapp: prefix
            if not to.startswith("whatsapp:"):
                to = f"whatsapp:{to}"

            # Prepare message parameters
            message_params: dict = {
                "from_": self.from_number,
                "to": to,
                "body": body
            }

            if media_url:
                message_params["media_url"] = [media_url]

            # Send message
            message = self.client.messages.create(**message_params)

            logger.info(
                f"Test WhatsApp message sent to {to}",
                extra={
                    "message_sid": message.sid,
                    "status": message.status,
                    "body_preview": body[:50]
                }
            )

            return {
                "sid": message.sid,
                "status": message.status,
                "to": to,
                "from": self.from_number,
                "body": body,
                "date_created": message.date_created.isoformat() if message.date_created else None
            }

        except TwilioRestException as e:
            logger.error(f"Failed to send test WhatsApp message: {e}", exc_info=True)
            raise

    def get_message_status(self, message_sid: str) -> dict[str, Any]:
        """Get message delivery status (synchronous).

        Args:
            message_sid: Twilio message SID

        Returns:
            Message status information

        Raises:
            RuntimeError: If client not initialized
            TwilioRestException: If fetch fails
        """
        if not self.client:
            raise RuntimeError("Twilio client not initialized")

        try:
            message = self.client.messages(message_sid).fetch()

            return {
                "sid": message.sid,
                "status": message.status,
                "error_code": message.error_code,
                "error_message": message.error_message,
                "date_sent": message.date_sent.isoformat() if message.date_sent else None,
                "date_updated": message.date_updated.isoformat() if message.date_updated else None
            }

        except TwilioRestException as e:
            logger.error(f"Failed to fetch message status: {e}", exc_info=True)
            raise

    async def wait_for_delivery(
        self,
        message_sid: str,
        timeout_seconds: int = 30,
        poll_interval: int = 2
    ) -> Optional[dict[str, Any]]:
        """Wait for message to be delivered (async wrapper).

        Args:
            message_sid: Twilio message SID to monitor
            timeout_seconds: Maximum time to wait for delivery
            poll_interval: Seconds between polling attempts

        Returns:
            Final message status if delivered, None if timeout

        Raises:
            RuntimeError: If client not initialized
        """
        if not self.client:
            raise RuntimeError("Twilio client not initialized")

        start_time = datetime.now(timezone.utc)

        logger.info(
            f"Waiting for message delivery: {message_sid}",
            extra={"timeout": timeout_seconds}
        )

        while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout_seconds:
            try:
                status = await asyncio.to_thread(
                    self.get_message_status, message_sid
                )

                # Check if delivered or failed
                if status["status"] in ["delivered", "read"]:
                    logger.info(
                        f"Message delivered: {message_sid}",
                        extra={"status": status["status"]}
                    )
                    return status
                elif status["status"] in ["failed", "undelivered"]:
                    logger.warning(
                        f"Message delivery failed: {message_sid}",
                        extra={
                            "status": status["status"],
                            "error_code": status.get("error_code"),
                            "error_message": status.get("error_message")
                        }
                    )
                    return status

            except TwilioRestException as e:
                logger.warning(f"Error polling message status: {e}")

            await asyncio.sleep(poll_interval)

        logger.warning(f"Timeout waiting for message delivery: {message_sid}")
        return None

    def list_recent_messages(
        self,
        limit: int = 10,
        to: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List recent messages (synchronous).

        Args:
            limit: Maximum number of messages to return
            to: Optional filter by recipient phone number

        Returns:
            List of recent messages

        Raises:
            RuntimeError: If client not initialized
        """
        if not self.client:
            raise RuntimeError("Twilio client not initialized")

        try:
            # Build filter parameters
            filter_params: dict = {"limit": limit}
            if to:
                if not to.startswith("whatsapp:"):
                    to = f"whatsapp:{to}"
                filter_params["to"] = to

            messages = self.client.messages.list(**filter_params)

            result = []
            for msg in messages:
                result.append({
                    "sid": msg.sid,
                    "from": msg.from_,
                    "to": msg.to,
                    "body": msg.body,
                    "status": msg.status,
                    "date_created": msg.date_created.isoformat() if msg.date_created else None
                })

            logger.info(f"Listed {len(result)} recent messages")
            return result

        except TwilioRestException as e:
            logger.error(f"Failed to list messages: {e}", exc_info=True)
            return []
