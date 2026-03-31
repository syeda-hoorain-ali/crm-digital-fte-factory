"""Agent API Router for Customer Success Agent FastAPI."""

import logging
from uuid import UUID

from agents import Runner, trace
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from src.agent.customer_success_agent import (
    customer_success_agent,
    CustomerSuccessContext,
)
from src.agent.hooks import RunHooks
from src.agent.session import PostgresSession
from src.database.connection import get_session
from src.database.models import ConversationStatus, Channel
from src.database.queries import identify_or_create_customer, create_conversation

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/agent")

# Request/Response Models
class ProcessInquiryRequest(BaseModel):
    """Request model for processing customer inquiries."""

    message: str
    customer_email: str | None = None
    customer_phone: str | None = None
    channel: str = "api"
    conversation_id: str | None = None  # Optional: continue existing conversation

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message is not empty."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        if len(v) > 5000:
            raise ValueError("Message cannot exceed 5000 characters")
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        """Validate channel is supported."""
        valid_channels = ["email", "whatsapp", "web_form", "api"]
        if v not in valid_channels:
            raise ValueError(f"Channel must be one of: {', '.join(valid_channels)}")
        return v

    def model_post_init(self, __context) -> None:
        """Validate at least one contact method is provided."""
        if not self.customer_email and not self.customer_phone:
            raise ValueError("At least one of customer_email or customer_phone must be provided")


class ProcessInquiryResponse(BaseModel):
    """Response model for processed customer inquiries."""

    response: str
    customer_id: str
    conversation_id: str
    sentiment_score: float | None = None
    escalated: bool = False
    escalation_reason: str | None = None


class MessageResponse(BaseModel):
    """Response model for individual messages."""

    id: str
    role: str
    content: str
    created_at: str
    sentiment_score: float | None = None
    tokens_used: int | None = None
    latency_ms: int | None = None


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""

    conversation_id: str
    status: str
    channel: str
    started_at: str
    ended_at: str | None = None
    sentiment_score: float | None = None
    escalated_to: str | None = None
    messages: list[MessageResponse]


@router.post("/process", response_model=ProcessInquiryResponse)
async def process_inquiry(request: ProcessInquiryRequest):
    """
    Process customer inquiry through Customer Success Agent.

    This endpoint:
    1. Creates or retrieves conversation
    2. Initializes agent context with customer information
    3. Executes agent with custom session and hooks
    4. Wraps execution in trace() for observability
    5. Returns formatted response with conversation tracking

    Args:
        request: Customer inquiry with message and optional contact info

    Returns:
        ProcessInquiryResponse: Agent response with conversation tracking

    Raises:
        HTTPException: 400 for invalid request, 500 if agent processing fails
    """
    try:
        async with get_session() as session:
            # Step 1: Identify or create customer FIRST (required for conversation)
            customer = await identify_or_create_customer(
                session=session,
                email=request.customer_email,
                phone=request.customer_phone,
            )
            await session.commit()
            logger.info(f"Customer identified/created: {customer.id}")

            # Step 2: Create or retrieve conversation (with customer_id)
            if request.conversation_id:
                # Continue existing conversation
                conversation_uuid = UUID(request.conversation_id)
                conversation_id = request.conversation_id
                logger.info(f"Continuing conversation: {conversation_id}")
            else:
                # Create new conversation with customer_id
                conversation = await create_conversation(
                    session=session,
                    customer_id=customer.id,
                    channel=Channel[request.channel.upper()],
                    status=ConversationStatus.ACTIVE,
                )
                await session.commit()
                conversation_uuid = conversation.id
                conversation_id = str(conversation.id)
                logger.info(f"Created new conversation: {conversation_id}")

            # Step 3: Initialize context with customer and conversation data
            ctx = CustomerSuccessContext(
                db_session=session,  # Pass database session to context for tools
                customer_id=str(customer.id),  # Set customer_id from identified/created customer
                customer_email=customer.email,  # Use customer email from database
                customer_phone=customer.phone,  # Use customer phone from database
                channel=request.channel,
                conversation_id=conversation_id,
            )

            # Step 4: Create custom session for conversation memory
            # PostgresSession(session: AsyncSession, conversation_id: UUID, channel: Channel)
            agent_session = PostgresSession(
                session=session,
                conversation_id=conversation_uuid,
                channel=Channel[request.channel.upper()],
            )

            # Step 5: Create hooks for observability
            # RunHooks(session: AsyncSession, conversation_id: UUID, correlation_id: str | None)
            hooks = RunHooks(
                session=session,
                conversation_id=conversation_uuid,
                correlation_id=conversation_id,
            )

            # Step 6: Wrap in trace() context manager for OpenAI dashboard
            with trace(
                workflow_name="Customer Support",
                group_id=conversation_id,  # Links all turns in conversation
                metadata={
                    "channel": request.channel,
                    "customer_email": customer.email,
                    "customer_id": str(customer.id),
                },
            ):
                # Step 7: Execute agent with Runner.run()
                result = await Runner.run(
                    customer_success_agent,
                    request.message,
                    session=agent_session,
                    context=ctx,
                    hooks=hooks,
                )

                print(result.final_output)
                raw_items = [item.raw_item for item in result.new_items]
                for item in raw_items:
                    print(item)
                print("\n\n\n")

            # Step 8: Return response
            return ProcessInquiryResponse(
                response=result.final_output,
                conversation_id=conversation_id,
                sentiment_score=ctx.sentiment_score,
                escalated=ctx.escalation_triggered,
                escalation_reason=ctx.escalation_reason,
                customer_id=str(customer.id),
            )

    except ValueError as e:
        # Validation errors (e.g., invalid UUID format)
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid request",
                "message": str(e),
            },
        )
    except Exception as e:
        # All other errors
        logger.error(f"Agent processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Agent processing failed",
                "message": str(e),
            },
        )


@router.get("/history/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(conversation_id: str, limit: int = 100, offset: int = 0):
    """
    Retrieve conversation history with all messages.

    This endpoint:
    1. Validates conversation_id format
    2. Retrieves conversation metadata
    3. Fetches all messages in chronological order
    4. Returns structured response with conversation and message details

    Args:
        conversation_id: UUID of the conversation
        limit: Maximum number of messages to return (default: 100)
        offset: Number of messages to skip (default: 0)

    Returns:
        ConversationHistoryResponse: Conversation metadata with messages

    Raises:
        HTTPException: 404 if conversation not found, 422 if invalid UUID
    """
    try:
        # Validate UUID format
        try:
            conversation_uuid = UUID(conversation_id)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Invalid conversation ID",
                    "message": "Conversation ID must be a valid UUID",
                },
            )

        async with get_session() as session:
            # Import queries
            from src.database.queries import get_conversation, get_conversation_history as get_messages

            # Retrieve conversation
            conversation = await get_conversation(session, conversation_uuid)

            if not conversation:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "Conversation not found",
                        "message": f"No conversation found with ID: {conversation_id}",
                    },
                )

            # Retrieve messages
            messages = await get_messages(
                session,
                conversation_uuid,
                limit=limit,
                offset=offset,
            )

            # Transform messages to response format
            message_responses = [
                MessageResponse(
                    id=str(msg.id),
                    role=msg.role.value,
                    content=msg.content,
                    created_at=msg.created_at.isoformat(),
                    sentiment_score=msg.sentiment_score,
                    tokens_used=msg.tokens_used,
                    latency_ms=msg.latency_ms,
                )
                for msg in messages
            ]

            # Return conversation history
            return ConversationHistoryResponse(
                conversation_id=str(conversation.id),
                status=conversation.status.value,
                channel=conversation.initial_channel.value,
                started_at=conversation.started_at.isoformat(),
                ended_at=conversation.ended_at.isoformat() if conversation.ended_at else None,
                sentiment_score=conversation.sentiment_score,
                escalated_to=conversation.escalated_to,
                messages=message_responses,
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # All other errors
        logger.error(f"Failed to retrieve conversation history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve conversation history",
                "message": str(e),
            },
        )
