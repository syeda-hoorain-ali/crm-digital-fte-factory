"""Unit tests for PostgreSQL session transformations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.agent.session import PostgresSession
from src.database.models import Message, MessageRole, MessageDirection, Channel


# ============================================================================
# Tests for PostgresSession (T081)
# ============================================================================

@pytest.mark.unit
@pytest.mark.session
class TestPostgresSession:
    """Unit tests for PostgresSession message transformations."""

    def test_session_initialization(self):
        """Test PostgresSession initializes with session, conversation_id, and channel."""
        mock_session = MagicMock()
        conversation_id = uuid4()

        pg_session = PostgresSession(mock_session, conversation_id, Channel.API)

        assert pg_session.session == mock_session
        assert pg_session.conversation_id == conversation_id
        assert pg_session.channel == Channel.API

    @pytest.mark.asyncio
    async def test_get_items_transforms_messages(self):
        """Test get_items transforms database messages to SDK format."""
        mock_session = MagicMock()
        conversation_id = uuid4()

        # Mock database messages
        mock_messages = [
            Message(
                id=uuid4(),
                conversation_id=conversation_id,
                channel="api",
                direction=MessageDirection.INBOUND,
                role=MessageRole.CUSTOMER,
                content="Hello, I need help",
                created_at=MagicMock(),
            ),
            Message(
                id=uuid4(),
                conversation_id=conversation_id,
                channel="api",
                direction=MessageDirection.OUTBOUND,
                role=MessageRole.AGENT,
                content="I'd be happy to help!",
                created_at=MagicMock(),
            ),
        ]

        pg_session = PostgresSession(mock_session, conversation_id, Channel.API)

        with patch(
            "src.agent.session.get_conversation_history",
            new_callable=AsyncMock,
        ) as mock_get_history:
            mock_get_history.return_value = mock_messages

            items = await pg_session.get_items()

            # Verify transformation
            assert len(items) == 2
            assert items[0]["role"] == "user"  # CUSTOMER -> user
            assert items[0]["content"] == "Hello, I need help"
            assert items[1]["role"] == "assistant"  # AGENT -> assistant
            assert items[1]["content"] == "I'd be happy to help!"

    @pytest.mark.asyncio
    async def test_add_items_creates_messages(self):
        """Test add_items transforms SDK messages to database format."""
        mock_session = MagicMock()
        conversation_id = uuid4()

        pg_session = PostgresSession(mock_session, conversation_id, Channel.API)

        sdk_messages = [
            {"role": "user", "content": "What is my account balance?"},
            {"role": "assistant", "content": "Your current balance is $100."},
        ]

        with patch(
            "src.agent.session.create_message",
            new_callable=AsyncMock,
        ) as mock_create_message:
            await pg_session.add_items(sdk_messages)

            # Verify messages were created
            assert mock_create_message.call_count == 2

            # Verify first call (user message)
            first_call = mock_create_message.call_args_list[0]
            assert first_call[1]["role"] == MessageRole.CUSTOMER
            assert first_call[1]["content"] == "What is my account balance?"
            assert first_call[1]["direction"] == MessageDirection.INBOUND

    @pytest.mark.asyncio
    async def test_pop_item_removes_latest_message(self):
        """Test pop_item removes and returns the latest message."""
        mock_session = MagicMock()
        conversation_id = uuid4()

        latest_message = Message(
            id=uuid4(),
            conversation_id=conversation_id,
            channel="api",
            direction=MessageDirection.OUTBOUND,
            role=MessageRole.AGENT,
            content="Latest message",
            created_at=MagicMock(),
        )

        pg_session = PostgresSession(mock_session, conversation_id, Channel.API)

        with patch(
            "src.agent.session.get_latest_message",
            new_callable=AsyncMock,
        ) as mock_get_latest, patch(
            "src.agent.session.delete_message",
            new_callable=AsyncMock,
        ) as mock_delete:
            mock_get_latest.return_value = latest_message
            mock_delete.return_value = True

            popped = await pg_session.pop_item()

            # Verify message was returned in SDK format
            assert popped is not None
            assert popped["role"] == "assistant"
            assert popped["content"] == "Latest message"

            # Verify delete was called
            mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_pop_item_empty_conversation(self):
        """Test pop_item returns None for empty conversation."""
        mock_session = MagicMock()
        conversation_id = uuid4()

        pg_session = PostgresSession(mock_session, conversation_id, Channel.API)

        with patch(
            "src.agent.session.get_latest_message",
            new_callable=AsyncMock,
        ) as mock_get_latest:
            mock_get_latest.return_value = None

            popped = await pg_session.pop_item()

            assert popped is None

    @pytest.mark.asyncio
    async def test_clear_session_preserves_data(self):
        """Test clear_session is a no-op (preserves message data)."""
        mock_session = MagicMock()
        conversation_id = uuid4()

        pg_session = PostgresSession(mock_session, conversation_id, Channel.API)

        # Should not raise any errors and should not delete anything
        await pg_session.clear_session()

        # Verify no database operations were performed
        mock_session.execute.assert_not_called()

    def test_map_role_to_sdk(self):
        """Test _map_role_to_sdk converts database roles to SDK roles."""
        assert PostgresSession._map_role_to_sdk(MessageRole.CUSTOMER) == "user"
        assert PostgresSession._map_role_to_sdk(MessageRole.AGENT) == "assistant"
        assert PostgresSession._map_role_to_sdk(MessageRole.SYSTEM) == "system"

    def test_map_role_from_sdk(self):
        """Test _map_role_from_sdk converts SDK roles to database roles."""
        assert PostgresSession._map_role_from_sdk("user") == MessageRole.CUSTOMER
        assert PostgresSession._map_role_from_sdk("assistant") == MessageRole.AGENT
        assert PostgresSession._map_role_from_sdk("system") == MessageRole.SYSTEM
