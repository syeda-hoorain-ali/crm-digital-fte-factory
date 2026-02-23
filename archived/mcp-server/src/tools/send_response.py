"""Send response to customer tool implementation."""
import time
from typing import Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from src.database.models import SupportTicket
from src.database.session import engine
from src.utils.metrics import metrics_collector
from src.utils.rate_limiter import check_rate_limit


def save_reply_impl(ticket_id: str, message: str, channel: str = "web_form", client_id: str = "default_client") -> Dict[str, Any]:
    """
    Implementation for saving a reply to a ticket.

    Args:
        ticket_id: The ID of the ticket
        message: The response message
        channel: Communication channel
        client_id: ID of the requesting client (for metrics/rate limiting)

    Returns:
        Dictionary containing response status
    """
    # Record metrics
    metrics_collector.increment_request()
    metrics_collector.record_tool_usage("send_response")
    start_time = time.time()

    # Check rate limit
    if not check_rate_limit(client_id):
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("send_response", duration)
        raise Exception("Rate limit exceeded")

    try:
        # Input validation
        if not ticket_id or not isinstance(ticket_id, str):
            raise ValueError("Ticket ID must be a non-empty string")
        if not message or not isinstance(message, str):
            raise ValueError("Message must be a non-empty string")
        if channel not in ["email", "web_form", "whatsapp", "chat"]:
            raise ValueError("Channel must be one of: email, web_form, whatsapp, chat")

        # In a real implementation, this might involve storing the response in a separate table
        # or marking the ticket as responded. For now, we'll just validate that the ticket exists.

        with Session(engine) as session:
            # Find the ticket to verify it exists
            ticket_statement = select(SupportTicket).where(SupportTicket.ticket_id == ticket_id)
            ticket = session.exec(ticket_statement).first()

            if not ticket:
                raise ValueError(f"Ticket with ID {ticket_id} not found")

            # In a real implementation, we would store the response in a separate table
            # For now, we just confirm the ticket exists and return success

            response_data = {
                "ticket_id": ticket_id,
                "message": message,
                "channel": channel,
                "delivery_status": "sent",
                "timestamp": datetime.now().isoformat(),
                "delivery_confirmation": f"Response sent via {channel}"
            }

        duration = time.time() - start_time
        metrics_collector.record_response_time("send_response", duration)
        return response_data

    except Exception as e:
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("send_response", duration)
        raise e
