"""Helper functions for integration test cleanup."""

import logging
from uuid import UUID
from sqlmodel import col
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Customer,
    CustomerIdentifier,
    Conversation,
    Message,
    Ticket,
    KnowledgeBase,
)

logger = logging.getLogger(__name__)


async def cleanup_customer_data(session: AsyncSession, customer_id: UUID) -> None:
    """Clean up all data associated with a customer.

    Deletes in proper order to respect foreign key constraints:
    1. Messages (depend on conversations)
    2. Tickets (depend on conversations and customers)
    3. Conversations (depend on customers)
    4. Customer identifiers (depend on customers)
    5. Customer (last)
    """
    logger.info(f"Starting cleanup for customer {customer_id}")

    try:
        # Get all conversation IDs for this customer
        result = await session.execute(
            select(col(Conversation.id)).where(col(Conversation.customer_id) == customer_id)
        )
        conversation_ids = [row[0] for row in result.fetchall()]
        logger.info(f"Found {len(conversation_ids)} conversations to clean up")

        if conversation_ids:
            # Delete messages for these conversations
            result = await session.execute(
                delete(Message).where(col(Message.conversation_id).in_(conversation_ids))
            )
            logger.info(f"Deleted {result.rowcount} messages")  # type: ignore[attr-defined]

            # Delete tickets for these conversations
            result = await session.execute(
                delete(Ticket).where(col(Ticket.conversation_id).in_(conversation_ids))
            )
            logger.info(f"Deleted {result.rowcount} tickets")  # type: ignore[attr-defined]

            # Delete conversations
            result = await session.execute(
                delete(Conversation).where(col(Conversation.customer_id) == customer_id)
            )
            logger.info(f"Deleted {result.rowcount} conversations")  # type: ignore[attr-defined]

        # Delete customer identifiers
        result = await session.execute(
            delete(CustomerIdentifier).where(col(CustomerIdentifier.customer_id) == customer_id)
        )
        logger.info(f"Deleted {result.rowcount} customer identifiers")  # type: ignore[attr-defined]

        # Delete customer
        result = await session.execute(delete(Customer).where(col(Customer.id) == customer_id))
        logger.info(f"Deleted {result.rowcount} customers")  # type: ignore[attr-defined]

        await session.commit()
        logger.info(f"Cleanup completed for customer {customer_id}")
    except Exception as e:
        logger.error(f"Error during cleanup for customer {customer_id}: {e}")
        await session.rollback()
        raise


async def cleanup_conversation_data(session: AsyncSession, conversation_id: UUID) -> None:
    """Clean up all data associated with a conversation.

    Deletes in proper order:
    1. Messages (depend on conversation)
    2. Tickets (depend on conversation)
    3. Conversation (last)
    """
    # Delete messages
    await session.execute(
        delete(Message).where(col(Message.conversation_id) == conversation_id)
    )

    # Delete tickets
    await session.execute(
        delete(Ticket).where(col(Ticket.conversation_id) == conversation_id)
    )

    # Delete conversation
    await session.execute(
        delete(Conversation).where(col(Conversation.id) == conversation_id)
    )

    await session.commit()


async def cleanup_knowledge_base_entry(session: AsyncSession, entry_id: UUID) -> None:
    """Clean up a knowledge base entry."""
    await session.execute(
        delete(KnowledgeBase).where(col(KnowledgeBase.id) == entry_id)
    )
    await session.commit()


async def cleanup_ticket(session: AsyncSession, ticket_id: UUID) -> None:
    """Clean up a ticket."""
    await session.execute(
        delete(Ticket).where(col(Ticket.id) == ticket_id)
    )
    await session.commit()


async def cleanup_customer_identifier(session: AsyncSession, identifier_id: UUID) -> None:
    """Clean up a customer identifier."""
    await session.execute(
        delete(CustomerIdentifier).where(col(CustomerIdentifier.id) == identifier_id)
    )
    await session.commit()