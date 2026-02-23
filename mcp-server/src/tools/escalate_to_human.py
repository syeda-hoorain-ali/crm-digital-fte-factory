"""Escalate ticket to human tool - simplified for file-based MVP."""
from typing import Dict, Any
from datetime import datetime
from src.storage import TicketStorage
from src.config import settings


# Initialize storage
ticket_storage = TicketStorage(str(settings.tickets_path))


def escalate_ticket_impl(ticket_id: str, reason: str) -> Dict[str, Any]:
    """
    Escalate a ticket to human support.

    Args:
        ticket_id: The ID of the ticket to escalate
        reason: The reason for escalation

    Returns:
        Dictionary containing escalation result
    """
    # Validation
    if not ticket_id or not isinstance(ticket_id, str):
        raise ValueError("Ticket ID must be a non-empty string")
    if not reason or not isinstance(reason, str):
        raise ValueError("Reason must be a non-empty string")

    # Find the ticket to escalate
    ticket = ticket_storage.get_ticket_by_id(ticket_id)
    if not ticket:
        raise ValueError(f"Ticket with ID {ticket_id} not found")

    # Generate escalation ID
    escalation_id = f"esc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Update the ticket to mark it as escalated
    updates = {
        "status": "escalated",
        "escalated": True,
        "escalation_reason": reason,
        "escalation_id": escalation_id,
        "escalated_at": datetime.now().isoformat()
    }

    ticket_storage.update_ticket(ticket_id, updates)

    return {
        "escalation_id": escalation_id,
        "ticket_id": ticket_id,
        "reason": reason,
        "status": "escalated",
        "timestamp": datetime.now().isoformat(),
        "next_steps": "Human agent will contact customer shortly"
    }
