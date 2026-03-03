"""Context model for Customer Success Agent state management."""

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession


class CustomerSuccessContext(BaseModel):
    """Context for Customer Success Agent state management.

    This context object holds shared state across all agent tool calls,
    enabling stateful conversation tracking, customer identification,
    sentiment analysis, and escalation management.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Database session
    db_session: AsyncSession | None = None

    # Customer identification
    customer_id: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None

    # Conversation tracking
    conversation_id: str | None = None

    # Ticket tracking
    ticket_id: str | None = None

    # Sentiment analysis
    sentiment_score: float | None = None

    # Escalation state
    escalation_triggered: bool = False
    escalation_reason: str | None = None

    # Knowledge retrieval
    knowledge_articles_retrieved: list[str] = []

    # Channel information
    channel: str = "api"

    # Conversation history
    conversation_history: list[dict] = []
