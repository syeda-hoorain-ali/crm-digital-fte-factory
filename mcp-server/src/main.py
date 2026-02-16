"""MCP Server for CRM Digital FTE Factory

Implements the core MCP server with tools for customer support functionality.
"""

import logging
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from src.config import settings
from src.utils.security import verify_token
from src.tools.crm_tools import (
    search_product_docs_impl,
    create_support_ticket_impl,
    lookup_customer_impl,
    escalate_ticket_impl,
    save_reply_impl,
    initialize_database
)


# Configure structured logging
logging.basicConfig(level=settings.log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow health check without auth
        if request.url.path == "/health":
            return await call_next(request)

        # If no token is configured on the server, skip auth (for development)
        if not settings.mcp_server_token:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized: Missing or invalid Authorization header"})

        token = auth_header.split(" ", 1)[1]
        if not verify_token(token):
            return JSONResponse(status_code=403, content={"detail": "Forbidden: Invalid token"})

        return await call_next(request)


# Create the MCP server instance
mcp = FastMCP(
    "crm-digital-fte",
    streamable_http_path="/",
    port=settings.server_port,
    host=settings.server_host,
    log_level=settings.log_level,
)

# Add the authentication middleware
mcp.add_middleware(AuthMiddleware)


@mcp.custom_route("/health", methods=["GET"]) 
async def health_check(request) -> Response: 
    return JSONResponse({"status": "ok"})


@mcp.tool(name="search_knowledge_base")
def search_tool(query: str):
    """
    Search the knowledge base for relevant documentation.

    args
    query(str): The search query string
    """
    return search_product_docs_impl(query)


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


def main():
    # Initialize the database when the server starts
    initialize_database()

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
