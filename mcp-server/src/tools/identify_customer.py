"""Identify or create customer tool - simplified for file-based MVP."""
from typing import Dict, Any, Optional
from src.storage import CustomerStorage, TicketStorage
from src.config import settings


# Initialize storage
ticket_storage = TicketStorage(str(settings.tickets_path))
customer_storage = CustomerStorage(ticket_storage)


def identify_customer_impl(email: Optional[str] = None, phone: Optional[str] = None) -> Dict[str, Any]:
    """
    Identify or create a customer based on email or phone.

    Args:
        email: Customer's email address (optional)
        phone: Customer's phone number (optional)

    Returns:
        Dictionary containing customer information
    """
    # Normalize inputs
    email = email.strip() if email else None
    phone = phone.strip() if phone else None

    # Validation
    if not email and not phone:
        raise ValueError("At least one of email or phone must be provided")

    # Try to find existing customer
    customer = customer_storage.get_customer_by_contact(email=email, phone=phone)

    if customer:
        # Customer exists in tickets
        return {
            "customer_id": customer.get("email") or customer.get("phone"),
            "is_new": False,
            "email": customer.get("email"),
            "phone": customer.get("phone"),
            "found_in_ticket": customer.get("found_in_ticket")
        }
    else:
        # Customer doesn't exist yet
        return {
            "customer_id": email or phone,
            "is_new": True,
            "email": email,
            "phone": phone,
            "found_in_ticket": None
        }
