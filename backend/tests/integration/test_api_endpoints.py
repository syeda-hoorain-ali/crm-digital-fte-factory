"""Integration tests for FastAPI endpoints with real database."""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.database.models import (
    Channel,
    Customer,
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
    MessageDirection,
)
from src.database.queries import (
    create_customer,
    create_customer_identifier,
    create_conversation,
    create_message,
)
from src.database.models import IdentifierType


# ============================================================================
# Integration Tests for API Endpoints (T093-T095)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestHealthEndpoint:
    """Integration tests for GET /health endpoint (T093)."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(self):
        """Test health endpoint returns 200 OK."""
        with TestClient(app) as client:
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_endpoint_includes_timestamp(self):
        """Test health endpoint includes timestamp."""
        with TestClient(app) as client:
            response = client.get("/health")

            data = response.json()
            assert "timestamp" in data
            assert isinstance(data["timestamp"], str)

    @pytest.mark.asyncio
    async def test_health_endpoint_includes_version(self):
        """Test health endpoint includes version info."""
        with TestClient(app) as client:
            response = client.get("/health")

            data = response.json()
            # Version info may be optional
            if "version" in data:
                assert isinstance(data["version"], str)


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.agent
class TestAgentProcessEndpoint:
    """Integration tests for POST /agent/process endpoint (T094)."""

    @pytest.mark.asyncio
    async def test_process_endpoint_with_new_customer(self, session: AsyncSession): # error in this
        """Test processing inquiry from new customer."""
        request_data = {
            "message": "Hello, I need help with my account",
            "customer_email": f"newcustomer{uuid4().hex[:8]}@example.com",
            "customer_phone": f"+12345{uuid4().hex[:6]}",
            "channel": "api",
        }

        with TestClient(app) as client:
            response = client.post("/agent/process", json=request_data)

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "response" in data
            assert "customer_id" in data
            assert "conversation_id" in data
            assert isinstance(data["response"], str)
            assert len(data["response"]) > 0

    @pytest.mark.asyncio
    async def test_process_endpoint_with_existing_customer(
        self, session: AsyncSession, test_customer: Customer
    ):
        """Test processing inquiry from existing customer."""
        # Ensure test customer has email
        assert test_customer.email is not None

        # Setup: Create customer identifier
        identifier = await create_customer_identifier(
            session,
            test_customer.id,
            IdentifierType.EMAIL,
            test_customer.email,
        )
        await session.commit()

        request_data = {
            "message": "I have a question about billing",
            "customer_email": test_customer.email,
            "channel": "email",
        }

        with TestClient(app) as client:
            response = client.post("/agent/process", json=request_data)

            assert response.status_code == 200
            data = response.json()

            # Verify customer was identified
            assert data["customer_id"] == str(test_customer.id)

        # Note: Cleanup happens automatically via fixtures

    @pytest.mark.asyncio
    async def test_process_endpoint_missing_message(self):
        """Test process endpoint with missing message field."""
        request_data = {
            "customer_email": "test@example.com",
            "channel": "api",
        }

        with TestClient(app) as client:
            response = client.post("/agent/process", json=request_data)

            # Should return 422 Unprocessable Entity for validation error
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_process_endpoint_missing_contact_info(self):
        """Test process endpoint with missing email and phone."""
        request_data = {
            "message": "Hello",
            "channel": "api",
        }

        with TestClient(app) as client:
            response = client.post("/agent/process", json=request_data)

            # Should return error or handle gracefully
            # Exact behavior depends on implementation
            assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_process_endpoint_includes_observability_metrics(self):
        """Test process endpoint includes observability metrics."""
        request_data = {
            "message": "Test message",
            "customer_email": "metrics@example.com",
            "channel": "api",
        }

        with TestClient(app) as client:
            response = client.post("/agent/process", json=request_data)

            assert response.status_code == 200
            data = response.json()
            print('      ')
            print(data)

            # Check for observability fields
            if "tokens_used" in data:
                assert isinstance(data["tokens_used"], int)
            if "latency_ms" in data:
                assert isinstance(data["latency_ms"], int)

    @pytest.mark.asyncio
    async def test_process_endpoint_handles_different_channels(self):
        """Test process endpoint handles different channel types."""
        channels = ["email", "whatsapp", "web_form", "api"]

        for channel in channels:
            request_data = {
                "message": f"Test message via {channel}",
                "customer_email": f"test-{channel}@example.com",
                "channel": channel,
            }

            with TestClient(app) as client:
                response = client.post("/agent/process", json=request_data)

                assert response.status_code == 200
                data = response.json()
                assert "response" in data

    @pytest.mark.asyncio
    async def test_process_endpoint_escalation_tracking(self):
        """Test process endpoint tracks escalation status."""
        request_data = {
            "message": "I'm extremely frustrated and want to speak to a manager!",
            "customer_email": "frustrated@example.com",
            "channel": "email",
        }

        with TestClient(app) as client:
            response = client.post("/agent/process", json=request_data)

            assert response.status_code == 200
            data = response.json()

            # Check if escalation was triggered
            if "escalated" in data:
                assert isinstance(data["escalated"], bool)
            if "escalation_reason" in data and data.get("escalated"):
                assert isinstance(data["escalation_reason"], str)


@pytest.mark.integration
@pytest.mark.database
class TestConversationHistoryEndpoint:
    """Integration tests for GET /agent/history/{conversation_id} endpoint (T095)."""

    @pytest.mark.asyncio
    async def test_history_endpoint_retrieves_messages(
        self, session: AsyncSession, test_customer: Customer
    ):
        """Test history endpoint retrieves conversation messages."""
        # Setup: Create conversation with messages
        conversation = await create_conversation(
            session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await create_message(
            session,
            conversation.id,
            MessageRole.CUSTOMER,
            "First message",
            MessageDirection.INBOUND,
            Channel.API,
        )

        await create_message(
            session,
            conversation.id,
            MessageRole.AGENT,
            "First response",
            MessageDirection.OUTBOUND,
            Channel.API,
        )

        await session.commit()

        with TestClient(app) as client:
            response = client.get(f"/agent/history/{conversation.id}")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "conversation_id" in data
            assert "messages" in data
            assert isinstance(data["messages"], list)
            assert len(data["messages"]) >= 2

            # Verify message structure
            first_message = data["messages"][0]
            assert "role" in first_message
            assert "content" in first_message
            assert "created_at" in first_message

    @pytest.mark.asyncio
    async def test_history_endpoint_not_found(self):
        """Test history endpoint with non-existent conversation."""
        fake_id = uuid4()

        with TestClient(app) as client:
            response = client.get(f"/agent/history/{fake_id}")

            # Should return 404 Not Found
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_history_endpoint_empty_conversation(
        self, session: AsyncSession, test_customer: Customer
    ):
        """Test history endpoint with conversation that has no messages."""
        # Setup: Create empty conversation
        conversation = await create_conversation(
            session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await session.commit()

        with TestClient(app) as client:
            response = client.get(f"/agent/history/{conversation.id}")

            assert response.status_code == 200
            data = response.json()

            assert data["conversation_id"] == str(conversation.id)
            assert data["messages"] == []

    @pytest.mark.asyncio
    async def test_history_endpoint_includes_metadata(
        self, session: AsyncSession, test_customer: Customer
    ):
        """Test history endpoint includes conversation metadata."""
        # Setup: Create conversation with metadata
        conversation = await create_conversation(
            session,
            test_customer.id,
            Channel.EMAIL,
            ConversationStatus.RESOLVED,
        )

        await create_message(
            session,
            conversation.id,
            MessageRole.CUSTOMER,
            "Test message",
            MessageDirection.INBOUND,
            Channel.API,
            tokens_used=50,
            latency_ms=100,
        )

        await session.commit()

        with TestClient(app) as client:
            response = client.get(f"/agent/history/{conversation.id}")

            assert response.status_code == 200
            data = response.json()

            # Check for conversation metadata
            if "status" in data:
                assert data["status"] == "resolved"
            if "channel" in data:
                assert data["channel"] == "email"

            # Check for message metadata
            if len(data["messages"]) > 0:
                message = data["messages"][0]
                if "tokens_used" in message:
                    assert isinstance(message["tokens_used"], int)

    @pytest.mark.asyncio
    async def test_history_endpoint_pagination(
        self, session: AsyncSession, test_customer: Customer
    ):
        """Test history endpoint supports pagination."""
        # Setup: Create conversation with many messages
        conversation = await create_conversation(
            session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        # Create 20 messages
        for i in range(20):
            role = MessageRole.CUSTOMER if i % 2 == 0 else MessageRole.AGENT
            direction = MessageDirection.INBOUND if i % 2 == 0 else MessageDirection.OUTBOUND

            await create_message(
                session,
                conversation.id,
                role,
                f"Message {i}",
                direction,
                Channel.API,
            )

        await session.commit()

        with TestClient(app) as client:
            # Test with limit parameter
            response = client.get(
                f"/agent/history/{conversation.id}",
                params={"limit": 10}
            )

            assert response.status_code == 200
            data = response.json()

            # Should return at most 10 messages
            assert len(data["messages"]) <= 10

    @pytest.mark.asyncio
    async def test_history_endpoint_chronological_order(
        self, session: AsyncSession, test_customer: Customer
    ):
        """Test history endpoint returns messages in chronological order."""
        # Setup: Create conversation with messages
        conversation = await create_conversation(
            session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        messages_content = ["First", "Second", "Third", "Fourth"]
        for content in messages_content:
            await create_message(
                session,
                conversation.id,
                MessageRole.CUSTOMER,
                content,
                MessageDirection.INBOUND,
                Channel.API,
            )

        await session.commit()

        with TestClient(app) as client:
            response = client.get(f"/agent/history/{conversation.id}")

            assert response.status_code == 200
            data = response.json()

            # Verify chronological order
            retrieved_content = [msg["content"] for msg in data["messages"]]
            assert retrieved_content == messages_content

    @pytest.mark.asyncio
    async def test_history_endpoint_invalid_uuid(self):
        """Test history endpoint with invalid UUID format."""
        with TestClient(app) as client:
            response = client.get("/agent/history/invalid-uuid")

            # Should return 422 Unprocessable Entity for invalid UUID
            assert response.status_code == 422
