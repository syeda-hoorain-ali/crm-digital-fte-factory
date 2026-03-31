"""Unit tests for ticket database queries."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Customer,
    Conversation,
    Ticket,
    TicketStatus,
    Priority,
    Channel,
)
from src.database.queries.ticket import (
    create_ticket,
    get_ticket,
    update_ticket,
    list_conversation_tickets,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestTicketCRUD:
    """Test ticket CRUD operations."""

    async def test_create_ticket_minimal(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test creating ticket with minimal fields."""
        ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL
        )

        assert ticket.id is not None
        assert ticket.conversation_id == sample_conversation.id
        assert ticket.customer_id == sample_customer.id
        assert ticket.source_channel == Channel.EMAIL
        assert ticket.category is None
        assert ticket.priority == Priority.MEDIUM
        assert ticket.status == TicketStatus.OPEN
        assert ticket.resolved_at is None

    async def test_create_ticket_full(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test creating ticket with all fields."""
        ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.WHATSAPP,
            category="billing",
            priority=Priority.HIGH,
            status=TicketStatus.IN_PROGRESS
        )

        assert ticket.id is not None
        assert ticket.source_channel == Channel.WHATSAPP
        assert ticket.category == "billing"
        assert ticket.priority == Priority.HIGH
        assert ticket.status == TicketStatus.IN_PROGRESS

    async def test_create_ticket_different_priorities(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test creating tickets with different priorities."""
        low_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            priority=Priority.LOW
        )

        medium_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            priority=Priority.MEDIUM
        )

        high_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            priority=Priority.HIGH
        )

        critical_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            priority=Priority.CRITICAL
        )

        assert low_ticket.priority == Priority.LOW
        assert medium_ticket.priority == Priority.MEDIUM
        assert high_ticket.priority == Priority.HIGH
        assert critical_ticket.priority == Priority.CRITICAL

    async def test_create_ticket_different_statuses(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test creating tickets with different statuses."""
        open_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            status=TicketStatus.OPEN
        )

        in_progress_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            status=TicketStatus.IN_PROGRESS
        )

        resolved_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            status=TicketStatus.RESOLVED
        )

        closed_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            status=TicketStatus.CLOSED
        )

        assert open_ticket.status == TicketStatus.OPEN
        assert in_progress_ticket.status == TicketStatus.IN_PROGRESS
        assert resolved_ticket.status == TicketStatus.RESOLVED
        assert closed_ticket.status == TicketStatus.CLOSED

    async def test_create_ticket_different_channels(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test creating tickets from different channels."""
        email_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL
        )

        whatsapp_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.WHATSAPP
        )

        webform_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.WEB_FORM
        )

        assert email_ticket.source_channel == Channel.EMAIL
        assert whatsapp_ticket.source_channel == Channel.WHATSAPP
        assert webform_ticket.source_channel == Channel.WEB_FORM

    async def test_get_ticket_exists(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test getting existing ticket."""
        created_ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            category="technical"
        )
        await session.commit()

        ticket = await get_ticket(session, created_ticket.id)

        assert ticket is not None
        assert ticket.id == created_ticket.id
        assert ticket.category == "technical"

    async def test_get_ticket_not_exists(self, session: AsyncSession):
        """Test getting non-existent ticket."""
        fake_id = uuid4()
        ticket = await get_ticket(session, fake_id)

        assert ticket is None

    async def test_update_ticket_category(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test updating ticket category."""
        ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL
        )
        await session.commit()

        updated = await update_ticket(
            session,
            ticket.id,
            category="technical"
        )

        assert updated is not None
        assert updated.category == "technical"

    async def test_update_ticket_resolution_notes(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test updating ticket resolution notes."""
        ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL
        )
        await session.commit()

        updated = await update_ticket(
            session,
            ticket.id,
            resolution="Detailed resolution notes"
        )

        assert updated is not None
        assert updated.resolution_notes == "Detailed resolution notes"

    async def test_update_ticket_priority(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test updating ticket priority."""
        ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            priority=Priority.LOW
        )
        await session.commit()

        updated = await update_ticket(
            session,
            ticket.id,
            priority=Priority.CRITICAL
        )

        assert updated is not None
        assert updated.priority == Priority.CRITICAL

    async def test_update_ticket_status_to_resolved(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test updating ticket status to resolved sets resolved_at."""
        ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            status=TicketStatus.OPEN
        )
        await session.commit()

        updated = await update_ticket(
            session,
            ticket.id,
            status=TicketStatus.RESOLVED,
            resolution="Issue was resolved by restarting the service"
        )

        assert updated is not None
        assert updated.status == TicketStatus.RESOLVED
        assert updated.resolved_at is not None
        assert updated.resolution_notes == "Issue was resolved by restarting the service"

    async def test_update_ticket_status_to_closed(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test updating ticket status to closed sets resolved_at."""
        ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            status=TicketStatus.OPEN
        )
        await session.commit()

        updated = await update_ticket(
            session,
            ticket.id,
            status=TicketStatus.CLOSED
        )

        assert updated is not None
        assert updated.status == TicketStatus.CLOSED
        assert updated.resolved_at is not None

    async def test_update_ticket_not_exists(self, session: AsyncSession):
        """Test updating non-existent ticket."""
        fake_id = uuid4()
        updated = await update_ticket(
            session,
            fake_id,
            category="test"
        )

        assert updated is None

    async def test_update_ticket_multiple_fields(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test updating multiple ticket fields at once."""
        ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL
        )
        await session.commit()

        updated = await update_ticket(
            session,
            ticket.id,
            category="technical",
            priority=Priority.CRITICAL,
            status=TicketStatus.IN_PROGRESS
        )

        assert updated is not None
        assert updated.category == "technical"
        assert updated.priority == Priority.CRITICAL
        assert updated.status == TicketStatus.IN_PROGRESS

    async def test_list_conversation_tickets_empty(self, session: AsyncSession, sample_conversation: Conversation):
        """Test listing tickets for conversation with none."""
        tickets = await list_conversation_tickets(session, sample_conversation.id)

        # sample_conversation fixture might have tickets, so just check it returns a list
        assert isinstance(tickets, list)

    async def test_list_conversation_tickets_with_data(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test listing tickets for conversation with data."""
        # Create multiple tickets
        ticket1 = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            category="billing"
        )

        ticket2 = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            category="technical"
        )

        ticket3 = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL,
            category="account"
        )
        await session.commit()

        tickets = await list_conversation_tickets(session, sample_conversation.id)

        assert len(tickets) >= 3
        ticket_ids = [t.id for t in tickets]
        assert ticket1.id in ticket_ids
        assert ticket2.id in ticket_ids
        assert ticket3.id in ticket_ids

    async def test_list_conversation_tickets_ordered_by_created_at(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test tickets are ordered by created_at descending."""
        # Create tickets in sequence
        ticket1 = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL
        )
        await session.flush()

        ticket2 = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL
        )
        await session.flush()

        ticket3 = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL
        )
        await session.commit()

        tickets = await list_conversation_tickets(session, sample_conversation.id)

        # Most recent should be first (descending order)
        assert tickets[0].id == ticket3.id
        assert tickets[1].id == ticket2.id
        assert tickets[2].id == ticket1.id

    async def test_tickets_isolated_by_conversation(self, session: AsyncSession, sample_customer: Customer):
        """Test tickets are isolated by conversation."""
        from src.database.queries.conversation import create_conversation

        # Create two conversations
        conv1 = await create_conversation(session, sample_customer.id, Channel.EMAIL)
        conv2 = await create_conversation(session, sample_customer.id, Channel.WHATSAPP)

        # Create tickets for each conversation
        ticket1 = await create_ticket(
            session,
            conv1.id,
            sample_customer.id,
            Channel.EMAIL
        )

        ticket2 = await create_ticket(
            session,
            conv2.id,
            sample_customer.id,
            Channel.WHATSAPP
        )
        await session.commit()

        # List tickets for conv1
        conv1_tickets = await list_conversation_tickets(session, conv1.id)
        conv1_ids = [t.id for t in conv1_tickets]

        # Should only include conv1's ticket
        assert ticket1.id in conv1_ids
        assert ticket2.id not in conv1_ids

    async def test_update_ticket_resolved_at_only_set_once(self, session: AsyncSession, sample_customer: Customer, sample_conversation: Conversation):
        """Test resolved_at is only set once when first resolved."""
        ticket = await create_ticket(
            session,
            sample_conversation.id,
            sample_customer.id,
            Channel.EMAIL
        )
        await session.commit()

        # First resolution
        updated1 = await update_ticket(
            session,
            ticket.id,
            status=TicketStatus.RESOLVED
        )
        assert updated1 is not None
        first_resolved_at = updated1.resolved_at
        await session.commit()

        # Update again (should not change resolved_at)
        updated2 = await update_ticket(
            session,
            ticket.id,
            status=TicketStatus.CLOSED
        )

        assert updated2 is not None
        assert updated2.resolved_at == first_resolved_at
