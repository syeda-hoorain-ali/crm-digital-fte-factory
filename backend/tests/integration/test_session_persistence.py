"""Integration tests for PostgresSession persistence with real database."""

import pytest
from uuid import uuid4
from typing import cast, List
from agents import TResponseInputItem
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.session import PostgresSession
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
    create_conversation,
    create_message,
    get_conversation_history,
)


# ============================================================================
# Integration Tests for PostgresSession Persistence (T091)
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
@pytest.mark.session
class TestPostgresSessionPersistence:
    """Integration tests for PostgresSession with real database."""

    @pytest.mark.asyncio
    async def test_get_items_retrieves_from_database(
        self, db_session: AsyncSession, test_customer: Customer
    ):
        """Test get_items retrieves messages from database."""
        # Create conversation
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        # Create messages
        await create_message(
            db_session,
            conversation.id,
            MessageRole.CUSTOMER,
            "Hello, I need help",
            MessageDirection.INBOUND,
            Channel.API,
        )
        await create_message(
            db_session,
            conversation.id,
            MessageRole.AGENT,
            "I'd be happy to help!",
            MessageDirection.OUTBOUND,
            Channel.API,
        )

        await db_session.commit()

        # Create PostgresSession
        pg_session = PostgresSession(db_session, conversation.id, Channel.API)

        # Get items
        items = await pg_session.get_items()

        # Verify messages were retrieved
        assert len(items) == 2
        assert items[0].get("role") == "user"
        assert items[0].get("content") == "Hello, I need help"
        assert items[1].get("role") == "assistant"
        assert items[1].get("content") == "I'd be happy to help!"

    @pytest.mark.asyncio
    async def test_add_items_persists_to_database(
        self, db_session: AsyncSession, test_customer: Customer
    ):
        """Test add_items persists messages to database."""
        # Create conversation
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await db_session.commit()

        # Create PostgresSession
        pg_session = PostgresSession(db_session, conversation.id, Channel.API)

        # Add items
        items = [
            {"role": "user", "content": "What is my balance?"},
            {"role": "assistant", "content": "Your balance is $100."},
        ]

        await pg_session.add_items(cast(List[TResponseInputItem], items))
        await db_session.commit()

        # Verify messages were persisted
        messages = await get_conversation_history(
            db_session,
            conversation.id,
            limit=10,
            offset=0,
        )

        assert len(messages) == 2
        assert messages[0].role == MessageRole.CUSTOMER
        assert messages[0].content == "What is my balance?"
        assert messages[1].role == MessageRole.AGENT
        assert messages[1].content == "Your balance is $100."

    @pytest.mark.asyncio
    async def test_pop_item_removes_from_database(
        self, db_session: AsyncSession, test_customer: Customer
    ):
        """Test pop_item removes message from database."""
        # Create conversation with messages
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await create_message(
            db_session,
            conversation.id,
            MessageRole.CUSTOMER,
            "First message",
            MessageDirection.INBOUND,
            Channel.API,
        )
        await create_message(
            db_session,
            conversation.id,
            MessageRole.AGENT,
            "Second message",
            MessageDirection.OUTBOUND,
            Channel.API,
        )

        await db_session.commit()

        # Create PostgresSession
        pg_session = PostgresSession(db_session, conversation.id, Channel.API)

        # Pop item
        popped = await pg_session.pop_item()
        await db_session.commit()

        # Verify message was removed
        assert popped is not None
        assert popped["content"] == "Second message"

        # Verify only one message remains
        messages = await get_conversation_history(
            db_session,
            conversation.id,
            limit=10,
            offset=0,
        )

        assert len(messages) == 1
        assert messages[0].content == "First message"

    @pytest.mark.asyncio
    async def test_session_persistence_across_runs(
        self, db_session: AsyncSession, test_customer: Customer
    ):
        """Test session persists messages across multiple agent runs."""
        # Create conversation
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await db_session.commit()

        # First agent run - add messages
        pg_session_1 = PostgresSession(db_session, conversation.id, Channel.API)
        await pg_session_1.add_items([
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
        ])
        await db_session.commit()

        # Second agent run - retrieve and add more messages
        pg_session_2 = PostgresSession(db_session, conversation.id, Channel.API)
        items = await pg_session_2.get_items()

        # Verify previous messages are available
        assert len(items) == 2

        # Add more messages
        await pg_session_2.add_items([
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
        ])
        await db_session.commit()

        # Third agent run - verify all messages
        pg_session_3 = PostgresSession(db_session, conversation.id, Channel.API)
        all_items = await pg_session_3.get_items()

        assert len(all_items) == 4
        assert all_items[0].get("content") == "Message 1"
        assert all_items[3].get("content") == "Response 2"

    @pytest.mark.asyncio
    async def test_clear_session_preserves_data(
        self, db_session: AsyncSession, test_customer: Customer
    ):
        """Test clear_session does not delete messages (no-op)."""
        # Create conversation with messages
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await create_message(
            db_session,
            conversation.id,
            MessageRole.CUSTOMER,
            "Important message",
            MessageDirection.INBOUND,
            Channel.API,
        )

        await db_session.commit()

        # Create PostgresSession and clear
        pg_session = PostgresSession(db_session, conversation.id, Channel.API)
        await pg_session.clear_session()
        await db_session.commit()

        # Verify message still exists
        messages = await get_conversation_history(
            db_session,
            conversation.id,
            limit=10,
            offset=0,
        )

        assert len(messages) == 1
        assert messages[0].content == "Important message"

    @pytest.mark.asyncio
    async def test_session_handles_tool_calls(
        self, db_session: AsyncSession, test_customer: Customer
    ):
        """Test session correctly handles messages with tool_calls."""
        # Create conversation
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        # Create message with tool_calls
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "identify_customer",
                    "arguments": '{"email": "test@example.com"}',
                },
            }
        ]

        await create_message(
            db_session,
            conversation.id,
            MessageRole.AGENT,
            "Let me identify you",
            MessageDirection.OUTBOUND,
            Channel.API,
            tool_calls=tool_calls,
        )

        await db_session.commit()

        # Create PostgresSession and retrieve
        pg_session = PostgresSession(db_session, conversation.id, Channel.API)
        items = await pg_session.get_items()

        # Verify tool_calls are included
        assert len(items) == 1
        assert items[0].get("role") == "assistant"
        assert "tool_calls" in items[0]
        assert items[0].get("tool_calls") == tool_calls

    @pytest.mark.asyncio
    async def test_session_handles_empty_conversation(
        self, db_session: AsyncSession, test_customer: Customer
    ):
        """Test session handles conversation with no messages."""
        # Create empty conversation
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        await db_session.commit()

        # Create PostgresSession
        pg_session = PostgresSession(db_session, conversation.id, Channel.API)

        # Get items from empty conversation
        items = await pg_session.get_items()

        assert len(items) == 0

        # Pop from empty conversation
        popped = await pg_session.pop_item()

        assert popped is None

    @pytest.mark.asyncio
    async def test_session_maintains_message_order(
        self, db_session: AsyncSession, test_customer: Customer
    ):
        """Test session maintains chronological message order."""
        # Create conversation
        conversation = await create_conversation(
            db_session,
            test_customer.id,
            Channel.API,
            ConversationStatus.ACTIVE,
        )

        # Add messages in specific order
        messages_content = [
            "First message",
            "Second message",
            "Third message",
            "Fourth message",
        ]

        for i, content in enumerate(messages_content):
            role = MessageRole.CUSTOMER if i % 2 == 0 else MessageRole.AGENT
            direction = MessageDirection.INBOUND if i % 2 == 0 else MessageDirection.OUTBOUND

            await create_message(
                db_session,
                conversation.id,
                role,
                content,
                direction,
                Channel.API,
            )

        await db_session.commit()

        # Create PostgresSession and retrieve
        pg_session = PostgresSession(db_session, conversation.id, Channel.API)
        items = await pg_session.get_items()

        # Verify order is maintained
        assert len(items) == 4
        for i, item in enumerate(items):
            assert item.get("content") == messages_content[i]
