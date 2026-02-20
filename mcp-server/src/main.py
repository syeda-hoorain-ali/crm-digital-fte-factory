"""MCP Server for CRM Digital FTE Factory

Implements the core MCP server with tools for customer support functionality.
"""

import logging
from typing import Optional
from pydantic import AnyHttpUrl
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings
from starlette.responses import JSONResponse, Response
from src.config import settings
from src.utils.security import AuthTokenVerifier
from src.tools import (
    search_product_docs_impl,
    create_support_ticket_impl,
    lookup_customer_impl,
    escalate_ticket_impl,
    save_reply_impl,
    analyze_sentiment_impl,
    identify_customer_impl
)


# Configure structured logging
logging.basicConfig(level=settings.log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Create the MCP server instance
mcp = FastMCP(
    "crm-digital-fte",
    streamable_http_path="/",
    port=settings.server_port,
    host=settings.server_host,
    log_level=settings.log_level,
    token_verifier=AuthTokenVerifier(),
        auth=AuthSettings(
        # We will use a dummy issuer URL for simple tokens
        issuer_url=AnyHttpUrl("https://local-auth"),
        resource_server_url=AnyHttpUrl("http://localhost:3001"),
        required_scopes=["user"],
    ),
)


@mcp.custom_route("/health", methods=["GET"]) 
async def health_check(request) -> Response: 
    return JSONResponse({"status": "ok"})


@mcp.tool(name="search_knowledge_base")
def search_tool(query: str, max_results: int = 5):
    """
    Search the knowledge base for relevant documentation.

    args
    query(str): The search query string
    max_results(int): Maximum number of results to return (default: 5)
    """
    return search_product_docs_impl(query, max_results)


@mcp.tool(name="create_ticket")
def create_ticket_tool(customer_id: str, issue: str, priority: str = "normal", channel: str = "web_form"):
    """
    Create a new support ticket for a customer.

    args
    customer_id(str): The ID of the customer creating the ticket
    issue(str): Description of the issue
    priority(str): Priority level (default: "normal")
    channel(str): Communication channel (default: "web_form")
    """
    return create_support_ticket_impl(customer_id, issue, priority, channel)


@mcp.tool(name="get_customer_history")
def get_customer_history_tool(customer_id: str):
    """
    Get the customer's history and past interactions.

    args
    customer_id(str): The ID of the customer
    """
    return lookup_customer_impl(customer_id)


@mcp.tool(name="escalate_to_human")
def escalate_to_human_tool(ticket_id: str, reason: str):
    """
    Escalate a ticket to human support agent.

    args
    ticket_id(str): The ID of the ticket to escalate
    reason(str): The reason for escalation
    """
    return escalate_ticket_impl(ticket_id, reason)


@mcp.tool(name="send_response")
def send_response_tool(ticket_id: str, message: str, channel: str = "web_form"):
    """
    Send a response to a customer regarding their ticket.

    args
    ticket_id(str): The ID of the ticket
    message(str): The response message
    channel(str): Communication channel (default: "web_form")
    """
    return save_reply_impl(ticket_id, message, channel)


@mcp.tool(name="analyze_sentiment")
def analyze_sentiment_tool(message_text: str):
    """
    Analyze the sentiment of a customer message.

    args
    message_text(str): The customer message text to analyze
    """
    return analyze_sentiment_impl(message_text)


@mcp.tool(name="identify_customer")
def identify_customer_tool(email: Optional[str] = None, phone: Optional[str] = None):
    """
    Identify or create a customer based on email or phone number.

    args
    email(str): Customer's email address (optional)
    phone(str): Customer's phone number (optional)
    """
    return identify_customer_impl(email, phone)


def main():
    import sys
    # Check if we should run in HTTP mode or stdio mode
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        # Run the async HTTP server
        mcp.run(transport="streamable-http") # uv run --with mcp src/main.py --http
    else:
        # Run in stdio mode (default behavior)
        mcp.run(transport="stdio") # uv run --with mcp src/main.py


if __name__ == "__main__":
    main()
