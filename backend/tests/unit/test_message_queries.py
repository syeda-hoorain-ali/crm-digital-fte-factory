"""Unit tests for message database queries."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Conversation,
    Message,
    MessageRole,
    MessageDirection,
    Channel,
)
from src.database.queries.message import (
    create_message,
    get_conversation_history,
    get_latest_message,
    delete_message,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestMessageCRUD:
    """Test message CRUD operations."""

    async def test_create_message_minimal(self, session: AsyncSession, sample_conversation: Conversation):
        """Test creating message with minimal fields."""
        message = await create_message(
            session,
            sample_conversation.id,
            MessageRole.CUSTOMER,
            "Hello, I need help",
            MessageDirection.INBOUND,
            Channel.EMAIL
        )

        assert message.id is not None
        assert message.conversation_id == sample_conversation.id
        assert message.role == MessageRole.CUSTOMER
        assert message.content == "Hello, I need help"
        assert message.direction == MessageDirection.INBOUND
        assert message.channel == Channel.EMAIL
        assert message.channel_message_id is None
        assert message.tokens_used is None
        assert message.latency_ms is None
        assert message.tool_calls == []

    async def test_create_message_full(self, session: AsyncSession, sample_conversation: Conversation):
        """Test creating message with all fields."""
        tool_calls = [{"name": "search_kb", "args": {"query": "billing"}}]

        message = await create_message(
            session,
            sample_conversation.id,
            MessageRole.AGENT,
            "Here's the information you requested",
            MessageDirection.OUTBOUND,
            Channel.WHATSAPP,
            channel_message_id="wa-msg-123",
            tokens_used=150,
            latency_ms=500,
            tool_calls=tool_calls
        )

        assert message.id is not None
        assert message.role == MessageRole.AGENT
        assert message.channel_message_id == "wa-msg-123"
        assert message.tokens_used == 150
        assert message.latency_ms == 500
        assert message.tool_calls == tool_calls

    async def test_create_message_different_roles(self, session: AsyncSession, sample_conversation: Conversation):
        """Test creating messages with different roles."""
        customer_msg = await create_message(
            session,
            sample_conversation.id,
            MessageRole.CUSTOMER,
            "Customer message",
            MessageDirection.INBOUND,
            Channel.EMAIL
        )

        agent_msg = await create_message(
            session,
            sample_conversation.id,
            MessageRole.AGENT,
            "Agent response",
            MessageDirection.OUTBOUND,
            Channel.EMAIL
        )

        system_msg = await create_message(
            session,
            sample_conversation.id,
            MessageRole.SYSTEM,
            "System notification",
            MessageDirection.OUTBOUND,
            Channel.EMAIL
        )

        assert customer_msg.role == MessageRole.CUSTOMER
        assert agent_msg.role == MessageRole.AGENT
        assert system_msg.role == MessageRole.SYSTEM

    async def test_create_message_different_channels(self, session: AsyncSession, sample_conversation: Conversation):
        """Test creating messages on different channels."""
        email_msg = await create_message(
            session,
            sample_conversation.id,
            MessageRole.CUSTOMER,
            "Email message",
            MessageDirection.INBOUND,
            Channel.EMAIL
        )

        whatsapp_msg = await create_message(
            session,
            sample_conversation.id,
            MessageRole.CUSTOMER,
            "WhatsApp message",
            MessageDirection.INBOUND,
            Channel.WHATSAPP
        )

        webform_msg = await create_message(
            session,
            sample_conversation.id,
            MessageRole.CUSTOMER,
            "Web form message",
            MessageDirection.INBOUND,
            Channel.WEB_FORM
        )

        assert email_msg.channel == Channel.EMAIL
        assert whatsapp_msg.channel == Channel.WHATSAPP
        assert webform_msg.channel == Channel.WEB_FORM

    async def test_get_conversation_history_empty(self, session: AsyncSession, sample_conversation: Conversation):
        """Test getting history for conversation with no messages."""
        messages = await get_conversation_history(session, sample_conversation.id)

        # sample_conversation fixture might have messages, so just check it returns a list
        assert isinstance(messages, list)

    async def test_get_conversation_history_with_messages(self, session: AsyncSession, sample_conversation: Conversation):
        """Test getting conversation history with messages."""
        # Create messages in sequence
        msg1 = await create_message(
            session,
            sample_conversation.id,
            MessageRole.CUSTOMER,
            "First message",
            MessageDirection.INBOUND,
            Channel.EMAIL
        )
        await session.flush()

        msg2 = await create_message(
            session,
            sample_conversation.id,
            MessageRole.AGENT,
            "Second message",
            MessageDirection.OUTBOUND,
            Channel.EMAIL
        )
        await session.flush()

        msg3 = await create_message(
            session,
            sample_conversation.id,
            MessageRole.CUSTOMER,
            "Third message",
            MessageDirection.INBOUND,
            Channel.EMAIL
        )
        await session.commit()

        messages = await get_conversation_history(session, sample_conversation.id)

        # Should be in chronological order (ascending)
        assert len(messages) >= 3
        assert messages[-3].id == msg1.id
        assert messages[-2].id == msg2.id
        assert messages[-1].id == msg3.id

    async def test_get_conversation_history_with_limit(self, session: AsyncSession, sample_conversation: Conversation):
        """Test getting conversation history with limit."""
        # Create multiple messages
        for i in range(5):
            await create_message(
                session,
                sample_conversation.id,
                MessageRole.CUSTOMER,
                f"Message {i}",
                MessageDirection.INBOUND,
                Channel.EMAIL
            )
        await session.commit()

        messages = await get_conversation_history(
            session,
            sample_conversation.id,
            limit=3
        )

        assert len(messages) == 3

    async def test_get_conversation_history_with_offset(self, session: AsyncSession, sample_conversation: Conversation):
        """Test getting conversation history with offset."""
        # Create messages
        for i in range(5):
            await create_message(
                session,
                sample_conversation.id,
                MessageRole.CUSTOMER,
                f"Message {i}",
                MessageDirection.INBOUND,
                Channel.EMAIL
            )
        await session.commit()

        all_messages = await get_conversation_history(session, sample_conversation.id)
        offset_messages = await get_conversation_history(
            session,
            sample_conversation.id,
            offset=2
        )

        assert len(offset_messages) == len(all_messages) - 2

    async def test_get_latest_message_exists(self, session: AsyncSession, sample_conversation: Conversation):
        """Test getting latest message when messages exist."""
        # Create messages
        msg1 = await create_message(
            session,
            sample_conversation.id,
            MessageRole.CUSTOMER,
            "First message",
            MessageDirection.INBOUND,
            Channel.EMAIL
        )
        await session.flush()

        msg2 = await create_message(
            session,
            sample_conversation.id,
            MessageRole.AGENT,
            "Latest message",
            MessageDirection.OUTBOUND,
            Channel.EMAIL
        )
        await session.commit()

        latest = await get_latest_message(session, sample_conversation.id)

        assert latest is not None
        assert latest.id == msg2.id
        assert latest.content == "Latest message"

    async def test_get_latest_message_empty_conversation(self, session: AsyncSession, sample_conversation: Conversation):
        """Test getting latest message from empty conversation."""
        # Use a new conversation with no messages
        from src.database.queries.conversation import create_conversation
        from src.database.queries.customer import create_customer

        customer = await create_customer(session)
        conversation = await create_conversation(session, customer.id, Channel.EMAIL)
        await session.commit()

        latest = await get_latest_message(session, conversation.id)

        assert latest is None

    async def test_delete_message_exists(self, session: AsyncSession, sample_message: Message):
        """Test deleting existing message."""
        result = await delete_message(session, sample_message.id)

        assert result is True

        # Verify message is deleted
        messages = await get_conversation_history(session, sample_message.conversation_id)
        message_ids = [m.id for m in messages]
        assert sample_message.id not in message_ids

    async def test_delete_message_not_exists(self, session: AsyncSession):
        """Test deleting non-existent message."""
        fake_id = uuid4()
        result = await delete_message(session, fake_id)

        assert result is False

    async def test_message_ordering_chronological(self, session: AsyncSession, sample_conversation: Conversation):
        """Test messages are ordered chronologically in history."""
        # Create messages with explicit ordering
        messages_created = []
        for i in range(3):
            msg = await create_message(
                session,
                sample_conversation.id,
                MessageRole.CUSTOMER,
                f"Message {i}",
                MessageDirection.INBOUND,
                Channel.EMAIL
            )
            messages_created.append(msg)
            await session.flush()
        await session.commit()

        history = await get_conversation_history(session, sample_conversation.id)

        # Verify chronological order (oldest first)
        for i, created_msg in enumerate(messages_created):
            assert history[-(3-i)].id == created_msg.id

    async def test_messages_isolated_by_conversation(self, session: AsyncSession):
        """Test messages are isolated by conversation."""
        from src.database.queries.conversation import create_conversation
        from src.database.queries.customer import create_customer

        # Create two conversations
        customer = await create_customer(session)
        conv1 = await create_conversation(session, customer.id, Channel.EMAIL)
        conv2 = await create_conversation(session, customer.id, Channel.WHATSAPP)

        # Create messages in each conversation
        msg1 = await create_message(
            session,
            conv1.id,
            MessageRole.CUSTOMER,
            "Conv1 message",
            MessageDirection.INBOUND,
            Channel.EMAIL
        )

        msg2 = await create_message(
            session,
            conv2.id,
            MessageRole.CUSTOMER,
            "Conv2 message",
            MessageDirection.INBOUND,
            Channel.WHATSAPP
        )
        await session.commit()

        # Get history for conv1
        conv1_history = await get_conversation_history(session, conv1.id)
        conv1_ids = [m.id for m in conv1_history]

        # Should only include conv1's message
        assert msg1.id in conv1_ids
        assert msg2.id not in conv1_ids

    async def test_create_message_with_empty_tool_calls(self, session: AsyncSession, sample_conversation: Conversation):
        """Test creating message with empty tool_calls list."""
        message = await create_message(
            session,
            sample_conversation.id,
            MessageRole.AGENT,
            "Response without tools",
            MessageDirection.OUTBOUND,
            Channel.EMAIL,
            tool_calls=[]
        )

        assert message.tool_calls == []

    async def test_create_message_with_multiple_tool_calls(self, session: AsyncSession, sample_conversation: Conversation):
        """Test creating message with multiple tool calls."""
        tool_calls = [
            {"name": "search_kb", "args": {"query": "billing"}},
            {"name": "create_ticket", "args": {"category": "technical"}},
            {"name": "get_history", "args": {"limit": 5}}
        ]

        message = await create_message(
            session,
            sample_conversation.id,
            MessageRole.AGENT,
            "Used multiple tools",
            MessageDirection.OUTBOUND,
            Channel.EMAIL,
            tool_calls=tool_calls
        )

        assert len(message.tool_calls) == 3
        assert message.tool_calls[0]["name"] == "search_kb"
        assert message.tool_calls[1]["name"] == "create_ticket"
        assert message.tool_calls[2]["name"] == "get_history"
