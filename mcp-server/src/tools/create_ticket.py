"""Create support ticket tool - simplified for file-based MVP."""
from typing import Dict, Any
from datetime import datetime
from src.storage import TicketStorage
from src.config import settings


# Initialize storage
ticket_storage = TicketStorage(str(settings.tickets_path))


def create_support_ticket_impl(customer_id: str, issue: str, priority: str = "normal", channel: str = "web_form") -> Dict[str, Any]:
    """
    Create a support ticket.

    Args:
        customer_id: The ID of the customer creating the ticket (email or phone)
        issue: Description of the issue
        priority: Priority level (low, normal, high, urgent)
        channel: Communication channel (email, web_form, whatsapp, chat, gmail)

    Returns:
        Dictionary containing ticket creation result
    """
    # Validation
    if not customer_id or not isinstance(customer_id, str):
        raise ValueError("Customer ID must be a non-empty string")
    if not issue or not isinstance(issue, str):
        raise ValueError("Issue must be a non-empty string")
    if priority not in ["low", "normal", "high", "urgent"]:
        raise ValueError("Priority must be one of: low, normal, high, urgent")
    if channel not in ["email", "web_form", "whatsapp", "chat", "gmail"]:
        raise ValueError("Channel must be one of: email, web_form, whatsapp, chat, gmail")

    # Determine if customer_id is email or phone
    email = customer_id if "@" in customer_id else None
    phone = customer_id if not email else None

    # Create ticket data
    ticket_data = {
        "customer_email": email,
        "customer_phone": phone,
        "channel": channel,
        "content": issue,
        "subject": issue[:50] + "..." if len(issue) > 50 else issue,
        "priority": priority,
        "created_at": datetime.now().isoformat(),
        "status": "open"
    }

    # Create the ticket and get the generated ID
    ticket_id = ticket_storage.create_ticket(ticket_data)

    return {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "issue": issue,
        "priority": priority,
        "channel": channel,
        "status": "created",
        "timestamp": datetime.now().isoformat()
    }
