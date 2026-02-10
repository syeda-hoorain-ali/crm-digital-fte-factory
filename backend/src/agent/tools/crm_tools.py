"""
CRM Tools for the Customer Success AI Agent
These tools allow the agent to interact with customer data and support systems
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from agents import function_tool


@dataclass
class CustomerData:
    """Data structure for customer information"""
    customer_id: str
    email: str
    plan_type: str
    subscription_status: str
    last_interaction: str
    support_tickets: List[str]


@dataclass
class SupportTicket:
    """Data structure for support tickets"""
    ticket_id: str
    customer_id: str
    channel: str
    query: str
    timestamp: str
    escalated: bool
    escalation_reason: Optional[str]


# Mock database for storing customer data and tickets
CUSTOMER_DB = {
    "jane.doe@pixel-agency.com": CustomerData(
        customer_id="cust-001",
        email="jane.doe@pixel-agency.com",
        plan_type="starter",
        subscription_status="active",
        last_interaction="2024-01-15",
        support_tickets=["TKT-001", "TKT-005"]
    ),
    "+14155550192": CustomerData(
        customer_id="cust-002",
        email="",
        plan_type="pro",
        subscription_status="active",
        last_interaction="2024-01-16",
        support_tickets=["TKT-002"]
    ),
    "tech-lead@webflow-pros.io": CustomerData(
        customer_id="cust-003",
        email="tech-lead@webflow-pros.io",
        plan_type="pro",
        subscription_status="active",
        last_interaction="2024-01-17",
        support_tickets=["TKT-003"]
    ),
    "frustrated-user@example.com": CustomerData(
        customer_id="cust-004",
        email="frustrated-user@example.com",
        plan_type="enterprise",
        subscription_status="active",
        last_interaction="2024-01-18",
        support_tickets=["TKT-005"]
    )
}

TICKET_DB = []


@function_tool
def lookup_customer(email_or_phone: str) -> Optional[Dict]:
    """
    Look up customer information by email or phone number.

    Args:
        email_or_phone: The email address or phone number to search for
    """
    customer = CUSTOMER_DB.get(email_or_phone)
    if customer:
        return {
            "customer_id": customer.customer_id,
            "email": customer.email,
            "plan_type": customer.plan_type,
            "subscription_status": customer.subscription_status,
            "last_interaction": customer.last_interaction,
            "support_tickets": customer.support_tickets
        }
    return None


@function_tool
def create_support_ticket(customer_email_or_phone: str, channel: str, query: str) -> Dict:
    """
    Create a new support ticket for a customer.

    Args:
        customer_email_or_phone: The customer's email or phone number
        channel: The communication channel (gmail, whatsapp, web_form)
        query: The customer's support query
    """
    # Generate a new ticket ID
    ticket_id = f"TKT-{len(TICKET_DB) + 1:03d}"

    # Create the ticket
    ticket = SupportTicket(
        ticket_id=ticket_id,
        customer_id=CUSTOMER_DB.get(customer_email_or_phone, {}).get("customer_id", "unknown"),
        channel=channel,
        query=query,
        timestamp=datetime.now().isoformat(),
        escalated=False,
        escalation_reason=None
    )

    TICKET_DB.append(ticket)

    return {
        "ticket_id": ticket_id,
        "status": "created",
        "estimated_resolution_time": "24 hours"
    }


@function_tool
def escalate_ticket(ticket_id: str, reason: str) -> Dict:
    """
    Escalate a support ticket to human agent.

    Args:
        ticket_id: The ID of the ticket to escalate
        reason: The reason for escalation
    """
    # Find the ticket in the database
    for ticket in TICKET_DB:
        if ticket.ticket_id == ticket_id:
            ticket.escalated = True
            ticket.escalation_reason = reason
            break

    return {
        "ticket_id": ticket_id,
        "status": "escalated",
        "reason": reason,
        "next_steps": "A human agent will contact the customer within 2 hours"
    }


@function_tool
def search_product_docs(query: str) -> List[Dict]:
    """
    Search the product documentation for relevant information.

    Args:
        query: The search query
    """
    # Mock product documentation
    docs = [
        {
            "id": "doc-001",
            "title": "Starter Plan Features",
            "content": "The Starter plan includes basic project management, team collaboration tools, and standard reporting. Gantt charts are only available on Pro and Enterprise plans.",
            "category": "pricing",
            "relevance_score": 0.9 if "gantt" in query.lower() or "starter" in query.lower() else 0.1
        },
        {
            "id": "doc-002",
            "title": "Client Portal Access",
            "content": "The 'Approve' button appears in the ClientBridge portal when a client has viewing access. Projects must be explicitly shared with clients through the Share menu in project settings.",
            "category": "features",
            "relevance_score": 0.9 if "approve" in query.lower() or "client" in query.lower() else 0.1
        },
        {
            "id": "doc-003",
            "title": "API Access and Webhooks",
            "content": "API access is available on Pro and Enterprise plans. API keys can be found in Settings > Integrations > API Keys. Documentation for webhooks is available at https://cloudstream-crm.com/docs/webhooks",
            "category": "integrations",
            "relevance_score": 0.9 if "api" in query.lower() or "webhook" in query.lower() else 0.1
        },
        {
            "id": "doc-004",
            "title": "Enterprise Features",
            "content": "Enterprise plan includes advanced analytics, custom branding, dedicated support, and SSO integration. Contact sales for custom enterprise packages.",
            "category": "pricing",
            "relevance_score": 0.9 if "enterprise" in query.lower() else 0.1
        },
        {
            "id": "doc-005",
            "title": "Cancellation Policy",
            "content": "Customers can cancel their subscription at any time. Cancellations take effect at the end of the current billing cycle. No refunds are provided for partial months.",
            "category": "support",
            "relevance_score": 0.9 if "cancel" in query.lower() or "cancellation" in query.lower() else 0.1
        }
    ]

    # Filter and sort by relevance
    relevant_docs = [doc for doc in docs if doc["relevance_score"] > 0.5]
    relevant_docs.sort(key=lambda x: x["relevance_score"], reverse=True)

    return relevant_docs[:3]  # Return top 3 results


@function_tool
def save_reply_to_file(ticket_id: str, customer_email_or_phone: str, reply: str, channel: str) -> Dict:
    """
    Save the agent's reply to a file for record keeping.

    Args:
        ticket_id: The ID of the associated ticket
        customer_email_or_phone: The customer identifier
        reply: The reply content
        channel: The communication channel
    """

    # Create replies directory if it doesn't exist
    import sys
    from pathlib import Path

    # Get the project root directory (where pyproject.toml is located)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent.parent

    replies_dir = project_root / "replies"
    os.makedirs(replies_dir, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{replies_dir}/reply_{ticket_id}_{timestamp}.txt"

    # Write the reply to the file
    with open(filename, "w") as f:
        f.write(f"Ticket ID: {ticket_id}\n")
        f.write(f"Customer: {customer_email_or_phone}\n")
        f.write(f"Channel: {channel}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Reply:\n{reply}\n")

    return {
        "status": "saved",
        "filename": filename,
        "ticket_id": ticket_id
    }
