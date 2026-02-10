"""
Runner Module for the Customer Success AI Agent
Handles processing customer queries and running the agent
"""

import sys
import json
from pathlib import Path
from typing import Dict, List
from agents import Runner
from agents.memory import SQLiteSession
from .agents import customer_success_agent


async def process_customer_query(query: str, customer_identifier: str, channel: str, session: SQLiteSession):
    """
    Process a customer query using the agent

    Args:
        query: The customer's query
        customer_identifier: Email or phone number of the customer
        channel: Communication channel (gmail, whatsapp, web_form)
        session: Session for maintaining conversation history
    """
    # Prepare the input for the agent
    full_input = f"""
Customer Query: {query}
Customer Identifier: {customer_identifier}
Communication Channel: {channel}

Please analyze this query, use available tools to gather information,
and provide an appropriate response. If the issue requires specialist attention,
please use the appropriate handoff.
"""

    # Run the agent
    result = await Runner.run(
        customer_success_agent,
        full_input,
        session=session
    )

    return result


async def run_customer_success_demo():
    """Run a demonstration of the customer success agent using sample tickets from context"""
    print("Starting Customer Success AI Agent Demo")
    print("=" * 60)


    # Get the project root directory (where pyproject.toml is located)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent

    # Load sample tickets from the context directory
    sample_tickets_path = project_root / "context" / "sample-tickets.json"
    with open(sample_tickets_path, "r") as f:
        sample_tickets: List[Dict] = json.load(f)

    # Process each ticket in the sample data
    for i, ticket in enumerate(sample_tickets):
        print(f"\nDemo Query {i+1}:")

        # Determine customer identifier (email or phone)
        customer_identifier = ticket.get("customer_email") or ticket.get("customer_phone")
        if not customer_identifier:
            print(f"Skipping ticket {ticket['id']} - no customer identifier")
            continue

        query = f"{ticket.get('subject', '')}\n {ticket.get('content', '')}".strip() if ticket.get('subject') else ticket.get("content", "")
        channel = ticket["channel"]

        print(f"Ticket ID: {ticket['id']}")
        print(f"Customer: {customer_identifier}")
        print(f"Channel: {channel}")
        print(f"Query: {query[:70]}{'...' if len(query) > 70 else ''}")

        try:
            # Create a session for each customer for conversation history
            session = SQLiteSession(f"customer_{customer_identifier}")

            result = await process_customer_query(
                query,
                customer_identifier,
                channel,
                session
            )

            print(f"Agent Response: {result.final_output[:100]}{'...' if len(result.final_output) > 100 else ''}")
            print("-" * 60)
        except Exception as e:
            print(f"Error processing query: {str(e)}")
            print("-" * 60)

    print("\nDemo completed! Check the 'replies' directory for saved responses.")
