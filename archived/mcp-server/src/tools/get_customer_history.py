"""Get customer history tool implementation."""
import time
from typing import Dict, Any
from datetime import datetime
from sqlmodel import Session, select, desc
from src.database.models import Customer, SupportTicket
from src.database.session import engine
from src.utils.metrics import metrics_collector
from src.utils.rate_limiter import check_rate_limit


def lookup_customer_impl(customer_id: str, client_id: str = "default_client") -> Dict[str, Any]:
    """
    Implementation for looking up customer information.

    Args:
        customer_id: The ID of the customer to look up
        client_id: ID of the requesting client (for metrics/rate limiting)

    Returns:
        Dictionary containing customer information and history
    """
    # Record metrics
    metrics_collector.increment_request()
    metrics_collector.record_tool_usage("get_customer_history")
    start_time = time.time()

    # Check rate limit
    if not check_rate_limit(client_id):
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("get_customer_history", duration)
        raise Exception("Rate limit exceeded")

    try:
        # Input validation
        if not customer_id or not isinstance(customer_id, str):
            raise ValueError("Customer ID must be a non-empty string")

        # Look up customer in the database
        with Session(engine) as session:
            # Get customer details
            customer_statement = select(Customer).where(Customer.customer_id == customer_id)
            customer = session.exec(customer_statement).first()

            if not customer:
                # Return a default customer if not found
                customer_data = {
                    "customer_id": customer_id,
                    "name": "Unknown Customer",
                    "email": f"{customer_id}@example.com",
                    "plan_type": "unknown",
                    "subscription_status": "inactive",
                    "last_interaction": datetime.now().isoformat(),
                    "support_tickets": [],
                    "interaction_history": []
                }
            else:
                # Get customer's support tickets
                tickets_statement = select(SupportTicket).where(SupportTicket.customer_id == customer_id).order_by(desc(SupportTicket.timestamp))
                tickets = session.exec(tickets_statement).all()

                # Format ticket IDs
                ticket_ids = [ticket.ticket_id for ticket in tickets]

                customer_data = {
                    "customer_id": customer.customer_id,
                    "name": f"Customer {customer.customer_id}",  # In a real system, we'd have names
                    "email": customer.email,
                    "plan_type": customer.plan_type,
                    "subscription_status": customer.subscription_status,
                    "last_interaction": customer.last_interaction,
                    "support_tickets": ticket_ids,
                    "interaction_history": [
                        {
                            "date": ticket.timestamp,
                            "type": "support_ticket",
                            "summary": f"Ticket #{ticket.ticket_id}: {ticket.query[:50]}{'...' if len(ticket.query) > 50 else ''}"
                        } for ticket in tickets
                    ]
                }

        duration = time.time() - start_time
        metrics_collector.record_response_time("get_customer_history", duration)
        return customer_data

    except Exception as e:
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("get_customer_history", duration)
        raise e
