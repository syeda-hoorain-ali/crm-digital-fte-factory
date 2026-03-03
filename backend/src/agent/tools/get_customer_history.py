"""Customer history retrieval tool for conversation and message tracking."""

import logging
import time
from uuid import UUID
from agents import function_tool, RunContextWrapper

from src.database.queries import (
    list_customer_conversations,
    get_conversation_history,
)
from ..context import CustomerSuccessContext

logger = logging.getLogger(__name__)


@function_tool
async def get_customer_history(
    context: RunContextWrapper[CustomerSuccessContext],
    limit: int = 5,
) -> str:
    """Retrieve customer's conversation history and recent messages for context.

    This tool fetches the customer's previous conversations across all channels, including
    conversation metadata (status, sentiment, escalations) and recent messages from each
    conversation. This enables the agent to provide personalized support by understanding
    the customer's history, recurring issues, and past resolutions.

    Use this tool to:
    - Understand customer's past interactions before responding
    - Identify recurring issues or patterns
    - Reference previous conversations or solutions
    - Provide continuity across multiple support sessions
    - Personalize responses based on customer history

    Args:
        limit: Maximum number of recent conversations to retrieve, ordered by most recent first.
            Default: 5. Range: 1-100. Higher values may impact performance.
            Example: limit=3 returns the 3 most recent conversations

    Returns:
        str: Formatted string containing conversation history with:
            - Total number of conversations found
            - For each conversation:
                - Conversation ID
                - Channel (email, whatsapp, web_form, api)
                - Status (active, closed, escalated)
                - Start timestamp
                - Sentiment (positive/neutral/negative with score)
                - Escalation info (if escalated)
                - Recent messages (up to 3 per conversation, truncated to 100 chars)
            - Message if no history found (new customer)
            Example: "Found 2 previous conversation(s):\n\n1. Conversation abc-123\n   Channel: email\n   Status: closed..."

    Raises:
        Exception: If customer not identified, database query fails, or context is invalid.
            Error message is returned as a string rather than raising to allow agent to handle gracefully.

    Example:
        >>> # Check history for returning customer
        >>> result = await get_customer_history(
        ...     context=agent_context,
        ...     limit=3,
        ... )
        >>> print(result)
        "Found 2 previous conversation(s):

        1. Conversation abc-123
           Channel: email
           Status: closed
           Started: 2024-01-15 10:30
           Sentiment: positive (0.85)
           Recent messages (2):
             - [customer] How do I reset my password?
             - [agent] I can help you with that. Navigate to Settings...

        2. Conversation def-456
           Channel: whatsapp
           Status: escalated
           Started: 2024-01-10 14:20
           Sentiment: negative (-0.45)
           Escalated to: support-senior@cloudstream.com"

        >>> # New customer with no history
        >>> result = await get_customer_history(context=agent_context)
        >>> print(result)
        "No previous conversation history found. This is a new customer interaction."

    Notes:
        - Requires customer to be identified first (use identify_customer)
        - Updates context.conversation_history with conversation metadata
        - Messages are truncated to 100 characters for readability
        - Shows up to 3 most recent messages per conversation
        - Sentiment scores: >0.3 positive, <-0.3 negative, else neutral
        - Conversations ordered by started_at descending (most recent first)
    """
    start_time = time.time()
    conversation_id = context.context.conversation_id if context and context.context else None

    try:
        logger.info(
            "Starting customer history retrieval",
            extra={
                "tool": "get_customer_history",
                "conversation_id": conversation_id,
                "limit": limit,
            }
        )

        # Validate customer is identified
        if not context.context.customer_id:
            logger.warning(
                "Customer history requested without customer identification",
                extra={
                    "tool": "get_customer_history",
                    "conversation_id": conversation_id,
                    "success": False,
                }
            )
            return "Error: Customer must be identified before retrieving history. Use identify_customer first."

        # Get database session from context
        session = context.context.db_session

        # Parse customer_id from context
        customer_id = UUID(context.context.customer_id)

        # Get customer's conversations
        conversations = await list_customer_conversations(
            session=session,
            customer_id=customer_id,
            status=None,  # Get all conversations regardless of status
            limit=limit,
            offset=0,
        )

        if not conversations:
            execution_time = (time.time() - start_time) * 1000
            logger.info(
                "No conversation history found",
                extra={
                    "tool": "get_customer_history",
                    "conversation_id": conversation_id,
                    "customer_id": str(customer_id),
                    "conversations_count": 0,
                    "execution_time_ms": round(execution_time, 2),
                    "success": True,
                }
            )
            return "No previous conversation history found. This is a new customer interaction."

        # Format response with conversation details
        response = f"Found {len(conversations)} previous conversation(s):\n\n"

        for i, conv in enumerate(conversations, 1):
            response += f"{i}. Conversation {conv.id}\n"
            response += f"   Channel: {conv.initial_channel.value}\n"
            response += f"   Status: {conv.status.value}\n"
            response += f"   Started: {conv.started_at.strftime('%Y-%m-%d %H:%M')}\n"

            # Add sentiment if available
            if conv.sentiment_score is not None:
                sentiment = "positive" if conv.sentiment_score > 0.3 else "negative" if conv.sentiment_score < -0.3 else "neutral"
                response += f"   Sentiment: {sentiment} ({conv.sentiment_score:.2f})\n"

            # Add escalation info if present
            if conv.escalated_to:
                response += f"   Escalated to: {conv.escalated_to}\n"

            # Get recent messages from this conversation (limit to 3 most recent)
            messages = await get_conversation_history(
                session=session,
                conversation_id=conv.id,
                limit=3,
                offset=0,
            )

            if messages:
                response += f"   Recent messages ({len(messages)}):\n"
                for msg in messages[-3:]:  # Show last 3 messages
                    # Truncate long messages
                    content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    response += f"     - [{msg.role.value}] {content_preview}\n"

            response += "\n"

        # Update context with conversation history
        context.context.conversation_history = [
            {
                "id": str(conv.id),
                "channel": conv.initial_channel.value,
                "status": conv.status.value,
                "sentiment_score": conv.sentiment_score,
            }
            for conv in conversations
        ]

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            "Customer history retrieved successfully",
            extra={
                "tool": "get_customer_history",
                "conversation_id": conversation_id,
                "customer_id": str(customer_id),
                "conversations_count": len(conversations),
                "execution_time_ms": round(execution_time, 2),
                "success": True,
            }
        )

        return response

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Error retrieving customer history: {e}",
            extra={
                "tool": "get_customer_history",
                "conversation_id": conversation_id,
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            },
            exc_info=True
        )
        return f"Error retrieving customer history: {str(e)}"
