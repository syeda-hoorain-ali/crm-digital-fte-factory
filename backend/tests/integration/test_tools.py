"""Integration tests for full agent workflow with real database."""

import json
import pytest
from unittest.mock import AsyncMock, patch
from agents.tool_context import ToolContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.context import CustomerSuccessContext
from src.agent.tools import (
    create_ticket, 
    escalate_to_human, 
    get_customer_history,
    identify_customer, 
    send_response, 
    search_knowledge_base, 
)
from src.database.models import (
    Channel,
    Customer,
    ConversationStatus,
    IdentifierType,
    MessageRole,
    MessageDirection,
)
from src.database.queries import (
    create_customer,
    create_customer_identifier,
    create_conversation,
    create_knowledge_base_entry,
    create_message,
    get_conversation,
    get_conversation_history,
    list_conversation_tickets,
)


# ============================================================================
# Integration Tests for Full Agent Workflow (T092)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
@pytest.mark.slow
@pytest.mark.skip
class TestAgentWorkflowIntegration:
    """Integration tests for complete agent workflow with real database."""

    @pytest.mark.asyncio
    async def test_complete_customer_support_workflow(self, session: AsyncSession, test_customer: Customer):
        """Test complete workflow: identify → search → respond."""
        # Ensure test customer has required fields
        assert test_customer.email is not None

        # Setup: Create customer identifiers
        await create_customer_identifier(
            session,
            test_customer.id,
            IdentifierType.EMAIL,
            test_customer.email,
        )

        # Setup: Create knowledge base article
        dummy_embedding = [0.1] * 384
        await create_knowledge_base_entry(
            session,
            "Password Reset Guide",
            "To reset your password, go to Settings > Security.",
            dummy_embedding,
        )

        # Setup: Create conversation
        conversation = await create_conversation(
            session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await session.commit()

        # Create context
        context = CustomerSuccessContext(
            db_session=session,
            conversation_id=str(conversation.id),
            channel="api",
        )

        # Mock the agent run to test tool integration
        # In a real scenario, this would call the actual agent
        # For integration testing, we verify the tools work with real database

        # Test 1: identify_customer tool
        input_data = {"email": test_customer.email}
        wrapper = ToolContext(
            context=context,
            tool_name=identify_customer.name,
            tool_arguments=input_data
        )
        result = await identify_customer.on_invoke_tool(wrapper, json.dumps(input_data))

        assert "Customer identified" in result
        assert context.customer_id == str(test_customer.id)

        # Test 2: search_knowledge_base tool
        with patch("src.agent.tools.search_knowledge_base.get_embedding_model") as mock_model:
            mock_embed = AsyncMock()
            mock_embed.embed.return_value = [[0.1] * 384]
            mock_model.return_value = mock_embed

            search_input_data = {"query": "How to reset password?"}
            search_wrapper = ToolContext(
                context=context,
                tool_name=search_knowledge_base.name,
                tool_arguments=search_input_data
            )
            search_result = await search_knowledge_base.on_invoke_tool(search_wrapper, json.dumps(search_input_data))

            assert "Password Reset Guide" in search_result or "No relevant articles" in search_result

        # Test 3: send_response tool
        response_input_data = {
            "response_text": "I can help you reset your password.",
            "tokens_used": 50,
            "latency_ms": 200,
        }
        response_wrapper = ToolContext(
            context=context,
            tool_name=send_response.name,
            tool_arguments=response_input_data
        )
        response_result = await send_response.on_invoke_tool(response_wrapper, json.dumps(response_input_data))

        assert "Response sent successfully" in response_result

        await session.commit()

        # Verify message was stored
        messages = await get_conversation_history(
            session,
            conversation.id,
            limit=10,
            offset=0,
        )

        assert len(messages) >= 1
        agent_messages = [m for m in messages if m.role == MessageRole.AGENT]
        assert len(agent_messages) >= 1
        assert agent_messages[0].content == "I can help you reset your password."

    @pytest.mark.asyncio
    async def test_escalation_workflow(self, session: AsyncSession, test_customer: Customer):
        """Test escalation workflow with sentiment analysis."""
        # Setup: Create conversation with negative sentiment
        conversation = await create_conversation(
            session,
            test_customer.id,
            Channel.EMAIL,
            ConversationStatus.ACTIVE,
        )

        # Add messages with negative sentiment
        await create_message(
            session,
            conversation.id,
            MessageRole.CUSTOMER,
            "I'm very frustrated with this service!",
            MessageDirection.INBOUND,
            Channel.EMAIL,
        )

        await session.commit()

        # Create context
        context = CustomerSuccessContext(
            db_session=session,
            customer_id=str(test_customer.id),
            conversation_id=str(conversation.id),
            channel="email",
        )

        # Test escalate_to_human tool
        input_data = {"reason": "Customer expressing frustration", "priority": "high"}
        wrapper = ToolContext(
            context=context,
            tool_name=escalate_to_human.name,
            tool_arguments=input_data
        )
        result = await escalate_to_human.on_invoke_tool(wrapper, json.dumps(input_data))


        assert "Escalated to human support" in result
        assert context.escalation_triggered is True

        await session.commit()

        # Verify conversation was updated
        updated_conv = await get_conversation(session, conversation.id)

        assert updated_conv
        assert updated_conv.status == ConversationStatus.ESCALATED
        assert updated_conv.escalated_to is not None

    @pytest.mark.asyncio
    async def test_ticket_creation_workflow(self, session: AsyncSession, test_customer: Customer):
        """Test ticket creation workflow."""
        # Setup: Create conversation
        conversation = await create_conversation(
            session,
            test_customer.id,
            Channel.WEB_FORM,
            ConversationStatus.ACTIVE,
        )

        await session.commit()

        # Create context
        context = CustomerSuccessContext(
            db_session=session,
            customer_id=str(test_customer.id),
            conversation_id=str(conversation.id),
            channel="web_form",
        )

        # Test create_ticket tool
        input_data = {"category": "billing", "priority": "medium"}
        wrapper = ToolContext(
            context=context,
            tool_name=create_ticket.name,
            tool_arguments=input_data
        )
        result = await create_ticket.on_invoke_tool(wrapper, json.dumps(input_data))

        assert "Support ticket created" in result
        assert context.ticket_id is not None

        await session.commit()

        # Verify ticket was created
        tickets = await list_conversation_tickets(session, conversation.id)

        assert len(tickets) >= 1
        assert tickets[0].category == "billing"

    @pytest.mark.asyncio
    async def test_customer_history_workflow(self, session: AsyncSession, test_customer: Customer):
        """Test customer history retrieval workflow."""
        # Setup: Create multiple conversations
        conv1 = await create_conversation(
            session,
            test_customer.id,
            Channel.EMAIL,
            ConversationStatus.RESOLVED,
        )

        conv2 = await create_conversation(
            session,
            test_customer.id,
            Channel.WHATSAPP,
            ConversationStatus.ACTIVE,
        )

        # Add messages to conversations
        await create_message(
            session,
            conv1.id,
            MessageRole.CUSTOMER,
            "Previous issue",
            MessageDirection.INBOUND,
            Channel.WHATSAPP,
        )

        await session.commit()

        # Create context
        context = CustomerSuccessContext(
            db_session=session,
            customer_id=str(test_customer.id),
            conversation_id=str(conv2.id),
            channel="whatsapp",
        )

        # Test get_customer_history tool
        input_data = {"limit": 5}
        wrapper = ToolContext(
            context=context,
            tool_name=get_customer_history.name,
            tool_arguments=input_data
        )
        result = await get_customer_history.on_invoke_tool(wrapper, json.dumps(input_data))


        assert "Found" in result
        assert "conversation" in result.lower()
        assert len(context.conversation_history) >= 2

    @pytest.mark.asyncio
    async def test_cross_channel_customer_unification(self, session):
        """Test customer unification across different channels."""
        # Create customer with email identifier
        customer = await create_customer(
            session,
            name="John Doe",
            email="john@example.com",
            phone="+1234567890",
        )

        await create_customer_identifier(
            session,
            customer.id,
            IdentifierType.EMAIL,
            "john@example.com",
        )

        await create_customer_identifier(
            session,
            customer.id,
            IdentifierType.PHONE,
            "+1234567890",
        )

        await session.commit()

        # Test identification via email (Channel 1: Email)
        context1 = CustomerSuccessContext(
            db_session=session,
            channel="email",
        )

        input_data1 = {"email": "jhon@example.com"}
        wrapper1 = ToolContext(
            context=context1,
            tool_name=identify_customer.name,
            tool_arguments=input_data1
        )
        result1 = await identify_customer.on_invoke_tool(wrapper1, json.dumps(input_data1))


        assert "Customer identified" in result1
        customer_id_1 = context1.customer_id

        # Test identification via phone (Channel 2: WhatsApp)
        context2 = CustomerSuccessContext(
            db_session=session,
            channel="whatsapp",
        )

        input_data2 = {"phone": "+1234567890"}
        wrapper2 = ToolContext(
            context=context2,
            tool_name=identify_customer.name,
            tool_arguments=input_data2
        )
        result2 = await identify_customer.on_invoke_tool(wrapper2, json.dumps(input_data2))


        assert "Customer identified" in result2
        customer_id_2 = context2.customer_id

        # Verify same customer was identified across channels
        assert customer_id_1 == customer_id_2
        assert customer_id_1 == str(customer.id)

    @pytest.mark.asyncio
    async def test_context_state_management(self, session: AsyncSession, test_customer: Customer):
        """Test context state is properly managed across tool calls."""
        # Ensure test customer has required fields
        assert test_customer.email is not None

        # Create conversation
        conversation = await create_conversation(
            session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await create_customer_identifier(
            session,
            test_customer.id,
            IdentifierType.EMAIL,
            test_customer.email,
        )

        await session.commit()

        # Create context
        context = CustomerSuccessContext(
            db_session=session,
            conversation_id=str(conversation.id),
            channel="api",
        )

        # Verify initial state
        assert context.customer_id is None
        assert context.ticket_id is None
        assert context.escalation_triggered is False

        # Call identify_customer - should update context
        identify_input = {"email": test_customer.email}
        wrapper_identify = ToolContext(
            context=context,
            tool_name=identify_customer.name,
            tool_arguments=identify_input
        )
        await identify_customer.on_invoke_tool(wrapper_identify, json.dumps(identify_input))

        assert context.customer_id == str(test_customer.id)
        assert context.customer_email == test_customer.email

        # Call create_ticket - should update context
        ticket_input = {"category": "technical"}
        wrapper_ticket = ToolContext(
            context=context,
            tool_name=create_ticket.name,
            tool_arguments=ticket_input
        )
        await create_ticket.on_invoke_tool(wrapper_ticket, json.dumps(ticket_input))

        assert context.ticket_id is not None

        # Verify all state is maintained
        assert context.customer_id == str(test_customer.id)
        assert context.ticket_id is not None
        assert context.conversation_id == str(conversation.id)

    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(self, session):
        """Test error handling when tools are called with invalid state."""
        # Create context without required fields
        context = CustomerSuccessContext(
            db_session=session,
            channel="api",
        )

        # Try to create ticket without customer/conversation
        input_data = {"category": "test"}
        wrapper_ticket = ToolContext(
            context=context,
            tool_name=create_ticket.name,
            tool_arguments=input_data
        )
        result = await create_ticket.on_invoke_tool(wrapper_ticket, json.dumps(input_data))

        assert "Error" in result
        assert "must be identified" in result.lower()

        # Try to send response without conversation
        response_input = {"response_text": "Test"}
        wrapper_response = ToolContext(
            context=context,
            tool_name=send_response.name,
            tool_arguments=response_input
        )
        result = await send_response.on_invoke_tool(wrapper_response, json.dumps(response_input))

        assert "Error" in result
        assert "conversation" in result.lower()
