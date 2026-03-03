"""Human escalation tool with intelligent routing and trigger detection."""

import logging
from uuid import UUID
from datetime import datetime, timezone
from agents import function_tool, RunContextWrapper

from src.config import settings
from src.database.models import ConversationStatus, Priority
from src.database.queries import (
    get_conversation,
    update_conversation_status,
    get_conversation_history,
    get_customer,
)
from ..context import CustomerSuccessContext

logger = logging.getLogger(__name__)


def analyze_sentiment_trend(messages: list, threshold: float = -0.3) -> tuple[bool, str]:
    """Analyze sentiment trend across recent messages.

    Args:
        messages: List of recent messages with sentiment scores
        threshold: Negative sentiment threshold (default: -0.3)

    Returns:
        Tuple of (should_escalate, reason)
    """
    if not messages:
        return False, ""

    # Get sentiment scores from recent messages
    sentiment_scores = [
        msg.sentiment_score for msg in messages
        if msg.sentiment_score is not None
    ]

    if not sentiment_scores:
        return False, ""

    # Check for consistently negative sentiment
    recent_negative = sum(1 for score in sentiment_scores[-3:] if score < threshold)
    if recent_negative >= 2:
        avg_sentiment = sum(sentiment_scores[-3:]) / len(sentiment_scores[-3:])
        return True, f"Negative sentiment trend detected (avg: {avg_sentiment:.2f})"

    # Check for declining sentiment
    if len(sentiment_scores) >= 3:
        if sentiment_scores[-1] < sentiment_scores[-2] < sentiment_scores[-3]:
            return True, "Declining sentiment pattern detected"

    return False, ""


def detect_conversation_looping(messages: list, similarity_threshold: int = 3) -> tuple[bool, str]:
    """Detect if conversation is looping with repeated similar messages.

    Args:
        messages: List of recent messages
        similarity_threshold: Number of similar messages to trigger escalation

    Returns:
        Tuple of (should_escalate, reason)
    """
    if len(messages) < similarity_threshold:
        return False, ""

    # Get customer messages only
    customer_messages = [
        msg.content.lower() for msg in messages
        if msg.role.value == "customer"
    ]

    if len(customer_messages) < similarity_threshold:
        return False, ""

    # Simple keyword-based similarity check
    # Check if customer is repeating similar questions/concerns
    recent_messages = customer_messages[-similarity_threshold:]

    # Count common keywords across messages
    common_keywords = ["still", "again", "same", "not working", "doesn't work", "problem"]
    keyword_matches = sum(
        1 for msg in recent_messages
        if any(keyword in msg for keyword in common_keywords)
    )

    if keyword_matches >= 2:
        return True, "Customer repeating similar concerns - possible conversation loop"

    return False, ""


def detect_explicit_escalation_request(message: str) -> tuple[bool, str]:
    """Detect explicit customer request for human support.

    Args:
        message: Customer message content

    Returns:
        Tuple of (should_escalate, reason)
    """
    message_lower = message.lower()

    # Escalation keywords and phrases
    escalation_phrases = [
        "speak to a human",
        "talk to a person",
        "speak to someone",
        "talk to manager",
        "speak to manager",
        "human agent",
        "real person",
        "not a bot",
        "actual person",
        "customer service",
        "supervisor",
        "escalate",
    ]

    for phrase in escalation_phrases:
        if phrase in message_lower:
            return True, f"Explicit escalation request detected: '{phrase}'"

    return False, ""


def check_high_value_account(customer_metadata: dict) -> tuple[bool, str, Priority]:
    """Check if customer is high-value and requires priority escalation.

    Args:
        customer_metadata: Customer metadata dictionary

    Returns:
        Tuple of (is_high_value, reason, priority_level)
    """
    tier = customer_metadata.get("tier", "standard").lower()

    # High-value tiers
    if tier in ["enterprise", "premium", "vip"]:
        priority = Priority.HIGH if tier == "premium" else Priority.CRITICAL
        return True, f"High-value account ({tier} tier)", priority

    # Check for other high-value indicators
    account_value = customer_metadata.get("account_value", 0)
    if account_value > 10000:
        return True, f"High account value (${account_value})", Priority.HIGH

    return False, "", Priority.MEDIUM


@function_tool
async def escalate_to_human(
    context: RunContextWrapper[CustomerSuccessContext],
    reason: str | None = None,
    priority: str = "medium",
) -> str:
    """Escalate conversation to human agent with intelligent routing and trigger detection.

    This tool performs intelligent escalation by analyzing multiple signals including sentiment
    trends, conversation patterns, explicit customer requests, and account value. It automatically
    detects escalation triggers, determines appropriate priority level, and routes to the correct
    support tier based on urgency and customer value.

    The tool updates the conversation status to "escalated" and sets the escalated_to field with
    the appropriate support team email for routing.

    Use this tool when:
    - Customer explicitly requests human support ("speak to a person", "talk to manager", etc.)
    - Negative sentiment trend detected (2+ messages with sentiment < -0.3)
    - Conversation is looping without resolution (repeated similar concerns)
    - Complex issue beyond agent capabilities
    - High-value customer requiring special attention (enterprise/premium/VIP tier)
    - Agent cannot resolve the issue after multiple attempts

    Args:
        reason: Optional explicit reason for escalation provided by the agent. This supplements
            the automatically detected triggers. Use this to provide context about why the agent
            cannot resolve the issue.
            Example: "Customer needs custom integration support beyond standard documentation"
        priority: Escalation priority level for routing. Valid values:
            - "low": Non-urgent, tier 1 support (support-tier1@cloudstream.com)
            - "medium": Standard priority, tier 2 support (support-tier2@cloudstream.com) [default]
            - "high": Urgent, senior support (support-senior@cloudstream.com)
            - "critical": Service down, VIP support (support-vip@cloudstream.com)
            Note: Detected triggers may override this priority (e.g., high-value accounts)

    Returns:
        str: Confirmation message with escalation details:
            - Escalation status
            - Priority level (may be elevated from input based on triggers)
            - Routing destination (support team email)
            - List of escalation triggers detected
            - Expected response time for high/critical priority
            Example: "Conversation escalated to human support team.\n\nPriority: HIGH\nRouted to: support-senior@cloudstream.com\nEscalation triggers:\n  1. Explicit escalation request detected: 'speak to a person'\n  2. High-value account (premium tier)\n\nDue to high priority, you can expect a response within 1 hour."

    Raises:
        Exception: If no active conversation, customer not identified, database error, or context invalid.
            Error message is returned as a string rather than raising to allow agent to handle gracefully.

    Example:
        >>> # Customer explicitly requests human support
        >>> result = await escalate_to_human(
        ...     reason="Customer requested to speak with a manager",
        ...     context=agent_context,
        ...     priority="high",
        ... )
        >>> print(result)
        "Conversation escalated to human support team.

        Priority: HIGH
        Routed to: support-senior@cloudstream.com
        Escalation triggers:
          1. Explicit escalation request detected: 'speak to manager'
          2. Agent reason: Customer requested to speak with a manager

        Due to high priority, you can expect a response within 1 hour."

        >>> # Automatic escalation due to negative sentiment
        >>> result = await escalate_to_human(context=agent_context)
        >>> print(result)
        "Conversation escalated to human support team.

        Priority: HIGH
        Routed to: support-senior@cloudstream.com
        Escalation triggers:
          1. Negative sentiment trend detected (avg: -0.52)
          2. Customer repeating similar concerns - possible conversation loop

        A human agent will review this conversation and respond shortly."

    Notes:
        - Requires customer and conversation to be identified first
        - Automatically detects 4 types of escalation triggers:
            1. Explicit requests (keyword detection in last message)
            2. Sentiment trends (2+ negative messages or declining pattern)
            3. Conversation looping (repeated similar concerns)
            4. High-value accounts (enterprise/premium/VIP tier or account_value > $10k)
        - Priority is automatically elevated for high-value accounts
        - Updates conversation.status to "escalated"
        - Updates conversation.escalated_to with support team email
        - Updates context.escalation_triggered and context.escalation_reason
        - Routing tiers: tier1 (low) → tier2 (medium) → senior (high) → vip (critical)
    """
    try:
        # Validate conversation exists
        if not context.context.conversation_id:
            return "Error: No active conversation to escalate."

        # Validate customer is identified
        if not context.context.customer_id:
            return "Error: Customer must be identified before escalation."

        # Get database session from context
        session = context.context.db_session

        # Parse IDs
        conversation_id = UUID(context.context.conversation_id)
        customer_id = UUID(context.context.customer_id)

        logger.info(f"Processing escalation for conversation {conversation_id}")

        # Get conversation and customer details
        conversation = await get_conversation(session, conversation_id)
        if not conversation:
            return f"Error: Conversation {conversation_id} not found."

        customer = await get_customer(session, customer_id)
        if not customer:
            return f"Error: Customer {customer_id} not found."

        # Get conversation history for analysis
        messages = await get_conversation_history(
            session=session,
            conversation_id=conversation_id,
            limit=10,
        )

        # Collect escalation triggers
        escalation_reasons = []
        detected_priority = Priority.MEDIUM

        # 1. Check for explicit escalation request (T066)
        if messages:
            last_message = messages[-1].content if messages else ""
            explicit_escalation, explicit_reason = detect_explicit_escalation_request(last_message)
            if explicit_escalation:
                escalation_reasons.append(explicit_reason)
                detected_priority = Priority.HIGH

        # 2. Analyze sentiment trend (T064)
        sentiment_escalation, sentiment_reason = analyze_sentiment_trend(messages)
        if sentiment_escalation:
            escalation_reasons.append(sentiment_reason)
            if detected_priority == Priority.MEDIUM:
                detected_priority = Priority.HIGH

        # 3. Detect conversation looping (T065)
        looping_escalation, looping_reason = detect_conversation_looping(messages)
        if looping_escalation:
            escalation_reasons.append(looping_reason)

        # 4. Check high-value account (T067)
        is_high_value, value_reason, value_priority = check_high_value_account(
            customer.meta_data
        )
        if is_high_value:
            escalation_reasons.append(value_reason)
            # High-value accounts get priority escalation
            if value_priority.value in ["high", "critical"]:
                detected_priority = value_priority

        # 5. Add explicit reason if provided
        if reason:
            escalation_reasons.append(f"Agent reason: {reason}")

        # If no triggers detected and no explicit reason, use default
        if not escalation_reasons:
            escalation_reasons.append("Manual escalation requested")

        # Parse priority
        try:
            priority_enum = Priority[priority.upper()]
        except KeyError:
            priority_enum = detected_priority

        # Use higher priority if detected
        if detected_priority.value in ["high", "critical"]:
            priority_enum = detected_priority

        # Determine escalation routing based on priority (from configuration)
        escalation_routing = {
            Priority.LOW: settings.escalation_email_low,
            Priority.MEDIUM: settings.escalation_email_medium,
            Priority.HIGH: settings.escalation_email_high,
            Priority.CRITICAL: settings.escalation_email_critical,
        }

        escalated_to = escalation_routing.get(priority_enum, settings.escalation_email_medium)

        # Update conversation status to ESCALATED (T063)
        conversation.escalated_to = escalated_to
        conversation.status = ConversationStatus.ESCALATED
        conversation.updated_at = datetime.now(timezone.utc)

        await session.flush()
        await session.refresh(conversation)

        # Update context
        context.context.escalation_triggered = True
        context.context.escalation_reason = "; ".join(escalation_reasons)

        logger.info(
            f"Escalated conversation {conversation_id} to {escalated_to} "
            f"with priority {priority_enum.value}"
        )

        # Format response
        response = f"Conversation escalated to human support team.\n\n"
        response += f"Priority: {priority_enum.value.upper()}\n"
        response += f"Routed to: {escalated_to}\n"
        response += f"Escalation triggers:\n"
        for i, trigger in enumerate(escalation_reasons, 1):
            response += f"  {i}. {trigger}\n"
        response += f"\nA human agent will review this conversation and respond shortly."

        if priority_enum in [Priority.HIGH, Priority.CRITICAL]:
            response += f"\n\nDue to {priority_enum.value} priority, you can expect a response within 1 hour."

        return response

    except Exception as e:
        logger.error(f"Error escalating to human: {e}", exc_info=True)
        return f"Error escalating to human: {str(e)}"

