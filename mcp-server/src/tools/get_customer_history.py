"""Get customer history tool - simplified for file-based MVP."""
from typing import Dict, Any
from datetime import datetime
from src.storage import CustomerStorage, TicketStorage
from src.config import settings


# Initialize storage
ticket_storage = TicketStorage(str(settings.tickets_path))
customer_storage = CustomerStorage(ticket_storage)


def lookup_customer_impl(customer_id: str) -> Dict[str, Any]:
    """
    Look up customer information and history.

    Args:
        customer_id: The ID of the customer to look up (email or phone)

    Returns:
        Dictionary containing customer information and history
    """
    # Validation
    if not customer_id or not isinstance(customer_id, str):
        raise ValueError("Customer ID must be a non-empty string")

    # Determine if customer_id is email or phone
    email = customer_id if "@" in customer_id else None
    phone = customer_id if not email else None

    # Get customer history
    history = customer_storage.get_customer_history(email=email, phone=phone)

    if not history["customer"]:
        # Customer not found
        return {
            "customer_id": customer_id,
            "name": "Unknown Customer",
            "email": email,
            "phone": phone,
            "plan_type": "unknown",
            "subscription_status": "inactive",
            "last_interaction": datetime.now().isoformat(),
            "support_tickets": [],
            "interaction_history": []
        }

    # Format customer data with tickets
    customer = history["customer"]
    tickets = history["tickets"]

    # Extract ticket IDs
    ticket_ids = [ticket.get("id") for ticket in tickets]

    # Build interaction history
    interaction_history = []
    for ticket in tickets:
        summary = ticket.get("content", "")[:50]
        if len(ticket.get("content", "")) > 50:
            summary += "..."

        interaction_history.append({
            "date": ticket.get("created_at", datetime.now().isoformat()),
            "type": "support_ticket",
            "summary": f"Ticket #{ticket.get('id')}: {summary}",
            "channel": ticket.get("channel", "unknown")
        })

    return {
        "customer_id": customer_id,
        "name": f"Customer {customer_id}",
        "email": customer.get("email"),
        "phone": customer.get("phone"),
        "plan_type": "unknown",
        "subscription_status": "active",
        "last_interaction": tickets[0].get("created_at") if tickets else datetime.now().isoformat(),
        "support_tickets": ticket_ids,
        "interaction_history": interaction_history,
        "total_tickets": history["total_tickets"]
    }
