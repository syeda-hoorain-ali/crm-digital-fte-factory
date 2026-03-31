"""Gmail test helper for E2E testing with real email sending/receiving."""

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from email.mime.text import MIMEText
from email.utils import make_msgid

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GmailTestHelper:
    """Helper class for Gmail E2E testing with real email operations.

    Note: Gmail API is synchronous. Methods that need to be awaited in async
    tests use asyncio.to_thread() to run sync operations in thread pool.
    """

    def __init__(self, credentials_path: str):
        """Initialize Gmail test helper.

        Args:
            credentials_path: Path to Gmail OAuth2 credentials JSON
        """
        self.credentials_path = credentials_path
        self.credentials: Optional[Credentials] = None
        self.service = None

    def initialize(self) -> None:
        """Initialize Gmail API service with credentials.

        Note: This is synchronous as Gmail API doesn't support async.
        """
        try:
            # Load credentials from file
            with open(self.credentials_path, 'r') as f:
                creds_data = json.load(f)

            # Create credentials object
            self.credentials = Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=creds_data.get('scopes', ['https://www.googleapis.com/auth/gmail.modify'])
            )

            # Refresh if expired
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())

            # Build service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("Gmail test helper initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Gmail test helper: {e}", exc_info=True)
            raise

    def send_test_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Send a test email (synchronous).

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            from_email: Optional sender email (defaults to authenticated account)

        Returns:
            Sent message metadata with id and threadId

        Raises:
            RuntimeError: If service not initialized
            HttpError: If send fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized. Call initialize() first.")

        try:
            # Create MIME message
            message = MIMEText(body)
            message['To'] = to
            message['Subject'] = subject
            if from_email:
                message['From'] = from_email

            # Add threading headers if this is a reply
            if in_reply_to:
                message['In-Reply-To'] = in_reply_to
                # References should include the parent and any previous IDs
                message['References'] = references or in_reply_to

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            request_body = {'raw': raw_message}
            if thread_id:
                request_body['threadId'] = thread_id

            sent_message = self.service.users().messages().send(
                userId='me',
                body=request_body
            ).execute()

            logger.info(
                f"Test email sent to {to}",
                extra={
                    "message_id": sent_message['id'],
                    "thread_id": sent_message.get('threadId'),
                    "subject": subject
                }
            )

            return sent_message

        except HttpError as e:
            logger.error(f"Failed to send test email: {e}", exc_info=True)
            raise

    async def wait_for_reply(
        self,
        thread_id: str,
        timeout_seconds: int = 60,
        poll_interval: int = 2
    ) -> Optional[dict[str, Any]]:
        """Wait for a reply in a specific thread (async wrapper).

        Args:
            thread_id: Gmail thread ID to monitor
            timeout_seconds: Maximum time to wait for reply
            poll_interval: Seconds between polling attempts

        Returns:
            Reply message data if found, None if timeout

        Raises:
            RuntimeError: If service not initialized
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        start_time = datetime.now(timezone.utc)
        initial_message_count = await asyncio.to_thread(
            self._get_thread_message_count, thread_id
        )

        logger.info(
            f"Waiting for reply in thread {thread_id}",
            extra={
                "initial_messages": initial_message_count,
                "timeout": timeout_seconds
            }
        )

        while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout_seconds:
            try:
                current_count = await asyncio.to_thread(
                    self._get_thread_message_count, thread_id
                )

                # Check if new message arrived
                if current_count > initial_message_count:
                    thread = await asyncio.to_thread(self._get_thread, thread_id)
                    # Return the last message (newest)
                    messages = thread.get('messages', [])
                    if messages:
                        reply = messages[-1]
                        logger.info(
                            f"Reply received in thread {thread_id}",
                            extra={"message_id": reply['id']}
                        )
                        return reply

            except HttpError as e:
                logger.warning(f"Error polling thread: {e}")

            await asyncio.sleep(poll_interval)

        logger.warning(f"Timeout waiting for reply in thread {thread_id}")
        return None

    def _get_thread_message_count(self, thread_id: str) -> int:
        """Get number of messages in a thread (synchronous).

        Args:
            thread_id: Gmail thread ID

        Returns:
            Number of messages in thread
        """
        try:
            thread = self._get_thread(thread_id)
            return len(thread.get('messages', []))
        except HttpError:
            return 0

    def _get_thread(self, thread_id: str) -> dict[str, Any]:
        """Fetch thread data (synchronous).

        Args:
            thread_id: Gmail thread ID

        Returns:
            Thread data with messages
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        thread = self.service.users().threads().get(
            userId='me',
            id=thread_id,
            format='full'
        ).execute()
        return thread

    def get_message(self, message_id: str) -> dict[str, Any]:
        """Fetch message by ID (synchronous).

        Args:
            message_id: Gmail message ID

        Returns:
            Message data
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        message = self.service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        return message

    def delete_message(self, message_id: str) -> None:
        """Delete a message - move to trash (synchronous).

        Args:
            message_id: Gmail message ID
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            logger.info(f"Deleted test message {message_id}")
        except HttpError as e:
            logger.warning(f"Failed to delete message {message_id}: {e}")

    def delete_thread(self, thread_id: str) -> None:
        """Delete all messages in a thread (synchronous).

        Args:
            thread_id: Gmail thread ID
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            # Get all messages in thread
            thread = self._get_thread(thread_id)
            messages = thread.get('messages', [])

            # Delete each message
            for message in messages:
                self.delete_message(message['id'])

            logger.info(f"Deleted thread {thread_id} with {len(messages)} messages")
        except HttpError as e:
            logger.warning(f"Failed to delete thread {thread_id}: {e}")

    def search_messages(
        self,
        query: str,
        max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search for messages matching query (synchronous).

        Args:
            query: Gmail search query (e.g., "subject:test from:user@example.com")
            max_results: Maximum number of results

        Returns:
            List of matching messages
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages matching query: {query}")
            return messages

        except HttpError as e:
            logger.error(f"Failed to search messages: {e}", exc_info=True)
            return []
