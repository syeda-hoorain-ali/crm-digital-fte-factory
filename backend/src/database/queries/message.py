"""Message CRUD operations."""

import logging
from typing import List
from uuid import UUID

from sqlmodel import col
from sqlalchemy import select, delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from typing import cast

from ..models import (
    Message,
    MessageRole,
    MessageDirection,
    Channel,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Message CRUD Operations (T023)
# ============================================================================

async def create_message(
    session: AsyncSession,
    conversation_id: UUID,
    role: MessageRole,
    content: str,
    direction: MessageDirection,
    channel: Channel,
    channel_message_id: str | None = None,
    tokens_used: int | None = None,
    latency_ms: int | None = None,
    tool_calls: list[dict] | None = None,
) -> Message:
    """
    Create a new message with observability fields.

    Args:
        session: Database session
        conversation_id: Conversation UUID
        role: Message role (user, assistant, system, tool)
        content: Message content
        direction: Message direction (inbound, outbound)
        channel: Communication channel
        channel_message_id: External channel message ID
        tokens_used: Token count for LLM calls
        latency_ms: Response latency in milliseconds
        tool_calls: Tool call metadata

    Returns:
        Message: Created message instance
    """
    import time
    start_time = time.time()

    try:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            direction=direction,
            channel=channel,
            channel_message_id=channel_message_id,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            tool_calls=tool_calls or [],
        )
        session.add(message)
        await session.flush()
        await session.refresh(message)

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            f"Created message",
            extra={
                "operation": "create",
                "entity": "message",
                "message_id": str(message.id),
                "conversation_id": str(conversation_id),
                "role": role.value,
                "direction": direction.value,
                "content_length": len(content),
                "execution_time_ms": round(execution_time, 2),
                "success": True,
            }
        )
        return message
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Failed to create message: {e}",
            extra={
                "operation": "create",
                "entity": "message",
                "conversation_id": str(conversation_id),
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            }
        )
        raise


async def get_conversation_history(
    session: AsyncSession,
    conversation_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> List[Message]:
    """
    Retrieve conversation history with messages ordered chronologically (T023).

    Args:
        session: Database session
        conversation_id: Conversation UUID
        limit: Maximum number of messages
        offset: Number of messages to skip

    Returns:
        List[Message]: List of messages in chronological order
    """
    stmt = (
        select(Message)
        .where(col(Message.conversation_id) == conversation_id)
        .order_by(col(Message.created_at).asc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_latest_message(
    session: AsyncSession,
    conversation_id: UUID,
) -> Message | None:
    """
    Get the most recent message in a conversation.

    Args:
        session: Database session
        conversation_id: Conversation UUID

    Returns:
        Message | None: Latest message or None if conversation is empty
    """
    stmt = (
        select(Message)
        .where(col(Message.conversation_id) == conversation_id)
        .order_by(col(Message.created_at).desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def delete_message(
    session: AsyncSession,
    message_id: UUID,
) -> bool:
    """
    Delete message by ID.

    Args:
        session: Database session
        message_id: Message UUID

    Returns:
        bool: True if deleted, False if not found
    """
    stmt = delete(Message).where(col(Message.id) == message_id)
    result = cast(CursorResult, await session.execute(stmt))
    return result.rowcount > 0
