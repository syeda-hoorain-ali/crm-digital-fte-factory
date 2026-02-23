"""Escalate ticket to human tool implementation."""
import time
import uuid
from typing import Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from src.database.models import SupportTicket, EscalationRecord
from src.database.session import engine
from src.utils.metrics import metrics_collector
from src.utils.rate_limiter import check_rate_limit


def escalate_ticket_impl(ticket_id: str, reason: str, client_id: str = "default_client") -> Dict[str, Any]:
    """
    Implementation for escalating a ticket to human support.

    Args:
        ticket_id: The ID of the ticket to escalate
        reason: The reason for escalation
        client_id: ID of the requesting client (for metrics/rate limiting)

    Returns:
        Dictionary containing escalation result
    """
    # Record metrics
    metrics_collector.increment_request()
    metrics_collector.record_tool_usage("escalate_to_human")
    start_time = time.time()

    # Check rate limit
    if not check_rate_limit(client_id):
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("escalate_to_human", duration)
        raise Exception("Rate limit exceeded")

    try:
        # Input validation
        if not ticket_id or not isinstance(ticket_id, str):
            raise ValueError("Ticket ID must be a non-empty string")
        if not reason or not isinstance(reason, str):
            raise ValueError("Reason must be a non-empty string")

        # Generate a unique escalation ID
        escalation_id = f"esc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        with Session(engine) as session:
            # Find the ticket to escalate
            ticket_statement = select(SupportTicket).where(SupportTicket.ticket_id == ticket_id)
            ticket = session.exec(ticket_statement).first()

            if not ticket:
                raise ValueError(f"Ticket with ID {ticket_id} not found")

            # Update the ticket to mark it as escalated
            ticket.escalated = True
            ticket.escalation_reason = reason
            session.add(ticket)
            session.commit()

            # Create an escalation record
            escalation_record = EscalationRecord(
                escalation_id=escalation_id,
                ticket_id=ticket_id,
                reason=reason,
                timestamp=datetime.now()
            )
            session.add(escalation_record)
            session.commit()

        escalation_data = {
            "escalation_id": escalation_id,
            "ticket_id": ticket_id,
            "reason": reason,
            "status": "escalated",
            "timestamp": datetime.now().isoformat(),
            "next_steps": "Human agent will contact customer shortly"
        }

        duration = time.time() - start_time
        metrics_collector.record_response_time("escalate_to_human", duration)
        return escalation_data

    except Exception as e:
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("escalate_to_human", duration)
        raise e
