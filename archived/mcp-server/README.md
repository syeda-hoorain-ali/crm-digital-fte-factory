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
DATABASE_URL=postgresql://user:password@localhost:5432/crm-gidital-fte
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

## Project Structure

The MCP server follows a modular architecture with each tool implemented in its own file:

```
mcp-server/
├── src/
│   ├── main.py                      # MCP server entry point
│   ├── config.py                    # Configuration management
│   ├── database/
│   │   ├── models.py                # SQLModel database models
│   │   └── session.py               # Database session factory
│   ├── tools/
│   │   ├── __init__.py              # Central export point for all tools
│   │   ├── analyze_sentiment.py    # Sentiment analysis tool
│   │   ├── create_ticket.py        # Ticket creation tool
│   │   ├── escalate_to_human.py    # Escalation tool
│   │   ├── get_customer_history.py # Customer lookup tool
│   │   ├── identify_customer.py    # Customer identification tool
│   │   ├── search_knowledge_base.py # Knowledge base search tool
│   │   └── send_response.py        # Response sending tool
│   └── utils/
│       ├── embeddings.py            # Vector embedding utilities
│       ├── metrics.py               # Metrics collection
│       ├── rate_limiter.py          # Rate limiting
│       └── security.py              # Authentication utilities
└── tests/
    ├── unit/                        # Unit tests for individual components
    ├── integration/                 # End-to-end workflow tests
    └── conftest.py                  # Shared test fixtures
```

### Modular Tool Design

Each tool is implemented in its own file (~77-139 lines each) for better:
- **Maintainability**: Easy to locate and modify individual tools
- **Readability**: Developers can focus on one tool at a time
- **Testability**: Easier to test tools in isolation
- **Version Control**: Changes to one tool don't affect others

All tools are exported through `src/tools/__init__.py` for convenient importing:

```python
from src.tools import (
    search_product_docs_impl,
    create_support_ticket_impl,
    # ... etc
)
```

## Architecture

- **Database**: SQLModel with asyncpg (PostgreSQL with pgvector for semantic search)
- **Security**: Token-based authentication and rate limiting
- **Metrics**: Request counting, error rates, and response times
- **Logging**: Structured logging for operations and debugging
- **Modular Tools**: Each tool in separate file for maintainability
