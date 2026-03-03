"""Conversation CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlmodel import col
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Conversation,
    ConversationStatus,
    Channel,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Conversation CRUD Operations (T022)
# ============================================================================

async def create_conversation(
    session: AsyncSession,
    customer_id: UUID,
    channel: Channel,
    status: ConversationStatus = ConversationStatus.ACTIVE,
) -> Conversation:
    """
    Create a new conversation with lifecycle tracking.

    Args:
        session: Database session
        customer_id: Customer UUID
        channel: Communication channel
        status: Initial conversation status

    Returns:
        Conversation: Created conversation instance
    """
    import time
    start_time = time.time()

    try:
        conversation = Conversation(
            customer_id=customer_id,
            status=status,
            initial_channel=channel,
        )
        session.add(conversation)
        await session.flush()
        await session.refresh(conversation)

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            f"Created conversation",
            extra={
                "operation": "create",
                "entity": "conversation",
                "conversation_id": str(conversation.id),
                "customer_id": str(customer_id),
                "channel": channel.value,
                "execution_time_ms": round(execution_time, 2),
                "success": True,
            }
        )
        return conversation
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Failed to create conversation: {e}",
            extra={
                "operation": "create",
                "entity": "conversation",
                "customer_id": str(customer_id),
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            }
        )
        raise


async def get_conversation(
    session: AsyncSession,
    conversation_id: UUID,
) -> Conversation | None:
    """
    Get conversation by ID.

    Args:
        session: Database session
        conversation_id: Conversation UUID

    Returns:
        Conversation | None: Conversation instance or None if not found
    """
    stmt = select(Conversation).where(col(Conversation.id) == conversation_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_conversation_status(
    session: AsyncSession,
    conversation_id: UUID,
    status: ConversationStatus,
) -> Conversation | None:
    """
    Update conversation status with lifecycle management.

    Args:
        session: Database session
        conversation_id: Conversation UUID
        status: New conversation status

    Returns:
        Conversation | None: Updated conversation or None if not found
    """
    conversation = await get_conversation(session, conversation_id)

    if not conversation:
        return None

    conversation.status = status
    conversation.updated_at = datetime.now(timezone.utc)

    # Set ended_at when conversation is closed
    if status == ConversationStatus.CLOSED and not conversation.ended_at:
        conversation.ended_at = datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(conversation)
    return conversation


async def list_customer_conversations(
    session: AsyncSession,
    customer_id: UUID,
    status: ConversationStatus | None = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Conversation]:
    """
    List conversations for a customer with optional status filter.

    Args:
        session: Database session
        customer_id: Customer UUID
        status: Optional status filter
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List[Conversation]: List of conversations
    """
    stmt = select(Conversation).where(col(Conversation.customer_id) == customer_id)

    if status:
        stmt = stmt.where(col(Conversation.status) == status)

    stmt = stmt.order_by(col(Conversation.created_at).desc()).limit(limit).offset(offset)

    result = await session.execute(stmt)
    return list(result.scalars().all())
