"""Send response to customer tool - simplified for file-based MVP."""
from typing import Dict, Any
from datetime import datetime
from src.storage import TicketStorage, ReplyStorage
from src.config import settings


# Initialize storage
ticket_storage = TicketStorage(str(settings.tickets_path))
reply_storage = ReplyStorage(str(settings.replies_path))


def save_reply_impl(ticket_id: str, message: str, channel: str = "web_form") -> Dict[str, Any]:
    """
    Save a reply to a ticket.

    Args:
        ticket_id: The ID of the ticket
        message: The response message
        channel: Communication channel (email, web_form, whatsapp, chat, gmail)

    Returns:
        Dictionary containing response status
    """
    # Validation
    if not ticket_id or not isinstance(ticket_id, str):
        raise ValueError("Ticket ID must be a non-empty string")
    if not message or not isinstance(message, str):
        raise ValueError("Message must be a non-empty string")
    if channel not in ["email", "web_form", "whatsapp", "chat", "gmail"]:
        raise ValueError("Channel must be one of: email, web_form, whatsapp, chat, gmail")

    # Verify ticket exists
    ticket = ticket_storage.get_ticket_by_id(ticket_id)
    if not ticket:
        raise ValueError(f"Ticket with ID {ticket_id} not found")

    # Get customer identifier
    customer = ticket.get("customer_email") or ticket.get("customer_phone") or "unknown"

    # Save reply to file
    reply_storage.save_reply(
        ticket_id=ticket_id,
        content=message,
        channel=channel,
        customer=customer
    )

    return {
        "ticket_id": ticket_id,
        "message": message,
        "channel": channel,
        "delivery_status": "sent",
        "timestamp": datetime.now().isoformat(),
        "delivery_confirmation": f"Response sent via {channel} and saved to replies folder"
    }
