"""Customer identification tool for cross-channel customer unification."""

import logging
import time
from agents import function_tool, RunContextWrapper

from src.database.models import IdentifierType
from src.database.queries import (
    get_customer_by_identifier,
    create_customer_identifier,
)
from ..context import CustomerSuccessContext

logger = logging.getLogger(__name__)


@function_tool
async def identify_customer(
    context: RunContextWrapper[CustomerSuccessContext],
) -> str:
    """Identify or create customer based on email/phone for cross-channel unification.

    This tool performs cross-channel customer lookup using the CustomerIdentifier table,
    enabling the same customer to be recognized across email, phone, and WhatsApp channels.
    If no existing customer is found, a new customer record is created with the provided
    contact information.

    **IMPORTANT:** This tool takes no arguments. It automatically uses the customer's
    email/phone from the request context. Simply call it without any parameters.

    Use this tool on EVERY incoming message before any other processing to ensure proper
    customer tracking and conversation history.

    Args:
        None

    Returns:
        str: Human-readable confirmation message containing:
            - Customer identification status (existing or new)
            - Customer ID (UUID)
            - Customer name (if available)
            - Account tier from metadata
            Example: "Customer identified: John Doe (ID: 123e4567-e89b-12d3-a456-426614174000). Account tier: premium"

    Raises:
        Exception: If database query fails or context is invalid. Error message is returned
            as a string rather than raising to allow agent to handle gracefully.

    Example:
        >>> # Simple call - uses context automatically
        >>> identify_customer()
        "Customer identified: Jane Smith (ID: abc-123). Account tier: standard"

    Notes:
        - Updates context.customer_id, context.customer_email, and context.customer_phone
        - Creates CustomerIdentifier records for cross-channel matching
        - New customers are assigned "standard" tier by default
        - Searches email first, then phone if email lookup fails
        - Reads customer contact info from request context automatically
    """
    start_time = time.time()
    conversation_id = context.context.conversation_id

    # Read customer contact info from context
    email = context.context.customer_email
    phone = context.context.customer_phone

    if not email and not phone:
        logger.warning(
            "identify_customer called without email or phone in args or context",
            extra={
                "tool": "identify_customer",
                "conversation_id": conversation_id,
                "success": False,
            }
        )
        return "Error: No customer contact information available. Please provide email or phone number."

    try:
        logger.info(
            "Starting customer identification",
            extra={
                "tool": "identify_customer",
                "conversation_id": conversation_id,
                "has_email": email is not None,
                "has_phone": phone is not None,
            }
        )
        # Get database session from context
        session = context.context.db_session

        # Search for existing customer via identifiers
        customer = None
        if email:
            customer = await get_customer_by_identifier(
                session, IdentifierType.EMAIL, email
            )
        if not customer and phone:
            customer = await get_customer_by_identifier(
                session, IdentifierType.PHONE, phone
            )

        if customer:
            # Update context with customer information
            context.context.customer_id = str(customer.id)
            context.context.customer_email = email or customer.email
            context.context.customer_phone = phone or customer.phone

            # Get customer tier from metadata
            tier = customer.metadata_.get("tier", "standard")

            execution_time = (time.time() - start_time) * 1000
            logger.info(
                "Customer identified successfully",
                extra={
                    "tool": "identify_customer",
                    "conversation_id": conversation_id,
                    "customer_id": str(customer.id),
                    "tier": tier,
                    "execution_time_ms": round(execution_time, 2),
                    "success": True,
                }
            )

            return f"Customer identified: {customer.name or 'Unknown'} (ID: {customer.id}). Account tier: {tier}"
        else:
            # Create new customer using the updated create_customer function
            from src.database.queries import create_customer

            customer = await create_customer(
                session,
                name=None,
                email=email,
                phone=phone,
                meta_data={"tier": "standard"},
            )

            # Create identifiers
            if email:
                await create_customer_identifier(
                    session, customer.id, IdentifierType.EMAIL, email
                )
            if phone:
                await create_customer_identifier(
                    session, customer.id, IdentifierType.PHONE, phone
                )

            # Update context with new customer information
            context.context.customer_id = str(customer.id)
            context.context.customer_email = email
            context.context.customer_phone = phone

            execution_time = (time.time() - start_time) * 1000
            logger.info(
                "New customer created successfully",
                extra={
                    "tool": "identify_customer",
                    "conversation_id": conversation_id,
                    "customer_id": str(customer.id),
                    "execution_time_ms": round(execution_time, 2),
                    "success": True,
                }
            )

            return f"New customer created: ID {customer.id}. Welcome to CloudStream CRM!"

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Error identifying customer: {e}",
            extra={
                "tool": "identify_customer",
                "conversation_id": conversation_id,
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            },
            exc_info=True
        )
        return f"Error identifying customer: {str(e)}"
