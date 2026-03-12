"""Gmail webhook endpoints for email support."""

import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Request, Depends, Header, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from src.database.connection import get_session_dependency
from src.database.models import (
    Customer,
    CustomerIdentifier,
    Conversation,
    Message,
    Ticket,
    WebhookDeliveryLog,
    GmailWatchState,
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
from src.channels.gmail_handler import GmailHandler
from src.kafka.producer import KafkaMessageProducer
from src.utils.rate_limiter import RateLimiter
from src.services.customer_identification import CustomerIdentificationService
from src.services.conversation_service import ConversationService
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize handlers (will be properly initialized in lifespan)
gmail_handler: Optional[GmailHandler] = None
kafka_producer: Optional[KafkaMessageProducer] = None
rate_limiter: Optional[RateLimiter] = None


class PubSubMessage(BaseModel):
    """Google Cloud Pub/Sub message format."""
    data: str = Field(..., description="Base64-encoded message data")
    messageId: str = Field(..., description="Pub/Sub message ID")
    publishTime: str = Field(..., description="Message publish timestamp")
    attributes: dict = Field(default_factory=dict, description="Message attributes")


class PubSubNotification(BaseModel):
    """Gmail Pub/Sub notification payload."""
    message: PubSubMessage
    subscription: str


async def get_stored_history_id(session: AsyncSession, email_address: str) -> str | None:
    """Retrieve the last successfully processed history ID from the database."""
    result = await session.execute(
        select(GmailWatchState).where(GmailWatchState.email == email_address)
    )
    state = result.scalars().first()
    return state.last_history_id if state else None


async def set_stored_history_id(session: AsyncSession, email_address: str, history_id: str):
    """Update or create the history ID record for an email address."""
    result = await session.execute(
        select(GmailWatchState).where(GmailWatchState.email == email_address)
    )
    state = result.scalars().first()
    
    if state:
        state.last_history_id = history_id
        state.updated_at = datetime.now(timezone.utc)
    else:
        new_state = GmailWatchState(
            email=email_address,
            last_history_id=history_id
        )
        session.add(new_state)
    
    # We commit here to ensure the "checkpoint" is saved 
    # even if subsequent Kafka steps fail later in the background task
    await session.commit()


async def process_gmail_notification_background(
    request_id: str,
    history_id: str,
    email_address: str,
    pubsub_message_id: str,
    x_goog_signature: Optional[str]
):
    """Process Gmail notification in background.

    Args:
        request_id: Unique request ID
        history_id: Gmail history ID
        email_address: Email address from notification
        pubsub_message_id: Pub/Sub message ID
        x_goog_signature: HMAC signature header
    """
    import sys
    print(f">>> BACKGROUND TASK STARTED: {request_id}", file=sys.stderr, flush=True)
    try:
        from src.database.connection import get_session

        async with get_session() as session:
            try:
                logger.info(
                    f"Background processing Gmail notification for {email_address}",
                    extra={"history_id": history_id, "request_id": request_id}
                )

                # Load previously stored history ID (the "start" for diffing)
                stored_history_id = await get_stored_history_id(session, email_address)

                if not stored_history_id:
                    # First-time: seed it and skip processing — no baseline to diff from
                    logger.warning(
                        f"No stored history ID for {email_address}, seeding with {history_id}",
                        extra={"request_id": request_id}
                    )
                    await set_stored_history_id(session, email_address, history_id)

                    # Update webhook log as completed (seeded)
                    result = await session.execute(
                        select(WebhookDeliveryLog).where(
                            WebhookDeliveryLog.request_id == request_id
                        )
                    )
                    webhook_log = result.scalars().first()
                    if webhook_log:
                        webhook_log.processing_status = WebhookProcessingStatus.COMPLETED
                        webhook_log.completed_at = datetime.now(timezone.utc)
                        await session.commit()
                    return

                # Process message through Gmail handler
                if not gmail_handler:
                    logger.error("Gmail handler not initialized")
                    return

                # Create payload with stored history ID as start (to get changes AFTER it)
                handler_payload = {
                    'history_id': str(stored_history_id)  # Use stored ID as start
                }

                channel_message = await gmail_handler.process_inbound_message(handler_payload)

                # If no new messages (notification was for label change, deletion, etc.), skip
                if channel_message is None:
                    logger.warning(f"[{request_id}] channel_message is None — no DB write will occur")
                    return
                    logger.info(
                        "No new messages to process",
                        extra={"history_id": history_id, "request_id": request_id}
                    )
                    # Update webhook log as completed (no-op)
                    result = await session.execute(
                        select(WebhookDeliveryLog).where(
                            WebhookDeliveryLog.request_id == request_id
                        )
                    )
                    webhook_log = result.scalars().first()
                    if webhook_log:
                        webhook_log.processing_status = WebhookProcessingStatus.COMPLETED
                        webhook_log.completed_at = datetime.now(timezone.utc)
                        await session.commit()
                    return

                # Check rate limit
                if rate_limiter:
                    is_allowed, remaining = await rate_limiter.check_rate_limit(
                        customer_id=channel_message.customer_contact,
                        channel="email"
                    )

                    if not is_allowed:
                        retry_after = await rate_limiter.get_retry_after(
                            channel_message.customer_contact,
                            "email"
                        )
                        logger.warning(
                            f"Rate limit exceeded for {channel_message.customer_contact}",
                            extra={
                                "email": channel_message.customer_contact,
                                "retry_after": retry_after
                            }
                        )
                        # Update webhook log
                        result = await session.execute(
                            select(WebhookDeliveryLog).where(
                                WebhookDeliveryLog.request_id == request_id
                            )
                        )
                        webhook_log = result.scalars().first()
                        if webhook_log:
                            webhook_log.processing_status = WebhookProcessingStatus.FAILED
                            webhook_log.error_message = "Rate limit exceeded"
                            await session.commit()
                        return

                    # Record request
                    await rate_limiter.record_request(
                        channel_message.customer_contact,
                        "email"
                    )

                # Find or create customer using identification service
                identification_service = CustomerIdentificationService(session)
                customer = await identification_service.find_or_create_customer_by_email(
                    email=channel_message.customer_contact,
                    name=channel_message.customer_name,
                    metadata={"source": "email", "last_channel": "email"}
                )

                # Use conversation service for cross-channel continuity
                conversation_service = ConversationService(session)

                # Check if this is a reply to existing conversation (email thread)
                existing_conversation = None
                if channel_message.thread_id:
                    # Look for existing conversation with this thread ID
                    result = await session.execute(
                        select(Conversation)
                        .join(Message)
                        .where(
                            Message.thread_id == channel_message.thread_id,
                            Conversation.customer_id == customer.id
                        )
                    )
                    existing_conversation = result.scalars().first()

                # If no thread match, check for conversation continuity across channels
                if not existing_conversation:
                    existing_conversation = await conversation_service.detect_conversation_continuity(
                        customer_id=customer.id,
                        new_message_content=channel_message.body,
                        new_channel=Channel.EMAIL,
                        similarity_threshold=0.3
                    )

                # Create or use existing conversation
                if existing_conversation:
                    conversation = existing_conversation
                    # Update conversation status if closed
                    if conversation.status == ConversationStatus.CLOSED:
                        await conversation_service.reopen_conversation(conversation.id)
                        await session.refresh(conversation)

                    logger.info(
                        f"Using existing conversation for email",
                        extra={
                            "conversation_id": str(conversation.id),
                            "original_channel": conversation.initial_channel.value,
                            "customer_id": str(customer.id)
                        }
                    )
                else:
                    conversation = Conversation(
                        customer_id=customer.id,
                        initial_channel=Channel.EMAIL,
                        status=ConversationStatus.ACTIVE
                    )
                    session.add(conversation)
                    await session.commit()
                    await session.refresh(conversation)

                # Create message
                message = Message(
                    conversation_id=conversation.id,
                    channel=Channel.EMAIL,
                    direction=MessageDirection.INBOUND,
                    role=MessageRole.CUSTOMER,
                    content=channel_message.body,
                    channel_message_id=channel_message.message_id,
                    thread_id=channel_message.thread_id,
                    delivery_status=DeliveryStatus.DELIVERED,
                    webhook_signature=x_goog_signature
                )
                session.add(message)

                # Create ticket if new conversation
                if not existing_conversation:
                    ticket = Ticket(
                        conversation_id=conversation.id,
                        customer_id=customer.id,
                        source_channel=Channel.EMAIL,
                        category="general",
                        priority=Priority.MEDIUM,
                        status=TicketStatus.OPEN
                    )
                    session.add(ticket)

                await session.commit()
                await session.refresh(message)

                # Update channel message with customer ID
                channel_message.customer_id = str(customer.id)

                # Send to Kafka (critical - webhook will fail if Kafka fails, triggering Pub/Sub retry)
                if kafka_producer:
                    success = await kafka_producer.send_message(channel_message)
                    if not success:
                        logger.error(
                            f"Failed to send message to Kafka: {channel_message.message_id}"
                        )
                        raise Exception(f"Kafka send failed for message {channel_message.message_id}")

                # Update stored history ID after successful processing
                await set_stored_history_id(session, email_address, history_id)
                logger.info(
                    f"Updated stored history ID to {history_id}",
                    extra={"email": email_address, "request_id": request_id}
                )

                # Update webhook log
                result = await session.execute(
                    select(WebhookDeliveryLog).where(
                        WebhookDeliveryLog.request_id == request_id
                    )
                )
                webhook_log = result.scalars().first()
                if webhook_log:
                    webhook_log.processing_status = WebhookProcessingStatus.COMPLETED
                    webhook_log.completed_at = datetime.now(timezone.utc)
                    await session.commit()

                logger.info(
                    "Gmail webhook processed successfully",
                    extra={
                        "message_id": channel_message.message_id,
                        "customer_id": str(customer.id),
                        "conversation_id": str(conversation.id),
                        "request_id": request_id,
                        "is_reply": bool(existing_conversation)
                    }
                )

            except Exception as e:
                logger.error(
                    f"Error processing Gmail webhook in background: {e}",
                    extra={"request_id": request_id},
                    exc_info=True
                )
                # Update webhook log
                result = await session.execute(
                    select(WebhookDeliveryLog).where(
                        WebhookDeliveryLog.request_id == request_id
                    )
                )
                webhook_log = result.scalars().first()
                if webhook_log:
                    webhook_log.processing_status = WebhookProcessingStatus.FAILED
                    webhook_log.error_message = str(e)
                    await session.commit()
    except Exception as e:
        logger.error(
            f"FATAL: Background task crashed: {e}",
            extra={"request_id": request_id},
            exc_info=True  # This prints the full traceback
        )


@router.post("/gmail")
async def gmail_webhook(
    request: Request,
    notification: PubSubNotification,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session_dependency),
    x_goog_signature: Optional[str] = Header(None, alias="X-Goog-Signature")
):
    """Handle Gmail Pub/Sub webhook notifications.

    Args:
        request: FastAPI request object
        notification: Pub/Sub notification payload
        background_tasks: FastAPI background tasks
        session: Database session
        x_goog_signature: HMAC signature header

    Returns:
        Success response (200 OK immediately to prevent Pub/Sub retries)

    Raises:
        HTTPException: If signature invalid or basic validation fails
    """
    request_id = str(uuid.uuid4())

    try:
        # Verify request is from Google Pub/Sub
        user_agent = request.headers.get("user-agent", "")

        # Verify User-Agent is from Google
        if not user_agent.startswith("APIs-Google"):
            logger.warning(
                "Invalid User-Agent for Pub/Sub webhook",
                extra={"request_id": request_id, "user_agent": user_agent}
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook source"
            )

        # Decode Pub/Sub message data
        try:
            decoded_data = base64.b64decode(notification.message.data).decode('utf-8')
            pubsub_data = json.loads(decoded_data)
        except Exception as e:
            logger.error(f"Failed to decode Pub/Sub message: {e}", exc_info=True)
            raise HTTPException(
                status_code=400,
                detail="Invalid Pub/Sub message format"
            )

        # Extract history ID from Gmail Pub/Sub notification
        email_address = pubsub_data.get('emailAddress')
        history_id = pubsub_data.get('historyId')

        if not history_id:
            logger.warning(
                "Missing historyId in Gmail notification",
                extra={"request_id": request_id, "data": pubsub_data}
            )
            raise HTTPException(
                status_code=400,
                detail="Missing historyId in notification"
            )

        # IDEMPOTENCY CHECK: Check if we've already processed this historyId
        result = await session.execute(
            select(WebhookDeliveryLog)
            .where(
                col(WebhookDeliveryLog.webhook_type) == "gmail",
                col(WebhookDeliveryLog.processing_status).in_([
                    WebhookProcessingStatus.COMPLETED,
                    WebhookProcessingStatus.PROCESSING
                ])
            )
            .order_by(col(WebhookDeliveryLog.received_at).desc())
            .limit(100)
        )
        recent_logs = result.scalars().all()

        # Check if this historyId was already processed
        for log in recent_logs:
            if log.payload and isinstance(log.payload, dict):
                log_message = log.payload.get('message', {})
                if isinstance(log_message, dict):
                    log_data = log_message.get('data')
                    if log_data:
                        try:
                            log_decoded = base64.b64decode(log_data).decode('utf-8')
                            log_pubsub_data = json.loads(log_decoded)
                            log_history_id = log_pubsub_data.get('historyId')

                            if log_history_id == history_id:
                                logger.info(
                                    f"Duplicate notification - historyId {history_id} already processed",
                                    extra={"request_id": request_id, "original_request_id": log.request_id}
                                )
                                # Return 200 OK to acknowledge (idempotent)
                                return {
                                    "status": "success",
                                    "message": "Already processed (idempotent)",
                                    "request_id": request_id,
                                    "history_id": history_id
                                }
                        except Exception:
                            continue

        # Log webhook delivery
        webhook_log = WebhookDeliveryLog(
            webhook_type="gmail",
            request_id=request_id,
            signature_valid=True,
            payload=notification.model_dump(),
            processing_status=WebhookProcessingStatus.PROCESSING
        )
        session.add(webhook_log)
        await session.commit()

        logger.info(
            f"Accepted Gmail notification for {email_address}",
            extra={"history_id": history_id, "request_id": request_id}
        )

        # Schedule background processing
        background_tasks.add_task(
            process_gmail_notification_background,
            request_id=request_id,
            history_id=str(history_id),
            email_address=email_address,
            pubsub_message_id=notification.message.messageId,
            x_goog_signature=x_goog_signature
        )

        # Return 200 OK immediately to prevent Pub/Sub retries
        return {
            "status": "accepted",
            "message": "Processing in background",
            "request_id": request_id,
            "history_id": history_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error validating Gmail webhook: {e}",
            extra={"request_id": request_id},
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to validate Gmail webhook"
        )
