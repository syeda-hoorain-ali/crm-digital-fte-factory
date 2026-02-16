# CRM Digital FTE Factory - MCP Server

The Model Context Protocol (MCP) server for the CRM Digital FTE Factory project. This server exposes customer support functionality through standardized MCP tools that can be used by AI agents.

## Overview

The MCP server provides the following tools for customer support operations:

- `search_knowledge_base(query)` - Search the product documentation knowledge base
- `create_ticket(customer_id, issue, priority, channel)` - Create a new support ticket
- `get_customer_history(customer_id)` - Retrieve customer interaction history
- `escalate_to_human(ticket_id, reason)` - Escalate a ticket to human support
- `send_response(ticket_id, message, channel)` - Send a response to a customer

## Setup

### Prerequisites

- Python 3.11+
- UV package manager

### Installation

```bash
cd mcp-server
uv sync
```

### Configuration

Create a `.env` file in the mcp-server directory:

```env
MCP_SERVER_TOKEN=your-secret-token-here
DATABASE_URL=sqlite:///./mcp_server.db
```

## Running the Server

### Development Mode

```bash
cd mcp-server
uv run mcp-server --stdio
```

### Production Mode

```bash
# For HTTP transport
uv run mcp-server
```

## Connecting to Claude

Configure Claude to connect to the MCP server:

```json
{
  "mcpServers": {
    "crm-digital-fte": {
      "command": "uv",
      "args": ["run", "src/main.py"],
      "env": {
        "MCP_SERVER_TOKEN": "your-secret-token-here"
      }
    }
  }
}
```

## Features

- **Authentication**: Secured with configurable tokens
- **Rate Limiting**: Prevents abuse with configurable limits
- **Monitoring**: Health checks and metrics collection
- **Structured Logging**: Comprehensive logging for debugging
- **Input Validation**: All inputs are validated before processing
- **Error Handling**: Comprehensive error handling with meaningful messages

## Testing

Run the unit tests:

```bash
cd mcp-server
uv run pytest tests/unit/
```

Run the integration tests:

```bash
cd mcp-server
uv run pytest tests/integration/
```

Run all tests:

```bash
cd mcp-server
uv run pytest
```

## Architecture

- **Database**: SQLModel with SQLite (configurable to PostgreSQL)
- **Security**: Token-based authentication and rate limiting
- **Metrics**: Request counting, error rates, and response times
- **Logging**: Structured logging for operations and debugging