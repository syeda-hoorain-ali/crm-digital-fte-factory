"""WhatsApp webhook endpoints for Twilio integration."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional, cast

from fastapi import APIRouter, HTTPException, Request, Depends, Header
from pydantic import BaseModel, Field
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
from src.channels.whatsapp_handler import WhatsAppHandler
from src.channels.twilio_client import TwilioClient
from src.kafka.producer import KafkaMessageProducer
from src.utils.rate_limiter import RateLimiter
from src.services.customer_identification import CustomerIdentificationService
from src.services.conversation_service import ConversationService
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize handlers (will be properly initialized in lifespan)
twilio_client: Optional[TwilioClient] = None
whatsapp_handler: Optional[WhatsAppHandler] = None
kafka_producer: Optional[KafkaMessageProducer] = None
rate_limiter: Optional[RateLimiter] = None


class WhatsAppStatusUpdate(BaseModel):
    """WhatsApp delivery status update from Twilio."""
    MessageSid: str
    MessageStatus: str  # sent, delivered, read, failed, undelivered
    ErrorCode: Optional[str] = None
    ErrorMessage: Optional[str] = None


@router.post("/whatsapp")
async def receive_whatsapp_message(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session_dependency)
):
    """Receive inbound WhatsApp message from Twilio webhook.

    Twilio sends form-encoded data with fields:
    - MessageSid: Unique message identifier
    - From: Sender phone (whatsapp:+1234567890)
    - To: Recipient phone (whatsapp:+1234567890)
    - Body: Message content
    - ProfileName: Sender's WhatsApp profile name
    - NumMedia: Number of media attachments

    Args:
        request: FastAPI request object
        x_twilio_signature: Twilio signature header for verification
        session: Database session

    Returns:
        TwiML response (empty for acknowledgment)

    Raises:
        HTTPException: If signature invalid, rate limit exceeded, or processing fails
    """
    request_id = str(uuid.uuid4())

    try:
        # Read raw body for signature verification
        raw_body = await request.body()

        # Parse form data
        form_data = await request.form()
        payload = dict(form_data)

        # Verify Twilio signature
        if whatsapp_handler and x_twilio_signature:
            url = str(request.url)
            is_valid = await whatsapp_handler.verify_webhook_signature(
                raw_body,
                x_twilio_signature,
                url
            )

            if not is_valid:
                logger.warning(
                    f"Invalid Twilio signature",
                    extra={"request_id": request_id, "url": url}
                )
                raise HTTPException(
                    status_code=403,
                    detail="Invalid signature"
                )

        # Extract phone number
        from_number = cast(str, payload.get("From", "")).replace("whatsapp:", "")

        if not from_number:
            raise HTTPException(status_code=400, detail="Missing From field")

        # Check rate limit
        if rate_limiter:
            is_allowed, remaining = await rate_limiter.check_rate_limit(
                customer_id=from_number,
                channel="whatsapp"
            )

            if not is_allowed:
                retry_after = await rate_limiter.get_retry_after(from_number, "whatsapp")
                logger.warning(
                    f"Rate limit exceeded for {from_number}",
                    extra={"phone": from_number, "retry_after": retry_after}
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many requests. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)} if retry_after else {}
                )

            # Record request
            await rate_limiter.record_request(from_number, "whatsapp")

        # Log webhook delivery
        webhook_log = WebhookDeliveryLog(
            webhook_type="whatsapp",
            request_id=request_id,
            signature_valid=True,
            payload=payload,
            processing_status=WebhookProcessingStatus.PROCESSING
        )
        session.add(webhook_log)
        await session.commit()

        # Find or create customer using identification service
        identification_service = CustomerIdentificationService(session)
        customer = await identification_service.find_or_create_customer_by_phone(
            phone=from_number,
            name=cast(str, payload.get("ProfileName") or "WhatsApp User"),
            metadata={"source": "whatsapp", "profile_name": payload.get("ProfileName"), "last_channel": "whatsapp"}
        )

        # Use conversation service for cross-channel continuity
        conversation_service = ConversationService(session)

        # Check for active conversation or conversation continuity
        existing_conversation = await conversation_service.find_active_conversation(
            customer_id=customer.id,
            channel=Channel.WHATSAPP,
            max_age_hours=24
        )

        # If no active WhatsApp conversation, check for continuity across channels
        if not existing_conversation:
            existing_conversation = await conversation_service.detect_conversation_continuity(
                customer_id=customer.id,
                new_message_content=cast(str, payload.get("Body", "")),
                new_channel=Channel.WHATSAPP,
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
                f"Using existing conversation for WhatsApp",
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
                initial_channel=Channel.WHATSAPP,
                status=ConversationStatus.ACTIVE
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

        # Create message
        message = Message(
            conversation_id=conversation.id,
            channel=Channel.WHATSAPP,
            direction=MessageDirection.INBOUND,
            role=MessageRole.CUSTOMER,
            content=payload.get("Body", ""),
            delivery_status=DeliveryStatus.DELIVERED,
            metadata_={
                "message_sid": payload.get("MessageSid"),
                "profile_name": payload.get("ProfileName"),
                "num_media": payload.get("NumMedia", "0")
            }
        )
        session.add(message)

        # Check if ticket exists for this conversation
        ticket_result = await session.execute(
            select(Ticket)
            .where(Ticket.conversation_id == conversation.id)
            .where(col(Ticket.status).in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]))
        )
        ticket = ticket_result.first()

        # Process message through handler
        if whatsapp_handler:
            channel_message = await whatsapp_handler.process_inbound_message(payload)
            channel_message.customer_id = str(customer.id)

            # Check for escalation
            requires_escalation = channel_message.metadata.get("requires_escalation", False)

            # Create ticket if escalation detected and no active ticket
            if requires_escalation and not ticket:
                ticket = Ticket(
                    conversation_id=conversation.id,
                    customer_id=customer.id,
                    source_channel=Channel.WHATSAPP,
                    category="escalation",
                    priority=Priority.HIGH,
                    status=TicketStatus.OPEN,
                    metadata_={"escalation_reason": "customer_requested"}
                )
                session.add(ticket)

                # Update conversation status
                conversation.status = ConversationStatus.ESCALATED

            # Send to Kafka
            if kafka_producer:
                success = await kafka_producer.send_message(channel_message)
                if not success:
                    logger.error(f"Failed to send message to Kafka: {channel_message.message_id}")

        await session.commit()

        # Update webhook log
        webhook_log.processing_status = WebhookProcessingStatus.COMPLETED
        webhook_log.completed_at = datetime.now(timezone.utc)
        await session.commit()

        logger.info(
            f"WhatsApp message processed successfully",
            extra={
                "message_sid": payload.get("MessageSid"),
                "customer_id": str(customer.id),
                "request_id": request_id,
                "requires_escalation": requires_escalation if whatsapp_handler else False
            }
        )

        # Return empty TwiML response (200 OK acknowledges receipt)
        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error processing WhatsApp message: {e}",
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
            detail="Failed to process WhatsApp message"
        )


@router.post("/whatsapp/status")
async def receive_whatsapp_status(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None),
    session = Depends(get_session_dependency)
):
    """Receive WhatsApp delivery status callback from Twilio.

    Twilio sends status updates for sent messages:
    - MessageSid: Message identifier
    - MessageStatus: sent, delivered, read, failed, undelivered
    - ErrorCode: Error code if failed
    - ErrorMessage: Error description if failed

    Args:
        request: FastAPI request object
        x_twilio_signature: Twilio signature header for verification
        session: Database session

    Returns:
        Acknowledgment response

    Raises:
        HTTPException: If signature invalid or processing fails
    """
    request_id = str(uuid.uuid4())

    try:
        # Read raw body for signature verification
        raw_body = await request.body()

        # Parse form data
        form_data = await request.form()
        payload = dict(form_data)

        # Verify Twilio signature
        if whatsapp_handler and x_twilio_signature:
            url = str(request.url)
            is_valid = await whatsapp_handler.verify_webhook_signature(
                raw_body,
                x_twilio_signature,
                url
            )

            if not is_valid:
                logger.warning(
                    f"Invalid Twilio signature for status callback",
                    extra={"request_id": request_id}
                )
                raise HTTPException(
                    status_code=403,
                    detail="Invalid signature"
                )

        message_sid = payload.get("MessageSid")
        message_status = payload.get("MessageStatus")

        if not message_sid or not message_status:
            raise HTTPException(
                status_code=400,
                detail="Missing MessageSid or MessageStatus"
            )

        # Map Twilio status to our DeliveryStatus enum
        status_map = {
            "queued": DeliveryStatus.PENDING,
            "sending": DeliveryStatus.PENDING,
            "sent": DeliveryStatus.SENT,
            "delivered": DeliveryStatus.DELIVERED,
            "read": DeliveryStatus.DELIVERED,  # We track read separately in metadata
            "failed": DeliveryStatus.FAILED,
            "undelivered": DeliveryStatus.FAILED
        }

        delivery_status = status_map.get(message_status.lower(), DeliveryStatus.PENDING)

        # Find message by MessageSid in channel_message_id
        result = await session.execute(
            select(Message).where(
                Message.channel == Channel.WHATSAPP,
                Message.channel_message_id == message_sid
            )
        )
        message = result.scalars().first()

        if message:
            # Update delivery status
            message.delivery_status = delivery_status

            # Store additional status details in metadata if field exists
            # Note: Message model may not have metadata_ field in all versions
            if hasattr(message, 'metadata_'):
                if not message.metadata_:
                    message.metadata_ = {}

                message.metadata_["last_status"] = message_status
                message.metadata_["status_updated_at"] = datetime.now(timezone.utc).isoformat()

                if message_status == "read":
                    message.metadata_["read_at"] = datetime.now(timezone.utc).isoformat()

                if payload.get("ErrorCode"):
                    message.metadata_["error_code"] = payload["ErrorCode"]
                    message.metadata_["error_message"] = payload.get("ErrorMessage")

            await session.commit()

            logger.info(
                f"WhatsApp message status updated",
                extra={
                    "message_sid": message_sid,
                    "status": message_status,
                    "message_id": str(message.id)
                }
            )
        else:
            logger.warning(
                f"Message not found for status update",
                extra={"message_sid": message_sid, "status": message_status}
            )

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error processing WhatsApp status: {e}",
            extra={"request_id": request_id},
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to process status update"
        )
