"""Web form support endpoints."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, EmailStr
from sqlmodel import col, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session_dependency
from src.database.models import (
    Customer,
    CustomerIdentifier,
    Conversation,
    Message,
    Ticket,
    WebhookDeliveryLog,
    Channel,
    IdentifierType,
    ConversationStatus,
    MessageDirection,
    MessageRole,
    DeliveryStatus,
    Priority,
    TicketStatus,
    WebhookProcessingStatus,
)
from src.channels.web_form_handler import WebFormHandler
from src.kafka.producer import KafkaMessageProducer
from src.utils.rate_limiter import RateLimiter
from src.services.notification_service import NotificationService
from src.services.customer_identification import CustomerIdentificationService
from src.services.conversation_service import ConversationService
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize handlers (will be properly initialized in lifespan)
web_form_handler = WebFormHandler()
kafka_producer: Optional[KafkaMessageProducer] = None
rate_limiter: Optional[RateLimiter] = None
notification_service: Optional[NotificationService] = None

# Initialize notification service if enabled
if settings.enable_email_notifications and settings.smtp_username and settings.smtp_password:
    notification_service = NotificationService(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_username=settings.smtp_username,
        smtp_password=settings.smtp_password,
        from_email=settings.smtp_from_email,
        use_tls=settings.smtp_use_tls
    )


class SupportFormRequest(BaseModel):
    """Support form submission request."""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    subject: str = Field(..., min_length=5, max_length=500)
    category: str = Field(..., pattern="^(general|technical|billing|feedback|bug_report)$")
    priority: str = Field(..., pattern="^(low|medium|high|critical)$")
    message: str = Field(..., min_length=10)


class SupportFormResponse(BaseModel):
    """Support form submission response."""
    ticket_id: str
    message: str
    estimated_response_time: str


class TicketStatusResponse(BaseModel):
    """Ticket status response."""
    ticket_id: str
    status: str
    created_at: str
    messages: list[dict]


@router.post("/submit", response_model=SupportFormResponse)
async def submit_support_request(
    request: Request,
    form_data: SupportFormRequest,
    session = Depends(get_session_dependency)
):
    """Submit a support request via web form.

    Args:
        request: FastAPI request object
        form_data: Support form data
        session: Database session

    Returns:
        Support form response with ticket ID

    Raises:
        HTTPException: If rate limit exceeded or processing fails
    """
    request_id = str(uuid.uuid4())

    try:
        # Check rate limit
        if rate_limiter:
            is_allowed, remaining = await rate_limiter.check_rate_limit(
                customer_id=form_data.email,  # Use email as customer ID for rate limiting
                channel="webform"
            )

            if not is_allowed:
                retry_after = await rate_limiter.get_retry_after(form_data.email, "webform")
                logger.warning(
                    f"Rate limit exceeded for {form_data.email}",
                    extra={"email": form_data.email, "retry_after": retry_after}
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many requests. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)} if retry_after else {}
                )

            # Record request
            await rate_limiter.record_request(form_data.email, "webform")

        # Log webhook delivery
        webhook_log = WebhookDeliveryLog(
            webhook_type="webform",
            request_id=request_id,
            signature_valid=True,  # No signature for web form
            payload=form_data.model_dump(),
            processing_status=WebhookProcessingStatus.PROCESSING
        )
        session.add(webhook_log)
        await session.commit()

        # Find or create customer using identification service
        identification_service = CustomerIdentificationService(session)
        customer = await identification_service.find_or_create_customer_by_email(
            email=form_data.email,
            name=form_data.name,
            metadata={"source": "web_form", "last_channel": "webform"}
        )

        # Use conversation service for cross-channel continuity
        conversation_service = ConversationService(session)

        # Check for active conversation or conversation continuity
        existing_conversation = await conversation_service.find_active_conversation(
            customer_id=customer.id,
            channel=Channel.WEB_FORM,
            max_age_hours=24
        )

        # If no active web form conversation, check for continuity across channels
        if not existing_conversation:
            existing_conversation = await conversation_service.detect_conversation_continuity(
                customer_id=customer.id,
                new_message_content=form_data.message,
                new_channel=Channel.WEB_FORM,
                similarity_threshold=0.3
            )

        # Create or use existing conversation
        if existing_conversation:
            conversation = existing_conversation
            # Reopen if closed
            if conversation.status == ConversationStatus.CLOSED:
                await conversation_service.reopen_conversation(conversation.id)
                await session.refresh(conversation)

            logger.info(
                f"Using existing conversation for web form",
                extra={
                    "conversation_id": str(conversation.id),
                    "original_channel": conversation.initial_channel.value,
                    "customer_id": str(customer.id)
                }
            )
        else:
            # Create conversation
            conversation = Conversation(
                customer_id=customer.id,
                initial_channel=Channel.WEB_FORM,
                status=ConversationStatus.ACTIVE
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

        # Create message
        message = Message(
            conversation_id=conversation.id,
            channel=Channel.WEB_FORM,
            direction=MessageDirection.INBOUND,
            role=MessageRole.CUSTOMER,
            content=form_data.message,
            delivery_status=DeliveryStatus.DELIVERED
        )
        session.add(message)

        # Create ticket
        priority_map = {
            "low": Priority.LOW,
            "medium": Priority.MEDIUM,
            "high": Priority.HIGH,
            "critical": Priority.CRITICAL
        }

        ticket = Ticket(
            conversation_id=conversation.id,
            customer_id=customer.id,
            source_channel=Channel.WEB_FORM,
            category=form_data.category,
            priority=priority_map.get(form_data.priority, Priority.MEDIUM),
            status=TicketStatus.OPEN
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)

        # Process message through handler
        payload = {
            "name": form_data.name,
            "email": form_data.email,
            "subject": form_data.subject,
            "category": form_data.category,
            "priority": form_data.priority,
            "message": form_data.message,
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host if request.client else None
        }

        channel_message = await web_form_handler.process_inbound_message(payload)
        channel_message.customer_id = str(customer.id)

        # Send to Kafka
        if kafka_producer:
            success = await kafka_producer.send_message(channel_message)
            if not success:
                logger.error(f"Failed to send message to Kafka: {channel_message.message_id}")

        # Update webhook log
        webhook_log.processing_status = WebhookProcessingStatus.COMPLETED
        webhook_log.completed_at = datetime.now(timezone.utc)
        await session.commit()

        # Send confirmation email if notification service is enabled
        if notification_service:
            try:
                await notification_service.send_support_confirmation(
                    to_email=form_data.email,
                    customer_name=form_data.name,
                    ticket_id=str(ticket.id),
                    subject=form_data.subject,
                    estimated_response_time="within 5 minutes"
                )
            except Exception as e:
                # Log error but don't fail the request
                logger.warning(
                    f"Failed to send confirmation email: {e}",
                    extra={
                        "ticket_id": str(ticket.id),
                        "customer_email": form_data.email
                    }
                )

        logger.info(
            f"Support request submitted successfully",
            extra={
                "ticket_id": str(ticket.id),
                "customer_id": str(customer.id),
                "request_id": request_id
            }
        )

        return SupportFormResponse(
            ticket_id=str(ticket.id),
            message="Your support request has been submitted successfully. We'll get back to you shortly.",
            estimated_response_time="within 5 minutes"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error processing support request: {e}",
            extra={"request_id": request_id},
            exc_info=True
        )

        # Update webhook log
        if 'webhook_log' in locals() and webhook_log:
            webhook_log.processing_status = WebhookProcessingStatus.FAILED
            webhook_log.error_message = str(e)
            await session.commit()

        raise HTTPException(
            status_code=500,
            detail="Failed to process support request. Please try again later."
        )


@router.get("/ticket/{ticket_id}", response_model=TicketStatusResponse)
async def get_ticket_status(
    ticket_id: str,
    session: AsyncSession = Depends(get_session_dependency)
):
    """Get ticket status and conversation history.

    Args:
        ticket_id: Ticket UUID
        session: Database session

    Returns:
        Ticket status with messages

    Raises:
        HTTPException: If ticket not found
    """
    try:
        # Parse ticket ID
        try:
            ticket_uuid = uuid.UUID(ticket_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ticket ID format")

        # Get ticket
        ticket = await session.get(Ticket, ticket_uuid)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Get messages
        messages_result = await session.execute(
            select(Message)
            .where(Message.conversation_id == ticket.conversation_id)
            .order_by(col(Message.created_at))
        )
        messages = list(messages_result.scalars().all())

        return TicketStatusResponse(
            ticket_id=str(ticket.id),
            status=ticket.status.value,
            created_at=ticket.created_at.isoformat(),
            messages=[
                {
                    "content": msg.content,
                    "role": msg.role.value,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ticket status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch ticket status"
        )
