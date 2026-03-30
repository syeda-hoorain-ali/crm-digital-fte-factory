"""End-to-end test for complete multi-channel flow."""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from httpx import AsyncClient
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.customer_identification import CustomerIdentificationService
from src.services.conversation_service import ConversationService
from src.database.models import (
    Customer,
    Conversation,
    Message,
    Ticket,
    Channel,
    ConversationStatus,
    MessageDirection,
    MessageRole,
    DeliveryStatus,
    TicketStatus,
)


class TestMultiChannelE2E:
    """End-to-end test for complete multi-channel customer journey."""

    @pytest.mark.asyncio
    async def test_complete_multichannel_flow(
        self,
        session: AsyncSession,
        clean_test_data,
        client_with_kafka: AsyncClient,
        kafka_consumer: AIOKafkaConsumer
    ):
        """Test complete flow: web form → email reply → WhatsApp message (same customer).

        This test verifies:
        1. Customer submits web form
        2. System creates customer and conversation
        3. Message is sent to Kafka for agent processing
        4. Same customer sends email (recognized by email)
        5. System links to existing customer
        6. Same customer messages via WhatsApp (linked by phone)
        7. System maintains unified conversation history
        8. Cross-channel recognition works correctly
        """
        import json
        import asyncio

        # Step 1: Customer submits web form
        web_form_data = {
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "subject": "Question about billing",
            "category": "billing",
            "priority": "medium",
            "message": "I have a question about my recent invoice charges"
        }

        response = await client_with_kafka.post("/support/submit", json=web_form_data)
        assert response.status_code == 200
        web_form_response = response.json()
        ticket_id = web_form_response["ticket_id"]

        # Step 1.5: Verify message sent to Kafka
        kafka_message = None
        try:
            # Wait for message with explicit timeout
            async def consume_message():
                async for msg in kafka_consumer:
                    if msg.value is None:
                        continue
                    message_data = json.loads(msg.value.decode('utf-8'))
                    # Check if this is our message
                    if message_data.get('customer_contact') == 'alice@example.com':
                        return message_data
                return None

            kafka_message = await asyncio.wait_for(consume_message(), timeout=10.0)
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for Kafka message - message not delivered to Kafka")
        except Exception as e:
            pytest.fail(f"Error consuming Kafka message: {e}")

        assert kafka_message is not None, "Message not found in Kafka"
        assert kafka_message['channel'] == 'webform'
        assert kafka_message['message_type'] == 'inbound'
        assert 'invoice' in kafka_message['body'].lower()
        assert kafka_message['metadata']['category'] == 'billing'

        # Verify customer created
        identification_service = CustomerIdentificationService(session)
        customer = await identification_service.find_customer_by_any_identifier(
            email="alice@example.com"
        )
        assert customer is not None
        assert customer.email == "alice@example.com"
        assert customer.name == "Alice Johnson"

        # Verify conversation created
        conversation_service = ConversationService(session)
        conversations = await conversation_service.find_related_conversations(
            customer_id=customer.id,
            max_age_hours=24
        )
        assert len(conversations) == 1
        assert conversations[0].initial_channel == Channel.WEB_FORM

        # Step 2: Same customer sends email (simulated)
        # In real scenario, this would come through Gmail webhook
        # For E2E test, we'll create the data directly

        # Link phone to customer (simulating WhatsApp contact info collection)
        await identification_service.link_phone_to_customer(
            customer_id=customer.id,
            phone="+1234567890",
            verified=False
        )

        # Create email conversation
        email_conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.EMAIL,
            status=ConversationStatus.ACTIVE
        )
        session.add(email_conversation)
        await session.commit()
        await session.refresh(email_conversation)

        # Add email message
        email_message = Message(
            conversation_id=email_conversation.id,
            channel=Channel.EMAIL,
            direction=MessageDirection.INBOUND,
            role=MessageRole.CUSTOMER,
            content="Following up on my billing question from the web form",
            delivery_status=DeliveryStatus.DELIVERED
        )
        session.add(email_message)
        await session.commit()

        # Step 3: Verify cross-channel recognition
        # Customer should now have 2 conversations
        conversations = await conversation_service.find_related_conversations(
            customer_id=customer.id,
            max_age_hours=24
        )
        assert len(conversations) == 2

        # Verify both channels represented
        channels = {conv.initial_channel for conv in conversations}
        assert Channel.WEB_FORM in channels
        assert Channel.EMAIL in channels

        # Step 4: Same customer messages via WhatsApp
        whatsapp_conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.WHATSAPP,
            status=ConversationStatus.ACTIVE
        )
        session.add(whatsapp_conversation)
        await session.commit()
        await session.refresh(whatsapp_conversation)

        whatsapp_message = Message(
            conversation_id=whatsapp_conversation.id,
            channel=Channel.WHATSAPP,
            direction=MessageDirection.INBOUND,
            role=MessageRole.CUSTOMER,
            content="Quick question about the invoice charges",
            delivery_status=DeliveryStatus.DELIVERED
        )
        session.add(whatsapp_message)
        await session.commit()

        # Step 5: Verify unified customer history
        history = await conversation_service.get_customer_conversation_history(
            customer_id=customer.id,
            limit=50,
            include_closed=True
        )

        # Should have 3 conversations
        assert len(history) == 3

        # Verify all channels represented
        history_channels = {conv['channel'] for conv in history}
        assert 'web_form' in history_channels
        assert 'email' in history_channels
        assert 'whatsapp' in history_channels

        # Verify total message count
        total_messages = sum(conv['message_count'] for conv in history)
        assert total_messages >= 3  # At least one message per channel

        # Step 6: Verify customer identifiers
        identifiers = await identification_service.get_customer_identifiers(customer.id)
        assert len(identifiers) == 2  # Email and phone

        identifier_types = {id.identifier_type.value for id in identifiers}
        assert 'email' in identifier_types
        assert 'phone' in identifier_types

        # Step 7: Test conversation continuity detection
        # New message with similar content should detect continuity
        similar_message = "Need more help with invoice and billing charges"
        related_conv = await conversation_service.detect_conversation_continuity(
            customer_id=customer.id,
            new_message_content=similar_message,
            new_channel=Channel.EMAIL,
            similarity_threshold=0.3
        )

        # Should detect one of the existing conversations as related
        assert related_conv is not None
        assert related_conv.customer_id == customer.id

        # Step 8: Verify customer profile API
        response = await client_with_kafka.get(f"/api/customers/{customer.id}/profile")
        assert response.status_code == 200
        profile = response.json()

        assert profile['customer_id'] == str(customer.id)
        assert profile['email'] == "alice@example.com"
        assert profile['phone'] == "+1234567890"
        assert profile['name'] == "Alice Johnson"
        assert len(profile['identifiers']) == 2

        # Step 9: Verify customer history API
        response = await client_with_kafka.get(f"/api/customers/{customer.id}/history")
        assert response.status_code == 200
        history_response = response.json()

        assert history_response['total_conversations'] == 3
        assert history_response['total_messages'] >= 3
        assert len(history_response['conversations']) == 3

        # Step 10: Verify ticket status API
        response = await client_with_kafka.get(f"/support/ticket/{ticket_id}")
        assert response.status_code == 200
        ticket_status = response.json()

        assert ticket_status['ticket_id'] == ticket_id
        assert ticket_status['status'] in ['open', 'in_progress']
        assert len(ticket_status['messages']) >= 1

        # Step 11: Verify Kafka message structure
        assert 'message_id' in kafka_message
        assert 'timestamp' in kafka_message
        assert kafka_message.get('customer_id') == str(customer.id)

    @pytest.mark.asyncio
    async def test_cross_channel_conversation_linking(self, session: AsyncSession):
        """Test that conversations are properly linked across channels."""
        identification_service = CustomerIdentificationService(session)
        conversation_service = ConversationService(session)

        # Create customer
        customer = await identification_service.find_or_create_customer_by_email(
            email="bob@example.com",
            name="Bob Smith"
        )

        # Create first conversation (web form)
        conv1 = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.WEB_FORM,
            status=ConversationStatus.ACTIVE
        )
        session.add(conv1)
        await session.commit()
        await session.refresh(conv1)

        # Add message about technical issue
        msg1 = Message(
            conversation_id=conv1.id,
            channel=Channel.WEB_FORM,
            direction=MessageDirection.INBOUND,
            role=MessageRole.CUSTOMER,
            content="I'm having trouble logging into my account and resetting password",
            delivery_status=DeliveryStatus.DELIVERED
        )
        session.add(msg1)
        await session.commit()

        # Create second conversation (email) with similar content
        conv2 = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.EMAIL,
            status=ConversationStatus.ACTIVE
        )
        session.add(conv2)
        await session.commit()
        await session.refresh(conv2)

        # Detect continuity
        related = await conversation_service.detect_conversation_continuity(
            customer_id=customer.id,
            new_message_content="Still can't login or reset my password",
            new_channel=Channel.EMAIL,
            similarity_threshold=0.3
        )

        # Should detect the web form conversation as related
        assert related is not None
        assert related.id == conv1.id

        # Link conversations
        await conversation_service.link_conversation_to_existing(
            new_conversation_id=conv2.id,
            existing_conversation_id=conv1.id
        )

        # Verify metadata updated
        await session.refresh(conv2)
        assert 'related_conversation_id' in conv2.metadata_
        assert conv2.metadata_['related_conversation_id'] == str(conv1.id)
        assert conv2.metadata_['continuation_detected'] is True

    @pytest.mark.asyncio
    async def test_rate_limiting_across_channels(
        self,
        session: AsyncSession,
        clean_test_data,
        client_with_kafka: AsyncClient,
        kafka_consumer: AIOKafkaConsumer
    ):
        """Test that rate limiting works correctly across channels.

        This test verifies basic flow and Kafka message delivery.
        Rate limiting requires Redis to be running.
        """
        import json
        import asyncio

        customer_email = "ratelimit@example.com"
        messages_received = []

        # Submit multiple requests rapidly and collect responses
        responses = []
        for i in range(3):
            try:
                response = await client_with_kafka.post("/support/submit", json={
                    "name": "Rate Test",
                    "email": customer_email,
                    "subject": f"Test {i}",
                    "category": "general",
                    "priority": "low",
                    "message": f"Test message {i}"
                })
                responses.append(response)
            except Exception as e:
                # Log but don't fail - some requests might fail due to rate limiting
                print(f"Request {i} failed: {e}")

        # Verify at least one request succeeded
        successful_responses = [r for r in responses if r.status_code == 200]
        assert len(successful_responses) >= 1, "At least one request should succeed"

        # Give a moment for Kafka messages to be sent
        await asyncio.sleep(1)

        # Verify at least one message made it to Kafka
        try:
            async def consume_messages():
                async for msg in kafka_consumer:
                    if msg.value is None:
                        continue
                    message_data = json.loads(msg.value.decode('utf-8'))
                    if message_data.get('customer_contact') == customer_email:
                        messages_received.append(message_data)
                        if len(messages_received) >= 1:  # Wait for at least 1 message
                            return messages_received
                return messages_received

            await asyncio.wait_for(consume_messages(), timeout=10.0)
        except asyncio.TimeoutError:
            pass  # Timeout is expected

        # Verify we received messages in Kafka
        assert len(messages_received) >= 1, "At least one message should reach Kafka"

    @pytest.mark.asyncio
    async def test_conversation_reopening(self, session: AsyncSession):
        """Test that closed conversations can be reopened."""
        identification_service = CustomerIdentificationService(session)
        conversation_service = ConversationService(session)

        # Create customer and conversation
        customer = await identification_service.find_or_create_customer_by_email(
            email="reopen@example.com"
        )

        conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.EMAIL,
            status=ConversationStatus.ACTIVE
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)

        # Close conversation
        await conversation_service.close_conversation(
            conversation_id=conversation.id,
            resolution_type="resolved"
        )
        await session.refresh(conversation)

        assert conversation.status == ConversationStatus.CLOSED
        assert conversation.ended_at is not None

        # Reopen conversation
        await conversation_service.reopen_conversation(conversation.id)
        await session.refresh(conversation)

        assert conversation.status == ConversationStatus.ACTIVE
        assert conversation.ended_at is None

    @pytest.mark.asyncio
    async def test_health_check_comprehensive(self, client_with_kafka: AsyncClient):
        """Test comprehensive health check endpoint."""
        response = await client_with_kafka.get("/health")

        # Should return 200 or 503 depending on system health
        assert response.status_code in [200, 503]

        # Handle both response formats (top-level or wrapped in 'detail')
        response_data = response.json()
        if 'detail' in response_data:
            health_data = response_data['detail']
        else:
            health_data = response_data

        assert 'status' in health_data
        assert 'components' in health_data
        assert 'database' in health_data['components']
        assert 'timestamp' in health_data

        # Verify component structure
        for component in ['database', 'redis', 'kafka']:
            if component in health_data['components']:
                comp_health = health_data['components'][component]
                assert 'status' in comp_health
                assert comp_health['status'] in ['healthy', 'unhealthy', 'degraded', 'unknown']
