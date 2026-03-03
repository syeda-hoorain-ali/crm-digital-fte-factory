"""Integration tests for full agent workflow with real database.

These tests require API credentials (GEMINI_API_KEY) to run.
They test the complete agent execution flow including LLM calls, tools, database, and hooks.
"""

import os
import pytest
from agents import Runner
from sqlalchemy.ext.asyncio import AsyncSession
from openai.types.responses import ResponseFunctionToolCall

from src.agent.tools.search_knowledge_base import get_embedding_model
from src.agent.customer_success_agent import customer_success_agent
from src.agent.context import CustomerSuccessContext
from src.agent.session import PostgresSession
from src.agent.hooks import RunHooks
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


# Skip all tests in this module if API credentials are not available
pytestmark = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="Requires GEMINI_API_KEY"
)


# ============================================================================
# Integration Tests for Full Agent Workflow (T092)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
@pytest.mark.agent
@pytest.mark.slow
class TestAgentWorkflowIntegration:
    """Integration tests for complete agent workflow with real database."""

    @pytest.mark.asyncio
    async def test_complete_customer_support_workflow(self, db_session: AsyncSession, test_customer: Customer):
        """Test complete workflow: identify → search → respond using actual agent."""
        # Setup: Create customer identifiers
        await create_customer_identifier(
            db_session,
            test_customer.id,
            IdentifierType.EMAIL,
            test_customer.email,
        )

        # Setup: Create knowledge base article
        article_data = {
            "title": "Password Reset Guide",
            "category": "security",
            "content": "To reset your password, go to Settings > Security."
        }
        
        # Generate embedding for query
        embedding_model = get_embedding_model()
        embedding = list(embedding_model.embed([article_data["content"]]))[0].tolist()

        await create_knowledge_base_entry(
            db_session,
            title=article_data["title"],
            content=article_data["content"],
            embedding=embedding,
            category=article_data["category"],
            metadata={"category": article_data["category"]},
        )

        # Setup: Create conversation
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await db_session.commit()

        # Create context with customer email for identification
        context = CustomerSuccessContext(
            db_session=db_session,
            customer_email=test_customer.email,
            conversation_id=str(conversation.id),
            channel="api",
        )

        # Create session and hooks
        agent_session = PostgresSession(
            session=db_session,
            conversation_id=conversation.id,
            channel=Channel.API,
        )

        hooks = RunHooks(
            session=db_session,
            conversation_id=conversation.id,
            correlation_id=str(conversation.id),
        )

        # Run the actual agent with a customer inquiry
        result = await Runner.run(
            customer_success_agent,
            "How do I reset my password?",
            session=agent_session,
            context=context,
            hooks=hooks,
        )

        # print("\n\n\n")
        # raw_items = [item.raw_item for item in result.new_items]
        # print(raw_items)    # Output at Line on 643
        # print("\n\n\n")

        # Extract tool calls and outputs from result
        tool_calls = []
        tool_outputs = []
        for item in result.new_items:
            raw_item = item.raw_item
            if isinstance(raw_item, ResponseFunctionToolCall):
                tool_calls.append({
                    "name": raw_item.name,
                    "arguments": raw_item.arguments,
                    "call_id": raw_item.call_id,
                })
            elif isinstance(raw_item, dict) and raw_item.get("type", '') == "function_call_output":
                tool_outputs.append({
                    "call_id": raw_item.get("call_id"),
                    "output": raw_item.get("output"),
                })


        # Verify agent provided a response
        assert result.final_output, "Agent should provide a final output"
        assert len(result.final_output) > 0, "Final output should not be empty"

        # Verify identify_customer was called first (with no arguments)
        assert len(tool_calls) >= 1, "Agent should call at least identify_customer tool"
        identify_call = next((tc for tc in tool_calls if tc["name"] == "identify_customer"), None)
        assert identify_call is not None, "identify_customer tool should be called"
        assert identify_call["arguments"] == "{}", "identify_customer should be called with no arguments (uses context)"

        # Verify search_knowledge_base was called with correct query
        search_call = next((tc for tc in tool_calls if tc["name"] == "search_knowledge_base"), None)
        assert search_call is not None, "search_knowledge_base tool should be called"
        assert "password" in search_call["arguments"].lower(), "Search query should mention password"

        # Verify customer was identified in context
        assert context.customer_id == str(test_customer.id), "Customer should be identified"
        assert context.customer_email == test_customer.email, "Customer email should be set in context"

        # Verify final output contains relevant information
        assert "password" in result.final_output.lower(), "Response should mention password"
        assert "settings" in result.final_output.lower() or "security" in result.final_output.lower(), \
            "Response should mention settings or security"

        # Verify tool outputs were successful
        identify_output = next((to for to in tool_outputs if any(tc["call_id"] == to["call_id"] and tc["name"] == "identify_customer" for tc in tool_calls)), None)
        assert identify_output is not None, "identify_customer should have output"
        assert "Customer identified" in identify_output["output"], "identify_customer should confirm identification"
        assert str(test_customer.id) in identify_output["output"], "Output should contain customer ID"

        search_output = next((to for to in tool_outputs if any(tc["call_id"] == to["call_id"] and tc["name"] == "search_knowledge_base" for tc in tool_calls)), None)
        assert search_output is not None, "search_knowledge_base should have output"
        assert "Password Reset Guide" in search_output["output"], "Search should find the password reset article"

        await db_session.commit()

        # Verify messages were stored in conversation
        messages = await get_conversation_history(
            db_session,
            conversation.id,
            limit=10,
            offset=0,
        )

        assert len(messages) >= 2  # At least user message + agent response
        user_messages = [m for m in messages if m.role == MessageRole.CUSTOMER]
        agent_messages = [m for m in messages if m.role == MessageRole.AGENT]

        assert len(user_messages) >= 1
        assert len(agent_messages) >= 1
        assert "reset" in user_messages[0].content.lower()

    @pytest.mark.asyncio
    async def test_escalation_workflow(self, db_session: AsyncSession, test_customer: Customer):
        """Test escalation workflow with sentiment analysis using actual agent."""
        # Setup: Create customer identifier
        await create_customer_identifier(
            db_session,
            test_customer.id,
            IdentifierType.EMAIL,
            test_customer.email,
        )

        # Setup: Create conversation
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.EMAIL,
            ConversationStatus.ACTIVE,
        )

        # Add previous message with negative sentiment
        await create_message(
            db_session,
            conversation.id,
            MessageRole.CUSTOMER,
            "I'm very frustrated with this service!",
            MessageDirection.INBOUND,
            Channel.EMAIL,
        )

        await db_session.commit()

        # Create context
        context = CustomerSuccessContext(
            db_session=db_session,
            customer_email=test_customer.email,
            conversation_id=str(conversation.id),
            channel="email",
        )

        # Create session and hooks
        agent_session = PostgresSession(
            session=db_session,
            conversation_id=conversation.id,
            channel=Channel.EMAIL,
        )

        hooks = RunHooks(
            session=db_session,
            conversation_id=conversation.id,
            correlation_id=str(conversation.id),
        )

        # Run agent with a message that should trigger escalation
        result = await Runner.run(
            customer_success_agent,
            "This is unacceptable! I want to speak to a manager immediately!",
            session=agent_session,
            context=context,
            hooks=hooks,
        )

        # Extract tool calls and outputs from result
        tool_calls = []
        tool_outputs = []
        for item in result.new_items:
            raw_item = item.raw_item
            if isinstance(raw_item, ResponseFunctionToolCall):
                tool_calls.append({
                    "name": raw_item.name,
                    "arguments": raw_item.arguments,
                    "call_id": raw_item.call_id,
                })
            elif isinstance(raw_item, dict) and raw_item.get("type", '') == "function_call_output":
                tool_outputs.append({
                    "call_id": raw_item.get("call_id"),
                    "output": raw_item.get("output"),
                })

        # Verify agent provided a response
        assert result.final_output, "Agent should provide a final output"
        assert len(result.final_output) > 0, "Final output should not be empty"

        # Verify identify_customer was called first
        identify_call = next((tc for tc in tool_calls if tc["name"] == "identify_customer"), None)
        assert identify_call is not None, "identify_customer tool should be called"
        assert identify_call["arguments"] == "{}", "identify_customer should be called with no arguments"

        # Verify customer was identified in context
        assert context.customer_id == str(test_customer.id), "Customer should be identified"

        # Verify escalate_to_human was called (agent should detect explicit escalation request)
        escalate_call = next((tc for tc in tool_calls if tc["name"] == "escalate_to_human"), None)
        assert escalate_call is not None, "escalate_to_human tool should be called for explicit escalation request"

        # Verify escalation output
        escalate_output = next((to for to in tool_outputs if any(tc["call_id"] == to["call_id"] and tc["name"] == "escalate_to_human" for tc in tool_calls)), None)
        assert escalate_output is not None, "escalate_to_human should have output"
        assert "escalated" in escalate_output["output"].lower(), "Output should confirm escalation"

        # Verify escalation was triggered in context
        assert context.escalation_triggered is True, "Escalation should be triggered in context"
        assert context.escalation_reason is not None, "Escalation reason should be set"

        await db_session.commit()

        # Verify conversation was updated in database
        updated_conv = await get_conversation(db_session, conversation.id)
        assert updated_conv is not None, "Conversation should exist"
        assert updated_conv.status == ConversationStatus.ESCALATED, "Conversation status should be ESCALATED"
        assert updated_conv.escalated_to is not None, "Escalated_to field should be set"
        assert "@cloudstream.com" in updated_conv.escalated_to, "Should be escalated to support team email"

    @pytest.mark.asyncio
    async def test_ticket_creation_workflow(self, db_session: AsyncSession, test_customer: Customer):
        """Test ticket creation workflow using actual agent."""
        # Setup: Create customer identifier
        await create_customer_identifier(
            db_session,
            test_customer.id,
            IdentifierType.EMAIL,
            test_customer.email,
        )

        # Setup: Create conversation
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.WEB_FORM,
            ConversationStatus.ACTIVE,
        )

        await db_session.commit()

        # Create context
        context = CustomerSuccessContext(
            db_session=db_session,
            customer_email=test_customer.email,
            conversation_id=str(conversation.id),
            channel="web_form",
        )

        # Create session and hooks
        agent_session = PostgresSession(
            session=db_session,
            conversation_id=conversation.id,
            channel=Channel.WEB_FORM,
        )

        hooks = RunHooks(
            session=db_session,
            conversation_id=conversation.id,
            correlation_id=str(conversation.id),
        )

        # Run agent with a billing inquiry
        result = await Runner.run(
            customer_success_agent,
            "I have a billing issue that needs to be tracked. Can you create a ticket?",
            session=agent_session,
            context=context,
            hooks=hooks,
        )

        # Extract tool calls and outputs from result
        tool_calls = []
        tool_outputs = []
        for item in result.new_items:
            raw_item = item.raw_item
            if isinstance(raw_item, ResponseFunctionToolCall):
                tool_calls.append({
                    "name": raw_item.name,
                    "arguments": raw_item.arguments,
                    "call_id": raw_item.call_id,
                })
            elif isinstance(raw_item, dict) and raw_item.get("type", '') == "function_call_output":
                tool_outputs.append({
                    "call_id": raw_item.get("call_id"),
                    "output": raw_item.get("output"),
                })

        # Verify agent provided a response
        assert result.final_output, "Agent should provide a final output"
        assert len(result.final_output) > 0, "Final output should not be empty"

        # Verify identify_customer was called first
        identify_call = next((tc for tc in tool_calls if tc["name"] == "identify_customer"), None)
        assert identify_call is not None, "identify_customer tool should be called"
        assert identify_call["arguments"] == "{}", "identify_customer should be called with no arguments"

        # Verify customer was identified in context
        assert context.customer_id == str(test_customer.id), "Customer should be identified"

        # Verify create_ticket was called (agent should detect ticket creation request)
        ticket_call = next((tc for tc in tool_calls if tc["name"] == "create_ticket"), None)
        assert ticket_call is not None, "create_ticket tool should be called for explicit ticket request"

        # Verify ticket arguments contain billing category
        assert "billing" in ticket_call["arguments"].lower(), "Ticket should be categorized as billing"

        # Verify ticket output
        ticket_output = next((to for to in tool_outputs if any(tc["call_id"] == to["call_id"] and tc["name"] == "create_ticket" for tc in tool_calls)), None)
        assert ticket_output is not None, "create_ticket should have output"
        assert "ticket" in ticket_output["output"].lower(), "Output should confirm ticket creation"

        # Verify ticket was created in context
        assert context.ticket_id is not None, "Ticket ID should be set in context"

        await db_session.commit()

        # Verify ticket was created in database
        tickets = await list_conversation_tickets(db_session, conversation.id)
        assert len(tickets) >= 1, "At least one ticket should be created"

        ticket = tickets[0]
        assert ticket.conversation_id == conversation.id, "Ticket should be linked to conversation"
        assert ticket.customer_id == test_customer.id, "Ticket should be linked to customer"
        assert ticket.category == "billing", "Ticket category should be billing"
        assert str(ticket.id) == context.ticket_id, "Ticket ID in context should match database"

        # Verify messages were stored
        messages = await get_conversation_history(db_session, conversation.id, limit=10, offset=0)
        assert len(messages) >= 2, "Should have user message and agent response"
        assert any("billing" in m.content.lower() for m in messages), "Messages should mention billing"

    @pytest.mark.asyncio
    async def test_customer_history_workflow(self, db_session: AsyncSession, test_customer: Customer):
        """Test customer history retrieval workflow using actual agent."""
        # Setup: Create customer identifier
        await create_customer_identifier(
            db_session,
            test_customer.id,
            IdentifierType.EMAIL,
            test_customer.email,
        )

        # Setup: Create multiple conversations
        conv1 = await create_conversation(
            db_session,
            test_customer.id,
            Channel.EMAIL,
            ConversationStatus.RESOLVED,
        )

        conv2 = await create_conversation(
            db_session,
            test_customer.id,
            Channel.WHATSAPP,
            ConversationStatus.ACTIVE,
        )

        # Add messages to previous conversation
        await create_message(
            db_session,
            conv1.id,
            MessageRole.CUSTOMER,
            "Previous billing issue",
            MessageDirection.INBOUND,
            Channel.EMAIL,
        )

        await db_session.commit()

        # Create context for new conversation
        context = CustomerSuccessContext(
            db_session=db_session,
            customer_email=test_customer.email,
            conversation_id=str(conv2.id),
            channel="whatsapp",
        )

        # Create session and hooks
        agent_session = PostgresSession(
            session=db_session,
            conversation_id=conv2.id,
            channel=Channel.WHATSAPP,
        )

        hooks = RunHooks(
            session=db_session,
            conversation_id=conv2.id,
            correlation_id=str(conv2.id),
        )

        # Run agent with a request that might trigger history lookup
        result = await Runner.run(
            customer_success_agent,
            "What was my previous issue about?",
            session=agent_session,
            context=context,
            hooks=hooks,
        )

        # Extract tool calls and outputs from result
        tool_calls = []
        tool_outputs = []
        for item in result.new_items:
            raw_item = item.raw_item
            if isinstance(raw_item, ResponseFunctionToolCall):
                tool_calls.append({
                    "name": raw_item.name,
                    "arguments": raw_item.arguments,
                    "call_id": raw_item.call_id,
                })
            elif isinstance(raw_item, dict) and raw_item.get("type", '') == "function_call_output":
                tool_outputs.append({
                    "call_id": raw_item.get("call_id"),
                    "output": raw_item.get("output"),
                })

        # Verify agent provided a response
        assert result.final_output, "Agent should provide a final output"
        assert len(result.final_output) > 0, "Final output should not be empty"

        # Verify identify_customer was called first
        identify_call = next((tc for tc in tool_calls if tc["name"] == "identify_customer"), None)
        assert identify_call is not None, "identify_customer tool should be called"
        assert identify_call["arguments"] == "{}", "identify_customer should be called with no arguments"

        # Verify customer was identified in context
        assert context.customer_id == str(test_customer.id), "Customer should be identified"
        assert context.customer_email == test_customer.email, "Customer email should be set in context"

        # Verify get_customer_history was called (agent should look up previous conversations)
        history_call = next((tc for tc in tool_calls if tc["name"] == "get_customer_history"), None)
        assert history_call is not None, "get_customer_history tool should be called for history inquiry"

        # Verify history output contains previous conversation info
        history_output = next((to for to in tool_outputs if any(tc["call_id"] == to["call_id"] and tc["name"] == "get_customer_history" for tc in tool_calls)), None)
        assert history_output is not None, "get_customer_history should have output"
        assert "conversation" in history_output["output"].lower(), "Output should mention conversations"
        assert "billing" in history_output["output"].lower(), "Output should mention previous billing issue"

        # Verify conversation history was populated in context
        assert len(context.conversation_history) > 0, "Context should have conversation history"

        # Verify final response references the previous issue
        assert "billing" in result.final_output.lower(), "Response should reference previous billing issue"

        await db_session.commit()

        # Verify messages were stored in current conversation
        messages = await get_conversation_history(db_session, conv2.id, limit=10, offset=0)
        assert len(messages) >= 2, "Should have user message and agent response"
        user_messages = [m for m in messages if m.role == MessageRole.CUSTOMER]
        agent_messages = [m for m in messages if m.role == MessageRole.AGENT]
        assert len(user_messages) >= 1, "Should have at least one user message"
        assert len(agent_messages) >= 1, "Should have at least one agent message"
        assert "previous" in user_messages[0].content.lower(), "User message should ask about previous issue"

    @pytest.mark.asyncio
    async def test_cross_channel_customer_unification(self, db_session):
        """Test customer unification across different channels using actual agent."""
        # Create customer with both email and phone identifiers
        customer = await create_customer(
            db_session,
            name="John Doe",
            email="john@example.com",
            phone="+1234567890",
        )

        await create_customer_identifier(
            db_session,
            customer.id,
            IdentifierType.EMAIL,
            "john@example.com",
        )

        await create_customer_identifier(
            db_session,
            customer.id,
            IdentifierType.PHONE,
            "+1234567890",
        )

        await db_session.commit()

        # Scenario 1: Customer contacts via email
        conv1 = await create_conversation(
            db_session,
            customer.id,
            Channel.EMAIL,
            ConversationStatus.ACTIVE,
        )

        await db_session.commit()

        context1 = CustomerSuccessContext(
            db_session=db_session,
            customer_email="john@example.com",
            conversation_id=str(conv1.id),
            channel="email",
        )

        agent_session1 = PostgresSession(
            session=db_session,
            conversation_id=conv1.id,
            channel=Channel.EMAIL,
        )

        hooks1 = RunHooks(
            session=db_session,
            conversation_id=conv1.id,
            correlation_id=str(conv1.id),
        )

        result1 = await Runner.run(
            customer_success_agent,
            "I need help with my account",
            session=agent_session1,
            context=context1,
            hooks=hooks1,
        )

        # Extract tool calls from first scenario
        tool_calls_1 = []
        tool_outputs_1 = []
        for item in result1.new_items:
            raw_item = item.raw_item
            if isinstance(raw_item, ResponseFunctionToolCall):
                tool_calls_1.append({
                    "name": raw_item.name,
                    "arguments": raw_item.arguments,
                    "call_id": raw_item.call_id,
                })
            elif isinstance(raw_item, dict) and raw_item.get("type", '') == "function_call_output":
                tool_outputs_1.append({
                    "call_id": raw_item.get("call_id"),
                    "output": raw_item.get("output"),
                })

        assert result1.final_output, "Agent should provide a final output for email channel"

        # Verify identify_customer was called via email
        identify_call_1 = next((tc for tc in tool_calls_1 if tc["name"] == "identify_customer"), None)
        assert identify_call_1 is not None, "identify_customer should be called for email channel"
        assert identify_call_1["arguments"] == "{}", "identify_customer should be called with no arguments"

        # Verify customer was identified via email
        customer_id_1 = context1.customer_id
        assert customer_id_1 == str(customer.id), "Customer should be identified via email"
        assert context1.customer_email == "john@example.com", "Email should be set in context"

        # Verify identification output
        identify_output_1 = next((to for to in tool_outputs_1 if any(tc["call_id"] == to["call_id"] and tc["name"] == "identify_customer" for tc in tool_calls_1)), None)
        assert identify_output_1 is not None, "identify_customer should have output"
        assert "Customer identified" in identify_output_1["output"], "Should confirm customer identification"
        assert str(customer.id) in identify_output_1["output"], "Output should contain customer ID"

        await db_session.commit()

        # Verify messages were stored for email conversation
        messages_1 = await get_conversation_history(db_session, conv1.id, limit=10, offset=0)
        assert len(messages_1) >= 2, "Should have messages for email conversation"

        # Scenario 2: Same customer contacts via WhatsApp (phone)
        conv2 = await create_conversation(
            db_session,
            customer.id,
            Channel.WHATSAPP,
            ConversationStatus.ACTIVE,
        )

        await db_session.commit()

        context2 = CustomerSuccessContext(
            db_session=db_session,
            customer_phone="+1234567890",
            conversation_id=str(conv2.id),
            channel="whatsapp",
        )

        agent_session2 = PostgresSession(
            session=db_session,
            conversation_id=conv2.id,
            channel=Channel.WHATSAPP,
        )

        hooks2 = RunHooks(
            session=db_session,
            conversation_id=conv2.id,
            correlation_id=str(conv2.id),
        )

        result2 = await Runner.run(
            customer_success_agent,
            "I need help with my account",
            session=agent_session2,
            context=context2,
            hooks=hooks2,
        )

        # Extract tool calls from second scenario
        tool_calls_2 = []
        tool_outputs_2 = []
        for item in result2.new_items:
            raw_item = item.raw_item
            if isinstance(raw_item, ResponseFunctionToolCall):
                tool_calls_2.append({
                    "name": raw_item.name,
                    "arguments": raw_item.arguments,
                    "call_id": raw_item.call_id,
                })
            elif isinstance(raw_item, dict) and raw_item.get("type", '') == "function_call_output":
                tool_outputs_2.append({
                    "call_id": raw_item.get("call_id"),
                    "output": raw_item.get("output"),
                })

        assert result2.final_output, "Agent should provide a final output for WhatsApp channel"

        # Verify identify_customer was called via phone
        identify_call_2 = next((tc for tc in tool_calls_2 if tc["name"] == "identify_customer"), None)
        assert identify_call_2 is not None, "identify_customer should be called for WhatsApp channel"
        assert identify_call_2["arguments"] == "{}", "identify_customer should be called with no arguments"

        # Verify customer was identified via phone
        customer_id_2 = context2.customer_id
        assert customer_id_2 == str(customer.id), "Customer should be identified via phone"
        assert context2.customer_phone == "+1234567890", "Phone should be set in context"

        # Verify identification output
        identify_output_2 = next((to for to in tool_outputs_2 if any(tc["call_id"] == to["call_id"] and tc["name"] == "identify_customer" for tc in tool_calls_2)), None)
        assert identify_output_2 is not None, "identify_customer should have output"
        assert "Customer identified" in identify_output_2["output"], "Should confirm customer identification"
        assert str(customer.id) in identify_output_2["output"], "Output should contain customer ID"

        # CRITICAL: Verify same customer was identified across both channels (cross-channel unification)
        assert customer_id_1 == customer_id_2, "Same customer should be identified across email and WhatsApp"
        assert customer_id_1 == str(customer.id), "Customer ID should match the original customer"

        await db_session.commit()

        # Verify messages were stored for WhatsApp conversation
        messages_2 = await get_conversation_history(db_session, conv2.id, limit=10, offset=0)
        assert len(messages_2) >= 2, "Should have messages for WhatsApp conversation"

        # Verify both conversations are linked to the same customer in database
        conv1_updated = await get_conversation(db_session, conv1.id)
        conv2_updated = await get_conversation(db_session, conv2.id)
        assert conv1_updated.customer_id == customer.id, "Email conversation should be linked to customer"
        assert conv2_updated.customer_id == customer.id, "WhatsApp conversation should be linked to customer"
        assert conv1_updated.customer_id == conv2_updated.customer_id, "Both conversations should link to same customer"

    @pytest.mark.asyncio
    async def test_context_state_management(self, db_session: AsyncSession, test_customer: Customer):
        """Test context state is properly managed during agent execution."""
        # Setup: Create customer identifier
        await create_customer_identifier(
            db_session,
            test_customer.id,
            IdentifierType.EMAIL,
            test_customer.email,
        )

        # Create conversation
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await db_session.commit()

        # Create context with customer email
        context = CustomerSuccessContext(
            db_session=db_session,
            customer_email=test_customer.email,
            conversation_id=str(conversation.id),
            channel="api",
        )

        # Verify initial state
        assert context.customer_id is None
        assert context.ticket_id is None
        assert context.escalation_triggered is False

        # Create session and hooks
        agent_session = PostgresSession(
            session=db_session,
            conversation_id=conversation.id,
            channel=Channel.API,
        )

        hooks = RunHooks(
            session=db_session,
            conversation_id=conversation.id,
            correlation_id=str(conversation.id),
        )

        # Run agent - should identify customer and maintain state
        result = await Runner.run(
            customer_success_agent,
            "I need help with a technical issue",
            session=agent_session,
            context=context,
            hooks=hooks,
        )

        # Extract tool calls and outputs from result
        tool_calls = []
        tool_outputs = []
        for item in result.new_items:
            raw_item = item.raw_item
            if isinstance(raw_item, ResponseFunctionToolCall):
                tool_calls.append({
                    "name": raw_item.name,
                    "arguments": raw_item.arguments,
                    "call_id": raw_item.call_id,
                })
            elif isinstance(raw_item, dict) and raw_item.get("type", '') == "function_call_output":
                tool_outputs.append({
                    "call_id": raw_item.get("call_id"),
                    "output": raw_item.get("output"),
                })

        # Verify agent provided a response
        assert result.final_output, "Agent should provide a final output"
        assert len(result.final_output) > 0, "Final output should not be empty"

        # Verify identify_customer was called
        identify_call = next((tc for tc in tool_calls if tc["name"] == "identify_customer"), None)
        assert identify_call is not None, "identify_customer tool should be called"
        assert identify_call["arguments"] == "{}", "identify_customer should be called with no arguments"

        # Verify customer was identified during execution (context state updated)
        assert context.customer_id == str(test_customer.id), "Customer ID should be set in context"
        assert context.customer_email == test_customer.email, "Customer email should be set in context"

        # Verify conversation context is maintained throughout execution
        assert context.conversation_id == str(conversation.id), "Conversation ID should remain unchanged"
        assert context.channel == "api", "Channel should remain unchanged"

        # Verify context state for optional fields (should remain as initialized)
        assert context.ticket_id is None, "Ticket ID should remain None (no ticket created)"
        assert context.escalation_triggered is False, "Escalation should not be triggered"
        assert context.escalation_reason is None, "Escalation reason should remain None"

        # Verify db_session is maintained in context
        assert context.db_session is not None, "Database session should be maintained in context"
        assert context.db_session == db_session, "Database session should be the same instance"

        # Verify tool outputs confirm successful identification
        identify_output = next((to for to in tool_outputs if any(tc["call_id"] == to["call_id"] and tc["name"] == "identify_customer" for tc in tool_calls)), None)
        assert identify_output is not None, "identify_customer should have output"
        assert "Customer identified" in identify_output["output"], "Should confirm customer identification"
        assert str(test_customer.id) in identify_output["output"], "Output should contain customer ID"

        await db_session.commit()

        # Verify messages were stored in database
        messages = await get_conversation_history(db_session, conversation.id, limit=10, offset=0)
        assert len(messages) >= 2, "Should have at least user message and agent response"

        user_messages = [m for m in messages if m.role == MessageRole.CUSTOMER]
        agent_messages = [m for m in messages if m.role == MessageRole.AGENT]

        assert len(user_messages) >= 1, "Should have at least one user message"
        assert len(agent_messages) >= 1, "Should have at least one agent message"
        assert "technical" in user_messages[0].content.lower(), "User message should mention technical issue"

        # Verify conversation state in database remains active
        updated_conv = await get_conversation(db_session, conversation.id)
        assert updated_conv is not None, "Conversation should exist in database"
        assert updated_conv.status == ConversationStatus.ACTIVE, "Conversation should remain active"
        assert updated_conv.customer_id == test_customer.id, "Conversation should be linked to customer"

    @pytest.mark.asyncio
    @pytest.mark.skip
    async def test_error_handling_in_workflow(self, db_session):
        """Test agent handles errors gracefully when customer is not found."""
        # Create conversation without customer
        conversation = await create_conversation(
            db_session,
            None,  # No customer_id
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await db_session.commit()

        # Create context with non-existent customer email
        context = CustomerSuccessContext(
            db_session=db_session,
            customer_email="nonexistent@example.com",
            conversation_id=str(conversation.id),
            channel="api",
        )

        # Create session and hooks
        agent_session = PostgresSession(
            session=db_session,
            conversation_id=conversation.id,
            channel=Channel.API,
        )

        hooks = RunHooks(
            session=db_session,
            conversation_id=conversation.id,
            correlation_id=str(conversation.id),
        )

        # Run agent with non-existent customer
        result = await Runner.run(
            customer_success_agent,
            "I need help with my account",
            session=agent_session,
            context=context,
            hooks=hooks,
        )

        # Verify agent provided a response (should handle gracefully)
        assert result.final_output

        # Agent should either create a new customer or inform about the issue
        # The exact behavior depends on the agent's implementation



# a = [  # raw_items output from 129
#     ResponseFunctionToolCall(
#         arguments='{}', 
#         call_id='function-call-1931015022371397987', 
#         name='identify_customer', 
#         type='function_call', 
#         id='__fake_id__', 
#         status=None, 
#         provider_data={'model': 'gemini-2.5-flash', 'response_id': 'Fx2jafG-BK7xxN8PzIj6kA4'}
#     ), 
#     {
#         'call_id': 'function-call-1931015022371397987', 
#         'output': 'Customer identified: Test Customer (ID: 7adf9b03-1398-4586-b07e-e739204bc71d). Account tier: standard', 
#         'type': 'function_call_output'
#     },
#     ResponseFunctionToolCall(
#         arguments='{"query":"How do I reset my password?"}', 
#         call_id='function-call-14171787214332623690', 
#         name='search_knowledge_base', 
#         type='function_call', 
#         id='__fake_id__', 
#         status=None, provider_data={'model': 'gemini-2.5-flash', 'response_id': 'GR2jacSPO_Sf28oP_KznYQ'}
#     ), 
#     {
#         'call_id': 'function-call-14171787214332623690', 
#         'output': 'Found 1 relevant articles:\n\n1. Password Reset Guide (relevance: 85%)\n To reset your password, go to Settings > Security.\n\n', 'type': 'function_call_output'
#     }, 
#     ResponseOutputMessage(
#         id='__fake_id__', 
#         content=[
#             ResponseOutputText(annotations=[], text='To reset your password, please navigate to your "Settings" and then select "Security." You should find the option to reset your password there.\n\nIf you have any further issues or can\'t find the option, please let me know!\n', type='output_text', logprobs=[])
#         ], 
#         role='assistant', 
#         status='completed', 
#         type='message', phase=None, 
#         provider_data={'model': 'gemini-2.5-flash', 'response_id': 'HB2jaZGyCqvTvdIP2-DFIQ'}
#     ),                            
#     ResponseFunctionToolCall(
#         arguments='{"response_text":"To reset your password, please navigate to your \\"Settings\\" and then select \\"Security.\\" You should find the option to reset your password there.\\n\\nIf you have any further issues or can\'t find the option, please let me know!"}', 
#         call_id='function-call-3750653453125530766', 
#         name='send_response', 
#         type='function_call', 
#         id='__fake_id__', 
#         status=None,
#         provider_data={'model': 'gemini-2.5-flash', 'response_id': 'HB2jaZGyCqvTvdIP2-DFIQ'}
#     ),
#     {
#         'call_id': 'function-call-3750653453125530766', 
#         'output': "Error sending response: create_message() missing 1 required positional argument: 'channel'", 
#         'type': 'function_call_output'
#     }, 
#     ResponseOutputMessage(
#         id='__fake_id__', 
#         content=[
#             ResponseOutputText(annotations=[], text='To reset your password, please navigate to your "Settings" and then select "Security." You should find the option to reset your password there.\n\nIf you have any further issues or can\'t find the option, please let me know!', type='output_text', logprobs=[])
#         ], 
#         role='assistant', 
#         status='completed', 
#         type='message', 
#         phase=None, 
#         provider_data={'model': 'gemini-2.5-flash', 'response_id': 'Hh2jadzWA4uAxs0P0MCgqAw'}
#     )
# ]
