"""Structured output schema for agent responses."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class AgentStructuredOutput:
    """
    Structured output format for agent responses.

    This ensures consistent response format and enables automatic
    ticket status updates, sentiment tracking, and escalation handling.
    """

    response_message: str
    """The message to send to the customer"""

    ticket_status: Literal["open", "in_progress", "resolved", "closed"]
    """
    Ticket status based on query resolution:
    - resolved: Query successfully answered with complete information
    - in_progress: Query partially answered, escalated to human, awaiting more information or action
    - open: Query received but not yet processed (should rarely be used)
    - closed: Query could not be resolved (information not found, tool errors)
    """

    sentiment_score: float
    """
    Sentiment score of the customer's query (-1.0 to 1.0):
    - Positive (0.3 to 1.0): Customer is satisfied, friendly, or expressing gratitude
    - Neutral (-0.3 to 0.3): Standard inquiry without strong emotion
    - Negative (-1.0 to -0.3): Customer is frustrated, angry, or dissatisfied
    """

    is_escalated: bool
    """Whether the query was escalated to a human agent"""

    resolution_summary: str | None = None
    """
    Brief summary of how the query was resolved (optional).
    Used for internal tracking and analytics.
    """
