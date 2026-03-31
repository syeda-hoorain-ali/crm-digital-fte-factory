"""Integration tests for web form support endpoints."""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlmodel import col, select

from src.main import app
from src.database.models import (
    Customer,
    Conversation,
    Message,
    Ticket,
    WebhookDeliveryLog,
    Channel,
    ConversationStatus,
    MessageDirection,
    MessageRole,
    DeliveryStatus,
    Priority,
    TicketStatus,
    WebhookProcessingStatus,
)
from src.database.connection import get_session


@pytest.mark.integration
@pytest.mark.database
class TestWebFormSubmitEndpoint:
    """Integration tests for POST /support/submit endpoint (T048)."""

    @pytest.mark.asyncio
    async def test_submit_success_creates_all_records(self, session):
        """Test successful submission creates customer, conversation, message, and ticket."""
        form_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "subject": "Need help with account setup",
            "category": "technical",
            "priority": "medium",
            "message": "I'm having trouble setting up my account. Can you help?"
        }

        with TestClient(app) as client:
            response = client.post("/support/submit", json=form_data)

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "ticket_id" in data
            assert "message" in data
            assert "estimated_response_time" in data
            assert data["estimated_response_time"] == "within 5 minutes"

            ticket_id = uuid.UUID(data["ticket_id"])

            # Verify database records
            async with get_session() as session:
                # Check customer created
                customer_result = await session.execute(
                    select(Customer).where(Customer.email == form_data["email"])
                )
                customer = customer_result.first()
                assert customer is not None
                assert customer.name == form_data["name"]
                assert customer.email == form_data["email"]

                # Check conversation created
                conversation_result = await session.execute(
                    select(Conversation).where(Conversation.customer_id == customer.id)
                )
                conversation = conversation_result.first()
                assert conversation is not None
                assert conversation.initial_channel == Channel.WEB_FORM
                assert conversation.status == ConversationStatus.ACTIVE

                # Check message created
                message_result = await session.execute(
                    select(Message).where(Message.conversation_id == conversation.id)
                )
                message = message_result.first()
                assert message is not None
                assert message.channel == Channel.WEB_FORM
                assert message.direction == MessageDirection.INBOUND
                assert message.role == MessageRole.CUSTOMER
                assert message.content == form_data["message"]
                assert message.delivery_status == DeliveryStatus.DELIVERED

                # Check ticket created
                ticket = await session.get(Ticket, ticket_id)
                assert ticket is not None
                assert ticket.conversation_id == conversation.id
                assert ticket.customer_id == customer.id
                assert ticket.source_channel == Channel.WEB_FORM
                assert ticket.category == form_data["category"]
                assert ticket.priority == Priority.MEDIUM
                assert ticket.status == TicketStatus.OPEN

    @pytest.mark.asyncio
    async def test_submit_creates_webhook_delivery_log(self, session):
        """Test submission creates WebhookDeliveryLog entry."""
        form_data = {
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "subject": "Billing question",
            "category": "billing",
            "priority": "low",
            "message": "I have a question about my recent invoice."
        }

        with TestClient(app) as client:
            response = client.post("/support/submit", json=form_data)

            assert response.status_code == 200

            # Verify webhook log created
            async with get_session() as session:
                webhook_log_result = await session.execute(
                    select(WebhookDeliveryLog)
                    .where(WebhookDeliveryLog.webhook_type == "webform")
                    .order_by(col(WebhookDeliveryLog.received_at).desc())
                )
                webhook_log = webhook_log_result.first()
                assert webhook_log is not None
                assert webhook_log.signature_valid is True
                assert webhook_log.processing_status == WebhookProcessingStatus.COMPLETED
                assert webhook_log.payload["email"] == form_data["email"]
                assert webhook_log.completed_at is not None

    @pytest.mark.asyncio
    async def test_submit_validation_error_missing_name(self):
        """Test submission with missing name field."""
        form_data = {
            "email": "test@example.com",
            "subject": "Test subject",
            "category": "general",
            "priority": "medium",
            "message": "Test message content"
        }

        with TestClient(app) as client:
            response = client.post("/support/submit", json=form_data)

            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_submit_validation_error_invalid_email(self):
        """Test submission with invalid email format."""
        form_data = {
            "name": "Test User",
            "email": "invalid-email",
            "subject": "Test subject",
            "category": "general",
            "priority": "medium",
            "message": "Test message content"
        }

        with TestClient(app) as client:
            response = client.post("/support/submit", json=form_data)

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_validation_error_short_message(self):
        """Test submission with message too short."""
        form_data = {
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Test subject",
            "category": "general",
            "priority": "medium",
            "message": "Short"  # Less than 10 characters
        }

        with TestClient(app) as client:
            response = client.post("/support/submit", json=form_data)

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_validation_error_invalid_category(self):
        """Test submission with invalid category."""
        form_data = {
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Test subject",
            "category": "invalid_category",
            "priority": "medium",
            "message": "Test message content"
        }

        with TestClient(app) as client:
            response = client.post("/support/submit", json=form_data)

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_validation_error_invalid_priority(self):
        """Test submission with invalid priority."""
        form_data = {
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Test subject",
            "category": "general",
            "priority": "invalid_priority",
            "message": "Test message content"
        }

        with TestClient(app) as client:
            response = client.post("/support/submit", json=form_data)

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_existing_customer_reuses_record(self, session):
        """Test submission with existing customer reuses customer record."""
        # Create existing customer using provided session fixture
        existing_customer = Customer(
            email="existing@example.com",
            name="Existing Customer",
            metadata_={"source": "previous"}
        )
        session.add(existing_customer)
        await session.commit()
        await session.refresh(existing_customer)
        existing_customer_id = existing_customer.id

        form_data = {
            "name": "Existing Customer",
            "email": "existing@example.com",
            "subject": "Follow-up question",
            "category": "general",
            "priority": "low",
            "message": "I have another question about my account."
        }

        with TestClient(app) as client:
            response = client.post("/support/submit", json=form_data)

            assert response.status_code == 200

            # Verify customer was reused, not created
            customer_result = await session.execute(
                select(Customer).where(Customer.email == form_data["email"])
            )
            customers = customer_result.scalars().all()
            assert len(customers) == 1
            assert customers[0].id == existing_customer_id

    @pytest.mark.asyncio
    @patch("src.api.webhooks.web_form.rate_limiter")
    async def test_submit_rate_limit_exceeded(self, mock_rate_limiter):
        """Test submission when rate limit is exceeded."""
        # Mock rate limiter to return exceeded
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=(False, 0))
        mock_rate_limiter.get_retry_after = AsyncMock(return_value=30)

        form_data = {
            "name": "Test User",
            "email": "ratelimited@example.com",
            "subject": "Test subject",
            "category": "general",
            "priority": "medium",
            "message": "Test message content"
        }

        with TestClient(app) as client:
            response = client.post("/support/submit", json=form_data)

            assert response.status_code == 429
            assert "Retry-After" in response.headers
            assert response.json()["detail"].startswith("Too many requests")

    @pytest.mark.asyncio
    async def test_submit_different_priorities(self):
        """Test submission with different priority levels."""
        priorities = ["low", "medium", "high", "critical"]

        for priority in priorities:
            form_data = {
                "name": f"Test User {priority}",
                "email": f"test-{priority}@example.com",
                "subject": f"Test {priority} priority",
                "category": "general",
                "priority": priority,
                "message": f"This is a {priority} priority request."
            }

            with TestClient(app) as client:
                response = client.post("/support/submit", json=form_data)

                assert response.status_code == 200
                data = response.json()
                assert "ticket_id" in data

                # Verify ticket priority
                ticket_id = uuid.UUID(data["ticket_id"])
                async with get_session() as session:
                    ticket = await session.get(Ticket, ticket_id)
                    assert ticket is not None
                    assert ticket.priority.value == priority


@pytest.mark.integration
@pytest.mark.database
class TestWebFormTicketStatusEndpoint:
    """Integration tests for GET /support/ticket/{ticket_id} endpoint (T048)."""

    @pytest.mark.asyncio
    async def test_get_ticket_status_success(self, session):
        """Test retrieving ticket status successfully."""
        # Create test data
        async with get_session() as session:
            customer = Customer(
                email="ticket-test@example.com",
                name="Ticket Test User"
            )
            session.add(customer)
            await session.commit()
            await session.refresh(customer)

            conversation = Conversation(
                customer_id=customer.id,
                initial_channel=Channel.WEB_FORM,
                status=ConversationStatus.ACTIVE
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

            message = Message(
                conversation_id=conversation.id,
                channel=Channel.WEB_FORM,
                direction=MessageDirection.INBOUND,
                role=MessageRole.CUSTOMER,
                content="Test message for ticket",
                delivery_status=DeliveryStatus.DELIVERED
            )
            session.add(message)

            ticket = Ticket(
                conversation_id=conversation.id,
                customer_id=customer.id,
                source_channel=Channel.WEB_FORM,
                category="general",
                priority=Priority.MEDIUM,
                status=TicketStatus.OPEN
            )
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            ticket_id = ticket.id

        with TestClient(app) as client:
            response = client.get(f"/support/ticket/{ticket_id}")

            assert response.status_code == 200
            data = response.json()

            assert data["ticket_id"] == str(ticket_id)
            assert data["status"] == "open"
            assert "created_at" in data
            assert "messages" in data
            assert len(data["messages"]) >= 1
            assert data["messages"][0]["content"] == "Test message for ticket"
            assert data["messages"][0]["role"] == "customer"

    @pytest.mark.asyncio
    async def test_get_ticket_status_not_found(self):
        """Test retrieving non-existent ticket."""
        fake_ticket_id = uuid.uuid4()

        with TestClient(app) as client:
            response = client.get(f"/support/ticket/{fake_ticket_id}")

            assert response.status_code == 404
            assert response.json()["detail"] == "Ticket not found"

    @pytest.mark.asyncio
    async def test_get_ticket_status_invalid_uuid(self):
        """Test retrieving ticket with invalid UUID format."""
        with TestClient(app) as client:
            response = client.get("/support/ticket/invalid-uuid-format")

            assert response.status_code == 400
            assert "Invalid ticket ID format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_ticket_status_multiple_messages(self, session):
        """Test retrieving ticket with multiple messages."""
        # Create test data with multiple messages
        async with get_session() as session:
            customer = Customer(
                email="multi-msg@example.com",
                name="Multi Message User"
            )
            session.add(customer)
            await session.commit()
            await session.refresh(customer)

            conversation = Conversation(
                customer_id=customer.id,
                initial_channel=Channel.WEB_FORM,
                status=ConversationStatus.ACTIVE
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

            # Create multiple messages
            messages_content = [
                ("customer", "Initial request"),
                ("agent", "Thank you for contacting us"),
                ("customer", "Follow-up question"),
            ]

            for role_str, content in messages_content:
                role = MessageRole.CUSTOMER if role_str == "customer" else MessageRole.AGENT
                direction = MessageDirection.INBOUND if role_str == "customer" else MessageDirection.OUTBOUND

                message = Message(
                    conversation_id=conversation.id,
                    channel=Channel.WEB_FORM,
                    direction=direction,
                    role=role,
                    content=content,
                    delivery_status=DeliveryStatus.DELIVERED
                )
                session.add(message)

            ticket = Ticket(
                conversation_id=conversation.id,
                customer_id=customer.id,
                source_channel=Channel.WEB_FORM,
                category="general",
                priority=Priority.MEDIUM,
                status=TicketStatus.OPEN
            )
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            ticket_id = ticket.id

        with TestClient(app) as client:
            response = client.get(f"/support/ticket/{ticket_id}")

            assert response.status_code == 200
            data = response.json()

            assert len(data["messages"]) == 3
            assert data["messages"][0]["content"] == "Initial request"
            assert data["messages"][1]["content"] == "Thank you for contacting us"
            assert data["messages"][2]["content"] == "Follow-up question"

    @pytest.mark.asyncio
    async def test_get_ticket_status_chronological_order(self, session):
        """Test messages are returned in chronological order."""
        async with get_session() as session:
            customer = Customer(
                email="chrono@example.com",
                name="Chrono User"
            )
            session.add(customer)
            await session.commit()
            await session.refresh(customer)

            conversation = Conversation(
                customer_id=customer.id,
                initial_channel=Channel.WEB_FORM,
                status=ConversationStatus.ACTIVE
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

            # Create messages with explicit ordering
            for i in range(5):
                message = Message(
                    conversation_id=conversation.id,
                    channel=Channel.WEB_FORM,
                    direction=MessageDirection.INBOUND,
                    role=MessageRole.CUSTOMER,
                    content=f"Message {i}",
                    delivery_status=DeliveryStatus.DELIVERED
                )
                session.add(message)

            ticket = Ticket(
                conversation_id=conversation.id,
                customer_id=customer.id,
                source_channel=Channel.WEB_FORM,
                category="general",
                priority=Priority.MEDIUM,
                status=TicketStatus.OPEN
            )
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            ticket_id = ticket.id

        with TestClient(app) as client:
            response = client.get(f"/support/ticket/{ticket_id}")

            assert response.status_code == 200
            data = response.json()

            # Verify chronological order
            for i in range(5):
                assert data["messages"][i]["content"] == f"Message {i}"
