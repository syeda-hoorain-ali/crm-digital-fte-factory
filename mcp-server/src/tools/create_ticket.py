"""Create support ticket tool implementation."""
import time
import uuid
from typing import Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from src.database.models import Customer, SupportTicket
from src.database.session import engine
from src.utils.metrics import metrics_collector
from src.utils.rate_limiter import check_rate_limit


def create_support_ticket_impl(customer_id: str, issue: str, priority: str = "normal", channel: str = "web_form", client_id: str = "default_client") -> Dict[str, Any]:
    """
    Implementation for creating a support ticket.

    Args:
        customer_id: The ID of the customer creating the ticket
        issue: Description of the issue
        priority: Priority level
        channel: Communication channel
        client_id: ID of the requesting client (for metrics/rate limiting)

    Returns:
        Dictionary containing ticket creation result
    """
    # Record metrics
    metrics_collector.increment_request()
    metrics_collector.record_tool_usage("create_ticket")
    start_time = time.time()

    # Check rate limit
    if not check_rate_limit(client_id):
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("create_ticket", duration)
        raise Exception("Rate limit exceeded")

    try:
        # Input validation
        if not customer_id or not isinstance(customer_id, str):
            raise ValueError("Customer ID must be a non-empty string")
        if not issue or not isinstance(issue, str):
            raise ValueError("Issue must be a non-empty string")
        if priority not in ["low", "normal", "high", "urgent"]:
            raise ValueError("Priority must be one of: low, normal, high, urgent")
        if channel not in ["email", "web_form", "whatsapp", "chat"]:
            raise ValueError("Channel must be one of: email, web_form, whatsapp, chat")

        # Generate a unique ticket ID - use UUID to ensure uniqueness
        ticket_id = f"ticket_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        # Create and save the support ticket in the database
        with Session(engine) as session:
            # First, check if the customer exists
            customer_statement = select(Customer).where(Customer.customer_id == customer_id)
            customer = session.exec(customer_statement).first()

            if not customer:
                raise ValueError(f"Customer with ID {customer_id} not found. Please use identify_customer tool first to get the correct customer_id.")

            # Create the support ticket
            support_ticket = SupportTicket(
                ticket_id=ticket_id,
                customer_id=customer_id,
                channel=channel,
                query=issue,
                timestamp=datetime.now(),
                escalated=False
            )

            session.add(support_ticket)
            session.commit()
            session.refresh(support_ticket)

        ticket_data = {
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "issue": issue,
            "priority": priority,
            "channel": channel,
            "status": "created",
            "timestamp": datetime.now().isoformat()
        }

        duration = time.time() - start_time
        metrics_collector.record_response_time("create_ticket", duration)
        return ticket_data

    except Exception as e:
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("create_ticket", duration)
        raise e