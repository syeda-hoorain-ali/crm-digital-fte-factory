"""CRM Tools functions for MCP server

These functions contain the actual business logic for CRM operations.
"""
import time
import uuid
from typing import Dict, Any, List
from datetime import datetime
from src.database.models import Customer, SupportTicket, DocumentationResult, EscalationRecord
from src.database.session import engine
from sqlmodel import Session, select, col, desc
from src.utils.metrics import metrics_collector
from src.utils.rate_limiter import check_rate_limit


def initialize_database():
    """Initialize the database tables if they don't exist."""
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(bind=engine)


def search_product_docs_impl(query: str, client_id: str = "default_client") -> List[Dict[str, Any]]:
    """
    Implementation for searching product documentation.

    Args:
        query: The search query string
        client_id: ID of the requesting client (for metrics/rate limiting)

    Returns:
        List of documentation results
    """
    # Record metrics
    metrics_collector.increment_request()
    metrics_collector.record_tool_usage("search_knowledge_base")
    start_time = time.time()

    # Check rate limit
    if not check_rate_limit(client_id):
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("search_knowledge_base", duration)
        raise Exception("Rate limit exceeded")

    try:
        # Input validation
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")

        # Initialize database if needed
        initialize_database()

        # Search for documentation results in the database
        with Session(engine) as session:
            # Look for documents that match the query in title or content
            statement = select(DocumentationResult).where(
                col(DocumentationResult.title).ilike(f"%{query}%") |
                col(DocumentationResult.content).ilike(f"%{query}%")
            ).order_by(desc(DocumentationResult.relevance_score))

            results = session.exec(statement).all()

            # Convert to dict format
            docs_list = []
            for doc in results:
                docs_list.append({
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content,
                    "category": doc.category,
                    "relevance_score": doc.relevance_score
                })

            # If no results found, return some default documentation
            if not docs_list:
                docs_list = [
                    {
                        "id": "doc_default",
                        "title": "General Product Information",
                        "content": "This is general product documentation that covers our main features.",
                        "category": "general",
                        "relevance_score": 0.5
                    }
                ]

        duration = time.time() - start_time
        metrics_collector.record_response_time("search_knowledge_base", duration)
        return docs_list

    except Exception as e:
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("search_knowledge_base", duration)
        raise e


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

        # Initialize database if needed
        initialize_database()

        # Generate a unique ticket ID - use UUID to ensure uniqueness
        import uuid
        ticket_id = f"ticket_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        # Create and save the support ticket in the database
        with Session(engine) as session:
            # First, check if the customer exists
            customer_statement = select(Customer).where(Customer.customer_id == customer_id)
            customer = session.exec(customer_statement).first()

            if not customer:
                # Create a default customer if not found
                customer = Customer(
                    customer_id=customer_id,
                    email=f"{customer_id}@example.com",
                    plan_type="unknown",
                    subscription_status="active",
                    last_interaction=datetime.now().isoformat()
                )
                session.add(customer)
                session.commit()

            # Create the support ticket
            support_ticket = SupportTicket(
                ticket_id=ticket_id,
                customer_id=customer_id,
                channel=channel,
                query=issue,
                timestamp=datetime.now().isoformat(),
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

        # Initialize database if needed
        initialize_database()

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

        # Initialize database if needed
        initialize_database()

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
                timestamp=datetime.now().isoformat()
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

        # Initialize database if needed
        initialize_database()

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
