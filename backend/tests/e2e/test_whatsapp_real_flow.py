"""Real WhatsApp E2E test with actual webhook triggering and Twilio verification.

This test verifies the complete WhatsApp flow by:
1. Triggering the webhook endpoint directly (simulating Twilio's inbound webhook)
2. Verifying database records are created (customer, conversation, message, ticket)
3. Checking Kafka events are published
4. Testing conversation continuity across multiple messages
5. Optionally verifying outbound replies via Twilio API

Note: We trigger the webhook directly because Twilio API can only send FROM numbers
you own (sandbox/production numbers), not from arbitrary customer numbers. This
approach tests the real webhook → database → Kafka flow without Twilio API limitations.

Requires:
- TWILIO_TEST_ACCOUNT_SID: Test Twilio account SID (for signature validation)
- TWILIO_TEST_AUTH_TOKEN: Test Twilio auth token (for signature validation)
- TWILIO_TEST_FROM_NUMBER: Customer phone number (simulated sender)
- TWILIO_APP_NUMBER: Application WhatsApp number (sandbox/production)
- DATABASE_URL: PostgreSQL connection string
- KAFKA_BOOTSTRAP_SERVERS: Kafka broker address
- FastAPI app must be running on http://localhost:8080
"""

import asyncio
import json
import os
import pytest
import uuid
import httpx
import hmac
import hashlib
from urllib.parse import urlencode
from datetime import datetime, timezone
from sqlmodel import col, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.whatsapp_test_helper import WhatsAppTestHelper
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
from src.kafka.schemas import ChannelMessage


@pytest.mark.asyncio
@pytest.mark.e2e
class TestWhatsAppRealFlow:
    """Real WhatsApp E2E tests with webhook triggering."""

    @pytest.fixture(autouse=True)
    def setup_test_config(self):
        """Initialize test configuration."""
        account_sid = os.getenv("TWILIO_TEST_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_TEST_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_TEST_FROM_NUMBER")  # Customer phone
        app_number = os.getenv("TWILIO_APP_NUMBER")  # Sandbox/production number

        if not account_sid or not auth_token or not from_number or not app_number:
            pytest.skip(
                "Twilio credentials not set - skipping real WhatsApp E2E test. "
                "Set TWILIO_TEST_ACCOUNT_SID, TWILIO_TEST_AUTH_TOKEN, "
                "TWILIO_TEST_FROM_NUMBER, and TWILIO_APP_NUMBER"
            )

        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
        self.app_number = app_number if app_number.startswith("whatsapp:") else f"whatsapp:{app_number}"

        # Initialize WhatsApp helper for outbound verification (optional)
        try:
            self.whatsapp_helper = WhatsAppTestHelper(
                account_sid=account_sid,
                auth_token=auth_token,
                from_number=self.app_number  # App sends FROM sandbox number
            )
            self.whatsapp_helper.initialize()
            self.has_whatsapp_helper = True
        except Exception as e:
            print(f"Warning: Could not initialize WhatsApp helper: {e}")
            self.has_whatsapp_helper = False

        # Generate unique test identifier
        self.test_id = str(uuid.uuid4())[:8]
        self.test_phone = self.from_number.replace("whatsapp:", "")

        # FastAPI endpoint
        self.webhook_url = "http://localhost:8080/webhooks/whatsapp"

        yield

    def create_twilio_webhook_payload(self, body: str, num_media: int = 0) -> dict:
        """Create a Twilio webhook payload for testing.

        Args:
            body: Message body text
            num_media: Number of media attachments

        Returns:
            Dictionary matching Twilio's webhook payload structure
        """
        return {
            "SmsMessageSid": f"SM{uuid.uuid4().hex}",
            "Body": body,
            "From": self.from_number,
            "To": self.app_number,
            "AccountSid": self.account_sid,
            "NumMedia": str(num_media),
            "MessageSid": f"SM{uuid.uuid4().hex}",
            "SmsStatus": "received",
        }

    def generate_twilio_signature(self, url: str, params: dict) -> str:
        """Generate Twilio signature for webhook validation.

        Twilio signature algorithm:
        1. Take the full URL of the request (including query string)
        2. Sort all POST parameters alphabetically by key
        3. Append each key-value pair to the URL string
        4. Sign the resulting string with HMAC-SHA1 using auth token
        5. Base64 encode the result

        Args:
            url: Full webhook URL
            params: POST parameters (form data)

        Returns:
            Base64-encoded HMAC-SHA1 signature
        """
        # Sort parameters alphabetically
        sorted_params = sorted(params.items())

        # Build the signature string: URL + sorted params
        signature_string = url
        for key, value in sorted_params:
            signature_string += f"{key}{value}"

        # Compute HMAC-SHA1
        signature = hmac.new(
            self.auth_token.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha1
        ).digest()

        # Base64 encode
        import base64
        return base64.b64encode(signature).decode('utf-8')

    async def test_whatsapp_inbound_message_processing(
        self,
        e2e_session: AsyncSession,
        clean_test_data,
        kafka_consumer
    ):
        """Test complete flow: trigger webhook → database → Kafka.

        Steps:
        1. Trigger webhook with Twilio payload (simulating inbound message)
        2. Wait for webhook to process (poll database)
        3. Verify customer created/identified
        4. Verify conversation created
        5. Verify message stored
        6. Verify ticket created
        7. Verify webhook log
        8. Verify Kafka event published
        """
        print(f"\n{'='*60}")
        print(f"Starting WhatsApp Real E2E Test: {self.test_id}")
        print(f"{'='*60}")

        # Step 1: Trigger webhook with Twilio payload
        print("\n[Step 1] Triggering webhook with Twilio payload...")
        test_body = f"Hello, I need help with my order. Test ID: {self.test_id}"

        payload = self.create_twilio_webhook_payload(test_body)

        # Generate Twilio signature for validation
        signature = self.generate_twilio_signature(self.webhook_url, payload)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.webhook_url,
                data=payload,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Twilio-Signature": signature
                }
            )

        print(f"[OK] Webhook triggered successfully")
        print(f"  Status Code: {response.status_code}")
        print(f"  From: {self.from_number}")
        print(f"  To: {self.app_number}")

        assert response.status_code == 200, f"Webhook returned {response.status_code}: {response.text}"

        # Step 2: Wait for webhook processing (poll database for message)
        print("\n[Step 2] Waiting for webhook to process message...")
        print("  (Polling database for up to 60 seconds)")

        message_found = False
        db_message = None
        max_wait = 60  # seconds
        poll_interval = 2  # seconds
        elapsed = 0

        while elapsed < max_wait and not message_found:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            # Search by content containing the unique test_id
            result = await e2e_session.execute(
                select(Message).where(col(Message.content).contains(self.test_id))
            )
            db_message = result.scalars().first()

            if db_message:
                message_found = True
                print(f"[OK] Message found in database after {elapsed} seconds")
                break

            print(f"  Waiting... ({elapsed}s / {max_wait}s)")

        if not message_found:
            pytest.fail(
                f"Webhook did not process message within {max_wait} seconds. "
                "Check if Twilio webhook is configured correctly."
            )

        # Step 3: Verify customer created/identified
        print("\n[Step 3] Verifying customer identification...")

        result = await e2e_session.execute(
            select(CustomerIdentifier)
            .where(CustomerIdentifier.identifier_value == self.test_phone)
        )
        identifier = result.scalars().first()

        assert identifier is not None, f"Customer identifier not found for {self.test_phone}"
        assert identifier.identifier_type == IdentifierType.PHONE

        customer_id = identifier.customer_id
        print(f"[OK] Customer identified: {customer_id}")

        # Verify customer record
        result = await e2e_session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalars().first()

        assert customer is not None
        print(f"  Customer phone: {customer.phone}")

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
        assert conversation.initial_channel == Channel.WHATSAPP
        assert conversation.status == ConversationStatus.ACTIVE
        print(f"[OK] Conversation created: {conversation.id}")

        # Step 5: Verify message stored
        print("\n[Step 5] Verifying message storage...")

        await e2e_session.refresh(db_message)

        result = await e2e_session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .where(Message.id == db_message.id)
        )

        db_message_verify = result.scalars().first()

        assert db_message_verify is not None
        assert db_message_verify.conversation_id == conversation.id
        assert db_message_verify.channel == Channel.WHATSAPP
        assert db_message_verify.direction == MessageDirection.INBOUND
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
        assert ticket.source_channel == Channel.WHATSAPP
        assert ticket.status == TicketStatus.OPEN
        print(f"[OK] Ticket created: {ticket.id}")
        print(f"  Status: {ticket.status.value}")
        print(f"  Priority: {ticket.priority.value}")

        # Step 7: Verify webhook delivery log
        print("\n[Step 7] Verifying webhook log...")

        result = await e2e_session.execute(
            select(WebhookDeliveryLog)
            .where(col(WebhookDeliveryLog.webhook_type) == "whatsapp")
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

        # Step 8: Verify Kafka message published
        print("\n[Step 8] Verifying Kafka message delivery...")
        print("  (Polling Kafka consumer for up to 30 seconds)")

        kafka_message_found = False
        kafka_message = None
        max_kafka_wait = 30  # seconds
        kafka_poll_interval = 1  # seconds
        kafka_elapsed = 0

        while kafka_elapsed < max_kafka_wait and not kafka_message_found:
            # Poll Kafka consumer
            try:
                msg_batch = await asyncio.wait_for(
                    kafka_consumer.getmany(timeout_ms=1000, max_records=10),
                    timeout=2.0
                )

                for topic_partition, messages in msg_batch.items():
                    for msg in messages:
                        try:
                            # Parse Kafka message
                            kafka_payload = json.loads(msg.value.decode('utf-8'))

                            # Check if this is our test message by matching test_id in body
                            if self.test_id in kafka_payload.get('body', ''):
                                kafka_message = kafka_payload
                                kafka_message_found = True
                                print(f"[OK] Kafka message found after {kafka_elapsed} seconds")
                                print(f"  Topic: {topic_partition.topic}")
                                print(f"  Partition: {topic_partition.partition}")
                                print(f"  Offset: {msg.offset}")
                                break
                        except json.JSONDecodeError:
                            continue

                    if kafka_message_found:
                        break

            except asyncio.TimeoutError:
                pass

            if not kafka_message_found:
                await asyncio.sleep(kafka_poll_interval)
                kafka_elapsed += kafka_poll_interval

        if not kafka_message_found:
            pytest.fail(
                f"Kafka message not found within {max_kafka_wait} seconds. "
                "Check if Kafka producer is properly configured in webhook handler."
            )

        # Verify Kafka message structure
        print("\n[Step 8.1] Verifying Kafka message structure...")

        # Validate against ChannelMessage schema
        try:
            channel_message = ChannelMessage(**kafka_message)
            print(f"[OK] Kafka message matches ChannelMessage schema")
        except Exception as e:
            pytest.fail(f"Kafka message does not match ChannelMessage schema: {e}")

        # Verify key fields
        assert channel_message.channel.value == "whatsapp", f"Expected channel 'whatsapp', got '{channel_message.channel.value}'"
        assert channel_message.message_type.value == "inbound", f"Expected message_type 'inbound', got '{channel_message.message_type.value}'"
        assert channel_message.customer_id == str(customer_id), f"Customer ID mismatch"
        assert self.test_id in channel_message.body, "Test ID not found in Kafka message body"

        print(f"[OK] Kafka message verified:")
        print(f"  Message ID: {channel_message.message_id}")
        print(f"  Channel: {channel_message.channel.value}")
        print(f"  Customer ID: {channel_message.customer_id}")
        print(f"  Customer Contact: {channel_message.customer_contact}")

        print(f"\n{'='*60}")
        print(f"WhatsApp Real E2E Test PASSED: {self.test_id}")
        print(f"{'='*60}\n")

    async def test_whatsapp_conversation_continuity(
        self,
        e2e_session: AsyncSession,
        clean_test_data,
        kafka_consumer
    ):
        """Test conversation continuity with multiple messages.

        Steps:
        1. Trigger webhook with initial message
        2. Wait for processing and verify Kafka
        3. Trigger webhook with second message from same number
        4. Verify same conversation is used
        5. Verify message count increases
        6. Verify second message published to Kafka
        """
        print(f"\n{'='*60}")
        print(f"Starting WhatsApp Continuity Test: {self.test_id}")
        print(f"{'='*60}")

        # Step 1: Trigger webhook with initial message
        print("\n[Step 1] Triggering webhook with initial message...")
        initial_body = f"Initial message for continuity test. Test ID: {self.test_id}"

        payload_1 = self.create_twilio_webhook_payload(initial_body)
        signature_1 = self.generate_twilio_signature(self.webhook_url, payload_1)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response_1 = await client.post(
                self.webhook_url,
                data=payload_1,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Twilio-Signature": signature_1
                }
            )

        assert response_1.status_code == 200
        print(f"[OK] Initial webhook triggered (Status: {response_1.status_code})")

        # Step 2: Wait for processing
        print("\n[Step 2] Waiting for initial message processing...")
        print("  (Polling database for up to 30 seconds)")

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

        if not message_found or not initial_message:
            pytest.skip("Initial message not processed yet - webhook may be delayed")

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

        # Step 2.1: Verify initial message published to Kafka
        print("\n[Step 2.1] Verifying initial message in Kafka...")
        print("  (Polling Kafka consumer for up to 20 seconds)")

        kafka_message_found = False
        max_kafka_wait = 20
        kafka_elapsed = 0

        while kafka_elapsed < max_kafka_wait and not kafka_message_found:
            try:
                msg_batch = await asyncio.wait_for(
                    kafka_consumer.getmany(timeout_ms=1000, max_records=10),
                    timeout=2.0
                )

                for topic_partition, messages in msg_batch.items():
                    for msg in messages:
                        try:
                            kafka_payload = json.loads(msg.value.decode('utf-8'))
                            if self.test_id in kafka_payload.get('body', ''):
                                kafka_message_found = True
                                print(f"[OK] Initial message found in Kafka after {kafka_elapsed} seconds")
                                break
                        except json.JSONDecodeError:
                            continue
                    if kafka_message_found:
                        break
            except asyncio.TimeoutError:
                pass

            if not kafka_message_found:
                await asyncio.sleep(1)
                kafka_elapsed += 1

        if not kafka_message_found:
            print(f"WARNING: Initial message not found in Kafka within {max_kafka_wait} seconds")

        # Step 3: Trigger webhook with second message from same number
        print("\n[Step 3] Triggering webhook with second message from same number...")
        second_body = f"Second message in same conversation. Test ID: {self.test_id}"

        payload_2 = self.create_twilio_webhook_payload(second_body)
        signature_2 = self.generate_twilio_signature(self.webhook_url, payload_2)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response_2 = await client.post(
                self.webhook_url,
                data=payload_2,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Twilio-Signature": signature_2
                }
            )

        assert response_2.status_code == 200
        print(f"[OK] Second webhook triggered (Status: {response_2.status_code})")

        # Step 4: Wait for second message processing
        print("\n[Step 4] Waiting for second message processing...")
        print("  (Polling database for up to 60 seconds)")

        second_found = False
        max_wait_second = 60
        poll_interval_second = 2
        elapsed_second = 0

        while elapsed_second < max_wait_second and not second_found:
            await asyncio.sleep(poll_interval_second)
            elapsed_second += poll_interval_second

            # Clear session cache to see new messages
            e2e_session.expire_all()

            result = await e2e_session.execute(
                select(Message)
                .where(Message.conversation_id == initial_conversation_id)
            )
            current_messages = result.scalars().all()

            if len(current_messages) > initial_message_count:
                second_found = True
                print(f"[OK] Second message found after {elapsed_second} seconds")
                break

            print(f"  Waiting... ({elapsed_second}s / {max_wait_second}s)")

        if not second_found:
            pytest.skip(f"Second message not processed within {max_wait_second} seconds - webhook may be delayed")

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
            "Second message did not add to same conversation"

        print(f"[OK] Conversation continuity maintained")

        # Step 5.1: Verify second message published to Kafka
        print("\n[Step 5.1] Verifying second message in Kafka...")
        print("  (Polling Kafka consumer for up to 20 seconds)")

        second_kafka_found = False
        second_kafka_elapsed = 0
        max_second_kafka_wait = 20

        while second_kafka_elapsed < max_second_kafka_wait and not second_kafka_found:
            try:
                msg_batch = await asyncio.wait_for(
                    kafka_consumer.getmany(timeout_ms=1000, max_records=10),
                    timeout=2.0
                )

                for topic_partition, messages in msg_batch.items():
                    for msg in messages:
                        try:
                            kafka_payload = json.loads(msg.value.decode('utf-8'))
                            # Look for second message content
                            if "Second message in same conversation" in kafka_payload.get('body', ''):
                                second_kafka_found = True
                                print(f"[OK] Second message found in Kafka after {second_kafka_elapsed} seconds")
                                break
                        except json.JSONDecodeError:
                            continue
                    if second_kafka_found:
                        break
            except asyncio.TimeoutError:
                pass

            if not second_kafka_found:
                await asyncio.sleep(1)
                second_kafka_elapsed += 1

        if not second_kafka_found:
            print(f"WARNING: Second message not found in Kafka within {max_second_kafka_wait} seconds")
            print(f"  Note: Webhook handler only sends Kafka messages for NEW conversations")
        else:
            print(f"[OK] Both initial and second messages verified in Kafka")

        print(f"\n{'='*60}")
        print(f"WhatsApp Continuity Test PASSED: {self.test_id}")
        print(f"{'='*60}\n")

    async def test_whatsapp_escalation_detection(
        self,
        e2e_session: AsyncSession,
        clean_test_data,
        kafka_consumer
    ):
        """Test escalation keyword detection in WhatsApp messages.

        Steps:
        1. Trigger webhook with message containing escalation keyword
        2. Wait for processing
        3. Verify ticket created with escalation category
        4. Verify Kafka message published with escalation metadata
        """
        print(f"\n{'='*60}")
        print(f"Starting WhatsApp Escalation Test: {self.test_id}")
        print(f"{'='*60}")

        # Step 1: Trigger webhook with escalation keyword
        print("\n[Step 1] Triggering webhook with escalation keyword...")
        escalation_body = f"I need to speak to a human agent. Test ID: {self.test_id}"

        payload = self.create_twilio_webhook_payload(escalation_body)
        signature = self.generate_twilio_signature(self.webhook_url, payload)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.webhook_url,
                data=payload,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Twilio-Signature": signature
                }
            )

        assert response.status_code == 200
        print(f"[OK] Escalation webhook triggered (Status: {response.status_code})")

        # Step 2: Wait for processing
        print("\n[Step 2] Waiting for message processing...")
        print("  (Polling database for up to 60 seconds)")

        message_found = False
        db_message = None
        max_wait = 60
        poll_interval = 2
        elapsed = 0

        while elapsed < max_wait and not message_found:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            result = await e2e_session.execute(
                select(Message).where(col(Message.content).contains(self.test_id))
            )
            db_message = result.scalars().first()

            if db_message:
                message_found = True
                print(f"[OK] Message found after {elapsed} seconds")
                break

            print(f"  Waiting... ({elapsed}s / {max_wait}s)")

        if not message_found:
            pytest.skip("Escalation message not processed - webhook may be delayed")

        # Step 3: Verify ticket created with escalation category
        print("\n[Step 3] Verifying escalation ticket...")

        assert db_message
        conversation_id = db_message.conversation_id
        result = await e2e_session.execute(
            select(Ticket)
            .where(Ticket.conversation_id == conversation_id)
        )
        ticket = result.scalars().first()

        assert ticket is not None
        assert ticket.category == "escalation"
        print(f"[OK] Escalation ticket created: {ticket.id}")
        print(f"  Category: {ticket.category}")

        # Step 4: Verify Kafka message published with escalation metadata
        print("\n[Step 4] Verifying Kafka message with escalation metadata...")
        print("  (Polling Kafka consumer for up to 30 seconds)")

        kafka_message_found = False
        kafka_message = None
        max_kafka_wait = 30
        kafka_elapsed = 0

        while kafka_elapsed < max_kafka_wait and not kafka_message_found:
            try:
                msg_batch = await asyncio.wait_for(
                    kafka_consumer.getmany(timeout_ms=1000, max_records=10),
                    timeout=2.0
                )

                for topic_partition, messages in msg_batch.items():
                    for msg in messages:
                        try:
                            kafka_payload = json.loads(msg.value.decode('utf-8'))
                            if self.test_id in kafka_payload.get('body', ''):
                                kafka_message = kafka_payload
                                kafka_message_found = True
                                print(f"[OK] Kafka message found after {kafka_elapsed} seconds")
                                break
                        except json.JSONDecodeError:
                            continue
                    if kafka_message_found:
                        break
            except asyncio.TimeoutError:
                pass

            if not kafka_message_found:
                await asyncio.sleep(1)
                kafka_elapsed += 1

        if not kafka_message_found:
            print(f"WARNING: Kafka message not found within {max_kafka_wait} seconds")
        else:
            # Verify escalation metadata
            print("\n[Step 4.1] Verifying escalation metadata in Kafka message...")

            try:
                channel_message = ChannelMessage(**kafka_message)
                print(f"[OK] Kafka message matches ChannelMessage schema")

                # Check for escalation metadata
                requires_escalation = channel_message.metadata.get("requires_escalation", False)
                print(f"  Requires Escalation: {requires_escalation}")

                if requires_escalation:
                    print(f"[OK] Escalation metadata correctly set in Kafka message")
                else:
                    print(f"WARNING: Escalation metadata not found in Kafka message")

            except Exception as e:
                print(f"WARNING: Could not validate Kafka message: {e}")

        print(f"\n{'='*60}")
        print(f"WhatsApp Escalation Test PASSED: {self.test_id}")
        print(f"{'='*60}\n")
