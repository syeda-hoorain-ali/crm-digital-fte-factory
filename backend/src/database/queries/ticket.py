"""Ticket CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlmodel import col
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Ticket,
    TicketStatus,
    Channel,
    Priority,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Ticket CRUD Operations (T024)
# ============================================================================

async def create_ticket(
    session: AsyncSession,
    conversation_id: UUID,
    customer_id: UUID,
    source_channel: Channel,
    category: str | None = None,
    priority: Priority = Priority.MEDIUM,
    status: TicketStatus = TicketStatus.OPEN,
) -> Ticket:
    """
    Create a new ticket linked to a conversation.

    Args:
        session: Database session
        conversation_id: Conversation UUID
        customer_id: Customer UUID
        source_channel: Channel where ticket originated
        category: Ticket category (optional)
        priority: Ticket priority
        status: Initial ticket status

    Returns:
        Ticket: Created ticket instance
    """
    import time
    start_time = time.time()

    try:
        ticket = Ticket(
            conversation_id=conversation_id,
            customer_id=customer_id,
            source_channel=source_channel,
            category=category,
            priority=priority,
            status=status,
        )
        session.add(ticket)
        await session.flush()
        await session.refresh(ticket)

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            f"Created ticket",
            extra={
                "operation": "create",
                "entity": "ticket",
                "ticket_id": str(ticket.id),
                "conversation_id": str(conversation_id),
                "customer_id": str(customer_id),
                "category": category,
                "priority": priority.value,
                "execution_time_ms": round(execution_time, 2),
                "success": True,
            }
        )
        return ticket
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Failed to create ticket: {e}",
            extra={
                "operation": "create",
                "entity": "ticket",
                "conversation_id": str(conversation_id),
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            }
        )
        raise


async def get_ticket(
    session: AsyncSession,
    ticket_id: UUID,
) -> Ticket | None:
    """
    Get ticket by ID.

    Args:
        session: Database session
        ticket_id: Ticket UUID

    Returns:
        Ticket | None: Ticket instance or None if not found
    """
    stmt = select(Ticket).where(col(Ticket.id) == ticket_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_ticket(
    session: AsyncSession,
    ticket_id: UUID,
    category: str | None = None,
    priority: Priority | None = None,
    status: TicketStatus | None = None,
    resolution: str | None = None,
) -> Ticket | None:
    """
    Update ticket with resolution tracking.

    Args:
        session: Database session
        ticket_id: Ticket UUID
        category: New ticket category (optional)
        priority: New ticket priority (optional)
        status: New ticket status (optional)
        resolution: Resolution notes (optional)

    Returns:
        Ticket | None: Updated ticket or None if not found
    """
    ticket = await get_ticket(session, ticket_id)

    if not ticket:
        return None

    if category is not None:
        ticket.category = category
    if priority is not None:
        ticket.priority = priority
    if status is not None:
        ticket.status = status
    if resolution is not None:
        ticket.resolution_notes = resolution

    ticket.updated_at = datetime.now(timezone.utc)

    # Set resolved_at when ticket is resolved or closed
    if status in (TicketStatus.RESOLVED, TicketStatus.CLOSED) and not ticket.resolved_at:
        ticket.resolved_at = datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(ticket)
    return ticket


async def list_conversation_tickets(
    session: AsyncSession,
    conversation_id: UUID,
) -> List[Ticket]:
    """
    List all tickets for a conversation.

    Args:
        session: Database session
        conversation_id: Conversation UUID

    Returns:
        List[Ticket]: List of tickets
    """
    stmt = (
        select(Ticket)
        .where(col(Ticket.conversation_id) == conversation_id)
        .order_by(col(Ticket.created_at).desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
