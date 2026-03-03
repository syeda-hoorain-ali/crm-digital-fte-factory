"""Support ticket creation tool for escalation and issue tracking."""

import logging
import time
from uuid import UUID
from agents import function_tool, RunContextWrapper

from src.database.models import Priority, TicketStatus, Channel
from src.database.queries import create_ticket as db_create_ticket
from ..context import CustomerSuccessContext

logger = logging.getLogger(__name__)


@function_tool
async def create_ticket(
    context: RunContextWrapper[CustomerSuccessContext],
    category: str,
    priority: str = "medium",
) -> str:
    """Create support ticket linked to current conversation for issue tracking.

    This tool creates a formal support ticket that is automatically linked to the current
    conversation and customer. Tickets enable tracking of customer issues through resolution,
    provide audit trails, and integrate with support team workflows.

    Use this tool when:
    - Customer reports a bug or technical issue
    - Issue requires investigation or follow-up
    - Formal tracking is needed for SLA compliance
    - Customer requests a feature or enhancement
    - Issue needs to be assigned to a specialist team

    Args:
        category: Ticket category for routing and classification. Common categories include:
            - "billing": Payment, invoices, subscription issues
            - "technical": Bugs, errors, system issues
            - "account": Login, permissions, profile updates
            - "feature_request": New feature suggestions
            - "integration": Third-party integration issues
            - "performance": Speed, latency, timeout issues
        priority: Priority level for ticket routing. Valid values:
            - "low": Non-urgent, can wait 3-5 business days
            - "medium": Standard priority, 1-2 business days (default)
            - "high": Urgent, same business day response needed
            - "critical": Service down, immediate response required

    Returns:
        str: Confirmation message with ticket details:
            - Ticket ID (UUID with # prefix)
            - Priority level
            - Category
            Example: "Support ticket created: #123e4567-e89b-12d3-a456-426614174000 (Priority: high, Category: technical)"

    Raises:
        Exception: If customer/conversation not identified, invalid priority, or database error.
            Error message is returned as a string rather than raising to allow agent to handle gracefully.

    Example:
        >>> # Customer reports a bug
        >>> result = await create_ticket(
        ...     context=agent_context,
        ...     category="technical",
        ...     priority="high",
        ... )
        >>> print(result)
        "Support ticket created: #abc-123 (Priority: high, Category: technical)"

        >>> # Customer has billing question
        >>> result = await create_ticket(
        ...     context=agent_context,
        ...     category="billing",
        ...     priority="medium",
        ... )
        >>> print(result)
        "Support ticket created: #def-456 (Priority: medium, Category: billing)"

    Notes:
        - Requires customer and conversation to be identified first (use identify_customer)
        - Ticket status is set to "open" by default
        - Source channel is automatically captured from context
        - Updates context.ticket_id for reference in subsequent tools
        - Invalid priority values default to "medium"
    """
    start_time = time.time()
    conversation_id = context.context.conversation_id if context and context.context else None

    try:
        logger.info(
            "Starting ticket creation",
            extra={
                "tool": "create_ticket",
                "conversation_id": conversation_id,
                "category": category,
                "priority": priority,
            }
        )

        # Validate and map priority
        priority_map = {
            "low": Priority.LOW,
            "medium": Priority.MEDIUM,
            "high": Priority.HIGH,
            "critical": Priority.CRITICAL,
        }
        priority_enum = priority_map.get(priority.lower(), Priority.MEDIUM)

        # Get required IDs from context
        customer_id = context.context.customer_id
        conversation_id = context.context.conversation_id
        channel = context.context.channel

        if not customer_id or not conversation_id:
            return "Error: Customer and conversation must be identified first. Use identify_customer tool before creating a ticket."

        # Map channel string to Channel enum
        channel_map = {
            "email": Channel.EMAIL,
            "whatsapp": Channel.WHATSAPP,
            "web_form": Channel.WEB_FORM,
            "api": Channel.API,
        }
        channel_enum = channel_map.get(channel.lower(), Channel.API)

        # Get database session
        session = context.context.db_session

        # Create ticket
        ticket = await db_create_ticket(
            session,
            conversation_id=UUID(conversation_id),
            customer_id=UUID(customer_id),
            source_channel=channel_enum,
            category=category,
            priority=priority_enum,
            status=TicketStatus.OPEN,
        )

        # Update context
        context.context.ticket_id = str(ticket.id)

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            "Ticket created successfully",
            extra={
                "tool": "create_ticket",
                "conversation_id": conversation_id,
                "ticket_id": str(ticket.id),
                "category": category,
                "priority": priority,
                "execution_time_ms": round(execution_time, 2),
                "success": True,
            }
        )

        return f"Support ticket created: #{ticket.id} (Priority: {priority}, Category: {category})"

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Error creating ticket: {e}",
            extra={
                "tool": "create_ticket",
                "conversation_id": conversation_id,
                "category": category,
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            },
            exc_info=True
        )
        return f"Error creating ticket: {str(e)}"
