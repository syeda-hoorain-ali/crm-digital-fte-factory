"""Response sending tool that stores agent messages with observability tracking."""

import logging
import time
from uuid import UUID
from agents import function_tool, RunContextWrapper

from src.database.models import (
    Channel,
    MessageRole,
    MessageDirection,
    DeliveryStatus,
)
from src.database.queries import create_message
from ..context import CustomerSuccessContext

logger = logging.getLogger(__name__)


@function_tool
async def send_response(
    context: RunContextWrapper[CustomerSuccessContext],
    response_text: str,
    tokens_used: int | None = None,
    latency_ms: int | None = None,
) -> str:
    """Send response to customer and store in database with observability tracking.

    This tool stores the agent's response message in the database with role="agent" and
    direction="outbound", enabling conversation history tracking and observability metrics.
    This is the final step in the agent workflow after processing the customer inquiry.

    The stored message includes:
    - Response content
    - Observability fields (tokens_used, latency_ms)
    - Conversation linkage
    - Channel information
    - Timestamp

    Use this tool as the final step after:
    - Customer identification
    - Knowledge base search (if needed)
    - Ticket creation (if needed)
    - Response generation

    Args:
        response_text: The complete response message to send to the customer. Should be
            properly formatted for the channel (use channel formatters if needed).
            No length limit, but keep responses concise and actionable.
            Example: "I found the answer in our documentation. To reset your password..."
        tokens_used: Number of tokens consumed in generating this response. Used for cost
            tracking and performance monitoring. Optional, but recommended for observability.
            Example: 150 (for a typical response)
        latency_ms: Response generation latency in milliseconds. Used for performance
            monitoring and SLA tracking. Optional, but recommended for observability.
            Example: 1200 (for 1.2 second response time)

    Returns:
        str: Confirmation message with response details:
            - Success status
            - Message ID (UUID)
            - Channel
            - Response length (character count)
            - Tokens used (if provided)
            - Latency (if provided)
            Example: "Response sent successfully!\nMessage ID: abc-123\nChannel: email\nLength: 245 characters\nTokens used: 150\nLatency: 1200ms"

    Raises:
        Exception: If no active conversation, database error, or context is invalid.
            Error message is returned as a string rather than raising to allow agent to handle gracefully.

    Example:
        >>> # Send response after processing inquiry
        >>> result = await send_response(
        ...     response_text="I found the solution in our documentation. To reset your password, go to Settings > Security > Reset Password.",
        ...     context=agent_context,
        ...     tokens_used=150,
        ...     latency_ms=1200,
        ... )
        >>> print(result)
        "Response sent successfully!
        Message ID: abc-123
        Channel: email
        Length: 108 characters
        Tokens used: 150
        Latency: 1200ms"

        >>> # Send response without observability metrics
        >>> result = await send_response(
        ...     context=agent_context,
        ...     response_text="Thank you for contacting support!",
        ... )
        >>> print(result)
        "Response sent successfully!
        Message ID: def-456
        Channel: api
        Length: 33 characters"

    Notes:
        - Requires active conversation (conversation_id in context)
        - Message role is automatically set to "agent"
        - Message direction is automatically set to "outbound"
        - Channel is captured from context
        - Tool calls are tracked separately in hooks (not in this message)
        - channel_message_id is set to None (populated by channel integration if needed)
    """
    start_time = time.time()
    conversation_id_str = context.context.conversation_id if context and context.context else None

    try:
        logger.info(
            "Starting response storage",
            extra={
                "tool": "send_response",
                "conversation_id": conversation_id_str,
                "response_length": len(response_text),
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
            }
        )

        # Validate conversation exists
        if not context.context.conversation_id:
            logger.warning(
                "send_response called without active conversation",
                extra={
                    "tool": "send_response",
                    "success": False,
                }
            )
            return "Error: No active conversation. Cannot send response without a conversation context."

        # Get database session from context
        session = context.context.db_session

        # Parse conversation_id from context
        conversation_id = UUID(context.context.conversation_id)

        # Parse channel from context (default to API if not set)
        channel_str = context.context.channel.upper()
        try:
            channel = Channel[channel_str]
        except KeyError:
            logger.warning(f"Invalid channel '{channel_str}', defaulting to API")
            channel = Channel.API

        # Create message with agent role and observability fields
        message = await create_message(
            session=session,
            conversation_id=conversation_id,
            role=MessageRole.AGENT,
            content=response_text,
            direction=MessageDirection.OUTBOUND,
            channel=channel,  # Pass channel from context
            channel_message_id=None,  # Will be set by channel integration if needed
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            tool_calls=None,  # Tool calls are tracked separately in hooks
        )

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            "Response stored successfully",
            extra={
                "tool": "send_response",
                "conversation_id": conversation_id_str,
                "message_id": str(message.id),
                "channel": channel.value,
                "response_length": len(response_text),
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "execution_time_ms": round(execution_time, 2),
                "success": True,
            }
        )

        # Format confirmation
        response = f"Response sent successfully!\n"
        response += f"Message ID: {message.id}\n"
        response += f"Channel: {channel.value}\n"
        response += f"Length: {len(response_text)} characters"

        if tokens_used:
            response += f"\nTokens used: {tokens_used}"
        if latency_ms:
            response += f"\nLatency: {latency_ms}ms"

        return response

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Error sending response: {e}",
            extra={
                "tool": "send_response",
                "conversation_id": conversation_id_str,
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            },
            exc_info=True
        )
        return f"Error sending response: {str(e)}"
