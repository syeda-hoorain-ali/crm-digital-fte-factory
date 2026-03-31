"""Twilio client wrapper for WhatsApp messaging."""

import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


class TwilioClient:
    """Wrapper for Twilio REST API client."""

    def __init__(self, account_sid: str, auth_token: str, whatsapp_from: str):
        """Initialize Twilio client.

        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            whatsapp_from: WhatsApp sender number (format: whatsapp:+1234567890)
        """
        self.client = Client(account_sid, auth_token)
        self.whatsapp_from = whatsapp_from
        logger.info("Twilio client initialized")

    async def send_whatsapp_message(
        self,
        to: str,
        body: str,
        media_url: Optional[str] = None
    ) -> dict:
        """Send WhatsApp message via Twilio.

        Args:
            to: Recipient phone number (format: whatsapp:+1234567890)
            body: Message content
            media_url: Optional media URL for attachments

        Returns:
            Response metadata with message SID and status

        Raises:
            TwilioRestException: If send fails
        """
        try:
            # Ensure phone number has whatsapp: prefix
            if not to.startswith("whatsapp:"):
                to = f"whatsapp:{to}"

            # Prepare message parameters
            message_params = {
                "from_": self.whatsapp_from,
                "to": to,
                "body": body
            }

            if media_url:
                message_params["media_url"] = [media_url]

            # Send message
            message = self.client.messages.create(**message_params)

            logger.info(
                f"WhatsApp message sent successfully",
                extra={
                    "message_sid": message.sid,
                    "to": to,
                    "status": message.status
                }
            )

            return {
                "message_sid": message.sid,
                "status": message.status,
                "to": to,
                "from": self.whatsapp_from,
                "date_created": message.date_created.isoformat() if message.date_created else None
            }

        except TwilioRestException as e:
            logger.error(
                f"Failed to send WhatsApp message: {e}",
                extra={
                    "error_code": e.code,
                    "error_message": e.msg,
                    "to": to
                },
                exc_info=True
            )
            raise

    async def get_message_status(self, message_sid: str) -> dict:
        """Get message delivery status from Twilio.

        Args:
            message_sid: Twilio message SID

        Returns:
            Message status information

        Raises:
            TwilioRestException: If fetch fails
        """
        try:
            message = self.client.messages(message_sid).fetch()

            return {
                "message_sid": message.sid,
                "status": message.status,
                "error_code": message.error_code,
                "error_message": message.error_message,
                "date_sent": message.date_sent.isoformat() if message.date_sent else None,
                "date_updated": message.date_updated.isoformat() if message.date_updated else None
            }

        except TwilioRestException as e:
            logger.error(
                f"Failed to fetch message status: {e}",
                extra={
                    "message_sid": message_sid,
                    "error_code": e.code
                },
                exc_info=True
            )
            raise
