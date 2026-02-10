"""
Channel Handler for Customer Success AI Agent
Manages different communication channels (Gmail, WhatsApp, Web Forms)
"""

import asyncio
from typing import Dict, Any
from datetime import datetime
from agents.memory import SQLiteSession
from src.agent import process_customer_query


class ChannelHandler:
    """Handles communication through different channels"""

    def __init__(self):
        self.sessions = {}  # Store sessions by customer identifier

    def _get_or_create_session(self, customer_identifier: str) -> SQLiteSession:
        """Get or create a session for a customer"""
        if customer_identifier not in self.sessions:
            self.sessions[customer_identifier] = SQLiteSession(f"customer_{customer_identifier}")
        return self.sessions[customer_identifier]

    async def handle_gmail(self, customer_email: str, subject: str, message_body: str) -> Dict[str, Any]:
        """Handle incoming Gmail messages"""
        print(f"Gmail received from {customer_email}")

        # Combine subject and message body
        full_query = f"Subject: {subject}\n\nMessage: {message_body}"

        # Get or create session for this customer
        session = self._get_or_create_session(customer_email)

        # Process the query with the agent
        result = await process_customer_query(full_query, customer_email, "gmail", session)

        return {
            "status": "processed",
            "customer_email": customer_email,
            "subject": subject,
            "response": result.final_output,
            "timestamp": datetime.now().isoformat()
        }

    async def handle_whatsapp(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Handle incoming WhatsApp messages"""
        print(f"WhatsApp received from {phone_number}")

        # Process the query with the agent
        session = self._get_or_create_session(phone_number)
        result = await process_customer_query(message, phone_number, "whatsapp", session)

        return {
            "status": "processed",
            "phone_number": phone_number,
            "original_message": message,
            "response": result.final_output,
            "timestamp": datetime.now().isoformat()
        }

    async def handle_web_form(self, customer_email: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming web form submissions"""
        print(f"Web form received from {customer_email}")

        # Construct the query from form data
        form_query_parts = []
        for key, value in form_data.items():
            if key != "email":  # Don't duplicate the email
                form_query_parts.append(f"{key}: {value}")
        full_query = "\n".join(form_query_parts)

        # Process the query with the agent
        session = self._get_or_create_session(customer_email)
        result = await process_customer_query(full_query, customer_email, "web_form", session)

        return {
            "status": "processed",
            "customer_email": customer_email,
            "form_data": form_data,
            "response": result.final_output,
            "timestamp": datetime.now().isoformat()
        }

    async def handle_incoming_message(self, channel: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generic handler that routes to the appropriate channel handler"""
        if channel.lower() == "gmail":
            return await self.handle_gmail(
                customer_email=data["email"],
                subject=data.get("subject", ""),
                message_body=data.get("message", "")
            )
        elif channel.lower() == "whatsapp":
            return await self.handle_whatsapp(
                phone_number=data["phone_number"],
                message=data["message"]
            )
        elif channel.lower() == "web_form":
            return await self.handle_web_form(
                customer_email=data["email"],
                form_data=data
            )
        else:
            raise ValueError(f"Unsupported channel: {channel}")


# Demo function to simulate incoming messages
async def run_channel_demo():
    """Run a demo of the channel handler"""
    print("Starting Channel Handler Demo")
    print("=" * 60)

    handler = ChannelHandler()

    # Simulate different types of incoming messages
    test_messages = [
        {
            "channel": "gmail",
            "data": {
                "email": "jane.doe@pixel-agency.com",
                "subject": "Gantt Chart Issue",
                "message": "Hi CloudStream team, I'm on the Starter plan and I can't find the Gantt chart view. Is it hidden somewhere or not available?"
            }
        },
        {
            "channel": "whatsapp",
            "data": {
                "phone_number": "+14155550192",
                "message": "Hey! My client is saying they can't see the 'Approve' button in the portal. Any idea why? I'm using the latest version."
            }
        },
        {
            "channel": "web_form",
            "data": {
                "email": "tech-lead@webflow-pros.io",
                "query_type": "API Access",
                "message": "We just upgraded to the Pro plan. Where can I find my API key and the documentation for the webhooks integration?"
            }
        },
        {
            "channel": "gmail",
            "data": {
                "email": "frustrated-user@example.com",
                "subject": "Account Cancellation",
                "message": "Your software is too complicated and I'm tired of the bugs. Cancel my account and I'm switching to a competitor."
            }
        }
    ]

    for i, test_msg in enumerate(test_messages):
        print(f"\nProcessing Message {i+1}:")
        print(f"Channel: {test_msg['channel']}")

        try:
            result = await handler.handle_incoming_message(
                channel=test_msg['channel'],
                data=test_msg['data']
            )

            print(f"Response preview: {result['response'][:100]}{'...' if len(result['response']) > 100 else ''}")
            print("-" * 60)
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            print("-" * 60)

    print("\nChannel handler demo completed!")


if __name__ == "__main__":
    asyncio.run(run_channel_demo())
