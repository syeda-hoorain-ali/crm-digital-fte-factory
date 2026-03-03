"""Unit tests for agent tools with mocked dependencies."""

import json
import pytest
from uuid import uuid4
from agents.tool_context import ToolContext
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch, create_autospec


from src.agent.context import CustomerSuccessContext
from src.agent.tools import (
    identify_customer,
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    send_response,
)
from src.database.models import (
    Channel,
    Customer,
    Conversation,
    ConversationStatus,
    KnowledgeBase,
    Message,
    MessageDirection,
    MessageRole,
    Priority,
    Ticket,
    TicketStatus
)

# ============================================================================
# Tests for identify_customer tool (T076)
# ============================================================================

@pytest.mark.unit
@pytest.mark.agent
class TestIdentifyCustomerTool:
    """Unit tests for identify_customer tool."""

    @pytest.mark.asyncio
    async def test_identify_existing_customer_by_email(self, mock_customer_context):
        """Test identifying existing customer by email."""
        # Mock database queries
        mock_customer = Customer(
            id=uuid4(),
            email="test@example.com",
            phone="+1234567890",
            name="Test Customer",
            meta_data={"tier": "premium"},
        )

        with patch(
            "src.agent.tools.identify_customer.get_customer_by_identifier",
            new_callable=AsyncMock,
        ) as mock_get_customer:
            mock_get_customer.return_value = mock_customer

            # Execute tool using mock wrapper
            wrapper = MagicMock()
            wrapper.context = mock_customer_context
            input_data = {"email": "test@example.com"}
            result = await identify_customer.on_invoke_tool(wrapper, json.dumps(input_data))

            # Verify result
            assert "Customer identified" in result
            assert str(mock_customer.id) in result
            assert "premium" in result

            # Verify context was updated
            assert mock_customer_context.customer_id == str(mock_customer.id)
            assert mock_customer_context.customer_email == "test@example.com"

            # Verify database was queried
            mock_get_customer.assert_called_once()

    @pytest.mark.asyncio
    async def test_identify_existing_customer_by_phone(self, mock_customer_context):
        """Test identifying existing customer by phone."""
        mock_customer = Customer(
            id=uuid4(),
            email="test@example.com",
            phone="+1234567890",
            name="Test Customer",
            meta_data={"tier": "standard"},
        )

        with patch(
            "src.agent.tools.identify_customer.get_customer_by_identifier",
            new_callable=AsyncMock,
        ) as mock_get_customer:
            # When only phone is provided, tool only calls once (skips email check)
            mock_get_customer.return_value = mock_customer

            wrapper = MagicMock()
            wrapper.context = mock_customer_context
            input_data = {"phone": "+1234567890"}
            result = await identify_customer.on_invoke_tool(wrapper, json.dumps(input_data))

            assert "Customer identified" in result
            assert str(mock_customer.id) in result

    @pytest.mark.asyncio
    async def test_create_new_customer(self, mock_customer_context):
        """Test creating new customer when not found."""
        new_customer = Customer(
            id=uuid4(),
            email="new@example.com",
            phone="+1111111111",
            name=None,
            meta_data={"tier": "standard"},
        )

        # Update context with new customer contact info (simulating incoming request)
        mock_customer_context.customer_email = "new@example.com"
        mock_customer_context.customer_phone = "+1111111111"

        with patch(
            "src.agent.tools.identify_customer.get_customer_by_identifier",
            new_callable=AsyncMock,
        ) as mock_get_customer, patch(
            "src.database.queries.customer.create_customer",
            new_callable=AsyncMock,
        ) as mock_create_customer, patch(
            "src.agent.tools.identify_customer.create_customer_identifier",
            new_callable=AsyncMock,
        ):
            mock_get_customer.return_value = None
            mock_create_customer.return_value = new_customer

            wrapper = MagicMock()
            wrapper.context = mock_customer_context
            # Tool no longer accepts arguments - reads from context
            result = await identify_customer.on_invoke_tool(wrapper, "{}")

            assert "New customer created" in result
            assert "Welcome to CloudStream CRM" in result

            # Verify context was updated with new customer ID
            assert mock_customer_context.customer_id is not None
            assert mock_customer_context.customer_email == "new@example.com"
            assert mock_customer_context.customer_phone == "+1111111111"

    @pytest.mark.asyncio
    async def test_error_no_contact_info(self, mock_customer_context):
        """Test error when neither email nor phone in context."""
        # Clear contact info from context
        mock_customer_context.customer_email = None
        mock_customer_context.customer_phone = None

        wrapper = MagicMock()
        wrapper.context = mock_customer_context
        # Tool no longer accepts arguments - reads from context
        result = await identify_customer.on_invoke_tool(wrapper, "{}")

        assert "Error" in result
        assert "No customer contact information" in result


# ============================================================================
# Tests for search_knowledge_base tool (T077)
# ============================================================================

@pytest.mark.unit
@pytest.mark.agent
class TestSearchKnowledgeBaseTool:
    """Unit tests for search_knowledge_base tool."""

    @pytest.mark.asyncio
    async def test_search_finds_relevant_articles(self, mock_customer_context):
        """Test searching knowledge base returns relevant articles."""
        mock_articles = [
            (
                KnowledgeBase(
                    id=uuid4(),
                    title="Password Reset Guide",
                    content="How to reset your password...",
                    category="account",
                    embedding=[0.1] * 384,
                ),
                0.95,  # similarity score
            ),
            (
                KnowledgeBase(
                    id=uuid4(),
                    title="Account Security",
                    content="Tips for securing your account...",
                    category="security",
                    embedding=[0.1] * 384,
                ),
                0.87,
            ),
        ]

        with patch(
            "src.agent.tools.search_knowledge_base.db_search_knowledge_base",
            new_callable=AsyncMock,
        ) as mock_search, patch(
            "src.agent.tools.search_knowledge_base.get_embedding_model"
        ) as mock_get_model:
            mock_search.return_value = mock_articles

            # Mock embedding model to return object with tolist() method
            mock_embedding = MagicMock()
            mock_embedding.tolist.return_value = [0.1] * 384
            mock_model = MagicMock()
            mock_model.embed.return_value = [mock_embedding]
            mock_get_model.return_value = mock_model

            wrapper = MagicMock()
            wrapper.context = mock_customer_context
            input_data = {"query": "How do I reset my password?"}
            result = await search_knowledge_base.on_invoke_tool(wrapper, json.dumps(input_data))

            assert "Found 2 relevant articles" in result
            assert "Password Reset Guide" in result
            assert "95%" in result  # similarity percentage

            # Verify context was updated
            assert len(mock_customer_context.knowledge_articles_retrieved) == 2

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_customer_context):
        """Test search with no relevant articles found."""
        with patch(
            "src.agent.tools.search_knowledge_base.db_search_knowledge_base",
            new_callable=AsyncMock,
        ) as mock_search, patch(
            "src.agent.tools.search_knowledge_base.get_embedding_model"
        ) as mock_get_model:
            mock_search.return_value = []

            # Mock embedding model to return object with tolist() method
            mock_embedding = MagicMock()
            mock_embedding.tolist.return_value = [0.1] * 384
            mock_model = MagicMock()
            mock_model.embed.return_value = [mock_embedding]
            mock_get_model.return_value = mock_model

            wrapper = MagicMock()
            wrapper.context = mock_customer_context
            input_data = {"query": "Obscure query with no matches"}
            result = await search_knowledge_base.on_invoke_tool(wrapper, json.dumps(input_data))

            assert "No relevant articles found" in result
            assert "human assistance" in result.lower()


# ============================================================================
# Tests for create_ticket tool (T078)
# ============================================================================

@pytest.mark.unit
@pytest.mark.agent
class TestCreateTicketTool:
    """Unit tests for create_ticket tool."""

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, mock_customer_context):
        """Test successful ticket creation."""
        mock_ticket = Ticket(
            id=uuid4(),
            conversation_id=uuid4(),
            customer_id=uuid4(),
            source_channel=Channel.API,
            category="technical",
            priority=Priority.HIGH,
            status=TicketStatus.OPEN,
        )

        with patch(
            "src.agent.tools.create_ticket.db_create_ticket",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_ticket

            wrapper = MagicMock()
            wrapper.context = mock_customer_context
            input_data = {"category": "technical", "priority": "high"}
            result = await create_ticket.on_invoke_tool(wrapper, json.dumps(input_data))

            assert "Support ticket created" in result
            assert str(mock_ticket.id) in result
            assert "high" in result.lower()
            assert "technical" in result.lower()

            # Verify context was updated
            assert mock_customer_context.ticket_id == str(mock_ticket.id)

    @pytest.mark.asyncio
    async def test_create_ticket_missing_context(self):
        """Test error when customer/conversation not identified."""
        # Create context without customer_id or conversation_id
        mock_session = create_autospec(AsyncSession, instance=True)
        context = CustomerSuccessContext(db_session=mock_session)

        wrapper = MagicMock()
        wrapper.context = context
        input_data = {"category": "billing"}
        result = await create_ticket.on_invoke_tool(wrapper, json.dumps(input_data))

        assert "Error" in result
        assert "must be identified first" in result


# ============================================================================
# Tests for get_customer_history tool (T079 - partial, escalate_to_human is separate)
# ============================================================================

@pytest.mark.unit
@pytest.mark.agent
class TestGetCustomerHistoryTool:
    """Unit tests for get_customer_history tool."""

    @pytest.mark.asyncio
    async def test_get_history_with_conversations(self, mock_customer_context):
        """Test retrieving customer history with conversations."""
        mock_conversations = [
            Conversation(
                id=uuid4(),
                customer_id=uuid4(),
                initial_channel=Channel.EMAIL,
                status=ConversationStatus.RESOLVED,
                sentiment_score=0.8,
                started_at=MagicMock(),
            )
        ]

        mock_messages = [
            Message(
                id=uuid4(),
                conversation_id=mock_conversations[0].id,
                channel=Channel.EMAIL,
                direction=MessageDirection.INBOUND,
                role=MessageRole.CUSTOMER,
                content="I need help with billing",
                created_at=MagicMock(),
            )
        ]

        with patch(
            "src.agent.tools.get_customer_history.list_customer_conversations",
            new_callable=AsyncMock,
        ) as mock_list_convs, patch(
            "src.agent.tools.get_customer_history.get_conversation_history",
            new_callable=AsyncMock,
        ) as mock_get_history:
            mock_list_convs.return_value = mock_conversations
            mock_get_history.return_value = mock_messages

            wrapper = MagicMock()
            wrapper.context = mock_customer_context
            input_data = {"limit": 5}
            result = await get_customer_history.on_invoke_tool(wrapper, json.dumps(input_data))

            assert "Found 1 previous conversation" in result
            assert "resolved" in result.lower()
            assert "positive" in result.lower()  # sentiment > 0.3

    @pytest.mark.asyncio
    async def test_get_history_no_conversations(self, mock_customer_context):
        """Test retrieving history for new customer."""
        with patch(
            "src.agent.tools.get_customer_history.list_customer_conversations",
            new_callable=AsyncMock,
        ) as mock_list_convs:
            mock_list_convs.return_value = []

            wrapper = MagicMock()
            wrapper.context = mock_customer_context
            input_data = {}
            result = await get_customer_history.on_invoke_tool(wrapper, json.dumps(input_data))

            assert "No previous conversation history" in result
            assert "new customer" in result.lower()


# ============================================================================
# Tests for send_response tool (T080)
# ============================================================================

@pytest.mark.unit
@pytest.mark.agent
class TestSendResponseTool:
    """Unit tests for send_response tool."""

    @pytest.mark.asyncio
    async def test_send_response_success(self, mock_customer_context):
        """Test successful response sending."""

        mock_message = Message(
            id=uuid4(),
            conversation_id=uuid4(),
            channel=Channel.API,
            direction=MessageDirection.OUTBOUND,
            role=MessageRole.AGENT,
            content="Thank you for contacting us!",
            tokens_used=100,
            latency_ms=500,
        )

        with patch(
            "src.agent.tools.send_response.create_message",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_message

            wrapper = MagicMock()
            wrapper.context = mock_customer_context
            input_data = {
                "response_text": "Thank you for contacting us!",
                "tokens_used": 100,
                "latency_ms": 500
            }
            result = await send_response.on_invoke_tool(wrapper, json.dumps(input_data))

            assert "Response sent successfully" in result
            assert str(mock_message.id) in result
            assert "100" in result  # tokens
            assert "500" in result  # latency

    @pytest.mark.asyncio
    async def test_send_response_no_conversation(self):
        """Test error when no active conversation."""
        mock_session = create_autospec(AsyncSession, instance=True)
        context = CustomerSuccessContext(db_session=mock_session)

        wrapper = MagicMock()
        wrapper.context = context
        input_data = {"response_text": "Test response"}
        result = await send_response.on_invoke_tool(wrapper, json.dumps(input_data))

        assert "Error" in result
        assert "No active conversation" in result

