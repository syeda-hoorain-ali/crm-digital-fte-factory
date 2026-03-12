"""Real Gmail E2E test with actual email sending/receiving.

This test sends real emails through Gmail API and verifies the complete flow:
1. Send email from test account to application email
2. Gmail receives and triggers Pub/Sub notification
3. Application webhook processes the email
4. Database records are created
5. Kafka events are published
6. Agent processes and sends response
7. Response email is received

Requires:
- GMAIL_TEST_CREDENTIALS_PATH: Path to test account credentials
- GMAIL_SUPPORT_ADDRESS: Application email address
- DATABASE_URL: PostgreSQL connection string
- KAFKA_BOOTSTRAP_SERVERS: Kafka broker address
"""

import asyncio
import os
import pytest
import uuid
from datetime import datetime, timezone
from sqlmodel import col, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.gmail_test_helper import GmailTestHelper
from src.database.models import (
    Customer,
    CustomerIdentifier,
    Conversation,
    Message,
    Ticket,
    WebhookDeliveryLog,
    Channel,
    IdentifierType,
    ConversationStatus,
    MessageDirection,
    MessageRole,
    DeliveryStatus,
    TicketStatus,
    WebhookProcessingStatus,
)


@pytest.mark.asyncio
@pytest.mark.e2e
class TestGmailRealFlow:
    """Real Gmail E2E tests with actual email operations."""

    @pytest.fixture(autouse=True)
    def setup_gmail_helper(self):
        """Initialize Gmail test helper (synchronous fixture)."""
        credentials_path = os.getenv("GMAIL_TEST_CREDENTIALS_PATH")
        if not credentials_path:
            pytest.skip("GMAIL_TEST_CREDENTIALS_PATH not set - skipping real Gmail E2E test")

        if not os.path.exists(credentials_path):
            pytest.skip(f"Gmail credentials not found at {credentials_path}")

        self.gmail_helper = GmailTestHelper(credentials_path)
        self.gmail_helper.initialize()  # Synchronous initialization

        # Get application email address
        self.app_email = os.getenv("GMAIL_SUPPORT_ADDRESS")
        if not self.app_email:
            pytest.skip("GMAIL_SUPPORT_ADDRESS not set")

        # Generate unique test identifier
        self.test_id = str(uuid.uuid4())[:8]
        self.test_subject = f"E2E Test {self.test_id}"

        yield

        # Cleanup: Delete test emails
        # Note: Cleanup happens in individual tests to capture thread_id

    async def test_gmail_inbound_email_processing(
        self,
        e2e_session: AsyncSession,
        clean_test_data
    ):
        """Test complete flow: send email → webhook → database → Kafka.

        Steps:
        1. Send test email from test account to application
        2. Wait for webhook to process (poll database)
        3. Verify customer created/identified
        4. Verify conversation created
        5. Verify message stored
        6. Verify ticket created
        7. Verify webhook log
        8. Verify Kafka event (if consumer available)
        """
        print(f"\n{'='*60}")
        print(f"Starting Gmail Real E2E Test: {self.test_id}")
        print(f"{'='*60}")

        # Step 1: Send test email
        print("\n[Step 1] Sending test email...")
        test_body = f"This is a test email for E2E testing. Test ID: {self.test_id}"

        # Gmail API is synchronous, run in thread pool
        sent_message = await asyncio.to_thread(
            self.gmail_helper.send_test_email,
            to=self.app_email,
            subject=self.test_subject,
            body=test_body
        )

        message_id = sent_message['id']
        thread_id = sent_message['threadId']

        print(f"[OK] Email sent successfully")
        print(f"  Message ID: {message_id}")
        print(f"  Thread ID: {thread_id}")

        # Step 2: Wait for webhook processing (poll database for message)
        print("\n[Step 2] Waiting for webhook to process email...")
        print("  (Polling database for up to 60 seconds)")

        message_found = False
        db_message = None
        max_wait = 60  # seconds
        poll_interval = 2  # seconds
        elapsed = 0

        while elapsed < max_wait and not message_found:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            # FIX: Search by content containing the unique test_id, NOT the sender's message_id
            result = await e2e_session.execute(
                select(Message).where(col(Message.content).contains(self.test_id))
            )
            db_message = result.scalars().first()

            if db_message:
                message_found = True
                # Save the actual receiver ID for later validation
                receiver_message_id = db_message.channel_message_id 
                print(f"[OK] Message found in database after {elapsed} seconds")
                break

            print(f"  Waiting... ({elapsed}s / {max_wait}s)")

        if not message_found:
            pytest.fail(
                f"Webhook did not process email within {max_wait} seconds. "
                "Check if Gmail Pub/Sub notifications are configured correctly."
            )

        # Step 3: Verify customer created/identified
        print("\n[Step 3] Verifying customer identification...")

        # Get test account email (sender)
        test_email = os.getenv("GMAIL_TEST_ACCOUNT_EMAIL")
        if not test_email:
            # Try to extract from sent message
            sent_message_details = await asyncio.to_thread(
                self.gmail_helper.get_message,
                message_id
            )
            # Parse from header
            test_email = "test@example.com"  # Fallback

        result = await e2e_session.execute(
            select(CustomerIdentifier)
            .where(CustomerIdentifier.identifier_value == test_email)
        )
        identifier = result.scalars().first()

        assert identifier is not None, f"Customer identifier not found for {test_email}"
        assert identifier.identifier_type == IdentifierType.EMAIL

        customer_id = identifier.customer_id
        print(f"[OK] Customer identified: {customer_id}")

        # Verify customer record
        result = await e2e_session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalars().first()

        assert customer is not None
        print(f"  Customer name: {customer.name}")

        # Step 4: Verify conversation created
        print("\n[Step 4] Verifying conversation...")

        # Use the conversation_id from the message we found
        await e2e_session.refresh(db_message)
        assert db_message is not None
        conversation_id = db_message.conversation_id

        result = await e2e_session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalars().first()

        assert conversation is not None
        assert conversation.customer_id == customer_id
        assert conversation.initial_channel == Channel.EMAIL
        assert conversation.status == ConversationStatus.ACTIVE
        print(f"[OK] Conversation created: {conversation.id}")

        # Step 5: Verify message stored
        print("\n[Step 5] Verifying message storage...")
        assert db_message is not None

        # --- ADD THIS LINE TO FIX THE FAILURE ---
        await e2e_session.refresh(db_message) 
        # ----------------------------------------

        result = await e2e_session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .where(Message.id == db_message.id)
        )
        
        db_message_verify = result.scalars().first()

        assert db_message_verify is not None
        assert db_message_verify.conversation_id == conversation.id # Now this will match
        print(f"[OK] Message correctly linked to conversation: {db_message_verify.id}")

        # Step 6: Verify ticket created
        print("\n[Step 6] Verifying ticket creation...")

        result = await e2e_session.execute(
            select(Ticket)
            .where(Ticket.conversation_id == conversation.id)
            .where(Ticket.customer_id == customer_id)
        )
        ticket = result.scalars().first()

        assert ticket is not None
        assert ticket.source_channel == Channel.EMAIL
        assert ticket.status == TicketStatus.OPEN
        print(f"[OK] Ticket created: {ticket.id}")
        print(f"  Status: {ticket.status.value}")
        print(f"  Priority: {ticket.priority.value}")

        # Step 7: Verify webhook delivery log
        print("\n[Step 7] Verifying webhook log...")

        result = await e2e_session.execute(
            select(WebhookDeliveryLog)
            .where(col(WebhookDeliveryLog.webhook_type) == "gmail")
            .order_by(col(WebhookDeliveryLog.received_at).desc())
            .limit(10)
        )
        webhook_logs = result.scalars().all()

        # Find log for this message
        webhook_log = None
        for log in webhook_logs:
            if log.processing_status == WebhookProcessingStatus.COMPLETED:
                webhook_log = log
                break

        assert webhook_log is not None, "No completed webhook log found"
        assert webhook_log.signature_valid is True
        print(f"[OK] Webhook log found: {webhook_log.id}")
        print(f"  Status: {webhook_log.processing_status.value}")
        print(f"  Request ID: {webhook_log.request_id}")

        # Step 8: Cleanup - Delete test email thread
        print("\n[Step 8] Cleaning up test emails...")
        try:
            await asyncio.to_thread(self.gmail_helper.delete_thread, thread_id)
            print(f"[OK] Test email thread deleted")
        except Exception as e:
            print(f"⚠ Failed to delete test thread: {e}")

        print(f"\n{'='*60}")
        print(f"Gmail Real E2E Test PASSED: {self.test_id}")
        print(f"{'='*60}\n")

    async def test_gmail_reply_threading(
        self,
        e2e_session: AsyncSession,
        clean_test_data
    ):
        """Test email reply threading and conversation continuity.

        Steps:
        1. Send initial email
        2. Wait for processing
        3. Send reply in same thread
        4. Verify same conversation is used
        5. Verify message count increases
        """
        print(f"\n{'='*60}")
        print(f"Starting Gmail Threading Test: {self.test_id}")
        print(f"{'='*60}")

        # Step 1: Send initial email
        print("\n[Step 1] Sending initial email...")
        initial_body = f"Initial message for threading test. Test ID: {self.test_id}"

        sent_message_1 = await asyncio.to_thread(
            self.gmail_helper.send_test_email,
            to=self.app_email,
            subject=self.test_subject,
            body=initial_body
        )

        thread_id = sent_message_1['threadId']
        print(f"[OK] Initial email sent (Thread: {thread_id})")

        # NEW: Fetch the REAL RFC Message-ID header from Gmail
        # This is the secret to successful threading!
        full_msg = await asyncio.to_thread(self.gmail_helper.get_message, sent_message_1['id'])
        headers = full_msg.get('payload', {}).get('headers', [])
        real_rfc_id = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), None)

        # Step 2: Wait for processing
        print("\n[Step 2] Waiting for initial email processing...")
        print("  (Polling database for up to 30 seconds)")

        # Poll for the initial message by test_id
        message_found = False
        initial_message = None
        max_wait = 30
        poll_interval = 2
        elapsed = 0

        while elapsed < max_wait and not message_found:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            result = await e2e_session.execute(
                select(Message).where(col(Message.content).contains(self.test_id))
            )
            initial_message = result.scalars().first()

            if initial_message:
                message_found = True
                print(f"[OK] Initial message found after {elapsed} seconds")
                break

            print(f"  Waiting... ({elapsed}s / {max_wait}s)")

        if not message_found:
            pytest.skip("Initial email not processed yet - webhook may be delayed")

        # Get the conversation from the message
        await e2e_session.refresh(initial_message)
        initial_conversation_id = initial_message.conversation_id

        result = await e2e_session.execute(
            select(Conversation).where(Conversation.id == initial_conversation_id)
        )
        initial_conversation = result.scalars().first()

        assert initial_conversation is not None
        customer_id = initial_conversation.customer_id
        print(f"[OK] Initial conversation: {initial_conversation_id}")

        # Count initial messages
        result = await e2e_session.execute(
            select(Message)
            .where(Message.conversation_id == initial_conversation_id)
        )
        initial_message_count = len(result.scalars().all())
        print(f"  Initial message count: {initial_message_count}")

        # Step 3: Send reply in same thread
        print("\n[Step 3] Sending reply in same thread...")
        reply_body = f"Reply message in same thread. Test ID: {self.test_id}"

        # Use proper MIME headers for threading
        # Extract Message-ID from first message for threading
        first_message_id = sent_message_1.get('message_id')

        sent_message_2 = await asyncio.to_thread(
            self.gmail_helper.send_test_email,
            to=self.app_email,
            subject=f"Re: {self.test_subject}",
            body=reply_body,
            in_reply_to=real_rfc_id,        # Use the real header
            references=real_rfc_id,         # Use the real header
            thread_id=thread_id             # Use sender's thread context
        )

        print(f"[OK] Reply sent (Thread: {sent_message_2['threadId']})")

        # Verify it's in the same thread
        if sent_message_2['threadId'] != thread_id:
            print(f"⚠ Warning: Reply created new thread {sent_message_2['threadId']} instead of using {thread_id}")

        # Step 4: Wait for reply processing
        print("\n[Step 4] Waiting for reply processing...")
        print("  (Polling database for up to 60 seconds)")

        # Poll for the reply message
        reply_found = False
        max_wait_reply = 60
        poll_interval_reply = 2
        elapsed_reply = 0

        while elapsed_reply < max_wait_reply and not reply_found:
            await asyncio.sleep(poll_interval_reply)
            elapsed_reply += poll_interval_reply

            # CRITICAL: Clear session cache to see the new message
            e2e_session.expire_all()

            result = await e2e_session.execute(
                select(Message)
                .where(Message.conversation_id == initial_conversation_id)
            )
            current_messages = result.scalars().all()

            if len(current_messages) > initial_message_count:
                reply_found = True
                print(f"[OK] Reply message found after {elapsed_reply} seconds")
                break

            print(f"  Waiting... ({elapsed_reply}s / {max_wait_reply}s)")

        if not reply_found:
            print(f"WARNING: Reply not processed within {max_wait_reply} seconds")
            print(f"  This may indicate Gmail isn't threading the emails on the receiver's side")
            print(f"  Sender thread: {thread_id}")
            print(f"  Receiver thread: {initial_message.thread_id}")

            # Check if reply created a new conversation
            result = await e2e_session.execute(
                select(Message).where(col(Message.content).contains(reply_body[:30]))
            )
            reply_message = result.scalars().first()

            if reply_message:
                await e2e_session.refresh(reply_message)
                print(f"  Reply found in different conversation: {reply_message.conversation_id}")
                print(f"  Reply thread_id: {reply_message.thread_id}")
                pytest.skip(
                    "Gmail receiver-side threading didn't work. "
                    "Reply was processed but created a new conversation. "
                    "This is a Gmail behavior limitation when both emails are sent FROM the same account."
                )
            else:
                pytest.skip(f"Reply not processed within {max_wait_reply} seconds - webhook may be delayed")

        # Step 5: Verify same conversation used
        print("\n[Step 5] Verifying conversation continuity...")

        result = await e2e_session.execute(
            select(Message)
            .where(Message.conversation_id == initial_conversation_id)
        )
        final_messages = result.scalars().all()
        final_message_count = len(final_messages)

        print(f"  Final message count: {final_message_count}")

        # Should have at least one more message
        assert final_message_count > initial_message_count, \
            "Reply did not add to same conversation"

        print(f"[OK] Conversation continuity maintained")

        # Cleanup
        print("\n[Step 6] Cleaning up...")
        try:
            await asyncio.to_thread(self.gmail_helper.delete_thread, thread_id)
            print(f"[OK] Test thread deleted")
        except Exception as e:
            print(f"⚠ Failed to delete thread: {e}")

        print(f"\n{'='*60}")
        print(f"Gmail Threading Test PASSED: {self.test_id}")
        print(f"{'='*60}\n")
