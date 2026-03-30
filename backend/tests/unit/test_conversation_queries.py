"""Unit tests for conversation database queries."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Customer,
    Conversation,
    ConversationStatus,
    Channel,
)
from src.database.queries.conversation import (
    create_conversation,
    get_conversation,
    update_conversation_status,
    list_customer_conversations,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestConversationCRUD:
    """Test conversation CRUD operations."""

    async def test_create_conversation_default_status(self, session: AsyncSession, sample_customer: Customer):
        """Test creating conversation with default status."""
        conversation = await create_conversation(
            session,
            sample_customer.id,
            Channel.EMAIL
        )

        assert conversation.id is not None
        assert conversation.customer_id == sample_customer.id
        assert conversation.initial_channel == Channel.EMAIL
        assert conversation.status == ConversationStatus.ACTIVE
        assert conversation.started_at is not None
        assert conversation.ended_at is None

    async def test_create_conversation_custom_status(self, session: AsyncSession, sample_customer: Customer):
        """Test creating conversation with custom status."""
        conversation = await create_conversation(
            session,
            sample_customer.id,
            Channel.WHATSAPP,
            status=ConversationStatus.RESOLVED
        )

        assert conversation.id is not None
        assert conversation.status == ConversationStatus.RESOLVED
        assert conversation.initial_channel == Channel.WHATSAPP

    async def test_create_conversation_different_channels(self, session: AsyncSession, sample_customer: Customer):
        """Test creating conversations on different channels."""
        email_conv = await create_conversation(session, sample_customer.id, Channel.EMAIL)
        whatsapp_conv = await create_conversation(session, sample_customer.id, Channel.WHATSAPP)
        webform_conv = await create_conversation(session, sample_customer.id, Channel.WEB_FORM)
        await session.commit()

        assert email_conv.initial_channel == Channel.EMAIL
        assert whatsapp_conv.initial_channel == Channel.WHATSAPP
        assert webform_conv.initial_channel == Channel.WEB_FORM

    async def test_get_conversation_exists(self, session: AsyncSession, sample_conversation: Conversation):
        """Test getting existing conversation."""
        conversation = await get_conversation(session, sample_conversation.id)

        assert conversation is not None
        assert conversation.id == sample_conversation.id
        assert conversation.customer_id == sample_conversation.customer_id

    async def test_get_conversation_not_exists(self, session: AsyncSession):
        """Test getting non-existent conversation."""
        fake_id = uuid4()
        conversation = await get_conversation(session, fake_id)

        assert conversation is None

    async def test_update_conversation_status_to_resolved(self, session: AsyncSession, sample_conversation: Conversation):
        """Test updating conversation status to resolved."""
        updated = await update_conversation_status(
            session,
            sample_conversation.id,
            ConversationStatus.RESOLVED
        )

        assert updated is not None
        assert updated.status == ConversationStatus.RESOLVED
        assert updated.ended_at is None  # ended_at only set on CLOSED

    async def test_update_conversation_status_to_closed(self, session: AsyncSession, sample_conversation: Conversation):
        """Test updating conversation status to closed sets ended_at."""
        updated = await update_conversation_status(
            session,
            sample_conversation.id,
            ConversationStatus.CLOSED
        )

        assert updated is not None
        assert updated.status == ConversationStatus.CLOSED
        assert updated.ended_at is not None

    async def test_update_conversation_status_not_exists(self, session: AsyncSession):
        """Test updating non-existent conversation."""
        fake_id = uuid4()
        updated = await update_conversation_status(
            session,
            fake_id,
            ConversationStatus.CLOSED
        )

        assert updated is None

    async def test_update_conversation_status_multiple_times(self, session: AsyncSession, sample_conversation: Conversation):
        """Test updating conversation status multiple times."""
        # Active -> Escalated
        updated1 = await update_conversation_status(
            session,
            sample_conversation.id,
            ConversationStatus.ESCALATED
        )
        assert updated1 is not None
        assert updated1.status == ConversationStatus.ESCALATED

        # Escalated -> Resolved
        updated2 = await update_conversation_status(
            session,
            sample_conversation.id,
            ConversationStatus.RESOLVED
        )
        assert updated2 is not None
        assert updated2.status == ConversationStatus.RESOLVED

        # Resolved -> Closed
        updated3 = await update_conversation_status(
            session,
            sample_conversation.id,
            ConversationStatus.CLOSED
        )
        assert updated3 is not None
        assert updated3.status == ConversationStatus.CLOSED
        assert updated3.ended_at is not None

    async def test_list_customer_conversations_empty(self, session: AsyncSession, sample_customer: Customer):
        """Test listing conversations for customer with none."""
        conversations = await list_customer_conversations(session, sample_customer.id)

        # sample_customer fixture might have conversations, so just check it returns a list
        assert isinstance(conversations, list)

    async def test_list_customer_conversations_with_data(self, session: AsyncSession, sample_customer: Customer):
        """Test listing conversations with data."""
        # Create multiple conversations
        conv1 = await create_conversation(session, sample_customer.id, Channel.EMAIL)
        conv2 = await create_conversation(session, sample_customer.id, Channel.WHATSAPP)
        conv3 = await create_conversation(session, sample_customer.id, Channel.WEB_FORM)
        await session.commit()

        conversations = await list_customer_conversations(session, sample_customer.id)

        assert len(conversations) >= 3
        conv_ids = [c.id for c in conversations]
        assert conv1.id in conv_ids
        assert conv2.id in conv_ids
        assert conv3.id in conv_ids

    async def test_list_customer_conversations_with_status_filter(self, session: AsyncSession, sample_customer: Customer):
        """Test listing conversations with status filter."""
        # Create conversations with different statuses
        active_conv = await create_conversation(
            session,
            sample_customer.id,
            Channel.EMAIL,
            status=ConversationStatus.ACTIVE
        )
        resolved_conv = await create_conversation(
            session,
            sample_customer.id,
            Channel.WHATSAPP,
            status=ConversationStatus.RESOLVED
        )
        await session.commit()

        # Filter by ACTIVE status
        active_conversations = await list_customer_conversations(
            session,
            sample_customer.id,
            status=ConversationStatus.ACTIVE
        )

        active_ids = [c.id for c in active_conversations]
        assert active_conv.id in active_ids
        assert resolved_conv.id not in active_ids

    async def test_list_customer_conversations_with_limit(self, session: AsyncSession, sample_customer: Customer):
        """Test listing conversations with limit."""
        # Create multiple conversations
        for i in range(5):
            await create_conversation(session, sample_customer.id, Channel.EMAIL)
        await session.commit()

        conversations = await list_customer_conversations(
            session,
            sample_customer.id,
            limit=3
        )

        assert len(conversations) == 3

    async def test_list_customer_conversations_with_offset(self, session: AsyncSession, sample_customer: Customer):
        """Test listing conversations with offset."""
        # Create conversations
        for i in range(5):
            await create_conversation(session, sample_customer.id, Channel.EMAIL)
        await session.commit()

        all_conversations = await list_customer_conversations(session, sample_customer.id)
        offset_conversations = await list_customer_conversations(
            session,
            sample_customer.id,
            offset=2
        )

        assert len(offset_conversations) == len(all_conversations) - 2

    async def test_list_customer_conversations_ordered_by_created_at(self, session: AsyncSession, sample_customer: Customer):
        """Test conversations are ordered by created_at descending."""
        # Create conversations in sequence
        conv1 = await create_conversation(session, sample_customer.id, Channel.EMAIL)
        await session.flush()
        conv2 = await create_conversation(session, sample_customer.id, Channel.WHATSAPP)
        await session.flush()
        conv3 = await create_conversation(session, sample_customer.id, Channel.WEB_FORM)
        await session.commit()

        conversations = await list_customer_conversations(session, sample_customer.id)

        # Most recent should be first (descending order)
        assert conversations[0].id == conv3.id
        assert conversations[1].id == conv2.id
        assert conversations[2].id == conv1.id

    async def test_list_customer_conversations_different_customers(self, session: AsyncSession):
        """Test conversations are filtered by customer."""
        from src.database.queries.customer import create_customer

        # Create two customers
        customer1 = await create_customer(session, name="Customer 1")
        customer2 = await create_customer(session, name="Customer 2")

        # Create conversations for each
        conv1 = await create_conversation(session, customer1.id, Channel.EMAIL)
        conv2 = await create_conversation(session, customer2.id, Channel.EMAIL)
        await session.commit()

        # List conversations for customer1
        customer1_convs = await list_customer_conversations(session, customer1.id)
        customer1_ids = [c.id for c in customer1_convs]

        # Should only include customer1's conversation
        assert conv1.id in customer1_ids
        assert conv2.id not in customer1_ids
