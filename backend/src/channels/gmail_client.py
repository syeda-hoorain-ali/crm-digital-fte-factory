"""Gmail API client wrapper for email operations."""

import base64
import logging
from typing import Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GmailClient:
    """Gmail API client for sending and receiving emails."""

    def __init__(self, credentials: Credentials):
        """Initialize Gmail client.

        Args:
            credentials: Google OAuth2 credentials
        """
        self.credentials = credentials
        self.service = None

    async def initialize(self) -> None:
        """Initialize Gmail API service."""
        try:
            # Refresh credentials if expired
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())

            # Build Gmail API service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("Gmail API service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail API: {e}", exc_info=True)
            raise

    async def get_message(self, message_id: str) -> dict[str, Any]:
        """Fetch email message by ID.

        Args:
            message_id: Gmail message ID

        Returns:
            Message data including headers and body

        Raises:
            HttpError: If API request fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            logger.info(f"Retrieved message {message_id}")
            return message
        except HttpError as e:
            logger.error(f"Failed to get message {message_id}: {e}", exc_info=True)
            raise

    async def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None
    ) -> dict[str, Any]:
        """Send email message.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            thread_id: Gmail thread ID for replies
            in_reply_to: Message-ID header for threading
            references: References header for threading

        Returns:
            Sent message metadata

        Raises:
            HttpError: If send fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            # Create MIME message
            message = MIMEText(body)
            message['To'] = to
            message['Subject'] = subject

            # Add threading headers for replies
            if in_reply_to:
                message['In-Reply-To'] = in_reply_to
            if references:
                message['References'] = references

            # Encode message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            # Prepare send request
            send_request = {
                'raw': raw_message
            }
            if thread_id:
                send_request['threadId'] = thread_id

            # Send message
            sent_message = self.service.users().messages().send(
                userId='me',
                body=send_request
            ).execute()

            logger.info(
                f"Sent message to {to}",
                extra={
                    "message_id": sent_message['id'],
                    "thread_id": sent_message.get('threadId')
                }
            )
            return sent_message

        except HttpError as e:
            logger.error(f"Failed to send message to {to}: {e}", exc_info=True)
            raise

    async def watch_mailbox(
        self,
        topic_name: str,
        label_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """Set up Gmail push notifications via Pub/Sub.

        Args:
            topic_name: Google Cloud Pub/Sub topic name (projects/{project}/topics/{topic})
            label_ids: Gmail label IDs to watch (default: INBOX)

        Returns:
            Watch response with expiration timestamp

        Raises:
            HttpError: If watch setup fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            request_body = {
                'topicName': topic_name,
                'labelIds': label_ids or ['INBOX']
            }

            watch_response = self.service.users().watch(
                userId='me',
                body=request_body
            ).execute()

            logger.info(
                f"Gmail watch registered",
                extra={
                    "history_id": watch_response.get('historyId'),
                    "expiration": watch_response.get('expiration')
                }
            )
            return watch_response

        except HttpError as e:
            logger.error(f"Failed to set up Gmail watch: {e}", exc_info=True)
            raise

    async def stop_watch(self) -> None:
        """Stop Gmail push notifications.

        Raises:
            HttpError: If stop fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            self.service.users().stop(userId='me').execute()
            logger.info("Gmail watch stopped")
        except HttpError as e:
            logger.error(f"Failed to stop Gmail watch: {e}", exc_info=True)
            raise

    async def get_thread(self, thread_id: str) -> dict[str, Any]:
        """Fetch email thread by ID.

        Args:
            thread_id: Gmail thread ID

        Returns:
            Thread data with all messages

        Raises:
            HttpError: If API request fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            logger.info(f"Retrieved thread {thread_id}")
            return thread
        except HttpError as e:
            logger.error(f"Failed to get thread {thread_id}: {e}", exc_info=True)
            raise

    async def get_history(
        self,
        start_history_id: str,
        history_types: list[str] | None = None
    ) -> dict[str, Any]:
        """Fetch mailbox history changes since a given history ID.

        Args:
            start_history_id: History ID to start from
            history_types: Types of history to fetch (messageAdded, messageDeleted, etc.)

        Returns:
            History records with message changes

        Raises:
            HttpError: If API request fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            request_params = {
                'userId': 'me',
                'startHistoryId': start_history_id
            }
            if history_types:
                request_params['historyTypes'] = history_types

            history = self.service.users().history().list(**request_params).execute()
            logger.info(
                f"Retrieved history from {start_history_id}",
                extra={"history_count": len(history.get('history', []))}
            )
            return history
        except HttpError as e:
            logger.error(f"Failed to get history from {start_history_id}: {e}", exc_info=True)
            raise

    async def search_recent_messages(
        self,
        max_results: int = 5,
        label_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Search for recent messages in mailbox.

        Args:
            max_results: Maximum number of messages to return
            label_ids: Filter by label IDs (default: INBOX)

        Returns:
            List of message metadata (id, threadId)

        Raises:
            HttpError: If API request fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            request_params = {
                'userId': 'me',
                'maxResults': max_results,
                'labelIds': label_ids or ['INBOX']
            }

            response = self.service.users().messages().list(**request_params).execute()
            messages = response.get('messages', [])

            logger.info(
                f"Found {len(messages)} recent messages",
                extra={"max_results": max_results}
            )
            return messages
        except HttpError as e:
            logger.error(f"Failed to search recent messages: {e}", exc_info=True)
            raise
